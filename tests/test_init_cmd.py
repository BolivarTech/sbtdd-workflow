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


def _setup_dest_root(tmp_path: Path) -> Path:
    """Create a dest_root directory inside tmp_path."""
    dest = tmp_path / "dest"
    dest.mkdir()
    return dest


def test_init_creates_claude_local_md_with_author_and_stack(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Happy-path Phase 3a + downstream phases: CLAUDE.local.md lands in dest_root."""
    import init_cmd

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())
    rc = init_cmd.main(
        [
            "--stack",
            "python",
            "--author",
            "Julian Tester",
            "--project-root",
            str(dest),
            "--plugins-root",
            str(tmp_path / "plugins"),
        ]
    )
    assert rc == 0
    text = (dest / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "Julian Tester" in text
    assert "python" in text
    assert "pytest" in text


def test_init_creates_plugin_local_md_with_valid_yaml_frontmatter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import init_cmd
    from config import load_plugin_local

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())
    init_cmd.main(
        [
            "--stack",
            "python",
            "--author",
            "Julian Tester",
            "--project-root",
            str(dest),
            "--plugins-root",
            str(tmp_path / "plugins"),
        ]
    )
    cfg = load_plugin_local(dest / ".claude" / "plugin.local.md")
    assert cfg.stack == "python"
    assert cfg.author == "Julian Tester"


def test_init_phase3a_writes_only_to_tempdir_not_dest_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """At the instant Phase 4 runs, dest_root is still untouched."""
    import init_cmd
    from errors import PreconditionError

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())

    observed: dict[str, bool] = {"ran": False}

    def fake_smoke(staging: Path) -> None:
        # At this point Phase 3a (+ 3b) have written to staging,
        # and dest_root must still be bare.
        assert (staging / "CLAUDE.local.md").exists()
        assert (staging / ".claude" / "plugin.local.md").exists()
        assert not (dest / "CLAUDE.local.md").exists()
        assert not (dest / ".claude" / "plugin.local.md").exists()
        observed["ran"] = True
        raise PreconditionError("stop-before-phase-5")

    monkeypatch.setattr(init_cmd, "_phase4_smoke_test", fake_smoke)
    with pytest.raises(PreconditionError):
        init_cmd.main(
            [
                "--stack",
                "python",
                "--author",
                "Julian Tester",
                "--project-root",
                str(dest),
                "--plugins-root",
                str(tmp_path / "plugins"),
            ]
        )
    assert observed["ran"] is True
    # After the abort, dest_root remains bare.
    assert not (dest / "CLAUDE.local.md").exists()
    assert not (dest / ".claude" / "plugin.local.md").exists()
