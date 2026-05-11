"""ChemLink CLI — unified molecular simulation toolkit entry point."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from argparse import ArgumentParser, HelpFormatter, Namespace
from datetime import datetime
from typing import Optional, Tuple
from uuid import uuid4

# ── Colour support ─────────────────────────────────────────────────────────────
# Respects NO_COLOR env var and non-TTY pipes automatically.
_TTY = sys.stdout.isatty() and not os.environ.get("NO_COLOR")


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _TTY else text


def bold(t: str) -> str:        return _c("1",    t)
def dim(t: str) -> str:         return _c("2",    t)
def red(t: str) -> str:         return _c("31",   t)
def green(t: str) -> str:       return _c("32",   t)
def yellow(t: str) -> str:      return _c("33",   t)
def cyan(t: str) -> str:        return _c("36",   t)
def bold_green(t: str) -> str:  return _c("1;32", t)
def bold_cyan(t: str) -> str:   return _c("1;36", t)
def bold_red(t: str) -> str:    return _c("1;31", t)
def bold_yellow(t: str) -> str: return _c("1;33", t)


# ── Logo ───────────────────────────────────────────────────────────────────────
LOGO = (
    "                                    ⢠⡆⠤⠀\n"
    "                                    ⠻⢿⣿⣿⣷⢤⡁\n"
    "                                        ⠉⠙⢿⣿⣿⣷⢦⡁\n"
    "                        ⡁⢤⢦⠤⠁        "
    "     ⠈⠙⠿⣿⣿⣿⠦⡁⠁\n"
    "                   ⠢⡁⢤⢶⢿⣿⣿⣿⣿⣶⢤⠁"
    "              ⠈⠙⠻⣿⣿⣿⢶⡁⠁\n"
    "              ⡁⢤⢾⣿⣿⣿⣿⣿⠿⠻⢿⣿⣿⣿⣿⣷⢦⡁"
    "                 ⠙⠻⢿⣿⣿⣿⠤⠁\n"
    "         ⠢⡁⢶⢿⣿⣿⣿⣿⣿⠿⠙⠉"
    "           ⠉⠙⢿⣿⣿⣿⣿⣿⢦⡁"
    "           ⠈⠻⢿⣿⣿⣿⣷⢦⡁\n"
    "    ⠢⡁⢴⢾⣿⣿⣿⣿⣿⠿⠙⠉"
    "                    ⠙⠿⣿⣿⣿⣿⣿⢶⡁⠁"
    "            ⠈⠙⠿⣿⣿⣿⣿⣿⣆\n"
    "⡁⢤⢶⣿⣿⣿⣿⣿⠿⠙⠉"
    "                                ⠻⢿⣿⣿⣿⣿⣷⢤⡁"
    "            ⠈⠙⠙\n"
    "⠢⡁⢴⣿⣿⣿⣿⣿⠿⠙⠉"
    "                 ⡁⢤⢶⣿⣿⣿⢦⡁⠁"
    "            ⠉⠻⢿⣿⣿⣿⣿⣷⢦⡁\n"
    "⠈⢺⣿⣿⣿⠿⠙⠉              ⠢⡁⢴⢾⣿⣿⣿⣿⣿⣿⣿⣿⢶⢤⠁"
    "               ⠉⠻⢿⣿⣿⣿⣿⣿⢶\n"
    "⠈⢸⣿⣿⠀     ⠀⠢⡁⢶⣿⣿⣿⣿⣿⠿⠙⠙⠻⢿⣿⣿⣿⣿⣿⢦⡁"
    "               ⠉⠙⢿⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⠢⡁⢾⣿⣿⣿⣿⣿⠿⠙⠉"
    "             ⠈⠙⠿⣿⣿⣿⣿⣿⢶⡁⠁"
    "        ⠀⠀⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠿⠙⠉"
    "                                ⠢⠙⣿⣿⣿⣿⣿⢷       ⠀⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇     ⣿⣿⣿⣿⠀"
    "                         ⣿⣿⣿⣿⠀     ⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇  ⠀  ⣿⣿⣿⣿⠀"
    "                          ⣿⣿⣿⣿⠀     ⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇  ⠀  ⣿⣿⣿⣿⠀"
    "                          ⣿⣿⣿⣿⠀  ⠢⡁⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇  ⠀  ⣿⣿⣿⣿⠀"
    "                          ⣿⣿⣿⣿⠀⢤⢶⣿⣿⣿⣿⣿\n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇  ⠀  ⣿⣿⣿⣿⢶⡁⠁"
    "                   ⠀⠀⠀⠀⠢⡁⣿⣿⣿⣿⣿⣿⠿⠙⠉"
    "           \n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⠇  ⠀  ⠙⠻⣿⣿⣿⣿⣿⣷⢤⠁"
    "                ⠢⢴⢾⣿⣿⣿⣿⣿⠿⠙⠉"
    "               \n"
    "⠈⢸⣿⣿⠀  ⢸⣿⣿⣿⢧⡁⠁     ⠀⠉⠻⢿⣿⣿⣿⣿⣷⢦⡁"
    "        ⠸⣿⣿⠀⠀⠀⠢⢤⢶⣿⣿⣿⣿⣿⠿⠙⠉"
    "               ⠢⡁⢴⢾⣆\n"
    "⠸⠿⠿⠀   ⠸⠿⣿⣿⣿⣿⣿⢶⢤⠁     ⠈⠙⠿⣿⣿⣿⣿⣿⢶⢤⣿⣿⢠⢴⢾⣿⣿⣿⣿⣿⠙⠉"
    "        ⡁⢤⢾⣿⣿⣿⣿⣿\n"
    "              ⠙⠻⢿⣿⣿⣿⣿⣷⢦⡁     ⠈⠙⠻⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠙⠉"
    "        ⠢⡁⢴⣿⣿⣿⣿⣿⠿⠙⠉\n"
    "                   ⠉⠙⢿⣿⣿⣿⣿⣷⢦⡁     ⠀⠀⠀⢺⣿⣿⠿⠙⠉"
    "        ⠢⡁⢶⣿⣿⣿⣿⣿⠿⠙⠉\n"
    "                         ⠉⠙⠿⢿⣿⣿⣿⣷⢤⣿⣿⣿⣿⣿⠿⠙⠉"
    "        ⠢⢴⢾⣿⣿⣿⣿⠿⠙⠉"
    "               \n"
    "                               ⠀⠈⠙⠿⣿⣿⣿⣿⣿⣿⠿⠙⠉"
    "        ⠢⢤⢶⣿⣿⣿⣿⠿⠙⠉\n"
    "                                           ⠢⢶⣿⣿⣿⠿⠙⠉\n"
    "                                           ⠀⠻⠿⠙⠉"
)

VERSION = "0.1.0"

# ── Default paths ──────────────────────────────────────────────────────────────
_REC_IN  = "data/input/receptors"
_LIG_IN  = "data/input/ligands"
_OUT     = "data/output"
_REC_OUT = f"{_OUT}/prepared_receptors_pdbqt"
_LIG_OUT = f"{_OUT}/prepared_ligands_pdbqt"
PIPELINE_STEPS = ("receptor", "ligand", "active-site", "execution", "analysis")

# ── Output helpers ─────────────────────────────────────────────────────────────

def ok(msg: str) -> str:   return f"  {bold_green('✓')}  {msg}"
def err(msg: str) -> str:  return f"  {bold_red('✗')}  {msg}"
def warn(msg: str) -> str: return f"  {bold_yellow('!')}  {msg}"
def info(msg: str) -> str: return f"  {cyan('·')}  {msg}"


def table(headers: list, rows: list) -> str:
    """Return a unicode box table as a string."""
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    def _seg(l: str, m: str, r: str) -> str:
        return l + m.join("─" * (w + 2) for w in widths) + r

    def _row(cells: list, color_fn=None) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i < len(widths):
                s = str(cell).ljust(widths[i])
                parts.append(f" {color_fn(s) if color_fn else s} ")
        return "│" + "│".join(parts) + "│"

    lines = [_seg("┌", "┬", "┐"), _row(headers, bold_cyan), _seg("├", "┼", "┤")]
    for r in rows:
        lines.append(_row(r))
    lines.append(_seg("└", "┴", "┘"))
    return "\n".join(lines)


def print_stats(stats: dict, title: str = "Results") -> None:
    rows = [[k, str(v)] for k, v in stats.items()]
    print(f"\n  {bold(title)}")
    print(table(["Metric", "Value"], rows))


# ── Custom formatter ───────────────────────────────────────────────────────────

class _Fmt(HelpFormatter):
    def __init__(self, prog: str):
        super().__init__(prog, max_help_position=32, width=88)

    def _fill_text(self, text: str, width: int, indent: str) -> str:
        # Preserve intentional newlines in description and epilog.
        return "\n".join(indent + line for line in text.splitlines())

    def start_section(self, heading: Optional[str]) -> None:
        super().start_section(bold_cyan(heading.upper()) if heading else heading)

    def _format_action_invocation(self, action) -> str:
        return cyan(super()._format_action_invocation(action))

    def _format_usage(self, usage, actions, groups, prefix) -> str:
        return super()._format_usage(
            usage, actions, groups,
            bold("Usage: ") if prefix is None else prefix,
        )


# ── Custom parser with coloured errors ────────────────────────────────────────

_TOP_CMDS = ["docking", "dynamic", "doctor", "completion"]


def _suggest(word: str) -> list:
    if not word or word.startswith("-"):
        return []
    return [c for c in _TOP_CMDS if c.startswith(word) or word in c][:3]


class _Parser(ArgumentParser):
    def error(self, message: str) -> None:
        sys.stderr.write(f"\n{bold_red('Error:')} {message}\n")
        if len(sys.argv) > 1:
            matches = _suggest(sys.argv[1])
            if matches:
                sys.stderr.write(
                    f"  Did you mean: {', '.join(cyan(m) for m in matches)}?\n"
                )
        sys.stderr.write(f"\n  Run {cyan('chemlink --help')} to see all commands.\n\n")
        sys.exit(2)


# ── Misc helpers ───────────────────────────────────────────────────────────────

def _manual_params(args: Namespace) -> Tuple[Optional[tuple], Optional[tuple]]:
    if (args.manual_center is None) != (args.manual_npts is None):
        sys.exit(
            f"{bold_red('Error:')} --manual-center and --manual-npts must be used together."
        )
    center = tuple(args.manual_center) if args.manual_center else None
    npts   = tuple(args.manual_npts)   if args.manual_npts   else None
    return center, npts


def _run_dir(base: str) -> str:
    os.makedirs(base, exist_ok=True)
    name = f"run_{datetime.now():%Y%m%dT%H%M%S}_{uuid4().hex[:8]}"
    path = os.path.join(base, name)
    os.makedirs(path)
    return path


# ── Docking command handlers ───────────────────────────────────────────────────

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
    print_stats(step.prepare(n_workers=args.workers), "Receptor Preparation")
    return 0


def _run_ligand_preparation(args: Namespace) -> int:
    try:
        from ..pipelines.docking.steps import LigandPreparation
    except ImportError:
        from chemlink.pipelines.docking.steps import LigandPreparation  # type: ignore
    step = LigandPreparation(input_path=args.input_dir, output_path=args.output_dir)
    print_stats(step.prepare(n_workers=args.workers), "Ligand Preparation")
    return 0


def _run_active_site(args: Namespace) -> int:
    try:
        from ..pipelines.docking.steps import ActiveSiteDetection
    except ImportError:
        from chemlink.pipelines.docking.steps import ActiveSiteDetection  # type: ignore
    center, npts = _manual_params(args)
    step = ActiveSiteDetection(
        receptor_path=args.receptor_dir,
        ligand_path=args.ligand_dir,
        output_path=args.output_dir,
        mgltools_path=args.mgltools_path,
        fpocket_path=args.fpocket_path,
        manual_center=center,
        manual_npts=npts,
    )
    print_stats(step.prepare(n_workers=args.workers), "Active Site Detection")
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
    workers = getattr(args, "workers", getattr(args, "docking_workers", 1))
    print_stats(step.run(n_workers=workers), "Docking Execution")
    return 0


def _run_docking_analysis(args: Namespace) -> int:
    try:
        from ..pipelines.docking.steps import DockingAnalysis
    except ImportError:
        from chemlink.pipelines.docking.steps import DockingAnalysis  # type: ignore
    step = DockingAnalysis(
        output_path=args.output_dir,
        pdb_export_limit=args.pdb_export_limit,
        max_workers=args.max_workers,
    )
    results = step.run()
    print_stats(
        {"Poses analyzed": results["parsed_poses"], "Ligands analyzed": results["analyzed_ligands"]},
        "Docking Analysis",
    )
    outputs = results.get("outputs", {})
    if outputs:
        print(f"\n  {bold('Output files:')}")
        for name, path in outputs.items():
            print(ok(f"{dim(name)}: {path}"))
    else:
        print(warn(f"No DLG files found under {args.output_dir}/docking_results/**/dlg/*.dlg"))
    return 0


def _run_docking_flow(args: Namespace) -> int:
    try:
        from ..pipelines.docking import DockingPipeline
    except ImportError:
        from chemlink.pipelines.docking import DockingPipeline  # type: ignore
    center, npts = _manual_params(args)
    run_output = _run_dir(args.output_dir)
    result = DockingPipeline(
        receptor_input_path=args.receptor_input_dir,
        ligand_input_path=args.ligand_input_dir,
        output_path=run_output,
        mgltools_path=args.mgltools_path,
        fpocket_path=args.fpocket_path,
        manual_center=center,
        manual_npts=npts,
    ).run_step_range(
        from_step=args.from_step,
        to_step=args.to_step,
        receptor_workers=args.receptor_workers,
        ligand_workers=args.ligand_workers,
        active_site_workers=args.active_site_workers,
        docking_workers=args.docking_workers,
        autogrid_executable=args.autogrid_executable,
        autodock_gpu_executable=args.autodock_gpu_executable,
        pdb_export_limit=args.pdb_export_limit,
        max_workers=args.max_workers,
    )
    stats: dict = {"Run directory": run_output, "Steps": ", ".join(result.executed_steps)}
    if "receptor"    in result.executed_steps: stats["Receptors"]         = result.receptor_preparation
    if "ligand"      in result.executed_steps: stats["Ligands"]           = result.ligand_preparation
    if "active-site" in result.executed_steps: stats["Active sites"]      = result.active_site_detection
    if "execution"   in result.executed_steps and result.docking_execution:
        stats["Docking execution"] = result.docking_execution
    if "analysis"    in result.executed_steps and result.docking_analysis:
        stats["Docking analysis"]  = result.docking_analysis
    print_stats(stats, "Pipeline Results")
    return 0


def _run_docking_pipeline(args: Namespace, *, full: bool) -> int:
    try:
        from ..pipelines.docking import DockingPipeline
    except ImportError:
        from chemlink.pipelines.docking import DockingPipeline  # type: ignore
    center, npts = _manual_params(args)
    out = _run_dir(args.output_dir) if full else args.output_dir
    pipeline = DockingPipeline(
        receptor_input_path=args.receptor_input_dir,
        ligand_input_path=args.ligand_input_dir,
        output_path=out,
        mgltools_path=args.mgltools_path,
        fpocket_path=args.fpocket_path,
        manual_center=center,
        manual_npts=npts,
    )
    result = (
        pipeline.run_full_pipeline(
            receptor_workers=args.receptor_workers,
            ligand_workers=args.ligand_workers,
            active_site_workers=args.active_site_workers,
            docking_workers=args.docking_workers,
            autogrid_executable=args.autogrid_executable,
            autodock_gpu_executable=args.autodock_gpu_executable,
            pdb_export_limit=args.pdb_export_limit,
        )
        if full
        else pipeline.run_preparation_pipeline(
            receptor_workers=args.receptor_workers,
            ligand_workers=args.ligand_workers,
            active_site_workers=args.active_site_workers,
        )
    )
    stats: dict = {}
    if full:
        stats["Run directory"] = out
    stats.update({
        "Receptors":    result.receptor_preparation,
        "Ligands":      result.ligand_preparation,
        "Active sites": result.active_site_detection,
    })
    if result.docking_execution: stats["Docking execution"] = result.docking_execution
    if result.docking_analysis:  stats["Docking analysis"]  = result.docking_analysis
    print_stats(stats, "Pipeline Results")
    return 0


# ── Dynamics command handler ───────────────────────────────────────────────────

def _resolve_file(filename: str, *, from_input_dir: bool) -> str:
    return os.path.join("data/input/dynamics", filename) if from_input_dir else filename


_DYN_SPEC = {
    #  name        sim_id  label                              min_files
    "oprotein":  ("1", "Protein",                               1),
    "pligand":   ("2", "Protein + Ligand",                      2),
    "ppeptide":  ("3", "Protein + Peptide",                     2),
    "pacid":     ("4", "Protein + Nucleic Acid",                2),
    "pprotein":  ("5", "Protein + Protein",                     2),
    "ppligand":  ("6", "Protein + Protein + Ligand/Cofactor",   3),
}

_DYN_FILE_LABELS = {
    "oprotein":  ["protein"],
    "pligand":   ["protein", "ligand"],
    "ppeptide":  ["protein", "peptide"],
    "pacid":     ["protein", "nucleic_acid"],
    "pprotein":  ["protein1", "protein2"],
    "ppligand":  ["protein1", "protein2", "ligand"],
}


def _run_dynamic(args: Namespace) -> int:
    try:
        from ..pipelines.dynamics.dynamics_pipeline import DynamicsPipeline
        from ..pipelines.dynamics.utils import get_system_threads, setup_work_directory
    except ImportError:
        try:
            from chemlink.pipelines.dynamics.dynamics_pipeline import DynamicsPipeline  # type: ignore
            from chemlink.pipelines.dynamics.utils import get_system_threads, setup_work_directory  # type: ignore
        except ImportError:
            from pipelines.dynamics.dynamics_pipeline import DynamicsPipeline  # type: ignore
            from pipelines.dynamics.utils import get_system_threads, setup_work_directory  # type: ignore

    dyn_type = args.dyn_type
    sim_id, label, min_files = _DYN_SPEC[dyn_type]

    # Collect files: -i flags resolve from data/input/dynamics; positional are raw paths.
    all_files = (
        [_resolve_file(f, from_input_dir=True) for f in (args.input_files or [])]
        + list(getattr(args, "files", None) or [])
    )

    if len(all_files) < min_files:
        needed = ", ".join(_DYN_FILE_LABELS[dyn_type])
        sys.stderr.write(
            f"\n{bold_red('Error:')} '{dyn_type}' requires {min_files} file(s): {needed}\n"
            f"  Got {len(all_files)}. Use {cyan('-i FILE')} for files inside data/input/dynamics.\n\n"
        )
        return 1

    work_dir = setup_work_directory("data/output/dynamics", dyn_type)
    threads  = get_system_threads()
    config: dict = {
        "sim_type":       sim_id,
        "sim_type_label": label,
        "ns_time":        args.time,
        "threads":        threads,
        "work_dir":       work_dir,
    }

    if dyn_type == "oprotein":
        config["pdb_input"] = all_files[0]
    elif dyn_type == "pligand":
        config.update(pdb_input=all_files[0], ligand_pdb=all_files[1],
                      ligand_charge=args.charge)
    elif dyn_type in ("ppeptide", "pacid", "pprotein"):
        config.update(pdb_protein=all_files[0], pdb_partner=all_files[1],
                      pdb_input=os.path.join(work_dir, "complex.pdb"))
    elif dyn_type == "ppligand":
        config.update(pdb_protein=all_files[0], pdb_partner=all_files[1],
                      pdb_input=os.path.join(work_dir, "complex.pdb"),
                      ligand_pdb=all_files[2], ligand_charge=args.charge)

    print()
    print(info(f"Simulation : {bold(label)}"))
    print(info(f"Duration   : {bold(str(args.time) + ' ns')}"))
    print(info(f"Threads    : {bold(str(threads))}"))
    print(info(f"Output     : {bold(work_dir)}"))
    print()

    DynamicsPipeline(config).execute()
    return 0


# ── Doctor ─────────────────────────────────────────────────────────────────────

def _run_doctor(args: Namespace) -> int:
    """Environment prerequisite check (full diagnostics planned — partial for now)."""
    print(f"\n  {bold('ChemLink Doctor')}  {dim('— environment prerequisite check')}\n")

    def _has_module(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    checks = [
        ("Python ≥ 3.9",   sys.version_info >= (3, 9),      sys.version.split()[0]),
        ("tqdm",           _has_module("tqdm"),              None),
        ("numpy",          _has_module("numpy"),             None),
        ("rdkit",          _has_module("rdkit"),             None),
        ("MGLTools",       bool(shutil.which("pythonsh")),   shutil.which("pythonsh")   or "not found"),
        ("fpocket",        bool(shutil.which("fpocket")),    shutil.which("fpocket")    or "not found"),
        ("AutoGrid4",      bool(shutil.which("autogrid4")),  shutil.which("autogrid4")  or "not found"),
        ("AutoDock-GPU",   bool(shutil.which("autodock_gpu")), shutil.which("autodock_gpu") or "not found"),
        ("GROMACS (gmx)",  bool(shutil.which("gmx")),       shutil.which("gmx")        or "not found"),
    ]

    passed = 0
    for name, is_ok, detail in checks:
        icon  = bold_green("✓") if is_ok else bold_red("✗")
        extra = f"  {dim(str(detail))}" if detail else ""
        print(f"  {icon}  {name}{extra}")
        passed += is_ok

    total = len(checks)
    print()
    if passed == total:
        print(ok(f"All {total} checks passed."))
    else:
        print(warn(f"{passed}/{total} checks passed — install missing tools to unlock all features."))

    print(f"\n  {dim('Note: full doctor diagnostics (version checks, config validation) are planned.')}\n")
    return 0


# ── Shell completion ───────────────────────────────────────────────────────────

_BASH_SCRIPT = """\
# ChemLink bash completion
# Add to ~/.bashrc:  source <(chemlink completion bash)

