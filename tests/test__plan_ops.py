# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for shared plan-edit helpers (_plan_ops.py)."""

from __future__ import annotations

import pytest


def test_plan_ops_module_importable() -> None:
    import _plan_ops

    assert hasattr(_plan_ops, "flip_task_checkboxes")
    assert hasattr(_plan_ops, "next_task")
    assert hasattr(_plan_ops, "first_open_task")


def test_flip_task_checkboxes_flips_target_task_only() -> None:
    import _plan_ops

    plan = "### Task 1: First\n- [ ] step a\n- [ ] step b\n### Task 2: Second\n- [ ] step c\n"
    out = _plan_ops.flip_task_checkboxes(plan, "1")
    assert "### Task 1: First\n- [x] step a\n- [x] step b\n" in out
    assert "### Task 2: Second\n- [ ] step c\n" in out


def test_flip_task_checkboxes_raises_on_missing_task() -> None:
    import _plan_ops
    from errors import PreconditionError

    with pytest.raises(PreconditionError):
        _plan_ops.flip_task_checkboxes("### Task 1: x\n- [ ] a\n", "99")


def test_next_task_returns_next_open_after_current() -> None:
    import _plan_ops

    plan = "### Task 1: First\n- [x] a\n### Task 2: Second\n- [ ] b\n### Task 3: Third\n- [ ] c\n"
    assert _plan_ops.next_task(plan, "1") == ("2", "Second")


def test_next_task_skips_fully_closed_task() -> None:
    import _plan_ops

    plan = "### Task 1: First\n- [x] a\n### Task 2: Second\n- [x] b\n### Task 3: Third\n- [ ] c\n"
    assert _plan_ops.next_task(plan, "1") == ("3", "Third")


def test_next_task_returns_none_when_plan_complete() -> None:
    import _plan_ops

    plan = "### Task 1: First\n- [x] a\n### Task 2: Second\n- [x] b\n"
    assert _plan_ops.next_task(plan, "1") == (None, None)


def test_first_open_task_returns_first_with_open_checkbox() -> None:
    import _plan_ops

    plan = "### Task 1: First\n- [x] a\n### Task 2: Second\n- [ ] b\n"
    assert _plan_ops.first_open_task(plan) == ("2", "Second")


def test_first_open_task_raises_when_none_open() -> None:
    import _plan_ops
    from errors import PreconditionError

    plan = "### Task 1: First\n- [x] a\n"
    with pytest.raises(PreconditionError):
        _plan_ops.first_open_task(plan)
