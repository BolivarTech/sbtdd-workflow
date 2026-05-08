# Especificacion base — sbtdd-workflow v1.0.4 (post-v1.0.3 ship)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.4).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-07 post-v1.0.3 ship (tag `v1.0.3` at commit `39a9c18`,
> branch `feature/v1.0.4-bundle` branched off `main` HEAD `0aeff7d` =
> v1.0.3 merge commit).
>
> v1.0.4 ships los items LOCKED CRITICAL para unblock automation paths
> que v1.0.1 introduced + v1.0.3 dogfood empirically confirmed broken
> (`/sbtdd pre-merge` + `/sbtdd spec` hang on `/receiving-code-review`,
> `/brainstorming`, `/writing-plans` interactive subprocess).
>
> Per Balthasar v1.0.3 Loop 2 iter 1 INFO ("v1.0.4 carrying meaningful
> debt"): scope-trim upfront. v1.0.4 = real headless detection + parallel
> task dispatcher + state file phase auto-advance methodology gap fix
> (3 pillars). Defer audit GAPs (L1.0.4-A through L1.0.4-D) + v1.0.3
> Items C/D/E (drift line-anchored, spec-snapshot autoregen, close-task
> convention codification) to v1.0.5 polish pillar.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este
> documento NO lo reemplaza — agrega el delta v1.0.4 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex.
>
> v1.0.4 G1 binding HARD: cap=3 sin INV-0 path para Checkpoint 2
> (precedente cerrado v1.0.0+v1.0.1+v1.0.2+v1.0.3 = 4-cycle no-override
> streak). G2 binding: scope-trim default si Loop 2 iter 3 no converge
> (defer Pillar C a v1.0.5 si necesario; Pillars A + B son hard-LOCKED).
>
> v1.0.3 introduced **iter-2 CRITICAL trigger** (spec sec.6.1) which
> fired empirically for the first time during v1.0.3 own-cycle. v1.0.4
> preserves this trigger pre-stage.

---

## 1. Objetivo

**v1.0.4 = "Headless automation unblock + parallel dispatcher"**:
arregla el v1.0.4 LOCKED CRITICAL del CHANGELOG `[1.0.3]` Deferred
section — real headless detection eliminating the
`/receiving-code-review` interactive subprocess hang that blocked
v1.0.3 Activity D' + Activity E' empirical validation. Plus the
v1.0.3 LOCKED parallel task dispatcher per memory
`project_v104_parallel_task_dispatcher.md`. Plus methodology gap fix
(close-task phase auto-advance) surfaced empirically by both Track
Alpha + Track Beta v1.0.3 subagents.

Tres clases de items:

### Clase 1 — Pillar A PRIMARY (LOCKED CRITICAL)

- **Item A — Real headless detection for subprocess-incompatible
  skills**. Replace v1.0.1 `_SUBPROCESS_INCOMPATIBLE_SKILLS` whitelist
  + `allow_interactive_skill: bool` override hatch with proper
  detection via env var `SBTDD_HEADLESS=1` + `os.isatty(0)` checks.
  When `superpowers_dispatch.invoke_skill` detects truly headless
  context (env or non-TTY stdin) AND skill is interactive
  (brainstorming, writing-plans, receiving-code-review), raise
  `PreconditionError` LOUD-FAST instead of spawning subprocess that
  hangs for 600s. v1.0.1's whitelist + override pattern was a
  conservative baseline; v1.0.4 replaces with real detection.

  Audit + criteria for `_SUBPROCESS_INCOMPATIBLE_SKILLS` set
  membership (folded scope per CHANGELOG `[1.0.1]` Deferred to v1.0.4
  bundled-with-real-headless-detection): document the criteria for
  classifying a skill as subprocess-incompatible (interactive
  multi-turn dialogue requirement). Audit current set
  ({brainstorming, writing-plans}) + extend to add
  `receiving-code-review` empirically observed in v1.0.3 dogfood.

- **Item B — 600s subprocess hang full LOUD-FAST fix**. Tightly
  coupled with Item A: when interactive skill dispatched in headless
  context, raise PreconditionError IMMEDIATELY (no subprocess spawn,
  no 600s timeout wait). Operator gets clear guidance message
  pointing to `--resume-from-magi` recovery path (already shipped
  v1.0.1 A3) for spec phase, OR manual `/receiving-code-review`
  triage per spec sec.6.4 fallback for pre-merge phase.

  **Empirical evidence** v1.0.3:
  - Activity D' Loop 2: `/sbtdd pre-merge` hung after Loop 1 iter 1
    on `/receiving-code-review` subprocess waiting interactive input.
    Operator killed via Ctrl+C + manual fallback.
  - Activity E' deferred entirely because same hang would block
    `/sbtdd spec --resume-from-magi`.

### Clase 2 — Pillar B LOCKED (HIGH VALUE)

- **Item C — Parallel task dispatcher**. Per memory
  `project_v104_parallel_task_dispatcher.md`: codify the manual
  subagent-parallel pattern (precedent v0.4.0/v0.5.0/v1.0.0/v1.0.2/v1.0.3)
  as a plugin feature. New subcommand or flag on existing
  `/sbtdd auto` that:
  1. Analyzes plan DAG via `### Task N` blocks + dependency
     declarations (e.g. "after Task M" markers).
  2. Identifies parallelizable task batches (no shared file surfaces).
  3. Dispatches batch via Agent tool (multi-subagent parallel)
     instead of sequential single-subagent.
  4. MAGI Loop 2 fires ONCE at end on cumulative diff (vs sequential
     per-task currently).

  Reduces wall-time substantially (~40% per v0.4.0 + v0.5.0 + v1.0.0
  empirical observation).

### Clase 3 — Pillar C LOCKED defensive (methodology gap)

- **Item D — State file phase auto-advance methodology gap fix**.
  v1.0.3 dogfood empirically surfaced: Track Alpha + Track Beta both
  had to manually advance `current_phase` from `red` → `refactor` in
  `.claude/session-state.json` before invoking `close-task`, because
  plan's literal `git commit` commands (used by subagents per plan
  template) skip the `close-phase` wrapper that does phase advance.

  Two paths:
  - **Option A (recommended)**: extend `close-task` preflight to
    auto-advance phase from any non-`refactor` value to `refactor` if
    last verification was `passed`, with audit trail in state file.
    Backward-compatible (close-phase still primary path; close-task
    becomes more tolerant).
  - **Option B**: update plan template to mandate close-phase per
    Red/Green/Refactor commit (current convention is raw `git commit`).
    Higher friction; subagents historically diverge.

  Brainstorming evaluates Option A vs B based on subagent ergonomics +
  drift detector compatibility.

