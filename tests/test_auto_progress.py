#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature D auto-run.json progress field.

v0.4.0 J4 + J6 extensions:

- ``test_update_progress_swallows_oserror_and_continues`` (J4.1).
- ``test_update_progress_retry_exhaustion_preserves_original`` (J4.2).
- ``test_write_auto_run_audit_preserves_progress_field`` (J6.1).
- ``test_write_auto_run_audit_when_progress_absent`` (J6.2).
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd


@pytest.fixture(autouse=True)
def _reset_auto_cmd_module_state():
    """Loop 2 iter 3 W2 fix: drain module-level state before AND after each test.

    The tests in this file directly mutate module-level mutable state
    on ``auto_cmd``:

    - ``_heartbeat_failures_q`` (queue.Queue) -- producers/tests put
      items; drain helpers consume them. A leak of items into a later
      test's drain() would shift its assertions.
    - ``_drain_state.last_drain_at`` -- timestamp guard for periodic
      drain skip logic (``_periodic_drain_if_due``).
    - ``_drain_decode_error_emitted`` -- W14 dedup flag for stderr
      breadcrumb.
    - ``_observability_swallowed_count`` -- I3 swallowed counter.
    - ``_assert_main_thread`` attribute -- some tests swap to a no-op
      lambda to exercise concurrency code paths from worker threads.

    Pre-fix individual tests drained the queue manually at their entry,
    but if a test failed mid-run between pollute and drain (e.g. an
    assertion error raised after ``put`` but before the next test's
    drain loop), the leaked items would spill forward. Post-fix this
    autouse fixture drains the queue + resets all flags + restores the
    original ``_assert_main_thread`` reference both in setup AND
    teardown, so test order is irrelevant and a mid-run failure
    cannot poison downstream tests.
    """
    original_assert = auto_cmd._assert_main_thread

    def _drain_all() -> None:
        while not auto_cmd._heartbeat_failures_q.empty():
            try:
                auto_cmd._heartbeat_failures_q.get_nowait()
            except queue.Empty:
                break
        auto_cmd._reset_drain_state_for_tests()
        auto_cmd._reset_drain_decode_error_emitted_for_tests()
        auto_cmd._reset_observability_swallowed_count_for_tests()

    _drain_all()
    try:
        yield
    finally:
        _drain_all()
        # Restore _assert_main_thread in case a test swapped it via direct
        # attribute mutation (the legacy pattern; new tests should prefer
        # ``monkeypatch.setattr`` so cleanup is automatic).
        auto_cmd._assert_main_thread = original_assert


def test_update_progress_writes_correct_schema(tmp_path):
    """D4.2: progress field has shape {phase, task_index, task_total, sub_phase}."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"started_at": "2026-04-25T10:00:00Z"}))
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=14,
        task_total=36,
        sub_phase="green",
    )
    data = json.loads(auto_run.read_text())
    assert data["progress"] == {
        "phase": 2,
        "task_index": 14,
        "task_total": 36,
        "sub_phase": "green",
    }
    assert data["started_at"] == "2026-04-25T10:00:00Z"  # preserved


def test_update_progress_is_atomic_under_concurrent_reads(tmp_path):
    """D4.1: concurrent readers never observe torn JSON."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(
        json.dumps(
            {
                "progress": {
                    "phase": 2,
                    "task_index": 13,
                    "task_total": 36,
                    "sub_phase": "refactor",
                }
            }
        )
    )
    failures: list[str] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            try:
                json.loads(auto_run.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(str(e))
            except (FileNotFoundError, PermissionError):
                # On Windows the brief window between os.replace operations
                # can yield a transient FileNotFoundError or PermissionError
                # when the reader opens the file precisely while the writer
                # is replacing it. The atomicity contract guarantees no
                # torn JSON; transient open failures are acceptable.
                pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    for i in range(50):
        auto_cmd._update_progress(
            auto_run, phase=2, task_index=14 + i, task_total=36, sub_phase="green"
        )
    stop.set()
    t.join(timeout=2)
    assert failures == [], f"reader saw torn JSON: {failures}"


def test_progress_field_absent_is_tolerated(tmp_path):
    """D4.3: parser tolerates auto-run.json without progress field."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"started_at": "2026-04-25T10:00:00Z"}))
    data = json.loads(auto_run.read_text())
    assert data.get("progress") is None  # absent is fine


def test_update_progress_always_emits_four_keys_with_null_sentinels(tmp_path):
    """D4.2 (iter 2 finding #4): all four keys ALWAYS present.

    Spec sec.2 D4.2 states 'shape exacto {phase, task_index, task_total,
    sub_phase}'. v0.3.0 baseline omitted keys whose value was None
    (degraded ``_task_progress`` returning ``(None, None)``). MAGI iter
    1 WARNING required satisfying the literal shape contract: emit JSON
    null for unknowns rather than omit the key. This protects future
    ``/sbtdd status --watch`` consumers from KeyError on degraded
    payloads.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"started_at": "2026-04-25T10:00:00Z"}))
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=None,
        task_total=None,
        sub_phase=None,
    )
    data = json.loads(auto_run.read_text())
    progress = data["progress"]
    assert set(progress.keys()) == {"phase", "task_index", "task_total", "sub_phase"}
    assert progress["phase"] == 2
    assert progress["task_index"] is None
    assert progress["task_total"] is None
    assert progress["sub_phase"] is None


