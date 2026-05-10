#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""Tests for sample.py + INV-16 isatty observation marker.

The ``test_isatty_observation`` test prints whether ``sys.stdin``
attached to the test runner is a TTY. On v1.0.7 POSIX the worker
inherits the PTY slave from ``subprocess_utils._spawn_worker_with_pty``
so isatty observes ``True``. On Windows the worker uses
``subprocess.PIPE`` (Option B-W3 hybrid) so isatty observes ``False``
but the worker bypasses the interactive skill via the
``SBTDD_AUTO_PARALLEL_WORKER`` env var so the chain still completes
without hanging.
"""

from __future__ import annotations

import os
import sys

from sample import add


def test_add_returns_sum() -> None:
    """Trivial smoke test."""
    assert add(2, 3) == 5


def test_add_zero_identity() -> None:
    """Zero is the additive identity."""
    assert add(0, 7) == 7


def test_isatty_observation() -> None:
    """INV-16 evidence-before-assertions marker for v1.0.7 A1/A2 dogfood.

    Prints isatty status + worker env marker so parent post-batch merge
    of the per-worker sidecar (under ``.claude/auto-run-workers/``) has
    visible evidence of which spawn path the worker took.
    """
    is_tty = sys.stdin.isatty()
    worker_marker = os.environ.get("SBTDD_AUTO_PARALLEL_WORKER", "<unset>")
    sys.stdout.write(
        f"[v1.0.7-a3-marker] isatty={is_tty} SBTDD_AUTO_PARALLEL_WORKER={worker_marker}\n"
    )
    # No assertion -- this test is observation-only; the actual gate is
    # the parent test's sidecar inspection in tests/test_auto_parallel_e2e.py.
    assert True
