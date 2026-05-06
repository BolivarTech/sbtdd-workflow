#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""scripts/cross_check_telemetry.py — aggregate cross-check artifacts.

Standalone tooling (not part of skills/sbtdd/scripts/ runtime path).
Consumes .claude/magi-cross-check/iter{N}-{ts}.json artifacts emitted
by pre_merge_cmd._loop2_with_cross_check (v1.0.0 Feature G) and
produces aggregated metrics (markdown or JSON).

Per spec sec.2.1 v1.0.2 Item A.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IterReport:
    iter: int
    verdict: str
    decisions: dict[str, int]
    agents: dict[str, int]
    severity: dict[str, int]
    diff_truncated: bool
    diff_original_bytes: int


@dataclass(frozen=True)
class TelemetryReport:
    total_iters: int
    decision_distribution: dict[str, int]
    per_iter: list[IterReport]
    agreement_rate: float
    truncation_rate: float


def _parse_iter(payload: dict[str, Any]) -> IterReport:
    decisions: dict[str, int] = {}
    agents: dict[str, int] = {}
    severity: dict[str, int] = {}
    cross = payload.get("cross_check_decisions", [])
    for d in cross:
        decisions[d["decision"]] = decisions.get(d["decision"], 0) + 1
        agents[d.get("agent", "?")] = agents.get(d.get("agent", "?"), 0) + 1
        sev = d.get("severity", "?")
        severity[sev] = severity.get(sev, 0) + 1
    return IterReport(
        iter=int(payload["iter"]),
        verdict=str(payload.get("magi_verdict", "")),
        decisions=decisions,
        agents=agents,
        severity=severity,
        diff_truncated=bool(payload.get("diff_truncated", False)),
        diff_original_bytes=int(payload.get("diff_original_bytes", 0)),
    )


def aggregate(
    root: Path,
    cycle_pattern: str = "iter*-*.json",
) -> TelemetryReport:
    """Aggregate cross-check artifacts under root.

    Args:
        root: Directory containing iter{N}-{ts}.json artifacts.
        cycle_pattern: Glob pattern matching v1.0.0 Feature G output.

    Returns:
        TelemetryReport. Empty dir returns total_iters=0 without error.

    Raises:
        FileNotFoundError: root does not exist (guidance-rich message).
    """
    if not root.exists():
        raise FileNotFoundError(
            f"Cross-check artifacts root not found: {root}\n"
            "Expected `.claude/magi-cross-check/` from v1.0.0 Feature G."
        )
    iters: list[IterReport] = []
    for path in sorted(root.glob(cycle_pattern)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[cross_check_telemetry] skip malformed {path}: {exc}\n")
            continue
        try:
            iters.append(_parse_iter(payload))
        except (KeyError, ValueError, TypeError) as exc:
            sys.stderr.write(f"[cross_check_telemetry] skip malformed {path}: {exc}\n")
            continue
    iters.sort(key=lambda i: i.iter)

    decision_dist: dict[str, int] = {}
    truncated_count = 0
    severity_match = 0
    severity_total = 0
    for ir in iters:
        for k, v in ir.decisions.items():
            decision_dist[k] = decision_dist.get(k, 0) + v
        if ir.diff_truncated:
            truncated_count += 1
        for k, v in ir.decisions.items():
            severity_total += v
            if k == "KEEP":
                severity_match += v

    agreement = severity_match / severity_total if severity_total else 0.0
    truncation = truncated_count / len(iters) if iters else 0.0

    return TelemetryReport(
        total_iters=len(iters),
        decision_distribution=decision_dist,
        per_iter=iters,
        agreement_rate=agreement,
        truncation_rate=truncation,
    )
