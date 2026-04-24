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


def _extract_output_dir(cmd: list[str]) -> str:
    """Pull ``--output-dir <path>`` out of the claude ``-p`` prompt string.

    The new ``_build_magi_cmd`` packs the slash command, its ``@file`` refs,
    and the MAGI flags into a single prompt (``cmd[-1]``) because ``claude``
    does not accept ``--output-dir`` as its own CLI flag -- the flag belongs
    to MAGI and must travel through the prompt so the sub-session forwards
    it to ``run_magi.py``.
    """
    tokens = cmd[-1].split()
    return tokens[tokens.index("--output-dir") + 1]


def _magi_report_payload(consensus_label: str = "GO (2-1)", degraded: bool = False) -> dict:
    """Build a minimal magi-report.json payload matching run_magi.py:445."""
    payload: dict = {
        "agents": [],
        "consensus": {
            "consensus": consensus_label,
            "consensus_verdict": "approve",
            "conditions": [],
            "findings": [],
            "recommendations": {},
            "dissent": [],
        },
    }
    if degraded:
        payload["degraded"] = True
        payload["failed_agents"] = ["caspar"]
    return payload


def test_invoke_magi_returns_verdict_on_success(monkeypatch):
    """Happy path: MAGI writes magi-report.json to --output-dir, we parse it."""
    from magi_dispatch import invoke_magi

    captured: dict = {}

    class FakeProc:
        returncode = 0
        stdout = "+==== ASCII banner ====+\n| GO (2-1) |\n"
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured["cmd"] = cmd
        # The new contract: MAGI writes <output-dir>/magi-report.json.
        # Locate the --output-dir arg and drop the report there.
        output_dir = _extract_output_dir(cmd)
        (Path(output_dir) / "magi-report.json").write_text(
            json.dumps(_magi_report_payload(consensus_label="GO (2-1)")),
            encoding="utf-8",
        )
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    v = invoke_magi(context_paths=["spec.md", "plan.md"])
    assert v.verdict == "GO"
    assert v.degraded is False
    # Command must be a list (shell=False) ending in a single prompt string
    # containing the slash command + @-refs + --output-dir flag.
    assert isinstance(captured["cmd"], list)
    assert captured["cmd"][:2] == ["claude", "-p"]
    prompt = captured["cmd"][-1]
    assert "/magi:magi" in prompt
    assert "--output-dir" in prompt


def test_invoke_magi_strips_split_suffix_from_label(monkeypatch):
    """MAGI banner labels like 'HOLD (2-1)' must normalise to 'HOLD'."""
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        output_dir = _extract_output_dir(cmd)
        (Path(output_dir) / "magi-report.json").write_text(
            json.dumps(_magi_report_payload(consensus_label="HOLD (2-1)")),
            encoding="utf-8",
        )
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    v = invoke_magi(context_paths=["spec.md"])
    assert v.verdict == "HOLD"


def test_invoke_magi_reads_degraded_flag_from_report(monkeypatch):
    """INV-28: top-level 'degraded' flag in magi-report.json is surfaced."""
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        output_dir = _extract_output_dir(cmd)
        (Path(output_dir) / "magi-report.json").write_text(
            json.dumps(_magi_report_payload(consensus_label="GO (2-0)", degraded=True)),
            encoding="utf-8",
        )
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    v = invoke_magi(context_paths=["spec.md"])
    assert v.degraded is True


def test_invoke_magi_raises_when_report_missing(monkeypatch):
    """Returncode 0 with no magi-report.json on disk is a contract violation."""
    from errors import MAGIGateError
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(MAGIGateError, match="magi-report.json"):
        invoke_magi(context_paths=["spec.md"])


def test_invoke_magi_raises_validation_on_malformed_report(monkeypatch):
    """Malformed JSON on disk raises ValidationError, not MAGIGateError."""
    from errors import ValidationError
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        output_dir = _extract_output_dir(cmd)
        (Path(output_dir) / "magi-report.json").write_text("not-valid-json{", encoding="utf-8")
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(ValidationError, match="malformed"):
        invoke_magi(context_paths=["spec.md"])


def test_parse_magi_report_extracts_conditions_as_strings():
    """consensus.conditions is a list of {agent, condition} dicts; we want strings."""
    from magi_dispatch import parse_magi_report

    report = {
        "consensus": {
            "consensus": "GO WITH CAVEATS (3-0)",
            "conditions": [
                {"agent": "melchior", "condition": "add unit test for edge case"},
                {"agent": "balthasar", "condition": "document trade-off in readme"},
            ],
            "findings": [],
        },
    }
    v = parse_magi_report(report)
    assert v.verdict == "GO_WITH_CAVEATS"
    assert v.conditions == (
        "add unit test for edge case",
        "document trade-off in readme",
    )


def test_parse_magi_report_handles_strong_no_go_no_split_suffix():
    """STRONG GO / STRONG NO-GO / HOLD -- TIE have no (N-M) suffix."""
    from magi_dispatch import parse_magi_report

    for label, expected in (
        ("STRONG GO", "STRONG_GO"),
        ("STRONG NO-GO", "STRONG_NO_GO"),
        ("HOLD -- TIE", "HOLD_TIE"),
    ):
        report = {"consensus": {"consensus": label, "conditions": [], "findings": []}}
        assert parse_magi_report(report).verdict == expected


def test_parse_magi_report_rejects_missing_consensus():
    from errors import ValidationError
    from magi_dispatch import parse_magi_report

    with pytest.raises(ValidationError, match="consensus"):
        parse_magi_report({"agents": []})


def test_parse_magi_report_rejects_unknown_label():
    from errors import ValidationError
    from magi_dispatch import parse_magi_report

    report = {"consensus": {"consensus": "MAYBE (1-1)", "conditions": [], "findings": []}}
    with pytest.raises(ValidationError, match="MAYBE"):
        parse_magi_report(report)


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


