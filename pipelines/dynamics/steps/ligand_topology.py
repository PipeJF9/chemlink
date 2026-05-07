import subprocess
import os
import shutil
from tqdm import tqdm
from pipelines.dynamics.utils import convert_pdbqt_to_pdb

from ..logger import get_step_logger

class LigandTopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.work_dir = self.config["work_dir"]
        
        self.ligand_pdb = os.path.abspath(self.config["ligand_pdb"])
        self.protein_gro = os.path.join(self.work_dir, "processed.gro")
        self.topol_file = os.path.join(self.work_dir, "topol.top")
        
        self.charge = self.config.get("ligand_charge", 0)
        self.acpype_workdir = os.path.join(self.work_dir, "acpype_work")
        self.logger = get_step_logger(__name__, os.path.join(self.work_dir, "simulation.log"))

    def run(self):
        with tqdm(total=5, desc="  └─ Ligand Topology Generation", leave=False) as pbar:
            try:
                if not os.path.exists(self.acpype_workdir):
                    os.makedirs(self.acpype_workdir)
                internal_pdb = os.path.join(self.acpype_workdir, "ligand.pdb")
                # Format Conversion
                if self.ligand_pdb.lower().endswith(".pdbqt"):
                    success = convert_pdbqt_to_pdb(self.ligand_pdb, internal_pdb)
                    if not success:
                        self.logger.error("Failed to convert %s to PDB using OpenBabel.", self.ligand_pdb)
                        raise RuntimeError("Failed to convert ligand PDBQT to PDB.")
                else:
                    try:
                        shutil.copy(self.ligand_pdb, internal_pdb)
                    except FileNotFoundError:
                        self.logger.error("Source ligand file not found: %s", self.ligand_pdb)
                        raise

                pbar.update(1)

                # Ensure the expected internal PDB was actually created
                if not os.path.exists(internal_pdb):
                    self.logger.error("Expected internal PDB not found after conversion/copy: %s", internal_pdb)
                    raise FileNotFoundError(f"Expected file not found: {internal_pdb}")

                with open(internal_pdb, 'r') as f:
                    content = f.readlines()
                    has_atoms = any(line.startswith(("ATOM", "HETATM")) for line in content)
                    if not has_atoms:
                        raise RuntimeError(
                            f"The file {internal_pdb} was generated empty or without atoms. "
                            "Please check the original PDBQT file.")
                    
                # Step 2: Running ACPYPE
                acpype_cmd = [
                    "acpype", "-i", "ligand.pdb",
                    "-b", "LIG", "-c", "bcc",
                    "-n", str(self.charge), "-a", "gaff2"
                ]

                subprocess.run(acpype_cmd, check=True, capture_output=True, text=True, cwd=self.acpype_workdir)
                pbar.update(1)

                acpype_out_folder = next((os.path.join(self.acpype_workdir, d) 
                                       for d in os.listdir(self.acpype_workdir) 
                                       if d.endswith(".acpype")), None)
                
                if not acpype_out_folder:
                    raise FileNotFoundError("ACPYPE output directory was not found.")

                acpype_gro = os.path.join(acpype_out_folder, "LIG_GMX.gro")
                acpype_itp = os.path.join(acpype_out_folder, "LIG_GMX.itp")
                
                self._clean_ligand_itp(acpype_itp)
                pbar.update(1)
                self._merge_gro(self.protein_gro, acpype_gro)
                pbar.update(1)
                self._patch_topology(acpype_itp)
                pbar.update(1)
            except subprocess.CalledProcessError as e:
                # capture stderr from ACPYPE and log it
                stderr = getattr(e, 'stderr', None)
                if stderr:
                    self.logger.exception("ACPYPE Execution Error: %s", stderr)
                else:
                    self.logger.exception("ACPYPE Execution Error: %s", e)
                raise
            except Exception as e:
                self.logger.exception("Unexpected error in LigandTopologyStep: %s", e)
                raise

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
            if "forcefield.itp" in line and not types_inserted:
                new_top.append(line)
                new_top.append("\n; Ligand-specific atomtypes (GAFF2)\n")
                new_top.extend(atomtypes)
                new_top.append("\n")
                types_inserted = True
                continue

            if "[ molecules ]" in line and not itp_included:
                new_top.append("; Include ligand topology\n")
                new_top.append('#include "ligand.itp"\n\n')
                new_top.append(line)
                itp_included = True
                continue

            if line.strip() == "LIG                1":
                continue

            new_top.append(line)
        
        if not any("LIG" in l for l in top_lines[-5:]):
            new_top.append(f"LIG                1\n")
        with open(self.topol_file, 'w') as f:
            f.writelines(new_top)