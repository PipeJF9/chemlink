"""
network_detector.py
Detects cluster interconnect speed and determines whether multi-node GROMACS
MPI is beneficial for a given system size.

Thresholds (atoms needed per GPU for multi-node to break even):
  1 GbE   → Never (threshold = inf) — communication always dominates
  10 GbE  → 500,000+ atoms
  25 GbE  → 200,000+ atoms
  100 GbE / InfiniBand EDR → 50,000+ atoms
  200 GbE / InfiniBand HDR → 30,000+ atoms
"""
from __future__ import annotations

import os
import re


_SPEED_THRESHOLDS = {
    1:   (float("inf"), "1 GbE interconnect — MPI communication overhead (~0.1ms/step) exceeds GPU compute time (~0.007ms/step) for all practical system sizes"),
    10:  (500_000,      "10 GbE interconnect — multi-node beneficial only for systems with 500,000+ atoms"),
    25:  (200_000,      "25 GbE interconnect — multi-node beneficial only for systems with 200,000+ atoms"),
    100: (50_000,       "100 GbE / InfiniBand EDR — multi-node beneficial for systems with 50,000+ atoms"),
    200: (30_000,       "200 GbE / InfiniBand HDR — multi-node beneficial for systems with 30,000+ atoms"),
}


def get_nic_speed_gbps() -> float:
    skip_prefixes = ("lo", "docker", "veth", "br-", "virbr", "tun", "tap")
    candidate_speeds: list[int] = []

    try:
        net_path = "/sys/class/net"
        for iface in sorted(os.listdir(net_path)):
            if any(iface.startswith(pfx) for pfx in skip_prefixes):
                continue
            speed_file = os.path.join(net_path, iface, "speed")
            try:
                with open(speed_file) as fh:
                    val = int(fh.read().strip())
                if val > 0:
                    candidate_speeds.append(val)
            except (OSError, ValueError):
                continue
    except OSError:
        pass

    if not candidate_speeds:
        return 1.0

    speed_mbps = min(candidate_speeds)
    return speed_mbps / 1000.0


def _nearest_threshold_gbps(speed_gbps: float) -> int:
    known = sorted(_SPEED_THRESHOLDS.keys())
    for s in known:
        if speed_gbps <= s + 0.5:
            return s
    return known[-1]


def get_multinode_recommendation(n_atoms: int, n_nodes: int) -> dict:
    speed_gbps = get_nic_speed_gbps()
    tier = _nearest_threshold_gbps(speed_gbps)
    threshold_atoms, base_reason = _SPEED_THRESHOLDS[tier]

    if n_nodes < 2:
        use_multinode = False
        reason = f"Only {n_nodes} node(s) specified — multi-node requires at least 2 nodes"
    elif tier == 1:
        use_multinode = False
        reason = base_reason
    elif n_atoms >= threshold_atoms:
        use_multinode = True
        reason = f"{base_reason} — system has {n_atoms:,} atoms (threshold: {threshold_atoms:,})"
    else:
        use_multinode = False
        reason = (
            f"{base_reason} — system has only {n_atoms:,} atoms "
            f"(need {threshold_atoms:,}+ for multi-node to be beneficial)"
        )

    return {
        "speed_gbps":      speed_gbps,
        "threshold_atoms": threshold_atoms,
        "use_multinode":   use_multinode,
        "reason":          reason,
    }