### Out of scope v1.0.4 (rolled forward a v1.0.5)

- **Audit GAPs from v1.0.3** (L1.0.4-A through L1.0.4-D) — Trigger
  criteria informational alignment, Carry-forward "Prior triage
  context" block emit path, Review summary artifact auto-emission,
  Per-project setup checklist template thinness. Defer to v1.0.5
  polish pillar per Balthasar v1.0.3 iter 3 INFO recommendation.
- **v1.0.3 deferred Items C/D/E** — drift detector line-anchored
  regex, spec-snapshot auto-regeneration, close-task convention
  codification. Defer to v1.0.5 per Balthasar v1.0.3 iter 3 INFO
  recommendation.

### Out of scope v1.0.4+ (rolled forward a v1.0.5+)

- `agreement_rate` field rename to `keep_rate` (schema bump).
- `spec_lint` R3 promote from warning to error severity.
- Per-module coverage raise to 85% baseline for `subprocess_utils.py`
  (74%) and `superpowers_dispatch.py` (83%).
- `pytest-cov` proper dev dep registration.
- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7 (opt-in flags).
- Migration tool real test (Feature I primer migration v1->v2).
- AST-based dead-helper detector codification.
- W8 Windows file-system retry-loop.
- `_read_auto_run_audit` skeleton wiring.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

