import os
from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline

def run_dynamics_menu():
    print("\n--- CONFIGURACIÓN DE DINÁMICA MOLECULAR ---")

    # 1. SELECCIÓN DE TIPO DE SIMULACIÓN
    print("\nTIPO DE SIMULACIÓN:")
    print("  1) Proteína sola")
    print("  2) Proteína con ligando pequeño (molécula orgánica) [Próximamente]")
    print("  3) Proteína con péptido [Próximamente]")
    print("  4) Proteína con ácido nucleico (DNA/RNA) [Próximamente]")
    print("  5) Proteína con otra proteína (complejo) [Próximamente]")
    print("  6) Proteína + proteína + cofactor/molécula pequeña")
    print("  7) salir")

    sim_type = input("\n➤ Ingrese una opción (1-7): ")
    if sim_type == "7":
        return
    elif sim_type != "1":
        return
    
    # 2. PEDIR TIEMPO DE SIMULACIÓN
    while True:
        try:
            ns_time = float(input("➤ Ingrese el tiempo de simulación en nanosegundos (ns): "))
            if ns_time > 0: break
            print("(!) El tiempo debe ser mayor a 0.")
        except ValueError:
            print("(!) Por favor, ingrese un número válido.")

    # 3. PEDIR PDB DE ENTRADA
    pdb_file = input("➤ Nombre del PDB (sin extensión): ")
    pdb_path = f"data/input/dynamics/{pdb_file}.pdb"
    if not os.path.exists(pdb_path):
        print(f"(!) Error: No se encuentra {pdb_path}")
        return #sale del menú si el archivo no existe

    num_threads = 8 

    # 4. CONFIGURAR EL PIPELINE
    config = {
        "sim_type": sim_type,
        "ns_time": ns_time,
        "threads": num_threads,
        "pdb_input": pdb_path,
        "work_dir": "data/output/dynamics"
    }

    # 5. EJECUTAR PIPELINE
    print(f"\n[ChemLink] Iniciando pipeline para {ns_time} ns...")
    pipeline = DynamicsPipeline(config)
    pipeline.execute()

if __name__ == "__main__":
    run_dynamics_menu()