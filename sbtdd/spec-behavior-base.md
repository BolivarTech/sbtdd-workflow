# Especificacion base — sbtdd-workflow v1.0.1 (post-v1.0.0 dogfood findings)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.1).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-03 post-v1.0.0 ship + dogfood discovery (commit `ebde133`,
> branch `feature/v1.0.1-bundle`).
>
> **CONTEXTO**: el primer intento de v1.0.1 con scope "Cross-check completion"
> (telemetry script + diff threading + spec_lint + own-cycle dogfood) revelo
> via dogfood real de `/sbtdd spec` que la dispatch chain del plugin esta
> rota a nivel arquitectural — `claude -p /<skill>` no funciona para Skills
> interactivos (brainstorming, writing-plans), y spec_snapshot tiene regex
> demasiado estricta vs production specs. Sin estas correcciones de
> fundacion, los items "Cross-check completion" stack-on-top of broken
> foundation y no se pueden ejercer end-to-end. **Por lo tanto v1.0.1 pivota
> a "Plugin self-hosting fix"; los 4 items previos (telemetry, diff
> threading, spec_lint, own-cycle dogfood) se mueven a v1.0.2** per user
> directive 2026-05-03 ("vamos a generar v1.0.1 para que arregle estos
> problemas, que son mayores, lo que estaba en v1.0.1 para a v1.0.2").
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0 frozen
> se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento
> NO lo reemplaza — agrega el delta v1.0.1 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder (verificable con grep).
>
> v1.0.1 es **single-pillar** per CHANGELOG `[1.0.0]` Process notes binding
> commitment. G1 binding HARD: cap=3 sin INV-0 path. G2 binding: scope-trim
> default si Loop 2 iter 3 no converge.

---

## 1. Objetivo

**v1.0.1 = "Plugin self-hosting fix"**: arregla las tres findings del dogfood
de v1.0.0 que descubrieron que el plugin `/sbtdd spec` y `/sbtdd pre-merge`
**no funcionan end-to-end** cuando se ejercen sobre el propio repositorio del
plugin (o, por extension, contra cualquier proyecto destino real).

Tres findings empiricos del dogfood 2026-05-03:

### Finding A (CRITICAL) — Skill subprocess invocation rota para Skills interactivos

`superpowers_dispatch.invoke_skill` dispara `claude -p "/<skill> ..."` como
subprocess one-shot. Para Skills no-interactivos (`/magi:magi` que es un
script Python self-contained) funciona correctamente — magi-report.json se
escribe. Para Skills interactivos (`/brainstorming`, `/writing-plans`)
designed for multi-turn dialogue, el subprocess exits 0 sin escribir
los artifacts esperados (`sbtdd/spec-behavior.md`, `planning/claude-plan-tdd-org.md`).

Verificacion empirica: `mtime` de los archivos sin cambio post-subprocess.
Causa raiz: `claude -p` es one-shot prompt sin stdin; Skills interactivos
terminan silently antes de producir el output.

### Finding B (IMPORTANT) — spec_snapshot regex demasiado estricta

`spec_snapshot._SECTION_RE` requiere literal `## §?4 ...Escenarios...`
header. La spec real v1.0.0 (`sbtdd/spec-behavior.md`) tiene escenarios
distribuidos a traves de `## 2. Pillar 1`, `## 3. Pillar 2`, `## 4. v0.5.1
fold-in` — ninguno con "Escenarios" en el header.

`_mark_plan_approved_with_snapshot` (R10 fix shipped en v1.0.0) raises
`ValueError` en cualquier spec con escenarios distribuidos. Tests pasan
porque fixtures usan synthetic header literal `## §4 Escenarios BDD`;
production specs no.

### Finding C (IMPORTANT) — `spec_cmd._run_spec_flow` no valida output

`spec_cmd.main` no checkea que `superpowers_dispatch.brainstorming(...)`
y `writing_plans(...)` hayan producido NUEVO contenido. Si los subprocess
exits 0 sin escribir (Finding A), spec_cmd asume exito y procede a MAGI
Checkpoint 2 con files stale del ciclo previo. MAGI evalua contenido
del v1.0.0 ciclo + nueva spec-base v1.0.1 = "looks coherent because no
mismatch detectable" = falso pass. Bug es invocation-site tripwire missing
en el output dimension.

### Cuatro items LOCKED v1.0.1

1. **Output validation tripwire (A0 fix Finding C)**: `_run_spec_flow`
   valida que spec-behavior.md y plan-tdd-org.md fueron modificados (mtime
   change check) post-subprocess. Si no, raise loud `PreconditionError`
   con guidance explicito.
2. **Permissive escenario regex (A1 fix Finding B)**: `spec_snapshot`
   acepta escenarios distribuidos a traves de cualquier seccion del spec
   (no requiere literal `## §4 Escenarios` header).
3. **Headless-mode detection + clear error (A2 fix Finding A)**:
   `superpowers_dispatch.brainstorming` y `writing_plans` detectan modo
   headless (subprocess `claude -p` con Skill interactivo) y raise
   `PreconditionError` con guidance: "Skill `/brainstorming` requiere
   sesion interactiva; correr manualmente y luego `/sbtdd spec
   --resume-from-magi`."
4. **`--resume-from-magi` flag (A3 supports A2)**: nuevo flag opcional en
   `/sbtdd spec` que skipea `_run_spec_flow` (asume artifacts ya producidos
   por el operator manualmente) y solo ejecuta `_run_magi_checkpoint2` +
   `_create_state_file` + `_commit_approved_artifacts`. Recovery path
   despues de un headless-abort.

Criterio de exito v1.0.1:
- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.0 -> 1.0.1.
- Tests baseline 1033 + 1 skipped preservados sin regresion + ~10-15
  nuevos (output validation tripwires + permissive regex + flag tests).
  Spec sec.10.4 NF-B target: +10-15 nuevos = 1043-1048 final.
- `make verify` runtime <= 150s (NF-A budget se mantiene).
- Empirical validation: `/sbtdd spec --resume-from-magi` (en interactive
  session despues de manual brainstorming/writing-plans) completa
  end-to-end y escribe state file + commit.
- v1.0.0 LOCKED commitments del CHANGELOG `[1.0.0]` Deferred section
  enteramente rolled forward a v1.0.2 (no perdidos, solo reschedulados).
- G1 binding respetado: cap=3 HARD para Checkpoint 2; sin INV-0 path.
- G2 binding respetado: si Loop 2 iter 3 no converge clean, scope-trim
  default per CHANGELOG `[0.5.0]` process commitment.

Out of scope v1.0.1 (rolled forward a v1.0.2):
- Cross-check telemetry aggregation script (`scripts/cross_check_telemetry.py`).
- Cross-check prompt diff threading (W-NEW1 fix).
- H5-2 spec_lint enforcement at Checkpoint 2.
- Own-cycle cross-check dogfood (DEPENDS on v1.0.1 fixes; primer ciclo
  donde es viable es v1.0.2).

Out of scope v1.0.1+ (rolled forward a v1.1.0+):
- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7 (opt-in flags).
- Migration tool real test.
- AST-based dead-helper detector.
- W8 Windows file-system retry-loop.
- `_read_auto_run_audit` skeleton wiring.
- R11 sweep methodology codification.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

---

## 2. Alcance v1.0.1 — items LOCKED post-v1.0.0 dogfood

### 2.1 Item A0 — Output validation tripwire (Finding C fix)

**Problema empirico**: `spec_cmd._run_spec_flow` invoca
`superpowers_dispatch.brainstorming(args=[...])` y `writing_plans(args=[...])`
y asume que escribieron `sbtdd/spec-behavior.md` y
`planning/claude-plan-tdd-org.md`. Solo verifica `path.exists()`
(no si fue **modificado**). Si los archivos pre-existen del ciclo previo,
el check pasa aunque la dispatcheada Skill no haya hecho nada.

**Entrega v1.0.1**:

- Modificar `spec_cmd._run_spec_flow` para capturar `mtime` (o `stat().st_mtime_ns`)
  pre-subprocess para cada output esperado.
- Post-subprocess: comparar mtime; si NO cambio, raise
  `PreconditionError(f"/<skill> exit 0 pero {path} no fue modificado;
  verifica que la sesion sea interactiva o usa --resume-from-magi")`.
- Tolerar el caso "first-run" (file no existe pre-subprocess; cualquier
  exists() post = success).
- Tests: `test_spec_flow_aborts_when_brainstorming_did_not_write`,
  `test_spec_flow_aborts_when_writing_plans_did_not_write`, plus first-
  run path test that mtime check skipped when file initially absent.

### 2.2 Item A1 — Permissive escenario regex (Finding B fix)

**Problema empirico**: `spec_snapshot._SECTION_RE` y `_SCENARIO_HEADER_RE`
fueron escritas con synthetic test fixtures en mente (`## §4 Escenarios BDD`
literal) pero no toleran production specs donde escenarios estan
distribuidos a traves de varios `## N. <pillar-name>` sections (e.g.,
v1.0.0 spec tiene escenarios en sec.2, sec.3, sec.4 — ninguno con
"Escenarios" en el header).

**Entrega v1.0.1**:

- Refactor `spec_snapshot.emit_snapshot` para usar TWO-tier strategy:
  1. **Primary**: si existe seccion `## §?4 ...Escenarios...` (legacy
     fixture format), usar el contenido limitado.
  2. **Fallback**: si NO, escanear el documento entero buscando todos los
     bloques `**Escenario X: ...**` o `### Escenario X: ...` (sin
     restriccion de seccion). Esto cubre production specs donde
     escenarios estan distribuidos.
- `_extract_scenarios` ya parsea esos bloques; solo necesitamos relax el
  call-site para no requerir `_SECTION_RE` match primero.
- Backward compat: synthetic fixtures con `## §4 Escenarios` siguen
  funcionando (primary path); production specs ahora funcionan (fallback
  path).
- Tests: `test_emit_snapshot_distributed_escenarios_across_sections`,
  `test_emit_snapshot_legacy_fixture_with_section_header_still_works`,
  `test_emit_snapshot_zero_escenarios_anywhere_raises_zero_match_guard`.

### 2.3 Item A2 — Headless-mode detection (Finding A mitigation)

**Problema empirico**: Skills interactivos (`/brainstorming`,
`/writing-plans`) terminan silently cuando se invocan via `claude -p`
porque no hay user input para responder a las clarifying questions.

**Entrega v1.0.1**:

- Modificar `superpowers_dispatch.invoke_skill` para detectar Skills
  conocidos como interactivos (set: `brainstorming`, `writing-plans`).
- Cuando un Skill interactivo se invoca via `claude -p`, **antes del
  subprocess**, raise `PreconditionError(
    f"Skill /{skill} es interactivo y requiere sesion Claude Code activa. "
    f"Run /{skill} manualmente en la sesion actual y luego "
    f"/sbtdd spec --resume-from-magi para continuar el flow"
  )`.
- Detectable via env var `CLAUDE_CODE_HEADLESS` o equivalente, OR
  conservatively: si el Skill esta en la set de "interactive-only",
  siempre raise (forzando al operator a usar el `--resume-from-magi`
  recovery path).
- Tests: `test_invoke_skill_brainstorming_raises_in_headless_mode`,
  `test_invoke_skill_magi_works_in_headless_mode_unchanged` (regression).

**Decision pendiente para brainstorming**: el set exacto de Skills
"interactive-only". Probable conservadora: `brainstorming`,
`writing-plans`, `verification-before-completion` (este ultimo tambien
es interactive-leve). v1.0.1 minimum = `brainstorming` + `writing-plans`.

### 2.4 Item A3 — `--resume-from-magi` recovery flag (supports A2)

**Problema**: si A2 raise hace que `/sbtdd spec` aborte cuando se intenta
sin sesion interactiva, el operator necesita un recovery path: **producir
los artifacts manualmente** (correr brainstorming/writing-plans
interactivamente, o editar spec-behavior.md y plan-tdd-org.md a mano), y
luego decirle al plugin "skipea el dispatch step, ya tengo los archivos,
solo corre Checkpoint 2".

**Entrega v1.0.1**:

- Nuevo flag `--resume-from-magi` en `_build_parser` de `spec_cmd.py`.
- Cuando set, `spec_cmd.main` skipea `_validate_spec_base_no_placeholders`
  + `_run_spec_flow` y va directo a `_run_magi_checkpoint2`.
- `_run_magi_checkpoint2` valida que spec-behavior.md + plan-tdd-org.md
  EXISTEN antes de dispatchar MAGI (ya esta validation, refuerza).
- Tests: `test_spec_resume_from_magi_skips_brainstorming_and_writing_plans`,
  `test_spec_resume_from_magi_still_runs_checkpoint2_and_state_writes`,
  `test_spec_resume_from_magi_aborts_when_artifacts_missing`.
- Dokumentacion: README + SKILL.md updates.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-36 preservados. v1.0.1 propone:

- **INV-37 (propuesta, contingent on Item A0)**: `spec_cmd._run_spec_flow`
  DEBE validar que outputs de `superpowers_dispatch.brainstorming` y
  `writing_plans` fueron escritos durante el subprocess (mtime change
  check), no solo que existen pre-subprocess.

Critical durante implementacion v1.0.1:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default OR
  exact phrase override. v1.0.1 single-pillar bundle deberia converger
  facil.
- **Single-pillar default**.
- **Invocation-site tripwires**: cualquier helper nuevo (incluyendo
  output validation gates A0 + headless detection A2) ships con
  invocation-site tripwire test ANTES de close-task.
- **`/receiving-code-review` sin excepcion** every Loop 2 iter MUST run
  skill on findings.

### Stack y runtime

Sin cambios vs v1.0.0:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot paths.
- Dependencias externas: git, tdd-guard, superpowers, magi (>= 2.2.x),
  claude CLI.
- Dependencias dev: pytest, pytest-asyncio, ruff, mypy, pyyaml.
- Licencia dual MIT OR Apache-2.0.

### Reglas duras no-eludibles (sin override)

- INV-0 autoridad global.
- INV-27 spec-base sin uppercase placeholder markers (este doc cumple).
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).
- G1 binding cap=3 HARD para Checkpoint 2 (CHANGELOG `[1.0.0]`).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F88 v1.0.0; v1.0.1 starts at F90.)

