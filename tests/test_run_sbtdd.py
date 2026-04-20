from __future__ import annotations

import pytest


def test_main_rejects_unknown_subcommand(capsys):
    from run_sbtdd import main

    code = main(["unknown-sub"])
    assert code == 1
    out = capsys.readouterr()
    assert "unknown" in (out.err + out.out).lower() or "invalid" in (out.err + out.out).lower()


def test_main_rejects_empty_argv(capsys):
    from run_sbtdd import main

    code = main([])
    assert code == 1


def test_main_accepts_all_nine_valid_subcommands(monkeypatch):
    """Dispatch succeeds (returns 0) for each name in VALID_SUBCOMMANDS when stub is installed."""
    import run_sbtdd
    from models import VALID_SUBCOMMANDS

    for sub in VALID_SUBCOMMANDS:
        monkeypatch.setitem(run_sbtdd.SUBCOMMAND_DISPATCH, sub, lambda argv: 0)
        assert run_sbtdd.main([sub]) == 0


def test_main_maps_validation_error_to_exit_1(monkeypatch):
    from errors import ValidationError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise ValidationError("bad input")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "init", raising)
    assert main(["init"]) == 1


def test_main_maps_dependency_error_to_exit_2(monkeypatch):
    from errors import DependencyError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise DependencyError("missing")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "init", raising)
    assert main(["init"]) == 2


def test_main_maps_drift_error_to_exit_3(monkeypatch):
    from errors import DriftError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise DriftError("drift")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "status", raising)
    assert main(["status"]) == 3


def test_main_maps_magi_gate_error_to_exit_8(monkeypatch):
    from errors import MAGIGateError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise MAGIGateError("STRONG_NO_GO")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "pre-merge", raising)
    assert main(["pre-merge"]) == 8


def test_main_maps_quota_exhausted_error_to_exit_11(monkeypatch):
    from errors import QuotaExhaustedError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise QuotaExhaustedError("rate limit")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "spec", raising)
    assert main(["spec"]) == 11


def test_main_maps_keyboard_interrupt_to_exit_130(monkeypatch):
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    def raising(argv):
        raise KeyboardInterrupt()

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "auto", raising)
    assert main(["auto"]) == 130


def test_main_maps_unknown_sbtdd_error_to_exit_1(monkeypatch):
    """Unknown SBTDDError subclass (not in EXIT_CODES) falls back to exit 1."""
    from errors import SBTDDError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    class UnmappedError(SBTDDError):
        pass

    def raising(argv):
        raise UnmappedError("unknown")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "status", raising)
    assert main(["status"]) == 1


def test_main_walks_mro_for_derived_sbtdd_errors(monkeypatch):
    """Subclass of a registered SBTDDError inherits the ancestor's exit code.

    MAGI Loop 2 Milestone B iter 1 Finding 1 (melchior): ``_exit_code_for``
    must walk ``type(exc).__mro__`` rather than doing a direct ``type(exc)``
    lookup -- otherwise future-added subclasses of the registered errors
    (eg. ``DerivedDriftError(DriftError)``) silently fall to the default
    exit 1 instead of inheriting the ancestor's code (3 in this case).
    """
    from errors import DriftError
    from run_sbtdd import SUBCOMMAND_DISPATCH, main

    class DerivedDriftError(DriftError):
        """Hypothetical future subclass -- must still exit 3, not default 1."""

    def raising(argv):
        raise DerivedDriftError("drifted further")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "status", raising)
    assert main(["status"]) == 3


def test_dispatch_table_has_all_nine_subcommands():
    from models import VALID_SUBCOMMANDS
    from run_sbtdd import SUBCOMMAND_DISPATCH

    assert set(SUBCOMMAND_DISPATCH.keys()) == set(VALID_SUBCOMMANDS)


def test_all_default_handlers_raise_not_implemented_validation_error():
    """Default handlers raise ValidationError pending Milestone C+ implementation."""
    from errors import ValidationError
    from run_sbtdd import _default_handler_factory

    handler = _default_handler_factory("init")
    with pytest.raises(ValidationError, match="not yet implemented"):
        handler([])
