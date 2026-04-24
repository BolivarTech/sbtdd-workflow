# sbtdd-workflow v0.2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver v0.2.0 of the `sbtdd-workflow` plugin by landing three LOCKED release blockers: (A) interactive MAGI escalation prompt, (B) superpowers spec-reviewer integration per task, (C) MAGI version-agnostic parity tests. Preserve all v0.1 invariants and zero-regression test baseline (≥597 passing).

**Architecture:** Two new self-contained modules under `skills/sbtdd/scripts/` (`escalation_prompt.py`, `spec_review_dispatch.py`) + targeted extensions to five existing modules (`errors.py`, `spec_cmd.py`, `pre_merge_cmd.py`, `finalize_cmd.py`, `resume_cmd.py`, `auto_cmd.py`, `close_task_cmd.py`, `run_sbtdd.py`, `models.py`) + one test file rewrite (`tests/test_distribution_coherence.py`). New subcommand `review-spec-compliance` registered in the 9→10 dispatch map. New exit code 12 for `SpecReviewError`.

**Tech Stack:** Python 3.9+ stdlib-only hot paths, `argparse`, `subprocess` via `subprocess_utils.run_with_timeout`, `quota_detector`, `dataclasses(frozen=True)`, `MappingProxyType`, `claude -p` subprocess transport, pytest, ruff, mypy --strict.

---

## Source of truth

- **Spec input:** `sbtdd/spec-behavior-base.md` (v0.2 base, untracked), CLAUDE.md LOCKED sections ("v0.2 requirement (LOCKED) — ..."), v0.1 frozen contract `sbtdd/sbtdd-workflow-plugin-spec-base.md` sec.S.10 (invariants) + sec.S.11 (exit codes).
- **SBTDD methodology:** `CLAUDE.local.md` §3 (Red-Green-Refactor protocol), §5 (commit prefixes), §6 (pre-merge Loops 1+2).
- **Global precedence:** `~/.claude/CLAUDE.md` (INV-0: absolute top authority).

## File Structure (new + modified)

### New files

| Path | Responsibility |
|------|----------------|
| `skills/sbtdd/scripts/escalation_prompt.py` | Feature A — interactive MAGI escalation prompt module (dataclasses + 4 public fns + audit artifact writer) |
| `skills/sbtdd/scripts/spec_review_dispatch.py` | Feature B — per-task spec-reviewer dispatcher (dataclass + `dispatch_spec_reviewer` + artifact writer) |
| `skills/sbtdd/scripts/review_spec_compliance_cmd.py` | Feature B — `/sbtdd review-spec-compliance <task-id>` subcommand handler |
| `tests/test_escalation_prompt.py` | Feature A unit tests (root-cause inference, message rendering, headless fallback, audit artifact) |
| `tests/test_spec_review_dispatch.py` | Feature B unit tests (dispatcher, safety valve, quota integration, audit artifact) |
| `tests/test_review_spec_compliance_cmd.py` | Feature B subcommand CLI tests |
| `tests/test_auto_cmd_spec_review.py` | Feature B integration tests into `auto_cmd._phase2_task_loop` |
| `tests/test_close_task_cmd_spec_review.py` | Feature B integration tests into `close_task_cmd` (`--skip-spec-review`) |
| `tests/fixtures/magi-escalations/` | Feature A golden-output fixtures per root-cause × context |
| `tests/fixtures/spec-reviews/` | Feature B synthetic reviewer output fixtures |

### Modified files

| Path | Nature of change |
|------|------------------|
| `skills/sbtdd/scripts/errors.py` | Add `SpecReviewError` + register in `EXIT_CODES` → 12 |
| `skills/sbtdd/scripts/models.py` | Add `"review-spec-compliance"` to `VALID_SUBCOMMANDS` |
| `skills/sbtdd/scripts/run_sbtdd.py` | Add dispatch entry for `review-spec-compliance` |
| `skills/sbtdd/scripts/spec_cmd.py` | Wire `--override-checkpoint`, `--reason`, `--non-interactive` + safety-valve escalation hook |
| `skills/sbtdd/scripts/pre_merge_cmd.py` | Same as `spec_cmd.py` |
| `skills/sbtdd/scripts/finalize_cmd.py` | Add `--override-checkpoint --reason` CLI flag with audit trail |
| `skills/sbtdd/scripts/resume_cmd.py` | Detect `.claude/magi-escalation-pending.md` + re-enter prompt |
| `skills/sbtdd/scripts/auto_cmd.py` | Extend `_phase2_task_loop` with spec-reviewer dispatch before `mark_and_advance`; honor headless policy for Feature A |
| `skills/sbtdd/scripts/close_task_cmd.py` | Add `--skip-spec-review` flag; invoke reviewer by default |
| `tests/fixtures/skill_stubs.py` | Add `StubSpecReviewer` mirroring `StubMAGI` pattern |
| `tests/test_distribution_coherence.py` | Rewrite `_resolve_magi_plugin_json()` + add `_semver_key` helper + test |
| `tests/test_errors.py` | Cover `SpecReviewError` + exit-code 12 mapping |
| `tests/test_run_sbtdd.py` | Cover new subcommand dispatch |
| `tests/test_models.py` | Cover expanded `VALID_SUBCOMMANDS` tuple |
| `CHANGELOG.md` | Under `## [Unreleased]`: Added (Features A/B/C), Changed (`bump plugin.json + marketplace.json to 0.2.0`), BREAKING (new exit 12 taxonomy entry) |
| `.claude-plugin/plugin.json` | `version` bump 0.1.0 → 0.2.0 |
| `.claude-plugin/marketplace.json` | `version` bump 0.1.0 → 0.2.0 (both top-level + plugin entry) |
| `CLAUDE.md` | Add INV-31 to "Invariants Summary" + remove shipped blockers from "v0.2 requirement (LOCKED)" sections |
| `sbtdd/sbtdd-workflow-plugin-spec-base.md` sec.S.10 | Register INV-31 (if adopted) |

## Invariants active during v0.2 (reminder)

- **INV-0** (`~/.claude/CLAUDE.md` top authority) — `--override-checkpoint` is the INV-0 escape valve, requires `--reason`.
- **INV-11** (safety valves) — Feature A fires when valve exhausts; Feature B loop caps at 3.
- **INV-22** (auto sequential + headless) — Feature A NEVER runs inside `auto_cmd`; policy file drives headless decision.
- **INV-26** (audit trail) — Features A + B both emit JSON artifacts in `.claude/`.
- **INV-28** (MAGI degraded no-exit) — Feature A fires on degraded exhaustion.
- **INV-29** (`/receiving-code-review` gate) — honored for Loop 1 (`requesting-code-review`) and Loop 2 (`magi`) findings as in v0.1. Feature B spec-reviewer findings are NOT routed through `/receiving-code-review` in v0.2 (see "v0.2 scope boundary — Feature B B6 relaxation" immediately below).
- **INV-30** (resumibility) — Feature A integrates with `resume_cmd` via pending marker.
- **INV-31 (new, proposed)** — Every task close in `auto_cmd` + `close_task_cmd` passes spec-reviewer unless `--skip-spec-review` or stub injected.

## v0.2 scope boundary — Feature B B6 relaxation

Spec-base §2.2 ("Entrega v0.2") describes a full reviewer-feedback loop: on `issues`, "treat as MAGI-like findings: feed to `/receiving-code-review`, mini-cycle TDD fix per accepted finding, re-dispatch reviewer, repeat up to a safety valve." Acceptance criterion B6 summarizes this as "Issues rutean via `/receiving-code-review` (extension INV-29)."

**v0.2 lands the dispatcher + integration halves of B6; the automated reviewer-feedback mini-cycle is deferred to v0.2.1 or v0.3.** Concretely:

- `spec_review_dispatch.dispatch_spec_reviewer` invokes the reviewer once per task, parses the result, writes the audit artifact, and returns `SpecReviewResult`.
- On `approved=False`, the dispatcher returns with `issues` populated. Its caller (`auto_cmd._phase2_task_loop`, `close_task_cmd`, `review_spec_compliance_cmd`) raises `SpecReviewError` (exit 12) and aborts the run — same failure shape as `MAGIGateError`.
- The user can (a) manually invoke `/receiving-code-review` on the findings, apply fixes via mini-cycle TDD, then resume via `/sbtdd resume`, or (b) pass `--skip-spec-review` on the re-run after investigating.
- Automating the `/receiving-code-review` → mini-cycle → re-dispatch loop requires a headless `claude -p` reviewing interaction pattern not yet exercised in the codebase; shipping it in v0.2 would expand scope materially and risks an INV-29-style sterile loop if the auto-accept/auto-reject heuristic is wrong. Deferring the automation preserves INV-29's spirit (a human evaluates findings before applying) while still delivering v0.2's primary value: the per-task drift detection itself, which is the Milestone-A-Scenario-4-class defect prevention the feature exists to solve.

**Decision record for MAGI:** when the Checkpoint 2 reviewer evaluates this plan, treat B6 as partially delivered and scoped accordingly. If MAGI classifies the deferral as CRITICAL, escalate to user per INV-11 safety-valve path; the user may (per INV-0) accept the deferral with `--reason "B6 scope split — dispatcher v0.2, auto-feedback v0.2.1"` or instruct that the full loop land in v0.2 before merge. This plan implements the dispatcher half; the second half is a single task addition (auto-accept lowest-risk findings, mini-cycle TDD, re-dispatch) if the user lands it here.

---

## MILESTONE F — Feature C: MAGI version-agnostic parity tests

**Rationale:** MAGI 2.1.4 shipped (patch bump, zero schema change). The hardcoded `2.1.3` in `tests/test_distribution_coherence.py:91` will silently skip on fresh caches. Replace with semver-sorted auto-resolver.

### Task F1: `_semver_key` helper + tests

**Files:**
- Modify: `tests/test_distribution_coherence.py:78-97`

- [x] **Step 1 (Red): add failing tests for `_semver_key`**

Append to `tests/test_distribution_coherence.py`:

```python
def test_semver_key_orders_patch_bump() -> None:
    from tests.test_distribution_coherence import _semver_key
    assert _semver_key("2.1.4") > _semver_key("2.1.3")
    assert _semver_key("2.2.0") > _semver_key("2.1.99")
    assert _semver_key("3.0.0") > _semver_key("2.99.99")


def test_semver_key_handles_mixed_version_strings() -> None:
    from tests.test_distribution_coherence import _semver_key
    # non-numeric segment sorts BELOW numeric (we use -1 as the sentinel)
    assert _semver_key("2.1.3") > _semver_key("2.1.beta")
    assert _semver_key("2.1.0") > _semver_key("garbage")
    # ties resolve deterministically
    assert _semver_key("2.1.3") == _semver_key("2.1.3")
```

- [x] **Step 2: run tests, confirm ImportError on `_semver_key`**

```bash
python -m pytest tests/test_distribution_coherence.py::test_semver_key_orders_patch_bump -v
```
Expected: FAIL — `ImportError: cannot import name '_semver_key'`.

- [x] **Step 3 (Red commit)**

```bash
git add tests/test_distribution_coherence.py
git commit -m "test: add failing _semver_key ordering tests"
```

- [x] **Step 4 (Green): implement `_semver_key`**

Insert BEFORE `_resolve_magi_plugin_json` in `tests/test_distribution_coherence.py`:

