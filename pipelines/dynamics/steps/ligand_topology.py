import subprocess
import os
import shutil

class LigandTopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.work_dir = self.config["work_dir"]
        
        # Archivos definidos en tu .sh
        self.ligand_pdb = os.path.join(self.work_dir, "ligand.pdb")
        self.protein_pdb = os.path.join(self.work_dir, "proteina.pdb")
        self.acpype_work = os.path.join(self.work_dir, "acpype_work")

    def run(self):
        print("\n[*] Paso 1.2: Procesando Ligando Pequeño con ACPYPE...")
        
        # 1. Crear directorio de trabajo para ACPYPE
        os.makedirs(self.acpype_work, exist_ok=True)
        shutil.copy(self.ligand_pdb, os.path.join(self.acpype_work, "ligand.pdb"))

        # 2. Ejecutar ACPYPE
        # acpype -i ligand.pdb -b LIG -c user -n charge -a gaff2
        charge = self.config.get("ligand_charge", "0")
        acpype_cmd = [
            "acpype", "-i", "ligand.pdb", 
            "-b", "LIG", 
            "-c", "user", 
            "-n", str(charge), 
            "-a", "gaff2"
        ]

        try:
            print(f"   -> Ejecutando ACPYPE (Carga: {charge})...")
            subprocess.run(acpype_cmd, check=True, cwd=self.acpype_work, capture_output=True, text=True)
            
            # Buscar la carpeta .acpype generada
            acpype_out_dir = next(d for d in os.listdir(self.acpype_work) if d.endswith(".acpype"))
            full_acpype_path = os.path.join(self.acpype_work, acpype_out_dir)

            # 3. Copiar y Limpiar archivos (Lógica del AWK en tu .sh)
            self._process_itp_files(full_acpype_path)
            
            # 4. Generar topología de la proteína
            print("   -> Generando topología de la proteína base...")
            protein_cmd = [
                self.gmx_bin, "pdb2gmx",
                "-f", "proteina.pdb",
                "-o", "protein.gro",
                "-ff", "amber03",
                "-water", "tip3p"
            ]
            subprocess.run(protein_cmd, check=True, cwd=self.work_dir, capture_output=True, text=True)

            # 5. Combinar archivos GRO (Proteína + Ligando)
            self._combine_gro_files()

            # 6. Modificar topol.top (Inyectar atomtypes e include)
            self._update_topol_file()

            print("[✓] Complejo Proteína-Ligando ensamblado correctamente.")

        except Exception as e:
            print(f"[X] Error en el procesamiento del ligando: {e}")
            raise e

    def _process_itp_files(self, source_dir):
        """Limpia el archivo ITP removiendo atomtypes duplicados"""
        orig_itp = os.path.join(source_dir, "LIG_GMX.itp")
        target_itp = os.path.join(self.work_dir, "ligand.itp")
        atomtypes_itp = os.path.join(self.work_dir, "ligand_atomtypes.itp")

        # Extraer atomtypes para el topol.top y limpiar el ligand.itp
        with open(orig_itp, 'r') as f:
            lines = f.readlines()

        with open(target_itp, 'w') as f_itp, open(atomtypes_itp, 'w') as f_at:
            skip = False
            in_atomtypes = False
            for line in lines:
                if line.startswith("[ atomtypes ]"):
                    in_atomtypes = True
                    f_at.write(line)
                    skip = True
                    continue
                if line.startswith("[") and in_atomtypes:
                    in_atomtypes = False
                    skip = False
                
                if in_atomtypes:
                    f_at.write(line)
                if not skip:
                    f_itp.write(line)
        
        # También copiamos el .gro del ligando
        shutil.copy(os.path.join(source_dir, "LIG_GMX.gro"), os.path.join(self.work_dir, "ligand.gro"))

    def _combine_gro_files(self):
        """Combina protein.gro y ligand.gro en raw.gro"""
        with open(os.path.join(self.work_dir, "protein.gro"), 'r') as f:
            p_lines = f.readlines()
        with open(os.path.join(self.work_dir, "ligand.gro"), 'r') as f:
            l_lines = f.readlines()

        p_atoms = int(p_lines[1].strip())
        l_atoms = int(l_lines[1].strip())
        
        with open(os.path.join(self.work_dir, "raw.gro"), 'w') as f:
            f.write("Complejo generado por ChemLink\n")
            f.write(f"{p_atoms + l_atoms}\n")
            f.extend(p_lines[2:-1]) # Átomos de proteína
            f.extend(l_lines[2:-1]) # Átomos de ligando
            f.write(p_lines[-1])    # Caja

    def _update_topol_file(self):
        """Inyecta la topología del ligando en el topol.top de la proteína"""
        topol_path = os.path.join(self.work_dir, "topol.top")
        at_path = os.path.join(self.work_dir, "ligand_atomtypes.itp")
        
        with open(topol_path, 'r') as f:
            lines = f.readlines()

        new_lines = []
        inserted_at = False
        inserted_itp = False

        for line in lines:
            # Insertar atomtypes antes de la primera moleculetype
            if "[ moleculetype ]" in line and not inserted_at:
                with open(at_path, 'r') as f_at:
                    new_lines.append("\n; Atomtypes from ligand\n")
                    new_lines.extend(f_at.readlines())
                inserted_at = True
            
            # Insertar el include del ligando antes de [ molecules ]
            if "[ molecules ]" in line and not inserted_itp:
                new_lines.append("\n; Include ligand topology\n")
                new_lines.append('#include "ligand.itp"\n\n')
                inserted_itp = True

            new_lines.append(line)

        # Añadir la molécula LIG al final
        new_lines.append("LIG                1\n")

        with open(topol_path, 'w') as f:
            f.writelines(new_lines)