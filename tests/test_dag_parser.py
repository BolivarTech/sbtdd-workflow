#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.1 — dag_parser module tests.

Covers escenarios C-1 (Task block parsing), C-2 (addBlockedBy
extraction), C-3 (cycle detection), C-4 (antichain identification)
from spec sec.4.3.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from dag_parser import Task, TaskGraph, parse_plan
from errors import ValidationError


@pytest.fixture
def simple_plan(tmp_path: Path) -> Path:
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            # Plan

            ### Task 1: Foo

            **Files:**
            - Modify: `src/foo.py`

            ### Task 2: Bar

            **Files:**
            - Modify: `src/bar.py`

            **Depends on**: Task 1

            ### Task 3: Baz

            **Files:**
            - Modify: `src/baz.py`
            """
        )
    )
    return plan


@pytest.fixture
def cyclic_plan(tmp_path: Path) -> Path:
    plan = tmp_path / "cyclic.md"
    plan.write_text(
        textwrap.dedent(
            """\
            # Plan

            ### Task 1: Foo

            **Files:**
            - Modify: `src/foo.py`

            **Depends on**: Task 2

            ### Task 2: Bar

            **Files:**
            - Modify: `src/bar.py`

            **Depends on**: Task 1
            """
        )
    )
    return plan


def test_c1_parses_task_blocks(simple_plan: Path) -> None:
    """C-1: dag_parser parses ### Task N: blocks into TaskGraph."""
    graph = parse_plan(simple_plan)
    assert isinstance(graph, TaskGraph)
    assert set(graph.tasks.keys()) == {"1", "2", "3"}
    assert graph.tasks["1"].title == "Foo"
    assert graph.tasks["2"].title == "Bar"
    assert graph.tasks["3"].title == "Baz"


def test_c1_extracts_files_lists(simple_plan: Path) -> None:
    """C-1: each Task has Files list extracted."""
    graph = parse_plan(simple_plan)
    assert "src/foo.py" in graph.tasks["1"].files
    assert "src/bar.py" in graph.tasks["2"].files
    assert "src/baz.py" in graph.tasks["3"].files


def test_c2_extracts_depends_on_dependencies(simple_plan: Path) -> None:
    """C-2: 'Depends on: Task M' extracted as edge."""
    graph = parse_plan(simple_plan)
    assert graph.edges.get("2", set()) == {"1"}
    assert graph.edges.get("1", set()) == set()
    assert graph.edges.get("3", set()) == set()


def test_c2_extracts_addblockedby_dependencies(tmp_path: Path) -> None:
    """C-2: 'addBlockedBy: [Task M, Task K]' extracted as edges."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            ### Task 2: B

            **Files:**
            - Modify: `b.py`

            **addBlockedBy**: [Task 1]

            ### Task 3: C

            **Files:**
            - Modify: `c.py`

            **addBlockedBy**: [Task 1, Task 2]
            """
        )
    )
    graph = parse_plan(plan)
    assert graph.edges["2"] == {"1"}
    assert graph.edges["3"] == {"1", "2"}


