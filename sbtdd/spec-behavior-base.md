# Especificacion base — sbtdd-workflow v1.0.0 (post-v0.3.0)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v1.0.0). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado 2026-04-25, post-v0.3.0 ship (commit `2befb88`, tag
> `v0.3.0`). v0.3.0 shipped el subset D+E del v1.0.0 backlog
> original; este documento reescribe el alcance v1.0.0 reflejando lo
> que queda + empirical findings del ciclo v0.3.0.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3 frozen se
> mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md` (mega-contrato
> 2860+ lineas); este documento NO lo reemplaza — agrega el delta
> v1.0.0 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder
> (verificable con grep).

---

## 1. Objetivo

**v1.0.0 es la graduacion estable** del plugin (salida del pre-1.0
v0.x). Consolida los items LOCKED restantes del backlog post-v0.3.0
ship + items operacionales rolled forward de v0.4.0 candidates +
schema versioning formal + decision strategic sobre INV-31 default
behavior. v1.0.0 es la version a la que el ecosistema externo
(usuarios + plugins consumidores) puede commitear con backward-compat
guarantees.

Criterio de exito:
- Plugin sigue instalable desde `BolivarTech/sbtdd-workflow`
  (marketplace `bolivartech-sbtdd`).
- Tests existentes (789 baseline post-v0.3.0) pasan sin regresion.
- Nuevos blockers suman cobertura apropiada.
- MAGI Loop 2 reliability mejora dramaticamente (Feature F empirical
  validation).
- Schema versioning formal habilita migracion a v2.0.0 + futuras
  iteraciones sin romper contratos.
- INV-31 default decision adoptada con field data v0.2/v0.2.1/v0.2.2/
  v0.3.0 detras.

Decision pendiente clave para brainstorming:
- **Monolithic v1.0.0** vs **v0.4.0 (operacional polish) + v1.0.0
  (semantic features + tag estable)**.
- Cual subset de v0.4.0 candidates entra en v1.0.0 vs queda en v1.x.
- Pattern de ejecucion: lightweight (precedente v0.2.1, v0.2.2,
  v0.3.0) vs full SBTDD `/sbtdd auto` (precedente v0.2.0, donde
  nunca se shipo via auto end-to-end por las inestabilidades MAGI).

---

## 2. Alcance v1.0.0 — items LOCKED post-v0.3.0

### 2.1 Feature F — MAGI dispatch hardening + tolerant parsing (TOP PRIORITY)

**Problema empirico v0.3.0**: en el final review loop del v0.3.0 cycle
(commit `2befb88`), MAGI v2.2.2 sufrio dos fallas consecutivas:

- Iter 1: caspar agent crash a los 665s con JSON decode error;
  veredicto degraded HOLD (1-1).
- Iter 2: synthesizer abort con `RuntimeError: Only 1 agent(s)
  succeeded` porque melchior + balthasar wrapped JSON en narrative
  preamble defeating el strict parser. Los `.raw.json` files
  contenian agent output completo y valid; solo el parser fallo.

Pattern: el strict JSON parser de MAGI no tolera preamble + el
output discovery basado en path es fragil contra cambios de layout
interno. Sin Feature F, MAGI Loop 2 reliability degrada cuanto mas
iteraciones se necesitan — exactamente cuando mas se necesita
robustness.

**Directiva implicita usuario**: el v0.3.0 cycle survived via manual
synthesis recovery (read `.raw.json` files + interpret agent verdicts
manually) + INV-0 override precedent. v1.0.0 debe absorbar este
pattern en MAGI dispatch infra para que la rescata sea automatica
cuando la sintetizadora crash y los agents tengan output valido.

**Entrega v1.0.0**:

- `magi_dispatch.py`: cambia de path-based discovery a
  marker-based: cada invocacion MAGI escribe
  `MAGI_VERDICT_MARKER.json` en directorio conocido; SBTDD enumera
  markers post-subprocess y picks el mas reciente by mtime.
  Defensivo contra cambios de layout interno (observado en v0.2/
  v0.3 cycles).
- `MAGIVerdict` parser: tolerant against preamble. Cuando
  `agent.raw.json` contiene `"result": "<narrative preamble>\n\n{...
  agent JSON ...}"`, el parser extrae el JSON object via regex de
  primera `{...}` balanced + JSON-parse. Falla solo si NO hay JSON
  object recoverable.
