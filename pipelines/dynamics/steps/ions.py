import subprocess
import os

class IonsStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entrada: El archivo solvatado del paso anterior
        self.solvated_gro = os.path.join(self.config["work_dir"], "solvated.gro")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        # Salidas y Temporales
        self.ions_mdp = os.path.join(self.config["work_dir"], "ions.mdp")
        self.ions_tpr = os.path.join(self.config["work_dir"], "ions.tpr")
        self.ionized_gro = os.path.join(self.config["work_dir"], "ionized.gro")

    def _create_ions_mdp(self): # Crea el archivo mdp mínimo para que genion funcione
        mdp_content = (
            "integrator  = steep\n"
            "emtol       = 1000.0\n"
            "emstep      = 0.01\n"
            "nsteps      = 50000\n"
            "nstlist     = 1\n"
            "cutoff-scheme = Verlet\n"
            "ns_type     = grid\n"
            "coulombtype = cutoff\n"
            "rcoulomb    = 1.0\n"
            "rvdw        = 1.0\n"
            "pbc         = xyz\n"
        )
        with open(self.ions_mdp, "w") as f:
            f.write(mdp_content)
        print("   -> Archivo ions.mdp creado.")

    def run(self):
        print("\n[*] Paso 3: Neutralización (Añadiendo Iones)...")
        
        # 1. Crear MDP
        self._create_ions_mdp()

        # 2. Generar TPR con grompp
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.ions_mdp,
            "-c", self.solvated_gro,
            "-p", self.topol,
            "-o", self.ions_tpr,
            "-maxwarn", "10"
        ]

        # 3. Añadir Iones con genion
        # Enviamos "13" que es el grupo SOL (agua) en Amber para ser reemplazado por iones PREGUNTAR
        genion_cmd = [
            self.gmx_bin, "genion",
            "-s", self.ions_tpr,
            "-o", self.ionized_gro,
            "-p", self.topol,
            "-pname", "NA",
            "-nname", "CL",
            "-neutral"
        ]

        try:
            print("   -> Preparando sistema para iones...")
            subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)

            print("   -> Neutralizando carga (reemplazando agua por NA/CL)...")
            process = subprocess.Popen(genion_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # "13" selecciona el grupo SOL para reemplazar
            stdout, stderr = process.communicate(input="13\n")
            
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, genion_cmd, stderr)

            print(f"[✓] Sistema neutralizado: {os.path.basename(self.ionized_gro)}")
            print(f"[✓] Topología actualizada con iones en {os.path.basename(self.topol)}")
            
        except subprocess.CalledProcessError as e:
            print(f"[X] Error en neutralización:\n{e.stderr}")
            raise e