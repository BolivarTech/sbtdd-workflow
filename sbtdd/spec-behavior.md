# BDD overlay — sbtdd-workflow v0.3.0

> Generado por `/brainstorming` el 2026-04-25 a partir de
> `sbtdd/spec-behavior-base.md` (v1.0.0 raw input). v0.3.0 cubre el
> sub-set v1.0.0 D+E (operational hardening: auto streaming + per-skill
> model selection flag) per directiva usuario sesion 2026-04-25
> ("split (b)" + "lightweight pattern (a)" + "balanced trim (2)").
>
> v0.4.0/v1.0.0 cubren los items deferred (D5 `status --watch`, E2
> `schema_version: 2`, Features F+G+H -- MAGI hardening + cross-check
> + Group B re-eval).
>
> Este BDD overlay materializa los criterios sec.S.12 del spec-base
> en escenarios Given/When/Then testables. INV-27 compliant: cero
> matches uppercase placeholder (verificado).

---

## 1. Resumen ejecutivo

**Objetivo v0.3.0**: ship dos features operacionales aditivos
(no-BREAKING) en un ciclo lightweight (~4-6h wall time, 2 subagents
paralelos + final review loop MAGI). Bumpa 0.2.2 -> 0.3.0 (MINOR).

**Out-of-scope v0.3.0** (deferred):
- D5 `/sbtdd status --watch` subcomando.
- E2 `schema_version: 2` field en `plugin.local.md`.
- Features F (MAGI marker discovery + retried_agents), G (cross-check
  via `/requesting-code-review`), H (Group B re-eval + INV-31 default
  flip).

**Criterio de exito**: bumpa 0.2.2->0.3.0 sin regresion (735 tests
baseline preservados + 50-70 nuevos) + `/sbtdd auto` arranque de v1.0.0
cycle gana ~70-80% cost reduction inmediato cuando el operador adopta
el Sonnet+Haiku baseline.

---

## 2. Feature D -- Auto progress streaming

### 2.1 Scope (4 deliverables)

- **D1**. `auto_cmd._stream_subprocess(proc)` -- read-line loop con
  prefijo orquestador.
- **D2**. `python -u` en argv del subprocess.
- **D3**. State-machine breadcrumbs por phase transition.
- **D4**. `auto-run.json` `progress` field atomic write.

### 2.2 Escenarios Given/When/Then

**Escenario D1.1: streaming flushes subprocess output line-by-line**

> **Given** un `/sbtdd auto` con un implementer subagent que escribe
> 5 lineas a stdout separadas por 200ms.
> **When** `auto_cmd._stream_subprocess(proc)` consume las pipes.
> **Then** las 5 lineas aparecen en stderr del orquestador con
> latencia maxima 250ms cada una (no se acumulan hasta proc exit).

**Escenario D1.2: stderr breadcrumbs prefijados con `[sbtdd ...]`**

> **Given** un subprocess invocando `/test-driven-development` que
> emite a su propio stderr `[skill] starting red phase`.
> **When** `_stream_subprocess` reescribe la linea al stderr del
> orquestador.
> **Then** la linea final lleva prefijo `[sbtdd task-N phase] [skill]
> starting red phase`, distinguiendo origen sbtdd de origen subprocess.

**Escenario D1.3: streaming sobrevive a SIGTERM cleanup**

> **Given** un `/sbtdd auto` interrumpido con Ctrl+C mid-task.
> **When** la state machine recibe SIGINT.
> **Then** `_stream_subprocess` flushea buffers pendientes a stderr
> orquestador antes de exit 130, preservando ultima senal de progreso
> visible.

**Escenario D2.1: python -u en argv del subprocess**

> **Given** `auto_cmd` invocando subprocess `run_sbtdd.py`.
> **When** se construye argv.
> **Then** argv = `["python", "-u", "<run_sbtdd.py>", "<subcommand>",
> ...]` (no `["python", "<run_sbtdd.py>", ...]`).

**Escenario D3.1: state-machine breadcrumb on red->green transition**

