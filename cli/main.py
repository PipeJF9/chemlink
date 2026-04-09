"""ChemLink CLI entry point."""

import os
import sys
from argparse import ArgumentParser, Namespace
from typing import Optional, Tuple

if __package__ in (None, ""):
	project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	if project_root not in sys.path:
		sys.path.insert(0, project_root)


DEFAULT_RECEPTOR_INPUT_DIR = "data/input/receptors"
DEFAULT_LIGAND_INPUT_DIR = "data/input/ligands"
DEFAULT_OUTPUT_DIR = "data/output"
DEFAULT_PREPARED_RECEPTORS_DIR = f"{DEFAULT_OUTPUT_DIR}/prepared_receptors_pdbqt"
DEFAULT_PREPARED_LIGANDS_DIR = f"{DEFAULT_OUTPUT_DIR}/prepared_ligands_pdbqt"


def _manual_params(args: Namespace) -> Tuple[Optional[Tuple[float, float, float]], Optional[Tuple[int, int, int]]]:
	if (args.manual_center is None) != (args.manual_npts is None):
		raise SystemExit("Both --manual-center and --manual-npts must be provided together")
	center = tuple(args.manual_center) if args.manual_center else None
	npts = tuple(args.manual_npts) if args.manual_npts else None
	return center, npts


def _run_receptor_preparation(args: Namespace) -> int:
	try:
		from ..pipelines.docking.steps import ReceptorPreparation
	except ImportError:
		from chemlink.pipelines.docking.steps import ReceptorPreparation  # type: ignore

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


def _run_ligand_preparation(args: Namespace) -> int:
	try:
		from ..pipelines.docking.steps import LigandPreparation
	except ImportError:
		from chemlink.pipelines.docking.steps import LigandPreparation  # type: ignore

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


def _run_active_site(args: Namespace) -> int:
	try:
		from ..pipelines.docking.steps import ActiveSiteDetection
	except ImportError:
		from chemlink.pipelines.docking.steps import ActiveSiteDetection  # type: ignore

	manual_center, manual_npts = _manual_params(args)
	step = ActiveSiteDetection(
		receptor_path=args.receptor_dir,
		ligand_path=args.ligand_dir,
		output_path=args.output_dir,
		mgltools_path=args.mgltools_path,
		fpocket_path=args.fpocket_path,
		manual_center=manual_center,
		manual_npts=manual_npts,
	)
	stats = step.prepare(n_workers=args.workers)
	print("\nFinal Statistics:")
	print(f"  Successful: {stats['successful']}")
	print(f"  Failed: {stats['failed']}")
	return 0


def _run_docking_execution(args: Namespace) -> int:
	try:
		from ..pipelines.docking.steps import DockingExecution
	except ImportError:
		from chemlink.pipelines.docking.steps import DockingExecution  # type: ignore

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


def _run_docking_analysis(args: Namespace) -> int:
	try:
		from ..pipelines.docking.steps import DockingAnalysis
	except ImportError:
		from chemlink.pipelines.docking.steps import DockingAnalysis  # type: ignore

	step = DockingAnalysis(output_path=args.output_dir)
	stats = step.run()
	print("\nFinal Statistics:")
	print(f"  Parsed: {stats['parsed']}")
	print(f"  Summarized: {stats['summarized']}")
	return 0


def _run_docking_pipeline(args: Namespace, full: bool) -> int:
	try:
		from ..pipelines.docking import DockingPipeline
	except ImportError:
		from chemlink.pipelines.docking import DockingPipeline  # type: ignore

	manual_center, manual_npts = _manual_params(args)
	pipeline = DockingPipeline(
		receptor_input_path=args.receptor_input_dir,
		ligand_input_path=args.ligand_input_dir,
		output_path=args.output_dir,
		mgltools_path=args.mgltools_path,
		fpocket_path=args.fpocket_path,
		manual_center=manual_center,
		manual_npts=manual_npts,
	)

	if full:
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


