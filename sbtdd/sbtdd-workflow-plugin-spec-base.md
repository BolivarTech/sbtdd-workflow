# Especificacion: plugin `sbtdd-workflow`

> **ENFORCEMENT ABSOLUTO — `~/.claude/CLAUDE.md` es la autoridad maxima.**
> Las reglas globales del desarrollador en `~/.claude/CLAUDE.md` (Code
> Standards: paradigma OOP, calidad, documentacion, estilo, error
> handling, testing, TDD Red-Green-Refactor, dependencias, memoria,
> seguridad, output format, build/environment, git con mensajes en ingles
> sin referencias a IA) tienen **precedencia absoluta** sobre cualquier
> disposicion de este spec, la metodologia SBTDD embebida, y cualquier
> configuracion del proyecto destino. **Todo subcomando, toda transicion
> de estado, todo commit y toda interaccion con sistemas externos DEBE
> respetarlas sin excepcion.** En caso de conflicto, `~/.claude/CLAUDE.md`
> prevalece siempre. El plugin NO implementa flags ni overrides para
> eludir esta regla. Esta clausula se formaliza como **INV-0** en
> sec.S.10.0 y se testea en cada subcomando — ver sec.S.12.1.
>
> Documento de especificacion funcional y de comportamiento para un plugin de
> Claude Code que materializa la metodologia **SBTDD** (Spec + Behavior +
> Test Driven Development combinada con el ecosistema Superpowers
> multi-agente) como componentes ejecutables (skill dispatcher +
> subcomandos Python + hooks). Este documento es el **contrato**; la
> implementacion debe cumplirlo literalmente.
>
> **Autocontencion:** el plugin es autocontenido. La metodologia SBTDD esta
> encarnada en los artefactos del plugin: `skills/sbtdd/SKILL.md` (reglas
> embebidas), `templates/*.template` (CLAUDE.local.md parametrizable que se
> instala en el proyecto destino), y los subcomandos Python. El plugin NO
> depende en runtime de ningun archivo externo a su propia distribucion.
>
> **Sobre las referencias `sec.N`:** las secciones numeradas (sec.0, sec.1, sec.2, etc.)
> que este documento cita son referencias internas a la organizacion
> conceptual de la metodologia SBTDD, tal como esta codificada en el propio
> plugin (principalmente en el template `templates/CLAUDE.local.md.template`
> y en `SKILL.md`). No apuntan a ningun archivo en la maquina del usuario
> ni a un documento externo; son shorthand de diseno para correlacionar
> comportamientos del plugin con bloques semanticos de la metodologia.
>
> **Referencia de arquitectura de implementacion (no distribuida):** el
> plugin MAGI v2.1.3 es el patron arquitectonico a seguir — estructura de
> directorios, convenciones Python, tooling de desarrollo, modelo de
> distribucion (marketplace via GitHub), formato de SKILL.md y patron de
> dispatch a scripts Python. Esta referencia no es una dependencia: MAGI
> se usa como guia durante la autoria/desarrollo del plugin, no como
> componente runtime.

---

## 0. Convenciones de este documento

- **MUST / DEBE**: invariante no-negociable. Una implementacion que no lo
  cumple es incorrecta.
- **SHOULD / DEBERIA**: recomendacion fuerte; desviarse requiere justificacion
  explicita en la documentacion del plugin.
- **MAY / PUEDE**: opcional.
- **metodologia SBTDD**: el cuerpo de reglas operativas que este plugin
  encarna, distribuido dentro de los artefactos del propio plugin (SKILL.md
  + templates/ + subcomandos). No es un archivo externo.
- **Notacion `sec.N`:** prefijo ASCII para todas las referencias seccionales
  (reemplaza el signo `§` usado en versiones previas del spec por portabilidad
  en CI logs, grep, emails, etc.). Tres variantes:
  - **`sec.N`** (sin prefijo): seccion de la **metodologia SBTDD** con ese
    numero. Es shorthand de correlacion de diseno; no apunta a ningun archivo
    externo. En ausencia de prefijo, el contexto implica metodologia (p.ej.
    "sec.3 reglas de fase", "sec.5 prefijos de commit", "sec.6 Loops pre-merge",
    "sec.7 checklist de finalizacion").
  - **`sec.M.N`**: referencia explicita a la **metodologia** (`M`). Se usa
    cuando podria haber colision con un numero tambien usado en este spec.
  - **`sec.S.N`**: referencia explicita a una seccion de **este spec** (`S`).
    Se usa cuando podria haber colision.
- **Regla por default:** en ausencia de prefijo M/S, numeros pequenos (sec.0,
  sec.1, sec.2, sec.3, sec.5, sec.6, sec.7 — los de la metodologia) son
  metodologia; numeros compuestos con sub-nivel (sec.5.1, sec.5.8, sec.11.1 —
  estructura de este spec) son spec. La notacion explicita (sec.M.N /
  sec.S.N) se usa solo cuando hay colision posible, p.ej. sec.M.5
  (metodologia: prefijos commit) vs sec.S.5.1 (spec: `init`).
- **proyecto destino**: el repositorio donde el plugin se instala via
  `/sbtdd init`, distinto del repositorio del plugin en si.
- **CLAUDE.local.md del proyecto destino**: el archivo instanciado por
  `init` a partir de `templates/CLAUDE.local.md.template`, que contiene las
  reglas SBTDD parametrizadas al stack y autor del proyecto. Es donde vive
  operativamente la metodologia en el proyecto destino.

---

## 1. Vision general

### 1.1 Proposito

Operacionalizar el flujo SBTDD + Superpowers (multi-agente) como un plugin
Claude Code instalable via marketplace, de modo que:

1. La configuracion de `.claude/settings.json` (hooks TDD-Guard) se instale
   deterministicamente via el subcomando `init` en vez de copiarse manualmente.
2. Las transiciones de estado runtime (state file, plan checkbox, commits
   atomicos) se ejecuten via subcomandos dedicados que aplican el protocolo
   de sec.M.2.3 y sec.M.3 de la metodologia sin re-implementar la logica
   en cada sesion.
3. Los dos loops pre-merge (Loop 1 `/requesting-code-review`, Loop 2
   `/magi:magi`) se orquesten via `pre-merge` con gate de umbral enforzado,
   eliminando la posibilidad de saltarse uno.
4. Las reglas no-ejecutables (sec.0, sec.M.2.4, sec.5 excepciones, sec.6 semantica) se
   expongan como secciones de la SKILL.md cargables bajo demanda, evitando
   que el agente las olvide o las reinterprete.

### 1.2 Alcance

**Dentro de alcance:**

- Bootstrapping de proyecto SBTDD (directorios, template, hooks, gitignore).
- Orquestacion de skills externas (superpowers, magi) en secuencias con gates.
- Lectura, escritura y validacion de `.claude/session-state.json`.
- Transiciones de fase TDD con verificacion + commit + update de state file.
- Cierre de tarea con marcado de checkbox del plan y avance.
- Ejecucion secuencial de Loop 1 + Loop 2 pre-merge con enforcement de umbral.
- Parametrizacion por stack (Rust / Python / C++) via `plugin.local.md` del
  proyecto destino.
- Deteccion de drift entre state file, git y plan (sec.M.2.1 "Orden de autoridad").

**Fuera de alcance (non-goals):**

- Re-implementar la logica de TDD-Guard (es binario externo — solo se invoca).
- Re-implementar la logica de superpowers skills (se orquestan, no se
  sustituyen).
- Re-implementar MAGI (se invoca, no se sustituye).
- Enforzar disciplina Red-Green-Refactor a nivel fisico (TDD-Guard lo hace).
- Garantizar atomicidad semantica de commits mas alla de lo detectable por
  prefijo y diff scope — la intencion del desarrollador no es observable.
- Automatizar decisiones subjetivas: aprobacion de plan, aceptacion de
  findings `[INFO]`, trade-offs de diseno reportados por MAGI. El plugin
  detiene y escala al usuario en esos puntos.
- Distribucion binaria. El plugin se distribuye como codigo fuente Python
  via marketplace GitHub; el usuario necesita Python 3.9+ instalado.

### 1.3 Dependencias externas (TODAS obligatorias)

El plugin DEBE verificar **todas** las dependencias durante `/sbtdd init`
antes de crear cualquier artefacto. Sin excepciones: el workflow SBTDD no
opera sin su cadena completa, y fallos parciales descubiertos a mitad de
camino (p.ej. `spec` fallando porque MAGI no esta instalado tras haber
hecho `init`) son inaceptables.

| # | Dependencia | Tipo | Uso | Criterio de "operativa" |
|---|-------------|------|-----|-------------------------|
| 1 | Python >= 3.9 | runtime | Ejecutar todos los scripts del plugin | `sys.version_info >= (3, 9)` |
| 2 | `git` | binario en PATH | Operaciones de commit, status, log | `shutil.which("git")` + `git --version` retorna exit 0 |
| 3 | `tdd-guard` | binario en PATH | Enforcement TDD en hooks del proyecto destino | `shutil.which("tdd-guard")` + `tdd-guard --version` retorna exit 0 + el directorio `.claude/tdd-guard/data/` es creable/escribible |
| 4 | Plugin `superpowers` | plugin CC instalado | Provee skills de workflow (`brainstorming`, `writing-plans`, `test-driven-development`, `verification-before-completion`, `requesting-code-review`, `receiving-code-review`, `executing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `systematic-debugging`, `using-git-worktrees`, `finishing-a-development-branch`) | Plugin descubrible en `~/.claude/plugins/` (cache o marketplaces) con los SKILL.md esperados presentes |
| 5 | Plugin `magi` | plugin CC instalado | Provee `/magi:magi` para Checkpoint 2 (spec) y Loop 2 (pre-merge) | Plugin descubrible con `skills/magi/SKILL.md` + `scripts/run_magi.py` |
| 6 | Toolchain del stack | binarios en PATH | Comandos sec.M.0.1 de la metodologia + reporter TDD-Guard del stack | Solo se valida el stack elegido (si `init --stack python`, no se verifican binarios Rust ni C++). **Rust**: `cargo`, `cargo-nextest`, `cargo-audit`, `cargo-clippy`, `cargo-fmt`, `tdd-guard-rust` (binario externo obligatorio para traducir output de nextest al schema TDD-Guard; install: `cargo install tdd-guard-rust`). **Python**: `python`, `pytest`, `ruff`, `mypy` (reporter via `conftest.py` shipped por el plugin — no binario extra). **C++**: `cmake`, `ctest` (con soporte `--output-junit`); el reporter es `ctest_reporter.py` dentro del plugin, parsea JUnit XML. **En v0.1 solo se soporta `ctest` como launcher de tests C++** — otros runners (bazel, meson, GoogleTest directo, Catch2 standalone) no estan cubiertos (ver sec.13 item 8) |
| 7 | Working tree git | estado | El proyecto destino es un repo valido | `.git/` existe. **`init` NO ejecuta `git init` en ningun caso** — si `.git/` no esta presente, el check falla y `init` aborta con exit 2 sugiriendo al usuario ejecutar `git init` manualmente antes de reintentar |

**Regla estricta de abort:**

Si **una sola** dependencia obligatoria no pasa su criterio, `init`:

1. **No crea ningun archivo** — el proyecto destino queda exactamente como
   estaba antes de invocar el subcomando.
2. **Agrega todos los fallos** — continua la verificacion hasta el final
   para reportar todos los items faltantes en una sola pasada; nunca se
   detiene al primer fallo.
3. **Aborta con exit code 2** (`PreconditionError`) e imprime el reporte
   estructurado de sec.5.1.1.
4. **Es re-entrante** — tras instalar lo faltante, volver a invocar
   `/sbtdd init` con los mismos argumentos reanuda desde cero, sin estado
   parcial residual.

No existe el concepto de "dependencia opcional con warning" en este plugin.
O el entorno esta completo, o `init` no procede.

### 1.4 No-objetivos explicitos

- **El plugin no commitea sin autorizacion fuera de los 4 contextos de
  sec.M.5 "Excepcion bajo plan aprobado" de la metodologia**. Si la aprobacion del plan no
  esta registrada (estado del state file o flag explicito), el plugin pide
  permiso.
- **El plugin no modifica archivos del desarrollador del proyecto destino
  fuera del scope autorizado.** En particular:
  1. No edita el **`CLAUDE.md` del proyecto destino** — es la memoria
     permanente del desarrollador (decisiones arquitectonicas duraderas).
     El subcomando `finalize` puede *sugerir* actualizarlo en el reporte,
     pero nunca lo edita por si mismo.
  2. No toca codigo fuente del proyecto destino fuera de lo que produce
     cada fase TDD del plan aprobado.
  3. No modifica archivos bajo `templates/` del propio repo del plugin en
     runtime — son recursos estaticos versionados con el codigo, solo
     lectura durante la ejecucion de `init`.

  Scope autorizado del plugin en el proyecto destino: `.claude/`,
  `sbtdd/`, `planning/`, `CLAUDE.local.md`, appends idempotentes a
  `.gitignore`, `conftest.py` en la raiz (solo si `--stack python`),
  y archivos fuente del proyecto como parte de fases TDD de un plan
  aprobado.

  **Runtime artifacts generados bajo `.claude/` (todos gitignored):**

  | Archivo | Escritor | Proposito | Ciclo de vida |
  |---------|----------|-----------|---------------|
  | `.claude/settings.json` | `init` (merge), raramente otros | Hooks TDD-Guard | Persistente; se re-fusiona en cada `init --force` |
  | `.claude/plugin.local.md` | `init` | Config del proyecto (stack, verification_commands, umbrales) | Persistente; editable manualmente |
  | `.claude/session-state.json` | `spec` crea, `close-phase`/`close-task`/`auto` actualizan | Estado runtime del ciclo TDD activo | Por-feature; al cerrar un plan queda en `done` y el siguiente `spec` lo archiva |
  | `.claude/magi-verdict.json` | `pre-merge`, `auto` | Registro del ultimo veredicto MAGI + conditions + flag `degraded` (ver INV-28) | Por-feature; sobrescrito en cada corrida de pre-merge |
  | `.claude/auto-run.json` | `auto` | Trazabilidad de corrida shoot-and-forget, incluyendo por iteracion: `magi_verdict`, `magi_degraded`, `conditions_proposed/accepted/rejected`, `rejection_history_passed_to_magi` (INV-29 feedback loop) | Por-corrida de auto; sobrescrito en cada invocacion |
  | `.claude/tdd-guard/data/test.json` | Reporters (rust_reporter, conftest, ctest_reporter) | Resultado de tests para TDD-Guard | Actualizado en cada ejecucion de tests |
- **El plugin no re-ejecuta automaticamente MAGI o review tras cambios
  subjetivos**; el usuario indica cuando re-correr.

---

## 2. Arquitectura del plugin

### 2.1 Layout del repositorio del plugin (replica de MAGI)

```
sbtdd-workflow/
├── .claude-plugin/
│   ├── plugin.json                      # Manifest CC (name, version, skills path)
│   └── marketplace.json                 # Marketplace catalog para install
├── .claude/
│   ├── settings.json                    # Hooks TDD-Guard para desarrollo del plugin
│   └── settings.local.json              # Permisos locales (gitignored)
├── .gitignore
├── CLAUDE.md                            # Guia tecnica del proyecto (espejo del MAGI CLAUDE.md)
├── CLAUDE.local.md                      # Reglas project-specific (minimal)
├── LICENSE                              # MIT
├── LICENSE-APACHE                       # Apache-2.0
├── Makefile                             # verify / test / lint / format / typecheck
├── README.md                            # Descripcion, installation, usage (estilo MAGI)
├── conftest.py                          # pytest hook + tdd-guard integration
├── pyproject.toml                       # Python >= 3.9, dual license, dev deps, ruff/mypy
├── uv.lock                              # uv lockfile (opcional; recomendado)
├── skills/
│   └── sbtdd/
│       ├── SKILL.md                     # Orchestrator: complexity gate + subcommand dispatch
│       └── scripts/
│           ├── __init__.py              # Package marker con header Author/Version/Date
│           ├── models.py                # Registros inmutables (prefijos commit, umbrales, etc.)
│           ├── errors.py                # SBTDDError base + subclases tipadas
│           ├── config.py                # Parser de plugin.local.md (YAML frontmatter)
│           ├── state_file.py            # Lectura/escritura/validacion de session-state.json
│           ├── commits.py               # Helpers de commit con prefijo validado
│           ├── hooks_installer.py       # Fusion idempotente de .claude/settings.json
│           ├── templates.py             # Expansion de archivos en templates/
│           ├── drift.py                 # Deteccion drift state vs git vs plan
│           ├── subprocess_utils.py      # Wrappers subprocess (estilo MAGI)
│           ├── superpowers_dispatch.py  # Invocacion de skills superpowers
│           ├── magi_dispatch.py         # Invocacion de /magi:magi, parsing de veredicto + flag `degraded`, y construccion de contexto de feedback (INV-29) para iteraciones subsiguientes del Loop 2. Usa quota_detector.py para mapear exhaustion de cuota Anthropic a exit 11
│           ├── quota_detector.py        # Deteccion de exhaustion de cuota externa (Anthropic API rate limit / session / weekly / credit). Regex-match sobre stderr de skills invocados (sec.S.11.4)
│           ├── run_sbtdd.py             # Entrypoint unico: python run_sbtdd.py <sub> [args]
│           ├── dependency_check.py      # Pre-flight check (usado por init, auto, status opcional)
│           ├── init_cmd.py              # Subcomando init
│           ├── spec_cmd.py              # Subcomando spec
│           ├── close_phase_cmd.py       # Subcomando close-phase
│           ├── close_task_cmd.py        # Subcomando close-task
│           ├── status_cmd.py            # Subcomando status
│           ├── pre_merge_cmd.py         # Subcomando pre-merge
│           ├── finalize_cmd.py          # Subcomando finalize
│           ├── auto_cmd.py              # Subcomando auto (shoot-and-forget, sec.5.8)
│           ├── resume_cmd.py            # Subcomando resume (recovery tras interrupcion, sec.5.10)
│           └── reporters/
│               ├── __init__.py
│               ├── tdd_guard_schema.py  # Dataclasses del schema test.json + writer comun
│               ├── rust_reporter.py     # Wrapper: cargo nextest | tdd-guard-rust (sin shell)
│               └── ctest_reporter.py    # Parser JUnit XML → test.json de TDD-Guard
├── templates/
│   ├── CLAUDE.local.md.template         # Template parametrizable (stack, author, error_type)
│   ├── plugin.local.md.template         # Schema de configuracion del proyecto destino
│   ├── settings.json.template           # Hooks TDD-Guard para el proyecto destino
│   ├── spec-behavior-base.md.template   # Esqueleto SBTDD
│   ├── conftest.py.template             # Reporter pytest (instalado por init --stack python)
│   └── gitignore.fragment               # Entradas a appendear al .gitignore destino
└── tests/
    ├── fixtures/
    │   ├── plans/                       # Planes sinteticos para tests
    │   ├── state-files/                 # state files validos e invalidos
    │   └── plugin-locals/               # plugin.local.md de prueba
    ├── test_models.py
    ├── test_errors.py
    ├── test_config.py
    ├── test_state_file.py
    ├── test_commits.py
    ├── test_hooks_installer.py
    ├── test_templates.py
    ├── test_drift.py
    ├── test_subprocess_utils.py
    ├── test_superpowers_dispatch.py
    ├── test_magi_dispatch.py
    ├── test_run_sbtdd.py
    ├── test_init_cmd.py
    ├── test_spec_cmd.py
    ├── test_close_phase_cmd.py
    ├── test_close_task_cmd.py
    ├── test_status_cmd.py
    ├── test_pre_merge_cmd.py
    ├── test_finalize_cmd.py
    ├── test_auto_cmd.py
    ├── test_resume_cmd.py
    ├── test_dependency_check.py
    ├── test_quota_detector.py
    ├── test_reporters_schema.py
    ├── test_reporters_rust.py
    ├── test_reporters_ctest.py
    └── test_conftest_template.py
```

**Notas sobre el layout (diferencias con MAGI):**

- MAGI tiene un solo skill (`magi`) con 3 modos (`code-review | design |
  analysis`). `sbtdd-workflow` sigue el mismo patron: **un solo skill
  (`sbtdd`) con 9 subcomandos** (`init | spec | close-phase | close-task |
  status | pre-merge | finalize | auto | resume`). El dispatcher unico
  es `run_sbtdd.py` (analogo a `run_magi.py`).
- MAGI tiene un subdirectorio `agents/` con system prompts para Melchior /
  Balthasar / Caspar. `sbtdd-workflow` NO tiene agents propios — delega
  analisis multi-perspectiva al plugin `magi`. Por tanto `skills/sbtdd/`
  NO incluye `agents/`.
- MAGI tiene `docs/` con documentacion tecnica. `sbtdd-workflow` PUEDE
  tener `docs/` si el README + CLAUDE.md no bastan.

### 2.2 Inventario de componentes

| Tipo | Nombre | Rol resumido |
|------|--------|--------------|
| skill | `sbtdd` | Orquestador unico (SKILL.md + run_sbtdd.py) que dispatcha los 9 subcomandos |
| subcomando | `init` | Bootstrap del proyecto destino |
| subcomando | `spec` | Orquesta flujo de especificacion (sec.M.1 "Flujo de especificacion") |
| subcomando | `close-phase` | Cierra fase TDD activa (sec.M.3, 3 pasos de cierre atomico) |
| subcomando | `close-task` | Cierra tarea (post-Refactor): checkbox + state + avance |
| subcomando | `status` | Reporta estado actual (state file + git + plan) |
| subcomando | `pre-merge` | Ejecuta Loop 1 + Loop 2 con gate MAGI (sec.M.6) |
| subcomando | `finalize` | Valida checklist sec.M.7 e invoca `/finishing-a-development-branch` |
| subcomando | `auto` | Modo shoot-and-forget: encadena ejecucion de tareas + pre-merge + checklist sec.M.7 sin intervencion humana. Presupuesto MAGI elevado a `auto_magi_max_iterations` (default 5 vs 3 interactivo). Entrega branch con `git status` limpio listo para que el usuario invoque `/sbtdd finalize` o `/finishing-a-development-branch` manualmente |
| subcomando | `resume` | Wrapper de recuperacion tras interrupcion (token exhaustion, crash, Ctrl+C, reinicio). Lee state file + git HEAD + runtime artifacts, diagnostica el punto de interrupcion, y delega al subcomando apropiado (`auto`, `pre-merge`, o `finalize`). Maneja trabajo sin commitear via default CONTINUE + flag opcional `--discard-uncommitted` para escape valve. Ver INV-30 |
| hook template | `settings.json.template` | Hooks TDD-Guard para el proyecto destino; instalado por `init` |
| template | `CLAUDE.local.md.template` | Reglas del proyecto instanciadas con placeholders resueltos |
| template | `plugin.local.md.template` | Configuracion por proyecto (stack, toolchain, author) |
| invocacion desde SKILL.md | `sbtdd-rules` | Seccion de referencia cargable dentro del propio SKILL.md |
| invocacion desde SKILL.md | `sbtdd-tdd-cycle` | Seccion de guia de ciclo TDD dentro del propio SKILL.md |

> Nota sobre `sbtdd-rules` / `sbtdd-tdd-cycle`: MAGI no crea skills separados
> para sus "reglas internas" — las embebe en SKILL.md. Para mantener
> paridad, SBTDD hace lo mismo: las secciones de reglas y de guia del ciclo
> TDD viven en `skills/sbtdd/SKILL.md`, accesibles leyendo el archivo. No
> hay `skills/sbtdd-rules/` ni `skills/sbtdd-tdd-cycle/` separados.

### 2.3 Flujo de datos entre componentes

```
Usuario
  │
  ├─[/sbtdd init]───────────► scripts/init_cmd.py
  │                            genera: CLAUDE.local.md, .claude/settings.json,
  │                                     .claude/plugin.local.md, sbtdd/, planning/,
  │                                     .gitignore (appended)
  │
  ├─[/sbtdd spec]───────────► scripts/spec_cmd.py
  │                            invoca via superpowers_dispatch.py:
  │                              /brainstorming → /writing-plans → /magi:magi
  │                            genera: sbtdd/spec-behavior.md,
  │                                     planning/claude-plan-tdd-org.md,
  │                                     planning/claude-plan-tdd.md
  │
  ├─[trabajo TDD con /subagent-driven-development o /executing-plans]
  │      │
  │      ├─[/sbtdd close-phase]───► scripts/close_phase_cmd.py
  │      │                           lee/escribe: .claude/session-state.json
  │      │                           invoca: /verification-before-completion
  │      │                           produce: commit atomico con prefijo sec.5
  │      │
  │      └─[/sbtdd close-task]────► scripts/close_task_cmd.py
  │                                  marca [x] en planning/claude-plan-tdd.md,
  │                                  commit `chore:`, avanza state file
  │
  ├─[/sbtdd status]─────────► scripts/status_cmd.py
  │                            reporta: state file + git HEAD + plan pending count
  │
  ├─[/sbtdd pre-merge]──────► scripts/pre_merge_cmd.py
  │                            loop 1: /requesting-code-review + /receiving-code-review
  │                            loop 2: /magi:magi + /receiving-code-review
  │                                     (gate: veredicto >= GO WITH CAVEATS
  │                                     AND no-degraded AND findings
  │                                     aceptadas por receiving-code-review;
  │                                     ver INV-28 e INV-29)
  │                            produce: commits mini-ciclo con prefijos
  │                                      `test:`, `fix:`, `refactor:`
  │
  ├─[/sbtdd finalize]───────► scripts/finalize_cmd.py
  │                            valida checklist sec.7,
  │                            invoca /finishing-a-development-branch
  │
  └─[/sbtdd auto]───────────► scripts/auto_cmd.py (sec.5.8)
                               encadena: task loop + pre-merge + checklist sec.7
                               sin intervencion humana. Mismos gates INV-28
                               (degraded) + INV-29 (receiving-code-review +
                               feedback history) que pre-merge.
                               presupuesto MAGI elevado a auto_magi_max_iterations (5).
                               NO invoca /finishing-a-development-branch;
                               termina con git clean y delega merge/PR al usuario.
```

**Patron de invocacion SKILL.md → Python (espejo de MAGI):**

SKILL.md NO ejecuta logica directamente. Delega al entrypoint unico via
Bash tool. Ejemplo textual dentro de SKILL.md:

```
    python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <subcommand> [args...]
```

`run_sbtdd.py` resuelve el subcomando y delega al modulo correspondiente.
Esto replica el patron MAGI donde SKILL.md ejecuta
`python skills/magi/scripts/run_magi.py <mode> <input>`.

---

## 3. Manifest del plugin (`.claude-plugin/plugin.json`)

### 3.1 Estructura requerida (espejo de MAGI)

`.claude-plugin/plugin.json`:

```jsonc
{
  "name": "sbtdd-workflow",
  "version": "0.1.0",
  "description": "SBTDD + Superpowers multi-agent workflow orchestrator. Operationalizes the Spec + Behavior + Test Driven Development methodology with mandatory pre-merge gates (code review + MAGI consensus).",
  "author": {
    "name": "BolivarTech",
    "url": "https://github.com/BolivarTech"
  },
  "repository": "https://github.com/BolivarTech/sbtdd-workflow",
  "license": "MIT OR Apache-2.0",
  "keywords": [
    "sbtdd",
    "tdd",
    "test-driven-development",
    "multi-agent",
    "workflow",
    "superpowers"
  ],
  "skills": "./skills/"
}
```

### 3.2 Marketplace manifest (`.claude-plugin/marketplace.json`)

```jsonc
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "bolivartech-plugins",
  "description": "Claude Code plugins by BolivarTech",
  "version": "0.1.0",
  "owner": {
    "name": "BolivarTech",
    "url": "https://github.com/BolivarTech"
  },
  "plugins": [
    {
      "name": "sbtdd-workflow",
      "description": "SBTDD + Superpowers multi-agent workflow orchestrator",
      "version": "0.1.0",
      "author": {
        "name": "Julian Bolivar",
        "url": "https://github.com/BolivarTech"
      },
      "source": "./",
      "category": "development",
      "homepage": "https://github.com/BolivarTech/sbtdd-workflow",
      "tags": ["sbtdd", "tdd", "workflow", "multi-agent", "superpowers"]
    }
  ]
}
```

### 3.3 Reglas de versionado

- `version` en `plugin.json` y `marketplace.json` DEBE coincidir en todo
  momento.
- Bumps de version siguen semver:
  - `MAJOR`: breaking changes en el contrato de subcomandos o state file.
  - `MINOR`: nuevas features preservando contratos.
  - `PATCH`: bug fixes.
- Al publicar: bumpear ambos manifests, correr `make verify`, commitear,
  push a GitHub main (identico al flujo documentado en el CLAUDE.md de
  MAGI, seccion "Publishing updates").

### 3.4 Auto-discovery

Plugin.json DEBE registrar `"skills": "./skills/"`. Este campo activa el
descubrimiento automatico de `skills/sbtdd/SKILL.md` al instalarse.

---

## 4. Parametrizacion del proyecto destino (`plugin.local.md`)

### 4.1 Proposito

Los placeholders del template operativo `templates/CLAUDE.local.md.template`
(`{Author}`, `{ErrorType}`, stack, comandos
de verificacion sec.M.0.1) DEBEN resolverse a valores concretos una sola vez, al
instalar el plugin en un proyecto destino. El subcomando `init` genera
`.claude/plugin.local.md` con esos valores. Los demas subcomandos lo leen
via `scripts/config.py` para parametrizar su comportamiento.

### 4.2 Schema

El contenido de `verification_commands` depende del stack; cada stack tiene
su propio default que `init` escribe. El primer comando de la lista DEBE
ser el que invoca el test runner + reporter TDD-Guard (es lo que garantiza
que `.claude/tdd-guard/data/test.json` se actualice). El resto son checks
adicionales (lint, format, build, audit).

**Ejemplo (stack Rust — default de `init --stack rust`):**

```markdown
---
stack: rust | python | cpp
author: "Nombre Apellido"
error_type: "MyProjectError"              # Rust: usado en sec.M.0.2 (reglas project-specific de la metodologia); null para otros stacks
verification_commands:
  - "python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/reporters/rust_reporter.py"
  - "cargo clippy --tests -- -D warnings"
  - "cargo fmt --check"
  - "cargo build --release"
  - "cargo doc --no-deps"
  - "cargo audit"
