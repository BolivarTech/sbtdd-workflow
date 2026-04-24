# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Tests for /sbtdd close-task --skip-spec-review flag + reviewer integration.

v0.2 Feature B, Task H5: ``close_task_cmd`` gains an INV-31 enforcement
path that dispatches the spec-reviewer before ``mark_and_advance`` and an
escape-valve ``--skip-spec-review`` flag for manual workflows.

Three behaviors asserted here:

1. Default invocation: ``spec_review_dispatch.dispatch_spec_reviewer`` is
   called with the closing task's id + plan path + project root BEFORE
   ``mark_and_advance`` advances state.
2. ``--skip-spec-review``: reviewer dispatch is bypassed entirely; the
   task still closes normally (INV-31 escape valve for interactive flows).
3. ``SpecReviewError`` propagation: when the reviewer raises (safety-valve
   exhausted or reviewer returned approved=False defensively), the
   exception bubbles up and state advance does NOT happen.

Tests use :class:`tests.fixtures.skill_stubs.StubSpecReviewer` and
``monkeypatch.setattr`` per the conftest.py test-isolation policy.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.fixtures.skill_stubs import StubSpecReviewer


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "refactor",
    current_task_id: str = "2",
    current_task_title: str = "Second task (in-progress)",
) -> None:
    """Seed ``.claude/session-state.json`` + a mixed three-task plan fixture."""
    claude = tmp_path / ".claude"
    claude.mkdir()
    planning = tmp_path / "planning"
    planning.mkdir()
    fixtures_root = Path(__file__).parent / "fixtures"
    shutil.copy(
        fixtures_root / "plans" / "three-tasks-mixed.md",
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
        "plan_approved_at": "2026-04-24T10:00:00Z",
    }
    (claude / "session-state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _install_happy_path_patches(
    monkeypatch: pytest.MonkeyPatch, captured: dict[str, object]
) -> None:
    """Patch drift + subprocess + commit so ``close_task_cmd.main`` runs end-to-end."""
    captured.setdefault("commit_calls", [])
    captured.setdefault("new_sha", "f00dcafe")

    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)

    def fake_run(cmd: list[str], timeout: int = 0, cwd: str | None = None):  # type: ignore[no-untyped-def]
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


def test_close_task_help_mentions_skip_spec_review_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`--help` output surfaces the new ``--skip-spec-review`` flag."""
    import close_task_cmd

    with pytest.raises(SystemExit) as ei:
        close_task_cmd.main(["--help"])
    assert ei.value.code == 0
    out = capsys.readouterr().out
    assert "--skip-spec-review" in out


def test_close_task_invokes_reviewer_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No flag => reviewer called with closing task's id + paths BEFORE advance."""
    import close_task_cmd
    import spec_review_dispatch

    _seed_state(tmp_path)
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)
    stub = StubSpecReviewer(sequence=[True])
    monkeypatch.setattr(
        spec_review_dispatch,
        "dispatch_spec_reviewer",
        stub.dispatch_spec_reviewer,
    )

    close_task_cmd.main(["--project-root", str(tmp_path)])

    assert len(stub.calls) == 1
    assert stub.calls[0]["task_id"] == "2"
    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] == "3"
    assert state["current_phase"] == "red"


def test_close_task_reviewer_receives_plan_and_repo_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reviewer dispatch receives ``plan_path`` and ``repo_root`` resolved from state."""
    import close_task_cmd
    import spec_review_dispatch

    _seed_state(tmp_path)
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    observed: dict[str, Any] = {}

    def fake_dispatch(
        *,
        task_id: str,
        plan_path: Path,
        repo_root: Path,
        max_iterations: int = 3,
        timeout: int = 900,
    ):  # type: ignore[no-untyped-def]
        from spec_review_dispatch import SpecReviewResult

        observed["task_id"] = task_id
        observed["plan_path"] = plan_path
        observed["repo_root"] = repo_root
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", fake_dispatch)

    close_task_cmd.main(["--project-root", str(tmp_path)])

    assert observed["task_id"] == "2"
    assert Path(observed["plan_path"]) == tmp_path / "planning" / "claude-plan-tdd.md"
    assert Path(observed["repo_root"]) == tmp_path


def test_close_task_skip_flag_bypasses_reviewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--skip-spec-review` => reviewer NOT called; task still closes (INV-31 escape)."""
    import close_task_cmd
    import spec_review_dispatch

    _seed_state(tmp_path)
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)
    stub = StubSpecReviewer(sequence=[])  # empty => IndexError if reviewer called
    monkeypatch.setattr(
        spec_review_dispatch,
        "dispatch_spec_reviewer",
        stub.dispatch_spec_reviewer,
    )

    close_task_cmd.main(["--project-root", str(tmp_path), "--skip-spec-review"])

    assert stub.calls == []
    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] == "3"


def test_close_task_reviewer_raises_spec_review_error_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``SpecReviewError`` from reviewer propagates; state does NOT advance."""
    import close_task_cmd
    import spec_review_dispatch
    from errors import SpecReviewError

    _seed_state(tmp_path)
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    def failing_dispatch(**kwargs: Any):  # type: ignore[no-untyped-def]
        raise SpecReviewError(
            "spec-reviewer safety valve exhausted for task 2",
            task_id="2",
            iteration=3,
            issues=("stub finding",),
        )

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", failing_dispatch)

    with pytest.raises(SpecReviewError):
        close_task_cmd.main(["--project-root", str(tmp_path)])

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] == "2"  # still on task 2
    assert state["current_phase"] == "refactor"
    assert captured["commit_calls"] == []  # no chore commit made


def test_close_task_reviewer_not_approved_raises_spec_review_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Defensive guard: reviewer returning approved=False => ``SpecReviewError``."""
    import close_task_cmd
    import spec_review_dispatch
    from errors import SpecReviewError

    _seed_state(tmp_path)
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)
    stub = StubSpecReviewer(sequence=[False])  # approved=False => one MISSING issue
    monkeypatch.setattr(
        spec_review_dispatch,
        "dispatch_spec_reviewer",
        stub.dispatch_spec_reviewer,
    )

    with pytest.raises(SpecReviewError):
        close_task_cmd.main(["--project-root", str(tmp_path)])

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_task_id"] == "2"
    assert captured["commit_calls"] == []
