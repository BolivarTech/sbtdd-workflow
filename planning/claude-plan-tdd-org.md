# v1.0.0 MAGI Quality + Schema/Infrastructure + v0.5.1 Fold-in Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.0.0 = Pillar 1 (Feature G MAGI cross-check meta-reviewer + F44.3 retried_agents propagation + J2 ResolvedModels preflight) + Pillar 2 (Feature I schema_version + migration tool skeleton + Feature H Group B options 2 spec-snapshot + 5 auto-gen scenario stubs) + v0.5.1 fold-in (J3+J7 production wiring + 4 Caspar concerns + Windows tmp PID flake + 5 INFOs housekeeping).

**Architecture:** True parallel 2-subagent dispatch with surfaces 100% disjoint per spec sec.6.1.

- **Subagent #1 — Dispatchers + observability completion** (sequential within: Pillar 1 features FIRST, then v0.5.1 fold-in): owns `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`, `status_cmd.py` + their tests. Forbidden: `config.py`, `models.py`, `superpowers_dispatch.py`, new scripts under `scripts/`.
- **Subagent #2 — Schema + new scripts + writing-plans extension**: owns `config.py`, `models.py` (ResolvedModels addition), new `scripts/spec_snapshot.py`, new `scripts/migrate_plugin_local.py`, `superpowers_dispatch.py` + their tests. Forbidden: `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`, `status_cmd.py`.

Cross-subagent contract: ResolvedModels dataclass + 2 PluginConfig fields + spec_snapshot helpers pinned in spec sec.5. Both subagents implement against the contract; integration verified at `make verify` post-merge.

**Tech Stack:** Python 3.9+, threading + queue + dataclasses + selectors + fnmatch (stdlib only on hot paths), pytest, ruff, mypy --strict, PyYAML (config parser; existing dependency).

---

## Pre-flight contracts (read-only reference for both subagents)

### Branch + working tree

- Branch: create `feature/v1.0.0-bundle` from current `main` (HEAD `3610a9f`).
- Working tree must be clean before each task starts. Verify via `git status` returns empty.
- Implementation commits land on the dev branch; merge to main only after pre-merge gate passes.

### ResolvedModels schema (spec sec.5.1)

```python
@dataclass(frozen=True)
class ResolvedModels:
    implementer: str
    spec_reviewer: str
    code_review: str
    magi_dispatch: str
```

Resolved once at task-loop entry per auto run. INV-0 cascade applies: CLAUDE.md model pin overrides plugin.local.md fields silently.

**Pre-existing dependency (CRITICAL #3 fix):**
``models.INV_0_PINNED_MODEL_RE`` is **pre-existing in `models.py` since v0.3.0** (Feature E per-skill model selection). v1.0.0 does NOT introduce, alias, or redefine the regex. S2-1 (Subagent #2) only ADDS the ``ResolvedModels`` dataclass beside the existing regex. S1-8 (Subagent #1) consumes via ``import models; models.INV_0_PINNED_MODEL_RE.search(...)`` without touching Subagent #2 surfaces.

### PluginConfig new fields (spec sec.5.2)

```python
# v1.0.0 Feature G — default OFF (opt-in) per balthasar Loop 2 iter 1
# WARNING: recursive dogfood circular risk. Operator flips via
# `magi_cross_check: true` in plugin.local.md.
magi_cross_check: bool = False

# v1.0.0 Feature I
schema_version: int = 1  # default 1 = v0.5.0 backward compat
```

### Spec_snapshot helpers (spec sec.5.3)

```python
def emit_snapshot(spec_path: Path) -> dict[str, str]:
    """Parse spec sec.4 Escenarios; return {scenario_title: hash}."""

def compare(prev: dict[str, str], curr: dict[str, str]) -> dict[str, list[str]]:
    """Return {'added': [...], 'removed': [...], 'modified': [...]}."""
```

### Cross-check audit artifact JSON schema (annotation redesign — CRITICAL #1+#4)

Cross-check NEVER removes findings; it ONLY annotates. ``annotated_findings``
has the SAME LENGTH as ``original_findings``; INV-29 is the only filter.

```json
{
  "iter": 1,
  "timestamp": "2026-MM-DDTHH:MM:SSZ",
  "magi_verdict": "GO_WITH_CAVEATS",
  "original_findings": [
    {"severity": "CRITICAL", "title": "...", "detail": "...", "agent": "caspar"}
  ],
  "cross_check_decisions": [
    {"original_index": 0, "decision": "REJECT", "rationale": "...",
     "recommended_severity": null}
  ],
  "annotated_findings": [
    {"severity": "CRITICAL", "title": "...", "detail": "...", "agent": "caspar",
     "cross_check_decision": "REJECT", "cross_check_rationale": "...",
     "cross_check_recommended_severity": null}
  ]
}
```

### auto-run.json extension (F44.3)

`magi_iter{N}_retried_agents: list[str]` per MAGI iter. Empty `[]` cuando no retries.

### New invariants

- **INV-35** (Feature G): Loop 2 MAGI findings DEBEN pasar por cross-check via `/requesting-code-review` antes de routear via INV-29 gate, salvo opt-out via `magi_cross_check: false`.
- **INV-36** (Feature I): PluginConfig has `schema_version: int = 1` field defaulting to 1 cuando absent (backward compat con v0.5.0 files); migrations tracked in `scripts/migrate_plugin_local.py` ladder.

### Cross-subagent contracts (S1 ↔ S2 dependency contract)

The four shared shapes below are pinned in spec sec.5 + this pre-flight
section. Both subagents implement against the contract; neither subagent
needs to wait for the other at code-write time. Runtime convergence
verified at `make verify` post-merge (when both subagents' commits are
on the integration branch).

Per WARNING caspar (Loop 2 iter 1): even though the pinned shapes are
identical between subagents, S1-8 (`auto_cmd._resolve_all_models_once`)
imports `models.ResolvedModels` which exists ONLY after S2-1 lands. Two
mitigations available, neither requires re-ordering the parallel
dispatch:

- **Mitigation A (preferred — pattern matches v0.5.0 ProgressContext)**:
  `auto_cmd._resolve_all_models_once` uses a deferred import (inside the
  function body) instead of a module-level import. Tests for S1-8 (J2-1)
  monkeypatch the helper or the constructor so import-time is irrelevant.
  Cross-subagent integration is verified at `make verify` only — when
  both subagents' commits coexist on the integration branch and the real
  import succeeds. Same pattern that worked for `ProgressContext` in
  v0.5.0.

- **Mitigation B (fallback)**: orchestrator dispatches Subagent #2 task
  S2-1 first, awaits DONE, then dispatches Subagent #1 in parallel with
  the rest of Subagent #2 tasks. Used only if Mitigation A discovers
  unexpected runtime coupling.

The same pattern applies to:
- `config.PluginConfig.magi_cross_check` (S2-2) consumed by S1-1 (and
  the entire Feature G test suite).
- `config.PluginConfig.schema_version` (S2-3) — no S1 consumer in
  v1.0.0.
- `spec_snapshot.emit_snapshot` / `compare` / `persist_snapshot` /
  `load_snapshot` (S2-5 + S2-6) consumed by S1-26 + S1-27.

For each consumer site in Subagent #1, prefer deferred imports inside
the consuming function body OR test-time `monkeypatch.setattr` of the
consumer surface so Subagent #1 tests pass standalone before S2 commits
land.

### Forbidden cross-subagent surfaces (recap)

| Subagent | OWNS | FORBIDDEN |
|----------|------|-----------|
| #1 Dispatchers | `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`, `status_cmd.py`, `tests/test_auto_progress.py` (extend), `tests/test_pre_merge_cross_check.py` (NEW), `tests/test_pre_merge_streaming.py` (extend), `tests/test_dispatch_heartbeat_wiring.py` (extend), `tests/test_subprocess_utils.py` (extend), `tests/test_status_watch.py` (extend), `tests/conftest.py` (extend) | `config.py`, `models.py`, `superpowers_dispatch.py`, new scripts under `scripts/` |
| #2 Schema/scripts | `config.py`, `models.py`, `scripts/spec_snapshot.py` (NEW), `scripts/migrate_plugin_local.py` (NEW), `superpowers_dispatch.py`, `tests/test_config.py` (extend), `tests/test_models.py` (extend), `tests/test_spec_snapshot.py` (NEW), `tests/test_migrate_plugin_local.py` (NEW), `tests/test_superpowers_dispatch.py` (extend) | `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`, `status_cmd.py` |

### Verification commands (after each TDD phase)

```bash
pytest tests/ -v                    # All pass
ruff check .                        # 0 warnings
ruff format --check .               # Clean
mypy . --strict                     # 0 errors
```

Shortcut: `make verify`. NF-A budget: <= 120s.

### Commit prefixes (sec.5 commit policy)

| Phase | Prefix |
|-------|--------|
| Red (test) | `test:` |
| Green (impl) | `feat:` (new feature) or `fix:` (bug fix) |
| Refactor (cleanup) | `refactor:` |
| Task close (chore) | `chore:` |
| Docs change | `docs:` |

---

## Subagent #1 — Dispatchers + observability completion (28 tasks)

### Task S1-1: Feature G — `_loop2_cross_check` skeleton in pre_merge_cmd

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Create: `tests/test_pre_merge_cross_check.py`

- [ ] **Step 1: Write failing test for `_loop2_cross_check` opt-out path (G4)**

Create `tests/test_pre_merge_cross_check.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for v1.0.0 Feature G MAGI cross-check meta-reviewer (sec.2.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


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
        diff=diff, verdict=verdict, findings=findings,
        iter_n=1, config=config, audit_dir=tmp_path,
    )
    assert result == findings  # unchanged
    # Audit dir empty (no artifact written when skipped)
    assert list(tmp_path.iterdir()) == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_pre_merge_cross_check.py::test_g4_opt_out_via_config_returns_findings_unchanged -v
```

Expected: `ImportError: cannot import name '_loop2_cross_check' from 'pre_merge_cmd'`.

- [ ] **Step 3: Add `_loop2_cross_check` skeleton with opt-out path**

In `skills/sbtdd/scripts/pre_merge_cmd.py`, add:

```python
from pathlib import Path
from typing import Any


def _loop2_cross_check(
    *,
    diff: str,
    verdict: str,
    findings: list[dict[str, Any]],
    iter_n: int,
    config: Any,
    audit_dir: Path,
) -> list[dict[str, Any]]:
    """Cross-check MAGI Loop 2 findings via /requesting-code-review meta-review.

    Per spec sec.2.1 Feature G + INV-35: filter false-positive CRITICAL/WARNING
    findings before routing to INV-29 triage. Opt-out via
    config.magi_cross_check=False.

    Args:
        diff: Full diff under review (string).
        verdict: MAGI consensus verdict (e.g., "GO_WITH_CAVEATS").
        findings: List of MAGI findings dicts.
        iter_n: Current MAGI Loop 2 iteration number.
        config: PluginConfig with magi_cross_check field.
        audit_dir: Directory for cross-check audit artifacts.

    Returns:
        Filtered findings list (subset of input or unchanged on opt-out).
    """
    if not config.magi_cross_check:
        return findings
    # Full implementation lands in S1-2 + S1-3.
    return findings  # placeholder
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_pre_merge_cross_check.py -v
ruff check skills/sbtdd/scripts/pre_merge_cmd.py
mypy skills/sbtdd/scripts/pre_merge_cmd.py --strict
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_cross_check.py
git commit -m "feat: add _loop2_cross_check skeleton with opt-out path (G4)"
```

---

### Task S1-2: Feature G — cross-check invokes /requesting-code-review

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_pre_merge_cross_check.py`

- [ ] **Step 1: Write failing test for review dispatch + filtered findings (G1)**

Append to `tests/test_pre_merge_cross_check.py`:

```python
def test_g1_cross_check_filters_false_positive_critical(tmp_path, monkeypatch):
    """G1: cross-check filters CRITICAL marked false-positive by review."""
    from pre_merge_cmd import _loop2_cross_check

    # Mock dispatch to return REJECT decision
    fake_review_output = {
        "decisions": [
            {"original_index": 0, "decision": "REJECT",
             "rationale": "phase arg validated at line N"},
        ],
    }
    captured_args: dict = {}

    def fake_dispatch(*, diff, prompt, **_kw):
        captured_args["prompt"] = prompt
        captured_args["diff"] = diff
        return fake_review_output

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review", fake_dispatch,
    )

    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {"severity": "CRITICAL", "title": "false positive",
         "detail": "auto_cmd doesn't validate phase arg",
         "agent": "caspar"},
    ]
    result = _loop2_cross_check(
        diff="stub", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=1, config=config, audit_dir=tmp_path,
    )
    # Filtered: rejected CRITICAL removed
    assert result == []
    # Prompt references spec + plan + diff + verdict
    assert "MAGI verdict" in captured_args["prompt"]
    assert "GO_WITH_CAVEATS" in captured_args["prompt"]
