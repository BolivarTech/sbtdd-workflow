# Especificacion base — sbtdd-workflow v1.0.3 (post-v1.0.2 ship)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.3).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-06 post-v1.0.2 ship (tag `v1.0.2` at commit `80731e6`,
> branch `feature/v1.0.3-bundle` branched off `main` HEAD `3169767` =
> v1.0.2 merge commit).
>
> v1.0.3 es **multi-pillar**: el original sole-pillar scope (MAGI gate
> template alignment audit per memory `project_v103_template_alignment_audit.md`)
> mas items de carry-forward del v1.0.2 ship process notes (cross-check
> Windows long-filename fix, drift detector tightening, spec-snapshot
> auto-regen, subagent close-task convention) mas methodology
> activities pendientes (Activity D Linux/POSIX dogfood, Activity E
> true `--resume-from-magi` end-to-end).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este
> documento NO lo reemplaza — agrega el delta v1.0.3 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex.
>
> v1.0.3 G1 binding HARD: cap=3 sin INV-0 path para Checkpoint 2
> (precedente cerrado v1.0.0+v1.0.1+v1.0.2 = 2-streak no-override post
> v1.0.0 last-allowed). G2 binding: scope-trim default si Loop 2 iter 3
> no converge (defer Pillar C + methodology a v1.0.4 si necesario).

---

## 1. Objetivo

**v1.0.3 = "Template alignment + v1.0.2 dogfood remediations"**: completa
la auditoria LOCKED original (MAGI gate template alignment) + arregla
los gaps de infraestructura que el v1.0.2 own-cycle dogfood surfaced,
preparando baseline aligned para v1.0.4 (parallel dispatcher + real
headless detection).

Cuatro clases de items:

### Clase 1 — Pillar A PRIMARY (LOCKED, original sole-pillar)

