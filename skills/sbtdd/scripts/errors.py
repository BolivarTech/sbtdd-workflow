#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Exception hierarchy for sbtdd-workflow plugin.

All plugin exceptions derive from :class:`SBTDDError` so dispatchers can
catch the whole hierarchy with a single except clause (sec.S.8.4). Each
subclass maps to a specific exit code per sec.S.11.1 taxonomy; the
canonical mapping is exposed programmatically as :data:`EXIT_CODES`
(MAGI Loop 2 Finding 7 -- codifies what was previously only documented
in CLAUDE.md + spec).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


class SBTDDError(Exception):
    """Base exception for all plugin errors. Subclasses map to exit codes."""


class ValidationError(SBTDDError):
    """Schema or input validation failed (exit 1, USER_ERROR)."""


class StateFileError(SBTDDError):
    """session-state.json corrupt (JSON invalid / schema invalid) — exit 1."""


class DriftError(SBTDDError):
    """State vs git HEAD vs plan mismatch detected by drift.detect_drift — exit 3."""


class DependencyError(SBTDDError):
    """Required dependency missing or non-operational — exit 2."""


class PreconditionError(SBTDDError):
    """Subcommand precondition not satisfied — exit 2 (PRECONDITION_FAILED)."""


class MAGIGateError(SBTDDError):
    """MAGI verdict below threshold or STRONG_NO_GO -- exit 8 (MAGI_GATE_BLOCKED).

    Carries the gate decision context as typed attributes so downstream
    audit-trail writers (``auto_cmd.main``) can enrich ``.claude/auto-run.json``
    without parsing the free-form message string. All new attributes are
    keyword-only with safe defaults; existing raisers that pass only a
    positional ``message`` continue to work unchanged (Plan D, scope
    addition -- Finding 1).

    Attributes:
        accepted_conditions: MAGI conditions that ``/receiving-code-review``
            accepted, awaiting user-materialised fixes via ``close-phase``.
        rejected_conditions: MAGI conditions rejected with rationale,
            fed back as context in the next MAGI iteration.
        verdict: The MAGI verdict string at gate-block time (``GO`` /
            ``GO_WITH_CAVEATS`` / ``STRONG_NO_GO`` / ``HOLD`` / ``HOLD_TIE``).
        iteration: The MAGI iteration number at which the gate blocked
            (1-indexed).
    """

    def __init__(
        self,
        message: str,
        *,
        accepted_conditions: tuple[str, ...] = (),
        rejected_conditions: tuple[str, ...] = (),
        verdict: str | None = None,
        iteration: int | None = None,
    ) -> None:
        super().__init__(message)
        self.accepted_conditions = accepted_conditions
        self.rejected_conditions = rejected_conditions
        self.verdict = verdict
        self.iteration = iteration


class QuotaExhaustedError(SBTDDError):
    """Anthropic API quota exhausted (rate limit / session / credit) — exit 11."""


class CommitError(SBTDDError):
    """Git commit subprocess failure (non-zero exit, timeout) — exit 1."""


class Loop1DivergentError(SBTDDError):
    """Loop 1 (/requesting-code-review) did not converge in 10 iterations (exit 7)."""


class ChecklistError(SBTDDError):
    """Finalize checklist item failed (exit 9, CHECKLIST_FAILED)."""


class VerificationIrremediableError(SBTDDError):
    """Phase verification failed after auto retry budget (exit 6)."""


class SpecReviewError(SBTDDError):
    """Spec-reviewer safety valve exhausted — exit 12 (SPEC_REVIEW_ISSUES).

    Introduced in v0.2 (Feature B). Carries the last-iteration issues
    list as a typed attribute so dispatchers can enrich audit artifacts.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        iteration: int | None = None,
        issues: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.iteration = iteration
        self.issues = issues


_EXIT_CODES_MUTABLE: dict[type[SBTDDError], int] = {
    ValidationError: 1,
    StateFileError: 1,
    CommitError: 1,
    DependencyError: 2,
    PreconditionError: 2,
    DriftError: 3,
    VerificationIrremediableError: 6,
    Loop1DivergentError: 7,
    MAGIGateError: 8,
    ChecklistError: 9,
    QuotaExhaustedError: 11,
    SpecReviewError: 12,
}

#: Read-only exception-class -> exit-code registry (sec.S.11.1 canonical
#: taxonomy). Dispatchers at ``run_sbtdd.py`` read this mapping when
#: converting uncaught ``SBTDDError`` subclasses to process exit codes.
#: Keep aligned with the taxonomy in CLAUDE.md "Key Design Decisions".
EXIT_CODES: Mapping[type[SBTDDError], int] = MappingProxyType(_EXIT_CODES_MUTABLE)
