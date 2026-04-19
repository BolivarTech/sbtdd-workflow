#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for quota_detector module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "quota-errors"


def test_quota_patterns_is_mapping_proxy():
    from quota_detector import QUOTA_PATTERNS

    assert isinstance(QUOTA_PATTERNS, MappingProxyType)


def test_quota_patterns_has_four_kinds():
    from quota_detector import QUOTA_PATTERNS

    assert set(QUOTA_PATTERNS.keys()) == {
        "rate_limit_429",
        "session_limit",
        "credit_exhausted",
        "server_throttle",
    }


def test_quota_patterns_are_compiled_regex():
    import re

    from quota_detector import QUOTA_PATTERNS

    for pattern in QUOTA_PATTERNS.values():
        assert isinstance(pattern, re.Pattern)


def test_quota_exhaustion_is_frozen():
    from quota_detector import QuotaExhaustion

    q = QuotaExhaustion(
        kind="session_limit",
        raw_message="...",
        reset_time="3:45pm",
        recoverable=True,
    )
    with pytest.raises(FrozenInstanceError):
        q.kind = "other"  # type: ignore[misc]


def test_quota_exhaustion_fields():
    from quota_detector import QuotaExhaustion

    fields = set(QuotaExhaustion.__dataclass_fields__)
    assert fields == {"kind", "raw_message", "reset_time", "recoverable"}


def test_detect_session_limit_extracts_reset_time():
    from quota_detector import detect

    stderr = (FIXTURES_DIR / "session_limit.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "session_limit"
    assert result.reset_time == "3:45pm"
    assert result.recoverable is True


def test_detect_rate_limit_429():
    from quota_detector import detect

    stderr = (FIXTURES_DIR / "rate_limit_429.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "rate_limit_429"
    assert result.reset_time is None


def test_detect_credit_exhausted():
    from quota_detector import detect

    stderr = (FIXTURES_DIR / "credit_exhausted.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "credit_exhausted"


def test_detect_server_throttle():
    from quota_detector import detect

    stderr = (FIXTURES_DIR / "server_throttle.txt").read_text()
    result = detect(stderr)
    assert result is not None
    assert result.kind == "server_throttle"


def test_detect_no_match_returns_none():
    from quota_detector import detect

    stderr = (FIXTURES_DIR / "no_quota_match.txt").read_text()
    assert detect(stderr) is None
