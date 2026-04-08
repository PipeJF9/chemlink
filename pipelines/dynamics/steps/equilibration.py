import subprocess
import os

class EquilibrationStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entradas
        self.input_gro = os.path.join(self.config["work_dir"], "em.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        # Salidas NVT
        self.nvt_mdp = os.path.join(self.config["work_dir"], "nvt.mdp")
        self.nvt_tpr = os.path.join(self.config["work_dir"], "nvt.tpr")
        self.nvt_gro = os.path.join(self.config["work_dir"], "nvt.gro")
        
        # Salidas NPT
        self.npt_mdp = os.path.join(self.config["work_dir"], "npt.mdp")
        self.npt_tpr = os.path.join(self.config["work_dir"], "npt.tpr")
        self.npt_gro = os.path.join(self.config["work_dir"], "npt.gro")

    def _create_nvt_mdp(self):
        """Basado en la lógica de equilibración de temperatura a 300K"""
        mdp_content = (
            "title                   = Proteina Sola NVT\n"
            "define                  = -DPOSRES  ; Restricciones de posición\n"
            "integrator              = md\n"
            "nsteps                  = 50000     ; 100 ps\n"
            "dt                      = 0.002\n"
            "nstlist                 = 10\n"
            "rlist                   = 1.0\n"
            "coulombtype             = PME\n"
            "rcoulomb                = 1.0\n"
            "rvdw                    = 1.0\n"
            "tcoupl                  = V-rescale\n"
            "tc-grps                 = Protein Non-Protein\n"
            "tau_t                   = 0.1     0.1\n"
            "ref_t                   = 300     300\n"
            "pcoupl                  = no\n"
            "pbc                     = xyz\n"
        )
        with open(self.nvt_mdp, "w") as f:
            f.write(mdp_content)

    def _create_npt_mdp(self):
        """Basado en la lógica de equilibración de presión a 1 bar"""
        mdp_content = (
            "title                   = Proteina Sola NPT\n"
            "define                  = -DPOSRES\n"
            "integrator              = md\n"
            "nsteps                  = 50000     ; 100 ps\n"
            "dt                      = 0.002\n"
            "nstlist                 = 10\n"
            "rlist                   = 1.0\n"
            "coulombtype             = PME\n"
            "rcoulomb                = 1.0\n"
            "rvdw                    = 1.0\n"
            "tcoupl                  = V-rescale\n"
            "tc-grps                 = Protein Non-Protein\n"
            "tau_t                   = 0.1     0.1\n"
            "ref_t                   = 300     300\n"
            "pcoupl                  = Parrinello-Rahman\n"
            "pcoupltype              = isotropic\n"
            "tau_p                   = 2.0\n"
            "ref_p                   = 1.0\n"
            "compressibility         = 4.5e-5\n"
            "pbc                     = xyz\n"
        )
        with open(self.npt_mdp, "w") as f:
            f.write(mdp_content)

    def run(self):
        print("\n[*] Paso 5: Equilibración del sistema...")

        # FASE 1: NVT
        print("   -> Iniciando fase NVT (Estabilización de Temperatura)...")
        self._create_nvt_mdp()
        
        grompp_nvt = [self.gmx_bin, "grompp", "-f", self.nvt_mdp, "-c", self.input_gro, "-r", self.input_gro, "-p", self.topol, "-o", self.nvt_tpr]
        subprocess.run(grompp_nvt, check=True, capture_output=True, text=True)
        
        mdrun_nvt = [self.gmx_bin, "mdrun", "-deffnm", "nvt", "-nt", str(self.config.get("threads", 8))]
        subprocess.run(mdrun_nvt, check=True, cwd=self.config["work_dir"])

        # FASE 2: NPT
        print("   -> Iniciando fase NPT (Estabilización de Presión)...")
        self._create_npt_mdp()
        
        grompp_npt = [self.gmx_bin, "grompp", "-f", self.npt_mdp, "-c", self.nvt_gro, "-r", self.nvt_gro, "-p", self.topol, "-o", self.npt_tpr]
        subprocess.run(grompp_npt, check=True, capture_output=True, text=True)
        
        mdrun_npt = [self.gmx_bin, "mdrun", "-deffnm", "npt", "-nt", str(self.config.get("threads", 8))]
        subprocess.run(mdrun_npt, check=True, cwd=self.config["work_dir"])

        print(f"[✓] Equilibración completada. Sistema listo para producción.")