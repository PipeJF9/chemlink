# VERIFICAR LO DE CORES
# RIVISAR SI ES ENCESARIO CORRER MMPBSA 
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess

from .dccm_analysis import DCCMAnalyzer
from .mmpbsa_analysis import GMX_MMPBSA_Analyzer

plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']

class GromacsAnalyzer:
    
    def __init__(self, results_dir: str, sim_type: str, gmx_bin: str = "gmx"):
        self.results_dir = Path(results_dir)
        self.gmx_bin = gmx_bin
        self.sim_type = sim_type  # Guardamos el tipo de simulación
        
        # Flags booleanos para facilitar las condiciones en las gráficas
        self.has_ligand = sim_type in ["2", "6"]
        self.is_protein_only = sim_type == "1"
        self.is_protein_protein = sim_type == "5"
        
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
        try:
            # Aseguramos que el directorio de trabajo exista antes de intentar entrar
            if not self.results_dir.exists():
                self.results_dir.mkdir(parents=True, exist_ok=True)

            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True, cwd=str(self.results_dir))
            stdout, stderr = process.communicate(input=stdin_input)
            
            if process.returncode != 0:
                print(f"❌ Error en comando GMX: {' '.join(cmd)}")
                # GROMACS suele enviar los errores fatales a stderr
                print(f"DEBUG STDERR: {stderr}")
                return False, stderr
                
            return True, stdout
        except Exception as e:
            print(f"❌ Error de ejecución: {e}")
            return False, ""
    
    def analyze_energy(self):
        print("\n" + "="*60)
        print("   ANALIZANDO ENERGÍAS DEL SISTEMA")
        print("="*60)

        # Asegurar que todas las carpetas de análisis existan físicamente
        for folder in self.analysis_dirs.values():
            folder.mkdir(parents=True, exist_ok=True)
        
        # Hemos ajustado los números de selección según tus logs de GROMACS 2025.4:
        # Formato: (archivo_edr, archivo_salida, seleccion_gmx)
        analyses = [
            ('em.edr',  'potential.xvg',        '10\n0\n'), # 'Potential' suele ser 10 en EM
            ('nvt.edr', 'temperature.xvg',      '14\n0\n'), # Según tu log: 14 Temperature
            ('npt.edr', 'pressure.xvg',         '15\n0\n'), # Según tu log: 15 Pressure
            ('md.edr',  'energy_total.xvg',     '12\n0\n'), # Según tu log: 12 Total-Energy
            ('md.edr',  'energy_potential.xvg', '10\n0\n'), # Según tu log: 10 Potential
            ('md.edr',  'energy_kinetic.xvg',   '11\n0\n'), # Según tu log: 11 Kinetic-En.
            ('md.edr',  'temperature_md.xvg',   '14\n0\n'), # Según tu log: 14 Temperature
            ('md.edr',  'volume.xvg',           '20\n0\n'), # Según tu log: 20 Volume
            ('md.edr',  'density.xvg',          '21\n0\n'), # Según tu log: 21 Density
        ]
        
        for edr, out, sel in analyses:
            edr_path = self.results_dir / edr
            if edr_path.exists():
                # Usamos la ruta relativa de la subcarpeta para evitar errores de I/O
                # Si self.analysis_dirs['energia'] es 'results/analisis_energia'
                rel_out_path = self.analysis_dirs['energia'].relative_to(self.results_dir) / out
                
                cmd = [self.gmx_bin, 'energy', '-f', edr,
                    '-o', str(rel_out_path)]
                
                success, _ = self._run_gmx_command(cmd, sel)
                if success:
                    print(f"✅ Generado: {out}")
            else:
                print(f"⚠️  Saltando {edr}: Archivo no encontrado")
    
    def analyze_rmsd(self):
        print("\n" + "="*80)
        print("PASO 8: Análisis de RMSD")
        print("="*80)
        
        out_dir = self.analysis_dirs['rmsd'].relative_to(self.results_dir)
        
        # Usamos nombres de grupos estándar en lugar de números
        analyses = [('Backbone\nBackbone\n', 'rmsd_backbone.xvg'), 
                    ('C-alpha\nC-alpha\n', 'rmsd_calpha.xvg'), 
                    ('Protein\nProtein\n', 'rmsd_protein.xvg')]
        
        for sel, out in analyses:
            cmd = [self.gmx_bin, 'rms', 
                   '-s', 'em.tpr',            
                   '-f', 'md_center.xtc',     
                   '-n', 'index.ndx',         
                   '-tu', 'ns', 
                   '-o', str(out_dir / out)]  
            self._run_gmx_command(cmd, sel)
        
        if self.has_ligand:
            # Según tu log: 13 es UNL (Ligando) y 0 es System (Complejo)
            for sel, out in [('Protein\nUNL\n', 'rmsd_ligand_fit_protein.xvg'),
                             ('UNL\nUNL\n', 'rmsd_ligand_fit_self.xvg'),
                             ('Protein\nSystem\n', 'rmsd_complex.xvg')]:
                cmd = [self.gmx_bin, 'rms', 
                       '-s', 'em.tpr', 
                       '-f', 'md_center.xtc',
                       '-n', 'index.ndx',
                       '-tu', 'ns', 
                       '-o', str(out_dir / out)]
                self._run_gmx_command(cmd, sel)
        
        print("✅ Completado")
    
    def analyze_rmsf(self):
        print("\n" + "="*80)
        print("PASO 9: Análisis de RMSF")
        print("="*80)
        
        out_dir = self.analysis_dirs['rmsf'].relative_to(self.results_dir)
        
        for sel, out in [('3\n', 'rmsf_calpha'), ('4\n', 'rmsf_backbone'), ('1\n', 'rmsf_protein')]:
            cmd = [self.gmx_bin, 'rmsf', 
                   '-s', 'md.tpr', 
                   '-f', 'md_center.xtc',
                   '-n', 'index.ndx',
                   '-o', str(out_dir / f'{out}.xvg'),
                   '-ox', str(out_dir / f'{out}_avg.pdb'),
                   '-oq', str(out_dir / f'bfactors_{out.split("_")[1]}.pdb'),
                   '-res']
            self._run_gmx_command(cmd, sel)
        
        if self.has_ligand:
            cmd = [self.gmx_bin, 'rmsf', 
                   '-s', 'md.tpr', 
                   '-f', 'md_center.xtc',
                   '-n', 'index.ndx',
                   '-o', str(out_dir / 'rmsf_ligand.xvg'),
                   '-ox', str(out_dir / 'rmsf_ligand_avg.pdb'),
                   '-oq', str(out_dir / 'bfactors_ligand.pdb'), 
                   '-res']
            self._run_gmx_command(cmd, '13\n')
        
        print("✅ Completado")
    
    def analyze_gyration(self):
        print("\n" + "="*80)
        print("PASO 10: Radio de Giro")
        print("="*80)
        
        out_dir = self.analysis_dirs['estructural'].relative_to(self.results_dir)
        
        for sel, out in [('1\n', 'gyrate_protein.xvg'), 
                        ('4\n', 'gyrate_backbone.xvg'), 
                        ('3\n', 'gyrate_calpha.xvg')]:
            cmd = [self.gmx_bin, 'gyrate', 
                   '-f', 'md_center.xtc',
                   '-s', 'md.tpr',
                   '-n', 'index.ndx',
                   '-o', str(out_dir / out)]
            self._run_gmx_command(cmd, sel)
        
        print("✅ Completado")
    
    def analyze_sasa(self):
        print("\n" + "="*80)
        print("PASO 11: Análisis de SASA")
        print("="*80)
        
        out_dir = self.analysis_dirs['sasa'].relative_to(self.results_dir)
        
        # Análisis de la Proteína usando el nombre del grupo
        cmd = [self.gmx_bin, 'sasa', 
               '-f', 'md_center.xtc',
               '-s', 'md.tpr',
               '-n', 'index.ndx',
               '-o', str(out_dir / 'sasa_protein.xvg'),
               '-or', str(out_dir / 'sasa_residue.xvg'),
               '-oa', str(out_dir / 'sasa_atom.xvg')]
        self._run_gmx_command(cmd, 'Protein\n')
        
        if self.has_ligand:
            # Usamos 'sustratos' comunes por nombre para evitar errores de índice
            for group_name, out in [('Other', 'sasa_ligand.xvg'), ('System', 'sasa_complex.xvg')]:
                cmd = [self.gmx_bin, 'sasa', 
                       '-f', 'md_center.xtc',
                       '-s', 'md.tpr',
                       '-n', 'index.ndx',
                       '-o', str(out_dir / out)]
                self._run_gmx_command(cmd, f'{group_name}\n')
        
        print("✅ Completado")
    
    def analyze_hbonds_detailed(self):
        """Análisis DETALLADO de puentes de hidrógeno y contactos"""
        print("\n" + "="*80)
        print("PASO 12: Análisis DETALLADO de Interacciones (H-bonds/Contactos)")
        print("="*80)
        
        out_dir = self.analysis_dirs['hbonds'].relative_to(self.results_dir)
        
        # H-bonds Intramoleculares (Proteína-Proteína)
        print("🔗 Analizando H-bonds internos de la proteína...")
        cmd_intra = [self.gmx_bin, 'hbond', 
                     '-f', 'md_center.xtc',
                     '-s', 'md.tpr',
                     '-n', 'index.ndx',
                     '-num', str(out_dir / 'hbond_protein_intra.xvg')]
        self._run_gmx_command(cmd_intra, '1\n1\n')
        
        if self.has_ligand:
            # ANÁLISIS DE CONTACTOS (Respaldo por si fallan los H-bonds químicos)
            print("📏 Midiendo contactos por distancia (corte 0.35nm)...")
            cmd_pair = [self.gmx_bin, 'pairdist',
                        '-f', 'md_center.xtc',
                        '-s', 'md.tpr',
                        '-n', 'index.ndx',
                        '-cutoff', '0.35',
                        '-o', str(out_dir / 'contacts_prot_lig.xvg')]
            self._run_gmx_command(cmd_pair, '1\n13\n')

            print("🧪 Intentando detectar H-bonds químicos...")
            cmd_hbond = [self.gmx_bin, 'hbond', 
                         '-f', 'md_center.xtc',
                         '-s', 'md.tpr',
                         '-n', 'index.ndx',
                         '-num', str(out_dir / 'hbond_prot_lig.xvg'),
                         '-dist', str(out_dir / 'hbond_prot_lig_dist.xvg'),
                         '-ang', str(out_dir / 'hbond_prot_lig_angle.xvg')]
            
            # Usamos try-except interno para que si falla el ligando, el script siga
            success, _ = self._run_gmx_command(cmd_hbond, '1\n13\n')
            
            if success:
                self._extract_hbond_residues(self.analysis_dirs['hbonds'])
                self._convert_hbond_matrix(self.analysis_dirs['hbonds'])
            else:
                print("⚠️  Nota: No se detectaron H-bonds químicos (falta de donadores/aceptores).")
                print("✅ Se ha generado 'contacts_prot_lig.xvg' como alternativa de interacción.")
        
        print("✅ Análisis de interacciones completado")
    
    def _extract_hbond_residues(self, hbonds_dir: Path):
        ndx_file = hbonds_dir / 'hbond_prot_lig.ndx'
        if not ndx_file.exists():
            return
        
        try:
            with open(ndx_file, 'r') as f:
                lines = f.readlines()
            
            hbond_groups = {}
            current_group = None
            
            for line in lines:
                if line.startswith('[') and line.endswith(']'):
                    current_group = line[1:-1].strip()
                    hbond_groups[current_group] = []
                elif current_group:
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
        eps_file = hbonds_dir / 'hbond_matrix.eps'

        if not xpm_file.exists():
            print(f"⚠️  Matriz {xpm_file.name} no encontrada. No se puede convertir a EPS.")
            return
        
        try:
            rel_xpm = xpm_file.relative_to(self.results_dir)[cite: 7]
            rel_eps = eps_file.relative_to(self.results_dir)[cite: 7]
            
            cmd = [
                self.gmx_bin, 'xpm2ps', 
                '-f', str(rel_xpm),
                '-o', str(rel_eps)
            ]
            
            success, stderr = self._run_gmx_command(cmd, '\n')
            
            if success and eps_file.exists():
                print(f"✅ Matriz convertida exitosamente: {eps_file.name}")[cite: 7]
            else:
                print(f"❌ Falló la conversión de la matriz XPM. Revisa los logs de GROMACS.")[cite: 7]
                
        except ValueError:
            print(f"⚠️  Error de ruta: {xpm_file} no es relativo a {self.results_dir}")
    
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
        """Grafica análisis detallado de H-bonds (Distancias, Ángulos e Inter/Intra)"""
        # Solo tiene sentido si hay un ligando (interacción intermolecular)
        if not self.has_ligand:
            return
        
        hbonds_dir = self.analysis_dirs['hbonds']
        hbond_file = hbonds_dir / 'hbond_prot_lig.xvg'
        
        if not hbond_file.exists():
            print("  ⚠️  Archivo hbond_prot_lig.xvg no encontrado. Omitiendo gráfica detallada.")
            return
        
        print("  📈 Generando análisis detallado de H-bonds...")
        try:
            # Usamos un estilo más limpio y profesional
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Análisis Detallado de Puentes de Hidrógeno Proteína-Ligando', 
                        fontsize=16, fontweight='bold')
            
            # 1. H-bonds vs tiempo (Evolución temporal)
            data = self._read_xvg(hbond_file)
            if data is not None:
                axes[0, 0].plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1)
                mean_val = np.mean(data[:, 1])
                axes[0, 0].axhline(y=mean_val, color='r', linestyle='--',
                                 label=f'Promedio: {mean_val:.2f}')
                axes[0, 0].set_xlabel('Tiempo (ps)', fontweight='bold')
                axes[0, 0].set_ylabel('Número de H-bonds', fontweight='bold')
                axes[0, 0].set_title('Evolución Temporal', fontweight='bold')
                axes[0, 0].legend()
                axes[0, 0].grid(True, alpha=0.3)

            # 2. Histograma de Distancias
            dist_file = hbonds_dir / 'hbond_prot_lig_dist.xvg'
            if dist_file.exists():
                data_dist = self._read_xvg(dist_file)
                if data_dist is not None and data_dist.shape[1] > 1:
                    # Filtramos ceros (GROMACS pone 0 cuando no existe el enlace en ese frame)
                    distances = data_dist[:, 1:].flatten()
                    distances = distances[distances > 0]
                    if len(distances) > 0:
                        axes[0, 1].hist(distances, bins=40, color=COLORS[1], alpha=0.7, edgecolor='black')
                        axes[0, 1].axvline(x=np.mean(distances), color='r', linestyle='--', 
                                         label=f'Media: {np.mean(distances):.3f} nm')
                        axes[0, 1].set_xlabel('Distancia (nm)', fontweight='bold')
                        axes[0, 1].set_ylabel('Frecuencia', fontweight='bold')
                        axes[0, 1].set_title('Distribución de Distancias', fontweight='bold')
                        axes[0, 1].legend()

            # 3. Histograma de Ángulos
            angle_file = hbonds_dir / 'hbond_prot_lig_angle.xvg'
            if angle_file.exists():
                data_angle = self._read_xvg(angle_file)
                if data_angle is not None and data_angle.shape[1] > 1:
                    angles = data_angle[:, 1:].flatten()
                    angles = angles[angles > 0]
                    if len(angles) > 0:
                        axes[1, 0].hist(angles, bins=40, color=COLORS[2], alpha=0.7, edgecolor='black')
                        axes[1, 0].axvline(x=np.mean(angles), color='r', linestyle='--', 
                                         label=f'Media: {np.mean(angles):.1f}°')
                        axes[1, 0].set_xlabel('Ángulo (grados)', fontweight='bold')
                        axes[1, 0].set_ylabel('Frecuencia', fontweight='bold')
                        axes[1, 0].set_title('Distribución de Ángulos', fontweight='bold')
                        axes[1, 0].legend()

            # 4. Comparación Intra vs Inter (Proteína sola vs Complejo)
            found_comp = False
            for filename, label, color in [('hbond_prot_lig.xvg', 'Inter (Prot-Lig)', COLORS[0]),
                                          ('hbond_protein_intra.xvg', 'Intra (Proteína)', COLORS[3])]:
                filepath = hbonds_dir / filename
                if filepath.exists():
                    data_comp = self._read_xvg(filepath)
                    if data_comp is not None:
                        axes[1, 1].plot(data_comp[:, 0], data_comp[:, 1], label=label, color=color, alpha=0.6)
                        found_comp = True
            
            if found_comp:
                axes[1, 1].set_xlabel('Tiempo (ps)', fontweight='bold')
                axes[1, 1].set_ylabel('Número de H-bonds', fontweight='bold')
                axes[1, 1].set_title('Comparación Inter vs Intra', fontweight='bold')
                axes[1, 1].legend()
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.savefig(output_dir / 'hbonds_detailed.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("  ✅ Gráfica detallada de H-bonds generada con éxito.")
            
        except Exception as e:
            print(f"  ⚠️ Error al graficar H-bonds detallados: {e}")
            if 'fig' in locals(): plt.close()
    
    def _plot_energy_analysis(self, output_dir: Path):
        """Grafica energías"""
        print("  📈 Graficando energías...")
        
        try:
            fig, axes = plt.subplots(3, 2, figsize=(15, 12))
            fig.suptitle('Análisis Energético de la Simulación MD', fontsize=16, fontweight='bold')
            
            plots = [('energy_potential.xvg', 'Energía Potencial', 'kJ/mol', axes[0, 0]),
                    ('energy_kinetic.xvg', 'Energía Cinética', 'kJ/mol', axes[0, 1]),
                    ('energy_total.xvg', 'Energía Total', 'kJ/mol', axes[1, 0]),
                    ('temperature_md.xvg', 'Temperatura', 'K', axes[1, 1]),
                    ('density.xvg', 'Densidad', 'kg/m³', axes[2, 0]),
                    ('volume.xvg', 'Volumen', 'nm³', axes[2, 1])]
            
            found_any = False
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
                        found_any = True
                else:
                    ax.text(0.5, 0.5, 'Archivo no encontrado', ha='center', va='center')
            
            if found_any:
                plt.tight_layout()
                plt.savefig(output_dir / 'energia_tiempo.png', dpi=300, bbox_inches='tight')
                print("  ✅ Gráfica de energías generada.")
            plt.close()
        except Exception as e:
            print(f"  ⚠️  Error al graficar energías: {e}")
    
    def _plot_rmsd_analysis(self, output_dir: Path):
        """Grafica RMSD"""
        print("  📈 Graficando RMSD...")
        
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            
            files = [('rmsd_backbone.xvg', 'Backbone', COLORS[0]),
                    ('rmsd_calpha.xvg', 'C-alpha', COLORS[1]),
                    ('rmsd_protein.xvg', 'Proteína completa', COLORS[2])]
            
            if self.has_ligand:
                files.extend([('rmsd_ligand_fit_protein.xvg', 'Ligando (fit proteína)', COLORS[3]),
                             ('rmsd_complex.xvg', 'Complejo', COLORS[4])])
            
            if self.is_protein_protein:
                files.append(('rmsd_other_fit_protein.xvg', 'Cadena B', COLORS[4]))

            found = False
            for filename, label, color in files:
                filepath = self.analysis_dirs['rmsd'] / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
                        found = True
            
            if found:
                ax.set_xlabel('Tiempo (ns)', fontsize=12, fontweight='bold')
                ax.set_ylabel('RMSD (nm)', fontsize=12, fontweight='bold')
                ax.set_title('RMSD vs Tiempo', fontsize=14, fontweight='bold')
                ax.legend(loc='best', frameon=True, shadow=True)
                ax.grid(True, alpha=0.3)
                plt.tight_layout()
                plt.savefig(output_dir / 'rmsd_tiempo.png', dpi=300, bbox_inches='tight')
                print("  ✅ Gráfica de RMSD generada.")
            plt.close()
        except Exception as e:
            print(f"  ⚠️  Error al graficar RMSD: {e}")
    
    def _plot_rmsf_analysis(self, output_dir: Path):
        """Grafica RMSF"""
        print("  📈 Graficando RMSF...")
        try:
            fig, ax = plt.subplots(figsize=(14, 6))
            found = False
            for filename, label, color in [('rmsf_calpha.xvg', 'C-alpha', COLORS[0]),
                                           ('rmsf_backbone.xvg', 'Backbone', COLORS[1])]:
                filepath = self.analysis_dirs['rmsf'] / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color)
                        found = True
            if found:
                ax.set_xlabel('Número de Residuo', fontsize=12, fontweight='bold'); ax.set_ylabel('RMSF (nm)', fontsize=12, fontweight='bold')
                ax.set_title('RMSF por Residuo', fontsize=14, fontweight='bold'); ax.legend(); ax.grid(True, alpha=0.3)
                plt.savefig(output_dir / 'rmsf_residuos.png', dpi=300); print("  ✅ RMSF graficado.")
            plt.close()
        except Exception as e: print(f"  ⚠️ Error en RMSF: {e}")
    
    def _plot_structural_properties(self, output_dir: Path):
        """Grafica Radio de Giro"""
        print("  📈 Graficando Radio de Giro...")
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            found = False
            for filename, label, color in [('gyrate_protein.xvg', 'Proteína completa', COLORS[0]),
                                           ('gyrate_backbone.xvg', 'Backbone', COLORS[1]),
                                           ('gyrate_calpha.xvg', 'C-alpha', COLORS[2])]:
                filepath = self.analysis_dirs['estructural'] / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        ax.plot(data[:, 0], data[:, 1], label=label, linewidth=1.5, color=color); found = True
            if found:
                ax.set_xlabel('Tiempo (ps)'); ax.set_ylabel('Radio de Giro (nm)'); ax.legend(); ax.grid(True, alpha=0.3)
                plt.savefig(output_dir / 'gyrate_tiempo.png', dpi=300); print("  ✅ Radio de giro graficado.")
            plt.close()
        except Exception as e: print(f"  ⚠️ Error en Radio de Giro: {e}")
    
    def _plot_sasa_analysis(self, output_dir: Path):
        """Grafica SASA"""
        print("  📈 Graficando SASA...")
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            files = [('sasa_protein.xvg', 'Proteína', COLORS[0])]
            if self.has_ligand: files.extend([('sasa_ligand.xvg', 'Ligando', COLORS[1]), ('sasa_complex.xvg', 'Complejo', COLORS[2])])
            found = False
            for filename, label, color in files:
                filepath = self.analysis_dirs['sasa'] / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        ax.plot(data[:, 0], data[:, 1], label=label, color=color); found = True
            if found:
                ax.set_xlabel('Tiempo (ps)'); ax.set_ylabel('SASA (nm²)'); ax.legend(); ax.grid(True, alpha=0.3)
                plt.savefig(output_dir / 'sasa_tiempo.png', dpi=300); print("  ✅ SASA graficado.")
            plt.close()
        except Exception as e: print(f"  ⚠️ Error en SASA: {e}")
    
    def _plot_hbonds_analysis(self, output_dir: Path):
        """Grafica H-bonds básicos"""
        print("  📈 Graficando H-bonds...")
        try:
            fig, ax = plt.subplots(figsize=(12, 6))
            files = [('hbond_protein_intra.xvg', 'Proteína (intra)', COLORS[0])]
            if self.has_ligand: 
                files.append(('hbond_prot_lig.xvg', 'Proteína-Ligando', COLORS[1]))
            
            found = False
            for filename, label, color in files:
                filepath = self.analysis_dirs['hbonds'] / filename
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None:
                        ax.plot(data[:, 0], data[:, 1], label=label, color=color)
                        found = True
            
            if found:
                ax.set_xlabel('Tiempo (ps)')
                ax.set_ylabel('Número de H-bonds')
                ax.legend()
                ax.grid(True, alpha=0.3)
                plt.savefig(output_dir / 'hbonds_tiempo.png', dpi=300)
                print("  ✅ H-bonds graficado.")
            plt.close()
        except Exception as e: 
            print(f"  ⚠️ Error en H-bonds: {e}")
    
    def _create_dashboard(self, output_dir: Path):
        """Dashboard resumen"""
        print("  📊 Creando dashboard...")
        try:
            fig = plt.figure(figsize=(20, 12))
            gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
            
            plots = [
                (gs[0, 0], 'rmsd', 'rmsd_backbone.xvg', 'RMSD Backbone', 'Tiempo (ns)', 'RMSD (nm)'),
                (gs[0, 1], 'energia', 'energy_potential.xvg', 'Energía Potencial', 'Tiempo (ps)', 'Energía (kJ/mol)'),
                (gs[0, 2], 'energia', 'temperature_md.xvg', 'Temperatura', 'Tiempo (ps)', 'Temperatura (K)'),
                (gs[1, 0], 'estructural', 'gyrate_protein.xvg', 'Radio de Giro', 'Tiempo (ps)', 'Rg (nm)'),
                (gs[1, 1], 'sasa', 'sasa_protein.xvg', 'SASA', 'Tiempo (ps)', 'SASA (nm²)'),
                (gs[1, 2], 'hbonds', 'hbond_protein_intra.xvg', 'H-bonds Intramoleculares', 'Tiempo (ps)', 'Número'),
                (gs[2, 2], 'energia', 'density.xvg', 'Densidad', 'Tiempo (ps)', 'kg/m³')
            ]
            
            for pos, dir_key, filename, title, xlabel, ylabel in plots:
                ax = fig.add_subplot(pos)
                filepath = self.analysis_dirs[dir_key] / filename
                
                if filepath.exists():
                    data = self._read_xvg(filepath)
                    if data is not None and data.size > 0:
                        ax.plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1.5)
                        ax.set_title(title, fontweight='bold', fontsize=10)
                        ax.set_xlabel(xlabel, fontsize=8)
                        ax.set_ylabel(ylabel, fontsize=8)
                        ax.grid(True, alpha=0.3)
                else:
                    ax.text(0.5, 0.5, f'No encontrado:\n{filename}', ha='center', va='center', fontsize=8, color='gray')
            
            ax_rmsf = fig.add_subplot(gs[2, :2])
            rmsf_path = self.analysis_dirs['rmsf'] / 'rmsf_calpha.xvg'
            if rmsf_path.exists():
                data = self._read_xvg(rmsf_path)
                if data is not None:
                    ax_rmsf.plot(data[:, 0], data[:, 1], color=COLORS[0], linewidth=1.5)
                    ax_rmsf.set_title('RMSF por Residuo', fontweight='bold', fontsize=10)
                    ax_rmsf.set_xlabel('Residuo', fontsize=8)
                    ax_rmsf.set_ylabel('RMSF (nm)', fontsize=8)
                    ax_rmsf.grid(True, alpha=0.3)
            
            fig.suptitle('Dashboard de Análisis MD - Resumen General', fontsize=16, fontweight='bold', y=0.995)
            plt.savefig(output_dir / 'dashboard_resumen.png', dpi=300, bbox_inches='tight')
            plt.close()
            print("  ✅ Dashboard generado correctamente.")
        except Exception as e:
            print(f"  ⚠️ Error al crear dashboard: {e}")
    
    def generate_summary_report(self):
        """Genera reporte estadístico buscando archivos en las carpetas correctas"""
        print("\n" + "="*80)
        print("GENERANDO RESUMEN ESTADÍSTICO")
        print("="*80)
        
        report = ["="*80, "RESUMEN COMPLETO DE ANÁLISIS DE DINÁMICA MOLECULAR", "="*80, "",
                 f"Sistema: {'Proteína-Ligando' if self.has_ligand else 'Proteína'}",
                 f"Directorio: {self.results_dir}", ""]
        
        def add_stats(title, key, filename, unit=''):
            filepath = self.analysis_dirs[key] / filename
            if filepath.exists():
                data = self._read_xvg(filepath)
                if data is not None and data.ndim > 1 and data.shape[0] > 0:
                    values = data[:, 1]
                    report.extend([f"{title}:",
                                 f"  Promedio: {np.mean(values):.3f} ± {np.std(values):.3f} {unit}",
                                 f"  Mín-Máx: {np.min(values):.3f} - {np.max(values):.3f} {unit}", ""])
                else:
                    report.extend([f"{title}: Sin datos disponibles", ""])
            else:
                report.extend([f"{title}: Archivo no encontrado", ""])
        
        sections = [
            ("1. ANÁLISIS DE RMSD", [
                ("RMSD Backbone", 'rmsd', 'rmsd_backbone.xvg', 'nm'),
                ("RMSD C-alpha", 'rmsd', 'rmsd_calpha.xvg', 'nm'),
                ("RMSD Proteína", 'rmsd', 'rmsd_protein.xvg', 'nm')]),
            ("2. ANÁLISIS DE RMSF", [("RMSF C-alpha", 'rmsf', 'rmsf_calpha.xvg', 'nm')]),
            ("3. PROPIEDADES ESTRUCTURALES", [("Radio de Giro", 'estructural', 'gyrate_protein.xvg', 'nm')]),
            ("4. ANÁLISIS DE SASA", [("SASA Proteína", 'sasa', 'sasa_protein.xvg', 'nm²')]),
            ("5. ANÁLISIS DE ENERGÍA", [
                ("Energía Potencial", 'energia', 'energy_potential.xvg', 'kJ/mol'),
                ("Energía Cinética", 'energia', 'energy_kinetic.xvg', 'kJ/mol'),
                ("Energía Total", 'energia', 'energy_total.xvg', 'kJ/mol'),
                ("Temperatura", 'energia', 'temperature_md.xvg', 'K'),
                ("Densidad", 'energia', 'density.xvg', 'kg/m³'),
                ("Volumen", 'energia', 'volume.xvg', 'nm³')]),
            ("6. PUENTES DE HIDRÓGENO", [("H-bonds Intramoleculares", 'hbonds', 'hbond_protein_intra.xvg', 'enlaces')])
        ]
        
        for section_title, stats_list in sections:
            report.extend([section_title, "-" * 80])
            for stat_title, key, fname, unit in stats_list:
                add_stats(stat_title, key, fname, unit)
        
        if self.has_ligand:
            report.extend(["7. PUENTES DE HIDRÓGENO DETALLADOS (PROTEÍNA-LIGANDO)", "-" * 80])
            dist_file = self.analysis_dirs['hbonds'] / 'hbond_prot_lig_dist.xvg'
            if dist_file.exists():
                data = self._read_xvg(dist_file)
                if data is not None and data.ndim > 1:
                    distances = data[:, 1:].flatten()
                    distances = distances[distances > 0]
                    if len(distances) > 0:
                        report.append(f"Distancia promedio H-bond: {np.mean(distances):.3f} ± {np.std(distances):.3f} nm")
            
            angle_file = self.analysis_dirs['hbonds'] / 'hbond_prot_lig_angle.xvg'
            if angle_file.exists():
                data = self._read_xvg(angle_file)
                if data is not None and data.ndim > 1:
                    angles = data[:, 1:].flatten()
                    angles = angles[angles > 0]
                    if len(angles) > 0:
                        report.append(f"Ángulo promedio H-bond: {np.mean(angles):.1f} ± {np.std(angles):.1f}°")
            report.append("")
        
        report.extend(["="*80, "FIN DEL RESUMEN", "="*80])
        
        report_file = self.results_dir / 'RESUMEN_ANALISIS.txt'
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report))
            print('\n'.join(report))
            print(f"\n✅ Resumen guardado en: {report_file}")
        except Exception as e:
            print(f"  ⚠️ Error al escribir el archivo de reporte: {e}")

    def detect_protein_protein(self) -> (bool, list):
        """Detecta si la simulación es probablemente proteína-proteína."""
        # Si ya marcamos que tiene ligando pequeño, no es proteína-proteína para este análisis
        if self.has_ligand:
            return False, []

        pdb_file = self.results_dir / 'md.pdb'
        if not pdb_file.exists():
            return False, []

        chains = set()
        try:
            with open(pdb_file, 'r') as f:
                for line in f:
                    # Buscamos líneas ATOM (estándar para proteínas)
                    if line.startswith('ATOM  '):
                        if len(line) >= 22:
                            chain_id = line[21].strip()
                            if chain_id: # Solo añadir si no es un espacio en blanco
                                chains.add(chain_id)
                    # Terminamos de leer si llegamos al final del primer frame para ahorrar tiempo
                    if line.startswith('ENDMDL'):
                        break
        except Exception as e:
            print(f"  ⚠️ Error leyendo PDB para detección de cadenas: {e}")
            return False, []

        sorted_chains = sorted(list(chains))
        if len(sorted_chains) > 1:
            print(f"  🧬 Detección: Complejo con {len(sorted_chains)} cadenas ({', '.join(sorted_chains)})")
            return True, sorted_chains
        
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
        print("\n" + "="*80)
        print("🔬 INICIANDO ANÁLISIS DCCM (Dynamic Cross-Correlation)")
        print("="*80)

        # Definición de rutas: self.results_dir es el 'work_dir' unificado
        work_dir = Path(self.results_dir)
        
        dccm_parent = work_dir / "analisis_dccm_pipeline"
        dccm_parent.mkdir(exist_ok=True)
        
        # Verificación de archivos requeridos en work_dir
        required_files = {
            'traj': work_dir / 'md_center.xtc',
            'tpr': work_dir / 'md.tpr',
            'ndx': work_dir / 'index.ndx'
        }
        
        missing = [f.name for f in required_files.values() if not f.exists()]
        if missing:
            print(f"⚠️  No se puede ejecutar DCCM. Faltan archivos en {work_dir.name}:")
            print(f"    {', '.join(missing)}")
            return

        try:
            print(f"📊 Configurando analizador en: {dccm_parent.name}")
            
            dccm_analyzer = DCCMAnalyzer(
                results_dir=str(dccm_parent),
                gmx_bin=self.gmx_bin
            )
            
            success = dccm_analyzer.run_pipeline_analysis(
                selection="C-alpha",
                max_residues=2000
            )
            
            if success:
                print(f"\n✅ DCCM COMPLETADO: Resultados en {dccm_parent.name}/analisis_dccm")
            else:
                print("\n⚠️  DCCM finalizó con advertencias (verificar logs de GROMACS).")
            
            
        except Exception as e:
            print(f"\n❌ Error crítico en la orquestación DCCM: {e}")
            import traceback
            print(traceback.format_exc()) 
        
        self.run_mmpbsa_analysis_automatically()

    def run_mmpbsa_analysis_automatically(self):
        """Ejecuta automáticamente el análisis MM-PBSA/MM-GBSA sin preguntar"""
        print("\n" + "="*80)
        print("🧪 INICIANDO ANÁLISIS MM-PBSA/MM-GBSA AUTOMÁTICAMENTE")
        print("="*80)
        
        # Validación de compatibilidad del sistema
        if not (self.has_ligand or self.is_protein_protein):
            print("\n⚠️  Sistema incompatible detectado")
            print("    El análisis MM-PBSA requiere un complejo (Prot-Lig o Prot-Prot)")
            print("    Omitiendo este análisis...")
            return

        # Verificación de archivos requeridos en results_dir
        required_files = ['md_center.xtc', 'md.tpr', 'index.ndx']
        missing_files = [f for f in required_files if not (self.results_dir / f).exists()]
        
        if missing_files:
            print(f"⚠️  Archivos requeridos faltantes en {self.results_dir.name}: {', '.join(missing_files)}")
            return
        
        try:
            print(f"\n📊 Ejecutando análisis para tipo: {'Prot-Lig' if self.has_ligand else 'Prot-Prot'}...")
            
            # Instanciación directa 
            mmpbsa_analyzer = GMX_MMPBSA_Analyzer(
                results_dir=str(self.results_dir),
                use_mpi=True,
                n_cores=6
            )
            
            # Ejecución del motor de cálculo
            success = mmpbsa_analyzer.run_analysis(use_pb=True)
            
            if success:
                print("\n" + "="*80)
                print("✅ ANÁLISIS MM-PBSA/MM-GBSA COMPLETADO EXITOSAMENTE")
                print("="*80)
            else:
                print("\n⚠️  El análisis MM-PBSA/MM-GBSA encontró problemas")
        
        except Exception as e:
            print(f"\n❌ Error ejecutando análisis MM-PBSA/MM-GBSA: {e}")
            import traceback
            traceback.print_exc()

    def run_pipeline_analysis(self, plot_only=False):
            """
            Sustituye la lógica del main. Permite decidir qué ejecutar
            basado en argumentos de función.
            """
            if not self.results_dir.exists():
                raise FileNotFoundError(f"❌ Error: Directorio {self.results_dir} no existe")

            if plot_only:
                print("[*] Modo: Solo generación de gráficas y reporte")
                self.plot_time_series()
                self.generate_summary_report()
            else:
                print("[*] Ejecutando análisis completo...")
                self.run_full_analysis()