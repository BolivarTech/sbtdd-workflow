# Especificacion base — sbtdd-workflow v1.0.7 (post-v1.0.6 ship)

> Generado 2026-05-09 a partir de v1.0.6 ship record + v1.0.6 own-cycle dogfood empirical findings + v1.0.6 Loop 2 deferred polish + v1.0.5 polish carry-forward.
>
> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v1.0.7). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado post-v1.0.6 ship (tag `v1.0.6` at commit `5ee8be6`,
> branch `feature/v1.0.7-bundle` branched off `main` HEAD `5ee8be6`).
>
> v1.0.7 = **`--parallel` operational unblock cycle (NON-POSTPONABLE)** per
> user mandate 2026-05-09 ("dejar parallel completamente operacional").
> Pillar A is hard-LOCKED + non-negotiable. Three pillars:
>
> - **Pillar A PRIMARY (NON-POSTPONABLE, HARD-LOCKED CRITICAL)** —
>   PTY allocation Fix B in worker subprocess spawn. Closes the
>   chicken-and-egg empirically confirmed in v1.0.6 own-cycle:
>   workers spawned via `subprocess.Popen` with `stdin=PIPE` have
>   no TTY → close-phase `/verification-before-completion` subprocess
>   hangs indefinitely (28+ min @ 0.04 CPU). v1.0.6 Pillar A J-1+J-2+J-3
>   added FAIL-FAST detection; v1.0.7 makes `--parallel` ACTUALLY WORK
>   end-to-end. POSIX `pty.openpty()` per worker spawn + Windows hybrid
>   Option B-W3 fallback (subprocess.PIPE + Fix A semantic skip of
>   interactive skill in worker mode). Per memory
>   `project_v107_pty_workers_locked.md`.
> - **Pillar B LOCKED (v1.0.6 dogfood findings + carry-forward)** —
>   B4 `spec_review_dispatch` file-reference pattern (analogous to
>   v1.0.3 cross-check Item B fix; closes WinError 206 argv too long
>   for Windows on T6+ close-task) + B5 drift detector unanchored
>   `[ ]` regex line-anchoring (false-positive on code-block fixtures
>   in plan-tdd.md test fixtures) + B3 `auto_cmd._atomic_write_json`
>   Windows PermissionError catch (analogous to v1.0.5 K-2
>   `_reap_orphans` fix; v1.0.6 hit it once mid-cycle).
> - **Pillar C LOCKED (selective polish from v1.0.6 deferred)** —
>   3-5 cherry-picked items from C1-C8 polish (memory
>   `project_v107_locked_backlog.md` Pillar C section).
>
> v1.0.7 INV stance: **strict no-INV-0** preserved (Q3=a per v1.0.6
> precedent) — preserve 8-cycle Checkpoint 2 streak goal +
> re-establish pre-merge Loop 2 streak (broken at v1.0.6 due to
> chicken-and-egg blocking `/sbtdd pre-merge`; v1.0.7 Pillar A unlocks
> empirically). G1 cap=3 HARD Checkpoint 2 sin INV-0 path. G2 binding
> pre-staged: scope-trim ladder defers Pillar C polish first → defer
> Pillar B subset second → only Pillar A hard-LOCKED.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento NO lo
> reemplaza — agrega el delta v1.0.7 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder
> word-boundary verificable con `spec_cmd._INV27_RE` regex.

---

## 1. Objetivo

**v1.0.7 = "`--parallel` operational unblock + dogfood-discovered fixes"**:
ships PTY allocation in worker subprocess spawn (Pillar A non-postponable
per user mandate) + 3 Pillar B fixes empirically discovered in v1.0.6
own-cycle (B4 + B5 + B3) + 3-5 cherry-picked Pillar C polish items.

Tres clases de items:

### Clase 1 — Pillar A PRIMARY (HARD-LOCKED, NON-POSTPONABLE)

- **Item A1 — POSIX PTY allocation in `_dispatch_tracks_concurrent`**.
  Modify `auto_cmd._dispatch_tracks_concurrent` worker spawn to use
  `pty.openpty()` for stdin (POSIX-only). Worker subprocess gets a
  pseudo-TTY slave; orchestrator holds master end. Skill subprocess
  chain inherits TTY from worker → interactive prompts work →
  `close-phase /verification-before-completion` no longer hangs.

