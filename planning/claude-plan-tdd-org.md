# v0.5.0 Observability Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the v0.5.0 observability pillar (heartbeat in-band emitter + `/sbtdd status --watch` companion + per-stream timeout J3 + origin disambiguation J7) plus three v0.4.1 doc-alignment hotfixes folded in. Closes the empirical UX gap where MAGI/code-review subprocess dispatches (5-10 min) make the auto run "look dead" with no operator visibility.

**Architecture:** True parallel 2-subagent dispatch with surfaces 100% disjoint per spec sec.4.2/4.3.

- **Subagent #1 — Heartbeat track:** owns `models.py` (+ ProgressContext), new `scripts/heartbeat.py` module (HeartbeatEmitter + Lock-protected singleton + queue-based reporting), `auto_cmd.py` (writer hooks + dispatch wrapping). Forbidden surfaces: `status_cmd.py`, streaming pump in `subprocess_utils.py`, CHANGELOG.md, SKILL.md.
- **Subagent #2 — Streaming + watch + docs track:** owns `subprocess_utils.py` streaming pump (per-stream timeout + origin disambiguation), `status_cmd.py` (--watch + helpers), `run_sbtdd.py` (argv), `config.py` (5 new fields + INV-34 validation), CHANGELOG.md (`[0.5.0]` + v0.4.1 hotfix sections), SKILL.md (--watch docs + v0.4.1 corrections), CLAUDE.md (release notes pointer), new `docs/v0.5.0-config-matrix.md` (R9 single-source matrix). Forbidden surfaces: `models.py`, `auto_cmd.py`, `scripts/heartbeat.py`.

Cross-subagent contract: ProgressContext schema pinned in spec sec.3. Both subagents implement against the contract; zero runtime code coupling.

**Tech Stack:** Python 3.9+, threading + queue + dataclasses + selectors + fnmatch (stdlib only on hot paths), pytest, pytest-asyncio (already in dev deps), ruff, mypy --strict.

---

## Pre-flight contracts (read-only reference for both subagents)

### Branch + working tree

- Branch: `feature/v0.5.0-observability` (already created, checked out).
- main is ahead of origin by 2 commits: `b4a37d6` (MAGI gate alignment + template + patch artifact) + `4538914` (v0.5.0 BDD overlay spec). The dev branch forks from `4538914`.
- Implementation commits land on the dev branch; merge to main only after pre-merge gate passes.
- Working tree must be clean before each task starts. Verify via `git status` returns empty.

### ProgressContext schema (sec.3 of spec)

Frozen dataclass with these fields:

```python
@dataclass(frozen=True)
class ProgressContext:
    iter_num: int = 0
    phase: int = 0
    task_index: int | None = None
    task_total: int | None = None
    dispatch_label: str | None = None
    started_at: datetime | None = None
```

`started_at` is the **dispatch start** (per spec sec.3 PINNED post-iter 3); not the phase start, not the auto-run start.

Serialized to `auto-run.json` under `progress` key with ISO 8601 UTC datetime (`Z` suffix).

### Five new PluginConfig fields (sec.4.3)

```python
auto_per_stream_timeout_seconds: int = 900
auto_heartbeat_interval_seconds: int = 15
status_watch_default_interval_seconds: float = 1.0
auto_origin_disambiguation: bool = True
auto_no_timeout_dispatch_labels: tuple[str, ...] = ("magi-*",)  # default via field()
```

INV-34 validation (4 clauses, each with distinct error message):
- Clause 1: `auto_per_stream_timeout_seconds >= 5 * auto_heartbeat_interval_seconds`
- Clause 2: `auto_heartbeat_interval_seconds <= 60`
- Clause 3: `auto_heartbeat_interval_seconds >= 5`
- Clause 4: `auto_per_stream_timeout_seconds >= 600` (absolute timeout floor — protects caspar opus runs)

### Three new invariants

- **INV-32**: heartbeat thread NO debe matar/bloquear el auto run; first-failure stderr breadcrumb + queue-reported counter to main thread for incremental auto-run.json persistence.
- **INV-33**: per-stream timeout es last-resort kill (heartbeat 1st-line, watch 2nd-line, timeout 3rd-line, operator intervention 4th).
- **INV-34**: timeout-vs-interval relationship + absolute floor + ceiling validations as above.

### Single-writer rule auto-run.json

ONLY the main thread writes. Heartbeat thread reports `_failed_writes` counter via thread-safe queue (`_heartbeat_failures_q`); main thread drains and persists. No race possible.

### Forbidden cross-subagent surfaces (recap)

| Subagent | OWNS | FORBIDDEN |
|----------|------|-----------|
| #1 Heartbeat | `models.py`, new `scripts/heartbeat.py`, `auto_cmd.py`, `tests/test_models.py` (extend), `tests/test_heartbeat.py` (NEW), `tests/test_heartbeat_smoke.py` (NEW), `tests/test_auto_progress.py` (extend) | `status_cmd.py`, `subprocess_utils.py`, `run_sbtdd.py`, `config.py`, CHANGELOG.md, SKILL.md, CLAUDE.md, `docs/v0.5.0-config-matrix.md` |
| #2 Streaming/Watch/Docs | `subprocess_utils.py`, `status_cmd.py`, `run_sbtdd.py`, `config.py`, CHANGELOG.md, SKILL.md, CLAUDE.md, new `docs/v0.5.0-config-matrix.md`, `tests/test_subprocess_utils.py` (extend), `tests/test_status_watch.py` (NEW), `tests/test_config.py` (extend), `tests/test_changelog.py` (extend), `tests/test_skill_md.py` (extend) | `models.py`, `auto_cmd.py`, `scripts/heartbeat.py` |

### Verification commands (after each TDD phase)

```bash
pytest tests/ -v                    # All pass
ruff check .                        # 0 warnings
ruff format --check .               # Clean
mypy . --strict                     # 0 errors
```

Shortcut: `make verify`.

### Commit prefixes (sec.5 commit policy)

| Phase | Prefix |
|-------|--------|
| Red (test) | `test:` |
| Green (impl) | `feat:` (new feature) or `fix:` (bug fix) |
| Refactor (cleanup) | `refactor:` |
| Task close (chore) | `chore:` |

---

## Subagent #1 — Heartbeat track (13 tasks)

### Task S1-1: Add ProgressContext dataclass to models.py

**Files:**
- Modify: `skills/sbtdd/scripts/models.py` (append)
- Modify: `tests/test_models.py` (append)

- [ ] **Step 1: Write failing test for ProgressContext immutability + defaults**

Append to `tests/test_models.py`:

```python
from datetime import datetime, timezone
from dataclasses import FrozenInstanceError
import pytest

from models import ProgressContext


def test_progress_context_default_construction_uses_zero_and_none():
    ctx = ProgressContext()
    assert ctx.iter_num == 0
    assert ctx.phase == 0
    assert ctx.task_index is None
    assert ctx.task_total is None
    assert ctx.dispatch_label is None
    assert ctx.started_at is None


def test_progress_context_full_construction_preserves_fields():
    ts = datetime(2026, 5, 1, 12, 34, 56, tzinfo=timezone.utc)
    ctx = ProgressContext(
        iter_num=2, phase=3, task_index=14, task_total=36,
        dispatch_label="magi-loop2-iter2", started_at=ts,
    )
    assert (ctx.iter_num, ctx.phase, ctx.task_index, ctx.task_total) == (2, 3, 14, 36)
    assert ctx.dispatch_label == "magi-loop2-iter2"
    assert ctx.started_at == ts


def test_progress_context_is_frozen():
    ctx = ProgressContext()
    with pytest.raises(FrozenInstanceError):
        ctx.iter_num = 5  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py::test_progress_context_default_construction_uses_zero_and_none -v
```

Expected: `ImportError: cannot import name 'ProgressContext' from 'models'`.

- [ ] **Step 3: Append ProgressContext dataclass to models.py**

Add at top of `skills/sbtdd/scripts/models.py` (after the existing `from __future__ import annotations`):

```python
from dataclasses import dataclass
from datetime import datetime
```

Append at end of `models.py`:

```python
@dataclass(frozen=True)
class ProgressContext:
    """Immutable snapshot of auto-run progress (sec.3 of v0.5.0 spec).

    Reader/writer protocol pinned in spec sec.3:
    - Writer (auto_cmd) creates a NEW ProgressContext per phase/task/dispatch
      transition and assigns to the module-level singleton via the
      lock-protected setter in :mod:`heartbeat`.
    - Reader (HeartbeatEmitter daemon thread) calls
      :func:`heartbeat.get_current_progress` to read; the returned snapshot
      is immutable so no further locking needed.

    The ``started_at`` field tracks the **current dispatch's** start time,
    NOT the phase start nor the overall auto-run start. Heartbeat ticks
    show ``elapsed=`` relative to this dispatch.

    Serialization to ``auto-run.json`` uses ISO 8601 UTC with the ``Z``
    suffix (e.g., ``"2026-05-01T12:34:56Z"``).
    """

    iter_num: int = 0
    phase: int = 0
    task_index: int | None = None
    task_total: int | None = None
    dispatch_label: str | None = None
    started_at: datetime | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_models.py -v
ruff check skills/sbtdd/scripts/models.py
mypy skills/sbtdd/scripts/models.py --strict
```

Expected: all pass, 0 warnings, 0 type errors.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/models.py tests/test_models.py
git commit -m "test: add ProgressContext immutable dataclass for heartbeat snapshots"
```

(Combined Red+Green commit acceptable for scaffolding; subsequent tasks split.)

---

### Task S1-2: Create scripts/heartbeat.py module skeleton with Lock-protected singleton

**Files:**
- Create: `skills/sbtdd/scripts/heartbeat.py`
- Create: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing test for getter/setter contract**

Create `tests/test_heartbeat.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-01
"""Unit tests for the v0.5.0 heartbeat module."""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta

import pytest

from heartbeat import (
    get_current_progress,
    set_current_progress,
    reset_current_progress,
    HeartbeatEmitter,
)
from models import ProgressContext


@pytest.fixture(autouse=True)
def _reset_progress():
    reset_current_progress()
    yield
    reset_current_progress()


def test_get_current_progress_initial_is_default_progress():
    assert get_current_progress() == ProgressContext()


def test_set_then_get_returns_same_reference():
    new_ctx = ProgressContext(iter_num=2, phase=3)
    set_current_progress(new_ctx)
    assert get_current_progress() is new_ctx


def test_repeated_set_replaces_singleton():
    set_current_progress(ProgressContext(iter_num=1))
    set_current_progress(ProgressContext(iter_num=2))
    assert get_current_progress().iter_num == 2


def test_reset_returns_default_after_set():
    set_current_progress(ProgressContext(iter_num=99))
    reset_current_progress()
    assert get_current_progress() == ProgressContext()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_heartbeat.py -v
```

Expected: `ImportError: No module named 'heartbeat'`.

- [ ] **Step 3: Create scripts/heartbeat.py with Lock-protected getter/setter**

Create `skills/sbtdd/scripts/heartbeat.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-01
"""HeartbeatEmitter and ProgressContext singleton for v0.5.0 observability.

Concurrency model (PINNED per spec sec.3):
- Module-level ``_current_progress`` reference, protected by
  ``_progress_lock: threading.Lock``.
- Writer (``auto_cmd`` main thread) calls :func:`set_current_progress`.
- Reader (HeartbeatEmitter daemon thread) calls :func:`get_current_progress`;
  operates on the immutable snapshot WITHOUT further locking.

The lock is forward-defensive against PEP 703 free-threaded Python and
maintainer drift; the immutable ``ProgressContext`` plus pointer
assignment is correct on current CPython but depends on memory model
implementation detail that the lock approach avoids.
"""

from __future__ import annotations

import queue
import sys
import threading
from datetime import datetime, timezone
from typing import Any

from models import ProgressContext

_progress_lock = threading.Lock()
_current_progress: ProgressContext = ProgressContext()


def get_current_progress() -> ProgressContext:
    """Return the current ProgressContext singleton (lock-protected)."""
    with _progress_lock:
        return _current_progress


def set_current_progress(new_ctx: ProgressContext) -> None:
    """Replace the current ProgressContext singleton (lock-protected)."""
    global _current_progress
    with _progress_lock:
        _current_progress = new_ctx


def reset_current_progress() -> None:
    """Reset the singleton to its default value. Test-only helper."""
    set_current_progress(ProgressContext())


# HeartbeatEmitter is added in S1-3.
class HeartbeatEmitter:
    pass  # placeholder; replaced in S1-3
