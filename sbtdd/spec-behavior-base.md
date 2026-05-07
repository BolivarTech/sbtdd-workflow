# Especificacion base — sbtdd-workflow v1.0.2 (post-v1.0.1 ship + rolled-forward LOCKED items)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.2).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-06 post-v1.0.1 ship (commit `8fc0db4`, branch
> `feature/v1.0.2-bundle` branched off `main` HEAD = v1.0.1).
>
> v1.0.2 ships los items LOCKED rolled forward del ciclo v1.0.1 original
> (pre-pivot) — los pillars de "cross-check completion" que dependian de
> la dispatch chain de v1.0.1 estar arreglada antes de poderse ejercer
> end-to-end. Con v1.0.1 shipped (composite-signature tripwire INV-37 +
> permissive escenario regex + headless detection whitelist + recovery
> flag), v1.0.2 es el primer ciclo donde:
>
> 1. `/sbtdd spec --resume-from-magi` puede ejercerse empiricamente
>    end-to-end (P7 acceptance criterion del v1.0.1 a satisfacer).
> 2. `/sbtdd pre-merge` con `magi_cross_check: true` puede correr el
>    Loop 2 sobre el propio diff del plugin (own-cycle dogfood).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este
> documento NO lo reemplaza — agrega el delta v1.0.2 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder (verificable
> con grep word-boundary).
>
> v1.0.2 es **multi-pillar pero scope acotado** (4 items LOCKED + 3
> defensive secondary). G1 binding HARD: cap=3 sin INV-0 path para
> Checkpoint 2 (precedente cerrado por v0.5.0 + v1.0.0 + v1.0.1).
> G2 binding: scope-trim default si Loop 2 iter 3 no converge
> (defer secondary items a v1.0.3 si necesario).

---

## 1. Objetivo

**v1.0.2 = "Cross-check completion + own-cycle dogfood"**: completa los
items LOCKED del ciclo v1.0.1 original (rolled forward post-pivot) y
ejerce el plugin contra el propio repositorio del plugin via
`/sbtdd pre-merge` end-to-end por primera vez.

Tres clases de items:

### Clase 1 — Cross-check completion (LOCKED, primary pillar)

Items A-D rolled forward del v1.0.1 original (CHANGELOG `[1.0.1]`
Deferred section):

- **Item A — `scripts/cross_check_telemetry.py`** (originally v1.0.1
  LOCKED per balthasar Loop 2 iter 3 WARNING). Aggregator script que
  consume los artifacts `.claude/magi-cross-check/iter{N}-{ts}.json`
  generados por `_loop2_with_cross_check` (v1.0.0 Feature G shipped) y
  emite metricas agregadas: total findings KEEP / DOWNGRADE / REJECT
  por iter, false-positive rate de MAGI agents, agreement rate del
  meta-reviewer, distribucion de severities. Output legible para humano
  (markdown table) + machine-readable JSON.

- **Item B — Cross-check prompt diff threading verification (W-NEW1
  empirical close-out)** (originally v1.0.1 LOCKED per caspar Loop 1
  iter 2 CRITICAL fix). El v1.0.0 cycle shipped la implementation
  (`_compute_loop2_diff_with_meta` + threading via `_build_cross_check_prompt`
  con seccion `## Cumulative diff under review (truncated to 200KB)`)
  pero no la ejercio empiricamente — el v1.0.0 ciclo mismo no podia
  correr `/sbtdd pre-merge` por defectos en otros componentes. v1.0.2
  cierra el loop empiricamente: ejecuta el path completo en el dogfood
  cycle y confirma que el diff se incluye en el prompt enviado a
  `/requesting-code-review`. Si la implementation actual tiene gaps
  observables (ejemplo: `diff_truncated` siempre `false` porque cap=200KB
  es nunca alcanzado en bundles chicos), documentar como Known
  Limitation o ajustar.

- **Item C — H5-2 spec_lint enforcement at Checkpoint 2** (originally
  v1.0.1 LOCKED per caspar Loop 2 iter 3 WARNING). H5-1 (auto-gen
  scenario stubs in `superpowers_dispatch.invoke_writing_plans` prompt
  extension) shipped en v1.0.0 Feature H Group B option 5. v1.0.2
  agrega H5-2: lint rule que valida la calidad de los stubs y bloquea
  Checkpoint 2 si la spec falla checks mecanicos de well-formedness.
  Reglas mecanicas a implementar en `scripts/spec_lint.py`:
  - Cada bloque `**Escenario X: ...**` tiene Given / When / Then bullets
    no-vacios.
  - Cada Escenario tiene un identifier unico (X-N format).
  - Section headers monotonous (no skip de `## 2` a `## 5`).
  - Cero matches uppercase placeholder (re-enforcement de INV-27 a
    nivel mecanico — actualmente solo enforced via grep en spec-base).
  - Frontmatter docstring con `Generado YYYY-MM-DD a partir de ...`
    pattern para audit trail.
  Invocada desde `spec_cmd._run_magi_checkpoint2` antes de
  `magi_dispatch.invoke_magi`. Failures bloquean con `ValidationError`
  guidance-rich (que linea, que regla, como arreglar).