### Criterio de exito v1.0.4

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.3 -> 1.0.4.
- Tests baseline 1105 + 1 skipped preservados sin regresion + ~25-40
  nuevos (Item A headless detection: ~10-15 incl. env var + isatty
  combinations + `_SUBPROCESS_INCOMPATIBLE_SKILLS` set extensions;
  Item B PreconditionError messages: ~3-5; Item C parallel dispatcher:
  ~10-15 incl. DAG analyzer + batch dispatch + cumulative-diff Loop
  2 wiring; Item D phase auto-advance: ~3-5).
- `make verify` runtime <= 165s (NF-A target; v1.0.3 baseline 151s;
  expected slight increase from new tests; soft-target <= 155s).
- Coverage threshold mantenido en 88% (per Q4 v1.0.2 baseline);
  no regression below 88%.
- **`/sbtdd spec --resume-from-magi` empirical validation
  end-to-end** in v1.0.4 own-cycle (deferred from v1.0.3 Activity E'
  per same hang bug; v1.0.4 fix unblocks this).
- **`/sbtdd pre-merge` empirical validation end-to-end** in v1.0.4
  own-cycle (deferred from v1.0.3 Activity D' partial completion;
  v1.0.4 fix unblocks Loop 1 fix-finding triage step).
- **Parallel task dispatcher empirical validation**: v1.0.4 own-cycle
  Track Alpha + Track Beta dispatched VIA THE NEW DISPATCHER (not
  manual Agent tool) to eat its own dogfood.
- v1.0.3 LOCKED carry-forward del CHANGELOG `[1.0.3]` Deferred
  (v1.0.4) section enteramente cerrados (real headless detection,
  parallel dispatcher, 600s hang fix, methodology gap).
- G1 binding respetado: cap=3 HARD para Checkpoint 2; sin INV-0.
  5-cycle no-override streak preserved (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4).
- G2 binding respetado: si Loop 2 iter 3 no converge clean,
  scope-trim default — defer Pillar C (Item D methodology gap) a
  v1.0.5; Pillar A + Pillar B son hard-LOCKED.
- v1.0.3 spec sec.6.1 iter-2 CRITICAL trigger preserved.

---

## 2. Alcance v1.0.4 — items LOCKED post-v1.0.3 ship

### 2.1 Item A — Real headless detection (Pillar A PRIMARY CRITICAL)

**Problema empirico v1.0.3**: `/sbtdd pre-merge` hung during Loop 1
fix-finding triage step on `/receiving-code-review` subprocess waiting
for interactive input. v1.0.1's `_SUBPROCESS_INCOMPATIBLE_SKILLS`
whitelist `{brainstorming, writing-plans}` + `allow_interactive_skill:
bool = False` kwarg in `invoke_skill` was conservative baseline; it
catches subprocess attempts BEFORE spawn for the 2 known-incompatible
skills, but `/receiving-code-review` was NOT in the set despite being
empirically interactive. Result: subprocess spawned, hung 600s, then
operator manual abort.

**Entrega v1.0.4**:

- Modify `superpowers_dispatch.invoke_skill` (or wrapper) to detect
  headless context BEFORE subprocess spawn:
  - `os.environ.get("SBTDD_HEADLESS") == "1"` ⇒ headless
  - `not sys.stdin.isatty()` AND `not os.environ.get("SBTDD_INTERACTIVE")` ⇒ headless
  - Otherwise interactive
- Extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set to include
  `receiving-code-review`. Document criteria in module docstring:
  skill is incompatible iff it requires multi-turn interactive
  dialogue (cannot complete in single non-interactive subprocess
  invocation).
- When headless context detected AND skill is in incompatible set,
  raise `PreconditionError(skill, recovery_path)` LOUD-FAST. Recovery
  path message points to:
  - For `brainstorming`/`writing-plans`: run skill manually in
    interactive Claude Code session, then use
    `/sbtdd spec --resume-from-magi`.
  - For `receiving-code-review`: run skill manually in interactive
    session OR fall back to manual `python skills/magi/scripts/run_magi.py`
    per spec sec.6.4 + apply mini-cycle TDD fixes manually.

