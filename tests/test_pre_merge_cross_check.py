#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for v1.0.0 Feature G MAGI cross-check meta-reviewer (sec.2.1).

Covers escenarios G1-G6 + carry-forward normalizer (W4) + JSON-parse-failure
distinct-from-dispatch-failure (melchior iter 4 W).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock


def test_g4_opt_out_via_config_returns_findings_unchanged(tmp_path):
    """G4: cross-check sub-phase short-circuits when magi_cross_check=False."""
    from pre_merge_cmd import _loop2_cross_check

    config = MagicMock()
    config.magi_cross_check = False

    findings = [
        {"severity": "CRITICAL", "title": "test", "detail": "...", "agent": "caspar"},
    ]
    diff = "stub diff"
    verdict = "GO_WITH_CAVEATS"

    result = _loop2_cross_check(
        diff=diff,
        verdict=verdict,
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    assert result == findings  # unchanged
    # Audit dir empty (no artifact written when skipped)
    assert list(tmp_path.iterdir()) == []


def test_g1_cross_check_annotates_false_positive_critical_with_reject(tmp_path, monkeypatch):
    """G1: cross-check annotates CRITICAL marked false-positive (REJECT) but never drops it."""
    from pre_merge_cmd import _loop2_cross_check

    captured_args: dict = {}

    def fake_dispatch(*, diff, prompt, **_kw):
        captured_args["prompt"] = prompt
        captured_args["diff"] = diff
        return {
            "decisions": [
                {
                    "original_index": 0,
                    "decision": "REJECT",
                    "rationale": "phase arg validated at line N",
                }
            ],
        }

    monkeypatch.setattr("pre_merge_cmd._dispatch_requesting_code_review", fake_dispatch)

    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {
            "severity": "CRITICAL",
            "title": "false positive",
            "detail": "auto_cmd doesn't validate phase arg",
            "agent": "caspar",
        },
    ]
    result = _loop2_cross_check(
        diff="stub",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    # Length preserved (annotation-only redesign per CRITICAL #1+#4).
    assert len(result) == len(findings)
    # Original severity unchanged.
    assert result[0]["severity"] == "CRITICAL"
    # Annotation attached.
    assert result[0]["cross_check_decision"] == "REJECT"
    assert "phase arg validated" in result[0]["cross_check_rationale"]
    # Prompt references MAGI verdict + verdict value.
    assert "MAGI verdict" in captured_args["prompt"]
    assert "GO_WITH_CAVEATS" in captured_args["prompt"]


def test_g2_cross_check_annotates_valid_critical_with_keep(tmp_path, monkeypatch):
    """G2: review classifies CRITICAL as KEEP -> finding annotated, not removed."""
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {
            "decisions": [
                {
                    "original_index": 0,
                    "decision": "KEEP",
                    "rationale": "missing assertion confirmed at line X",
                }
            ]
        },
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {
            "severity": "CRITICAL",
            "title": "valid issue",
            "detail": "missing assertion at X",
            "agent": "melchior",
        }
    ]
    result = _loop2_cross_check(
        diff="x",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    # Length preserved.
    assert len(result) == len(findings)
    # Original severity unchanged.
    assert result[0]["severity"] == "CRITICAL"
    # Annotation fields attached.
    assert result[0]["cross_check_decision"] == "KEEP"
    assert "missing assertion" in result[0]["cross_check_rationale"]
    assert result[0]["cross_check_recommended_severity"] is None


def test_g3_cross_check_annotates_warning_with_downgrade_recommendation(tmp_path, monkeypatch):
    """G3: DOWNGRADE recorded as annotation; original severity preserved."""
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {
            "decisions": [
                {
                    "original_index": 0,
                    "decision": "DOWNGRADE",
                    "rationale": "polish concern, not high-impact",
                    "recommended_severity": "INFO",
                }
            ]
        },
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {
            "severity": "WARNING",
            "title": "naming polish",
            "detail": "rename for clarity",
            "agent": "balthasar",
        }
    ]
    result = _loop2_cross_check(
        diff="x",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    # Length preserved.
    assert len(result) == len(findings)
    # Original severity preserved (annotation-only redesign).
    assert result[0]["severity"] == "WARNING"
    # Recommendation surfaced via annotation, not by mutation.
    assert result[0]["cross_check_decision"] == "DOWNGRADE"
    assert result[0]["cross_check_recommended_severity"] == "INFO"


def test_g5_cross_check_failure_returns_original_findings(tmp_path, monkeypatch, capsys):
    """G5: dispatch failure -> graceful fallback, no block, no annotation."""
    from pre_merge_cmd import _loop2_cross_check

    def failing_dispatch(**_kw):
        raise RuntimeError("subprocess timeout")

    monkeypatch.setattr("pre_merge_cmd._dispatch_requesting_code_review", failing_dispatch)
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "CRITICAL", "title": "x", "detail": "...", "agent": "caspar"}]
    result = _loop2_cross_check(
        diff="x",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    assert result == findings  # original returned, no annotations attached
    captured = capsys.readouterr()
    assert "[sbtdd magi-cross-check] failed" in captured.err
    # Audit artifact records cross_check_failed
    audit_files = list(tmp_path.glob("iter1-*.json"))
    assert len(audit_files) == 1
    audit = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert audit["cross_check_failed"] is True


def test_g6_cross_check_audit_artifact_schema(tmp_path, monkeypatch):
    """G6: audit JSON has annotated_findings (not filtered_findings) per redesign."""
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {
            "decisions": [
                {
                    "original_index": 0,
                    "decision": "REJECT",
                    "rationale": "false positive",
                }
            ]
        },
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "CRITICAL", "title": "x", "detail": "...", "agent": "caspar"}]
    _loop2_cross_check(
        diff="diff content",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=2,
        config=config,
        audit_dir=tmp_path,
    )
    audit_files = list(tmp_path.glob("iter2-*.json"))
    assert len(audit_files) == 1
    audit = json.loads(audit_files[0].read_text(encoding="utf-8"))
    assert audit["iter"] == 2
    assert "timestamp" in audit
    assert audit["magi_verdict"] == "GO_WITH_CAVEATS"
    assert audit["original_findings"] == findings
    assert len(audit["cross_check_decisions"]) == 1
    # Annotation redesign: annotated_findings replaces filtered_findings;
    # length preserved (REJECT no longer drops).
    assert "annotated_findings" in audit
    assert "filtered_findings" not in audit
    assert len(audit["annotated_findings"]) == len(findings)
    assert audit["annotated_findings"][0]["cross_check_decision"] == "REJECT"


