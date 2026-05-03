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
from pathlib import Path
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


def test_loop2_with_cross_check_invokes_cross_check_on_findings(tmp_path, monkeypatch):
    """S1-5: _loop2_with_cross_check threads findings through _loop2_cross_check."""
    from pre_merge_cmd import _loop2_with_cross_check

    cross_check_calls = {"count": 0}

    def fake_cross_check(*, findings, **_kw):
        cross_check_calls["count"] += 1
        # Annotate to simulate KEEP for the single finding.
        return [{**f, "cross_check_decision": "KEEP"} for f in findings]

    monkeypatch.setattr("pre_merge_cmd._loop2_cross_check", fake_cross_check)

    config = MagicMock()
    config.magi_cross_check = True

    fake_findings = [{"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "z"}]
    fake_verdict = "GO_WITH_CAVEATS"

    def fake_invoke_magi(**_kw):
        return (fake_verdict, fake_findings)

    monkeypatch.setattr("pre_merge_cmd._invoke_magi_loop2", fake_invoke_magi)

    result_verdict, result_findings = _loop2_with_cross_check(
        diff="x",
        iter_n=1,
        config=config,
        audit_dir=tmp_path,
    )
    assert cross_check_calls["count"] == 1
    assert result_verdict == fake_verdict
    assert len(result_findings) == 1
    assert result_findings[0]["cross_check_decision"] == "KEEP"


def test_g4_breadcrumb_emitted_when_cross_check_disabled(monkeypatch, capsys, tmp_path):
    """G4 stderr breadcrumb (spec sec.2.1 impl note): one-time
    breadcrumb when magi_cross_check=False so operators see cross-check OFF."""
    from pre_merge_cmd import (
        _emit_cross_check_disabled_breadcrumb_once,
        _reset_cross_check_breadcrumb_for_tests,
    )

    _reset_cross_check_breadcrumb_for_tests()

    config = MagicMock()
    config.magi_cross_check = False

    _emit_cross_check_disabled_breadcrumb_once(config)
    captured = capsys.readouterr()
    assert "cross-check is OFF" in captured.err

    # Second call: deduped (no further output)
    _emit_cross_check_disabled_breadcrumb_once(config)
    captured2 = capsys.readouterr()
    assert captured2.err == ""

    _reset_cross_check_breadcrumb_for_tests()


def test_s1_6_auto_phase4_passes_audit_dir_to_cross_check(tmp_path, monkeypatch):
    """S1-6: auto_cmd phase 4 passes .claude/magi-cross-check/ as audit_dir."""
    from auto_cmd import _phase4_pre_merge_audit_dir

    root = tmp_path
    (root / ".claude").mkdir()

    audit_dir = _phase4_pre_merge_audit_dir(root)
    assert audit_dir == root / ".claude" / "magi-cross-check"


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


# ---------------------------------------------------------------------------
# v1.0.0 O-2 Loop 1 review CRITICAL #1 (C1): Wire Feature G cross-check into
# the production _loop2 path. Spec sec.2.1 G1-G6 + INV-35 unenforceable
# without these tests because _loop2_cross_check is unit-tested but never
# invoked from _loop2 itself.
# ---------------------------------------------------------------------------


def _make_pluginconfig_for_loop2(*, magi_cross_check: bool, root):
    """Return a duck-typed PluginConfig stub suitable for _loop2.

    _loop2 reads ``magi_threshold``, ``magi_max_iterations``, ``plan_path``,
    and (post-C1 wiring) ``magi_cross_check``.
    """
    cfg = MagicMock()
    cfg.magi_threshold = "GO_WITH_CAVEATS"
    cfg.magi_max_iterations = 3
    cfg.plan_path = "planning/claude-plan-tdd.md"
    cfg.magi_cross_check = magi_cross_check
    return cfg


def _make_magi_verdict_with_findings(verdict_str, findings_tuple):
    """Return a real MAGIVerdict so dataclasses.replace works in the wiring."""
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=verdict_str,
        degraded=False,
        conditions=(),
        findings=findings_tuple,
        raw_output=f'{{"verdict": "{verdict_str}"}}',
    )


def _make_magi_verdict_with_findings_degraded(verdict_str, findings_tuple, degraded):
    """Variant for tests that need a specific degraded flag."""
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=verdict_str,
        degraded=degraded,
        conditions=(),
        findings=findings_tuple,
        raw_output=f'{{"verdict": "{verdict_str}"}}',
    )