def _run_docking_prepare(args: Namespace) -> int:
	return _run_docking_pipeline(args, full=False)


def _run_docking_full(args: Namespace) -> int:
	return _run_docking_pipeline(args, full=True)


def _add_pipeline_common_args(parser: ArgumentParser) -> None:
	parser.add_argument(
		"receptor_input_dir",
		nargs="?",
		default=DEFAULT_RECEPTOR_INPUT_DIR,
		help=f"Directory with receptor PDB files (default: {DEFAULT_RECEPTOR_INPUT_DIR})",
	)
	parser.add_argument(
		"ligand_input_dir",
		nargs="?",
		default=DEFAULT_LIGAND_INPUT_DIR,
		help=f"Directory with ligand input files (default: {DEFAULT_LIGAND_INPUT_DIR})",
	)
	parser.add_argument(
		"output_dir",
		nargs="?",
		default=DEFAULT_OUTPUT_DIR,
		help=f"Base output directory (default: {DEFAULT_OUTPUT_DIR})",
	)
	parser.add_argument("--mgltools-path", "--mgltools", dest="mgltools_path", default=None, help="MGLTools installation path")
	parser.add_argument("--fpocket-path", "--fpocket", dest="fpocket_path", default=None, help="fpocket binary path")
	parser.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"), default=None, help="Manual grid center")
	parser.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"), default=None, help="Manual AutoDock grid size")
	parser.add_argument("--receptor-workers", "-r", type=int, default=None, help="Workers for receptor preparation")
	parser.add_argument("--ligand-workers", "-l", type=int, default=None, help="Workers for ligand preparation")
	parser.add_argument("--active-site-workers", "-a", type=int, default=None, help="Workers for active-site detection")


def _add_pipeline_full_only_args(parser: ArgumentParser) -> None:
	parser.add_argument("--docking-workers", "-d", type=int, default=1, help="Workers for docking execution (default: 1)")
	parser.add_argument("--autogrid-executable", "--autogrid", dest="autogrid_executable", default=None, help="AutoGrid4 executable")
	parser.add_argument("--autodock-gpu-executable", "--autodock", dest="autodock_gpu_executable", default=None, help="AutoDock-GPU executable")


def _register_legacy_commands(subparsers) -> None:
	# receptor-preparation
	receptor = subparsers.add_parser("receptor-preparation", help="Prepare receptor PDB files and convert them to PDBQT")
	receptor.add_argument("input_dir", help="Directory with receptor PDB files")
	receptor.add_argument("output_dir", help="Base output directory")
	receptor.add_argument("--mgltools-path", default=None, help="MGLTools installation path")
	receptor.add_argument("--workers", type=int, default=None, help="Number of workers")
	receptor.set_defaults(handler=_run_receptor_preparation)

	# ligand-preparation
	ligand = subparsers.add_parser("ligand-preparation", help="Prepare ligand files for docking")
	ligand.add_argument("input_dir", help="Directory with ligand input files")
	ligand.add_argument("output_dir", help="Base output directory")
	ligand.add_argument("--workers", type=int, default=None, help="Number of workers")
	ligand.set_defaults(handler=_run_ligand_preparation)

	# active-site
	active = subparsers.add_parser("active-site", help="Detect active sites and generate GPF files")
	active.add_argument("receptor_dir", help="Directory with prepared receptor PDBQT files")
	active.add_argument("ligand_dir", help="Directory with prepared ligand PDBQT files")
	active.add_argument("output_dir", help="Base output directory")
	active.add_argument("--mgltools-path", default=None, help="MGLTools installation path")
	active.add_argument("--fpocket-path", default=None, help="fpocket binary path")
	active.add_argument("--workers", type=int, default=None, help="Number of workers")
	active.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"), default=None, help="Manual grid center")
	active.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"), default=None, help="Manual AutoDock grid size")
	active.set_defaults(handler=_run_active_site)

	# docking-execution
	exec_cmd = subparsers.add_parser("docking-execution", help="Run AutoGrid4 and AutoDock-GPU for prepared inputs")
	exec_cmd.add_argument("prepared_receptors_dir", help="Directory with .maps.fld files")
	exec_cmd.add_argument("prepared_ligands_dir", help="Directory with prepared ligand files")
	exec_cmd.add_argument("output_dir", help="Base output directory")
	exec_cmd.add_argument("--autogrid-executable", default=None, help="AutoGrid4 executable name")
	exec_cmd.add_argument("--autodock-gpu-executable", default=None, help="AutoDock-GPU executable path")
	exec_cmd.add_argument("--workers", type=int, default=None, help="Number of workers")
	exec_cmd.set_defaults(handler=_run_docking_execution)

	# docking-analysis
	analysis = subparsers.add_parser("docking-analysis", help="Analyze docking DLG files and generate reports")
	analysis.add_argument("output_dir", help="Base output directory")
	analysis.set_defaults(handler=_run_docking_analysis)

	# docking-pipeline (legacy flat command)
	pipeline = subparsers.add_parser("docking-pipeline", help="Run full pipeline (legacy flat command)")
	_add_pipeline_common_args(pipeline)
	_add_pipeline_full_only_args(pipeline)
	pipeline.add_argument("--full", action="store_true", help="Run full flow: preparation + docking + analysis")
	pipeline.set_defaults(handler=lambda args: _run_docking_pipeline(args, full=args.full))


