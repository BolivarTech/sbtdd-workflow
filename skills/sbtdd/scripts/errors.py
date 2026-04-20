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
    """MAGI verdict below threshold or STRONG_NO_GO — exit 8 (MAGI_GATE_BLOCKED)."""


class QuotaExhaustedError(SBTDDError):
    """Anthropic API quota exhausted (rate limit / session / credit) — exit 11."""


class CommitError(SBTDDError):
    """Git commit subprocess failure (non-zero exit, timeout) — exit 1."""


class Loop1DivergentError(SBTDDError):
    """Loop 1 (/requesting-code-review) did not converge in 10 iterations (exit 7)."""


_EXIT_CODES_MUTABLE: dict[type[SBTDDError], int] = {
    ValidationError: 1,
    StateFileError: 1,
    CommitError: 1,
    DependencyError: 2,
    PreconditionError: 2,
    DriftError: 3,
    Loop1DivergentError: 7,
    MAGIGateError: 8,
    QuotaExhaustedError: 11,
}

#: Read-only exception-class -> exit-code registry (sec.S.11.1 canonical
#: taxonomy). Dispatchers at ``run_sbtdd.py`` read this mapping when
#: converting uncaught ``SBTDDError`` subclasses to process exit codes.
#: Keep aligned with the taxonomy in CLAUDE.md "Key Design Decisions".
EXIT_CODES: Mapping[type[SBTDDError], int] = MappingProxyType(_EXIT_CODES_MUTABLE)
