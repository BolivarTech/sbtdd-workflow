# Especificacion base — sbtdd-workflow v0.2.0

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v0.2). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado 2026-04-23. Source of truth autoritativo para v0.1 frozen
> se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md` (mega-contrato
> de 2860 lineas); este documento NO lo reemplaza — solo agrega el delta
> v0.2 a implementar sobre v0.1.
>
> Archivo cumple INV-27: no contiene los tres marcadores uppercase
> enumerados en esa invariante (ver `sbtdd/sbtdd-workflow-plugin-spec-base.md`
> sec.S.10 para la lista completa).

---

## 1. Objetivo

Entregar **v0.2.0** del plugin `sbtdd-workflow` incorporando tres release blockers locked, derivados de gaps observables durante el desarrollo de v0.1 (Milestones A-E). El alcance v0.2 es deliberadamente minimal y enfocado; todo lo demas (operational items + siete opciones complementarias de spec-drift detection) se difiere a v0.3.

Criterio de exito: el plugin sigue siendo instalable desde `BolivarTech/sbtdd-workflow` (marketplace sin collision, verified v0.1.0 hotfix), todos los tests de v0.1 (597) siguen pasando sin regresion, y los tres blockers nuevos suman cobertura de tests apropiada + acceptance criteria sec.S.12 extendidos para v0.2.

---

## 2. Alcance v0.2 — tres release blockers LOCKED

### 2.1 Feature A — Interactive MAGI escalation prompt

**Problema v0.1**: cuando safety valve INV-11 se agota (3 iteraciones MAGI sin clearing el umbral), el plugin escribe artefactos (`.claude/magi-conditions.md`, `.claude/magi-feedback.md`, iter-report.json), emite resumen stderr, y hace exit 8. El usuario tiene que leer archivos y re-invocar manualmente. Durante desarrollo de Milestones A-E, el orquestador-asistente en chat presentaba un prompt de 4 opciones (a/b/c/d) al usuario; esa interaccion era puramente del assistant, NO del plugin.

**Directiva usuario 2026-04-21**: "quiero que se incorpore esa funcion de preguntar al usuario que hacer en ese caso de la misma forma que tu lo hiciste".

**Entrega v0.2**:

- Modulo nuevo `skills/sbtdd/scripts/escalation_prompt.py` con cuatro funciones publicas:
  - `build_escalation_context(iterations, plan_path, context)` — recolecta historia de iteraciones, per-agent verdicts, findings clasificados por severidad, root-cause inference.
  - `format_escalation_message(ctx)` — renderiza el template canonical (documentado verbatim en `CLAUDE.md` seccion "v0.2 requirement (LOCKED) — interactive escalation prompt on MAGI exhaustion").
  - `prompt_user(ctx, options)` — emite mensaje + `input()` TTY-guarded + valida choice + retorna `UserDecision` estructurada.
  - `apply_decision(decision)` — ejecuta la accion elegida (override, retry, abandon, alternative) + escribe audit artifact.
- Clasificador de root-cause: infra-transient (mismo agente fallo N iters) / plan-vs-spec gap (CRITICAL findings persisten) / structural defect (STRONG_NO_GO de ≥1 agente) / spec ambiguity (confidence decreciente).
- Opciones dinamicas: siempre disponibles `(a) override via INV-0 + --reason`, `(d) v0.1 exit-8 behavior`; condicionales `(b) retry iter`, `(c) replan/split`.
- CLI flag `--override-checkpoint --reason "<text>"` en `finalize_cmd`, `spec_cmd`, `pre_merge_cmd`. `--reason` obligatorio.
- Audit artifact `.claude/magi-escalations/<timestamp>-<plan_id>.json` con `decision`, `chosen_option`, `reason`, `escalation_context`, `timestamp`, `plan_id`, `magi_context`.
- Headless fallback: cuando `sys.stdin.isatty()` es False OR `--non-interactive` flag OR invocado dentro de `auto_cmd`, aplica policy de `.claude/magi-auto-policy.json` (`{on_exhausted: "abort" | "override_strong_go_only" | "retry_once"}`, default `abort`).
- `resume_cmd` detecta `.claude/magi-escalation-pending.md` y continua el prompt si el usuario hizo Ctrl+C.
- Golden-output unit tests per root-cause class x context (checkpoint2/pre-merge/auto). Fixtures bajo `tests/fixtures/magi-escalations/`.

**Invariantes de diseño obligatorios**:

- Nunca corre dentro de `auto_cmd` (INV-22 sequential + headless).
- Cada override produce audit artifact. Ningun override silencioso.
- Non-TTY safe: EOFError wrap en `input()`. Nunca cuelga.
- Backward-compatible: si usuario no hace eleccion, default = comportamiento v0.1 (exit 8 + artefactos).
- `--reason` obligatorio en override — fuerza al desarrollador a articular por que esta overrideando verdict negativo.
- Idioma: Spanish + English mix matching precedente de sesiones observadas (Plans A-E).
- Template emite <= 40 lineas.

**Precedente historico**: Milestone D Checkpoint 2 iter 3 DEGRADED → orquestador presento opciones a/b/c/d → usuario respondio `a` → override documentado en commit `5d7bfc4`. v0.2 automatiza esta interaccion.

### 2.2 Feature B — Superpowers spec-reviewer integration per task

**Problema v0.1**: el plugin verifica alineacion codigo-vs-spec solo en dos gates (Checkpoint 2 MAGI pre-codigo + pre-merge Loop 2 MAGI post-codigo) + disciplina TDD durante ejecucion (agente re-lee spec per task, tests nombrados por escenarios BDD). No hay check mecanico per-commit que el diff actual siga satisfaciendo cada escenario en `sbtdd/spec-behavior.md`. Los gaps se descubren solo en pre-merge. Ejemplo de Milestone A: caspar detecto que `detect_drift` omitia Scenario 4 (state=green + HEAD=refactor:) al final del milestone, no durante Task 14/15 close.

**Directiva usuario 2026-04-23**: "para v0.2 solo 8, los demas para 0.3". La opcion 8 es integrar `superpowers:subagent-driven-development/spec-reviewer-prompt.md` como primary per-task drift detector — skill que ya existe en el ecosistema superpowers y captura tres defect classes: missing requirements, extra/unneeded work (over-engineering), misunderstandings. Directiva interna del prompt: "verify by reading code, NOT by trusting report".

**Entrega v0.2**:

- Modulo nuevo `skills/sbtdd/scripts/spec_review_dispatch.py` con API publica:
  - `dispatch_spec_reviewer(task_id, plan_path, repo_root)` -> `SpecReviewResult`.
  - `SpecReviewResult = @dataclass(frozen=True)` con `approved: bool`, `issues: tuple[SpecIssue, ...]`, `reviewer_iter: int`, `artifact_path: Path`.
  - Invoca subagent superpowers via subprocess `claude -p /subagent-driven-development/spec-reviewer-prompt.md`, pasa task text + diff de ultimos commits del task.
- Integracion en `auto_cmd._phase2_task_loop`: despues de que implementer subagent reporta DONE, antes de `close_task_cmd.mark_and_advance`, despachar spec-reviewer. Si retorna `issues`, rutear via `/receiving-code-review` (extension de INV-29 gate), mini-cycle TDD fix per accepted finding, re-dispatch, safety valve 3 iter.
- `close_task_cmd` gana flag `--skip-spec-review` como escape valve para flows manuales donde usuario ya verifico compliance. Default = invocar reviewer.
- Nuevo subcomando `/sbtdd review-spec-compliance <task-id>` para flows `executing-plans` + manual. Lee task del plan, recolecta diff, despacha reviewer. Exit 0 en approved, exit 12 (propuesto) en issues.
- Nueva excepcion `SpecReviewError(SBTDDError)` en `errors.py`, exit code 12 — extiende sec.S.11.1 taxonomy. Document en CHANGELOG BREAKING si codigo nuevo, o mapea a ValidationError (exit 1) si el blocker preferiria no expandir taxonomy.
- Audit artifact `.claude/spec-reviews/<task-id>-<timestamp>.json` con reviewer output completo + accepted/rejected findings breakdown (similar al patron MAGI verdict artifact).
- Integracion con `quota_detector`: si `quota_detector.detect(stderr)` fire durante reviewer dispatch, lanza `QuotaExhaustedError` (exit 11) + persiste estado para resume — mismo patron que MAGI dispatcher.
- `StubSpecReviewer` en `tests/fixtures/skill_stubs.py` con knobs `approved: bool` + `issues: list[str]`, mirroring `StubMAGI` patron.
- Propuesta de extension al invariant set: **INV-31** — "Every task close in `auto_cmd` and `close_task_cmd` (interactive) MUST pass spec-reviewer approval before `mark_and_advance` advances state, unless `--skip-spec-review` flag set (manual workflows) or stub fixture injected (tests)." Documentar en spec-base sec.S.10 + CLAUDE.md invariants summary.

**Invariantes de diseño obligatorios**:

- Reviewer opera sobre task diff + task text (NO full spec) — mantiene cost bounded, prompt size ~1-5 KB por call.
- Issues rutean via `/receiving-code-review` — extiende INV-29 gate a spec-review findings (no solo MAGI findings).
- Non-TTY safe: es `claude -p` subprocess call, funciona headless (`auto_cmd`); no requiere interaccion de usuario a nivel reviewer.
- Audit artifact per invocation: cada reviewer run escribe a `.claude/spec-reviews/` para post-mortem + provenance.
- Safety valve per task: max 3 reviewer iters; exhaustion lanza `SpecReviewError` y bloquea `mark_and_advance` con error claro.
- Quota-aware: quota_detector integrado.
- Backward-compat: `--skip-spec-review` + stub injection paths mantienen ejecucion estilo Milestones A-E posible; default cambia a invocar.

**Mitigacion de costo**: para un plan de 36 tasks (Milestone A size) eso suma 36 `claude -p` calls extra. El reviewer opera sobre task diff + task text (~1-5 KB), no full spec, manteniendo envelope aceptable. Observabilidad: audit artifacts permiten medir cost real vs beneficio post-v0.2 field usage.

### 2.3 Feature C — MAGI version-agnostic parity tests

**Problema v0.1**: `tests/test_distribution_coherence.py` hardcodea path a MAGI cache en version `2.1.3`:

```python
Path.home() / ".claude" / "plugins" / "cache" / "bolivartech-plugins" / "magi" / "2.1.3"
```

MAGI shipeo v2.1.4 el 2026-04-23 (patch bump, zero schema change verified: solo cambia `"version"` string en `plugin.json`; `marketplace.json` byte-identical).

**Directiva usuario 2026-04-23**: "actualiza MAGI de una vez en v0.2". Resolucion: en lugar de bumpear hardcoded pin de `2.1.3` a `2.1.4` (repitiendo esto para cada patch futuro), v0.2 hace el pin version-agnostic, resolviendo la version mas alta cacheada.

**Entrega v0.2**:

- Rewrite `_resolve_magi_plugin_json()` en `tests/test_distribution_coherence.py`:
  - Enumera subdirs bajo `~/.claude/plugins/cache/bolivartech-plugins/magi/`.
  - Ordena por semver key `(major, minor, patch)` tupla, picks max.
  - Retorna path al `plugin.json` de la version mas alta.
  - Graceful fallback: si `cache_base` no existe o dir vacio, retorna non-existent path (triggers existing `@pytest.mark.skipif` gate).
- Helper `_semver_key(v: str) -> tuple[int, ...]`: convierte `"2.1.4"` a `(2, 1, 4)`; segmentos no-numericos ordenan last (`-1`).
- Env var `MAGI_PLUGIN_ROOT` preservado como override para CI o ambientes sin cache — unchanged de v0.1.
- Nuevo test `test_semver_key_handles_mixed_version_strings` validando tie-break + non-numeric segment handling.
- Tests parity existentes (required-keys subset + `repository` field-form) continuan sin cambios — ya usan subset checks (Plan E iter-2 fix) asi que toleran MAGI agregando optional fields en el futuro.
- Opcional: emite stderr warning si multiple versions MAGI cacheadas simultaneamente (detecta dev machines con cache stale); no fallar — Claude Code cache cleanup esta out-of-scope.

**Invariantes de diseño obligatorios**:

- Auto-resolver skip grazefully cuando `cache_base` no existe (CI sin MAGI instalado).
- Semver ordering solo — no alpha/beta suffix handling en v0.2 (MAGI usa `major.minor.patch` limpio). Documentar supuesto en CHANGELOG.
- No runtime mutation de MAGI cache — resolver es read-only reflection sobre filesystem state.
- Backward compat: `MAGI_PLUGIN_ROOT` env var override preservado exactly, CI pipelines unaffected.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-30 del contrato `sbtdd/sbtdd-workflow-plugin-spec-base.md` sec.S.10 aplican. Critical durante implementacion v0.2:

- **INV-0 (autoridad maxima)**: `~/.claude/CLAUDE.md` siempre prevalece. Feature A override commands respetan esto — INV-0 es el rationale del escape valve.
- **INV-2 (no-mezcla fases)**: los mini-cycles de Feature B spec-reviewer mantienen atomicidad per-commit.
- **INV-11 (safety valves)**: Feature B reviewer loop respeta 3-iter cap. Feature A se dispara cuando safety valve se agota, no lo extiende.
- **INV-22 (sequential only)**: Feature A nunca corre dentro de `auto_cmd`.
- **INV-23 (TDD-Guard inviolable)**: Feature B reviewer no toggea TDD-Guard.
- **INV-26 (audit trail)**: Features A + B ambas producen audit artifacts en `.claude/`.
- **INV-27 (spec-base no placeholders)**: este documento cumple. v0.2 scope no introduce nuevos placeholders.
- **INV-28 (MAGI degraded)**: Feature A dispara en degraded verdicts per INV-28.
- **INV-29 (/receiving-code-review gate)**: Feature B extiende INV-29 a spec-review findings, no solo MAGI.
- **INV-30 (resumibilidad)**: Feature A resume_cmd integration cubre Ctrl+C mid-prompt.

Nuevo invariante propuesto:

- **INV-31 (spec-reviewer gate)**: cada task close en `auto_cmd` y `close_task_cmd` (interactive) DEBE pasar spec-reviewer approval antes de `mark_and_advance` advance state, excepto cuando `--skip-spec-review` flag set o stub fixture injected.

### Stack y runtime

Sin cambios vs v0.1:

- Python 3.9+ estricto, `mypy --strict` sin warnings, cross-platform (Windows/Linux/macOS), stdlib-only en hot paths.
- Dependencias externas obligatorias identicas (git, tdd-guard, superpowers plugin, magi plugin, claude CLI).
- Dependencias dev: pytest, pytest-asyncio, ruff, mypy, pyyaml.
- Licencia dual: MIT OR Apache-2.0.

### Arquitectura obligatoria

Preservada de v0.1. v0.2 agrega:

- Un modulo nuevo por Feature A (`escalation_prompt.py`) + por Feature B (`spec_review_dispatch.py`).
- Zero modificacion a modulos frozen de v0.1 excepto:
  - `errors.py`: agregar `SpecReviewError` subclass + entry en `EXIT_CODES` (si se adopta exit 12).
  - `auto_cmd.py`: extender `_phase2_task_loop` con spec-reviewer dispatch.
  - `close_task_cmd.py`: agregar `--skip-spec-review` flag handling.
  - `spec_cmd.py`, `pre_merge_cmd.py`, `finalize_cmd.py`: extender con `--override-checkpoint --reason` CLI flag + integration con escalation_prompt.
  - `resume_cmd.py`: detectar `.claude/magi-escalation-pending.md` + integrar.
  - `run_sbtdd.py`: registrar nueva subcomando `review-spec-compliance`.
  - `tests/fixtures/skill_stubs.py`: agregar `StubSpecReviewer`.
  - `tests/test_distribution_coherence.py`: rewrite `_resolve_magi_plugin_json()` + nuevo test `_semver_key`.

### Exit code taxonomy

Preservada de v0.1 (sec.S.11.1). v0.2 propone extension:

- **Exit 12**: `SPEC_REVIEW_ISSUES` (SpecReviewError). Se adopta solo si SpecReviewError se introduce como nueva exception; alternativa es mapear via ValidationError (exit 1). Decision del planner durante writing-plans.

### Reglas duras no-eludibles (sin `--force` ni override)

Todas las v0.1 se preservan:

- INV-0 autoridad global.
- INV-27 spec-base sin los tres marcadores uppercase que el regex del plugin rechaza (lista en sec.S.10 del contrato autoritativo).
- INV-28 MAGI degraded no-salida.
- INV-29 /receiving-code-review gate.
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).

Nuevo (v0.2):

- INV-31 (propuesto): spec-reviewer gate en task close.

---

## 4. Funcionalidad requerida (SDD)

Requerimientos funcionales v0.2 (F serie continuando desde v0.1 sec.S.12.1):

**F15**. `escalation_prompt.build_escalation_context(iterations, plan_path, context)` acepta lista de `MAGIVerdict`s + path del plan + contexto (literal `"checkpoint2"` | `"pre-merge"` | `"auto"`) y retorna `EscalationContext` inmutable con iter history + per-agent verdicts + severity-classified findings + root-cause inference classification.

**F16**. `escalation_prompt.format_escalation_message(ctx)` renderiza el template canonical documentado en CLAUDE.md seccion "v0.2 requirement (LOCKED) — interactive escalation prompt on MAGI exhaustion", usando datos runtime. Output es string <=40 lineas. Incluye root-cause hint, per-agent verdict lines, severity-classified findings, 4 opciones dinamicas, y prompt question "Cual?".

**F17**. `escalation_prompt.prompt_user(ctx, options)` emite mensaje formatted + `input()` TTY-guarded + valida choice contra `options` (letra de `a` a `d`, case-insensitive) + retorna `UserDecision` estructurada. Si `sys.stdin.isatty()` False o `--non-interactive` flag set, aplica headless policy de `.claude/magi-auto-policy.json` (default `abort`).

**F18**. `escalation_prompt.apply_decision(decision)` ejecuta accion correspondiente: override (extiende flow, marca audit), retry (extiende safety valve +1, marca audit), abandon (exit 8 + artefactos), alternative (path context-specific: replan, split, abandon). En todos los casos escribe audit artifact `.claude/magi-escalations/<timestamp>-<plan_id>.json`.

**F19**. Feature A integra en `spec_cmd`, `pre_merge_cmd`, `resume_cmd` via `_handle_safety_valve_exhaustion(ctx)` helper. `finalize_cmd` gana `--override-checkpoint --reason "<text>"` CLI flag con reason mandatory.

**F20**. `spec_review_dispatch.dispatch_spec_reviewer(task_id, plan_path, repo_root)` despacha subagent superpowers via subprocess `claude -p /subagent-driven-development/spec-reviewer-prompt.md`. Input = task text extraido del plan + diff de ultimos commits del task. Timeout 900s (configurable). Quota-detector integrado. Retorna `SpecReviewResult` (`approved: bool`, `issues: tuple[SpecIssue, ...]`, `reviewer_iter: int`, `artifact_path: Path`).

**F21**. Feature B integra en `auto_cmd._phase2_task_loop` post-implementer / pre-`mark_and_advance`. Si `approved`, continua. Si `issues`, rutea via `/receiving-code-review` (acepta/rechaza findings), mini-cycle TDD fix per accepted, re-dispatch reviewer, safety valve 3 iter. Exhaustion lanza `SpecReviewError` (exit 12 propuesto, o exit 1 via ValidationError mapping).

**F22**. `close_task_cmd` gana flag `--skip-spec-review` (default False). Cuando True, skip reviewer dispatch.

**F23**. Nuevo subcomando `/sbtdd review-spec-compliance <task-id>` para `executing-plans` + manual flows. Implementado en `review_spec_compliance_cmd.py` modulo nuevo O extension de `close_task_cmd.py`. Wired en `run_sbtdd.py` dispatch.

**F24**. `_resolve_magi_plugin_json()` en `tests/test_distribution_coherence.py` enumera MAGI cache versions, ordena por semver, retorna path a latest. `_semver_key(v)` helper tuple order.

**F25**. `MAGI_PLUGIN_ROOT` env var override preservado identico a v0.1.

**F26**. `StubSpecReviewer` en `tests/fixtures/skill_stubs.py` con knobs `approved: bool` + `issues: list[str]` + `iter_count: int`. Mirroring `StubMAGI` patron.

**F27**. Audit artifacts v0.2:
- `.claude/magi-escalations/<timestamp>-<plan_id>.json` (Feature A).
- `.claude/spec-reviews/<task-id>-<timestamp>.json` (Feature B).
- `.claude/magi-auto-policy.json` (optional, usuario configura; default `abort`).
- `.claude/magi-escalation-pending.md` (effimero, para Ctrl+C recovery).

### Requerimientos no-funcionales (NF)

**NF8**. `make verify` continua limpio (pytest + ruff check + ruff format + mypy --strict). Runtime <=60s budget del Milestone D preservado.

**NF9**. Features A + B cruzan plataforma Windows/Linux/macOS. TTY detection via `sys.stdin.isatty()`. EOFError handling en `input()` pattern match con `resume_cmd` existing.

**NF10**. Registros fijos nuevos (si aplica): `AutoPolicy` literal set `{"abort", "override_strong_go_only", "retry_once"}` como `tuple[str, ...]`.

**NF11**. Subprocess calls en `spec_review_dispatch` usan `subprocess_utils.run_with_timeout` per NF5 de v0.1. `shell=False`. Quota-detector integrado.

**NF12**. Nuevos `.py` files con header `# Author: Julian Bolivar / # Version: 1.0.0 / # Date: YYYY-MM-DD` per sec.S.8.1.

