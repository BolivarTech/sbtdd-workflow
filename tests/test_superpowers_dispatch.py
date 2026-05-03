#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for superpowers_dispatch module."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest


def test_skill_result_is_frozen_dataclass():
    from dataclasses import FrozenInstanceError

    from superpowers_dispatch import SkillResult

    res = SkillResult(skill="brainstorming", returncode=0, stdout="ok", stderr="")
    with pytest.raises(FrozenInstanceError):
        res.returncode = 1  # type: ignore[misc]


def test_invoke_skill_returns_skill_result_on_success(monkeypatch):
    from superpowers_dispatch import SkillResult, invoke_skill

    class FakeProc:
        returncode = 0
        stdout = "hello"
        stderr = ""

    calls: dict = {}

    def fake_run(cmd, timeout, capture=True, cwd=None):
        calls["cmd"] = cmd
        calls["timeout"] = timeout
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    # v1.0.1 Pre-A2 migration: brainstorming is in the
    # _SUBPROCESS_INCOMPATIBLE_SKILLS set; this direct invoke_skill test
    # exercises the underlying subprocess flow, not the gate, so it opts
    # into the wrapper-aware override.
    result = invoke_skill("brainstorming", args=["arg1"], timeout=42, allow_interactive_skill=True)
    assert isinstance(result, SkillResult)
    assert result.skill == "brainstorming"
    assert result.returncode == 0
    assert result.stdout == "hello"
    assert calls["timeout"] == 42
    # Must use shell=False (as list), no shell=True risk.
    assert isinstance(calls["cmd"], list)
    # Command must include skill invocation marker.
    assert any("brainstorming" in t for t in calls["cmd"])


def test_invoke_skill_raises_quota_on_quota_pattern(monkeypatch):
    from errors import QuotaExhaustedError
    from superpowers_dispatch import invoke_skill

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "Request rejected (429)"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(QuotaExhaustedError) as exc_info:
        # v1.0.1 Pre-A2 migration: opt into wrapper-aware override so the
        # quota-detection branch (post-subprocess) is exercised rather than
        # the new A2 gate (pre-subprocess).
        invoke_skill("brainstorming", allow_interactive_skill=True)
    assert "429" in str(exc_info.value) or "rate_limit" in str(exc_info.value)


def test_invoke_skill_non_quota_nonzero_raises_validation_error(monkeypatch):
    from errors import ValidationError
    from superpowers_dispatch import invoke_skill

    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "some unrelated error"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(ValidationError) as exc_info:
        # v1.0.1 Pre-A2 migration: opt into wrapper-aware override so the
        # returncode validation branch (post-subprocess) is exercised
        # rather than the A2 gate (pre-subprocess).
        invoke_skill("brainstorming", allow_interactive_skill=True)
    assert "returncode=2" in str(exc_info.value) or "returncode" in str(exc_info.value)


