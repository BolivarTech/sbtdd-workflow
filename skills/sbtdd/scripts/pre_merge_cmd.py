#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd pre-merge -- Loop 1 + Loop 2 (sec.S.5.6, INV-9/28/29)."""

from __future__ import annotations

import argparse
from pathlib import Path

from drift import detect_drift
from errors import DriftError, PreconditionError
from state_file import SessionState
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``sbtdd pre-merge``."""
    p = argparse.ArgumentParser(prog="sbtdd pre-merge")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--magi-threshold",
        type=str,
        default=None,
        help="Override magi_threshold (ELEVATE only).",
    )
    return p


def _preflight(root: Path) -> SessionState:
    """Verify preconditions for /sbtdd pre-merge.

    Preconditions (sec.S.5.6):
      - ``.claude/session-state.json`` exists.
      - ``current_phase`` is exactly ``done``.
      - No drift between state file, git HEAD, and plan.

    Args:
        root: Project root directory.

    Returns:
        The loaded :class:`SessionState`.

    Raises:
        PreconditionError: Missing state file or current_phase != done.
        DriftError: Drift between state / git HEAD / plan detected.
    """
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "done":
        raise PreconditionError(
            f"pre-merge requires current_phase='done', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}"
        )
    return state


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd pre-merge (scaffold, preconditions only)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    return 0


run = main
