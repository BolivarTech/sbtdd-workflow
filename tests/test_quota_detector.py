#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for quota_detector module."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest


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
