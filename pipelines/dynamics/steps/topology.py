import subprocess
import os

class TopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Archivos de salida
        self.output_gro = os.path.join(self.config["work_dir"], "processed_complex.gro")
        self.output_top = os.path.join(self.config["work_dir"], "topol.top")
        self.output_itp = os.path.join(self.config["work_dir"], "posre.itp")

    def run(self):
        print(f"[*] Paso 1: Ejecutando pdb2gmx para: {self.config['pdb_input']}")
    
        # -ff amber99sb-ildn: Campo de fuerza (puedes parametrizarlo luego)
        # -water tip3p: Modelo de agua
        # -ignh: Ignorar hidrógenos presentes para evitar errores de nomenclatura
        command_cmd = [
            self.gmx_bin, "pdb2gmx",
            "-f", self.config["pdb_input"],
            "-o", self.output_gro,
            "-p", self.output_top,
            "-i", self.output_itp,
            "-ff", "amber03", 
            "-water", "tip3p",
            "-ignh"
        ]

        try:
            # Ejecuta el comando
            result = subprocess.run(command_cmd, check=True, capture_output=True, text=True)
            
            # Verificamos que el archivo se creo correctamente
            if os.path.exists(self.output_top):
                print(f"[✓] Topología generada exitosamente en: {self.output_top}")
            else:
                raise FileNotFoundError("El comando terminó pero no se encontró el archivo .top")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error fatal en pdb2gmx:")
            print(e.stderr) # Esto te da el error exacto de GROMACS
            raise e
        except Exception as e:
            print(f"[X] Error inesperado en el paso de topología: {e}")
            raise e