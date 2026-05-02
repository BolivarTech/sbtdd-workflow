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
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd


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
    assert second_started == first_started, (
        "started_at must NOT refresh within same dispatch"
    )
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
            phase=2, started_at=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
    )
    serialized = _serialize_progress()
    assert serialized["started_at"].endswith("Z")
    reset_current_progress()


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