- **Item A2 — Windows hybrid Option B-W3 fallback**. Python `pty`
  module is POSIX-only. Windows has no native PTY equivalent in
  stdlib (ConPTY exists in Win10+ but stdlib doesn't expose).
  Fallback: detect Windows via `sys.platform == "win32"`; on Windows,
  workers use existing `subprocess.PIPE` (no PTY); workers detect
  worker context via env var (`SBTDD_AUTO_PARALLEL_WORKER=1` set by
  parent) + skip `/verification-before-completion` skill dispatch in
  worker mode + run `make verify` shell command directly via
  `subprocess.run` (no skill wrapper, no interactive prompt). POSIX
  gets real PTY semantics; Windows gets reliable shell-direct semantics.

- **Item A3 — F-A2 dogfood empirical end-to-end validation**.
  v1.0.7 own-cycle MUST exercise `auto --parallel` end-to-end on
  POSIX (if available) AND Windows. Validates that v1.0.6 Pillar A
  fail-fast detection + v1.0.7 Pillar A PTY allocation jointly
  unlock production-grade `--parallel` adoption. Acceptance: synthetic
  2-track plan with 4 disjoint tasks completes via `auto --parallel`
  end-to-end on Windows AND POSIX (if available; orchestrator dev
  env is Windows so POSIX validation may be deferred to CI).

### Clase 2 — Pillar B LOCKED (v1.0.6 dogfood findings + carry-forward)

- **Item B4 — `spec_review_dispatch` file-reference pattern**.
  v1.0.6 own-cycle T6+T7 close-task hit `WinError 206` "filename or
  extension is too long" because `spec_review_dispatch.dispatch_spec_reviewer`
  packs full reviewer prompt (task text + diff) into argv via
  `claude -p <large-prompt>`. Large diffs exceed Windows cmdline
  limit. Same pattern as v1.0.3 cross-check Item B fix. Apply
  analogous solution: write reviewer prompt to project-relative
  `<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md` + pass
  `@<filepath>` reference in argv. `try/finally` cleanup post-dispatch.

- **Item B5 — Drift detector line-anchored `[ ]` regex**. v1.0.6
  drift detector counts `[ ]` markers inside Python test fixture
  string literals (code blocks in plan-tdd.md) as "open task
  checkboxes" → false-positive "plan still has open tasks [ ]" even
  when all task sections are fully `[x]`-flipped. Same pattern as
  v1.0.6 K-1 fix for `_section_has_flipped`. Apply line-anchored
  multiline regex `^[ \t]*- \[ \]` to drift detector's plan-state
  check (likely in `drift._plan_all_tasks_complete` or analogous
  helper). Affects `tests/test_drift.py::test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs`.

- **Item B3 — `auto_cmd._atomic_write_json` Windows PermissionError catch**.
  v1.0.6 hit `PermissionError: [WinError 5] Access is denied:
  '...auto-run.json.q6wjytm7.tmp' -> '...auto-run.json'` once
  mid-cycle. Cause: AV scanner OR concurrent writer holding file.
  Fix: wrap `os.replace(tmp, dst)` in try/except `(PermissionError,
  OSError)` with retry-with-backoff (~3 attempts × ~100ms).
  Analogous to v1.0.5 K-2 `_reap_orphans` PermissionError catch
  pattern.

### Clase 3 — Pillar C LOCKED (selective polish from v1.0.6 deferred)

- **Item C1 — K-4 single-level subparser walk comment**.
  `_validate_forwardable_flags_against_argparse` walks
  `parser._actions` + `action.choices` only one level deep. Add
  inline comment: "single-level subparser walk; deeper nesting not
  supported. If plugin gains deeply nested subparsers, extend
  recursive walk."

- **Item C5 — K-3 monkeypatch comment extension**. Extend deprecation
  marker comment in `close_task_cmd.py`:
  "DEPRECATED: alias removed in v1.0.7. NOTE:
  monkeypatch.setattr('_preflight_triplet_check', ...) does NOT
  patch the canonical `_preflight`; tests must target the canonical
  name to actually patch behavior."

- **Item C6 — K-4 helper docstring note re: importlib.reload**.
  Add brief docstring note to
  `_validate_forwardable_flags_against_argparse`: "Tests that
  monkeypatch _FORWARDABLE_FLAGS should call this helper directly
  rather than reloading auto_cmd to avoid import-time guard
  interaction."

- **Item C7 — CHANGELOG Process notes commitment for methodology activities**.
  Document in `skills/sbtdd/SKILL.md` ship-time procedure: any
  methodology-activity finding (F-J9, F-J10, F-A2, F-Resume, P2)
  that doesn't trigger ship abort gets a v1.0.X+1 LOCKED entry at
  ship time (not mid-cycle). Process discipline: prevents deferral
  pipeline drift between cycles.

- **Item C-X-K3-Removal — Remove K-3 deprecation alias** per Q3'=a
  decision in v1.0.6 (1-cycle window). v1.0.7 ships removal of
  `_preflight_triplet_check = _preflight` alias. Update test
  monkeypatch targets to use canonical `_preflight` name. Verify
  no remaining callsites reference legacy name.

### Out of scope v1.0.7 (rolled forward a v1.0.8+)

- **B2 worker subprocess auto-message generation hardening** (larger
  refactor; defer to v1.0.8 if Pillar A bandwidth allows polish-only
  cycle next).
- **C2 K-4 escape hatch test coverage** (defer until empirical
  evidence of false-positive).
- **C3 F-A2 worker env guard** (`SBTDD_AUTO_PARALLEL_WORKER` runtime
  guard in `invoke_skill`) — actually MAY be needed for Pillar A
  Windows hybrid Option B-W3; could promote to Pillar A in
  brainstorming.
- **C4 NF-B test count rebaseline** (process-only; defer).
- **C8 F-A2 abort criterion (b) diagnosis hint refinement** (cosmetic
  doc improvement; defer).
- **Pillar D items** (5 v1.0.5 polish carry-forward not addressed in
  v1.0.6) — defer to v1.0.8 polish-only cycle.
- **Edge cases E1-E3** — defer until empirical evidence in field.
- **All v1.0.4 carry-forward inherited items** — defer to v1.1.0
  (major version bump for breaking changes).

### Criterio de exito v1.0.7

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.6 -> 1.0.7.
- Tests baseline 1271 + 1 skipped preservados sin regresion + ~10-15
  nuevos (Pillar A PTY allocation: ~5-7 incl. POSIX + Windows fallback;
  Pillar B B4+B5+B3: ~4-6; Pillar C polish: ~2-3 doc-coherence smoke).
- `make verify` runtime <= 200s soft / 220s hard (acknowledges v1.0.6
  baseline 185s + ~10-15s incremental).
- Coverage threshold mantenido en 88% (v1.0.6 measured 89.82%; v1.0.7
  must not regress below).
- **`auto --parallel` empirical end-to-end validation** (NON-NEGOTIABLE):
  synthetic 2-track plan with 4 disjoint tasks completes via
  `auto --parallel` on POSIX (if available) AND Windows. NO subprocess
  hang on `close-phase /verification-before-completion`. Workers
  successfully complete TDD cycle + close-phase + close-task.
- **`/sbtdd pre-merge` end-to-end**: post Pillar A ship, `/sbtdd pre-merge`
  Loop 1 + Loop 2 should work end-to-end. Re-establish pre-merge
  Loop 2 no-override streak from 1 cycle (broken in v1.0.6 due to
  chicken-and-egg).
- **G1 binding HARD respetado**: cap=3 HARD para Checkpoint 2; sin
  INV-0. **8-cycle Checkpoint 2 no-override streak goal**
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6+v1.0.7).
- **Pre-merge Loop 2 streak**: re-establish from 1 cycle goal.
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no
  converge — defer Pillar C polish first → defer Pillar B subset
  second → only Pillar A (A1+A2+A3) hard-LOCKED.

