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


def _run_init(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    dest: Path,
    *,
    stack: str = "python",
    extra_args: tuple[str, ...] = (),
) -> None:
    import init_cmd

    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())
    args = [
        "--stack",
        stack,
        "--author",
        "Julian Tester",
        "--project-root",
        str(dest),
        "--plugins-root",
        str(tmp_path / "plugins"),
    ]
    args.extend(extra_args)
    init_cmd.main(args)


def test_init_merges_settings_json_preserving_user_hooks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    dest = _setup_dest_root(tmp_path)
    (dest / ".claude").mkdir()
    existing = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write", "hooks": [{"type": "command", "command": "eslint"}]}
            ]
        }
    }
    (dest / ".claude" / "settings.json").write_text(json.dumps(existing), encoding="utf-8")

    _run_init(tmp_path, monkeypatch, dest)

    merged = json.loads((dest / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hooks_list = merged["hooks"]["PreToolUse"]
    commands = [entry["hooks"][0]["command"] for entry in hooks_list]
    assert "eslint" in commands
    assert "tdd-guard" in commands


def test_init_creates_spec_behavior_base_md_skeleton(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The skeleton MUST NOT contain INV-27 uppercase pending markers."""
    import re

    dest = _setup_dest_root(tmp_path)
    _run_init(tmp_path, monkeypatch, dest)
    text = (dest / "sbtdd" / "spec-behavior-base.md").read_text(encoding="utf-8")
    # INV-27 forbids TODO/TODOS/TBD uppercase word tokens in the generated skeleton.
    assert not re.search(r"\b(TODO|TODOS|TBD)\b", text)


def test_init_appends_gitignore_fragment_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = _setup_dest_root(tmp_path)
    _run_init(tmp_path, monkeypatch, dest, extra_args=("--force",))
    _run_init(tmp_path, monkeypatch, dest, extra_args=("--force",))
    text = (dest / ".gitignore").read_text(encoding="utf-8")
    assert text.count(".claude/") == 1
    assert text.count("CLAUDE.local.md") == 1


def test_init_creates_planning_gitkeep(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest = _setup_dest_root(tmp_path)
    _run_init(tmp_path, monkeypatch, dest)
    assert (dest / "planning" / ".gitkeep").exists()


def test_init_python_stack_writes_conftest_py(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dest = _setup_dest_root(tmp_path)
    _run_init(tmp_path, monkeypatch, dest, extra_args=("--conftest-mode", "merge"))
    text = (dest / "conftest.py").read_text(encoding="utf-8")
    assert "# --- SBTDD TDD-Guard reporter START ---" in text


def test_init_phase3b_writes_only_to_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before Phase 4 runs, dest_root has no Phase 3b artifacts."""
    import init_cmd
    from errors import PreconditionError

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())

    def fake_smoke(staging: Path) -> None:
        assert (staging / ".claude" / "settings.json").exists()
        assert (staging / "sbtdd" / "spec-behavior-base.md").exists()
        assert (staging / "planning" / ".gitkeep").exists()
        assert (staging / "conftest.py").exists()
        assert not (dest / ".claude" / "settings.json").exists()
        assert not (dest / "sbtdd" / "spec-behavior-base.md").exists()
        assert not (dest / "planning" / ".gitkeep").exists()
        assert not (dest / "conftest.py").exists()
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
    assert not (dest / ".claude" / "settings.json").exists()
    assert not (dest / "conftest.py").exists()


def test_init_smoke_test_rejects_invalid_settings_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Corrupt settings.json in staging aborts Phase 4 and rolls back."""
    import init_cmd
    from errors import PreconditionError

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())

    original_phase3b = init_cmd._phase3b_install

    def corrupt_phase3b(ns, staging: Path, dest_root: Path) -> None:
        original_phase3b(ns, staging, dest_root)
        (staging / ".claude" / "settings.json").write_text("{not valid json", encoding="utf-8")

    monkeypatch.setattr(init_cmd, "_phase3b_install", corrupt_phase3b)
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
    # Rollback contract: dest_root has nothing.
    assert not (dest / ".claude" / "settings.json").exists()
    assert not (dest / "CLAUDE.local.md").exists()


def test_init_smoke_test_validates_plugin_local_md(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 4 runs ``load_plugin_local`` against the staged file."""
    import init_cmd

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())

    seen_paths: list[Path] = []

    original = init_cmd.load_plugin_local

    def tracker(path: Path | str):  # type: ignore[no-untyped-def]
        seen_paths.append(Path(path))
        return original(path)

    monkeypatch.setattr(init_cmd, "load_plugin_local", tracker)
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
    # Called against staged plugin.local.md (not dest_root path).
    assert any("sbtdd-init-" in str(p) for p in seen_paths)


def test_init_phase5_reports_all_ok_components(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import init_cmd

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
    out = capsys.readouterr().out
    assert "[ok]" in out
    assert "Created:" in out


def test_init_exit_0_on_full_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_init_rollback_on_smoke_test_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 4 failure leaves dest_root byte-identical to its pre-invocation state."""
    import init_cmd
    from errors import PreconditionError

    dest = _setup_dest_root(tmp_path)
    monkeypatch.setattr(init_cmd, "check_environment", lambda *a, **kw: _make_ok_report())

    staging_captured: dict[str, Path] = {}

    def forced_failure(staging: Path) -> None:
        staging_captured["path"] = staging
        raise PreconditionError("smoke test forced failure")

    monkeypatch.setattr(init_cmd, "_phase4_smoke_test", forced_failure)
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
    assert not (dest / "CLAUDE.local.md").exists()
    assert not (dest / ".claude" / "settings.json").exists()
    assert not (dest / "sbtdd" / "spec-behavior-base.md").exists()
    # Staging must have been cleaned up.
    assert "path" in staging_captured
    assert not staging_captured["path"].exists()


def test_init_phase5_relocate_rolls_back_partial_copy_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAGI Loop 2 iter 1 Finding 3: mid-copy failure removes partial files.

    ``_phase5_relocate`` copies the staging tree into ``dest_root`` file by
    file with ``shutil.copy2``. If the process dies midway (disk full,
    permission denied on N-th file, etc.), the pre-fix implementation
    left a partial tree in ``dest_root``. Post-fix contract: on ANY
    per-file copy failure the helper best-effort removes every file it
    already copied, then re-raises. True atomicity across volumes is
    impossible without ``os.rename``; this is "best effort atomicity
    with rollback" -- sufficient because a subsequent ``/sbtdd init``
    invocation sees a clean dest_root and can retry cleanly.
    """
    import shutil as _shutil

    import init_cmd

    # Build a minimal staging tree with several files so the copy loop
    # has something to fail partway through.
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "a.txt").write_text("a", encoding="utf-8")
    (staging / "b.txt").write_text("b", encoding="utf-8")
    nested = staging / "sub"
    nested.mkdir()
    (nested / "c.txt").write_text("c", encoding="utf-8")
    (nested / "d.txt").write_text("d", encoding="utf-8")

    dest = tmp_path / "dest"
    dest.mkdir()

    # Monkeypatch shutil.copy2 to succeed for the first 2 files, then
    # fail. The rollback must remove both already-copied files.
    original_copy2 = _shutil.copy2
    call_counter = {"n": 0}

    def flaky_copy2(src: str, dst: str, *a: object, **kw: object) -> object:
        call_counter["n"] += 1
        if call_counter["n"] >= 3:
            raise OSError("simulated disk full")
        return original_copy2(src, dst, *a, **kw)

    monkeypatch.setattr(init_cmd.shutil, "copy2", flaky_copy2)

    with pytest.raises(OSError, match="simulated disk full"):
        init_cmd._phase5_relocate(staging, dest)

    # Rollback invariant: no new files must remain under dest_root.
    surviving = [p for p in dest.rglob("*") if p.is_file()]
    assert surviving == [], f"rollback left partial files behind: {surviving}"
