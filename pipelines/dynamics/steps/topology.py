import subprocess
import os
from tqdm import tqdm
from pdbfixer import PDBFixer
from openmm.app import PDBFile

from ..logger import get_step_logger

class TopologyStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.pdb_input_abs = os.path.abspath(self.config["pdb_input"])
        self.output_gro = "processed.gro" 
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def _repair_pdb(self, input_pdb, output_pdb_path):
        with tqdm(total=4, desc="  └─ Repairing Structure", leave=False) as pbar:
            try:
                fixer = PDBFixer(filename=input_pdb)
                pbar.update(1)
                fixer.findMissingResidues()
                pbar.update(1)
                fixer.findMissingAtoms()
                pbar.update(1)
                fixer.addMissingAtoms()
                pbar.update(1)
                fixer.addMissingHydrogens(7.0)
                pbar.update(1)
                
                with open(output_pdb_path, 'w') as f:
                    PDBFile.writeFile(fixer.topology, fixer.positions, f)
                pbar.update(1)
                
                return True
            except Exception as e:
                self.logger.exception("PDBFixer failed")
                return False

    def run(self):
        work_dir = self.config["work_dir"]
        repaired_filename = "complex_repaired.pdb"
        work_dir_abs = os.path.abspath(work_dir)
        repaired_pdb_abs = os.path.join(work_dir_abs, repaired_filename)
        
        sim_type = self.config.get("sim_type")
        if sim_type in ["3", "4", "5", "6"]:
            command_cmd = [
                self.gmx_bin, "pdb2gmx",
                "-f", self.pdb_input_abs,
                "-o", self.output_gro,
                "-ff", "amber99sb-ildn", 
                "-water", "tip3p",
                "-ignh",
                "-chainsep", "id"
            ]
        else:
            command_cmd = [
                self.gmx_bin, "pdb2gmx",
                "-f", self.pdb_input_abs,
                "-o", self.output_gro,
                "-ff", "amber03", 
                "-water", "tip3p",
                "-ignh"
            ]

        try:
            subprocess.run(command_cmd, check=True, capture_output=True, text=True, cwd=work_dir)
        except subprocess.CalledProcessError as e:
            if "not found in the input file" in e.stderr or "atom" in e.stderr:             
                if self._repair_pdb(self.pdb_input_abs, repaired_pdb_abs):
                    command_cmd[command_cmd.index("-f") + 1] = repaired_filename
                    
                    try:
                        subprocess.run(command_cmd, check=True, capture_output=True, text=True, cwd=work_dir)
                    except subprocess.CalledProcessError as e2:
                        self.logger.exception("Persistent error after repair:\n%s", e2.stderr)
                        raise e2
            else:
                self.logger.exception("Error in pdb2gmx:\n%s", e.stderr)
                raise e