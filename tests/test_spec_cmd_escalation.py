# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Red-phase tests for Task G6: ``spec_cmd`` -> ``escalation_prompt`` wiring.

These tests exercise the Feature A safety-valve integration point in
``spec_cmd.main``. They are expected to FAIL at Red phase because:

* ``spec_cmd._build_parser`` does not yet accept ``--override-checkpoint``,
  ``--reason``, or ``--non-interactive`` (argparse will exit 2).
* ``spec_cmd._run_magi_checkpoint2`` does not import or call
  ``escalation_prompt`` on exhaustion -- it raises ``MAGIGateError``
  directly without first invoking ``prompt_user`` or writing an audit
  artifact under ``.claude/magi-escalations/``.

The failures MUST be feature-missing failures, not import errors, so all
symbols referenced here exist in v0.2 already (``escalation_prompt``,
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


def _seed_valid_spec_base(tmp_path: Path) -> Path:
    """Write a valid (INV-27-clean, >= 200 non-ws chars) spec-behavior-base.md."""
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature spec\n\n## Objetivo\nsomething meaningful\n" + ("valid content " * 50)
    path = spec_dir / "spec-behavior-base.md"
    path.write_text(body, encoding="utf-8")
    (tmp_path / "planning").mkdir()
    return path


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


def _seed_spec_flow_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up a full env for ``spec_cmd.main`` end-to-end tests."""
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)
    _setup_git_repo(tmp_path)

    def fake_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        # R10: minimal §4 so spec_snapshot.emit_snapshot finds a section.
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: stub**\n\n"
            "> **Given** g.\n> **When** w.\n> **Then** t.\n",
            encoding="utf-8",
        )
        return None

    def fake_writing_plans(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "# Plan\n\n### Task 1: First task\n- [ ] do it\n", encoding="utf-8"
        )
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", fake_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", fake_writing_plans)


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


def test_spec_cmd_escalates_on_safety_valve_exhaustion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Safety-valve exhaustion must route through ``escalation_prompt``.

    When MAGI returns ``HOLD`` for all three iterations (default cap),
    ``spec_cmd.main`` must:

    1. Invoke ``escalation_prompt.prompt_user(ctx, options, ...)``.
    2. Call ``apply_decision`` which writes an audit artifact under
       ``<root>/.claude/magi-escalations/*.json``.
    3. Re-raise ``MAGIGateError`` when the prompt returns an ``abandon``
       decision (the default headless policy).
    """
    import escalation_prompt
    import magi_dispatch
    import spec_cmd
    from errors import MAGIGateError
    from escalation_prompt import UserDecision

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
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
        spec_cmd.main(["--project-root", str(tmp_path)])

    # prompt_user must have been invoked exactly once on exhaustion.
    assert len(prompt_calls) == 1, (
        f"expected prompt_user to be called once on safety-valve exhaustion, "
        f"got {len(prompt_calls)} call(s)"
    )

    # apply_decision (invoked inside the wiring) must have produced an
    # audit artifact under .claude/magi-escalations/.
    audit_dir = tmp_path / ".claude" / "magi-escalations"
    audits = list(audit_dir.glob("*.json")) if audit_dir.is_dir() else []
    assert audits, f"expected >= 1 audit artifact under {audit_dir}, found {audits!r}"


def test_spec_cmd_override_flag_skips_prompt_and_writes_audit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--override-checkpoint --reason bypasses the prompt and returns 0.

    When the user passes ``--override-checkpoint --reason "manual override"``,
    ``spec_cmd.main`` must NOT invoke ``prompt_user``. It must still write
    the audit artifact (via ``apply_decision``) with ``decision=="override"``,
    ``reason=="manual override"``, and ``plan_id=="X"`` (the fallback value
    ``_plan_id_from_path`` returns for ``claude-plan-tdd.md`` with no suffix).
    """
    import escalation_prompt
    import magi_dispatch
    import spec_cmd

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("HOLD", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)

    def boom_prompt_user(*args: object, **kwargs: object) -> object:
        raise AssertionError("prompt_user must NOT be called when --override-checkpoint is set")

    monkeypatch.setattr(escalation_prompt, "prompt_user", boom_prompt_user)

    rc = spec_cmd.main(
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
    # (plain "claude-plan-tdd.md" is the Checkpoint 2 default).
    assert payload["plan_id"] == "X", payload
