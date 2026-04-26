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


# ---------------------------------------------------------------------------
# F45 -- _tolerant_agent_parse
# ---------------------------------------------------------------------------


def test_tolerant_agent_parse_extracts_from_preamble(tmp_path: Path) -> None:
    """F45.1: extract JSON object from agent result wrapped in narrative."""
    raw = tmp_path / "melchior.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": (
                    "Based on my review of the iter-2 fixes, the streaming wiring is "
                    "correctly threaded.\n\n"
                    '{"agent": "melchior", "verdict": "GO", "confidence": 0.88, '
                    '"summary": "Iter 2 closes findings.", "reasoning": "...", '
                    '"findings": [], "recommendation": "Ship v0.3.0."}'
                ),
            }
        ),
        encoding="utf-8",
    )
    parsed = magi_dispatch._tolerant_agent_parse(raw)
    assert parsed["agent"] == "melchior"
    assert parsed["verdict"] == "GO"
    assert parsed["confidence"] == 0.88


def test_tolerant_agent_parse_pure_json(tmp_path: Path) -> None:
    """F45.2: pure JSON result parses identically to strict parser."""
    raw = tmp_path / "caspar.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": json.dumps(
                    {
                        "agent": "caspar",
                        "verdict": "approve",
                        "confidence": 0.85,
                        "summary": "Ship.",
                        "reasoning": "...",
                        "findings": [],
                        "recommendation": "Ship.",
                    }
                ),
            }
        ),
        encoding="utf-8",
    )
    parsed = magi_dispatch._tolerant_agent_parse(raw)
    assert parsed["agent"] == "caspar"
    assert parsed["verdict"] == "approve"


def test_tolerant_agent_parse_no_recoverable_json(tmp_path: Path) -> None:
    """F45.3: result with only narrative raises ValidationError with preview."""
    raw = tmp_path / "broken.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": "I encountered an error and could not produce a verdict for this run.",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as ei:
        magi_dispatch._tolerant_agent_parse(raw)
    assert "No JSON object recoverable" in str(ei.value)
    assert "encountered an error" in str(ei.value)


def test_tolerant_agent_parse_skips_code_examples(tmp_path: Path) -> None:
    """F45.4: parser skips embedded code-example dicts, finds verdict."""
    raw = tmp_path / "balthasar.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": (
                    'Here is an example structure: {"key": "val"}.\n'
                    'And another: {"name": "thing"}.\n\n'
                    '{"agent": "balthasar", "verdict": "approve", '
                    '"confidence": 0.88, "summary": "OK.", '
                    '"reasoning": "Reasonable trade-offs.", '
                    '"findings": [], "recommendation": "Ship."}'
                ),
            }
        ),
        encoding="utf-8",
    )
    parsed = magi_dispatch._tolerant_agent_parse(raw)
    assert parsed["agent"] == "balthasar"
    assert parsed["verdict"] == "approve"


def test_tolerant_agent_parse_rejects_unknown_verdict(tmp_path: Path) -> None:
    """F45.5 (iter 2 W2): unknown verdict in candidate dict is not accepted.

    Defense in depth against MAGI agents emitting verdict typos
    (e.g. ``"GO_LATER"``) that would otherwise weigh 0.0 in
    :func:`_manual_synthesis_recovery` and silently dilute consensus.
    Per spec sec.2.4 the recovery path requires ``agent`` field in the
    canonical name set AND ``verdict`` in the known verdict set; the
    iter 1 implementation only enforced the agent half.
    """
    raw = tmp_path / "melchior.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": json.dumps(
                    {
                        "agent": "melchior",
                        "verdict": "maybe",
                        "confidence": 0.5,
                        "summary": "Unsure.",
                        "reasoning": "...",
                        "findings": [],
                        "recommendation": "Re-run.",
                    }
                ),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError) as ei:
        magi_dispatch._tolerant_agent_parse(raw)
    assert "No JSON object recoverable" in str(ei.value)


def test_tolerant_agent_parse_skips_unknown_verdict_finds_valid(tmp_path: Path) -> None:
    """F45.6 (iter 2 W2): unknown-verdict candidate is skipped, valid one wins.

    When a result string carries multiple balanced JSON objects -- e.g.
    a stale draft with ``verdict: "maybe"`` followed by the corrected
    final verdict -- the parser must walk past the typo and accept the
    valid candidate that follows. Mirrors the F45.4 code-example skip
    pattern but for the verdict-set axis.
    """
    raw = tmp_path / "balthasar.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": (
                    'Draft attempt: {"agent": "balthasar", "verdict": "perhaps"}.\n\n'
                    'Final: {"agent": "balthasar", "verdict": "approve", '
                    '"confidence": 0.8, "summary": "OK.", "reasoning": "...", '
                    '"findings": [], "recommendation": "Ship."}'
                ),
            }
        ),
        encoding="utf-8",
    )
    parsed = magi_dispatch._tolerant_agent_parse(raw)
    assert parsed["agent"] == "balthasar"
    assert parsed["verdict"] == "approve"


def test_tolerant_agent_parse_accepts_synthesis_label(tmp_path: Path) -> None:
    """F45.7 (iter 2 W2): synthesis labels (STRONG_GO/...) are valid verdicts.

    Per-agent JSON sometimes carries a synthesis-style label rather than
    the lowercase agent verdict (the canonical contract has agents emit
    ``approve`` / ``conditional`` / ``reject`` but historical fixtures
    show MAGI synthesizer crash recovery payloads carrying
    ``GO_WITH_CAVEATS`` directly). The known-verdict set must include
    both axes so legitimate recovery payloads are not rejected.
    """
    raw = tmp_path / "caspar.raw.json"
    raw.write_text(
        json.dumps(
            {
                "type": "result",
                "result": json.dumps(
                    {
                        "agent": "caspar",
                        "verdict": "GO_WITH_CAVEATS",
                        "confidence": 0.75,
                        "summary": "Caveats.",
                        "reasoning": "...",
                        "findings": [],
                        "recommendation": "Ship with caveats.",
                    }
                ),
            }
        ),
        encoding="utf-8",
    )
    parsed = magi_dispatch._tolerant_agent_parse(raw)
    assert parsed["agent"] == "caspar"
    assert parsed["verdict"] == "GO_WITH_CAVEATS"
