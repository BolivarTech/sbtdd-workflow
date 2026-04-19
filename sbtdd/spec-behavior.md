# Especificacion de comportamiento — feature: sbtdd-workflow plugin (mega-feature v0.1)

> Navegador + BDD overlay sobre `sbtdd/sbtdd-workflow-plugin-spec-base.md`
> (el contrato funcional autoritativo, 2860 lineas). Este documento NO
> duplica el contrato — agrega la dimension BDD (Given/When/Then
> testables) y sirve de input para `/writing-plans` (output:
> `planning/claude-plan-tdd-org.md`).
>
> **Generado por `/brainstorming` usando
> `@sbtdd/sbtdd-workflow-plugin-spec-base.md` como input.** Fecha:
> 2026-04-19. Approach elegido: navegador + BDD overlay (no standalone,
> no destilacion condensada) con 19 escenarios ordenados por dependency
> graph (foundation → state → config → subprocess → commits → subcomandos).
>
> Source of truth permanece en el contrato. Cambios al contrato NO
> requieren re-sync de este documento salvo que invaliden escenarios
> existentes.

---

## 1. Objetivo

Implementar `sbtdd-workflow` como plugin Claude Code distribuible via
marketplace BolivarTech — un orquestador que materializa la metodologia
SBTDD (Spec + Behavior + Test Driven Development combinada con el
ecosistema Superpowers multi-agente) mediante un skill unico (`sbtdd`)
que dispatcha 9 subcomandos implementados como modulos Python bajo
`skills/sbtdd/scripts/`. El plugin sigue el patron arquitectonico de
MAGI v2.1.3 (SKILL.md + run_sbtdd.py + scripts/) y depende runtime de
los plugins `superpowers` y `magi` + binarios externos `git` y
`tdd-guard`. Acceptance: **todos los criterios de sec.S.12 del
contrato** — funcionales (sec.S.12.1), paridad con MAGI (sec.S.12.2),
no-funcionales (sec.S.12.3), test coverage (sec.S.12.4), distribucion
publica en marketplace (sec.S.12.5).

---

## 2. Requerimientos SDD

### Requerimientos funcionales (F)

F1. El plugin expone un skill `sbtdd` que dispatcha 9 subcomandos via
    `python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <sub>`.
    Ref: contrato sec.S.2.3, sec.S.6.
F2. `/sbtdd init` bootstrappea el proyecto destino: valida 7 dependencias
    obligatorias (sec.S.1.3), genera CLAUDE.local.md +
    .claude/settings.json + .claude/plugin.local.md + esqueleto
    sbtdd/spec-behavior-base.md + planning/ + appends al .gitignore.
    Ref: sec.S.5.1.
F3. `/sbtdd spec` orquesta el Flujo de especificacion: /brainstorming →
    /writing-plans → Checkpoint 2 MAGI con safety valve 3 iter. Crea
    .claude/session-state.json al aprobar el plan. Ref: sec.S.5.2 +
    INV-27, INV-28.
F4. `/sbtdd close-phase` ejecuta cierre atomico de fase TDD en 4 pasos:
    drift check → verificacion → commit atomico con prefijo sec.M.5 →
    update state file. En Refactor invoca close-task. Ref: sec.S.5.3
    + INV-1, INV-2.
F5. `/sbtdd close-task` marca [x] en el plan + commit `chore:` + avanza
    state file al proximo [ ] o a `"done"`. Ref: sec.S.5.4.
F6. `/sbtdd status` reporta state + git + plan + drift detection.
    Read-only, emite exit 3 en drift. Ref: sec.S.5.5.
F7. `/sbtdd pre-merge` ejecuta Loop 1 (/requesting-code-review hasta
    clean-to-go, safety valve 10 iter) + Loop 2 (/magi:magi con INV-28
    degraded check + INV-29 /receiving-code-review gate + feedback
    loop). Ref: sec.S.5.6 + INV-28, INV-29.
F8. `/sbtdd finalize` valida checklist sec.M.7 (gate MAGI full
    no-degraded) e invoca /finishing-a-development-branch. Ref:
    sec.S.5.7.
F9. `/sbtdd auto` shoot-and-forget: encadena task loop + pre-merge +
    checklist sec.M.7. Budget MAGI elevado (auto_magi_max_iterations=5).
    Termina con git limpio sin invocar /finishing-a-development-branch.
    Ref: sec.S.5.8 + INV-22..26.