- **Item D — Own-cycle cross-check dogfood**. v1.0.2 ejecuta su propio
  `/sbtdd pre-merge` end-to-end con `magi_cross_check: true` set in
  `plugin.local.md` mid-cycle. Empirical validation del path completo
  Loop 1 (`/requesting-code-review`) + Loop 2 (`/magi:magi`) + cross-check
  meta-reviewer + telemetry script (Item A) consumiendo el artifact
  generado durante el propio cycle. Documentar findings empiricos en
  CHANGELOG `[1.0.2]` Process notes, incluyendo cualquier gap observable
  vs intended behavior.

### Clase 2 — Defensive secondary (LOCKED si scope holds)

- **Item E — P7 empirical proof-of-recovery for `--resume-from-magi`**
  (W5 caspar Loop 2 iter 1 disclosure de v1.0.1; rolled forward). v1.0.1
  shipped `--resume-from-magi` flag con structural validation, pero P7
  acceptance criterion ("en sesion Claude Code nueva, correr
  /brainstorming + /writing-plans manualmente, luego `/sbtdd spec
  --resume-from-magi` debe completar end-to-end") fue satisfied solo
  at unit-test level. v1.0.2 ejerce el path en una sesion fresh Claude
  Code (la sesion actual o una nueva) usando el ciclo v1.0.2 mismo como
  empirical case. Documentar resultado.

- **Item F — Meta-test enforcing `allow_interactive_skill=True` on
  direct `invoke_skill` callsites** (W4 caspar Loop 2 iter 2 de v1.0.1;
  rolled forward). v1.0.1's pre-A2 audit migro 3 production callsites
  + 4 test callsites a pasar el override explicito; v1.0.2 agrega
  meta-test (AST-based via `ast.parse` + walking, o grep-based con
  pattern strict) que escanea `skills/sbtdd/scripts/` + `tests/` y
  asserta:
  - Toda call directa a `invoke_skill(skill="brainstorming", ...)` o
    `invoke_skill(skill="writing-plans", ...)` pasa
    `allow_interactive_skill=True`.
  - Wrappers (`brainstorming`, `writing_plans`) son la unica via
    "permitida" de invocar Skills interactivos sin el override
    explicito en el callsite (porque el wrapper internamente lo
    pasa).
  - Test fails con mensaje guidance-rich que incluye file:line del
    callsite ofensor.
  Pattern: similar al test `test_changelog.py` cross-artifact alignment.
  Regression-guards futuro: si alguien agrega nuevo callsite y olvida
  el override, falla en CI.

- **Item G — Per-module coverage threshold via `coverage.py`** (I2 caspar
  Loop 2 iter 1 de v1.0.1; rolled forward). v1.0.1 shipped sin tracking
  formal de per-module coverage; v1.0.2 agrega:
  - `pytest-cov` agregado como dev dependency.
  - `pyproject.toml` `[tool.coverage]` config con per-module exclude
    list para modulos que son legitimamente bajo-coverage (ejemplo:
    template files, scripts triviales).
  - `make verify` extendido con `pytest --cov=skills/sbtdd/scripts/
    --cov-report=term-missing --cov-fail-under=85`.
  - CHANGELOG `[1.0.2]` documenta el baseline coverage observado por
    modulo y excludes justificados.

### Criterio de exito v1.0.2

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.1 -> 1.0.2.
- Tests baseline 1059 + 1 skipped preservados sin regresion + ~30-50
  nuevos (Item A telemetry: ~5-8; Item C spec_lint: ~10-15; Item F
  meta-test: ~3-5; Item G coverage: ~2-3 wiring tests; Items B/D/E
  son empirical, ~5-10 tests entre regression guards y validation).
  Spec sec.10.4 NF-B target: +30-50 nuevos = 1089-1109 final.
- `make verify` runtime <= 160s (NF-A target; v1.0.1 baseline 127s;
  v1.0.2 expected slight increase from coverage instrumentation +
  spec_lint check at Checkpoint 2 + nuevos tests).
- Coverage baseline >= 85% per-module documentado.
- **Empirical validation del path completo de cross-check + own-cycle
  dogfood** documented en CHANGELOG `[1.0.2]` Process notes.
- v1.0.1 LOCKED commitments del CHANGELOG `[1.0.1]` Deferred section
  enteramente cerrados (telemetry, diff threading, spec_lint, dogfood,
  meta-test, coverage) excepto los explicitamente rolled forward a
  v1.0.4 (`_SUBPROCESS_INCOMPATIBLE_SKILLS` audit, 600s subprocess
  hang full LOUD-FAST fix).
- G1 binding respetado: cap=3 HARD para Checkpoint 2; sin INV-0 path.
- G2 binding respetado: si Loop 2 iter 3 no converge clean,
  scope-trim default (defer Items E/F/G a v1.0.3 si necesario).

### Out of scope v1.0.2 (rolled forward a v1.0.3)

- MAGI gate template alignment audit vs `D:\jbolivarg\BolivarTech\AI_Tools\
  magi-gate-template.md` (sole pillar v1.0.3 per memory
  `project_v103_template_alignment_audit.md`).

### Out of scope v1.0.2 (rolled forward a v1.0.4)

- Parallel task dispatcher (memory
  `project_v104_parallel_task_dispatcher.md`).
- Real headless detection (env var + `os.isatty`) replacing v1.0.1's
  whitelist + override (memory `project_v104_subprocess_headless_detection.md`).
- `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit + criteria for set
  membership (bundled with v1.0.4 LOCKED real headless detection).
- 600s subprocess hang full LOUD-FAST fix (bundled with v1.0.4
  headless detection).

### Out of scope v1.0.2+ (rolled forward a v1.1.0+)

- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7 (opt-in flags).
- Migration tool real test (Feature I shipped en v1.0.0 ships solo el
  skeleton; primera migration v1 -> v2 sera v1.1.0+).
- AST-based dead-helper detector codification (R11 sweep methodology).
- W8 Windows file-system retry-loop (accepted-risk per spec sec.4.4.5).
- `_read_auto_run_audit` skeleton wiring.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

---

## 2. Alcance v1.0.2 — items LOCKED post-v1.0.1 ship

### 2.1 Item A — Cross-check telemetry aggregation script

**Problema**: v1.0.0 Feature G ships `_loop2_with_cross_check` que
emite `.claude/magi-cross-check/iter{N}-{timestamp}.json` por iter de
Loop 2 con shape:

```json
{
  "iter": 1,
  "timestamp": "2026-05-XX...",
  "magi_verdict": "GO_WITH_CAVEATS",
  "cross_check_decisions": [
    {"original_index": 0, "decision": "KEEP", "rationale": "...",
     "recommended_severity": null, "agent": "melchior",
     "title": "...", "severity": "WARNING"},
    ...
  ],
  "diff_truncated": false,
  "diff_original_bytes": 12345,
  "diff_cap_bytes": 200000
}
```

Sin un script de aggregation, el operador tiene que parsear los
JSON manualmente para entender meta-trends (false-positive rate,
agreement rate, distribucion).

**Entrega v1.0.2**:

- Nuevo script `scripts/cross_check_telemetry.py` standalone
  (no `skills/sbtdd/scripts/` — es tooling de developer/operator,
  no parte del runtime path del plugin).
- CLI: `python scripts/cross_check_telemetry.py --root <path>
  [--cycle <pattern>] [--format markdown|json]`
- Defaults: `--root .claude/magi-cross-check`, `--cycle "iter*-*.json"`,
  `--format markdown`.
- Output markdown table:
  - Total iters analizados.
  - Distribucion KEEP / DOWNGRADE / REJECT por iter.
  - Per-agent false-positive rate (REJECT count / total findings).
  - Per-severity distribution (CRITICAL / WARNING / INFO).
  - Agreement rate (% findings donde meta-reviewer matchea MAGI
    severity).
  - Diff truncation rate (% iters donde `diff_truncated=true`).
- Output JSON: misma data en machine-readable shape para downstream
  consumption.
- Error handling: `FileNotFoundError` cuando dir no existe; mensaje
  guidance-rich. Malformed JSON files skipped con stderr breadcrumb
  (no abort).
- Tests `tests/test_cross_check_telemetry.py`:
  - Happy path con fixtures de ejemplo.
  - Empty dir tolerated (output: "No iterations found").
  - Malformed JSON skipped con breadcrumb.
  - Markdown output valid (parseable como tabla).
  - JSON output valid (json.loads succeeds).

### 2.2 Item B — Cross-check diff threading empirical close-out

**Problema**: v1.0.0 ship-time documenta `diff=""` fallback en
`_loop2_cross_check` ("no `_compute_loop2_diff` helper exists in the
codebase yet"). Mid-cycle iter 2->3 fix shipped el helper +
threading; v1.0.0 own-cycle no pudo ejercer el path empiricamente.

**Estado actual** (verificado 2026-05-06):

- `_compute_loop2_diff_with_meta` exists (`pre_merge_cmd.py` line ~1111).
- `_build_cross_check_prompt(diff, verdict, findings)` accepts diff
  parameter (line ~1192) y embeds en `## Cumulative diff under review
  (truncated to 200KB)` section cuando `diff != ""`.
- Threading via `_loop2_with_cross_check` line ~1484
  (`prompt = _build_cross_check_prompt(diff, verdict, findings)`).

**Entrega v1.0.2**:

- Empirical validation: durante Item D dogfood, capturar el prompt
  literal enviado a `/requesting-code-review` y verificar que include
  el diff section. Smoke test al mid-cycle.
- Documentar en CHANGELOG `[1.0.2]` Process notes:
  - Tamano observado de cumulative diff en el v1.0.2 cycle.
  - Si se hit el cap de 200KB (likely no para bundle chico).
  - Si meta-reviewer references file:line en sus rationales (signal
    de que diff embedding se esta usando).
- Si la implementation tiene gap observable (ejemplo: cap demasiado
  bajo, prompt format ambiguo), apply mini-cycle TDD fix.
- Regression test `tests/test_pre_merge_cross_check.py::
  test_cross_check_prompt_embeds_diff_when_provided`: monkeypatch
  `_dispatch_requesting_code_review` para capturar el prompt;
  asserta `## Cumulative diff under review` substring presente
  cuando `diff != ""`, ausente cuando `diff == ""`.

### 2.3 Item C — H5-2 spec_lint enforcement at Checkpoint 2

**Problema**: v1.0.0 H5-1 ships auto-gen scenario stubs en el prompt
de `/writing-plans` (Feature H Group B option 5), pero no hay
mechanical enforcement de la calidad de la spec generada. Specs
malformadas (escenarios sin Given/When/Then, identifiers duplicados,
section headers skip) pasan a Checkpoint 2 y consumen MAGI iter
budget en findings mecanicos que un lint check podria catch
upfront.

**Entrega v1.0.2**:

- Nuevo modulo `skills/sbtdd/scripts/spec_lint.py` con interfaz:
  ```python
  def lint_spec(path: Path) -> list[LintFinding]:
      """Run mechanical lint checks against spec-behavior.md.

      Returns list of findings (empty = clean). Each finding has
      file path, line number, rule id, severity, message.
      """
  ```
- 5 lint rules a implementar (cada una con su propio test):
  1. **R1 — escenario blocks well-formed**: cada `**Escenario X: ...**`
     o `### Escenario X: ...` o `## Escenario X: ...` block tiene
     Given / When / Then bullets no-vacios. Bullet pattern:
     `> **Given** ...`, `> **When** ...`, `> **Then** ...`.
  2. **R2 — identifiers unicos**: cada Escenario tiene un identifier
     X-N (alphanumeric + dash) y dos escenarios no comparten id.
  3. **R3 — section headers monotonous**: si `## 2.` exists, debe
     existir `## 1.` o ser primer section. No skip de `## 2` a
     `## 5`.
  4. **R4 — INV-27 mechanical**: cero matches uppercase placeholder
     (los tres tokens uppercase enforced por
     `spec_cmd._INV27_RE` con word-boundary). Ya enforced en
     spec-base via `_validate_spec_base_no_placeholders`; R4 lo
     extiende a spec-behavior.md (output de brainstorming) y
     plan-tdd-org.md (output de writing-plans).
  5. **R5 — frontmatter docstring**: spec-behavior.md y
     plan-tdd-org.md inician con frontmatter docstring que include
     `Generado YYYY-MM-DD` line + reference a source artifact.
- Integration en `spec_cmd._run_magi_checkpoint2`: invoca
  `lint_spec(spec_behavior_path)` y `lint_spec(plan_org_path)`
  antes de `magi_dispatch.invoke_magi`. Findings con severity
  `error` raise `ValidationError` con guidance message; severity
  `warning` emite stderr breadcrumb pero no bloquea.
- CLI standalone: `python -m skills.sbtdd.scripts.spec_lint
  <path> [--severity error|warning|info]` para invocacion manual.
- Tests `tests/test_spec_lint.py`:
  - 5 rule tests (uno por R1-R5) con fixture spec malformada.
  - Happy path con fixture clean.
  - Integration test: `_run_magi_checkpoint2` aborts cuando
    spec-behavior.md falla R1.
- Tests `tests/test_spec_cmd.py` extension:
  - Regression: existing tests de `_run_magi_checkpoint2`
    siguen pasando (lint clean en fixtures).

### 2.4 Item D — Own-cycle cross-check dogfood

**Problema**: v1.0.0 ships `_loop2_with_cross_check` con
`magi_cross_check: false` default. v1.0.1 cycle no pudo ejercer
porque dispatch chain estaba rota. v1.0.2 es el primer cycle donde
toggle a `true` mid-cycle es viable.

**Entrega v1.0.2**:

- Pre-merge phase del v1.0.2 cycle:
  - Set `magi_cross_check: true` en `.claude/plugin.local.md`
    antes de invocar `/sbtdd pre-merge`.
  - Run `/sbtdd pre-merge` end-to-end (Loop 1 + Loop 2 + cross-check).
  - Capturar artifacts `.claude/magi-cross-check/iter{N}-*.json`.
  - Run telemetry script (Item A) sobre los artifacts.
  - Document findings empiricos en CHANGELOG `[1.0.2]` Process
    notes:
    - Cuantos iters Loop 2 (esperado: 1-2 para single-pillar
      bundle).
    - Cross-check decision distribution.
    - Meta-reviewer agreement rate vs MAGI verdicts.
    - Cualquier gap observable (ejemplo: meta-reviewer no
      references file:line; diff embedding ambiguo; carry-forward
      block missing en iter 2+).
- Si Item D surfaces production bug en cross-check path:
  abort cycle, escalate al usuario, evaluate scope (mini-fix in
  v1.0.2 vs new cycle v1.0.2.1).

### 2.5 Item E — P7 empirical proof-of-recovery (defensive)

**Problema**: v1.0.1 P7 ("`/sbtdd spec --resume-from-magi` completes
end-to-end") satisfied solo at unit-test level. Real-world
end-to-end exercise pendiente.

**Entrega v1.0.2**:

- Mid-cycle, en una sesion Claude Code fresh (puede ser la sesion
  actual o nueva), validar el recovery path:
  1. Generar v1.0.2 spec-behavior.md interactivamente (this
     session via `/brainstorming` o hand-craft).
  2. Generar plan-tdd-org.md interactivamente via
     `/writing-plans` (o hand-craft).
  3. Set `magi_cross_check: true` para Item D parallel.
  4. Invoke `/sbtdd spec --resume-from-magi` desde esta sesion.
  5. Verify: (a) skipea brainstorming/writing-plans dispatch,
     (b) ejecuta MAGI Checkpoint 2 sobre artifacts existentes,
     (c) escribe state file + commit chore: si verdict >=
     GO_WITH_CAVEATS.
- Document en CHANGELOG `[1.0.2]` Process notes:
  - Resultado del exercise (success / failure).
  - Tiempo wall-clock end-to-end.
  - Cualquier gap observable (ejemplo: structural validation
    too strict, mensaje de error confuso).

### 2.6 Item F — Meta-test enforcing `allow_interactive_skill=True`

**Problema**: v1.0.1's pre-A2 audit migro callsites point-in-time;
sin enforcement automatizado, futuro contributor puede agregar
nuevo callsite sin override y silently break A2's whitelist
semantic.

**Entrega v1.0.2**:

- Nuevo test `tests/test_invoke_skill_callsites_audit.py`:
  - AST walk via `ast.parse(file.read_text())` sobre todos los
    `.py` files en `skills/sbtdd/scripts/` y `tests/`.
  - Para cada `Call` node a `invoke_skill(...)` (matched via
    `node.func.attr == "invoke_skill"` + import alias resolution):
    - Si `keyword skill=` value matchea string en
      `_SUBPROCESS_INCOMPATIBLE_SKILLS` literal set, asserta
      `keyword allow_interactive_skill=` exists con value `True`
      (`ast.Constant`).
  - Excludes: `superpowers_dispatch.py` mismo (donde el set y
    wrappers viven; wrappers son safe path).
  - Failure mode: AssertionError con file:line + recomendacion
    "add `allow_interactive_skill=True` to this callsite, or use
    the wrapper `superpowers_dispatch.brainstorming` /
    `writing_plans`".
- Tests `tests/test_invoke_skill_callsites_audit.py::
  test_meta_test_catches_regression`:
  - Synthetic fixture con call site sin override; meta-test
    debe fail con mensaje guidance-rich.
- Excluded paths configured via `_EXCLUDED_FILES` constant in
  the meta-test module (ej. test fixtures que intentionally
  exercise the gate without the override).

### 2.7 Item G — Per-module coverage threshold

**Problema**: v1.0.1 ships sin tracking formal de per-module
coverage. Modulos pueden tener bajo coverage silently.

**Entrega v1.0.2**:

- `pyproject.toml` agrega:
  ```toml
  [project.optional-dependencies]
  dev = [
      ...
      "pytest-cov>=4.1",
  ]

  [tool.coverage.run]
  source = ["skills/sbtdd/scripts"]
  omit = [
      "skills/sbtdd/scripts/__init__.py",
      "templates/*",
  ]

  [tool.coverage.report]
  fail_under = 85
  show_missing = true
  exclude_lines = [
      "pragma: no cover",
      "if TYPE_CHECKING:",
      "raise NotImplementedError",
      "def __repr__",
  ]
  ```
- `Makefile` `verify` target extendido:
  ```makefile
  verify: test lint format typecheck coverage

  coverage:
      pytest --cov=skills/sbtdd/scripts --cov-report=term-missing \
          --cov-fail-under=85
  ```
- CHANGELOG `[1.0.2]` documenta:
  - Per-module coverage baseline (tabla de modulo / %coverage).
  - Excludes justificados (ejemplo: `templates/` solo contiene
    template files).
  - Gap analysis: si algun modulo cae bajo 85%, plan v1.0.x para
    raise.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.2 NO propone
nuevos invariantes (los items son additive: telemetry, lint,
testing, observability — no cambian semantica core).

Critical durante implementacion v1.0.2:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default
  OR exact phrase override. v1.0.2 multi-pillar bundle podria
  necesitar scope-trim si Loop 2 hits structural findings — defer
  Items E/F/G a v1.0.3 si necesario.
- **Multi-pillar pero scope acotado** — 7 items totales pero todos
  son adicion de scripts/lint/tests, no cambios semanticos.
  Ningun item toca `pre_merge_cmd.py` core path (solo Item B verifica
  empiricamente, no muta).
- **Invocation-site tripwires**: cualquier helper nuevo (telemetry
  parser, spec_lint, meta-test) ships con invocation-site tripwire
  test ANTES de close-task.
- **`/receiving-code-review` sin excepcion**: every Loop 2 iter
  MUST run skill on findings (carry-forward from v1.0.1).
- **Empirical validation requerida**: Items B + D + E son
  empirical-only (no ship sin observed dogfood result).

### Stack y runtime

Sin cambios vs v1.0.1:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot
  paths (telemetry script + spec_lint son tooling, no hot path).
- Dependencias externas runtime: git, tdd-guard, superpowers, magi
  (>= 2.2.x), claude CLI.
- Dependencias dev: pytest, pytest-asyncio, ruff, mypy, pyyaml,
  **pytest-cov >= 4.1** (nuevo en v1.0.2).
- Licencia dual MIT OR Apache-2.0.

### Reglas duras no-eludibles (sin override)

- INV-0 autoridad global.
- INV-27 spec-base sin uppercase placeholder markers (este doc cumple).
- INV-37 (v1.0.1) composite-signature output validation tripwire.
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).
- G1 binding cap=3 HARD para Checkpoint 2 (CHANGELOG `[1.0.0]`,
  precedente cerrado v1.0.1).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F99 v1.0.1; v1.0.2 starts at F100.)

