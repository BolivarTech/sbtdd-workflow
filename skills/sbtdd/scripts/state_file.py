#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""session-state.json schema + load/save/validate (sec.S.9.1).

SessionState is frozen — mutation requires save() with a new instance.
load() validates JSON + schema and raises StateFileError on any issue.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionState:
    """Runtime state of active TDD cycle (sec.S.9.1 schema)."""

    plan_path: str
    current_task_id: str | None
    current_task_title: str | None
    current_phase: str  # Literal["red","green","refactor","done"] enforced in validate
    phase_started_at_commit: str
    last_verification_at: str | None
    last_verification_result: str | None  # Literal["passed","failed", None]
    plan_approved_at: str | None
