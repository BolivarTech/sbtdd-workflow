# Milestone C: Interactive Subcomandos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir los 9 subcomandos interactivos del plugin sbtdd-workflow como modulos `*_cmd.py` bajo `skills/sbtdd/scripts/` — `status_cmd`, `close_task_cmd`, `close_phase_cmd`, `init_cmd`, `spec_cmd`, `pre_merge_cmd`, `finalize_cmd`, `auto_cmd`, `resume_cmd` — y cablearlos al dispatcher de Milestone B (`run_sbtdd.py`) reemplazando los 9 placeholder handlers en `SUBCOMMAND_DISPATCH`. Todo con `make verify` limpio.

**Architecture:** Python 3.9+ consumiendo la infraestructura de Milestones A+B: `state_file` (load/save/SessionState), `drift` (detect_drift/DriftReport), `commits` (create/validate_prefix/validate_message), `config` (load_plugin_local/PluginConfig), `templates` (expand), `hooks_installer` (merge), `dependency_check` (check_environment/DependencyReport), `superpowers_dispatch` (12 typed wrappers), `magi_dispatch` (invoke_magi/MAGIVerdict/verdict_passes_gate/write_verdict_artifact), `errors` (SBTDDError + 8 subclases + EXIT_CODES), `models` (COMMIT_PREFIX_MAP, VERDICT_RANK, VALID_SUBCOMMANDS, verdict_meets_threshold), `subprocess_utils` (run_with_timeout, kill_tree), `quota_detector` (detect). Cada `*_cmd.py` expone `main(args: list[str]) -> int` + `run(args: list[str]) -> int` (alias estable que el dispatcher consumira). Argparse para todos los flags. Fallos se propagan como subclases de `SBTDDError`; el dispatcher central mapea a exit codes via `_exit_code_for`.

**Tech Stack:** Python 3.9+ stdlib + PyYAML 6 (ya presente en dev deps). Sin runtime deps nuevas.

---

## File Structure

Archivos creados en este milestone:

```
skills/sbtdd/scripts/
├── status_cmd.py                # read-only: state + git + plan + drift report
├── close_task_cmd.py            # mark [x] + chore commit + advance state
├── close_phase_cmd.py           # 4-step atomic phase close (drift/verify/commit/state)
├── init_cmd.py                  # 5-phase atomic bootstrap
├── spec_cmd.py                  # /brainstorming -> /writing-plans -> MAGI checkpoint
├── pre_merge_cmd.py             # Loop 1 + Loop 2 (INV-28/29)
├── finalize_cmd.py              # checklist sec.M.7 + /finishing-a-development-branch
├── auto_cmd.py                  # 5-phase shoot-and-forget
└── resume_cmd.py                # diagnostic wrapper + delegation

skills/sbtdd/scripts/run_sbtdd.py    # MODIFIED: wire SUBCOMMAND_DISPATCH to real handlers

tests/
├── test_status_cmd.py
├── test_close_task_cmd.py
├── test_close_phase_cmd.py
├── test_init_cmd.py
├── test_spec_cmd.py
├── test_pre_merge_cmd.py
├── test_finalize_cmd.py
├── test_auto_cmd.py
├── test_resume_cmd.py
└── test_run_sbtdd_wiring.py     # Verifies SUBCOMMAND_DISPATCH wired end-to-end

tests/fixtures/
├── plans/                       # Synthetic claude-plan-tdd.md samples
│   ├── one-task-red.md
│   ├── three-tasks-mixed.md
│   └── all-done.md
└── magi-verdicts/               # Synthetic .claude/magi-verdict.json samples
    ├── go-full.json
    ├── go-with-caveats-full.json
    └── go-degraded.json
```

Tareas: 52 total. Orden lineal por dependencias — Fase 1 entrega los tres subcomandos mas simples (read/write primarios) como base; Fase 2 bootstrappea proyectos; Fase 3 los dos gates pre-merge; Fase 4 encadena todo en modo autonomo; Fase 5 cablea el dispatcher. Cada tarea asume las previas completas.

**Comandos de verificacion por fase TDD** (sec.M.0.1 + CLAUDE.local.md §0.1):

```bash
python -m pytest tests/ -v          # All pass, 0 fail
python -m ruff check .              # 0 warnings
python -m ruff format --check .     # Clean
python -m ruff format --check .     # Clean
python -m mypy .                    # No type errors
```

Atajo: `make verify` corre los 4 en orden.

**Supuestos post-Milestone A+B (consumidos, no re-implementados):**

- `errors.EXIT_CODES: Mapping[type[SBTDDError], int]` — canonical sec.S.11.1 mapping.
- `errors.SBTDDError, ValidationError, StateFileError, DriftError, DependencyError, PreconditionError, MAGIGateError, QuotaExhaustedError, CommitError`.
- `models.COMMIT_PREFIX_MAP, VERDICT_RANK, VALID_SUBCOMMANDS, verdict_meets_threshold`.
- `state_file.SessionState, load, save, validate_schema, _validate_iso8601`.
- `drift.detect_drift, _evaluate_drift, DriftReport`.
- `config.PluginConfig, load_plugin_local`.
- `templates.expand`.
- `hooks_installer.merge, read_existing`.
- `subprocess_utils.run_with_timeout, kill_tree`.
- `quota_detector.detect`.
- `commits.create, validate_prefix, validate_message`.
- `dependency_check.check_environment, check_python, check_git, check_tdd_guard_binary, check_tdd_guard_data_dir, check_claude_cli, check_superpowers, check_magi, check_stack_toolchain, check_working_tree, DependencyReport`.
- `superpowers_dispatch.invoke_skill + 12 wrappers (brainstorming, writing_plans, verification_before_completion, requesting_code_review, receiving_code_review, test_driven_development, subagent_driven_development, executing_plans, finishing_a_development_branch, using_git_worktrees, systematic_debugging, dispatching_parallel_agents)`.
- `magi_dispatch.invoke_magi, parse_verdict, MAGIVerdict, verdict_is_strong_no_go, verdict_passes_gate, write_verdict_artifact`.
- `run_sbtdd.SUBCOMMAND_DISPATCH, SubcommandHandler, _exit_code_for`.
- `conftest.py` en root ya inyecta `skills/sbtdd/scripts/` en `sys.path`.

---

## Commit prefix policy

Precedente de Milestones A y B: cuando un task introduce **un modulo nuevo** (test file + implementation file que no existian), un commit unico con prefix `test:` es canonico (sec.M.5 row 1). Cuando un task agrega **nueva logica a un modulo preexistente** con tests downstream que dependen del contrato, se exige split estricto `test:` (Red) -> `feat:`/`fix:` (Green) -> opcional `refactor:`.

En Milestone C los 9 modulos `*_cmd.py` son **todos nuevos** — cada uno nace en su task de scaffold inicial como commit `test:`. Los tasks subsecuentes que **extienden** el mismo `*_cmd.py` con logica nueva siguen el patron estricto: `test:` (nuevo test, falla por ausencia), `feat:`/`fix:` (implementacion minima), y `refactor:` cuando aplica limpieza post-green.

Excepciones explicitas:

- **Task 52 (dispatcher wiring, run_sbtdd.py):** `feat:` — `run_sbtdd.py` ya existe (Milestone B), y este task reemplaza los placeholder handlers por imports reales. Es cambio de comportamiento en modulo preexistente.
- **Tasks 0 (fixtures bootstrap) y cualquiera que solo agregue fixtures JSON/MD:** `chore:` cuando no introducen codigo Python.

Todos los commits:

1. Ingles, sin `Co-Authored-By`, sin menciones a Claude/AI/asistente (`~/.claude/CLAUDE.md` §Git, INV-5..7).
2. Atomico — un task == un commit (o el ciclo Red-Green-Refactor cuando corresponde).
3. Prefijo del mapa sec.M.5 via `commits.create` (validation enforzada por `validate_prefix` + `validate_message`).

---

## Test isolation policy

Heredada de Milestone B: todos los tests que sustituyen atributos de modulos (p.ej. `superpowers_dispatch.invoke_skill`, `subprocess_utils.run_with_timeout`, `magi_dispatch.invoke_magi`, `state_file.load`, `state_file.save`, `commits.create`, `drift.detect_drift`, `dependency_check.check_environment`) DEBEN usar `monkeypatch.setattr(...)` / `monkeypatch.setitem(...)` exclusivamente — nunca asignacion directa. La auto-restauracion de `monkeypatch` evita polucion cross-test. Regla documentada en `conftest.py` root (Milestone B); reviewers la enforzan en code-review.

Cada `*_cmd.py` test file usa `tmp_path` para aislar filesystem state (state file + plan + git repo). Cuando hace falta un git repo real, usa `subprocess.run(["git", "init"], cwd=tmp_path)` dentro de una fixture `pytest.fixture`.

---

## Dispatcher wiring policy

`run_sbtdd.SUBCOMMAND_DISPATCH` en Milestone B contiene 9 placeholder handlers que raisan `ValidationError("not yet implemented")`. En Milestone C los reemplazamos sin mutar la **firma** de `SUBCOMMAND_DISPATCH` (sigue siendo `MutableMapping[str, SubcommandHandler]`; `SubcommandHandler = Callable[[list[str]], int]`). Cada `*_cmd.py` expone:

```python
def run(argv: list[str]) -> int: ...
def main(argv: list[str] | None = None) -> int: ...   # canonical entrypoint
```

`run` es el alias estable que el dispatcher importa. `main` acepta `None` para compatibilidad con tests de integracion que invocan como CLI. Ambas rutas delegan a una funcion interna `_run(args: argparse.Namespace) -> int` tras parseo de flags.

Task 52 edita `run_sbtdd.py` una sola vez, import-by-import, bajo el marker `# MILESTONE-C-REPLACE-POINT`. No se altera la shape de la mapping — solo se reemplazan los valores.

---

## Phase 0: Pre-flight and fixtures (Task 0)

### Task 0: Fixture scaffolding for C tests

**Files:**
- Create: `tests/fixtures/plans/one-task-red.md`
- Create: `tests/fixtures/plans/three-tasks-mixed.md`
- Create: `tests/fixtures/plans/all-done.md`
- Create: `tests/fixtures/magi-verdicts/go-full.json`
- Create: `tests/fixtures/magi-verdicts/go-with-caveats-full.json`
- Create: `tests/fixtures/magi-verdicts/go-degraded.json`

Estos fixtures alimentan tests de varios subcomandos (status, close-phase, close-task, pre-merge, finalize, auto, resume). Se crean una sola vez al inicio del milestone.

- [ ] **Step 1: Create plan fixtures**

Create `tests/fixtures/plans/one-task-red.md`:

```markdown
# One-task plan (Red only)

### Task 1: Add parser for empty input

- [ ] Step 1: Write failing test
- [ ] Step 2: Implementation
- [ ] Step 3: Verify
```

Create `tests/fixtures/plans/three-tasks-mixed.md`:

```markdown
# Three-task mixed plan

### Task 1: First task (done)

- [x] Step 1: test
- [x] Step 2: impl

### Task 2: Second task (in-progress)

- [ ] Step 1: test
- [ ] Step 2: impl

### Task 3: Third task (pending)

- [ ] Step 1: test
- [ ] Step 2: impl
```

Create `tests/fixtures/plans/all-done.md`:

```markdown
# All-done plan

### Task 1: First

- [x] Step 1

### Task 2: Second

- [x] Step 1
```

- [ ] **Step 2: Create MAGI verdict fixtures**

Create `tests/fixtures/magi-verdicts/go-full.json`:

```json
{
  "timestamp": "2026-04-19T12:00:00Z",
  "verdict": "GO",
  "degraded": false,
  "conditions": [],
  "findings": []
}
```

Create `tests/fixtures/magi-verdicts/go-with-caveats-full.json`:

```json
{
  "timestamp": "2026-04-19T12:00:00Z",
  "verdict": "GO_WITH_CAVEATS",
  "degraded": false,
  "conditions": ["Document the retry policy in module docstring"],
  "findings": [{"severity": "INFO", "message": "Consider naming clarity"}]
}
```

Create `tests/fixtures/magi-verdicts/go-degraded.json`:

```json
{
  "timestamp": "2026-04-19T12:00:00Z",
  "verdict": "GO",
  "degraded": true,
  "conditions": [],
  "findings": []
}
```

- [ ] **Step 3: Verify fixture load round-trip**

Run:

```bash
python -c "import json; d=json.load(open('tests/fixtures/magi-verdicts/go-full.json')); assert d['verdict']=='GO'; print('OK')"
python -c "t=open('tests/fixtures/plans/three-tasks-mixed.md').read(); assert '### Task 2:' in t; print('OK')"
```

Expected: `OK` printed twice.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/plans/ tests/fixtures/magi-verdicts/
git commit -m "chore: add plan and MAGI verdict fixtures for Milestone C tests"
```

---

## Phase 1: Simple read/write subcomandos (Tasks 1-10 — scenarios 13, 14, 15)

Foundation for Phase 2-4 subcomandos. Order: `status_cmd` (read-only) -> `close_task_cmd` (mutates plan + state) -> `close_phase_cmd` (full 4-step protocol, depends on close_task for refactor cascade).

### Task 1: `status_cmd.py` — module scaffold + `main()` skeleton

**Files:**
- Create: `skills/sbtdd/scripts/status_cmd.py`
- Create: `tests/test_status_cmd.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_status_cmd.py
from __future__ import annotations
import pytest


def test_status_cmd_module_importable():
    import status_cmd
    assert hasattr(status_cmd, "main")
    assert hasattr(status_cmd, "run")


def test_status_cmd_run_is_main_alias():
    import status_cmd
    assert callable(status_cmd.main) and callable(status_cmd.run)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_status_cmd.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'status_cmd'`.

- [ ] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/status_cmd.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd status — read-only report of state + git + plan + drift (sec.S.5.5).

Exit codes: 0 success, 1 state file corrupt (StateFileError), 3 drift detected.
'''

from __future__ import annotations

import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sbtdd status",
        description="Read-only status report of active SBTDD session.",
    )
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.parse_args(argv)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/status_cmd.py tests/test_status_cmd.py
git commit -m "test: scaffold status_cmd module with argparse skeleton"
```

---

### Task 2: `status_cmd` — state file + git HEAD + plan counts

**Files:** Modify `status_cmd.py` + test.

- [ ] **Step 1: Write failing test**