- Backward compat: when `allow_interactive_skill=True` kwarg passed
  (existing override), preserve current behavior (let subprocess
  attempt). v1.0.1 wrappers (`brainstorming`, `writing_plans`) pass
  this internally; they continue working.

- Tests: ~10-15 covering env var combinations, isatty mock, set
  extension, recovery message correctness.

### 2.2 Item B — 600s subprocess hang full LOUD-FAST fix (Pillar A PRIMARY CRITICAL)

**Tightly coupled with Item A**. Once Item A's headless detection
fires `PreconditionError` BEFORE subprocess spawn, the 600s hang is
eliminated by construction. Item B contributes the message + recovery
guidance side.

**Entrega v1.0.4**:

- `PreconditionError` message format (when raised by Item A's
  headless gate):
  ```
  Skill `/<skill>` cannot run via `claude -p` subprocess in headless
  context (interactive dialogue required). Detected:
    SBTDD_HEADLESS=<env-value> | stdin.isatty()=<bool>
  Recovery options:
    1. Run `/<skill>` manually in an interactive Claude Code session,
       then [skill-specific recovery: `/sbtdd spec --resume-from-magi`
       OR manual `run_magi.py` fallback per spec sec.6.4].
    2. Set SBTDD_INTERACTIVE=1 if you ARE in interactive context but
       isatty() returns false (rare; e.g., piped script).
    3. Use the wrapper function (superpowers_dispatch.<skill>) which
       passes allow_interactive_skill=True automatically (advanced).
  ```

- Tests: ~3-5 covering message format + each recovery option's
  precondition resolution.

### 2.3 Item C — Parallel task dispatcher (Pillar B LOCKED HIGH VALUE)

**Problema**: v0.4.0 + v0.5.0 + v1.0.0 + v1.0.2 + v1.0.3 cycles
all manually dispatched 2-track parallel subagents via the orchestrator
Agent tool. Wall-time savings ~40% empirically observed. But the
pattern is unautomated — every cycle the orchestrator hand-codes
subagent prompts + tracks dispatch + coordinates state file +
synchronizes pre-merge. Plugin should automate this.

**Entrega v1.0.4** (per memory `project_v104_parallel_task_dispatcher.md`):

- Plan DAG analysis: parse `planning/claude-plan-tdd.md` for
  `### Task N` blocks + extract any `**Depends on**: Task M` declarations
  (or similar marker). Build directed acyclic graph of task
  dependencies. Identify maximal antichains (sets of tasks with no
  pairwise dependencies + no shared file surfaces).

- File surface collision detection: parse each task's `**Files:**`
  list. Tasks share a surface if any file appears in both lists.
  Surface-colliding tasks cannot run in same parallel batch.

- Batch dispatch: instead of sequential one-task-per-subagent, dispatch
  parallel-safe batch via Agent tool with N subagents concurrently.
  Wait for all to complete before next batch.

- Loop 2 cumulative-diff: MAGI Loop 2 fires ONCE at end of all task
  batches on cumulative diff (instead of per-task). Aligns with
  current /sbtdd pre-merge semantics.

- Backward compat: existing sequential `auto_cmd._task_loop` preserved
  as default. New `--parallel` flag (or `parallel: true` config)
  opts in.

- Tests: ~10-15 covering DAG parsing, antichain identification,
  surface collision detection, batch dispatch coordination,
  cumulative-diff Loop 2 wiring.

### 2.4 Item D — State file phase auto-advance (Pillar C LOCKED defensive)

**Problema empirico v1.0.3**: both Track Alpha + Track Beta subagents
had to manually edit `.claude/session-state.json` to advance
`current_phase` from `red` → `refactor` before invoking `close-task`,
because plan's literal `git commit` commands (per Q2 Option B v1.0.2
mandate) skip the `close-phase` wrapper that does phase advance.
Drift detector returned clean only because subagents knew about this
and applied workaround manually. Future cycles may diverge or drift.

**Entrega v1.0.4** (Option A path):

