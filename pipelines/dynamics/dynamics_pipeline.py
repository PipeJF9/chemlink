import os
from .utils import calculate_nsteps, update_md_nsteps, check_gmx_installation
from .steps import TopologyStep, SolvationStep

class DynamicsPipeline:
    def __init__(self, config):
        """
        config: Diccionario enviado por el CLI con:
                - ns_time (float)
                - pdb_input (str)
                - work_dir (str)
                - threads (int)
        """
        self.config = config
        # Ruta del md.mdp (conf de producción)
        self.md_mdp_path = "data/input/dynamics/md.mdp"
        self.gmx_bin = check_gmx_installation()

    def _prepare_time(self):
        print(f"\n[ChemLink] Configurando simulación para {self.config['ns_time']} ns...")
        
        steps = calculate_nsteps(self.config['ns_time'])
        update_md_nsteps(self.md_mdp_path, steps)
        
        return steps

    def execute(self):
        print("\n" + "="*50)
        print("   INICIANDO ORQUESTADOR DE DINÁMICA: CHEMLINK   ")
        print("="*50)

        self._prepare_time()

        try:
            # 1. Ejecutar Paso 1: Topología
            print("\n[Paso 1/5] Generando Topología...")
            topo = TopologyStep(self.config, self.gmx_bin)
            topo.run()

            # 2. Ejecutar Paso 2: Solvatación
            print("\n[Paso 2/5] Solvatando sistema...")
            solv = SolvationStep(self.config, self.gmx_bin)
            solv.run()

            # x. Ejecutar siguientes pasos: EnergyMin, Equilibration, Production (próximamente)

            print("\n[✓] ¡Proceso de Dinámica finalizado con éxito!")
        except Exception as e:
            print(f"\n[X] ERROR CRÍTICO EN EL PIPELINE: {e}")
            raise e