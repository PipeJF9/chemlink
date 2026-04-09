"""Active site detection pipeline step for molecular docking."""

import os
import shutil
import subprocess
import tempfile
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from typing import Optional, Dict, List, Tuple, Any

from tqdm import tqdm


from ....storage.file_manager import (
	create_folder,
	list_files_in_directory,
	find_compound_name,
	create_out_file,
)
from ....utils.logger import setup_logger

logger = setup_logger(__name__)


class ActiveSiteDetection:
	"""Detect binding pockets and generate GPF files for docking.

	Workflow:
	1. Run fpocket for each receptor
	2. Collect pocket1 atoms file
	3. Compute box center and size
	4. Generate receptor-specific .gpf with prepare_gpf4.py
	"""

	DEFAULT_FPOCKET_PATH = "/usr/bin/fpocket"
	FPOCKET_CANDIDATES = (
		"/usr/local/bin/fpocket",
		"/usr/bin/fpocket",
	)
	DEFAULT_MGLTOOLS_PATH = "/opt/mgltools"

	def __init__(
		self,
		receptor_path: str,
		ligand_path: str,
		output_path: str,
		fpocket_path: Optional[str] = None,
		mgltools_path: Optional[str] = None,
		box_padding: float = 5.0,
		autodock_margin: int = 55,
		npts_min: int = 20,
		npts_max: int = 126,
		manual_center: Optional[Tuple[float, float, float]] = None,
		manual_npts: Optional[Tuple[int, int, int]] = None,
	):
		"""Initialize active site detection step.

		Args:
			receptor_path: Directory containing prepared receptor .pdbqt files
			ligand_path: Directory containing prepared ligand .pdbqt files
			output_path: Base directory for generated outputs/reports
			fpocket_path: Path to fpocket binary
			mgltools_path: Path to MGLTools installation
			box_padding: Padding added to raw pocket dimensions (angstrom)
			autodock_margin: Margin added before converting to npts
			npts_min: Minimum npts dimension for AutoDock grid
			npts_max: Maximum npts dimension for AutoDock grid
		"""
		self.receptor_path = receptor_path
		self.ligand_path = ligand_path
		self.output_path = output_path

		self.fpocket_path = self._resolve_fpocket_path(fpocket_path)
		self.mgltools_path = mgltools_path or self.DEFAULT_MGLTOOLS_PATH

		self.box_padding = box_padding
		self.autodock_margin = autodock_margin
		self.npts_min = npts_min
		self.npts_max = npts_max
		self.manual_center = manual_center
		self.manual_npts = manual_npts

		if (self.manual_center is None) != (self.manual_npts is None):
			raise ValueError(
				"Manual mode requires both manual_center and manual_npts"
			)

		if self.manual_npts is not None:
			if any(value <= 0 for value in self.manual_npts):
				raise ValueError("manual_npts values must be > 0")

		self.pocket_folder = os.path.join(self.output_path, "pdbBoxes")
		self.dimensions_folder = os.path.join(self.output_path, "dimensionsBoxes")

		self.mgltools_python = os.path.join(self.mgltools_path, "bin", "pythonsh")
		self.prepare_gpf_script = os.path.join(
			self.mgltools_path,
			"MGLToolsPckgs",
			"AutoDockTools",
			"Utilities24",
			"prepare_gpf4.py",
		)

	@property
	def is_manual_mode(self) -> bool:
		"""Return True when manual grid center and npts are configured."""
		return self.manual_center is not None and self.manual_npts is not None

	@classmethod
	def _resolve_fpocket_path(cls, fpocket_path: Optional[str]) -> str:
		"""Resolve fpocket executable from explicit path, PATH, or known locations."""
		if fpocket_path:
			if os.path.isabs(fpocket_path):
				return fpocket_path
			resolved = shutil.which(fpocket_path)
			if resolved:
				return resolved
			return fpocket_path

		resolved = shutil.which("fpocket")
		if resolved:
			return resolved

		for candidate in cls.FPOCKET_CANDIDATES:
			if os.path.isfile(candidate):
				return candidate

		return cls.DEFAULT_FPOCKET_PATH

	def _validate_dependencies(self) -> None:
		"""Validate required external binaries and scripts."""
		if not self.is_manual_mode:
			if not os.path.isfile(self.fpocket_path):
				raise FileNotFoundError(
					f"fpocket not found: {self.fpocket_path}. "
					"Pass --fpocket-path or ensure fpocket is available in PATH."
				)
			if not os.access(self.fpocket_path, os.X_OK):
				raise RuntimeError(f"fpocket is not executable: {self.fpocket_path}")

		if not os.path.isfile(self.mgltools_python):
			raise FileNotFoundError(
				f"MGLTools pythonsh not found: {self.mgltools_python}"
			)
		if not os.path.isfile(self.prepare_gpf_script):
			raise FileNotFoundError(
				f"prepare_gpf4.py not found: {self.prepare_gpf_script}"
			)

	def _get_mgltools_env(self) -> Dict[str, str]:
		"""Build environment variables for MGLTools execution."""
		env = os.environ.copy()
		env["MGLTOOLS_HOME"] = self.mgltools_path
		env["MGL_ROOT"] = self.mgltools_path
		env["PYTHONPATH"] = os.path.join(
			self.mgltools_path, "MGLToolsPckgs"
		) + ":" + env.get("PYTHONPATH", "")
		env["PATH"] = os.path.join(self.mgltools_path, "bin") + ":" + env.get("PATH", "")
		env["LD_LIBRARY_PATH"] = os.path.join(
			self.mgltools_path, "lib"
		) + ":" + env.get("LD_LIBRARY_PATH", "")
		return env

	def _collect_receptors(self) -> List[str]:
		"""Collect receptor files to process."""
		return sorted(list_files_in_directory(self.receptor_path, ["*.pdbqt"]))

	def _select_reference_ligand(self) -> str:
		"""Select first available ligand .pdbqt as reference for GPF generation."""
		ligands = sorted(list_files_in_directory(self.ligand_path, ["*.pdbqt"]))
		if not ligands:
			raise RuntimeError(f"No ligand .pdbqt files found in: {self.ligand_path}")
		return ligands[0]

	def _get_shard_config(self) -> Optional[Tuple[int, int]]:
		"""Return (shard_index, shard_count) from environment if configured."""
		shard_index_env = os.getenv("CHEMLINK_SHARD_INDEX")
		shard_count_env = os.getenv("CHEMLINK_SHARD_COUNT")

		if shard_index_env is not None or shard_count_env is not None:
			if shard_index_env is None or shard_count_env is None:
				raise RuntimeError(
					"Both CHEMLINK_SHARD_INDEX and CHEMLINK_SHARD_COUNT must be set"
				)

			try:
				shard_index = int(shard_index_env)
				shard_count = int(shard_count_env)
			except ValueError as exc:
				raise RuntimeError(
					"CHEMLINK_SHARD_INDEX and CHEMLINK_SHARD_COUNT must be integers"
				) from exc
		elif os.getenv("SLURM_ARRAY_TASK_ID") is not None:
			try:
				slurm_task_id = int(os.getenv("SLURM_ARRAY_TASK_ID", "0"))
			except ValueError as exc:
				raise RuntimeError("SLURM_ARRAY_TASK_ID must be an integer") from exc

			slurm_task_count = os.getenv("SLURM_ARRAY_TASK_COUNT")
			slurm_task_min = os.getenv("SLURM_ARRAY_TASK_MIN")
			slurm_task_max = os.getenv("SLURM_ARRAY_TASK_MAX")

			if slurm_task_count is not None:
				try:
					shard_count = int(slurm_task_count)
				except ValueError as exc:
					raise RuntimeError(
						"SLURM_ARRAY_TASK_COUNT must be an integer"
					) from exc

				if slurm_task_min is not None:
					try:
						task_min = int(slurm_task_min)
					except ValueError as exc:
						raise RuntimeError(
							"SLURM_ARRAY_TASK_MIN must be an integer"
						) from exc
					shard_index = slurm_task_id - task_min
				else:
					shard_index = slurm_task_id
			elif slurm_task_min is not None and slurm_task_max is not None:
				try:
					task_min = int(slurm_task_min)
					task_max = int(slurm_task_max)
				except ValueError as exc:
					raise RuntimeError(
						"SLURM_ARRAY_TASK_MIN and SLURM_ARRAY_TASK_MAX must be integers"
					) from exc

				shard_count = (task_max - task_min) + 1
				shard_index = slurm_task_id - task_min
			else:
				return None
		else:
			return None

		if shard_count <= 1:
			return None
		if shard_count <= 0:
			raise RuntimeError("Shard count must be > 0")
		if shard_index < 0 or shard_index >= shard_count:
			raise RuntimeError(
				f"Invalid shard index {shard_index} for shard count {shard_count}"
			)

		return shard_index, shard_count

	@staticmethod
	def _select_shard_files(files: List[str], shard_index: int, shard_count: int) -> List[str]:
		"""Return round-robin file subset assigned to a shard."""
		return files[shard_index::shard_count]

	@staticmethod
	def _strip_pdbqt_to_pdb(input_pdbqt: str, output_pdb: str) -> None:
		"""Create a PDB-like file from PDBQT for tools that expect PDB."""
		kept = 0
		with open(input_pdbqt, "r") as src, open(output_pdb, "w") as dst:
			for line in src:
				if line.startswith(("ATOM", "HETATM", "TER", "END")):
					dst.write(line[:66].rstrip() + "\n")
					kept += 1

		if kept == 0:
			raise RuntimeError(f"No ATOM/HETATM records found in {input_pdbqt}")

	def _run_fpocket(self, receptor_file: str) -> str:
		"""Run fpocket for one receptor and return pocket1 file path."""
		receptor_name = find_compound_name(receptor_file)

		with tempfile.TemporaryDirectory(prefix=f"fpocket_{receptor_name}_") as tmpdir:
			pdb_input = os.path.join(tmpdir, f"{receptor_name}.pdb")
			self._strip_pdbqt_to_pdb(receptor_file, pdb_input)

			cmd = [self.fpocket_path, "-f", pdb_input]
			result = subprocess.run(
				cmd,
				capture_output=True,
				text=True,
				cwd=tmpdir,
			)

			if result.returncode != 0:
				raise RuntimeError(
					f"fpocket failed for {receptor_name}: {result.stderr.strip()}"
				)

			fpocket_out = os.path.join(tmpdir, f"{receptor_name}_out")
			pocket1 = os.path.join(fpocket_out, "pockets", "pocket1_atm.pdb")
			if not os.path.isfile(pocket1):
				raise RuntimeError(
					f"fpocket output missing pocket1_atm.pdb for {receptor_name}"
				)

			output_pocket = create_out_file(
				self.pocket_folder,
				f"{receptor_name}_pocket_atm1.pdb",
			)
			shutil.copy2(pocket1, output_pocket)
			return output_pocket

	@staticmethod
	def _parse_atom_xyz(line: str) -> Tuple[float, float, float]:
		"""Parse atom coordinates from a PDB atom line using fixed columns."""
		return (
			float(line[30:38].strip()),
			float(line[38:46].strip()),
			float(line[46:54].strip()),
		)

	def _calculate_box(self, pocket_file: str) -> Dict[str, Any]:
		"""Calculate center/size from pocket atom coordinates."""
		x_min, y_min, z_min = float("inf"), float("inf"), float("inf")
		x_max, y_max, z_max = float("-inf"), float("-inf"), float("-inf")
		atom_count = 0

		with open(pocket_file, "r") as handle:
			for line in handle:
				if not line.startswith(("ATOM", "HETATM")):
					continue
				x, y, z = self._parse_atom_xyz(line)
				x_min = min(x_min, x)
				y_min = min(y_min, y)
				z_min = min(z_min, z)
				x_max = max(x_max, x)
				y_max = max(y_max, y)
				z_max = max(z_max, z)
				atom_count += 1

		if atom_count == 0:
			raise RuntimeError(f"No atoms found in pocket file: {pocket_file}")

		center = (
			(x_min + x_max) / 2,
			(y_min + y_max) / 2,
			(z_min + z_max) / 2,
		)
		size = (
			(x_max - x_min) + self.box_padding,
			(y_max - y_min) + self.box_padding,
			(z_max - z_min) + self.box_padding,
		)

		return {
			"atom_count": atom_count,
			"limits": {
				"x": (x_min, x_max),
				"y": (y_min, y_max),
				"z": (z_min, z_max),
			},
			"center": center,
			"size": size,
		}

	def _calculate_npts(self, size: Tuple[float, float, float]) -> Tuple[int, int, int]:
		"""Convert floating size to AutoDock npts with safeguards."""
		nx = int(size[0]) + self.autodock_margin
		ny = int(size[1]) + self.autodock_margin
		nz = int(size[2]) + self.autodock_margin

		nx = max(self.npts_min, min(nx, self.npts_max))
		ny = max(self.npts_min, min(ny, self.npts_max))
		nz = max(self.npts_min, min(nz, self.npts_max))

		return nx, ny, nz

	def _run_prepare_gpf(
		self,
		receptor_file: str,
		ligand_file: str,
		center: Tuple[float, float, float],
		npts: Tuple[int, int, int],
		output_gpf: str,
	) -> None:
		"""Generate GPF file with MGLTools prepare_gpf4.py."""
		receptor_file = os.path.abspath(receptor_file)
		ligand_file = os.path.abspath(ligand_file)
		output_gpf = os.path.abspath(output_gpf)
		center_str = f"{center[0]:.3f},{center[1]:.3f},{center[2]:.3f}"
		npts_str = f"{npts[0]},{npts[1]},{npts[2]}"

		cmd = [
			self.mgltools_python,
			self.prepare_gpf_script,
			"-l",
			ligand_file,
			"-r",
			receptor_file,
			"-o",
			output_gpf,
			"-p",
			"ligand_types=HD,A,C,OA,NA,N,SA,S,Cl,F,Br,I,P",
			"-p",
			f"npts={npts_str}",
			"-p",
			f"gridcenter={center_str}",
		]

		result = subprocess.run(
			cmd,
			capture_output=True,
			text=True,
			cwd=os.path.dirname(output_gpf),
			env=self._get_mgltools_env(),
		)

		if result.returncode != 0:
			raise RuntimeError(
				f"prepare_gpf4.py failed for {find_compound_name(receptor_file)}: "
				f"{result.stderr.strip()}"
			)

		if not os.path.isfile(output_gpf) or os.path.getsize(output_gpf) == 0:
			raise RuntimeError(f"GPF output missing or empty: {output_gpf}")

	def _write_dimensions_report(self, rows: List[Dict[str, Any]], timestamp: str) -> str:
		"""Write computed center/size report for all processed receptors."""
		report_path = os.path.join(
			self.dimensions_folder,
			f"dimensions_results_{timestamp}.txt",
		)

		with open(report_path, "w") as handle:
			handle.write("Box Dimensions Report\n")
			handle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
			handle.write("=============================================\n\n")

			for row in rows:
				limits = row.get("limits")
				center = row["center"]
				size = row.get("size")
				npts = row["npts"]
				mode = row.get("mode", "automatic")

				handle.write(f"File: {row['pocket_file']}\n")
				handle.write(f"Mode: {mode}\n")
				handle.write(f"Processed Atoms: {row['atom_count']}\n")
				if limits is not None:
					handle.write(f"X Limits: {limits['x'][0]:.3f} to {limits['x'][1]:.3f}\n")
					handle.write(f"Y Limits: {limits['y'][0]:.3f} to {limits['y'][1]:.3f}\n")
					handle.write(f"Z Limits: {limits['z'][0]:.3f} to {limits['z'][1]:.3f}\n")
				else:
					handle.write("X Limits: N/A (manual)\n")
					handle.write("Y Limits: N/A (manual)\n")
					handle.write("Z Limits: N/A (manual)\n")
				handle.write(
					f"Center of box: ({center[0]:.3f}, {center[1]:.3f}, {center[2]:.3f})\n"
				)
				if size is not None:
					handle.write(
						f"Size of box (X, Y, Z): ({size[0]:.3f}, {size[1]:.3f}, {size[2]:.3f})\n"
					)
				else:
					handle.write("Size of box (X, Y, Z): N/A (manual)\n")
				handle.write(f"NPTS (X, Y, Z): ({npts[0]}, {npts[1]}, {npts[2]})\n")
				handle.write("---------------------------------------------\n\n")

		return report_path

	def _write_error_report(self, failed: List[Dict[str, Any]], timestamp: str) -> str:
		"""Write a detailed error report file."""
		log_path = os.path.join(
			self.output_path,
			f"active_site_detection_errors_{timestamp}.txt",
		)

		with open(log_path, "w") as handle:
			handle.write("Active Site Detection Error Report\n")
			handle.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
			handle.write(f"{'='*80}\n\n")
			handle.write(f"Summary: {len(failed)} receptor(s) failed\n\n")
			handle.write(f"{'='*80}\n\n")

			for i, error in enumerate(failed, 1):
				handle.write(f"Error #{i}\n")
				handle.write(f"{'-'*80}\n")
				handle.write(f"Receptor: {error['receptor']}\n")
				handle.write(f"File: {error['file']}\n")
				handle.write(f"Error: {error['error']}\n")
				handle.write(f"\nTraceback:\n{error['traceback']}\n")
				handle.write(f"{'='*80}\n\n")

		return log_path

	def _process_single(self, receptor_file: str, ligand_file: str) -> Dict[str, Any]:
		"""Process one receptor end-to-end."""
		receptor_name = find_compound_name(receptor_file)

		if self.is_manual_mode:
			pocket_file = "manual"
			center = self.manual_center
			npts = self.manual_npts
			if center is None or npts is None:
				raise RuntimeError("Manual mode is enabled but center/npts were not set")
			box_data = {
				"atom_count": 0,
				"limits": None,
				"center": center,
				"size": None,
			}
		else:
			pocket_file = self._run_fpocket(receptor_file)
			box_data = self._calculate_box(pocket_file)
			npts = self._calculate_npts(box_data["size"])

		out_gpf = create_out_file(self.receptor_path, f"{receptor_name}.gpf")
		self._run_prepare_gpf(
			receptor_file=receptor_file,
			ligand_file=ligand_file,
			center=box_data["center"],
			npts=npts,
			output_gpf=out_gpf,
		)

		return {
			"receptor": receptor_name,
			"receptor_file": receptor_file,
			"pocket_file": os.path.basename(pocket_file),
			"gpf_file": out_gpf,
			"atom_count": box_data["atom_count"],
			"limits": box_data["limits"],
			"center": box_data["center"],
			"size": box_data["size"],
			"npts": npts,
			"mode": "manual" if self.is_manual_mode else "automatic",
		}

	def prepare(self, n_workers: Optional[int] = None) -> Dict[str, int]:
		"""Run active site detection and GPF generation for all receptors.

		Args:
			n_workers: Local worker count (None = auto)

		Returns:
			Dictionary with statistics: {'successful': int, 'failed': int}
		"""
		self._validate_dependencies()

		if not self.is_manual_mode:
			create_folder(self.pocket_folder)
		create_folder(self.dimensions_folder)

		receptors = self._collect_receptors()
		if not receptors:
			print(f"No receptor .pdbqt files found in {self.receptor_path}")
			return {"successful": 0, "failed": 0}

		ligand_file = self._select_reference_ligand()

		shard_cfg = self._get_shard_config()
		total_files = len(receptors)
		if shard_cfg:
			shard_index, shard_count = shard_cfg
			receptors = self._select_shard_files(receptors, shard_index, shard_count)
			print(
				f"SLURM sharding enabled: shard {shard_index + 1}/{shard_count} "
				f"processing {len(receptors)}/{total_files} receptor(s)"
			)
			if not receptors:
				print("No receptors assigned to this shard.")
				return {"successful": 0, "failed": 0}

		if n_workers is None:
			slurm_cpus = os.getenv("SLURM_CPUS_PER_TASK")
			if slurm_cpus and slurm_cpus.isdigit():
				n_workers = int(slurm_cpus)
			else:
				n_workers = cpu_count()

		n_workers = max(1, min(n_workers, len(receptors)))

		successful_rows: List[Dict[str, Any]] = []
		failed: List[Dict[str, Any]] = []
		timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

		print(
			f"\nDetecting active sites for {len(receptors)} receptor(s) "
			f"using {n_workers} worker(s)...\n"
		)
		if self.is_manual_mode:
			print(
				"Manual grid mode enabled: using provided center "
				f"{self.manual_center} and npts {self.manual_npts}"
			)

		if n_workers == 1:
			for receptor_file in tqdm(receptors, desc="Progress", unit="receptor", ncols=80):
				receptor_name = find_compound_name(receptor_file)
				try:
					result = self._process_single(receptor_file, ligand_file)
					successful_rows.append(result)
					logger.info(f"✓ Active site prepared for {receptor_name}")
				except Exception as e:
					failed.append(
						{
							"receptor": receptor_name,
							"file": receptor_file,
							"error": str(e),
							"traceback": traceback.format_exc(),
						}
					)
					logger.error(f"Failed {receptor_name}: {e}")
		else:
			with ThreadPoolExecutor(max_workers=n_workers) as executor:
				future_map = {
					executor.submit(self._process_single, receptor_file, ligand_file): receptor_file
					for receptor_file in receptors
				}

				for future in tqdm(
					as_completed(future_map),
					total=len(future_map),
					desc="Progress",
					unit="receptor",
					ncols=80,
				):
					receptor_file = future_map[future]
					receptor_name = find_compound_name(receptor_file)
					try:
						result = future.result()
						successful_rows.append(result)
						logger.info(f"✓ Active site prepared for {receptor_name}")
					except Exception as e:
						failed.append(
							{
								"receptor": receptor_name,
								"file": receptor_file,
								"error": str(e),
								"traceback": traceback.format_exc(),
							}
						)
						logger.error(f"Failed {receptor_name}: {e}")

		print(f"\n✓ Successfully processed: {len(successful_rows)}/{len(receptors)} receptors")

		if successful_rows:
			dimensions_report = self._write_dimensions_report(successful_rows, timestamp)
			print(f"Dimensions report: {dimensions_report}")

		if failed:
			error_report = self._write_error_report(failed, timestamp)
			print(f"Failed: {len(failed)} - See: {error_report}")

		print()
		return {"successful": len(successful_rows), "failed": len(failed)}
