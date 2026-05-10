#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Drift detection between state file, git HEAD, and plan (sec.S.9.2).

Each mutating subcommand invokes detect_drift() at entry; non-None
result aborts with exit 3 (DRIFT_DETECTED). Silent reconciliation is
forbidden by design - hiding drift hides protocol bugs.

All git invocations go through :mod:`subprocess_utils` so the wrapper's
timeout + Windows kill-tree discipline (sec.S.8.6 / NF5) applies
uniformly across the codebase.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

import subprocess_utils


@dataclass(frozen=True)
class DriftReport:
    """Three-way discrepancy between state, git, and plan."""

    state_value: str
    git_value: str
    plan_value: str
    reason: str


#: TDD phase ordering for phase-inversion drift detection.
_PHASE_ORDER: tuple[str, ...] = ("red", "green", "refactor")

#: Generic task-header pattern for section-boundary detection (matches any
#: ``### Task <id>:``, used to locate the NEXT task after a specific match).
_ANY_TASK_HEADER: re.Pattern[str] = re.compile(r"^### Task \S+?:", re.MULTILINE)

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

    Flags four kinds of drift per sec.S.9.2:
    - **Close-without-advance:** HEAD commit is the close-prefix of
      `current_phase` but state file still points to that phase
      (close ran, state didn't update).
    - **Phase-ordering inversion:** HEAD commit is the close-prefix of a
      phase AFTER `current_phase` in the ordering (Scenario 4 canonical:
      phase=green + HEAD=refactor:).
    - **Plan-advance-without-state:** state points to an active task
      (phase != done) but plan already shows [x] (INV-3 violation).
    - **Plan-done-with-open-tasks:** state=done but plan still has [ ]
      (task-advance bug left plan/state inconsistent; MAGI Loop 2
      Finding 3).

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

    # Parse last commit prefix from git log HEAD; route through
    # subprocess_utils for NF5 consistency (timeout + Windows kill-tree,
    # MAGI Loop 2 Finding 8).
    result = subprocess_utils.run_with_timeout(
        ["git", "log", "-1", "--format=%s"],
        timeout=10,
        cwd=str(repo_root),
    )
    subject = result.stdout.strip()
    match = re.match(r"^([a-z]+):", subject)
    last_commit_prefix = match.group(1) if match else ""

    # Parse plan checkbox for the active task.
    #
    # Fallback when current_task_id is None (terminal ``done`` state):
    # inspect the plan directly to determine whether every task section
    # has zero remaining ``- [ ]``. The previous hard-coded ``"[ ]"``
    # fallback produced a false-positive drift when:
    #   state.current_phase == "done"
    #   state.current_task_id is None (set by close_task_cmd at plan end)
    #   plan is actually fully flipped (all 28 chores landed)
    #   last HEAD commit is a post-plan infrastructure fix (prefix=fix/chore)
    # Observed 2026-04-24 after v0.2 auto task-loop completed + two
    # infra-fix commits landed on top. ``_plan_all_tasks_complete`` walks
    # every ``### Task <id>:`` section and returns ``"[x]"`` iff every
    # section is fully flipped.
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    if current_task_id:
        plan_task_state = _all_task_steps_complete(plan_text, current_task_id)
    else:
        plan_task_state = _plan_all_tasks_complete(plan_text)

    return _evaluate_drift(current_phase, last_commit_prefix, plan_task_state)


def _all_task_steps_complete(plan_text: str, task_id: str) -> str:
    """Return "[x]" if every step in the task section is checked, else "[ ]".

    Heuristic (renamed from ``_extract_task_checkbox`` per MAGI Loop 2
    Finding 4 for honesty): plan files written by ``/writing-plans``
    decompose each task into multiple ``- [ ]`` step checkboxes. The
    plan is not expected to contain a single task-level checkbox; the
    close-task subcommand flips all step checkboxes to ``- [x]`` when
    the task's refactor phase closes. This function therefore returns
    ``"[x]"`` only when ALL step checkboxes in the task section have
    been flipped -- i.e. the whole task is structurally complete.

    Args:
        plan_text: Full text of planning/claude-plan-tdd.md.
        task_id: Task identifier matching ``### Task <id>:``.

    Returns:
        "[x]" if all step checkboxes in the task section are checked;
        "[ ]" otherwise (including the task-not-found case -- conservative
        default to avoid false "task complete" reports).
    """
    task_header = re.compile(rf"^### Task {re.escape(task_id)}:", re.MULTILINE)
    match = task_header.search(plan_text)
    if not match:
        return "[ ]"
    # Use a generic next-task-header pattern to find the section boundary;
    # the specific task_header regex would only re-match the SAME task id.
    section_end = _ANY_TASK_HEADER.search(plan_text, match.end())
    end_pos = section_end.start() if section_end else len(plan_text)
    section = plan_text[match.end() : end_pos]
    if "- [ ]" in section:
        return "[ ]"
    if "- [x]" in section:
        return "[x]"
    return "[ ]"


#: v1.0.7 B5: line-anchored open-checkbox regex. Matches ``- [ ]`` at line
#: start (with optional leading whitespace for indented bullets) so plan
#: text containing ``- [ ]`` inside code-block string literals doesn't
#: false-positive the drift detector.
_OPEN_CHECKBOX_LINE_RE = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)


def _plan_all_tasks_complete(plan_text: str) -> str:
    """Return ``"[x]"`` iff every ``### Task <id>:`` section is fully flipped.

    Walks every task header in the plan and checks that the text between
    it and the next task header contains NO line-anchored ``- [ ]``
    markers. Used by :func:`detect_drift` when the state file has
    ``current_task_id=None`` (terminal ``done`` state) to distinguish
    between:

    * ``state=done, all chores landed`` -> every section ``[x]`` -> ``"[x]"``
      -> no drift (terminal).
    * ``state=done, some task advance skipped`` -> at least one section
      still has ``- [ ]`` -> ``"[ ]"`` -> drift reported (the
      ``state-done-plan-open`` branch of ``_evaluate_drift``).

    When the plan has no ``### Task`` headers at all (malformed or
    empty), return ``"[x]"`` to avoid false-positive drift; the check is
    conservative in the other direction (phase=done with open-task
    evidence is real drift, but phase=done with a planless repo is not a
    useful signal).

    v1.0.7 B5 fix: line-anchored multiline regex ``^[ \\t]*- \\[ \\]``
    replaces the previous unanchored substring check ``"- [ ]" in section``.
    The substring check produced false-positives on plans containing
    Python test fixture string literals like ``"- [ ] Step 1\\n"`` inside
    code blocks (v1.0.6 dogfood empirical finding). The regex requires
    the ``- [ ]`` marker to start at line beginning (with optional
    leading whitespace for indented bullets), excluding code-block
    fixtures whose ``- [ ]`` substrings sit inside string literal
    contexts.
    """
    headers = list(_ANY_TASK_HEADER.finditer(plan_text))
    if not headers:
        return "[x]"
    for i, match in enumerate(headers):
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(plan_text)
        if _OPEN_CHECKBOX_LINE_RE.search(plan_text[start:end]):
            return "[ ]"
    return "[x]"