commit_prefix_map:
  red: "test"
  green_feat: "feat"
  green_fix: "fix"
  refactor: "refactor"
  task_close: "chore"
plan_path: "planning/claude-plan-tdd.md"
plan_org_path: "planning/claude-plan-tdd-org.md"
spec_base_path: "sbtdd/spec-behavior-base.md"
spec_path: "sbtdd/spec-behavior.md"
state_file_path: ".claude/session-state.json"
magi_threshold: "GO_WITH_CAVEATS"         # minimo aceptable (interactivo y auto)
magi_max_iterations: 3                    # safety valve interactivo (sec.1 paso 6 y sec.6 loop correccion)
auto_magi_max_iterations: 5               # safety valve en modo auto (shoot-and-forget; ver sec.5.8)
auto_verification_retries: 1              # reintentos ante fallo de /verification-before-completion en auto
tdd_guard_enabled: true
worktree_policy: "optional"               # "optional" | "required" (auto honra el valor)
---

# Configuracion local del plugin sbtdd-workflow

Este archivo es generado por `/sbtdd init`. Editable manualmente si el stack
o toolchain cambia. No commitear (queda gitignored via `.claude/`).
```

**Variantes por stack de `verification_commands` (defaults que `init` escribe):**

```yaml
# Python (init --stack python)
verification_commands:
  - "pytest"                             # conftest.py instalado en la raiz escribe test.json
  - "ruff check ."
  - "ruff format --check ."
  - "mypy ."

# C++ (init --stack cpp)
verification_commands:
  - "ctest --test-dir build --output-junit build/test-results.xml --output-on-failure"
  - "python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/reporters/ctest_reporter.py build/test-results.xml .claude/tdd-guard/data/test.json"
  - "cmake --build build --config Release"
```

Los defaults son editables por el usuario tras `init`. Si el proyecto cambia
de test runner o agrega checks adicionales, edita `plugin.local.md` directamente.

### 4.3 Validacion

`scripts/config.py` DEBE implementar `load_plugin_local(path) -> PluginConfig`
con validacion explicita. `PluginConfig` es un `@dataclass(frozen=True)`
con un atributo por cada campo del schema sec.4.2, tipado estrictamente
(enums como `Literal["rust", "python", "cpp"]`, enteros como `int`,
listas como `tuple[str, ...]` para respetar inmutabilidad sec.8.5). El
loader lanza `ValidationError` (subclase de `SBTDDError`, sec.8.4) con el
nombre del campo ofensor ante cualquier fallo de schema.

**Validaciones:**

- `stack` DEBE ser uno de: `rust`, `python`, `cpp`.
- `verification_commands` DEBE ser no vacio.
- `magi_threshold` DEBE ser uno de: `STRONG_GO`, `GO`, `GO_WITH_CAVEATS`.
- `magi_max_iterations` DEBE ser entero >= 1.
- `auto_magi_max_iterations` DEBE ser entero >= `magi_max_iterations`
  (el modo auto nunca tiene menos presupuesto que el interactivo). Default 5.
- `auto_verification_retries` DEBE ser entero >= 0. Default 1.
- `worktree_policy` DEBE ser uno de: `"optional"`, `"required"`. Default
  `"optional"`. Con `"required"`, `auto` aborta si el directorio actual
  no es una worktree dedicada (sec.5.8 precondiciones).
- `tdd_guard_enabled` DEBE ser booleano. Default `true`. `false`
  desactiva la ejecucion de hooks TDD-Guard pero NO el reporter (el
  schema de `test.json` se sigue escribiendo — solo que TDD-Guard no lo
  consume). Usar con cautela; viola el espiritu de SBTDD.
- Rutas DEBEN ser relativas al root del proyecto destino.

Si el schema es invalido al leer, `config.py` lanza `SBTDDError` con el
campo ofensor. El subcomando consumidor detiene sin modificar estado.

**Limitacion de la validacion schema-only:** `config.py` valida tipos y
enums pero NO verifica que `verification_commands[0]` (o la secuencia
stack-dependiente) realmente produzca `.claude/tdd-guard/data/test.json`.
Si el usuario edita `plugin.local.md` y elimina el comando del reporter,
la validacion pasa pero TDD-Guard no recibira datos — falla silenciosa.
Este check runtime lo enforce el smoke test de `init` (sec.S.5.1.2), pero
NO se re-ejecuta en cada carga de `plugin.local.md`. Para re-verificar
tras una edicion manual, ejecutar `/sbtdd init --force` (re-corre el smoke
test) o invocar `python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/dependency_check.py`
con el flag `--smoke-test`.

---

## 5. Especificacion de subcomandos

Cada subcomando es un modulo Python `scripts/{name}_cmd.py` con una funcion
publica `run(args: Namespace) -> int` que retorna exit code (0 = ok). El
dispatcher `run_sbtdd.py` parsea `sys.argv`, valida el subcomando y llama al
modulo correspondiente.

Cada subcomando sigue esta estructura en su contrato:

- **Trigger**: como se invoca desde SKILL.md.
- **Argumentos**: posicionales y flags (parseados via `argparse`).
- **Precondiciones**: estado que DEBE existir antes de ejecutar.
- **Comportamiento**: pasos ordenados, deterministas.
- **Postcondiciones**: estado garantizado tras ejecucion exitosa.
- **Errores**: condiciones de fallo y comportamiento esperado (abortar con
  exit code != 0, escalar, revertir).
- **Invariantes**: propiedades que DEBEN sostenerse durante y despues.

### 5.1 `init`

**Trigger:** `/sbtdd init` en el proyecto destino.

**Argumentos:**

| Arg | Tipo | Default | Descripcion |
|-----|------|---------|-------------|
| `--stack` | `rust \| python \| cpp` | pregunta | Stack del proyecto. Si se omite y el terminal es interactivo, `init` pregunta explicitamente al usuario y valida la respuesta contra el enum; si no-interactivo, aborta listando `--stack` como arg faltante. No se asume default — el stack condiciona todo el pre-flight check y los artefactos generados |
| `--author` | string | pregunta | Nombre para header de archivos (sec.M.0.2 de la metodologia) |
| `--error-type` | string | pregunta (Rust) | Nombre del tipo de error del proyecto |
| `--conftest-mode` | `merge \| replace \| skip` | `merge` | Solo aplica con `--stack python`. Controla como se instala `conftest.py` (reporter pytest) en la raiz del proyecto destino. Ver sec.5.1.3 |
| `--force` | flag | false | Sobrescribir archivos existentes |

**Precondiciones:**

- Directorio actual es un proyecto (contiene `.git/`; si no, `init` NO
  inicializa el repo — aborta sugiriendo `git init`).
- No existe `CLAUDE.local.md` preexistente, O `--force` presente.

**Interaccion con `.claude/session-state.json` preexistente:** `init` NO
lee ni modifica el state file. Si existe de una instalacion previa, queda
intacto. Esto es intencional: `init` configura el proyecto (bootstrap),
mientras que `spec` gestiona el state file (ver sec.5.2). Con `--force`, los
artefactos de bootstrap se regeneran pero el state file runtime queda
como estaba. El usuario que quiera "empezar de cero de verdad" debe
eliminar `.claude/session-state.json` manualmente.

**Comportamiento — cinco fases estrictas, ninguna se salta:**

1. **Fase 1 — Pre-flight check (detallado en sec.5.1.1):** valida las 7
   dependencias obligatorias de sec.1.3. Agrega todos los fallos antes de
   reportar. Si alguna falla, aborta con exit code 2 y reporte estructurado.
   **NO SE CREAN ARTEFACTOS DEL PLUGIN EN ESTA FASE** — excepcion tecnica:
   la verificacion del check "tdd-guard writable data dir" (sec.S.5.1.1)
   crea `.claude/tdd-guard/data/` si no existe, porque probar escritura
   requiere que el directorio exista. Este directorio es gitignored
   (forma parte de `.claude/`) y se considera infraestructura runtime,
   no artefacto de configuracion. Si Fase 1 aborta despues de crearlo,
   el directorio queda (no se revierte); no contamina el proyecto
   porque es inocuo y util para la siguiente corrida.

2. **Fase 2 — Resolucion de argumentos:** todos los args sin default
   (`--stack`, `--author`, y `--error-type` si el stack resuelto es Rust)
   se preguntan via `input()` si el terminal es interactivo; si
   no-interactivo, aborta listando args faltantes. `--stack` NO tiene
   default — el usuario debe elegirlo explicitamente (CLI flag o prompt).
   `--conftest-mode` tiene default `merge` (solo relevante si el stack
   resuelto es Python).

3. **Fase 3 — Generacion (quasi-atomica) de artefactos:** los artefactos
   se construyen primero en un directorio temporal (`tempfile.mkdtemp`)
   y se mueven al proyecto destino uno por uno via `os.replace` (atomico
   a nivel de archivo individual en POSIX y Windows). Si cualquier paso
   previo al move falla, el directorio temporal se descarta y el proyecto
   destino queda intacto. Si falla un move intermedio, los archivos ya
   movidos se revierten segun el tracking de rollback (sec.S.5.1.2 Fase 4
   describe el protocolo).

   **Nota importante sobre atomicidad:** `shutil.copytree` y `shutil.move`
   NO son atomicos a nivel de arbol de directorios (pueden fallar a mitad
   de camino dejando estado parcial). La atomicidad real es por archivo
   individual (`os.replace`). El rollback cubre la brecha: si fallamos
   en medio, revertimos los archivos ya movidos para preservar la
   invariante todo-o-nada.

   Artefactos generados (7 items):
   - `CLAUDE.local.md` — expansion de la metodologia con author, error_type y
     comandos sec.M.0.1 del stack elegido.
   - `.claude/settings.json` — fusion idempotente via
     `scripts/hooks_installer.py` (si existe, preserva hooks externos no
     conflictivos; nunca pierde configuracion previa del usuario). **Nota
     sobre atomicidad:** para archivos generados ex-nihilo (CLAUDE.local.md,
     plugin.local.md, spec-behavior-base.md) se usa "escribir en temp dir
     + move atomico". Para `settings.json` que requiere merge con contenido
     existente, el patron es: (a) leer el archivo actual del destino, (b)
     computar el nuevo contenido en memoria, (c) escribir a un archivo
     temporal en el MISMO directorio (`.claude/settings.json.tmp.<pid>`),
     (d) `os.replace(tmp, target)` — atomico en POSIX y Windows. Si
     cualquier paso falla, el archivo original queda intacto.
   - `.claude/plugin.local.md` — configuracion del proyecto, sec.4.2 schema.
   - `sbtdd/spec-behavior-base.md` — esqueleto del spec; solo si no existe,
     nunca sobrescribe. **Importante:** el esqueleto usa marcadores
     `<REPLACE: ...>` para placeholders (NO usa `TODO`, `TODOS`, ni `TBD`),
     de modo que `init` genera un archivo que — si el usuario intenta
     `/sbtdd spec` sin completarlo — fallara la precondicion (d) de
     sec.S.5.2 (marcadores `<REPLACE: ...>` detectados) pero no (c). Esto
     deja la regla (c) reservada exclusivamente para detectar pendientes
     que el usuario agrego manualmente.
   - `planning/.gitkeep` — directorio vacio.
   - `.gitignore` — appendea entradas de `templates/gitignore.fragment`
     con dedup (no re-appendear si ya estan).
   - **Reporter TDD-Guard (condicional por stack):**
     - **Rust:** ningun archivo nuevo en el proyecto destino. El reporter
       es `rust_reporter.py` dentro del plugin; `verification_commands[0]`
       lo invoca via `${CLAUDE_PLUGIN_ROOT}`.
     - **Python:** instala `conftest.py` en la raiz del proyecto destino
       segun el modo de `--conftest-mode`. Detalle completo en sec.5.1.3.
     - **C++:** ningun archivo nuevo. El reporter es `ctest_reporter.py`
       dentro del plugin; `verification_commands[1]` lo invoca parseando
       el JUnit XML que emitio `ctest --output-junit`.

4. **Fase 4 — Smoke test post-setup:** verifica que la configuracion
   escrita es funcional (detallado en sec.5.1.2):
   - Parseo OK de `.claude/settings.json` y los 3 hooks TDD-Guard presentes.
   - Parseo OK de `.claude/plugin.local.md` (yaml frontmatter + schema).
   - `tdd-guard` puede escribir en `.claude/tdd-guard/data/` (touch +
     delete de archivo temporal).
   - `git status` responde sin error (proyecto es repo valido).
   Si cualquiera falla, aborta y revierte todo lo generado en Fase 3.

5. **Fase 5 — Reporte al usuario:** resumen con archivos creados, estado
   de cada dependencia verificada, y proximos pasos:

   ```
   [ok] Python 3.11.7
   [ok] git 2.43.0
   [ok] tdd-guard 0.8.2  (data dir writable: .claude/tdd-guard/data/)
   [ok] superpowers plugin  (12 skills discovered)
   [ok] magi plugin v2.1.3
   [ok] Rust toolchain  (cargo 1.81.0, nextest 0.9.86, cargo-audit 0.21,
                         cargo-clippy 0.1.81, cargo-fmt 1.8.0,
                         tdd-guard-rust 0.3.1)
   [ok] git working tree at: D:\proyectos\miapp

   Created:
     CLAUDE.local.md
     .claude/settings.json         (3 hooks: PreToolUse, UserPromptSubmit, SessionStart)
     .claude/plugin.local.md
     sbtdd/spec-behavior-base.md
     planning/.gitkeep
   Appended to .gitignore: CLAUDE.local.md, CLAUDE.md, .claude/

   Next steps:
     1. Edit sbtdd/spec-behavior-base.md with the feature requirements.
     2. Run /sbtdd spec to generate the TDD plan.
   ```

**Postcondiciones:**

- Los 7 criterios de sec.1.3 estan verificados y documentados en el reporte.
- Los archivos listados existen con contenido valido.
- `.gitignore` contiene las entradas esperadas.
- Hooks TDD-Guard activos y el smoke test post-setup paso.

**Errores (con exit codes, ver tabla canonica sec.11.1):**

- **Exit 2 (PRECONDITION_FAILED):** cualquier dependencia de sec.1.3 faltante
  o no operativa. Reporta todas las faltantes en una sola pasada (sec.5.1.1).
- **Exit 4 (FILE_CONFLICT):** `CLAUDE.local.md` preexistente sin `--force`,
  O fallo al mover archivos del dir temporal al proyecto destino. En
  ambos casos el proyecto queda intacto (sin archivos parciales).
- **Exit 5 (SMOKE_TEST_FAILED):** Fase 4 fallo. Rollback aplicado segun
  sec.5.1.2; reporta que check especifico fallo.

**Invariantes:**

- **Todo-o-nada:** si cualquier fase falla, el proyecto destino NO queda
  con archivos parciales. Estado del proyecto tras fallo == estado previo.
- **Re-entrancia:** tras instalar lo faltante, re-ejecutar `/sbtdd init`
  con los mismos args funciona sin artefactos residuales de la corrida
  abortada.
- **Idempotencia con `--force`:** dos corridas exitosas consecutivas con
  mismos args producen archivos byte-identicos.
- NO modifica codigo fuente del proyecto destino, solo metadata bajo
  `.claude/`, `sbtdd/`, `planning/`, mas `CLAUDE.local.md` y appends a
  `.gitignore`.

### 5.1.1 Protocolo de pre-flight check

Implementado en `scripts/dependency_check.py`. Expone una funcion:

```python
def check_environment(stack: Stack) -> DependencyReport:
    """Run all mandatory checks. Accumulate failures; never short-circuit.

    Returns a DependencyReport with per-item status. Caller decides how to
    handle: init aborts on any failure; status subcommand prints but does
    not abort.
    """