def test_c3_detects_cycle(cyclic_plan: Path) -> None:
    """C-3: cyclic dependencies raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(cyclic_plan)
    msg = str(exc_info.value).lower()
    assert "cycle" in msg or "cyclic" in msg


def test_c4_antichain_identification(simple_plan: Path) -> None:
    """C-4: antichains() returns ordered list of parallelizable batches."""
    graph = parse_plan(simple_plan)
    chains = graph.antichains()
    assert len(chains) == 2
    # First antichain: tasks with no dependencies (1 + 3)
    assert chains[0] == {"1", "3"}
    # Second antichain: tasks unblocked after first batch (2)
    assert chains[1] == {"2"}


def test_c4_antichain_single_task_per_batch_when_chain(tmp_path: Path) -> None:
    """C-4: linear chain produces single-task antichains."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            ### Task 2: B

            **Files:**
            - Modify: `b.py`

            **Depends on**: Task 1

            ### Task 3: C

            **Files:**
            - Modify: `c.py`

            **Depends on**: Task 2
            """
        )
    )
    graph = parse_plan(plan)
    chains = graph.antichains()
    assert chains == [{"1"}, {"2"}, {"3"}]


def test_c4_antichain_all_independent_single_batch(tmp_path: Path) -> None:
    """C-4: fully independent tasks produce single antichain."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            ### Task 2: B

            **Files:**
            - Modify: `b.py`

            ### Task 3: C

            **Files:**
            - Modify: `c.py`
            """
        )
    )
    graph = parse_plan(plan)
    chains = graph.antichains()
    assert chains == [{"1", "2", "3"}]


def test_c1_empty_plan_returns_empty_graph(tmp_path: Path) -> None:
    """Defensive: plan with no Task blocks returns empty graph."""
    plan = tmp_path / "empty.md"
    plan.write_text("# Plan\n\nNo tasks here.\n")
    graph = parse_plan(plan)
    assert graph.tasks == {}
    assert graph.antichains() == []


def test_c1_task_without_files_section_parses(tmp_path: Path) -> None:
    """Defensive: task without Files: section parses with empty files set."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: Doc-only

            Some description without Files block.
            """
        )
    )
    graph = parse_plan(plan)
    assert "1" in graph.tasks
    assert graph.tasks["1"].files == frozenset()


def test_c2_unknown_dependency_target_raises(tmp_path: Path) -> None:
    """Defensive: dependency on non-existent task raises ValidationError."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            **Depends on**: Task 999
            """
        )
    )
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(plan)
    msg = str(exc_info.value).lower()
    assert "999" in msg or "unknown" in msg


def test_c1_code_fence_aware_skips_phantom_headers(tmp_path: Path) -> None:
    """C-1 iter 1 triage WARNING (melchior + caspar): code-fenced ### Task N:
    examples MUST NOT pollute graph as phantom tasks."""
    plan = tmp_path / "plan.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: Real

            **Files:**
            - Modify: `real.py`

            Example template embedded in plan:

            ```markdown
            ### Task 99: Phantom

            **Files:**
            - Modify: `phantom.py`
            ```

            ### Task 2: AlsoReal

            **Files:**
            - Modify: `also_real.py`
            """
        )
    )
    graph = parse_plan(plan)
    # Only T1 + T2 — phantom T99 inside fence MUST be skipped
    assert set(graph.tasks.keys()) == {"1", "2"}
    assert "99" not in graph.tasks


def test_c3_iterative_cycle_detection_no_recursion_limit(tmp_path: Path) -> None:
    """C-3 iter 1 triage WARNING (caspar): cycle detection iterative — no
    recursion limit failure for deep dependency chains."""
    plan_lines = ["# Deep chain plan"]
    # 1500 sequential tasks: each depends on the previous
    for i in range(1, 1501):
        plan_lines.append(f"\n### Task {i}: T{i}")
        plan_lines.append("\n**Files:**")
        plan_lines.append(f"- Modify: `t{i}.py`")
        if i > 1:
            plan_lines.append(f"\n**Depends on**: Task {i - 1}")
    plan = tmp_path / "deep.md"
    plan.write_text("\n".join(plan_lines))
    # Recursive DFS would hit Python recursion limit (default 1000).
    # Iterative algorithm must succeed without RecursionError.
    graph = parse_plan(plan)
    assert len(graph.tasks) == 1500
    chains = graph.antichains()
    # Linear chain: 1500 antichains, one task each
    assert len(chains) == 1500


def test_c3_iterative_cycle_detection_self_loop(tmp_path: Path) -> None:
    """C-3 iter 1 triage: self-loop is a cycle — iterative algorithm detects."""
    plan = tmp_path / "self.md"
    plan.write_text(
        textwrap.dedent(
            """\
            ### Task 1: SelfLoop

            **Files:**
            - Modify: `self.py`

            **Depends on**: Task 1
            """
        )
    )
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(plan)
    msg = str(exc_info.value).lower()
    assert "cycle" in msg or "cyclic" in msg


def test_task_dataclass_is_immutable() -> None:
    """Defensive: Task is frozen dataclass."""
    t = Task(id="1", title="x", files=frozenset({"a.py"}))
    with pytest.raises((AttributeError, Exception)):
        t.title = "modified"  # type: ignore[misc]