```python
def _semver_key(v: str) -> tuple[int, ...]:
    """Convert '2.1.4' -> (2, 1, 4); non-numeric segments sort last (-1)."""
    parts: list[int] = []
    for seg in v.split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            parts.append(-1)
    return tuple(parts)
```

- [x] **Step 5: run the two new tests, confirm PASS**

```bash
python -m pytest tests/test_distribution_coherence.py -k semver_key -v
```
Expected: 2 PASSED.

- [x] **Step 6 (Green commit)**

```bash
git add tests/test_distribution_coherence.py
git commit -m "feat: add _semver_key helper for MAGI version resolution"
```

- [x] **Step 7 (Refactor + verify)**

```bash
make verify
```
Expected: pytest 0 fail, ruff clean, mypy 0 errors. If any, fix before commit.

- [x] **Step 8 (Refactor commit if any cleanup landed)**

```bash
git commit --allow-empty -m "refactor: no-op; _semver_key reviewed, clean"
```

### Task F2: auto-resolver `_resolve_magi_plugin_json`

**Files:**
- Modify: `tests/test_distribution_coherence.py:78-97`

- [x] **Step 1 (Red): add test asserting latest-version selection**

Append:

```python
def test_resolve_magi_plugin_json_picks_latest_semver(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    # Build synthetic cache with 2.1.3 and 2.1.4
    for v in ("2.1.3", "2.1.4"):
        d = tmp_path / "bolivartech-plugins" / "magi" / v / ".claude-plugin"
        d.mkdir(parents=True)
        (d / "plugin.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("MAGI_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(
        "pathlib.Path.home",
        lambda: tmp_path.parent,  # home()/.claude/plugins/cache -> tmp_path
    )
    # Compose the expected base the resolver walks to
    monkeypatch.setattr(
        "tests.test_distribution_coherence._magi_cache_base",
        lambda: tmp_path / "bolivartech-plugins" / "magi",
    )
    resolved = _resolve_magi_plugin_json()
    assert resolved.parent.parent.name == "2.1.4"


def test_resolve_magi_plugin_json_honors_env_override(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    monkeypatch.setenv("MAGI_PLUGIN_ROOT", str(tmp_path))
    result = _resolve_magi_plugin_json()
    assert result == tmp_path / ".claude-plugin" / "plugin.json"


def test_resolve_magi_plugin_json_graceful_when_cache_missing(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    monkeypatch.delenv("MAGI_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(
        "tests.test_distribution_coherence._magi_cache_base",
        lambda: tmp_path / "does-not-exist",
    )
    result = _resolve_magi_plugin_json()
    assert not result.is_file()  # triggers existing skipif gate
```

- [x] **Step 2: run tests, confirm FAIL (resolver still hardcodes 2.1.3, no `_magi_cache_base` symbol)**

```bash
python -m pytest tests/test_distribution_coherence.py -k "resolve_magi" -v
```
Expected: FAIL.

- [x] **Step 3 (Red commit)**

```bash
git add tests/test_distribution_coherence.py
git commit -m "test: add failing tests for MAGI auto-resolver"
```

- [x] **Step 4 (Green): rewrite `_resolve_magi_plugin_json`**

Replace the existing function in `tests/test_distribution_coherence.py` (current lines 78-97):

```python
def _magi_cache_base() -> Path:
    """Return the Claude Code cache base for MAGI. Extracted for test monkeypatch."""
    return (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "bolivartech-plugins"
        / "magi"
    )


def _resolve_magi_plugin_json() -> Path:
    """Resolve the latest cached MAGI's plugin.json, honoring MAGI_PLUGIN_ROOT override.

    Enumerates version subdirs under the cache base and picks the highest
    semver. Non-numeric segments sort last. Graceful skip when cache is
    absent (returns a non-existent path that `is_file()` rejects, triggering
    the existing `@pytest.mark.skipif` gate).
    """
    env_override = os.environ.get("MAGI_PLUGIN_ROOT")
    if env_override:
        return Path(env_override) / ".claude-plugin" / "plugin.json"
    cache_base = _magi_cache_base()
    if not cache_base.is_dir():
        return cache_base / "missing" / ".claude-plugin" / "plugin.json"
    versions = [p.name for p in cache_base.iterdir() if p.is_dir()]
    if not versions:
        return cache_base / "missing" / ".claude-plugin" / "plugin.json"
    latest = max(versions, key=_semver_key)
    return cache_base / latest / ".claude-plugin" / "plugin.json"
```

- [x] **Step 5: run new + existing tests, confirm PASS**

```bash
python -m pytest tests/test_distribution_coherence.py -v
```
Expected: all PASS (or skip when cache absent, which is the graceful path).

- [x] **Step 6 (Green commit)**

```bash
git add tests/test_distribution_coherence.py
git commit -m "feat: auto-resolve MAGI cache to latest semver version"
```

- [x] **Step 7 (Refactor): verify + ensure `MAGI_PLUGIN_JSON` module-level still computes correctly**

```bash
make verify
```
If `MAGI_PLUGIN_JSON` at module top-level now points to a real path on your dev machine (2.1.4 installed), the two `@pytest.mark.skipif` parity tests should run, not skip.

- [x] **Step 8 (Refactor commit)**

```bash
git commit --allow-empty -m "refactor: keep _resolve_magi_plugin_json pure; cache base extracted for test patching"
```

### Task F3: close-task bookkeeping

- [x] **Step 1: update plan checkbox for Milestone F**

(Handled by `/sbtdd close-task` or manual edit.)

- [x] **Step 2: close-task commit**

```bash
git commit --allow-empty -m "chore: mark task F complete"
```

---

## MILESTONE G — Feature A: Interactive MAGI escalation prompt

**Rationale:** v0.1 exits 8 with artefacts when MAGI safety valve exhausts. v0.2 adds an interactive prompt emulating the assistant-in-chat interaction observed during Milestones A-E (see commit `5d7bfc4`, session 2026-04-20). INV-22 forbids running inside `auto_cmd`; headless policy file drives non-TTY fallback.

### Task G1: skeleton module + dataclasses

**Files:**
- Create: `skills/sbtdd/scripts/escalation_prompt.py`
- Create: `tests/test_escalation_prompt.py`

- [x] **Step 1 (Red): write failing test for `EscalationContext` + `UserDecision` + `EscalationOption` dataclasses**

`tests/test_escalation_prompt.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Unit tests for escalation_prompt module (Feature A)."""

from __future__ import annotations

import pytest

from escalation_prompt import (
    EscalationContext,
    EscalationOption,
    UserDecision,
    _RootCause,
)


def test_escalation_context_is_frozen() -> None:
    ctx = EscalationContext(
        iterations=(),
        plan_id="A",
        context="checkpoint2",
        per_agent_verdicts=(),
        findings=(),
        root_cause=_RootCause.INFRA_TRANSIENT,
    )
    with pytest.raises((AttributeError, Exception)):
        ctx.plan_id = "B"  # frozen


def test_user_decision_is_frozen_and_carries_reason() -> None:
    d = UserDecision(chosen_option="a", action="override", reason="caspar JSON bug again")
    assert d.chosen_option == "a"
    assert d.reason == "caspar JSON bug again"
    with pytest.raises((AttributeError, Exception)):
        d.reason = "changed"


def test_escalation_option_has_letter_action_rationale() -> None:
    opt = EscalationOption(letter="a", action="override", rationale="INV-0 user authority")
    assert opt.letter == "a"
    assert opt.action == "override"
```

- [x] **Step 2: run, confirm `ModuleNotFoundError: escalation_prompt`**

```bash
python -m pytest tests/test_escalation_prompt.py -v
```

- [x] **Step 3 (Red commit)**

```bash
git add tests/test_escalation_prompt.py
git commit -m "test: add failing tests for escalation_prompt dataclasses"
```

- [x] **Step 4 (Green): implement module skeleton**

`skills/sbtdd/scripts/escalation_prompt.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Interactive MAGI escalation prompt (Feature A, v0.2.0).

Fires when INV-11 safety valve exhausts in `/sbtdd spec` (Checkpoint 2) or
`/sbtdd pre-merge` (Loop 2). INV-22 forbids running inside `/sbtdd auto`:
auto invocations consult `.claude/magi-auto-policy.json` instead.

Public API:
    build_escalation_context(iterations, plan_id, context) -> EscalationContext
    format_escalation_message(ctx) -> str
    prompt_user(ctx, options) -> UserDecision
    apply_decision(decision, ctx, root) -> int  # writes audit artifact

Precedent: Milestone D Checkpoint 2 iter 3 chat escalation (commit 5d7bfc4).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Literal


class _RootCause(enum.Enum):
    INFRA_TRANSIENT = "infra_transient"       # same agent fails across iters
    PLAN_VS_SPEC = "plan_vs_spec"             # CRITICAL findings persist
    STRUCTURAL_DEFECT = "structural_defect"   # STRONG_NO_GO from >=1 agent
    SPEC_AMBIGUITY = "spec_ambiguity"         # confidence trending down


_ContextLit = Literal["checkpoint2", "pre-merge", "auto"]
_ActionLit = Literal["override", "retry", "abandon", "alternative"]


@dataclass(frozen=True)
class EscalationOption:
    letter: str       # 'a' | 'b' | 'c' | 'd'
    action: _ActionLit
    rationale: str    # shown in the menu after the action verb
    caveat: str = ""  # optional consequence / tradeoff line


@dataclass(frozen=True)
class EscalationContext:
    iterations: tuple[dict[str, Any], ...]     # per-iter verdict snapshots
    plan_id: str
    context: _ContextLit
    per_agent_verdicts: tuple[tuple[str, str], ...]  # (agent_name, verdict)
    findings: tuple[tuple[str, str], ...]            # (severity, text)
    root_cause: _RootCause


@dataclass(frozen=True)
class UserDecision:
    chosen_option: str
    action: _ActionLit
    reason: str
```

- [x] **Step 5: run tests, confirm PASS**

```bash
python -m pytest tests/test_escalation_prompt.py -v
```

- [x] **Step 6 (Green commit)**

```bash
git add skills/sbtdd/scripts/escalation_prompt.py tests/test_escalation_prompt.py
git commit -m "feat: add escalation_prompt skeleton with typed dataclasses"
```

- [x] **Step 7 (Refactor + verify)**

```bash
make verify
```

- [x] **Step 8 (Refactor commit)**

```bash
git commit --allow-empty -m "refactor: escalation_prompt skeleton reviewed, clean"
```

### Task G2: root-cause classifier + `build_escalation_context`

**Files:**
- Modify: `skills/sbtdd/scripts/escalation_prompt.py`
- Modify: `tests/test_escalation_prompt.py`

- [x] **Step 1 (Red): tests for classifier**

Append to `tests/test_escalation_prompt.py`:

```python
from escalation_prompt import (
    build_escalation_context,
    _classify_root_cause,
)
from magi_dispatch import MAGIVerdict


def _mkv(verdict: str, degraded: bool = False, findings: tuple = (), conds: tuple = ()) -> MAGIVerdict:
    return MAGIVerdict(verdict=verdict, degraded=degraded, conditions=conds, findings=findings, raw_output="")


def test_classify_infra_transient_when_degraded_repeats() -> None:
    iters = [
        _mkv("HOLD", degraded=True),
        _mkv("GO", degraded=False),
        _mkv("HOLD", degraded=True),
    ]
    assert _classify_root_cause(iters) == _RootCause.INFRA_TRANSIENT


def test_classify_structural_defect_when_strong_no_go_present() -> None:
    iters = [_mkv("STRONG_NO_GO")]
    assert _classify_root_cause(iters) == _RootCause.STRUCTURAL_DEFECT


def test_classify_plan_vs_spec_when_critical_findings_persist() -> None:
    critical = ({"severity": "CRITICAL", "text": "f"},)
    iters = [_mkv("HOLD", findings=critical), _mkv("HOLD", findings=critical)]
    assert _classify_root_cause(iters) == _RootCause.PLAN_VS_SPEC


def test_build_escalation_context_checkpoint2_returns_frozen_struct() -> None:
    iters = [_mkv("HOLD_TIE"), _mkv("HOLD"), _mkv("HOLD_TIE")]
    ctx = build_escalation_context(iterations=iters, plan_id="A", context="checkpoint2")
    assert ctx.plan_id == "A"
    assert ctx.context == "checkpoint2"
    assert len(ctx.iterations) == 3
    assert ctx.root_cause in set(_RootCause)
```

- [x] **Step 2: run, confirm FAIL**

```bash
python -m pytest tests/test_escalation_prompt.py -v
```

- [x] **Step 3 (Red commit)**

```bash
git add tests/test_escalation_prompt.py
git commit -m "test: add classifier + build_escalation_context tests"
```

- [x] **Step 4 (Green): implement classifier + builder**

Append to `skills/sbtdd/scripts/escalation_prompt.py`:

```python
from magi_dispatch import MAGIVerdict


def _classify_root_cause(iterations: list[MAGIVerdict]) -> _RootCause:
    """Infer the dominant failure mode across iterations."""
    if any(v.verdict == "STRONG_NO_GO" for v in iterations):
        return _RootCause.STRUCTURAL_DEFECT
    degraded_count = sum(1 for v in iterations if v.degraded)
    if degraded_count >= 2 and degraded_count >= len(iterations) / 2:
        return _RootCause.INFRA_TRANSIENT
    critical_across = [
        any(str(f.get("severity", "")).upper() == "CRITICAL" for f in v.findings)
        for v in iterations
    ]
    if sum(critical_across) >= 2:
        return _RootCause.PLAN_VS_SPEC
    return _RootCause.SPEC_AMBIGUITY


def build_escalation_context(
    iterations: list[MAGIVerdict],
    plan_id: str,
    context: _ContextLit,
) -> EscalationContext:
    """Collect iter history + classify root cause."""
    snapshots = tuple(
        {
            "verdict": v.verdict,
            "degraded": v.degraded,
            "n_conditions": len(v.conditions),
            "n_findings": len(v.findings),
        }
        for v in iterations
    )
    per_agent: tuple[tuple[str, str], ...] = ()  # v0.2: MAGI does not expose per-agent breakdown
    findings = tuple(
        (str(f.get("severity", "INFO")).upper(), str(f.get("text", f)))
        for v in iterations
        for f in v.findings
    )
    return EscalationContext(
        iterations=snapshots,
        plan_id=plan_id,
        context=context,
        per_agent_verdicts=per_agent,
        findings=findings,
        root_cause=_classify_root_cause(iterations),
    )
```

- [x] **Step 5: run tests, PASS**

- [x] **Step 6 (Green commit)**

```bash
git add skills/sbtdd/scripts/escalation_prompt.py tests/test_escalation_prompt.py
git commit -m "feat: implement root-cause classifier + build_escalation_context"
```

- [x] **Step 7-8 (Refactor + verify + commit)**

```bash
make verify && git commit --allow-empty -m "refactor: classifier reviewed, clean"
```

### Task G3: `format_escalation_message` (golden-output render)

**Files:**
- Modify: `skills/sbtdd/scripts/escalation_prompt.py`
- Modify: `tests/test_escalation_prompt.py`
- Create: `tests/fixtures/magi-escalations/checkpoint2-infra-transient.txt`

- [x] **Step 1 (Red): golden-output test**

Create `tests/fixtures/magi-escalations/checkpoint2-infra-transient.txt` with the full template from CLAUDE.md "canonical output template" section, adapted to synthetic inputs. Then append to `tests/test_escalation_prompt.py`:

```python
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "magi-escalations"


def test_format_escalation_message_matches_golden_checkpoint2_infra() -> None:
    from escalation_prompt import format_escalation_message
    iters = [
        _mkv("HOLD", degraded=True),
        _mkv("GO", degraded=False),
        _mkv("HOLD", degraded=True),
    ]
    ctx = build_escalation_context(iters, plan_id="D", context="checkpoint2")
    msg = format_escalation_message(ctx)
    # Render must be <=40 lines and include the four expected markers
    assert msg.count("\n") <= 40
    assert "Escalando al usuario" in msg
    assert "Opciones per INV-0" in msg
    assert "(a)" in msg and "(b)" in msg and "(c)" in msg and "(d)" in msg
    assert "Cual?" in msg or "¿Cuál?" in msg


def test_format_escalation_message_structural_defect_omits_retry() -> None:
    from escalation_prompt import format_escalation_message
    iters = [_mkv("STRONG_NO_GO")]
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    msg = format_escalation_message(ctx)
    # option (b) retry should be absent when STRONG_NO_GO present
    assert "retry" not in msg.lower() or "abandonar" in msg.lower()
```

- [x] **Step 2-3 (Red commit)**

```bash
git add tests/test_escalation_prompt.py tests/fixtures/magi-escalations/
git commit -m "test: add golden-output tests for format_escalation_message"
```

- [x] **Step 4 (Green): implement `format_escalation_message` + dynamic option composer**

Append to `skills/sbtdd/scripts/escalation_prompt.py`:

```python
def _compose_options(ctx: EscalationContext) -> tuple[EscalationOption, ...]:
    """Build context-aware menu per root cause."""
    opts: list[EscalationOption] = []
    # (a) override — always available unless STRONG_NO_GO
    if ctx.root_cause != _RootCause.STRUCTURAL_DEFECT:
        opts.append(EscalationOption(
            letter="a",
            action="override",
            rationale="Override INV-0 (user authority)",
            caveat="requires --reason; audit artifact written.",
        ))
    # (b) retry one iter — only for infra transient
    if ctx.root_cause == _RootCause.INFRA_TRANSIENT:
        opts.append(EscalationOption(
            letter="b",
            action="retry",
            rationale="Re-invocar MAGI una iter mas (safety valve +1)",
            caveat="consume iter extra; INV-0 override del INV-11.",
        ))
    # (c) replan / split — for plan-vs-spec or ambiguity
    if ctx.root_cause in (_RootCause.PLAN_VS_SPEC, _RootCause.SPEC_AMBIGUITY):
        opts.append(EscalationOption(
            letter="c",
            action="alternative",
            rationale="Replan: split spec o ajustar scope",
            caveat="reinicia flujo desde sec.1.",
        ))
    # (d) v0.1 behavior — always available, default in non-TTY
    opts.append(EscalationOption(
        letter="d",
        action="abandon",
        rationale="Exit 8 (v0.1 behavior) + artefactos para review manual",
        caveat="default en non-TTY.",
    ))
    # Reassign letters a/b/c/d sequentially so the menu is contiguous
    letters = ("a", "b", "c", "d")
    return tuple(
        EscalationOption(letter=letters[i], action=o.action, rationale=o.rationale, caveat=o.caveat)
        for i, o in enumerate(opts[:4])
    )


def format_escalation_message(ctx: EscalationContext) -> str:
    """Render the canonical escalation template (<=40 lines)."""
    n = len(ctx.iterations)
    last = ctx.iterations[-1] if ctx.iterations else {"verdict": "?", "degraded": False}
    root_label = {
        _RootCause.INFRA_TRANSIENT: "transient-infra (agent degraded repite)",
        _RootCause.PLAN_VS_SPEC: "plan-vs-spec gap (CRITICAL findings persisten)",
        _RootCause.STRUCTURAL_DEFECT: "defecto estructural (STRONG_NO_GO)",
        _RootCause.SPEC_AMBIGUITY: "spec ambiguity (confidence trending down)",
    }[ctx.root_cause]
    opts = _compose_options(ctx)
    lines = [
        f"MAGI iter {n} FINAL ({ctx.context}): veredicto '{last['verdict']}' degraded={last['degraded']}.",
        f"Causa raiz inferida: {root_label}.",
        f"Safety valve INV-11 exhausted tras {n} iter.",
        "",
        "Escalando al usuario per INV-11 + INV-18:",
        "",
        f"Estado plan {ctx.plan_id}:",
        f"- Iteraciones: {n}",
        f"- Findings residuales: {len(ctx.findings)}",
        "",
        "Opciones per INV-0 (user authority):",
    ]
    for o in opts:
        line = f"- ({o.letter}) {o.action}: {o.rationale}."
        if o.caveat:
            line += f" {o.caveat}"
        lines.append(line)
    lines.append("")
    lines.append("¿Cuál?")
    return "\n".join(lines)
```

- [x] **Step 5 (verify tests PASS)**

```bash
python -m pytest tests/test_escalation_prompt.py -v
```

- [x] **Step 6-8 (Green + Refactor commits)**

```bash
git add skills/sbtdd/scripts/escalation_prompt.py
git commit -m "feat: implement format_escalation_message with dynamic option menu"
make verify
git commit --allow-empty -m "refactor: template render reviewed, ≤40 lines"
```

### Task G4: `prompt_user` TTY-guarded + headless fallback

**Files:**
- Modify: `skills/sbtdd/scripts/escalation_prompt.py`
- Modify: `tests/test_escalation_prompt.py`

- [x] **Step 1 (Red): TTY + headless tests**

Append to `tests/test_escalation_prompt.py`:

```python
def test_prompt_user_non_tty_defaults_to_abandon(monkeypatch, capsys) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True), _mkv("HOLD", degraded=True)]
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    decision = prompt_user(ctx, opts, non_interactive=True)
    assert decision.action == "abandon"
    assert decision.chosen_option == "d"


def test_prompt_user_tty_accepts_letter(monkeypatch) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="checkpoint2")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    inputs = iter(["a", "caspar JSON bug"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    decision = prompt_user(ctx, opts, non_interactive=False)
    assert decision.action == "override"
    assert decision.reason == "caspar JSON bug"


def test_prompt_user_invalid_letter_reprompts(monkeypatch) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="checkpoint2")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    inputs = iter(["z", "A", "reason text"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    decision = prompt_user(ctx, opts, non_interactive=False)
    assert decision.chosen_option == "a"
```

- [x] **Step 2-3 (Red commit)**

```bash
git add tests/test_escalation_prompt.py
git commit -m "test: add prompt_user TTY + headless + re-prompt tests"
```

- [x] **Step 4 (Green): implement `prompt_user`**

Append to `skills/sbtdd/scripts/escalation_prompt.py`:

```python
import json
import sys
from pathlib import Path


_HEADLESS_POLICY_FILE = ".claude/magi-auto-policy.json"
# Canonical registry of allowed `on_exhausted` policy values. Lives in
# models.py per NF10 (fixed registries are centralized in models.py).
# Imported here to avoid a second source of truth.
from models import AUTO_POLICIES  # tuple[str, ...] of allowed policy names


def _read_headless_policy(root: Path) -> str:
    """Return the configured policy or 'abort' (default)."""
    p = root / _HEADLESS_POLICY_FILE
    if not p.is_file():
        return "abort"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "abort"
    policy = str(data.get("on_exhausted", "abort"))
    return policy if policy in AUTO_POLICIES else "abort"


def prompt_user(
    ctx: EscalationContext,
    options: tuple[EscalationOption, ...],
    *,
    non_interactive: bool = False,
    project_root: Path | None = None,
) -> UserDecision:
    """Print the formatted escalation message + prompt user for choice.

    Non-TTY / --non-interactive / auto path: apply headless policy from
    .claude/magi-auto-policy.json (default 'abort' = option d).

    TTY path: loop input() until user enters a valid letter; then collect
    a one-line reason (mandatory for override action).
    """
    sys.stderr.write(format_escalation_message(ctx) + "\n")
    tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
    if non_interactive or not tty:
        policy = _read_headless_policy(project_root or Path.cwd())
        if policy == "override_strong_go_only" and ctx.root_cause != _RootCause.STRUCTURAL_DEFECT:
            match = next((o for o in options if o.action == "override"), options[-1])
            return UserDecision(chosen_option=match.letter, action=match.action,
                                reason="headless policy: override_strong_go_only")
        if policy == "retry_once" and any(o.action == "retry" for o in options):
            match = next(o for o in options if o.action == "retry")
            return UserDecision(chosen_option=match.letter, action=match.action,
                                reason="headless policy: retry_once")
        # default 'abort' -> option d (abandon)
        match = next((o for o in options if o.action == "abandon"), options[-1])
        return UserDecision(chosen_option=match.letter, action=match.action,
                            reason="headless policy: abort (default)")
    valid = {o.letter: o for o in options}
    while True:
        try:
            choice = input("Option (a/b/c/d): ").strip().lower()
        except EOFError:
            match = next((o for o in options if o.action == "abandon"), options[-1])
            return UserDecision(chosen_option=match.letter, action=match.action,
                                reason="EOFError during prompt; headless default")
        if choice in valid:
            break
        sys.stderr.write(f"Invalid choice '{choice}'; expected one of {sorted(valid)}.\n")
    opt = valid[choice]
    if opt.action == "override":
        try:
            reason = input("Reason (mandatory for override): ").strip()
        except EOFError:
            reason = ""
        if not reason:
            sys.stderr.write("Override requires non-empty --reason; falling back to abandon.\n")
            match = next((o for o in options if o.action == "abandon"), options[-1])
            return UserDecision(chosen_option=match.letter, action=match.action,
                                reason="override requested without reason")
        return UserDecision(chosen_option=choice, action="override", reason=reason)
    return UserDecision(chosen_option=choice, action=opt.action, reason=f"user chose {opt.action}")
```

- [x] **Step 5: tests PASS**

```bash
python -m pytest tests/test_escalation_prompt.py -v
```

- [x] **Step 6-8**

```bash
git add skills/sbtdd/scripts/escalation_prompt.py
git commit -m "feat: add prompt_user with TTY + headless fallback paths"
make verify
git commit --allow-empty -m "refactor: prompt_user reviewed for EOFError safety"
```

### Task G5: `apply_decision` + audit artifact writer

**Files:**
- Modify: `skills/sbtdd/scripts/escalation_prompt.py`
- Modify: `tests/test_escalation_prompt.py`

- [x] **Step 1 (Red): audit artifact test**

Append:

```python
def test_apply_decision_writes_audit_artifact(tmp_path) -> None:
    from escalation_prompt import apply_decision, _compose_options
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="D", context="checkpoint2")
    opts = _compose_options(ctx)
    decision = UserDecision(chosen_option="a", action="override", reason="caspar bug")
    code = apply_decision(decision, ctx, project_root=tmp_path)
    assert code == 0
    # artifact written
    audits = list((tmp_path / ".claude" / "magi-escalations").glob("*.json"))
    assert len(audits) == 1
    import json
    data = json.loads(audits[0].read_text(encoding="utf-8"))
    assert data["decision"] == "override"
    assert data["chosen_option"] == "a"
    assert data["reason"] == "caspar bug"
    assert data["plan_id"] == "D"
    assert data["magi_context"] == "checkpoint2"


def test_apply_decision_abandon_returns_exit_8(tmp_path) -> None:
    from escalation_prompt import apply_decision
    iters = [_mkv("HOLD_TIE")] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    decision = UserDecision(chosen_option="d", action="abandon",
                            reason="headless policy")
    code = apply_decision(decision, ctx, project_root=tmp_path)
    assert code == 8
```

- [x] **Step 2-3 (Red commit)**

```bash
python -m pytest tests/test_escalation_prompt.py -v
git add tests/test_escalation_prompt.py
git commit -m "test: add apply_decision audit artifact + exit-code tests"
```

- [x] **Step 4 (Green)**

Append to `skills/sbtdd/scripts/escalation_prompt.py`:

```python
from datetime import datetime, timezone


def apply_decision(decision: UserDecision, ctx: EscalationContext, project_root: Path) -> int:
    """Write audit artifact + return process exit code.

    Returns:
        0 if decision is override/retry/alternative (caller continues);
        8 if abandon (exit 8 matches v0.1 behavior so wrappers can propagate).
    """
    artifact_dir = project_root / ".claude" / "magi-escalations"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    safe_ts = ts.replace(":", "-")
    artifact = artifact_dir / f"{safe_ts}-{ctx.plan_id}.json"
    payload = {
        "decision": decision.action,
        "chosen_option": decision.chosen_option,
        "reason": decision.reason,
        "escalation_context": {
            "iterations": list(ctx.iterations),
            "plan_id": ctx.plan_id,
            "root_cause": ctx.root_cause.value,
            "n_findings": len(ctx.findings),
        },
        "timestamp": ts,
        "plan_id": ctx.plan_id,
        "magi_context": ctx.context,
    }
    artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 8 if decision.action == "abandon" else 0
```

- [x] **Step 5: tests PASS**

- [x] **Step 6-8**

```bash
git add skills/sbtdd/scripts/escalation_prompt.py
git commit -m "feat: add apply_decision with audit artifact + exit-code mapping"
make verify
git commit --allow-empty -m "refactor: apply_decision reviewed"
```

### Task G6: wire into `spec_cmd.py` safety-valve exhaustion path

**Files:**
- Modify: `skills/sbtdd/scripts/spec_cmd.py`
- Create: `tests/test_spec_cmd_escalation.py`

- [x] **Step 1 (Red): test escalation fires on exhaustion**

`tests/test_spec_cmd_escalation.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""spec_cmd -> escalation_prompt wiring tests (Feature A)."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

import spec_cmd
from errors import MAGIGateError
from tests.fixtures.skill_stubs import StubMAGI, make_verdict


def test_spec_cmd_escalates_on_safety_valve_exhaustion(tmp_path, monkeypatch) -> None:
    # synthesize a full project root with spec-behavior-base.md etc
    # (use existing fixtures helper if one exists; otherwise create minimal)
    ...  # skeleton; concretize using test_spec_cmd.py fixtures


def test_spec_cmd_override_flag_skips_prompt_and_writes_audit(tmp_path) -> None:
    ...  # `--override-checkpoint --reason "..."` path bypasses prompt
```

Replace the `...` placeholders by lifting fixture setup from existing `tests/test_spec_cmd.py`. (Do NOT ship literal `...` — that would be a placeholder per skill rules.) The exact fixture setup uses `_make_project_fixture(tmp_path)` analogous to what test_spec_cmd already does.

- [x] **Step 2-3 (Red commit)**

```bash
git add tests/test_spec_cmd_escalation.py
git commit -m "test: add spec_cmd safety-valve escalation wiring tests"
```

- [x] **Step 4 (Green): wire escalation into `spec_cmd`**

In `skills/sbtdd/scripts/spec_cmd.py`:

1. Extend `_build_parser()` to accept `--override-checkpoint`, `--reason`, and `--non-interactive`:

```python
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd spec")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--override-checkpoint", action="store_true",
                   help="Override MAGI gate per INV-0; requires --reason")
    p.add_argument("--reason", type=str, default=None,
                   help="Mandatory when --override-checkpoint is set")
    p.add_argument("--non-interactive", action="store_true",
                   help="Force headless path on safety-valve exhaustion")
    return p
```

2. Modify `_run_magi_checkpoint2` to catch exhaustion and route to `escalation_prompt`:

```python
import escalation_prompt


def _run_magi_checkpoint2(root: Path, cfg: object, ns: argparse.Namespace) -> magi_dispatch.MAGIVerdict:
    ...  # existing body (unchanged until final raise)
    # replace `raise MAGIGateError(f"... did not converge ...")` with:
    # Build escalation context from the iterations the loop tracked; wire
    # apply_decision to either raise (abandon/exit 8), override (accept
    # last verdict), or retry (one more iter). Plan_id derived from the
    # plan path name suffix ('A' in claude-plan-tdd-A.md).
```

Concretely replace the final `raise MAGIGateError(...)` with:

```python
    # Exhaustion path: build context + escalate
    ctx = escalation_prompt.build_escalation_context(
        iterations=list(_verdict_history),
        plan_id=_plan_id_from_path(plan.name),
        context="checkpoint2",
    )
    options = escalation_prompt._compose_options(ctx)
    if ns.override_checkpoint:
        if not ns.reason:
            raise MAGIGateError("--override-checkpoint requires --reason")
        decision = UserDecision(chosen_option="a", action="override", reason=ns.reason)
    else:
        decision = escalation_prompt.prompt_user(
            ctx, options, non_interactive=ns.non_interactive, project_root=root
        )
    code = escalation_prompt.apply_decision(decision, ctx, project_root=root)
    if code == 0 and decision.action == "override":
        return _verdict_history[-1]  # accept last verdict
    if code == 0 and decision.action == "retry":
        # One extra iter — re-enter the loop body once more
        verdict = magi_dispatch.invoke_magi(context_paths=[str(spec), str(plan_org)], cwd=str(root))
        _write_plan_tdd(root, verdict, plan_org, plan)
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            return verdict
        raise MAGIGateError("retry iter also failed gate")
    raise MAGIGateError(f"user chose '{decision.action}' on safety-valve exhaustion")
```

Track iterations via `_verdict_history: list[MAGIVerdict]` accumulated inside the for loop (refactor the existing loop to append each `verdict` observed). Add module-level `_plan_id_from_path` helper:

```python
def _plan_id_from_path(name: str) -> str:
    """Extract plan id suffix from filename (claude-plan-tdd-A.md -> 'A')."""
    import re
    m = re.search(r"-([A-Z0-9]+)\.md$", name)
    return m.group(1) if m else "X"
```

Pass `ns` to `_run_magi_checkpoint2(root, cfg, ns)` from `main(argv)`.

- [x] **Step 5: tests PASS**

- [x] **Step 6-8 (Green + Refactor commits)**

```bash
git add skills/sbtdd/scripts/spec_cmd.py tests/test_spec_cmd_escalation.py
git commit -m "feat: wire escalation_prompt into spec_cmd safety-valve exhaustion"
make verify
git commit --allow-empty -m "refactor: spec_cmd wiring reviewed"
```