```

**Checks ejecutados en orden (pero ninguno aborta; se acumulan):**

| Check | Metodo |
|-------|--------|
| Python runtime | `sys.version_info >= (3, 9)` |
| git binary | `shutil.which("git")` → `subprocess.run(["git", "--version"], timeout=5)` |
| tdd-guard binary | `shutil.which("tdd-guard")` → `subprocess.run(["tdd-guard", "--version"], timeout=5)` |
| tdd-guard writable data dir | Crea `.claude/tdd-guard/data/` + touch/delete de archivo temporal |
| superpowers plugin | Probe `~/.claude/plugins/cache/**/superpowers/**/skills/{brainstorming,writing-plans,test-driven-development,verification-before-completion,requesting-code-review,receiving-code-review,executing-plans,subagent-driven-development,dispatching-parallel-agents,systematic-debugging,using-git-worktrees,finishing-a-development-branch}/SKILL.md` — las 12 skills deben estar |
| magi plugin | Probe `~/.claude/plugins/cache/**/magi/**/skills/magi/{SKILL.md,scripts/run_magi.py}` — ambos archivos deben estar |
| Stack toolchain (Rust) | `cargo --version`, `cargo nextest --version`, `cargo audit --version`, `cargo clippy --version`, `cargo fmt --version`, `tdd-guard-rust --version` (obligatorio — sin el, el reporter Rust no funciona) |
| Stack toolchain (Python) | `python --version`, `pytest --version`, `ruff --version`, `mypy --version` (el conftest.py reporter no requiere binarios extras; verifica ademas que pytest puede cargar hooks con `python -c "import pytest"`) |
| Stack toolchain (C++) | `cmake --version`, `ctest --version` (DEBE soportar `--output-junit`; se verifica con `ctest --help \| grep -- --output-junit`. Si falla, mensaje: "ctest too old — v3.21+ required for JUnit output") |
| Working tree | `.git/` existe. Si no esta presente, el check falla; `init` NO ejecuta `git init` (el usuario debe hacerlo manualmente antes de reintentar) |

**Reporte estructurado en caso de fallo (formato canonico):**

```
SBTDD init: environment check FAILED.

The following dependencies are missing or not operational. Install all of
them and re-run /sbtdd init:

  [MISSING]  tdd-guard
             Binary not found in PATH.
             Install: npm install -g @nizos/tdd-guard
             Docs:    https://github.com/nizos/tdd-guard

  [MISSING]  magi plugin
             Plugin not discoverable under ~/.claude/plugins/.
             Install: /plugin marketplace add BolivarTech/magi
                      /plugin install magi@bolivartech-plugins

  [BROKEN]   tdd-guard data directory
             .claude/tdd-guard/data/ is not writable.
             Check filesystem permissions on the project directory.

  [MISSING]  cargo-nextest
             Binary not found in PATH.
             Install: cargo install cargo-nextest --locked

3 issues found. /sbtdd init aborted. Exit code 2.
No files were created in the project.
```

Reglas del reporte:

- Cada item: severidad (`MISSING` | `BROKEN`), nombre, descripcion, accion
  de remediacion con URL si aplica.
- El reporte lista **todos** los items fallidos, no solo el primero.
- Termina con el conteo total y la afirmacion de que no se creo nada.
- Exit code 2 (PreconditionError).

### 5.1.2 Protocolo de smoke test post-setup

Tras Fase 3 (archivos generados en el proyecto destino), Fase 4 verifica
que el entorno quedo operativo:

| Check | Metodo | Fallo → |
|-------|--------|---------|
| `settings.json` parseable | `json.load(...)` | Rollback + exit 5 |
| 3 hooks presentes | Los paths `hooks.PreToolUse[*]`, `hooks.UserPromptSubmit[*]`, `hooks.SessionStart[*]` existen y cada uno contiene al menos un entry con `command: "tdd-guard"` | Rollback + exit 5 |
| `plugin.local.md` parseable | Parser YAML + validacion de schema sec.4.2 | Rollback + exit 5 |
| tdd-guard data dir escribible | Touch + delete de archivo temporal en `.claude/tdd-guard/data/` | Rollback + exit 5 |
| git responde | `git status --short` retorna exit 0 | Rollback + exit 5 |
| `CLAUDE.local.md` no vacio + header presente | Abre y verifica que contiene `{Author}` resuelto, no el placeholder literal | Rollback + exit 5 |
| Reporter TDD-Guard operativo | Genera un test dummy que falla (contenido: una sola assertion `assert False` o equivalente en el stack), ejecuta **la secuencia de `verification_commands` necesaria para producir `test.json`** — stack-dependiente: Rust ejecuta `[0]` (rust_reporter); Python ejecuta `[0]` (pytest con conftest); C++ ejecuta `[0]` y `[1]` en orden (ctest JUnit XML + ctest_reporter). Verifica que `.claude/tdd-guard/data/test.json` existe y parsea como JSON valido con los campos requeridos del schema TDD-Guard (`testModules`, `reason`). El test dummy se elimina antes de marcar exito | Rollback + exit 5 |

**Rollback:** el tracking de archivos creados en Fase 3 se mantiene en
memoria durante la ejecucion del subcomando. En caso de fallo de Fase 4:

1. Los archivos creados en Fase 3 se borran (reverse order).
2. Los appends a `.gitignore` se revierten eliminando exactamente las
   lineas appendeadas (no el archivo entero).
3. En el caso especifico de `--stack python` con `--conftest-mode merge`,
   el bloque SBTDD appendeado al `conftest.py` del usuario (delimitado por
   los marcadores `# --- SBTDD TDD-Guard reporter START/END ---`) se
   elimina del archivo; el resto del contenido queda intacto.
4. Si una operacion de rollback falla, se reporta pero no se re-intenta
   — el usuario debe limpiar manualmente con instrucciones especificas.

### 5.1.3 Instalacion del reporter Python (`conftest.py`)

Solo aplica a `init --stack python`. El reporter es un `conftest.py` con
pytest hooks (`pytest_sessionstart`, `pytest_sessionfinish`,
`pytest_runtest_makereport`) que captura resultados de tests y escribe
`.claude/tdd-guard/data/test.json` en el formato TDD-Guard (ver
`scripts/reporters/tdd_guard_schema.py`).

`templates/conftest.py.template` contiene el bloque de hooks delimitado
por marcadores:

```python
# --- SBTDD TDD-Guard reporter START ---
# (hooks pytest que escriben .claude/tdd-guard/data/test.json)
...
# --- SBTDD TDD-Guard reporter END ---
```

**Flag `--conftest-mode`:**

| Modo | Si existe `conftest.py` en raiz del destino | Si no existe |
|------|---------------------------------------------|--------------|
| `merge` (default) | Appendea el bloque marcado al archivo existente. Re-ejecutar `init --force --conftest-mode merge` reemplaza **solo** el bloque delimitado por los marcadores (busqueda + substitucion idempotente). No toca el resto del archivo del usuario | Escribe el conftest completo (el template entero) |
| `replace` | Renombra el existente a `conftest.py.bak.YYYYMMDD-HHMMSS` y escribe el del plugin | Escribe el conftest |
| `skip` | No instala archivo; imprime el contenido requerido a stdout para copy-paste manual. Smoke test (sec.5.1.2) valida que los hooks esten presentes en el `conftest.py` del usuario (busca los nombres de las funciones hook: `pytest_sessionfinish` + marcador `SBTDD TDD-Guard reporter`). Si no estan, rollback + exit 5 | Igual — imprime y valida |

**Invariantes:**

- **Idempotencia bajo `merge`:** dos corridas consecutivas con
  `init --force --conftest-mode merge` producen el `conftest.py` byte a
  byte identico. Los marcadores delimitan exactamente el bloque
  reemplazable.
- **Colision de nombres de hooks:** si el usuario ya define
  `pytest_sessionfinish` (u otro hook que el reporter agrega) fuera del
  bloque marcado, pytest usara solo una version y los tests podrian no
  reportar a TDD-Guard. El smoke test (sec.5.1.2) lo detecta al ejecutar el
  test dummy y no encontrar `test.json` generado. Recovery sugerido: el
  usuario integra los hooks manualmente (modo `skip`), o renombra sus
  hooks, o usa `replace` si acepta perder sus hooks previos.
- **Localizacion:** el `conftest.py` va en la **raiz del proyecto destino**.
  Pytest lo auto-descubre desde cualquier subdirectorio de tests. No se
  instala en `tests/` porque proyectos con multiples directorios de tests
  quedan no cubiertos.

### 5.2 `spec`

**Trigger:** `/sbtdd spec` tras editar `sbtdd/spec-behavior-base.md`.

**Argumentos:** ninguno (todo se lee de plugin.local.md).

**Precondiciones:**

- `sbtdd/spec-behavior-base.md` existe y tiene contenido **completo y
  especificado** (no-esqueleto, sin marcadores pendientes). Validacion
  aplicada por `scripts/spec_cmd.py` antes de invocar `/brainstorming`
  — las 4 condiciones deben cumplirse simultaneamente; si alguna falla,
  aborta con exit 2 (PRECONDITION_FAILED):

  | # | Regla | Criterio |
  |---|-------|----------|
  | a | Tamano minimo | Archivo contiene >= 200 caracteres excluyendo whitespace |
  | b | Contenido real bajo cada heading | No consiste unicamente en headers de seccion sin texto debajo (detectado: numero de lineas con contenido no-heading debe ser > 2x el numero de lineas heading) |
  | c | **Sin marcadores pendientes (REGLA DURA):** el archivo NO debe contener ninguna de estas cadenas en mayusculas, como palabras completas (word boundary): **`TODO`**, **`TODOS`**, **`TBD`** (To Be Determined). Regex: `\bTODO\b\|\bTODOS\b\|\bTBD\b` con match **case-sensitive** (solo uppercase). Minusculas estan permitidas — "todos los usuarios" en un escenario BDD escrito en espanol NO es marcador, es prosa legitima. **Motivacion:** la presencia de cualquier marcador TODO/TODOS/TBD en la spec-base significa que el usuario dejo requerimientos sin especificar; ejecutar `/brainstorming` sobre una spec incompleta produce un plan TDD con huecos que MAGI tendra que tapar o rechazar. Es mas economico detectarlo antes que iterar MAGI sobre spec rota | |
  | d | No marcadores del esqueleto literal | El archivo NO contiene las cadenas exactas que genero `init` como placeholders (p.ej. `<REPLACE: describir objetivo>`, `<REPLACE: escenarios BDD>`) — la lista completa esta en `templates/spec-behavior-base.md.template`. Esto cubre el caso donde el usuario dejo placeholders intactos sin usar los tokens prohibidos por (c) |

  **Mensaje de error cuando (c) falla:** el subcomando imprime las lineas
  especificas con los marcadores detectados y su numero de linea, p.ej.:

  ```
  spec-behavior-base.md contiene marcadores pendientes (regla c):

    line 12: "- TODO: definir timeout maximo"
    line 34: "  Respuesta: TBD"
    line 58: "TODOS: los edge cases"

  Completa esos puntos con el contenido real antes de re-ejecutar /sbtdd spec.
  Exit code 2 (PRECONDITION_FAILED).
  ```

- Plugins `superpowers` y `magi` se asumen disponibles (garantia de
  `init` via sec.S.1.3). NO se re-verifican aqui — ver sec.S.5.9 "Politica
  de re-verificacion" para el racional.

**Comportamiento:** implementa sec.1 "Flujo de especificacion" de la metodologia.

1. Invoca `/brainstorming` via `scripts/superpowers_dispatch.py`, pasandole
   `sbtdd/spec-behavior-base.md` como input. Espera que se genere
   `sbtdd/spec-behavior.md`.
2. Verifica que el archivo se genero. Si no, aborta con el error del skill.
3. Invoca `/writing-plans` pasandole `sbtdd/spec-behavior.md`. Espera que
   se genere `planning/claude-plan-tdd-org.md`.
4. Presenta el plan al usuario para revision manual (Checkpoint 1). Si
   rechaza, vuelve al paso 3.
5. Inicia loop MAGI (Checkpoint 2):
   a. Invoca `/magi:magi` via `scripts/magi_dispatch.py` con ambos archivos.
   b. Parsea veredicto + flag `degraded` + *Conditions for Approval*.
   c. **Short-circuit STRONG_NO_GO:** si `verdict == STRONG_NO_GO`
      (full o degraded), **aborta con exit 8** (MAGI_GATE_BLOCKED,
      sec.S.11.1) y escala al usuario sugiriendo refinar
      `sbtdd/spec-behavior-base.md` (el plan tiene problemas
      estructurales que los agentes detectaron; continuar iterando
      no resuelve un NO-GO claro). Aplica antes de cualquier otro
      gate.
   d. **Pre-gate INV-28 (degraded, si no STRONG_NO_GO):** si
      `verdict.degraded == true`, aplica conditions segun (e) pero
      **NO cuenta como salida**; re-invoca MAGI al final de esta
      iteracion esperando full 3-agent consensus.
   e. El agente aplica las conditions reescribiendo
      `planning/claude-plan-tdd.md` a partir de `claude-plan-tdd-org.md`.
   f. Si veredicto >= `magi_threshold` **Y no-degraded**, sale del loop.
   g. Si inferior o degraded, incrementa contador. Si >
      `magi_max_iterations`, **aborta con exit 8** (MAGI_GATE_BLOCKED)
      — MAGI no converge a full consensus dentro del presupuesto;
      sugerir refinar `sbtdd/spec-behavior-base.md` antes de re-ejecutar.
