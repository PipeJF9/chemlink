import os

from pipelines.dynamics.steps.ligand_topology import LigandTopologyStep
from .utils import check_gmx_installation
from tqdm import tqdm
from .steps import ComplexBuilderStep,TopologyStep, SolvationStep, IonsStep, EnergyMinStep, EquilibrationStep, ProductionStep, PostProcessingStep, AnalysisStep

class DynamicsPipeline:
    def __init__(self, config):
        """
        # Prioridad 1: Slurm | Prioridad 2: Config CLI | Prioridad 3: Hardware local
        assigned_cpus = os.environ.get("SLURM_CPUS_ON_NODE")
        total_threads = int(assigned_cpus) if assigned_cpus else self.config.get("threads", os.cpu_count())

        config: Diccionario enviado por el CLI con:
                - ns_time (float)
                - pdb_input (str)
                - work_dir (str)
                - threads (int)
        """
        self.config = config
        self.gmx_bin = check_gmx_installation()
        self.total_steps = 10

    def execute(self):
        print(f" CHEMLINK DYNAMICS ORCHESTRATOR: {self.config['sim_type_label'].upper()}")
        print("="*50)

        pipeline_bar = tqdm(total=self.total_steps, desc="Overall Progress", unit="step")
        try:
            #'''
            # 0. COMPLEX BUILDING
            if self.config["sim_type"] in ["3", "4", "5", "6"]:
                comp = ComplexBuilderStep(self.config)
                comp.run()
            pipeline_bar.update(1)

            # 1. TOPOLOGY
            topo = TopologyStep(self.config, self.gmx_bin)
            topo.run()
            pipeline_bar.update(1)

            # 1.5 LIGAND TOPOLOGY
            if self.config["sim_type"] in ["2", "6"]:
                ligand_step = LigandTopologyStep(self.config, self.gmx_bin)
                ligand_step.run()
                self.config["current_gro"] = "complex.gro"
            else:
                self.config["current_gro"] = "processed.gro"
            pipeline_bar.update(1)
            # 2. SOLVATION
            solv = SolvationStep(self.config, self.gmx_bin)
            solv.run()
            pipeline_bar.update(1)

            # 3. IONS
            ions = IonsStep(self.config, self.gmx_bin)
            ions.run()
            pipeline_bar.update(1)

            # 4. ENERGY MINIMIZATION
            em = EnergyMinStep(self.config, self.gmx_bin)
            em.run()
            pipeline_bar.update(1)

            # 5. EQUILIBRATION
            equil = EquilibrationStep(self.config, self.gmx_bin)
            equil.run()
            pipeline_bar.update(1)

            # 6. PRODUCTION
            prod = ProductionStep(self.config, self.gmx_bin)
            prod.run()
            pipeline_bar.update(1)

            # 7. POST-PROCESSING
            post_proc = PostProcessingStep(self.config, self.gmx_bin)
            post_proc.run()
            pipeline_bar.update(1)
            #'''
            # 8. ANALYSIS
            analysis = AnalysisStep(self.config, self.gmx_bin)
            analysis.run()
            pipeline_bar.update(1)

        except Exception as e:
            print(f"\n[X] CRITICAL ERROR : {e}")
            raise e