```

- [ ] **Step 4: Run tests to verify pass**

```bash
pytest tests/test_heartbeat.py -k "current_progress or repeated_set or reset" -v
ruff check skills/sbtdd/scripts/heartbeat.py
mypy skills/sbtdd/scripts/heartbeat.py --strict
```

Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: add scripts/heartbeat.py with lock-protected ProgressContext singleton"
```

---

### Task S1-3: HeartbeatEmitter context manager scaffold

**Files:**
- Modify: `skills/sbtdd/scripts/heartbeat.py`
- Modify: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing test for context manager protocol**

Append to `tests/test_heartbeat.py`:

```python
def test_heartbeat_emitter_context_manager_protocol():
    emitter = HeartbeatEmitter(label="test-dispatch", interval_seconds=15)
    assert emitter.label == "test-dispatch"
    assert emitter.interval_seconds == 15
    with emitter as e:
        assert e is emitter


def test_heartbeat_emitter_validates_interval_positive():
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        HeartbeatEmitter(label="x", interval_seconds=0)
    with pytest.raises(ValueError, match="interval_seconds must be > 0"):
        HeartbeatEmitter(label="x", interval_seconds=-1)
```

- [ ] **Step 2: Run + verify fail**

```bash
pytest tests/test_heartbeat.py::test_heartbeat_emitter_context_manager_protocol -v
```

Expected: fail (placeholder class has no `__init__`).

- [ ] **Step 3: Replace placeholder with full HeartbeatEmitter scaffold**

Replace the `class HeartbeatEmitter: pass` placeholder in `heartbeat.py`:

```python
class HeartbeatEmitter:
    """Context manager that emits stderr ticks every ``interval_seconds``.

    Wraps long subprocess dispatches (MAGI Loop 2, /requesting-code-review,
    spec-reviewer) so the operator sees periodic liveness signals on
    stderr while the dispatch's own stdout/stderr is quiet.
    """

    # Class-level zombie counter (Checkpoint 2 iter 3 caspar CRITICAL fix):
    # tracks heartbeat threads that survived __exit__'s 2s join timeout.
    _zombie_thread_count: int = 0

    def __init__(
        self,
        label: str,
        interval_seconds: float = 15.0,
        failures_queue: "queue.Queue[int] | None" = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(
                f"interval_seconds must be > 0, got {interval_seconds!r}"
            )
        self.label = label
        self.interval_seconds = interval_seconds
        self._failures_queue = failures_queue
        self._failed_writes = 0
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "HeartbeatEmitter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_heartbeat.py -v
mypy skills/sbtdd/scripts/heartbeat.py --strict
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: add HeartbeatEmitter context manager scaffold (no thread yet)"
```

---

### Task S1-4: Daemon thread + threading.Event tick loop

**Files:**
- Modify: `skills/sbtdd/scripts/heartbeat.py`
- Modify: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing tests for tick emission + Event-interruptible exit**

Append to `tests/test_heartbeat.py`:

```python
def test_heartbeat_thread_emits_ticks_during_active_lifetime(capsys):
    set_current_progress(
        ProgressContext(
            iter_num=2, phase=3, task_index=14, task_total=36,
            dispatch_label="test-dispatch",
            started_at=datetime.now(timezone.utc),
        )
    )
    with HeartbeatEmitter(label="test-dispatch", interval_seconds=0.05):
        time.sleep(0.18)  # ~3 ticks at 50ms cadence
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines()
        if line.startswith("[sbtdd auto] tick:")
    ]
    assert len(tick_lines) >= 2


def test_heartbeat_exit_join_returns_within_timeout_when_thread_sleeping():
    """Verify Event.wait() (NOT time.sleep) so __exit__ can interrupt mid-tick."""
    emitter = HeartbeatEmitter(label="x", interval_seconds=10.0)
    t0 = time.monotonic()
    with emitter:
        time.sleep(0.1)
    t1 = time.monotonic()
    assert t1 - t0 < 2.5, (
        f"exit took {t1-t0:.2f}s; thread loop is using time.sleep instead of "
        f"threading.Event.wait()"
    )
```

- [ ] **Step 2: Run + verify fail**

Expected: both fail (no thread yet).

- [ ] **Step 3: Implement daemon thread with Event-interruptible wait**

Replace `__enter__` and `__exit__` and add `_tick_loop` + `_emit_tick` + `_format_tick` in `HeartbeatEmitter`:

```python
    def __enter__(self) -> "HeartbeatEmitter":
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._tick_loop,
            name=f"heartbeat-{self.label}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        return None

    def _tick_loop(self) -> None:
        """Emit a stderr tick every interval until _stop_event is set.

        Per Checkpoint 2 iter 1 caspar fix: check `_stop_event.is_set()` BEFORE
        each emit_tick to avoid the daemon-thread-outlives-context-manager race
        where the thread is between `wait()` returns (stop signaled) and the
        next iteration starts. Combined with `Event.wait(timeout)` (which
        returns immediately when set), this guarantees thread terminates
        within max(interval, time-since-last-emit) of __exit__ signal.
        """
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            self._emit_tick()
            if self._stop_event.wait(timeout=self.interval_seconds):
                break

    def _emit_tick(self) -> None:
        """Format + write a single tick to stderr (best-effort)."""
        ctx = get_current_progress()
        line = self._format_tick(ctx)
        try:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
        except OSError:
            self._failed_writes += 1

    def _format_tick(self, ctx: ProgressContext) -> str:
        """Stub format — full impl in S1-5."""
        return f"[sbtdd auto] tick: phase {ctx.phase}"
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_heartbeat.py -v
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: HeartbeatEmitter spawns Event-interruptible daemon tick thread"
```

---

### Task S1-5: Tick format with full fields (H5) + null omission (H6) + elapsed helper

**Files:**
- Modify: `skills/sbtdd/scripts/heartbeat.py`
- Modify: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing tests for H5/H6**

Append to `tests/test_heartbeat.py`:

```python
def test_format_tick_full_fields_matches_h5():
    fake_start = datetime.now(timezone.utc) - timedelta(seconds=15)
    ctx = ProgressContext(
        iter_num=2, phase=3, task_index=14, task_total=36,
        dispatch_label="magi-loop2-iter2", started_at=fake_start,
    )
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ctx)
    assert line.startswith("[sbtdd auto] tick:")
    assert "iter 2" in line
    assert "phase 3" in line
    assert "task 14/36" in line
    assert "dispatch=magi-loop2-iter2" in line
    assert "elapsed=" in line
    assert any(s in line for s in ("0m14s", "0m15s", "0m16s"))


def test_format_tick_omits_null_fields_h6():
    fake_start = datetime.now(timezone.utc) - timedelta(seconds=45)
    ctx = ProgressContext(phase=1, started_at=fake_start)
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ctx)
    assert "phase 1" in line
    assert "iter " not in line
    assert "task " not in line
    assert "dispatch=" not in line
    assert "elapsed=" in line


def test_format_tick_no_started_at_omits_elapsed():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    line = emitter._format_tick(ProgressContext())
    assert line.startswith("[sbtdd auto] tick:")
    assert "phase 0" in line
    assert "elapsed" not in line
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement full _format_tick + elapsed helper**

Replace `_format_tick` in `heartbeat.py` and add helper:

```python
    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """Render elapsed seconds as ``<min>m<sec>s`` (clamped to >= 0)."""
        mins, secs = divmod(int(max(seconds, 0)), 60)
        return f"{mins}m{secs}s"

    def _format_tick(self, ctx: ProgressContext) -> str:
        """Format a tick line per sec.2.1 H5 (full) and H6 (null omission)."""
        parts: list[str] = []
        if ctx.iter_num:
            parts.append(f"iter {ctx.iter_num}")
        parts.append(f"phase {ctx.phase}")
        if ctx.task_index is not None and ctx.task_total is not None:
            parts.append(f"task {ctx.task_index}/{ctx.task_total}")
        if ctx.dispatch_label:
            parts.append(f"dispatch={ctx.dispatch_label}")
        if ctx.started_at is not None:
            elapsed_s = (datetime.now(timezone.utc) - ctx.started_at).total_seconds()
            parts.append(f"elapsed={self._format_elapsed(elapsed_s)}")
        return "[sbtdd auto] tick: " + " ".join(parts)
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: implement tick format with H5 full-fields and H6 null-omission"
```

---

### Task S1-6: First-failure breadcrumb + counter (INV-32 part 1)

**Files:**
- Modify: `skills/sbtdd/scripts/heartbeat.py`
- Modify: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing tests for first-failure breadcrumb + counter**

Append to `tests/test_heartbeat.py`:

```python
def test_heartbeat_first_failure_emits_breadcrumb_then_silent(monkeypatch):
    write_calls = {"count": 0}
    real_write = sys.stderr.write

    def failing_write(s):
        write_calls["count"] += 1
        if write_calls["count"] == 1 or write_calls["count"] >= 3:
            raise OSError("broken pipe")
        return real_write(s)

    monkeypatch.setattr(sys.stderr, "write", failing_write)
    emitter = HeartbeatEmitter(label="x", interval_seconds=0.05)
    with emitter:
        time.sleep(0.18)
    assert emitter._failed_writes >= 1


def test_heartbeat_failed_writes_counter_starts_zero():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15)
    assert emitter._failed_writes == 0
```

- [ ] **Step 2: Run + verify fail**

`test_heartbeat_failed_writes_counter_starts_zero` already passes; the breadcrumb test may need the explicit logic.

- [ ] **Step 3: Add explicit first-failure breadcrumb logic in _emit_tick**

Replace `_emit_tick` in `heartbeat.py`:

```python
    def _emit_tick(self) -> None:
        """Format + write a single tick to stderr (best-effort).

        On stderr write failure (OSError, e.g. broken pipe):
        - First failure: emit one warning breadcrumb (best-effort).
        - Subsequent failures: silent.
        """
        ctx = get_current_progress()
        line = self._format_tick(ctx)
        try:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
        except OSError as exc:
            self._failed_writes += 1
            if self._failed_writes == 1:
                try:
                    sys.stderr.write(
                        f"[sbtdd auto] heartbeat write failed "
                        f"(will continue silently): {exc}\n"
                    )
                    sys.stderr.flush()
                except OSError:
                    pass
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: heartbeat first-failure breadcrumb + silent subsequent failures"
```

---

### Task S1-7: Queue-based incremental persistence (INV-32 part 2)

**Files:**
- Modify: `skills/sbtdd/scripts/heartbeat.py`
- Modify: `tests/test_heartbeat.py`

- [ ] **Step 1: Write failing tests for queue reporting + exit flush**

Append to `tests/test_heartbeat.py`:

```python
import queue


def test_heartbeat_reports_failure_counter_via_queue_every_n10(monkeypatch):
    real_write = sys.stderr.write

    def always_fail(s):
        raise OSError("broken pipe")

    monkeypatch.setattr(sys.stderr, "write", always_fail)
    q: "queue.Queue[int]" = queue.Queue()
    emitter = HeartbeatEmitter(
        label="x", interval_seconds=0.01, failures_queue=q,
    )
    with emitter:
        deadline = time.monotonic() + 2.0
        while emitter._failed_writes < 10 and time.monotonic() < deadline:
            time.sleep(0.01)
    assert emitter._failed_writes >= 10
    drained: list[int] = []
    while not q.empty():
        drained.append(q.get_nowait())
    assert any(c >= 10 for c in drained), f"expected counter >= 10 in queue, got {drained}"


def test_heartbeat_exit_pushes_final_counter_to_queue():
    q: "queue.Queue[int]" = queue.Queue()
    emitter = HeartbeatEmitter(label="x", interval_seconds=15.0, failures_queue=q)
    with emitter:
        emitter._failed_writes = 7
    drained: list[int] = []
    while not q.empty():
        drained.append(q.get_nowait())
    assert drained[-1] == 7


def test_heartbeat_no_queue_means_no_persistence():
    emitter = HeartbeatEmitter(label="x", interval_seconds=15.0, failures_queue=None)
    with emitter:
        emitter._failed_writes = 5
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add queue push at every N=10 increments + on exit**

Modify `_emit_tick` to push every N=10:

```python
        except OSError as exc:
            self._failed_writes += 1
            if self._failures_queue is not None and self._failed_writes % 10 == 0:
                try:
                    self._failures_queue.put_nowait(self._failed_writes)
                except queue.Full:
                    pass
            if self._failed_writes == 1:
                # ... existing breadcrumb logic ...
```