---

## 2. Alcance v1.0.7 — items LOCKED post-v1.0.6 ship

### 2.1 Item A1 — POSIX PTY allocation in `_dispatch_tracks_concurrent` (Pillar A PRIMARY HARD-LOCKED)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
  (`_dispatch_tracks_concurrent` worker spawn helper)
- Possibly modify: `skills/sbtdd/scripts/subprocess_utils.py`
  (new `spawn_worker_with_pty()` helper if extracted)
- Extend: `tests/test_auto_cmd.py` + `tests/test_parallel_dispatcher.py`
  (new test class for PTY allocation)

**Empirical context (v1.0.6 ship reconfirmation)**:

v1.0.6 own-cycle `auto --parallel` dogfood (F-A2 Activity) hit
chicken-and-egg subprocess hang on `close-phase
/verification-before-completion`. Workers spawned via
`subprocess.Popen` with `stdin=PIPE` have no TTY → skill subprocess
inherits non-TTY stdin → waits for interactive prompt that never
arrives. Worker meta-cognition explicitly identified the cause and
aborted at 28+ min @ 0.04 CPU.

v1.0.6 Pillar A J-1+J-2+J-3 added FAIL-FAST detection — workers in
headless context raise `PreconditionError` LOUD-FAST instead of
silent hang. v1.0.7 Pillar A makes `--parallel` ACTUALLY WORK by
giving workers a real TTY via PTY allocation.

**Implementation outline (POSIX)**:

```python
import pty
import os
import subprocess

def _spawn_worker_with_pty(argv: list[str], env: dict[str, str]) -> subprocess.Popen:
    """v1.0.7 A1 POSIX: allocate pseudo-TTY for worker subprocess.

    Workers inherit the slave end as stdin/stdout/stderr; orchestrator
    holds master end (returned via .stdin attribute). Skill subprocess
    chain inherits TTY from worker → /verification-before-completion
    interactive prompt works.
    """
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
    proc._pty_master_fd = master_fd  # store for cleanup
    return proc
```

