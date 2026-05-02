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
        f"exit took {t1 - t0:.2f}s; thread loop is using time.sleep instead of "
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


def test_heartbeat_first_failure_emits_breadcrumb_then_silent(monkeypatch):
    write_calls = {"count": 0}
    real_write = sys.stderr.write

    def failing_write(s):
        write_calls["count"] += 1
        if write_calls["count"] == 1 or write_calls["count"] >= 3:
            raise OSError("broken pipe")
        return real_write(s)

    monkeypatch.setattr(sys.stderr, "write", failing_write)
    emitter = HeartbeatEmitter(label="x", interval_seconds=0.05)
    with emitter:
        time.sleep(0.18)
    assert emitter._failed_writes >= 1


def test_heartbeat_failed_writes_counter_starts_zero():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    assert emitter._failed_writes == 0


def test_heartbeat_reports_failure_counter_via_queue_every_n10(monkeypatch):
    import queue as _q

    def always_fail(s):
        raise OSError("broken pipe")

    monkeypatch.setattr(sys.stderr, "write", always_fail)
    q: "_q.Queue[int]" = _q.Queue()
    emitter = HeartbeatEmitter(
        label="x",
        interval_seconds=0.01,
        failures_queue=q,
    )
    with emitter:
        deadline = time.monotonic() + 2.0
        while emitter._failed_writes < 10 and time.monotonic() < deadline:
            time.sleep(0.01)
    assert emitter._failed_writes >= 10
    drained: list[int] = []
    while not q.empty():
        drained.append(q.get_nowait())
    assert any(c >= 10 for c in drained), f"expected counter >= 10 in queue, got {drained}"


def test_heartbeat_exit_pushes_final_counter_to_queue():
    import queue as _q

    q: "_q.Queue[int]" = _q.Queue()
    emitter = HeartbeatEmitter(label="x", interval_seconds=15.0, failures_queue=q)
    with emitter:
        emitter._failed_writes = 7
    drained: list[int] = []
    while not q.empty():
        drained.append(q.get_nowait())
    assert drained[-1] == 7


def test_heartbeat_no_queue_means_no_persistence():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15.0, failures_queue=None)
    with emitter:
        emitter._failed_writes = 5
    # No assertion failure expected; just exercise the no-queue path.


def test_zombie_thread_count_persists_across_emitter_lifecycles():
    """C3 fold-in: class-level zombie counter persists across instances."""
    from heartbeat import HeartbeatEmitter as HE

    initial = HE._zombie_thread_count
    # Smoke: instances do not reset class-level counter.
    HeartbeatEmitter(label="a", interval_seconds=1.0)
    HeartbeatEmitter(label="b", interval_seconds=1.0)
    assert HE._zombie_thread_count == initial


def test_zombie_thread_threshold_raises_runtime_error_after_max(monkeypatch):
    """C3 fold-in: hard zombie threshold (5 default) raises RuntimeError.

    We simulate the zombie-detection path by setting the class counter
    just below threshold then forcing one __exit__ that registers a zombie.
    The actual zombie detection (thread.is_alive() after join timeout)
    requires real subprocess work; we mock the thread-join behavior.
    """
    from heartbeat import HeartbeatEmitter as HE

    # Save original counter.
    original = HE._zombie_thread_count
    try:
        # Set to threshold - 1 so that one more zombie pushes over.
        HE._zombie_thread_count = HE._max_zombie_threads - 1
        emitter = HeartbeatEmitter(label="z", interval_seconds=10.0)
        # Manually simulate __enter__ path then force a "blocked" thread.

        class FakeBlockedThread:
            def is_alive(self) -> bool:
                return True

            def join(self, timeout: float | None = None) -> None:
                return None

        emitter._stop_event = __import__("threading").Event()
        emitter._thread = FakeBlockedThread()  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="zombie"):
            emitter.__exit__(None, None, None)
    finally:
        HE._zombie_thread_count = original


def test_zombie_alert_sentinel_pushed_to_failures_queue(monkeypatch):
    """C3 fold-in: zombie counter persisted via failures queue with +1000 sentinel."""
    import queue as _q

    from heartbeat import HeartbeatEmitter as HE

    original = HE._zombie_thread_count
    try:
        HE._zombie_thread_count = 0
        q: "_q.Queue[int]" = _q.Queue()
        emitter = HeartbeatEmitter(label="z", interval_seconds=10.0, failures_queue=q)

        class FakeBlockedThread:
            def is_alive(self) -> bool:
                return True

            def join(self, timeout: float | None = None) -> None:
                return None

        emitter._stop_event = __import__("threading").Event()
        emitter._thread = FakeBlockedThread()  # type: ignore[assignment]
        emitter.__exit__(None, None, None)
        # Drain queue and look for sentinel.
        drained: list[int] = []
        while not q.empty():
            drained.append(q.get_nowait())
        # Sentinel: any value >= 1000 indicates zombie alert.
        assert any(v >= 1000 for v in drained), (
            f"expected zombie sentinel (>=1000) in queue, got {drained}"
        )
    finally:
        HE._zombie_thread_count = original
