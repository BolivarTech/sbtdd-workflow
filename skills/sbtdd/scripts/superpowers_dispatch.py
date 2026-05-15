#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dispatcher for superpowers skills (/<skill> via claude -p subprocess).

Transport: uses subprocess ``claude -p`` to invoke sub-skills across plugin
boundaries (the only available transport from Python code). Aligned with
MAGI v2.1.3 pattern and documented in CLAUDE.md External Dependencies.

The plugin invokes superpowers skills (``/brainstorming``, ``/writing-plans``,
``/requesting-code-review``, etc.) via the claude CLI. Each wrapper
materialises the invocation as a subprocess and converts failures into
typed :class:`errors.SBTDDError` subclasses so dispatchers at
``run_sbtdd.py`` map them to the sec.S.11.1 exit code taxonomy.

Quota exhaustion (sec.S.11.4) is detected on stderr via
:mod:`quota_detector` BEFORE a generic failure is reported -- the caller
then sees :class:`errors.QuotaExhaustedError` and exits 11.

Subprocess-incompatible skill audit history
-------------------------------------------

- v1.0.1 (Finding A discovery): brainstorming, writing-plans.
  Manifestation: silent no-op (subprocess returns without producing
  skill output). Caught post-spawn via INV-37 composite-signature
  check (v1.0.1 Item A0).
- v1.0.4 (v1.0.3 Activity D' empirical hang during Loop 1 fix-finding
  triage step): receiving-code-review. Manifestation: 600s subprocess
  hang waiting interactive input. Cannot be caught post-spawn
  (operator-blocking); requires pre-spawn gate.

A skill is subprocess-incompatible iff it requires multi-turn
interactive dialogue with the operator. Adding a new entry to the
set without empirical evidence (subprocess hang or silent-no-op
observed) is forbidden -- operators must run the skill manually in
interactive session and document the failure mode in CHANGELOG
before promoting.