### 2.2 Item A2 — Windows hybrid Option B-W3 fallback (Pillar A PRIMARY HARD-LOCKED)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
  (`_dispatch_tracks_concurrent` Windows branch + worker
  `SBTDD_AUTO_PARALLEL_WORKER=1` env var setting)
- Modify: `skills/sbtdd/scripts/close_phase_cmd.py`
  (`_run_verification` Windows worker mode bypass)
- Possibly modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (analogous worker bypass for any future interactive skill called
  from worker context)
- Extend: tests for Windows fallback path

**Implementation outline (Windows)**:

```python
# auto_cmd._dispatch_tracks_concurrent (Windows branch)
import sys
if sys.platform == "win32":
    # Option B-W3: workers use subprocess.PIPE + run shell directly
    env_with_marker = {**env, "SBTDD_AUTO_PARALLEL_WORKER": "1"}
    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env_with_marker,
    )
else:
    # POSIX: real PTY allocation
    proc = _spawn_worker_with_pty(argv, env)
```

```python
# close_phase_cmd._run_verification (worker bypass)
def _run_verification(root: Path) -> None:
    if os.environ.get("SBTDD_AUTO_PARALLEL_WORKER") == "1":
        # Worker mode (any platform): bypass interactive skill,
        # run make verify shell command directly. No interactive
        # prompt; deterministic verify result.
        result = subprocess.run(
            ["make", "verify"], cwd=str(root), check=False
        )
        if result.returncode != 0:
            raise ValidationError(f"make verify failed: rc={result.returncode}")
    else:
        # Orchestrator/sequential mode: existing skill dispatch
        superpowers_dispatch.verification_before_completion(cwd=str(root))
```

### 2.3 Item A3 — F-A2 dogfood empirical end-to-end validation (Pillar A PRIMARY)

**Track**: orchestrator (post Pillar A ship).

v1.0.7 own-cycle MUST exercise `auto --parallel` end-to-end on
Windows (mandatory; dev env). POSIX validation deferred to CI or
v1.0.8 if no POSIX dev env available.

**Acceptance**: synthetic 2-track plan with 4 disjoint tasks (NOT
v1.0.7 own-cycle plan — separate test fixture); dispatch via
`auto --parallel`; workers complete TDD cycle + close-phase +
close-task; parent post-batch merge produces final state with
all tasks `[x]`. NO subprocess hang on `/verification-before-completion`.

### 2.4 Item B4 — `spec_review_dispatch` file-reference pattern (Pillar B)

**Archivos**:
- Modify: `skills/sbtdd/scripts/spec_review_dispatch.py`
  (write prompt to file + pass `@<filepath>` reference in argv)
- Extend: `tests/test_spec_review_dispatch.py` (file-reference pattern test)

**Empirical context (v1.0.6 own-cycle T6+T7)**:

`spec_review_dispatch.dispatch_spec_reviewer` invokes `claude -p
<large-prompt>` subprocess where `<large-prompt>` is the full reviewer
prompt with task text + diff content embedded. Large diffs (e.g.,
T6 K-4 + T7 K-5 cumulative) exceed Windows cmdline limit (~32K chars
per Windows API).

v1.0.6 hit `FileNotFoundError: [WinError 206] The filename or
extension is too long` during T6 close-task spec-reviewer dispatch.
Same pattern as v1.0.3 cross-check Item B fix.

**Implementation outline**:

```python
import uuid
import tempfile

def dispatch_spec_reviewer(...):
    prompt = _build_reviewer_prompt(task_id, task_text, diff_text)
    # v1.0.7 B4: write prompt to project-relative tempfile + pass
    # @<filepath> reference in argv (analogous v1.0.3 cross-check fix)
    tmp_dir = repo_root / ".claude" / "spec-reviews" / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = tmp_dir / f"prompt-{uuid.uuid4().hex[:16]}.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    try:
        argv = ["claude", "-p", f"@{prompt_path}", ...]
        result = subprocess_utils.run_with_timeout(argv, ...)
        # ... process result ...
    finally:
        prompt_path.unlink(missing_ok=True)
```

### 2.5 Item B5 — Drift detector line-anchored `[ ]` regex (Pillar B)

**Archivos**:
- Modify: `skills/sbtdd/scripts/drift.py` (line-anchored regex)
- Extend: `tests/test_drift.py` (regression test for code-block
  fixtures)

**Empirical context**:

v1.0.6 post-cycle drift detector counted 22 `[ ]` occurrences inside
Python test fixture string literals (e.g., `"- [ ] Step 1\n"`) as
"open task checkboxes" → false-positive `Drift: detected: state=done,
HEAD=chore:, plan=[ ] (state is done but plan still has open tasks
[ ])`. Caused `tests/test_drift.py::test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs`
failure even when all task sections were fully `[x]`.

