#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E model registry constants."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import models


def test_allowed_claude_model_ids_is_tuple() -> None:
    """E6.1: ALLOWED_CLAUDE_MODEL_IDS is immutable (tuple, not list)."""
    assert isinstance(models.ALLOWED_CLAUDE_MODEL_IDS, tuple)
    with pytest.raises((AttributeError, TypeError)):
        models.ALLOWED_CLAUDE_MODEL_IDS.append("foo")  # type: ignore[attr-defined]


def test_allowed_claude_model_ids_contains_current_4x_families() -> None:
    """E6.2: tuple contains at least Opus 4.7, Sonnet 4.6, Haiku 4.5."""
    ids = set(models.ALLOWED_CLAUDE_MODEL_IDS)
    assert "claude-opus-4-7" in ids
    assert "claude-sonnet-4-6" in ids
    assert "claude-haiku-4-5-20251001" in ids
