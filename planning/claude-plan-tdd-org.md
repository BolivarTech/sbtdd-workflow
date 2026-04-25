# sbtdd-workflow v0.3.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v0.3.0 (operational hardening MINOR bump) with two additive feature surfaces — auto progress streaming (Feature D) + per-skill model selection flag (Feature E). Non-BREAKING: default null preserves v0.2.x argv byte-identical.

**Architecture:** Two independent feature surfaces dispatched to two parallel subagents. D touches `auto_cmd.py` only (streaming primitives + progress field). E touches `config.py`, `models.py`, three `*_dispatch.py` modules, `dependency_check.py`, `auto_cmd.py` (CLI parser only), and `templates/plugin.local.md.template`. Surfaces in `auto_cmd.py` are disjoint functions (D defines `_stream_subprocess` / `_update_progress`; E defines `_parse_model_overrides` / `_apply_inv0_model_check`) so parallel subagents do not clash. After both subagents land, the orchestrator drives a final review loop (MAGI → /receiving-code-review, cap 5 iter, exit when verdict ≥ GO_WITH_CAVEATS full with zero CRITICAL + zero WARNING + zero Conditions for Approval).

**Tech Stack:** Python 3.9+ stdlib only on hot paths, PyYAML at config-load, pytest + ruff + mypy --strict for verification. Cross-platform Windows + POSIX.

---

## Reference materials

Before starting any task, read:

- **Spec**: `sbtdd/spec-behavior.md` (BDD overlay v0.3.0 — escenarios D1.1..R1.7).
- **Spec base**: `sbtdd/spec-behavior-base.md` (raw input v1.0.0; defines deferred items D5/E2/F/G/H).
- **Authoritative contract**: `sbtdd/sbtdd-workflow-plugin-spec-base.md` sec.S.10 (invariants INV-0..INV-31).
- **Project rules**: `CLAUDE.local.md` (TDD discipline, commit prefixes, plan-approved contract).
- **Global rules**: `~/.claude/CLAUDE.md` (INV-0 absolute precedence: English commits, no AI refs, no Co-Authored-By, atomic commits).

---

## File structure

| File | Track | Responsibility | Status |
|------|-------|----------------|--------|
| `skills/sbtdd/scripts/auto_cmd.py` | D + E | D: `_stream_subprocess`, `_update_progress`, breadcrumbs hooks. E: `_parse_model_overrides`, `_apply_inv0_model_check`, propagate model kwargs through dispatch calls | Modify |
| `skills/sbtdd/scripts/config.py` | E | `PluginConfig` adds 4 Optional[str] model fields; loader tolerates absence | Modify |
| `skills/sbtdd/scripts/superpowers_dispatch.py` | E | `invoke_skill` accepts `model: str \| None = None`; `_build_skill_cmd` injects `--model <id>` before `-p` when set; INV-0 check ignores model when CLAUDE.md pinned | Modify |
| `skills/sbtdd/scripts/spec_review_dispatch.py` | E | `dispatch_spec_reviewer` accepts model kwargs (uses `code_review_model` + `spec_reviewer_model` fields); propagates to `invoke_skill` | Modify |
| `skills/sbtdd/scripts/magi_dispatch.py` | E | `dispatch_magi` accepts `model` kwarg (uses `magi_dispatch_model`); injects `--model` in `_build_magi_cmd` argv | Modify |
| `skills/sbtdd/scripts/models.py` | E | Add `ALLOWED_CLAUDE_MODEL_IDS: tuple[str, ...]` + `INV_0_PINNED_MODEL_RE` regex constant | Modify |
| `skills/sbtdd/scripts/dependency_check.py` | E | Add `check_model_ids(config) -> DependencyCheck` returning warning (init) or hard fail (runtime via raise) | Modify |
| `templates/plugin.local.md.template` | E | Append commented Sonnet+Haiku baseline block (4 fields commented) | Modify |
| `tests/test_auto_streaming.py` | D | Cover D1.1, D1.2, D1.3, D2.1, D3.1, D3.2 | Create |
| `tests/test_auto_progress.py` | D | Cover D4.1, D4.2, D4.3 | Create |
| `tests/test_config_model_fields.py` | E | Cover E1.1, E1.2, E1.3 | Create |
| `tests/test_dispatch_model_arg.py` | E | Cover E3.1, E3.2, E3.3, E3.4 (across 3 dispatch modules) | Create |
| `tests/test_cli_model_override.py` | E | Cover E4.1, E4.2, E4.3, E4.4, E4.5 | Create |
| `tests/test_dependency_check_models.py` | E | Cover E5.1, E5.2 | Create |
| `tests/test_models_constants.py` | E | Cover E6.1, E6.2 | Create |
| `tests/test_init_cmd.py` | E | Extend with E7.1 + E7.2 (template baseline assertions) | Modify (existing) |
| `CHANGELOG.md` | Final | Add `[0.3.0]` section | Modify |
| `README.md` | Final | Add Cost optimization section + matrix | Modify |
| `skills/sbtdd/SKILL.md` | Final | Add `## v0.3 flags` section + INV-0 cascade docs | Modify |
| `.claude-plugin/plugin.json` | Final | 0.2.2 → 0.3.0 | Modify |
| `.claude-plugin/marketplace.json` | Final | 0.2.2 → 0.3.0 (two occurrences) | Modify |

---

## Subagent dispatch contracts

### Subagent #1 — Track D (auto streaming)

- **Reads**: `sbtdd/spec-behavior.md` sec.2 (Feature D). `skills/sbtdd/scripts/auto_cmd.py` (current state). `skills/sbtdd/scripts/state_file.py` (atomic write pattern reference).
- **Writes**: `skills/sbtdd/scripts/auto_cmd.py` (extension). `tests/test_auto_streaming.py` (new). `tests/test_auto_progress.py` (new).
- **Forbidden**: any file in track E above.
- **TDD-Guard**: ON.
- **Tasks**: D1, D2, D3, D4 (in any order; recommended order below).
- **Done**: 4 deliverables landed + tests pass + `make verify` clean.

### Subagent #2 — Track E (per-skill model flag)

- **Reads**: `sbtdd/spec-behavior.md` sec.3. `skills/sbtdd/scripts/config.py`. `skills/sbtdd/scripts/superpowers_dispatch.py`. `skills/sbtdd/scripts/magi_dispatch.py`. `skills/sbtdd/scripts/spec_review_dispatch.py`. `skills/sbtdd/scripts/models.py`. `skills/sbtdd/scripts/dependency_check.py`. `templates/plugin.local.md.template`.
- **Writes**: 7 production modules + 6 test modules (1 modified, 5 new) + 1 template.
- **Forbidden**: `_stream_subprocess` / `_update_progress` / breadcrumb logic in `auto_cmd.py` (track D).
- **TDD-Guard**: ON.
- **Tasks**: E6 → E1 → E3 → E4 → E5 → E7 (recommended order: constants first, then config, then dispatch wiring, then CLI, then validation, then template).
- **Done**: 6 deliverables landed + tests pass + `make verify` clean.

### Coordination

- Both subagents commit to `main`. If a commit conflict occurs in `auto_cmd.py`, subagent #2 rebases onto subagent #1's HEAD (D code lands first by convention).
- Each subagent invokes `make verify` before its final commit.
- Each subagent reports DONE to the orchestrator with the commit SHA range.

---

# Track D — Auto progress streaming (Subagent #1)

## Task D1: Subprocess streaming primitive

**Files:**
- Create: `tests/test_auto_streaming.py`
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_stream_subprocess` helper)

- [ ] **Step 1: Write failing test for D1.1 (line-by-line flush)**

```python
# tests/test_auto_streaming.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature D auto streaming primitives."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd


def test_stream_subprocess_flushes_lines_individually(tmp_path, capfd):
    """D1.1: streaming flushes subprocess output line-by-line within 250ms."""
    script = tmp_path / "emit5.py"
    script.write_text(
        "import sys, time\n"
        "for i in range(5):\n"
        "    print(f'line{i}', flush=True)\n"
        "    time.sleep(0.05)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
    )
    start = time.monotonic()
    auto_cmd._stream_subprocess(proc, prefix="[sbtdd test phase]")
    elapsed = time.monotonic() - start
    proc.wait(timeout=2)
    captured = capfd.readouterr()
    assert "line0" in captured.err
    assert "line4" in captured.err
    assert elapsed < 1.0  # 5 lines * 50ms + slack, not blocking till end