---

## 5. Scope exclusions

Explicitamente out-of-scope para v0.2 (ALL deferred a v0.3):

**Operational / infra** (originalmente en v0.2 backlog, movidos por directiva 2026-04-23):

- GitHub Actions CI workflow (habilita tests-passing badge).
- `schema_version` field en `plugin.local.md` (sec.S.13 item 5).
- GoogleTest / Catch2 / bazel / meson adapters para C++ stack (sec.S.13 item 7).
- `marketplace.json` `$schema` URL post-push verification.

**Complementary spec-drift detection options** (siete opciones evaluadas alongside Feature B pero deferred):

- **(1)** `scenario_coverage_check.py` mechanical regex pre-filter.
- **(2)** Spec-snapshot diff check (proposed LOCKED para v0.3 regardless).
- **(3)** Inverted traceability matrix (`Scenario coverage:` line per task).
- **(4)** Per-phase MAGI-lite (3-perspective analysis).
- **(5)** Auto-generated scenario stubs desde `/writing-plans` (strong candidate LOCK para v0.3).
- **(6)** Watermark comments + lint rule.
- **(7)** Bespoke LLM drift detector.

Full rationale + decision matrix en local `CLAUDE.md` seccion "v0.3 backlog — complementary spec-drift detection options".

---

## 6. Criterios de aceptacion finales

