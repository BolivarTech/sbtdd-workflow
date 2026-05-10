# BDD overlay — sbtdd-workflow v1.0.7

> Generado 2026-05-09 a partir de `sbtdd/spec-behavior-base.md` v1.0.7.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1+v1.0.2+v1.0.3+v1.0.4
> +v1.0.5+v1.0.6 precedent (chicken-and-egg until v1.0.7 Pillar A
> ships + v1.0.8 own-cycle validates empirically).
>
> v1.0.7 = **`--parallel` operational unblock cycle (NON-POSTPONABLE)**
> per user mandate 2026-05-09 ("dejar parallel completamente
> operacional"). Pillar A is hard-LOCKED + non-negotiable. Three
> pillars: Pillar A PRIMARY (A1 POSIX PTY allocation + A2 Windows
> hybrid Option B-W3 fallback + A3 F-A2 dogfood empirical
> validation); Pillar B LOCKED (B5 + B4 + B3 v1.0.6 dogfood
> findings); Pillar C LOCKED (C1+C5+C6+C7+C-X-K3-Removal selective
> polish).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex. R5 compliant: frontmatter
> docstring above.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.7**: ships PTY allocation in worker subprocess spawn
(Pillar A non-postponable per user mandate) + 3 Pillar B fixes
empirically discovered in v1.0.6 own-cycle (B5+B4+B3) + 5
cherry-picked Pillar C polish items (C1+C5+C6+C7+C-X-K3-Removal).

Decisiones macro (baked in spec-base, confirmed by user 2026-05-09):

- **Q1 (scope) = B**: operational unblock NON-POSTPONABLE per user
  mandate. Pillar A hard-LOCKED.
- **Q2 (PTY approach) = Fix B Option B-W3 hybrid**: POSIX
  `pty.openpty()` per worker spawn + Windows `subprocess.PIPE` +
  `SBTDD_AUTO_PARALLEL_WORKER=1` env var + `_run_verification`
  worker-mode bypass.
- **Q3 (INV stance) = a**: strict no-INV-0 stance — preserve 8-cycle
  Checkpoint 2 streak goal + re-establish pre-merge Loop 2 streak
  from 1 cycle (broken in v1.0.6 due to chicken-and-egg).

Decisiones de brainstorming refinement 2026-05-09 (Q1'-Q5'):

- **Q1' (subagent partition) = a**: single subagent sequential
  through entire cycle (A1→A2→A3 → B5→B4→B3 → C polish).
  **Forced by chicken-and-egg**: cannot use `--parallel` for Pillar A
  own-cycle until Pillar A actually ships + is validated. Wall-time
  ~2-3 days. Zero chicken-and-egg risk during impl. v1.0.6 cycle
  empirically validated single-sequential-subagent fallback works
  reliably (took ~5h sequential auto + manual completion to ship);
  v1.0.7 inherits same pattern.
- **Q2' (Windows hybrid scope) = b**: promote C3 (worker env runtime
  guard) INTO Pillar A A2 as defense-in-depth. A2 ships BOTH
  `_run_verification` worker-mode bypass AND `invoke_skill` runtime
  guard checking `SBTDD_AUTO_PARALLEL_WORKER=1` + skill in
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` → raise worker-specific error.
  Closes Cas v1.0.6 iter-2 WARNING ("F-A2 worker headless audit is
  grep-snapshot, not runtime guard"). ~5-10 LOC additional.
- **Q3' (Pillar B subset prioritization) = b**: B5 → B4 → B3 order
  (smallest fix first). B5 (drift detector regex) is single
  surgical change + unblocks `make verify` clean state for the rest
  of the cycle. B4 (spec_review_dispatch file-reference) second
  because operational but not HARD blocker (operator can workaround).
  B3 (atomic_write retry) third because defensive flake-handling.
- **Q4' (Pillar C cherry-pick scope) = a**: ship all 5 items per
  baseline (C1+C5+C6+C7+C-X-K3-Removal). Total impl burden minimal
  (~30-60 min); zero risk; clears polish backlog efficiently.
  G2 ladder defers C items first if needed → low-cost-of-failure.
- **Q5' (MAGI Checkpoint 2 budget + G2 ladder pre-stage) = a**:
  default ladder per spec-base baseline. iter trigger → defer Pillar C
  polish first (5 items, low value-per-item) → defer Pillar B subset
  second (in reverse order: B3 first, then B4, then B5) → only
  Pillar A A1+A2+A3 hard-LOCKED. Symmetric to v1.0.5+v1.0.6
  empirically validated ladder pattern.

**Hybrid methodology continued**: brainstorming + writing-plans
in-session via Skill tool (NO `claude -p` subprocess —
chicken-and-egg until Pillar A lands + v1.0.8 own-cycle validates).
Opcion A manual `run_magi.py` for Checkpoint 2 + Loop 2 dispatch
per v1.0.2..v1.0.6 precedent.

**Criterio de exito v1.0.7**:

- Tests baseline 1271 + 1 skipped preservados + ~10-15 nuevos =
  ~1281-1290 final.
- `make verify` runtime <= 200s soft / 220s hard (acknowledges
  v1.0.6 baseline 185s + ~10-15s incremental).
- Coverage threshold mantenido en 88% (v1.0.6 measured 89.82%;
  v1.0.7 must not regress below).
- **`auto --parallel` empirical end-to-end validation**
  (NON-NEGOTIABLE): synthetic 2-track plan with 4 disjoint tasks
  completes via `auto --parallel` on Windows (mandatory; dev env)
  AND POSIX (deferred to CI or v1.0.8 if no POSIX dev env). NO
  subprocess hang.
- **`/sbtdd pre-merge` end-to-end** post Pillar A ship: re-establish
  pre-merge Loop 2 no-override streak from 1 cycle.
- **G1 binding HARD respetado**: cap=3 HARD para Checkpoint 2 sin
  INV-0. **8-cycle Checkpoint 2 no-override streak goal**.
- **Pre-merge Loop 2 streak re-establish**: clean GO_WITH_CAVEATS
  full no-degraded WITHOUT INV-0 override.

---

## 2. Items LOCKED

### 2.1 Item A1 — POSIX PTY allocation (Pillar A PRIMARY HARD-LOCKED, Track Alpha)

**Track**: Single subagent sequential (Q1'=a). A1 first; A2 second; A3
third within Pillar A.

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
  (`_dispatch_tracks_concurrent` worker spawn helper)
- Modify: `skills/sbtdd/scripts/subprocess_utils.py`
  (new `_spawn_worker_with_pty()` helper)
- Extend: `tests/test_auto_cmd.py` + `tests/test_parallel_dispatcher.py`
  (new test class for PTY allocation)

**Empirical context (v1.0.6 ship reconfirmation)**:

v1.0.6 own-cycle `auto --parallel` dogfood (F-A2 Activity) hit
chicken-and-egg subprocess hang on `close-phase
/verification-before-completion`. Workers spawned via
`subprocess.Popen` with `stdin=PIPE` have no TTY → skill subprocess
inherits non-TTY stdin → waits for interactive prompt that never
arrives. Worker meta-cognition explicitly identified the cause
("This matches the v1.0.6 Pillar A subprocess hang bug — it's
exactly what J-1+J-2+J-3 are designed to detect").

v1.0.6 J-1+J-2+J-3 added FAIL-FAST detection. v1.0.7 A1 makes
`--parallel` ACTUALLY WORK on POSIX by giving workers a real TTY.

**Implementation (POSIX)**:

```python
# subprocess_utils.py (new module-level helper)
import pty
import os
import sys

