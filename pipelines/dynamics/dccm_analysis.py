#!/usr/bin/env python3
"""
Dynamic Cross-Correlation Matrix (DCCM) Analysis - VERSIÓN FUNCIONAL
Ubicación: /home/ChemFusion/funciones/dccm_analysis.py

SOLUCIÓN: Calcular DCCM directamente desde la trayectoria
Ya que 'gmx covar -ascii' no genera el formato correcto
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from pathlib import Path
import subprocess
import argparse

plt.style.use('seaborn-v0_8-darkgrid')


class DCCMAnalyzer:
    """Analizador de matriz de correlación cruzada dinámica"""
    
    def __init__(self, results_dir: str, gmx_bin: str = "gmx"):
        self.results_dir = Path(results_dir)
        self.gmx_bin = gmx_bin
        
        self.dccm_dir = self.results_dir / 'analisis_dccm'
        self.dccm_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*80}")
        print("DYNAMIC CROSS-CORRELATION MATRIX (DCCM) ANALYSIS")
        print(f"{'='*80}")
        print(f"Directorio de trabajo: {self.results_dir}")
        print(f"Directorio DCCM: {self.dccm_dir}")
    
    def _run_gmx_command(self, cmd: list, stdin_input: str = "") -> tuple:
        """Ejecuta comando GROMACS"""
        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.results_dir)
            )
            stdout, stderr = process.communicate(input=stdin_input)
            return process.returncode == 0, stdout
        except Exception as e:
            print(f"❌ Error ejecutando comando: {e}")
            return False, ""
    
    def extract_calpha_trajectory(self, selection: str = "C-alpha"):
        """Extrae trayectoria de C-alpha en formato PDB"""
        print(f"\n{'='*80}")
        print("PASO 1: Extrayendo Trayectoria de C-alpha")
        print(f"{'='*80}")
        
        selection_map = {
            "C-alpha": "3\n",
            "Backbone": "4\n",
            "Protein": "1\n"
        }
        
        sel_input = selection_map.get(selection, "3\n")
        
        # Extraer trayectoria como PDB multi-frame
        traj_pdb = self.dccm_dir / 'calpha_traj.pdb'
        
        cmd = [
            self.gmx_bin, 'trjconv',
            '-f', str(self.results_dir / 'md_1_center.xtc'),
            '-s', str(self.results_dir / 'md_1.tpr'),
            '-o', str(traj_pdb),
            '-n', str(self.results_dir / 'index.ndx')
        ]
        
        print(f"Extrayendo átomos {selection}...")
        success, output = self._run_gmx_command(cmd, sel_input)
        
        if success and traj_pdb.exists():
            print(f"✅ Trayectoria extraída: {traj_pdb}")
            return traj_pdb
        else:
            print("❌ Error extrayendo trayectoria")
            return None
    
    def parse_pdb_trajectory(self, pdb_file: Path, max_frames: int = None):
        """
        Lee trayectoria PDB multi-frame y extrae coordenadas
        
        Returns:
            coords: array (n_frames, n_atoms, 3)
        """
        print(f"\n{'='*80}")
        print("PASO 2: Leyendo Coordenadas de la Trayectoria")
        print(f"{'='*80}")
        
        frames = []
        current_frame = []
        
        with open(pdb_file, 'r') as f:
            for line in f:
                if line.startswith('ATOM') or line.startswith('HETATM'):
                    # Extraer coordenadas x, y, z (columnas 31-54 en formato PDB)
                    x = float(line[30:38].strip())
                    y = float(line[38:46].strip())
                    z = float(line[46:54].strip())
                    current_frame.append([x, y, z])
                
                elif line.startswith('ENDMDL') or line.startswith('END'):
                    if current_frame:
                        frames.append(current_frame)
                        current_frame = []
                        
                        if max_frames and len(frames) >= max_frames:
                            break
        
        # Si hay un frame sin ENDMDL al final
        if current_frame:
            frames.append(current_frame)
        
        # Convertir a numpy array
        coords = np.array(frames)
        
        print(f"✓ Frames leídos: {coords.shape[0]:,}")
        print(f"✓ Átomos por frame: {coords.shape[1]:,}")
        print(f"✓ Dimensiones: {coords.shape[2]}")
        print(f"✓ Tamaño total: {coords.nbytes / (1024**2):.1f} MB")
        
        return coords
    
    def compute_dccm_from_trajectory(self, coords: np.ndarray, max_residues: int = 2000):
        """
        Calcula DCCM directamente desde coordenadas
        
        Args:
            coords: array (n_frames, n_atoms, 3)
        """
        print(f"\n{'='*80}")
        print("PASO 3: Calculando DCCM desde Coordenadas")
        print(f"{'='*80}")
        
        n_frames, n_atoms, n_dims = coords.shape
        
        print(f"Frames: {n_frames:,}")
        print(f"Átomos: {n_atoms:,}")
        
        # Limitar número de átomos si es necesario
        if n_atoms > max_residues:
            print(f"⚠️  Limitando análisis a primeros {max_residues} residuos")
            n_atoms = max_residues
            coords = coords[:, :n_atoms, :]
        
        # Calcular posiciones promedio
        print(f"\n🧮 Calculando posiciones promedio...")
        avg_pos = np.mean(coords, axis=0)  # (n_atoms, 3)
        
        # Calcular desplazamientos respecto al promedio
        print(f"🧮 Calculando desplazamientos...")
        displacements = coords - avg_pos  # (n_frames, n_atoms, 3)
        
        # Calcular DCCM
        print(f"🧮 Calculando correlaciones cruzadas...")
        dccm_matrix = np.zeros((n_atoms, n_atoms))
        
        # Procesar por bloques para eficiencia
        block_size = 50
        total_blocks = (n_atoms + block_size - 1) // block_size
        
        for i_block in range(0, n_atoms, block_size):
            i_end = min(i_block + block_size, n_atoms)
            
            for j_block in range(0, n_atoms, block_size):
                j_end = min(j_block + block_size, n_atoms)
                
                # Calcular para este bloque
                for i in range(i_block, i_end):
                    # Desplazamientos del átomo i
                    d_i = displacements[:, i, :]  # (n_frames, 3)
                    
                    # Varianza del átomo i
                    var_i = np.mean(np.sum(d_i * d_i, axis=1))  # escalar
                    
                    for j in range(j_block, j_end):
                        # Desplazamientos del átomo j
                        d_j = displacements[:, j, :]  # (n_frames, 3)
                        
                        # Varianza del átomo j
                        var_j = np.mean(np.sum(d_j * d_j, axis=1))  # escalar
                        
                        # Covarianza entre i y j
                        # <d_i · d_j> = promedio del producto punto sobre todos los frames
                        cov_ij = np.mean(np.sum(d_i * d_j, axis=1))  # escalar
                        
                        # Correlación
                        if var_i > 1e-10 and var_j > 1e-10:
                            dccm_matrix[i, j] = cov_ij / np.sqrt(var_i * var_j)
                        else:
                            dccm_matrix[i, j] = 0.0
            
            # Mostrar progreso
            current_block = (i_block // block_size) + 1
            progress = (current_block / total_blocks) * 100
            if current_block % 5 == 0 or current_block == total_blocks:
                print(f"  Progreso: {progress:.1f}%")
        
        # Guardar matriz
        dccm_file = self.dccm_dir / 'dccm_matrix.dat'
        np.savetxt(dccm_file, dccm_matrix, fmt='%.6f')
        print(f"\n✅ DCCM guardada: {dccm_file}")
        
        # Estadísticas
        self._print_dccm_statistics(dccm_matrix)
        
        return dccm_matrix
    
    def _print_dccm_statistics(self, dccm_matrix: np.ndarray):
        """Imprime estadísticas de la DCCM"""
        print(f"\n{'='*80}")
        print("ESTADÍSTICAS DE LA DCCM")
        print(f"{'='*80}")
        
        # Verificar diagonal (debe ser ~1.0)
        diagonal = np.diag(dccm_matrix)
        print(f"Diagonal (auto-correlación):")
        print(f"  Promedio: {np.mean(diagonal):.4f}")
        print(f"  Min: {np.min(diagonal):.4f}")
        print(f"  Max: {np.max(diagonal):.4f}")
        
        # Extraer triángulo superior (sin diagonal)
        upper_tri = np.triu(dccm_matrix, k=1)
        correlations = upper_tri[upper_tri != 0]
        
        if len(correlations) == 0:
            print("\n⚠️  No se encontraron correlaciones en triángulo superior")
            return
        
        print(f"\nDimensión de la matriz: {dccm_matrix.shape[0]} x {dccm_matrix.shape[0]}")
        print(f"Pares analizados: {len(correlations):,}")
        print(f"\nCorrelación promedio: {np.mean(correlations):.4f}")
        print(f"Desviación estándar: {np.std(correlations):.4f}")
        print(f"Máximo: {np.max(correlations):.4f}")
        print(f"Mínimo: {np.min(correlations):.4f}")
        
        # Distribución
        print(f"\nDistribución de correlaciones:")
        for threshold in [0.8, 0.6, 0.4, 0.2, -0.2, -0.4, -0.6, -0.8]:
            if threshold > 0:
                count = np.sum(upper_tri > threshold)
                percent = (count / len(correlations)) * 100 if len(correlations) > 0 else 0
                print(f"  > {threshold:5.2f}: {count:6,} pares ({percent:5.2f}%)")
            else:
                count = np.sum(upper_tri < threshold)
                percent = (count / len(correlations)) * 100 if len(correlations) > 0 else 0
                print(f"  < {threshold:5.2f}: {count:6,} pares ({percent:5.2f}%)")
        
        # Guardar estadísticas detalladas
        stats_file = self.dccm_dir / 'dccm_statistics.txt'
        with open(stats_file, 'w') as f:
            f.write(f"{'='*80}\n")
            f.write("ESTADÍSTICAS DE LA DCCM\n")
            f.write(f"{'='*80}\n\n")
            f.write(f"Dimensión: {dccm_matrix.shape[0]} x {dccm_matrix.shape[0]}\n")
            f.write(f"Pares analizados: {len(correlations):,}\n\n")
            f.write(f"Correlación promedio: {np.mean(correlations):.4f}\n")
            f.write(f"Desviación estándar: {np.std(correlations):.4f}\n")
            f.write(f"Máximo: {np.max(correlations):.4f}\n")
            f.write(f"Mínimo: {np.min(correlations):.4f}\n\n")
            
            # Top correlaciones
            f.write("TOP 50 PARES MÁS CORRELACIONADOS (> 0.5):\n")
            f.write(f"{'-'*80}\n")
            high_corr_idx = np.where(upper_tri > 0.5)
            high_corr_vals = [dccm_matrix[i, j] for i, j in zip(*high_corr_idx)]
            
            # Ordenar por valor
            sorted_indices = np.argsort(high_corr_vals)[::-1][:50]
            
            for idx in sorted_indices:
                i = high_corr_idx[0][idx]
                j = high_corr_idx[1][idx]
                f.write(f"  Res {i+1:4d} ↔ Res {j+1:4d}: {dccm_matrix[i,j]:7.4f}\n")
            
            # Anti-correlaciones
            f.write(f"\nTOP 50 PARES MÁS ANTI-CORRELACIONADOS (< -0.3):\n")
            f.write(f"{'-'*80}\n")
            anti_corr_idx = np.where(upper_tri < -0.3)
            anti_corr_vals = [dccm_matrix[i, j] for i, j in zip(*anti_corr_idx)]
            
            # Ordenar por valor (más negativo primero)
            sorted_indices = np.argsort(anti_corr_vals)[:50]
            
            for idx in sorted_indices:
                i = anti_corr_idx[0][idx]
                j = anti_corr_idx[1][idx]
                f.write(f"  Res {i+1:4d} ↔ Res {j+1:4d}: {dccm_matrix[i,j]:7.4f}\n")
        
        print(f"\n✅ Estadísticas guardadas: {stats_file}")
    
    def visualize_dccm(self, dccm_matrix: np.ndarray):
        """Visualiza la DCCM como mapa de calor"""
        print(f"\n{'='*80}")
        print("PASO 4: Visualizando DCCM")
        print(f"{'='*80}")
        
        try:
            fig, ax = plt.subplots(figsize=(12, 10))
            
            im = ax.imshow(
                dccm_matrix,
                cmap='RdBu_r',  # Azul = negativo, Rojo = positivo
                vmin=-1.0,
                vmax=1.0,
                aspect='auto',
                origin='lower',
                interpolation='nearest'
            )
            
            cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
            cbar.set_label('Correlación Cruzada', rotation=270, labelpad=25, 
                          fontweight='bold', fontsize=11)
            
            n_res = dccm_matrix.shape[0]
            ax.set_xlabel('Número de Residuo', fontweight='bold', fontsize=12)
            ax.set_ylabel('Número de Residuo', fontweight='bold', fontsize=12)
            ax.set_title('Dynamic Cross-Correlation Matrix (DCCM)', 
                        fontweight='bold', fontsize=14, pad=20)
            
            # Ticks
            tick_spacing = max(50, n_res // 10)
            ticks = np.arange(0, n_res, tick_spacing)
            ax.set_xticks(ticks)
            ax.set_yticks(ticks)
            ax.set_xticklabels(ticks + 1)
            ax.set_yticklabels(ticks + 1)
            
            ax.grid(False)
            
            # Línea diagonal
            ax.plot([0, n_res-1], [0, n_res-1], 'k--', linewidth=0.5, alpha=0.3)
            
            # Añadir texto informativo
            textstr = f'Residuos: {n_res}\nRango: [-1, +1]'
            props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                   verticalalignment='top', bbox=props)
            
            plt.tight_layout()
            
            output_file = self.dccm_dir / 'dccm_matrix.png'
            plt.savefig(output_file, dpi=300, bbox_inches='tight')
            print(f"✅ Visualización guardada: {output_file}")
            plt.close()
            
            # Crear regiones
            self._create_dccm_regions(dccm_matrix)
            
        except Exception as e:
            print(f"❌ Error en visualización: {e}")
            import traceback
            traceback.print_exc()
    
    def _create_dccm_regions(self, dccm_matrix: np.ndarray):
        """Crea visualizaciones de regiones específicas"""
        print("\n🔎 Creando visualizaciones de regiones...")
        
        n_res = dccm_matrix.shape[0]
        
        if n_res > 200:
            mid = n_res // 2
            regions = [
                (0, mid, 0, mid, "Q1_N-terminal"),
                (0, mid, mid, n_res, "Q2_N-C_interaction"),
                (mid, n_res, 0, mid, "Q3_C-N_interaction"),
                (mid, n_res, mid, n_res, "Q4_C-terminal")
            ]
            
            for i_start, i_end, j_start, j_end, label in regions:
                fig, ax = plt.subplots(figsize=(10, 8))
                
                region = dccm_matrix[i_start:i_end, j_start:j_end]
                
                im = ax.imshow(
                    region,
                    cmap='RdBu_r',
                    vmin=-1.0,
                    vmax=1.0,
                    aspect='auto',
                    origin='lower',
                    interpolation='nearest'
                )
                
                plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
                
                ax.set_xlabel(f'Residuo {j_start+1}-{j_end}', fontweight='bold')
                ax.set_ylabel(f'Residuo {i_start+1}-{i_end}', fontweight='bold')
                ax.set_title(f'DCCM - {label}', fontweight='bold', fontsize=12)
                
                plt.tight_layout()
                plt.savefig(self.dccm_dir / f'dccm_region_{label}.png', dpi=200)
                plt.close()
            
            print(f"✅ Creadas 4 regiones de zoom")
    
    def run_full_analysis(self, selection: str = "C-alpha", max_residues: int = 2000, 
                         max_frames: int = None):
        """Ejecuta análisis completo de DCCM"""
        print(f"\n{'='*80}")
        print("INICIANDO ANÁLISIS COMPLETO DE DCCM")
        print(f"{'='*80}\n")
        
        # Paso 1: Extraer trayectoria
        traj_pdb = self.extract_calpha_trajectory(selection)
        if traj_pdb is None:
            print("\n❌ Error extrayendo trayectoria. Abortando.")
            return False
        
        # Paso 2: Leer coordenadas
        try:
            coords = self.parse_pdb_trajectory(traj_pdb, max_frames)
        except Exception as e:
            print(f"\n❌ Error leyendo coordenadas: {e}")
            return False
        
        # Paso 3: Calcular DCCM
        dccm_matrix = self.compute_dccm_from_trajectory(coords, max_residues)
        if dccm_matrix is None:
            print("\n❌ Error en cálculo de DCCM. Abortando.")
            return False
        
        # Paso 4: Visualizar
        self.visualize_dccm(dccm_matrix)
        
        print(f"\n{'='*80}")
        print("✅ ANÁLISIS DCCM COMPLETADO")
        print(f"{'='*80}")
        print(f"\n📊 Resultados en: {self.dccm_dir}")
        print(f"  - dccm_matrix.dat (matriz numérica)")
        print(f"  - dccm_matrix.png (visualización completa)")
        print(f"  - dccm_region_*.png (visualizaciones regionales)")
        print(f"  - dccm_statistics.txt (estadísticas detalladas)")
        print(f"{'='*80}\n")
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Dynamic Cross-Correlation Matrix (DCCM) Analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-d', '--directory', type=str, required=True,
                       help='Directorio con resultados de MD')
    parser.add_argument('-g', '--gmx-bin', type=str, default='gmx',
                       help='Ruta al ejecutable de GROMACS')
    parser.add_argument('-s', '--selection', type=str,
                       choices=['C-alpha', 'Backbone', 'Protein'],
                       default='C-alpha',
                       help='Selección de átomos')
    parser.add_argument('--max-residues', type=int, default=2000,
                       help='Número máximo de residuos')
    parser.add_argument('--max-frames', type=int, default=None,
                       help='Número máximo de frames (None = todos)')
    
    args = parser.parse_args()
    
    if not Path(args.directory).exists():
        print(f"❌ Error: Directorio no encontrado: {args.directory}")
        sys.exit(1)
    
    required_files = ['md_1_center.xtc', 'md_1.tpr', 'index.ndx']
    for filename in required_files:
        filepath = Path(args.directory) / filename
        if not filepath.exists():
            print(f"❌ Error: Archivo requerido no encontrado: {filename}")
            sys.exit(1)
    
    analyzer = DCCMAnalyzer(args.directory, args.gmx_bin)
    success = analyzer.run_full_analysis(args.selection, args.max_residues, args.max_frames)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()