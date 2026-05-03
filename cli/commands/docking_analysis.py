"""CLI command for docking analysis."""

from ...pipelines.docking.steps import DockingAnalysis


def register(subparsers) -> None:
	parser = subparsers.add_parser(
		"docking-analysis",
		help="Analyze docking DLG files and generate reports",
	)
	parser.add_argument("output_dir", help="Base output directory")
	parser.add_argument("--pdb-export-limit", type=int, default=10, help="Number of top candidates to export as PDB (default: 10)")
	parser.set_defaults(handler=_run)


def _run(args) -> int:
	step = DockingAnalysis(output_path=args.output_dir, pdb_export_limit=args.pdb_export_limit)
	results = step.run()
	
	print("\nDocking Analysis Complete:")
	print(f"  Poses analyzed: {results['parsed_poses']}")
	print(f"  Ligands analyzed: {results['analyzed_ligands']}")
	
	print("\nOutput files generated:")
	for name, path in results.get('outputs', {}).items():
		print(f"  • {name}: {path}")
	if not results.get('outputs'):
		print("  (none) No DLG files were found under <output_dir>/ResultadosDocking/**/dlg/*.dlg")
	
	return 0