### Item A — telemetry

**F100**. `scripts/cross_check_telemetry.py` standalone CLI (no parte
de `skills/sbtdd/scripts/` runtime path).

**F101**. CLI flags `--root`, `--cycle`, `--format` con defaults
sensibles.

**F102**. Markdown output: tabla con totals + per-iter breakdown +
agreement rate + truncation rate.

**F103**. JSON output: same data shape parseable via `json.loads`.

**F104**. Error handling: missing dir + malformed JSON tolerated.

### Item B — diff threading empirical

**F105**. Regression test asserta `## Cumulative diff under review`
substring presente en prompt cuando `diff != ""`, ausente cuando
empty.

**F106**. CHANGELOG `[1.0.2]` Process notes documenta empirical
diff size observed durante Item D dogfood.

### Item C — spec_lint

**F107**. Modulo `skills/sbtdd/scripts/spec_lint.py` con `lint_spec`
function returning `list[LintFinding]`.

**F108**. R1-R5 rules implementadas (escenario well-formed,
identifiers unicos, headers monotonous, INV-27 mechanical,
frontmatter docstring).

**F109**. `LintFinding` dataclass con file path, line number, rule
id, severity, message.

**F110**. Integration en `spec_cmd._run_magi_checkpoint2` invoca
lint sobre spec-behavior.md y plan-tdd-org.md ANTES de
`magi_dispatch.invoke_magi`.

