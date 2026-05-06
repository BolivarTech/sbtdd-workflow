# BDD overlay — sbtdd-workflow v1.0.2

> Generado 2026-05-06 a partir de `sbtdd/spec-behavior-base.md` v1.0.2.
> Hand-crafted en sesion interactiva (sesion Claude Code activa, NO via
> `claude -p /brainstorming` subprocess) por consistencia con
> precedente v1.0.1 — el A2 whitelist shipped en v1.0.1 raisearia
> `PreconditionError` automatically si se intentase, pero la
> hand-craft pattern es metodologia validada y robusta.
>
> v1.0.2 ships los items LOCKED rolled forward del ciclo v1.0.1
> original (pre-pivot) + items defensive secondary E/F/G del
> CHANGELOG `[1.0.1]` Deferred section. Brainstorming refinement
> 2026-05-06 reclasifica D + E como methodology activities (no plan
> task TDD-cycle); plan tasks bona-fide = A + B + C + F + G (5 items).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex (los tres tokens
> uppercase enforced en spec-base + extension a este artifact via
> Item C R4).

---

## 1. Resumen ejecutivo

**Objetivo v1.0.2**: completar los items LOCKED del ciclo v1.0.1
original (rolled forward post-pivot) + items defensive de v1.0.1
Loop 2 iter 1-2 disclosure, y ejercer el plugin contra el propio
repositorio del plugin via `/sbtdd pre-merge` end-to-end por
primera vez.

Tres clases de work units:

- **Plan tasks bona-fide (5 items)**: A, B, C, F, G — TDD-cycle
  tasks con archivos production + tests adicionales.
- **Methodology activities (2 items)**: D (own-cycle dogfood), E
  (P7 recovery empirical) — orchestrator-driven, sin plan task.
- **Process notes (CHANGELOG)**: documentation de findings empiricos
  de D + E.

Decisiones de brainstorming 2026-05-06:

