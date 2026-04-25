# Especificacion base — sbtdd-workflow v1.0.0

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v1.0.0). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado 2026-04-25, post-v0.2.2 ship. v0.2 cycle cerrado completo.
> Source of truth autoritativo para v0.1+v0.2 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md` (mega-contrato 2860+
> lineas); este documento NO lo reemplaza — agrega el delta v1.0.0
> y, al landing, se incorporan sus decisiones a la base.
>
> Archivo cumple INV-27: no contiene los tres marcadores uppercase
> enumerados en esa invariante (ver `sbtdd-workflow-plugin-spec-base.md`
> sec.S.10 para la lista completa).

---

## 1. Objetivo

Entregar **v1.0.0** (graduacion estable del plugin, salida del
pre-1.0) consolidando cinco release blockers LOCKED derivados de gaps
empiricos del dogfood v0.2 + items operacionales rolled forward del
backlog v0.3 (renombrado a v1.0.0 en CHANGELOG forward sections el
2026-04-25). El alcance v1.0.0 es deliberadamente focused en
estabilidad operacional + control de costo + meta-review pattern; no
introduce features de spec/plan ni cambia la semantica del ciclo TDD.

Criterio de exito: el plugin sigue siendo instalable desde
`BolivarTech/sbtdd-workflow` (marketplace `bolivartech-sbtdd`); todos
los tests existentes (735 baseline post-v0.2.2) siguen pasando sin
regresion; los cinco blockers nuevos suman cobertura de tests
apropiada + acceptance criteria sec.S.12 extendidos para v1.0.0; y
el plugin pasa su primer `/sbtdd auto` end-to-end usando la nueva
config Sonnet+Haiku mix sin overrun de costo Opus-default.

Decision pendiente al inicio del ciclo (refinable durante
brainstorming): bundle de los 5 items en un solo `/sbtdd auto` cycle,
o split en sub-ciclos secuenciales (p.ej. v0.3.0 = items operacionales
1+2; v0.4.0 = MAGI hardening 3+4; v1.0.0 = re-eval 5 + tag estable).

---

## 2. Alcance v1.0.0 — cinco release blockers LOCKED

### 2.1 Feature D — Auto progress streaming (UX)

**Problema v0.2**: durante `/sbtdd auto` runs multi-hora (Milestone-A
size, 36+ tasks), el operador no ve progreso intermedio. El subprocess
`claude -p` del implementer captura stdout/stderr; sin `python -u`
flushing + per-phase stderr breadcrumbs + actualizaciones live a
`auto-run.json`, el run "looks hung" durante minutos. Empirico v0.2
dogfood: tee buffering atrapaba salidas hasta task completion. Operador
sin senal = aborta prematuramente o asume crash.

**Entrega v1.0.0**:

- `auto_cmd.py` invoca subprocess con `stdout=PIPE, stderr=PIPE,
  bufsize=1` + read-line loop que reescribe a stderr del orquestador
  con prefijo `[task-N phase] ` para distinguir fuentes en logs.
- `python -u` agregado a la invocacion (`["python", "-u",
  run_sbtdd.py, ...]`) para deshabilitar Python output buffering en
  el dispatcher mismo.
- Per-phase stderr breadcrumbs: `auto_cmd` emite `[phase 2/5: task
  loop -- task 14/36 (red)]` cada vez que avanza la state machine.
- `auto-run.json` actualizado live (no solo al final): nuevo campo
  `progress` con `{phase, task_index, task_total, sub_phase}`
  reescrito con `tmp + os.replace` (atomic) cada transicion.
- Nuevo subcomando `/sbtdd status --watch` que tail-followea
  `auto-run.json` en intervalos de 1s y renderiza progress en TTY
  (humano-friendly) o JSON (machine-friendly). Default = TTY.

**Invariantes obligatorios**:

- INV-22 sequential preservado — streaming es write-only del
  dispatcher; no introduce parallelism.
- Atomic writes a `auto-run.json` (mismo patron que `state_file.save`
  + `magi-escalation-pending.md` de v0.2.1).
- Stderr breadcrumbs siempre prefijados con `[sbtdd]` para distinguir
  de subprocess output.
- Cross-platform: Windows + POSIX line-buffering identico (test
  cubre ambos).

### 2.2 Feature E — Per-skill model selection flag (cost)

**Problema v0.2**: cero `--model` flags en los tres dispatch modules
(`superpowers_dispatch.py`, `spec_review_dispatch.py`,
`magi_dispatch.py`). Todo subagent hereda el modelo de la sesion del
orquestador. Si el operador corre con Opus default, un `/sbtdd auto`
sobre 36 tasks dispara 36+ implementer dispatches + 36+ spec-reviewer
dispatches + 5-15 MAGI iterations todos en Opus. Bill domina el
costo del proyecto.

**Entrega v1.0.0**:

- `plugin.local.md` schema extension: cuatro campos opcionales
  default `null` (= inherit session, preserva v0.x behavior, fully
  backward compat):
  - `implementer_model: claude-sonnet-4-6` (recommended baseline)
  - `spec_reviewer_model: claude-haiku-4-5` (recommended baseline)
  - `code_review_model: claude-sonnet-4-6` (recommended baseline)
  - `magi_dispatch_model: null` (recommended; outer dispatcher es
    I/O; sub-agentes Melchior/Balthasar/Caspar pickn modelo
    internamente per MAGI plugin contract).
- `schema_version: 2` introducido en `plugin.local.md` (nuevo
  campo, primera vez; bumpa de schema implicit v1 a explicit v2).
- Wiring: cuando un campo es non-null, dispatch module agrega
  `--model <id>` al argv. INV-0 honored: si `~/.claude/CLAUDE.md`
  pina un modelo global, gana sobre `plugin.local.md` y emite
  stderr breadcrumb explicando cost implication.
- CLI override: `--model-override <skill>:<model>` en `auto`,
  `pre-merge`, `close-task`, `review-spec-compliance`. Multi-flag.
  Skill validation: solo cuatro nombres validos
  (`implementer|spec_reviewer|code_review|magi_dispatch`).
- `dependency_check.py` extension: valida que cada model string
  configurado este en `models.ALLOWED_CLAUDE_MODEL_IDS` tuple
  (Opus 4.x, Sonnet 4.x, Haiku 4.x families). Unknown ID = warning
  en `init`, hard fail en runtime.
- `models.py` agrega `ALLOWED_CLAUDE_MODEL_IDS` immutable tuple,
  bumped cuando Anthropic shipea family nueva.

**Invariantes obligatorios**:

- INV-0 (CLAUDE.md pinned model wins; stderr breadcrumb obligatorio).
- Default null = byte-identical argv a v0.x. Regression test pina.
- Schema v2 backward-compat: plugins.local.md sin `schema_version`
  field tratado como v1 (todos los model fields = null implicit).
- MAGI sub-agent models NO controlados por v1.0.0 (caveat
  documentado en CHANGELOG + SKILL.md operational impact).

**Cost-impact projection**: 36-task auto run con Sonnet+Haiku mix vs
default-Opus session = ~70-80% reduccion total, preservando Opus solo
en MAGI Loop 2 iterations donde multi-perspective consensus value
es maximo.

### 2.3 Feature F — MAGI dispatch hardening + retried_agents telemetry

**Problema v0.2**: `magi_dispatch.py` localiza el output de MAGI
buscando un archivo en una ruta esperada bajo `--output-dir`. Si MAGI
cambia el layout (v2.2.x ya lo hizo parcialmente — observado en plan
F del v0.2 cycle), la deteccion rompe. Adicionalmente, MAGI 2.2.1+
introduce un nuevo campo `retried_agents` en su verdict JSON que el
parser de SBTDD ignora silently.

**Entrega v1.0.0**:

- `magi_dispatch.py` cambia de path-based discovery a
  marker-based discovery: cada invocacion MAGI escribe un
  `MAGI_VERDICT_MARKER.json` en un directorio conocido; SBTDD
  enumera markers despues del subprocess return y picks el mas
  reciente by mtime. Defensivo contra cambios de layout interno
  de MAGI.
- Parser extension: `MAGIVerdict` dataclass gana campo
  `retried_agents: tuple[str, ...]`. Parser tolera ausencia (MAGI
  < 2.2.1) defaulting a `()`. Fed back to user output via
  `auto-run.json` + escalation_prompt context.
- Backward compat: SBTDD funciona con MAGI 2.1.x+ y 2.2.x+ sin
  bumps de version requirement; retried_agents simplemente vacio
  en versiones viejas.

**Invariantes obligatorios**:

- INV-28 (degraded MAGI no-exit) + INV-29 (receiving-code-review
  gate) preservados sin cambio.
- Tests parity: MAGI 2.1.x golden output + MAGI 2.2.x+ golden output
  (con + sin retried_agents field) ambos pasan.
- Marker file format: JSON con `verdict`, `iteration`, `agents`,
  `retried_agents`, `timestamp`. Schema fixed in `models.py`.

### 2.4 Feature G — MAGI -> /requesting-code-review cross-check (PRIORITY)

**Problema v0.2**: MAGI Loop 2 a veces emite findings CRITICAL que
son falsos positivos (interpretacion erronea de la spec, asuncion
incorrecta sobre el plan, contexto faltante). El user los validado
empiricamente en proyectos adyacentes corriendo
`/requesting-code-review` AFTER MAGI sobre el mismo diff + el output
MAGI como contexto: el code-reviewer cataches false-positive
CRITICALs y los downgradea a INFO/WARNING o los rechaza directo.
Pattern: MAGI primero (breadth, 3 perspectivas),
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
  INV-11 (es meta-review, no una iteracion del Loop 2 mismo).

### 2.5 Feature H — Group B spec-drift re-eval + INV-31 default-on opt-in re-eval

**Problema v0.2**: siete opciones de spec-drift detection (Group B
options 1-7) deferred a v1.0.0 cuando v0.2 se enfoco en option 8
(spec-reviewer integration via Feature B). Field data de v0.2/v0.2.1/
v0.2.2 no esta complete pero sugiere que option 8 cubre la mayoria
de drift cases per-task. Decision deferida: que subset de options 1-7
se requiere vs opt-in?

Adicionalmente, INV-31 default-on (spec-reviewer per task) introduce
overhead 1-3 `claude -p` calls por task close. Combined con Feature E
(model flag), el overhead se reduce significativamente, pero la
decision strategic queda: el default sigue siendo on, o flips a
opt-in (requiere `--enable-spec-review` per command)?

**Entrega v1.0.0**:

- Field data summary en `docs/v1.0.0-field-data.md` (post-v0.2 dogfood
  observations: how many spec-reviewer rejections were true-positive,
  how many were noise, cumulative cost overhead, etc.).
- Decision document en `docs/v1.0.0-spec-drift-decision.md` evaluando
  cada Group B option contra field data, con recommendations:
  - Option (1) `scenario_coverage_check.py` mechanical regex pre-filter
    -- implementar como pre-filter de Feature B (skip reviewer si task
    no toca scenarios) si field data muestra >30% noise.
  - Option (2) Spec-snapshot diff check -- implementar (LOCKED for
    v1.0.0 regardless of field data; cubre risk class option 8
    cannot).
  - Option (5) Auto-generated scenario stubs -- implementar (strong
    candidate per v0.3 backlog).
  - Options (3), (4), (6), (7) -- opt-in via flags, no shipped default.
- INV-31 default decision: based on field data, one of:
  - **Option A** (preserve default-on): keep current; `--skip-spec-review`
    remains escape valve. Justified si reviewer catches >X true-positive
    drifts per Y tasks.
  - **Option B** (flip to opt-in): rename flag to `--enable-spec-review`
    on `close-task`/`auto`; default skip. Justified si overhead >>
    benefit empiricamente.
  - **Option C** (config-driven): new field `spec_review_default` en
    `plugin.local.md` con `on|off|auto-detect-by-stack`.
- Implementaciones concretas: opciones (2) + (5) shipped; otras
  documentadas como opt-in flags adicionales (no shipped en v1.0.0).
- INV-31 decision adoptada en SKILL.md operational impact + README
  matrix.

**Invariantes obligatorios**:

- Cualquier flip de default INV-31 = BREAKING bump (v1.0.0 absorbe
  multiple BREAKINGs por la graduacion stable).
- Group B options shipped (option 2 spec-snapshot + option 5 auto-gen
  stubs) preservan INV-29 gate sin cambio.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-31 del contrato preservados. v1.0.0
introduce propuestas:

- **INV-32 (propuesta)**: MAGI cross-check via `/requesting-code-review`
  obligatorio antes de INV-29 gate (Feature G), salvo opt-out explicit.
- **INV-31 contract evolution** (preserva o flippea segun decision
  Feature H).

Critical durante implementacion v1.0.0:

- INV-0 (autoridad maxima `~/.claude/CLAUDE.md`) + Feature E model
  flag interaction: pinned model en CLAUDE.md gana siempre.
- INV-22 (sequential auto) + Feature D streaming: streaming es
  write-only, no introduce parallelism.
- INV-26 (audit trail) + Features D, E, G: nuevos artifacts en
  `.claude/auto-run.json` (live), `.claude/magi-cross-check/<...>.json`.
- INV-27 (spec-base placeholder): este documento cumple.
- INV-28, INV-29: preservados sin cambio.

### Stack y runtime

Sin cambios vs v0.2:

- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot paths.
- Dependencias externas: git, tdd-guard, superpowers, magi (>= 2.1.3
  per backward compat de Feature F), claude CLI.
- Dependencias dev: pytest, pytest-asyncio, ruff, mypy, pyyaml.
- Licencia dual MIT OR Apache-2.0.

### Arquitectura obligatoria

v0.2 architecture preserved. v1.0.0 changes:

- `auto_cmd.py`: extender phase loop con streaming (Feature D).
- `superpowers_dispatch.py`, `spec_review_dispatch.py`,
  `magi_dispatch.py`: agregar `--model` argv passing (Feature E).
- `magi_dispatch.py`: marker-based discovery rewrite + retried_agents
  field (Feature F).
- `pre_merge_cmd.py`, `auto_cmd.py`: Loop 2 cross-check sub-fase
  (Feature G).
- `models.py`: agregar `ALLOWED_CLAUDE_MODEL_IDS`, marker schema.
- `config.py`: parsear cuatro nuevos campos plugin.local.md +
  `schema_version` + `magi_cross_check`.
- `dependency_check.py`: validacion de model IDs.
- `templates/plugin.local.md.template`: agregar campos nuevos con
  recommended baseline (Sonnet+Haiku mix).
- Nuevo modulo: `scripts/scenario_coverage_check.py` (Group B
  option 1 mechanical pre-filter -- only if field data justifies).
- Nuevo modulo: `scripts/spec_snapshot.py` (Group B option 2 spec
  diff check, LOCKED).
- Extension a `/writing-plans` invocation: auto-generate scenario
  stubs (Group B option 5, LOCKED).

### Exit code taxonomy

Preservada de v0.2. v1.0.0 propone:

- **Exit 13**: `MODEL_VALIDATION_FAILED` (Feature E
  `dependency_check` rejects unknown model ID en runtime). Adopt si
  el equipo decide expandir taxonomy; alternativa = ValidationError
  exit 1.

---

## 4. Funcionalidad requerida (SDD)

Continua F-series desde v0.2 (F27 fue el ultimo). v1.0.0:

**F28**. `auto_cmd._stream_subprocess(proc)` lee stdout/stderr line-by-line
y reescribe con prefijo `[sbtdd task-N phase] `. `bufsize=1`,
`subprocess.PIPE`, `python -u` en el invocation argv.

**F29**. `auto_cmd._update_progress(phase, task_idx, task_total, sub_phase)`
reescribe `auto-run.json` `progress` field via tmp + `os.replace`.

**F30**. `status_cmd --watch` poll loop sobre `auto-run.json` mtime con
intervalo 1s, render TTY o JSON.

**F31**. `config.PluginConfig` gana cuatro campos opcionales (`Optional[str]`
default None): `implementer_model`, `spec_reviewer_model`,
`code_review_model`, `magi_dispatch_model`. + `schema_version: int = 1`.
+ `magi_cross_check: bool = True`.

**F32**. `superpowers_dispatch.dispatch_skill(skill_name, args, model=None)`
agrega `--model` al argv si `model is not None`. INV-0 check: si
`~/.claude/CLAUDE.md` pinned model detected, ignore `model` arg + emit
breadcrumb.

**F33**. Mismo pattern para `spec_review_dispatch.dispatch_spec_reviewer`
(consume `code_review_model` + `spec_reviewer_model`) y
`magi_dispatch.dispatch_magi` (consume `magi_dispatch_model`).

**F34**. CLI flag `--model-override <skill>:<model>` parser + validation
en `auto_cmd`, `pre_merge_cmd`, `close_task_cmd`,
`review_spec_compliance_cmd`. Multi-flag accumulator. Skill name
validation contra cuatro nombres canonicos.

**F35**. `dependency_check.check_model_ids(config)` valida que cada
non-null model field este en `models.ALLOWED_CLAUDE_MODEL_IDS`.

**F36**. `magi_dispatch._discover_verdict_marker(output_dir)`
enumera `MAGI_VERDICT_MARKER.json` files, picks max mtime. Replace
path-based discovery.

**F37**. `MAGIVerdict.retried_agents: tuple[str, ...]` field. Parser
tolera ausencia.

**F38**. `pre_merge_cmd._loop2_cross_check(diff, magi_verdict)` invoke
`/requesting-code-review` con prompt instructivo de meta-review.
Output = filtered findings set. Audit artifact escrito.

**F39**. `auto_cmd._phase4_pre_merge_loop2` adopta cross-check.

**F40**. `scenario_coverage_check.py` (condicional, solo si Feature H
field data justifica).

**F41**. `spec_snapshot.py` + `pre_merge_cmd` integration (LOCKED Group B
option 2).

**F42**. `/writing-plans` invocation extiende prompt para auto-generate
scenario stubs per task (LOCKED Group B option 5).

### Requerimientos no-funcionales (NF)

**NF13**. Streaming subprocess output adds < 5% wall-time overhead
en autos benchmark (medible via `tests/test_auto_cmd_streaming.py`).

**NF14**. Cross-platform: streaming buffer/line endings funciona
identicamente Windows + POSIX.

**NF15**. `make verify` runtime <= 90s budget (era 60s en v0.2;
v1.0.0 absorbe regression de tests adicionales).

---

## 5. Scope exclusions

Out-of-scope para v1.0.0:

- GitHub Actions CI workflow (deferred to v1.1).
- C++ stack adapters adicionales (Catch2, GoogleTest) -- solo ctest
  preserved (deferred to v1.1).
- Marketplace `$schema` URL post-push verification (deferred to v1.1).
- MAGI sub-agent model control (out of SBTDD scope; MAGI plugin
  responsability).
- Streaming UI / TUI dashboard (CLI status --watch suficiente para
  v1.0.0; dashboard deferred to v1.1+).

---

## 6. Criterios de aceptacion finales

### 6.1 Functional (Feature D -- auto streaming)

- **D1**. `auto_cmd` subprocess invocation usa `python -u` + line buffering.
- **D2**. Stderr breadcrumbs prefijados `[sbtdd task-N phase]` cada
  state transition.
- **D3**. `auto-run.json progress` field reescrito atomicamente cada
  transition.
- **D4**. `/sbtdd status --watch` funcional TTY + JSON.
- **D5**. NF13 cumplido (< 5% overhead).

### 6.2 Functional (Feature E -- model flag)

- **E1**. Cuatro campos optional en `plugin.local.md` parseados.
- **E2**. CLI `--model-override` funcional con multi-flag + validation.
- **E3**. INV-0 precedence enforced + stderr breadcrumb.
- **E4**. `dependency_check` valida model IDs.
- **E5**. Default null = byte-identical argv a v0.x (regression test).
- **E6**. `schema_version: 2` documentado.

### 6.3 Functional (Feature F -- MAGI hardening)

- **F1**. Marker-based discovery reemplaza path-based.
- **F2**. `retried_agents` parsed + propagado a `auto-run.json` + escalation.
- **F3**. Backward-compat MAGI 2.1.x + 2.2.x+ tests pasan.

### 6.4 Functional (Feature G -- cross-check)

- **G1**. Loop 2 cross-check sub-fase implementada.
- **G2**. Audit artifact `.claude/magi-cross-check/...` escrito.
- **G3**. INV-32 (propuesta) documentado + adoptado o rejected.
- **G4**. Default `magi_cross_check: true`; opt-out via plugin.local.md.

### 6.5 Functional (Feature H -- re-eval)

- **H1**. Field data documento escrito.
- **H2**. INV-31 default decision adoptada (one of: preserve / flip /
  config-driven).
- **H3**. Group B options (2) + (5) implementadas; (1), (3), (4),
  (6), (7) opt-in flags or rejected with rationale.

### 6.6 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict, runtime <= 90s.
- **NF-B**. Tests totales >= 735 baseline + nuevos (proyeccion 80-150
  extras).
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en nuevos `.py` files.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados
  explicitamente.

### 6.7 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter budget 3 + INV-0 override available.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict >=
  `GO_WITH_CAVEATS` full. Cross-check (Feature G) self-validates
  durante el ciclo.
- **P3**. CHANGELOG.md `[1.0.0]` entry con BREAKING / Added / Changed.
- **P4**. Version bump 0.2.2 -> 1.0.0 sync `plugin.json` +
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
(ya presente).

---

## 8. Risk register v1.0.0

- **R1**. Streaming overhead > NF13 5% budget -- mitigation: optimizar
  read-line loop, considerar no-blocking I/O si excede budget.
- **R2**. Marker-based MAGI discovery rompe si MAGI 2.2.x cambia
  marker schema -- mitigation: SBTDD tolera ausencia de campos
  opcionales en marker, requiere mantener test contra MAGI versions
  cacheadas.
- **R3**. Cross-check (Feature G) introduce false-negative risk
  (downgrades CRITICAL real a INFO) -- mitigation: audit artifact
  permite post-mortem; INV-32 caveat documentado.
- **R4**. INV-31 flip decision sin field data sufficient -- mitigation:
  bundle Feature H ultimo en el ciclo, despues de v0.2.x dogfood data
  acumulada.
- **R5**. Schema bump v1 -> v2 sin migration tool -- mitigation: parser
  defaulta `schema_version: 1` cuando ausente; warning at load if old.
- **R6**. Bundle 5 features en un solo cycle = MAGI Checkpoint 2 verdict
  difficult -- mitigation: prepared INV-0 override path; alternativamente
  split en sub-ciclos (decision durante brainstorming).

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- Frozen v0.2 BDD overlay: previous `sbtdd/spec-behavior.md` (will be
  archived once v1.0.0 spec written).
- v1.0.0 LOCKED specs detalladas: memory files
  - `project_v100_progress_streaming.md`
  - `project_v100_per_skill_model_flag.md`
  - `project_v100_magi_dispatch_hardening.md`
  - `project_v100_magi_cross_check.md` (PRIORITY)
  - Re-eval: backlog notes en CLAUDE.md "v1.0.0 backlog" section.
- Field data input: `.claude/auto-run.json` archives + spec-reviews
  artifacts from v0.2/v0.2.1/v0.2.2 dogfood.
- Historical precedent: v0.2.0 INV-0 override commit `5d7bfc4`,
  v0.2.1 lightweight pattern (commits `9622a55`..`cfb39ee`),
  v0.2.2 docs hotfix (commit `337aba2`).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (scan: 0 matches uppercase placeholder).
Listo como input para `/brainstorming`. Decision pendiente clave para
brainstorming: bundle 5 features in one cycle, o split en sub-ciclos
(p.ej. v0.3.0 = D+E operational; v0.4.0 = F+G MAGI; v1.0.0 = H + tag
estable). Brainstorming refinara esta decision basado en complejidad
estimada y MAGI Checkpoint 2 risk.
