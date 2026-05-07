# BDD overlay — sbtdd-workflow v1.0.3

> Generado 2026-05-06 a partir de `sbtdd/spec-behavior-base.md` v1.0.3.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1 + v1.0.2 precedent
> (Finding A subprocess pattern preserved hasta v1.0.4 real headless
> detection).
>
> v1.0.3 ships los items LOCKED del original sole-pillar (template
> alignment audit per memory `project_v103_template_alignment_audit.md`)
> mas v1.0.2 carry-forward fixes (cross-check Windows long-filename,
> drift detector tightening, spec-snapshot autoregen, subagent
> close-task convention) mas methodology activities pendientes
> (Activity D Linux/POSIX dogfood + Activity E true `--resume-from-magi`
> end-to-end como smoke test post-Track-close per hybrid methodology).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex (los tres tokens
> uppercase enforced en spec-base + extension a este artifact via
> Item C R4 v1.0.2 ship).

---

## 1. Resumen ejecutivo

**Objetivo v1.0.3 (revised iter 2 — scope-trimmed per pre-staged
iter-2 CRITICAL trigger)**: completa la auditoria LOCKED original
(MAGI gate template alignment vs `magi-gate-template.md`) + arregla
el cross-check Windows infrastructure failure surfaced en v1.0.2
own-cycle dogfood. Items C (drift line-anchored), D (spec-snapshot
autoregen), E (close-task convention codification) **deferred to
v1.0.4** per spec sec.6.1 iter-2 CRITICAL trigger pre-stage:
Checkpoint 2 iter 2 still surfaced 1 CRITICAL (Task 2 test fidelity
+ refined Item B root-cause analysis), forcing immediate scope-trim
rather than burning iter 3 on a multi-pillar bundle.

**Refined Item B root-cause (iter 2)**: WinError 206 fires because
`superpowers_dispatch._build_skill_cmd` packs the cross-check prompt
(including diff truncated to 200KB) into a single `-p <prompt>`
argv argument. On Windows, total cmdline length triggers
ERROR_FILENAME_EXCEEDS_RANGE (WinError 206). Fix: pass large prompts
via `@<filepath>` reference in argv (small) with content written to
project-relative temp file (`.claude/magi-cross-check/.tmp/prompt-<run-id>.md`).
Combined with project-relative temp dir per R2 ladder step 3,
addresses both possible failure modes (argv length AND MAX_PATH).

Tres clases de work units (scope-trimmed iter 2):

- **Plan tasks bona-fide (2 items)**: A, B — TDD-cycle tasks. Items
  C+D+E **deferred to v1.0.4 per iter-2 CRITICAL trigger** (spec
  sec.6.1 pre-stage; orig brainstorming Q1 partition collapses to
  Track Alpha = A only / Track Beta = B only).
- **Methodology activities (2 items)**: D' (Linux/POSIX dogfood
  completion post Item B fix), E' (true `--resume-from-magi`
  end-to-end smoke test post Track-close per hybrid methodology).
- **Process notes (CHANGELOG)**: documentation de findings empiricos
  de D' + E' + iter-2 trigger ship rationale.

**Deferred to v1.0.4** (sections 2.3, 2.4, 2.5 below preserved for
v1.0.4 cycle reference; Items C, D, E descriptions remain valid as
backlog entries):
- Item C: drift detector line-anchored regex (false-positive on
  inline backtick prose mentions of `- [ ]`).
- Item D: spec-snapshot auto-regeneration in
  `_run_magi_checkpoint2` post-MAGI-pass branch.
- Item E: close-task convention codification (Q2 Option B —
  `/sbtdd close-task` automation enforcement via
  `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template`).

Decisiones de brainstorming 2026-05-06:

- **Q1 — Subagent partition**: Option 2 — 2-track parallel.
  - Track Alpha (subagent #1, single-purpose audit): Item A SOLO.
    Output = audit doc + alignment test. NO production code.
    ~1 dia wall-time.
  - Track Beta (subagent #2, sequential B → C → D → E): all code
    fixes + doc updates. ~3 dias wall-time.
  - Cero file overlap verificado: Alpha solo escribe
    `docs/audits/...` + `tests/test_magi_template_alignment.py`;
    Beta touches `pre_merge_cmd.py`, `drift.py`, `spec_cmd.py`,
    `spec_snapshot.py`, `state_file.py`, doc files.
- **Q2 — Item E close-task convention**: Option B — codify via
  `/sbtdd close-task` automation. v1.0.2 empirically proved
  documentation alone (I5 process notes) doesn't enforce convention
  (subagents diverged). `/sbtdd close-task` already shipped v0.1+;
  forces structural consistency (per-step checkbox flip + atomic
  chore commit + state file advance + INV-31 spec-reviewer integrated).
  Implementation: doc/prompt updates only — NO core plugin code change.
- **Hybrid methodology** (user decision pre-brainstorming): Activity
  E' (true `--resume-from-magi` end-to-end) runs as **smoke test
  post Track-close**, NOT as gating Checkpoint 2 dispatch path.
  Rationale: lower risk vs Opcion A (manual run_magi.py for
  Checkpoint 2 dispatch as v1.0.2 precedent). Allows empirical
  observation of `_commit_approved_artifacts` conflict (R10) +
  `--resume-from-magi` autoregen interaction (R4) without blocking
  ship-readiness.

**Criterio de exito v1.0.3 (refinado vs spec-base)**:

- Tests baseline 1093 + 1 skipped preservados + ~13-22 nuevos =
  ~1106-1115 final (revisado vs spec-base 20-35; refleja Item E
  doc-only sin tests).
- `make verify` runtime <= 160s (NF-A); soft-target <= 150s.
- Coverage threshold mantenido en 88% (per Q4 v1.0.2 baseline);
  no regression below.
- **Activity D' Linux/POSIX dogfood validated** end-to-end con
  `magi_cross_check: true` + cross-check meta-reviewer artifacts
  produced (post Item B fix).
- **Activity E' true `--resume-from-magi` smoke-tested** post
  Track-close; observable gaps documented.
- v1.0.2 LOCKED carry-forward del CHANGELOG `[1.0.2]` Deferred
  (v1.0.3) section enteramente cerrados.
- G1 binding respetado: cap=3 HARD; sin INV-0. 3-cycle no-override
  streak preserved (v1.0.0 + v1.0.1 + v1.0.2).
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no
  converge — defer Pillar C (Items C+D+E) + methodology a v1.0.4.
  Pillar A + Pillar B son hard-LOCKED.

---

## 2. Items LOCKED

### 2.1 Item A — MAGI gate template alignment audit (Pillar A PRIMARY, Track Alpha)

**Track**: Alpha (subagent #1, single-purpose audit-only).

**Archivos**:
- Create: `docs/audits/v1.0.3-magi-gate-template-alignment.md` (audit
  artifact, doc-only).
- Create: `tests/test_magi_template_alignment.py` (alignment test,
  cross-artifact pattern).
- NO production code modifications by Track Alpha. GAP findings
  produce backlog entries for Track Beta OR defer to v1.0.4.

**Audit deliverable structure** — section-by-section table per
template's 6 sections:

```
| Template Section          | Plugin Impl Path                    | Status              | Evidence                       | Action                |
|---------------------------|-------------------------------------|---------------------|--------------------------------|------------------------|
| Trigger criteria          | pre_merge_cmd._loop2 + auto_cmd     | MATCH/GAP/OBSOLETE  | file:line citation             | resolved/deferred     |
| Pass threshold            | magi_dispatch.verdict_passes_gate   | ...                 | ...                            | ...                   |
| Carry-forward format      | pre_merge_cmd._build_carry_forward  | ...                 | ...                            | ...                   |
| Review summary artifact   | (likely missing)                    | likely GAP          | manual-only docs/reviews/      | auto-emit OR defer    |
| Cost awareness            | config.auto_skill_models            | ...                 | ...                            | ...                   |
| Per-project setup         | templates/CLAUDE.local.md.template  | ...                 | ...                            | ...                   |
```

**Alignment test** (`tests/test_magi_template_alignment.py`):

Pattern follows `tests/test_changelog.py` HF1 cross-artifact alignment:
- Read template content from
  `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md` (or
  copy fixture if portability concern).
- Extract required canonical strings (verdicts table headers,
  per-project setup checklist items, etc.) per template's normative
  format.
- Grep plugin's MAGI dispatch code (`pre_merge_cmd.py`,
  `magi_dispatch.py`) + templates (`templates/CLAUDE.local.md.template`)
  for those strings.
- Assert presence of required strings (or absence if template removed
  them).

**GAP routing protocol** (revised iter 1 fix W3+W10+I5
melchior+caspar+balthasar — Track Alpha truly audit-only):
- For each row marked `GAP`: assess severity (CRITICAL = template
  requires + plugin doesn't enforce; WARNING = plugin enforces stricter
  than template; INFO = doc-only difference).
- **ALL GAPs (CRITICAL + WARNING + INFO) → defer to v1.0.4 backlog by
  default**. Track Alpha is purely audit-only; it does NOT interrupt
  Track Beta with mid-cycle backlog entries. The audit doc Action
  column captures GAP findings + recommended v1.0.4 fix; orchestrator
  evaluates at finalization whether any GAP is severe enough to
  warrant cycle-abort + scope-spike (rare; documented escape valve).
- This preserves Q1 disjoint-surface contract: Track Alpha output =
  audit doc + alignment test only; Track Beta scope is fixed at
  cycle-start (B+C+D+E) and does NOT grow mid-cycle from Alpha
  findings.
- Template defects (template wrong, plugin right) → propose template
  amendment in audit doc; physical update to template file
  (`D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`)
  out-of-scope for this cycle (sister project).

### 2.2 Item B — Cross-check Windows long-filename fix (Pillar B LOCKED, Track Beta)

**Track**: Beta (subagent #2, first sequential task).

**Archivos**:
- Modify: `skills/sbtdd/scripts/pre_merge_cmd.py`
  (`_loop2_with_cross_check` o downstream subprocess invocation —
  exact location pending Beta subagent investigation).
- Possibly modify: `skills/sbtdd/scripts/subprocess_utils.py` if
  helper for long-path handling needed.
- New tests in `tests/test_pre_merge_cross_check.py` (extend) for
  WinError 206 reproduction + fix validation.

**Empirical context (v1.0.2 ship)**:

```
[sbtdd magi-cross-check] failed (will fall back to MAGI findings as-is): [WinError 206] The filename or extension is too long
```

Fired during all 3 v1.0.2 Loop 2 iters. Cross-check meta-reviewer
NEVER ran on Windows. Activity D' incomplete.

**Mitigation strategy (revised iter 2 — actual root cause identified)**:

Static read of `superpowers_dispatch._build_skill_cmd` (line 99)
revealed: cross-check prompt is packed into a single `-p <prompt>`
argv argument. For cross-check, this prompt includes the verdict +
findings text + diff truncated to 200KB. On Windows, ERROR_FILENAME_EXCEEDS_RANGE
(WinError 206) fires when total cmdline exceeds platform limits.

**Defense-in-depth fix** (combines two mitigations addressing both
possible root causes):

1. **`@filepath` prompt reference** (primary fix, addresses argv
   length): write the cross-check prompt content to a project-relative
   temp file (`.claude/magi-cross-check/.tmp/prompt-<run-id>.md`) and
   pass `@<filepath>` reference in argv. Argv stays short (<1KB);
   prompt content unbounded. Per `_build_skill_cmd` docstring, claude
   CLI supports `@file` references inside prompts — the sub-session
   forwards them.
2. **Project-relative temp dir** (secondary fix, addresses MAX_PATH):
   the `<run-id>` is short UUID4 hex (8 chars), keeping path under
   `.claude/magi-cross-check/.tmp/prompt-12345678.md` (<= 50 chars
   from repo root) — well under MAX_PATH 260 limit. Side-steps
   Windows MAX_PATH per R2 ladder step 3.

Modification surfaces:
- `pre_merge_cmd._dispatch_requesting_code_review` (line ~1243):
  write prompt to temp file before invoking
  `superpowers_dispatch.requesting_code_review`; pass file path as
  argv `@<path>` reference instead of inline prompt content.
- Cleanup: `finally`-block `Path(prompt_file).unlink(missing_ok=True)`
  + `shutil.rmtree(temp_dir, ignore_errors=True)`.

**Empirical validation**: Activity D' Linux/POSIX dogfood validates
end-to-end. Project-relative path + @file reference eliminate
Windows-specific test runtime dependency: any OS reproduces the
fix's behavior via tests that capture argv content.

### Items C, D, E — Deferred to v1.0.4 per iter-2 CRITICAL trigger

The original v1.0.3 spec sec.2.3-2.5 (Items C drift detector, D spec-snapshot autoregen, E close-task convention codification) are **deferred to v1.0.4 per spec sec.6.1 iter-2 CRITICAL trigger pre-stage**. MAGI Checkpoint 2 iter 2 still surfaced 1 CRITICAL (Task 2 test fidelity + refined Item B root-cause); pre-staged decision (`Items C+D+E defer to v1.0.4 first`) executed.

The Items C/D/E technical detail (problem statement, empirical context, implementation plan, escenarios) is preserved IN-PLACE below for v1.0.4 cycle reference. Track Alpha + Track Beta v1.0.3 implementation does NOT touch these items.

### 2.3 Item C — Drift detector line-anchored match (DEFERRED to v1.0.4)

**Track**: Beta (subagent #2, after Item B).

**Archivos**:
- Modify: `skills/sbtdd/scripts/drift.py` —
  `_plan_all_tasks_complete` function.
- Modify: `tests/test_drift.py` — append regression tests.

**Empirical context (v1.0.2 ship)**:

`drift._plan_all_tasks_complete` uses substring match
`"- [ ]" in plan_text[start:end]` which detects inline backtick
prose mentions of `\`- [ ]\`` literal as falsos pendientes. v1.0.2
hit during pre-merge dispatch:

```
DriftError: drift detected: state=done, HEAD=chore:, plan=[ ]
```

Trigger: 2 inline `\`- [ ]\`` mentions in plan-tdd.md (lineas 8 +
2238 documenting checkbox convention). Workaround was sanitize prose;
permanent fix requires line-anchored regex.

**Implementation**:

```python
import re

_OPEN_CHECKBOX_RE = re.compile(r"^- \[ \]", re.MULTILINE)


def _plan_all_tasks_complete(plan_text: str) -> str:
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

**Backward compat**: existing tests with real `- [ ]` checkboxes
(line-start) continue to detect drift correctly. Inline backtick
mentions no longer false-positive.

### 2.4 Item D — Spec-snapshot auto-regeneration (DEFERRED to v1.0.4)

**Track**: Beta (subagent #2, after Item C).

**Archivos**:
- Modify: `skills/sbtdd/scripts/spec_cmd.py` —
  `_run_magi_checkpoint2` post-MAGI-pass branch.
- Modify: `skills/sbtdd/scripts/state_file.py` (if needed) for
  `spec_snapshot_emitted_at` field handling.
- Use existing: `skills/sbtdd/scripts/spec_snapshot.py`
  (`emit_snapshot` + `persist_snapshot` already shipped v1.0.0
  Feature H Group B option 2).
- Modify: `tests/test_spec_cmd.py` — append autoregen tests.

**Empirical context (v1.0.2 ship)**:

`planning/spec-snapshot.json` carried v1.0.1 escenarios (A0/A1/A2/A3
series) into v1.0.2 cycle. Required manual regeneration via direct
Python invocation during pre-merge debug. Resulted in:

```
MAGIGateError: Spec scenarios changed since plan approval; re-approve plan via /writing-plans + Checkpoint 2.
```

**Implementation in `_run_magi_checkpoint2`**:

After MAGI verdict converges to `>= GO_WITH_CAVEATS` full no-degraded
(post-iter-loop branch, before `_create_state_file` +
`_commit_approved_artifacts`):

```python
# v1.0.3 Item D: spec-snapshot auto-regeneration
import spec_snapshot
snapshot = spec_snapshot.emit_snapshot(spec_path)
spec_snapshot.persist_snapshot(snapshot, root / "planning" / "spec-snapshot.json")
# state_file.spec_snapshot_emitted_at update happens via existing
# _mark_plan_approved_with_snapshot pattern (R10 v1.0.0 fix).
```

**R4 risk mitigation** (revised iter 1 fix W7+I7 balthasar+caspar —
defensive guard, not observable-only):
- Idempotency assertion: autoregen test asserts that two consecutive
  invocations over identical spec content produce byte-identical
  snapshot file (escenario D-3 below codifies this).
- Skip-on-resume guard option: if `--resume-from-magi` detected AND
  spec-snapshot.json mtime is within 60s of spec-behavior.md mtime
  (i.e., autoregen already happened recently), skip the autoregen
  call to prevent redundant write. Defensive only — idempotency
  means double-write is also safe, but skip avoids unnecessary I/O.
- Activity E' validates the guard empirically (no surprise commit
  conflicts).

**INV-37 invocation-site tripwire** (iter 1 fix W11 caspar):
new test `test_d_inv37_unaffected_by_autoregen` asserts that
`spec_cmd._run_spec_flow` mtime + size + sha256 composite-signature
check still fires correctly when autoregen runs in the
`_run_magi_checkpoint2` post-MAGI-pass branch. This codifies the
spec sec.9.5 "INV-37 unaffected" claim as test enforcement, not
just documentation.

### 2.5 Item E — Close-task convention codification (DEFERRED to v1.0.4)

**Track**: Beta (subagent #2, after Item D).

**Archivos** (doc-only, NO production code):
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add
  close-task automation requirement).
- Modify: `templates/CLAUDE.local.md.template` (template guidance to
  destination projects).
- Document: convention in plan template generation (writing-plans
  skill prompt extension).

**Empirical context (v1.0.2 ship)**: subagents marked task headings
(`### Task N: ... [x]`) instead of per-step checkboxes (`- [ ]` →
`- [x]`). Drift detector + spec_lint expect per-step checkboxes per
the convention documented in plan I5 Process notes; subagents
diverged despite explicit documentation.

**Q2 decision (brainstorming): Option B — codify via `/sbtdd close-task`
automation**. The command already exists and does:
1. Flip ALL `- [ ]` → `- [x]` in active task section atomically.
2. Atomic `chore: mark task {id} complete` commit (plan diff only).
3. Advance state file (next open task fresh red OR plan done).
4. Bonus: dispatches spec-reviewer (INV-31 v0.2 default-on;
   `--skip-spec-review` escape valve).

**Implementation footprint (doc-only)**:
- `skills/sbtdd/SKILL.md` orchestrator rules add explicit:
  "Subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py
  close-task` after Refactor phase verify-clean. Manual plan-file
  edits for checkbox flips are NON-CONFORMING and trigger drift
  detection."
- `templates/CLAUDE.local.md.template` updated to include the
  convention rule + reference to close-task command.
- Smoke test in new file `tests/test_close_task_subagent_pattern.py`
  asserts close-task invocation chain (existing tests cover the
  command itself; smoke test covers the convention enforcement
  point).

**Cost (R9)**: ~1-2 min per task close (INV-31 spec-reviewer overhead,
default-on). Track Beta has 4 tasks; total overhead ~4-8 min across
cycle. Acceptable.

### 2.6 Activity D' — Linux/POSIX dogfood completion (methodology)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (config + run de comandos).

**Pasos del orchestrator post Track-Alpha + Track-Beta close,
post-Item-B fix landed**:

1. Verify `magi_cross_check: true` set in `.claude/plugin.local.md`
   (already enabled since v1.0.0 Loop 2 iter 3 dogfood).
2. Run `/sbtdd pre-merge` end-to-end:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
3. Verify cross-check meta-reviewer ejecuta sin WinError 206 (Item B
   fix validates here).
4. Capture artifacts:
   ```bash
   ls .claude/magi-cross-check/iter*-*.json
   ```
5. Run telemetry script (Item A v1.0.2 ship) on real artifacts:
   ```bash
   python scripts/cross_check_telemetry.py --root .claude/magi-cross-check --format markdown > /tmp/v103-cross-check.md
   ```
6. Document findings in CHANGELOG `[1.0.3]` Process notes:
   - Cross-check meta-reviewer succeeded vs failed.
   - Iter count Loop 2.
   - Cross-check decision distribution.
   - Observable gaps (meta-reviewer file:line referencing rate;
     diff embedding effectiveness; carry-forward block presence).

**Failure mode** (R7 risk): if Item B fix incomplete or new failure
mode surfaces, document and defer to v1.0.4 retry. Activity D' is
non-blocking for ship.

### 2.7 Activity E' — True `--resume-from-magi` smoke test (methodology)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (test path exercise + Process notes).

**Hybrid methodology placement**: Activity E' runs as **smoke test
post Track-close + post Activity D'**, NOT as gating Checkpoint 2
dispatch path. Per user pre-brainstorming decision, Opcion A (manual
`run_magi.py`) handles the Checkpoint 2 dispatch (lower-risk, v1.0.2
precedent); Opcion B (`/sbtdd spec --resume-from-magi`) is exercised
afterwards as smoke test on already-approved artifacts.

**Pasos del orchestrator** (post Activity D'):

1. Verify spec-behavior.md + plan-tdd-org.md exist + are committed
   (already true post-Track-close).
2. Pre-flight spec_lint dry-run (W5 v1.0.1 fix):
   ```bash
   python -m skills.sbtdd.scripts.spec_lint sbtdd/spec-behavior.md
   python -m skills.sbtdd.scripts.spec_lint planning/claude-plan-tdd-org.md
   ```
3. Invoke `/sbtdd spec --resume-from-magi`:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
   ```
4. Observe:
   - Brainstorming/writing-plans subprocess NOT spawned (verifiable).
   - MAGI Checkpoint 2 dispatched on existing artifacts.
   - Item D autoregen interaction: spec-snapshot regenerated
     idempotently OR conflict observable.
   - `_commit_approved_artifacts` interaction: artifacts already
     committed, behavior observable (no-op? amend? new commit?).
   - State file mutations: existing post-impl state vs new
     `_create_state_file` overwrite behavior.
5. Document observable gaps in CHANGELOG `[1.0.3]` Process notes:
   - Wall-clock end-to-end.
   - R10 commit-conflict observability.
   - R4 autoregen-interaction observability.
   - Any other unexpected behavior.

**Failure mode**: methodology activity is **non-gating for ship**.
If E' fails (e.g., R10 commit conflict surfaces), document the
specific failure mode + roll forward to v1.0.4 fix. Cycle continues
to finalization regardless.

---

## 3. Cross-module contracts

v1.0.3 NO introduce nuevos cross-cuts. Items consumen helpers
existentes:

- **Item A** alignment test follows `tests/test_changelog.py` HF1
  cross-artifact alignment pattern (line-anchored grep template
  strings vs plugin code paths).
- **Item B** modifies cross-check temp dir construction in
  `pre_merge_cmd.py` (likely `_loop2_with_cross_check` o downstream
  subprocess invocation). May extend `subprocess_utils.py` if Windows
  long-path helper needed.
- **Item C** `drift._plan_all_tasks_complete` regex tightening —
  preserved interface signature (input: plan_text str, output: "[x]"
  or "[ ]" string).
- **Item D** `spec_cmd._run_magi_checkpoint2` post-MAGI-pass branch
  invokes existing `spec_snapshot.emit_snapshot` +
  `spec_snapshot.persist_snapshot` (shipped v1.0.0 Feature H Group B
  option 2).
- **Item E** `/sbtdd close-task` command preserved as-is (already
  shipped v0.1+; implementation in `close_task_cmd.py`); this item
  is doc-only enforcement update.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` (existing
  en `errors.py`).
- `subprocess_utils.run_with_timeout`: ningun item nuevo lo invoca
  directamente.
- `_compute_loop2_diff_with_meta` (v1.0.0): unchanged.
- `_loop2_with_cross_check` (v1.0.0): Item B modifies temp dir
  handling within this function; semantic preserved.
- `_run_magi_checkpoint2` lint timing contract (v1.0.2 Item C C1
  fix): preserved — autoregen happens AFTER MAGI iter loop converges,
  not in lint gate.
- INV-37 composite-signature output validation tripwire (v1.0.1):
  unchanged.

---

## 4. Escenarios BDD

Distribuidos por item — la spec usa Tier 2 permissive regex de
`spec_snapshot.emit_snapshot` (shipped en v1.0.1 Item A1) que
acepta escenarios distribuidos a traves de cualquier seccion sin
requerir literal `## §4 Escenarios` header. Top-level numbering uses
`## 4.` (digit + dot + space) to satisfy R3 monotonic check (v1.0.2
Item C R3 warning regression preventive).

### Item A — Template alignment audit

**Escenario A-1: audit doc structure exists per template's 6 sections**

> **Given** Template canonical at `D:\jbolivarg\BolivarTech\AI_Tools\
> magi-gate-template.md` con 6 sections (Trigger criteria, Pass
> threshold, Carry-forward, Review summary, Cost awareness,
> Per-project setup).
> **When** Audit doc `docs/audits/v1.0.3-magi-gate-template-alignment.md`
> generated by Track Alpha subagent.
> **Then** Doc contains tabla con minimum 6 rows (one per template
> section). Each row has TEMPLATE_SECTION + PLUGIN_IMPL_PATH +
> STATUS + EVIDENCE + ACTION columns.

**Escenario A-2: each row has Status + Evidence + Action**

> **Given** Audit doc rows generated.
> **When** Inspecting per-row content.
> **Then** Each row's STATUS field is one of {MATCH, GAP, OBSOLETE}.
> EVIDENCE field is non-empty (contains file:line citation or doc
> reference). ACTION field describes resolution (resolved en cycle
> OR deferred to v1.0.4 OR template amendment proposed).

**Escenario A-3: alignment test grep template strings**

> **Given** Template at known location + plugin source code in
> `skills/sbtdd/scripts/`.
> **When** `tests/test_magi_template_alignment.py` runs.
> **Then** Test extracts canonical strings from template (verdicts
> table headers, per-project setup checklist items, etc.) +
> grep plugin code for required strings + asserts presence/absence
> per template normative format.

**Escenario A-4: GAP findings produce actionable items**

> **Given** Audit identifies GAP row (template requires X, plugin
> doesn't enforce X).
> **When** ACTION column populated.
> **Then** ACTION is either: code change ID for Track Beta backlog,
> OR documentation update target, OR template amendment proposal,
> OR explicit "deferred to v1.0.4 with rationale".

**Escenario A-5: cross-artifact alignment test detects regression**

> **Given** Template string `XYZ` required + plugin code currently
> includes `XYZ`.
> **When** Plugin code modified to remove `XYZ` (hypothetical
> regression).
> **Then** Alignment test FAILS with message identifying which
> template section + which plugin file lost the canonical string.

### Item B — Cross-check Windows long-filename fix

**Escenario B-1: synthetic long path triggers WinError 206 pre-fix**

> **Given** Windows runtime + cross-check temp dir construction with
> long base path (>= 260 chars total path length).
> **When** Pre-fix `_loop2_with_cross_check` invokes subprocess
> writing to that temp file.
> **Then** OSError raised with `[WinError 206] The filename or
> extension is too long` (or equivalent Windows long-path error).

**Escenario B-2: fix applied passes**

> **Given** Same setup as B-1 + Item B fix applied (shorter prefix
> OR `\\?\` syntax OR project-relative temp dir).
> **When** `_loop2_with_cross_check` invokes subprocess.
> **Then** No WinError 206. Cross-check meta-reviewer artifact
> written successfully.

**Escenario B-3: paths >= 300 chars work post-fix**

> **Given** Synthetic path construction with total length >= 300
> chars (NF36 requirement).
> **When** Cross-check temp file write.
> **Then** Write succeeds. Validates fix robustness against
> aggressive long paths, not just edge case at 260.

**Escenario B-4: short paths still work (backward compat)**

> **Given** Normal-length paths (< 260 chars).
> **When** Cross-check runs.
> **Then** No regression — cross-check works identically to v1.0.2
> behavior when paths are short.

**Escenario B-5: Linux/POSIX path unaffected**

> **Given** Linux/POSIX runtime + cross-check.
> **When** Activity D' Linux dogfood runs.
> **Then** No WinError 206 (POSIX has no MAX_PATH equivalent).
> Behavior identical to pre-fix on POSIX systems.

### Item C — Drift detector line-anchored match

**Escenario C-1: inline backtick prose mention NOT false-positive**

> **Given** Plan file con `### Task 1:` header marked complete +
> all step checkboxes flipped to `- [x]` + 2 inline backtick prose
> mentions of `\`- [ ]\`` literal (descriptive, not actual checkboxes).
> **When** `drift._plan_all_tasks_complete(plan_text)` invoked.
> **Then** Returns `"[x]"` (no false-positive). Inline backtick
> mentions NOT counted as open checkboxes.

**Escenario C-2: real `- [ ]` checkbox detected drift**

> **Given** Plan file with task section containing real
> line-anchored `- [ ]` checkbox (not inside backticks).
> **When** `_plan_all_tasks_complete` invoked.
> **Then** Returns `"[ ]"`. Drift correctly detected.

**Escenario C-3: line-anchored regex skipea backtick prose**

> **Given** Multi-task plan with mix of real `- [ ]` checkboxes +
> inline backtick `\`- [ ]\`` prose mentions across multiple
> sections.
> **When** Detection invoked.
> **Then** Only line-start `- [ ]` patterns counted; backtick mentions
> ignored. Result reflects actual task completion state.

**Escenario C-4: backward compat existing real-checkbox fixtures**

> **Given** Existing test fixtures with real `- [ ]` checkboxes
> (no backtick prose).
> **When** Refactored regex applied.
> **Then** All existing fixtures' detection results unchanged. No
> regression.

### Item D — Spec-snapshot auto-regeneration

**Escenario D-1: post-MAGI-pass auto-regenerates snapshot**

> **Given** `_run_magi_checkpoint2` invoked + MAGI verdict converges
> to GO_WITH_CAVEATS full no-degraded + spec-behavior.md content
> has 26 escenarios.
> **When** Post-MAGI-pass branch executes.
> **Then** `planning/spec-snapshot.json` contains all 26 escenarios
> (current spec content). Old escenarios from prior cycle replaced.

**Escenario D-2: state file `spec_snapshot_emitted_at` updated**

> **Given** Same setup as D-1.
> **When** Autoregen completes.
> **Then** `state_file.SessionState.spec_snapshot_emitted_at`
> contains current UTC ISO 8601 timestamp.

**Escenario D-3: `--resume-from-magi` interaction safe**

> **Given** spec-behavior.md committed + spec-snapshot.json
> previously emitted (from prior cycle's plan approval).
> **When** `/sbtdd spec --resume-from-magi` invoked + MAGI verdict
> passes.
> **Then** Autoregen runs idempotently. If spec content unchanged
> from prior emit, snapshot file content identical. If spec content
> changed (current cycle), snapshot updated. NO MAGIGateError on
> snapshot drift.

**Escenario D-4: backward compat existing snapshot persistence**

> **Given** Plain `/sbtdd spec` (NOT --resume-from-magi) invoked
> with `--brainstorming` + `--writing-plans` dispatched normally.
> **When** Cycle reaches MAGI verdict pass.
> **Then** Same autoregen behavior as D-1 + D-2. No regression
> against pre-v1.0.3 manual emit pattern (which was via
> `_mark_plan_approved_with_snapshot` per R10 v1.0.0 fix).

### Item E — Close-task convention codification

**Escenario E-1: close-task command flips per-step checkboxes correctly**

> **Given** Plan-tdd.md with active task containing 5 step
> checkboxes (4 already `[x]`, 1 still `[ ]`) + state file
> `current_task_id="3", current_phase="refactor"`.
> **When** Subagent invokes `python skills/sbtdd/scripts/run_sbtdd.py
> close-task --skip-spec-review` after Refactor verify-clean.
> **Then** All 5 step checkboxes flipped to `[x]`. Atomic `chore:
> mark task 3 complete` commit landed (plan diff only). State file
> advances to next open task `current_task_id="4",
> current_phase="red"` OR `done` if last task.

**Escenario E-2: documentation references close-task in subagent prompts**

> **Given** Updated `skills/sbtdd/SKILL.md` orchestrator rules +
> `templates/CLAUDE.local.md.template` + plan template generation
> prompt (writing-plans skill extension).
> **When** Grep for "close-task" pattern.
> **Then** Each of these documents contains explicit instruction:
> "after Refactor phase verify-clean, invoke `python
> skills/sbtdd/scripts/run_sbtdd.py close-task` (--skip-spec-review
> if appropriate). Manual plan-file checkbox edits are
> NON-CONFORMING."

---

## 5. Subagent layout + execution timeline

### 5.1 Track Alpha (subagent #1, single-purpose audit)

**Owner**: code-architect or general-purpose subagent.
**Scope**: Item A only (audit doc + alignment test + GAP findings
backlog routing).
**Wall-time estimado**: ~1 dia.

Single task, no sequential ordering needed:

1. **A** (~1 dia): read template at
   `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`. Audit
   plugin's MAGI dispatch path code section-by-section. Generate
   `docs/audits/v1.0.3-magi-gate-template-alignment.md` table.
   Generate `tests/test_magi_template_alignment.py` cross-artifact
   test. Route GAP findings: CRITICAL → Track Beta backlog;
   WARNING/INFO → Process notes deferred. NO production code
   modifications.

Sin dependencias inter-track durante implementation phase. Track
Alpha output (audit doc + test) is purely additive.

### 5.2 Track Beta (subagent #2, sequential B → C → D → E)

**Owner**: code-architect or general-purpose subagent.
**Scope**: Items B + C + D + E (all code fixes + doc updates).
**Wall-time estimado**: ~3 dias.

Sequential ordering rationale:

1. **B first** (~1 dia): cross-check Windows long-filename fix in
   `pre_merge_cmd.py`. Critical infrastructure; landing first
   unblocks Activity D' Linux/POSIX dogfood.
2. **C second** (~0.5 dia): drift detector line-anchored regex in
   `drift.py`. Independent of B.
3. **D third** (~1 dia): spec-snapshot autoregen in `spec_cmd.py` +
   state_file integration + tests. Independent of C.
4. **E last** (~0.5 dia): close-task convention codification in
   `SKILL.md` + `templates/CLAUDE.local.md.template` + smoke test.
   Doc-only; no overlap with B/C/D code surfaces.

Sin dependencias inter-track.

### 5.3 Mid-cycle methodology (orchestrator)

**Owner**: orchestrator (single Claude Code session).
**Scope**: Activity D' + Activity E' (smoke test).
**Wall-time estimado**: ~30-60 min total.

Triggered AFTER Track-Alpha + Track-Beta close + AFTER Item B fix
landed:

1. **D' first** (~30-45 min): Activity D Linux/POSIX dogfood
   completion. Run `/sbtdd pre-merge` end-to-end con cross-check
   enabled. Capture artifacts. Run telemetry script. Document.
2. **E' last** (~15-30 min): True `--resume-from-magi` smoke test.
   Pre-flight spec_lint dry-run. Exercise Opcion B path. Observe
   R4 + R10 interactions. Document observable gaps. Non-gating.

### 5.4 True parallelism observado

Surfaces Track Alpha vs Track Beta:

| Surface | Alpha | Beta |
|---------|-------|------|
| `docs/audits/v1.0.3-magi-gate-template-alignment.md` | yes (new) | — |
| `tests/test_magi_template_alignment.py` | yes (new) | — |
| `skills/sbtdd/scripts/pre_merge_cmd.py` | — | yes (Item B modify) |
| `skills/sbtdd/scripts/subprocess_utils.py` | — | possibly (Item B helper) |
| `tests/test_pre_merge_cross_check.py` | — | yes (Item B extend) |
| `skills/sbtdd/scripts/drift.py` | — | yes (Item C modify) |
| `tests/test_drift.py` | — | yes (Item C extend) |
| `skills/sbtdd/scripts/spec_cmd.py` | — | yes (Item D modify) |
| `skills/sbtdd/scripts/state_file.py` | — | possibly (Item D field handling) |
| `tests/test_spec_cmd.py` | — | yes (Item D extend) |
| `skills/sbtdd/SKILL.md` | — | yes (Item E modify) |
| `templates/CLAUDE.local.md.template` | — | yes (Item E modify) |
| `tests/test_close_task_subagent_pattern.py` | — | yes (Item E new smoke) |

**Cero overlap**. Tracks pueden run truly parallel sin merge
conflicts.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (CHANGELOG `[1.0.0]`, precedente
  cerrado v1.0.1+v1.0.2 = 2-streak no-override). NO INV-0 path.
- Bundle scope multi-pillar (5 plan tasks + 2 methodology) — esperamos
  converger en 2-3 iters.
- **Iter 2 CRITICAL trigger** (revised iter 1 fix W5+I1+I8
  balthasar+melchior+caspar): if Loop 2 iter 2 still surfaces ANY
  CRITICAL finding (post-iter-1-triage-fix), scope-trim immediately
  rather than burning iter 3 on a multi-pillar bundle. Pre-staged
  decision: Items C+D+E defer to v1.0.4 first; if needed, also
  Item E only; only Pillar A + Pillar B are hard-LOCKED for v1.0.3
  ship.
- Si llega a iter 3 sin convergencia (despite iter-2 trigger), default
  scope-trim ladder applies:
  1. Defer Pillar C Items C+D+E to v1.0.4 (smaller scope).
  2. Then Item E only deferred (codification can happen any cycle).
  3. Then Item D only deferred (autoregen is opt-in convenience).
  4. Pillar A audit + Pillar B Windows fix son hard-LOCKED.

**Methodology decision**: Checkpoint 2 dispatch usa **Opcion A
manual `run_magi.py`** per hybrid methodology + v1.0.2 precedent.
Activity E' (Opcion B `/sbtdd spec --resume-from-magi`) corre
DESPUES como smoke test, no como gating dispatch.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- Bundle scope minimal (5 plan tasks, mostly small fixes) —
  esperamos converger en 1 iter.

### 6.3 Loop 2 (`/magi:magi`) — Activity D' dogfood

- **Cap=5** per `auto_magi_max_iterations`.
- **Cross-check enabled mid-cycle**: Activity D' ENTREGA es running
  `/sbtdd pre-merge` post Item B fix.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding fallback**: si Loop 2 iter 3 no converge clean,
  scope-trim per spec-base sec.6.1 ladder. Pillar C + methodology
  defer to v1.0.4.
- **Manual fallback** (R7 mitigation): si `/sbtdd pre-merge` hits
  failure mode after Item B fix, escape via Ctrl+C + `python
  skills/magi/scripts/run_magi.py code-review <payload>` (precedente
  v1.0.0+v1.0.1+v1.0.2).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.3 own-cycle (e.g.,
Item B fix incomplete, new regression), el operator MUST fall back
a manual `python skills/magi/scripts/run_magi.py` direct dispatch +
manual mini-cycle commits. Document en CHANGELOG `[1.0.3]` Process
notes. Precedentes v0.5.0 + v1.0.0 + v1.0.1 + v1.0.2 todos demonstrate
ship viability con manual fallback.

**Verbatim fallback command** (warm + ready to copy-paste,
operator-prepared header per W4 v1.0.2 fix):

```bash
mkdir -p .claude/magi-runs/v103-loop2-iter1
# Step 0: operator prepares v103-loop2-iter1-header.md (Loop 2 mode
# context; see .claude/magi-runs/v103-checkpoint2-iter1-header.md
# for the analogous Checkpoint 2 template).
{
  cat .claude/magi-runs/v103-loop2-iter1-header.md
  echo "---"
  cat sbtdd/spec-behavior.md
  echo "---"
  cat planning/claude-plan-tdd.md
} > .claude/magi-runs/v103-loop2-iter1-payload.md
python skills/magi/scripts/run_magi.py code-review \
  .claude/magi-runs/v103-loop2-iter1-payload.md \
  --model opus --timeout 900 \
  --output-dir .claude/magi-runs/v103-loop2-iter1
```

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.2 → 1.0.3.

### 7.2 CHANGELOG `[1.0.3]` sections

- **Added** —
  `docs/audits/v1.0.3-magi-gate-template-alignment.md` (Item A);
  `tests/test_magi_template_alignment.py` (Item A);
  Cross-check Windows long-filename fix in `pre_merge_cmd.py`
  (Item B);
  Drift detector line-anchored regex in `drift.py` (Item C);
  Spec-snapshot autoregen in `spec_cmd._run_magi_checkpoint2`
  (Item D);
  Close-task convention codification in `skills/sbtdd/SKILL.md` +
  `templates/CLAUDE.local.md.template` (Item E doc-only).
- **Changed** — same as Added per item; no API breaks expected.
- **Process notes** — Activity D' Linux/POSIX dogfood findings
  (cross-check working, iter count, decision distribution);
  Activity E' `--resume-from-magi` smoke test observable gaps (R4
  autoregen interaction, R10 commit conflict); Item A audit
  GAP/MATCH stats; v1.0.2 LOCKED carry-forward closed.
- **Deferred (rolled to v1.0.4)** — parallel task dispatcher; real
  headless detection; `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit; 600s
  subprocess hang full LOUD-FAST fix.
- **Deferred (rolled to v1.0.5+)** — agreement_rate→keep_rate API
  rename (schema bump); spec_lint R3 promote to error severity;
  per-module coverage raise to 85% baseline for outliers;
  pytest-cov proper dev dep registration; INV-31 default flip
  cycle.

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.3 docs section sobre template alignment audit
  artifact + Item B Windows fix + close-task convention requirement.
- **SKILL.md**: `### v1.0.3 notes` section documentando 5 plan
  tasks + 2 methodology activities + close-task automation
  enforcement (Q2 Option B).
- **CLAUDE.md**: v1.0.3 release notes pointer.

---

## 8. Risk register v1.0.3

(Extends spec-base R1-R8 + R9-R10 added per brainstorming Q2 +
hybrid methodology.)

- **R1** (spec-base): Item A audit may surface MANY gaps. Mitigation:
  prioritize gaps by severity (CRITICAL = fix in Track Beta;
  WARNING/INFO = defer to v1.0.4); audit doc allows Action column to
  document deferral with rationale.
- **R2** (spec-base): Item B Windows fix may require deeper changes
  than expected. Mitigation: 3-step ladder (shorter prefix → `\\?\`
  syntax → project-relative temp dir); if scope spike, reduce to
  minimum viable + defer full to v1.0.4.
- **R3** (spec-base): Item C drift detector regex may break existing
  fixtures. Mitigation: thorough regression test suite covering both
  true positives + false positives; backward compat verified by
  existing test_drift.py passing.
- **R4** (spec-base): Item D autoregen may interact unexpectedly
  with `--resume-from-magi`. Mitigation: Activity E' empirical
  validation catches; if surfaces, adjust autoregen to skip on
  flag detected (or document idempotency works correctly).
- **R5** (spec-base): Item E close-task convention may surface
  fundamental disagreement between subagent ergonomics + drift
  detector. Mitigation: Q2 brainstorming chose Option B (codify via
  existing `/sbtdd close-task` command); enforced via doc + smoke
  test; subagents can use `--skip-spec-review` escape valve for
  speed.
- **R6** (spec-base): Bundle scope multi-pillar aumenta riesgo de
  Loop 2 non-convergence. Mitigation: G2 binding scope-trim ladder
  defer Pillar C + methodology a v1.0.4 si Loop 2 iter 3 no converge.
- **R7** (spec-base): Activity D' could fail again if Item B fix
  incomplete; Activity E' could fail if `--resume-from-magi` path
  has regression. Mitigation: methodology activities are non-blocking
  for ship — document failures + defer to v1.0.4.
- **R8** (spec-base): Template alignment may reveal template defects.
  Mitigation: audit doc Action column allows "template amendment"
  proposal; physical update to template file out-of-scope (sister
  project).
- **R9** (NEW Q2 brainstorming): Option B close-task codification
  adds ~1-2 min per task close (INV-31 spec-reviewer overhead).
  Mitigation: Track Beta has 4 tasks; total ~4-8 min across cycle;
  `--skip-spec-review` escape valve available for non-INV-31-blocking
  workflows.
- **R10** (NEW hybrid methodology): Activity E' smoke test may hit
  `_commit_approved_artifacts` conflict since artifacts are already
  committed by orchestrator before E' runs. Mitigation: methodology
  activity is non-gating; if conflict surfaces, document observable
  + roll forward to v1.0.4 fix; Activity D' methodology runs FIRST
  (validates cross-check infra), Activity E' runs LAST as final
  smoke test, even failure doesn't block ship.

---

## 9. Acceptance criteria final v1.0.3

v1.0.3 ship-ready cuando:

### 9.1 Functional Items A-E + Activities D'-E'

- **F1**. F124-F127: template alignment audit document + alignment
  test + GAP fixes routed.
- **F2**. F128-F131: Windows long-filename fix + reproduction test
  + empirical Activity D' validation.
- **F3**. F132-F134: drift detector line-anchored regex + regression
  + backward compat.
- **F4**. F135-F137: spec-snapshot autoregen + state file update +
  test.
- **F5**. F138-F139: close-task convention codification + impl + docs.
- **F6**. F140-F142: Activity D' Linux/POSIX dogfood empirical
  validation + telemetry consumption.
- **F7**. F143-F144: Activity E' true `--resume-from-magi` smoke
  test (non-gating) + observable gaps documented.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 160s. Soft-target
  <= 150s.
- **NF-B**. Tests baseline 1093 + 1 skipped + ~13-22 nuevos =
  ~1106-1115 final (revised down vs spec-base 20-35).
- **NF-C**. Cross-platform (Windows + POSIX) — Item B specifically
  validates Windows.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `pre_merge_cmd.py` (Item B), `drift.py` (Item C),
  `spec_cmd.py` (Item D), `state_file.py` (Item D field handling),
  `subprocess_utils.py` (Item B helper if needed),
  `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template`
  (Item E doc).

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path. 3-cycle
  no-override streak preserved (becomes 4-cycle with v1.0.3 ship).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.3]` entry written con secciones Added /
  Changed / Process notes + Activity D' empirical findings +
  Activity E' empirical findings + template alignment GAP/MATCH
  stats + R10 commit-conflict observability.
- **P4**. Version bump 1.0.2 -> 1.0.3 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.3` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. Activity D' Linux/POSIX dogfood: cross-check infrastructure
  validated empirically post Item B fix.
- **P8**. Activity E' true `--resume-from-magi` smoke test exercised
  post Track-close; observable gaps documented (non-gating).

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.3 ship + 5 plan tasks
  + 2 methodology activities + audit document).
- **D3**. Nuevos artifacts documentados:
  - `docs/audits/v1.0.3-magi-gate-template-alignment.md` (audit
    artifact).
  - `tests/test_magi_template_alignment.py` (alignment test).
  - Item B cross-check Windows fix changes in CHANGELOG.

---

## 9.5 Inherited invariants from v0.4.x and v1.0.1+v1.0.2 (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording (canonical
single-line text `[sbtdd magi] synthesizer failed; manual synthesis
recovery applied`) is preserved verbatim across spec / CHANGELOG /
impl per the cross-artifact alignment contract
(`tests/test_changelog.py`). v1.0.3 ships no behavioral change to
this path.

The INV-37 composite-signature output validation tripwire (v1.0.1
Item A0) is also preserved verbatim — `_run_spec_flow` mtime + size
+ sha256 check applies during v1.0.3 own-cycle if operator drives
`/sbtdd spec` instead of using `--resume-from-magi`. Item D autoregen
runs in `_run_magi_checkpoint2` post-MAGI-pass branch, NOT in
`_run_spec_flow` lint timing path; INV-37 unaffected.

The Item C v1.0.2 `spec_lint` gate (R1-R5 rules with R3 warning per
Q3) is preserved unchanged. v1.0.3 Activity E' pre-flight spec_lint
dry-run (W5 v1.0.1 fix) catches self-inflicted R5/R1 violations
before `--resume-from-magi` invocation.

The Q4 v1.0.2 coverage threshold = `floor(baseline) - 2%` protocol
is preserved at 88% (measured baseline 90.12% in v1.0.2 ship).
v1.0.3 must not regress below 88%.

---

## 10. Referencias

- Spec base v1.0.3: `sbtdd/spec-behavior-base.md`
  (commit en branch `feature/v1.0.3-bundle`).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2
  frozen: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.2 ship record: tag `v1.0.2` (commit `80731e6`); merge
  `3169767` on `main`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.2 LOCKED carry-forward to v1.0.3 per CHANGELOG `[1.0.2]`
  Process notes + Deferred (rolled to v1.0.3) section.
- v1.0.3 LOCKED original sole-pillar: memory
  `project_v103_template_alignment_audit.md` (template alignment
  audit per user directive 2026-05-03).
- Template canonical source:
  `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md` (411
  lines, synthesized 2026-05-01 from sbtdd-workflow + MAGI plugin
  empirical learnings).
- v1.0.4 LOCKED items: memory
  `project_v104_parallel_task_dispatcher.md` +
  `project_v104_subprocess_headless_detection.md` (sequenced AFTER
  v1.0.3 so v1.0.4+ runs against template-aligned baseline).
- Brainstorming refinement decisions (2026-05-06):
  - Q1 — 2-track parallel partition: Track Alpha = A audit-only
    (no production code); Track Beta = B + C + D + E (all code +
    doc fixes).
  - Q2 — Item E close-task convention codification via Option B
    (`/sbtdd close-task` automation, doc-only enforcement).
  - Hybrid methodology (pre-brainstorming user decision): Opcion A
    manual `run_magi.py` for Checkpoint 2 dispatch; Opcion B
    `/sbtdd spec --resume-from-magi` as Activity E' smoke test post
    Track-close.
- Branch: trabajo en `feature/v1.0.3-bundle` (branched off `main`
  HEAD `3169767` = v1.0.2 merge commit).