v0.2.0 se considera shipeable cuando los siguientes items sec.S.12 se cumplen:

### 6.1 Functional (Feature A — escalation prompt)

- **A1**. `escalation_prompt.py` modulo presente con 4 funciones publicas documentadas (`build_escalation_context`, `format_escalation_message`, `prompt_user`, `apply_decision`).
- **A2**. Template canonical render byte-for-byte matching el ejemplo verbatim de CLAUDE.md (Plan D Checkpoint 2 iter 3 escalation).
- **A3**. 4 opciones context-aware (a/b/c/d) composed dinamicamente del root-cause classification.
- **A4**. `--override-checkpoint --reason "<text>"` CLI flag implementado en `finalize_cmd`, `spec_cmd`, `pre_merge_cmd`. Reason mandatory.
- **A5**. Audit artifact `.claude/magi-escalations/<timestamp>-<plan_id>.json` emitido en cada override o headless fallback.
- **A6**. `resume_cmd` detecta `.claude/magi-escalation-pending.md` y continua prompt.
- **A7**. Non-TTY / CI contextos usan `.claude/magi-auto-policy.json` o default `abort`; nunca cuelgan.
- **A8**. Feature A nunca ejecuta dentro de `auto_cmd` (verified by test).
- **A9**. Golden-output unit tests per root-cause class x context pasan.

