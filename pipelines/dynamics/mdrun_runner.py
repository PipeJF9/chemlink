"""
mdrun_runner.py
Streaming runner for GROMACS mdrun.

Why the old pipe approach didn't work
--------------------------------------
GROMACS is a C program.  When its stderr is attached to a pipe instead of a
terminal, the C runtime switches to *full* (block) buffering.  Python's
``bufsize=1`` only controls the Python-side buffer; it cannot force the child
process to flush.  As a result, output was only visible once the 4-8 kB C
buffer filled — effectively at the very end of the run.

What we do instead
-------------------
Primary source  — GROMACS .log file (nvt.log / npt.log / md.log).
  GROMACS writes this file with explicit fflush() every ``nstlog`` steps,
  so data is available in real time regardless of pipe buffering.
  We tail it in a background thread.

Secondary source — stderr with stdbuf.
  If ``stdbuf`` is installed, we prepend ``stdbuf -oL -eL`` to the command,
  which forces line-buffered stderr.  This gives us GPU-init diagnostics
  before the first nstlog checkpoint.  Falls back gracefully if not present.

Progress display
-----------------
* Step N / total  (from log file Step-Time table, every nstlog steps)
* Live ns/day     (computed from steps done and wall-clock time)
* Live ETA        (from the same ratio)
* Final ns/day    (from GROMACS Performance line at end of .log)
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import List, Optional
import logging

from tqdm import tqdm

# ── Patterns: GROMACS .log file ───────────────────────────────────────────────
_RE_LOG_STEP_HDR = re.compile(r"^\s+Step\s+Time\s*$")
_RE_LOG_STEP_VAL = re.compile(r"^\s+(\d+)\s+[\d.]+\s*$")
_RE_LOG_PERF     = re.compile(r"^\s*Performance:\s+([\d.]+)\s+([\d.]+)")
_RE_LOG_GPU      = re.compile(
    r"(?:GPU info|compute cap\.|Offload|offload|stat:\s*compatible"
    r"|CUDA.*version|update.*GPU|bonded.*GPU|PME.*GPU|nb.*GPU"
    r"|GPU-based offload)", re.I
)
_RE_LOG_NOTE     = re.compile(r"^\s*(?:NOTE|WARNING):", re.I)
_RE_LOG_DISABLED = re.compile(r"disabled|not offload|falling back|skipping", re.I)

# ── Patterns: stderr (early GPU init output, fallback step lines) ─────────────
_RE_STDERR_FATAL = re.compile(r"Fatal error|FATAL ERROR")
_RE_STDERR_GPU   = re.compile(r"(?:Offload|GPU info|compute cap|stat:|CUDA error)", re.I)
_RE_STDERR_NOTE  = re.compile(r"^\s*(?:NOTE|WARNING):", re.I)
_RE_STDERR_STEP  = re.compile(
    r"step\s+(\d+).*?remaining wall clock time:\s*([\d.]+)\s*s", re.I
)

_BAR_FMT = (
    "{desc:<36} {percentage:3.0f}%|{bar}| "
    "step {n_fmt}/{total_fmt} [{elapsed}<{remaining}]  {postfix}"
)

# dt used in all our MDP files (ps)
_DT_PS = 0.002


@dataclass
class MdrunResult:
    ns_per_day:   float     = 0.0
    wall_time_s:  float     = 0.0
    gpu_offloads: List[str] = field(default_factory=list)
    notes:        List[str] = field(default_factory=list)
    disabled:     List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_deffnm(cmd: List[str]) -> str:
    try:
        return cmd[cmd.index("-deffnm") + 1]
    except (ValueError, IndexError):
        return "md"


def _maybe_stdbuf(cmd: List[str]) -> List[str]:
    """Prepend stdbuf -oL -eL when available to force line-buffered stderr."""
    exe = shutil.which("stdbuf")
    return ([exe, "-oL", "-eL"] + cmd) if exe else cmd


def _compute_live_metrics(step: int, total_steps: int, t_start: float, dt_ps: float):
    """Return (ns_per_day, eta_s) from current progress."""
    elapsed = time.monotonic() - t_start
    if step <= 0 or elapsed < 1.0:
        return 0.0, 0.0
    sim_ns   = step * dt_ps / 1000.0
    ns_day   = sim_ns / (elapsed / 86400.0)
    eta_s    = elapsed * (total_steps - step) / step
    return ns_day, eta_s


# ── Public API ────────────────────────────────────────────────────────────────

def run_mdrun_streaming(
    cmd: List[str],
    *,
    work_dir: str,
    phase: str,
    total_steps: int,
    logger: logging.Logger,
    timeout: Optional[int] = None,
) -> MdrunResult:
    """
    Run one GROMACS mdrun attempt with real-time progress from the .log file.

    Raises subprocess.CalledProcessError on non-zero exit.
    """
    result   = MdrunResult()
    deffnm   = _get_deffnm(cmd)
    log_path = os.path.join(work_dir, f"{deffnm}.log")
    t_start  = time.monotonic()

    actual_cmd = _maybe_stdbuf(cmd)
    stdbuf_tag = " [+stdbuf]" if actual_cmd is not cmd and len(actual_cmd) > len(cmd) else ""
    logger.info("[%s] mdrun START%s  cmd: %s", phase, stdbuf_tag, " ".join(cmd))
    logger.info("[%s] tailing log: %s", phase, log_path)

    bar = tqdm(
        total=total_steps,
        desc=f"  └─ {phase}",
        bar_format=_BAR_FMT,
        dynamic_ncols=True,
        leave=False,
        unit="step",
    )

    last_step: int   = 0
    stderr_lines: List[str] = []
    _done = threading.Event()

    # ── Thread A: tail GROMACS .log (primary progress source) ─────────────────
    def _tail_log() -> None:
        nonlocal last_step

        # Wait for GROMACS to create the log file (up to 60 s)
        deadline = time.monotonic() + 60
        while not os.path.exists(log_path):
            if _done.is_set() or time.monotonic() > deadline:
                logger.warning(
                    "[%s] Log file not found after 60 s: %s", phase, log_path
                )
                return
            time.sleep(0.5)

        after_hdr = False
        buf = ""

        with open(log_path, "r", errors="replace") as fh:
            while not _done.is_set():
                chunk = fh.read(4096)
                if not chunk:
                    time.sleep(0.3)
                    continue

                buf += chunk
                lines = buf.split("\n")
                buf = lines[-1]          # keep any incomplete trailing line

                for line in lines[:-1]:
                    # ── GPU / offload lines ────────────────────────────────
                    if _RE_LOG_GPU.search(line):
                        stripped = line.strip()
                        if _RE_LOG_DISABLED.search(line):
                            result.disabled.append(stripped)
                            tqdm.write(f"[GPU DISABLED | {phase}] {stripped}")
                            logger.warning("[%s] %s", phase, stripped)
                        else:
                            result.gpu_offloads.append(stripped)
                            tqdm.write(f"[GPU | {phase}] {stripped}")
                            logger.info("[%s] %s", phase, stripped)
                        continue

                    # ── Notes / warnings ──────────────────────────────────
                    if _RE_LOG_NOTE.match(line):
                        stripped = line.strip()
                        result.notes.append(stripped)
                        tqdm.write(f"[NOTE | {phase}] {stripped}")
                        logger.warning("[%s] %s", phase, stripped)
                        continue

                    # ── Step/Time table header ─────────────────────────────
                    if _RE_LOG_STEP_HDR.match(line):
                        after_hdr = True
                        continue

                    if after_hdr:
                        after_hdr = False
                        m = _RE_LOG_STEP_VAL.match(line)
                        if m:
                            step  = int(m.group(1))
                            delta = max(0, step - last_step)
                            if delta > 0:
                                bar.update(delta)
                                last_step = step
                                ns_day, eta_s = _compute_live_metrics(
                                    step, total_steps, t_start, _DT_PS
                                )
                                bar.set_postfix({
                                    "ns/day": f"{ns_day:.1f}",
                                    "ETA":    f"{int(eta_s)}s",
                                })
                        continue

                    # ── Performance (end of run) ───────────────────────────
                    m = _RE_LOG_PERF.match(line)
                    if m:
                        result.ns_per_day = float(m.group(1))
                        h_per_ns = float(m.group(2))
                        tqdm.write(
                            f"\n[PERF | {phase}]  {result.ns_per_day:.3f} ns/day"
                            f"  ({h_per_ns:.3f} h/ns)"
                        )
                        logger.info(
                            "[%s] Performance: %.3f ns/day  (%.3f h/ns)",
                            phase, result.ns_per_day, h_per_ns,
                        )
                        bar.set_postfix({"ns/day": f"{result.ns_per_day:.2f}"})

    # ── Thread B: stderr (GPU init + fallback steps before first nstlog) ──────
    def _read_stderr(pipe) -> None:
        nonlocal last_step
        for raw in pipe:
            line = raw.rstrip()
            if not line:
                continue
            stderr_lines.append(line)

            if _RE_STDERR_FATAL.search(line):
                tqdm.write(f"[FATAL | {phase}] {line}")
                logger.error("[%s] FATAL: %s", phase, line)
                continue
            if _RE_STDERR_GPU.search(line):
                tqdm.write(f"[GPU | {phase}] {line}")
                logger.info("[%s] %s", phase, line)
                continue
            if _RE_STDERR_NOTE.match(line):
                tqdm.write(f"[NOTE | {phase}] {line}")
                logger.warning("[%s] %s", phase, line)
                continue
            # Fallback: step lines on stderr (only effective when stdbuf is present)
            m = _RE_STDERR_STEP.search(line)
            if m and last_step == 0:
                step  = int(m.group(1))
                eta_s = float(m.group(2))
                delta = max(0, step - last_step)
                bar.update(delta)
                last_step = step
                bar.set_postfix({"ETA": f"{int(eta_s)}s"})

    def _drain(pipe) -> None:
        for _ in pipe:
            pass

    # ── Launch process ────────────────────────────────────────────────────────
    proc = subprocess.Popen(
        actual_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=work_dir,
        bufsize=1,
    )

    t_log    = threading.Thread(target=_tail_log,              daemon=True)
    t_stderr = threading.Thread(target=_read_stderr, args=(proc.stderr,), daemon=True)
    t_stdout = threading.Thread(target=_drain,       args=(proc.stdout,), daemon=True)
    t_log.start()
    t_stderr.start()
    t_stdout.start()

    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        _done.set()
        bar.close()
        raise RuntimeError(f"[{phase}] mdrun timed out after {timeout}s")
    finally:
        _done.set()
        t_stderr.join(timeout=10)
        t_log.join(timeout=8)
        t_stdout.join(timeout=5)
        # Ensure bar reaches 100 % on success
        if proc.returncode == 0:
            remaining = max(0, total_steps - last_step)
            if remaining:
                bar.update(remaining)
        bar.close()

    result.wall_time_s = time.monotonic() - t_start

    if proc.returncode != 0:
        tail = "\n".join(stderr_lines[-40:])
        logger.error(
            "[%s] mdrun FAILED rc=%d  wall=%.1fs\n--- stderr tail ---\n%s\n---",
            phase, proc.returncode, result.wall_time_s, tail,
        )
        raise subprocess.CalledProcessError(
            proc.returncode, actual_cmd, stderr="\n".join(stderr_lines)
        )

    logger.info(
        "[%s] mdrun DONE  wall=%.1fs | ns/day=%.3f | gpu_lines=%d | disabled=%d | notes=%d",
        phase, result.wall_time_s, result.ns_per_day,
        len(result.gpu_offloads), len(result.disabled), len(result.notes),
    )
    if result.disabled:
        logger.warning(
            "[%s] Disabled GPU offloads detected:\n  %s",
            phase, "\n  ".join(result.disabled),
        )
    return result


def run_mdrun_with_fallback(
    cmd_gpu: List[str],
    cmd_cpu: List[str],
    *,
    work_dir: str,
    phase: str,
    total_steps: int,
    logger: logging.Logger,
    use_gpu: bool,
    timeout: Optional[int] = None,
) -> MdrunResult:
    """Run mdrun GPU-first; on CalledProcessError fall back to CPU."""
    first_cmd = cmd_gpu if use_gpu else cmd_cpu
    try:
        return run_mdrun_streaming(
            first_cmd,
            work_dir=work_dir, phase=phase,
            total_steps=total_steps, logger=logger, timeout=timeout,
        )
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        if not use_gpu:
            raise
        logger.warning("[%s] GPU run failed (%s) — retrying on CPU.", phase, exc)
        return run_mdrun_streaming(
            cmd_cpu,
            work_dir=work_dir, phase=phase,
            total_steps=total_steps, logger=logger, timeout=timeout,
        )
