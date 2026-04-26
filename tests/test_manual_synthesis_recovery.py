#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.4.0 Feature F manual synthesis recovery (F46)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import magi_dispatch  # noqa: E402
from errors import MAGIGateError  # noqa: E402


def _write_raw_agent(path: Path, agent: str, verdict: str, *, preamble: bool = True) -> None:
    """Write an agent ``*.raw.json`` envelope with optional narrative preamble.

    Mirrors the shape MAGI 2.2.x emits per agent: outer envelope
    ``{"type": "result", "result": <string>}`` where ``result`` is either
    a JSON-encoded verdict dict (preamble=False) or a narrative preamble
    followed by the JSON dict (preamble=True). Used by the F46 tests as a
    fixture builder so each test stays focused on the behavior it asserts.
    """
    body = {
        "agent": agent,
        "verdict": verdict,
        "confidence": 0.88,
        "summary": f"{agent} verdict {verdict}",
        "reasoning": "...",
        "findings": [],
        "recommendation": ("Ship." if verdict in ("approve", "GO", "GO_WITH_CAVEATS") else "HOLD."),
    }
    if preamble:
        result = f"Based on my review...\n\n{json.dumps(body)}"
    else:
        result = json.dumps(body)
    path.write_text(json.dumps({"type": "result", "result": result}), encoding="utf-8")


def test_manual_synthesis_recovers_with_two_agents(tmp_path: Path) -> None:
    """F46.1: synthesizer crashed but 2/3 agents have valid raw JSON."""
    _write_raw_agent(tmp_path / "melchior.raw.json", "melchior", "approve", preamble=True)
    _write_raw_agent(tmp_path / "balthasar.raw.json", "balthasar", "approve", preamble=True)
    _write_raw_agent(tmp_path / "caspar.raw.json", "caspar", "approve", preamble=False)
    verdict = magi_dispatch._manual_synthesis_recovery(tmp_path)
    assert verdict.verdict in ("GO", "STRONG_GO")
    assert (tmp_path / "manual-synthesis.json").exists()
    report = json.loads((tmp_path / "manual-synthesis.json").read_text(encoding="utf-8"))
    assert report["recovered"] is True
    assert report["recovery_reason"] == "synthesizer-failure"


def test_manual_synthesis_preserves_dissent(tmp_path: Path) -> None:
    """F46.2: 2-1 majority recovers GO-or-better with dissent visible."""
    _write_raw_agent(tmp_path / "melchior.raw.json", "melchior", "reject")
    _write_raw_agent(tmp_path / "balthasar.raw.json", "balthasar", "approve")
    _write_raw_agent(tmp_path / "caspar.raw.json", "caspar", "approve")
    verdict = magi_dispatch._manual_synthesis_recovery(tmp_path)
    # 2 approves + 1 reject => score = (1 + 1 - 1) / 3 ~= 0.33 -> GO
    assert verdict.verdict == "GO"
    report = json.loads((tmp_path / "manual-synthesis.json").read_text(encoding="utf-8"))
    assert report["consensus"]["approves"] == 2
    assert report["consensus"]["rejects"] == 1


def test_manual_synthesis_raises_when_zero_recoverable(tmp_path: Path) -> None:
    """F46.3: all agents broken -> MAGIGateError."""
    (tmp_path / "melchior.raw.json").write_text(
        json.dumps({"type": "result", "result": "broken"}),
        encoding="utf-8",
    )
    (tmp_path / "balthasar.raw.json").write_text(
        json.dumps({"type": "result", "result": "broken"}),
        encoding="utf-8",
    )
    with pytest.raises(MAGIGateError) as ei:
        magi_dispatch._manual_synthesis_recovery(tmp_path)
    assert "No recoverable agent verdicts" in str(ei.value)


def test_invoke_magi_auto_recovers_on_synthesizer_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    """F46.4: invoke_magi auto-invokes recovery when run_magi.py crashes."""
    import re as _re

    import subprocess_utils

    captured: dict[str, Path] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        prompt = cmd[-1]
        m = _re.search(r"--output-dir (\S+)", prompt)
        assert m is not None
        out = Path(m.group(1))
        out.mkdir(parents=True, exist_ok=True)
        _write_raw_agent(out / "melchior.raw.json", "melchior", "approve")
        _write_raw_agent(out / "balthasar.raw.json", "balthasar", "approve")
        _write_raw_agent(out / "caspar.raw.json", "caspar", "approve")
        captured["dir"] = out
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="RuntimeError: Only 2 agent(s) succeeded -- fewer than 3 required",
        )

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    verdict = magi_dispatch.invoke_magi(["@spec.md"])
    assert verdict.verdict in ("GO", "STRONG_GO", "GO_WITH_CAVEATS")
    # 3 agents recovered -> not degraded.
    assert verdict.degraded is False
    assert "dir" in captured


def test_invoke_magi_no_recovery_flag_skips_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """F46.5: allow_recovery=False suppresses auto-recovery."""
    import subprocess_utils

    def fake_run(cmd: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="RuntimeError: Only 1 agent(s) succeeded",
        )

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    with pytest.raises(MAGIGateError) as ei:
        magi_dispatch.invoke_magi(["@spec.md"], allow_recovery=False)
    assert "Only 1 agent(s)" in str(ei.value) or "/magi:magi failed" in str(ei.value)
