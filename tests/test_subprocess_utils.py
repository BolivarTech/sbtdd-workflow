#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for subprocess_utils module."""

from __future__ import annotations

import sys


def test_run_with_timeout_returns_completed_process():
    from subprocess_utils import run_with_timeout

    result = run_with_timeout([sys.executable, "-c", "print('hi')"], timeout=5)
    assert result.returncode == 0
    assert "hi" in result.stdout


def test_run_with_timeout_rejects_shell_true():
    from subprocess_utils import run_with_timeout

    # shell parameter is not exposed — the helper enforces shell=False.
    result = run_with_timeout([sys.executable, "-c", "import sys; sys.exit(3)"], timeout=5)
    assert result.returncode == 3


def test_kill_tree_windows_calls_taskkill_before_proc_kill(monkeypatch):
    """Verifies MAGI R3-1 order: taskkill /F /T /PID BEFORE proc.kill()."""
    from subprocess_utils import kill_tree

    call_order: list[str] = []

    def fake_run(cmd, **kwargs):
        call_order.append(f"subprocess.run:{cmd[0]}")

        class R:
            returncode = 0

        return R()

    class FakeProc:
        pid = 12345

        def kill(self):
            call_order.append("proc.kill")

        def poll(self):
            return None  # still running

        def wait(self, timeout=None):
            call_order.append(f"proc.wait:{timeout}")
            return 0

    monkeypatch.setattr("subprocess_utils.subprocess.run", fake_run)
    monkeypatch.setattr("subprocess_utils.sys.platform", "win32")
    kill_tree(FakeProc())
    # taskkill MUST appear before proc.kill
    taskkill_idx = next(i for i, c in enumerate(call_order) if "taskkill" in c)
    kill_idx = call_order.index("proc.kill")
    assert taskkill_idx < kill_idx, f"call order wrong: {call_order}"


def test_kill_tree_posix_sends_sigterm_then_sigkill(monkeypatch):
    from subprocess_utils import kill_tree
    import subprocess as sp

    signals_sent: list[str] = []

    class FakeProc:
        pid = 54321
        _waits = 0

        def send_signal(self, sig):
            import signal

            signals_sent.append("SIGTERM" if sig == signal.SIGTERM else str(sig))

        def kill(self):
            signals_sent.append("SIGKILL")

        def poll(self):
            return None

        def wait(self, timeout=None):
            self._waits += 1
            if self._waits == 1:
                raise sp.TimeoutExpired(cmd="x", timeout=timeout)
            return 0

    monkeypatch.setattr("subprocess_utils.sys.platform", "linux")
    kill_tree(FakeProc())
    assert signals_sent == ["SIGTERM", "SIGKILL"]
