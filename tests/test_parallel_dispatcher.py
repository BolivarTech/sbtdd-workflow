#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.2 — parallel_dispatcher module tests.

Covers escenarios C-5 (file collision detection), C-6 (disjoint
passthrough), C-10 (deterministic ordering), C-11 (synthetic
concurrent state-file write race) from spec sec.4.3.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

import pytest

from dag_parser import Task, TaskGraph
from parallel_dispatcher import (
    _files_collide,
    partition_by_collision,
    partition_by_tracks,
)

# v1.0.4 iter-5 Loop 1 CRITICAL #2: ``partition_by_collision`` is
# deprecated. Tests still exercise it for regression coverage; suppress
# the DeprecationWarning module-wide so the legitimate coverage does not
# pollute pytest output. Production callers (none remain) would still
# see the warning at runtime via the default filter.
pytestmark = pytest.mark.filterwarnings(
    "ignore:parallel_dispatcher.partition_by_collision is deprecated:DeprecationWarning"
)


def _make_graph(tasks_with_files: dict[str, set[str]]) -> TaskGraph:
    tasks = {
        tid: Task(id=tid, title=f"Task {tid}", files=frozenset(files))
        for tid, files in tasks_with_files.items()
    }
    return TaskGraph(tasks=tasks, edges={tid: set() for tid in tasks})


def _make_graph_with_edges(
    tasks_with_files: dict[str, set[str]],
    edges: dict[str, set[str]],
) -> TaskGraph:
    """Helper: construct a TaskGraph with explicit edges."""
    tasks = {
        tid: Task(id=tid, title=f"Task {tid}", files=frozenset(files))
        for tid, files in tasks_with_files.items()
    }
    full_edges = {tid: edges.get(tid, set()) for tid in tasks}
    return TaskGraph(tasks=tasks, edges=full_edges)


def test_c5_collision_detection_shared_file() -> None:
    """C-5: tasks sharing a file collide."""
    graph = _make_graph({"1": {"a.py"}, "2": {"a.py"}})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is True


def test_c5_partition_collision_splits_batch() -> None:
    """C-5: collision-detected antichain splits into 2 sub-batches."""
    graph = _make_graph({"1": {"auto_cmd.py"}, "2": {"auto_cmd.py"}})
    batches = partition_by_collision({"1", "2"}, graph)
    # Two single-task batches (cannot run parallel)
    assert len(batches) == 2
    assert {"1"} in batches
    assert {"2"} in batches


def test_c6_disjoint_files_pass_through() -> None:
    """C-6: tasks with disjoint files yield single batch."""
    graph = _make_graph({"1": {"a.py"}, "2": {"b.py"}})
    batches = partition_by_collision({"1", "2"}, graph)
    assert batches == [{"1", "2"}]


def test_c6_no_files_pass_through() -> None:
    """C-6: tasks without files (doc-only) pass through as single batch."""
    graph = _make_graph({"1": set(), "2": set()})
    batches = partition_by_collision({"1", "2"}, graph)
    assert batches == [{"1", "2"}]


def test_c5_three_way_collision() -> None:
    """C-5: three tasks pairwise-colliding split fully."""
    graph = _make_graph(
        {
            "1": {"a.py"},
            "2": {"a.py"},
            "3": {"a.py"},
        }
    )
    batches = partition_by_collision({"1", "2", "3"}, graph)
    assert len(batches) == 3
    assert all(len(b) == 1 for b in batches)


def test_c6_partial_collision_groups_deterministic() -> None:
    """C-6 + C-10 (iter 1 triage): 1+2 collide on a.py; 3 disjoint.

    Ascending-id sort + greedy first-fit → exact batches [{1, 3}, {2}].
    """
    graph = _make_graph(
        {
            "1": {"a.py"},
            "2": {"a.py"},
            "3": {"b.py"},
        }
    )
    batches = partition_by_collision({"1", "2", "3"}, graph)
    # Deterministic: sorted ids → "1" packed first with disjoint "3";
    # "2" left over (collides with "1" on a.py).
    assert batches == [{"1", "3"}, {"2"}]


def test_c10_partition_deterministic_across_invocations() -> None:
    """C-10 iter 1 triage: same input MUST produce same output across calls.

    Eliminates Python set iteration order dependency.
    """
    graph = _make_graph(
        {
            "1": {"x.py"},
            "2": {"y.py"},
            "3": {"x.py"},
            "4": {"z.py"},
        }
    )
    # Run twice; results must be byte-identical
    batches_1 = partition_by_collision({"1", "2", "3", "4"}, graph)
    batches_2 = partition_by_collision({"1", "2", "3", "4"}, graph)
    assert batches_1 == batches_2
    # Pin canonical ordering: ascending-id greedy fit
    assert batches_1 == [{"1", "2", "4"}, {"3"}]


