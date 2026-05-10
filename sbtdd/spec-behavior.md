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

## Iter-3 carry-forward — Checkpoint 2 iter 2 triage applied 2026-05-09

> Per CLAUDE.local.md §6 v1.0.0+ carry-forward block format. Verdict
> iter 2: GO_WITH_CAVEATS (3-0) full no-degraded — Mel APPROVE 82% +
> Bal APPROVE 82% + Cas CONDITIONAL 74%. 1 CRITICAL (cas) + 9 WARNING
> + 9 INFO. Mel + Bal treat the sidecar issue as WARNING; Cas's strict
> G1 reading triggers G2. **Resolution**: apply ALL of Cas's 7 inline
> fixes (which subsume Mel + Bal WARNINGs); per Cas item (5) "T7
> commit-level collapse stays", T7 STAYS in scope (no defer). Iter 3
> expects clean convergence at 0 CRITICAL preserving the 8-cycle
> Checkpoint 2 no-override streak.

| Iter | Severity | Title (verbatim from iter 2) | Decision | Rationale |
|------|----------|-------------------------------|----------|-----------|
| 2 | critical | Sidecar PID collision silently corrupts INV-16 evidence _(cas)_ | keep | Resolved sec.2.2 + sec.4.2: sidecar filename now `<pid>-<monotonic_ns>-<uuid8>-verify.json` + parent post-batch merge LOUD-FAILS via `ConcurrentDispatchError` on missing sidecar (worker spawned but no sidecar persisted = bug). Updated A2-7 escenario + new sec.5.1 plan T2 implementation outline. |
| 2 | warning | PID uniqueness in sidecar path under run-reuse _(mel)_ | keep | Same root as C1 above; addressed by monotonic_ns + uuid8 suffix. |
| 2 | warning | T7 4-doc-smoke-tests in single Red commit _(mel+bal+cas)_ | keep | Resolved plan T7 Red phase: 4 test classes preserved with discriminating function names (`test_c1_*`, `test_c5_*`, `test_c6_*`, `test_c7_*`) so bisect can pinpoint regression to a specific doc surface within a single commit. CHANGELOG Process notes will document the collapse trade-off (per Mel recommendation). |
| 2 | warning | T6 → T2 ordering: prefer the swap _(bal+cas)_ | keep | Resolved plan §5.1 + plan invariants: swap T2 ↔ T6 in execution order. New order T1 → T6 → T2 → T3 → T4 → T5 → T7 → T8. T6 (atomic_write_json retry) lands BEFORE T2 (which calls it via `_persist_worker_verify_evidence`); eliminates documented PermissionError flake risk during T3 dogfood. Zero-cost swap (both file-disjoint). |
| 2 | warning | A3 fixture realism does not assert PTY path execution _(cas)_ | keep | Resolved sec.4.3 escenario A3-1: on POSIX, integration test asserts at least one sidecar entry contains evidence the worker observed a TTY (e.g., per-worker stdout fragment confirms PTY path took the v1.0.7 A1 helper, not the Windows hybrid path). NEW escenario A3-3 dedicated to POSIX PTY-path empirical assertion. |
| 2 | warning | Risk register missing R9 for sidecar collision class _(cas)_ | keep | Resolved sec.8: NEW R9 (per-worker artifact collision class) covering not just sidecars but all per-worker temp files generated under `--parallel`. Documents PID-recycle risk + collision-detection LOUD-FAIL contract. |
| 2 | info | C1 lifecycle helper EIO drain semantics _(mel)_ | n/a | Positive validation; preserved. |
| 2 | info | C4 sec.0.1 chain + sidecar evidence preserves INV-16 _(mel)_ | n/a | Positive validation; preserved. |
| 2 | info | C3 REAL fixture exercises chicken-and-egg surface _(mel)_ | n/a | Positive validation; preserved. |
| 2 | info | T6→T2 ordering trade-off acceptable _(mel)_ | n/a | Mel commendation acknowledged; chose Bal+Cas swap recommendation anyway because zero-cost. |
| 2 | info | Backward compat preserved _(mel)_ | n/a | Positive validation; preserved. |
| 2 | info | sec.0.1 chain replacement is a clear win _(bal)_ | n/a | Positive validation; preserved. |
| 2 | info | A3 fixture realism is now genuinely empirical _(bal)_ | n/a | Positive validation; preserved. |
| 2 | info | Scope-trim ladder pre-stage is good operational hygiene _(bal+cas)_ | n/a | Positive validation; G2 ladder preserved as pre-staged option for iter 3 if it surfaces fresh CRITICAL. |

**Pillar C T7 NOT deferred**: Cas item (2) suggested defer Pillar C
polish per G2 ladder, but Cas item (5) "commit-level collapse stays"
explicitly KEEPS T7 in scope — the apparent contradiction resolves to
"T7 stays + improve internal test naming". Mel + Bal endorse keeping
T7. Net: T7 stays; G2 ladder NOT invoked; 8-cycle no-override streak
goal preserved.

---

## Iter-2 carry-forward — Checkpoint 2 iter 1 triage applied 2026-05-09

