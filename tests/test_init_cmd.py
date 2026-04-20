# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd init subcomando (sec.S.5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest


def test_init_cmd_module_importable() -> None:
    import init_cmd

    assert hasattr(init_cmd, "main")


def test_init_parses_stack_flag() -> None:
    import init_cmd

    with pytest.raises(SystemExit) as ei:
        init_cmd.main(["--help"])
    assert ei.value.code == 0


def test_init_rejects_invalid_stack() -> None:
    import init_cmd

    with pytest.raises(SystemExit):
        init_cmd.main(["--stack", "not-a-real-stack"])


def _make_broken_report() -> object:
    """Return a DependencyReport-like object whose .ok() is False."""
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(
            DependencyCheck(
                name="tdd-guard",
                status="MISSING",
                detail="binary not found in PATH",
                remediation="npm i -g tdd-guard",
            ),
        )
    )


def _make_ok_report() -> object:
    """Return a DependencyReport-like object whose .ok() is True."""
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(
            DependencyCheck(
                name="python",
                status="OK",
                detail="3.11.0",
                remediation=None,
            ),
        )
    )


def test_init_aborts_when_preflight_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import init_cmd
    from errors import DependencyError

    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_broken_report())
    with pytest.raises(DependencyError):
        init_cmd.main(
            [
                "--stack",
                "python",
                "--author",
                "Tester",
                "--project-root",
                str(tmp_path),
                "--plugins-root",
                str(tmp_path / "plugins"),
            ]
        )


def test_init_does_not_create_files_on_preflight_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import init_cmd
    from errors import DependencyError

    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_broken_report())
    with pytest.raises(DependencyError):
        init_cmd.main(
            [
                "--stack",
                "python",
                "--author",
                "Tester",
                "--project-root",
                str(tmp_path),
                "--plugins-root",
                str(tmp_path / "plugins"),
            ]
        )
    assert not (tmp_path / "CLAUDE.local.md").exists()
    assert not (tmp_path / ".claude" / "plugin.local.md").exists()


def test_init_aborts_when_stack_missing_non_interactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import init_cmd
    from errors import ValidationError

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    with pytest.raises(ValidationError):
        init_cmd.main(
            [
                "--author",
                "Tester",
                "--project-root",
                str(tmp_path),
                "--plugins-root",
                str(tmp_path / "plugins"),
            ]
        )