def _writer_for_concurrent_test(
    state_path_str: str,
    task_id: str,
    barrier: object,
) -> None:
    """Top-level helper for multiprocessing.Process spawn (must be picklable).

    Imports state_file inside the function so the child process picks
    up the same sys.path setup as conftest in the parent.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))
    from state_file import SessionState, save  # noqa: WPS433 - intentional in-fn import

    barrier.wait()  # type: ignore[attr-defined]
    state = SessionState(
        plan_path="planning/claude-plan-tdd.md",
        current_task_id=task_id,
        current_task_title=f"Task {task_id}",
        current_phase="green",
        phase_started_at_commit="abc123",
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at=None,
    )
    save(state, Path(state_path_str))


def test_c11_no_partial_writes_under_concurrent_replace(tmp_path: Path) -> None:
    """C-11 (renamed v1.0.4 Path 3 sub-issue 1, Mel WARNING — honest naming):
    no partial-merge JSON file under concurrent ``state_file.save`` calls.

    Two processes call ``state_file.save`` simultaneously against
    disjoint task IDs. Final file MUST parse as valid JSON and match
    one of the two writers' final states (never partial-merge nor
    corrupt JSON). Relies on ``state_file.save`` atomic-write semantics
    (write-temp + os.replace), which is the canonical OS-level
    serialization strategy adopted by this project.

    NOTE on naming: the prior name implied this test exercises a true
    race condition with non-trivial concurrent modification semantics.
    In reality, the OS-level atomic-rename guarantees mean "last writer
    wins" deterministically; this test merely validates that no
    intermediate write is observable. Renamed for honest description.
    """
    state_path = tmp_path / "session-state.json"
    # Initialize with a baseline valid state file
    initial = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "0",
        "current_task_title": "baseline",
        "current_phase": "red",
        "phase_started_at_commit": "deadbeef",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": None,
    }
    state_path.write_text(json.dumps(initial), encoding="utf-8")

    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    procs = [
        ctx.Process(
            target=_writer_for_concurrent_test,
            args=(str(state_path), tid, barrier),
        )
        for tid in ("5", "6")
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join(timeout=30)

    for p in procs:
        assert not p.is_alive(), f"writer process {p.pid} did not terminate"

    text = state_path.read_text(encoding="utf-8")
    parsed = json.loads(text)  # must NOT raise — file must parse cleanly
    # Final state MUST be one of the two writers' states (never partial)
    assert parsed.get("current_task_id") in {"5", "6"}
    assert parsed.get("current_phase") == "green"


def test_c5_singleton_passthrough() -> None:
    """C-5/C-6: singleton antichain returns single-task batch."""
    graph = _make_graph({"1": {"a.py"}})
    batches = partition_by_collision({"1"}, graph)
    assert batches == [{"1"}]


def test_c5_files_collide_helper_disjoint() -> None:
    """C-5: ``_files_collide`` returns False for disjoint sets."""
    graph = _make_graph({"1": {"a.py"}, "2": {"b.py"}})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is False


def test_c5_files_collide_helper_empty() -> None:
    """C-5: ``_files_collide`` returns False for empty file sets."""
    graph = _make_graph({"1": set(), "2": set()})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is False


def test_partition_empty_antichain_returns_empty_list() -> None:
    """Defensive: empty antichain produces no sub-batches."""
    graph = _make_graph({"1": {"a.py"}})
    batches = partition_by_collision(set(), graph)
    assert batches == []


# ---------------------------------------------------------------------------
# v1.0.4 Path 3 -- partition_by_tracks: track-based weakly-connected
# components in (dep edges UNION file-conflict edges) graph. Each track is
# an ordered list of task IDs that must serialize within the track; tracks
# between each other are file-disjoint AND dep-disjoint, so they may be
# dispatched in parallel as N concurrent subprocess workers.
# ---------------------------------------------------------------------------


def test_path3_partition_by_tracks_two_disjoint_tracks() -> None:
    """Path 3: two file-disjoint, dep-disjoint groups produce 2 tracks.

    Tasks 1+2 share file a.py (collide → same track).
    Tasks 3+4 share file b.py (collide → same track).
    No cross-track files or deps → 2 separate tracks.
    """
    graph = _make_graph(
        {
            "1": {"a.py"},
            "2": {"a.py"},
            "3": {"b.py"},
            "4": {"b.py"},
        }
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 2
    track_sets = [set(t) for t in tracks]
    assert {"1", "2"} in track_sets
    assert {"3", "4"} in track_sets


def test_path3_partition_by_tracks_dependency_creates_track() -> None:
    """Path 3: dep edge alone (no shared file) puts tasks in same track.

    Track partition uses (deps UNION file-conflicts) graph. Two tasks
    sharing a dep-edge are weakly connected → same track.
    """
    graph = _make_graph_with_edges(
        tasks_with_files={
            "1": {"x.py"},
            "2": {"y.py"},  # different file
        },
        edges={"2": {"1"}},  # 2 depends on 1
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 1
    assert set(tracks[0]) == {"1", "2"}


def test_path3_partition_by_tracks_topo_order_within_track() -> None:
    """Path 3: tasks within a track sorted topologically (deps first)."""
    graph = _make_graph_with_edges(
        tasks_with_files={
            "A": {"a.py"},
            "B": {"b.py"},
            "C": {"c.py"},
        },
        edges={"B": {"A"}, "C": {"B"}},  # A < B < C
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 1
    # Topological order: A before B before C
    assert tracks[0] == ["A", "B", "C"]


def test_path3_partition_by_tracks_v104_plan_shape() -> None:
    """Path 3: example matching v1.0.4 plan -- 2 tracks of 4+3 tasks.

    T1+T3+T4+T5 share superpowers_dispatch.py (Track Alpha analog).
    T6+T7+T8 share dag_parser/parallel_dispatcher/auto_cmd (Track Beta
    analog with sequential deps T6 < T7 < T8).
    """
    graph = _make_graph_with_edges(
        tasks_with_files={
            "T1": {"superpowers_dispatch.py"},
            "T3": {"superpowers_dispatch.py"},
            "T4": {"superpowers_dispatch.py"},
            "T5": {"superpowers_dispatch.py"},
            "T6": {"dag_parser.py"},
            "T7": {"parallel_dispatcher.py"},
            "T8": {"auto_cmd.py"},
        },
        edges={"T7": {"T6"}, "T8": {"T7"}},
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 2
    track_sets = [set(t) for t in tracks]
    assert {"T1", "T3", "T4", "T5"} in track_sets
    assert {"T6", "T7", "T8"} in track_sets
    # Track Beta must be topologically ordered T6 < T7 < T8
    beta = next(t for t in tracks if "T6" in t)
    assert beta == ["T6", "T7", "T8"]


def test_path3_partition_by_tracks_all_independent_n_tracks() -> None:
    """Path 3: N file-disjoint, dep-disjoint tasks → N single-task tracks."""
    graph = _make_graph(
        {
            "1": {"a.py"},
            "2": {"b.py"},
            "3": {"c.py"},
        }
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 3
    assert all(len(t) == 1 for t in tracks)
    track_sets = [set(t) for t in tracks]
    assert {"1"} in track_sets
    assert {"2"} in track_sets
    assert {"3"} in track_sets


def test_path3_partition_by_tracks_empty_graph_returns_empty() -> None:
    """Defensive: empty graph → no tracks."""
    graph = _make_graph({})
    tracks = partition_by_tracks(graph)
    assert tracks == []


def test_path3_partition_by_tracks_deterministic_across_invocations() -> None:
    """Path 3: same graph → byte-identical partition across calls."""
    graph = _make_graph(
        {
            "1": {"a.py"},
            "2": {"b.py"},
            "3": {"a.py"},
            "4": {"c.py"},
        }
    )
    t1 = partition_by_tracks(graph)
    t2 = partition_by_tracks(graph)
    assert t1 == t2


def test_path3_partition_by_tracks_singleton_no_files_no_deps() -> None:
    """Defensive: single doc-only task → 1 track with 1 task."""
    graph = _make_graph({"1": set()})
    tracks = partition_by_tracks(graph)
    assert tracks == [["1"]]


def test_path3_partition_by_tracks_chain_creates_single_track() -> None:
    """Path 3: linear dependency chain → single track in topo order."""
    graph = _make_graph_with_edges(
        tasks_with_files={
            "1": {"a.py"},
            "2": {"b.py"},
            "3": {"c.py"},
            "4": {"d.py"},
        },
        edges={"2": {"1"}, "3": {"2"}, "4": {"3"}},
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 1
    assert tracks[0] == ["1", "2", "3", "4"]


def test_path3_partition_by_tracks_file_conflict_unifies_unrelated_tasks() -> None:
    """Path 3: tasks with no deps but shared file → same track (file conflict
    forces serialization)."""
    graph = _make_graph(
        {
            "X": {"shared.py"},
            "Y": {"shared.py"},  # file conflict with X
        }
    )
    tracks = partition_by_tracks(graph)
    assert len(tracks) == 1
    assert set(tracks[0]) == {"X", "Y"}