- `MAGIVerdict.retried_agents: tuple[str, ...]` field. Parser tolera
  ausencia (MAGI < 2.2.1 default a `()`). Propagado a `auto-run.json`
  + escalation_prompt context.
- Synthesizer-recovery flag: cuando run_magi.py synthesis falla con
  RuntimeError pero >= 1 agent succeeded, SBTDD wrapper reads raw.json
  files directamente, applies tolerant parser, emite manual
  synthesis report a `.claude/magi-runs/<iter>/manual-synthesis.json`,
  log warning a stderr, y proceeds. Operador can suppress via
  `--no-magi-recovery` flag (default ON post-v1.0.0).
- Tests parity: MAGI 2.1.x golden output + MAGI 2.2.x+ golden con +
  sin retried_agents + agent JSON con preamble + agent JSON sin
  preamble + synthesizer crash recovery.

**Invariantes obligatorios**:
- INV-28 (degraded MAGI no-exit) preservado.
- INV-29 (/receiving-code-review gate) preservado sin cambio.
- Recovery NO es backdoor para skip MAGI: requiere `>= 1 agent
  succeeded` AND `agent verdict parses cleanly` AND `findings
  classifiable`.
- Marker file format: JSON con `verdict`, `iteration`, `agents`,
  `retried_agents`, `timestamp`, `synthesizer_status`. Schema fixed
  in `models.py`.

### 2.2 Feature G — MAGI -> /requesting-code-review cross-check

(Sin cambio del scope original v1.0.0; esta inalterado por v0.3.0
ship porque pre_merge_cmd no fue tocado. Re-incluido aqui para
completitud.)

**Problema**: MAGI Loop 2 a veces emite findings CRITICAL false
positives (interpretacion erronea de spec, asuncion incorrecta sobre
plan, contexto faltante). User validated empiricamente en proyectos
adyacentes corriendo `/requesting-code-review` AFTER MAGI sobre el
mismo diff + el output MAGI como contexto: el code-reviewer cataches
false-positive CRITICALs y los downgradea a INFO/WARNING o los
rechaza directo. Pattern: MAGI primero (breadth, 3 perspectivas),
`/requesting-code-review` segundo (depth meta-review).

**Entrega v1.0.0**:

- `pre_merge_cmd.py` Loop 2 nueva sub-fase: despues de MAGI emit
  verdict, antes de aplicar findings via `/receiving-code-review`,
  invoke `/requesting-code-review` pasando el diff + MAGI verdict
  como contexto, instruyendo: "evalua si los findings MAGI son
  technically sound o false positives". Output del cross-check
  reduce/expand el set de findings a aplicar.
- INV-29 ahora tiene tres-stage pipeline: MAGI emite findings ->
  cross-check via `/requesting-code-review` (filtra) ->
  `/receiving-code-review` evalua tecnico -> mini-cycle TDD aplica
  los aprobados.
- `auto_cmd._phase4_pre_merge_loop2` adopta el mismo pipeline.
- Audit artifact: `.claude/magi-cross-check/<iter>-<timestamp>.json`
  con set original de MAGI findings + decisions del cross-check
  (kept/downgraded/rejected) + reason por cada decision.
- Default behavior: cross-check ON. Opt-out via
  `magi_cross_check: false` en `plugin.local.md` (nueva field).

**Invariantes obligatorios**:
- Nueva propuesta INV-32: "Loop 2 MAGI findings DEBEN pasar por
  cross-check via `/requesting-code-review` antes de routear via
  INV-29 gate, salvo que `magi_cross_check: false` este set."
