#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""End-to-end integration tests for the 9 subcomandos wired through run_sbtdd.

Covers BDD scenarios 13 (spec + close-phase x3), 18 (auto happy path),
19 (resume after quota exhaustion) and 17 (finalize rejects degraded
verdict). Tests consume the shared :mod:`tests.fixtures.skill_stubs`
fixture (Task 46a) so stub signatures stay canonical across the suite.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

# Import the fixture helpers here (imports at top of file per PEP 8 / E402).
from tests.fixtures.skill_stubs import StubMAGI, StubSuperpowers, make_verdict

_VALID_SPEC_BASE_BODY = "# Feature spec\n\n## Objetivo\nsomething meaningful\n" + (
    "valid content " * 50
)
_PLAN_ORG_BODY = (
    "# Plan\n\n### Task 1: First task\n\n- [ ] write the test\n- [ ] implement\n- [ ] refactor\n"
)


def _setup_git(tmp_path: Path) -> None:
    """Initialise a git repo at tmp_path with tester identity + initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    for key, value in (
        ("user.email", "tester@example.com"),
        ("user.name", "Tester"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "chore: seed"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into .claude/."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_spec_base(tmp_path: Path) -> None:
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    (spec_dir / "spec-behavior-base.md").write_text(_VALID_SPEC_BASE_BODY, encoding="utf-8")
    (tmp_path / "planning").mkdir()


@pytest.fixture
def bootstrapped_project(tmp_path, monkeypatch):
    """Tmp git repo with plugin.local.md + spec-base + skill stubs installed."""
    import magi_dispatch
    import superpowers_dispatch

    _setup_git(tmp_path)
    _seed_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)

    sp = StubSuperpowers()
    # Emulate artifacts produced by /brainstorming and /writing-plans.
    (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
        "# behavior\nsomething\n", encoding="utf-8"
    )

    def fake_brainstorming(args=None, timeout=600, cwd=None):
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\nContent\n", encoding="utf-8"
        )
        sp.calls.append(("brainstorming", list(args or []), cwd or ""))
        return None

    def fake_writing_plans(args=None, timeout=600, cwd=None):
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            _PLAN_ORG_BODY, encoding="utf-8"
        )
        sp.calls.append(("writing_plans", list(args or []), cwd or ""))
        return None

    def fake_noop(args=None, timeout=600, cwd=None):
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", fake_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", fake_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "test_driven_development", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "systematic_debugging", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "finishing_a_development_branch", fake_noop)

    magi = StubMAGI(sequence=[make_verdict("GO", degraded=False)])

    def fake_invoke_magi(context_paths, timeout=1800, cwd=None):
        return magi.invoke_magi(context_paths=list(context_paths), cwd=cwd or "", timeout=timeout)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    return tmp_path


def _stage_scratch_change(root: Path, name: str, content: str) -> None:
    """Write a file inside the project and stage it so git commit has something to commit."""
    scratch = root / name
    scratch.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=str(root), check=True, capture_output=True)


def test_spec_then_three_close_phase_end_to_end(bootstrapped_project, monkeypatch):
    """Scenario 13 end-to-end: spec approves plan, then 3 close-phase cycles complete task 1.

    Uses ``close_task_cmd.mark_and_advance`` (the public helper per iter-2 W1)
    in place of ``close_task_cmd.main`` in the cascade: the main() path re-runs
    drift detection, which legitimately flags ``state=refactor + HEAD=refactor:``
    as "close already landed but state not advanced". In the cascade context
    this IS the intermediate pre-advance state, which :func:`mark_and_advance`
    consumes directly (same path auto_cmd uses to side-step the spurious flag).
    """
    import close_task_cmd
    import run_sbtdd

    def cascade_without_drift_check(argv=None):
        from pathlib import Path as _Path

        from state_file import load as _load_state

        parsed_root = _Path(argv[argv.index("--project-root") + 1]) if argv else _Path.cwd()
        state = _load_state(parsed_root / ".claude" / "session-state.json")
        close_task_cmd.mark_and_advance(state, parsed_root)
        return 0

    monkeypatch.setattr(close_task_cmd, "main", cascade_without_drift_check)

    # Run spec -- stubs write spec-behavior.md + plan-org.md, MAGI returns GO.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    state_path = bootstrapped_project / ".claude" / "session-state.json"
    assert state_path.exists(), "spec should create session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_phase"] == "red"
    assert state["plan_approved_at"] is not None

    # Red close: stage a scratch test file, then close-phase.
    _stage_scratch_change(bootstrapped_project, "tests_scratch_red.py", "# red stub\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--message",
            "red phase for task 1",
        ]
    )
    assert rc == 0

    # Green close with --variant feat.
    _stage_scratch_change(bootstrapped_project, "impl_scratch.py", "# green stub\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--variant",
            "feat",
            "--message",
            "green phase for task 1",
        ]
    )
    assert rc == 0

    # Refactor close -- cascades into close-task bookkeeping.
    _stage_scratch_change(bootstrapped_project, "impl_scratch.py", "# refactored\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--message",
            "refactor phase for task 1",
        ]
    )
    assert rc == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_phase"] == "done"
    assert state["current_task_id"] is None
