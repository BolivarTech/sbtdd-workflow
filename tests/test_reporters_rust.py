# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for reporters.rust_reporter (Task 16)."""

from __future__ import annotations

import subprocess

import pytest


def test_run_pipeline_invokes_nextest_piped_to_tdd_guard_rust(monkeypatch):
    from reporters import rust_reporter

    call_log: list[tuple[str, list[str]]] = []

    class FakeProc:
        def __init__(self, cmd, stdout=None, stdin=None, **kwargs):
            self.returncode = 0
            self.cmd = cmd
            self.stdout = b"junit-output"
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (self.stdout, self.stderr)

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    def fake_popen(cmd, stdout=None, stdin=None, stderr=None, **kwargs):
        call_log.append(("popen", cmd))
        return FakeProc(cmd, stdout=stdout, stdin=stdin)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rc = rust_reporter.run_pipeline(cwd=".")
    assert rc == 0
    # Two popens: cargo nextest, then tdd-guard-rust.
    assert len(call_log) == 2
    first, second = call_log[0][1], call_log[1][1]
    assert "cargo" in first[0]
    assert any("nextest" in tok for tok in first)
    assert "tdd-guard-rust" in second[0]


def test_run_pipeline_no_shell_obligatorio(monkeypatch):
    """Both Popen calls MUST use lists (shell=False equivalent); no str commands."""
    from reporters import rust_reporter

    captured_shell: list[bool] = []

    class FakeProc:
        def __init__(self, *a, **k):
            self.returncode = 0
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (b"", b"")

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    def fake_popen(cmd, shell=False, **kwargs):
        captured_shell.append(shell)
        assert isinstance(cmd, list), f"Popen must receive list, got {type(cmd).__name__}"
        return FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rust_reporter.run_pipeline(cwd=".")
    assert all(s is False for s in captured_shell)


def test_run_pipeline_propagates_nonzero_from_tdd_guard_rust(monkeypatch):
    from reporters import rust_reporter

    class FailingProc:
        def __init__(self, *a, **k):
            self.returncode = 2
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (b"", b"")

        def wait(self, timeout=None):
            return 2

        def poll(self):
            return 2

    class PassingProc(FailingProc):
        returncode = 0

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    calls: list[object] = []

    def fake_popen(cmd, **kwargs):
        # First call (nextest) passes, second (tdd-guard-rust) fails.
        proc = PassingProc() if not calls else FailingProc()
        calls.append(proc)
        return proc

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rc = rust_reporter.run_pipeline(cwd=".")
    assert rc == 2


def test_run_pipeline_honours_timeout_and_kills_both_procs(monkeypatch):
    """Triple-flagged MAGI Checkpoint 2 iter 1 WARNING (melchior/caspar/balthasar).

    When the pipeline exceeds its timeout, both processes must be
    kill-tree'd (Windows taskkill-before-kill via subprocess_utils.kill_tree)
    and ``subprocess.TimeoutExpired`` must surface to the caller.
    """
    from reporters import rust_reporter

    killed: list[object] = []

    class HangingProc:
        def __init__(self, *a, **k):
            self.returncode = None
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 1)

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 1)

        def poll(self):
            return None

    procs: list[HangingProc] = []

    def fake_popen(cmd, **kwargs):
        proc = HangingProc()
        procs.append(proc)
        return proc

    def fake_kill_tree(proc):
        killed.append(proc)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("subprocess_utils.kill_tree", fake_kill_tree)

    with pytest.raises(subprocess.TimeoutExpired):
        rust_reporter.run_pipeline(cwd=".", timeout=1)

    # Both nextest AND reporter procs must have been kill-tree'd.
    assert len(killed) == 2
    assert procs[0] in killed
    assert procs[1] in killed


def test_run_pipeline_default_timeout_is_documented(monkeypatch):
    """The default timeout is 300s (documented in module docstring)."""
    from reporters import rust_reporter

    # The module exposes the constant for discoverability.
    assert rust_reporter._DEFAULT_TIMEOUT_SEC == 300


def test_run_pipeline_nextest_exit_slack_constant_exposed():
    """The nextest post-EOF slack is a named constant, not a magic number.

    Elevated per MAGI Checkpoint 2 iter 2 WARNING (melchior): hardcoded
    5-second timeouts inside the cleanup path are a maintenance smell.
    """
    from reporters import rust_reporter

    assert rust_reporter._NEXTEST_EXIT_SLACK_SECONDS == 5


def test_run_pipeline_nextest_wait_timeout_also_kills_both_procs(monkeypatch):
    """Fix 4 (MAGI ckpt2 iter 2 caspar WARNING): if the *nextest* post-EOF
    wait times out (while reporter has already finished cleanly), both
    procs must still be kill-tree'd before TimeoutExpired re-raises.
    Orphaning nextest here would leak a child process."""
    from reporters import rust_reporter

    killed: list[object] = []

    class ReporterFinishedProc:
        """Reporter exits cleanly before timeout."""

        def __init__(self):
            self.returncode = 0
            self.stdout = b"ok"
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (self.stdout, self.stderr)

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    class NextestHangingProc:
        """Nextest hangs past the exit slack."""

        def __init__(self):
            self.returncode = None
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            raise subprocess.TimeoutExpired(cmd="nextest", timeout=timeout or 1)

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="nextest", timeout=timeout or 1)

        def poll(self):
            return None

    procs: list[object] = []

    def fake_popen(cmd, **kwargs):
        # First call -> nextest (hangs), second -> reporter (finishes).
        proc: object
        if not procs:
            proc = NextestHangingProc()
        else:
            proc = ReporterFinishedProc()
        procs.append(proc)
        return proc

    def fake_kill_tree(proc):
        killed.append(proc)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("subprocess_utils.kill_tree", fake_kill_tree)

    with pytest.raises(subprocess.TimeoutExpired):
        rust_reporter.run_pipeline(cwd=".", timeout=60)

    # Both procs kill-tree'd despite only nextest being the timeout cause.
    assert len(killed) == 2
    assert procs[0] in killed, "nextest (the hanging one) must be killed"
    assert procs[1] in killed, "reporter must also be killed defensively"
