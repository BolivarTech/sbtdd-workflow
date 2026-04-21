# Milestone E: Distribution artifacts v0.1 ship — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar los artefactos de distribucion del plugin `sbtdd-workflow` para el ship de `v0.1.0` — crear `skills/sbtdd/SKILL.md` (el skill orquestador que es la primera superficie user-visible de `/sbtdd`), los dos manifests del marketplace BolivarTech (`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`) con versiones sincronizadas, el `README.md` publico de GitHub con shields y flujo end-to-end, y los contract tests que pinnean la estructura de estos cuatro archivos. **Cero cambios de codigo** en los modulos existentes bajo `skills/sbtdd/scripts/`: este milestone es puramente artefactos de distribucion y documentacion usuario-visible. Al cierre, el plugin es instalable publicamente via `/plugin marketplace add BolivarTech/sbtdd-workflow` y cumple los criterios de sec.S.12.2 (paridad con MAGI) + sec.S.12.5 (distribucion).

**Architecture:** Cuatro artefactos textuales (Markdown + JSON) + cuatro contract tests en Python stdlib. Ninguna nueva clase, ninguna nueva funcion. El SKILL.md sigue la estructura obligatoria de sec.S.6.3 del contrato (7 secciones en orden: Overview → Subcommand dispatch → Complexity gate → Execution pipeline → `sbtdd-rules` → `sbtdd-tdd-cycle` → Fallback), con cuerpo ~300-500 lineas (paridad con MAGI `skills/magi/SKILL.md` que tiene ~325 lineas). Los manifests siguen literalmente el schema declarado en sec.S.3.1 y sec.S.3.2. El README sigue la estructura de MAGI `README.md` (shields → Why multi-agent? → Installation → Usage → Architecture → Tests → License) adaptada al vocabulario SBTDD. Los contract tests validan presencia de keys/secciones requeridas — NO validan prose (evitan acoplamiento excesivo).

**Tech Stack:** Python 3.9+ stdlib solo para los contract tests (`json`, `re`, `pathlib`). Markdown + YAML frontmatter para SKILL.md y README. JSON para manifests. Ninguna dependencia runtime ni dev nueva.

---

## File Structure

Archivos creados en este milestone:

```
.claude-plugin/
├── plugin.json                 # NEW: plugin manifest v0.1.0 (sec.S.3.1)
└── marketplace.json            # NEW: BolivarTech marketplace catalog entry (sec.S.3.2)

skills/sbtdd/
└── SKILL.md                    # NEW: orchestrator skill (sec.S.6)

README.md                       # REWRITE: currently near-empty (1 line); full public README
CONTRIBUTING.md                 # NEW: brief contributor guide referenced from README

tests/
├── test_skill_md.py            # NEW: contract test for skills/sbtdd/SKILL.md
├── test_plugin_manifest.py     # NEW: contract test for .claude-plugin/plugin.json
├── test_marketplace_manifest.py# NEW: contract test for .claude-plugin/marketplace.json
├── test_readme.py              # NEW: contract test for README.md
└── test_distribution_coherence.py # NEW: cross-artifact coherence test (Task 9)

CHANGELOG.md                    # MODIFY: append Milestone E entries under existing ## Unreleased (Milestone D created the file)
```

Tareas: **12 total** (Task 0 pre-flight + Task 1 SKILL.md Red contract tests + Task 1b SKILL.md Green skeleton + Tasks 2-4 SKILL.md incremental sections + Task 5 plugin.json + Task 6 marketplace.json + Task 7 README + Task 8 CONTRIBUTING + Task 9 contract test consolidation + Task 10 acceptance sweep). Orden: las dependencias son minimas porque los artefactos no se importan entre si; el orden sigue el flujo logico de distribucion (skill → manifests → README → tests).

**Red-Green split policy (scope and rationale — addresses F1 MAGI iter 2).**

Strict Red-Green split (two commits: one `test:` that fails, one `feat:`/`docs:`/`chore:` that turns it green) is applied **only to the introduction of a wholly new artifact** — i.e., the creation of a file that did not exist before. In Milestone E this applies to:

- Task 1 / 1b (`skills/sbtdd/SKILL.md` creation).
- Task 5 (`.claude-plugin/plugin.json` creation).
- Task 6 (`.claude-plugin/marketplace.json` creation).
- Task 7 (`README.md` rewrite — treated as new artifact because the pre-existing stub is 1 line).
- Task 8 (`CONTRIBUTING.md` creation).

Tasks 2-4 (extending SKILL.md with sections 1-3, 4-6, 7) are **NOT** split. Rationale: each of those tasks extends an already-committed test file (`tests/test_skill_md.py`) alongside the SKILL.md section it asserts. The contract is that the SKILL.md section **and** the test assertions are a single logical unit — a new section body does not make sense without its tests, and the new test assertions fail immediately if committed alone. Committing both in the same `feat:` commit preserves atomicity of a single logical change without ballooning the plan to 15+ tasks. The policy is:

- **New file (first time on disk)** → Red-Green split (two commits).
- **Extension of an already-committed test file alongside a new-section body on an already-committed artifact** → one commit (`feat:` or equivalent), because the test-extension and the section-body are the same logical change.

No other commit combines unrelated concerns.

**Comandos de verificacion por fase TDD** (sec.M.0.1 + CLAUDE.local.md §0.1):

```bash
python -m pytest tests/ -v          # All pass, 0 fail
python -m ruff check .              # 0 warnings
python -m ruff format --check .     # Clean
python -m mypy .                    # No type errors
```

Atajo: `make verify` corre los 4 en orden.

**Supuestos post-Milestones A+B+C+D (consumidos, no re-implementados):**

- 528 tests existentes pasan limpios; HEAD en `d1d0598`; branch 248 commits ahead of origin/main.
- `skills/sbtdd/scripts/` completo (28 modulos Python + 2 reporters) con `make verify` verde en 33s.
- Templates bajo `templates/` completos: `CLAUDE.local.md.template`, `plugin.local.md.template`, `settings.json.template`, `spec-behavior-base.md.template`, `conftest.py.template`, `gitignore.fragment`.
- `LICENSE` (MIT) + `LICENSE-APACHE` (Apache-2.0) presentes en repo root desde Milestone A.
- `Makefile` con targets `test`, `lint`, `format`, `typecheck`, `verify` presente desde Milestone A.
- `pyproject.toml` con `mypy --strict`, ruff line-length 100, Python >=3.9 presente desde Milestone A.
- `CHANGELOG.md` con seccion `## Unreleased` presente desde Milestone D.
- `conftest.py` root-level con reporter tdd-guard presente desde Milestone A.

---

## Commit prefix policy

Precedente de Milestones A-D:

- `test:` para Red (test nuevo que falla).
- `feat:` para Green cuando introduce nueva superficie user-visible (ej. `skills/sbtdd/SKILL.md` es una nueva superficie user-visible: canonical entry point para `/sbtdd`).
- `chore:` para artefactos de distribucion: manifests (`plugin.json`, `marketplace.json`), CHANGELOG updates, fixtures, bookkeeping.
- `docs:` para documentacion pura (README, CONTRIBUTING).
- `refactor:` solo si tras Green hay cleanup explicito.

Mapping por tarea de este milestone:

| Task | Commit prefix | Rationale |
|------|---------------|-----------|
| 0 (pre-flight inventory) | N/A (no-op — read-only inventory, no files created) | — |
| 1 (SKILL.md Red: contract test skeleton) | `test:` | Contract test added, fails because `skills/sbtdd/SKILL.md` does not exist |
| 1b (SKILL.md Green: minimal skeleton) | `feat:` | Minimal frontmatter + H1 only — enough to pass Task 1 assertions |
| 2-4 (SKILL.md sections 1-3, 4-6, 7) | `feat:` → `feat:` → `feat:` | Progressive sections; each task extends `test_skill_md.py` (already committed in Task 1) alongside the SKILL.md section body — single logical change per the Red-Green split policy above (test-extension + section-body = one unit). Not split into separate `test:`/`feat:` commits |
| 5 (plugin.json) | `test:` → `chore:` | Red commits the contract test (fails), Green commits the manifest |
| 6 (marketplace.json) | `test:` → `chore:` | Red commits the contract test (fails), Green commits the catalog entry |
| 7 (README.md) | `test:` → `docs:` | Red commits the contract test (README stub fails most assertions), Green commits the rewrite |
| 8 (CONTRIBUTING.md) | `test:` → `docs:` | Red commits the contract test extension (fails -- file absent), Green commits the contributor guide |
| 9 (cross-artifact coherence test) | `test:` | New test file. **Per sec.M.5 row 1, adding a new test file is `test:`, not `chore:`** (addresses F12) |
| 10 (acceptance sweep + CHANGELOG update) | `chore:` | Bookkeeping: extends existing `CHANGELOG.md` `## Unreleased` section; no new surface |
| Version tag prep | N/A — no commit (user-driven, outside milestone execution scope) | Tag creation + push deferred to maintainer |

Todos los commits:

1. Ingles, sin `Co-Authored-By`, sin menciones a Claude/AI/asistente (`~/.claude/CLAUDE.md` §Git, INV-5..7).
2. Atomico — un task == un commit (o ciclo Red-Green cuando aplica).
3. Prefijo del mapa sec.M.5 via `commits.create` cuando se commitea codigo del plan; para bookkeeping (docs, manifests, acceptance) se usa `git commit` directo sin pasar por `commits.create`.

---

## Test isolation policy

Heredada de Milestones B-D: todos los tests que sustituyen atributos de modulos DEBEN usar `monkeypatch.setattr(...)` / `monkeypatch.setitem(...)` exclusivamente — nunca asignacion directa. La auto-restauracion de `monkeypatch` evita polucion cross-test.

Los contract tests de este milestone leen archivos reales del repo (no fixtures sinteticos). Cada test usa `pathlib.Path(__file__).parent.parent` para resolver repo root de forma path-independent y `.read_text("utf-8")` con encoding explicito (Windows/POSIX-safe). Ninguna tarea de Milestone E requiere `tmp_path` ni git repo sintetico.

---

## Frozen-module policy

**Milestones A, B, C y D estan congelados.** Este milestone NO modifica ningun archivo bajo `skills/sbtdd/scripts/` ni bajo `tests/` (excepto anadir cuatro nuevos test files). Ningun test existente debe romperse: si un test previo falla, hay que entender el motivo (no silenciarlo) y ajustar. Los unicos archivos tocables en Milestone E:

| Archivo | Razon | Contract test |
|---------|-------|---------------|
| `skills/sbtdd/SKILL.md` | Nueva superficie user-visible (dispatcher skill) | `tests/test_skill_md.py` |
| `.claude-plugin/plugin.json` | Plugin manifest para distribucion | `tests/test_plugin_manifest.py` |
| `.claude-plugin/marketplace.json` | BolivarTech marketplace catalog | `tests/test_marketplace_manifest.py` |
| `README.md` | Public GitHub README | `tests/test_readme.py` |
| `CONTRIBUTING.md` | Contributor guide | `tests/test_readme.py::test_readme_references_contributing` |

---

## Phase 0: Pre-flight (Task 0)

### Task 0: Pre-flight inventory

**Files:**
- No creation. Read-only inventory.

Este milestone no requiere fixtures (solo contract tests sobre archivos reales). La Fase 0 verifica que las precondiciones post-Milestone D estan intactas.

- [ ] **Step 1: Verify post-Milestone-D baseline**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green. If any fails, abort Milestone E and investigate regression before touching new artefacts.

- [ ] **Step 2: Verify destination paths are empty**

```bash
ls -la .claude-plugin/ 2>&1 || echo "absent: OK"
ls -la skills/sbtdd/SKILL.md 2>&1 || echo "absent: OK"
cat README.md | wc -l
```

Expected:
- `.claude-plugin/` does not exist (or is empty).
- `skills/sbtdd/SKILL.md` does not exist.
- `README.md` is 0 or 1 line (near-empty stub — this milestone rewrites it).

If `.claude-plugin/plugin.json` or `skills/sbtdd/SKILL.md` already exist, abort and investigate — Milestone E assumes greenfield artefacts.

- [ ] **Step 3: Read MAGI reference files**

Read-only reference (DO NOT copy verbatim — adapt to SBTDD vocabulary):

- `~/.claude/plugins/cache/bolivartech-plugins/magi/2.1.3/.claude-plugin/plugin.json` — manifest shape reference.
- `~/.claude/plugins/cache/bolivartech-plugins/magi/2.1.3/.claude-plugin/marketplace.json` — catalog shape reference.
- `~/.claude/plugins/cache/bolivartech-plugins/magi/2.1.3/README.md` — README structure reference (shields, sections).
- `~/.claude/plugins/cache/bolivartech-plugins/magi/2.1.3/skills/magi/SKILL.md` — SKILL.md structure reference.

Note: MAGI plugin is pinned at `v2.1.3`; our plugin ships at `v0.1.0`. Version numbers are NOT to be copied.

- [ ] **Step 4: No commit**

Task 0 is read-only inventory; no files created or modified.

---

## Phase 1: SKILL.md orchestrator (Tasks 1, 1b, 2-4)

Construimos el SKILL.md progresivamente para mantener bocados commiteables pequenos. **Task 1 (Red)** introduce el contract test que falla porque el archivo no existe. **Task 1b (Green)** commitea el esqueleto minimo que pasa las aserciones de Task 1. Tasks 2-4 anaden las 7 secciones obligatorias de sec.S.6.3 en tres pares Red-Green agrupados tematicamente:

- Task 2: Overview + Subcommand dispatch + Complexity gate (secciones 1-3).
- Task 3: Execution pipeline + sbtdd-rules + sbtdd-tdd-cycle (secciones 4-6 — el core operativo).
- Task 4: Fallback (seccion 7) + MAGI invocation patterns.

