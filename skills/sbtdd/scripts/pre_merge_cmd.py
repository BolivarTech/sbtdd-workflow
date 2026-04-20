#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd pre-merge -- Loop 1 + Loop 2 (sec.S.5.6, INV-9/28/29)."""

from __future__ import annotations

import argparse
from pathlib import Path

import superpowers_dispatch
from drift import detect_drift
from errors import DriftError, Loop1DivergentError, PreconditionError
from state_file import SessionState
from state_file import load as load_state

#: Safety valve for Loop 1 (sec.S.5.6, INV-11). Exceeding aborts with exit 7.
_LOOP1_MAX: int = 10


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


def _is_clean_to_go(result: object) -> bool:
    """Return True iff the skill's stdout advertises a ``clean-to-go`` signal.

    Accepts either ``clean-to-go`` (hyphenated) or ``clean to go`` (spaced)
    case-insensitively; the superpowers skill has emitted both forms in
    practice.
    """
    stdout_attr = getattr(result, "stdout", None) if result is not None else None
    out = stdout_attr.lower() if isinstance(stdout_attr, str) else ""
    return "clean-to-go" in out or "clean to go" in out


def _loop1(root: Path) -> None:
    """Run Loop 1 -- ``/requesting-code-review`` until clean-to-go (sec.S.5.6).

    Each iteration invokes ``/requesting-code-review``. If the skill result
    does not advertise ``clean-to-go`` the loop invokes
    ``/receiving-code-review`` to apply fixes (the concrete mini-cycle TDD
    commits are materialised by ``_apply_condition_via_mini_cycle`` in Loop
    2; Loop 1 stays at the skill-invocation level because the
    superpowers contract does not expose individual findings here).

    Args:
        root: Project root directory passed to the skill as ``cwd``.

    Raises:
        Loop1DivergentError: If the loop exhausts :data:`_LOOP1_MAX`
            iterations without reaching ``clean-to-go``.
    """
    for _ in range(1, _LOOP1_MAX + 1):
        result = superpowers_dispatch.requesting_code_review(cwd=str(root))
        if _is_clean_to_go(result):
            return
        superpowers_dispatch.receiving_code_review(cwd=str(root))
    raise Loop1DivergentError(f"Loop 1 did not converge in {_LOOP1_MAX} iterations")


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd pre-merge (Loop 1 wired; Loop 2 added in Task 21)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    _preflight(root)
    _loop1(root)
    return 0


run = main
