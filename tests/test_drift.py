#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for drift module — DriftReport + _evaluate_drift + detect_drift."""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError


def test_drift_report_is_frozen():
    from drift import DriftReport

    report = DriftReport(
        state_value="green",
        git_value="refactor:",
        plan_value="[ ]",
        reason="phase/prefix mismatch",
    )
    with pytest.raises(FrozenInstanceError):
        report.state_value = "red"  # type: ignore[misc]


def test_drift_report_fields():
    from drift import DriftReport

    fields = set(DriftReport.__dataclass_fields__)
    assert fields == {"state_value", "git_value", "plan_value", "reason"}


def test_detect_drift_phase_red_with_test_commit():
    """current_phase=red + HEAD=test: is drift (close ran, state not advanced)."""
    from drift import _evaluate_drift, DriftReport

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="test",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "red"
    assert report.git_value == "test"


def test_detect_drift_phase_green_with_feat_commit():
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="green",
        last_commit_prefix="feat",
        plan_task_state="[ ]",
    )
    assert report is not None
    assert "feat" in report.git_value


def test_detect_drift_phase_refactor_with_refactor_commit():
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="refactor",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_scenario_4_green_with_refactor_commit():
    """Scenario 4 (spec-behavior.md sec.4.2 + CLAUDE.md sec.2.1) -- canonical.

    state=green but HEAD=refactor: means a later phase's close committed
    without the state file advancing through green.
    """
    from drift import _evaluate_drift, DriftReport

    report = _evaluate_drift(
        current_phase="green",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "green"
    assert report.git_value == "refactor"
    assert "refactor" in report.reason


def test_detect_drift_scenario_4_red_with_feat_commit():
    """Phase-ordering inversion: state=red but HEAD=feat: (green close landed)."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="feat",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_red_with_refactor_commit():
    """Phase-ordering inversion: state=red but HEAD=refactor: (refactor close landed)."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_consistent_returns_none():
    """current_phase=red + HEAD=chore: (previous task close) is consistent."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="chore",
        plan_task_state="[ ]",
    )
    assert report is None


def test_detect_drift_done_phase_returns_none():
    """Phase=done is terminal -- no drift regardless of commit prefix."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="done",
        last_commit_prefix="refactor",
        plan_task_state="[x]",
    )
    assert report is None