**F111**. Findings con severity `error` raise `ValidationError`;
severity `warning` emite stderr breadcrumb (no bloquea).

**F112**. CLI standalone `python -m skills.sbtdd.scripts.spec_lint`
para invocacion manual.

### Item D — dogfood

**F113**. v1.0.2 cycle runs `/sbtdd pre-merge` end-to-end con
`magi_cross_check: true`.

**F114**. Telemetry script (Item A) consumed en mid-cycle sobre
generated artifacts.

**F115**. CHANGELOG `[1.0.2]` Process notes documenta dogfood
findings (iter count, decision distribution, agreement rate,
gaps).

### Item E — recovery flag empirical

**F116**. v1.0.2 cycle exercises `/sbtdd spec --resume-from-magi`
end-to-end mid-cycle.

**F117**. CHANGELOG `[1.0.2]` Process notes documenta resultado
(success/failure + wall-clock + gaps).

### Item F — meta-test

**F118**. Test `tests/test_invoke_skill_callsites_audit.py` AST walk
sobre `skills/sbtdd/scripts/` + `tests/`.

**F119**. Failure mode: AssertionError con file:line + remediation
guidance.

**F120**. Synthetic fixture asserta meta-test catches regression.

### Item G — coverage

**F121**. `pyproject.toml` agrega `pytest-cov` dev dep + coverage
config.

