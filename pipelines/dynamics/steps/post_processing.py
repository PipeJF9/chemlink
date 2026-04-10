import subprocess
import os

class PostProcessingStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Archivos de entrada (tal cual salen de la producción en el .sh)
        self.md_tpr = os.path.join(self.config["work_dir"], "md_1.tpr")
        self.md_xtc = os.path.join(self.config["work_dir"], "md_1.xtc")
        
        # Archivos de salida (nombres exactos del .sh)
        self.no_pbc_xtc = os.path.join(self.config["work_dir"], "md_1_noPBC.xtc")
        self.final_xtc = os.path.join(self.config["work_dir"], "md_1_center.xtc")
        self.final_pdb = os.path.join(self.config["work_dir"], "md_1.pdb")

    def run(self):
        print("\n[*] Paso 7: Post-procesamiento (Limpieza de PBC)...")

        # COMANDO 1: gmx trjconv -s md_1.tpr -f md_1.xtc -o md_1_noPBC.xtc -pbc mol -ur compact
        # Este comando mete las moléculas rotas dentro de la caja.
        pbc_mol_cmd = [
            self.gmx_bin, "trjconv",
            "-s", self.md_tpr,
            "-f", self.md_xtc,
            "-o", self.no_pbc_xtc,
            "-pbc", "mol",
            "-ur", "compact"
        ]

        # COMANDO 2: gmx trjconv -s md_1.tpr -f md_1_noPBC.xtc -o md_1_center.xtc -center
        # Este centra la proteína.
        center_cmd = [
            self.gmx_bin, "trjconv",
            "-s", self.md_tpr,
            "-f", self.no_pbc_xtc,
            "-o", self.final_xtc,
            "-center"
        ]

        # COMANDO 3: gmx trjconv -s md_1.tpr -f md_1_center.xtc -o md_1.pdb -dump 0
        # Genera el PDB final de referencia.
        dump_pdb_cmd = [
            self.gmx_bin, "trjconv",
            "-s", self.md_tpr,
            "-f", self.final_xtc,
            "-o", self.final_pdb,
            "-dump", "0"
        ]

        try:
            # En el primer comando, el .sh asume seleccionar "System" (0)
            print("   -> Aplicando -pbc mol -ur compact...")
            subprocess.run(pbc_mol_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            # En el segundo, pide: 1 (Protein) para centrar y 0 (System) para guardar
            print("   -> Centrando proteína en la caja...")
            subprocess.run(center_cmd, input="1\n0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            # En el tercero, selecciona "System" (0) para el PDB
            print("   -> Generando PDB final...")
            subprocess.run(dump_pdb_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            print("[✓] Post-procesamiento completado. Trayectoria final: md_1_center.xtc")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error en trjconv:\n{e.stderr}")
            raise e