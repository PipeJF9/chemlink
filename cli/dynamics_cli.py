import os
import sys
import argparse
from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline

def run_cli():
    # Creamos el parser principal
    parser = argparse.ArgumentParser(
        prog="chemlink", 
        description="ChemLink: Ejecución de pipelines de Dinámica Molecular por CLI"
    )
    
    # Subparser para el comando "dynamic" (permite escalar en el futuro, ej: "docking")
    subparsers = parser.add_subparsers(dest="command")
    dynamic_parser = subparsers.add_parser("dynamic", help="Ejecutar simulaciones de Dinámica Molecular")
    
    # Subparser para las opciones dentro de "dynamic" (oprotein, pligand, etc.)
    dyn_subparsers = dynamic_parser.add_subparsers(dest="dyn_type")

    # --- Argumento global -t para todas las simulaciones ---
    # nargs='?' permite que el flag pueda venir sin valor, const le da el valor si viene vacío, 
    # y default se usa si no se escribe la flag en absoluto.
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-t", "--time", type=float, nargs='?', const=0.1, default=0.1, 
                               help="Tiempo de simulación en ns (default: 0.1)")

    # 1: Proteína sola
    p_oprotein = dyn_subparsers.add_parser("oprotein", parents=[parent_parser])
    p_oprotein.add_argument("protein", help="Proteína (se asume .pdb automáticamente)")

    # 2: Proteína + Ligando
    p_pligand = dyn_subparsers.add_parser("pligand", parents=[parent_parser])
    p_pligand.add_argument("protein", help="Proteína (se asume .pdb)")
    p_pligand.add_argument("ligand", help="Ligando (DEBE incluir extensión .pdb o .pdbqt)")
    p_pligand.add_argument("-c", "--charge", type=int, required=True, help="Carga neta del ligando (Obligatoria)")

    # 3: Proteína + Péptido
    p_ppeptide = dyn_subparsers.add_parser("ppeptide", parents=[parent_parser])
    p_ppeptide.add_argument("protein", help="Proteína principal (se asume .pdb)")
    p_ppeptide.add_argument("peptide", help="Péptido (se asume .pdb)")

    # 4: Proteína + Ácido nucleico
    p_pacid = dyn_subparsers.add_parser("pacid", parents=[parent_parser])
    p_pacid.add_argument("protein", help="Proteína (se asume .pdb)")
    p_pacid.add_argument("acid", help="Ácido nucleico (se asume .pdb)")

    # 5: Proteína + Proteína
    p_pprotein = dyn_subparsers.add_parser("pprotein", parents=[parent_parser])
    p_pprotein.add_argument("protein1", help="Proteína 1 (se asume .pdb)")
    p_pprotein.add_argument("protein2", help="Proteína 2 (se asume .pdb)")

    # 6: Proteína + Proteína + Ligando/Cofactor
    p_ppligand = dyn_subparsers.add_parser("ppligand", parents=[parent_parser])
    p_ppligand.add_argument("protein1", help="Proteína 1 (se asume .pdb)")
    p_ppligand.add_argument("protein2", help="Proteína 2 (se asume .pdb)")
    p_ppligand.add_argument("ligand", help="Ligando/Cofactor (DEBE incluir extensión)")
    p_ppligand.add_argument("-c", "--charge", type=int, required=True, help="Carga neta del ligando (Obligatoria)")

    # Manejo de error si no se pasa nada
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    try:
        # Esto automáticamente lanza un error si hay banderas desconocidas, un orden incorrecto
        # o si falta alguna variable obligatoria como -c
        args = parser.parse_args()
    except SystemExit:
        print("\n(!) Error de comando: argumentos inválidos o flag obligatoria faltante.")
        sys.exit(1)

    if args.command != "dynamic":
        parser.print_help()
        sys.exit(1)

    if not args.dyn_type:
        dynamic_parser.print_help()
        sys.exit(1)

    # --- 3. CONFIGURAR EL PIPELINE ---
    config = {
        "ns_time": args.time,
        "threads": 10,
        "work_dir": "data/output/dynamics"
    }

    # Procesar opciones manteniendo la lógica de sim_type intacta
    if args.dyn_type == "oprotein":
        config["sim_type"] = "1"
        config["sim_type_label"] = "Proteína sola"
        config["pdb_input"] = f"data/input/dynamics/{args.protein}.pdb"

    elif args.dyn_type == "pligand":
        config["sim_type"] = "2"
        config["sim_type_label"] = "Proteína + Ligando pequeño"
        config["pdb_input"] = f"data/input/dynamics/{args.protein}.pdb"
        config["ligand_pdb"] = f"data/input/dynamics/{args.ligand}"
        config["ligand_charge"] = args.charge

    elif args.dyn_type == "ppeptide":
        config["sim_type"] = "3"
        config["sim_type_label"] = "Proteína + Péptido"
        config["pdb_protein"] = f"data/input/dynamics/{args.protein}.pdb"
        config["pdb_partner"] = f"data/input/dynamics/{args.peptide}.pdb"
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "pacid":
        config["sim_type"] = "4"
        config["sim_type_label"] = "Proteína + Ácido nucleico"
        config["pdb_protein"] = f"data/input/dynamics/{args.protein}.pdb"
        config["pdb_partner"] = f"data/input/dynamics/{args.acid}.pdb"
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "pprotein":
        config["sim_type"] = "5"
        config["sim_type_label"] = "Proteína + Proteína"
        config["pdb_protein"] = f"data/input/dynamics/{args.protein1}.pdb"
        config["pdb_partner"] = f"data/input/dynamics/{args.protein2}.pdb"
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "ppligand":
        config["sim_type"] = "6"
        config["sim_type_label"] = "Proteína + Proteína + Cofactor"
        config["pdb_protein"] = f"data/input/dynamics/{args.protein1}.pdb"
        config["pdb_partner"] = f"data/input/dynamics/{args.protein2}.pdb"
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")
        config["ligand_pdb"] = f"data/input/dynamics/{args.ligand}"
        config["ligand_charge"] = args.charge

    # --- 4. EJECUTAR PIPELINE ---
    print(f"\n[ChemLink] Iniciando pipeline para {config['ns_time']} ns... ({config['sim_type_label']})")
    
    pipeline = DynamicsPipeline(config)
    pipeline.execute()