### 6.2 Functional (Feature B — spec-reviewer integration)

- **B1**. `spec_review_dispatch.py` modulo presente con `dispatch_spec_reviewer` + `SpecReviewResult` dataclass.
- **B2**. Integracion con `auto_cmd._phase2_task_loop`: reviewer despachado post-implementer, pre-`mark_and_advance`.
- **B3**. `close_task_cmd --skip-spec-review` flag funcional.
- **B4**. Subcomando `/sbtdd review-spec-compliance <task-id>` dispatched correctamente por `run_sbtdd.py`.
- **B5**. Audit artifact `.claude/spec-reviews/<task-id>-<timestamp>.json` emitido en cada reviewer run.
- **B6**. Issues rutean via `/receiving-code-review` (extension INV-29).
- **B7**. Safety valve 3 iter; exhaustion lanza `SpecReviewError` (o mapped exit code).
- **B8**. Quota-detector integrado (exit 11 en quota).
- **B9**. `StubSpecReviewer` en `skill_stubs.py`.
- **B10**. INV-31 documentado (si adoptado) en CLAUDE.md + spec-base extension.

### 6.3 Functional (Feature C — MAGI auto-resolver)

- **C1**. `_resolve_magi_plugin_json()` enumera cache versions + picks latest semver.
- **C2**. `_semver_key()` helper con test coverage para mixed version strings.
- **C3**. Env var `MAGI_PLUGIN_ROOT` override preservado.
- **C4**. Skipif graceful cuando cache vacio o no existe.
- **C5**. Tests existentes de parity (required-keys subset + `repository` field-form) continuan passing sin cambios.

