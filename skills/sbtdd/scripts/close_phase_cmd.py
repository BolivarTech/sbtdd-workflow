#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd close-phase - atomic TDD phase close (sec.S.5.3).

4-step protocol: 0) drift check, 1) verification, 2) atomic commit, 3) state
update. Refactor close cascades to close-task (sec.S.5.3 paso 3c-d).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import superpowers_dispatch
from drift import detect_drift
from errors import DriftError, PreconditionError
from state_file import SessionState, load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-phase")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--message",
        type=str,
        default=None,
        help="Commit message body (without prefix).",
    )
    p.add_argument(
        "--variant",
        choices=("feat", "fix"),
        default=None,
        help="Applicable to Green phase only.",
    )
    return p


def _preflight(root: Path) -> SessionState:
    """Validate state + plan approval + drift before verification/commit."""
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.plan_approved_at is None:
        raise PreconditionError(
            "plan_approved_at is null - plan not approved; cannot close phase autonomously"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}"
        )
    return state


def _run_verification() -> None:
    """Invoke /verification-before-completion; errors propagate unchanged."""
    superpowers_dispatch.verification_before_completion()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    _run_verification()
    return 0


run = main