6. Pide confirmacion explicita del usuario. Al aceptar, **`spec` crea
   `.claude/session-state.json` inicializado** con los siguientes valores
   (este es el unico punto donde el state file se crea; los demas
   subcomandos lo leen/actualizan pero no lo crean):

   | Campo | Valor inicial |
   |-------|---------------|
   | `plan_path` | `"planning/claude-plan-tdd.md"` |
   | `current_task_id` | id de la primera tarea `[ ]` del plan |
   | `current_task_title` | titulo legible de esa tarea |
   | `current_phase` | `"red"` (toda tarea arranca en Red) |
   | `phase_started_at_commit` | SHA del HEAD al momento de aprobacion |
   | `last_verification_at` | `null` |
   | `last_verification_result` | `null` |
   | `plan_approved_at` | timestamp ISO 8601 actual |

   Si ya existia un state file (corrida previa de otro feature), se
   archiva como `.claude/session-state.json.bak.<timestamp>` antes de
   crear el nuevo. Esto ocurre solo si el state file previo tiene
   `current_phase: "done"` (feature anterior cerrado); si tiene otro
   valor, `spec` aborta con exit 2 (PRECONDITION_FAILED) indicando que
   hay un feature en progreso sin finalizar.

   **Limpieza de runtime artifacts del feature anterior:** al crear el
   nuevo state file, `spec` tambien archiva los siguientes artefactos
   residuales del feature previo para evitar que contaminen el nuevo
   ciclo (archiving siempre activo; no hay flag para desactivarlo):

   - `.claude/magi-verdict.json` → `.claude/magi-verdict.json.bak.<timestamp>`
   - `.claude/auto-run.json` → `.claude/auto-run.json.bak.<timestamp>`

   **Por que es critico:** sin esta limpieza, `finalize` del nuevo feature
   podria leer el `magi-verdict.json` del feature anterior y pasar el
   gate MAGI sin haber ejecutado `pre-merge` en el nuevo ciclo. Misma
   logica para `auto-run.json` — pertenece a la corrida especifica que
   lo produjo. El archiving los preserva por si el usuario quiere
   auditar corridas pasadas; el siguiente feature parte limpio.

**Postcondiciones:**

- `sbtdd/spec-behavior.md`, `planning/claude-plan-tdd-org.md`,
  `planning/claude-plan-tdd.md` existen.
- `.claude/session-state.json` existe con los 8 campos del schema sec.9.1
  inicializados. `plan_approved_at` no es `null`.

**Invariantes:**

- Nunca sobrescribe `spec-behavior-base.md`.
- `claude-plan-tdd-org.md` no se modifica tras generacion (preservado como
  referencia pre-MAGI).
- `claude-plan-tdd.md` solo se escribe tras recibir veredicto MAGI.

### 5.3 `close-phase`

**Trigger:** `/sbtdd close-phase [--message "..."]`.

**Argumentos:**

| Arg | Tipo | Default | Descripcion |
|-----|------|---------|-------------|
| `--message` | string | pregunta | Mensaje del commit (sin prefijo) |
| `--variant` | `feat \| fix` | pregunta si Green | Aplicable solo a Green |

**Precondiciones:**

- `.claude/session-state.json` existe y es valido segun el schema de
  sec.S.9.1 (spec).
- Hay cambios sin commitear en el working tree.
- `planning/claude-plan-tdd.md` existe y esta aprobado (`plan_approved_at`
  != null en state file).

**Comportamiento:** implementa sec.3 "Verificacion y cierre atomico de cada
fase" de la metodologia (3 pasos no-negociables), precedido por un paso 0
de drift check (sec.S.9.2 "Orden de autoridad").

0. **Paso 0 — Drift check:** invoca `detect_drift` (sec.S.9.2) antes de
   cualquier lectura o mutacion. Si retorna no-None, aborta con exit 3
   (DRIFT_DETECTED) reportando los 3 valores enfrentados (state file, git
   HEAD, plan). `close-phase` NO intenta reconciliar drift automaticamente
   — la recuperacion es manual del usuario.

1. **Paso 1 — Verificacion:**
   a. Lee `current_phase` del state file via `scripts/state_file.py`.
   b. Invoca `/verification-before-completion`, pasandole los comandos sec.M.0.1
      de la metodologia (leidos de `verification_commands` en
      `plugin.local.md`).
   c. Si falla: aborta con exit 1 (USER_ERROR, sec.11.1), NO commitea,
      reporta evidencia literal del fallo (INV-16). El usuario arregla y
      re-invoca `close-phase`.

2. **Paso 2 — Commit atomico:**
   a. Elige prefijo segun `current_phase` y `commit_prefix_map`.
   b. Crea commit con mensaje `{prefix}: {user_message}` via
      `scripts/commits.py`.
   c. Verifica que `git status` queda limpio tras el commit. Si no, aborta.

3. **Paso 3 — Actualizar state file:**
   a. Actualiza `phase_started_at_commit` al SHA recien creado.
   b. Actualiza `last_verification_at` y `last_verification_result`.
   c. **Transicion de `current_phase` (dos casos mutuamente exclusivos):**
      - Si la fase cerrada fue `red` o `green`: avanza `current_phase` al
        siguiente valor del ciclo (`red → green`, `green → refactor`).
        Termina el subcomando.
      - Si la fase cerrada fue `refactor`: **NO avanza `current_phase`
        aqui** (queda en `refactor`). Delega toda la transicion de cierre
        de tarea a `close-task`, que se invoca inmediatamente a
        continuacion. `close-task` es el unico responsable de mover
        `current_phase` fuera de `refactor` (a `red` de la proxima tarea,
        o a `done` si era la ultima).
   d. **Caso especial refactor cerrado:** invoca internamente `close-task`
      (ver sec.5.4). Esta invocacion es parte atomica de `close-phase` — si
      `close-task` falla, `close-phase` reporta el fallo y el estado queda
      con el commit `refactor:` creado pero la tarea sin marcar `[x]`, lo
      que `status` detecta como drift y el usuario puede retomar
      re-invocando `/sbtdd close-task` manualmente.

**Postcondiciones:**

- Un commit nuevo en HEAD con prefijo correcto.
- State file actualizado consistente con el commit (drift = 0).
- Si fase era refactor: tarea cerrada segun sec.5.4.

**Invariantes:**

- Si el commit se crea, el state file se actualiza. Si alguno falla, el
  otro se revierte (mejor esfuerzo — si revert del state file falla,
  reporta drift al usuario via stderr).
- Nunca mezcla cambios de fases distintas en el commit.

### 5.4 `close-task`

**Trigger:** interno, invocado por `close-phase` cuando fase cerrada es
`refactor`. PUEDE invocarse manualmente tras recovery.

**Argumentos:** ninguno.

**Precondiciones:**

- State file tiene `current_phase: "refactor"`. Este es el unico estado
  valido: `close-phase` invoca `close-task` SIN haber avanzado la fase
  (ver sec.5.3 paso 3c). Si `current_phase` es otro valor, `close-task`
  aborta con `PreconditionError` y mensaje de drift.
- Ultimo commit tiene prefijo `refactor:` (el commit que `close-phase`
  acaba de crear).
- `current_task_id` referencia tarea existente en el plan.

**Comportamiento:** implementa sec.M.2.3 "Al cerrar tarea completa" y
sec.M.2.3 "Al cerrar el plan" de la metodologia, precedido por drift
check (sec.S.9.2).

0. **Paso 0 — Drift check:** invoca `detect_drift` (sec.S.9.2). Si
   retorna no-None, aborta con exit 3. Relevante especialmente cuando
   `close-task` se invoca manualmente tras recovery (ver Trigger); en
   la invocacion interna desde `close-phase`, el drift check de
   `close-phase` ya paso, asi que este es idempotente y rapido — pero
   se mantiene por defensa en profundidad.

1. Marca `[x]` en el checkbox de la tarea `current_task_id` en el plan.
2. Crea commit `chore: mark task {current_task_id} complete` conteniendo
   solo la edicion del plan.
3. Busca proximo `[ ]`:
   - Existe: avanza `current_task_id` / `current_task_title`, setea
     `current_phase: "red"`.
   - No existe: protocolo "Al cerrar el plan" — null + `current_phase:
     "done"`. Notifica al usuario.

**Invariantes:**

- El commit `chore:` contiene EXCLUSIVAMENTE la edicion del checkbox.

### 5.5 `status`

**Trigger:** `/sbtdd status` en cualquier momento.

**Argumentos:** ninguno.

**Precondiciones:** ninguna (read-only).

**Comportamiento:**

1. Lee `.claude/session-state.json` si existe.
2. Lee ultimo commit (`git log -1 --format="%h %s"`).
3. Cuenta tareas pendientes/completadas en el plan.
4. Detecta drift (sec.M.2.1 "Orden de autoridad") via `scripts/drift.py`.
5. Imprime reporte estructurado a stdout:

   ```
   Tarea activa:    {current_task_id} — {current_task_title}
   Fase activa:     {current_phase}
   Ultimo commit:   {sha} {prefijo}: {mensaje}
   Plan:            {completed}/{total} tareas [x]
   Ultima verif:    {last_verification_at} — {last_verification_result}
   Drift:           {none | detected: {descripcion}}
   ```

**Errores (con exit codes, ver sec.11.1):**

- **Exit 0 (SUCCESS):** reporte impreso limpio, sin drift detectado.
- **Exit 3 (DRIFT_DETECTED):** se detecto discrepancia entre state file,
  git HEAD y plan. El reporte incluye la linea "Drift: detected: {descripcion}"
  y stdout lista los valores enfrentados. Util para CI: un wrapper puede
  abortar si `status` retorna 3.
- **Exit 1 (USER_ERROR):** state file existe pero es JSON invalido (parseo
  fallo). La regeneracion es manual; `status` no auto-recupera.

**Invariantes:** solo lectura. Nunca escribe. Emite exit 3 SIN escalar ni
pedir confirmacion — es pura funcion de diagnostico; la accion correctiva
queda a criterio del usuario.

### 5.6 `pre-merge`

**Trigger:** `/sbtdd pre-merge` cuando `current_phase: "done"`.

**Argumentos:**

| Arg | Tipo | Default | Descripcion |
|-----|------|---------|-------------|
| `--magi-threshold` | string | de config | Override del umbral (solo puede ELEVAR el umbral minimo, nunca bajarlo; p.ej. pasar `GO` si config dice `GO_WITH_CAVEATS` es valido, pero `HOLD` no) |

**Precondiciones:**

- State file: `current_phase: "done"`.
- Todas las tareas `[x]` en el plan.
- sec.M.0.1 pasa limpio (re-verifica al inicio).
- `git status` limpio respecto al alcance del plan.

**Comportamiento:** implementa sec.6 "Pre-merge: revisiones obligatorias",
dos loops secuenciales independientes, precedido por drift check.

0. **Paso 0 — Drift check:** invoca `detect_drift` (sec.S.9.2). Si
   retorna no-None, aborta con exit 3 antes de iniciar los loops. Aunque
   en este punto el state file deberia estar en `current_phase: "done"`
   (precondicion), el drift check valida coherencia entre state, git y
   plan completos.

1. **Pre-check:** sec.M.0.1 + `git status`. Aborta si falla.

2. **Loop 1 — `/requesting-code-review`:**
   a. Invoca el skill sobre el diff acumulado.
   b. Si clean-to-go: sale del Loop 1.
   c. Si findings: invoca `/receiving-code-review`, aplica fixes via
      mini-ciclos TDD (`test:` → `fix:` → `refactor:`, cada uno cerrado
      con verificacion). `[INFO]` diferidos se loggean, no aplican.
   d. Re-invoca hasta clean-to-go. **Safety valve duro: 10 iteraciones
      maximo** (mismo cap que en `auto`, hardcoded no configurable, ver
      INV-11 en sec.S.10.3). Si se alcanza, aborta con exit 7
      (LOOP1_DIVERGENT, sec.S.11.1) — indica bug del skill o divergencia
      severa spec/plan; requiere investigacion manual. En la practica
      Loop 1 converge en 1-3 iteraciones sobre codigo sano.

3. **Loop 2 — `/magi:magi`:**
   a. Invoca sobre diff limpio, pasando como contexto el historial de
      rechazos de iteraciones previas del Loop 2 actual (formato de
      INV-29). En la primera iteracion, el historial esta vacio.

   b. **Short-circuit STRONG_NO_GO:** si `verdict == STRONG_NO_GO`
      (full o degraded), abortar inmediatamente con exit 8 (requiere
      replan). Esta regla aplica ANTES que cualquier otro gate — un
      NO-GO claro no necesita receiving-code-review ni re-iteracion.

   c. **Pre-gate INV-28 — chequeo de degraded (solo si verdict !=
      STRONG_NO_GO):** si el output de MAGI tiene `degraded: true`, el
      veredicto **no cuenta como senal de salida**. Se continua al
      paso (d) para aplicar findings via INV-29, pero al final de esta
      iteracion se re-invoca MAGI esperando full 3-agent consensus,
      incluso si el veredicto degradado supera `magi_threshold`.

   d. **Pre-gate INV-29 — evaluacion tecnica de findings:** si el
      veredicto implica cambios (GO_WITH_CAVEATS / HOLD / HOLD_TIE),
      invocar `/receiving-code-review` sobre las Conditions for
      Approval de MAGI. El skill retorna una clasificacion por finding:
      aceptada, rechazada, o (solo en interactivo) ambigua que el
      usuario resuelve. Registrar titulo + razon de cada rechazo en
      el historial de rechazos de la iteracion actual (para feedback
      en la proxima, ver paso (a) de la siguiente iteracion).

   e. Interpretar veredicto aplicando el filtro de INV-28/29:
      - `STRONG_GO` / `GO` full (no degraded): sale.
      - `STRONG_GO` / `GO` degraded: re-invoca MAGI (INV-28), consume
        iteracion.
      - `GO_WITH_CAVEATS` (full o degraded): aplica findings aceptadas
        por INV-29 via mini-ciclo TDD. **Salida vs re-invocacion:**
        - Si MAGI era full Y todas las findings aceptadas eran bajo
          riesgo (doc/tests/naming/logging/msgs/comentarios): sale
          sin re-evaluar.
        - Si MAGI era degraded, O habia findings estructurales
          (firmas/contratos/comportamiento/capas), O alguna finding
          fue rechazada por INV-29: re-invoca MAGI.
      - `HOLD` / `HOLD_TIE`: aplica findings aceptadas, re-invoca MAGI.
      - (`STRONG_NO_GO` no llega aqui — ya abortado en paso (b).)

   f. Si umbral usuario > `GO_WITH_CAVEATS`, aplica ese umbral al
      paso (e) — `GO_WITH_CAVEATS` ya no basta para salir.
   g. Si > `magi_max_iterations` sin convergencia: detiene con exit 8,
      escala con posibles causas de la metodologia sec.6 incluyendo
      "iteraciones consumidas por degraded MAGI" o "findings
      rechazadas repetidamente por `/receiving-code-review`" como
      diagnostico especifico si aplica.

4. **Salida exitosa:** registra veredicto MAGI en
   `.claude/magi-verdict.json` con los campos: `timestamp`, `verdict`,
   `conditions`, y **`degraded`** (propagado del output de MAGI — ver
   INV-28; necesario para que `finalize` rechace veredictos degraded
   como gate no-aprobado). Sugiere `finalize` al usuario.

**Postcondiciones:**

- Ambos loops pasados.
- Commits del mini-ciclo de fix presentes, atomicos.
- Veredicto MAGI registrado.

**Invariantes:**

- Loop 2 NUNCA arranca antes de clean-to-go de Loop 1.
- Commits mini-ciclo atomicos uno por uno (no batch).

### 5.7 `finalize`

**Trigger:** `/sbtdd finalize` tras `pre-merge` exitoso.

**Argumentos:** ninguno.

**Comportamiento:** implementa checklist sec.7 de la metodologia.

1. Verifica cada item:
   - [ ] Tareas del plan todas `[x]`.
   - [ ] State file: `null` + `"done"`.
   - [ ] sec.M.0.1 limpio.
   - [ ] `git status` limpio respecto al plan.
   - [ ] Spec + plan reflejan estado final.
   - [ ] Loop 1 clean-to-go registrado.
   - [ ] Gate MAGI aprobado (lee `.claude/magi-verdict.json`).
   - [ ] Commits siguen convenciones sec.5 (spot-check prefijos).
   - [ ] `CLAUDE.md` actualizado si aplica (recordatorio, no enforcement).
2. Si item falla, reporta cual y detiene.
3. Si todos pasan, invoca `/finishing-a-development-branch`.

**Errores (con exit codes, ver sec.S.11.1):**

- **Exit 0 (SUCCESS):** checklist completo pasa y se invoca
  `/finishing-a-development-branch` sin errores.
- **Exit 2 (PRECONDITION_FAILED) — precondiciones de existencia:** state
  file ausente, `current_phase` no es `"done"`, `.claude/magi-verdict.json`
  ausente (pre-merge/auto no corrio), o **veredicto MAGI pertenece a
  feature anterior** (defensa contra residuo: `finalize` compara el
  timestamp de `magi-verdict.json.mtime` vs `state_file.plan_approved_at`;
  si el verdict es anterior al plan_approved_at, lo trata como residuo
  — pre-merge del feature actual NO corrio — y aborta). La limpieza
  principal ocurre en `spec` (ver sec.S.5.2), estos checks son defensa
  en profundidad.
- **Exit 9 (CHECKLIST_FAILED) — checklist items fallan:** uno o mas
  items del checklist sec.M.7 no pasan. Incluye explicitamente:
  - tareas incompletas,
  - `git status` sucio,
  - **veredicto MAGI por debajo del umbral** (label no alcanza
    `magi_threshold`),
  - **veredicto MAGI con `degraded: true`** (INV-28, sec.S.10.3): el
    item "Gate MAGI aprobado" del checklist exige verdict >= threshold
    **Y** `degraded: false`. Un verdict degraded cuenta como gate
    no-aprobado aunque el label supere threshold — consenso parcial
    no satisface el gate de calidad final. Mensaje sugiere re-ejecutar
    `pre-merge` o `auto` hasta obtener full 3-agent consensus.
  - prefijos de commit invalidos,
  - etc.
  El reporte enumera exactamente que items fallaron. Consistente con
  `auto` Fase 4 (sec.S.5.8) que tambien mapea fallos del gate MAGI
  (umbral o degraded) a exit 9.

**Invariantes:**

- Nunca ejecuta merge / PR por si mismo — delega al skill.
- Nunca fuerza push.

### 5.8 `auto` (modo shoot-and-forget)

**Trigger:** `/sbtdd auto` tras un `/sbtdd spec` exitoso (plan aprobado).

Ejecuta el ciclo completo de creacion del feature **sin intervencion humana
en ningun punto**: ejecucion de todas las tareas del plan, ambos loops
pre-merge, y validacion del checklist sec.7. Delega la calidad del codigo
entregado a sec.6 (Code review) y sec.7 (Finalizacion) de la metodologia, con presupuesto
MAGI elevado para absorber la falta de juicio humano interactivo.

**Argumentos:**

| Arg | Tipo | Default | Descripcion |
|-----|------|---------|-------------|
| `--magi-max-iterations` | int | de config (`auto_magi_max_iterations`, default 5) | Override del safety valve MAGI para esta corrida |
| `--magi-threshold` | string | de config (`magi_threshold`, default `GO_WITH_CAVEATS`) | Override del umbral MAGI para esta corrida (misma semantica que en pre-merge: solo puede ELEVAR el umbral minimo, nunca bajarlo). Util cuando se quiere un gate mas estricto en una corrida autonoma especifica |
| `--verification-retries` | int | de config (`auto_verification_retries`, default 1) | Reintentos al fallar verificacion de fase |
| `--dry-run` | flag | false | Imprime el plan de ejecucion sin ejecutar |

**Precondiciones:**

- `.claude/session-state.json` existe, es valido, y tiene `plan_approved_at != null`.
- sec.M.0.1 pasa limpio en el estado actual (auto NO rescata de un punto de partida roto).
- `git status` limpio respecto al alcance del plan.
- Las 7 dependencias de sec.1.3 siguen operativas (auto re-ejecuta el
  pre-flight check completo de sec.5.1.1 al iniciar — ver Fase 1a).
- Si `worktree_policy: required` en `plugin.local.md` y el directorio
  actual no es una worktree dedicada, aborta.
- `tdd_guard_enabled: true` (auto no desactiva TDD-Guard — ver invariantes).

**Comportamiento — cinco fases estrictamente secuenciales:**

1. **Fase 1 — Pre-flight check ampliado:**
   a. Re-ejecuta `dependency_check.check_environment()` — aborta si el
      entorno degrado desde `init`.
   b. Valida precondiciones de arriba.
   c. Imprime el plan de ejecucion: N tareas pendientes, fase activa,
      presupuesto MAGI, timestamp de inicio. **Si `--dry-run`, termina
      aqui con exit 0 SIN escribir nada al proyecto destino** (la Fase 1
      es puramente de lectura hasta este punto).
   d. Solo si NO es `--dry-run`: anota `auto_started_at` (ISO 8601) en
      `.claude/auto-run.json` para trazabilidad. Este es el primer
      side effect del subcomando.