### 6.4 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format + mypy --strict, todos verdes, runtime <=60s.
- **NF-B**. Tests totales v0.2 >= 597 baseline + nuevos tests (proyeccion 40-80 extras).
- **NF-C**. Cross-platform: TTY detection + subprocess wrapping funciona en Windows + POSIX.
- **NF-D**. Nuevos `.py` files con header Author/Version/Date.
- **NF-E**. Zero modificacion a modulos frozen de v0.1 excepto los enumerados explicitamente en seccion 3 "Arquitectura obligatoria".

### 6.5 Process

- **P1**. MAGI Checkpoint 2 del plan v0.2 retorna verdict >= `GO_WITH_CAVEATS` full (no degraded) per INV-28. Iter budget 3 + INV-0 override precedent disponible para degraded-only contexts.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict >= `GO_WITH_CAVEATS` full.
- **P3**. CHANGELOG.md Unreleased section updated con entries Added/Changed/BREAKING per Features A/B/C.
- **P4**. Version bump: `plugin.json` + `marketplace.json` 0.1.0 -> 0.2.0, synced.
- **P5**. Tag `v0.2.0` creado + pushed (user-driven, per INV-0 commit authorization rules).

### 6.6 Distribution (sec.S.12.5 extended)

- **D1**. Plugin instalable via `/plugin marketplace add BolivarTech/sbtdd-workflow` + `/plugin install sbtdd-workflow@bolivartech-sbtdd` (marketplace rename de v0.1.0 hotfix preservado).
- **D2**. Tests de cross-artifact coherence (SKILL.md + README + CHANGELOG + manifests) actualizados para version 0.2.0.
- **D3**. Nuevos subcomandos y flags documentados en README.md + SKILL.md + CLAUDE.md.