_chemlink() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    case "${COMP_WORDS[1]}" in
        docking)
            COMPREPLY=( $(compgen -W "prepare prep full flow run analyze analysis --help" -- "$cur") );;
        dynamic)
            COMPREPLY=( $(compgen -W "oprotein pligand ppeptide pacid pprotein ppligand --help" -- "$cur") );;
        completion)
            COMPREPLY=( $(compgen -W "bash zsh fish install" -- "$cur") );;
        *)
            COMPREPLY=( $(compgen -W "docking dynamic doctor completion --help --version" -- "$cur") );;
    esac
}
complete -F _chemlink chemlink
"""

_ZSH_SCRIPT = """\
#compdef chemlink
# ChemLink zsh completion
# Add to ~/.zshrc:  source <(chemlink completion zsh)

_chemlink() {
    local -a top dock dyn
    top=('docking:Molecular docking workflows' 'dynamic:Molecular dynamics simulations'
         'doctor:Check environment prerequisites' 'completion:Generate shell completion scripts')
    dock=('prepare:Preparation stages only (receptor+ligand+active-site)' 'prep:Alias for prepare'
          'full:Full pipeline (prepare + execution + analysis)' 'flow:Run a contiguous subset of steps'
          'run:Docking execution on prepared files' 'analyze:Analyze DLG results')
    dyn=('oprotein:Protein-only simulation' 'pligand:Protein + small-molecule ligand'
         'ppeptide:Protein + peptide' 'pacid:Protein + nucleic acid'
         'pprotein:Protein + protein' 'ppligand:Protein + protein + ligand/cofactor')

    case $words[2] in
        docking)   _describe 'docking subcommands' dock;;
        dynamic)   _describe 'dynamic types' dyn;;
        completion) _values 'shell' bash zsh fish install;;
        *)         _describe 'commands' top;;
    esac
}
_chemlink "$@"
"""


def _run_completion(args: Namespace) -> int:
    shell = args.shell
    if shell == "bash":
        print(_BASH_SCRIPT)
    elif shell == "zsh":
        print(_ZSH_SCRIPT)
    elif shell == "fish":
        sys.stderr.write("Fish completion is not yet available. Use bash or zsh.\n")
        return 1
    elif shell == "install":
        _install_completion()
    return 0


def _install_completion() -> None:
    shell_bin = os.environ.get("SHELL", "")
    is_zsh    = "zsh" in shell_bin
    rc        = os.path.expanduser("~/.zshrc" if is_zsh else "~/.bashrc")
    line      = f'source <(chemlink completion {"zsh" if is_zsh else "bash"})'
    print(info(f"Appending completion hook to {rc}"))
    try:
        with open(rc, "a") as fh:
            fh.write(f"\n# ChemLink autocompletion\n{line}\n")
        print(ok(f"Done. Restart your shell or run:  {cyan('source ' + rc)}"))
    except OSError as exc:
        print(err(f"Could not write to {rc}: {exc}"))


# ── Argument parser ────────────────────────────────────────────────────────────

def _common_pipeline_args(p: ArgumentParser) -> None:
    p.add_argument("receptor_input_dir", nargs="?", default=_REC_IN, metavar="RECEPTOR_DIR",
                   help=f"Receptor PDB directory  [{_REC_IN}]")
    p.add_argument("ligand_input_dir", nargs="?", default=_LIG_IN, metavar="LIGAND_DIR",
                   help=f"Ligand input directory  [{_LIG_IN}]")
    p.add_argument("output_dir", nargs="?", default=_OUT, metavar="OUTPUT_DIR",
                   help=f"Base output directory  [{_OUT}]")
    p.add_argument("--mgltools-path", "--mgltools", dest="mgltools_path", metavar="PATH",
                   help="MGLTools installation path")
    p.add_argument("--fpocket-path", "--fpocket", dest="fpocket_path", metavar="PATH",
                   help="fpocket binary path")
    p.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"),
                   help="Manual grid center  (requires --manual-npts)")
    p.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"),
                   help="Manual AutoDock grid dimensions  (requires --manual-center)")
    p.add_argument("--receptor-workers", "-r", type=int, metavar="N",
                   help="Parallel workers for receptor preparation")
    p.add_argument("--ligand-workers", "-l", type=int, metavar="N",
                   help="Parallel workers for ligand preparation")
    p.add_argument("--active-site-workers", "-a", type=int, metavar="N",
                   help="Parallel workers for active-site detection")


def _exec_args(p: ArgumentParser) -> None:
    p.add_argument("--docking-workers", "-d", type=int, default=1, metavar="N",
                   help="Parallel workers for docking execution  [1]")
    p.add_argument("--autogrid-executable", "--autogrid", dest="autogrid_executable", metavar="EXE",
                   help="AutoGrid4 executable path or name")
    p.add_argument("--autodock-gpu-executable", "--autodock", dest="autodock_gpu_executable", metavar="EXE",
                   help="AutoDock-GPU executable path or name")
    p.add_argument("--pdb-export-limit", type=int, default=10, metavar="N",
                   help="Top candidates to export as PDB  [10]")
    p.add_argument("--max-workers", type=int, default=4, metavar="N",
                   help="Max parallel threads for PDB export  [4]")


def _step_range_args(p: ArgumentParser) -> None:
    choices_str = " | ".join(PIPELINE_STEPS)
    p.add_argument("--from-step", choices=PIPELINE_STEPS, default="receptor", metavar="STEP",
                   help=f"First pipeline step  [receptor]  ({choices_str})")
    p.add_argument("--to-step", choices=PIPELINE_STEPS, default="analysis", metavar="STEP",
                   help=f"Last pipeline step   [analysis]  ({choices_str})")


def _dyn_parent() -> ArgumentParser:
    p = ArgumentParser(add_help=False)
    p.add_argument("-i", "--input-dir", action="append", dest="input_files", metavar="FILE",
                   help="File inside data/input/dynamics  (repeatable)")
    p.add_argument("files", nargs="*", metavar="PATH",
                   help="Absolute or relative file paths")
    p.add_argument("-t", "--time", type=float, default=0.1, metavar="NS",
                   help="Simulation time in nanoseconds  [0.1]")
    return p


def build_parser() -> _Parser:
    epilog = (
        f"\n  {bold('Quick examples:')}\n"
        f"    {cyan('chemlink docking prepare')}  data/receptors  data/ligands\n"
        f"    {cyan('chemlink docking full')}     data/receptors  data/ligands\n"
        f"    {cyan('chemlink dynamic oprotein')} -i protein.pdb  -t 0.5\n"
        f"    {cyan('chemlink dynamic pligand')}  -i prot.pdb -i lig.pdbqt -c 0\n"
        f"    {cyan('chemlink doctor')}\n"
        f"    {cyan('chemlink completion bash')}  >> ~/.bashrc  &&  source ~/.bashrc\n"
    )

    parser = _Parser(
        prog="chemlink",
        formatter_class=_Fmt,
        epilog=epilog,
    )
    parser.add_argument("--version", "-V", action="version", version=f"chemlink {VERSION}")

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ── docking ────────────────────────────────────────────────────────────────
    dock_desc = (
        f"  {bold_cyan('docking')}  — Run molecular docking pipelines.\n\n"
        f"  Pipeline steps (in order):\n"
        f"    {cyan('receptor')}  →  {cyan('ligand')}  →  {cyan('active-site')}  "
        f"→  {cyan('execution')}  →  {cyan('analysis')}"
    )
    dock = sub.add_parser("docking", help="Molecular docking workflows",
                          description=dock_desc, formatter_class=_Fmt)
    dock_sub = dock.add_subparsers(dest="docking_command", metavar="SUBCOMMAND")

    prep = dock_sub.add_parser("prepare", aliases=["prep"], formatter_class=_Fmt,
                               help="Preparation only  (receptor + ligand + active-site)")
    _common_pipeline_args(prep)
    prep.set_defaults(handler=lambda a: _run_docking_pipeline(a, full=False))

    full_p = dock_sub.add_parser("full", formatter_class=_Fmt,
                                 help="Full pipeline  (preparation + execution + analysis)")
    _common_pipeline_args(full_p)
    _exec_args(full_p)
    full_p.set_defaults(handler=lambda a: _run_docking_pipeline(a, full=True))

    flow_p = dock_sub.add_parser("flow", formatter_class=_Fmt,
                                 help="Run any contiguous subset of pipeline steps")
    _common_pipeline_args(flow_p)
    _exec_args(flow_p)
    _step_range_args(flow_p)
    flow_p.set_defaults(handler=_run_docking_flow)

    run_p = dock_sub.add_parser("run", formatter_class=_Fmt,
                                help="Docking execution on already-prepared files")
    run_p.add_argument("prepared_receptors_dir", nargs="?", default=_REC_OUT, metavar="RECEPTOR_DIR",
                       help=f"Directory with .maps.fld files  [{_REC_OUT}]")
    run_p.add_argument("prepared_ligands_dir", nargs="?", default=_LIG_OUT, metavar="LIGAND_DIR",
                       help=f"Directory with prepared ligands  [{_LIG_OUT}]")
    run_p.add_argument("output_dir", nargs="?", default=_OUT, metavar="OUTPUT_DIR",
                       help=f"Base output directory  [{_OUT}]")
    run_p.add_argument("--workers", "-w", type=int, default=1, metavar="N",
                       help="Parallel workers  [1]")
    run_p.add_argument("--autogrid-executable", "--autogrid", dest="autogrid_executable", metavar="EXE")
    run_p.add_argument("--autodock-gpu-executable", "--autodock", dest="autodock_gpu_executable", metavar="EXE")
    run_p.set_defaults(handler=_run_docking_execution)

    ana_p = dock_sub.add_parser("analyze", aliases=["analysis"], formatter_class=_Fmt,
                                help="Analyze DLG results and generate reports")
    ana_p.add_argument("output_dir", help="Base output directory")
    ana_p.add_argument("--pdb-export-limit", type=int, default=10, metavar="N",
                       help="Top candidates to export as PDB  [10]")
    ana_p.add_argument("--max-workers", type=int, default=4, metavar="N",
                       help="Max threads for PDB export  [4]")
    ana_p.set_defaults(handler=_run_docking_analysis)

    # ── dynamic ────────────────────────────────────────────────────────────────
    dyn_desc = (
        f"  {bold_cyan('dynamic')}  — Run GROMACS-based molecular dynamics.\n\n"
        f"  Simulation types:\n"
        f"    {cyan('oprotein')}   Protein only\n"
        f"    {cyan('pligand')}    Protein + small-molecule ligand  (needs {bold('-c')} charge)\n"
        f"    {cyan('ppeptide')}   Protein + peptide\n"
        f"    {cyan('pacid')}      Protein + nucleic acid\n"
        f"    {cyan('pprotein')}   Protein + protein\n"
        f"    {cyan('ppligand')}   Protein + protein + ligand/cofactor  (needs {bold('-c')} charge)"
    )
    parent = _dyn_parent()
    dyn = sub.add_parser("dynamic", help="Molecular dynamics simulations",
                         description=dyn_desc, formatter_class=_Fmt)
    dyn_sub = dyn.add_subparsers(dest="dyn_type", metavar="TYPE")

    for name, help_text, needs_charge in [
        ("oprotein",  "Protein-only simulation",                       False),
        ("pligand",   "Protein + small-molecule ligand",               True),
        ("ppeptide",  "Protein + peptide complex",                     False),
        ("pacid",     "Protein + nucleic acid complex",                False),
        ("pprotein",  "Protein + protein complex",                     False),
        ("ppligand",  "Protein + protein + ligand/cofactor complex",   True),
    ]:
        dp = dyn_sub.add_parser(name, help=help_text, parents=[parent], formatter_class=_Fmt)
        if needs_charge:
            dp.add_argument("-c", "--charge", type=int, required=True, metavar="Q",
                            help="Net charge of the ligand (required)")
        dp.set_defaults(handler=_run_dynamic, dyn_type=name)

    # ── doctor ─────────────────────────────────────────────────────────────────
    doc = sub.add_parser("doctor", formatter_class=_Fmt,
                         help="Check environment and tool prerequisites")
    doc.set_defaults(handler=_run_doctor)

    # ── completion ─────────────────────────────────────────────────────────────
    comp_desc = (
        f"  {bold_cyan('completion')}  — Generate shell tab-completion scripts.\n\n"
        f"  Quick setup:\n"
        f"    bash  →  {cyan('source <(chemlink completion bash)')}\n"
        f"    zsh   →  {cyan('source <(chemlink completion zsh)')}\n"
        f"    auto  →  {cyan('chemlink completion install')}  (appends to your shell rc)"
    )
    comp = sub.add_parser("completion", help="Generate shell tab-completion scripts",
                          description=comp_desc, formatter_class=_Fmt)
    comp.add_argument("shell", choices=["bash", "zsh", "fish", "install"], metavar="SHELL",
                      help="Target shell: bash · zsh · fish · install (auto-detect)")
    comp.set_defaults(handler=_run_completion)

    # ── legacy flat commands (backward compatibility) ──────────────────────────
    _register_legacy(sub)

    return parser


def _register_legacy(sub) -> None:
    """Backward-compatible flat commands, labelled as legacy in help text."""

    def _lp(name: str, hlp: str) -> ArgumentParser:
        return sub.add_parser(name, help=f"{dim('[legacy]')} {hlp}", formatter_class=_Fmt)

    rec = _lp("receptor-preparation", "Prepare receptor PDB files")
    rec.add_argument("input_dir"); rec.add_argument("output_dir")
    rec.add_argument("--mgltools-path", dest="mgltools_path")
    rec.add_argument("--workers", type=int)
    rec.set_defaults(handler=_run_receptor_preparation)

    lig = _lp("ligand-preparation", "Prepare ligand files for docking")
    lig.add_argument("input_dir"); lig.add_argument("output_dir")
    lig.add_argument("--workers", type=int)
    lig.set_defaults(handler=_run_ligand_preparation)

    act = _lp("active-site", "Detect active sites and generate GPF files")
    act.add_argument("receptor_dir"); act.add_argument("ligand_dir"); act.add_argument("output_dir")
    act.add_argument("--mgltools-path", dest="mgltools_path")
    act.add_argument("--fpocket-path", dest="fpocket_path")
    act.add_argument("--workers", type=int)
    act.add_argument("--manual-center", nargs=3, type=float, metavar=("X", "Y", "Z"))
    act.add_argument("--manual-npts", nargs=3, type=int, metavar=("NX", "NY", "NZ"))
    act.set_defaults(handler=_run_active_site)

    exc = _lp("docking-execution", "Run AutoGrid4 and AutoDock-GPU")
    exc.add_argument("prepared_receptors_dir"); exc.add_argument("prepared_ligands_dir")
    exc.add_argument("output_dir")
    exc.add_argument("--autogrid-executable", dest="autogrid_executable")
    exc.add_argument("--autodock-gpu-executable", dest="autodock_gpu_executable")
    exc.add_argument("--workers", type=int)
    exc.set_defaults(handler=_run_docking_execution)

    ana = _lp("docking-analysis", "Analyze docking DLG files")
    ana.add_argument("output_dir")
    ana.add_argument("--pdb-export-limit", type=int, default=10)
    ana.add_argument("--max-workers", type=int, default=4)
    ana.set_defaults(handler=_run_docking_analysis)

    flw = _lp("docking-flow", "Run a contiguous subset of pipeline steps")
    _common_pipeline_args(flw); _exec_args(flw); _step_range_args(flw)
    flw.set_defaults(handler=_run_docking_flow)

    pip = _lp("docking-pipeline", "Run full pipeline")
    _common_pipeline_args(pip); _exec_args(pip)
    pip.add_argument("--full", action="store_true")
    pip.set_defaults(handler=lambda a: _run_docking_pipeline(a, full=a.full))


# ── Entry point ────────────────────────────────────────────────────────────────

def _print_banner() -> None:
    logo = cyan(LOGO) if _TTY else LOGO
    print(logo)
    print(f"  {bold_cyan('ChemLink')}  {dim('v' + VERSION)}  Molecular Simulation Toolkit")
    print(f"  {dim('Docking · Molecular Dynamics · Analysis')}\n")


def main() -> int:
    # Optional argcomplete support — install with: pip install argcomplete
    try:
        import argcomplete  # type: ignore
        _has_argcomplete = True
    except ImportError:
        _has_argcomplete = False

    parser = build_parser()

    if _has_argcomplete:
        argcomplete.autocomplete(parser)

    if len(sys.argv) == 1:
        _print_banner()
        parser.print_help()
        return 0

    if sys.argv[1] in ("-h", "--help"):
        _print_banner()

    args = parser.parse_args()

    if not hasattr(args, "handler"):
        # A group command was given without a subcommand — show its help.
        parser.parse_args([args.command, "--help"])
        return 0

    try:
        return args.handler(args) or 0
    except KeyboardInterrupt:
        sys.stderr.write(f"\n{yellow('Interrupted.')}\n")
        return 130
    except Exception as exc:
        sys.stderr.write(f"\n{bold_red('Error:')} {exc}\n")
        if os.environ.get("CHEMLINK_DEBUG"):
            import traceback
            traceback.print_exc()
        else:
            sys.stderr.write(f"  {dim('Set CHEMLINK_DEBUG=1 for a full traceback.')}\n\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