2. **Fase 2 — Bucle de ejecucion de tareas** (si `current_phase != "done"`):

   Antes de entrar al bucle, se invoca `detect_drift` (sec.S.9.2); si
   retorna no-None, aborta con exit 3 (DRIFT_DETECTED). El bucle asume
   que el state file es autoridad del presente (INV-3).

   Para cada tarea desde `current_task_id` hasta la ultima `[ ]` del plan,
   **secuencialmente** (sin paralelismo, independiente de `addBlockedBy`):

   **Punto de entrada al inner loop de fases (crucial para retomar
   correctamente):**

   - Para la **primera tarea del bucle** (la que apunta `current_task_id`
     al iniciar auto), el inner loop empieza en la fase indicada por
     `current_phase` del state file, no siempre en Red. Esto permite
     retomar una tarea en progreso respetando INV-3 (p.ej. si
     `current_phase: "green"`, salta Red y empieza en Green).
   - Para **cada tarea subsiguiente** (las que llegan por avance via
     `close-task`), el inner loop siempre empieza en Red — `close-task`
     ya dejo `current_phase: "red"` al avanzar el `current_task_id`.

   Para cada fase desde el punto de entrada hasta Refactor (orden fijo
   Red → Green → Refactor, saltando las fases que ya pasaron segun
   `current_phase`):

   a. Invoca `/test-driven-development` para disciplinar la fase.
   b. **Verifica trabajo existente:** si hay cambios sin commitear en el
      working tree consistentes con la fase actual, saltar a (c) sin
      re-escribir. Si no hay cambios, el agente escribe el codigo
      correspondiente (tests en Red, impl minima en Green, limpieza en
      Refactor).
   c. Invoca `/verification-before-completion` con los comandos de sec.M.0.1.
   d. Si falla:
      - Invoca `/systematic-debugging` para diagnosticar causa raiz.
      - El agente aplica el fix segun el diagnostico.
      - Re-invoca `/verification-before-completion`.
      - Reintenta hasta `auto_verification_retries` veces. Si al agotar
        los reintentos la verificacion sigue fallando, **aborta con exit
        6** (falla de verificacion irremediable en auto).
   e. Si pasa: ejecuta logica de `close-phase` (commit atomico + update
      state file).

   Tras Refactor cerrado de cada tarea, ejecuta logica de `close-task`
   (marca `[x]` + commit `chore:` + avance).

   Al terminar la ultima tarea, `current_phase` queda en `"done"`.

3. **Fase 3 — Pre-merge con presupuesto elevado:**

   Reutiliza la logica de `pre_merge_cmd.py` con `magi_max_iterations`
   override:

   a. **Loop 1 (`/requesting-code-review`):** itera aplicando mini-ciclos
      TDD (`test:` → `fix:` → `refactor:`) para cada finding `[CRITICAL]`
      y `[WARNING]`. Los `[INFO]` se defierren con justificacion en el log
      de auto. Continua hasta *clean-to-go*. Loop 1 converge por
      naturaleza (cada iteracion reduce findings mecanicos); para cubrir
      casos patologicos (bug del skill, divergencia severa de spec/plan)
      existe un safety valve duro de **10 iteraciones maximo**. Si lo
      alcanza, aborta con exit 7 e instruye al usuario a investigar
      manualmente.
   b. **Loop 2 (`/magi:magi`):** itera con `--magi-max-iterations` (5
      por default). Aplica INV-28 (degraded no sale) + INV-29
      (receiving-code-review gate + feedback) como en `pre-merge`
      (sec.S.5.6 paso 3), con las siguientes especificidades de auto:

      - **Contexto de feedback a MAGI** (sec.S.10.3 INV-29): al
        invocar `/magi:magi` en iteraciones N>1, se pasa el historial
        de rechazos acumulado de las ultimas 3 iteraciones de este
        Loop 2. El historial se persiste en `.claude/auto-run.json`
        con campo `rejection_history_passed_to_magi` para auditoria
        post-mortem (ver esquema de auto-run.json).
      - **Short-circuit STRONG_NO_GO:** si `verdict == STRONG_NO_GO`
        (full o degraded), abortar inmediatamente con exit 8 (auto
        no replannea — el problema es estructural). Aplica antes de
        cualquier otro gate; no se invoca `/receiving-code-review`.
      - **Pre-gate INV-28 (degraded, si no STRONG_NO_GO):** si
        `verdict.degraded == true`, el veredicto no cuenta como
        salida — aplica findings via INV-29, consume iteracion,
        re-invoca MAGI esperando full consensus.
      - **Pre-gate INV-29 (receiving-code-review):** antes de aplicar
        cualquier cambio, invoca `/receiving-code-review`. Bajo
        INV-24 (auto conservador), findings ambiguas se tratan como
        rechazadas. Todos los rechazos se acumulan en el historial.
      - **Arbol de veredicto (aplicado tras INV-28/29):**
        - `STRONG_GO` / `GO` full: sale.
        - `STRONG_GO` / `GO` degraded: re-invoca (INV-28).
        - `GO_WITH_CAVEATS`: aplica findings aceptadas; sale solo si
          full AND todas bajo-riesgo AND ningun rechazo de INV-29.
          Sino, re-invoca.
        - `HOLD` / `HOLD_TIE`: aplica findings aceptadas, re-invoca.
        - (`STRONG_NO_GO` no llega aqui — ya abortado en short-circuit.)

   c. Al salir: registra veredicto final en `.claude/magi-verdict.json`
      con campo `degraded` propagado del output MAGI. Si al alcanzar
      `auto_magi_max_iterations` el veredicto sigue degraded o con
      findings rechazadas persistentes, aborta exit 8 con diagnostico
      especifico en el reporte final y en `.claude/auto-run.json`.

4. **Fase 4 — Validacion del checklist sec.7:**

   Reutiliza la logica de `finalize_cmd.py` **hasta el paso previo** al
   `/finishing-a-development-branch`. Verifica cada item:

   - [ ] Todas las tareas `[x]` en el plan.
   - [ ] State file: `null` + `"done"`.
   - [ ] sec.M.0.1 limpio.
   - [ ] `git status` limpio.
   - [ ] Loop 1 clean-to-go registrado.
   - [ ] **Gate MAGI aprobado Y no-degraded** (INV-28, sec.S.10.3):
         `.claude/magi-verdict.json` debe tener verdict >= threshold
         Y `degraded: false`. Si el ultimo veredicto es degraded, Fase 4
         falla incluso aunque label supere threshold — Fase 3 no logro
         consensus completo de 3 agentes.
   - [ ] Commits siguen convenciones sec.5.

   Si algun item falla: aborta con exit 9 (post-condiciones del plan
   insatisfechas — algo raro ocurrio entre Fase 3 y Fase 4, o un edge case
   no cubierto).

5. **Fase 5 — Reporte final + stop:**

   Imprime resumen ejecutivo:

   ```
   /sbtdd auto: DONE.

   Started:   2026-04-19T10:00:00Z
   Finished:  2026-04-19T12:34:17Z
   Duration:  2h 34m

   Tasks:     7/7 completed
   Commits:   24 (tasks + 3 review fixes + 2 MAGI fixes)
   MAGI:      GO WITH CAVEATS (3-0) after 2 iterations
   Verdict:   All finalization checklist items pass.

   Branch status: clean, ready for merge/PR.

   Next steps (manual):
     /sbtdd finalize       — invokes /finishing-a-development-branch
     or                     — use your own merge/PR flow directly
   ```

   **`auto` no invoca `/finishing-a-development-branch`.** Termina con
   `git status` limpio sobre el branch actual y delega la decision de
   merge/PR al usuario. Exit 0 significa "rama lista para merge segun
   tus reglas".

   **Interaccion con `/sbtdd finalize` post-auto:** si el usuario invoca
   `finalize` despues de `auto` exitoso, el checklist sec.7 es idempotente
   — `auto` ya lo valido en Fase 4, asi que `finalize` re-pasa rapidamente
   sin hacer cambios, y dispara `/finishing-a-development-branch`. No es
   redundante: `finalize` existe precisamente para que el usuario decida
   cuando pasar al merge/PR, desacoplando el paso final de la ejecucion
   del plan.

**Postcondiciones (exito):**

- Todas las tareas del plan commiteadas atomicamente con prefijos correctos.
- Ambos loops pre-merge pasados y registrados.
- Checklist sec.7 validado.
- `git status` limpio respecto al alcance del plan.
- `.claude/auto-run.json` contiene trazabilidad (timestamps, tareas
  procesadas, veredictos, commits del mini-ciclo).
- Exit code 0.

**Errores (con exit codes, ver sec.S.11.1):**

| Exit | Condicion | Recovery |
|------|-----------|----------|
| 2 | Pre-flight check fallo (sec.1.3) | Instala faltantes, re-ejecutar `/sbtdd auto` |
| 3 | Drift detectado por `detect_drift` al inicio de Fase 2 o entre iteraciones del bucle de tareas (discrepancia entre state file, git HEAD y plan) | Ejecutar `/sbtdd status` para ver los 3 valores enfrentados; resolver manualmente antes de re-invocar `auto` |
| 6 | Verificacion sec.M.0.1 fallo tras `auto_verification_retries` en una fase | Modo manual: inspecciona la tarea, arregla, re-ejecutar desde donde state file apunta |
| 7 | Loop 1 no converge en 10 iteraciones | Probablemente bug en `/requesting-code-review` o divergencia severa; investigar manualmente |
| 8 | MAGI `STRONG_NO_GO` o > `auto_magi_max_iterations` sin convergencia | Requiere replan: volver a `/sbtdd spec` con feedback de los findings acumulados |
| 9 | Checklist sec.7 falla tras Fase 3 completada | Drift o edge case; ejecutar `/sbtdd status` para diagnosticar, resolver manualmente |
| 11 | Exhaustion de cuota Anthropic detectada durante Fase 2 (en `close-phase` interno) o Fase 3 (en `pre-merge` interno): rate limit 429 persistente, session/weekly/Opus limit, credit balance, server throttle — ver sec.S.11.4 | Esperar al reset indicado (si el mensaje lo expone) o recargar creditos; re-invocar `/sbtdd resume` tras reponerse la cuota para continuar desde el ultimo punto estable |

En todos los casos de aborto:

- **NO** se revierten commits ya creados (son evidencia de la corrida).
- Se registra el estado en `.claude/auto-run.json` con razon del aborto.
- `/sbtdd status` reporta correctamente el punto de interrupcion.
- El usuario puede retomar: desde el estado actual con `/sbtdd auto` de
  nuevo (si el aborto fue transiente), o pasando a modo manual/
  subagent-driven desde donde el state file apunta.

**Invariantes especificas de auto:**

- **INV-22 (Secuencialidad obligatoria):** auto ejecuta tareas y fases
  secuencialmente, incluso si el plan permite paralelismo via
  `addBlockedBy`. Razon: sin supervision humana, paralelizar amplifica el
  blast radius de un bug temprano. Quien quiera paralelizar usa
  `/subagent-driven-development` + worktrees.
- **INV-23 (TDD-Guard inviolable):** auto NUNCA toggea `tdd-guard off`.
  Si el usuario quiere correr sin guard, usa otro modo. En auto, el guard
  es red de seguridad.
- **INV-24 (Sin elevacion subjetiva):** si en cualquier punto el flujo
  requeriria decision subjetiva del usuario que no puede automatizarse
  (p.ej. evaluar si un caveat MAGI es "bajo riesgo" en la frontera),
  auto aplica la regla conservadora: **trata caveats ambiguos como
  estructurales** y re-invoca MAGI. Prefiere gastar presupuesto MAGI sobre
  asumir.
- **INV-25 (Alcance limitado al branch):** auto no mergea, no pushea, no
  abre PRs, no toca remoto. Delega toda interaccion con mundo compartido
  al usuario.
- **INV-26 (Trazabilidad completa):** `.claude/auto-run.json` debe
  reflejar cada transicion importante (fase cerrada, tarea cerrada,
  iteracion de loop). Es el audit trail post-mortem para cualquier aborto
  o revision.

### 5.9 Politica de re-verificacion de dependencias

La re-ejecucion del pre-flight check (sec.S.5.1.1) **no** es uniforme entre
subcomandos — aplica el siguiente criterio fijo:

| Subcomando | Re-verifica deps al iniciar? | Razon |
|------------|------------------------------|-------|
| `init` | SI (es su funcion principal) | Es la primera ejecucion; nada esta garantizado aun |
| `auto` | SI (sec.S.5.8 Fase 1a) | Corrida larga sin supervision; el entorno puede haber degradado desde init |
| `resume` | SI (sec.S.5.10 Fase 1) | Puede estar ejecutandose en sesion completamente distinta a la que dejo el trabajo a medias; el entorno podria haber cambiado |
| `spec`, `close-phase`, `close-task`, `status`, `pre-merge`, `finalize` | NO | Confian en que `init` dejo el entorno operativo; re-verificar en cada subcomando agrega latencia sin beneficio practico |

**Consecuencia:** si el usuario desinstala una dependencia obligatoria
entre `init` y un subcomando interactivo, el subcomando fallara en el
momento en que intente usarla (p.ej. `spec` fallara al invocar
`/brainstorming` si superpowers fue desinstalado; `pre-merge` fallara al
invocar `/magi:magi` si magi fue desinstalado). Estos fallos se mapean a
exit code 2 (PRECONDITION_FAILED) con mensaje claro, pero pueden llegar
tras trabajo parcial. Es un trade-off deliberado: uniformidad entre
interactivos + perf, a costa de deteccion tardia en el caso patologico
de "desinstalar mid-workflow". `auto` es la excepcion porque no puede
pedir al usuario que repare mid-run.

### 5.10 `resume` (recuperacion tras interrupcion)

**Trigger:** `/sbtdd resume` tras una sesion anterior que haya quedado a
medias — token exhaustion, crash del proceso, Ctrl+C, reinicio de maquina,
timeout del modelo, etc. Funciona tanto en la misma sesion como en una
sesion completamente nueva (incluso dias despues), porque el state file y
git son persistentes (sec.S.9.2 INV-30).

**Proposito:** punto de entrada **explicito y diagnostico** para reanudar
cualquier flujo SBTDD interrumpido. Lee state file + git HEAD + runtime
artifacts, reporta el estado con claridad, y delega al subcomando
apropiado. No reimplementa logica de fase; es un wrapper de diagnostico
y despacho.

**Argumentos:**

| Arg | Tipo | Default | Descripcion |
|-----|------|---------|-------------|
| `--discard-uncommitted` | flag | false | Descarta trabajo sin commitear en el working tree (`git checkout HEAD -- .` + `git clean -fd`) antes de reanudar. Escape valve cuando el trabajo no-commiteado quedo corrupto tras un crash. Respeta `.gitignore` — no borra `.venv/`, `.claude/`, etc. |
| `--auto` | flag | false | Modo no-interactivo: no pregunta al usuario ante ambigüedad; aplica defaults conservadores (CONTINUE sobre uncommitted, INV-24 para decisiones subjetivas) |
| `--dry-run` | flag | false | Analiza el estado e imprime el plan de reanudacion, sin ejecutar |

**Precondiciones:**

- `.claude/plugin.local.md` existe (bootstrap de `init` completado; sin
  esto no hay proyecto SBTDD al que reanudar).
- `.claude/session-state.json` existe. Si NO existe, `resume` imprime
  *"No hay sesion SBTDD activa para reanudar — el proyecto esta en modo
  manual o aun no se inicio un feature. Invoca `/sbtdd spec` para
  arrancar."* y sale con exit 0.

**Comportamiento — cinco fases:**

1. **Fase 1 — Pre-flight check + lectura de estado:**
   a. Re-ejecuta `dependency_check.check_environment()` (sec.S.5.1.1) —
      el entorno pudo haber cambiado entre sesiones. Aborta exit 2 si
      dependencias faltan.
   b. Lee state file → `current_task_id`, `current_task_title`,
      `current_phase`, `plan_approved_at`, `last_verification_at`,
      `last_verification_result`, `phase_started_at_commit`.
   c. Lee HEAD de git (`git log -1 --format="%h %s"`) y prefijo del
      ultimo commit.
   d. Ejecuta `detect_drift` (sec.S.9.2). Si retorna no-None, aborta
      con exit 3 — no se puede reanudar sobre drift (reconciliacion
      silenciosa oculta bugs de protocolo).
   e. Inspecciona estado del working tree (`git status --short`):
      `clean` vs `dirty` (con lista de archivos).
   f. Revisa presencia de `.claude/magi-verdict.json` y
      `.claude/auto-run.json` para detectar si habia una corrida
      autonoma o pre-merge en progreso. De `auto-run.json` extrae
      `auto_started_at` y la ultima fase registrada.

2. **Fase 2 — Reporte diagnostico al usuario:**

   Imprime un resumen estructurado (siempre, incluso con `--auto` y
   `--dry-run`):

   ```
   /sbtdd resume: analizando estado...

   State file (.claude/session-state.json):
     current_task_id:        3
     current_task_title:     "Extract validation into separate fn"
     current_phase:          green
     plan_approved_at:       2026-04-18T10:00:00Z
     phase_started_at_commit: a3f2d1c
     last_verification:      2026-04-19T14:22:00Z — passed

   Git HEAD:
     SHA:       b7e8f0d
     Prefijo:   test:
     Mensaje:   "test: parser edge case for empty input"
     Edad:      3 hours ago

   Working tree:
     Status:    DIRTY (2 modified, 1 untracked)
     Archivos:  M src/parser.py
                M src/validator.py
                ? src/parser_helpers.py

   Runtime artifacts:
     magi-verdict.json:   ausente (pre-merge no ha corrido)
     auto-run.json:       presente — auto_started_at=2026-04-19T13:00:00Z,
                           ultima transicion: task 3 phase red cerrada

   Drift check:  none
   ```

3. **Fase 3 — Determinacion del punto de reanudacion:**

   Segun el diagnostico, `resume` decide el subcomando de destino:

   | Condicion | Accion |
   |-----------|--------|
   | `current_phase` en {`red`, `green`, `refactor`} + tree clean | Delegar a `/sbtdd auto` (si `auto-run.json` presente) o sugerir modo manual (`/sbtdd close-phase` tras trabajo del usuario) |
   | `current_phase` en {`red`, `green`, `refactor`} + tree dirty | Resolucion de uncommitted (Fase 4), luego delegar como arriba |
   | `current_phase: "done"` + sin `magi-verdict.json` + tree clean | Delegar a `/sbtdd pre-merge` |
   | `current_phase: "done"` + `magi-verdict.json` presente + tree clean | Delegar a `/sbtdd finalize` |
   | `current_phase: "done"` + tree dirty | Resolucion de uncommitted (Fase 4); probablemente mini-ciclo de pre-merge interrumpido |

4. **Fase 4 — Resolucion de uncommitted work (solo si tree dirty):**

   El trabajo sin commitear es AMBIGUO: puede ser progreso valido
   (usuario mid-trabajo cuando crashed) O corrupto (crash a mitad de
   escritura). El plugin NO puede distinguir automaticamente. Politica:

   - **Con flag `--discard-uncommitted`:** ejecuta
     `git checkout HEAD -- .` + `git clean -fd` (descarta modificados y
     untracked no-ignorados). Confirma al usuario cuantos archivos se
     descartaron. Luego continua a Fase 5.
   - **Interactivo (sin `--auto` ni `--discard-uncommitted`):** muestra
     lista de archivos dirty + la fase activa, y pregunta:
     ```
     El trabajo sin commitear puede ser progreso valido o resto de un
     crash. ¿Que haces?
       [C] Continue  — mantener trabajo sin commitear y reanudar
                       (el siguiente close-phase decidira si pasa
                       verificacion)
       [R] Reset     — descartar uncommitted y reanudar desde HEAD
       [A] Abort     — salir sin hacer nada

     Eleccion [C/R/A]:
     ```
   - **`--auto` (no-interactivo sin `--discard-uncommitted`):** default
     conservador para preservar trabajo — **CONTINUE**. Razon: el
     usuario puede tener horas de codigo sin commitear que no se debe
     perder silenciosamente. Si el trabajo esta roto, la verificacion
     fallara en el proximo `close-phase` y los safety valves existentes
     (`auto_verification_retries` + exit 6) lo capturaran.