- **Item A — MAGI gate template alignment audit** (per memory
  `project_v103_template_alignment_audit.md` + user directive
  2026-05-03). Auditoria seccion-por-seccion del plugin's MAGI cycle
  contra `D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md`
  (411 lines, synthesized 2026-05-01 from sbtdd-workflow + MAGI
  empirical learnings). Deliverable:
  - `docs/audits/v1.0.3-magi-gate-template-alignment.md` con tabla
    seccion-por-seccion: TEMPLATE_SECTION | PLUGIN_IMPL_PATH |
    STATUS (MATCH | GAP | OBSOLETE) | EVIDENCE | ACTION.
  - GAP items resueltos en plan TDD subsiguientes (code change,
    documentation update, o template amendment per item).
  - Cross-artifact alignment test (similar a v0.4.x HF1 canonical
    wording pattern) que grep template para required strings
    presentes en plugin's MAGI dispatch path code.
  - `templates/CLAUDE.local.md.template` actualizado si alignment
    shift el template contract.
  - `CLAUDE.local.md` template version bump si el contrato cambia.

  Sections to audit per template:
  1. Trigger criteria match (`pre_merge_cmd._loop2` +
     `auto_cmd._phase4` mandatory vs optional MAGI classification).
  2. Pass threshold logic (`magi_dispatch.invoke_magi` +
     `verdict_passes_gate` honor template's verdict-action table).
  3. Carry-forward format (orchestrator injects "Prior triage
     context" block into iter N+1 payload per template format).
  4. Review summary artifact emission
     (`docs/reviews/<feature>-review-summary.md` per-cycle).
  5. Cost awareness (`auto_skill_models` per-skill model selection
     Haiku/Opus per template recommendation).
  6. Per-project setup checklist (`templates/CLAUDE.local.md.template`
     `{placeholder}` markers match template requirements).

### Clase 2 — Pillar B LOCKED secondary (v1.0.2 critical infrastructure carry-forward)

- **Item B — Cross-check Windows long-filename infrastructure fix**
  (v1.0.2 ship process notes carry-forward; deferred per memory
  `project_v102_shipped.md`). v1.0.2 dogfood revealed `WinError 206
  filename too long` fired during all 3 Loop 2 iters, preventing
  cross-check meta-reviewer from running on Windows. Root cause is
  Windows `MAX_PATH` limit hit by cross-check temp directory layout
  (`C:\Users\...\AppData\Local\Temp\sbtdd-magi-<8chars>\` + nested
  files). Fix candidates:
  - Shorter temp dir prefix (e.g. `\sbtdd-x<2chars>\`).
  - `\\?\` long-path syntax wrapping for Windows file operations.
  - Move cross-check temp dir to project-relative path
    (`.claude/magi-cross-check/.tmp/`) with shorter base.

  Deliverable: cross-check meta-reviewer succeeds end-to-end on
  Windows (verifiable via Activity D dogfood in v1.0.3 own-cycle).

### Clase 3 — Pillar C LOCKED defensive (v1.0.2 small infrastructure fixes)

- **Item C — Drift detector line-anchored match**. v1.0.2
  surfaced false-positive: `drift._plan_all_tasks_complete` uses
  substring `"- [ ]" in plan_text[start:end]` which matches inline
  backtick prose mentions of `\`- [ ]\``. Fix: switch to
  `re.search(r'^- \[ \]', section, re.MULTILINE)` (line-anchored).
- **Item D — Spec-snapshot auto-regeneration**. v1.0.2 surfaced
  manual-regenerate friction: `planning/spec-snapshot.json` carried
  v1.0.1 escenarios into v1.0.2 cycle, requiring manual regenerate
  during pre-merge debug. Fix: `spec_cmd._run_magi_checkpoint2`
  (post-MAGI-pass branch) auto-regenerates `spec-snapshot.json` +
  updates `state_file.spec_snapshot_emitted_at`.
- **Item E — Subagent close-task convention clarification**. v1.0.2
  subagents marked task headings (`### Task N: ... [x]`) instead of
  step checkboxes (`- [ ]` → `- [x]`). Fix:
  - Update plan template (`templates/claude-plan-tdd.md.template`
    if exists, or document in plan generation guidance) with
    explicit per-step checkbox convention.
  - OR document the heading-mark convention as alternative + update
    drift detector + spec_lint to handle both.
  - OR codify automation via `/sbtdd close-task` invocation
    (existing subcommand) so subagents don't manually edit plan.

### Clase 4 — Methodology activities (v1.0.2 carry-forward)

- **Activity D' — Activity D Linux/POSIX dogfood completion**. v1.0.2
  Activity D failed on Windows (Pillar B above). Once Pillar B fix
  lands, repeat Activity D in v1.0.3 own-cycle to validate
  cross-check infrastructure works cross-platform.
- **Activity E' — Activity E true `--resume-from-magi` end-to-end**.
  v1.0.2 deferred true E2E exercise because state was post-impl.
  v1.0.3 cycle CAN exercise it during plan-approval phase BEFORE
  Track dispatch.

### Criterio de exito v1.0.3

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.2 -> 1.0.3.
- Tests baseline 1093 + 1 skipped preservados sin regresion + ~20-35
  nuevos (Item A audit + alignment test ~5-8; Item B cross-check
  Windows fix tests ~5-8; Item C drift detector regression ~3-5;
  Item D spec-snapshot autoregen tests ~3-5; Item E doc update sin
  tests; methodology empirical).
  Spec sec.10.4 NF-B target: +20-35 nuevos = 1113-1128 final.
- `make verify` runtime <= 160s (v1.0.2 baseline 144s; expected
  slight increase from new tests; soft-target <= 150s).
- Coverage threshold mantenido en 88% (per Q4 v1.0.2 baseline);
  no regression below 88%.
- **Activity D Linux/POSIX dogfood validated** end-to-end con
  `magi_cross_check: true` + cross-check meta-reviewer artifacts
  produced + telemetry script consumed empirically.
- **Activity E true `--resume-from-magi` validated** end-to-end
  during plan-approval phase.
- v1.0.2 LOCKED carry-forward del CHANGELOG `[1.0.2]` Deferred
  (v1.0.3) section enteramente cerrados.
- G1 binding respetado: cap=3 HARD para Checkpoint 2; sin INV-0.
- G2 binding respetado: si Loop 2 iter 3 no converge clean,
  scope-trim default — defer Pillar C (Items C+D+E) a v1.0.4 si
  necesario; Pillar A + Pillar B son hard-LOCKED per cycle scope.

### Out of scope v1.0.3 (rolled forward a v1.0.4)

- Parallel task dispatcher (memory
  `project_v104_parallel_task_dispatcher.md`).
- Real headless detection (env var `SBTDD_HEADLESS=1` + `os.isatty(0)`)
  replacing v1.0.1's whitelist + `allow_interactive_skill` override
  (memory `project_v104_subprocess_headless_detection.md`).
- `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit + criteria for set
  membership (bundled with v1.0.4 LOCKED real headless detection).
- 600s subprocess hang full LOUD-FAST fix (bundled with v1.0.4
  headless detection).

### Out of scope v1.0.3+ (rolled forward a v1.0.5+)

- `agreement_rate` field rename to `keep_rate` (Loop 2 iter 3
  caspar API consideration; would require schema_version bump per
  Feature I migration tool).
- `spec_lint` R3 monotonic headers severity promote from warning
  to error (Q3 v1.0.2 brainstorming + Loop 2 iter 3 caspar
  suggestion; collect empirical false-positive data first).
- Per-module coverage raise to 85% baseline for `subprocess_utils.py`
  (74%) and `superpowers_dispatch.py` (83%).
- `pytest-cov` registered as proper dev dep (Loop 2 iter 3 caspar
  INFO 14 — `tomli` install in Task 17 step 4 fallback verification
  isn't recorded in dev-deps).
- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7 (opt-in flags).
- Migration tool real test (Feature I primer migration v1->v2).
- AST-based dead-helper detector codification (R11 sweep methodology).
- W8 Windows file-system retry-loop (accepted-risk).
- `_read_auto_run_audit` skeleton wiring.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

---

## 2. Alcance v1.0.3 — items LOCKED post-v1.0.2 ship

### 2.1 Item A — MAGI gate template alignment audit (Pillar A PRIMARY)

**Problema**: el plugin's MAGI cycle (sbtdd-workflow's
`pre_merge_cmd._loop2`, `magi_dispatch.invoke_magi`,
`_loop2_with_cross_check`, carry-forward block builder, etc.) ha
evolucionado organicamente a traves de v0.5.0 + v1.0.0 + v1.0.1 +
v1.0.2 cycles. El template canonical
`magi-gate-template.md` (411 lines, 2026-05-01) fue synthesized DESDE
estas mismas empirical learnings, pero el plugin no ha sido
explicitamente auditado para alineamiento contra el template tal cual.
Risk: drift entre template (canonical procedure) y plugin (actual
enforcement) sin nadie notando — el plugin podria estar enforcing
rules que el template no menciona, o NO enforcing rules que el
template considera mandatory.

**Entrega v1.0.3**:

- Nuevo audit document `docs/audits/v1.0.3-magi-gate-template-alignment.md`
  con tabla seccion-por-seccion del template:

  | Template Section | Plugin Impl Path | Status | Evidence | Action |
  |------------------|------------------|--------|----------|--------|
  | Trigger criteria | `pre_merge_cmd._loop2:NNN` | MATCH/GAP/OBSOLETE | file:line | code/doc fix |
  | Pass threshold | `magi_dispatch.verdict_passes_gate:NNN` | ... | ... | ... |
  | Carry-forward format | `pre_merge_cmd._build_carry_forward:NNN` | ... | ... | ... |
  | Review summary artifact | (none yet?) | likely GAP | manual-only | auto-emit |
  | Cost awareness | `config.auto_skill_models` | ... | ... | ... |
  | Per-project setup | `templates/CLAUDE.local.md.template` | ... | ... | ... |

- For each GAP: code change in plugin OR documentation update OR
  template amendment per side-of-truth.
- Cross-artifact alignment test
  `tests/test_magi_template_alignment.py` que grep template para
  required strings + asserta presence en plugin's dispatch path
  (similar a `test_changelog.py` HF1 canonical wording pattern).
- `templates/CLAUDE.local.md.template` actualizado si alignment
  shifts el contract.
- CHANGELOG `[1.0.3]` Process notes documenta GAP/MATCH stats +
  fixes applied.

### 2.2 Item B — Cross-check Windows long-filename fix (Pillar B LOCKED)

**Problema empirico v1.0.2**: durante Activity D dogfood, todos los
3 Loop 2 iters surfaced:

```
[sbtdd magi-cross-check] failed (will fall back to MAGI findings as-is): [WinError 206] The filename or extension is too long
```

Resultado: cross-check meta-reviewer NO se ejecuto durante v1.0.2
Loop 2; sistema fell back to MAGI findings as-is (Feature G graceful
fallback per G5). v1.0.2's own Item D could NOT validate cross-check
infrastructure empirically on Windows.

**Root cause**: cross-check temp directory layout uses long paths.
Cuando `pre_merge_cmd._loop2_with_cross_check` invokes
`/requesting-code-review` via subprocess + writes prompt + diff to
temp file under `C:\Users\<userlong>\AppData\Local\Temp\sbtdd-magi-<8chars>\`
+ nested paths, total path length exceeds Windows MAX_PATH (260
chars).

**Entrega v1.0.3**:

- Identificar exact path construction en `pre_merge_cmd._loop2_cross_check`
  o downstream (probablemente `_dispatch_requesting_code_review` o
  `subprocess_utils` helpers).
- Apply mitigation: shorter temp dir prefix OR `\\?\` long-path
  syntax OR project-relative temp dir
  (`.claude/magi-cross-check/.tmp/<run-id>/`).
- Test que reproduce error on Windows (con synthetic long path) +
  asserts fix resolves.
- Validate empirically en v1.0.3 own-cycle Activity D Linux/POSIX
  dogfood (Activity D' below).

### 2.3 Item C — Drift detector line-anchored match (Pillar C defensive)

**Problema empirico v1.0.2**: `drift._plan_all_tasks_complete` uses
substring match `"- [ ]" in plan_text[start:end]` que detecta inline
backtick prose mentions de checkbox literal como falsos pendientes.
v1.0.2 hit during pre-merge dispatch:

```
DriftError: drift detected: state=done, HEAD=chore:, plan=[ ]
```

Trigger: 2 inline `\`- [ ]\`` mentions en plan-tdd.md (lineas 8 +
2238 documenting checkbox convention). Workaround: sanitizar prose.
Fix permanente: line-anchored regex.

**Entrega v1.0.3**:

- Modificar `drift._plan_all_tasks_complete` (file:line en module)
  para usar `re.search(r'^- \[ \]', section, re.MULTILINE)` instead
  of substring `in`.
- Regression test en `tests/test_drift.py` con fixture plan que
  contiene inline backtick prose mentions + asserts no false-positive
  drift.
- Backward compat: existing fixtures con real `- [ ]` checkboxes
  siguen detectando drift correctamente.

### 2.4 Item D — Spec-snapshot auto-regeneration (Pillar C defensive)

**Problema empirico v1.0.2**: `planning/spec-snapshot.json` carried
v1.0.1 escenarios (A0/A1/A2/A3 series) into v1.0.2 cycle. Required
manual regeneration via direct `python -c "import spec_snapshot;
spec_snapshot.emit_snapshot(...)"` during pre-merge debug. Resulted
in `MAGIGateError: Spec scenarios changed since plan approval`
during first pre-merge attempt v1.0.2 cycle.

**Entrega v1.0.3**:

- Modificar `spec_cmd._run_magi_checkpoint2` post-MAGI-pass branch
  (after verdict >= GO_WITH_CAVEATS confirmed) para:
  1. Invoke `spec_snapshot.emit_snapshot(spec_behavior_path)`.
  2. Persist via `spec_snapshot.persist_snapshot(snapshot,
     planning_dir / 'spec-snapshot.json')`.
  3. Update `state_file.spec_snapshot_emitted_at = <timestamp>`.
- Test que dispatcheado MAGI + verdict pass auto-regenerates the
  snapshot file with current escenarios + state file timestamp.

### 2.5 Item E — Subagent close-task convention clarification (Pillar C defensive)

**Problema empirico v1.0.2**: subagents marcaron task headings
(`### Task 1: ... [x]`) en lugar de per-step checkboxes
(`- [ ]` → `- [x]`). Drift detector + spec_lint expect
per-step checkboxes per the convention documented en plan I5
Process notes pero subagents diverged.

**Entrega v1.0.3**:

- Decision branch:
  - **Option A**: Update plan template guidance + writing-plans
    skill prompt extension to be explicit about per-step convention.
    Document with one-line example.
  - **Option B**: Codify via `/sbtdd close-task` automation —
    require subagents to invoke this subcommand (which mutates
    state file + plan checkboxes correctly) instead of editing plan
    manually.
  - **Option C**: Make drift detector tolerant to BOTH conventions
    (per-step OR heading-mark).
- Brainstorming will pick best option per cost/risk/durability.
- Deliverable: implementation per chosen option + plan template +
  documentation update.

### 2.6 Activity D' — Linux/POSIX dogfood completion (methodology)

**Problema**: v1.0.2 Activity D failed on Windows (Item B above);
cross-check infrastructure unvalidated empirically.

**Entrega v1.0.3**:

- After Item B Pillar B fix lands, exercise Activity D again in
  v1.0.3 own-cycle:
  1. `magi_cross_check: true` already set in `plugin.local.md`.
  2. Run `/sbtdd pre-merge` end-to-end.
  3. Verify cross-check meta-reviewer ejecuta sin WinError 206.
  4. Capture `.claude/magi-cross-check/iter*-*.json` artifacts
     (real, not synthetic).
  5. Run `python scripts/cross_check_telemetry.py` on artifacts.
- Document findings en CHANGELOG `[1.0.3]` Process notes.

### 2.7 Activity E' — True `--resume-from-magi` end-to-end (methodology)

**Problema**: v1.0.2 Activity E was structurally inappropriate
post-implementation; equivalent code path exercised but flag-specific
path NOT directly invoked.

**Entrega v1.0.3**:

- During v1.0.3 plan-approval phase (BEFORE Track dispatch), exercise
  `/sbtdd spec --resume-from-magi`:
  1. Hand-craft spec-behavior.md + plan-tdd-org.md interactivamente
     (this session).
  2. Pre-flight spec_lint dry-run (W5 v1.0.1 fix preserved).
  3. Invoke `python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi`.
  4. Verify post-conditions: skipea brainstorming/writing-plans
     dispatch, ejecuta MAGI Checkpoint 2 sobre artifacts, escribe
     state file + commit chore.
- Document end-to-end wall-clock + observable gaps in CHANGELOG
  `[1.0.3]` Process notes.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.3 NO propone
nuevos invariantes (los items son additive: audit, infrastructure
fix, drift detector tightening, autoregen, convention clarification).

Critical durante implementacion v1.0.3:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  3-cycle no-override streak (v1.0.0 + v1.0.1 + v1.0.2) — preserve.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.3 multi-pillar bundle podria necesitar scope-trim si Loop 2
  hits structural findings — defer Pillar C (Items C+D+E) +
  methodology activities a v1.0.4.
- **Multi-pillar pero scope acotado** — 5 plan tasks (A, B, C, D, E)
  + 2 methodology activities (D', E'). Pillar A audit + Pillar B
  Windows fix son hard-LOCKED per cycle scope.
- **Invocation-site tripwires**: cualquier helper nuevo (alignment
  test, snapshot autoregen, drift line-anchored regex) ships con
  invocation-site tripwire test ANTES de close-task.
- **`/receiving-code-review` sin excepcion**: every Loop 2 iter
  MUST run skill on findings (carry-forward from v1.0.2; per
  template alignment Item A audit will validate this).
- **Empirical validation requerida**: Activity D' + Activity E' son
  empirical-only (no ship sin observed dogfood result + recovery
  exercise success).

### Stack y runtime

Sin cambios vs v1.0.2:
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
  precedente cerrado v1.0.1+v1.0.2 streak).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F123 v1.0.2; v1.0.3 starts at F124.)

### Item A — Template alignment audit

**F124**. `docs/audits/v1.0.3-magi-gate-template-alignment.md` exists
con tabla seccion-por-seccion completa per template's 6 sections.

**F125**. Each row includes Status (MATCH | GAP | OBSOLETE) +
Evidence (file:line citation) + Action (resolved or deferred).

**F126**. `tests/test_magi_template_alignment.py` cross-artifact
test asserts required strings from template present en plugin's
dispatch path code (similar to test_changelog.py HF1 pattern).

**F127**. GAP items resueltos via code change (in plugin) OR
documentation update (in template) OR amendment (in
`templates/CLAUDE.local.md.template`).

### Item B — Cross-check Windows long-filename fix

**F128**. Identify exact path construction triggering WinError 206 +
document in audit.

**F129**. Apply fix (shorter prefix OR `\\?\` syntax OR
project-relative temp dir).

**F130**. Reproduction test that synthetic long path triggers error
pre-fix; post-fix passes.

**F131**. Activity D' empirical validation: cross-check meta-reviewer
ejecuta end-to-end on Windows during v1.0.3 own-cycle Loop 2.

### Item C — Drift detector line-anchored match

**F132**. `drift._plan_all_tasks_complete` uses
`re.search(r'^- \[ \]', section, re.MULTILINE)` instead of substring.

**F133**. Regression test fixture con inline backtick prose mentions
de checkbox literal + asserts NO false-positive drift.

**F134**. Backward compat: existing real-checkbox fixtures siguen
detectando drift.

### Item D — Spec-snapshot auto-regeneration

**F135**. `spec_cmd._run_magi_checkpoint2` post-MAGI-pass branch
auto-regenerates `planning/spec-snapshot.json`.

**F136**. State file `spec_snapshot_emitted_at` updated to current
timestamp on autoregen.

**F137**. Test asserts dispatcheado MAGI verdict pass auto-emits
snapshot + updates state file.

### Item E — Close-task convention clarification

**F138**. Decision documented (Option A / B / C per sec.2.5) + impl
landed.

**F139**. Plan template + writing-plans guidance + `/sbtdd close-task`
documentation reflect chosen convention.

### Activity D' — Linux/POSIX dogfood

**F140**. v1.0.3 cycle runs `/sbtdd pre-merge` end-to-end with
`magi_cross_check: true`; cross-check meta-reviewer runs without
WinError 206.

**F141**. Real `iter*-*.json` artifacts captured in
`.claude/magi-cross-check/`.

**F142**. Telemetry script (Item A v1.0.2 ship) consumed empirically
on real artifacts; output documented in CHANGELOG `[1.0.3]`.

### Activity E' — True `--resume-from-magi` end-to-end

**F143**. v1.0.3 cycle exercises `/sbtdd spec --resume-from-magi`
during plan-approval phase; flag-specific code path validated
empirically.

**F144**. CHANGELOG `[1.0.3]` Process notes documenta wall-clock +
gaps observed.

### Requerimientos no-funcionales (NF)

**NF33**. `make verify` runtime <= 160s (v1.0.2 baseline 144s; v1.0.3
expected slight increase from new tests; soft-target <= 150s).

**NF34**. v1.0.2 plans (with state file post-v1.0.2 schema) parse
correctly; no migration required for v1.0.3.

**NF35**. Per-module coverage threshold preserved at 88% (no
regression below).

**NF36**. Cross-check Windows fix works with paths >= 300 chars (not
just synthetic short paths).

---

## 5. Scope exclusions

Out-of-scope v1.0.3 (rolled forward a v1.0.4):

- Parallel task dispatcher.
- Real headless detection (env var + os.isatty replacing whitelist).
- `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit + criteria.
- 600s subprocess hang full LOUD-FAST fix.

Out-of-scope v1.0.3+ (rolled forward a v1.0.5+):

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

v1.0.3 ship-ready cuando:

### 6.1 Functional Items A-E + Activities D'-E'

- **F1**. F124-F127: template alignment audit document + alignment
  test + GAP fixes.
- **F2**. F128-F131: Windows long-filename fix + reproduction test
  + empirical Activity D' validation.
- **F3**. F132-F134: drift detector line-anchored regex + regression
  + backward compat.
- **F4**. F135-F137: spec-snapshot autoregen + state file update +
  test.
- **F5**. F138-F139: close-task convention decision + impl + docs.
- **F6**. F140-F142: Activity D' Linux/POSIX dogfood empirical
  validation + telemetry consumption.
- **F7**. F143-F144: Activity E' true `--resume-from-magi` empirical
  validation.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 160s. Soft-target
  <= 150s.
- **NF-B**. Tests baseline 1093 + 1 skipped + ~20-35 nuevos =
  ~1113-1128 final.
- **NF-C**. Cross-platform (Windows + POSIX) — Item B specifically
  validates Windows.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `pre_merge_cmd.py` (Item B fix + possible Item A GAP
  fixes), `spec_cmd.py` (Item D autoregen integration), `drift.py`
  (Item C regex), `magi_dispatch.py` (possible Item A GAP fixes),
  `templates/CLAUDE.local.md.template` (Item A amendment if
  alignment shifts contract).

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path. 3-cycle
  no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.3]` entry written con secciones Added /
  Changed / Process notes + Activity D' empirical findings +
  Activity E' empirical findings + template alignment GAP/MATCH
  stats.
- **P4**. Version bump 1.0.2 -> 1.0.3 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.3` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. Activity D' Linux/POSIX dogfood: cross-check infrastructure
  validated empirically.
- **P8**. Activity E' true `--resume-from-magi` end-to-end exercised
  during plan-approval phase.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.3 ship + 5 plan tasks
  + 2 methodology activities + audit document).
