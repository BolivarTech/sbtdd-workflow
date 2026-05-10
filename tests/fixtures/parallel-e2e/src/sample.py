#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""Sample module for v1.0.7 A3 parallel e2e fixture.

Provides a trivial pure function exercised by ``tests/test_sample.py``
so the fixture project's ``pytest`` / ``ruff`` / ``mypy`` chain has
real (non-empty) targets during ``auto --parallel`` worker close-phase
execution.
"""

from __future__ import annotations


def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Args:
        a: First addend.
        b: Second addend.

    Returns:
        Integer sum ``a + b``.
    """
    return a + b
