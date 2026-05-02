import subprocess
import os

class EquilibrationStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entradas
        self.em_gro = os.path.join(self.config["work_dir"], "em.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        # Salidas NVT
        self.nvt_mdp = os.path.join(self.config["work_dir"], "nvt.mdp")
        self.nvt_tpr = os.path.join(self.config["work_dir"], "nvt.tpr")
        self.nvt_gro = os.path.join(self.config["work_dir"], "nvt.gro")
        self.nvt_cpt = os.path.join(self.config["work_dir"], "nvt.cpt")
        
        # Salidas NPT
        self.npt_mdp = os.path.join(self.config["work_dir"], "npt.mdp")
        self.npt_tpr = os.path.join(self.config["work_dir"], "npt.tpr")
        self.npt_gro = os.path.join(self.config["work_dir"], "npt.gro")

    def _create_nvt_mdp(self):
        mdp_content = (
            "integrator  = md\n"
            "nsteps      = 50000\n"
            "dt          = 0.002\n"
            "nstxout     = 5000\n"
            "nstvout     = 5000\n"
            "nstenergy   = 5000\n"
            "nstlog      = 5000\n"
            "continuation = no\n"
            "constraint_algorithm = lincs\n"
            "constraints = h-bonds\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "nstlist     = 10\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "coulombtype = PME\n"
            "pme_order   = 4\n"
            "fourierspacing = 0.16\n"
            "tcoupl      = V-rescale\n"
            "tc-grps     = System\n"
            "tau_t       = 0.1\n"
            "ref_t       = 300\n"
            "pcoupl      = no\n"
            "pbc         = xyz\n"
            "gen_vel     = yes\n"
            "gen_temp    = 300\n"
            "gen_seed    = -1\n"
        )
        with open(self.nvt_mdp, "w") as f:
            f.write(mdp_content)

    def _create_npt_mdp(self):
        mdp_content = (
            "integrator  = md\n"
            "nsteps      = 50000\n"
            "dt          = 0.002\n"
            "nstxout     = 5000\n"
            "nstvout     = 5000\n"
            "nstenergy   = 5000\n"
            "nstlog      = 5000\n"
            "continuation = yes\n"
            "constraint_algorithm = lincs\n"
            "constraints = h-bonds\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "nstlist     = 10\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "coulombtype = PME\n"
            "pme_order   = 4\n"
            "fourierspacing = 0.16\n"
            "tcoupl      = V-rescale\n"
            "tc-grps     = System\n"
            "tau_t       = 0.1\n"
            "ref_t       = 300\n"
            "pcoupl      = Parrinello-Rahman\n"
            "pcoupltype  = isotropic\n"
            "tau_p       = 2.0\n"
            "ref_p       = 1.0\n"
            "compressibility = 4.5e-5\n"
            "refcoord_scaling = com\n"
            "pbc         = xyz\n"
            "gen_vel     = no\n"
        )
        with open(self.npt_mdp, "w") as f:
            f.write(mdp_content)

    def run(self):
        print("\n[*] Paso 5: Equilibración del sistema...")

        # FASE 1: NVT
        print("   -> Iniciando fase NVT (Estabilización de Temperatura)...")
        self._create_nvt_mdp()
        
        grompp_nvt = [
            self.gmx_bin, "grompp", 
            "-f", self.nvt_mdp, 
            "-c", self.em_gro, 
            "-r", self.em_gro, 
            "-p", self.topol, 
            "-o", self.nvt_tpr,
            "-maxwarn", "10"
            ]
        subprocess.run(grompp_nvt, check=True, capture_output=True, text=True)
        
        mdrun_nvt = [
            self.gmx_bin, "mdrun", 
            "-v",
            "-deffnm", "nvt", 
            "-ntomp", str(self.config.get("threads", 8)),
            "-nb", "gpu",       
            "-pme", "gpu",      
            "-update", "gpu"
            ]
        subprocess.run(mdrun_nvt, check=True, cwd=self.config["work_dir"])

        # FASE 2: NPT
        print(f"   -> Iniciando fase NPT (Estabilización de Presión) {str(self.config.get('threads', 8))}")
        self._create_npt_mdp()
        
        grompp_npt = [
            self.gmx_bin, "grompp", 
            "-f", self.npt_mdp, 
            "-c", self.nvt_gro, 
            "-r", self.nvt_gro, 
            "-t", self.nvt_cpt,
            "-p", self.topol, 
            "-o", self.npt_tpr,
            "-maxwarn", "10"
            ]
        subprocess.run(grompp_npt, check=True, capture_output=True, text=True)
        
        mdrun_npt = [
            self.gmx_bin, "mdrun", 
            "-v",
            "-deffnm", "npt", 
            "-ntomp", str(self.config.get("threads", 8)),
            "-nb", "gpu",       
            "-pme", "gpu",      
            "-update", "gpu"
            ]
        subprocess.run(mdrun_npt, check=True, cwd=self.config["work_dir"])

        print(f"[✓] Equilibración completada. Sistema listo para producción.")