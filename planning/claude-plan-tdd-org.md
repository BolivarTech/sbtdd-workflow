# v1.0.3 Template Alignment + v1.0.2 Dogfood Remediations Implementation Plan

> Generado 2026-05-06 a partir de sbtdd/spec-behavior.md v1.0.3 via
> superpowers:writing-plans skill (interactive session, post-MAGI
> Checkpoint 2 STRONG GO unanimous expected). Frontmatter required by
> spec_lint R5 (Item C v1.0.2 enforcement).
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax (open + closed bracket forms) for tracking.

**Goal:** Ship v1.0.3 — completar la auditoria LOCKED original (MAGI gate template alignment vs canonical template) + arreglar gaps de infraestructura del v1.0.2 own-cycle dogfood (Windows long-filename, drift detector false-positive, spec-snapshot manual regen friction, subagent close-task convention divergence). 5 plan tasks (A audit + B Windows fix + C drift + D autoregen + E close-task codification) over 2 parallel subagent tracks; 2 methodology activities (D' Linux/POSIX dogfood + E' --resume-from-magi smoke test) executed by orchestrator.

**Architecture:** 2-track parallel dispatch with disjoint surfaces. Track Alpha (audit-only) writes `docs/audits/v1.0.3-magi-gate-template-alignment.md` + `tests/test_magi_template_alignment.py` — NO production code. Track Beta (sequential B → C → D → E) modifies `pre_merge_cmd.py` + `drift.py` + `spec_cmd.py` + `state_file.py` + `subprocess_utils.py` (possibly) + doc files. Cero file overlap. Activity D' (Linux/POSIX dogfood post Item B fix) + Activity E' (--resume-from-magi smoke test post Track-close) run mid-cycle in orchestrator session before pre-merge gate.

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict, stdlib-only on hot paths. TDD-Guard active. Brainstorming refinements 2026-05-06: Q1 = 2-track parallel (Alpha audit-only, Beta code+doc); Q2 = Item E close-task codify via `/sbtdd close-task` automation (Option B); hybrid methodology (Opcion A run_magi.py for Checkpoint 2; Opcion B --resume-from-magi as Activity E' smoke test).

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-06`.
- **Task close protocol (Q2 Option B mandate)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review` after Refactor verify-clean. Manual plan-file checkbox edits are NON-CONFORMING and trigger drift detection. Use `--skip-spec-review` to bypass INV-31 spec-reviewer dispatch (~1-2 min/task overhead acceptable but not required for these defensive infrastructure items).
- INV-37 composite-signature tripwire preserved unchanged in all paths.
- Item C v1.0.2 spec_lint gate (R1-R5) preserved unchanged.

**Commit prefix map per task type** (from `CLAUDE.local.md` §5):

| Phase | Prefix |
|-------|--------|
| Red (failing test) | `test:` |
| Green (impl) | `feat:` (new module/feature) or `fix:` (bug fix) |
| Refactor | `refactor:` |
| Task close (via `/sbtdd close-task`) | `chore:` (automated) |

---

## Track Alpha — Template alignment audit (Subagent #1, single-task)

**Owner**: Subagent #1 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Beta): `docs/audits/v1.0.3-magi-gate-template-alignment.md` (new); `tests/test_magi_template_alignment.py` (new).
**Wall-time estimated**: ~1 day.

### Task 1: Item A — MAGI gate template alignment audit

**Files:**
- Create: `docs/audits/v1.0.3-magi-gate-template-alignment.md`
- Create: `tests/test_magi_template_alignment.py`
- Read-only inspection: `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`, `skills/sbtdd/scripts/pre_merge_cmd.py`, `skills/sbtdd/scripts/magi_dispatch.py`, `skills/sbtdd/scripts/auto_cmd.py`, `templates/CLAUDE.local.md.template`, `skills/sbtdd/scripts/config.py`

Covers escenarios A-1, A-2, A-3, A-4, A-5 from spec sec.4.

#### Red Phase

- [ ] **Step 1: Write the failing test**

Create `tests/test_magi_template_alignment.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Cross-artifact alignment test: plugin's MAGI dispatch path matches
canonical template at D:\\jbolivarg\\BolivarTech\\AI_Tools\\magi-gate-template.md.

Per spec sec.2.1 v1.0.3 Item A. Pattern follows tests/test_changelog.py
HF1 cross-artifact wording alignment (line-anchored grep template
canonical strings vs plugin code paths).

Covers escenarios A-3 (alignment grep) + A-5 (regression detection).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest


_TEMPLATE_PATH = Path(
    os.environ.get(
        "SBTDD_MAGI_TEMPLATE_PATH",
        r"D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md",
    )
)
_REPO_ROOT = Path(__file__).resolve().parents[1]


def _canonical_strings_from_template() -> list[str]:
    """Extract required canonical strings from template's normative sections.

    Each entry is a substring that MUST appear in the plugin's MAGI
    dispatch path code or templates. Curated list per audit findings;
    update when audit doc changes.
    """
    return [
        # Verdict labels (Pass threshold section)
        "STRONG_NO_GO",
        "HOLD",
        "GO_WITH_CAVEATS",
        "GO",
        "STRONG_GO",
        # Carry-forward block header (per template's normative format)
        "Prior triage context",
        # Per-project setup checklist marker
        "magi_threshold",
        # Cost awareness signal
        "auto_skill_models",
    ]


def _grep_repo(pattern: str, search_paths: list[Path]) -> list[tuple[Path, int]]:
    """Return list of (path, line_number) where pattern appears."""
    hits = []
    for base in search_paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    hits.append((path, lineno))
    return hits


def test_template_file_exists():
    """A-3 prerequisite: template canonical source exists."""
    if not _TEMPLATE_PATH.exists():
        pytest.skip(
            f"Template not found at {_TEMPLATE_PATH}. "
            "Set SBTDD_MAGI_TEMPLATE_PATH env var to override."
        )
    assert _TEMPLATE_PATH.is_file()


def test_canonical_strings_present_in_plugin():
    """A-3: required canonical strings from template appear in plugin code."""
    if not _TEMPLATE_PATH.exists():
        pytest.skip("Template not available")

    template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    search_paths = [
        _REPO_ROOT / "skills" / "sbtdd" / "scripts",
        _REPO_ROOT / "templates",
    ]
    missing = []
    for canonical in _canonical_strings_from_template():
        if canonical not in template_text:
            pytest.skip(f"Canonical string {canonical!r} not in template; outdated test fixture")
        hits = _grep_repo(canonical, search_paths)
        if not hits:
            missing.append(canonical)
    assert not missing, (
        "Plugin missing canonical template strings:\n"
        + "\n".join(f"  - {s!r}" for s in missing)
    )


def test_audit_doc_exists():
    """A-1 prerequisite: audit doc was generated by Track Alpha."""
    audit_doc = _REPO_ROOT / "docs" / "audits" / "v1.0.3-magi-gate-template-alignment.md"
    assert audit_doc.exists(), f"Audit doc missing: {audit_doc}"


def test_audit_doc_has_required_columns():
    """A-2: audit doc contains tabla con required columns per row."""
    audit_doc = _REPO_ROOT / "docs" / "audits" / "v1.0.3-magi-gate-template-alignment.md"
    if not audit_doc.exists():
        pytest.skip("Audit doc not yet generated")
    text = audit_doc.read_text(encoding="utf-8")
    # Header columns required by spec sec.2.1
    required_columns = ["Template Section", "Plugin Impl Path", "Status", "Evidence", "Action"]
    for col in required_columns:
        assert col in text, f"Audit doc missing column header: {col}"


def test_audit_doc_status_values_canonical():
    """A-2: status values are one of {MATCH, GAP, OBSOLETE}."""
    audit_doc = _REPO_ROOT / "docs" / "audits" / "v1.0.3-magi-gate-template-alignment.md"
    if not audit_doc.exists():
        pytest.skip("Audit doc not yet generated")
    text = audit_doc.read_text(encoding="utf-8")
    canonical_statuses = {"MATCH", "GAP", "OBSOLETE"}
    # Verify at least one canonical status appears (smoke check for non-empty audit)
    assert any(s in text for s in canonical_statuses), (
        f"Audit doc has no rows with canonical status (expected one of {canonical_statuses})"
    )
```

- [ ] **Step 2: Run tests to verify failure**

```bash
python -m pytest tests/test_magi_template_alignment.py -v
```

Expected: 5 tests; `test_template_file_exists` PASS (template exists or skip), `test_canonical_strings_present_in_plugin` may PASS or FAIL depending on plugin state, `test_audit_doc_exists` FAIL (audit doc not yet created), `test_audit_doc_has_required_columns` SKIP, `test_audit_doc_status_values_canonical` SKIP.

The Red phase signal here is: `test_audit_doc_exists` FAIL (`AssertionError: Audit doc missing`).

- [ ] **Step 3: Verify + commit Red phase**

```bash
python -m ruff check tests/test_magi_template_alignment.py
python -m ruff format --check tests/test_magi_template_alignment.py
python -m mypy tests/test_magi_template_alignment.py
git add tests/test_magi_template_alignment.py
git commit -m "test: A-1/A-2/A-3/A-5 alignment test scaffolding"
```

#### Green Phase

- [ ] **Step 4: Generate audit doc per template's 6 sections**

Read template (`D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`) section-by-section. For each of the 6 normative sections, audit the corresponding plugin impl path:

1. **Trigger criteria** → `pre_merge_cmd._loop2` + `auto_cmd._phase4`. Inspect what triggers MAGI gate dispatch.
2. **Pass threshold** → `magi_dispatch.invoke_magi` + `verdict_passes_gate` (or equivalent). Verify verdict-action table matches.
3. **Carry-forward format** → `pre_merge_cmd._build_carry_forward` (or equivalent helper). Verify "Prior triage context" block format.
4. **Review summary artifact** → grep for `docs/reviews/<feature>-review-summary.md` emission. Likely GAP per spec sec.2.1.
5. **Cost awareness** → `config.auto_skill_models` field + per-skill model selection. Verify Haiku/Opus per template recommendation.
6. **Per-project setup** → `templates/CLAUDE.local.md.template`. Verify `{placeholder}` markers match template requirements.

Create `docs/audits/v1.0.3-magi-gate-template-alignment.md`:

```markdown
# MAGI Gate Template Alignment Audit — v1.0.3

> Generated 2026-05-06 by Track Alpha subagent during v1.0.3 cycle.
> Audits sbtdd-workflow plugin's MAGI dispatch path against canonical
> template at `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`
> (411 lines, synthesized 2026-05-01).

## Per-section table

| Template Section | Plugin Impl Path | Status | Evidence | Action |
|------------------|------------------|--------|----------|--------|
| Trigger criteria | `skills/sbtdd/scripts/pre_merge_cmd.py:NNN` (`_loop2`) + `skills/sbtdd/scripts/auto_cmd.py:NNN` | MATCH or GAP per investigation | `pre_merge_cmd.py:NNN file:line citation` | resolved / deferred-v1.0.4 / template-amendment |
| Pass threshold | `skills/sbtdd/scripts/magi_dispatch.py:NNN` (`verdict_passes_gate` or equivalent) | per investigation | file:line | per investigation |
| Carry-forward format | `skills/sbtdd/scripts/pre_merge_cmd.py:NNN` (`_build_carry_forward` or equivalent) | per investigation | file:line | per investigation |
| Review summary artifact | (likely GAP — manual emission only) | likely GAP | `docs/reviews/` not auto-emitted | defer to v1.0.4 |
| Cost awareness | `skills/sbtdd/scripts/config.py:NNN` (`auto_skill_models` field) | per investigation | file:line | per investigation |
| Per-project setup | `templates/CLAUDE.local.md.template:NNN` | per investigation | file:line | per investigation |

## GAP routing protocol

For each GAP row:
- **CRITICAL** (template requires + plugin doesn't enforce): backlog entry for Track Beta to fix in this cycle. Document in CHANGELOG `[1.0.3]` Process notes.
- **WARNING** (plugin enforces stricter than template): document discrepancy + defer to v1.0.4 with rationale (probably plugin-correct, template needs amendment).
- **INFO** (doc-only difference): note + defer to v1.0.4.
- **Template defects** (template wrong, plugin right): propose template amendment in this audit doc; physical update to template file out-of-scope (sister project).

## Audit findings summary

(Populated by subagent during execution. Format: per row Status + Evidence + Action with concrete file:line citations.)

## Ship-readiness criteria

- All 6 template sections audited.
- All GAP rows have ACTION populated (resolved / deferred / proposed).
- `tests/test_magi_template_alignment.py` passes (canonical strings present in plugin).
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/test_magi_template_alignment.py -v
```

Expected: 5 tests PASS (assuming canonical strings present in plugin; if missing, those rows become CRITICAL GAPs in audit doc).

If `test_canonical_strings_present_in_plugin` FAILS with missing strings: this is a real CRITICAL GAP. Document in audit doc. Either (a) add canonical string to plugin code as part of Track Alpha minimum-viable-audit deliverable, OR (b) document as CRITICAL backlog entry for Track Beta and SKIP the failing assertion temporarily (use `pytest.skip` with explicit GAP reference). Subagent decision per scope.

- [ ] **Step 6: Verify + commit Green phase**

```bash
make verify
git add docs/audits/v1.0.3-magi-gate-template-alignment.md
git add tests/test_magi_template_alignment.py
git commit -m "feat: template alignment audit doc + cross-artifact test (Item A)"
```

#### Refactor Phase

- [ ] **Step 7: Refactor (audit doc polish)**

Review audit doc for:
- Each row's Status field is one of {MATCH, GAP, OBSOLETE}.
- Each row's Evidence field has concrete file:line citation (not vague "see code").
- Each row's Action field describes resolution (not blank).
- Summary section captures GAP/MATCH stats.

If polish needed, apply + verify.

- [ ] **Step 8: Verify + commit Refactor phase (skip if no changes)**

```bash
make verify
# If polish applied:
# git add docs/audits/v1.0.3-magi-gate-template-alignment.md
# git commit -m "refactor: polish audit doc evidence + action columns"
```

#### Task close

- [ ] **Step 9: Close task via `/sbtdd close-task` automation (Q2 Option B)**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

Expected: all `- [ ]` step checkboxes in Task 1 section flipped to `- [x]`. Atomic `chore: mark task 1 complete` commit landed (plan diff only). State file advances to `current_task_id="2"` (Item B), `current_phase="red"`.

---

## Track Beta — Code + doc fixes (Subagent #2, sequential B → C → D → E)

**Owner**: Subagent #2 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Alpha): `skills/sbtdd/scripts/pre_merge_cmd.py` + `skills/sbtdd/scripts/drift.py` + `skills/sbtdd/scripts/spec_cmd.py` + `skills/sbtdd/scripts/state_file.py` + `skills/sbtdd/scripts/subprocess_utils.py` (possibly) + `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template` + tests.
**Wall-time estimated**: ~3 days.

### Task 2: Item B — Cross-check Windows long-filename fix

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py` (`_loop2_with_cross_check` o downstream subprocess invocation — exact location pending Beta investigation)
- Possibly modify: `skills/sbtdd/scripts/subprocess_utils.py` (long-path helper if needed)
- Modify: `tests/test_pre_merge_cross_check.py` (extend with B-1 to B-5 escenarios)

Covers escenarios B-1, B-2, B-3, B-4, B-5 from spec sec.4.

#### Red Phase

- [ ] **Step 1: Investigate cross-check temp dir construction**

Subagent reads `skills/sbtdd/scripts/pre_merge_cmd.py` to identify exact location where cross-check temp paths are constructed. Look for `tempfile.mkdtemp(prefix=...)` calls or similar within `_loop2_with_cross_check` or downstream subprocess invocation helpers. Document the exact file:line in commit message of subsequent Red commit.

- [ ] **Step 2: Write the failing reproduction test**

Append to `tests/test_pre_merge_cross_check.py`:

```python
import os
import tempfile
from pathlib import Path

import pytest


def _make_long_synthetic_path(tmp_path: Path, target_length: int) -> Path:
    """Create a path under tmp_path whose total length is at least target_length chars."""
    base = tmp_path
    # Pad with nested dirs of fixed name until total length >= target_length
    pad_segment = "x" * 8  # short segment to control length precisely
    while len(str(base / "f.json")) < target_length:
        base = base / pad_segment
        base.mkdir(exist_ok=True)
    return base / "f.json"


@pytest.mark.skipif(os.name != "nt", reason="WinError 206 is Windows-only")
def test_b1_b2_long_path_handling_post_fix(tmp_path):
    """B-1 + B-2: synthetic long path post-fix succeeds (Windows-only).

    Pre-fix: synthetic path >= 260 chars triggers WinError 206.
    Post-fix: shorter prefix OR \\?\\ syntax OR project-relative dir
    bypasses MAX_PATH limit.
    """
    long_path = _make_long_synthetic_path(tmp_path, target_length=270)
    assert len(str(long_path)) >= 260, (
        f"Test setup error: path only {len(str(long_path))} chars"
    )
    # Post-fix behavior: write succeeds
    long_path.write_text("test", encoding="utf-8")
    assert long_path.read_text(encoding="utf-8") == "test"


def test_b3_paths_300_plus_chars_work(tmp_path):
    """B-3: paths >= 300 chars work post-fix (NF36 robustness).

    Cross-platform reproduction: write + read at 300+ char path.
    On Windows, requires Item B fix; on POSIX, always works (no MAX_PATH).
    """
    long_path = _make_long_synthetic_path(tmp_path, target_length=300)
    assert len(str(long_path)) >= 300
    long_path.write_text("payload", encoding="utf-8")
    assert long_path.read_text(encoding="utf-8") == "payload"


def test_b4_short_paths_backward_compat(tmp_path):
    """B-4: normal-length paths (<260 chars) still work (no regression)."""
    short_path = tmp_path / "short.json"
    assert len(str(short_path)) < 260
    short_path.write_text("ok", encoding="utf-8")
    assert short_path.read_text(encoding="utf-8") == "ok"


def test_b5_posix_unaffected(tmp_path):
    """B-5: POSIX runtime cross-check unaffected by fix (POSIX has no MAX_PATH)."""
    if os.name == "nt":
        pytest.skip("POSIX-only test")
    # On POSIX, long paths just work
    long_path = _make_long_synthetic_path(tmp_path, target_length=400)
    long_path.write_text("posix-ok", encoding="utf-8")
    assert long_path.read_text(encoding="utf-8") == "posix-ok"
```

- [ ] **Step 3: Run test to verify Red signal**

```bash
python -m pytest tests/test_pre_merge_cross_check.py::test_b1_b2_long_path_handling_post_fix tests/test_pre_merge_cross_check.py::test_b3_paths_300_plus_chars_work -v
```

Expected on Windows pre-fix: `test_b1_b2_long_path_handling_post_fix` may FAIL with WinError 206 (or similar long-path error) if the test fixture itself triggers it. On Linux/POSIX: PASS (no MAX_PATH).

If tests pass on Windows pre-fix, the synthetic fixture isn't aggressive enough — increase target_length to 400 and/or use deeper nesting.

- [ ] **Step 4: Verify + commit Red**

```bash
python -m ruff check tests/test_pre_merge_cross_check.py
python -m ruff format --check tests/test_pre_merge_cross_check.py
python -m mypy tests/test_pre_merge_cross_check.py
git add tests/test_pre_merge_cross_check.py
git commit -m "test: B-1..B-5 long-path handling tripwires (cross-platform)"
```

#### Green Phase

- [ ] **Step 5: Apply mitigation (R2 ladder — start with shorter prefix)**

Per spec sec.2.2 Mitigation ladder, attempt #1 = shorter temp dir prefix. Subagent locates the cross-check temp dir construction (identified in Step 1 investigation) and reduces prefix length.

Example diff (exact location subagent-determined):

```python
# Before (hypothetical):
temp_dir = tempfile.mkdtemp(prefix="sbtdd-magi-cross-check-")

# After:
temp_dir = tempfile.mkdtemp(prefix="sbm-")
```

If shorter prefix insufficient (test still fails on Windows with sufficiently long base path), escalate to attempt #2 (`\\?\` long-path syntax wrapping) or attempt #3 (project-relative `.claude/magi-cross-check/.tmp/<run-id>/`). Document choice in commit message.

- [ ] **Step 6: Run tests to verify Green pass**

```bash
python -m pytest tests/test_pre_merge_cross_check.py -v
```

Expected: all B-1..B-5 tests PASS. Existing pre-merge cross-check tests continue passing (regression check).

- [ ] **Step 7: Verify + commit Green phase**

```bash
make verify
git add skills/sbtdd/scripts/pre_merge_cmd.py
# Possibly also subprocess_utils.py if helper added
git commit -m "fix: cross-check Windows long-path mitigation (Item B R2 step 1)"
```

#### Refactor Phase

- [ ] **Step 8: Refactor (extract helper if pattern repeats)**

If the path construction logic appears in multiple places, extract a helper function (e.g., `_make_short_temp_dir(suffix: str) -> Path`) in `subprocess_utils.py` and replace inline calls. Otherwise skip.

- [ ] **Step 9: Verify + commit Refactor phase (skip if no changes)**

```bash
make verify
# If helper extracted:
# git add skills/sbtdd/scripts/subprocess_utils.py skills/sbtdd/scripts/pre_merge_cmd.py
# git commit -m "refactor: extract _make_short_temp_dir helper"
```

#### Task close

- [ ] **Step 10: Close task via automation**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

State file advances to `current_task_id="3"` (Item C), `current_phase="red"`.

---

### Task 3: Item C — Drift detector line-anchored match

**Files:**
- Modify: `skills/sbtdd/scripts/drift.py` (`_plan_all_tasks_complete` function)
- Modify: `tests/test_drift.py` (append C-1 to C-4 escenarios)

Covers escenarios C-1, C-2, C-3, C-4 from spec sec.4.

#### Red Phase

- [ ] **Step 1: Append failing tests**

Append to `tests/test_drift.py`:

```python
def test_c1_inline_backtick_prose_not_false_positive(tmp_path):
    """C-1: inline backtick prose mention NOT counted as open checkbox."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    from drift import _plan_all_tasks_complete

    plan_text = (
        "# Plan\n\n"
        "### Task 1: example\n\n"
        "- [x] Step 1: done\n"
        "- [x] Step 2: done\n\n"
        "Note: the syntax `- [ ]` represents an open checkbox.\n"
        "Subagents must use `- [x]` form when closing tasks.\n"
    )

    result = _plan_all_tasks_complete(plan_text)
    assert result == "[x]", (
        "Inline backtick prose mentions of `- [ ]` should NOT be counted as open checkboxes"
    )


def test_c2_real_open_checkbox_detected(tmp_path):
    """C-2: real line-anchored - [ ] checkbox correctly detected as drift."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    from drift import _plan_all_tasks_complete

    plan_text = (
        "# Plan\n\n"
        "### Task 1: example\n\n"
        "- [x] Step 1: done\n"
        "- [ ] Step 2: not done\n"
    )

    result = _plan_all_tasks_complete(plan_text)
    assert result == "[ ]", "Real line-anchored - [ ] checkbox should be detected"


def test_c3_mixed_real_and_prose(tmp_path):
    """C-3: mix of real checkboxes + prose backtick mentions in multi-task plan."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    from drift import _plan_all_tasks_complete

    plan_text_all_done = (
        "# Plan\n\n"
        "Note: standard syntax is `- [ ]` for open and `- [x]` for closed.\n\n"
        "### Task 1: alpha\n\n"
        "- [x] Step 1: done\n\n"
        "### Task 2: beta\n\n"
        "- [x] Step 1: done\n"
        "Reference to `- [ ]` form in prose, not actual checkbox.\n"
    )
    assert _plan_all_tasks_complete(plan_text_all_done) == "[x]"

    plan_text_one_open = (
        "# Plan\n\n"
        "Note: `- [ ]` in prose.\n\n"
        "### Task 1: alpha\n\n"
        "- [x] Step 1: done\n\n"
        "### Task 2: beta\n\n"
        "- [ ] Step 1: open!\n"
    )
    assert _plan_all_tasks_complete(plan_text_one_open) == "[ ]"


def test_c4_backward_compat_existing_fixtures(tmp_path):
    """C-4: existing real-checkbox fixtures continue working post-refactor."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    from drift import _plan_all_tasks_complete

    # Standard fixture pattern from existing test_drift.py
    plan_text_complete = (
        "### Task 1: ex\n\n"
        "- [x] Step 1\n"
        "- [x] Step 2\n"
    )
    assert _plan_all_tasks_complete(plan_text_complete) == "[x]"

    plan_text_incomplete = (
        "### Task 1: ex\n\n"
        "- [x] Step 1\n"
        "- [ ] Step 2\n"
    )
    assert _plan_all_tasks_complete(plan_text_incomplete) == "[ ]"
```

- [ ] **Step 2: Run tests to verify Red signal**

```bash
python -m pytest tests/test_drift.py::test_c1_inline_backtick_prose_not_false_positive -v
```

Expected pre-fix: FAIL because current substring-match detects backtick prose. Specifically, `"- [ ]" in plan_text[start:end]` returns True for the prose mention.

- [ ] **Step 3: Verify + commit Red**

```bash
python -m ruff check tests/test_drift.py
python -m ruff format --check tests/test_drift.py
python -m mypy tests/test_drift.py
git add tests/test_drift.py
git commit -m "test: C-1..C-4 drift detector line-anchored regression"
```

#### Green Phase

- [ ] **Step 4: Apply line-anchored regex fix**

Modify `skills/sbtdd/scripts/drift.py`. Locate `_plan_all_tasks_complete` function (~line 242 per v1.0.2 inspection). Replace substring match with regex:

```python
import re

# Add at module level near other regex constants:
_OPEN_CHECKBOX_RE = re.compile(r"^- \[ \]", re.MULTILINE)


def _plan_all_tasks_complete(plan_text: str) -> str:
    """Return ``"[x]"`` iff every ``### Task <id>:`` section is fully flipped.

    Uses line-anchored regex (re.MULTILINE) to match ``- [ ]`` checkboxes
    only at line start, avoiding false-positives from inline backtick
    prose mentions of the literal `- [ ]` string in documentation.

    v1.0.3 Item C fix: previously used substring ``"- [ ]" in plan_text[start:end]``
    which matched inline prose like ``Note: use `- [ ]` for open`` as
    a real open checkbox, triggering DriftError when plan was actually
    fully complete. v1.0.2 ship hit this with 2 such prose mentions.
    """
    headers = list(_ANY_TASK_HEADER.finditer(plan_text))
    if not headers:
        return "[x]"
    for i, match in enumerate(headers):
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(plan_text)
        section = plan_text[start:end]
        if _OPEN_CHECKBOX_RE.search(section):
            return "[ ]"
    return "[x]"
```

- [ ] **Step 5: Run tests to verify pass**

```bash
python -m pytest tests/test_drift.py -v
```

Expected: ALL drift tests pass (existing + new C-1..C-4). Backward compat preserved.

- [ ] **Step 6: Verify + commit Green phase**

```bash
make verify
git add skills/sbtdd/scripts/drift.py
git commit -m "fix: drift detector line-anchored - [ ] regex (Item C)"
```

#### Refactor + Task close

- [ ] **Step 7-8: Refactor optional (skip if regex shape clean)**
- [ ] **Step 9: Close task via automation**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

State file advances to `current_task_id="4"` (Item D), `current_phase="red"`.

---

### Task 4: Item D — Spec-snapshot auto-regeneration

**Files:**
- Modify: `skills/sbtdd/scripts/spec_cmd.py` (`_run_magi_checkpoint2` post-MAGI-pass branch)
- Modify: `skills/sbtdd/scripts/state_file.py` (if `spec_snapshot_emitted_at` field needs handling — check existing schema)
- Modify: `tests/test_spec_cmd.py` (append D-1 to D-4 escenarios)
- Read-only: `skills/sbtdd/scripts/spec_snapshot.py` (existing `emit_snapshot` + `persist_snapshot`)

Covers escenarios D-1, D-2, D-3, D-4 from spec sec.4.

#### Red Phase

- [ ] **Step 1: Investigate existing emit pattern**

Read `skills/sbtdd/scripts/spec_cmd.py` to locate `_run_magi_checkpoint2` post-MAGI-pass branch + existing `_mark_plan_approved_with_snapshot` helper (R10 v1.0.0 fix). Determine if autoregen is partially shipped or fully missing. If partially shipped (e.g., `_mark_plan_approved_with_snapshot` exists and is called from `--resume-from-magi` path), this task tightens vs adds.

Read `skills/sbtdd/scripts/state_file.py` to verify `SessionState` dataclass has `spec_snapshot_emitted_at` field. If missing, add it.

- [ ] **Step 2: Write failing tests**

Append to `tests/test_spec_cmd.py`:

```python
def test_d1_d2_post_magi_pass_autoregen(tmp_path, monkeypatch):
    """D-1 + D-2: after MAGI pass, snapshot regenerated + state file timestamp."""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    import spec_cmd
    import spec_snapshot
    from state_file import SessionState

    root = tmp_path
    (root / "sbtdd").mkdir()
    (root / "planning").mkdir()
    (root / ".claude").mkdir()

    spec = root / "sbtdd" / "spec-behavior.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. Section\n\n"
        "**Escenario X-1: example**\n\n"
        "> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )
    plan = root / "planning" / "claude-plan-tdd-org.md"
    plan.write_text(
        "# Plan\n> Generado 2026-05-06 a partir de y.md\n\n## 1. T\n",
        encoding="utf-8",
    )
    plan_final = root / "planning" / "claude-plan-tdd.md"
    plan_final.write_text(plan.read_text(encoding="utf-8"), encoding="utf-8")

    # Pre-existing snapshot from prior cycle (with stale escenarios)
    snapshot_path = root / "planning" / "spec-snapshot.json"
    snapshot_path.write_text(json.dumps({"OLD-1: stale": "deadbeef"}), encoding="utf-8")

    invoke_called = []
    def fake_invoke(*a, **kw):
        invoke_called.append(True)
        return {"verdict": "GO", "iterations": [], "degraded": False}
    monkeypatch.setattr("magi_dispatch.invoke_magi", fake_invoke)
    monkeypatch.setattr(spec_cmd, "_create_state_file", lambda *a, **kw: None)
    monkeypatch.setattr(spec_cmd, "_commit_approved_artifacts", lambda *a, **kw: None)

    cfg = type("Cfg", (), {"magi_max_iterations": 3, "magi_threshold": "GO_WITH_CAVEATS"})()
    ns = type("NS", (), {"override_checkpoint": False, "reason": None,
                          "resume_from_magi": False})()
    spec_cmd._run_magi_checkpoint2(root, cfg, ns)

    # D-1: snapshot regenerated with current escenarios (X-1, not OLD-1)
    new_snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert "OLD-1: stale" not in new_snapshot, "Stale escenario should be removed"
    assert any("X-1" in title for title in new_snapshot.keys()), (
        "Current spec X-1 escenario should be in regenerated snapshot"
    )


def test_d3_resume_from_magi_idempotent(tmp_path, monkeypatch):
    """D-3: --resume-from-magi autoregen idempotent (same content -> same hashes)."""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    import spec_cmd

    root = tmp_path
    (root / "sbtdd").mkdir()
    (root / "planning").mkdir()
    (root / ".claude").mkdir()
    spec = root / "sbtdd" / "spec-behavior.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. Section\n\n"
        "**Escenario Y-1: stable**\n\n"
        "> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )
    plan = root / "planning" / "claude-plan-tdd-org.md"
    plan.write_text(
        "# Plan\n> Generado 2026-05-06 a partir de y.md\n\n## 1. T\n",
        encoding="utf-8",
    )
    plan_final = root / "planning" / "claude-plan-tdd.md"
    plan_final.write_text(plan.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr("magi_dispatch.invoke_magi",
                        lambda *a, **kw: {"verdict": "GO", "iterations": [], "degraded": False})
    monkeypatch.setattr(spec_cmd, "_create_state_file", lambda *a, **kw: None)
    monkeypatch.setattr(spec_cmd, "_commit_approved_artifacts", lambda *a, **kw: None)

    cfg = type("Cfg", (), {"magi_max_iterations": 3, "magi_threshold": "GO_WITH_CAVEATS"})()
    ns = type("NS", (), {"override_checkpoint": False, "reason": None,
                          "resume_from_magi": True})()

    # First invocation
    spec_cmd._run_magi_checkpoint2(root, cfg, ns)
    snapshot_after_first = (root / "planning" / "spec-snapshot.json").read_text(encoding="utf-8")

    # Second invocation (idempotent)
    spec_cmd._run_magi_checkpoint2(root, cfg, ns)
    snapshot_after_second = (root / "planning" / "spec-snapshot.json").read_text(encoding="utf-8")

    assert snapshot_after_first == snapshot_after_second, (
        "Idempotent autoregen: same spec content should yield same snapshot"
    )


def test_d4_backward_compat_normal_flow(tmp_path, monkeypatch):
    """D-4: plain /sbtdd spec (NOT --resume-from-magi) gets same autoregen behavior."""
    import json
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "sbtdd" / "scripts"))
    import spec_cmd

    root = tmp_path
    (root / "sbtdd").mkdir()
    (root / "planning").mkdir()
    (root / ".claude").mkdir()
    spec = root / "sbtdd" / "spec-behavior.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. Section\n\n"
        "**Escenario Z-1: normal**\n\n"
        "> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )
    plan = root / "planning" / "claude-plan-tdd-org.md"
    plan.write_text(
        "# Plan\n> Generado 2026-05-06 a partir de y.md\n\n## 1. T\n",
        encoding="utf-8",
    )
    plan_final = root / "planning" / "claude-plan-tdd.md"
    plan_final.write_text(plan.read_text(encoding="utf-8"), encoding="utf-8")

    monkeypatch.setattr("magi_dispatch.invoke_magi",
                        lambda *a, **kw: {"verdict": "GO", "iterations": [], "degraded": False})
    monkeypatch.setattr(spec_cmd, "_create_state_file", lambda *a, **kw: None)
    monkeypatch.setattr(spec_cmd, "_commit_approved_artifacts", lambda *a, **kw: None)

    cfg = type("Cfg", (), {"magi_max_iterations": 3, "magi_threshold": "GO_WITH_CAVEATS"})()
    # resume_from_magi=False (normal flow)
    ns = type("NS", (), {"override_checkpoint": False, "reason": None,
                          "resume_from_magi": False})()
    spec_cmd._run_magi_checkpoint2(root, cfg, ns)

    snapshot_path = root / "planning" / "spec-snapshot.json"
    assert snapshot_path.exists(), "Normal flow should also emit snapshot"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert any("Z-1" in title for title in snapshot.keys())