> Per CLAUDE.local.md §6 v1.0.0+ carry-forward block format. Verdict
> iter 1: GO_WITH_CAVEATS (3-0) full no-degraded, but 5 CRITICAL +
> 10 WARNING + 5 INFO findings. Triage applied via INV-29
> `/receiving-code-review` discipline; resolutions inlined into spec
> sec.2.1, sec.2.2, sec.2.3, sec.2.7, sec.4.1, sec.4.2, sec.4.3,
> sec.4.7, sec.5.1, sec.7.2, sec.8 below.

| Iter | Severity | Title (verbatim from iter 1) | Decision | Rationale |
|------|----------|-------------------------------|----------|-----------|
| 1 | critical | A1 PTY lifecycle: master fd close + EIO + slave-in-parent not specified _(mel)_ | keep | Resolved sec.2.1: explicit `_close_pty_master(proc)` lifecycle helper + drain semantics + Popen-failure slave_fd leak guard added to implementation outline + escenarios A1-3 / A1-5. |
| 1 | critical | Pillar C T7..T10 empty-Refactor blocked by v1.0.5 _preflight HARD-BLOCK _(mel)_ | keep | Resolved sec.2.7 + sec.5.1: collapse C1+C5+C6+C7 into single combined task with real Refactor (cross-link K-4 helper docs + consolidate). 11 tasks -> 8 tasks. C-X-K3-Removal stays separate (real code change). |
| 1 | critical | A3 dogfood fixture doesn't exercise the chicken-and-egg failure surface _(cas)_ | keep | Resolved sec.2.3 + sec.4.3: fixture rewritten to exercise real `close-phase` -> worker `_run_verification` -> sec.0.1 chain dispatch in workers. Without this, A3 doesn't validate the fix. |
| 1 | critical | Worker-mode `make verify` bypass: Windows make dependency + INV-16 regression _(cas)_ | keep | Resolved sec.2.2 + sec.4.2: A2 replaces `["make", "verify"]` with explicit sec.0.1 chain (`pytest` / `ruff check` / `ruff format --check` / `mypy`); per-worker captured stdout/stderr persisted to sidecar for INV-16 evidence-before-assertions continuity. |
| 1 | critical | T7+T8+T9+T10 doc-only tasks fake the Red->Green->Refactor triplet _(cas)_ | keep | Same root as C2; resolution above (collapse into single multi-edit task with real diffs in each phase). |
| 1 | warning | Q2'=b worker-guard ordering risks orchestrator false-positive trip _(mel)_ | keep | Resolved sec.4.2 escenario A2-6': explicit test that orchestrator-mode (no env var) does NOT trip guard even when invoking incompatible skill via `allow_interactive_skill=True`. |
| 1 | warning | A3-2 dogfood does not exercise PTY drain under large cumulative output _(mel)_ | defer | Smoke validation in A3-1 suffices for v1.0.7 ship. Large-output drain is rare path; v1.0.8 follow-up backlog item (memory `project_v108_pty_drain_locked.md`). |
| 1 | warning | Risk register sec.8 omits EIO/SIGHUP race and guard false-positive _(mel)_ | keep | Resolved sec.8: R7 EIO/SIGHUP race + R8 worker-context guard false-positive resilience added. |
| 1 | warning | Windows worker INV-16 evidence gap (Pillar A2) _(bal)_ | keep | Same root as C4; resolution above (per-worker sidecar captured output). |
| 1 | warning | POSIX path ships unvalidated end-to-end (A3 scope) _(bal)_ | keep | Resolved sec.7.2 + sec.7.3: `--parallel` POSIX marked **experimental** in v1.0.7 docs; CHANGELOG `[1.0.7]` Process notes documents Windows-mandatory + POSIX deferred to v1.0.8 dogfood. README operational note added. |
| 1 | warning | Empty-Refactor gate interaction not verified upfront (Pillar C) _(bal)_ | keep | Same root as C2; resolution above (collapse + real Refactor diffs). |
| 1 | warning | A1-1 test does not validate `sys.stdin.isatty() == True`; spec promise unfulfilled _(cas)_ | keep | Resolved plan T1 Red phase test: `worker_isatty.py` worker writes `isatty=True` to its stdout; orchestrator reads + asserts via PTY master fd. |
| 1 | warning | T1 implementation lacks master_fd leak guard on Popen failure + omits pre-close drain _(cas)_ | keep | Resolved sec.2.1: implementation outline wraps `subprocess.Popen` in `try/except` with `os.close(slave_fd)` on failure + drain-before-close in `_close_pty_master`. |
| 1 | warning | C5 <-> C-X-K3-Removal pair both ship in v1.0.7; comment is structurally vestigial _(cas)_ | defer | Documented as transitional archaeology in plan: C5 comment lives between T7-collapsed commit and T8 (= old T11) commit. Educational value for `git log` readers preserved. |
| 1 | warning | T11 alias-removal `--variant fix` commit prefix violates CLAUDE.md sec.Git semantics _(cas)_ | keep | Resolved plan T8 (= old T11): Green commit uses `--variant fix` framing as "closes v1.0.7 C5-documented monkeypatch footgun"; documented in plan task header. |
| 1 | info | B-pillar order Q3'=b smallest-fix-first is correct _(mel)_ | n/a | Positive validation; preserved. |
| 1 | info | Q1'=a single-sequential modality is the only safe choice for v1.0.7 _(mel)_ | n/a | Positive validation; preserved. |
| 1 | info | Cross-task ordering documented but not mechanically enforced _(bal)_ | n/a | Positive triage; mechanical enforcement deferred to v1.0.8 backlog (`addBlockedBy` integration). |
| 1 | info | G2 ladder defer order well-calibrated _(bal)_ | n/a | Positive validation; preserved. |
| 1 | info | Risk register R1-R6 coverage adequate for shipped scope _(bal)_ | n/a | Positive validation; R7+R8 added per W3 above. |

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