Same pattern as v1.0.6 K-1 fix for `_section_has_flipped`. Apply
line-anchored multiline regex `^[ \t]*- \[ \]` to drift detector's
plan-state check.

### 2.6 Item B3 — `auto_cmd._atomic_write_json` Windows PermissionError catch (Pillar B)

**Archivos**:
- Modify: `skills/sbtdd/scripts/state_file.py` (where
  `atomic_write_json` is consolidated per v1.0.5 K-2 DRY)
- Extend: `tests/test_state_file.py` (Windows PermissionError retry test)

**Empirical context**:

v1.0.6 hit `PermissionError: [WinError 5] Access is denied:
'...auto-run.json.q6wjytm7.tmp' -> '...auto-run.json'` once mid-cycle.
Cause: AV scanner OR concurrent writer holding file.

**Implementation outline**:

```python
def atomic_write_json(path: Path, data: object, max_retries: int = 3) -> None:
    """v1.0.7 B3: atomic JSON write with Windows PermissionError
    retry-with-backoff. Analogous to v1.0.5 K-2 _reap_orphans catch.
    """
    fd, tmp_str = tempfile.mkstemp(...)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        for attempt in range(max_retries):
            try:
                os.replace(tmp_str, path)
                return
            except (PermissionError, OSError) as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (attempt + 1))  # backoff
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise
```

### 2.7 Items C1+C5+C6+C7+C-X-K3-Removal — Pillar C polish

Per memory `project_v107_locked_backlog.md` Pillar C details:

- **C1**: 1-line comment in K-4 helper documenting single-level
  subparser walk limitation.
- **C5**: extend K-3 deprecation marker comment with monkeypatch
  footgun warning.
- **C6**: add docstring note to `_validate_forwardable_flags_against_argparse`
  re: importlib.reload interaction.
- **C7**: document ship-time methodology-activity findings → v1.0.X+1
  LOCKED procedure in `skills/sbtdd/SKILL.md`.
- **C-X-K3-Removal**: remove `_preflight_triplet_check = _preflight`
  alias per Q3'=a decision in v1.0.6 (1-cycle deprecation window
  expires in v1.0.7). Update test references.

### 2.8 v1.0.7 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B ship).

**Activities**:
1. **A3 `auto --parallel` empirical validation** (NON-NEGOTIABLE)
2. **B4 spec-reviewer file-reference dogfood**: own-cycle close-task
   should NOT hit `WinError 206` even with large cumulative diffs.
3. **B5 drift detector regression dogfood**: post-cycle `make verify`
   should pass `test_v104_plan_has_no_h3_task_headers...` test
   (currently false-positive failure).
4. **`/sbtdd pre-merge` end-to-end** (post Pillar A ship): re-establish
   pre-merge Loop 2 no-override streak from 1 cycle.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.7 NO propone
nuevos invariantes (todos los items son bug fix + polish).

Critical durante implementacion v1.0.7:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  8-cycle Checkpoint 2 no-override streak goal preserved
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6+v1.0.7). NO INV-0
  override en Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.7 multi-pillar bundle podria necesitar scope-trim si Loop 2
  hits structural findings — defer Pillar C polish items first →
  defer Pillar B subset second; Pillar A A1+A2+A3 hard-LOCKED.
- **Pre-merge Loop 2 streak preservation**: v1.0.6 broke (chicken-and-egg).
  v1.0.7 goal = re-establish from 1 cycle sin INV-0 (post Pillar A
  PTY allocation unblocks `/sbtdd pre-merge`).
- **`--parallel` empirical dogfood requerida** post Pillar A ship:
  v1.0.7 cycle MUST exercise own dogfood via `auto --parallel`
  end-to-end on Windows AND POSIX (if available) to validate Pillar A
  fix empirically.

### Stack y runtime

Sin cambios vs v1.0.6:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot
  paths.
- Dependencias externas runtime: git, tdd-guard, superpowers, magi
  (>= 2.2.x), claude CLI.
- Dependencias dev: pytest, pytest-asyncio, pytest-cov >= 4.1, ruff,
  mypy, pyyaml.
- Licencia dual MIT OR Apache-2.0.

### Reglas duras no-eludibles (sin override)

- INV-0 autoridad global.
- INV-27 spec-base sin uppercase placeholder markers (este doc cumple).
- INV-37 (v1.0.1) composite-signature output validation tripwire.
- Commits en ingles + sin Co-Authored-By + sin IA refs.
- No force push a ramas compartidas (INV-13).
- No commitear archivos con patrones de secretos (INV-14).
- G1 binding cap=3 HARD para Checkpoint 2 (precedente cerrado
  v1.0.0..v1.0.6 = 7-cycle no-override streak; v1.0.7 preserves to 8).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F195 v1.0.6; v1.0.7 starts at F196.)