def test_invoke_skill_wraps_timeout_as_validation_error(monkeypatch):
    from errors import ValidationError
    from superpowers_dispatch import invoke_skill

    def fake_run(cmd, timeout, capture=True, cwd=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(ValidationError, match="timed out"):
        # v1.0.1 Pre-A2 migration: writing-plans is in the
        # _SUBPROCESS_INCOMPATIBLE_SKILLS set; opt into wrapper-aware
        # override so the timeout-handling branch is exercised.
        invoke_skill("writing-plans", allow_interactive_skill=True)


def test_typed_wrappers_cover_all_twelve_skills(monkeypatch):
    """One typed wrapper per superpowers skill; each calls invoke_skill."""
    from superpowers_dispatch import (
        SkillResult,
        brainstorming,
        dispatching_parallel_agents,
        executing_plans,
        finishing_a_development_branch,
        receiving_code_review,
        requesting_code_review,
        subagent_driven_development,
        systematic_debugging,
        test_driven_development,
        using_git_worktrees,
        verification_before_completion,
        writing_plans,
    )

    calls: list[str] = []

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        calls.append(skill)
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    brainstorming(["spec.md"])
    writing_plans(["behavior.md"])
    test_driven_development()
    verification_before_completion()
    requesting_code_review()
    receiving_code_review()
    executing_plans(["plan.md"])
    subagent_driven_development()
    dispatching_parallel_agents()
    systematic_debugging()
    using_git_worktrees()
    finishing_a_development_branch()
    assert calls == [
        "brainstorming",
        "writing-plans",
        "test-driven-development",
        "verification-before-completion",
        "requesting-code-review",
        "receiving-code-review",
        "executing-plans",
        "subagent-driven-development",
        "dispatching-parallel-agents",
        "systematic-debugging",
        "using-git-worktrees",
        "finishing-a-development-branch",
    ]


def test_typed_wrappers_forward_args_and_timeout(monkeypatch):
    from superpowers_dispatch import SkillResult, brainstorming

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["skill"] = skill
        captured["args"] = args
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    brainstorming(args=["x", "y"], timeout=900)
    assert captured["skill"] == "brainstorming"
    assert captured["args"] == ["x", "y"]
    assert captured["timeout"] == 900


def test_wrapper_monkeypatch_propagates_through_module_attr(monkeypatch):
    """Regression guard for the closure-rebind bug (MAGI ckpt2 CRITICAL 1)."""
    from superpowers_dispatch import SkillResult, brainstorming

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        return SkillResult(skill=skill, returncode=0, stdout="patched", stderr="")

    # Must patch via the module attribute, which the wrapper resolves at call time.
    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    result = brainstorming()
    assert result.stdout == "patched", (
        "wrapper closure captured invoke_skill; monkeypatch must replace "
        "module attribute and be picked up via sys.modules[__name__].invoke_skill"
    )


def test_requesting_code_review_default_timeout_is_1800s(monkeypatch):
    """``/requesting-code-review`` subprocess must default to 1800s.

    Empirical v0.2 pre-merge Loop 1 (2026-04-24): reviewing the full
    accumulated v0.2 diff (27 tasks worth of code + ~1500 lines of new
    tests) exceeded the 600s default. Same bucket as ``/writing-plans``
    and ``/test-driven-development``.
    """
    from superpowers_dispatch import SkillResult, requesting_code_review

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    requesting_code_review()
    assert captured["timeout"] == 1800


def test_test_driven_development_default_timeout_is_1800s(monkeypatch):
    """``/test-driven-development`` subprocess must default to 1800s.

    Empirical v0.2 auto run G2 green phase (2026-04-24): the subagent's
    combined read-plan + write-tests + implement + run-make-verify pass
    exceeds the 600s default on substantial tasks. Raising the per-skill
    default prevents the ``ValidationError: skill
    '/test-driven-development' timed out after 600s`` that killed auto
    mid-task. Same override mechanism as ``/writing-plans``.
    """
    from superpowers_dispatch import SkillResult, test_driven_development

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    test_driven_development(["--phase=green"])
    assert captured["timeout"] == 1800


def test_writing_plans_default_timeout_is_1800s(monkeypatch):
    """``/writing-plans`` subprocess must default to 1800s.

    Empirical v0.2 Checkpoint 2 run (2026-04-23): the subprocess exceeded
    600s even when ``planning/claude-plan-tdd-org.md`` was already fully
    written. Raising the per-skill default prevents the ``ValidationError:
    skill '/writing-plans' timed out after 600s`` that aborted
    ``/sbtdd spec`` before MAGI Checkpoint 2 could run.
    """
    from superpowers_dispatch import SkillResult, writing_plans

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    writing_plans(["@spec.md"])
    assert captured["timeout"] == 1800


def test_brainstorming_default_timeout_is_600s(monkeypatch):
    """Skills without a per-skill override keep the 600s default."""
    from superpowers_dispatch import SkillResult, brainstorming

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    brainstorming(["@spec-base.md"])
    assert captured["timeout"] == 600


def test_invoke_skill_packs_args_into_claude_p_prompt_string(monkeypatch):
    """Skill args MUST travel inside the claude -p prompt, not as separate argv.

    ``claude -p`` only understands its own CLI flags; skill-specific tokens
    like ``--phase=red`` or ``@file.md`` belong to the skill being invoked
    and have to live inside the prompt string so the sub-session forwards
    them. Appending them as separate argv after ``-p /<skill>`` causes
    ``claude`` to reject with ``error: unknown option '<flag>'``. Observed
    2026-04-24 when ``/sbtdd auto`` crashed at the first
    ``/test-driven-development --phase=red`` dispatch.
    """
    from superpowers_dispatch import invoke_skill

    captured: dict = {}

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    invoke_skill("test-driven-development", args=["--phase=red", "@task.md"])
    # argv must be exactly ["claude", "-p", "<single-prompt-string>"].
    assert captured["cmd"][:2] == ["claude", "-p"]
    assert len(captured["cmd"]) == 3, f"expected 3 argv entries, got {captured['cmd']!r}"
    prompt = captured["cmd"][2]
    # The prompt string must embed the slash command + both args.
    assert "/test-driven-development" in prompt
    assert "--phase=red" in prompt
    assert "@task.md" in prompt


def test_writing_plans_explicit_timeout_still_overrides(monkeypatch):
    """Caller-provided ``timeout=`` kwarg still wins over the per-skill default."""
    from superpowers_dispatch import SkillResult, writing_plans

    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    writing_plans(["@spec.md"], timeout=3600)
    assert captured["timeout"] == 3600


# ---------------------------------------------------------------------------
# v1.0.0 Feature H option 5 — invoke_writing_plans prompt extension
# (sec.3.3 H5-1; S2-7).
# ---------------------------------------------------------------------------


def test_h5_1_invoke_writing_plans_prompt_includes_scenario_stub_directive(monkeypatch):
    """H5-1: invoke_writing_plans prompt instructs auto-generate scenario stubs."""
    from superpowers_dispatch import invoke_writing_plans

    captured: dict[str, Any] = {}

    def fake_invoke(*, prompt: str, **kwargs: Any) -> dict[str, Any]:
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        return {"output": "stub plan content"}

    monkeypatch.setattr("superpowers_dispatch._invoke_skill", fake_invoke)
    invoke_writing_plans(spec_path="sbtdd/spec-behavior.md")
    assert "scenario stub" in captured["prompt"].lower()
    assert "pytest.skip" in captured["prompt"]


def test_h5_1_invoke_writing_plans_prompt_references_spec_path(monkeypatch):
    """H5-1: prompt names the spec_path so the sub-session knows where to read scenarios."""
    from superpowers_dispatch import invoke_writing_plans

    captured: dict[str, Any] = {}

    def fake_invoke(*, prompt: str, **kwargs: Any) -> dict[str, Any]:
        captured["prompt"] = prompt
        return {"output": ""}

    monkeypatch.setattr("superpowers_dispatch._invoke_skill", fake_invoke)
    invoke_writing_plans(spec_path="sbtdd/spec-behavior.md")
    assert "sbtdd/spec-behavior.md" in captured["prompt"]


def test_h5_1_invoke_writing_plans_passes_skill_kwarg(monkeypatch):
    """H5-1: invoke_writing_plans tells the wrapper which skill to invoke."""
    from superpowers_dispatch import invoke_writing_plans

    captured: dict[str, Any] = {}

    def fake_invoke(*, prompt: str, skill: str, **kwargs: Any) -> dict[str, Any]:
        captured["skill"] = skill
        return {"output": ""}

    monkeypatch.setattr("superpowers_dispatch._invoke_skill", fake_invoke)
    invoke_writing_plans(spec_path="sbtdd/spec-behavior.md")
    assert captured["skill"] == "writing-plans"