> **Given** task 14/36 en fase red, ultimo verification passed.
> **When** `auto_cmd._phase2_task_loop` avanza fase a green.
> **Then** stderr orquestador recibe linea exacta:
> `[sbtdd] phase 2/5: task loop -- task 14/36 (green)` ANTES del
> dispatch del siguiente subagent.

**Escenario D3.2: breadcrumb on task close**

> **Given** task 14/36 cerrando refactor + chore: mark complete.
> **When** state machine avanza task_index 14 -> 15.
> **Then** stderr orquestador recibe `[sbtdd] phase 2/5: task loop --
> task 15/36 (red)` despues del commit `chore:` y antes del nuevo
> implementer dispatch.

**Escenario D4.1: progress field reescrito atomicamente cada transition**

> **Given** `.claude/auto-run.json` existing con `progress: {phase: 2,
> task_index: 13, task_total: 36, sub_phase: "refactor"}`.
> **When** state machine transitions a task 14 red.
> **Then** un escritor concurrente leyendo `auto-run.json` durante el
> write nunca observa estado intermediate corrupto: lee o el progress
> previo (task 13 refactor) o el posterior (task 14 red), nunca un
> JSON parcial.

**Escenario D4.2: progress field schema correcto**

> **Given** mid-`auto` run.
> **When** se carga `auto-run.json` con `json.load`.
> **Then** keys top-level incluyen `progress` con shape exacto
> `{"phase": int, "task_index": int, "task_total": int, "sub_phase":
> str}`. `phase` ∈ {0..5}, `sub_phase` ∈ {"red", "green", "refactor",
> "task-close", "magi-loop", "checklist"}.

**Escenario D4.3: progress field absent en auto-run.json antes del primer phase**

> **Given** `auto_cmd` recien iniciado, antes de phase 1.
> **When** se carga `auto-run.json` (que ya existe del checkpoint
> initial pero sin progress).
> **Then** `progress` field es opcional (parser tolera ausencia,
> default `None` o `{}`); no es schema-required.

### 2.3 Acceptance criteria mapping (sec.S.12 v0.3.0)

| Criterion | Escenario | Test fixture |
|-----------|-----------|--------------|
| **D1**: subprocess streaming line-by-line | D1.1, D1.2, D1.3 | `tests/test_auto_streaming.py` |
| **D2**: `python -u` en argv | D2.1 | `tests/test_auto_streaming.py` |
| **D3**: stderr breadcrumbs por phase | D3.1, D3.2 | `tests/test_auto_streaming.py` |
| **D4**: `auto-run.json progress` atomic write | D4.1, D4.2, D4.3 | `tests/test_auto_progress.py` |

### 2.4 Invariantes Feature D

- INV-22 (sequential auto) preservado -- streaming es write-only.
- Atomic writes a `auto-run.json` mismo patron que `state_file.save`
  + `magi-escalation-pending.md` (v0.2.1).
- Cross-platform: Windows + POSIX line-buffering identico (test
  cubre ambos).
- Streaming no introduce latencia perceptible: NF13 < 5% wall-time
  overhead (medido benchmark mock auto run).

---

## 3. Feature E -- Per-skill model selection flag

### 3.1 Scope (6 deliverables)

- **E1**. 4 campos opcionales en `config.PluginConfig`.
- **E3**. Dispatch wiring + INV-0 precedence.
- **E4**. `--model-override <skill>:<model>` CLI en `auto`.
- **E5**. `dependency_check.check_model_ids`.
- **E6**. `models.ALLOWED_CLAUDE_MODEL_IDS` immutable tuple.
- **E7**. Template `plugin.local.md.template` ships Sonnet+Haiku baseline.

**Deferred a v1.0.0**: E2 (`schema_version: 2`).

### 3.2 Escenarios Given/When/Then

**Escenario E1.1: 4 campos parseados de plugin.local.md**

