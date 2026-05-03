import os

from pipelines.dynamics.steps.ligand_topology import LigandTopologyStep
from .utils import check_gmx_installation
from .steps import TopologyStep, SolvationStep, IonsStep, EnergyMinStep, EquilibrationStep, ProductionStep, PostProcessingStep, AnalysisStep

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
        self.gmx_bin = check_gmx_installation()

    def execute(self):
        print("\n" + "="*50)
        print("   INICIANDO ORQUESTADOR DE DINÁMICA: CHEMLINK   ")
        print("="*50)

        try:
            '''
            # 1. Ejecutar Paso 1: Topología
            print("\n[Paso 1/6] Generando Topología...")
            topo = TopologyStep(self.config, self.gmx_bin)
            topo.run()

            # Lógica de ligando pequeño Opción 2
            if self.config["sim_type"] == "2":
                ligand_step = LigandTopologyStep(self.config, self.gmx_bin)
                ligand_step.run()
                
                self.config["current_gro"] = "complex.gro"
            else:
                self.config["current_gro"] = "processed.gro"
            # ---------------------------------

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

            # 6. Ejecutar Paso 6: Producción
            print("\n[Paso 6/6] Ejecutando simulación de producción...")
            prod = ProductionStep(self.config, self.gmx_bin)
            prod.run()

            # 7. Ejecutar Paso 7: Post-procesamiento
            print("\n[Paso 7/7] Post-procesando resultados...")
            post_proc = PostProcessingStep(self.config, self.gmx_bin)
            post_proc.run()
'''
            # 8. Ejecutar Paso 8: Análisis
            print("\n[Paso 8/8] Analizando resultados...")
            analysis = AnalysisStep(self.config, self.gmx_bin)
            analysis.run()

            print("\n[✓] ¡Proceso de Dinámica finalizado con éxito!")
        except Exception as e:
            print(f"\n[X] ERROR CRÍTICO EN EL PIPELINE: {e}")
            raise e