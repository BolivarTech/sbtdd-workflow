#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.1 — DAG parser for plan-tdd.md.

Parses planning/claude-plan-tdd.md task blocks + dependency markers
to build a directed acyclic graph used by `parallel_dispatcher.py`
for batch dispatch.

Public API:
    parse_plan(plan_path: Path) -> TaskGraph
    class Task (dataclass, frozen)
    class TaskGraph (with .tasks, .edges, .antichains())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from errors import ValidationError

# Match `### Task N: title` or `### Task N title`, capturing the id and title.
_TASK_HEADER_RE = re.compile(r"^### Task (\d+)(?::|\s)\s*(.*)$", re.MULTILINE)
_FILES_BLOCK_RE = re.compile(
    r"^\*\*Files:\*\*\s*\n((?:^\s*-\s+(?:Create|Modify|Test)\s*:\s*[`\S].+\n?)+)",
    re.MULTILINE,
)
_FILE_LINE_RE = re.compile(
    r"^\s*-\s+(?:Create|Modify|Test)\s*:\s*`?([^`\s]+)`?",
    re.MULTILINE,
)
_DEPENDS_ON_RE = re.compile(r"^\*\*Depends on\*\*\s*:\s*Task\s+(\d+)\s*$", re.MULTILINE)
_ADD_BLOCKED_BY_RE = re.compile(r"^\*\*addBlockedBy\*\*\s*:\s*\[(.+?)\]\s*$", re.MULTILINE)
_TASK_REF_RE = re.compile(r"Task\s+(\d+)")
_CODE_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True)
class Task:
    """One task entry from the plan.

    Attributes:
        id: Task numeric id as string (e.g. ``"6"``).
        title: Human-readable title from the ``### Task N:`` header.
        files: Frozen set of file paths declared under ``**Files:**`` block.
    """

    id: str
    title: str
    files: frozenset[str] = field(default_factory=frozenset)


@dataclass
class TaskGraph:
    """Directed acyclic graph of plan tasks.

    Attributes:
        tasks: Mapping of task_id -> Task dataclass.
        edges: Mapping of task_id -> set of task_ids it depends on
            (predecessors). edges[X] = {A, B} means X depends on A AND B,
            so A + B must complete before X.
    """

    tasks: dict[str, Task] = field(default_factory=dict)
    edges: dict[str, set[str]] = field(default_factory=dict)

    def antichains(self) -> list[set[str]]:
        """Return ordered list of maximal antichains (parallel batches).

        First antichain contains tasks with no dependencies. Subsequent
        antichains contain tasks whose dependencies all appear in
        prior antichains. Output respects ONLY explicit dependencies;
        file-surface collision detection is a separate step in
        ``parallel_dispatcher.partition_by_collision``.

        Returns:
            List of sets; each set is a parallel batch (in plan order).

        Raises:
            ValidationError: If antichain partition stalls (residual
                cycle slipped past ``_detect_cycle``; defensive).
        """
        result: list[set[str]] = []
        completed: set[str] = set()
        remaining = set(self.tasks.keys())
        while remaining:
            batch = {tid for tid in remaining if self.edges.get(tid, set()) <= completed}
            if not batch:
                # Should not happen if cycle check passed; defensive
                raise ValidationError(
                    f"Antichain partition stalled; possible cycle in remaining: {remaining}"
                )
            result.append(batch)
            completed |= batch
            remaining -= batch
        return result