def test_c1_loop2_invokes_cross_check_when_magi_cross_check_true(tmp_path, monkeypatch):
    """C1: _loop2 routes verdict.findings through _loop2_cross_check when enabled.

    The wiring must call _loop2_cross_check exactly once per MAGI iter when
    magi_cross_check=True, with the iter's verdict + findings + the
    .claude/magi-cross-check/ audit_dir.
    """
    import magi_dispatch
    import pre_merge_cmd

    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("# plan\n", encoding="utf-8")

    pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    findings_t = ({"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "caspar"},)
    fake_verdict = _make_magi_verdict_with_findings("GO", findings_t)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", lambda **_kw: fake_verdict)

    spy = {"calls": 0, "kwargs": None}

    def fake_cross_check(*, diff, verdict, findings, iter_n, config, audit_dir, **_kw):
        spy["calls"] += 1
        spy["kwargs"] = {
            "diff": diff,
            "verdict": verdict,
            "findings": findings,
            "iter_n": iter_n,
            "config": config,
            "audit_dir": audit_dir,
        }
        # Annotate findings to simulate KEEP.
        return [{**f, "cross_check_decision": "KEEP"} for f in findings]

    monkeypatch.setattr(pre_merge_cmd, "_loop2_cross_check", fake_cross_check)
    # Skip the F44.3 retried_agents persistence (no auto-run.json present).
    monkeypatch.setattr(pre_merge_cmd, "_persist_retried_agents_to_audit", lambda *_a, **_kw: None)

    cfg = _make_pluginconfig_for_loop2(magi_cross_check=True, root=tmp_path)
    result = pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)

    assert spy["calls"] == 1
    assert spy["kwargs"]["verdict"] == "GO"
    # findings list contains the same dict shape as MAGIVerdict.findings
    assert spy["kwargs"]["findings"] == [dict(findings_t[0])]
    assert spy["kwargs"]["iter_n"] == 1
    assert spy["kwargs"]["config"] is cfg
    assert spy["kwargs"]["audit_dir"] == tmp_path / ".claude" / "magi-cross-check"
    # Verdict object is reconstructed with annotated findings via
    # dataclasses.replace; downstream consumers (e.g. write_magi_findings_file)
    # see annotated_findings.
    assert result.findings[0]["cross_check_decision"] == "KEEP"


def test_c1_loop2_skips_cross_check_when_magi_cross_check_false(tmp_path, monkeypatch, capsys):
    """C1: _loop2 does NOT invoke _loop2_cross_check when opted-out."""
    import magi_dispatch
    import pre_merge_cmd

    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("# plan\n", encoding="utf-8")

    pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    findings_t = ({"severity": "WARNING", "title": "x", "detail": "y", "agent": "balthasar"},)
    fake_verdict = _make_magi_verdict_with_findings("GO", findings_t)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", lambda **_kw: fake_verdict)

    spy = {"calls": 0}

    def fake_cross_check(**_kw):
        spy["calls"] += 1
        raise AssertionError("cross-check must not run when magi_cross_check=False")

    monkeypatch.setattr(pre_merge_cmd, "_loop2_cross_check", fake_cross_check)
    monkeypatch.setattr(pre_merge_cmd, "_persist_retried_agents_to_audit", lambda *_a, **_kw: None)

    cfg = _make_pluginconfig_for_loop2(magi_cross_check=False, root=tmp_path)
    result = pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)

    assert spy["calls"] == 0
    # OFF breadcrumb fires (G4 stderr breadcrumb).
    captured = capsys.readouterr()
    assert "cross-check is OFF" in captured.err
    # Findings flow through unchanged (no annotation fields attached).
    assert "cross_check_decision" not in result.findings[0]


def test_c1_loop2_emits_off_breadcrumb_once_per_invocation(tmp_path, monkeypatch, capsys):
    """C1: G4 breadcrumb is dedup'd even when _loop2 runs multiple iters."""
    import magi_dispatch
    import pre_merge_cmd

    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("# plan\n", encoding="utf-8")

    pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    # Force two iters: degraded -> non-degraded.
    sequence = iter(
        [
            _make_magi_verdict_with_findings_degraded("GO", (), True),
            _make_magi_verdict_with_findings("GO", ()),
        ]
    )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", lambda **_kw: next(sequence))
    monkeypatch.setattr(pre_merge_cmd, "_persist_retried_agents_to_audit", lambda *_a, **_kw: None)

    cfg = _make_pluginconfig_for_loop2(magi_cross_check=False, root=tmp_path)
    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)

    captured = capsys.readouterr()
    # Single occurrence (count of "cross-check is OFF" lines == 1).
    assert captured.err.count("cross-check is OFF") == 1


