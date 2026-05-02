#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for /sbtdd status --watch (sec.2.2 W1-W6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_w3_watch_exits_zero_when_auto_run_missing(tmp_path, capsys):
    """W3: missing auto-run.json -> exit 0 with operator-friendly message."""
    from status_cmd import _watch_loop_once

    rc = _watch_loop_once(tmp_path / "missing.json", json_mode=False)
    assert rc == 0
    captured = capsys.readouterr()
    assert "no auto run in progress" in captured.err.lower()


def test_w1_watch_render_tty_contains_progress_fields():
    """W1: TTY render packs iter / phase / task / dispatch into one line."""
    from status_cmd import _watch_render_tty

    progress = {
        "iter_num": 2,
        "phase": 3,
        "task_index": 14,
        "task_total": 36,
        "dispatch_label": "magi-loop2-iter2",
        "started_at": "2026-05-01T12:00:00Z",
    }
    output = _watch_render_tty(progress)
    assert "iter 2" in output
    assert "phase 3" in output
    assert "task 14/36" in output
    assert "magi-loop2-iter2" in output


def test_w6_validates_interval_minimum():
    """W6: --interval below 0.1s rejected (sub-100ms spins CPU)."""
    from errors import ValidationError
    from status_cmd import validate_watch_interval

    with pytest.raises(ValidationError, match=">= 0.1"):
        validate_watch_interval(0.05)
    validate_watch_interval(0.1)
    validate_watch_interval(5.0)


def test_w4_retry_5x_with_4_sleeps_between_attempts(tmp_path, monkeypatch):
    """W4: 5 attempts, 4 sleeps between (no sleep after final fail)."""
    from status_cmd import _read_auto_run_with_retry

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("not-json", encoding="utf-8")

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))
    result = _read_auto_run_with_retry(auto_run_path, max_retries=5)
    assert result is None
    # Per Checkpoint 2 iter 1 melchior fix: 4 sleeps (between 5 attempts), not 5.
    assert sleep_calls == [0.05, 0.1, 0.2, 0.4]


def test_w4_slow_poll_fallback_after_3_consecutive_parse_failures():
    """W4: slow-poll doubles interval after 3 consecutive parse failures."""
    from status_cmd import WatchPollState

    state = WatchPollState(default_interval=1.0)
    state.record_parse_failure()
    state.record_parse_failure()
    state.record_parse_failure()
    assert state.current_interval == 2.0
    state.record_parse_failure()
    assert state.current_interval == 4.0
    state.record_parse_failure()
    state.record_parse_failure()
    state.record_parse_failure()
    assert state.current_interval <= 10.0
    state.record_parse_success()
    assert state.current_interval == 1.0


def test_w4_idle_does_not_trigger_slow_poll(tmp_path):
    """Idle auto-run (same data on each poll) does NOT trigger slow-poll."""
    from status_cmd import WatchPollState

    state = WatchPollState(default_interval=1.0)
    for _ in range(10):
        state.record_parse_success()
    assert state.current_interval == 1.0  # NEVER doubled
    assert state.consecutive_parse_failures == 0


def test_w4_three_consecutive_parse_failures_triggers_slow_poll():
    """W4: exactly 3 consecutive failures crosses the threshold."""
    from status_cmd import WatchPollState

    state = WatchPollState(default_interval=1.0)
    state.record_parse_failure()
    state.record_parse_failure()
    state.record_parse_failure()
    assert state.current_interval == 2.0
    state.record_parse_success()
    assert state.current_interval == 1.0