def test_verdict_passes_gate_strong_go_full_passes():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("STRONG_GO", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is True


def test_verdict_passes_gate_go_full_passes():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("GO", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is True


def test_verdict_passes_gate_below_threshold_fails():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("HOLD", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is False


def test_verdict_passes_gate_degraded_always_fails_even_strong_go():
    """INV-28: degraded verdicts NEVER count as gate-pass (except STRONG_NO_GO abort)."""
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("STRONG_GO", True, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is False


def test_verdict_is_strong_no_go_returns_true_for_strong_no_go():
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go

    assert verdict_is_strong_no_go(MAGIVerdict("STRONG_NO_GO", False, (), (), "")) is True


def test_verdict_is_strong_no_go_true_even_when_degraded():
    """INV-28 exception: STRONG_NO_GO degraded still aborts."""
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go

    assert verdict_is_strong_no_go(MAGIVerdict("STRONG_NO_GO", True, (), (), "")) is True


def test_verdict_is_strong_no_go_false_for_other_verdicts():
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go

    for label in ("HOLD", "HOLD_TIE", "GO_WITH_CAVEATS", "GO", "STRONG_GO"):
        assert verdict_is_strong_no_go(MAGIVerdict(label, False, (), (), "")) is False


def test_verdict_passes_gate_rejects_unknown_threshold():
    """Unknown threshold raises ValidationError (MAGI ckpt2 iter 1 WARNING -- melchior).

    Per Milestone A ``errors.py``, schema violations (including unrecognised
    threshold labels) are ``ValidationError``. The previous ``(ValidationError,
    KeyError)`` tuple was ambiguous; the contract is now strict.
    """
    from errors import ValidationError
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("GO", False, (), (), "")
    with pytest.raises(ValidationError, match="threshold"):
        verdict_passes_gate(v, threshold="MAYBE")


def test_verdict_passes_gate_rejects_lowercase_threshold():
    """Threshold must be uppercase enum member; lowercase rejected."""
    from errors import ValidationError
    from magi_dispatch import MAGIVerdict, verdict_passes_gate

    v = MAGIVerdict("GO", False, (), (), "")
    with pytest.raises(ValidationError):
        verdict_passes_gate(v, threshold="go_with_caveats")


def test_write_verdict_artifact_creates_parent_directories(tmp_path):
    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict(
        "GO_WITH_CAVEATS",
        False,
        conditions=("fix edge case",),
        findings=(),
        raw_output='{"verdict":"GO_WITH_CAVEATS"}',
    )
    target = tmp_path / ".claude" / "magi-verdict.json"
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["verdict"] == "GO_WITH_CAVEATS"
    assert data["degraded"] is False
    assert data["conditions"] == ["fix edge case"]
    assert data["timestamp"] == "2026-04-19T10:00:00Z"


def test_write_verdict_artifact_is_atomic(tmp_path):
    """write fails -> no partial file, no tmp leak."""
    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict("GO", False, (), (), "")
    target = tmp_path / "subdir" / "verdict.json"
    # Parent doesn't exist; function MUST create it.
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    assert target.exists()
    # No stray tmp files.
    assert list(target.parent.glob("*.tmp.*")) == []


def test_write_verdict_artifact_preserves_degraded_flag(tmp_path):
    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict("GO", True, (), (), "")
    target = tmp_path / "verdict.json"
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["degraded"] is True


def test_write_verdict_artifact_rejects_invalid_timestamp(tmp_path):
    """Non-ISO-8601 timestamp must raise ValidationError (Finding 2, melchior).

    MAGI Loop 2 Milestone B iter 1 Finding 2: previously the function
    accepted any string as ``timestamp`` and persisted it verbatim. A
    caller passing garbage (eg. 'not-a-timestamp') wrote a malformed
    artifact that the ``finalize`` subcommand would then be expected to
    parse, corrupting the downstream gate. The function now validates
    against the same ISO 8601 contract used by state_file.py.
    """
    from errors import ValidationError
    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict("GO", False, (), (), "")
    target = tmp_path / "verdict.json"
    with pytest.raises(ValidationError, match="ISO 8601"):
        write_verdict_artifact(v, target, timestamp="not-a-timestamp")
    # Bad input must NOT leave a partial artifact behind.
    assert not target.exists()


def test_write_verdict_artifact_defaults_timestamp_to_now(tmp_path):
    """When timestamp is None the function stamps UTC ISO 8601 with Z suffix.

    MAGI Loop 2 Milestone B iter 1 Finding 2: makes timestamp optional
    so hot-path callers don't need to recompute the canonical form
    everywhere. The default is ``datetime.now(timezone.utc)`` rendered
    with the project's ``Z`` suffix.
    """
    import re

    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict("GO", False, (), (), "")
    target = tmp_path / "verdict.json"
    write_verdict_artifact(v, target, timestamp=None)
    data = json.loads(target.read_text(encoding="utf-8"))
    # Same regex state_file.py uses.
    iso_re = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
    assert iso_re.match(data["timestamp"]), (
        f"default timestamp '{data['timestamp']}' is not ISO 8601 with timezone"
    )


def test_write_verdict_artifact_accepts_valid_iso_timestamp(tmp_path):
    """Valid ISO 8601 with Z suffix is accepted and persisted verbatim."""
    from magi_dispatch import MAGIVerdict, write_verdict_artifact

    v = MAGIVerdict("GO", False, (), (), "")
    target = tmp_path / "verdict.json"
    write_verdict_artifact(v, target, timestamp="2026-04-19T16:30:00Z")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["timestamp"] == "2026-04-19T16:30:00Z"
