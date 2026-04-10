import subprocess
import os

class ProductionStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        
        # Entradas (vienen del paso de NPT)
        self.input_gro = os.path.join(self.config["work_dir"], "npt.gro")
        self.input_cpt = os.path.join(self.config["work_dir"], "npt.cpt")
        self.topol = os.path.join(self.config["work_dir"], "topol.top")
        
        # Salidas
        self.work_mdp = os.path.join(self.config["work_dir"], "md.mdp")
        self.md_tpr = os.path.join(self.config["work_dir"], "md_1.tpr")
        self.output_base = "md_1"

    def _create_production_mdp(self):
        """Genera el archivo md.mdp dinámicamente con los parámetros del script original."""
        ns_time = float(self.config["ns_time"])
        # nsteps = (ns * 1000) / 0.002
        nsteps = int((ns_time * 1000) / 0.002)
        
        mdp_content = f"""; md.mdp - Producción MD generada por ChemLink
integrator          = md
nsteps              = {nsteps}
dt                  = 0.002
nstxout             = 0
nstvout             = 0
nstfout             = 0
nstenergy           = 5000
nstlog              = 5000
nstxout-compressed  = 5000
compressed-x-grps   = System
continuation        = yes
constraint_algorithm = lincs
constraints         = h-bonds
cutoff-scheme       = Verlet
ns_type             = grid
nstlist             = 10
rcoulomb            = 1.0
rvdw                = 1.0
coulombtype         = PME
pme_order           = 4
fourierspacing      = 0.16
tcoupl              = V-rescale
tc-grps             = System
tau_t               = 0.1
ref_t               = 300
pcoupl              = Parrinello-Rahman
pcoupltype          = isotropic
tau_p               = 2.0
ref_p               = 1.0
compressibility     = 4.5e-5
pbc                 = xyz
gen_vel             = no
"""
        with open(self.work_mdp, "w") as f:
            f.write(mdp_content.strip())

    def run(self):
        print("\n[*] Paso 6: Dinámica de Producción (Simulación Real)...")

        # 1. Crear el archivo de parámetros al vuelo
        print(f"   -> Configurando parámetros para {self.config['ns_time']} ns...")
        self._create_production_mdp()

        # 2. Generar el TPR
        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.work_mdp,
            "-c", self.input_gro,
            "-t", self.input_cpt,
            "-p", self.topol,
            "-o", self.md_tpr
        ]

        # 3. Ejecutar mdrun
        mdrun_cmd = [
            self.gmx_bin, "mdrun",
            "-deffnm", self.output_base,
            "-nt", str(self.config.get("threads", 8))
        ]

        try:
            print("   -> Preparando binario de simulación...")
            subprocess.run(grompp_cmd, check=True, capture_output=True, text=True)

            print(f"   -> Ejecutando dinámica... (Esto puede tardar)")
            subprocess.run(mdrun_cmd, check=True, cwd=self.config["work_dir"])
            print("[✓] Simulación de producción finalizada con éxito.")
            
        except subprocess.CalledProcessError as e:
            print(f"[X] Error en la producción:\n{e.stderr}")
            raise e