### Item A1 — POSIX PTY allocation

**F196**. New helper `_spawn_worker_with_pty(argv, env)` allocating
`pty.openpty()` per worker on POSIX. Worker subprocess inherits
slave fd as stdin/stdout/stderr; orchestrator holds master fd.

**F197**. `_dispatch_tracks_concurrent` worker spawn uses
`_spawn_worker_with_pty` on POSIX (`sys.platform != "win32"`).

**F198**. PTY master fd cleanup post-worker-completion (close + drain
buffered output if any).

### Item A2 — Windows hybrid Option B-W3

**F199**. `_dispatch_tracks_concurrent` worker spawn on Windows
(`sys.platform == "win32"`) uses existing `subprocess.PIPE` for
stdin AND sets `SBTDD_AUTO_PARALLEL_WORKER=1` env var in worker.

**F200**. `close_phase_cmd._run_verification` checks
`SBTDD_AUTO_PARALLEL_WORKER` env var; if set, bypasses
`/verification-before-completion` skill dispatch and runs `make
verify` shell command directly via `subprocess.run` (no interactive
prompt; deterministic).

**F201**. ValidationError raised on `make verify` non-zero exit
(equivalent to skill failure semantics).

### Item A3 — F-A2 empirical validation

**F202**. v1.0.7 own-cycle exercises `auto --parallel` end-to-end
on Windows AND POSIX (if available). Synthetic 2-track plan with 4
disjoint tasks completes successfully without subprocess hang.

### Item B4 — spec_review_dispatch file-reference

**F203**. `spec_review_dispatch.dispatch_spec_reviewer` writes
reviewer prompt to project-relative
`<repo_root>/.claude/spec-reviews/.tmp/prompt-<uuid16>.md` + passes
`@<filepath>` reference in argv. `try/finally` cleanup post-dispatch.

**F204**. Closes WinError 206 root cause for spec-reviewer
subprocess on Windows; cumulative diff growth no longer breaks
close-task on T6+ in long cycles.

### Item B5 — Drift detector line-anchored regex

**F205**. `drift._plan_all_tasks_complete` (or analogous helper)
uses line-anchored multiline regex `^[ \t]*- \[ \]` to detect open
checkboxes. Defends against false-positives from `[ ]` substrings
in code-block string literals.

**F206**. `tests/test_drift.py::test_v104_plan_has_no_h3_task_headers_for_absorbed_deferred_stubs`
passes when all task sections are fully `[x]`-flipped (currently
false-positive failure due to fixture content).

### Item B3 — atomic_write_json Windows PermissionError catch

**F207**. `state_file.atomic_write_json` wraps `os.replace(tmp, dst)`
in try/except `(PermissionError, OSError)` with retry-with-backoff
(default 3 attempts × 100ms × attempt-number).

### Items C1+C5+C6+C7+C-X-K3-Removal

**F208**. C1: K-4 helper inline comment about single-level subparser
walk limitation.

**F209**. C5: K-3 deprecation marker comment extension with
monkeypatch footgun warning.

**F210**. C6: K-4 helper docstring note re: importlib.reload
interaction with import-time guard.

**F211**. C7: SKILL.md ship-time procedure for methodology-activity
findings → v1.0.X+1 LOCKED entries.

**F212**. C-X-K3-Removal: remove `_preflight_triplet_check =
_preflight` 1-cycle alias per Q3'=a v1.0.6 commitment. Update test
monkeypatch targets.

### Requerimientos no-funcionales (NF)

**NF53**. `make verify` runtime <= 200s soft target / 220s hard
(acknowledges v1.0.6 baseline 185s + new tests).

**NF54**. v1.0.6 plans + state files parse correctly; no migration
required for v1.0.7.

**NF55**. Per-module coverage threshold preserved at 88% (no
regression).

**NF56**. v1.0.7 own-cycle dogfood `auto --parallel` end-to-end on
Windows (mandatory) + POSIX (if available).

**NF57**. v1.0.7 ship WITHOUT INV-0 override at pre-merge Loop 2
(re-establish streak from 1 cycle goal).

**NF58**. v1.0.7 ship WITHOUT INV-0 override at Checkpoint 2
(8-cycle streak goal).

---

## 5. Scope exclusions

Out-of-scope v1.0.7 (rolled forward a v1.0.8+):

- B2 worker subprocess auto-message generation hardening
- C2 K-4 escape hatch test coverage
- C3 F-A2 worker env guard runtime check (potentially merged into
  Pillar A A2 brainstorming)
