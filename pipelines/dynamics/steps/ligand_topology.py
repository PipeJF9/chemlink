import subprocess
import os
import shutil
from pipelines.dynamics.utils import convert_pdbqt_to_pdb

class LigandTopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.work_dir = self.config["work_dir"]
        
        # Archivos de entrada
        self.ligand_pdb = os.path.abspath(self.config["ligand_pdb"])
        self.protein_gro = os.path.join(self.work_dir, "processed.gro")
        self.topol_file = os.path.join(self.work_dir, "topol.top")
        
        # Carga y directorio temporal
        self.charge = self.config.get("ligand_charge", 0)
        self.acpype_workdir = os.path.join(self.work_dir, "acpype_work")

    def run(self):
        print(f"\n[*] Paso 1.5: Procesamiento de Ligando Pequeño (Carga: {self.charge})")
        
        if not os.path.exists(self.acpype_workdir):
            os.makedirs(self.acpype_workdir)
        
        internal_pdb = os.path.join(self.acpype_workdir, "ligand.pdb")
        
        if self.ligand_pdb.lower().endswith(".pdbqt"):
            print("   -> Detectado PDBQT. Convirtiendo a PDB con OpenBabel...")
            success = convert_pdbqt_to_pdb(self.ligand_pdb, internal_pdb)
            if not success:
                raise RuntimeError("Falló la conversión del ligando a PDB.")
        else:
            shutil.copy(self.ligand_pdb, internal_pdb)
        
        with open(internal_pdb, 'r') as f:
            content = f.readlines()
            # Verifica que el archivo no esté vacío y tenga coordenadas
            has_atoms = any(line.startswith(("ATOM", "HETATM")) for line in content)
            if not has_atoms:
                raise RuntimeError(f"El archivo {internal_pdb} se generó vacío o sin átomos. Revisa el PDBQT original.")

        # Ejecutar ACPYPE
        acpype_cmd = [
            "acpype", "-i", "ligand.pdb",
            "-b", "LIG", "-c", "bcc",
            "-n", str(self.charge), "-a", "gaff2"
        ]
        
        try:
            subprocess.run(acpype_cmd, check=True, cwd=self.acpype_workdir)
        except Exception as e:
            print(f"[X] Error en ACPYPE: {e}")
            raise e

        acpype_out_folder = ""
        for d in os.listdir(self.acpype_workdir):
            if d.endswith(".acpype"):
                acpype_out_folder = os.path.join(self.acpype_workdir, d)
                break
        
        if not acpype_out_folder:
            raise FileNotFoundError("No se encontró la carpeta de salida de ACPYPE")

        acpype_gro = os.path.join(acpype_out_folder, "LIG_GMX.gro")
        acpype_itp = os.path.join(acpype_out_folder, "LIG_GMX.itp")
        
        # Procesamiento de archivos
        self._clean_ligand_itp(acpype_itp)
        self._merge_gro(self.protein_gro, acpype_gro)
        self._patch_topology(acpype_itp)

        print(f"[✓] Ligando integrado: complex.gro")

    def _clean_ligand_itp(self, itp_path):
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
        with open(prot_gro, 'r') as f: p_lines = f.readlines()
        with open(lig_gro, 'r') as f: l_lines = f.readlines()

        p_atoms = p_lines[2:-1]
        l_atoms = l_lines[2:-1]
        box = p_lines[-1]
        total = len(p_atoms) + len(l_atoms)

        with open(os.path.join(self.work_dir, "complex.gro"), 'w') as f:
            f.write("Complex System\n")
            f.write(f"{total}\n")
            f.writelines(p_atoms)
            f.writelines(l_atoms)
            f.write(box)

    def _patch_topology(self, original_itp):
        atomtypes = []
        with open(original_itp, 'r') as f:
            capture = False
            for line in f:
                if "[ atomtypes ]" in line:
                    capture = True
                    atomtypes.append(line)
                    continue
                if capture and line.startswith("["): break
                if capture: atomtypes.append(line)

        with open(self.topol_file, 'r') as f:
            top_lines = f.readlines()

        new_top = []
        types_inserted = False
        itp_included = False

        for line in top_lines:
            # 1. Insertar atomtypes justo después del forcefield (inicio del archivo)
            if "forcefield.itp" in line and not types_inserted:
                new_top.append(line)
                new_top.append("\n; Atomtypes extraídos del ligando (GAFF2)\n")
                new_top.extend(atomtypes)
                new_top.append("\n")
                types_inserted = True
                continue

            # 2. Incluir el ITP del ligando antes de la sección de moléculas
            if "[ molecules ]" in line and not itp_included:
                new_top.append("; Topología del ligando\n")
                new_top.append('#include "ligand.itp"\n\n')
                new_top.append(line)
                itp_included = True
                continue
            
            # Evitar repetir la línea de LIG si ya existe por un error previo
            if line.strip() == "LIG                1":
                continue

            new_top.append(line)
        
        # 3. Añadir el ligando a la lista final de moléculas
        if not any("LIG" in l for l in top_lines[-5:]):
            new_top.append(f"LIG                1\n")

        with open(self.topol_file, 'w') as f:
            f.writelines(new_top)