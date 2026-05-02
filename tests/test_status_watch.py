#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for /sbtdd status --watch (sec.2.2 W1-W6)."""

from __future__ import annotations

import json

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


def test_w2_json_mode_emits_progress(tmp_path, capsys):
    """W2: JSON mode emits one timestamped JSON line per progress change."""
    from status_cmd import _watch_render_one

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(json.dumps({"progress": {"phase": 2}}), encoding="utf-8")
    _watch_render_one(auto_run_path, json_mode=True, last_progress=None)
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert "timestamp" in line
    assert line["progress"]["phase"] == 2


def test_w5_ctrl_c_returns_130(tmp_path, monkeypatch):
    """W5: KeyboardInterrupt mid-watch returns exit 130 (SIGINT convention)."""
    from status_cmd import watch_main

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(json.dumps({"progress": {"phase": 1}}), encoding="utf-8")

    def raise_kbi(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("status_cmd._watch_render_one", raise_kbi)
    rc = watch_main(auto_run_path, interval=1.0, json_mode=False)
    assert rc == 130


def test_watch_main_reads_auto_run_once_per_cycle(tmp_path, monkeypatch):
    """Loop 2 WARNING #9: ``watch_main`` must read auto-run.json once per cycle.

    Pre-fix the loop body called ``_watch_render_one`` (which itself calls
    ``_read_auto_run_with_retry`` to load the dict and emit the diff line)
    and then called ``_read_auto_run_with_retry`` AGAIN to drive the
    ``WatchPollState`` parse-failure / parse-success counter. Two reads
    per cycle wastes I/O and -- more importantly -- can produce
    inconsistent state machine updates if the two reads observe different
    on-disk payloads (one writer's atomic-replace can land between the
    pair). Post-fix the loop reads once and shares the dict between the
    diff check and the state update.

    This test counts ``_read_auto_run_with_retry`` invocations across one
    poll cycle by monkeypatching it; the cycle is forced to terminate
    after a single iteration via a sentinel that raises ``KeyboardInterrupt``
    on the second call to ``time.sleep`` (the one that gates the next
    cycle).
    """
    from status_cmd import watch_main

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(json.dumps({"progress": {"phase": 1}}), encoding="utf-8")

    call_counter = {"n": 0}
    real_read = __import__("status_cmd")._read_auto_run_with_retry

    def counting_read(path, *, max_retries: int = 5):
        call_counter["n"] += 1
        return real_read(path, max_retries=max_retries)

    monkeypatch.setattr("status_cmd._read_auto_run_with_retry", counting_read)

    sleeps = {"n": 0}

    def fake_sleep(_seconds):
        sleeps["n"] += 1
        # Allow the first sleep to execute (end of cycle 1); on the
        # second sleep break out of the poll loop so the test terminates.
        if sleeps["n"] >= 1:
            raise KeyboardInterrupt()

    monkeypatch.setattr("status_cmd.time.sleep", fake_sleep)

    rc = watch_main(auto_run_path, interval=1.0, json_mode=False)
    assert rc == 130  # KeyboardInterrupt path
    # One full cycle ran before the sleep raised -- assert the cycle did
    # NOT double-read auto-run.json.
    assert call_counter["n"] == 1, (
        f"watch_main read auto-run.json {call_counter['n']} times per cycle "
        f"(expected 1, Loop 2 WARNING #9)"
    )
