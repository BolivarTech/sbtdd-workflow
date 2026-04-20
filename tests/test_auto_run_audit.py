#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Schema contract tests for AutoRunAudit (Milestone D Task 1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import auto_cmd
from errors import ValidationError


def test_auto_run_audit_is_frozen_dataclass() -> None:
    audit = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at="2026-04-19T10:15:00Z",
        status="success",
        verdict="GO",
        degraded=False,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=3,
        error=None,
    )
    with pytest.raises((AttributeError, Exception)):
        audit.status = "magi_gate_blocked"  # type: ignore[misc]


def test_auto_run_audit_from_dict_round_trip(tmp_path: Path) -> None:
    fixture = Path("tests/fixtures/auto-run/happy-path.json").read_text("utf-8")
    payload = json.loads(fixture)
    audit = auto_cmd.AutoRunAudit.from_dict(payload)
    assert audit.schema_version == 1
    assert audit.status == "success"
    assert audit.tasks_completed == 3
    assert audit.to_dict() == payload


def test_auto_run_audit_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError) as exc:
        auto_cmd.AutoRunAudit(
            schema_version=1,
            auto_started_at="2026-04-19T10:00:00Z",
            auto_finished_at=None,
            status="something_else",
            verdict=None,
            degraded=None,
            accepted_conditions=0,
            rejected_conditions=0,
            tasks_completed=0,
            error=None,
        ).validate_schema()
    assert "status" in str(exc.value)


def test_auto_run_audit_rejects_negative_counts() -> None:
    audit = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at=None,
        status="success",
        verdict="GO",
        degraded=False,
        accepted_conditions=-1,
        rejected_conditions=0,
        tasks_completed=0,
        error=None,
    )
    with pytest.raises(ValidationError):
        audit.validate_schema()


def test_write_auto_run_audit_accepts_audit_object(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "auto-run.json"
    audit = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at="2026-04-19T10:05:00Z",
        status="success",
        verdict="GO",
        degraded=False,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=2,
        error=None,
    )
    auto_cmd._write_auto_run_audit(target, audit)
    data = json.loads(target.read_text("utf-8"))
    assert data["schema_version"] == 1
    assert data["status"] == "success"


def test_write_auto_run_audit_validates_before_write(tmp_path: Path) -> None:
    target = tmp_path / ".claude" / "auto-run.json"
    bad = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at=None,
        status="bogus",
        verdict=None,
        degraded=None,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=0,
        error=None,
    )
    with pytest.raises(ValidationError):
        auto_cmd._write_auto_run_audit(target, bad)
    assert not target.exists()


def test_write_auto_run_audit_rejects_dict(tmp_path: Path) -> None:
    # Plan D iter 2 Caspar WARNING: removed the dict back-compat path to
    # force every caller through strict schema validation. Passing a
    # raw dict must now raise TypeError (or be caught by mypy), not
    # silently persist an unvalidated payload. Pre-1.0 the removal is
    # safe; post-1.0 this test guards against regression.
    target = tmp_path / ".claude" / "auto-run.json"
    with pytest.raises((TypeError, ValidationError)):
        auto_cmd._write_auto_run_audit(
            target,
            {"auto_started_at": "2026-04-19T10:00:00Z"},  # type: ignore[arg-type]
        )
    assert not target.exists()


def test_write_auto_run_audit_is_atomic_on_os_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAGI Loop 2 D iter 1 Caspar: incremental audit write must be atomic.

    If ``os.replace`` raises (permission denied, cross-device rename,
    read-only target) the tmp file must be cleaned up before the error
    propagates. Otherwise a Windows process killed mid-write leaves
    ``auto-run.json.tmp.<pid>`` leaking onto disk and corrupts the
    raise-safety guarantee that the last-persisted audit = truth.
    """
    target = tmp_path / ".claude" / "auto-run.json"
    audit = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at=None,
        status="success",
        verdict="GO",
        degraded=False,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=1,
        error=None,
    )

    def _boom(_src: object, _dst: object) -> None:
        raise OSError("simulated replace failure")

    import os as _os

    monkeypatch.setattr(_os, "replace", _boom)
    with pytest.raises(OSError):
        auto_cmd._write_auto_run_audit(target, audit)

    # Target must not exist (atomic failure) and tmp must be cleaned up.
    assert not target.exists()
    leftovers = list(target.parent.glob("auto-run.json.tmp.*"))
    assert leftovers == [], f"stray tmp files leaked: {leftovers}"


def test_write_auto_run_audit_persists_via_replace(tmp_path: Path) -> None:
    """Happy path writes via tmp + replace, leaving no residual tmp files."""
    target = tmp_path / ".claude" / "auto-run.json"
    audit = auto_cmd.AutoRunAudit(
        schema_version=1,
        auto_started_at="2026-04-19T10:00:00Z",
        auto_finished_at="2026-04-19T10:05:00Z",
        status="success",
        verdict="GO",
        degraded=False,
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=1,
        error=None,
    )
    auto_cmd._write_auto_run_audit(target, audit)
    assert target.exists()
    leftovers = list(target.parent.glob("auto-run.json.tmp.*"))
    assert leftovers == []