def test_g6_audit_serializes_null_for_keep_and_reject(tmp_path, monkeypatch):
    """G6 (melchior iter 2 WARNING): KEEP/REJECT decisions serialize
    cross_check_recommended_severity=null in audit; only DOWNGRADE carries a value.
    """
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {
            "decisions": [
                {
                    "original_index": 0,
                    "decision": "KEEP",
                    "rationale": "valid concern, severity correct",
                },
                {
                    "original_index": 1,
                    "decision": "REJECT",
                    "rationale": "false positive, no underlying issue",
                },
                {
                    "original_index": 2,
                    "decision": "DOWNGRADE",
                    "rationale": "polish, not blocking",
                    "recommended_severity": "INFO",
                },
            ]
        },
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {
            "severity": "CRITICAL",
            "title": "valid",
            "detail": "...",
            "agent": "melchior",
        },
        {
            "severity": "CRITICAL",
            "title": "fp",
            "detail": "...",
            "agent": "balthasar",
        },
        {
            "severity": "WARNING",
            "title": "polish",
            "detail": "...",
            "agent": "caspar",
        },
    ]
    _loop2_cross_check(
        diff="x",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=3,
        config=config,
        audit_dir=tmp_path,
    )
    audit_files = list(tmp_path.glob("iter3-*.json"))
    assert len(audit_files) == 1
    audit = json.loads(audit_files[0].read_text(encoding="utf-8"))
    annotated = audit["annotated_findings"]
    for entry in annotated:
        decision = entry["cross_check_decision"]
        if decision in ("KEEP", "REJECT"):
            # Field MUST be present in serialized JSON and equal to None
            # (i.e., null), not absent.
            assert "cross_check_recommended_severity" in entry
            assert entry["cross_check_recommended_severity"] is None
        elif decision == "DOWNGRADE":
            assert entry["cross_check_recommended_severity"] in ("WARNING", "INFO")