Modify `__exit__` to flush final counter:

```python
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            # Per Checkpoint 2 iter 2 caspar + iter 3 caspar CRITICAL fix:
            # if join timed out, the thread is blocked on a stderr write
            # (broken pipe + the write call itself blocks). EXPLICIT
            # accounting: increment a class-level _zombie_thread_count and
            # emit a structured warning to alternate channel (best-effort
            # syslog-style line via os.write to fd=2 if available, swallow
            # otherwise). The thread is daemonized so process exit collects
            # it; we cannot safely interrupt a blocked syscall without
            # unsafe primitives.
            if self._thread.is_alive():
                HeartbeatEmitter._zombie_thread_count += 1
                # Best-effort alternate-channel breadcrumb: write directly
                # to fd=2 (bypasses sys.stderr buffering that caused the
                # original block).
                try:
                    import os as _os
                    _os.write(
                        2,
                        f"[sbtdd auto] WARNING: heartbeat thread blocked at "
                        f"__exit__ for label={self.label!r} (zombie count="
                        f"{HeartbeatEmitter._zombie_thread_count}); "
                        f"daemon=True will GC at process end\n".encode(),
                    )
                except OSError:
                    pass
        # Final flush queue counter (single-writer rule preserved — main
        # thread sees the put via queue API).
        if self._failures_queue is not None and self._failed_writes > 0:
            try:
                self._failures_queue.put_nowait(self._failed_writes)
            except queue.Full:
                pass
            try:
                sys.stderr.write(
                    f"[sbtdd auto] heartbeat completed with "
                    f"{self._failed_writes} silent write failures\n"
                )
                sys.stderr.flush()
            except OSError:
                pass
        return None
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/heartbeat.py tests/test_heartbeat.py
git commit -m "feat: heartbeat reports failure counter via queue every N=10 + on exit"
```

---

### Task S1-8: Mechanical smoke fixture (R2.3 — protect NF-A budget)

**Files:**
- Create: `tests/test_heartbeat_smoke.py`

- [ ] **Step 1: Write smoke fixture test**

Create `tests/test_heartbeat_smoke.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-01
"""Mechanical smoke fixture for HeartbeatEmitter (sec.5.2 R2.3)."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from heartbeat import HeartbeatEmitter, set_current_progress, reset_current_progress
from models import ProgressContext


def test_emitter_emits_ticks_deterministically(capsys):
    """R2.3: Sub-second cadence = ~5 ticks in 2.5s wall time (NF-A protected)."""
    reset_current_progress()
    set_current_progress(
        ProgressContext(
            iter_num=1, phase=2, task_index=3, task_total=10,
            dispatch_label="smoke-dispatch",
            started_at=datetime.now(timezone.utc),
        )
    )
    with HeartbeatEmitter(label="smoke-dispatch", interval_seconds=0.5):
        time.sleep(2.5)
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines()
        if line.startswith("[sbtdd auto] tick:")
    ]
    assert 4 <= len(tick_lines) <= 6, (
        f"expected 4-6 ticks in 2.5s window, got {len(tick_lines)}: {tick_lines}"
    )
    for line in tick_lines:
        assert "dispatch=smoke-dispatch" in line
        assert "elapsed=" in line
    reset_current_progress()
```

- [ ] **Step 2: Run smoke test**

```bash
time pytest tests/test_heartbeat_smoke.py -v
```

Expected: pass; wall time <5s.

- [ ] **Step 3: Commit**

```bash
git add tests/test_heartbeat_smoke.py
git commit -m "test: add mechanical heartbeat smoke fixture (NF-A budget protected)"
```

---

### Task S1-9: ProgressContext writer hooks at the 10 transition sites in auto_cmd

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Survey existing auto_cmd structure**

```bash
grep -n "_phase\|def _.*phase\|def _.*dispatch\|task_index\|task_total" skills/sbtdd/scripts/auto_cmd.py | head -40
```

Locate the 10 transition sites enumerated in spec sec.3.

- [ ] **Step 2: Add helper + writer at phase 1 entry**

In `skills/sbtdd/scripts/auto_cmd.py`, add at top:

```python
from datetime import datetime, timezone
from heartbeat import set_current_progress
from models import ProgressContext


def _set_progress(
    *,
    iter_num: int = 0,
    phase: int,
    task_index: int | None = None,
    task_total: int | None = None,
    dispatch_label: str | None = None,
) -> None:
    """Helper: write a fresh ProgressContext for the current transition.

    **started_at semantics (Checkpoint 2 iter 2 caspar CRITICAL #3 fix):**
    `started_at` represents the **current dispatch's** start time per spec
    sec.3. Refreshing per `_set_progress` call would break that contract
    when a single dispatch has multiple intra-dispatch updates (e.g.,
    progress refinement during a long subagent invocation).

    Rules:
    - If `dispatch_label` differs from current ProgressContext's label
      (or current is None): treat as new dispatch, refresh `started_at`.
    - If `dispatch_label` matches current: preserve `started_at`
      (intra-dispatch update; elapsed timer continues monotonically).
    - If `dispatch_label is None` (between dispatches): set started_at to None.
    """
    from heartbeat import get_current_progress
    current = get_current_progress()
    # Single label-transition predicate (Checkpoint 2 iter 3 melchior CRITICAL fix):
    # Compute is_dispatch_transition first; then derive started_at from one rule.
    is_dispatch_transition = (current.dispatch_label != dispatch_label)
    if dispatch_label is None:
        new_started = None
    elif is_dispatch_transition or current.started_at is None:
        # New dispatch OR first dispatch ever.
        new_started = datetime.now(timezone.utc)
    else:
        # Same dispatch — preserve started_at for monotonic elapsed.
        new_started = current.started_at
    set_current_progress(
        ProgressContext(
            iter_num=iter_num, phase=phase,
            task_index=task_index, task_total=task_total,
            dispatch_label=dispatch_label,
            started_at=new_started,
        )
    )
```

**Test additions for `started_at` semantics (per Checkpoint 2 iter 2 caspar fix):**

```python
def test_set_progress_preserves_started_at_within_same_dispatch():
    """Intra-dispatch update keeps elapsed monotonic (sec.3 PINNED semantics)."""
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress
    import time

    reset_current_progress()
    _set_progress(phase=2, task_index=1, task_total=10, dispatch_label="green")
    first_started = get_current_progress().started_at
    time.sleep(0.01)
    # Same dispatch_label, intra-dispatch progress refinement
    _set_progress(phase=2, task_index=1, task_total=10, dispatch_label="green")
    second_started = get_current_progress().started_at
    assert second_started == first_started, "started_at must NOT refresh within same dispatch"
    reset_current_progress()


def test_set_progress_refreshes_started_at_on_dispatch_change():
    """Different dispatch_label resets the elapsed timer."""
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress
    import time

    reset_current_progress()
    _set_progress(phase=2, dispatch_label="red")
    red_started = get_current_progress().started_at
    time.sleep(0.01)
    _set_progress(phase=2, dispatch_label="green")
    green_started = get_current_progress().started_at
    assert green_started > red_started, "different dispatch must refresh started_at"
    reset_current_progress()


def test_set_progress_clears_started_at_when_label_none():
    """Between-dispatches state has no elapsed timer."""
    from auto_cmd import _set_progress
    from heartbeat import get_current_progress, reset_current_progress

    reset_current_progress()
    _set_progress(phase=2, dispatch_label="red")
    assert get_current_progress().started_at is not None
    _set_progress(phase=2, dispatch_label=None)
    assert get_current_progress().started_at is None
    reset_current_progress()
```

- [ ] **Step 3: Write failing test for phase 1 entry**

Append to `tests/test_auto_progress.py`:

```python
from datetime import datetime, timezone
from heartbeat import get_current_progress, reset_current_progress


def test_phase_1_entry_writes_progress_phase_1(monkeypatch, tmp_path):
    reset_current_progress()
    from auto_cmd import _set_progress
    _set_progress(phase=1)
    ctx = get_current_progress()
    assert ctx.phase == 1
    assert ctx.iter_num == 0
    assert ctx.dispatch_label is None
    reset_current_progress()
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Wire `_set_progress` into all 10 transition sites**

For each transition, find the existing function and insert `_set_progress(...)` at entry. Sites:

1. **Phase 1 entry** (`_phase1_*` or `run_phase_1`): `_set_progress(phase=1)`
2. **Phase 2 entry** (task loop start): `_set_progress(phase=2, task_total=len(tasks))`
3. **Per-task iteration**: inside the task loop, before each iteration: `_set_progress(phase=2, task_index=i+1, task_total=len(tasks))`
4. **Per-dispatch within task** (TDD red/green/refactor, spec-reviewer, code-review): `_set_progress(phase=2, task_index=i+1, task_total=len(tasks), dispatch_label=<label>)` where `<label>` is `"red" | "green" | "refactor" | "spec-review" | "code-review"`.
5. **Phase 3 entry**: `_set_progress(phase=3, task_total=len(tasks))` (preserve task_total)
6. **MAGI Loop 2 iter**: `_set_progress(iter_num=N, phase=3, dispatch_label=f"magi-loop2-iter{N}")`
7. **Phase 3 dispatch sites** (Loop 1 review, mini-cycle fix dispatches): `_set_progress(iter_num=N, phase=3, dispatch_label=...)`
8. **Phase 4 entry**: `_set_progress(phase=4)`
9. **Phase 5 entry**: `_set_progress(phase=5)`
10. **End-of-dispatch (clear label)**: `_set_progress(phase=current_phase, dispatch_label=None)` — apply between successive dispatches in same task.

- [ ] **Step 6: Add coverage tests for each transition site**

For each site, add a test stubbing the surrounding function so the test verifies ProgressContext fields after the transition. Example for phase 2:

```python
def test_phase_2_entry_writes_phase_2_with_task_total():
    reset_current_progress()
    from auto_cmd import _set_progress
    _set_progress(phase=2, task_total=36)
    ctx = get_current_progress()
    assert ctx.phase == 2
    assert ctx.task_total == 36
    reset_current_progress()


def test_magi_loop_2_iter_writes_iter_n():
    reset_current_progress()
    from auto_cmd import _set_progress
    _set_progress(iter_num=2, phase=3, dispatch_label="magi-loop2-iter2")
    ctx = get_current_progress()
    assert ctx.iter_num == 2
    assert ctx.phase == 3
    assert ctx.dispatch_label == "magi-loop2-iter2"
    reset_current_progress()
```

- [ ] **Step 7: Run all tests + verify**

```bash
pytest tests/test_auto_progress.py -v
ruff check skills/sbtdd/scripts/auto_cmd.py
mypy skills/sbtdd/scripts/auto_cmd.py --strict
```

- [ ] **Step 8: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: add ProgressContext writer hooks at 10 transitions in auto_cmd"
```

---

### Task S1-10: Wrap long dispatches in auto_cmd with HeartbeatEmitter

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test for `_dispatch_with_heartbeat` helper**

Append to `tests/test_auto_progress.py`:

```python
import time


def test_long_dispatch_wrapped_with_heartbeat_emits_ticks(capsys):
    from auto_cmd import _dispatch_with_heartbeat, _set_progress
    from heartbeat import reset_current_progress

    reset_current_progress()
    # Per Checkpoint 2 iter 2 melchior fix: caller MUST set dispatch_label
    # before invoking the wrapper (fail-loud); no silent fallback.
    _set_progress(phase=2, dispatch_label="test-dispatch")

    def fake_invoke():
        time.sleep(1.0)
        return 0

    rc = _dispatch_with_heartbeat(
        invoke=fake_invoke,
        heartbeat_interval=0.3,
    )
    assert rc == 0
    captured = capsys.readouterr()
    tick_lines = [
        line for line in captured.err.splitlines()
        if line.startswith("[sbtdd auto] tick:")
    ]
    assert len(tick_lines) >= 2  # 1.0s / 0.3s = 3-4 ticks
    reset_current_progress()


def test_dispatch_with_heartbeat_fails_loud_when_no_dispatch_label():
    """Per Checkpoint 2 iter 2 melchior CRITICAL #1: silent fallback rejected."""
    from auto_cmd import _dispatch_with_heartbeat
    from heartbeat import reset_current_progress

    reset_current_progress()
    with pytest.raises(ValueError, match="dispatch_label"):
        _dispatch_with_heartbeat(invoke=lambda: 0, heartbeat_interval=0.5)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_dispatch_with_heartbeat`**

In `skills/sbtdd/scripts/auto_cmd.py`:

