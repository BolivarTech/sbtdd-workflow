#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Subprocess wrappers enforcing sec.S.8.6 conventions.

- shell=False always.
- Arguments as lists, not strings.
- Explicit timeouts.
- Windows kill-tree via taskkill /F /T /PID BEFORE proc.kill() (MAGI R3-1).
"""

from __future__ import annotations

import signal
import subprocess
import sys


def run_with_timeout(
    cmd: list[str],
    timeout: int,
    capture: bool = True,
    cwd: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command with shell=False and an explicit timeout.

    Args:
        cmd: Command as list of strings (never a single string).
        timeout: Wall-clock seconds before SIGTERM.
        capture: If True, capture stdout/stderr as text.
        cwd: Working directory (None = current).

    Returns:
        CompletedProcess with returncode, stdout, stderr.

    Raises:
        subprocess.TimeoutExpired: If the process did not finish in time.
    """
    return subprocess.run(
        cmd,
        shell=False,
        capture_output=capture,
        text=True,
        timeout=timeout,
        cwd=cwd,
        check=False,
    )


def kill_tree(proc: subprocess.Popen[str]) -> None:
    """Terminate process and all children cross-platform.

    Windows: taskkill /F /T /PID <pid> BEFORE proc.kill() (MAGI R3-1 —
    parent must still be alive for taskkill to enumerate its descendants).
    POSIX: SIGTERM + 3-second wait + SIGKILL fallback.

    Args:
        proc: Running Popen instance.
    """
    if proc.poll() is not None:
        return  # Already exited.
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                shell=False,
                capture_output=True,
                timeout=5,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Fall through to proc.kill as belt-and-suspenders.
        proc.kill()
        proc.wait(timeout=5)
    else:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
