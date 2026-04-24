# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Spec-reviewer dispatch dataclasses for the sbtdd-workflow plugin.

Green phase of task H2 (v0.2 Feature B — superpowers spec-reviewer
integration per task). This module currently exposes only the immutable
result types consumed by higher layers; the actual dispatch logic
(``dispatch_spec_reviewer``, artifact writing, reviewer-output parsing)
lands in later tasks (H3+) per the approved plan.

The two dataclasses mirror the contract declared in
``sbtdd/spec-behavior.md`` §2.2 / §4 F20 and in ``CLAUDE.md`` under
"v0.2 requirement (LOCKED) — superpowers spec-reviewer integration per
task":

* :class:`SpecIssue` — one finding raised by the reviewer, classified by
  severity against the three defect classes documented in the superpowers
  ``spec-reviewer-prompt.md`` template (missing requirements, extra/unneeded
  work, misunderstandings).
* :class:`SpecReviewResult` — aggregate outcome returned by
  ``dispatch_spec_reviewer`` (to be implemented in H3+): approval flag,
  tuple of issues, iteration count, and path to the audit artifact written
  under ``.claude/spec-reviews/``.

Both dataclasses are ``frozen=True`` so they honour the immutability rule
from ``CLAUDE.local.md`` §0.2 "Inmutabilidad".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple

_SeverityLit = Literal["MISSING", "EXTRA", "MISUNDERSTANDING"]


@dataclass(frozen=True)
class SpecIssue:
    """One finding raised by the spec-reviewer for a single task.

    Attributes:
        severity: Defect class as classified by the reviewer. One of
            ``"MISSING"`` (requirement not implemented),
            ``"EXTRA"`` (over-engineering outside spec scope),
            ``"MISUNDERSTANDING"`` (solved wrong problem / wrong way).
        text: Human-readable description of the finding emitted by the
            reviewer subagent.
    """

    severity: _SeverityLit
    text: str


@dataclass(frozen=True)
class SpecReviewResult:
    """Aggregate outcome of a spec-reviewer dispatch for one task.

    Attributes:
        approved: ``True`` when the reviewer raised no issues for the
            task's diff; ``False`` when at least one issue requires
            remediation before ``close_task_cmd.mark_and_advance`` may
            advance state.
        issues: Immutable tuple of :class:`SpecIssue` entries. Empty when
            ``approved`` is ``True``.
        reviewer_iter: Count of reviewer iterations consumed for this
            task, bounded by the safety valve (default 3 per task).
        artifact_path: Filesystem path to the audit artifact written
            under ``.claude/spec-reviews/`` for this dispatch. ``None``
            when no artifact was produced (e.g. construction in tests).
    """

    approved: bool
    issues: Tuple[SpecIssue, ...]
    reviewer_iter: int
    artifact_path: Optional[Path]