**Cleanup (v1.0.7 iter-2 carry-forward C1 resolution)**: dedicated
lifecycle helper colocated with `_spawn_worker_with_pty`:

```python
def _close_pty_master(proc: "subprocess.Popen[bytes]") -> None:
    """v1.0.7 A1 lifecycle: drain + close master fd. Idempotent.

    Drains buffered output from the master end before close; without
    drain, subsequent reads raise EIO on POSIX. Idempotent: safe to
    call multiple times (no-op when ``_pty_master_fd`` attribute
    missing or already closed).
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
        # Worker already closed slave end; drain done.
        pass
    try:
        _os.close(master_fd)
    except OSError:
        # Already closed (idempotent).
        pass
    # Mark consumed so re-invocation is a true no-op.
    proc._pty_master_fd = None  # type: ignore[attr-defined]
```

Orchestrator MUST call `_close_pty_master(proc)` after `proc.wait()`
in `_dispatch_tracks_concurrent` post-batch cleanup (NEW production
contract; not just test cleanup). The integration test in plan T3 + the
A1 unit tests in plan T1 BOTH cover the lifecycle pattern.

**Popen-failure leak guard (v1.0.7 iter-2 carry-forward W8 resolution)**:
the `_spawn_worker_with_pty` body wraps the `subprocess.Popen` call in
`try/except`, closing both `master_fd` and `slave_fd` on failure to
prevent file descriptor leak when `Popen` raises:

```python
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
        os.close(master_fd)
        os.close(slave_fd)
        raise
    os.close(slave_fd)  # parent only needs master after success
    proc._pty_master_fd = master_fd
    return proc
```

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
import subprocess

def _run_verification(root: Path) -> None:
    """v1.0.7 A2: worker-mode bypass via explicit sec.0.1 chain.

    When SBTDD_AUTO_PARALLEL_WORKER=1 set (parent-injected env),
    bypass interactive `/verification-before-completion` skill and
    run the sec.0.1 4-tool chain directly: pytest, ruff check,
    ruff format --check, mypy. Deterministic; no interactive prompt;
    no TTY required; no make-on-Windows dependency.

    v1.0.7 iter-2 carry-forward C4 resolution: replaces earlier
    `make verify` shell-out which (a) requires `make` installed on
    Windows (cygwin/MSYS only — not always present), (b) loses INV-16
    evidence-before-assertions semantic by sending stdout/stderr to
    inherited streams. New design captures stdout/stderr per-tool +
    persists to per-worker sidecar
    (`<root>/.claude/auto-run-workers/<worker_id>-verify.json`) so
    INV-16 evidence is preserved across the parent post-batch merge.

    ValidationError raised on first non-zero exit; remaining tools NOT
    run (semantically equivalent to `make verify` early-abort).
    """
    if os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1":
        # sec.0.1 4-tool chain (matches /verification-before-completion
        # skill's discovery on Python stack).
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
                _persist_worker_verify_evidence(root, captured)
                raise ValidationError(
                    f"v1.0.7 A2 worker-mode verify failed at "
                    f"{cmd[0]!r}: rc={result.returncode}"
                )
        _persist_worker_verify_evidence(root, captured)
        return
    # Orchestrator/sequential mode: existing v1.0.5+ skill dispatch
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
    contains 3-component disambiguator to prevent silent collision:
    - ``pid``: human-readable identifier for cross-referencing with
      OS process listings.
    - ``monotonic_ns``: ``time.monotonic_ns()`` at write time —
      sub-microsecond resolution defends against same-pid re-spawn
      within the same parent batch (PID recycle on POSIX, fast worker
      churn on Windows).
    - ``uuid8``: ``uuid.uuid4().hex[:8]`` — final tiebreaker
      eliminating any residual collision risk under exotic
      monotonic-clock skew (rare but observable on virtualised hosts).

    The parent post-batch merge in ``auto_cmd._dispatch_tracks_concurrent``
    LOUD-FAILS via ``ConcurrentDispatchError`` if any spawned worker
    completed without producing a sidecar (worker spawned but no
    sidecar persisted = code-path bug, not silent data loss).
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
``auto_cmd._dispatch_tracks_concurrent`` post-batch merge MUST verify
each spawned worker produced AT LEAST ONE sidecar matching the prefix
pattern ``<worker_pid>-*-verify.json`` in ``<root>/.claude/auto-run-workers/``.
Missing sidecar (worker spawned, ran close-phase, but no evidence
file) raises ``ConcurrentDispatchError`` naming the offending pid +
listing all observed sidecars, halting the batch. This catches the
class of bugs where transient errors swallow the sidecar write before
``state_file.atomic_write_json`` completes — silently lost INV-16
evidence is unacceptable; LOUD-FAIL surfaces it during test/dogfood.

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

