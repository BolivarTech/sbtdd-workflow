#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Exit 8 enriched audit-trail tests (Milestone D Task 4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import auto_cmd
from errors import MAGIGateError


def test_magi_gate_error_typed_attributes() -> None:
    # Scope-addition regression: the new kw-only attributes exist with
    # safe defaults when omitted (back-compat for any legacy raiser) and
    # are populated when provided.
    legacy = MAGIGateError("boom")
    assert legacy.accepted_conditions == ()
    assert legacy.rejected_conditions == ()
    assert legacy.verdict is None
    assert legacy.iteration is None

    enriched = MAGIGateError(
        "MAGI iter 1 produced 2 accepted condition(s)",
        accepted_conditions=("Refactor X", "Rename Y"),
        rejected_conditions=("Add broken thing",),
        verdict="GO_WITH_CAVEATS",
        iteration=1,
    )
    assert enriched.accepted_conditions == ("Refactor X", "Rename Y")
    assert enriched.rejected_conditions == ("Add broken thing",)
    assert enriched.verdict == "GO_WITH_CAVEATS"
    assert enriched.iteration == 1


def test_auto_cmd_exit8_records_condition_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Simulate _phase3_pre_merge raising MAGIGateError with typed
    # attributes. The MAGIGateError handling branch in main MUST include
    # those counts in the AutoRunAudit written to auto-run.json. The
    # tasks_completed value comes from the most recent incremental audit
    # write performed during Phase 2 (iter 2 revision -- raise-safe partial
    # counts, no frozen-attribute hackery and no tuple return).
    state_dir = tmp_path / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)

    def fake_phase1(ns: Any) -> tuple[Any, Any]:
        return (None, None)

    # Task 4 keeps `_phase2_task_loop` returning `state` only (signature
    # unchanged). Each task close inside the loop incrementally rewrites
    # auto-run.json with the running `tasks_completed` count; the fake
    # below mimics that behavior so the MAGIGateError handler can re-read
    # the last persisted count.
    def fake_phase2(ns: Any, state: Any, cfg: Any) -> Any:
        audit = auto_cmd.AutoRunAudit(
            schema_version=1,
            auto_started_at="2026-04-19T10:00:00Z",
            auto_finished_at=None,
            status="success",
            verdict=None,
            degraded=None,
            accepted_conditions=0,
            rejected_conditions=0,
            tasks_completed=2,  # 2 tasks closed before gate blocked
            error=None,
        )
        auto_cmd._write_auto_run_audit(tmp_path / ".claude" / "auto-run.json", audit)
        return state

    def fake_phase3(ns: Any, cfg: Any) -> Any:
        raise MAGIGateError(
            "MAGI iter 1 produced 2 accepted condition(s); "
            "apply them via `sbtdd close-phase` and re-run `sbtdd pre-merge`. "
            "See .claude/magi-conditions.md.",
            accepted_conditions=("Refactor X", "Rename Y"),
            rejected_conditions=("Add broken thing",),
            verdict="GO_WITH_CAVEATS",
            iteration=1,
        )

    # Make the dry-run branch NOT trigger. The fake_phase1 returns dummy
    # state/cfg so main proceeds into phase2.
    class _FakeState:
        current_phase = "red"
        current_task_id = None
        plan_approved_at = "2026-04-19T09:00:00Z"

    def fake_phase1_real(ns: Any) -> tuple[Any, Any]:
        return (_FakeState(), None)

    monkeypatch.setattr(auto_cmd, "_phase1_preflight", fake_phase1_real)
    monkeypatch.setattr(auto_cmd, "_phase2_task_loop", fake_phase2)
    monkeypatch.setattr(auto_cmd, "_phase3_pre_merge", fake_phase3)

    with pytest.raises(MAGIGateError):
        auto_cmd.main(["--project-root", str(tmp_path)])

    audit_file = tmp_path / ".claude" / "auto-run.json"
    assert audit_file.exists()
    data = json.loads(audit_file.read_text("utf-8"))
    assert data["status"] == "magi_gate_blocked"
    assert data["accepted_conditions"] == 2
    assert data["rejected_conditions"] == 1
    assert data["tasks_completed"] == 2
    assert data["verdict"] == "GO_WITH_CAVEATS"
    captured = capsys.readouterr()
    assert "accepted=2" in captured.err
    assert "rejected=1" in captured.err


def test_auto_cmd_exit8_strong_no_go_records_zero_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # STRONG_NO_GO has no conditions; MAGIGateError is raised with
    # default empty tuples. Audit trail MUST record 0/0 without
    # failure (no regex parse, no crash on empty tuples).
    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)

    class _FakeState:
        current_phase = "done"
        current_task_id = None
        plan_approved_at = "2026-04-19T09:00:00Z"

    def fake_phase1(ns: Any) -> tuple[Any, Any]:
        return (_FakeState(), None)

    # STRONG_NO_GO can fire in Phase 3 without any Phase 2 tasks
    # completing (e.g., plan has 0 done tasks when the gate blocks on
    # first iter). Phase 2 writes no audit; the handler must default to
    # tasks_completed=0 when the file is absent. Because state.current_phase
    # is "done", Phase 2 is skipped (main() branch).
    def fake_phase3(ns: Any, cfg: Any) -> Any:
        raise MAGIGateError("MAGI STRONG_NO_GO at iter 1", verdict="STRONG_NO_GO")

    monkeypatch.setattr(auto_cmd, "_phase1_preflight", fake_phase1)
    monkeypatch.setattr(auto_cmd, "_phase3_pre_merge", fake_phase3)

    with pytest.raises(MAGIGateError):
        auto_cmd.main(["--project-root", str(tmp_path)])

    data = json.loads((tmp_path / ".claude" / "auto-run.json").read_text("utf-8"))
    assert data["accepted_conditions"] == 0
    assert data["rejected_conditions"] == 0
    assert data["verdict"] == "STRONG_NO_GO"
    assert data["tasks_completed"] == 0