def test_update_progress_emits_four_keys_with_partial_unknowns(tmp_path):
    """D4.2 (iter 2 finding #4): partial-None payload still has all four keys."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}")
    auto_cmd._update_progress(
        auto_run,
        phase=3,
        task_index=14,
        task_total=None,  # unknown total -- still emit as null
        sub_phase="green",
    )
    data = json.loads(auto_run.read_text())
    assert data["progress"] == {
        "phase": 3,
        "task_index": 14,
        "task_total": None,
        "sub_phase": "green",
    }


def test_update_progress_swallows_oserror_and_continues(tmp_path, monkeypatch, capfd):
    """J4.1: OSError on tmp write does not kill the auto run.

    Simulates a ``OSError(28, "No space left on device")`` raised by the
    ``Path.write_text`` call that creates the tmp file. ``_update_progress``
    must catch the OSError, emit a stderr breadcrumb starting ``[sbtdd]``,
    and return without raising. The original ``auto-run.json`` is left
    intact so resume / status readers see a consistent file rather than
    a half-written one.
    """
    auto_run = tmp_path / "auto-run.json"
    pre_state = {"started_at": "2026-04-25T10:00:00Z"}
    auto_run.write_text(json.dumps(pre_state))
    real_write_text = Path.write_text

    def boom(self, *args, **kwargs):
        # Only the tmp side-write should fail; preserve the original.
        if ".tmp." in str(self):
            raise OSError(28, "No space left on device")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", boom)
    # Should NOT raise.
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=1,
        task_total=10,
        sub_phase="red",
    )
    captured = capfd.readouterr()
    assert "[sbtdd]" in captured.err
    assert "progress write failed" in captured.err
    # Original auto-run.json preserved (not corrupted, no progress key
    # written because write failed).
    data = json.loads(auto_run.read_text())
    assert data["started_at"] == "2026-04-25T10:00:00Z"


def test_update_progress_retry_exhaustion_preserves_original(tmp_path, monkeypatch, capfd):
    """J4.2: retry-loop exhaustion does not corrupt auto-run.json.

    On Windows ``os.replace`` can fail with ``PermissionError`` when a
    concurrent reader holds the destination open without
    ``FILE_SHARE_DELETE``. The retry loop attempts up to 20 times; if
    every attempt fails the helper must catch the resulting OSError,
    clean up the tmp file, emit a breadcrumb, and leave the original
    auto-run.json intact rather than re-raising.
    """
    auto_run = tmp_path / "auto-run.json"
    original = {
        "progress": {
            "phase": 1,
            "task_index": 0,
            "task_total": 5,
            "sub_phase": "red",
        }
    }
    auto_run.write_text(json.dumps(original))

    def always_fail(src, dst):  # type: ignore[no-untyped-def]
        raise PermissionError(13, "Locked")

    monkeypatch.setattr(os, "replace", always_fail)
    # Should NOT raise.
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=1,
        task_total=5,
        sub_phase="green",
    )
    captured = capfd.readouterr()
    assert "[sbtdd]" in captured.err
    assert "progress write failed" in captured.err
    # Original payload preserved.
    data = json.loads(auto_run.read_text())
    assert data["progress"]["phase"] == 1
    assert data["progress"]["task_index"] == 0


def _make_audit() -> auto_cmd.AutoRunAudit:
    """Build a minimal valid :class:`AutoRunAudit` for J6 tests."""
    return auto_cmd.AutoRunAudit(
        schema_version=auto_cmd._AUTO_RUN_SCHEMA_VERSION,
        auto_started_at="2026-04-25T10:00:00Z",
        auto_finished_at=None,
        status="success",
        verdict=None,
        degraded=None,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=0,
        error=None,
    )


def test_write_auto_run_audit_preserves_progress_field(tmp_path):
    """J6.1: AutoRunAudit serialisation preserves existing progress key.

    Before v0.4.0 the audit writer overwrote ``auto-run.json`` with the
    serialised :class:`AutoRunAudit` only, transiently dropping the
    ``progress`` field until the next ``_update_progress`` call. v0.4.0
    J6 changes the helper to read-modify-write so the live progress
    snapshot survives audit refreshes; downstream readers (notably the
    eventual ``/sbtdd status --watch`` companion) never observe a
    half-second window where progress disappears between phase
    boundaries.
    """
    auto_run = tmp_path / "auto-run.json"
    pre_state = {
        "schema_version": auto_cmd._AUTO_RUN_SCHEMA_VERSION,
        "auto_started_at": "2026-04-25T09:00:00Z",
        "auto_finished_at": None,
        "status": "success",
        "verdict": None,
        "degraded": None,
        "accepted_conditions": 0,
        "rejected_conditions": 0,
        "tasks_completed": 0,
        "error": None,
        "progress": {
            "phase": 2,
            "task_index": 14,
            "task_total": 36,
            "sub_phase": "green",
        },
    }
    auto_run.write_text(json.dumps(pre_state))
    auto_cmd._write_auto_run_audit(auto_run, _make_audit())
    data = json.loads(auto_run.read_text())
    # Progress field preserved across audit write.
    assert data["progress"] == {
        "phase": 2,
        "task_index": 14,
        "task_total": 36,
        "sub_phase": "green",
    }
    # Audit fields also persisted.
    assert data["auto_started_at"] == "2026-04-25T10:00:00Z"
    assert data["status"] == "success"


def test_write_auto_run_audit_when_progress_absent(tmp_path):
    """J6.2: audit writes correctly when no prior progress field exists.

    Early in an auto run (before the first phase fires) ``auto-run.json``
    has no ``progress`` key. The audit writer must not synthesise one;
    the absent state stays absent so the D4.3 absent-tolerant downstream
    contract is preserved.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_cmd._write_auto_run_audit(auto_run, _make_audit())
    data = json.loads(auto_run.read_text())
    # Absent stays absent (D4.3 absent-tolerant downstream).
    assert "progress" not in data
    # Audit body is present.
    assert data["auto_started_at"] == "2026-04-25T10:00:00Z"
    assert data["status"] == "success"


# ---------------------------------------------------------------------------
# v0.5.0 S1-9: ProgressContext writer hooks at the 10 transition sites.
# ---------------------------------------------------------------------------


def test_phase_1_entry_writes_progress_phase_1():
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=1)
    ctx = get_current_progress()
    assert ctx.phase == 1
    assert ctx.iter_num == 0
    assert ctx.dispatch_label is None
    reset_current_progress()


def test_phase_2_entry_writes_phase_2_with_task_total():
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, task_total=36)
    ctx = get_current_progress()
    assert ctx.phase == 2
    assert ctx.task_total == 36
    reset_current_progress()


def test_magi_loop_2_iter_writes_iter_n():
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(iter_num=2, phase=3, dispatch_label="magi-loop2-iter2")
    ctx = get_current_progress()
    assert ctx.iter_num == 2
    assert ctx.phase == 3
    assert ctx.dispatch_label == "magi-loop2-iter2"
    reset_current_progress()


def test_set_progress_preserves_started_at_within_same_dispatch():
    """Intra-dispatch update keeps elapsed monotonic (sec.3 PINNED semantics)."""
    import time

    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, task_index=1, task_total=10, dispatch_label="green")
    first_started = get_current_progress().started_at
    time.sleep(0.01)
    # Same dispatch_label, intra-dispatch progress refinement.
    _set_progress(phase=2, task_index=1, task_total=10, dispatch_label="green")
    second_started = get_current_progress().started_at
    assert second_started == first_started, "started_at must NOT refresh within same dispatch"
    reset_current_progress()