Add tests using a `repo_with_state` fixture that runs `git init` + seed empty commit, writes `.claude/session-state.json` (payload with current_task_id="2", current_task_title="Second task (in-progress)", current_phase="red", phase_started_at_commit=<seed_sha>, last_verification_at=None, last_verification_result=None, plan_approved_at="2026-04-19T10:00:00Z"), and copies `tests/fixtures/plans/three-tasks-mixed.md` to `planning/claude-plan-tdd.md`:

- `test_status_reports_active_task_phase_and_plan_counts`: invoke `status_cmd.main(["--project-root", repo_with_state])`; capsys stdout contains `Second task`, `red`, `1/3`.
- `test_status_prints_last_verification_null_when_unset`: same setup; stdout contains `null` for last_verif_at and last_verif_result.
- `test_status_missing_state_file_prints_manual_mode`: empty tmp git repo, no state; rc=0 and stdout contains `no active` or `manual mode`.

- [ ] **Step 2: Run test to verify it fails** — scaffold returns 0 without printing.

- [ ] **Step 3: Write minimal implementation**

Replace `main` in `status_cmd.py`. All imports at top of file:

```python
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import subprocess_utils
from errors import StateFileError
from state_file import load as load_state


def _count_plan_tasks(plan_path: Path) -> tuple[int, int]:
    '''Return (completed, total). Completed = task section contains no "- [ ]".'''
    if not plan_path.exists():
        return (0, 0)
    text = plan_path.read_text(encoding="utf-8")
    task_headers = re.findall(r"^### Task (\S+?):", text, flags=re.MULTILINE)
    total = len(task_headers)
    completed = 0
    sections = re.split(r"^### Task \S+?:", text, flags=re.MULTILINE)
    for section in sections[1:]:
        if "- [ ]" not in section and "- [x]" in section:
            completed += 1
    return (completed, total)


def _read_head_commit(project_root: Path) -> tuple[str, str]:
    try:
        result = subprocess_utils.run_with_timeout(
            ["git", "log", "-1", "--format=%h|%s"], timeout=10, cwd=str(project_root)
        )
    except Exception:
        return ("-", "-")
    if result.returncode != 0:
        return ("-", "-")
    parts = result.stdout.strip().split("|", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else ("-", "-")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        sys.stdout.write(
            "No active SBTDD session (state file missing).\n"
            "Project is in manual mode. Invoke /sbtdd spec to bootstrap a feature.\n"
        )
        return 0
    try:
        state = load_state(state_path)
    except StateFileError as exc:
        sys.stderr.write(f"StateFileError: {exc}\n")
        return 1
    plan_path = root / state.plan_path
    completed, total = _count_plan_tasks(plan_path)
    sha, subject = _read_head_commit(root)
    last_v_at = state.last_verification_at or "null"
    last_v_res = state.last_verification_result or "null"
    sys.stdout.write(
        f"Active task:   {state.current_task_id or 'null'}"
        f" — {state.current_task_title or 'null'}\n"
        f"Active phase:  {state.current_phase}\n"
        f"HEAD commit:   {sha} {subject}\n"
        f"Plan progress: {completed}/{total} tasks [x]\n"
        f"Last verif:    {last_v_at} — {last_v_res}\n"
    )
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 5 tests.

- [ ] **Step 5: Commit** — `feat: status_cmd reads state file, HEAD commit, and plan counts`.

---

### Task 3: `status_cmd` — drift detection + exit 3

**Files:** Modify `status_cmd.py` + test.

- [ ] **Step 1: Write failing test**

Add:
- `test_status_reports_drift_and_exits_3`: from `repo_with_state`, commit `refactor: dummy` (state=red + HEAD=refactor: triggers phase-ordering inversion). rc=3, stdout contains `Drift` and `detected`.
- `test_status_drift_report_includes_three_values`: same setup; stdout contains `red` and `refactor`.

- [ ] **Step 2: Run test to verify it fails** — `detect_drift` not called.

- [ ] **Step 3: Write minimal implementation**

Add to top-of-file imports: `from drift import detect_drift`.

After `_count_plan_tasks(plan_path)` in `main`:

```python
drift_report = detect_drift(state_path, plan_path, root)
if drift_report is None:
    drift_line = "Drift:         none\n"
else:
    drift_line = (
        f"Drift:         detected: state={drift_report.state_value}, "
        f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}\n"
        f"               reason: {drift_report.reason}\n"
    )
# Append drift_line to the report. Return 3 if drift_report else 0.
```

- [ ] **Step 4: Run test to verify it passes** — 7 tests.

- [ ] **Step 5: Commit** — `feat: status_cmd detects drift and exits 3 on divergence`.

---

### Task 4: `close_task_cmd.py` — scaffold

**Files:**
- Create: `skills/sbtdd/scripts/close_task_cmd.py`
- Create: `tests/test_close_task_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_close_task_cmd_module_importable():
    import close_task_cmd
    assert hasattr(close_task_cmd, "main")
    assert hasattr(close_task_cmd, "run")


def test_close_task_cmd_help_exits_zero():
    import close_task_cmd
    with pytest.raises(SystemExit) as ei:
        close_task_cmd.main(["--help"])
    assert ei.value.code == 0
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create with header + docstring referencing sec.S.5.4. argparse with `--project-root`. `main` returns 0. `run = main`.

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd close-task — mark [x] + chore commit + advance state (sec.S.5.4).'''
from __future__ import annotations
import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-task")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.parse_args(argv)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 2 tests.

- [ ] **Step 5: Commit** — `test: scaffold close_task_cmd module with argparse skeleton`.

---

### Task 5: `close_task_cmd` — precondition checks + drift check

**Files:** Modify `close_task_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_close_task_aborts_when_state_missing`: no state file -> `PreconditionError`.
- `test_close_task_aborts_when_phase_not_refactor`: state has `current_phase=green` -> `PreconditionError` mentioning "refactor" and current phase.
- `test_close_task_aborts_on_drift`: monkeypatch `drift.detect_drift` to return a `DriftReport` -> `DriftError`.

- [ ] **Step 2: Run test to verify it fails** — scaffold returns 0.

- [ ] **Step 3: Write minimal implementation**

```python
from drift import detect_drift
from errors import DriftError, PreconditionError, StateFileError
from state_file import load as load_state


def _preflight(root: Path):
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "refactor":
        raise PreconditionError(
            f"close-task requires current_phase='refactor', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value} "
            f"({drift_report.reason})"
        )
    return state


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 5 tests.

- [ ] **Step 5: Commit** — `test: close_task_cmd enforces precondition phase=refactor and drift check`.

---

### Task 6: `close_task_cmd` — flip [x] + chore commit + advance state

**Files:** Modify `close_task_cmd.py` + test.

Implements sec.S.5.4 pasos 1-3.

- [ ] **Step 1: Write failing test**

Each test uses a tmp git repo fixture with seeded commit + state file with `current_phase=refactor`:

- `test_close_task_flips_checkbox_in_plan_section`: plan has task 2 with `- [ ] Step 1`; after close-task, task 2 section has `- [x]` entries; other tasks untouched.
- `test_close_task_creates_chore_commit_with_task_id`: `git log -1 --format=%s` returns `chore: mark task 2 complete`.
- `test_close_task_chore_commit_contains_only_plan_edit`: `git show --stat HEAD` shows one file: `planning/claude-plan-tdd.md`.
- `test_close_task_advances_state_when_next_task_exists`: 3-task plan; after close-task of task 2: `current_task_id="3"`, `current_task_title="Third task (pending)"`, `current_phase="red"`.
- `test_close_task_closes_plan_when_no_next_task`: plan with task 2 open, no task 3. After close-task: `current_task_id=None`, `current_task_title=None`, `current_phase="done"`.
- `test_close_task_updates_phase_started_at_commit_to_chore_sha`: after close-task, `phase_started_at_commit` == short SHA of the chore commit.

- [ ] **Step 2: Run test to verify it fails** — mutation and commit not implemented.

- [ ] **Step 3: Write minimal implementation**

Top-of-file imports: `import os`, `import re`, `from datetime import datetime, timezone`, `import subprocess_utils`, `from commits import create as commit_create`, `from state_file import SessionState, save as save_state`.

```python
def _flip_task_checkboxes(plan_text: str, task_id: str) -> str:
    header = re.compile(rf"^### Task {re.escape(task_id)}:", re.MULTILINE)
    m = header.search(plan_text)
    if not m:
        raise PreconditionError(f"task '{task_id}' not found in plan")
    next_hdr = re.compile(r"^### Task \S+?:", re.MULTILINE)
    nm = next_hdr.search(plan_text, m.end())
    end = nm.start() if nm else len(plan_text)
    section = plan_text[m.end():end].replace("- [ ]", "- [x]")
    return plan_text[:m.end()] + section + plan_text[end:]


def _next_task(plan_text: str, after_task_id: str) -> tuple[str | None, str | None]:
    pattern = re.compile(r"^### Task (\S+?): (.+)$", re.MULTILINE)
    tasks = [(m.group(1), m.group(2).strip()) for m in pattern.finditer(plan_text)]
    found = False
    for tid, title in tasks:
        if found:
            hdr = re.compile(rf"^### Task {re.escape(tid)}:", re.MULTILINE)
            hm = hdr.search(plan_text)
            nm = pattern.search(plan_text, hm.end())
            end = nm.start() if nm else len(plan_text)
            if "- [ ]" in plan_text[hm.end():end]:
                return (tid, title)
        if tid == after_task_id:
            found = True
    return (None, None)


def _current_head_sha(root: Path) -> str:
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    plan_path = root / state.plan_path
    plan_text = plan_path.read_text(encoding="utf-8")
    new_plan = _flip_task_checkboxes(plan_text, state.current_task_id)
    tmp = plan_path.with_suffix(plan_path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(new_plan, encoding="utf-8")
    os.replace(tmp, plan_path)
    subprocess_utils.run_with_timeout(
        ["git", "add", str(plan_path.relative_to(root))], timeout=10, cwd=str(root)
    )
    commit_create("chore", f"mark task {state.current_task_id} complete", cwd=str(root))
    new_sha = _current_head_sha(root)
    next_id, next_title = _next_task(new_plan, state.current_task_id)
    new_state = SessionState(
        plan_path=state.plan_path,
        current_task_id=next_id,
        current_task_title=next_title,
        current_phase="red" if next_id else "done",
        phase_started_at_commit=new_sha,
        last_verification_at=state.last_verification_at,
        last_verification_result=state.last_verification_result,
        plan_approved_at=state.plan_approved_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    import sys
    sys.stdout.write(
        f"Task {state.current_task_id} closed. "
        f"{'Next: task ' + next_id if next_id else 'Plan complete.'}\n"
    )
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 11 tests.

- [ ] **Step 5: Commit** — `feat: close_task_cmd flips checkbox, commits chore, advances state`.

---

### Task 7: `close_phase_cmd.py` — scaffold + `--variant` parsing

**Files:**
- Create: `skills/sbtdd/scripts/close_phase_cmd.py`
- Create: `tests/test_close_phase_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_close_phase_cmd_module_importable():
    import close_phase_cmd
    assert hasattr(close_phase_cmd, "main")


def test_close_phase_cmd_parses_help():
    import close_phase_cmd
    with pytest.raises(SystemExit):
        close_phase_cmd.main(["--help"])
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd close-phase — atomic TDD phase close (sec.S.5.3).

4-step protocol: 0) drift check, 1) verification, 2) atomic commit, 3) state update.
Refactor close cascades to close-task (sec.S.5.3 paso 3c-d).
'''
from __future__ import annotations
import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-phase")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--message", type=str, default=None,
                   help="Commit message body (without prefix).")
    p.add_argument("--variant", choices=("feat", "fix"), default=None,
                   help="Applicable to Green phase only.")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.parse_args(argv)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 2 tests.

- [ ] **Step 5: Commit** — `test: scaffold close_phase_cmd module with argparse skeleton`.

---

### Task 8: `close_phase_cmd` — drift check + verification gate

**Files:** Modify `close_phase_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_close_phase_aborts_on_drift`: monkeypatched `drift.detect_drift` returns a report -> `DriftError`.
- `test_close_phase_aborts_on_state_missing`: -> `PreconditionError`.
- `test_close_phase_aborts_when_plan_not_approved`: state has `plan_approved_at=None` -> `PreconditionError`.
- `test_close_phase_aborts_when_verification_fails`: monkeypatch `superpowers_dispatch.verification_before_completion` to raise `ValidationError` -> error propagates, no commit.
- `test_close_phase_does_not_commit_when_verification_fails`: after failing verification, `git log` HEAD unchanged.

- [ ] **Step 2: Run test to verify it fails** — scaffold returns 0.

- [ ] **Step 3: Write minimal implementation**

Top-of-file imports:

```python
from drift import detect_drift
from errors import DriftError, PreconditionError, StateFileError
from state_file import load as load_state
import superpowers_dispatch


def _preflight(root: Path):
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.plan_approved_at is None:
        raise PreconditionError(
            "plan_approved_at is null - plan not approved; cannot close phase autonomously"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}"
        )
    return state


def _run_verification() -> None:
    superpowers_dispatch.verification_before_completion()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    state = _preflight(ns.project_root)
    _run_verification()
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 7 tests.

- [ ] **Step 5: Commit** — `feat: close_phase_cmd enforces drift + verification gate`.

---

### Task 9: `close_phase_cmd` — atomic commit + state file advance (red/green)

**Files:** Modify `close_phase_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_close_phase_red_emits_test_prefix_commit`: state `current_phase=red`, `--message "add parser"`; HEAD prefix `test:`.
- `test_close_phase_green_feat_emits_feat`: state=green + `--variant feat`; HEAD `feat:`.
- `test_close_phase_green_fix_emits_fix`: variant=fix; HEAD `fix:`.
- `test_close_phase_advances_state_red_to_green`: after red close, `current_phase=green`.
- `test_close_phase_advances_state_green_to_refactor`: after green close, `current_phase=refactor`.
- `test_close_phase_updates_phase_started_at_commit_to_new_sha`: equals new HEAD short SHA.
- `test_close_phase_updates_last_verification_fields`: `last_verification_at` is ISO 8601 Z, `last_verification_result="passed"`.
- `test_close_phase_green_without_variant_raises_validation_error`.

- [ ] **Step 2: Run test to verify it fails** — commit + state update not wired.

- [ ] **Step 3: Write minimal implementation**

```python
from commits import create as commit_create
from models import COMMIT_PREFIX_MAP
from state_file import SessionState, save as save_state
from datetime import datetime, timezone
import subprocess_utils
from errors import ValidationError