> **Given** un `plugin.local.md` con frontmatter:
> ```yaml
> implementer_model: claude-sonnet-4-6
> spec_reviewer_model: claude-haiku-4-5
> code_review_model: claude-sonnet-4-6
> magi_dispatch_model: null
> ```
> **When** `config.load(path)` parsea el archivo.
> **Then** retorna `PluginConfig(implementer_model="claude-sonnet-4-6",
> spec_reviewer_model="claude-haiku-4-5",
> code_review_model="claude-sonnet-4-6", magi_dispatch_model=None, ...)`.

**Escenario E1.2: campos ausentes default None (backward compat)**

> **Given** un `plugin.local.md` v0.2 sin ninguno de los 4 model fields.
> **When** `config.load(path)` parsea.
> **Then** retorna `PluginConfig` con todos los 4 model fields = None.
> Ningun error, ningun warning. Plugin v0.2 plugin.local.md files cargan
> sin migracion.

**Escenario E1.3: campo invalido (typo en YAML key) ignorado silenciosamente**

> **Given** `plugin.local.md` con campo `implementer-model:
> claude-sonnet-4-6` (dash en vez de underscore).
> **When** `config.load(path)` parsea.
> **Then** `implementer_model` = None (campo desconocido ignorado),
> stderr emite warning `[sbtdd] unknown plugin.local.md key:
> implementer-model -- did you mean implementer_model?`.

**Escenario E3.1: dispatch con model=None = byte-identical argv a v0.2**

> **Given** `superpowers_dispatch.dispatch_skill("test-driven-development",
> args, model=None)`.
> **When** se construye argv.
> **Then** argv = `["claude", "-p", "/test-driven-development", *args]`
> (idéntico a v0.2.x; ningun `--model` flag presente).

**Escenario E3.2: dispatch con model="claude-haiku-4-5" agrega --model**

> **Given** `superpowers_dispatch.dispatch_skill("test-driven-development",
> args, model="claude-haiku-4-5")`.
> **When** se construye argv.
> **Then** argv = `["claude", "-p", "--model", "claude-haiku-4-5",
> "/test-driven-development", *args]`. Order: `--model` antes del
> skill path.

**Escenario E3.3: INV-0 precedence -- CLAUDE.md pinned model wins**

> **Given** `~/.claude/CLAUDE.md` contiene linea
> `Use claude-opus-4-7 for all sessions` (detectable por scan).
> **And** `plugin.local.md` tiene `implementer_model:
> claude-sonnet-4-6`.
> **When** `superpowers_dispatch.dispatch_skill(...,
> model="claude-sonnet-4-6")` (pasado de config).
> **Then** argv NO contiene `--model claude-sonnet-4-6`. Stderr emite
> breadcrumb: `[sbtdd inv-0] CLAUDE.md pins claude-opus-4-7 globally;
> ignoring plugin.local.md implementer_model=claude-sonnet-4-6 to
> respect global authority. Cost implication: ~5x vs configured
> Sonnet baseline.`

**Escenario E3.4: INV-0 detection no-pinned = config respetada**

> **Given** `~/.claude/CLAUDE.md` no contiene patron `claude-opus-X` /
> `claude-sonnet-X` / `claude-haiku-X` pinning.
> **When** dispatch fires con model="claude-sonnet-4-6".
> **Then** argv contiene `--model claude-sonnet-4-6`. Ningun breadcrumb.

**Escenario E4.1: --model-override con skill name valido acepta**

> **Given** `/sbtdd auto --model-override implementer:claude-haiku-4-5`.
> **When** `auto_cmd` parsea CLI args.
> **Then** `auto_cmd._cli_model_overrides` = `{"implementer":
> "claude-haiku-4-5"}`. Override gana sobre `plugin.local.md` para
> ese skill solamente; los otros 3 skills siguen usando config.

**Escenario E4.2: --model-override con skill name invalido rechaza**

> **Given** `/sbtdd auto --model-override foo:claude-haiku-4-5` (foo
> no es uno de los 4 skill names canonicos).
> **When** `auto_cmd` parsea CLI args.
> **Then** exit code 1 (USER_ERROR). Stderr: `[sbtdd] invalid
> --model-override skill name 'foo'. Valid: implementer,
> spec_reviewer, code_review, magi_dispatch.`

