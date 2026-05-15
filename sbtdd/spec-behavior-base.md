# Especificacion base — sbtdd-workflow v1.0.8 (post-v1.0.7 ship)

> Generado 2026-05-14 a partir de v1.0.7 ship record + v1.0.8 T3 e2e
> diagnostic empirical findings.
>
> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v1.0.8). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado post-v1.0.7 ship (tag `v1.0.7` at commit `b97ed1a`,
> branch `feature/v1.0.8-bundle` branched off `main` HEAD `b97ed1a`).
>
> v1.0.8 = **T3 e2e empirical chicken-and-egg closure (PRIORITY LOCKED)**
> per user mandate 2026-05-10. v1.0.7 production T1+T2 unit tests
> proven (19 PASS) but the T3 end-to-end test (`tests/test_auto_parallel_e2e.py`)
> is xfail-marked because it hangs 600s. Without v1.0.8 closure, the
> `--parallel` operational claim remains: architecture complete,
> unit-level validated, end-to-end UNVALIDATED. Two pillars:
>
> - **Pillar A PRIMARY (HARD-LOCKED CRITICAL)** — T3 e2e test
>   redesign via test-only stub gate. v1.0.8 diagnostic empirically
>   ruled out 4 of 5 v1.0.7 hypotheses; root cause confirmed: worker
>   `_phase2_task_loop` invokes `superpowers_dispatch.test_driven_development(...)`
>   which spawns `claude -p /test-driven-development` — a REAL
>   LLM-driven code-generation call. In production this works; in the
>   v1.0.7 synthetic fixture (lacking `.claude/settings.json` permissions
>   config + `CLAUDE.md`) the call hangs indefinitely (>180s, zero
>   output empirically observed). Test budget (600s) was always too
>   small even without the hang: 4 workers × 3 phases × tens-to-hundreds
>   of seconds per skill call. **Fix**: add a test-only env var
>   `SBTDD_E2E_STUB_DISPATCH` that bypasses `claude -p` dispatch for
>   `_E2E_STUBBABLE_SKILLS` (`/test-driven-development`,
>   `/systematic-debugging`) returning synthetic `SkillResult(rc=0)`.
>   The test sets the env var; production code path is unchanged.
>   This isolates what T3 is supposed to validate (worker chicken-and-egg
>   surface at `/verification-before-completion`) from the cost +
>   upstream bug of the implementer skill dispatch.
>
> - **Pillar B LOCKED (defensive fixture hardening + bug archaeology)** —
>   Two surgical adjuncts to Pillar A:
>   - **B1 fixture hardening**: add minimal `.claude/settings.json`
>     to `tests/fixtures/parallel-e2e/` granting writes to `scratch/`,
>     `tests/`, `src/` so even if the stub is bypassed (e.g. a future
>     test variant), the fixture is "less broken" from the wrapper
>     claude perspective. Doble defensa con Pillar A.
>   - **B2 secondary issue archive**: archive in CLAUDE.md "Known
>     limitations" section + new memory `project_v108_claude_p_hang_upstream.md`
>     the empirically observed `claude -p` cwd-dependent hang
>     (≥180s no output when cwd has `sbtdd/` + `planning/` + no
>     `.claude/settings.json`). Stage the upstream report content
>     (repro instructions + the 3 reproducer scripts) for future
>     submission to `anthropics/claude-code` issue tracker.
>     v1.0.8 does NOT submit the upstream report (deferred to
>     post-v1.0.8 user decision).
>
> Out-of-scope v1.0.8 (rolled forward a v1.0.9+):
> - Submitting the upstream report to `anthropics/claude-code`
>   (Pillar B2 stages the content; actual submission deferred).
> - Re-evaluating whether the stub gate should be promoted to a
>   production worker-mode bypass (decision deferred until v1.1.0
>   --parallel UX review).
> - Carry-forward items from v1.0.7 deferred: B2 worker subprocess
>   auto-message hardening, C2 K-4 escape hatch test coverage, C4
>   NF-B test count rebaseline, C8 F-A2 abort criterion diagnosis
>   hint, Pillar D v1.0.5 polish carry-forward, edge cases E1-E3.
> - All v1.0.4 carry-forward inherited items.
>
> v1.0.8 INV stance: **strict no-INV-0** preserved per Q3=a v1.0.7
> precedent. Goals: preserve 9-cycle Checkpoint 2 no-override streak
> (v1.0.0..v1.0.7 = 8 cycles + v1.0.8 = 9) + preserve pre-merge Loop
> 2 no-override streak (v1.0.5 + v1.0.7 = 2 cycles + v1.0.8 = 3 cycles
> consecutive). G1 cap=3 HARD Checkpoint 2 sin INV-0 path. G2 binding
> pre-staged: scope-trim ladder defers Pillar B2 first → defer Pillar
> B1 second → only Pillar A hard-LOCKED.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6+v1.0.7 frozen se mantiene
> en `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento NO lo
> reemplaza — agrega el delta v1.0.8 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder
> word-boundary verificable con `spec_cmd._INV27_RE` regex.

---

## 1. Objetivo

**v1.0.8 = "T3 e2e empirical closure via test-only stub gate"**:
ships the v1.0.7 PRIORITY LOCKED T3 closure. After v1.0.8:
- T3 e2e test (`tests/test_auto_parallel_e2e.py`) is no longer xfail.
- T3 runs in <60s instead of timing out at 600s.
- T3 validates the **actual chicken-and-egg surface** that v1.0.7 A1+A2
  was designed to close (workers reach `_run_verification` worker-mode
  bypass via sec.0.1 chain, no TTY-dependent hang).
- T3 isolates the validation from the cost + upstream bug of real
  `/test-driven-development` LLM dispatch.

Tres clases de items:

### Clase 1 — Pillar A PRIMARY (HARD-LOCKED)

- **Item A1 — `SBTDD_E2E_STUB_DISPATCH` env var gate in
  `superpowers_dispatch.invoke_skill`**. Add module-level constants
  `_E2E_STUB_ENV` (string `"SBTDD_E2E_STUB_DISPATCH"`) and
  `_E2E_STUBBABLE_SKILLS` (frozenset containing
  `"test-driven-development"` and `"systematic-debugging"`). At the
  top of `invoke_skill`, check env var + skill membership; if both
  match, return `SkillResult(skill=skill, returncode=0,
  stdout=f"[sbtdd e2e stub] /{skill} bypassed (SBTDD_E2E_STUB_DISPATCH=1)",
  stderr="")` immediately. Frozen via `frozenset` (style consistent
  with `_SUBPROCESS_INCOMPATIBLE_SKILLS`). Documented as **test-only**
  in docstring with explicit warning that production callers MUST
  NOT set the env var.

- **Item A2 — Worker env propagation contract preserved**. Verify
  `auto_cmd._dispatch_tracks_concurrent` line 2061 (`worker_env =
  os.environ.copy()`) carries `SBTDD_E2E_STUB_DISPATCH=1` from
  parent test → orchestrator → worker subprocess transparently.
  Add regression test asserting the env var is passed through
  unchanged when set in the parent.

- **Item A3 — T3 e2e test redesign**. Remove `@pytest.mark.xfail`
  from `test_auto_parallel_e2e_chicken_and_egg_closed`. Set
  `SBTDD_E2E_STUB_DISPATCH=1` in the subprocess `env` dict. Shrink
  `_AUTO_TIMEOUT_S` from 600s to 60s. Strengthen assertions from
  permissive workers_reached to:
  - `proc.returncode == 0` (full happy path).
  - `session-state.json` reports `current_phase == "done"`.
  - Plan checkboxes all flipped to `[x]` (no `- [ ]` line-start in
    `planning/claude-plan-tdd.md`).
  - At least one `<pid>-*-verify.json` sidecar exists under
    `.claude/auto-run-workers/` with valid `verify_chain` JSON.
  - At least one git commit per task (4 commits minimum above seed
    SHA; some may be `--allow-empty` per the worker case-3 fallback
    because the stub doesn't write files — explicitly accept this).
  - `auto-run.json` has `auto_finished_at` non-null AND
    `status == "success"`.

- **Item A4 — Regression test for the gate itself**. New test in
  `tests/test_superpowers_dispatch.py` asserting:
  - Gate fires: env var set + skill in stubbable set → returns synthetic
    SkillResult with rc=0 without spawning subprocess (monkeypatch
    `subprocess_utils.run_with_timeout` to raise if called).
  - Gate does NOT fire on production path: env var unset → real path
    attempted (monkeypatch verifies `run_with_timeout` IS called).
  - Gate does NOT fire on skills outside the stubbable set: e.g.,
    `/verification-before-completion` with env var set → real path
    attempted.
  - Gate stdout contains the explicit `[sbtdd e2e stub]` marker so
    test failures can grep for it.

### Clase 2 — Pillar B LOCKED (defensive + archival)

- **Item B1 — Fixture `.claude/settings.json` hardening**. Add
  minimal `.claude/settings.json` to `tests/fixtures/parallel-e2e/`
  granting writes to `scratch/`, `tests/`, `src/` (per claude
  permissions schema). Update `_stage_fixture` helper in
  `test_auto_parallel_e2e.py` to copy it into the staged project.
  Goal: even if the stub gate is bypassed in a future variant,
  the fixture is "less broken" upstream.

- **Item B2 — CLAUDE.md "Known limitations" section + memory
  archive of the upstream bug**. Add a top-level section to
  CLAUDE.md "Known upstream limitations" documenting:
  - Bug: `claude -p /test-driven-development` hangs ≥180s with zero
    output when cwd contains `sbtdd/` + `planning/` files but no
    `.claude/settings.json` and no `CLAUDE.md`.
  - Empirically verified in v1.0.8 diagnostic 2026-05-14 (3
    reproducer scripts in `.tmp_repro/`: `repro_t3.py`,
    `repro_worker.py`, `repro_skill_with_fixture_cwd.py`).
  - Workaround in test: SBTDD_E2E_STUB_DISPATCH (v1.0.8 Pillar A).
  - In production: properly configured projects (with
    `.claude/settings.json` from `/sbtdd init` template) do NOT
    hit this bug.
  - Upstream report content STAGED for future submission to
    `anthropics/claude-code` issue tracker (deferred per v1.0.8
    spec out-of-scope).
  - Create memory `project_v108_claude_p_hang_upstream.md` with
    full repro + diagnostic evidence + decision rationale to
    archive context.

### Clase 3 — v1.0.8 own-cycle dogfood (orchestrator post-impl)

- **Activity D — `make verify` clean pass with new T3 unxfailed**.
  Run `make verify` after Pillar A + B land. T3 should now PASS
  (not xfail). Coverage threshold 88% preserved. Runtime <= 200s
  soft / 220s hard.
- **Activity E — Manual `/sbtdd pre-merge` Loop 1 + Loop 2 end-to-end**.
  Re-establish pre-merge Loop 2 no-override streak (3 cycles
  consecutive after v1.0.8). If `/sbtdd pre-merge` hangs (same
  upstream bug class), fall back to manual `run_magi.py` dispatch
  per v1.0.7 precedent.
- **Activity F — Verify production T1+T2 unit tests still pass**.
  No regression in `test_auto_cmd.py` + `test_parallel_dispatcher.py`
  + `test_close_phase_cmd.py` worker-mode bypass tests (19+ tests
  preserved).

### Criterio de exito v1.0.8

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.7 -> 1.0.8.
- Tests baseline 1304 + 1 skipped preservados + ~5-8 nuevos (Pillar
  A1+A4: ~3-4 gate tests; Pillar A3: T3 unxfailed; Pillar B1: 1
  fixture-file test) = ~1309-1312 final.
- `make verify` runtime <= 200s soft / 220s hard.
- Coverage threshold mantenido en 88% (v1.0.7 measured 89.46%;
  v1.0.8 must not regress below).
- **T3 e2e test PASSES (not xfail)** in <60s when run with
  `SBTDD_E2E_STUB_DISPATCH=1` in the subprocess env. Empirical
  chicken-and-egg closure CONFIRMED end-to-end (workers reach
  `_run_verification` worker-mode bypass, run sec.0.1 chain, exit
  cleanly, parent merges sidecars, plan flips, state advances).
- **G1 binding HARD respetado**: cap=3 HARD para Checkpoint 2; sin
  INV-0. **9-cycle Checkpoint 2 no-override streak goal**
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6+v1.0.7+v1.0.8).
- **Pre-merge Loop 2 streak preservation**: 3 cycles consecutive
  goal (v1.0.5+v1.0.7+v1.0.8 sin INV-0).
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no
  converge — defer Pillar B2 first → defer Pillar B1 second → only
  Pillar A hard-LOCKED.

---

## 2. Alcance v1.0.8 — items LOCKED post-v1.0.7 ship

### 2.1 Item A1 — `SBTDD_E2E_STUB_DISPATCH` env var gate (Pillar A PRIMARY HARD-LOCKED)

**Archivos**:
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (add `_E2E_STUB_ENV` + `_E2E_STUBBABLE_SKILLS` + gate at top of
  `invoke_skill`)
- Extend: `tests/test_superpowers_dispatch.py` (4 new tests per A4)

**Empirical context (v1.0.8 T3 diagnostic 2026-05-14)**:

`tests/test_auto_parallel_e2e_chicken_and_egg_closed` (v1.0.7 A3)
xfail-marked because subprocess timeout at 600s. v1.0.8 diagnostic
empirically traced root cause:

- Worker enters `_phase2_task_loop` ✓ (emits `[sbtdd] phase 2/5: task
  loop -- task 1/4 (red)`)
- Worker invokes `superpowers_dispatch.test_driven_development(args=["--phase=red"], cwd=str(root), stream_prefix=...)`
- That dispatch spawns `claude -p /test-driven-development --phase=red`
  via `subprocess_utils.run_with_timeout(..., stream_prefix=...)`
- The `claude -p` subprocess HANGS (>180s no output) when cwd is the
  fixture temp dir (which has `sbtdd/` + `planning/` files but lacks
  `.claude/settings.json` permissions config + `CLAUDE.md`)
- 4 of 5 v1.0.7 hypotheses ruled out: env propagation works
  (worker received SBTDD_AUTO_PARALLEL_WORKER=1), pytest recursion
  never reached, A2 fix is correct (only for `/verification-before-completion`,
  not implementer), Windows PIPE buffer not full (only 1 line emitted)

**Implementation outline**:

```python
# superpowers_dispatch.py module-level

