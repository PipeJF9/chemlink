import subprocess
import os

class PostProcessingStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Archivos de salida
        self.final_xtc = os.path.join(self.config["work_dir"], "md_center.xtc")
        self.rel_seg_dir = "trayectorias_segmentadas"
        self.segment_dir = os.path.join(self.config["work_dir"], self.rel_seg_dir)

    def run(self):
        print("\n[*] Paso 7: Post-procesamiento (Limpieza de PBC e Índices)...")
        if not os.path.exists(self.segment_dir):
            os.makedirs(self.segment_dir)

        # 1. Correción de PBC y centrado
        center_cmd = [
            self.gmx_bin, "trjconv",
            "-s", "md.tpr", "-f", "md.xtc",
            "-o", "md_center.xtc",
            "-center", "-pbc", "mol", "-ur", "compact"
        ]

        # 2. Generar PDB final para análisis
        sim_time_ps = int(float(self.config["ns_time"]) * 1000)
        dump_pdb_cmd = [
            self.gmx_bin, "trjconv",
            "-s", "md.tpr", "-f", "md_center.xtc",
            "-o", "md.pdb", "-dump", str(sim_time_ps)
        ]

        try:
            print(f"   -> Centrando y corrigiendo PBC...")
            subprocess.run(center_cmd, input="1\n0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            print(f"   -> Extrayendo estructura final a {sim_time_ps} ps...")
            try:
                subprocess.run(dump_pdb_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            except subprocess.CalledProcessError:
                print("      (!) Tiempo exacto no disponible, usando último frame...")
                fallback_cmd = [self.gmx_bin, "trjconv", "-s", "md.tpr", "-f", "md_center.xtc", "-o", "md.pdb", "-dump", "-1"]
                subprocess.run(fallback_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            self._generate_smart_index()

            self._extract_segments(sim_time_ps)

            print("[✓] Post-procesamiento finalizado con éxito.")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error en trjconv:\n{e.stderr}")
            raise e

    def _generate_smart_index(self):
        sim_type = self.config.get("sim_type")
        print(f"   -> Configurando índice para Opción {sim_type}...")

        if sim_type == "2": # Proteína-Ligando
            make_ndx_input = "1 | 13\nname 22 Protein_Ligand\nq\n"
        
        elif sim_type == "4": # Ácido Nucleico
            make_ndx_input = "r DNA RNA DR DNA5 DNA3\nname 22 Nucleic_Acid\n1 | 22\nname 23 Complex\nq\n"
            print("      [i] Identificando grupos de Ácidos Nucleicos...")

        elif sim_type in ["3", "5"]: # Péptido o Proteína-Proteína
            print("      [i] Creando índice separando cadenas mediante topología (splitres)...")
            make_ndx_input = "splitres 0\nq\n" 
        
        elif sim_type == "6": # Proteína-Proteína + Ligando
            print("      [i] Creando índice para Proteína-Proteína + Ligando...")
            make_ndx_input = "splitres 0\n1 | 13\nname 22 Complex_System\nq\n"
        else:
            make_ndx_input = "q\n"

        try:
            subprocess.run(
                [self.gmx_bin, "make_ndx", "-f", "md.tpr", "-o", "index.ndx"], 
                input=make_ndx_input, 
                text=True, 
                capture_output=True, 
                check=True, 
                cwd=self.config["work_dir"]
            )
            print("      [✓] index.ndx generado correctamente.")
        except subprocess.CalledProcessError as e:
            print(f"      [X] Error crítico al generar index.ndx:\n{e.stderr}")
            raise e

    def _extract_segments(self, sim_time_ps):
        last_10_ps = sim_time_ps * 0.9
        segments = [
            (os.path.join(self.rel_seg_dir, "md_first_100ps.xtc"), "0", "100"),
            (os.path.join(self.rel_seg_dir, "md_last_10percent.xtc"), str(last_10_ps), str(sim_time_ps))
        ]
        
        for out_file, start, end in segments:
            if sim_time_ps > float(start):
                cmd = [self.gmx_bin, "trjconv", "-s", "md.tpr", "-f", "md_center.xtc", 
                       "-o", out_file, "-b", start, "-e", end, "-tu", "ps"]
                subprocess.run(cmd, input="0\n", text=True, capture_output=True, cwd=self.config["work_dir"])