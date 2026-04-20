#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Rust stack TDD-Guard reporter: pipeline ``cargo nextest`` | ``tdd-guard-rust``.

Invoked as ``verification_commands[0]`` by ``--stack rust`` (sec.S.4.2).
Runs ``cargo nextest run --message-format libtest-json-plus`` (the machine-
readable JSON format nextest emits) and pipes stdout into the external
``tdd-guard-rust`` binary, which translates it into the canonical
``.claude/tdd-guard/data/test.json`` schema.

Never uses ``shell=True``. Arguments passed as lists. The ``tdd-guard-rust``
binary is a mandatory external dependency (sec.S.1.3 item 6 Rust); dependency
check (dependency_check.check_stack_toolchain('rust')) verifies it before
any reporter invocation.

Deliberate ``subprocess.Popen`` exception (vs the project-standard
``subprocess_utils.run_with_timeout``): piping stdout of one process into
stdin of another requires two concurrent handles, which the helper does not
expose. The timeout discipline from NF5 is preserved here manually via the
``timeout`` parameter + ``subprocess_utils.kill_tree`` for cleanup on the
two Popens (MAGI Checkpoint 2 iter 1 triple-flagged WARNING from melchior,
caspar, and balthasar).
"""

from __future__ import annotations

import subprocess
import sys
from typing import Iterable

import subprocess_utils

_NEXTEST_CMD: tuple[str, ...] = (
    "cargo",
    "nextest",
    "run",
    "--message-format",
    "libtest-json-plus",
)
_TDD_GUARD_RUST_CMD: tuple[str, ...] = ("tdd-guard-rust",)
#: Default timeout for the nextest + reporter pipeline. Long runs are
#: legitimate (integration suites), but 5 min is the outer bound before
#: the caller must explicitly raise the cap.
_DEFAULT_TIMEOUT_SEC: int = 300
#: Slack window given to ``cargo nextest`` to flush and exit after the
#: downstream reporter has already consumed its stdout. Nextest's epilog
#: (JSON footer + child-test teardown) runs post-EOF on the pipe, and 5s
#: is empirically more than enough on CI. Elevated to a named constant
#: per MAGI Checkpoint 2 iter 2 WARNING (melchior): hardcoded integers in
#: timeout paths are a maintenance smell.
_NEXTEST_EXIT_SLACK_SECONDS: int = 5


def run_pipeline(
    cwd: str | None = None,
    nextest_cmd: Iterable[str] = _NEXTEST_CMD,
    reporter_cmd: Iterable[str] = _TDD_GUARD_RUST_CMD,
    timeout: int = _DEFAULT_TIMEOUT_SEC,
) -> int:
    """Run ``cargo nextest run | tdd-guard-rust`` as a two-process pipeline.

    Args:
        cwd: Working directory for both subprocesses. ``None`` uses current.
        nextest_cmd: Override the nextest invocation (tests / future stacks).
        reporter_cmd: Override the reporter invocation.
        timeout: Wall-clock seconds for the combined pipeline before
            SIGTERM + cleanup via :func:`subprocess_utils.kill_tree`.
            Default 300s (5 min). Raising the cap is the caller's
            responsibility.

    Returns:
        The exit code of the reporter subprocess (right-hand side of the
        pipe). The caller (verification runner) propagates this to its
        overall return code.

    Raises:
        subprocess.TimeoutExpired: If the combined pipeline exceeds
            ``timeout``. Both nextest and tdd-guard-rust are kill-tree'd
            (Windows taskkill-before-kill via
            :func:`subprocess_utils.kill_tree`) before the exception
            surfaces. The caller can wrap this as needed.
    """
    nextest = subprocess.Popen(
        list(nextest_cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
    )
    reporter = subprocess.Popen(
        list(reporter_cmd),
        stdin=nextest.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
    )
    # Close nextest's stdout in the parent so the reporter sees EOF when
    # nextest exits (POSIX pipeline semantics). Guarded ``hasattr`` check
    # keeps test mocks (which use raw bytes for ``stdout``) compatible with
    # the real ``subprocess.Popen`` contract where ``stdout`` is a
    # BufferedReader exposing ``close()``.
    if nextest.stdout is not None and hasattr(nextest.stdout, "close"):
        nextest.stdout.close()
    try:
        out, err = reporter.communicate(timeout=timeout)
        # Reporter is done; ensure nextest is also wrapped up within the
        # explicit slack window. This wait CAN itself raise TimeoutExpired
        # (e.g., nextest hangs after emitting its JSON footer) and that
        # path is just as lethal as the reporter timing out — so the same
        # except-clause below handles both, killing BOTH procs before
        # re-raising. Fix 4 (MAGI ckpt2 iter 2 caspar WARNING): the
        # cleanup path is shared and guaranteed so no orphan remains on
        # either failure mode.
        nextest.wait(timeout=_NEXTEST_EXIT_SLACK_SECONDS)
    except subprocess.TimeoutExpired:
        # Kill BOTH processes cross-platform (Windows taskkill-before-kill)
        # regardless of which wait raised. kill_tree is idempotent on an
        # already-exited proc (subprocess_utils guarantees this on both
        # POSIX and Windows).
        subprocess_utils.kill_tree(reporter)
        subprocess_utils.kill_tree(nextest)
        # Drain pipes to avoid zombie FDs; ignore further timeouts here.
        for proc in (reporter, nextest):
            try:
                proc.communicate(timeout=_NEXTEST_EXIT_SLACK_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        raise
    if err:
        sys.stderr.write(err.decode("utf-8", errors="replace"))
    if out:
        sys.stdout.write(out.decode("utf-8", errors="replace"))
    return reporter.returncode


def main() -> int:
    """Entry point when invoked as a standalone script."""
    return run_pipeline()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