def test_g6_json_parse_failure_distinct_from_dispatch_failure(tmp_path, monkeypatch):
    """G6 (melchior iter 4 W): JSON parse failure surfaces as
    dispatch_failure block, distinct from cross_check_failed.
    """
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {
            "decisions": [],
            "_dispatch_failure": "json_parse_error",
            "_failure_reason": "Expecting value: line 1 column 1",
        },
    )
    config = MagicMock()
    config.magi_cross_check = True
    findings = [{"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "z"}]
    _loop2_cross_check(
        diff="x",
        verdict="GO_WITH_CAVEATS",
        findings=findings,
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    audit_files = list(tmp_path.glob("iter1-*.json"))
    assert len(audit_files) == 1
    audit = json.loads(audit_files[0].read_text(encoding="utf-8"))
    # dispatch_failure block surfaces json_parse_error mode separately.
    assert audit.get("dispatch_failure", {}).get("kind") == "json_parse_error"
    assert "Expecting value" in audit["dispatch_failure"]["reason"]
    # cross_check_failed must NOT be set for this distinct mode.
    assert audit.get("cross_check_failed") is not True
    # Findings unchanged because parse failed (no review ran).
    assert audit["original_findings"] == findings


def test_dispatch_invokes_superpowers_requesting_code_review(monkeypatch):
    """S1-4: _dispatch_requesting_code_review delegates to superpowers wrapper.

    Real wiring: parses the skill's stdout as JSON. Returns decisions dict.
    """
    from pre_merge_cmd import _dispatch_requesting_code_review

    captured: dict = {}

    class _FakeResult:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout
            self.stderr = ""
            self.returncode = 0

    def fake_invoke(args=None, timeout=None, cwd=None, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _FakeResult(
            '{"decisions": [{"original_index": 0, "decision": "KEEP", "rationale": "ok"}]}'
        )

    monkeypatch.setattr("superpowers_dispatch.requesting_code_review", fake_invoke)
    result = _dispatch_requesting_code_review(diff="diff", prompt="meta-prompt")
    assert "decisions" in result
    assert result["decisions"][0]["decision"] == "KEEP"


def test_dispatch_returns_json_parse_error_marker_on_malformed_output(monkeypatch, capsys):
    """S1-4: dispatch surfaces _dispatch_failure='json_parse_error' when stdout malformed."""
    from pre_merge_cmd import _dispatch_requesting_code_review

    class _FakeResult:
        def __init__(self, stdout: str) -> None:
            self.stdout = stdout
            self.stderr = ""
            self.returncode = 0

    monkeypatch.setattr(
        "superpowers_dispatch.requesting_code_review",
        lambda **_kw: _FakeResult("not json at all"),
    )
    result = _dispatch_requesting_code_review(diff="x", prompt="y")
    assert result["_dispatch_failure"] == "json_parse_error"
    assert "decisions" in result
    assert result["decisions"] == []
    captured = capsys.readouterr()
    assert "malformed JSON" in captured.err


def test_w4_normalize_strips_cross_check_annotation_fields():
    """W4 (caspar iter 4): annotation fields stripped before carry-forward."""
    from pre_merge_cmd import _normalize_findings_for_carry_forward

    annotated = [
        {
            "severity": "CRITICAL",
            "title": "x",
            "detail": "y",
            "agent": "z",
            "cross_check_decision": "REJECT",
            "cross_check_rationale": "false positive at line N",
            "cross_check_recommended_severity": None,
            "_dispatch_failure": "json_parse_error",
            "_failure_reason": "Expecting value",
        },
    ]
    normalized = _normalize_findings_for_carry_forward(annotated)
    assert len(normalized) == 1
    f = normalized[0]
    # Original fields preserved
    assert f["severity"] == "CRITICAL"
    assert f["title"] == "x"
    assert f["detail"] == "y"
    assert f["agent"] == "z"
    # Annotation + diagnostic fields stripped
    assert "cross_check_decision" not in f
    assert "cross_check_rationale" not in f
    assert "cross_check_recommended_severity" not in f
    assert "_dispatch_failure" not in f
    assert "_failure_reason" not in f