Cada task 2-4 extiende el contract test con nuevas aserciones PRIMERO (Red), corre tests para verificar que fallan, y LUEGO edita `skills/sbtdd/SKILL.md` para agregar las secciones que hagan verdes los nuevos asserts (Green). El commit unico de cada task 2-4 cubre ambos ficheros porque la extension del test y el body de las nuevas secciones son el mismo cambio logico -- el test no existia antes, no es un "test previo". Tasks 1 y 1b son dos commits separados porque introducen el archivo nuevo desde cero.

### Task 1: SKILL.md contract test (Red)

**Files:**
- Create: `tests/test_skill_md.py`

Objetivo (Red): introducir el contract test que valida frontmatter + presencia del titulo principal. El test falla porque `skills/sbtdd/SKILL.md` todavia no existe.

- [ ] **Step 1: Write failing test**

```python
# tests/test_skill_md.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for skills/sbtdd/SKILL.md.

Validates the orchestrator skill file is present, has valid YAML frontmatter,
declares the nine subcommands, documents the Python invocation pattern, and
follows the seven-section structure mandated by sec.S.6.3 of the contract.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"

NINE_SUBCOMMANDS = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
)


def _read_skill() -> str:
    assert SKILL_PATH.is_file(), f"SKILL.md missing at {SKILL_PATH}"
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_is_readable_and_non_empty() -> None:
    """Replaces the tautological `assert SKILL_PATH.exists()`.

    Verifies the file is present AND has enough bytes to be a real skill
    file (not an empty placeholder) AND is valid UTF-8. The trivial
    existence check is already covered implicitly by every other test
    via `_read_skill()`; this test adds the non-trivial property
    `len(text) > 100`.
    """
    assert SKILL_PATH.is_file(), f"SKILL.md missing at {SKILL_PATH}"
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert len(text) > 100, f"SKILL.md too short to be a real skill file ({len(text)} bytes)"


def test_skill_has_yaml_frontmatter() -> None:
    text = _read_skill()
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    # Frontmatter terminator on its own line
    assert re.search(r"^---\s*$", text, flags=re.MULTILINE), "frontmatter must close with ---"


def test_skill_frontmatter_declares_name_sbtdd() -> None:
    text = _read_skill()
    assert re.search(r"^name:\s*sbtdd\s*$", text, flags=re.MULTILINE), (
        "frontmatter must declare name: sbtdd"
    )


def test_skill_frontmatter_has_description_block() -> None:
    text = _read_skill()
    # Description is a scalar block (">" YAML multi-line folded or literal)
    assert re.search(r"^description:\s*>", text, flags=re.MULTILINE) or re.search(
        r"^description:\s*\|", text, flags=re.MULTILINE
    ), "frontmatter must declare description (folded or literal block)"


def test_skill_has_main_title() -> None:
    text = _read_skill()
    assert re.search(
        r"^#\s+SBTDD", text, flags=re.MULTILINE
    ), "SKILL.md must have a top-level H1 starting with 'SBTDD'"
```

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: FAIL (`skills/sbtdd/SKILL.md` does not exist — the assertion in `_read_skill()` triggers). 5 tests collected, all failing on `assert SKILL_PATH.is_file()` or similar.

- [ ] **Step 2: Run full verify**

```bash
python -m pytest tests/ -q   # expect 5 new failures (contract tests)
python -m ruff check tests/test_skill_md.py
python -m ruff format --check tests/test_skill_md.py
python -m mypy tests/test_skill_md.py
```

Lint/format/types must be clean on the new test file even though the test itself fails at runtime — Red phase means the test fails for the *correct* reason (missing artifact), not for a compile/type/lint error.

- [ ] **Step 3: Commit the Red test**

```bash
git add tests/test_skill_md.py
git commit -m "test: add SKILL.md contract test (failing — artifact not yet present)"
```

Rationale: per sec.M.5 row 1, a new test file with assertions that fail because the target artifact does not exist yet is the canonical Red commit. No production surface is introduced in this commit.

---

### Task 1b: SKILL.md skeleton (Green)

**Files:**
- Create: `skills/sbtdd/SKILL.md`

Objetivo (Green): crear el esqueleto minimo que hace pasar las 5 aserciones introducidas en Task 1 -- YAML frontmatter con `name: sbtdd` + description block folded + H1 comenzando con "SBTDD". Sin body; las secciones completas se anaden en Tasks 2-4.

- [ ] **Step 1: Write minimal SKILL.md skeleton**

Create `skills/sbtdd/SKILL.md` with frontmatter + H1 title only (bare minimum for the 5 Task 1 assertions to pass):

```markdown
---
name: sbtdd
description: >
  SBTDD + Superpowers multi-agent workflow orchestrator. Use when working on a
  project that follows the SBTDD methodology (Spec + Behavior + Test Driven
  Development) and needs to execute one of the nine workflow operations:
  init, spec, close-phase, close-task, status, pre-merge, finalize, auto,
  resume. Trigger phrases: "sbtdd init", "sbtdd close phase", "advance TDD
  phase", "run pre-merge review", "finalize SBTDD plan", "sbtdd auto",
  "shoot-and-forget SBTDD run", "resume SBTDD", "sbtdd resume", "continue
  interrupted SBTDD session", or any "/sbtdd <subcommand>" invocation. NOT
  suitable for projects that do not use SBTDD -- only invoke when the project
  has `sbtdd/spec-behavior-base.md` or `.claude/plugin.local.md` with `stack` set.
---

# SBTDD Workflow -- Spec + Behavior + Test Driven Development Orchestrator

<!-- SKELETON: Tasks 2-4 populate the seven mandated sections (Overview,
     Subcommand dispatch, Complexity gate, Execution pipeline, sbtdd-rules,
     sbtdd-tdd-cycle, Fallback). This comment is a **skeleton sentinel**
     that is rejected by `test_skill_has_no_skeleton_sentinel` (added in
     Task 2 alongside sentinel removal, per Caspar iter 3 fix) so that the
     Milestone E ship cannot silently land with an empty body. -->
```

**Rationale for the skeleton sentinel (F8 MAGI iter 2, Caspar iter 3 refined):** without a sentinel, if execution halts after Task 1b but before Task 2, the minimal SKILL.md would be a valid but empty skeleton that passes Task 1 assertions. The `<!-- SKELETON: ... -->` comment above is an explicit marker that **Task 2** adds a contract test against (moved from Task 4 per Caspar iter 3 — the test must land in the same task that removes the sentinel so the no-sentinel property is verified at the exact moment of removal, eliminating the unverified gap between Task 2 and Task 4). Any SKILL.md still carrying the sentinel at ship time fails that test. The sentinel is intentionally a comment (not rendered in the Claude Code UI) so it does not appear to users if Task 2 removes it as required.

- [ ] **Step 2: Run test to verify it passes**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: all 5 Task 1 tests pass.

- [ ] **Step 3: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green (528 + 5 = 533 tests).

- [ ] **Step 4: Commit the Green skeleton**

```bash
git add skills/sbtdd/SKILL.md
git commit -m "feat: add SKILL.md skeleton (orchestrator entry point, sections pending)"
```

Rationale: SKILL.md is a new user-visible surface (the `/sbtdd` entry point), so `feat:` is the correct prefix per sec.M.5 row 2 / commit-prefix table above. Task 1b introduces the minimum production artifact that turns Task 1 tests green.

**After Task 1 + Task 1b:** 5 tests passing, 2 commits (`test:` + `feat:`), strict Red-Green split preserved.

---

### Task 2: SKILL.md sections 1-3 (Overview + Subcommand dispatch + Complexity gate)

**Files:**
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `tests/test_skill_md.py`

Objetivo: anadir las primeras tres secciones del cuerpo (de las 7 de sec.S.6.3) + las aserciones correspondientes al contract test.

- [ ] **Step 1: Extend contract test**

Append to `tests/test_skill_md.py`:

```python
def test_skill_has_overview_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Overview\s*$", text, flags=re.MULTILINE), (
        "Overview section required (sec.S.6.3 item 1)"
    )


def test_skill_has_subcommand_dispatch_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Subcommand dispatch\s*$", text, flags=re.MULTILINE), (
        "Subcommand dispatch section required (sec.S.6.3 item 2)"
    )


def test_skill_mentions_all_nine_subcommands() -> None:
    text = _read_skill()
    for sub in NINE_SUBCOMMANDS:
        assert sub in text, f"SKILL.md must reference subcommand '{sub}'"


def test_skill_has_complexity_gate_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Complexity gate\s*$", text, flags=re.MULTILINE), (
        "Complexity gate section required (sec.S.6.3 item 3)"
    )


def test_skill_has_no_skeleton_sentinel() -> None:
    """F8 MAGI iter 2: reject SKILL.md shipping with the Task 1b skeleton sentinel.

    Task 1b creates SKILL.md with an explicit `<!-- SKELETON: ... -->` comment
    that flags the body as pending. Task 2 removes that comment as it populates
    the first three sections. This test is introduced in Task 2 (alongside the
    removal itself) so that the no-sentinel property is verified at the exact
    moment the sentinel is deleted, eliminating the window between sentinel
    removal and guard arming that would exist if this test were deferred to
    Task 4 (Caspar iter 3 fix).

    We match on the stable prefix of the comment (`<!-- SKELETON:` with the
    literal text used in Task 1b) rather than an exact full-text match so that
    a minor edit to the sentinel body in Task 1b does not require a matching
    edit here.
    """
    text = _read_skill()
    assert "<!-- SKELETON:" not in text, (
        "SKILL.md still contains the Task 1b skeleton sentinel; "
        "Task 2 must remove it while populating the first three sections"
    )
```