#: v1.0.8 Pillar A: env var name that activates the test-only
#: stub gate at the top of :func:`invoke_skill`. When set to "1",
#: skills in :data:`_E2E_STUBBABLE_SKILLS` short-circuit to a
#: synthetic :class:`SkillResult` instead of spawning ``claude -p``.
#: Test-only — production callers MUST NOT set this variable.
_E2E_STUB_ENV: str = "SBTDD_E2E_STUB_DISPATCH"

#: v1.0.8 Pillar A: skills whose ``claude -p`` dispatch is bypassed
#: when :data:`_E2E_STUB_ENV` is set. Frozen via ``frozenset`` (style
#: consistent with :data:`_SUBPROCESS_INCOMPATIBLE_SKILLS`).
#: Membership-bound list — adding skills here requires explicit
#: rationale documented in CHANGELOG.
_E2E_STUBBABLE_SKILLS: frozenset[str] = frozenset({
    "test-driven-development",
    "systematic-debugging",
})


def invoke_skill(skill, args=None, ..., allow_interactive_skill=False):
    """... existing docstring + v1.0.8 addendum ..."""
    # v1.0.8 Pillar A1: test-only stub gate. Checked FIRST so it
    # short-circuits ALL downstream dispatch logic (including the
    # v1.0.4 membership gate + v1.0.6 J-3 headless guard + v1.0.7
    # A2 worker-context guard). Test-only: production MUST NOT
    # set SBTDD_E2E_STUB_DISPATCH.
    if (
        os.environ.get(_E2E_STUB_ENV) == "1"
        and skill in _E2E_STUBBABLE_SKILLS
    ):
        return SkillResult(
            skill=skill,
            returncode=0,
            stdout=f"[sbtdd e2e stub] /{skill} bypassed ({_E2E_STUB_ENV}=1)",
            stderr="",
        )
    # ... existing v1.0.7 gate logic preserved unchanged ...