F10. `/sbtdd resume` wrapper de recuperacion tras interrupcion. Lee
     state + git + runtime artifacts, diagnostica, delega. Maneja
     uncommitted work con default CONTINUE + flag
     `--discard-uncommitted`. Ref: sec.S.5.10 + INV-30.
F11. Detector de cuota Anthropic (`quota_detector.py`) mapea patrones
     regex (rate limit, session/weekly/Opus limit, credit exhausted,
     server throttle) a exit 11 (QUOTA_EXHAUSTED). Ref: sec.S.11.4.
F12. Reporters TDD-Guard por stack: `rust_reporter.py`,
     `ctest_reporter.py`, `conftest.py.template`. Ref: sec.S.4.2,
     sec.S.5.1.3.
F13. Distribucion via marketplace BolivarTech: manifests
     `.claude-plugin/plugin.json` + `marketplace.json` con `version`
     sincronizada (bumps MAJOR/MINOR/PATCH coinciden), repo GitHub
     publico `github.com/BolivarTech/sbtdd-workflow`, dual license files
     (`LICENSE` MIT + `LICENSE-APACHE`). Ref: sec.S.3, sec.S.12.2,
     sec.S.12.5.
F14. README.md profesional (paridad con README de MAGI v2.1.3):
     - Shields/badges: Python 3.9+, license dual, tests status, ruff/mypy.
     - Descripcion con seccion "Why SBTDD? Why multi-agent?" (analogo
       al "Why Three Adversarial Perspectives?" de MAGI).
     - Installation: marketplace (`/plugin marketplace add`) + local
       dev (`claude --plugin-dir` + symlink `.claude/skills/`).
     - Usage: tabla de 9 subcomandos con comandos de ejemplo + flujo
       tipico end-to-end (init → spec → auto → finalize).
     - Architecture: referencia al diagrama de sec.S.2.3 del contrato.
     - Test coverage + CI: badge + instrucciones `make verify`.
     - Contributing + License dual (MIT OR Apache-2.0).
     Ref: sec.S.12.2, espejando el README de MAGI.

### Requerimientos no-funcionales (NF)

NF1. Python >= 3.9, cross-platform Windows/Linux/macOS, stdlib-only en
     hot paths (close-phase, close-task, status). Ref: INV-19..21.
NF2. `make verify` limpio: pytest + ruff check + ruff format --check +
     mypy --strict. Line length 100.
NF3. Todos los `.py` con header `# Author: Julian Bolivar / # Version:
     1.0.0 / # Date: YYYY-MM-DD` (sec.S.8.1).
NF4. Registros fijos como `MappingProxyType` o `tuple` — no mutables
     (sec.S.8.5).
NF5. `subprocess.run` con `shell=False`, timeouts explicitos, Windows
     kill-tree con `taskkill /F /T /PID` antes de `proc.kill()`
     (sec.S.8.6).
NF6. >= 1 test file por modulo bajo `scripts/`; fixtures en
     `tests/fixtures/` (sec.S.12.4).
NF7. Dual license MIT OR Apache-2.0 (sec.S.3.1).

---

## 3. Restricciones y constraints duros

Todas las invariantes INV-0 a INV-30 del contrato sec.S.10 aplican. Las
mas criticas durante la implementacion:

- **INV-0 (autoridad maxima):** `~/.claude/CLAUDE.md` siempre prevalece
  sobre este spec, el contrato, CLAUDE.local.md, y plugin.local.md.
  Ningun override posible.
- **INV-2 (no-mezcla de fases):** ningun commit mezcla cambios de
  distintas fases TDD. Atomico estricto.
- **INV-5..7 (commits):** prefijos de sec.M.5 obligatorios, mensajes
  en ingles, sin Co-Authored-By, sin referencias a Claude/IA. Aplicado
  por `commits.py`.
- **INV-11 (safety valves):** 3 caps duros — `magi_max_iterations`
  (3), `auto_magi_max_iterations` (5), 10 (hardcoded Loop 1). Ningun
  loop itera indefinidamente.
- **INV-27 (spec-base limpia):** `spec-behavior-base.md` rechaza
  `TODO`, `TODOS`, `TBD` uppercase. Regla dura sin `--force`.
- **INV-28 (MAGI degraded):** veredicto degraded NO cuenta como salida
  de loop (excepto STRONG_NO_GO). Aplica a los 3 loops MAGI (spec
  Checkpoint 2, pre-merge Loop 2, auto Fase 3b).
