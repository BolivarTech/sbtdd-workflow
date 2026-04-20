#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for magi_dispatch module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "magi-outputs"


def test_magi_verdict_is_frozen_dataclass():
    from dataclasses import FrozenInstanceError

    from magi_dispatch import MAGIVerdict

    v = MAGIVerdict(
        verdict="GO",
        degraded=False,
        conditions=(),
        findings=(),
        raw_output="",
    )
    with pytest.raises(FrozenInstanceError):
        v.verdict = "HOLD"  # type: ignore[misc]


def test_parse_verdict_accepts_all_six_known_labels():
    from magi_dispatch import parse_verdict

    for label in (
        "STRONG_NO_GO",
        "HOLD",
        "HOLD_TIE",
        "GO_WITH_CAVEATS",
        "GO",
        "STRONG_GO",
    ):
        payload = {
            "verdict": label,
            "degraded": False,
            "conditions": [],
            "findings": [],
        }
        parsed = parse_verdict(json.dumps(payload))
        assert parsed.verdict == label


def test_parse_verdict_normalises_spaces_to_underscores():
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "GO WITH CAVEATS",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "GO_WITH_CAVEATS"


def test_parse_verdict_rejects_unknown_label():
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "MAYBE",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    with pytest.raises(ValidationError, match="MAYBE"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_missing_verdict_field():
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    with pytest.raises(ValidationError, match="verdict"):
        parse_verdict(json.dumps({"degraded": False}))


def test_parse_verdict_rejects_non_json():
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    with pytest.raises(ValidationError, match="JSON"):
        parse_verdict("not valid json at all")


def test_parse_verdict_degraded_flag_preserved():
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "GO",
        "degraded": True,
        "conditions": [],
        "findings": [],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.degraded is True


def test_parse_verdict_extracts_conditions_and_findings_as_tuples():
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "GO_WITH_CAVEATS",
        "degraded": False,
        "conditions": ["doc test edge case", "add audit log"],
        "findings": [{"severity": "INFO", "message": "consider renaming"}],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.conditions == ("doc test edge case", "add audit log")
    assert len(parsed.findings) == 1
    assert parsed.findings[0]["severity"] == "INFO"
    # Immutability: conditions is tuple.
    assert isinstance(parsed.conditions, tuple)


def test_parse_verdict_loads_from_fixture_go_full():
    from magi_dispatch import parse_verdict

    parsed = parse_verdict((FIXTURES / "go_full.json").read_text(encoding="utf-8"))
    assert parsed.verdict == "GO"
    assert parsed.degraded is False


def test_parse_verdict_loads_from_fixture_degraded():
    from magi_dispatch import parse_verdict

    parsed = parse_verdict((FIXTURES / "go_with_caveats_degraded.json").read_text(encoding="utf-8"))
    assert parsed.verdict == "GO_WITH_CAVEATS"
    assert parsed.degraded is True


def test_parse_verdict_loads_from_fixture_strong_no_go():
    from magi_dispatch import parse_verdict

    parsed = parse_verdict((FIXTURES / "strong_no_go_full.json").read_text(encoding="utf-8"))
    assert parsed.verdict == "STRONG_NO_GO"


def test_parse_verdict_rejects_unknown_fixture():
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    with pytest.raises(ValidationError):
        parse_verdict((FIXTURES / "unknown_verdict.json").read_text(encoding="utf-8"))


# Strict normalisation edge cases (MAGI Checkpoint 2 iter 1 WARNING -- caspar).


def test_parse_verdict_rejects_lowercase_label():
    """Lowercase input must NOT be silently normalised to uppercase."""
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "go with caveats",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_mixed_case_label():
    """Mixed case ('Go_With_Caveats') must be rejected."""
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "Go_With_Caveats",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_strips_leading_trailing_whitespace():
    """Leading/trailing whitespace is stripped before validation."""
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "  GO_WITH_CAVEATS  ",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "GO_WITH_CAVEATS"


def test_parse_verdict_rejects_empty_label():
    """Empty or whitespace-only verdict string is rejected."""
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "   ",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    with pytest.raises(ValidationError, match="empty"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_normalises_hyphenated_label():
    """Hyphens in labels are converted to underscores ('STRONG-NO-GO')."""
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "STRONG-NO-GO",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "STRONG_NO_GO"


def test_parse_verdict_rejects_label_with_punctuation():
    """Punctuation beyond underscore/hyphen is rejected."""
    from errors import ValidationError
    from magi_dispatch import parse_verdict

    payload = {
        "verdict": "GO!WITH!CAVEATS",
        "degraded": False,
        "conditions": [],
        "findings": [],
    }
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))


def test_invoke_magi_returns_verdict_on_success(monkeypatch):
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = '{"verdict": "GO", "degraded": false, "conditions": [], "findings": []}'
        stderr = ""

    captured: dict = {}

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    v = invoke_magi(context_paths=["spec.md", "plan.md"])
    assert v.verdict == "GO"
    # Command must be a list (shell=False), include magi reference.
    assert isinstance(captured["cmd"], list)
    assert any("magi" in tok for tok in captured["cmd"])


def test_invoke_magi_wraps_timeout_as_magi_gate_error(monkeypatch):
    import subprocess

    from errors import MAGIGateError
    from magi_dispatch import invoke_magi

    def fake_run(cmd, timeout, capture=True, cwd=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(MAGIGateError, match="timed out"):
        invoke_magi(context_paths=["spec.md"])


def test_invoke_magi_raises_quota_on_quota_pattern(monkeypatch):
    from errors import QuotaExhaustedError
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "You've hit your session limit - resets 3:45pm"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(QuotaExhaustedError):
        invoke_magi(context_paths=["spec.md"])


def test_invoke_magi_non_quota_nonzero_raises_magi_gate_error(monkeypatch):
    from errors import MAGIGateError
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 3
        stdout = ""
        stderr = "consensus agent failure"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(MAGIGateError, match="returncode=3"):
        invoke_magi(context_paths=["spec.md"])
