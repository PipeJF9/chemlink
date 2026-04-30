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
        self.rel_seg_dir = "trayectorias_segmentadas"
        self.segment_dir = os.path.join(self.config["work_dir"], self.rel_seg_dir)
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
            "-o", "md.pdb",
            "-dump", str(sim_time_ps)
        ]
        # Comando para extraer primeros 100 ps (analisis rapido)
        cmd_100 = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md_center.xtc",
                    "-o", os.path.join(self.rel_seg_dir, "md_first_100ps.xtc"),
                    "-e", "100", "-tu", "ps"
                ]
        # Comando para extraer último 10% de la trayectoria
        last_10_percent_time = sim_time_ps * 0.9
        cmd_last = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md_center.xtc",
                    "-o", os.path.join(self.rel_seg_dir, "md_last_10percent.xtc"),
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
                    "-o", "md.pdb", 
                    "-dump", "-1"]
                subprocess.run(fallback_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
            

            print(f"   -> Creando archivo de índice optimizado...")
            pdb_path = os.path.join(self.config["work_dir"], "md.pdb")
            chains = self._detect_chains(pdb_path)

            if self.config.get("sim_type") == "2":
                print("      -> Grupos para Proteína-Ligando...")
                make_ndx_input = "1 | 13\nname 22 Protein_Ligand\nq\n"
                #make_ndx_input = "1 | ! (Protein | Water | Ion)\nname 22 Protein_Ligand\nq\n"
                subprocess.run([self.gmx_bin, "make_ndx", "-f", "md.tpr", "-o", "index.ndx"], 
                               input=make_ndx_input, text=True, capture_output=True, cwd=self.config["work_dir"])
            elif self.config.get("sim_type") == "5":
                if len(chains) >= 2:
                    print(f"      -> Detectadas {len(chains)} cadenas. Creando índice P-P (Opción 5)...")
                    self._create_custom_pp_index(pdb_path, chains)
                else:
                    print(f"      (!) No se detectaron al menos 2 cadenas en el PDB. Creando índice estándar...")
                    subprocess.run([self.gmx_bin, "make_ndx", "-f", "md.tpr", "-o", "index.ndx"], 
                       input="q\n", text=True, capture_output=True, cwd=self.config["work_dir"])
            else:
                print("      -> Creando índice estándar...")
                subprocess.run([self.gmx_bin, "make_ndx", "-f", "md.tpr", "-o", "index.ndx"], 
                               input="q\n", text=True, capture_output=True, cwd=self.config["work_dir"])


            print(f"   -> Extrayendo segmentos temporales...")
            if sim_time_ps >= 100:
                subprocess.run(cmd_100, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            if last_10_percent_time > 0:
                print(f"      -> Guardando último 10% (desde {last_10_percent_time} ps)...")
                subprocess.run(cmd_last, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])

            print("[✓] Post-procesamiento finalizado. Archivos generados: md_center.xtc, md.pdb")

        except subprocess.CalledProcessError as e:
            print(f"[X] Error en trjconv:\n{e.stderr}")
            raise e
        
    def _detect_chains(self, pdb_file):
        chains = set()
        if not os.path.exists(pdb_file):
            return []
        with open(pdb_file, 'r') as f:
            for line in f:
                if line.startswith("ATOM"):

                    chain = line[21].strip()
                    if chain:
                        chains.add(chain)
        return sorted(list(chains))
    
    def _create_custom_pp_index(self, pdb_file, chains):
        atoms_by_chain = {c: [] for c in chains}
        with open(pdb_file, 'r') as f:
            for line in f:
                # El .sh filtra por ATOM/HETATM y longitud >= 27
                if line.startswith(("ATOM", "HETATM")) and len(line) >= 27:
                    try:
                        atom_num = line[6:11].strip()
                        chain = line[21].strip()
                        if chain in atoms_by_chain:
                            atoms_by_chain[chain].append(atom_num)
                    except: continue
        
        # Ordenar por tamaño como hace el .sh (sorted_chains)
        sorted_chains = sorted(atoms_by_chain.items(), key=lambda x: len(x[1]), reverse=True)
        c1_name, c1_atoms = sorted_chains[0]
        c2_name, c2_atoms = sorted_chains[1]

        index_path = os.path.join(self.config["work_dir"], "index.ndx")
        with open(index_path, 'w') as f:
            # Grupo 0: Protein (Cadena A)
            f.write("[ Protein ]\n")
            for i in range(0, len(c1_atoms), 15):
                f.write(" ".join(c1_atoms[i:i+15]) + "\n")
            # Grupo 1: Other (Cadena B)
            f.write("\n[ Other ]\n")
            for i in range(0, len(c2_atoms), 15):
                f.write(" ".join(c2_atoms[i:i+15]) + "\n")
        print(f"      [✓] index.ndx creado: [0] Protein ({c1_name}), [1] Other ({c2_name})")