- **INV-29 (/receiving-code-review gate):** toda finding de MAGI que
  implique cambio de codigo pasa por evaluacion tecnica antes de
  aplicarse. Rechazos se feedbackean a la proxima iteracion MAGI.
- **INV-30 (resumibilidad):** toda corrida interrumpida reanudable via
  `/sbtdd resume`. Peor caso = se pierde uncommitted del current_phase.

### Stack y runtime

- **Python 3.9+** estricto. `mypy --strict` sin warnings. Cross-platform
  (Windows / Linux / macOS). stdlib-only en hot paths.
- **Dependencias externas obligatorias:** `git`, `tdd-guard` (binario
  npm global), plugins CC `superpowers` + `magi`.
- **Dependencias dev:** pytest, pytest-asyncio, ruff, mypy.
- **Licencia dual:** MIT OR Apache-2.0 (archivos `LICENSE` +
  `LICENSE-APACHE`).

### Arquitectura obligatoria (paridad MAGI v2.1.3)

- Un skill (`sbtdd`) con SKILL.md + `run_sbtdd.py` como entrypoint
  unico.
- Layout `.claude-plugin/` + `skills/sbtdd/scripts/` + `templates/`
  + `tests/fixtures/`.
- `pyproject.toml` (mypy strict, ruff line-length 100,
  `explicit_package_bases`).
- `Makefile` con targets `test / lint / format / typecheck / verify`.
- `conftest.py` con integracion tdd-guard (escribe
  `.claude/tdd-guard/data/test.json`).

### Exit code taxonomy (sec.S.11.1)

0 (SUCCESS) / 1 (USER_ERROR) / 2 (PRECONDITION_FAILED) /
3 (DRIFT_DETECTED) / 4 (FILE_CONFLICT) / 5 (SMOKE_TEST_FAILED) /
6 (VERIFICATION_IRREMEDIABLE) / 7 (LOOP1_DIVERGENT) /
8 (MAGI_GATE_BLOCKED) / 9 (CHECKLIST_FAILED) / 11 (QUOTA_EXHAUSTED) /
130 (INTERRUPTED). Cada uno con excepcion Python mapeada (sec.S.11.1
tabla de mapeo).

### Reglas duras no-eludibles (sin `--force` ni override)

- INV-0 (autoridad global)
- INV-27 (spec-base sin TODO/TODOS/TBD uppercase)
- INV-28 (MAGI degraded no-salida)
- INV-29 (/receiving-code-review gate)
- Commits en ingles + sin Co-Authored-By + sin IA refs
- No force push a ramas compartidas (INV-13)
- No commitear archivos con patrones de secretos (INV-14)

---

## 4. Escenarios BDD (19 scenarios ordenados por dependency graph)

### 4.1 Foundation layer

**Escenario 1: `models.py` — registros inmutables**

> **Given:** `scripts/models.py` define `COMMIT_PREFIX_MAP`,
> `VERDICT_RANK`, `VALID_SUBCOMMANDS` como `MappingProxyType` / `tuple`
> (sec.S.8.5).
> **When:** test intenta mutar uno (ej. `COMMIT_PREFIX_MAP["new"] = "..."`).
> **Then:** Python lanza `TypeError`; registro mantiene contenido
> original.
> *Ref: sec.S.2.1, sec.S.8.5.*

**Escenario 2: `errors.py` — jerarquia tipada**

> **Given:** `scripts/errors.py` define `SBTDDError` base + 7 subclases
> (`ValidationError`, `StateFileError`, `DriftError`, `DependencyError`,
> `PreconditionError`, `MAGIGateError`, `QuotaExhaustedError`).
> **When:** codigo lanza una subclase (ej. `raise DriftError("phase mismatch")`).
> **Then:** catch contra `SBTDDError` la captura; catch contra subclase
> distinta NO la captura; mapeo a exit code correcto por sec.S.11.1.
> *Ref: sec.S.8.4, sec.S.11.1.*

### 4.2 State & drift

**Escenario 3: `state_file.py` — schema validation**

> **Given:** `.claude/session-state.json` con JSON schema-invalido (p.ej.
> `current_phase="yellow"` no esta en enum, o `plan_approved_at` mal
> formateado).
> **When:** `state_file.load()` lo lee.
> **Then:** lanza `StateFileError` con mensaje indicando el campo
> ofensor; NO retorna estado corrupto silenciosamente.
> *Ref: sec.S.9.1 schema, sec.S.8.4.*

