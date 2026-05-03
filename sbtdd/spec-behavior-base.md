# Especificacion base — sbtdd-workflow v1.0.0 (post-v0.5.0)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.0).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-02 post-v0.5.0 ship (commit `3610a9f`, tag `v0.5.0`).
> v0.5.0 shipped la pillar observability (heartbeat in-band + status --watch
> + J3/J7 helpers + 3 v0.4.1 hotfixes). v0.5.1 LOCKED commitments per CHANGELOG
> son **rolled forward into v1.0.0** per user directive 2026-05-02
> (opcion 1 "v1.0.0 directo with v0.5.1 fold-in").
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5 frozen se
> mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento
> NO lo reemplaza — agrega el delta v1.0.0 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder (verificable con grep).

---

## 1. Objetivo

**v1.0.0 es el siguiente milestone** post-v0.5.0 (no graduacion formal). Per
brainstorming session 2026-05-01 Q1=B: 1.0 es solo un numero, BREAKINGs OK,
cadencia rapida sigue. Per Q2=C: large bundle absorbing all LOCKED items
minus INV-31 default flip (que defiere a v1.x con field-data doc dedicated).

v1.0.0 ships dos pillars + v0.5.1 hotfix fold-in:

- **Pillar 1 — MAGI quality / observability completion**: Feature G cross-check
  meta-reviewer (PRIORITY validated empirically en proyectos adyacentes),
  F44.3 retried_agents propagation a auto-run.json audit, J2 ResolvedModels
  preflight (cost optimization).
- **Pillar 2 — Schema/infrastructure**: Feature I schema_version: 2 + migration
  tool skeleton, Feature H Group B option 2 (spec-snapshot diff check) + option
  5 (auto-gen scenario stubs from /writing-plans).
- **v0.5.1 fold-in (LOCKED commitments rolled forward)**: J3 + J7 production
  wiring (33 callers), 4 Caspar Loop 2 iter 4 concerns, Windows tmp filename
  PID collision flake, 5 INFOs.

Out of scope v1.0.0 (defer a v1.x):
- INV-31 default flip decision (requires dedicated field-data doc cycle).
- Group B options 1, 3, 4, 6, 7 (opt-in flags only, not core deliverable).

