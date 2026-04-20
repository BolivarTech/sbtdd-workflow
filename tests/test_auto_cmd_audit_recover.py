# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for `_read_audit_tasks_completed` observability (MAGI Loop 2 D iter 1 Balthasar).

The helper used to silently return ``0`` on every failure mode (missing
file, corrupt JSON, OSError). That silences real audit corruption.
Softened contract: still best-effort recovery, but emit a stderr
diagnostic so operators can see why the count regressed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import auto_cmd


def test_read_audit_tasks_completed_missing_file_is_silent_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Missing file is the expected-cold-start path; no stderr noise."""
    missing = tmp_path / "auto-run.json"
    result = auto_cmd._read_audit_tasks_completed(missing)
    assert result == 0
    # Cold start (no file yet) must not pollute stderr; only actual
    # corruption deserves a diagnostic.
    assert capsys.readouterr().err == ""


def test_read_audit_tasks_completed_happy_path(tmp_path: Path) -> None:
    target = tmp_path / "auto-run.json"
    target.write_text('{"tasks_completed": 7}', encoding="utf-8")
    assert auto_cmd._read_audit_tasks_completed(target) == 7


def test_read_audit_tasks_completed_corrupt_json_emits_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Corrupt file: still best-effort 0, but stderr must flag it."""
    target = tmp_path / "auto-run.json"
    target.write_text("{not json at all", encoding="utf-8")
    result = auto_cmd._read_audit_tasks_completed(target)
    assert result == 0
    err = capsys.readouterr().err
    assert "auto-run.json" in err or str(target) in err
    assert "fallback" in err.lower() or "corrupt" in err.lower()


def test_read_audit_tasks_completed_non_int_emits_stderr(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Non-int tasks_completed: stderr flag."""
    target = tmp_path / "auto-run.json"
    target.write_text('{"tasks_completed": "lots"}', encoding="utf-8")
    result = auto_cmd._read_audit_tasks_completed(target)
    assert result == 0
    err = capsys.readouterr().err
    assert "auto-run.json" in err or str(target) in err
