# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Integration test: pre-merge exit 8 -> resume conditions-pending (Plan D Task 13).

Regression-pinning test (no Red phase) over the user journey built in
Tasks 9 + 12. Per CLAUDE.local.md sec.3, commit uses ``test:`` per
sec.M.5 row 1.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import magi_dispatch
import pre_merge_cmd
import resume_cmd
import superpowers_dispatch
from errors import MAGIGateError


@pytest.fixture()
def project(tmp_path: Path) -> Path:
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
        "---\n"
        "stack: python\n"
        'author: "Julian Bolivar"\n'
        "error_type: null\n"
        "verification_commands:\n"
        '  - "pytest"\n'
        '  - "ruff check ."\n'
        '  - "ruff format --check ."\n'
        '  - "mypy ."\n'
        'plan_path: "planning/claude-plan-tdd.md"\n'
        'plan_org_path: "planning/claude-plan-tdd-org.md"\n'
        'spec_base_path: "sbtdd/spec-behavior-base.md"\n'
        'spec_path: "sbtdd/spec-behavior.md"\n'
        'state_file_path: ".claude/session-state.json"\n'
        'magi_threshold: "GO_WITH_CAVEATS"\n'
        "magi_max_iterations: 3\n"
        "auto_magi_max_iterations: 5\n"
        "auto_verification_retries: 1\n"
        "tdd_guard_enabled: true\n"
        'worktree_policy: "optional"\n'
        "---\n",
    )
    (tmp_path / "planning").mkdir()
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("### Task 1:\n- [x]\n")
    (tmp_path / ".claude" / "session-state.json").write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": None,
                "current_task_title": None,
                "current_phase": "done",
                "phase_started_at_commit": "abc1234",
                "last_verification_at": "2026-04-19T16:30:00Z",
                "last_verification_result": "passed",
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        )
    )
    return tmp_path


def test_pre_merge_exit8_then_resume_directs_to_close_phase(
    project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Step 1: pre-merge hits exit 8 -> writes magi-conditions.md.
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)
    monkeypatch.setattr(pre_merge_cmd, "_preflight", lambda root: None)

    class V:
        conditions = ("Refactor X",)
        verdict = "GO_WITH_CAVEATS"
        degraded = False

    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, cwd: V(),
    )
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda v: False)
    monkeypatch.setattr(
        pre_merge_cmd,
        "_parse_receiving_review",
        lambda r: (["Refactor X"], []),
    )
    monkeypatch.setattr(
        superpowers_dispatch,
        "receiving_code_review",
        lambda args, cwd: {},
    )
    monkeypatch.setattr(
        pre_merge_cmd,
        "_conditions_to_skill_args",
        lambda cs: list(cs),
    )
    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(project)])
    assert (project / ".claude" / "magi-conditions.md").exists()

    # Step 2: resume detects magi-conditions.md -> exit 0 with instructions.
    monkeypatch.setattr(resume_cmd, "_recheck_environment", lambda root: None)
    rc = resume_cmd.main(["--project-root", str(project)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "magi-conditions.md" in captured.out
    assert "close-phase" in captured.out
