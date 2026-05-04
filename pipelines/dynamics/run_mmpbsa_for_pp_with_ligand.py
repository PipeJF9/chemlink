#!/usr/bin/env python3
"""
MM-PBSA Analysis para PROTEINA-PROTEINA (Sistema con 2 cadenas proteicas)
===========================================================================

Sistema: Dos cadenas proteicas (A y B)
Analisis: Calcula la energia de union entre las dos proteinas

La energia de union se calcula como:
  ΔG_binding = E(Proteina_A + Proteina_B) - E(Proteina_A) - E(Proteina_B)

NOTA: Este script IGNORA cofactores, ligandos pequeños y otros elementos.
      Solo analiza la interaccion entre las dos cadenas proteicas principales.

Uso:
  python3 run_mmpbsa_for_pp_with_ligand.py -d <results_dir>
"""

import os
import sys
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('mmpbsa_pp.log')
    ]
)
logger = logging.getLogger(__name__)


def log_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def detect_protein_chains(pdb_file):
    """Detecta las dos cadenas proteicas principales (por numero de residuos)."""
    chains_info = {}
    
    with open(pdb_file, 'r') as f:
        for line in f:
            if line.startswith('ATOM'):  # SOLO ATOM, no HETATM
                chain = line[21] if len(line) > 21 else ' '
                if chain.strip():
                    if chain not in chains_info:
                        chains_info[chain] = {'atoms': [], 'residues': set()}
                    
                    atom_num = int(line[6:11].strip())
                    res_seq = line[22:26].strip()
                    
                    chains_info[chain]['atoms'].append(atom_num)
                    chains_info[chain]['residues'].add(res_seq)
    
    # Ordenar por tamaño (numero de residuos)
    sorted_chains = sorted(
        chains_info.items(),
        key=lambda x: len(x[1]['residues']),
        reverse=True
    )
    
    return sorted_chains


def get_atom_indices_for_chain(pdb_file, chain_id):
    """Extract atom indices for a specific chain from PDB file (SOLO ATOM)."""
    indices = []
    try:
        with open(pdb_file, 'r') as f:
            for line in f:
                if line.startswith('ATOM'):  # SOLO ATOM
                    if len(line) > 21 and line[21] == chain_id:
                        atom_num = int(line[6:11].strip())
                        indices.append(atom_num)
    except Exception as e:
        logger.error(f"Error reading PDB file {pdb_file}: {e}")
        return []
    
    return sorted(indices)


