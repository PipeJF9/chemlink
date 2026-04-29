#!/usr/bin/env python3
"""
MM-PBSA & MM-GBSA Free Energy Analysis
VERSIÓN CORREGIDA: MPI funcionando + Extracción de energías mejorada
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
import re

# CONFIGURACIÓN HARDCODEADA
CONDA_BASE = Path("/home/ChemFusion/funciones/Aplicaciones/miniconda3")
CONDA_ENV = "gmx_mmpbsa"
MPIRUN_PATH = Path("/home/ChemFusion/funciones/Aplicaciones/miniconda3/envs/gmx_mmpbsa/bin/mpirun")

# Verificar MPI ANTES de imports
print("🔍 Verificación inicial de MPI...")
print(f"   Ruta: {MPIRUN_PATH}")
print(f"   Existe: {MPIRUN_PATH.exists()}")
MPI_AVAILABLE = MPIRUN_PATH.exists()
if MPI_AVAILABLE:
    print("   ✅ MPI disponible")
else:
    print("   ❌ MPI NO disponible")
print()

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c']


class GMX_MMPBSA_Analyzer:
    """Analizador de energía libre usando gmx_MMPBSA"""
    
    def __init__(self, results_dir: str, use_mpi: bool = False, n_cores: int = None):
        self.results_dir = Path(results_dir)
        self.binding_dir = self.results_dir / 'analisis_binding_energy'
        self.binding_dir.mkdir(exist_ok=True)
        self.gmx_mmpbsa_dir = self.binding_dir / 'gmx_MMPBSA'
        self.gmx_mmpbsa_dir.mkdir(exist_ok=True)
        
        # Usar la variable global
        self.mpi_available = MPI_AVAILABLE
        
        # Lógica de MPI
        if n_cores is not None and n_cores > 1:
            if self.mpi_available:
                self.use_mpi = True
                self.n_cores = n_cores
                print(f"🚀 MPI HABILITADO con {n_cores} núcleos")
            else:
                print("⚠️  MPI solicitado pero no disponible - usando modo serial")
                self.use_mpi = False
                self.n_cores = 1
        else:
            self.use_mpi = use_mpi and self.mpi_available
            self.n_cores = 4 if self.use_mpi else 1
            if self.use_mpi:
                print(f"🚀 MPI HABILITADO con {self.n_cores} núcleos")
        
        print(f"{'='*70}")
        print(f"Directorio: {self.results_dir}")
        print(f"Salida: {self.gmx_mmpbsa_dir}")
        print(f"Modo: {'MPI paralelo (%d cores)' % self.n_cores if self.use_mpi else 'Serial'}")
        print()
    
    def detect_groups(self):
        """Detecta grupos del sistema"""
        print("🔍 Detectando grupos...")
        
        index_file = self.results_dir / 'index.ndx'
        if not index_file.exists():
            print("❌ index.ndx no encontrado")
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
                print(f"✅ Proteína: [{num}] {name}")
                break
        
        ligand_group = None
        for name, num in groups.items():
            if any(kw in name for kw in ['LIG', 'Lig', 'ligand', 'Other']) and 'Protein' not in name:
                ligand_group = num
                print(f"✅ Ligando: [{num}] {name}\n")
                break
        
        return protein_group, ligand_group
    
    def detect_available_frames(self):
        """Detecta frames disponibles"""
        print("📊 Detectando frames disponibles...")
        
        traj_file = self.results_dir / 'md_1_center.xtc'
        if not traj_file.exists():
            print("   ⚠️  Trayectoria no encontrada, usando 500 por defecto")
            return 500
        
        try:
            cmd = ['gmx', 'check', '-f', str(traj_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            for line in result.stdout.split('\n') + result.stderr.split('\n'):
                if 'Last frame' in line:
                    match = re.search(r'Last frame\s+(\d+)', line)
                    if match:
                        n_frames = int(match.group(1))
                        print(f"   ✅ Frames detectados: {n_frames:,}")
                        return n_frames
            
            print("   🔎 Método alternativo...")
            cmd = ['gmx', 'dump', '-f', str(traj_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            frame_count = result.stdout.count('frame')
            if frame_count > 0:
                print(f"   ✅ Frames contados: {frame_count:,}")
                return frame_count
            
            file_size_mb = traj_file.stat().st_size / (1024**2)
            estimated_frames = int(file_size_mb * 1024 / 20)
            estimated_frames = max(100, min(estimated_frames, 50000))
            print(f"   📦 Estimación: {estimated_frames:,} frames")
            return estimated_frames
                
        except subprocess.TimeoutExpired:
            return 1000
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
            return 1000
    
    def find_ligand_files(self):
        """Busca archivos del ligando - Retorna None,None si no existen"""
        print("🔍 Buscando archivos del ligando...")
        
        acpype_dir = self.results_dir / 'acpype_work'
        
        # Buscar directorio .acpype
        acpype_subdirs = list(acpype_dir.glob('*.acpype')) if acpype_dir.exists() else []
        
        if not acpype_subdirs:
            print(f"❌ Directorio ACPYPE no encontrado - proteína-proteína sin ligando pequeño")
            return None, None
        
        acpype_dir = acpype_subdirs[0]
        
        mol2_gaff2 = list(acpype_dir.glob('*_gaff2.mol2'))
        mol2_gaff = list(acpype_dir.glob('*_gaff.mol2'))
        mol2_ac = list(acpype_dir.glob('*_AC.mol2'))
        mol2_default = list(acpype_dir.glob('LIG.mol2'))
        
        mol2_file = None
        if mol2_gaff2:
            mol2_file = mol2_gaff2[0]
            print(f"✅ MOL2 (GAFF2): {mol2_file.name}")
        elif mol2_gaff:
            mol2_file = mol2_gaff[0]
            print(f"✅ MOL2 (GAFF): {mol2_file.name}")
        elif mol2_ac:
            mol2_file = mol2_ac[0]
            print(f"⚠️  MOL2 (AC): {mol2_file.name}")
        elif mol2_default:
            mol2_file = mol2_default[0]
            print(f"⚠️  MOL2 (default): {mol2_file.name}")
        else:
            print(f"❌ No se encontró archivo MOL2")
            return None, None
        
        frcmod_file = None
        if mol2_file:
            base_name = mol2_file.stem
            frcmod_candidates = [
                acpype_dir / f"{base_name}.frcmod",
                acpype_dir / "LIG.frcmod",
                *list(acpype_dir.glob('*.frcmod'))
            ]
            
            for f in frcmod_candidates:
                if f.exists():
                    frcmod_file = f
                    print(f"✅ FRCMOD: {frcmod_file.name}")
                    break
        
        print()
        return mol2_file, frcmod_file
    
    def create_input_file(self, use_gb=True, use_pb=False, n_frames=None):
        """Crea archivo de entrada"""
        input_file = self.gmx_mmpbsa_dir / 'mmpbsa.in'
        
        if n_frames is None:
            n_frames = self.detect_available_frames()
        
        if n_frames < 500:
            start_frame = 1
            end_frame = n_frames
            interval = 1
            frames_calc = n_frames
        elif n_frames < 5000:
            start_frame = int(n_frames * 0.2)
            end_frame = n_frames
            interval = max(1, (end_frame - start_frame) // 500)
            frames_calc = (end_frame - start_frame) // interval
        else:
            start_frame = int(n_frames * 0.2)
            end_frame = n_frames
            interval = max(5, (end_frame - start_frame) // 1000)
            frames_calc = (end_frame - start_frame) // interval
        
        config = [
            "&general",
            f"startframe={start_frame},",
            f"endframe={end_frame},",
            f"interval={interval},",
            "/",
            ""
        ]
        
        if use_gb:
            config.extend([
                "&gb",
                "igb=5,",
                "saltcon=0.150,",
                "/",
                ""
            ])
        
        if use_pb:
            config.extend([
                "&pb",
                "istrng=0.150,",
                "/",
                ""
            ])
        
        with open(input_file, 'w') as f:
            f.write('\n'.join(config))
        
        print(f"✅ Configuración MM-PBSA:")
        print(f"   Frames totales: {n_frames}")
        print(f"   Rango: {start_frame}-{end_frame} (intervalo {interval})")
        print(f"   Cálculos: {frames_calc}")
        print(f"   GB: {'✅' if use_gb else '❌'}")
        print(f"   PB: {'✅' if use_pb else '❌'}")
        
        time_per_frame = 8 if use_pb else 3
        estimated_min = (time_per_frame * frames_calc) // 60
        print(f"   ⏱️  Tiempo estimado: ~{max(1, estimated_min)} minutos")
        print()
        
        return input_file
    
    def run_gmx_mmpbsa(self, protein_group: int, ligand_group: int,
                       use_pb: bool = False, n_frames: int = None) -> bool:
        """Ejecuta gmx_MMPBSA - OPTIMIZADO PARA PROTEÍNA-PROTEÍNA"""
        print("="*70)
        print("EJECUTANDO gmx_MMPBSA")
        print("="*70 + "\n")
        
        if n_frames is None:
            n_frames = self.detect_available_frames()
        
        # Para proteína-proteína, INTENTAMOS buscar ligando pero sin fallar si no existe
        mol2_file, frcmod_file = None, None
        
        # Intentar encontrar archivos de ligando (para proteína-ligando)
        try:
            mol2_file, frcmod_file = self.find_ligand_files()
        except Exception as e:
            print(f"⚠️  No se encontraron archivos de ligando: {str(e)[:100]}")
            print("    Continuando con análisis proteína-proteína puro...")
        
        local_mol2 = None
        if mol2_file is None:
            print("ℹ️  Analizando como proteína-proteína (sin ligando pequeño)")
            is_protein_protein = True
        else:
            print("ℹ️  Analizando como proteína-ligando")
            is_protein_protein = False
            local_mol2 = self.gmx_mmpbsa_dir / mol2_file.name
            try:
                shutil.copy2(mol2_file, local_mol2)
            except Exception as e:
                print(f"⚠️  Error copiando MOL2: {e}")
                local_mol2 = None
                is_protein_protein = True

            if frcmod_file and local_mol2:
                try:
                    local_frcmod = self.gmx_mmpbsa_dir / frcmod_file.name
                    shutil.copy2(frcmod_file, local_frcmod)
                except Exception as e:
                    print(f"⚠️  Error copiando FRCMOD: {e}")
        
        input_file = self.create_input_file(use_gb=True, use_pb=use_pb, n_frames=n_frames)
        
        gmx_mmpbsa_path = shutil.which('gmx_MMPBSA')
        if not gmx_mmpbsa_path:
            print("❌ gmx_MMPBSA no encontrado en PATH")
            return False
        
        print(f"🔧 Usando: {gmx_mmpbsa_path}\n")
        
        # Comando base (sin MPI primero)
        base_cmd = [
            '-O',
            '-i', str(input_file),
            '-cs', str(self.results_dir / 'md_1.tpr'),
            '-ci', str(self.results_dir / 'index.ndx'),
            '-cg', str(protein_group), str(ligand_group),
            '-ct', str(self.results_dir / 'md_1_center.xtc'),
        ]

        # Añadir archivo de ligando SOLO si existe (para proteína-ligando)
        if local_mol2 is not None and local_mol2.exists():
            base_cmd.extend(['-lm', str(local_mol2)])
        
        
        topology = self.results_dir / 'topol.top'
        if topology.exists():
            base_cmd.extend(['-cp', str(topology)])
        
        # Construcción del comando
        if self.use_mpi and MPIRUN_PATH.exists():
            # Modo MPI: mpirun -np N gmx_MMPBSA MPI [args]
            # Para proteína-proteína, usar solo 1 core por defecto
            n_cores_to_use = 1 if is_protein_protein else self.n_cores
            
            cmd = [
                str(MPIRUN_PATH),
                '-np', str(n_cores_to_use),
                gmx_mmpbsa_path,
                'MPI'
            ] + base_cmd
            
            actual_mode = f"MPI ({n_cores_to_use} núcleo{'s' if n_cores_to_use > 1 else ''})"
            print(f"🚀 Modo: {actual_mode}")
            print(f"   mpirun: {MPIRUN_PATH}")
            print(f"   Núcleos: {n_cores_to_use}")
        else:
            # Modo Serial: gmx_MMPBSA [args]
            cmd = [gmx_mmpbsa_path] + base_cmd
            actual_mode = "Serial"
            print(f"🏃 Modo: {actual_mode}")
        
        print(f"\n📝 Comando:")
        print(f"   {' '.join(cmd)}\n")
        
        log_file = self.gmx_mmpbsa_dir / 'gmx_mmpbsa.log'
        error_file = self.gmx_mmpbsa_dir / 'gmx_mmpbsa.err'
        
        print("⏳ Iniciando cálculo...")
        TIMEOUT_SECONDS = 28800  # 480 minutos
        print(f"   Timeout: {TIMEOUT_SECONDS // 60} minutos\n")
        
        try:
            with open(log_file, 'w') as log_out, open(error_file, 'w') as err_out:
                process = subprocess.run(
                    cmd,
                    cwd=str(self.gmx_mmpbsa_dir),
                    stdout=log_out,
                    stderr=err_out,
                    timeout=TIMEOUT_SECONDS,
                    env=os.environ.copy()
                )
            
            if process.returncode == 0:
                print(f"\n✅ Cálculo completado ({actual_mode})\n")
                return True
            else:
                print(f"\n❌ Error (código {process.returncode})")
                print(f"   Logs: {log_file}\n")
                
                with open(error_file, 'r') as f:
                    error_lines = f.readlines()
                    if error_lines:
                        print("Últimas líneas del error:")
                        for line in error_lines[-10:]:
                            print(f"   {line.rstrip()}")
                
                return False
                
        except subprocess.TimeoutExpired:
            print(f"\n❌ Timeout\n")
            return False
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            return False
    
    def extract_energies(self):
        """Extrae energías - MEJORADO"""
        print("📊 Extrayendo energías...\n")
        
        energies = {'GB': {}, 'PB': {}}
        dat_file = self.gmx_mmpbsa_dir / 'FINAL_RESULTS_MMPBSA.dat'
        
        if not dat_file.exists():
            print("⚠️  Archivo de resultados no encontrado")
            return energies
        
        try:
            with open(dat_file, 'r') as f:
                content = f.read()
            
            # Extraer GB
            if 'GENERALIZED BORN' in content:
                gb_section = content.split('GENERALIZED BORN')[1]
                if 'POISSON BOLTZMANN' in gb_section:
                    gb_section = gb_section.split('POISSON BOLTZMANN')[0]
                
                for line in gb_section.split('\n'):
                    if 'DELTA TOTAL' in line or 'DELTA G binding' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                energies['GB']['total_mean'] = float(parts[-2])
                                energies['GB']['total_std'] = float(parts[-1])
                                print(f"   ΔG (GB) = {parts[-2]} ± {parts[-1]} kcal/mol")
                                break
                            except:
                                continue
            
            # Extraer PB
            if 'POISSON BOLTZMANN' in content:
                pb_section = content.split('POISSON BOLTZMANN')[1]
                
                for line in pb_section.split('\n'):
                    if 'DELTA TOTAL' in line or 'DELTA G binding' in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                energies['PB']['total_mean'] = float(parts[-2])
                                energies['PB']['total_std'] = float(parts[-1])
                                print(f"   ΔG (PB) = {parts[-2]} ± {parts[-1]} kcal/mol")
                                break
                            except:
                                continue
            
            # Si no se encontraron energías, buscar en todo el archivo
            if not energies['GB'] and not energies['PB']:
                print("   ⚠️  Búsqueda alternativa...")
                for line in content.split('\n'):
                    if 'TOTAL' in line and 'DELTA' in line:
                        print(f"   Línea encontrada: {line.strip()}")
        
        except Exception as e:
            print(f"   ⚠️  Error: {e}")
        
        print()
        return energies
    
    def plot_results(self, energies):
        """Genera gráficas"""
        print("📈 Generando gráficas...\n")
        
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
        
        if not methods:
            print("   ⚠️  No hay energías para graficar")
            return
        
        fig, ax = plt.subplots(figsize=(10, 6))
        x_pos = np.arange(len(methods))
        
        bars = ax.bar(x_pos, means, yerr=stds, capsize=10,
                     color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)
        
        for bar, mean, std in zip(bars, means, stds):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + std + 0.5,
                   f'{mean:.2f} ± {std:.2f}\nkcal/mol',
                   ha='center', va='bottom', fontweight='bold')
        
        ax.set_ylabel('ΔG_bind (kcal/mol)', fontweight='bold', fontsize=12)
        ax.set_title('Energía Libre de Unión', fontweight='bold', fontsize=14)
        ax.set_xticks(x_pos)
        ax.set_xticklabels(methods, fontweight='bold', fontsize=11)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax.grid(True, axis='y', alpha=0.3)
        
        plt.tight_layout()
        output = self.gmx_mmpbsa_dir / 'binding_energy.png'
        plt.savefig(output, dpi=300, bbox_inches='tight')
        print(f"   ✓ {output.name}")
        plt.close()
    
    def generate_report(self, energies):
        """Genera reporte"""
        report = [
            "="*70,
            "REPORTE gmx_MMPBSA",
            "="*70,
            "",
            "RESULTADOS:",
            "-"*70
        ]
        
        if energies['GB'].get('total_mean'):
            gb = energies['GB']
            report.append(f"\nMM-GBSA:")
            report.append(f"  ΔG_bind = {gb['total_mean']:.2f} ± {gb['total_std']:.2f} kcal/mol")
        
        if energies['PB'].get('total_mean'):
            pb = energies['PB']
            report.append(f"\nMM-PBSA:")
            report.append(f"  ΔG_bind = {pb['total_mean']:.2f} ± {pb['total_std']:.2f} kcal/mol")
        
        if not energies['GB'] and not energies['PB']:
            report.append("\n⚠️  No se pudieron extraer energías")
            report.append("    Revisa FINAL_RESULTS_MMPBSA.dat manualmente")
        
        report.extend([
            "",
            "INTERPRETACIÓN:",
            "-"*70,
            "• ΔG < 0: Unión favorable",
            "• ΔG > 0: Unión desfavorable",
            "",
            "="*70
        ])
        
        report_file = self.gmx_mmpbsa_dir / 'SUMMARY_REPORT.txt'
        with open(report_file, 'w') as f:
            f.write('\n'.join(report))
        
        print('\n'.join(report))
        print(f"\n✅ Reporte: {report_file.name}\n")
    
    def run_analysis(self, use_pb: bool = False, n_frames: int = None) -> bool:
        """Ejecuta análisis completo"""
        protein_group, ligand_group = self.detect_groups()
        if protein_group is None or ligand_group is None:
            print("❌ Grupos no detectados")
            return False
        
        if not self.run_gmx_mmpbsa(protein_group, ligand_group, use_pb, n_frames):
            return False
        
        energies = self.extract_energies()
        self.plot_results(energies)
        self.generate_report(energies)
        
        print("="*70)
        print("✅ ANÁLISIS COMPLETADO")
        print("="*70)
        print(f"📊 Resultados: {self.gmx_mmpbsa_dir}")
        print("="*70 + "\n")
        
        return True


def main():
    parser = argparse.ArgumentParser(description='Análisis MM-PBSA/MM-GBSA')
    parser.add_argument('-d', '--directory', required=True, help='Directorio MD')
    parser.add_argument('--pb', action='store_true', help='Activar MM-PBSA')
    parser.add_argument('--mpi', action='store_true', help='Usar MPI')
    parser.add_argument('--cores', type=int, default=6, help='Número de núcleos')
    parser.add_argument('--frames', type=int, default=None, help='Número de frames')
    args = parser.parse_args()
    
    if not Path(args.directory).exists():
        print(f"❌ Directorio no encontrado: {args.directory}")
        sys.exit(1)
    
    use_mpi = args.mpi
    n_cores = args.cores if use_mpi else None
    
    print(f"\n{'='*70}")
    print("CONFIGURACIÓN:")
    print(f"{'='*70}")
    print(f"MPI solicitado: {'Sí' if use_mpi else 'NO'}")
    print(f"Núcleos: {n_cores if n_cores else 'N/A'}")
    print(f"Ruta MPI: {MPIRUN_PATH}")
    print(f"MPI existe: {MPIRUN_PATH.exists()}")
    print(f"MPI disponible: {MPI_AVAILABLE}")
    print(f"{'='*70}\n")
    
    analyzer = GMX_MMPBSA_Analyzer(args.directory, use_mpi=use_mpi, n_cores=n_cores)
    success = analyzer.run_analysis(use_pb=args.pb, n_frames=args.frames)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()