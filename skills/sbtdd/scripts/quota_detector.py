#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Detection of Anthropic API quota exhaustion (sec.S.11.4).

The plugin invokes skills (superpowers, magi) that internally run
claude -p against the Anthropic API. When the API hits rate limits or
subscription/credit limits, the skill's stderr contains distinctive
messages. This module regex-matches those patterns and returns a
typed QuotaExhaustion result; the dispatcher raises QuotaExhaustedError
and exits with code 11.

Patterns are brittle (Anthropic can change the text). Centralizing them
here makes updates a one-file change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

_QUOTA_PATTERNS_MUTABLE: dict[str, re.Pattern[str]] = {
    "rate_limit_429": re.compile(r"Request rejected \(429\)"),
    # Per MAGI Checkpoint 2 iter 1 (caspar): accept alternative separators
    # (middle-dot U+00B7, ASCII hyphen, en-dash, em-dash, colon) because
    # Anthropic may tweak copy. Also allow surrounding whitespace.
    # Per MAGI Loop 2 Finding 9: capture reset_time until end-of-line or
    # a 2+ whitespace gap, so multi-word values like "3:45pm tomorrow"
    # or "10:00 AM (UTC)" are preserved. Trailing single-whitespace no
    # longer truncates the capture.
    "session_limit": re.compile(
        r"You've hit your (session|weekly|Opus) limit\s*[·\-–—:]\s*resets (.+?)(?:\s{2,}|\s*$)",
        re.MULTILINE,
    ),
    "credit_exhausted": re.compile(r"Credit balance is too low"),
    "server_throttle": re.compile(r"Server is temporarily limiting requests"),
}

#: Read-only registry of quota exhaustion regex patterns.
QUOTA_PATTERNS: Mapping[str, re.Pattern[str]] = MappingProxyType(_QUOTA_PATTERNS_MUTABLE)


@dataclass(frozen=True)
class QuotaExhaustion:
    """Parsed result of a quota-exhaustion match on stderr."""

    kind: str  # Key of QUOTA_PATTERNS that matched.
    raw_message: str  # Matched substring from stderr.
    reset_time: str | None  # Extracted from session_limit pattern; None otherwise.
    recoverable: bool  # True for all current cases.


def detect(stderr: str) -> QuotaExhaustion | None:
    """Scan stderr for quota exhaustion patterns.

    Args:
        stderr: Standard error output from an invoked skill/subprocess.

    Returns:
        QuotaExhaustion if any pattern matches; None otherwise.
    """
    for kind, pattern in QUOTA_PATTERNS.items():
        match = pattern.search(stderr)
        if match:
            reset_time = match.group(2) if kind == "session_limit" else None
            return QuotaExhaustion(
                kind=kind,
                raw_message=match.group(0),
                reset_time=reset_time,
                recoverable=True,
            )
    return None