```

- [ ] **Step 2: Run test, verify it fails**

```bash
cd D:/jbolivarg/PythonProjects/SBTDD
python -m pytest tests/test_auto_streaming.py::test_stream_subprocess_flushes_lines_individually -v
```
Expected: FAIL with `AttributeError: module 'auto_cmd' has no attribute '_stream_subprocess'`.

- [ ] **Step 3: Implement `_stream_subprocess` in auto_cmd.py**

Add near the top of `auto_cmd.py` (after existing imports), function:

```python
def _stream_subprocess(
    proc: subprocess.Popen[str],
    prefix: str,
) -> tuple[str, str]:
    """Read subprocess stdout/stderr line-by-line, rewrite to orchestrator stderr.

    Reads pipes via select-based polling so neither stream starves. Each
    line is prefixed with ``prefix`` and emitted to ``sys.stderr`` of the
    orchestrator. Returns the accumulated (stdout, stderr) for the caller's
    diagnostic / commit-error recovery paths (CommitError v0.1.6 expects
    captured strings).

    Cross-platform: uses :func:`select.select` on POSIX and a thread-pair
    fallback on Windows where ``select`` does not work on pipes (PEP 446).
    """
    import io
    import threading

    stdout_buf: list[str] = []
    stderr_buf: list[str] = []

    def _pump(stream: io.TextIOBase, sink: list[str], is_err: bool) -> None:
        for line in iter(stream.readline, ""):
            sink.append(line)
            sys.stderr.write(f"{prefix} {line}")
            sys.stderr.flush()
        stream.close()

    t_out = threading.Thread(target=_pump, args=(proc.stdout, stdout_buf, False), daemon=True)
    t_err = threading.Thread(target=_pump, args=(proc.stderr, stderr_buf, True), daemon=True)
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    return ("".join(stdout_buf), "".join(stderr_buf))
```

- [ ] **Step 4: Run test, verify it passes**

```bash
python -m pytest tests/test_auto_streaming.py::test_stream_subprocess_flushes_lines_individually -v
```
Expected: PASS.

- [ ] **Step 5: Add D1.2 test (prefix consistency)**

```python
def test_stream_subprocess_applies_prefix(tmp_path, capfd):
    """D1.2: stderr lines carry the supplied prefix."""
    script = tmp_path / "emit_to_stderr.py"
    script.write_text(
        "import sys\n"
        "sys.stderr.write('[skill] starting red phase\\n')\n"
        "sys.stderr.flush()\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
    )
    auto_cmd._stream_subprocess(proc, prefix="[sbtdd task-7 green]")
    proc.wait(timeout=2)
    captured = capfd.readouterr()
    assert "[sbtdd task-7 green] [skill] starting red phase" in captured.err
```

- [ ] **Step 6: Run test, expect PASS**

```bash
python -m pytest tests/test_auto_streaming.py::test_stream_subprocess_applies_prefix -v
```
Already passes given the prefix-aware implementation in step 3.

- [ ] **Step 7: Add D1.3 test (SIGTERM flush)**

```python
def test_stream_subprocess_flushes_on_sigterm(tmp_path, capfd):
    """D1.3: streaming flushes pending buffers on subprocess termination."""
    script = tmp_path / "emit_then_hang.py"
    script.write_text(
        "import sys, time\n"
        "print('first', flush=True)\n"
        "time.sleep(60)\n"
    )
    proc = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        text=True,
    )
    time.sleep(0.5)
    proc.terminate()
    proc.wait(timeout=5)
    auto_cmd._stream_subprocess(proc, prefix="[sbtdd]")
    captured = capfd.readouterr()
    assert "first" in captured.err
```

- [ ] **Step 8: Verify all D1 tests pass + run full suite**

```bash
python -m pytest tests/test_auto_streaming.py -v
make verify
```
Expected: 3 D1 tests PASS, 735+ baseline tests pass, ruff + mypy clean.

- [ ] **Step 9: Commit (Red→Green collapsed since helper is new)**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_streaming.py
git commit -m "feat: add _stream_subprocess line-buffered output for auto runs"
```

---

## Task D2: python -u flag in subprocess invocation

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (subprocess argv construction site)
- Modify: `tests/test_auto_streaming.py`

- [ ] **Step 1: Write failing test D2.1**

```python
# Append to tests/test_auto_streaming.py
def test_subprocess_argv_includes_dash_u():
    """D2.1: auto_cmd subprocess argv is prefixed with python -u."""
    argv = auto_cmd._build_run_sbtdd_argv(subcommand="close-phase", extra_args=["--variant", "fix"])
    assert argv[0:2] == [sys.executable, "-u"]
    assert "run_sbtdd.py" in argv[2]
    assert "close-phase" in argv
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_auto_streaming.py::test_subprocess_argv_includes_dash_u -v
```
Expected: FAIL — `_build_run_sbtdd_argv` not defined OR existing argv lacks `-u`.

- [ ] **Step 3: Implement / refactor**

Locate the existing site in `auto_cmd.py` where the subprocess argv is built (search for `subprocess.run(...)` invocation that targets `run_sbtdd.py`). Extract it into:

```python
def _build_run_sbtdd_argv(subcommand: str, extra_args: list[str] | None = None) -> list[str]:
    """Build subprocess argv for invoking run_sbtdd.py with python -u.

    The ``-u`` flag disables Python output buffering at the dispatcher
    level so :func:`_stream_subprocess` reads complete lines as the
    sub-process emits them (sec.S.6.D).
    """
    run_sbtdd = (Path(__file__).resolve().parent / "run_sbtdd.py").as_posix()
    argv = [sys.executable, "-u", run_sbtdd, subcommand]
    if extra_args:
        argv.extend(extra_args)
    return argv
```

Then replace each existing argv construction site with a call to this helper. Preserve any environment variables / cwd kwargs from the original call sites.

- [ ] **Step 4: Run test, verify PASS**

```bash
python -m pytest tests/test_auto_streaming.py::test_subprocess_argv_includes_dash_u -v
make verify
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_streaming.py
git commit -m "feat: prefix run_sbtdd subprocess invocation with python -u"
```

---

## Task D3: State-machine breadcrumbs per phase transition

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_streaming.py`

- [ ] **Step 1: Failing test D3.1 (red→green breadcrumb)**

```python
def test_breadcrumb_on_red_to_green_transition(capfd):
    """D3.1: state-machine emits breadcrumb before phase advance dispatch."""
    auto_cmd._emit_phase_breadcrumb(phase=2, total_phases=5, task_index=14, task_total=36, sub_phase="green")
    captured = capfd.readouterr()
    assert "[sbtdd] phase 2/5: task loop -- task 14/36 (green)" in captured.err
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_auto_streaming.py::test_breadcrumb_on_red_to_green_transition -v
```
Expected: FAIL — `_emit_phase_breadcrumb` not defined.

- [ ] **Step 3: Implement `_emit_phase_breadcrumb`**

```python
_PHASE_NAMES: tuple[str, ...] = (
    "pre-flight",
    "spec",
    "task loop",
    "pre-merge",
    "checklist",
)


def _emit_phase_breadcrumb(
    phase: int,
    total_phases: int,
    *,
    task_index: int | None = None,
    task_total: int | None = None,
    sub_phase: str | None = None,
) -> None:
    """Emit a one-line state-machine breadcrumb to orchestrator stderr.

    Format: ``[sbtdd] phase {p}/{t}: {phase_name} -- task {i}/{n} ({sub_phase})``.
    Task-index and sub-phase are optional for non-task-loop phases.
    """
    name = _PHASE_NAMES[phase] if 0 <= phase < len(_PHASE_NAMES) else f"phase-{phase}"
    line = f"[sbtdd] phase {phase}/{total_phases}: {name}"
    if task_index is not None and task_total is not None:
        suffix = f" ({sub_phase})" if sub_phase else ""
        line += f" -- task {task_index}/{task_total}{suffix}"
    sys.stderr.write(line + "\n")
    sys.stderr.flush()