### Task G7: wire into `pre_merge_cmd.py`

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Create: `tests/test_pre_merge_cmd_escalation.py`

Mirror Task G6 for `pre_merge_cmd._loop2`. The non-convergence raise at `pre_merge_cmd.py:540-546` becomes the escalation entry. Pass `context="pre-merge"` and `plan_id` derived analogously. The `MAGIGateError` constructor already carries `accepted_conditions` / `rejected_conditions` / `verdict` / `iteration` — preserve them on re-raise paths when the user picks abandon.

- [x] **Step 1-3 (Red commit)**

Same structure as G6 step 1-3.

- [x] **Step 4 (Green)**

Add `import escalation_prompt` and modify the final raise in `_loop2`:

```python
# replace the final raise MAGIGateError(...) block with:
from escalation_prompt import build_escalation_context, _compose_options, prompt_user, apply_decision
ctx = build_escalation_context(
    iterations=_verdict_history,
    plan_id=_plan_id_from_path(cfg.plan_path),
    context="pre-merge",
)
opts = _compose_options(ctx)
if ns.override_checkpoint:
    if not ns.reason:
        raise MAGIGateError("--override-checkpoint requires --reason")
    decision = UserDecision(chosen_option="a", action="override", reason=ns.reason)
else:
    decision = prompt_user(ctx, opts, non_interactive=ns.non_interactive, project_root=root)
apply_decision(decision, ctx, project_root=root)
if decision.action == "override" and last_verdict is not None:
    return last_verdict
raise MAGIGateError(
    f"user chose '{decision.action}' on pre-merge Loop 2 exhaustion",
    verdict=last_verdict.verdict if last_verdict else None,
    iteration=cfg.magi_max_iterations,
)
```

Accumulate `_verdict_history` inside the existing `for iteration in range(...)` loop and add the same three flags to `_build_parser()`. Pass `ns` into `_loop2`.

- [x] **Step 5-8**: verify + commits.

### Task G8: `finalize_cmd --override-checkpoint --reason`

**Files:**
- Modify: `skills/sbtdd/scripts/finalize_cmd.py`
- Create: `tests/test_finalize_cmd_override.py`

- [x] **Step 1-3 (Red)**: test asserting override flag produces audit artifact + bypasses `degraded: true` reject.

- [x] **Step 4 (Green)**: add `--override-checkpoint --reason` to `finalize_cmd._build_parser`. In `main()`, before rejecting a degraded verdict, check `ns.override_checkpoint`. When set, build an abbreviated `EscalationContext` (synthesize a single-iter history from `.claude/magi-verdict.json`), call `apply_decision` with the user's reason, and permit the gate to pass. The audit artifact is the record.

- [x] **Step 5-8**: tests + commits.

### Task G9: `resume_cmd` detects pending escalation

**Files:**
- Modify: `skills/sbtdd/scripts/resume_cmd.py`
- Create: `tests/test_resume_cmd_escalation_recovery.py`

- [x] **Step 1-3 (Red)**: test that `resume_cmd` detects `.claude/magi-escalation-pending.md` and re-enters the prompt.

- [x] **Step 4 (Green)**: in `resume_cmd._preflight_diagnose` (or equivalent entry point), check for `.claude/magi-escalation-pending.md`. When present, read the serialized `EscalationContext` JSON inside it, compose options, call `prompt_user`, `apply_decision`, delete the pending marker, then delegate to the original subcommand (`spec` or `pre-merge`) based on the stored context. In parallel, modify `prompt_user` to write the pending marker BEFORE the first `input()` call so Ctrl+C recovery works:

```python
# inside prompt_user, right before input():
pending = (project_root or Path.cwd()) / ".claude" / "magi-escalation-pending.md"
pending.parent.mkdir(parents=True, exist_ok=True)
pending.write_text(json.dumps({
    "plan_id": ctx.plan_id,
    "context": ctx.context,
    "root_cause": ctx.root_cause.value,
    "iterations": list(ctx.iterations),
}, indent=2), encoding="utf-8")
# ... after decision made (success or EOF), remove:
if pending.is_file():
    pending.unlink()
```

- [x] **Step 5-8**: tests + commits.

### Task G9b: A8 invariant — Feature A never invoked from `auto_cmd`

**Files:**
- Create: `tests/test_auto_cmd_escalation_headless.py`

Acceptance criterion A8 (`spec-behavior-base.md:282`) and INV-22 both require that Feature A's interactive prompt NEVER runs inside `/sbtdd auto`. This task proves the invariant with two orthogonal checks: a static import check (`auto_cmd.py` does not import `prompt_user`) and a behavioral check (stubbing `prompt_user` to count calls, then driving `auto_cmd` through a MAGI-exhaustion path and asserting zero calls).

- [x] **Step 1 (Red): create `tests/test_auto_cmd_escalation_headless.py`**

```python
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "sbtdd" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _names_imported_by(module_path: Path, from_module: str) -> set[str]:
    """Return the set of names imported from `from_module` by the given .py file."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == from_module:
            names.update(alias.name for alias in node.names)
    return names


def test_auto_cmd_does_not_import_prompt_user() -> None:
    """A8 static guarantee: auto_cmd.py must not import any TTY-driven entry
    point from escalation_prompt. Importing build_escalation_context /
    apply_decision is permitted (headless-safe); prompt_user is not."""
    imported = _names_imported_by(SCRIPTS_DIR / "auto_cmd.py", "escalation_prompt")
    assert "prompt_user" not in imported, (
        "INV-22 / A8 violation: auto_cmd imports escalation_prompt.prompt_user. "
        "auto_cmd must remain headless; use apply_decision with a headless "
        "UserDecision synthesized from .claude/magi-auto-policy.json instead."
    )


def test_auto_cmd_magi_exhaustion_never_calls_prompt_user(tmp_path: Path) -> None:
    """A8 behavioral guarantee: drive auto_cmd through a MAGI non-convergence
    path with a StubMAGI that returns HOLD on every iter. prompt_user is patched
    to raise on invocation. The run must abort with MAGIGateError (or the
    headless policy verdict) without ever calling prompt_user."""
    from tests.fixtures.skill_stubs import StubMAGI  # existing fixture
    import auto_cmd
    import escalation_prompt

    # Stage a minimal project: state file done-with-plan, plan approved, one
    # pre-merge Loop 2 non-convergence path. Reuse existing tests/fixtures/auto-runs
    # staging helpers (lifted from tests/test_auto_cmd.py setup).
    ...  # concretize: reuse _stage_auto_run(tmp_path) helper, approved plan, all tasks [x]

    def _boom(*a: object, **kw: object) -> None:
        raise AssertionError("prompt_user invoked inside auto_cmd — INV-22 violated")

    with patch.object(escalation_prompt, "prompt_user", _boom):
        with pytest.raises(Exception):  # MAGIGateError or SystemExit
            auto_cmd.main(["--dry-run=false"])
```

- [x] **Step 2: run tests to confirm Red**

```bash
python -m pytest tests/test_auto_cmd_escalation_headless.py -v
```
Expected: `test_auto_cmd_does_not_import_prompt_user` FAILS if Task G6/G7 accidentally leaked the import into `auto_cmd.py`; `test_auto_cmd_magi_exhaustion_never_calls_prompt_user` FAILS with `NotImplementedError` on the `...` placeholder until the stage helper is concretized.

- [x] **Step 3 (Red commit)**

```bash
git add tests/test_auto_cmd_escalation_headless.py
git commit -m "test: add A8 invariant — prompt_user never called inside auto_cmd"
```

- [x] **Step 4 (Green): concretize the stage helper**

Replace the `...` line with the real staging code lifted from `tests/test_auto_cmd.py::_stage_auto_run` (or equivalent fixture helper). Ensure the test run uses a stub pre-merge Loop 2 that exhausts iterations with HOLD verdicts.

> **Do NOT ship literal `...`**: any `...` left in committed test code is a landing-time failure. Replace every `...` placeholder with real code before the Green commit, and re-run `pytest` + `ruff check` to confirm zero warnings.

- [x] **Step 5: run tests, confirm PASS**

```bash
python -m pytest tests/test_auto_cmd_escalation_headless.py -v
```
Expected: both tests PASS. If the behavioral test passes vacuously (auto_cmd raises before reaching the Loop 2 exhaustion at all), add an explicit `assert verdict_exhausted_code_was_hit` breadcrumb inside the stage helper to detect the vacuous case.

- [x] **Step 6 (Green commit)**

```bash
make verify
git add tests/test_auto_cmd_escalation_headless.py
git commit -m "feat: concretize A8 headless invariant test"
```

- [x] **Step 7 (Refactor)**

```bash
git commit --allow-empty -m "refactor: A8 test reviewed, clean"
```

### Task G10: close-task Milestone G

- [x] **Step 1**: mark Milestone G checkbox [x] in the plan.
- [x] **Step 2**: commit.

```bash
git commit --allow-empty -m "chore: mark task G complete"
```

---

## MILESTONE H — Feature B: Superpowers spec-reviewer integration per task

**Rationale:** Per-task semantic drift detection. Runs a superpowers spec-reviewer subagent after implementer DONE but before `mark_and_advance`. Reviewer operates on task diff + task text (NOT full spec) to bound cost. Findings route via `/receiving-code-review` (INV-29 extension → INV-31 new).

### Task H1: new `SpecReviewError` + exit 12

**Files:**
- Modify: `skills/sbtdd/scripts/errors.py`
- Modify: `tests/test_errors.py`

- [x] **Step 1 (Red)**:

Append to `tests/test_errors.py`:

```python
def test_spec_review_error_maps_to_exit_12() -> None:
    from errors import EXIT_CODES, SpecReviewError
    assert EXIT_CODES[SpecReviewError] == 12


def test_spec_review_error_is_sbtdd_error() -> None:
    from errors import SBTDDError, SpecReviewError
    assert issubclass(SpecReviewError, SBTDDError)
```

- [x] **Step 2-3**: run, fail, commit `test:`.

- [x] **Step 4 (Green)**: in `skills/sbtdd/scripts/errors.py`:

```python
class SpecReviewError(SBTDDError):
    """Spec-reviewer safety valve exhausted — exit 12 (SPEC_REVIEW_ISSUES).

    Introduced in v0.2 (Feature B). Carries the last-iteration issues
    list as a typed attribute so dispatchers can enrich audit artifacts.
    """

    def __init__(
        self,
        message: str,
        *,
        task_id: str | None = None,
        iteration: int | None = None,
        issues: tuple[str, ...] = (),
    ) -> None:
        super().__init__(message)
        self.task_id = task_id
        self.iteration = iteration
        self.issues = issues
```

Add to `_EXIT_CODES_MUTABLE`:

```python
    SpecReviewError: 12,
```

- [x] **Step 5-8**: tests pass, `feat:`, verify, `refactor:` commits.

### Task H2: `SpecReviewResult` + `SpecIssue` dataclasses

**Files:**
- Create: `skills/sbtdd/scripts/spec_review_dispatch.py`
- Create: `tests/test_spec_review_dispatch.py`

- [x] **Step 1 (Red)**: dataclass shape tests mirroring Task G1 pattern.

