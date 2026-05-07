import logging
import os
import sys
import logging
import subprocess
import shutil
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from tqdm import tqdm

logger = logging.getLogger(__name__)

matplotlib.use('Agg')
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c']


class GMX_MMPBSA_Analyzer:
    def __init__(self, results_dir: str, gmx_bin: str = None):
        self.results_dir = Path(results_dir)
        self.binding_dir = self.results_dir / 'binding_energy_analysis'
        self.gmx_mmpbsa_dir = self.binding_dir / 'gmx_MMPBSA'
        
        self.gmx_mmpbsa_dir.mkdir(parents=True, exist_ok=True)
        self.gmx_bin = gmx_bin
        
        if not self.gmx_bin:
            logger.error("GROMACS binary (gmx_mpi/gmx) not found in system.")
            raise RuntimeError("GROMACS binary not found.")
    
    def detect_groups(self):
        index_file = self.results_dir / 'index.ndx'
        if not index_file.exists():
            logger.error("index.ndx not found.")
            return None, None

        groups = {}
        with open(index_file, 'r') as f:
            group_num = 0
            for line in f:
                if line.strip().startswith('['):
                    name = line.strip().strip('[]').strip()
                    groups[name] = group_num
                    group_num += 1
        
        protein_group = None
        for name, num in groups.items():
            if 'Protein' in name:
                protein_group = num
                break
        
        ligand_group = None
        for name, num in groups.items():
            if any(kw in name for kw in ['LIG', 'Lig', 'ligand', 'Other']) and 'Protein' not in name:
                ligand_group = num
                break
        
        return protein_group, ligand_group
    
    def detect_available_frames(self):
        traj_file = self.results_dir / 'md_center.xtc'
            
        if not traj_file.exists():
            logger.warning(f"Trajectory {traj_file.name} not found, defaulting to 500 frames.")
            return 500
        
        try:
            cmd = [self.gmx_bin, 'check', '-f', str(traj_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            output = result.stdout + result.stderr
            frames = re.findall(r'Step\s+(\d+)', output)
            if frames:
                return int(frames[-1])
            return 1000        
        except Exception as e:
            logger.warning(f"Error detecting frames: {e}")
            return 1000
    
    def find_ligand_files(self):
        acpype_dir = self.results_dir / 'acpype_work'
        acpype_subdirs = list(acpype_dir.glob('*.acpype')) if acpype_dir.exists() else []
        
        if not acpype_subdirs:
            logger.debug("ACPYPE directory not found. Proceeding as Protein-Protein or Standard FF.")
            return None, None
        
        acpype_dir = acpype_subdirs[0]
        
        # Search for MOL2
        mol2_patterns = ['*_gaff2.mol2', '*_gaff.mol2', '*_AC.mol2', 'LIG.mol2']
        mol2_file = None
        for pattern in mol2_patterns:
            found = list(acpype_dir.glob(pattern))
            if found:
                mol2_file = found[0]
                break
        
        if not mol2_file:
            return None, None
        
        # Search for FRCMOD
        base_name = mol2_file.stem
        frcmod_candidates = [
            acpype_dir / f"{base_name}.frcmod",
            acpype_dir / "LIG.frcmod",
            *list(acpype_dir.glob('*.frcmod'))
        ]
            
        frcmod_file = next((f for f in frcmod_candidates if f.exists()), None)
        return mol2_file, frcmod_file
    
    def create_input_file(self, use_gb=True, use_pb=False, n_frames=None):
        input_file = self.gmx_mmpbsa_dir / 'mmpbsa.in'
        
        if n_frames is None:
            n_frames = self.detect_available_frames()
        
        # Auto-interval logic
        if n_frames < 500:
            start_frame = 1
            end_frame = n_frames
            interval = 1
        elif n_frames < 5000:
            start_frame = int(n_frames * 0.2)
            end_frame = n_frames
            interval = max(1, (end_frame - start_frame) // 500)
        else:
            start_frame = int(n_frames * 0.2)
            end_frame = n_frames
            interval = max(5, (end_frame - start_frame) // 1000)

        config = ["&general", f"startframe={start_frame},", f"endframe={end_frame},", f"interval={interval},", "/", ""]

        if use_gb:
            config.extend(["&gb", "igb=5,", "saltcon=0.150,", "/", ""])
        if use_pb:
            config.extend(["&pb", "istrng=0.150,", "/", ""])
        
        with open(input_file, 'w') as f:
            f.write('\n'.join(config))
        
        return input_file
    
    def run_gmx_mmpbsa(self, protein_group: int, ligand_group: int, use_pb: bool = False, n_frames: int = None) -> bool:
        if n_frames is None:
            n_frames = self.detect_available_frames()

        mol2_file, frcmod_file = self.find_ligand_files()
        
        local_mol2 = None
        if mol2_file:
            local_mol2 = self.gmx_mmpbsa_dir / mol2_file.name
            shutil.copy2(mol2_file, local_mol2)
            if frcmod_file:
                shutil.copy2(frcmod_file, self.gmx_mmpbsa_dir / frcmod_file.name)
        
        input_file_path = self.create_input_file(use_gb=True, use_pb=use_pb, n_frames=n_frames)
        input_abs = os.path.abspath(input_file_path) 

        tpr_abs = os.path.abspath(self.results_dir / 'md.tpr')
        ndx_abs = os.path.abspath(self.results_dir / 'index.ndx')
        xtc_abs = os.path.abspath(self.results_dir / 'md_center.xtc')
        top_abs = os.path.abspath(self.results_dir / 'topol.top')
        
        if not os.path.exists(tpr_abs):
            print(f"Error md.tpr not exist: {tpr_abs}")
            return False

        cmd = [
            'gmx_MMPBSA','-O',
            '-i', input_abs,  
            '-cs', tpr_abs,
            '-ci', ndx_abs,
            '-cg', str(protein_group), str(ligand_group),
            '-ct', xtc_abs,
            '-nogui'
        ]

        if local_mol2:
            cmd.extend(['-lm', os.path.abspath(local_mol2)])
        
        if os.path.exists(top_abs):
            cmd.extend(['-cp', top_abs])

        env = os.environ.copy()
        env["GMX_BIN"] = self.gmx_bin

        try:
            subprocess.run(cmd, cwd=str(self.gmx_mmpbsa_dir), check=True, capture_output=True, text=True, env=env)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"gmx_MMPBSA failed: {e.stderr}")
            (self.gmx_mmpbsa_dir / "error_mmpbsa.log").write_text(e.stderr + e.stdout)
            return False
    
    def extract_energies(self):
        energies = {'GB': {}, 'PB': {}}
        dat_file = self.gmx_mmpbsa_dir / 'FINAL_RESULTS_MMPBSA.dat'
        
        if not dat_file.exists():
            logger.warning("FINAL_RESULTS_MMPBSA.dat not found. Cannot extract energies.")
            return energies
        try:
            content = dat_file.read_text()
            sections = {'GB': 'GENERALIZED BORN', 'PB': 'POISSON BOLTZMANN'}
            
            for key, section_name in sections.items():
                if section_name in content:
                    sec = content.split(section_name)[1].split('POISSON BOLTZMANN')[0] if key == 'GB' else content.split(section_name)[1]
                    for line in sec.split('\n'):
                        if any(x in line for x in ['DELTA', 'Δ']) and any(x in line for x in ['TOTAL', 'G binding']):
                            parts = line.split()
                            if len(parts) >= 3:
                                energies[key]['total_mean'] = float(parts[-2])
                                energies[key]['total_std'] = float(parts[-1])
                                break
        except Exception as e:
            logger.warning(f"Energy extraction failed: {e}")
        return energies
    
    def plot_results(self, energies):
        methods, means, stds, colors = [], [], [], []
        
        if energies['GB'].get('total_mean'):
            methods.append('MM-GBSA')
            means.append(energies['GB']['total_mean'])
            stds.append(energies['GB']['total_std'])
            colors.append(COLORS[2])
        
        if energies['PB'].get('total_mean'):
            methods.append('MM-PBSA')
            means.append(energies['PB']['total_mean'])
            stds.append(energies['PB']['total_std'])
            colors.append(COLORS[0])
        
        if not methods: return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        x_pos = np.arange(len(methods))
        bars = ax.bar(x_pos, means, yerr=stds, capsize=10, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std + 0.5, f'{mean:.2f} ± {std:.2f}\nkcal/mol', ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('ΔG_bind (kcal/mol)', fontweight='bold', fontsize=12)
        ax.set_title('Binding Free Energy', fontweight='bold', fontsize=14)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(methods, fontweight='bold', fontsize=11)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.gmx_mmpbsa_dir / 'binding_energy.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_report(self, energies):
        report = ["="*70, "gmx_MMPBSA SUMMARY REPORT", "="*70, "", "RESULTS:", "-"*70]
        found = False
        for method in ['GB', 'PB']:
            if energies[method].get('total_mean'):
                val = energies[method]
                report.append(f"\nMM-{method}SA:")
                report.append(f"  ΔG_bind = {val['total_mean']:.2f} ± {val['total_std']:.2f} kcal/mol")
                found = True
        if not found:
            report.append("\nWarning: No energies extracted. Check FINAL_RESULTS_MMPBSA.dat.")
        
        report.extend(["", "INTERPRETATION:", "-"*70, "• ΔG < 0: Favorable binding", "• ΔG > 0: Unfavorable binding", "", "="*70])
        
        (self.gmx_mmpbsa_dir / 'SUMMARY_REPORT.txt').write_text('\n'.join(report))
    
    def run_analysis(self, use_pb: bool = False, n_frames: int = None) -> bool:
        protein_group, ligand_group = self.detect_groups()
        if protein_group is None or ligand_group is None:
            logger.error("Groups not detected in index file.")
            return False
        
        if not self.run_gmx_mmpbsa(protein_group, ligand_group, use_pb, n_frames):
            return False
        
        with tqdm(total=4, desc="  └─ Binding Energy Analysis", leave=False) as pbar:
            # Step 1: Execution
            if not self.run_gmx_mmpbsa(protein_group, ligand_group, use_pb, n_frames):
                return False
            pbar.update(1)
            
            # Step 2: Extraction
            energies = self.extract_energies()
            pbar.update(1)
            
            # Step 3: Plotting
            self.plot_results(energies)
            pbar.update(1)
            
            # Step 4: Reporting
            self.generate_report(energies)
            pbar.update(1)
        return True

