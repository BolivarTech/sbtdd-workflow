#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.2 — Parallel task dispatcher.

Coordinates concurrent task execution within an antichain
(dependency-free batch from ``dag_parser.TaskGraph.antichains()``),
splitting the antichain into file-surface-disjoint sub-batches to
avoid same-worktree write conflicts.

v1.0.4 Path 3 (track-based dispatch) adds :func:`partition_by_tracks`,
a different partitioning strategy: it groups tasks into TRACKS where
each track is a weakly-connected component in the union graph
(dep edges UNION file-conflict edges). Tracks between each other are
file-disjoint AND dep-disjoint; within a track, tasks must serialize
(internal deps OR conflicts). Used by ``auto_cmd._dispatch_tracks_concurrent``
to dispatch one subprocess worker per track.

Public API:
    partition_by_collision(antichain, graph) -> list[set[str]]
    partition_by_tracks(graph) -> list[list[str]]

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

Note on track partitioning: ``partition_by_tracks`` uses union-find
to identify weakly-connected components in O((V+E)*α(V)) time. Tasks
within a track are sorted topologically (Kahn's algorithm) so internal
dependencies are honored when a worker processes the track sequentially.
Determinism is enforced by sorting task ids ascending in tie-break.
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


# ---------------------------------------------------------------------------
# v1.0.4 Path 3 -- track-based partitioning (weakly-connected components in
# (dep edges UNION file-conflict edges) graph). Each track is a sequence of
# task IDs that must serialize within the track (internal dep OR conflict);
# tracks between each other are file-disjoint AND dep-disjoint, so they may
# be dispatched as N concurrent subprocess workers (one per track).
# ---------------------------------------------------------------------------


class _UnionFind:
    """Minimal union-find structure for connected-components partitioning.

    Path compression + union by rank give O(α(V)) amortized per op.
    """

    def __init__(self, elements: list[str]) -> None:
        self._parent: dict[str, str] = {e: e for e in elements}
        self._rank: dict[str, int] = {e: 0 for e in elements}

    def find(self, x: str) -> str:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        # Path compression
        cur = x
        while self._parent[cur] != root:
            nxt = self._parent[cur]
            self._parent[cur] = root
            cur = nxt
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        # Union by rank (deterministic tie-break: smaller id wins).
        if self._rank[ra] < self._rank[rb]:
            self._parent[ra] = rb
        elif self._rank[ra] > self._rank[rb]:
            self._parent[rb] = ra
        else:
            # Same rank: pick smaller id as new root for determinism.
            if ra < rb:
                self._parent[rb] = ra
                self._rank[ra] += 1
            else:
                self._parent[ra] = rb
                self._rank[rb] += 1


def _topo_sort_within_track(track_ids: set[str], graph: TaskGraph) -> list[str]:
    """Topologically sort task ids inside one track (deps before dependents).

    Uses Kahn's algorithm restricted to the track's task set so dependencies
    OUTSIDE the track (which by construction shouldn't exist if the track
    partition is correct) are ignored gracefully. Ties broken by ascending
    task id for determinism.

    Args:
        track_ids: Set of task ids forming a single track.
        graph: The full ``TaskGraph`` (used for ``edges`` lookup).

    Returns:
        List of task ids in topological order. For tasks with no internal
        dependencies, ascending id order is used.
    """
    # Build restricted in-degree map (edges only between track members).
    in_degree: dict[str, int] = {tid: 0 for tid in track_ids}
    for tid in track_ids:
        for dep in graph.edges.get(tid, set()):
            if dep in track_ids:
                in_degree[tid] += 1
    # Kahn's: start with zero in-degree nodes; pick smallest id at each step.
    result: list[str] = []
    available = sorted(t for t, d in in_degree.items() if d == 0)
    while available:
        # Pop smallest-id available node (deterministic tie-break).
        node = available.pop(0)
        result.append(node)
        # Decrement in-degree of all dependents of `node` within track.
        new_zero: list[str] = []
        for tid in track_ids:
            if node in graph.edges.get(tid, set()) and tid not in result:
                in_degree[tid] -= 1
                if in_degree[tid] == 0:
                    new_zero.append(tid)
        # Insert sorted to preserve ascending-id determinism.
        for nz in new_zero:
            # Bisect-insert; track sizes are tiny so list ops are fine.
            idx = 0
            while idx < len(available) and available[idx] < nz:
                idx += 1
            available.insert(idx, nz)
    return result


def partition_by_tracks(graph: TaskGraph) -> list[list[str]]:
    """Partition tasks into tracks (weakly-connected components).

    Each track is an ordered list of task ids that must serialize within
    the track because of either:

    - Internal dependencies: ``graph.edges[X]`` contains a node in the
      same track; or
    - File conflicts: another task in the same track shares one or more
      files in ``Task.files``.

    Tracks between each other are file-disjoint AND dep-disjoint, so they
    may be dispatched as N concurrent subprocess workers (one per track)
    by :func:`auto_cmd._dispatch_tracks_concurrent`.

    Algorithm:
        1. Build undirected union-find over all task ids.
        2. For each dependency edge (X depends on Y): union(X, Y).
        3. For each pair (X, Y) sharing one or more files: union(X, Y).
        4. Group task ids by their union-find root → one group per track.
        5. Sort task ids within each track topologically (Kahn).
        6. Sort tracks deterministically by smallest-id-in-track ascending.

    Args:
        graph: ``TaskGraph`` from :func:`dag_parser.parse_plan`.

    Returns:
        List of tracks. Each track is a ``list[str]`` of task ids in
        execution order (deps first). Track-list order is deterministic
        (ascending by smallest member id). Order BETWEEN tracks does not
        matter for correctness — they can run in any order or in parallel.
    """
    if not graph.tasks:
        return []
    all_ids = sorted(graph.tasks.keys())
    uf = _UnionFind(all_ids)
    # Step 1: union over dependency edges (undirected for component
    # purposes — direction matters only for topo-sort within a track).
    for tid, deps in graph.edges.items():
        for dep in deps:
            if dep in graph.tasks:  # defensive: skip dangling refs
                uf.union(tid, dep)
    # Step 2: union over file-conflict edges (any two tasks sharing
    # at least one file are weakly connected). O(n^2) — fine for n <= ~50
    # which covers any realistic plan.
    for i, a in enumerate(all_ids):
        files_a = graph.tasks[a].files
        if not files_a:
            continue
        for b in all_ids[i + 1 :]:
            files_b = graph.tasks[b].files
            if files_b and (files_a & files_b):
                uf.union(a, b)
    # Step 3: group by root.
    groups: dict[str, set[str]] = {}
    for tid in all_ids:
        root = uf.find(tid)
        groups.setdefault(root, set()).add(tid)
    # Step 4: topo-sort within each track + emit deterministic order.
    tracks: list[list[str]] = []
    for root in groups:
        sorted_track = _topo_sort_within_track(groups[root], graph)
        tracks.append(sorted_track)
    # Step 5: order tracks by ascending min-id (deterministic between-track
    # order). Algorithm correctness does not depend on this; tests + audit
    # readability do.
    tracks.sort(key=lambda t: t[0] if t else "")
    return tracks
