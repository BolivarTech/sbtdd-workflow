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

    Args:
        current_phase: "red" | "green" | "refactor" | "done" from state.
        last_commit_prefix: prefix of HEAD commit, without colon
            (e.g. "test", "feat", "chore", "refactor").
        plan_task_state: "[ ]" or "[x]" for the current task.

    Returns:
        DriftReport if state/git/plan are inconsistent; None otherwise.
    """
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
