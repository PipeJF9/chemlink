import subprocess
import os
from tqdm import tqdm

from ..logger import get_step_logger

class ProductionStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.npt_gro = os.path.join(self.config["work_dir"], "npt.gro")
        self.npt_cpt = os.path.join(self.config["work_dir"], "npt.cpt")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        self.md_mdp = os.path.join(self.config["work_dir"], "md.mdp")
        self.md_tpr = os.path.join(self.config["work_dir"], "md.tpr")
        self.output_base = "md"
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def _create_production_mdp(self):
        ns_time = float(self.config["ns_time"])
        nsteps = int((ns_time * 1000) / 0.002)
        
        mdp_content = f"""
        integrator          = md
        nsteps              = {nsteps}
        dt                  = 0.002
        nstxout             = 0
        nstvout             = 0
        nstfout             = 0
        nstenergy           = 5000
        nstlog              = 5000
        nstxout-compressed  = 5000
        compressed-x-grps   = System
        continuation        = yes
        constraint_algorithm = lincs
        constraints         = h-bonds
        cutoff-scheme       = Verlet
        ns_type             = grid
        nstlist             = 10
        rcoulomb            = 1.0
        rvdw                = 1.0
        coulombtype         = PME
        pme_order           = 4
        fourierspacing      = 0.16
        tcoupl              = V-rescale
        tc-grps             = System
        tau_t               = 0.1
        ref_t               = 300
        pcoupl              = Parrinello-Rahman
        pcoupltype          = isotropic
        tau_p               = 2.0
        ref_p               = 1.0
        compressibility     = 4.5e-5
        pbc                 = xyz
        gen_vel             = no
        """
        with open(self.md_mdp, "w") as f:
            f.write(mdp_content.strip())

    def run(self):
        self._create_production_mdp()
        # Generating TPR
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.md_mdp,
            "-c", self.npt_gro,
            "-t", self.npt_cpt,
            "-p", self.topol,
            "-o", self.md_tpr,
            "-maxwarn", "10"
        ]

        # Simulation
        mdrun_cmd = [
            self.gmx_bin, "mdrun",
            "-v",
            "-deffnm", self.output_base,
            "-ntomp", str(self.config.get("threads", 8)),
            "-pin", "on",
            "-nb", "gpu",       
            "-pme", "gpu",      
            "-update", "gpu"
        ]

        with tqdm(total=2, desc="  └─ Production Dynamics", leave=False) as pbar:
            try:
                subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)
                pbar.update(1)
                subprocess.run(mdrun_cmd, check=True, capture_output=True, text=True, cwd=self.config["work_dir"])
                pbar.update(1)
                
            except subprocess.CalledProcessError as e:
                self.logger.exception("Production MD Error:\n%s", e.stderr)
                raise e
            except Exception as e:
                self.logger.exception("Unexpected Error in ProductionStep")
                raise e