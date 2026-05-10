# v1.0.7 `--parallel` Operational Unblock + Polish Implementation Plan

> Generado 2026-05-09 a partir de sbtdd/spec-behavior.md v1.0.7 via
> superpowers:writing-plans skill (interactive session, brainstorming
> Q1'-Q5' resolved). Frontmatter required by spec_lint R5.
>
> **Iter-3 carry-forward applied 2026-05-09**: MAGI Checkpoint 2 iter 2
> verdict GO_WITH_CAVEATS (3-0) — Mel APPROVE 82% + Bal APPROVE 82% +
> Cas CONDITIONAL 74%. 1 CRITICAL (sidecar PID collision, cas) + 9
> WARNING + 9 INFO. Cas item (5) "T7 commit-level collapse stays"
> KEEPS T7 in scope. Resolution: apply ALL 7 of Cas's inline fixes +
> swap T6 → T2 ordering per Bal+Cas WARNING. Pillar C T7 NOT deferred.
> 8-cycle no-override streak goal preserved; iter 3 expects clean
> convergence at 0 CRITICAL.
>
> **Iter-3 carry-forward inlined deltas**:
> - **Sidecar collision (cas iter-2 CRITICAL)**: T2 implementation
>   uses `<pid>-<monotonic_ns>-<uuid8>-verify.json` filename + parent
>   post-batch merge LOUD-FAILS via `ConcurrentDispatchError` on
>   missing sidecar. New escenarios A2-9 + A2-10.
> - **T6 → T2 ordering swap (bal+cas iter-2 WARNING)**: execution
>   order changed to T1 → T6 → T2 → T3 → T4 → T5 → T7 → T8. T6 (B3
>   atomic_write_json retry) lands BEFORE T2 (which calls it via
>   `_persist_worker_verify_evidence`). Eliminates documented
>   PermissionError flake risk during T3 dogfood.
> - **A3 PTY-path assertion (cas iter-2 WARNING)**: NEW escenario
>   A3-3 + integration test assertion: on POSIX, sidecar evidence must
>   include TTY-observation marker; SKIPPED on Windows.
> - **R9 risk register (cas iter-2 WARNING)**: per-worker artifact
>   collision class added to spec sec.8.
> - **T7 4-doc Red commit bisect (mel+bal+cas iter-2 WARNING)**:
>   discriminating test class names preserved (`TestC1*`, `TestC5*`,
>   `TestC6*`, `TestC7*`); CHANGELOG Process notes will document the
>   collapse trade-off so it isn't generalized.
>
> **Iter-2 carry-forward applied 2026-05-09**: MAGI Checkpoint 2 iter 1
> verdict GO_WITH_CAVEATS (3-0) full no-degraded with 5 CRITICAL + 10
> WARNING + 5 INFO findings. Triage applied via INV-29 receiving-code-review
> discipline. Inlined deltas:
>
> - **C1 (mel)**: T1 prod code adds `_close_pty_master(proc)` lifecycle
>   helper + Popen-failure leak guard.
> - **C2/C5 (mel+cas)**: Pillar C C1+C5+C6+C7 collapsed into ONE plan
>   task (T7) with real Refactor diff (cross-link K-4 helper docs from
>   C1+C6); C-X-K3-Removal stays separate (T8). 11 tasks → 8 tasks.
> - **C3 (cas)**: T3 fixture rewritten — each worker invokes real
>   `close-phase` chain via `pyproject.toml`-bearing fixture project
>   so sec.0.1 chain dispatches and trips chicken-and-egg surface.
> - **C4 (cas)**: T2 worker-mode bypass replaces `["make", "verify"]`
>   with explicit sec.0.1 chain (`pytest` / `ruff check` /
>   `ruff format --check` / `mypy`) + per-worker
>   `<root>/.claude/auto-run-workers/<pid>-verify.json` sidecar
>   capture for INV-16 evidence-before-assertions continuity.
> - **W1 (mel)**: T2 adds A2-8 regression test pinning orchestrator-mode
>   pass-through.
> - **W3 (mel)**: spec sec.8 R7 (PTY EIO/SIGHUP race) + R8 (worker
>   guard false-positive) added.
> - **W7 (cas)**: T1 A1-1 test exercises real `sys.stdin.isatty() == True`
>   assertion via worker-writes-isatty fixture script.
> - **W8 (cas)**: T1 implementation wraps `subprocess.Popen` in
>   try/except closing slave_fd on Popen failure.
> - **W10 (cas)**: T8 (= old T11) Green commit prefix `--variant fix`
>   framed as "closes v1.0.7 C5-documented monkeypatch footgun" in
>   task header.
> - **W2/W9 deferred**: PTY drain under large output → v1.0.8;
>   C5↔C-X-K3-Removal vestigial-comment → kept as transitional
>   archaeology (T7 commit → T8 commit window has educational value).
>
> v1.0.7 = **`--parallel` operational unblock cycle (NON-POSTPONABLE)** per
> user mandate 2026-05-09 ("dejar parallel completamente operacional").
> Three pillars:
> - Pillar A PRIMARY HARD-LOCKED: A1 POSIX PTY allocation + A2 Windows
>   hybrid Option B-W3 (with Q2'=b promotion of worker-context runtime
>   guard) + A3 F-A2 dogfood empirical validation.
> - Pillar B LOCKED (v1.0.6 dogfood findings, ordered Q3'=b smallest
>   fix first): B5 drift detector line-anchored regex + B4
>   spec_review_dispatch file-reference + B3 atomic_write_json
>   PermissionError retry.
> - Pillar C LOCKED (selective polish, Q4'=a all 5; iter-2 collapsed):
>   T7 combined polish (C1+C5+C6+C7) + T8 C-X-K3-Removal.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax for tracking.

**Goal:** Ship v1.0.7 — close v1.0.6-deferred Pillar A LOCKED commitment
(PTY allocation in worker subprocess spawn unblocking `auto --parallel`
end-to-end on POSIX + Windows hybrid) + ship 3 Pillar B v1.0.6 dogfood
findings (B5 drift regex false-positive, B4 spec_review_dispatch
WinError 206, B3 atomic_write_json Windows PermissionError flake) + 5
cherry-picked Pillar C polish items (C1+C5+C6+C7+C-X-K3-Removal).
**8 plan tasks (collapsed from 11 per iter-2 C2/C5 carry-forward); single
subagent sequential execution per Q1'=a forced by chicken-and-egg until
Pillar A ships + v1.0.8 own-cycle validates.**

**Architecture:** Pillar A introduces `subprocess_utils._spawn_worker_with_pty`
(POSIX-only `pty.openpty()` per worker spawn) + `auto_cmd._spawn_worker`
cross-platform dispatcher (POSIX → A1 PTY; Windows →
`subprocess.PIPE` + `SBTDD_AUTO_PARALLEL_WORKER=1` env marker) +
`close_phase_cmd._run_verification` worker-mode bypass (runs `make verify`
shell directly, sidestepping interactive `/verification-before-completion`
skill) + Q2'=b worker-context runtime guard in
`superpowers_dispatch.invoke_skill` (defense-in-depth: raises if a worker
ever attempts to dispatch a `_SUBPROCESS_INCOMPATIBLE_SKILLS` member).
Pillar B fixes 3 v1.0.6-discovered defects: B5 swaps unanchored
`"- [ ]" in section` substring check for line-anchored multiline regex
`^[ \t]*- \[ \]` in `drift._plan_all_tasks_complete`; B4 writes the
spec-reviewer prompt to `<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md`
and passes `@<filepath>` reference in argv (cmdline length bounded by
filepath, ~32K argv limit no longer triggered by prompt content); B3 wraps
`state_file.atomic_write_json`'s `os.replace` in 3-attempt
retry-with-backoff (`100ms × attempt-number`) absorbing AV-scanner /
concurrent-writer Windows `PermissionError` flakes. Pillar C is doc +
1-cycle K-3 alias removal. **Single subagent sequential execution per
Q1'=a chicken-and-egg constraint** — no `--parallel` self-dispatch until
A3 dogfood validates the fix end-to-end on Windows.

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict,
stdlib-only on hot paths (`pty` is POSIX stdlib; Windows path uses
`subprocess` only). TDD-Guard active. Brainstorming Q-decisions:
Q1=B operational unblock NON-POSTPONABLE; Q2=Fix B Option B-W3 hybrid
(POSIX `pty.openpty()` + Windows `subprocess.PIPE` +
`SBTDD_AUTO_PARALLEL_WORKER` env + `_run_verification` bypass);
Q3=a strict no-INV-0 stance; Q1'=a single subagent sequential (forced by
chicken-and-egg); Q2'=b promote C3 worker env runtime guard INTO Pillar
A A2 as defense-in-depth; Q3'=b Pillar B order B5 → B4 → B3 (smallest
fix first unblocks `make verify`); Q4'=a ship all 5 Pillar C items per
baseline; Q5'=a default G2 ladder.

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no
  AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of
  `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` /
  `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1:
  `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before
  the commit.
- Every new `.py` file starts with the 4-line header:
  `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`,
  `# Version: 1.0.0`, `# Date: 2026-05-09`.
- **Phase close protocol (v1.0.4 mandate + v1.0.5 Item D Q3-A HARD-BLOCK
  enforced)**: subagent MUST invoke
  `python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each
  Red/Green/Refactor verify-clean. Manual `git commit` per phase BYPASSES
  the phase-advance + state-file update + verification gate; **close-task
  HARD-BLOCKS via `_preflight` when commit chain since last
  `chore: mark task` lacks the canonical TDD triplet**. Override
  available via `--skip-preflight` (audit-logged to stderr; emergency
  only).
- **Task close protocol**: subagent MUST invoke
  `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`
  after Refactor close-phase. Use `--skip-spec-review` to bypass INV-31
  spec-reviewer dispatch (~1-2 min/task overhead acceptable but not
  required for these infrastructure items).
- **Sequential execution mandate**: Q1'=a forces SINGLE subagent
  through the full chain. **Order (post iter-3 carry-forward T6 → T2
  swap)**: T1 → T6 → T2 → T3 → T4 → T5 → T7 → T8. NO
  `auto --parallel` self-dispatch during v1.0.7 own-cycle
  (chicken-and-egg until Pillar A ships + A3 dogfood validates).
  v1.0.7 own-cycle uses `auto` sequential foreground OR manual
  subagent dispatch via Agent tool.
- **Within-Pillar-A ordering (HARD)**: T1 (A1) must land BEFORE T2 (A2)
  because A2's cross-platform dispatcher imports `_spawn_worker_with_pty`
  + `_close_pty_master` from `subprocess_utils`. T3 (A3) integration
  test must run AFTER T1+T2 ship.
- **Within-Pillar-C ordering (HARD, post iter-2 collapse)**: T7
  (combined C1+C5+C6+C7 polish) must land BEFORE T8 (C-X-K3-Removal
  alias removal) — T7 adds the C5 warning comment on the alias line;
  T8 removes both alias AND comment together.
- INV-37 composite-signature tripwire preserved unchanged.
- Item C v1.0.2 spec_lint gate (R1-R5) preserved unchanged.
- v1.0.4 Items A+B membership-based subprocess gate preserved + EXTENDED
  with v1.0.7 A2 Q2'=b worker-context runtime guard.
- v1.0.4 Path 3 `--parallel` architecture preserved unchanged. v1.0.7
  EXTENDS with PTY allocation (POSIX) + Windows hybrid bypass (Windows).
- v1.0.5 per-worker sidecar (I-1) + scratch (I-2) + flag forwarding (I-3)
  patterns preserved unchanged.
- v1.0.6 J-1+J-2+J-3 headless detection helper +
  `superpowers_dispatch.invoke_skill` headless guard preserved + EXTENDED
  with v1.0.7 A2 Q2'=b worker-context runtime guard.

**Commit prefix map per phase** (from `CLAUDE.local.md` §5):

| Phase | Prefix | Closer |
|-------|--------|--------|
| Red (failing test) | `test:` | `close-phase` |
| Green (impl) | `feat:` (new module/feature) or `fix:` (bug fix) | `close-phase` |
| Refactor | `refactor:` | `close-phase` |
| Task close | `chore:` (automated) | `close-task --skip-spec-review` |

---

## Pillar A PRIMARY HARD-LOCKED — `auto --parallel` operational unblock

### Task 1: A1 — POSIX PTY allocation + lifecycle helper + leak guard

**Files:**
- Modify: `skills/sbtdd/scripts/subprocess_utils.py` (add
  `_spawn_worker_with_pty(argv, env) -> subprocess.Popen[bytes]` +
  `_close_pty_master(proc) -> None` module-level helpers; POSIX-only;
  raises `RuntimeError` on Windows for the spawn helper)
- Modify: `tests/test_subprocess_utils.py` (extend with
  `TestSpawnWorkerWithPty` class covering escenarios A1-1 through A1-5)
- Create: `tests/fixtures/pty/worker_isatty.py` (worker fixture script
  that writes `isatty=<sys.stdin.isatty()>` to stdout — used by A1-1
  to validate worker observes a TTY)

Covers escenarios A1-1 (W7 isatty assertion), A1-2, A1-3 (C1 lifecycle
helper drain+close), A1-5 (W8 Popen-failure leak guard) from spec
sec.4.1.

#### Red Phase

- [x] **Step 1: Write failing tests in `tests/test_subprocess_utils.py`**

First, create the worker fixture at
`tests/fixtures/pty/worker_isatty.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 A1 worker fixture: writes isatty=<bool> to stdout."""
import sys
sys.stdout.write("isatty=" + str(sys.stdin.isatty()))
sys.stdout.flush()
```

Then append to `tests/test_subprocess_utils.py`:

```python
class TestSpawnWorkerWithPty:
    """v1.0.7 A1 POSIX PTY allocation + lifecycle per spec sec.4.1."""

    def test_posix_worker_observes_tty_via_isatty(self) -> None:
        """A1-1 (W7 carry-forward): worker sees real TTY via isatty()."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only test")
        worker_script = (
            Path(__file__).parent / "fixtures" / "pty" / "worker_isatty.py"
        )
        proc = subprocess_utils._spawn_worker_with_pty(
            [sys.executable, str(worker_script)],
            env=dict(os.environ),
        )
        try:
            # Read from master fd to capture worker stdout.
            output = b""
            proc.wait(timeout=10)
            try:
                while True:
                    chunk = os.read(proc._pty_master_fd, 4096)
                    if not chunk:
                        break
                    output += chunk
            except OSError:
                pass  # worker closed slave; drain done
            assert proc.returncode == 0
            # CRITICAL: worker must observe TTY (not just parent).
            assert b"isatty=True" in output, (
                f"worker did not observe TTY. output={output!r}"
            )
        finally:
            subprocess_utils._close_pty_master(proc)

    def test_windows_worker_spawn_raises_runtime_error(self) -> None:
        """A1-2: Windows worker spawn raises if PTY helper called directly."""
        if sys.platform != "win32":
            pytest.skip("Windows-only guard test")
        with pytest.raises(RuntimeError, match="POSIX-only"):
            subprocess_utils._spawn_worker_with_pty(
                [sys.executable, "-c", "pass"],
                env=dict(os.environ),
            )

    def test_close_pty_master_drains_then_closes_idempotent(
        self,
    ) -> None:
        """A1-3 (C1 carry-forward): lifecycle helper drains + closes + idempotent."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only test")
        proc = subprocess_utils._spawn_worker_with_pty(
            [sys.executable, "-c", "import sys; sys.stdout.write('hello'); sys.stdout.flush()"],
            env=dict(os.environ),
        )
        proc.wait(timeout=10)
        master_fd = proc._pty_master_fd
        assert isinstance(master_fd, int)
        # First close: drains + closes + sets attr to None.
        subprocess_utils._close_pty_master(proc)
        assert proc._pty_master_fd is None
        # Verify fd is actually closed (os.close should raise EBADF).
        with pytest.raises(OSError):
            os.close(master_fd)
        # Second close: idempotent no-op.
        subprocess_utils._close_pty_master(proc)
        assert proc._pty_master_fd is None

    def test_popen_failure_does_not_leak_fds(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A1-5 (W8 carry-forward): Popen failure closes both master + slave fds."""
        if sys.platform == "win32":
            pytest.skip("POSIX-only test")
        leaked_fds: list[int] = []
        original_popen = subprocess.Popen

        def boom_popen(*args: object, **kwargs: object) -> object:
            # Capture the fds passed via stdin= kwarg before raising.
            slave = kwargs.get("stdin")
            if isinstance(slave, int):
                leaked_fds.append(slave)
            raise OSError("simulated spawn failure")

        monkeypatch.setattr(
            "subprocess_utils.subprocess.Popen", boom_popen
        )
        with pytest.raises(OSError, match="simulated spawn failure"):
            subprocess_utils._spawn_worker_with_pty(
                [sys.executable, "-c", "pass"],
                env=dict(os.environ),
            )
        # Both fds the helper opened should be closed; if the slave_fd
        # we captured is still open, os.close should succeed (=leak).
        for fd in leaked_fds:
            with pytest.raises(OSError):
                os.close(fd)