- **D3**. Nuevos modulos documentados:
  - `docs/audits/v1.0.3-magi-gate-template-alignment.md` (audit
    artifact).
  - `tests/test_magi_template_alignment.py` (alignment test).
  - Item B cross-check Windows fix changes documented in CHANGELOG.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva (pytest-cov ya en v1.0.2).

---

## 8. Risk register v1.0.3

- **R1**. Item A audit may surface MANY gaps (template was
  synthesized FROM plugin learnings, but plugin has continued to
  evolve through v1.0.0+v1.0.1+v1.0.2). Mitigation: prioritize gaps
  by severity (CRITICAL = template requires + plugin doesn't enforce;
  WARNING = plugin enforces stricter than template); defer
  non-critical gaps to v1.0.4+.
- **R2**. Item B Windows fix may require deeper changes than
  expected if path construction is spread across multiple modules.
  Mitigation: if scope spike beyond 1 day, reduce Item B to "document
  the issue + apply minimum viable fix (shorter prefix only)" + defer
  full `\\?\` syntax to v1.0.4.
- **R3**. Item C drift detector line-anchored regex may break
  existing test fixtures that rely on substring match behavior.
  Mitigation: thorough regression test suite covering both true
  positives + false positives.
- **R4**. Item D spec-snapshot autoregen may interact unexpectedly
  with Activity E' `--resume-from-magi` flow (re-running checkpoint
  re-emits snapshot). Mitigation: Activity E' empirical validation
  catches this; if surfaces, adjust autoregen to skip when
  `--resume-from-magi` flag detected.
- **R5**. Item E close-task convention decision may surface
  fundamental disagreement between subagent ergonomics + drift
  detector requirements. Mitigation: pick conservative option
  (Option A documentation update + drift detector tolerant to both
  conventions per Option C) for v1.0.3; codify via `/sbtdd close-task`
  automation as v1.0.4+ candidate.
- **R6**. Bundle scope multi-pillar con 7 items aumenta riesgo de
  Loop 2 non-convergence. Mitigation: G2 binding scope-trim ladder
  defer Pillar C (Items C+D+E) + methodology activities (D'+E') a
  v1.0.4 si Loop 2 iter 3 no converge.
- **R7**. Activity D' could fail again if Item B fix is incomplete;
  Activity E' could fail if `--resume-from-magi` path has regression.
  Mitigation: methodology activities are non-blocking for ship —
  document failures in CHANGELOG + defer to v1.0.4 retry.
- **R8**. Template alignment may reveal that template itself has
  defects (was synthesized hastily 2026-05-01). Mitigation: audit
  doc allows "template amendment" as Action; if template is wrong,
  update template (D:\jbolivarg\BolivarTech\AI_Tools\) instead of
  plugin.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.2 ship record: tag `v1.0.2` (commit `80731e6`); merge
  `3169767` on `main`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.2 LOCKED carry-forward to v1.0.3: ver CHANGELOG `[1.0.2]`
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
- Branch: trabajo en `feature/v1.0.3-bundle` (branched off `main`
  HEAD `3169767` = v1.0.2 merge commit).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.3 own-cycle**: per CLAUDE.local.md §1 Flujo de
especificacion + v1.0.2 Process notes precedent, brainstorming se
correra en sesion interactiva (esta sesion), NO via `claude -p`
subprocess (consistencia con Finding A precedent que se mantiene
hasta v1.0.4 real headless detection).

Decisiones pendientes clave para brainstorming:

1. **Subagent partition**: 5 plan items (A, B, C, D, E) + 2
   methodology (D', E'). Posibles particiones disjoint:
   - **Single subagent sequential**: ~3-4 dias wall-time.
   - **2-subagent parallel**: Track Alpha = A (audit doc + alignment
     test) + B (Windows fix). Track Beta = C (drift) + D (autoregen)
     + E (close-task convention). Methodology D'+E' mid-cycle.
   - **3-subagent parallel** (riesgo overhead): Track Alpha = A,
     Track Beta = B, Track Gamma = C+D+E.
   Brainstorming evalua basado en complejidad estimada por item.

2. **Item ordering**:
   - Item A audit MUST come first (its findings drive Items B/C/D/E
     scope refinement).
   - Item B Windows fix MUST land BEFORE Activity D' (otherwise
     Activity D' fails again).
   - Items C/D/E independent of each other.

3. **MAGI Checkpoint 2 budget allocation**: bundle multi-pillar con
   7 items. G2 binding fallback ready.

4. **Activity E' first or last in methodology**: if E' first +
   exercises `--resume-from-magi`, validates that path BEFORE Track
   dispatch. If last, post-Track-close exercise.

5. **Item E close-task convention option**: Option A (docs only) vs
   B (`/sbtdd close-task` automation) vs C (drift detector
   tolerant). Brainstorming chooses based on ergonomics + risk.

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0+v1.0.1+v1.0.2 precedents.
