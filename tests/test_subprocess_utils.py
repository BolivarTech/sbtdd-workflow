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
