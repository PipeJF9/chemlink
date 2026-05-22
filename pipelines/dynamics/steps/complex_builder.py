import os
from tqdm import tqdm

from ..logger import get_step_logger

class ComplexBuilderStep:
    def __init__(self, config):
        self.config = config
        self.prot_path = os.path.abspath(self.config["pdb_protein"])
        self.partner_path = os.path.abspath(self.config["pdb_partner"])
        self.output_path = os.path.abspath(self.config["pdb_input"])
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def run(self):
        with tqdm(total=2, desc="  └─ Building Molecular Complex", leave=False) as pbar:
            if not os.path.exists(self.config["work_dir"]):
                os.makedirs(self.config["work_dir"])

            try:
                with open(self.output_path, 'w') as f_out:
                    # 1. Process Protein: Force Chain ID 'A'
                    with open(self.prot_path, 'r') as f_prot:
                        for line in f_prot:
                            if line.startswith(("ATOM", "HETATM")):
                                # Replace the character at position 21 (PDB format Chain ID) with 'A'
                                line_mod = line[:21] + 'A' + line[22:]
                                f_out.write(line_mod)
                            elif line.startswith(("TER", "ANISOU")):
                                f_out.write(line)
                    
                    f_out.write("TER\n")
                    pbar.update(1)
                    # 2. Process Partner: Force Chain ID 'B'
                    with open(self.partner_path, 'r') as f_partner:
                        for line in f_partner:
                            if line.startswith(("ATOM", "HETATM")):
                                # Replace the character at position 21 (PDB format Chain ID) with 'B'
                                line_mod = line[:21] + 'B' + line[22:]
                                f_out.write(line_mod)
                            elif line.startswith(("TER", "ANISOU")):
                                f_out.write(line)
                    
                    f_out.write("END\n")
                    pbar.update(1) 
            except Exception as e:
                self.logger.exception("Error during complex assembly")
                raise e