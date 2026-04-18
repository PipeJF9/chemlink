import subprocess
import os

class LigandTopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.work_dir = self.config["work_dir"]
        
        # Archivos de entrada
        self.ligand_pdb = os.path.abspath(self.config["ligand_pdb"])
        self.protein_gro = os.path.join(self.work_dir, "processed.gro")
        self.topol_file = os.path.join(self.work_dir, "topol.top")
        
        # Carga (por defecto 0 si no se especifica)
        self.charge = self.config.get("ligand_charge", 0)

    def run(self):
        print(f"\n[*] Paso 1.5: Procesamiento de Ligando Pequeño (Carga: {self.charge})")
        
        # 1. Ejecutar ACPYPE (Equivalente a tu comando de Bash)
        # Usamos gaff2 y bcc como en el script original
        acpype_cmd = [
            "acpype", "-i", self.ligand_pdb,
            "-b", "LIG",
            "-c", "bcc",
            "-n", str(self.charge),
            "-a", "gaff2"
        ]
        
        try:
            subprocess.run(acpype_cmd, check=True, cwd=self.work_dir)
        except Exception as e:
            print(f"[X] Error en ACPYPE: {e}")
            raise e

        # Localizar la carpeta de salida (ej: ligand.acpype)
        acpype_out = ""
        for d in os.listdir(self.work_dir):
            if d.endswith(".acpype"):
                acpype_out = os.path.join(self.work_dir, d)
                break
        
        if not acpype_out:
            raise FileNotFoundError("No se encontró la carpeta de salida de ACPYPE")

        # 2. Rutas de archivos generados
        acpype_gro = os.path.join(acpype_out, "LIG_GMX.gro")
        acpype_itp = os.path.join(acpype_out, "LIG_GMX.itp")
        
        # 3. Limpiar ITP (Remover [ atomtypes ] para evitar duplicados, como en tu Bash)
        self._clean_ligand_itp(acpype_itp)
        
        # 4. Combinar .gro (Proteína + Ligando)
        self._merge_gro(self.protein_gro, acpype_gro)
        
        # 5. Modificar topol.top (Insertar atomtypes e include)
        self._patch_topology(acpype_itp)

        print("[✓] Ligando integrado exitosamente.")

    def _clean_ligand_itp(self, itp_path):
        """Remueve la sección [ atomtypes ] del ITP del ligando."""
        with open(itp_path, 'r') as f:
            lines = f.readlines()
        
        clean_lines = []
        skip = False
        for line in lines:
            if "[ atomtypes ]" in line:
                skip = True
                continue
            if skip and line.startswith("["):
                skip = False
            if not skip:
                clean_lines.append(line)
        
        with open(os.path.join(self.work_dir, "ligand.itp"), 'w') as f:
            f.writelines(clean_lines)

    def _merge_gro(self, prot_gro, lig_gro):
        """Combina las coordenadas de proteína y ligando."""
        with open(prot_gro, 'r') as f:
            p_lines = f.readlines()
        with open(lig_gro, 'r') as f:
            l_lines = f.readlines()

        p_atoms = p_lines[2:-1]
        l_atoms = l_lines[2:-1]
        box = p_lines[-1]
        total = len(p_atoms) + len(l_atoms)

        with open(os.path.join(self.work_dir, "complex.gro"), 'w') as f:
            f.write("Complex Protein-Ligand\n")
            f.write(f"{total}\n")
            f.writelines(p_atoms)
            f.writelines(l_atoms)
            f.write(box)

    def _patch_topology(self, original_itp):
        """Modifica el topol.top para incluir atomtypes y el ligand.itp."""
        # Extraer solo los atomtypes del ITP original (lo que hace tu awk)
        atomtypes = []
        with open(original_itp, 'r') as f:
            capture = False
            for line in f:
                if "[ atomtypes ]" in line:
                    capture = True
                    atomtypes.append(line)
                    continue
                if capture and line.startswith("["):
                    break
                if capture:
                    atomtypes.append(line)

        with open(self.topol_file, 'r') as f:
            top_lines = f.readlines()

        new_top = []
        for line in top_lines:
            # Insertar atomtypes antes de la primera moleculetype
            if "[ moleculetype ]" in line and atomtypes:
                new_top.append("; Atomtypes from ligand\n")
                new_top.extend(atomtypes)
                new_top.append("\n")
                atomtypes = None # Solo insertar una vez
                new_top.append(line)
            # Insertar include ligand.itp antes de la sección de moléculas
            elif "[ molecules ]" in line:
                new_top.append("; Include ligand topology\n")
                new_top.append('#include "ligand.itp"\n\n')
                new_top.append(line)
            else:
                new_top.append(line)
        
        # Añadir la línea del ligando al final
        new_top.append(f"LIG                1\n")

        with open(self.topol_file, 'w') as f:
            f.writelines(new_top)