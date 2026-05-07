import subprocess
import os
from tqdm import tqdm

from ..logger import get_step_logger

class SolvationStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        gro_name = self.config.get("current_gro", "processed.gro")
        self.input_gro = os.path.join(self.config["work_dir"], gro_name)
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        self.boxed_gro = os.path.join(self.config["work_dir"], "boxed.gro")
        self.solvated_gro = os.path.join(self.config["work_dir"], "solvated.gro")
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def run(self):
        # ACTION 1: Define box with editconf
        editconf_cmd = [
            self.gmx_bin, "editconf",
            "-f", self.input_gro,
            "-o", self.boxed_gro,
            "-bt", "cubic",
            "-d", "1.0",
            "-c"
        ]
        # ACTION 2: Add water with solvate
        solvate_cmd = [
            self.gmx_bin, "solvate",
            "-cp", self.boxed_gro,
            "-cs", "spc216.gro",
            "-o", self.solvated_gro,
            "-p", self.topol
        ]
        with tqdm(total=2, desc="  └─ System Solvation", leave=False) as pbar:
            try:
                subprocess.run(editconf_cmd, check=True, capture_output=True, text=True)
                pbar.update(1)
                subprocess.run(solvate_cmd, check=True, capture_output=True, text=True)
                pbar.update(1)
                if not os.path.exists(self.solvated_gro):
                    raise FileNotFoundError("GROMACS execution finished, but solvated file was not found.")
            except subprocess.CalledProcessError as e:
                self.logger.exception("Unexpected error in SolvationStep")
                raise e