def _spawn_worker_with_pty(argv: list[str], env: dict[str, str]) -> "subprocess.Popen[bytes]":
    """v1.0.7 A1 POSIX: allocate pseudo-TTY for worker subprocess.

    Workers spawned via this helper inherit the slave end as
    stdin/stdout/stderr; orchestrator holds master end. Skill
    subprocess chain (close-phase → /verification-before-completion)
    inherits TTY from worker → interactive prompts work → no hang.

    POSIX-only. Windows callers should use Option B-W3 hybrid path
    (subprocess.PIPE + SBTDD_AUTO_PARALLEL_WORKER env + _run_verification
    bypass per A2).

    Returns:
        subprocess.Popen instance with `_pty_master_fd` attribute set
        for orchestrator cleanup post-completion.
    """
    if sys.platform == "win32":
        raise RuntimeError(
            "_spawn_worker_with_pty is POSIX-only; Windows uses "
            "Option B-W3 hybrid (see auto_cmd._dispatch_tracks_concurrent)"
        )
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen(
        argv,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        close_fds=True,
    )
    os.close(slave_fd)  # parent only needs master
    proc._pty_master_fd = master_fd  # type: ignore[attr-defined]
    return proc
```

**Cleanup**: post-worker-completion, `os.close(proc._pty_master_fd)` to
free the master end. Orchestrator drains buffered output before close
(prevents EIO on subsequent reads).

### 2.2 Item A2 — Windows hybrid Option B-W3 + worker env runtime guard (Pillar A PRIMARY HARD-LOCKED, Q2'=b promotion)

**Track**: Single subagent sequential (after A1).

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
  (`_dispatch_tracks_concurrent` Windows branch + worker env var)
- Modify: `skills/sbtdd/scripts/close_phase_cmd.py`
  (`_run_verification` worker mode bypass)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (Q2'=b promotion: `invoke_skill` runtime guard for worker context)
- Extend: `tests/test_close_phase_cmd.py` +
  `tests/test_superpowers_dispatch.py`

**Implementation outline**:

```python
# auto_cmd._dispatch_tracks_concurrent (cross-platform branch)
import sys
def _spawn_worker(argv, env):
    """v1.0.7 A2: cross-platform worker spawn dispatcher.

    POSIX → real PTY allocation (A1).
    Windows → subprocess.PIPE + SBTDD_AUTO_PARALLEL_WORKER env var.
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
    else:
        return subprocess_utils._spawn_worker_with_pty(argv, env_with_marker)
```

```python
# close_phase_cmd._run_verification (worker bypass)
import os
def _run_verification(root: Path) -> None:
    """v1.0.7 A2: worker-mode bypass.

    When SBTDD_AUTO_PARALLEL_WORKER=1 set (parent-injected env),
    bypass interactive `/verification-before-completion` skill and
    run `make verify` shell command directly. Deterministic; no
    interactive prompt; no TTY required. ValidationError raised on
    non-zero exit (equivalent to skill failure semantics).
    """
    if os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1":
        result = subprocess.run(
            ["make", "verify"], cwd=str(root), check=False
        )
        if result.returncode != 0:
            raise ValidationError(
                f"v1.0.7 A2 worker-mode verify failed: rc={result.returncode}"
            )
        return
    # Orchestrator/sequential mode: existing v1.0.5+ skill dispatch
    superpowers_dispatch.verification_before_completion(cwd=str(root))
```

```python
# superpowers_dispatch.invoke_skill (Q2'=b promotion: runtime guard)
def invoke_skill(skill_name: str, *, allow_interactive_skill: bool = False, ...):
    """v1.0.4 Items A+B subprocess gate + v1.0.6 J-3 headless detection +
    v1.0.7 A2 (Q2'=b promotion) worker-context runtime guard.
    """
    if skill_name in _SUBPROCESS_INCOMPATIBLE_SKILLS:
        # v1.0.7 A2 (Q2'=b promotion): defense-in-depth runtime guard.
        # Workers under auto --parallel never reach interactive skills
        # in normal code paths, but transitive imports could regress
        # this contract. Loud-fast catch surfaces drift earlier.
        if os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1":
            raise PreconditionError(
                f"Worker subprocess attempted to dispatch interactive "
                f"skill {skill_name!r}; this should never happen in "
                f"the auto --parallel worker code path. Bug. "
                f"Either: (a) the worker code path was extended to call "
                f"the skill — refactor to use shell command directly per "
                f"v1.0.7 A2 _run_verification pattern, OR (b) the parent "
                f"set SBTDD_AUTO_PARALLEL_WORKER=1 incorrectly."
            )
        # v1.0.4 + v1.0.6 existing membership gate + headless guard
        # (preserved unchanged below)
        if not allow_interactive_skill:
            raise PreconditionError(_build_recovery_message(skill_name))
        if subprocess_utils.is_headless_context():
            raise PreconditionError(
                f"Cannot dispatch interactive skill {skill_name!r} via "
                f"`claude -p` subprocess: context is headless. "
                f"Recovery: {_build_recovery_message(skill_name)}"
            )
    # ... existing subprocess dispatch ...
```

### 2.3 Item A3 — F-A2 dogfood empirical end-to-end validation (Pillar A PRIMARY)

**Track**: orchestrator (post Pillar A A1+A2 ship).

**Activities**:

v1.0.7 own-cycle MUST exercise `auto --parallel` end-to-end on
Windows (mandatory; dev env). Synthetic 2-track plan with 4 disjoint
tasks (separate test fixture, NOT v1.0.7 own-cycle plan) dispatched
via `auto --parallel`. Workers complete TDD cycle + close-phase +
close-task. Parent post-batch merge produces final state with all
tasks `[x]`. NO subprocess hang.

POSIX validation deferred to CI or v1.0.8 if no POSIX dev env
available.

**Acceptance**: integration test `tests/test_auto_parallel_e2e.py`
(new) exercises full `auto --parallel` flow end-to-end on Windows
with synthetic plan fixture + asserts:
- All workers complete (no `ConcurrentDispatchError`).
- `.claude/auto-run.json` contains start_time + per-worker records (I-1).
- Plan checkboxes all `[x]` post-merge (I-2).
- State file `current_phase: "done"` post-completion.
- No subprocess hangs > 600s timeout.

### 2.4 Item B5 — Drift detector line-anchored `[ ]` regex (Pillar B, Q3'=b first)

**Track**: Single subagent sequential (after A3, BEFORE B4 per Q3'=b).

**Archivos**:
- Modify: `skills/sbtdd/scripts/drift.py` (line-anchored regex)
- Extend: `tests/test_drift.py` (regression test for code-block
  fixtures)

**Empirical context**:

v1.0.6 post-cycle drift detector counted 22 `[ ]` occurrences inside
Python test fixture string literals (e.g., `"- [ ] Step 1\n"`) as
"open task checkboxes" → false-positive `Drift: detected: state=done,
HEAD=chore:, plan=[ ] (state is done but plan still has open tasks
[ ])`. Caused
`tests/test_drift.py::test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs`
failure even when all task sections were fully `[x]`-flipped.

Same pattern as v1.0.6 K-1 fix for `_section_has_flipped`. Apply
line-anchored multiline regex `^[ \t]*- \[ \]` to drift detector's
plan-state check.

### 2.5 Item B4 — `spec_review_dispatch` file-reference pattern (Pillar B, Q3'=b second)

**Track**: Single subagent sequential (after B5).

**Archivos**:
- Modify: `skills/sbtdd/scripts/spec_review_dispatch.py`
  (write prompt to file + pass `@<filepath>` reference in argv)
- Extend: `tests/test_spec_review_dispatch.py` (file-reference pattern test)

**Empirical context (v1.0.6 own-cycle T6+T7)**:

`spec_review_dispatch.dispatch_spec_reviewer` invokes `claude -p
<large-prompt>` subprocess where `<large-prompt>` is the full
reviewer prompt with task text + diff content embedded. Large diffs
(e.g., T6 K-4 + T7 K-5 cumulative) exceed Windows cmdline limit
(~32K chars per Windows API).

v1.0.6 hit `FileNotFoundError: [WinError 206] The filename or
extension is too long` during T6 close-task spec-reviewer dispatch.
Same pattern as v1.0.3 cross-check Item B fix.

### 2.6 Item B3 — `auto_cmd._atomic_write_json` Windows PermissionError catch (Pillar B, Q3'=b third)

**Track**: Single subagent sequential (after B4).

**Archivos**:
- Modify: `skills/sbtdd/scripts/state_file.py` (where
  `atomic_write_json` is consolidated per v1.0.5 K-2 DRY)
- Extend: `tests/test_state_file.py` (Windows PermissionError retry test)

**Empirical context**:

v1.0.6 hit `PermissionError: [WinError 5] Access is denied:
'...auto-run.json.q6wjytm7.tmp' -> '...auto-run.json'` once
mid-cycle. Cause: AV scanner OR concurrent writer holding file.

### 2.7 Items C1+C5+C6+C7+C-X-K3-Removal — Pillar C polish (Q4'=a all 5)

Per memory `project_v107_locked_backlog.md` Pillar C details:

- **C1**: 1-line comment in K-4 helper documenting single-level
  subparser walk limitation.
- **C5**: extend K-3 deprecation marker comment with monkeypatch
  footgun warning (will be IRRELEVANT post C-X-K3-Removal removes
  the alias; commit C5 BEFORE C-X-K3-Removal so the comment is
  actually present at one point, then C-X-K3-Removal removes both
  alias + comment).
- **C6**: add docstring note to
  `_validate_forwardable_flags_against_argparse` re: importlib.reload
  interaction.
- **C7**: document ship-time methodology-activity findings →
  v1.0.X+1 LOCKED procedure in `skills/sbtdd/SKILL.md`.
- **C-X-K3-Removal**: remove `_preflight_triplet_check = _preflight`
  alias per Q3'=a decision in v1.0.6 (1-cycle deprecation window
  expires in v1.0.7). Update test references.

**Within-Pillar-C ordering**: C5 → C-X-K3-Removal pair (C5 adds
warning comment, C-X-K3-Removal removes alias + comment; C5 is
quasi-vestigial but documented as transitional). C1 + C6 + C7
independent; can run in any order.

### 2.8 v1.0.7 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B + Pillar C ship).

**Activities**:

1. **A3 `auto --parallel` empirical validation** (NON-NEGOTIABLE) —
   synthetic 2-track plan + 4 disjoint tasks, end-to-end on Windows.
2. **B4 spec-reviewer file-reference dogfood**: own-cycle close-task
   should NOT hit `WinError 206` even with large cumulative diffs.
3. **B5 drift detector regression dogfood**: post-cycle `make verify`
   should pass `test_v104_plan_has_no_h3_task_headers...` test.
4. **`/sbtdd pre-merge` end-to-end** (post Pillar A ship): re-establish
   pre-merge Loop 2 no-override streak from 1 cycle.

---

## 3. Cross-module contracts

v1.0.7 introduces:

- **Item A1**: NEW `subprocess_utils._spawn_worker_with_pty(argv, env)`
  POSIX-only helper allocating `pty.openpty()` per worker.
- **Item A2**: NEW `auto_cmd._spawn_worker(argv, env)` cross-platform
  dispatcher (POSIX → A1; Windows → `subprocess.PIPE` +
  `SBTDD_AUTO_PARALLEL_WORKER=1` env). NEW worker-mode bypass in
  `close_phase_cmd._run_verification`. NEW worker-context runtime
  guard in `superpowers_dispatch.invoke_skill` (Q2'=b promotion).
- **Item A3**: NEW integration test `tests/test_auto_parallel_e2e.py`
  exercising full `auto --parallel` flow on Windows.
- **Item B5**: `drift._plan_all_tasks_complete` (or analogous helper)
  uses line-anchored multiline regex `^[ \t]*- \[ \]` for plan-state
  check.
- **Item B4**: `spec_review_dispatch.dispatch_spec_reviewer` writes
  prompt to project-relative
  `<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md` + passes
  `@<filepath>` reference in argv. `try/finally` cleanup.
- **Item B3**: `state_file.atomic_write_json` wraps
  `os.replace(tmp, dst)` in retry-with-backoff (3 attempts ×
  100ms × attempt-number).
- **Item C-X-K3-Removal**: removes `_preflight_triplet_check =
  _preflight` 1-cycle alias from `close_task_cmd.py`. Updates test
  monkeypatch targets.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` /
  `SBTDDError` hierarchy unchanged.
- INV-37 composite-signature output validation tripwire unchanged.
- `state_file.SessionState` schema unchanged (no migration).
- `partition_by_tracks` (v1.0.4 Path 3) unchanged.
- v1.0.4 Items A+B membership-based subprocess gate
  (`_SUBPROCESS_INCOMPATIBLE_SKILLS` + `_build_recovery_message`)
  preserved + EXTENDED with v1.0.7 A2 Q2'=b worker-context runtime
  guard.
- v1.0.5 per-worker sidecar (I-1) + scratch (I-2) + flag forwarding
  (I-3) patterns unchanged.
- v1.0.6 J-1+J-2+J-3 headless detection helper +
  `superpowers_dispatch.invoke_skill` headless guard preserved.

---

## 4. Escenarios BDD

### 4.1 Item A1 — POSIX PTY allocation

**Escenario A1-1: POSIX worker spawn allocates PTY**

> **Given** Operator on POSIX (`sys.platform != "win32"`).
> **When** `_dispatch_tracks_concurrent` calls
> `subprocess_utils._spawn_worker_with_pty(argv, env)` for a track.
> **Then** Worker subprocess has stdin/stdout/stderr connected to
> PTY slave (returned by `pty.openpty()`); orchestrator holds master
> end via `proc._pty_master_fd`. Worker subprocess can detect TTY
> via `sys.stdin.isatty()` returning True.

**Escenario A1-2: Windows worker spawn raises if PTY helper called**

> **Given** Operator on Windows (`sys.platform == "win32"`).
> **When** `subprocess_utils._spawn_worker_with_pty(argv, env)` invoked
> directly (e.g., test harness misuse).
> **Then** Raises `RuntimeError` with message naming Option B-W3
> hybrid path. Defensive guard prevents accidental misuse.

**Escenario A1-3: Master fd cleanup post-worker-completion**

> **Given** Worker subprocess completed; orchestrator collected exit code.
> **When** Orchestrator calls cleanup helper.
> **Then** `os.close(proc._pty_master_fd)` invoked; master fd freed.
> Subsequent buffered-output reads (if any) drained before close.
> No file descriptor leak across multi-worker dispatch.

**Escenario A1-4: Worker close-phase /verification-before-completion succeeds with PTY**

> **Given** POSIX worker spawned with PTY allocation. Worker calls
> `close-phase` mid-task → `superpowers_dispatch.verification_before_completion`
> → `invoke_skill("verification-before-completion")` → `claude -p`
> subprocess.
> **When** Skill subprocess inherits stdin from worker (PTY).
> **Then** `/verification-before-completion` skill detects TTY +
> proceeds with interactive prompts that complete normally.
> No 600s+ hang.

### 4.2 Item A2 — Windows hybrid + worker runtime guard

**Escenario A2-1: Windows worker spawn uses subprocess.PIPE + env marker**

> **Given** Operator on Windows.
> **When** `_dispatch_tracks_concurrent` calls `_spawn_worker(argv, env)`.
> **Then** Worker spawned via `subprocess.Popen` with
> `stdin=subprocess.PIPE` AND env contains
> `SBTDD_AUTO_PARALLEL_WORKER=1`. No PTY allocation attempted
> (Windows doesn't support).

**Escenario A2-2: Worker close-phase bypasses skill via SBTDD_AUTO_PARALLEL_WORKER**

> **Given** Worker subprocess on any platform with
> `SBTDD_AUTO_PARALLEL_WORKER=1` set in env.
> **When** Worker calls `close_phase_cmd._run_verification(root)`.
> **Then** `_run_verification` checks env var → True → bypasses
> `superpowers_dispatch.verification_before_completion()` skill
> dispatch → runs `subprocess.run(["make", "verify"], cwd=root,
> check=False)` directly. Deterministic verify result; no
> interactive prompt.

**Escenario A2-3: Worker close-phase shell verify failure raises ValidationError**

> **Given** Worker subprocess calls `_run_verification(root)` in
> worker mode; `make verify` returns non-zero.
> **When** `subprocess.run` returncode != 0.
> **Then** `ValidationError` raised with rc info, equivalent to
> existing skill failure semantics. Worker subprocess exits with
> error code; orchestrator collects + reports.

**Escenario A2-4: Orchestrator/sequential mode preserves skill dispatch**

> **Given** Orchestrator (or sequential `auto`) calls
> `_run_verification(root)` WITHOUT `SBTDD_AUTO_PARALLEL_WORKER` env
> set.
> **When** Worker mode check returns False.
> **Then** Existing `superpowers_dispatch.verification_before_completion()`
> skill dispatch path executes (v1.0.5+ behavior preserved).
> Operator inherits TTY → interactive prompts work. INV-16
> evidence-before-assertions semantic preserved.

**Escenario A2-5 (Q2'=b): Worker context invoke_skill runtime guard fires for incompatible skill**

> **Given** Worker subprocess with `SBTDD_AUTO_PARALLEL_WORKER=1`
> set + skill in `_SUBPROCESS_INCOMPATIBLE_SKILLS` (e.g.,
> `/receiving-code-review`).
> **When** Worker code path invokes `superpowers_dispatch.invoke_skill(
> "receiving-code-review", ..., allow_interactive_skill=True)`.
> **Then** Runtime guard fires: `PreconditionError` raised with
> message naming worker-context-bug nature ("Worker subprocess
> attempted to dispatch interactive skill X; this should never
> happen in the auto --parallel worker code path. Bug.").
> Defense-in-depth catches transitive-import drift.

**Escenario A2-6: Orchestrator invoke_skill unaffected by worker guard**

> **Given** Orchestrator (no worker env var) invokes
> `superpowers_dispatch.invoke_skill("receiving-code-review", ...,
> allow_interactive_skill=True)`.
> **When** v1.0.7 A2 Q2'=b runtime guard checks env var → False.
> **Then** Worker guard short-circuits + falls through to existing
> v1.0.4 + v1.0.6 membership/headless gates. No worker-bug error.

### 4.3 Item A3 — F-A2 empirical validation

**Escenario A3-1: Synthetic 2-track plan dispatches via auto --parallel end-to-end on Windows**

> **Given** Synthetic 2-track plan (4 disjoint tasks; test fixture).
> **When** Operator on Windows runs `auto --parallel` against fixture.
> **Then** All workers complete within 600s timeout (no
> `ConcurrentDispatchError`); `.claude/auto-run.json` contains
> start_time + per-worker completion records (validates v1.0.5 I-1);
> plan checkboxes all `[x]` post-merge (validates I-2); state file
> `current_phase: "done"` post-completion.

**Escenario A3-2: --parallel empirically validates --parallel chicken-and-egg closure**

> **Given** Same scenario as A3-1, but check the failure mode:
> WITHOUT v1.0.7 Pillar A (A1+A2), workers would hang on
> `close-phase /verification-before-completion`.
> **When** v1.0.7 Pillar A (A1+A2) shipped.
> **Then** Workers complete close-phase within ~3 min each (typical
> `make verify` runtime); no hang; no SBTDD_AUTO_PARALLEL_WORKER
> related errors. Q1'=a single-sequential cycle pattern can be
> retired in favor of `--parallel` for v1.0.8+ cycles.

### 4.4 Item B5 — Drift detector line-anchored regex

**Escenario B5-1: Code-block `[ ]` fixtures don't false-positive drift**

> **Given** `planning/claude-plan-tdd.md` with all task sections
> fully `[x]`-flipped, but containing 22+ `[ ]` occurrences inside
> Python test fixture string literals (code blocks, e.g.,
> `"- [ ] Step 1\n"`).
> **When** `drift._plan_all_tasks_complete` (or analogous helper)
> called.
> **Then** Returns True (all complete). Pre-fix unanchored substring
> check returned False (false-positive open task). Post-fix
> line-anchored multiline regex `^[ \t]*- \[ \]` only matches
> line-start checkboxes; ignores code-block fixtures.

**Escenario B5-2: Mid-cycle plan with real open `[ ]` correctly detects incomplete**

> **Given** Plan with task section having actual unchecked step
> `- [ ] Step 1` at line start (real open task during impl).
> **When** Drift check called.
> **Then** Returns False (legitimate open task). v1.0.6 normal
> mid-cycle drift detection preserved.

**Escenario B5-3: test_v104 regression passes**

> **Given** v1.0.6+ post-cycle plan state with all task sections
> `[x]` + code-block `[ ]` fixtures present.
> **When** `tests/test_drift.py::test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs`
> runs.
> **Then** Test passes (currently false-positive failure due to
> drift detector regex picking up code-block `[ ]`).

### 4.5 Item B4 — spec_review_dispatch file-reference

**Escenario B4-1: Reviewer prompt written to project-relative tempfile**

> **Given** `spec_review_dispatch.dispatch_spec_reviewer` invoked
> with task_id + plan_path + repo_root + large reviewer prompt.
> **When** Helper builds reviewer prompt + writes to file.
> **Then** Prompt written to
> `<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md`.
> Directory created if missing. Filename uses 16-char uuid hex slice
> (collision-safe per cycle).

**Escenario B4-2: Subprocess argv uses @<filepath> reference**

> **Given** Prompt file written per B4-1.
> **When** Helper builds subprocess argv.
> **Then** argv contains `["claude", "-p", f"@{prompt_path}", ...]`
> with `@`-prefix file reference (claude CLI convention).
> Inline prompt content NOT in argv → cmdline length bounded by
> filepath length (~100 chars vs ~32K chars unbounded).
> WinError 206 cannot fire from prompt content.

**Escenario B4-3: try/finally cleans up tempfile post-dispatch**

> **Given** Subprocess dispatch completes (success OR failure).
> **When** `dispatch_spec_reviewer` flow reaches `finally:` block.
> **Then** `prompt_path.unlink(missing_ok=True)` invoked. Tempfile
> removed. `.claude/spec-reviews/.tmp/` directory may accumulate
> orphans only if process killed mid-dispatch (acceptable; cleaned
> by next invocation OR session end).

**Escenario B4-4: Large diff no longer triggers WinError 206**

> **Given** v1.0.7 own-cycle close-task on T6+T7-equivalent
> mid-cycle moment with large cumulative diff.
> **When** `dispatch_spec_reviewer` invoked with prompt > 32K chars.
> **Then** Subprocess succeeds (file-reference path); no
> `FileNotFoundError: [WinError 206]`.

### 4.6 Item B3 — atomic_write_json Windows PermissionError catch

**Escenario B3-1: PermissionError on os.replace triggers retry-with-backoff**

> **Given** `state_file.atomic_write_json(path, data)` invoked.
> AV scanner OR concurrent writer holds destination file briefly.
> **When** `os.replace(tmp, path)` raises `PermissionError` on first
> attempt.
> **Then** Helper catches PermissionError → sleeps `0.1s` (attempt 1
> backoff) → retries. Up to 3 attempts × `0.1s × attempt-number`
> backoff (cumulative ~0.6s max).

**Escenario B3-2: Retry succeeds when lock releases**

> **Given** AV scanner releases destination file after ~150ms.
> **When** `atomic_write_json` retry attempt 2 fires after 100ms
> backoff + retries os.replace.
> **Then** os.replace succeeds; no exception raised. Cycle continues
> normally.

**Escenario B3-3: Final retry exhaustion raises PermissionError**

> **Given** Persistent file lock (e.g., AV scanner stuck OR
> concurrent writer never releases).
> **When** Retry attempt 3 fails.
> **Then** PermissionError re-raised with original args. Operator
> sees real error; can investigate AV/process holding file.

### 4.7 Items C1+C5+C6+C7+C-X-K3-Removal — Polish

**Escenario C1: K-4 helper docstring documents single-level subparser walk**

> **Given** `auto_cmd._validate_forwardable_flags_against_argparse`
> source post-v1.0.7.
> **When** Reader inspects helper code.
> **Then** Inline comment present: "single-level subparser walk;
> deeper nesting not supported. If plugin gains deeply nested
> subparsers, extend recursive walk." Documentation surface matches
> implementation surface.

**Escenario C5: K-3 deprecation marker comment includes monkeypatch warning**

> **Given** `close_task_cmd.py` post-C5 (BEFORE C-X-K3-Removal).
> **When** Reader inspects deprecation marker.
> **Then** Comment includes: "DEPRECATED: alias removed in v1.0.7.
> NOTE: monkeypatch.setattr('_preflight_triplet_check', ...) does
> NOT patch the canonical `_preflight`; tests must target the
> canonical name to actually patch behavior." (vestigial after
> C-X-K3-Removal but documented as transitional.)

**Escenario C6: K-4 helper docstring notes importlib.reload caveat**

> **Given** `_validate_forwardable_flags_against_argparse` docstring
> post-v1.0.7.
> **When** Reader inspects docstring.
> **Then** Note present: "Tests that monkeypatch _FORWARDABLE_FLAGS
> should call this helper directly rather than reloading auto_cmd
> to avoid import-time guard interaction." Saves future debugging
> cycle.

**Escenario C7: SKILL.md documents methodology-activity ship-time procedure**

> **Given** `skills/sbtdd/SKILL.md` post-v1.0.7.
> **When** Grep for "methodology-activity" pattern.
> **Then** Section present documenting: "Any methodology-activity
> finding (F-J9, F-J10, F-A2, F-Resume, P2) that doesn't trigger
> ship abort gets a v1.0.X+1 LOCKED entry at ship time (not
> mid-cycle). Process discipline: prevents deferral pipeline drift
> between cycles."

**Escenario C-X-K3-Removal: Alias removed; legacy name no longer callable**

> **Given** `close_task_cmd.py` post-v1.0.7.
> **When** Test invokes `close_task_cmd._preflight_triplet_check(state,
> project_root)`.
> **Then** `AttributeError` raised: "module 'close_task_cmd' has no
> attribute '_preflight_triplet_check'". 1-cycle deprecation window
> per v1.0.6 commitment expired; operator scripts that monkeypatched
> alias must migrate to canonical `_preflight` name.

---

## 5. Subagent layout + execution timeline

### 5.1 Single subagent sequential (Q1'=a forced by chicken-and-egg)

**Owner**: Single subagent dispatched from orchestrator (or operator
runs sequential `auto` in foreground for v1.0.7 own-cycle since
`auto --parallel` cannot be used until Pillar A ships + validates).

**Wall-time estimado**: ~2-3 dias.

**Within-cycle ordering** (cannot be parallelized due to chicken-and-egg):

1. **A1** (POSIX PTY allocation) — `subprocess_utils.py` +
   `auto_cmd.py` + tests. ~3-5 hours.
2. **A2** (Windows hybrid + Q2'=b worker runtime guard) —
   `auto_cmd.py` + `close_phase_cmd.py` +
   `superpowers_dispatch.py` + tests. ~5-7 hours.
3. **A3** (F-A2 empirical validation) — orchestrator activity post
   A1+A2 ship. Synthetic 2-track plan integration test. ~2-3 hours.
4. **B5** (drift detector regex) — `drift.py` + tests. ~30-60 min.
5. **B4** (spec_review_dispatch file-reference) —
   `spec_review_dispatch.py` + tests. ~2-3 hours.
6. **B3** (atomic_write retry) — `state_file.py` + tests. ~1-2 hours.
7. **C polish** (5 items) — close_task_cmd.py + auto_cmd.py +
   SKILL.md + tests. ~30-60 min total.

### 5.2 Cross-cycle implication

v1.0.7 own-cycle uses sequential `auto` (single-process, foreground)
per Q1'=a chicken-and-egg constraint. v1.0.8+ cycles can use
`auto --parallel` per A3 dogfood validation in v1.0.7.

### 5.3 Mid-cycle methodology (orchestrator)

**Activities post-A3 ship** (NON-NEGOTIABLE per spec sec.1 criterio):

1. **A3 `auto --parallel` empirical validation** on Windows
2. **B4 spec-reviewer file-reference dogfood** — own-cycle close-task
   should NOT hit WinError 206
3. **B5 drift detector regression dogfood** — `make verify` should
   pass `test_v104_plan_has_no_h3_task_headers...`
4. **`/sbtdd pre-merge` end-to-end** — re-establish pre-merge Loop 2
   no-override streak from 1 cycle (post Pillar A ship unblocks).

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (precedente cerrado v1.0.0..v1.0.6
  = 7-cycle no-override streak). NO INV-0 path. v1.0.7 goal:
  8-cycle Checkpoint 2 streak.
- Bundle scope focused (3 pillars, 11 items) — esperamos converger
  en 1-2 iters.
- **Iter-2 CRITICAL trigger**: if iter 2 still surfaces ANY
  CRITICAL finding, scope-trim immediately. Pre-staged G2 ladder
  (Q5'=a default):
  1. Defer Pillar C polish first (5 items, low value-per-item).
  2. Defer Pillar B subset second in REVERSE order: B3 first
     (lowest priority), B4 second, B5 third (highest priority).
  3. Pillar A A1+A2+A3 hard-LOCKED.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- v1.0.7 own-cycle uses sequential `auto` (foreground) — `/sbtdd
  pre-merge` Loop 1 dispatch can complete because orchestrator
  inherits TTY.

### 6.3 Loop 2 (`/magi:magi`) — strict no-INV-0 stance

- **Cap=5** per `auto_magi_max_iterations`.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding stance (Q3=a strict)**: si Loop 2 iter 3 no converge
  clean, scope-trim per spec-base sec.6.1 ladder (C polish first
  → B subset second → Pillar A hard-LOCKED).
- **NO INV-0 override** without explicit user authorization. If
  Loop 2 doesn't converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0 (per memory
  `feedback_manual_synthesis_exceptional`).
- **Goal**: re-establish pre-merge Loop 2 no-override streak from
  1 cycle (broken in v1.0.6 due to chicken-and-egg blocking
  `/sbtdd pre-merge`).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.7 own-cycle
(e.g., new regression OR pre-A1-ship attempt), el operator MUST
fall back a manual `python skills/magi/scripts/run_magi.py` direct
dispatch + manual mini-cycle commits. Document en CHANGELOG
`[1.0.7]` Process notes. Precedentes v1.0.0..v1.0.6.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.6 → 1.0.7.

### 7.2 CHANGELOG `[1.0.7]` sections

- **Added** —
  POSIX PTY allocation in worker subprocess spawn
  (`subprocess_utils._spawn_worker_with_pty`); Windows hybrid Option
  B-W3 fallback (`subprocess.PIPE` + `SBTDD_AUTO_PARALLEL_WORKER`
  env + `_run_verification` worker bypass); Worker-context runtime
  guard in `superpowers_dispatch.invoke_skill` (Q2'=b promotion);
  `spec_review_dispatch` file-reference pattern (Item B4 closes
  WinError 206); `atomic_write_json` Windows PermissionError catch
  with retry-with-backoff (Item B3).
- **Changed** —
  Drift detector regex line-anchored `^[ \t]*- \[ \]` for plan-state
  check (Item B5); 4 polish items (C1+C5+C6+C7) with documentation
  + procedure additions.
- **Removed** —
  `_preflight_triplet_check = _preflight` 1-cycle deprecation alias
  (Item C-X-K3-Removal per v1.0.6 Q3'=a commitment).
- **Process notes** — Pillar A NON-POSTPONABLE per user mandate
  2026-05-09 ("dejar parallel completamente operacional"); Q2'=b
  promotion of C3 worker env runtime guard into A2 as
  defense-in-depth; Q3'=b Pillar B ordering (B5 first, smallest fix
  unblocks make verify); Q4'=a all 5 Pillar C items shipped;
  Q5'=a default G2 ladder pre-staged; Q1'=a single subagent
  sequential forced by chicken-and-egg; A3 own-cycle dogfood
  validates `--parallel` end-to-end on Windows.
- **Deferred (rolled to v1.0.8)** — B2 worker subprocess auto-message
  hardening; C2 K-4 escape hatch test coverage; C4 NF-B test count
  rebaseline; C8 F-A2 abort criterion (b) diagnosis hint refinement;
  Pillar D items (5 v1.0.5 polish carry-forward); Edge cases E1-E3.
- **Deferred (rolled to v1.1.0)** — All v1.0.4 carry-forward
  inherited items.

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.7 docs section sobre `auto --parallel` operational
  status post Pillar A ship; PTY allocation note for POSIX vs
  Windows hybrid behavior; `SBTDD_AUTO_PARALLEL_WORKER` operator-
  facing env var documentation.
- **SKILL.md**: `### v1.0.7 notes` section documentando Pillar A
  PTY allocation + Windows hybrid + Q2'=b worker runtime guard;
  Pillar B fixes (B5 drift regex + B4 file-reference + B3 retry);
  Pillar C polish + C-X-K3-Removal alias removal; v1.0.6 K-3 1-cycle
  deprecation window expiration.
- **CLAUDE.md** (project root, gitignored): v1.0.7 release notes
  pointer.

---

## 8. Risk register v1.0.7

- **R1**. POSIX PTY allocation may have subtle stdin/stdout
  buffering issues on some POSIX variants (Linux vs macOS vs BSD).
  Mitigation: explicit drain of master fd post-worker-completion;
  integration test exercises full TDD cycle on POSIX (CI; if no
  POSIX dev env, defer empirical validation to v1.0.8).
- **R2**. Windows hybrid Option B-W3 bypass of
  `/verification-before-completion` skill loses INV-16 evidence-
  before-assertions semantic in worker context. Mitigation: `make
  verify` returncode is deterministic; failure raises
  ValidationError equivalent to skill failure. INV-16 preserved in
  orchestrator/sequential mode.
- **R3**. Q2'=b worker-context runtime guard may false-positive
  if operator manually sets `SBTDD_AUTO_PARALLEL_WORKER=1` outside
  `auto --parallel` context (unusual but possible). Mitigation:
  env var name is descriptive + operator-namespaced; documented in
  README + SKILL.md as parent-injected only.
- **R4**. v1.0.7 own-cycle dogfood requires successful Pillar A
  ship before exercising A3 on real `--parallel`. Chicken-and-egg:
  if Pillar A has bugs surfacing only at runtime, dogfood fails +
  cycle stuck. Mitigation: sequential `auto` foreground for v1.0.7
  own-cycle (Q1'=a chosen path); Pillar A runtime validation
  deferred to A3 integration test post-A2-ship.
- **R5**. Pre-merge Loop 2 streak re-establish goal may not be
  achievable if cycle surfaces fundamental architectural questions
  in Pillar A or Pillar B. Mitigation: G2 scope-trim ladder (defer
  Pillar C polish first → Pillar B subset reverse order; Pillar A
  hard-LOCKED). Q3=a strict no-INV-0 stance + escalate-to-user
  before-INV-0 discipline preserved.
- **R6**. C-X-K3-Removal may break operator scripts that
  monkeypatched `_preflight_triplet_check` alias name. Mitigation:
  1-cycle deprecation window per v1.0.6 Q3'=a commitment;
  documented in CHANGELOG `[1.0.6]` Deferred section + this CHANGELOG
  `[1.0.7]` Removed section. Operators on contract: monkeypatch
  canonical `_preflight` name only.

---

## 9. Acceptance criteria final v1.0.7

v1.0.7 ship-ready cuando:

### 9.1 Functional Items A1+A2+A3 + B5+B4+B3 + C1+C5+C6+C7+C-X-K3-Removal

- **F1**. F196-F198 (A1): POSIX `pty.openpty()` allocation +
  master fd cleanup + worker spawn integration.
- **F2**. F199-F201 (A2): Windows hybrid Option B-W3 fallback +
  `SBTDD_AUTO_PARALLEL_WORKER` env var + `_run_verification`
  worker-mode bypass + Q2'=b worker-context runtime guard in
  `invoke_skill`.
- **F3**. F202 (A3): F-A2 empirical validation passes end-to-end on
  Windows (synthetic 2-track + 4 disjoint tasks).
- **F4**. F205-F206 (B5): drift detector line-anchored regex +
  test_v104 regression pass.
- **F5**. F203-F204 (B4): spec_review_dispatch file-reference
  closes WinError 206.
- **F6**. F207 (B3): atomic_write_json Windows PermissionError
  catch + retry-with-backoff.
- **F7**. F208-F212 (C1+C5+C6+C7+C-X-K3-Removal): polish items +
  K-3 alias removal.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s
  hard.
- **NF-B**. Tests baseline 1271 + 1 skipped + ~10-15 nuevos =
  ~1281-1290 final.
- **NF-C**. Cross-platform (Windows + POSIX): A1 POSIX pty.openpty
  validated on POSIX (CI or v1.0.8 if no dev env); A2 Windows hybrid
  validated on Windows (mandatory dev env); B5 line-anchored regex
  + B4 file-reference + B3 retry all cross-platform.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados.

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**.
  8-cycle Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (re-establish streak from 1 cycle post v1.0.6 break).
  If unable to converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0.
- **P3**. CHANGELOG `[1.0.7]` entry written con secciones Added /
  Changed / Removed / Process notes + Pillar A A1+A2+A3 + Pillar B
  B5+B4+B3 + Pillar C polish + dogfood findings.
- **P4**. Version bump 1.0.6 -> 1.0.7 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.7` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. v1.0.7 own-cycle dogfood: A3 `auto --parallel` end-to-end
  on Windows; B4 spec-reviewer file-reference closes WinError 206
  even with large diffs; B5 drift detector test_v104 regression
  passes.
- **P8**. `/sbtdd pre-merge` validated end-to-end post Pillar A ship.

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.7 ship + items + dogfood
  observations).
- **D3**. Documented:
  - Pillar A PTY allocation in `auto_cmd.py` + `subprocess_utils.py`
    docstrings + README operational notes + SKILL.md v1.0.7 notes.
  - `SBTDD_AUTO_PARALLEL_WORKER` env var in operator-facing docs.
  - C7 ship-time methodology-activity procedure in SKILL.md.
  - K-3 alias removal in CHANGELOG `[1.0.7]` Removed section.

---

## 9.5 Inherited invariants (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording, INV-37 composite-
signature output validation tripwire, Item C v1.0.2 spec_lint gate,
Q4 v1.0.2 coverage threshold protocol, v1.0.3 cross-check Windows
long-filename fix, v1.0.4 Items A+B membership-based subprocess gate,
v1.0.4 Path 3 `--parallel` architecture, v1.0.5 per-worker sidecar +
scratch + flag forwarding, v1.0.6 J-1+J-2+J-3 headless detection +
J-3 invoke_skill guard — all preserved unchanged. v1.0.7 EXTENDS v1.0.6
J-3 with v1.0.7 A2 Q2'=b worker-context runtime guard. v1.0.7 EXTENDS
v1.0.4 Path 3 `--parallel` with v1.0.7 A1 POSIX PTY + A2 Windows hybrid
spawn helpers.

---

## 10. Referencias

- Spec base v1.0.7: `sbtdd/spec-behavior-base.md` (committed
  `bb16de3` on `feature/v1.0.7-bundle`).
- Contrato autoritativo
  v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5
  +v1.0.6 frozen: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.6 ship record: tag `v1.0.6` (commit `5ee8be6`); merge
  `5ee8be6` on `main`; branch `feature/v1.0.7-bundle` branched
  off main HEAD.
- v1.0.7 LOCKED memories:
  - `project_v107_pty_workers_locked.md` (Pillar A primary detail)
  - `project_v107_locked_backlog.md` (full 17-item backlog
    consolidation)
  - `project_v106_shipped.md` (full v1.0.6 ship record + empirical
    findings driving v1.0.7 Pillar B)
- v1.0.8 deferred backlog: B2 + C2 + C3 (now folded into v1.0.7 A2
  per Q2'=b promotion; C3 entry retired) + C4 + C8 + Pillar D items
  + Edge cases.
- v1.1.0 deferred backlog: all v1.0.4 carry-forward inherited
  items.
- Brainstorming refinement decisions (2026-05-09):
  - Q1' = a single subagent sequential (forced by chicken-and-egg
    until Pillar A lands + v1.0.8 own-cycle validates)
  - Q2' = b promote C3 worker env runtime guard INTO Pillar A A2
    (defense-in-depth)
  - Q3' = b Pillar B ordering B5 → B4 → B3 (smallest fix first
    unblocks make verify)
  - Q4' = a ship all 5 Pillar C items per baseline
  - Q5' = a default G2 ladder per spec-base baseline
- Branch: trabajo en `feature/v1.0.7-bundle` (branched off `main`
  HEAD `5ee8be6`).