**Escenario 4: `drift.py` — deteccion state-vs-git-vs-plan**

> **Given:** state file `current_phase="green"` + ultimo commit prefijo
> `refactor:` (regla operativa sec.S.9.2 declara drift).
> **When:** `detect_drift(state_file_path, plan_path, repo_root)` se invoca.
> **Then:** retorna `DriftReport` con los 3 valores enfrentados
> (`state.current_phase="green"`, `git.last_prefix="refactor:"`,
> `plan.task_state="[ ]"`); NO retorna `None`.
> *Ref: sec.S.9.2, sec.S.11.1 exit 3.*

### 4.3 Config & templates

**Escenario 5: `config.py` — parsing de `plugin.local.md`**

> **Given:** `.claude/plugin.local.md` con YAML frontmatter valido
> (stack, verification_commands, magi_threshold, etc.).
> **When:** `config.load_plugin_local(path)` se invoca.
> **Then:** retorna `PluginConfig` (`@dataclass(frozen=True)`) con tipos
> estrictos (`Literal["rust","python","cpp"]`, `tuple[str,...]`, `int`);
> valores coinciden con frontmatter.
> *Ref: sec.S.4.2, sec.S.4.3.*

**Escenario 6: `templates.py` — expansion de placeholders**

> **Given:** template string con `{Author}`, `{ErrorType}`, `{stack}`;
> contexto dict con values.
> **When:** `templates.expand(template_str, context)` se invoca.
> **Then:** retorna string con placeholders sustituidos; placeholders no
> resueltos (`{UnknownKey}`) quedan literales (no silent error, no
> `KeyError`).
> *Ref: sec.S.2.1 (templates.py).*

**Escenario 7: `hooks_installer.py` — fusion idempotente**

> **Given:** `.claude/settings.json` existente con hook externo
> (PreToolUse "eslint"); template del plugin con PreToolUse "tdd-guard".
> **When:** `hooks_installer.merge(existing, template)` se invoca.
> **Then:** `settings.json` final con AMBOS hooks PreToolUse; segunda
> invocacion con mismos inputs produce archivo byte-identico
> (idempotencia).
> *Ref: sec.S.5.1 Fase 3, sec.S.7.2.*

### 4.4 Subprocess & quota

**Escenario 8: `subprocess_utils.py` — Windows kill-tree order**

> **Given:** subprocess en Windows que excede timeout.
> **When:** `kill_tree(proc)` se invoca.
> **Then:** ejecuta `taskkill /F /T /PID <pid>` **antes** de
> `proc.kill()` (patron MAGI R3-1); en POSIX: SIGTERM + SIGKILL fallback.
> *Ref: sec.S.8.6.*

**Escenario 9: `quota_detector.py` — deteccion de patrones Anthropic**

> **Given:** stderr contiene `"You've hit your session limit · resets 3:45pm"`.
> **When:** `quota_detector.detect(stderr)` se invoca.
> **Then:** retorna `QuotaExhaustion(kind="session_limit", reset_time="3:45pm", recoverable=True)`;
> dispatchers capturan + lanzan `QuotaExhaustedError` → exit 11.
> Negative: stderr sin patron → retorna `None`.
> *Ref: sec.S.11.4, sec.S.8.4.*

### 4.5 Commits

**Escenario 10: `commits.py` — prefijo validado + ingles-only**

> **Given:** intento de commit con mensaje en espanol (`"feat: implementar parser"`)
> O con linea `Co-Authored-By`.
> **When:** `commits.create(phase="green", message=...)` se invoca.
> **Then:** lanza `ValidationError`; `git log` NO muestra nuevo commit;
> mensaje: "commit message must be English / no Co-Authored-By".
> *Ref: INV-0 sec.S.10.0, INV-5..7 sec.S.10.2.*

### 4.6 Subcomandos

**Escenario 11: `/sbtdd init` — happy path Rust stack**

> **Given:** proyecto git vacio, sin `CLAUDE.local.md`, 7 dependencias
> sec.S.1.3 presentes.
> **When:** `/sbtdd init --stack rust --author "Test" --error-type "TestErr"`.
> **Then:** 5 fases (pre-flight → args → generacion atomica → smoke test
> → reporte); 5 archivos creados; `.gitignore` con 3 entries; exit 0;
> segunda invocacion con `--force` idempotente.
> *Ref: sec.S.5.1, sec.S.12.1.*

**Escenario 12: `/sbtdd spec` — loop MAGI con degraded handling**