**F90** (Item A0). `spec_cmd._run_spec_flow` captures pre-subprocess mtime
for each expected output. Post-subprocess raises `PreconditionError` if
file unchanged (or missing entirely when first-run).

**F91** (Item A0). Error message includes guidance: "verify interactive
session OR use `--resume-from-magi` flag if artifacts produced manually".

**F92** (Item A1). `spec_snapshot.emit_snapshot` accepts distributed
escenarios across multiple sections (no `## §4 Escenarios` header
required).

**F93** (Item A1). Backward compat: synthetic fixtures with
`## §4 Escenarios BDD` continue working (primary path preserved).

**F94** (Item A1). Zero-match guard preserved: spec with NO escenarios
anywhere raises `ValueError` (silent-drift prevention).

**F95** (Item A2). `superpowers_dispatch.invoke_skill` detects Skills
classified as interactive-only (set: `brainstorming`, `writing-plans`)
and raises `PreconditionError` with recovery guidance BEFORE the
subprocess.

**F96** (Item A2). MAGI dispatch path (`magi_dispatch.invoke_magi`)
unchanged — non-interactive Skills continue working.

**F97** (Item A3). `spec_cmd._build_parser` adds `--resume-from-magi`
flag.

**F98** (Item A3). When `--resume-from-magi` set, `spec_cmd.main` skips
`_validate_spec_base_no_placeholders` + `_run_spec_flow` and proceeds
directly to `_run_magi_checkpoint2`.