# ---------------------------------------------------------------------------
# C1 (melchior CRITICAL) — exhaustive verification that
# `_apply_cross_check_decisions` honors the annotation-only invariant
# (length-preserved + original `severity` unchanged on DOWNGRADE).
# Single test per spec sec.2.1 redesign: the surfaced finding's `severity`
# field is NEVER mutated; DOWNGRADE recommendations live solely in
# `cross_check_recommended_severity`. INV-29 (operator + receiving-code-review)
# is the only stage that may filter findings.
# ---------------------------------------------------------------------------


def test_g1_apply_cross_check_decisions_length_preserved():
    """C1 verification: REJECT/DOWNGRADE/KEEP all length-preserved + original severity unchanged.

    Annotation-only redesign (spec sec.2.1 CRITICAL #1+#4):

    - REJECT must NOT remove the finding.
    - DOWNGRADE must NOT mutate the original ``severity`` field; the
      review's recommended severity lives in
      ``cross_check_recommended_severity`` for INV-29 consideration.
    - KEEP/REJECT must surface ``cross_check_recommended_severity == None``.
    - The annotated list length always equals the input list length.
    - Pre-existing finding fields (severity, title, detail, agent) are
      preserved verbatim.
    """
    from pre_merge_cmd import _apply_cross_check_decisions

    findings = [
        {
            "severity": "CRITICAL",
            "title": "fp",
            "detail": "false positive at line N",
            "agent": "caspar",
        },
        {
            "severity": "WARNING",
            "title": "naming polish",
            "detail": "rename for clarity",
            "agent": "balthasar",
        },
        {
            "severity": "CRITICAL",
            "title": "valid",
            "detail": "missing assertion",
            "agent": "melchior",
        },
    ]
    decisions = [
        {
            "original_index": 0,
            "decision": "REJECT",
            "rationale": "no underlying issue",
        },
        {
            "original_index": 1,
            "decision": "DOWNGRADE",
            "rationale": "polish only",
            "recommended_severity": "INFO",
        },
        {
            "original_index": 2,
            "decision": "KEEP",
            "rationale": "valid concern",
        },
    ]
    annotated = _apply_cross_check_decisions(findings, decisions)

    # Length-preserved invariant (spec sec.2.1 CRITICAL #1+#4).
    assert len(annotated) == len(findings)

    # Original severity NEVER mutated (annotation-only redesign).
    assert annotated[0]["severity"] == "CRITICAL"  # REJECT keeps severity
    assert annotated[1]["severity"] == "WARNING"  # DOWNGRADE keeps severity
    assert annotated[2]["severity"] == "CRITICAL"  # KEEP keeps severity

    # cross_check_decision matches the input decision.
    assert annotated[0]["cross_check_decision"] == "REJECT"
    assert annotated[1]["cross_check_decision"] == "DOWNGRADE"
    assert annotated[2]["cross_check_decision"] == "KEEP"

    # cross_check_recommended_severity surfaced ONLY for DOWNGRADE; KEEP
    # and REJECT carry None so audit JSON serializes them as null.
    assert annotated[0]["cross_check_recommended_severity"] is None
    assert annotated[1]["cross_check_recommended_severity"] == "INFO"
    assert annotated[2]["cross_check_recommended_severity"] is None

    # Pre-existing fields preserved verbatim across the annotation pass.
    for idx, original in enumerate(findings):
        for k in ("severity", "title", "detail", "agent"):
            assert annotated[idx][k] == original[k]