> **Given:** `sbtdd/spec-behavior-base.md` completo (sin
> `TODO`/`TODOS`/`TBD`); stub MAGI retorna `HOLD` degraded iter 1,
> `GO_WITH_CAVEATS` full iter 2.
> **When:** `/sbtdd spec`.
> **Then:** iter 1 aplica conditions pero NO sale (INV-28); iter 2 pasa
> gate; state file creado con `plan_approved_at`; residuales archivados.
> Negative: 3 iter `STRONG_NO_GO` → exit 8.
> *Ref: sec.S.5.2, INV-28.*

**Escenario 13: `/sbtdd close-phase` — ciclo 3 fases x 1 tarea**

> **Given:** plan con tarea `[ ]`, state `current_phase="red"`, tree
> clean, `plan_approved_at != null`.
> **When:** Red tests → close-phase; Green impl → close-phase
> `--variant feat`; Refactor → close-phase.
> **Then:** 3 commits atomicos (`test:`, `feat:`, `refactor:`) + al
> cerrar refactor: auto-invoca close-task → 4to commit
> `chore: mark task 1 complete` + `[x]` en plan + state
> `current_phase="done"`.
> *Ref: sec.S.5.3 + sec.S.5.4, INV-1..4.*

**Escenario 14: `/sbtdd close-task` — bookkeeping atomico**

> **Given:** ultimo commit `refactor:`, state `current_phase="refactor"`,
> plan con tarea activa `[ ]`.
> **When:** close-task ejecuta.
> **Then:** `[x]` marcado; commit `chore: mark task {id} complete`
> conteniendo SOLO edicion del plan; si hay proximo `[ ]`: avanza
> `current_task_id` + `current_phase="red"`; si no: `null` + `"done"`.
> *Ref: sec.S.5.4, INV-3.*

**Escenario 15: `/sbtdd status` — drift detection read-only**

> **Given:** state `current_phase="green"` + ultimo commit `refactor:`
> (drift sintetico).
> **When:** `/sbtdd status`.
> **Then:** reporte con linea `Drift: detected: state=green, HEAD=refactor:, plan=[ ]`;
> exit 3; NO modifica archivos; NO escala.
> *Ref: sec.S.5.5, sec.S.9.2.*

**Escenario 16: `/sbtdd pre-merge` — Loop 1 + Loop 2 con INV-28/29**

> **Given:** state `current_phase="done"`, plan todo `[x]`, git clean.
> Stubs: `/requesting-code-review` 1 `[CRITICAL]` iter 1 + clean-to-go
> iter 2; `/magi:magi` `GO_WITH_CAVEATS` full iter 1 con 1 condition
> bajo-riesgo.
> **When:** `/sbtdd pre-merge`.
> **Then:** Loop 1 mini-cycle TDD (3 commits), clean-to-go. Loop 2
> `/receiving-code-review` acepta + mini-cycle; sale full + bajo-riesgo;
> `magi-verdict.json` con `degraded: false`; exit 0.
> *Ref: sec.S.5.6, INV-28/29.*

**Escenario 17: `/sbtdd finalize` — checklist gate**

> **Given:** `magi-verdict.json` con `degraded: false` y verdict ≥
> threshold; items de sec.M.7 pasables.
> **When:** `/sbtdd finalize`.
> **Then:** verifica 9 items; todos pasan; invoca
> `/finishing-a-development-branch`; exit 0. Negative: `degraded: true`
> → exit 9 ("Gate MAGI aprobado Y no-degraded").
> *Ref: sec.S.5.7, INV-10/28.*

**Escenario 18: `/sbtdd auto` — shoot-and-forget full-cycle**

> **Given:** `spec` completo, `plan_approved_at != null`, 3 tareas `[ ]`.
> **When:** `/sbtdd auto`.
> **Then:** 5 fases (pre-flight → task loop [12 commits: 3 fases × 3
> tareas + 3 chore] → pre-merge con INV-28/29 → checklist → reporte);
> `auto-run.json` trazabilidad; NO invoca
> `/finishing-a-development-branch`; exit 0. Errors: `--dry-run` → 0
> sin escribir; retries agotados → 6; Loop 1 > 10 → 7; STRONG_NO_GO →
> 8; quota → 11.
> *Ref: sec.S.5.8, INV-22..26 + 28/29.*

**Escenario 19: `/sbtdd resume` — diagnostico + delegacion**

