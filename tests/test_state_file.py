#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for state_file module — SessionState + validate_schema + load + save."""

from __future__ import annotations

import json
import os

import pytest
from dataclasses import FrozenInstanceError
from pathlib import Path

import state_file

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "state-files"


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


def test_session_state_has_nine_fields():
    """v1.0.0: schema gains spec_snapshot_emitted_at (R10 caspar
    Checkpoint 2 iter 5 W). Optional with default None for backward
    compatibility with v0.5.0 state files.
    """
    from state_file import SessionState

    fields = [f for f in SessionState.__dataclass_fields__]
    expected = {
        "plan_path",
        "current_task_id",
        "current_task_title",
        "current_phase",
        "phase_started_at_commit",
        "last_verification_at",
        "last_verification_result",
        "plan_approved_at",
        "spec_snapshot_emitted_at",
    }
    assert set(fields) == expected


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


def test_load_rejects_non_iso8601_plan_approved_at():
    from state_file import load
    from errors import StateFileError

    with pytest.raises(StateFileError) as exc_info:
        load(FIXTURES_DIR / "invalid-approved-at.json")
    assert "plan_approved_at" in str(exc_info.value)


def test_load_wraps_typeerror_as_state_file_error(tmp_path):
    """Wrong field type (int instead of str) must raise StateFileError, not TypeError."""
    from state_file import load
    from errors import StateFileError
    import json as _json

    bad = tmp_path / "bad.json"
    bad.write_text(
        _json.dumps(
            {
                "plan_path": 42,  # wrong type, should be string
                "current_task_id": "1",
                "current_task_title": "t",
                "current_phase": "red",
                "phase_started_at_commit": "abc1234",
                "last_verification_at": None,
                "last_verification_result": None,
                "plan_approved_at": None,
            }
        )
    )
    # validate_schema passes (doesn't check plan_path type) → constructor may fail.
    # load() must wrap any TypeError as StateFileError.
    try:
        load(bad)
    except StateFileError:
        return
    except TypeError:
        pytest.fail(
            "load must wrap TypeError as StateFileError (MAGI Checkpoint 2 iter 1 caspar fix)"
        )


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

    state = SessionState(
        plan_path="p",
        current_task_id=None,
        current_task_title=None,
        current_phase="done",
        phase_started_at_commit="abc1234",
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at=None,
    )
    target = tmp_path / "subdir" / "state.json"
    # subdir does not exist; save should raise, target should not exist
    with pytest.raises((FileNotFoundError, OSError)):
        save(state, target)
    assert not target.exists()


def test_save_cleans_up_tmp_on_os_replace_failure(tmp_path, monkeypatch):
    """If os.replace raises, the .tmp file must not be left behind (MAGI iter 1 melchior)."""
    from state_file import SessionState, save
    import os as _os

    state = SessionState(
        plan_path="p",
        current_task_id=None,
        current_task_title=None,
        current_phase="done",
        phase_started_at_commit="abc1234",
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at=None,
    )
    target = tmp_path / "state.json"

    def failing_replace(src, dst):
        raise PermissionError("synthetic failure")

    monkeypatch.setattr(_os, "replace", failing_replace)

    with pytest.raises(PermissionError):
        save(state, target)

    # No .tmp file should remain anywhere under tmp_path.
    leaked = list(tmp_path.glob("*.tmp.*"))
    assert leaked == [], f"tmp files leaked: {leaked}"


class TestAtomicWriteJsonRetry:
    """v1.0.7 B3 atomic_write_json retry per spec sec.4.6."""

    def test_permission_error_triggers_retry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-1: PermissionError on first os.replace -> retry."""
        path = tmp_path / "audit.json"
        attempts: list[int] = []
        original_replace = os.replace

        def flaky_replace(src: str, dst: str) -> None:
            attempts.append(1)
            if len(attempts) == 1:
                raise PermissionError(5, "Access denied", src)
            original_replace(src, dst)

        sleeps: list[float] = []

        def fake_sleep(s: float) -> None:
            sleeps.append(s)

        monkeypatch.setattr("state_file.os.replace", flaky_replace)
        monkeypatch.setattr("state_file.time.sleep", fake_sleep)
        state_file.atomic_write_json(path, {"key": "value"})
        assert len(attempts) == 2
        # First retry slept 100ms (attempt-number 1 * 100ms).
        assert sleeps == [0.1]
        assert json.loads(path.read_text(encoding="utf-8")) == {"key": "value"}

    def test_retry_backoff_grows_per_attempt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-2: backoff = 100ms × attempt-number."""
        path = tmp_path / "audit.json"
        original_replace = os.replace

        def flaky_replace(src: str, dst: str) -> None:
            flaky_replace.calls += 1  # type: ignore[attr-defined]
            if flaky_replace.calls < 3:  # type: ignore[attr-defined]
                raise PermissionError(5, "Access denied", src)
            original_replace(src, dst)

        flaky_replace.calls = 0  # type: ignore[attr-defined]
        sleeps: list[float] = []

        monkeypatch.setattr("state_file.os.replace", flaky_replace)
        monkeypatch.setattr("state_file.time.sleep", lambda s: sleeps.append(s))
        state_file.atomic_write_json(path, {"key": "value"})
        # 2 retries: attempt 1 sleeps 100ms, attempt 2 sleeps 200ms.
        assert sleeps == [0.1, 0.2]

    def test_retry_exhaustion_reraises_permission_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-3: 3 attempts all fail -> re-raise PermissionError."""
        path = tmp_path / "audit.json"

        def always_fail(src: str, dst: str) -> None:
            raise PermissionError(5, "Access denied", src)

        monkeypatch.setattr("state_file.os.replace", always_fail)
        monkeypatch.setattr("state_file.time.sleep", lambda s: None)
        with pytest.raises(PermissionError, match="Access denied"):
            state_file.atomic_write_json(path, {"key": "value"})
