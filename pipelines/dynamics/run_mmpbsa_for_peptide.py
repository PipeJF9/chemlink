#!/usr/bin/env python3
"""
Wrapper para ejecutar gmx_MMPBSA cuando la simulación es
de tipo "Proteína-Proteína".

Comportamiento:
- Detecta el tipo de simulación leyendo `RESUMEN_SIMULACION.txt`.
- Si detecta o infiere un sistema proteína-proteína, extrae las dos
    cadenas principales y crea un `index.ndx` con grupos `Protein` y `Other`.
- Llama a `mmpbsa_analysis.GMX_MMPBSA_Analyzer` para ejecutar gmx_MMPBSA.
"""

import argparse
import subprocess
from pathlib import Path
import sys
import shutil
import importlib.util


def read_sim_type(results_dir: Path) -> str:
    summary = results_dir / 'RESUMEN_SIMULACION.txt'
    if not summary.exists():
        return ''
    txt = summary.read_text(encoding='utf-8', errors='ignore')
    for line in txt.splitlines():
        if 'Sistema:' in line or 'Sistema' in line and ':' in line:
            # Extraer parte tras ':'
            parts = line.split(':', 1)
            if len(parts) > 1:
                return parts[1].strip()
    return ''


def find_smallest_chain(pdb_file: Path) -> str:
    # legacy: not used
    return ''


def find_two_largest_chains(pdb_file: Path):
    """Devuelve las dos cadenas con más residuos como (chainA, chainB)"""
    chains = {}
    with open(pdb_file, 'r') as f:
        for l in f:
            if l.startswith(('ATOM', 'HETATM')) and len(l) >= 22:
                chain = l[21].strip()
                resseq = l[22:26].strip()
                if not chain:
                    continue
                chains.setdefault(chain, set()).add(resseq)

    if not chains:
        return None, None

    sorted_chains = sorted(chains.items(), key=lambda kv: len(kv[1]), reverse=True)
    if len(sorted_chains) == 1:
        return sorted_chains[0][0], None
    return sorted_chains[0][0], sorted_chains[1][0]


def index_ndx_valid(index_path: Path) -> bool:
    if not index_path.exists():
        return False
    try:
        with open(index_path, 'r') as f:
            content = f.read()
        groups = [g for g in content.split('[') if ']' in g]
        valid_groups = 0
        for g in groups:
            lines = g.split(']')[-1].strip().splitlines()
            nums = [int(x) for l in lines for x in l.split() if x.isdigit()]
            if len(nums) > 0:
                valid_groups += 1
        return valid_groups >= 2
    except Exception:
        return False


def get_atom_indices_for_chain(pdb_file: Path):
    """Devuelve dict chain -> list of atom serial indices (1-based)"""
    chains = {}
    with open(pdb_file, 'r') as f:
        for l in f:
            if l.startswith(('ATOM', 'HETATM')) and len(l) >= 11:
                try:
                    idx = int(l[6:11].strip())
                except Exception:
                    continue
                chain = l[21]
                chains.setdefault(chain, []).append(idx)
    return chains


def write_index_ndx(results_dir: Path, group1_chain: str, group2_chain: str, chains_dict: dict) -> bool:
    """Escribe un index.ndx simple con dos grupos: [ Protein ] y [ Other ]"""
    idx_file = results_dir / 'index.ndx'
    try:
        with open(idx_file, 'w') as f:
            f.write('[ Protein ]\n')
            arr = chains_dict.get(group1_chain, [])
            for i in range(0, len(arr), 15):
                f.write(' '.join(str(x) for x in arr[i:i+15]) + '\n')
            f.write('\n')
            f.write('[ Other ]\n')
            arr2 = chains_dict.get(group2_chain, [])
            for i in range(0, len(arr2), 15):
                f.write(' '.join(str(x) for x in arr2[i:i+15]) + '\n')
            f.write('\n')
        return True
    except Exception as e:
        print(f"⚠️  Error escribiendo index.ndx: {e}")
        return False


def extract_chain_pdb(pdb_in: Path, pdb_out: Path, chain_id: str) -> bool:
    try:
        with open(pdb_in, 'r') as inp, open(pdb_out, 'w') as out:
            for l in inp:
                if l.startswith(('ATOM', 'HETATM')) and len(l) >= 22:
                    if l[21] == chain_id:
                        out.write(l)
                elif l.startswith('TER'):
                    out.write(l)
            out.write('END\n')
        return True
    except Exception as e:
        print(f"⚠️  Error extrayendo cadena: {e}")
        return False


