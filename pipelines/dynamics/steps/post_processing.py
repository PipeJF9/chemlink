import subprocess
import os

class PostProcessingStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Archivos de entrada
        self.md_tpr = os.path.join(self.config["work_dir"], "md.tpr")
        self.md_xtc = os.path.join(self.config["work_dir"], "md.xtc")
        
        # Archivos de salida
        self.final_xtc = os.path.join(self.config["work_dir"], "md_center.xtc")
        self.final_pdb = os.path.join(self.config["work_dir"], "md.pdb")

    def run(self):
        print("\n[*] Paso 7: Post-procesamiento (Limpieza de PBC)...")

        # Correción de PBC y centrado de proteína
        center_cmd = [
            self.gmx_bin, "trjconv",
            "-s", self.md_tpr,
            "-f", self.md_xtc,
            "-o", self.final_xtc,
            "-center",
            "-pbc", "mol",
            "-ur", "compact"
        ]

        # Generar PDB final
        sim_time_ps = int(float(self.config["ns_time"]) * 1000)
        dump_pdb_cmd = [
            self.gmx_bin, "trjconv",
            "-s", self.md_tpr,
            "-f", self.final_xtc,
            "-o", self.final_pdb,
            "-dump", str(sim_time_ps)
        ]

        try:
            print(f"   -> Centrando y corrigiendo PBC en {self.final_xtc}...")
            # El .sh envía "1" (Protein) y "0" (System)
            subprocess.run(center_cmd, input="1\n0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            print(f"   -> Extrayendo estructura final a los {sim_time_ps} ps...")
            try:
                # Intentamos dump al tiempo exacto (Seleccionamos 0: System)
                subprocess.run(dump_pdb_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            except subprocess.CalledProcessError:
                # Si falla usamos el último frame (-dump -1)
                print("      (!) Tiempo exacto no disponible, usando último frame disponible...")
                fallback_cmd = [self.gmx_bin, "trjconv", "-s", self.md_tpr, "-f", self.final_xtc, "-o", self.final_pdb, "-dump", "-1"]
                subprocess.run(fallback_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            
            print("[✓] Post-procesamiento completado. Trayectoria final: md_1_center.xtc")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error en trjconv:\n{e.stderr}")
            raise e