- C4 NF-B test count rebaseline
- C8 F-A2 abort criterion (b) diagnosis hint refinement
- All Pillar D items (5 v1.0.5 polish carry-forward)
- Edge cases E1-E3

Out-of-scope v1.0.7+ (rolled forward a v1.1.0):

- All v1.0.4 carry-forward inherited items (`agreement_rate` rename,
  `spec_lint` R3 promote, per-module coverage 85%, GitHub Actions CI
  workflow, Migration tool real test, AST dead-helper detector
  codification, W8 Windows fs retry-loop, `_read_auto_run_audit`
  skeleton wiring, spec sec.7.1.3 G2 amendment, `magi_cross_check`
  default-flip, Group B options 1/3/4/6/7) — defer to v1.1.0 cycle.

---

## 6. Criterios de aceptacion finales

v1.0.7 ship-ready cuando:

### 6.1 Functional Items A1/A2/A3 + B4+B5+B3 + C1+C5+C6+C7+C-X-K3-Removal

- **F1**. F196-F198 (Item A1): POSIX `pty.openpty()` allocation +
  master fd cleanup + worker spawn integration.
- **F2**. F199-F201 (Item A2): Windows hybrid Option B-W3 fallback
  + `SBTDD_AUTO_PARALLEL_WORKER` env var + `_run_verification`
  worker-mode bypass.
- **F3**. F202 (Item A3): F-A2 empirical validation passes
  end-to-end on Windows.
- **F4**. F203-F204 (Item B4): spec_review_dispatch file-reference
  closes WinError 206.
- **F5**. F205-F206 (Item B5): drift detector line-anchored regex +
  test_v104 regression pass.
- **F6**. F207 (Item B3): atomic_write_json Windows PermissionError
  catch + retry-with-backoff.
- **F7**. F208-F212 (Items C1+C5+C6+C7+C-X-K3-Removal): polish
  items + K-3 alias removal.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s
  hard.
- **NF-B**. Tests baseline 1271 + 1 skipped + ~10-15 nuevos =
  ~1281-1290 final.
- **NF-C**. Cross-platform (Windows + POSIX) — Pillar A validated
  on both via env var + isatty mocking + real PTY allocation
  (POSIX) + Windows hybrid (Windows).
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados.

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**.
  8-cycle Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (re-establish streak from 1 cycle post v1.0.6 break).
  If unable to converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0.
- **P3**. CHANGELOG `[1.0.7]` entry written con secciones Added /
  Changed / Process notes + Pillar A A1+A2+A3 + Pillar B B4+B5+B3 +
  Pillar C polish + dogfood findings.