- Cross-check no afecta el verdict del Loop 2 (que sigue siendo
  consenso MAGI con threshold y degraded handling). Solo afecta el
  set de findings a aplicar.
- Adicional iteration count del cross-check no consume safety valve
  INV-11.

### 2.3 Feature H — Group B spec-drift re-eval + INV-31 default-on opt-in re-eval

(Sin cambio scope original; field data ahora incluye v0.3.0 dogfood.)

Field data summary acumulada de v0.2.0 a v0.3.0 (5 ciclos):
- v0.2.0: spec-reviewer hard-blocked en mid-cycle, INV-31 enforced
  fail-fast — ratificado pero costoso.
- v0.2.1: B6 auto-feedback loop maduro; reviewer findings ahora
  routean via /receiving-code-review automaticamente.
- v0.2.2: docs only, no field data.
- v0.3.0: lightweight pattern (no /sbtdd auto), pero spec-reviewer
  not invoked porque ciclo no usa close_task_cmd.

**Decision Feature H**: based on field data, decide:
- **Option A** (preserve default-on): keep current; `--skip-spec-review`
  remains escape valve. Justified si reviewer catches >X true-positive
  drifts per Y tasks.
- **Option B** (flip to opt-in): rename flag to `--enable-spec-review`
  on `close-task`/`auto`; default skip. Justified si overhead >>
  benefit empiricamente.
- **Option C** (config-driven): new field `spec_review_default` en
  `plugin.local.md` con `on|off|auto-detect-by-stack`.

**Entrega v1.0.0**:

- Field data document: `docs/v1.0.0-field-data.md` con observations
  de v0.2/v0.2.1/v0.3.0 cycles.
- INV-31 decision adoptada en SKILL.md operational impact + README
  matrix.
- Group B options evaluation:
  - Option (1) `scenario_coverage_check.py` mechanical pre-filter —
    implementar como Feature B pre-filter si field data muestra
    >30% noise rate.
  - Option (2) Spec-snapshot diff check — **LOCKED implementar**
    (covers risk class option 8 cannot).
  - Option (5) Auto-generated scenario stubs from /writing-plans —
    **LOCKED implementar** (strong v0.3 backlog candidate).
  - Options (3), (4), (6), (7) — opt-in via flags, no shipped default.

**Invariantes obligatorios**:
- Cualquier flip de default INV-31 = formal BREAKING bump (v1.0.0
  absorbs multiple BREAKINGs por la graduacion).
- Group B options shipped (option 2 + option 5) preservan INV-29
  gate sin cambio.

### 2.4 Feature I — schema_version: 2 formal versioning

(Item E2 deferred de v0.3.0 + nuevo schema_version field como
graduacion formal pre-1.0.)

**Problema**: `plugin.local.md` schema crecio en v0.2.x (model
fields, auto_max_spec_review_seconds, etc.) sin formal version
field. Future migrations across breaking schema bumps require
identificable schema version per file.

**Entrega v1.0.0**:

- `plugin.local.md` schema gain `schema_version: 2` field.
  Default `1` cuando absent (backward compat con v0.2.x files).
  Parser tolera ambos.
- Migration tool stub: `scripts/migrate_plugin_local.py` (no-op
  for v1 -> v2 transition; future-proof skeleton).
- Tests: parity entre v1 (no schema_version) y v2 (explicit
  schema_version: 2) parsing.

### 2.5 Feature J — v0.4.0 candidates re-evaluation

7 INFO-class items emergieron del MAGI iter 1+2 review de v0.3.0
(memorias `project_v030_shipped.md` Open items section). Decision:
cual subset entra en v1.0.0 vs deferred a v1.x.

Items candidatos:
1. **D5 `/sbtdd status --watch` companion subcommand** — orthogonal
   al D streaming; podria entrar v1.0.0 o v1.1.0.
2. **INFO #10 ResolvedModels dataclass** — one preflight CLAUDE.md
   scan instead of per-dispatch (~70-150 disk reads per 36-task
   auto run actualmente).
