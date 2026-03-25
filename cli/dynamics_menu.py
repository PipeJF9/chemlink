import os
from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline

def run_dynamics_menu():
    print("\n--- CONFIGURACIÓN DE DINÁMICA MOLECULAR ---")

    # 1. Pedir tiempo de simulación
    while True:
        try:
            ns_time = float(input("➤ Ingrese el tiempo de simulación en nanosegundos (ns): "))
            if ns_time > 0: break
            print("(!) El tiempo debe ser mayor a 0.")
        except ValueError:
            print("(!) Por favor, ingrese un número válido.")

    pdb_file = input("➤ Ingrese el nombre del archivo PDB (sin extensión): ")

    num_threads = 8 

    # 2. Configuracion que tomara el pipeline
    config = {
        "ns_time": ns_time,
        "threads": num_threads,
        "pdb_input": f"../data/input/dynamics/{pdb_file}.pdb",
        "work_dir": "../data/output/dynamics"
    }

    # 3. EJECUTAR PIPELINE
    print(f"\n[ChemLink] Iniciando pipeline para {ns_time} ns...")
    pipeline = DynamicsPipeline(config)
    pipeline.execute()

if __name__ == "__main__":
    run_dynamics_menu()