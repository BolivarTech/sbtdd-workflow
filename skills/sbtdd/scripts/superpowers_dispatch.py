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
from typing import Callable

import quota_detector
import subprocess_utils
from errors import QuotaExhaustedError, ValidationError


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


def _build_skill_cmd(skill: str, args: list[str] | None) -> list[str]:
    """Build the argv list for ``claude -p`` invoking ``skill``.

    Centralised so ``invoke_skill`` and future callers (e.g. a direct
    pipeline driver) stay in sync.
    """
    cmd = ["claude", "-p", f"/{skill}"]
    if args:
        cmd.extend(args)
    return cmd


def invoke_skill(
    skill: str,
    args: list[str] | None = None,
    timeout: int = 600,
    cwd: str | None = None,
) -> SkillResult:
    """Invoke a superpowers skill via ``claude -p`` subprocess.

    Args:
        skill: Skill name without leading slash (``brainstorming``,
            ``writing-plans``, ...).
        args: Extra tokens appended after the skill invocation.
        timeout: Wall-clock seconds before SIGTERM (sec.S.8.6 -- explicit
            timeout mandatory).
        cwd: Working directory; ``None`` uses current.

    Returns:
        :class:`SkillResult` with returncode, stdout, stderr.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        ValidationError: If the subprocess timed out OR exited non-zero without
            matching a quota pattern. Mapped to exit 1 by run_sbtdd.py.
    """
    cmd = _build_skill_cmd(skill, args)
    try:
        result = subprocess_utils.run_with_timeout(cmd, timeout=timeout, capture=True, cwd=cwd)
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


def _make_wrapper(
    skill_name: str,
) -> Callable[..., SkillResult]:
    """Return a typed wrapper function bound to ``skill_name``.

    Resolves ``invoke_skill`` at call time via the module's own attribute
    table so ``monkeypatch.setattr('superpowers_dispatch.invoke_skill', ...)``
    takes effect in tests.
    """

    def _wrapper(
        args: list[str] | None = None,
        timeout: int = 600,
        cwd: str | None = None,
    ) -> SkillResult:
        module = _sys.modules[__name__]
        fn = module.invoke_skill  # late-bound: tests can replace via monkeypatch
        result: SkillResult = fn(skill_name, args=args, timeout=timeout, cwd=cwd)
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