```python
import queue
from typing import Callable, Any

from heartbeat import HeartbeatEmitter

# Module-level queue: heartbeat thread -> main thread (sec.3 single-writer rule).
# maxsize=0 (UNBOUNDED) is a hard contract per Checkpoint 2 iter 3 melchior CRITICAL #3:
# bounded queue + queue.Full silently loses heartbeat audit data. Memory cost is
# negligible (single int per push, bounded by failed-write count + N=10 batching).
_heartbeat_failures_q: "queue.Queue[int]" = queue.Queue(maxsize=0)


def _dispatch_with_heartbeat(
    *,
    invoke: Callable[..., Any],
    heartbeat_interval: float = 15.0,
    **invoke_kwargs: Any,
) -> Any:
    """Wrap a long subprocess invocation in a HeartbeatEmitter.

    The dispatch label is **derived from the current ProgressContext**
    (set by ``_set_progress`` immediately before this call). Eliminates
    the iter-1 Checkpoint 2 caspar finding: dispatch_label drift between
    the writer hook and the heartbeat wrapper.

    **Fail-loud (Checkpoint 2 iter 2 melchior fix)**: raises ValueError
    if `dispatch_label` is None at call time. Silent fallback to
    "unlabeled-dispatch" was rejected per fail-loud principle — caller
    MUST establish dispatch context before invoking the wrapper.

    Failures queue is the module-level ``_heartbeat_failures_q`` drained
    by ``_update_progress`` (single-writer rule per sec.3 of spec).
    """
    from heartbeat import get_current_progress
    ctx = get_current_progress()
    if ctx.dispatch_label is None:
        raise ValueError(
            "_dispatch_with_heartbeat called without dispatch_label set. "
            "Caller must invoke `_set_progress(..., dispatch_label='...')` "
            "BEFORE this wrapper. Silent fallback rejected per fail-loud "
            "(Checkpoint 2 iter 2 melchior CRITICAL #1)."
        )
    with HeartbeatEmitter(
        label=ctx.dispatch_label,
        interval_seconds=heartbeat_interval,
        failures_queue=_heartbeat_failures_q,
    ):
        return invoke(**invoke_kwargs)
```

**Note (Checkpoint 2 iter 1 caspar finding):** caller MUST call `_set_progress(..., dispatch_label="...")` BEFORE invoking `_dispatch_with_heartbeat`. The wrapper auto-derives label from ProgressContext to eliminate label-drift risk. Add unit test asserting derivation:

```python
def test_dispatch_with_heartbeat_derives_label_from_progress(capsys):
    from auto_cmd import _dispatch_with_heartbeat, _set_progress
    _set_progress(phase=2, dispatch_label="green")
    captured_label = {}

    def fake_invoke():
        from heartbeat import get_current_progress
        captured_label["label"] = get_current_progress().dispatch_label
        return 0

    rc = _dispatch_with_heartbeat(invoke=fake_invoke, heartbeat_interval=0.1)
    assert rc == 0
    assert captured_label["label"] == "green"
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Wire `_dispatch_with_heartbeat` into existing dispatch sites**

For each long-running subprocess invocation in auto_cmd (MAGI Loop 2 dispatch, /requesting-code-review dispatch, mini-cycle TDD red/green/refactor, spec-reviewer dispatch), wrap it:

```python
# Before:
result = magi_dispatch.invoke_magi(...)

# After:
_set_progress(iter_num=iter_n, phase=3, dispatch_label=f"magi-loop2-iter{iter_n}")
result = _dispatch_with_heartbeat(
    invoke=lambda: magi_dispatch.invoke_magi(...),
    heartbeat_interval=config.auto_heartbeat_interval_seconds,
)
```

The wrapper reads `dispatch_label` from `_set_progress` automatically (Checkpoint 2 iter 1 caspar fix), eliminating label drift risk.

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: wrap long dispatches in auto_cmd with HeartbeatEmitter"
```

---

### Task S1-11: Drain heartbeat queue + persist counter in _update_progress

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test for queue drain semantics (max())**

Append to `tests/test_auto_progress.py`:

```python
def test_update_progress_drains_heartbeat_queue_and_writes_max(tmp_path):
    """sec.3 single-writer rule: main thread drains queue, persists max() to JSON."""
    from auto_cmd import _heartbeat_failures_q, _drain_heartbeat_queue_and_persist
    import json

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()

    _heartbeat_failures_q.put(5)
    _heartbeat_failures_q.put(10)
    _heartbeat_failures_q.put(15)

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")
    _drain_heartbeat_queue_and_persist(auto_run_path)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["heartbeat_failed_writes_total"] == 15
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_drain_heartbeat_queue_and_persist`**

In `skills/sbtdd/scripts/auto_cmd.py`:

```python
import json
from pathlib import Path


def _drain_heartbeat_queue_and_persist(auto_run_path: Path) -> None:
    """Drain queue + persist max() counter to auto-run.json (sec.3 single-writer)."""
    drained: list[int] = []
    while True:
        try:
            drained.append(_heartbeat_failures_q.get_nowait())
        except queue.Empty:
            break
    if not drained:
        return
    try:
        data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    data["heartbeat_failed_writes_total"] = max(
        data.get("heartbeat_failed_writes_total", 0), *drained,
    )
    # Atomic rename pattern (preserve existing _update_progress mechanism).
    tmp_path = auto_run_path.with_suffix(auto_run_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp_path.replace(auto_run_path)
```

Add a call to `_drain_heartbeat_queue_and_persist(auto_run_path)` inside the existing `_update_progress` function (or its equivalent) so each progress write also drains the queue.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: drain heartbeat failures queue + persist max() to auto-run.json"
```

---

### Task S1-12: ProgressContext serialization to auto-run.json (ISO 8601 UTC)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_auto_progress.py`:

```python
def test_serialize_progress_context_iso_utc(tmp_path):
    from auto_cmd import _serialize_progress
    from heartbeat import set_current_progress, reset_current_progress
    from models import ProgressContext
    import json

    set_current_progress(
        ProgressContext(
            iter_num=2, phase=3, task_index=14, task_total=36,
            dispatch_label="magi-loop2-iter2",
            started_at=datetime(2026, 5, 1, 12, 34, 56, tzinfo=timezone.utc),
        )
    )
    serialized = _serialize_progress()
    assert serialized["iter_num"] == 2
    assert serialized["phase"] == 3
    assert serialized["task_index"] == 14
    assert serialized["task_total"] == 36
    assert serialized["dispatch_label"] == "magi-loop2-iter2"
    assert serialized["started_at"] == "2026-05-01T12:34:56Z"
    reset_current_progress()
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_serialize_progress`**

In `skills/sbtdd/scripts/auto_cmd.py`:

```python
from heartbeat import get_current_progress


def _serialize_progress() -> dict[str, Any]:
    """Serialize current ProgressContext to JSON-friendly dict (ISO 8601 UTC)."""
    ctx = get_current_progress()
    started = ctx.started_at
    if started is not None:
        # Normalize to UTC + format with 'Z' suffix via strftime (NOT
        # str.replace('+00:00', 'Z') — that breaks if input already has 'Z'
        # or different tzinfo formatting). Per Checkpoint 2 iter 1 melchior fix.
        started_str = started.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        started_str = None
    return {
        "iter_num": ctx.iter_num,
        "phase": ctx.phase,
        "task_index": ctx.task_index,
        "task_total": ctx.task_total,
        "dispatch_label": ctx.dispatch_label,
        "started_at": started_str,
    }
```

Wire into existing `_update_progress` (or equivalent): after reading `data` and before atomic rename:

```python
    data["progress"] = _serialize_progress()
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: serialize ProgressContext to auto-run.json with ISO 8601 UTC"
```

---

### Task S1-13: Periodic queue drain (W8 fix — bound counter latency)

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Modify: `tests/test_auto_progress.py`

- [ ] **Step 1: Write failing test**

```python
def test_periodic_drain_persists_counter_without_phase_transition(tmp_path):
    """Spec sec.11.1 W8: bound persistence latency to <= 30s even sin transitions."""
    from auto_cmd import _periodic_drain_if_due, _heartbeat_failures_q
    import json

    while not _heartbeat_failures_q.empty():
        _heartbeat_failures_q.get_nowait()
    _heartbeat_failures_q.put(5)

    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text('{"started_at": "2026-05-01T12:00:00Z"}', encoding="utf-8")
    _periodic_drain_if_due(auto_run_path, force=True)
    data = json.loads(auto_run_path.read_text(encoding="utf-8"))
    assert data["heartbeat_failed_writes_total"] == 5
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement `_periodic_drain_if_due`**

In `auto_cmd.py`:

```python
import time

_PROGRESS_DRAIN_INTERVAL_SECONDS = 30


@dataclass
class _DrainState:
    """Encapsulates last-drain timestamp to avoid module-level state.

    Per Checkpoint 2 iter 1 caspar fix: module-level `_last_drain_at` caused
    test order dependency. Encapsulating in a dataclass instance allows
    fixture reset and parallel-test isolation.
    """
    last_drain_at: float = 0.0


_drain_state = _DrainState()


def _periodic_drain_if_due(
    auto_run_path: Path,
    *,
    force: bool = False,
    state: _DrainState = _drain_state,
) -> None:
    """Drain heartbeat queue if 30s elapsed since last drain (sec.11.1 W8)."""
    now = time.monotonic()
    if not force and (now - state.last_drain_at) < _PROGRESS_DRAIN_INTERVAL_SECONDS:
        return
    _drain_heartbeat_queue_and_persist(auto_run_path)
    state.last_drain_at = now


def _reset_drain_state_for_tests() -> None:
    """Test-only helper: reset drain state to ensure isolation."""
    _drain_state.last_drain_at = 0.0
```

Wire `_periodic_drain_if_due` into the auto_cmd main loop at convenient checkpoints (e.g., between dispatch invocations within a task, between task iterations). Tests should call `_reset_drain_state_for_tests()` in fixture setup or use `force=True`.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/auto_cmd.py tests/test_auto_progress.py
git commit -m "feat: periodic queue drain bounds heartbeat counter persistence latency"
```

---

## Subagent #2 — Streaming + watch + docs track (17 tasks)

### Task S2-1: Add 5 new fields to PluginConfig

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_config.py`:

```python
def test_plugin_config_new_observability_fields_have_defaults(tmp_path):
    """v0.5.0: 5 new PluginConfig fields with documented defaults."""
    config_path = tmp_path / "plugin.local.md"
    config_path.write_text("""---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest, "ruff check ."]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
---
""")
    from config import load_plugin_local
    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 900
    assert cfg.auto_heartbeat_interval_seconds == 15
    assert cfg.status_watch_default_interval_seconds == 1.0
    assert cfg.auto_origin_disambiguation is True
    assert cfg.auto_no_timeout_dispatch_labels == ("magi-*",)


def test_plugin_config_observability_fields_overridable(tmp_path):
    config_path = tmp_path / "plugin.local.md"
    config_path.write_text("""---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 600
auto_heartbeat_interval_seconds: 30
status_watch_default_interval_seconds: 0.5
auto_origin_disambiguation: false
auto_no_timeout_dispatch_labels: ["magi-*", "long-build-*"]
---
""")
    from config import load_plugin_local
    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 600
    assert cfg.auto_heartbeat_interval_seconds == 30
    assert cfg.status_watch_default_interval_seconds == 0.5
    assert cfg.auto_origin_disambiguation is False
    assert cfg.auto_no_timeout_dispatch_labels == ("magi-*", "long-build-*")
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add fields to PluginConfig + apply defaults in load**

In `skills/sbtdd/scripts/config.py`, modify the `PluginConfig` dataclass:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PluginConfig:
    # ... existing fields ...

    # v0.5.0 observability fields (sec.4.3 of spec).
    auto_per_stream_timeout_seconds: int = 900
    auto_heartbeat_interval_seconds: int = 15
    status_watch_default_interval_seconds: float = 1.0
    auto_origin_disambiguation: bool = True
    auto_no_timeout_dispatch_labels: tuple[str, ...] = field(
        default_factory=lambda: ("magi-*",)
    )
```

In `load_plugin_local`, after the existing validations:

```python
    # v0.5.0 observability defaults applied if absent.
    data.setdefault("auto_per_stream_timeout_seconds", 900)
    data.setdefault("auto_heartbeat_interval_seconds", 15)
    data.setdefault("status_watch_default_interval_seconds", 1.0)
    data.setdefault("auto_origin_disambiguation", True)
    data.setdefault("auto_no_timeout_dispatch_labels", ["magi-*"])
    if isinstance(data.get("auto_no_timeout_dispatch_labels"), list):
        data["auto_no_timeout_dispatch_labels"] = tuple(
            data["auto_no_timeout_dispatch_labels"]
        )
