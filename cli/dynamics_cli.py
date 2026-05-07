'''
Usage examples:
1: chemlink dynamic oprotein -i protein.pdb -t 0.1
   chemlink dynamic oprotein /path/to/protein.pdb -t 0.1

2: chemlink dynamic pligand -i protein.pdb -i ligand.pdbqt -c 0 -t 0.1
   chemlink dynamic pligand /path/to/protein.pdb /path/to/ligand.pdbqt -c 0 -t 0.1
   (flag -i searches in data/input/dynamics; without -i, file path is taken as absolute/relative)

3: chemlink dynamic ppeptide -i protein.pdb -i peptide.pdb -t 0.1

4: chemlink dynamic pacid -i protein.pdb -i acid.pdb -t 0.1

5: chemlink dynamic pprotein -i protein1.pdb -i protein2.pdb -t 0.1

6: chemlink dynamic ppligand -i protein1.pdb -i protein2.pdb -i ligand.pdbqt -c 0 -t 0.1

All files now require explicit extension (.pdb, .pdbqt, etc.). The -i flag is required
for each file that should be searched in data/input/dynamics.
'''

import os
import sys
import argparse
from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline
from pipelines.dynamics.utils import get_system_threads, setup_work_directory


def resolve_file_path(filename, use_input_dir=False):
    if use_input_dir:
        return os.path.join("data/input/dynamics", filename)
    return filename


def run_cli():
    # Create main parser
    parser = argparse.ArgumentParser(
        prog="chemlink", 
        description="ChemLink: Molecular Dynamics Pipeline Executor by CLI"
    )
    
    # Subparser for "dynamic" command
    subparsers = parser.add_subparsers(dest="command")
    dynamic_parser = subparsers.add_parser("dynamic", help="Run Molecular Dynamics simulations")
    
    # Subparser for workflow types within "dynamic"
    dyn_subparsers = dynamic_parser.add_subparsers(dest="dyn_type")

    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("-i", "--input-dir", action="append", dest="input_files", 
                               help="File in data/input/dynamics (can be used multiple times)")
    parent_parser.add_argument("files", nargs="*", 
                               help="Absolute or relative file paths (not in data/input/dynamics)")
    parent_parser.add_argument("-t", "--time", type=float, nargs='?', const=0.1, default=0.1, 
                               help="Simulation time in ns (default: 0.1)")

    # 1: Protein
    p_oprotein = dyn_subparsers.add_parser("oprotein", parents=[parent_parser])

    # 2: Protein + Ligand
    p_pligand = dyn_subparsers.add_parser("pligand", parents=[parent_parser])
    p_pligand.add_argument("-c", "--charge", type=int, required=True, help="Ligand net charge (required)")

    # 3: Protein + Peptide
    p_ppeptide = dyn_subparsers.add_parser("ppeptide", parents=[parent_parser])

    # 4: Protein + Nucleic Acid
    p_pacid = dyn_subparsers.add_parser("pacid", parents=[parent_parser])

    # 5: Protein + Protein
    p_pprotein = dyn_subparsers.add_parser("pprotein", parents=[parent_parser])

    # 6: Protein + Protein + Ligand/Cofactor
    p_ppligand = dyn_subparsers.add_parser("ppligand", parents=[parent_parser])
    p_ppligand.add_argument("-c", "--charge", type=int, required=True, help="Ligand net charge (required)")


    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    try:
        args = parser.parse_args()
    except SystemExit:
        print("\n(!) Command error: invalid arguments or missing required flag.")
        sys.exit(1)

    if args.command != "dynamic":
        parser.print_help()
        sys.exit(1)

    if not args.dyn_type:
        dynamic_parser.print_help()
        sys.exit(1)

    # --- PIPELINE CONFIGURATION ---
    base_out = "data/output/dynamics"
    work_dir = setup_work_directory(base_out, args.dyn_type)
    threads = get_system_threads()
    config = {
        "ns_time": args.time,
        "threads": threads,
        "work_dir": work_dir
    }

    # Combine input_files (from -i flags) and files (positional arguments)
    input_dir_files = args.input_files if args.input_files else []
    absolute_files = args.files if hasattr(args, 'files') and args.files else []
    
    # Helper to resolve files and create a list in order of expected arguments
    all_files = []
    for f in input_dir_files:
        all_files.append(resolve_file_path(f, use_input_dir=True))
    for f in absolute_files:
        all_files.append(f)

    if args.dyn_type == "oprotein":
        if len(all_files) < 1:
            print("(!) Error: oprotein requires 1 file (protein).")
            sys.exit(1)
        config["sim_type"] = "1"
        config["sim_type_label"] = "Protein"
        config["pdb_input"] = all_files[0]

    elif args.dyn_type == "pligand":
        if len(all_files) < 2:
            print("(!) Error: pligand requires 2 files (protein, ligand).")
            sys.exit(1)
        config["sim_type"] = "2"
        config["sim_type_label"] = "Protein + Ligand"
        config["pdb_input"] = all_files[0]
        config["ligand_pdb"] = all_files[1]
        config["ligand_charge"] = args.charge

    elif args.dyn_type == "ppeptide":
        if len(all_files) < 2:
            print("(!) Error: ppeptide requires 2 files (protein, peptide).")
            sys.exit(1)
        config["sim_type"] = "3"
        config["sim_type_label"] = "Protein + Peptide"
        config["pdb_protein"] = all_files[0]
        config["pdb_partner"] = all_files[1]
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "pacid":
        if len(all_files) < 2:
            print("(!) Error: pacid requires 2 files (protein, nucleic_acid).")
            sys.exit(1)
        config["sim_type"] = "4"
        config["sim_type_label"] = "Protein + Nucleic Acid"
        config["pdb_protein"] = all_files[0]
        config["pdb_partner"] = all_files[1]
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "pprotein":
        if len(all_files) < 2:
            print("(!) Error: pprotein requires 2 files (protein1, protein2).")
            sys.exit(1)
        config["sim_type"] = "5"
        config["sim_type_label"] = "Protein + Protein"
        config["pdb_protein"] = all_files[0]
        config["pdb_partner"] = all_files[1]
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")

    elif args.dyn_type == "ppligand":
        if len(all_files) < 3:
            print("(!) Error: ppligand requires 3 files (protein1, protein2, ligand).")
            sys.exit(1)
        config["sim_type"] = "6"
        config["sim_type_label"] = "Protein + Protein + Ligand/Cofactor"
        config["pdb_protein"] = all_files[0]
        config["pdb_partner"] = all_files[1]
        config["pdb_input"] = os.path.join(config["work_dir"], "complex.pdb")
        config["ligand_pdb"] = all_files[2]
        config["ligand_charge"] = args.charge
    
    print(f"\n[i] Starting simulation Params: {config['ns_time']} ns, {config['threads']} threads")
    print(f"[i] Output directory: {config['work_dir']}\n")

    pipeline = DynamicsPipeline(config)
    pipeline.execute()