#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Mechanical smoke fixture for HeartbeatEmitter (sec.5.2 R2.3).

W6 fold-in: ships a real-time short-window primary fixture (sub-second
cadence, ~0.3s wall-clock window) plus a longer real-time fallback variant
that is skipped on CI (``CI=true``) to avoid sub-second jitter flakiness.
The primary fixture exercises the actual thread + ``threading.Event.wait``
path -- monkey-patching ``time.monotonic`` was considered but the daemon
thread internally calls ``Event.wait(timeout)`` which is OS-scheduled,
so a faked clock alone does not deterministically advance the loop. The
real-time short-window approach gives a permissive lower-bound assertion
(``>= 2`` ticks in 0.3s at 50ms cadence) which is robust enough for both
local and CI runs without flakiness on observed CI variance.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pytest

from heartbeat import HeartbeatEmitter, reset_current_progress, set_current_progress
from models import ProgressContext


def test_emitter_emits_ticks_at_short_cadence(capsys):
    """W6 PRIMARY: real-time short-window cadence (sub-second).

    Strategy: drive the daemon-thread loop with a 50ms interval over a
    ~0.3s wall-clock window. Permissive lower bound (>= 2 ticks) tolerates
    OS scheduler jitter; on CI variance the assertion still holds because
    the window is long enough to comfortably fit several intervals.

    The longer 2.5s real-time variant below is skipped on CI to avoid
    sub-second-cadence flakiness; it is retained as a developer-workstation
    sanity check.
    """
    reset_current_progress()
    set_current_progress(
        ProgressContext(
            iter_num=1,
            phase=2,
            task_index=3,
            task_total=10,
            dispatch_label="smoke-dispatch",
            started_at=datetime.now(timezone.utc),
        )
    )
    with HeartbeatEmitter(label="smoke-dispatch", interval_seconds=0.05):
        # Allow daemon thread to emit ~5 ticks (interval=0.05 over ~0.3s).
        time.sleep(0.3)
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines() if line.startswith("[sbtdd auto] tick:")
    ]
    # Permissive lower bound (NF-A: protect <90s budget; CI variance OK).
    assert len(tick_lines) >= 2, (
        f"expected >= 2 ticks in 0.3s window, got {len(tick_lines)}: {tick_lines}"
    )
    for line in tick_lines:
        assert "dispatch=smoke-dispatch" in line
        assert "elapsed=" in line
    reset_current_progress()


@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="W6 fallback: real-time sub-second cadence is CI-fragile",
)
def test_emitter_emits_ticks_real_time_fallback(capsys):
    """W6 FALLBACK: longer real-time sleep cadence; skipped on CI.

    Retained for developer-workstation verification of the actual
    thread + sleep path with a wider window (2.5s, 4-6 ticks expected
    at 0.5s cadence). CI relies on the short-window primary above
    which is robust to scheduler jitter; this longer variant tightens
    the upper bound and is therefore CI-fragile.
    """
    reset_current_progress()
    set_current_progress(
        ProgressContext(
            iter_num=1,
            phase=2,
            task_index=3,
            task_total=10,
            dispatch_label="smoke-dispatch",
            started_at=datetime.now(timezone.utc),
        )
    )
    with HeartbeatEmitter(label="smoke-dispatch", interval_seconds=0.5):
        time.sleep(2.5)
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines() if line.startswith("[sbtdd auto] tick:")
    ]
    assert 4 <= len(tick_lines) <= 6, (
        f"expected 4-6 ticks in 2.5s window, got {len(tick_lines)}: {tick_lines}"
    )
    reset_current_progress()
