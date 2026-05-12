import os
from tqdm import tqdm
from pdbfixer import PDBFixer
from openmm.app import PDBFile

from ..logger import get_step_logger
from utils.retry import SubprocessError, run_subprocess

_PDB2GMX_TIMEOUT = 300


class TopologyStep:
    def __init__(self, config, gmx_bin):
        self.config        = config
        self.gmx_bin       = gmx_bin
        self.pdb_input_abs = os.path.abspath(self.config["pdb_input"])
        self.output_gro    = "processed.gro"
        self.logger        = get_step_logger(
            __name__, os.path.join(self.config["work_dir"], "simulation.log")
        )

    def _repair_pdb(self, input_pdb: str, output_pdb_path: str) -> bool:
        with tqdm(total=4, desc="  └─ Repairing Structure", leave=False) as pbar:
            try:
                fixer = PDBFixer(filename=input_pdb)
                pbar.update(1)
                fixer.findMissingResidues()
                pbar.update(1)
                fixer.findMissingAtoms()
                fixer.addMissingAtoms()
                pbar.update(1)
                fixer.addMissingHydrogens(7.0)
                with open(output_pdb_path, "w") as fh:
                    PDBFile.writeFile(fixer.topology, fixer.positions, fh)
                pbar.update(1)
                return True
            except Exception:
                self.logger.exception("PDBFixer failed")
                return False

    def _build_pdb2gmx_cmd(self, pdb_path: str) -> list:
        sim_type = self.config.get("sim_type")
        base = [
            self.gmx_bin, "pdb2gmx",
            "-f", pdb_path,
            "-o", self.output_gro,
            "-water", "tip3p",
            "-ignh",
        ]
        if sim_type in ["3", "4", "5", "6"]:
            return base + ["-ff", "amber99sb-ildn", "-chainsep", "id"]
        return base + ["-ff", "amber03"]

    def run(self) -> None:
        work_dir         = self.config["work_dir"]
        repaired_pdb_abs = os.path.join(os.path.abspath(work_dir), "complex_repaired.pdb")
        cmd              = self._build_pdb2gmx_cmd(self.pdb_input_abs)

        try:
            run_subprocess(
                cmd,
                timeout=_PDB2GMX_TIMEOUT,
                retries=1,
                cwd=work_dir,
                logger=self.logger,
            )
        except SubprocessError as exc:
            # Attempt PDBFixer repair when the error is atom-related.
            if "not found in the input file" in exc.stderr or "atom" in exc.stderr:
                if self._repair_pdb(self.pdb_input_abs, repaired_pdb_abs):
                    repaired_cmd = self._build_pdb2gmx_cmd("complex_repaired.pdb")
                    try:
                        run_subprocess(
                            repaired_cmd,
                            timeout=_PDB2GMX_TIMEOUT,
                            retries=1,
                            cwd=work_dir,
                            logger=self.logger,
                        )
                        return
                    except SubprocessError as exc2:
                        self.logger.error("Persistent error after repair:\n%s", exc2.stderr)
                        raise RuntimeError(str(exc2)) from exc2
            self.logger.error("pdb2gmx failed:\n%s", exc.stderr)
            raise RuntimeError(str(exc)) from exc