5. **Fase 5 — Invocacion del subcomando delegado:**

   Tras resolver el estado del tree, `resume` invoca internamente el
   subcomando determinado en Fase 3. Ejemplo:
   - `/sbtdd resume` → determina `pre-merge` → invoca `pre_merge_cmd.run()`.
   - El exit code de `resume` es el del subcomando delegado.

   **Con `--dry-run`:** la Fase 5 NO se ejecuta. En su lugar imprime:
   ```
   Resume plan: invocaria `pre_merge_cmd.run()` con args por default.
   No se ejecuto nada (--dry-run).
   ```
   Exit 0.

**Postcondiciones (exito):**

- `resume` delego a un subcomando concreto que completo con exit 0, O
  retorno el exit code de ese subcomando sin transformacion.
- El state file y el working tree son coherentes al salir (mismo
  requerimiento que cualquier transicion de fase).

**Errores (con exit codes, ver sec.S.11.1):**

- **Exit 0 (SUCCESS):** diagnostico + delegacion sin errores. O
  `--dry-run`. O `session-state.json` ausente (nada que reanudar).
- **Exit 1 (USER_ERROR):** state file corrupto (`StateFileError`).
- **Exit 2 (PRECONDITION_FAILED):** dependencia faltante (re-flight
  check fallo), `plugin.local.md` ausente.
- **Exit 3 (DRIFT_DETECTED):** `detect_drift` retorna no-None. Resume
  no fuerza reconciliacion.
- **Exit codes del subcomando delegado** (2, 3, 6, 7, 8, 9, **11**): se
  propagan sin transformacion. Ejemplos:
  - `resume` → delega a `pre-merge` → pre-merge aborta exit 8
    (MAGI_GATE_BLOCKED) → `resume` retorna 8.
  - `resume` → delega a `auto` → `/brainstorming` hit quota → exit 11
    (QUOTA_EXHAUSTED, sec.S.11.4) → `resume` retorna 11. El usuario
    ve el mensaje con `reset_time` y re-invoca `/sbtdd resume` tras
    el reset — loop de recuperacion convergente.
  - `resume` → delega a `close-phase` → drift detectado → exit 3 →
    `resume` retorna 3.

**Invariantes:**

- **Nunca modifica el state file directamente.** Delega a subcomandos
  que si lo hacen (close-phase, close-task, auto, etc.).
- **Nunca crea commits.** Los subcomandos delegados pueden commitear
  segun su propia logica.
- **Con `--dry-run`, cero side effects.** No toca disco (salvo lectura).
- **Con `--discard-uncommitted`:** NO afecta archivos fuera del working
  tree git (no borra `.venv/`, `.claude/`, `CLAUDE.local.md` u otros
  ignorados).
- **Default conservador en `--auto`:** NUNCA descarta trabajo sin
  commitear sin flag explicito. Preservar progreso sobre asumir
  corrupcion.
- **Idempotente:** invocar `resume` dos veces seguidas en un estado
  clean-done produce el mismo comportamiento (delegar a `finalize` o
  imprimir "nothing to resume").

---

## 6. Especificacion del skill `sbtdd` (SKILL.md)

### 6.1 Proposito

Unico skill del plugin (paridad con MAGI). Es el **dispatcher**: gate de
complejidad + parseo de intent + delegacion al script Python correcto. NO
ejecuta logica de estado; todo pasa por `run_sbtdd.py`.

### 6.2 Frontmatter (YAML)

```yaml
---
name: sbtdd
description: >
  SBTDD + Superpowers multi-agent workflow orchestrator. Use when working on
  a project that follows the SBTDD methodology (Spec + Behavior + Test
  Driven Development) and needs to execute one of the nine workflow
  operations: init, spec, close-phase, close-task, status, pre-merge,
  finalize, auto, resume. Trigger phrases: "sbtdd init", "sbtdd close
  phase", "advance TDD phase", "run pre-merge review", "finalize SBTDD
  plan", "sbtdd auto", "shoot-and-forget SBTDD run", "resume SBTDD",
  "sbtdd resume", "continue interrupted SBTDD session", or any "/sbtdd
  <subcommand>" invocation. NOT suitable for projects that do not use
  SBTDD — only invoke when the project has `sbtdd/spec-behavior-base.md`
  or a `.claude/plugin.local.md` with `stack` set.
---
```

### 6.3 Estructura del cuerpo

SKILL.md DEBE contener las siguientes secciones, en orden:

1. **Overview** — descripcion breve del sistema SBTDD.
2. **Subcommand dispatch** — tabla: subcomando → proposito → cuando usar.
3. **Complexity gate** — "si el usuario pregunta cosas triviales que no
   involucran transicion de estado, responde directo sin invocar Python".
4. **Execution pipeline** — pseudocodigo de como invocar `run_sbtdd.py`:

   ```
       python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py \
           <subcommand> [args...]
   ```

5. **Seccion `sbtdd-rules`** (embebida) — reglas de la metodologia cargadas como
   referencia. Contenido: sec.0, sec.M.2.1, sec.M.2.4, sec.3 reglas por
   fase, sec.3 reglas universales, sec.5 prefijos + excepciones, sec.6
   tabla de veredictos.
6. **Seccion `sbtdd-tdd-cycle`** (embebida) — guia de ciclo TDD. Contenido:
   que hacer en Red, Green, Refactor; cuando invocar
   `/test-driven-development`, `/verification-before-completion`,
   `/sbtdd close-phase`, `/systematic-debugging`.
7. **Fallback** — si Python no disponible, responder con guia manual al
   usuario (analogo al fallback de MAGI SKILL.md cuando `claude -p` no
   disponible).

### 6.4 Invariantes del skill

- SKILL.md NO debe duplicar semantica de la metodologia. Cita secciones
  embebidas por referencia (`ver sec.N`, siguiendo la notacion de sec.0)
  en lugar de reescribir reglas; el contenido fuente vive en la propia
  SKILL.md + `templates/CLAUDE.local.md.template` (ver el preambulo del
  spec — principio de Autocontencion).
- SKILL.md NO debe ejecutar transiciones de estado — siempre delega a
  Python.
- SKILL.md DEBE declararse en frontmatter con trigger description lo
  suficientemente especifico para que Claude lo invoque solo en proyectos
  SBTDD (ver 6.2 — la descripcion menciona los archivos marcadores).

---

## 7. Especificacion de hooks

### 7.1 Hooks del plugin (desarrollo)

`.claude/settings.json` del plugin `sbtdd-workflow` (para quien desarrolla
el plugin, no para el proyecto destino) DEBE replicar los hooks de MAGI:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|TodoWrite",
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ]
  }
}
```

Identico al `settings.json` del plugin MAGI.

### 7.2 Hooks del proyecto destino (instalados por `init`)

`templates/settings.json.template` DEBE contener el mismo set de tres
hooks (PreToolUse / UserPromptSubmit / SessionStart) para instalarse en
`.claude/settings.json` del proyecto destino. El subcomando `init` fusiona
con hooks existentes del usuario sin sobrescribir.

### 7.3 Drift-check hook (opcional)

`SessionStart` puede extenderse con un segundo comando que invoque
`python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/drift.py` para detectar
drift heredado de sesion previa. Non-blocking: solo warning a stderr.

**Nota sobre `drift.py` dual-use:** el modulo se usa como biblioteca
(importado desde `status_cmd.py`, `close_phase_cmd.py`, etc.) y como
script CLI (invocado por el hook). DEBE incluir el bloque
`if __name__ == "__main__":` con parseo minimo via `argparse` (flag
`--project-root`, default `os.getcwd()`), y exit code 0 (sin drift), 3
(drift detectado, segun taxonomia sec.11.1). Cuando se invoca como
biblioteca, las funciones retornan estructuras de datos; el mapeo a exit
code se hace solo en el bloque `__main__`.

---

## 8. Convenciones Python (derivadas de MAGI)

### 8.1 File headers

Todo archivo `.py` creado por el plugin DEBE comenzar con el header de
sec.M.0.2 (reglas project-specific de la metodologia), en formato Python:

```python
#!/usr/bin/env python3
# Author: {Author}
# Version: 1.0.0
# Date: YYYY-MM-DD
"""Module docstring."""
```

El shebang aplica solo a scripts ejecutables (no a `__init__.py`).

### 8.2 Tipado estricto

- Python >= 3.9.
- `from __future__ import annotations` en todo modulo que use anotaciones
  de tipo modernas.
- `mypy --strict` debe pasar sin warnings.
- Configuracion en `pyproject.toml` replica MAGI:
  ```toml
  [tool.mypy]
  python_version = "3.9"
  strict = true
  mypy_path = "skills/sbtdd/scripts"
  explicit_package_bases = true
  ```

### 8.3 Linting y formato

- `ruff check .` — 0 warnings.
- `ruff format --check .` — clean.
- Line length: 100 (identico a MAGI).
- Docstrings: Google o NumPy style (segun la seccion "Documentation" en `~/.claude/CLAUDE.md`).

### 8.4 Errores

- Modulo `scripts/errors.py` define:
  ```python
  class SBTDDError(Exception): ...
  class ValidationError(SBTDDError): ...       # Schema / plugin.local.md
  class StateFileError(SBTDDError): ...        # state file corrupto
  class DriftError(SBTDDError): ...            # drift detectado
  class DependencyError(SBTDDError): ...       # toolchain / plugins CC
  class PreconditionError(SBTDDError): ...     # precondicion de subcomando
  class MAGIGateError(SBTDDError): ...         # veredicto < umbral
  class QuotaExhaustedError(SBTDDError): ...   # API Anthropic: rate limit / session / weekly / credit (sec.S.11.4)
  ```
- Todas las excepciones del plugin DEBEN derivar de `SBTDDError` para
  permitir catch-all en el dispatcher.
- NO usar `assert` para validar input — usar `raise ValidationError(...)`.

### 8.5 Inmutabilidad

- Registros fijos (prefijos de commit, mapa de veredictos, nombres de
  subcomandos) DEBEN exponerse como `MappingProxyType` o `tuple`, no dict /
  list mutables. Patron directo de MAGI `scripts/models.py`.

### 8.6 Subprocess

- Usar `subprocess.run` con `check=False` + validacion explicita del
  returncode (patron MAGI `subprocess_utils.py`).
- `shell=False` obligatorio. Argumentos como lista, no como string.
- Timeouts explicitos en toda invocacion externa.
- Kill-tree en Windows replica el orden MAGI: `taskkill /F /T /PID` antes
  de `proc.kill()`.

### 8.7 Logging

- `print()` a stdout solo para reportes legibles al usuario (status,
  banners, mensajes de exito).
- Errores y warnings a stderr via `sys.stderr.write` o `print(..., file=sys.stderr)`.
- No usar `logging` module (MAGI no lo usa; evitar dependencias extra).

---

## 9. Contrato del state file (`.claude/session-state.json`)

### 9.1 Schema (extension local del schema de sec.M.2.2)

Superset del schema base de la metodologia: incluye todos sus campos
originales mas un campo adicional local (`plan_approved_at`) para tracking
de aprobacion del plan:

```json
{
  "type": "object",
  "required": ["plan_path", "current_task_id", "current_task_title",
               "current_phase", "phase_started_at_commit",
               "last_verification_at", "last_verification_result",
               "plan_approved_at"],
  "properties": {
    "plan_path": { "type": "string" },
    "current_task_id": { "type": ["string", "null"] },
    "current_task_title": { "type": ["string", "null"] },
    "current_phase": {
      "type": "string",
      "enum": ["red", "green", "refactor", "done"]
    },
    "phase_started_at_commit": { "type": "string", "pattern": "^[0-9a-f]{7,40}$" },
    "last_verification_at": { "type": ["string", "null"], "format": "date-time" },
    "last_verification_result": { "type": ["string", "null"], "enum": ["passed", "failed", null] },
    "plan_approved_at": { "type": ["string", "null"], "format": "date-time" }
  }
}
```

`plan_approved_at` es la extension local de este plugin sobre el schema
base de la metodologia: registra el timestamp ISO 8601 cuando el usuario
confirmo la aprobacion del plan al final de `spec`. `null` significa "plan
no aprobado — sin commits automaticos" (sec.M.5 "Excepcion bajo plan
aprobado" de la metodologia).

### 9.2 Orden de autoridad

Los tres artefactos de estado runtime (state file, git, plan) pueden
discrepar sobre la misma transicion. Cuando lo hacen, este es el orden
canonico de autoridad (inlined aqui para cumplir el principio de
Autocontencion del preambulo del spec):

```
1. Git es canon del pasado      — los commits son inmutables, la
                                   timeline es verdad.
2. State file es canon del presente — unica fuente del "ahora" durante
                                   ejecucion (`.claude/session-state.json`).
3. Plan es canon del futuro + registro documental — que falta + que se
                                   completo (`planning/claude-plan-tdd.md`).
```

**Regla operativa:** si `current_phase` en state file reporta `green`
pero el ultimo commit tiene prefijo `refactor:`, **hay drift** — el
subcomando aborta con exit 3 (DRIFT_DETECTED, sec.S.11.1). La recuperacion
es manual, no automatica; sincronizacion silenciosa ocultaria bugs de
protocolo.

Implementacion: `scripts/drift.py` expone:

```python
def detect_drift(state_file_path: Path, plan_path: Path,
                 repo_root: Path) -> DriftReport | None:
    """Return None if no drift; DriftReport with the three conflicting
    values (state, git, plan) if detected."""
