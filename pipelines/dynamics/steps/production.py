import subprocess
import os
import shutil

class ProductionStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Rutas de archivos basadas en tu Pipeline y el .sh
        self.input_gro = os.path.join(self.config["work_dir"], "npt.gro")
        self.input_cpt = os.path.join(self.config["work_dir"], "npt.cpt")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        # El MDP que tu Pipeline ya modificó en data/input/dynamics/md.mdp
        self.source_mdp = "data/input/dynamics/md.mdp"
        # El MDP que usaremos en la carpeta de trabajo
        self.work_mdp = os.path.join(self.config["work_dir"], "md.mdp")
        
        self.md_tpr = os.path.join(self.config["work_dir"], "md_0_1.tpr")
        self.output_base = "md_0_1"

    def run(self):
        print("\n[*] Paso 6: Dinámica de Producción (Simulación Real)...")

        # 1. Copiar el MDP ya modificado por el Pipeline a la carpeta de trabajo
        # Esto es lo que hace el .sh al trabajar sobre el directorio de resultados
        if os.path.exists(self.source_mdp):
            shutil.copy(self.source_mdp, self.work_mdp)
            print(f"   -> Usando configuración de: {self.source_mdp}")
        else:
            raise FileNotFoundError(f"No se encontró el archivo MDP maestro en {self.source_mdp}")

        # 2. Generar el TPR con grompp
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.work_mdp,
            "-c", self.input_gro,
            "-t", self.input_cpt,
            "-p", self.topol,
            "-o", self.md_tpr
        ]

        # 3. Ejecutar la Dinámica con mdrun
        mdrun_cmd = [
            self.gmx_bin, "mdrun",
            "-deffnm", self.output_base,
            "-nt", str(self.config.get("threads", 8))
        ]

        try:
            print("   -> Preparando binario de producción...")
            subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)

            print(f"   -> Ejecutando simulación de {self.config['ns_time']} ns...")
            subprocess.run(mdrun_cmd, check=True, cwd=self.config["work_dir"])

            print(f"[✓] Simulación finalizada.")
            
        except subprocess.CalledProcessError as e:
            print(f"[X] Error en la producción:\n{e.stderr}")
            raise e