def test_detect_drift_done_with_remaining_open_tasks():
    """state=done but plan still has [ ] is drift (task-advance bug).

    Per MAGI Loop 2 Finding 3: if current_phase=done but the plan still
    shows open tasks, a subcommand bug failed to advance through all
    tasks. This must surface as drift (exit 3), not hide.
    """
    from drift import DriftReport, _evaluate_drift

    report = _evaluate_drift(
        current_phase="done",
        last_commit_prefix="chore",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "done"
    assert report.plan_value == "[ ]"
    assert "done" in report.reason.lower()


def test_evaluate_drift_plan_already_checked():
    """state points to current_task but plan shows [x] -- drift per INV-3."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="chore",
        plan_task_state="[x]",  # but state still pointing here
    )
    assert report is not None
    assert "already [x]" in report.reason or "completed" in report.reason.lower()


def test_detect_drift_routes_git_through_subprocess_utils(tmp_path, monkeypatch):
    """detect_drift must use subprocess_utils.run_with_timeout for NF5 consistency.

    Per MAGI Loop 2 Finding 8: the direct ``subprocess.run`` call on git
    log bypasses the timeout + Windows kill-tree wrapper that all other
    subprocess invocations go through. Route through subprocess_utils.
    """
    import json

    from drift import detect_drift

    state_path = tmp_path / ".claude" / "session-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": "1",
                "current_task_title": "t",
                "current_phase": "green",
                "phase_started_at_commit": "deadbeef",
                "last_verification_at": None,
                "last_verification_result": None,
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        )
    )
    plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("### Task 1: do something\n- [ ] step 1\n")

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))

        class R:
            returncode = 0
            stdout = "refactor: do the refactor\n"
            stderr = ""

        return R()

    import subprocess_utils

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    detect_drift(
        state_file_path=state_path,
        plan_path=plan_path,
        repo_root=tmp_path,
    )
    git_calls = [c for c in calls if "git" in c]
    assert len(git_calls) == 1, f"expected 1 git call via subprocess_utils, got {git_calls}"
    assert "log" in git_calls[0]


def test_detect_drift_io_wrapper_reads_three_sources(tmp_path, monkeypatch):
    """detect_drift reads state/plan/git itself -- spec-behavior.md sec.4.2 signature."""
    import json

    from drift import detect_drift, DriftReport

    # Seed synthetic state file (phase=green)
    state_path = tmp_path / ".claude" / "session-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": "1",
                "current_task_title": "t",
                "current_phase": "green",
                "phase_started_at_commit": "deadbeef",
                "last_verification_at": None,
                "last_verification_result": None,
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        )
    )

    # Seed synthetic plan with active task [ ]
    plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("### Task 1: do something\n- [ ] step 1\n")

    # Stub git log HEAD -> refactor: commit (Scenario 4)
    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "refactor: do the refactor\n"
            stderr = ""

        return R()

    import subprocess_utils

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)

    report = detect_drift(
        state_file_path=state_path,
        plan_path=plan_path,
        repo_root=tmp_path,
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "green"
    assert report.git_value == "refactor"


def test_all_task_steps_complete_returns_x_when_all_steps_checked():
    """All step-level checkboxes [x] in the task section -> [x]."""
    from drift import _all_task_steps_complete

    plan = (
        "### Task 1: parse headers\n"
        "- [x] step 1\n"
        "- [x] step 2\n"
        "- [x] step 3\n"
        "### Task 2: next\n"
        "- [ ] step 1\n"
    )
    assert _all_task_steps_complete(plan, "1") == "[x]"


def test_all_task_steps_complete_returns_open_when_any_step_unchecked():
    """Even one [ ] step means the task is not complete."""
    from drift import _all_task_steps_complete

    plan = (
        "### Task 1: parse headers\n"
        "- [x] step 1\n"
        "- [ ] step 2\n"
        "- [x] step 3\n"
        "### Task 2: next\n"
        "- [ ] step 1\n"
    )
    assert _all_task_steps_complete(plan, "1") == "[ ]"


def test_all_task_steps_complete_returns_open_when_task_missing():
    """Task header not found -> default to [ ] (conservative)."""
    from drift import _all_task_steps_complete

    plan = "### Task 1: parse headers\n- [x] step 1\n"
    assert _all_task_steps_complete(plan, "99") == "[ ]"


def test_plan_all_tasks_complete_returns_x_when_all_flipped():
    """No ``- [ ]`` anywhere in any ``### Task`` section -> fully complete."""
    from drift import _plan_all_tasks_complete

    plan = "### Task 1: foo\n- [x] step 1\n\n### Task 2: bar\n- [x] step 1\n- [x] step 2\n"
    assert _plan_all_tasks_complete(plan) == "[x]"


def test_plan_all_tasks_complete_returns_open_when_any_section_has_box():
    """One open ``- [ ]`` in any task section -> plan is not fully complete."""
    from drift import _plan_all_tasks_complete

    plan = "### Task 1: foo\n- [x] step 1\n\n### Task 2: bar\n- [ ] step 1\n- [x] step 2\n"
    assert _plan_all_tasks_complete(plan) == "[x]" if False else _plan_all_tasks_complete(plan)
    assert _plan_all_tasks_complete(plan) == "[ ]"


def test_plan_all_tasks_complete_returns_x_when_no_task_headers():
    """Malformed / empty plan -> conservative ``[x]`` (no false drift)."""
    from drift import _plan_all_tasks_complete

    assert _plan_all_tasks_complete("") == "[x]"
    assert _plan_all_tasks_complete("no task headers here") == "[x]"


def test_any_task_header_regex_skips_h2_collapsed_form():
    """v1.0.4 Loop 2 iter-1 CRITICAL #2 regression — h2-collapsed ABSORBED /
    DEFERRED stubs MUST NOT be matched by ``_ANY_TASK_HEADER``.

    Fix per Option (b) for v1.0.4 stale T2/T9 stubs: collapse to
    ``## Task N (ABSORBED into ...)`` (h2) instead of ``### Task N:`` (h3).
    Drift detector's ``_ANY_TASK_HEADER`` regex pins to h3 + colon, so h2
    collapsed-form is structurally invisible to the section walker.

    Asserts the regex matches h3 form but NOT h2 collapsed form. Combined
    with ``test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs``
    below this is the contract guaranteeing future authors cannot
    accidentally re-introduce checkbox-bearing stubs that trip drift.
    """
    from drift import _ANY_TASK_HEADER

    # h3 form: matches (real Task header).
    assert _ANY_TASK_HEADER.search("### Task 1: real task\n") is not None

    # h2 collapsed form: does NOT match (annotation, not visited by walker).
    assert _ANY_TASK_HEADER.search("## Task 2 (ABSORBED into Task 1)\n") is None
    assert _ANY_TASK_HEADER.search("## Task 9 (DEFERRED to v1.0.5)\n") is None

    # Bold inline form: also does NOT match (alternative collapsed form).
    assert _ANY_TASK_HEADER.search("**Task 2 (ABSORBED)** — see T1\n") is None


def test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs():
    """v1.0.4 Loop 2 iter-1 CRITICAL #2 regression — concrete plan-tdd.md must
    use collapsed-form (h2 or non-h3) for T2 ABSORBED + T9 DEFERRED stubs so
    drift detector does not visit them. Stubs that retain ``### Task N:``
    header are OK ONLY if they contain zero ``- [ ]`` markers.

    Asserts current plan body either:
      * uses collapsed-form (no ``### Task 2:`` / ``### Task 9:`` h3 header), OR
      * uses h3 header BUT carries no ``- [ ]`` markers in section body.

    Either form satisfies drift safety; this test pins the contract so a
    future author touching either stub does not accidentally re-introduce
    the failure mode.
    """
    from pathlib import Path

    from drift import _plan_all_tasks_complete, _ANY_TASK_HEADER

    plan_path = Path(__file__).resolve().parent.parent / "planning" / "claude-plan-tdd.md"
    if not plan_path.exists():
        pytest.skip("plan file absent; test only meaningful in own-cycle dogfood")
    plan = plan_path.read_text(encoding="utf-8")

    # Top-level invariant: state=done + this plan -> drift detector returns [x].
    assert _plan_all_tasks_complete(plan) == "[x]", (
        "Plan should be fully complete; T2/T9 stubs must not introduce open checkboxes."
    )

    # Structural invariant: every header visited by drift detector regex must
    # NOT correspond to an ABSORBED/DEFERRED stub that carries open checkboxes.
    headers = list(_ANY_TASK_HEADER.finditer(plan))
    for i, match in enumerate(headers):
        header_line_start = plan.rfind("\n", 0, match.start()) + 1
        header_line_end = plan.find("\n", match.start())
        header_line = plan[header_line_start:header_line_end]
        section_start = match.end()
        section_end = headers[i + 1].start() if i + 1 < len(headers) else len(plan)
        section = plan[section_start:section_end]
        is_stub = "ABSORBED" in header_line or "DEFERRED" in header_line
        if is_stub:
            assert "- [ ]" not in section, (
                f"ABSORBED/DEFERRED stub header `{header_line}` carries `- [ ]` "
                f"markers in body; drift detector will flag false-positive when "
                f"state=done. Collapse to non-h3 form OR strip body checkboxes."
            )


def test_detect_drift_done_with_no_current_task_and_all_tasks_complete(tmp_path, monkeypatch):
    """state=done + current_task_id=None + plan fully flipped -> no drift.

    Regression for the 2026-04-24 false-positive: after a successful v0.2
    auto task loop (all 28 chores landed, every task section flipped to
    ``[x]``), two infrastructure-fix commits landed on top. The
    pre-merge drift check flagged false drift because the old hard-coded
    ``plan_task_state = "[ ]"`` fallback (when ``current_task_id`` is
    None) made ``_evaluate_drift`` report "state is done but plan still
    has open tasks". Fix: inspect the plan and compute the real
    all-complete signal via ``_plan_all_tasks_complete``.
    """
    import json

    from drift import detect_drift

    state_path = tmp_path / ".claude" / "session-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": None,
                "current_task_title": None,
                "current_phase": "done",
                "phase_started_at_commit": "deadbeef",
                "last_verification_at": None,
                "last_verification_result": "passed",
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        )
    )
    plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
    plan_path.parent.mkdir(parents=True)
    # Every task section fully flipped.
    plan_path.write_text(
        "### Task 1: alpha\n- [x] step 1\n\n### Task 2: beta\n- [x] step 1\n- [x] step 2\n"
    )

    class _Result:
        returncode = 0
        stdout = "fix: some post-plan infrastructure change\n"
        stderr = ""

    import subprocess_utils

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", lambda *a, **kw: _Result())

    assert detect_drift(state_file_path=state_path, plan_path=plan_path, repo_root=tmp_path) is None


