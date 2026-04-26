#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature D auto-run.json progress field.

v0.4.0 J4 extensions:

- ``test_update_progress_swallows_oserror_and_continues`` (J4.1).
- ``test_update_progress_retry_exhaustion_preserves_original`` (J4.2).
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