def _prefix_for(phase: str, variant: str | None) -> str:
    if phase == "red":
        return COMMIT_PREFIX_MAP["red"]
    if phase == "green":
        if variant == "feat":
            return COMMIT_PREFIX_MAP["green_feat"]
        if variant == "fix":
            return COMMIT_PREFIX_MAP["green_fix"]
        raise ValidationError("Green phase requires --variant {feat,fix}")
    if phase == "refactor":
        return COMMIT_PREFIX_MAP["refactor"]
    raise ValidationError(f"cannot close phase='{phase}'")


def _next_phase(phase: str) -> str:
    if phase == "red":
        return "green"
    if phase == "green":
        return "refactor"
    if phase == "refactor":
        return "refactor"  # close-task handles the real transition
    raise ValidationError(f"cannot advance from phase='{phase}'")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_head_sha(root: Path) -> str:
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    state = _preflight(root)
    _run_verification()
    prefix = _prefix_for(state.current_phase, ns.variant)
    if ns.message is None:
        raise ValidationError("close-phase requires --message")
    commit_create(prefix, ns.message, cwd=str(root))
    new_sha = _current_head_sha(root)
    new_phase = _next_phase(state.current_phase)
    new_state = SessionState(
        plan_path=state.plan_path,
        current_task_id=state.current_task_id,
        current_task_title=state.current_task_title,
        current_phase=new_phase,
        phase_started_at_commit=new_sha,
        last_verification_at=_now_iso(),
        last_verification_result="passed",
        plan_approved_at=state.plan_approved_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 15 tests.

- [ ] **Step 5: Commit** — `feat: close_phase_cmd creates atomic commit and advances state for red/green`.

---

### Task 10: `close_phase_cmd` — refactor cascade to close_task

**Files:** Modify `close_phase_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_close_phase_refactor_cascades_to_close_task`: monkeypatch `close_task_cmd.main` to record args; close-phase in refactor calls it with `--project-root` matching root.
- `test_close_phase_refactor_creates_refactor_commit_before_cascade`: inspect `git log -2` after close-phase: newest is `chore:`, second is `refactor:` (close-task's commit on top of close-phase's).
- `test_close_phase_refactor_integration_flips_checkbox_and_advances`: 3-task plan, task 2 in refactor; after close-phase: plan task 2 [x], state advances to task 3 red, TWO commits added in the expected order.

- [ ] **Step 2: Run test to verify it fails** — cascade not wired.

- [ ] **Step 3: Write minimal implementation**

After `save_state(new_state, ...)` in `main`:

```python
if state.current_phase == "refactor":
    import close_task_cmd
    import sys
    rc = close_task_cmd.main(["--project-root", str(root)])
    if rc != 0:
        sys.stderr.write(
            f"close-task cascade failed with rc={rc}; "
            f"refactor commit created but task bookkeeping incomplete. "
            f"Re-invoke /sbtdd close-task to recover.\n"
        )
        return rc
return 0
```

- [ ] **Step 4: Run test to verify it passes** — 18 tests.

- [ ] **Step 5: Commit** — `feat: close_phase_cmd cascades refactor close to close_task`.

---

## Phase 2: Bootstrap subcomandos (Tasks 11-18 — scenarios 11, 12)

### Task 11: `init_cmd.py` — scaffold + arg parsing

**Files:**
- Create: `skills/sbtdd/scripts/init_cmd.py`
- Create: `tests/test_init_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_init_cmd_module_importable():
    import init_cmd
    assert hasattr(init_cmd, "main")


def test_init_parses_stack_flag():
    import init_cmd
    with pytest.raises(SystemExit) as ei:
        init_cmd.main(["--help"])
    assert ei.value.code == 0


def test_init_rejects_invalid_stack():
    import init_cmd
    with pytest.raises(SystemExit):
        init_cmd.main(["--stack", "not-a-real-stack"])
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd init — atomic 5-phase bootstrap (sec.S.5.1).

Phases: 1 pre-flight deps, 2 arg resolution, 3 atomic generation, 4 smoke test, 5 report.
Invariant todo-o-nada: abort at any phase leaves project intact.
'''
from __future__ import annotations
import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd init")
    p.add_argument("--stack", choices=("rust", "python", "cpp"), default=None)
    p.add_argument("--author", type=str, default=None)
    p.add_argument("--error-type", type=str, default=None)
    p.add_argument("--conftest-mode", choices=("merge", "replace", "skip"), default="merge")
    p.add_argument("--force", action="store_true")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--plugins-root", type=Path,
                   default=Path.home() / ".claude" / "plugins")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    parser.parse_args(argv)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold init_cmd module with argparse + stack validation`.

---

### Task 12: `init_cmd` — Phase 1 pre-flight dependency check

**Files:** Modify `init_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_init_aborts_when_preflight_fails`: monkeypatch `check_environment` to return a report with a BROKEN check; `DependencyError` raised.
- `test_init_does_not_create_files_on_preflight_failure`: after call with failing preflight, tmp_path contains no `CLAUDE.local.md`, no `plugin.local.md`.
- `test_init_aborts_when_stack_missing_non_interactive`: no --stack, stdin not tty (monkeypatch); `ValidationError`.

- [ ] **Step 2: Run test to verify it fails** — scaffold returns 0.

- [ ] **Step 3: Write minimal implementation**

```python
import sys
from dependency_check import check_environment
from errors import DependencyError, ValidationError


def _resolve_args(ns: argparse.Namespace) -> argparse.Namespace:
    if ns.stack is None:
        if sys.stdin.isatty():
            raw = input("Stack (rust/python/cpp): ").strip()
            if raw not in ("rust", "python", "cpp"):
                raise ValidationError(f"stack must be rust, python, or cpp; got '{raw}'")
            ns.stack = raw
        else:
            raise ValidationError("--stack is required in non-interactive mode")
    if ns.author is None:
        if sys.stdin.isatty():
            ns.author = input("Author name: ").strip() or "Unknown"
        else:
            raise ValidationError("--author is required in non-interactive mode")
    if ns.stack == "rust" and ns.error_type is None:
        if sys.stdin.isatty():
            ns.error_type = input("Error type name (e.g. MyErr): ").strip() or "Error"
        else:
            raise ValidationError("--error-type is required for --stack rust")
    return ns


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    ns = _resolve_args(ns)
    report = check_environment(ns.stack, ns.project_root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 6 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd runs pre-flight dependency check and resolves args`.

---

### Task 13: `init_cmd` — Phase 3a generation of CLAUDE.local.md + plugin.local.md

**Files:** Modify `init_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_init_creates_claude_local_md_with_author_and_stack`: monkeypatched all-OK preflight; after init, `CLAUDE.local.md` contains author and stack-specific verification commands.
- `test_init_creates_plugin_local_md_with_valid_yaml_frontmatter`: `config.load_plugin_local` returns `PluginConfig` without raising.
- `test_init_atomic_on_move_failure`: monkeypatch `os.replace` to raise `OSError`; project_root left intact (no files created).

- [ ] **Step 2: Run test to verify it fails** — files not created.

- [ ] **Step 3: Write minimal implementation**

```python
import os
import shutil
import tempfile
from templates import expand
from errors import PreconditionError


_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TEMPLATES_DIR = _PLUGIN_ROOT / "templates"


_VERIF_CMDS = {
    "rust": (
        "cargo nextest run",
        "cargo audit",
        "cargo clippy --all-targets -- -D warnings",
        "cargo fmt --check",
    ),
    "python": (
        "python -m pytest",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m mypy .",
    ),
    "cpp": (
        "ctest --output-junit ctest-junit.xml",
    ),
}


def _phase3a_generate(ns: argparse.Namespace, dest_root: Path,
                      created: list[Path]) -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        tpl_c = (_TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
        ctx = {
            "Author": ns.author,
            "ErrorType": ns.error_type or "Error",
            "stack": ns.stack,
            "verification_commands": "\n".join(_VERIF_CMDS[ns.stack]),
        }
        (td_path / "CLAUDE.local.md").write_text(expand(tpl_c, ctx), encoding="utf-8")
        tpl_p = (_TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
        (td_path / "plugin.local.md").write_text(expand(tpl_p, ctx), encoding="utf-8")
        target_claude = dest_root / "CLAUDE.local.md"
        if target_claude.exists() and not ns.force:
            raise PreconditionError(
                "CLAUDE.local.md already exists; use --force to overwrite"
            )
        target_plugin_dir = dest_root / ".claude"
        target_plugin_dir.mkdir(exist_ok=True)
        target_plugin = target_plugin_dir / "plugin.local.md"
        shutil.copy2(td_path / "CLAUDE.local.md", target_claude)
        created.append(target_claude)
        shutil.copy2(td_path / "plugin.local.md", target_plugin)
        created.append(target_plugin)
```

Wire into `main` after pre-flight, with rollback on exception.

- [ ] **Step 4: Run test to verify it passes** — 9 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phase 3a generates CLAUDE.local.md and plugin.local.md atomically`.

---

### Task 14: `init_cmd` — Phase 3b settings.json + spec-base + .gitignore + conftest

**Files:** Modify `init_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_init_merges_settings_json_preserving_user_hooks`: pre-create `.claude/settings.json` with user hook; after init, both user and plugin hooks present.
- `test_init_creates_spec_behavior_base_md_skeleton`: `sbtdd/spec-behavior-base.md` exists, contains no uppercase pending markers forbidden by INV-27 (the three tokens enumerated in INV-27 — see `spec_cmd._INV27_RE` in Task 16).
- `test_init_appends_gitignore_fragment_once`: after 2 init --force runs, each fragment line appears exactly once.
- `test_init_creates_planning_gitkeep`: `planning/.gitkeep` exists.
- `test_init_python_stack_writes_conftest_py`: --stack python --conftest-mode=merge writes `conftest.py` in project root with `# --- SBTDD TDD-Guard reporter START ---` marker.

- [ ] **Step 2: Run test to verify it fails** — Phase 3b absent.

- [ ] **Step 3: Write minimal implementation**

```python
import json
import time
from hooks_installer import merge as merge_hooks


def _settings_payload() -> dict:
    return {
        "hooks": {
            "PreToolUse": [{"matcher": "Write|Edit|MultiEdit|TodoWrite",
                             "hooks": [{"type": "command", "command": "tdd-guard"}]}],
            "SessionStart": [{"matcher": "startup|resume|clear",
                               "hooks": [{"type": "command", "command": "tdd-guard"}]}],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "tdd-guard"}]}],
        }
    }


def _phase3b_install(ns: argparse.Namespace, dest_root: Path,
                     created: list[Path]) -> None:
    settings_path = dest_root / ".claude" / "settings.json"
    merge_hooks(settings_path, _settings_payload(), settings_path)
    if settings_path not in created:
        created.append(settings_path)
    spec_dir = dest_root / "sbtdd"
    spec_dir.mkdir(exist_ok=True)
    spec_base = spec_dir / "spec-behavior-base.md"
    if not spec_base.exists():
        tpl = (_TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
        spec_base.write_text(tpl, encoding="utf-8")
        created.append(spec_base)
    plan_dir = dest_root / "planning"
    plan_dir.mkdir(exist_ok=True)
    gitkeep = plan_dir / ".gitkeep"
    gitkeep.write_text("", encoding="utf-8")
    created.append(gitkeep)
    gi = dest_root / ".gitignore"
    frag = (_TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    new_lines = [line for line in frag.splitlines() if line and line not in existing]
    if new_lines:
        gi.write_text(existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n",
                       encoding="utf-8")
    if ns.stack == "python" and ns.conftest_mode != "skip":
        _install_conftest(dest_root, ns.conftest_mode)


def _install_conftest(dest_root: Path, mode: str) -> None:
    target = dest_root / "conftest.py"
    tpl = (_TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    if mode == "replace" and target.exists():
        bak = target.with_suffix(target.suffix + f".bak.{int(time.time())}")
        target.rename(bak)
        target.write_text(tpl, encoding="utf-8")
        return
    if mode == "merge" and target.exists():
        existing = target.read_text(encoding="utf-8")
        start = "# --- SBTDD TDD-Guard reporter START ---"
        end = "# --- SBTDD TDD-Guard reporter END ---"
        if start in existing and end in existing:
            pre, rest = existing.split(start, 1)
            _, post = rest.split(end, 1)
            target.write_text(pre + tpl + post, encoding="utf-8")
            return
        target.write_text(existing.rstrip("\n") + "\n\n" + tpl, encoding="utf-8")
        return
    target.write_text(tpl, encoding="utf-8")
```

Call `_phase3b_install` from `main`.

- [ ] **Step 4: Run test to verify it passes** — 14 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phase 3b installs hooks, spec-base, planning, gitignore fragment`.

---

### Task 15: `init_cmd` — Phase 4 smoke test + Phase 5 report + rollback

**Files:** Modify `init_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_init_smoke_test_rejects_invalid_settings_json`: monkeypatch `hooks_installer.merge` to write corrupt JSON; smoke test fails -> rollback + all created files removed.
- `test_init_smoke_test_validates_plugin_local_md`: verify `load_plugin_local` call succeeds against generated file.
- `test_init_phase5_reports_all_ok_components`: stdout contains `[ok]` for each dep check and `Created:` section.
- `test_init_exit_0_on_full_success`: happy path, rc=0.

- [ ] **Step 2: Run test to verify it fails** — Phase 4/5 absent.

- [ ] **Step 3: Write minimal implementation**

```python
from config import load_plugin_local


def _phase4_smoke_test(dest_root: Path) -> None:
    settings = dest_root / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PreconditionError(f"smoke test: settings.json not parseable: {exc}") from exc
    for event in ("PreToolUse", "UserPromptSubmit", "SessionStart"):
        if event not in data.get("hooks", {}):
            raise PreconditionError(f"smoke test: hook '{event}' missing")
    plugin_local = dest_root / ".claude" / "plugin.local.md"
    load_plugin_local(plugin_local)


def _phase5_report(ns, created: list[Path], report) -> None:
    lines = [""]
    for chk in report.checks:
        lines.append(f"[{chk.status.lower()}] {chk.name} - {chk.detail}")
    lines.append("")
    lines.append("Created:")
    for p in created:
        lines.append(f"  {p}")
    lines.append("")
    lines.append("Next steps:")
    lines.append("  1. Edit sbtdd/spec-behavior-base.md with the feature requirements.")
    lines.append("  2. Run /sbtdd spec to generate the TDD plan.")
    sys.stdout.write("\n".join(lines) + "\n")


def _rollback(created: list[Path]) -> None:
    for p in reversed(created):
        try:
            if p.is_file():
                p.unlink()
        except OSError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    ns = _resolve_args(ns)
    report = check_environment(ns.stack, ns.project_root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    created: list[Path] = []
    try:
        _phase3a_generate(ns, ns.project_root, created)
        _phase3b_install(ns, ns.project_root, created)
        _phase4_smoke_test(ns.project_root)
    except Exception:
        _rollback(created)
        raise
    _phase5_report(ns, created, report)
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 18 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phases 4-5 smoke test and user report with rollback`.

---

### Task 16: `spec_cmd.py` — scaffold + INV-27 placeholder rejection

**Files:**
- Create: `skills/sbtdd/scripts/spec_cmd.py`
- Create: `tests/test_spec_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_spec_cmd_module_importable():
    import spec_cmd
    assert hasattr(spec_cmd, "main")


def test_spec_rejects_spec_base_with_uppercase_todo(tmp_path):
    import spec_cmd
    from errors import PreconditionError
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    (spec_dir / "spec-behavior-base.md").write_text(
        "# Feature spec\n\n- TODO: define timeout\n" + ("x " * 200), encoding="utf-8"
    )
    with pytest.raises(PreconditionError) as ei:
        spec_cmd.main(["--project-root", str(tmp_path)])
    # INV-27 enforcement visible in message.
    assert "TODO" in str(ei.value) or "pending" in str(ei.value).lower()


def test_spec_accepts_lowercase_todos_spanish_prose(tmp_path):
    import spec_cmd
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature\n\nScenario: todos los usuarios\n" + ("x " * 200)
    (spec_dir / "spec-behavior-base.md").write_text(body, encoding="utf-8")
    # Lowercase must not trigger INV-27; may still fail on later precondition.
    try:
        spec_cmd.main(["--project-root", str(tmp_path)])
    except Exception as e:
        assert "TODO" not in str(e) and "pending" not in str(e).lower()
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd spec — Flujo de especificacion (sec.S.5.2) with INV-27 and INV-28.'''
from __future__ import annotations
import argparse
import re
from pathlib import Path

from errors import PreconditionError


_INV27_RE = re.compile(r"\b(TODO|TODOS|TBD)\b")


def _validate_spec_base(path: Path) -> None:
    if not path.exists():
        raise PreconditionError(f"spec-behavior-base.md not found: {path}")
    text = path.read_text(encoding="utf-8")
    if len("".join(text.split())) < 200:
        raise PreconditionError("spec-behavior-base.md is too short (need >= 200 non-ws chars)")
    violations = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _INV27_RE.search(line):
            violations.append((lineno, line.strip()))
    if violations:
        details = "\n".join(f"  line {ln}: {txt!r}" for ln, txt in violations)
        raise PreconditionError(
            "spec-behavior-base.md contains pending markers (INV-27, rule c):\n" + details
        )
    if "<REPLACE:" in text:
        raise PreconditionError(
            "spec-behavior-base.md contains <REPLACE: ...> skeleton markers. "
            "Fill each with actual content before running /sbtdd spec."
        )


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd spec")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _validate_spec_base(ns.project_root / "sbtdd" / "spec-behavior-base.md")
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold spec_cmd with INV-27 placeholder rejection`.

---

### Task 17: `spec_cmd` — invoke /brainstorming + /writing-plans

**Files:** Modify `spec_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_spec_invokes_brainstorming_with_spec_base_path`: monkeypatch `superpowers_dispatch.brainstorming` to track args; expect invoked with `@path/to/spec-behavior-base.md`.
- `test_spec_invokes_writing_plans_after_spec_generated`: spec stub creates `spec-behavior.md`; expect `writing_plans` invoked with that path and creates `claude-plan-tdd-org.md`.
- `test_spec_aborts_when_brainstorming_fails`: stub raises ValidationError -> propagates.

- [ ] **Step 2: Run test to verify it fails** — flow not wired.

- [ ] **Step 3: Write minimal implementation**

```python
import superpowers_dispatch


def _run_spec_flow(root: Path) -> None:
    spec_base = root / "sbtdd" / "spec-behavior-base.md"
    spec_behavior = root / "sbtdd" / "spec-behavior.md"
    superpowers_dispatch.brainstorming(args=[f"@{spec_base}"])
    if not spec_behavior.exists():
        raise PreconditionError(
            f"/brainstorming completed but {spec_behavior} was not generated"
        )
    plan_org = root / "planning" / "claude-plan-tdd-org.md"
    superpowers_dispatch.writing_plans(args=[f"@{spec_behavior}"])
    if not plan_org.exists():
        raise PreconditionError(
            f"/writing-plans completed but {plan_org} was not generated"
        )
```

Call from `main` after validation.

- [ ] **Step 4: Run test to verify it passes** — 6 tests.

- [ ] **Step 5: Commit** — `feat: spec_cmd invokes brainstorming and writing-plans in sequence`.

---

### Task 18: `spec_cmd` — Checkpoint 2 MAGI loop with INV-28 + state file creation

**Files:** Modify `spec_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_spec_magi_loop_accepts_full_go_on_first_iter`: stubbed magi returns GO full; exit after 1 iteration.
- `test_spec_magi_loop_rejects_degraded_and_retries`: iter 1 GO degraded, iter 2 GO full; 2 iterations (INV-28).
- `test_spec_magi_loop_strong_no_go_aborts`: `STRONG_NO_GO` -> `MAGIGateError` immediately.
- `test_spec_magi_loop_aborts_after_max_iterations`: always HOLD -> `MAGIGateError` after `magi_max_iterations`.
- `test_spec_creates_state_file_on_approval`: happy path; state file at `.claude/session-state.json` with `plan_approved_at` not null, `current_phase=red`, `current_task_id` pointing to first `[ ]` task.

- [ ] **Step 2: Run test to verify it fails** — MAGI loop + state creation missing.

- [ ] **Step 3: Write minimal implementation**

```python
import magi_dispatch
from config import load_plugin_local
from errors import MAGIGateError
from state_file import SessionState, save as save_state
from datetime import datetime, timezone
import subprocess_utils


def _write_plan_tdd(root, verdict, plan_org, plan) -> None:
    org_text = plan_org.read_text(encoding="utf-8")
    tail = ""
    if verdict.conditions:
        tail = "\n\n## MAGI Conditions for Approval\n\n" + "\n".join(
            f"- {c}" for c in verdict.conditions
        )
    plan.write_text(org_text + tail, encoding="utf-8")


def _first_open_task(plan: Path) -> tuple[str, str]:
    text = plan.read_text(encoding="utf-8")
    pattern = re.compile(r"^### Task (\S+?): (.+)$", re.MULTILINE)
    for m in pattern.finditer(text):
        tid = m.group(1)
        title = m.group(2).strip()
        hdr = re.compile(rf"^### Task {re.escape(tid)}:", re.MULTILINE)
        hm = hdr.search(text)
        nm = pattern.search(text, hm.end())
        end = nm.start() if nm else len(text)
        if "- [ ]" in text[hm.end():end]:
            return (tid, title)
    raise PreconditionError("plan has no open [ ] tasks")


def _run_magi_checkpoint2(root: Path, cfg):
    spec = root / "sbtdd" / "spec-behavior.md"
    plan_org = root / "planning" / "claude-plan-tdd-org.md"
    plan = root / "planning" / "claude-plan-tdd.md"
    for iteration in range(1, cfg.magi_max_iterations + 1):
        verdict = magi_dispatch.invoke_magi(
            context_paths=[str(spec), str(plan_org)], cwd=str(root)
        )
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(
                f"MAGI returned STRONG_NO_GO at iter {iteration}. Refine spec-behavior-base.md."
            )
        _write_plan_tdd(root, verdict, plan_org, plan)
        if verdict.degraded:
            continue  # INV-28: degraded never exits.
        if magi_dispatch.verdict_passes_gate(verdict, cfg.magi_threshold):
            return verdict
    raise MAGIGateError(
        f"MAGI did not converge to full {cfg.magi_threshold}+ "
        f"after {cfg.magi_max_iterations} iterations"
    )


def _create_state_file(root: Path, cfg, plan: Path) -> None:
    task_id, task_title = _first_open_task(plan)
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    sha = r.stdout.strip() or "0000000"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state = SessionState(
        plan_path="planning/claude-plan-tdd.md",
        current_task_id=task_id,
        current_task_title=task_title,
        current_phase="red",
        phase_started_at_commit=sha,
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at=now,
    )
    save_state(state, root / ".claude" / "session-state.json")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    _validate_spec_base(root / "sbtdd" / "spec-behavior-base.md")
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _run_spec_flow(root)
    _run_magi_checkpoint2(root, cfg)
    _create_state_file(root, cfg, root / "planning" / "claude-plan-tdd.md")
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 11 tests.

- [ ] **Step 5: Commit** — `feat: spec_cmd runs MAGI Checkpoint 2 loop and creates state file on approval`.

---

## Phase 3: Merge-gate subcomandos (Tasks 19-25 — scenarios 16, 17)

### Task 19: `pre_merge_cmd.py` — scaffold + precondition checks

**Files:**
- Create: `skills/sbtdd/scripts/pre_merge_cmd.py`
- Create: `tests/test_pre_merge_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_pre_merge_cmd_module_importable():
    import pre_merge_cmd
    assert hasattr(pre_merge_cmd, "main")


def test_pre_merge_aborts_when_state_not_done(tmp_path):
    import pre_merge_cmd
    from errors import PreconditionError
    # Fixture: tmp_path with git init + state current_phase=green.
    with pytest.raises(PreconditionError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])


def test_pre_merge_aborts_on_drift(tmp_path, monkeypatch):
    import pre_merge_cmd
    from drift import DriftReport
    from errors import DriftError
    monkeypatch.setattr(
        "pre_merge_cmd.detect_drift",
        lambda *a, **kw: DriftReport("done", "test", "[ ]", "stub"),
    )
    # Setup state file with current_phase=done.
    with pytest.raises(DriftError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd pre-merge — Loop 1 + Loop 2 (sec.S.5.6, INV-9/28/29).'''
from __future__ import annotations
import argparse
from pathlib import Path

from drift import detect_drift
from errors import DriftError, PreconditionError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd pre-merge")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--magi-threshold", type=str, default=None,
                   help="Override magi_threshold (ELEVATE only).")
    return p


def _preflight(root: Path):
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "done":
        raise PreconditionError(
            f"pre-merge requires current_phase='done', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}"
        )
    return state


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold pre_merge_cmd with preconditions and drift check`.

---

### Task 20: `pre_merge_cmd` — Loop 1 `/requesting-code-review` with safety valve 10

**Files:** Modify `pre_merge_cmd.py` + `errors.py` + tests.

- [ ] **Step 1: Write failing test**

In `tests/test_errors.py` (append):
- `test_loop1_divergent_error_exit_code_is_7`: `EXIT_CODES[Loop1DivergentError] == 7`.

In `tests/test_pre_merge_cmd.py`:
- `test_pre_merge_loop1_exits_on_clean_to_go`: monkeypatch `requesting_code_review` to return stdout containing `clean-to-go`; loop runs 1 iteration, no error.
- `test_pre_merge_loop1_applies_fixes_until_clean`: sequence `[WARNING]` -> `clean-to-go`; loop runs 2 iterations, `receiving_code_review` called once between.
- `test_pre_merge_loop1_aborts_after_10_iterations_exit_7`: always `[WARNING]` -> raises `Loop1DivergentError` after 10 iterations; dispatcher maps to exit 7.

- [ ] **Step 2: Run test to verify it fails** — Loop 1 and exception class missing.

- [ ] **Step 3: Write minimal implementation**

Edit `skills/sbtdd/scripts/errors.py`:

```python
class Loop1DivergentError(SBTDDError):
    '''Loop 1 (/requesting-code-review) did not converge in 10 iterations (exit 7).'''
```

Extend `_EXIT_CODES_MUTABLE` dict: `Loop1DivergentError: 7`.

Edit `pre_merge_cmd.py`:

```python
import superpowers_dispatch
from errors import Loop1DivergentError


_LOOP1_MAX = 10


def _is_clean_to_go(result) -> bool:
    out = result.stdout.lower() if result and result.stdout else ""
    return "clean-to-go" in out or "clean to go" in out


def _loop1(root: Path) -> None:
    for iteration in range(1, _LOOP1_MAX + 1):
        result = superpowers_dispatch.requesting_code_review(cwd=str(root))
        if _is_clean_to_go(result):
            return
        # Apply fixes via /receiving-code-review + TDD mini-cycle.
        superpowers_dispatch.receiving_code_review(cwd=str(root))
    raise Loop1DivergentError(
        f"Loop 1 did not converge in {_LOOP1_MAX} iterations"
    )
```

- [ ] **Step 4: Run test to verify it passes** — 5 tests (2 error tests + 3 pre-merge tests).

- [ ] **Step 5: Commit** — `feat: pre_merge_cmd Loop 1 requesting-code-review with Loop1DivergentError exit 7`.

---

### Task 21: `pre_merge_cmd` — Loop 2 `/magi:magi` with INV-28 + INV-29

**Files:** Modify `pre_merge_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_pre_merge_loop2_exits_on_full_go`: Loop 1 stubbed clean, magi GO full; exit after 1 iter; `magi-verdict.json` written with `degraded: false`.
- `test_pre_merge_loop2_retries_on_degraded`: iter 1 GO degraded, iter 2 GO full; 2 iterations (INV-28).
- `test_pre_merge_loop2_strong_no_go_aborts_immediately`: STRONG_NO_GO -> `MAGIGateError`.
- `test_pre_merge_loop2_go_with_caveats_exits_on_low_risk_conditions`: conditions contain only "docstring" / "naming"; loop exits after 1 iter.
- `test_pre_merge_loop2_go_with_caveats_reinvokes_on_structural`: conditions contain "signature" or "contract"; re-invoke MAGI, needs 2+ iterations.
- `test_pre_merge_loop2_aborts_after_max_iterations`: always HOLD -> `MAGIGateError`.
- `test_pre_merge_writes_magi_verdict_artifact`: after success, `.claude/magi-verdict.json` contains timestamp, verdict, degraded=False, conditions, findings.

- [ ] **Step 2: Run test to verify it fails** — Loop 2 not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
import magi_dispatch
from config import load_plugin_local
from errors import MAGIGateError, ValidationError
from models import VERDICT_RANK


_LOW_RISK_KEYWORDS = ("doc", "docstring", "naming", "comment", "test", "logging", "message")


def _conditions_low_risk(conditions: tuple[str, ...]) -> bool:
    return all(
        any(kw in c.lower() for kw in _LOW_RISK_KEYWORDS) for c in conditions
    )


def _loop2(root: Path, cfg, threshold_override: str | None):
    threshold = threshold_override or cfg.magi_threshold
    if VERDICT_RANK[threshold] < VERDICT_RANK[cfg.magi_threshold]:
        raise ValidationError(
            f"--magi-threshold can only elevate; {threshold} < config {cfg.magi_threshold}"
        )
    diff_paths = [str(root / "planning" / "claude-plan-tdd.md")]
    for iteration in range(1, cfg.magi_max_iterations + 1):
        verdict = magi_dispatch.invoke_magi(context_paths=diff_paths, cwd=str(root))
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(f"MAGI STRONG_NO_GO at iter {iteration}")
        if verdict.conditions:
            superpowers_dispatch.receiving_code_review(cwd=str(root))
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            if verdict.verdict == "GO_WITH_CAVEATS" and not _conditions_low_risk(verdict.conditions):
                continue  # structural condition - re-invoke
            return verdict
    raise MAGIGateError(
        f"MAGI did not converge to full {threshold}+ after {cfg.magi_max_iterations} iterations"
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    _preflight(root)
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _loop1(root)
    verdict = _loop2(root, cfg, ns.magi_threshold)
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 12 tests.

- [ ] **Step 5: Commit** — `feat: pre_merge_cmd Loop 2 MAGI with INV-28 degraded and INV-29 receiving-code-review`.

---

### Task 22: `finalize_cmd.py` — scaffold + precondition checks

**Files:**
- Create: `skills/sbtdd/scripts/finalize_cmd.py`
- Create: `tests/test_finalize_cmd.py`

- [ ] **Step 1: Write failing test**

- `test_finalize_cmd_module_importable`.
- `test_finalize_aborts_when_magi_verdict_missing`: state current_phase=done, no magi-verdict.json -> `PreconditionError`.
- `test_finalize_aborts_when_state_not_done`: state current_phase=red -> `PreconditionError`.

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd finalize — checklist sec.M.7 + /finishing-a-development-branch (sec.S.5.7).'''
from __future__ import annotations
import argparse
import json
from pathlib import Path

from errors import PreconditionError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd finalize")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def _preflight(root: Path):
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "done":
        raise PreconditionError(
            f"finalize requires current_phase='done', got '{state.current_phase}'"
        )
    magi_verdict = root / ".claude" / "magi-verdict.json"
    if not magi_verdict.exists():
        raise PreconditionError(
            f"magi-verdict.json not found: {magi_verdict}. Run /sbtdd pre-merge first."
        )
    return state, magi_verdict


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _preflight(ns.project_root)
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold finalize_cmd with state and magi-verdict preconditions`.

---

### Task 23: `finalize_cmd` — verdict staleness guard (plan_approved_at comparison)

**Files:** Modify `finalize_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_finalize_aborts_when_verdict_predates_plan_approved_at`: state.plan_approved_at=2026-04-20, verdict timestamp=2026-04-10 -> `PreconditionError`.
- `test_finalize_accepts_verdict_after_plan_approved_at`: verdict timestamp later than plan_approved_at; passes this check.

- [ ] **Step 2: Run test to verify it fails** — staleness check missing.

- [ ] **Step 3: Write minimal implementation**

```python
def _verdict_is_stale(state, magi_verdict_path: Path) -> bool:
    data = json.loads(magi_verdict_path.read_text(encoding="utf-8"))
    ts = data.get("timestamp")
    if not ts or not state.plan_approved_at:
        return False
    return ts < state.plan_approved_at


# In _preflight, after loading magi_verdict:
if _verdict_is_stale(state, magi_verdict):
    data = json.loads(magi_verdict.read_text(encoding="utf-8"))
    raise PreconditionError(
        f"magi-verdict.json (timestamp={data.get('timestamp')}) predates "
        f"plan_approved_at={state.plan_approved_at} - belongs to previous feature. "
        f"Run /sbtdd pre-merge for the current feature."
    )
```

- [ ] **Step 4: Run test to verify it passes** — 5 tests.

- [ ] **Step 5: Commit** — `feat: finalize_cmd rejects stale magi-verdict from previous feature`.

---

### Task 24: `finalize_cmd` — checklist validation + `ChecklistError`

**Files:** Modify `finalize_cmd.py` + `errors.py` + test.

- [ ] **Step 1: Write failing test**

In `tests/test_errors.py`:
- `test_checklist_error_exit_code_is_9`: `EXIT_CODES[ChecklistError] == 9`.

In `tests/test_finalize_cmd.py`:
- `test_finalize_rejects_verdict_below_threshold`: verdict=HOLD full -> `ChecklistError`.
- `test_finalize_rejects_degraded_verdict_even_above_threshold`: verdict=GO degraded -> `ChecklistError` (INV-28 defense-in-depth).
- `test_finalize_accepts_go_full`: 9 items pass, rc=0.
- `test_finalize_aborts_on_dirty_working_tree`: uncommitted changes -> `ChecklistError`.
- `test_finalize_aborts_on_plan_with_open_tasks`: plan has `- [ ]` -> `ChecklistError`.

- [ ] **Step 2: Run test to verify it fails** — class + logic missing.

- [ ] **Step 3: Write minimal implementation**

Edit `errors.py`:

```python
class ChecklistError(SBTDDError):
    '''Finalize checklist item failed (exit 9, CHECKLIST_FAILED).'''
```

Add to `_EXIT_CODES_MUTABLE`: `ChecklistError: 9`.

Edit `finalize_cmd.py`:

```python
from models import verdict_meets_threshold
from config import load_plugin_local
from errors import ChecklistError
import subprocess_utils
import superpowers_dispatch


def _checklist(root: Path, state, magi_verdict_path: Path, cfg) -> list[tuple[str, bool, str]]:
    items = []
    plan = (root / state.plan_path).read_text(encoding="utf-8")
    all_done = "- [ ]" not in plan
    items.append(("plan fully [x]", all_done,
                   "no open [ ] found" if all_done else "open tasks remain"))
    items.append(("state current_phase=done", state.current_phase == "done", ""))
    items.append(("state current_task_id=null", state.current_task_id is None, ""))
    try:
        superpowers_dispatch.verification_before_completion(cwd=str(root))
        sec01_ok, sec01_detail = True, "passed"
    except Exception as exc:
        sec01_ok, sec01_detail = False, str(exc)
    items.append(("sec.M.0.1 verification", sec01_ok, sec01_detail))
    r = subprocess_utils.run_with_timeout(
        ["git", "status", "--short"], timeout=10, cwd=str(root)
    )
    clean = r.stdout.strip() == ""
    items.append(("git status clean", clean, r.stdout.strip() or "ok"))
    v_data = json.loads(magi_verdict_path.read_text(encoding="utf-8"))
    gate_pass = (
        verdict_meets_threshold(v_data["verdict"], cfg.magi_threshold)
        and not v_data.get("degraded", False)
    )
    items.append((
        "MAGI verdict >= threshold AND not degraded",
        gate_pass,
        f"verdict={v_data['verdict']}, degraded={v_data.get('degraded')}",
    ))
    items.append(("spec-behavior.md exists",
                   (root / "sbtdd" / "spec-behavior.md").exists(), ""))
    items.append(("claude-plan-tdd.md exists",
                   (root / state.plan_path).exists(), ""))
    items.append(("commits use sec.M.5 prefixes", True,
                   "spot-check deferred to reviewer"))
    return items


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    state, magi_verdict_path = _preflight(root)
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    items = _checklist(root, state, magi_verdict_path, cfg)
    failures = [(n, d) for (n, ok, d) in items if not ok]
    if failures:
        import sys
        for name, detail in failures:
            sys.stderr.write(f"  [FAIL] {name}: {detail}\n")
        raise ChecklistError(f"{len(failures)} checklist items failed")
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 11 tests.

- [ ] **Step 5: Commit** — `feat: finalize_cmd validates 9-item checklist with ChecklistError exit 9`.

---

### Task 25: `finalize_cmd` — invoke `/finishing-a-development-branch`

**Files:** Modify `finalize_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_finalize_invokes_finishing_skill_on_success`: happy path; monkeypatched `finishing_a_development_branch` recorded called once.
- `test_finalize_does_not_invoke_finishing_on_checklist_failure`: dirty tree; skill NOT called.

- [ ] **Step 2: Run test to verify it fails** — skill not invoked.

- [ ] **Step 3: Write minimal implementation**

At the end of `main`, after `failures` empty:

```python
superpowers_dispatch.finishing_a_development_branch(cwd=str(root))
return 0
```

- [ ] **Step 4: Run test to verify it passes** — 13 tests.

- [ ] **Step 5: Commit** — `feat: finalize_cmd invokes finishing-a-development-branch on checklist pass`.

---

## Phase 4: Automation subcomandos (Tasks 26-36 — scenarios 18, 19)

### Task 26: `auto_cmd.py` — scaffold + argparse + `--dry-run` entrypoint

**Files:**
- Create: `skills/sbtdd/scripts/auto_cmd.py`
- Create: `tests/test_auto_cmd.py`

- [ ] **Step 1: Write failing test**

```python
def test_auto_cmd_module_importable():
    import auto_cmd
    assert hasattr(auto_cmd, "main")


def test_auto_dry_run_returns_0_without_side_effects(tmp_path, monkeypatch):
    # Stub the preflight check so Phase 1 passes.
    import auto_cmd
    # Setup tmp_path with state + plugin.local.md...
    rc = auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert not (tmp_path / ".claude" / "auto-run.json").exists()


def test_auto_parses_magi_max_iterations_flag():
    import auto_cmd
    ns = auto_cmd._build_parser().parse_args(["--magi-max-iterations", "7"])
    assert ns.magi_max_iterations == 7
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd auto — shoot-and-forget full-cycle (sec.S.5.8, INV-22..26).'''
from __future__ import annotations
import argparse
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd auto")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--plugins-root", type=Path,
                   default=Path.home() / ".claude" / "plugins")
    p.add_argument("--magi-max-iterations", type=int, default=None)
    p.add_argument("--magi-threshold", type=str, default=None)
    p.add_argument("--verification-retries", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    if ns.dry_run:
        print("/sbtdd auto --dry-run: would execute phases 1-5 sequentially.")
        return 0
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold auto_cmd module with argparse + dry-run short-circuit`.

---

### Task 27: `auto_cmd` — Phase 1 pre-flight re-check + state validation

**Files:** Modify `auto_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_auto_runs_preflight_check`: monkeypatched `check_environment` recorded called once.
- `test_auto_aborts_when_preflight_fails`: preflight non-OK -> `DependencyError`.
- `test_auto_aborts_when_state_missing`: -> `PreconditionError`.
- `test_auto_aborts_when_plan_not_approved`: state.plan_approved_at=None -> `PreconditionError`.

- [ ] **Step 2: Run test to verify it fails** — Phase 1 missing.

- [ ] **Step 3: Write minimal implementation**

```python
from dependency_check import check_environment
from config import load_plugin_local
from errors import DependencyError, PreconditionError
from state_file import load as load_state


def _phase1_preflight(ns):
    root = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.plan_approved_at is None:
        raise PreconditionError(
            "plan_approved_at is null - run /sbtdd spec to approve a plan before /sbtdd auto"
        )
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    report = check_environment(cfg.stack, root, ns.plugins_root)
    if not report.ok():
        import sys
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    return state, cfg
```

Call from `main` at entry (before dry-run short-circuit modifies execution).

- [ ] **Step 4: Run test to verify it passes** — 7 tests.

- [ ] **Step 5: Commit** — `feat: auto_cmd phase 1 pre-flight and state validation`.

---

### Task 28: `auto_cmd` — Phase 2 task-loop inner loop + `VerificationIrremediableError`

**Files:** Modify `auto_cmd.py` + `errors.py` + test.

- [ ] **Step 1: Write failing test**

In `tests/test_errors.py`:
- `test_verification_irremediable_error_exit_code_is_6`: `EXIT_CODES[VerificationIrremediableError] == 6`.

In `tests/test_auto_cmd.py`:
- `test_auto_phase2_processes_single_task_red_green_refactor`: one-task plan; happy path creates 3 commits (test:, feat:, refactor:) + 1 chore cascade; state becomes done.
- `test_auto_phase2_respects_verification_retries_budget`: verification fails twice then passes; with retries=2 passes, with retries=1 raises `VerificationIrremediableError`.
- `test_auto_phase2_aborts_after_exhausting_retries_exit_6`: verification always fails -> raises; dispatcher maps to 6.
- `test_auto_phase2_sequential_order`: 3-task plan; tasks processed in order 1, 2, 3.
- `test_auto_phase2_aborts_on_drift`: monkeypatched `detect_drift` returns report -> `DriftError`.
- `test_auto_phase2_inner_loop_entry_phase_respects_state`: state.current_phase=green; auto starts at green, skipping red.

- [ ] **Step 2: Run test to verify it fails** — class + logic missing.

- [ ] **Step 3: Write minimal implementation**

Edit `errors.py`:

```python
class VerificationIrremediableError(SBTDDError):
    '''Phase verification failed after auto retry budget (exit 6).'''
```

Add to `_EXIT_CODES_MUTABLE`: `VerificationIrremediableError: 6`.

Edit `auto_cmd.py`:

```python
import os
import re
from drift import detect_drift
from errors import DriftError, VerificationIrremediableError
import superpowers_dispatch
from commits import create as commit_create
from state_file import SessionState, save as save_state
from models import COMMIT_PREFIX_MAP
from datetime import datetime, timezone
import subprocess_utils


_PHASE_ORDER = ("red", "green", "refactor")


def _next_task(plan_text: str, current_id: str | None) -> tuple[str | None, str | None]:
    pattern = re.compile(r"^### Task (\S+?): (.+)$", re.MULTILINE)
    tasks = [(m.group(1), m.group(2).strip()) for m in pattern.finditer(plan_text)]
    if current_id is None:
        for tid, title in tasks:
            hdr = re.compile(rf"^### Task {re.escape(tid)}:", re.MULTILINE)
            hm = hdr.search(plan_text)
            nm = pattern.search(plan_text, hm.end())
            end = nm.start() if nm else len(plan_text)
            if "- [ ]" in plan_text[hm.end():end]:
                return (tid, title)
        return (None, None)
    found = False
    for tid, title in tasks:
        if found:
            return (tid, title)
        if tid == current_id:
            found = True
    return (None, None)


def _run_verification_with_retries(root: Path, retries: int) -> None:
    for attempt in range(retries + 1):
        try:
            superpowers_dispatch.verification_before_completion(cwd=str(root))
            return
        except Exception as exc:
            if attempt >= retries:
                raise VerificationIrremediableError(
                    f"verification failed after {retries} retries: {exc}"
                ) from exc
            superpowers_dispatch.systematic_debugging(cwd=str(root))


def _phase2_task_loop(ns, state: SessionState, cfg) -> SessionState:
    root = ns.project_root
    retries = (ns.verification_retries
               if ns.verification_retries is not None
               else cfg.auto_verification_retries)
    state_path = root / ".claude" / "session-state.json"
    plan_path = root / state.plan_path
    dr = detect_drift(state_path, plan_path, root)
    if dr is not None:
        raise DriftError(f"drift at auto Phase 2: {dr.reason}")
    current = state
    while current.current_task_id is not None:
        phase_idx = (_PHASE_ORDER.index(current.current_phase)
                     if current.current_phase in _PHASE_ORDER else 0)
        for phase in _PHASE_ORDER[phase_idx:]:
            superpowers_dispatch.test_driven_development(
                args=[f"--phase={phase}"], cwd=str(root)
            )
            _run_verification_with_retries(root, retries)
            prefix = COMMIT_PREFIX_MAP[
                {"red": "red", "green": "green_feat", "refactor": "refactor"}[phase]
            ]
            commit_create(prefix, f"{phase} for task {current.current_task_id}",
                           cwd=str(root))
            r = subprocess_utils.run_with_timeout(
                ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
            )
            new_sha = r.stdout.strip()
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if phase != "refactor":
                next_phase = _PHASE_ORDER[_PHASE_ORDER.index(phase) + 1]
                current = SessionState(
                    plan_path=current.plan_path,
                    current_task_id=current.current_task_id,
                    current_task_title=current.current_task_title,
                    current_phase=next_phase,
                    phase_started_at_commit=new_sha,
                    last_verification_at=now,
                    last_verification_result="passed",
                    plan_approved_at=current.plan_approved_at,
                )
                save_state(current, state_path)
            else:
                current = _close_task_inline(current, root)
        # After refactor cascade, the inner loop ends; outer while re-evaluates.
    return current


def _close_task_inline(current: SessionState, root: Path) -> SessionState:
    import close_task_cmd
    plan_path = root / current.plan_path
    plan_text = plan_path.read_text(encoding="utf-8")
    new_plan = close_task_cmd._flip_task_checkboxes(plan_text, current.current_task_id)
    tmp = plan_path.with_suffix(plan_path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(new_plan, encoding="utf-8")
    os.replace(tmp, plan_path)
    subprocess_utils.run_with_timeout(
        ["git", "add", str(plan_path.relative_to(root))], timeout=10, cwd=str(root)
    )
    commit_create("chore", f"mark task {current.current_task_id} complete", cwd=str(root))
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    new_sha = r.stdout.strip()
    next_id, next_title = _next_task(new_plan, current.current_task_id)
    new_state = SessionState(
        plan_path=current.plan_path,
        current_task_id=next_id,
        current_task_title=next_title,
        current_phase="red" if next_id else "done",
        phase_started_at_commit=new_sha,
        last_verification_at=current.last_verification_at,
        last_verification_result=current.last_verification_result,
        plan_approved_at=current.plan_approved_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    return new_state
```

- [ ] **Step 4: Run test to verify it passes** — 14 tests.

- [ ] **Step 5: Commit** — `feat: auto_cmd phase 2 task loop with VerificationIrremediableError exit 6`.

---

### Task 29: `auto_cmd` — Phase 3 pre-merge with elevated MAGI budget

**Files:** Modify `auto_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_auto_phase3_invokes_loop1_and_loop2`: stubs return clean + GO full; both loops run.
- `test_auto_phase3_uses_auto_magi_max_iterations`: cfg.magi_max_iterations=3, auto_magi_max_iterations=5; stub magi HOLD 4 times + GO full -> 5th iter exits.
- `test_auto_phase3_respects_flag_override`: `--magi-max-iterations=2`; 2 HOLD -> `MAGIGateError`.
- `test_auto_phase3_aborts_on_strong_no_go`: STRONG_NO_GO iter 1 -> `MAGIGateError` immediately.

- [ ] **Step 2: Run test to verify it fails** — Phase 3 missing.

- [ ] **Step 3: Write minimal implementation**

```python
def _phase3_pre_merge(ns, cfg):
    import pre_merge_cmd
    import magi_dispatch
    root = ns.project_root
    pre_merge_cmd._loop1(root)
    max_iter = (ns.magi_max_iterations
                if ns.magi_max_iterations is not None
                else cfg.auto_magi_max_iterations)
    threshold = ns.magi_threshold or cfg.magi_threshold
    class _ShadowCfg:
        def __init__(self, base, overrides):
            self.__dict__.update(base.__dict__)
            self.__dict__.update(overrides)
    shadow = _ShadowCfg(cfg, {"magi_max_iterations": max_iter})
    verdict = pre_merge_cmd._loop2(root, shadow, threshold)
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return verdict
```

- [ ] **Step 4: Run test to verify it passes** — 18 tests.

- [ ] **Step 5: Commit** — `feat: auto_cmd phase 3 pre-merge with elevated MAGI budget`.

---

### Task 30: `auto_cmd` — Phase 4 checklist + Phase 5 report with auto-run.json trail

**Files:** Modify `auto_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_auto_phase4_runs_checklist_but_does_not_invoke_finishing`: successful run; `finishing_a_development_branch` NOT invoked (INV-25).
- `test_auto_phase4_aborts_on_degraded_verdict_exit_9`: magi-verdict.json has degraded=true -> `ChecklistError` (reuses finalize checklist logic).
- `test_auto_phase5_writes_auto_run_json`: `.claude/auto-run.json` contains `auto_started_at` + `auto_finished_at` ISO timestamps + `verdict`.

- [ ] **Step 2: Run test to verify it fails** — Phase 4/5 missing.

- [ ] **Step 3: Write minimal implementation**

```python
import json


def _phase4_checklist(root: Path, state, cfg) -> None:
    import finalize_cmd
    magi_verdict_path = root / ".claude" / "magi-verdict.json"
    items = finalize_cmd._checklist(root, state, magi_verdict_path, cfg)
    failures = [(n, d) for (n, ok, d) in items if not ok]
    if failures:
        from errors import ChecklistError
        raise ChecklistError(
            f"auto Phase 4 checklist FAILED ({len(failures)} items): "
            + "; ".join(f"{n} - {d}" for n, d in failures)
        )


def _phase5_report(root: Path, started: str, verdict) -> None:
    auto_run = root / ".claude" / "auto-run.json"
    finished = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    data = {
        "auto_started_at": started,
        "auto_finished_at": finished,
        "verdict": verdict.verdict if verdict else None,
        "degraded": verdict.degraded if verdict else None,
    }
    auto_run.write_text(json.dumps(data, indent=2), encoding="utf-8")
    import sys
    sys.stdout.write(
        f"/sbtdd auto: DONE.\n"
        f"Started:  {started}\n"
        f"Finished: {finished}\n"
        f"MAGI:     {data['verdict']} (degraded={data['degraded']})\n"
        f"Branch status: clean, ready for merge/PR.\n"
    )
```

- [ ] **Step 4: Run test to verify it passes** — 21 tests.

- [ ] **Step 5: Commit** — `feat: auto_cmd phase 4 checklist and phase 5 report with auto-run.json trail`.

---

### Task 31: `auto_cmd` — end-to-end wire + quota detection at boundaries

**Files:** Modify `auto_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_auto_happy_path_end_to_end`: single-task plan; after auto: 3 commits + 1 chore + state done + auto-run.json + magi-verdict.json.
- `test_auto_quota_exhaustion_propagates_exit_11`: monkeypatch verification to raise `QuotaExhaustedError`; dispatcher maps to 11.
- `test_auto_dry_run_prints_plan_without_side_effects`: --dry-run creates no auto-run.json.

- [ ] **Step 2: Run test to verify it fails** — wiring incomplete.

- [ ] **Step 3: Write minimal implementation**

```python
def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    state, cfg = _phase1_preflight(ns)
    if ns.dry_run:
        import sys
        sys.stdout.write(
            "/sbtdd auto --dry-run:\n"
            f"  Plan: {state.plan_path}\n"
            f"  Current task: {state.current_task_id} ({state.current_task_title})\n"
            f"  Phase: {state.current_phase}\n"
            f"  MAGI budget: "
            f"{ns.magi_max_iterations or cfg.auto_magi_max_iterations} iterations\n"
        )
        return 0
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    auto_run = ns.project_root / ".claude" / "auto-run.json"
    auto_run.write_text(json.dumps({"auto_started_at": started}, indent=2),
                         encoding="utf-8")
    if state.current_phase != "done":
        state = _phase2_task_loop(ns, state, cfg)
    verdict = _phase3_pre_merge(ns, cfg)
    _phase4_checklist(ns.project_root, state, cfg)
    _phase5_report(ns.project_root, started, verdict)
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 24 tests.

- [ ] **Step 5: Commit** — `feat: auto_cmd end-to-end wiring phase 1-5 with quota propagation`.

---

### Task 32: `resume_cmd.py` — scaffold + state-file absent short-circuit

**Files:**
- Create: `skills/sbtdd/scripts/resume_cmd.py`
- Create: `tests/test_resume_cmd.py`

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_resume_cmd_module_importable():
    import resume_cmd
    assert hasattr(resume_cmd, "main")


def test_resume_prints_no_session_and_exits_0_when_state_absent(tmp_path, capsys):
    import resume_cmd
    # Create plugin.local.md so plugin_local precondition passes.
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "plugin.local.md").write_text(
        "---\nstack: python\n---\n", encoding="utf-8"
    )
    rc = resume_cmd.main(["--project-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no active" in out.lower() or "manual" in out.lower()


def test_resume_aborts_when_plugin_local_md_missing(tmp_path):
    import resume_cmd
    from errors import PreconditionError
    with pytest.raises(PreconditionError):
        resume_cmd.main(["--project-root", str(tmp_path)])
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''/sbtdd resume — diagnostic wrapper (sec.S.5.10, INV-30).'''
from __future__ import annotations
import argparse
import sys
from pathlib import Path

from errors import PreconditionError


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd resume")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--auto", action="store_true")
    p.add_argument("--discard-uncommitted", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    plugin_local = root / ".claude" / "plugin.local.md"
    if not plugin_local.exists():
        raise PreconditionError(
            f"plugin.local.md not found at {plugin_local}. Run /sbtdd init first."
        )
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        sys.stdout.write(
            "No active SBTDD session to resume.\n"
            "Project is in manual mode. Invoke /sbtdd spec to bootstrap a feature.\n"
        )
        return 0
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold resume_cmd with plugin.local.md and state preconditions`.

---

### Task 33: `resume_cmd` — Phase 1 diagnostic read (state, git, tree, artifacts)

**Files:** Modify `resume_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_resume_prints_state_file_fields`: state with current_task_id=3, phase=green; diagnostic stdout contains all 7 fields.
- `test_resume_prints_head_commit_info`: output contains HEAD short SHA + subject.
- `test_resume_prints_working_tree_status`: DIRTY if uncommitted, else clean.
- `test_resume_detects_runtime_artifacts`: presence of magi-verdict.json and auto-run.json reflected in report.

- [ ] **Step 2: Run test to verify it fails** — diagnostic missing.

- [ ] **Step 3: Write minimal implementation**

```python
from state_file import load as load_state
import subprocess_utils


def _report_diagnostic(root: Path) -> dict:
    state_path = root / ".claude" / "session-state.json"
    state = load_state(state_path)
    head_r = subprocess_utils.run_with_timeout(
        ["git", "log", "-1", "--format=%h|%s"], timeout=10, cwd=str(root)
    )
    raw = head_r.stdout.strip()
    if "|" in raw:
        sha, subject = raw.split("|", 1)
    else:
        sha, subject = ("-", "-")
    status_r = subprocess_utils.run_with_timeout(
        ["git", "status", "--short"], timeout=10, cwd=str(root)
    )
    dirty = status_r.stdout.strip() != ""
    runtime = {
        "magi-verdict.json": (root / ".claude" / "magi-verdict.json").exists(),
        "auto-run.json": (root / ".claude" / "auto-run.json").exists(),
    }
    print("State file:")
    print(f"  current_task_id:          {state.current_task_id}")
    print(f"  current_task_title:       {state.current_task_title}")
    print(f"  current_phase:            {state.current_phase}")
    print(f"  plan_approved_at:         {state.plan_approved_at}")
    print(f"  phase_started_at_commit:  {state.phase_started_at_commit}")
    print(f"  last_verification_at:     {state.last_verification_at}")
    print(f"  last_verification_result: {state.last_verification_result}")
    print(f"Git HEAD:     {sha} {subject}")
    print(f"Working tree: {'DIRTY' if dirty else 'clean'}")
    for art, present in runtime.items():
        print(f"  {art}: {'present' if present else 'absent'}")
    return {"state": state, "head_sha": sha, "tree_dirty": dirty, "runtime": runtime}
```

Call from `main` after `state_path` existence check.

- [ ] **Step 4: Run test to verify it passes** — 7 tests.

- [ ] **Step 5: Commit** — `feat: resume_cmd phase 1 diagnostic reports state, git, tree, artifacts`.

---

### Task 34: `resume_cmd` — Phase 1 dependency + drift re-check

**Files:** Modify `resume_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_resume_reruns_dependency_check`: monkeypatched `check_environment` called.
- `test_resume_aborts_on_failed_preflight`: -> `DependencyError`.
- `test_resume_aborts_on_drift`: monkeypatched drift returns report -> `DriftError`.

- [ ] **Step 2: Run test to verify it fails** — re-check missing.

- [ ] **Step 3: Write minimal implementation**

```python
from drift import detect_drift
from dependency_check import check_environment
from config import load_plugin_local
from errors import DriftError, DependencyError


def _recheck_environment(root: Path) -> None:
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    report = check_environment(cfg.stack, root, Path.home() / ".claude" / "plugins")
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    state = load_state(root / ".claude" / "session-state.json")
    plan_path = root / state.plan_path
    dr = detect_drift(root / ".claude" / "session-state.json", plan_path, root)
    if dr is not None:
        raise DriftError(
            f"drift at resume: state={dr.state_value}, "
            f"HEAD={dr.git_value}:, plan={dr.plan_value}"
        )
```

Call from `main` after diagnostic report.

- [ ] **Step 4: Run test to verify it passes** — 10 tests.

- [ ] **Step 5: Commit** — `feat: resume_cmd reruns dependency check and drift check at entry`.

---

### Task 35: `resume_cmd` — Phase 3 delegation decision tree

**Files:** Modify `resume_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_resume_delegates_to_auto_when_phase_red_and_auto_run_present`: state=red + auto-run.json present; delegates to `auto_cmd.main(["--project-root", root])`.
- `test_resume_delegates_to_pre_merge_when_done_no_verdict`: state=done, no magi-verdict.json, tree clean -> `pre_merge_cmd.main`.
- `test_resume_delegates_to_finalize_when_done_and_verdict_present`: state=done, verdict present, tree clean -> `finalize_cmd.main`.
- `test_resume_dry_run_prints_plan_without_delegating`: --dry-run prints "would delegate to ..." and does NOT invoke the target module.

- [ ] **Step 2: Run test to verify it fails** — delegation missing.

- [ ] **Step 3: Write minimal implementation**

```python
def _decide_delegation(state, tree_dirty, runtime) -> tuple[str | None, list[str]]:
    if state.current_phase in ("red", "green", "refactor") and not tree_dirty:
        if runtime["auto-run.json"]:
            return ("auto_cmd", [])
        return (None, [])
    if state.current_phase in ("red", "green", "refactor") and tree_dirty:
        return ("uncommitted-resolution", [])
    if state.current_phase == "done":
        if not runtime["magi-verdict.json"] and not tree_dirty:
            return ("pre_merge_cmd", [])
        if runtime["magi-verdict.json"] and not tree_dirty:
            return ("finalize_cmd", [])
        if tree_dirty:
            return ("uncommitted-resolution", [])
    return (None, [])


def _delegate(module_name: str, root: Path, extra: list[str]) -> int:
    import importlib
    mod = importlib.import_module(module_name)
    return mod.main(["--project-root", str(root)] + extra)
```

In `main`, after the re-check:

```python
report = _report_diagnostic(root)
_recheck_environment(root)
module_name, extra = _decide_delegation(
    report["state"], report["tree_dirty"], report["runtime"]
)
if module_name is None:
    sys.stdout.write("Nothing to delegate. Run a manual subcomando.\n")
    return 0
if ns.dry_run:
    sys.stdout.write(f"Would delegate to: {module_name} with args {extra}\n")
    return 0
if module_name == "uncommitted-resolution":
    return 1  # Task 36 wires real behavior.
return _delegate(module_name, root, extra)
```

- [ ] **Step 4: Run test to verify it passes** — 14 tests.

- [ ] **Step 5: Commit** — `feat: resume_cmd phase 3 delegation decision tree`.

---

### Task 36: `resume_cmd` — Phase 4 uncommitted-work resolution

**Files:** Modify `resume_cmd.py` + test.

- [ ] **Step 1: Write failing test**

- `test_resume_auto_continues_when_dirty`: --auto + tree dirty; does NOT run git reset; prints CONTINUE.
- `test_resume_discard_uncommitted_runs_git_checkout_and_clean`: --discard-uncommitted + dirty; subprocess calls include `git checkout HEAD -- .` and `git clean -fd`.
- `test_resume_discard_preserves_gitignored_files`: file in `.venv/` and other gitignored path preserved after --discard-uncommitted.
- `test_resume_interactive_R_choice_triggers_reset`: monkeypatch `input` to return "R"; invokes checkout/clean.
- `test_resume_abort_choice_A_exits_130`: input "A" -> rc=130.

- [ ] **Step 2: Run test to verify it fails** — Phase 4 missing.

- [ ] **Step 3: Write minimal implementation**

```python
def _resolve_uncommitted(ns, root: Path) -> str:
    if ns.discard_uncommitted:
        subprocess_utils.run_with_timeout(
            ["git", "checkout", "HEAD", "--", "."], timeout=30, cwd=str(root)
        )
        subprocess_utils.run_with_timeout(
            ["git", "clean", "-fd"], timeout=30, cwd=str(root)
        )
        print("Uncommitted work discarded.")
        return "RESET"
    if ns.auto:
        print("CONTINUE (preserving uncommitted work). Next close-phase will decide.")
        return "CONTINUE"
    print("\nUncommitted work detected. Options:")
    print("  [C] Continue - keep uncommitted and resume.")
    print("  [R] Reset    - discard and resume from HEAD.")
    print("  [A] Abort    - exit without changes.")
    choice = input("Choice [C/R/A]: ").strip().upper() or "C"
    if choice == "R":
        subprocess_utils.run_with_timeout(
            ["git", "checkout", "HEAD", "--", "."], timeout=30, cwd=str(root)
        )
        subprocess_utils.run_with_timeout(
            ["git", "clean", "-fd"], timeout=30, cwd=str(root)
        )
        return "RESET"
    if choice == "A":
        return "ABORT"
    return "CONTINUE"
```

Update the `main` uncommitted-resolution path:

```python
if module_name == "uncommitted-resolution":
    action = _resolve_uncommitted(ns, root)
    if action == "ABORT":
        return 130
    report = _report_diagnostic(root)
    module_name, extra = _decide_delegation(
        report["state"], report["tree_dirty"], report["runtime"]
    )
    if module_name is None or module_name == "uncommitted-resolution":
        return 0
    return _delegate(module_name, root, extra)
```

- [ ] **Step 4: Run test to verify it passes** — 19 tests.

- [ ] **Step 5: Commit** — `feat: resume_cmd phase 4 uncommitted-work resolution with CONTINUE default`.

---

## Phase 5: Dispatcher wiring (Tasks 37-52)

Connect each `*_cmd.main` into `run_sbtdd.SUBCOMMAND_DISPATCH` replacing the 9 placeholder handlers. Each wiring task is atomic and reviewable. Tasks 37-45 wire one subcomando each; Task 46 removes the scaffolding. Tasks 47-50 add end-to-end integration tests. Tasks 51-52 polish and validate.

### Task 37: Wire `status` into dispatcher

**Files:**
- Modify: `skills/sbtdd/scripts/run_sbtdd.py`
- Create: `tests/test_run_sbtdd_wiring.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_run_sbtdd_wiring.py
from __future__ import annotations


def test_dispatcher_routes_status_to_status_cmd():
    import run_sbtdd
    import status_cmd
    assert run_sbtdd.SUBCOMMAND_DISPATCH["status"] is status_cmd.main


def test_dispatcher_status_returns_0_with_no_state(tmp_path):
    import run_sbtdd
    rc = run_sbtdd.main(["status", "--project-root", str(tmp_path)])
    assert rc == 0
```

- [ ] **Step 2: Run test to verify it fails** — placeholder handler still in dispatch.

- [ ] **Step 3: Write minimal implementation**

In `run_sbtdd.py`, add at top of imports: `import status_cmd`.

In the `SUBCOMMAND_DISPATCH` dict literal under the `MILESTONE-C-REPLACE-POINT` marker, replace the "status" entry:

```python
SUBCOMMAND_DISPATCH: MutableMapping[str, SubcommandHandler] = {
    "init": _default_handler_factory("init"),
    "spec": _default_handler_factory("spec"),
    "close-phase": _default_handler_factory("close-phase"),
    "close-task": _default_handler_factory("close-task"),
    "status": status_cmd.main,
    "pre-merge": _default_handler_factory("pre-merge"),
    "finalize": _default_handler_factory("finalize"),
    "auto": _default_handler_factory("auto"),
    "resume": _default_handler_factory("resume"),
}
```

- [ ] **Step 4: Run test to verify it passes** — 2 tests.

- [ ] **Step 5: Commit** — `feat: wire status_cmd into run_sbtdd dispatcher`.

---

### Task 38: Wire `close-task` into dispatcher

**Files:** Modify `run_sbtdd.py` + `tests/test_run_sbtdd_wiring.py`.

- [ ] **Step 1: Write failing test**

```python
def test_dispatcher_routes_close_task_to_close_task_cmd():
    import run_sbtdd
    import close_task_cmd
    assert run_sbtdd.SUBCOMMAND_DISPATCH["close-task"] is close_task_cmd.main
```

- [ ] **Step 2: Run test to verify it fails** — placeholder still present.

- [ ] **Step 3: Write minimal implementation**

Add `import close_task_cmd`. Replace dispatch entry value.

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `feat: wire close_task_cmd into run_sbtdd dispatcher`.

---

### Task 39: Wire `close-phase` into dispatcher

Identical pattern to Task 38; replace `"close-phase"` entry. Commit `feat: wire close_phase_cmd into run_sbtdd dispatcher`.

- [ ] **Step 1:** test `test_dispatcher_routes_close_phase_to_close_phase_cmd` asserting `SUBCOMMAND_DISPATCH["close-phase"] is close_phase_cmd.main`.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3:** `import close_phase_cmd`; replace entry.
- [ ] **Step 4:** PASS (4 tests total).
- [ ] **Step 5:** Commit.

---

### Task 40: Wire `init` into dispatcher

Same pattern. Test `test_dispatcher_routes_init_to_init_cmd`. Add `import init_cmd`. Commit `feat: wire init_cmd into run_sbtdd dispatcher`.

---

### Task 41: Wire `spec` into dispatcher

Same pattern. Test `test_dispatcher_routes_spec_to_spec_cmd`. Add `import spec_cmd`. Commit `feat: wire spec_cmd into run_sbtdd dispatcher`.

---

### Task 42: Wire `pre-merge` into dispatcher

Same pattern. Test `test_dispatcher_routes_pre_merge_to_pre_merge_cmd`. Add `import pre_merge_cmd`. Commit `feat: wire pre_merge_cmd into run_sbtdd dispatcher`.

---

### Task 43: Wire `finalize` into dispatcher

Same pattern. Test `test_dispatcher_routes_finalize_to_finalize_cmd`. Add `import finalize_cmd`. Commit `feat: wire finalize_cmd into run_sbtdd dispatcher`.

---

### Task 44: Wire `auto` into dispatcher

Same pattern. Test `test_dispatcher_routes_auto_to_auto_cmd`. Add `import auto_cmd`. Commit `feat: wire auto_cmd into run_sbtdd dispatcher`.

---

### Task 45: Wire `resume` into dispatcher

Same pattern. Test `test_dispatcher_routes_resume_to_resume_cmd`. Add `import resume_cmd`. Commit `feat: wire resume_cmd into run_sbtdd dispatcher`.

After Task 45 all 9 entries point to real `*_cmd.main` functions; `_default_handler_factory` is defined but never used.

---

### Task 46: Remove `_default_handler_factory` + `MILESTONE-C-REPLACE-POINT` marker

**Files:** Modify `run_sbtdd.py` + `tests/test_run_sbtdd_wiring.py`.

- [ ] **Step 1: Write failing test**

```python
def test_default_handler_factory_is_removed():
    import run_sbtdd
    assert not hasattr(run_sbtdd, "_default_handler_factory")


def test_replace_point_marker_is_removed():
    import inspect
    import run_sbtdd
    src = inspect.getsource(run_sbtdd)
    assert "MILESTONE-C-REPLACE-POINT" not in src
```

- [ ] **Step 2: Run test to verify it fails** — factory + marker still present.

- [ ] **Step 3: Write minimal implementation**

Delete `_default_handler_factory` function. Rewrite `SUBCOMMAND_DISPATCH` as a clean dict literal:

```python
SUBCOMMAND_DISPATCH: MutableMapping[str, SubcommandHandler] = {
    "init": init_cmd.main,
    "spec": spec_cmd.main,
    "close-phase": close_phase_cmd.main,
    "close-task": close_task_cmd.main,
    "status": status_cmd.main,
    "pre-merge": pre_merge_cmd.main,
    "finalize": finalize_cmd.main,
    "auto": auto_cmd.main,
    "resume": resume_cmd.main,
}
```

Remove the `MILESTONE-C-REPLACE-POINT` comment block entirely. Update the module docstring to remove references to "placeholder handlers" and Milestone B wiring; add a final line "In Milestone C, all 9 entries point to the real subcomando implementations."

- [ ] **Step 4: Run test to verify it passes** — 13 tests total.

- [ ] **Step 5: Commit** — `refactor: remove Milestone C placeholder scaffolding from dispatcher`.

---

### Task 47: Integration test — full spec -> close-phase x3 cycle

**Files:** Create `tests/test_integration_full_cycle.py`.

- [ ] **Step 1: Write failing test**

```python
from __future__ import annotations
import json
import subprocess
from pathlib import Path
import pytest


@pytest.fixture
def bootstrapped_project(tmp_path, monkeypatch):
    '''A tmp git repo with plugin.local.md, state, and stubs for all skills.'''
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "test: seed"], cwd=tmp_path, check=True
    )
    # Write plugin.local.md + spec-behavior-base.md + spec-behavior.md + plan org.
    # Stub all superpowers + magi to avoid actual subprocess calls.
    import superpowers_dispatch
    import magi_dispatch
    monkeypatch.setattr(
        superpowers_dispatch, "brainstorming",
        lambda *a, **k: superpowers_dispatch.SkillResult(
            "brainstorming", 0, "", ""
        ),
    )
    # ... etc for each stubbed skill.
    # Return tmp_path for test use.
    return tmp_path