- [ ] **Step 2: Run to verify new tests fail**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: 5 new tests fail (sections do not exist yet; `test_skill_has_no_skeleton_sentinel` also fails because Task 1b's SKILL.md still contains the sentinel until Step 3 of this task removes it).

- [ ] **Step 3: Append sections 1-3 to SKILL.md**

After the H1 and before the `<!-- SKELETON: ... -->` sentinel comment, insert the following (and **delete the sentinel comment** — the `test_skill_has_no_skeleton_sentinel` contract test added in Step 1 of this task rejects any SKILL.md still carrying it):

```markdown
> `~/.claude/CLAUDE.md` has absolute precedence (INV-0). This skill is a
> dispatcher -- it never overrides the developer's global Code Standards.

## Overview

SBTDD (Spec + Behavior + Test Driven Development) combines three disciplines:

- **SDD (Spec Driven Development):** a textual specification (`sbtdd/spec-behavior.md`)
  is authoritative. No behavior is implemented that is not declared there.
- **BDD (Behavior Driven Development):** Given/When/Then scenarios in the spec
  document expected behavior in testable form.
- **TDD (Test Driven Development):** Red-Green-Refactor discipline, enforced
  physically by TDD-Guard hooks and procedurally by `/test-driven-development`.

This plugin orchestrates the SBTDD lifecycle end to end: from blank spec through
pre-merge gates to a ship-ready branch. Every state transition produces an atomic
git commit following the sec.M.5 prefix map (`test:` / `feat:` / `fix:` /
`refactor:` / `chore:`). Two mandatory pre-merge loops -- automated code review
(`/requesting-code-review`) and multi-perspective review (`/magi:magi`) -- gate
the branch before `/finishing-a-development-branch`.

The plugin follows the architectural pattern of MAGI (one skill, one entrypoint,
Python-backed scripts). The skill below is the dispatcher; all state-changing
logic lives in `scripts/run_sbtdd.py` and the nine `{subcommand}_cmd.py` modules.

## Subcommand dispatch

| Subcommand | Purpose | When to invoke |
|------------|---------|----------------|
| `init` | Bootstrap an SBTDD project (generate rules, hooks, skeleton spec) | Once per destination project, greenfield |
| `spec` | Run the spec pipeline (`/brainstorming` -> `/writing-plans` -> MAGI Checkpoint 2) | After `init`, before any code; iteratively until MAGI approves |
| `close-phase` | Close one TDD phase (Red/Green/Refactor) atomically: verify + commit + advance state | After implementing each phase, before moving to the next |
| `close-task` | Mark `[x]` in the plan + commit `chore:` + advance state to the next `[ ]` | After the Refactor phase of a task (also auto-invoked by `close-phase refactor`) |
| `status` | Read-only structured report of state + git + plan + drift | At any time, safe to invoke (read-only) |
| `pre-merge` | Run Loop 1 (`/requesting-code-review` until clean-to-go) + Loop 2 (`/magi:magi` gate) | When all plan tasks are `[x]` and `current_phase: "done"` |
| `finalize` | Run the sec.M.7 checklist + invoke `/finishing-a-development-branch` | After `pre-merge` returns exit 0 |
| `auto` | Shoot-and-forget full cycle: task loop + pre-merge + checklist (stops before `/finishing-a-development-branch`) | When the user wants unattended execution of an approved plan |
| `resume` | Diagnose interrupted runs (quota exhaustion, crash, reboot) and delegate recovery | After an `auto` run aborted mid-flight, or after any interruption |

Invocation pattern: `/sbtdd <subcommand> [args...]`. Under the hood, every
subcommand routes through `run_sbtdd.py` (see `## Execution pipeline` below).

## Complexity gate

Before delegating to Python, assess whether the user's request actually needs
state transitions. If the user asks a simple factual question about SBTDD
methodology (e.g., "what does INV-27 mean?", "what is the commit prefix for a
Refactor phase?"), respond directly from the embedded rules in `## sbtdd-rules`
below -- no Python invocation needed.

Invoke Python (via `run_sbtdd.py`) when the user asks for:

- Any of the nine subcommands (explicit: `/sbtdd init`, `/sbtdd close-phase`, ...).
- State interrogation that must be accurate (e.g., "what phase am I on?",
  "is my plan complete?").
- Any action that mutates `.claude/session-state.json`, the plan, or git.

Do NOT invoke Python for:

- Explaining methodology sections (answer from the embedded `## sbtdd-rules`).
- Clarifying commit prefix rules (answer from the embedded `## sbtdd-tdd-cycle`).
- Meta-questions about the plugin (version, repository, license) -- answer
  from the `plugin.json` manifest directly.
```

- [ ] **Step 4: Run tests to verify green**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: 10 tests pass (5 from Task 1 + 5 from Task 2).

- [ ] **Step 5: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/SKILL.md tests/test_skill_md.py
git commit -m "feat: add SKILL.md Overview, Subcommand dispatch, Complexity gate sections"
```

---

### Task 3: SKILL.md sections 4-6 (Execution pipeline + sbtdd-rules + sbtdd-tdd-cycle)

**Files:**
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `tests/test_skill_md.py`

Objetivo: anadir el core operativo: el patron de invocacion de Python + las dos secciones embebidas de reglas. Estas son las secciones mas densas del SKILL.md.

- [ ] **Step 1: Extend contract test**

Append to `tests/test_skill_md.py`:

```python
def test_skill_has_execution_pipeline_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Execution pipeline\s*$", text, flags=re.MULTILINE), (
        "Execution pipeline section required (sec.S.6.3 item 4)"
    )


def test_skill_documents_python_invocation_pattern() -> None:
    text = _read_skill()
    # The canonical invocation line from sec.S.6.3 item 4
    assert re.search(
        r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/sbtdd/scripts/run_sbtdd\.py",
        text,
    ), "SKILL.md must document the ${CLAUDE_PLUGIN_ROOT}/.../run_sbtdd.py pattern"


def test_skill_has_sbtdd_rules_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+sbtdd-rules\s*$", text, flags=re.MULTILINE), (
        "sbtdd-rules section required (sec.S.6.3 item 5)"
    )


def test_skill_has_sbtdd_tdd_cycle_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+sbtdd-tdd-cycle\s*$", text, flags=re.MULTILINE), (
        "sbtdd-tdd-cycle section required (sec.S.6.3 item 6)"
    )


def test_skill_rules_reference_commit_prefix_map() -> None:
    text = _read_skill()
    # All five sec.M.5 prefixes must appear, confirming the rules section is non-trivial
    for prefix in ("test:", "feat:", "fix:", "refactor:", "chore:"):
        assert prefix in text, f"SKILL.md must reference commit prefix '{prefix}'"


def test_skill_mentions_invariants() -> None:
    text = _read_skill()
    # At minimum reference the critical invariants mentioned throughout the plugin
    for inv in ("INV-0", "INV-27", "INV-28", "INV-29"):
        assert inv in text, f"SKILL.md must reference invariant '{inv}'"
```

- [ ] **Step 2: Run to verify new tests fail**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: 6 new tests fail.

- [ ] **Step 3: Append sections 4-6 to SKILL.md**

Append after the Complexity gate section:

```markdown
## Execution pipeline

All state-changing subcommands route through a single Python entrypoint:

```
python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <subcommand> [args...]
```

The dispatcher (`run_sbtdd.py`) parses the subcommand, validates preconditions
(INV-12), loads `.claude/session-state.json` (INV-4) and `.claude/plugin.local.md`,
and delegates to `skills/sbtdd/scripts/{subcommand}_cmd.py`. Every subcommand
emits exit codes according to the canonical taxonomy (sec.S.11.1):

| Exit | Symbol | Meaning |
|------|--------|---------|
| 0 | SUCCESS | Nominal completion |
| 1 | USER_ERROR | Invalid flags, unknown subcommand |
| 2 | PRECONDITION_FAILED | Missing dependency, schema mismatch, uppercase placeholder tokens in spec (INV-27) |
| 3 | DRIFT_DETECTED | State/git/plan divergence; user must resolve manually (INV-17) |
| 4 | FILE_CONFLICT | `init` aborted due to existing non-empty artifacts |
| 5 | SMOKE_TEST_FAILED | `init` Phase 4 (post-setup smoke test) failed |
| 6 | VERIFICATION_IRREMEDIABLE | sec.M.0.1 verification failed; auto cannot recover |
| 7 | LOOP1_DIVERGENT | `/requesting-code-review` did not converge in 10 iter |
| 8 | MAGI_GATE_BLOCKED | `/magi:magi` verdict below threshold after max iter (INV-11) |
| 9 | CHECKLIST_FAILED | `finalize` sec.M.7 checklist item failed |
| 11 | QUOTA_EXHAUSTED | Anthropic API quota detected via `quota_detector.py` (INV-30) |
| 130 | INTERRUPTED | SIGINT (Ctrl+C) |

**MAGI invocation pattern.** Two subcommands invoke MAGI:
- `spec` at Checkpoint 2: `/magi:magi revisa @sbtdd/spec-behavior.md y @planning/claude-plan-tdd-org.md`.
  Iteration cap: `magi_max_iterations` (default 3). Exceeding escalates to user with candidate root causes.
- `pre-merge` Loop 2: after Loop 1 returns clean-to-go, invoke `/magi:magi` on
  the accumulated diff. Same iteration cap (default 3). `auto` uses `auto_magi_max_iterations`
  (default 5) to compensate for the absence of human supervision.

Both invocations honor **INV-28** (degraded verdict with fewer than 3 agents
does NOT count as a loop-exit signal; consumes one iteration and re-invokes
MAGI). Exception: `STRONG_NO_GO` degraded still aborts immediately (2 agents
saying NO-GO is evidence enough).

Both invocations honor **INV-29** (every MAGI finding that requires a code change
MUST be evaluated by `/receiving-code-review` before the mini-cycle TDD is
applied; rejected findings are logged and fed back as context into the next
MAGI iteration to break sterile loops).

## sbtdd-rules

The authoritative rules live in the destination project's
`CLAUDE.local.md` (installed from `templates/CLAUDE.local.md.template` by
`sbtdd init`). The summary below lets the skill answer common rule questions
without opening Python.

### Commit prefix map (sec.M.5)

| Context | Prefix | Example |
|---------|--------|---------|
| Red phase close | `test:` | `test: add parser edge case for empty input` |
| Green phase close (new feature) | `feat:` | `feat: implement parser minimum viable logic` |
| Green phase close (bug fix) | `fix:` | `fix: handle trailing whitespace in values` |
| Refactor phase close | `refactor:` | `refactor: extract validation into separate fn` |
| Task close (checkbox `[x]`) | `chore:` | `chore: mark task 3 complete` |
| Loop 1/2 mini-cycle fix | `test:` -> `fix:` -> `refactor:` | Three atomic commits per finding |

### Commit discipline (INV-5..8)

- English prose only (no Spanish, no other languages).
- No `Co-Authored-By` lines.
- No references to Claude / AI / assistant in commit messages.
- Atomic: one commit = one concern = one prefix. Never mix phases or tasks.
- Outside the four authorized categories (phase close, task close, Loop 1 fix,
  Loop 2 fix), commits require explicit user permission (INV-8).

### Plan-approved contract (`plan_approved_at != null`)

Once `/sbtdd spec` approves the plan (sets `plan_approved_at` in
`.claude/session-state.json`), the plugin is pre-authorized to create commits
in the four categories above without prompting. Outside those categories, the
user is still prompted.

### Degraded MAGI (INV-28)

A MAGI verdict with `degraded: true` (fewer than 3 agents returned usable
output) NEVER counts as a loop-exit signal. The iteration is consumed and
MAGI is re-invoked. Exception: `STRONG_NO_GO` degraded aborts immediately
(sec.S.10.3).

### Spec-base placeholder rejection (INV-27)

`sbtdd/spec-behavior-base.md` MUST NOT contain the uppercase word-boundary
tokens (the three uppercase placeholder markers enumerated in INV-27, rule of sec.S.10.4 of the contract). There is no `--force` override. Rationale:
specs with placeholders waste MAGI iterations at Checkpoint 2. Lowercase
"todos" (Spanish natural text meaning "all") is explicitly allowed.

### Global authority (INV-0)

`~/.claude/CLAUDE.md` overrides every other configuration file, including
this SKILL.md, `CLAUDE.local.md`, and `plugin.local.md`. No override flags
exist. Every subcommand honors (does not redefine) the developer's global
Code Standards.

## sbtdd-tdd-cycle

The Red-Green-Refactor cycle is enforced by two layers:

- **TDD-Guard** (physical): hooks intercept file writes in real time. Writing
  code without a failing test triggers a hard block. Toggle via quick prompt
  (`tdd-guard on` / `tdd-guard off`) configured through the `UserPromptSubmit`
  hook.
- **`/test-driven-development`** (procedural): the Superpowers skill guides
  the agent through the cycle disciplinedly. Invoked at the start of each task.

### Red phase

- Allowed: failing tests (assertion failures OR compile/type errors on the
  absent implementation).
- Blocked: production code, tests that pass trivially.
- Close ritual (three steps, strict):
  1. `/verification-before-completion` -- confirm the test fails for the correct reason.
  2. Atomic commit with prefix `test:`.
  3. Advance `.claude/session-state.json`: `current_phase: "green"`, update
     `phase_started_at_commit`, `last_verification_at`, `last_verification_result`.

### Green phase

- Allowed: minimum implementation that turns the Red tests green.
- Blocked: modifying tests, adding unrelated functionality.
- Close ritual: `/verification-before-completion` + commit prefix `feat:` (new
  feature) or `fix:` (hardening / bug-fix) + state advance to `refactor`.

### Refactor phase

- Allowed: structural improvements, renames, deduplication, doc-comments.
- Blocked: changing behavior, adding functionality, editing tests.
- Close ritual: `/verification-before-completion` + commit `refactor:` +
  state advance to `done` + auto-invoke `close-task` (mark `[x]` + commit
  `chore:` + advance to next `[ ]` or set `current_phase: "done"` if plan complete).

### When a test fails unexpectedly

Invoke `/systematic-debugging` BEFORE proposing a fix. Diagnose the root cause
(missing implementation vs. environmental issue vs. test bug) and then apply
the appropriate fix. Do not patch symptoms.

### Close-phase delegation

The agent should NOT attempt the three-step close by hand. Always invoke
`/sbtdd close-phase` -- the Python command handles the drift check, invokes
`/verification-before-completion`, runs `commits.create` with the validated
prefix, and updates the state file atomically. Manual close = drift risk.
```

- [ ] **Step 4: Run tests to verify green**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: 16 tests pass (10 from Tasks 1-2 + 6 new).

- [ ] **Step 5: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/SKILL.md tests/test_skill_md.py
git commit -m "feat: add SKILL.md Execution pipeline, sbtdd-rules, sbtdd-tdd-cycle sections"
```

---

### Task 4: SKILL.md section 7 (Fallback) + MAGI patterns recap + structure finalization

**Files:**
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `tests/test_skill_md.py`

Objetivo: cerrar el SKILL.md con el fallback (cuando Python no disponible) y verificar la secuencia de secciones via test.

- [ ] **Step 1: Extend contract test**

Append to `tests/test_skill_md.py`:

```python
def test_skill_has_fallback_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Fallback\s*$", text, flags=re.MULTILINE), (
        "Fallback section required (sec.S.6.3 item 7)"
    )


def test_skill_sections_in_correct_order() -> None:
    """sec.S.6.3: sections appear in the mandated order."""
    text = _read_skill()
    required_headers = [
        "## Overview",
        "## Subcommand dispatch",
        "## Complexity gate",
        "## Execution pipeline",
        "## sbtdd-rules",
        "## sbtdd-tdd-cycle",
        "## Fallback",
    ]
    positions = []
    for header in required_headers:
        idx = text.find("\n" + header + "\n")
        assert idx >= 0, f"missing header line: {header}"
        positions.append(idx)
    assert positions == sorted(positions), (
        f"section headers are out of order: {positions} vs sorted {sorted(positions)}"
    )


def test_skill_has_nontrivial_body() -> None:
    """Content-based non-triviality check (F7 MAGI iter 2).

    An earlier draft of this test pinned a `>= 200 lines` floor. Line count
    is an arbitrary proxy; we now assert the **content** property: every one
    of the seven sections mandated by sec.S.6.3 must be present with a
    non-empty body (at least one non-blank line after the header before the
    next header or EOF). If each section has real content, line count is a
    natural consequence (~300+ lines as shipped) and the prior floor adds
    nothing.

    This is independent of `test_skill_sections_in_correct_order` (which
    pins ORDER) and of `test_skill_has_*_section` (which pin PRESENCE of
    the header). This test pins that each section has a body.
    """
    text = _read_skill()
    required_headers = [
        "## Overview",
        "## Subcommand dispatch",
        "## Complexity gate",
        "## Execution pipeline",
        "## sbtdd-rules",
        "## sbtdd-tdd-cycle",
        "## Fallback",
    ]
    # Find each header's position; then check that the next non-blank line
    # after the header is NOT another header (which would indicate an empty
    # section).
    for header in required_headers:
        pattern = re.compile(rf"^{re.escape(header)}\s*$", flags=re.MULTILINE)
        match = pattern.search(text)
        assert match is not None, f"missing header: {header}"
        # Slice from end of header to find the next non-blank line
        body_start = match.end()
        # Look at the next ~500 chars (enough for a real section body)
        window = text[body_start : body_start + 500]
        # Strip the immediate newline after the header and any blank lines
        stripped = window.lstrip("\n \t")
        assert stripped, f"section '{header}' has no body before EOF"
        # Ensure the first non-blank line after the header is NOT another H2
        first_line = stripped.split("\n", 1)[0]
        assert not first_line.startswith("## "), (
            f"section '{header}' is empty (immediately followed by another H2: '{first_line}')"
        )
```

- [ ] **Step 2: Run to verify new tests fail**

Expected: `test_skill_has_fallback_section` and `test_skill_sections_in_correct_order` fail (no Fallback yet). `test_skill_has_nontrivial_body` fails because the Fallback section is still absent (its header is missing in Task 3 output). Note: `test_skill_has_no_skeleton_sentinel` was introduced in Task 2 (not Task 4) and is already green by this point (Caspar iter 3 fix).

- [ ] **Step 3: Append Fallback section to SKILL.md**

```markdown
## Fallback

If Python is not available (e.g., unusual sandbox, bootstrapping environment,
explicit "simulate" request), respond to the user with structured manual
instructions matching the invoked subcommand:

- **`init` fallback:** list the seven mandatory dependencies (sec.S.1.3) and
  the five files `init` would generate. Ask the user to verify each dependency
  and copy the template files manually from `templates/`.
- **`spec` fallback:** walk the user through `/brainstorming` -> `/writing-plans`
  -> MAGI Checkpoint 2 manually. Emit the canonical MAGI invocation
  (`/magi:magi revisa @sbtdd/spec-behavior.md y @planning/claude-plan-tdd-org.md`)
  with explicit iteration cap 3 (INV-11).
- **`close-phase` fallback:** remind the user of the three-step close ritual
  (verification -> atomic commit with prefix -> state update). Emit the exact
  commit prefix from the commit prefix map above.
- **`pre-merge` fallback:** instruct the user to run Loop 1
  (`/requesting-code-review` until clean-to-go, cap 10 iter) followed by Loop 2
  (`/magi:magi`, cap 3 iter, honor INV-28 and INV-29).
- **`auto` fallback:** the auto mode is Python-exclusive (no manual analogue)
  because it requires coordinated dispatch across six phases. If Python is not
  available, tell the user to run the phases sequentially via manual invocations
  of `spec`, `close-phase`, `close-task`, `pre-merge`, `finalize` (in that order).
- **`resume` fallback:** walk the user through the diagnostic manually: read
  `.claude/session-state.json`, inspect `git status`, inspect recent commit
  messages, and determine the appropriate next subcommand based on
  `current_phase`.

In all fallback modes, honor INV-0 (global CLAUDE.md prevails), INV-5..8
(commit discipline), INV-27 (spec-base placeholder rejection), INV-28 (MAGI
degraded non-exit), and INV-29 (receiving-code-review gate) manually.

## Notes

- The plugin is pre-1.0 (`v0.1.x`); the schema of `session-state.json` and
  `plugin.local.md` MAY change between minor versions. Consult `CHANGELOG.md`
  before upgrading.
- For the full functional contract, see
  `sbtdd/sbtdd-workflow-plugin-spec-base.md` in the plugin repository.
- Authoritative methodology lives in the destination project's `CLAUDE.local.md`
  (installed by `sbtdd init`); the `sbtdd-rules` and `sbtdd-tdd-cycle` sections
  above are summaries intended for in-skill reference, not redefinitions.
```

- [ ] **Step 4: Run tests to verify green**

Run: `python -m pytest tests/test_skill_md.py -v`
Expected: 19 tests pass (16 from Tasks 1-3 + 3 new: fallback, section-order, nontrivial-body). The `no-skeleton-sentinel` test landed in Task 2, not Task 4 (Caspar iter 3 fix).

- [ ] **Step 5: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green (528 + 19 = 547 tests at this checkpoint; final Milestone E tally reconciled in Task 10 / Acceptance).

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/SKILL.md tests/test_skill_md.py
git commit -m "feat: add SKILL.md Fallback section and Notes; finalize orchestrator skill"
```

---

## Phase 2: Plugin manifests (Tasks 5-6)

Dos tareas independientes que pueden ejecutarse en paralelo si se desea. Cada una es un Red-Green: contract test primero, luego manifest que pasa el test.

### Task 5: `.claude-plugin/plugin.json`

**Files:**
- Create: `tests/test_plugin_manifest.py`
- Create: `.claude-plugin/plugin.json`

Objetivo: manifest mirror of MAGI per sec.S.3.1.

- [ ] **Step 1: Write failing test**

```python
# tests/test_plugin_manifest.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for .claude-plugin/plugin.json.

Validates the plugin manifest follows sec.S.3.1 of the functional contract:
name, version, description, author, repository, license, keywords, skills path.
Version MUST match .claude-plugin/marketplace.json (sec.S.3.3).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _load_plugin() -> dict:
    assert PLUGIN_JSON.is_file(), f"plugin.json missing at {PLUGIN_JSON}"
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))


def test_plugin_json_is_valid_json() -> None:
    _load_plugin()


def test_plugin_name_is_sbtdd_workflow() -> None:
    d = _load_plugin()
    assert d["name"] == "sbtdd-workflow"


def test_plugin_version_is_semver() -> None:
    d = _load_plugin()
    assert re.match(r"^\d+\.\d+\.\d+$", d["version"]), f"version must be semver: {d['version']}"


def test_plugin_version_is_zero_one_zero_for_v0_1_ship() -> None:
    d = _load_plugin()
    assert d["version"] == "0.1.0", "Milestone E ships v0.1.0"


def test_plugin_has_description() -> None:
    d = _load_plugin()
    assert isinstance(d["description"], str) and len(d["description"]) >= 20


def test_plugin_author_structure() -> None:
    d = _load_plugin()
    assert isinstance(d["author"], dict)
    assert "name" in d["author"]
    assert "url" in d["author"]


def test_plugin_repository_points_to_bolivartech() -> None:
    d = _load_plugin()
    assert "BolivarTech/sbtdd-workflow" in d["repository"]


def test_plugin_license_is_dual_mit_apache() -> None:
    d = _load_plugin()
    assert d["license"] == "MIT OR Apache-2.0"


def test_plugin_has_skills_path() -> None:
    d = _load_plugin()
    assert d["skills"] == "./skills/"


def test_plugin_keywords_include_sbtdd() -> None:
    d = _load_plugin()
    assert "sbtdd" in d.get("keywords", [])


def test_plugin_version_syncs_with_marketplace() -> None:
    """sec.S.3.3: plugin.json version MUST match marketplace.json version.

    Between Task 5 (plugin.json created) and Task 6 (marketplace.json created),
    marketplace.json does not exist yet. We skip (not silently pass) during
    that window -- the test becomes an unconditional assertion once Task 6
    lands. Silent early-return would hide genuine regressions once both files
    are in place, so skip is preferred.
    """
    if not MARKETPLACE_JSON.is_file():
        pytest.skip("marketplace.json not yet written (Task 6 pending)")
    plugin_v = _load_plugin()["version"]
    marketplace = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    marketplace_top_v = marketplace["version"]
    assert plugin_v == marketplace_top_v, (
        f"version mismatch: plugin.json={plugin_v}, marketplace.json={marketplace_top_v}"
    )
    # And the entry for this plugin inside the marketplace catalog
    for entry in marketplace["plugins"]:
        if entry["name"] == "sbtdd-workflow":
            assert entry["version"] == plugin_v, (
                f"marketplace plugin entry version mismatch: {entry['version']} vs {plugin_v}"
            )
            break
    else:  # pragma: no cover
        raise AssertionError("sbtdd-workflow entry missing from marketplace.json")
```

Run: `python -m pytest tests/test_plugin_manifest.py -v`
Expected: FAIL (`.claude-plugin/plugin.json` does not exist). The version-sync test is `pytest.skip`ped because `marketplace.json` is absent (added in Task 6).

- [ ] **Step 2: Commit the Red test**

```bash
git add tests/test_plugin_manifest.py
git commit -m "test: add plugin.json contract test (failing — manifest not yet present)"
```

- [ ] **Step 3: Create `.claude-plugin/plugin.json`**

```bash
mkdir -p .claude-plugin
```

Create `.claude-plugin/plugin.json`:

```json
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

**Note on `repository` field form (F13 from MAGI iter 1):** Claude Code plugin manifests accept either a plain URL string or an object `{ "url": "...", "type": "git" }`. MAGI v2.1.3 uses the **string form** (`"repository": "https://github.com/BolivarTech/magi"`) — we match that form for paridad. If a future Claude Code spec release requires the object form, a migration commit will be scheduled in v0.2.

- [ ] **Step 4: Run tests to verify green**

Run: `python -m pytest tests/test_plugin_manifest.py -v`
Expected: 10 tests pass; `test_plugin_version_syncs_with_marketplace` is skipped because `marketplace.json` does not exist yet (Task 6). Count: 10 passed, 1 skipped.

- [ ] **Step 5: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green (skips are green).

- [ ] **Step 6: Commit the Green manifest**

```bash
git add .claude-plugin/plugin.json
git commit -m "chore: add plugin.json manifest (version 0.1.0, MAGI-parity schema)"
```

---

### Task 6: `.claude-plugin/marketplace.json`

**Files:**
- Create: `tests/test_marketplace_manifest.py`
- Create: `.claude-plugin/marketplace.json`
- Modify: `tests/test_plugin_manifest.py` (activate version-sync branch -- already written)

Objetivo: BolivarTech marketplace catalog entry per sec.S.3.2.

- [ ] **Step 1: Write failing test**

```python
# tests/test_marketplace_manifest.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for .claude-plugin/marketplace.json.

Validates the BolivarTech marketplace catalog per sec.S.3.2: owner/plugins
structure, sbtdd-workflow entry, tags, category, source path. Version MUST
match plugin.json (sec.S.3.3).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _load_marketplace() -> dict:
    assert MARKETPLACE_JSON.is_file(), f"marketplace.json missing at {MARKETPLACE_JSON}"
    return json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))


