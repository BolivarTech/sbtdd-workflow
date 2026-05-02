#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for the v0.5.0 heartbeat module."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone

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


def test_heartbeat_emitter_context_manager_protocol():
    emitter = HeartbeatEmitter(label="test-dispatch", interval_seconds=15)
    assert emitter.label == "test-dispatch"
    assert emitter.interval_seconds == 15
    with emitter as e:
        assert e is emitter


def test_heartbeat_emitter_validates_interval_positive():
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        HeartbeatEmitter(label="x", interval_seconds=0)
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        HeartbeatEmitter(label="x", interval_seconds=-1)


def test_heartbeat_thread_emits_ticks_during_active_lifetime(capsys):
    set_current_progress(
        ProgressContext(
            iter_num=2,
            phase=3,
            task_index=14,
            task_total=36,
            dispatch_label="test-dispatch",
            started_at=datetime.now(timezone.utc),
        )
    )
    with HeartbeatEmitter(label="test-dispatch", interval_seconds=0.05):
        time.sleep(0.18)  # ~3 ticks at 50ms cadence
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines() if line.startswith("[sbtdd auto] tick:")
    ]
    assert len(tick_lines) >= 2


def test_heartbeat_exit_join_returns_within_timeout_when_thread_sleeping():
    """Verify Event.wait() (NOT time.sleep) so __exit__ can interrupt mid-tick."""
    emitter = HeartbeatEmitter(label="x", interval_seconds=10.0)
    t0 = time.monotonic()
    with emitter:
        time.sleep(0.1)
    t1 = time.monotonic()
    assert t1 - t0 < 2.5, (
        f"exit took {t1-t0:.2f}s; thread loop is using time.sleep instead of "
        f"threading.Event.wait()"
    )
    # Make sure sys is referenced so import isn't unused.
    _ = sys.stderr


def test_format_tick_full_fields_matches_h5():
    fake_start = datetime.now(timezone.utc) - timedelta(seconds=15)
    ctx = ProgressContext(
        iter_num=2,
        phase=3,
        task_index=14,
        task_total=36,
        dispatch_label="magi-loop2-iter2",
        started_at=fake_start,
    )
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ctx)
    assert line.startswith("[sbtdd auto] tick:")
    assert "iter 2" in line
    assert "phase 3" in line
    assert "task 14/36" in line
    assert "dispatch=magi-loop2-iter2" in line
    assert "elapsed=" in line
    assert any(s in line for s in ("0m14s", "0m15s", "0m16s"))


def test_format_tick_omits_null_fields_h6():
    fake_start = datetime.now(timezone.utc) - timedelta(seconds=45)
    ctx = ProgressContext(phase=1, started_at=fake_start)
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ctx)
    assert "phase 1" in line
    assert "iter " not in line
    assert "task " not in line
    assert "dispatch=" not in line
    assert "elapsed=" in line


def test_format_tick_no_started_at_omits_elapsed():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ProgressContext())
    assert line.startswith("[sbtdd auto] tick:")
    assert "phase 0" in line
    assert "elapsed" not in line