**F122**. `Makefile` `verify` target invoca `pytest --cov ... --cov-fail-under=85`.

**F123**. CHANGELOG `[1.0.2]` documenta per-module coverage baseline
+ excludes justificados.

### Requerimientos no-funcionales (NF)

**NF29**. `make verify` runtime <= 160s (v1.0.1 baseline 127s; v1.0.2
expected slight increase from coverage instrumentation + spec_lint
checkpoint check + nuevos tests; soft-target <= 145s).

**NF30**. v1.0.1 plans (with state file post-v1.0.1 schema) parse
correctly; no migration required for v1.0.2.

**NF31**. Per-module coverage >= 85% on `skills/sbtdd/scripts/`
modules (excludes documented).

**NF32**. Cross-check telemetry script handles N >= 100 iter files
without quadratic blowup (linear pass, single read per file).

---

## 5. Scope exclusions

Out-of-scope v1.0.2 (rolled forward a v1.0.3):

- **MAGI gate template alignment audit** vs `magi-gate-template.md` (sole
  pillar v1.0.3 per memory `project_v103_template_alignment_audit.md`).

Out-of-scope v1.0.2 (rolled forward a v1.0.4):

- Parallel task dispatcher.
- Real headless detection (env var + os.isatty replacing whitelist).
- `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit + criteria.
- 600s subprocess hang full LOUD-FAST fix.

Out-of-scope v1.0.2+ (rolled forward a v1.1.0+):

- INV-31 default flip dedicated cycle.
- GitHub Actions CI workflow.
- Group B options 1, 3, 4, 6, 7.
- Migration tool real test (Feature I primer migration v1->v2).
- AST-based dead-helper detector (R11 sweep methodology codification).
- W8 Windows file-system retry-loop.
- `_read_auto_run_audit` skeleton wiring.
- Spec sec.7.1.3 G2 amendment.
- `magi_cross_check` default-flip a `true`.

---

## 6. Criterios de aceptacion finales

v1.0.2 ship-ready cuando:

### 6.1 Functional Items A-G

- **F1**. F100-F104: telemetry script exists, CLI flags, markdown +
  JSON output, error handling.
- **F2**. F105-F106: diff threading regression test + empirical
  observation documented.
- **F3**. F107-F112: spec_lint module + 5 rules + Checkpoint 2
  integration + CLI.
- **F4**. F113-F115: dogfood cycle ran + telemetry consumed +
  Process notes.
- **F5**. F116-F117: recovery flag empirical exercised + Process
  notes.
- **F6**. F118-F120: meta-test AST walk + regression fixture.
- **F7**. F121-F123: coverage config + Makefile + baseline doc.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 85%, runtime <= 160s. Soft-target
  <= 145s.
- **NF-B**. Tests baseline 1059 + 1 skipped preservados + ~30-50
  nuevos = ~1089-1109.
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en archivos modificados/nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados:
  `spec_cmd.py` (Item C integration), `pre_merge_cmd.py` (Item B
  regression test only), nuevos modulos (`spec_lint.py`,
  `cross_check_telemetry.py`, meta-test).

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.2]` entry written con secciones Added /
  Changed / Process notes + dogfood empirical findings + recovery
  empirical findings + per-module coverage baseline + cross-check
  telemetry observations.