```

### 2.2 Item A2 — Worker env propagation contract preserved (Pillar A)

**Archivos**:
- Verify: `skills/sbtdd/scripts/auto_cmd.py` line 2061
  (`worker_env = os.environ.copy()`)
- Extend: `tests/test_auto_cmd.py` (regression test: parent env
  with `SBTDD_E2E_STUB_DISPATCH=1` propagates to worker env)

**Implementation note**: no code change required — `os.environ.copy()`
already passes all env vars through. The new test pins the contract
so a future refactor that filters env vars would surface the
regression.

### 2.3 Item A3 — T3 e2e test redesign (Pillar A)

**Archivos**:
- Modify: `tests/test_auto_parallel_e2e.py`
  - Remove `@pytest.mark.xfail` decorator
  - Set `env["SBTDD_E2E_STUB_DISPATCH"] = "1"` in subprocess `env`
    dict; preserve full `os.environ.copy()` baseline so claude /
    git / pytest / ruff / mypy stay discoverable on PATH
  - Shrink `_AUTO_TIMEOUT_S` from 600 to 60
  - Strengthen assertions per criterio in sec.1 Item A3
  - Update test docstring + xfail comment removal

**Acceptance**: T3 runs in <60s, asserts full happy path, passes
reliably on Windows + POSIX (POSIX deferred to CI per v1.0.7 W5
carry-forward).

### 2.4 Item A4 — Gate regression tests (Pillar A)

**Archivos**:
- Extend: `tests/test_superpowers_dispatch.py` (4 new tests)

**Test class layout**:

```python
class TestE2EStubGate:
    """v1.0.8 Pillar A4: regression tests for SBTDD_E2E_STUB_DISPATCH gate."""

    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """Env=1 + skill in set -> stub returns rc=0 without subprocess."""

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """Env unset -> real path attempted (monkeypatched to error)."""

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """Env=1 + skill NOT in set (e.g. verification-before-completion) ->
        real path attempted."""

    def test_gate_stdout_contains_marker(self):
        """Stub returns explicit '[sbtdd e2e stub]' marker for grepping."""