**Acceptance** (v1.0.7 iter-2 carry-forward C3 resolution): integration
test `tests/test_auto_parallel_e2e.py` (new) MUST exercise the
chicken-and-egg failure surface explicitly. Trivial "append text"
worker tasks DO NOT trip the chicken-and-egg; the failure mode requires
workers to actually invoke `close-phase` -> `_run_verification` ->
sec.0.1 chain dispatch.

Fixture design:
- Synthetic 2-track plan + 4 tasks, each task's TDD cycle invokes a
  REAL `python skills/sbtdd/scripts/run_sbtdd.py close-phase` from
  inside the worker subprocess (not a no-op shell command).
- Each task's "Step 2: verify" actually runs the worker
  `_run_verification` path (which on workers is the new sec.0.1 chain
  per A2). The fixture project ships a minimal `pyproject.toml` +
  `tests/test_smoke.py` so `pytest` / `ruff check` / `ruff format
  --check` / `mypy` all succeed inside the worker.
- Pre-A1+A2 baseline: WITHOUT v1.0.7 Pillar A, worker stdin=PIPE has
  no TTY -> if the worker code path attempted skill dispatch, hang.
  Post-Pillar A: workers either get PTY (POSIX) or use sec.0.1 chain
  bypass (Windows) and complete.

The integration test asserts:
- All workers complete within 600s timeout (no `ConcurrentDispatchError`,
  no subprocess hang).
- `.claude/auto-run.json` contains `start_time` + per-worker records
  (validates v1.0.5 I-1 sidecar merge).
- `.claude/auto-run-workers/<pid>-verify.json` files exist per worker
  containing the captured sec.0.1 chain stdout/stderr (validates
  v1.0.7 A2 INV-16 evidence continuity).
- Plan checkboxes all `[x]` post-merge (validates v1.0.5 I-2 scratch
  merge).
- State file `current_phase: "done"` post-completion.
- No subprocess hangs > 600s timeout (THE chicken-and-egg closure
  signal).

**Smoke vs full validation**: v1.0.7 ships smoke validation only
(synthetic 4-task fixture). PTY drain under large cumulative output
deferred to v1.0.8 per W2 triage above.

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

**v1.0.7 iter-2 carry-forward C2/C5 resolution — task collapse**: the
v1.0.5 Item D Q3-A `_preflight` HARD-BLOCK enforces canonical
Red→Green→Refactor triplet with REAL diffs in each phase. Doc-only
items C1+C5+C6+C7 each individually have no real Refactor surface
(empty-Refactor commits are blocked), and using `--skip-preflight`
audit-log per-task degrades the v1.0.5 contract.

**Resolution**: collapse C1+C5+C6+C7 into ONE combined task (new T7) with:
- Single Red phase: write all 4 doc smoke tests in one commit (one
  `test:` close).
- Single Green phase: apply all 4 doc edits in one commit (one
  `feat:` close — `feat:` justified because the cumulative diff
  introduces new documented contracts, not bug fixes).
- Single Refactor phase with REAL diff: cross-link C1 ↔ C6 (both
  touch the same K-4 helper `_validate_forwardable_flags_against_argparse`
  — the inline comment from C1 + the docstring note from C6 should
  reference each other; consolidate any duplicated wording so the
  single-level walk limitation + importlib.reload caveat read as a
  coherent helper-level documentation block, not as two disjoint
  notes added 2 commits apart).

**C-X-K3-Removal stays as separate task** (new T8) — has real code
change (alias removal + test monkeypatch target rewrites), legitimate
TDD triplet (Red: assert AttributeError on legacy name; Green: remove
alias + rewrite test refs; Refactor: final sweep + lint cleanup).

**Plan task count**: 11 tasks → 8 tasks total (T1 A1, T2 A2, T3 A3,
T4 B5, T5 B4, T6 B3, T7 collapsed Pillar C polish, T8 C-X-K3-Removal).

**Within-Pillar-C ordering** (post-collapse): T7 (combined polish)
must land BEFORE T8 (C-X-K3-Removal). T7's C5 component adds the
deprecation marker comment on the alias line; T8 removes both alias +
comment together. The C5 comment IS structurally vestigial (W9 cas
WARNING acknowledged + deferred); preserved as transitional
archaeology — for the duration between T7 commit and T8 commit, `git
log` readers see the documented footgun rationale that motivated the
removal. Educational value justifies the brief lifespan.

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

**Escenario A1-1: POSIX worker spawn allocates PTY + worker observes TTY (W7 carry-forward)**

