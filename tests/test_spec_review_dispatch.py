"""Tests for skills/sbtdd/scripts/spec_review_dispatch.py — dataclasses + dispatch."""

from __future__ import annotations

import pytest

from errors import SpecReviewError


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


def test_dispatch_default_max_iterations_is_one_per_b6_defer() -> None:
    """dispatch_spec_reviewer defaults max_iterations=1 in v0.2 per B6 defer.

    Regression for MAGI Loop 2 CRITICAL finding (2026-04-24): the default
    was 3 but the loop re-invokes the reviewer on byte-identical inputs
    because spec-base §2.2's mini-cycle TDD feedback between dispatches
    is deferred to v0.2.1. With no input mutation between iters the
    reviewer is nominally deterministic, so iter 2+ burn quota for zero
    semantic benefit. Pinning default=1 until v0.2.1 lands the feedback
    path bumps it back to 3.
    """
    import inspect

    from spec_review_dispatch import dispatch_spec_reviewer  # type: ignore[import-not-found]

    sig = inspect.signature(dispatch_spec_reviewer)
    assert sig.parameters["max_iterations"].default == 1


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