**Escenario E4.3: multi-flag accumulator**

> **Given** `/sbtdd auto --model-override
> implementer:claude-haiku-4-5 --model-override
> spec_reviewer:claude-sonnet-4-6`.
> **When** parser procesa.
> **Then** `_cli_model_overrides` = `{"implementer":
> "claude-haiku-4-5", "spec_reviewer": "claude-sonnet-4-6"}` (ambos
> presentes).

**Escenario E4.4: --model-override pierde contra INV-0 pinned**

> **Given** `/sbtdd auto --model-override
> implementer:claude-haiku-4-5` + `~/.claude/CLAUDE.md` pina
> claude-opus-4-7.
> **When** dispatch fires.
> **Then** argv usa modelo de session (no `--model`), stderr emite
> breadcrumb INV-0 mencionando que el CLI override fue ignorado en
> favor del global pin.

**Escenario E4.5: --model-override format invalido (sin ":") rechaza**

> **Given** `/sbtdd auto --model-override implementerhaiku4-5` (sin
> separator).
> **When** parser procesa.
> **Then** exit 1, stderr `[sbtdd] --model-override expects
> '<skill>:<model>'; got 'implementerhaiku4-5'`.

**Escenario E5.1: dependency_check warns en init para model ID desconocido**

> **Given** `plugin.local.md` con `implementer_model:
> claude-sonnet-9-9` (no en `ALLOWED_CLAUDE_MODEL_IDS`).
> **When** `/sbtdd init` corre dependency_check.
> **Then** init no fail (exit 0); stderr emite warning `[sbtdd init]
> implementer_model 'claude-sonnet-9-9' not in known model list. Will
> hard-fail at runtime if Anthropic does not recognize this ID. Verify
> spelling.`

**Escenario E5.2: dependency_check hard-fails en runtime para model ID desconocido**

> **Given** `plugin.local.md` con `implementer_model:
> claude-sonnet-9-9`. Subagent dispatch fires.
> **When** `superpowers_dispatch.dispatch_skill(...,
> model="claude-sonnet-9-9")` ejecuta y `claude` CLI rejecta el flag.
> **Then** raise `ValidationError("Unknown model 'claude-sonnet-9-9'.
> Configured in plugin.local.md implementer_model. Update to one of
> ALLOWED_CLAUDE_MODEL_IDS or remove the field.")`. Exit 1.

**Escenario E6.1: ALLOWED_CLAUDE_MODEL_IDS es immutable**

> **Given** `from models import ALLOWED_CLAUDE_MODEL_IDS`.
> **When** intento `ALLOWED_CLAUDE_MODEL_IDS.append(...)` o
> `ALLOWED_CLAUDE_MODEL_IDS[0] = ...`.
> **Then** raise `AttributeError` (es `tuple[str, ...]`, no list) o
> `TypeError` (immutable). Test pina contra mutation.

**Escenario E6.2: ALLOWED_CLAUDE_MODEL_IDS contiene families 4.x actuales**

> **Given** `models.ALLOWED_CLAUDE_MODEL_IDS`.
> **When** se enumera.
> **Then** contiene al menos: `claude-opus-4-7`, `claude-sonnet-4-6`,
> `claude-haiku-4-5-20251001`. (Lista exacta refrescable cada family
> bump; pero la presencia de las 3 actuales es regression-pinned).

**Escenario E7.1: template ships Sonnet+Haiku baseline (commented)**

> **Given** `templates/plugin.local.md.template`.
> **When** se renderiza con substitutions standard de `init --stack
> python --author "Foo"`.
> **Then** output contiene los 4 fields como comentarios YAML:
> ```yaml
> # Recommended cost-optimized baseline (uncomment to opt in):
> # implementer_model: claude-sonnet-4-6
> # spec_reviewer_model: claude-haiku-4-5
> # code_review_model: claude-sonnet-4-6
> # magi_dispatch_model: null   # outer dispatcher, sub-agents pick own
> ```
> Default null preservado (todos comentados); operador opt-in
> uncommentando.

