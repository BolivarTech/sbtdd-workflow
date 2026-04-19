#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for drift module — DriftReport + _evaluate_drift + detect_drift."""

from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError


def test_drift_report_is_frozen():
    from drift import DriftReport

    report = DriftReport(
        state_value="green",
        git_value="refactor:",
        plan_value="[ ]",
        reason="phase/prefix mismatch",
    )
    with pytest.raises(FrozenInstanceError):
        report.state_value = "red"  # type: ignore[misc]


def test_drift_report_fields():
    from drift import DriftReport

    fields = set(DriftReport.__dataclass_fields__)
    assert fields == {"state_value", "git_value", "plan_value", "reason"}