def run_acpype(peptide_pdb: Path, work_dir: Path, charge: int = 0) -> bool:
    # Mantener función por compatibilidad, pero para proteína-proteína
    # generalmente no es necesaria
    if shutil.which('acpype') is None:
        return False
    work_dir.mkdir(parents=True, exist_ok=True)
    local_pdb = work_dir / peptide_pdb.name
    shutil.copy2(peptide_pdb, local_pdb)
    cmd = ['acpype', '-i', str(local_pdb), '-b', 'LIG', '-c', 'user', '-n', str(charge), '-a', 'gaff2']
    p = subprocess.run(cmd, cwd=str(work_dir))
    return p.returncode == 0


def ensure_index_with_chains(results_dir: Path, chainA: str, chainB: str) -> bool:
    """
    Asegura que el archivo index.ndx contiene grupos [ Protein ] y [ Other ]
    compatibles con gmx_MMPBSA. Crea el archivo manualmente desde el PDB
    para garantizar exactamente 2 grupos en posiciones correctas.
    
    IMPORTANTE: gmx_MMPBSA no acepta agua e iones en las estructuras,
    y espera exactamente dos grupos en posiciones [0] y [1].
    """
    gmx = shutil.which('gmx') or shutil.which('gmx_d') or shutil.which('gmx_mpi')
    if gmx is None:
        gmx = '/home/ChemFusion/funciones/Aplicaciones/gromacs/bin/gmx'
        if not Path(gmx).exists():
            gmx = '/usr/local/gromacs/bin/gmx'

    pdb_file = results_dir / 'md_1.pdb'
    if not pdb_file.exists():
        print('❌ md_1.pdb no encontrado en', results_dir)
        return False
    
    tpr = results_dir / 'md_1.tpr'
    if not tpr.exists():
        print('❌ md_1.tpr no encontrado en', results_dir)
        return False
    
    idx_path = results_dir / 'index.ndx'
    
    # Verificar si el index.ndx existente es válido y tiene los grupos necesarios
    if idx_path.exists():
        try:
            with open(idx_path, 'r') as f:
                content = f.read()
            has_protein = '[ Protein ]' in content
            has_other = '[ Other ]' in content
            
            if has_protein and has_other:
                # Verificar que solo hay 2 grupos
                num_groups = content.count('[')
                if num_groups == 2:
                    print('ℹ️  index.ndx existente válido detectado con exactamente 2 grupos [ Protein ] y [ Other ]')
                    return True
        except Exception:
            pass
    
    # Si llegamos aquí, necesitamos crear el índice desde scratch
    print('🔧 Creando index.ndx manualmente desde estructuras PDB...')
    
    # Extraer átomos de cada cadena
    chains_atoms = get_atom_indices_for_chain(pdb_file)
    
    if chainA not in chains_atoms or chainB not in chains_atoms:
        print(f'⚠️  Una o ambas cadenas no encontradas en PDB')
        print(f'   Cadenas en PDB: {list(chains_atoms.keys())}')
        print(f'   Se esperaba: A={chainA}, B={chainB}')
        return False
    
    protein_atoms = chains_atoms[chainA]
    other_atoms = chains_atoms[chainB]
    
    print(f'   Cadena {chainA}: {len(protein_atoms)} átomos')
    print(f'   Cadena {chainB}: {len(other_atoms)} átomos')
    
    # Crear archivo index.ndx manualmente (GARANTIZA exactamente 2 grupos)
    try:
        with open(idx_path, 'w') as f:
            f.write('[ Protein ]\n')
            for i in range(0, len(protein_atoms), 15):
                line = ' '.join(str(x) for x in protein_atoms[i:i+15])
                f.write(line + '\n')
            
            f.write('\n[ Other ]\n')
            for i in range(0, len(other_atoms), 15):
                line = ' '.join(str(x) for x in other_atoms[i:i+15])
                f.write(line + '\n')
        
        print(f'✅ index.ndx creado manualmente con exactamente 2 grupos:')
        print(f'   [0] Protein: {len(protein_atoms)} átomos')
        print(f'   [1] Other: {len(other_atoms)} átomos')
        
        # Verificar que se creó correctamente
        with open(idx_path, 'r') as f:
            content = f.read()
        if '[ Protein ]' in content and '[ Other ]' in content:
            num_groups = content.count('[')
            print(f'✅ Verificación: Exactamente {num_groups} grupos en el archivo')
            return True
        else:
            print('❌ Verificación falló: grupos no encontrados en archivo creado')
            return False
            
    except Exception as e:
        print(f'❌ Error escribiendo index.ndx manualmente: {e}')
        return False


