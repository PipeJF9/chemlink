from pathlib import Path
import subprocess
import os
import datetime

from pipelines.dynamics.md_analysis import GromacsAnalyzer

class AnalysisStep:
    def __init__(self, config, gmx_bin):
        self.config = config
        self.gmx_bin = gmx_bin
        self.results_dir = config["work_dir"]

        # Rutas de scripts de análisis
        self.base_path = "pipeline/dynamics"
        self.mmpbsa_pp_ligand = os.path.join(self.base_path, "run_mmpbsa_for_pp_with_ligand.py")
        self.mmpbsa_peptide = os.path.join(self.base_path, "run_mmpbsa_for_peptide.py")
        self.mmpbsa_ligand = os.path.join(self.base_path, "mmpbsa_analysis.py")

    def run(self):
        print("\n" + "="*65)
        print("      EJECUTANDO ANÁLISIS COMPLETO AUTOMATIZADO")
        print("="*65)

        # 1. ANÁLISIS ESTRUCTURAL GENERAL
        # Este script genera RMSD, RMSF, Radios de Giro, SASA, etc.
        self._run_general_analysis()

        # 2. ANÁLISIS DE ENERGÍA DE BINDING (MM-PBSA)
        sim_type = self.config["sim_type"]
        if sim_type == "2":
            print("\n[*] Configuración: Proteína + Ligando")
            print("    -> Iniciando MM-PBSA para molécula pequeña...")
            #self._execute_mmpbsa(self.mmpbsa_ligand, "Proteína-Ligando")

        elif sim_type == "5" or sim_type == "3":
            print("\n[*] Configuración: Complejo de Proteína + (Proteína/Péptido)")
            print("    -> Iniciando MM-PBSA para interacción P-P...")
            #self._execute_mmpbsa(self.mmpbsa_peptide, "Proteína-Proteína")

        elif sim_type == "6":
            print("\n[*] Configuración: Proteína + Proteína + Cofactor")
            print("    -> Iniciando MM-PBSA P-P con ligando explícito...")
            #self._execute_mmpbsa(self.mmpbsa_pp_ligand, "P-P + Cofactor")
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
                sim_type=str(self.config.get("sim_type", "1")), 
                gmx_bin=self.gmx_bin
            )

            for key in analyzer.analysis_dirs:
                os.makedirs(analyzer.analysis_dirs[key], exist_ok=True)

            # Ejecutamos el análisis
            analyzer.run_pipeline_analysis(plot_only=self.config.get("plot_only", False))
        
        except Exception as e:
            print(f"[X] Error en el análisis: {e}")

    def _execute_mmpbsa(self, script_path, label):
        # Helper para ejecutar los wrappers de MM-PBSA
        if os.path.exists(script_path):
            print(f"    -> Ejecutando análisis MM-PBSA ({label})...")
            cmd = ["python3", script_path, "-d", self.results_dir ]
            try:
                subprocess.run(cmd, check=True)
                print(f"    [✓] MM-PBSA {label} completado.")
                self._verify_mmpbsa_results()
            except subprocess.CalledProcessError:
                print(f"    [X] Error: Falló el cálculo de MM-PBSA para {label}.")
        else:
            print(f"    [!] Error: No se encontró el wrapper {script_path}")

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