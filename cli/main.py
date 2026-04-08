"""ChemLink CLI entry point."""

import os
import sys
from argparse import ArgumentParser

if __package__ in (None, ""):
	project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	if project_root not in sys.path:
		sys.path.insert(0, project_root)

try:
	from .commands import (
		active_site,
		docking_analysis,
		docking_execution,
		docking_pipeline,
		ligand_preparation,
		receptor_preparation,
	)
except ImportError:
	from chemlink.cli.commands import (  # type: ignore
		active_site,
		docking_analysis,
		docking_execution,
		docking_pipeline,
		ligand_preparation,
		receptor_preparation,
	)


def build_parser() -> ArgumentParser:
	parser = ArgumentParser(prog="chemlink", description="ChemLink molecular docking CLI")
	subparsers = parser.add_subparsers(dest="command", required=True)

	receptor_preparation.register(subparsers)
	ligand_preparation.register(subparsers)
	active_site.register(subparsers)
	docking_execution.register(subparsers)
	docking_analysis.register(subparsers)
	docking_pipeline.register(subparsers)

	return parser


def main() -> int:
	parser = build_parser()
	args = parser.parse_args()
	return args.handler(args)


if __name__ == "__main__":
	raise SystemExit(main())