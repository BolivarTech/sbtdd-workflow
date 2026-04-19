#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""session-state.json schema + load/save/validate (sec.S.9.1).

SessionState is frozen — mutation requires save() with a new instance.
load() validates JSON + schema and raises StateFileError on any issue.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
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


# ISO 8601 strict with timezone — `YYYY-MM-DDTHH:MM:SS[.ffffff](Z | +HH:MM | -HH:MM)`.
# Timezone suffix is MANDATORY (Z or +HH:MM / -HH:MM) — per CLAUDE.md sec.2.2 the
# project convention is UTC timestamps with explicit `Z`. Subcommands MUST call
# `datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")` or equivalent;
# the naive `datetime.now().isoformat()` omits the timezone and will be rejected
# here. Per MAGI Checkpoint 2 iter 2 (caspar): explicit contract documented.
_ISO_8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def _validate_iso8601(field_name: str, value: object) -> None:
    """Validate that value is None or a well-formed ISO 8601 string."""
    if value is None:
        return
    if not isinstance(value, str) or not _ISO_8601_RE.match(value):
        raise StateFileError(f"{field_name} must be null or ISO 8601 string, got {value!r}")


def load(path: Path | str) -> SessionState:
    """Read and validate .claude/session-state.json.

    Args:
        path: Path to the state file.

    Returns:
        SessionState constructed from the file contents.

    Raises:
        StateFileError: If the file is missing, malformed JSON, fails
        schema validation (including ISO 8601 checks on timestamp
        fields), or if field types are incompatible with SessionState.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise StateFileError(f"state file not found: {p}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateFileError(f"malformed JSON in {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise StateFileError(f"top-level JSON must be object, got {type(data).__name__}")
    validate_schema(data)

    # Per MAGI Checkpoint 2 iter 1 — caspar finding: validate timestamp ISO format
    _validate_iso8601("plan_approved_at", data.get("plan_approved_at"))
    _validate_iso8601("last_verification_at", data.get("last_verification_at"))

    # Per MAGI Checkpoint 2 iter 1 — caspar finding: wrap TypeError (wrong field types
    # or extra fields) as StateFileError so callers see a uniform exception.
    try:
        return SessionState(**data)
    except TypeError as exc:
        raise StateFileError(f"state file schema mismatch: {exc}") from exc