> **Given:** state `current_phase="green"`, tree dirty (2 M + 1
> untracked), `auto-run.json` residual.
> **When:** `/sbtdd resume --auto`.
> **Then:** pre-flight → reporte diagnostico → decision delegacion a
> `/sbtdd auto` → uncommitted resuelto default CONTINUE (INV-24
> conservador) → delega. Variants: `--discard-uncommitted` →
> `git checkout HEAD -- .` + `git clean -fd`; `--dry-run` → plan sin
> side effects; drift → exit 3 sin delegar.
> *Ref: sec.S.5.10, INV-30.*

---

## 5. Scope exclusions

Se preservan todas las exclusiones de sec.S.1.4 del contrato:

- Re-implementar logica de TDD-Guard (es binario externo; solo se invoca).
- Re-implementar logica de superpowers skills (se orquestan).
- Re-implementar MAGI (se invoca; sus veredictos se parsean).
- Enforzar disciplina Red-Green-Refactor a nivel fisico (TDD-Guard lo hace).
- Garantizar atomicidad semantica de commits mas alla de prefijo +
  diff scope.
- Automatizar decisiones subjetivas (approval, trade-offs MAGI
  fronterizos).
- Distribucion binaria (solo codigo fuente Python via marketplace
  GitHub).

Adicionales para este mega-feature v0.1 (se difieren a iteraciones
futuras per sec.S.13):

- **Soporte multi-framework C++:** v0.1 solo `ctest` + JUnit XML; NO
  adaptadores para GoogleTest/Catch2/bazel/meson (sec.S.13 item 7).
- **Paridad de verification checks entre stacks:** v0.1 mantiene Rust
  6 checks / Python 4 / C++ 2; NO expansion a 6 checks uniformes
  (sec.S.13 item 9).
- **`schema_version` en plugin.local.md:** queda para v0.2 cuando
  haya breaking changes reales (sec.S.13 item 5).
- **Sub-skills separados** `sbtdd-rules` / `sbtdd-tdd-cycle`: NO se
  crean como directorios independientes; viven embebidos en SKILL.md
  per paridad MAGI (sec.S.6.3).

---

## 6. Criterios de aceptacion finales

El mega-feature se considera terminado cuando **todos** los items de
sec.S.12 del contrato pasan. Resumen por subseccion:

- **sec.S.12.1 Funcionales:** 12 items — INV-0 enforcement cross-
  subcommand, init happy path + idempotencia, spec loop MAGI con
  safety valve, close-phase x 3, status read-only + drift, pre-merge
  Loop 1+2 con STRONG_NO_GO stop, finalize checklist, auto full-cycle
  (incluyendo `--dry-run` + todos los exit codes), INV-28 en 3
  contextos, INV-29 gate + feedback, quota_detector 4 patrones,
  INV-30 resume (6 variantes).
- **sec.S.12.2 Paridad con MAGI:** 9 items — layout identico,
  pyproject mypy strict + ruff 100, Makefile 5 targets, conftest.py
  tdd-guard, plugin.json + marketplace.json version-sync, LICENSE +
  LICENSE-APACHE dual, README profesional (F14: shields + usage +
  arch + contributing), CLAUDE.md con 6 secciones, headers
  Author/Version/Date en todo `.py`.
- **sec.S.12.3 No-funcionales:** 4 items — idempotencia
  `init --force` byte-identica, atomicidad (fallo parcial deja
  proyecto intacto), performance `/sbtdd status` < 1s en repos 10k
  commits, portabilidad Windows/Linux/macOS.
- **sec.S.12.4 Test coverage:** 8 items — >= 1 test file por modulo
  bajo `scripts/`, contrato por subcomando, schema state file,
  deteccion drift, idempotencia init, fusion settings.json, fixtures
  `tests/fixtures/`, `make verify` limpio.
- **sec.S.12.5 Distribucion:** 4 items — repo publico GitHub
  `BolivarTech/sbtdd-workflow`, instalable via
  `/plugin marketplace add` + `install`, version sync plugin.json ↔
  marketplace.json, symlink dev documentado.

**Gate MAGI final:** pre-merge debe retornar veredicto full
(no-degraded) ≥ `GO_WITH_CAVEATS` con los findings aplicados via
`/receiving-code-review` + mini-ciclo TDD (INV-28 + INV-29
respetados). El plan acumula ~80-100 tareas estimadas; es
responsabilidad de `/writing-plans` descomponer y ordenar
topologicamente.
