#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd close-task - mark [x] + chore commit + advance state (sec.S.5.4).

Implements the sec.S.5.4 three-step protocol:
1. Flip all ``- [ ]`` checkboxes in the active task section to ``- [x]``.
2. Create an atomic ``chore: mark task {id} complete`` commit containing
   only the plan edit.
3. Advance ``session-state.json`` to the next open task (fresh red phase)
   or mark the plan ``done`` if this was the last task.

Enforces INV-3 (plan checkboxes monotonic: [x] never unset) and is
subject to INV-12 (every subcomando validates preconditions before
mutating state). The ``chore:`` commit honours INV-5..7 commit discipline
via :mod:`commits`.

v0.2 Feature B (INV-31): before advancing state, the subcommand dispatches
the superpowers spec-reviewer for the closing task unless the
``--skip-spec-review`` escape valve is set. A non-approved result surfaces
as :class:`SpecReviewError` (exit 12) and leaves state untouched.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import _plan_ops
import spec_review_dispatch
import subprocess_utils
from commits import create as commit_create
from drift import detect_drift
from errors import DriftError, PreconditionError, SpecReviewError
from state_file import SessionState, load as load_state, save as save_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-task")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--skip-spec-review",
        action="store_true",
        help="Skip spec-reviewer dispatch (INV-31 escape valve)",
    )
    return p


def _preflight(root: Path) -> SessionState:
    """Validate state + drift before any mutation."""
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


def _current_head_sha(root: Path) -> str:
    """Return short SHA of HEAD via ``git rev-parse --short``."""
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def mark_and_advance(state: SessionState, root: Path) -> SessionState:
    """Close the current task and advance state.

    Public helper (no leading underscore) so ``auto_cmd.py`` can reuse the
    exact same sequence without duplicating logic (addresses iter-2 Finding
    W1). Consumes the plan at ``state.plan_path``, mutates it atomically
    via :func:`os.replace`, creates a ``chore: mark task {id} complete``
    commit, then writes the advanced :class:`SessionState` (next open
    ``[ ]`` task in red phase, or ``done``). Returns the new
    ``SessionState``.

    Preconditions: ``state.current_task_id is not None``; the working tree
    has no pending changes outside of the plan file edit produced here
    (enforced by the caller's drift/preflight checks).

    Args:
        state: Current :class:`SessionState` (must have a non-null
            ``current_task_id`` and ``current_phase='refactor'``).
        root: Project root directory.

    Returns:
        The advanced :class:`SessionState` (either pointing to the next
        open task or marked ``done``).
    """
    if state.current_task_id is None:
        raise PreconditionError("mark_and_advance requires non-null current_task_id")
    plan_path = root / state.plan_path
    plan_text = plan_path.read_text(encoding="utf-8")
    new_plan = _plan_ops.flip_task_checkboxes(plan_text, state.current_task_id)
    if new_plan != plan_text:
        # Only write + stage + commit when the flip actually changed bytes.
        # If the implementer subagent already flipped the checkboxes as
        # part of its phase work, the plan is already at the final state
        # and a chore commit here would fail with "nothing to commit".
        tmp = plan_path.with_suffix(plan_path.suffix + f".tmp.{os.getpid()}")
        tmp.write_text(new_plan, encoding="utf-8")
        os.replace(tmp, plan_path)
        subprocess_utils.run_with_timeout(
            ["git", "add", str(plan_path.relative_to(root))],
            timeout=10,
            cwd=str(root),
        )
        commit_create("chore", f"mark task {state.current_task_id} complete", cwd=str(root))
    # else: plan already reflects task completion; the state advance below
    # still runs so the session bookkeeping moves to the next open task.
    new_sha = _current_head_sha(root)
    next_id, next_title = _plan_ops.next_task(new_plan, state.current_task_id)
    new_state = SessionState(
        plan_path=state.plan_path,
        current_task_id=next_id,
        current_task_title=next_title,
        current_phase="red" if next_id else "done",
        phase_started_at_commit=new_sha,
        last_verification_at=state.last_verification_at,
        last_verification_result=state.last_verification_result,
        plan_approved_at=state.plan_approved_at,
        spec_snapshot_emitted_at=state.spec_snapshot_emitted_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    return new_state


def _run_spec_review(task_id: str, state: SessionState, root: Path) -> None:
    """Dispatch the spec-reviewer and raise on non-approval (INV-31).

    Keeps :func:`main` flat: callers see a single pre-advance gate, not an
    inline reviewer-plus-error-mapping block. Returns ``None`` on approval;
    raises :class:`SpecReviewError` when the reviewer is unconvinced, which
    aborts the subcommand before ``mark_and_advance`` mutates anything.
    """
    result = spec_review_dispatch.dispatch_spec_reviewer(
        task_id=task_id,
        plan_path=root / state.plan_path,
        repo_root=root,
    )
    if not result.approved:
        raise SpecReviewError(
            f"spec-reviewer did not approve task {task_id}",
            task_id=task_id,
            iteration=result.reviewer_iter,
            issues=tuple(i.text for i in result.issues),
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    closed_task_id = state.current_task_id or ""
    if not ns.skip_spec_review:
        _run_spec_review(closed_task_id, state, root)
    new_state = mark_and_advance(state, root)
    next_msg = (
        f"Next: task {new_state.current_task_id}" if new_state.current_task_id else "Plan complete."
    )
    sys.stdout.write(f"Task {closed_task_id} closed. {next_msg}\n")
    return 0


run = main