```

- [ ] **Step 3: Verify + commit Red**

```bash
python -m pytest tests/test_spec_cmd.py::test_d1_d2_post_magi_pass_autoregen tests/test_spec_cmd.py::test_d3_resume_from_magi_idempotent tests/test_spec_cmd.py::test_d4_backward_compat_normal_flow -v
```

Expected: Red signal varies. If autoregen partially shipped via `_mark_plan_approved_with_snapshot`, some tests may PASS already. Document which tests fail vs pass — those that fail represent the gap to fill.

```bash
python -m ruff check tests/test_spec_cmd.py
python -m ruff format --check tests/test_spec_cmd.py
python -m mypy tests/test_spec_cmd.py
git add tests/test_spec_cmd.py
git commit -m "test: D-1..D-4 spec-snapshot autoregen tripwires"
```

#### Green Phase

- [ ] **Step 4: Implement autoregen in `_run_magi_checkpoint2`**

In `skills/sbtdd/scripts/spec_cmd.py`, locate `_run_magi_checkpoint2`. After MAGI verdict converges to `>= GO_WITH_CAVEATS` full no-degraded (post-iter-loop branch, BEFORE `_create_state_file` and `_commit_approved_artifacts`), insert:

```python
    # v1.0.3 Item D: spec-snapshot auto-regeneration (post-MAGI-pass)
    import spec_snapshot
    snapshot = spec_snapshot.emit_snapshot(spec_path)
    spec_snapshot.persist_snapshot(snapshot, root / "planning" / "spec-snapshot.json")
    # state_file.spec_snapshot_emitted_at update happens via existing
    # _mark_plan_approved_with_snapshot pattern OR via _create_state_file
    # depending on flow. The autoregen here ensures the JSON file is
    # current; state file timestamp is updated downstream.
