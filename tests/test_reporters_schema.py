# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for reporters.tdd_guard_schema (Tasks 14-15)."""

from __future__ import annotations

import json

import pytest


def test_test_error_is_frozen_dataclass():
    from reporters.tdd_guard_schema import TestError
    from dataclasses import FrozenInstanceError

    err = TestError(message="msg", stack="trace")
    with pytest.raises(FrozenInstanceError):
        err.message = "other"  # type: ignore[misc]


def test_test_entry_defaults_to_no_errors():
    from reporters.tdd_guard_schema import TestEntry

    e = TestEntry(name="t1", full_name="tests/t.py::t1", state="passed")
    assert e.errors == ()


def test_test_module_collects_entries():
    from reporters.tdd_guard_schema import TestEntry, TestModule

    e1 = TestEntry(name="t1", full_name="f::t1", state="passed")
    e2 = TestEntry(name="t2", full_name="f::t2", state="failed")
    m = TestModule(module_id="tests/t.py", tests=(e1, e2))
    assert len(m.tests) == 2


def test_test_json_valid_reason_values():
    from reporters.tdd_guard_schema import VALID_REASONS

    assert VALID_REASONS == ("passed", "failed", "interrupted")


def test_test_json_rejects_invalid_state():
    from reporters.tdd_guard_schema import TestEntry, VALID_STATES
    from errors import ValidationError

    assert VALID_STATES == ("passed", "failed", "skipped")
    with pytest.raises(ValidationError):
        TestEntry(name="t1", full_name="f::t1", state="bogus")


def test_test_json_to_dict_contract():
    from reporters.tdd_guard_schema import (
        TestEntry,
        TestError,
        TestModule,
        TestJSON,
    )

    e = TestEntry(
        name="t1",
        full_name="tests/t.py::t1",
        state="failed",
        errors=(TestError(message="oops", stack="frame"),),
    )
    m = TestModule(module_id="tests/t.py", tests=(e,))
    j = TestJSON(test_modules=(m,), reason="failed")
    data = j.to_dict()
    assert data == {
        "testModules": [
            {
                "moduleId": "tests/t.py",
                "tests": [
                    {
                        "name": "t1",
                        "fullName": "tests/t.py::t1",
                        "state": "failed",
                        "errors": [{"message": "oops", "stack": "frame"}],
                    }
                ],
            }
        ],
        "reason": "failed",
    }


def test_test_json_omits_errors_key_when_empty():
    from reporters.tdd_guard_schema import TestEntry, TestModule, TestJSON

    e = TestEntry(name="t1", full_name="f::t1", state="passed")
    j = TestJSON(
        test_modules=(TestModule(module_id="f", tests=(e,)),),
        reason="passed",
    )
    data = j.to_dict()
    # Passing tests: no "errors" key (conftest.py behavior).
    assert "errors" not in data["testModules"][0]["tests"][0]


def test_write_test_json_creates_parent_dir_and_writes(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry,
        TestModule,
        TestJSON,
        write_test_json,
    )

    j = TestJSON(
        test_modules=(
            TestModule(
                module_id="tests/t.py",
                tests=(TestEntry(name="t1", full_name="f::t1", state="passed"),),
            ),
        ),
        reason="passed",
    )
    target = tmp_path / ".claude" / "tdd-guard" / "data" / "test.json"
    write_test_json(j, target)
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["reason"] == "passed"
    assert data["testModules"][0]["moduleId"] == "tests/t.py"


def test_write_test_json_atomic_no_tmp_leak(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry,
        TestModule,
        TestJSON,
        write_test_json,
    )

    j = TestJSON(
        test_modules=(
            TestModule(
                module_id="m",
                tests=(TestEntry(name="t", full_name="m::t", state="passed"),),
            ),
        ),
        reason="passed",
    )
    target = tmp_path / "test.json"
    write_test_json(j, target)
    # No *.tmp.<pid> file should remain.
    assert list(tmp_path.glob("*.tmp.*")) == []


def test_write_test_json_overwrites_existing(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry,
        TestModule,
        TestJSON,
        write_test_json,
    )

    target = tmp_path / "test.json"
    target.write_text('{"stale": true}', encoding="utf-8")
    j = TestJSON(
        test_modules=(
            TestModule(
                module_id="m",
                tests=(TestEntry(name="t", full_name="m::t", state="passed"),),
            ),
        ),
        reason="passed",
    )
    write_test_json(j, target)
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "stale" not in data
    assert data["reason"] == "passed"
