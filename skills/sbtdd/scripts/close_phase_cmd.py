#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd close-phase - atomic TDD phase close (sec.S.5.3).

4-step protocol: 0) drift check, 1) verification, 2) atomic commit, 3) state
update. Refactor close cascades to close-task (sec.S.5.3 paso 3c-d).

Enforces INV-1 (atomic phase close: commit + state file consistent),
INV-2 (no phase mixing in a single commit), INV-12 (precondition
validation), INV-16 (verification emits evidence via
/verification-before-completion), and INV-17 (drift surfaced explicitly).
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import close_task_cmd
import subprocess_utils
import superpowers_dispatch
from commits import create as commit_create
from drift import detect_drift
from errors import DriftError, PreconditionError, ValidationError
from models import COMMIT_PREFIX_MAP
from state_file import SessionState, load as load_state, save as save_state


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


def _run_verification(root: Path) -> None:
    """Invoke /verification-before-completion with ``root`` as the working dir.

    MAGI Loop 2 iter 1 Finding 4: the skill wrapper spawns a subprocess
    that shells out to the stack's test runner (pytest / cargo / ctest).
    Without a ``cwd=`` those tools attempt to discover tests relative to
    wherever ``/sbtdd close-phase`` was invoked from -- typically a
    subdirectory of the project root, which breaks test discovery and
    produces a spurious "no tests collected" result. Passing ``cwd=root``
    makes the working directory match the project root regardless of
    which subdirectory the user invoked the command from.

    Args:
        root: Project root directory (``--project-root``).

    Raises:
        ValidationError: Skill wrapper raised (timeout / non-zero exit).
        QuotaExhaustedError: Anthropic API cap hit during verification.
    """
    superpowers_dispatch.verification_before_completion(cwd=str(root))


def _prefix_for(phase: str, variant: str | None) -> str:
    """Return the sec.M.5 commit prefix for the closing phase."""
    if phase == "red":
        return COMMIT_PREFIX_MAP["red"]
    if phase == "green":
        if variant == "feat":
            return COMMIT_PREFIX_MAP["green_feat"]
        if variant == "fix":
            return COMMIT_PREFIX_MAP["green_fix"]
        raise ValidationError("Green phase requires --variant {feat,fix}")
    if phase == "refactor":
        return COMMIT_PREFIX_MAP["refactor"]
    raise ValidationError(f"cannot close phase='{phase}'")


def _next_phase(phase: str) -> str:
    """Return the phase that comes AFTER the closing one.

    For ``refactor`` the close itself stays in ``refactor`` until
    :mod:`close_task_cmd` advances the task (Task 10 cascade).
    """
    if phase == "red":
        return "green"
    if phase == "green":
        return "refactor"
    if phase == "refactor":
        return "refactor"  # close-task handles the real transition
    raise ValidationError(f"cannot advance from phase='{phase}'")


def _now_iso() -> str:
    """Return UTC ISO 8601 timestamp with a Z suffix (CLAUDE.md sec.2.2)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_head_sha(root: Path) -> str:
    """Return short SHA of HEAD via ``git rev-parse --short``."""
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd close-phase (sec.S.5.3).

    Four-step protocol: preflight (state + drift) -> verification (with
    ``cwd=root`` per MAGI Loop 2 Finding 4) -> atomic commit with the
    sec.M.5 prefix -> state file update. When closing ``refactor`` the
    function cascades into :mod:`close_task_cmd` to mark the task [x]
    in the plan.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    _run_verification(root)
    prefix = _prefix_for(state.current_phase, ns.variant)
    if ns.message is None:
        raise ValidationError("close-phase requires --message")
    commit_create(prefix, ns.message, cwd=str(root))
    new_sha = _current_head_sha(root)
    new_phase = _next_phase(state.current_phase)
    new_state = SessionState(
        plan_path=state.plan_path,
        current_task_id=state.current_task_id,
        current_task_title=state.current_task_title,
        current_phase=new_phase,
        phase_started_at_commit=new_sha,
        last_verification_at=_now_iso(),
        last_verification_result="passed",
        plan_approved_at=state.plan_approved_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    if state.current_phase == "refactor":
        rc = close_task_cmd.main(["--project-root", str(root)])
        if rc != 0:
            sys.stderr.write(
                f"close-task cascade failed with rc={rc}; "
                "refactor commit created but task bookkeeping incomplete. "
                "Re-invoke /sbtdd close-task to recover.\n"
            )
            return rc
    return 0


run = main
