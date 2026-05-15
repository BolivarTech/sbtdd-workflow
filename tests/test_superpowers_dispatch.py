#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for superpowers_dispatch module."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

import superpowers_dispatch
from errors import PreconditionError


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


# ---------------------------------------------------------------------------
# v1.0.1 Item A2 -- headless-mode detection (sec.2.3 / sec.4 escenarios
# A2-1 .. A2-5). Skills in ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` raise
# ``PreconditionError`` before subprocess spawn unless the caller opts
# into ``allow_interactive_skill=True`` (Pre-A2 migration done; wrappers
# already pass the override automatically).
# ---------------------------------------------------------------------------


def test_a2_1_brainstorming_headless_raises_precondition(monkeypatch):
    """A2-1: invoke_skill('brainstorming') raises before subprocess spawn.

    Default ``allow_interactive_skill=False`` triggers the gate.
    """
    from errors import PreconditionError
    from superpowers_dispatch import invoke_skill

    # Sentinel: subprocess MUST NOT be reached.
    def explosive_run(*a, **kw):  # pragma: no cover -- guarded by raise
        raise AssertionError("subprocess spawned despite A2 gate")

    monkeypatch.setattr("subprocess_utils.run_with_timeout", explosive_run)
    with pytest.raises(PreconditionError) as ei:
        invoke_skill("brainstorming", args=["@spec.md"])
    msg = str(ei.value)
    assert "brainstorming" in msg, msg
    assert "interactivo" in msg.lower() or "subprocess" in msg.lower(), msg


def test_a2_2_writing_plans_headless_raises_precondition(monkeypatch):
    """A2-2: invoke_skill('writing-plans') raises before subprocess spawn."""
    from errors import PreconditionError
    from superpowers_dispatch import invoke_skill

    def explosive_run(*a, **kw):  # pragma: no cover
        raise AssertionError("subprocess spawned despite A2 gate")

    monkeypatch.setattr("subprocess_utils.run_with_timeout", explosive_run)
    with pytest.raises(PreconditionError) as ei:
        invoke_skill("writing-plans", args=["@spec.md"])
    msg = str(ei.value)
    assert "writing-plans" in msg, msg


def test_a2_3_magi_skill_unaffected_regression(monkeypatch):
    """A2-3: ``magi:magi`` (or other non-interactive skill) keeps working.

    ``magi:magi`` is NOT in ``_SUBPROCESS_INCOMPATIBLE_SKILLS``; gate
    short-circuits and subprocess flow proceeds.
    """
    from superpowers_dispatch import SkillResult, invoke_skill

    class FakeProc:
        returncode = 0
        stdout = "magi output"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    result = invoke_skill("magi:magi", args=["@spec.md"])
    assert isinstance(result, SkillResult)
    assert result.stdout == "magi output"


def test_a2_4_unknown_skill_passes_through_whitelist_semantic(monkeypatch):
    """A2-4: skills NOT in the set pass through the gate (whitelist semantic).

    Conservative-by-default: only demonstrably-broken skills are gated.
    Future skills not in the set behave identically to v1.0.0 (subprocess
    spawned). This regression-guards against accidentally widening the
    gate to a blacklist.
    """
    from superpowers_dispatch import SkillResult, invoke_skill

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    # ``custom-skill`` not in _SUBPROCESS_INCOMPATIBLE_SKILLS: must pass.
    result = invoke_skill("custom-skill", args=["@x.md"])
    assert isinstance(result, SkillResult)


def test_a2_5_wrapper_call_passes_override_internally(monkeypatch):
    """A2-5: high-level ``brainstorming`` wrapper bypasses the gate.

    Wrappers ARE the safe coordinated dispatch path; they pass
    ``allow_interactive_skill=True`` internally (Pre-A2 migration), so
    the gate short-circuits and the subprocess flow proceeds. This
    regression-guards against a blanket-raise pattern that would force
    every wrapper to bypass the gate by hand.
    """
    from superpowers_dispatch import SkillResult, brainstorming

    class FakeProc:
        returncode = 0
        stdout = "wrapper bypass works"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    # Wrapper invokes invoke_skill with allow_interactive_skill=True (per
    # Pre-A2 inspect-based forwarding); the gate must short-circuit.
    result = brainstorming(args=["@spec.md"])
    assert isinstance(result, SkillResult)
    assert result.stdout == "wrapper bypass works"