```

Verify integration with existing `_mark_plan_approved_with_snapshot` helper (R10 v1.0.0 fix). If existing helper already covers this for one path (e.g., normal `/sbtdd spec`), ensure `--resume-from-magi` path ALSO triggers via consistent code.

If `state_file.py` lacks `spec_snapshot_emitted_at` field, add it (defaulting to None for backward compat).

- [ ] **Step 5: Run tests pass**

```bash
python -m pytest tests/test_spec_cmd.py -v -k "test_d1 or test_d2 or test_d3 or test_d4"
```

Expected: 4 PASS.

- [ ] **Step 6: Verify + commit Green phase**

```bash
make verify
git add skills/sbtdd/scripts/spec_cmd.py
# Possibly state_file.py if field added:
# git add skills/sbtdd/scripts/state_file.py
git commit -m "feat: spec-snapshot autoregen in _run_magi_checkpoint2 (Item D)"
```

#### Refactor + Task close

- [ ] **Step 7-8: Refactor optional (skip if cohesive)**
- [ ] **Step 9: Close task via automation**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

State file advances to `current_task_id="5"` (Item E), `current_phase="red"`.

---

### Task 5: Item E — Close-task convention codification (doc-only)

**Files:**
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add close-task automation requirement)
- Modify: `templates/CLAUDE.local.md.template` (template guidance for destination projects)
- Create: `tests/test_close_task_subagent_pattern.py` (smoke test asserting docs reference close-task)

Covers escenarios E-1, E-2 from spec sec.4.

#### Red Phase

- [ ] **Step 1: Write failing smoke test**

Create `tests/test_close_task_subagent_pattern.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Smoke tests for v1.0.3 Item E close-task convention codification.

