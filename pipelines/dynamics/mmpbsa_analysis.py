import os
import sys
import subprocess
import shutil
import re
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c']


class GMX_MMPBSA_Analyzer:
    
    def __init__(self, results_dir: str, gmx_bin: str = None):
        self.results_dir = Path(results_dir)
        self.binding_dir = self.results_dir / 'analisis_binding_energy'
        self.gmx_mmpbsa_dir = self.binding_dir / 'gmx_MMPBSA'
        
        self.gmx_mmpbsa_dir.mkdir(parents=True, exist_ok=True)
        
        self.gmx_bin = gmx_bin
        
        if not self.gmx_bin:
            raise RuntimeError("❌ No se encontró gmx_mpi ni gmx en el sistema.")
            
        print(f"✅ GROMACS detectado: {self.gmx_bin}")
        print("ℹ️  Modo serial forzado para gmx_MMPBSA por compatibilidad con gmx_mpi.")
    
    def detect_groups(self):
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
        print("📊 Detectando frames disponibles...")
        
        traj_file = self.results_dir / 'md_center.xtc'
            
        if not traj_file.exists():
            print(f"   ⚠️  Trayectoria {traj_file.name} no encontrada, usando 500 por defecto")
            return 500
        
        try:
            cmd = [self.gmx_bin, 'check', '-f', str(traj_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            output = result.stdout + result.stderr
            # Buscamos 'Step' seguido de números
            frames = re.findall(r'Step\s+(\d+)', output)
            if frames:
                n_frames = int(frames[-1])
                print(f"   ✅ Frames detectados: {n_frames:,}")
                return n_frames
            
            return 1000 
                
        except Exception as e:
            print(f"   ⚠️  Error detectando frames: {e}")
            return 1000
    
    def find_ligand_files(self):
        """Busca archivos del ligando - Retorna None,None si no existen"""
        print("🔍 Buscando archivos del ligando...")
        
        acpype_dir = self.results_dir / 'acpype_work'
        
        # Buscar directorio .acpype
        acpype_subdirs = list(acpype_dir.glob('*.acpype')) if acpype_dir.exists() else []
        
        if not acpype_subdirs:
            print(f"❌ Directorio ACPYPE no encontrado - Análisis sin ligando o fallo en generación de parámetros")
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
    
    def run_gmx_mmpbsa(self, protein_group: int, ligand_group: int, use_pb: bool = False, n_frames: int = None) -> bool:
        """Ejecuta gmx_MMPBSA SIEMPRE en modo serial para evitar conflictos de MPI"""
        print("="*70)
        print("EJECUTANDO gmx_MMPBSA (MODO SERIAL)")
        print("="*70 + "\n")
        
        if n_frames is None:
            n_frames = self.detect_available_frames()

        mol2_file, frcmod_file = self.find_ligand_files()
        
        local_mol2 = None
        if mol2_file:
            local_mol2 = self.gmx_mmpbsa_dir / mol2_file.name
            shutil.copy2(mol2_file, local_mol2)
            if frcmod_file:
                shutil.copy2(frcmod_file, self.gmx_mmpbsa_dir / frcmod_file.name)
        
        # Crear archivo de entrada y obtener ruta absoluta
        input_file_path = self.create_input_file(use_gb=True, use_pb=use_pb, n_frames=n_frames)
        input_abs = os.path.abspath(input_file_path) 
        
        gmx_mmpbsa_path = shutil.which('gmx_MMPBSA')

        # Convertir archivos de GROMACS a rutas absolutas
        tpr_abs = os.path.abspath(self.results_dir / 'md.tpr')
        ndx_abs = os.path.abspath(self.results_dir / 'index.ndx')
        xtc_abs = os.path.abspath(self.results_dir / 'md_center.xtc')
        top_abs = os.path.abspath(self.results_dir / 'topol.top')
        
        if not os.path.exists(tpr_abs):
            print(f"❌ Error: El archivo TPR no existe en: {tpr_abs}")
            return False

        # Construcción del comando SERIAL (sin mpirun ni flag MPI)
        # Nota: gmx_MMPBSA detectará gmx_mpi internamente a través de GMX_BIN
        cmd_list = [
            gmx_mmpbsa_path,
            '-O',
            '-i', input_abs,  
            '-cs', tpr_abs,
            '-ci', ndx_abs,
            '-cg', str(protein_group), str(ligand_group),
            '-ct', xtc_abs,
            '-nogui'
        ]

        if local_mol2:
            cmd_list.extend(['-lm', os.path.abspath(local_mol2)])
        
        if os.path.exists(top_abs):
            cmd_list.extend(['-cp', top_abs])

        # Limpiar comando de valores None y asegurar strings
        cmd = [str(item) for item in cmd_list if item is not None]
        
        # Inyectar el binario gmx_mpi para que gmx_MMPBSA lo use internamente
        env = os.environ.copy()
        env["GMX_BIN"] = self.gmx_bin # Aquí sigue yendo la ruta a gmx_mpi

        try:
            print(f"🚀 Lanzando gmx_MMPBSA en serial usando binario: {self.gmx_bin}")
            result = subprocess.run(
                cmd, 
                cwd=str(self.gmx_mmpbsa_dir), 
                check=True,
                capture_output=True,
                text=True,
                env=env
            )
            print("✅ gmx_MMPBSA finalizó correctamente.")
            return True
        except subprocess.CalledProcessError as e:
            # Capturar errores y guardarlos en log
            error_msg = e.stderr if e.stderr else e.stdout
            print(f"❌ Error en gmx_MMPBSA: {error_msg}")
            with open(self.gmx_mmpbsa_dir / "error_mmpbsa.log", "w") as f:
                f.write(error_msg)
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
                    if ('DELTA' in line or 'Δ' in line) and ('TOTAL' in line or 'G binding' in line):
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
                    if ('DELTA' in line or 'Δ' in line) and ('TOTAL' in line or 'G binding' in line):
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
                    if ('DELTA' in line or 'Δ' in line) and 'TOTAL' in line:
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