```

**Invocadores de `detect_drift`:** cinco subcomandos invocan esta funcion,
divididos en dos clases por proposito:

- **Mutadores de estado (abort-before-mutation):** `close-phase`,
  `close-task`, `pre-merge`, `auto`. Invocan `detect_drift` al inicio,
  antes de cualquier cambio; si retorna no-None, abortan con exit 3
  (DRIFT_DETECTED) **antes** de mutar estado. La sincronizacion
  silenciosa ocultaria bugs de protocolo.
- **Lector de diagnostico (report-only):** `status`. Invoca `detect_drift`
  para reportar el estado al usuario; si detecta drift, lo imprime en
  el reporte estructurado y sale con exit 3 (util para CI), pero sin
  modificar nada ni escalar mas alla del exit code. Status es pura
  funcion de diagnostico — la accion correctiva queda al usuario.

Subcomandos que **NO** invocan `detect_drift`: `init` (no lee state file),
`spec` (crea/resetea state file), `finalize` (valida checklist, no
transiciones mid-flight).

### 9.3 Recovery

- State file corrupto: `scripts/state_file.py` lanza `StateFileError`.
- Regeneracion manual guiada por `/sbtdd status` que imprime ultimo `[x]`
  del plan + ultimo commit + sugerencia de valores para cada campo.
- El plugin NO auto-recover; siempre pide confirmacion del usuario.

---

## 10. Comportamientos esperados (invariantes del sistema)

Estas propiedades DEBEN sostenerse a lo largo de cualquier sesion que use
el plugin. Son invariantes globales, no de componentes individuales.

### 10.0 Invariante de precedencia maxima

- **INV-0 (`~/.claude/CLAUDE.md` manda):** las reglas globales del
  desarrollador en `~/.claude/CLAUDE.md` (Code Standards) tienen
  **precedencia absoluta** sobre todo lo demas: este spec, la metodologia
  SBTDD embebida, `CLAUDE.local.md` del proyecto destino, `plugin.local.md`,
  y los defaults de cualquier subcomando. Si una regla de este spec entra
  en conflicto con `~/.claude/CLAUDE.md`, gana `~/.claude/CLAUDE.md`. El
  plugin no implementa flag ni override que eluda esta invariante.

  **Aplicacion practica:** cada subcomando que genera codigo, mensajes de
  commit, docstrings, o cualquier artefacto textual DEBE adherir a los
  Code Standards globales — en particular:

  - Paradigma: OOP preferido, funcional solo cuando aplica (seccion "Programming Paradigm" de `~/.claude/CLAUDE.md`).
  - Nombres y estilo: snake_case/PascalCase/UPPER segun el lenguaje (seccion "Style").
  - Git: mensajes en ingles, sin `Co-Authored-By`, sin referencias a Claude/IA (seccion "Git").
  - Testing: TDD estricto Red-Green-Refactor, nombres descriptivos (seccion "Testing").
  - Errores: patrones idiomaticos del lenguaje (seccion "Error Handling").
  - Seguridad: validacion de input, sin secretos hardcoded (seccion "Security").

  Los subcomandos del plugin NO duplican estas reglas en su propia logica
  — las invocan via el Code Standards autoritativo. Cualquier verificacion
  cruzada (p.ej. `commits.py` valida prefijos + idioma ingles + ausencia
  de `Co-Authored-By`) es **enforcement**, no redefinicion.

### 10.1 Invariantes de estado

- **INV-1 (atomicidad de fase):** tras `close-phase` exitoso, el commit en
  HEAD y el state file DEBEN ser consistentes (drift = 0).
- **INV-2 (no-mezcla de fases):** ningun commit contiene cambios de mas de
  una fase TDD.
- **INV-3 (plan monotono):** los `[x]` del plan solo se marcan, nunca se
  desmarcan. **Semantica de retomar `auto` tras aborto** (coherente con
  sec.S.9.2 "Orden de autoridad" — state file es canon del presente):
  - El state file indica la fase **activa** (a trabajar o en progreso),
    NO una fase recien completada. Ejemplo: si el state file dice
    `current_phase: "red"` y el usuario cerro Red via `close-phase`,
    `close-phase` YA avanzo el state file a `"green"` antes de terminar
    (sec.S.5.3 paso 3c). `current_phase: "red"` con un commit `test:` en
    HEAD es **drift**, no estado normal.
  - Si al retomar `auto` el state file apunta a una tarea cuyo checkbox
    en el plan ya esta `[x]`: drift, exit 3 (sec.S.11.1).
  - Si `current_phase` en state file es inconsistente con el prefijo del
    ultimo commit segun la tabla de transiciones (`red` → commit con
    prefijo `test:` es drift; `green` → commit `feat:`/`fix:` es drift;
    `refactor` → commit `refactor:` es drift — todos estos "fase-X con
    commit de cierre de fase-X" indican que `close-phase` fallo entre
    el commit y la actualizacion del state file): drift, exit 3.
  - Si `current_phase` es consistente con el HEAD de git — es decir,
    el prefijo del ultimo commit NO es el commit-de-cierre de la fase
    indicada por `current_phase` (p.ej. `current_phase: "red"` + ultimo
    commit es `chore:` de la tarea anterior, O es un commit anterior a
    `plan_approved_at` porque esta es la primera tarea del feature):
    `auto` retoma **la fase indicada por el state file**, verificando
    antes si hay cambios sin commitear. Si los hay, ejecuta la logica
    de `close-phase` de esa fase. Si no, procede a escribir el codigo
    de esa fase desde cero.
  - **Nunca re-ejecuta una fase cuyo commit ya esta en HEAD** — pero la
    deteccion de ese caso es via drift check (no via asuncion silenciosa);
    si el drift check pasa, es porque el state file y git son coherentes.
- **INV-4 (state file ausencia):** si el state file no existe, el proyecto
  esta en modo manual (sec.M.3 "Flujo manual" de la metodologia). Ningun
  subcomando opera sin confirmacion excepto `init`, `spec`, `status`.

### 10.2 Invariantes de commits

- **INV-5 (prefijos):** todo commit creado por el plugin lleva uno de los
  prefijos de sec.5 de la metodologia.
- **INV-6 (ingles):** todo mensaje de commit en ingles.
- **INV-7 (sin referencias a IA):** ningun commit menciona Claude, IA,
  asistente, ni `Co-Authored-By`.
- **INV-8 (autorizacion):** fuera de las 4 categorias de la metodologia sec.5
  "Excepcion bajo plan aprobado" (plan_approved_at != null), el plugin pide
  permiso explicito.

### 10.3 Invariantes de orquestacion

- **INV-9 (Loop 2 requiere Loop 1):** `pre-merge` NUNCA invoca MAGI antes
  de clean-to-go de `/requesting-code-review`.
- **INV-10 (umbral MAGI):** `finalize` NO permite avanzar con veredicto
  menor al umbral configurado.
- **INV-11 (safety valves — tres inventarios distintos):** ningun loop del
  plugin itera indefinidamente. Caps duros:
  - `magi_max_iterations` (default 3): Checkpoint 2 de `spec` (loop MAGI
    contra spec + plan) y Loop 2 de `pre-merge` interactivo.
  - `auto_magi_max_iterations` (default 5, DEBE `>= magi_max_iterations`):
    Loop 2 dentro de `auto` (shoot-and-forget eleva el presupuesto para
    absorber la falta de juicio humano).
  - `10` (hardcoded, no configurable): Loop 1 de `pre-merge` y `auto` —
    `/requesting-code-review` deberia converger por naturaleza; este cap
    solo dispara ante bug del skill o divergencia severa.

  Al alcanzar cualquier cap, el subcomando detiene con exit code
  apropiado (sec.S.11.1) y escala al usuario con causas candidatas.
- **INV-12 (precondiciones estrictas):** cada subcomando valida sus
  precondiciones antes de modificar estado.
- **INV-28 (MAGI degradado NO sale del loop):** si `/magi:magi` retorna
  un veredicto con flag `degraded: true` (< 3 agentes con verdict
  exitoso; MAGI mismo setea este flag cuando procede con 2 agentes
  en lugar de abortar), el subcomando NO usa ese veredicto como senal
  de salida de su loop MAGI, incluso si cumple `magi_threshold`. La
  regla aplica a los **tres loops MAGI del plugin**:
  1. **Checkpoint 2 de `spec`** (sec.S.5.2 paso 5): aprobacion del
     plan TDD contra spec.
  2. **Loop 2 de `pre-merge`** (sec.S.5.6): gate de calidad final
     pre-merge interactivo.
  3. **Loop 2 de `auto` Fase 3b** (sec.S.5.8): gate de calidad final
     shoot-and-forget.
  - Para veredictos GO-family o HOLD-family degradados: aplicar las
    acciones recomendadas (via el gate INV-29 para los loops 2 y 3;
    para el Checkpoint 2 de `spec`, el agente aplica las conditions
    reescribiendo el plan, ver sec.S.5.2), consumir una iteracion del
    safety valve, re-invocar MAGI esperando full 3-agent consensus.
  - **Excepcion — STRONG_NO_GO degradado:** abortar con exit 8 igual
    que full STRONG_NO_GO. Dos agentes independientes diciendo NO-GO
    es suficiente evidencia; no requiere 3-agent consensus para
    escalar fallos graves. En `spec`, esto escala al usuario con
    sugerencia de refinar `spec-behavior-base.md`.
  - Motivacion: el valor de MAGI es el consenso de 3 perspectivas
    independientes (Melchior/Balthasar/Caspar). Aceptar salida con
    < 3 agentes rompe ese contrato y oculta sistematicamente el
    riesgo que el agente ausente habria identificado. Caspar (el
    critico adversarial) es el mas propenso a detectar fallos
    sutiles; perderlo silenciosamente es inaceptable.
  - El campo `degraded: true` se propaga a `.claude/magi-verdict.json`
    y `finalize` (sec.S.5.7) rechaza avanzar si el veredicto final
    registrado es degraded, incluso aunque numericamente pase el
    threshold.

- **INV-29 (MAGI findings requieren evaluacion tecnica + feedback a la
  proxima iteracion):** toda condition o accion recomendada por MAGI
  que implique cambio de codigo — independientemente del veredicto
  (GO_WITH_CAVEATS, HOLD, HOLD_TIE) y del modo (full o degraded) —
  DEBE procesarse primero via `/receiving-code-review` antes de
  aplicarse al mini-ciclo TDD.

  **Clasificacion del resultado de `/receiving-code-review`:**
  - **Accepted** (tecnicamente valido): aplicar via mini-ciclo TDD
    (`test:` → `fix:` → `refactor:`).
  - **Rejected** (tecnicamente invalido): descartar el finding,
    registrar titulo + razon del rechazo en el historial de
    rechazos de la iteracion actual.
  - **Ambiguo** (el skill no puede decidir con confianza):
    - En `pre-merge` interactivo: pedir decision al usuario.
    - En `auto`: INV-24 aplica — tratar como rejected (conservador).

  **Feedback a la siguiente iteracion de MAGI:** el historial de
  rechazos se pasa como **contexto adicional** en la proxima
  invocacion de `/magi:magi` dentro del mismo Loop 2, con formato:

  ```
  [CONTEXTO DE ITERACIONES PREVIAS]

  En iteracion N-1, /receiving-code-review rechazo las siguientes
  recomendaciones de MAGI por las razones tecnicas indicadas:

    - Finding: "{titulo}"
      Razon del rechazo: "{razon}"
    - Finding: "{titulo}"
      Razon del rechazo: "{razon}"
    ...

  Considera estas evaluaciones tecnicas al formular el veredicto
  actual. Podes refinar, retirar, o contra-argumentar las
  recomendaciones previas, pero no las re-propongas identicamente
  sin atender al argumento tecnico que las rechazo.
  ```

  Esto da a MAGI contexto para **refinar o conceder** en vez de
  re-emitir findings identicas, reduciendo loops estériles.

  **Limites del contexto de feedback:**
  - Se incluyen las rechazos de las **ultimas 3 iteraciones** del
    Loop 2 actual (no del feature completo).
  - Si hay mas de 3 iteraciones previas, las mas viejas se
    resumen en una linea: "Adicionalmente, en iteraciones <1..N-3>
    se rechazaron findings sobre: {lista de titulos cortos}".
  - El texto del rechazo se sanitiza (escape de markdown/prompt
    markers) antes de pasarse, para evitar inyeccion accidental.

  **Interaccion con INV-28:** si MAGI retorna degraded, igual se
  invoca `/receiving-code-review` sobre sus findings (porque
  potencialmente aplican cambios), y el feedback se pasa a la
  siguiente iteracion igual. La regla de INV-28 (no salir con
  degraded) y la de INV-29 (evaluar + feedback) operan en capas
  distintas y no se cancelan.

  **Excepcion — STRONG_NO_GO:** no tiene conditions aplicables al
  codigo, asi que `/receiving-code-review` no se invoca. Se aborta
  directo con exit 8 (vía INV-28 si degraded, sino via el arbol
  normal de veredicto).

- **INV-30 (Resumibilidad tras interrupcion):** toda corrida SBTDD
  interrumpida por cualquier causa externa al plugin es **reanudable**
  en una sesion posterior de Claude Code, incluso dias o semanas
  despues. Causas cubiertas:
  - **Token/quota exhaustion del API Anthropic** (rate limit 429
    persistente, session/weekly/Opus limit de subscription, credit
    balance insuficiente, server throttle). Detectado automaticamente
    por `quota_detector.py` (sec.S.11.4) y mapeado a exit 11
    (QUOTA_EXHAUSTED). El usuario recibe mensaje con `reset_time` si
    el plan lo expone, e invoca `/sbtdd resume` tras el reset.
  - **Crash del proceso Claude Code** (OOM, segfault, power loss).
    No detectado por el plugin (proceso muere); el state file queda
    en el ultimo punto estable confirmado. Usuario re-abre Claude
    Code e invoca `/sbtdd resume`.
  - **Ctrl+C del usuario** (SIGINT). El dispatcher captura y sale
    con exit 130; state file en ultimo punto estable.
  - **Timeout del modelo / context window exhaustion dentro de un
    skill invocado**. Propagado via stderr del skill; si coincide con
    patrones de `quota_detector.py`, exit 11; si no, el dispatcher
    lo trata como fallo generico (exit 1) con mensaje descriptivo.

  La resumibilidad se sostiene sobre tres mecanismos existentes:

  1. **Persistencia del state file** al final de cada fase cerrada
     (INV-1): `.claude/session-state.json` siempre refleja el ultimo
     punto estable confirmado.
  2. **Atomicidad de commits** (INV-2): el HEAD de git siempre apunta
     a un punto estable verificado por sec.M.0.1. No hay commits
     parciales ni "work-in-progress" en git.
  3. **Subcomando dedicado `/sbtdd resume`** (sec.S.5.10): punto de
     entrada explicito que lee state + git + runtime artifacts,
     diagnostica el punto de interrupcion, y delega al subcomando
     apropiado para continuar.

  **Garantia:** en el peor caso se pierde **unicamente el trabajo
  sin commitear del `current_phase` activo al momento de la
  interrupcion**. Todas las fases cerradas previas (commits en HEAD)
  quedan preservadas. El usuario puede:
  - Preservar el trabajo sin commitear (default `resume --auto`) —
    util si el crash ocurrio en un punto donde el trabajo era
    progresivo-valido.
  - Descartarlo via `resume --discard-uncommitted` — util si el
    crash dejo archivos corruptos o a mitad de escritura.

  **Consecuencia arquitectonica:** ningun subcomando SBTDD debe
  asumir que la sesion en la que fue invocado es la misma que
  aprobo el plan o cerro la fase anterior. Cada subcomando DEBE
  validar estado al iniciar (drift check + state file + plan
  checkboxes) y degradar a exit 3 ante inconsistencia. Sesiones son
  stateless por contrato; el estado runtime vive en disco.

- **INV-31 (spec-reviewer gate en task close):** todo cierre de
  tarea en `auto_cmd` y `close_task_cmd` (interactive) DEBE pasar
  aprobacion del spec-reviewer (superpowers `/subagent-driven-development`
  spec-reviewer-prompt.md) antes de que `mark_and_advance` avance el
  state file, excepto cuando `--skip-spec-review` este presente (flows
  manuales donde el usuario ya verifico compliance) o cuando un stub
  de test inyectado reemplace el dispatcher. El reviewer opera sobre
  el diff del task + texto del task (NO el spec completo) para mantener
  cost acotado. Findings rutean via `/receiving-code-review` (extension
  de INV-29 a spec-review findings). Safety valve: 3 iter por task;
  exhaustion lanza `SpecReviewError` y bloquea `mark_and_advance`.
  Introducido en v0.2 (Feature B).

### 10.4 Invariantes de seguridad

- **INV-13 (no force push):** nunca `git push --force` ni `git reset --hard`
  sobre ramas compartidas.
- **INV-14 (no secretos):** nunca commitear archivos con patrones de
  secretos (`.env`, claves API). Si detecta, aborta y avisa.
- **INV-15 (respeto a gitignore):** los archivos listados en `.gitignore`
  por el plugin (`.claude/`, `CLAUDE.md`, `CLAUDE.local.md`) nunca son
  staged ni commiteados.

### 10.5 Invariantes de comunicacion

- **INV-16 (evidencia antes de aserciones):** reports de "verificacion
  paso" DEBEN mostrar salida literal de los comandos sec.M.0.1.
- **INV-17 (drift visible):** drift detectado se reporta explicitamente
  con los 3 valores enfrentados. Nunca se oculta.
- **INV-18 (escalacion explicita):** detencion por safety valve,
  precondicion fallida, veredicto irremontable DEBE explicar por que y
  que opciones tiene el usuario.

### 10.6 Invariantes de compatibilidad (herencia MAGI)

- **INV-19 (Python 3.9+):** todos los scripts funcionan en Python 3.9 en
  adelante. No usar features de 3.10+ sin fallback.
- **INV-20 (cross-platform):** scripts funcionan en Windows, Linux, macOS.
  Usar `pathlib.Path`, `tempfile.mkdtemp`, `shutil.which` — no asumir
  separadores UNIX.
- **INV-21 (stdlib-only en hot path):** subcomandos de estado criticos
  (`close-phase`, `close-task`, `status`) NO deben depender de paquetes
  externos runtime. Dev deps (ruff, mypy, pytest) son aceptables; runtime
  es stdlib.

### 10.7 Invariantes de validacion de entradas

- **INV-27 (spec base sin pendientes):** `spec-behavior-base.md` NUNCA
  debe entrar al pipeline de `/sbtdd spec` si contiene los marcadores
  `TODO`, `TODOS`, o `TBD` (uppercase, word boundary). La validacion
  aplicada en sec.S.5.2 precondicion (c) es **regla dura** no-eludible:
  no hay flag `--force` ni override que la desactive. El racional es
  economico — invocar `/brainstorming` sobre una spec incompleta genera
  un plan con huecos que MAGI tiene que rechazar en Checkpoint 2,
  gastando ciclos inutilmente. Detectar antes = iterar menos.

  **Nota de numeracion:** INV-27 viene tras INV-22..26 (invariantes
  auto-especificas definidas en sec.S.5.8). La secuencia INV-16..18
  (comunicacion) → INV-19..21 (compatibilidad) → INV-22..26 (auto,
  ubicadas en sec.5.8) → INV-27 (validacion de entradas) es monotona
  creciente aunque las familias esten distribuidas en distintas
  secciones.

---

## 11. Modos de falla y recuperacion

### 11.1 Taxonomia canonica de exit codes

Todos los subcomandos comparten esta taxonomia. El dispatcher
`run_sbtdd.py` mapea `SBTDDError` y subclases (sec.8.4) a estos codigos. No
se introducen exit codes fuera de esta tabla; la consistencia cross-
subcommand permite que scripts externos (CI, wrappers del usuario) reaccionen
igual sin importar que subcomando fallo.

| Exit | Nombre | Excepcion | Descripcion | Emitido por |
|------|--------|-----------|-------------|-------------|
| 0 | SUCCESS | — | Exito | Todos |
| 1 | USER_ERROR | `ValidationError` o `StateFileError` o violacion de input | Arg invalido, mensaje vacio, stack no soportado, state file corrupto (JSON invalido o schema-invalido detectado por `status` u otros subcomandos que lo lean; lanzan `StateFileError`, subclase de `SBTDDError` via sec.S.8.4), etc. | Todos |
| 2 | PRECONDITION_FAILED | `PreconditionError` o `DependencyError` | Precondicion no cumplida: dependencia faltante (lanza `DependencyError`, mapeada a este codigo porque conceptualmente una dep faltante es una precondicion no cumplida), state file ausente cuando se requiere, state file previo sin cerrar (caso del subcomando `spec` cuando encuentra feature anterior en progreso), git status sucio, `plan_approved_at` null cuando se exige, etc. | init, spec, close-phase, close-task, pre-merge, finalize, auto, resume |
| 3 | DRIFT_DETECTED | `DriftError` | Discrepancia entre state file, git HEAD y plan que requiere intervencion humana | close-phase, close-task, status, pre-merge, auto, resume |
| 4 | FILE_CONFLICT | `SBTDDError` | Archivo existente bloquea la operacion (p.ej. `CLAUDE.local.md` sin `--force`). Disjunto de exit 3 — no es drift, es conflicto de archivo usuario | init |
| 5 | SMOKE_TEST_FAILED | `SBTDDError` | Fase 4 post-setup de `init` fallo; rollback aplicado | init |
| 6 | VERIFICATION_IRREMEDIABLE | `SBTDDError` | `/verification-before-completion` fallo tras `auto_verification_retries` reintentos en modo auto. Equivalente en modo interactivo (`close-phase`) es exit 1 (USER_ERROR) — contexto interactivo permite al usuario reintentar sin escalada; auto no | auto |
| 7 | LOOP1_DIVERGENT | `SBTDDError` | Loop 1 de code review no converge tras 10 iteraciones (safety valve duro) | pre-merge, auto |
| 8 | MAGI_GATE_BLOCKED | `MAGIGateError` | Veredicto MAGI `STRONG_NO_GO`, O > `magi_max_iterations` / `auto_magi_max_iterations` sin convergencia. Requiere replan | spec, pre-merge, auto |
| 9 | CHECKLIST_FAILED | `SBTDDError` | Uno o mas items del checklist sec.7 fallaron en `finalize` o en Fase 4 de auto | finalize, auto |
| 11 | QUOTA_EXHAUSTED | `QuotaExhaustedError` (nueva, subclase de `SBTDDError` via sec.S.8.4) | Exhaustion de cuota externa Anthropic detectada al invocar un skill (superpowers o magi): rate limit 429 persistente tras retries, session/weekly/Opus limit de subscription, credit balance agotado, o server throttle. El plugin persiste state y escala al usuario con sugerencia de `/sbtdd resume` al reponerse la cuota. Ver sec.S.11.4 para patrones exactos detectados | spec, pre-merge, auto |
| 130 | INTERRUPTED | `KeyboardInterrupt` | Usuario envio SIGINT (Ctrl+C). Dispatcher termina subprocesos limpiamente y exit | Todos |

**Reglas de diseno:**

- Un subcomando NUNCA emite un codigo fuera de los que le corresponden
  (columna "Emitido por"). Si un subcomando detecta un fallo cuyo codigo
  "no es suyo", debe mapearlo al codigo mas cercano de su conjunto o
  elevar a exit 1 (USER_ERROR) con mensaje explicativo.
- **Exit codes altos (6-11) representan fallos estructurales o de
  escalacion que NO se resuelven con un prompt simple al usuario.** Se
  emiten tanto en modo autonomo (`auto`) como interactivo (spec,
  pre-merge, finalize) cuando aplica. La distincion es por tipo de fallo,
  no por modo:
  - **Exit 6 es exclusivo de `auto`** (VERIFICATION_IRREMEDIABLE tras
    agotarse `auto_verification_retries`). En modo interactivo, un
    close-phase con verificacion fallida simplemente retorna exit 1 y
    el usuario reintenta — no escala.
  - **Exits 7, 8, 9, 11** se emiten por interactivos Y auto ante
    condiciones estructurales que requieren accion humana especifica:
    Loop 1 divergente (bug de skill), MAGI STRONG_NO_GO (replan),
    checklist fail (drift entre fase 3 y 4), quota externa agotada
    (esperar reset). En estos casos no hay un prompt simple que
    resuelva la situacion — el usuario debe actuar fuera del plugin.
  - Para otros fallos recuperables dentro del flujo interactivo
    (precondiciones, ambiguedad, decisiones de diseno), los
    subcomandos interactivos SI usan prompts en vez de exit codes.
- Cualquier exit code alto (>= 6) se acompana de trazabilidad en el
  artefacto correspondiente (`auto-run.json` para auto;
  `magi-verdict.json` para decisiones MAGI) y mensaje claro al usuario
  con el siguiente paso sugerido.

**Mapeo completo de excepciones → exit codes (sec.S.8.4 → sec.S.11.1):**

| Excepcion (sec.S.8.4) | Exit code mapeado |
|-----------------------|-------------------|
| `ValidationError` | 1 (USER_ERROR) |
| `StateFileError` | 1 (USER_ERROR) — JSON/schema invalido |
| `DriftError` | 3 (DRIFT_DETECTED) |
| `DependencyError` | 2 (PRECONDITION_FAILED) |
| `PreconditionError` | 2 (PRECONDITION_FAILED) |
| `MAGIGateError` | 8 (MAGI_GATE_BLOCKED) |
| `QuotaExhaustedError` | 11 (QUOTA_EXHAUSTED) |
| `SBTDDError` (base, no especifica) | depende del subcomando (4/5/6/7/9) |

Toda subclase futura de `SBTDDError` DEBE agregarse a esta tabla antes de
usarse en produccion; el dispatcher (sec.S.11.2) catchea `SBTDDError` pero
el mapeo a exit code requiere registro explicito para no caer al codigo
genérico 1 por default.

### 11.2 Falla del dispatcher

- `run_sbtdd.py` captura `SBTDDError` y sus subclases en el top level,
  imprime mensaje human-readable a stderr, y sale con el exit code de
  sec.11.1.
- Excepciones no capturadas (bug del plugin) se propagan con traceback
  completo y exit 1 — el usuario las reporta como bug.

### 11.3 Kill de subproceso largo

Si usuario interrumpe (Ctrl+C) durante `spec`, `pre-merge`, o `auto`, los
sub-subprocesos que el plugin lanzo (/brainstorming, /writing-plans,
/magi:magi, etc.) DEBEN ser terminados limpiamente siguiendo el patron
MAGI: en Windows, `taskkill /F /T /PID` antes de `proc.kill()`; en
POSIX, `signal.SIGTERM` con timeout y luego `signal.SIGKILL`. Ningun
sub-subproceso debe quedar huerfano. Exit code del dispatcher en este
caso: 130 (SIGINT estandar).

### 11.4 Deteccion de exhaustion de cuota externa (Anthropic API)

Cuando el plugin invoca skills de Claude Code (via `superpowers_dispatch.py`
o `magi_dispatch.py`) que a su vez ejecutan `claude -p` contra el API de
Anthropic, el API puede responder con errores de cuota/rate limit. Claude
Code CLI reintenta automaticamente hasta `CLAUDE_CODE_MAX_RETRIES` (default
10) para errores 429 transitorios; si tras los retries el error persiste,
o si es un limite de subscription/credit (no retryable), el skill devuelve
stderr con patrones especificos que el plugin DEBE detectar y mapear a
exit 11 (QUOTA_EXHAUSTED).

**Patrones de deteccion (texto literal emitido por Claude Code CLI):**

| Tipo de exhaustion | Patron regex | Recuperable | Mensaje al usuario |
|-------------------|--------------|-------------|---------------------|
| Rate limit 429 persistente (tras 10 retries) | `Request rejected \(429\)` | Si (esperar/retry) | "Rate limit de API Anthropic excedido. Los retries automaticos de Claude CLI se agotaron. Esperar unos minutos y re-invocar con `/sbtdd resume`." |
| Session limit (plan Pro/Max) | `You've hit your session limit · resets (.+)` | Si (esperar al reset indicado) | "Cuota de sesion Claude agotada. Se repone a las {reset_time}. Re-invocar `/sbtdd resume` despues de esa hora." |
| Weekly limit (plan) | `You've hit your weekly limit · resets (.+)` | Si (esperar al reset) | "Cuota semanal Claude agotada. Se repone el {reset_time}. Re-invocar `/sbtdd resume` en esa fecha." |
| Opus-specific limit | `You've hit your Opus limit · resets (.+)` | Si (esperar o usar otro modelo) | "Cuota de Opus agotada. Se repone a las {reset_time}. Opciones: esperar, o re-invocar con override de modelo a Sonnet/Haiku si el skill lo acepta." |
| Credit balance (pay-as-you-go) | `Credit balance is too low` | Si (recargar creditos) | "Balance de creditos Anthropic insuficiente. Recargar en console.anthropic.com y re-invocar `/sbtdd resume`." |
| Server throttle temporal | `Server is temporarily limiting requests` | Si (esperar) | "Anthropic esta throttleando requests temporalmente (no es tu cuota). Esperar unos minutos y re-invocar `/sbtdd resume`." |

