import os

from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline

def run_dynamics_menu():
    print("\n--- CONFIGURACIÓN DE DINÁMICA MOLECULAR ---")

    # 1. SELECCIÓN DE TIPO DE SIMULACIÓN
    print("\nTIPO DE SIMULACIÓN:")
    print("  1) Proteína sola")
    print("  2) Proteína con ligando pequeño (molécula orgánica)")
    print("  3) Proteína con péptido [Próximamente]")
    print("  4) Proteína con ácido nucleico (DNA/RNA) [Próximamente]")
    print("  5) Proteína con otra proteína (complejo) [Próximamente]")
    print("  6) Proteína + proteína + cofactor/molécula pequeña")
    print("  7) salir")

    sim_type = input("\n➤ Ingrese una opción (1-7): ")
    if sim_type == "7":
        return
    elif sim_type != "1" and sim_type != "2" and sim_type != "5":
        return
    
    # 2. PEDIR TIEMPO DE SIMULACIÓN
    while True:
        try:
            ns_time = float(input("➤ Ingrese el tiempo de simulación en nanosegundos (ns): "))
            if ns_time > 0: break
            print("(!) El tiempo debe ser mayor a 0.")
        except ValueError:
            print("(!) Por favor, ingrese un número válido.")

    num_threads = 10 

    # 3. CONFIGURAR EL PIPELINE
    config = {
        "sim_type": sim_type,
        "ns_time": ns_time,
        "threads": num_threads,
        "work_dir": "data/output/dynamics"
    }

    # 4. PEDIR ARCHIVOS DE ENTRADA
    if sim_type == "2":
        prot_file = input("➤ PDB de la PROTEÍNA (sin extensión): ")
        lig_file = input("➤ PDB del LIGANDO (sin extensión): ")
        config["pdb_input"] = f"data/input/dynamics/{prot_file}.pdb"
        config["ligand_pdb"] = f"data/input/dynamics/{lig_file}"
        config["ligand_charge"] = int(input("➤ Carga neta del ligando (ej: 0): "))
    elif sim_type == "5":
        pdb_complex = input("➤ Nombre del PDB del COMPLEJO (sin extension): ")
        config["pdb_input"] = f"data/input/dynamics/{pdb_complex}.pdb"
    else:
        pdb_file = input("➤ Nombre del PDB (sin extensión): ")
        config["pdb_input"] = f"data/input/dynamics/{pdb_file}.pdb"

    # 5. EJECUTAR PIPELINE
    print(f"\n[ChemLink] Iniciando pipeline para {ns_time} ns...")
    pipeline = DynamicsPipeline(config)
    pipeline.execute()

    print("\n[✓] Proceso completado con éxito.")
    input("\nPresione Enter para volver al menú principal...")

if __name__ == "__main__":
    run_dynamics_menu()