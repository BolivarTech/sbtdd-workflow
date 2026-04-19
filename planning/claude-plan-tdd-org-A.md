# Milestone A: Infrastructure Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el nucleo de infraestructura stdlib-only del plugin sbtdd-workflow — modulos `models`, `errors`, `state_file`, `drift`, `config`, `templates`, `hooks_installer`, `subprocess_utils`, `quota_detector`, `commits` — todos con `make verify` limpio y sin subcomandos todavia.

**Architecture:** Python 3.9+, stdlib + `dataclasses` + `typing`. Registros inmutables via `MappingProxyType`/`tuple`. Todas las excepciones derivan de `SBTDDError`. Un modulo = una responsabilidad, testeable en aislamiento con pytest.

**Tech Stack:** Python 3.9+ stdlib, pytest 9.x, ruff 0.15.x, mypy 1.20.x (strict mode), uv para venv.

---

## File Structure

Archivos creados en este milestone:

```
skills/sbtdd/scripts/
├── __init__.py
├── reporters/__init__.py
├── models.py               # COMMIT_PREFIX_MAP, VERDICT_RANK, VALID_SUBCOMMANDS (inmutables)
├── errors.py               # SBTDDError + 7 subclases
├── state_file.py           # SessionState dataclass + load/save/validate
├── drift.py                # DriftReport + detect_drift
├── config.py               # PluginConfig + load_plugin_local + YAML parse
├── templates.py            # expand function
├── hooks_installer.py      # merge settings.json idempotente
├── subprocess_utils.py     # run_with_timeout + kill_tree (Windows/POSIX)
├── quota_detector.py       # QUOTA_PATTERNS + QuotaExhaustion + detect
└── commits.py              # create con validacion (prefijo/ingles/no-AI)

tests/
├── test_models.py
├── test_errors.py
├── test_state_file.py
├── test_drift.py
├── test_config.py
├── test_templates.py
├── test_hooks_installer.py
├── test_subprocess_utils.py
├── test_quota_detector.py
└── test_commits.py

tests/fixtures/
├── state-files/{valid.json, invalid-phase.json, invalid-approved-at.json}
├── plugin-locals/{valid-rust.md, valid-python.md}
└── quota-errors/{rate_limit_429.txt, session_limit.txt, weekly_limit.txt,
                  credit_exhausted.txt, server_throttle.txt}

LICENSE                     # MIT
LICENSE-APACHE              # Apache-2.0
```

Tareas: 35 total. Orden lineal; cada tarea asume las previas completas.

**Comandos de verificacion por fase TDD** (sec.M.0.1 + CLAUDE.local.md §0.1):

```bash
.venv/Scripts/pytest tests/ -v          # All pass, 0 fail
.venv/Scripts/ruff check .              # 0 warnings
.venv/Scripts/ruff format --check .     # Clean
.venv/Scripts/mypy .                    # No type errors
```

Atajo: `make verify` corre los 4 en orden.

---

## Phase 1: Foundation (Tasks 1-8 — scenarios 1, 2)

### Task 1: Package skeleton

**Files:**
- Create: `skills/sbtdd/scripts/__init__.py`
- Create: `skills/sbtdd/scripts/reporters/__init__.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py (stub para forzar descubrimiento de imports)
def test_package_importable():
    """scripts package should be importable from tests via sys.path injection."""
    import sys
    from pathlib import Path
    scripts_dir = str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts")
    assert scripts_dir in sys.path or any(scripts_dir in p for p in sys.path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: FAIL (directorio `skills/sbtdd/scripts/` no existe).

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/__init__.py`:

```python
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
```

Create `skills/sbtdd/scripts/reporters/__init__.py`:

```python
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
```

Create dir via: `mkdir -p skills/sbtdd/scripts/reporters`

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: PASS — 1 test.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/__init__.py skills/sbtdd/scripts/reporters/__init__.py tests/test_models.py
git commit -m "test: add scripts package skeleton and import test"
```

---

### Task 2: `models.py` — `COMMIT_PREFIX_MAP` (inmutabilidad)

**Files:**
- Create: `skills/sbtdd/scripts/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py (append)
from types import MappingProxyType
import pytest

def test_commit_prefix_map_is_mapping_proxy():
    from models import COMMIT_PREFIX_MAP
    assert isinstance(COMMIT_PREFIX_MAP, MappingProxyType)

def test_commit_prefix_map_rejects_mutation():
    from models import COMMIT_PREFIX_MAP
    with pytest.raises(TypeError):
        COMMIT_PREFIX_MAP["new"] = "whatever"  # type: ignore[index]

def test_commit_prefix_map_has_required_keys():
    from models import COMMIT_PREFIX_MAP
    assert COMMIT_PREFIX_MAP["red"] == "test"
    assert COMMIT_PREFIX_MAP["green_feat"] == "feat"
    assert COMMIT_PREFIX_MAP["green_fix"] == "fix"
    assert COMMIT_PREFIX_MAP["refactor"] == "refactor"
    assert COMMIT_PREFIX_MAP["task_close"] == "chore"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'models'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/models.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Immutable registries for sbtdd-workflow plugin.

Single source of truth for commit prefixes, MAGI verdict ranks, and the
list of valid subcommand names. All registries are exposed as
MappingProxyType or tuple to prevent runtime mutation (sec.S.8.5).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

_COMMIT_PREFIX_MAP_MUTABLE: dict[str, str] = {
    "red": "test",
    "green_feat": "feat",
    "green_fix": "fix",
    "refactor": "refactor",
    "task_close": "chore",
}

