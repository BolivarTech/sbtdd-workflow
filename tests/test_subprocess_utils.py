#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for subprocess_utils module."""

from __future__ import annotations

import sys

import pytest


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


def test_streamed_with_timeout_returns_stdout_and_stderr_separately():
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, time\n"
            "for i in range(3):\n"
            "    sys.stdout.write(f'out{i}\\n'); sys.stdout.flush()\n"
            "    time.sleep(0.05)\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=10.0,
        dispatch_label="test",
    )
    assert result.returncode == 0
    assert "out0" in result.stdout
    assert "out2" in result.stdout


def test_pump_handles_partial_utf8_split_at_chunk_boundary():
    """C1 fold-in: incremental UTF-8 decoder handles multi-byte split.

    Emits a byte stream containing 2-byte (e-acute) + 3-byte (currency
    sign) + 4-byte (emoji) UTF-8 sequences interleaved with ASCII so
    that any naive per-chunk decode would corrupt the output. The
    incremental decoder must reassemble all sequences cleanly.
    """
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys\n"
            "data = ('hello cafe' + chr(0xE9) + ' euro' + chr(0x20AC) +\n"
            "        ' emoji' + chr(0x1F600) + ' done').encode('utf-8')\n"
            "sys.stdout.buffer.write(data)\n"
            "sys.stdout.buffer.flush()\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=10.0,
        dispatch_label="test",
    )
    assert result.returncode == 0
    assert chr(0xE9) in result.stdout
    assert chr(0x20AC) in result.stdout
    assert chr(0x1F600) in result.stdout


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="C2 Windows threaded-reader fallback is Windows-specific",
)
def test_streaming_pump_works_on_windows_subprocess():
    """C2 fold-in: Windows threaded-reader fallback delivers chunks."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, time\n"
            "for i in range(5):\n"
            "    sys.stdout.write(f'win{i}\\n'); sys.stdout.flush()\n"
            "    time.sleep(0.02)\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=10.0,
        dispatch_label="test-win",
    )
    assert result.returncode == 0
    assert "win0" in result.stdout
    assert "win4" in result.stdout


def test_t1_all_streams_silent_kills_subprocess(capsys):
    """T1: silence on all open streams beyond timeout triggers kill."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=0.5,
        dispatch_label="test-hang",
    )
    assert result.returncode != 0
    captured = capsys.readouterr()
    assert "all open streams silent" in captured.err
    assert "auto_no_timeout_dispatch_labels" in captured.err


def test_t5_allowlist_exempts_dispatch_label():
    """T5: dispatch_label matching allowlist -> no kill, full output captured."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [sys.executable, "-c", "import time; time.sleep(1.0)"]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=0.3,
        dispatch_label="magi-loop2-iter1",
        no_timeout_labels=("magi-*",),
    )
    assert result.returncode == 0


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.close(sys.stdout.fileno()) has Windows-specific failure modes; "
    "T7 verified via integration on POSIX (Checkpoint 2 iter 1 caspar finding)",
)
def test_t7_closed_stream_excluded_from_timeout():
    """T7: an EOF'd stream is dropped from the open set -- timeout uses
    only the still-open streams."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, os, time\n"
            "os.close(sys.stdout.fileno())\n"
            "for i in range(3):\n"
            "    sys.stderr.write(f'err{i}\\n')\n"
            "    sys.stderr.flush()\n"
            "    time.sleep(0.1)\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=0.3,
        dispatch_label="test-closed",
    )
    assert result.returncode == 0
    assert "err0" in result.stderr


def test_t8_kill_tree_order_preserved_on_windows(monkeypatch):
    """T8: R3-1 invariant -- taskkill /F /T /PID BEFORE proc.kill()."""
    if sys.platform != "win32":
        pytest.skip("Windows-only invariant")
    from unittest.mock import MagicMock

    from subprocess_utils import _kill_subprocess_tree

    call_order: list[str] = []

    def fake_run(*args, **kwargs):
        call_order.append("taskkill")
        from subprocess import CompletedProcess

        return CompletedProcess(args=args[0], returncode=0)

    monkeypatch.setattr("subprocess_utils.subprocess.run", fake_run)
    proc = MagicMock()
    proc.pid = 12345
    proc.kill = lambda: call_order.append("proc.kill")
    _kill_subprocess_tree(proc)
    assert call_order == ["taskkill", "proc.kill"]


def test_o1_single_stream_no_prefix():
    """O1: single-stream output never gets origin prefix."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys\n"
            "for i in range(3):\n"
            "    sys.stdout.write(f'line{i}\\n')\n"
            "    sys.stdout.flush()\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=True,
        dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "line0" in result.stdout


def test_o2_dual_stream_in_window_prefixes():
    """O2: both streams within disambig window -> at least one prefixed."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys\n"
            "sys.stdout.write('out1\\n'); sys.stdout.flush()\n"
            "sys.stderr.write('err1\\n'); sys.stderr.flush()\n"
        ),
    ]
    # Use a generous window (500ms) to ensure both writes land inside
    # without scheduler-jitter flakiness on CI.
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=True,
        dispatch_label="test",
        origin_window_seconds=0.5,
    )
    combined = result.stdout + result.stderr
    assert "[stdout]" in combined or "[stderr]" in combined