# ---------------------------------------------------------------------------
# v1.0.4 Item A.1 (Task 1, ABSORBS Task 2) -- _SUBPROCESS_INCOMPATIBLE_SKILLS
# extension + module docstring audit history.
# Covers escenarios A-2 (set semantics) + A-5 (set membership + doc coherence)
# from spec sec.4.1 (post iter 1 triage: A-3 + A-4 env-var escenarios DROPPED
# per CRITICAL #1+#2 simplification).
# ---------------------------------------------------------------------------


class TestSubprocessIncompatibleSkillsExtended:
    """v1.0.4 Item A.1 escenarios A-2 + A-5 -- set extension + docstring audit history."""

    def test_a5_receiving_code_review_in_incompatible_set(self):
        """A-5: receiving-code-review extended in v1.0.4."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "receiving-code-review" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_a5_brainstorming_writing_plans_preserved_v101(self):
        """A-5: v1.0.1 baseline (brainstorming, writing-plans) preserved."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "brainstorming" in _SUBPROCESS_INCOMPATIBLE_SKILLS
        assert "writing-plans" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_a2_set_is_frozenset_immutable(self):
        """A-2: set is frozenset to prevent runtime mutation."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert isinstance(_SUBPROCESS_INCOMPATIBLE_SKILLS, frozenset)

    def test_a5_module_docstring_documents_audit_history(self):
        """A-5 doc-coherence: module docstring records v1.0.1 + v1.0.4 additions."""
        import superpowers_dispatch

        docstring = superpowers_dispatch.__doc__ or ""
        assert "v1.0.1" in docstring
        assert "brainstorming" in docstring
        assert "writing-plans" in docstring
        assert "v1.0.4" in docstring
        assert "receiving-code-review" in docstring

    def test_a5_module_docstring_documents_gate_semantics(self):
        """A-5 doc-coherence (post iter 1 triage): module docstring documents
        membership-based gate semantics (NOT env-var/isatty heuristic)."""
        import superpowers_dispatch

        docstring = superpowers_dispatch.__doc__ or ""
        assert "BLOCKED UNCONDITIONALLY" in docstring
        assert "allow_interactive_skill=True" in docstring
        assert "NO env-var/isatty heuristic" in docstring


# ---------------------------------------------------------------------------
# v1.0.4 Item A.2 (Task 3) -- invoke_skill membership gate.
# Covers escenarios A-1 (gate fires unconditionally + no subprocess spawn),
# A-3 (allow_interactive_skill=True bypasses), A-4 (existing wrappers
# backward-compat), A-5 (skills NOT in set pass through) from spec sec.4.1.
# Project convention: monkeypatch ``subprocess_utils.run_with_timeout``
# rather than ``subprocess.run`` (production code goes through the helper);
# args=[...] list per invoke_skill signature.
# ---------------------------------------------------------------------------


class TestInvokeSkillMembershipGate:
    """v1.0.4 Item A.2 escenarios A-1, A-3, A-4, A-5 -- invoke_skill gate."""

    def test_a1_receiving_code_review_raises_unconditionally(self, monkeypatch):
        """A-1: invoke_skill('receiving-code-review', ...) raises without override."""
        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        def explosive_run(*a, **kw):  # pragma: no cover -- guarded by raise
            raise AssertionError("subprocess spawned despite v1.0.4 Item A gate")

        monkeypatch.setattr("subprocess_utils.run_with_timeout", explosive_run)
        with pytest.raises(PreconditionError) as exc_info:
            invoke_skill("receiving-code-review", args=["any prompt"])
        msg = str(exc_info.value)
        assert "Skill `/receiving-code-review` cannot run via `claude -p` subprocess" in msg
        assert "empirically incompatible" in msg

    def test_a1_no_subprocess_spawned_when_blocked(self, monkeypatch):
        """A-1: PreconditionError raised BEFORE subprocess spawn (run_with_timeout not called)."""
        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        calls: list[Any] = []

        def fake_run(*a, **kw):  # pragma: no cover -- must NOT be reached
            calls.append((a, kw))
            raise AssertionError("subprocess spawned despite gate")

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        with pytest.raises(PreconditionError):
            invoke_skill("receiving-code-review", args=["any prompt"])
        assert calls == [], "subprocess_utils.run_with_timeout was invoked"

    def test_a3_allow_interactive_skill_bypasses_gate(self, monkeypatch):
        """A-3: allow_interactive_skill=True bypasses gate (override active)."""
        from superpowers_dispatch import SkillResult, invoke_skill

        class FakeProc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        called: list[Any] = []

        def fake_run(cmd, timeout, capture=True, cwd=None):
            called.append(cmd)
            return FakeProc()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        result = invoke_skill(
            "receiving-code-review",
            args=["any prompt"],
            allow_interactive_skill=True,
        )
        assert isinstance(result, SkillResult)
        assert len(called) == 1, "subprocess should be spawned when override is True"

    def test_a4_brainstorming_wrapper_backward_compat(self, monkeypatch):
        """A-4: existing brainstorming wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import SkillResult, brainstorming

        class FakeProc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        called: list[Any] = []

        def fake_run(cmd, timeout, capture=True, cwd=None):
            called.append(cmd)
            return FakeProc()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        result = brainstorming(args=["any prompt"])
        assert isinstance(result, SkillResult)
        assert len(called) == 1, "wrapper should bypass gate via override"

    def test_a4_writing_plans_wrapper_backward_compat(self, monkeypatch):
        """A-4: existing writing_plans wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import SkillResult, writing_plans

        class FakeProc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        called: list[Any] = []

        def fake_run(cmd, timeout, capture=True, cwd=None):
            called.append(cmd)
            return FakeProc()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        result = writing_plans(args=["any prompt"])
        assert isinstance(result, SkillResult)
        assert len(called) == 1, "wrapper should bypass gate via override"

    def test_a5_skills_not_in_set_pass_through(self, monkeypatch):
        """A-5: skills NOT in _SUBPROCESS_INCOMPATIBLE_SKILLS pass through."""
        from superpowers_dispatch import SkillResult, invoke_skill

        class FakeProc:
            returncode = 0
            stdout = "ok"
            stderr = ""

        called: list[Any] = []

        def fake_run(cmd, timeout, capture=True, cwd=None):
            called.append(cmd)
            return FakeProc()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        result = invoke_skill("systematic-debugging", args=["any prompt"])
        assert isinstance(result, SkillResult)
        assert len(called) == 1, "non-incompatible skills should pass through gate"

    def test_a1_gate_fires_in_tty_session(self, monkeypatch):
        """A-1 (post iter 1 triage CRITICAL #1+#2): gate fires regardless of TTY state.

        This is the key fix vs caspar's CRITICAL -- operator main session has
        TTY=True but gate must STILL fire to prevent v1.0.3 hang. Test
        emulates the TTY-true main-session scenario by monkeypatching
        ``sys.stdin.isatty`` and confirms the gate is unaffected.
        """
        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        # Even if some hypothetical TTY-detection heuristic evaluates True,
        # the gate must NOT depend on it. Force isatty=True and confirm the
        # gate still fires.
        monkeypatch.setattr("sys.stdin.isatty", lambda: True)

        def explosive_run(*a, **kw):  # pragma: no cover -- guarded by raise
            raise AssertionError("subprocess spawned despite gate (TTY=True)")

        monkeypatch.setattr("subprocess_utils.run_with_timeout", explosive_run)
        with pytest.raises(PreconditionError):
            invoke_skill("receiving-code-review", args=["any prompt"])


# ---------------------------------------------------------------------------
# v1.0.4 Item B (Task 4) -- _build_recovery_message + _PER_SKILL_RECOVERY +
# _GENERIC_RECOVERY.
# Covers escenarios B-1 (recovery options included), B-2 (per-skill paths),
# B-3 (no subprocess hang -- gate fires < 1s) from spec sec.4.2.
# Post iter 1 triage simplified: no env-var formatting (gate is membership-
# based, not heuristic-based).
# ---------------------------------------------------------------------------


class TestBuildRecoveryMessage:
    """v1.0.4 Item B escenarios B-1, B-2, B-3 -- recovery message."""

    def test_b1_message_includes_recovery_options(self):
        """B-1: PreconditionError message includes recovery options."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("receiving-code-review")
        assert "Skill `/receiving-code-review` cannot run via `claude -p` subprocess" in msg
        assert "empirically incompatible" in msg
        assert "Run `/receiving-code-review` manually" in msg
        assert "python skills/magi/scripts/run_magi.py" in msg
        assert "spec sec.6.4" in msg
        assert "allow_interactive_skill=True" in msg

    def test_b2_per_skill_recovery_brainstorming(self):
        """B-2: brainstorming recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("brainstorming")
        assert "Run `/brainstorming` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_writing_plans(self):
        """B-2: writing-plans recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("writing-plans")
        assert "Run `/writing-plans` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_receiving_code_review(self):
        """B-2: receiving-code-review recovery references run_magi.py + sec.6.4."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("receiving-code-review")
        assert "Run `/receiving-code-review` manually in interactive session" in msg
        assert "skills/magi/scripts/run_magi.py code-review" in msg
        assert "spec sec.6.4" in msg

    def test_b2_unknown_skill_uses_generic_recovery(self):
        """B-2: unknown skill name falls back to generic recovery message."""
        from superpowers_dispatch import _GENERIC_RECOVERY, _build_recovery_message

        msg = _build_recovery_message("never-shipped-skill")
        for line in _GENERIC_RECOVERY.splitlines():
            stripped = line.strip()
            if stripped:
                assert stripped in msg, f"Generic recovery line missing: {stripped!r}"

    def test_b3_no_subprocess_when_blocked_under_one_second(self, monkeypatch):
        """B-3: PreconditionError raised within 1 second (NOT 600s hang)."""
        import time

        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        def explosive_run(*a, **kw):  # pragma: no cover -- guarded by raise
            raise AssertionError("subprocess spawned despite v1.0.4 Item A gate")

        monkeypatch.setattr("subprocess_utils.run_with_timeout", explosive_run)
        start = time.monotonic()
        with pytest.raises(PreconditionError):
            invoke_skill("receiving-code-review", args=["any prompt"])
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Expected <1s; took {elapsed:.2f}s"


class TestInvokeSkillWorkerGuard:
    """v1.0.7 A2 Q2'=b worker-context runtime guard per spec sec.4.2 A2-5/A2-6."""

    def test_worker_env_with_incompatible_skill_raises_worker_bug_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-5: worker env + incompatible skill -> PreconditionError naming bug."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        # Pick any skill that's in the membership set.
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        with pytest.raises(PreconditionError, match="Worker subprocess attempted"):
            superpowers_dispatch.invoke_skill(skill, allow_interactive_skill=True)

    def test_orchestrator_unaffected_by_worker_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A2-6: no env var -> falls through to existing v1.0.4+v1.0.6 gates."""
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        # With allow_interactive_skill=True + no headless context, dispatch
        # would proceed; we monkeypatch run_with_timeout to short-circuit.
        captured: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            captured.append(cmd)
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        # Force non-headless context for this test.
        monkeypatch.setattr(
            "subprocess_utils.is_headless_context",
            lambda: False,
            raising=False,
        )
        result = superpowers_dispatch.invoke_skill(skill, allow_interactive_skill=True)
        assert result.returncode == 0
        assert captured  # subprocess WAS dispatched (no worker guard fired)

    def test_orchestrator_with_tty_dispatches_normally_pin_guard_ordering(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-8 (W1 carry-forward): pin guard ordering against future regressions.

        Verifies the v1.0.7 A2 worker check fires AFTER membership +
        BEFORE headless gate AND requires BOTH env var presence AND
        skill membership. Checking env var alone would trip on operator
        scripts that set SBTDD_AUTO_PARALLEL_WORKER=1 unrelated to
        --parallel context. Future refactors that reorder the guards
        must keep this test green.
        """
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        captured: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def _capture_run(cmd: list[str], **kw: Any) -> FakeResult:
            captured.append(cmd)
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", _capture_run)
        monkeypatch.setattr(
            "subprocess_utils.is_headless_context",
            lambda: False,
            raising=False,
        )
        # Orchestrator dispatch SHOULD proceed: not headless + override allowed.
        result = superpowers_dispatch.invoke_skill(skill, allow_interactive_skill=True)
        assert result.returncode == 0
        assert len(captured) == 1
        # Now flip the env var to verify the worker guard DOES fire.
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        with pytest.raises(PreconditionError, match="Worker subprocess attempted"):
            superpowers_dispatch.invoke_skill(skill, allow_interactive_skill=True)


# ---------------------------------------------------------------------------
# v1.0.8 Pillar A1: SBTDD_E2E_STUB_DISPATCH env var stub gate smoke test.
# Expanded gate regression suite lives in TestE2EStubGate (added by T3/A4).
# ---------------------------------------------------------------------------


def test_v108_a1_gate_smoke_test_driven_development_with_env_set(monkeypatch):
    """v1.0.8 A1-1 smoke: gate fires for /test-driven-development with env=1.

    Pins the minimum contract that T3 (A4 regression suite) expands on:
    when SBTDD_E2E_STUB_DISPATCH=1 AND "pytest" in sys.modules AND
    skill is stubbable, invoke_skill returns synthetic
    SkillResult(rc=0) WITHOUT spawning claude -p.

    Note: ``"pytest" in sys.modules`` is True by construction in this
    test because pytest is the runner; iter-2 carry-forward W11
    production safeguard does not interfere with test environments.
    """
    import sys

    import superpowers_dispatch
    from superpowers_dispatch import SkillResult

    # Sanity-check the pytest sys.modules runtime guard precondition
    # holds in this test environment (would fail in production where
    # pytest is not loaded).
    assert "pytest" in sys.modules, "test environment must have pytest loaded for the gate to fire"

    monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "v1.0.8 A1 regression: gate should have fired before "
            "subprocess_utils.run_with_timeout was reached"
        )

    monkeypatch.setattr(
        superpowers_dispatch.subprocess_utils,
        "run_with_timeout",
        _fail_if_called,
    )

    result = superpowers_dispatch.invoke_skill(
        "test-driven-development",
        args=["--phase=red"],
        allow_interactive_skill=True,
    )

    assert isinstance(result, SkillResult)
    assert result.returncode == 0
    assert result.skill == "test-driven-development"
    assert "[sbtdd e2e stub]" in result.stdout
    assert "test-driven-development" in result.stdout
    assert "SBTDD_E2E_STUB_DISPATCH=1" in result.stdout
    assert result.stderr == ""


