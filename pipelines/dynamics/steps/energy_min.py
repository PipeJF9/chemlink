import subprocess
import os
from tqdm import tqdm

from ..logger import get_step_logger

class EnergyMinStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.input_gro = os.path.join(self.config["work_dir"], "ionized.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        self.em_mdp = os.path.join(self.config["work_dir"], "em.mdp")
        self.em_tpr = os.path.join(self.config["work_dir"], "em.tpr")
        self.em_gro = os.path.join(self.config["work_dir"], "em.gro")
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def _create_em_mdp(self):
        mdp_content = (
            "integrator  = steep\n"
            "emtol       = 1000.0\n"
            "emstep      = 0.01\n"
            "nsteps      = 50000\n"
            "nstlist     = 1\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "coulombtype = PME\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "pbc         = xyz\n"
        )
        with open(self.em_mdp, "w") as f:
            f.write(mdp_content)

    def run(self):
        self._create_em_mdp()
        # 1. Prepare TPR
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.em_mdp,
            "-c", self.input_gro,
            "-p", self.topol,
            "-o", self.em_tpr,
            "-maxwarn", "10"
        ]
        # 2. Optimized Energy Minimization
        mdrun_cmd = [
            self.gmx_bin, "mdrun",
            "-v", 
            "-deffnm", "em",
            "-ntomp", str(self.config.get("threads", 8)),
            "-pin", "on",
            "-nb", "gpu",       
        ]

        with tqdm(total=2, desc="  └─ Energy Minimization", leave=False) as pbar:
            try:
                subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)
                pbar.update(1)
                subprocess.run(mdrun_cmd, check=True, capture_output=True, text=True, cwd=self.config["work_dir"])
                pbar.update(1)

                if not os.path.exists(self.em_gro):
                    raise FileNotFoundError("Minimization finished but output file was not found.")    
            except subprocess.CalledProcessError as e:
                self.logger.exception("Energy Minimization Error:\n%s", e.stderr)
                raise e
            except Exception as e:
                self.logger.exception("Unexpected Error in EnergyMinStep")
                raise e