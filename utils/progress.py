"""Shared tqdm styling for ChemLink pipelines."""
from __future__ import annotations

from tqdm import tqdm

_FMT_STEP = "{desc:<38} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}]"
_FMT_PIPE = "{desc:<22} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} steps [{elapsed}]"
_FMT_JOB  = (
    "{desc:<24} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} "
    "[{elapsed}<{remaining}, {rate_fmt}]  {postfix}"
)

CTRL_C_HINT = "  Press Ctrl+C at any time to abort.\n"


def step_bar(desc: str, total: int, *, colour: str = "cyan", leave: bool = False) -> tqdm:
    """Short-lived bar for a single step inside a pipeline."""
    return tqdm(
        total=total,
        desc=desc,
        bar_format=_FMT_STEP,
        colour=colour,
        leave=leave,
        dynamic_ncols=True,
    )


def pipeline_bar(total: int, *, desc: str = "  Pipeline") -> tqdm:
    """Outer bar that tracks overall pipeline steps."""
    return tqdm(
        total=total,
        desc=desc,
        bar_format=_FMT_PIPE,
        colour="blue",
        unit="step",
        dynamic_ncols=True,
    )


def job_bar(desc: str, total: int, *, unit: str = "job", colour: str = "cyan") -> tqdm:
    """Bar for a batch of parallel jobs (docking, receptors, …)."""
    return tqdm(
        total=total,
        desc=desc,
        bar_format=_FMT_JOB,
        colour=colour,
        unit=unit,
        leave=True,
        dynamic_ncols=True,
    )
