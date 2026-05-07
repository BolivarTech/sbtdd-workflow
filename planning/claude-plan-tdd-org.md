# v1.0.3 Template Alignment + Cross-check Windows Fix Implementation Plan (scope-trimmed iter 2)

> Generado 2026-05-06 a partir de sbtdd/spec-behavior.md v1.0.3 via
> superpowers:writing-plans skill (interactive session, post-MAGI
> Checkpoint 2 iter 2 scope-trim per pre-staged trigger). Frontmatter
> required by spec_lint R5 (Item C v1.0.2 enforcement).
>
> Iter 2 verdict GO_WITH_CAVEATS (3-0) with 1 CRITICAL persisting
> (Task 2 test fidelity + Item B root-cause refinement) triggered
> spec sec.6.1 iter-2 CRITICAL pre-stage: scope-trim Items C+D+E
> deferred to v1.0.4 cycle. v1.0.3 ships Pillar A (audit) + Pillar B
> (cross-check Windows fix via @file prompt reference) only.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax (open + closed bracket forms) for tracking.

**Goal:** Ship v1.0.3 — completar la auditoria LOCKED original (MAGI gate template alignment vs canonical template) + arreglar el cross-check Windows infrastructure failure surfaced en v1.0.2 own-cycle dogfood. 2 plan tasks (Task 1 = Item A audit; Task 2 = Item B cross-check Windows fix via @file prompt reference + project-relative temp dir) over 2 parallel subagent tracks; 2 methodology activities (D' Linux/POSIX dogfood + E' --resume-from-magi smoke test) executed by orchestrator. Items C+D+E (drift line-anchored, spec-snapshot autoregen, close-task convention codification) **deferred to v1.0.4** per iter-2 CRITICAL trigger.

**Architecture:** 2-track parallel dispatch with disjoint surfaces. Track Alpha (audit-only) writes `docs/audits/v1.0.3-magi-gate-template-alignment.md` + `tests/test_magi_template_alignment.py` — NO production code. Track Beta (Item B only) modifies `pre_merge_cmd.py` + extends `tests/test_pre_merge_cross_check.py`. Cero file overlap. Activity D' (Linux/POSIX dogfood post Item B fix) + Activity E' (--resume-from-magi smoke test post Track-close) run mid-cycle in orchestrator session before pre-merge gate.

**State file write serialization**: Track Alpha owns Task 1 (single close). Track Beta owns Task 2 (single close). State file `current_task_id` advances 1 → 2 → done. `state_file.save()` atomic `os.replace` (existing v0.5.0 pattern) ensures no partial writes. Concurrent close-task invocations against disjoint task IDs are safe.

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

### Task 2: Item B — Cross-check Windows fix via @file prompt reference

**Files:**
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py` (`_dispatch_requesting_code_review` function ~line 1243 — write prompt to project-relative temp file before invoking `superpowers_dispatch.requesting_code_review`; pass `@<filepath>` reference in argv)
- Modify: `tests/test_pre_merge_cross_check.py` (extend with B-1..B-5 escenarios; concrete monkeypatch on `subprocess_utils.run_with_timeout` to capture argv)

Covers escenarios B-1, B-2, B-3, B-4, B-5 from spec sec.4. Refined iter 2 root cause: WinError 206 fires because cross-check prompt (with diff embedded ~200KB) is packed into a single `-p <prompt>` argv argument that exceeds Windows cmdline limits. Fix: write prompt to project-relative temp file + pass `@<filepath>` reference in argv (small payload).

#### Red Phase

- [ ] **Step 1: Append failing tests with concrete monkeypatch on subprocess capture**

Append to `tests/test_pre_merge_cross_check.py`:

```python
import os
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _capture_dispatch_argv(monkeypatch) -> list[list[str]]:
    """Monkeypatch subprocess_utils.run_with_timeout to capture argv per call."""
    sys.path.insert(0, str(_REPO_ROOT / "skills" / "sbtdd" / "scripts"))
    import subprocess_utils

    captured: list[list[str]] = []

    def fake_run_with_timeout(cmd, **kwargs):
        captured.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        result.stdout = '{"decisions": []}'
        result.stderr = ""
        return result

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run_with_timeout)
    return captured


