"""Tests for skills/sbtdd/scripts/spec_review_dispatch.py — dataclasses + dispatch."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from errors import SpecReviewError


def _init_repo(path: Path) -> None:
    """Initialise a git repo with identity set for commit authorship."""
    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True)
    for cfg in (("user.email", "t@example.com"), ("user.name", "tester")):
        subprocess.run(["git", "-C", str(path), "config", *cfg], check=True, capture_output=True)


def _commit(path: Path, filename: str, content: str, message: str) -> str:
    """Write ``filename`` with ``content`` and make a commit, returning SHA."""
    (path / filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", filename], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(path), "commit", "-m", message], check=True, capture_output=True
    )
    sha_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return sha_r.stdout.strip()


def _seed_multi_task_repo(path: Path) -> dict[str, str]:
    """Seed a repo with two closed tasks + one in-flight task.

    Layout (chronological):
      initial.txt -> initial commit
      task-1-red, task-1-green, task-1-refactor -> 3 phase commits
      chore: mark task 1 complete -> task 1 chore
      task-2-red, task-2-green, task-2-refactor -> 3 phase commits
      chore: mark task 2 complete -> task 2 chore
      task-3-red -> task 3 in flight (no chore yet)

    Returns a dict keyed by phase/task -> SHA so tests can assert the
    diff range boundaries are correct.
    """
    _init_repo(path)
    shas: dict[str, str] = {}
    shas["initial"] = _commit(path, "initial.txt", "seed", "chore: seed initial")
    shas["t1_red"] = _commit(path, "t1.py", "# red", "test: red for task 1")
    shas["t1_green"] = _commit(path, "t1.py", "# green", "feat: green for task 1")
    shas["t1_refactor"] = _commit(path, "t1.py", "# refactor", "refactor: task 1")
    shas["t1_chore"] = _commit(path, "plan.md", "[x] t1", "chore: mark task 1 complete")
    shas["t2_red"] = _commit(path, "t2.py", "# red", "test: red for task 2")
    shas["t2_green"] = _commit(path, "t2.py", "# green", "feat: green for task 2")
    shas["t2_refactor"] = _commit(path, "t2.py", "# refactor", "refactor: task 2")
    shas["t2_chore"] = _commit(path, "plan.md", "[x] t2", "chore: mark task 2 complete")
    shas["t3_red"] = _commit(path, "t3.py", "# red", "test: red for task 3")
    return shas


def test_spec_review_result_is_frozen() -> None:
    from spec_review_dispatch import SpecReviewResult, SpecIssue  # type: ignore[import-not-found]  # noqa: F401

    r = SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)
    with pytest.raises((AttributeError, Exception)):
        r.approved = False


def test_spec_issue_carries_severity_and_text() -> None:
    from spec_review_dispatch import SpecIssue  # type: ignore[import-not-found]

    i = SpecIssue(severity="MISSING", text="Scenario 4 not covered")
    assert i.severity == "MISSING"


def test_dispatch_approved_path(tmp_path, monkeypatch) -> None:
    from spec_review_dispatch import dispatch_spec_reviewer  # type: ignore[import-not-found,attr-defined]

    plan = tmp_path / "plan.md"
    plan.write_text("### Task 1: foo\n- [ ] stuff\n", encoding="utf-8")

    def fake_run(*a, **k):
        class R:
            returncode = 0
            stdout = '{"approved": true, "issues": []}'
            stderr = ""

        return R()

    monkeypatch.setattr("spec_review_dispatch.subprocess_utils.run_with_timeout", fake_run)
    result = dispatch_spec_reviewer(task_id="1", plan_path=plan, repo_root=tmp_path)
    assert result.approved is True
    assert result.issues == ()


def test_dispatch_default_max_iterations_is_three_per_b6_shipped() -> None:
    """dispatch_spec_reviewer defaults max_iterations=3 in v0.2.1 per B6 ship.

    v0.2.0 pinned this to 1 because the loop re-invoked the reviewer on
    byte-identical inputs (no feedback loop between dispatches), so iter
    2+ burned quota for zero semantic benefit. v0.2.1 ships the
    auto-feedback loop (see ``auto_cmd._apply_spec_review_findings_via_mini_cycle``):
    accepted reviewer findings now route through ``/receiving-code-review``
    + a mini-cycle TDD fix per accepted finding (test/fix/refactor) + a
    re-dispatch of the reviewer on the now-mutated diff. With real input
    mutation between iterations the safety valve has work to do, so the
    default reverts to the original B6 design value of 3.
    """
    import inspect

    from spec_review_dispatch import dispatch_spec_reviewer  # type: ignore[import-not-found]

    sig = inspect.signature(dispatch_spec_reviewer)
    assert sig.parameters["max_iterations"].default == 3


def test_find_task_chore_sha_exact_match_only(tmp_path: Path) -> None:
    """task_id substring matches must NOT resolve to a chore for another task.

    Regression for MAGI Loop 2 CRITICAL #1/#5 (2026-04-24): the v0.2
    baseline greped the commit subject for ``task_id`` as a substring,
    so ``task_id="1"`` false-matched "task 10", "task 11", "phase 1",
    etc. The fix correlates on exact subject equality against
    ``chore: mark task {id} complete``.
    """
    from spec_review_dispatch import _find_task_chore_sha  # type: ignore[import-not-found]

    shas = _seed_multi_task_repo(tmp_path)
    # Seed an adjacent-id chore (task 10) to prove substring collision.
    _commit(tmp_path, "t10.py", "# t10", "chore: mark task 10 complete")

    assert _find_task_chore_sha(tmp_path, "1") == shas["t1_chore"]
    assert _find_task_chore_sha(tmp_path, "2") == shas["t2_chore"]
    # task_id "999" does not exist; must return empty string, not a false match.
    assert _find_task_chore_sha(tmp_path, "999") == ""


def test_collect_task_diff_closed_task_bounds_by_prev_chore(tmp_path: Path) -> None:
    """Closed task -> diff between previous task's chore and this task's chore.

    Task 2's diff must include t2_* phase commits but must NOT include
    t1_* phase commits (which are bounded by t1_chore). Assertion
    checks file-level markers in the diff body.
    """
    from spec_review_dispatch import _collect_task_diff  # type: ignore[import-not-found]

    _seed_multi_task_repo(tmp_path)
    diff = _collect_task_diff(tmp_path, "2")

    # Task 2's files must appear.
    assert "t2.py" in diff
    # Task 1's phase commits must NOT appear (they are bounded behind t1_chore).
    assert "t1.py" not in diff


def test_collect_task_diff_first_task_falls_back_to_log_p(tmp_path: Path) -> None:
    """First task has no prior chore -> ``git log -p`` against this task's chore.

    The full history up to and including task 1's chore appears in the
    diff because the helper cannot bound at an earlier chore.
    """
    from spec_review_dispatch import _collect_task_diff  # type: ignore[import-not-found]

    _seed_multi_task_repo(tmp_path)
    diff = _collect_task_diff(tmp_path, "1")

    # Seed + task 1's three phase commits are all present.
    assert "initial.txt" in diff
    assert "t1.py" in diff


def test_collect_task_diff_in_flight_task_bounds_at_head(tmp_path: Path) -> None:
    """In-flight task (no chore yet) -> diff from last chore to HEAD.

    ``_seed_multi_task_repo`` leaves task 3 in flight (``t3_red`` on
    HEAD, no chore). The diff must include t3's file but not t1 or t2's
    (bounded behind task 2's chore).
    """
    from spec_review_dispatch import _collect_task_diff  # type: ignore[import-not-found]

    _seed_multi_task_repo(tmp_path)
    diff = _collect_task_diff(tmp_path, "3")

    assert "t3.py" in diff
    assert "t1.py" not in diff
    assert "t2.py" not in diff


def test_collect_task_diff_returns_empty_when_git_fails(tmp_path: Path) -> None:
    """No git repo -> empty string, not a crash (dispatcher resilience)."""
    from spec_review_dispatch import _collect_task_diff  # type: ignore[import-not-found]

    # tmp_path has no .git; the helper must swallow git failure.
    diff = _collect_task_diff(tmp_path, "1")
    assert diff == ""


def test_dispatch_safety_valve_raises_spec_review_error(tmp_path, monkeypatch) -> None:
    from spec_review_dispatch import dispatch_spec_reviewer  # type: ignore[import-not-found,attr-defined]

    plan = tmp_path / "plan.md"
    plan.write_text("### Task 1: foo\n- [ ] stuff\n", encoding="utf-8")

    def fake_run(*a, **k):
        class R:
            returncode = 0
            stdout = (
                '{"approved": false, "issues": [{"severity": "MISSING", "text": "scenario N"}]}'
            )
            stderr = ""

        return R()

    monkeypatch.setattr("spec_review_dispatch.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(SpecReviewError):
        dispatch_spec_reviewer(task_id="1", plan_path=plan, repo_root=tmp_path, max_iterations=3)
