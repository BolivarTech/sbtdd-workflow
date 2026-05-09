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

    v1.0.5 Item D Q3-A: also monkeypatches ``_preflight_triplet_check``
    to a no-op so the happy-path tests (which run against ``tmp_path``
    with no real git history) bypass the new HARD-BLOCK introduced in
    Task 4. Tests that exercise the preflight gate explicitly target
    :class:`TestPreflightHardBlock`.
    """
    captured.setdefault("commit_calls", [])
    captured.setdefault("new_sha", "f00dcafe")

    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)
    monkeypatch.setattr(
        "close_task_cmd._preflight_triplet_check",
        lambda state, project_root=None, *, skip_preflight=False: None,
    )

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
    # v1.0.5 Item D Q3-A: bypass HARD-BLOCK in this happy-path test.
    monkeypatch.setattr(
        "close_task_cmd._preflight_triplet_check",
        lambda state, project_root=None, *, skip_preflight=False: None,
    )

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
    assert new_state is not None  # v1.0.5 I-2: orchestrator path returns SessionState
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
    assert new_state is not None  # v1.0.5 I-2: orchestrator path returns SessionState
    assert new_state.current_task_id == "3"
    assert new_state.current_phase == "red"


# ---------------------------------------------------------------------------
# v1.0.5 Item I-2 -- per-worker scratch plan + flip-merge pattern
# (escenarios I2-1..I2-5)
# ---------------------------------------------------------------------------


def _scratch_writer_worker(
    project_root_str: str,
    task_ids: list[str],
    barrier,  # noqa: ANN001
) -> None:
    """Top-level helper for ``multiprocessing.Process`` spawn (must be picklable).

    v1.0.5 Item I-2 race regression test (escenario I2-4): each worker
    waits at the shared :class:`multiprocessing.Barrier` and then races
    to write its scratch plan flips. The barrier amplifies the race
    window by guaranteeing both workers reach the read-modify-write
    sequence simultaneously.
    """
    import shutil as _shutil
    import sys as _sys
    from pathlib import Path as _Path

    _sys.path.insert(
        0,
        str(_Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"),
    )
    from close_task_cmd import _scratch_plan_path

    project_root = _Path(project_root_str)
    barrier.wait()
    scratch = _scratch_plan_path(tuple(sorted(task_ids)), project_root)
    if not scratch.exists():
        _shutil.copy2(project_root / "planning" / "claude-plan-tdd.md", scratch)
    text = scratch.read_text(encoding="utf-8")
    for tid in task_ids:
        text = text.replace(
            f"### Task {tid}\n- [ ] step",
            f"### Task {tid}\n- [x] step",
            1,
        )
    scratch.write_text(text, encoding="utf-8")


class TestPerWorkerScratchPlan:
    """v1.0.5 Item I-2 escenarios I2-1 through I2-5 -- per-worker scratch + flip-merge."""

    def test_i2_1_worker_mode_writes_flip_to_scratch(self, tmp_path: Path) -> None:
        """I2-1: worker mode redirects flip to per-worker scratch."""
        import argparse

        from close_task_cmd import _scratch_plan_path, mark_and_advance

        # Synthesize main plan
        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 3: Demo\n\n- [ ] **Step 1**\n- [ ] **Step 2**\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        ns = argparse.Namespace(no_recursive=True, task_ids="3")
        state = {"current_task_id": "3", "current_phase": "refactor"}
        mark_and_advance(state, tmp_path, ns)

        scratch = _scratch_plan_path(("3",), tmp_path)
        assert scratch.exists()
        scratch_text = scratch.read_text(encoding="utf-8")
        assert "[x]" in scratch_text  # flip applied to scratch
        # Main plan UNCHANGED in worker mode
        main_text = main_plan.read_text(encoding="utf-8")
        assert "[x]" not in main_text

    def test_i2_2_orchestrator_mode_writes_to_main_plan(self, tmp_path: Path) -> None:
        """I2-2: orchestrator mode (no ns / no worker markers) writes main plan."""
        import argparse

        from close_task_cmd import mark_and_advance

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 3: Demo\n\n- [ ] **Step 1**\n",
            encoding="utf-8",
        )

        ns = argparse.Namespace(no_recursive=False, task_ids=None)
        state = {"current_task_id": "3", "current_phase": "refactor"}
        mark_and_advance(state, tmp_path, ns)

        main_text = main_plan.read_text(encoding="utf-8")
        assert "[x]" in main_text  # flip applied directly to main

    def test_i2_3_parent_post_batch_merges_scratch_flips(self, tmp_path: Path) -> None:
        """I2-3: parent post-batch merges scratch flips into main."""
        from close_task_cmd import _merge_scratch_plans, _scratch_plan_path

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 1\n- [ ] T1 step\n\n### Task 2\n- [ ] T2 step\n\n"
            "### Task 3\n- [ ] T3 step\n\n### Task 4\n- [ ] T4 step\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        # Worker A scratch (T1 + T3 flipped)
        scratch_a = _scratch_plan_path(("1", "3"), tmp_path)
        scratch_a.write_text(
            "### Task 1\n- [x] T1 step\n\n### Task 2\n- [ ] T2 step\n\n"
            "### Task 3\n- [x] T3 step\n\n### Task 4\n- [ ] T4 step\n",
            encoding="utf-8",
        )
        # Worker B scratch (T2 + T4 flipped)
        scratch_b = _scratch_plan_path(("2", "4"), tmp_path)
        scratch_b.write_text(
            "### Task 1\n- [ ] T1 step\n\n### Task 2\n- [x] T2 step\n\n"
            "### Task 3\n- [ ] T3 step\n\n### Task 4\n- [x] T4 step\n",
            encoding="utf-8",
        )

        _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)

        merged_text = main_plan.read_text(encoding="utf-8")
        # ALL 4 flips visible in main
        assert merged_text.count("[x]") == 4
        # Scratch files cleaned up
        assert not scratch_a.exists()
        assert not scratch_b.exists()

    def test_i2_3b_partial_worker_failure_no_fabrication(self, tmp_path: Path) -> None:
        """I2-3b (iter-1 CRITICAL #1+#3 fix): worker crashes after flipping
        T1 in scratch but BEFORE flipping T3 -> main gets T1 only; T3
        remains [ ] (no fabricated flip). Operator can resume via
        ``/sbtdd auto --task-ids T3`` later.

        Pre-fix behavior would have flipped both T1 AND T3 in main
        regardless of scratch state. iter-1 CRITICAL #1+#3 fix derives
        flips from scratch-vs-main diff.
        """
        import shutil as _shutil

        from close_task_cmd import (
            _flip_checkbox,
            _merge_scratch_plans,
            _scratch_plan_path,
            _section_has_flipped,
        )

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 1\n- [ ] step\n\n### Task 2\n- [ ] step\n\n"
            "### Task 3\n- [ ] step\n\n### Task 4\n- [ ] step\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        # Simulate worker A (assigned [1, 3]) that crashed after flipping
        # T1 in scratch but BEFORE flipping T3:
        scratch_a = _scratch_plan_path(("1", "3"), tmp_path)
        _shutil.copy2(main_plan, scratch_a)
        text = scratch_a.read_text(encoding="utf-8")
        text = _flip_checkbox(text, "1")  # T1 flipped, T3 NOT flipped
        scratch_a.write_text(text, encoding="utf-8")

        # Worker B (assigned [2, 4]) completed normally:
        scratch_b = _scratch_plan_path(("2", "4"), tmp_path)
        _shutil.copy2(main_plan, scratch_b)
        text = scratch_b.read_text(encoding="utf-8")
        text = _flip_checkbox(text, "2")
        text = _flip_checkbox(text, "4")
        scratch_b.write_text(text, encoding="utf-8")

        # Parent merge -- must derive flips from scratch-vs-main diff
        _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)
        merged_text = main_plan.read_text(encoding="utf-8")
        # T1 flipped (scratch_a had [x]); T3 NOT flipped (scratch_a [ ]);
        # T2 flipped; T4 flipped -> exactly 3 [x], NOT 4
        assert merged_text.count("[x]") == 3, (
            f"Expected 3 flips (T1+T2+T4); got {merged_text.count('[x]')}. "
            "Pre-fix bug would fabricate T3 flip."
        )
        # T3 specifically must remain [ ]
        assert not _section_has_flipped(merged_text, "3"), (
            "T3 was fabricated as flipped -- iter-1 CRITICAL #1+#3 regression"
        )

    def test_i2_4_real_multiprocessing_race_regression(self, tmp_path: Path) -> None:
        """I2-4: cross-process race regression test via ``multiprocessing.spawn``.

        v1.0.5 iter-2 WARNING fix: explicit ``for _ in range(50):`` repeat
        loop wrapping the multiprocessing barrier-synchronized RMW.
        Asserts no flip lost across all 50 iterations to amplify
        race-window detection per spec sec.4.2 escenario I2-4.
        """
        import multiprocessing

        from close_task_cmd import _merge_scratch_plans

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan_path = plan_dir / "claude-plan-tdd.md"
        original_plan = (
            "### Task 1\n- [ ] step\n\n### Task 2\n- [ ] step\n\n"
            "### Task 3\n- [ ] step\n\n### Task 4\n- [ ] step\n"
        )
        (tmp_path / ".claude").mkdir()

        ctx = multiprocessing.get_context("spawn")

        for iteration in range(50):
            # Reset main plan + cleanup any stale scratch from prior loop
            main_plan_path.write_text(original_plan, encoding="utf-8")
            for stale in (tmp_path / ".claude").glob("plan-scratch-*.md"):
                stale.unlink(missing_ok=True)

            barrier = ctx.Barrier(2)
            procs = [
                ctx.Process(
                    target=_scratch_writer_worker,
                    args=(str(tmp_path), ["1", "3"], barrier),
                ),
                ctx.Process(
                    target=_scratch_writer_worker,
                    args=(str(tmp_path), ["2", "4"], barrier),
                ),
            ]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=30)
                assert p.exitcode == 0, f"Iter {iteration}: worker exited {p.exitcode}"

            _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)
            merged_text = main_plan_path.read_text(encoding="utf-8")
            # ALL 4 flips visible across all 50 iterations (no lost updates)
            assert merged_text.count("[x]") == 4, (
                f"Iter {iteration}: lost flip -- got {merged_text.count('[x]')} "
                f"[x] in merged plan, expected 4"
            )

    def test_i2_5_anchored_flip_checkbox_respects_section_boundaries(self, tmp_path: Path) -> None:
        """I2-5 (iter-1 CRITICAL #2 fix): anchored regex bounds flips to
        current task's section. Pre-fix unanchored regex with re.DOTALL
        could match a [ ] from a LATER task when current task has no [ ].
        """
        from close_task_cmd import _flip_checkbox, _section_has_flipped

        # Plan: Task 3 has NO [ ] checkbox; Task 4 has [ ]
        plan_text = (
            "### Task 3\nThe operator already removed the checkbox.\n\n### Task 4\n- [ ] step\n"
        )

        # Flip T3 -- pre-fix would match Task 4's [ ] across the boundary
        result = _flip_checkbox(plan_text, "3")

        # Anchored impl: T3 has no [ ] -> result unchanged (idempotent guard)
        assert result == plan_text, "Pre-fix regex would have flipped Task 4's [ ] across boundary"
        # T4's [ ] still intact:
        assert not _section_has_flipped(result, "4"), (
            "T4 boundary violated -- iter-1 CRITICAL #2 regression"
        )


# ---------------------------------------------------------------------------
# v1.0.5 Item D Q3 OPTION A -- close_task_cmd._preflight HARD-BLOCK
# (escenarios D-1..D-4)
# ---------------------------------------------------------------------------


class TestPreflightHardBlock:
    """v1.0.5 Item D Q3-A escenarios D-1 through D-4 -- preflight enforcement."""

    def test_d1_bypass_detected_raises_precondition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-1: commit chain without TDD triplet -> PreconditionError."""
        from close_task_cmd import _preflight_triplet_check
        from errors import PreconditionError

        # Mock _git_log_between to return chain without triplet
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "raw commit 1",
                "another raw commit",
            ],
        )
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc123",
        )
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        with pytest.raises(PreconditionError) as exc_info:
            _preflight_triplet_check(state, tmp_path)

        msg = str(exc_info.value)
        assert "Phase advance gate bypassed" in msg
        assert "test:/feat:|fix:/refactor: triplet" in msg
        assert "INV-1" in msg
        assert "close-phase" in msg
        assert "--skip-preflight" in msg

    def test_d2_canonical_triplet_no_trigger(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-2: canonical TDD triplet in commit chain -> no PreconditionError."""
        from close_task_cmd import _preflight_triplet_check

        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement minimum",
                "refactor: clean up",
            ],
        )
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc123",
        )
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        # Should NOT raise
        _preflight_triplet_check(state, tmp_path)

    def test_d3_skip_preflight_bypasses_with_breadcrumb(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-3: --skip-preflight bypasses + emits stderr breadcrumb.

        Loop 1 iter-2 Important #1 fix: breadcrumb MUST include
        `since SHA <sha>` segment per spec D-3 wording.
        """
        from close_task_cmd import _preflight_triplet_check

        # Stub _last_chore_task_close_sha so the bypass path produces a
        # deterministic SHA in the breadcrumb (no real git dependency).
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc1234",
        )
        # Bypass scenario: skip_preflight=True
        state = {"current_task_id": "3", "phase_started_at_commit": "doesntmatter"}

        # Should NOT raise (override active)
        _preflight_triplet_check(state, tmp_path, skip_preflight=True)

        captured = capsys.readouterr()
        assert "[sbtdd close-task] WARNING" in captured.err
        assert "--skip-preflight active" in captured.err
        assert "task_id=3" in captured.err
        # Loop 1 iter-2 Important #1: breadcrumb MUST cite SHA boundary
        assert "since SHA abc1234" in captured.err
        assert "Audit-logged" in captured.err

    def test_d3b_skip_preflight_bypasses_first_task_branch_root_in_breadcrumb(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """D-3 (Loop 1 iter-2 fix): first-task case (no prior chore commit)
        renders 'since SHA branch root' in the bypass breadcrumb."""
        from close_task_cmd import _preflight_triplet_check

        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: None,
        )
        state = {"current_task_id": "1"}

        _preflight_triplet_check(state, tmp_path, skip_preflight=True)

        captured = capsys.readouterr()
        assert "since SHA branch root" in captured.err

    def test_d4_no_chore_commit_first_task_branch_root_boundary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-2b (iter-1 CRITICAL #5 fix): no prior `chore: mark task` commit
        -> boundary is branch root + canonical triplet OK -> no raise."""
        from close_task_cmd import _preflight_triplet_check

        # Simulate: first task in plan, no prior chore commit exists
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: None,
        )
        # Branch root -> HEAD contains canonical triplet
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement",
                "refactor: extract helper",
            ],
        )
        state = {"current_task_id": "1"}

        # Should NOT raise (first task, branch-root boundary, full triplet)
        _preflight_triplet_check(state, tmp_path)

    def test_d5_partial_triplet_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """D-5 (iter-1 CRITICAL #5 fix): commit chain since last chore: mark
        task with only 2 of 3 triplet prefixes -> still raises.

        (Loop 1 iter-2 minor fix: docstring previously said "D-1" — copy-
        paste typo from D-1 case; corrected to D-5 to match test name.)"""
        from close_task_cmd import _preflight_triplet_check
        from errors import PreconditionError

        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc123",
        )
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement",
                # missing refactor
            ],
        )
        state = {"current_task_id": "3"}

        with pytest.raises(PreconditionError) as excinfo:
            _preflight_triplet_check(state, tmp_path)
        # iter-1 CRITICAL #5: error message references "since last chore commit"
        # boundary (or "branch root") -- NOT phase_started_at_commit
        assert "since" in str(excinfo.value)
        assert "abc123" in str(excinfo.value) or "chore" in str(excinfo.value)

    def test_d6_skip_preflight_argparse_flag_exposed(self) -> None:
        """D-3 (argparse): close-task --skip-preflight is exposed via argparse."""
        from close_task_cmd import _build_parser

        parser = _build_parser()
        ns = parser.parse_args(["--skip-preflight"])
        assert ns.skip_preflight is True
        ns_default = parser.parse_args([])
        assert ns_default.skip_preflight is False


class TestSectionHasFlippedPerCheckbox:
    """v1.0.6 K-1: _section_has_flipped per-checkbox parity.

    Covers escenarios K-1a through K-1c from spec sec.4.4. Pre-fix:
    returned True on first [x] in section. Post-fix: requires ALL
    checkboxes in section to be [x] for True.
    """

    def test_k1a_mixed_checkbox_section_returns_false(self) -> None:
        """K-1a: section with both [x] and [ ] returns False (not fully flipped)."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n- [x] Step 1\n- [ ] Step 2\n- [x] Step 3\n\n### Task 2\n- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is False, (
            "Mixed-checkbox section should NOT be considered flipped"
        )

    def test_k1b_fully_flipped_section_returns_true(self) -> None:
        """K-1b: section with all [x] returns True."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n- [x] Step 1\n- [x] Step 2\n- [x] Step 3\n\n### Task 2\n- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is True

    def test_k1c_empty_section_returns_false(self) -> None:
        """K-1c: section with no checkboxes returns False (vacuously not flipped)."""
        from close_task_cmd import _section_has_flipped

        plan_text = "### Task 1\nDescription only, no checkboxes.\n\n### Task 2\n- [ ] Step 1\n"
        assert _section_has_flipped(plan_text, "1") is False

    def test_k1d_single_open_checkbox_returns_false(self) -> None:
        """K-1d (regression for v1.0.5): section with single [ ] and no [x] returns False."""
        from close_task_cmd import _section_has_flipped

        plan_text = "### Task 1\n- [ ] Step 1\n\n### Task 2\n- [x] Step 1\n"
        assert _section_has_flipped(plan_text, "1") is False

    def test_k1e_single_flipped_checkbox_returns_true(self) -> None:
        """K-1e (preserve v1.0.5): single [x] checkbox + no [ ] returns True."""
        from close_task_cmd import _section_has_flipped

        plan_text = "### Task 1\n- [x] Step 1\n\n### Task 2\n- [ ] Step 1\n"
        assert _section_has_flipped(plan_text, "1") is True

    def test_k1f_codeblock_x_inside_section_does_not_count(self) -> None:
        """K-1f (iter-1 mel WARNING): line-anchored regex ignores `[x]` inside code blocks."""
        from close_task_cmd import _section_has_flipped

        # `[x]` appears inside a code block (not at line start) -- should NOT count
        plan_text = (
            "### Task 1\n"
            "Example code: `if x is None:` shows `[x]` syntax\n"
            "- [ ] Step 1\n"  # actual checkbox open
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        # has_x=False (no `^- [x]`), has_open=True → False
        assert _section_has_flipped(plan_text, "1") is False, (
            "Pre-fix substring check would have returned True (matched `[x]` in prose); "
            "post-fix line-anchored regex returns False"
        )

    def test_k1g_v105_i2_race_partial_worker_failure_no_fabrication(self, tmp_path: Path) -> None:
        """K-1g (iter-1 bal WARNING): per-checkbox parity preserves v1.0.5 I-2 race contract.

        Worker A scratch shows partial T1 flips (1 of 2 steps `[x]`, 1 still `[ ]`);
        `_apply_flips_from_diff` MUST NOT fabricate full-task `[x]` for T1
        in main plan based on the partial scratch state.
        """
        from close_task_cmd import _apply_flips_from_diff

        main_plan = "### Task 1\n- [ ] Step A\n- [ ] Step B\n\n### Task 2\n- [ ] Step 1\n"
        # Worker A scratch: T1 partially flipped (Step A done, Step B not done)
        scratch_a = (
            "### Task 1\n"
            "- [x] Step A\n"
            "- [ ] Step B\n"  # NOT flipped
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )

        merged = _apply_flips_from_diff(main_plan, scratch_a)
        # Per K-1 line-anchored + per-checkbox parity: T1 section in scratch
        # is NOT fully flipped (has both [x] and [ ]) → main plan T1 unchanged
        # NO fabrication of full-task `[x]` flip
        assert "- [ ] Step B" in merged, (
            "T1 Step B remained unflipped in main plan (no fabrication)"
        )

    def test_k1h_v105_i2_race_full_worker_completion_flips_correctly(self, tmp_path: Path) -> None:
        """K-1h (iter-1 bal WARNING): fully-flipped scratch correctly propagates to main."""
        from close_task_cmd import _apply_flips_from_diff

        main_plan = "### Task 1\n- [ ] Step A\n- [ ] Step B\n\n### Task 2\n- [ ] Step 1\n"
        # Worker A scratch: T1 FULLY flipped
        scratch_a = "### Task 1\n- [x] Step A\n- [x] Step B\n\n### Task 2\n- [ ] Step 1\n"

        merged = _apply_flips_from_diff(main_plan, scratch_a)
        # T1 fully flipped in scratch (per K-1 semantic) → propagates to main
        assert "- [x] Step A" in merged
        assert "- [x] Step B" in merged
        # T2 untouched
        assert "- [ ] Step 1" in merged