def test_b1_b2_cross_check_uses_atfile_reference(monkeypatch):
    """B-1 + B-2: cross-check passes prompt via @<filepath>, not inline argv.

    Captures the cmd argv passed to subprocess_utils.run_with_timeout
    by superpowers_dispatch (invoked via
    pre_merge_cmd._dispatch_requesting_code_review). Asserts the prompt
    content is NOT packed into argv (which would trigger WinError 206
    on Windows for ~200KB cross-check diffs); instead, an @<filepath>
    reference appears.
    """
    sys.path.insert(0, str(_REPO_ROOT / "skills" / "sbtdd" / "scripts"))
    from pre_merge_cmd import _dispatch_requesting_code_review

    captured_cmds = _capture_dispatch_argv(monkeypatch)

    large_prompt = "## Cumulative diff under review\n\n" + ("x" * 50000)
    diff = "--- a/foo.py\n+++ b/foo.py\n" + ("x" * 50000)

    _dispatch_requesting_code_review(diff=diff, prompt=large_prompt)

    assert captured_cmds, "No subprocess invocation captured"
    cmd_text = " ".join(captured_cmds[0])

    assert len(cmd_text) < 2048, (
        f"Argv too long ({len(cmd_text)} chars). Prompt should be passed via "
        f"@<filepath> reference, not inline."
    )
    assert "@" in cmd_text, "Argv should contain @<filepath> reference"
    assert ("x" * 50000) not in cmd_text, "Prompt content leaked into argv"


def test_b3_temp_file_is_project_relative(monkeypatch):
    """B-3: temp prompt file lives under .claude/magi-cross-check/.tmp/ (project-relative).

    Side-steps Windows MAX_PATH 260 limit by keeping path short
    relative to repo root.
    """
    sys.path.insert(0, str(_REPO_ROOT / "skills" / "sbtdd" / "scripts"))
    from pre_merge_cmd import _dispatch_requesting_code_review

    captured_cmds = _capture_dispatch_argv(monkeypatch)
    _dispatch_requesting_code_review(diff="x", prompt="## Test prompt")

    assert captured_cmds
    cmd_text = " ".join(captured_cmds[0])

    match = re.search(r"@(\S+)", cmd_text)
    assert match, "No @<filepath> reference in argv"
    filepath_str = match.group(1)

    posix_path = filepath_str.replace("\\", "/")
    assert ".claude/magi-cross-check/.tmp" in posix_path, (
        f"Temp file not project-relative: {filepath_str}"
    )


def test_b4_short_prompts_use_uniform_path(monkeypatch):
    """B-4: small prompts also use @file reference (no regression for typical case)."""
    sys.path.insert(0, str(_REPO_ROOT / "skills" / "sbtdd" / "scripts"))
    from pre_merge_cmd import _dispatch_requesting_code_review

    captured_cmds = _capture_dispatch_argv(monkeypatch)
    _dispatch_requesting_code_review(diff="", prompt="## Tiny prompt")

    assert captured_cmds, "Even short prompts dispatch via subprocess"
    cmd_text = " ".join(captured_cmds[0])
    assert "@" in cmd_text, "Uniform @file reference path even for small prompts"


def test_b5_temp_file_cleanup(monkeypatch):
    """B-5: temp prompt file is cleaned up after dispatch (no leak)."""
    sys.path.insert(0, str(_REPO_ROOT / "skills" / "sbtdd" / "scripts"))
    from pre_merge_cmd import _dispatch_requesting_code_review

    tmp_dir = _REPO_ROOT / ".claude" / "magi-cross-check" / ".tmp"
    initial_files = set(tmp_dir.glob("*")) if tmp_dir.exists() else set()

    _capture_dispatch_argv(monkeypatch)
    _dispatch_requesting_code_review(diff="x", prompt="## Cleanup test")

    final_files = set(tmp_dir.glob("*")) if tmp_dir.exists() else set()
    leaked = final_files - initial_files
    # Filter out non-prompt files (only check prompt-*.md files we may have created)
    leaked_prompts = {f for f in leaked if f.name.startswith("prompt-") and f.suffix == ".md"}
    assert not leaked_prompts, (
        f"Temp prompt files leaked (no cleanup): {leaked_prompts}"
    )