```

- [ ] **Step 4: Run + verify pass**

```bash
pytest tests/test_config.py -v
mypy skills/sbtdd/scripts/config.py --strict
```

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "feat: add 5 v0.5.0 observability fields to PluginConfig"
```

---

### Task S2-2: INV-34 four-clause validation with distinct error messages

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for each of the 3 INV-34 clauses**

```python
def test_inv34_clause_1_ratio_violation(tmp_path):
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
"""
    config_path = tmp_path / "p1.md"
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 50\n"
        "auto_heartbeat_interval_seconds: 15\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError
    with pytest.raises(ValidationError, match="INV-34 clause 1"):
        load_plugin_local(config_path)


def test_inv34_clause_2_ceiling_violation(tmp_path):
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
"""
    config_path = tmp_path / "p2.md"
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 1000\n"
        "auto_heartbeat_interval_seconds: 120\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError
    with pytest.raises(ValidationError, match="INV-34 clause 2"):
        load_plugin_local(config_path)


def test_inv34_clause_3_floor_violation(tmp_path):
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
"""
    config_path = tmp_path / "p3.md"
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 100\n"
        "auto_heartbeat_interval_seconds: 2\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError
    with pytest.raises(ValidationError, match="INV-34 clause 3"):
        load_plugin_local(config_path)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add INV-34 validation with distinct error messages**

In `load_plugin_local`, after the observability defaults block:

```python
    # INV-34 (sec.2.7 of spec): timeout-vs-interval + floor + ceiling.
    timeout = data["auto_per_stream_timeout_seconds"]
    interval = data["auto_heartbeat_interval_seconds"]
    if not isinstance(timeout, int) or timeout < 0:
        raise ValidationError(
            f"auto_per_stream_timeout_seconds must be int >= 0, got {timeout!r}"
        )
    if not isinstance(interval, int) or interval < 0:
        raise ValidationError(
            f"auto_heartbeat_interval_seconds must be int >= 0, got {interval!r}"
        )
    # Validation order PINNED post-Checkpoint 2 iter 2 melchior fix: cheapest
    # bound checks first (clauses 4, 2, 3), then ratio (clause 1) which only
    # runs after absolute floors confirm no pathological values.
    if timeout < 600:
        raise ValidationError(
            f"INV-34 clause 4: auto_per_stream_timeout_seconds must be >= 600s "
            f"(caspar opus runs observed empirically up to 10min); got {timeout}"
        )
    if interval > 60:
        raise ValidationError(
            f"INV-34 clause 2: auto_heartbeat_interval_seconds must be <= 60s "
            f"to keep operator awareness within 1-minute granularity; got {interval}"
        )
    if interval < 5:
        raise ValidationError(
            f"INV-34 clause 3: auto_heartbeat_interval_seconds must be >= 5s "
            f"to avoid stderr spam without value; got {interval}"
        )
    # Clause 1 last: ratio check. With clauses 2-4 already satisfied,
    # this only catches the narrow case where timeout in [600, 5*interval).
    # E.g., timeout=600, interval=60: 5*60=300 <= 600, pass.
    # E.g., timeout=600, interval=121 (rejected by clause 2 first).
    if timeout < 5 * interval:
        raise ValidationError(
            f"INV-34 clause 1: auto_per_stream_timeout_seconds ({timeout}) "
            f"must be >= 5 * auto_heartbeat_interval_seconds ({interval}) "
            f"= {5 * interval}; got {timeout}"
        )
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Add positive boundary test**

Append to `tests/test_config.py`:

```python
def test_inv34_clause_1_boundary_timeout_equals_5x_interval_accepts(tmp_path):
    """Boundary: timeout == 5 * interval is accepted (>= ratio satisfied)."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
"""
    config_path = tmp_path / "boundary.md"
    # 600s = max(5*60, 600) = 600 — boundary of clauses 1 AND 4.
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 600\n"
        "auto_heartbeat_interval_seconds: 60\n---\n"
    )
    from config import load_plugin_local
    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 600
    assert cfg.auto_heartbeat_interval_seconds == 60


def test_inv34_clause_4_timeout_below_600_rejected(tmp_path):
    """Clause 4: timeout < 600s rejected even if clauses 1-3 satisfied."""
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
"""
    config_path = tmp_path / "p4.md"
    # 75s satisfies clause 1 (5*15=75) but violates clause 4 (>=600).
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 75\n"
        "auto_heartbeat_interval_seconds: 15\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError
    with pytest.raises(ValidationError, match="INV-34 clause 4"):
        load_plugin_local(config_path)
```

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "feat: add INV-34 four-clause validation (incl. clause 4 absolute timeout floor)"
```

---

### Task S2-3: Allowlist validation (reject bare wildcards)

**Files:**
- Modify: `skills/sbtdd/scripts/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing test**

```python
def test_allowlist_bare_wildcard_rejected(tmp_path):
    base = """---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
"""
    from config import load_plugin_local
    from errors import ValidationError
    config_path = tmp_path / "p.md"
    config_path.write_text(base + 'auto_no_timeout_dispatch_labels: ["*"]\n---\n')
    with pytest.raises(ValidationError, match="bare '\\*' rejected"):
        load_plugin_local(config_path)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add allowlist validation**

After INV-34 in `load_plugin_local`:

```python
    # W11 (sec.11.1): bare '*' or '' would defeat timeout entirely.
    labels = data["auto_no_timeout_dispatch_labels"]
    if isinstance(labels, (list, tuple)):
        for label in labels:
            if label == "*" or label == "":
                raise ValidationError(
                    f"auto_no_timeout_dispatch_labels: bare '*' rejected "
                    f"(would defeat timeout); use specific glob like 'magi-*'"
                )
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/config.py tests/test_config.py
git commit -m "fix: reject bare '*' in auto_no_timeout_dispatch_labels"
```

---

### Task S2-4: subprocess_utils — `run_streamed_with_timeout` scaffold + last_write_at tracking

**Files:**
- Modify: `skills/sbtdd/scripts/subprocess_utils.py`
- Modify: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Survey existing subprocess_utils**

```bash
grep -n "def \|select\|read" skills/sbtdd/scripts/subprocess_utils.py | head -30
```

- [ ] **Step 2: Write failing test**

```python
import sys

def test_streamed_with_timeout_returns_stdout_and_stderr_separately():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", """
import sys, time
for i in range(3):
    sys.stdout.write(f'out{i}\\n'); sys.stdout.flush()
    time.sleep(0.05)
"""]
    result = run_streamed_with_timeout(
        cmd, per_stream_timeout_seconds=10.0, dispatch_label="test",
    )
    assert result.returncode == 0
    assert "out0" in result.stdout
    assert "out2" in result.stdout
```

- [ ] **Step 3: Run + verify fail**

- [ ] **Step 4: Implement `run_streamed_with_timeout` scaffold**

In `skills/sbtdd/scripts/subprocess_utils.py`:

```python
import fnmatch
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class StreamedResult:
    """Output of run_streamed_with_timeout."""
    returncode: int
    stdout: str
    stderr: str


DEFAULT_ORIGIN_WINDOW_SECONDS = 0.050  # 50ms temporal window default.


def _matches_allowlist(label: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(label, pat) for pat in patterns)


def run_streamed_with_timeout(
    cmd: list[str],
    *,
    per_stream_timeout_seconds: float = 900.0,
    dispatch_label: str = "",
    no_timeout_labels: tuple[str, ...] = ("magi-*",),
    origin_disambiguation: bool = True,
    origin_window_seconds: float = DEFAULT_ORIGIN_WINDOW_SECONDS,
    **popen_kwargs: object,
) -> StreamedResult:
    """Per Checkpoint 2 iter 1 melchior+balthasar finding: origin_window_seconds
    is now a parameter (not a module constant) so tests can override to avoid
    Windows CI flakiness on loaded systems. Default 50ms preserves prior behavior."""
    """Run subprocess with per-stream timeout + origin disambiguation."""
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
        **popen_kwargs,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    now = time.monotonic()
    last_write_at: dict[str, float] = {"stdout": now, "stderr": now}
    last_chunk_at: dict[str, float] = {"stdout": 0.0, "stderr": 0.0}
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ, data="stdout")
    sel.register(proc.stderr, selectors.EVENT_READ, data="stderr")
    open_streams = {"stdout", "stderr"}
    timeout_exempt = _matches_allowlist(dispatch_label, no_timeout_labels)

    # Per Checkpoint 2 iter 3 caspar CRITICAL fix: use read1() not readline().
    # readline() blocks waiting for newline; if subprocess writes partial-line
    # bytes (e.g., progress bar without \n), pump never sees the bytes and
    # last_write_at stays stale -> false-positive timeout kill.
    # read1(N) returns whatever bytes are available (after select indicated
    # readiness), allowing the timeout tracker to update on every chunk.
    READ_CHUNK_SIZE = 8192
    while open_streams:
        events = sel.select(timeout=0.1)
        for key, _ in events:
            stream_name = key.data
            chunk = key.fileobj.read1(READ_CHUNK_SIZE) if hasattr(key.fileobj, "read1") else key.fileobj.read(READ_CHUNK_SIZE)
            if isinstance(chunk, bytes):
                chunk = chunk.decode("utf-8", errors="replace")
            line = chunk
            if line == "":
                sel.unregister(key.fileobj)
                open_streams.discard(stream_name)
                continue
            now = time.monotonic()
            last_write_at[stream_name] = now
            other_stream = "stderr" if stream_name == "stdout" else "stdout"
            both_recent = (
                origin_disambiguation
                and last_chunk_at[other_stream] > 0
                and (now - last_chunk_at[other_stream]) < origin_window_seconds
            )
            last_chunk_at[stream_name] = now
            output_line = f"[{stream_name}] " + line if both_recent else line
            if stream_name == "stdout":
                stdout_chunks.append(output_line)
            else:
                stderr_chunks.append(output_line)
        # Per-stream timeout: kill if all open streams silent for window.
        if (
            not timeout_exempt
            and open_streams
            and all(
                (time.monotonic() - last_write_at[s]) > per_stream_timeout_seconds
                for s in open_streams
            )
        ):
            sys.stderr.write(
                f"[sbtdd] killed subprocess (all open streams silent for "
                f">{per_stream_timeout_seconds}s); add 'dispatch_label_pattern' "
                f"to plugin.local.md auto_no_timeout_dispatch_labels to exempt\n"
            )
            sys.stderr.flush()
            _kill_subprocess_tree(proc)
            break
        if proc.poll() is not None and not open_streams:
            break

    proc.wait()
    return StreamedResult(
        returncode=proc.returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def _kill_subprocess_tree(proc: subprocess.Popen) -> None:
    """Kill subprocess + descendants (preserves R3-1 invariant on Windows).

    Per Checkpoint 2 iter 3 melchior W3: taskkill timeout reduced from 5s
    to 1s — kill path should not block the pump's select loop measurably.
    Even if taskkill itself is slow on a loaded box, proc.kill() runs
    immediately after as fallback. R3-1 ordering preserved.
    """
    if sys.platform == "win32":
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                check=False, capture_output=True, timeout=1,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    proc.kill()
```

- [ ] **Step 5: Run + verify pass**

```bash
pytest tests/test_subprocess_utils.py -v
mypy skills/sbtdd/scripts/subprocess_utils.py --strict
```

- [ ] **Step 6: Commit**

```bash
git add skills/sbtdd/scripts/subprocess_utils.py tests/test_subprocess_utils.py
git commit -m "feat: add run_streamed_with_timeout with per-stream timeout + origin disambig"
```

---

### Task S2-5: Per-stream timeout escenarios T1, T5, T7, T8

**Files:**
- Modify: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Write failing tests for T1, T5, T7, T8**

Append to `tests/test_subprocess_utils.py`:

```python
import sys
import pytest
from unittest.mock import MagicMock


def test_t1_all_streams_silent_kills_subprocess(capsys):
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", "import time; time.sleep(10)"]
    result = run_streamed_with_timeout(
        cmd, per_stream_timeout_seconds=0.5, dispatch_label="test-hang",
    )
    assert result.returncode != 0
    captured = capsys.readouterr()
    assert "all open streams silent" in captured.err
    assert "auto_no_timeout_dispatch_labels" in captured.err


def test_t5_allowlist_exempts_dispatch_label():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", "import time; time.sleep(1.0)"]
    result = run_streamed_with_timeout(
        cmd, per_stream_timeout_seconds=0.3, dispatch_label="magi-loop2-iter1",
        no_timeout_labels=("magi-*",),
    )
    assert result.returncode == 0


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="os.close(sys.stdout.fileno()) has Windows-specific failure modes; "
           "T7 verified via integration on POSIX (Checkpoint 2 iter 1 caspar finding)",
)
def test_t7_closed_stream_excluded_from_timeout():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", """
import sys, os, time
os.close(sys.stdout.fileno())
for i in range(3):
    sys.stderr.write(f'err{i}\\n')
    sys.stderr.flush()
    time.sleep(0.1)