def test_g1_apply_cross_check_decisions_default_keep_for_missing_decision():
    """C1 verification: missing per-finding decision defaults to KEEP, length still preserved.

    When the meta-reviewer returns fewer decisions than findings (e.g. the
    review timed out partway), `_apply_cross_check_decisions` must still
    return a length-preserved list with the missing entries defaulting to
    KEEP. INV-29 then evaluates the original severity unchanged.
    """
    from pre_merge_cmd import _apply_cross_check_decisions

    findings = [
        {"severity": "CRITICAL", "title": "a", "detail": "x", "agent": "caspar"},
        {"severity": "WARNING", "title": "b", "detail": "y", "agent": "balthasar"},
    ]
    # Only one decision returned — second finding has no per-index decision.
    decisions = [
        {
            "original_index": 0,
            "decision": "REJECT",
            "rationale": "false positive",
        },
    ]
    annotated = _apply_cross_check_decisions(findings, decisions)

    assert len(annotated) == len(findings)
    assert annotated[0]["cross_check_decision"] == "REJECT"
    # Default KEEP applied for finding without an explicit decision.
    assert annotated[1]["cross_check_decision"] == "KEEP"
    # Severities still untouched.
    assert annotated[0]["severity"] == "CRITICAL"
    assert annotated[1]["severity"] == "WARNING"


# ---------------------------------------------------------------------------
# C3 (caspar CRITICAL) — invocation-site tripwires for v1.0.0 helpers.
# Loop 1 caught dead-code wiring on TWO showpiece features (Feature G
# cross-check + spec-snapshot drift gate). C3 audits the remaining four
# helpers to prove they are invoked from production paths, not just
# unit-tested in isolation.
# ---------------------------------------------------------------------------


def test_c3_record_magi_retried_agents_invoked_from_persist_helper(tmp_path, monkeypatch):
    """C3: ``_record_magi_retried_agents`` is invoked from
    ``pre_merge_cmd._persist_retried_agents_to_audit`` in the production
    path after each MAGI Loop 2 iter when ``auto-run.json`` exists.

    Wiring under test: ``_loop2`` calls ``_persist_retried_agents_to_audit``,
    which (when the audit file is present) invokes
    ``auto_cmd._record_magi_retried_agents`` to propagate retried_agents
    telemetry. Spy on ``auto_cmd._record_magi_retried_agents`` and assert
    it fires once.
    """
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd

    (tmp_path / ".claude").mkdir(exist_ok=True)
    # Audit file MUST exist for the wiring to fire (interactive pre-merge
    # without auto-run.json skips silently per design).
    (tmp_path / ".claude" / "auto-run.json").write_text("{}", encoding="utf-8")

    spy = {"calls": 0, "kwargs": None}

    def fake_record(auto_run_path, *, iter_n, retried_agents):
        spy["calls"] += 1
        spy["kwargs"] = {
            "auto_run_path": auto_run_path,
            "iter_n": iter_n,
            "retried_agents": retried_agents,
        }

    monkeypatch.setattr(auto_cmd, "_record_magi_retried_agents", fake_record)

    verdict = magi_dispatch.MAGIVerdict(
        verdict="GO",
        degraded=False,
        conditions=(),
        findings=(),
        raw_output='{"verdict": "GO"}',
        retried_agents=("balthasar",),
    )
    pre_merge_cmd._persist_retried_agents_to_audit(tmp_path, 2, verdict)

    assert spy["calls"] == 1
    assert spy["kwargs"]["iter_n"] == 2
    assert spy["kwargs"]["retried_agents"] == ["balthasar"]


def test_c3_resolve_all_models_once_invoked_from_phase2_task_loop(tmp_path, monkeypatch):
    """C3: ``_resolve_all_models_once`` is invoked from the production
    ``auto_cmd._phase2_task_loop`` preflight path EXACTLY ONCE per auto run.

    Spec sec.2.3 (J2): replaces ~70-150 CLAUDE.md disk reads per auto run
    with a single read at task-loop entry. If this helper is genuinely dead
    (defined + unit-tested but never called from production), this test
    reveals the wiring gap.
    """
    import auto_cmd
    import inspect

    # Text-level audit: ``_phase2_task_loop`` body must reference the
    # preflight helper at least once. If absent, the helper is dead code
    # despite being unit-tested in isolation.
    source = inspect.getsource(auto_cmd._phase2_task_loop)
    assert "_resolve_all_models_once" in source, (
        "DEAD CODE: ``_resolve_all_models_once`` is defined and unit-tested "
        "but never invoked from ``auto_cmd._phase2_task_loop``. Wire the "
        "preflight call at task-loop entry per spec sec.2.3 (J2)."
    )


