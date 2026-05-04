import os
import re
import shutil
import subprocess

def calculate_nsteps(ns_time, dt=0.002): # Convierte nanosegundos a pasos de GROMACS.
    # 1 ns = 1000 ps. nsteps = (ns * 1000) / dt
    ps_time = ns_time * 1000
    nsteps = int(ps_time / dt)
    return nsteps

def update_md_nsteps(mdp_path, nsteps): #Actualiza valor de nsteps para producción.

    if not os.path.exists(mdp_path): # revisa la existencia del archivo MDP
        print(f"[Error] No se encontró el archivo MDP en: {mdp_path}")
        return False

    with open(mdp_path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    found = False
    pattern = re.compile(r'^(\s*nsteps\s*=\s*)(\d+)(.*)$')

    for line in lines:
        if pattern.match(line):
            new_line = pattern.sub(rf'\1{nsteps}\3', line)
            new_lines.append(new_line)
            found = True
        else:
            new_lines.append(line)

    # Si por alguna razón no existe la línea nsteps, la añadimos al final
    if not found:
        new_lines.append(f"\n; Agregado por ChemLink\nnsteps = {nsteps}\n")

    with open(mdp_path, 'w') as f:
        f.writelines(new_lines)

    print(f"[✓] Archivo {os.path.basename(mdp_path)} actualizado a {nsteps} pasos.")
    return True

def check_gmx_installation(): # Verifica si gmx o gmx_mpi están disponibles en el sistema
    # Priorizamos gmx_mpi
    for binary in ["gmx_mpi", "gmx"]:
        if shutil.which(binary):
            print(f"[✓] GROMACS detectado: {binary}")
            return binary

    raise EnvironmentError(
        "(!) Error: No se encontró GROMACS (gmx o gmx_mpi) instalado en el PATH del sistema.\n"
        "Asegúrese de que GROMACS esté instalado y cargado correctamente."
    )

def convert_pdbqt_to_pdb(input_path, output_path):
    # -h: añade hidrógenos según pH 7.0
    # --error 0: silencia warnings no críticos
    obabel_cmd = ["obabel", input_path, "-O", output_path, "-h", "--error", "0"]
    
    try:
        result = subprocess.run(obabel_cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"(!) Error en OpenBabel: {e.stderr}")
        return False