"""CLI command for docking execution."""

from ...pipelines.docking.steps import DockingExecution


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"docking-execution",
		help="Run AutoGrid4 and AutoDock-GPU for prepared inputs",
	)
	parser.add_argument("prepared_receptors_dir", help="Directory with .maps.fld files")
	parser.add_argument("prepared_ligands_dir", help="Directory with prepared ligand files")
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--autogrid-executable", default=None, help="AutoGrid4 executable name")
	parser.add_argument("--autodock-gpu-executable", default=None, help="AutoDock-GPU executable path")
	parser.add_argument("--workers", type=int, default=None, help="Number of workers")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = DockingExecution(
		protein_maps_dir=args.prepared_receptors_dir,
		ligand_dir=args.prepared_ligands_dir,
		output_path=args.output_dir,
		autogrid_executable=args.autogrid_executable,
		autodock_gpu_executable=args.autodock_gpu_executable,
	)
	stats = step.run(n_workers=args.workers)
	print("\nFinal Statistics:")
	print(f"  Successful: {stats['successful']}")
	print(f"  Failed: {stats['failed']}")
	print(f"  Total: {stats['total']}")
	return 0