```

Add at the top of `tests/test_subprocess_utils.py` if missing:

```python
import os
import subprocess
import sys
from pathlib import Path

import pytest
```

Add at the top of `tests/test_subprocess_utils.py` if missing:

```python
import os
import sys
from pathlib import Path

import pytest
```

- [x] **Step 2: Run tests to verify failure**

Run on Windows dev env: `pytest tests/test_subprocess_utils.py::TestSpawnWorkerWithPty -v`
Expected: `test_windows_worker_spawn_raises_runtime_error` FAILS with
`AttributeError: module 'subprocess_utils' has no attribute '_spawn_worker_with_pty'`.
The two POSIX-only tests SKIP on Windows.

- [x] **Step 3: Run `make verify` (must show only the new test failures)**

Run: `make verify`
Expected: pytest collects, the 3 new tests fail/skip per platform, all
other tests pass; ruff + mypy clean.

- [x] **Step 4: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 A1 POSIX PTY allocation tests"`

Expected: commit with prefix `test:` lands; state advances to `green`.

#### Green Phase

- [x] **Step 5: Implement `_spawn_worker_with_pty` + `_close_pty_master` in `subprocess_utils.py`**

Add at the bottom of `skills/sbtdd/scripts/subprocess_utils.py`:

```python
def _spawn_worker_with_pty(
    argv: list[str],
    env: dict[str, str],
) -> "subprocess.Popen[bytes]":
    """v1.0.7 A1 POSIX: allocate pseudo-TTY for worker subprocess.

    Workers spawned via this helper inherit the slave end as
    stdin/stdout/stderr; orchestrator holds master end via
    ``proc._pty_master_fd``. Skill subprocess chain (close-phase ->
    /verification-before-completion) inherits TTY from worker ->
    interactive prompts work -> no chicken-and-egg hang (see v1.0.6
    empirical findings + spec sec.2.1).

    POSIX-only. Windows callers must use the Option B-W3 hybrid path
    (``subprocess.PIPE`` + ``SBTDD_AUTO_PARALLEL_WORKER`` env +
    ``close_phase_cmd._run_verification`` worker-mode bypass per A2).

    v1.0.7 iter-2 carry-forward W8: Popen failure closes BOTH master and
    slave fds before re-raising, preventing fd leak on spawn failure.

    Args:
        argv: Subprocess argv (executable + args). ``shell=False``
            invariant from sec.S.8.6 preserved.
        env: Environment dict passed to the subprocess. Caller must
            inject ``SBTDD_AUTO_PARALLEL_WORKER=1`` (done by
            ``auto_cmd._spawn_worker`` cross-platform dispatcher).

    Returns:
        ``subprocess.Popen`` instance with ``_pty_master_fd`` integer
        attribute set for downstream :func:`_close_pty_master` cleanup.

    Raises:
        RuntimeError: When invoked on Windows. Defensive guard against
            test-harness misuse; production callers route via
            ``auto_cmd._spawn_worker`` dispatcher.
        OSError: Re-raised from underlying ``subprocess.Popen``; both
            master and slave fds closed before re-raise (no leak).
    """
    # pty is POSIX-only stdlib; local-import keeps the Windows path
    # of subprocess_utils.py importable without conditional top-level
    # ImportError handling.
    import pty
    import os as _os

    if sys.platform == "win32":
        raise RuntimeError(
            "_spawn_worker_with_pty is POSIX-only; Windows uses "
            "Option B-W3 hybrid (see auto_cmd._spawn_worker)"
        )
    master_fd, slave_fd = pty.openpty()
    try:
        proc = subprocess.Popen(
            argv,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            close_fds=True,
        )
    except Exception:
        # v1.0.7 W8 leak guard: close both fds on Popen failure.
        try:
            _os.close(master_fd)
        except OSError:
            pass
        try:
            _os.close(slave_fd)
        except OSError:
            pass
        raise
    _os.close(slave_fd)  # parent only needs master after success
    proc._pty_master_fd = master_fd  # type: ignore[attr-defined]
    return proc


def _close_pty_master(proc: "subprocess.Popen[bytes]") -> None:
    """v1.0.7 A1 lifecycle: drain + close master fd. Idempotent.

    v1.0.7 iter-2 carry-forward C1 resolution: orchestrator MUST call
    this helper after ``proc.wait()`` for every worker spawned via
    :func:`_spawn_worker_with_pty`. Drains buffered output from the
    master end before close; without drain, subsequent reads raise EIO
    on POSIX. Idempotent: safe to call multiple times — second
    invocation observes ``_pty_master_fd is None`` and returns no-op.

    EIO/SIGHUP race tolerance (R7): if the worker closes the slave end
    OR receives SIGHUP between ``proc.wait()`` and this helper, the
    drain loop may observe ``OSError(EIO)`` immediately on first read.
    Catch broadly + treat as drain-complete; worker exit code +
    per-worker sidecar evidence preserve the actual results.

    Args:
        proc: ``subprocess.Popen`` returned by
            :func:`_spawn_worker_with_pty`.
    """
    import os as _os

    master_fd = getattr(proc, "_pty_master_fd", None)
    if master_fd is None:
        return
    try:
        while True:
            data = _os.read(master_fd, 4096)
            if not data:
                break
    except OSError:
        # Worker already closed slave end OR SIGHUP race; drain done.
        pass
    try:
        _os.close(master_fd)
    except OSError:
        # Already closed (idempotent).
        pass
    proc._pty_master_fd = None  # type: ignore[attr-defined]
```

- [x] **Step 6: Run the new tests to verify they pass**

Run: `pytest tests/test_subprocess_utils.py::TestSpawnWorkerWithPty -v`
Expected: on POSIX, all 3 PASS; on Windows, the guard test PASSES, the
other 2 SKIP.

- [x] **Step 7: Run `make verify`**

Expected: pytest all green; ruff + mypy clean.

- [x] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.7 A1 POSIX PTY allocation in subprocess_utils"`

Expected: commit with prefix `feat:` lands; state advances to `refactor`.

#### Refactor Phase

- [x] **Step 9: Tighten `_spawn_worker_with_pty` docstring + sort imports**

Inspect the helper with fresh eyes; if any line exceeds 100 chars, wrap
appropriately. Consider hoisting the `import pty` + `import os as _os`
to module top if other code can reuse them; otherwise keep local-import
to keep Windows-only code paths from importing POSIX-only `pty` at
module load time. Document the local-import rationale inline if
hoisting is rejected.

The local import is the right call: hoisting `import pty` to module top
breaks Windows imports of `subprocess_utils.py` (the module is widely
imported across `auto_cmd`, `close_*_cmd`, etc.). Add a one-line
comment above the local imports:

```python
    # pty is POSIX-only stdlib; local-import keeps the Windows path
    # of subprocess_utils.py importable without conditional top-level
    # ImportError handling.
    import pty
    import os as _os
```

- [x] **Step 10: Run `make verify`**

Expected: clean.

- [x] **Step 11: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 A1 PTY helper docstring + import comment"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` commit + `chore: mark task` commit + state advances
to next task.

---

### Task 2: A2 — Windows hybrid Option B-W3 + Q2'=b worker-context runtime guard

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add new module-level
  helper `_spawn_worker(argv, env)` cross-platform dispatcher; wire into
  `_dispatch_tracks_concurrent` worker spawn site)
- Modify: `skills/sbtdd/scripts/close_phase_cmd.py:70`
  (`_run_verification` worker-mode bypass via
  `SBTDD_AUTO_PARALLEL_WORKER` env check)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py:336`
  (Q2'=b promotion: insert worker-context runtime guard BEFORE existing
  membership gate in `invoke_skill`)
- Modify: `tests/test_close_phase_cmd.py` (extend with
  `TestRunVerificationWorkerBypass` class for escenarios A2-2/A2-3/A2-4)
- Modify: `tests/test_superpowers_dispatch.py` (extend with
  `TestInvokeSkillWorkerGuard` class for escenarios A2-5/A2-6)
- Modify: `tests/test_auto_cmd.py` (extend with `TestSpawnWorkerDispatcher`
  for escenario A2-1)

Covers escenarios A2-1 through A2-6 from spec sec.4.2.

#### Red Phase

- [x] **Step 1: Write failing tests for `auto_cmd._spawn_worker` dispatcher**

Append to `tests/test_auto_cmd.py`:

```python
class TestSpawnWorkerDispatcher:
    """v1.0.7 A2 cross-platform worker spawn dispatcher per spec sec.4.2."""

    def test_windows_worker_uses_subprocess_pipe_with_env_marker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-1 (Windows path): subprocess.PIPE + SBTDD_AUTO_PARALLEL_WORKER=1."""
        monkeypatch.setattr(sys, "platform", "win32")
        captured: dict[str, object] = {}

        class FakeProc:
            def wait(self, timeout: int | None = None) -> int:
                return 0

        def fake_popen(
            argv: list[str],
            **kwargs: object,
        ) -> FakeProc:
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return FakeProc()

        monkeypatch.setattr("auto_cmd.subprocess.Popen", fake_popen)
        proc = auto_cmd._spawn_worker(
            ["python", "-c", "pass"], env={"PATH": "/usr/bin"}
        )
        kwargs = captured["kwargs"]
        assert kwargs["stdin"] is subprocess.PIPE
        assert kwargs["stdout"] is subprocess.PIPE
        assert kwargs["stderr"] is subprocess.PIPE
        assert kwargs["env"]["SBTDD_AUTO_PARALLEL_WORKER"] == "1"
        assert kwargs["env"]["PATH"] == "/usr/bin"

    def test_posix_worker_routes_to_pty_helper(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-1 (POSIX path): routes to subprocess_utils._spawn_worker_with_pty."""
        if sys.platform == "win32":
            # Force POSIX behavior by monkeypatching sys.platform.
            monkeypatch.setattr(sys, "platform", "linux")
        captured: dict[str, object] = {}

        class FakeProc:
            pass

        def fake_pty_spawn(
            argv: list[str], env: dict[str, str]
        ) -> FakeProc:
            captured["argv"] = argv
            captured["env"] = env
            return FakeProc()

        monkeypatch.setattr(
            "subprocess_utils._spawn_worker_with_pty", fake_pty_spawn
        )
        auto_cmd._spawn_worker(
            ["python", "-c", "pass"], env={"PATH": "/usr/bin"}
        )
        assert captured["argv"] == ["python", "-c", "pass"]
        assert captured["env"]["SBTDD_AUTO_PARALLEL_WORKER"] == "1"
        assert captured["env"]["PATH"] == "/usr/bin"