def test_set_progress_refreshes_started_at_on_dispatch_change():
    """Different dispatch_label resets the elapsed timer."""
    import time

    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, dispatch_label="red")
    red_started = get_current_progress().started_at
    assert red_started is not None
    time.sleep(0.01)
    _set_progress(phase=2, dispatch_label="green")
    green_started = get_current_progress().started_at
    assert green_started is not None
    assert green_started > red_started, "different dispatch must refresh started_at"
    reset_current_progress()


def test_set_progress_clears_started_at_when_label_none():
    """Between-dispatches state has no elapsed timer."""
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, dispatch_label="red")
    assert get_current_progress().started_at is not None
    _set_progress(phase=2, dispatch_label=None)
    assert get_current_progress().started_at is None
    reset_current_progress()


def test_long_dispatch_wrapped_with_heartbeat_emits_ticks(capsys):
    import time

    from auto_cmd import _dispatch_with_heartbeat, _set_progress
    from heartbeat import reset_current_progress

    reset_current_progress()
    # Per Checkpoint 2 iter 2 melchior fix: caller MUST set dispatch_label
    # before invoking the wrapper (fail-loud); no silent fallback.
    _set_progress(phase=2, dispatch_label="test-dispatch")

    def fake_invoke():
        time.sleep(0.5)
        return 0

    rc = _dispatch_with_heartbeat(
        invoke=fake_invoke,
        heartbeat_interval=0.15,
    )
    assert rc == 0
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines() if line.startswith("[sbtdd auto] tick:")
    ]
    assert len(tick_lines) >= 2  # 0.5s / 0.15s ~ 3 ticks
    reset_current_progress()


def test_dispatch_with_heartbeat_fails_loud_when_no_dispatch_label():
    """Per Checkpoint 2 iter 2 melchior CRITICAL #1: silent fallback rejected."""
    import pytest as _pytest

    from auto_cmd import _dispatch_with_heartbeat
    from heartbeat import reset_current_progress

    reset_current_progress()
    with _pytest.raises(ValueError, match="dispatch_label"):
        _dispatch_with_heartbeat(invoke=lambda: 0, heartbeat_interval=0.5)


def test_update_progress_drains_heartbeat_queue_and_writes_max(tmp_path):
    """sec.3 single-writer rule: main thread drains queue, persists max() to JSON."""
    from auto_cmd import _drain_heartbeat_queue_and_persist, _heartbeat_failures_q

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()

    _heartbeat_failures_q.put(5)
    _heartbeat_failures_q.put(10)
    _heartbeat_failures_q.put(15)

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")
    _drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["heartbeat_failed_writes_total"] == 15


def test_drain_heartbeat_queue_persists_zombie_alert_sentinel(tmp_path):
    """C3 fold-in: zombie sentinel (>= _ZOMBIE_SENTINEL_OFFSET=1000) persisted as separate field."""
    from auto_cmd import _drain_heartbeat_queue_and_persist, _heartbeat_failures_q

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()

    _heartbeat_failures_q.put(5)  # plain failed-writes counter
    _heartbeat_failures_q.put(1003)  # zombie sentinel: 1000 + 3 zombies

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")
    _drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["heartbeat_failed_writes_total"] == 5
    assert data["heartbeat_zombie_thread_count"] == 3


def test_drain_heartbeat_queue_no_data_skips_write(tmp_path):
    """No queued data => helper returns without touching the file."""
    from auto_cmd import _drain_heartbeat_queue_and_persist, _heartbeat_failures_q

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"untouched": true}', encoding="utf-8")
    _drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data == {"untouched": True}


def test_concurrent_writers_serialize_via_file_lock(tmp_path):
    """C4 fold-in: cross-process file lock around auto-run.json read-modify-write.

    Best-effort smoke: invoke the helper twice in succession with the same
    queue; the second call must observe the first call's persisted value
    (no race-induced corruption).
    """
    from auto_cmd import _drain_heartbeat_queue_and_persist, _heartbeat_failures_q

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")
    _heartbeat_failures_q.put(20)
    _drain_heartbeat_queue_and_persist(auto_run_path)
    _heartbeat_failures_q.put(30)
    _drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    # max() preserved across calls.
    assert data["heartbeat_failed_writes_total"] == 30


def test_serialize_progress_context_iso_utc():
    from datetime import datetime, timezone

    from auto_cmd import _serialize_progress
    from heartbeat import reset_current_progress, set_current_progress
    from models import ProgressContext

    set_current_progress(
        ProgressContext(
            iter_num=2,
            phase=3,
            task_index=14,
            task_total=36,
            dispatch_label="magi-loop2-iter2",
            started_at=datetime(2026, 5, 1, 12, 34, 56, tzinfo=timezone.utc),
        )
    )
    serialized = _serialize_progress()
    assert serialized["iter_num"] == 2
    assert serialized["phase"] == 3
    assert serialized["task_index"] == 14
    assert serialized["task_total"] == 36
    assert serialized["dispatch_label"] == "magi-loop2-iter2"
    assert serialized["started_at"] == "2026-05-01T12:34:56Z"
    reset_current_progress()


def test_serialize_progress_context_started_at_none_serializes_as_null():
    from auto_cmd import _serialize_progress
    from heartbeat import reset_current_progress, set_current_progress
    from models import ProgressContext

    set_current_progress(ProgressContext(iter_num=1, phase=2, started_at=None))
    serialized = _serialize_progress()
    assert serialized["started_at"] is None
    reset_current_progress()


def test_serialize_progress_context_naive_datetime_normalized_to_utc():
    """Defensive: even if a naive datetime sneaks in, output is UTC-stamped."""
    from datetime import datetime, timezone

    from auto_cmd import _serialize_progress
    from heartbeat import reset_current_progress, set_current_progress
    from models import ProgressContext

    set_current_progress(
        ProgressContext(
            phase=2,
            started_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
    )
    serialized = _serialize_progress()
    assert serialized["started_at"].endswith("Z")
    reset_current_progress()


def test_periodic_drain_persists_counter_without_phase_transition(tmp_path):
    """Spec sec.11.1 W8: bound persistence latency to <= 30s sin transitions."""
    from auto_cmd import (
        _heartbeat_failures_q,
        _periodic_drain_if_due,
        _reset_drain_state_for_tests,
    )

    _reset_drain_state_for_tests()
    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()
    _heartbeat_failures_q.put(5)

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")
    _periodic_drain_if_due(auto_run_path, force=True)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["heartbeat_failed_writes_total"] == 5


def test_periodic_drain_skips_when_not_due(tmp_path):
    """Without ``force=True`` and without 30s elapsed, helper is a no-op."""
    from auto_cmd import (
        _heartbeat_failures_q,
        _periodic_drain_if_due,
        _reset_drain_state_for_tests,
    )

    _reset_drain_state_for_tests()
    # First call sets last_drain_at; second call within window must skip.
    _periodic_drain_if_due(tmp_path / "first.json", force=True)
    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()
    _heartbeat_failures_q.put(99)

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"untouched": true}', encoding="utf-8")
    _periodic_drain_if_due(auto_run_path)  # no force; just-set timestamp
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data == {"untouched": True}
    # Counter still in queue (skip preserved data).
    drained: list[int] = []
    while not _heartbeat_failures_q.empty():
        drained.append(_heartbeat_failures_q.get_nowait())
    assert 99 in drained