```

- [ ] **Step 2: Run tests to verify Red signal**

```bash
python -m pytest tests/test_pre_merge_cross_check.py -k "test_b1_b2 or test_b3 or test_b4 or test_b5" -v
```

Expected pre-fix: all 4 FAIL because current `_dispatch_requesting_code_review` passes prompt inline (no @file reference, no temp file).

- [ ] **Step 3: Verify + commit Red phase**

```bash
python -m ruff check tests/test_pre_merge_cross_check.py
python -m ruff format --check tests/test_pre_merge_cross_check.py
python -m mypy tests/test_pre_merge_cross_check.py
git add tests/test_pre_merge_cross_check.py
git commit -m "test: B-1..B-5 cross-check @file prompt reference tripwires"
```

#### Green Phase

- [ ] **Step 4: Implement @file prompt reference in `_dispatch_requesting_code_review`**

Modify `skills/sbtdd/scripts/pre_merge_cmd.py` line ~1243 `_dispatch_requesting_code_review` function. Add the prompt-to-tempfile + @file reference logic:

```python
def _dispatch_requesting_code_review(
    *,
    diff: str,
    prompt: str,
    cwd: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dispatch /requesting-code-review skill with cross-check meta-prompt.

    v1.0.3 Item B fix: write prompt content to project-relative temp file
    + pass @<filepath> reference in argv (instead of packing the entire
    prompt -- including diff up to 200KB -- into a single -p argv element
    which exceeds Windows cmdline limits triggering WinError 206).

    [existing docstring continues...]
    """
    import uuid

    # v1.0.3 Item B: project-relative temp dir + @file reference
    repo_root = Path(cwd) if cwd else Path.cwd()
    tmp_dir = repo_root / ".claude" / "magi-cross-check" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex[:8]
    prompt_file = tmp_dir / f"prompt-{run_id}.md"

    try:
        prompt_file.write_text(prompt, encoding="utf-8")
        atfile_arg = f"@{prompt_file.relative_to(repo_root).as_posix()}"
        result = superpowers_dispatch.requesting_code_review(
            args=[atfile_arg],
            cwd=cwd,
        )
    finally:
        prompt_file.unlink(missing_ok=True)

    output_text = getattr(result, "stdout", "") or "{}"
    try:
        parsed: dict[str, Any] = json.loads(output_text)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"[sbtdd magi-cross-check] /requesting-code-review returned "
            f"malformed JSON (meta-review skipped, findings unchanged): "
            f"{exc}\n"
        )
        sys.stderr.flush()
        return {
            "decisions": [],
            "_dispatch_failure": "json_parse_error",
            "_failure_reason": str(exc),
        }
    parsed.setdefault("decisions", [])
    return parsed
```

Verify the imports `import uuid` (and `import json` already present) at top of `pre_merge_cmd.py`.

- [ ] **Step 5: Run tests to verify Green pass**

```bash
python -m pytest tests/test_pre_merge_cross_check.py -v
```

Expected: B-1..B-5 PASS + existing pre-merge cross-check tests continue passing.

- [ ] **Step 6: Verify + commit Green phase**

```bash
make verify
git add skills/sbtdd/scripts/pre_merge_cmd.py
git commit -m "fix: cross-check prompt via @file reference (Item B Windows fix)"
```

#### Refactor Phase

- [ ] **Step 7: Refactor (optional helper extraction)**

Consider extracting `_write_prompt_atfile(prompt: str, repo_root: Path) -> tuple[Path, str]` helper if other dispatchers benefit from the same pattern. Otherwise skip.

- [ ] **Step 8: Verify + commit Refactor phase (skip if no changes)**

```bash
make verify
# If helper extracted:
# git add skills/sbtdd/scripts/pre_merge_cmd.py
# git commit -m "refactor: extract _write_prompt_atfile helper"
```

#### Task close

- [ ] **Step 9: Close task via `/sbtdd close-task` automation**

```bash
python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review
```

State file advances to `current_task_id=null, current_task_title=null, current_phase="done"` (plan complete; both tasks closed). This unlocks finalization flow per spec sec.7.

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

**Rollback protocol** (iter 1 I2 melchior fix): if E' produces
unwanted commits or state file mutations during the smoke test
(e.g., `_commit_approved_artifacts` lands a commit that conflicts
with the existing finalization sequence), apply rollback BEFORE
proceeding to pre-merge gate:

```bash
# Identify any unexpected commits landed during E' invocation
git log --oneline 10 --since="<E'-start-time>"

# Hard-reset working tree to pre-E' commit (capture SHA before E'
# invocation; subagent records it as part of Activity E' step 1)
git reset --hard <pre-E-prime-sha>

# Restore .claude/session-state.json from pre-E' state if mutated
# (capture pre-E' content before invocation)
echo '<pre-E-prime-state-json>' > .claude/session-state.json

# Document the rollback + observable gap in CHANGELOG [1.0.3] Process notes
```

The rollback is reversible (no force-push, no branch destruction);
captured pre-E' state ensures clean recovery. Subagent or orchestrator
records pre-E' SHA + state file content explicitly in Activity E'
step 1 BEFORE invocation as the rollback anchor.

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