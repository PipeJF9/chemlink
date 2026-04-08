"""CLI command for the docking preparation pipeline."""

from ...pipelines.docking import DockingPipeline


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"docking-pipeline",
		help="Run receptor preparation, ligand preparation, and active-site detection",
	)
	parser.add_argument("receptor_input_dir", help="Directory with receptor PDB files")
	parser.add_argument("ligand_input_dir", help="Directory with ligand input files")
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--mgltools-path", default=None, help="MGLTools installation path")
	parser.add_argument("--fpocket-path", default=None, help="fpocket binary path")
	parser.add_argument("--receptor-workers", type=int, default=None, help="Workers for receptor preparation")
	parser.add_argument("--ligand-workers", type=int, default=None, help="Workers for ligand preparation")
	parser.add_argument("--active-site-workers", type=int, default=None, help="Workers for active-site detection")
	parser.add_argument("--docking-workers", type=int, default=None, help="Workers for docking execution")
	parser.add_argument("--full", action="store_true", help="Run full flow: preparation + docking + analysis")
	parser.add_argument("--autogrid-executable", default=None, help="AutoGrid4 executable name")
	parser.add_argument("--autodock-gpu-executable", default=None, help="AutoDock-GPU executable path")
	parser.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"), default=None, help="Manual grid center")
	parser.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"), default=None, help="Manual AutoDock grid size")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	if (args.manual_center is None) != (args.manual_npts is None):
		raise SystemExit("Both --manual-center and --manual-npts must be provided together")

	pipeline = DockingPipeline(
		receptor_input_path=args.receptor_input_dir,
		ligand_input_path=args.ligand_input_dir,
		output_path=args.output_dir,
		mgltools_path=args.mgltools_path,
		fpocket_path=args.fpocket_path,
		manual_center=tuple(args.manual_center) if args.manual_center else None,
		manual_npts=tuple(args.manual_npts) if args.manual_npts else None,
	)
	if args.full:
		result = pipeline.run_full_pipeline(
			receptor_workers=args.receptor_workers,
			ligand_workers=args.ligand_workers,
			active_site_workers=args.active_site_workers,
			docking_workers=args.docking_workers,
			autogrid_executable=args.autogrid_executable,
			autodock_gpu_executable=args.autodock_gpu_executable,
		)
	else:
		result = pipeline.run_preparation_pipeline(
			receptor_workers=args.receptor_workers,
			ligand_workers=args.ligand_workers,
			active_site_workers=args.active_site_workers,
		)

	print("\nFinal Statistics:")
	print(f"  Receptors: {result.receptor_preparation}")
	print(f"  Ligands: {result.ligand_preparation}")
	print(f"  Active sites: {result.active_site_detection}")
	if result.docking_execution is not None:
		print(f"  Docking execution: {result.docking_execution}")
	if result.docking_analysis is not None:
		print(f"  Docking analysis: {result.docking_analysis}")
	return 0