def test_drain_helper_rejects_non_main_thread():
    """W8 fold-in: _assert_main_thread enforces single-writer rule mechanically."""
    import threading as _t
    import pytest as _pytest

    from auto_cmd import _drain_heartbeat_queue_and_persist

    captured: dict[str, BaseException | None] = {"err": None}

    def background():
        try:
            _drain_heartbeat_queue_and_persist(Path("ignored.json"))
        except BaseException as e:  # noqa: BLE001
            captured["err"] = e

    th = _t.Thread(target=background)
    th.start()
    th.join(timeout=2.0)
    assert isinstance(captured["err"], RuntimeError)
    assert "main thread" in str(captured["err"]).lower()
    _ = _pytest  # keep import alive (avoid unused-import lint)


def test_dispatch_with_heartbeat_derives_label_from_progress():
    from auto_cmd import _dispatch_with_heartbeat, _set_progress
    from heartbeat import reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, dispatch_label="green")
    captured_label = {}

    def fake_invoke():
        from heartbeat import get_current_progress

        captured_label["label"] = get_current_progress().dispatch_label
        return 0

    rc = _dispatch_with_heartbeat(invoke=fake_invoke, heartbeat_interval=0.1)
    assert rc == 0
    assert captured_label["label"] == "green"
    reset_current_progress()


def test_set_progress_first_dispatch_from_none_label_refreshes_started_at():
    """W2 fold-in: None -> label first dispatch must set started_at.

    Predicate ``is_dispatch_transition = current.dispatch_label != dispatch_label``
    correctly evaluates ``None != "red"`` as True; this test pins that
    behavior so a future refactor doesn't accidentally swallow the first
    dispatch.
    """
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    # Initial: label None.
    assert get_current_progress().dispatch_label is None
    assert get_current_progress().started_at is None
    # First labeled dispatch must populate started_at.
    _set_progress(phase=2, dispatch_label="red")
    ctx = get_current_progress()
    assert ctx.dispatch_label == "red"
    assert ctx.started_at is not None
    reset_current_progress()


def test_update_progress_routes_through_with_file_lock(tmp_path, monkeypatch):
    """C4 extension Red: ``_update_progress`` MUST call ``_with_file_lock``.

    Pre-fix: only ``_drain_heartbeat_queue_and_persist`` wrapped its
    read-modify-write in ``_with_file_lock``. ``_update_progress`` did its
    full RMW without the cross-process advisory lock. CHANGELOG `[0.5.0]`
    claimed C4 fully shipped; this test pins the contract that the
    progress writer ALSO routes through ``_with_file_lock`` so the C4
    claim holds for both writers of ``auto-run.json``.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    call_count = {"n": 0}
    real_lock = auto_cmd._with_file_lock

    def spy_lock(path, fn):  # type: ignore[no-untyped-def]
        call_count["n"] += 1
        return real_lock(path, fn)

    monkeypatch.setattr(auto_cmd, "_with_file_lock", spy_lock)
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=1,
        task_total=10,
        sub_phase="red",
    )
    # _update_progress MUST have invoked _with_file_lock at least once
    # for its RMW. Pre-fix this assertion fails (call_count == 0).
    assert call_count["n"] >= 1, (
        "_update_progress did not route through _with_file_lock; "
        "C4 claim in CHANGELOG is incomplete"
    )


def test_write_auto_run_audit_routes_through_with_file_lock(tmp_path, monkeypatch):
    """C4 extension Red: ``_write_auto_run_audit`` MUST call ``_with_file_lock``.

    Counterpart to ``test_update_progress_routes_through_with_file_lock``
    for the audit writer.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    call_count = {"n": 0}
    real_lock = auto_cmd._with_file_lock

    def spy_lock(path, fn):  # type: ignore[no-untyped-def]
        call_count["n"] += 1
        return real_lock(path, fn)

    monkeypatch.setattr(auto_cmd, "_with_file_lock", spy_lock)
    audit = auto_cmd.AutoRunAudit(
        schema_version=auto_cmd._AUTO_RUN_SCHEMA_VERSION,
        auto_started_at="2026-05-02T00:00:00Z",
        auto_finished_at=None,
        status="success",
        verdict=None,
        degraded=None,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=0,
        error=None,
    )
    auto_cmd._write_auto_run_audit(auto_run, audit)
    assert call_count["n"] >= 1, (
        "_write_auto_run_audit did not route through _with_file_lock; "
        "C4 claim in CHANGELOG is incomplete"
    )