**F99** (Item A3). `_run_magi_checkpoint2` validates artifact existence
before MAGI dispatch (`PreconditionError` if absent).

### Requerimientos no-funcionales (NF)

**NF26**. `make verify` runtime <= 150s (v1.0.0 baseline 117s; v1.0.1
expected slight increase from new tests; soft-target <= 130s).

**NF27**. v1.0.0 plans (with state file post-v1.0.0 schema) parse
correctly; no migration required for v1.0.1.

**NF28**. v1.0.0 production specs (escenarios distribuidos) ahora
parsean por `spec_snapshot.emit_snapshot` sin error (regression de
v1.0.0's overly-strict regex).

---

## 5. Scope exclusions

Out-of-scope v1.0.1 (rolled forward a v1.0.2):

- **Cross-check telemetry aggregation script**: dependia de
  `.claude/magi-cross-check/iter*.json` artifacts existir; v1.0.1
  habilita ese path al arreglar la dispatch chain, pero el script
  mismo se ship en v1.0.2.
- **Cross-check prompt diff threading (W-NEW1)**: scope se preserva,
  solo defer.
- **H5-2 spec_lint enforcement**: scope se preserva, solo defer.
- **Own-cycle cross-check dogfood**: DEPENDS de v1.0.1 fixes; primer
  ciclo donde es viable es v1.0.2 (correr `/sbtdd pre-merge` real
  contra v1.0.1's own diff).

Out-of-scope v1.0.1+ (a v1.1.0+):

- Mismo set que el original v1.0.0 backlog (INV-31 flip, GitHub
  Actions, Group B 1/3/4/6/7, etc.).

---

## 6. Criterios de aceptacion finales

v1.0.1 ship-ready cuando:

### 6.1 Functional Item A0 — Output validation

- **F1**. `spec_cmd._run_spec_flow` mtime check antes/despues de
  brainstorming/writing-plans subprocess.
- **F2**. Raise `PreconditionError` con guidance message si mtime no
  cambia (file no fue modificado).
- **F3**. Tests cubren: brainstorming-no-write -> abort, writing-plans-
  no-write -> abort, both-write -> success, first-run-no-prior-file ->
  success path.

### 6.2 Functional Item A1 — Permissive regex

- **F4**. `spec_snapshot.emit_snapshot` acepta production specs con
  escenarios distribuidos.
- **F5**. Backward compat preservado para synthetic fixtures.
- **F6**. Zero-match guard preservado (silent-drift prevention).

### 6.3 Functional Item A2 — Headless detection

- **F7**. `superpowers_dispatch.invoke_skill` raises antes del subprocess
  para Skills interactivos.
- **F8**. MAGI dispatch path unchanged (regression test).

### 6.4 Functional Item A3 — Recovery flag

- **F9**. `/sbtdd spec --resume-from-magi` skipea brainstorming/writing-
  plans.
- **F10**. Recovery path valida artifacts existentes antes de MAGI.

### 6.5 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format + mypy
  --strict, runtime <= 150s. Soft-target <= 130s.
- **NF-B**. Tests baseline 1033 + 1 skipped preservados + ~10-15 nuevos
  (4-5 output validation + 3-4 regex relax + 2-3 headless detect + 2-3
  recovery flag) = ~1043-1048.
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en archivos modificados/nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados:
  `spec_cmd.py`, `superpowers_dispatch.py`, `spec_snapshot.py`.

### 6.6 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per INV-28.
  Iter cap=3 HARD per G1 binding; NO INV-0 path.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict >=
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.1]` entry written con secciones Added /
  Changed / Process notes + dogfood lessons documented.
- **P4**. Version bump 1.0.0 -> 1.0.1 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.1` + push (con autorizacion explicita user).
- **P6**. Empirical proof: en una nueva sesion Claude Code, correr
  /brainstorming + /writing-plans manualmente, luego
  `/sbtdd spec --resume-from-magi` debe completar end-to-end y escribir
  state file + commit (validacion del recovery path).

### 6.7 Distribution

- **D1**. Plugin instalable.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos flags documentados en README + SKILL.md + CLAUDE.md.

---

## 7. Dependencias externas nuevas

Ninguna runtime nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.1

- **R1**. Item A2 headless detection puede ser too aggressive y
  rompe casos de uso donde Skills "interactivos" funcionan parcialmente
  via claude -p (e.g., test stubs en pytest). Mitigation: limitar set
  a Skills demonstrably-broken (brainstorming, writing-plans);
  evaluacion empirica via `/sbtdd spec --resume-from-magi` recovery
  path.
- **R2**. Item A1 permissive regex puede over-match y capturar bloques
  que no son escenarios reales (e.g., palabra "Escenario" en prosa
  natural). Mitigation: regex requiere `**Escenario\s+...**` o
  `### Escenario\s+...` con boundary chars, no plain text.
- **R3**. Item A3 `--resume-from-magi` flag puede ser misused como
  bypass general de validation. Mitigation: documentar como recovery-
  path-only; spec_cmd lo trata como explicit operator-acknowledged
  state.
- **R4**. v1.0.1 cycle se ejerce con MISMO bug que esta arreglando —
  chicken-and-egg. Mitigation: el ciclo v1.0.1 ITSELF requiere correr
  `/brainstorming` + `/writing-plans` interactivamente desde esta
  sesion Claude Code (ya estamos en sesion interactiva), luego usar
  el plugin para Checkpoint 2. Recovery path A3 NO es necesario para
  v1.0.1's own cycle si el operator drives manualmente.
- **R5**. Bundle scope de v1.0.1 es chico (4 items, todos doc/regex/
  validation level — ninguna feature nueva). Riesgo de bundle
  width minimal.
- **R6**. Items v1.0.2 (telemetry, diff threading, spec_lint, own-cycle
  dogfood) son OWNED por v1.0.2 spec-behavior-base.md (a generar
  post-v1.0.1 ship); v1.0.1 los cita pero no los implementa. Mitigation:
  CHANGELOG `[1.0.1]` Process notes lista los 4 items rolled forward
  con explicit "v1.0.2 LOCKED" marker.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.0 cycle decisions: `CHANGELOG.md` `[1.0.0]` and
  `.claude/magi-runs/v100-*` artifacts.
- **v1.0.0 dogfood findings (2026-05-03)**: este documento sec.1 Findings
  A/B/C son discoveries empiricas de intentar correr `/sbtdd spec`
  contra el propio repo del plugin. Stack trace + analysis preservado
  en conversation log de la sesion.
- v1.0.0 LOCKED commitments rolled forward a v1.0.2: ver CHANGELOG
  `[1.0.0]` Deferred section + nuevo CHANGELOG `[1.0.1]` Process notes
  rolled-forward bullets.
- v1.0.1+ deferred items roadmap (continuing to v1.1.0+):
  - INV-31 default flip dedicated cycle.
  - GitHub Actions CI workflow.
  - Group B options 1, 3, 4, 6, 7.
  - Migration tool real test.
  - AST-based dead-helper detector.
  - W8 Windows file-system retry-loop.
  - `_read_auto_run_audit` skeleton wiring.
  - R11 sweep methodology codification.
  - Spec sec.7.1.3 G2 amendment.
  - `magi_cross_check` default-flip a `true`.

---

## Nota sobre siguiente paso

Este archivo cumple INV-27. Listo como input para `/brainstorming`
(que se correra interactivamente en esta sesion, NO via `claude -p`
subprocess — por consistencia con Finding A).

Decisiones pendientes clave para brainstorming:

1. **Subagent partition**: 4 items, single-pillar, scope ~10-15h
   estimado. Probable single-subagent suffice. Item A2 + A3 son
   tightly coupled (recovery flag depende de detection). Item A0 + A1
   son independientes. Brainstorming evalua si paralelizar 2-subagent
   o sequential single-subagent.
2. **Item ordering within sequential**: A0 -> A1 -> A2 -> A3 (de mas
   simple a mas complejo).
3. **Dispatch chain alternatives consideradas**: solo Item A2
   "headless detection raise" en v1.0.1; redesign profundo de la
   skill dispatch arquitectura (e.g., capability detection,
   non-interactive variants) deferido a v1.x.
4. **v1.0.1 own-cycle methodology**: el ciclo v1.0.1 mismo NO sufre
   de su propio bug porque estamos en sesion interactiva — el operator
   correra `/brainstorming` + `/writing-plans` interactivamente, luego
   el plugin para Checkpoint 2. Recovery path A3 se valida en v1.0.2
   cuando exista.

Brainstorming refinara estas decisiones basado en complejidad, risk,
y empirical findings de v1.0.0 cycle.
