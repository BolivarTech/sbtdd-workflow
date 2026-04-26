#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.4.0 Feature F MAGI dispatch hardening (F43, F44, F45)."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import magi_dispatch  # noqa: E402
from errors import ValidationError  # noqa: E402


# ---------------------------------------------------------------------------
# F43 -- _discover_verdict_marker
# ---------------------------------------------------------------------------


def test_discover_verdict_marker_picks_newest_by_mtime(tmp_path: Path) -> None:
    """F43.1: enumerator returns marker with max mtime."""
    sub_old = tmp_path / "old"
    sub_new = tmp_path / "new"
    sub_old.mkdir()
    sub_new.mkdir()
    (sub_old / "MAGI_VERDICT_MARKER.json").write_text(
        json.dumps({"verdict": "GO"}), encoding="utf-8"
    )
    time.sleep(0.05)
    (sub_new / "MAGI_VERDICT_MARKER.json").write_text(
        json.dumps({"verdict": "GO_WITH_CAVEATS"}), encoding="utf-8"
    )
    # Force mtime ordering across coarse-granularity Windows clocks.
    old_marker = sub_old / "MAGI_VERDICT_MARKER.json"
    os.utime(old_marker, (old_marker.stat().st_atime, old_marker.stat().st_mtime - 10))
    found = magi_dispatch._discover_verdict_marker(tmp_path)
    assert found.parent.name == "new"


def test_discover_verdict_marker_raises_when_empty(tmp_path: Path) -> None:
    """F43.2: ValidationError when no markers found, lists present files."""
    (tmp_path / "stray.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValidationError) as ei:
        magi_dispatch._discover_verdict_marker(tmp_path)
    assert "MAGI_VERDICT_MARKER.json" in str(ei.value)
    assert "stray.json" in str(ei.value)


def test_discover_verdict_marker_finds_in_subdir(tmp_path: Path) -> None:
    """F43.3: rglob finds markers in nested subdirs (layout-change defensive)."""
    sub = tmp_path / "run-XYZ"
    sub.mkdir()
    (sub / "MAGI_VERDICT_MARKER.json").write_text(json.dumps({"verdict": "GO"}), encoding="utf-8")
    found = magi_dispatch._discover_verdict_marker(tmp_path)
    assert found.parent.name == "run-XYZ"


# ---------------------------------------------------------------------------
# F44 -- retried_agents field on MAGIVerdict
# ---------------------------------------------------------------------------


def _marker_with_consensus(verdict: str, **extra: object) -> dict[str, object]:
    """Return a MAGI marker payload built around the canonical report shape.

    The plugin's :func:`magi_dispatch.parse_magi_report` requires the legacy
    ``consensus.consensus`` slot to extract the verdict label. The MAGI
    2.2.1+ marker schema may add a top-level ``verdict`` key plus a flatter
    ``consensus`` block; this helper produces a payload that satisfies both
    shapes so ``MAGIVerdict.from_marker`` can keep delegating to the report
    parser without sec.S.10 drift.
    """
    payload: dict[str, object] = {
        "verdict": verdict,
        "consensus": {
            "consensus": verdict,
            "conditions": [],
            "findings": [],
        },
    }
    payload.update(extra)
    return payload


def test_retried_agents_parsed_when_present(tmp_path: Path) -> None:
    """F44.1: retried_agents from marker JSON becomes tuple."""
    marker = tmp_path / "MAGI_VERDICT_MARKER.json"
    payload = _marker_with_consensus(
        "GO_WITH_CAVEATS",
        iteration=1,
        agents=["melchior", "balthasar", "caspar"],
        retried_agents=["caspar"],
    )
    marker.write_text(json.dumps(payload), encoding="utf-8")
    verdict = magi_dispatch.MAGIVerdict.from_marker(marker)
    assert verdict.retried_agents == ("caspar",)


def test_retried_agents_defaults_empty_tuple(tmp_path: Path) -> None:
    """F44.2: MAGI 2.1.x marker without retried_agents loads cleanly."""
    marker = tmp_path / "MAGI_VERDICT_MARKER.json"
    payload = _marker_with_consensus(
        "GO",
        iteration=1,
        agents=["melchior", "balthasar", "caspar"],
    )
    marker.write_text(json.dumps(payload), encoding="utf-8")
    verdict = magi_dispatch.MAGIVerdict.from_marker(marker)
    assert verdict.retried_agents == ()


def test_retried_agents_consumable_by_audit_writer() -> None:
    """F44.3 (re-scoped): retried_agents tuple is JSON-serializable + ordered."""
    verdict = magi_dispatch.MAGIVerdict(
        verdict="GO_WITH_CAVEATS",
        degraded=False,
        conditions=(),
        findings=(),
        raw_output="{}",
        retried_agents=("balthasar", "caspar"),
    )
    serialized = json.dumps(list(verdict.retried_agents))
    assert json.loads(serialized) == ["balthasar", "caspar"]
