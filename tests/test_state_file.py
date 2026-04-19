#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for state_file module — SessionState + validate_schema + load + save."""

from __future__ import annotations

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
    expected = {
        "plan_path",
        "current_task_id",
        "current_task_title",
        "current_phase",
        "phase_started_at_commit",
        "last_verification_at",
        "last_verification_result",
        "plan_approved_at",
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