class TestE2EStubGate:
    """v1.0.8 Pillar A4: regression tests for SBTDD_E2E_STUB_DISPATCH gate.

    Each test monkeypatches ``subprocess_utils.run_with_timeout`` at the
    bottom of the call chain so the gate at the top of
    :func:`superpowers_dispatch.invoke_skill` is exercised end-to-end
    (real ``invoke_skill`` execution; only the subprocess call is faked).
    Monkeypatching ``invoke_skill`` itself would break the gate test
    semantic (gate would never run).

    See ``sbtdd/spec-behavior.md`` v1.0.8 sec.4.4 escenarios A4-1..A4-3.
    """

    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """v1.0.8 A4-1 (covers A1-1 + A1-4): env=1 + stubbable skill -> stub."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

        def _fail(*args, **kwargs):
            raise AssertionError(
                "v1.0.8 A4-3 regression: subprocess attempted but gate should have fired"
            )

        monkeypatch.setattr(superpowers_dispatch.subprocess_utils, "run_with_timeout", _fail)

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert isinstance(result, SkillResult)
        assert result.returncode == 0
        assert result.skill == "test-driven-development"
        assert result.stderr == ""

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """v1.0.8 A4-2 (covers A1-2): env unset -> real path attempted."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.delenv("SBTDD_E2E_STUB_DISPATCH", raising=False)

        captured = {"called": False}

        def _capture(cmd, **kwargs):
            captured["called"] = True
            captured["cmd"] = cmd
            return type("_CP", (), {"returncode": 0, "stdout": "real", "stderr": ""})()

        monkeypatch.setattr(superpowers_dispatch.subprocess_utils, "run_with_timeout", _capture)

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-2 regression: gate fired even though env var unset; "
            "production path was incorrectly bypassed"
        )
        assert isinstance(result, SkillResult)
        assert result.returncode == 0
        # Real path returns subprocess output, not the stub marker.
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """v1.0.8 A4-3 (covers A1-3): env=1 + non-stubbable -> real path."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

        captured = {"called": False}

        def _capture(cmd, **kwargs):
            captured["called"] = True
            return type("_CP", (), {"returncode": 0, "stdout": "real", "stderr": ""})()

        monkeypatch.setattr(superpowers_dispatch.subprocess_utils, "run_with_timeout", _capture)

        # /verification-before-completion is in _SUBPROCESS_INCOMPATIBLE_SKILLS
        # but NOT in _E2E_STUBBABLE_SKILLS, so the v1.0.8 A1 gate must skip
        # it even with env var set. The v1.0.4 membership gate is bypassed
        # via allow_interactive_skill=True (production wrapper path).
        result = superpowers_dispatch.invoke_skill(
            "verification-before-completion",
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-3 regression: gate fired for a skill outside "
            "_E2E_STUBBABLE_SKILLS; production "
            "/verification-before-completion path was incorrectly bypassed"
        )
        assert isinstance(result, SkillResult)
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_stdout_contains_marker(self, monkeypatch):
        """v1.0.8 A4-4 (covers A1-4): stub stdout has '[sbtdd e2e stub]' literal."""
        import superpowers_dispatch

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils,
            "run_with_timeout",
            lambda *a, **kw: (_ for _ in ()).throw(AssertionError("subprocess attempted")),
        )

        result = superpowers_dispatch.invoke_skill(
            "systematic-debugging",
            args=[],
            allow_interactive_skill=True,
        )

        assert result.stdout.startswith("[sbtdd e2e stub] /"), (
            f"Expected stdout to start with '[sbtdd e2e stub] /' marker; got: {result.stdout!r}"
        )
        assert "systematic-debugging" in result.stdout
        assert "bypassed (SBTDD_E2E_STUB_DISPATCH=1)" in result.stdout