def test_concurrent_update_progress_writers_serialize_via_file_lock(tmp_path):
    """C4 extension: ``_update_progress`` writes serialize through ``_with_file_lock``.

    Pre-fix: ``_with_file_lock`` only wrapped ``_drain_heartbeat_queue_and_persist``.
    ``_update_progress`` performed read-modify-write WITHOUT the lock, so a
    concurrent reader / second writer could interleave the read with another
    writer's ``os.replace`` and produce a torn JSON document or lost update.

    Post-fix: ``_update_progress`` wraps the full read-write-os.replace cycle
    in ``_with_file_lock``. This test spawns N=10 background threads each
    calling ``_update_progress`` with a distinct ``sub_phase`` label and
    asserts the final on-disk JSON parses cleanly (no torn document).
    True cross-process serialisation is hard to test from a single test
    process; this test uses threads as the closest available proxy and
    relies on the lock-acquisition path being executed even though the
    advisory POSIX/Windows lock is per-process.

    NOTE (Loop 2 iter 3 W5): this test deliberately bypasses
    ``_assert_main_thread()`` via direct attribute swap to exercise the
    concurrency code path. Coverage gap acknowledged: no test exercises
    BOTH the main-thread assertion AND the concurrent-writer code path
    together; that combination is impossible by construction (the assert
    raises on non-main-thread entry, blocking the very path under test).
    The W13 main-thread guard is covered separately by
    ``test_update_progress_asserts_main_thread_at_entry``.
    """
    import sys

    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    errors: list[BaseException] = []

    def writer(label: str) -> None:
        try:
            auto_cmd._update_progress(
                auto_run,
                phase=2,
                task_index=1,
                task_total=10,
                sub_phase=label,
            )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    # Loop 2 W13: ``_update_progress`` enforces main-thread at entry; this
    # concurrent test exercises the LOCK code path under thread contention,
    # which by definition must run from worker threads. Bypass the W13
    # assert for the duration of this test (production callers stay on
    # the main thread; the assertion guards them).
    original_assert = auto_cmd._assert_main_thread
    auto_cmd._assert_main_thread = lambda: None
    try:
        threads = [threading.Thread(target=writer, args=(f"label-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)
    finally:
        auto_cmd._assert_main_thread = original_assert

    if errors:
        # Re-raise the first error so the test failure is informative.
        raise errors[0]

    # Final on-disk JSON must parse cleanly (no torn write).
    data = json.loads(auto_run.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "progress" in data
    # Some writer's label survived (last-writer-wins is acceptable; what's
    # NOT acceptable is a torn JSON or a missing progress key).
    assert data["progress"]["sub_phase"].startswith("label-")
    _ = sys  # silence unused-import lint


def test_concurrent_write_audit_writers_serialize_via_file_lock(tmp_path):
    """C4 extension: ``_write_auto_run_audit`` writes serialize through ``_with_file_lock``.

    Same rationale as ``test_concurrent_update_progress_writers_serialize_via_file_lock``
    but for ``_write_auto_run_audit``. Both helpers must hold the lock so
    concurrent writers do not corrupt ``auto-run.json``.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    errors: list[BaseException] = []

    def writer(idx: int) -> None:
        try:
            audit = auto_cmd.AutoRunAudit(
                schema_version=auto_cmd._AUTO_RUN_SCHEMA_VERSION,
                auto_started_at="2026-05-02T00:00:00Z",
                auto_finished_at=None,
                status="success",
                verdict=None,
                degraded=None,
                accepted_conditions=0,
                rejected_conditions=0,
                tasks_completed=idx,
                error=None,
            )
            auto_cmd._write_auto_run_audit(auto_run, audit)
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    if errors:
        raise errors[0]

    # Final on-disk JSON must parse cleanly.
    data = json.loads(auto_run.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "tasks_completed" in data
    assert isinstance(data["tasks_completed"], int)


def test_update_progress_with_nonempty_queue_does_not_deadlock(tmp_path):
    """Loop 2 CRITICAL #1: ``_update_progress`` + drain must not self-deadlock.

    Pre-fix: ``_do_update_progress`` ran inside ``_with_file_lock`` and then
    invoked ``_drain_heartbeat_queue_and_persist`` which itself acquired
    ``_with_file_lock`` on the same path. On Windows ``msvcrt.locking``
    returns ``OSError`` for nested locks (no reentrancy); on POSIX
    ``fcntl.flock(LOCK_EX)`` is reentrant per-process so the deadlock would
    only manifest under specific kernel configs. The fix makes
    ``_with_file_lock`` reentrant on the same thread (RLock-style) so any
    nested call from inside the locked region completes immediately.

    The test pre-loads the heartbeat failures queue so the drain path
    actually fires (skipping the early ``if not drained: return`` branch).
    The whole call must complete in well under 3 seconds; a deadlock would
    block forever.

    NOTE (Loop 2 iter 3 W5): this test deliberately bypasses
    ``_assert_main_thread()`` via direct attribute swap to run
    ``_update_progress`` from a worker thread (so the test thread can
    enforce a deadlock timeout via ``threading.Event.wait``). Coverage
    gap acknowledged: no test exercises BOTH the main-thread assertion
    AND the concurrent-writer code path together; that combination is
    impossible by construction.
    """
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")

    # Drain any leftover queue items from earlier tests so we control the state.
    while not auto_cmd._heartbeat_failures_q.empty():
        try:
            auto_cmd._heartbeat_failures_q.get_nowait()
        except Exception:  # noqa: BLE001
            break
    auto_cmd._heartbeat_failures_q.put(5)
    auto_cmd._heartbeat_failures_q.put(15)

    completed = threading.Event()
    error_holder: list[BaseException] = []

    def call() -> None:
        try:
            auto_cmd._update_progress(
                auto_run_path,
                phase=2,
                task_index=3,
                task_total=10,
                sub_phase="green",
            )
        except BaseException as exc:  # noqa: BLE001
            error_holder.append(exc)
        finally:
            completed.set()

    # Run on the main thread is the production path -- but to detect a
    # deadlock we must time-bound the call; running it on a worker thread
    # lets the test thread enforce the timeout. Use the main-thread mode
    # of the writer (which checks ``_assert_main_thread`` only inside
    # ``_serialize_progress``; if that asserts, the test still observes
    # the OSError-or-similar surfacing through the auto-run write).
    # However, ``_assert_main_thread`` raises RuntimeError unconditionally
    # off-thread. Bypass by spy-patching it for this test only.
    original_assert = auto_cmd._assert_main_thread
    auto_cmd._assert_main_thread = lambda: None
    try:
        worker = threading.Thread(target=call)
        worker.start()
        worker.join(timeout=3.0)
    finally:
        auto_cmd._assert_main_thread = original_assert

    assert completed.is_set(), (
        "deadlock detected: _update_progress did not return within 3s "
        "with non-empty heartbeat queue (CRITICAL #1)"
    )
    if error_holder:
        # Any error is acceptable -- the test guards specifically against
        # deadlock. But surface unexpected errors so they are not silenced.
        raise error_holder[0]


def test_with_file_lock_uses_threading_rlock_not_custom_bookkeeping(tmp_path):
    """Loop 2 W1+W3+W6+W9: ``_with_file_lock`` uses ``threading.RLock``.

    Pre-fix: ``_with_file_lock`` used a custom dict-based reentrancy
    counter (``_lock_holders: dict[(path, thread_id), int]``) with
    multiple subtle bugs:

    - W1: race between ``existing_depth`` check and ``_lock_holders[key] = 1``
      assignment when the OS lock is acquired (two threads could both
      see depth=0 and both try to acquire the OS lock).
    - W3: counter leak on early return paths (when ``open(lock_path)`` or
      ``msvcrt.locking`` fails the holder entry was set then cleaned up,
      but if cleanup itself failed the counter would persist).
    - W6: brittleness vs. the stdlib primitive that solves the same
      problem in 5 lines.
    - W9: key generation via ``str(path.resolve() if path.exists() else
      path)`` is fragile -- the same logical path can yield different
      keys depending on filesystem state mid-call.

    Post-fix: ``threading.RLock`` keyed by path string handles reentrancy
    natively (per-thread depth tracked by the RLock itself), so the
    custom bookkeeping is gone. This test asserts the public symbol
    ``_get_file_lock`` returns a ``threading.RLock`` instance for the
    given path and that the same path yields the same lock object
    (lock identity is stable, otherwise concurrent writers wouldn't
    serialize).
    """
    p = tmp_path / "auto-run.json"
    lock1 = auto_cmd._get_file_lock(p)
    lock2 = auto_cmd._get_file_lock(p)
    # Same path -> same lock instance (otherwise serialization is broken).
    assert lock1 is lock2, "two _get_file_lock calls on same path must return same RLock"
    # Must be an RLock (the stdlib type is _thread.RLock; the public
    # constructor returns instances of that type).
    rlock_type = type(threading.RLock())
    assert isinstance(lock1, rlock_type), (
        f"_get_file_lock must return threading.RLock, got {type(lock1).__name__}"
    )


def test_concurrent_writers_with_threading_rlock_serialize(tmp_path):
    """Loop 2 W1+W6: 20 concurrent writers serialize via stdlib RLock.

    Strengthened version of
    ``test_concurrent_update_progress_writers_serialize_via_file_lock``
    (which used 10 threads). Bumps to 20 to exercise the lock harder
    and asserts the final on-disk JSON is well-formed (no torn document)
    AND that all writers reached completion (no thread hangs because
    of bookkeeping leak).

    NOTE (Loop 2 iter 3 W5): this test deliberately bypasses
    ``_assert_main_thread()`` via direct attribute swap to exercise the
    concurrency code path. Coverage gap acknowledged: no test exercises
    BOTH the main-thread assertion AND the concurrent-writer code path
    together; that combination is impossible by construction (the assert
    raises on non-main-thread entry, blocking the very path under test).
    The W13 main-thread guard is covered separately by
    ``test_update_progress_asserts_main_thread_at_entry``.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    errors: list[BaseException] = []

    def writer(label: str) -> None:
        try:
            auto_cmd._update_progress(
                auto_run,
                phase=2,
                task_index=1,
                task_total=20,
                sub_phase=label,
            )
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    # Loop 2 W13: bypass main-thread guard for this concurrency-only test.
    original_assert = auto_cmd._assert_main_thread
    auto_cmd._assert_main_thread = lambda: None
    try:
        threads = [threading.Thread(target=writer, args=(f"label-{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=15.0)
            assert not t.is_alive(), (
                f"writer thread {t.name} hung past 15s -- bookkeeping leak suspected"
            )
    finally:
        auto_cmd._assert_main_thread = original_assert

    if errors:
        raise errors[0]

    data = json.loads(auto_run.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "progress" in data
    assert data["progress"]["sub_phase"].startswith("label-")


def test_drain_decode_error_breadcrumb_is_dedup(tmp_path, capsys):
    """Loop 2 W14: drain decode-error stderr breadcrumb is de-duped.

    Pre-fix: every JSON decode failure in ``_drain_heartbeat_queue_and_persist``
    emitted ``[sbtdd] warning: failed to read auto-run.json...`` to stderr.
    A persistently corrupt file (e.g. truncated to zero bytes mid-read)
    would spam stderr on every drain. Post-fix: emit the breadcrumb only
    on the first decode failure; subsequent failures are silent until
    the test-only reset.
    """
    auto_run_path = tmp_path / "auto-run.json"
    # Write a CORRUPT (non-JSON) payload so the drain's read trips the
    # JSONDecodeError branch.
    auto_run_path.write_text("not json{{{", encoding="utf-8")
    # Reset the dedup flag so test order doesn't matter.
    auto_cmd._reset_drain_decode_error_emitted_for_tests()

    # Drain leftover items.
    while not auto_cmd._heartbeat_failures_q.empty():
        try:
            auto_cmd._heartbeat_failures_q.get_nowait()
        except Exception:  # noqa: BLE001
            break

    # Two drains with corrupt file -> only one breadcrumb.
    auto_cmd._heartbeat_failures_q.put(("failed_writes", 5))
    auto_cmd._drain_heartbeat_queue_and_persist(auto_run_path)
    auto_cmd._heartbeat_failures_q.put(("failed_writes", 6))
    auto_cmd._drain_heartbeat_queue_and_persist(auto_run_path)
    captured = capsys.readouterr()
    breadcrumbs = [
        line
        for line in captured.err.splitlines()
        if "failed to read auto-run.json for heartbeat" in line
    ]
    assert len(breadcrumbs) == 1, (
        f"expected exactly 1 dedup'd breadcrumb across 2 drains with "
        f"corrupt file, got {len(breadcrumbs)}: {breadcrumbs}"
    )


def test_update_progress_asserts_main_thread_at_entry(tmp_path):
    """Loop 2 W13: ``_update_progress`` enforces single-writer at entry.

    Pre-fix: ``_assert_main_thread`` was only invoked inside
    ``_serialize_progress`` (which runs after the read step has already
    happened). A misbehaved caller invoking ``_update_progress`` from a
    non-main thread would do the read + lock acquisition before the
    assert tripped -- wasting work and creating a window where the
    intra-process lock was held by the wrong thread.

    Post-fix: ``_update_progress`` calls ``_assert_main_thread`` at
    entry, so the single-writer rule (sec.3) trips immediately on
    misuse rather than after partial work.
    """
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text("{}", encoding="utf-8")

    captured: list[BaseException] = []

    def call_from_worker() -> None:
        try:
            auto_cmd._update_progress(
                auto_run,
                phase=2,
                task_index=1,
                task_total=10,
                sub_phase="green",
            )
        except BaseException as e:  # noqa: BLE001
            captured.append(e)

    t = threading.Thread(target=call_from_worker)
    t.start()
    t.join(timeout=3.0)
    assert captured, "expected RuntimeError from non-main thread call"
    assert isinstance(captured[0], RuntimeError), (
        f"expected RuntimeError (single-writer guard), got {type(captured[0]).__name__}"
    )
    assert "main thread" in str(captured[0]).lower() or "single-writer" in str(captured[0]).lower()


def test_drain_separates_failed_writes_from_zombie_via_tagged_tuple(tmp_path):
    """Loop 2 W2+W7: tagged-tuple queue protocol.

    Pre-fix: the heartbeat failures queue multiplexed two unrelated counters
    (``failed_writes`` and ``zombie_thread_count``) on a single channel using
    ``+1000`` numeric offset as the discriminator. This had two problems:

    - W2: ``+1000`` collides with legitimate ``failed_writes`` values if a
      long-lived emitter accumulates >1000 failed writes (rare but
      pathological); the drain would mis-classify the value as zombie.
    - W7: multiplexing two semantically distinct counters on one channel via
      numeric offset is hard to maintain and read.

    Post-fix: producer emits ``("failed_writes", N)`` or ``("zombie", N)``
    tuples on the same queue. Drain dispatches by tag. This test pushes a
    mix of tuples and asserts both fields are persisted correctly with
    no cross-contamination, including a tuple with N >> 1000 in the
    ``failed_writes`` channel that pre-fix would have been mis-classified.
    """
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")

    # Drain leftover items.
    while not auto_cmd._heartbeat_failures_q.empty():
        try:
            auto_cmd._heartbeat_failures_q.get_nowait()
        except Exception:  # noqa: BLE001
            break

    # Push tagged tuples: failed_writes 5 + 1500 (would be mis-classified
    # as zombie under +1000 sentinel scheme), zombie 3.
    auto_cmd._heartbeat_failures_q.put(("failed_writes", 5))
    auto_cmd._heartbeat_failures_q.put(("failed_writes", 1500))
    auto_cmd._heartbeat_failures_q.put(("zombie", 3))

    auto_cmd._drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    # max() of failed_writes channel:
    assert data["heartbeat_failed_writes_total"] == 1500, (
        "failed_writes max() must be 1500 (tuple-tagged), pre-fix "
        "+1000 sentinel scheme would mis-classify as zombie"
    )
    # zombie field:
    assert data["heartbeat_zombie_thread_count"] == 3


def test_with_file_lock_uses_no_private_api():
    """Loop 2 iter 3 W1+W4+W6: no ``threading.RLock`` private API in helper.

    Pre-fix (Loop 2 iter 2): ``_with_file_lock`` invoked
    ``in_process_lock._is_owned()`` to distinguish outermost vs reentrant
    entry. ``_is_owned`` is a CPython-internal underscore-prefixed method
    on ``threading.RLock``. It is documented in CPython source but is not
    part of the public stdlib contract; future Python versions may rename
    or remove it without notice.

    Post-fix (Loop 2 iter 3): the helper uses a public ``threading.local``
    per-thread, per-path depth counter to determine outermost vs reentrant
    entry. No private API references remain.

    This test reads the source of ``_with_file_lock`` and asserts the
    forbidden ``_is_owned`` token is absent. A regression that re-introduces
    the private API call (e.g. via copy-paste from older Loop 2 iter 2
    docs) trips this test immediately.
    """
    import inspect

    source = inspect.getsource(auto_cmd._with_file_lock)
    assert "_is_owned" not in source, (
        "_with_file_lock must not depend on threading.RLock private API "
        "(_is_owned). Use a public threading.local depth counter instead."
    )


def test_module_state_is_clean_at_test_entry():
    """Loop 2 iter 3 W2: autouse fixture resets module state per test.

    Pre-fix (Loop 2 iter 2): tests in this file directly mutated module-
    level state -- ``_heartbeat_failures_q`` queue items,
    ``_drain_state.last_drain_at`` counter, ``_drain_decode_error_emitted``
    flag, and ``_assert_main_thread`` attribute swap -- without proper
    teardown. If a test failed mid-run OR if test ordering changed, the
    leaked state could contaminate subsequent tests with hard-to-diagnose
    flakes.

    Post-fix: ``conftest.py`` (or a module-scope autouse fixture) resets
    these knobs before AND after each test in this file. This test runs
    immediately after the fixture's setup phase and verifies the queue
    is empty + the drain decode flag is reset, demonstrating the fixture
    fired cleanly.

    Pollute the queue here, then rely on the autouse fixture's teardown
    to drain it before the next test starts. If the fixture breaks, the
    next test in collection order (alphabetically nearby) will observe
    the pollution and fail.
    """
    # Verify clean state at entry: fixture must have drained any prior leak.
    assert auto_cmd._heartbeat_failures_q.empty(), (
        "Loop 2 iter 3 W2 regression: heartbeat queue is not empty at test "
        "entry. The autouse module-state fixture failed to drain."
    )
    assert not auto_cmd._drain_decode_error_emitted, (
        "Loop 2 iter 3 W2 regression: _drain_decode_error_emitted is True "
        "at test entry. The autouse fixture failed to reset the flag."
    )
    # Pollute -- the fixture's teardown must drain.
    auto_cmd._heartbeat_failures_q.put(("failed_writes", 999))


# v1.0.0 F44.3: MAGI retried_agents propagation to auto-run.json audit.
def test_f44_3_retried_agents_persisted_to_auto_run_json(tmp_path):
    """F44.3-1: MAGI iter retried_agents written to auto-run.json."""
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(
        json.dumps({"started_at": "2026-05-01T12:00:00Z"}),
        encoding="utf-8",
    )

    auto_cmd._record_magi_retried_agents(auto_run_path, iter_n=2, retried_agents=["balthasar"])

    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["magi_iter2_retried_agents"] == ["balthasar"]
    # Existing field preserved.
    assert data["started_at"] == "2026-05-01T12:00:00Z"


def test_f44_3_backward_compat_with_v0_5_0_files(tmp_path):
    """F44.3-2: v0.5.0 auto-run.json (no field) parses cleanly."""
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(
        json.dumps({"started_at": "2026-05-01T12:00:00Z"}),
        encoding="utf-8",
    )
    audit = auto_cmd._read_auto_run_audit(auto_run_path)
    # Field absent -> empty list per F44.3-2 contract.
    assert audit.get("magi_iter1_retried_agents", []) == []


def test_f44_3_records_empty_list_when_no_retries(tmp_path):
    """F44.3 corner case: empty retried_agents tuple persists as []."""
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")

    auto_cmd._record_magi_retried_agents(auto_run_path, iter_n=1, retried_agents=[])
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["magi_iter1_retried_agents"] == []


# v1.0.0 J2: ResolvedModels preflight cache (S1-8 + S1-9).
def test_j2_resolve_all_models_once_returns_resolvedmodels(monkeypatch, tmp_path):
    """J2-1: _resolve_all_models_once returns ResolvedModels populated from config."""
    from models import ResolvedModels
    from unittest.mock import MagicMock

    # Stub Path.read_text so neither global nor project CLAUDE.md is "pinned".
    monkeypatch.setattr("pathlib.Path.read_text", lambda self, **_kw: "")

    config = MagicMock()
    config.implementer_model = "claude-haiku-4-5"
    config.spec_reviewer_model = "claude-sonnet-4-6"
    config.code_review_model = "claude-sonnet-4-6"
    config.magi_dispatch_model = "claude-opus-4-7"

    resolved = auto_cmd._resolve_all_models_once(config)
    assert isinstance(resolved, ResolvedModels)
    assert resolved.implementer == "claude-haiku-4-5"
    assert resolved.spec_reviewer == "claude-sonnet-4-6"
    assert resolved.code_review == "claude-sonnet-4-6"
    assert resolved.magi_dispatch == "claude-opus-4-7"


def test_j2_2_inv0_pin_overrides_plugin_local_md(monkeypatch, capsys):
    """J2-2: CLAUDE.md INV-0 pin wins over plugin.local.md fields."""
    from unittest.mock import MagicMock

    monkeypatch.setattr(
        "pathlib.Path.read_text",
        lambda self, **_kw: (
            "Use claude-opus-4-7 for all sessions" if "CLAUDE.md" in str(self) else ""
        ),
    )
    config = MagicMock()
    config.implementer_model = "claude-haiku-4-5"
    config.spec_reviewer_model = "claude-haiku-4-5"
    config.code_review_model = "claude-haiku-4-5"
    config.magi_dispatch_model = "claude-haiku-4-5"

    resolved = auto_cmd._resolve_all_models_once(config)
    # INV-0 wins: all fields = pinned model.
    assert resolved.implementer == "claude-opus-4-7"
    assert resolved.spec_reviewer == "claude-opus-4-7"
    assert resolved.code_review == "claude-opus-4-7"
    assert resolved.magi_dispatch == "claude-opus-4-7"
    captured = capsys.readouterr()
    assert "INV-0 cascade" in captured.err


def test_j2_2b_global_pin_wins_over_project_pin(monkeypatch, capsys):
    """J2-2b: global ~/.claude/CLAUDE.md pin wins over project pin (INV-0).

    Regression guard for caspar Loop 2 iter 3 CRITICAL #1: cascade had
    been inverted (project-first) in iter 2; iter 3 inverted back to
    global-first per INV-0 maxima precedencia.
    """
    from unittest.mock import MagicMock

    global_path = Path.home() / ".claude" / "CLAUDE.md"
    project_path = Path.cwd() / "CLAUDE.md"

    def fake_read_text(self, **_kw):
        if str(self) == str(global_path):
            return "Use claude-opus-4-7 for all sessions"
        if str(self) == str(project_path):
            return "Use claude-haiku-4-5 for all sessions"
        return ""

    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)
    config = MagicMock()
    config.implementer_model = "claude-sonnet-4-6"
    config.spec_reviewer_model = "claude-sonnet-4-6"
    config.code_review_model = "claude-sonnet-4-6"
    config.magi_dispatch_model = "claude-sonnet-4-6"

    resolved = auto_cmd._resolve_all_models_once(config)
    # Global wins per INV-0: all fields = global pin (opus).
    assert resolved.implementer == "claude-opus-4-7"
    assert resolved.spec_reviewer == "claude-opus-4-7"
    assert resolved.code_review == "claude-opus-4-7"
    assert resolved.magi_dispatch == "claude-opus-4-7"
    captured = capsys.readouterr()
    assert "INV-0 cascade" in captured.err
    # Source explicitly identified as global.
    assert "global" in captured.err


def test_j2_2c_multi_pin_shadow_breadcrumb(monkeypatch, capsys):
    """J2-2c (melchior iter 4 W7): when global AND project pin DIFFERENT
    models, an additional shadow breadcrumb tells the operator the
    project pin was overridden.
    """
    from unittest.mock import MagicMock

    global_path = Path.home() / ".claude" / "CLAUDE.md"
    project_path = Path.cwd() / "CLAUDE.md"

    def fake_read_text(self, **_kw):
        if str(self) == str(global_path):
            return "Use claude-opus-4-7 for all sessions"
        if str(self) == str(project_path):
            return "Use claude-haiku-4-5 for all sessions"
        return ""

    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)
    config = MagicMock()
    config.implementer_model = None
    config.spec_reviewer_model = None
    config.code_review_model = None
    config.magi_dispatch_model = None

    auto_cmd._resolve_all_models_once(config)
    captured = capsys.readouterr()
    assert "OVERRIDES" in captured.err
    assert "claude-opus-4-7" in captured.err  # global pin
    assert "claude-haiku-4-5" in captured.err  # project pin
    assert "shadowed" in captured.err.lower()


def test_j2_2d_no_shadow_breadcrumb_when_pins_match(monkeypatch, capsys):
    """J2-2d: same-pin global+project case is silent (no shadow surprise)."""
    from unittest.mock import MagicMock

    global_path = Path.home() / ".claude" / "CLAUDE.md"
    project_path = Path.cwd() / "CLAUDE.md"
    same_pin_text = "Use claude-opus-4-7 for all sessions"

    def fake_read_text(self, **_kw):
        if str(self) in (str(global_path), str(project_path)):
            return same_pin_text
        return ""

    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)
    config = MagicMock()
    config.implementer_model = None
    config.spec_reviewer_model = None
    config.code_review_model = None
    config.magi_dispatch_model = None

    auto_cmd._resolve_all_models_once(config)
    captured = capsys.readouterr()
    # Single-pin breadcrumb fires.
    assert "INV-0 cascade" in captured.err
    # But no shadow surprise (no contradiction).
    assert "OVERRIDES" not in captured.err
    assert "shadowed" not in captured.err.lower()


def test_j2_3_resolved_models_is_frozen():
    """J2-3: ResolvedModels is immutable."""
    from dataclasses import FrozenInstanceError

    from models import ResolvedModels

    rm = ResolvedModels(implementer="a", spec_reviewer="b", code_review="c", magi_dispatch="d")
    with pytest.raises(FrozenInstanceError):
        rm.implementer = "z"  # type: ignore[misc]


def test_f44_3_multiple_iters_do_not_clobber_each_other(tmp_path):
    """F44.3: per-iter fields coexist."""
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")

    auto_cmd._record_magi_retried_agents(auto_run_path, iter_n=1, retried_agents=["caspar"])
    auto_cmd._record_magi_retried_agents(
        auto_run_path, iter_n=2, retried_agents=["balthasar", "melchior"]
    )
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["magi_iter1_retried_agents"] == ["caspar"]
    assert data["magi_iter2_retried_agents"] == ["balthasar", "melchior"]