def create_index_file_pp_pure(pdb_file, output_ndx):
    """
    Crea index.ndx para sistema Proteina-Proteina PURO.
    
    ESTRUCTURA REQUERIDA:
    =====================
    [ Protein ]     ← Grupo 0: Cadena A (proteina mas grande)
    [ Other ]       ← Grupo 1: Cadena B (segunda proteina)
    
    gmx_MMPBSA usara estos grupos para calcular:
    ΔG = E(Protein + Other) - E(Protein) - E(Other)
    
    NOTA: Se IGNORAN completamente HETATM (cofactores, ligandos, etc.)
    """
    try:
        logger.info("Leyendo estructura PDB y detectando componentes...")
        
        # Detectar cadenas PROTEICAS (solo ATOM records)
        sorted_chains = detect_protein_chains(pdb_file)
        
        if len(sorted_chains) < 2:
            logger.error("Se requieren al menos 2 cadenas proteicas (ATOM records)")
            return False
        
        # Las dos cadenas mas grandes
        chain_a = sorted_chains[0][0]
        chain_b = sorted_chains[1][0]
        
        atoms_a = get_atom_indices_for_chain(pdb_file, chain_a)
        atoms_b = get_atom_indices_for_chain(pdb_file, chain_b)
        
        if not atoms_a or not atoms_b:
            logger.error("No se encontraron ambas cadenas proteicas")
            return False
        
        logger.info(f"Cadena A ('{chain_a}'): {len(atoms_a)} atomos ({len(atoms_a)//6} residuos aprox.)")
        logger.info(f"Cadena B ('{chain_b}'): {len(atoms_b)} atomos ({len(atoms_b)//6} residuos aprox.)")
        
        # IGNORAR completamente HETATM
        logger.info("NOTA: HETATM (cofactores/ligandos) seran IGNORADOS para este analisis")
        
        # Crear archivo index.ndx
        logger.info(f"\nCreando index.ndx para MM-PBSA...")
        
        with open(output_ndx, 'w') as f:
            # Grupo 0: Proteina A
            f.write(f"[ Protein ]\n")
            for i, atom in enumerate(atoms_a):
                if i % 15 == 0 and i != 0:
                    f.write("\n")
                f.write(f"{atom} ")
            f.write("\n\n")
            
            # Grupo 1: Proteina B
            f.write(f"[ Other ]\n")
            for i, atom in enumerate(atoms_b):
                if i % 15 == 0 and i != 0:
                    f.write("\n")
                f.write(f"{atom} ")
            f.write("\n")
        
        logger.info(f"index.ndx creado exitosamente")
        logger.info(f"\n   Grupos para gmx_MMPBSA:")
        logger.info(f"   [0] Protein (Cadena {chain_a})")
        logger.info(f"   [1] Other (Cadena {chain_b})")
        logger.info(f"\n   Usar: -cg 0 1")
        logger.info(f"   (Receptor = Grupo 0, Ligando = Grupo 1)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creando index.ndx: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def ensure_pdb_prepared(results_dir):
    """Asegurar que md_1.pdb existe y es valido."""
    pdb_path = os.path.join(results_dir, 'md_1.pdb')
    
    if not os.path.exists(pdb_path):
        logger.warn(f"PDB no encontrado: {pdb_path}")
        
        gro_path = os.path.join(results_dir, 'md_1.gro')
        if os.path.exists(gro_path):
            logger.info(f"Convirtiendo {gro_path} a PDB...")
            try:
                cmd = f"echo 'System' | gmx editconf -f {gro_path} -o {pdb_path} 2>/dev/null"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0 and os.path.exists(pdb_path):
                    logger.info(f"PDB creado desde GRO")
                    return pdb_path
            except Exception as e:
                logger.warn(f"No se pudo convertir: {e}")
        
        return None
    
    logger.info(f"PDB encontrado: {pdb_path}")
    return pdb_path


def run_mmpbsa_analysis(results_dir):
    """Ejecuta gmx_MMPBSA para Proteina-Proteina PURA (sin cofactores)."""
    log_section("MM-PBSA Analysis: PROTEINA-PROTEINA")
    
    logger.info("Este analisis calcula la energia de union ENTRE LAS DOS PROTEINAS")
    logger.info("IGNORANDO completamente cofactores, ligandos y otros HETATM.")
    logger.info("")
    
    # 1. Preparar PDB
    pdb_file = ensure_pdb_prepared(results_dir)
    if not pdb_file:
        logger.error("No se pudo preparar PDB")
        return False
    
    # 2. Crear indices
    index_file = os.path.join(results_dir, 'index.ndx')
    logger.info("\nCreando indices para gmx_MMPBSA...")
    
    if not create_index_file_pp_pure(pdb_file, index_file):
        logger.error("Error creando index.ndx")
        return False
    
    # 3. Preparar directorio de salida
    output_dir = os.path.join(results_dir, 'analisis_binding_energy', 'gmx_MMPBSA')
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"\nDirectorio de salida: {output_dir}")
    
    # 4. Verificar archivos necesarios
    traj_file = os.path.join(results_dir, 'md_1_center.xtc')
    tpr_file = os.path.join(results_dir, 'md_1.tpr')
    
    logger.info("\nVerificando archivos necesarios...")
    
    if not os.path.exists(traj_file):
        logger.error(f"Trayectoria no encontrada: {traj_file}")
        return False
    logger.info(f"Trayectoria: {traj_file}")
    
    if not os.path.exists(tpr_file):
        logger.error(f"TPR no encontrado: {tpr_file}")
        return False
    logger.info(f"TPR: {tpr_file}")
    
    if not os.path.exists(index_file):
        logger.error(f"Index no encontrado: {index_file}")
        return False
    logger.info(f"Index: {index_file}")
    
    # 5. Llamar a mmpbsa_analysis.py con configuracion correcta
    log_section("Ejecutando gmx_MMPBSA para Proteina-Proteina")
    
    try:
        import sys
        sys.path.insert(0, '/home/ChemFusion/funciones')
        
        from mmpbsa_analysis import GMX_MMPBSA_Analyzer
        
        logger.info("Iniciando gmx_MMPBSA...")
        logger.info("   Modo: Proteina-Proteina PURA")
        logger.info("   Metodo: Serial (sin MPI por defecto)")
        
        analyzer = GMX_MMPBSA_Analyzer(
            results_dir=results_dir,
            use_mpi=False,  # Serial mode por defecto para PP
            n_cores=1
        )
        
        # Para PP, el modulo usa automaticamente grupos 0 y 1
        # Nuestro index.ndx ahora tiene:
        # [0] Protein (Cadena A)
        # [1] Other (Cadena B)
        
        success = analyzer.run_analysis(use_pb=True, n_frames=None)
        
        if not success:
            logger.error("gmx_MMPBSA fallo")
            return False
        
        logger.info("MM-PBSA analisis completado")
        
        # Verificar resultados
        logger.info("\nVerificando resultados...")
        output_files = [
            'SUMMARY_REPORT.txt',
            'FINAL_RESULTS_MMPBSA.dat'
        ]
        
        files_found = 0
        for fname in output_files:
            fpath = os.path.join(output_dir, fname)
            if os.path.exists(fpath):
                logger.info(f"  {fname}")
                files_found += 1
            else:
                logger.warn(f"  {fname} no encontrado")
        
        logger.info(f"\nArchivos generados: {files_found}/{len(output_files)}")
        
        if files_found > 0:
            logger.info("Resultados verificados")
            
            # Mostrar resumen de energias
            log_section("RESUMEN DE RESULTADOS")
            
            try:
                results_file = os.path.join(output_dir, 'FINAL_RESULTS_MMPBSA.dat')
                with open(results_file, 'r') as f:
                    content = f.read()
                
                # Buscar energias de union
                if 'DELTA' in content or 'delta' in content.lower():
                    for line in content.split('\n'):
                        if any(keyword in line.upper() for keyword in ['DELTA', 'BINDING', 'ΔG']):
                            if any(char.isdigit() for char in line):
                                logger.info(f"  {line.strip()}")
            except Exception as e:
                logger.debug(f"No se pudo mostrar energias: {e}")
            
            return True
        else:
            logger.warn("No se encontraron archivos de salida")
            return False
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='MM-PBSA Analysis para Proteina-Proteina (PURA, sin cofactores)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EJEMPLO:
  python3 run_mmpbsa_for_pp_with_ligand.py -d /ruta/resultados