> **Given** Operator on POSIX (`sys.platform != "win32"`).
> **When** `_dispatch_tracks_concurrent` calls
> `subprocess_utils._spawn_worker_with_pty(argv, env)` for a track,
> where ``argv`` invokes a Python subprocess that writes
> ``isatty=<sys.stdin.isatty()>`` to stdout and exits.
> **Then** Worker subprocess has stdin/stdout/stderr connected to
> PTY slave (returned by `pty.openpty()`); orchestrator holds master
> end via `proc._pty_master_fd`; orchestrator reads buffered output
> from master fd post-`proc.wait()` and asserts the literal string
> `isatty=True` is present (proves the worker observed a TTY, not
> just that the parent allocated one). The integer file descriptor
> is non-negative (`proc._pty_master_fd >= 0`) for downstream cleanup.

**Escenario A1-2: Windows worker spawn raises if PTY helper called**

> **Given** Operator on Windows (`sys.platform == "win32"`).
> **When** `subprocess_utils._spawn_worker_with_pty(argv, env)` invoked
> directly (e.g., test harness misuse).
> **Then** Raises `RuntimeError` with message naming Option B-W3
> hybrid path. Defensive guard prevents accidental misuse.

**Escenario A1-3: Master fd lifecycle helper drains then closes (C1 carry-forward)**

> **Given** Worker subprocess completed; orchestrator collected exit code.
> **When** Orchestrator calls `subprocess_utils._close_pty_master(proc)`.
> **Then** Master fd buffered output is drained via repeated
> `os.read(master_fd, 4096)` until empty (silently absorbing OSError if
> the worker closed the slave end first); then `os.close(master_fd)`
> invoked; then `proc._pty_master_fd` set to `None` for idempotency.
> Helper is safe to call multiple times — second invocation observes
> `master_fd is None` and returns no-op. No file descriptor leak across
> multi-worker dispatch (verified via `psutil.Process().num_fds()` delta
> assertion in unit test, or equivalent platform fd count check).

**Escenario A1-5: Popen failure does not leak slave fd (W8 carry-forward)**

> **Given** Operator on POSIX; `pty.openpty()` returned valid
> (master_fd, slave_fd); `subprocess.Popen` is patched to raise
> `OSError("simulated spawn failure")`.
> **When** `_spawn_worker_with_pty(argv, env)` invoked.
> **Then** The Popen exception propagates AND both `master_fd` and
> `slave_fd` are closed BEFORE the exception escapes the helper. No
> file descriptor leak. Verified via `os.close(master_fd)` raising
> `OSError(EBADF)` post-helper (proves the helper closed it).

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

**Escenario A2-2: Worker close-phase runs sec.0.1 chain (C4 carry-forward)**

> **Given** Worker subprocess on any platform with
> `SBTDD_AUTO_PARALLEL_WORKER=1` set in env.
> **When** Worker calls `close_phase_cmd._run_verification(root)`.
> **Then** `_run_verification` checks env var → True → bypasses
> `superpowers_dispatch.verification_before_completion()` skill
> dispatch → runs the sec.0.1 4-tool chain in order (`pytest`,
> `ruff check .`, `ruff format --check .`, `mypy .`) via
> `subprocess.run(..., capture_output=True, text=True)` directly.
> Each tool's stdout/stderr/returncode is captured into a
> `captured` list. No `make` dependency. No interactive prompt. No
> TTY required.

**Escenario A2-3: Worker close-phase failure raises ValidationError + persists evidence (C4 carry-forward)**

> **Given** Worker subprocess calls `_run_verification(root)` in
> worker mode; `pytest` (the first sec.0.1 tool) returns non-zero.
> **When** `subprocess.run` for `pytest` returncode != 0.
> **Then** `_persist_worker_verify_evidence(root, captured)` is
> invoked first (writes the partial captured chain to
> `<root>/.claude/auto-run-workers/<pid>-verify.json` so INV-16
> evidence is preserved); THEN `ValidationError` is raised naming
> the failing tool (e.g., `"v1.0.7 A2 worker-mode verify failed at
> 'pytest': rc=1"`). Subsequent tools (`ruff`, `mypy`) are NOT run
> (semantically equivalent to `make verify` early-abort behavior).

**Escenario A2-7 (per iter-2 carry-forward C4 + iter-3 carry-forward C1): Worker close-phase success persists evidence with collision-resistant filename**

> **Given** Worker subprocess calls `_run_verification(root)` in
> worker mode; all 4 sec.0.1 tools return 0.
> **When** Each `subprocess.run` returncode == 0.
> **Then** `_persist_worker_verify_evidence(root, captured)` is
> invoked once at the end with all 4 tool captures. A sidecar file
> matching the glob `<root>/.claude/auto-run-workers/<pid>-*-verify.json`
> exists with full filename pattern
> `<pid>-<monotonic_ns>-<uuid8>-verify.json` (3-component
> disambiguator per iter-3 carry-forward C1: pid for human
> cross-reference, monotonic_ns sub-microsecond resolution against
> same-pid re-spawn, uuid8 final tiebreaker). File contains
> `{"verify_chain": [...]}` with one entry per tool + rc=0 +
> non-empty stdout. Parent post-batch merge in
> `auto_cmd._dispatch_tracks_concurrent` can introspect this for
> INV-16 evidence-before-assertions continuity.