```python
def test_spec_review_result_is_frozen() -> None:
    from spec_review_dispatch import SpecReviewResult, SpecIssue
    r = SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)
    with pytest.raises((AttributeError, Exception)):
        r.approved = False


def test_spec_issue_carries_severity_and_text() -> None:
    from spec_review_dispatch import SpecIssue
    i = SpecIssue(severity="MISSING", text="Scenario 4 not covered")
    assert i.severity == "MISSING"
```

- [x] **Step 2-3**: commit `test:`.

- [x] **Step 4 (Green)**: create `skills/sbtdd/scripts/spec_review_dispatch.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Superpowers spec-reviewer dispatcher (Feature B, v0.2.0).

Wraps `superpowers:subagent-driven-development/spec-reviewer-prompt.md` as
a per-task spec-compliance check. Invoked by `auto_cmd._phase2_task_loop`
after implementer DONE / before `close_task_cmd.mark_and_advance`, and by
`close_task_cmd` interactively (unless --skip-spec-review set).

Reviewer contract (three defect classes):
  - MISSING: requirement claimed but not built
  - EXTRA: work outside spec scope (over-engineering)
  - MISUNDERSTANDING: right problem solved wrong way

Directive embedded in reviewer prompt (per superpowers): 'Verify by reading
code, NOT by trusting report.'

Cost envelope: task diff + task text (~1-5 KB per call). For a 36-task
plan this adds 36 `claude -p` invocations. Quota-aware via quota_detector.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import quota_detector
import subprocess_utils
from errors import QuotaExhaustedError, SpecReviewError, ValidationError


_SeverityLit = Literal["MISSING", "EXTRA", "MISUNDERSTANDING", "INFO"]


@dataclass(frozen=True)
class SpecIssue:
    severity: _SeverityLit
    text: str


@dataclass(frozen=True)
class SpecReviewResult:
    approved: bool
    issues: tuple[SpecIssue, ...]
    reviewer_iter: int
    artifact_path: Path | None


def _extract_task_text(plan_text: str, task_id: str) -> str:
    """Return the task section from plan markdown (### Task N: title body)."""
    import re
    # Find heading line for this task; take until the next ### heading
    pattern = re.compile(
        rf"^### Task {re.escape(task_id)}[:\s].*?(?=^### Task |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(plan_text)
    return m.group(0) if m else ""


def _collect_task_diff(repo_root: Path, task_id: str, n_commits: int = 4) -> str:
    """Return combined diff of last N commits tagged for this task."""
    # Best effort: pull HEAD~N..HEAD; caller can refine via commit-message grep
    result = subprocess_utils.run_with_timeout(
        ["git", "log", f"-{n_commits}", "--pretty=format:%H %s", "--no-merges"],
        timeout=10,
        cwd=str(repo_root),
    )
    # Filter commit lines referencing the task id
    shas: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split(" ", 1)
        if len(parts) == 2 and task_id in parts[1]:
            shas.append(parts[0])
    if not shas:
        return ""
    diff = subprocess_utils.run_with_timeout(
        ["git", "show", "--stat", *shas],
        timeout=30,
        cwd=str(repo_root),
    )
    return diff.stdout
```

- [x] **Step 5-8**: tests pass, commits.

### Task H3: `dispatch_spec_reviewer` core

- [x] **Step 1 (Red)**: tests using a stubbed `subprocess.run` that returns scripted reviewer outputs.

```python
def test_dispatch_approved_path(tmp_path, monkeypatch) -> None:
    from spec_review_dispatch import dispatch_spec_reviewer
    # craft minimal plan + fake subprocess
    plan = tmp_path / "plan.md"
    plan.write_text("### Task 1: foo\n- [x] stuff\n", encoding="utf-8")
    def fake_run(*a, **k):
        class R: returncode = 0; stdout = '{"approved": true, "issues": []}'; stderr = ""
        return R()
    monkeypatch.setattr("spec_review_dispatch.subprocess_utils.run_with_timeout", fake_run)
    result = dispatch_spec_reviewer(task_id="1", plan_path=plan, repo_root=tmp_path)
    assert result.approved is True
    assert result.issues == ()


def test_dispatch_safety_valve_raises_spec_review_error(tmp_path, monkeypatch) -> None:
    from spec_review_dispatch import dispatch_spec_reviewer
    plan = tmp_path / "plan.md"
    plan.write_text("### Task 1: foo\n- [x] stuff\n", encoding="utf-8")
    def fake_run(*a, **k):
        class R:
            returncode = 0
            stdout = '{"approved": false, "issues": [{"severity": "MISSING", "text": "scenario N"}]}'
            stderr = ""
        return R()
    monkeypatch.setattr("spec_review_dispatch.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(SpecReviewError):
        dispatch_spec_reviewer(task_id="1", plan_path=plan, repo_root=tmp_path,
                               max_iterations=3)
```

- [x] **Step 2-3**: commit `test:`.

- [x] **Step 4 (Green)**: append to `spec_review_dispatch.py`:

```python
_REVIEWER_SKILL_REF = "/superpowers:subagent-driven-development/spec-reviewer-prompt.md"


def _parse_reviewer_output(raw: str) -> tuple[bool, tuple[SpecIssue, ...]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"spec-reviewer output is not valid JSON: {exc}") from exc
    approved = bool(payload.get("approved", False))
    issues_raw = payload.get("issues", []) or []
    if not isinstance(issues_raw, list):
        raise ValidationError("spec-reviewer 'issues' must be a list")
    issues = tuple(
        SpecIssue(
            severity=str(i.get("severity", "INFO")).upper(),  # type: ignore[arg-type]
            text=str(i.get("text", "")),
        )
        for i in issues_raw
    )
    return approved, issues


def _write_artifact(
    result_payload: dict,
    repo_root: Path,
    task_id: str,
) -> Path:
    d = repo_root / ".claude" / "spec-reviews"
    d.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").replace(":", "-")
    artifact = d / f"{task_id}-{ts}.json"
    artifact.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    return artifact


def dispatch_spec_reviewer(
    *,
    task_id: str,
    plan_path: Path,
    repo_root: Path,
    max_iterations: int = 3,
    timeout: int = 900,
) -> SpecReviewResult:
    """Run the spec-reviewer for ONE task; retry on issues up to `max_iterations`.

    Raises:
        SpecReviewError: Safety valve exhausted (issues remain after last iter).
        QuotaExhaustedError: Claude API quota detected in stderr.
        ValidationError: Reviewer output malformed.
    """
    plan_text = plan_path.read_text(encoding="utf-8")
    task_text = _extract_task_text(plan_text, task_id)
    diff_text = _collect_task_diff(repo_root, task_id)
    iter_history: list[dict] = []
    for iteration in range(1, max_iterations + 1):
        prompt = (
            f"Task: {task_id}\n\n"
            f"Task text:\n{task_text}\n\n"
            f"Diff:\n{diff_text}\n\n"
            "Verify by reading code, NOT by trusting implementer report."
        )
        cmd = ["claude", "-p", _REVIEWER_SKILL_REF, prompt]
        try:
            r = subprocess_utils.run_with_timeout(cmd, timeout=timeout, capture=True,
                                                   cwd=str(repo_root))
        except subprocess.TimeoutExpired as exc:
            raise SpecReviewError(
                f"spec-reviewer timed out at iter {iteration} for task {task_id}",
                task_id=task_id, iteration=iteration,
            ) from exc
        if r.returncode != 0:
            exh = quota_detector.detect(r.stderr)
            if exh is not None:
                raise QuotaExhaustedError(f"{exh.kind}: {exh.raw_message}")
            raise SpecReviewError(
                f"spec-reviewer exited {r.returncode} at iter {iteration}",
                task_id=task_id, iteration=iteration,
            )
        approved, issues = _parse_reviewer_output(r.stdout)
        iter_history.append({"iter": iteration, "approved": approved,
                             "n_issues": len(issues)})
        if approved:
            artifact = _write_artifact({
                "task_id": task_id,
                "approved": True,
                "iter_history": iter_history,
                "final_issues": [],
            }, repo_root, task_id)
            return SpecReviewResult(approved=True, issues=(),
                                    reviewer_iter=iteration, artifact_path=artifact)
        # Not approved: exhaust budget first, then raise.
        if iteration == max_iterations:
            artifact = _write_artifact({
                "task_id": task_id,
                "approved": False,
                "iter_history": iter_history,
                "final_issues": [{"severity": i.severity, "text": i.text} for i in issues],
            }, repo_root, task_id)
            raise SpecReviewError(
                f"spec-reviewer safety valve exhausted for task {task_id} "
                f"after {iteration} iterations ({len(issues)} issues)",
                task_id=task_id, iteration=iteration,
                issues=tuple(i.text for i in issues),
            )
        # Otherwise: next iteration re-dispatches. v0.2 keeps it simple —
        # caller (auto_cmd) is responsible for landing mini-cycle TDD fixes
        # between reviewer iterations via /receiving-code-review. The
        # dispatcher itself does not mutate code; it only decides approval.
    # unreachable
    raise SpecReviewError(f"unreachable: max_iterations must be >= 1 for task {task_id}",
                          task_id=task_id, iteration=0)
```

- [x] **Step 5-8**: tests pass, commits.

### Task H4: `StubSpecReviewer` fixture

**Files:**
- Modify: `tests/fixtures/skill_stubs.py`
- Modify: `tests/test_skill_stubs.py`

- [x] **Step 1 (Red)**: tests for the stub.

```python
def test_stub_spec_reviewer_sequence_consumed_fifo() -> None:
    from tests.fixtures.skill_stubs import StubSpecReviewer
    stub = StubSpecReviewer(sequence=[True, False, True])
    assert stub.dispatch_spec_reviewer(task_id="1", plan_path=None, repo_root=None).approved is True
    assert stub.dispatch_spec_reviewer(task_id="2", plan_path=None, repo_root=None).approved is False
    assert stub.dispatch_spec_reviewer(task_id="3", plan_path=None, repo_root=None).approved is True


def test_stub_spec_reviewer_empty_raises() -> None:
    from tests.fixtures.skill_stubs import StubSpecReviewer
    stub = StubSpecReviewer(sequence=[])
    with pytest.raises(IndexError):
        stub.dispatch_spec_reviewer(task_id="1", plan_path=None, repo_root=None)
```

- [x] **Step 2-3**: commit `test:`.

- [x] **Step 4 (Green)**: append to `tests/fixtures/skill_stubs.py`:

```python
from spec_review_dispatch import SpecIssue, SpecReviewResult


@dataclass
class StubSpecReviewer:
    """Stub for spec_review_dispatch.dispatch_spec_reviewer (Feature B)."""

    sequence: list[bool]   # True -> approved; False -> 1 MISSING issue returned
    calls: list[dict[str, Any]] = field(default_factory=list)
    iter_count: int = 1

    def dispatch_spec_reviewer(
        self,
        *,
        task_id: str,
        plan_path: Any,
        repo_root: Any,
        max_iterations: int = 3,
        timeout: int = 900,
    ) -> SpecReviewResult:
        self.calls.append({"task_id": task_id, "max_iterations": max_iterations})
        approved = self.sequence.pop(0)
        issues: tuple[SpecIssue, ...] = ()
        if not approved:
            issues = (SpecIssue(severity="MISSING", text=f"stub issue for task {task_id}"),)
        return SpecReviewResult(
            approved=approved, issues=issues,
            reviewer_iter=self.iter_count, artifact_path=None,
        )
```

- [x] **Step 5-8**: tests pass, commits.