```

Add `import subprocess` and `import sys` at top of file if missing.

- [x] **Step 2: Write failing tests for `close_phase_cmd._run_verification` worker bypass (sec.0.1 chain + INV-16 sidecar)**

Append to `tests/test_close_phase_cmd.py`:

```python
class TestRunVerificationWorkerBypass:
    """v1.0.7 A2 worker-mode bypass per spec sec.4.2 + iter-2 C4 carry-forward.

    Replaces `make verify` shell-out with explicit sec.0.1 chain:
    pytest, ruff check, ruff format --check, mypy. Persists per-worker
    captured output to <root>/.claude/auto-run-workers/<pid>-verify.json
    for INV-16 evidence-before-assertions continuity.
    """

    def test_worker_mode_runs_sec_0_1_chain(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-2 (C4 carry-forward): worker runs sec.0.1 4-tool chain."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        skill_called = []

        def fake_skill(*, cwd: str) -> None:
            skill_called.append(cwd)

        monkeypatch.setattr(
            "superpowers_dispatch.verification_before_completion", fake_skill
        )
        captured_cmds: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        def fake_run(cmd: list[str], **kwargs: object) -> FakeResult:
            captured_cmds.append(cmd)
            return FakeResult()

        monkeypatch.setattr("close_phase_cmd.subprocess.run", fake_run)
        close_phase_cmd._run_verification(tmp_path)
        assert skill_called == []  # bypassed
        assert captured_cmds == [
            ["pytest"],
            ["ruff", "check", "."],
            ["ruff", "format", "--check", "."],
            ["mypy", "."],
        ]

    def test_worker_mode_first_tool_failure_aborts_chain_and_persists_evidence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-3 (C4 carry-forward): pytest failure aborts chain + evidence persisted."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        captured_cmds: list[list[str]] = []

        class FailResult:
            returncode = 1
            stdout = "FAILED"
            stderr = "test foo failed"

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        def fake_run(cmd: list[str], **kwargs: object) -> object:
            captured_cmds.append(cmd)
            return FailResult() if cmd == ["pytest"] else PassResult()

        monkeypatch.setattr("close_phase_cmd.subprocess.run", fake_run)
        with pytest.raises(ValidationError, match="A2 worker-mode verify failed at 'pytest'"):
            close_phase_cmd._run_verification(tmp_path)
        # Only pytest ran; ruff/mypy NOT invoked (early-abort).
        assert captured_cmds == [["pytest"]]
        # Evidence sidecar persisted with the partial chain.
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 1
        payload = json.loads(sidecars[0].read_text(encoding="utf-8"))
        assert payload["verify_chain"] == [
            {"cmd": ["pytest"], "rc": 1, "stdout": "FAILED", "stderr": "test foo failed"}
        ]

    def test_worker_mode_full_chain_success_persists_evidence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-7 (C4 + iter-3 C1 carry-forward): full success + collision-resistant filename."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        monkeypatch.setattr(
            "close_phase_cmd.subprocess.run",
            lambda cmd, **kw: PassResult(),
        )
        close_phase_cmd._run_verification(tmp_path)
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 1
        # v1.0.7 iter-3 C1: filename pattern <pid>-<monotonic_ns>-<uuid8>-verify.json
        stem = sidecars[0].stem
        # Expected: <pid>-<monotonic_ns>-<uuid8hex>-verify
        parts = stem.split("-")
        assert parts[-1] == "verify"
        assert len(parts) == 4  # pid, monotonic_ns, uuid8, "verify"
        assert parts[0] == str(os.getpid())
        assert parts[1].isdigit() and int(parts[1]) > 0  # monotonic_ns
        assert len(parts[2]) == 8 and all(c in "0123456789abcdef" for c in parts[2])
        payload = json.loads(sidecars[0].read_text(encoding="utf-8"))
        assert len(payload["verify_chain"]) == 4
        assert all(entry["rc"] == 0 for entry in payload["verify_chain"])

    def test_pid_recycle_simulation_does_not_collide(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-9 (iter-3 C1 carry-forward): same-pid re-spawn produces 2 distinct sidecars."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        monkeypatch.setattr(
            "close_phase_cmd.subprocess.run",
            lambda cmd, **kw: PassResult(),
        )
        # Call twice from the same process (simulates PID recycle).
        close_phase_cmd._run_verification(tmp_path)
        close_phase_cmd._run_verification(tmp_path)
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 2  # NO collision
        # Both sidecars share pid prefix but differ in monotonic_ns or uuid8.
        stems = [s.stem for s in sidecars]
        assert all(stem.startswith(f"{os.getpid()}-") for stem in stems)
        assert len(set(stems)) == 2

    def test_orchestrator_mode_preserves_skill_dispatch(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-4: no env var -> existing skill path."""
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill_called = []

        def fake_skill(*, cwd: str) -> None:
            skill_called.append(cwd)

        monkeypatch.setattr(
            "superpowers_dispatch.verification_before_completion", fake_skill
        )
        # subprocess.run should NOT be called in orchestrator mode.
        def boom(cmd: list[str], **kw: object) -> None:
            raise AssertionError("subprocess.run must not be called in orchestrator mode")

        monkeypatch.setattr("close_phase_cmd.subprocess.run", boom)
        close_phase_cmd._run_verification(tmp_path)
        assert skill_called == [str(tmp_path)]
```

Add `from errors import ValidationError`, `import close_phase_cmd`,
`import json`, `from pathlib import Path` at top of file if missing.

- [x] **Step 3: Write failing tests for Q2'=b worker-context runtime guard**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestInvokeSkillWorkerGuard:
    """v1.0.7 A2 Q2'=b worker-context runtime guard per spec sec.4.2 A2-5/A2-6."""

    def test_worker_env_with_incompatible_skill_raises_worker_bug_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-5: worker env + incompatible skill -> PreconditionError naming bug."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        # Pick any skill that's in the membership set.
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        with pytest.raises(PreconditionError, match="Worker subprocess attempted"):
            superpowers_dispatch.invoke_skill(
                skill, allow_interactive_skill=True
            )

    def test_orchestrator_unaffected_by_worker_guard(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-6: no env var -> falls through to existing v1.0.4+v1.0.6 gates."""
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        # With allow_interactive_skill=True + no headless context, dispatch
        # would proceed; we monkeypatch run_with_timeout to short-circuit.
        captured: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            captured.append(cmd)
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        # Force non-headless context for this test.
        monkeypatch.setattr(
            "subprocess_utils.is_headless_context", lambda: False
        )
        result = superpowers_dispatch.invoke_skill(
            skill, allow_interactive_skill=True
        )
        assert result.returncode == 0
        assert captured  # subprocess WAS dispatched (no worker guard fired)

    def test_orchestrator_with_tty_dispatches_normally_pin_guard_ordering(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-8 (W1 carry-forward): pin guard ordering against future regressions.

        Verifies the v1.0.7 A2 worker check fires AFTER membership +
        BEFORE headless gate AND requires BOTH env var presence AND
        skill membership. Checking env var alone would trip on operator
        scripts that set SBTDD_AUTO_PARALLEL_WORKER=1 unrelated to
        --parallel context. Future refactors that reorder the guards
        must keep this test green.
        """
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill = next(iter(superpowers_dispatch._SUBPROCESS_INCOMPATIBLE_SKILLS))
        captured: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        monkeypatch.setattr(
            "subprocess_utils.run_with_timeout",
            lambda cmd, **kw: (captured.append(cmd) or FakeResult()),
        )
        monkeypatch.setattr(
            "subprocess_utils.is_headless_context", lambda: False
        )
        # Orchestrator dispatch SHOULD proceed: not headless + override allowed.
        result = superpowers_dispatch.invoke_skill(
            skill, allow_interactive_skill=True
        )
        assert result.returncode == 0
        assert len(captured) == 1
        # Now flip the env var to verify the worker guard DOES fire.
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        with pytest.raises(PreconditionError, match="Worker subprocess attempted"):
            superpowers_dispatch.invoke_skill(
                skill, allow_interactive_skill=True
            )
```

Add imports if missing at top of `tests/test_superpowers_dispatch.py`:

```python
from errors import PreconditionError
import superpowers_dispatch
```

- [x] **Step 4: Run tests to verify failure**

Run: `pytest tests/test_auto_cmd.py::TestSpawnWorkerDispatcher tests/test_close_phase_cmd.py::TestRunVerificationWorkerBypass tests/test_superpowers_dispatch.py::TestInvokeSkillWorkerGuard -v`

Expected: all FAIL with `AttributeError`/missing-symbol errors.

- [x] **Step 5: Run `make verify`**

Expected: only the new tests fail; ruff + mypy clean.

- [x] **Step 6: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 A2 Windows hybrid + worker runtime guard tests"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [x] **Step 7: Implement `auto_cmd._spawn_worker` cross-platform dispatcher**

Add to `skills/sbtdd/scripts/auto_cmd.py` near the `_dispatch_tracks_concurrent`
helper (search for `def _dispatch_tracks_concurrent`):

```python
def _spawn_worker(
    argv: list[str],
    env: dict[str, str],
) -> "subprocess.Popen[bytes]":
    """v1.0.7 A2 cross-platform worker spawn dispatcher.

    POSIX -> real PTY allocation via
    :func:`subprocess_utils._spawn_worker_with_pty` (Item A1). Workers
    inherit slave fd as stdin/stdout/stderr; close-phase /verification-
    before-completion subprocess inherits TTY -> no chicken-and-egg hang.

    Windows -> ``subprocess.PIPE`` (Option B-W3 hybrid; Windows lacks
    POSIX-style PTY). Workers carry ``SBTDD_AUTO_PARALLEL_WORKER=1`` env
    marker so :func:`close_phase_cmd._run_verification` shells out to
    ``make verify`` directly instead of dispatching the interactive
    skill (sidesteps TTY requirement).

    Args:
        argv: Subprocess argv. ``shell=False`` invariant preserved.
        env: Environment dict; this helper injects
            ``SBTDD_AUTO_PARALLEL_WORKER=1`` before spawn.

    Returns:
        ``subprocess.Popen`` instance ready for orchestrator post-batch
        merge (per v1.0.5 I-1 sidecar + I-2 scratch patterns).
    """
    env_with_marker = {**env, "SBTDD_AUTO_PARALLEL_WORKER": "1"}
    if sys.platform == "win32":
        return subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_with_marker,
        )
    return subprocess_utils._spawn_worker_with_pty(argv, env_with_marker)
```

Then locate the `_dispatch_tracks_concurrent` worker spawn site (around
line 1801+; search for `subprocess.Popen(` inside that function). Replace
the direct `subprocess.Popen(...)` call with `_spawn_worker(argv, env)`,
preserving the existing argv-build path (`_build_worker_argv` per v1.0.5
I-3) and any os.environ.copy() prep for env. The orchestrator's existing
post-batch sidecar/scratch merge logic is unchanged.

If the existing call site uses keyword args incompatible with the new
helper (e.g., `cwd=` or `creationflags=`), keep those args inline by
passing them through a dispatcher kwarg surface — extend `_spawn_worker`
to accept `**popen_kwargs` and forward them. For the v1.0.7 minimal
landing, only `env` and `argv` are required; if other kwargs surface
during impl, extend the helper signature in the same Green commit and
update the dispatcher tests accordingly.

- [x] **Step 8: Implement `close_phase_cmd._run_verification` worker-mode bypass with sec.0.1 chain + INV-16 sidecar (C4 carry-forward)**

Edit `skills/sbtdd/scripts/close_phase_cmd.py:70` — replace the body of
`_run_verification` with:

```python
def _run_verification(root: Path) -> None:
    """Invoke /verification-before-completion with ``root`` as the working dir.

    MAGI Loop 2 iter 1 Finding 4: the skill wrapper spawns a subprocess
    that shells out to the stack's test runner (pytest / cargo / ctest).
    Without a ``cwd=`` those tools attempt to discover tests relative to
    wherever ``/sbtdd close-phase`` was invoked from -- typically a
    subdirectory of the project root, which breaks test discovery and
    produces a spurious "no tests collected" result. Passing ``cwd=root``
    makes the working directory match the project root regardless of
    which subdirectory the user invoked the command from.

    v1.0.7 A2 Option B-W3 hybrid: when ``SBTDD_AUTO_PARALLEL_WORKER=1``
    is set in the environment (parent-injected by
    :func:`auto_cmd._spawn_worker` for ``--parallel`` workers), bypass
    the interactive ``/verification-before-completion`` skill subprocess
    and run the sec.0.1 4-tool chain directly: pytest, ruff check,
    ruff format --check, mypy. Rationale: workers spawned via
    ``subprocess.PIPE`` on Windows have no TTY -> the skill subprocess
    hangs waiting for an interactive prompt that never arrives
    (chicken-and-egg, empirically confirmed in v1.0.6 dogfood, spec
    sec.2.1). v1.0.7 iter-2 carry-forward C4: chain is explicit (no
    `make` dependency on Windows) + per-worker stdout/stderr captured
    to ``<root>/.claude/auto-run-workers/<pid>-verify.json`` for INV-16
    evidence-before-assertions continuity (parent post-batch merge can
    introspect for actual sec.0.1 results, not just success/fail).

    Args:
        root: Project root directory (``--project-root``).

    Raises:
        ValidationError: Skill wrapper raised (timeout / non-zero exit)
            in orchestrator mode, OR any sec.0.1 tool returned non-zero
            in worker mode (early-abort semantics: subsequent tools NOT
            run; partial captured chain still persisted to sidecar).
        QuotaExhaustedError: Anthropic API cap hit during verification
            (orchestrator mode only; shell command path is offline).
    """
    if os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1":
        commands = [
            ["pytest"],
            ["ruff", "check", "."],
            ["ruff", "format", "--check", "."],
            ["mypy", "."],
        ]
        captured: list[dict[str, object]] = []
        for cmd in commands:
            result = subprocess.run(
                cmd, cwd=str(root), check=False,
                capture_output=True, text=True,
            )
            captured.append({
                "cmd": cmd,
                "rc": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            })
            if result.returncode != 0:
                # Persist partial chain BEFORE raising for INV-16 evidence.
                _persist_worker_verify_evidence(root, captured)
                raise ValidationError(
                    f"v1.0.7 A2 worker-mode verify failed at "
                    f"{cmd[0]!r}: rc={result.returncode}"
                )
        _persist_worker_verify_evidence(root, captured)
        return
    superpowers_dispatch.verification_before_completion(cwd=str(root))


def _persist_worker_verify_evidence(
    root: Path,
    captured: list[dict[str, object]],
) -> None:
    """v1.0.7 A2 INV-16 continuity: write per-worker verify capture.

    Writes to ``<root>/.claude/auto-run-workers/<pid>-<monotonic_ns>-<uuid8>-verify.json``
    so parent post-batch merge has evidence of what each worker actually
    ran + observed. Uses ``state_file.atomic_write_json`` (which gains
    Windows PermissionError retry per v1.0.7 B3 = T6).

    v1.0.7 iter-3 carry-forward C1 (Cas iter-2 CRITICAL): filename
    has 3-component disambiguator preventing PID-recycle / re-spawn
    collision (pid for human cross-reference + monotonic_ns
    sub-microsecond resolution + uuid8 final tiebreaker). Parent-side
    LOUD-FAIL contract enforced in `_dispatch_tracks_concurrent`
    post-batch merge: missing sidecar raises ConcurrentDispatchError.
    """
    import time as _time
    import uuid as _uuid

    sidecar_dir = root / ".claude" / "auto-run-workers"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    suffix = f"{os.getpid()}-{_time.monotonic_ns()}-{_uuid.uuid4().hex[:8]}"
    sidecar = sidecar_dir / f"{suffix}-verify.json"
    state_file.atomic_write_json(sidecar, {"verify_chain": captured})
```

**Parent-side LOUD-FAIL contract** (v1.0.7 iter-3 carry-forward C1):
in `auto_cmd._dispatch_tracks_concurrent` post-batch merge, after
collecting worker exit codes, glob for sidecars matching each
spawned worker's pid:

```python
# auto_cmd._dispatch_tracks_concurrent post-batch merge addendum
def _verify_worker_sidecars_present(
    project_root: Path,
    worker_pids: list[int],
) -> None:
    """v1.0.7 iter-3 carry-forward C1: LOUD-FAIL on missing sidecar.

    Each spawned worker MUST produce >= 1 sidecar matching the
    glob `<pid>-*-verify.json`. Missing sidecar = code-path bug
    (worker spawned + ran close-phase but failed to persist evidence).
    LOUD-FAIL via ConcurrentDispatchError surfaces it during
    test/dogfood instead of silent INV-16 evidence loss.
    """
    sidecar_dir = project_root / ".claude" / "auto-run-workers"
    if not sidecar_dir.exists():
        # No workers wrote sidecars at all; possible if all workers
        # failed before reaching close-phase. Log + return; missing
        # close-phase chain is a separate failure surface caught by
        # worker exit code aggregation.
        return
    observed = list(sidecar_dir.glob("*-verify.json"))
    observed_pids = {int(p.name.split("-")[0]) for p in observed}
    missing = [pid for pid in worker_pids if pid not in observed_pids]
    if missing:
        raise ConcurrentDispatchError(
            f"v1.0.7 iter-3 C1: workers {missing} completed but produced "
            f"no INV-16 sidecar. Observed sidecars: {[p.name for p in observed]}. "
            f"Expected workers: {worker_pids}. Bug in "
            f"_persist_worker_verify_evidence OR transient OS error "
            f"swallowed mid-write; investigate before next dispatch."
        )
```

Wire `_verify_worker_sidecars_present(project_root, [proc.pid for
proc in completed_workers])` into `_dispatch_tracks_concurrent` just
before the existing per-worker sidecar/scratch merge.

Add to imports at the top of `close_phase_cmd.py` if missing:

```python
import os
import subprocess

from errors import ValidationError
import state_file
```

- [x] **Step 9: Implement Q2'=b runtime guard in `superpowers_dispatch.invoke_skill`**

Edit `skills/sbtdd/scripts/superpowers_dispatch.py` around line 336.
Locate the existing membership gate:

```python
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
        raise PreconditionError(_build_recovery_message(skill))
```

Insert BEFORE that line:

```python
    # v1.0.7 A2 Q2'=b promotion: defense-in-depth worker-context runtime
    # guard. Workers under `auto --parallel` (parent-injected env var
    # SBTDD_AUTO_PARALLEL_WORKER=1) MUST NOT dispatch interactive skills
    # via subprocess. The membership gate below + v1.0.6 J-3 headless
    # detection catch the orchestrator path; this guard catches the
    # worker path even when a wrapper sets allow_interactive_skill=True.
    # Closes Cas v1.0.6 iter-2 WARNING: F-A2 worker headless audit was
    # grep-snapshot, not runtime guard. Fires loud-fast so any drift
    # (transitive imports adding a skill dispatch to the worker code
    # path) surfaces during dev/CI rather than producing a silent
    # subprocess hang in production.
    if (
        skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
        and os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1"
    ):
        raise PreconditionError(
            f"Worker subprocess attempted to dispatch interactive "
            f"skill {skill!r}; this should never happen in the auto "
            f"--parallel worker code path. Bug. Either: (a) the worker "
            f"code path was extended to call the skill -- refactor to "
            f"use shell command directly per v1.0.7 A2 "
            f"_run_verification pattern, OR (b) the parent set "
            f"SBTDD_AUTO_PARALLEL_WORKER=1 incorrectly."
        )
```

Add `import os` to the imports at the top of the file if not already present.

- [x] **Step 10: Run tests to verify they pass**

Run: `pytest tests/test_auto_cmd.py::TestSpawnWorkerDispatcher tests/test_close_phase_cmd.py::TestRunVerificationWorkerBypass tests/test_superpowers_dispatch.py::TestInvokeSkillWorkerGuard -v`

Expected: all PASS (POSIX/Windows split per `sys.platform` monkeypatch).

- [x] **Step 11: Run `make verify`**

Expected: clean.

- [x] **Step 12: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.7 A2 Windows hybrid worker spawn + Q2'=b runtime guard"`

Expected: `feat:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [x] **Step 13: Tighten docstrings + audit for remaining direct Popen calls**

Search for any other `subprocess.Popen` calls in `auto_cmd.py` that
spawn workers; if any bypass `_spawn_worker`, they need to route through
the dispatcher to preserve the env-var contract. Likely target:
`_dispatch_tracks_concurrent` may have only one spawn site (the one
just refactored). Confirm via:

```bash
grep -n "subprocess.Popen" skills/sbtdd/scripts/auto_cmd.py
```

Document the worker-spawn contract in `_spawn_worker` docstring: "All
worker subprocess spawns under `auto --parallel` MUST go through this
helper to preserve the `SBTDD_AUTO_PARALLEL_WORKER=1` env contract that
`close_phase_cmd._run_verification` and `superpowers_dispatch.invoke_skill`
depend on."

- [x] **Step 14: Run `make verify`**

Expected: clean.

- [x] **Step 15: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 A2 dispatcher + worker contract documentation"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next task.

---

### Task 3: A3 — F-A2 dogfood empirical e2e (REAL chicken-and-egg fixture per C3 carry-forward)

**Files:**
- Create: `tests/test_auto_parallel_e2e.py` (new integration test
  exercising full `auto --parallel` flow on Windows with synthetic
  2-track + 4 disjoint tasks where each worker invokes REAL
  `close-phase` chain → sec.0.1 dispatch)
- Create: `tests/fixtures/parallel-e2e/plan-fixture.md` (synthetic
  4-task plan; each task's TDD cycle invokes real `close-phase` from
  worker subprocess)
- Create: `tests/fixtures/parallel-e2e/spec-fixture.md` (synthetic
  spec)
- Create: `tests/fixtures/parallel-e2e/pyproject.toml` (minimal
  fixture project so worker `pytest` / `ruff` / `mypy` chain can
  discover something to run)
- Create: `tests/fixtures/parallel-e2e/src/sample.py` + tests (minimal
  source + smoke tests that all 4 sec.0.1 tools succeed against)

Covers escenarios A3-1 (C3 real chicken-and-egg fixture) and A3-2 from
spec sec.4.3.

**CRITICAL design constraint (C3 carry-forward)**: trivial "append
text" worker tasks DO NOT trip the chicken-and-egg failure surface.
The fixture project MUST be a real Python project with pyproject.toml
+ source + tests so each worker's `close-phase` invocation actually
dispatches the sec.0.1 chain (`pytest`, `ruff check`, `ruff format
--check`, `mypy`). WITHOUT v1.0.7 Pillar A, this fixture would hang
on the first worker close-phase invocation. WITH Pillar A: workers
either get real PTY (POSIX) or use sec.0.1 chain bypass (Windows) and
complete.

#### Red Phase

- [x] **Step 1: Create synthetic 2-track + 4-task plan fixture WITH real Python project (C3 carry-forward)**

Create `tests/fixtures/parallel-e2e/spec-fixture.md`:

```markdown
# Synthetic e2e spec

> v1.0.7 A3 dogfood fixture — exercises real chicken-and-egg surface
> via worker close-phase chain dispatch.

## 1. Objective

Synthetic 4-task workload to exercise `auto --parallel` end-to-end with
each worker invoking real close-phase → sec.0.1 chain.

## 4. Escenarios

**Escenario fixture-1**: Given the parallel dispatcher + a real Python
fixture project; When 4 disjoint tasks dispatched across 2 tracks each
invoking real close-phase; Then all complete without hang AND
per-worker verify-evidence sidecars exist.
```

Create `tests/fixtures/parallel-e2e/pyproject.toml`:

```toml
[project]
name = "parallel-e2e-fixture"
version = "0.0.1"
requires-python = ">=3.9"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
```

Create `tests/fixtures/parallel-e2e/src/sample.py`:

```python
"""Sample source for fixture project (passes ruff + mypy --strict)."""


def add(x: int, y: int) -> int:
    """Return x + y."""
    return x + y
```

Create `tests/fixtures/parallel-e2e/tests/test_sample.py`:

```python
"""Sample tests for fixture project (passes pytest)."""
import sys

from src.sample import add


def test_add() -> None:
    """add returns sum."""
    assert add(1, 2) == 3


def test_isatty_observation() -> None:
    """v1.0.7 iter-3 A3-3 carry-forward: emit isatty marker for INV-16 evidence.

    On POSIX, the worker subprocess inherits a real TTY via PTY
    allocation (T1 production code); on Windows it inherits PIPE.
    This test prints the observation to stdout so the captured
    sec.0.1 chain output (T2 sidecar) records it for the integration
    test (T3) to assert.
    """
    print(f"isatty={sys.stdin.isatty()}")
    assert True  # always passes; the side-effect is the print
```

Create `tests/fixtures/parallel-e2e/Makefile` (optional fallback for
operators who want to run `make verify` locally; v1.0.7 worker bypass
does NOT depend on it):

```makefile
verify:
	pytest && ruff check . && ruff format --check . && mypy .
```

Create `tests/fixtures/parallel-e2e/plan-fixture.md` with 4 tasks
where each task's Step 2 invokes the REAL `close-phase` chain (which
in worker mode dispatches the sec.0.1 chain via T2 production code).
Each task touches a different scratch file for disjoint surfaces:

```markdown
# Synthetic 4-task parallel e2e plan

**Goal:** Exercise auto --parallel end-to-end with 4 disjoint tasks
each invoking real close-phase chain.

### Task 1: Touch alpha + invoke close-phase chain

**Files:**
- Modify: `scratch/alpha.txt`

- [ ] Step 1: Append "alpha-red" to scratch/alpha.txt
- [ ] Step 2: close-phase via run_sbtdd.py (dispatches sec.0.1 chain)
- [ ] Step 3: Done

### Task 2: Touch beta + invoke close-phase chain

**Files:**
- Modify: `scratch/beta.txt`

- [ ] Step 1: Append "beta-red" to scratch/beta.txt
- [ ] Step 2: close-phase via run_sbtdd.py
- [ ] Step 3: Done

### Task 3: Touch gamma + invoke close-phase chain

**Files:**
- Modify: `scratch/gamma.txt`

- [ ] Step 1: Append "gamma-red" to scratch/gamma.txt
- [ ] Step 2: close-phase via run_sbtdd.py
- [ ] Step 3: Done

### Task 4: Touch delta + invoke close-phase chain

**Files:**
- Modify: `scratch/delta.txt`

- [ ] Step 1: Append "delta-red" to scratch/delta.txt
- [ ] Step 2: close-phase via run_sbtdd.py
- [ ] Step 3: Done
```

- [ ] **Step 2: Write failing integration test in `tests/test_auto_parallel_e2e.py`**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 A3 F-A2 dogfood empirical end-to-end validation.

Exercises full auto --parallel flow on Windows (mandatory dev env) with
synthetic 2-track + 4 disjoint tasks. Asserts:
- All workers complete within 600s timeout (no ConcurrentDispatchError).
- .claude/auto-run.json contains start_time + per-worker records (I-1).
- Plan checkboxes all [x] post-merge (I-2).
- State file current_phase: "done" post-completion.
- No subprocess hangs > 600s timeout.

POSIX validation deferred to CI or v1.0.8 if no POSIX dev env.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
@pytest.mark.timeout(700)  # 600s parallel budget + 100s overhead
def test_auto_parallel_synthetic_2track_4task_e2e(
    tmp_path: Path,
) -> None:
    """A3-1: synthetic 2-track plan completes via auto --parallel."""
    if sys.platform != "win32":
        pytest.skip("v1.0.7 A3 mandatory on Windows; POSIX deferred to v1.0.8")
    fixture_root = Path(__file__).parent / "fixtures" / "parallel-e2e"
    project_root = tmp_path / "project"
    project_root.mkdir()
    # Stage fixture into a real git repo + minimal session state.
    shutil.copytree(fixture_root, project_root, dirs_exist_ok=True)
    subprocess.run(["git", "init"], cwd=project_root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_root,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=project_root,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=project_root, check=True)
    subprocess.run(
        ["git", "commit", "-m", "test: e2e fixture baseline"],
        cwd=project_root,
        check=True,
    )
    # Run auto --parallel against the fixture.
    run_sbtdd = (
        Path(__file__).parent.parent
        / "skills"
        / "sbtdd"
        / "scripts"
        / "run_sbtdd.py"
    )
    proc = subprocess.run(
        [sys.executable, str(run_sbtdd), "auto", "--parallel"],
        cwd=project_root,
        timeout=600,
        capture_output=True,
        text=True,
    )
    # Acceptance assertions per spec sec.4.3 A3-1.
    assert proc.returncode == 0, (
        f"auto --parallel failed: stdout={proc.stdout} stderr={proc.stderr}"
    )
    audit_path = project_root / ".claude" / "auto-run.json"
    assert audit_path.exists()
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert "start_time" in audit
    assert "per_worker" in audit  # v1.0.5 I-1 sidecar merge
    assert len(audit["per_worker"]) == 2  # 2 tracks
    plan_text = (project_root / "plan-fixture.md").read_text(encoding="utf-8")
    assert "- [ ]" not in plan_text  # all flipped (v1.0.5 I-2 merge)
    state = json.loads(
        (project_root / ".claude" / "session-state.json").read_text(encoding="utf-8")
    )
    assert state["current_phase"] == "done"
    # v1.0.7 iter-2 carry-forward C4: per-worker INV-16 evidence sidecars.
    workers_dir = project_root / ".claude" / "auto-run-workers"
    assert workers_dir.exists(), "T2 INV-16 sidecar dir must exist post-cycle"
    sidecars = list(workers_dir.glob("*-verify.json"))
    assert len(sidecars) >= 1, "at least one worker must have written verify evidence"
    # v1.0.7 iter-3 carry-forward C1: collision-resistant filename pattern.
    for sidecar in sidecars:
        stem = sidecar.stem
        parts = stem.split("-")
        assert parts[-1] == "verify"
        assert len(parts) == 4, f"sidecar {sidecar.name} not in <pid>-<monotonic_ns>-<uuid8>-verify pattern"
        assert parts[0].isdigit()  # pid
        assert parts[1].isdigit() and int(parts[1]) > 0  # monotonic_ns
        assert len(parts[2]) == 8 and all(c in "0123456789abcdef" for c in parts[2])  # uuid8
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        assert "verify_chain" in payload
        assert all("rc" in entry and "stdout" in entry for entry in payload["verify_chain"])
    # v1.0.7 iter-3 carry-forward W (cas A3 fixture realism): on POSIX,
    # at least one sidecar must contain TTY-observation evidence (PTY
    # path executed, not Windows hybrid bypass). On Windows this check
    # is skipped (Windows uses subprocess.PIPE intentionally).
    if sys.platform != "win32":
        tty_observed = False
        for sidecar in sidecars:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
            for entry in payload["verify_chain"]:
                # pytest under TTY emits "PASSED" with color codes OR
                # known TTY-only marker; fixture conftest.py asserts
                # sys.stdin.isatty() in a test that prints the result
                # to stdout, captured here.
                if "isatty=True" in entry["stdout"]:
                    tty_observed = True
                    break
            if tty_observed:
                break
        assert tty_observed, (
            "POSIX A3-3 carry-forward: at least one worker must have observed "
            "a TTY via _spawn_worker_with_pty. Without this assertion, the "
            "test could pass even if the PTY path silently fell back to "
            "subprocess.PIPE (regression invisible). Add an isatty=True echo "
            "to the fixture's conftest.py or a smoke test."
        )
```

- [ ] **Step 3: Run test to verify failure**

Run: `pytest tests/test_auto_parallel_e2e.py -v`
Expected: FAIL on Windows with subprocess hang OR `auto --parallel`
returncode != 0 (depends on whether T1+T2 already landed; if yes, test
should PASS — in which case A3 is empirically validated. If not yet
landed, test FAILS via timeout / non-zero rc).

NOTE: this is the empirical-validation test; if it PASSES on Windows
without intervention, that's the strongest signal that A1+A2 closed
the chicken-and-egg gap end-to-end. If it FAILS, surface the failure
mode (hang vs error) and route fix to A1/A2 mini-cycle BEFORE proceeding.

- [ ] **Step 4: Run `make verify`**

Expected: only the new integration test fails (or passes on Windows if
A1+A2 are complete); ruff + mypy clean.

- [ ] **Step 5: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 A3 auto --parallel e2e integration test fixture + harness"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [ ] **Step 6: Empirical validation — manually run the integration test on Windows**

This task's "implementation" is the empirical run: the test itself
exercises A1+A2 production code; no new production code is added in
Green. The Green deliverable is empirical evidence (test PASSES).

Run on Windows: `pytest tests/test_auto_parallel_e2e.py -v --tb=short`

Expected: PASS within ~5-10 minutes (4 noop tasks; each task's
`make verify` runs the full test suite ~3 min, but with disjoint
parallelism only ~2 tracks of ~3 min each = ~3-6 min total worst case).

If FAIL: diagnose:
- Hang -> A2 Windows hybrid bypass not firing OR
  `SBTDD_AUTO_PARALLEL_WORKER` env var not propagated -> file fix as
  A1/A2 sub-mini-cycle, then re-run.
- Non-zero rc -> read worker stderr for actual error; route fix similarly.

- [ ] **Step 7: Run `make verify`**

Expected: full test suite green including the new e2e integration test.

- [ ] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.7 A3 empirical validation -- auto --parallel e2e passes on Windows"`

Expected: `feat:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [ ] **Step 9: Mark integration test idempotent + cleanup-safe**

Audit `tests/test_auto_parallel_e2e.py` for any state pollution
(temp git repos under `tmp_path` are auto-cleaned by pytest fixture).
Confirm the test does not leave stray processes (no `subprocess.Popen`
without `wait()`); the helper `subprocess.run(...)` with timeout
inherently waits.

If the test produces > 10s of total wall time variance across runs,
add a comment noting expected runtime range so future engineers don't
mistake variance for flakiness.

- [ ] **Step 10: Run `make verify`**

Expected: clean.

- [ ] **Step 11: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 A3 e2e test cleanup + runtime variance comment"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next task.

---

## Pillar B LOCKED — v1.0.6 dogfood findings (Q3'=b ordering: B5 → B4 → B3)

### Task 4: B5 — Drift detector line-anchored `[ ]` regex

**Files:**
- Modify: `skills/sbtdd/scripts/drift.py:242` (replace substring check
  in `_plan_all_tasks_complete` with line-anchored multiline regex
  `^[ \t]*- \[ \]`)
- Modify: `tests/test_drift.py` (extend with `TestPlanAllTasksCompleteLineAnchored`
  class for escenarios B5-1, B5-2, B5-3)

Covers escenarios B5-1, B5-2, B5-3 from spec sec.4.4.

#### Red Phase

- [ ] **Step 1: Write failing tests in `tests/test_drift.py`**

Append:

```python
class TestPlanAllTasksCompleteLineAnchored:
    """v1.0.7 B5 drift detector line-anchored regex per spec sec.4.4."""

    def test_codeblock_open_checkbox_does_not_false_positive(self) -> None:
        """B5-1: `- [ ]` inside Python string literal (code block) ignored."""
        plan = (
            "### Task 1: A\n"
            "- [x] Step 1\n"
            "    Example fixture content:\n"
            "    ```python\n"
            '    text = "- [ ] Step 1\\n"\n'
            "    ```\n"
            "### Task 2: B\n"
            "- [x] Step 1\n"
        )
        assert drift._plan_all_tasks_complete(plan) == "[x]"

    def test_real_open_checkbox_at_line_start_detected(self) -> None:
        """B5-2: legit `- [ ]` at line start still flags incomplete."""
        plan = (
            "### Task 1: A\n"
            "- [ ] Step 1\n"
            "### Task 2: B\n"
            "- [x] Step 1\n"
        )
        assert drift._plan_all_tasks_complete(plan) == "[ ]"

    def test_indented_open_checkbox_detected(self) -> None:
        """B5 partial: indented `  - [ ]` still flags incomplete."""
        plan = (
            "### Task 1: A\n"
            "  - [ ] indented step\n"
            "### Task 2: B\n"
            "- [x] Step 1\n"
        )
        assert drift._plan_all_tasks_complete(plan) == "[ ]"
```

Add `import drift` if missing.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_drift.py::TestPlanAllTasksCompleteLineAnchored -v`
Expected: `test_codeblock_open_checkbox_does_not_false_positive` FAILS
(returns `"[ ]"` due to current unanchored substring check). The other
two PASS already (existing implementation handles them correctly).

- [ ] **Step 3: Run `make verify`**

Expected: only the one new test fails; ruff + mypy clean.

- [ ] **Step 4: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 B5 drift detector code-block fixture regression test"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [ ] **Step 5: Replace substring check with line-anchored regex in `drift._plan_all_tasks_complete`**

Edit `skills/sbtdd/scripts/drift.py:242` — locate the `if "- [ ]" in plan_text[start:end]:` line. Replace with line-anchored multiline regex:

```python
def _plan_all_tasks_complete(plan_text: str) -> str:
    """Return ``"[x]"`` iff every ``### Task <id>:`` section is fully flipped.

    Walks every task header in the plan and checks that the text between
    it and the next task header contains NO line-anchored ``- [ ]``
    markers. Used by :func:`detect_drift` when the state file has
    ``current_task_id=None`` (terminal ``done`` state) to distinguish
    between:

    * ``state=done, all chores landed`` -> every section ``[x]`` -> ``"[x]"``
      -> no drift (terminal).
    * ``state=done, some task advance skipped`` -> at least one section
      still has ``- [ ]`` -> ``"[ ]"`` -> drift reported (the
      ``state-done-plan-open`` branch of ``_evaluate_drift``).

    When the plan has no ``### Task`` headers at all (malformed or
    empty), return ``"[x]"`` to avoid false-positive drift; the check is
    conservative in the other direction (phase=done with open-task
    evidence is real drift, but phase=done with a planless repo is not a
    useful signal).

    v1.0.7 B5 fix: line-anchored multiline regex ``^[ \\t]*- \\[ \\]``
    replaces the previous unanchored substring check ``"- [ ]" in section``.
    The substring check produced false-positives on plans containing
    Python test fixture string literals like ``"- [ ] Step 1\\n"`` inside
    code blocks (v1.0.6 dogfood empirical finding). The regex requires
    the ``- [ ]`` marker to start at line beginning (with optional
    leading whitespace for indented bullets), excluding code-block
    fixtures whose ``- [ ]`` substrings sit inside string literal
    contexts.
    """
    headers = list(_ANY_TASK_HEADER.finditer(plan_text))
    if not headers:
        return "[x]"
    for i, match in enumerate(headers):
        start = match.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(plan_text)
        if _OPEN_CHECKBOX_LINE_RE.search(plan_text[start:end]):
            return "[ ]"
    return "[x]"
```

Add the module-level regex near the existing `_ANY_TASK_HEADER` definition:

```python
#: v1.0.7 B5: line-anchored open-checkbox regex. Matches ``- [ ]`` at line
#: start (with optional leading whitespace for indented bullets) so plan
#: text containing ``- [ ]`` inside code-block string literals doesn't
#: false-positive the drift detector.
_OPEN_CHECKBOX_LINE_RE = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)
```

Confirm `re` is already imported at the top of `drift.py`.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_drift.py -v`
Expected: full module green including the 3 new B5 tests + the
previously-failing v1.0.6 `test_v104_plan_has_no_h3_task_headers...`
regression (escenario B5-3 hand-validated).

- [ ] **Step 7: Run `make verify`**

Expected: clean.

- [ ] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant fix --message "v1.0.7 B5 drift detector line-anchored regex eliminates code-block false-positive"`

Expected: `fix:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [ ] **Step 9: Audit other drift.py callsites for unanchored substring patterns**

Grep `drift.py` for other `"- [ ]"` substring occurrences:

```bash
grep -n '"- \[' skills/sbtdd/scripts/drift.py
```

If `_all_task_steps_complete` (line 205) or any other helper uses the
same unanchored check on plan content, apply the same line-anchored
fix consistently. Otherwise leave them alone (e.g.,
`_all_task_steps_complete` operates on a per-task section that is
unlikely to contain code-block fixtures referencing `- [ ]`; the v1.0.7
B5 fix targets `_plan_all_tasks_complete` specifically).

- [ ] **Step 10: Run `make verify`**

Expected: clean.

- [ ] **Step 11: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 B5 audit + docstring rationale"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next task.

---

### Task 5: B4 — `spec_review_dispatch` file-reference pattern

**Files:**
- Modify: `skills/sbtdd/scripts/spec_review_dispatch.py:413-485` (write
  prompt to `<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md`
  + pass `@<filepath>` reference in argv + try/finally cleanup)
- Modify: `tests/test_spec_review_dispatch.py` (extend with
  `TestSpecReviewerFileReference` class for escenarios B4-1 through B4-4)

Covers escenarios B4-1, B4-2, B4-3, B4-4 from spec sec.4.5.

#### Red Phase

- [ ] **Step 1: Write failing tests in `tests/test_spec_review_dispatch.py`**

Append:

```python
class TestSpecReviewerFileReference:
    """v1.0.7 B4 spec_review_dispatch file-reference per spec sec.4.5."""

    def test_prompt_written_to_project_relative_tempfile(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B4-1: prompt written to .claude/spec-reviews/.tmp/prompt-<uuid16>.md."""
        repo_root = tmp_path / "repo"
        (repo_root / ".claude" / "spec-reviews").mkdir(parents=True)
        plan_path = repo_root / "planning" / "claude-plan-tdd.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text("### Task 1: dummy\n- [x] step\n", encoding="utf-8")
        captured: dict[str, object] = {}

        class FakeResult:
            returncode = 0
            stdout = '{"approved": true, "issues": []}'
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            captured["argv"] = list(cmd)
            # Verify the prompt file existed at dispatch time.
            for tok in cmd:
                if tok.startswith("@"):
                    captured["prompt_file_existed"] = Path(tok[1:]).exists()
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id="1",
            plan_path=plan_path,
            repo_root=repo_root,
            max_iterations=1,
        )
        argv = captured["argv"]
        prompt_token = next(t for t in argv if isinstance(t, str) and t.startswith("@"))
        prompt_path = Path(prompt_token[1:])
        # Filename matches prompt-<uuid16>.md pattern.
        assert prompt_path.parent.name == ".tmp"
        assert prompt_path.parent.parent.name == "spec-reviews"
        assert prompt_path.name.startswith("prompt-")
        assert prompt_path.name.endswith(".md")
        assert len(prompt_path.stem.removeprefix("prompt-")) == 16
        # File existed at dispatch time per B4-2.
        assert captured["prompt_file_existed"] is True

    def test_argv_uses_at_filepath_not_inline_prompt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B4-2: argv contains @<filepath> reference; no inline prompt."""
        repo_root = tmp_path / "repo"
        (repo_root / ".claude" / "spec-reviews").mkdir(parents=True)
        plan_path = repo_root / "planning" / "claude-plan-tdd.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text("### Task 1: dummy\n- [x] step\n", encoding="utf-8")
        captured_argv: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = '{"approved": true, "issues": []}'
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            captured_argv.append(list(cmd))
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id="1",
            plan_path=plan_path,
            repo_root=repo_root,
            max_iterations=1,
        )
        argv = captured_argv[0]
        at_tokens = [t for t in argv if isinstance(t, str) and t.startswith("@")]
        assert len(at_tokens) == 1
        # No inline prompt content (would be a giant string in argv).
        assert all(len(t) < 1000 for t in argv if isinstance(t, str))

    def test_tempfile_cleaned_up_after_dispatch(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B4-3: try/finally cleans tempfile post-dispatch."""
        repo_root = tmp_path / "repo"
        (repo_root / ".claude" / "spec-reviews").mkdir(parents=True)
        plan_path = repo_root / "planning" / "claude-plan-tdd.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text("### Task 1: dummy\n- [x] step\n", encoding="utf-8")
        prompt_paths: list[Path] = []

        class FakeResult:
            returncode = 0
            stdout = '{"approved": true, "issues": []}'
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            for tok in cmd:
                if isinstance(tok, str) and tok.startswith("@"):
                    prompt_paths.append(Path(tok[1:]))
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id="1",
            plan_path=plan_path,
            repo_root=repo_root,
            max_iterations=1,
        )
        assert prompt_paths
        for p in prompt_paths:
            assert not p.exists(), f"tempfile leaked: {p}"

    def test_large_prompt_does_not_blow_argv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B4-4: 200KB diff -> argv stays under 32K chars."""
        repo_root = tmp_path / "repo"
        (repo_root / ".claude" / "spec-reviews").mkdir(parents=True)
        plan_path = repo_root / "planning" / "claude-plan-tdd.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text("### Task 1: dummy\n- [x] step\n", encoding="utf-8")
        # Force a giant diff via monkeypatch.
        monkeypatch.setattr(
            "spec_review_dispatch._collect_task_diff",
            lambda repo, tid: "x" * 200_000,
        )
        captured_argv: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = '{"approved": true, "issues": []}'
            stderr = ""

        def fake_run(cmd: list[str], **kw: object) -> FakeResult:
            captured_argv.append(list(cmd))
            return FakeResult()

        monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id="1",
            plan_path=plan_path,
            repo_root=repo_root,
            max_iterations=1,
        )
        argv_total_len = sum(len(t) for t in captured_argv[0] if isinstance(t, str))
        assert argv_total_len < 5_000  # well under Windows 32K limit
```

Add `import spec_review_dispatch` and `from pathlib import Path` if missing.

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_spec_review_dispatch.py::TestSpecReviewerFileReference -v`
Expected: all 4 FAIL (current impl puts inline prompt in argv → no
`@`-prefix tokens, no tempfile created).

- [ ] **Step 3: Run `make verify`**

Expected: only the 4 new tests fail; ruff + mypy clean.

- [ ] **Step 4: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 B4 spec_review_dispatch file-reference tests"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [ ] **Step 5: Refactor `dispatch_spec_reviewer` to use file-reference pattern**

Edit `skills/sbtdd/scripts/spec_review_dispatch.py` around line 413-485.
Locate the prompt-build + argv-build block (lines ~413-435):

```python
    plan_text = plan_path.read_text(encoding="utf-8")
    task_text = _extract_task_text(plan_text, task_id)
    diff_text = _collect_task_diff(repo_root, task_id)
    prompt = _build_reviewer_prompt(task_id, task_text, diff_text)
    # ...
    cmd: list[str] = ["claude"]
    if effective_model is not None:
        cmd.extend(["--model", effective_model])
    cmd.extend(["-p", _REVIEWER_SKILL_REF, prompt])
```

Replace with file-reference pattern:

```python
    plan_text = plan_path.read_text(encoding="utf-8")
    task_text = _extract_task_text(plan_text, task_id)
    diff_text = _collect_task_diff(repo_root, task_id)
    prompt = _build_reviewer_prompt(task_id, task_text, diff_text)
    # v1.0.7 B4: write prompt to project-relative tempfile + pass
    # ``@<filepath>`` reference in argv. Closes WinError 206 (Windows
    # cmdline limit ~32K chars) when prompt + diff exceed argv budget;
    # filepath is bounded to ~120 chars regardless of prompt size.
    # Same pattern as v1.0.3 cross-check Item B fix.
    import uuid
    prompt_dir = repo_root / ".claude" / "spec-reviews" / ".tmp"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"prompt-{uuid.uuid4().hex[:16]}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    # v0.3.0 Feature E: apply INV-0 cascade then optionally inject
    # ``--model <id>`` BEFORE the ``-p`` flag (mirrors superpowers_dispatch
    # convention). With model=None (default) argv is byte-identical to v0.2.x
    # except for the prompt token which is now ``@<filepath>``.
    from superpowers_dispatch import _apply_inv0_model_check

    effective_model = _apply_inv0_model_check(model, skill_field_name)
    cmd: list[str] = ["claude"]
    if effective_model is not None:
        cmd.extend(["--model", effective_model])
    cmd.extend(["-p", _REVIEWER_SKILL_REF, f"@{prompt_path}"])
```

Then wrap the for-loop dispatch in `try/finally` to clean the tempfile:

Locate the `for iteration in range(1, max_iterations + 1):` block (line
~436). Wrap the entire iteration loop in `try/finally`:

```python
    iter_history: list[dict[str, Any]] = []
    rwt_kwargs: dict[str, Any] = {"timeout": timeout, "capture": True, "cwd": str(repo_root)}
    if stream_prefix is not None:
        rwt_kwargs["stream_prefix"] = stream_prefix
    try:
        for iteration in range(1, max_iterations + 1):
            # ... existing iter loop body unchanged ...
    finally:
        # v1.0.7 B4: cleanup tempfile regardless of outcome.
        prompt_path.unlink(missing_ok=True)
```

Move the existing iter-loop body (lines ~436-485) into the `try:` block,
preserving its current logic. The duplicated `iter_history` declaration
must be hoisted to the outer scope (already is, per the line above the
new `try:`).

NOTE: the existing function returns `SpecReviewResult` from inside the
for-loop and raises `SpecReviewError` from inside the for-loop too;
both flows now hit the `finally:` block as required.

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_spec_review_dispatch.py -v`
Expected: full module green including the 4 new B4 tests.

- [ ] **Step 7: Run `make verify`**

Expected: clean.

- [ ] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant fix --message "v1.0.7 B4 spec_review_dispatch file-reference closes WinError 206"`

Expected: `fix:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [ ] **Step 9: Hoist `import uuid` to module top + audit other long-prompt callsites**

Move the local `import uuid` to the module-top imports block of
`spec_review_dispatch.py`. Confirm no other callsite in the codebase
passes a >32K prompt inline via argv (grep for `claude.*-p` patterns):

```bash
grep -rn "claude.*-p" skills/sbtdd/scripts/ | grep -v "claude-p"
```

If other dispatch helpers exhibit the same pattern (e.g., a future
cross-check helper), document them in a follow-up backlog entry; do
NOT broaden the v1.0.7 B4 scope — that's a separate cycle.

- [ ] **Step 10: Run `make verify`**

Expected: clean.

- [ ] **Step 11: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 B4 hoist uuid import + audit other callsites"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next task.

---

### Task 6: B3 — `state_file.atomic_write_json` Windows PermissionError retry

**Files:**
- Modify: `skills/sbtdd/scripts/state_file.py:143-171` (wrap `os.replace`
  in 3-attempt retry-with-backoff)
- Modify: `tests/test_state_file.py` (extend with
  `TestAtomicWriteJsonRetry` class for escenarios B3-1, B3-2, B3-3)

Covers escenarios B3-1, B3-2, B3-3 from spec sec.4.6.

#### Red Phase

- [x] **Step 1: Write failing tests in `tests/test_state_file.py`**

Append:

```python
class TestAtomicWriteJsonRetry:
    """v1.0.7 B3 atomic_write_json retry per spec sec.4.6."""

    def test_permission_error_triggers_retry(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-1: PermissionError on first os.replace -> retry."""
        path = tmp_path / "audit.json"
        attempts: list[int] = []
        original_replace = os.replace

        def flaky_replace(src: str, dst: str) -> None:
            attempts.append(1)
            if len(attempts) == 1:
                raise PermissionError(5, "Access denied", src)
            original_replace(src, dst)

        sleeps: list[float] = []

        def fake_sleep(s: float) -> None:
            sleeps.append(s)

        monkeypatch.setattr("state_file.os.replace", flaky_replace)
        monkeypatch.setattr("state_file.time.sleep", fake_sleep)
        state_file.atomic_write_json(path, {"key": "value"})
        assert len(attempts) == 2
        # First retry slept 100ms (attempt-number 1 * 100ms).
        assert sleeps == [0.1]
        assert json.loads(path.read_text(encoding="utf-8")) == {"key": "value"}

    def test_retry_backoff_grows_per_attempt(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-2: backoff = 100ms × attempt-number."""
        path = tmp_path / "audit.json"
        original_replace = os.replace

        def flaky_replace(src: str, dst: str) -> None:
            flaky_replace.calls += 1  # type: ignore[attr-defined]
            if flaky_replace.calls < 3:  # type: ignore[attr-defined]
                raise PermissionError(5, "Access denied", src)
            original_replace(src, dst)

        flaky_replace.calls = 0  # type: ignore[attr-defined]
        sleeps: list[float] = []

        monkeypatch.setattr("state_file.os.replace", flaky_replace)
        monkeypatch.setattr("state_file.time.sleep", lambda s: sleeps.append(s))
        state_file.atomic_write_json(path, {"key": "value"})
        # 2 retries: attempt 1 sleeps 100ms, attempt 2 sleeps 200ms.
        assert sleeps == [0.1, 0.2]

    def test_retry_exhaustion_reraises_permission_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B3-3: 3 attempts all fail -> re-raise PermissionError."""
        path = tmp_path / "audit.json"

        def always_fail(src: str, dst: str) -> None:
            raise PermissionError(5, "Access denied", src)

        monkeypatch.setattr("state_file.os.replace", always_fail)
        monkeypatch.setattr("state_file.time.sleep", lambda s: None)
        with pytest.raises(PermissionError, match="Access denied"):
            state_file.atomic_write_json(path, {"key": "value"})
```

Add `import json`, `import os`, `import state_file`, and `from pathlib import Path` if missing at top of file.

- [x] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_state_file.py::TestAtomicWriteJsonRetry -v`
Expected: all 3 FAIL (current impl raises on first PermissionError;
no retry; no `time.sleep` call).

- [x] **Step 3: Run `make verify`**

Expected: only the 3 new tests fail; ruff + mypy clean.

- [x] **Step 4: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 B3 atomic_write_json retry-with-backoff tests"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [x] **Step 5: Add retry-with-backoff to `atomic_write_json`**

Edit `skills/sbtdd/scripts/state_file.py:143-171` — replace the body:

```python
def atomic_write_json(path: Path, data: object) -> None:
    """Atomic JSON write via ``tempfile.mkstemp`` + ``os.replace``.

    v1.0.5 T3 Refactor (iter-2 WARNING fix): DRY-shared helper used by
    ``auto_cmd._write_audit`` (per-worker sidecar pattern) and any
    other module that needs a cross-platform atomic JSON write under
    concurrent dispatch. ``tempfile.mkstemp`` ensures concurrent
    writers in the same directory receive unique tmp names so they
    never collide. ``os.replace`` is atomic on POSIX and Windows; on
    failure the tmp file is cleaned up before re-raising so nothing
    leaks.

    v1.0.7 B3: ``os.replace`` is wrapped in a 3-attempt retry-with-backoff
    (``100ms * attempt-number``) absorbing transient Windows
    ``PermissionError`` flakes from AV-scanner / concurrent-writer
    contention. Empirical context: v1.0.6 mid-cycle hit
    ``PermissionError: [WinError 5] Access is denied:
    '...auto-run.json.q6wjytm7.tmp' -> '...auto-run.json'`` once;
    retry absorbs the typical AV-scanner release window (~150ms).
    Final attempt failure re-raises the original ``PermissionError``
    so the operator sees the real error if the lock is persistent.

    Args:
        path: Destination JSON path. Parent directory is created if
            absent.
        data: JSON-serialisable payload (dict, list, scalar, etc.).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(suffix=".tmp", prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        # v1.0.7 B3: retry-with-backoff for Windows PermissionError flakes.
        last_exc: PermissionError | None = None
        for attempt in range(1, 4):  # 3 attempts: 0 backoff, 100ms, 200ms
            try:
                os.replace(tmp_str, path)
                return
            except PermissionError as exc:
                last_exc = exc
                if attempt < 3:
                    time.sleep(0.1 * attempt)
        # 3 attempts exhausted; re-raise the last PermissionError.
        assert last_exc is not None  # mypy: unreachable
        raise last_exc
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise
```

Add `import time` to the top of `state_file.py` if not already present.

NOTE: the inner retry loop's `return` exits early on success; the outer
`except Exception:` cleanup branch only fires if `json.dump` raised OR
the final retry re-raised. The `os.replace` success path bypasses the
cleanup (the tmp file is gone — `os.replace` rename consumed it).

- [x] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_state_file.py -v`
Expected: full module green including the 3 new B3 tests.

- [x] **Step 7: Run `make verify`**

Expected: clean.

- [x] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant fix --message "v1.0.7 B3 atomic_write_json retry-with-backoff for Windows PermissionError"`

Expected: `fix:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [x] **Step 9: Apply same retry to `atomic_write_text` (DRY)**

Inspect `state_file.atomic_write_text` (line 174+) — it has the same
`os.replace` pattern. Apply identical retry-with-backoff for symmetry,
since both helpers share the same concurrent-writer + AV-scanner
exposure surface.

OR: extract the retry loop into a private `_replace_with_retry(tmp_str, path)`
helper used by both `atomic_write_json` and `atomic_write_text` to keep
DRY. Choose whichever surface is cleaner; the helper-extraction path
is preferred when the function bodies otherwise diverge significantly.

- [x] **Step 10: Run `make verify`**

Expected: clean.

- [x] **Step 11: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "refactor v1.0.7 B3 share retry helper between atomic_write_json + atomic_write_text"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next task.

---

## Pillar C LOCKED — Selective polish (Q4'=a all 5 items, iter-2 collapsed per C2/C5 carry-forward)

### Task 7: Combined Pillar C polish (C1+C5+C6+C7) — single TDD cycle

> **v1.0.7 iter-2 carry-forward C2/C5 resolution**: original plan had
> C1+C5+C6+C7 as 4 separate tasks (T7-T10) each with empty-Refactor
> commits. v1.0.5 Item D Q3-A `_preflight` HARD-BLOCK rejects empty
> Refactor diffs (canonical TDD triplet must have real diffs in each
> phase). Resolution: collapse all 4 into ONE task with single
> Red/Green/Refactor cycle:
> - Red: write all 4 doc smoke tests in one commit.
> - Green: apply all 4 doc edits in one commit.
> - Refactor: cross-link C1 ↔ C6 in K-4 helper docs (real diff —
>   both C1 inline comment + C6 docstring note touch the same
>   `_validate_forwardable_flags_against_argparse` helper; the Refactor
>   makes them reference each other as a coherent helper-level docs
>   block instead of two disjoint additions).

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py:1447`
  (`_validate_forwardable_flags_against_argparse` — C1 inline comment
  + C6 docstring note; Refactor cross-links them)
- Modify: `skills/sbtdd/scripts/close_task_cmd.py:451` (C5 deprecation
  marker comment with monkeypatch footgun warning)
- Modify: `skills/sbtdd/SKILL.md` (C7 ship-time methodology-activity
  procedure section)
- Modify: `tests/test_auto_cmd.py` (smoke tests for C1 + C6)
- Modify: `tests/test_close_task_cmd.py` (smoke test for C5)
- Create: `tests/test_skill_md_methodology_activity_procedure.py`
  (smoke test for C7)

Covers escenarios C1, C5, C6, C7 from spec sec.4.7. C-X-K3-Removal
ships in T8 (separate task; has real code change).

#### Red Phase

- [ ] **Step 1: Write 4 failing smoke tests covering C1+C5+C6+C7 with discriminating class names**

> **iter-3 carry-forward (mel+bal+cas WARNING)**: even though all 4
> doc smoke tests land in a single Red commit (per C2/C5 collapse),
> the test CLASS NAMES must remain distinct (`TestC1*`, `TestC5*`,
> `TestC6*`, `TestC7*`) so future bisect can pinpoint which doc
> surface regressed. Do NOT collapse the test classes themselves into
> one — only the commit boundary collapses.

Append to `tests/test_auto_cmd.py` (C1 + C6 — both touch K-4 helper):

```python
class TestC1ForwardableFlagsHelperDocs:
    """v1.0.7 C1 K-4 helper docs comment per spec sec.4.7."""

    def test_helper_source_documents_single_level_subparser_walk(self) -> None:
        """C1: helper source contains comment about single-level walk limitation."""
        import inspect
        src = inspect.getsource(auto_cmd._validate_forwardable_flags_against_argparse)
        assert "single-level subparser walk" in src.lower()


class TestC6ForwardableFlagsImportlibReloadCaveat:
    """v1.0.7 C6 K-4 helper docstring caveat per spec sec.4.7."""

    def test_docstring_documents_importlib_reload_interaction(self) -> None:
        """C6: docstring notes importlib.reload caveat for monkeypatch tests."""
        doc = auto_cmd._validate_forwardable_flags_against_argparse.__doc__ or ""
        assert "importlib.reload" in doc
        assert "monkeypatch" in doc.lower()

    def test_docstring_cross_links_c1_inline_comment(self) -> None:
        """C6 Refactor cross-link (iter-2 carry-forward C2/C5): docstring references C1."""
        doc = auto_cmd._validate_forwardable_flags_against_argparse.__doc__ or ""
        # Refactor phase cross-links C1 inline comment + C6 docstring note
        # so the helper's docs read as a coherent block.
        assert "single-level subparser" in doc.lower() or "see inline comment" in doc.lower()
```

Append to `tests/test_close_task_cmd.py` (C5 — touches alias):

```python
class TestC5DeprecationMarkerMonkeypatchWarning:
    """v1.0.7 C5 K-3 deprecation marker monkeypatch warning per spec sec.4.7."""

    def test_alias_line_comment_warns_about_monkeypatch_footgun(self) -> None:
        """C5: comment on alias line mentions monkeypatch warning."""
        import inspect
        src = inspect.getsource(close_task_cmd)
        assert "_preflight_triplet_check = _preflight" in src
        lines = src.splitlines()
        for i, line in enumerate(lines):
            if "_preflight_triplet_check = _preflight" in line:
                surrounding = "\n".join(lines[max(0, i - 5) : i + 1])
                assert "monkeypatch" in surrounding.lower()
                assert "v1.0.7" in surrounding
                return
        raise AssertionError("alias line not found")
```

Create `tests/test_skill_md_methodology_activity_procedure.py` (C7):

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 C7 smoke test for SKILL.md methodology-activity procedure."""

from __future__ import annotations

from pathlib import Path


def test_skill_md_documents_methodology_activity_ship_time_procedure() -> None:
    """C7: SKILL.md contains methodology-activity ship-time procedure section."""
    skill_md = Path(__file__).parent.parent / "skills" / "sbtdd" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "methodology-activity" in text.lower()
    assert "ship time" in text.lower() or "ship-time" in text.lower()
    assert "v1.0.X+1 LOCKED" in text or "next-cycle LOCKED" in text.lower()
```

- [ ] **Step 2: Run all 4 new tests to verify failure**

Run: `pytest tests/test_auto_cmd.py::TestC1ForwardableFlagsHelperDocs tests/test_auto_cmd.py::TestC6ForwardableFlagsImportlibReloadCaveat tests/test_close_task_cmd.py::TestC5DeprecationMarkerMonkeypatchWarning tests/test_skill_md_methodology_activity_procedure.py -v`

Expected: all FAIL (4 doc surfaces missing).

- [ ] **Step 3: Run `make verify`**

Expected: only the new doc smoke tests fail; ruff + mypy clean.

- [ ] **Step 4: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 Pillar C polish doc smoke tests (C1+C5+C6+C7)"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [ ] **Step 5: Apply C1 inline comment in K-4 helper**

Edit `skills/sbtdd/scripts/auto_cmd.py:1447` — locate
`_validate_forwardable_flags_against_argparse` body and insert just
above the parser-walk loop:

```python
    # v1.0.7 C1: single-level subparser walk; deeper nesting not supported.
    # If the plugin gains deeply nested subparsers (e.g., subcommands of
    # subcommands), extend this loop with a recursive walk.
    for action in parser._actions:
        # ... existing walk logic ...
```

- [ ] **Step 6: Apply C5 deprecation marker comment in close_task_cmd.py**

Edit `skills/sbtdd/scripts/close_task_cmd.py:451`. Replace existing
deprecation comment block + alias line with:

```python
# v1.0.6 K-3: alias for backward-compat; legacy callsites monkeypatched
# this name. SCHEDULED REMOVAL in v1.0.7 C-X-K3-Removal (T8 of v1.0.7).
# v1.0.7 C5 NOTE: monkeypatch.setattr("close_task_cmd._preflight_triplet_check",
# fake) does NOT patch the canonical `_preflight` (alias is a module-load-time
# rebind, not a transparent reference). Tests must monkeypatch the canonical
# `_preflight` name to actually patch behavior. This footgun is the reason
# C-X-K3-Removal proceeds (single canonical entry point).
_preflight_triplet_check = _preflight
```

- [ ] **Step 7: Apply C6 docstring note in K-4 helper**

Continue editing `auto_cmd.py:1447`. In the
`_validate_forwardable_flags_against_argparse` docstring, insert a
note paragraph just before the `Raises:` section:

```
v1.0.7 C6 NOTE: tests that monkeypatch ``_FORWARDABLE_FLAGS`` should
call this helper directly rather than reloading ``auto_cmd`` via
``importlib.reload`` to avoid the import-time guard interaction. The
guard fires at module import; reload re-imports + re-fires, which can
mask the monkeypatch's effect. Direct helper invocation respects the
patched dictionary.
```

- [ ] **Step 8: Apply C7 ship-time methodology-activity procedure in SKILL.md**

Append to `skills/sbtdd/SKILL.md` (placement: near existing
version-notes sections):

```markdown
### Ship-time methodology-activity procedure (v1.0.7+)

Any methodology-activity finding (F-J9, F-J10, F-A2, F-Resume, P2 — i.e.,
non-test process observations surfaced during own-cycle dogfood) that
does NOT trigger a ship abort gets a v1.0.X+1 LOCKED entry at ship
time, NOT mid-cycle. Process discipline:

1. **At ship-time** (post pre-merge Loop 2 convergence + before tag
   push), enumerate all methodology-activity findings observed during
   the cycle (own-cycle dogfood, sequential vs --parallel mode
   decisions, manual fallbacks, etc.).
2. **Triage each finding** as either:
   - **Ship-blocker** → fix in current cycle before ship.
   - **Next-cycle LOCKED** → write a memory file
     `project_v1_0_X+1_<finding>_locked.md` referenced by
     `MEMORY.md` index. Include in next-cycle spec-base sec.1
     "Out of scope vN.M.Z+1 (rolled forward)".
   - **Discard** → document rationale in current-cycle CHANGELOG
     "Process notes" section (e.g., "F-J9 observation noted but
     superseded by v1.0.7 Pillar A").
3. **Prevents deferral pipeline drift between cycles**: by ship-time
   triaging methodology findings, next cycle's spec-base inherits a
   complete LOCKED backlog without mid-cycle scope creep.

This procedure is documented for v1.0.7 onwards; precedent established
by v1.0.6 own-cycle dogfood findings → v1.0.7 LOCKED Pillar B
(B5+B4+B3) carry-forward.
```

- [ ] **Step 9: Run all 4 new doc tests + full make verify**

Run: `pytest tests/test_auto_cmd.py::TestC1ForwardableFlagsHelperDocs tests/test_auto_cmd.py::TestC6ForwardableFlagsImportlibReloadCaveat tests/test_close_task_cmd.py::TestC5DeprecationMarkerMonkeypatchWarning tests/test_skill_md_methodology_activity_procedure.py -v`

Expected: 3 of 4 PASS; the C6 cross-link test still FAILS (Refactor
phase will resolve it). All other tests still green.

Then: `make verify`
Expected: only the C6 cross-link smoke test fails; ruff + mypy clean
on production changes.

- [ ] **Step 10: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.7 Pillar C polish (C1+C5+C6+C7) docs land"`

Expected: `feat:` commit lands; state advances to `refactor`. The
remaining failing C6 cross-link test is the explicit Refactor surface
(designed-in real Refactor diff per iter-2 C2/C5 carry-forward).

#### Refactor Phase

- [ ] **Step 11: Cross-link C1 inline comment + C6 docstring note in K-4 helper**

Edit `skills/sbtdd/scripts/auto_cmd.py:1447` —
`_validate_forwardable_flags_against_argparse`. The Green-phase additions
left the C1 inline comment (above the walk loop) and the C6 docstring
note (in the docstring) as two disjoint additions. Refactor restructures
them into a coherent helper-level docs block:

In the docstring, change the C6 note paragraph to reference C1 explicitly:

```
v1.0.7 C6 NOTE: tests that monkeypatch ``_FORWARDABLE_FLAGS`` should
call this helper directly rather than reloading ``auto_cmd`` via
``importlib.reload`` to avoid the import-time guard interaction. The
guard fires at module import; reload re-imports + re-fires, which can
mask the monkeypatch's effect. Direct helper invocation respects the
patched dictionary.

Implementation note: the parser walk below is single-level (see
inline comment above the loop body for limitations + extension path).
```

This satisfies the C6 cross-link smoke test (`assert "single-level
subparser" in doc.lower() or "see inline comment" in doc.lower()`).

- [ ] **Step 12: Run smoke tests + `make verify`**

Run: `pytest tests/test_auto_cmd.py::TestC6ForwardableFlagsImportlibReloadCaveat -v`
Expected: PASS (cross-link present).

Then: `make verify`
Expected: full suite green.

- [ ] **Step 13: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "refactor v1.0.7 Pillar C polish -- cross-link C1 inline comment + C6 docstring in K-4 helper"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to next
task. Real Refactor diff (cross-link statement added to docstring +
test PASSES post-cross-link) satisfies v1.0.5 `_preflight` HARD-BLOCK.

---

### Task 8: C-X-K3-Removal — Remove `_preflight_triplet_check` 1-cycle alias

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py:451` (delete the
  alias line + the C5 comment block above it)
- Modify: `tests/test_close_task_cmd.py` (update any test that
  monkeypatches `_preflight_triplet_check` to monkeypatch `_preflight`
  directly; add new test asserting `AttributeError` on legacy name access)

Covers escenario C-X-K3-Removal from spec sec.4.7.

**Plan invariant**: T8 must run AFTER T7 (T7 collapsed Pillar C polish
adds the C5 warning comment on the alias line; T8 removes both alias +
comment together).

**Commit prefix framing (v1.0.7 iter-2 carry-forward W10)**: T8 Green
commit uses `--variant fix` because the alias removal closes the
v1.0.7 C5-documented monkeypatch footgun (semantically a fix to the
test discipline surface — the alias was a footgun that silently
bypassed canonical-name patches; removing it forces tests onto the
correct surface). Even though the diff is "code removal", the framing
as `fix:` is accurate per CLAUDE.local.md sec.5 commit prefix map
(Green close uses `feat:` for new features OR `fix:` for bug-fix
behavior change).

#### Red Phase

- [ ] **Step 1: Write failing test asserting `AttributeError` on legacy alias**

Append to `tests/test_close_task_cmd.py`:

```python
class TestCXK3RemovalAliasGone:
    """v1.0.7 C-X-K3-Removal: alias removed per spec sec.4.7."""

    def test_legacy_alias_no_longer_attribute_of_module(self) -> None:
        """C-X-K3-Removal: `_preflight_triplet_check` raises AttributeError."""
        with pytest.raises(AttributeError, match="_preflight_triplet_check"):
            close_task_cmd._preflight_triplet_check  # noqa: B018

    def test_canonical_preflight_still_callable(
        self,
        tmp_path: Path,
    ) -> None:
        """C-X-K3-Removal: canonical `_preflight` still works."""
        # Sanity check: canonical name exists + is callable.
        assert callable(close_task_cmd._preflight)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_close_task_cmd.py::TestCXK3RemovalAliasGone -v`
Expected: `test_legacy_alias_no_longer_attribute_of_module` FAILS — alias
still present from T8; the second test PASSES.

- [ ] **Step 3: Audit existing tests for `_preflight_triplet_check` references**

Run:

```bash
grep -rn "_preflight_triplet_check" tests/
grep -rn "_preflight_triplet_check" skills/
```

For each callsite that monkeypatches or references the alias name,
note the location. The Green step rewrites them to use `_preflight`.

- [ ] **Step 4: Run `make verify`**

Expected: only the new alias-removal test fails (and possibly some
pre-existing tests that monkeypatch the alias — those will need
update in Green); ruff + mypy clean except for any pre-existing
test refs that produce import warnings.

- [ ] **Step 5: Close Red phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "add v1.0.7 C-X-K3-Removal alias-removal regression tests"`

Expected: `test:` commit lands; state advances to `green`.

#### Green Phase

- [ ] **Step 6: Remove the alias line + C5 comment**

Edit `skills/sbtdd/scripts/close_task_cmd.py:451`. Delete BOTH the
multi-line C5 comment block and the alias assignment line:

Lines to remove:
```python
# v1.0.6 K-3: alias for backward-compat; legacy callsites monkeypatched
# this name. SCHEDULED REMOVAL in v1.0.7 C-X-K3-Removal.
# v1.0.7 C5 NOTE: monkeypatch.setattr("close_task_cmd._preflight_triplet_check",
# fake) does NOT patch the canonical `_preflight` (alias is a module-load-time
# rebind, not a transparent reference). Tests must monkeypatch the canonical
# `_preflight` name to actually patch behavior. This footgun is the reason
# C-X-K3-Removal proceeds (single canonical entry point).
_preflight_triplet_check = _preflight
```

- [ ] **Step 7: Update test callsites that monkeypatched the alias**

For each location identified in Red Step 3, rewrite:

```python
monkeypatch.setattr("close_task_cmd._preflight_triplet_check", fake)
```

to:

```python
monkeypatch.setattr("close_task_cmd._preflight", fake)
```

Same transformation for any direct attribute references.

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_close_task_cmd.py -v`
Expected: full module green including the new C-X-K3-Removal tests
+ all previously-passing tests (after monkeypatch target rewrites).

- [ ] **Step 9: Run `make verify`**

Expected: clean.

- [ ] **Step 10: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant fix --message "v1.0.7 C-X-K3-Removal remove _preflight_triplet_check alias + update tests"`

Expected: `fix:` commit lands; state advances to `refactor`.

#### Refactor Phase

- [ ] **Step 11: Audit codebase for any remaining alias references**

Final sweep:

```bash
grep -rn "_preflight_triplet_check" .
```

Expected: zero matches except in CHANGELOG history references (which
should be left as-is — they document the alias's lifecycle).

If any test files OR production code still references the alias, fix
them now (monkeypatch path or direct call). Confirm test count
preserved.

- [ ] **Step 12: Run `make verify`**

Expected: clean.

- [ ] **Step 13: Close Refactor phase + close task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "polish v1.0.7 C-X-K3-Removal final alias sweep"`

Then: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: `refactor:` + `chore:` commits land; state advances to `done`.

---

## Post-cycle: own-cycle dogfood + ship checklist

After T11 closes:

1. **Verify state file is `done`**:
   ```bash
   cat .claude/session-state.json | grep current_phase
   ```
   Expected: `"current_phase": "done"`.

2. **Run `/sbtdd pre-merge`** end-to-end (post Pillar A ship; orchestrator
   inherits TTY → Loop 1 + Loop 2 dispatch should complete):
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
   Expected: Loop 1 clean-to-go + Loop 2 verdict >= `GO_WITH_CAVEATS`
   full no-degraded, **WITHOUT INV-0 override** (re-establish streak
   from 1 cycle per Q3=a strict). If `/sbtdd pre-merge` fails for
   non-content reasons (regression, transient infra), fall back to
   manual `python skills/magi/scripts/run_magi.py` per spec sec.6.4 +
   document in CHANGELOG.

3. **Bump version 1.0.6 → 1.0.7** in `.claude-plugin/plugin.json` +
   `.claude-plugin/marketplace.json`. Sync values across both files.

4. **Write CHANGELOG `[1.0.7]` entry** with sections per spec sec.7.2:
   Added (PTY allocation + Windows hybrid + worker runtime guard +
   spec_review file-reference + atomic_write retry), Changed (drift
   regex line-anchored + 4 polish items), Removed (K-3 alias),
   Process notes (Pillar A NON-POSTPONABLE + Q1'=a single sequential
   forced + Q2'=b promotion + Q3'=b ordering + Q4'=a all 5 + Q5'=a
   default G2 + A3 dogfood empirical findings), Deferred (B2, C2, C4,
   C8, Pillar D, Edge cases → v1.0.8; v1.0.4 carry-forward → v1.1.0).

5. **Update README + SKILL.md + CLAUDE.md** per spec sec.7.3:
   - README: `auto --parallel` operational status post Pillar A;
     PTY allocation note POSIX vs Windows; `SBTDD_AUTO_PARALLEL_WORKER`
     operator-facing env var doc.
   - SKILL.md: `### v1.0.7 notes` section.
   - CLAUDE.md (gitignored): pointer.

6. **Merge `feature/v1.0.7-bundle` → `main`** with `git merge --no-ff`.
   Tag `v1.0.7` at the merge commit. Push tag (with explicit user
   authorization).

---

## Self-review checklist (run before handoff)

1. **Spec coverage** (post iter-2 carry-forward C2/C5 task collapse:
   11 tasks → 8 tasks):
   - [x] A1 → T1 (POSIX PTY allocation + lifecycle helper + leak guard
     in `subprocess_utils`)
   - [x] A2 → T2 (Windows hybrid + Q2'=b runtime guard + sec.0.1 chain
     bypass + INV-16 evidence sidecar per C4 carry-forward)
   - [x] A3 → T3 (F-A2 dogfood empirical e2e with REAL chicken-and-egg
     fixture per C3 carry-forward)
   - [x] B5 → T4 (drift regex line-anchored)
   - [x] B4 → T5 (spec_review_dispatch file-reference)
   - [x] B3 → T6 (atomic_write_json retry)
   - [x] C1+C5+C6+C7 → T7 (combined Pillar C polish single TDD cycle
     with real Refactor cross-link per C2/C5 carry-forward)
   - [x] C-X-K3-Removal → T8 (alias removal; W10 carry-forward
     `--variant fix` framing documented)

2. **Placeholder scan**: zero placeholder markers (no uppercase
   to-be-determined / to-do / to-be-defined word-boundary tokens)
   in this plan; every step has concrete code or commands.

3. **Type consistency**:
   - `_spawn_worker_with_pty(argv: list[str], env: dict[str, str]) -> subprocess.Popen[bytes]` (T1) — referenced consistently in T2's `_spawn_worker(argv, env)` dispatcher.
   - `_close_pty_master(proc: subprocess.Popen[bytes]) -> None` (T1) — new lifecycle helper per C1 carry-forward.
   - `_run_verification(root: Path) -> None` (T2) — signature unchanged from existing v1.0.6 baseline; only body modified.
   - `_persist_worker_verify_evidence(root: Path, captured: list[dict[str, object]]) -> None` (T2) — new helper per C4 carry-forward.
   - `_OPEN_CHECKBOX_LINE_RE: re.Pattern[str]` (T4) — new module-level constant in `drift.py`.
   - `_preflight` (post-T8) — canonical name remains; alias removed.
   - `dispatch_spec_reviewer(...)` (T5) — public signature unchanged; only argv-build internals refactored.
   - `atomic_write_json(path: Path, data: object) -> None` (T6) — public signature unchanged; only body wrapped with retry loop.

4. **Cross-task ordering invariants** (post iter-3 carry-forward T6 → T2 swap):
   - T1 → T6 → T2 → T3 → T4 → T5 → T7 → T8 (sequential execution
     order).
   - T1 → T2 (A2 imports `_spawn_worker_with_pty` + `_close_pty_master`
     from T1).
   - T6 → T2 (HARD per iter-3 bal+cas WARNING resolution): T2's
     `_persist_worker_verify_evidence` calls
     `state_file.atomic_write_json` which T6 hardens with retry; T6
     lands BEFORE T2 so the sidecar write benefits from retry from
     day 1, eliminating documented Windows PermissionError flake risk
     during T3 dogfood.
   - T2 → T3 (A3 e2e exercises T1+T2 production code; fixture project
     depends on T2 worker-mode bypass to avoid hanging).
   - T7 → T8 (T7 collapsed Pillar C polish adds C5 comment on alias
     line; T8 removes both alias + comment together).
   - All other tasks file-disjoint or doc-only.

5. **Commit prefix discipline**: every Red closes with `test:`, every
   Green with `feat:` (new features) or `fix:` (bug fixes), every
   Refactor with `refactor:`, every task close with `chore:` via
   `close-task --skip-spec-review`.
