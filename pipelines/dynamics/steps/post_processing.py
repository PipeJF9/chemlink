import subprocess
import os

class PostProcessingStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Archivos de entrada
        #self.md_tpr = os.path.join(self.config["work_dir"], "md.tpr")
        #self.md_xtc = os.path.join(self.config["work_dir"], "md.xtc")
        
        # Archivos de salida
        self.final_xtc = os.path.join(self.config["work_dir"], "md_center.xtc")
        self.segment_dir = os.path.join(self.config["work_dir"], "trayectorias_segmentadas")
        #self.final_pdb = os.path.join(self.config["work_dir"], "md.pdb")

    def run(self):
        print("\n[*] Paso 7: Post-procesamiento (Limpieza de PBC)...")
        if not os.path.exists(self.segment_dir):
                os.makedirs(self.segment_dir)
        # Correción de PBC y centrado de proteína
        center_cmd = [
            self.gmx_bin, "trjconv",
            "-s", "md.tpr",
            "-f", "md.xtc",
            "-o", "md_center.xtc",
            "-center",
            "-pbc", "mol",
            "-ur", "compact"
        ]
        # Generar PDB final
        sim_time_ps = int(float(self.config["ns_time"]) * 1000)
        dump_pdb_cmd = [
            self.gmx_bin, "trjconv",
            "-s", "md.tpr",
            "-f", "md_center.xtc",
            "-o", "md_final.pdb",
            "-dump", str(sim_time_ps)
        ]
        # Comando para extraer primeros 100 ps (analisis rapido)
        cmd_100 = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md_center.xtc",
                    "-o", os.path.join(self.segment_dir, "md_first_100ps.xtc"),
                    "-e", "100", "-tu", "ps"
                ]
        # Comando para extraer último 10% de la trayectoria
        last_10_percent_time = sim_time_ps * 0.9
        cmd_last = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md_center.xtc",
                    "-o", os.path.join(self.segment_dir, "md_last_10percent.xtc"),
                    "-b", str(last_10_percent_time), "-tu", "ps"
                ]
        try:
            print(f"   -> Centrando y corrigiendo PBC en {self.final_xtc}...")
            # El .sh envía "1" (Protein) y "0" (System)
            subprocess.run(center_cmd, input="1\n0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])


            print(f"   -> Extrayendo estructura final a los {sim_time_ps} ps...")
            try:
                subprocess.run(dump_pdb_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            except subprocess.CalledProcessError:
                print("      (!) Tiempo exacto no disponible, usando último frame disponible...")
                fallback_cmd = [
                    self.gmx_bin, "trjconv", 
                    "-s", "md.tpr", 
                    "-f", "md_center.xtc",
                    "-o", "md_final.pdb", 
                    "-dump", "-1"]
                subprocess.run(fallback_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            

            print(f"   -> Extrayendo segmentos temporales...")
            if sim_time_ps >= 100:
                subprocess.run(cmd_100, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            if last_10_percent_time > 0:
                print(f"      -> Guardando último 10% (desde {last_10_percent_time} ps)...")
                subprocess.run(cmd_last, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            print("[✓] Post-procesamiento finalizado. Archivos generados: md_center.xtc, md_final.pdb")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error en trjconv:\n{e.stderr}")
            raise e