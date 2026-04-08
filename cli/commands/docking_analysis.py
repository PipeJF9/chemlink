"""CLI command for docking analysis."""

from ...pipelines.docking.steps import DockingAnalysis


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"docking-analysis",
		help="Analyze docking DLG files and generate reports",
	)
	parser.add_argument("output_dir", help="Base output directory")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = DockingAnalysis(output_path=args.output_dir)
	stats = step.run()
	print("\nFinal Statistics:")
	print(f"  Parsed: {stats['parsed']}")
	print(f"  Summarized: {stats['summarized']}")
	return 0