def test_marketplace_json_is_valid_json() -> None:
    _load_marketplace()


def test_marketplace_name_is_bolivartech_plugins() -> None:
    d = _load_marketplace()
    assert d["name"] == "bolivartech-plugins"


def test_marketplace_has_owner_structure() -> None:
    d = _load_marketplace()
    assert isinstance(d["owner"], dict)
    assert d["owner"]["name"] == "BolivarTech"
    assert "github.com/BolivarTech" in d["owner"]["url"]


def test_marketplace_contains_sbtdd_workflow_entry() -> None:
    d = _load_marketplace()
    names = [p["name"] for p in d.get("plugins", [])]
    assert "sbtdd-workflow" in names, f"sbtdd-workflow missing from plugins: {names}"


def test_marketplace_sbtdd_entry_has_required_fields() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    for field in ("name", "description", "version", "author", "source", "category", "homepage", "tags"):
        assert field in entry, f"missing field '{field}' in sbtdd-workflow entry"


def test_marketplace_sbtdd_entry_source_is_relative() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert entry["source"] == "./", "source must be './' for root-level plugin manifest"


def test_marketplace_tags_include_sbtdd() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert "sbtdd" in entry["tags"]


def test_marketplace_has_top_level_version() -> None:
    d = _load_marketplace()
    assert "version" in d, "top-level version required for marketplace update tracking"


def test_marketplace_homepage_points_to_repo() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert "BolivarTech/sbtdd-workflow" in entry["homepage"]
```

Run: `python -m pytest tests/test_marketplace_manifest.py -v`
Expected: FAIL (file does not exist).

- [ ] **Step 2: Commit the Red test**

```bash
git add tests/test_marketplace_manifest.py
git commit -m "test: add marketplace.json contract test (failing — catalog not yet present)"
```

- [ ] **Step 3: Create `.claude-plugin/marketplace.json`**

```json
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
      "tags": [
        "sbtdd",
        "tdd",
        "workflow",
        "multi-agent",
        "superpowers"
      ]
    }
  ]
}
```

**Note on the `"$schema"` URL (F8 MAGI iter 1 + F6 MAGI iter 2):** the schema URL matches MAGI v2.1.3's `marketplace.json` literally (`https://anthropic.com/claude-code/marketplace.schema.json`). We include it for **parity with MAGI**, not because the URL has been formally verified as resolvable — Claude Code does not officially publish a marketplace schema as of `v0.1.0` ship date.

**Explicit risk acceptance (F6 MAGI iter 2):**

- The field is **parity, not validation**. No runtime assertion ties it to a working network fetch; JSON does not support inline comments, so the explanation lives here in the plan and in `CHANGELOG.md` under `## Unreleased` → `Deferred`.
- A runtime smoke test of the form `requests.head(url)` would require a network dependency (currently zero) and CI egress (not configured for v0.1.0). **Rejected** for Milestone E.
- **Contingency:** if the schema URL is ever confirmed to 404 or Claude Code emits a warning about it, a follow-up `chore:` commit drops the `$schema` field across both plugins in lockstep. The CHANGELOG `## Unreleased` `Deferred` section tracks this item as "verify `$schema` URL resolves post-push; fallback: drop field if Anthropic removes it."

- [ ] **Step 4: Run tests to verify green**

Run:
```bash
python -m pytest tests/test_marketplace_manifest.py tests/test_plugin_manifest.py -v
```
Expected: 9 marketplace tests + 11 plugin tests pass (the previously-skipped `test_plugin_version_syncs_with_marketplace` now activates and asserts both manifests at `0.1.0`).

- [ ] **Step 5: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 6: Commit the Green catalog**

```bash
git add .claude-plugin/marketplace.json
git commit -m "chore: add marketplace.json BolivarTech catalog entry (version 0.1.0)"
```

---

