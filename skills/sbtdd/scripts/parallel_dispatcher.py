#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.2 — Parallel task dispatcher.

Coordinates concurrent task execution within an antichain
(dependency-free batch from ``dag_parser.TaskGraph.antichains()``),
splitting the antichain into file-surface-disjoint sub-batches to
avoid same-worktree write conflicts.

Public API:
    partition_by_collision(antichain, graph) -> list[set[str]]

Note on concurrency-safety: state-file race-condition safety is
delegated to the canonical project mechanism — ``state_file.save``
performs a write-temp + ``os.replace`` atomic swap, which is atomic on
both POSIX and Windows. No additional ``flock``/``msvcrt.locking``
wrapper is introduced here; relying on the OS-level rename is
simpler, cross-platform, and consistent with the existing project
conventions. Concurrent writers thus never produce a partial-merge
file: the last writer wins, and the file is always fully valid.

Note on greedy packing: ``partition_by_collision`` uses an O(n^2)
greedy first-fit algorithm. Optimal partitioning is equivalent to
graph coloring (NP-hard); the greedy approximation is acceptable
because typical antichains are small (n <= ~10 for plans we see in
practice). Determinism is enforced by sorting task ids ascending
before packing (iter 1 triage WARNING #7 + iter 2 CRITICAL #2 fix).
"""

from __future__ import annotations

from dag_parser import Task, TaskGraph


def _files_collide(task_a: Task, task_b: Task) -> bool:
    """Return ``True`` if two tasks share at least one file surface.

    Args:
        task_a: First task.
        task_b: Second task.

    Returns:
        ``True`` if ``task_a.files`` and ``task_b.files`` have any
        element in common; ``False`` otherwise (including when either
        set is empty).
    """
    if not task_a.files or not task_b.files:
        return False
    return bool(task_a.files & task_b.files)


def partition_by_collision(
    antichain: set[str],
    graph: TaskGraph,
) -> list[set[str]]:
    """Split a dependency-free antichain into surface-disjoint sub-batches.

    Two tasks can run in the same parallel batch only if their
    ``Files:`` lists are disjoint. This function greedy-packs tasks
    into sub-batches so that every task in a sub-batch is
    pairwise-disjoint with every other task in the same sub-batch.

    iter 1 triage WARNING #7 + iter 2 CRITICAL #2 fix: input task ids
    are SORTED ASCENDING before greedy first-fit packing, so output is
    deterministic regardless of Python set iteration order.

    Args:
        antichain: Set of task ids (output of
            ``TaskGraph.antichains()``).
        graph: The ``TaskGraph`` (used for ``Task`` lookup).

    Returns:
        List of sets; each set is a sub-batch where every task has
        disjoint file surfaces with every other task in the same
        sub-batch. Single-task sub-batches indicate the task collides
        with at least one other task in every other sub-batch and
        cannot share a batch under the greedy heuristic.
    """
    if not antichain:
        return []
    remaining: list[str] = sorted(antichain)  # iter 2 CRITICAL #2: deterministic
    sub_batches: list[set[str]] = []
    while remaining:
        head = remaining.pop(0)
        batch: set[str] = {head}
        merged_files: set[str] = set(graph.tasks[head].files)
        leftover: list[str] = []
        for tid in remaining:
            tid_files = graph.tasks[tid].files
            if not (tid_files & merged_files):
                batch.add(tid)
                merged_files |= tid_files
            else:
                leftover.append(tid)
        sub_batches.append(batch)
        remaining = leftover
    return sub_batches
