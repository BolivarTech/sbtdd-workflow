#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd close-task - mark [x] + chore commit + advance state (sec.S.5.4)."""

from __future__ import annotations

import argparse
from pathlib import Path

from drift import detect_drift
from errors import DriftError, PreconditionError
from state_file import SessionState, load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-task")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def _preflight(root: Path) -> SessionState:
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "refactor":
        raise PreconditionError(
            f"close-task requires current_phase='refactor', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value} "
            f"({drift_report.reason})"
        )
    return state


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    return 0


run = main