- Modify `close_task_cmd._preflight` to allow phase auto-advance:
  - If `current_phase == 'refactor'` ⇒ proceed normally (current
    behavior).
  - If `current_phase in {'red', 'green'}` AND
    `last_verification_result == 'passed'` ⇒ auto-advance to
    `refactor` with audit trail comment in state file
    (`auto_advanced_from: 'red'|'green'`). Then proceed.
  - If `current_phase` invalid (other state), raise
    `PreconditionError` per current behavior.

- Tests: ~3-5 covering each branch (refactor passthrough, red→refactor
  auto-advance, green→refactor auto-advance, invalid state error).

- Document in plan template (writing-plans skill prompt extension):
  subagents may invoke close-task directly without explicit
  close-phase preflight; phase advance happens automatically when
  verification was the most recent successful operation.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.4 NO propone
nuevos invariantes (los items son additive: detection logic +
dispatcher orchestration + state file convenience).

Critical durante implementacion v1.0.4:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  5-cycle no-override streak (v1.0.0+v1.0.1+v1.0.2+v1.0.3) — preserve.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.4 multi-pillar bundle (3 pillars) podria necesitar scope-trim
  si Loop 2 hits structural findings — defer Pillar C (Item D) a
  v1.0.5. Pillar A + Pillar B son hard-LOCKED.
- **Iter-2 CRITICAL trigger preserved** per spec sec.6.1: if
  Checkpoint 2 iter 2 still surfaces ANY CRITICAL, scope-trim
  immediately (defer Pillar C first).
- **Multi-pillar pero scope acotado** — 4 plan tasks (A+B coupled,
  C, D) + dogfood activities. Pillar A real headless + 600s LOUD-FAST
  is the cycle's primary CRITICAL deliverable.
- **`/receiving-code-review` MUST be exercised end-to-end** post Item
  A fix as empirical validation. v1.0.3 deferred this exercise; v1.0.4
  cycle MUST exercise it during Loop 1 fix-finding triage step.
- **Empirical validation requerida**:
  - Activity D' v1.0.3 retry: `/sbtdd pre-merge` end-to-end
    completion on Windows + cross-check artifacts produced + Loop 1
    fix-finding triage doesn't hang.
  - Activity E' v1.0.3 retry: `/sbtdd spec --resume-from-magi` true
    end-to-end exercise.
  - Parallel dispatcher dogfood: v1.0.4 own-cycle Track Alpha +
    Track Beta dispatched via the new Item C dispatcher, not manual
    Agent tool.

### Stack y runtime

Sin cambios vs v1.0.3:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot paths.
- Dependencias externas runtime: git, tdd-guard, superpowers, magi
  (>= 2.2.x), claude CLI.
- Dependencias dev: pytest, pytest-asyncio, pytest-cov >= 4.1, ruff,
  mypy, pyyaml.
- Licencia dual MIT OR Apache-2.0.

### Reglas duras no-eludibles (sin override)

- INV-0 autoridad global.
- INV-27 spec-base sin uppercase placeholder markers (este doc cumple).
- INV-37 (v1.0.1) composite-signature output validation tripwire.
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).
- G1 binding cap=3 HARD para Checkpoint 2 (CHANGELOG `[1.0.0]`,
  precedente cerrado v1.0.1+v1.0.2+v1.0.3 streak).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F144 v1.0.3; v1.0.4 starts at F145.)

### Item A — Real headless detection

**F145**. `superpowers_dispatch.invoke_skill` checks env var
`SBTDD_HEADLESS=1` BEFORE subprocess spawn.

**F146**. `superpowers_dispatch.invoke_skill` checks
`sys.stdin.isatty()` AND env var `SBTDD_INTERACTIVE` override BEFORE
subprocess spawn.

**F147**. `_SUBPROCESS_INCOMPATIBLE_SKILLS` set extended to include
`receiving-code-review`.

**F148**. Module docstring documents criteria: skill is incompatible
iff requires multi-turn interactive dialogue.

**F149**. When headless detected AND skill in incompatible set, raise
`PreconditionError` LOUD-FAST (before subprocess spawn).

**F150**. `allow_interactive_skill=True` kwarg preserved as override
(backward compat for v1.0.1 wrappers).

### Item B — 600s subprocess hang LOUD-FAST fix (coupled with A)

