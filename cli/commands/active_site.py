"""CLI command for active site detection."""

from ...pipelines.docking.steps import ActiveSiteDetection


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"active-site",
		help="Detect active sites and generate GPF files",
	)
	parser.add_argument("receptor_dir", help="Directory with prepared receptor PDBQT files")
	parser.add_argument("ligand_dir", help="Directory with prepared ligand PDBQT files")
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--mgltools-path", default=None, help="MGLTools installation path")
	parser.add_argument("--fpocket-path", default=None, help="fpocket binary path")
	parser.add_argument("--workers", type=int, default=None, help="Number of workers")
	parser.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"), default=None, help="Manual grid center")
	parser.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"), default=None, help="Manual AutoDock grid size")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = ActiveSiteDetection(
		receptor_path=args.receptor_dir,
		ligand_path=args.ligand_dir,
		output_path=args.output_dir,
		mgltools_path=args.mgltools_path,
		fpocket_path=args.fpocket_path,
		manual_center=tuple(args.manual_center) if args.manual_center else None,
		manual_npts=tuple(args.manual_npts) if args.manual_npts else None,
	)
	stats = step.prepare(n_workers=args.workers)
	print("\nFinal Statistics:")
	print(f"  Successful: {stats['successful']}")
	print(f"  Failed: {stats['failed']}")
	return 0