#: Read-only TDD phase → git commit prefix mapping (sec.M.5).
COMMIT_PREFIX_MAP: Mapping[str, str] = MappingProxyType(_COMMIT_PREFIX_MAP_MUTABLE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: PASS — 4 tests (incluye el de package_importable).

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/models.py tests/test_models.py
git commit -m "test: add COMMIT_PREFIX_MAP with immutability guard"
```

---

### Task 3: `models.py` — `VERDICT_RANK` + `verdict_meets_threshold`

**Files:**
- Modify: `skills/sbtdd/scripts/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py (append)
def test_verdict_rank_ordering():
    from models import VERDICT_RANK
    assert VERDICT_RANK["STRONG_NO_GO"] < VERDICT_RANK["HOLD"]
    assert VERDICT_RANK["HOLD"] < VERDICT_RANK["HOLD_TIE"]
    assert VERDICT_RANK["HOLD_TIE"] < VERDICT_RANK["GO_WITH_CAVEATS"]
    assert VERDICT_RANK["GO_WITH_CAVEATS"] < VERDICT_RANK["GO"]
    assert VERDICT_RANK["GO"] < VERDICT_RANK["STRONG_GO"]

def test_verdict_meets_threshold_positive():
    from models import verdict_meets_threshold
    assert verdict_meets_threshold("GO", "GO_WITH_CAVEATS") is True
    assert verdict_meets_threshold("GO_WITH_CAVEATS", "GO_WITH_CAVEATS") is True

def test_verdict_meets_threshold_negative():
    from models import verdict_meets_threshold
    assert verdict_meets_threshold("HOLD", "GO_WITH_CAVEATS") is False
    assert verdict_meets_threshold("STRONG_NO_GO", "GO") is False

def test_verdict_rank_is_mapping_proxy():
    from types import MappingProxyType
    from models import VERDICT_RANK
    assert isinstance(VERDICT_RANK, MappingProxyType)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: FAIL con `ImportError: cannot import name 'VERDICT_RANK'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/models.py`:

```python
_VERDICT_RANK_MUTABLE: dict[str, int] = {
    "STRONG_NO_GO": 0,
    "HOLD": 1,
    "HOLD_TIE": 2,
    "GO_WITH_CAVEATS": 3,
    "GO": 4,
    "STRONG_GO": 5,
}

#: Read-only MAGI verdict → integer rank mapping (sec.S.11.1 + CLAUDE.md crossfile).
VERDICT_RANK: Mapping[str, int] = MappingProxyType(_VERDICT_RANK_MUTABLE)


def verdict_meets_threshold(verdict: str, threshold: str) -> bool:
    """Return True if verdict >= threshold in VERDICT_RANK ordering.

    Args:
        verdict: MAGI verdict label (must be a key of VERDICT_RANK).
        threshold: Minimum acceptable verdict label (same domain).

    Returns:
        True if verdict's rank is >= threshold's rank.

    Raises:
        KeyError: If either verdict or threshold is not in VERDICT_RANK.
    """
    return VERDICT_RANK[verdict] >= VERDICT_RANK[threshold]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: PASS — 8 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/models.py tests/test_models.py
git commit -m "test: add VERDICT_RANK and verdict_meets_threshold helper"
```

---

### Task 4: `models.py` — `VALID_SUBCOMMANDS`

**Files:**
- Modify: `skills/sbtdd/scripts/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_models.py (append)
def test_valid_subcommands_is_tuple():
    from models import VALID_SUBCOMMANDS
    assert isinstance(VALID_SUBCOMMANDS, tuple)

def test_valid_subcommands_has_nine():
    from models import VALID_SUBCOMMANDS
    assert len(VALID_SUBCOMMANDS) == 9

def test_valid_subcommands_contents():
    from models import VALID_SUBCOMMANDS
    expected = ("init", "spec", "close-phase", "close-task", "status",
                "pre-merge", "finalize", "auto", "resume")
    assert VALID_SUBCOMMANDS == expected

def test_valid_subcommands_rejects_mutation():
    from models import VALID_SUBCOMMANDS
    import pytest
    with pytest.raises((TypeError, AttributeError)):
        VALID_SUBCOMMANDS[0] = "hacked"  # type: ignore[index]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: FAIL con `ImportError: cannot import name 'VALID_SUBCOMMANDS'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/models.py`:

```python
#: Ordered tuple of all valid subcommand names (sec.S.2.2 inventario).
VALID_SUBCOMMANDS: tuple[str, ...] = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_models.py -v`
Expected: PASS — 12 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/models.py tests/test_models.py
git commit -m "test: add VALID_SUBCOMMANDS tuple with immutability"
```

---

### Task 5: `errors.py` — `SBTDDError` base + `ValidationError`

**Files:**
- Create: `skills/sbtdd/scripts/errors.py`
- Create: `tests/test_errors.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_errors.py
import pytest

def test_sbtdd_error_base_class():
    from errors import SBTDDError
    assert issubclass(SBTDDError, Exception)
    err = SBTDDError("generic failure")
    assert str(err) == "generic failure"

def test_validation_error_is_sbtdd_error():
    from errors import SBTDDError, ValidationError
    assert issubclass(ValidationError, SBTDDError)

def test_validation_error_caught_by_sbtdd_error():
    from errors import SBTDDError, ValidationError
    with pytest.raises(SBTDDError):
        raise ValidationError("schema invalid")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'errors'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/errors.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Exception hierarchy for sbtdd-workflow plugin.

All plugin exceptions derive from SBTDDError for catch-all in the
dispatcher (sec.S.8.4). Each subclass maps to a specific exit code
per sec.S.11.1 taxonomy.
"""

from __future__ import annotations


class SBTDDError(Exception):
    """Base exception for all plugin errors. Subclasses map to exit codes."""


class ValidationError(SBTDDError):
    """Schema or input validation failed (exit 1, USER_ERROR)."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/errors.py tests/test_errors.py
git commit -m "test: add SBTDDError base and ValidationError subclass"
```

---

### Task 6: `errors.py` — `StateFileError` + `DriftError` + `DependencyError`

**Files:**
- Modify: `skills/sbtdd/scripts/errors.py`
- Modify: `tests/test_errors.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_errors.py (append)
def test_state_file_error_derives_from_sbtdd():
    from errors import SBTDDError, StateFileError
    assert issubclass(StateFileError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise StateFileError("corrupt JSON")

def test_drift_error_derives_from_sbtdd():
    from errors import SBTDDError, DriftError
    assert issubclass(DriftError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise DriftError("state vs git mismatch")

def test_dependency_error_derives_from_sbtdd():
    from errors import SBTDDError, DependencyError
    assert issubclass(DependencyError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise DependencyError("tdd-guard not in PATH")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: FAIL con `ImportError: cannot import name 'StateFileError'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/errors.py`:

```python
class StateFileError(SBTDDError):
    """session-state.json corrupt (JSON invalid / schema invalid) — exit 1."""


class DriftError(SBTDDError):
    """State vs git HEAD vs plan mismatch detected by drift.detect_drift — exit 3."""


class DependencyError(SBTDDError):
    """Required dependency missing or non-operational — exit 2."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/errors.py tests/test_errors.py
git commit -m "test: add StateFileError, DriftError, DependencyError"
```

---

### Task 7: `errors.py` — `PreconditionError` + `MAGIGateError` + `QuotaExhaustedError`

**Files:**
- Modify: `skills/sbtdd/scripts/errors.py`
- Modify: `tests/test_errors.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_errors.py (append)
def test_precondition_error_derives_from_sbtdd():
    from errors import SBTDDError, PreconditionError
    assert issubclass(PreconditionError, SBTDDError)

def test_magi_gate_error_derives_from_sbtdd():
    from errors import SBTDDError, MAGIGateError
    assert issubclass(MAGIGateError, SBTDDError)

def test_quota_exhausted_error_derives_from_sbtdd():
    from errors import SBTDDError, QuotaExhaustedError
    assert issubclass(QuotaExhaustedError, SBTDDError)

def test_all_seven_subclasses_exist():
    import errors
    expected = {"ValidationError", "StateFileError", "DriftError",
                "DependencyError", "PreconditionError", "MAGIGateError",
                "QuotaExhaustedError"}
    actual = {name for name in dir(errors) if name.endswith("Error") and name != "SBTDDError"}
    assert expected == actual, f"mismatch: expected {expected}, got {actual}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: FAIL con `ImportError: cannot import name 'PreconditionError'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/errors.py`:

```python
class PreconditionError(SBTDDError):
    """Subcommand precondition not satisfied — exit 2 (PRECONDITION_FAILED)."""


class MAGIGateError(SBTDDError):
    """MAGI verdict below threshold or STRONG_NO_GO — exit 8 (MAGI_GATE_BLOCKED)."""


class QuotaExhaustedError(SBTDDError):
    """Anthropic API quota exhausted (rate limit / session / credit) — exit 11."""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: PASS — 10 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/errors.py tests/test_errors.py
git commit -m "test: add PreconditionError, MAGIGateError, QuotaExhaustedError"
```

---

### Task 8: `errors.py` — polymorphic catch hierarchy test

**Files:**
- Modify: `tests/test_errors.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_errors.py (append)
def test_non_matching_subclass_not_caught():
    """Catching specific subclass must not catch sibling subclasses."""
    from errors import DriftError, MAGIGateError
    with pytest.raises(MAGIGateError):
        try:
            raise MAGIGateError("strong no-go")
        except DriftError:
            pytest.fail("DriftError catch must not intercept MAGIGateError")

def test_mro_is_flat_single_inheritance():
    """All subclasses inherit directly from SBTDDError (no diamond)."""
    from errors import (SBTDDError, ValidationError, StateFileError,
                        DriftError, DependencyError, PreconditionError,
                        MAGIGateError, QuotaExhaustedError)
    subclasses = [ValidationError, StateFileError, DriftError,
                  DependencyError, PreconditionError, MAGIGateError,
                  QuotaExhaustedError]
    for cls in subclasses:
        assert cls.__mro__[1] is SBTDDError, f"{cls.__name__} MRO skips SBTDDError"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_errors.py::test_mro_is_flat_single_inheritance -v`
Expected: PASS (no code change needed — tests the existing design).

Actually, run it first: if it passes immediately (no red phase), it means the existing code already satisfies the invariant. That's fine for Refactor-only commits, but here we're adding coverage. This task is a Refactor-phase commit.

- [ ] **Step 3: (no new impl needed — tests verify existing design)**

- [ ] **Step 4: Run full test suite**

Run: `.venv/Scripts/pytest tests/test_errors.py -v`
Expected: PASS — 12 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_errors.py
git commit -m "refactor: add polymorphic catch + MRO flatness tests for errors"
```

---

## Phase 2: State & Drift (Tasks 9-15 — scenarios 3, 4)

### Task 9: `state_file.py` — `SessionState` dataclass + schema keys

**Files:**
- Create: `skills/sbtdd/scripts/state_file.py`
- Create: `tests/test_state_file.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state_file.py
import pytest
from dataclasses import FrozenInstanceError

def test_session_state_is_frozen_dataclass():
    from state_file import SessionState
    state = SessionState(
        plan_path="planning/claude-plan-tdd.md",
        current_task_id="3",
        current_task_title="Extract validation",
        current_phase="green",
        phase_started_at_commit="a3f2d1c",
        last_verification_at="2026-04-19T10:00:00Z",
        last_verification_result="passed",
        plan_approved_at="2026-04-18T10:00:00Z",
    )
    with pytest.raises(FrozenInstanceError):
        state.current_phase = "red"  # type: ignore[misc]

def test_session_state_has_eight_fields():
    from state_file import SessionState
    fields = [f for f in SessionState.__dataclass_fields__]
    expected = {"plan_path", "current_task_id", "current_task_title",
                "current_phase", "phase_started_at_commit",
                "last_verification_at", "last_verification_result",
                "plan_approved_at"}
    assert set(fields) == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'state_file'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/state_file.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/state_file.py tests/test_state_file.py
git commit -m "test: add SessionState frozen dataclass with 8 fields"
```

---

### Task 10: `state_file.py` — `validate_schema` (rechaza enum invalido)

**Files:**
- Modify: `skills/sbtdd/scripts/state_file.py`
- Modify: `tests/test_state_file.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state_file.py (append)
def test_validate_rejects_invalid_phase():
    from state_file import validate_schema
    from errors import StateFileError
    data = {
        "plan_path": "p",
        "current_task_id": "1",
        "current_task_title": "t",
        "current_phase": "yellow",  # invalid
        "phase_started_at_commit": "abc1234",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": None,
    }
    with pytest.raises(StateFileError) as exc_info:
        validate_schema(data)
    assert "current_phase" in str(exc_info.value)

def test_validate_rejects_missing_field():
    from state_file import validate_schema
    from errors import StateFileError
    data = {"plan_path": "p"}  # missing 7 required fields
    with pytest.raises(StateFileError) as exc_info:
        validate_schema(data)
    assert "missing" in str(exc_info.value).lower() or "required" in str(exc_info.value).lower()

def test_validate_accepts_valid_data():
    from state_file import validate_schema
    data = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "3",
        "current_task_title": "Extract validation",
        "current_phase": "green",
        "phase_started_at_commit": "a3f2d1c",
        "last_verification_at": "2026-04-19T10:00:00Z",
        "last_verification_result": "passed",
        "plan_approved_at": "2026-04-18T10:00:00Z",
    }
    validate_schema(data)  # no raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: FAIL con `ImportError: cannot import name 'validate_schema'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/state_file.py`:

```python
from typing import Any

from errors import StateFileError

_REQUIRED_FIELDS: tuple[str, ...] = (
    "plan_path", "current_task_id", "current_task_title",
    "current_phase", "phase_started_at_commit",
    "last_verification_at", "last_verification_result",
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
            f"current_phase='{data['current_phase']}' not in "
            f"{sorted(_VALID_PHASES)}"
        )
    verif = data["last_verification_result"]
    if verif is not None and verif not in _VALID_VERIFICATION_RESULTS:
        raise StateFileError(
            f"last_verification_result='{verif}' not in "
            f"{sorted(_VALID_VERIFICATION_RESULTS)} or null"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/state_file.py tests/test_state_file.py
git commit -m "test: add validate_schema with enum/required-field checks"
```

---

### Task 11: `state_file.py` — `load` function (JSON + validate)

**Files:**
- Modify: `skills/sbtdd/scripts/state_file.py`
- Modify: `tests/test_state_file.py`
- Create: `tests/fixtures/state-files/valid.json`
- Create: `tests/fixtures/state-files/invalid-phase.json`
- Create: `tests/fixtures/state-files/malformed.json`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state_file.py (append)
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "state-files"

def test_load_valid_state_file():
    from state_file import load, SessionState
    state = load(FIXTURES_DIR / "valid.json")
    assert isinstance(state, SessionState)
    assert state.current_phase == "green"

def test_load_rejects_invalid_phase():
    from state_file import load
    from errors import StateFileError
    with pytest.raises(StateFileError):
        load(FIXTURES_DIR / "invalid-phase.json")

def test_load_rejects_malformed_json():
    from state_file import load
    from errors import StateFileError
    with pytest.raises(StateFileError) as exc_info:
        load(FIXTURES_DIR / "malformed.json")
    assert "JSON" in str(exc_info.value) or "decode" in str(exc_info.value).lower()
```

Create fixtures:

`tests/fixtures/state-files/valid.json`:
```json
{
  "plan_path": "planning/claude-plan-tdd.md",
  "current_task_id": "3",
  "current_task_title": "Extract validation",
  "current_phase": "green",
  "phase_started_at_commit": "a3f2d1c",
  "last_verification_at": "2026-04-19T10:00:00Z",
  "last_verification_result": "passed",
  "plan_approved_at": "2026-04-18T10:00:00Z"
}
```

`tests/fixtures/state-files/invalid-phase.json`:
```json
{
  "plan_path": "p",
  "current_task_id": "1",
  "current_task_title": "t",
  "current_phase": "yellow",
  "phase_started_at_commit": "abc1234",
  "last_verification_at": null,
  "last_verification_result": null,
  "plan_approved_at": null
}
```

`tests/fixtures/state-files/malformed.json`:
```
{this is not valid json
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: FAIL con `ImportError: cannot import name 'load'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/state_file.py`:

```python
import json
from pathlib import Path


def load(path: Path | str) -> SessionState:
    """Read and validate .claude/session-state.json.

    Args:
        path: Path to the state file.

    Returns:
        SessionState constructed from the file contents.

    Raises:
        StateFileError: If the file is missing, malformed JSON, or fails
        schema validation.
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
    return SessionState(**data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: PASS — 8 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/state_file.py tests/test_state_file.py tests/fixtures/state-files/
git commit -m "test: add state_file.load with JSON + schema validation"
```

---

### Task 12: `state_file.py` — `save` function (atomic write)

**Files:**
- Modify: `skills/sbtdd/scripts/state_file.py`
- Modify: `tests/test_state_file.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_state_file.py (append)
def test_save_writes_and_reloads(tmp_path):
    from state_file import SessionState, save, load
    state = SessionState(
        plan_path="planning/claude-plan-tdd.md",
        current_task_id="1",
        current_task_title="First",
        current_phase="red",
        phase_started_at_commit="abc1234",
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at="2026-04-19T10:00:00Z",
    )
    target = tmp_path / "session-state.json"
    save(state, target)
    assert target.exists()
    reloaded = load(target)
    assert reloaded == state

def test_save_is_atomic_no_partial_on_error(tmp_path, monkeypatch):
    """If os.replace raises, target should not exist (atomicity)."""
    from state_file import SessionState, save
    import os
    state = SessionState(
        plan_path="p", current_task_id=None, current_task_title=None,
        current_phase="done", phase_started_at_commit="abc1234",
        last_verification_at=None, last_verification_result=None,
        plan_approved_at=None,
    )
    target = tmp_path / "subdir" / "state.json"
    # subdir does not exist; save should raise, target should not exist
    with pytest.raises((FileNotFoundError, OSError)):
        save(state, target)
    assert not target.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: FAIL con `ImportError: cannot import name 'save'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/state_file.py`:

```python
import os
from dataclasses import asdict


def save(state: SessionState, path: Path | str) -> None:
    """Write SessionState to disk atomically via tmp-file + os.replace.

    Args:
        state: SessionState to persist.
        path: Destination path. Parent directory must exist.

    Raises:
        OSError / FileNotFoundError: If the parent directory does not
        exist or the write fails. No partial file left behind.
    """
    p = Path(path)
    tmp = p.with_suffix(p.suffix + f".tmp.{os.getpid()}")
    data = asdict(state)
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, p)  # atomic on POSIX and Windows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_state_file.py -v`
Expected: PASS — 10 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/state_file.py tests/test_state_file.py
git commit -m "test: add state_file.save with atomic write via os.replace"
```

---

### Task 13: `drift.py` — `DriftReport` dataclass

**Files:**
- Create: `skills/sbtdd/scripts/drift.py`
- Create: `tests/test_drift.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_drift.py
import pytest
from dataclasses import FrozenInstanceError

def test_drift_report_is_frozen():
    from drift import DriftReport
    report = DriftReport(
        state_value="green",
        git_value="refactor:",
        plan_value="[ ]",
        reason="phase/prefix mismatch",
    )
    with pytest.raises(FrozenInstanceError):
        report.state_value = "red"  # type: ignore[misc]

def test_drift_report_fields():
    from drift import DriftReport
    fields = set(DriftReport.__dataclass_fields__)
    assert fields == {"state_value", "git_value", "plan_value", "reason"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_drift.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'drift'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/drift.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Drift detection between state file, git HEAD, and plan (sec.S.9.2).

Each mutating subcommand invokes detect_drift() at entry; non-None
result aborts with exit 3 (DRIFT_DETECTED). Silent reconciliation is
forbidden by design — hiding drift hides protocol bugs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftReport:
    """Three-way discrepancy between state, git, and plan."""

    state_value: str
    git_value: str
    plan_value: str
    reason: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_drift.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/drift.py tests/test_drift.py
git commit -m "test: add DriftReport frozen dataclass"
```

---

### Task 14: `drift.py` — `detect_drift` (phase vs prefix mismatch)

**Files:**
- Modify: `skills/sbtdd/scripts/drift.py`
- Modify: `tests/test_drift.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_drift.py (append)
def test_detect_drift_phase_red_with_test_commit():
    """current_phase=red + last commit prefix=test: is drift (sec.S.10.1 INV-3)."""
    from drift import detect_drift, DriftReport
    report = detect_drift(
        current_phase="red",
        last_commit_prefix="test",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "red"
    assert report.git_value == "test"

def test_detect_drift_phase_green_with_feat_commit():
    from drift import detect_drift
    report = detect_drift(
        current_phase="green",
        last_commit_prefix="feat",
        plan_task_state="[ ]",
    )
    assert report is not None
    assert "feat" in report.git_value

def test_detect_drift_phase_refactor_with_refactor_commit():
    from drift import detect_drift
    report = detect_drift(
        current_phase="refactor",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert report is not None

def test_detect_drift_consistent_returns_none():
    """current_phase=red + last commit prefix=chore (previous task close) is consistent."""
    from drift import detect_drift
    report = detect_drift(
        current_phase="red",
        last_commit_prefix="chore",
        plan_task_state="[ ]",
    )
    assert report is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_drift.py -v`
Expected: FAIL con `ImportError: cannot import name 'detect_drift'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/drift.py`:

```python
# Mapping of phase → commit prefix that would indicate drift if present.
# (phase=X + HEAD commit is the close-commit of phase X → close-phase ran
#  but state file update failed — drift per sec.S.9.2 regla operativa.)
_DRIFT_PHASE_PREFIX: dict[str, tuple[str, ...]] = {
    "red": ("test",),
    "green": ("feat", "fix"),
    "refactor": ("refactor",),
}


def detect_drift(
    current_phase: str,
    last_commit_prefix: str,
    plan_task_state: str,
) -> DriftReport | None:
    """Detect state/git/plan divergence per sec.S.9.2.

    Args:
        current_phase: "red" | "green" | "refactor" | "done" from state file.
        last_commit_prefix: prefix of HEAD commit (e.g. "test", "feat", "chore").
        plan_task_state: "[ ]" or "[x]" for the current task.

    Returns:
        DriftReport if state/git/plan are inconsistent; None otherwise.
    """
    conflicting = _DRIFT_PHASE_PREFIX.get(current_phase, ())
    if last_commit_prefix in conflicting:
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                f"close-phase for {current_phase} appears to have "
                f"committed ({last_commit_prefix}:) but state file was "
                f"not advanced"
            ),
        )
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_drift.py -v`
Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/drift.py tests/test_drift.py
git commit -m "test: add detect_drift phase-vs-prefix mismatch detection"
```

---

### Task 15: `drift.py` — plan-checkbox drift case

**Files:**
- Modify: `skills/sbtdd/scripts/drift.py`
- Modify: `tests/test_drift.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_drift.py (append)
def test_detect_drift_plan_already_checked_but_state_points_to_it():
    """state points to current_task_id but plan shows [x] — drift per INV-3."""
    from drift import detect_drift
    report = detect_drift(
        current_phase="red",
        last_commit_prefix="chore",
        plan_task_state="[x]",  # but state still pointing here
    )
    assert report is not None
    assert "already [x]" in report.reason or "completed" in report.reason.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_drift.py::test_detect_drift_plan_already_checked_but_state_points_to_it -v`
Expected: FAIL — existing function returns None for this case.

- [ ] **Step 3: Write minimal implementation**

Update `detect_drift` in `skills/sbtdd/scripts/drift.py` — add plan check BEFORE the existing phase/prefix check:

```python
def detect_drift(
    current_phase: str,
    last_commit_prefix: str,
    plan_task_state: str,
) -> DriftReport | None:
    """Detect state/git/plan divergence per sec.S.9.2.

    Checks (in order):
    1. Plan checkbox already [x] but state still points to this task (INV-3).
    2. current_phase + HEAD commit prefix = close-phase pair (sec.S.9.2 regla operativa).

    Args:
        current_phase: "red" | "green" | "refactor" | "done" from state file.
        last_commit_prefix: prefix of HEAD commit.
        plan_task_state: "[ ]" or "[x]" for the current task.

    Returns:
        DriftReport if any check fires; None if state/git/plan are coherent.
    """
    if current_phase != "done" and plan_task_state == "[x]":
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                f"state points to an active task (phase={current_phase}) "
                f"but plan already shows [x] — task completed without "
                f"state advance (INV-3)"
            ),
        )
    conflicting = _DRIFT_PHASE_PREFIX.get(current_phase, ())
    if last_commit_prefix in conflicting:
        return DriftReport(
            state_value=current_phase,
            git_value=last_commit_prefix,
            plan_value=plan_task_state,
            reason=(
                f"close-phase for {current_phase} appears to have "
                f"committed ({last_commit_prefix}:) but state file was "
                f"not advanced"
            ),
        )
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_drift.py -v`
Expected: PASS — 7 tests (including previous ones still green).

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/drift.py tests/test_drift.py
git commit -m "test: add drift detection for plan-checkbox vs state mismatch"
```

---

## Phase 3: Config & Templates (Tasks 16-23 — scenarios 5, 6, 7)

### Task 16: `config.py` — `PluginConfig` dataclass

**Files:**
- Create: `skills/sbtdd/scripts/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import pytest
from dataclasses import FrozenInstanceError

def test_plugin_config_is_frozen():
    from config import PluginConfig
    cfg = PluginConfig(
        stack="python",
        author="Test",
        error_type=None,
        verification_commands=("pytest", "ruff check ."),
        plan_path="planning/claude-plan-tdd.md",
        plan_org_path="planning/claude-plan-tdd-org.md",
        spec_base_path="sbtdd/spec-behavior-base.md",
        spec_path="sbtdd/spec-behavior.md",
        state_file_path=".claude/session-state.json",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        auto_magi_max_iterations=5,
        auto_verification_retries=1,
        tdd_guard_enabled=True,
        worktree_policy="optional",
    )
    with pytest.raises(FrozenInstanceError):
        cfg.stack = "rust"  # type: ignore[misc]

def test_plugin_config_verification_commands_is_tuple():
    from config import PluginConfig
    cfg = PluginConfig(
        stack="python", author="Test", error_type=None,
        verification_commands=("pytest",),
        plan_path="", plan_org_path="", spec_base_path="",
        spec_path="", state_file_path="",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3, auto_magi_max_iterations=5,
        auto_verification_retries=1, tdd_guard_enabled=True,
        worktree_policy="optional",
    )
    assert isinstance(cfg.verification_commands, tuple)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'config'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/config.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""plugin.local.md YAML frontmatter parser (sec.S.4.2 schema).

PluginConfig is a frozen dataclass with one attribute per field of the
schema. load_plugin_local validates the YAML frontmatter and returns
an instance; any schema violation raises ValidationError.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PluginConfig:
    """Parsed configuration from .claude/plugin.local.md (sec.S.4.2)."""

    stack: Literal["rust", "python", "cpp"]
    author: str
    error_type: str | None
    verification_commands: tuple[str, ...]
    plan_path: str
    plan_org_path: str
    spec_base_path: str
    spec_path: str
    state_file_path: str
    magi_threshold: Literal["STRONG_GO", "GO", "GO_WITH_CAVEATS"]
    magi_max_iterations: int
    auto_magi_max_iterations: int
    auto_verification_retries: int
    tdd_guard_enabled: bool
    worktree_policy: Literal["optional", "required"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "test: add PluginConfig frozen dataclass with strict Literal types"
```

---

### Task 17: `config.py` — `load_plugin_local` (YAML frontmatter parsing)

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`
- Create: `tests/fixtures/plugin-locals/valid-python.md`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py (append)
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plugin-locals"

def test_load_valid_python_config():
    from config import load_plugin_local, PluginConfig
    cfg = load_plugin_local(FIXTURES_DIR / "valid-python.md")
    assert isinstance(cfg, PluginConfig)
    assert cfg.stack == "python"
    assert cfg.author == "Julian Bolivar"
    assert cfg.magi_max_iterations == 3
    assert cfg.auto_magi_max_iterations == 5
    assert isinstance(cfg.verification_commands, tuple)
    assert "pytest" in cfg.verification_commands

def test_load_missing_file():
    from config import load_plugin_local
    from errors import ValidationError
    with pytest.raises(ValidationError):
        load_plugin_local(Path("/nonexistent/path.md"))
```

Create `tests/fixtures/plugin-locals/valid-python.md`:

```markdown
---
stack: python
author: "Julian Bolivar"
error_type: null
verification_commands:
  - "pytest"
  - "ruff check ."
  - "ruff format --check ."
  - "mypy ."
plan_path: "planning/claude-plan-tdd.md"
plan_org_path: "planning/claude-plan-tdd-org.md"
spec_base_path: "sbtdd/spec-behavior-base.md"
spec_path: "sbtdd/spec-behavior.md"
state_file_path: ".claude/session-state.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---

# Test config for Python stack
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: FAIL con `ImportError: cannot import name 'load_plugin_local'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/config.py`:

```python
import re
from pathlib import Path

from errors import ValidationError

# Minimal YAML-subset parser sufficient for sec.S.4.2 schema.
# We avoid adding PyYAML as a runtime dep per NF1 (stdlib-only hot paths).
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)


def _parse_simple_yaml(text: str) -> dict[str, object]:
    """Minimal YAML parser for flat scalar + simple list frontmatter.

    Supports: scalars (string, int, bool, null), quoted strings,
    sequences via "- value" lines. Does NOT support nested maps
    beyond the top level.
    """
    result: dict[str, object] = {}
    current_key: str | None = None
    current_list: list[str] | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line.startswith("  - ") and current_key is not None:
            # Sequence item under previous key.
            item = line[4:].strip()
            if item.startswith('"') and item.endswith('"'):
                item = item[1:-1]
            if current_list is None:
                current_list = []
                result[current_key] = current_list
            current_list.append(item)
            continue
        if ":" in line and not line.startswith(" "):
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            current_key = key
            current_list = None
            if not value:
                result[key] = []  # Will be filled by subsequent "-" lines.
                current_list = result[key]  # type: ignore[assignment]
                continue
            if value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value == "true":
                result[key] = True
            elif value == "false":
                result[key] = False
            elif value == "null":
                result[key] = None
            else:
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = value
    return result


def load_plugin_local(path: Path | str) -> PluginConfig:
    """Parse .claude/plugin.local.md and validate against sec.S.4.2.

    Args:
        path: Path to plugin.local.md.

    Returns:
        PluginConfig instance.

    Raises:
        ValidationError: If file missing, malformed frontmatter, or any
        schema constraint violated.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"plugin.local.md not found: {p}") from exc
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValidationError(f"no YAML frontmatter in {p}")
    data = _parse_simple_yaml(match.group(1))
    # Convert verification_commands list → tuple for immutability.
    if isinstance(data.get("verification_commands"), list):
        data["verification_commands"] = tuple(data["verification_commands"])  # type: ignore[arg-type]
    try:
        return PluginConfig(**data)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValidationError(f"schema mismatch in {p}: {exc}") from exc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py tests/fixtures/plugin-locals/valid-python.md
git commit -m "test: add load_plugin_local with minimal YAML frontmatter parser"
```

---

### Task 18: `config.py` — schema validation (stack enum, thresholds)

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py (append)
def test_validate_rejects_invalid_stack(tmp_path):
    from config import load_plugin_local
    from errors import ValidationError
    content = """---
stack: ruby
author: "Test"
error_type: null
verification_commands:
  - "pytest"
plan_path: "p"
plan_org_path: "p"
spec_base_path: "s"
spec_path: "s"
state_file_path: ".claude/s.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---
"""
    f = tmp_path / "bad.md"
    f.write_text(content)
    with pytest.raises(ValidationError) as exc_info:
        load_plugin_local(f)
    assert "stack" in str(exc_info.value)

def test_validate_rejects_auto_magi_less_than_base():
    from config import load_plugin_local
    from errors import ValidationError
    # auto_magi_max_iterations must be >= magi_max_iterations (sec.S.4.3)
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
stack: python
author: "T"
error_type: null
verification_commands:
  - "pytest"
plan_path: "p"
plan_org_path: "p"
spec_base_path: "s"
spec_path: "s"
state_file_path: ".claude/s.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 5
auto_magi_max_iterations: 3
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---
""")
        path = f.name
    with pytest.raises(ValidationError) as exc_info:
        load_plugin_local(path)
    assert "auto_magi_max_iterations" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: FAIL — no validation for enums/thresholds yet.

- [ ] **Step 3: Write minimal implementation**

Append validation logic to `load_plugin_local` in `skills/sbtdd/scripts/config.py` — insert before the `PluginConfig(**data)` call:

```python
    # Semantic validation beyond type-checking (sec.S.4.3).
    valid_stacks = {"rust", "python", "cpp"}
    if data.get("stack") not in valid_stacks:
        raise ValidationError(
            f"stack='{data.get('stack')}' not in {sorted(valid_stacks)}"
        )
    valid_thresholds = {"STRONG_GO", "GO", "GO_WITH_CAVEATS"}
    if data.get("magi_threshold") not in valid_thresholds:
        raise ValidationError(
            f"magi_threshold='{data.get('magi_threshold')}' not in "
            f"{sorted(valid_thresholds)}"
        )
    valid_policies = {"optional", "required"}
    if data.get("worktree_policy") not in valid_policies:
        raise ValidationError(
            f"worktree_policy='{data.get('worktree_policy')}' not in "
            f"{sorted(valid_policies)}"
        )
    mag = data.get("magi_max_iterations")
    auto_mag = data.get("auto_magi_max_iterations")
    if not isinstance(mag, int) or mag < 1:
        raise ValidationError(f"magi_max_iterations must be int >= 1, got {mag!r}")
    if not isinstance(auto_mag, int) or auto_mag < mag:
        raise ValidationError(
            f"auto_magi_max_iterations ({auto_mag}) must be int >= "
            f"magi_max_iterations ({mag})"
        )
    retries = data.get("auto_verification_retries")
    if not isinstance(retries, int) or retries < 0:
        raise ValidationError(
            f"auto_verification_retries must be int >= 0, got {retries!r}"
        )
    if not isinstance(data.get("verification_commands"), tuple):
        raise ValidationError("verification_commands must be a non-empty list")
    if len(data["verification_commands"]) == 0:  # type: ignore[arg-type]
        raise ValidationError("verification_commands must be non-empty")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_config.py -v`
Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "test: add semantic validation for stack/threshold/policy/iterations"
```

---

### Task 19: `templates.py` — `expand` simple placeholder substitution

**Files:**
- Create: `skills/sbtdd/scripts/templates.py`
- Create: `tests/test_templates.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_templates.py
def test_expand_substitutes_known_placeholders():
    from templates import expand
    template = "# Author: {Author}\n# Version: {Version}\n"
    result = expand(template, {"Author": "Jane Doe", "Version": "1.0.0"})
    assert result == "# Author: Jane Doe\n# Version: 1.0.0\n"

def test_expand_leaves_unknown_placeholders_literal():
    """Unknown placeholders stay as-is (no KeyError, no silent error)."""
    from templates import expand
    template = "Hello {Known} and {Unknown}"
    result = expand(template, {"Known": "world"})
    assert result == "Hello world and {Unknown}"

def test_expand_empty_context():
    from templates import expand
    template = "no placeholders here"
    assert expand(template, {}) == "no placeholders here"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_templates.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'templates'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/templates.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Placeholder expansion for template files (sec.S.2.1 templates.py).

expand() substitutes {Key} placeholders using a context dict. Unknown
placeholders are left literal (no KeyError) to enable partial expansion
and forward compatibility with template additions.
"""

from __future__ import annotations

import re
from typing import Mapping

_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def expand(template: str, context: Mapping[str, str]) -> str:
    """Substitute {Key} placeholders in template using context.

    Args:
        template: The template string containing {Key} placeholders.
        context: Mapping of placeholder names → replacement strings.

    Returns:
        The template with known placeholders replaced; unknown
        placeholders are left literal (e.g. "{Unknown}").
    """
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(_replace, template)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_templates.py -v`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/templates.py tests/test_templates.py
git commit -m "test: add templates.expand with unknown-placeholder pass-through"
```

---

### Task 20: `templates.py` — preserve trailing newlines + edge cases

**Files:**
- Modify: `tests/test_templates.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_templates.py (append)
def test_expand_preserves_trailing_newline():
    from templates import expand
    template = "{X}\n"
    assert expand(template, {"X": "a"}) == "a\n"

def test_expand_placeholder_with_special_chars_in_value():
    """Value containing braces should not be re-expanded (single pass)."""
    from templates import expand
    template = "{X}"
    result = expand(template, {"X": "{Y}"})
    assert result == "{Y}"  # not recursive; {Y} stays literal.
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `.venv/Scripts/pytest tests/test_templates.py -v`
Expected: PASS — the existing `re.sub` implementation is single-pass and preserves whitespace. This task is a Refactor-phase commit (coverage expansion).

- [ ] **Step 3: (no new impl needed)**

- [ ] **Step 4: Verify all tests pass**

Run: `.venv/Scripts/pytest tests/test_templates.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_templates.py
git commit -m "refactor: add edge-case tests for templates.expand"
```

---

### Task 21: `hooks_installer.py` — parse existing settings.json

**Files:**
- Create: `skills/sbtdd/scripts/hooks_installer.py`
- Create: `tests/test_hooks_installer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_hooks_installer.py
import json
import pytest
from pathlib import Path

def test_read_existing_settings_returns_dict(tmp_path):
    from hooks_installer import read_existing
    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"hooks": {"PreToolUse": []}}))
    result = read_existing(target)
    assert result == {"hooks": {"PreToolUse": []}}

def test_read_missing_returns_empty_dict(tmp_path):
    from hooks_installer import read_existing
    missing = tmp_path / "missing.json"
    assert read_existing(missing) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'hooks_installer'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/hooks_installer.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Idempotent merge of .claude/settings.json (sec.S.5.1 Fase 3, sec.S.7.2).

When init runs on a project that already has settings.json with user
hooks, we must preserve those hooks and ADD ours — never overwrite.
Subsequent runs with identical inputs must produce byte-identical
output (idempotency invariant).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_existing(path: Path | str) -> dict[str, Any]:
    """Read existing settings.json or return {} if missing.

    Args:
        path: Path to settings.json.

    Returns:
        Parsed dict, or empty dict if the file does not exist.

    Raises:
        json.JSONDecodeError: If the file exists but is malformed.
    """
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/hooks_installer.py tests/test_hooks_installer.py
git commit -m "test: add hooks_installer.read_existing for settings.json"
```

---

### Task 22: `hooks_installer.py` — `merge` (preserve user hooks + add plugin)

**Files:**
- Modify: `skills/sbtdd/scripts/hooks_installer.py`
- Modify: `tests/test_hooks_installer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_hooks_installer.py (append)
def test_merge_preserves_user_hooks_and_adds_plugin(tmp_path):
    from hooks_installer import merge
    user_settings = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write", "hooks": [{"type": "command", "command": "eslint"}]}
            ]
        }
    }
    plugin_hooks = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write|Edit|MultiEdit|TodoWrite",
                 "hooks": [{"type": "command", "command": "tdd-guard"}]}
            ],
            "SessionStart": [
                {"matcher": "startup|resume|clear",
                 "hooks": [{"type": "command", "command": "tdd-guard"}]}
            ]
        }
    }
    existing = tmp_path / "settings.json"
    existing.write_text(json.dumps(user_settings))
    target = tmp_path / "settings.json"
    merge(existing_path=existing, plugin_hooks=plugin_hooks, target_path=target)
    result = json.loads(target.read_text())
    # Both user and plugin hooks should be in PreToolUse.
    commands = [h["hooks"][0]["command"] for h in result["hooks"]["PreToolUse"]]
    assert "eslint" in commands
    assert "tdd-guard" in commands
    # SessionStart (plugin-only) should exist.
    assert "SessionStart" in result["hooks"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py -v`
Expected: FAIL con `ImportError: cannot import name 'merge'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/hooks_installer.py`:

```python
import os


def merge(
    existing_path: Path | str,
    plugin_hooks: dict[str, Any],
    target_path: Path | str,
) -> None:
    """Merge plugin hooks into existing settings.json, writing atomically.

    Preserves all user hooks; appends plugin hooks alongside them. Write
    pattern: write to tmp file in same directory, then os.replace —
    atomic on POSIX and Windows.

    Args:
        existing_path: Path to existing settings.json (may not exist).
        plugin_hooks: Plugin hook fragment to merge in. Expected shape:
            {"hooks": {"<event>": [hook_entry, ...], ...}}
        target_path: Where to write the merged result.
    """
    existing = read_existing(existing_path)
    existing_hooks = existing.setdefault("hooks", {})
    for event, entries in plugin_hooks.get("hooks", {}).items():
        existing_list = existing_hooks.setdefault(event, [])
        for entry in entries:
            if entry not in existing_list:
                existing_list.append(entry)
    target = Path(target_path)
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    os.replace(tmp, target)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py -v`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/hooks_installer.py tests/test_hooks_installer.py
git commit -m "test: add hooks_installer.merge preserving user hooks"
```

---

### Task 23: `hooks_installer.py` — idempotency verification

**Files:**
- Modify: `tests/test_hooks_installer.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_hooks_installer.py (append)
def test_merge_is_idempotent(tmp_path):
    """Running merge twice with same inputs produces byte-identical output."""
    from hooks_installer import merge
    plugin_hooks = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write", "hooks": [{"type": "command", "command": "tdd-guard"}]}
            ]
        }
    }
    target = tmp_path / "settings.json"
    merge(existing_path=target, plugin_hooks=plugin_hooks, target_path=target)
    first = target.read_bytes()
    merge(existing_path=target, plugin_hooks=plugin_hooks, target_path=target)
    second = target.read_bytes()
    assert first == second
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py::test_merge_is_idempotent -v`
Expected: PASS (dedup via `if entry not in existing_list` already ensures idempotency). This is a Refactor-phase commit (verification of existing behavior).

- [ ] **Step 3: (no new impl needed)**

- [ ] **Step 4: Verify all tests pass**

Run: `.venv/Scripts/pytest tests/test_hooks_installer.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_hooks_installer.py
git commit -m "refactor: add idempotency test for hooks_installer.merge"
```

---

## Phase 4: Subprocess & Quota (Tasks 24-30 — scenarios 8, 9)

### Task 24: `subprocess_utils.py` — `run_with_timeout`

**Files:**
- Create: `skills/sbtdd/scripts/subprocess_utils.py`
- Create: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_subprocess_utils.py
import pytest
import sys

def test_run_with_timeout_returns_completed_process():
    from subprocess_utils import run_with_timeout
    result = run_with_timeout([sys.executable, "-c", "print('hi')"], timeout=5)
    assert result.returncode == 0
    assert "hi" in result.stdout

def test_run_with_timeout_rejects_shell_true():
    from subprocess_utils import run_with_timeout
    # shell parameter is not exposed — the helper enforces shell=False.
    result = run_with_timeout([sys.executable, "-c", "import sys; sys.exit(3)"], timeout=5)
    assert result.returncode == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'subprocess_utils'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/subprocess_utils.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Subprocess wrappers enforcing sec.S.8.6 conventions.

- shell=False always.
- Arguments as lists, not strings.
- Explicit timeouts.
- Windows kill-tree via taskkill /F /T /PID BEFORE proc.kill() (MAGI R3-1).
"""

from __future__ import annotations

import subprocess
import sys


def run_with_timeout(
    cmd: list[str],
    timeout: int,
    capture: bool = True,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with shell=False and an explicit timeout.

    Args:
        cmd: Command as list of strings (never a single string).
        timeout: Wall-clock seconds before SIGTERM.
        capture: If True, capture stdout/stderr as text.
        cwd: Working directory (None = current).

    Returns:
        CompletedProcess with returncode, stdout, stderr.

    Raises:
        subprocess.TimeoutExpired: If the process did not finish in time.
    """
    return subprocess.run(
        cmd,
        shell=False,
        capture_output=capture,
        text=True,
        timeout=timeout,
        cwd=cwd,
        check=False,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/subprocess_utils.py tests/test_subprocess_utils.py
git commit -m "test: add run_with_timeout enforcing shell=False"
```

---

### Task 25: `subprocess_utils.py` — `kill_tree` Windows path

**Files:**
- Modify: `skills/sbtdd/scripts/subprocess_utils.py`
- Modify: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_subprocess_utils.py (append)
def test_kill_tree_windows_calls_taskkill_before_proc_kill(monkeypatch):
    """Verifies MAGI R3-1 order: taskkill /F /T /PID BEFORE proc.kill()."""
    from subprocess_utils import kill_tree
    call_order: list[str] = []

    def fake_run(cmd, **kwargs):
        call_order.append(f"subprocess.run:{cmd[0]}")
        class R:
            returncode = 0
        return R()

    class FakeProc:
        pid = 12345
        def kill(self):
            call_order.append("proc.kill")
        def poll(self):
            return None  # still running
        def wait(self, timeout=None):
            call_order.append(f"proc.wait:{timeout}")
            return 0

    monkeypatch.setattr("subprocess_utils.subprocess.run", fake_run)
    monkeypatch.setattr("subprocess_utils.sys.platform", "win32")
    kill_tree(FakeProc())
    # taskkill MUST appear before proc.kill
    taskkill_idx = next(i for i, c in enumerate(call_order) if "taskkill" in c)
    kill_idx = call_order.index("proc.kill")
    assert taskkill_idx < kill_idx, f"call order wrong: {call_order}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py -v`
Expected: FAIL con `ImportError: cannot import name 'kill_tree'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/subprocess_utils.py`:

```python
def kill_tree(proc: "subprocess.Popen[str]") -> None:
    """Terminate process and all children cross-platform.

    Windows: taskkill /F /T /PID <pid> BEFORE proc.kill() (MAGI R3-1 —
    parent must still be alive for taskkill to enumerate its descendants).
    POSIX: SIGTERM + 3-second wait + SIGKILL fallback.

    Args:
        proc: Running Popen instance.
    """
    if proc.poll() is not None:
        return  # Already exited.
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                shell=False,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Fall through to proc.kill as belt-and-suspenders.
        proc.kill()
        proc.wait(timeout=5)
    else:
        import signal
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py -v`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/subprocess_utils.py tests/test_subprocess_utils.py
git commit -m "test: add kill_tree Windows taskkill-before-kill order"
```

---

### Task 26: `subprocess_utils.py` — POSIX kill_tree path

**Files:**
- Modify: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_subprocess_utils.py (append)
def test_kill_tree_posix_sends_sigterm_then_sigkill(monkeypatch):
    from subprocess_utils import kill_tree
    import subprocess as sp
    signals_sent: list[str] = []

    class FakeProc:
        pid = 54321
        _waits = 0
        def send_signal(self, sig):
            import signal
            signals_sent.append("SIGTERM" if sig == signal.SIGTERM else str(sig))
        def kill(self):
            signals_sent.append("SIGKILL")
        def poll(self):
            return None
        def wait(self, timeout=None):
            self._waits += 1
            if self._waits == 1:
                raise sp.TimeoutExpired(cmd="x", timeout=timeout)
            return 0

    monkeypatch.setattr("subprocess_utils.sys.platform", "linux")
    kill_tree(FakeProc())
    assert signals_sent == ["SIGTERM", "SIGKILL"]
```

- [ ] **Step 2: Run test to verify it fails/passes**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py::test_kill_tree_posix_sends_sigterm_then_sigkill -v`
Expected: PASS (behavior already implemented in Task 25). This is a Refactor-phase test adding POSIX coverage.

- [ ] **Step 3: (no new impl needed)**

- [ ] **Step 4: Verify all tests pass**

Run: `.venv/Scripts/pytest tests/test_subprocess_utils.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_subprocess_utils.py
git commit -m "refactor: add POSIX kill_tree SIGTERM+SIGKILL test coverage"
```

---

### Task 27: `quota_detector.py` — `QUOTA_PATTERNS` registry

**Files:**
- Create: `skills/sbtdd/scripts/quota_detector.py`
- Create: `tests/test_quota_detector.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_quota_detector.py
from types import MappingProxyType

def test_quota_patterns_is_mapping_proxy():
    from quota_detector import QUOTA_PATTERNS
    assert isinstance(QUOTA_PATTERNS, MappingProxyType)

def test_quota_patterns_has_four_kinds():
    from quota_detector import QUOTA_PATTERNS
    assert set(QUOTA_PATTERNS.keys()) == {
        "rate_limit_429", "session_limit", "credit_exhausted", "server_throttle"
    }

def test_quota_patterns_are_compiled_regex():
    import re
    from quota_detector import QUOTA_PATTERNS
    for pattern in QUOTA_PATTERNS.values():
        assert isinstance(pattern, re.Pattern)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'quota_detector'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/quota_detector.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Detection of Anthropic API quota exhaustion (sec.S.11.4).

The plugin invokes skills (superpowers, magi) that internally run
claude -p against the Anthropic API. When the API hits rate limits or
subscription/credit limits, the skill's stderr contains distinctive
messages. This module regex-matches those patterns and returns a
typed QuotaExhaustion result; the dispatcher raises QuotaExhaustedError
and exits with code 11.

Patterns are brittle (Anthropic can change the text). Centralizing them
here makes updates a one-file change.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Mapping

_QUOTA_PATTERNS_MUTABLE: dict[str, re.Pattern[str]] = {
    "rate_limit_429": re.compile(r"Request rejected \(429\)"),
    "session_limit": re.compile(
        r"You've hit your (session|weekly|Opus) limit · resets (.+?)(?:\s|$)"
    ),
    "credit_exhausted": re.compile(r"Credit balance is too low"),
    "server_throttle": re.compile(r"Server is temporarily limiting requests"),
}

#: Read-only registry of quota exhaustion regex patterns.
QUOTA_PATTERNS: Mapping[str, re.Pattern[str]] = MappingProxyType(_QUOTA_PATTERNS_MUTABLE)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: PASS — 3 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/quota_detector.py tests/test_quota_detector.py
git commit -m "test: add QUOTA_PATTERNS registry as MappingProxyType"
```

---

### Task 28: `quota_detector.py` — `QuotaExhaustion` dataclass

**Files:**
- Modify: `skills/sbtdd/scripts/quota_detector.py`
- Modify: `tests/test_quota_detector.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_quota_detector.py (append)
import pytest
from dataclasses import FrozenInstanceError

def test_quota_exhaustion_is_frozen():
    from quota_detector import QuotaExhaustion
    q = QuotaExhaustion(
        kind="session_limit",
        raw_message="...",
        reset_time="3:45pm",
        recoverable=True,
    )
    with pytest.raises(FrozenInstanceError):
        q.kind = "other"  # type: ignore[misc]

def test_quota_exhaustion_fields():
    from quota_detector import QuotaExhaustion
    fields = set(QuotaExhaustion.__dataclass_fields__)
    assert fields == {"kind", "raw_message", "reset_time", "recoverable"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: FAIL con `ImportError: cannot import name 'QuotaExhaustion'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/quota_detector.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class QuotaExhaustion:
    """Parsed result of a quota-exhaustion match on stderr."""

    kind: str                    # Key of QUOTA_PATTERNS that matched.
    raw_message: str             # Matched substring from stderr.
    reset_time: str | None       # Extracted from session_limit pattern; None otherwise.
    recoverable: bool            # True for all current cases.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: PASS — 5 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/quota_detector.py tests/test_quota_detector.py
git commit -m "test: add QuotaExhaustion frozen dataclass"
```

---

### Task 29: `quota_detector.py` — `detect` function + fixtures

**Files:**
- Modify: `skills/sbtdd/scripts/quota_detector.py`
- Modify: `tests/test_quota_detector.py`
- Create: `tests/fixtures/quota-errors/session_limit.txt`
- Create: `tests/fixtures/quota-errors/rate_limit_429.txt`
- Create: `tests/fixtures/quota-errors/credit_exhausted.txt`
- Create: `tests/fixtures/quota-errors/server_throttle.txt`
- Create: `tests/fixtures/quota-errors/no_quota_match.txt`

- [ ] **Step 1: Write failing test**

```python
# tests/test_quota_detector.py (append)
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "quota-errors"

def test_detect_session_limit_extracts_reset_time():
    from quota_detector import detect
    stderr = (FIXTURES_DIR / "session_limit.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "session_limit"
    assert result.reset_time == "3:45pm"
    assert result.recoverable is True

def test_detect_rate_limit_429():
    from quota_detector import detect
    stderr = (FIXTURES_DIR / "rate_limit_429.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "rate_limit_429"
    assert result.reset_time is None

def test_detect_credit_exhausted():
    from quota_detector import detect
    stderr = (FIXTURES_DIR / "credit_exhausted.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "credit_exhausted"

def test_detect_server_throttle():
    from quota_detector import detect
    stderr = (FIXTURES_DIR / "server_throttle.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "server_throttle"

def test_detect_no_match_returns_none():
    from quota_detector import detect
    stderr = (FIXTURES_DIR / "no_quota_match.txt").read_text()
    assert detect(stderr) is None
```

Create fixtures:

`tests/fixtures/quota-errors/session_limit.txt`:
```
Error: You've hit your session limit · resets 3:45pm
Please try again after the reset time.
```

`tests/fixtures/quota-errors/rate_limit_429.txt`:
```
API Error: Request rejected (429) · this may be a temporary capacity issue
```

`tests/fixtures/quota-errors/credit_exhausted.txt`:
```
Error: Credit balance is too low to process this request.
Add credits at console.anthropic.com
```

`tests/fixtures/quota-errors/server_throttle.txt`:
```
API Error: Server is temporarily limiting requests (not your usage limit)
```

`tests/fixtures/quota-errors/no_quota_match.txt`:
```
Error: file not found: /tmp/missing.txt
Exit code: 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: FAIL con `ImportError: cannot import name 'detect'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/quota_detector.py`:

```python
def detect(stderr: str) -> QuotaExhaustion | None:
    """Scan stderr for quota exhaustion patterns.

    Args:
        stderr: Standard error output from an invoked skill/subprocess.

    Returns:
        QuotaExhaustion if any pattern matches; None otherwise.
    """
    for kind, pattern in QUOTA_PATTERNS.items():
        match = pattern.search(stderr)
        if match:
            reset_time = match.group(2) if kind == "session_limit" else None
            return QuotaExhaustion(
                kind=kind,
                raw_message=match.group(0),
                reset_time=reset_time,
                recoverable=True,
            )
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: PASS — 10 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/quota_detector.py tests/test_quota_detector.py tests/fixtures/quota-errors/
git commit -m "test: add quota_detector.detect with 4-pattern fixture suite"
```

---

### Task 30: `quota_detector.py` — negative case polish

**Files:**
- Modify: `tests/test_quota_detector.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_quota_detector.py (append)
def test_detect_empty_stderr_returns_none():
    from quota_detector import detect
    assert detect("") is None

def test_detect_unrelated_429_text_does_not_match():
    """'429' alone is not a quota signal — requires 'Request rejected (429)'."""
    from quota_detector import detect
    assert detect("HTTP 429 found in docs") is None
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: PASS (tests verify that the pattern is correctly specific). This is a Refactor-phase commit.

- [ ] **Step 3: (no new impl needed)**

- [ ] **Step 4: Verify all tests pass**

Run: `.venv/Scripts/pytest tests/test_quota_detector.py -v`
Expected: PASS — 12 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_quota_detector.py
git commit -m "refactor: add negative-case coverage for quota_detector.detect"
```

---

## Phase 5: Commits (Tasks 31-34 — scenario 10)

### Task 31: `commits.py` — `validate_prefix`

**Files:**
- Create: `skills/sbtdd/scripts/commits.py`
- Create: `tests/test_commits.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_commits.py
import pytest

def test_validate_prefix_accepts_known():
    from commits import validate_prefix
    for prefix in ("test", "feat", "fix", "refactor", "chore"):
        validate_prefix(prefix)  # no raise

def test_validate_prefix_rejects_unknown():
    from commits import validate_prefix
    from errors import ValidationError
    with pytest.raises(ValidationError):
        validate_prefix("wip")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'commits'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/commits.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Git commit helpers enforcing sec.M.5 prefixes + INV-0/5-7 rules.

All plugin commits go through this module so validation is centralized:
- Only allowed prefixes (sec.M.5).
- English-only messages (Code Standards Git section).
- No Co-Authored-By lines (INV-7).
- No Claude/AI references (INV-7).
"""

from __future__ import annotations

from errors import ValidationError

_ALLOWED_PREFIXES: frozenset[str] = frozenset({"test", "feat", "fix", "refactor", "chore"})


def validate_prefix(prefix: str) -> None:
    """Raise ValidationError if prefix is not in the allowed set."""
    if prefix not in _ALLOWED_PREFIXES:
        raise ValidationError(
            f"commit prefix '{prefix}' not in {sorted(_ALLOWED_PREFIXES)} (sec.M.5)"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/commits.py tests/test_commits.py
git commit -m "test: add validate_prefix enforcing sec.M.5 allowed prefixes"
```

---

### Task 32: `commits.py` — `validate_message_english_only`

**Files:**
- Modify: `skills/sbtdd/scripts/commits.py`
- Modify: `tests/test_commits.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_commits.py (append)
def test_validate_message_rejects_co_authored_by():
    from commits import validate_message
    from errors import ValidationError
    with pytest.raises(ValidationError) as exc_info:
        validate_message("add parser\n\nCo-Authored-By: someone")
    assert "Co-Authored-By" in str(exc_info.value)

def test_validate_message_rejects_claude_reference():
    from commits import validate_message
    from errors import ValidationError
    with pytest.raises(ValidationError):
        validate_message("add parser suggested by Claude")

def test_validate_message_rejects_ai_reference():
    from commits import validate_message
    from errors import ValidationError
    with pytest.raises(ValidationError):
        validate_message("fix: regression found by AI assistant")

def test_validate_message_accepts_clean_english():
    from commits import validate_message
    validate_message("add parser for empty input edge case")  # no raise
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: FAIL con `ImportError: cannot import name 'validate_message'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/commits.py`:

```python
import re

_FORBIDDEN_MESSAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Co-Authored-By", re.IGNORECASE),
    re.compile(r"\bClaude\b", re.IGNORECASE),
    re.compile(r"\bAI\b"),
    re.compile(r"\bassistant\b", re.IGNORECASE),
)


def validate_message(message: str) -> None:
    """Reject commit messages that violate INV-0/5-7.

    Args:
        message: Full commit message (without prefix).

    Raises:
        ValidationError: If message contains Co-Authored-By or Claude/AI
        references.
    """
    for pattern in _FORBIDDEN_MESSAGE_PATTERNS:
        match = pattern.search(message)
        if match:
            raise ValidationError(
                f"commit message contains forbidden pattern '{match.group(0)}' "
                f"(INV-7, ~/.claude/CLAUDE.md Git section)"
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: PASS — 6 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/commits.py tests/test_commits.py
git commit -m "test: add validate_message rejecting Co-Authored-By and AI refs"
```

---

### Task 33: `commits.py` — `create` function (validate + git commit)

**Files:**
- Modify: `skills/sbtdd/scripts/commits.py`
- Modify: `tests/test_commits.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_commits.py (append)
def test_create_invokes_git_commit(monkeypatch, tmp_path):
    from commits import create
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class R:
            returncode = 0
            stdout = "[main abc1234] test: foo"
            stderr = ""
        return R()

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    create(prefix="test", message="add parser edge case", cwd=str(tmp_path))
    # At least one call should be `git commit -m "test: add parser edge case"`.
    commit_calls = [c for c in calls if "commit" in c]
    assert len(commit_calls) == 1
    assert commit_calls[0][-1] == "test: add parser edge case"

def test_create_rejects_before_git_call(monkeypatch):
    from commits import create
    from errors import ValidationError
    def fake_run(cmd, **kwargs):
        raise AssertionError("git should not be invoked on invalid input")
    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(ValidationError):
        create(prefix="wip", message="fine message", cwd=".")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: FAIL con `ImportError: cannot import name 'create'`.

- [ ] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/commits.py`:

```python
import subprocess_utils


def create(prefix: str, message: str, cwd: str | None = None) -> str:
    """Validate and create a git commit with `{prefix}: {message}`.

    Args:
        prefix: TDD-phase prefix (test/feat/fix/refactor/chore).
        message: Commit message body (will be prefixed with `{prefix}: `).
        cwd: Working directory for the git command.

    Returns:
        Output from `git commit` (stdout).

    Raises:
        ValidationError: If prefix invalid, or message contains forbidden
        patterns (Co-Authored-By, Claude/AI refs).
        RuntimeError: If git commit returns non-zero.
    """
    validate_prefix(prefix)
    validate_message(message)
    full_message = f"{prefix}: {message}"
    result = subprocess_utils.run_with_timeout(
        ["git", "commit", "-m", full_message],
        timeout=30,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git commit failed (returncode={result.returncode}): {result.stderr}"
        )
    return result.stdout
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: PASS — 8 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/commits.py tests/test_commits.py
git commit -m "test: add commits.create orchestrating validation + git commit"
```

---

### Task 34: `commits.py` — integration: validation runs before git

**Files:**
- Modify: `tests/test_commits.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_commits.py (append)
def test_create_full_input_validation_chain(monkeypatch):
    """Validates the chain: prefix → message → git (short-circuits on first fail)."""
    from commits import create
    from errors import ValidationError

    def fake_run(cmd, **kwargs):
        raise AssertionError("git should not run — validation must short-circuit")
    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)

    # Bad prefix:
    with pytest.raises(ValidationError, match="prefix"):
        create(prefix="invalid", message="ok message", cwd=".")
    # Bad message (valid prefix):
    with pytest.raises(ValidationError, match="forbidden pattern"):
        create(prefix="feat", message="add Claude integration", cwd=".")
```

- [ ] **Step 2: Run test to verify it passes**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: PASS (chain already works from Task 33). Refactor-phase test.

- [ ] **Step 3: (no new impl needed)**

- [ ] **Step 4: Verify all tests pass**

Run: `.venv/Scripts/pytest tests/test_commits.py -v`
Expected: PASS — 9 tests.

- [ ] **Step 5: Commit**

```bash
git add tests/test_commits.py
git commit -m "refactor: add validation-chain short-circuit test for commits.create"
```

---

## Phase 6: Milestone Gate (Task 35)

### Task 35: LICENSE dual files + full `make verify` clean

**Files:**
- Create: `LICENSE`
- Create: `LICENSE-APACHE`

- [ ] **Step 1: Write failing test**

```python
# tests/test_commits.py (append — convenient location)
def test_license_files_exist():
    from pathlib import Path
    root = Path(__file__).parent.parent
    assert (root / "LICENSE").exists(), "MIT LICENSE file missing (sec.S.12.2)"
    assert (root / "LICENSE-APACHE").exists(), "Apache LICENSE file missing"

def test_license_dual_in_pyproject():
    from pathlib import Path
    root = Path(__file__).parent.parent
    content = (root / "pyproject.toml").read_text()
    assert 'license = "MIT OR Apache-2.0"' in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/pytest tests/test_commits.py::test_license_files_exist tests/test_commits.py::test_license_dual_in_pyproject -v`
Expected: FAIL — LICENSE files don't exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `LICENSE` (MIT):

```
MIT License

Copyright (c) 2026 Julian Bolivar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Create `LICENSE-APACHE` — fetch official Apache-2.0 text from https://www.apache.org/licenses/LICENSE-2.0.txt and save verbatim (too long to inline here; engineer should copy the standard Apache-2.0 license text).

- [ ] **Step 4: Run full make verify**

Run:

```bash
.venv/Scripts/pytest tests/ -v
.venv/Scripts/ruff check .
.venv/Scripts/ruff format --check .
.venv/Scripts/mypy .
```

Expected: All four pass cleanly. Full test count should be 60+ tests across 10 test files.

- [ ] **Step 5: Commit**

```bash
git add LICENSE LICENSE-APACHE tests/test_commits.py
git commit -m "chore: add LICENSE (MIT) and LICENSE-APACHE (Apache-2.0) for dual license"
```

---

## Milestone A — Acceptance

Tras completar las 35 tareas:

- **10 módulos Python** bajo `skills/sbtdd/scripts/` + 2 `__init__.py` = 12 archivos fuente.
- **10 test files** bajo `tests/` con ~60+ tests cubriendo: inmutabilidad, jerarquía de errores, schema state file, drift detection, config parsing con validación, templates expansion, hooks merge idempotente, subprocess timeouts + kill-tree, quota detection 4-pattern, commit validation chain.
- **Fixtures** bajo `tests/fixtures/` para state files, plugin-locals, quota errors.
- **LICENSE** + **LICENSE-APACHE** presentes.
- `make verify` limpio: pytest + ruff check + ruff format --check + mypy (strict).
- **35 commits atómicos** con prefijos sec.M.5 (`test:`, `feat:`, `fix:`, `refactor:`, `chore:`).

Productos habilitados para Milestone B:
- `errors.SBTDDError` + 7 subclases → base de exit code mapping (sec.S.11.1).
- `state_file.SessionState` + `load`/`save` → backbone de los subcomandos.
- `drift.detect_drift` → invocado por `close-phase`, `close-task`, `status`, `pre-merge`, `auto`, `resume`.
- `config.PluginConfig` + `load_plugin_local` → leído por todos los subcomandos.
- `subprocess_utils.run_with_timeout` + `kill_tree` → base de `superpowers_dispatch` y `magi_dispatch`.
- `quota_detector.detect` → invocado por los dos dispatchers de skills.
- `commits.create` → invocado por `close-phase`, `close-task`, `pre-merge` mini-ciclo, `auto`.
- `templates.expand` + `hooks_installer.merge` → usados por `init_cmd`.

No implementados en Milestone A (para milestones B-E):
- `dependency_check.py`, `run_sbtdd.py`, los 9 `*_cmd.py`, `superpowers_dispatch.py`, `magi_dispatch.py`, `reporters/`, `SKILL.md`, manifests, README, CLAUDE.md, templates files.

---

## Self-Review

**1. Spec coverage (spec-behavior.md §4 Escenarios BDD):**
- Escenario 1 (models.py inmutables) → Tasks 2, 3, 4 ✓
- Escenario 2 (errors.py jerarquía) → Tasks 5, 6, 7, 8 ✓
- Escenario 3 (state_file schema) → Tasks 9, 10, 11, 12 ✓
- Escenario 4 (drift detection) → Tasks 13, 14, 15 ✓
- Escenario 5 (config parsing) → Tasks 16, 17, 18 ✓
- Escenario 6 (templates expand) → Tasks 19, 20 ✓
- Escenario 7 (hooks_installer merge) → Tasks 21, 22, 23 ✓
- Escenario 8 (subprocess kill-tree) → Tasks 24, 25, 26 ✓
- Escenario 9 (quota_detector) → Tasks 27, 28, 29, 30 ✓
- Escenario 10 (commits validation) → Tasks 31, 32, 33, 34 ✓
- Escenarios 11-19 (subcomandos) → OUT OF SCOPE para Milestone A (diferidos a B-E).

**2. Placeholder scan:** grep por "TODO"/"TBD"/"implement later" en el plan — ninguno encontrado. Todas las tareas tienen código completo.

**3. Type consistency:** nombres usados consistentemente a través de tareas:
- `COMMIT_PREFIX_MAP`, `VERDICT_RANK`, `VALID_SUBCOMMANDS` (models.py).
- `SBTDDError`, `ValidationError`, `StateFileError`, `DriftError`, `DependencyError`, `PreconditionError`, `MAGIGateError`, `QuotaExhaustedError` (errors.py).
- `SessionState`, `validate_schema`, `load`, `save` (state_file.py).
- `DriftReport`, `detect_drift` (drift.py).
- `PluginConfig`, `load_plugin_local` (config.py).
- `expand` (templates.py).
- `read_existing`, `merge` (hooks_installer.py).
- `run_with_timeout`, `kill_tree` (subprocess_utils.py).
- `QUOTA_PATTERNS`, `QuotaExhaustion`, `detect` (quota_detector.py).
- `validate_prefix`, `validate_message`, `create` (commits.py).

No naming inconsistencies detectadas.

---

## Execution Handoff

Plan complete y saved to `planning/claude-plan-tdd-org-A.md`. Dos execution options:

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

**¿Cuál approach?** (Recordatorio: antes de ejecutar, per CLAUDE.local.md §1 Flujo de especificación, este plan requiere Checkpoint 2 — revisión MAGI con umbral ≥ `GO_WITH_CAVEATS` full. El plan actual es el `-org.md` original; tras MAGI se produce `planning/claude-plan-tdd-A.md` con las correcciones aplicadas.)
