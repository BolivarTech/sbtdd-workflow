# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for concurrent state-file write detection (Plan D Task 10)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import resume_cmd
from errors import StateFileError


def _write_state(root: Path, phase: str) -> None:
    state_dir = root / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "session-state.json").write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": "1",
                "current_task_title": "T1",
                "current_phase": phase,
                "phase_started_at_commit": "abc1234",
                "last_verification_at": None,
                "last_verification_result": None,
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_concurrent_state_write_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Plan D iter 2 Caspar WARNING: the iter 1 variant relied on
    # `time.sleep(0.02)` + a racing writer. Deterministic replacement:
    # monkeypatch `Path.stat` + `Path.read_bytes` so BOTH mtime AND
    # content diverge between the two internal reads (softened contract
    # per MAGI Loop 2 D iter 1: raise only on content divergence; mtime
    # alone just warns).
    state_path = tmp_path / ".claude" / "session-state.json"
    _write_state(tmp_path, "red")

    real_stat = Path.stat
    real_read = Path.read_bytes
    call_count = {"n": 0}

    class _FakeStatResult:
        def __init__(self, mtime_ns: int, real: Any) -> None:
            self._mtime_ns = mtime_ns
            self._real = real

        def __getattr__(self, name: str) -> Any:
            if name == "st_mtime_ns":
                return self._mtime_ns
            return getattr(self._real, name)

    # Pre-compute two distinct mtimes so the second read observes drift.
    mtimes_ns = iter([1_000_000_000, 1_500_000_000])
    contents = iter([b'{"a":1}', b'{"a":2}'])

    def fake_stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == state_path:
            call_count["n"] += 1
            try:
                return _FakeStatResult(next(mtimes_ns), real_stat(self, *args, **kwargs))
            except StopIteration:
                return real_stat(self, *args, **kwargs)
        return real_stat(self, *args, **kwargs)

    def fake_read(self: Path) -> bytes:
        if self == state_path:
            try:
                return next(contents)
            except StopIteration:
                return real_read(self)
        return real_read(self)

    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(Path, "read_bytes", fake_read)

    with pytest.raises(StateFileError) as exc:
        resume_cmd._assert_state_stable_between_reads(state_path)
    assert "concurrent" in str(exc.value).lower() or "content" in str(exc.value).lower()
    # Sanity: both reads actually happened.
    assert call_count["n"] >= 2


def test_stable_state_does_not_raise(tmp_path: Path) -> None:
    state_path = tmp_path / ".claude" / "session-state.json"
    _write_state(tmp_path, "red")
    # Negative: stable reads must not raise. Without monkeypatching,
    # the two real stat()s within the 10 ms sleep window observe the
    # same mtime on any reasonable filesystem.
    resume_cmd._assert_state_stable_between_reads(state_path)


def test_mtime_only_change_warns_but_does_not_raise(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """MAGI Loop 2 D iter 1 (Caspar + Balthasar + Melchior triple-flag).

    On Windows NTFS an editor "save" rewrites the same bytes but bumps
    mtime. Previously this triggered a ``StateFileError`` and trapped
    the user. Softened contract: raise only when BOTH mtime AND
    content diverge. mtime-only divergence emits a stderr warning and
    returns normally.
    """
    state_path = tmp_path / ".claude" / "session-state.json"
    _write_state(tmp_path, "red")

    real_stat = Path.stat

    class _FakeStatResult:
        def __init__(self, mtime_ns: int, real: Any) -> None:
            self._mtime_ns = mtime_ns
            self._real = real

        def __getattr__(self, name: str) -> Any:
            if name == "st_mtime_ns":
                return self._mtime_ns
            return getattr(self._real, name)

    mtimes_ns = iter([1_000_000_000, 1_500_000_000])

    def fake_stat(self: Path, *args: Any, **kwargs: Any) -> Any:
        if self == state_path:
            try:
                return _FakeStatResult(next(mtimes_ns), real_stat(self, *args, **kwargs))
            except StopIteration:
                return real_stat(self, *args, **kwargs)
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)
    # No content change: read_bytes returns the same bytes both times.
    # Softened contract: must NOT raise.
    resume_cmd._assert_state_stable_between_reads(state_path)
    err = capsys.readouterr().err
    assert "mtime" in err.lower()


def test_content_change_without_mtime_still_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If only content differs (mtime-pin hack), still raise -- content
    divergence is the strong signal of an actual concurrent writer."""
    state_path = tmp_path / ".claude" / "session-state.json"
    _write_state(tmp_path, "red")

    call = {"n": 0}
    real_read = Path.read_bytes

    def fake_read(self: Path) -> bytes:
        if self == state_path:
            call["n"] += 1
            if call["n"] == 1:
                return b'{"a":1}'
            return b'{"a":2}'
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", fake_read)

    with pytest.raises(StateFileError):
        resume_cmd._assert_state_stable_between_reads(state_path)