Asserts orchestrator skill + template files reference /sbtdd close-task
automation per Q2 Option B brainstorming decision. Doc-only enforcement
of the convention; underlying close-task command tested in
tests/test_close_task_cmd.py.

Covers escenarios E-1 (command behavior — re-asserts via existing
close_task_cmd tests) + E-2 (docs reference).
"""

from __future__ import annotations

from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_e2_skill_md_references_close_task():
    """E-2: skills/sbtdd/SKILL.md mentions close-task automation requirement."""
    skill_md = _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
    assert skill_md.exists()
    text = skill_md.read_text(encoding="utf-8")
    assert "close-task" in text, (
        "SKILL.md must reference /sbtdd close-task convention (v1.0.3 Item E Q2 Option B)"
    )
    assert "NON-CONFORMING" in text or "non-conforming" in text.lower(), (
        "SKILL.md must explicitly mark manual checkbox edits as non-conforming"
    )


def test_e2_template_claude_local_references_close_task():
    """E-2: templates/CLAUDE.local.md.template mentions close-task command."""
    template = _REPO_ROOT / "templates" / "CLAUDE.local.md.template"
    assert template.exists()
    text = template.read_text(encoding="utf-8")
    assert "close-task" in text, (
        "templates/CLAUDE.local.md.template must reference /sbtdd close-task convention"
    )


def test_e1_close_task_command_is_runnable():
    """E-1 prerequisite: close-task subcommand exists and accepts --skip-spec-review."""
    import subprocess
    result = subprocess.run(
        ["python", "skills/sbtdd/scripts/run_sbtdd.py", "close-task", "--help"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, f"close-task --help failed: {result.stderr}"
    assert "--skip-spec-review" in result.stdout, (
        "close-task command must accept --skip-spec-review escape valve"
    )
```

- [ ] **Step 2: Run tests to verify Red**

```bash
python -m pytest tests/test_close_task_subagent_pattern.py -v
```

Expected: `test_e2_skill_md_references_close_task` FAIL (SKILL.md doesn't yet mention close-task convention). `test_e2_template_claude_local_references_close_task` FAIL similarly. `test_e1_close_task_command_is_runnable` PASS (command exists v0.1+).

- [ ] **Step 3: Verify + commit Red**

```bash
python -m ruff check tests/test_close_task_subagent_pattern.py
python -m ruff format --check tests/test_close_task_subagent_pattern.py
python -m mypy tests/test_close_task_subagent_pattern.py
git add tests/test_close_task_subagent_pattern.py
git commit -m "test: E-1/E-2 close-task convention codification tripwires"
```

#### Green Phase

- [ ] **Step 4: Update `skills/sbtdd/SKILL.md` orchestrator rules**

Append a new section to `skills/sbtdd/SKILL.md`:

```markdown

### v1.0.3 Item E: Close-task automation convention (Q2 Option B)

**Mandate**: subagents MUST close each plan task via the
`/sbtdd close-task` automation command after Refactor phase
verify-clean. Manual plan-file edits to flip `- [ ]` → `- [x]`
checkboxes are **NON-CONFORMING** and trigger drift detection.

Invocation pattern (subagent appends as final task close step):

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

The `--skip-spec-review` flag bypasses INV-31 spec-reviewer dispatch
(~1-2 min/task overhead). Use it for defensive infrastructure work
where INV-31 enforcement is not the cycle's primary concern.

What `/sbtdd close-task` does atomically:
1. Flip ALL `- [ ]` → `- [x]` in active task section.
2. Atomic `chore: mark task {id} complete` commit (plan diff only).
3. Advance `session-state.json` to next open task (fresh red phase)
   OR mark plan `done` if last task.
4. Honors INV-3 (plan checkboxes monotonic) + INV-12 (precondition
   validation).

Rationale: v1.0.2 ship empirically demonstrated that documentation
alone (I5 Process notes in plan) doesn't enforce the per-step
checkbox convention; subagents diverged to heading-mark pattern.
Codifying via existing automation eliminates the divergence vector.
```

- [ ] **Step 5: Update `templates/CLAUDE.local.md.template`**

Append to `templates/CLAUDE.local.md.template` (in the section about TDD discipline / per-task closing, or appropriate location):

```markdown

### Cierre de tarea (subagent convention v1.0.3)

Subagents MUST close each plan task via the automation command after
Refactor phase verify-clean:

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

Manual plan-file edits to flip `[ ]` → `[x]` checkboxes are
**NON-CONFORMING** and trigger drift detection per the v1.0.2 ship
process notes. The close-task command flips ALL step checkboxes in
the active task section atomically + creates the chore commit +
advances state file.

The `--skip-spec-review` flag is the recommended default for
defensive infrastructure cycles; for feature work where INV-31
spec-reviewer dispatch is desired, omit the flag.
```

- [ ] **Step 6: Run tests to verify pass**

```bash
python -m pytest tests/test_close_task_subagent_pattern.py -v
```

Expected: 3 PASS.

- [ ] **Step 7: Verify + commit Green**

```bash
make verify
git add skills/sbtdd/SKILL.md templates/CLAUDE.local.md.template
git commit -m "docs: codify close-task convention via automation (Item E Q2 Option B)"
```

#### Refactor + Task close

- [ ] **Step 8-9: Refactor optional (doc-only; skip if clean)**
- [ ] **Step 10: Close task via automation (this is the final Track Beta task!)**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

State file advances to `current_task_id=null, current_task_title=null, current_phase="done"` (plan complete; all 5 tasks closed). This unlocks finalization flow per spec sec.7.

---

## Methodology Activities (Orchestrator, post-tracks pre-pre-merge)

These are NOT plan tasks (no Red-Green-Refactor commits). They are orchestrator-driven activities documented in CHANGELOG `[1.0.3]` Process notes.

### Activity D' — Linux/POSIX dogfood completion (~30-45min)

Triggered AFTER Track Alpha + Track Beta close (state file `current_phase: "done"`):

1. Verify `magi_cross_check: true` in `.claude/plugin.local.md` (already enabled since v1.0.0 Loop 2 iter 3 dogfood per `project_v100_shipped.md`).

2. Verify Item B Windows fix landed (commits from Task 2 present in git log).

3. Run `/sbtdd pre-merge` end-to-end:

```bash
python skills/sbtdd/scripts/run_sbtdd.py pre-merge
```

4. Verify cross-check meta-reviewer ejecuta sin WinError 206:

```bash
ls .claude/magi-cross-check/iter*-*.json
```

If files exist + non-empty: cross-check ran successfully. If empty or absent: Item B fix incomplete on Windows runtime; document and defer to v1.0.4.

5. Run telemetry script (Item A v1.0.2 ship) on real artifacts:

```bash
python scripts/cross_check_telemetry.py --root .claude/magi-cross-check --format markdown > /tmp/v103-cross-check.md
cat /tmp/v103-cross-check.md
```

6. Document findings in CHANGELOG `[1.0.3]` Process notes:
   - Cross-check meta-reviewer succeeded vs failed (Item B fix validated).
   - Iter count Loop 2.
   - Cross-check decision distribution (KEEP / DOWNGRADE / REJECT counts).
   - Meta-reviewer agreement rate vs MAGI verdicts.
   - Observable gaps.

If Activity D' surfaces a production bug in cross-check path beyond Item B fix scope: document + defer to v1.0.4. Activity D' is non-blocking for ship.

### Activity E' — True `--resume-from-magi` smoke test (~15-30min)

Triggered AFTER Activity D' completes:

1. Verify spec-behavior.md + plan-tdd-org.md exist + are committed (true post Track-close).

2. Pre-flight spec_lint dry-run (W5 v1.0.1 fix):

```bash
PYTHONPATH=skills/sbtdd/scripts python -m spec_lint sbtdd/spec-behavior.md
PYTHONPATH=skills/sbtdd/scripts python -m spec_lint planning/claude-plan-tdd-org.md
```

Both must exit 0 (no R1-R5 errors). Warnings (R3 monotonic skip) acceptable.

3. Invoke `/sbtdd spec --resume-from-magi`:

```bash
python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi 2>&1 | tee /tmp/v103-activity-e-prime.log
```

4. Observe + document in CHANGELOG `[1.0.3]` Process notes:
   - Brainstorming/writing-plans subprocess NOT spawned (verifiable via process tree or stderr breadcrumb).
   - MAGI Checkpoint 2 dispatched on existing artifacts (or skipped if state already done).
   - Item D autoregen interaction observed: spec-snapshot regenerated idempotently OR conflict observable.
   - `_commit_approved_artifacts` interaction observed: artifacts already committed, behavior visible (no-op? amend? new commit?).
   - State file mutation observed: existing post-impl state vs new `_create_state_file` overwrite behavior.
   - Wall-clock end-to-end.
   - R10 commit-conflict observability.
   - R4 autoregen-interaction observability.

**Failure mode**: methodology activity is **non-gating for ship**. If E' fails (e.g., R10 commit conflict surfaces), document the specific failure mode + roll forward to v1.0.4 fix. Cycle continues to finalization regardless.

---

## Pre-merge gate sequencing

After Activities D' + E':

1. Loop 1: `/requesting-code-review` cap=10, expecting 1-2 iters (small bundle).
2. Loop 2: `/magi:magi` cap=5 with cross-check enabled. Activity D' validated cross-check infrastructure works (or documented failure).
3. G2 binding fallback: if Loop 2 iter 3 doesn't converge, scope-trim per spec sec.6.1 ladder (defer Pillar C Items C+D+E to v1.0.4; Pillar A audit + Pillar B Windows fix hard-LOCKED).

Pre-merge dispatch:

```bash
python skills/sbtdd/scripts/run_sbtdd.py pre-merge
```

If pre-merge auto-abandons per INV-11 + non-TTY default at safety valve exhaustion (v1.0.2 precedent), apply caveats per spec sec.6 + manually accept verdict if at-threshold.

## Finalization (Task 6 — orchestrator-only)

After pre-merge passes:

1. Bump `plugin.json` + `marketplace.json` to `1.0.3`.
2. Append final CHANGELOG `[1.0.3]` sections (Added / Changed / Process notes — Activity D' + E' empirical findings + template alignment GAP/MATCH stats / Deferred — v1.0.4 + v1.0.5+ items).
3. Commit `chore: bump to 1.0.3 + finalize CHANGELOG with full ship record`.
4. Create local tag `git tag v1.0.3 -m "v1.0.3: template alignment + v1.0.2 dogfood remediations"`.
5. Memory write: `~/.claude/projects/D--jbolivarg-PythonProjects-SBTDD/memory/project_v103_shipped.md` + MEMORY.md index update.
6. Request explicit user authorization for `git push origin main && git push origin v1.0.3` (per global rules + memory `feedback_never_commit_without_explicit_request`).
7. After user authorizes: checkout main, `git merge --no-ff feature/v1.0.3-bundle -m "Merge branch 'feature/v1.0.3-bundle' for v1.0.3 release"`, push.

---

## Self-Review

**Spec coverage:**

| Spec section | Plan task |
|--------------|-----------|
| 2.1 Item A | Task 1 |
| 2.2 Item B | Task 2 |
| 2.3 Item C | Task 3 |
| 2.4 Item D | Task 4 |
| 2.5 Item E | Task 5 |
| 2.6 Activity D' | Activity D' |
| 2.7 Activity E' | Activity E' |
| 4 Escenarios A-1..A-5 | Task 1 (3 tests assert; A-4 narrative; A-5 regression test) |
| 4 Escenarios B-1..B-5 | Task 2 (4 tests cover; B-1+B-2 in single test post-fix) |
| 4 Escenarios C-1..C-4 | Task 3 (4 tests) |
| 4 Escenarios D-1..D-4 | Task 4 (4 tests) |
| 4 Escenarios E-1..E-2 | Task 5 (3 tests) |

All 20 escenarios covered (modulo A-4 which is process narrative). All 5 plan items covered with TDD cycles. D' + E' covered with methodology activity steps.

**Placeholder scan:** No INV-27 uppercase placeholder tokens, no "implement later" / "add error handling" weasel words. The "(exact location pending Beta investigation)" in Task 2 Step 1 is intentional — subagent investigates as part of Step 1.

**Type consistency:**
- `_OPEN_CHECKBOX_RE` constant introduced in Task 3 referenced consistently.
- `spec_snapshot.emit_snapshot` + `persist_snapshot` signatures from existing v1.0.0 code (read-only consumed by Task 4).
- `SessionState` dataclass field `spec_snapshot_emitted_at` referenced in Task 4 (verify field exists OR add as Task 4 step).
- `/sbtdd close-task --skip-spec-review` invocation pattern consistent across all 5 tasks' close steps.

---

## Execution Handoff

Plan complete and saved to `planning/claude-plan-tdd-org.md`. Per the SBTDD methodology (CLAUDE.local.md §1 Flujo de especificacion), the next steps are:

1. **Manual review (Checkpoint 1)** of `planning/claude-plan-tdd-org.md` by the user.
2. **MAGI Checkpoint 2** evaluating spec + plan together (`/magi:magi` cap=3 G1 HARD) via Opcion A manual `run_magi.py` per hybrid methodology.
3. Iterate plan based on MAGI findings, rewriting refined version to `planning/claude-plan-tdd.md`.
4. Once verdict >= GO_WITH_CAVEATS full, dispatch Track Alpha + Track Beta as 2 parallel subagents per `superpowers:dispatching-parallel-agents` + `superpowers:subagent-driven-development`.

**Subagent-Driven is the project default** per memory `feedback_subagent_delegation.md`. Track Alpha (Item A audit-only, ~1 day) + Track Beta (Items B+C+D+E sequential, ~3 days) dispatched in parallel after MAGI Checkpoint 2 approval.
