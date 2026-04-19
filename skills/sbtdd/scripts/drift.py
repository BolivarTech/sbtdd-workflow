#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Drift detection between state file, git HEAD, and plan (sec.S.9.2).

Each mutating subcommand invokes detect_drift() at entry; non-None
result aborts with exit 3 (DRIFT_DETECTED). Silent reconciliation is
forbidden by design - hiding drift hides protocol bugs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftReport:
    """Three-way discrepancy between state, git, and plan."""

    state_value: str
    git_value: str
    plan_value: str
    reason: str
