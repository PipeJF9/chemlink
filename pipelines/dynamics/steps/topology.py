import subprocess
import os

class TopologyStep:
    def __init__(self, config, gmx_bin):
        """
        Recibe la configuración del pipeline.
        Utiliza el PDB de entrada y define dónde se guardará la topología.
        """
        self.config = config
        self.gmx_bin = gmx_bin
        # Asegúrate de que este comando esté en tu PATH o ajusta la ruta aquí.
        
        # Definimos los nombres de los archivos de salida en el directorio de trabajo
        self.output_gro = os.path.join(self.config["work_dir"], "processed_complex.gro")
        self.output_top = os.path.join(self.config["work_dir"], "topol.top")
        self.output_itp = os.path.join(self.config["work_dir"], "posre.itp")

    def run(self):
        print(f"[*] Ejecutando pdb2gmx para: {self.config['pdb_input']}")
        
        # Construcción del comando siguiendo la lógica del Dinamica.sh
        # -ff amber99sb-ildn: Campo de fuerza (puedes parametrizarlo luego)
        # -water tip3p: Modelo de agua
        # -ignh: Ignorar hidrógenos presentes para evitar errores de nomenclatura
        command = [
            self.gmx_bin, "pdb2gmx",
            "-f", self.config["pdb_input"],
            "-o", self.output_gro,
            "-p", self.output_top,
            "-i", self.output_itp,
            "-ff", "amber99sb-ildn", 
            "-water", "tip3p",
            "-ignh"
        ]

        try:
            # Ejecutamos el comando
            # check=True lanza una excepción si el comando falla
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True
            )
            
            # Verificamos si los archivos se crearon realmente
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