```

### 2.5 Item B1 — Fixture `.claude/settings.json` hardening (Pillar B)

**Archivos**:
- Create: `tests/fixtures/parallel-e2e/dot-claude-settings.json`
  (must be staged into `.claude/settings.json` by the test helper
  — `.claude/` itself is gitignored, so we ship under a discoverable
  filename and the staging helper renames during copy)
- Modify: `tests/test_auto_parallel_e2e.py::_stage_fixture` to copy
  the dot-claude-settings.json into `<dest>/.claude/settings.json`
- Extend: `tests/test_auto_parallel_e2e.py::test_fixture_files_present`
  to also assert the new fixture file exists

**Content** (`dot-claude-settings.json`):

```json
{
  "permissions": {
    "allow": [
      "Write(scratch/**)",
      "Edit(scratch/**)",
      "Write(tests/**)",
      "Edit(tests/**)",
      "Write(src/**)",
      "Edit(src/**)",
      "Bash(pytest *)",
      "Bash(ruff *)",
      "Bash(mypy *)"
    ]
  }
}
```

### 2.6 Item B2 — Upstream bug archive (Pillar B)

**Archivos**:
- Modify: `CLAUDE.md` (project root) — add new section "Known upstream
  limitations" with documented bug + repro context + workaround
  (cross-referenced to v1.0.8 Pillar A)
- Create: memory `project_v108_claude_p_hang_upstream.md` with full
  diagnostic context + repro instructions + stagad upstream report
  content (NOT submitted in v1.0.8)
- Modify: `CHANGELOG.md` `[1.0.8]` "Deferred" section explicitly
  lists the upstream report submission as deferred

**Content** (CLAUDE.md "Known upstream limitations" section):

```markdown
## Known upstream limitations