**F151**. PreconditionError message includes recovery options
(`/sbtdd spec --resume-from-magi`, manual run_magi.py, SBTDD_INTERACTIVE
env var, wrapper function override).

**F152**. Per-skill recovery message tailored to skill class
(spec-phase vs pre-merge-phase vs other).

### Item C — Parallel task dispatcher

**F153**. New module `skills/sbtdd/scripts/dag_parser.py` parses
`### Task N` blocks from plan + extracts dependency declarations.

**F154**. New module `skills/sbtdd/scripts/parallel_dispatcher.py`
identifies parallelizable batches via DAG antichain analysis +
file surface collision detection.

**F155**. `auto_cmd` accepts `--parallel` flag (or `parallel: true`
config); when set, dispatches batches via Agent tool concurrently.

**F156**. MAGI Loop 2 fires ONCE at end on cumulative diff (parallel
mode) vs per-task (sequential mode preserved as default).

**F157**. Sequential default preserves v1.0.3 behavior exactly.

### Item D — State file phase auto-advance

**F158**. `close_task_cmd._preflight` accepts `current_phase` in
`{red, green, refactor}` when `last_verification_result == 'passed'`.

**F159**. Auto-advance writes `auto_advanced_from: <prior_phase>`
field to state file for audit trail.

**F160**. Invalid `current_phase` values still raise
`PreconditionError` per existing behavior.

**F161**. Plan template documentation updated: subagents may invoke
close-task directly when verification passed, phase advance happens
automatically.

### Requerimientos no-funcionales (NF)

**NF37**. `make verify` runtime <= 165s (v1.0.3 baseline 151s;
v1.0.4 expected slight increase from ~25-40 nuevos tests + parallel
dispatcher tests; soft-target <= 155s).

**NF38**. v1.0.3 plans (with state file post-v1.0.3 schema) parse
correctly; no migration required for v1.0.4. State file
`auto_advanced_from` field is OPTIONAL (default None) for backward
compat.

**NF39**. Per-module coverage threshold preserved at 88% (no
regression below).

**NF40**. Item A headless detection works on Windows + POSIX
(detect via env var + isatty cross-platform).

**NF41**. Item C parallel dispatcher dogfood empirical validation
during v1.0.4 own-cycle (eat own dogfood).

---

## 5. Scope exclusions

Out-of-scope v1.0.4 (rolled forward a v1.0.5):

- **Audit GAPs from v1.0.3** (L1.0.4-A through L1.0.4-D):
  Trigger criteria informational, Carry-forward "Prior triage
  context" block emit, Review summary artifact auto-emission,
  Per-project setup checklist template thinness.
- **v1.0.3 deferred Items C+D+E**: drift detector line-anchored
  regex, spec-snapshot autoregen, close-task convention codification.

Out-of-scope v1.0.4+ (rolled forward a v1.0.5+):

- `agreement_rate` field rename to `keep_rate` (schema bump).
- `spec_lint` R3 promote to error severity.
- Per-module coverage raise to 85% baseline for outliers.
- `pytest-cov` proper dev dep registration.
- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7.
- Migration tool real test (Feature I primer migration v1->v2).
- AST-based dead-helper detector codification.
- W8 Windows file-system retry-loop.
- `_read_auto_run_audit` skeleton wiring.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

---

## 6. Criterios de aceptacion finales

v1.0.4 ship-ready cuando:

### 6.1 Functional Items A-D

- **F1**. F145-F150: real headless detection + recovery message +
  set extension to include receiving-code-review + backward compat
  for wrappers.
- **F2**. F151-F152: PreconditionError messages with per-skill
  recovery guidance.
- **F3**. F153-F157: parallel dispatcher (DAG parser + antichain
  identification + file surface collision detection + cumulative-diff
  Loop 2).
- **F4**. F158-F161: state file phase auto-advance + audit trail +
  plan template documentation.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 165s. Soft-target
  <= 155s.
- **NF-B**. Tests baseline 1105 + 1 skipped + ~25-40 nuevos =
  ~1130-1145 final.
