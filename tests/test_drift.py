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


def test_detect_drift_phase_red_with_test_commit():
    """current_phase=red + HEAD=test: is drift (close ran, state not advanced)."""
    from drift import _evaluate_drift, DriftReport

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="test",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "red"
    assert report.git_value == "test"


def test_detect_drift_phase_green_with_feat_commit():
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="green",
        last_commit_prefix="feat",
        plan_task_state="[ ]",
    )
    assert report is not None
    assert "feat" in report.git_value


def test_detect_drift_phase_refactor_with_refactor_commit():
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="refactor",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_scenario_4_green_with_refactor_commit():
    """Scenario 4 (spec-behavior.md sec.4.2 + CLAUDE.md sec.2.1) -- canonical.

    state=green but HEAD=refactor: means a later phase's close committed
    without the state file advancing through green.
    """
    from drift import _evaluate_drift, DriftReport

    report = _evaluate_drift(
        current_phase="green",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert isinstance(report, DriftReport)
    assert report.state_value == "green"
    assert report.git_value == "refactor"
    assert "refactor" in report.reason


def test_detect_drift_scenario_4_red_with_feat_commit():
    """Phase-ordering inversion: state=red but HEAD=feat: (green close landed)."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="feat",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_red_with_refactor_commit():
    """Phase-ordering inversion: state=red but HEAD=refactor: (refactor close landed)."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="refactor",
        plan_task_state="[ ]",
    )
    assert report is not None


def test_detect_drift_consistent_returns_none():
    """current_phase=red + HEAD=chore: (previous task close) is consistent."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="red",
        last_commit_prefix="chore",
        plan_task_state="[ ]",
    )
    assert report is None


def test_detect_drift_done_phase_returns_none():
    """Phase=done is terminal -- no drift regardless of commit prefix."""
    from drift import _evaluate_drift

    report = _evaluate_drift(
        current_phase="done",
        last_commit_prefix="refactor",
        plan_task_state="[x]",
    )
    assert report is None