def test_c3_normalize_findings_for_carry_forward_invoked_from_loop2():
    """C3: ``_normalize_findings_for_carry_forward`` is invoked from the
    production ``pre_merge_cmd._loop2`` between MAGI iters to strip
    cross-check annotation fields before re-emitting findings.

    Spec sec.2.1 W4 (caspar Loop 2 iter 4 fix): annotation fields
    accumulate unbounded across iters if not stripped. The "Prior triage
    context" block is the canonical record; the working ``findings`` set
    MUST be normalized back to the un-annotated form.
    """
    import inspect
    import pre_merge_cmd

    # Text-level audit: ``_loop2`` body must reference the normalizer at
    # least once. If absent, annotations carry over unbounded across iters
    # despite the helper being unit-tested in isolation.
    source = inspect.getsource(pre_merge_cmd._loop2)
    assert "_normalize_findings_for_carry_forward" in source, (
        "DEAD CODE: ``_normalize_findings_for_carry_forward`` is defined "
        "and unit-tested but never invoked from ``pre_merge_cmd._loop2``. "
        "Wire it between MAGI iters to strip annotations before "
        "re-emitting findings (spec sec.2.1 W4)."
    )


def test_c3_emit_cross_check_disabled_breadcrumb_referenced_from_loop2_body():
    """C3: ``_emit_cross_check_disabled_breadcrumb_once`` is referenced
    from the production ``pre_merge_cmd._loop2`` body.

    Already exercised functionally by
    ``test_c1_loop2_emits_off_breadcrumb_once_per_invocation``; this
    grep-style audit is a defense-in-depth tripwire that catches
    dead-code regressions even if the functional test is silently
    monkeypatched away in a refactor.
    """
    import inspect
    import pre_merge_cmd

    source = inspect.getsource(pre_merge_cmd._loop2)
    assert "_emit_cross_check_disabled_breadcrumb_once" in source, (
        "REGRESSION: ``_emit_cross_check_disabled_breadcrumb_once`` no "
        "longer referenced from ``pre_merge_cmd._loop2``. The G4 "
        "breadcrumb is silently dead. Re-wire per spec sec.2.1 G4."
    )


# ---------------------------------------------------------------------------
# C2 (caspar Loop 2 iter 1 CRITICAL): cross-check must evaluate findings
# against the real cumulative diff, not an empty placeholder. Without this,
# the meta-reviewer has no production code to compare against -- the
# recursive payoff is invalidated. Spec sec.2.1 G6 + W-NEW1.
# ---------------------------------------------------------------------------


def test_c2_compute_loop2_diff_returns_diff_text(tmp_path, monkeypatch):
    """C2: ``_compute_loop2_diff`` returns the cumulative diff text on success."""
    import subprocess_utils
    from pre_merge_cmd import _compute_loop2_diff

    fake_diff = "diff --git a/foo.py b/foo.py\n+changed line\n"

    def fake_run(cmd, timeout=None, cwd=None):
        result = MagicMock()
        result.returncode = 0
        result.stdout = fake_diff
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    out = _compute_loop2_diff(tmp_path)
    assert out == fake_diff


def test_c2_compute_loop2_diff_handles_subprocess_failure(tmp_path, monkeypatch, capsys):
    """C2: ``_compute_loop2_diff`` returns '' + stderr breadcrumb on subprocess failure."""
    import subprocess_utils
    from pre_merge_cmd import _compute_loop2_diff

    def fake_run(cmd, timeout=None, cwd=None):
        raise OSError("git not found")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    out = _compute_loop2_diff(tmp_path)
    assert out == ""
    captured = capsys.readouterr()
    assert "[sbtdd magi-cross-check] failed to compute diff" in captured.err
    assert "git not found" in captured.err


def test_c2_compute_loop2_diff_truncates_oversized(tmp_path, monkeypatch):
    """Loop 2 iter 2->3 W3/W7: diff cap raised to 1MB; >1MB triggers truncation.

    v0.5.0 cap was 200KB, but cumulative v1.0.0 diff observed at 918KB
    silently truncated 78% of the patch threaded into the cross-check
    meta-reviewer. The cap was raised to 1MB to match observed plan
    bundle sizes; 500KB no longer triggers truncation.
    """
    import subprocess_utils
    from pre_merge_cmd import _compute_loop2_diff

    huge_diff = "x" * (1_500 * 1024)  # 1.5MB triggers truncation under 1MB cap

    def fake_run(cmd, timeout=None, cwd=None):
        result = MagicMock()
        result.returncode = 0
        result.stdout = huge_diff
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    out = _compute_loop2_diff(tmp_path)
    assert len(out) <= 1024 * 1024 + 100  # 1MB + truncation marker overhead
    assert "[... truncated for prompt budget ...]" in out


