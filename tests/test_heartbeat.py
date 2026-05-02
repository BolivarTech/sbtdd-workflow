#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for the v0.5.0 heartbeat module."""

from __future__ import annotations

import pytest

from heartbeat import (
    HeartbeatEmitter,
    get_current_progress,
    reset_current_progress,
    set_current_progress,
)
from models import ProgressContext


@pytest.fixture(autouse=True)
def _reset_progress():
    reset_current_progress()
    yield
    reset_current_progress()


def test_get_current_progress_initial_is_default_progress():
    assert get_current_progress() == ProgressContext()


def test_set_then_get_returns_same_reference():
    new_ctx = ProgressContext(iter_num=2, phase=3)
    set_current_progress(new_ctx)
    assert get_current_progress() is new_ctx


def test_repeated_set_replaces_singleton():
    set_current_progress(ProgressContext(iter_num=1))
    set_current_progress(ProgressContext(iter_num=2))
    assert get_current_progress().iter_num == 2


def test_reset_returns_default_after_set():
    set_current_progress(ProgressContext(iter_num=99))
    reset_current_progress()
    assert get_current_progress() == ProgressContext()


def test_heartbeat_emitter_class_exists():
    """Smoke check: scaffold class importable; full behavior tested in S1-3+."""
    assert HeartbeatEmitter is not None
