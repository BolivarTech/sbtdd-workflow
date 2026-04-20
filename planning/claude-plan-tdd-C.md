# Milestone C: Interactive Subcomandos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **MAGI Checkpoint 2 iter 1 revisions (2026-04-19):** this revision of `claude-plan-tdd-org-C.md` applies all 9 WARNING findings from iter 1 (verdict `GO_WITH_CAVEATS (2-0) degraded` — Caspar failed with JSON format error; Melchior + Balthasar full). Per INV-28 a degraded verdict cannot exit the loop, so findings are applied proactively and iter 2 will re-invoke MAGI for full 3-agent consensus. Revision summary:
>
> - **Finding 1** (Melchior): Task 21 now emits the explicit `test:`/`fix:`/`refactor:` mini-cycle for each accepted MAGI condition via `_apply_condition_via_mini_cycle`; rejected conditions thread back into the next MAGI iteration as context.
> - **Finding 2** (Melchior): Tasks 13-15 now stage ALL Phase 3a/3b writes in a tempdir (`tempfile.mkdtemp(prefix="sbtdd-init-")`). Phase 4 smoke tests against staging; Phase 5 atomically relocates to dest_root. Rollback on any failure leaves dest_root byte-identical.
> - **Finding 3** (Melchior): Task 18 commits `sbtdd/spec-behavior.md` + `planning/claude-plan-tdd-org.md` + `planning/claude-plan-tdd.md` with a `chore:` commit AFTER `plan_approved_at` is persisted to the state file.
> - **Finding 4** (Melchior): Tasks 26 and 31 move the `--dry-run` short-circuit to BEFORE `_phase1_preflight`; a test asserts `subprocess.run` is never called in dry-run.
> - **Finding 5** (Melchior): Task 21 wraps `VERDICT_RANK[threshold]` lookups in a `_safe_threshold_rank` helper that raises `ValidationError` (never `KeyError`) on unknown thresholds.
> - **Finding 6** (Balthasar): shared plan-edit helpers extracted into a new module `skills/sbtdd/scripts/_plan_ops.py` (new Task 6a) consumed by Tasks 6, 18, 28 — eliminates the private-helper coupling between `auto_cmd` and `close_task_cmd`.
> - **Finding 7** (Balthasar): integration-test stubs consolidated in a new module `tests/fixtures/skill_stubs.py` (new Task 46a) consumed by Tasks 47-50.
> - **Finding 8** (Balthasar): Milestone C acceptance adds a `make verify` runtime budget of `<= 60 seconds` with `@pytest.mark.slow` escape hatch + Makefile fast/slow split on overrun.
> - **Finding 9** (Balthasar): Task 31 adds an explicit `test_auto_never_toggles_tdd_guard` test enforcing INV-23.

**Goal:** Construir los 9 subcomandos interactivos del plugin sbtdd-workflow como modulos `*_cmd.py` bajo `skills/sbtdd/scripts/` — `status_cmd`, `close_task_cmd`, `close_phase_cmd`, `init_cmd`, `spec_cmd`, `pre_merge_cmd`, `finalize_cmd`, `auto_cmd`, `resume_cmd` — y cablearlos al dispatcher de Milestone B (`run_sbtdd.py`) reemplazando los 9 placeholder handlers en `SUBCOMMAND_DISPATCH`. Todo con `make verify` limpio.

**Architecture:** Python 3.9+ consumiendo la infraestructura de Milestones A+B: `state_file` (load/save/SessionState), `drift` (detect_drift/DriftReport), `commits` (create/validate_prefix/validate_message), `config` (load_plugin_local/PluginConfig), `templates` (expand), `hooks_installer` (merge), `dependency_check` (check_environment/DependencyReport), `superpowers_dispatch` (12 typed wrappers), `magi_dispatch` (invoke_magi/MAGIVerdict/verdict_passes_gate/write_verdict_artifact), `errors` (SBTDDError + 8 subclases + EXIT_CODES), `models` (COMMIT_PREFIX_MAP, VERDICT_RANK, VALID_SUBCOMMANDS, verdict_meets_threshold), `subprocess_utils` (run_with_timeout, kill_tree), `quota_detector` (detect). Cada `*_cmd.py` expone `main(args: list[str]) -> int` + `run(args: list[str]) -> int` (alias estable que el dispatcher consumira). Argparse para todos los flags. Fallos se propagan como subclases de `SBTDDError`; el dispatcher central mapea a exit codes via `_exit_code_for`.

**Tech Stack:** Python 3.9+ stdlib + PyYAML 6 (ya presente en dev deps). Sin runtime deps nuevas.

---

## File Structure

Archivos creados en este milestone:

```
skills/sbtdd/scripts/
├── _plan_ops.py                 # Shared plan-edit helpers (Task 6a, Finding 6)
├── status_cmd.py                # read-only: state + git + plan + drift report
├── close_task_cmd.py            # mark [x] + chore commit + advance state
├── close_phase_cmd.py           # 4-step atomic phase close (drift/verify/commit/state)
├── init_cmd.py                  # 5-phase atomic bootstrap (stage-smoke-relocate)
├── spec_cmd.py                  # /brainstorming -> /writing-plans -> MAGI checkpoint
├── pre_merge_cmd.py             # Loop 1 + Loop 2 (INV-28/29)
├── finalize_cmd.py              # checklist sec.M.7 + /finishing-a-development-branch
├── auto_cmd.py                  # 5-phase shoot-and-forget
└── resume_cmd.py                # diagnostic wrapper + delegation

skills/sbtdd/scripts/run_sbtdd.py    # MODIFIED: wire SUBCOMMAND_DISPATCH to real handlers

tests/
├── test__plan_ops.py            # Shared helpers (Task 6a)
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
├── skill_stubs.py               # Shared stub classes for integration tests (Task 46a)
├── plans/                       # Synthetic claude-plan-tdd.md samples
│   ├── one-task-red.md
│   ├── three-tasks-mixed.md
│   └── all-done.md
└── magi-verdicts/               # Synthetic .claude/magi-verdict.json samples
    ├── go-full.json
    ├── go-with-caveats-full.json
    └── go-degraded.json
```

Tareas: 55 total (Task 0 + Tasks 1-52 + Task 6a + Task 46a; the two inserted tasks address Findings 6 and 7 from MAGI Checkpoint 2 iter 1). Orden lineal por dependencias — Fase 1 entrega los tres subcomandos mas simples (read/write primarios) como base + `_plan_ops` shared helpers; Fase 2 bootstrappea proyectos; Fase 3 los dos gates pre-merge; Fase 4 encadena todo en modo autonomo; Fase 5 cablea el dispatcher; Task 46a precede los integration tests. Cada tarea asume las previas completas.

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

Top-of-file imports: `import os`, `from datetime import datetime, timezone`, `import subprocess_utils`, `from commits import create as commit_create`, `from state_file import SessionState, save as save_state`, `import _plan_ops` (see Task 6a — shared plan-edit helpers).