**Escenario A2-9 (NEW per iter-3 carry-forward C1): Parent-side sidecar collision LOUD-FAIL**

> **Given** Two workers spawned via `_dispatch_tracks_concurrent`
> with overlapping pids (PID recycle scenario simulated by direct
> orchestrator code path) both call `_persist_worker_verify_evidence`.
> **When** Filenames are computed: each worker's
> `<pid>-<monotonic_ns>-<uuid8>-verify.json` is unique because
> monotonic_ns AND uuid8 differ even when pids match.
> **Then** Both sidecars exist on disk; neither overwrites the other;
> parent post-batch merge ingests BOTH into `.claude/auto-run.json`
> per-worker entry list (no silent data loss).

**Escenario A2-10 (NEW per iter-3 carry-forward C1): Parent-side missing sidecar raises ConcurrentDispatchError**

> **Given** Worker spawned via `_dispatch_tracks_concurrent` with
> known pid; worker completes (returncode collected) but
> `<root>/.claude/auto-run-workers/<pid>-*-verify.json` glob returns
> EMPTY (worker ran close-phase but failed to persist sidecar before
> exit, e.g., due to a bug in `_persist_worker_verify_evidence` or
> a transient OS error swallowed mid-write).
> **When** Parent post-batch merge enumerates expected workers vs
> observed sidecars.
> **Then** `ConcurrentDispatchError` raised naming the missing pid +
> listing observed sidecars + total expected workers. Batch HALTS;
> no silent INV-16 evidence loss.

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

**Escenario A2-8 (NEW per iter-2 carry-forward W1): Orchestrator invoke_skill with TTY context dispatches normally (guard ordering pin)**

> **Given** Orchestrator (no `SBTDD_AUTO_PARALLEL_WORKER` env var)
> invokes a `_SUBPROCESS_INCOMPATIBLE_SKILLS` member with
> `allow_interactive_skill=True` AND `subprocess_utils.is_headless_context()`
> returns False (TTY present, no `SBTDD_HEADLESS` env var).
> **When** Code path traverses the v1.0.7 A2 Q2'=b worker guard,
> then v1.0.4 membership gate, then v1.0.6 J-3 headless guard.
> **Then** All three gates short-circuit (worker-env False, member +
> override True, headless False); subprocess dispatch via `claude -p`
> proceeds normally. Test asserts the underlying
> `subprocess_utils.run_with_timeout` is invoked with the expected
> argv. No false-positive worker-context error in orchestrator code
> path. (This regression test pins the guard ordering: worker check
> MUST come first AND must check env var presence + skill membership
> jointly; checking env var alone would trip on operator scripts
> that set the env var unrelated to `--parallel`.)

### 4.3 Item A3 — F-A2 empirical validation

**Escenario A3-1: Synthetic 2-track plan dispatches via auto --parallel end-to-end on Windows + exercises chicken-and-egg surface (C3 carry-forward)**