- **P4**. Version bump 1.0.1 -> 1.0.2 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.2` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. Empirical proof-of-recovery for `--resume-from-magi`
  ejercido end-to-end mid-cycle (cierra v1.0.1's deferred P7).
- **P8**. Empirical proof-of-cross-check: own-cycle dogfood ran +
  telemetry artifacts produced + Process notes document
  observations.

### 6.4 Distribution

- **D1**. Plugin instalable.
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.2 ship + 4 LOCKED items).
- **D3**. Nuevos modulos documentados:
  - `cross_check_telemetry.py` en README + SKILL.md.
  - `spec_lint.py` en README + SKILL.md (Checkpoint 2 integration).
  - Coverage threshold en CONTRIBUTING.md (si existe) o README.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: **pytest-cov >= 4.1** (Item G).

---

## 8. Risk register v1.0.2

- **R1**. Item D dogfood puede surfacear production bug en
  cross-check path no-cubierto por v1.0.0 unit tests. Mitigation:
  if surfaces, mini-cycle TDD fix in v1.0.2 if scope minimal;
  otherwise abort + new cycle v1.0.2.1.
- **R2**. Item C spec_lint R1-R5 rules pueden ser too strict y
  rechazar specs legitimas (especialmente R3 monotonous headers).
  Mitigation: empirical validation contra spec v1.0.0, v1.0.1,
  v1.0.2 (este doc); ajustar R3 a "warning" severity inicialmente,
  promote a "error" en v1.0.3 despues de empirical confidence.
- **R3**. Item G coverage <85% baseline puede surfacear modulos
  legitimamente bajo-coverage (ejemplo: error paths dificiles de
  exercise). Mitigation: documented excludes via
  `[tool.coverage.report] exclude_lines` + per-module threshold
  (algunos modulos pueden setear lower threshold con justification).
- **R4**. Item E recovery exercise puede fail si v1.0.2 own-cycle
  drives `/brainstorming` interactivamente Y `--resume-from-magi`
  mid-cycle. Mitigation: empirical validation con fallback a manual
  `python skills/magi/scripts/run_magi.py` (precedente v1.0.0,
  v1.0.1 documented en spec sec.6.5).
- **R5**. Item F meta-test puede have false-positives en wrappers
  internos de `superpowers_dispatch.py` si AST walk es too broad.
  Mitigation: explicit `_EXCLUDED_FILES` con `superpowers_dispatch.py`
  + comprehensive synthetic fixtures.
- **R6**. Bundle scope multi-pillar con 7 items aumenta riesgo de
  Loop 2 non-convergence vs v1.0.1 single-pillar (4 items). G2
  binding mitigates: scope-trim a 4 items LOCKED (A-D) + defer
  defensive items (E-G) a v1.0.3 si Loop 2 iter 3 no converge.
- **R7**. Telemetry script (Item A) puede consumir artifacts
  malformados de pre-v1.0.0 cycles si operator runs en project con
  legacy `.claude/magi-cross-check/`. Mitigation: skip malformed
  files con stderr breadcrumb (no abort); regression test cubre
  escenario.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.1 LOCKED commitments rolled forward a v1.0.2: ver CHANGELOG
  `[1.0.1]` Deferred section + Process notes rolled-forward bullets.
- v1.0.0 deferred items context: ver CHANGELOG `[1.0.0]` Deferred
  section.
- v1.0.3 LOCKED template alignment audit: memory
  `project_v103_template_alignment_audit.md` (sole pillar, ~1-2
  days, sequenced first so v1.0.4+ runs against template-aligned
  baseline).
- v1.0.4 LOCKED items: memory
  `project_v104_parallel_task_dispatcher.md` +
  `project_v104_subprocess_headless_detection.md`.
- v1.0.0 Feature G cross-check: `pre_merge_cmd._loop2_with_cross_check`
  shipped en v1.0.0 con `magi_cross_check: false` default; v1.0.2
  Item D primer empirical exercise con toggle a `true`.
- v1.0.1 INV-37: composite-signature tripwire en `spec_cmd._run_spec_flow`
  (referencia para Item C lint integration en mismo flow).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con grep). Listo como input para
`/brainstorming`.

**Methodology v1.0.2 own-cycle**: per CLAUDE.local.md §1 Flujo de
especificacion + v1.0.1 Process notes precedent, brainstorming se
correra en sesion interactiva (esta sesion), NO via `claude -p`
subprocess. v1.0.1 ship A2 whitelist evita el subprocess hang
automaticamente; A3 `--resume-from-magi` provee recovery path si
operator necesita producir artifacts manualmente.

Decisiones pendientes clave para brainstorming:

1. **Subagent partition**: 7 items, multi-pillar pero acotado.
   Posibles particiones disjoint:
   - **Single subagent sequential**: ~5-7 dias wall-time.
   - **2-subagent parallel** (precedent v0.4.0, v0.5.0, v1.0.0):
     Track Alpha = Items A + B + D (cross-check completion +
     telemetry + dogfood, todos tocan `pre_merge_cmd.py` o
     consumen sus artifacts). Track Beta = Items C + F + G
     (spec_lint en `spec_cmd.py` + meta-test orthogonal +
     coverage wiring). Item E (recovery empirical) es methodology
     mid-cycle, no requiere subagent. Disjoint surfaces.
   - **3-subagent parallel** (riesgo overhead): Track Alpha =
     A + B + D, Track Beta = C, Track Gamma = F + G.
   Brainstorming evalua basado en complejidad estimada por item
   y riesgo de coordination.

2. **Item ordering within pillar**:
   - Track Alpha sequential: A (telemetry) → B (regression test) →
     D (mid-cycle dogfood after pre-merge phase).
   - Track Beta sequential: C (spec_lint module) → integration en
     spec_cmd → meta-test (F) → coverage (G).

3. **MAGI Checkpoint 2 budget allocation**: bundle multi-pillar pero
   scope-acotado por item. Esperamos converger en 1-2 iters; iter
   3 triggers G2 scope-trim default (defer E/F/G a v1.0.3 if
   needed).

4. **Loop 2 cross-check enabled mid-cycle**: setting
   `magi_cross_check: true` en `plugin.local.md` antes de
   `/sbtdd pre-merge` es Item D ENTREGA — cycle valida su propia
   feature. R1 risk: production bug surfaced; mitigated by
   ability to mini-cycle fix or split a v1.0.2.1.

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0 + v1.0.1 precedents.
