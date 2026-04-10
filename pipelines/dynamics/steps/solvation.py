import subprocess
import os

class SolvationStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entrada (TopologyStep)
        self.input_gro = os.path.join(self.config["work_dir"], "processed.gro")
        # Entrada y salida
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        # Salida
        self.boxed_gro = os.path.join(self.config["work_dir"], "boxed.gro")
        self.solvated_gro = os.path.join(self.config["work_dir"], "solvated.gro")

    def run(self):
        print("\n[*] Paso 2: Configurando entorno (Caja + Solvatación)...")

        # ACCIÓN 1: Definir la caja con editconf
        editconf_cmd = [
            self.gmx_bin, "editconf",
            "-f", self.input_gro,
            "-o", self.boxed_gro,
            "-bt", "cubic",
            "-d", "1.0",
            "-c"
        ]
        
        # ACCIÓN 2: Añadir agua con solvate
        solvate_cmd = [
            self.gmx_bin, "solvate",
            "-cp", self.boxed_gro,
            "-cs", "spc216.gro",
            "-o", self.solvated_gro,
            "-p", self.topol
        ]

        try:
            # Ejecutar 1
            print("   -> Definiendo dimensiones de la caja...")
            subprocess.run(editconf_cmd, check=True, capture_output=True, text=True)
            
            # Ejecutar 2
            print("   -> Añadiendo moléculas de agua (Solvatación)...")
            subprocess.run(solvate_cmd, check=True, capture_output=True, text=True)
            
            if os.path.exists(self.solvated_gro):
                print(f"[✓] Sistema solvatado con éxito: {self.solvated_gro}")
                print(f"[✓] Topología actualizada: {os.path.basename(self.topol)}")
            else:
                raise FileNotFoundError("GROMACS terminó, pero no se encontró el archivo solvatado.")
            
        except subprocess.CalledProcessError as e:
            print(f"[X] Error en solvatación:\n{e.stderr}")
            raise e