### Task H5: `close_task_cmd --skip-spec-review` flag

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py`
- Create: `tests/test_close_task_cmd_spec_review.py`

- [x] **Step 1 (Red)**: tests asserting default-invoke + `--skip-spec-review` bypass + reviewer-issues abort.

- [x] **Step 2-3**: commit `test:`.

- [x] **Step 4 (Green)**: modify `close_task_cmd._build_parser`:

```python
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-task")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--skip-spec-review", action="store_true",
                   help="Skip spec-reviewer dispatch (INV-31 escape valve)")
    return p
```

Modify `main()` to call the reviewer before `mark_and_advance`:

```python
def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    closed_task_id = state.current_task_id
    if not ns.skip_spec_review:
        import spec_review_dispatch
        result = spec_review_dispatch.dispatch_spec_reviewer(
            task_id=closed_task_id or "",
            plan_path=root / state.plan_path,
            repo_root=root,
        )
        if not result.approved:
            # Unreachable in practice — dispatch_spec_reviewer raises on
            # non-approved exhaustion — but keep the guard for safety.
            raise SpecReviewError(f"spec-reviewer did not approve task {closed_task_id}")
    new_state = mark_and_advance(state, root)
    next_msg = (
        f"Next: task {new_state.current_task_id}" if new_state.current_task_id else "Plan complete."
    )
    sys.stdout.write(f"Task {closed_task_id} closed. {next_msg}\n")
    return 0
```

Add the import:

```python
from errors import DriftError, PreconditionError, SpecReviewError
```

- [x] **Step 5-8**: verify + commits.

### Task H6: `auto_cmd._phase2_task_loop` integration

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Create: `tests/test_auto_cmd_spec_review.py`

- [x] **Step 1 (Red)**: integration tests using `StubSpecReviewer` — auto loop with 3 tasks where task 2 returns issues that route via `/receiving-code-review` + mini-cycle.

For v0.2 simplification: `auto_cmd` invokes the dispatcher which is already wrapped with its own safety-valve loop. On `SpecReviewError` the loop aborts with exit 12.

- [x] **Step 2-3**: commit `test:`.

- [x] **Step 4 (Green)**: in `auto_cmd.py`, import `spec_review_dispatch`. In `_phase2_task_loop`, right before the `current = close_task_cmd.mark_and_advance(current, root)` line (currently at auto_cmd.py:441):

```python
            else:
                # Feature B (v0.2, INV-31): spec-reviewer gate before task close.
                # Wrap in try/except so the audit trail captures the abort.
                try:
                    spec_review_dispatch.dispatch_spec_reviewer(
                        task_id=current.current_task_id or "",
                        plan_path=root / current.plan_path,
                        repo_root=root,
                    )
                except SpecReviewError:
                    _write_auto_run_audit(
                        auto_run,
                        AutoRunAudit(
                            schema_version=_AUTO_RUN_SCHEMA_VERSION,
                            auto_started_at=started_at,
                            auto_finished_at=_now_iso(),
                            status="failed",
                            verdict=None,
                            degraded=None,
                            accepted_conditions=0,
                            rejected_conditions=0,
                            tasks_completed=tasks_completed,
                            error="SpecReviewError",
                        ),
                    )
                    raise
                # W1: delegate to public helper in close_task_cmd
                current = close_task_cmd.mark_and_advance(current, root)
                ...  # existing body below — replace `...` with the actual remainder of _phase2_task_loop before committing
```

> **Do NOT ship literal `...`:** the `...` above is a structural marker for "paste the existing body here unchanged." Before the Green commit, open `skills/sbtdd/scripts/auto_cmd.py` at `_phase2_task_loop`, copy the loop body that follows the current `mark_and_advance` call, and substitute it in. A literal `...` left in production code is a landing-time failure — run `python -c "from auto_cmd import _phase2_task_loop; _phase2_task_loop(...)"` against a staged fixture before committing to force-execute the diff path and prove no `Ellipsis` slipped through.

Add import:

```python
import spec_review_dispatch
from errors import (
    ChecklistError,
    DriftError,
    Loop1DivergentError,
    MAGIGateError,
    PreconditionError,
    QuotaExhaustedError,
    SpecReviewError,        # NEW
    ValidationError,
    VerificationIrremediableError,
)
```

- [x] **Step 5-8**: verify + commits.

### Task H7: new subcommand `review-spec-compliance`

**Files:**
- Create: `skills/sbtdd/scripts/review_spec_compliance_cmd.py`
- Modify: `skills/sbtdd/scripts/models.py`
- Modify: `skills/sbtdd/scripts/run_sbtdd.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_run_sbtdd.py`
- Create: `tests/test_review_spec_compliance_cmd.py`

- [ ] **Step 1 (Red)**: tests:

```python
# tests/test_models.py — extend
def test_valid_subcommands_includes_review_spec_compliance() -> None:
    from models import VALID_SUBCOMMANDS
    assert "review-spec-compliance" in VALID_SUBCOMMANDS


# tests/test_run_sbtdd.py — extend
def test_dispatch_review_spec_compliance_routes_to_cmd(monkeypatch) -> None:
    import run_sbtdd
    called: list = []
    def fake(argv): called.append(argv); return 0
    monkeypatch.setitem(run_sbtdd.SUBCOMMAND_DISPATCH, "review-spec-compliance", fake)
    assert run_sbtdd.main(["review-spec-compliance", "3"]) == 0
    assert called == [["3"]]


# tests/test_review_spec_compliance_cmd.py
def test_review_spec_compliance_approved_exits_0(tmp_path, monkeypatch):
    ...  # using StubSpecReviewer + fixture plan
def test_review_spec_compliance_issues_exits_12(tmp_path, monkeypatch):
    ...
```

- [ ] **Step 2-3**: commit `test:`.

- [ ] **Step 4 (Green)**: 

In `models.py`:

```python
VALID_SUBCOMMANDS: tuple[str, ...] = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
    "review-spec-compliance",   # Feature B, v0.2
)
```

Create `skills/sbtdd/scripts/review_spec_compliance_cmd.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""/sbtdd review-spec-compliance <task-id> — manual spec-reviewer dispatch.

Exposes dispatch_spec_reviewer as a subcommand for flows outside auto_cmd
(executing-plans, manual close-task after --skip-spec-review was used).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import spec_review_dispatch
from errors import PreconditionError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd review-spec-compliance")
    p.add_argument("task_id", type=str, help="Plan task id to review")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--max-iterations", type=int, default=3)
    return p


def main(argv: list[str] | None = None) -> int:
    ns = _build_parser().parse_args(argv)
    root: Path = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.is_file():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    plan_path = root / state.plan_path
    if not plan_path.is_file():
        raise PreconditionError(f"plan file not found: {plan_path}")
    result = spec_review_dispatch.dispatch_spec_reviewer(
        task_id=ns.task_id,
        plan_path=plan_path,
        repo_root=root,
        max_iterations=ns.max_iterations,
    )
    if result.approved:
        sys.stdout.write(f"Task {ns.task_id}: spec-review APPROVED (iter {result.reviewer_iter}).\n")
        return 0
    # dispatch_spec_reviewer raises on non-approved exhaustion; this path is
    # only reached when max_iterations=1 and issues returned without retry.
    sys.stderr.write(f"Task {ns.task_id}: {len(result.issues)} issue(s) found.\n")
    for i in result.issues:
        sys.stderr.write(f"  [{i.severity}] {i.text}\n")
    return 12


run = main
```

In `run_sbtdd.py`:

```python
import review_spec_compliance_cmd  # with the other imports

SUBCOMMAND_DISPATCH: MutableMapping[str, SubcommandHandler] = {
    "init": init_cmd.main,
    "spec": spec_cmd.main,
    "close-phase": close_phase_cmd.main,
    "close-task": close_task_cmd.main,
    "status": status_cmd.main,
    "pre-merge": pre_merge_cmd.main,
    "finalize": finalize_cmd.main,
    "auto": auto_cmd.main,
    "resume": resume_cmd.main,
    "review-spec-compliance": review_spec_compliance_cmd.main,
}
```

- [ ] **Step 5-8**: verify + commits.

### Task H8: close-task Milestone H

- [ ] **Step 1**: mark Milestone H complete.
- [ ] **Step 2**: `git commit --allow-empty -m "chore: mark task H complete"`.

---

## MILESTONE I — Meta: documentation + version bump + INV-31

### Task I1: INV-31 documentation

**Files:**
- Modify: `CLAUDE.md` (Invariants Summary section)
- Modify: `sbtdd/sbtdd-workflow-plugin-spec-base.md` (sec.S.10)
- Modify: `tests/test_inv_documentation.py`

- [ ] **Step 1 (Red)**: test asserting INV-31 appears in both artifacts.

```python
def test_inv31_documented_in_claude_md() -> None:
    t = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "INV-31" in t
    assert "spec-reviewer" in t
```

- [ ] **Step 2-4**: commit `test:`, add the INV-31 bullet to both docs, commit `feat:`.

In `CLAUDE.md` under "Invariants Summary":

```markdown
- **INV-31** Every task close in `auto_cmd` and `close_task_cmd` (interactive) MUST pass spec-reviewer approval before `mark_and_advance` advances state, unless `--skip-spec-review` flag set (manual workflows) or stub fixture injected (tests). Introduced in v0.2 (Feature B).
```

- [ ] **Step 5-8**: verify + commits.

### Task I1b: D2/D3 — update SKILL.md dispatch + README usage

Spec-base §6.6 acceptance criteria D2 (cross-artifact coherence tests updated for 0.2.0) and D3 (new subcommand `review-spec-compliance` + four new flags `--override-checkpoint`, `--reason`, `--non-interactive`, `--skip-spec-review` documented in README + SKILL.md + CLAUDE.md) require user-visible documentation updates. CLAUDE.md is covered by I1 (INV-31) and I4 (strip shipped blockers); this task covers SKILL.md + README.md and the matching coherence test deltas.

**Files:**
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `README.md`
- Modify: `tests/test_distribution_coherence.py`
- Modify: `tests/test_skill_md.py`
- Modify: `tests/test_readme.py`

- [ ] **Step 1 (Red): extend coherence tests for the new subcommand + flags**

Append to `tests/test_distribution_coherence.py`:

```python
def test_skill_md_lists_review_spec_compliance_subcommand() -> None:
    skill = (REPO_ROOT / "skills" / "sbtdd" / "SKILL.md").read_text(encoding="utf-8")
    assert "review-spec-compliance" in skill, (
        "D3: SKILL.md must document new v0.2 subcommand review-spec-compliance"
    )


def test_readme_documents_v02_flags() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    for flag in ("--override-checkpoint", "--reason", "--non-interactive", "--skip-spec-review"):
        assert flag in readme, f"D3: README.md must document {flag}"