def _strip_code_fences(plan_text: str) -> str:
    """Replace markdown code-fenced regions with blank lines.

    Per iter 1 triage WARNING #3+#15 + iter 2 verification: ``### Task N:``
    headers inside code fences are EXAMPLES (e.g., writing-plans extension
    template) and MUST NOT pollute the graph as phantom tasks. Replace
    fenced regions with the same number of blank lines so byte offsets
    used by downstream regexes remain stable.

    Args:
        plan_text: Raw plan markdown.

    Returns:
        Plan markdown with all triple-backtick fenced regions replaced
        by newlines preserving line count.
    """

    def _replace(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")

    return _CODE_FENCE_RE.sub(_replace, plan_text)


def _split_task_blocks(plan_text: str) -> list[tuple[str, str, str]]:
    """Split plan text into ``(task_id, title, body)`` tuples.

    Returns one entry per ``### Task N:`` block, with body containing
    everything from the header up to (but not including) the next
    ``### Task N:`` header or end-of-file. Code-fenced regions are
    stripped before regex application (iter 1 triage WARNING #3+#15).
    """
    cleaned = _strip_code_fences(plan_text)
    headers = list(_TASK_HEADER_RE.finditer(cleaned))
    if not headers:
        return []
    blocks: list[tuple[str, str, str]] = []
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(cleaned)
        body = cleaned[start:end]
        blocks.append((m.group(1), m.group(2).strip(), body))
    return blocks


def _extract_files(task_text: str) -> frozenset[str]:
    """Extract ``Files:`` list from a task body.

    Args:
        task_text: Task body markdown (between two task headers).

    Returns:
        Frozen set of file paths; empty if no ``**Files:**`` block found.
    """
    match = _FILES_BLOCK_RE.search(task_text)
    if not match:
        return frozenset()
    block = match.group(0)
    return frozenset(_FILE_LINE_RE.findall(block))


def _extract_dependencies(task_text: str) -> set[str]:
    """Extract ``Depends on:`` + ``addBlockedBy:`` dependencies as task IDs.

    Args:
        task_text: Task body markdown.

    Returns:
        Set of task ids the current task depends on.
    """
    deps: set[str] = set()
    for m in _DEPENDS_ON_RE.finditer(task_text):
        deps.add(m.group(1))
    abb_match = _ADD_BLOCKED_BY_RE.search(task_text)
    if abb_match:
        for ref_match in _TASK_REF_RE.finditer(abb_match.group(1)):
            deps.add(ref_match.group(1))
    return deps


def _detect_cycle(edges: dict[str, set[str]]) -> list[str] | None:
    """Return cycle path if found, else ``None``.

    iter 1 triage WARNING #16 + iter 2 CRITICAL #1 fix: ITERATIVE
    Kahn's algorithm. Nodes whose dependencies are all completed get
    removed from the graph progressively; any node never removed
    participates in a cycle. Eliminates Python recursion limit failure
    mode for plans with > 1000 dependency depth.

    Args:
        edges: Mapping of task_id -> set of dep task_ids.

    Returns:
        Cycle path (list of task ids) if a cycle exists, else ``None``.
    """
    in_degree: dict[str, int] = {node: 0 for node in edges}
    for node, deps in edges.items():
        for dep in deps:
            in_degree.setdefault(dep, 0)
    for node, deps in edges.items():
        for _ in deps:
            in_degree[node] = in_degree.get(node, 0) + 1

    queue = [node for node, deg in in_degree.items() if deg == 0]
    completed: set[str] = set()
    while queue:
        node = queue.pop(0)
        completed.add(node)
        # When `node` completes, every dependent of `node` (i.e., every
        # X where `node` in edges[X]) loses one inbound edge.
        for x, deps in edges.items():
            if node in deps and x not in completed and x not in queue:
                in_degree[x] -= 1
                if in_degree[x] == 0:
                    queue.append(x)

    leftover = set(in_degree.keys()) - completed
    if not leftover:
        return None
    # Reconstruct cycle path by following edges from any leftover node.
    start = sorted(leftover)[0]
    path: list[str] = [start]
    seen: set[str] = {start}
    current = start
    while True:
        next_nodes = [d for d in edges.get(current, set()) if d in leftover]
        if not next_nodes:
            return path
        nxt = sorted(next_nodes)[0]
        if nxt in seen:
            cycle_start = path.index(nxt)
            return path[cycle_start:] + [nxt]
        path.append(nxt)
        seen.add(nxt)
        current = nxt


def parse_plan(plan_path: Path) -> TaskGraph:
    """Parse plan file into ``TaskGraph``.

    Args:
        plan_path: Path to ``planning/claude-plan-tdd.md``.

    Returns:
        TaskGraph with tasks + edges populated.

    Raises:
        ValidationError: If plan contains a dependency cycle OR
            references a non-existent task.
    """
    plan_text = plan_path.read_text(encoding="utf-8")
    blocks = _split_task_blocks(plan_text)
    tasks: dict[str, Task] = {}
    edges: dict[str, set[str]] = {}
    for tid, title, body in blocks:
        tasks[tid] = Task(id=tid, title=title, files=_extract_files(body))
        edges[tid] = _extract_dependencies(body)

    # Validate dependency targets exist
    all_ids = set(tasks.keys())
    for tid, deps in edges.items():
        unknown = deps - all_ids
        if unknown:
            raise ValidationError(f"Task {tid} depends on unknown task(s): {sorted(unknown)}")

    # Cycle detection (iterative; safe for deep chains)
    cycle = _detect_cycle(edges)
    if cycle is not None:
        raise ValidationError(f"Cyclic dependency detected: {' -> '.join(cycle)}")

    return TaskGraph(tasks=tasks, edges=edges)