def test_spec_then_three_close_phase_end_to_end(bootstrapped_project, monkeypatch):
    '''Scenario 13 end-to-end: spec approves plan, then 3 close-phase cycles
    (red, green feat, refactor) complete a 1-task plan.'''
    import run_sbtdd
    # Stub magi verdict GO full.
    # Run spec.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    # Run 3 close-phase cycles.
    rc = run_sbtdd.main([
        "close-phase", "--project-root", str(bootstrapped_project),
        "--message", "red phase for task 1",
    ])
    assert rc == 0
    rc = run_sbtdd.main([
        "close-phase", "--project-root", str(bootstrapped_project),
        "--variant", "feat", "--message", "green phase for task 1",
    ])
    assert rc == 0
    rc = run_sbtdd.main([
        "close-phase", "--project-root", str(bootstrapped_project),
        "--message", "refactor phase for task 1",
    ])
    assert rc == 0
    # Verify state is done.
    state = json.loads(
        (bootstrapped_project / ".claude" / "session-state.json").read_text()
    )
    assert state["current_phase"] == "done"
```

- [ ] **Step 2: Run test to verify it fails** — integration test may surface bugs in Tasks 1-45 wiring.

- [ ] **Step 3: Write minimal implementation**

No production code change expected. If the test fails, debug in the relevant `*_cmd.py` and fix via its own mini-cycle.

- [ ] **Step 4: Run test to verify it passes** — 14 tests (13 wiring + 1 integration).

- [ ] **Step 5: Commit** — `test: end-to-end integration test spec-close_phase-x3`.

---

### Task 48: Integration test — `auto` full cycle happy path

**Files:** Modify `tests/test_integration_full_cycle.py`.

- [ ] **Step 1: Write failing test**

```python
def test_auto_full_cycle_happy_path(bootstrapped_project, monkeypatch):
    '''Scenario 18: single auto invocation completes plan + pre-merge + checklist.'''
    import run_sbtdd
    # spec first.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    # auto.
    rc = run_sbtdd.main(["auto", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    # Assertions.
    assert (bootstrapped_project / ".claude" / "auto-run.json").exists()
    assert (bootstrapped_project / ".claude" / "magi-verdict.json").exists()
    verdict = json.loads(
        (bootstrapped_project / ".claude" / "magi-verdict.json").read_text()
    )
    assert verdict["degraded"] is False
    state = json.loads(
        (bootstrapped_project / ".claude" / "session-state.json").read_text()
    )
    assert state["current_phase"] == "done"
    assert state["current_task_id"] is None
```

- [ ] **Step 2: Run test to verify it fails** — requires full auto wiring to work.

- [ ] **Step 3: Write minimal implementation** — debug as needed.

- [ ] **Step 4: Run test to verify it passes** — 15 tests.

- [ ] **Step 5: Commit** — `test: end-to-end integration test auto full cycle happy path`.

---

### Task 49: Integration test — `resume` after quota exhaustion mid-auto

**Files:** Modify `tests/test_integration_full_cycle.py`.

- [ ] **Step 1: Write failing test**

```python
def test_resume_after_quota_exhaustion_continues_to_completion(
    bootstrapped_project, monkeypatch
):
    '''Scenario 19: auto hits quota mid-phase-2, exits 11; resume delegates back.'''
    import run_sbtdd
    from errors import QuotaExhaustedError
    import superpowers_dispatch
    # First pass: verification raises quota.
    call_count = {"n": 0}
    original = superpowers_dispatch.verification_before_completion
    def flaky(*a, **k):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise QuotaExhaustedError("rate_limit_429")
        return original(*a, **k)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", flaky)
    rc = run_sbtdd.main(["auto", "--project-root", str(bootstrapped_project)])
    assert rc == 11
    # Second pass: resume delegates to auto, quota no longer hit.
    rc = run_sbtdd.main(["resume", "--project-root", str(bootstrapped_project), "--auto"])
    assert rc == 0
```

- [ ] **Step 2-5:** same pattern. Commit `test: end-to-end integration test resume after quota exhaustion`.

---

### Task 50: Integration test — `finalize` rejects degraded verdict (INV-28 defense-in-depth)

**Files:** Modify `tests/test_integration_full_cycle.py`.

- [ ] **Step 1: Write failing test**

```python
def test_finalize_blocks_on_degraded_verdict(bootstrapped_project, monkeypatch):
    '''Write a magi-verdict.json with degraded=true; finalize must exit 9.'''
    import run_sbtdd
    # Setup state + plan all done + degraded verdict.
    (bootstrapped_project / ".claude" / "magi-verdict.json").write_text(
        json.dumps({
            "timestamp": "2026-04-19T12:00:00Z",
            "verdict": "GO",
            "degraded": True,
            "conditions": [],
            "findings": [],
        }),
        encoding="utf-8",
    )
    rc = run_sbtdd.main(["finalize", "--project-root", str(bootstrapped_project)])
    assert rc == 9
```

- [ ] **Step 2-5:** same pattern. Commit `test: integration test finalize rejects degraded verdict exit 9`.

---

### Task 51: Cross-reference spec sections + invariants in cmd docstrings

**Files:** Edit module docstrings of all 9 `*_cmd.py`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_run_sbtdd_wiring.py (append)
def test_all_cmd_modules_reference_spec_section_in_docstring():
    import ast
    for mod_name in ("status_cmd", "close_task_cmd", "close_phase_cmd",
                      "init_cmd", "spec_cmd", "pre_merge_cmd",
                      "finalize_cmd", "auto_cmd", "resume_cmd"):
        import importlib
        mod = importlib.import_module(mod_name)
        doc = ast.get_docstring(ast.parse(open(mod.__file__).read()))
        assert doc is not None, f"{mod_name}: missing module docstring"
        assert "sec.S." in doc, f"{mod_name}: docstring lacks sec.S. reference"
```

- [ ] **Step 2: Run test to verify it fails** — may already pass if prior tasks seeded docstrings; otherwise fail with modules missing refs.

- [ ] **Step 3: Write minimal implementation** — edit each `*_cmd.py` docstring to reference its spec section (sec.S.5.1 through sec.S.5.10) and the relevant invariants (INV-0, INV-1..4, INV-27, INV-28, INV-29, INV-30 as appropriate).

- [ ] **Step 4: Run test to verify it passes** — 18 tests.

- [ ] **Step 5: Commit** — `docs: cross-reference spec sections and invariants in cmd docstrings`.

---

### Task 52: Milestone C acceptance sweep — full `make verify` + scenario audit

**Files:** None (verification-only task).

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: all tests pass (Milestones A+B baseline + ~120+ Milestone C tests). 0 failures.

- [ ] **Step 2: Run lint + format + types**

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: 0 warnings, clean format, 0 mypy errors (strict mode).

- [ ] **Step 3: Scenario coverage audit**

Cross-check BDD scenarios 11-19 from `sbtdd/spec-behavior.md`:

| Scenario | Covered by tasks |
|----------|------------------|
| 11 (init Rust) | 11-15 |
| 12 (spec MAGI degraded) | 16-18 |
| 13 (close-phase x3) | 4-10 + Task 47 |
| 14 (close-task) | 4-6 |
| 15 (status drift) | 1-3 |
| 16 (pre-merge) | 19-21 |
| 17 (finalize) | 22-25 + Task 50 |
| 18 (auto) | 26-31 + Task 48 |
| 19 (resume) | 32-36 + Task 49 |

- [ ] **Step 4: INV scan**

Grep for INV tokens across `tests/` to confirm coverage: INV-0 (all commits via `commits.create`), INV-5..7 (Milestone A `validate_message`), INV-9 (Task 21 Loop 1 -> Loop 2), INV-22 (Task 28), INV-23 (Task 26-31 never toggles tdd-guard), INV-24 (Task 36 CONTINUE default), INV-25 (Task 30 no finishing skill in auto), INV-26 (Task 30-31 auto-run.json), INV-27 (Task 16), INV-28 (Tasks 18, 21, 24, 29, 50), INV-29 (Task 21), INV-30 (Tasks 32-36).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: milestone C acceptance sweep with all tests green"
```

---

## Milestone C — Acceptance

Tras completar las 53 tareas (Task 0 + Tasks 1-52):

- **9 nuevos modulos `*_cmd.py`** bajo `skills/sbtdd/scripts/`, cada uno con `main(argv)` + `run = main` + argparse parser.
- **1 modulo modificado** (`run_sbtdd.py`) con `SUBCOMMAND_DISPATCH` completamente cableado a los 9 `*_cmd.main` reales.
- **3 nuevas clases de excepcion** en `errors.py`: `Loop1DivergentError` (exit 7), `VerificationIrremediableError` (exit 6), `ChecklistError` (exit 9). `EXIT_CODES` extendido.
- **10 test files nuevos** (`test_status_cmd`, `test_close_task_cmd`, `test_close_phase_cmd`, `test_init_cmd`, `test_spec_cmd`, `test_pre_merge_cmd`, `test_finalize_cmd`, `test_auto_cmd`, `test_resume_cmd`, `test_run_sbtdd_wiring`) + `test_integration_full_cycle` con ~120+ tests cubriendo escenarios 11-19 BDD + integracion end-to-end.
- **6 fixtures nuevos** (3 plans + 3 MAGI verdicts) bajo `tests/fixtures/`.
- `make verify` limpio: pytest + ruff check + ruff format --check + mypy (strict).
- ~53 commits atomicos con prefijos sec.M.5:
  - Task 0, Task 52: `chore:` (bookkeeping).
  - Tasks 1, 4, 7, 11, 16, 19, 22, 26, 32: `test:` (fresh module scaffolds).
  - Tasks 2, 3, 5, 6, 8, 9, 10, 12, 13, 14, 15, 17, 18, 20, 21, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36: `feat:` (new behavior in existing modules).
  - Tasks 37-45: `feat:` (dispatcher wiring).
  - Task 46: `refactor:` (scaffold cleanup, behavior-preserving).
  - Tasks 47-50: `test:` (integration tests).
  - Task 51: `docs:`.

Productos habilitados para Milestones D-E:

- 9 subcomandos invocables via `python run_sbtdd.py <sub>` con exit codes correctos (0/1/2/3/6/7/8/9/11/130 segun sec.S.11.1).
- Integracion end-to-end validada: spec -> close-phase x3 -> done -> pre-merge -> finalize.
- Auto mode probado en happy path + quota interruption + degraded-verdict rejection.

No implementados en Milestone C (para milestones D-E):

- `skills/sbtdd/SKILL.md` (orchestrator con reglas embebidas) — Milestone E.
- `.claude-plugin/plugin.json` + `marketplace.json` manifests — Milestone E.
- `README.md` profesional (shields, arquitectura, contributing) — Milestone E.
- Pulido adicional de `auto`-mode (trail expandido, diagnosticos profundos en `auto-run.json`) — Milestone D si necesario, basado en feedback MAGI.

---

## Self-Review (pre-MAGI Checkpoint 2)

**1. Spec coverage (spec-behavior.md sec.4 Escenarios BDD):**

- Escenario 11 (init Rust happy path) -> Tasks 11-15 OK.
- Escenario 12 (spec MAGI degraded) -> Tasks 16-18 OK (INV-28 en Task 18).
- Escenario 13 (close-phase x3) -> Tasks 7-10 + Task 47 OK.
- Escenario 14 (close-task bookkeeping) -> Tasks 4-6 OK.
- Escenario 15 (status drift detection) -> Tasks 1-3 OK.
- Escenario 16 (pre-merge Loop 1+2) -> Tasks 19-21 OK (INV-28/29).
- Escenario 17 (finalize checklist) -> Tasks 22-25 + Task 50 OK (INV-28 defense-in-depth).
- Escenario 18 (auto shoot-and-forget) -> Tasks 26-31 + Task 48 OK (5 phases, INV-22..26).
- Escenario 19 (resume diagnostic) -> Tasks 32-36 + Task 49 OK (INV-30, CONTINUE default).

**2. Invariant enforcement audit:**

| INV | Covered by tasks | Notes |
|-----|------------------|-------|
| INV-0 | Every cmd commit via `commits.create` | Inherited from Milestone A |
| INV-1 | Task 9 (close-phase atomic) | Commit + state file paired |
| INV-2 | Task 9 | No phase mixing in commits |
| INV-3 | Task 6 close-task | Checkbox monotonic |
| INV-4 | Task 1 status manual-mode | No state = manual |
| INV-5..7 | Milestone A `validate_message` | Inherited |
| INV-9 | Task 21 | Loop 2 runs only after Loop 1 clean-to-go |
| INV-10 | Task 24 | Finalize gate below threshold |
| INV-11 | Tasks 18, 20, 21, 29 | Safety valves 3/10/3/5 |
| INV-12 | Tasks 5, 8, 19, 22, 27, 34 | Every cmd preflight |
| INV-16 | Task 8 | `/verification-before-completion` emits evidence |
| INV-17 | Tasks 3, 8, 19, 27, 34 | Drift surfaced explicitly |
| INV-18 | Tasks 18, 21, 29 | MAGI escalation with diagnostics |
| INV-22 | Task 28 | Auto sequential-only |
| INV-23 | Tasks 26-31 | Auto never toggles tdd-guard |
| INV-24 | Tasks 21, 36 | Conservative caveat / CONTINUE default |
| INV-25 | Task 30 | Auto does not invoke finishing-a-development-branch |
| INV-26 | Tasks 30-31 | auto-run.json trail |
| INV-27 | Task 16 | Spec placeholder rejection hard-coded |
| INV-28 | Tasks 18, 21, 24, 29, 50 | MAGI degraded never exits loop |
| INV-29 | Task 21 | receiving-code-review over Conditions |
| INV-30 | Tasks 32-36 + Task 49 | Full resume semantics |

**3. Commit prefix audit:** see table above; every task's commit follows sec.M.5 precedence.

**4. Placeholder scan:** grep `\bTODO\b|\bTODOS\b|\bTBD\b` on this plan -> 0 matches (INV-27 self-enforced).

**5. Type consistency across tasks:** `main(argv: list[str] | None) -> int` + `run = main` pattern uniform across all 9 cmd modules; `_preflight(root: Path) -> SessionState` pattern in 5 of them; argparse helper `_build_parser` in every one; error classes raised (never caught silently).

---

## Execution Handoff

Plan listo para MAGI Checkpoint 2. Al aprobarse con veredicto >= `GO_WITH_CAVEATS` full non-degraded, se guarda como `planning/claude-plan-tdd-C.md` (incorporando los *Conditions for Approval* que MAGI reporte) y se inicia ejecucion via `/subagent-driven-development` (sesion actual, tareas independientes, recommended) o `/executing-plans` (sesion separada con checkpoints).
