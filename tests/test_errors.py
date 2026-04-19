"""Tests for skills/sbtdd/scripts/errors.py — exception hierarchy."""

from __future__ import annotations

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


def test_state_file_error_derives_from_sbtdd():
    from errors import SBTDDError, StateFileError

    assert issubclass(StateFileError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise StateFileError("corrupt JSON")


def test_drift_error_derives_from_sbtdd():
    from errors import DriftError, SBTDDError

    assert issubclass(DriftError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise DriftError("state vs git mismatch")


def test_dependency_error_derives_from_sbtdd():
    from errors import DependencyError, SBTDDError

    assert issubclass(DependencyError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise DependencyError("tdd-guard not in PATH")