def test_compute_loop2_diff_cap_raised_to_1mb(tmp_path, monkeypatch):
    """Task 2 (W3/W7): 900KB diff fits under raised 1MB cap (no truncation).

    Pre-fix the cap was 200KB, so a 900KB cumulative diff (observed
    empirically as ~918KB during v1.0.0 cycle) was silently truncated to
    22% of its content. The fix raises the cap to 1MB so realistic
    bundle diffs fit untruncated and the meta-reviewer evaluates the
    full patch.
    """
    import subprocess_utils
    from pre_merge_cmd import _compute_loop2_diff

    # 900KB: realistic cumulative diff size at v1.0.0; under the new 1MB cap.
    diff = "x" * (900 * 1024)

    def fake_run(cmd, timeout=None, cwd=None):
        result = MagicMock()
        result.returncode = 0
        result.stdout = diff
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    out = _compute_loop2_diff(tmp_path)
    # No truncation: full diff content present, no marker.
    assert len(out) == len(diff), "900KB diff must NOT be truncated under the raised 1MB cap"
    assert "[... truncated for prompt budget ...]" not in out


def test_compute_loop2_diff_truncates_at_1mb(tmp_path, monkeypatch):
    """Task 2 (W3/W7): >1MB diff triggers truncation marker.

    Sanity-check the boundary: bumping the cap above 1MB still preserves
    the truncation contract for genuinely-oversized bundles.
    """
    import subprocess_utils
    from pre_merge_cmd import _compute_loop2_diff

    diff = "y" * (2 * 1024 * 1024)  # 2MB exceeds 1MB cap

    def fake_run(cmd, timeout=None, cwd=None):
        result = MagicMock()
        result.returncode = 0
        result.stdout = diff
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    out = _compute_loop2_diff(tmp_path)
    assert len(out) <= 1024 * 1024 + 100, (
        f"2MB diff must be truncated to <=1MB+marker, got {len(out)} bytes"
    )
    assert "[... truncated for prompt budget ...]" in out
    assert "[... truncated for prompt budget ...]" in out


def test_c2_loop2_passes_real_diff_to_cross_check(tmp_path, monkeypatch):
    """C2: ``_loop2`` threads ``_compute_loop2_diff`` output into cross-check."""
    import inspect
    import pre_merge_cmd

    # Text-level audit: ``_loop2`` body must reference the diff helper. If
    # absent, the cross-check is still evaluating ``diff=""`` -- recursive
    # payoff is invalidated.
    source = inspect.getsource(pre_merge_cmd._loop2)
    assert "_compute_loop2_diff" in source, (
        "REGRESSION: ``_compute_loop2_diff`` no longer referenced from "
        "``pre_merge_cmd._loop2``. Cross-check meta-reviewer evaluates "
        "an empty diff -- recursive payoff invalidated. Re-wire per "
        "spec sec.2.1 W-NEW1 / Loop 2 iter 1 caspar CRITICAL."
    )