- **P4**. Version bump 1.0.6 -> 1.0.7 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.7` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. v1.0.7 own-cycle dogfood: `auto --parallel` end-to-end on
  Windows.
- **P8**. `/sbtdd spec --resume-from-magi` + `/sbtdd pre-merge`
  validated end-to-end post Pillar A ship.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.7 ship + items + dogfood
  observations).
- **D3**. Documented:
  - Pillar A PTY allocation in `auto_cmd.py` docstring + README
    operational notes + SKILL.md v1.0.7 notes.
  - `SBTDD_AUTO_PARALLEL_WORKER` env var in operator-facing docs.
  - C7 ship-time methodology-activity procedure in SKILL.md.
  - K-3 alias removal in CHANGELOG.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.7

- **R1**. POSIX PTY allocation may have subtle stdin/stdout
  buffering issues. Mitigation: explicit drain of master fd
  post-worker-completion; integration test exercises full TDD
  cycle.
- **R2**. Windows hybrid Option B-W3 bypass of
  `/verification-before-completion` skill loses INV-16 evidence-
  before-assertions semantic in worker context. Mitigation: `make
  verify` returncode is deterministic; failure raises
  ValidationError equivalent to skill failure. INV-16 preserved in
  orchestrator/sequential mode.
- **R3**. v1.0.7 own-cycle dogfood requires successful Pillar A
  ship before exercising. Chicken-and-egg: if Pillar A has bugs
  surfacing only at runtime, dogfood fails + cycle stuck.
  Mitigation: extensive Pillar A unit tests + manual `auto`
  sequential fallback for cycle completion. Same workaround pattern
  as v1.0.6.
- **R4**. Pre-merge Loop 2 streak re-establish goal may not be
  achievable if cycle surfaces fundamental architectural questions
  in Pillar A or Pillar B. Mitigation: G2 scope-trim ladder (defer
  Pillar C polish first → Pillar B subset second; Pillar A
  hard-LOCKED). Q3=a strict no-INV-0 stance + escalate-to-user-
  before-INV-0 discipline preserved.
- **R5**. `_PREFLIGHT_TRIPLET_CHECK` alias removal (C-X-K3-Removal)
  may break operator scripts that monkeypatched the alias name.
  Mitigation: 1-cycle deprecation window expired per v1.0.6
  commitment; documented in CHANGELOG `[1.0.6]` Deferred section.
  Operators on contract: monkeypatch canonical name only.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.6 ship record: tag `v1.0.6` (commit `5ee8be6`); branch
  `feature/v1.0.7-bundle` branched off `main` HEAD `5ee8be6`.
- v1.0.5 ship record: tag `v1.0.5` (commit `8539af1`); merge
  `b1c5262` on `main`.
- v1.0.7 LOCKED memories:
  - `project_v107_locked_backlog.md` (full 17-item backlog
    consolidation).
  - `project_v107_pty_workers_locked.md` (Pillar A primary detail).
  - `project_v106_shipped.md` (full v1.0.6 ship record + empirical
    findings).
- v1.0.8 deferred backlog: B2 + C2 + C3 + C4 + C8 + Pillar D items
  + Edge cases.
- v1.1.0 deferred backlog: all v1.0.4 carry-forward inherited
  items.
- Branch: trabajo en `feature/v1.0.7-bundle` (branched off `main`
  HEAD `5ee8be6`).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.7 own-cycle**: per CLAUDE.local.md sec.1 Flujo
de especificacion + v1.0.6 Process notes precedent, brainstorming
se correra en sesion interactiva (esta sesion) via Skill tool
in-session. NO via `claude -p` subprocess (chicken-and-egg until
Pillar A lands; precedent preserved).

**Hybrid methodology continued**: Opcion A manual `run_magi.py`
for Checkpoint 2 + Loop 2 dispatch per v1.0.2..v1.0.6 precedent.
Once v1.0.7 Pillar A lands, future cycles can attempt subprocess
path (`/sbtdd spec` + `/sbtdd pre-merge` end-to-end).

Decisiones pendientes clave para brainstorming (Q1'-Q5' estimated):

1. **Subagent partition (Q1')**: 11 items (A1+A2+A3 in Pillar A;
   B4+B5+B3 in Pillar B; C1+C5+C6+C7+C-X-K3-Removal in Pillar C).
   Possibilities:
   - **Single subagent sequential**: A1→A2→A3 (Pillar A) → B4→B5→B3 →
     C polish. ~2-3 dias wall-time. **Forced by chicken-and-egg**:
     can't use --parallel for Pillar A own-cycle until Pillar A lands.
   - **2-track parallel post Pillar A ship**: once A1+A2+A3 commits
     land, switch to --parallel for Pillar B + C tasks. Risky if
     Pillar A has bugs surfacing at runtime.
   - **Manual subagent dispatch via Agent tool fan-out** (Q1' option b
     from v1.0.6 fallback): Agent tool subagents inherit TTY differently
     than auto --parallel workers. Could work for Pillar B + C parallel.

2. **Windows hybrid Option B-W3 scope (Q2')**: `_run_verification`
   bypass IS the v1.0.7 A2 fix. But should A2 ALSO add C3 worker env
   guard runtime check (raise PreconditionError if any worker-reachable
   code path tries to dispatch interactive skill)? C3 is currently
   v1.0.7+ deferred but logically part of the Windows hybrid story.
   Brainstorming evaluates promote vs defer.

3. **Pillar B subset prioritization (Q3')**: B4 + B5 + B3 all have
   different urgency. B4 (spec-reviewer file-reference) blocks long
   cycles on Windows; B5 (drift detector regex) blocks v1.0.6 own
   test_v104 failure; B3 (atomic_write Windows retry) is one-off
   flake. Order: B4 first (blocks operational), B5 second (test
   failure), B3 third (low priority). Or all parallel if disjoint.

4. **Pillar C cherry-pick scope (Q4')**: 5 items chosen (C1+C5+C6+C7+
   C-X-K3-Removal). C-X-K3-Removal is HARD-LOCKED per v1.0.6
   commitment. C1+C5+C6 are 1-line / docstring-only changes (low
   risk, low value). C7 is doc methodology procedure. Could trim to
   C-X-K3-Removal + C7 only if cycle width tight. Brainstorming evaluates.

5. **MAGI Checkpoint 2 budget allocation (Q5')**: bundle 11 items
   (A1+A2+A3 + B4+B5+B3 + C1+C5+C6+C7+C-X-K3-Removal). Esperamos
   converger en 1-2 iters dado que Pillar A es well-scoped + Pillar B
   are surgical fixes + Pillar C is polish. Iter 3 triggers G2
   scope-trim default. Defer Pillar C polish first; then Pillar B
   subset (B5 first since least operational); only Pillar A A1+A2+A3
   hard-LOCKED.

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4
+v1.0.5+v1.0.6 precedents.