---

## 7. Dependencias externas nuevas

Ninguna. v0.2 usa todas las dependencias existentes de v0.1:

- `superpowers:subagent-driven-development` (ya presente, Feature B lo consume).
- `magi` plugin (ya presente, Feature A reacciona a su output).
- `claude` CLI (ya presente, Feature B lo usa via subprocess).

Zero nuevas dependencias Python runtime. Zero nuevas dev deps.

---

## 8. Risk register v0.2

- **R1**. Feature B cost overhead: 36 extra `claude -p` calls per Milestone-A-sized plan. Mitigacion: audit artifacts permiten medir cost real post-v0.2; si excede envelope, considerar Group A opcion (1) `scenario_coverage_check.py` en v0.3 como pre-filter para reducir invocaciones.
- **R2**. Feature A template rendering cross-platform: golden-output tests en Windows line-endings vs POSIX. Mitigacion: normalize line endings en comparaciones de test.
- **R3**. Feature C assumes clean semver en MAGI version strings. Si MAGI introduce alpha/beta suffix futuro, `_semver_key` ordena non-numeric last — documentar supuesto en comment + CHANGELOG.
- **R4**. INV-31 adoption: si el planner decide NO extender invariant set, Feature B default-invocation deja de estar enforzado. Mitigacion: documentar explicitamente durante Checkpoint 2 si INV-31 adoptado o deferido, update CLAUDE.md seccion accordingly.
- **R5**. Resume integration con escalation pending: edge case si usuario interrumpe durante `input()` en el prompt + cache del state el Ctrl+C. Mitigacion: `.claude/magi-escalation-pending.md` marker file creado antes del input; `resume_cmd` detecta y restaura.