def call_mmpbsa_module(results_dir: Path, use_pb: bool = True, use_mpi: bool = True, cores: int = 6) -> int:
    """
    Llama al módulo mmpbsa_analysis para proteína-proteína.
    
    Para proteína-proteína PURA (sin ligando pequeño), gmx_MMPBSA debe:
    - Tratar ambas proteínas como complejos (sin archivo MOL2)
    - Usar topología basada en GROMACS
    - NO buscar archivos ACPYPE/MOL2/FRCMOD
    
    Returns:
        0 si éxito, código de error si falla
    """
    mmpbsa_script = Path(__file__).parent / 'mmpbsa_analysis.py'
    if not mmpbsa_script.exists():
        print('❌ mmpbsa_analysis.py no encontrado en', mmpbsa_script)
        return 2

    spec = importlib.util.spec_from_file_location('mmpbsa_analysis', str(mmpbsa_script))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Para proteína-proteína, usar modo serial por defecto
    # (MPI puede causar problemas con sistemas grandes)
    analyzer = module.GMX_MMPBSA_Analyzer(str(results_dir), use_mpi=False, n_cores=1)
    success = analyzer.run_analysis(use_pb=use_pb)
    return 0 if success else 3


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Ejecuta gmx_MMPBSA para simulaciones proteína-proteína')
    parser.add_argument('-d', '--directory', required=True, help='Directorio de resultados MD')
    parser.add_argument('--charge', type=int, default=0, help='Carga neta (si aplica)')
    args = parser.parse_args()

    results_dir = Path(args.directory)
    if not results_dir.exists():
        print(f'❌ Directorio no existe: {results_dir}')
        sys.exit(1)

    # Detectar tipo de simulación
    sim_type = read_sim_type(results_dir)
    print(f'🔎 Tipo de simulación detectado: "{sim_type}"')
    
    # Verificar archivos necesarios
    pdb_file = results_dir / 'md_1.pdb'
    if not pdb_file.exists():
        print('❌ md_1.pdb no encontrado en', results_dir)
        sys.exit(1)
    
    tpr_file = results_dir / 'md_1.tpr'
    if not tpr_file.exists():
        print('❌ md_1.tpr no encontrado en', results_dir)
        sys.exit(1)

    # Detectar cadenas
    chainA, chainB = find_two_largest_chains(pdb_file)
    if not chainA or not chainB:
        print('⚠️  No se detectaron dos cadenas grandes - intentando con todas las cadenas...')
        # Fallback: usar las dos primeras cadenas
        chains_file = {}
        with open(pdb_file, 'r') as f:
            for line in f:
                if line.startswith(('ATOM', 'HETATM')) and len(line) >= 22:
                    chain = line[21]
                    chains_file.setdefault(chain, 0)
                    chains_file[chain] += 1
        
        sorted_chains = sorted(chains_file.items(), key=lambda x: x[1], reverse=True)
        if len(sorted_chains) >= 2:
            chainA, _ = sorted_chains[0]
            chainB, _ = sorted_chains[1]
            print(f'✅ Cadenas detectadas: A={chainA}, B={chainB}')
        else:
            print('❌ No se encontraron suficientes cadenas en la estructura')
            sys.exit(1)
    else:
        print(f'✅ Cadenas detectadas: A={chainA}, B={chainB}')

    # Crear o validar index.ndx
    print('🔧 Preparando archivo de índice...')
    if not ensure_index_with_chains(results_dir, chainA, chainB):
        print('❌ No se pudo crear/validar index.ndx')
        sys.exit(1)

    # Ejecutar análisis MM-PBSA
    print('🔧 Ejecutando análisis MM-PBSA/MM-GBSA (gmx_MMPBSA)')
    print('   Esto puede tomar varios minutos...')
    rc = call_mmpbsa_module(results_dir, use_pb=True, use_mpi=True, cores=6)
    
    if rc == 0:
        print('✅ Análisis MM-PBSA completado exitosamente')
    else:
        print(f'⚠️  Análisis MM-PBSA finalizó con código: {rc}')
    
    sys.exit(rc)