**Escenario E7.2: init --stack python expande template preservando comentarios**

> **Given** `init --stack python --author "Test"` ejecutando.
> **When** template se expande a destination project's
> `.claude/plugin.local.md`.
> **Then** las 4 lineas commented (Sonnet+Haiku baseline) estan
> presentes en el archivo final. Operador puede uncommentar con un
> editor sin re-correr init.

### 3.3 Acceptance criteria mapping (sec.S.12 v0.3.0)

| Criterion | Escenario | Test fixture |
|-----------|-----------|--------------|
| **E1**: 4 fields opcionales parseados | E1.1, E1.2, E1.3 | `tests/test_config_model_fields.py` |
| **E3**: dispatch wiring + INV-0 | E3.1, E3.2, E3.3, E3.4 | `tests/test_dispatch_model_arg.py` |
| **E4**: CLI override en `auto` | E4.1, E4.2, E4.3, E4.4, E4.5 | `tests/test_cli_model_override.py` |
| **E5**: dependency_check models | E5.1, E5.2 | `tests/test_dependency_check_models.py` |
| **E6**: ALLOWED_CLAUDE_MODEL_IDS immutable | E6.1, E6.2 | `tests/test_models_constants.py` |
| **E7**: template baseline | E7.1, E7.2 | `tests/test_init_cmd.py` (existing, extended) |

### 3.4 Invariantes Feature E

- **INV-0** (CLAUDE.md prevails): pinned model en CLAUDE.md gana
  siempre. Cascade: CLAUDE.md > CLI `--model-override` > plugin.local.md
  > None (inherit session). Stderr breadcrumb obligatorio cuando
  CLAUDE.md pin fires.
- **Default null = byte-identical argv a v0.2.x**. Escenario E3.1
  pina; cualquier regression en argv shape rompe esta invariante.
- **MAGI sub-agent models NO controlados**: el field
  `magi_dispatch_model` afecta SOLO el outer dispatcher (proceso que
  invoca `claude -p /magi:magi`). Los 3 sub-agentes
  Melchior/Balthasar/Caspar pickan modelo internamente per MAGI plugin
  contract. Documentado en CHANGELOG + SKILL.md operational impact.
- **No-BREAKING**: ningun field requerido nuevo, ningun default flip,
  ningun exit code nuevo. v0.2 plugin.local.md files load sin
  migration.

---

## 4. Final review loop (post-implementation)

### 4.1 Scope

Despues de que ambos subagents (D + E) reporten DONE + working tree
limpio, ejecuta loop MAGI -> /receiving-code-review hasta exit
criterion o cap.

### 4.2 Escenarios

**Escenario R1.1: exit cuando MAGI verdict GO_WITH_CAVEATS clean**

> **Given** iter 1 del final review loop. MAGI emite verdict
> `GO_WITH_CAVEATS` full (3 agentes consensus, no degraded), 0
> findings `[CRITICAL]`, 0 findings `[WARNING]`, 0 Conditions for
> Approval pendientes.
> **When** verdict parser evalua exit criterion.
> **Then** loop sale con SHIP. Proceder a version bump 0.2.2 -> 0.3.0
> + tag + push.

**Escenario R1.2: continue cuando hay CRITICAL findings**

> **Given** iter 1. MAGI emite `GO_WITH_CAVEATS` full pero con 2
> findings `[CRITICAL]`.
> **When** parser evalua exit.
> **Then** NO exit. Route findings via `/receiving-code-review` (INV-29
> gate). Findings aceptadas -> mini-cycle TDD per finding (test: ->
> fix: -> refactor:) con `commits.create`. Findings rechazadas
> documentadas + alimentadas como contexto en iter 2 MAGI invocation.

**Escenario R1.3: continue cuando hay WARNING findings o Conditions**