- **Q1 — Subagent partition**: 2-track parallel.
  - Track Alpha (subagent #1, sequential A → B): cross-check
    completion + telemetry. ~6-9h wall-time.
  - Track Beta (subagent #2, sequential C → F → G): spec_lint +
    meta-test + coverage. ~16-25h wall-time.
  - Mid-cycle methodology (orchestrator, no subagent): D + E.
- **Q2 — Defensive items E/F/G handling**: Plan tasks =
  A + B + C + F + G; D + E como methodology Process notes (no plan
  task). Reduces visible scope a MAGI sin perder capability.
- **Q3 — `spec_lint` R3 severity**: warning inicial; promote a
  error en v1.0.5+ despues de empirical data sobre false-positive
  rate.
- **Q4 — Coverage threshold**: measure baseline first, set
  `--cov-fail-under=floor(baseline) - 2%`. Final value documented
  en task close de Item G + CHANGELOG `[1.0.2]`.

**Criterio de exito v1.0.2 (refinado vs spec-base)**:

- Tests baseline 1059 + 1 skipped preservados + ~30-35 nuevos =
  ~1089-1094 final (revisado vs spec-base 30-50, refleja D+E como
  methodology).
- `make verify` runtime <= 160s (NF-A); soft-target <= 145s.
- Coverage threshold = `floor(baseline) - 2%` (medido en task close
  de Item G).
- Empirical validation del path completo cross-check + own-cycle
  dogfood documentado en CHANGELOG `[1.0.2]` Process notes (Item D).
- Empirical proof-of-recovery del flag `--resume-from-magi`
  documentado en CHANGELOG `[1.0.2]` Process notes (Item E).
- v1.0.1 LOCKED commitments del CHANGELOG `[1.0.1]` Deferred
  section enteramente cerrados excepto rolled-forward a v1.0.4.
- G1 binding respetado: cap=3 HARD para Checkpoint 2; sin INV-0.
- G2 binding respetado: si Loop 2 iter 3 no converge clean,
  scope-trim default (defer F+G a v1.0.3).

---

## 2. Items LOCKED

### 2.1 Item A — Cross-check telemetry aggregation script

**Track**: Alpha (subagent #1).

**Archivos**:
- `scripts/cross_check_telemetry.py` (new, standalone tooling).
- `tests/test_cross_check_telemetry.py` (new).

**Interface**:

```python
def aggregate(
    root: Path,
    cycle_pattern: str = "iter*-*.json",
) -> TelemetryReport:
    """Aggregate cross-check artifacts under root.

    Args:
        root: Directory containing iter{N}-{ts}.json artifacts.
        cycle_pattern: Glob pattern (default matches v1.0.0
            Feature G output naming).

    Returns:
        TelemetryReport with totals, per-iter breakdown, agreement
        rate, truncation rate.

    Raises:
        FileNotFoundError: root does not exist (guidance-rich
            message). Malformed individual JSON files are skipped
            with stderr breadcrumb (no abort).
    """
```

**CLI**:

```
python scripts/cross_check_telemetry.py [--root <path>] \
    [--cycle <pattern>] [--format markdown|json]
```

Defaults: `--root .claude/magi-cross-check`,
`--cycle "iter*-*.json"`, `--format markdown`.

**Output markdown** (human-readable tabla):
- Total iters analizados.
- Distribucion KEEP / DOWNGRADE / REJECT por iter.
- Per-agent false-positive rate (REJECT count / total findings).
- Per-severity distribution (CRITICAL / WARNING / INFO).
- Agreement rate (% findings donde meta-reviewer matchea MAGI
  severity).
- Diff truncation rate (% iters donde `diff_truncated=true`).

**Output JSON** (machine-readable):

```json
{
  "total_iters": 5,
  "decision_distribution": {"KEEP": 12, "DOWNGRADE": 3, "REJECT": 2},
  "per_iter": [
    {"iter": 1, "verdict": "GO_WITH_CAVEATS",
     "decisions": {"KEEP": 8, "DOWNGRADE": 2, "REJECT": 1},
     "agents": {"melchior": 4, "balthasar": 3, "caspar": 4},
     "severity": {"CRITICAL": 0, "WARNING": 7, "INFO": 4},
     "diff_truncated": false, "diff_original_bytes": 12345}
  ],
  "agreement_rate": 0.71,
  "truncation_rate": 0.0
}
```

**Error handling**:
- `FileNotFoundError` cuando dir no existe; mensaje guidance-rich
  ("expected `.claude/magi-cross-check/` from v1.0.0 Feature G
  artifacts").
- Malformed JSON files skipped con stderr breadcrumb identificando
  file path + parse error; no abort.
- Empty dir tolerated (output: "No iterations found").

### 2.2 Item B — Cross-check diff threading regression test

**Track**: Alpha (subagent #1, after Item A).

**Estado actual** (verificado 2026-05-06; clarificado iter 1 W8 fix):

- **Wiring shipped en v1.0.0** (mid-cycle iter 2→3 fix):
  `_compute_loop2_diff_with_meta` existe en `pre_merge_cmd.py:1111`;
  `_build_cross_check_prompt(diff, verdict, findings)` accepts diff
  parameter en `pre_merge_cmd.py:1192` y embeds en
  `## Cumulative diff under review (truncated to 200KB)` section
  cuando `diff != ""`; threading via `_loop2_with_cross_check` en
  `pre_merge_cmd.py:1484`.
- **NOT shipped**: empirical observation of cumulative diff size,
  truncation rate, meta-reviewer file:line referencing rate. v1.0.0
  could not exercise this path because `/sbtdd pre-merge` was broken
  by other defects.
- **v1.0.2 closes the loop**: regression-guard tests (Task 6) verify
  the wiring; empirical observation deferred to Activity D dogfood
  (sec.2.4) and reported in CHANGELOG `[1.0.2]` Process notes.

**Entrega v1.0.2**:

- Regression tests adicionales en
  `tests/test_pre_merge_cross_check.py`:
  - `test_cross_check_prompt_embeds_diff_when_provided`:
    monkeypatch `_dispatch_requesting_code_review` para capturar
    el prompt; asserta substring `## Cumulative diff under review`
    presente cuando `diff != ""`.
  - `test_cross_check_prompt_omits_diff_when_empty`: asserta el
    substring AUSENTE cuando `diff == ""`.
- Empirical validation: durante Item D dogfood, capturar el prompt
  literal enviado y verificar diff section presente. Document
  observado size en CHANGELOG `[1.0.2]` Process notes.

### 2.3 Item C — H5-2 `spec_lint` enforcement at Checkpoint 2

**Track**: Beta (subagent #2, primary task).

**Archivos**:
- `skills/sbtdd/scripts/spec_lint.py` (new module).
- `skills/sbtdd/scripts/spec_cmd.py` (extend `_run_magi_checkpoint2`).
- `tests/test_spec_lint.py` (new).
- `tests/test_spec_cmd.py` (extension para integration test).

**Interface**:

```python
@dataclass(frozen=True)
class LintFinding:
    file: Path
    line: int
    rule: str        # "R1" | "R2" | "R3" | "R4" | "R5"
    severity: str    # "error" | "warning" | "info"
    message: str

def lint_spec(path: Path) -> list[LintFinding]:
    """Run mechanical lint checks against a spec file.

    Returns:
        list of LintFinding (empty = clean). Error-severity findings
        block Checkpoint 2; warning-severity emit stderr breadcrumb
        but do not block.
    """
```

**5 reglas** (Q3 dictamina R3 severity = warning inicial):

| Rule | Check | Severity v1.0.2 |
|------|-------|-----------------|
| R1 | Cada bloque `**Escenario X: ...**` / `### Escenario X: ...` / `## Escenario X: ...` tiene Given / When / Then bullets no-vacios | error |
| R2 | Cada Escenario tiene identifier unico (X-N format alphanumeric+dash) | error |
| R3 | Section headers monotonous **top-level integer only** (matches `^##\s+\d+\.\s` strict; non-numeric `## Heading` y sub-numbered `## 9.5` correctamente skipean per W2/W7 iter 1 fix) | **warning** (Q3) |
| R4 | Cero matches uppercase placeholder (los tres tokens word-boundary, reusa `spec_cmd._INV27_RE`) | error |
| R5 | Frontmatter docstring con `Generado YYYY-MM-DD` line + reference a source artifact | error |

**Integration en `spec_cmd._run_magi_checkpoint2`**:

```python
def _run_magi_checkpoint2(...):
    spec_path = root / "sbtdd" / "spec-behavior.md"
    plan_path = root / "planning" / "claude-plan-tdd-org.md"

    # NEW v1.0.2 Item C: lint pre-MAGI dispatch
    for path in (spec_path, plan_path):
        findings = spec_lint.lint_spec(path)
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]
        for w in warnings:
            sys.stderr.write(
                f"[sbtdd spec-lint] {w.file}:{w.line} "
                f"({w.rule}) {w.message}\n"
            )
        if errors:
            details = "\n".join(
                f"  {e.file}:{e.line} ({e.rule}) {e.message}"
                for e in errors
            )
            raise ValidationError(
                f"spec_lint blocked Checkpoint 2 dispatch:\n{details}\n"
                f"Fix violations and re-run /sbtdd spec."
            )

    # ... existing magi_dispatch.invoke_magi(...) iter loop
```

**Lint timing contract (C1 iter 1 fix)**: `spec_lint.lint_spec` runs
**ONCE at the top of `_run_magi_checkpoint2`, BEFORE the MAGI iter
loop begins**. If lint raises `ValidationError`, the cycle aborts
without entering the iter loop — no MAGI iter budget is consumed.
The safety valve cap=3 G1 binding remains intact for the next
attempt after the operator fixes the lint violations and re-runs
`/sbtdd spec`. This places the lint gate upstream of the safety
valve, not inside it.

**CLI standalone**:

```
python -m skills.sbtdd.scripts.spec_lint <path> \
    [--severity error|warning|info] [--rule R1|R2|R3|R4|R5]
```

Exit codes: 0 (clean), 1 (errors found), 2 (file missing or
unreadable).

### 2.4 Item D — Own-cycle cross-check dogfood (methodology)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (config toggle + run de comandos).

**Pasos del orchestrator durante pre-merge phase**:

1. Set `magi_cross_check: true` en `.claude/plugin.local.md`.
2. Run `/sbtdd pre-merge` end-to-end (Loop 1 + Loop 2 + cross-check).
3. Capture artifacts `.claude/magi-cross-check/iter{N}-*.json`.
4. Run `python scripts/cross_check_telemetry.py
   --root .claude/magi-cross-check --format markdown` sobre los
   artifacts producidos por el propio cycle.
5. Document findings empiricos en CHANGELOG `[1.0.2]` Process notes:
   - Cuantos iters Loop 2 (esperado: 1-2 para bundle 5 plan tasks).
   - Cross-check decision distribution.
   - Meta-reviewer agreement rate vs MAGI verdicts.
   - Cualquier gap observable (meta-reviewer no references
     file:line; diff embedding ambiguo; carry-forward block missing
     en iter 2+).
- Si Item D surfaces production bug en cross-check path:
  abort cycle, escalate al usuario, evaluate scope (mini-fix in
  v1.0.2 vs new cycle v1.0.2.1).

### 2.5 Item E — P7 empirical proof-of-recovery (methodology)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (test path exercise + Process notes).

**Pasos del orchestrator** (post-Track-Alpha + Track-Beta close,
pre-pre-merge):

1. Verify spec-behavior.md + plan-tdd-org.md existen (producidos
   durante este cycle por brainstorming + writing-plans
   interactivos en sesion actual).
2. Invoke `/sbtdd spec --resume-from-magi` desde esta sesion.
3. Verify post-conditions:
   - skipea brainstorming/writing-plans dispatch (no subprocess
     spawn observable);
   - ejecuta MAGI Checkpoint 2 sobre artifacts existentes;
   - escribe state file `.claude/session-state.json` con
     `plan_approved_at: <ts>` + commit chore: del bundle de
     artifacts si verdict >= GO_WITH_CAVEATS.
4. Document en CHANGELOG `[1.0.2]` Process notes:
   - Resultado del exercise (success / failure).
   - Tiempo wall-clock end-to-end.
   - Cualquier gap observable (structural validation too strict,
     mensaje de error confuso, edge case en `--resume-from-magi`).

### 2.6 Item F — Meta-test enforcing `allow_interactive_skill=True`

**Track**: Beta (subagent #2, after Item C).

**Archivos**:
- `tests/test_invoke_skill_callsites_audit.py` (new).

**Implementacion (AST-based)**:

```python
import ast
import pathlib

_EXCLUDED_FILES = {
    # Wrappers internamente pasan allow_interactive_skill=True;
    # son safe path por design (Item A2 v1.0.1).
    "skills/sbtdd/scripts/superpowers_dispatch.py",
}
_AUDITED_DIRS = (
    "skills/sbtdd/scripts/",
    "tests/",
)
_INTERACTIVE_SKILLS = frozenset({"brainstorming", "writing-plans"})


def _walk_invoke_skill_calls(path: Path) -> list[ast.Call]:
    """Yield ast.Call nodes calling invoke_skill in path."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # Match foo.invoke_skill(...) or invoke_skill(...)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "invoke_skill":
                yield node
        elif isinstance(node.func, ast.Name):
            if node.func.id == "invoke_skill":
                yield node


def test_interactive_skill_callsites_pass_override():
    violations = []
    for d in _AUDITED_DIRS:
        for path in pathlib.Path(d).rglob("*.py"):
            if str(path).replace("\\", "/") in _EXCLUDED_FILES:
                continue
            for call in _walk_invoke_skill_calls(path):
                # Find skill kwarg
                skill_value = next(
                    (kw.value for kw in call.keywords
                     if kw.arg == "skill"
                     and isinstance(kw.value, ast.Constant)
                     and kw.value.value in _INTERACTIVE_SKILLS),
                    None,
                )
                if skill_value is None:
                    continue
                # Skill is interactive — assert override present
                has_override = any(
                    kw.arg == "allow_interactive_skill"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                    for kw in call.keywords
                )
                if not has_override:
                    violations.append(
                        f"{path}:{call.lineno} invokes "
                        f"invoke_skill(skill='{skill_value.value}') "
                        f"without allow_interactive_skill=True"
                    )
    assert not violations, (
        "Interactive skill callsites missing override:\n"
        + "\n".join(violations)
        + "\n\nFix: add allow_interactive_skill=True or use "
        "wrapper (superpowers_dispatch.brainstorming / writing_plans)."
    )
```

**Tests adicionales en mismo archivo**:

- `test_meta_test_catches_synthetic_regression`: synthetic fixture
  con call site SIN override; meta-test recognizes y fails con
  guidance message (use `pytest.raises(AssertionError)`).
- `test_wrapper_files_excluded`: smoke test que `superpowers_dispatch.py`
  esta en `_EXCLUDED_FILES`.
- `test_unknown_skill_passes_through`: callsite con
  `skill="custom-skill"` (no en `_INTERACTIVE_SKILLS`) NO viola
  contract (whitelist semantic).

### 2.7 Item G — Per-module coverage threshold

**Track**: Beta (subagent #2, after Item F).

**Archivos**:
- `pyproject.toml` (modificado: add `pytest-cov` + `[tool.coverage]`).
- `Makefile` (modificado: extend `verify` target).
- CHANGELOG `[1.0.2]` (documenta baseline + excludes).

**Q4 dictamina**: measure baseline first, set
`--cov-fail-under=floor(baseline) - 2%`. Final value documented
en task close.

**`pyproject.toml`** (extension):

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",   # NEW v1.0.2
    "ruff>=0.1",
    "mypy>=1.5",
    "pyyaml>=6.0",
]

[tool.coverage.run]
source = ["skills/sbtdd/scripts"]
omit = [
    "skills/sbtdd/scripts/__init__.py",
    "templates/*",
]

[tool.coverage.report]
fail_under = 0   # placeholder — real value committed in task close
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "def __repr__",
]
```

Note: `fail_under = 0` es placeholder en initial commit. Task close
de Item G measures baseline + commits real value (e.g., `82` if
baseline is 84%) en separate atomic commit.

**`Makefile`** (extension):

```makefile
.PHONY: test lint format typecheck coverage verify

coverage:
	python -m pytest --cov=skills/sbtdd/scripts --cov-report=term-missing tests/

verify: test lint format typecheck coverage
```

Note (C2/W4 iter 1 fix): the threshold value is read from
`pyproject.toml [tool.coverage.report] fail_under` automatically by
`pytest-cov` when `--cov-fail-under` is omitted, so no `tomllib`
runtime dep is needed. tomllib is Python 3.11+ stdlib and the project
supports 3.9+; using pytest-cov's built-in TOML reader keeps the
toolchain portable across the supported Python range.

**CHANGELOG `[1.0.2]` documenta**:
- Per-module coverage baseline (tabla de modulo / %coverage
  measured during Item G implementation).
- Final threshold value (`floor(baseline) - 2%`).
- Excludes justificados con razon explicita.
- Gap analysis: modulos under 85% (target eventual) listados como
  v1.0.5+ raise candidates.

---

## 3. Cross-module contracts

v1.0.2 NO introduce nuevos cross-cuts. Items consumen helpers
existentes:

- **Item A** consume frozen JSON shape de `_loop2_with_cross_check`
  (v1.0.0 Feature G). Schema documented en spec-base sec.2.1; no
  cambia en v1.0.2.
- **Item B** monkeypatchea `pre_merge_cmd._dispatch_requesting_code_review`
  en tests para capturar el prompt content; no muta el modulo.
- **Item C `spec_lint.py`** importa `spec_cmd._INV27_RE` para R4
  (reuse en lugar de redefinir). `spec_cmd._run_magi_checkpoint2`
  importa `spec_lint.lint_spec` para Checkpoint 2 integration.
- **Item F** AST-walks `skills/sbtdd/scripts/` + `tests/`; lookup
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` literal set en
  `superpowers_dispatch.py` (frozenset constant, frozen v1.0.1).
- **Item G** wiring puro (`pyproject.toml` + `Makefile`); no toca
  codigo Python.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` (existing en `errors.py`):
  Item C Checkpoint 2 abort raisea `ValidationError`.
- `subprocess_utils.run_with_timeout`: ningun item nuevo lo invoca
  directamente.
- `_compute_loop2_diff_with_meta` (v1.0.0): Item B asserts sobre su
  output integration en prompt builder, no muta.
- `_loop2_with_cross_check` (v1.0.0): Item D toggle a
  `magi_cross_check: true` ejerce el path; no muta.

---

## §4 Escenarios BDD

Distribuidos por item — la spec usa Tier 2 permissive regex de
`spec_snapshot.emit_snapshot` (shipped en v1.0.1 Item A1) que
acepta escenarios distribuidos a traves de cualquier seccion sin
requerir literal `## §4 Escenarios` header.

### Item A — Cross-check telemetry

**Escenario A-1: happy path con multiple iter artifacts**

> **Given** Directorio `tmp/.claude/magi-cross-check/` con 3
> archivos `iter1-2026-05-XX.json`, `iter2-...json`,
> `iter3-...json` con shape valido (cross_check_decisions list +
> magi_verdict + diff_truncated fields).
> **When** `aggregate(Path("tmp/.claude/magi-cross-check"))`.
> **Then** Returns `TelemetryReport` con `total_iters == 3`,
> `decision_distribution` agregado de los 3 files,
> `per_iter` list con 3 entries en orden de iter ascending,
> `agreement_rate` calculado como float entre 0.0 y 1.0,
> `truncation_rate` calculado.

**Escenario A-2: empty directory tolerated**

> **Given** Directorio existe pero esta vacio.
> **When** `aggregate(empty_dir)`.
> **Then** Returns `TelemetryReport` con `total_iters == 0`. CLI
> markdown output incluye literal `No iterations found`. NO error.

**Escenario A-3: malformed JSON skipped with breadcrumb**

> **Given** Directorio con 2 files validos + 1 file con JSON
> invalido (truncated mid-content).
> **When** `aggregate(dir)`.
> **Then** `total_iters == 2` (solo los validos contados).
> stderr contiene breadcrumb identificando el file malformado +
> parse error message. NO abort.

**Escenario A-4: markdown output well-formed**

> **Given** Aggregator output con valid TelemetryReport.
> **When** `format_markdown(report)`.
> **Then** Output es valid markdown table parseable: header row
> presente, separator row con `|---|`, data rows con counts.
> Tables identificadas: "Decision distribution", "Per-iter
> breakdown", "Per-agent rate", "Per-severity distribution".

**Escenario A-5: JSON output parseable**

> **Given** Aggregator output con valid TelemetryReport.
> **When** `format_json(report)`.
> **Then** Output es valid JSON parseable via `json.loads`.
> Top-level keys: `total_iters`, `decision_distribution`,
> `per_iter`, `agreement_rate`, `truncation_rate`. `per_iter` es
> list, otros son dict / float / int per shape.

**Escenario A-6: 100+ files linear performance (NF32 guard)**

> **Given** Directorio con 100 valid iter artifacts synthetically
> generated.
> **When** `aggregate(dir)` con timing measurement.
> **Then** Wall-clock < 5 segundos en CI Linux runner. Memory
> peak < 100MB. Single read-pass per file (no quadratic blowup).

### Item B — Diff threading regression

**Escenario B-1: prompt embeds diff section when non-empty**

> **Given** `_dispatch_requesting_code_review` monkeypatched para
> capturar prompt arg. `_loop2_with_cross_check` invoked con
> `diff="--- a/foo.py\n+++ b/foo.py\n@@ ..."`.
> **When** prompt construido por `_build_cross_check_prompt(diff,
> verdict, findings)`.
> **Then** Captured prompt contiene substring
> `## Cumulative diff under review (truncated to 200KB)`. Diff
> bytes presentes en el prompt body dentro del code block.

**Escenario B-2: prompt omits diff section when empty**

> **Given** Same setup pero `diff=""` (subprocess fallback).
> **When** prompt construido.
> **Then** Captured prompt NO contiene substring
> `## Cumulative diff under review`. Findings text + verdict
> presentes; diff section ausente.

### Item C — `spec_lint`

**Escenario C-R1-1: escenario block with all bullets passes**

> **Given** Spec con bloque
> `**Escenario X-1: ejemplo**\n> **Given** ...\n> **When** ...\n>
> **Then** ...`.
> **When** `lint_spec(path)`.
> **Then** Returns list sin LintFinding con rule="R1" para ese
> bloque.

**Escenario C-R1-2: escenario missing Given block fails**

> **Given** Spec con bloque
> `**Escenario X-1: ejemplo**\n> **When** ...\n> **Then** ...` (no
> Given).
> **When** `lint_spec(path)`.
> **Then** Returns list con LintFinding(rule="R1",
> severity="error") referencing the block's line. Message incluye
> `missing Given block`.

**Escenario C-R2-1: unique scenario IDs pass**

> **Given** Spec con escenarios `X-1`, `X-2`, `Y-1` (todos
> distintos).
> **When** `lint_spec(path)`.
> **Then** Returns list sin LintFinding rule="R2".

**Escenario C-R2-2: duplicate scenario IDs fail**

> **Given** Spec con dos bloques `**Escenario X-1: ...**` (id
> duplicado).
> **When** `lint_spec(path)`.
> **Then** Returns list con LintFinding(rule="R2",
> severity="error") identifying both occurrences (file:line for
> each).

**Escenario C-R3-1: monotonic headers pass without warning**

> **Given** Spec con sections `## 1. ...`, `## 2. ...`, `## 3. ...`
> (monotonic).
> **When** `lint_spec(path)`.
> **Then** Returns list sin LintFinding rule="R3".

**Escenario C-R3-2: header skip emits warning but does not block**

> **Given** Spec con sections `## 1.`, `## 2.`, `## 5.` (skipea
> `## 3.` y `## 4.`).
> **When** `lint_spec(path)` y luego
> `_run_magi_checkpoint2(spec_path=...)`.
> **Then** lint returns list con LintFinding(rule="R3",
> severity="warning"). `_run_magi_checkpoint2` emite stderr
> breadcrumb pero NO raisea. MAGI dispatch proceeds. Q3 dictamen.

**Escenario C-R4-1: INV-27 mechanical extends to spec-behavior.md**

> **Given** spec-behavior.md generado por brainstorming contiene
> uppercase placeholder token uno-de-tres (synthetic fixture
> incluye el word-boundary match).
> **When** `lint_spec(spec_behavior_path)`.
> **Then** Returns list con LintFinding(rule="R4", severity="error",
> line=<line>, message=referencing INV-27).

**Escenario C-R5-1: frontmatter docstring present passes**

> **Given** Spec inicia con bloque `> Generado 2026-05-06 a partir
> de sbtdd/spec-behavior-base.md` line en first 30 lines.
> **When** `lint_spec(path)`.
> **Then** Returns list sin LintFinding rule="R5".

**Escenario C-R5-2: missing frontmatter docstring fails**

> **Given** Spec inicia directamente con `# Title` sin frontmatter
> blockquote.
> **When** `lint_spec(path)`.
> **Then** Returns list con LintFinding(rule="R5",
> severity="error", line=1).

**Escenario C-int-1: `_run_magi_checkpoint2` aborts on R1 error**

> **Given** spec-behavior.md fixture viola R1 (escenario sin Given
> bullet); plan-tdd-org.md fixture clean.
> **When** `_run_magi_checkpoint2(root)`.
> **Then** Raises `ValidationError` con guidance message
> referencing R1 + file path + line. `magi_dispatch.invoke_magi`
> NUNCA called (asserted via monkeypatch spy).

**Escenario C-int-2: warnings emit breadcrumb without blocking**

> **Given** spec-behavior.md viola R3 (header skip) pero clean en
> R1, R2, R4, R5.
> **When** `_run_magi_checkpoint2(root)`.
> **Then** stderr contiene breadcrumb identificando R3 violation +
> file:line. `magi_dispatch.invoke_magi` IS called (proceeds).

**Escenario C-cli-1: standalone CLI exit codes**

> **Given** Path a spec clean (sin findings).
> **When** `python -m skills.sbtdd.scripts.spec_lint <path>`.
> **Then** Exit code 0. stdout vacio o "No findings".
> Vs spec con error finding: exit 1, stdout lista findings.

### Item F — meta-test

**Escenario F-1: callsite without override fails meta-test**

> **Given** Synthetic fixture file con literal call
> `invoke_skill(skill="brainstorming", args=[...])` (sin
> `allow_interactive_skill`).
> **When** Meta-test corre AST walk sobre el fixture file.
> **Then** Raises AssertionError con message containing fixture
> path + line + sugerencia "add allow_interactive_skill=True or
> use wrapper".

**Escenario F-2: callsite with override passes**

> **Given** Synthetic fixture con literal call
> `invoke_skill(skill="brainstorming", allow_interactive_skill=True,
> args=[...])`.
> **When** Meta-test runs sobre fixture.
> **Then** No assertion failure for ese callsite.

**Escenario F-3: wrapper files excluded from audit**

> **Given** `superpowers_dispatch.py` (donde wrappers viven y
> internamente llaman `invoke_skill(skill="brainstorming",
> allow_interactive_skill=True)`) esta en `_EXCLUDED_FILES`.
> **When** Meta-test runs full audit.
> **Then** AST walk skipea ese file. No assertion sobre callsites
> internos del wrapper.

**Escenario F-4: unknown skill name passes through**

> **Given** Fixture con call
> `invoke_skill(skill="custom-skill", args=[...])` — `custom-skill`
> NO en `_INTERACTIVE_SKILLS` set.
> **When** Meta-test runs.
> **Then** Skill name NOT en interactive set ⇒ no override
> required. No assertion failure.

### Item G — coverage

**Escenario G-1: `make verify` invokes coverage gate**

> **Given** Repo en estado clean (todos los tests passing).
> **When** `make verify` runs.
> **Then** `pytest --cov=skills/sbtdd/scripts
> --cov-report=term-missing --cov-fail-under=<threshold>` invoked.
> Exit code 0. Coverage table impresa en stdout.

**Escenario G-2: coverage threshold violation fails verify**

> **Given** Synthetic test scenario donde coverage measured esta
> 1% bajo threshold (e.g., threshold=85, measured=84).
> **When** `pytest --cov ... --cov-fail-under=85` corre.
> **Then** Exit code != 0. Mensaje stderr containing
> `Required test coverage of 85% not reached`.

---

## 5. Subagent layout + execution timeline

### 5.1 Track Alpha (subagent #1, sequential)

**Owner**: code-architect single subagent.
**Scope**: Items A → B (5 plan tasks total en bundle, Alpha owns
2).
**Wall-time estimado**: 6-9h.

Sequential ordering rationale:

1. **A first** (~5-8h): telemetry script standalone, no
   dependencies. Production code + tests.
2. **B last** (~1h): regression test sobre prompt builder. Could
   technically run before A (no dep), but B is a 1-test addition;
   bundling with A keeps Track Alpha's mental model coherent.

Sin dependencias inter-track durante implementation phase.

### 5.2 Track Beta (subagent #2, sequential)

**Owner**: code-architect single subagent.
**Scope**: Items C → F → G (3 plan tasks).
**Wall-time estimado**: 16-25h.

Sequential ordering rationale:

1. **C first** (~10-15h): spec_lint module + 5 rules + Checkpoint
   2 integration. Heaviest item; sets foundation.
2. **F second** (~3-5h): meta-test AST walk. Orthogonal a C, pero
   secuenciado despues para que Beta subagent tenga continuity.
3. **G last** (~3-5h): coverage wiring. Final task; measures
   baseline AFTER F adds new tests (slightly higher count) so
   threshold reflects post-bundle state.

Sin dependencias inter-track.

### 5.3 Mid-cycle methodology (orchestrator)

**Owner**: orchestrator (single Claude Code session).
**Scope**: Items D + E.
**Wall-time estimado**: ~30-60min total.

Triggered AFTER ambos tracks completan AND BEFORE pre-merge phase:

1. **E exercise** (~15-30min): exercise `/sbtdd spec
   --resume-from-magi` end-to-end. Verify post-conditions. Document
   en CHANGELOG `[1.0.2]` Process notes.
2. **D dogfood** (~30-45min): set `magi_cross_check: true` +
   run `/sbtdd pre-merge` end-to-end. Capture artifacts. Run
   telemetry script (Item A produced output) sobre artifacts.
   Document findings.

Item D y E pueden ejecutarse en cualquier orden; E primero es
recomendado porque ejerce el upstream path (Checkpoint 2 vs
pre-merge) — si E falla, signal de issue mas fundamental que
puede contaminar D.

### 5.4 True parallelism observado

Surfaces Track Alpha vs Track Beta:

| Surface | Alpha | Beta |
|---------|-------|------|
| `scripts/cross_check_telemetry.py` | yes (new) | — |
| `tests/test_cross_check_telemetry.py` | yes (new) | — |
| `tests/test_pre_merge_cross_check.py` | yes (extend) | — |
| `skills/sbtdd/scripts/spec_lint.py` | — | yes (new) |
| `skills/sbtdd/scripts/spec_cmd.py` | — | yes (extend) |
| `tests/test_spec_lint.py` | — | yes (new) |
| `tests/test_spec_cmd.py` | — | yes (extend) |
| `tests/test_invoke_skill_callsites_audit.py` | — | yes (new) |
| `pyproject.toml` | — | yes (modify) |
| `Makefile` | — | yes (modify) |

**Cero overlap**. Tracks pueden run truly parallel sin merge
conflicts.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (CHANGELOG `[1.0.0]`, precedente
  cerrado v1.0.1). NO INV-0 path.
- Bundle scope acotado (5 plan tasks + 2 methodology) — esperamos
  converger en 1-2 iters limpios.
- Si llega a iter 3 sin convergencia, scope-trim mandatorio
  (no override): defer F + G a v1.0.3 (E es methodology, puede
  ejercerse en cualquier ciclo posterior; D dogfood es own-cycle
  evidence intrinsica).

**Scope-trim ladder for Checkpoint 2 iter 3** (W6 iter 1 fix —
balthasar pre-staged decision):

If Checkpoint 2 iter 3 verdict < `GO_WITH_CAVEATS` full no-degraded,
trim scope in this order (smallest impact first), re-emit spec+plan
artifacts, and proceed directly to implementation phase without
further MAGI iterations:

1. **First trim**: defer Item G (coverage threshold) → v1.0.3.
   Smallest scope — `pyproject.toml` + `Makefile` only, no production
   code. Plan tasks 17-19 removed; ~2-3 nuevos tests removed.
2. **Second trim** (if iter 3 verdict still blocks after Item G defer
   in re-evaluation): defer Item F (meta-test) → v1.0.3. Plan tasks
   15-16 removed; ~3-5 nuevos tests removed. Bundle reduces a
   A + B + C + D + E (3 plan tasks + 2 methodology).
3. **Third trim** (rarely needed): defer Item C (spec_lint) →
   v1.0.3 standalone cycle. Plan tasks 7-14 removed; bundle reduces
   to A + B + D + E (2 plan tasks + 2 methodology). At this point
   v1.0.2 is essentially "telemetry script + own-cycle dogfood" —
   ship-ready single-pillar.

The orchestrator picks the trim level at iter 3 escalation; record
the decision in CHANGELOG `[1.0.2]` Process notes alongside the
deferred-to-v1.0.3 list.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- Bundle scope minimal (5 plan tasks, ningun toca core path) —
  esperamos converger en 1 iter.

### 6.3 Loop 2 (`/magi:magi`) — own-cycle dogfood

- **Cap=5** per `auto_magi_max_iterations`.
- **Cross-check enabled mid-cycle**: Item D ENTREGA es setear
  `magi_cross_check: true` antes de invocar `/sbtdd pre-merge`.
  Cycle valida su propia feature.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding fallback**: si Loop 2 iter 3 no converge clean,
  scope-trim default — defer F + G a v1.0.3. D y E ya ejecutados
  pre-Loop2 (mid-cycle methodology), no se pueden defer.
- **Manual fallback** (R8 mitigation): si `/sbtdd pre-merge` hits
  infinite loop o regresion en cross-check path, escape via Ctrl+C
  + `python skills/magi/scripts/run_magi.py code-review <payload>
  --model opus --timeout 900` (precedente v1.0.0, v1.0.1).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.2 own-cycle
(chicken-and-egg: cross-check path se ejerce por primera vez), el
operator MUST fall back a manual `python skills/magi/scripts/run_magi.py`
direct dispatch + manual mini-cycle commits. Document en CHANGELOG
`[1.0.2]` Process notes. Precedentes v0.5.0 + v1.0.0 + v1.0.1
todos demonstrate ship viability con manual fallback.

**Verbatim fallback command** (warm + ready to copy-paste):

```bash
mkdir -p .claude/magi-runs/v102-loop2-iter1
{
  cat .claude/magi-runs/v102-loop2-iter1-header.md
  echo "---"
  cat sbtdd/spec-behavior.md
  echo "---"
  cat planning/claude-plan-tdd.md
} > .claude/magi-runs/v102-loop2-iter1-payload.md
python skills/magi/scripts/run_magi.py code-review \
  .claude/magi-runs/v102-loop2-iter1-payload.md \
  --model opus --timeout 900 \
  --output-dir .claude/magi-runs/v102-loop2-iter1
```

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.1 → 1.0.2.

### 7.2 CHANGELOG `[1.0.2]` sections

- **Added** — `scripts/cross_check_telemetry.py` (Item A);
  `skills/sbtdd/scripts/spec_lint.py` con 5 reglas R1-R5 (Item C);
  meta-test `tests/test_invoke_skill_callsites_audit.py` (Item F);
  `pytest-cov` dev dep + coverage config (Item G).
- **Changed** — `spec_cmd._run_magi_checkpoint2` ahora invoca
  `spec_lint.lint_spec` antes de MAGI dispatch (Item C
  integration); `Makefile verify` target extends con coverage check
  (Item G).
- **Process notes** — Item D dogfood findings (iter count,
  decision distribution, agreement rate, observable gaps); Item E
  recovery flag empirical findings (success/failure, wall-clock,
  gaps); v1.0.1 LOCKED commitments cerrados; per-module coverage
  baseline + final threshold value.
- **Deferred (rolled to v1.0.3)** — MAGI gate template alignment
  audit (sole pillar v1.0.3 per memory).
- **Deferred (rolled to v1.0.4)** — parallel task dispatcher; real
  headless detection; `_SUBPROCESS_INCOMPATIBLE_SKILLS` audit; 600s
  subprocess hang full LOUD-FAST fix.

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.2 docs section sobre `cross_check_telemetry.py`
  CLI + `spec_lint.py` Checkpoint 2 integration.
- **SKILL.md**: `### v1.0.2 notes` section documentando 5 plan
  tasks + 2 methodology activities + cross-check dogfood
  observations.
- **CLAUDE.md**: v1.0.2 release notes pointer.

---

## 8. Risk register v1.0.2

(Extends spec-base R1-R7 con adiciones de brainstorming
2026-05-06.)

- **R1** (spec-base): Item D dogfood puede surfacear production
  bug en cross-check path no-cubierto por v1.0.0 unit tests.
  Mitigation: if surfaces, mini-cycle TDD fix in v1.0.2 if scope
  minimal; otherwise abort + new cycle v1.0.2.1.
- **R2** (spec-base): Item C R1-R5 rules pueden ser too strict y
  rechazar specs legitimas (especialmente R3 monotonous headers).
  Mitigation: Q3 dictamina R3=warning inicial; promote a error en
  v1.0.5+ despues de empirical confidence.
- **R3** (spec-base): Item G coverage <85% baseline puede surfacear
  modulos legitimamente bajo-coverage. Mitigation: Q4 dictamina
  measure-baseline-first + threshold = floor(baseline) - 2%; final
  value documented en task close + CHANGELOG.
- **R4** (spec-base): Item E recovery exercise puede fail si
  v1.0.2 own-cycle drives `/brainstorming` interactivamente Y
  `--resume-from-magi` mid-cycle. Mitigation: empirical validation
  con fallback a manual `python skills/magi/scripts/run_magi.py`
  (precedente v1.0.0, v1.0.1).
- **R5** (spec-base): Item F meta-test puede have false-positives
  en wrappers internos. Mitigation: explicit `_EXCLUDED_FILES` con
  `superpowers_dispatch.py` + 4 test escenarios (F-1..F-4)
  cubriendo edge cases.
- **R6** (spec-base): Bundle scope multi-pillar aumenta riesgo de
  Loop 2 non-convergence vs v1.0.1 single-pillar. Mitigation: Q2
  reclasificacion D + E como methodology reduces visible scope a
  MAGI; G2 binding fallback defer F + G a v1.0.3 si Loop 2 iter 3
  no converge.
- **R7** (spec-base): Telemetry script (Item A) consume artifacts
  malformados de pre-v1.0.0 cycles si operator runs en project
  con legacy `.claude/magi-cross-check/`. Mitigation: skip
  malformed files con stderr breadcrumb (escenario A-3).
- **R8** (NEW brainstorming): Item D dogfood puede surface
  infinite loop en `_loop2_with_cross_check` (untested combination
  cross-check + carry-forward + Loop 2 escalation). Mitigation:
  `auto_magi_max_iterations: 5` cap protects budget; manual escape
  via Ctrl+C + manual run_magi.py fallback (sec.6.4 verbatim
  command warm).
- **R9** (NEW brainstorming): Item G coverage measurement runtime
  puede impactar NF-A target (~30-60s extra). Mitigation: scope
  coverage source a `skills/sbtdd/scripts/` only; exclude `tests/`
  y `templates/`. Re-evaluate threshold si NF-A breached en task
  close.
- **R10** (NEW brainstorming): spec-behavior.md generada por
  brainstorming session puede fail R3 monotonic si tiene header
  skips. Mitigation: hand-craft monotonic headers (este doc:
  `## 1` a `## 10` monotonic); R3 es warning-only per Q3 anyway
  (no bloquea Loop 2 propio).

---

## 9. Acceptance criteria final v1.0.2

v1.0.2 ship-ready cuando:

### 9.1 Functional Items A-G

- **F1**. F100-F104: telemetry script exists, CLI flags, markdown
  + JSON output, error handling.
- **F2**. F105-F106: diff threading regression test +
  empirical observation documented (Item D).
- **F3**. F107-F112: spec_lint module + 5 rules + Checkpoint 2
  integration + CLI standalone.
- **F4**. F113-F115: dogfood cycle ran + telemetry consumed +
  Process notes (Item D).
- **F5**. F116-F117: recovery flag empirical exercised + Process
  notes (Item E).
- **F6**. F118-F120: meta-test AST walk + 4 escenarios (F-1..F-4).
- **F7**. F121-F123: coverage config + Makefile + baseline doc +
  final threshold.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= floor(baseline) - 2%, runtime
  <= 160s. Soft-target <= 145s.
- **NF-B**. Tests baseline 1059 + 1 skipped + ~30-35 nuevos =
  ~1089-1094 final.
- **NF-C**. Cross-platform (Windows + POSIX).
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `spec_cmd.py` (Item C integration),
  `pre_merge_cmd.py` (Item B regression test only — no muta
  modulo), nuevos modulos (`spec_lint.py`,
  `cross_check_telemetry.py`, meta-test).

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.2]` entry written con secciones Added /
  Changed / Process notes + Item D dogfood findings + Item E
  recovery findings + per-module coverage baseline + cross-check
  telemetry observations.
- **P4**. Version bump 1.0.1 -> 1.0.2 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.2` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. Empirical proof-of-recovery for `--resume-from-magi`
  ejercido end-to-end mid-cycle (cierra v1.0.1's deferred P7 W5
  caspar disclosure).
- **P8**. Empirical proof-of-cross-check: own-cycle dogfood ran +
  telemetry artifacts produced + Process notes document
  observations (cierra Item D).

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.2 ship + 5 plan tasks
  + 2 methodology activities).
- **D3**. Nuevos modulos documentados:
  - `cross_check_telemetry.py` en README + SKILL.md (CLI usage).
  - `spec_lint.py` en README + SKILL.md (Checkpoint 2 integration).
  - Coverage threshold en README (final value + rationale).

---

## 9.5 Inherited invariants from v0.4.x and v1.0.1 (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording (canonical
single-line text `[sbtdd magi] synthesizer failed; manual synthesis
recovery applied`) is preserved verbatim across spec / CHANGELOG /
impl per the cross-artifact alignment contract
(`tests/test_changelog.py`). v1.0.2 ships no behavioral change
to this path; the wording is repeated here so the v0.4.x +
v1.0.1 invariant survives the v1.0.2 spec rewrite.

The INV-37 composite-signature output validation tripwire
(v1.0.1 Item A0) is also preserved verbatim — `_run_spec_flow`
mtime + size + sha256 check applies during v1.0.2 own-cycle if
operator drives `/sbtdd spec` instead of using
`--resume-from-magi`. v1.0.2 Item E exercises the
`--resume-from-magi` path, NOT the standard flow, so INV-37 does
not fire during the recovery exercise (path skipped entirely).

---

## 10. Referencias

- Spec base v1.0.2: `sbtdd/spec-behavior-base.md`
  (commit en branch `feature/v1.0.2-bundle`).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1
  frozen: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.1 LOCKED commitments rolled forward a v1.0.2 per CHANGELOG
  `[1.0.1]` Deferred section + Process notes rolled-forward
  bullets.
- v1.0.0 Feature G cross-check: `pre_merge_cmd._loop2_with_cross_check`
  shipped en v1.0.0 con `magi_cross_check: false` default; v1.0.2
  Item D primer empirical exercise con toggle a `true`.
- v1.0.1 INV-37: composite-signature tripwire en
  `spec_cmd._run_spec_flow` (preservado en v1.0.2; sec.9.5).
- v1.0.3 LOCKED template alignment audit: memory
  `project_v103_template_alignment_audit.md` (sole pillar, ~1-2
  dias, sequenced first so v1.0.4+ runs against template-aligned
  baseline).
- v1.0.4 LOCKED items: memory
  `project_v104_parallel_task_dispatcher.md` +
  `project_v104_subprocess_headless_detection.md`.
- Brainstorming refinement decisions (2026-05-06):
  - Q1 — 2-track parallel partition (Alpha = A+B, Beta = C+F+G).
  - Q2 — D + E reclassified as methodology activities (no plan
    task TDD-cycle); plan tasks = A + B + C + F + G (5 items).
  - Q3 — `spec_lint` R3 severity = warning inicial; promote a
    error en v1.0.5+.
  - Q4 — coverage threshold = floor(baseline) - 2%, measured
    en task close de Item G.
- Branch: trabajo en `feature/v1.0.2-bundle` (branched off `main`
  HEAD `8fc0db4` = v1.0.1 ship).
