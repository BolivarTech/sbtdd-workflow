# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd close-task subcomando (sec.S.5.4)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_close_task_cmd_module_importable() -> None:
    import close_task_cmd

    assert hasattr(close_task_cmd, "main")
    assert hasattr(close_task_cmd, "run")


def test_close_task_cmd_help_exits_zero() -> None:
    import close_task_cmd

    with pytest.raises(SystemExit) as ei:
        close_task_cmd.main(["--help"])
    assert ei.value.code == 0


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str,
    plan_fixture: str = "three-tasks-mixed.md",
    current_task_id: str = "2",
    current_task_title: str = "Second task (in-progress)",
) -> None:
    """Seed ``.claude/session-state.json`` + ``planning/claude-plan-tdd.md``."""
    claude = tmp_path / ".claude"
    claude.mkdir()
    planning = tmp_path / "planning"
    planning.mkdir()
    fixtures_root = Path(__file__).parent / "fixtures"
    shutil.copy(
        fixtures_root / "plans" / plan_fixture,
        planning / "claude-plan-tdd.md",
    )
    payload = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": current_task_id,
        "current_task_title": current_task_title,
        "current_phase": current_phase,
        "phase_started_at_commit": "abc1234",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": "2026-04-19T10:00:00Z",
    }
    (claude / "session-state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_close_task_aborts_when_state_missing(tmp_path: Path) -> None:
    import close_task_cmd
    from errors import PreconditionError

    with pytest.raises(PreconditionError):
        close_task_cmd.main(["--project-root", str(tmp_path)])


def test_close_task_aborts_when_phase_not_refactor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd
    from errors import PreconditionError

    _seed_state(tmp_path, current_phase="green")
    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)
    with pytest.raises(PreconditionError) as ei:
        close_task_cmd.main(["--project-root", str(tmp_path)])
    msg = str(ei.value)
    assert "refactor" in msg
    assert "green" in msg


def test_close_task_aborts_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import close_task_cmd
    from drift import DriftReport
    from errors import DriftError

    _seed_state(tmp_path, current_phase="refactor")

    def fake_drift(*a, **k):  # type: ignore[no-untyped-def]
        return DriftReport(
            state_value="refactor",
            git_value="feat",
            plan_value="[ ]",
            reason="synthetic",
        )

    monkeypatch.setattr("close_task_cmd.detect_drift", fake_drift)
    with pytest.raises(DriftError):
        close_task_cmd.main(["--project-root", str(tmp_path)])


