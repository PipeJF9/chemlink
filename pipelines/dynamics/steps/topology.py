import subprocess
import os

class TopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Convertimos la entrada a ruta absoluta para evitar el error que tuviste
        self.pdb_input_abs = os.path.abspath(self.config["pdb_input"])
        
        # El archivo de salida será processed.gro dentro del work_dir
        self.output_gro = "processed.gro" 

    def run(self):
        print(f"[*] Paso 1: Generando topología del sistema...")
    
        # Comando idéntico a tu .sh
        command_cmd = [
            self.gmx_bin, "pdb2gmx",
            "-f", self.pdb_input_abs, # <--- Ruta absoluta
            "-o", self.output_gro,
            "-ff", "amber03", 
            "-water", "tip3p",
            "-ignh"
        ]

        try:
            # Ejecutamos dentro de work_dir para que topol.top se cree ahí
            subprocess.run(
                command_cmd, 
                check=True, 
                capture_output=True, 
                text=True, 
                cwd=self.config["work_dir"] # Aquí es donde se "para" GROMACS
            )
            
            # Verificamos si se creó el archivo en la carpeta de trabajo
            if os.path.exists(os.path.join(self.config["work_dir"], "topol.top")):
                print(f"[✓] Topología generada exitosamente.")
            else:
                raise FileNotFoundError("No se encontró topol.top tras ejecutar pdb2gmx")

        except subprocess.CalledProcessError as e:
            # Imprimimos el error de GROMACS para debug
            print(f"[X] Error en pdb2gmx:\n{e.stderr}")
            raise e