"""]
    result = run_streamed_with_timeout(
        cmd, per_stream_timeout_seconds=0.3, dispatch_label="test-closed",
    )
    assert result.returncode == 0
    assert "err0" in result.stderr


def test_t8_kill_tree_order_preserved_on_windows(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("Windows-only invariant")
    from subprocess_utils import _kill_subprocess_tree
    call_order: list[str] = []

    def fake_run(*args, **kwargs):
        call_order.append("taskkill")
        from subprocess import CompletedProcess
        return CompletedProcess(args=args[0], returncode=0)

    monkeypatch.setattr("subprocess_utils.subprocess.run", fake_run)
    proc = MagicMock()
    proc.pid = 12345
    proc.kill = lambda: call_order.append("proc.kill")
    _kill_subprocess_tree(proc)
    assert call_order == ["taskkill", "proc.kill"]
```

- [ ] **Step 2: Run + verify pass**

The S2-4 implementation already covers T1, T5, T7 (closed stream auto-removed), T8 (R3-1 order). All four tests should pass.

```bash
pytest tests/test_subprocess_utils.py -v
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_subprocess_utils.py
git commit -m "test: cover T1/T5/T7/T8 escenarios for per-stream timeout"
```

---

### Task S2-6: Origin disambiguation escenarios O1-O4

**Files:**
- Modify: `tests/test_subprocess_utils.py`

- [ ] **Step 1: Write failing tests for O1-O4**

```python
def test_o1_single_stream_no_prefix():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", "import sys\nfor i in range(3):\n    sys.stdout.write(f'line{i}\\n')\n    sys.stdout.flush()"]
    result = run_streamed_with_timeout(
        cmd, origin_disambiguation=True, dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "line0" in result.stdout


def test_o2_dual_stream_in_50ms_window_prefixes():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", """
import sys, time
sys.stdout.write('out1\\n'); sys.stdout.flush()
time.sleep(0.005)
sys.stderr.write('err1\\n'); sys.stderr.flush()
"""]
    result = run_streamed_with_timeout(
        cmd, origin_disambiguation=True, dispatch_label="test",
    )
    # At least one of out1/err1 should be prefixed because they emit within 50ms.
    combined = result.stdout + result.stderr
    assert "[stdout]" in combined or "[stderr]" in combined


def test_o3_alternating_distant_windows_no_prefix():
    """O3: streams emit far apart -> no prefix.

    Per Checkpoint 2 iter 2 melchior fix: use a 5ms origin_window_seconds
    override (vs production 50ms default) and a deterministic 100ms gap to
    avoid Windows CI flakiness on loaded systems.
    """
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", """
import sys, time
sys.stdout.write('out1\\n'); sys.stdout.flush()
time.sleep(0.1)  # 100ms gap >> 5ms test window
sys.stderr.write('err1\\n'); sys.stderr.flush()
"""]
    result = run_streamed_with_timeout(
        cmd,
        origin_disambiguation=True,
        origin_window_seconds=0.005,  # 5ms test window (vs 50ms production)
        dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "[stderr]" not in result.stderr


def test_o4_disabled_no_prefix_even_on_dual_stream():
    from subprocess_utils import run_streamed_with_timeout
    cmd = [sys.executable, "-c", """
