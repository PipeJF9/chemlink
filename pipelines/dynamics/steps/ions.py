import subprocess
import os
from tqdm import tqdm

from ..logger import get_step_logger

class IonsStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.solvated_gro = os.path.join(self.config["work_dir"], "solvated.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        self.ions_mdp = os.path.join(self.config["work_dir"], "ions.mdp")
        self.ions_tpr = os.path.join(self.config["work_dir"], "ions.tpr")
        self.ionized_gro = os.path.join(self.config["work_dir"], "ionized.gro")
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def _create_ions_mdp(self):
        mdp_content = (
            "integrator  = steep\n"
            "emtol       = 1000.0\n"
            "emstep      = 0.01\n"
            "nsteps      = 50000\n"
            "nstlist     = 1\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "coulombtype = cutoff\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "pbc         = xyz\n"
        )
        with open(self.ions_mdp, "w") as f:
            f.write(mdp_content)

    def run(self):      
        self._create_ions_mdp()
        # Execution 1: Prepare TPR
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.ions_mdp,
            "-c", self.solvated_gro,
            "-p", self.topol,
            "-o", self.ions_tpr,
            "-maxwarn", "10"
        ]
        # Execution 2: Add Ions
        genion_cmd = [
            self.gmx_bin, "genion",
            "-s", self.ions_tpr,
            "-o", self.ionized_gro,
            "-p", self.topol,
            "-pname", "NA",
            "-nname", "CL",
            "-neutral"
        ]

        with tqdm(total=3, desc="  └─ System Neutralization", leave=False) as pbar:
            try:
                subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)
                pbar.update(1)

                process = subprocess.Popen(genion_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(input="SOL\n")# Automatically select 'SOL' group for replacement
                if process.returncode != 0:
                    self.logger.error("genion execution failed:\n%s", stderr)
                    raise subprocess.CalledProcessError(process.returncode, genion_cmd, stderr)
                pbar.update(1)
                if not os.path.exists(self.ionized_gro):
                    raise FileNotFoundError("GROMACS finished, but ionized file was not found.")
                pbar.update(1)
                
            except subprocess.CalledProcessError as e:
                self.logger.exception("Neutralization Error:\n%s", e.stderr)
                raise e
            except Exception as e:
                self.logger.exception("Unexpected Error in IonsStep")
                raise e