> **Given** Synthetic 2-track plan + 4 disjoint tasks where each task
> ships a real (not no-op) `_run_verification` invocation chain — the
> fixture project has `pyproject.toml` + minimal source + tests so the
> sec.0.1 chain (`pytest`, `ruff check`, `ruff format --check`, `mypy`)
> all return 0. Each task's TDD cycle invokes the actual `python
> skills/sbtdd/scripts/run_sbtdd.py close-phase` from inside the worker
> subprocess (NOT a shell-noop), which in turn calls
> `_run_verification` → worker-mode bypass → sec.0.1 chain dispatch.
> **When** Operator on Windows runs `auto --parallel` against fixture.
> **Then** All workers complete within 600s timeout (no
> `ConcurrentDispatchError`); `.claude/auto-run.json` contains
> start_time + per-worker completion records (validates v1.0.5 I-1);
> per-worker `<root>/.claude/auto-run-workers/<pid>-verify.json` files
> exist containing the captured sec.0.1 chain output (validates v1.0.7
> A2 INV-16 evidence persistence); plan checkboxes all `[x]` post-merge
> (validates I-2); state file `current_phase: "done"` post-completion.
> No subprocess hangs > 600s timeout — THE chicken-and-egg closure
> signal. WITHOUT v1.0.7 Pillar A (A1+A2), this fixture would hang on
> the first worker close-phase invocation (workers spawned via
> `subprocess.Popen` stdin=PIPE without TTY). Post Pillar A: workers
> get either real PTY (POSIX) or worker-mode sec.0.1 bypass (Windows)
> and complete.

**Escenario A3-3 (NEW per iter-3 carry-forward W "A3 fixture realism"): On POSIX, integration test asserts PTY path executed**

> **Given** A3-1 fixture run on POSIX (`sys.platform != "win32"`).
> **When** Workers complete; integration test inspects per-worker
> sidecar files under `<root>/.claude/auto-run-workers/`.
> **Then** At least one sidecar's `verify_chain` entry's stdout
> contains evidence the worker observed a TTY (e.g., a pytest
> verbose marker that only appears under TTY, OR an explicit
> isatty=True echo from a test helper). This empirically distinguishes
> the v1.0.7 A1 PTY code path from the Windows hybrid Option B-W3
> bypass path — without this assertion, the integration test could
> pass on POSIX even if `_spawn_worker_with_pty` silently fell back
> to `subprocess.PIPE` (regression invisible to test). On Windows
> this escenario is SKIPPED (`pytest.skip("POSIX-only assertion")`)
> because the Windows path uses subprocess.PIPE intentionally.

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

> **v1.0.7 iter-2 carry-forward C2/C5 task collapse**: C1+C5+C6+C7 ship
> as ONE plan task T7 (combined polish with cross-linked Refactor diff
> per sec.2.7). C-X-K3-Removal ships as separate plan task T8.
> Escenarios below remain individually addressable but are validated
> within the collapsed-task TDD cycle (one Red writes all 4 doc smoke
> tests; one Green applies all 4 doc edits; one Refactor cross-links
> the K-4 helper docs from C1 + C6).

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
v1.0.7 iter-2 carry-forward C2/C5 collapse — 11 tasks → 8 tasks.
v1.0.7 iter-3 carry-forward (bal+cas WARNING): T6 → T2 swap places
B3 (atomic_write_json retry) BEFORE A2 worker-mode bypass that calls
`state_file.atomic_write_json` via `_persist_worker_verify_evidence`,
eliminating documented PermissionError flake risk during T3 dogfood.

1. **T1 = A1** (POSIX PTY allocation + lifecycle helper + leak guard) —
   `subprocess_utils.py` (`_spawn_worker_with_pty` + `_close_pty_master`)
   + tests. ~4-6 hours (carry-forward C1 + W7 + W8 expand original
   ~3-5h estimate).
2. **T6 = B3 (relocated per iter-3 carry-forward)** (atomic_write retry)
   — `state_file.py` + tests. ~1-2 hours. Lands BEFORE T2 so T2's
   `_persist_worker_verify_evidence` benefits from retry from day 1.
3. **T2 = A2** (Windows hybrid + Q2'=b worker runtime guard + sec.0.1
   chain bypass + INV-16 evidence sidecar with collision-resistant
   filename + parent-side LOUD-FAIL contract) — `auto_cmd.py` +
   `close_phase_cmd.py` + `superpowers_dispatch.py` +
   `_persist_worker_verify_evidence` helper +
   `_verify_worker_sidecars_present` parent-side helper + tests.
   ~7-9 hours (carry-forward C4 + W4 + W1 + W3 + iter-3 C1 expand
   original ~5-7h estimate).
4. **T3 = A3** (F-A2 empirical validation with real chicken-and-egg
   fixture + POSIX PTY-path assertion per iter-3 carry-forward) —
   synthetic 2-track plan + 4 disjoint tasks each invoking real
   `close-phase` chain via worker subprocess; integration test +
   fixture project with `pyproject.toml`. ~4-6 hours.
5. **T4 = B5** (drift detector regex) — `drift.py` + tests. ~30-60 min.
6. **T5 = B4** (spec_review_dispatch file-reference) —
   `spec_review_dispatch.py` + tests. ~2-3 hours.
7. **T7 = collapsed Pillar C polish** (C1+C5+C6+C7 in single combined
   task) — `auto_cmd.py` + `close_task_cmd.py` + `skills/sbtdd/SKILL.md`
   + tests. Single Red writes 4 doc smoke tests with discriminating
   class names (`TestC1*`, `TestC5*`, `TestC6*`, `TestC7*` per iter-3
   carry-forward bisect-granularity preservation); single Green
   applies 4 doc edits; single Refactor cross-links K-4 helper docs
   from C1+C6. ~1-2 hours total (real Refactor diff satisfies v1.0.5
   `_preflight` HARD-BLOCK).
8. **T8 = C-X-K3-Removal** (alias removal + test rewrite) —
   `close_task_cmd.py` + tests. Real TDD triplet (Red: AttributeError
   assertion; Green: alias removal + test monkeypatch target rewrites;
   Refactor: final sweep + lint cleanup). Green commit prefix `fix:`
   framed as "closes v1.0.7 C5-documented monkeypatch footgun" per
   W10 carry-forward. ~1-2 hours.

Total wall-time estimate: ~21-31 hours = ~3-4 days. Slightly above
original ~2-3 days estimate due to iter-2 + iter-3 carry-forward
expansions (C1 + C3 + C4 + iter-3 C1 substantively grew T1, T2, T3
work).

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
  unblocks make verify); Q4'=a all 5 Pillar C items shipped (collapsed
  into 1 combined task per iter-2 C2/C5 carry-forward + 1 separate
  C-X-K3-Removal task = 2 plan tasks for Pillar C, 8 plan tasks total);
  Q5'=a default G2 ladder pre-staged; Q1'=a single subagent sequential
  forced by chicken-and-egg; A3 own-cycle dogfood validates `--parallel`
  end-to-end on Windows. **`--parallel` POSIX path marked experimental**
  until v1.0.8 own-cycle dogfood validates POSIX end-to-end (per W5
  carry-forward) — A3 v1.0.7 dogfood mandatory on Windows only; POSIX
  validation deferred to CI / v1.0.8 if no POSIX dev env. **Worker-mode
  verify uses sec.0.1 chain (not `make verify`)** per C4 carry-forward,
  preserving INV-16 evidence-before-assertions semantic via per-worker
  sidecar capture. **Sidecar filename uses 3-component collision-resistant
  scheme** (`<pid>-<monotonic_ns>-<uuid8>-verify.json`) per iter-3
  carry-forward C1 (Cas iter-2 CRITICAL); parent post-batch merge
  LOUD-FAILS via `ConcurrentDispatchError` on missing sidecar. **T7
  (combined Pillar C polish) lands 4 doc smoke tests in a single Red
  commit per C2/C5 collapse — TEST CLASS NAMES preserved as distinct
  (`TestC1*` / `TestC5*` / `TestC6*` / `TestC7*`) for bisect granularity
  per iter-3 carry-forward (mel+bal+cas WARNING)**; this is a one-off
  pattern for v1.0.7 doc-only Pillar C polish, NOT a generalizable
  template — future cycles default to one-test-per-commit unless
  v1.0.5 `_preflight` HARD-BLOCK constraints similarly require
  collapse. **T6 (B3 atomic_write_json retry) lands BEFORE T2 (A2
  worker-mode bypass)** per iter-3 carry-forward (bal+cas WARNING) so
  the sidecar write benefits from retry from day 1.
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
- **R7 (NEW v1.0.7 iter-2 carry-forward W3)**. POSIX PTY master fd
  EIO/SIGHUP race: if the worker subprocess closes the slave end OR
  receives SIGHUP between `proc.wait()` returning and the orchestrator
  invoking `_close_pty_master`, the buffered-output drain loop may
  observe `OSError(EIO)` immediately on the first `os.read`. Mitigation:
  the lifecycle helper catches `OSError` broadly during drain (treats
  any failure as "drain complete") + idempotently closes the master
  fd. If a real SIGHUP race manifests in the field, the worst case is
  some buffered worker output is silently dropped — but the worker's
  exit code + per-worker sidecar evidence (v1.0.7 A2 INV-16 capture)
  preserves the actual verify-chain results. Acceptable trade-off for
  v1.0.7; tighten to explicit signal-aware drain in v1.0.8 if observed.
- **R9 (NEW v1.0.7 iter-3 carry-forward C1)**. Per-worker artifact
  collision class: PID recycle on POSIX (within ~32K pids on Linux,
  ~99K on macOS) OR same-pid re-spawn on Windows under fast worker
  churn could cause two workers' artifacts (sidecar verify evidence,
  per-worker scratch from v1.0.5 I-2, etc.) to share an identifier and
  silently collide. Mitigation: filename suffix = `<pid>-<monotonic_ns>-<uuid8>`
  for sidecars (v1.0.7 A2 implementation); applies same pattern to
  any future per-worker artifact. Parent-side LOUD-FAIL contract:
  post-batch merge MUST verify EVERY spawned worker produced AT LEAST
  ONE expected artifact; missing artifact raises `ConcurrentDispatchError`
  naming the offender. This catches the broader class of bugs where
  transient errors silently swallow per-worker writes — silent data
  loss is unacceptable; LOUD-FAIL surfaces it during dogfood / CI.
  Future v1.0.8+ work: extend the LOUD-FAIL contract to v1.0.5 I-1
  audit-trail sidecars + I-2 scratch plans (currently they have
  collision-resistant naming but no parent-side missing-artifact
  check).
- **R8 (NEW v1.0.7 iter-2 carry-forward W1)**. Worker-context guard
  (Q2'=b) false-positive risk: an operator script that sets
  `SBTDD_AUTO_PARALLEL_WORKER=1` in their shell environment for an
  unrelated reason AND invokes a `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  member would trip the guard with a misleading "worker subprocess"
  error. Mitigation: env var name is descriptive +
  operator-namespaced; documented in README + SKILL.md as
  parent-injected only (operator scripts MUST NOT set it manually).
  Escenario A2-6' (NEW) regression test pins the orchestrator-mode
  pass-through to catch any guard-ordering regression in future
  refactors.

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
  on Windows with REAL chicken-and-egg fixture (each worker invokes
  real `close-phase` chain → sec.0.1 4-tool dispatch); B4
  spec-reviewer file-reference closes WinError 206 even with large
  diffs; B5 drift detector test_v104 regression passes; per-worker
  `<root>/.claude/auto-run-workers/<pid>-verify.json` sidecar files
  exist post-cycle (validates v1.0.7 A2 INV-16 evidence persistence).
  POSIX validation deferred to v1.0.8 / CI per W5 carry-forward.
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