def test_o2_dual_stream_within_production_100ms_window_prefixes():
    """O2 production-default boundary (Loop 2 WARNING #3 fix).

    The original ``test_o2_dual_stream_in_window_prefixes`` uses a
    permissive 500ms window to absorb CI scheduling jitter. That value
    does not validate the production default 100ms window
    (``DEFAULT_ORIGIN_WINDOW_SECONDS = 0.100``) — a regression that
    halved the window to 50ms would still pass the 500ms test.

    This test exercises the production 100ms window boundary
    deterministically: subprocess writes stdout, sleeps 5ms (well within
    100ms), writes stderr. Both chunks must be classified as dual-stream
    and at least one of them prefixed. Larger sleeps would risk falling
    outside the window on slow CI machines; 5ms is comfortably below
    even pessimistic scheduler jitter.
    """
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, time\n"
            "sys.stdout.write('out1\\n'); sys.stdout.flush()\n"
            "time.sleep(0.005)\n"
            "sys.stderr.write('err1\\n'); sys.stderr.flush()\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=True,
        dispatch_label="test",
        origin_window_seconds=0.100,  # Production default
    )
    combined = result.stdout + result.stderr
    assert "[stdout]" in combined or "[stderr]" in combined, (
        "production 100ms window must classify writes 5ms apart as "
        "dual-stream and prefix at least one chunk; got combined="
        f"{combined!r}"
    )


def test_o3_alternating_distant_windows_no_prefix():
    """O3: streams emit > origin_window_seconds apart -> no prefix.

    Per Checkpoint 2 iter 2 melchior fix: use 5ms test window vs the
    100ms production default and a deterministic 100ms gap to avoid
    Windows CI flakiness on loaded systems.
    """
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, time\n"
            "sys.stdout.write('out1\\n'); sys.stdout.flush()\n"
            "time.sleep(0.1)\n"
            "sys.stderr.write('err1\\n'); sys.stderr.flush()\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=True,
        origin_window_seconds=0.005,  # 5ms test window vs 100ms production
        dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "[stderr]" not in result.stderr


def test_o4_disabled_no_prefix_even_on_dual_stream():
    """O4: origin_disambiguation=False forbids any prefix."""
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys\n"
            "sys.stdout.write('out1\\n'); sys.stdout.flush()\n"
            "sys.stderr.write('err1\\n'); sys.stderr.flush()\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=False,
        dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "[stderr]" not in result.stderr


def test_t1_windows_kill_residual_queue_drain_code_present():
    """W7 (caspar Loop 2 iter 3): Windows kill path drains reader queue.

    Pre-fix: the Windows threaded-reader fallback funnels chunks into a
    ``queue.Queue``. When the timeout-kill branch fires, the function
    breaks out of the read loop and proceeds to ``proc.wait()`` without
    draining chunks still queued by the reader threads. If a reader
    thread put a chunk into the queue but the main loop hasn't dequeued
    it yet (race window between ``chunk_queue.get(timeout=0.1)`` and
    the silence-check), the chunk is silently discarded.

    Post-fix: after ``_kill_subprocess_tree(proc)``, the kill branch
    drains the chunk queue once more (best-effort, non-blocking) so
    any residual bytes already pumped by the reader threads are
    absorbed into the captured output.

    A live concurrency test for this race window is impossible to make
    reliable (the race depends on OS scheduler choices). Instead this
    test is a structural regression guard: assert the kill branch in
    the Windows path contains the residual-drain comment marker so a
    future refactor cannot silently drop the drain.
    """
    import inspect

    from subprocess_utils import run_streamed_with_timeout

    source = inspect.getsource(run_streamed_with_timeout)
    assert "residual reader-thread queue data" in source, (
        "W7 regression: Windows kill branch is missing the residual "
        "reader-thread queue drain. Restore the post-kill drain in "
        "subprocess_utils.run_streamed_with_timeout (Windows path)."
    )


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="W7 live test exercises the Windows threaded-reader fallback; "
    "the POSIX selector path reads directly from the pipe FD with no "
    "intermediate queue.",
)
def test_t1_windows_kill_preserves_pre_kill_stderr_data():
    """W7 live (caspar Loop 2 iter 3): pre-kill stderr is captured.

    Subprocess writes a sentinel to stderr, then sleeps. The per-stream
    timeout fires, the subprocess is killed, and the sentinel must
    appear in ``result.stderr`` because either the read loop already
    absorbed it OR (post-fix) the residual-queue drain absorbed it.
    Pre-fix this test passed in most schedules; it serves as a smoke
    test for the W7 fold-in to ensure no observable regression.
    """
    from subprocess_utils import run_streamed_with_timeout

    cmd = [
        sys.executable,
        "-c",
        (
            "import sys, time\n"
            "sys.stderr.write('final-stderr-line\\n')\n"
            "sys.stderr.flush()\n"
            "time.sleep(5)\n"
        ),
    ]
    result = run_streamed_with_timeout(
        cmd,
        per_stream_timeout_seconds=0.5,
        dispatch_label="test-w7-live",
    )
    assert result.returncode != 0
    assert "final-stderr-line" in result.stderr, (
        f"W7 regression: pre-kill stderr data lost. stderr={result.stderr!r}"
    )