Gate semantics (v1.0.4 post iter 1 triage): subprocess spawn for
incompatible skills is BLOCKED UNCONDITIONALLY unless caller passes
allow_interactive_skill=True. The override is the explicit opt-in
for known-safe wrappers that have arranged for subprocess success
(silent-no-op tolerated by v1.0.1 wrappers via INV-37 post-detection;
or operator-controlled interactive callsites). NO env-var/isatty heuristic
is used -- caspar Checkpoint 2 iter 1 CRITICAL verified the heuristic
does not fix the v1.0.3 bug in operator main sessions (TTY=True so the
gate would not fire, subprocess would spawn, hang persists).
"""

from __future__ import annotations

import os
import subprocess
import sys as _sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

import quota_detector
import subprocess_utils
from errors import PreconditionError, QuotaExhaustedError, ValidationError
from models import INV_0_PINNED_MODEL_RE


#: v1.0.1 Item A2 (sec.2.3) -- skills demonstrably broken under
#: ``claude -p`` headless subprocess transport. Empirically (v1.0.0
#: dogfood Finding A) ``/brainstorming`` and ``/writing-plans`` exit 0
#: but produce silently-empty output when invoked outside an interactive
#: Claude Code session. Whitelist semantic: only known-broken skills are
#: gated; unknown / future skills pass through unchanged.
#:
#: ``invoke_skill`` raises :class:`PreconditionError` BEFORE subprocess
#: spawn when the called skill is in this set unless the caller passes
#: ``allow_interactive_skill=True`` (which the Pre-A2 wrappers do
#: automatically). The error guides operators toward
#: ``/sbtdd spec --resume-from-magi`` (v1.0.1 Item A3) for recovery.
_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset(
    {
        "brainstorming",
        "writing-plans",
        # v1.0.4 (Item A.1, Task 1): added per v1.0.3 Activity D'
        # empirical hang. /receiving-code-review requires multi-turn
        # interactive triage of MAGI findings before the wrapper can
        # accept/reject each; subprocess spawn hung 600s waiting for
        # operator input.
        "receiving-code-review",
    }
)


#: v1.0.8 Pillar A1: env var name that activates the test-only stub
#: gate at the top of :func:`invoke_skill`. When set to ``"1"`` AND
#: :data:`_E2E_TEST_RUNNER_ENV` is also set to ``"1"``, skills in
#: :data:`_E2E_STUBBABLE_SKILLS` short-circuit to a synthetic
#: :class:`SkillResult` instead of spawning ``claude -p``.
#:
#: **Test-only**: production callers MUST NOT set this variable.
_E2E_STUB_ENV: str = "SBTDD_E2E_STUB_DISPATCH"

#: v1.0.8 Pillar A1 (T4 follow-up fix): second env var that AND-gates
#: with :data:`_E2E_STUB_ENV`. Two env vars required to fire the gate
#: provides defense-in-depth against accidental production leak —
#: requires BOTH vars to leak simultaneously (much less likely than
#: a single env var leak via shared shell profile / .env / devcontainer
#: template). The original v1.0.8 design used ``"pytest" in sys.modules``
#: but that breaks the legitimate e2e use case where a test parent
#: spawns a subprocess that inherits env vars but does NOT import
#: pytest in the subprocess process (run_sbtdd.py orchestrator).
#: Per Caspar iter-1 W11 explicit alternative recommendation:
#: "(b) AND-gate with a second env var".
_E2E_TEST_RUNNER_ENV: str = "SBTDD_E2E_TEST_RUNNER"

#: v1.0.8 Pillar A1: skills whose ``claude -p`` dispatch is bypassed
#: when :data:`_E2E_STUB_ENV` is set AND ``"pytest"`` is loaded.
#: Frozen via ``frozenset`` (style consistent with
#: :data:`_SUBPROCESS_INCOMPATIBLE_SKILLS`).
#:
#: Membership-bound list -- adding skills here requires explicit
#: rationale documented in CHANGELOG and approval through MAGI
#: Checkpoint 2 / pre-merge gate. v1.0.8 baseline scope is 2 skills
#: per Q1'=a decision: ``/test-driven-development`` (root cause of
#: the v1.0.7 T3 hang) + ``/systematic-debugging`` (used in
#: ``_run_verification_with_retries`` retry path; would surface the
#: same upstream bug class on a real verification failure).
_E2E_STUBBABLE_SKILLS: frozenset[str] = frozenset(
    {
        "test-driven-development",
        "systematic-debugging",
        # v1.0.8 T4: requesting-code-review subprocess hangs in headless
        # e2e context (no TTY). Stubbed under both env vars so the
        # orchestrator's phase 3 pre-merge Loop 1 short-circuits to a
        # synthetic clean review result.
        "requesting-code-review",
        # v1.0.8 T4: verification-before-completion can be invoked from
        # orchestrator code paths (e.g., review mini-cycle in phase 3)
        # that DO NOT carry SBTDD_AUTO_PARALLEL_WORKER=1. Stub so
        # orchestrator runs without TTY hang in e2e.
        "verification-before-completion",
        # v1.0.8 T4: receiving-code-review invoked via /receiving-code-review
        # in phase 3 mini-cycle; loops on iter-1/2/3 in headless e2e.
        # Stub to short-circuit the mini-cycle loop.
        "receiving-code-review",
    }
)


@dataclass(frozen=True)
class SkillResult:
    """Outcome of a successful skill invocation.

    Failures never reach the caller as a ``SkillResult`` -- they are raised
    as typed exceptions. ``returncode`` is therefore always ``0`` in
    practice but is preserved for diagnostic logs.
    """

    skill: str
    returncode: int
    stdout: str
    stderr: str


def _build_skill_cmd(
    skill: str,
    args: list[str] | None,
    model: str | None = None,
) -> list[str]:
    """Build the argv list for ``claude -p`` invoking ``skill``.

    The slash command and its args MUST be packed into the single prompt
    string passed to ``claude -p``. ``claude`` itself does not parse
    skill-specific flags like ``--phase=red`` or ``@file`` refs -- those
    belong to the skill being invoked and have to travel inside the prompt
    so the sub-session forwards them. Appending them as separate argv
    tokens after ``-p <skill>`` causes ``claude`` to reject them with
    ``error: unknown option '<flag>'``.

    When ``model`` is provided (v0.3.0 Feature E), ``--model <id>`` is
    inserted BEFORE the ``-p`` flag (claude CLI flag ordering convention).
    When ``model`` is None (default), argv is byte-identical to v0.2.x.

    Same pattern as :func:`magi_dispatch._build_magi_cmd` (sec.S.0.2
    cross-plugin dispatch contract).
    """
    prompt_parts = [f"/{skill}"]
    if args:
        prompt_parts.extend(args)
    cmd: list[str] = ["claude"]
    if model is not None:
        cmd.extend(["--model", model])
    cmd.extend(["-p", " ".join(prompt_parts)])
    return cmd


def _apply_inv0_model_check(
    configured_model: str | None,
    skill_field_name: str,
) -> str | None:
    """Apply INV-0 cascade: if ~/.claude/CLAUDE.md pins a model, ignore config.

    INV-0 (sec.S.10.0) makes ``~/.claude/CLAUDE.md`` the top authority over
    project-level configuration. v0.3.0 Feature E surfaces this for the
    per-skill model selection: when the developer's global file pins a
    model (``Use claude-opus-4-7 for all sessions``, ``Pin claude-sonnet-4-6``,
    etc.) the plugin MUST ignore any plugin.local.md / CLI override and let
    the session's default model take effect.

    Returns the *effective* model to pass to ``--model``, which is None
    when INV-0 fires (CLAUDE.md pinned a global model) and otherwise
    equals ``configured_model``. Emits a stderr breadcrumb on the rare
    INV-0 path so operators see the cost implication.

    Args:
        configured_model: Model ID resolved by the upstream cascade
            (CLI override > plugin.local.md > None). When ``None`` no
            scan is performed (cheap short-circuit).
        skill_field_name: Name of the plugin.local.md field whose value
            became ``configured_model`` (for the breadcrumb message).

    Returns:
        ``None`` when INV-0 fires (plugin must omit ``--model`` and
        inherit the session default); ``configured_model`` otherwise.
    """
    if configured_model is None:
        return None
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if not claude_md.exists():
        return configured_model
    try:
        text = claude_md.read_text(encoding="utf-8")
    except OSError:
        return configured_model
    match = INV_0_PINNED_MODEL_RE.search(text)
    if match is None:
        return configured_model
    pinned = match.group(1)
    _sys.stderr.write(
        f"[sbtdd inv-0] CLAUDE.md pins {pinned} globally; ignoring "
        f"plugin.local.md {skill_field_name}={configured_model} to "
        f"respect global authority. Cost implication may differ from "
        f"configured baseline.\n"
    )
    _sys.stderr.flush()
    return None


#: v1.0.4 Item B (Task 4): per-skill recovery message body. Each entry
#: is appended after the leading sentence in :func:`_build_recovery_message`
#: so operators see a tailored recovery path matching the skill's role.
#: Frozen via :class:`types.MappingProxyType` to prevent accidental
#: runtime mutation (style consistent with ``_SUBPROCESS_INCOMPATIBLE_SKILLS``).
#:
#: - ``brainstorming`` and ``writing-plans``: spec-phase skills; the
#:   recovery is to run the skill manually in an interactive Claude Code
#:   session, then resume via ``/sbtdd spec --resume-from-magi`` (v1.0.1
#:   Item A3).
#: - ``receiving-code-review``: pre-merge-phase skill; the recovery is
#:   either run the skill manually OR fall back to direct
#:   ``run_magi.py code-review`` per spec sec.6.4.
_PER_SKILL_RECOVERY: Mapping[str, str] = MappingProxyType(
    {
        "brainstorming": (
            "  1. Run `/brainstorming` manually in interactive Claude Code session,\n"
            "     then use `/sbtdd spec --resume-from-magi`."
        ),
        "writing-plans": (
            "  1. Run `/writing-plans` manually in interactive Claude Code session,\n"
            "     then use `/sbtdd spec --resume-from-magi`."
        ),
        "receiving-code-review": (
            "  1. Run `/receiving-code-review` manually in interactive session, OR\n"
            "  2. Fall back to manual `python skills/magi/scripts/run_magi.py code-review <payload>`\n"
            "     per spec sec.6.4 + apply mini-cycle TDD fixes manually."
        ),
    }
)


#: Generic recovery body used when a skill name is not present in
#: :data:`_PER_SKILL_RECOVERY`. Tailored entries are preferred, but a
#: catch-all keeps :func:`_build_recovery_message` total over the
#: input space.
_GENERIC_RECOVERY = (
    "  1. Run the skill manually in interactive session,\n     then resume the SBTDD workflow."
)


def _build_recovery_message(skill: str) -> str:
    """Construct the operator-facing recovery message for a blocked skill.

    v1.0.4 Item B (Task 4): replaces the Task 3 placeholder with a per-skill
    recovery body so the operator sees actionable guidance tailored to the
    skill that was blocked. Post iter 1 triage simplified: NO env-var
    formatting (the gate is membership-based, not heuristic-based -- there
    is no env state to report).

    The leading sentence is preserved verbatim from the Task 3 placeholder
    so callsite tests that match the prefix keep passing monotonically.

    Args:
        skill: Slash-command name (e.g., ``"receiving-code-review"``).

    Returns:
        Multi-line operator-facing message including:
        - Reason (skill empirically incompatible).
        - Per-skill recovery options (or generic fallback when the skill
          is not present in :data:`_PER_SKILL_RECOVERY`).
        - Override hint (``allow_interactive_skill=True`` for known-safe
          callers that have arranged for subprocess success).
    """
    per_skill = _PER_SKILL_RECOVERY.get(skill, _GENERIC_RECOVERY)
    return (
        f"Skill `/{skill}` cannot run via `claude -p` subprocess "
        f"(empirically incompatible: requires multi-turn interactive "
        f"dialogue or hangs > 600s). Recovery options:\n"
        f"{per_skill}\n"
        f"To override (only when caller has arranged interactive "
        f"completion path), pass `allow_interactive_skill=True` to "
        f"`invoke_skill(...)`."
    )


def invoke_skill(
    skill: str,
    args: list[str] | None = None,
    timeout: int = 600,
    cwd: str | None = None,
    *,
    model: str | None = None,
    skill_field_name: str = "implementer_model",
    stream_prefix: str | None = None,
    allow_interactive_skill: bool = False,
) -> SkillResult:
    """Invoke a superpowers skill via ``claude -p`` subprocess.

    v1.0.8 Pillar A1: test-only stub gate. When env var
    :data:`_E2E_STUB_ENV` (``SBTDD_E2E_STUB_DISPATCH``) is set to
    ``"1"`` AND ``"pytest"`` is in :data:`sys.modules` AND
    ``skill`` is in :data:`_E2E_STUBBABLE_SKILLS`
    (``test-driven-development`` or ``systematic-debugging``), this
    function short-circuits to a synthetic ``SkillResult(rc=0)``
    without spawning ``claude -p``. The gate is checked FIRST so it
    short-circuits ALL downstream dispatch logic.

    Gate precedence (iter-2 carry-forward Mel-I2): the v1.0.8 A1
    stub gate is positioned BEFORE the v1.0.7 A2 worker-context
    guard, the v1.0.6 J-3 headless guard, and the v1.0.4
    membership gate. When both ``SBTDD_E2E_STUB_DISPATCH=1`` AND
    ``SBTDD_AUTO_PARALLEL_WORKER=1`` are set (test scenario where
    the parent test sets the stub env var, which propagates to
    worker via ``os.environ.copy()`` per A2), the stub gate wins
    -- correct for the test path.

    Defense-in-depth via pytest sys.modules guard (iter-2
    carry-forward Cas-W11): the gate requires both the env var
    AND ``"pytest" in sys.modules``. Production processes
    (auto_cmd orchestrator, worker subprocesses) do NOT import
    pytest at runtime, so accidental env var leak into production
    has ZERO effect -- gate cannot fire. Test runners load pytest
    into sys.modules at process start. This converts the gate
    from "test-by-convention" to "test-by-runtime-check".

    Test-only -- production callers MUST NOT set the env var
    (gate is namespaced via ``SBTDD_E2E_*`` prefix; production
    workers continue to dispatch real LLM via ``claude -p``).

    Args:
        skill: Skill name without leading slash (``brainstorming``,
            ``writing-plans``, ...).
        args: Extra tokens appended after the skill invocation.
        timeout: Wall-clock seconds before SIGTERM (sec.S.8.6 -- explicit
            timeout mandatory).
        cwd: Working directory; ``None`` uses current.
        model: Optional Claude model ID for the v0.3.0 Feature E
            per-skill model selection. ``None`` (default) preserves the
            v0.2.x argv shape exactly. When set, the INV-0 cascade fires
            against ``~/.claude/CLAUDE.md`` first; if the global file
            pins a different model the kwarg is suppressed and a stderr
            breadcrumb is emitted.
        skill_field_name: Name of the plugin.local.md field whose value
            became ``model`` -- surfaces in the INV-0 breadcrumb. Defaults
            to ``"implementer_model"`` so callers that pass ``model=``
            without explicitly tagging it still get a sensible message.
        stream_prefix: When set, forwards to
            :func:`subprocess_utils.run_with_timeout` so the underlying
            ``claude -p`` subprocess emits stdout/stderr line-by-line to
            the orchestrator's stderr during execution (Feature D
            streaming integration -- iter 2 finding #1 + #7 fix). When
            ``None`` (default) the v0.2.x ``capture_output=True``
            behavior is preserved.
        allow_interactive_skill: v1.0.1 Item A2 (sec.2.3) opt-in
            override. ``False`` (default) is safe-by-default for headless
            CLI / external callers: when v1.0.1 Item A2 lands, skills in
            ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` raise ``PreconditionError``
            before subprocess spawn. ``True`` is the wrapper-aware path:
            high-level wrappers (``brainstorming``, ``writing_plans``,
            ``_invoke_skill``) pass ``True`` because they ARE the
            coordinated dispatch path. Pre-A2 lands the kwarg as no-op;
            A2 Step 4 adds the gate logic that consumes it.

    Returns:
        :class:`SkillResult` with returncode, stdout, stderr.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        ValidationError: If the subprocess timed out OR exited non-zero without
            matching a quota pattern. Mapped to exit 1 by run_sbtdd.py.
    """
    # v1.0.8 Pillar A1: test-only stub gate. Checked FIRST so it
    # short-circuits ALL downstream dispatch logic (v1.0.4 membership
    # gate + v1.0.6 J-3 headless guard + v1.0.7 A2 worker-context
    # guard). Test-only: production MUST NOT set
    # SBTDD_E2E_STUB_DISPATCH nor SBTDD_E2E_TEST_RUNNER.
    #
    # T4 follow-up fix: original v1.0.8 design used
    # ``"pytest" in sys.modules`` as runtime production safeguard
    # (Caspar W11 option a). That worked for in-process test
    # invocations but BROKE the legitimate e2e use case where
    # ``tests/test_auto_parallel_e2e.py`` spawns
    # ``python run_sbtdd.py auto --parallel`` as subprocess: the
    # subprocess inherits env vars via os.environ.copy() but does
    # NOT import pytest (auto_cmd has no pytest dep). Switched to
    # Caspar W11 option b: AND-gate with a second env var
    # SBTDD_E2E_TEST_RUNNER. Both vars must be set; production
    # accidental leak of one (or both) without the other has zero
    # effect. Test parent sets both before subprocess.run + both
    # propagate to subprocess via os.environ.copy().
    if (
        os.environ.get(_E2E_STUB_ENV) == "1"
        and os.environ.get(_E2E_TEST_RUNNER_ENV) == "1"
        and skill in _E2E_STUBBABLE_SKILLS
    ):
        # v1.0.8 T4: requesting-code-review consumer (pre_merge_cmd
        # ._is_clean_to_go) requires the literal "clean-to-go" token in
        # stdout to exit Loop 1. Other stubbed skills accept any stdout.
        stub_stdout = f"[sbtdd e2e stub] /{skill} bypassed ({_E2E_STUB_ENV}=1)"
        if skill == "requesting-code-review":
            stub_stdout += " clean-to-go"
        return SkillResult(
            skill=skill,
            returncode=0,
            stdout=stub_stdout,
            stderr="",
        )
    # v1.0.1 Item A2 (sec.2.3) + v1.0.4 Item A.2 (Task 3): safe-by-default
    # gate -- skills in ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` (e.g.
    # ``/brainstorming``, ``/writing-plans``, ``/receiving-code-review``)
    # raise BEFORE subprocess spawn unless the caller opts into the
    # override. Wrappers built via ``_make_wrapper`` and the H5-1
    # ``_invoke_skill`` helper pass ``True`` automatically (per Pre-A2
    # migration); external callers must opt in explicitly.
    #
    # v1.0.4 (Task 3 + Task 4): the operator-facing recovery message is
    # built by :func:`_build_recovery_message` so per-skill recovery
    # paths can be tailored (Task 4 expansion). NO env-var/isatty
    # heuristic -- caspar Checkpoint 2 iter 1 CRITICAL verified that
    # heuristic does not fix the v1.0.3 bug because operator main
    # sessions have TTY=True so the gate would not fire.
    # v1.0.7 A2 Q2'=b promotion: defense-in-depth worker-context runtime
    # guard. Workers under `auto --parallel` (parent-injected env var
    # SBTDD_AUTO_PARALLEL_WORKER=1) MUST NOT dispatch interactive skills
    # via subprocess. The membership gate below + v1.0.6 J-3 headless
    # detection catch the orchestrator path; this guard catches the
    # worker path even when a wrapper sets allow_interactive_skill=True.
    # Closes Cas v1.0.6 iter-2 WARNING: F-A2 worker headless audit was
    # grep-snapshot, not runtime guard. Fires loud-fast so any drift
    # (transitive imports adding a skill dispatch to the worker code
    # path) surfaces during dev/CI rather than producing a silent
    # subprocess hang in production.
    if (
        skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
        and os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1"
    ):
        raise PreconditionError(
            f"Worker subprocess attempted to dispatch interactive "
            f"skill {skill!r}; this should never happen in the auto "
            f"--parallel worker code path. Bug. Either: (a) the worker "
            f"code path was extended to call the skill -- refactor to "
            f"use shell command directly per v1.0.7 A2 "
            f"_run_verification pattern, OR (b) the parent set "
            f"SBTDD_AUTO_PARALLEL_WORKER=1 incorrectly."
        )
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
        raise PreconditionError(_build_recovery_message(skill))
    effective_model = _apply_inv0_model_check(model, skill_field_name)
    cmd = _build_skill_cmd(skill, args, model=effective_model)
    # iter 2 finding #1 + #7: only pass stream_prefix when supplied so
    # test fakes for run_with_timeout that don't accept the new kwarg
    # keep working byte-identically (the v0.2 baseline behavior).
    rwt_kwargs: dict[str, Any] = {"timeout": timeout, "capture": True, "cwd": cwd}
    if stream_prefix is not None:
        rwt_kwargs["stream_prefix"] = stream_prefix
    try:
        result = subprocess_utils.run_with_timeout(cmd, **rwt_kwargs)
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(f"skill '/{skill}' timed out after {exc.timeout}s") from exc

    if result.returncode != 0:
        exhaustion = quota_detector.detect(result.stderr)
        if exhaustion is not None:
            msg = f"{exhaustion.kind}: {exhaustion.raw_message}"
            if exhaustion.reset_time:
                msg += f" (reset: {exhaustion.reset_time})"
            raise QuotaExhaustedError(msg)
        raise ValidationError(
            f"skill '/{skill}' failed (returncode={result.returncode}): {result.stderr.strip()}"
        )
    return SkillResult(
        skill=skill,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


# NOTE: wrappers must call invoke_skill via module attribute (not closure capture)
# so tests can monkeypatch "superpowers_dispatch.invoke_skill" at runtime.
# Fix for MAGI Checkpoint 2 iter 1 CRITICAL 1 (melchior): closure binding
# made monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake) a no-op.
# The wrapper resolves ``invoke_skill`` by reaching into the module's own
# namespace at call time (``sys.modules[__name__].invoke_skill``), which IS
# what ``monkeypatch.setattr`` replaces.


# Per-skill default timeouts (seconds). The global default is 600s; skills
# whose subprocess reliably needs more time override it below.
#
# - ``/writing-plans`` is raised to 1800s because empirically (v0.2
#   Checkpoint 2 first run, 2026-04-23) the subprocess exceeded 600s even
#   when the plan file was already written to disk -- the sub-session
#   spends non-trivial post-write time on closing actions, and killing it
#   at 600s aborts the whole ``/sbtdd spec`` pipeline before MAGI
#   Checkpoint 2 can run.
# - ``/test-driven-development`` is raised to 1800s because real
#   implementer work on substantial tasks (observed G2 of Feature A:
#   root-cause classifier + build_escalation_context on 2026-04-24)
#   exceeds 600s when the sub-session reads the plan, writes tests,
#   implements the production code, and runs ``make verify`` in one pass.
#   The 600s default was tuned for the small Milestone A tasks where
#   each phase is a few functions; v0.2's larger tasks need more budget.
_DEFAULT_TIMEOUT = 600
_SKILL_TIMEOUT_OVERRIDES: dict[str, int] = {
    "writing-plans": 1800,
    "test-driven-development": 1800,
    # ``/requesting-code-review`` raised to 1800s empirically (v0.2
    # pre-merge Loop 1 2026-04-24): reviewing the full accumulated v0.2
    # diff (27 tasks worth of new/modified code across 6 modules +
    # ~1500 lines of new tests) exceeded 600s. Same pattern as the
    # other two skills -- large v0.2-scale inputs need more budget.
    "requesting-code-review": 1800,
}


def _make_wrapper(
    skill_name: str,
) -> Callable[..., SkillResult]:
    """Return a typed wrapper function bound to ``skill_name``.

    Resolves ``invoke_skill`` at call time via the module's own attribute
    table so ``monkeypatch.setattr('superpowers_dispatch.invoke_skill', ...)``
    takes effect in tests.

    The wrapper's default timeout comes from ``_SKILL_TIMEOUT_OVERRIDES[skill_name]``
    when defined, else ``_DEFAULT_TIMEOUT``. Callers can still pass an
    explicit ``timeout=`` kwarg to override per call.
    """
    default_timeout = _SKILL_TIMEOUT_OVERRIDES.get(skill_name, _DEFAULT_TIMEOUT)

    def _wrapper(
        args: list[str] | None = None,
        timeout: int = default_timeout,
        cwd: str | None = None,
        *,
        model: str | None = None,
        skill_field_name: str = "implementer_model",
        stream_prefix: str | None = None,
    ) -> SkillResult:
        module = _sys.modules[__name__]
        fn = module.invoke_skill  # late-bound: tests can replace via monkeypatch
        # v0.3.0 Feature E: pass model + skill_field_name when the caller
        # supplied a non-None model so INV-0 + --model arg injection fires
        # downstream. With model=None the wrapper preserves the v0.2.x
        # call signature (no kwargs added) so monkeypatched stubs that
        # only accept (args, timeout, cwd) keep working in tests.
        #
        # iter 2 finding #1 + #7: stream_prefix is opt-in; the wrapper
        # forwards it only when the caller supplied a non-None value so
        # pre-existing monkeypatched stubs continue to accept the call
        # signature byte-identically.
        kwargs: dict[str, Any] = {"args": args, "timeout": timeout, "cwd": cwd}
        if model is not None:
            kwargs["model"] = model
            kwargs["skill_field_name"] = skill_field_name
        if stream_prefix is not None:
            kwargs["stream_prefix"] = stream_prefix
        # v1.0.1 Pre-A2: wrappers ARE the safe coordinated dispatch path
        # for any skill (including those in _SUBPROCESS_INCOMPATIBLE_SKILLS),
        # so the wrapper opts into the override automatically. A2 Step 4
        # adds the gate logic that consumes this kwarg; here Pre-A2
        # ensures the wrapper continues to work once the gate is wired.
        #
        # Forwarding pattern matches v0.3.0 ``model`` + v0.5.0
        # ``stream_prefix``: only inject the kwarg when the late-bound
        # ``fn`` accepts it. Pre-existing test fakes that monkeypatch
        # ``invoke_skill`` with the v0.2/v0.3/v0.5 signatures (no
        # ``allow_interactive_skill`` parameter) keep working
        # byte-identically. Production ``invoke_skill`` (which DID gain
        # the kwarg in Pre-A2) gets the override; stubs without it do
        # not.
        try:
            import inspect

            sig = inspect.signature(fn)
            if "allow_interactive_skill" in sig.parameters or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                kwargs["allow_interactive_skill"] = True
        except (TypeError, ValueError):
            # Builtin / C-extension callables may not be inspectable;
            # skip the override gracefully (same defensive pattern as
            # other v0.5.0 introspection paths).
            pass
        result: SkillResult = fn(skill_name, **kwargs)
        return result

    _wrapper.__name__ = skill_name.replace("-", "_")
    _wrapper.__doc__ = f"Invoke the /{skill_name} superpowers skill."
    return _wrapper


brainstorming = _make_wrapper("brainstorming")
writing_plans = _make_wrapper("writing-plans")
test_driven_development = _make_wrapper("test-driven-development")
verification_before_completion = _make_wrapper("verification-before-completion")
requesting_code_review = _make_wrapper("requesting-code-review")
receiving_code_review = _make_wrapper("receiving-code-review")
executing_plans = _make_wrapper("executing-plans")
subagent_driven_development = _make_wrapper("subagent-driven-development")
dispatching_parallel_agents = _make_wrapper("dispatching-parallel-agents")
systematic_debugging = _make_wrapper("systematic-debugging")
using_git_worktrees = _make_wrapper("using-git-worktrees")
finishing_a_development_branch = _make_wrapper("finishing-a-development-branch")


# ---------------------------------------------------------------------------
# v1.0.0 Feature H option 5 -- /writing-plans prompt extension (sec.3.3 H5-1).
#
# Per spec sec.3.3 the SBTDD pipeline invokes ``/writing-plans`` with an
# extended prompt directing the sub-session to auto-generate scenario stub
# tests for every Escenario in ``sbtdd/spec-behavior.md`` sec.4. Stub bodies
# use ``pytest.skip("Scenario stub: replace with real assertions")`` so a
# missing implementation never silently passes -- per H5-2 (deferred to
# v1.0.1+) Checkpoint 2 will reject plans missing any stub.
#
# v1.0.0 ships H5-1 (auto-generation in the prompt) only; the H5-2 enforcing
# spec_lint at Checkpoint 2 is deferred per CHANGELOG `[1.0.0]` Deferred to
# collect empirical data on stub-gen quality first.
# ---------------------------------------------------------------------------

_WRITING_PLANS_STUB_DIRECTIVE = """

## Auto-generated scenario stubs (Feature H option 5)

For each scenario in the spec's §4 Escenarios BDD section, generate a
stub test in the plan's task list with:

- Function name: ``test_scenario_<N>_<slug>()`` where ``N`` is the scenario
  number (or letter-prefixed identifier like ``S1``) and ``slug`` is a
  snake_case version of the title.
- Body: ``pytest.skip("Scenario stub: replace with real assertions")``.
- Docstring: reference the scenario number + title verbatim.

Plan authors replace stub bodies with real assertions before MAGI
Checkpoint 2. Missing any stub at Checkpoint 2 will be flagged as a
plan-quality failure (v1.0.1+ ``spec_lint``); for v1.0.0 the convention
is enforced by reviewer eye + manual ``/sbtdd close-task`` discipline.
"""


def _invoke_skill(*, prompt: str, skill: str, **kwargs: Any) -> Any:
    """Invoke a skill with a free-form prompt (used by Feature H option 5).

    The standard :func:`invoke_skill` formats the prompt as
    ``"/<skill> <args joined>"``; H5-1 needs to inject a multi-paragraph
    directive into the prompt instead, so this helper packs ``prompt``
    as the single args entry and delegates to :func:`invoke_skill` with
    ``skill`` for argv-shape compatibility. Tests monkeypatch this
    function to capture the prompt without invoking ``claude -p``.

    Args:
        prompt: Full free-form prompt body (without leading slash; the
            slash command is added by :func:`_build_skill_cmd`).
        skill: Skill name without leading slash (e.g. ``writing-plans``).
        **kwargs: Forwarded to :func:`invoke_skill` (``timeout``, ``cwd``,
            ``model``, ``stream_prefix``, ...).

    Returns:
        :class:`SkillResult` from the underlying :func:`invoke_skill`.
    """
    module = _sys.modules[__name__]
    fn = module.invoke_skill  # late-bound so tests can replace via monkeypatch.
    # v1.0.1 Pre-A2: same rationale as _make_wrapper -- _invoke_skill is the
    # H5-1 prompt-extension path and ARE the coordinated dispatch entry.
    # Inject ``allow_interactive_skill=True`` only when ``fn`` accepts it;
    # this preserves byte-identical behavior for pre-existing test fakes
    # that monkeypatch ``invoke_skill`` with the v0.5/v1.0 signature.
    if "allow_interactive_skill" not in kwargs:
        try:
            import inspect

            sig = inspect.signature(fn)
            if "allow_interactive_skill" in sig.parameters or any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            ):
                kwargs["allow_interactive_skill"] = True
        except (TypeError, ValueError):
            pass
    return fn(skill, args=[prompt], **kwargs)


def invoke_writing_plans(*, spec_path: str, **kwargs: Any) -> Any:
    """Invoke ``/writing-plans`` with the H5-1 scenario-stub directive injected.

    Per spec sec.3.3 H5-1: the extended prompt directs the sub-session to
    auto-generate one scenario stub test per spec §4 Escenario. Stub
    bodies use ``pytest.skip("Scenario stub: replace with real
    assertions")`` so a missing implementation never silently passes.

    Args:
        spec_path: Path to ``sbtdd/spec-behavior.md`` for the
            sub-session to read scenarios from.
        **kwargs: Forwarded to :func:`_invoke_skill`.

    Returns:
        Result of the underlying :func:`_invoke_skill` call.
    """
    base_prompt = f"Generate TDD plan from {spec_path}"
    extended_prompt = base_prompt + _WRITING_PLANS_STUB_DIRECTIVE
    return _invoke_skill(prompt=extended_prompt, skill="writing-plans", **kwargs)