- **NF-C**. Cross-platform (Windows + POSIX) — Item A headless
  detection validated on both via env var + isatty.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `superpowers_dispatch.py` (Item A+B),
  `close_task_cmd.py` (Item D), nuevos modulos (`dag_parser.py`,
  `parallel_dispatcher.py`), `auto_cmd.py` (Item C `--parallel`
  flag wiring).

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path. 5-cycle
  no-override streak preserved (becomes 6-cycle with v1.0.4 ship).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded. **`/sbtdd pre-merge`
  end-to-end completion** without subprocess hang (Item A+B
  validated empirically).
- **P3**. CHANGELOG `[1.0.4]` entry written con secciones Added /
  Changed / Process notes + Activity D' v1.0.3 retry findings +
  Activity E' v1.0.3 retry findings + parallel dispatcher dogfood
  observations.
- **P4**. Version bump 1.0.3 -> 1.0.4 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.4` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion. **P6 IS POSSIBLE for the first time
  via subprocess** post Item A+B fix.
- **P7**. `/sbtdd spec --resume-from-magi` exercised end-to-end
  during plan-approval phase (Activity E' retry from v1.0.3
  deferral).
- **P8**. `/sbtdd pre-merge` exercised end-to-end during pre-merge
  phase (Activity D' retry from v1.0.3 partial completion).
- **P9**. v1.0.4 own-cycle Track Alpha + Track Beta dispatched via
  Item C parallel dispatcher (not manual Agent tool) — dogfood eat-own.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.4 ship + 4 plan tasks
  across 3 pillars + dogfood activities).
- **D3**. Nuevos modulos + flags documentados:
  - `dag_parser.py` + `parallel_dispatcher.py` en README + SKILL.md.
  - `--parallel` flag en `auto_cmd` documented.
  - `SBTDD_HEADLESS` + `SBTDD_INTERACTIVE` env vars documented.
  - Phase auto-advance behavior documented in plan template.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.4

- **R1**. Item A real headless detection may be too strict and reject
  legitimate `claude -p` uses where the orchestrator IS in interactive
  context but isatty() returns false (rare: piped script wrapping
  claude CLI). Mitigation: `SBTDD_INTERACTIVE=1` env var override
  documented + tested.
- **R2**. Item A breaking behavior for callers that ignored the
  v1.0.1 whitelist warning and used `allow_interactive_skill=True`
  override liberally. Mitigation: backward compat preserved (override
  still works); audit existing callsites via test_invoke_skill_callsites_audit.py
  v1.0.2 meta-test (already enforces appropriate use).
- **R3**. Item C parallel dispatcher DAG analysis may misclassify
  tasks as parallel-safe when they have implicit dependencies (e.g.,
  Task N reads file Task M creates). Mitigation: file surface
  collision detection covers explicit `**Files:**` declarations;
  implicit dependencies surfaced via empirical dogfood (parallel
  dispatcher dogfood validates v1.0.4 own-cycle Track Alpha + Track
  Beta).
- **R4**. Item C cumulative-diff Loop 2 may consume more MAGI iter
  budget if cumulative diff is large vs per-task. Mitigation: spec
  sec.6.1 iter-2 CRITICAL trigger pre-stage + scope-trim ladder
  fallback.
- **R5**. Item D phase auto-advance may mask state file corruption
  bugs that close-phase explicit invocation would catch. Mitigation:
  audit trail field `auto_advanced_from` records the prior phase;
  drift detector inspects this field and surfaces unexpected patterns
  (e.g., red→refactor without intermediate green commit).
- **R6**. Bundle scope multi-pillar (3 pillars + dogfood) aumenta
  riesgo de Loop 2 non-convergence. Mitigation: G2 binding scope-trim
  ladder defer Pillar C (Item D) a v1.0.5 si Loop 2 iter 3 no
  converge.
- **R7**. Item C parallel dispatcher own-cycle dogfood may surface
  edge cases not covered by tests (concurrent state file write,
  Agent tool race conditions). Mitigation: v1.0.4 cycle uses
  sequential dispatch as fallback if parallel dogfood surfaces
  blocking issue; document as v1.0.5+ refinement.
- **R8**. Item A `_SUBPROCESS_INCOMPATIBLE_SKILLS` set extension
  may surface MORE skills empirically incompatible (e.g.,
  `verification-before-completion`?). Mitigation: audit doc in Item A
  Step 1 documents criteria + current set; v1.0.4+ extends as
  empirically observed.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.3 ship record: tag `v1.0.3` (commit `39a9c18`); merge
  `0aeff7d` on `main`.
- v1.0.2 ship record: tag `v1.0.2` (commit `80731e6`); merge
  `3169767` on `main`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.3 LOCKED carry-forward to v1.0.4: ver CHANGELOG `[1.0.3]`
  Process notes + Deferred (rolled to v1.0.4) section. CRITICAL
  unblocking item: real headless detection.
- v1.0.4 LOCKED memories:
  - `project_v104_subprocess_headless_detection.md` (CRITICAL).
  - `project_v104_parallel_task_dispatcher.md` (HIGH VALUE).
- v1.0.5 deferred backlog: audit GAPs L1.0.4-A through L1.0.4-D from
  v1.0.3 audit + Items C/D/E from v1.0.3 deferral. Bundle as v1.0.5
  polish pillar per Balthasar v1.0.3 iter 3 INFO recommendation.
- Branch: trabajo en `feature/v1.0.4-bundle` (branched off `main`
  HEAD `0aeff7d` = v1.0.3 merge commit).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.4 own-cycle**: per CLAUDE.local.md §1 Flujo de
especificacion + v1.0.1+v1.0.2+v1.0.3 Process notes precedent,
brainstorming se correra en sesion interactiva (esta sesion), NO via
`claude -p` subprocess (consistencia con Finding A precedent — IRONIC
since v1.0.4 ships the real headless detection that fixes this; but
the v1.0.4 own-cycle itself ships before the fix lands so the
workaround applies).

**Hybrid methodology continued**: Opcion A manual `run_magi.py` for
Checkpoint 2 dispatch per v1.0.2 + v1.0.3 precedent. Opcion B
`/sbtdd spec --resume-from-magi` exercised AS Activity E' empirical
validation during plan-approval phase (deferred from v1.0.3).

Decisiones pendientes clave para brainstorming:

1. **Subagent partition**: 4 plan items (A, B coupled with A; C; D)
   + dogfood activities. Posibles particiones disjoint:
   - **Single subagent sequential**: ~5-6 dias wall-time.
   - **2-track parallel** (precedent v1.0.3): Track Alpha = A+B
     coupled (real headless detection + LOUD-FAST messages); Track
     Beta = C parallel dispatcher + D phase auto-advance.
     Methodology activities orchestrator post Track-close.
   - **3-track parallel** (riesgo overhead): Track Alpha = A+B,
     Track Beta = C, Track Gamma = D. Higher coordination.
   Brainstorming evalua basado en complejidad + Item C complexity
   (parallel dispatcher likely ~2-3 days alone).

2. **Item C parallel dispatcher API surface**: subcommand vs flag.
   `--parallel` flag on existing `/sbtdd auto` is simpler (no new
   subcommand) but couples parallel dispatch to auto-mode. New
   subcommand `/sbtdd parallel-dispatch` is cleaner separation but
   adds plugin surface. Brainstorming chooses based on usage pattern.

3. **Item D phase auto-advance Option A vs B**: Option A close-task
   tolerates non-refactor phase; Option B mandate close-phase per
   commit. Option A favored per spec-base (subagent ergonomics) but
   Option B is more strict.

4. **Activity E' true exercise sequencing**: pre-Track-close (validate
   --resume-from-magi works pre-impl) vs post-Track-close (validate
   it works post-impl). v1.0.3 deferred entirely; v1.0.4 first
   true exercise.

5. **MAGI Checkpoint 2 budget allocation**: bundle multi-pillar but
   focused. Esperamos converger en 1-2 iters; iter 3 triggers G2
   scope-trim default (defer Pillar C to v1.0.5 si needed).

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0+v1.0.1+v1.0.2+v1.0.3 precedents.
