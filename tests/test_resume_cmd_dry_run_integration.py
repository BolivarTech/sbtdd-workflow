# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Pin resume --dry-run end-to-end zero-side-effects behaviour (Plan D Task 11).

Regression-pinning test (no Red phase) over the behaviour produced by
Tasks 9 + 10 -- validates the user-facing contract once those tasks are
green. Per CLAUDE.local.md sec.3 and Plans A-C precedent, commit uses
``test:`` per sec.M.5 row 1.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import resume_cmd


def _snapshot_dir(root: Path) -> dict[str, str]:
    """Return {relpath: sha256} for every file under root."""
    result: dict[str, str] = {}
    for p in root.rglob("*"):
        if p.is_file():
            result[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


@pytest.fixture()
def interrupted_auto_project(tmp_path: Path) -> Path:
    subprocess.run(
        ["git", "init", "--initial-branch", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.io",
            "-c",
            "user.name=t",
            "commit",
            "--allow-empty",
            "-m",
            "init",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "plugin.local.md").write_text(
        "---\nstack: python\n---\n", encoding="utf-8"
    )
    (tmp_path / ".claude" / "session-state.json").write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": "2",
                "current_task_title": "T2",
                "current_phase": "green",
                "phase_started_at_commit": "abc1234",
                "last_verification_at": "2026-04-19T16:30:00Z",
                "last_verification_result": "passed",
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / ".claude" / "auto-run.json").write_text(
        json.dumps({"auto_started_at": "2026-04-19T10:00:00Z"}),
        encoding="utf-8",
    )
    (tmp_path / "planning").mkdir()
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text(
        "### Task 1: first\n- [x] step\n\n### Task 2: second\n- [ ] step\n",
        encoding="utf-8",
    )
    # Dirty tree: create an untracked file.
    (tmp_path / "scratch.txt").write_text("wip\n", encoding="utf-8")
    return tmp_path


def test_dry_run_has_zero_side_effects(
    interrupted_auto_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = interrupted_auto_project
    monkeypatch.setattr(resume_cmd, "_recheck_environment", lambda root: None)
    pre = _snapshot_dir(root)
    rc = resume_cmd.main(["--project-root", str(root), "--dry-run"])
    post = _snapshot_dir(root)
    assert rc == 0
    assert pre == post, f"dry-run mutated filesystem: {set(pre) ^ set(post)}"


def test_dry_run_prints_delegation_target(
    interrupted_auto_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(resume_cmd, "_recheck_environment", lambda root: None)
    resume_cmd.main(["--project-root", str(interrupted_auto_project), "--dry-run"])
    captured = capsys.readouterr()
    # With phase=green + tree_dirty=True, decision tree returns
    # uncommitted-resolution. --dry-run prints "Would delegate to:
    # uncommitted-resolution" and returns without acting.
    assert "uncommitted-resolution" in captured.out or "CONTINUE" in captured.out


def test_dry_run_clean_tree_delegates_to_auto(
    interrupted_auto_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Remove scratch.txt and commit everything else so the tree is
    # genuinely clean (not merely minus-one-file). Without this, the
    # fixture's unconfigured .claude/ + planning/ dirs remain untracked
    # and `git status --short` still reports DIRTY.
    (interrupted_auto_project / "scratch.txt").unlink()
    # Ignore .claude/ (session state is local by policy).
    (interrupted_auto_project / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    subprocess.run(
        ["git", "-c", "user.email=t@t.io", "-c", "user.name=t", "add", "-A"],
        cwd=interrupted_auto_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@t.io",
            "-c",
            "user.name=t",
            "commit",
            "-m",
            "seed",
        ],
        cwd=interrupted_auto_project,
        check=True,
        capture_output=True,
    )
    monkeypatch.setattr(resume_cmd, "_recheck_environment", lambda root: None)
    rc = resume_cmd.main(["--project-root", str(interrupted_auto_project), "--dry-run"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "auto_cmd" in captured.out
    assert "Would delegate" in captured.out
