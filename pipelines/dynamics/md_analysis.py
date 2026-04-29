
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import argparse
import importlib.util

plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

class GromacsAnalyzer:
    
    def __init__(self, results_dir: str, gmx_bin: str = "gmx"):
        self.results_dir = Path(results_dir)
        self.gmx_bin = gmx_bin
        
        self.has_ligand = (self.results_dir / 'ligand.itp').exists()
        
        self.analysis_dirs = {
            'energia': self.results_dir / 'analisis_energia',
            'rmsd': self.results_dir / 'analisis_rmsd',
            'rmsf': self.results_dir / 'analisis_rmsf',
            'estructural': self.results_dir / 'analisis_estructural',
            'sasa': self.results_dir / 'analisis_sasa',
            'hbonds': self.results_dir / 'analisis_hbonds',
            'graficas': self.results_dir / 'graficas'
        }
    
    def _read_xvg(self, filename: str) -> Optional[np.ndarray]:
        """Lee archivos XVG"""
        try:
            data = []
            with open(filename, 'r') as f:
                for line in f:
                    if not line.startswith(('#', '@')):
                        try:
                            data.append([float(x) for x in line.strip().split()])
                        except ValueError:
                            continue
            return np.array(data) if data else None
        except Exception as e:
            print(f"⚠️  Error leyendo {filename}: {e}")
            return None
    
    def _run_gmx_command(self, cmd: List[str], stdin_input: str = "") -> Tuple[bool, str]:
        """Ejecuta comando GROMACS"""
        try:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, cwd=str(self.results_dir))
            stdout, stderr = process.communicate(input=stdin_input)
            return process.returncode == 0, stdout
        except Exception as e:
            print(f"❌ Error: {e}")
            return False, ""
    
    def analyze_energy(self):
        """Análisis de energía"""
        print("\n" + "="*60)
        print("  ANALIZANDO ENERGÍAS DEL SISTEMA")
        print("="*60)
        
        analyses = [
            ('em.edr', 'potential.xvg', '11\n0\n'),
            ('nvt.edr', 'temperature.xvg', '16\n0\n'),
            ('npt.edr', 'pressure.xvg', '17\n0\n'),
            ('md_1.edr', 'energy_total.xvg', '10\n0\n'),
            ('md_1.edr', 'energy_potential.xvg', '11\n0\n'),
            ('md_1.edr', 'energy_kinetic.xvg', '12\n0\n'),
            ('md_1.edr', 'temperature_md.xvg', '16\n0\n'),
            ('md_1.edr', 'volume.xvg', '21\n0\n'),
            ('md_1.edr', 'density.xvg', '22\n0\n'),
        ]
        
        for edr, out, sel in analyses:
            edr_path = self.results_dir / edr
            if edr_path.exists():
                # El comando se ejecuta dentro de results_dir, así que pasamos solo el nombre del edr
                cmd = [self.gmx_bin, 'energy', '-f', edr,
                       '-o', str(self.analysis_dirs['energia'] / out)]
                self._run_gmx_command(cmd, sel)
            else:
                print(f"⚠️  Saltando {edr}: Archivo no encontrado")
    
    def analyze_rmsd(self):
        print("\n" + "="*80)
        print("PASO 8: Análisis de RMSD")
        print("="*80)
        
        analyses = [('4\n4\n', 'rmsd_backbone.xvg'), ('3\n3\n', 'rmsd_calpha.xvg'), 
                   ('1\n1\n', 'rmsd_protein.xvg')]
        
        for sel, out in analyses:
            cmd = [self.gmx_bin, 'rms', '-s', str(self.results_dir / 'em.tpr'),
                   '-f', str(self.results_dir / 'md_1_center.xtc'),
                   '-n', str(self.results_dir / 'index.ndx'),
                   '-tu', 'ns', '-o', str(self.analysis_dirs['rmsd'] / out)]
            self._run_gmx_command(cmd, sel)
        
        if self.has_ligand:
            for sel, out in [('1\n13\n', 'rmsd_ligand_fit_protein.xvg'),
                            ('13\n13\n', 'rmsd_ligand_fit_self.xvg'),
                            ('1\n22\n', 'rmsd_complex.xvg')]:
                cmd = [self.gmx_bin, 'rms', '-s', str(self.results_dir / 'em.tpr'),
                       '-f', str(self.results_dir / 'md_1_center.xtc'),
                       '-n', str(self.results_dir / 'index.ndx'),
                       '-tu', 'ns', '-o', str(self.analysis_dirs['rmsd'] / out)]
                self._run_gmx_command(cmd, sel)
        
        print("✅ Completado")
    
    def analyze_rmsf(self):
        print("\n" + "="*80)
        print("PASO 9: Análisis de RMSF")
        print("="*80)
        
        for sel, out in [('3\n', 'rmsf_calpha'), ('4\n', 'rmsf_backbone'), ('1\n', 'rmsf_protein')]:
            cmd = [self.gmx_bin, 'rmsf', '-s', str(self.results_dir / 'md_1.tpr'),
                   '-f', str(self.results_dir / 'md_1_center.xtc'),
                   '-o', str(self.analysis_dirs['rmsf'] / f'{out}.xvg'),
                   '-n', str(self.results_dir / 'index.ndx'),
                   '-ox', str(self.analysis_dirs['rmsf'] / f'{out}_avg.pdb'),
                   '-oq', str(self.analysis_dirs['rmsf'] / f'bfactors_{out.split("_")[1]}.pdb'),
                   '-res']
            self._run_gmx_command(cmd, sel)
        
        if self.has_ligand:
            cmd = [self.gmx_bin, 'rmsf', '-s', str(self.results_dir / 'md_1.tpr'),
                   '-f', str(self.results_dir / 'md_1_center.xtc'),
                   '-o', str(self.analysis_dirs['rmsf'] / 'rmsf_ligand.xvg'),
                   '-n', str(self.results_dir / 'index.ndx'),
                   '-ox', str(self.analysis_dirs['rmsf'] / 'rmsf_ligand_avg.pdb'),
                   '-oq', str(self.analysis_dirs['rmsf'] / 'bfactors_ligand.pdb'), '-res']
            self._run_gmx_command(cmd, '13\n')
        
        print("✅ Completado")
    
    def analyze_gyration(self):
        print("\n" + "="*80)
        print("PASO 10: Radio de Giro")
        print("="*80)
        
        for sel, out in [('1\n', 'gyrate_protein.xvg'), ('4\n', 'gyrate_backbone.xvg'), 
                        ('3\n', 'gyrate_calpha.xvg')]:
            cmd = [self.gmx_bin, 'gyrate', '-f', str(self.results_dir / 'md_1_center.xtc'),
                   '-s', str(self.results_dir / 'md_1.tpr'),
                   '-o', str(self.analysis_dirs['estructural'] / out),
                   '-n', str(self.results_dir / 'index.ndx')]
            self._run_gmx_command(cmd, sel)
        
        print("✅ Completado")
    
    def analyze_sasa(self):
        print("\n" + "="*80)
        print("PASO 11: Análisis de SASA")
        print("="*80)
        
        cmd = [self.gmx_bin, 'sasa', '-f', str(self.results_dir / 'md_1_center.xtc'),
               '-s', str(self.results_dir / 'md_1.tpr'),
               '-o', str(self.analysis_dirs['sasa'] / 'sasa_protein.xvg'),
               '-or', str(self.analysis_dirs['sasa'] / 'sasa_residue.xvg'),
               '-oa', str(self.analysis_dirs['sasa'] / 'sasa_atom.xvg'),
               '-n', str(self.results_dir / 'index.ndx')]
        self._run_gmx_command(cmd, '1\n')
        
        if self.has_ligand:
            for sel, out in [('13\n', 'sasa_ligand.xvg'), ('22\n', 'sasa_complex.xvg')]:
                cmd = [self.gmx_bin, 'sasa', '-f', str(self.results_dir / 'md_1_center.xtc'),
                       '-s', str(self.results_dir / 'md_1.tpr'),
                       '-o', str(self.analysis_dirs['sasa'] / out),
                       '-n', str(self.results_dir / 'index.ndx')]
                self._run_gmx_command(cmd, sel)
        
        print("✅ Completado")
    
    def analyze_hbonds_detailed(self):
        """Análisis DETALLADO de puentes de hidrógeno"""
        print("\n" + "="*80)
        print("PASO 12: Análisis DETALLADO de H-bonds")
        print("="*80)
        
        hbonds_dir = self.analysis_dirs['hbonds']
        
        cmd = [self.gmx_bin, 'hbond', '-f', str(self.results_dir / 'md_1_center.xtc'),
               '-s', str(self.results_dir / 'md_1.tpr'),
               '-num', str(hbonds_dir / 'hbond_protein_intra.xvg'),
               '-n', str(self.results_dir / 'index.ndx')]
        self._run_gmx_command(cmd, '1\n1\n')
        
        if self.has_ligand:
            cmd = [self.gmx_bin, 'hbond', '-f', str(self.results_dir / 'md_1_center.xtc'),
                   '-s', str(self.results_dir / 'md_1.tpr'),
                   '-num', str(hbonds_dir / 'hbond_prot_lig.xvg'),
                   '-dist', str(hbonds_dir / 'hbond_prot_lig_dist.xvg'),
                   '-ang', str(hbonds_dir / 'hbond_prot_lig_angle.xvg'),
                   '-hbn', str(hbonds_dir / 'hbond_prot_lig.ndx'),
                   '-hbm', str(hbonds_dir / 'hbond_matrix.xpm'),
                   '-n', str(self.results_dir / 'index.ndx')]
            success, _ = self._run_gmx_command(cmd, '1\n13\n')
            
            if success:
                self._extract_hbond_residues(hbonds_dir)
            self._convert_hbond_matrix(hbonds_dir)
        
        print("✅ Análisis de H-bonds completado")
    
    def _extract_hbond_residues(self, hbonds_dir: Path):
        """Extrae información de residuos involucrados en H-bonds"""
        ndx_file = hbonds_dir / 'hbond_prot_lig.ndx'
        if not ndx_file.exists():
            return
        
        try:
            with open(ndx_file, 'r') as f:
                lines = f.readlines()
            
            hbond_groups = {}
            current_group = None
            
            for line in lines:
                if line.startswith('[') and line.endswith(']\n'):
                    current_group = line.strip()[1:-1].strip()
                    hbond_groups[current_group] = []
                elif current_group and line.strip():
                    hbond_groups[current_group].extend([int(x) for x in line.split() if x.isdigit()])
            
            summary = ["="*80, "RESIDUOS FORMANDO H-BONDS PROTEÍNA-LIGANDO", "="*80,
                      f"\nTotal de grupos encontrados: {len(hbond_groups)}\n"]
            
            for group, atoms in hbond_groups.items():
                summary.extend([f"{group}:", f"  Átomos: {len(atoms)}",
                              f"  IDs: {atoms[:10]}..." if len(atoms) > 10 else f"  IDs: {atoms}", ""])
            
            with open(hbonds_dir / 'hbond_residues_summary.txt', 'w') as f:
                f.write('\n'.join(summary))
            
        except Exception as e:
            print(f"    ⚠️  Error extrayendo residuos: {e}")
    
    def _convert_hbond_matrix(self, hbonds_dir: Path):
        """Convierte matriz XPM de H-bonds a EPS"""
        xpm_file = hbonds_dir / 'hbond_matrix.xpm'
        if xpm_file.exists():
            cmd = [self.gmx_bin, 'xpm2ps', '-f', str(xpm_file),
                   '-o', str(hbonds_dir / 'hbond_matrix.eps')]
            self._run_gmx_command(cmd, '\n')
    
    def plot_time_series(self):
        """Genera todas las gráficas"""
        print("\n" + "="*80)
        print("GENERACIÓN DE GRÁFICAS")
        print("="*80)
        
        graficas_dir = self.analysis_dirs['graficas']
        
        self._plot_energy_analysis(graficas_dir)
        self._plot_rmsd_analysis(graficas_dir)
        self._plot_rmsf_analysis(graficas_dir)
        self._plot_structural_properties(graficas_dir)
        self._plot_sasa_analysis(graficas_dir)
        self._plot_hbonds_analysis(graficas_dir)
        self._plot_hbonds_detailed(graficas_dir)
        self._create_dashboard(graficas_dir)
        
        print("✅ Todas las gráficas generadas")
    
    def _plot_hbonds_detailed(self, output_dir: Path):
        """Grafica análisis detallado de H-bonds"""
        if not self.has_ligand:
            return
        
        hbonds_dir = self.analysis_dirs['hbonds']
        
        if not (hbonds_dir / 'hbond_prot_lig.xvg').exists():
            print("  ⚠️  Archivos de H-bonds proteína-ligando no encontrados, omitiendo gráfica detallada")
            return
        
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Análisis Detallado de Puentes de Hidrógeno Proteína-Ligando', 
                        fontsize=14, fontweight='bold')
            
            # H-bonds vs tiempo
            hbond_file = hbonds_dir / 'hbond_prot_lig.xvg'
            if hbond_file.exists():
                data = self._read_xvg(hbond_file)
                if data is not None:
                    axes[0, 0].plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1)
                    axes[0, 0].axhline(y=np.mean(data[:, 1]), color='r', linestyle='--',
                                     label=f'Promedio: {np.mean(data[:, 1]):.1f}')
                    axes[0, 0].set_xlabel('Tiempo (ps)', fontweight='bold')
                    axes[0, 0].set_ylabel('Número de H-bonds', fontweight='bold')
                    axes[0, 0].set_title('H-bonds vs Tiempo', fontweight='bold')
                    axes[0, 0].legend()
                    axes[0, 0].grid(True, alpha=0.3)
            
            # Distancias
            dist_file = hbonds_dir / 'hbond_prot_lig_dist.xvg'
            if dist_file.exists():
                data = self._read_xvg(dist_file)
                if data is not None and data.shape[1] > 1:
                    distances = data[:, 1:].flatten()
                    distances = distances[distances > 0]
                    axes[0, 1].hist(distances, bins=50, color=COLORS[1], alpha=0.7, edgecolor='black')
                    axes[0, 1].axvline(x=np.mean(distances), color='r', linestyle='--', linewidth=2,
                                      label=f'Media: {np.mean(distances):.3f} nm')
                    axes[0, 1].set_xlabel('Distancia (nm)', fontweight='bold')
                    axes[0, 1].set_ylabel('Frecuencia', fontweight='bold')
                    axes[0, 1].set_title('Distribución de Distancias H-bond', fontweight='bold')
                    axes[0, 1].legend()
                    axes[0, 1].grid(True, alpha=0.3)
            
            # Ángulos
            angle_file = hbonds_dir / 'hbond_prot_lig_angle.xvg'
            if angle_file.exists():
                data = self._read_xvg(angle_file)
                if data is not None and data.shape[1] > 1:
                    angles = data[:, 1:].flatten()
                    angles = angles[angles > 0]
                    axes[1, 0].hist(angles, bins=50, color=COLORS[2], alpha=0.7, edgecolor='black')
                    axes[1, 0].axvline(x=np.mean(angles), color='r', linestyle='--', linewidth=2,
                                      label=f'Media: {np.mean(angles):.1f}°')
                    axes[1, 0].set_xlabel('Ángulo (grados)', fontweight='bold')
                    axes[1, 0].set_ylabel('Frecuencia', fontweight='bold')
                    axes[1, 0].set_title('Distribución de Ángulos H-bond', fontweight='bold')
                    axes[1, 0].legend()
                    axes[1, 0].grid(True, alpha=0.3)
            
            # Comparación
            for filename, label, color in [('hbond_prot_lig.xvg', 'Proteína-Ligando', COLORS[0]),
                                          ('hbond_protein_intra.xvg', 'Proteína (intra)', COLORS[3])]:
                filepath = hbonds_dir / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        axes[1, 1].plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color, alpha=0.7)
            
            axes[1, 1].set_xlabel('Tiempo (ps)', fontweight='bold')
            axes[1, 1].set_ylabel('Número de H-bonds', fontweight='bold')
            axes[1, 1].set_title('Comparación de H-bonds', fontweight='bold')
            axes[1, 1].legend()
            axes[1, 1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(output_dir / 'hbonds_detailed.png', dpi=300, bbox_inches='tight')
            plt.close()
            
        except Exception as e:
            print(f"    ⚠️  Error: {e}")
    
    def _plot_energy_analysis(self, output_dir: Path):
        """Grafica energías"""
        print("  📈 Graficando energías...")
        
        fig, axes = plt.subplots(3, 2, figsize=(15, 12))
        fig.suptitle('Análisis Energético de la Simulación MD', fontsize=16, fontweight='bold')
        
        plots = [('energy_potential.xvg', 'Energía Potencial', 'kJ/mol', axes[0, 0]),
                ('energy_kinetic.xvg', 'Energía Cinética', 'kJ/mol', axes[0, 1]),
                ('energy_total.xvg', 'Energía Total', 'kJ/mol', axes[1, 0]),
                ('temperature_md.xvg', 'Temperatura', 'K', axes[1, 1]),
                ('density.xvg', 'Densidad', 'kg/m³', axes[2, 0]),
                ('volume.xvg', 'Volumen', 'nm³', axes[2, 1])]
        
        for filename, title, ylabel, ax in plots:
            filepath = self.analysis_dirs['energia'] / filename
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None:
                    ax.plot(data[:, 0], data[:, 1], linewidth=1.5, color=COLORS[0])
                    ax.set_xlabel('Tiempo (ps)', fontweight='bold')
                    ax.set_ylabel(ylabel, fontweight='bold')
                    ax.set_title(title, fontweight='bold')
                    ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'energia_tiempo.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_rmsd_analysis(self, output_dir: Path):
        """Grafica RMSD"""
        print("  📈 Graficando RMSD...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        files = [('rmsd_backbone.xvg', 'Backbone', COLORS[0]),
                ('rmsd_calpha.xvg', 'C-alpha', COLORS[1]),
                ('rmsd_protein.xvg', 'Proteína completa', COLORS[2])]
        
        if self.has_ligand:
            files.extend([('rmsd_ligand_fit_protein.xvg', 'Ligando (fit proteína)', COLORS[3]),
                         ('rmsd_complex.xvg', 'Complejo', COLORS[4])])
        
        for filename, label, color in files:
            filepath = self.analysis_dirs['rmsd'] / filename
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None:
                    ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
        
        ax.set_xlabel('Tiempo (ns)', fontsize=12, fontweight='bold')
        ax.set_ylabel('RMSD (nm)', fontsize=12, fontweight='bold')
        ax.set_title('RMSD vs Tiempo', fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'rmsd_tiempo.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_rmsf_analysis(self, output_dir: Path):
        """Grafica RMSF"""
        print("  📈 Graficando RMSF...")
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for filename, label, color in [('rmsf_calpha.xvg', 'C-alpha', COLORS[0]),
                                       ('rmsf_backbone.xvg', 'Backbone', COLORS[1])]:
            data = self._read_xvg(self.analysis_dirs['rmsf'] / filename)
            if data is not None:
                ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
        
        ax.set_xlabel('Número de Residuo', fontsize=12, fontweight='bold')
        ax.set_ylabel('RMSF (nm)', fontsize=12, fontweight='bold')
        ax.set_title('RMSF por Residuo', fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'rmsf_residuos.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_structural_properties(self, output_dir: Path):
        """Grafica propiedades estructurales"""
        print("  📈 Graficando propiedades estructurales...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        for filename, label, color in [('gyrate_protein.xvg', 'Proteína completa', COLORS[0]),
                                       ('gyrate_backbone.xvg', 'Backbone', COLORS[1]),
                                       ('gyrate_calpha.xvg', 'C-alpha', COLORS[2])]:
            data = self._read_xvg(self.analysis_dirs['estructural'] / filename)
            if data is not None:
                ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
        
        ax.set_xlabel('Tiempo (ps)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Radio de Giro (nm)', fontsize=12, fontweight='bold')
        ax.set_title('Radio de Giro vs Tiempo', fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'gyrate_tiempo.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_sasa_analysis(self, output_dir: Path):
        """Grafica SASA"""
        print("  📈 Graficando SASA...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        files = [('sasa_protein.xvg', 'Proteína', COLORS[0])]
        if self.has_ligand:
            files.extend([('sasa_ligand.xvg', 'Ligando', COLORS[1]),
                         ('sasa_complex.xvg', 'Complejo', COLORS[2])])
        
        for filename, label, color in files:
            filepath = self.analysis_dirs['sasa'] / filename
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None:
                    ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
        
        ax.set_xlabel('Tiempo (ps)', fontsize=12, fontweight='bold')
        ax.set_ylabel('SASA (nm²)', fontsize=12, fontweight='bold')
        ax.set_title('Área Accesible al Solvente vs Tiempo', fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'sasa_tiempo.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _plot_hbonds_analysis(self, output_dir: Path):
        """Grafica H-bonds básicos"""
        print("  📈 Graficando H-bonds...")
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        files = [('hbond_protein_intra.xvg', 'Proteína (intra)', COLORS[0])]
        if self.has_ligand:
            files.append(('hbond_prot_lig.xvg', 'Proteína-Ligando', COLORS[1]))
        
        for filename, label, color in files:
            filepath = self.analysis_dirs['hbonds'] / filename
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None:
                    ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
        
        ax.set_xlabel('Tiempo (ps)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Número de H-bonds', fontsize=12, fontweight='bold')
        ax.set_title('Puentes de Hidrógeno vs Tiempo', fontsize=14, fontweight='bold')
        ax.legend(loc='best', frameon=True, shadow=True)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'hbonds_tiempo.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _create_dashboard(self, output_dir: Path):
        """Dashboard resumen"""
        print("  📊 Creando dashboard...")
        
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        plots = [(gs[0, 0], 'rmsd', 'rmsd_backbone.xvg', 'RMSD Backbone', 'Tiempo (ns)', 'RMSD (nm)'),
                (gs[0, 1], 'energia', 'energy_potential.xvg', 'Energía Potencial', 'Tiempo (ps)', 'Energía (kJ/mol)'),
                (gs[0, 2], 'energia', 'temperature_md.xvg', 'Temperatura', 'Tiempo (ps)', 'Temperatura (K)'),
                (gs[1, 0], 'estructural', 'gyrate_protein.xvg', 'Radio de Giro', 'Tiempo (ps)', 'Rg (nm)'),
                (gs[1, 1], 'sasa', 'sasa_protein.xvg', 'SASA', 'Tiempo (ps)', 'SASA (nm²)'),
                (gs[1, 2], 'hbonds', 'hbond_protein_intra.xvg', 'H-bonds Intramoleculares', 'Tiempo (ps)', 'Número'),
                (gs[2, 2], 'energia', 'density.xvg', 'Densidad', 'Tiempo (ps)', 'kg/m³')]
        
        for pos, dir_key, filename, title, xlabel, ylabel in plots:
            ax = fig.add_subplot(pos)
            data = self._read_xvg(self.analysis_dirs[dir_key] / filename)
            if data is not None:
                ax.plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1.5)
                ax.set_title(title, fontweight='bold', fontsize=10)
                ax.set_xlabel(xlabel, fontsize=8)
                ax.set_ylabel(ylabel, fontsize=8)
                ax.grid(True, alpha=0.3)
        
        ax_rmsf = fig.add_subplot(gs[2, :2])
        data = self._read_xvg(self.analysis_dirs['rmsf'] / 'rmsf_calpha.xvg')
        if data is not None:
            ax_rmsf.plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1.5)
            ax_rmsf.set_title('RMSF por Residuo', fontweight='bold', fontsize=10)
            ax_rmsf.set_xlabel('Residuo', fontsize=8)
            ax_rmsf.set_ylabel('RMSF (nm)', fontsize=8)
            ax_rmsf.grid(True, alpha=0.3)
        
        fig.suptitle('Dashboard de Análisis MD - Resumen General', fontsize=16, fontweight='bold', y=0.995)
        plt.savefig(output_dir / 'dashboard_resumen.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def generate_summary_report(self):
        """Genera reporte estadístico"""
        print("\n" + "="*80)
        print("GENERANDO RESUMEN ESTADÍSTICO")
        print("="*80)
        
        report = ["="*80, "RESUMEN COMPLETO DE ANÁLISIS DE DINÁMICA MOLECULAR", "="*80, "",
                 f"Sistema: {'Proteína-Ligando' if self.has_ligand else 'Proteína'}",
                 f"Directorio: {self.results_dir}", ""]
        
        def add_stats(title, filepath, unit=''):
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None and len(data) > 0:
                    values = data[:, 1]
                    report.extend([f"{title}:",
                                 f"  Promedio: {np.mean(values):.3f} ± {np.std(values):.3f} {unit}",
                                 f"  Mín-Máx: {np.min(values):.3f} - {np.max(values):.3f} {unit}", ""])
        
        sections = [
            ("1. ANÁLISIS DE RMSD", [
                ("RMSD Backbone", 'rmsd/rmsd_backbone.xvg', 'nm'),
                ("RMSD C-alpha", 'rmsd/rmsd_calpha.xvg', 'nm'),
                ("RMSD Proteína", 'rmsd/rmsd_protein.xvg', 'nm')]),
            ("2. ANÁLISIS DE RMSF", [("RMSF C-alpha", 'rmsf/rmsf_calpha.xvg', 'nm')]),
            ("3. PROPIEDADES ESTRUCTURALES", [("Radio de Giro", 'estructural/gyrate_protein.xvg', 'nm')]),
            ("4. ANÁLISIS DE SASA", [("SASA Proteína", 'sasa/sasa_protein.xvg', 'nm²')]),
            ("5. ANÁLISIS DE ENERGÍA", [
                ("Energía Potencial", 'energia/energy_potential.xvg', 'kJ/mol'),
                ("Energía Cinética", 'energia/energy_kinetic.xvg', 'kJ/mol'),
                ("Energía Total", 'energia/energy_total.xvg', 'kJ/mol'),
                ("Temperatura", 'energia/temperature_md.xvg', 'K'),
                ("Densidad", 'energia/density.xvg', 'kg/m³'),
                ("Volumen", 'energia/volume.xvg', 'nm³')]),
            ("6. PUENTES DE HIDRÓGENO", [("H-bonds Intramoleculares", 'hbonds/hbond_protein_intra.xvg', 'enlaces')])
        ]
        
        for section_title, stats_list in sections:
            report.extend([section_title, "-" * 80])
            for stat_title, filepath, unit in stats_list:
                add_stats(stat_title, self.results_dir / filepath, unit)
        
        if self.has_ligand:
            report.extend(["7. PUENTES DE HIDRÓGENO DETALLADOS (PROTEÍNA-LIGANDO)", "-" * 80])
            
            dist_file = self.analysis_dirs['hbonds'] / 'hbond_prot_lig_dist.xvg'
            if dist_file.exists():
                data = self._read_xvg(dist_file)
                if data is not None and data.shape[1] > 1:
                    distances = data[:, 1:].flatten()
                    distances = distances[distances > 0]
                    report.append(f"Distancia promedio H-bond: {np.mean(distances):.3f} ± {np.std(distances):.3f} nm")
            
            angle_file = self.analysis_dirs['hbonds'] / 'hbond_prot_lig_angle.xvg'
            if angle_file.exists():
                data = self._read_xvg(angle_file)
                if data is not None and data.shape[1] > 1:
                    angles = data[:, 1:].flatten()
                    angles = angles[angles > 0]
                    report.append(f"Ángulo promedio H-bond: {np.mean(angles):.1f} ± {np.std(angles):.1f}°")
            report.append("")
        
        report.extend(["="*80, "FIN DEL RESUMEN", "="*80])
        
        report_file = self.results_dir / 'RESUMEN_ANALISIS.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print('\n'.join(report))
        print(f"\n✅ Resumen guardado en: {report_file}")

    def detect_protein_protein(self) -> (bool, list):
        """Detecta si la simulación es probablemente proteína-proteína.

        Devuelve (True, [chain_ids]) si encuentra >1 cadenas en `md_1.pdb`
        y no hay ligando. En caso contrario devuelve (False, []).
        """
        if self.has_ligand:
            return False, []

        pdb_file = self.results_dir / 'md_1.pdb'
        if not pdb_file.exists():
            return False, []

        chains = set()
        try:
            with open(pdb_file, 'r') as f:
                for l in f:
                    if l.startswith(('ATOM', 'HETATM')) and len(l) >= 22:
                        chains.add(l[21])
        except Exception:
            return False, []

        # Filtrar entradas vacías
        chains = [c for c in chains if c.strip()]
        if len(chains) > 1:
            return True, sorted(chains)
        return False, []
    
    def run_full_analysis(self):
        """Ejecuta análisis COMPLETO con generación GARANTIZADA del reporte PDF"""
        print("\n" + "="*80)
        print("INICIANDO ANÁLISIS COMPLETO DE DINÁMICA MOLECULAR")
        print("="*80)
        print(f"Directorio: {self.results_dir}")
        print(f"Sistema: {'Proteína-Ligando' if self.has_ligand else 'Proteína'}")
        print("="*80)
        
        # Análisis básicos
        self.analyze_energy()
        self.analyze_rmsd()
        self.analyze_rmsf()
        self.analyze_gyration()
        self.analyze_sasa()
        self.analyze_hbonds_detailed()
        self.plot_time_series()
        self.generate_summary_report()
        
        print("\n" + "="*80)
        print("✅ ANÁLISIS COMPLETO FINALIZADO")
        print("="*80)
        print(f"\nResultados guardados en:")
        print(f"  📊 Gráficas: {self.analysis_dirs['graficas']}")
        print(f"  📄 Resumen: {self.results_dir / 'RESUMEN_ANALISIS.txt'}")
        
        if self.has_ligand:
            print(f"\n🆕 ANÁLISIS DETALLADOS:")
            print(f"  🔗 H-bonds detallados: {self.analysis_dirs['hbonds']}")
        print("="*80)
        
        # Análisis avanzados opcionales
        self.run_dccm_analysis_automatically()

        # Detectar si es probablemente proteína-proteína y marcarlo
        is_pp, chains = self.detect_protein_protein()
        if is_pp:
            try:
                sim_file = self.results_dir / 'SIMULATION_TYPE.txt'
                sim_file.write_text('Proteína-Proteína\n')
                # Añadir al resumen
                resumen = self.results_dir / 'RESUMEN_ANALISIS.txt'
                if resumen.exists():
                    with open(resumen, 'a', encoding='utf-8') as f:
                        f.write('\n')
                        f.write('DETECCIÓN AUTOMÁTICA: Sistema identificado como Proteína-Proteína\n')
                        f.write(f'  Cadenas detectadas: {",".join(chains)}\n')
                print(f"✅ Marcado como Proteína-Proteína (cadenas: {','.join(chains)})")
            except Exception as e:
                print(f"⚠️  No se pudo escribir marcador Proteína-Proteína: {e}")

        # ======================================================================
        # Reporte PDF - DESHABILITADO (no disponible en esta versión)
        # ======================================================================
        # Comentado: generate_pdf_report_final() no disponible
        pass
    
    def run_dccm_analysis_automatically(self):
        """Ejecuta automáticamente el análisis DCCM sin preguntar"""
        print("\n" + "="*80)
        print("🔬 INICIANDO ANÁLISIS DCCM AUTOMÁTICAMENTE")
        print("="*80)
        
        dccm_script_locations = [
            Path("/home/ChemFusion/funciones/dccm_analysis.py"),
            self.results_dir.parent / "dccm_analysis.py",
            Path(__file__).parent / "dccm_analysis.py",
        ]
        
        dccm_script = None
        for location in dccm_script_locations:
            if location.exists():
                dccm_script = location
                print(f"✅ Script DCCM encontrado: {dccm_script}")
                break
        
        if dccm_script is None:
            print("⚠️  Script dccm_analysis.py no encontrado")
            print("    Búsqueda realizada en:")
            for loc in dccm_script_locations:
                print(f"      - {loc}")
            print("\n    El análisis DCCM debe ejecutarse manualmente:")
            print(f"    python3 dccm_analysis.py -d {self.results_dir} -g {self.gmx_bin}")
            return
        
        required_files = ['md_1_center.xtc', 'md_1.tpr', 'index.ndx']
        missing_files = []
        for filename in required_files:
            if not (self.results_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            print(f"⚠️  Archivos requeridos faltantes: {', '.join(missing_files)}")
            print("    El análisis DCCM no puede ejecutarse automáticamente")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("dccm_analysis", dccm_script)
            dccm_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dccm_module)
            
            print("\n📊 Ejecutando análisis DCCM...")
            print("    (Esto puede tomar varios minutos dependiendo del tamaño de la proteína)")
            
            dccm_analyzer = dccm_module.DCCMAnalyzer(
                results_dir=str(self.results_dir),
                gmx_bin=self.gmx_bin
            )
            
            success = dccm_analyzer.run_full_analysis(
                selection="C-alpha",
                max_residues=2000,
                max_frames=None
            )
            
            if success:
                print("\n" + "="*80)
                print("✅ ANÁLISIS DCCM COMPLETADO EXITOSAMENTE")
                print("="*80)
                dccm_dir = self.results_dir / 'analisis_dccm'
                print(f"\n📊 Resultados DCCM en: {dccm_dir}")
                print("    Archivos generados:")
                print("      - dccm_matrix.dat (matriz numérica)")
                print("      - dccm_matrix.png (visualización completa)")
                print("      - dccm_region_*.png (visualizaciones regionales)")
                print("      - dccm_statistics.txt (estadísticas detalladas)")
                print("="*80)
                
                # Ejecutar MM-PBSA si hay ligando
                self.run_mmpbsa_analysis_automatically()
            else:
                print("\n⚠️  El análisis DCCM encontró problemas")
                print("    Revisa los mensajes arriba para más detalles")
        
        except Exception as e:
            print(f"\n❌ Error ejecutando análisis DCCM: {e}")
            print("    El análisis puede ejecutarse manualmente con:")
            print(f"    python3 {dccm_script} -d {self.results_dir} -g {self.gmx_bin}")
            import traceback
            traceback.print_exc()
    
    def run_mmpbsa_analysis_automatically(self):
        """Ejecuta automáticamente el análisis MM-PBSA/MM-GBSA sin preguntar"""
        print("\n" + "="*80)
        print("🧪 INICIANDO ANÁLISIS MM-PBSA/MM-GBSA AUTOMÁTICAMENTE")
        print("="*80)
        
        if not self.has_ligand:
            print("\n⚠️  Sistema sin ligando detectado")
            print("    El análisis MM-PBSA/MM-GBSA requiere un sistema proteína-ligando")
            print("    Omitiendo este análisis...")
            return
        
        mmpbsa_script_locations = [
            Path("/home/ChemFusion/funciones/mmpbsa_analysis.py"),
            self.results_dir.parent / "mmpbsa_analysis.py",
            Path(__file__).parent / "mmpbsa_analysis.py",
        ]
        
        mmpbsa_script = None
        for location in mmpbsa_script_locations:
            if location.exists():
                mmpbsa_script = location
                print(f"✅ Script MM-PBSA/MM-GBSA encontrado: {mmpbsa_script}")
                break
        
        if mmpbsa_script is None:
            print("⚠️  Script mmpbsa_analysis.py no encontrado")
            print("    Búsqueda realizada en:")
            for loc in mmpbsa_script_locations:
                print(f"      - {loc}")
            print("\n    El análisis MM-PBSA/MM-GBSA debe ejecutarse manualmente:")
            print(f"    python3 mmpbsa_analysis.py -d {self.results_dir}")
            return
        
        required_files = ['md_1_center.xtc', 'md_1.tpr', 'index.ndx']
        missing_files = []
        for filename in required_files:
            if not (self.results_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            print(f"⚠️  Archivos requeridos faltantes: {', '.join(missing_files)}")
            print("    El análisis MM-PBSA/MM-GBSA no puede ejecutarse automáticamente")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("mmpbsa_analysis", mmpbsa_script)
            mmpbsa_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mmpbsa_module)
            
            print("\n📊 Ejecutando análisis MM-PBSA/MM-GBSA...")
            print("    (Calculando energía libre de unión ΔG...)")
            print("    (Esto puede tomar varios minutos)")
            
            mmpbsa_analyzer = mmpbsa_module.GMX_MMPBSA_Analyzer(
                results_dir=str(self.results_dir),
                use_mpi=True,  # ← CAMBIO: Activar MPI por defecto
                n_cores=6
            )
            
            # ← CORRECCIÓN: Eliminar argumento generate_pdf inexistente
            success = mmpbsa_analyzer.run_analysis(use_pb=True)
            
            if success:
                print("\n" + "="*80)
                print("✅ ANÁLISIS MM-PBSA/MM-GBSA COMPLETADO EXITOSAMENTE")
                print("="*80)
                binding_dir = self.results_dir / 'analisis_binding_energy' / 'gmx_MMPBSA'
                print(f"\n📊 Resultados en: {binding_dir}")
                print("    Archivos generados:")
                print("      📊 binding_energy.png (gráfica de energías)")
                print("      📄 SUMMARY_REPORT.txt (reporte completo)")
                print("      📈 FINAL_RESULTS_MMPBSA.dat (resultados detallados)")
                print("="*80)
            else:
                print("\n⚠️  El análisis MM-PBSA/MM-GBSA encontró problemas")
                print("    Revisa los mensajes arriba para más detalles")
        
        except Exception as e:
            print(f"\n❌ Error ejecutando análisis MM-PBSA/MM-GBSA: {e}")
            print("    El análisis puede ejecutarse manualmente con:")
            print(f"    python3 {mmpbsa_script} -d {self.results_dir} --mpi --cores 6")
            import traceback
            traceback.print_exc()
    
    def run_mmpbsa_analysis_automatically(self):
        """Ejecuta automáticamente el análisis MM-PBSA/MM-GBSA sin preguntar"""
        print("\n" + "="*80)
        print("🧪 INICIANDO ANÁLISIS MM-PBSA/MM-GBSA AUTOMÁTICAMENTE")
        print("="*80)
        
        if not self.has_ligand:
            print("\n⚠️  Sistema sin ligando detectado")
            print("    El análisis MM-PBSA/MM-GBSA requiere un sistema proteína-ligando")
            print("    Omitiendo este análisis...")
            return
        
        mmpbsa_script_locations = [
            Path("/home/ChemFusion/funciones/mmpbsa_analysis.py"),
            self.results_dir.parent / "mmpbsa_analysis.py",
            Path(__file__).parent / "mmpbsa_analysis.py",
        ]
        
        mmpbsa_script = None
        for location in mmpbsa_script_locations:
            if location.exists():
                mmpbsa_script = location
                print(f"✅ Script MM-PBSA/MM-GBSA encontrado: {mmpbsa_script}")
                break
        
        if mmpbsa_script is None:
            print("⚠️  Script mmpbsa_analysis.py no encontrado")
            print("    Búsqueda realizada en:")
            for loc in mmpbsa_script_locations:
                print(f"      - {loc}")
            print("\n    El análisis MM-PBSA/MM-GBSA debe ejecutarse manualmente:")
            print(f"    python3 mmpbsa_analysis.py -d {self.results_dir}")
            return
        
        required_files = ['md_1_center.xtc', 'md_1.tpr', 'index.ndx']
        missing_files = []
        for filename in required_files:
            if not (self.results_dir / filename).exists():
                missing_files.append(filename)
        
        if missing_files:
            print(f"⚠️  Archivos requeridos faltantes: {', '.join(missing_files)}")
            print("    El análisis MM-PBSA/MM-GBSA no puede ejecutarse automáticamente")
            return
        
        try:
            spec = importlib.util.spec_from_file_location("mmpbsa_analysis", mmpbsa_script)
            mmpbsa_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mmpbsa_module)
            
            print("\n📊 Ejecutando análisis MM-PBSA/MM-GBSA...")
            print("    (Calculando energía libre de unión ΔG...)")
            print("    (Esto puede tomar varios minutos)")
            
            mmpbsa_analyzer = mmpbsa_module.GMX_MMPBSA_Analyzer(
                results_dir=str(self.results_dir),
                use_mpi=True,  # ← CAMBIO: Activar MPI por defecto
                n_cores=6
            )
            
            # ← CORRECCIÓN: Eliminar argumento generate_pdf inexistente
            success = mmpbsa_analyzer.run_analysis(use_pb=True)
            
            if success:
                print("\n" + "="*80)
                print("✅ ANÁLISIS MM-PBSA/MM-GBSA COMPLETADO EXITOSAMENTE")
                print("="*80)
                binding_dir = self.results_dir / 'analisis_binding_energy' / 'gmx_MMPBSA'
                print(f"\n📊 Resultados en: {binding_dir}")
                print("    Archivos generados:")
                print("      📊 binding_energy.png (gráfica de energías)")
                print("      📄 SUMMARY_REPORT.txt (reporte completo)")
                print("      📈 FINAL_RESULTS_MMPBSA.dat (resultados detallados)")
                print("="*80)
            else:
                print("\n⚠️  El análisis MM-PBSA/MM-GBSA encontró problemas")
                print("    Revisa los mensajes arriba para más detalles")
        
        except Exception as e:
            print(f"\n❌ Error ejecutando análisis MM-PBSA/MM-GBSA: {e}")
            print("    El análisis puede ejecutarse manualmente con:")
            print(f"    python3 {mmpbsa_script} -d {self.results_dir} --mpi --cores 6")
            import traceback
            traceback.print_exc()


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Análisis completo de simulaciones MD con GROMACS (CON REPORTE PDF GARANTIZADO)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🆕 FUNCIONALIDADES:
  - Análisis detallado de H-bonds proteína-ligando con residuos específicos
  - Análisis DCCM automático
  - Análisis MM-PBSA/MM-GBSA automático (solo para sistemas con ligando)
  - 📄 GENERACIÓN GARANTIZADA DE REPORTE PDF AL FINAL""")
    
    parser.add_argument('-d', '--directory', type=str, required=True, help='Directorio con resultados MD')
    parser.add_argument('-g', '--gmx-bin', type=str, default='gmx', help='Ruta al ejecutable de GROMACS')
    parser.add_argument('--plot-only', action='store_true', help='Solo generar gráficas')
    
    args = parser.parse_args()
    
    if not Path(args.directory).exists():
        print(f"❌ Error: Directorio {args.directory} no existe")
        sys.exit(1)
    
    analyzer = GromacsAnalyzer(args.directory, args.gmx_bin)
    
    if args.plot_only:
        print("Modo: Solo gráficas")
        analyzer.plot_time_series()
        analyzer.generate_summary_report()
        # Generar PDF deshabilitado (no disponible)
        # analyzer.generate_pdf_report_final()
    else:
        analyzer.run_full_analysis()


if __name__ == '__main__':
    main()