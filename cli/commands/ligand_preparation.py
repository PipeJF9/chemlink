"""CLI command for ligand preparation."""

from ...pipelines.docking.steps import LigandPreparation


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"ligand-preparation",
		help="Prepare ligand files for docking",
	)
	parser.add_argument("input_dir", help="Directory with ligand input files")
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--workers", type=int, default=None, help="Number of workers")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = LigandPreparation(
		input_path=args.input_dir,
		output_path=args.output_dir,
	)
	stats = step.prepare(n_workers=args.workers)
	print("\nFinal Statistics:")
	print(f"  Successful: {stats['successful']}")
	print(f"  Failed: {stats['failed']}")
	print(f"  Warnings: {stats['warnings']}")
	return 0