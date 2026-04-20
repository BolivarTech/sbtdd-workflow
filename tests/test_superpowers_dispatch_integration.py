#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""End-to-end integration test: claude CLI subprocess round-trip.

Skipped automatically when `claude` is not on PATH so CI and local
environments without the CLI stay green.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

_CLAUDE_PATH = shutil.which("claude")


@pytest.mark.skipif(
    _CLAUDE_PATH is None,
    reason="claude CLI not installed; integration test skipped",
)
def test_claude_cli_version_invocation() -> None:
    """Invoke ``claude --version`` and assert a non-empty stdout + exit 0.

    Cheap enough to run on every ``make verify`` when the CLI is present,
    and skipped otherwise. Replaces the iter-1 manual smoke-test acceptance
    item with a trackable automated check.
    """
    assert _CLAUDE_PATH is not None  # skipif guarantees this; assertion for mypy
    result = subprocess.run(
        [_CLAUDE_PATH, "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, (
        f"claude --version failed: rc={result.returncode} stderr={result.stderr!r}"
    )
    assert result.stdout.strip(), "claude --version produced empty stdout"
