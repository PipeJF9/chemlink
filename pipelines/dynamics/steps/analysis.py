from pathlib import Path
import subprocess
import os
import datetime

from pipelines.dynamics.md_analysis import GromacsAnalyzer
from pipelines.dynamics.mmpbsa_analysis import GMX_MMPBSA_Analyzer
from pipelines.dynamics.run_mmpbsa_for_peptide import MMPBSAPeptideAnalyzer
from pipelines.dynamics.run_mmpbsa_for_pp_with_ligand import MMPBSAPPLigandAnalyzer

class AnalysisStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.results_dir = config["work_dir"]
        self.threads = config.get("threads", 8)

        # Rutas de scripts de análisis
        self.base_path = "pipeline/dynamics"
        self.mmpbsa_peptide = os.path.join(self.base_path, "run_mmpbsa_for_peptide.py")
        self.mmpbsa_pp_ligand = os.path.join(self.base_path, "run_mmpbsa_for_pp_with_ligand.py")
        
        #self.mmpbsa_ligand = os.path.join(self.base_path, "mmpbsa_analysis.py")

    def run(self):
        print("\n" + "="*65)
        print("      EJECUTANDO ANÁLISIS COMPLETO AUTOMATIZADO")
        print("="*65)

        # 1. ANÁLISIS ESTRUCTURAL GENERAL: RMSD, RMSF, Radios de Giro, SASA, etc.
        self._run_general_analysis()

        sim_type = self.config["sim_type"]
        if sim_type == "2":
            print("    -> Iniciando MM-PBSA para molécula pequeña...")
            analyzer = GMX_MMPBSA_Analyzer(str(self.results_dir), self.gmx_bin)
            self._execute_mmpbsa(analyzer, "Proteína-Ligando")

        elif sim_type == "5" or sim_type == "3":
            print("    -> Iniciando MM-PBSA para interacción...")
            analyzer = MMPBSAPeptideAnalyzer(results_dir=str(self.results_dir), gmx_bin=self.gmx_bin)

            if sim_type == "5":
                self._execute_mmpbsa(analyzer, "Proteína-Proteína")
            else:
                self._execute_mmpbsa(analyzer, "Proteína-Péptido")

        elif sim_type == "6":
            print("\n[*] Configuración: Proteína + Proteína + Cofactor (Opción 6)")
            # Instancia la nueva clase especializada para PP + Ligando
            analyzer = MMPBSAPPLigandAnalyzer(
                results_dir=str(self.results_dir), 
                gmx_bin=self.gmx_bin,
                n_cores=self.threads # Se pasan los cores para procesamiento paralelo no-MPI[cite: 20]
            )
            self._execute_mmpbsa(analyzer, "P-P + Cofactor")
        else:
            print(f"\n[*] Tipo de sistema {sim_type}: No requiere análisis de binding energy.")

        # 3. GENERACIÓN DEL REPORTE FINAL DE TEXTO
        self._generate_final_report()

        print("\n" + "="*65)
        print("             PROCESO DE ANÁLISIS FINALIZADO")
        print("="*65)
    
    def _run_general_analysis(self):
        try:
            # Instanciamos apuntando a work_dir
            analyzer = GromacsAnalyzer(
                results_dir=self.results_dir, 
                sim_type=str(self.config.get("sim_type")), 
                gmx_bin=self.gmx_bin
            )

            for key in analyzer.analysis_dirs:
                os.makedirs(analyzer.analysis_dirs[key], exist_ok=True)

            # Ejecutamos el análisis
            analyzer.run_pipeline_analysis(plot_only=self.config.get("plot_only", False))
        
        except Exception as e:
            print(f"[X] Error en el análisis: {e}")

    def _execute_mmpbsa(self, analyzer, label="no especificado"):
        required_files = ['md_center.xtc', 'md.tpr', 'index.ndx']
        missing_files = [f for f in required_files if not (Path(self.results_dir) / f).exists()]
        
        if missing_files:
            print(f"⚠️  Archivos requeridos faltantes en {self.results_dir.name}: {', '.join(missing_files)}")
            return
        
        try:
            print(f"\n📊 Ejecutando análisis para tipo: '{label}'...")
            
            success = analyzer.run_analysis(use_pb=True)
            
            if success:
                print("\n" + "="*80)
                print("✅ ANÁLISIS MM-PBSA/MM-GBSA COMPLETADO EXITOSAMENTE")
                print("="*80)
            else:
                print("\n⚠️  El análisis MM-PBSA/MM-GBSA encontró problemas")
        
        except Exception as e:
            print(f"\n❌ Error ejecutando análisis MM-PBSA/MM-GBSA: {e}")
            import traceback
            traceback.print_exc()

    def _verify_mmpbsa_results(self):
        # Verifica la existencia de los archivos de salida de MM-PBSA
        output_dir = os.path.join(self.results_dir, "analisis_binding_energy/gmx_MMPBSA")
        if os.path.exists(output_dir):
            files = ["SUMMARY_REPORT.txt", "FINAL_RESULTS_MMPBSA.dat", "binding_energy.png"]
            found = [f for f in files if os.path.exists(os.path.join(output_dir, f))]
            if found:
                print(f"    -> Resultados verificados: {len(found)} archivos generados.")

    def _generate_final_report(self):
        # Genera el archivo RESUMEN_SIMULACION.txt
        report_path = os.path.join(self.results_dir, "RESUMEN_SIMULACION.txt")
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        sim_label = self.config.get("sim_type_label", "Simulación MD")
        ns = self.config.get("ns_time", "0")
        
        report_content = f"""
═══════════════════════════════════════════════════════════
                    RESUMEN DE SIMULACIÓN MD
═══════════════════════════════════════════════════════════

CONFIGURACIÓN:
-------------
   Sistema:           {sim_label}
   Tiempo solicitado: {ns} ns
   Directorio:        {self.results_dir}
   Campo de fuerza:   AMBER03
   Modelo de agua:    TIP3P
   Temperatura:       300 K
   Presión:           1 bar
   Fecha:             {fecha}

ARCHIVOS PRINCIPALES:
--------------------
   Gráficas:          graficas/dashboard_resumen.png
   Análisis:          RESUMEN_ANALISIS.txt
   Trayectoria:       md_center.xtc
   Estructura final:  md.pdb
   Topología:         topol.top
   Índices:           index.ndx

PRÓXIMOS PASOS:
---------------
  1. Revisar dashboard de gráficas en la carpeta 'graficas/'
  2. Leer el reporte estadístico RESUMEN_ANALISIS.txt
  3. Verificar convergencia en graficas/rmsd_tiempo.png
  4. Visualizar trayectoria con: vmd md.pdb md_center.xtc

COMANDOS ÚTILES:
----------------
  # Visualizar en VMD
  vmd md.pdb md_center.xtc


═══════════════════════════════════════════════════════════
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\n[✓] Resumen guardado en: {report_path}")