---

## 9. Referencias

- Contrato autoritativo v0.1: `sbtdd/sbtdd-workflow-plugin-spec-base.md` (2860 lineas).
- BDD overlay v0.1: `sbtdd/spec-behavior.md` (468 lineas, frozen post-v0.1.0 ship).
- v0.2 LOCKED specs detalladas: `CLAUDE.md` secciones:
  - "v0.2 requirement (LOCKED) — interactive escalation prompt on MAGI exhaustion"
  - "v0.2 requirement (LOCKED) — superpowers spec-reviewer integration per task"
  - "v0.2 requirement (LOCKED) — MAGI version-agnostic parity tests"
- v0.3 backlog: `CLAUDE.md` seccion "v0.3 backlog — complementary spec-drift detection options" + `CHANGELOG.md` Deferred v0.3 section.
- Historical precedent: commit `5d7bfc4` (Milestone D iter 3 override), commit `14ac8e5` (README CLAUDE.md reference fix).
- Hotfix v0.1.0 post-ship: marketplace rename `bolivartech-plugins` -> `bolivartech-sbtdd` (commit `dee81aa`).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (scan: 0 matches uppercase). Listo como input para `/brainstorming` — proxima ejecucion `/sbtdd spec` desde este repo arranca el ciclo SBTDD v0.2:

1. `/brainstorming sbtdd/spec-behavior-base.md` -> genera `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then per feature).
2. `/writing-plans sbtdd/spec-behavior.md` -> genera `planning/claude-plan-tdd-org.md` (plan TDD por fases).
3. Checkpoint 2 MAGI review del plan contra spec; safety valve INV-11 3 iter.
4. Plan aprobado -> ejecucion via `/subagent-driven-development` (o `/sbtdd auto` cuando Feature B pueda auto-despachar spec-reviewer, lo cual es la entrega misma del v0.2).
5. Pre-merge Loop 1 + Loop 2 MAGI.
6. Tag v0.2.0 + push a GitHub (user-driven, per INV-0 commit rules).
