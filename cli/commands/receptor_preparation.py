"""CLI command for receptor preparation."""

from argparse import ArgumentParser, _SubParsersAction

from ...pipelines.docking.steps import ReceptorPreparation


def register(subparsers: _SubParsersAction) -> None:
	parser = subparsers.add_parser(
		"receptor-preparation",
		help="Prepare receptor PDB files and convert them to PDBQT",
	)
	parser.add_argument("input_dir", help="Directory with receptor PDB files")
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--mgltools-path", default=None, help="MGLTools installation path")
	parser.add_argument("--workers", type=int, default=None, help="Number of workers")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = ReceptorPreparation(
		input_path=args.input_dir,
		output_path=args.output_dir,
		mgltools_path=args.mgltools_path,
	)
	stats = step.prepare(n_workers=args.workers)
	print("\nFinal Statistics:")
	print(f"  Successful: {stats['successful']}")
	print(f"  Failed: {stats['failed']}")
	return 0