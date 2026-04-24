# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Red-phase tests for Task G8: ``finalize_cmd --override-checkpoint --reason``.

These tests exercise the Feature A escape-valve wiring inside
``finalize_cmd.main``. They are expected to FAIL at Red phase because:

* ``finalize_cmd._build_parser`` does not yet accept ``--override-checkpoint``
  or ``--reason`` (argparse will raise ``SystemExit(2)`` on the unknown flags).
* ``finalize_cmd.main`` does not yet consult ``ns.override_checkpoint`` before
  the degraded-verdict checklist reject path, so a ``GO`` + ``degraded=True``
  verdict will still raise :class:`ChecklistError` even when ``--override-
  checkpoint --reason "<text>"`` is supplied.
* The override path does not yet synthesise an :class:`EscalationContext`
  from ``.claude/magi-verdict.json`` nor call
  :func:`escalation_prompt.apply_decision`, so no audit artifact is written
  under ``.claude/magi-escalations/``.

The failures MUST be feature-missing failures, not import errors, so all
referenced symbols already exist in v0.2 (``finalize_cmd``, ``MAGIGateError``,
``ChecklistError``, ``escalation_prompt.apply_decision``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Local fixture helpers -- self-contained (convention: every test_*.py is
# standalone; do not import private helpers from sibling test modules).
# ---------------------------------------------------------------------------


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo with one initial commit so HEAD resolves."""
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
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into tmp_path/.claude."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_plan_all_done(tmp_path: Path) -> Path:
    """Write a plan where every task is marked ``[x]``."""
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    plan.write_text(
        "# Plan\n\n### Task 1: done\n- [x] step\n\n### Task 2: done\n- [x] step\n",
        encoding="utf-8",
    )
    return plan


def _seed_spec_files(tmp_path: Path) -> None:
    """Write minimal sbtdd/spec-behavior.md so the checklist item passes."""
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec-behavior.md").write_text("# behavior\n", encoding="utf-8")


def _seed_state_done(tmp_path: Path) -> Path:
    """Write a valid session-state.json with ``current_phase='done'``."""
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    state = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": None,
        "current_task_title": None,
        "current_phase": "done",
        "phase_started_at_commit": "abc1234",
        "last_verification_at": "2026-04-24T03:30:00Z",
        "last_verification_result": "passed",
        "plan_approved_at": "2026-04-24T01:00:00Z",
    }
    state_path = claude / "session-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _seed_magi_verdict(
    tmp_path: Path,
    *,
    verdict: str = "GO",
    degraded: bool = True,
    timestamp: str = "2026-04-24T02:00:00Z",
) -> Path:
    """Write a magi-verdict.json artifact (degraded by default for override tests)."""
    path = tmp_path / ".claude" / "magi-verdict.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": timestamp,
        "verdict": verdict,
        "degraded": degraded,
        "conditions": [],
        "findings": [],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _seed_finalize_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    verdict: str = "GO",
    degraded: bool = True,
) -> None:
    """Seed an environment where every checklist item passes except the
    degraded / threshold gate -- so only the MAGI gate can block ``main``.

    Side effects:

    * git repo initialised with one commit,
    * plan + spec tracked (so ``git status`` stays clean),
    * ``.claude/`` gitignored so state + verdict do not dirty the tree,
    * ``verification_before_completion`` stubbed to a no-op,
    * ``finishing_a_development_branch`` stubbed to a no-op.
    """
    import superpowers_dispatch

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_spec_files(tmp_path)
    _seed_plan_all_done(tmp_path)
    (tmp_path / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "sbtdd", "planning"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: seed spec and plan"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    _seed_state_done(tmp_path)
    _seed_magi_verdict(tmp_path, verdict=verdict, degraded=degraded)

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", lambda **kw: None)
    monkeypatch.setattr(superpowers_dispatch, "finishing_a_development_branch", lambda **kw: None)


# ---------------------------------------------------------------------------
# Red-phase assertions
# ---------------------------------------------------------------------------


def test_finalize_override_bypasses_degraded_reject_and_writes_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--override-checkpoint --reason`` bypasses the INV-28 degraded reject.

    Baseline (covered by ``test_finalize_rejects_degraded_verdict_even_above_threshold``):
    ``GO`` + ``degraded=True`` raises :class:`ChecklistError`.

    With ``--override-checkpoint --reason "<text>"`` the same verdict must:

    1. Not raise -- ``main`` returns ``0``.
    2. Invoke :func:`escalation_prompt.apply_decision` which writes an audit
       artifact under ``<root>/.claude/magi-escalations/*.json``.
    3. The audit payload records ``decision=="override"`` and preserves the
       user-supplied ``reason``.
    """
    import finalize_cmd

    _seed_finalize_env(tmp_path, monkeypatch, verdict="GO", degraded=True)

    rc = finalize_cmd.main(
        [
            "--project-root",
            str(tmp_path),
            "--override-checkpoint",
            "--reason",
            "INV-0 manual override: degraded verdict accepted",
        ]
    )
    assert rc == 0, f"override path must return 0, got {rc}"

    audit_dir = tmp_path / ".claude" / "magi-escalations"
    audits = list(audit_dir.glob("*.json")) if audit_dir.is_dir() else []
    assert audits, f"expected >= 1 audit artifact under {audit_dir}, found {audits!r}"

    payload = json.loads(audits[0].read_text(encoding="utf-8"))
    assert payload["decision"] == "override", payload
    assert payload["reason"] == "INV-0 manual override: degraded verdict accepted", payload
    # _plan_id_from_path returns "X" for the default plain ``claude-plan-tdd.md``.
    assert payload["plan_id"] == "X", payload


def test_finalize_override_without_reason_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``--override-checkpoint`` alone (no ``--reason``) must error out.

    Mirrors :mod:`pre_merge_cmd` precedent (``raise MAGIGateError("--override-
    checkpoint requires --reason")``) -- the override path cannot be used
    anonymously; the audit trail is only meaningful if the user articulates
    why they are bypassing the MAGI gate.
    """
    import finalize_cmd
    from errors import SBTDDError

    _seed_finalize_env(tmp_path, monkeypatch, verdict="GO", degraded=True)

    with pytest.raises(SBTDDError):
        finalize_cmd.main(
            [
                "--project-root",
                str(tmp_path),
                "--override-checkpoint",
            ]
        )

    # No audit artifact should be written on the error path -- the override
    # contract requires a reason up front, and ``apply_decision`` must never
    # be invoked without one.
    audit_dir = tmp_path / ".claude" / "magi-escalations"
    audits = list(audit_dir.glob("*.json")) if audit_dir.is_dir() else []
    assert not audits, f"override-without-reason must not write an audit artifact, found {audits!r}"