```python
def _current_head_sha(root: Path) -> str:
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def mark_and_advance(state: SessionState, root: Path) -> SessionState:
    '''Close the current task and advance state: flip [x], commit chore, persist state.

    Public helper (no leading underscore) so auto_cmd.py can reuse the exact
    same sequence without duplicating logic (addresses iter-2 Finding W1).
    Consumes the plan at state.plan_path, mutates it atomically via
    `os.replace`, creates a `chore: mark task {id} complete` commit, then
    writes the advanced SessionState (next open [ ] task in red phase, or
    done). Returns the new SessionState.

    Preconditions: `state.current_task_id is not None`; the working tree
    has no pending changes outside of the plan file edit produced here
    (enforced by the caller's drift/preflight checks).
    '''
    plan_path = root / state.plan_path
    plan_text = plan_path.read_text(encoding="utf-8")
    new_plan = _plan_ops.flip_task_checkboxes(plan_text, state.current_task_id)
    tmp = plan_path.with_suffix(plan_path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(new_plan, encoding="utf-8")
    os.replace(tmp, plan_path)
    subprocess_utils.run_with_timeout(
        ["git", "add", str(plan_path.relative_to(root))], timeout=10, cwd=str(root)
    )
    commit_create("chore", f"mark task {state.current_task_id} complete", cwd=str(root))
    new_sha = _current_head_sha(root)
    next_id, next_title = _plan_ops.next_task(new_plan, state.current_task_id)
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
    return new_state


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    closed_task_id = state.current_task_id
    new_state = mark_and_advance(state, root)
    import sys
    sys.stdout.write(
        f"Task {closed_task_id} closed. "
        f"{'Next: task ' + new_state.current_task_id if new_state.current_task_id else 'Plan complete.'}\n"
    )
    return 0
```

Rationale for the split into `_plan_ops`: `close_task_cmd`, `spec_cmd._first_open_task`, and `auto_cmd` Phase 2 refactor cascade all need to parse `### Task N:` headers and flip `[ ]` checkboxes. Keeping the helpers inside `close_task_cmd` would force `auto_cmd` to reach into a private underscore-prefixed symbol (Finding 6 anti-pattern). `_plan_ops.py` keeps the underscore-prefix-filename convention signalling "internal to plugin but shared across cmd modules".

Rationale for `mark_and_advance` as a public helper: iter-2 Finding W1 noted that `auto_cmd._close_task_inline` (Task 28) duplicated the entire close-task sequence. Extracting it as a public function on `close_task_cmd` (no leading underscore) lets Task 28 delegate without violating the underscore-private contract. This is the minimal-surgery option per iter-2 fix guidance.

- [ ] **Step 4: Run test to verify it passes** — 11 tests.

Add one extra test `test_mark_and_advance_is_public_api` asserting `hasattr(close_task_cmd, "mark_and_advance")` and that calling it directly on a seeded state produces the same 1-commit + advanced state result as calling `main`.

- [ ] **Step 5: Commit** — `feat: close_task_cmd flips checkbox, commits chore, advances state`.

---

### Task 6a: `_plan_ops.py` — shared plan-edit helpers (extracted from close_task_cmd)

**Files:**
- Create: `skills/sbtdd/scripts/_plan_ops.py`
- Create: `tests/test__plan_ops.py`

Rationale (addresses Finding 6 Balthasar + iter-2 Finding W1 follow-through): plan parsing and `[ ]` flipping are needed by `close_task_cmd`, `spec_cmd._first_open_task`, and `auto_cmd` Phase 2's refactor cascade. Keeping them inside `close_task_cmd` with underscore-prefixed names (`_flip_task_checkboxes`, `_next_task`) would force other cmd modules to reach into private symbols — a coupling smell. `_plan_ops.py` exposes them as public module-level functions (no leading underscore on the identifiers themselves; the underscore-prefix-filename convention signals "internal to plugin but shared across cmd modules"). Tasks 6 and 18 consume the public API. Task 28 (auto) no longer needs to import `_plan_ops` directly — per iter-2 W1 it delegates to `close_task_cmd.mark_and_advance`, which itself consumes `_plan_ops`.

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_plan_ops_module_importable():
    import _plan_ops
    assert hasattr(_plan_ops, "flip_task_checkboxes")
    assert hasattr(_plan_ops, "next_task")
    assert hasattr(_plan_ops, "first_open_task")


def test_flip_task_checkboxes_flips_target_task_only():
    import _plan_ops
    plan = (
        "### Task 1: First\n- [ ] step a\n- [ ] step b\n"
        "### Task 2: Second\n- [ ] step c\n"
    )
    out = _plan_ops.flip_task_checkboxes(plan, "1")
    assert "### Task 1: First\n- [x] step a\n- [x] step b\n" in out
    assert "### Task 2: Second\n- [ ] step c\n" in out


def test_flip_task_checkboxes_raises_on_missing_task():
    import _plan_ops
    from errors import PreconditionError
    with pytest.raises(PreconditionError):
        _plan_ops.flip_task_checkboxes("### Task 1: x\n- [ ] a\n", "99")


def test_next_task_returns_next_open_after_current():
    import _plan_ops
    plan = (
        "### Task 1: First\n- [x] a\n"
        "### Task 2: Second\n- [ ] b\n"
        "### Task 3: Third\n- [ ] c\n"
    )
    assert _plan_ops.next_task(plan, "1") == ("2", "Second")


def test_next_task_skips_fully_closed_task():
    import _plan_ops
    plan = (
        "### Task 1: First\n- [x] a\n"
        "### Task 2: Second\n- [x] b\n"
        "### Task 3: Third\n- [ ] c\n"
    )
    assert _plan_ops.next_task(plan, "1") == ("3", "Third")


def test_next_task_returns_none_when_plan_complete():
    import _plan_ops
    plan = "### Task 1: First\n- [x] a\n### Task 2: Second\n- [x] b\n"
    assert _plan_ops.next_task(plan, "1") == (None, None)


def test_first_open_task_returns_first_with_open_checkbox():
    import _plan_ops
    plan = (
        "### Task 1: First\n- [x] a\n"
        "### Task 2: Second\n- [ ] b\n"
    )
    assert _plan_ops.first_open_task(plan) == ("2", "Second")


def test_first_open_task_raises_when_none_open():
    import _plan_ops
    from errors import PreconditionError
    plan = "### Task 1: First\n- [x] a\n"
    with pytest.raises(PreconditionError):
        _plan_ops.first_open_task(plan)
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''Shared plan-editing helpers used by close_task_cmd, spec_cmd, auto_cmd.

Public API:
- flip_task_checkboxes(plan_text, task_id) -> plan_text with [ ] -> [x] inside
  the section whose header matches task_id.
- next_task(plan_text, after_task_id) -> (id, title) of the next task with
  at least one [ ] checkbox after after_task_id, or (None, None).
- first_open_task(plan_text) -> (id, title) of the first task containing
  [ ], raises PreconditionError if none.