def _install_happy_path_patches(
    monkeypatch: pytest.MonkeyPatch, captured: dict[str, object]
) -> None:
    """Patch drift + git rev-parse + commits.create for happy-path tests.

    Collects side-effects into ``captured`` so tests can assert on them:
    - ``commit_calls``: list of ``(prefix, message)`` tuples.
    - ``new_sha``: short SHA returned by rev-parse.
    """
    captured.setdefault("commit_calls", [])
    captured.setdefault("new_sha", "f00dcafe")

    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)

    def fake_run(cmd: list[str], timeout: int = 0, cwd: str | None = None):  # type: ignore[no-untyped-def]
        # git add ... and git rev-parse --short HEAD both route through here.
        if "rev-parse" in cmd:
            return SimpleNamespace(returncode=0, stdout=str(captured["new_sha"]) + "\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("close_task_cmd.subprocess_utils.run_with_timeout", fake_run)

    def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
        calls = captured["commit_calls"]
        assert isinstance(calls, list)
        calls.append((prefix, message))
        return ""

    monkeypatch.setattr("close_task_cmd.commit_create", fake_commit)


def test_close_task_flips_checkbox_in_plan_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    plan_text = (tmp_path / "planning" / "claude-plan-tdd.md").read_text(encoding="utf-8")
    # Task 2 section should now have [x] for all steps.
    task2_idx = plan_text.index("### Task 2:")
    task3_idx = plan_text.index("### Task 3:")
    task2_section = plan_text[task2_idx:task3_idx]
    assert "- [ ]" not in task2_section
    assert "- [x] Step 1" in task2_section
    assert "- [x] Step 2" in task2_section
    # Task 3 untouched
    task3_section = plan_text[task3_idx:]
    assert "- [ ] Step 1" in task3_section


def test_close_task_creates_chore_commit_with_task_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert len(calls) == 1
    prefix, message = calls[0]
    assert prefix == "chore"
    assert message == "mark task 2 complete"


def test_close_task_chore_commit_contains_only_plan_edit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify only `git add <plan>` ran before commit_create (no extra adds)."""
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    captured["git_add_args"] = []

    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)

    def fake_run(cmd: list[str], timeout: int = 0, cwd: str | None = None):  # type: ignore[no-untyped-def]
        if cmd[:2] == ["git", "add"]:
            ga = captured["git_add_args"]
            assert isinstance(ga, list)
            ga.append(cmd[2:])
        if "rev-parse" in cmd:
            return SimpleNamespace(returncode=0, stdout="f00dcafe\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("close_task_cmd.subprocess_utils.run_with_timeout", fake_run)
    monkeypatch.setattr("close_task_cmd.commit_create", lambda prefix, message, cwd=None: "")

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    ga = captured["git_add_args"]
    assert isinstance(ga, list)
    # Exactly one `git add` with exactly one path: the plan.
    assert len(ga) == 1
    assert len(ga[0]) == 1
    assert Path(ga[0][0]).as_posix().endswith("planning/claude-plan-tdd.md")


def test_close_task_advances_state_when_next_task_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")  # task 2 refactor, task 3 pending
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] == "3"
    assert state["current_task_title"] == "Third task (pending)"
    assert state["current_phase"] == "red"


def test_close_task_closes_plan_when_no_next_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd

    # Use a 2-task plan where task 2 is the only remaining open task.
    claude = tmp_path / ".claude"
    claude.mkdir()
    planning = tmp_path / "planning"
    planning.mkdir()
    plan_text = (
        "# Single-open plan\n\n"
        "### Task 1: First (done)\n\n- [x] step\n\n"
        "### Task 2: Second (open, last)\n\n- [ ] step\n"
    )
    (planning / "claude-plan-tdd.md").write_text(plan_text, encoding="utf-8")
    payload = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "2",
        "current_task_title": "Second (open, last)",
        "current_phase": "refactor",
        "phase_started_at_commit": "abc1234",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": "2026-04-19T10:00:00Z",
    }
    (claude / "session-state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] is None
    assert state["current_task_title"] is None
    assert state["current_phase"] == "done"


def test_close_task_updates_phase_started_at_commit_to_chore_sha(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {"new_sha": "deadbee"}
    _install_happy_path_patches(monkeypatch, captured)

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["phase_started_at_commit"] == "deadbee"


def test_mark_and_advance_skips_commit_when_plan_already_fully_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """flip_task_checkboxes no-op -> skip git add/commit, still advance state.

    Regression for the 2026-04-24 edge case: if the implementer subagent
    has already flipped ``- [ ]`` -> ``- [x]`` inside the current task
    section as part of its phase work, ``flip_task_checkboxes`` returns
    identical bytes. The previous code unconditionally ran ``os.replace``
    + ``git add`` + ``commit_create``, which produced a ``CommitError``
    (nothing to commit). Post-fix, mark_and_advance detects the no-op
    flip, skips the write/stage/commit, and still advances the session
    state so bookkeeping doesn't stall.
    """
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    # Pre-flip ONLY Task 2's section (leave Task 3 open) so
    # ``flip_task_checkboxes(text, "2")`` produces bytes-identical output.
    plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
    plan_text = plan_path.read_text(encoding="utf-8")
    task2_start = plan_text.index("### Task 2:")
    task3_start = plan_text.index("### Task 3:")
    pre_flipped = (
        plan_text[:task2_start]
        + plan_text[task2_start:task3_start].replace("- [ ]", "- [x]")
        + plan_text[task3_start:]
    )
    plan_path.write_text(pre_flipped, encoding="utf-8")

    captured: dict[str, object] = {"new_sha": "cafe123"}
    _install_happy_path_patches(monkeypatch, captured)
    from state_file import load as load_state

    state = load_state(tmp_path / ".claude" / "session-state.json")
    new_state = close_task_cmd.mark_and_advance(state, tmp_path)

    # Commit MUST NOT have been called because plan was a no-op flip.
    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert len(calls) == 0
    # State still advances to next task despite the skipped commit.
    assert new_state.current_task_id == "3"
    assert new_state.current_phase == "red"


def test_mark_and_advance_is_public_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Iter-2 W1 guard: ``mark_and_advance`` must be a public function.

    ``auto_cmd`` delegates to it rather than reaching into a private symbol.
    """
    import close_task_cmd
    from state_file import load as load_state

    assert hasattr(close_task_cmd, "mark_and_advance")
    assert callable(close_task_cmd.mark_and_advance)
    # No leading underscore on the identifier.
    assert not close_task_cmd.mark_and_advance.__name__.startswith("_")

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {"new_sha": "cafe123"}
    _install_happy_path_patches(monkeypatch, captured)

    state = load_state(tmp_path / ".claude" / "session-state.json")
    new_state = close_task_cmd.mark_and_advance(state, tmp_path)
    # Same 1-commit + advanced-state result as calling main().
    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert len(calls) == 1
    assert new_state.current_task_id == "3"
    assert new_state.current_phase == "red"
