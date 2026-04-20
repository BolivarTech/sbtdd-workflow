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


def test_all_nine_subclasses_exist():
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
        "Loop1DivergentError",
    }
    actual = {name for name in dir(errors) if name.endswith("Error") and name != "SBTDDError"}
    assert expected == actual, f"mismatch: expected {expected}, got {actual}"


def test_loop1_divergent_error_derives_from_sbtdd():
    from errors import Loop1DivergentError, SBTDDError

    assert issubclass(Loop1DivergentError, SBTDDError)
    with pytest.raises(SBTDDError):
        raise Loop1DivergentError("did not converge")


def test_loop1_divergent_error_exit_code_is_7():
    from errors import EXIT_CODES, Loop1DivergentError

    assert EXIT_CODES[Loop1DivergentError] == 7


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


def test_exit_codes_mapping_covers_all_subclasses():
    """EXIT_CODES must map every SBTDDError subclass to its exit code.

    Per MAGI Loop 2 Finding 7: codify the exception -> exit code
    mapping in errors.py so dispatchers (run_sbtdd.py, *_cmd.py) have
    a single source of truth aligned with spec sec.S.11.1 taxonomy.
    """
    from errors import (
        EXIT_CODES,
        CommitError,
        DependencyError,
        DriftError,
        Loop1DivergentError,
        MAGIGateError,
        PreconditionError,
        QuotaExhaustedError,
        StateFileError,
        ValidationError,
    )

    expected_classes = {
        ValidationError,
        StateFileError,
        DriftError,
        DependencyError,
        PreconditionError,
        MAGIGateError,
        QuotaExhaustedError,
        CommitError,
        Loop1DivergentError,
    }
    assert set(EXIT_CODES.keys()) == expected_classes


def test_exit_codes_match_canonical_taxonomy():
    """Canonical sec.S.11.1 exit code mapping is enforced."""
    from errors import (
        EXIT_CODES,
        CommitError,
        DependencyError,
        DriftError,
        MAGIGateError,
        PreconditionError,
        QuotaExhaustedError,
        StateFileError,
        ValidationError,
    )

    # Canonical per sec.S.11.1 + CLAUDE.md "Key Design Decisions":
    assert EXIT_CODES[ValidationError] == 1
    assert EXIT_CODES[StateFileError] == 1
    assert EXIT_CODES[CommitError] == 1
    assert EXIT_CODES[DependencyError] == 2
    assert EXIT_CODES[PreconditionError] == 2
    assert EXIT_CODES[DriftError] == 3
    assert EXIT_CODES[MAGIGateError] == 8
    assert EXIT_CODES[QuotaExhaustedError] == 11


def test_exit_codes_is_read_only():
    """EXIT_CODES is MappingProxyType -- mutation must raise TypeError."""
    from errors import EXIT_CODES, ValidationError

    with pytest.raises(TypeError):
        EXIT_CODES[ValidationError] = 99  # type: ignore[index]


def test_mro_is_flat_single_inheritance():
    """All subclasses inherit directly from SBTDDError (no diamond)."""
    from errors import (
        CommitError,
        DependencyError,
        DriftError,
        Loop1DivergentError,
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
        Loop1DivergentError,
    ]
    for cls in subclasses:
        assert cls.__mro__[1] is SBTDDError, f"{cls.__name__} MRO skips SBTDDError"
