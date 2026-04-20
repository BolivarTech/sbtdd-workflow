#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Canonical stubs for integration tests consuming superpowers and MAGI dispatchers.

Behavior contract (assertion points for Tasks 47-50):

StubSuperpowers:
  - Records every skill invocation as (name, args, cwd) in ``self.calls``.
  - Returns a zero-exit SkillResult by default; raise via ``self.fail_on = {"name"}``.
  - Writes synthetic output files when configured via
    ``self.create_files = {"name": [Path(...), ...]}`` -- emulates skills that
    produce tracked artifacts (brainstorming, writing_plans).

StubMAGI:
  - ``sequence: list[MAGIVerdict]`` is consumed FIFO per invocation.
  - Each call records ``context_paths`` (full list per invocation) so tests
    can verify iter-2 W6 rejection-feedback threading: Loop 2 appends
    ``.claude/magi-feedback.md`` to ``context_paths`` on iter N+1 when
    iter N produced rejected conditions. Tests assert that path is
    present in the second call's ``context_paths`` but absent in the first.
  - Raises IndexError on exhaustion so runaway loops fail loud, not silent.

make_verdict(verdict, conditions=(), findings=(), degraded=False) -> MAGIVerdict:
  - Convenience constructor so tests read declaratively.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magi_dispatch import MAGIVerdict
from superpowers_dispatch import SkillResult


def make_verdict(
    verdict: str,
    conditions: tuple[str, ...] = (),
    findings: tuple[dict[str, Any], ...] = (),
    degraded: bool = False,
) -> MAGIVerdict:
    """Build an ``MAGIVerdict`` with sensible defaults for tests."""
    return MAGIVerdict(
        verdict=verdict,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output="",
    )


@dataclass
class StubSuperpowers:
    """Stub for the 12 wrapper functions exported by ``superpowers_dispatch``."""

    calls: list[tuple[str, list[str], str]] = field(default_factory=list)
    fail_on: set[str] = field(default_factory=set)
    create_files: dict[str, list[Path]] = field(default_factory=dict)

    def _record(self, name: str, args: list[str], cwd: str) -> SkillResult:
        self.calls.append((name, list(args), cwd))
        if name in self.fail_on:
            raise RuntimeError(f"stub forced failure for {name}")
        for p in self.create_files.get(name, ()):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
        return SkillResult(name, 0, "", "")

    def brainstorming(self, *, args: list[str] | None = None, cwd: str = "") -> SkillResult:
        return self._record("brainstorming", args or [], cwd)

    def writing_plans(self, *, args: list[str] | None = None, cwd: str = "") -> SkillResult:
        return self._record("writing_plans", args or [], cwd)

    def verification_before_completion(self, *, cwd: str = "") -> SkillResult:
        return self._record("verification_before_completion", [], cwd)

    def requesting_code_review(self, *, cwd: str = "") -> SkillResult:
        return self._record("requesting_code_review", [], cwd)

    def receiving_code_review(self, *, cwd: str = "", findings: list[str] | None = None) -> Any:
        self._record("receiving_code_review", list(findings or []), cwd)

        class _Review:
            accepted = tuple(findings or ())
            rejected: tuple[str, ...] = ()

        return _Review()

    def test_driven_development(
        self, *, args: list[str] | None = None, cwd: str = ""
    ) -> SkillResult:
        return self._record("test_driven_development", args or [], cwd)

    def systematic_debugging(self, *, cwd: str = "") -> SkillResult:
        return self._record("systematic_debugging", [], cwd)

    def finishing_a_development_branch(self, *, cwd: str = "") -> SkillResult:
        return self._record("finishing_a_development_branch", [], cwd)


@dataclass
class StubMAGI:
    """Stub for ``magi_dispatch.invoke_magi`` with a scripted verdict queue."""

    sequence: list[MAGIVerdict]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def invoke_magi(
        self,
        *,
        context_paths: list[str],
        cwd: str,
        timeout: int = 1800,
    ) -> MAGIVerdict:
        # Signature mirrors magi_dispatch.invoke_magi EXACTLY
        # (no extra_context -- Milestone B's frozen signature takes
        # context_paths, timeout, cwd only; rejection feedback flows
        # via an auxiliary .claude/magi-feedback.md path appended to
        # context_paths by _loop2 -- see iter-2 Finding W6).
        self.calls.append(
            {
                "context_paths": list(context_paths),
                "cwd": cwd,
                "timeout": timeout,
            }
        )
        return self.sequence.pop(0)