> **Given** iter 1. MAGI emite `GO_WITH_CAVEATS` full, 0 CRITICAL, pero
> 3 findings `[WARNING]` + 2 Conditions for Approval ("address before
> merge").
> **When** parser evalua exit.
> **Then** NO exit. Mismo pipeline R1.2 (route via
> /receiving-code-review + mini-cycle).

**Escenario R1.4: continue cuando MAGI degraded (INV-28)**

> **Given** iter 1. MAGI verdict `GO_WITH_CAVEATS` pero `degraded:
> true` (solo 2 agentes retornaron output usable).
> **When** parser evalua exit + INV-28 check.
> **Then** verdict NO cuenta como exit signal (per INV-28). Iter
> consumed. Re-invoke MAGI esperando full 3-agent consensus en iter 2.
> Excepcion: si verdict degraded es `STRONG_NO_GO`, abort inmediato
> (sec.S.10.3).

**Escenario R1.5: cap 5 iter exhausted -> escalation_prompt**

> **Given** iter 5 completed. Verdict aun no cumple exit criterion
> (sigue con CRITICAL o WARNING findings).
> **When** loop counter alcanza cap.
> **Then** trigger `escalation_prompt.py` con context `pre-merge`,
> findings clasificadas, root-cause inference. Operador elige (a)
> override INV-0 con `--reason` mandatory, (b) retry +1 (extiende cap
> a 6), (c) replan, (d) abort (default headless).

**Escenario R1.6: rejected findings alimentan contexto MAGI iter+1**

> **Given** iter 2 con MAGI emitiendo finding `[CRITICAL] race
> condition in _stream_subprocess`. `/receiving-code-review` evalua y
> rechaza con razon "false positive: subprocess module is GIL-protected
> for line-buffered reads on POSIX, equivalent on Windows via
> WaitForMultipleObjects".
> **When** se construye prompt para MAGI iter 3.
> **Then** prompt incluye sub-section "Previous findings rejected with
> rationale: [iter 2] race condition in _stream_subprocess --
> rejected: GIL-protected line reads on POSIX, equivalent Windows
> guarantee. Do not re-raise unless new evidence." Reduce loops
> esteriles.

**Escenario R1.7: Loop 1 surrogate via make verify**

> **Given** ambos subagents reportan DONE. `make verify` ejecuta:
> pytest, ruff check, ruff format --check, mypy --strict.
> **When** todos los 4 checks return exit 0.
> **Then** Loop 1 (`/requesting-code-review`) considerado satisfied
> per shortcut documentado v0.3.0 (SBTDD INV-9 interpretation: clean
> mechanical lint = clean Loop 1 surrogate). Avanzar a Loop 2 MAGI.

### 4.3 Acceptance criteria mapping

| Criterion | Escenario | Notes |
|-----------|-----------|-------|
| Exit on GO_WITH_CAVEATS clean | R1.1 | No CRITICAL, no WARNING |
| Continue on CRITICAL/WARNING | R1.2, R1.3 | Mini-cycle TDD per finding |
| INV-28 degraded handling | R1.4 | Iter consumed, re-invoke |
| Cap exhaustion -> escalation_prompt | R1.5 | Feature A v0.2.0 |
| Sterile loop prevention | R1.6 | Rejected findings contextualizadas |
| Loop 1 shortcut justification | R1.7 | Documented en CHANGELOG Process notes |

### 4.4 Invariantes final review

- INV-9 (Loop 2 requires Loop 1 clean): satisfied via `make verify`
  surrogate; shortcut documentado en CHANGELOG.
- INV-11 (safety valve): cap 5 iteraciones (mas alto que default 3
  per Feature A precedent v0.2.0).
- INV-28 (MAGI degraded): preservado.
- INV-29 (/receiving-code-review gate): cada finding enrutada antes
  de mini-cycle TDD.

---

## 5. Subagent layout + execution timeline

### 5.1 Layout

| Phase | Duracion proyectada | Subagents | Output |
|-------|--------------------|-----------|--------|
| 0. Spec base + brainstorming + spec-behavior.md | DONE | -- | esta seccion + spec-base |
| 1. Subagent #1 (D) | ~2.5h | 1 paralelo | 4 atomic commits (Red/Green/Refactor + integ) |
| 1. Subagent #2 (E) | ~2.5h | 1 paralelo | ~6 atomic commits |
| 2. `make verify` post-merge | ~5min | -- | 4 checks clean |
| 3. Final review loop MAGI -> /receiving-code-review | 1.5-3h | -- | 1-5 iter, exit en GO_WITH_CAVEATS clean |
| 4. Version bump + tag + push | ~10min | -- | 0.2.2 -> 0.3.0 |
| **Total wall time** | **~4-6h** | -- | -- |

### 5.2 Subagent dispatch contracts

**Subagent #1 (D)**:
- Input: spec-behavior.md sec.2 (Feature D scope + escenarios D1-D4).
- Tools: Edit, Write, Bash (para `make verify`), Read, Grep, Glob.
- TDD-Guard: ON (ciclo Red->Green->Refactor enforced).
- Output: atomic commits con prefijos sec.M.5 + actualizacion
  state-file por phase.
- Files tocados: `skills/sbtdd/scripts/auto_cmd.py` +
  `tests/test_auto_streaming.py` +
  `tests/test_auto_progress.py`.
- Done criterion: 4 deliverables D1-D4 implemented + tests passing
  + `make verify` clean.

**Subagent #2 (E)**:
- Input: spec-behavior.md sec.3 (Feature E scope + escenarios E1-E7).
- Tools: idem.
- TDD-Guard: ON.
- Files tocados: `skills/sbtdd/scripts/config.py` (extension),
  `skills/sbtdd/scripts/superpowers_dispatch.py` (extension),
  `skills/sbtdd/scripts/spec_review_dispatch.py` (extension),
  `skills/sbtdd/scripts/magi_dispatch.py` (extension),
  `skills/sbtdd/scripts/models.py` (extension),
  `skills/sbtdd/scripts/dependency_check.py` (extension),
  `skills/sbtdd/scripts/auto_cmd.py` (CLI override parser solo) +
  `templates/plugin.local.md.template` (extension) + 6 nuevos test
  modules.
- Done criterion: 6 deliverables E1, E3-E7 implemented + tests
  passing + `make verify` clean.

**Coordination**: ambos subagents tocan `auto_cmd.py` (D toca
streaming logic; E toca CLI parser solo). Files-conflict riesgo
mitigado: D escribe `_stream_subprocess` + `_update_progress`; E
escribe `_parse_model_overrides` + `_apply_inv0_check`. Funciones
disjuntas. Si conflicto en commit, subagent #2 espera + rebases.

### 5.3 Final review loop dispatch

**Loop driver**: orquestador session (no subagent), invoca:
1. `/magi:magi revisa v0.3.0 diff` directamente (no via
   `pre_merge_cmd` -- lightweight pattern, skip Loop 1 formal).
2. Parsea verdict + findings.
3. Si exit cumple -> ship. Si no, dispatcha subagent #3 con findings
   filtradas (post-receiving-code-review).
4. Subagent #3 corre mini-cycle TDD per finding.
5. Loop hasta cap o exit.

---

## 6. Version + distribution

### 6.1 Bump

`plugin.json` + `marketplace.json`: 0.2.2 -> 0.3.0 (MINOR).

Justificacion MINOR (no MAJOR): aditivo puro, no BREAKING, default
null preserva v0.2.x behavior byte-identical.

### 6.2 CHANGELOG.md `[0.3.0]` sections

- **Added** -- Features D + E + 50-70 nuevos tests.
- **Changed** -- (vacio para v0.3.0; ningun behavior change).
- **Process notes** -- Loop 1 surrogate via `make verify`
  documentado (justificacion: lightweight pattern v0.3.0 scope).
- **Deferred a v1.0.0** -- D5, E2, F, G, H.

### 6.3 README + SKILL.md

- README: agregar seccion "Cost optimization" con matriz Sonnet+Haiku
  baseline vs full Opus.
- SKILL.md: nueva seccion `## v0.3 flags` mencionando
  `--model-override`.
- CLAUDE.md (proyecto): agregar `## v0.3.0 release notes` apuntando
  a CHANGELOG entry.

---

## 7. Risk register v0.3.0

- **R1**. Subagents paralelos en `auto_cmd.py` -- mitigacion:
  funciones disjuntas (D toca _stream_subprocess + _update_progress;
  E toca _parse_model_overrides solo); rebase no-fast-forward si
  commits clash; subagent #2 ultimo.
- **R2**. Streaming overhead > NF13 5% -- mitigacion: benchmark con
  mock `auto_cmd` corriendo 10 fake tasks; si excede, switch a
  `select.select` non-blocking I/O.
- **R3**. INV-0 detection en CLAUDE.md scan -- mitigacion: regex
  contra patrones explicitos (`use claude-X-Y for`, `pin claude-X-Y`,
  etc.); false-positive rate ~0; documentar regex en `models.py`.
- **R4**. Final review loop MAGI 5-iter exhaustion -- mitigacion:
  escalation_prompt v0.2.0 maduro + INV-0 override precedent
  disponible.
- **R5**. ALLOWED_CLAUDE_MODEL_IDS staleness (Anthropic shipea
  family nueva durante v0.3 cycle) -- mitigacion: hard-fail at
  runtime con error message accionable; bump tuple en `models.py`
  como hotfix v0.3.1.

---

## 8. Acceptance criteria final v0.3.0

v0.3.0 ship-ready cuando:

- [ ] Feature D 4 deliverables implementados + escenarios D1-D4 pass.
- [ ] Feature E 6 deliverables implementados + escenarios E1-E7 pass.
- [ ] Final review loop alcanzado exit en <= 5 iter con MAGI verdict
      `GO_WITH_CAVEATS` full + 0 CRITICAL + 0 WARNING + 0 Conditions
      pendientes.
- [ ] `make verify` clean (pytest + ruff + mypy --strict).
- [ ] Tests baseline 735 preservados + 50-70 nuevos = 785-805.
- [ ] CHANGELOG `[0.3.0]` entry escrita.
- [ ] Version bump 0.2.2 -> 0.3.0 sync `plugin.json` +
      `marketplace.json`.
- [ ] Tag `v0.3.0` creado + push `origin/main` + push tag.
- [ ] README + SKILL.md actualizados con cost-optimization seccion.
- [ ] Memory `project_v030_shipped.md` written + MEMORY.md index
      updated.

---

## 9. Referencias

- Spec base v1.0.0 raw input: `sbtdd/spec-behavior-base.md` (este
  ciclo cubre subset D+E del LOCKED v1.0.0 backlog).
- Contrato autoritativo v0.1+v0.2 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- Brainstorming session decisions log:
  - (b) Split: v0.3.0 = D+E, v1.0.0 = F+G+H.
  - (a) Lightweight TDD-Guard + subagents + final review pattern.
  - (2) Balanced trim (defer D5, E2).
  - Final review = MAGI -> /receiving-code-review loop, exit on
    GO_WITH_CAVEATS clean, cap 5 iter (user directive 2026-04-25).
- v1.0.0 LOCKED memory files (deferred items):
  - `project_v100_progress_streaming.md` (D5 deferred portion).
  - `project_v100_per_skill_model_flag.md` (E2 deferred portion).
  - `project_v100_magi_dispatch_hardening.md` (F).
  - `project_v100_magi_cross_check.md` (G).
- Historical precedent:
  - v0.2.1 lightweight pattern (commits 9622a55..cfb39ee, ~3h wall
    time, 4 LOCKED items).
  - v0.2.0 INV-0 override (commit 5d7bfc4, MAGI 4-iter overrun).
  - v0.2.2 docs hotfix (commit 337aba2).
- Branch: trabajo en `main` directamente (lightweight pattern, no
  feature branch necesario per scope reducido). Si MAGI Loop 2 spawnea
  scope-creep mid-loop, considerar branch v0_3_0 retroactivo.
