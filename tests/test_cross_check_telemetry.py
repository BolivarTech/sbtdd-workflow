#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Tests for scripts/cross_check_telemetry.py (v1.0.2 Item A).

Covers escenarios A-1 (happy path), A-2 (empty dir), A-3 (malformed
JSON skipped) per sbtdd/spec-behavior.md sec.§4.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _make_iter_artifact(path: Path, iter_n: int, decisions: list[dict]) -> None:
    """Write a synthetic iter{N}-{ts}.json artifact."""
    payload = {
        "iter": iter_n,
        "timestamp": f"2026-05-06T0{iter_n}:00:00Z",
        "magi_verdict": "GO_WITH_CAVEATS",
        "cross_check_decisions": decisions,
        "diff_truncated": False,
        "diff_original_bytes": 12345,
        "diff_cap_bytes": 200000,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_a1_happy_path_aggregates_three_iters(tmp_path):
    """A-1: aggregate three valid iter artifacts."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-2026-05-06.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t1",
                "severity": "WARNING",
            }
        ],
    )
    _make_iter_artifact(
        root / "iter2-2026-05-06.json",
        2,
        [
            {
                "original_index": 0,
                "decision": "DOWNGRADE",
                "rationale": "info",
                "recommended_severity": "INFO",
                "agent": "balthasar",
                "title": "t2",
                "severity": "WARNING",
            }
        ],
    )
    _make_iter_artifact(
        root / "iter3-2026-05-06.json",
        3,
        [
            {
                "original_index": 0,
                "decision": "REJECT",
                "rationale": "fp",
                "recommended_severity": None,
                "agent": "caspar",
                "title": "t3",
                "severity": "WARNING",
            }
        ],
    )

    report = aggregate(root)

    assert report.total_iters == 3
    assert report.decision_distribution == {"KEEP": 1, "DOWNGRADE": 1, "REJECT": 1}
    assert len(report.per_iter) == 3
    assert [p.iter for p in report.per_iter] == [1, 2, 3]
    assert 0.0 <= report.agreement_rate <= 1.0
    assert 0.0 <= report.truncation_rate <= 1.0


def test_a2_empty_directory_tolerated(tmp_path):
    """A-2: empty dir returns total_iters=0 without error."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()

    report = aggregate(root)

    assert report.total_iters == 0
    assert report.decision_distribution == {}
    assert report.per_iter == []


def test_a3_malformed_json_skipped_with_breadcrumb(tmp_path, capsys):
    """A-3: malformed JSON files skipped with stderr breadcrumb."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-good.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )
    (root / "iter2-broken.json").write_text("{not json", encoding="utf-8")
    _make_iter_artifact(
        root / "iter3-good.json",
        3,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "balthasar",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )

    report = aggregate(root)

    assert report.total_iters == 2
    captured = capsys.readouterr()
    assert "iter2-broken.json" in captured.err
    assert "skip" in captured.err.lower() or "malformed" in captured.err.lower()


def test_aggregate_missing_root_raises_filenotfounderror(tmp_path):
    """W3 iter 1 fix: aggregate() raises FileNotFoundError when root absent."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate  # type: ignore[import-not-found]

    ghost = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError) as exc:
        aggregate(ghost)
    assert str(ghost) in str(exc.value)
    assert "Feature G" in str(exc.value)


def test_a4_markdown_output_well_formed(tmp_path):
    """A-4: markdown output contains required tables."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_markdown  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-x.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )

    report = aggregate(root)
    md = format_markdown(report)

    assert "Decision distribution" in md
    assert "Per-iter breakdown" in md
    assert "Per-agent" in md
    assert "Per-severity" in md
    assert "|---" in md
    assert "KEEP" in md


def test_a4_empty_markdown_no_iterations_message(tmp_path):
    """A-4 empty: markdown shows 'No iterations found' for empty dir."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_markdown  # type: ignore[import-not-found]

    root = tmp_path / "empty"
    root.mkdir()
    md = format_markdown(aggregate(root))

    assert "No iterations found" in md


def test_a5_json_output_parseable(tmp_path):
    """A-5: JSON output round-trips through json.loads."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_json  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-x.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )

    report = aggregate(root)
    text = format_json(report)
    parsed = json.loads(text)

    assert set(parsed.keys()) >= {
        "total_iters",
        "decision_distribution",
        "per_iter",
        "agreement_rate",
        "truncation_rate",
    }
    assert parsed["total_iters"] == 1
    assert isinstance(parsed["per_iter"], list)
    assert isinstance(parsed["agreement_rate"], (int, float))


def test_cli_default_format_markdown(tmp_path, capsys):
    """CLI invokes aggregate + format_markdown by default."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-x.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )

    rc = main(["--root", str(root)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Decision distribution" in captured.out


def test_cli_format_json_flag(tmp_path, capsys):
    """CLI --format json outputs JSON parseable text."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main  # type: ignore[import-not-found]

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-x.json",
        1,
        [
            {
                "original_index": 0,
                "decision": "KEEP",
                "rationale": "ok",
                "recommended_severity": None,
                "agent": "melchior",
                "title": "t",
                "severity": "WARNING",
            }
        ],
    )

    rc = main(["--root", str(root), "--format", "json"])
    captured = capsys.readouterr()

    assert rc == 0
    parsed = json.loads(captured.out)
    assert parsed["total_iters"] == 1


def test_cli_missing_root_exit_2(tmp_path, capsys):
    """CLI raises FileNotFoundError ⇒ exit code 2."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main  # type: ignore[import-not-found]

    rc = main(["--root", str(tmp_path / "does-not-exist")])
    captured = capsys.readouterr()

    assert rc == 2
    assert "not found" in captured.err.lower()