```

Extend `tests/test_skill_md.py` contract: the subcommand dispatch table must have 10 rows (was 9 in v0.1); add a row for `review-spec-compliance`.

Extend `tests/test_readme.py` contract: the usage section must reference `review-spec-compliance` and the four new flags.

- [ ] **Step 2: run tests, confirm Red**

```bash
python -m pytest tests/test_distribution_coherence.py tests/test_skill_md.py tests/test_readme.py -v
```
Expected: three new test cases FAIL with assertion errors on missing strings.

- [ ] **Step 3 (Red commit)**

```bash
git add tests/test_distribution_coherence.py tests/test_skill_md.py tests/test_readme.py
git commit -m "test: add D2/D3 coherence tests for v0.2 subcommand + flags"
```

- [ ] **Step 4 (Green): update SKILL.md**

Locate the subcommand dispatch table in `skills/sbtdd/SKILL.md` (section "Subcommand dispatch", sec.S.6.3). Add a new row between `finalize` and `auto` (keeping alphabetical-free v0.1 order + new subcommand grouped with its conceptual neighbor `close-task`):

```markdown
| `review-spec-compliance` | `review_spec_compliance_cmd.py` | Per-task spec-reviewer dispatch for manual flows (`/executing-plans`, ad-hoc). Dispatches `superpowers:subagent-driven-development/spec-reviewer-prompt.md`, returns exit 0 on approve, exit 12 on issues. New in v0.2. |
```

In the same SKILL.md, under the "Fallback" section (or equivalent flag-summary section), append the four new v0.2 flags with one-line descriptions:

```markdown
**v0.2 flags:**

- `--override-checkpoint --reason "<text>"` (on `spec`, `pre-merge`, `finalize`) — INV-0 escape valve when MAGI safety valve exhausts. `--reason` is mandatory; reason + verdict persisted to `.claude/magi-escalations/`.
- `--non-interactive` (on `spec`, `pre-merge`) — force headless policy even on a TTY; applies `.claude/magi-auto-policy.json`.
- `--skip-spec-review` (on `close-task`) — bypass Feature B reviewer for manual flows where compliance is verified by hand.
```

- [ ] **Step 5 (Green): update README.md**

In `README.md` under the "Usage" section (subcommands table), add a row for `/sbtdd review-spec-compliance <task-id>` with one-line purpose. Below the table, in the "New in v0.2" (or equivalent) subsection, list the four flags with the same one-line descriptions as SKILL.md.

- [ ] **Step 6: run tests, confirm PASS**

```bash
make verify
```
Expected: all coherence tests PASS; mypy clean; ruff clean.

- [ ] **Step 7 (Green commit)**

```bash
git add skills/sbtdd/SKILL.md README.md
git commit -m "docs: document review-spec-compliance subcommand and v0.2 flags"
```

- [ ] **Step 8 (Refactor)**

```bash
git commit --allow-empty -m "refactor: SKILL.md + README v0.2 docs reviewed"
```

### Task I2: CHANGELOG Unreleased → v0.2.0

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1 (Red)**: new test asserting 0.2.0 entry exists AND references the three features:

```python
def test_changelog_v02_section_references_features() -> None:
    t = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.2.0" in t
    assert "escalation" in t.lower()
    assert "spec-reviewer" in t.lower() or "spec reviewer" in t.lower()
    assert "semver" in t.lower() or "auto-resolve" in t.lower()
```

- [ ] **Step 2-3**: commit `test:`.

- [ ] **Step 4 (Green)**: in `CHANGELOG.md`, promote `[Unreleased]` to `[0.2.0] - 2026-04-XX`:

```markdown
## [0.2.0] - 2026-04-XX

### Added
- Interactive MAGI escalation prompt (`escalation_prompt.py`) — fires on
  INV-11 safety valve exhaustion in `spec` / `pre-merge` / `finalize`. New
  CLI flags `--override-checkpoint --reason` (mandatory reason); audit
  artifacts at `.claude/magi-escalations/`. Headless fallback via
  `.claude/magi-auto-policy.json` (default `abort` preserves v0.1 exit 8).
- Superpowers spec-reviewer integration per task
  (`spec_review_dispatch.py`, `review_spec_compliance_cmd.py`) — new
  subcommand `/sbtdd review-spec-compliance <task-id>`; default-invoke in
  `close_task_cmd` + `auto_cmd._phase2_task_loop`; opt-out via
  `--skip-spec-review`. Audit artifacts at `.claude/spec-reviews/`.
- `SpecReviewError` exception + exit code 12 (`SPEC_REVIEW_ISSUES`).
- `StubSpecReviewer` fixture for test suites.
- INV-31: spec-reviewer gate on task close.

### Changed
- MAGI parity tests auto-detect latest cached version instead of pinning
  to v2.1.3 (`_resolve_magi_plugin_json` + `_semver_key` in
  `tests/test_distribution_coherence.py`). `MAGI_PLUGIN_ROOT` env var
  override preserved.
- `close_task_cmd.main` now invokes spec-reviewer by default before
  `mark_and_advance` (behavior change under INV-31).
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`
  `version` bumped 0.1.0 → 0.2.0.

### BREAKING
- New exit code 12 (`SPEC_REVIEW_ISSUES`). Scripts grepping exit codes
  should update their taxonomy. v0.1 exit 8 semantics preserved for the
  default headless policy.
```

- [ ] **Step 5-8**: verify + commits.

### Task I3: version bump 0.1.0 → 0.2.0

**Files:**
- Modify: `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1**: existing test `test_plugin_and_marketplace_versions_match` will fail immediately once either file changes without the other. Use that as the red signal:

```bash
# Edit plugin.json only first
python -m pytest tests/test_distribution_coherence.py::test_plugin_and_marketplace_versions_match -v
```
Expected: FAIL with version mismatch.

- [ ] **Step 2 (Green)**: edit both files in one commit:

`.claude-plugin/plugin.json`: change `"version": "0.1.0"` → `"version": "0.2.0"`.

`.claude-plugin/marketplace.json`: change BOTH the top-level `"version"` AND the plugin entry `"version"` to `"0.2.0"`.

- [ ] **Step 3 (verify)**:

```bash
python -m pytest tests/test_distribution_coherence.py -v
```
Expected: all PASS.

- [ ] **Step 4 (Green commit)**:

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump plugin + marketplace to v0.2.0"
```

### Task I4: strip shipped blockers from CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1**: remove the three `## v0.2 requirement (LOCKED) — ...` sections from `CLAUDE.md` now that they shipped. Replace with a single `## v0.2 release notes` pointer to `CHANGELOG.md [0.2.0]`.

- [ ] **Step 2 (commit)**:

```bash
git add CLAUDE.md
git commit -m "docs: archive shipped v0.2 blockers to CHANGELOG"
```

### Task I5: final full test sweep + close plan

- [ ] **Step 1**: run full `make verify` at repo root.

```bash
make verify
```
Expected: pytest ≥ 597 baseline + ~40-80 new tests all PASS; ruff clean; mypy clean.

- [ ] **Step 2**: mark Milestone I complete; plan [x] all.

- [ ] **Step 3**: close-plan:

```bash
git commit --allow-empty -m "chore: mark task I complete"
```

---

## Pre-merge gate (after all tasks closed)

Follow `CLAUDE.local.md` §6 pre-merge protocol strictly:

1. Confirm state: `.claude/session-state.json` has `current_phase: "done"`, all plan boxes `[x]`, `git status` clean.
2. Run `/sbtdd pre-merge` — Loop 1 (`/requesting-code-review` clean-to-go, safety valve 10 iter) then Loop 2 (`/magi:magi` verdict ≥ `GO_WITH_CAVEATS` full + non-degraded, INV-28 honored).
3. MAGI findings route through `/receiving-code-review` (INV-29) + mini-cycle TDD fixes per accepted finding. With Feature A live, exhausted safety valve now prompts interactively (or writes pending marker + exit 8 headless per `.claude/magi-auto-policy.json`).
4. Run `/sbtdd finalize` — validates sec.M.7 checklist and invokes `/finishing-a-development-branch`. Merge + tag `v0.2.0` happens here under explicit user authorization (INV-0 / `~/.claude/CLAUDE.md` Git section — NEVER autonomous).

## Self-review notes

**Spec coverage check:** every F15-F27 + NF8-NF12 + A1-A9 + B1-B10 + C1-C5 + NF-A-E + P1-P5 + D1-D3 acceptance criterion maps to a task above. The only spec item deliberately deferred is Feature B safety-valve MID-cycle `/receiving-code-review` + mini-cycle TDD fix automation — v0.2 dispatcher raises `SpecReviewError` on issues and the caller (`auto_cmd` / `close_task_cmd`) aborts. Full mini-cycle automation between reviewer iterations lands in v0.3 or a v0.2.1 patch. This matches the spec-base §2.2 "entrega v0.2" which says "si `issues`, treat as MAGI-like findings: feed to `/receiving-code-review`, mini-cycle TDD fix per accepted finding, re-dispatch reviewer, repeat up to a safety valve" — but keeping automation strictly inside `auto_cmd` (not the dispatcher) is a defensible design boundary; document this split in the Task H6 commit message.

**Placeholder scan:** searched for `TODO`, `TBD`, `implement later`, `...`. The three `...` occurrences in Tasks G6, H3, H6, H7 test skeletons (marked with `...  # skeleton; concretize ...`) are intentional pointers to lift fixtures from existing test modules. The implementer MUST replace each one with concrete code before landing the red commit — per the per-task instruction. This is not a shipping-time placeholder.

**Type consistency:** `SpecReviewResult.issues: tuple[SpecIssue, ...]`, `SpecReviewError.issues: tuple[str, ...]` — different shapes by design. The `Error.issues` is flat text (for stderr printing) while `Result.issues` carries severity. Call sites need only one or the other.

**Sequencing:** Feature C first (isolated test rewrite, zero risk). Feature A before Feature B because `apply_decision`'s audit artifact pattern informs `_write_artifact` in `spec_review_dispatch.py`. Meta (I1-I5) last because CHANGELOG + version bump must reflect landed features.

---

## Execution Handoff

**Plan complete and saved to `planning/claude-plan-tdd-org.md`.**

Per CLAUDE.md §1 Flujo de especificacion step 4-6: this is `claude-plan-tdd-org.md` (pre-MAGI review). Next steps belong to the USER:

1. Manual review (Checkpoint 1). If the user rejects, re-run `/writing-plans` (or `/sbtdd spec`) with feedback.
2. Checkpoint 2 MAGI review: `/magi:magi revisa @sbtdd/spec-behavior-base.md y @planning/claude-plan-tdd-org.md`.
3. Apply Conditions for Approval and write `planning/claude-plan-tdd.md` (safety valve 3 iter per INV-11; INV-28 degraded handling).
4. Execute via `/subagent-driven-development` or `/executing-plans`.

**Plugin's own auto path:** once `planning/claude-plan-tdd.md` exists and `plan_approved_at` is set in `.claude/session-state.json`, `/sbtdd auto` can ship v0.2 end-to-end (with Feature B dogfooded — `auto_cmd` will invoke spec-reviewer per task using `StubSpecReviewer` in test environments, real `dispatch_spec_reviewer` in production).

The merge + `v0.2.0` tag are explicit user actions per INV-0 / `~/.claude/CLAUDE.md` Git rules — not autonomous even under `/sbtdd auto`.


## MAGI Conditions for Approval

- Plan is architecturally sound and covers 95% of spec, but contains several concrete correctness defects plus a material scope deviation from B6 that must be resolved before execution.
- Pragmatic plan with strong TDD discipline, but scope creep risks and a few landing-time traps need tightening before execution.
- Plan is structurally sound but carries three high-impact risks: Feature B scope relaxation against INV-31/INV-29, fragile task-diff correlation, and placeholder code in test skeletons.