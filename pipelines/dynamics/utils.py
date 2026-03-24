import os
import re

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