**Implementacion en `scripts/quota_detector.py`:**

```python
# Author: Julian Bolivar
# Version: 1.0.0
# Date: YYYY-MM-DD
"""Detecta exhaustion de cuota Anthropic en stderr de skills invocados."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

QUOTA_PATTERNS: Mapping[str, re.Pattern[str]] = MappingProxyType({
    "rate_limit_429": re.compile(r"Request rejected \(429\)"),
    "session_limit": re.compile(r"You've hit your (session|weekly|Opus) limit · resets (.+?)(?:\s|$)"),
    "credit_exhausted": re.compile(r"Credit balance is too low"),
    "server_throttle": re.compile(r"Server is temporarily limiting requests"),
})

@dataclass(frozen=True)
class QuotaExhaustion:
    kind: str                    # key de QUOTA_PATTERNS
    raw_message: str             # linea completa del stderr
    reset_time: str | None       # extraido de session_limit si aplica
    recoverable: bool            # True para todos los casos actuales; reservado por si Anthropic agrega no-recoverable

def detect(stderr: str) -> QuotaExhaustion | None:
    """Scan stderr for quota exhaustion patterns. Returns None if no match."""
    for kind, pattern in QUOTA_PATTERNS.items():
        match = pattern.search(stderr)
        if match:
            reset_time = match.group(2) if kind == "session_limit" else None
            return QuotaExhaustion(
                kind=kind,
                raw_message=match.group(0),
                reset_time=reset_time,
                recoverable=True,
            )
    return None
```

**Integracion en dispatchers** (`magi_dispatch.py`, `superpowers_dispatch.py`):

```python
from errors import QuotaExhaustedError
import quota_detector

def invoke_skill(skill_cmd: list[str]) -> str:
    proc = subprocess.run(skill_cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        # Check for quota exhaustion BEFORE treating as generic failure
        exhaustion = quota_detector.detect(proc.stderr)
        if exhaustion is not None:
            raise QuotaExhaustedError(
                f"{exhaustion.kind}: {exhaustion.raw_message}"
                + (f" (reset: {exhaustion.reset_time})" if exhaustion.reset_time else "")
            )
        # ... otros manejos de error
```

**Comportamiento del plugin ante deteccion de cuota exhausta:**

1. **Persistencia del state file YA esta garantizada** por INV-1 (state file se actualiza solo al final de cada fase cerrada — en medio de una invocacion de skill, el state file refleja el ultimo punto estable).
2. **Abort sin efectos parciales**: si el skill fallo mid-invocacion, no se aplica el finding/condicion que estaba procesando. No hay commit parcial.
3. **Mensaje claro al usuario**: imprime el `raw_message` del error + `reset_time` (si aplica) + sugerencia explicita de re-invocar `/sbtdd resume` cuando la cuota se reponga.
4. **Exit 11 (QUOTA_EXHAUSTED)**: el dispatcher captura `QuotaExhaustedError` y retorna exit 11.
5. **Trazabilidad en `.claude/auto-run.json`** (si estaba corriendo `auto`): se registra la detection con timestamp, kind, y raw_message antes del abort.

**Limitaciones documentadas:**

- **La deteccion es regex-based sobre texto libre.** Anthropic no publica un formato JSON estructurado para rate-limit errors (confirmado en research — ver `docs/claude-code-errors-research.md` si se decide archivar la investigacion). Si Anthropic cambia los mensajes, `QUOTA_PATTERNS` en `quota_detector.py` debe actualizarse. Para mitigar: centralizar patrones en un unico modulo (el presente) + test contract con fixtures capturados de errores reales.
- **No hay hook de "exhaustion imminent"**: Claude Code CLI no emite senal anticipada. El plugin solo se entera cuando el skill ya fallo. Consecuencia: si un skill falla en medio de un mini-ciclo de fix, ese mini-ciclo queda a medias — pero el state file sigue apuntando al ultimo close-phase exitoso, asi que `/sbtdd resume` re-ejecuta el mini-ciclo completo limpiamente (idempotente).
- **Los retries automaticos de Claude CLI** (10x exponential backoff) ocurren ANTES de que veamos el error. Ya no necesitamos reintentar — si vemos el patron, es porque ya se agoto el retry budget.

**Relacion con INV-30 (Resumibilidad):** quota exhaustion es **uno de los casos explicitos** que INV-30 cubre. La deteccion via `quota_detector.py` + exit 11 es el canal automatico por el que el plugin se entera; `/sbtdd resume` es el mecanismo manual para continuar tras reset.

---

## 12. Criterios de aceptacion del plugin

### 12.1 Funcionales

- [ ] **INV-0 enforcement:** ningun subcomando genera commits con
      `Co-Authored-By`, mensajes en idioma distinto a ingles, o
      referencias a Claude/IA. Test cross-subcommand: cada `*_cmd.py`
      que invoque `commits.py` debe validarse contra muestras que
      contengan esos patrones prohibidos, y el test debe pasar SOLO si
      el subcomando aborta antes de commitear.
- [ ] `/sbtdd init --stack rust --author "Test" --error-type "TestErr"` en
      repo git vacio genera los archivos documentados sin estado parcial si
      aborta.
- [ ] `/sbtdd spec` completa loop MAGI o escala tras 3 iteraciones. Aborta
      con exit 2 si `spec-behavior-base.md` contiene marcadores `TODO`,
      `TODOS`, o `TBD` uppercase (INV-27, regla dura sec.S.5.2.c). El
      reporte de error muestra cada linea con su numero y el marcador
      detectado.
- [ ] Ciclo `/sbtdd close-phase` x 3 sobre una tarea produce 3 commits
      atomicos + transicion + cierre de tarea automatico al cerrar Refactor.
- [ ] `/sbtdd status` sobre cualquier estado valido imprime reporte sin
      modificar archivos.
- [ ] `/sbtdd pre-merge` con findings simulados aplica mini-ciclo, re-corre
      hasta clean, luego Loop 2. `STRONG_NO_GO` detiene sin fix automatico.
- [ ] **INV-28 enforcement (MAGI degraded) — tres contextos:**
      - **Loop 2 de `pre-merge`**: stub retorna `{verdict: "GO",
        degraded: true}` → Loop 2 NO sale, consume iteracion, re-
        invoca. Cap alcanzado con degraded persistente → exit 8.
        Variante `{verdict: "STRONG_NO_GO", degraded: true}` → short-
        circuit exit 8 inmediato.
      - **Loop 2 de `auto` Fase 3b**: mismo comportamiento que
        pre-merge, con `auto_magi_max_iterations` como cap.
      - **Checkpoint 2 de `spec` (sec.S.5.2)**: stub retorna
        `{verdict: "GO_WITH_CAVEATS", degraded: true}` → el loop
        aplica conditions pero no sale; sigue iterando hasta full
        consensus o exit 8 al agotar `magi_max_iterations`. Variante
        `{verdict: "STRONG_NO_GO", degraded: true}` → short-circuit
        exit 8 sugiriendo refinar spec-behavior-base.md.
- [ ] **INV-29 enforcement (receiving-code-review gate + feedback):**
      - Test donde MAGI emite una finding claramente invalida
        (p.ej. contradice `CLAUDE.local.md`). `/receiving-code-review`
        la rechaza, el mini-ciclo NO ejecuta, el rechazo se registra en
        el historial.
      - Test que en la proxima iteracion, `/magi:magi` recibe el
        historial como contexto (verificable capturando el prompt
        pasado al skill).
      - Test que `finalize` rechaza (**exit 9** CHECKLIST_FAILED) si
        `magi-verdict.json` tiene `degraded: true`, incluso si el label
        pasa threshold — el item "Gate MAGI aprobado" del checklist
        exige threshold **Y** `degraded: false`. Consistente con
        `auto` Fase 4 que mapea la misma condicion a exit 9.
- [ ] `/sbtdd finalize` aborta si cualquier item del checklist sec.7 falla.
- [ ] `/sbtdd auto` desde plan aprobado hasta branch limpio:
      - Ejecuta las tareas pendientes secuencialmente sin intervencion humana.
      - `--dry-run` imprime el plan y sale con exit 0 sin crear
        `.claude/auto-run.json`.
      - Aborta con exit 6 si `/verification-before-completion` falla
        despues de `auto_verification_retries` reintentos en una fase.
      - Aborta con exit 7 si Loop 1 no converge en 10 iteraciones.
      - Aborta con exit 8 si MAGI retorna `STRONG_NO_GO` o no converge en
        `auto_magi_max_iterations` iteraciones.
      - Termina con `git status` limpio, sin invocar
        `/finishing-a-development-branch`, y con `.claude/auto-run.json`
        conteniendo trazabilidad completa.
- [ ] **Deteccion de exhaustion de cuota (`quota_detector.py`,
      sec.S.11.4):** para cada patron de `QUOTA_PATTERNS`, test con
      fixture de stderr que contiene el mensaje. Cada test verifica:
      - `quota_detector.detect(fixture)` retorna `QuotaExhaustion` con
        `kind` correcto y `reset_time` parseado si aplica.
      - Integracion: `magi_dispatch.py` stub que simula skill falla
        con stderr = fixture propaga `QuotaExhaustedError`. Dispatcher
        (`run_sbtdd.py`) sale con exit 11.
      - Negativo: stderr con texto normal de error (no-quota) NO
        dispara `QuotaExhaustedError`; cae a fallo generico (exit 1).
      - Fixtures archivados en `tests/fixtures/quota-errors/` (al
        menos una muestra literal por cada tipo en `QUOTA_PATTERNS`).
- [ ] **INV-30 enforcement (`/sbtdd resume`) — recuperacion tras
      interrupcion:**
      - Test: tras simular interrupcion durante `auto` (state file
        quedo en `current_phase: "green"` + tree dirty con codigo
        parcial), invocar `/sbtdd resume --auto` resulta en: default
        CONTINUE (preserva tree), delega a `auto`, y la proxima
        iteracion de close-phase valida el trabajo.
      - Test: `/sbtdd resume --discard-uncommitted` sobre mismo estado
        ejecuta `git checkout HEAD -- .` + `git clean -fd`, luego
        delega a `auto` con tree limpio.
      - Test: `/sbtdd resume --dry-run` imprime plan de reanudacion
        sin side effects (no toca `auto-run.json`, no invoca
        subcomandos delegados).
      - Test: `/sbtdd resume` con drift detectado aborta con exit 3
        sin intentar delegar.
      - Test: `/sbtdd resume` sin `.claude/session-state.json` sale
        con exit 0 y mensaje "nothing to resume".
      - Test: `/sbtdd resume` tras `auto` completo exitosamente
        (state `done` + `magi-verdict.json` presente) delega a
        `finalize`.

### 12.2 Paridad con MAGI

- [ ] Estructura de directorios identica al layout sec.S.2.1.
- [ ] `pyproject.toml` con `mypy strict` + `ruff line-length 100`.
- [ ] `Makefile` con targets `test / lint / format / typecheck / verify`.
- [ ] `conftest.py` con integracion tdd-guard (archivo de test results).
- [ ] `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` con
      version coincidente.
- [ ] LICENSE + LICENSE-APACHE (dual).
- [ ] README.md con seccion Installation + marketplace instructions.
- [ ] CLAUDE.md con Project Overview + Development Commands + Plugin
      Structure + Cross-file contracts + Distribution + Test Coverage.
- [ ] Todos los scripts Python con header `Author / Version / Date`.

### 12.3 No-funcionales

- [ ] Idempotencia: `/sbtdd init --force` con mismos args produce archivos
      byte-identicos.
- [ ] Atomicidad: fallo parcial (disco lleno) deja proyecto destino en
      estado previo.
- [ ] Performance: `/sbtdd status` < 1s en repos de hasta 10k commits.
- [ ] Portabilidad: Windows (git bash / WSL), Linux, macOS.

### 12.4 Test coverage (paridad MAGI)

- [ ] >= 1 test file por modulo bajo `skills/sbtdd/scripts/`.
- [ ] Tests de contrato para cada subcomando (inputs invalidos,
      precondiciones, happy path).
- [ ] Tests de schema del state file (JSON valido + invalido).
- [ ] Tests de deteccion de drift.
- [ ] Tests de idempotencia de `init`.
- [ ] Tests de fusion de `settings.json` preservando hooks externos.
- [ ] Fixtures en `tests/fixtures/` (planes sinteticos, state files, plugin
      locals) — paradigma identico a MAGI `tests/fixtures/`.
- [ ] `make verify` pasa limpio: pytest + ruff check + ruff format + mypy.

### 12.5 Distribucion (paridad MAGI)

- [ ] Repo publico en GitHub bajo BolivarTech.
- [ ] Instalable via `/plugin marketplace add` + `/plugin install`.
- [ ] Version en `plugin.json` y `marketplace.json` en sync.
- [ ] Symlink development documentado (`mkdir -p .claude/skills && ln -s
      ../../skills/sbtdd .claude/skills/sbtdd`).

---

## 13. Decisiones de diseno pendientes

1. **Registro de aprobacion del plan:** RESUELTO — campo `plan_approved_at`
   en state file (sec.9.1).
2. **Registro del veredicto MAGI:** RESUELTO — archivo
   `.claude/magi-verdict.json` escrito por `pre-merge` (sec.5.6).
3. **Granularidad de "bajo riesgo" en caveats MAGI:** preguntar al usuario
   en la primera iteracion; futuras versiones pueden aprender patrones.
4. **Politica de worktrees:** `plugin.local.md` define
   `worktree_policy: optional | required`. `pre-merge` pregunta modo
   serial | paralelo; si paralelo, exige worktree.
5. **Versioning:** `plugin.local.md` incluira un campo `schema_version`
   en v0.2 para manejar upgrades de la metodologia.
6. **Internacionalizacion:** split espanol (archivos bajo `templates/` del
   plugin, documentacion de usuario, este spec) + ingles (mensajes de
   error, commits, nombres de tests, frontmatter de SKILL.md). Mantener.
7. **Soporte multi-framework C++ (v0.2+):** v0.1 requiere `ctest` como
   launcher y JUnit XML como formato intermedio. Para v0.2+ se evaluaran
   adaptadores directos a GoogleTest (`--gtest_output=xml:`), Catch2
   (`-r junit`), y launchers alternativos (bazel `--test_output`, meson
   test, build.ninja directo). Mientras tanto, la **formula de escape**
   para proyectos no-ctest: el usuario edita `verification_commands`
   manualmente y provee un reporter custom que escriba
   `.claude/tdd-guard/data/test.json` en el schema TDD-Guard. Cualquier
   script que cumpla ese contrato de salida es suficiente; el plugin no
   impone ctest como requisito tecnico, solo como default del `init`.
8. **Resumibilidad tras interrupcion:** RESUELTO — subcomando
   `/sbtdd resume` (sec.S.5.10) con diagnostico + delegacion + manejo
   explicito de trabajo sin commitear. Formalizado como INV-30
   (sec.S.10.3).
9. **Paridad de verification checks entre stacks (futuro):** actualmente
   Rust tiene 6 checks (test + lint + format + build + doc + audit),
   Python 4 (test + lint + format + typecheck), C++ 2 (test + build).
   Para v0.2+ se evaluara llevar los tres stacks a 6 checks, agregando en
   Python `ruff check --select D` (doc style) + `pip-audit`, y en C++
   `clang-tidy` + `clang-format --dry-run` + `doxygen` + `cve-bin-tool`.
   Trade-off: sube la barra de entrada del pre-flight check (mas
   dependencias que instalar) a cambio de rigor uniforme. Mientras tanto,
   el usuario puede agregar comandos manualmente a `verification_commands`
   en `plugin.local.md` sin esperar al release.

---

## 14. Referencias

- **Metodologia SBTDD (encarnada en este plugin):**
  - `skills/sbtdd/SKILL.md` — reglas operativas embebidas.
  - `templates/CLAUDE.local.md.template` — reglas parametrizables que se
    instalan en el proyecto destino.
  - Este spec (`sbtdd-workflow-plugin-spec.md`) — contrato funcional.
- **Reglas globales (`~/.claude/CLAUDE.md`) — autoridad maxima:** el
  archivo personal del desarrollador que invoca Claude Code, presente en
  cualquier maquina donde el plugin corre (desarrollo del plugin,
  instalacion en un proyecto destino, ejecucion de cualquier subcomando).
  Cubre Code Standards (paradigma, calidad, documentacion, estilo, error
  handling, testing, TDD, dependencias, memoria, seguridad, output
  format, build/environment, git). **Tienen precedencia absoluta sobre
  este spec y cualquier otro archivo del plugin.** Formalizado como
  INV-0 (sec.S.10.0) y reforzado en el preambulo del spec; ninguna
  clausula en ninguna otra seccion puede contradecirlas.
- **Plugin `superpowers`:** provee los skills de especificacion,
  planificacion, ejecucion, review, finalizacion que el plugin orquesta.
- **Plugin `magi`:** provee `/magi:magi` para los gates de calidad
  (Checkpoint 2 del flujo `spec` y Loop 2 del flujo `pre-merge`/`auto`).
- **Binario `tdd-guard`:** https://github.com/nizos/tdd-guard (verificar
  URL al implementar).
- **Notas de autoria (no distribuidas con el plugin):** durante la autoria
  de este spec se uso como material fuente un documento de metodologia
  SBTDD local al desarrollador del plugin. Ese material no forma parte
  de la distribucion; el plugin ships con su propia version destilada de
  las reglas en los artefactos listados arriba.