3. **INFO #11 streaming pump per-stream timeout** — wall-clock
   timeout currently unreachable si subprocess writes sin newlines.
4. **INFO #12 _update_progress OSError handling** — observability
   failure could kill auto run.
5. **balthasar iter-2 INFO #1**: SKILL.md line 78 documents
   `--model-override invalid skill -> exit 2` but impl raises
   ValidationError -> exit 1. Docs vs code align.
6. **balthasar iter-2 INFO #2**: `_write_auto_run_audit` transiently
   drops `progress` field. Cleanest fix alongside D5
   (`status --watch`).
7. **caspar iter-2 INFO #1**: two-pump stdout/stderr origin
   ambiguity in streamed output.
8. **caspar iter-2 INFO #3**: pre-merge dispatches don't pass
   `stream_prefix`. v0.4.0 follow-up to extend streaming consciously.

**Decision Feature J**: which subset goes into v1.0.0 vs v1.1.0
(post-1.0 hardening). Brainstorming refinara basandose en complejidad
estimada y alineacion semantic con feature F+G+H+I.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-31 preservados. Propuestas
v1.0.0:

- **INV-32 (propuesta)**: MAGI cross-check via `/requesting-code-review`
  obligatorio antes de INV-29 gate (Feature G), salvo opt-out
  explicit.
- **INV-33 (propuesta, contingent on Feature F shipping)**: MAGI
  synthesizer recovery via tolerant parser is non-optional for
  v1.0.0+; raw.json files MUST be persisted en `.claude/magi-runs/`
  para post-mortem auditability.
- INV-31 contract evolution segun decision Feature H.

Critical durante implementacion v1.0.0:

- INV-0 (autoridad maxima `~/.claude/CLAUDE.md`).
- INV-22 (sequential auto) preservado en cualquier path nuevo.
- INV-26 (audit trail) extendido con MAGI markers + cross-check
  artifacts + manual synthesis reports.
- INV-27 (spec-base placeholder): este documento cumple.
- INV-28, INV-29: preservados sin cambio.

### Stack y runtime

Sin cambios vs v0.3:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot
  paths.
- Dependencias externas: git, tdd-guard, superpowers, magi (>= 2.1.x
  per backward compat de Feature F), claude CLI.
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

(F-series continua desde F42; v0.3.0 shipped F28-F35 implicitly.
v1.0.0 starts at F43.)

**F43**. `magi_dispatch._discover_verdict_marker(output_dir)` enumera
`MAGI_VERDICT_MARKER.json` files, picks max mtime. Replace path-based
discovery.

**F44**. `MAGIVerdict.retried_agents: tuple[str, ...]` field. Parser
tolera ausencia.

**F45**. `magi_dispatch._tolerant_agent_parse(raw_json_path)` extracts
JSON object from agent `result` field via regex when wrapped in
narrative preamble. Returns parsed agent verdict OR raises
ValidationError if no recoverable JSON.

**F46**. `magi_dispatch._manual_synthesis_recovery(run_dir)` reads
all `*.raw.json` in run_dir, applies tolerant parser, emits manual
synthesis to `manual-synthesis.json`, returns synthesized verdict.

**F47**. `pre_merge_cmd._loop2_cross_check(diff, magi_verdict)` invoke
`/requesting-code-review` con prompt instructivo de meta-review.
Output = filtered findings set. Audit artifact escrito a
`.claude/magi-cross-check/<iter>-<timestamp>.json`.

**F48**. `auto_cmd._phase4_pre_merge_loop2` adopta cross-check.

**F49**. `config.PluginConfig` gana `magi_cross_check: bool = True`
field + `schema_version: int = 1` field.

**F50**. `scripts/migrate_plugin_local.py` skeleton (no-op v1 -> v2).

**F51**. `scripts/spec_snapshot.py` (LOCKED Group B option 2).

