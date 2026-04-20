# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for ctest_reporter empty-XML handling (Plan D Task 8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from errors import ValidationError
from reporters import ctest_reporter


_EMPTY_FIXTURE = Path("tests/fixtures/junit-xml/empty.xml")
_MALFORMED_FIXTURE = Path("tests/fixtures/junit-xml/malformed.xml")


def test_parse_junit_on_empty_file_raises_validation_error(tmp_path: Path) -> None:
    # Use the fixture directly -- 0-byte file.
    with pytest.raises(ValidationError) as exc:
        ctest_reporter.parse_junit(_EMPTY_FIXTURE)
    # Message must make it obvious the file was empty, not generically
    # "malformed".
    assert "empty" in str(exc.value).lower() or "0 bytes" in str(exc.value)


def test_parse_junit_on_malformed_file_raises_validation_error() -> None:
    with pytest.raises(ValidationError) as exc:
        ctest_reporter.parse_junit(_MALFORMED_FIXTURE)
    # Malformed is distinguishable from empty -- we want the caller to
    # see a different reason.
    assert "empty" not in str(exc.value).lower()
    assert "invalid" in str(exc.value).lower() or "parse" in str(exc.value).lower()


def test_parse_junit_on_nonexistent_file_raises_validation_error(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "nope.xml"
    with pytest.raises(ValidationError) as exc:
        ctest_reporter.parse_junit(missing)
    assert "not found" in str(exc.value).lower() or "does not exist" in str(
        exc.value
    ).lower()


def test_run_wraps_empty_file(tmp_path: Path) -> None:
    target = tmp_path / "test.json"
    with pytest.raises(ValidationError):
        ctest_reporter.run(_EMPTY_FIXTURE, target)
    assert not target.exists()
