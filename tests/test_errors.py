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


def test_precondition_error_derives_from_sbtdd():
    from errors import PreconditionError, SBTDDError

    assert issubclass(PreconditionError, SBTDDError)


def test_magi_gate_error_derives_from_sbtdd():
    from errors import MAGIGateError, SBTDDError

    assert issubclass(MAGIGateError, SBTDDError)


def test_quota_exhausted_error_derives_from_sbtdd():
    from errors import QuotaExhaustedError, SBTDDError

    assert issubclass(QuotaExhaustedError, SBTDDError)


def test_all_eight_subclasses_exist():
    import errors

    expected = {
        "ValidationError",
        "StateFileError",
        "DriftError",
        "DependencyError",
        "PreconditionError",
        "MAGIGateError",
        "QuotaExhaustedError",
        "CommitError",
    }
    actual = {name for name in dir(errors) if name.endswith("Error") and name != "SBTDDError"}
    assert expected == actual, f"mismatch: expected {expected}, got {actual}"


def test_commit_error_derives_from_sbtdd():
    from errors import CommitError, SBTDDError

    assert issubclass(CommitError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise CommitError("git commit failed")


def test_non_matching_subclass_not_caught():
    """Catching a specific subclass must not intercept a sibling subclass."""
    from errors import DriftError, MAGIGateError

    with pytest.raises(MAGIGateError):
        try:
            raise MAGIGateError("strong no-go")
        except DriftError:
            pytest.fail("DriftError catch must not intercept MAGIGateError")


def test_mro_is_flat_single_inheritance():
    """All subclasses inherit directly from SBTDDError (no diamond)."""
    from errors import (
        CommitError,
        DependencyError,
        DriftError,
        MAGIGateError,
        PreconditionError,
        QuotaExhaustedError,
        SBTDDError,
        StateFileError,
        ValidationError,
    )

    subclasses = [
        ValidationError,
        StateFileError,
        DriftError,
        DependencyError,
        PreconditionError,
        MAGIGateError,
        QuotaExhaustedError,
        CommitError,
    ]
    for cls in subclasses:
        assert cls.__mro__[1] is SBTDDError, f"{cls.__name__} MRO skips SBTDDError"
