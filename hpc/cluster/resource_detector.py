"""Hardware resource detection — GPUs, RAM, and CPU."""
from __future__ import annotations

import multiprocessing
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class GpuInfo:
    index: int
    name: str
    memory_total_mb: int
    memory_free_mb: int
    driver_version: str = ""

    @property
    def memory_total_gb(self) -> float:
        return round(self.memory_total_mb / 1024, 1)

    @property
    def memory_free_gb(self) -> float:
        return round(self.memory_free_mb / 1024, 1)


@dataclass
class HardwareProfile:
    gpus: List[GpuInfo] = field(default_factory=list)
    ram_total_gb: float = 0.0
    ram_available_gb: float = 0.0
    cpu_cores: int = 0
    cpu_threads: int = 0

    @property
    def gpu_count(self) -> int:
        return len(self.gpus)

    @property
    def has_gpu(self) -> bool:
        return bool(self.gpus)

    @property
    def gpu_indices(self) -> List[int]:
        return [g.index for g in self.gpus]


def _detect_gpus() -> List[GpuInfo]:
    if not shutil.which("nvidia-smi"):
        return []
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,memory.free,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        gpus: List[GpuInfo] = []
        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 5:
                continue
            try:
                gpus.append(GpuInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    memory_total_mb=int(parts[2]),
                    memory_free_mb=int(parts[3]),
                    driver_version=parts[4],
                ))
            except (ValueError, IndexError):
                continue
        return gpus
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return []


def _detect_ram() -> Tuple[float, float]:
    """Return (total_gb, available_gb); falls back to (0.0, 0.0) on failure."""
    try:
        info: dict = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                m = re.match(r"^(\w+):\s+(\d+)", line)
                if m:
                    info[m.group(1)] = int(m.group(2))
        total     = round(info.get("MemTotal",     0) / 1024 / 1024, 1)
        available = round(info.get("MemAvailable", 0) / 1024 / 1024, 1)
        return total, available
    except OSError:
        return 0.0, 0.0


def _detect_cpu() -> Tuple[int, int]:
    """Return (physical_cores, logical_threads)."""
    try:
        threads = len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError, OSError):
        threads = multiprocessing.cpu_count()

    try:
        cores_seen: set = set()
        pkg = core = ""
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("physical id"):
                    pkg = line.split(":")[1].strip()
                elif line.startswith("core id"):
                    core = line.split(":")[1].strip()
                    cores_seen.add(f"{pkg}:{core}")
        physical = len(cores_seen) or threads
    except OSError:
        physical = threads

    return physical, threads


def get_hardware_profile() -> HardwareProfile:
    """Detect and return the current hardware profile (GPU / RAM / CPU)."""
    gpus = _detect_gpus()
    ram_total, ram_avail = _detect_ram()
    cpu_cores, cpu_threads = _detect_cpu()
    return HardwareProfile(
        gpus=gpus,
        ram_total_gb=ram_total,
        ram_available_gb=ram_avail,
        cpu_cores=cpu_cores,
        cpu_threads=cpu_threads,
    )