Criterio de exito:
- Plugin sigue instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`).
- Tests v0.5.0 baseline (930 + 1 skipped) preservados sin regresion + nuevos.
- v0.5.0 LOCKED concerns resolved empirically.
- MAGI Loop 2 reliability sostenida (ahora con cross-check + preflight model
  resolution = recursive payoff bigger).

---

## 2. Alcance v1.0.0 — items LOCKED post-v0.5.0

### 2.1 Feature G — MAGI cross-check meta-reviewer (TOP PRIORITY)

**Problema empirico**: MAGI Loop 2 a veces emite findings CRITICAL false
positives (interpretacion erronea de spec, asuncion incorrecta sobre plan,
contexto faltante). User validated empiricamente en proyectos adyacentes
running `/requesting-code-review` AFTER MAGI sobre el mismo diff + el output
MAGI como contexto: el code-reviewer cataches false-positive CRITICALs y los
downgradea a INFO/WARNING o los rechaza directo. Pattern: MAGI primero
(breadth, 3 perspectivas), `/requesting-code-review` segundo (depth meta-review).

**Empirical evidence v0.5.0 cycle**: Loop 2 iter 4 had 2 APPROVE + 1 CONDITIONAL,
but several iter 1-3 findings turned out to be agent-level interpretation
issues that a meta-reviewer pass would have downgraded earlier. Cross-check
would have shortened the iter-2-3-4 cycle.

**Entrega v1.0.0**:

- `pre_merge_cmd._loop2_cross_check(diff, magi_verdict)`: nueva sub-fase
  despues de MAGI emit verdict, antes de aplicar findings via
  `/receiving-code-review`. Invokes `/requesting-code-review` con prompt
  meta-review especifico ("evaluate if MAGI findings are technically sound
  or false positives given the spec + plan context").
- Output del cross-check reduce/expand el set de findings a aplicar.
- INV-29 ahora tiene tres-stage pipeline: MAGI → cross-check filter →
  `/receiving-code-review` triage → mini-cycle TDD applies approved.
- `auto_cmd._phase4_pre_merge_loop2` adopta el mismo pipeline.
- Audit artifact: `.claude/magi-cross-check/<iter>-<timestamp>.json` con
  set original de MAGI findings + cross-check decisions (kept/downgraded/
  rejected) + reason por cada decision.
- Default behavior: cross-check ON. Opt-out via `magi_cross_check: false`
  en `plugin.local.md` (nueva field).

**Invariantes obligatorios**:
- Nueva propuesta INV-32-bis (renumbrar si conflict con v0.5.0 INV-32):
  "Loop 2 MAGI findings DEBEN pasar por cross-check via
  `/requesting-code-review` antes de routear via INV-29 gate, salvo que
  `magi_cross_check: false` este set."
- Cross-check NO afecta el verdict del Loop 2 (que sigue siendo consenso
  MAGI con threshold y degraded handling). Solo afecta el set de findings
  a aplicar.
- Adicional iteration count del cross-check no consume safety valve INV-11.

### 2.2 Feature I — schema_version: 2 + migration tool

**Problema**: `plugin.local.md` schema crecio en v0.2.x + v0.3.0 + v0.5.0 (v0.5.0
agrego 5 nuevos fields). Future migrations across breaking schema bumps require
identificable schema version per file.

**Entrega v1.0.0**:

- `plugin.local.md` schema gain `schema_version: 2` field. Default `1` cuando
  absent (backward compat con v0.2.x y v0.5.0 files). Parser tolera ambos.
- Migration tool stub: `scripts/migrate_plugin_local.py` (no-op for v1 → v2;
  future-proof skeleton with versioned migration ladder).
- Tests: parity entre v1 (no schema_version) y v2 (explicit schema_version:
  2) parsing. Round-trip serialization tests.

### 2.3 F44.3 — retried_agents propagation to auto-run.json

**Background**: v0.4.0 Feature F shipped marker-based discovery + retried_agents
parsing, pero el field NO se propaga a `auto-run.json` audit. v0.5.0 deferred
this. v1.0.0 closes the gap.

**Entrega v1.0.0**:

- `auto_cmd._serialize_progress` extendido (o `_write_auto_run_audit`) para
  incluir `magi_iter{N}_retried_agents: list[str]` field per MAGI iter.
- Audit accessible via status --watch + post-mortem.
- Tests: marker file con retried_agents → auto-run.json contains field.

### 2.4 Feature H Group B subset — spec-drift detection

Per brainstorming Q2=C, ship LOCKED options 2 + 5; defer INV-31 default flip
to v1.x; defer options 1, 3, 4, 6, 7 to opt-in flags.

**Option 2 — Spec-snapshot diff check**:
- `scripts/spec_snapshot.py` emits structured JSON of spec scenarios
  (title + Given/When/Then hashes) at pre-merge entry.
- Compare against last committed `planning/spec-snapshot.json`.
- Any scenario whose Given/When/Then changed since plan approval fails the
  gate unless plan is also updated.
- Protects against silently-edited `spec-behavior.md` between approval and
  merge.

**Option 5 — Auto-generated scenario stubs from /writing-plans**:
- `superpowers_dispatch.invoke_writing_plans()` extends prompt to auto-
  generate scenario stub tests per task in `planning/claude-plan-tdd-org.md`.
- Plan authors replace stubs with real assertions.
- Missing any stub at Checkpoint 2 = plan-quality failure.
- Forces 1:1 scenario-to-test mapping at plan time.

### 2.5 J2 — ResolvedModels preflight dataclass

**Problem**: `auto_cmd` dispatches read CLAUDE.md ~70-150 times during a 36-task
run to resolve per-skill model overrides. Should be done once at preflight.

**Entrega v1.0.0**:

- `models.ResolvedModels` dataclass — frozen, fields per known skill names
  (implementer, spec_reviewer, code_review, magi_dispatch, plus future).
- `auto_cmd._resolve_all_models_once(config)` helper at task-loop entry
  reads CLAUDE.md once + plugin.local.md fields, caches resolved IDs.
- All dispatches read from cached ResolvedModels instead of re-resolving.

### 2.6 v0.5.1 LOCKED fold-in (rolled forward per user directive)

Per CHANGELOG `[0.5.0]` Deferred section + Loop 2 iter 4 acceptance audit:

**a) J3 + J7 production wiring**:
- Route the 33 existing `run_with_timeout` callers in `auto_cmd.py` /
  `pre_merge_cmd.py` through `subprocess_utils.run_streamed_with_timeout`.
- v0.5.0 shipped helpers (binary-mode pipes + os.read + incremental UTF-8
  decoder POSIX, threading.Thread + queue.Queue Windows fallback, 100ms
  origin disambig window, allowlist exempt for magi-* dispatches).
- v1.0.0 closes the gap: helpers actually exercised in production paths.

**b) 4 Caspar Loop 2 iter 4 concerns**:
- W4: `pre_merge_cmd._wrap_with_heartbeat_if_auto` bare-except neutralizes
  fail-loud `_dispatch_with_heartbeat` contract. Fix: narrow except to
  AttributeError + RuntimeError (introspection failures) only; let
  ValueError (the fail-loud signal) propagate.
- W5: `status_cmd.watch_main` poll loop has no exception guard around cycle
  body. Fix: wrap body in try/except logging + continue poll loop.
- W6: tests directly mutate `auto_cmd._assert_main_thread` instead of
  `monkeypatch.setattr`. Fix: convert to monkeypatch.setattr for automatic
  cleanup on test failure.
- W7: decode-error dedup + observability counter self-defeat when
  persistence itself is failing path. Fix: separate persistence-failure
  breadcrumb from drain-failure breadcrumb.

**c) Windows tmp filename PID collision flake**:
- `test_concurrent_write_audit_writers_serialize_via_file_lock` shows
  intermittent PermissionError on Windows during concurrent os.replace of
  `.tmp.{getpid()}` files when threads share PID.
- Fix: include thread-id in tmp filename pattern in three writers
  (`auto_cmd.py:644, 997, 2469`).

**d) 5 INFOs from Loop 2 iter 4** (housekeeping pass):
- Bytecode-deployment fragility of inspect.getsource assertion in
  `_with_file_lock` (or remove the runtime assertion; unit test covers it).
- BaseException catch in `_write_auto_run_audit` delays SystemExit /
  KeyboardInterrupt — narrow to Exception.
- INV-34 validation messages omit unit suffix in 'got N' fragment — add
  's' (seconds).
- Autouse fixture only in `test_auto_progress.py` — promote to conftest.py
  for cross-test-file consistency.
- Windows kill-path race with reader chunks despite W7 drain — document
  as accepted-risk inherent to threaded-reader fallback design.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-34 preservados. Propuestas v1.0.0:

- **INV-32-bis (propuesta)**: cross-check via `/requesting-code-review`
  obligatorio antes de INV-29 gate (Feature G), salvo opt-out explicit
  via `magi_cross_check: false`.
- **INV-35 (propuesta, contingent on Feature I)**: `plugin.local.md` schema
  declares `schema_version: int = 1` (default cuando absent → backward
  compat); future schema bumps increment + migration tool handles
  upgrade path.

Critical durante implementacion v1.0.0:

- INV-0 (autoridad maxima `~/.claude/CLAUDE.md`).
- INV-22 (sequential auto) preservado.
- INV-26 (audit trail) extendido con MAGI cross-check artifacts +
  retried_agents propagation + ResolvedModels preflight cache.
- INV-27 (spec-base placeholder): este documento cumple.
- INV-28, INV-29, INV-32, INV-33, INV-34: preservados sin cambio.

### Stack y runtime

Sin cambios vs v0.5.0:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot paths.
- Dependencias externas: git, tdd-guard, superpowers, magi (>= 2.2.x per
  Feature F backward compat), claude CLI.
- Dependencias dev: pytest, pytest-asyncio, ruff, mypy, pyyaml.
- Licencia dual MIT OR Apache-2.0.

### Reglas duras no-eludibles (sin override)

- INV-0 autoridad global.
- INV-27 spec-base sin uppercase placeholder markers.
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F55 v0.5.0; v1.0.0 starts at F60.)

**F60**. `pre_merge_cmd._loop2_cross_check(diff, magi_verdict)` invoke
`/requesting-code-review` con prompt instructivo de meta-review. Output =
filtered findings set. Audit artifact written to
`.claude/magi-cross-check/<iter>-<timestamp>.json`.

**F61**. `auto_cmd._phase4_pre_merge_loop2` adopts cross-check pipeline.

**F62**. `PluginConfig.magi_cross_check: bool = True` field nuevo.

**F63**. `models.ResolvedModels` dataclass + `_resolve_all_models_once(config)`
helper invoked at task-loop entry instead of per-dispatch.

**F64**. `PluginConfig.schema_version: int = 1` field nuevo (default 1
cuando absent → backward compat).

**F65**. `scripts/migrate_plugin_local.py` skeleton (no-op v1 → v2;
versioned migration ladder).

**F66**. `auto_cmd` audit serialization includes `magi_iter{N}_retried_agents:
list[str]` field per iter.

**F67**. `scripts/spec_snapshot.py` (Feature H option 2) emits + compares
spec scenarios JSON.

**F68**. `superpowers_dispatch.invoke_writing_plans` extends prompt to
auto-generate scenario stub tests (Feature H option 5).

**F69 thru F76 (v0.5.1 fold-in)**:
- F69: route 33 `run_with_timeout` callers → `run_streamed_with_timeout`.
- F70: narrow `_wrap_with_heartbeat_if_auto` except clauses (W4).
- F71: exception guard around `watch_main` cycle body (W5).
- F72: convert `_assert_main_thread` test mutations to monkeypatch.setattr (W6).
- F73: separate persistence-failure vs drain-failure breadcrumbs (W7).
- F74: thread-id in tmp filename pattern in three writers (Windows flake fix).
- F75: 5 INFOs housekeeping (bytecode-deploy assert, BaseException narrow,
  INV-34 unit suffix, conftest autouse promotion, kill-path race doc).

### Requerimientos no-funcionales (NF)

**NF20**. `make verify` runtime ≤ 120s budget (v0.5.0 was 100.56s; v1.0.0
expected slight increase from new tests; soft-target ≤ 120s).

**NF21**. v0.5.0 `plugin.local.md` files (sin schema_version) cargan en
v1.0.0 sin error (Feature I backward compat).

**NF22**. v0.4.0 + v0.5.0 `auto-run.json` files (sin retried_agents +
sin progress key) parse cleanly post-F66 (D4.3 absent-tolerant continued).

---

## 5. Scope exclusions

Out-of-scope para v1.0.0:

- **INV-31 default flip decision** (deferred to v1.x dedicated cycle with
  field-data doc; user explicit per Q2=C "minus INV-31 default flip").
- **Group B options 1, 3, 4, 6, 7** (opt-in flags only; not core v1.0.0
  deliverable; ship as flags-without-default).
- **GitHub Actions CI workflow** (deferred v1.1).
- **C++ stack adapters adicionales** (deferred v1.1).
- **TUI dashboard** (CLI status --watch shipped v0.5.0 suficiente).

---

## 6. Criterios de aceptacion finales

v1.0.0 ship-ready cuando:

### 6.1 Functional Pillar 1 — MAGI quality

- **F1**. Feature G cross-check sub-fase implementada en pre_merge_cmd +
  auto_cmd phase 3.
- **F2**. Audit artifact `.claude/magi-cross-check/...` written per iter.
- **F3**. INV-32-bis documented + adopted.
- **F4**. Default `magi_cross_check: true`; opt-out via plugin.local.md.
- **F5**. F44.3: `retried_agents` propagated to auto-run.json audit.
- **F6**. J2: ResolvedModels preflight cache reduces CLAUDE.md reads from
  ~70-150 per run to 1.

### 6.2 Functional Pillar 2 — Schema/infrastructure

- **F7**. `schema_version` field added to PluginConfig; backward compat
  v1 (no field) loads as schema_version=1.
- **F8**. Migration script skeleton present at `scripts/migrate_plugin_local.py`.
- **F9**. Feature H option 2: spec-snapshot diff check at pre-merge entry.
- **F10**. Feature H option 5: auto-gen scenario stubs from /writing-plans
  prompt extension.

### 6.3 Functional v0.5.1 fold-in

- **F11**. J3 + J7 production wiring: 33 callers routed through
  `run_streamed_with_timeout`. Heartbeat actually fires in production for
  all long dispatches.
- **F12**. 4 Caspar Loop 2 iter 4 concerns resolved: bare-except narrowed,
  watch_main guarded, monkeypatch.setattr migration, decode-error breadcrumb
  separation.
- **F13**. Windows tmp PID flake fixed via thread-id in tmp filename.
- **F14**. 5 INFOs housekeeping pass complete.

### 6.4 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format + mypy
  --strict, runtime ≤ 120s.
- **NF-B**. Tests baseline 930 + 1 skipped preservados + nuevos.
- **NF-C**. Cross-platform (POSIX + Windows). Windows-specific tests
  empirically pass.
- **NF-D**. Author/Version/Date headers en nuevos `.py` files.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados
  explicitamente.

### 6.5 Process

- **P1**. MAGI Checkpoint 2 verdict ≥ `GO_WITH_CAVEATS` full per INV-28.
  Iter budget 3 + INV-0 override available (but per CHANGELOG `[0.5.0]`
  process commitment, scope-trim is the first hypothesis when iter 3
  doesn't converge — bundle width should be reduced before INV-0 override).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict ≥
  `GO_WITH_CAVEATS` full. Cross-check sub-fase (Feature G shipping in this
  cycle) self-validates during own ciclo.
- **P3**. CHANGELOG `[1.0.0]` entry written con secciones Added / Changed
  / Deferred + Process notes.
- **P4**. Version bump 0.5.0 → 1.0.0 sync `plugin.json` + `marketplace.json`.
- **P5**. Tag `v1.0.0` + push (con autorizacion explicita user).

### 6.6 Distribution

- **D1**. Plugin instalable via `/plugin marketplace add ...` +
  `/plugin install ...`.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos subcomandos / flags documentados en README + SKILL.md +
  CLAUDE.md.

---

## 7. Dependencias externas nuevas

Ninguna runtime nueva. Dev: ninguna nueva. Feature G assumes
`/requesting-code-review` superpowers skill present (already required
v0.4.0+); testing requires MAGI 2.2.x+ goldens cached locally for
cross-check pipeline tests.

---

## 8. Risk register v1.0.0

- **R1**. Cross-check (Feature G) introduces false-negative risk
  (downgrades CRITICAL real to INFO). Mitigation: audit artifact permite
  post-mortem + cross-check NO modifies the verdict, only the findings
  set; raw MAGI verdict + findings still preserved.
- **R2**. Bundle width: 5 features + v0.5.1 fold-in (~12 commitments).
  Per `[0.5.0]` Process notes scope-trim default for v0.6.0+, this
  v1.0.0 bundle is at the edge. Mitigation: brainstorming session may
  recommend split if MAGI Checkpoint 2 doesn't converge in 3 iters.
- **R3**. Feature H option 2 spec-snapshot risks blocking legitimate
  spec edits between plan approval and merge. Mitigation: exit valve via
  re-running /writing-plans + Checkpoint 2 to re-approve plan against
  updated spec.
- **R4**. Feature H option 5 auto-gen stubs may produce noisy
  unimplemented test bodies. Mitigation: clear convention in stubs that
  "stub bodies must be replaced with assertions before MAGI Checkpoint 2";
  spec_lint could check.
- **R5**. v0.5.1 fold-in: 4 Caspar concerns are localized but expand
  surface. Mitigation: each is small (~5-15 line fix) with clear
  resolution per Loop 2 iter 4 Recommended Actions.
- **R6**. Schema migration tool (Feature I) is no-op for v1 → v2; future
  v3 migrations will need real implementation. Mitigation: ship the
  framework now (skeleton + ladder), populate when needed.
- **R7**. INV-31 default-flip out-of-scope but spec-reviewer hard-block
  remains v0.5.0 default. Operator pain continues. Mitigation: documented
  out-of-scope rationale; users can opt-out via `--skip-spec-review`.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v0.5.0 ship record: just-shipped tag `v0.5.0` (commit `3610a9f` on `main`).
- v0.4.0 ship + Feature F empirical findings:
  `memory/project_v040_shipped.md`.
- v0.5.0 cycle decisions (brainstorming + 4-iter MAGI Checkpoint 2 +
  Loop 1 + 4-iter Loop 2 INV-0 acceptance): see git log
  `4538914..3610a9f` and `.claude/magi-runs/v050-*` artifacts.
- v0.5.1 LOCKED commitments rolled into v1.0.0 per user directive 2026-05-02:
  CHANGELOG `[0.5.0]` Deferred section.
- v1.0.0 deferred items roadmap (continuing to v1.x):
  - INV-31 default flip dedicated cycle.
  - Group B options 1, 3, 4, 6, 7 (opt-in flags).
  - GitHub Actions CI workflow.
  - C++ stack adapter expansion.

---

## Nota sobre siguiente paso

Este archivo cumple INV-27. Listo como input para `/brainstorming`.
Decisiones pendientes clave para brainstorming:

1. **Pillar 1 / Pillar 2 / fold-in priority order**: orchestrator picks
   ship-order. Recommendation: G + F44.3 + J2 first (MAGI quality), then
   I + Group B (schema/infra), then v0.5.1 fold-in (housekeeping).
2. **Bundle vs split**: per CHANGELOG process commitment, if scope
   exceeds 3-iter MAGI budget, scope-trim is preferred over INV-0
   override. Brainstorming may recommend split into v0.6.0 (Pillar 1 +
   v0.5.1 fold-in) + v1.0.0 (Pillar 2 schema/infra).
3. **Subagent layout**: surfaces analysis. Pillar 1 touches pre_merge_cmd +
   auto_cmd + magi_dispatch + models. Pillar 2 touches config + new
   scripts. v0.5.1 fold-in touches auto_cmd + pre_merge_cmd + status_cmd +
   tests. HIGH overlap on auto_cmd/pre_merge_cmd → single sequential
   subagent OR carefully phased parallel.
4. **Cross-check (Feature G) recursive payoff**: v1.0.0 Loop 2 is the
   first pre-merge gate to USE cross-check (it ships in this cycle).
   Self-validation during own ship is a strong empirical signal.

Brainstorming refinara estas decisiones basado en complejidad, risk, y
empirical findings de v0.5.0 cycle.