### claude -p /test-driven-development hangs in fixture-style cwd

**Manifest**: invoking `claude -p /test-driven-development --phase=red`
as a subprocess with cwd pointing to a directory that contains
`sbtdd/spec-behavior.md` + `planning/claude-plan-tdd.md` but lacks
`.claude/settings.json` + `CLAUDE.md` causes the subprocess to hang
indefinitely (>180s empirically observed, zero stdout/stderr output)
before timeout-killed by the caller.

**Repro context**: empirically verified in v1.0.8 T3 diagnostic
2026-05-14 across 3 reproducer scripts. Same command in cwd=empty
temp dir returns rc=0 in ~30s with sensible "working directory is
empty" output; same command in cwd=SBTDD repo dir returns rc=0 in
~66s with sensible "plan already complete, ready for next test"
output. Bug is cwd-dependent on a specific combination of files
without permission config.

**Workaround**: `tests/test_auto_parallel_e2e.py` uses
`SBTDD_E2E_STUB_DISPATCH=1` to bypass the dispatch entirely
(v1.0.8 Pillar A1). In production, properly-initialized SBTDD
projects (via `/sbtdd init`) have a complete `.claude/settings.json`
that grants the permissions the implementer skill needs, avoiding
the hang.

**Upstream**: report content STAGED in `project_v108_claude_p_hang_upstream.md`
memory for future submission to `anthropics/claude-code`. v1.0.8
does NOT submit — deferred to user decision post-v1.0.8 ship.
```

### 2.7 v1.0.8 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B ship).

**Activities**:
1. **D `make verify` clean pass** (NON-NEGOTIABLE): tests 1304 + 1
   skipped + ~5-8 new = ~1309-1312, coverage >= 88%, runtime <= 200s
   soft / 220s hard. T3 unxfailed and PASSES.
2. **E `/sbtdd pre-merge` end-to-end**: re-establish 3-cycle Loop 2
   no-override streak.
3. **F production T1+T2 regression check**: 19 worker-mode bypass
   tests still pass.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.8 NO propone
nuevos invariantes (todos los items son test infrastructure +
documentation).

Critical durante implementacion v1.0.8:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  9-cycle Checkpoint 2 no-override streak goal preserved
  (v1.0.0..v1.0.8). NO INV-0 override en Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.8 bundle podria necesitar scope-trim si Loop 2 hits structural
  findings — defer Pillar B2 first (low-cost archival) → defer
  Pillar B1 second (defensive but not blocking) → Pillar A
  hard-LOCKED.
- **Pre-merge Loop 2 streak preservation**: v1.0.5 + v1.0.7 = 2 cycles
  no-override. v1.0.8 goal = 3 cycles consecutive sin INV-0.
- **Production semantics preservation NON-NEGOTIABLE**: Pillar A is
  TEST-ONLY. The new env var MUST NOT change production worker
  behavior. Any pre-merge finding suggesting the stub be promoted
  to production worker-mode bypass is OUT-OF-SCOPE — rejected via
  `/receiving-code-review` with explicit rationale (production
  workers should do real TDD work; bypassing implementer dispatch
  would break the `--parallel` semantic contract).

### Stack y runtime

Sin cambios vs v1.0.7:
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
  v1.0.0..v1.0.7 = 8-cycle no-override streak; v1.0.8 preserves to 9).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F212 v1.0.7; v1.0.8 starts at F213.)

### Item A1 — Env var stub gate

**F213**. New module-level constants in `superpowers_dispatch.py`:
`_E2E_STUB_ENV` (string `"SBTDD_E2E_STUB_DISPATCH"`) +
`_E2E_STUBBABLE_SKILLS` (frozenset of `{"test-driven-development",
"systematic-debugging"}`).

**F214**. New gate at top of `invoke_skill`: checks
`os.environ.get(_E2E_STUB_ENV) == "1"` AND `skill in
_E2E_STUBBABLE_SKILLS`; if both true, returns
`SkillResult(skill=skill, returncode=0, stdout=f"[sbtdd e2e stub]
/{skill} bypassed ({_E2E_STUB_ENV}=1)", stderr="")` without spawning
subprocess.

**F215**. Gate is the FIRST check in `invoke_skill` — short-circuits
the v1.0.4 membership gate, the v1.0.6 J-3 headless guard, and the
v1.0.7 A2 worker-context guard. Documented in docstring as test-only.

### Item A2 — Worker env propagation

**F216**. `_dispatch_tracks_concurrent` line 2061 (`worker_env =
os.environ.copy()`) preserves `SBTDD_E2E_STUB_DISPATCH` env var from
parent process unchanged. No code change — regression test pins
the contract.

### Item A3 — T3 e2e test redesign

**F217**. `test_auto_parallel_e2e_chicken_and_egg_closed` decorator
list no longer contains `@pytest.mark.xfail`. Test asserts strict
happy path (rc=0, state=done, plan flipped, sidecars present, audit
trail valid).

**F218**. `_AUTO_TIMEOUT_S` shrunken from 600 to 60.

**F219**. Subprocess env dict includes `SBTDD_E2E_STUB_DISPATCH=1`
in addition to the inherited `os.environ.copy()` baseline.

### Item A4 — Gate regression tests

**F220**. 4 new tests in `tests/test_superpowers_dispatch.py`
class `TestE2EStubGate` validating gate firing semantics +
production path preservation.

### Item B1 — Fixture hardening

**F221**. `tests/fixtures/parallel-e2e/dot-claude-settings.json`
shipped with permissions schema enabling writes to scratch/, tests/,
src/ + bash invocations for pytest/ruff/mypy.

**F222**. `_stage_fixture` helper in `test_auto_parallel_e2e.py`
renames-on-copy to `<dest>/.claude/settings.json` so the fixture
ships under a non-dotfile name (gitignore-safe) but lands as a
proper dotfile in the staged tree.

### Item B2 — Upstream bug archive

**F223**. New "Known upstream limitations" section in `CLAUDE.md`
documenting the empirically-observed claude -p hang + workaround
+ deferred upstream report.

**F224**. New memory `project_v108_claude_p_hang_upstream.md`
archiving full diagnostic context + repro scripts + staged upstream
report content.

**F225**. `CHANGELOG.md` `[1.0.8]` "Deferred" section lists
upstream report submission as deferred to user decision
post-v1.0.8 ship.

### Requerimientos no-funcionales (NF)

**NF59**. `make verify` runtime <= 200s soft target / 220s hard
(unchanged from v1.0.7 NF53).

**NF60**. v1.0.7 plans + state files parse correctly; no migration
required for v1.0.8.

**NF61**. Per-module coverage threshold preserved at 88% (no
regression).

**NF62**. v1.0.8 own-cycle dogfood `make verify` clean with T3 PASS
(not xfail).

**NF63**. v1.0.8 ship WITHOUT INV-0 override at pre-merge Loop 2
(3-cycle streak goal: v1.0.5+v1.0.7+v1.0.8).

**NF64**. v1.0.8 ship WITHOUT INV-0 override at Checkpoint 2
(9-cycle streak goal: v1.0.0..v1.0.8).

---

## 5. Scope exclusions

Out-of-scope v1.0.8 (rolled forward a v1.0.9+):

- Upstream report submission to `anthropics/claude-code` (Pillar B2
  stages content; user decides post-v1.0.8 ship)
- Promoting the stub gate to production worker-mode bypass (decision
  deferred until v1.1.0 --parallel UX review)
- v1.0.7 deferred carry-forward: B2 worker subprocess auto-message
  hardening, C2 K-4 escape hatch test coverage, C3 F-A2 worker env
  guard (folded into A2 in v1.0.7), C4 NF-B test count rebaseline,
  C8 F-A2 abort criterion diagnosis hint
- Pillar D items (5 v1.0.5 polish carry-forward not addressed in
  v1.0.6/v1.0.7)
- Edge cases E1-E3

Out-of-scope v1.0.8+ (rolled forward a v1.1.0):

- All v1.0.4 carry-forward inherited items (`agreement_rate` rename,
  `spec_lint` R3 promote, per-module coverage 85%, GitHub Actions CI
  workflow, Migration tool real test, AST dead-helper detector
  codification, W8 Windows fs retry-loop, `_read_auto_run_audit`
  skeleton wiring, spec sec.7.1.3 G2 amendment, `magi_cross_check`
  default-flip, Group B options 1/3/4/6/7) — defer to v1.1.0 cycle.

---

## 6. Criterios de aceptacion finales

v1.0.8 ship-ready cuando:

### 6.1 Functional Items A1+A2+A3+A4 + B1+B2

- **F1**. F213-F215 (A1): env var stub gate at top of `invoke_skill`
  short-circuiting `claude -p` dispatch for stubbable skills.
- **F2**. F216 (A2): worker env propagation regression test passes;
  no production code change.
- **F3**. F217-F219 (A3): T3 e2e test redesigned, no longer xfail,
  passes in <60s with strict happy-path assertions.
- **F4**. F220 (A4): 4 new gate regression tests pass.
- **F5**. F221-F222 (B1): fixture ships `.claude/settings.json`
  with permissions; staging helper copies it correctly.
- **F6**. F223-F225 (B2): CLAUDE.md "Known upstream limitations"
  section added; new memory archived; CHANGELOG deferred list
  updated.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s
  hard.
- **NF-B**. Tests baseline 1304 + 1 skipped + ~5-8 nuevos =
  ~1309-1312 final. T3 e2e PASSES (not xfail).
- **NF-C**. Cross-platform (Windows + POSIX): gate semantics
  platform-agnostic; T3 runs on Windows (mandatory) + POSIX
  (deferred to CI per W5 carry-forward).
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados (Pillar A: `superpowers_dispatch.py`,
  `test_superpowers_dispatch.py`, `test_auto_parallel_e2e.py`,
  `test_auto_cmd.py`; Pillar B: `tests/fixtures/parallel-e2e/dot-claude-settings.json`,
  `CLAUDE.md`, `CHANGELOG.md`).

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**.
  9-cycle Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (3-cycle streak goal: v1.0.5+v1.0.7+v1.0.8). If unable to
  converge cleanly within cap=5: escalate to user BEFORE applying
  INV-0.
- **P3**. CHANGELOG `[1.0.8]` entry written con secciones Added /
  Changed / Process notes / Deferred + Pillar A A1+A2+A3+A4 +
  Pillar B B1+B2 + dogfood findings + claim that v1.0.7 T3 e2e
  empirical gap closed.
- **P4**. Version bump 1.0.7 -> 1.0.8 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.8` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. v1.0.8 own-cycle dogfood: T3 unxfailed + PASSES in <60s
  with real chicken-and-egg surface validation (workers reach
  `_run_verification` worker-mode bypass via sec.0.1 chain, no TTY
  hang). All v1.0.7 T1+T2 production unit tests still pass.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.8 ship + items +
  T3 empirical closure).
- **D3**. Documented:
  - `SBTDD_E2E_STUB_DISPATCH` env var in `superpowers_dispatch.py`
    docstring + README operational notes + SKILL.md v1.0.8 notes
    (as test-only, with explicit warning).
  - CLAUDE.md "Known upstream limitations" section.
  - CHANGELOG `[1.0.8]` Deferred section lists upstream report
    submission.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.8

- **R1**. Stub gate could mask future regressions in real
  `/test-driven-development` dispatch path (since T3 no longer
  exercises it). Mitigation: production T1+T2 unit tests in
  `test_auto_cmd.py` + `test_close_phase_cmd.py` continue to
  exercise the dispatch path with real (non-stub) skill invocations
  at unit level. T3 explicitly validates the dispatch INFRASTRUCTURE
  (env propagation, sidecar persistence, parent-side hooks) not the
  skill internals.
- **R2**. Env var name `SBTDD_E2E_STUB_DISPATCH` could be set
  accidentally in production. Mitigation: namespace `SBTDD_E2E_*`
  signals test-only intent; docstring explicit warning; documented
  in CLAUDE.md + SKILL.md + README; gate fires only for the
  narrowly-scoped `_E2E_STUBBABLE_SKILLS` set (production
  `/verification-before-completion` path NOT affected even if env
  var is set).
- **R3**. Pillar A4 regression tests might monkeypatch
  `invoke_skill` itself instead of the dispatch path, breaking the
  gate test semantic. Mitigation: tests monkeypatch
  `subprocess_utils.run_with_timeout` at the bottom of the call
  chain so the gate at top of `invoke_skill` is exercised
  end-to-end (real invoke_skill execution; only the subprocess
  call is faked).
- **R4**. Fixture `.claude/settings.json` schema could become
  inconsistent with upstream Claude Code permissions format if the
  format evolves. Mitigation: fixture schema kept minimal +
  documented in spec; periodic re-validation in v1.1.0+ cycle.
- **R5**. Upstream bug archive (B2) could become stale if
  `anthropics/claude-code` fixes the hang upstream without us
  noticing. Mitigation: memory `project_v108_claude_p_hang_upstream.md`
  scheduled for v1.1.0 re-check; if fixed, B2 can be archived (but
  the test stub stays as cinturon de seguridad).

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.7 ship record: tag `v1.0.7` (commit `b97ed1a`); branch
  `feature/v1.0.8-bundle` branched off `main` HEAD `b97ed1a`.
- v1.0.8 PRIORITY LOCKED memory: `project_v108_t3_e2e_priority_locked.md`
  (full v1.0.7 T3 xfail context + 5-hypothesis prioritization).
- v1.0.8 diagnostic reproducer scripts in `.tmp_repro/` (gitignored):
  - `repro_t3.py` — full subprocess via test path
  - `repro_worker.py` — single worker direct spawn
  - `repro_skill_with_fixture_cwd.py` — claude -p with cwd=fixture
- v1.0.9 deferred backlog: upstream report submission + v1.0.7
  carry-forward items.
- v1.1.0 deferred backlog: all v1.0.4 carry-forward inherited items
  + stub gate production-promotion decision review.

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.8 own-cycle**: per CLAUDE.local.md sec.1 Flujo
de especificacion + v1.0.7 Process notes precedent, brainstorming
se correra en sesion interactiva (esta sesion) via Skill tool
in-session. NO via `claude -p` subprocess (chicken-and-egg until
v1.0.8 Pillar A lands + v1.0.9 own-cycle validates).

**Hybrid methodology continued**: Opcion A manual `run_magi.py`
for Checkpoint 2 + Loop 2 dispatch per v1.0.2..v1.0.7 precedent.
Once v1.0.8 Pillar A lands, future cycles can attempt subprocess
path (`/sbtdd spec` + `/sbtdd pre-merge` end-to-end) but only if
the chicken-and-egg hang upstream bug is also resolved.

Decisiones pendientes clave para brainstorming (Q1'-Q5' estimated):

1. **Stub gate scope (Q1')**: `_E2E_STUBBABLE_SKILLS` = exactly
   `{"test-driven-development", "systematic-debugging"}`?
   - **a (baseline)**: 2-skill set as specified. Minimal scope.
   - **b**: extend to include `/brainstorming` and `/writing-plans`
     (they're also v1.0.4-membership-gated and could be useful in
     future spec-flow e2e tests).
   Brainstorming evaluates a vs b trade-off.

2. **Stub stdout content (Q2')**: how detailed should the synthetic
   `SkillResult.stdout` be?
   - **a (baseline)**: minimal marker `[sbtdd e2e stub] /{skill}
     bypassed`. Grepable but no semantic content.
   - **b**: include skill args + cwd + timestamp for richer audit
     trail. Useful for failure-mode debugging.
   Brainstorming evaluates a vs b.

3. **Fixture settings.json permissions (Q3')**: how broad should
   the permissions be?
   - **a (baseline)**: scratch/, tests/, src/ + bash for
     pytest/ruff/mypy. Matches minimum needed for fixture.
   - **b**: add `**` wildcard for full read/write everywhere.
     Liberal but matches what real `/sbtdd init` projects get.
   Brainstorming evaluates trade-offs.

4. **T3 assertion strictness (Q4')**: how strict should the new
   T3 assertions be?
   - **a (baseline)**: strict happy path (rc=0, state=done, plan
     flipped, sidecars present). Matches spec sec.2.3.
   - **b**: even stricter — assert exact commit count (4 per task
     phase = 12 commits), assert sidecar `verify_chain` contains
     all 4 tools.
   Brainstorming evaluates whether overly-strict assertions
   introduce flakiness.

5. **MAGI Checkpoint 2 budget allocation (Q5')**: small bundle
   (4 Pillar A items + 2 Pillar B items = 6 total). Expect
   convergence in 1-2 iters. Iter 3 triggers G2 scope-trim default
   (defer B2 first since archival-only → defer B1 second since
   defensive → Pillar A hard-LOCKED).

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0..v1.0.7 precedents.
