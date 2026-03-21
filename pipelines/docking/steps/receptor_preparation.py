"""Receptor preparation pipeline step for molecular docking."""

import os
import subprocess
import traceback
from datetime import datetime
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional, Dict, List, Any
from tqdm import tqdm

try:
    from openbabel import openbabel as ob
except ImportError:
    import openbabel as ob

from chemlink.storage.file_manager import (
    create_folder, list_files_in_directory,
    find_compound_name, create_out_file
)
from chemlink.utils.logger import setup_logger

logger = setup_logger(__name__)


def _prepare_receptor_worker(task: Dict[str, Any]) -> Dict[str, Any]:
    """Worker for process-based receptor preparation.

    Args:
        task: Task configuration and receptor file path

    Returns:
        Dictionary with task result metadata
    """
    receptor_file = task['receptor_file']
    receptor_name = find_compound_name(receptor_file)

    prep = ReceptorPreparation(
        input_path=task['input_path'],
        output_path=task['output_path'],
        mgltools_path=task['mgltools_path'],
        remove_water=task['remove_water'],
        remove_ligands=task['remove_ligands'],
        remove_ions=task['remove_ions'],
        keep_clean_pdb=task['keep_clean_pdb']
    )

    try:
        out_pdbqt = prep._prepare_single(receptor_file)
        return {
            'receptor': receptor_name,
            'file': receptor_file,
            'success': True,
            'output': out_pdbqt,
            'error': None,
            'traceback': None
        }
    except Exception as e:
        return {
            'receptor': receptor_name,
            'file': receptor_file,
            'success': False,
            'output': None,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


class ReceptorPreparation:
    """Batch receptor preparation for molecular docking.
    
    This class orchestrates the preparation of protein receptor files,
    handling cleaning (water/ligand/ion removal) and PDBQT conversion via MGLTools.
    """
    
    # Standard amino acid residues to keep
    PROTEIN_RESIDUES = {
        'ALA', 'ARG', 'ASN', 'ASP', 'CYS', 'GLN', 'GLU', 'GLY',
        'HIS', 'ILE', 'LEU', 'LYS', 'MET', 'PHE', 'PRO', 'SER',
        'THR', 'TRP', 'TYR', 'VAL',
        'HID', 'HIE', 'HIP', 'HSE', 'HSD', 'HSP',  # Histidine variants
        'CYX', 'CYM',  # Cysteine variants
        'ACE', 'NME'   # Capping groups
    }
    
    DEFAULT_MGLTOOLS_PATH = "/opt/mgltools"
    
    def __init__(
        self,
        input_path: str,
        output_path: str,
        mgltools_path: Optional[str] = None,
        remove_water: bool = True,
        remove_ligands: bool = True,
        remove_ions: bool = True,
        keep_clean_pdb: bool = True
    ):
        """Initialize receptor preparation pipeline.
        
        Args:
            input_path: Directory containing input receptor PDB files
            output_path: Base directory for output files
            mgltools_path: Path to MGLTools installation (default: /opt/mgltools)
            remove_water: Remove water molecules from receptor
            remove_ligands: Remove ligand molecules from receptor
            remove_ions: Remove ions from receptor
            keep_clean_pdb: Keep intermediate cleaned PDB files
        """
        self.input_path = input_path
        self.output_path = output_path
        self.mol = ob.OBMol()
        
        # Cleaning options
        self.remove_water = remove_water
        self.remove_ligands = remove_ligands
        self.remove_ions = remove_ions
        self.keep_clean_pdb = keep_clean_pdb
        
        # MGLTools configuration
        self.mgltools_path = mgltools_path or self.DEFAULT_MGLTOOLS_PATH
        self._setup_mgltools_paths()
    
    def _setup_mgltools_paths(self) -> None:
        """Configure paths to MGLTools pythonsh and prepare_receptor4.py."""
        self.mgltools_python = os.path.join(self.mgltools_path, "bin", "pythonsh")
        self.prepare_receptor_script = os.path.join(
            self.mgltools_path,
            "MGLToolsPckgs",
            "AutoDockTools",
            "Utilities24",
            "prepare_receptor4.py"
        )
    
    def _validate_mgltools(self) -> None:
        """Ensure MGLTools and prepare_receptor4.py exist.
        
        Raises:
            FileNotFoundError: If MGLTools components are not found
        """
        if not os.path.isfile(self.mgltools_python):
            raise FileNotFoundError(
                f"MGLTools Python not found: {self.mgltools_python}"
            )
        if not os.path.isfile(self.prepare_receptor_script):
            raise FileNotFoundError(
                f"prepare_receptor4.py not found: {self.prepare_receptor_script}"
            )
    
    def _get_mgltools_env(self) -> Dict[str, str]:
        """Return environment dict for running MGLTools.
        
        Returns:
            Environment variables configured for MGLTools execution
        """
        env = os.environ.copy()
        env['MGL_ROOT'] = self.mgltools_path
        env['PYTHONPATH'] = os.path.join(
            self.mgltools_path, "MGLToolsPckgs"
        ) + ":" + env.get('PYTHONPATH', '')
        env['LD_LIBRARY_PATH'] = os.path.join(
            self.mgltools_path, "lib"
        ) + ":" + env.get('LD_LIBRARY_PATH', '')
        return env
    
    def _read_receptor(self, receptor_file: str) -> None:
        """Read a receptor PDB into self.mol using OpenBabel.
        
        Args:
            receptor_file: Path to receptor PDB file
            
        Raises:
            RuntimeError: If receptor cannot be read
        """
        # Check if file exists first
        if not os.path.exists(receptor_file):
            abs_path = os.path.abspath(receptor_file)
            cwd = os.getcwd()
            
            error_msg = f"Receptor file not found: {receptor_file}\n"
            error_msg += f"  Absolute path attempted: {abs_path}\n"
            error_msg += f"  Current working directory: {cwd}\n"
            
            # Check if file exists with different path
            basename = os.path.basename(receptor_file)
            possible_paths = [
                f"data/input/receptors/{basename}",
                f"./data/input/receptors/{basename}",
                f"../data/input/receptors/{basename}"
            ]
            
            for possible in possible_paths:
                if os.path.exists(possible):
                    error_msg += f"  ✓ File found at: {possible}\n"
                    error_msg += f"  Use this path instead!\n"
                    break
            
            raise RuntimeError(error_msg.strip())
        
        # Check if file is readable
        if not os.access(receptor_file, os.R_OK):
            raise RuntimeError(
                f"Cannot read receptor file (permission denied): {receptor_file}\n"
                f"  Try: chmod +r {receptor_file}"
            )
        
        # Now try to read with OpenBabel
        self.mol = ob.OBMol()
        conv = ob.OBConversion()
        conv.SetInFormat('pdb')
        
        logger.info(f"Reading receptor: {receptor_file}")
        
        if not conv.ReadFile(self.mol, receptor_file):
            # Get file size for diagnostics
            file_size = os.path.getsize(receptor_file)
            
            error_msg = f"OpenBabel failed to read receptor: {receptor_file}\n"
            error_msg += f"  File exists: Yes\n"
            error_msg += f"  File size: {file_size} bytes\n"
            error_msg += f"  File readable: {os.access(receptor_file, os.R_OK)}\n"
            
            # Try to read first line
            try:
                with open(receptor_file, 'r') as f:
                    first_line = f.readline().strip()
                    error_msg += f"  First line: {first_line[:50]}...\n"
            except Exception as e:
                error_msg += f"  Cannot read file content: {e}\n"
            
            error_msg += f"  This may indicate a corrupted or malformed PDB file"
            
            raise RuntimeError(error_msg.strip())
        
        num_atoms = self.mol.NumAtoms()
        
        if num_atoms == 0:
            raise RuntimeError(
                f"Read 0 atoms from {receptor_file}. File may be empty or corrupted."
            )
        
        logger.info(f"Successfully read {num_atoms:,} atoms from {receptor_file}")
    
    def _get_residue_summary(self) -> Dict[str, int]:
        """Return a dict {res_name: atom_count} for the current receptor.
        
        Returns:
            Dictionary mapping residue names to atom counts
        """
        residues = {}
        for atom in ob.OBMolAtomIter(self.mol):
            res = atom.GetResidue()
            if res:
                name = res.GetName().strip().upper()
                residues[name] = residues.get(name, 0) + 1
        return residues
    
    def _identify_atoms_to_remove(self) -> tuple:
        """Identify atoms to remove as non-protein (water, ions, ligands).
        
        Returns:
            Tuple of (atoms_to_remove, removed_info) where atoms_to_remove is a list
            of atom indices and removed_info is a dict with removal statistics
        """
        atoms_to_remove = []
        removed_info = {'water': 0, 'ligand': 0, 'ion': 0, 'other': 0}
        
        for atom in ob.OBMolAtomIter(self.mol):
            res = atom.GetResidue()
            
            if not res:
                atoms_to_remove.append(atom.GetIdx())
                removed_info['other'] += 1
                continue
            
            name = res.GetName().strip().upper()
            
            # Keep protein residues
            if name in self.PROTEIN_RESIDUES:
                continue
            
            # Water molecules
            if name in {'HOH', 'WAT', 'H2O', 'DOD'}:
                if self.remove_water:
                    atoms_to_remove.append(atom.GetIdx())
                    removed_info['water'] += 1
                continue
            
            # Ions
            if name in {'NA', 'CL', 'MG', 'CA', 'ZN', 'FE', 'K', 'MN', 'CU'}:
                if self.remove_ions:
                    atoms_to_remove.append(atom.GetIdx())
                    removed_info['ion'] += 1
                continue
            
            # Everything else (ligands, cofactors, etc.)
            if self.remove_ligands:
                atoms_to_remove.append(atom.GetIdx())
                removed_info['ligand'] += 1
        
        return atoms_to_remove, removed_info
    
    def _remove_non_protein(self) -> Dict[str, int]:
        """Remove all non-protein atoms from self.mol.
        
        Returns:
            Dictionary with removal statistics
        """
        atoms_to_remove, info = self._identify_atoms_to_remove()
        
        # Delete atoms in reverse order to maintain valid indices
        for idx in sorted(atoms_to_remove, reverse=True):
            atom = self.mol.GetAtom(idx)
            if atom:
                self.mol.DeleteAtom(atom)
        
        # Fix bonds after deletion
        self.mol.PerceiveBondOrders()
        
        logger.info(
            f"Removed: {info['water']} water, {info['ligand']} ligand, "
            f"{info['ion']} ion, {info['other']} other atoms"
        )
        logger.info(f"Remaining atoms: {self.mol.NumAtoms()}")
        
        return info
    
    def _save_clean_receptor(self, output_file: str) -> None:
        """Write cleaned receptor (self.mol) as PDB.
        
        Args:
            output_file: Path for output PDB file
            
        Raises:
            RuntimeError: If receptor cannot be written
        """
        conv = ob.OBConversion()
        conv.SetOutFormat('pdb')
        
        if not conv.WriteFile(self.mol, output_file):
            raise RuntimeError(f"Failed to write receptor: {output_file}")
    
    def _pre_prepare(self, receptor_file: str, output_clean_pdb: str) -> None:
        """Clean receptor: read, remove non-protein, write clean PDB.
        
        Args:
            receptor_file: Input receptor PDB file
            output_clean_pdb: Output cleaned PDB file
        """
        self._read_receptor(receptor_file)
        residues = self._get_residue_summary()
        logger.info(f"Residues found: {residues}")
        
        self._remove_non_protein()
        self._save_clean_receptor(output_clean_pdb)
        logger.info(f"Saved cleaned receptor to {output_clean_pdb}")
    
    def _run_prepare_receptor(self, input_pdb: str, output_pdbqt: str) -> None:
        """Run MGLTools prepare_receptor4.py on a cleaned receptor PDB.
        
        Args:
            input_pdb: Input cleaned PDB file
            output_pdbqt: Output PDBQT file
            
        Raises:
            RuntimeError: If MGLTools preparation fails
        """
        self._validate_mgltools()
        
        cmd = [
            self.mgltools_python,
            self.prepare_receptor_script,
            '-r', input_pdb,
            '-o', output_pdbqt,
            '-A', 'hydrogens',
            '-U', 'nphs_lps_waters_nonstdres'
        ]
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=self._get_mgltools_env(),
                check=True,
                timeout=300
            )
            logger.info(f"MGLTools success: {result.stdout}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"MGLTools failed: {e}\nSTDERR: {e.stderr}")
            raise RuntimeError(
                f"prepare_receptor4.py failed with code {e.returncode}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("MGLTools timed out after 300s")
        
        # Verify output
        if not os.path.isfile(output_pdbqt) or os.path.getsize(output_pdbqt) == 0:
            raise RuntimeError(f"Output PDBQT empty or missing: {output_pdbqt}")
        
        logger.info(f"Generated PDBQT: {output_pdbqt}")
    
    def _prepare_single(self, receptor_file: str) -> str:
        """Run full pipeline (clean + MGLTools) for a single receptor.
        
        Args:
            receptor_file: Path to input receptor PDB file
            
        Returns:
            Path to output PDBQT file
        """
        base = find_compound_name(receptor_file)
        safe_base = base.replace(' ', '_').replace(',', '_')
        
        # Step 1: Clean receptor
        clean_pdb = create_out_file(
            f'{self.output_path}/clean_receptors',
            f'{safe_base}_clean.pdb'
        )
        self._pre_prepare(receptor_file, clean_pdb)
        
        # Step 2: Convert to PDBQT with MGLTools
        out_pdbqt = create_out_file(
            f'{self.output_path}/prepared_receptors_pdbqt',
            f'{safe_base}_clean.pdbqt'
        )
        self._run_prepare_receptor(clean_pdb, out_pdbqt)
        
        # Clean up intermediate file if requested
        if not self.keep_clean_pdb and os.path.exists(clean_pdb):
            os.remove(clean_pdb)
            logger.debug(f"Removed intermediate: {clean_pdb}")
        
        return out_pdbqt
    
    def _write_error_report(self, failed: List[dict], timestamp: str) -> str:
        """Write detailed error report to file.
        
        Args:
            failed: List of error dictionaries
            timestamp: Timestamp string for filename
            
        Returns:
            Path to error log file
        """
        log_path = os.path.join(
            self.output_path,
            f'receptor_preparation_errors_{timestamp}.txt'
        )
        
        with open(log_path, 'w') as f:
            f.write("Receptor Preparation Error Report\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Summary: {len(failed)} receptor(s) failed to prepare\n\n")
            f.write(f"{'='*80}\n\n")
            
            for i, error in enumerate(failed, 1):
                f.write(f"Error #{i}\n")
                f.write(f"{'-'*80}\n")
                f.write(f"Receptor: {error['receptor']}\n")
                f.write(f"File: {error['file']}\n")
                f.write(f"Error: {error['error']}\n")
                f.write(f"\nTraceback:\n{error['traceback']}\n")
                f.write(f"{'='*80}\n\n")
        
        return log_path

    def _get_shard_config(self) -> Optional[tuple]:
        """Return (shard_index, shard_count) from environment if configured.

        Supports both generic variables and SLURM array variables:
        - CHEMLINK_SHARD_INDEX / CHEMLINK_SHARD_COUNT
        - SLURM_ARRAY_TASK_ID / SLURM_ARRAY_TASK_COUNT
        - SLURM_ARRAY_TASK_MIN / SLURM_ARRAY_TASK_MAX (fallback for count)

        Returns:
            Tuple (index, count) using zero-based index, or None when disabled.

        Raises:
            RuntimeError: If shard values are invalid
        """
        shard_index_env = os.getenv('CHEMLINK_SHARD_INDEX')
        shard_count_env = os.getenv('CHEMLINK_SHARD_COUNT')

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
        elif os.getenv('SLURM_ARRAY_TASK_ID') is not None:
            try:
                slurm_task_id = int(os.getenv('SLURM_ARRAY_TASK_ID', '0'))
            except ValueError as exc:
                raise RuntimeError("SLURM_ARRAY_TASK_ID must be an integer") from exc

            slurm_task_count = os.getenv('SLURM_ARRAY_TASK_COUNT')
            slurm_task_min = os.getenv('SLURM_ARRAY_TASK_MIN')
            slurm_task_max = os.getenv('SLURM_ARRAY_TASK_MAX')

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
        """Return the subset of files assigned to a shard.

        Uses round-robin assignment for balanced distribution.
        """
        return files[shard_index::shard_count]

    def _build_worker_task(self, receptor_file: str) -> Dict[str, Any]:
        """Build worker task payload for process-based execution."""
        return {
            'receptor_file': receptor_file,
            'input_path': self.input_path,
            'output_path': self.output_path,
            'mgltools_path': self.mgltools_path,
            'remove_water': self.remove_water,
            'remove_ligands': self.remove_ligands,
            'remove_ions': self.remove_ions,
            'keep_clean_pdb': self.keep_clean_pdb
        }
    
    def prepare(self, n_workers: Optional[int] = None) -> Dict[str, int]:
        """Prepare all receptors found in input directory.

        Args:
            n_workers: Number of local process workers (None = auto)
        
        Returns:
            Dictionary with statistics: {'successful': int, 'failed': int}
        """
        # Setup output directories
        if self.keep_clean_pdb:
            create_folder(f'{self.output_path}/clean_receptors')
        create_folder(f'{self.output_path}/prepared_receptors_pdbqt')
        
        # Collect receptor files
        files = sorted(list_files_in_directory(self.input_path, ['*.pdb']))
        
        if not files:
            print(f'No receptor files found in {self.input_path}')
            return {'successful': 0, 'failed': 0}

        shard_cfg = self._get_shard_config()
        total_files = len(files)
        if shard_cfg:
            shard_index, shard_count = shard_cfg
            files = self._select_shard_files(files, shard_index, shard_count)

            print(
                f"SLURM sharding enabled: shard {shard_index + 1}/{shard_count} "
                f"processing {len(files)}/{total_files} receptor(s)"
            )

            if not files:
                print("No receptors assigned to this shard.")
                return {'successful': 0, 'failed': 0}

        # Determine worker count
        if n_workers is None:
            slurm_cpus = os.getenv('SLURM_CPUS_PER_TASK')
            if slurm_cpus and slurm_cpus.isdigit():
                n_workers = int(slurm_cpus)
            else:
                n_workers = cpu_count()

        n_workers = max(1, min(n_workers, len(files)))
        
        # Track results
        successful = []
        failed = []
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\nPreparing {len(files)} receptor(s) using {n_workers} worker(s)...\n")

        if n_workers == 1:
            # Sequential processing
            for f in tqdm(files, desc="Progress", unit="receptor", ncols=80):
                receptor_name = find_compound_name(f)
                try:
                    out_pdbqt = self._prepare_single(f)
                    successful.append(receptor_name)
                    logger.info(f"✓ Prepared {receptor_name}")
                except Exception as e:
                    error_details = {
                        'receptor': receptor_name,
                        'file': f,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                    failed.append(error_details)
                    error_msg = str(e)
                    if "not found" in error_msg.lower() or "File found at:" in error_msg:
                        print(f"\n{'='*60}")
                        print(f"ERROR: Failed {receptor_name}")
                        print(f"{'='*60}")
                        print(error_msg)
                        print(f"{'='*60}\n")
                    else:
                        logger.error(f"Failed {receptor_name}: {e}")
        else:
            # Process-based parallel processing (safe isolation per receptor)
            tasks = [self._build_worker_task(receptor_file) for receptor_file in files]

            with ProcessPoolExecutor(max_workers=n_workers) as executor:
                futures = [executor.submit(_prepare_receptor_worker, task) for task in tasks]
                for future in tqdm(
                    as_completed(futures),
                    total=len(futures),
                    desc="Progress",
                    unit="receptor",
                    ncols=80
                ):
                    result = future.result()
                    receptor_name = result['receptor']
                    if result['success']:
                        successful.append(receptor_name)
                        logger.info(f"✓ Prepared {receptor_name}")
                    else:
                        error_details = {
                            'receptor': result['receptor'],
                            'file': result['file'],
                            'error': result['error'],
                            'traceback': result['traceback']
                        }
                        failed.append(error_details)
                        error_msg = result['error'] or ''
                        if "not found" in error_msg.lower() or "File found at:" in error_msg:
                            print(f"\n{'='*60}")
                            print(f"ERROR: Failed {receptor_name}")
                            print(f"{'='*60}")
                            print(error_msg)
                            print(f"{'='*60}\n")
                        else:
                            logger.error(f"Failed {receptor_name}: {result['error']}")
        
        # Print summary
        print(f"\nSuccessfully prepared: {len(successful)}/{len(files)} receptors")
        
        # Write error report if needed
        if failed:
            error_log = self._write_error_report(failed, timestamp)
            print(f"Failed: {len(failed)} - See: {error_log}")
        
        print()
        
        return {
            'successful': len(successful),
            'failed': len(failed)
        }


def main():
    """Command-line entry point for receptor preparation."""
    import sys
    
    if len(sys.argv) < 3:
        print(
            "Usage: python receptor_preparation.py <input_dir> <output_dir> "
            "[mgltools_path] [n_workers]"
        )
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    mgltools_path = None
    n_workers = None

    if len(sys.argv) == 4:
        # Allow third argument to be either mgltools_path or n_workers
        if sys.argv[3].isdigit():
            n_workers = int(sys.argv[3])
        else:
            mgltools_path = sys.argv[3]
    elif len(sys.argv) > 4:
        mgltools_path = sys.argv[3]
        n_workers = int(sys.argv[4])
    
    prep = ReceptorPreparation(
        input_dir,
        output_dir,
        mgltools_path=mgltools_path,
        remove_water=True,
        remove_ligands=True,
        remove_ions=True,
        keep_clean_pdb=True
    )
    
    stats = prep.prepare(n_workers=n_workers)
    
    print(f"\nFinal Statistics:")
    print(f"  Successful: {stats['successful']}")
    print(f"  Failed: {stats['failed']}")


if __name__ == '__main__':
    main()