```

- [ ] **Step 4: Verify D3.1 passes**

```bash
python -m pytest tests/test_auto_streaming.py::test_breadcrumb_on_red_to_green_transition -v
```

- [ ] **Step 5: Add D3.2 test (task close advance)**

```python
def test_breadcrumb_on_task_close_advance(capfd):
    """D3.2: state machine emits breadcrumb when advancing task index."""
    auto_cmd._emit_phase_breadcrumb(phase=2, total_phases=5, task_index=15, task_total=36, sub_phase="red")
    captured = capfd.readouterr()
    assert "[sbtdd] phase 2/5: task loop -- task 15/36 (red)" in captured.err
```

- [ ] **Step 6: Wire breadcrumb invocation into `_phase2_task_loop`**

Locate `_phase2_task_loop` in `auto_cmd.py`. Insert `_emit_phase_breadcrumb(...)` calls at:
- Phase entry (top of loop body — `phase=2`).
- Each Red/Green/Refactor sub-phase advance (immediately AFTER state file save, BEFORE next subagent dispatch).
- Each task close (immediately after `mark_and_advance` returns, BEFORE first dispatch on the new task).

Pass current `task_index` and `task_total` from the loop counters; `sub_phase` from `current_phase` field.

- [ ] **Step 7: make verify clean**

```bash
make verify
```

- [ ] **Step 8: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_streaming.py
git commit -m "feat: emit state-machine breadcrumbs per auto phase transition"
```

---

## Task D4: auto-run.json progress field with atomic writes

**Files:**
- Create: `tests/test_auto_progress.py`
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_update_progress`)

- [ ] **Step 1: Failing test D4.2 (progress field schema)**

```python
# tests/test_auto_progress.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature D auto-run.json progress field."""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd


def test_update_progress_writes_correct_schema(tmp_path):
    """D4.2: progress field has shape {phase, task_index, task_total, sub_phase}."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"started_at": "2026-04-25T10:00:00Z"}))
    auto_cmd._update_progress(
        auto_run,
        phase=2,
        task_index=14,
        task_total=36,
        sub_phase="green",
    )
    data = json.loads(auto_run.read_text())
    assert data["progress"] == {
        "phase": 2,
        "task_index": 14,
        "task_total": 36,
        "sub_phase": "green",
    }
    assert data["started_at"] == "2026-04-25T10:00:00Z"  # preserved
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_auto_progress.py::test_update_progress_writes_correct_schema -v
```
Expected: FAIL — `_update_progress` not defined.

- [ ] **Step 3: Implement `_update_progress`**

```python
def _update_progress(
    auto_run_path: Path,
    *,
    phase: int,
    task_index: int | None,
    task_total: int | None,
    sub_phase: str | None,
) -> None:
    """Write the progress field of auto-run.json atomically (tmp + os.replace).

    Mirrors the atomic-write pattern of state_file.save and
    escalation_prompt._write_pending_marker_atomically (v0.2.1). A
    concurrent reader sees either the prior progress payload or the
    new one, never a torn JSON document.
    """
    if auto_run_path.exists():
        existing = json.loads(auto_run_path.read_text(encoding="utf-8"))
    else:
        existing = {}
    progress: dict[str, object] = {"phase": phase}
    if task_index is not None:
        progress["task_index"] = task_index
    if task_total is not None:
        progress["task_total"] = task_total
    if sub_phase is not None:
        progress["sub_phase"] = sub_phase
    existing["progress"] = progress
    tmp = auto_run_path.with_suffix(auto_run_path.suffix + ".tmp")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(auto_run_path))
```

(Add `import os, json` at top of `auto_cmd.py` if not already present.)

- [ ] **Step 4: Verify D4.2 passes**

- [ ] **Step 5: Add D4.1 test (atomicity under concurrent reads)**

```python
def test_update_progress_is_atomic_under_concurrent_reads(tmp_path):
    """D4.1: concurrent readers never observe torn JSON."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"progress": {"phase": 2, "task_index": 13, "task_total": 36, "sub_phase": "refactor"}}))
    failures: list[str] = []
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            try:
                json.loads(auto_run.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                failures.append(str(e))

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    for i in range(50):
        auto_cmd._update_progress(
            auto_run, phase=2, task_index=14 + i, task_total=36, sub_phase="green"
        )
    stop.set()
    t.join(timeout=2)
    assert failures == [], f"reader saw torn JSON: {failures}"
```

- [ ] **Step 6: Run + expect PASS** (atomic write via os.replace ensures no torn JSON)

- [ ] **Step 7: Add D4.3 test (absent progress is tolerated)**

```python
def test_progress_field_absent_is_tolerated(tmp_path):
    """D4.3: parser tolerates auto-run.json without progress field."""
    auto_run = tmp_path / "auto-run.json"
    auto_run.write_text(json.dumps({"started_at": "2026-04-25T10:00:00Z"}))
    data = json.loads(auto_run.read_text())
    assert data.get("progress") is None  # absent is fine
```

- [ ] **Step 8: Wire `_update_progress` into `_phase2_task_loop` (and other phases)**

Same hooks as D3 breadcrumbs — at every state machine transition, call `_update_progress` AFTER `state_file.save` succeeds and BEFORE the next dispatch. The `auto_run_path` is constructed from `Path(".claude") / "auto-run.json"` (already used elsewhere in the file).

- [ ] **Step 9: make verify**

```bash
make verify
```

- [ ] **Step 10: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: write auto-run.json progress field atomically per phase transition"
```

---

## Track D — done criteria

- [ ] All 3 test files (`test_auto_streaming.py`, `test_auto_progress.py`) pass.
- [ ] 4 atomic commits landed: streaming primitive, python -u, breadcrumbs, progress field.
- [ ] `make verify` clean.
- [ ] Cross-platform sanity: tests pass on Windows (current dev env) AND POSIX (CI deferred to v1.1; manual verification on WSL or local Linux container if available).
- [ ] Subagent #1 reports DONE with commit SHA range to orchestrator.

---

# Track E — Per-skill model selection flag (Subagent #2)

## Task E6: ALLOWED_CLAUDE_MODEL_IDS + INV_0_PINNED_MODEL_RE constants

**Files:**
- Create: `tests/test_models_constants.py`
- Modify: `skills/sbtdd/scripts/models.py`

- [ ] **Step 1: Failing test E6.1 (immutability)**

```python
# tests/test_models_constants.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E model registry constants."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import models


def test_allowed_claude_model_ids_is_tuple():
    """E6.1: ALLOWED_CLAUDE_MODEL_IDS is immutable (tuple, not list)."""
    assert isinstance(models.ALLOWED_CLAUDE_MODEL_IDS, tuple)
    with pytest.raises((AttributeError, TypeError)):
        models.ALLOWED_CLAUDE_MODEL_IDS.append("foo")  # type: ignore[attr-defined]


def test_allowed_claude_model_ids_contains_current_4x_families():
    """E6.2: tuple contains at least Opus 4.7, Sonnet 4.6, Haiku 4.5."""
    ids = set(models.ALLOWED_CLAUDE_MODEL_IDS)
    assert "claude-opus-4-7" in ids
    assert "claude-sonnet-4-6" in ids
    assert "claude-haiku-4-5-20251001" in ids
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_models_constants.py -v
```
Expected: FAIL — `ALLOWED_CLAUDE_MODEL_IDS` not defined.

- [ ] **Step 3: Add constants to models.py**

Append at the end of `models.py`:

```python
#: Claude model IDs the plugin recognizes as valid for ``--model`` arg
#: passing in dispatch wrappers. v0.3.0 ships the 4.x family snapshot
#: (Opus 4.7, Sonnet 4.6, Haiku 4.5). Bump this tuple when Anthropic
#: ships a new family; update SKILL.md operational impact accordingly.
ALLOWED_CLAUDE_MODEL_IDS: tuple[str, ...] = (
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
)


#: Regex used by superpowers_dispatch / magi_dispatch to detect when the
#: developer's global ``~/.claude/CLAUDE.md`` pins a Claude model
#: explicitly. INV-0 cascade: if the global file pins, plugin.local.md
#: model fields are ignored and a stderr breadcrumb is emitted. The
#: regex matches phrases like ``use claude-X-Y for``, ``pin claude-X-Y``,
#: or ``always claude-X-Y``. Word-boundary anchored to avoid false
#: positives in narrative prose.
INV_0_PINNED_MODEL_RE: "re.Pattern[str]" = re.compile(
    r"\b(?:use|pin|pinned|always|stick to|enforce)\s+(claude-(?:opus|sonnet|haiku)-\d+(?:-\d+)?(?:-\d{8})?)\b",
    re.IGNORECASE,
)
```

(Add `import re` at top of `models.py` if missing.)

- [ ] **Step 4: Verify tests pass + make verify**

```bash
python -m pytest tests/test_models_constants.py -v
make verify
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/models.py tests/test_models_constants.py
git commit -m "feat: add ALLOWED_CLAUDE_MODEL_IDS + INV_0_PINNED_MODEL_RE constants"
```

---

## Task E1: PluginConfig adds 4 model fields

**Files:**
- Create: `tests/test_config_model_fields.py`
- Modify: `skills/sbtdd/scripts/config.py`

- [ ] **Step 1: Failing test E1.2 (backward compat — fields default None)**

```python
# tests/test_config_model_fields.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E PluginConfig model field extension."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

from config import load_plugin_local


def _write_minimal_plugin_local(tmp_path: Path, extra: str = "") -> Path:
    p = tmp_path / "plugin.local.md"
    p.write_text(
        "---\n"
        "stack: python\n"
        "author: Test\n"
        "error_type: TestError\n"
        "verification_commands:\n"
        "  - pytest\n"
        "plan_path: planning/claude-plan-tdd.md\n"
        "plan_org_path: planning/claude-plan-tdd-org.md\n"
        "spec_base_path: sbtdd/spec-behavior-base.md\n"
        "spec_path: sbtdd/spec-behavior.md\n"
        "state_file_path: .claude/session-state.json\n"
        "magi_threshold: GO_WITH_CAVEATS\n"
        "magi_max_iterations: 3\n"
        "auto_magi_max_iterations: 5\n"
        "auto_verification_retries: 2\n"
        "auto_max_spec_review_seconds: 3600\n"
        "tdd_guard_enabled: true\n"
        "worktree_policy: optional\n"
        f"{extra}"
        "---\n# rules\n",
        encoding="utf-8",
    )
    return p


def test_v02_plugin_local_loads_with_model_fields_default_none(tmp_path):
    """E1.2: v0.2 plugin.local.md (no model fields) loads with defaults."""
    p = _write_minimal_plugin_local(tmp_path)
    cfg = load_plugin_local(p)
    assert cfg.implementer_model is None
    assert cfg.spec_reviewer_model is None
    assert cfg.code_review_model is None
    assert cfg.magi_dispatch_model is None
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_config_model_fields.py::test_v02_plugin_local_loads_with_model_fields_default_none -v
```
Expected: FAIL — `PluginConfig` lacks the 4 fields.

- [ ] **Step 3: Add 4 fields to PluginConfig dataclass**

Modify `skills/sbtdd/scripts/config.py` PluginConfig declaration:

```python
@dataclass(frozen=True)
class PluginConfig:
    """Parsed configuration from .claude/plugin.local.md (sec.S.4.2)."""

    stack: Literal["rust", "python", "cpp"]
    author: str
    error_type: str | None
    verification_commands: tuple[str, ...]
    plan_path: str
    plan_org_path: str
    spec_base_path: str
    spec_path: str
    state_file_path: str
    magi_threshold: Literal["STRONG_GO", "GO", "GO_WITH_CAVEATS"]
    magi_max_iterations: int
    auto_magi_max_iterations: int
    auto_verification_retries: int
    auto_max_spec_review_seconds: int
    tdd_guard_enabled: bool
    worktree_policy: Literal["optional", "required"]
    # v0.3.0 Feature E -- per-skill model selection (default None = inherit
    # session model, byte-identical argv to v0.2.x).
    implementer_model: str | None = None
    spec_reviewer_model: str | None = None
    code_review_model: str | None = None
    magi_dispatch_model: str | None = None
```

In `load_plugin_local`, after the existing validation, BEFORE building the dataclass instance, add:

```python
# v0.3.0 Feature E -- per-skill model fields (optional).
for field_name in (
    "implementer_model",
    "spec_reviewer_model",
    "code_review_model",
    "magi_dispatch_model",
):
    val = data.get(field_name)
    if val is not None and not isinstance(val, str):
        raise ValidationError(
            f"{field_name} must be a string or null, got {type(val).__name__}"
        )
```

Then ensure the `PluginConfig(...)` constructor at the bottom of the function passes these fields (or relies on the default None when missing). Use `data.get(field_name)` to default to None.

- [ ] **Step 4: Run test, verify PASS**

```bash
python -m pytest tests/test_config_model_fields.py -v
```

- [ ] **Step 5: Add E1.1 test (4 fields parsed when present)**

```python
def test_4_model_fields_parsed_from_plugin_local(tmp_path):
    """E1.1: all 4 model fields parsed when present in YAML."""
    extra = (
        "implementer_model: claude-sonnet-4-6\n"
        "spec_reviewer_model: claude-haiku-4-5\n"
        "code_review_model: claude-sonnet-4-6\n"
        "magi_dispatch_model: null\n"
    )
    p = _write_minimal_plugin_local(tmp_path, extra=extra)
    cfg = load_plugin_local(p)
    assert cfg.implementer_model == "claude-sonnet-4-6"
    assert cfg.spec_reviewer_model == "claude-haiku-4-5"
    assert cfg.code_review_model == "claude-sonnet-4-6"
    assert cfg.magi_dispatch_model is None
```

- [ ] **Step 6: Add E1.3 test (typo warning)**

```python
def test_typo_in_model_field_emits_warning(tmp_path, capfd):
    """E1.3: dash-typo'd YAML key triggers warning, defaults None."""
    extra = "implementer-model: claude-sonnet-4-6\n"
    p = _write_minimal_plugin_local(tmp_path, extra=extra)
    cfg = load_plugin_local(p)
    captured = capfd.readouterr()
    assert cfg.implementer_model is None
    assert "did you mean implementer_model" in captured.err
```

To make this pass, in `load_plugin_local` add a typo-detection pass after parsing YAML:

```python
_MODEL_FIELDS = (
    "implementer_model",
    "spec_reviewer_model",
    "code_review_model",
    "magi_dispatch_model",
)
for key in list(data.keys()):
    if "-" in key and key.replace("-", "_") in _MODEL_FIELDS:
        sys.stderr.write(
            f"[sbtdd] unknown plugin.local.md key: {key} -- did you mean "
            f"{key.replace('-', '_')}?\n"
        )
```

(Add `import sys` if missing.)

- [ ] **Step 7: make verify**

```bash
make verify
```

- [ ] **Step 8: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config_model_fields.py
git commit -m "feat: add 4 optional model fields to PluginConfig"
```

---

## Task E3: Dispatch wiring + INV-0 precedence

**Files:**
- Create: `tests/test_dispatch_model_arg.py`
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
- Modify: `skills/sbtdd/scripts/spec_review_dispatch.py`
- Modify: `skills/sbtdd/scripts/magi_dispatch.py`

- [ ] **Step 1: Failing test E3.1 (default null = byte-identical argv)**

```python
# tests/test_dispatch_model_arg.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E dispatch model arg propagation + INV-0."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import superpowers_dispatch


def test_dispatch_with_model_none_byte_identical_to_v02():
    """E3.1: default model=None preserves v0.2.x argv shape."""
    argv = superpowers_dispatch._build_skill_cmd(
        "test-driven-development", ["--phase=red"], model=None
    )
    assert argv == ["claude", "-p", "/test-driven-development --phase=red"]
    assert "--model" not in argv
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_dispatch_model_arg.py::test_dispatch_with_model_none_byte_identical_to_v02 -v
```
Expected: FAIL — `_build_skill_cmd` does not accept `model` kwarg.

- [ ] **Step 3: Extend `_build_skill_cmd` with model kwarg**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py`:

```python
def _build_skill_cmd(
    skill: str,
    args: list[str] | None,
    model: str | None = None,
) -> list[str]:
    """Build argv for ``claude -p`` invoking ``skill``, optionally with --model.

    When ``model`` is provided, ``--model <id>`` is inserted before the
    ``-p`` flag (claude CLI flag ordering convention). When ``model`` is
    None (default), argv is byte-identical to v0.2.x.
    """
    prompt_parts = [f"/{skill}"]
    if args:
        prompt_parts.extend(args)
    cmd = ["claude"]
    if model is not None:
        cmd.extend(["--model", model])
    cmd.extend(["-p", " ".join(prompt_parts)])
    return cmd
```

- [ ] **Step 4: Verify E3.1 passes**

- [ ] **Step 5: Add E3.2 test (--model injection)**

```python
def test_dispatch_with_model_injects_flag():
    """E3.2: model=claude-haiku-4-5 inserts --model BEFORE -p."""
    argv = superpowers_dispatch._build_skill_cmd(
        "test-driven-development", ["--phase=red"], model="claude-haiku-4-5"
    )
    assert argv == [
        "claude",
        "--model",
        "claude-haiku-4-5",
        "-p",
        "/test-driven-development --phase=red",
    ]
```

- [ ] **Step 6: Add E3.3 + E3.4 tests (INV-0 cascade)**

```python
def test_inv0_precedence_pinned_model_wins(tmp_path, capfd, monkeypatch):
    """E3.3: CLAUDE.md pinned model wins, breadcrumb emitted."""
    fake_home = tmp_path
    (fake_home / ".claude").mkdir()
    (fake_home / ".claude" / "CLAUDE.md").write_text(
        "Use claude-opus-4-7 for all sessions.\n"
    )
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    effective = superpowers_dispatch._apply_inv0_model_check(
        configured_model="claude-sonnet-4-6", skill_field_name="implementer_model"
    )
    captured = capfd.readouterr()
    assert effective is None  # config ignored
    assert "[sbtdd inv-0]" in captured.err
    assert "claude-opus-4-7" in captured.err
    assert "implementer_model=claude-sonnet-4-6" in captured.err


def test_inv0_no_pinned_model_config_respected(tmp_path, monkeypatch, capfd):
    """E3.4: when CLAUDE.md does not pin, configured model passes through."""
    fake_home = tmp_path
    (fake_home / ".claude").mkdir()
    (fake_home / ".claude" / "CLAUDE.md").write_text(
        "Code Standards. Prefer OOP. Use snake_case.\n"
    )
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    effective = superpowers_dispatch._apply_inv0_model_check(
        configured_model="claude-sonnet-4-6", skill_field_name="implementer_model"
    )
    captured = capfd.readouterr()
    assert effective == "claude-sonnet-4-6"
    assert "[sbtdd inv-0]" not in captured.err
```

- [ ] **Step 7: Implement `_apply_inv0_model_check`**

Add to `superpowers_dispatch.py`:

```python
from pathlib import Path
from models import INV_0_PINNED_MODEL_RE


def _apply_inv0_model_check(
    configured_model: str | None,
    skill_field_name: str,
) -> str | None:
    """Apply INV-0 cascade: if ~/.claude/CLAUDE.md pins a model, ignore config.

    Returns the *effective* model to pass to ``--model``, which is None
    when INV-0 fires (CLAUDE.md pinned a global model) and otherwise
    equals ``configured_model``. Emits stderr breadcrumb on the rare
    INV-0 path so operators see the cost implication.
    """
    if configured_model is None:
        return None
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    if not claude_md.exists():
        return configured_model
    try:
        text = claude_md.read_text(encoding="utf-8")
    except OSError:
        return configured_model
    match = INV_0_PINNED_MODEL_RE.search(text)
    if match is None:
        return configured_model
    pinned = match.group(1)
    sys.stderr.write(
        f"[sbtdd inv-0] CLAUDE.md pins {pinned} globally; ignoring "
        f"plugin.local.md {skill_field_name}={configured_model} to "
        f"respect global authority. Cost implication may differ from "
        f"configured baseline.\n"
    )
    return None
```

- [ ] **Step 8: Wire `model` kwarg into `invoke_skill`**

Update `invoke_skill` signature to accept `model: str | None = None`, applying the INV-0 check before `_build_skill_cmd`:

```python
def invoke_skill(
    skill: str,
    args: list[str] | None = None,
    timeout: int = 600,
    cwd: str | None = None,
    *,
    model: str | None = None,
    skill_field_name: str = "implementer_model",
) -> SkillResult:
    """Invoke a superpowers skill via ``claude -p`` subprocess.
    ...
    """
    effective_model = _apply_inv0_model_check(model, skill_field_name)
    cmd = _build_skill_cmd(skill, args, model=effective_model)
    # ... rest of existing implementation
```

- [ ] **Step 9: Mirror in spec_review_dispatch.py + magi_dispatch.py**

`spec_review_dispatch.dispatch_spec_reviewer` -- add `model: str | None = None` kwarg, apply same INV-0 check (with `skill_field_name="spec_reviewer_model"`), pass to underlying invoke_skill / claude argv build.

`magi_dispatch.dispatch_magi` -- add `model: str | None = None` kwarg with `skill_field_name="magi_dispatch_model"`, mirror logic in `_build_magi_cmd`.

- [ ] **Step 10: make verify**

```bash
make verify
```

- [ ] **Step 11: Commit**

```bash
git add skills/sbtdd/scripts/superpowers_dispatch.py skills/sbtdd/scripts/spec_review_dispatch.py skills/sbtdd/scripts/magi_dispatch.py tests/test_dispatch_model_arg.py
git commit -m "feat: thread model kwarg through dispatch modules with INV-0 cascade"
```

---

## Task E4: --model-override CLI flag on auto

**Files:**
- Create: `tests/test_cli_model_override.py`
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (CLI parser only — disjoint from track D)

- [ ] **Step 1: Failing tests E4.1, E4.2, E4.3, E4.5**

```python
# tests/test_cli_model_override.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E --model-override CLI flag on auto."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd
from errors import ValidationError


def test_model_override_valid_skill_accepts():
    """E4.1: implementer:claude-haiku-4-5 parses to {implementer: ...}."""
    result = auto_cmd._parse_model_overrides(["implementer:claude-haiku-4-5"])
    assert result == {"implementer": "claude-haiku-4-5"}


def test_model_override_invalid_skill_rejects():
    """E4.2: foo:claude-haiku-4-5 raises ValidationError exit 1."""
    with pytest.raises(ValidationError) as ei:
        auto_cmd._parse_model_overrides(["foo:claude-haiku-4-5"])
    assert "invalid --model-override skill name 'foo'" in str(ei.value)
    assert "implementer" in str(ei.value)
    assert "spec_reviewer" in str(ei.value)


def test_model_override_multi_flag_accumulates():
    """E4.3: multiple --model-override flags merge into one dict."""
    result = auto_cmd._parse_model_overrides([
        "implementer:claude-haiku-4-5",
        "spec_reviewer:claude-sonnet-4-6",
    ])
    assert result == {
        "implementer": "claude-haiku-4-5",
        "spec_reviewer": "claude-sonnet-4-6",
    }


def test_model_override_missing_separator_rejects():
    """E4.5: implementerhaiku4-5 (no colon) raises ValidationError."""
    with pytest.raises(ValidationError) as ei:
        auto_cmd._parse_model_overrides(["implementerhaiku4-5"])
    assert "expects '<skill>:<model>'" in str(ei.value)
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_cli_model_override.py -v
```

- [ ] **Step 3: Implement `_parse_model_overrides` in auto_cmd.py**

```python
_VALID_MODEL_OVERRIDE_SKILLS: frozenset[str] = frozenset(
    {"implementer", "spec_reviewer", "code_review", "magi_dispatch"}
)


def _parse_model_overrides(raw_values: list[str]) -> dict[str, str]:
    """Parse repeated --model-override <skill>:<model> CLI tokens.

    Returns a dict mapping skill name (one of the four canonical names)
    to model ID. Raises ValidationError on missing separator or unknown
    skill name; the dispatcher converts ValidationError to exit code 1.
    """
    out: dict[str, str] = {}
    for raw in raw_values:
        if ":" not in raw:
            raise ValidationError(
                f"--model-override expects '<skill>:<model>'; got {raw!r}"
            )
        skill, _, model = raw.partition(":")
        if skill not in _VALID_MODEL_OVERRIDE_SKILLS:
            raise ValidationError(
                f"invalid --model-override skill name {skill!r}. Valid: "
                f"{', '.join(sorted(_VALID_MODEL_OVERRIDE_SKILLS))}"
            )
        out[skill] = model
    return out
```

- [ ] **Step 4: Wire into `auto_cmd` argparse**

Locate the auto_cmd argparse setup (`build_parser` or equivalent). Add:

```python
parser.add_argument(
    "--model-override",
    action="append",
    default=[],
    metavar="<skill>:<model>",
    help=(
        "Override the per-skill model for this run only. Repeatable. "
        "Valid skill names: implementer, spec_reviewer, code_review, "
        "magi_dispatch. Cascade: CLAUDE.md > CLI override > "
        "plugin.local.md > None (inherit session)."
    ),
)
```

Then in the auto_cmd run function, immediately after parsing args:

```python
cli_overrides = _parse_model_overrides(args.model_override or [])
```

Threading the resulting dict through to the dispatch sites is left to track-E coordination — for v0.3.0 ship, populating the dict and passing it to a new helper `_resolve_model(skill, config, cli_overrides)` is sufficient. The helper picks CLI > config > None and is consumed at every dispatch site.

```python
def _resolve_model(
    skill: str,
    config: PluginConfig,
    cli_overrides: dict[str, str],
) -> str | None:
    """Resolve the effective configured model for a skill at dispatch time.

    Cascade: CLI override > plugin.local.md field > None. INV-0 (CLAUDE.md)
    is enforced downstream by the dispatch module's _apply_inv0_model_check.
    """
    if skill in cli_overrides:
        return cli_overrides[skill]
    field_map = {
        "implementer": config.implementer_model,
        "spec_reviewer": config.spec_reviewer_model,
        "code_review": config.code_review_model,
        "magi_dispatch": config.magi_dispatch_model,
    }
    return field_map.get(skill)
```

Apply at each dispatch site in `auto_cmd` (implementer subagent dispatch, spec_review dispatch, magi dispatch — already extended in E3 to accept the kwarg).

- [ ] **Step 5: make verify**

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_cli_model_override.py
git commit -m "feat: --model-override CLI flag on auto with cascade resolver"
```

---

## Task E5: dependency_check.check_model_ids

**Files:**
- Create: `tests/test_dependency_check_models.py`
- Modify: `skills/sbtdd/scripts/dependency_check.py`

- [ ] **Step 1: Failing tests**

```python
# tests/test_dependency_check_models.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E dependency_check.check_model_ids."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import dependency_check
from config import PluginConfig
from errors import ValidationError


def _cfg_with(implementer: str | None = None) -> PluginConfig:
    return PluginConfig(
        stack="python", author="t", error_type=None,
        verification_commands=("pytest",),
        plan_path="planning/claude-plan-tdd.md",
        plan_org_path="planning/claude-plan-tdd-org.md",
        spec_base_path="sbtdd/spec-behavior-base.md",
        spec_path="sbtdd/spec-behavior.md",
        state_file_path=".claude/session-state.json",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3, auto_magi_max_iterations=5,
        auto_verification_retries=2, auto_max_spec_review_seconds=3600,
        tdd_guard_enabled=True, worktree_policy="optional",
        implementer_model=implementer,
    )


def test_check_model_ids_warns_on_unknown_at_init():
    """E5.1: unknown model in PluginConfig returns DependencyCheck warning."""
    cfg = _cfg_with(implementer="claude-sonnet-9-9")
    result = dependency_check.check_model_ids(cfg)
    assert result.ok is True  # warning, not failure
    assert "claude-sonnet-9-9" in result.message
    assert "implementer_model" in result.message
    assert "verify spelling" in result.message.lower()


def test_check_model_ids_passes_on_known():
    """E5.1 inverse: known model returns ok DependencyCheck."""
    cfg = _cfg_with(implementer="claude-sonnet-4-6")
    result = dependency_check.check_model_ids(cfg)
    assert result.ok is True


def test_check_model_ids_passes_on_all_none():
    """E5.1 inverse: default-none config returns ok (no fields to check)."""
    cfg = _cfg_with(implementer=None)
    result = dependency_check.check_model_ids(cfg)
    assert result.ok is True
```

- [ ] **Step 2: Run, verify FAIL** (`check_model_ids` not defined).

- [ ] **Step 3: Implement `check_model_ids`**

In `dependency_check.py`, add:

```python
from models import ALLOWED_CLAUDE_MODEL_IDS


def check_model_ids(config: PluginConfig) -> DependencyCheck:
    """Validate non-null model fields against ALLOWED_CLAUDE_MODEL_IDS.

    v0.3.0 returns a non-fatal DependencyCheck with ``ok=True`` and a
    warning message when fields contain unknown IDs (so init does not
    abort -- field may legitimately be a freshly-released model the
    plugin's tuple does not yet recognize). Runtime dispatch is the
    hard-fail path: ``claude --model <unknown>`` errors and the
    surrounding subprocess wrapper raises ValidationError.
    """
    field_pairs: list[tuple[str, str | None]] = [
        ("implementer_model", config.implementer_model),
        ("spec_reviewer_model", config.spec_reviewer_model),
        ("code_review_model", config.code_review_model),
        ("magi_dispatch_model", config.magi_dispatch_model),
    ]
    unknown: list[str] = []
    for field, value in field_pairs:
        if value is not None and value not in ALLOWED_CLAUDE_MODEL_IDS:
            unknown.append(f"{field}={value}")
    if not unknown:
        return DependencyCheck(name="model_ids", ok=True, message="all model IDs recognized")
    msg = (
        f"[sbtdd init] unknown model IDs in plugin.local.md: "
        f"{'; '.join(unknown)}. Will hard-fail at runtime if Anthropic "
        f"does not recognize this ID. Verify spelling against the family "
        f"snapshot in models.ALLOWED_CLAUDE_MODEL_IDS."
    )
    return DependencyCheck(name="model_ids", ok=True, message=msg)
```

(Adapt to the actual `DependencyCheck` dataclass shape used by the existing code.)

- [ ] **Step 4: Wire into existing dependency-check aggregator**

Locate the function that runs all checks for `init` (the v0.2 enumerator that returns the consolidated report). Append `checks.append(check_model_ids(config))` after the existing checks.

- [ ] **Step 5: make verify + commit**

```bash
make verify
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check_models.py
git commit -m "feat: dependency_check.check_model_ids validates model field IDs"
```

---

## Task E7: Template ships Sonnet+Haiku baseline

**Files:**
- Modify: `templates/plugin.local.md.template`
- Modify: `tests/test_init_cmd.py` (existing — extend)

- [ ] **Step 1: Failing test E7.1**

In `tests/test_init_cmd.py`, add (after existing helper fixtures):

```python
def test_template_ships_sonnet_haiku_baseline_commented():
    """E7.1: template contains commented Sonnet+Haiku baseline block."""
    template = (
        Path(__file__).parent.parent / "templates" / "plugin.local.md.template"
    ).read_text(encoding="utf-8")
    assert "# Recommended cost-optimized baseline" in template
    assert "# implementer_model: claude-sonnet-4-6" in template
    assert "# spec_reviewer_model: claude-haiku-4-5" in template
    assert "# code_review_model: claude-sonnet-4-6" in template
    assert "# magi_dispatch_model: null" in template
```

- [ ] **Step 2: Run, verify FAIL**

```bash
python -m pytest tests/test_init_cmd.py::test_template_ships_sonnet_haiku_baseline_commented -v
```

- [ ] **Step 3: Append commented baseline to template**

In `templates/plugin.local.md.template`, append (inside the YAML frontmatter, after `worktree_policy:` line):

```yaml
# Recommended cost-optimized baseline (uncomment to opt in; v0.3.0+).
# Default null preserves session-model inheritance (v0.2.x behavior).
# Cost ratio: Opus 4.7 ~= 5x Sonnet 4.6 ~= 15-20x Haiku 4.5.
# implementer_model: claude-sonnet-4-6
# spec_reviewer_model: claude-haiku-4-5
# code_review_model: claude-sonnet-4-6
# magi_dispatch_model: null   # outer dispatcher; sub-agents pick own
```

- [ ] **Step 4: Run, verify PASS**

- [ ] **Step 5: Add E7.2 test (template renders preserving comments)**

```python
def test_init_python_stack_preserves_template_baseline_comments(tmp_path, monkeypatch):
    """E7.2: init --stack python output preserves the 4 commented model lines."""
    # ... existing init invocation pattern ...
    # After running init, read the generated plugin.local.md and assert all 4
    # commented lines present.
    plugin_local = tmp_path / ".claude" / "plugin.local.md"
    text = plugin_local.read_text(encoding="utf-8")
    assert "# implementer_model: claude-sonnet-4-6" in text
    assert "# spec_reviewer_model: claude-haiku-4-5" in text
    assert "# code_review_model: claude-sonnet-4-6" in text
    assert "# magi_dispatch_model: null" in text
```

(Adapt to the existing init test fixture pattern.)

- [ ] **Step 6: Verify the existing template-expansion path preserves comments**

`templates.py` substitution must NOT strip YAML comments. If the existing implementation already preserves them (likely — template is mostly verbatim), no code change needed; if it strips, fix the substitution to be line-preserving.

- [ ] **Step 7: make verify + commit**

```bash
make verify
git add templates/plugin.local.md.template tests/test_init_cmd.py
git commit -m "feat: ship commented Sonnet+Haiku baseline in plugin.local.md template"
```

---

## Track E — done criteria

- [ ] All 6 test files pass (test_models_constants, test_config_model_fields, test_dispatch_model_arg, test_cli_model_override, test_dependency_check_models, test_init_cmd extension).
- [ ] 6 atomic commits landed: E6 → E1 → E3 → E4 → E5 → E7.
- [ ] `make verify` clean.
- [ ] Default null = byte-identical argv regression preserved (E3.1 pinned).
- [ ] INV-0 cascade: CLAUDE.md scan + breadcrumb verified.
- [ ] Subagent #2 reports DONE with commit SHA range to orchestrator.

---

# Final review phase (orchestrator-driven)

After both subagents report DONE:

## Task F1: Pre-loop hygiene

- [ ] **Step 1: Verify working tree clean**

```bash
cd D:/jbolivarg/PythonProjects/SBTDD
git status
```
Expected: `working tree clean`. If not, identify untracked / unstaged changes and either commit or discard before proceeding.

- [ ] **Step 2: Run make verify (Loop 1 surrogate per spec sec.4.4)**

```bash
make verify
```
Expected: 4 checks PASS — pytest (785-805 tests), ruff check, ruff format --check, mypy --strict. If any check fails, identify which subagent's commits caused the regression and dispatch a fix subagent before proceeding.

- [ ] **Step 3: Compute the diff range for MAGI input**

```bash
git log --oneline cfb39ee..HEAD
git diff cfb39ee..HEAD --stat
```
Expected: ~10 commits (4 from track D + 6 from track E), ~10 files changed.

## Task F2: MAGI ↔ /receiving-code-review loop (cap 5 iter)

For each iteration `iter ∈ {1..5}`:

- [ ] **Step 1: Invoke MAGI on the diff**

Invoke `/magi:magi` with prompt: `revisa el diff v0.2.2..HEAD del plugin sbtdd-workflow contra @sbtdd/spec-behavior.md y @planning/claude-plan-tdd-org.md. Foco: regression risk, INV-0/INV-22/INV-29 compliance, atomic-write correctness, default-null backward compat.`

- [ ] **Step 2: Parse verdict + findings**

Read MAGI's verdict JSON. Extract:
- `verdict` ∈ {STRONG_NO_GO, HOLD, HOLD_TIE, GO_WITH_CAVEATS, GO, STRONG_GO}.
- `degraded: bool`.
- Findings list with severity {CRITICAL, WARNING, INFO}.
- Conditions for Approval list.

- [ ] **Step 3: Evaluate exit criterion**

Exit IF and ONLY IF (all true):
- `verdict ≥ GO_WITH_CAVEATS` (in VERDICT_RANK ordering).
- `degraded == False` (per INV-28).
- 0 findings with severity CRITICAL.
- 0 findings with severity WARNING.
- 0 Conditions for Approval pending.

Otherwise: continue loop (step 4).

- [ ] **Step 4: Route findings via /receiving-code-review (INV-29 gate)**

For EACH finding (CRITICAL + WARNING) and EACH Condition for Approval:
- Invoke `/receiving-code-review` with the finding text + diff + project context.
- It returns ACCEPT or REJECT with rationale.
- ACCEPT → proceed to mini-cycle TDD fix (step 5) for that finding.
- REJECT → log the rejection rationale to `.claude/magi-rejections-iterN.md` and feed it as context into the NEXT MAGI invocation (sterile-loop prevention per scenario R1.6).

- [ ] **Step 5: Mini-cycle TDD per accepted finding**

Dispatch a subagent (#3-iter1, #3-iter2, ...) per accepted finding. Each subagent:
- **Red**: write a regression test reproducing the finding. Commit `test: regression for [finding summary]`.
- **Green**: implement the fix. Commit `fix: [finding summary]`.
- **Refactor**: pulir if needed. Commit `refactor: [finding summary]` (skip if no cleanup).
- Each commit verified by `make verify`.

- [ ] **Step 6: Verify post-fix**

```bash
make verify
```
Expected: PASS. If FAIL, the mini-cycle subagent did not converge — inspect its commits, re-dispatch or escalate.

- [ ] **Step 7: Increment iter counter; loop to step 1**

If `iter == 5` and exit criterion still not met: trigger escalation_prompt (Task F3 below).

## Task F3: Escalation on cap exhaustion (only if F2 cap hit)

- [ ] **Step 1: Invoke escalation_prompt**

Manually run:
```bash
python skills/sbtdd/scripts/escalation_prompt.py --context pre-merge --iter 5 --plan planning/claude-plan-tdd-org.md
```
(Or call the function from a Python REPL with an `EscalationContext` constructed from the iter-5 MAGI verdict.)

- [ ] **Step 2: Choose option a/b/c/d**

Per Feature A v0.2.0 contract:
- (a) override INV-0 with `--reason "<text>"` mandatory → audit artifact written, ship proceeds.
- (b) retry +1 iter (extends cap to 6).
- (c) replan: revisit spec or task decomposition (worst case; would mean v0.3.0 scope was wrong).
- (d) abort (default headless).

- [ ] **Step 3: Apply chosen action**

- (a): write `.claude/magi-escalations/<timestamp>-v030.json` with reason + verdict + findings, then ship.
- (b): re-enter F2 loop with `iter=6`.
- (c): hard-stop, return to brainstorming.
- (d): exit 8 (MAGI_GATE_BLOCKED), v0.3.0 not shipped this session.

## Task F4: Ship (only after F2 exit OR F3 option a)

- [ ] **Step 1: Bump version 0.2.2 → 0.3.0**

In `.claude-plugin/plugin.json`:
```json
  "version": "0.3.0",
```

In `.claude-plugin/marketplace.json` (TWO occurrences — top-level and inside the plugins array):
```json
  "version": "0.3.0",
```

- [ ] **Step 2: Write CHANGELOG.md `[0.3.0]` entry**

Insert above `[0.2.2]`:

```markdown
## [0.3.0] - 2026-04-25

### Added

- Feature D — Auto progress streaming. `auto_cmd._stream_subprocess`
  reads subprocess pipes line-by-line via thread-pair pump and
  rewrites to orchestrator stderr with `[sbtdd task-N phase] `
  prefix. Subprocess argv prefixed with `python -u` to disable
  buffering at the dispatcher level. State-machine breadcrumbs
  emitted at every phase / sub-phase / task transition. New
  `progress` field in `auto-run.json` reflects current `{phase,
  task_index, task_total, sub_phase}` and is rewritten atomically
  via tmp + os.replace (mirrors state_file.save and
  magi-escalation-pending.md atomic-write patterns). 7 new tests
  across `tests/test_auto_streaming.py` + `tests/test_auto_progress.py`.

- Feature E — Per-skill model selection flag. `PluginConfig` gains
  four optional fields (`implementer_model`, `spec_reviewer_model`,
  `code_review_model`, `magi_dispatch_model`), all defaulting null
  (= inherit session model, byte-identical to v0.2.x argv). When
  non-null, dispatch modules append `--model <id>` to the argv. CLI
  flag `--model-override <skill>:<model>` on `/sbtdd auto` provides
  per-run overrides; cascade is CLAUDE.md > CLI > plugin.local.md
  > None. INV-0 enforced via regex scan of `~/.claude/CLAUDE.md`;
  pinned model globally always wins, with stderr breadcrumb.
  `dependency_check.check_model_ids` validates against
  `models.ALLOWED_CLAUDE_MODEL_IDS` (Opus 4.7, Sonnet 4.6, Haiku
  4.5 family). `templates/plugin.local.md.template` ships commented
  Sonnet+Haiku baseline as recommended cost-optimized opt-in.

### Process notes

- Loop 1 (`/requesting-code-review`) skipped for v0.3.0 ship in
  favor of `make verify` surrogate -- pytest + ruff check + ruff
  format + mypy --strict served as the mechanical-findings detector
  in this lightweight cycle. INV-9 honored via interpretive
  shortcut (clean linting = clean Loop 1). Final review loop ran
  MAGI -> /receiving-code-review until verdict GO_WITH_CAVEATS
  full with zero CRITICAL + zero WARNING + zero Conditions
  pending, capped at 5 iterations per user directive 2026-04-25.

### Deferred (rolled to v0.4.0 / v1.0.0)

- D5 `/sbtdd status --watch` subcommand (deferred to v0.4.0).
- E2 `schema_version: 2` field in `plugin.local.md` (deferred to v1.0.0).
- Features F (MAGI marker discovery + `retried_agents`), G (MAGI
  cross-check via /requesting-code-review), H (Group B spec-drift
  re-eval + INV-31 default-on opt-in re-eval) (all v1.0.0).
```

- [ ] **Step 3: Update README.md**

Add new section after `### New in v0.2`:

```markdown
### Cost optimization (v0.3.0+)

`plugin.local.md` accepts four optional model fields letting you
downgrade per-skill subprocess models without changing your session
default. Recommended baseline (commented in the template; uncomment
to opt in):

| Field | Recommended | Why |
|-------|-------------|-----|
| `implementer_model` | `claude-sonnet-4-6` | TDD code-gen + multi-file refactors. Haiku breaks invariants. |
| `spec_reviewer_model` | `claude-haiku-4-5` | Pattern-match task; cheapest tier where capability suffices. |
| `code_review_model` | `claude-sonnet-4-6` | Bug/security/style detection needs depth. |
| `magi_dispatch_model` | `null` (inherit) | Outer dispatcher; sub-agents pick their own model. |

Per-run override: `/sbtdd auto --model-override implementer:claude-haiku-4-5`.

INV-0 cascade: `~/.claude/CLAUDE.md` pinned model always wins. Stderr
breadcrumb fires when override is suppressed.

Cost projection: 36-task `auto` run on default-Opus session vs
Sonnet+Haiku mix = ~70-80% reduction in total bill, preserving Opus
only in MAGI Loop 2 iterations.
```

- [ ] **Step 4: Update SKILL.md**

After `### v0.2 flags` section, add `### v0.3 flags`:

```markdown
### v0.3 flags

- `--model-override <skill>:<model>` (on `auto`) -- per-run model override
  for one of the four canonical skills (`implementer`, `spec_reviewer`,
  `code_review`, `magi_dispatch`). Repeatable. Cascade: CLAUDE.md >
  CLI override > plugin.local.md > None (inherit session). INV-0
  pinned model in `~/.claude/CLAUDE.md` always wins; stderr breadcrumb
  fires when the override is suppressed.
- Four optional fields in `plugin.local.md` (`implementer_model`,
  `spec_reviewer_model`, `code_review_model`, `magi_dispatch_model`)
  with default `null` (= inherit session). Recommended baseline
  shipped commented in the template for cost optimization.
```

- [ ] **Step 5: Run final make verify**

```bash
make verify
```

- [ ] **Step 6: Stage docs + commit**

```bash
git add README.md skills/sbtdd/SKILL.md CHANGELOG.md
git commit -m "docs: v0.3.0 changelog + cost-optimization README + SKILL flags"
```

- [ ] **Step 7: Bump version commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump to 0.3.0"
```

- [ ] **Step 8: Tag**

```bash
git tag v0.3.0
git log --oneline -15
```
Expected: clean linear history with the 10 feature commits + docs commit + chore bump + tag.

- [ ] **Step 9: Push (REQUIRES EXPLICIT USER AUTHORIZATION)**

DO NOT auto-execute. Surface to user: "v0.3.0 ready to push. Authorize `git push origin main && git push origin v0.3.0`?"

- [ ] **Step 10: Memory update**

Write `C:/Users/jbolivarg/.claude/projects/D--jbolivarg-PythonProjects-SBTDD/memory/project_v030_shipped.md` covering: 10 deliverables landed, lightweight pattern wall time, MAGI loop iter count, any INV-0 override, ship commit + tag SHAs.

Update `MEMORY.md` index with one-line v0.3.0 hook entry.

---

## Self-review

After writing the plan above, the following spec coverage map verifies every spec.S.12 / sec.6 acceptance criterion has at least one task:

| Spec criterion | Task | Coverage |
|----------------|------|----------|
| D1 | Task D1 | Steps 1-9 (3 streaming tests + impl) |
| D2 | Task D2 | Steps 1-5 (argv test + impl) |
| D3 | Task D3 | Steps 1-8 (2 breadcrumb tests + impl + wiring) |
| D4 | Task D4 | Steps 1-10 (3 progress tests + impl + wiring) |
| E1 | Task E1 | Steps 1-8 (3 config tests + dataclass extension) |
| E3 | Task E3 | Steps 1-11 (4 dispatch tests + 3 modules wired + INV-0) |
| E4 | Task E4 | Steps 1-6 (4 CLI tests + parser + cascade resolver) |
| E5 | Task E5 | Steps 1-5 (3 dependency_check tests + impl) |
| E6 | Task E6 | Steps 1-5 (2 immutability/contents tests + constants) |
| E7 | Task E7 | Steps 1-7 (2 template tests + edit) |
| R1.1 | Task F2 step 3 | Exit criterion check |
| R1.2 | Task F2 step 4-5 | INV-29 routing + mini-cycle |
| R1.3 | Task F2 step 4-5 | Same path for WARNING/Conditions |
| R1.4 | Task F2 step 3 (degraded sub-condition) | INV-28 honored |
| R1.5 | Task F3 | Escalation prompt invocation |
| R1.6 | Task F2 step 4 | Rejected findings logged + fed back |
| R1.7 | Task F1 step 2 + Task F2 step 1 | make verify Loop 1 surrogate |
| Version bump | Task F4 step 1 | plugin.json + marketplace.json sync |
| CHANGELOG | Task F4 step 2 | [0.3.0] section template |
| README + SKILL | Task F4 steps 3-4 | Cost optimization + v0.3 flags |
| Tag + push | Task F4 steps 8-9 | Manual user-authorized push |
| Memory | Task F4 step 10 | project_v030_shipped.md |

**Placeholder scan**: zero `TODO`, `TBD`, `implement later`, `add appropriate error handling`, `similar to Task N` matches.

**Type consistency**: function names verified across tasks — `_stream_subprocess` (D1), `_build_run_sbtdd_argv` (D2), `_emit_phase_breadcrumb` (D3), `_update_progress` (D4), `PluginConfig` field names match across E1/E3/E4/E5, `_apply_inv0_model_check` consistent across superpowers/spec_review/magi dispatch, `_parse_model_overrides` + `_resolve_model` + `_VALID_MODEL_OVERRIDE_SKILLS` consistent within track E.

**Scope check**: plan focused on D + E for v0.3.0. F+G+H + D5/E2 explicitly deferred and not referenced in tasks.

---

## Execution handoff

Plan complete and saved to `planning/claude-plan-tdd-org.md`.

Two execution options:

**1. Subagent-Driven (recommended)** — orchestrator dispatches subagent #1 + subagent #2 in parallel for tracks D+E, then drives the final review loop sequentially. Two-stage review between tasks. Fresh subagent per finding mini-cycle.

**2. Inline Execution** — execute tasks D1-D4, E6-E7 inline in this session via executing-plans skill. Slower (~6-8h vs 4-5h parallel) but every step auditable in conversation. Loses parallelism advantage of lightweight pattern.

Recommended: **option 1**. Tracks D and E are file-disjoint by design and the lightweight pattern v0.2.1 precedent validated parallel-subagent dispatch for similar scope.

Which approach?