def test_detect_drift_io_wrapper_returns_none_when_consistent(tmp_path, monkeypatch):
    import json

    from drift import detect_drift

    state_path = tmp_path / ".claude" / "session-state.json"
    state_path.parent.mkdir(parents=True)
    state_path.write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": "1",
                "current_task_title": "t",
                "current_phase": "red",
                "phase_started_at_commit": "deadbeef",
                "last_verification_at": None,
                "last_verification_result": None,
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        )
    )

    plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("### Task 1: do something\n- [ ] step 1\n")

    def fake_run(cmd, **kw):
        class R:
            returncode = 0
            stdout = "chore: mark task 0 complete\n"
            stderr = ""

        return R()

    import subprocess_utils

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)

    assert (
        detect_drift(
            state_file_path=state_path,
            plan_path=plan_path,
            repo_root=tmp_path,
        )
        is None
    )



class TestPlanAllTasksCompleteLineAnchored:
    """v1.0.7 B5 drift detector line-anchored regex per spec sec.4.4."""

    def test_codeblock_open_checkbox_does_not_false_positive(self) -> None:
        """B5-1: `- [ ]` inside Python string literal (code block) ignored."""
        from drift import _plan_all_tasks_complete

        plan = (
            "### Task 1: A\n"
            "- [x] Step 1\n"
            "    Example fixture content:\n"
            "    ```python\n"
            '    text = "- [ ] Step 1\\n"\n'
            "    ```\n"
            "### Task 2: B\n"
            "- [x] Step 1\n"
        )
        assert _plan_all_tasks_complete(plan) == "[x]"

    def test_real_open_checkbox_at_line_start_detected(self) -> None:
        """B5-2: legit `- [ ]` at line start still flags incomplete."""
        from drift import _plan_all_tasks_complete

        plan = "### Task 1: A\n- [ ] Step 1\n### Task 2: B\n- [x] Step 1\n"
        assert _plan_all_tasks_complete(plan) == "[ ]"

    def test_indented_open_checkbox_detected(self) -> None:
        """B5 partial: indented `  - [ ]` still flags incomplete."""
        from drift import _plan_all_tasks_complete

        plan = "### Task 1: A\n  - [ ] indented step\n### Task 2: B\n- [x] Step 1\n"
        assert _plan_all_tasks_complete(plan) == "[ ]"
