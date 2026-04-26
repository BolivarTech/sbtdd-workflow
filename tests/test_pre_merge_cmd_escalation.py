# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Red-phase tests for Task G7: ``pre_merge_cmd`` -> ``escalation_prompt`` wiring.

These tests exercise the Feature A safety-valve integration point in
``pre_merge_cmd._loop2``. They are expected to FAIL at Red phase because:

* ``pre_merge_cmd._build_parser`` does not yet accept ``--override-checkpoint``,
  ``--reason``, or ``--non-interactive`` (argparse will exit 2).
* ``pre_merge_cmd._loop2`` does not import or call ``escalation_prompt`` on
  iteration-budget exhaustion -- it raises ``MAGIGateError`` directly without
  first invoking ``prompt_user`` or writing an audit artifact under
  ``.claude/magi-escalations/``.

The failures MUST be feature-missing failures, not import errors, so all
symbols referenced here already exist in v0.2 (``escalation_prompt``,
``UserDecision``, ``MAGIGateError``, ``MAGIVerdict``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Local fixture helpers -- self-contained (do not import private helpers
# from sibling test modules; convention: every test_*.py is standalone).
# ---------------------------------------------------------------------------


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


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into tmp_path/.claude."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo at tmp_path with one initial commit so HEAD resolves."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
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


def _seed_pre_merge_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up a full env for ``pre_merge_cmd.main`` end-to-end tests.

    - git repo with one initial commit,
    - state file with ``current_phase='done'``,
    - plan with every task marked ``[x]``,
    - python plugin.local.md,
    - drift detection bypassed (done+null-task-id heuristic false positive),
    - Loop 1 short-circuited via a ``clean-to-go`` skill stub,
    - MAGI verdict artifact write no-op'd (success-path safety).
    """
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from superpowers_dispatch import SkillResult

    _setup_git_repo(tmp_path)
    _seed_state_done(tmp_path)
    _seed_plan_all_done(tmp_path)
    _seed_plugin_local(tmp_path)

    def fake_requesting(
        args: list[str] | None = None,
        timeout: int = 600,
        cwd: str | None = None,
        **_kwargs: object,
    ) -> object:
        return SkillResult(skill="stub", returncode=0, stdout="Review: clean-to-go", stderr="")

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_requesting)
    # At state=done with current_task_id=None, the shipped drift heuristic
    # defaults to "[ ]" and trips the done+open-tasks rule. Bypass here so
    # the test focuses on Feature A wiring, not drift semantics.
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)
    # Prevent success-path writes from leaking real verdict JSON on disk.
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **kw: None)


def _make_verdict(label: str = "HOLD", degraded: bool = False) -> object:
    """Return a ``MAGIVerdict`` shaped like real MAGI output."""
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=(),
        findings=(),
        raw_output=f'{{"verdict": "{label}"}}',
    )


# ---------------------------------------------------------------------------
# Red-phase assertions
# ---------------------------------------------------------------------------


def test_pre_merge_cmd_escalates_on_safety_valve_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop 2 exhaustion must route through ``escalation_prompt``.

    When MAGI returns ``HOLD`` for all three iterations (default cap) in
    pre-merge Loop 2, ``pre_merge_cmd.main`` must:

    1. Invoke ``escalation_prompt.prompt_user(ctx, options, ...)`` exactly
       once on exhaustion.
    2. Call ``apply_decision`` which writes an audit artifact under
       ``<root>/.claude/magi-escalations/*.json``.
    3. Re-raise ``MAGIGateError`` when the prompt returns an ``abandon``
       decision (the default headless policy).
    """
    import escalation_prompt
    import magi_dispatch
    import pre_merge_cmd
    from errors import MAGIGateError
    from escalation_prompt import UserDecision

    _seed_pre_merge_env(tmp_path, monkeypatch)

    def fake_magi(
        context_paths: list[str],
        cwd: str | None = None,
        **_kwargs: object,
    ) -> object:
        return _make_verdict("HOLD", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)

    prompt_calls: list[dict[str, object]] = []

    def spy_prompt_user(
        ctx: object,
        options: object,
        *,
        non_interactive: bool = False,
        project_root: Path | None = None,
    ) -> UserDecision:
        prompt_calls.append(
            {
                "ctx": ctx,
                "options": options,
                "non_interactive": non_interactive,
                "project_root": project_root,
            }
        )
        return UserDecision(chosen_option="d", action="abandon", reason="user chose abandon")

    monkeypatch.setattr(escalation_prompt, "prompt_user", spy_prompt_user)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])

    # prompt_user must have been invoked exactly once on exhaustion.
    assert len(prompt_calls) == 1, (
        f"expected prompt_user to be called once on pre-merge Loop 2 exhaustion, "
        f"got {len(prompt_calls)} call(s)"
    )

    # apply_decision (invoked inside the wiring) must have produced an
    # audit artifact under .claude/magi-escalations/.
    audit_dir = tmp_path / ".claude" / "magi-escalations"
    audits = list(audit_dir.glob("*.json")) if audit_dir.is_dir() else []
    assert audits, f"expected >= 1 audit artifact under {audit_dir}, found {audits!r}"


def test_pre_merge_cmd_override_flag_skips_prompt_and_writes_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--override-checkpoint --reason bypasses the prompt and returns 0.

    When the user passes ``--override-checkpoint --reason "manual override"``,
    ``pre_merge_cmd.main`` must NOT invoke ``prompt_user``. It must still
    write the audit artifact (via ``apply_decision``) with
    ``decision=="override"``, ``reason=="manual override"``, and
    ``plan_id=="X"`` (the fallback value ``_plan_id_from_path`` returns for
    ``claude-plan-tdd.md`` with no suffix).
    """
    import escalation_prompt
    import magi_dispatch
    import pre_merge_cmd

    _seed_pre_merge_env(tmp_path, monkeypatch)

    def fake_magi(
        context_paths: list[str],
        cwd: str | None = None,
        **_kwargs: object,
    ) -> object:
        return _make_verdict("HOLD", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)

    def boom_prompt_user(*args: object, **kwargs: object) -> object:
        raise AssertionError("prompt_user must NOT be called when --override-checkpoint is set")

    monkeypatch.setattr(escalation_prompt, "prompt_user", boom_prompt_user)

    rc = pre_merge_cmd.main(
        [
            "--project-root",
            str(tmp_path),
            "--override-checkpoint",
            "--reason",
            "manual override",
        ]
    )
    assert rc == 0, f"override path must return 0, got {rc}"

    audit_dir = tmp_path / ".claude" / "magi-escalations"
    audits = list(audit_dir.glob("*.json")) if audit_dir.is_dir() else []
    assert len(audits) == 1, (
        f"expected exactly one audit artifact under {audit_dir}, got {audits!r}"
    )
    payload = json.loads(audits[0].read_text(encoding="utf-8"))
    assert payload["decision"] == "override", payload
    assert payload["reason"] == "manual override", payload
    # _plan_id_from_path returns "X" when plan filename has no -<ID>.md suffix
    # (plain "claude-plan-tdd.md" is the pre-merge default).
    assert payload["plan_id"] == "X", payload
