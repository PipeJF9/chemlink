import subprocess
import os

class EnergyMinStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entradas
        self.input_gro = os.path.join(self.config["work_dir"], "ionized.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        self.em_mdp = os.path.join(self.config["work_dir"], "em.mdp")
        self.em_tpr = os.path.join(self.config["work_dir"], "em.tpr")
        self.em_gro = os.path.join(self.config["work_dir"], "em.gro")
        # em_log = os.path.join(self.config["work_dir"], "em.log") lo quitamos porque gmx mdrun ya lo genera automáticamente

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
        print("\n[*] Paso 4: Minimización de Energía (EM)...")
        self._create_em_mdp()

        # 1. grompp
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.em_mdp,
            "-c", self.input_gro,
            "-p", self.topol,
            "-o", self.em_tpr,
            "-maxwarn", "10"
        ]

        # 2. mdrun
        mdrun_cmd = [
            self.gmx_bin, "mdrun",
            "-v", 
            "-deffnm", "em",
            "-nt", str(self.config.get("threads", 8)) # tomamos el número de threads del config, con un default de 8
        ]

        try:
            print("   -> Preparando sistema...")
            subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)

            print("   -> Minimizando (revisar em.log para detalles)...")
            subprocess.run(mdrun_cmd, check=True, cwd=self.config["work_dir"])

            if os.path.exists(self.em_gro):
                print(f"[✓] Estructura minimizada en: {os.path.basename(self.em_gro)}")
            
        except subprocess.CalledProcessError as e:
            print(f"[X] Error en el Paso 4!")
            raise e