```

- [ ] **Step 2: Run test to verify fail**

```bash
pytest tests/test_pre_merge_cross_check.py::test_g1_cross_check_filters_false_positive_critical -v
```

Expected: fail.

- [ ] **Step 3: Implement dispatch + filter logic**

In `pre_merge_cmd.py`, replace placeholder `return findings` in `_loop2_cross_check`:

```python
def _build_cross_check_prompt(diff: str, verdict: str, findings: list[dict[str, Any]]) -> str:
    """Build the meta-review prompt for /requesting-code-review."""
    findings_text = "\n".join(
        f"- [{f['severity']}] ({f['agent']}): {f['title']}: {f['detail']}"
        for f in findings
    )
    return (
        f"Evaluate if the following MAGI Loop 2 findings are technically "
        f"sound or false positives given the spec + plan + diff context.\n\n"
        f"MAGI verdict: {verdict}\n"
        f"MAGI findings:\n{findings_text}\n\n"
        f"For each finding output JSON: "
        f"{{decisions: [{{original_index: N, decision: KEEP|DOWNGRADE|REJECT, rationale: ...}}, ...]}}"
    )


def _dispatch_requesting_code_review(*, diff: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch /requesting-code-review skill with cross-check prompt.

    Returns parsed decisions dict per `_build_cross_check_prompt` contract.
    Implementation: use existing superpowers_dispatch.invoke_skill or
    equivalent; parse output JSON.
    """
    # Real impl uses superpowers_dispatch.invoke_requesting_code_review
    # with the meta-review prompt; for now, stub returns empty decisions.
    # Tests monkeypatch this function.
    raise NotImplementedError("Real dispatch implementation in S1-3")


def _apply_cross_check_decisions(
    findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate findings with cross-check decisions; never remove (CRITICAL #1+#4).

    Per spec sec.2.1 redesign: cross-check is annotation-only. The returned
    list has the SAME LENGTH as ``findings``. INV-29 (operator +
    ``/receiving-code-review``) is the only stage that may filter findings.

    Each annotated finding gains the following fields:
    - ``cross_check_decision`` (KEEP | DOWNGRADE | REJECT)
    - ``cross_check_rationale`` (review text)
    - ``cross_check_recommended_severity`` (only set when DOWNGRADE; the
      original ``severity`` field is preserved unchanged)

    Decision semantics:
    - KEEP: review judges the finding technically sound.
    - DOWNGRADE: review recommends lower severity; recommended severity
      surfaced in annotation only, original severity preserved on finding.
    - REJECT: review thinks the finding is a false positive; operator
      should consider rejecting at INV-29 stage but the finding REMAINS
      visible in the returned list with the REJECT annotation attached.
    """
    decision_by_index = {d["original_index"]: d for d in decisions}
    severity_downgrade = {"CRITICAL": "WARNING", "WARNING": "INFO"}
    annotated: list[dict[str, Any]] = []
    for idx, finding in enumerate(findings):
        decision = decision_by_index.get(idx, {"decision": "KEEP"})
        action = decision.get("decision", "KEEP")
        rationale = decision.get("rationale", "")
        recommended_severity: str | None = None
        if action == "DOWNGRADE":
            recommended_severity = decision.get(
                "recommended_severity",
                severity_downgrade.get(finding["severity"], "INFO"),
            )
        annotated.append({
            **finding,
            "cross_check_decision": action,
            "cross_check_rationale": rationale,
            "cross_check_recommended_severity": recommended_severity,
        })
    return annotated


def _loop2_cross_check(
    *,
    diff: str,
    verdict: str,
    findings: list[dict[str, Any]],
    iter_n: int,
    config: Any,
    audit_dir: Path,
) -> list[dict[str, Any]]:
    """Cross-check MAGI Loop 2 findings (full impl)."""
    if not config.magi_cross_check:
        return findings
    prompt = _build_cross_check_prompt(diff, verdict, findings)
    review_output = _dispatch_requesting_code_review(diff=diff, prompt=prompt)
    decisions = review_output.get("decisions", [])
    filtered = _apply_cross_check_decisions(findings, decisions)
    # Audit artifact lands in S1-3
    return filtered
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_pre_merge_cross_check.py -v
mypy skills/sbtdd/scripts/pre_merge_cmd.py --strict
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_cross_check.py
git commit -m "feat: cross-check invokes review and filters findings (G1)"
```

---

### Task S1-3: Feature G — audit artifact + KEEP/DOWNGRADE escenarios + graceful failure

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_pre_merge_cross_check.py`

- [ ] **Step 1: Write failing tests for G2, G3, G5, G6**

Append to `tests/test_pre_merge_cross_check.py`:

```python
import json


def test_g2_cross_check_annotates_valid_critical_with_keep(tmp_path, monkeypatch):
    """G2: review classifies CRITICAL as KEEP -> finding annotated, not removed."""
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {"decisions": [
            {"original_index": 0, "decision": "KEEP",
             "rationale": "missing assertion confirmed at line X"}
        ]},
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "CRITICAL", "title": "valid issue",
                 "detail": "missing assertion at X", "agent": "melchior"}]
    result = _loop2_cross_check(
        diff="x", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=1, config=config, audit_dir=tmp_path,
    )
    # Length preserved (annotation-only redesign per CRITICAL #1+#4).
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
        lambda **_kw: {"decisions": [
            {"original_index": 0, "decision": "DOWNGRADE",
             "rationale": "polish concern, not high-impact",
             "recommended_severity": "INFO"}
        ]},
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "WARNING", "title": "naming polish",
                 "detail": "rename for clarity", "agent": "balthasar"}]
    result = _loop2_cross_check(
        diff="x", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=1, config=config, audit_dir=tmp_path,
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

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review", failing_dispatch,
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "CRITICAL", "title": "x",
                 "detail": "...", "agent": "caspar"}]
    result = _loop2_cross_check(
        diff="x", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=1, config=config, audit_dir=tmp_path,
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
        lambda **_kw: {"decisions": [
            {"original_index": 0, "decision": "REJECT", "rationale": "false positive"}
        ]},
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [{"severity": "CRITICAL", "title": "x",
                 "detail": "...", "agent": "caspar"}]
    _loop2_cross_check(
        diff="diff content", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=2, config=config, audit_dir=tmp_path,
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

    Annotation-only redesign promises that absence of severity recommendation
    is encoded as JSON ``null`` (not as a missing key) so downstream tooling
    can distinguish "reviewer had no recommendation" from "reviewer never ran".
    """
    from pre_merge_cmd import _loop2_cross_check

    monkeypatch.setattr(
        "pre_merge_cmd._dispatch_requesting_code_review",
        lambda **_kw: {"decisions": [
            {"original_index": 0, "decision": "KEEP",
             "rationale": "valid concern, severity correct"},
            {"original_index": 1, "decision": "REJECT",
             "rationale": "false positive, no underlying issue"},
            {"original_index": 2, "decision": "DOWNGRADE",
             "rationale": "polish, not blocking",
             "recommended_severity": "INFO"},
        ]},
    )
    config = MagicMock()
    config.magi_cross_check = True

    findings = [
        {"severity": "CRITICAL", "title": "valid", "detail": "...", "agent": "melchior"},
        {"severity": "CRITICAL", "title": "fp", "detail": "...", "agent": "balthasar"},
        {"severity": "WARNING", "title": "polish", "detail": "...", "agent": "caspar"},
    ]
    _loop2_cross_check(
        diff="x", verdict="GO_WITH_CAVEATS", findings=findings,
        iter_n=3, config=config, audit_dir=tmp_path,
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
```

- [ ] **Step 2: Run + verify fail**

```bash
pytest tests/test_pre_merge_cross_check.py -v
```

Expected: 5 fail.

- [ ] **Step 3: Add audit artifact + graceful failure to `_loop2_cross_check`**

Replace `_loop2_cross_check` in `pre_merge_cmd.py`:

```python
import json
import sys
from datetime import datetime, timezone


def _write_cross_check_audit(
    audit_dir: Path,
    *,
    iter_n: int,
    verdict: str,
    original_findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]] | None = None,
    annotated_findings: list[dict[str, Any]] | None = None,
    cross_check_failed: bool = False,
    failure_reason: str | None = None,
) -> Path:
    """Write cross-check audit artifact JSON atomically (spec sec.2.1 G6 schema).

    Atomic write: serialize to ``<path>.tmp``, then ``Path.replace`` to
    final name. Prevents partial-write corruption if process crashes
    mid-write (per WARNING melchior — atomicization).
    """
    audit_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    audit_path = audit_dir / f"iter{iter_n}-{timestamp}.json"
    audit_data: dict[str, Any] = {
        "iter": iter_n,
        "timestamp": timestamp,
        "magi_verdict": verdict,
        "original_findings": original_findings,
        "cross_check_decisions": decisions or [],
        "annotated_findings": annotated_findings if annotated_findings is not None else original_findings,
    }
    if cross_check_failed:
        audit_data["cross_check_failed"] = True
        if failure_reason:
            audit_data["failure_reason"] = failure_reason
    tmp_path = audit_path.with_suffix(audit_path.suffix + ".tmp")
    tmp_path.write_text(
        json.dumps(audit_data, indent=2, default=str), encoding="utf-8"
    )
    tmp_path.replace(audit_path)  # atomic rename
    return audit_path


def _loop2_cross_check(
    *,
    diff: str,
    verdict: str,
    findings: list[dict[str, Any]],
    iter_n: int,
    config: Any,
    audit_dir: Path,
) -> list[dict[str, Any]]:
    """Cross-check MAGI Loop 2 findings: ANNOTATE only, never remove.

    Per spec sec.2.1 redesign (CRITICAL #1+#4): the returned list has the
    SAME LENGTH as ``findings``; each surfaced finding is augmented with
    ``cross_check_decision``, ``cross_check_rationale``, and
    ``cross_check_recommended_severity`` annotation fields. INV-29 (operator
    + ``/receiving-code-review``) is the only stage that may filter
    findings — silent drops here would hide real CRITICALs when the review
    is wrong.
    """
    if not config.magi_cross_check:
        return findings
    prompt = _build_cross_check_prompt(diff, verdict, findings)
    try:
        review_output = _dispatch_requesting_code_review(diff=diff, prompt=prompt)
    except Exception as exc:  # noqa: BLE001 - graceful fallback per G5
        sys.stderr.write(
            f"[sbtdd magi-cross-check] failed (will fall back to MAGI findings as-is): {exc}\n"
        )
        sys.stderr.flush()
        _write_cross_check_audit(
            audit_dir, iter_n=iter_n, verdict=verdict,
            original_findings=findings,
            cross_check_failed=True, failure_reason=str(exc),
        )
        return findings
    decisions = review_output.get("decisions", [])
    annotated = _apply_cross_check_decisions(findings, decisions)
    _write_cross_check_audit(
        audit_dir, iter_n=iter_n, verdict=verdict,
        original_findings=findings,
        decisions=decisions,
        annotated_findings=annotated,
    )
    return annotated
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_pre_merge_cross_check.py -v
mypy skills/sbtdd/scripts/pre_merge_cmd.py --strict
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_cross_check.py
git commit -m "feat: cross-check audit artifact + KEEP/DOWNGRADE/graceful failure (G2/G3/G5/G6)"
```

---

### Task S1-4: Feature G — wire `_dispatch_requesting_code_review` to real superpowers dispatch

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_pre_merge_cross_check.py`

- [ ] **Step 1: Write failing test for real dispatch wiring**

Append to `tests/test_pre_merge_cross_check.py`:

```python
def test_dispatch_invokes_superpowers_invoke_requesting_code_review(monkeypatch, tmp_path):
    """Real dispatch wiring: _dispatch_requesting_code_review delegates to superpowers."""
    from pre_merge_cmd import _dispatch_requesting_code_review

    captured: dict = {}

    def fake_invoke(*, prompt: str, **kwargs):
        captured["prompt"] = prompt
        captured["kwargs"] = kwargs
        # Simulate skill returning structured JSON in its output text
        return {"output": '{"decisions": [{"original_index": 0, "decision": "KEEP", "rationale": "ok"}]}'}

    monkeypatch.setattr(
        "superpowers_dispatch.invoke_requesting_code_review", fake_invoke,
    )
    result = _dispatch_requesting_code_review(diff="diff", prompt="meta-prompt")
    assert "decisions" in result
    assert captured["prompt"] == "meta-prompt"
```

- [ ] **Step 2: Run + verify fail**

Expected: NotImplementedError (current stub).

- [ ] **Step 3: Implement real dispatch wiring**

Replace `_dispatch_requesting_code_review` in `pre_merge_cmd.py`:

```python
import superpowers_dispatch


def _dispatch_requesting_code_review(*, diff: str, prompt: str, **kwargs: Any) -> dict[str, Any]:
    """Dispatch /requesting-code-review skill with cross-check meta-prompt.

    Parses the skill's output as JSON. Returns decisions dict per
    `_build_cross_check_prompt` contract.

    Tests monkeypatch this function (see test_pre_merge_cross_check).
    """
    raw_output = superpowers_dispatch.invoke_requesting_code_review(
        prompt=prompt, **kwargs,
    )
    output_text = raw_output.get("output", "{}")
    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        # Defensive: if review output isn't structured JSON, return empty decisions
        # (G5 graceful failure path will then return original findings unchanged).
        return {"decisions": []}
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_pre_merge_cross_check.py -v
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_cross_check.py
git commit -m "feat: wire _dispatch_requesting_code_review to superpowers_dispatch"
```

---

### Task S1-5: Feature G — integration into pre_merge_cmd._loop2

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_pre_merge_cross_check.py`

**Concrete site references (per balthasar Loop 2 iter 1 WARNING — file:line precision):**
- ``pre_merge_cmd.py:568`` — existing ``def _loop2(root, cfg, threshold_override, ns=None)`` definition. Returns ``magi_dispatch.MAGIVerdict``. This is the function whose body needs the cross-check sub-phase wired in (or wrapped by ``_loop2_with_cross_check`` per Step 3 below).
- ``pre_merge_cmd.py:808`` — single existing caller in ``main()``: ``verdict = _loop2(root, cfg, ns.magi_threshold, ns)``. After Step 5 wiring, this caller passes ``audit_dir = root / ".claude" / "magi-cross-check"`` through the wrapper.

Verify locally before editing:

```bash
grep -n "def _loop2\|_loop2(" skills/sbtdd/scripts/pre_merge_cmd.py
# Expected lines: 568 (def), 808 (caller in main)
```

The wrapper ``_loop2_with_cross_check`` either replaces the body of
``_loop2`` (preferred — preserves caller signature) OR introduces a new
function called from line 808 (if signature change is necessary).

- [ ] **Step 1: Write failing test for _loop2 integration**

Append to `tests/test_pre_merge_cross_check.py`:

```python
def test_loop2_integration_calls_cross_check_after_magi(tmp_path, monkeypatch):
    """_loop2 invokes _loop2_cross_check on findings before INV-29 routing."""
    from pre_merge_cmd import _loop2_with_cross_check

    cross_check_called = {"count": 0}
    def fake_cross_check(**kwargs):
        cross_check_called["count"] += 1
        return kwargs["findings"]  # return unchanged

    monkeypatch.setattr("pre_merge_cmd._loop2_cross_check", fake_cross_check)

    config = MagicMock()
    config.magi_cross_check = True

    fake_findings = [{"severity": "CRITICAL", "title": "x", "detail": "y", "agent": "z"}]
    fake_verdict = "GO_WITH_CAVEATS"

    # Stub MAGI dispatch
    monkeypatch.setattr(
        "pre_merge_cmd._invoke_magi_loop2",
        lambda **_kw: (fake_verdict, fake_findings),
    )

    result_verdict, result_findings = _loop2_with_cross_check(
        diff="x", iter_n=1, config=config, audit_dir=tmp_path,
    )
    assert cross_check_called["count"] == 1
    assert result_verdict == fake_verdict
    assert result_findings == fake_findings
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement _loop2 integration**

Add to `pre_merge_cmd.py` (or refactor existing `_loop2`):

```python
def _invoke_magi_loop2(**kwargs: Any) -> tuple[str, list[dict[str, Any]]]:
    """Existing MAGI Loop 2 dispatch (signature stub; existing impl preserved)."""
    # The actual impl in v0.5.0 already exists; this stub is illustrative.
    # Signature: returns (verdict_string, findings_list).
    raise NotImplementedError("preserve existing _loop2 dispatch")


def _loop2_with_cross_check(
    *,
    diff: str,
    iter_n: int,
    config: Any,
    audit_dir: Path,
    **magi_kwargs: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Wrapper around MAGI Loop 2 dispatch + cross-check sub-phase.

    Per spec sec.2.1 + INV-35: cross-check filters findings BEFORE INV-29
    routes them to /receiving-code-review. Verdict itself is unchanged
    (cross-check only modifies findings set).
    """
    verdict, findings = _invoke_magi_loop2(**magi_kwargs)
    filtered_findings = _loop2_cross_check(
        diff=diff, verdict=verdict, findings=findings,
        iter_n=iter_n, config=config, audit_dir=audit_dir,
    )
    return verdict, filtered_findings
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Wire into existing `_loop2` dispatchers**

Find existing `_loop2` callers in pre_merge_cmd.py and replace direct MAGI invocation with `_loop2_with_cross_check`. Pass `audit_dir = root / ".claude" / "magi-cross-check"`.

- [ ] **Step 6: Run + verify pass + commit**

```bash
pytest tests/test_pre_merge_cross_check.py -v
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_cross_check.py
git commit -m "feat: integrate _loop2_cross_check into pre_merge_cmd._loop2 dispatch"
```

---

### Task S1-6: Feature G — auto_cmd phase4 pre-merge integration

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Survey auto_cmd phase4 pre-merge structure**

```bash
grep -n "_phase4\|_pre_merge\|_loop2\|magi_cross_check" skills/sbtdd/scripts/auto_cmd.py | head -20
```

Locate the existing phase 4 pre-merge entrypoint that invokes `pre_merge_cmd._loop2`.

- [ ] **Step 2: Write failing test asserting cross_check audit_dir is passed**

Append to `tests/test_auto_progress.py`:

```python
def test_phase4_pre_merge_passes_audit_dir_to_cross_check(tmp_path, monkeypatch):
    """auto_cmd phase 4 passes .claude/magi-cross-check/ as audit_dir to _loop2_with_cross_check."""
    from auto_cmd import _phase4_pre_merge_loop2

    captured = {}
    def fake_loop2(**kwargs):
        captured["audit_dir"] = kwargs.get("audit_dir")
        return ("GO_WITH_CAVEATS", [])

    monkeypatch.setattr("pre_merge_cmd._loop2_with_cross_check", fake_loop2)

    config = MagicMock()
    config.magi_cross_check = True
    root = tmp_path
    (root / ".claude").mkdir()

    _phase4_pre_merge_loop2(root=root, config=config, iter_n=1, diff="x")
    assert captured["audit_dir"] == root / ".claude" / "magi-cross-check"
```

- [ ] **Step 3: Run + verify fail**

- [ ] **Step 4: Add or update _phase4_pre_merge_loop2 in auto_cmd.py**

```python
import pre_merge_cmd


def _phase4_pre_merge_loop2(
    *,
    root: Path,
    config: Any,
    iter_n: int,
    diff: str,
    **kwargs: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Phase 4 pre-merge MAGI Loop 2 dispatch with cross-check sub-phase."""
    audit_dir = root / ".claude" / "magi-cross-check"
    return pre_merge_cmd._loop2_with_cross_check(
        diff=diff, iter_n=iter_n, config=config, audit_dir=audit_dir,
        **kwargs,
    )
```

- [ ] **Step 5: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py::test_phase4_pre_merge_passes_audit_dir_to_cross_check -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: auto_cmd phase 4 wires cross-check audit_dir to pre_merge_cmd"
```

---

### Task S1-7: F44.3 — retried_agents propagation to auto-run.json

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test for retried_agents in auto-run.json**

Append to `tests/test_auto_progress.py`:

```python
def test_f44_3_retried_agents_persisted_to_auto_run_json(tmp_path):
    """F44.3-1: MAGI iter retried_agents written to auto-run.json."""
    from auto_cmd import _record_magi_retried_agents
    import json

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")

    _record_magi_retried_agents(auto_run_path, iter_n=2, retried_agents=["balthasar"])

    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["magi_iter2_retried_agents"] == ["balthasar"]


def test_f44_3_backward_compat_with_v0_5_0_files(tmp_path):
    """F44.3-2: v0.5.0 auto-run.json (no field) parses cleanly."""
    from auto_cmd import _read_auto_run_audit
    import json

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(
        json.dumps({"started_at": "2026-05-01T12:00:00Z"}),
        encoding="utf-8",
    )
    audit = _read_auto_run_audit(auto_run_path)
    # Field absent -> []
    assert audit.get("magi_iter1_retried_agents", []) == []
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_record_magi_retried_agents` helper**

In `auto_cmd.py`:

```python
def _record_magi_retried_agents(
    auto_run_path: Path,
    *,
    iter_n: int,
    retried_agents: list[str],
) -> None:
    """Persist `magi_iter{N}_retried_agents` to auto-run.json (F44.3).

    Uses the existing _with_file_lock pattern for single-writer serialization.
    """
    def _do_record() -> None:
        try:
            data = json.loads(auto_run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        data[f"magi_iter{iter_n}_retried_agents"] = list(retried_agents)
        tmp_path = auto_run_path.with_suffix(
            f"{auto_run_path.suffix}.tmp.{os.getpid()}.{threading.get_ident()}"
        )
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(auto_run_path)

    _with_file_lock(auto_run_path, _do_record)


def _read_auto_run_audit(auto_run_path: Path) -> dict[str, Any]:
    """Read auto-run.json into dict (used for tests + post-mortem)."""
    return json.loads(auto_run_path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Wire `_record_magi_retried_agents` into MAGI Loop 2 dispatch sites**

Find `pre_merge_cmd._loop2` or `auto_cmd._phase4_pre_merge_loop2` MAGI invocation; after each iter, extract `verdict.retried_agents` and call `_record_magi_retried_agents(auto_run_path, iter_n=N, retried_agents=verdict.retried_agents)`.

- [ ] **Step 5: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "retried_agents" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: persist MAGI retried_agents to auto-run.json per iter (F44.3)"
```

---

### Task S1-8: J2 ResolvedModels consumer in auto_cmd

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

**Cross-subagent contract:** `models.ResolvedModels` dataclass shape comes from Subagent #2 task T2-1. Subagent #1 imports it.

- [ ] **Step 1: Write failing test for `_resolve_all_models_once`**

Append to `tests/test_auto_progress.py`:

```python
def test_j2_resolve_all_models_once_caches_lookups(tmp_path, monkeypatch):
    """J2-1: _resolve_all_models_once reads CLAUDE.md exactly once."""
    from auto_cmd import _resolve_all_models_once
    from models import ResolvedModels  # provided by Subagent #2

    claude_md_reads = {"count": 0}

    def fake_read_text(self, **_kw):
        if "CLAUDE.md" in str(self):
            claude_md_reads["count"] += 1
        return ""

    monkeypatch.setattr("pathlib.Path.read_text", fake_read_text)

    config = MagicMock()
    config.implementer_model = "claude-haiku-4-5"
    config.spec_reviewer_model = "claude-sonnet-4-6"
    config.code_review_model = "claude-sonnet-4-6"
    config.magi_dispatch_model = "claude-opus-4-7"

    resolved = _resolve_all_models_once(config)
    assert isinstance(resolved, ResolvedModels)
    assert resolved.magi_dispatch == "claude-opus-4-7"
    assert claude_md_reads["count"] == 1
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_resolve_all_models_once` helper**

In `auto_cmd.py`:

```python
def _resolve_all_models_once(config: Any) -> Any:
    """Preflight: resolve per-skill model IDs ONCE per auto run (J2).

    Per spec sec.2.3: replaces ~70-150 CLAUDE.md disk reads per 36-task
    run with a single read at task-loop entry. INV-0 cascade applies:
    CLAUDE.md model pin (per `models.INV_0_PINNED_MODEL_RE`) overrides
    plugin.local.md fields silently.

    Note: ``ResolvedModels`` is defined in ``models.py`` by Subagent #2
    task S2-1. Cross-subagent Mitigation A (per pre-flight Cross-subagent
    contracts section): deferred import inside this function body avoids
    module-load-time coupling, so Subagent #1 tests can monkeypatch this
    function and pass standalone before S2-1 lands. Runtime convergence
    verified at ``make verify`` post-merge.
    """
    import models  # deferred — S2-1 dependency
    from models import ResolvedModels  # noqa: PLC0415 - deferred per pre-flight Mitigation A
    # Read CLAUDE.md once (or use existing helper if available)
    claude_md_path = Path.home() / ".claude" / "CLAUDE.md"
    try:
        claude_md_text = claude_md_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        claude_md_text = ""

    # Check for INV-0 pin
    pinned_model = None
    match = models.INV_0_PINNED_MODEL_RE.search(claude_md_text)
    if match:
        pinned_model = match.group(1)
        sys.stderr.write(
            f"[sbtdd] INV-0 cascade: CLAUDE.md pins {pinned_model!r}; "
            f"plugin.local.md per-skill model fields silently overridden\n"
        )

    def _pick(field_value: str | None, default: str) -> str:
        if pinned_model:
            return pinned_model
        return field_value or default

    return ResolvedModels(
        implementer=_pick(config.implementer_model, "claude-sonnet-4-6"),
        spec_reviewer=_pick(config.spec_reviewer_model, "claude-sonnet-4-6"),
        code_review=_pick(config.code_review_model, "claude-sonnet-4-6"),
        magi_dispatch=_pick(config.magi_dispatch_model, "claude-opus-4-7"),
    )
```

- [ ] **Step 4: Wire `_resolve_all_models_once` at task-loop entry**

In `auto_cmd._phase2_task_loop` (or equivalent), call `_resolve_all_models_once(config)` once at entry; pass the resulting `ResolvedModels` instance to all dispatch helpers as a kwarg.

- [ ] **Step 5: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "resolve_all_models" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: J2 ResolvedModels preflight cache reduces CLAUDE.md reads (J2-1)"
```

---

### Task S1-9: J2 — INV-0 pin override + immutability tests

**Files:**
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test for J2-2 INV-0 override + J2-3 immutability**

Append to `tests/test_auto_progress.py`:

```python
def test_j2_inv0_pin_overrides_plugin_local_md(monkeypatch, capsys):
    """J2-2: CLAUDE.md INV-0 pin wins over plugin.local.md fields."""
    from auto_cmd import _resolve_all_models_once

    monkeypatch.setattr(
        "pathlib.Path.read_text",
        lambda self, **_kw: "Use claude-opus-4-7 for all sessions"
        if "CLAUDE.md" in str(self) else "",
    )
    config = MagicMock()
    config.implementer_model = "claude-haiku-4-5"
    config.spec_reviewer_model = "claude-haiku-4-5"
    config.code_review_model = "claude-haiku-4-5"
    config.magi_dispatch_model = "claude-haiku-4-5"

    resolved = _resolve_all_models_once(config)
    # INV-0 wins: all fields = pinned model
    assert resolved.implementer == "claude-opus-4-7"
    assert resolved.spec_reviewer == "claude-opus-4-7"
    assert resolved.code_review == "claude-opus-4-7"
    assert resolved.magi_dispatch == "claude-opus-4-7"
    captured = capsys.readouterr()
    assert "INV-0 cascade" in captured.err


def test_j2_resolved_models_is_frozen():
    """J2-3: ResolvedModels is immutable."""
    from models import ResolvedModels
    from dataclasses import FrozenInstanceError

    rm = ResolvedModels(
        implementer="a", spec_reviewer="b",
        code_review="c", magi_dispatch="d",
    )
    with pytest.raises(FrozenInstanceError):
        rm.implementer = "z"  # type: ignore[misc]
```

- [ ] **Step 2: Run + verify pass**

J2-2 should already pass given S1-8 implementation. J2-3 depends on Subagent #2's `ResolvedModels(frozen=True)`.

```bash
pytest tests/test_auto_progress.py -k "j2" -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_auto_progress.py
git commit -m "test: J2-2 INV-0 override + J2-3 ResolvedModels immutability"
```

---

### Tasks S1-10 through S1-15: J3+J7 production wiring (33 callers, batched by site cluster)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_dispatch_heartbeat_wiring.py` (extend)

**Site clusters** (per spec sec.4.1 W1):

1. **S1-10**: auto_cmd verification + sysdebug retry sites (lines ~1148-1196)
2. **S1-11**: auto_cmd spec-review gate sites (lines ~1238-1262)
3. **S1-12**: auto_cmd mini-cycle red/green/refactor sites (lines ~1413-1448)
4. **S1-13**: pre_merge_cmd Loop 1 review sites (lines ~175-194)
5. **S1-14**: pre_merge_cmd Loop 2 MAGI dispatch (lines ~611-626)
6. **S1-15**: pre_merge_cmd receiving-findings sites (lines ~646-657)

For each cluster, the pattern is:

- [ ] **Step 1: Write failing test asserting site uses `run_streamed_with_timeout`**

Example for S1-10 (verification site):

```python
def test_s1_10_verification_site_uses_run_streamed_with_timeout(monkeypatch):
    """W1: verification dispatch site routed through run_streamed_with_timeout."""
    from auto_cmd import _run_verification_with_retries

    captured = {"called": False}
    def fake_run(*args, **kwargs):
        captured["called"] = True
        captured["dispatch_label"] = kwargs.get("dispatch_label")
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "subprocess_utils.run_streamed_with_timeout", fake_run,
    )
    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda *a, **kw: pytest.fail("should use run_streamed_with_timeout, not run_with_timeout"),
    )
    # Invoke verification site (existing function)
    # ... (specific to each site cluster) ...
    assert captured["called"] is True
    assert captured["dispatch_label"] == "verification"
```

- [ ] **Step 2: Run + verify fail**

Expected: `pytest.fail` because old `run_with_timeout` is called.

- [ ] **Step 3: Replace `run_with_timeout` with `run_streamed_with_timeout` at the site**

```python
# Before:
result = subprocess_utils.run_with_timeout(cmd, timeout=900)

# After:
result = subprocess_utils.run_streamed_with_timeout(
    cmd,
    per_stream_timeout_seconds=900,
    dispatch_label="verification",  # or appropriate label per spec
)
```

Use `dispatch_label` matching the existing `_set_progress` label at that site for consistency with v0.5.0 heartbeat wiring.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_dispatch_heartbeat_wiring.py
git commit -m "feat: route verification dispatch through run_streamed_with_timeout (S1-10 W1)"
```

Repeat the pattern for S1-11, S1-12, S1-13, S1-14, S1-15 with appropriate `dispatch_label` per site:

- S1-11 spec-review gate: `dispatch_label="spec-review"`
- S1-12 mini-cycle red/green/refactor: `dispatch_label="spec-review-mini-cycle-{red,green,refactor}"`
- S1-13 Loop 1 review: `dispatch_label=f"code-review-loop1-iter{N}"`
- S1-14 Loop 2 MAGI: `dispatch_label=f"magi-loop2-iter{N}"`
- S1-15 receiving-findings: `dispatch_label=f"receiving-magi-findings-iter{N}"`

---

### Task S1-16: W4 — narrow `_wrap_with_heartbeat_if_auto` except clauses

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_dispatch_heartbeat_wiring.py`

- [ ] **Step 1: Write failing test asserting ValueError propagates through wrap**

Append to `tests/test_dispatch_heartbeat_wiring.py`:

```python
def test_w4_wrap_propagates_valueerror_from_dispatch_with_heartbeat():
    """W4: ValueError from _dispatch_with_heartbeat MUST propagate (fail-loud)."""
    from pre_merge_cmd import _wrap_with_heartbeat_if_auto

    def failing_invoke():
        raise ValueError("missing dispatch_label")

    # phase=2 simulates auto-mode (wrap active)
    from heartbeat import set_current_progress, reset_current_progress
    from models import ProgressContext

    reset_current_progress()
    set_current_progress(ProgressContext(phase=2, dispatch_label="test"))
    try:
        with pytest.raises(ValueError, match="missing dispatch_label"):
            _wrap_with_heartbeat_if_auto(
                invoke=failing_invoke,
                iter_num=1, phase=2, dispatch_label="test",
            )
    finally:
        reset_current_progress()
```

- [ ] **Step 2: Run + verify fail**

Expected: bare-except swallows ValueError → no exception raised → test fails.

- [ ] **Step 3: Narrow except in `_wrap_with_heartbeat_if_auto`**

Locate the function in `pre_merge_cmd.py`. Replace `except Exception` (or bare `except`) with `except (AttributeError, RuntimeError)`:

```python
def _wrap_with_heartbeat_if_auto(
    *, invoke, iter_num, phase, dispatch_label, **kwargs
):
    # ... gating logic ...
    try:
        ctx = get_current_progress()
        is_auto_mode = ctx.phase != 0
    except (AttributeError, RuntimeError):
        # Per Loop 2 iter 4 W4 fix: narrow except to introspection failures only.
        # ValueError (fail-loud signal from _dispatch_with_heartbeat) MUST propagate.
        is_auto_mode = False

    if is_auto_mode:
        return _dispatch_with_heartbeat(
            invoke=invoke, **kwargs,
        )
    return invoke()
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_dispatch_heartbeat_wiring.py -k "w4" -v
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_dispatch_heartbeat_wiring.py
git commit -m "fix: narrow _wrap_with_heartbeat_if_auto except clauses (W4)"
```

---

### Task S1-17: W5 — status_cmd.watch_main exception guard

**Files:**
- Modify: `skills/sbtdd/scripts/status_cmd.py`
- Modify: `tests/test_status_watch.py`

- [ ] **Step 1: Write failing test for cycle body exception guard**

Append to `tests/test_status_watch.py`:

```python
def test_w5_watch_main_survives_cycle_body_exception(tmp_path, monkeypatch, capsys):
    """W5: transient exception in watch cycle does NOT kill the loop."""
    from status_cmd import watch_main
    import threading

    cycle_calls = {"count": 0}

    def flaky_render(*args, **kwargs):
        cycle_calls["count"] += 1
        if cycle_calls["count"] == 2:
            raise RuntimeError("transient error")
        if cycle_calls["count"] >= 4:
            raise KeyboardInterrupt()  # exit after 4 cycles
        return None

    monkeypatch.setattr("status_cmd._watch_render_one", flaky_render)
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"progress": {}}', encoding="utf-8")

    rc = watch_main(auto_run_path, interval=0.01, json_mode=False)
    assert rc == 130  # SIGINT exit
    assert cycle_calls["count"] >= 4
    captured = capsys.readouterr()
    assert "[sbtdd watch] cycle error" in captured.err
```

- [ ] **Step 2: Run + verify fail**

Expected: RuntimeError propagates kills loop before 4 cycles.

- [ ] **Step 3: Add try/except around cycle body in watch_main**

In `status_cmd.py::watch_main`:

```python
def watch_main(
    auto_run_path: Path,
    *,
    interval: float,
    json_mode: bool,
) -> int:
    """W1-W6: full status --watch poll loop. Per Loop 2 iter 4 W5 fix:
    exception guard around cycle body so transient errors don't kill watch."""
    validate_watch_interval(interval)
    if not auto_run_path.exists():
        sys.stderr.write("[sbtdd status] no auto run in progress\n")
        return 0
    state = WatchPollState(default_interval=interval)
    last_progress: dict | None = None
    try:
        while True:
            try:
                # ... existing cycle body ...
                # (read auto-run, render, sleep, etc.)
                pass  # placeholder for actual existing body
            except KeyboardInterrupt:
                raise  # let outer handler exit cleanly
            except Exception as exc:  # noqa: BLE001 - W5 guard
                sys.stderr.write(
                    f"[sbtdd watch] cycle error (will continue): {exc}\n"
                )
                sys.stderr.flush()
                time.sleep(state.current_interval)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 130
```

(Adapt to actual existing watch_main structure.)

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_status_watch.py -k "w5" -v
git add skills/sbtdd/scripts/status_cmd.py tests/test_status_watch.py
git commit -m "fix: watch_main exception guard around cycle body (W5)"
```

---

### Task S1-18: W6 — convert _assert_main_thread test mutations to monkeypatch.setattr

**Files:**
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Locate existing test mutations**

```bash
grep -n "_assert_main_thread = \|auto_cmd._assert_main_thread" tests/test_auto_progress.py
```

- [ ] **Step 2: Convert each direct mutation to monkeypatch.setattr**

For each test that has:
```python
def test_concurrent_X():
    auto_cmd._assert_main_thread = lambda: None  # bypass
    try:
        # test body
    finally:
        auto_cmd._assert_main_thread = original  # restore
```

Replace with:
```python
def test_concurrent_X(monkeypatch):
    monkeypatch.setattr("auto_cmd._assert_main_thread", lambda: None)
    # test body — cleanup automatic on test exit/failure
```

- [ ] **Step 3: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "concurrent" -v
git add tests/test_auto_progress.py
git commit -m "refactor: use monkeypatch.setattr for _assert_main_thread bypass (W6)"
```

---

### Task S1-19: W7 — separate persistence-failure vs drain-failure breadcrumb dedup

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test asserting independent dedup flags**

Append to `tests/test_auto_progress.py`:

```python
def test_w7_persistence_vs_drain_breadcrumbs_independent(monkeypatch, capsys):
    """W7: persistence-failure and drain-failure breadcrumbs use separate dedup flags."""
    from auto_cmd import (
        _drain_decode_error_emitted,
        _persistence_error_emitted,
        _emit_drain_decode_error_breadcrumb,
        _emit_persistence_error_breadcrumb,
        _reset_breadcrumb_flags_for_tests,
    )

    _reset_breadcrumb_flags_for_tests()

    # First drain decode error: emits
    _emit_drain_decode_error_breadcrumb("decode failure")
    captured1 = capsys.readouterr()
    assert "[sbtdd auto] drain JSON decode error" in captured1.err

    # First persistence error: emits SEPARATELY (not deduped against drain)
    _emit_persistence_error_breadcrumb("persistence failure")
    captured2 = capsys.readouterr()
    assert "[sbtdd auto] persistence error" in captured2.err

    # Repeat each: should NOT re-emit (per-flag dedup)
    _emit_drain_decode_error_breadcrumb("decode failure 2")
    _emit_persistence_error_breadcrumb("persistence failure 2")
    captured3 = capsys.readouterr()
    assert captured3.err == ""

    _reset_breadcrumb_flags_for_tests()
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement separate breadcrumb helpers**

In `auto_cmd.py`:

```python
_drain_decode_error_emitted = False
_persistence_error_emitted = False


def _emit_drain_decode_error_breadcrumb(reason: str) -> None:
    """Per W7: separate dedup for drain JSON decode failures."""
    global _drain_decode_error_emitted
    if _drain_decode_error_emitted:
        return
    _drain_decode_error_emitted = True
    try:
        sys.stderr.write(
            f"[sbtdd auto] drain JSON decode error (will continue silently): {reason}\n"
        )
        sys.stderr.flush()
    except OSError:
        pass


def _emit_persistence_error_breadcrumb(reason: str) -> None:
    """Per W7: separate dedup for auto-run.json persistence failures."""
    global _persistence_error_emitted
    if _persistence_error_emitted:
        return
    _persistence_error_emitted = True
    try:
        sys.stderr.write(
            f"[sbtdd auto] persistence error (will continue silently): {reason}\n"
        )
        sys.stderr.flush()
    except OSError:
        pass


def _reset_breadcrumb_flags_for_tests() -> None:
    """Test-only helper."""
    global _drain_decode_error_emitted, _persistence_error_emitted
    _drain_decode_error_emitted = False
    _persistence_error_emitted = False
```

Replace existing breadcrumb emit sites in auto_cmd to call the appropriate helper.

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "w7" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "fix: separate dedup flags for drain vs persistence breadcrumbs (W7)"
```

---

### Task S1-20: W8 — Windows tmp filename PID collision fix (thread-id in pattern)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test for tmp filename uniqueness across threads**

Append to `tests/test_auto_progress.py`:

```python
def test_w8_tmp_filename_includes_thread_id(monkeypatch, tmp_path):
    """W8: tmp filename in atomic-rename pattern includes thread.get_ident()."""
    import threading
    from auto_cmd import _atomic_replace_with_tmp

    captured_tmp_paths: list[str] = []
    real_replace = Path.replace

    def fake_replace(self, target):
        captured_tmp_paths.append(str(self))
        # Don't actually rename in test
        return None

    monkeypatch.setattr("pathlib.Path.replace", fake_replace)

    target = tmp_path / "out.json"
    target.write_text("{}", encoding="utf-8")

    barrier = threading.Barrier(3)
    def writer():
        barrier.wait()
        _atomic_replace_with_tmp(target, content="{}")

    threads = [threading.Thread(target=writer) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()

    # Each tmp path must include both PID and thread-id
    for p in captured_tmp_paths:
        assert ".tmp." in p
        # Pattern: <name>.tmp.<pid>.<tid>
        parts = p.split(".tmp.")[1].split(".")
        assert len(parts) == 2  # pid . tid
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add `_atomic_replace_with_tmp` helper using thread-id**

In `auto_cmd.py`:

```python
import threading


def _atomic_replace_with_tmp(target: Path, *, content: str) -> None:
    """Per W8: tmp filename includes PID + thread.get_ident() to avoid
    Windows PermissionError when threads in same process share PID."""
    tmp_path = target.with_suffix(
        f"{target.suffix}.tmp.{os.getpid()}.{threading.get_ident()}"
    )
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(target)
```

Audit existing 3 writers (per spec sec.4.3 caspar finding lines 644, 997, 2469) and replace direct `tmp_path = ... .tmp.{getpid()}` patterns with calls to `_atomic_replace_with_tmp`.

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "w8" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "fix: tmp filename includes thread-id to avoid Windows PID collision (W8)"
```

---

### Task S1-21: I-Hk1 — narrow BaseException to Exception in _write_auto_run_audit

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_auto_progress.py`:

```python
def test_i_hk1_systemexit_propagates_through_write_audit(tmp_path):
    """I-Hk1: SystemExit / KeyboardInterrupt MUST propagate through _write_auto_run_audit."""
    from auto_cmd import _write_auto_run_audit
    from unittest.mock import patch

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("{}", encoding="utf-8")

    audit = MagicMock()
    audit.to_dict.return_value = {"some": "data"}

    with patch("pathlib.Path.write_text", side_effect=SystemExit(2)):
        with pytest.raises(SystemExit):
            _write_auto_run_audit(auto_run_path, audit)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Replace `BaseException` with `Exception` in _write_auto_run_audit**

```bash
grep -n "BaseException" skills/sbtdd/scripts/auto_cmd.py
```

For each match in `_write_auto_run_audit`, replace `except BaseException` with `except Exception`.

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "systemexit" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "fix: narrow BaseException to Exception in _write_auto_run_audit (I-Hk1)"
```

---

### Task S1-22: I-Hk3 — promote autouse fixture to tests/conftest.py

**Files:**
- Modify: `tests/conftest.py` (extend if exists, create otherwise)
- Modify: `tests/test_auto_progress.py` (remove duplicated fixture)

- [ ] **Step 1: Identify the autouse fixture in test_auto_progress.py**

```bash
grep -n "autouse=True" tests/test_auto_progress.py
```

- [ ] **Step 2: Move fixture body to tests/conftest.py**

Read existing `tests/conftest.py`; append the autouse fixture so it applies to all test files:

```python
# In tests/conftest.py
import queue
import pytest


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Per Loop 2 iter 4 I-Hk3: reset module state between tests across all files."""
    from auto_cmd import (
        _heartbeat_failures_q,
        _reset_drain_state_for_tests,
        _reset_breadcrumb_flags_for_tests,
    )

    # Drain any residuals
    while not _heartbeat_failures_q.empty():
        try:
            _heartbeat_failures_q.get_nowait()
        except queue.Empty:
            break
    _reset_drain_state_for_tests()
    _reset_breadcrumb_flags_for_tests()
    yield
    # Same drain after
    while not _heartbeat_failures_q.empty():
        try:
            _heartbeat_failures_q.get_nowait()
        except queue.Empty:
            break
    _reset_drain_state_for_tests()
    _reset_breadcrumb_flags_for_tests()
```

- [ ] **Step 3: Remove duplicate from test_auto_progress.py**

Delete the local autouse fixture in `test_auto_progress.py` (now provided by conftest).

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/ -v -x
git add tests/conftest.py tests/test_auto_progress.py
git commit -m "refactor: promote autouse module-state fixture to conftest.py (I-Hk3)"
```

---

### Task S1-23: I-Hk4 — bytecode-deploy fragility fix (remove or guard inspect.getsource)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`

- [ ] **Step 1: Locate the runtime assertion**

```bash
grep -n "inspect.getsource\|_is_owned" skills/sbtdd/scripts/auto_cmd.py
```

- [ ] **Step 2: Add graceful fallback**

```python
# Defensive: ensure no private API regression in _with_file_lock.
# Per I-Hk4 fix: fragility under bytecode-only deployments.
try:
    _with_file_lock_source = inspect.getsource(_with_file_lock)
    assert "_is_owned" not in _with_file_lock_source, (
        "_with_file_lock must not depend on threading.RLock private API"
    )
    del _with_file_lock_source
except (OSError, TypeError):
    # Bytecode-only deployment; unit test in tests/test_auto_progress.py
    # covers the regression check at test time.
    pass
```

- [ ] **Step 3: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py
git commit -m "fix: graceful fallback for inspect.getsource under bytecode deploy (I-Hk4)"
```

---

### Task S1-24: I-Hk5 — document Windows kill-path race accepted-risk

**Files:**
- Modify: `skills/sbtdd/scripts/subprocess_utils.py`

- [ ] **Step 1: Add module-level or function-level docstring note**

In `skills/sbtdd/scripts/subprocess_utils.py`, near the Windows reader-thread fallback:

```python
def _windows_threaded_reader_pump(...):
    """Reader-thread fallback for Windows pipes (selectors.DefaultSelector
    fails on Windows pipes).

    .. note:: Loop 2 iter 4 I-Hk5 — accepted-risk: kill-path race window.
       Despite W7 drain after `_kill_subprocess_tree`, residual reader-thread
       chunks may arrive between kill issuance and reader thread observing
       EOF. Pre-existing single-thread auto_cmd invariant means this race
       is theoretical under current usage. v1.x re-evaluation: if observable
       in field, evaluate locked reader-thread shutdown.
    """
```

- [ ] **Step 2: Commit**

```bash
git add skills/sbtdd/scripts/subprocess_utils.py
git commit -m "docs: document Windows kill-path race as accepted risk (I-Hk5)"
```

---

### Task S1-26: Spec-snapshot drift check at pre-merge entry (CRITICAL #2)

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Modify: `tests/test_pre_merge_streaming.py` (or extend a more apt
  pre_merge test module)

**Background (CRITICAL #2 fix):** spec sec.3.2 / Escenario H2-3 promises
that pre-merge fails when scenarios drifted between plan approval and
merge. Subagent #2 ships the helpers (`spec_snapshot.emit_snapshot`,
`compare`, `load_snapshot`) but NO task wires them into the pre-merge
gate entry. This task closes the wiring gap on the consumer side.

- [ ] **Step 1: Write failing test for H2-3 drift detection**

```python
def test_h2_3_pre_merge_raises_on_spec_snapshot_drift(tmp_path, monkeypatch):
    """H2-3: pre_merge_cmd._check_spec_snapshot_drift raises PreMergeError when scenarios changed."""
    from pre_merge_cmd import _check_spec_snapshot_drift
    from errors import PreMergeError

    # Persisted snapshot at plan-approval time.
    persisted = tmp_path / "spec-snapshot.json"
    persisted.write_text(
        '{"S1: parser handles empty input": "old-hash"}', encoding="utf-8"
    )
    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder; emit_snapshot is monkeypatched", encoding="utf-8")

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1: parser handles empty input": "new-hash"},
    )

    with pytest.raises(PreMergeError) as excinfo:
        _check_spec_snapshot_drift(spec_path=spec, snapshot_path=persisted)
    msg = str(excinfo.value)
    assert "S1: parser handles empty input" in msg
    assert "re-approve" in msg.lower() or "re-run" in msg.lower()


def test_h2_3_pre_merge_passes_when_no_drift(tmp_path, monkeypatch):
    """H2-3: no drift -> _check_spec_snapshot_drift returns None silently."""
    from pre_merge_cmd import _check_spec_snapshot_drift

    persisted = tmp_path / "spec-snapshot.json"
    persisted.write_text('{"S1": "matching"}', encoding="utf-8")
    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot", lambda _p: {"S1": "matching"},
    )

    # Returns None (no exception).
    assert _check_spec_snapshot_drift(spec_path=spec, snapshot_path=persisted) is None


def test_h2_3_missing_snapshot_warns_but_does_not_block(tmp_path, monkeypatch, capsys):
    """H2-3: missing snapshot file -> stderr breadcrumb, no PreMergeError.

    Backward compat: pre-v1.0.0 plan-approval flows did not emit a
    snapshot. Pre-merge logs a warning but does not block.
    """
    from pre_merge_cmd import _check_spec_snapshot_drift

    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")
    snapshot_path = tmp_path / "spec-snapshot.json"  # does not exist

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot", lambda _p: {"S1": "anything"},
    )

    assert _check_spec_snapshot_drift(spec_path=spec, snapshot_path=snapshot_path) is None
    captured = capsys.readouterr()
    assert "spec-snapshot.json" in captured.err
```

- [ ] **Step 2: Run + verify fail**

Expected: `ImportError` for `_check_spec_snapshot_drift` not yet defined.

- [ ] **Step 3: Implement `_check_spec_snapshot_drift` in pre_merge_cmd.py**

```python
import sys
import spec_snapshot
from errors import PreMergeError


def _check_spec_snapshot_drift(
    *, spec_path: Path, snapshot_path: Path,
) -> None:
    """Verify spec scenarios have not drifted since plan approval.

    Raises:
        PreMergeError: when persisted snapshot differs from current spec
            (added, removed, or modified scenarios).

    Backward compat: missing ``snapshot_path`` (pre-v1.0.0 plan-approval
    flows) emits a stderr breadcrumb and returns silently.
    """
    if not snapshot_path.exists():
        sys.stderr.write(
            f"[sbtdd pre-merge] no spec-snapshot.json at {snapshot_path}; "
            f"drift check skipped (pre-v1.0.0 plan-approval flow). "
            f"Re-approve plan to enable drift detection.\n"
        )
        sys.stderr.flush()
        return

    prev = spec_snapshot.load_snapshot(snapshot_path)
    curr = spec_snapshot.emit_snapshot(spec_path)
    diff = spec_snapshot.compare(prev, curr)
    if diff["added"] or diff["removed"] or diff["modified"]:
        raise PreMergeError(
            f"Spec scenarios changed since plan approval; re-approve plan "
            f"via /writing-plans + Checkpoint 2.\n"
            f"  added: {diff['added']}\n"
            f"  removed: {diff['removed']}\n"
            f"  modified: {diff['modified']}"
        )
```

- [ ] **Step 4: Wire `_check_spec_snapshot_drift` into pre-merge entry**

Locate the existing pre-merge entrypoint (the function that runs before
Loop 1; near the top of `_loop2`'s caller, or the CLI handler) and add
the drift check at entry, before any work is done:

```python
spec_path = root / "sbtdd" / "spec-behavior.md"
snapshot_path = root / "planning" / "spec-snapshot.json"
_check_spec_snapshot_drift(spec_path=spec_path, snapshot_path=snapshot_path)
```

- [ ] **Step 5: Run + verify pass + commit**

```bash
pytest tests/test_pre_merge_streaming.py -k "h2_3" -v
git add skills/sbtdd/scripts/pre_merge_cmd.py tests/test_pre_merge_streaming.py
git commit -m "feat: add spec-snapshot drift check at pre-merge entry (CRITICAL #2)"
```

---

### Task S1-27: Plan-approval snapshot emit hook (CRITICAL #2)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (and/or
  `skills/sbtdd/scripts/state_file.py` if plan-approval transitions live
  there; pre-flight grep to locate)
- Modify: `tests/test_auto_progress.py`

**Background (CRITICAL #2 fix):** the spec-snapshot drift check at
pre-merge entry (S1-26) requires a persisted ``planning/spec-snapshot.json``
emitted at plan-approval time. This task wires the emit hook to fire when
``plan_approved_at`` is set in the state file (template sec.5 "Excepcion
bajo plan aprobado" trigger).

- [ ] **Step 1: Survey plan-approval handler location**

```bash
grep -n "plan_approved_at\b" skills/sbtdd/scripts/*.py | head -20
```

Locate the helper that sets ``plan_approved_at`` on the state file.
Likely candidates: ``state_file.set_plan_approved`` (Subagent #1 surface
indirectly via ``auto_cmd``) or ``auto_cmd._mark_plan_approved`` if it
exists. If the helper lives in ``state_file.py`` (Subagent #2-adjacent),
adapt by adding the snapshot emit at the auto_cmd-level wrapper that
calls it; never reach into Subagent #2 surfaces.

- [ ] **Step 2: Write failing test asserting snapshot emitted on plan approval**

```python
def test_plan_approval_emits_spec_snapshot(tmp_path, monkeypatch):
    """CRITICAL #2: when plan_approved_at is set, spec-snapshot.json written."""
    from auto_cmd import _mark_plan_approved_with_snapshot
    import json

    # Create minimal repo skeleton.
    (tmp_path / "sbtdd").mkdir()
    (tmp_path / "planning").mkdir()
    (tmp_path / ".claude").mkdir()
    spec = tmp_path / "sbtdd" / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")

    captured = {}
    def fake_emit(p):
        captured["spec_path"] = p
        return {"S1: x": "hash1"}

    monkeypatch.setattr("spec_snapshot.emit_snapshot", fake_emit)

    _mark_plan_approved_with_snapshot(root=tmp_path)

    snapshot_path = tmp_path / "planning" / "spec-snapshot.json"
    assert snapshot_path.exists()
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert data == {"S1: x": "hash1"}
    assert captured["spec_path"] == spec
```

- [ ] **Step 3: Implement `_mark_plan_approved_with_snapshot`**

```python
import spec_snapshot


def _mark_plan_approved_with_snapshot(*, root: Path) -> None:
    """Persist spec-snapshot at plan-approval time (CRITICAL #2).

    Wired into the plan-approval transition: when the state file gets
    ``plan_approved_at`` set (template sec.5 "Excepcion bajo plan
    aprobado" trigger), this helper emits the current spec scenarios
    snapshot and persists it to ``planning/spec-snapshot.json``. The
    pre-merge gate (S1-26 ``_check_spec_snapshot_drift``) consumes this
    snapshot.
    """
    spec_path = root / "sbtdd" / "spec-behavior.md"
    snapshot_path = root / "planning" / "spec-snapshot.json"
    snapshot = spec_snapshot.emit_snapshot(spec_path)
    spec_snapshot.persist_snapshot(snapshot_path, snapshot)
```

- [ ] **Step 4: Wire into existing plan-approval transition**

Find the call site that currently sets ``plan_approved_at`` in
``state_file.session-state.json`` (per pre-flight grep in Step 1) and
invoke ``_mark_plan_approved_with_snapshot(root=...)`` immediately
afterwards. Idempotent: re-approving the plan re-emits the snapshot
(``persist_snapshot`` overwrites).

- [ ] **Step 5: Run + verify pass + commit**

```bash
pytest tests/test_auto_progress.py -k "plan_approval_emits" -v
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: emit spec-snapshot on plan approval (CRITICAL #2)"
```

---

### Task S1-28: J3+J7 wiring sweep test (CRITICAL #5)

**Files:**
- Modify: `tests/test_dispatch_heartbeat_wiring.py` (extend with sweep
  assertion)

**Background (CRITICAL #5 fix):** spec sec.4.1 W1 promises ALL 33
``run_with_timeout`` callers in ``auto_cmd.py`` + ``pre_merge_cmd.py``
are routed through ``run_streamed_with_timeout``. Tasks S1-10..S1-15
test ~6 representative sites, one per cluster, leaving the bulk of
sites unverified. This task closes the coverage gap with a single
AST-walk assertion that fails if any production site still calls the
unwired ``run_with_timeout``.

- [ ] **Step 1: Append sweep test to test_dispatch_heartbeat_wiring.py**

```python
def test_w1_sweep_no_remaining_run_with_timeout_in_production():
    """W1 sweep (CRITICAL #5): ALL 33 callers must route through run_streamed_with_timeout.

    AST-walks auto_cmd.py + pre_merge_cmd.py and asserts no remaining
    `subprocess_utils.run_with_timeout(...)` callsites. Helper definition
    itself in subprocess_utils.py is excluded (not in the scanned set).
    Test files excluded by virtue of not being in the production path
    list. Failure message lists file:line of unwired sites for triage.
    """
    import ast
    from pathlib import Path

    production_paths = [
        Path("skills/sbtdd/scripts/auto_cmd.py"),
        Path("skills/sbtdd/scripts/pre_merge_cmd.py"),
    ]
    unwired_sites: list[str] = []
    for path in production_paths:
        assert path.exists(), f"production file missing: {path}"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            # Match `subprocess_utils.run_with_timeout(...)` (Attribute access).
            if isinstance(func, ast.Attribute) and func.attr == "run_with_timeout":
                unwired_sites.append(f"{path}:{node.lineno}")
            # Match bare `run_with_timeout(...)` (Name access — direct import).
            elif isinstance(func, ast.Name) and func.id == "run_with_timeout":
                unwired_sites.append(f"{path}:{node.lineno}")

    assert unwired_sites == [], (
        f"v1.0.0 W1 contract violation: production sites still call "
        f"run_with_timeout (must use run_streamed_with_timeout):\n"
        + "\n".join(f"  {s}" for s in unwired_sites)
    )
```

- [ ] **Step 2: Run + verify pass**

Pre-S1-10..S1-15: this test FAILS by listing all 33 unwired sites.
Post-S1-10..S1-15: the test PASSES because every callsite has been
migrated. The test acts as a coverage backstop for the per-cluster
tests, catching any cluster missed by the manual partition in
S1-10..S1-15.

```bash
pytest tests/test_dispatch_heartbeat_wiring.py::test_w1_sweep_no_remaining_run_with_timeout_in_production -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_dispatch_heartbeat_wiring.py
git commit -m "test: sweep all 33 J3+J7 wiring sites (CRITICAL #5)"
```

**Ordering note:** S1-28 lands AFTER S1-15 (last per-cluster site
migration); pre-S1-15 the sweep test is a deliberate failing tripwire
ensuring complete coverage. Subagent #1 sequential ordering: S1-1..S1-9
(Pillar 1 Feature G + F44.3 + J2) → S1-10..S1-15 (J3+J7 per-cluster
migration) → S1-16..S1-19 (Caspar W4-W7) → S1-20 (Windows W8) →
S1-21..S1-24 (5 INFOs) → S1-26..S1-27 (CRITICAL #2 spec-snapshot wiring)
→ S1-28 (CRITICAL #5 sweep) → S1-25 (final make verify).

---

### Task S1-25: Final make verify pass for Subagent #1

- [ ] **Step 1: Run full make verify**

```bash
make verify
```

Expected: pytest pass (930 baseline + ~30-40 new tests), ruff check + format clean, mypy --strict clean, runtime ≤ 120s (NF-A).

- [ ] **Step 2: Report DONE**

Verify all S1-1 through S1-24 commits landed cleanly. Report `DONE: Subagent #1` with commit list.

---

## Subagent #2 — Schema + new scripts + writing-plans extension (9 tasks)

### Task S2-1: ResolvedModels dataclass in models.py

**Files:**
- Modify: `skills/sbtdd/scripts/models.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_models.py`:

```python
def test_resolved_models_dataclass_shape():
    """Spec sec.5.1: ResolvedModels has implementer/spec_reviewer/code_review/magi_dispatch fields."""
    from models import ResolvedModels

    rm = ResolvedModels(
        implementer="claude-sonnet-4-6",
        spec_reviewer="claude-sonnet-4-6",
        code_review="claude-sonnet-4-6",
        magi_dispatch="claude-opus-4-7",
    )
    assert rm.implementer == "claude-sonnet-4-6"
    assert rm.magi_dispatch == "claude-opus-4-7"


def test_resolved_models_is_frozen():
    """Spec sec.5.1: ResolvedModels frozen dataclass."""
    from models import ResolvedModels
    from dataclasses import FrozenInstanceError

    rm = ResolvedModels(implementer="a", spec_reviewer="b", code_review="c", magi_dispatch="d")
    with pytest.raises(FrozenInstanceError):
        rm.implementer = "z"  # type: ignore[misc]
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add ResolvedModels to models.py**

Append to `skills/sbtdd/scripts/models.py`:

```python
@dataclass(frozen=True)
class ResolvedModels:
    """Cached preflight resolution of per-skill model IDs (spec sec.5.1).

    Resolved once at task-loop entry per auto run via
    `auto_cmd._resolve_all_models_once(config)`. All dispatches read
    from this cache instead of re-resolving CLAUDE.md + plugin.local.md
    (~70-150 disk reads per 36-task run reduced to 1).

    INV-0 cascade: CLAUDE.md model pin (per `INV_0_PINNED_MODEL_RE`)
    overrides plugin.local.md fields silently; stderr breadcrumb emitted.
    """

    implementer: str
    spec_reviewer: str
    code_review: str
    magi_dispatch: str
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_models.py -k "resolved_models" -v
git add skills/sbtdd/scripts/models.py tests/test_models.py
git commit -m "feat: add ResolvedModels frozen dataclass (J2 sec.5.1)"
```

---

### Task S2-2: PluginConfig.magi_cross_check field

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_config.py`:

```python
def test_plugin_config_magi_cross_check_default_false(tmp_path):
    """Feature G: magi_cross_check field defaults to False (opt-in per balthasar WARNING)."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
---
"""
    config_path = tmp_path / "p.md"
    config_path.write_text(base, encoding="utf-8")
    from config import load_plugin_local

    cfg = load_plugin_local(config_path)
    assert cfg.magi_cross_check is False


def test_plugin_config_magi_cross_check_can_be_disabled(tmp_path):
    """G4 opt-out: magi_cross_check: false respected."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
magi_cross_check: false
---
"""
    config_path = tmp_path / "p.md"
    config_path.write_text(base, encoding="utf-8")
    from config import load_plugin_local

    cfg = load_plugin_local(config_path)
    assert cfg.magi_cross_check is False
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add field to PluginConfig**

In `skills/sbtdd/scripts/config.py`, modify `PluginConfig`:

```python
@dataclass(frozen=True)
class PluginConfig:
    # ... existing fields ...

    # v1.0.0 Feature G — default OFF (opt-in per balthasar Loop 2 iter 1
    # WARNING: recursive dogfood circular risk). Operator opts in via
    # `magi_cross_check: true` in plugin.local.md.
    magi_cross_check: bool = False
```

In `load_plugin_local`, add default:

```python
# v1.0.0: default False (opt-in initially) — see balthasar Loop 2 iter 1
# WARNING + sec.5.2 v1.x default-flip criteria.
data.setdefault("magi_cross_check", False)
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_config.py -k "magi_cross_check" -v
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "feat: add PluginConfig.magi_cross_check field defaulting to False (sec.5.2)"
```

---

### Task S2-3: PluginConfig.schema_version field + INV-36

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for I1, I2**

Append to `tests/test_config.py`:

```python
def test_i1_v0_5_0_files_load_as_schema_version_1(tmp_path):
    """I1: plugin.local.md without schema_version field defaults to 1."""
    # Use the test_plugin_config_observability_fields_overridable fixture as base
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
---
"""
    config_path = tmp_path / "p.md"
    config_path.write_text(base, encoding="utf-8")
    from config import load_plugin_local

    cfg = load_plugin_local(config_path)
    assert cfg.schema_version == 1


def test_i2_v1_0_0_files_declare_schema_version_2(tmp_path):
    """I2: plugin.local.md with schema_version: 2 parses correctly."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
schema_version: 2
---
"""
    config_path = tmp_path / "p.md"
    config_path.write_text(base, encoding="utf-8")
    from config import load_plugin_local

    cfg = load_plugin_local(config_path)
    assert cfg.schema_version == 2
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add schema_version field**

In `config.py`:

```python
@dataclass(frozen=True)
class PluginConfig:
    # ... existing fields ...

    # v1.0.0 Feature I (INV-36)
    schema_version: int = 1
```

In `load_plugin_local`:

```python
data.setdefault("schema_version", 1)
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_config.py -k "schema_version" -v
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "feat: add PluginConfig.schema_version field + INV-36 (Feature I)"
```

---

### Task S2-4: scripts/migrate_plugin_local.py skeleton

**Files:**
- Create: `skills/sbtdd/scripts/migrate_plugin_local.py`
- Create: `tests/test_migrate_plugin_local.py`

- [ ] **Step 1: Write failing tests for I3, I4**

Create `tests/test_migrate_plugin_local.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for v1.0.0 Feature I migration tool skeleton (sec.3.1)."""

from __future__ import annotations

import pytest


def test_i3_migrate_v1_to_v2_is_no_op_skeleton():
    """I3: v1 -> v2 migration is no-op skeleton (just adds schema_version field)."""
    from migrate_plugin_local import migrate_to

    v1_data = {"stack": "python", "author": "Julian Bolivar"}
    result = migrate_to(target_version=2, data=v1_data)
    assert result["stack"] == "python"
    assert result["author"] == "Julian Bolivar"
    assert result["schema_version"] == 2


def test_i4_migration_ladder_supports_future_bumps():
    """I4: MIGRATIONS dict has v1 entry; future bumps add entries."""
    from migrate_plugin_local import MIGRATIONS

    assert 1 in MIGRATIONS
    assert callable(MIGRATIONS[1])
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Create migrate_plugin_local.py skeleton**

Create `skills/sbtdd/scripts/migrate_plugin_local.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""plugin.local.md schema migration tool skeleton (Feature I, INV-36).

Per spec sec.3.1: migrations tracked in MIGRATIONS dict; each entry is a
callable taking the current dict and returning the dict at the next
schema version. v1 -> v2 is a no-op skeleton (just adds the field).

Future migrations populate the ladder. Operator runs:
    python -m migrate_plugin_local <plugin.local.md path> --to <target_version>
"""

from __future__ import annotations

from typing import Any, Callable


def _v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """No-op migration v1 -> v2: just declare schema_version=2."""
    return {**data, "schema_version": 2}


#: Migration ladder. Each key N is "starting from version N+1 produces target".
#: To add a v2 -> v3 migration, append `2: _v2_to_v3` and define the callable.
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _v1_to_v2,
}


def migrate_to(*, target_version: int, data: dict[str, Any]) -> dict[str, Any]:
    """Migrate data dict to the target schema version.

    Walks the MIGRATIONS ladder from current version (data.get('schema_version', 1))
    up to target_version, applying each step.

    Args:
        target_version: Target schema_version to migrate to.
        data: Parsed plugin.local.md frontmatter dict.

    Returns:
        Migrated dict at the target schema version.
    """
    current = data.get("schema_version", 1)
    while current < target_version:
        if current not in MIGRATIONS:
            raise ValueError(
                f"No migration defined from schema_version {current} "
                f"to {current + 1}. Add an entry to MIGRATIONS dict."
            )
        data = MIGRATIONS[current](data)
        current += 1
    return data
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_migrate_plugin_local.py -v
git add skills/sbtdd/scripts/migrate_plugin_local.py tests/test_migrate_plugin_local.py
git commit -m "feat: add migrate_plugin_local.py skeleton with v1->v2 no-op (Feature I)"
```

---

### Task S2-5: scripts/spec_snapshot.py emit_snapshot

**Files:**
- Create: `skills/sbtdd/scripts/spec_snapshot.py`
- Create: `tests/test_spec_snapshot.py`

- [ ] **Step 1: Write failing test for emit_snapshot (H2-1)**

Create `tests/test_spec_snapshot.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for v1.0.0 Feature H option 2 spec-snapshot (sec.3.2)."""

from __future__ import annotations

import pytest
from pathlib import Path


def test_h2_1_emit_snapshot_extracts_scenario_hashes(tmp_path):
    """H2-1: emit_snapshot returns {scenario_title: hash} per scenario."""
    from spec_snapshot import emit_snapshot

    spec = tmp_path / "spec-behavior.md"
    spec.write_text("""# BDD overlay

## §4 Escenarios BDD

**Escenario S1: parser handles empty input**

> **Given** empty input
> **When** parse() is called
> **Then** returns []

**Escenario S2: parser handles whitespace**

> **Given** whitespace input
> **When** parse() is called
> **Then** returns []
""", encoding="utf-8")

    snapshot = emit_snapshot(spec)
    assert "S1: parser handles empty input" in snapshot or "S1" in str(snapshot)
    assert isinstance(snapshot, dict)
    assert len(snapshot) >= 2  # at least S1 and S2


def test_h2_1_hash_deterministic_for_same_content(tmp_path):
    """H2-1: same scenario content yields same hash on multiple emits."""
    from spec_snapshot import emit_snapshot

    spec_text = """# BDD overlay

## §4 Escenarios BDD

**Escenario S1: empty input**

> **Given** x
> **When** y
> **Then** z
"""
    spec1 = tmp_path / "s1.md"
    spec1.write_text(spec_text, encoding="utf-8")
    spec2 = tmp_path / "s2.md"
    spec2.write_text(spec_text, encoding="utf-8")

    snap1 = emit_snapshot(spec1)
    snap2 = emit_snapshot(spec2)
    assert snap1 == snap2


def test_emit_snapshot_raises_when_no_escenarios_section(tmp_path):
    """WARNING melchior zero-match guard: missing §4 section raises ValueError."""
    from spec_snapshot import emit_snapshot

    spec = tmp_path / "spec.md"
    spec.write_text("# spec without scenarios section", encoding="utf-8")
    with pytest.raises(ValueError, match="No §4 Escenarios section"):
        emit_snapshot(spec)


def test_emit_snapshot_raises_when_section_empty(tmp_path):
    """WARNING melchior zero-match guard: empty §4 section raises ValueError.

    Silent {} would compare equal to another empty {} from a similarly
    broken spec, masking real drift.
    """
    from spec_snapshot import emit_snapshot

    spec = tmp_path / "spec.md"
    spec.write_text("""# spec

## §4 Escenarios BDD

(no scenario blocks)

## §5 next section
""", encoding="utf-8")
    with pytest.raises(ValueError, match="zero scenarios"):
        emit_snapshot(spec)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Create spec_snapshot.py with emit_snapshot**

Create `skills/sbtdd/scripts/spec_snapshot.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Spec scenario snapshot + diff for v1.0.0 Feature H option 2 (sec.3.2).

emit_snapshot parses spec-behavior.md sec.4 Escenarios block, extracts
scenario title + Given/When/Then text per scenario, hashes the
whitespace-normalized content. Pre-merge gate compares against previous
snapshot to detect spec drift between plan approval and merge.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# Regex for scenario blocks: matches "**Escenario <title>**" + Given/When/Then text
_SCENARIO_RE = re.compile(
    r"^\*\*Escenario\s+([^\*]+?)\*\*\s*\n+(.*?)(?=^\*\*Escenario\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _normalize(text: str) -> str:
    """Whitespace-normalize text so trivial reformats don't change hash."""
    return re.sub(r"\s+", " ", text.strip())


def emit_snapshot(spec_path: Path) -> dict[str, str]:
    """Parse spec sec.4 Escenarios; return {scenario_title: hash}.

    Args:
        spec_path: Path to sbtdd/spec-behavior.md.

    Returns:
        Dict mapping scenario title (without ``**Escenario ... **`` prefix)
        to SHA-256 hex hash of normalized scenario body.

    Raises:
        ValueError: when no §4 Escenarios section is found OR the section
            contains zero scenario blocks. Per WARNING melchior zero-match
            guard: silently returning ``{}`` would later compare equal to
            another empty snapshot from a similarly broken spec, masking
            real drift.
    """
    text = spec_path.read_text(encoding="utf-8")
    # Constrain matching to the §4 Escenarios section so unrelated bold
    # text earlier/later in the spec doesn't accidentally match the
    # `**Escenario` regex.
    section_match = re.search(
        r"##\s*§?4[^\n]*Escenarios[\s\S]*?(?=^##\s|\Z)",
        text, re.MULTILINE,
    )
    if not section_match:
        raise ValueError(
            f"No §4 Escenarios section found in {spec_path}; "
            f"spec-snapshot drift detection requires the section header."
        )
    section_text = section_match.group(0)
    snapshot: dict[str, str] = {}
    for match in _SCENARIO_RE.finditer(section_text):
        title = match.group(1).strip()
        body = match.group(2).strip()
        normalized = _normalize(body)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        snapshot[title] = digest
    if not snapshot:
        raise ValueError(
            f"§4 Escenarios section in {spec_path} contains zero scenarios; "
            f"refusing to emit empty snapshot (would mask drift)."
        )
    return snapshot
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_spec_snapshot.py -v
git add skills/sbtdd/scripts/spec_snapshot.py tests/test_spec_snapshot.py
git commit -m "feat: add spec_snapshot.emit_snapshot (H2-1)"
```

---

### Task S2-6: spec_snapshot compare + persist

**Files:**
- Modify: `skills/sbtdd/scripts/spec_snapshot.py`
- Modify: `tests/test_spec_snapshot.py`

- [ ] **Step 1: Write failing tests for H2-2, H2-4**

Append to `tests/test_spec_snapshot.py`:

```python
def test_h2_2_compare_detects_modifications():
    """H2-2: compare returns added/removed/modified lists."""
    from spec_snapshot import compare

    prev = {"S1": "hashA", "S2": "hashB"}
    curr = {"S1": "hashA", "S2": "hashB-MODIFIED", "S3": "hashC"}

    diff = compare(prev, curr)
    assert diff["added"] == ["S3"]
    assert diff["removed"] == []
    assert diff["modified"] == ["S2"]


def test_h2_4_persist_snapshot_to_planning_dir(tmp_path):
    """H2-4: persist_snapshot writes JSON to planning/spec-snapshot.json."""
    from spec_snapshot import persist_snapshot
    import json

    snapshot = {"S1": "hash1", "S2": "hash2"}
    target = tmp_path / "spec-snapshot.json"
    persist_snapshot(target, snapshot)

    data = json.loads(target.read_text(encoding="utf-8"))
    assert data == snapshot


def test_load_snapshot_round_trip(tmp_path):
    """Sanity: persist then load round-trip."""
    from spec_snapshot import persist_snapshot, load_snapshot

    snapshot = {"S1": "abc", "S2": "def"}
    target = tmp_path / "snap.json"
    persist_snapshot(target, snapshot)
    loaded = load_snapshot(target)
    assert loaded == snapshot
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add compare + persist + load**

Append to `spec_snapshot.py`:

```python
import json


def compare(prev: dict[str, str], curr: dict[str, str]) -> dict[str, list[str]]:
    """Return {'added': [...], 'removed': [...], 'modified': [...]}.

    Args:
        prev: Previous snapshot (e.g., from plan-approval time).
        curr: Current snapshot (e.g., from pre-merge time).

    Returns:
        Dict with keys 'added' (in curr not in prev), 'removed' (in prev
        not in curr), 'modified' (in both but different hash).
    """
    prev_titles = set(prev.keys())
    curr_titles = set(curr.keys())
    return {
        "added": sorted(curr_titles - prev_titles),
        "removed": sorted(prev_titles - curr_titles),
        "modified": sorted(
            t for t in (prev_titles & curr_titles) if prev[t] != curr[t]
        ),
    }


def persist_snapshot(path: Path, snapshot: dict[str, str]) -> None:
    """Write snapshot to JSON file (used post-plan-approval)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")


def load_snapshot(path: Path) -> dict[str, str]:
    """Load previously persisted snapshot."""
    return json.loads(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_spec_snapshot.py -v
git add skills/sbtdd/scripts/spec_snapshot.py tests/test_spec_snapshot.py
git commit -m "feat: spec_snapshot compare + persist + load helpers (H2-2/H2-4)"
```

---

### Task S2-7: Group B option 5 — writing-plans prompt extension

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
- Modify: `tests/test_superpowers_dispatch.py`

- [ ] **Step 1: Write failing test for prompt extension**

Append to `tests/test_superpowers_dispatch.py`:

```python
def test_h5_1_invoke_writing_plans_prompt_includes_scenario_stub_directive(monkeypatch):
    """H5-1: invoke_writing_plans prompt instructs auto-generate scenario stubs."""
    from superpowers_dispatch import invoke_writing_plans

    captured: dict = {}
    def fake_invoke(*, prompt: str, **kwargs):
        captured["prompt"] = prompt
        return {"output": "stub plan content"}

    monkeypatch.setattr(
        "superpowers_dispatch._invoke_skill", fake_invoke,
    )
    invoke_writing_plans(spec_path="sbtdd/spec-behavior.md")
    assert "scenario stub" in captured["prompt"].lower()
    assert "pytest.skip" in captured["prompt"]
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add scenario-stub directive to invoke_writing_plans prompt**

In `superpowers_dispatch.py`:

```python
_WRITING_PLANS_STUB_DIRECTIVE = """

## Auto-generated scenario stubs (Feature H option 5)

For each scenario in the spec's §4 Escenarios BDD section, generate a
stub test in the plan's task list with:
- Function name: `test_scenario_<N>_<slug>()` where N is the scenario
  number and slug is a snake_case version of the title.
- Body: `pytest.skip("Scenario stub: replace with real assertions")`.
- Docstring: reference the scenario number + title.

Plan authors replace stub bodies with real assertions before MAGI Checkpoint 2.
Missing any stub at Checkpoint 2 = plan-quality failure.
"""


def invoke_writing_plans(*, spec_path: str, **kwargs: Any) -> dict[str, Any]:
    """Invoke /writing-plans superpowers skill.

    Per spec sec.3.3 H5: extended prompt directs auto-generation of
    scenario stubs per spec §4 Escenarios.
    """
    base_prompt = f"Generate TDD plan from {spec_path}"
    extended_prompt = base_prompt + _WRITING_PLANS_STUB_DIRECTIVE
    return _invoke_skill(prompt=extended_prompt, skill="writing-plans", **kwargs)
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_superpowers_dispatch.py -k "writing_plans" -v
git add skills/sbtdd/scripts/superpowers_dispatch.py tests/test_superpowers_dispatch.py
git commit -m "feat: writing-plans prompt extension auto-generates scenario stubs (H5-1)"
```

---

### Task S2-8: I-Hk2 — INV-34 messages append unit suffix

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing test asserting unit suffix in INV-34 messages**

Append to `tests/test_config.py`:

```python
def test_i_hk2_inv34_clause_messages_append_unit_suffix(tmp_path):
    """I-Hk2: INV-34 ValidationError messages include 's' (seconds) unit."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 50
auto_heartbeat_interval_seconds: 15
---
"""
    config_path = tmp_path / "p.md"
    config_path.write_text(base, encoding="utf-8")
    from config import load_plugin_local
    from errors import ValidationError

    with pytest.raises(ValidationError) as excinfo:
        load_plugin_local(config_path)
    msg = str(excinfo.value)
    # Per I-Hk2: messages should include 's' unit suffix
    assert "got 50s" in msg or "got 50 s" in msg.lower()
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Update INV-34 ValidationError messages**

In `config.py`, replace each `got {timeout}` / `got {interval}` with `got {timeout}s` / `got {interval}s`:

```python
if timeout < 600:
    raise ValidationError(
        f"INV-34 clause 4: auto_per_stream_timeout_seconds must be >= 600s "
        f"(caspar opus runs observed empirically up to 10min); got {timeout}s"
    )
# ... and similar for clauses 1, 2, 3 ...
```

- [ ] **Step 4: Run + verify pass + commit**

```bash
pytest tests/test_config.py -k "inv34" -v
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "fix: append 's' unit suffix to INV-34 validation messages (I-Hk2)"
```

---

### Task S2-9: Final make verify pass for Subagent #2

- [ ] **Step 1: Run full make verify**

```bash
make verify
```

Expected: pytest pass with new tests added, ruff check + format clean, mypy --strict clean.

- [ ] **Step 2: Report DONE**

Verify all S2-1 through S2-8 commits landed cleanly. Report `DONE: Subagent #2` with commit list.

---

## Pre-merge prep (orchestrator-level after both subagents complete)

### Task O-1: `make verify` clean post-merge

- [ ] Run `make verify` locally with both subagent commits merged on the feature branch.
- [ ] Expected: pytest pass (930 baseline + ~30-40 new tests = ~960-970), ruff check 0 warnings, ruff format clean, mypy --strict 0 errors.
- [ ] Total runtime ≤ 120s (NF-A budget).

### Task O-2: Pre-merge MAGI gate (Loop 1 + Loop 2)

- [ ] **Loop 1**: invoke `/requesting-code-review` on diff `<base>..HEAD`. Iterate until clean-to-go (zero CRITICAL + zero high-impact WARNING) or cap=10.
- [ ] **Loop 2**: invoke `/magi:magi` on the cumulative diff. Iterate until verdict ≥ GO_WITH_CAVEATS full no-degraded, OR scope-trim per CHANGELOG `[0.5.0]` Process notes if doesn't converge in 3 iters (INV-0 override only with documented rationale).
- [ ] **Cross-check dogfood (R-Dogfood)**: Feature G should be active during Loop 2 iter 2+ since it shipped in this cycle. Verify cross-check audit artifacts present in `.claude/magi-cross-check/`.

### Task O-3: Version bump 0.5.0 → 1.0.0

- [ ] Modify `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`: bump `"version"` from `0.5.0` to `1.0.0`. Both files MUST match.
- [ ] Add CHANGELOG `[1.0.0]` entry per spec sec.8.2.
- [ ] Commit: `chore: bump to 1.0.0`.

### Task O-4: Tag + push (with explicit user authorization)

- [ ] Create annotated tag: `git tag -a v1.0.0 -m "v1.0.0 MAGI quality + schema/infrastructure + v0.5.1 fold-in"`.
- [ ] **Pause for explicit user authorization before `git push`** (per `~/.claude/CLAUDE.md` Git rules + memory feedback rule).
- [ ] On authorization: merge `feature/v1.0.0-bundle` to `main`, then `git push origin main && git push origin v1.0.0`.

---

## Self-review checklist

- [x] **Spec coverage:** every spec sec.2-4 deliverable mapped to a task. Cross-check:
  - Feature G (sec.2.1, G1-G6) → S1-1 through S1-6 + S2-2 (config field)
  - F44.3 (sec.2.2, F44.3-1/2) → S1-7
  - J2 (sec.2.3, J2-1/2/3) → S1-8 + S1-9 + S2-1 (dataclass)
  - Feature I (sec.3.1, I1-I4) → S2-3 + S2-4
  - Feature H option 2 (sec.3.2, H2-1/2/3/4) → S2-5 + S2-6 (helpers) + **S1-26** (pre-merge drift check wiring) + **S1-27** (plan-approval emit hook wiring)
  - Feature H option 5 (sec.3.3, H5-1/2) → S2-7
  - J3+J7 wiring (sec.4.1, W1-W3) → S1-10 through S1-15 (6 site clusters)
  - Caspar W4-W7 → S1-16 through S1-19
  - Windows W8 → S1-20
  - 5 INFOs (I-Hk1-5) → S1-21, S1-22, S1-23, S1-24 + S2-8
- [x] **Placeholder scan:** no "TBD", "implement later", "similar to Task N" without code, etc.
- [x] **Type consistency:** ResolvedModels, PluginConfig fields, spec_snapshot helpers used consistently across S1 + S2 tasks per cross-subagent contract sec.5.

---

## Execution Handoff

**Plan complete and saved to `planning/claude-plan-tdd-org.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — orchestrator dispatches a fresh subagent per task, reviews between tasks, fast iteration. Aligns with v0.4.0 + v0.5.0 true parallel pattern (Subagent #1 + Subagent #2 dispatched in single message, surfaces disjoint).

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**

**If Subagent-Driven chosen:**
- REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.
- Per spec sec.6.1 partition (true parallel surfaces 100% disjoint), Subagent #1 + Subagent #2 are dispatched in a SINGLE message with two `Agent` tool calls (validated v0.4.0 + v0.5.0 pattern).
- Each subagent owns its task list strictly per the forbidden-files matrix in pre-flight.

**If Inline Execution chosen:**
- REQUIRED SUB-SKILL: `superpowers:executing-plans`.
- Sequential task-by-task in this session with manual checkpoints.

Note: per project convention (`CLAUDE.local.md` §1 paso 5) the next step **before any execution** is MAGI Checkpoint 2 — invoke `/magi:magi` on `@sbtdd/spec-behavior.md` AND `@planning/claude-plan-tdd-org.md` simultaneously, iterate until verdict ≥ `GO_WITH_CAVEATS` full no-degraded (per CHANGELOG `[0.5.0]` Process commitment, scope-trim default if doesn't converge in 3 iters), write final approved plan to `planning/claude-plan-tdd.md`.