def _register_grouped_commands(subparsers) -> None:
	docking = subparsers.add_parser("docking", help="Docking workflows with intuitive subcommands")
	docking_sub = docking.add_subparsers(dest="docking_command", required=True)

	prepare = docking_sub.add_parser("prepare", aliases=["prep"], help="Run preparation stages only")
	_add_pipeline_common_args(prepare)
	prepare.set_defaults(handler=_run_docking_prepare)

	full = docking_sub.add_parser("full", help="Run preparation + execution + analysis")
	_add_pipeline_common_args(full)
	_add_pipeline_full_only_args(full)
	full.set_defaults(handler=_run_docking_full)

	run = docking_sub.add_parser("run", help="Run docking execution on prepared files")
	run.add_argument(
		"prepared_receptors_dir",
		nargs="?",
		default=DEFAULT_PREPARED_RECEPTORS_DIR,
		help=f"Directory with .maps.fld/.gpf files (default: {DEFAULT_PREPARED_RECEPTORS_DIR})",
	)
	run.add_argument(
		"prepared_ligands_dir",
		nargs="?",
		default=DEFAULT_PREPARED_LIGANDS_DIR,
		help=f"Directory with prepared ligand files (default: {DEFAULT_PREPARED_LIGANDS_DIR})",
	)
	run.add_argument(
		"output_dir",
		nargs="?",
		default=DEFAULT_OUTPUT_DIR,
		help=f"Base output directory (default: {DEFAULT_OUTPUT_DIR})",
	)
	run.add_argument("--workers", "-w", type=int, default=1, help="Number of workers (default: 1)")
	run.add_argument("--autogrid-executable", "--autogrid", dest="autogrid_executable", default=None, help="AutoGrid4 executable")
	run.add_argument("--autodock-gpu-executable", "--autodock", dest="autodock_gpu_executable", default=None, help="AutoDock-GPU executable")
	run.set_defaults(handler=_run_docking_execution)

	analyze = docking_sub.add_parser("analyze", aliases=["analysis"], help="Analyze generated DLG results")
	analyze.add_argument("output_dir", help="Base output directory")
	analyze.set_defaults(handler=_run_docking_analysis)


def build_parser() -> ArgumentParser:
	parser = ArgumentParser(prog="chemlink", description="ChemLink molecular docking CLI")
	subparsers = parser.add_subparsers(dest="command", required=True)

	_register_grouped_commands(subparsers)
	_register_legacy_commands(subparsers)

	return parser


def main() -> int:
	parser = build_parser()
	args = parser.parse_args()
	return args.handler(args)


if __name__ == "__main__":
	raise SystemExit(main())