import sys, time
sys.stdout.write('out1\\n'); sys.stdout.flush()
time.sleep(0.005)
sys.stderr.write('err1\\n'); sys.stderr.flush()
"""]
    result = run_streamed_with_timeout(
        cmd, origin_disambiguation=False, dispatch_label="test",
    )
    assert "[stdout]" not in result.stdout
    assert "[stderr]" not in result.stderr
```

- [ ] **Step 2: Run + verify pass**

S2-4's implementation covers O1-O4 already. All tests should pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_subprocess_utils.py
git commit -m "test: cover O1-O4 escenarios for origin disambiguation"
```

---

### Task S2-7: status_cmd watch helpers (W1, W3, W6 — TTY render + missing file + interval validation)

**Files:**
- Modify: `skills/sbtdd/scripts/status_cmd.py`
- Create: `tests/test_status_watch.py`

- [ ] **Step 1: Create failing test file**

Create `tests/test_status_watch.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-01
"""Unit tests for /sbtdd status --watch (sec.2.2 W1-W6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_w3_watch_exits_zero_when_auto_run_missing(tmp_path, capsys):
    from status_cmd import _watch_loop_once
    rc = _watch_loop_once(tmp_path / "missing.json", json_mode=False)
    assert rc == 0
    captured = capsys.readouterr()
    assert "no auto run in progress" in captured.err.lower()


def test_w1_watch_render_tty_contains_progress_fields():
    from status_cmd import _watch_render_tty
    progress = {
        "iter_num": 2, "phase": 3, "task_index": 14, "task_total": 36,
        "dispatch_label": "magi-loop2-iter2",
        "started_at": "2026-05-01T12:00:00Z",
    }
    output = _watch_render_tty(progress)
    assert "iter 2" in output
    assert "phase 3" in output
    assert "task 14/36" in output
    assert "magi-loop2-iter2" in output


def test_w6_validates_interval_minimum():
    from status_cmd import validate_watch_interval
    from errors import ValidationError
    with pytest.raises(ValidationError, match=">= 0.1"):
        validate_watch_interval(0.05)
    validate_watch_interval(0.1)
    validate_watch_interval(5.0)
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement helpers in status_cmd.py**

In `skills/sbtdd/scripts/status_cmd.py`:

```python
import json
import sys
from pathlib import Path

from errors import ValidationError


def validate_watch_interval(interval: float) -> None:
    """W6: validate watch interval is >= 0.1s."""
    if interval < 0.1:
        raise ValidationError(
            f"--interval must be >= 0.1s (sub-100ms spins CPU); got {interval}"
        )


def _watch_render_tty(progress: dict) -> str:
    """W1: format ProgressContext snapshot for TTY rewrite-line render."""
    parts: list[str] = []
    if progress.get("iter_num"):
        parts.append(f"iter {progress['iter_num']}")
    parts.append(f"phase {progress.get('phase', 0)}")
    if progress.get("task_index") is not None and progress.get("task_total") is not None:
        parts.append(f"task {progress['task_index']}/{progress['task_total']}")
    if progress.get("dispatch_label"):
        parts.append(f"dispatch={progress['dispatch_label']}")
    return "[sbtdd watch] " + " ".join(parts)


def _watch_loop_once(auto_run_path: Path, *, json_mode: bool) -> int:
    """W3: single-poll cycle. Returns 0 if missing file."""
    if not auto_run_path.exists():
        sys.stderr.write("[sbtdd status] no auto run in progress\n")
        return 0
    return 0  # full loop in S2-9
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/status_cmd.py tests/test_status_watch.py
git commit -m "feat: status --watch helpers (TTY render + missing file + interval validation)"
```

---

### Task S2-8: status --watch JSON race retry + slow-poll fallback (W4)

**Files:**
- Modify: `skills/sbtdd/scripts/status_cmd.py`
- Modify: `tests/test_status_watch.py`

- [ ] **Step 1: Write failing test**

```python
def test_w4_retry_5x_with_4_sleeps_between_attempts(tmp_path, monkeypatch):
    """W4: 5 attempts, 4 sleeps between (no sleep after final fail)."""
    from status_cmd import _read_auto_run_with_retry
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text("not-json", encoding="utf-8")

    sleep_calls: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleep_calls.append(s))
    result = _read_auto_run_with_retry(auto_run_path, max_retries=5)
    assert result is None
    # Per Checkpoint 2 iter 1 melchior fix: 4 sleeps (between 5 attempts), not 5.
    assert sleep_calls == [0.05, 0.1, 0.2, 0.4]


def test_w4_slow_poll_fallback_after_3_consecutive_parse_failures():
    from status_cmd import WatchPollState
    state = WatchPollState(default_interval=1.0)
    state.record_parse_failure(); state.record_parse_failure(); state.record_parse_failure()
    assert state.current_interval == 2.0
    state.record_parse_failure()
    assert state.current_interval == 4.0
    state.record_parse_failure(); state.record_parse_failure(); state.record_parse_failure()
    assert state.current_interval <= 10.0
    state.record_parse_success()
    assert state.current_interval == 1.0
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement retry + WatchPollState**

In `status_cmd.py`:

```python
import time
from dataclasses import dataclass, field


def _read_auto_run_with_retry(
    auto_run_path: Path, *, max_retries: int = 5
) -> dict | None:
    """W4: 5x exponential backoff on JSON parse error.

    Sleep occurs BETWEEN attempts (not after the last one) — total budget
    is 4 sleeps (50+100+200+400ms = 750ms) for 5 attempts. Per Checkpoint 2
    iter 1 melchior fix (no wasted sleep after final failed attempt).
    """
    backoff_schedule = [0.05, 0.1, 0.2, 0.4]  # 4 sleeps between 5 attempts
    for attempt_idx in range(max_retries):
        try:
            return json.loads(auto_run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if attempt_idx < len(backoff_schedule):
                time.sleep(backoff_schedule[attempt_idx])
            # No sleep after final attempt; just return None below.
    return None


@dataclass
class WatchPollState:
    """W4 slow-poll fallback: track JSON parse failures, adjust interval.

    Critical (Checkpoint 2 iter 1 caspar fix): only triggered by ACTUAL
    JSON parse contention failures (5x retry exhaustion). Idle auto-runs
    that return same data successfully are NOT failures — they keep the
    default poll interval so operators see updates promptly when MAGI
    dispatch ends.
    """
    default_interval: float
    current_interval: float = field(default=0.0)
    consecutive_parse_failures: int = 0
    cap_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.current_interval == 0.0:
            self.current_interval = self.default_interval

    def record_parse_failure(self) -> None:
        """Called ONLY when _read_auto_run_with_retry returns None."""
        self.consecutive_parse_failures += 1
        if self.consecutive_parse_failures >= 3:
            self.current_interval = min(self.current_interval * 2, self.cap_seconds)

    def record_parse_success(self) -> None:
        """Called when JSON parsed (even if progress dict equals previous — idle)."""
        if self.current_interval > self.default_interval:
            self.current_interval = self.default_interval
        self.consecutive_parse_failures = 0
```

**Note (Checkpoint 2 iter 1 caspar fix):** previous design conflated "no progress change" with "parse failure". Now `record_parse_success()` is called whenever JSON loads cleanly, even if the progress dict is unchanged from the previous poll (idle case). Slow-poll triggers ONLY on contention (5x retry exhaustion), not on idle. Update the test accordingly:

```python
def test_w4_idle_does_not_trigger_slow_poll(tmp_path):
    """Idle auto-run (same data on each poll) does NOT trigger slow-poll fallback."""
    from status_cmd import WatchPollState
    state = WatchPollState(default_interval=1.0)
    # Simulate 10 successful idle polls (same data each time)
    for _ in range(10):
        state.record_parse_success()
    assert state.current_interval == 1.0  # NEVER doubled
    assert state.consecutive_parse_failures == 0


def test_w4_three_consecutive_parse_failures_triggers_slow_poll():
    from status_cmd import WatchPollState
    state = WatchPollState(default_interval=1.0)
    state.record_parse_failure(); state.record_parse_failure(); state.record_parse_failure()
    assert state.current_interval == 2.0
    state.record_parse_success()
    assert state.current_interval == 1.0
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/status_cmd.py tests/test_status_watch.py
git commit -m "feat: add W4 5x retry + slow-poll fallback to status --watch"
```

---

### Task S2-9: status --watch full poll loop + Ctrl+C handling + JSON mode (W2, W5)

**Files:**
- Modify: `skills/sbtdd/scripts/status_cmd.py`
- Modify: `tests/test_status_watch.py`

- [ ] **Step 1: Write failing tests**

```python
def test_w2_json_mode_emits_progress(tmp_path, capsys):
    from status_cmd import _watch_render_one
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(
        json.dumps({"progress": {"phase": 2}}), encoding="utf-8"
    )
    _watch_render_one(auto_run_path, json_mode=True, last_progress=None)
    captured = capsys.readouterr()
    line = json.loads(captured.out.strip())
    assert "timestamp" in line
    assert line["progress"]["phase"] == 2


def test_w5_ctrl_c_returns_130(tmp_path, monkeypatch):
    from status_cmd import watch_main
    auto_run_path = tmp_path / "auto-run.json"
    auto_run_path.write_text(
        json.dumps({"progress": {"phase": 1}}), encoding="utf-8"
    )

    def raise_kbi(*args, **kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr("status_cmd._watch_render_one", raise_kbi)
    rc = watch_main(auto_run_path, interval=1.0, json_mode=False)
    assert rc == 130
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Implement full watch_main**

In `status_cmd.py`:

```python
def _watch_render_one(
    auto_run_path: Path,
    *,
    json_mode: bool,
    last_progress: dict | None,
) -> dict | None:
    """Single-poll render. Returns the new progress dict or None on no-op."""
    data = _read_auto_run_with_retry(auto_run_path, max_retries=5)
    if data is None:
        return last_progress
    progress = data.get("progress", {})
    if progress != last_progress:
        if json_mode:
            sys.stdout.write(
                json.dumps({"timestamp": time.time(), "progress": progress}) + "\n"
            )
        else:
            sys.stdout.write("\r" + _watch_render_tty(progress) + " ")
        sys.stdout.flush()
    return progress


def watch_main(
    auto_run_path: Path,
    *,
    interval: float,
    json_mode: bool,
) -> int:
    """W1-W6: full status --watch poll loop.

    Distinguishes (a) idle (parse success, same data), (b) contention (parse
    failure after 5x retries), and (c) file-disappearance (path stops existing
    mid-poll, e.g., auto-run finished + cleaned up). Per Checkpoint 2 iter 1
    caspar + iter 2 caspar fixes.
    """
    validate_watch_interval(interval)
    if not auto_run_path.exists():
        sys.stderr.write("[sbtdd status] no auto run in progress\n")
        return 0
    state = WatchPollState(default_interval=interval)
    last_progress: dict | None = None
    try:
        while True:
            # Re-check existence each poll: file may disappear mid-watch
            # (auto-run completed + .claude/ cleanup). Distinguish from
            # contention.
            if not auto_run_path.exists():
                sys.stderr.write(
                    "\n[sbtdd status] auto run ended (auto-run.json no longer present)\n"
                )
                sys.stderr.flush()
                return 0
            data = _read_auto_run_with_retry(auto_run_path, max_retries=5)
            if data is None:
                # CONTENTION (parse failure): trigger slow-poll if sustained
                state.record_parse_failure()
                # Per Checkpoint 2 iter 3 caspar W9 fix: align breadcrumb
                # cadence with slow-poll trigger threshold (3) rather than 5.
                if state.consecutive_parse_failures % 3 == 0:
                    sys.stderr.write(
                        f"[sbtdd status] contention: JSON parse failed after "
                        f"5 retries (cumulative={state.consecutive_parse_failures})\n"
                    )
                    sys.stderr.flush()
            else:
                # PARSE SUCCESS (idle OR change): record success either way
                state.record_parse_success()
                progress = data.get("progress", {})
                if progress != last_progress:
                    if json_mode:
                        sys.stdout.write(
                            json.dumps({"timestamp": time.time(), "progress": progress}) + "\n"
                        )
                    else:
                        sys.stdout.write("\r" + _watch_render_tty(progress) + " ")
                    sys.stdout.flush()
                    last_progress = progress
            time.sleep(state.current_interval)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 130
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/status_cmd.py tests/test_status_watch.py
git commit -m "feat: status --watch full poll loop with JSON mode + SIGINT handling"
```

---

### Task S2-10: run_sbtdd.py argv extension (--watch, --interval, --json)

**Files:**
- Modify: `skills/sbtdd/scripts/run_sbtdd.py`
- Modify: `tests/test_run_sbtdd.py`

- [ ] **Step 1: Write failing test**

```python
def test_status_watch_dispatches_with_new_flags(monkeypatch):
    from run_sbtdd import main
    captured: dict = {}

    def fake_watch_main(auto_run_path, *, interval, json_mode):
        captured["interval"] = interval
        captured["json_mode"] = json_mode
        return 0

    monkeypatch.setattr("status_cmd.watch_main", fake_watch_main)
    rc = main(["status", "--watch", "--interval", "2.0", "--json"])
    assert rc == 0
    assert captured["interval"] == 2.0
    assert captured["json_mode"] is True
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Extend run_sbtdd argv parsing**

In `run_sbtdd.py`, add to the status subcommand parser:

```python
def _build_status_parser(subparsers):
    p = subparsers.add_parser("status", help="Report current sbtdd state")
    p.add_argument("--watch", action="store_true", help="Live poll of auto-run.json")
    p.add_argument(
        "--interval", type=float, default=1.0,
        help="Poll interval (seconds, >= 0.1)",
    )
    p.add_argument(
        "--json", dest="json_mode", action="store_true",
        help="Emit JSON per progress change",
    )
    return p


def _dispatch_status(args) -> int:
    if getattr(args, "watch", False):
        from status_cmd import watch_main
        from pathlib import Path
        return watch_main(
            Path(".claude/auto-run.json"),
            interval=args.interval,
            json_mode=args.json_mode,
        )
    return _existing_status_dispatch(args)
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/run_sbtdd.py tests/test_run_sbtdd.py
git commit -m "feat: extend run_sbtdd status with --watch, --interval, --json flags"
```

---

### Task S2-11: HF1 — recovery breadcrumb wording alignment

**Files:**
- Modify: `CHANGELOG.md` (verify wording)
- Modify: `skills/sbtdd/scripts/magi_dispatch.py` (verify wording — DO NOT touch logic)
- Modify: `tests/test_changelog.py`

- [ ] **Step 1: Write failing test**

In `tests/test_changelog.py`:

```python
from pathlib import Path


def test_hf1_recovery_breadcrumb_wording_aligned():
    """HF1: spec, CHANGELOG, and impl all use identical recovery breadcrumb wording."""
    canonical = "[sbtdd magi] synthesizer failed; manual synthesis recovery applied"
    spec = Path("sbtdd/spec-behavior.md").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    impl = Path("skills/sbtdd/scripts/magi_dispatch.py").read_text(encoding="utf-8")
    assert canonical in spec, "spec missing canonical wording"
    assert canonical in changelog, "CHANGELOG missing canonical wording"
    assert canonical in impl, "impl missing canonical wording"
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Adjust CHANGELOG and impl wording to match spec**

If CHANGELOG.md or magi_dispatch.py wording diverges from the canonical line, update them to use the exact text. Do NOT change the logic in magi_dispatch.py — only the message text. Search:

```bash
grep -n "synthesizer\|manual synthesis" CHANGELOG.md skills/sbtdd/scripts/magi_dispatch.py
```

Adjust as needed.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md skills/sbtdd/scripts/magi_dispatch.py tests/test_changelog.py
git commit -m "fix: align recovery breadcrumb wording across spec/CHANGELOG/impl"
```

---

### Task S2-12: HF2 — marker file schema docs match impl emission

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `tests/test_changelog.py`

- [ ] **Step 1: Write failing test**

```python
def test_hf2_marker_schema_docs_match_impl():
    impl = Path("skills/sbtdd/scripts/magi_dispatch.py").read_text(encoding="utf-8")
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    expected_fields = ["verdict", "iteration", "agents", "timestamp"]
    for field in expected_fields:
        assert f'"{field}"' in impl, f"impl missing marker field {field!r}"
        assert field in changelog, f"CHANGELOG missing marker field doc {field!r}"
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Update CHANGELOG to enumerate marker fields**

In `CHANGELOG.md` `[0.4.0]` Added section, ensure the marker file description lists `verdict`, `iteration`, `agents`, `timestamp`.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md tests/test_changelog.py
git commit -m "docs: align marker file schema docs with actual impl emission"
```

---

### Task S2-13: HF3 — F45 verdict-set delta documentation

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `tests/test_changelog.py`

- [ ] **Step 1: Write failing test**

```python
def test_hf3_f45_verdict_set_delta_documented():
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "VERDICT_RANK" in changelog
    assert "ValidationError" in changelog
    assert "tolerant parser" in changelog.lower()
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add F45 delta paragraph to CHANGELOG**

In `CHANGELOG.md` `[0.4.0]` Added section:

```markdown
- F45 tolerant parser additionally validates that the parsed `verdict` field
  is in the known `VERDICT_RANK` set; agent JSON with unknown verdict raises
  ValidationError instead of silently passing through. (Behavior delta vs the
  v0.4.0 strict parser baseline.)
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md tests/test_changelog.py
git commit -m "docs: document F45 verdict-set delta in CHANGELOG [0.4.0]"
```

---

### Task S2-14: CHANGELOG [0.5.0] entry

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `tests/test_changelog.py`

- [ ] **Step 1: Write failing test for [0.5.0] structure**

```python
def test_changelog_v0_5_0_entry_complete():
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [0.5.0]" in changelog
    section = changelog.split("## [0.5.0]")[1].split("## [0.4")[0]
    assert "### Added" in section
    assert "Heartbeat" in section
    assert "status --watch" in section
    assert "Per-stream timeout" in section
    assert "Origin disambiguation" in section
    assert "ProgressContext" in section
    assert "INV-32" in section or "INV-34" in section
    assert "### Deferred" in section
    assert "Feature G" in section
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add [0.5.0] entry**

Insert at top of `CHANGELOG.md`:

```markdown
## [0.5.0] - 2026-MM-DD

### Added
- **Heartbeat in-band emitter** (`scripts/heartbeat.py`) — context manager
  wrapping long subprocess dispatches; daemon thread emits stderr breadcrumb
  every 15s (configurable) with iter / phase / task / dispatch / elapsed.
- **`/sbtdd status --watch`** companion subcommand for out-of-band monitoring;
  default TTY rewrite-line render, `--json` flag for piping, `--interval`
  override.
- **Per-stream timeout (J3)** — `subprocess_utils.run_streamed_with_timeout`
  kills subprocess if all open streams silent for `auto_per_stream_timeout_seconds`
  (default 900s). `auto_no_timeout_dispatch_labels` allowlist exempts MAGI
  dispatches by default (`["magi-*"]`).
- **Origin disambiguation (J7)** — pump prefixes `[stdout]` / `[stderr]` when
  both streams emit chunks within a 50ms temporal window. Forward-only
  semantics (no retroactive prefix). Gated behind `auto_origin_disambiguation`
  (default ON).
- **ProgressContext dataclass** in `models.py`; lock-protected singleton in
  `scripts/heartbeat.py` with `get_current_progress()` / `set_current_progress()`.
- **5 new PluginConfig fields**: `auto_per_stream_timeout_seconds`,
  `auto_heartbeat_interval_seconds`, `status_watch_default_interval_seconds`,
  `auto_origin_disambiguation`, `auto_no_timeout_dispatch_labels`.
- **3 new invariants**: INV-32 (heartbeat resilience + queue-based incremental
  persistence), INV-33 (per-stream timeout last-resort), INV-34 (timeout/interval
  ratio + floor + ceiling validation).

### Changed
- `auto-run.json` schema gains `progress` key (ProgressContext snapshot,
  ISO 8601 UTC datetimes) and `heartbeat_failed_writes_total` counter.
  Backward-compat: v0.4.0 files without these fields parse cleanly.

### Hotfixes folded
- HF1: recovery breadcrumb wording aligned across spec / CHANGELOG / impl.
- HF2: marker file schema docs match actual emission fields.
- HF3: F45 verdict-set delta documented (validates `verdict in VERDICT_RANK`).

### Process notes
- Bundle accepted via INV-0 override after MAGI Loop 2 4-iter convergence
  pattern (verdict stable `GO_WITH_CAVEATS (3-0)` full no-degraded).
  Known Limitations from iter 4 documented in spec sec.11; resolution in
  this implementation phase.
- True parallel 2-subagent dispatch repeated (Heartbeat track vs
  Streaming/Watch/Docs track), surfaces 100% disjoint, ~6-8h wall time.

### Deferred (rolled to v1.0.0)
- Feature G: MAGI -> /requesting-code-review cross-check meta-reviewer.
- F44.3: retried_agents propagation to auto-run.json.
- J2: ResolvedModels preflight dataclass.
- Feature I: schema_version + migration tool.
- Feature H: Group B re-eval + INV-31 default decision.
```

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md tests/test_changelog.py
git commit -m "docs: add CHANGELOG [0.5.0] entry"
```

---

### Task S2-15: SKILL.md v0.5 notes section

**Files:**
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `tests/test_skill_md.py`

- [ ] **Step 1: Write failing test**

```python
def test_skill_md_has_v0_5_notes_section():
    skill_md = Path("skills/sbtdd/SKILL.md").read_text(encoding="utf-8")
    assert "v0.5" in skill_md
    assert "status --watch" in skill_md
    assert "heartbeat" in skill_md.lower()
```

- [ ] **Step 2: Run + verify fail**

- [ ] **Step 3: Add v0.5 notes section**

Append to `skills/sbtdd/SKILL.md` (after existing v0.4 notes, before final references):

```markdown
### v0.5 notes

v0.5.0 adds the observability pillar:

- **Heartbeat in-band**: long dispatches (MAGI, `/requesting-code-review`)
  emit a stderr tick every 15s showing `iter / phase / task / dispatch /
  elapsed`. Configurable via `auto_heartbeat_interval_seconds` (5-60s,
  default 15).
- **`/sbtdd status --watch`**: companion subcommand for out-of-band
  monitoring. Run from a second terminal: `python run_sbtdd.py status --watch`.
  Use `--json` for piping; `--interval N` for poll cadence.
- **Per-stream timeout** (`auto_per_stream_timeout_seconds`, default 900s):
  kills subprocess if all open streams are silent for the timeout window.
  MAGI dispatches are exempt by default (`auto_no_timeout_dispatch_labels:
  ["magi-*"]`).

See `docs/v0.5.0-config-matrix.md` for the full field/invariant matrix.
```

Also fix any HF1 wording in v0.4 notes section if divergent.

- [ ] **Step 4: Run + verify pass**

- [ ] **Step 5: Commit**

```bash
git add skills/sbtdd/SKILL.md tests/test_skill_md.py
git commit -m "docs: add v0.5 notes section to SKILL.md"
```

---

### Task S2-16: CLAUDE.md release notes pointer for v0.5.0

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Open CLAUDE.md and locate the v0.4 release notes section**

- [ ] **Step 2: Append v0.5.0 release notes pointer**

```markdown
## v0.5.0 release notes

The v0.5.0 observability pillar (heartbeat + `/sbtdd status --watch` +
per-stream timeout J3 + origin disambiguation J7 + 3 v0.4.1 doc-alignment
hotfixes) shipped in v0.5.0. Bundle accepted via INV-0 override after
MAGI Loop 2 4-iter convergence pattern (verdict stable `GO_WITH_CAVEATS
(3-0)` full no-degraded). Known Limitations from iter 4 documented in
`sbtdd/spec-behavior.md` sec.11; resolution applied during implementation.
See `CHANGELOG.md` `[0.5.0]` for the as-shipped behavior.
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add v0.5.0 release notes pointer to CLAUDE.md"
```

---

### Task S2-17: docs/v0.5.0-config-matrix.md (R9 single-source matrix)

**Files:**
- Create: `docs/v0.5.0-config-matrix.md`

- [ ] **Step 1: Create the matrix doc**

Create `docs/v0.5.0-config-matrix.md`:

```markdown
# v0.5.0 Config Matrix — single-source-of-truth

> **Purpose (R9 mitigation):** prevent doc-drift recurrence by maintaining a
> single source of truth for every new PluginConfig field and every new
> invariant. HF1-HF3 hotfixes were caused by exactly this drift class in v0.4.0.
>
> If you change a default, validation, or wording for any of these,
> update THIS doc + the related code + the related test in lock-step.

## Config fields (5)

| Field | Default | Type | Range | Where defined | Where validated | Where documented |
|-------|---------|------|-------|---------------|-----------------|------------------|
| `auto_per_stream_timeout_seconds` | `900` | `int` | `>= 5 * auto_heartbeat_interval_seconds` (INV-34 clause 1) | `config.py:PluginConfig` | `config.py:load_plugin_local` | spec sec.2.3, CHANGELOG `[0.5.0]`, SKILL.md v0.5 notes |
| `auto_heartbeat_interval_seconds` | `15` | `int` | `[5, 60]` (INV-34 clauses 2 + 3) | `config.py:PluginConfig` | `config.py:load_plugin_local` | spec sec.2.1, CHANGELOG `[0.5.0]`, SKILL.md v0.5 notes |
| `status_watch_default_interval_seconds` | `1.0` | `float` | `>= 0.1` (validated by `validate_watch_interval`) | `config.py:PluginConfig` | `status_cmd.validate_watch_interval` | spec sec.2.2, CHANGELOG `[0.5.0]` |
| `auto_origin_disambiguation` | `True` | `bool` | n/a | `config.py:PluginConfig` | (no validation) | spec sec.2.4, CHANGELOG `[0.5.0]` |
| `auto_no_timeout_dispatch_labels` | `("magi-*",)` | `tuple[str, ...]` | bare `"*"` rejected | `config.py:PluginConfig` | `config.py:load_plugin_local` | spec sec.2.3, CHANGELOG `[0.5.0]` |

## Invariants (3 new)

| Invariant | Statement | Enforcement | Where defined | Tests |
|-----------|-----------|-------------|---------------|-------|
| **INV-32** | Heartbeat thread NEVER blocks/kills auto run; first-failure stderr breadcrumb; counter persisted incrementally via queue → main thread → auto-run.json | `scripts/heartbeat.py:HeartbeatEmitter._emit_tick` + `auto_cmd._drain_heartbeat_queue_and_persist` | spec sec.2.7 | `tests/test_heartbeat.py::test_heartbeat_first_failure_*`, `tests/test_auto_progress.py::test_update_progress_drains_*` |
| **INV-33** | Per-stream timeout is last-resort kill (heartbeat 1st-line, watch 2nd-line, timeout 3rd-line) | `subprocess_utils.run_streamed_with_timeout` | spec sec.2.7 | `tests/test_subprocess_utils.py::test_t1_*` |
| **INV-34** | Timeout-vs-interval relationship: `timeout >= 5*interval`; interval in `[5, 60]` | `config.py:load_plugin_local` (3 clauses with distinct error messages) | spec sec.2.7 | `tests/test_config.py::test_inv34_clause_*` |

## Worked examples

### Example 1: Default config
```yaml
# (no overrides; all defaults applied)
```
Resulting validated config: timeout=900s, interval=15s, watch_interval=1.0s, origin=True, allowlist=("magi-*",). All INV-34 clauses satisfied (900 >= 75, 15 in [5,60]).

### Example 2: Aggressive CI config
```yaml
auto_per_stream_timeout_seconds: 600
auto_heartbeat_interval_seconds: 10
auto_origin_disambiguation: false
```
Validates: 600 >= 50, 10 in [5,60]. Origin disambiguation off for parser-strict consumers.

### Example 3: INV-34 clause 1 violation
```yaml
auto_per_stream_timeout_seconds: 50
auto_heartbeat_interval_seconds: 15
```
Raises: `ValidationError: INV-34 clause 1: auto_per_stream_timeout_seconds (50) must be >= 5 * auto_heartbeat_interval_seconds (15) = 75; got 50`.

### Example 4: INV-34 clause 2 violation
```yaml
auto_heartbeat_interval_seconds: 120
```
Raises: `ValidationError: INV-34 clause 2: auto_heartbeat_interval_seconds must be <= 60s ...; got 120`.

### Example 5: INV-34 clause 3 violation
```yaml
auto_heartbeat_interval_seconds: 2
```
Raises: `ValidationError: INV-34 clause 3: auto_heartbeat_interval_seconds must be >= 5s ...; got 2`.

### Example 6: Allowlist bare wildcard rejected
```yaml
auto_no_timeout_dispatch_labels: ["*"]
```
Raises: `ValidationError: auto_no_timeout_dispatch_labels: bare '*' rejected (would defeat timeout); use specific glob like 'magi-*'`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/v0.5.0-config-matrix.md
git commit -m "docs: add v0.5.0 config matrix (R9 single-source mitigation)"
```

---

## Pre-merge prep (orchestrator-level after both subagents complete)

### Task O-1: `make verify` clean post-merge

- [ ] Run `make verify` locally with both subagent commits merged on the feature branch.
- [ ] Expected: pytest pass (818 baseline + ~30-40 new tests = 848-858), ruff check 0 warnings, ruff format clean, mypy --strict 0 errors.
- [ ] Total runtime <= 90s (NF-A budget).

### Task O-2: Pre-merge MAGI gate (Loop 1 + Loop 2)

- [ ] Loop 1 surrogate: `make verify` clean (already done in O-1).
- [ ] Loop 2: invoke `/magi:magi` on the cumulative diff vs `4538914`.
- [ ] If iter 1 verdict >= `GO_WITH_CAVEATS` full no-degraded: proceed.
- [ ] If iter 1 verdict has structural conditions: route via `/receiving-code-review` + mini-cycle TDD; iterate up to cap=5 (auto_magi_max_iterations).

### Task O-3: Version bump

- [ ] Modify `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`: bump `"version"` from `0.4.0` to `0.5.0`. Both files MUST match.

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "chore: bump to 0.5.0"
```

### Task O-4: Tag + push (with explicit user authorization)

- [ ] Create annotated tag: `git tag -a v0.5.0 -m "v0.5.0 observability foundation"`.
- [ ] **Pause for explicit user authorization before `git push`** (per `~/.claude/CLAUDE.md` Git rules).
- [ ] On authorization: merge `feature/v0.5.0-observability` to `main`, then `git push origin main && git push origin v0.5.0`.

---

## Self-review checklist (run after writing this plan, before dispatch)

- [x] **Spec coverage:** every spec sec.2 deliverable mapped to a task.
  - Heartbeat emitter (sec.2.1, H1-H6) → S1-2 through S1-7 + S1-10
  - status --watch (sec.2.2, W1-W6) → S2-7 through S2-10
  - Per-stream timeout (sec.2.3, T1-T8) → S2-4 through S2-5
  - Origin disambiguation (sec.2.4, O1-O4) → S2-6
  - v0.4.1 hotfixes (sec.2.5, HF1-HF3) → S2-11 through S2-13
  - ProgressContext schema (sec.3) → S1-1
  - 5 PluginConfig fields + INV-34 + allowlist validation → S2-1 through S2-3
  - Mechanical smoke fixture (R2.3) → S1-8
  - 10 transition writer hooks (sec.3) → S1-9
  - HeartbeatEmitter wrapping (sec.4.2) → S1-10
  - Single-writer drain + persistence + ISO 8601 → S1-11, S1-12, S1-13
  - CHANGELOG / SKILL / CLAUDE / matrix → S2-14 through S2-17
- [x] **Placeholder scan:** no "TBD", "implement later", "similar to Task N" without code, etc.
- [x] **Type consistency:** ProgressContext fields used uniformly across S1-1 (definition), S1-9 (writer), S1-12 (serializer). PluginConfig new fields named consistently across S2-1, S2-2, S2-3, S2-15, S2-17. HeartbeatEmitter API stable across S1-2 through S1-10.

---

## Execution Handoff

**Plan complete and saved to `planning/claude-plan-tdd-org.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — orchestrator dispatches a fresh subagent per task, reviews between tasks, fast iteration. Aligns with v0.4.0 true parallel pattern (Subagent #1 + Subagent #2 dispatched in single message, surfaces disjoint).

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**

**If Subagent-Driven chosen:**
- REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`.
- Per spec sec.4.4 + 6.2 (true parallel surfaces 100% disjoint), Subagent #1 + Subagent #2 are dispatched in a SINGLE message with two `Agent` tool calls (validated v0.4.0 pattern).
- Each subagent owns its task list strictly per the forbidden-files matrix in pre-flight.

**If Inline Execution chosen:**
- REQUIRED SUB-SKILL: `superpowers:executing-plans`.
- Sequential task-by-task in this session with manual checkpoints.

Note: per project convention (`CLAUDE.local.md` §1 paso 5) the next step **before any execution** is MAGI Checkpoint 2 — invoke `/magi:magi` on `@sbtdd/spec-behavior.md` AND `@planning/claude-plan-tdd-org.md` simultaneously, iterate until verdict >= `GO_WITH_CAVEATS` full no-degraded, write final approved plan to `planning/claude-plan-tdd.md`.
