import os
import shutil
from tqdm import tqdm
from pipelines.dynamics.utils import convert_pdbqt_to_pdb

from ..logger import get_step_logger
from utils.retry import SubprocessError, run_subprocess

_ACPYPE_TIMEOUT = 600


class LigandTopologyStep:
    def __init__(self, config, gmx_bin):
        self.config        = config
        self.gmx_bin       = gmx_bin
        self.work_dir      = self.config["work_dir"]
        self.ligand_pdb    = os.path.abspath(self.config["ligand_pdb"])
        self.protein_gro   = os.path.join(self.work_dir, "processed.gro")
        self.topol_file    = os.path.join(self.work_dir, "topol.top")
        self.charge        = self.config.get("ligand_charge", 0)
        self.acpype_workdir = os.path.join(self.work_dir, "acpype_work")
        self.logger        = get_step_logger(
            __name__, os.path.join(self.work_dir, "simulation.log")
        )

    def run(self) -> None:
        with tqdm(total=5, desc="  └─ Ligand Topology Generation", leave=False) as pbar:
            try:
                os.makedirs(self.acpype_workdir, exist_ok=True)
                internal_pdb = os.path.join(self.acpype_workdir, "ligand.pdb")

                # Format conversion: PDBQT → PDB or plain copy.
                if self.ligand_pdb.lower().endswith(".pdbqt"):
                    if not convert_pdbqt_to_pdb(self.ligand_pdb, internal_pdb):
                        self.logger.error(
                            "Failed to convert %s to PDB using OpenBabel.", self.ligand_pdb
                        )
                        raise RuntimeError("Failed to convert ligand PDBQT to PDB.")
                else:
                    try:
                        shutil.copy(self.ligand_pdb, internal_pdb)
                    except FileNotFoundError:
                        self.logger.error("Source ligand file not found: %s", self.ligand_pdb)
                        raise
                pbar.update(1)

                if not os.path.exists(internal_pdb):
                    raise FileNotFoundError(
                        f"Expected internal PDB not found after conversion/copy: {internal_pdb}"
                    )
                with open(internal_pdb) as fh:
                    if not any(l.startswith(("ATOM", "HETATM")) for l in fh):
                        raise RuntimeError(
                            f"{internal_pdb} has no atom records. "
                            "Check the original PDBQT file."
                        )

                # Run ACPYPE for GAFF2 parameters.
                run_subprocess(
                    [
                        "acpype", "-i", "ligand.pdb",
                        "-b", "LIG", "-c", "bcc",
                        "-n", str(self.charge), "-a", "gaff2",
                    ],
                    timeout=_ACPYPE_TIMEOUT,
                    retries=1,
                    cwd=self.acpype_workdir,
                    logger=self.logger,
                )
                pbar.update(1)

                acpype_out_folder = next(
                    (
                        os.path.join(self.acpype_workdir, d)
                        for d in os.listdir(self.acpype_workdir)
                        if d.endswith(".acpype")
                    ),
                    None,
                )
                if not acpype_out_folder:
                    raise FileNotFoundError("ACPYPE output directory was not found.")

                acpype_gro = os.path.join(acpype_out_folder, "LIG_GMX.gro")
                acpype_itp = os.path.join(acpype_out_folder, "LIG_GMX.itp")

                self._clean_ligand_itp(acpype_itp)
                pbar.update(1)
                self._merge_gro(self.protein_gro, acpype_gro)
                pbar.update(1)
                self._patch_topology(acpype_itp)
                pbar.update(1)

            except SubprocessError as exc:
                self.logger.error("ACPYPE failed:\n%s", exc.stderr)
                raise RuntimeError(str(exc)) from exc
            except Exception:
                self.logger.exception("Unexpected error in LigandTopologyStep")
                raise

    def _clean_ligand_itp(self, itp_path: str) -> None:
        with open(itp_path) as fh:
            lines = fh.readlines()
        clean, skip = [], False
        for line in lines:
            if "[ atomtypes ]" in line:
                skip = True
                continue
            if skip and line.startswith("["):
                skip = False
            if not skip:
                clean.append(line)
        with open(os.path.join(self.work_dir, "ligand.itp"), "w") as fh:
            fh.writelines(clean)

    def _merge_gro(self, prot_gro: str, lig_gro: str) -> None:
        with open(prot_gro) as fh:
            p_lines = fh.readlines()
        with open(lig_gro) as fh:
            l_lines = fh.readlines()
        p_atoms = p_lines[2:-1]
        l_atoms = l_lines[2:-1]
        box     = p_lines[-1]
        total   = len(p_atoms) + len(l_atoms)
        with open(os.path.join(self.work_dir, "complex.gro"), "w") as fh:
            fh.write("Complex System\n")
            fh.write(f"{total}\n")
            fh.writelines(p_atoms)
            fh.writelines(l_atoms)
            fh.write(box)

    def _patch_topology(self, original_itp: str) -> None:
        atomtypes: list = []
        with open(original_itp) as fh:
            capture = False
            for line in fh:
                if "[ atomtypes ]" in line:
                    capture = True
                    atomtypes.append(line)
                    continue
                if capture and line.startswith("["):
                    break
                if capture:
                    atomtypes.append(line)

        with open(self.topol_file) as fh:
            top_lines = fh.readlines()

        new_top: list = []
        types_inserted = itp_included = False

        for line in top_lines:
            if "forcefield.itp" in line and not types_inserted:
                new_top.append(line)
                new_top.append("\n; Ligand-specific atomtypes (GAFF2)\n")
                new_top.extend(atomtypes)
                new_top.append("\n")
                types_inserted = True
                continue
            if "[ molecules ]" in line and not itp_included:
                new_top.append("; Include ligand topology\n")
                new_top.append('#include "ligand.itp"\n\n')
                new_top.append(line)
                itp_included = True
                continue
            if line.strip() == "LIG                1":
                continue
            new_top.append(line)

        if not any("LIG" in l for l in top_lines[-5:]):
            new_top.append("LIG                1\n")
        with open(self.topol_file, "w") as fh:
            fh.writelines(new_top)