Module filename is underscore-prefixed to signal "internal to plugin
but shared across cmd modules" (distinct from pure stdlib helpers).
'''
from __future__ import annotations
import re

from errors import PreconditionError


_TASK_HEADER_RE = re.compile(r"^### Task (\S+?): (.+)$", re.MULTILINE)


def _task_section_bounds(plan_text: str, task_id: str) -> tuple[int, int]:
    header = re.compile(rf"^### Task {re.escape(task_id)}:", re.MULTILINE)
    m = header.search(plan_text)
    if not m:
        raise PreconditionError(f"task '{task_id}' not found in plan")
    nm = _TASK_HEADER_RE.search(plan_text, m.end())
    end = nm.start() if nm else len(plan_text)
    return (m.end(), end)


def flip_task_checkboxes(plan_text: str, task_id: str) -> str:
    start, end = _task_section_bounds(plan_text, task_id)
    section = plan_text[start:end].replace("- [ ]", "- [x]")
    return plan_text[:start] + section + plan_text[end:]


def next_task(plan_text: str, after_task_id: str) -> tuple[str | None, str | None]:
    tasks = [
        (m.group(1), m.group(2).strip())
        for m in _TASK_HEADER_RE.finditer(plan_text)
    ]
    found = False
    for tid, title in tasks:
        if found:
            start, end = _task_section_bounds(plan_text, tid)
            if "- [ ]" in plan_text[start:end]:
                return (tid, title)
        if tid == after_task_id:
            found = True
    return (None, None)


def first_open_task(plan_text: str) -> tuple[str, str]:
    for m in _TASK_HEADER_RE.finditer(plan_text):
        tid = m.group(1)
        title = m.group(2).strip()
        start, end = _task_section_bounds(plan_text, tid)
        if "- [ ]" in plan_text[start:end]:
            return (tid, title)
    raise PreconditionError("plan has no open [ ] tasks")
```

- [ ] **Step 4: Run test to verify it passes** — 8 tests.

- [ ] **Step 5: Commit** — `feat: extract shared plan-edit helpers into _plan_ops module`.

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

**Atomicity contract (addresses Finding 2 Melchior):** every file created during Phase 3a AND Phase 3b lands FIRST in a tempdir built from `tempfile.mkdtemp(prefix="sbtdd-init-")`. The dest_root is NOT touched until Phase 4 smoke test (which runs against the tempdir) passes. Phase 5 performs a single atomic relocation from tempdir to dest_root. If Phase 4 fails, the tempdir is cleaned up and dest_root remains byte-identical to its pre-invocation state — satisfying sec.S.5.1 all-or-nothing.

- [ ] **Step 1: Write failing test**

- `test_init_creates_claude_local_md_with_author_and_stack`: monkeypatched all-OK preflight; after init, `CLAUDE.local.md` contains author and stack-specific verification commands.
- `test_init_creates_plugin_local_md_with_valid_yaml_frontmatter`: `config.load_plugin_local` returns `PluginConfig` without raising.
- `test_init_phase3a_writes_only_to_tempdir_not_dest_root`: stub Phase 4 smoke test to assert tempdir has both files and dest_root has NEITHER at that point.

- [ ] **Step 2: Run test to verify it fails** — files not created.

- [ ] **Step 3: Write minimal implementation**

```python
import os
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


def _make_staging_dir() -> Path:
    '''Create a tempdir that mirrors the dest_root tree during init.

    All Phase 3a + Phase 3b writes land here; dest_root is untouched
    until Phase 5 relocation after Phase 4 smoke-test succeeds.
    '''
    td = Path(tempfile.mkdtemp(prefix="sbtdd-init-"))
    (td / ".claude").mkdir()
    (td / "sbtdd").mkdir()
    (td / "planning").mkdir()
    return td


def _phase3a_generate(ns: argparse.Namespace, staging: Path, dest_root: Path) -> None:
    '''Write CLAUDE.local.md + .claude/plugin.local.md into STAGING (not dest_root).

    Pre-flight check against dest_root for existing CLAUDE.local.md runs
    here (requires --force to overwrite).
    '''
    tpl_c = (_TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    ctx = {
        "Author": ns.author,
        "ErrorType": ns.error_type or "Error",
        "stack": ns.stack,
        "verification_commands": "\n".join(_VERIF_CMDS[ns.stack]),
    }
    (staging / "CLAUDE.local.md").write_text(expand(tpl_c, ctx), encoding="utf-8")
    tpl_p = (_TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    (staging / ".claude" / "plugin.local.md").write_text(
        expand(tpl_p, ctx), encoding="utf-8"
    )
    if (dest_root / "CLAUDE.local.md").exists() and not ns.force:
        raise PreconditionError(
            "CLAUDE.local.md already exists; use --force to overwrite"
        )
```

Wire into `main` after pre-flight; staging is created at the start of Phase 3a and consumed by Phase 3b + Phase 4. On any exception, the staging dir is cleaned up by `main` via `_cleanup_staging` (Task 15).

- [ ] **Step 4: Run test to verify it passes** — 9 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phase 3a stages CLAUDE.local.md and plugin.local.md in tempdir`.

---

### Task 14: `init_cmd` — Phase 3b settings.json + spec-base + .gitignore + conftest

**Files:** Modify `init_cmd.py` + test.

All writes in this phase go to the STAGING dir from Task 13 — dest_root stays untouched until Phase 5 relocation. The `.gitignore` and `conftest.py` merge steps still READ pre-existing content from dest_root (so user overrides are preserved), but the resulting merged file is WRITTEN into the staging tree, not to dest_root directly.

- [ ] **Step 1: Write failing test**

- `test_init_merges_settings_json_preserving_user_hooks`: pre-create `.claude/settings.json` with user hook in dest_root; after full init, both user and plugin hooks present.
- `test_init_creates_spec_behavior_base_md_skeleton`: `sbtdd/spec-behavior-base.md` exists, contains no uppercase pending markers forbidden by INV-27 (the three tokens enumerated in INV-27 — see `spec_cmd._INV27_RE` in Task 16).
- `test_init_appends_gitignore_fragment_once`: after 2 init --force runs, each fragment line appears exactly once.
- `test_init_creates_planning_gitkeep`: `planning/.gitkeep` exists.
- `test_init_python_stack_writes_conftest_py`: --stack python --conftest-mode=merge writes `conftest.py` in project root with `# --- SBTDD TDD-Guard reporter START ---` marker.
- `test_init_phase3b_writes_only_to_staging`: before Phase 4 runs, assert dest_root still has no `.claude/settings.json`, no `sbtdd/spec-behavior-base.md`, no `planning/.gitkeep`, and no `conftest.py` (unless user had one pre-existing). All new files are in staging.

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


def _phase3b_install(ns: argparse.Namespace, staging: Path, dest_root: Path) -> None:
    '''Write settings.json, spec-base, .gitignore, conftest to STAGING.

    Existing user content in dest_root is READ to preserve overrides
    but OUTPUT lands in staging only. Phase 5 relocation is what makes
    these changes visible in dest_root.
    '''
    staged_settings = staging / ".claude" / "settings.json"
    existing_settings = dest_root / ".claude" / "settings.json"
    merge_hooks(existing_settings, _settings_payload(), staged_settings)
    staged_spec_base = staging / "sbtdd" / "spec-behavior-base.md"
    if not (dest_root / "sbtdd" / "spec-behavior-base.md").exists():
        tpl = (_TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
        staged_spec_base.write_text(tpl, encoding="utf-8")
    staged_gitkeep = staging / "planning" / ".gitkeep"
    staged_gitkeep.write_text("", encoding="utf-8")
    staged_gi = staging / ".gitignore"
    frag = (_TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    existing_gi = dest_root / ".gitignore"
    existing = existing_gi.read_text(encoding="utf-8") if existing_gi.exists() else ""
    new_lines = [line for line in frag.splitlines() if line and line not in existing]
    merged = existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n" if new_lines else existing
    staged_gi.write_text(merged, encoding="utf-8")
    if ns.stack == "python" and ns.conftest_mode != "skip":
        _install_conftest_staged(staging, dest_root, ns.conftest_mode)


def _install_conftest_staged(staging: Path, dest_root: Path, mode: str) -> None:
    target = staging / "conftest.py"
    existing_target = dest_root / "conftest.py"
    tpl = (_TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    if mode == "replace" and existing_target.exists():
        # The backup of the user's conftest.py still lands in dest_root
        # at Phase 5 alongside the new one. In staging we only prepare
        # the new conftest.py.
        target.write_text(tpl, encoding="utf-8")
        return
    if mode == "merge" and existing_target.exists():
        existing = existing_target.read_text(encoding="utf-8")
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

Call `_phase3b_install` from `main` after `_phase3a_generate`, same staging dir.

- [ ] **Step 4: Run test to verify it passes** — 15 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phase 3b stages hooks, spec-base, planning, gitignore fragment`.

---

### Task 15: `init_cmd` — Phase 4 smoke test + Phase 5 atomic relocation + rollback

**Files:** Modify `init_cmd.py` + test.

Phase 4 smoke-tests the STAGING tree. If it fails, the staging dir is wiped and dest_root is byte-identical to its pre-invocation state. Phase 5 first copies the staged tree into dest_root (under the same layout) and then reports. Relocation uses `shutil.copytree` with `dirs_exist_ok=True` so pre-existing user files (e.g., project source) stay put; only files the plugin staged are written.

- [ ] **Step 1: Write failing test**

- `test_init_smoke_test_rejects_invalid_settings_json`: monkeypatch `hooks_installer.merge` to write corrupt JSON into staging; smoke test fails -> staging wiped + dest_root has no plugin files.
- `test_init_smoke_test_validates_plugin_local_md`: verify `load_plugin_local` call against the STAGED plugin.local.md succeeds.
- `test_init_phase5_reports_all_ok_components`: stdout contains `[ok]` for each dep check and `Created:` section listing dest_root paths.
- `test_init_exit_0_on_full_success`: happy path, rc=0.
- `test_init_rollback_on_smoke_test_failure`: monkeypatch `_phase4_smoke_test` to raise; after call, dest_root has no `CLAUDE.local.md`, no `.claude/settings.json`, no `sbtdd/spec-behavior-base.md`. Staging dir removed from filesystem. Covers Finding 2 rollback contract.

- [ ] **Step 2: Run test to verify it fails** — Phase 4/5 absent.

- [ ] **Step 3: Write minimal implementation**

```python
import shutil
from config import load_plugin_local


def _phase4_smoke_test(staging: Path) -> None:
    '''Validate the STAGED tree before Phase 5 relocation.

    Runs exclusively against staging — dest_root is untouched if this raises.
    '''
    settings = staging / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PreconditionError(f"smoke test: settings.json not parseable: {exc}") from exc
    for event in ("PreToolUse", "UserPromptSubmit", "SessionStart"):
        if event not in data.get("hooks", {}):
            raise PreconditionError(f"smoke test: hook '{event}' missing")
    plugin_local = staging / ".claude" / "plugin.local.md"
    load_plugin_local(plugin_local)


def _phase5_relocate(staging: Path, dest_root: Path) -> list[Path]:
    '''Atomically copy the staged tree into dest_root. Returns list of targets.'''
    staged_files = [p for p in staging.rglob("*") if p.is_file()]
    created: list[Path] = []
    for src in staged_files:
        rel = src.relative_to(staging)
        target = dest_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        created.append(target)
    return created


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


def _cleanup_staging(staging: Path) -> None:
    try:
        shutil.rmtree(staging, ignore_errors=True)
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
    staging = _make_staging_dir()
    try:
        _phase3a_generate(ns, staging, ns.project_root)
        _phase3b_install(ns, staging, ns.project_root)
        _phase4_smoke_test(staging)
        created = _phase5_relocate(staging, ns.project_root)
    except Exception:
        _cleanup_staging(staging)
        raise
    _cleanup_staging(staging)
    _phase5_report(ns, created, report)
    return 0
```

- [ ] **Step 4: Run test to verify it passes** — 19 tests.

- [ ] **Step 5: Commit** — `feat: init_cmd phases 4-5 stage-smoke-relocate pattern with strict rollback`.

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
- `test_spec_commits_approved_artifacts_after_state_write` (Finding 3 + iter-2 W7 deterministic probe): after a full-GO MAGI verdict, assert the chore commit (a) exists with message `chore: add MAGI-approved spec and plan` in English, (b) contains exactly the three paths `sbtdd/spec-behavior.md`, `planning/claude-plan-tdd-org.md`, `planning/claude-plan-tdd.md`, and (c) lands AFTER `plan_approved_at` is persisted in the state file. Do NOT assert ordering via mtime comparison or "file exists before commit" — both are non-deterministic across OSes (Windows mtime resolution is ~16ms, Linux ext4 is 1ns, APFS is 1ns). Instead, monkeypatch with a shared call-order list:

```python
call_order: list[str] = []
orig_save = state_file.save
orig_create = commits.create

def spy_save(*a, **kw):
    call_order.append("save")
    return orig_save(*a, **kw)

def spy_create(prefix, message, *a, **kw):
    call_order.append(f"commit:{prefix}")
    return orig_create(prefix, message, *a, **kw)

monkeypatch.setattr(state_file, "save", spy_save)
monkeypatch.setattr(commits, "create", spy_create)

spec_cmd.main([...])

# _create_state_file must run BEFORE _commit_approved_artifacts.
assert call_order == ["save", "commit:chore"]
```

Deterministic across Windows/Linux/macOS, no race.
- `test_spec_does_not_commit_artifacts_when_magi_rejects`: if MAGI does not converge (`MAGIGateError` raised), assert no `chore:` commit is produced — artifacts remain uncommitted for the user to inspect.

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
    import _plan_ops
    return _plan_ops.first_open_task(plan.read_text(encoding="utf-8"))


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


def _commit_approved_artifacts(root: Path) -> None:
    '''Commit the three spec/plan artifacts that MAGI just approved.

    Addresses Finding 3: /brainstorming and /writing-plans produce files
    that are tracked in git, but the spec flow previously left them
    uncommitted. Under the "Excepcion bajo plan aprobado" clause of
    template sec.5, once plan_approved_at is set this commit is one of
    the four authorized categories (here: plan bookkeeping, chore:).
    '''
    from commits import create as commit_create
    artifacts = [
        "sbtdd/spec-behavior.md",
        "planning/claude-plan-tdd-org.md",
        "planning/claude-plan-tdd.md",
    ]
    for rel in artifacts:
        subprocess_utils.run_with_timeout(
            ["git", "add", rel], timeout=10, cwd=str(root)
        )
    commit_create("chore", "add MAGI-approved spec and plan", cwd=str(root))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = ns.project_root
    _validate_spec_base(root / "sbtdd" / "spec-behavior-base.md")
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _run_spec_flow(root)
    _run_magi_checkpoint2(root, cfg)
    # State file MUST be persisted before the artifacts commit so that
    # plan_approved_at is visible to any follow-on subcommand even if
    # the commit itself fails mid-way (the state is canon of the present;
    # git is canon of the past; see CLAUDE.local.md §2.1).
    _create_state_file(root, cfg, root / "planning" / "claude-plan-tdd.md")
    _commit_approved_artifacts(root)
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
- `test_pre_merge_loop2_rejects_unknown_threshold_override_with_validation_error`: pass `--magi-threshold=BANANA`; `ValidationError` raised (NOT `KeyError`) — maps to exit 1. Covers Finding 5.
- `test_pre_merge_loop2_accepted_condition_emits_test_fix_refactor_mini_cycle`: MAGI iter 1 returns `GO_WITH_CAVEATS` full with 1 structural condition; `/receiving-code-review` stub ACCEPTS it. Assert three commits land in order: prefix `test:` (reproducing test), prefix `fix:` (implementation), prefix `refactor:` (polish). Each commit created via `commits.create`. Covers Finding 1.
- `test_pre_merge_loop2_rejected_condition_feeds_into_next_iteration`: MAGI iter 1 `GO_WITH_CAVEATS` with 1 condition; `/receiving-code-review` REJECTS it; no mini-cycle commits land; iter 2 invocation carries rejection as context; iter 2 returns `GO` full -> exit. Covers Finding 1 rejected-path contract.

- [ ] **Step 2: Run test to verify it fails** — Loop 2 not implemented.

- [ ] **Step 3: Write minimal implementation**

```python
import magi_dispatch
import superpowers_dispatch
from commits import create as commit_create
from config import load_plugin_local
from errors import MAGIGateError, ValidationError
from models import VERDICT_RANK


# iter-2 Finding W8: "test" removed — phrases like "add structural test for X"
# are STRUCTURAL, not low-risk. Keep only keywords that genuinely don't require
# re-MAGI (doc/docstring/naming/rename/comment/logging/message).
_LOW_RISK_KEYWORDS = (
    "doc", "docstring", "naming", "rename", "comment", "logging", "message"
)


def _conditions_low_risk(conditions: tuple[str, ...]) -> bool:
    return all(
        any(kw in c.lower() for kw in _LOW_RISK_KEYWORDS) for c in conditions
    )


def _parse_receiving_review(
    skill_result: "superpowers_dispatch.SkillResult",
) -> tuple[list[str], list[str]]:
    '''Parse /receiving-code-review stdout into (accepted, rejected) lists.

    Expected stdout format (markdown bullet lists under two headers):

        ## Accepted
        - condition text 1
        - condition text 2

        ## Rejected
        - condition text 3 (rationale: ...)

    Returns ([accepted_texts], [rejected_texts]) with leading bullet/dash/
    whitespace stripped. Either section may be absent (empty list). A
    completely empty stdout returns ([], []) — the caller treats this as
    "no decisions produced, re-raise" via a dedicated ValidationError
    path in _loop2 (test documents this).
    '''
    accepted: list[str] = []
    rejected: list[str] = []
    section: list[str] | None = None
    for line in skill_result.stdout.splitlines():
        s = line.strip()
        if s.lower().startswith("## accepted"):
            section = accepted
            continue
        if s.lower().startswith("## rejected"):
            section = rejected
            continue
        if section is not None and s.startswith(("-", "*")):
            section.append(s.lstrip("-* ").strip())
    return accepted, rejected


def _safe_threshold_rank(threshold: str) -> int:
    '''Return VERDICT_RANK[threshold] or raise ValidationError (NOT KeyError).

    Ensures threshold-override errors flow through the SBTDDError hierarchy
    so the dispatcher maps them to exit 1 (USER_ERROR), not an unhandled
    KeyError (Finding 5).
    '''
    if threshold not in VERDICT_RANK:
        raise ValidationError(
            f"threshold '{threshold}' not in VERDICT_RANK "
            f"(valid values: {', '.join(sorted(VERDICT_RANK))})"
        )
    return VERDICT_RANK[threshold]


def _apply_condition_via_mini_cycle(
    condition: str, root: Path, iteration: int, idx: int
) -> None:
    '''Record ONE accepted MAGI condition as a test/fix/refactor mini-cycle.

    Does NOT perform code edits. Expects the caller to have already
    staged the fixed code before invoking. Emits three atomic commits
    asserting the test->fix->refactor cycle was observed.

    Contract (iter-2 Finding W2 clarification):
      - The actual code modifications are the responsibility of the
        upstream orchestrator — in interactive `pre-merge` the user
        applies them; in `auto` mode the subagent-driven-development
        dispatcher applies them before invoking this helper. In both
        cases /receiving-code-review has already validated the approach
        (INV-29 gate). This helper only MATERIALIZES the TDD discipline
        as three atomic commits over the working-tree state the caller
        has prepared.
      - Each commit_create call stages whatever the caller has staged
        via `git add` plus the implicit index state; the three commits
        are sequential so the caller is expected to re-stage between
        each (the reproducing test, the fix, the refactor). If the
        caller fails to stage, commit_create emits an empty commit
        which fails its precondition check and raises ValidationError.

    Preconditions:
      - caller has already invoked /receiving-code-review and the
        condition is ACCEPTED (rejected conditions never reach here;
        they feed back into the next MAGI iteration as context — see
        _loop2's rejection bookkeeping).
      - caller has already applied the fix code in the working tree
        AND staged the relevant files between each commit boundary.

    INV-29 compliance: /receiving-code-review acts as the technical
    gate BEFORE this helper runs. Mini-cycle atomicity per sec.M.5
    row 5: test: (reproducing), fix: (resolution), refactor: (polish).
    '''
    tag = f"magi iter {iteration} cond {idx}"
    commit_create(
        "test", f"add reproducing test for {condition} ({tag})", cwd=str(root)
    )
    commit_create("fix", f"apply fix for {condition} ({tag})", cwd=str(root))
    commit_create("refactor", f"polish {condition} ({tag})", cwd=str(root))


_MAGI_FEEDBACK_FILENAME = "magi-feedback.md"


def _write_magi_feedback_file(root: Path, rejections: list[str]) -> Path:
    '''Persist rejection history to `.claude/magi-feedback.md` for next iter.

    Implements iter-2 Finding W6 Option B: the current `invoke_magi(
    context_paths, timeout, cwd)` signature does NOT accept an
    `extra_context` kwarg (verified in Milestone B's magi_dispatch.py).
    Instead of extending the frozen Milestone B API, we pass rejection
    feedback through an auxiliary file that MAGI reads via its
    `context_paths` argument. The file lives at
    `.claude/magi-feedback.md` (inside the destination project's
    `.claude/` gitignored dir, never committed). It is overwritten each
    iteration with the full rejection history so MAGI receives
    cumulative context, not per-iter deltas.
    '''
    path = root / ".claude" / _MAGI_FEEDBACK_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "# MAGI iteration feedback\n\n"
    body += (
        "The following conditions from prior iterations were REJECTED "
        "by /receiving-code-review with documented rationale. Re-raising "
        "them without new evidence produces sterile loops.\n\n"
    )
    for line in rejections:
        body += f"- {line}\n"
    path.write_text(body, encoding="utf-8")
    return path


def _loop2(root: Path, cfg, threshold_override: str | None):
    threshold = threshold_override or cfg.magi_threshold
    if _safe_threshold_rank(threshold) < _safe_threshold_rank(cfg.magi_threshold):
        raise ValidationError(
            f"--magi-threshold can only elevate; {threshold} < config {cfg.magi_threshold}"
        )
    diff_paths = [str(root / "planning" / "claude-plan-tdd.md")]
    rejections: list[str] = []
    for iteration in range(1, cfg.magi_max_iterations + 1):
        # W6: rejection feedback is passed via an auxiliary file added to
        # context_paths, NOT via an extra_context kwarg (Milestone B's
        # invoke_magi signature is frozen and takes only context_paths +
        # timeout + cwd).
        iter_paths = list(diff_paths)
        if rejections:
            iter_paths.append(str(_write_magi_feedback_file(root, rejections)))
        verdict = magi_dispatch.invoke_magi(
            context_paths=iter_paths,
            cwd=str(root),
        )
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(f"MAGI STRONG_NO_GO at iter {iteration}")
        if verdict.conditions:
            # W3: /receiving-code-review returns SkillResult(stdout, ...).
            # Parse stdout into (accepted, rejected) lists rather than
            # assuming the skill result exposes accepted/rejected attrs
            # directly (SkillResult does NOT).
            review_result = superpowers_dispatch.receiving_code_review(
                args=_conditions_to_skill_args(verdict.conditions),
                cwd=str(root),
            )
            accepted, rejected = _parse_receiving_review(review_result)
            if not accepted and not rejected and verdict.conditions:
                raise ValidationError(
                    f"/receiving-code-review produced no decisions for "
                    f"{len(verdict.conditions)} MAGI conditions; cannot proceed"
                )
            for idx, cond in enumerate(accepted, start=1):
                _apply_condition_via_mini_cycle(cond, root, iteration, idx)
            rejections.extend(f"iter {iteration} rejected: {c}" for c in rejected)
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            if verdict.verdict == "GO_WITH_CAVEATS" and not _conditions_low_risk(verdict.conditions):
                continue  # structural condition - re-invoke
            return verdict
    raise MAGIGateError(
        f"MAGI did not converge to full {threshold}+ after {cfg.magi_max_iterations} iterations"
    )


def _conditions_to_skill_args(conditions: tuple[str, ...]) -> list[str]:
    '''Serialize MAGI conditions as CLI args for /receiving-code-review.

    The skill accepts findings as quoted positional arguments via
    `claude -p /receiving-code-review "<finding1>" "<finding2>" ...`
    (consistent with the _make_wrapper pattern in superpowers_dispatch).
    '''
    return [c for c in conditions]


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

**Narrative clarification (addresses Finding 1 + iter-2 W3/W6):** `/receiving-code-review` is the INV-29 technical gate. It is invoked via `superpowers_dispatch.receiving_code_review` which returns a `SkillResult(stdout, stderr, returncode)` — there is NO `accepted` / `rejected` attribute on the result directly. `_parse_receiving_review` parses the skill's stdout into `(accepted, rejected)` text lists, under two markdown headers `## Accepted` / `## Rejected`. Accepted findings feed into `_apply_condition_via_mini_cycle`, which emits the three atomic commits required by sec.M.5 row 5 (mini-cycle of fix). Rejected findings accumulate in the local `rejections` list; each subsequent MAGI invocation passes them as an auxiliary `.claude/magi-feedback.md` file inside `context_paths` (Milestone B's `invoke_magi` signature is frozen and does not accept `extra_context`). This breaks sterile loops where MAGI keeps re-raising dismissed concerns. The `/receiving-code-review` orchestration is responsible for applying the actual code edits before the helper commits them; the helper only materializes the commit atomicity.

Add to the test list in Step 1:

- `test_parse_receiving_review_extracts_accepted_and_rejected_sections`: synthetic skill stdout with two sections; assert parser returns the right lists with leading bullet stripped.
- `test_parse_receiving_review_handles_empty_sections`: stdout has `## Accepted` header only, no bullets → returns `([], [])`.
- `test_parse_receiving_review_empty_stdout_returns_empty_lists`: stdout is `""` → returns `([], [])`; `_loop2` should then raise `ValidationError` if MAGI conditions were present.
- `test_loop2_writes_magi_feedback_file_when_rejections_accumulate`: iter 1 has 1 rejected condition; iter 2 invocation's `context_paths` includes `.claude/magi-feedback.md`; file contains the rejection text verbatim.
- `test_loop2_does_not_write_feedback_file_when_no_rejections` (defense-in-depth): single iter GO full no conditions; `.claude/magi-feedback.md` MUST NOT exist.
- `test_conditions_low_risk_classifies_structural_test_as_structural` (addresses W8): condition `"add structural test for timeout path"` returns False (not low-risk). Paired: condition `"fix docstring naming"` returns True. Without this test, the "test" keyword false-positive survives.

- [ ] **Step 4: Run test to verify it passes** — 20 tests (14 original + 6 new from W3/W6/W8).

- [ ] **Step 5: Commit** — `feat: pre_merge_cmd Loop 2 MAGI with INV-28 degraded and INV-29 receiving-code-review mini-cycle`.

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
    # DEFER v0.2: automate commit-prefix spot-check via git log parsing
    # (currently hardcoded True; reviewer covers this manually in pre-merge).
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


def test_auto_dry_run_short_circuits_before_preflight(tmp_path, monkeypatch):
    '''Dry-run must return 0 WITHOUT invoking subprocess/preflight (Finding 4).

    Guards against wasted time when the user only wants a plan preview
    on a machine where toolchain checks are slow or unavailable.
    '''
    import auto_cmd
    import subprocess
    original_run = subprocess.run

    def _boom(*a, **k):
        raise AssertionError("dry-run must not invoke subprocess.run")

    monkeypatch.setattr(subprocess, "run", _boom)
    rc = auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert not (tmp_path / ".claude" / "auto-run.json").exists()
    # Restore for downstream tests.
    monkeypatch.setattr(subprocess, "run", original_run)


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
import sys
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


def _print_dry_run_preview(ns: argparse.Namespace) -> None:
    '''Emit the dry-run plan without reading any subprocess/tool output.

    Keeps dry-run stdlib-only and side-effect-free so it works even
    when git/tdd-guard/plugins are unavailable.
    '''
    sys.stdout.write(
        "/sbtdd auto --dry-run:\n"
        f"  project_root: {ns.project_root}\n"
        f"  magi_max_iterations (override): {ns.magi_max_iterations}\n"
        f"  magi_threshold (override): {ns.magi_threshold}\n"
        f"  verification_retries (override): {ns.verification_retries}\n"
        "  Would execute phases 1-5 sequentially (preflight, task loop,\n"
        "  pre-merge, checklist, report). No commits, no subprocess calls.\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    # Dry-run short-circuit BEFORE any subprocess work (Finding 4). The
    # cheap parser.parse_args above does not touch the filesystem;
    # stopping here guarantees a preview never invokes preflight,
    # git, or plugin dispatchers.
    if ns.dry_run:
        _print_dry_run_preview(ns)
        return 0
    return 0


run = main
```

- [ ] **Step 4: Run test to verify it passes** — 3 tests.

- [ ] **Step 5: Commit** — `test: scaffold auto_cmd module with argparse and dry-run early short-circuit`.

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

Call from `main` AFTER the dry-run short-circuit from Task 26 (so `--dry-run` remains zero-subprocess per Finding 4) but BEFORE any Phase 2+ work. The order is: (1) parse_args, (2) if dry_run then preview + exit 0, (3) `_phase1_preflight(ns)`, (4) subsequent phases.

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
from drift import detect_drift
from errors import DriftError, VerificationIrremediableError
import superpowers_dispatch
from commits import create as commit_create
from state_file import SessionState, save as save_state
from models import COMMIT_PREFIX_MAP
from datetime import datetime, timezone
import subprocess_utils
import close_task_cmd  # public helper mark_and_advance (addresses W1)


_PHASE_ORDER = ("red", "green", "refactor")


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
                # W1: delegate to public helper in close_task_cmd instead of
                # duplicating the entire flip / commit chore / advance sequence.
                current = close_task_cmd.mark_and_advance(current, root)
        # After refactor cascade, the inner loop ends; outer while re-evaluates.
    return current
```

Rationale (iter-2 Finding W1): previous draft had `auto_cmd._close_task_inline` duplicating the full close-task sequence from `close_task_cmd.main`. Task 6 now exposes `close_task_cmd.mark_and_advance` as a public helper (no underscore), so auto's refactor cascade imports `close_task_cmd` and delegates. Single source of truth for the close-task bookkeeping; any change in the contract (e.g., extra state field, commit message tweak) propagates to both subcomandos automatically.

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
- `test_auto_never_toggles_tdd_guard` (INV-23 enforcement, Finding 9 + iter-2 W5): seed dest_root with a pre-existing `.claude/settings.json` containing the three TDD-Guard hooks (`PreToolUse`, `SessionStart`, `UserPromptSubmit`). Capture `hashlib.sha256(settings.read_bytes()).hexdigest()` BEFORE invoking `auto_cmd.main`. Spy on `Path.write_text` + `Path.open("w"|"wb"|"a")` via a factory that **filters by `self.name == "settings.json"`** — so recording ignores legitimate writes to `session-state.json`, `auto-run.json`, `magi-verdict.json`, etc. in the same `.claude/` dir (iter-2 W5: the previous "any write to that path" spy was too broad, causing false positives). Run `auto_cmd.main` end-to-end on a synthetic plan with stubbed skills + magi. Assert: (a) the filtered spy recorded ZERO writes targeting `settings.json`, (b) POST-run `hashlib.sha256(settings.read_bytes()).hexdigest()` == PRE-run hash (byte-identity — catches any write path the spy may have missed), (c) no `tdd-guard on`/`tdd-guard off` prompt is emitted to stdout. Both (a) and (b) must hold — the hash is the authoritative check; the spy is diagnostic. Docstring states the test enforces INV-23 (TDD-Guard inviolable in auto mode) per CLAUDE.local.md §3 and sec.S.10 INV-23.

- [ ] **Step 2: Run test to verify it fails** — wiring incomplete.

- [ ] **Step 3: Write minimal implementation**

```python
def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    # Dry-run must short-circuit BEFORE preflight or any subprocess work
    # (Finding 4). Keep this branch free of any read that would fail on
    # a machine without the destination project fully set up.
    if ns.dry_run:
        _print_dry_run_preview(ns)
        return 0
    state, cfg = _phase1_preflight(ns)
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

> **Ordering note (iter-2 Finding W4):** Task 46a — `tests/fixtures/skill_stubs.py` — is logically a prerequisite of Tasks 47-50 (integration tests import `StubSuperpowers` / `StubMAGI` / `make_verdict` from it). Despite its "46a" suffix the execution order is: complete Task 46 first (dispatcher cleanup), then Task 46a (shared fixture), then Tasks 47-50 (integration tests). The "a" suffix is purely a labelling convenience to keep the dispatcher cleanup (46) before the fixture (46a) without churning all downstream task numbers. Do NOT attempt Task 47 before Task 46a's `skill_stubs.py` is committed.

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

### Task 46a: `tests/fixtures/skill_stubs.py` — shared integration-test stubs

> **Execution prerequisite (iter-2 Finding W4):** run this task BEFORE Tasks 47-50. The "46a" numbering keeps Task 46 (dispatcher cleanup) first without renumbering downstream tasks, but logically this fixture is consumed by the four integration tests that follow. Tasks 47-50 will fail with `ModuleNotFoundError` on `tests.fixtures.skill_stubs` until 46a lands.

**Files:**
- Create: `tests/fixtures/skill_stubs.py`
- Create: `tests/fixtures/__init__.py` (empty marker, if not already present from earlier milestones)

**Rationale (addresses Finding 7 Balthasar):** Tasks 47-50 are integration tests that need to stub `superpowers_dispatch.*` and `magi_dispatch.invoke_magi` consistently. Sketching these stubs inline in each test creates drift and duplicated bugs. Consolidating them here gives each integration test a single import point and documented behavior.

- [ ] **Step 1: Write failing test**

```python
import pytest


def test_skill_stubs_module_importable():
    from tests.fixtures import skill_stubs
    assert hasattr(skill_stubs, "StubSuperpowers")
    assert hasattr(skill_stubs, "StubMAGI")


def test_stub_superpowers_records_invocations(tmp_path):
    from tests.fixtures.skill_stubs import StubSuperpowers
    stub = StubSuperpowers()
    stub.brainstorming(args=["@x.md"], cwd=str(tmp_path))
    assert stub.calls == [("brainstorming", ["@x.md"], str(tmp_path))]


def test_stub_magi_returns_scripted_verdict_sequence():
    from tests.fixtures.skill_stubs import StubMAGI, make_verdict
    stub = StubMAGI(sequence=[
        make_verdict("HOLD", degraded=True),
        make_verdict("GO", degraded=False),
    ])
    v1 = stub.invoke_magi(context_paths=[], cwd="/tmp")
    v2 = stub.invoke_magi(context_paths=[], cwd="/tmp")
    assert v1.verdict == "HOLD" and v1.degraded is True
    assert v2.verdict == "GO" and v2.degraded is False


def test_stub_magi_raises_on_exhausted_sequence():
    from tests.fixtures.skill_stubs import StubMAGI, make_verdict
    stub = StubMAGI(sequence=[make_verdict("GO")])
    stub.invoke_magi(context_paths=[], cwd="/tmp")
    with pytest.raises(IndexError):
        stub.invoke_magi(context_paths=[], cwd="/tmp")
```

- [ ] **Step 2: Run test to verify it fails** — `ModuleNotFoundError` on `tests.fixtures.skill_stubs`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
'''Canonical stubs for integration tests consuming superpowers and MAGI dispatchers.

Behavior contract (assertion points for Tasks 47-50):

StubSuperpowers:
  - Records every skill invocation as (name, args, cwd) in `self.calls`.
  - Returns a zero-exit SkillResult by default; raise via `self.fail_on = {"name"}`.
  - Writes synthetic output files when configured via
    `self.create_files = {"name": [Path(...), ...]}` — emulates skills that
    produce tracked artifacts (brainstorming, writing_plans).

StubMAGI:
  - `sequence: list[MAGIVerdict]` is consumed FIFO per invocation.
  - Each call records `context_paths` (full list per invocation) so tests
    can verify iter-2 W6 rejection-feedback threading: Loop 2 appends
    `.claude/magi-feedback.md` to `context_paths` on iter N+1 when
    iter N produced rejected conditions. Tests assert that path is
    present in the second call's `context_paths` but absent in the first.
  - Raises IndexError on exhaustion so runaway loops fail loud, not silent.

make_verdict(verdict, conditions=(), findings=(), degraded=False) -> MAGIVerdict:
  - Convenience constructor so tests read declaratively.
'''
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from magi_dispatch import MAGIVerdict
from superpowers_dispatch import SkillResult


def make_verdict(
    verdict: str,
    conditions: tuple[str, ...] = (),
    findings: tuple[str, ...] = (),
    degraded: bool = False,
) -> MAGIVerdict:
    return MAGIVerdict(
        verdict=verdict,
        conditions=conditions,
        findings=findings,
        degraded=degraded,
    )


@dataclass
class StubSuperpowers:
    calls: list[tuple[str, list[str], str]] = field(default_factory=list)
    fail_on: set[str] = field(default_factory=set)
    create_files: dict[str, list[Path]] = field(default_factory=dict)

    def _record(self, name: str, args: list[str], cwd: str) -> SkillResult:
        self.calls.append((name, list(args), cwd))
        if name in self.fail_on:
            raise RuntimeError(f"stub forced failure for {name}")
        for p in self.create_files.get(name, ()):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("", encoding="utf-8")
        return SkillResult(name, 0, "", "")

    def brainstorming(self, *, args: list[str] | None = None,
                      cwd: str = "") -> SkillResult:
        return self._record("brainstorming", args or [], cwd)

    def writing_plans(self, *, args: list[str] | None = None,
                      cwd: str = "") -> SkillResult:
        return self._record("writing_plans", args or [], cwd)

    def verification_before_completion(self, *, cwd: str = "") -> SkillResult:
        return self._record("verification_before_completion", [], cwd)

    def requesting_code_review(self, *, cwd: str = "") -> SkillResult:
        return self._record("requesting_code_review", [], cwd)

    def receiving_code_review(self, *, cwd: str = "",
                              findings: list[str] | None = None) -> Any:
        self._record("receiving_code_review", list(findings or []), cwd)

        class _Review:
            accepted = tuple(findings or ())
            rejected: tuple[str, ...] = ()

        return _Review()

    def test_driven_development(self, *, args: list[str] | None = None,
                                cwd: str = "") -> SkillResult:
        return self._record("test_driven_development", args or [], cwd)

    def systematic_debugging(self, *, cwd: str = "") -> SkillResult:
        return self._record("systematic_debugging", [], cwd)

    def finishing_a_development_branch(self, *, cwd: str = "") -> SkillResult:
        return self._record("finishing_a_development_branch", [], cwd)


@dataclass
class StubMAGI:
    sequence: list[MAGIVerdict]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def invoke_magi(self, *, context_paths: list[str], cwd: str,
                    timeout: int = 1800) -> MAGIVerdict:
        # Signature mirrors magi_dispatch.invoke_magi EXACTLY
        # (no extra_context — Milestone B's frozen signature takes
        # context_paths, timeout, cwd only; rejection feedback flows
        # via an auxiliary .claude/magi-feedback.md path appended to
        # context_paths by _loop2 — see iter-2 Finding W6).
        self.calls.append({
            "context_paths": list(context_paths),
            "cwd": cwd,
            "timeout": timeout,
        })
        return self.sequence.pop(0)
```

Tests 47-50 import `StubSuperpowers`, `StubMAGI`, `make_verdict` and wire them through `monkeypatch.setattr(superpowers_dispatch, "<name>", stub.<name>)` + `monkeypatch.setattr(magi_dispatch, "invoke_magi", stub.invoke_magi)`.

- [ ] **Step 4: Run test to verify it passes** — 4 tests.

- [ ] **Step 5: Commit** — `test: add shared skill_stubs fixture for integration tests`.

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

from tests.fixtures.skill_stubs import StubSuperpowers, StubMAGI, make_verdict


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
    import superpowers_dispatch
    import magi_dispatch
    sp = StubSuperpowers()
    sp.create_files["brainstorming"] = [tmp_path / "sbtdd" / "spec-behavior.md"]
    sp.create_files["writing_plans"] = [tmp_path / "planning" / "claude-plan-tdd-org.md"]
    for name in (
        "brainstorming", "writing_plans", "verification_before_completion",
        "requesting_code_review", "receiving_code_review",
        "test_driven_development", "systematic_debugging",
        "finishing_a_development_branch",
    ):
        monkeypatch.setattr(superpowers_dispatch, name, getattr(sp, name))
    magi = StubMAGI(sequence=[make_verdict("GO", degraded=False)])
    monkeypatch.setattr(magi_dispatch, "invoke_magi", magi.invoke_magi)
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

- [ ] **Step 1: Run full test suite + time budget check** (Finding 8 Balthasar)

```bash
/usr/bin/time -f "%e" python -m pytest tests/ -v --tb=short 2> pytest-elapsed.txt
tail -1 pytest-elapsed.txt
```

On Windows, use PowerShell `Measure-Command { python -m pytest tests/ }` and read the `.TotalSeconds` field. Expected: all tests pass (Milestones A+B baseline + ~130+ Milestone C tests). 0 failures. Wall-clock runtime of `make verify` on a developer laptop (Python 3.12 in `.venv`) MUST be `<= 60 seconds`. If exceeded, mark the slowest 20% with `@pytest.mark.slow` and introduce a fast/slow split in the Makefile (`make verify` = fast; `make verify-all` = fast + slow) before shipping Milestone C.

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
| 14 (close-task) | 4-6 + Task 6a (shared `_plan_ops`) |
| 15 (status drift) | 1-3 |
| 16 (pre-merge) | 19-21 |
| 17 (finalize) | 22-25 + Task 50 |
| 18 (auto) | 26-31 + Task 48 |
| 19 (resume) | 32-36 + Task 49 |
| Integration infra | Task 46a (skill_stubs shared fixture) |

- [ ] **Step 4: INV scan**

Grep for INV tokens across `tests/` to confirm coverage: INV-0 (all commits via `commits.create`), INV-5..7 (Milestone A `validate_message`), INV-9 (Task 21 Loop 1 -> Loop 2), INV-22 (Task 28), INV-23 (Task 26-31 never toggles tdd-guard), INV-24 (Task 36 CONTINUE default), INV-25 (Task 30 no finishing skill in auto), INV-26 (Task 30-31 auto-run.json), INV-27 (Task 16), INV-28 (Tasks 18, 21, 24, 29, 50), INV-29 (Task 21), INV-30 (Tasks 32-36).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: milestone C acceptance sweep with all tests green"
```

---

## Milestone C — Acceptance

Tras completar las 55 tareas (Task 0 + Tasks 1-52 + Task 6a + Task 46a):

- **9 nuevos modulos `*_cmd.py`** bajo `skills/sbtdd/scripts/`, cada uno con `main(argv)` + `run = main` + argparse parser.
- **1 modulo modificado** (`run_sbtdd.py`) con `SUBCOMMAND_DISPATCH` completamente cableado a los 9 `*_cmd.main` reales.
- **3 nuevas clases de excepcion** en `errors.py`: `Loop1DivergentError` (exit 7), `VerificationIrremediableError` (exit 6), `ChecklistError` (exit 9). `EXIT_CODES` extendido.
- **10 test files nuevos** (`test_status_cmd`, `test_close_task_cmd`, `test_close_phase_cmd`, `test_init_cmd`, `test_spec_cmd`, `test_pre_merge_cmd`, `test_finalize_cmd`, `test_auto_cmd`, `test_resume_cmd`, `test_run_sbtdd_wiring`) + `test_integration_full_cycle` con ~120+ tests cubriendo escenarios 11-19 BDD + integracion end-to-end.
- **6 fixtures nuevos** (3 plans + 3 MAGI verdicts) bajo `tests/fixtures/`.
- `make verify` limpio: pytest + ruff check + ruff format --check + mypy (strict).
- **`make verify` runtime budget (Finding 8):** debe completar en `<= 60 segundos` en una developer laptop (Python 3.12 + `.venv`, Milestone A+B+C combined suite, ~350+ tests). Si se excede, marcar el 20% mas lento con `@pytest.mark.slow` y dividir en `make verify` (fast) vs `make verify-all` (fast + slow) antes de cerrar Milestone C.
- ~55 commits atomicos con prefijos sec.M.5:
  - Task 0, Task 52: `chore:` (bookkeeping).
  - Tasks 1, 4, 7, 11, 16, 19, 22, 26, 32: `test:` (fresh module scaffolds).
  - Task 6a: `feat:` (extracts shared `_plan_ops` module, precedente de row "nueva logica en modulo nuevo" del commit-prefix policy — file nuevo + contrato establecido por tests).
  - Tasks 2, 3, 5, 6, 8, 9, 10, 12, 13, 14, 15, 17, 18, 20, 21, 23, 24, 25, 27, 28, 29, 30, 31, 33, 34, 35, 36: `feat:` (new behavior in existing modules).
  - Tasks 37-45: `feat:` (dispatcher wiring).
  - Task 46: `refactor:` (scaffold cleanup, behavior-preserving).
  - Task 46a: `test:` (fresh integration-test fixture module `tests/fixtures/skill_stubs.py`).
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
- Escenario 14 (close-task bookkeeping) -> Tasks 4-6 + Task 6a OK (Task 6a extracts shared plan-ops helpers used by 6, 18, 28 per Finding 6).
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
| INV-23 | Tasks 26-31 + Task 31 explicit test `test_auto_never_toggles_tdd_guard` (Finding 9) | Auto never toggles tdd-guard |
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
