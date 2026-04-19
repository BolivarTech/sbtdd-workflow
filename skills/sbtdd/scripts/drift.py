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

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True)
class DriftReport:
    """Three-way discrepancy between state, git, and plan."""

    state_value: str
    git_value: str
    plan_value: str
    reason: str


#: TDD phase ordering for phase-inversion drift detection.
_PHASE_ORDER: tuple[str, ...] = ("red", "green", "refactor")

#: Map of phase -> set of close-commit prefixes that the close of that phase emits.
_PHASE_CLOSE_PREFIXES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "red": ("test",),
        "green": ("feat", "fix"),
        "refactor": ("refactor",),
    }
)


def _evaluate_drift(
    current_phase: str,
    last_commit_prefix: str,
    plan_task_state: str,
) -> DriftReport | None:
    """Pure drift detector -- no I/O, testable in isolation.

    Flags two kinds of drift per sec.S.9.2:
    - **Close-without-advance:** HEAD commit is the close-prefix of
      `current_phase` but state file still points to that phase
      (close ran, state didn't update).
    - **Phase-ordering inversion:** HEAD commit is the close-prefix of a
      phase AFTER `current_phase` in the ordering (Scenario 4 canonical:
      phase=green + HEAD=refactor:).

    Note on `chore:` commits: `chore` is NOT a close-prefix of any TDD
    phase - it is emitted ONLY by task-close bookkeeping (sec.M.5 row
    4). A `chore:` at HEAD with `state=red` + `plan=[ ]` therefore
    describes the consistent post-task-close state where the NEW task's
    red phase has started fresh (state advanced via close-task, no
    subsequent fix has landed yet). See
    `test_detect_drift_consistent_returns_none` for this canonical
    consistent case.

    Args:
        current_phase: "red" | "green" | "refactor" | "done" from state.
        last_commit_prefix: prefix of HEAD commit, without colon
            (e.g. "test", "feat", "chore", "refactor").
        plan_task_state: "[ ]" or "[x]" for the current task.

    Returns:
        DriftReport if state/git/plan are inconsistent; None otherwise.
    """
    if current_phase == "done" and plan_task_state == "[ ]":
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                "state is done but plan still has open tasks [ ] -- "
                "task-advance bug left plan/state inconsistent; plan "
                "completion requires all tasks marked [x] first "
                "(sec.S.9.2, MAGI Loop 2 Finding 3)"
            ),
        )
    if current_phase != "done" and plan_task_state == "[x]":
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                f"state points to an active task (phase={current_phase}) "
                f"but plan already shows [x] -- task completed without "
                f"state advance (INV-3)"
            ),
        )
    if current_phase == "done":
        return None  # terminal phase -- all close commits are expected behind it

    conflicting: tuple[str, ...] = ()
    if current_phase in _PHASE_ORDER:
        current_idx = _PHASE_ORDER.index(current_phase)
        for p in _PHASE_ORDER[current_idx:]:
            conflicting += _PHASE_CLOSE_PREFIXES.get(p, ())

    if last_commit_prefix in conflicting:
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                f"state_file phase={current_phase} but HEAD commit prefix="
                f"{last_commit_prefix}: indicates close of "
                f"{_close_prefix_owner(last_commit_prefix)} phase already landed; "
                "state file was not advanced"
            ),
        )
    return None


def _close_prefix_owner(prefix: str) -> str:
    """Return the phase name that emits `prefix` as its close-commit."""
    for phase, prefixes in _PHASE_CLOSE_PREFIXES.items():
        if prefix in prefixes:
            return phase
    return "unknown"


def detect_drift(
    state_file_path: Path,
    plan_path: Path,
    repo_root: Path,
) -> DriftReport | None:
    """Read state, git HEAD, and plan; evaluate drift.

    Matches the signature in spec-behavior.md sec.4.2 Escenario 4. Reads
    the three canonical sources then delegates to the pure `_evaluate_drift`.

    Args:
        state_file_path: Path to `.claude/session-state.json`.
        plan_path: Path to `planning/claude-plan-tdd.md`.
        repo_root: Git repository root (for `git log -1 --format=%s`).

    Returns:
        DriftReport if state/git/plan are inconsistent; None otherwise.
    """
    data = json.loads(state_file_path.read_text(encoding="utf-8"))
    current_phase = data["current_phase"]
    current_task_id = data.get("current_task_id")

    # Parse last commit prefix from git log HEAD
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    subject = result.stdout.strip()
    match = re.match(r"^([a-z]+):", subject)
    last_commit_prefix = match.group(1) if match else ""

    # Parse plan checkbox for the active task
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    plan_task_state = (
        _extract_task_checkbox(plan_text, current_task_id) if current_task_id else "[ ]"
    )

    return _evaluate_drift(current_phase, last_commit_prefix, plan_task_state)


def _extract_task_checkbox(plan_text: str, task_id: str) -> str:
    """Extract the checkbox state of the task matching `### Task <id>:`."""
    task_header = re.compile(rf"^### Task {re.escape(task_id)}:", re.MULTILINE)
    match = task_header.search(plan_text)
    if not match:
        return "[ ]"
    # Find the next `- [x]` or `- [ ]` in the task block (simplest heuristic:
    # return [x] only if ALL checkboxes in the task section are [x]).
    section_end = task_header.search(plan_text, match.end())
    end_pos = section_end.start() if section_end else len(plan_text)
    section = plan_text[match.end() : end_pos]
    if "- [ ]" in section:
        return "[ ]"
    if "- [x]" in section:
        return "[x]"
    return "[ ]"