def test_c2_build_cross_check_prompt_embeds_diff():
    """C2: ``_build_cross_check_prompt`` includes diff content in the prompt."""
    from pre_merge_cmd import _build_cross_check_prompt

    diff = "diff --git a/foo.py b/foo.py\n+real change\n"
    findings: list[dict] = [
        {"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "caspar"},
    ]
    prompt = _build_cross_check_prompt(diff, "GO_WITH_CAVEATS", findings)
    assert "Cumulative diff under review" in prompt


def test_cross_check_audit_records_truncation_metadata(tmp_path, monkeypatch):
    """Task 2 (W3/W7): when diff is truncated, audit JSON records the metadata.

    The pre-fix audit JSON had no diff_truncated / original_bytes / cap_bytes
    fields, so post-mortem readers had no way to tell whether the meta-
    reviewer had evaluated the full diff or a silently-truncated subset.
    The fix threads the truncation flag + sizes through ``_loop2`` ->
    ``_loop2_cross_check`` -> ``_write_cross_check_audit`` so audit
    artifacts surface the truncation context.
    """
    import subprocess_utils
    import pre_merge_cmd
    import magi_dispatch

    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("# plan\n", encoding="utf-8")

    pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    # Force _compute_loop2_diff to surface a >1MB diff so truncation triggers.
    huge_diff = "z" * (2 * 1024 * 1024)

    def fake_run(cmd, timeout=None, cwd=None):
        result = MagicMock()
        result.returncode = 0
        result.stdout = huge_diff
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)

    findings_t = ({"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "caspar"},)
    fake_verdict = _make_magi_verdict_with_findings("GO", findings_t)
    monkeypatch.setattr(magi_dispatch, "invoke_magi", lambda **_kw: fake_verdict)

    def fake_dispatch(*, diff, prompt, **_kw):
        return {
            "decisions": [
                {"original_index": 0, "decision": "KEEP", "rationale": "ok"},
            ],
        }

    monkeypatch.setattr(pre_merge_cmd, "_dispatch_requesting_code_review", fake_dispatch)
    monkeypatch.setattr(pre_merge_cmd, "_persist_retried_agents_to_audit", lambda *_a, **_kw: None)

    cfg = _make_pluginconfig_for_loop2(magi_cross_check=True, root=tmp_path)
    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)

    # Read the cross-check audit artifact.
    audit_dir = tmp_path / ".claude" / "magi-cross-check"
    assert audit_dir.exists(), "cross-check audit dir must be created"
    artifacts = sorted(audit_dir.glob("iter*.json"))
    assert len(artifacts) >= 1, "at least one cross-check audit artifact must exist"
    audit = json.loads(artifacts[-1].read_text(encoding="utf-8"))
    assert audit.get("diff_truncated") is True, (
        "audit JSON must record diff_truncated when diff exceeded the cap"
    )
    assert audit.get("diff_original_bytes") == len(huge_diff), (
        "audit JSON must record the original (pre-truncation) byte count"
    )
    assert audit.get("diff_cap_bytes") == 1024 * 1024, (
        "audit JSON must record the cap (1MB) used during truncation"
    )


def test_phase4_pre_merge_audit_dir_invoked_from_loop2(tmp_path, monkeypatch):
    """Task 1c (Loop 2 iter 2->3 R11 sweep): ``_loop2`` must compute the
    cross-check audit directory through ``auto_cmd._phase4_pre_merge_audit_dir``.

    Pre-fix the audit_dir was inlined as
    ``root / ".claude" / "magi-cross-check"`` at the call site, leaving
    ``auto_cmd._phase4_pre_merge_audit_dir`` actually-dead. The fix wires
    the cross-cutting helper into the production path via deferred
    ``import auto_cmd`` so the cross-subagent boundary is respected (pre-
    merge is dispatcher-side, the helper lives in auto_cmd which both
    pre-merge and the auto-mode loop2-with-cross-check call site use).
    """
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd

    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("# plan\n", encoding="utf-8")

    pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    findings_t = ({"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "caspar"},)
    fake_verdict = _make_magi_verdict_with_findings("GO", findings_t)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", lambda **_kw: fake_verdict)

    # Spy on the helper; return a sentinel path so the test can assert
    # the value flows through to _loop2_cross_check.
    sentinel_dir = tmp_path / "sentinel-cross-check-dir"
    spy_calls: list[Path] = []

    def _spy(root: Path) -> Path:
        spy_calls.append(root)
        return sentinel_dir

    monkeypatch.setattr(auto_cmd, "_phase4_pre_merge_audit_dir", _spy)

    captured: dict = {}

    def fake_cross_check(*, diff, verdict, findings, iter_n, config, audit_dir, **_kw):
        captured["audit_dir"] = audit_dir
        return [{**f, "cross_check_decision": "KEEP"} for f in findings]

    monkeypatch.setattr(pre_merge_cmd, "_loop2_cross_check", fake_cross_check)
    monkeypatch.setattr(pre_merge_cmd, "_persist_retried_agents_to_audit", lambda *_a, **_kw: None)

    cfg = _make_pluginconfig_for_loop2(magi_cross_check=True, root=tmp_path)
    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)

    assert len(spy_calls) == 1, (
        "_loop2 must invoke auto_cmd._phase4_pre_merge_audit_dir exactly once "
        "(pre-fix the helper was actually-dead and the path was inlined)"
    )
    assert spy_calls[0] == tmp_path
    assert captured["audit_dir"] == sentinel_dir, (
        "audit_dir threaded into _loop2_cross_check must be the helper's return"
    )