SALIDA ESPERADA:
  ΔG_binding = E(Proteina_A + Proteina_B) 
             - E(Proteina_A) 
             - E(Proteina_B)
  
  Si ΔG < 0: Las proteinas se unen favorablemente
  Si ΔG > 0: Las proteinas no se unen favorablemente

NOTA: Este script IGNORA cofactores/ligandos (HETATM).
      Solo analiza las 2 cadenas proteicas principales (ATOM).
        """
    )
    parser.add_argument(
        '-d', '--directory',
        required=True,
        help='Directorio con resultados MD'
    )
    
    args = parser.parse_args()
    
    results_dir = args.directory
    
    if not os.path.isdir(results_dir):
        logger.error(f"Directorio no encontrado: {results_dir}")
        sys.exit(1)
    
    logger.info("="*80)
    logger.info("  MM-PBSA ANALYSIS: PROTEINA-PROTEINA (PURA)")
    logger.info("="*80)
    logger.info(f"  Directorio: {results_dir}")
    logger.info(f"  Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Ejecutar analisis
    success = run_mmpbsa_analysis(results_dir)
    
    if success:
        logger.info("")
        logger.info("="*80)
        logger.info("  ANALISIS COMPLETADO EXITOSAMENTE")
        logger.info("="*80)
        logger.info(f"  Resultados en: {os.path.join(results_dir, 'analisis_binding_energy/gmx_MMPBSA')}")
        logger.info("="*80)
        sys.exit(0)
    else:
        logger.error("")
        logger.error("="*80)
        logger.error("  ANALISIS FALLO")
        logger.error("="*80)
        sys.exit(1)


if __name__ == '__main__':
    main()