**F52**. `/writing-plans` invocation extiende prompt para auto-generate
scenario stubs per task (LOCKED Group B option 5).

**F53**. (Si Feature J item D5 incluido en v1.0.0)
`status_cmd --watch` poll loop sobre `auto-run.json` mtime con
intervalo 1s, render TTY o JSON.

**F54**. (Si Feature J item INFO #10 incluido)
`models.ResolvedModels` dataclass + `_resolve_all_models_once(config)`
helper invoked at task-loop entry instead of per-dispatch.

**F55**. INV-31 decision adoption en SKILL.md + README + plugin.local.md.

### Requerimientos no-funcionales (NF)

**NF16**. MAGI Loop 2 reliability target: >= 90% successful syntheses
on first attempt with full 3-agent consensus (current empirical
v0.3.0: 0/2 = 0%).

**NF17**. `make verify` runtime <= 90s budget preservado.

**NF18**. v0.3.0 plugin.local.md files (sin schema_version) cargan
en v1.0.0 sin error.

---

## 5. Scope exclusions

Out-of-scope para v1.0.0:

- GitHub Actions CI workflow (deferred v1.1).
- C++ stack adapters adicionales (deferred v1.1).
- Marketplace `$schema` URL post-push verification (v1.1).
- MAGI sub-agent model control (out of SBTDD scope).
- TUI dashboard (CLI status --watch suficiente).

---

## 6. Criterios de aceptacion finales

v1.0.0 ship-ready cuando:

### 6.1 Functional (Feature F — MAGI hardening)

- **F1**. Marker-based discovery reemplaza path-based.
- **F2**. `retried_agents` parsed + propagado.
- **F3**. Tolerant agent JSON parsing (preamble-wrapped).
- **F4**. Manual synthesis recovery automatic on synthesizer crash
  with >= 1 agent succeeded.
- **F5**. Backward-compat MAGI 2.1.x + 2.2.x+ tests pasan.
- **F6**. NF16 reliability target met empirically en v1.0.0 dogfood
  pre-merge.

### 6.2 Functional (Feature G — cross-check)

- **G1**. Loop 2 cross-check sub-fase implementada.
- **G2**. Audit artifact `.claude/magi-cross-check/...` escrito.
- **G3**. INV-32 documentado + adoptado.
- **G4**. Default `magi_cross_check: true`; opt-out via
  plugin.local.md.

### 6.3 Functional (Feature H — re-eval)

- **H1**. Field data documento escrito.
- **H2**. INV-31 default decision adoptada.
- **H3**. Group B options (2) + (5) implementadas; (1), (3), (4),
  (6), (7) opt-in flags or rejected with rationale.

### 6.4 Functional (Feature I — schema_version)

- **I1**. `schema_version` field added to PluginConfig.
- **I2**. Backward-compat: v1 (no field) loads as schema_version=1.
- **I3**. Migration script skeleton present.

### 6.5 Functional (Feature J — v0.4.0 candidates)

- **J1**. Subset decision documented (which items in v1.0.0 vs v1.1).
- **J2**. Items in v1.0.0 implemented + tested.

### 6.6 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict, runtime <= 90s.
- **NF-B**. Tests totales >= 789 baseline + nuevos.
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en nuevos `.py` files.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados
  explicitamente.
- **NF-F**. NF16 MAGI reliability target met.

### 6.7 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter budget 3 + INV-0 override available.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict >=
  `GO_WITH_CAVEATS` full. **NEW**: cross-check (Feature G)
  self-validates durante el ciclo.
- **P3**. CHANGELOG.md `[1.0.0]` entry con BREAKING / Added / Changed
  / Process notes.
- **P4**. Version bump 0.3.0 -> 1.0.0 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.0` + push.

### 6.8 Distribution

- **D1**. Plugin instalable via `/plugin marketplace add ...` +
  `/plugin install ...`.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos subcomandos / flags documentados en
  README + SKILL + CLAUDE.md.

---

## 7. Dependencias externas nuevas

Ninguna runtime nueva. Dev: ninguna nueva. Feature F asume MAGI 2.1.x+
ya presente; testing requiere acceso a MAGI 2.2.x+ goldens (cached
locally).

---

## 8. Risk register v1.0.0

- **R1**. Tolerant agent JSON parsing introduces false-positive
  recovery — mitigation: regex requires balanced `{...}` AND valid
  JSON-parse AND verdict in known set; manual synthesis report
  flags recovery clearly.
- **R2**. Marker-based MAGI discovery breaks if MAGI changes marker
  schema — mitigation: SBTDD tolera ausencia de campos opcionales en
  marker; mantener test contra MAGI versions cacheadas.
- **R3**. Cross-check (Feature G) introduces false-negative risk
  (downgrades CRITICAL real to INFO) — mitigation: audit artifact
  permite post-mortem.
- **R4**. INV-31 flip decision: breaking change in default behavior —
  mitigation: v1.0.0 BREAKING bump absorbs; clear migration docs.
- **R5**. Schema bump v1 -> v2 sin migration tool prematuro —
  mitigation: v1.0.0 ships skeleton + no-op for v1 -> v2; future
  migrations populate.
- **R6**. Bundle 5 features in one cycle = MAGI Checkpoint 2 verdict
  difficult — mitigation: Feature F itself improves MAGI reliability,
  recursive gain. Alternativamente split: v0.4.0 (operational polish)
  + v1.0.0 (semantic features + tag estable).
- **R7**. Lightweight vs full SBTDD pattern — v0.3.0 lightweight worked
  but iter-2 mini-cycle costed +14 tests + 11 commits. Full SBTDD
  has not been validated end-to-end via /sbtdd auto. Iter cap +
  manual MAGI recovery may need refinement before /sbtdd auto can
  run unsupervised long cycles.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v0.3.0 ship record: memory `project_v030_shipped.md`.
- v0.2.x ship records: memory `project_v020_shipped.md`,
  `project_v021_shipped.md`, `project_v022_shipped.md`.
- v1.0.0 LOCKED memory files (deferred items):
  - `project_v100_progress_streaming.md` (D5 deferred portion).
  - `project_v100_per_skill_model_flag.md` (E2 deferred portion).
  - `project_v100_magi_dispatch_hardening.md` (Feature F).
  - `project_v100_magi_cross_check.md` (Feature G PRIORITY).
- Empirical findings v0.3.0:
  - `.claude/magi-runs/v030-iter1/magi-report.json`.
  - `.claude/magi-runs/v030-iter2/{melchior,balthasar,caspar}.raw.json`
    (synthesizer crash, manual synthesis recovery rationale).
- Historical precedent:
  - v0.2.0 INV-0 override commit `5d7bfc4`.
  - v0.2.1 lightweight pattern.
  - v0.3.0 lightweight + 2-iter MAGI Loop 2 + manual synthesis.

---

## Nota sobre siguiente paso

Este archivo cumple INV-27. Listo como input para `/brainstorming`.
Decisiones pendientes clave para brainstorming:

1. **Bundle vs split**: monolithic v1.0.0 (F+G+H+I+J subset) vs
   v0.4.0 (operational polish J subset) + v1.0.0 (F+G+H+I + tag
   estable).
2. **Pattern**: lightweight (precedente v0.3.0 worked despite
   MAGI fragility) vs full SBTDD `/sbtdd auto` (precedent v0.2.0
   never reached, full auto e2e never validated).
3. **Feature J subset**: which v0.4.0 candidates enter v1.0.0
   (D5, INFO #10, INFO #11, INFO #12, balthasar #1, balthasar #2,
   caspar #1, caspar #3).
4. **INV-31 default decision**: option A preserve / B opt-in / C
   config-driven.
5. **Group B subset within Feature H**: (2) + (5) LOCKED, but
   should (1) `scenario_coverage_check.py` ship as Feature B
   pre-filter? Field data inconclusive.

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v0.3.0.
