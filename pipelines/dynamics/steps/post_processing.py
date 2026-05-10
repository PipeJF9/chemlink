import subprocess
import os
from tqdm import tqdm

from ..logger import get_step_logger

class PostProcessingStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        self.final_xtc = os.path.join(self.config["work_dir"], "md_center.xtc")
        self.rel_seg_dir = "segmented_trajectories"
        self.segment_dir = os.path.join(self.config["work_dir"], self.rel_seg_dir)
        self.logger = get_step_logger(__name__, os.path.join(self.config["work_dir"], "simulation.log"))

    def run(self):
        if not os.path.exists(self.segment_dir):
            os.makedirs(self.segment_dir)

        with tqdm(total=4, desc="  └─ Post-Processing & Cleanup", leave=False) as pbar:
            try:

                # Step 1: PBC Correction & Centering
                center_cmd = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md.xtc",
                    "-o", "md_center.xtc",
                    "-center", "-pbc", "mol", "-ur", "compact"
                ]
                subprocess.run(center_cmd, input="1\n0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
                pbar.update(1)

                # Step 2: Final Structure Extraction (PDB)
                sim_time_ps = int(float(self.config["ns_time"]) * 1000)
                dump_pdb_cmd = [
                    self.gmx_bin, "trjconv",
                    "-s", "md.tpr", "-f", "md_center.xtc",
                    "-o", "md.pdb", "-dump", str(sim_time_ps)
                ]
                try:
                    subprocess.run(dump_pdb_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
                except subprocess.CalledProcessError:
                    fallback_cmd = [self.gmx_bin, "trjconv", "-s", "md.tpr", "-f", "md_center.xtc", "-o", "md.pdb", "-dump", "-1"]
                    subprocess.run(fallback_cmd, input="0\n", text=True, check=True, capture_output=True, cwd=self.config["work_dir"])
                pbar.update(1)

                self._generate_smart_index()
                pbar.update(1)
                self._extract_segments(sim_time_ps)
                pbar.update(1)
            except subprocess.CalledProcessError as e:
                self.logger.exception("Post-processing Error (trjconv):\n%s", e.stderr)
                raise e
            except Exception as e:
                self.logger.exception("Unexpected error in PostProcessingStep")
                raise e
            
    def _generate_smart_index(self):
        sim_type = self.config.get("sim_type")

        if sim_type == "2": # Protein-Ligand
            make_ndx_input = "1 | 13\nname 22 Protein_Ligand\nq\n"
        elif sim_type == "4": # Nucleic Acids
            make_ndx_input = "r DNA RNA DR DNA5 DNA3\nname 22 Nucleic_Acid\n1 | 22\nname 23 Complex\nq\n"
        elif sim_type in ["3", "5"]: # Peptide or Protein-Protein
            make_ndx_input = "splitres 0\nq\n" 
        elif sim_type == "6": # Protein-Protein + Ligand
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
        except subprocess.CalledProcessError as e:
            self.logger.exception("Critical error while generating index.ndx:\n%s", e.stderr)
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