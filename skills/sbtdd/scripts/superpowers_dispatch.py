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
"""

from __future__ import annotations

import subprocess
import sys as _sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import quota_detector
import subprocess_utils
from errors import QuotaExhaustedError, ValidationError
from models import INV_0_PINNED_MODEL_RE


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


def invoke_skill(
    skill: str,
    args: list[str] | None = None,
    timeout: int = 600,
    cwd: str | None = None,
    *,
    model: str | None = None,
    skill_field_name: str = "implementer_model",
    stream_prefix: str | None = None,
) -> SkillResult:
    """Invoke a superpowers skill via ``claude -p`` subprocess.

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

    Returns:
        :class:`SkillResult` with returncode, stdout, stderr.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        ValidationError: If the subprocess timed out OR exited non-zero without
            matching a quota pattern. Mapped to exit 1 by run_sbtdd.py.
    """
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