## Phase 3: README + CONTRIBUTING (Tasks 7-8)

### Task 7: `README.md` public GitHub README

**Files:**
- Create: `tests/test_readme.py`
- Modify: `README.md` (currently near-empty stub)

Objetivo: README paridad con MAGI README -- shields, "Why SBTDD?" section, installation (marketplace + local dev), usage table con 9 subcomandos, architecture tree, test coverage, license.

- [ ] **Step 1: Write failing test**

```python
# tests/test_readme.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for README.md (public GitHub README).

Validates presence of the required sections (parity with MAGI README):
shields, Why SBTDD?, Installation, Usage (subcommand table), Architecture,
Tests, License. Intentionally does NOT assert on prose content to avoid
over-coupling.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
CONTRIBUTING_PATH = REPO_ROOT / "CONTRIBUTING.md"

NINE_SUBCOMMANDS = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
)


def _read_readme() -> str:
    assert README_PATH.is_file(), f"README.md missing at {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


def test_readme_exists_and_non_empty() -> None:
    text = _read_readme()
    assert len(text) > 2000, f"README.md too short ({len(text)} chars); expected >= 2000"


def test_readme_has_title() -> None:
    text = _read_readme()
    assert re.search(r"^#\s+SBTDD", text, flags=re.MULTILINE), (
        "README must have a top-level H1 starting with 'SBTDD'"
    )


def test_readme_has_python_shield() -> None:
    text = _read_readme()
    assert "python-3.9" in text.lower() or "python 3.9" in text.lower(), (
        "README must declare Python 3.9+ via shield or prose"
    )


def test_readme_has_license_shield() -> None:
    text = _read_readme()
    assert "MIT" in text and "Apache" in text, (
        "README must reference dual MIT OR Apache-2.0 license"
    )


def test_readme_why_sbtdd_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Why SBTDD\?", text, flags=re.MULTILINE), (
        "README must have 'Why SBTDD?' section (parity with MAGI README)"
    )


def test_readme_installation_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Installation\s*$", text, flags=re.MULTILINE)


def test_readme_installation_references_marketplace_add() -> None:
    text = _read_readme()
    assert "/plugin marketplace add" in text, "README must document marketplace add command"
    assert "BolivarTech/sbtdd-workflow" in text


def test_readme_installation_references_plugin_install() -> None:
    text = _read_readme()
    assert "/plugin install sbtdd-workflow" in text


def test_readme_installation_references_local_dev_symlink() -> None:
    text = _read_readme()
    assert "claude --plugin-dir" in text or ".claude/skills" in text, (
        "README must document at least one local-dev mechanism"
    )


def test_readme_usage_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Usage\s*$", text, flags=re.MULTILINE)


def test_readme_mentions_all_nine_subcommands() -> None:
    text = _read_readme()
    for sub in NINE_SUBCOMMANDS:
        # Match as standalone token (prevents substring false positives like "status" in "statuses")
        assert re.search(rf"\b{re.escape(sub)}\b", text), (
            f"README must mention subcommand '{sub}'"
        )


def test_readme_end_to_end_flow() -> None:
    text = _read_readme()
    # Must describe the typical flow init -> spec -> close-phase -> pre-merge -> finalize
    assert "init" in text and "spec" in text and "pre-merge" in text and "finalize" in text


def test_readme_architecture_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Architecture\s*$", text, flags=re.MULTILINE) or re.search(
        r"^##\s+Project Structure\s*$", text, flags=re.MULTILINE
    ), "README must have Architecture or Project Structure section"


def test_readme_tests_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+(Running )?Tests", text, flags=re.MULTILINE) or re.search(
        r"make verify", text
    ), "README must document how to run tests"


def test_readme_license_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+License\s*$", text, flags=re.MULTILINE)


def test_readme_references_contributing() -> None:
    text = _read_readme()
    assert "CONTRIBUTING" in text or "Contributing" in text, (
        "README must reference CONTRIBUTING.md or a Contributing section"
    )


def test_readme_no_uppercase_placeholders() -> None:
    """Extends the rationale of INV-27 (which applies to `sbtdd/spec-behavior-base.md`)
    to the public README. INV-27 itself is scoped to the spec-base input of the
    `/sbtdd spec` pipeline; this test does not enforce INV-27 on the README (which
    is outside its formal scope) but prevents placeholder markers from shipping
    in the GitHub-visible surface for the same rationale: they signal unfinished
    work and erode perceived quality.
    """
    text = _read_readme()
    # Tokens are assembled at runtime so this test file itself never embeds them
    # literally. Concatenating the two halves ("TO" + "DO") keeps the source
    # clean under INV-27-like scans without needing a path-exclusion list.
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"README contains forbidden placeholder '{token}' (extends INV-27 rationale to README)"
        )
```

Run: `python -m pytest tests/test_readme.py -v`
Expected: several tests FAIL (README is a 1-line stub).

- [ ] **Step 2: Rewrite `README.md` in full**

Overwrite `README.md` entirely with:

````markdown
# SBTDD Workflow -- Spec + Behavior + Test Driven Development Orchestrator

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Ruff](https://img.shields.io/badge/linter-ruff-orange.svg)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/types-mypy%20strict-informational.svg)](https://mypy-lang.org/)

<!--
F2 rationale: a live "tests passing" badge requires a GitHub Actions workflow
publishing status. Milestone E ships v0.1.0 without CI configured; we therefore
ship only the four static shields above. A dynamic "tests passing" shield
(backed by `.github/workflows/ci.yml` running `make verify`) is scheduled for
v0.2.0 and tracked under CHANGELOG's `## Unreleased` section as a deferred item.
-->


A Claude Code plugin that operationalizes **SBTDD (Spec + Behavior + Test Driven Development)** combined with the **Superpowers multi-agent skill ecosystem**.

One skill (`/sbtdd`), nine subcommands, five invariant-preserving phases: from blank spec to ship-ready branch, with mandatory pre-merge gates driven by code review + MAGI multi-perspective consensus.

---

## Why SBTDD? Why multi-agent?

### The problem

Classical TDD (Red-Green-Refactor) disciplines the implementation step, but leaves upstream decisions -- what to build, how to model the behavior, whether the design is sound -- as prose and intuition. Two chronic failure modes follow:

- **Scope drift:** the implementation satisfies its tests but diverges from the original intent because the intent was never written down atomically.
- **Local optimization:** each test passes, each commit is clean, yet the accumulated design has trade-offs nobody surfaced explicitly.

### The SBTDD answer

SBTDD layers three complementary disciplines:

| Discipline | Artifact | Authority |
|------------|----------|-----------|
| **SDD** (Spec Driven Development) | `sbtdd/spec-behavior.md` | Source of truth for what the system does |
| **BDD** (Behavior Driven Development) | Given/When/Then scenarios inside the spec | Translates intent into testable observations |
| **TDD** (Test Driven Development) | `planning/claude-plan-tdd.md` + commits | Enforces the Red-Green-Refactor discipline |

No behavior is implemented that is not declared in the spec; no code lands without a failing test reproducing its behavior; every commit is atomic and prefixed (`test:` / `feat:` / `fix:` / `refactor:` / `chore:` / `docs:`).

### Why multi-agent pre-merge?

SBTDD gates every branch through **two independent review loops** before merge:

1. **Loop 1 -- automated code review** (`/requesting-code-review`): mechanical findings (security, style, obvious bugs) are surfaced and applied via mini-cycle TDD until the diff is clean.
2. **Loop 2 -- MAGI multi-perspective review** (`/magi:magi`): three agents (Scientist, Pragmatist, Critic) evaluate trade-offs from orthogonal lenses. Their consensus -- not any single verdict -- is the gate.

Why separate? A WARNING from a mechanical reviewer can drag the MAGI agents into CONDITIONAL verdicts, contaminating the signal. Running them sequentially and independently keeps each verdict unambiguous (see CLAUDE.local.md sec.6).

### When does it pay off?

SBTDD is optimized for:

- Features with **genuine uncertainty** about the design.
- Branches whose **cost of regression is high**.
- Teams that value **auditability over speed** (every decision is a commit message).

For trivial fixes or exploratory hacks, use the fallback manual mode -- the full gate is intentionally friction-rich for non-trivial work.

---

## Installation

### From GitHub (for users)

```bash
# 1. Add the BolivarTech marketplace as a source
/plugin marketplace add BolivarTech/sbtdd-workflow

# 2. Install the plugin
/plugin install sbtdd-workflow@bolivartech-plugins

# 3. Bootstrap a project that uses SBTDD
cd /path/to/your/project
/sbtdd init
```

To update after new versions are published:

```bash
/plugin marketplace update
```

### Local Development

```bash
# Option 1: Plugin flag (explicit path, one-shot)
claude --plugin-dir /path/to/sbtdd-workflow

# Option 2: Symlink for auto-discovery (no flags needed)
mkdir -p .claude/skills
ln -s ../../skills/sbtdd .claude/skills/sbtdd
claude
```

The `.claude/` directory is gitignored; each developer creates their own symlink locally. Changes are picked up with `/reload-plugins` without restarting.

---

## Usage

Invoke with `/sbtdd <subcommand>` or natural trigger phrases ("advance TDD phase", "run pre-merge review", "sbtdd status").

### The nine subcommands

| Subcommand | Purpose | Typical invocation |
|------------|---------|--------------------|
| `init` | Bootstrap an SBTDD project (rules, hooks, skeleton spec, .gitignore entries) | `/sbtdd init --stack python --author "Your Name"` |
| `spec` | Run the spec pipeline: `/brainstorming` -> `/writing-plans` -> MAGI Checkpoint 2 | `/sbtdd spec` |
| `close-phase` | Close one TDD phase atomically (Red/Green/Refactor): verify + commit + advance state | `/sbtdd close-phase` (or `close-phase --variant fix` for Green-as-fix) |
| `close-task` | Mark `[x]` in the plan + `chore:` commit + advance to the next `[ ]` | `/sbtdd close-task` (auto-invoked by `close-phase refactor`) |
| `status` | Read-only structured report of state + git + plan + drift | `/sbtdd status` |
| `pre-merge` | Run Loop 1 (code review) then Loop 2 (MAGI) sequentially | `/sbtdd pre-merge` |
| `finalize` | Run sec.M.7 checklist + `/finishing-a-development-branch` | `/sbtdd finalize` |
| `auto` | Shoot-and-forget full cycle (task loop + pre-merge + checklist), stops before finalize | `/sbtdd auto` or `/sbtdd auto --dry-run` |
| `resume` | Diagnose interrupted runs and delegate recovery | `/sbtdd resume` or `/sbtdd resume --discard-uncommitted` |

### Typical end-to-end flow

```bash
# 1. Bootstrap (once per project)
/sbtdd init --stack python --author "Your Name"

# 2. Write the spec base, then run the spec pipeline
#    (drafts spec-behavior.md, claude-plan-tdd-org.md, iterates via MAGI)
/sbtdd spec

# 3. Execute the plan
#    Option A: manual (one phase at a time)
/sbtdd close-phase            # after implementing Red
/sbtdd close-phase            # after Green (or: --variant fix)
/sbtdd close-phase            # after Refactor (auto-invokes close-task)
# ... repeat for each task ...

#    Option B: shoot-and-forget
/sbtdd auto

# 4. Pre-merge gates
/sbtdd pre-merge              # Loop 1 (code review) + Loop 2 (MAGI)

# 5. Finalize (runs the checklist + /finishing-a-development-branch)
/sbtdd finalize
```

### Direct CLI (bypassing the skill)

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <subcommand> [args...]
```

See `python skills/sbtdd/scripts/run_sbtdd.py --help` for the full flag reference.

---

## How it works

```
User input
  |
  v
/sbtdd skill (SKILL.md) -- complexity gate + subcommand parsing
  |
  v
run_sbtdd.py (dispatcher) -- validates preconditions + loads state
  |
  v
{subcommand}_cmd.py (one per subcommand)
  |
  +-- init_cmd.py       -- 5-phase bootstrap (pre-flight -> atomic gen -> smoke test)
  +-- spec_cmd.py       -- /brainstorming -> /writing-plans -> MAGI Checkpoint 2
  +-- close_phase_cmd.py-- drift check -> verify -> atomic commit -> state advance
  +-- close_task_cmd.py -- mark [x] + chore: commit + advance to next task
  +-- status_cmd.py     -- read-only report (state + git + plan + drift)
  +-- pre_merge_cmd.py  -- Loop 1 (review) -> Loop 2 (MAGI gate)
  +-- finalize_cmd.py   -- checklist validation + /finishing-a-development-branch
  +-- auto_cmd.py       -- 5-phase autonomous cycle (task loop + pre-merge + sec.M.7)
  +-- resume_cmd.py     -- diagnostic + delegation after interruption
```

### State model

Four orthogonal artifacts, each with exactly one writer:

- **`.claude/plugin.local.md`** (user) -- project rules (stack, verification commands, MAGI thresholds).
- **`.claude/session-state.json`** (plugin) -- canonical present (active task + phase).
- **Git commits + branch** (plugin) -- canonical past (immutable timeline).
- **`planning/claude-plan-tdd.md`** (plugin) -- canonical future + completion registry.

Drift between the three plugin-owned artifacts is detected but NEVER auto-reconciled (INV-17). The agent surfaces the divergence and defers to the user.

### Invariants

30+ invariants are enforced across the plugin surface. The most critical:

- **INV-0:** `~/.claude/CLAUDE.md` has absolute precedence over every other configuration.
- **INV-1:** Phase closes are atomic (commit + state + plan consistent after each operation).
- **INV-5..8:** Commit discipline (English, no Co-Authored-By, no AI refs, atomic, prefixed).
- **INV-9:** Pre-merge Loop 2 requires Loop 1 clean-to-go first (no parallel loops).
- **INV-11:** Every MAGI loop has a hard iteration cap; exceeding escalates with candidate root causes.
- **INV-27:** Spec base cannot contain the three uppercase placeholder markers (enumerated in sec.S.10.4 of the contract).
- **INV-28:** MAGI degraded verdict (fewer than 3 agents) never counts as loop-exit.
- **INV-29:** Every MAGI finding passes through `/receiving-code-review` before a mini-cycle TDD applies it.
- **INV-30:** Every interrupted run is resumable via `/sbtdd resume`.

The full list lives in `sbtdd/sbtdd-workflow-plugin-spec-base.md sec.S.10`.

---

## Architecture

```
.claude-plugin/
  plugin.json                 -- Plugin manifest (name, version, author, repository)
  marketplace.json            -- BolivarTech marketplace catalog entry
skills/sbtdd/
  SKILL.md                    -- Orchestrator (complexity gate + dispatch + embedded rules)
  scripts/
    __init__.py
    run_sbtdd.py              -- Entrypoint: python run_sbtdd.py <subcommand> [args]
    models.py                 -- Immutable registries (prefix map, verdict ranks)
    errors.py                 -- SBTDDError hierarchy + EXIT_CODES mapping
    config.py                 -- plugin.local.md parser (YAML frontmatter)
    state_file.py             -- session-state.json read/write/validate
    commits.py                -- git commit helpers with prefix validation
    hooks_installer.py        -- Idempotent merge of .claude/settings.json
    templates.py              -- Placeholder expansion for destination files
    drift.py                  -- state/git/plan drift detection
    subprocess_utils.py       -- Cross-platform subprocess (Windows kill-tree)
    quota_detector.py         -- Anthropic quota pattern detection (exit 11)
    dependency_check.py       -- 7-item pre-flight validator
    superpowers_dispatch.py   -- Invocation of Superpowers skills
    magi_dispatch.py          -- Invocation of /magi:magi + verdict parsing
    init_cmd.py               -- bootstrap destination project
    spec_cmd.py               -- spec pipeline with MAGI Checkpoint 2
    close_phase_cmd.py        -- three-step atomic phase close
    close_task_cmd.py         -- mark [x] + chore: commit + state advance
    status_cmd.py             -- structured read-only report
    pre_merge_cmd.py          -- Loop 1 + Loop 2 sequential gate
    finalize_cmd.py           -- sec.M.7 checklist + finishing-a-branch
    auto_cmd.py               -- shoot-and-forget full cycle
    resume_cmd.py             -- recovery from interrupted sessions
    reporters/
      __init__.py
      tdd_guard_schema.py     -- test.json schema for TDD-Guard integration
      rust_reporter.py        -- cargo nextest -> tdd-guard-rust pipeline
      ctest_reporter.py       -- ctest JUnit XML -> TDD-Guard JSON
templates/
  CLAUDE.local.md.template    -- Parameterized project rules
  plugin.local.md.template    -- Destination project configuration schema
  settings.json.template      -- Three TDD-Guard hooks for destination project
  spec-behavior-base.md.template -- SBTDD spec skeleton
  conftest.py.template        -- pytest reporter for destination project
  gitignore.fragment          -- Entries to append to destination .gitignore
tests/
  test_*.py                   -- One test module per scripts/ module
  fixtures/
    plans/
    state-files/
    plugin-locals/
    quota-errors/
    junit-xml/
    auto-run/
pyproject.toml                -- Python >= 3.9, dual license, mypy strict, ruff
conftest.py                   -- pytest hook for TDD-Guard test.json
Makefile                      -- verify, test, lint, format, typecheck targets
CHANGELOG.md                  -- Human-curated release notes (Keep a Changelog format)
CONTRIBUTING.md               -- Contributor guide
LICENSE                       -- MIT
LICENSE-APACHE                -- Apache-2.0
```

See the functional contract in `sbtdd/sbtdd-workflow-plugin-spec-base.md` for the authoritative architecture reference (sec.S.2).

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Full verification (tests + lint + format + types)
make verify

# Individual checks
make test        # pytest
make lint        # ruff check
make format      # ruff format --check
make typecheck   # mypy --strict
```

---

## Requirements

| Component | Required | Notes |
|-----------|----------|-------|
| Python 3.9+ | Yes | stdlib-only on hot paths (close-phase, close-task, status) |
| `git` | Yes | All commit operations |
| `tdd-guard` binary | Yes | Real-time TDD phase enforcement in the destination project |
| `superpowers` plugin | Yes | 12 workflow skills (brainstorming, writing-plans, test-driven-development, ...) |
| `magi` plugin | Yes | Pre-merge Loop 2 + spec Checkpoint 2 |
| Per-stack toolchain | Yes (for chosen stack only) | `sbtdd init --stack <stack>` validates toolchain for the chosen stack only -- NOT for other stacks. **Rust:** `cargo`, `cargo-nextest`, `cargo-audit`, `tdd-guard-rust`. **Python:** `pytest`, `ruff`, `mypy`. **C++:** `cmake`, `ctest --output-junit`. |

`sbtdd init` runs a strict pre-flight that aggregates all missing dependencies into a single report before aborting -- no half-configured installs. The per-stack toolchain check is scoped to `--stack` (e.g., installing `sbtdd-workflow` for a Python project does NOT require Rust's `cargo-nextest`).

### Dev dependencies

```bash
pip install pytest pytest-asyncio ruff mypy pyyaml
```

Or via `uv`:

```bash
uv sync
```

---

## Publishing updates

1. Bump `"version"` in both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (must match, sec.S.3.3).
2. Update `CHANGELOG.md` (Keep a Changelog format: BREAKING / Added / Changed / Fixed / Deprecated / Removed).
3. Run `make verify` -- all tests must pass, zero lint warnings, clean formatting, no type errors.
4. Commit and push to `main` on GitHub.
5. Users pick up updates with `/plugin marketplace update`.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the contributor guide: branching model, commit discipline, PR checklist, and the non-negotiable invariants.

In brief: SBTDD applies to its own development (dogfooding). Every contribution goes through `/sbtdd spec` -> plan approval -> task-by-task execution -> `/sbtdd pre-merge` -> `/sbtdd finalize`. No shortcuts.

---

## License

Dual licensed under [MIT](LICENSE) OR [Apache-2.0](LICENSE-APACHE), at your option. This dual-license convention is inherited from MAGI and from the Rust ecosystem.

---

## Credits

The SBTDD methodology and plugin architecture are designed and maintained by Julian Bolivar (BolivarTech). The plugin operationalizes the Superpowers skill ecosystem (Obra Inc.) and integrates with the MAGI multi-perspective plugin (also BolivarTech).

See `CLAUDE.md` for the full methodology reference and `sbtdd/sbtdd-workflow-plugin-spec-base.md` for the authoritative functional contract.
````

- [ ] **Step 3: Run tests to verify green**

Run: `python -m pytest tests/test_readme.py -v`
Expected: 16 tests pass. (Note: `test_readme_references_contributing` will pass because the README references CONTRIBUTING.md even before the file itself exists; Task 8 creates the file.)

- [ ] **Step 4: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add tests/test_readme.py README.md
git commit -m "docs: add professional README with shields, installation, usage, architecture"
```

---

### Task 8: `CONTRIBUTING.md` brief contributor guide

**Files:**
- Create: `CONTRIBUTING.md`
- Modify: `tests/test_readme.py` (add CONTRIBUTING contract test)

Objetivo: brief contributor guide referenciado desde README. Contenido minimo: branching model, commit discipline (pointer to CLAUDE.md sec.M.5), PR checklist, dogfooding note. No duplicar la metodologia completa -- linkear a CLAUDE.md + spec-base.

- [ ] **Step 1: Extend test**

Append to `tests/test_readme.py`:

```python
def test_contributing_file_exists() -> None:
    assert CONTRIBUTING_PATH.is_file(), f"CONTRIBUTING.md missing at {CONTRIBUTING_PATH}"


def test_contributing_has_title() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    assert re.search(r"^#\s+Contributing", text, flags=re.MULTILINE)


def test_contributing_references_commit_prefixes() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    for prefix in ("test:", "feat:", "fix:", "refactor:", "chore:"):
        assert prefix in text, f"CONTRIBUTING must mention commit prefix '{prefix}'"


def test_contributing_references_inv0() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    assert "INV-0" in text or "~/.claude/CLAUDE.md" in text, (
        "CONTRIBUTING must reference the global authority rule"
    )


def test_contributing_no_uppercase_placeholders() -> None:
    """Extends the rationale of INV-27 to CONTRIBUTING.md. INV-27 itself is
    scoped to `sbtdd/spec-behavior-base.md`; this test applies the same
    hygiene guard to the contributor-facing documentation.
    """
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    # Runtime-assembled tokens keep this test file clean under INV-27-like scans
    # (concatenation avoids embedding the literal markers in the source).
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"CONTRIBUTING contains forbidden placeholder '{token}' "
            "(extends INV-27 rationale to CONTRIBUTING.md)"
        )
```

Run: `python -m pytest tests/test_readme.py -v`
Expected: 5 new tests fail.

- [ ] **Step 2: Create `CONTRIBUTING.md`**

```markdown
# Contributing to SBTDD Workflow

Thank you for your interest in contributing. This plugin implements a strict methodology (SBTDD) and applies it to its own development -- dogfooding is the point.

## Prerequisites

- Read `~/.claude/CLAUDE.md` first. Its Code Standards have absolute precedence (INV-0) over everything in this repository.
- Read `CLAUDE.md` (project-level) and `CLAUDE.local.md` (project-level local rules).
- Read `sbtdd/sbtdd-workflow-plugin-spec-base.md` -- the authoritative functional contract.

## Branching model

- `main` is the integration branch. Always green (`make verify` clean).
- Feature branches follow `feature/<short-description>` or `fix/<short-description>`.
- No direct commits to `main`. All changes land via PR after `/sbtdd pre-merge` passes.

## Workflow

Every feature is implemented via the full SBTDD cycle:

1. **Spec (sec.1 of `CLAUDE.local.md`).** Draft `sbtdd/spec-behavior-base.md` for the feature. No uppercase placeholder markers (INV-27 -- enumerated in `CLAUDE.local.md`).
2. **Plan.** Run `/sbtdd spec` to drive `/brainstorming` -> `/writing-plans` -> MAGI Checkpoint 2. Iterate until MAGI returns a full (non-degraded) verdict `>= GO_WITH_CAVEATS`.
3. **Execute.** Run `/sbtdd close-phase` at the end of each TDD phase (Red, Green, Refactor), or `/sbtdd auto` for shoot-and-forget execution of the whole plan.
4. **Pre-merge.** Run `/sbtdd pre-merge` -- Loop 1 (automated review) then Loop 2 (MAGI). Both must converge.
5. **Finalize.** Run `/sbtdd finalize` -- the sec.M.7 checklist gate + `/finishing-a-development-branch`.
6. **Open PR.** Link to the approved plan, include the final MAGI verdict summary.

## Commit discipline (sec.M.5 of `CLAUDE.local.md`)

All commits:

- English prose only.
- No `Co-Authored-By` lines.
- No references to Claude, AI, or assistants.
- Atomic -- one commit, one concern, one prefix.

Allowed prefixes:

| Context | Prefix |
|---------|--------|
| Red phase close (test added) | `test:` |
| Green phase close (new feature) | `feat:` |
| Green phase close (bug fix / hardening) | `fix:` |
| Refactor phase close | `refactor:` |
| Task close (mark `[x]` in plan) | `chore:` |
| Documentation-only change | `docs:` |

Mini-cycle fixes during pre-merge Loop 1 or Loop 2 produce three commits each (`test:` -> `fix:` -> `refactor:`), one per finding.

## PR checklist

Before opening a PR:

- [ ] `make verify` clean on the latest commit.
- [ ] `/sbtdd status` reports `current_phase: "done"`.
- [ ] All plan tasks marked `[x]`.
- [ ] `CHANGELOG.md` updated under `## Unreleased` (BREAKING / Added / Changed / Fixed).
- [ ] `/sbtdd pre-merge` converged to a full (non-degraded) verdict `>= GO_WITH_CAVEATS`.
- [ ] No `Co-Authored-By` in any commit.
- [ ] No references to Claude, AI, or assistants in any commit.

## Adding a new invariant

Invariants are numbered `INV-N` and live in `sbtdd/sbtdd-workflow-plugin-spec-base.md sec.S.10`. Adding one:

1. Append the invariant to sec.S.10 with a unique N.
2. Enforce it in the plugin (test-first).
3. Document it in `CLAUDE.md` invariants summary.
4. Reference it in the affected subcommand docstrings.

## Reporting issues

Open a GitHub issue at <https://github.com/BolivarTech/sbtdd-workflow/issues> with:

- Plugin version (`cat .claude-plugin/plugin.json | jq .version`).
- `/sbtdd status` output.
- Relevant lines from `.claude/auto-run.json` (if reproducing an `auto` failure).

## License

By contributing, you agree that your contribution is dual licensed under [MIT](LICENSE) OR [Apache-2.0](LICENSE-APACHE), at the user's option.
```

- [ ] **Step 3: Run tests to verify green**

Run: `python -m pytest tests/test_readme.py -v`
Expected: 21 tests pass (16 + 5 new).

- [ ] **Step 4: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add CONTRIBUTING.md tests/test_readme.py
git commit -m "docs: add CONTRIBUTING.md contributor guide and contract test"
```

---

## Phase 4: Final acceptance sweep (Tasks 9-10)

### Task 9: Cross-artifact coherence test

**Files:**
- Create: `tests/test_distribution_coherence.py`

Objetivo: un test holistico que valida relaciones cruzadas entre los cuatro artefactos (SKILL.md / plugin.json / marketplace.json / README.md). Detecta drift silencioso (ej. SKILL.md lista 9 subcomandos pero README solo 8).

- [ ] **Step 1: Write failing test**

```python
# tests/test_distribution_coherence.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Cross-artifact coherence tests for Milestone E distribution.

Validates invariants that span multiple files: version sync across manifests,
subcommand parity across SKILL.md + README, license consistency.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILL_MD = REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
README_MD = REPO_ROOT / "README.md"
CHANGELOG_MD = REPO_ROOT / "CHANGELOG.md"

NINE_SUBCOMMANDS = frozenset(
    ("init", "spec", "close-phase", "close-task", "status", "pre-merge", "finalize", "auto", "resume")
)


def test_plugin_and_marketplace_versions_match() -> None:
    plugin_v = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    mkt = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    assert plugin_v == mkt["version"]
    entry = next(p for p in mkt["plugins"] if p["name"] == "sbtdd-workflow")
    assert plugin_v == entry["version"]


def test_plugin_and_marketplace_license_match() -> None:
    plugin_license = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["license"]
    assert plugin_license == "MIT OR Apache-2.0"
    readme = README_MD.read_text(encoding="utf-8")
    assert "MIT" in readme and "Apache-2.0" in readme


def test_skill_and_readme_subcommands_match() -> None:
    skill = SKILL_MD.read_text(encoding="utf-8")
    readme = README_MD.read_text(encoding="utf-8")
    for sub in NINE_SUBCOMMANDS:
        assert re.search(rf"\b{re.escape(sub)}\b", skill), f"SKILL.md missing subcommand '{sub}'"
        assert re.search(rf"\b{re.escape(sub)}\b", readme), f"README missing subcommand '{sub}'"


def test_all_artifacts_mention_bolivartech_org() -> None:
    for path in (PLUGIN_JSON, MARKETPLACE_JSON, README_MD):
        text = path.read_text(encoding="utf-8")
        assert "BolivarTech" in text, f"{path.name} missing BolivarTech reference"


def test_changelog_still_present_and_references_v0_1() -> None:
    """Milestone D created CHANGELOG.md; Milestone E must not remove it."""
    assert CHANGELOG_MD.is_file()
    changelog = CHANGELOG_MD.read_text(encoding="utf-8")
    assert "Unreleased" in changelog or "0.1" in changelog


def _resolve_magi_plugin_json() -> Path:
    """Resolve the path to MAGI's plugin.json, honoring MAGI_PLUGIN_ROOT override."""
    import os

    magi_root_env = os.environ.get("MAGI_PLUGIN_ROOT")
    if magi_root_env:
        return Path(magi_root_env) / ".claude-plugin" / "plugin.json"
    # Default cache location used by Claude Code on Windows/POSIX.
    return (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "bolivartech-plugins"
        / "magi"
        / "2.1.3"
        / ".claude-plugin"
        / "plugin.json"
    )


MAGI_PLUGIN_JSON = _resolve_magi_plugin_json()


@pytest.mark.skipif(
    not MAGI_PLUGIN_JSON.is_file(),
    reason=(
        f"MAGI plugin.json not found at {MAGI_PLUGIN_JSON}; set MAGI_PLUGIN_ROOT to override. "
        "Parity check is a local-dev convenience, not a CI enforcement — "
        "addresses F3 MAGI iter 2."
    ),
)
def test_plugin_json_has_required_keys_matching_magi() -> None:
    """Parity with MAGI's plugin.json — required-keys subset check (F4 MAGI iter 2).

    This is a **local-dev parity check**, NOT a Claude Code spec validation.
    Anthropic does not formally publish a plugin manifest schema as of
    v0.1.0 ship date; the authoritative reference is MAGI v2.1.3's
    `plugin.json`, which is the template the SBTDD plugin follows
    field-for-field.

    **F4 MAGI iter 2 fix:** previous draft asserted `set(sbtdd.keys()) ==
    set(magi.keys())` (exact equality). That check breaks the moment MAGI
    adds an optional field (e.g., `dependencies`, `homepage`, `engines`) —
    both plugins would be healthy but the test would false-positive.
    Replaced with a **subset check on the six fields we care about**
    (`name`, `version`, `author`, `repository`, `license`, `skills`).
    Optional fields MAGI may add are now silently tolerated.

    **F3 MAGI iter 2 fix:** the skip condition is now a `@pytest.mark.skipif`
    decorator (not an inline `pytest.skip` call). This surfaces the skip
    reason in pytest's short summary (`-rs` flag) and documents the test as
    local-dev-only rather than CI-enforcement.
    """
    sbtdd = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    magi = json.loads(MAGI_PLUGIN_JSON.read_text(encoding="utf-8"))

    required_keys = {"name", "version", "author", "repository", "license", "skills"}
    sbtdd_keys = frozenset(sbtdd.keys())
    magi_keys = frozenset(magi.keys())

    # Both manifests MUST declare the six required keys. Optional extras on
    # either side are tolerated.
    assert required_keys.issubset(sbtdd_keys), (
        f"sbtdd plugin.json missing required keys: {required_keys - sbtdd_keys}"
    )
    assert required_keys.issubset(magi_keys), (
        f"magi plugin.json missing required keys (MAGI-side drift): {required_keys - magi_keys}"
    )


@pytest.mark.skipif(
    not MAGI_PLUGIN_JSON.is_file(),
    reason=(
        f"MAGI plugin.json not found at {MAGI_PLUGIN_JSON}; set MAGI_PLUGIN_ROOT to override. "
        "Parity check is a local-dev convenience, not a CI enforcement."
    ),
)
def test_plugin_json_repository_field_form_matches_magi() -> None:
    """F5 MAGI iter 2: verify `repository` field form parity at runtime.

    The plan declares that the SBTDD plugin uses the **string form** for
    `repository` because MAGI v2.1.3 uses the string form. This test ties
    that claim to runtime evidence: the two manifests must use the same
    Python type for the field (both `str`, or both `dict`). If MAGI ever
    switches to the object form `{"url": "...", "type": "git"}`, this
    test fails and we schedule a migration commit rather than silently
    drifting apart.

    Skipped when MAGI cache is unavailable (same condition as above).
    """
    sbtdd = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    magi = json.loads(MAGI_PLUGIN_JSON.read_text(encoding="utf-8"))
    assert isinstance(sbtdd["repository"], type(magi["repository"])), (
        f"repository field form drift: "
        f"sbtdd is {type(sbtdd['repository']).__name__}, "
        f"magi is {type(magi['repository']).__name__} — "
        "migration commit required to re-align"
    )


def test_no_uppercase_placeholders_in_skill_md() -> None:
    """Extends the rationale of INV-27 to the user-facing orchestrator skill.

    **Scope note (F5 + F11 from MAGI iter 1):** INV-27 formally applies only to
    `sbtdd/spec-behavior-base.md` (it guards the input to `/sbtdd spec`). This
    test does NOT enforce INV-27; it extends the same *rationale* (placeholder
    markers signal unfinished work) to the SKILL.md artifact, which is the
    first user-visible surface of the plugin.

    Intentionally scoped to `SKILL.md` only -- NOT to `README.md` or
    `CHANGELOG.md`, which legitimately discuss INV-27 and its history and
    would therefore false-positive on a blanket grep. Per-artifact guards for
    README and CONTRIBUTING already live in `test_readme.py` (those tests
    exclude their own rationale prose by virtue of the concatenation pattern).
    """
    # Runtime assembly keeps this file itself clean: the literal markers never
    # appear in source. The inline concatenation ("TO" + "DO", etc.) guarantees
    # the guard does not trip on its own implementation.
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    text = SKILL_MD.read_text(encoding="utf-8")
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"SKILL.md contains forbidden placeholder '{token}' "
            "(extends INV-27 rationale to SKILL.md)"
        )
```

Run: `python -m pytest tests/test_distribution_coherence.py -v -rs`
Expected: 8 tests pass (local dev with MAGI cache present) or 6 passed + 2 skipped (CI without MAGI cache). The two MAGI-parity tests (`test_plugin_json_has_required_keys_matching_magi` and `test_plugin_json_repository_field_form_matches_magi`) are decorated with `@pytest.mark.skipif` so skips are surfaced in pytest's short summary (`-rs` flag) rather than silently passing — addresses F3 MAGI iter 2.

- [ ] **Step 2: Run full verify**

```bash
python -m pytest tests/ -q
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add tests/test_distribution_coherence.py
git commit -m "test: add cross-artifact coherence test for Milestone E distribution"
```

**Note (F12 from MAGI iter 1):** adding a new test file is `test:` per sec.M.5 row 1, not `chore:`. The coherence test IS a test — the earlier `chore:` prefix was inconsistent with the commit-prefix table above.

---

### Task 10: Milestone E acceptance sweep

**Files:**
- Modify: `CHANGELOG.md` (append Milestone E entries under `## Unreleased`)

Objetivo: verificar parity con MAGI (sec.S.12.2) + distribucion (sec.S.12.5), registrar el cierre en CHANGELOG, y confirmar que todos los artefactos estan en su sitio.

- [ ] **Step 1: Full verification sweep**

```bash
python -m pytest tests/ -v --tb=short
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green. Report total test count: **596 when every conditional runs** (local dev with MAGI cache); **594 when MAGI cache absent** (two `@pytest.mark.skipif` parity tests skip but are surfaced via `-rs` in pytest summary). Skip-aware per F2 MAGI iter 2.

- [ ] **Step 2: Parity audit (sec.S.12.2)**

Manually verify each item:

| sec.S.12.2 item | Milestone E check |
|-----------------|-------------------|
| Plugin manifest (`plugin.json`) exists with correct schema | Task 5 (`tests/test_plugin_manifest.py`) |
| Marketplace manifest (`marketplace.json`) with version sync | Task 6 (`tests/test_marketplace_manifest.py`) |
| Orchestrator SKILL.md with 7 sections per sec.S.6.3 | Tasks 1-4 (`tests/test_skill_md.py`) |
| README with shields, installation, usage, architecture | Task 7 (`tests/test_readme.py`) |
| Dual LICENSE files (MIT + Apache-2.0) | Existed from Milestone A |
| CHANGELOG.md | Existed from Milestone D (Task 10 extends it) |
| CONTRIBUTING.md | Task 8 |

Run:

```bash
ls -la LICENSE LICENSE-APACHE CHANGELOG.md CONTRIBUTING.md README.md
ls -la .claude-plugin/plugin.json .claude-plugin/marketplace.json
ls -la skills/sbtdd/SKILL.md
```

Expected: all seven files present and non-empty.

- [ ] **Step 3: Distribution audit (sec.S.12.5)**

Manually verify:

| sec.S.12.5 item | Milestone E check |
|-----------------|-------------------|
| Public GitHub repo at `BolivarTech/sbtdd-workflow` | Deferred: user-driven after final commit |
| Installable via `/plugin marketplace add BolivarTech/sbtdd-workflow` | Enabled by `marketplace.json` (Task 6) |
| Installable via `/plugin install sbtdd-workflow@bolivartech-plugins` | Enabled by `plugin.json` + `marketplace.json` (Tasks 5, 6) |
| Version sync plugin.json <-> marketplace.json | Pinned by `test_distribution_coherence.py::test_plugin_and_marketplace_versions_match` (Task 9) |
| Symlink documented for local dev | Documented in README Installation section (Task 7) |

- [ ] **Step 4: Update CHANGELOG.md**

**Note (informational):** `CHANGELOG.md` was created during Milestone D with a `## Unreleased` section. Milestone E **appends** to that existing section — it does NOT create a new file.

Append under the existing `## Unreleased` heading in `CHANGELOG.md`:

```markdown
### Added (Milestone E -- distribution artifacts v0.1 ship)

- `skills/sbtdd/SKILL.md` orchestrator skill following the seven-section
  structure mandated by sec.S.6.3 (Overview -> Subcommand dispatch ->
  Complexity gate -> Execution pipeline -> sbtdd-rules -> sbtdd-tdd-cycle
  -> Fallback).
- `.claude-plugin/plugin.json` at version `0.1.0` (name `sbtdd-workflow`,
  dual license MIT OR Apache-2.0, `repository` field as a plain URL string
  matching MAGI v2.1.3's form, pointing to
  `github.com/BolivarTech/sbtdd-workflow`).
- `.claude-plugin/marketplace.json` BolivarTech catalog entry at version
  `0.1.0` synchronized with `plugin.json` (sec.S.3.3).
- Public `README.md` with four static shields (Python 3.9+, license, ruff,
  mypy), "Why SBTDD? Why multi-agent?" section, Installation (marketplace
  + local dev), Usage (nine-subcommand table + end-to-end flow),
  Architecture, and License sections (parity with MAGI `README.md`).
- `CONTRIBUTING.md` contributor guide with commit-prefix reference,
  pre-merge expectations, and invariant addition procedure.
- Five new contract test files covering the distribution artifacts:
  `tests/test_skill_md.py` (**19 tests**: see Task-by-task breakdown in the
  Acceptance section), `tests/test_plugin_manifest.py` (**11 tests**,
  includes 1 that skips when marketplace.json absent then asserts when
  present), `tests/test_marketplace_manifest.py` (**9 tests**),
  `tests/test_readme.py` (**21 tests**, 16 for README + 5 for
  CONTRIBUTING.md), and `tests/test_distribution_coherence.py`
  (**8 tests**: 6 cross-artifact + 2 MAGI-parity smoke — required-keys
  subset check + `repository` field-form check, both decorated with
  `@pytest.mark.skipif` when MAGI cache absent).
  **Total new: 68 tests** (528 baseline). Reachable totals, stated
  explicitly per Caspar iter 3 (the earlier "594-595" range was
  imprecise): **593** (mid-milestone window during Milestone E execution,
  between Tasks 5 and 6 when the version-sync coherence test is
  additionally skipped — this window does not exist at ship time),
  **594** (CI environment without MAGI cache installed — the 3 skipif-
  guarded MAGI parity tests skip), **596** (local development with MAGI
  cache present — every conditional test runs). Range reflects the 3
  skipif-guarded MAGI parity tests. Skip-aware phrasing mandated by F2
  MAGI iter 2 to make the accounting exact.

### Changed

- `README.md`: rewrote from the previous single-line stub into the full
  user-facing GitHub README.

### Deferred (tracked for v0.2.0)

- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running `make verify`
  on push and PR, with a live "tests passing" shield (Milestone E intentionally
  ships without a `tests-passing` badge rather than publish a fake one — F2 of
  MAGI Checkpoint 2 Plan E iter 1).
- `schema_version` field in `plugin.local.md` (sec.S.13 item 5).
- GoogleTest / Catch2 / bazel / meson adapters for C++ stack (sec.S.13 item 7).
- Verify `marketplace.json` `$schema` URL
  (`https://anthropic.com/claude-code/marketplace.schema.json`) resolves
  post-push. Fallback: drop the field across both plugins in lockstep if
  Anthropic removes it or Claude Code emits a warning (F6 MAGI iter 2).
- MAGI-version coupling in parity tests — track for v0.2 if MAGI v2.2+
  changes schema (Caspar iter 3 final recommendation). The two parity
  tests in `test_distribution_coherence.py` (required-keys subset check
  + `repository` field-form check) pin against MAGI v2.1.3 artifacts
  cached locally; if MAGI evolves its manifest schema, these tests must
  be refreshed against the new cache snapshot to remain meaningful.

(Milestones A-D changelog entries preserved; Milestone E is the last
milestone before the `v0.1.0` public ship tag.)
```

- [ ] **Step 5: Final verification**

```bash
python -m pytest tests/ -v
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all green. Capture the total test count.

- [ ] **Step 6: Commit**

```bash
git add CHANGELOG.md
git commit -m "chore: milestone E acceptance sweep and CHANGELOG update"
```

- [ ] **Step 7: Version tag preparation (user-driven)**

This step is NOT a commit -- it is a pointer for the human maintainer.

After Milestone E is merged to `main`:

```bash
# Verify version is 0.1.0 everywhere
cat .claude-plugin/plugin.json | python -c "import json,sys; print(json.load(sys.stdin)['version'])"
cat .claude-plugin/marketplace.json | python -c "import json,sys; print(json.load(sys.stdin)['version'])"

# Create the release tag
git tag -a v0.1.0 -m "Release v0.1.0: initial public ship"
git push origin main
git push origin v0.1.0
```

The tag push triggers the marketplace update cycle (`/plugin marketplace update` picks up `v0.1.0`).

---

## Milestone E -- Acceptance

Tras completar las **12 tareas** (Task 0 + Task 1 + Task 1b + Tasks 2-10):

- **1 nuevo SKILL.md** (`skills/sbtdd/SKILL.md`) con las 7 secciones de sec.S.6.3 en orden correcto. No line-count floor — the Task 4 `test_skill_has_nontrivial_body` pins that **each section has a non-empty body** (content-based check, F7 MAGI iter 2), which is strictly stronger than an arbitrary line floor.
- **2 nuevos manifests** (`.claude-plugin/plugin.json` + `marketplace.json`) con version `0.1.0` sincronizada. `plugin.json.repository` usa forma string matching MAGI v2.1.3.
- **1 README profesional** reescrito desde stub, con **4 static shields** (Python 3.9+, license, ruff, mypy) — sin fake "tests passing" badge.
- **1 CONTRIBUTING.md** con commit discipline + PR checklist.
- **5 test files nuevos** bajo `tests/`:
  - `test_skill_md.py` (**19 tests**: Task 1 aporta 5 [meaningful-content, yaml-frontmatter, name-sbtdd, description-block, main-title]; Task 2 aporta 5 [overview, subcommand-dispatch, all-nine-subcommands, complexity-gate, no-skeleton-sentinel (F8 MAGI iter 2, moved from Task 4 per Caspar iter 3 so the guard arms at the same moment the sentinel is removed)]; Task 3 aporta 6 [execution-pipeline, python-invocation-pattern, sbtdd-rules, sbtdd-tdd-cycle, commit-prefix-map, invariants]; Task 4 aporta 3 [fallback, section-order, non-trivial-body (content-based per F7 MAGI iter 2)]; total 5+5+6+3 = 19)
  - `test_plugin_manifest.py` (**11 tests**: 10 structural + 1 version-sync-or-skip; version-sync skipped until Task 6 creates marketplace.json)
  - `test_marketplace_manifest.py` (**9 tests**)
  - `test_readme.py` (**21 tests**: 16 for README + 5 for CONTRIBUTING)
  - `test_distribution_coherence.py` (**8 tests**: 6 cross-artifact + 2 MAGI-parity decorated with `@pytest.mark.skipif` per F3 MAGI iter 2 — required-keys subset per F4, repository field-form per F5)
  - **Total: 68 new tests**. Skip-aware accounting (per F2 MAGI iter 2):
    - **596 total** when every conditional test runs (local dev, MAGI cache present, Tasks 5+6 both complete).
    - **594 total** at ship time in CI without MAGI cache (both coherence parity tests skip; baseline 528 + 68 − 2 skipped = 594).
    - **593 total** during the mid-milestone window between Tasks 5 and 6 (version-sync test skipped) — this window does not exist at ship time.
- **1 update a `CHANGELOG.md`** bajo la seccion `## Unreleased` pre-existente (created in Milestone D) con 6 entries Added + 1 Changed + 4 Deferred (Caspar iter 3 added the MAGI-version coupling entry).
- `make verify` limpio: pytest + ruff check + ruff format --check + mypy (strict). Skips are reported, not hidden.
- Ningun cambio a modulos preexistentes bajo `skills/sbtdd/scripts/` (frozen-module policy preservada).
- **12 commits atomicos** con prefijos sec.M.5 + `docs:` (strict Red-Green split, no combined test+impl commits):
  - Task 0: sin commits (read-only inventory).
  - Task 1: 1 commit `test:` (contract test, Red — fails because SKILL.md absent).
  - Task 1b: 1 commit `feat:` (minimal SKILL.md skeleton, Green — 5 tests pass).
  - Task 2: 1 commit `feat:` (sections 1-3 + test extension).
  - Task 3: 1 commit `feat:` (sections 4-6 + test extension).
  - Task 4: 1 commit `feat:` (Fallback section + test extension).
  - Task 5: 2 commits — `test:` (Red) + `chore:` (Green plugin.json).
  - Task 6: 2 commits — `test:` (Red) + `chore:` (Green marketplace.json).
  - Task 7: 2 commits — `test:` (Red) + `docs:` (Green README).
  - Task 8: 2 commits — `test:` (Red) + `docs:` (Green CONTRIBUTING).
  - Task 9: 1 commit `test:` (cross-artifact coherence test — fixed F12: was `chore:`).
  - Task 10: 1 commit `chore:` (acceptance sweep + CHANGELOG update).
  - **Total: 15 commits across 12 tasks** (9 tasks contribute commits; 2 tasks [0 and version-tag prep] are no-op; task 1 splits into 1+1b).

Productos habilitados por Milestone E:

- Instalacion publica via `/plugin marketplace add BolivarTech/sbtdd-workflow`.
- Instalacion publica via `/plugin install sbtdd-workflow@bolivartech-plugins`.
- `/sbtdd` como entry point dispatcher funcional (SKILL.md user-visible).
- Shields y badges en GitHub surface.
- Version tag `v0.1.0` listo para push.

No implementados en Milestone E (fuera de scope por diseno):

- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running `make verify` on push/PR and exposing a live "tests passing" shield. Deferred to v0.2.0 (CHANGELOG Unreleased tracks this). Milestone E ships four static shields only — no fake badge is published.
- Integration tests end-to-end que lancen un proyecto destino real y corran `/sbtdd init`.
- Documentacion en espanol (solo ingles).
- `schema_version` en `plugin.local.md` (deferred a v0.2 per sec.S.13 item 5).

---

## Self-Review (pre-MAGI Checkpoint 2)

**1. Scope coverage (items in scope per Milestone E brief):**

- SKILL.md with 7 sections (sec.S.6.3) -> Tasks 1-4.
- plugin.json manifest -> Task 5.
- marketplace.json catalog -> Task 6.
- README.md professional -> Task 7.
- CONTRIBUTING.md -> Task 8.
- Contract tests for all four user-facing artifacts -> Tasks 1+1b, 5, 6, 7, 8, 9.
- Final acceptance sweep + CHANGELOG update -> Task 10.

**2. Parity with MAGI audit (sec.S.12.2):**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Plugin manifest shape | Met | Task 5 mirrors MAGI `plugin.json` field-by-field |
| Marketplace manifest shape | Met | Task 6 mirrors MAGI `marketplace.json` field-by-field |
| README structure (shields, why, installation, usage, arch, license) | Met | Task 7; `test_readme.py` pins each section |
| SKILL.md seven-section structure | Met | Tasks 1, 1b, 2-4; `test_skill_md.py::test_skill_sections_in_correct_order` pins ordering |
| Dual LICENSE | Pre-existing (Milestone A) | Pins preserved by `test_readme_has_license_shield` |
| CHANGELOG | Pre-existing (Milestone D), extended in Task 10 | `test_distribution_coherence.py::test_changelog_still_present_and_references_v0_1` |

**3. Distribution audit (sec.S.12.5):**

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Public GitHub repo URL referenced | Met | `plugin.json.repository`, `marketplace.json.plugins[0].homepage`, `README.md` |
| Marketplace install flow documented | Met | `README.md` Installation section |
| Version sync plugin.json <-> marketplace.json | Met + pinned | Task 5 + Task 6 + `test_distribution_coherence.py` |
| Symlink for local dev documented | Met | `README.md` Installation section (Option 2) |

**4. Invariant enforcement audit:**

| INV | Covered by Milestone E | Status |
|-----|------------------------|--------|
| INV-0 | SKILL.md cites `~/.claude/CLAUDE.md` absolute precedence | Documented |
| INV-5..8 | CONTRIBUTING.md commit discipline section | Documented |
| INV-27 rationale (not INV-27 itself -- INV-27 is scoped to `spec-behavior-base.md`) | `test_readme_no_uppercase_placeholders`, `test_contributing_no_uppercase_placeholders`, `test_no_uppercase_placeholders_in_skill_md` | Pinned (rationale-extended) |
| INV-28 | SKILL.md sbtdd-rules section + pre-merge invocation pattern | Documented |
| INV-29 | SKILL.md sbtdd-rules section + MAGI invocation pattern | Documented |
| INV-30 | SKILL.md Subcommand dispatch (resume row) + README Usage table | Documented |

**5. Commit prefix audit:** see table in "Milestone E -- Acceptance"; every task follows sec.M.5. The `docs:` prefix is used for pure documentation artefacts (README, CONTRIBUTING), consistent with `~/.claude/CLAUDE.md` §Git commit types.

**6. Placeholder scan:** grep `\bT0D0\b|\bT0D0S\b|\bTBD\b` (zero-substituted here to keep this file itself clean under INV-27-rationale scans) on this plan -> 0 matches outside runtime-assembled string literals (`"TO" + "DO"`, etc., in the test bodies quoted above -- those are explicitly OK because the concatenation never produces the literal token in source). `test_no_uppercase_placeholders_in_skill_md` extends the guard to SKILL.md; `test_readme_no_uppercase_placeholders` extends it to README.md; `test_contributing_no_uppercase_placeholders` extends it to CONTRIBUTING.md. The guard is scoped (not a blanket grep across the repo) so legitimate rationale prose in CHANGELOG / plan files does not false-positive -- addresses F11 from MAGI iter 1.

**7. Frozen-module impact audit:** Milestone E creates only new files; no files under `skills/sbtdd/scripts/` are modified. The frozen-module policy is honored. The only new files under `tests/` are contract tests for the new artifacts; no existing test is modified.

**8. Type consistency:** contract tests are `def test_*() -> None` with no shared state and no monkeypatch (they are read-only assertions over real repo files). Type annotations follow the post-Milestone-A convention (`from __future__ import annotations`, `Path` for filesystem access, `dict` for JSON payloads).

**9. Back-compat guarantee:** Milestone E introduces new user-visible surfaces (SKILL.md, manifests, README, CONTRIBUTING) but modifies no existing API. No existing call-site is affected. The only behavioral implication is for Claude Code itself: once `plugin.json` + `marketplace.json` land, the plugin becomes discoverable in the BolivarTech marketplace; users are expected to run `/plugin marketplace update` to pick up `v0.1.0`.

---

## Execution Handoff

Plan listo para MAGI Checkpoint 2. Al aprobarse con veredicto >= `GO_WITH_CAVEATS` full non-degraded, se guarda como `planning/claude-plan-tdd-E.md` (incorporando las *Conditions for Approval* que MAGI reporte) y se inicia ejecucion via `/subagent-driven-development` (recomendado) o `/executing-plans`.

Post-ejecucion: Milestone E es el ultimo antes del ship tag `v0.1.0`. El user-driven step al final de Task 10 Step 7 (tag + push) queda fuera del scope de ejecucion autonoma del plan -- requiere decision humana final.
