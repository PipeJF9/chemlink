import os
from .utils import calculate_nsteps, update_md_nsteps, check_gmx_installation
from .steps import TopologyStep, SolvationStep, IonsStep, EnergyMinStep, EquilibrationStep

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
            print("\n[Paso 1/6] Generando Topología...")
            topo = TopologyStep(self.config, self.gmx_bin)
            topo.run()

            # 2. Ejecutar Paso 2: Solvatación
            print("\n[Paso 2/6] Solvatando sistema...")
            solv = SolvationStep(self.config, self.gmx_bin)
            solv.run()

            # 3. Ejecutar Paso 3: Iones
            print("\n[Paso 3/6] Añadiendo iones para neutralizar carga...")
            ions = IonsStep(self.config, self.gmx_bin)
            ions.run()

            # 4. Ejecutar Paso 4: Minimización de Energía
            print("\n[Paso 4/6] Minimizando energía...")
            em = EnergyMinStep(self.config, self.gmx_bin)
            em.run()

            # 5. Ejecutar Paso 5: Equilibración
            print("\n[Paso 5/6] Equilibrando sistema...")
            equil = EquilibrationStep(self.config, self.gmx_bin)
            equil.run()

            # x. Ejecutar siguientes pasos: Production (próximamente)

            print("\n[✓] ¡Proceso de Dinámica finalizado con éxito!")
        except Exception as e:
            print(f"\n[X] ERROR CRÍTICO EN EL PIPELINE: {e}")
            raise e