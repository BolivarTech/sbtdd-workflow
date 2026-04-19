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
from typing import Any

from errors import StateFileError


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


_REQUIRED_FIELDS: tuple[str, ...] = (
    "plan_path",
    "current_task_id",
    "current_task_title",
    "current_phase",
    "phase_started_at_commit",
    "last_verification_at",
    "last_verification_result",
    "plan_approved_at",
)
_VALID_PHASES: frozenset[str] = frozenset({"red", "green", "refactor", "done"})
_VALID_VERIFICATION_RESULTS: frozenset[str] = frozenset({"passed", "failed"})


def validate_schema(data: dict[str, Any]) -> None:
    """Validate session-state.json payload against sec.S.9.1 schema.

    Args:
        data: Parsed JSON as a dict.

    Raises:
        StateFileError: If any required field is missing, or any field
        violates its type/enum constraint.
    """
    for field in _REQUIRED_FIELDS:
        if field not in data:
            raise StateFileError(f"missing required field: {field}")
    if data["current_phase"] not in _VALID_PHASES:
        raise StateFileError(
            f"current_phase='{data['current_phase']}' not in {sorted(_VALID_PHASES)}"
        )
    verif = data["last_verification_result"]
    if verif is not None and verif not in _VALID_VERIFICATION_RESULTS:
        raise StateFileError(
            f"last_verification_result='{verif}' not in "
            f"{sorted(_VALID_VERIFICATION_RESULTS)} or null"
        )
