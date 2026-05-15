# v1.0.8 Implementation Plan (pre-MAGI Checkpoint 2 draft)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar la brecha empirica de v1.0.7 T3 e2e (xfail con 600s timeout) via un env var stub gate test-only en `superpowers_dispatch.invoke_skill`, mas hardening defensivo del fixture, mas archivo del bug upstream de claude -p para reporte futuro.

**Architecture:** Una sola modificacion funcional en produccion (gate al top de `invoke_skill` short-circuiting claude -p dispatch cuando env var `SBTDD_E2E_STUB_DISPATCH=1` AND skill in `_E2E_STUBBABLE_SKILLS={"test-driven-development","systematic-debugging"}`) + 5 adjuntos de tests/docs/fixture/changelog. Test-only por contrato: namespaced env var, frozen membership set, docstring + multiple cross-refs documentando test-only intent.

**Tech Stack:** Python 3.9+, pytest, ruff, mypy --strict, `subprocess.run`/`subprocess.Popen`, JSON. Plugin runtime: claude CLI, git, tdd-guard, superpowers + magi plugins. SBTDD methodology: TDD strict Red/Green/Refactor per task via `/sbtdd close-phase`, `/sbtdd close-task` automaticos bajo plan-approved contract.

**Reference docs:**
- Spec: `sbtdd/spec-behavior.md` v1.0.8 (escenarios A1-1..A1-5, A2-1..A2-2, A3-1..A3-4, A4-1..A4-3, B1-1..B1-3, B2-1..B2-4)
- Spec-base: `sbtdd/spec-behavior-base.md` v1.0.8 (Q1'-Q5' decisiones + risk register R1-R7)
- Rules: `~/.claude/CLAUDE.md` (global, absolute precedence — INV-0) + `CLAUDE.local.md` (project, sec.5 commit prefixes + sec.3 TDD enforcement)

**Execution mode:** Single-track sequential subagent per CLAUDE.local.md §5.1 (chicken-and-egg precedent v1.0.6+v1.0.7). MAGI Checkpoint 2 may revise to 2-3 track parallel; until then assume sequential.

**Task ordering (strict):**
- T1 (A1 gate) must complete before T3 (A4 tests) and T4 (A3 e2e) — they depend on the gate existing.
- T5 (B1 fixture) must complete before T4 (A3 e2e) — e2e test stages the fixture file.
- T2 (A2 env propagation), T5 (B1), T6 (B2) are disjoint from T1/T3/T4; may parallelize if MAGI approves.

**Red-phase commit methodology (iter-2 carry-forward Mel-W3+Cas-W9 resolution):**

Red phases introduce intentionally-failing tests. The standard close-phase invocation runs sec.0.1 verification (pytest + ruff + mypy) BEFORE committing, which aborts on the new failing test. Per iter-2 carry-forward, the v1.0.7 workaround pattern (temporary `@pytest.mark.xfail` marker added in Red, removed in Green) is REPLACED with a cleaner pattern:

- **Red commit**: use raw `git commit -m "test: <message>"` (NOT `/sbtdd close-phase`). Per CLAUDE.local.md §5 "Excepcion bajo plan aprobado" the `test:` prefix is authorized for TDD Red close under the plan-approved auto-commit contract. State file (`current_phase`) is NOT advanced by the Red commit — it stays at `red`.
- **Green commit**: use `/sbtdd close-phase --variant {feat|fix} --message "..."`. The Green test (now passing because impl exists) is verified by close-phase's sec.0.1 chain, then committed with `feat:` / `fix:` prefix, and state advances to `refactor`.
- **Refactor commit**: use `/sbtdd close-phase --message "..."`. Refactor verified clean, committed with `refactor:` prefix, cascade into close-task (marks plan checkbox `[x]`, commits `chore:`, advances state to next task `red` or to `done`).

This methodology adjustment applies to ALL tasks T1-T6 wherever a Red phase introduces a failing test. No `@pytest.mark.xfail` temporary markers are used. The advantage: no policy escape hatch hits the v1.0.5 `_preflight` HARD-BLOCK on empty phases, and there is no brittle 6-commit window where a stale marker could survive past Green.

**TDD-Guard toggle during Green write window (iter-2 carry-forward Cas-W4+Cas-W7 resolution):**

The raw-git-commit-for-Red methodology has a known interaction with TDD-Guard: because the Red commit does NOT advance `current_phase` past `red`, any subsequent Green-phase Write/Edit to **non-test production code** (e.g., gate impl in `superpowers_dispatch.py`, docstring extension in `auto_cmd.py`, CLAUDE.md/CHANGELOG edits) WILL trip TDD-Guard's PreToolUse hook (per CLAUDE.local.md §3 "Codigo de produccion BLOCKED" under state=red).

**Required operator action**: BEFORE the first Green-phase Write/Edit to non-test code, the operator MUST issue the prompt `tdd-guard off` to disable TDD-Guard enforcement for the Green window. AFTER `/sbtdd close-phase --variant {feat|fix}` completes (which advances state to `refactor`), the operator MUST issue `tdd-guard on` to restore enforcement. Refactor + close-task phases run under state=`refactor` or beyond, so TDD-Guard's doc-comment-allowed rule kicks in naturally.

**Tasks affected**: T1 (gate impl in `superpowers_dispatch.py`), T2 (docstring + inline comment in `auto_cmd.py`), T5 (new fixture `dot-claude-settings.json`), T6 (CLAUDE.md + CHANGELOG.md edits). T3 (test class only — `tests/test_superpowers_dispatch.py`) and T4 (test redesign only — `tests/test_auto_parallel_e2e.py`) are unaffected because their Green-phase edits are to test files (TDD-Guard allows under state=red).

This pattern is well-precedented in CLAUDE.local.md §3 "TDD-Guard bajo ejecucion multi-agente" (operator toggle for parallel execution windows). The toggle is session-scope via the `UserPromptSubmit` hook; subagents CANNOT toggle it themselves — only the operator (human + main session) can.

---

## Task 1: A1 — `SBTDD_E2E_STUB_DISPATCH` env var stub gate

**Goal:** Add a test-only short-circuit at the top of `superpowers_dispatch.invoke_skill` so that when env var `SBTDD_E2E_STUB_DISPATCH=1` AND skill is in `_E2E_STUBBABLE_SKILLS`, the function returns synthetic `SkillResult(rc=0)` without spawning `claude -p`. Production semantics MUST NOT change.

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (add 2 module constants after `_SUBPROCESS_INCOMPATIBLE_SKILLS` at line ~79; add gate as FIRST check in `invoke_skill` body at line ~322; extend docstring of `invoke_skill`)
- Test: `tests/test_superpowers_dispatch.py` (add 1 smoke test of the gate firing; expanded suite comes in T3)

**Spec mapping:** Escenario A1-1 (gate fires for stubbable skill with env set), A1-5 (gate position is FIRST in invoke_skill body)

- [ ] **Step 1: Read current `invoke_skill` signature + first guard block to identify exact insertion point**

Read `skills/sbtdd/scripts/superpowers_dispatch.py` lines 308-370. The current FIRST guard is the v1.0.7 A2 worker-context check (lines ~348-360). The new v1.0.8 A1 gate goes BEFORE that, immediately after the function signature + docstring.

Run: `grep -n "_SUBPROCESS_INCOMPATIBLE_SKILLS\|^def invoke_skill" skills/sbtdd/scripts/superpowers_dispatch.py`
Expected output: line numbers of the existing constant + function definition, confirming insertion targets.

- [ ] **Step 2: Write the failing Red test**

Append the following test to `tests/test_superpowers_dispatch.py` immediately after the existing test class definitions (around line ~860):

```python
# ---------------------------------------------------------------------------
# v1.0.8 Pillar A1: SBTDD_E2E_STUB_DISPATCH env var stub gate smoke test.
# Expanded gate regression suite lives in TestE2EStubGate (added by T3/A4).
# ---------------------------------------------------------------------------


def test_v108_a1_gate_smoke_test_driven_development_with_env_set(monkeypatch):
    """v1.0.8 A1-1 smoke: gate fires for /test-driven-development with env=1.

    Pins the minimum contract that T3 (A4 regression suite) expands on:
    when SBTDD_E2E_STUB_DISPATCH=1 AND "pytest" in sys.modules AND
    skill is stubbable, invoke_skill returns synthetic
    SkillResult(rc=0) WITHOUT spawning claude -p.

    Note: ``"pytest" in sys.modules`` is True by construction in this
    test because pytest is the runner; iter-2 carry-forward W11
    production safeguard does not interfere with test environments.
    """
    import sys
    import superpowers_dispatch
    from superpowers_dispatch import SkillResult

    # Sanity-check the pytest sys.modules runtime guard precondition
    # holds in this test environment (would fail in production where
    # pytest is not loaded).
    assert "pytest" in sys.modules, (
        "test environment must have pytest loaded for the gate to fire"
    )

    monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

    def _fail_if_called(*args, **kwargs):
        raise AssertionError(
            "v1.0.8 A1 regression: gate should have fired before "
            "subprocess_utils.run_with_timeout was reached"
        )

    monkeypatch.setattr(
        superpowers_dispatch.subprocess_utils,
        "run_with_timeout",
        _fail_if_called,
    )

    result = superpowers_dispatch.invoke_skill(
        "test-driven-development",
        args=["--phase=red"],
        allow_interactive_skill=True,
    )

    assert isinstance(result, SkillResult)
    assert result.returncode == 0
    assert result.skill == "test-driven-development"
    assert "[sbtdd e2e stub]" in result.stdout
    assert "test-driven-development" in result.stdout
    assert "SBTDD_E2E_STUB_DISPATCH=1" in result.stdout
    assert result.stderr == ""
```

- [ ] **Step 3: Run the Red test to verify it fails**

Run: `pytest tests/test_superpowers_dispatch.py::test_v108_a1_gate_smoke_test_driven_development_with_env_set -v`

Expected: FAIL with `AssertionError: v1.0.8 A1 regression: gate should have fired...` (because the gate doesn't exist yet, so `invoke_skill` falls through to `run_with_timeout` which we patched to raise).

- [ ] **Step 4: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the Red phase test fails by design (gate doesn't exist yet), so close-phase verification would abort. Use raw git commit instead. State file stays at `current_phase=red`.

```bash
git add tests/test_superpowers_dispatch.py
git commit -m "test: v1.0.8 T1 Red — smoke test for SBTDD_E2E_STUB_DISPATCH gate"
```

Expected: Commit recorded; `git status` clean; `.claude/session-state.json` `current_phase` unchanged (still `red`).

- [ ] **Step 5: Write the Green implementation — module constants**

Add the following two module-level constants in `skills/sbtdd/scripts/superpowers_dispatch.py` IMMEDIATELY AFTER the existing `_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset(...)` block (currently ending around line 90):

```python
#: v1.0.8 Pillar A1: env var name that activates the test-only stub
#: gate at the top of :func:`invoke_skill`. When set to ``"1"``,
#: skills in :data:`_E2E_STUBBABLE_SKILLS` short-circuit to a
#: synthetic :class:`SkillResult` instead of spawning ``claude -p``,
#: PROVIDED ``"pytest"`` is in :data:`sys.modules` (runtime guard
#: against accidental production env var leak — see iter-2 carry-
#: forward W11).
#:
#: **Test-only**: production callers MUST NOT set this variable.
#: Defense-in-depth: even if the env var is accidentally exported in
#: a production context (shared shell profile, devcontainer template
#: leak, accidentally-committed `.env`), the runtime guard in
#: :func:`invoke_skill` checks ``"pytest" in sys.modules`` —
#: production workers do NOT import pytest at runtime (they invoke
#: pytest as a separate subprocess via
#: ``[sys.executable, "-m", "pytest"]`` in
#: :func:`close_phase_cmd._run_verification` worker-mode bypass),
#: so the gate cannot fire in production. Test runners load pytest
#: into sys.modules BEFORE collecting tests, so the gate fires
#: correctly in test environments.
_E2E_STUB_ENV: str = "SBTDD_E2E_STUB_DISPATCH"

#: v1.0.8 Pillar A1: skills whose ``claude -p`` dispatch is bypassed
#: when :data:`_E2E_STUB_ENV` is set AND ``"pytest"`` is loaded.
#: Frozen via ``frozenset`` (style consistent with
#: :data:`_SUBPROCESS_INCOMPATIBLE_SKILLS`).
#:
#: Membership-bound list — adding skills here requires explicit
#: rationale documented in CHANGELOG and approval through MAGI
#: Checkpoint 2 / pre-merge gate. v1.0.8 baseline scope is 2 skills
#: per Q1'=a decision: ``/test-driven-development`` (root cause of
#: the v1.0.7 T3 hang) + ``/systematic-debugging`` (used in
#: ``_run_verification_with_retries`` retry path; would surface the
#: same upstream bug class on a real verification failure).
_E2E_STUBBABLE_SKILLS: frozenset[str] = frozenset(
    {
        "test-driven-development",
        "systematic-debugging",
    }
)
```

- [ ] **Step 6: Write the Green implementation — gate at top of `invoke_skill`**

Insert the gate block IMMEDIATELY AFTER the `invoke_skill` function signature + docstring closing `"""`, BEFORE the existing v1.0.7 A2 worker-context check (currently the first guard at line ~348). The new gate must be the very first executable statement.

The gate has **three conjunctive conditions** (per iter-2 carry-forward W11+W7 combined fix):
1. `os.environ.get(_E2E_STUB_ENV) == "1"` — env var set
2. `"pytest" in sys.modules` — runtime guard against accidental env var leak in production
3. `skill in _E2E_STUBBABLE_SKILLS` — frozen membership

Locate the docstring end. After the docstring, insert (before any existing code):

```python
    # v1.0.8 Pillar A1: test-only stub gate. Checked FIRST so it
    # short-circuits ALL downstream dispatch logic (v1.0.4 membership
    # gate + v1.0.6 J-3 headless guard + v1.0.7 A2 worker-context
    # guard). Test-only: production MUST NOT set
    # SBTDD_E2E_STUB_DISPATCH. Defense-in-depth: the
    # ``"pytest" in sys.modules`` runtime guard ensures the gate
    # cannot fire in production processes (orchestrator, workers)
    # because they do NOT import pytest at runtime; pytest is
    # spawned as a separate subprocess via [sys.executable, "-m",
    # "pytest"] in worker-mode close-phase. Test runners load
    # pytest into sys.modules at process start. Rationale: enables
    # end-to-end orchestration tests (T3 e2e) without spawning
    # real claude -p subprocess (which hangs upstream in fixture-
    # style cwd per CLAUDE.md "Known upstream limitations").
    if (
        os.environ.get(_E2E_STUB_ENV) == "1"
        and "pytest" in sys.modules
        and skill in _E2E_STUBBABLE_SKILLS
    ):
        return SkillResult(
            skill=skill,
            returncode=0,
            stdout=f"[sbtdd e2e stub] /{skill} bypassed ({_E2E_STUB_ENV}=1)",
            stderr="",
        )
```

Verify `import sys` is already present at the top of `superpowers_dispatch.py` (it is, used by `_sys.stderr.write` calls elsewhere — check via `grep -n "^import sys\|^from sys" skills/sbtdd/scripts/superpowers_dispatch.py`). If somehow missing, add `import sys` to the import block.

- [ ] **Step 7: Run the Green test to verify it passes**

Run: `pytest tests/test_superpowers_dispatch.py::test_v108_a1_gate_smoke_test_driven_development_with_env_set -v`
Expected: PASS.

Run: `pytest tests/test_superpowers_dispatch.py -v` (full module)
Expected: all existing tests still pass; new smoke test passes; no regressions.

Run: `make verify` for full sec.0.1 chain.
Expected: pytest all pass, ruff check clean, ruff format clean, mypy strict clean.

- [ ] **Step 8: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T1 Green: add SBTDD_E2E_STUB_DISPATCH env var stub gate to invoke_skill"`

Expected: commit with `feat:` prefix; state advances to `refactor`.

- [ ] **Step 9: Write the Refactor — extend `invoke_skill` docstring**

Modify the `invoke_skill` docstring in `skills/sbtdd/scripts/superpowers_dispatch.py` to document the new gate including gate precedence rationale (iter-2 carry-forward Mel-I2) + pytest sys.modules guard explanation (iter-2 carry-forward Cas-W11). Locate the docstring section that mentions v1.0.7 A2 (around line ~337-347). After that paragraph and BEFORE the `Args:` or `Returns:` section, add:

```
    v1.0.8 Pillar A1: test-only stub gate. When env var
    :data:`_E2E_STUB_ENV` (``SBTDD_E2E_STUB_DISPATCH``) is set to
    ``"1"`` AND ``"pytest"`` is in :data:`sys.modules` AND
    ``skill`` is in :data:`_E2E_STUBBABLE_SKILLS`
    (``test-driven-development`` or ``systematic-debugging``), this
    function short-circuits to a synthetic ``SkillResult(rc=0)``
    without spawning ``claude -p``. The gate is checked FIRST so it
    short-circuits ALL downstream dispatch logic.

    Gate precedence (iter-2 carry-forward Mel-I2): the v1.0.8 A1
    stub gate is positioned BEFORE the v1.0.7 A2 worker-context
    guard, the v1.0.6 J-3 headless guard, and the v1.0.4
    membership gate. When both ``SBTDD_E2E_STUB_DISPATCH=1`` AND
    ``SBTDD_AUTO_PARALLEL_WORKER=1`` are set (test scenario where
    the parent test sets the stub env var, which propagates to
    worker via ``os.environ.copy()`` per A2), the stub gate wins
    — correct for the test path.

    Defense-in-depth via pytest sys.modules guard (iter-2
    carry-forward Cas-W11): the gate requires both the env var
    AND ``"pytest" in sys.modules``. Production processes
    (auto_cmd orchestrator, worker subprocesses) do NOT import
    pytest at runtime, so accidental env var leak into production
    has ZERO effect — gate cannot fire. Test runners load pytest
    into sys.modules at process start. This converts the gate
    from "test-by-convention" to "test-by-runtime-check".

    Test-only — production callers MUST NOT set the env var
    (gate is namespaced via ``SBTDD_E2E_*`` prefix; production
    workers continue to dispatch real LLM via ``claude -p``).
```

- [ ] **Step 10: Run sec.0.1 chain after refactor**

Run: `make verify`
Expected: all 4 tools clean; coverage >= 88%; no new test failures.

- [ ] **Step 11: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T1 Refactor: document SBTDD_E2E_STUB_DISPATCH gate in invoke_skill docstring"`

Expected: commit with `refactor:` prefix; cascade into close-task which flips T1 checkbox `[x]` in `planning/claude-plan-tdd.md` + commits `chore: mark task 1 complete` + state advances to next task `red`.

---

## Task 2: A2 — Worker env propagation regression test + contract documentation

**Goal:** Pin the contract that `auto_cmd._dispatch_tracks_concurrent`'s `worker_env = os.environ.copy()` propagates ALL parent env vars unfiltered to worker subprocesses, including `SBTDD_E2E_STUB_DISPATCH`. Per iter-2 carry-forward Mel-W2+Cas-W8 resolution: Green phase contains SUBSTANTIVE documentation work — docstring extension on `_dispatch_tracks_concurrent` + inline comment block — NOT a 1-line throwaway comment. The contract is doc-pinned in TWO places (runtime via test + static via doc surfaces).

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` — `_dispatch_tracks_concurrent` docstring + inline comment block at line ~2061
- Test: `tests/test_auto_cmd.py` (add 1 regression test near existing dispatch tests)

**Spec mapping:** Escenario A2-1 (parent env var propagates via os.environ.copy), A2-2 (env propagation unfiltered, no allowlist)

- [ ] **Step 1: Locate target test insertion point in test_auto_cmd.py**

Run: `grep -n "_dispatch_tracks_concurrent\|test_dispatch" tests/test_auto_cmd.py | head -10`
Expected: line numbers of existing dispatcher tests. Insert the new test after the cluster of `test_dispatch_tracks_concurrent_*` tests (likely around the same line area).

- [ ] **Step 2: Write the failing Red test**

Append the following test to `tests/test_auto_cmd.py` after the existing `_dispatch_tracks_concurrent` test cluster:

```python
def test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v1.0.8 A2-1: parent env var SBTDD_E2E_STUB_DISPATCH propagates to worker.

    Pins the contract that ``_dispatch_tracks_concurrent`` does NOT
    filter env vars when building ``worker_env = os.environ.copy()``.
    A future refactor introducing an allowlist would break v1.0.8
    Pillar A1 (gate would never fire in worker subprocess).

    Test monkeypatches ``_spawn_worker`` to capture the env dict; no
    real subprocess spawned.
    """
    import auto_cmd

    monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
    monkeypatch.setenv("V108_A2_REGRESSION_MARKER", "propagated")

    captured_envs: list[dict[str, str]] = []

    class _FakeProc:
        def __init__(self) -> None:
            self.pid = 4242
            self.returncode = 0

        def communicate(self, timeout: int):
            return (b"", b"")

    def _fake_spawn_worker(argv, env, **popen_kwargs):
        captured_envs.append(dict(env))
        return _FakeProc()

    monkeypatch.setattr(auto_cmd, "_spawn_worker", _fake_spawn_worker)

    # Stub out post-batch hooks so the test focuses only on env propagation.
    # Per iter-2 carry-forward Mel-W1: also stub close_task_cmd._merge_scratch_plans
    # because auto_cmd._dispatch_tracks_concurrent does `getattr(_ctc,
    # "_merge_scratch_plans", None)` and invokes it if present (auto_cmd.py
    # line ~2124-2128). Without this stub, the helper may try to read
    # scratch plans from disk and fail in the test temp dir.
    monkeypatch.setattr(
        auto_cmd, "_verify_worker_sidecars_present", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        auto_cmd, "_merge_audit_sidecars", lambda *a, **kw: {"schema_version": 1}
    )
    monkeypatch.setattr(
        auto_cmd, "_atomic_write_json", lambda *a, **kw: None
    )
    monkeypatch.setattr(auto_cmd, "_reap_orphans", lambda *a, **kw: None)

    # Stub close_task_cmd._merge_scratch_plans (post-batch hook resolved
    # via getattr in auto_cmd line ~2126). Use monkeypatch on the close_task_cmd
    # module attribute so the getattr lookup finds our stub.
    import close_task_cmd
    monkeypatch.setattr(
        close_task_cmd, "_merge_scratch_plans", lambda *a, **kw: None, raising=False
    )

    (tmp_path / ".claude").mkdir()

    auto_cmd._dispatch_tracks_concurrent(
        tracks=[["1"]],
        effective_workers=1,
        project_root=tmp_path,
        ns=None,
    )

    assert len(captured_envs) == 1, "exactly one worker should have been spawned"
    worker_env = captured_envs[0]
    assert worker_env.get("SBTDD_E2E_STUB_DISPATCH") == "1", (
        "v1.0.8 A2 regression: SBTDD_E2E_STUB_DISPATCH must propagate from "
        "parent to worker unchanged"
    )
    assert worker_env.get("V108_A2_REGRESSION_MARKER") == "propagated", (
        "v1.0.8 A2-2 regression: unrelated custom env vars must also "
        "propagate (no filtering allowlist)"
    )
```

- [ ] **Step 3: Run the Red test to verify it passes (regression-pin pattern)**

Run: `pytest tests/test_auto_cmd.py::test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch -v`

Expected outcome — this test is a REGRESSION PIN: it should pass immediately because `os.environ.copy()` already propagates env vars without filtering. Per iter-2 carry-forward Mel-W2+Cas-W8: this is NOT classical TDD (no failing-then-passing transition); it's a characterization test. The Green phase below does NOT add minimal-to-pass impl — it adds documentation that pins the contract for static readers, complementing the dynamic pin from the test.

If the test FAILS at scaffold-time (import path issues, missing fixture), fix those test-side issues until it passes against the unchanged production code.

- [ ] **Step 4: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the Red test passes-by-design (regression pin), but close-phase Red verification would still run sec.0.1 chain which is heavy. Use raw git commit instead for consistency with other Red phases. State stays at `current_phase=red`.

```bash
git add tests/test_auto_cmd.py
git commit -m "test: v1.0.8 T2 Red — regression pin for worker env propagation"
```

Expected: Commit recorded; `git status` clean; state file unchanged.

- [ ] **Step 5: Write the Green — substantive documentation of env propagation contract**

Per iter-2 carry-forward Mel-W2+Cas-W8: the Green phase has TWO substantive doc surfaces. NOT a 1-line throwaway comment.

**(a)** Modify the docstring of `auto_cmd._dispatch_tracks_concurrent` in `skills/sbtdd/scripts/auto_cmd.py` around line ~1948-1991. Locate the existing docstring's `Args:` section. Add a new paragraph BEFORE `Args:` documenting the env propagation contract:

```
    **Env var propagation contract** (v1.0.8 Pillar A2): each
    worker subprocess inherits the parent's environment via
    ``worker_env = os.environ.copy()`` at line ~2061 — UNFILTERED.
    All env vars present in the parent process are propagated to
    workers unchanged. This contract is load-bearing for v1.0.8
    Pillar A1: the stub gate's env var (``SBTDD_E2E_STUB_DISPATCH``)
    flows from a parent test process down through the orchestrator
    to each worker, where the gate fires and bypasses real
    ``claude -p`` dispatch. A future refactor introducing an
    env-var allowlist (e.g., to scrub secrets) would break the
    stub gate semantics and the v1.0.8 e2e test
    (``test_auto_parallel_e2e``). The regression test
    ``test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch``
    in ``tests/test_auto_cmd.py`` pins this contract at runtime.
```

**(b)** Around line 2061, locate the existing comment block above `worker_env = os.environ.copy()`. Insert a NEW multi-line comment block (not a single line) between the existing v1.0.7 comment block and the assignment:

```python
                # v1.0.7 A2: route through the cross-platform dispatcher so
                # the SBTDD_AUTO_PARALLEL_WORKER=1 env contract holds for
                # every worker (POSIX -> PTY allocation; Windows -> PIPE +
                # env marker). Direct subprocess.Popen here would bypass
                # the chicken-and-egg fix.
                #
                # v1.0.8 A2: env propagation is UNFILTERED — os.environ.copy()
                # preserves all parent env vars in the worker context. This
                # contract is load-bearing for v1.0.8 Pillar A1 (the stub
                # gate's SBTDD_E2E_STUB_DISPATCH env var flows parent ->
                # orchestrator -> worker unchanged; gate fires in worker
                # subprocess + bypasses real claude -p). The regression
                # test test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch
                # pins this. Any future allowlist refactor MUST update
                # both this comment AND the regression test together.
                worker_env = os.environ.copy()
```

Together (a) + (b) constitute the substantive Green diff: ~10 lines of docstring + 8 lines of inline comment. Both serve the same goal as the test — pin the env propagation contract for future maintainers.

- [ ] **Step 6: Run sec.0.1 chain after Green diff**

Run: `make verify`
Expected: clean sec.0.1 chain.

- [ ] **Step 7: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T2 Green: document worker env propagation contract (docstring + inline) — pins SBTDD_E2E_STUB_DISPATCH semantics for v1.0.8 Pillar A1"`

Expected: commit with `feat:` prefix; state advances to `refactor`.

- [ ] **Step 8: Write the Refactor — extract reusable env-capture helper for related tests**

In `tests/test_auto_cmd.py`, the `_FakeProc` + `_fake_spawn_worker` pattern in the new test could be reused by future env-propagation regression tests. Extract them to module-level helpers at the top of the file (after imports, before the first test function):

```python
class _CapturingFakeWorkerProc:
    """v1.0.8 T2 helper: minimal subprocess.Popen stub for env-capture tests.

    Returns (b"", b"") from communicate(); pid=4242; returncode=0.
    """

    def __init__(self) -> None:
        self.pid = 4242
        self.returncode = 0

    def communicate(self, timeout: int):
        return (b"", b"")


def _make_env_capturing_spawn_worker(
    captured_envs: list[dict[str, str]],
):
    """v1.0.8 T2 helper: build a fake _spawn_worker that records env dicts.

    Returns a callable matching the _spawn_worker signature that appends
    each invocation's env dict to ``captured_envs`` and returns a
    :class:`_CapturingFakeWorkerProc`.
    """

    def _fake(argv, env, **popen_kwargs):
        captured_envs.append(dict(env))
        return _CapturingFakeWorkerProc()

    return _fake
```

Then refactor the test body to use these helpers:

```python
def test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(docstring preserved from Red)"""
    import auto_cmd

    monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
    monkeypatch.setenv("V108_A2_REGRESSION_MARKER", "propagated")

    captured_envs: list[dict[str, str]] = []
    monkeypatch.setattr(
        auto_cmd,
        "_spawn_worker",
        _make_env_capturing_spawn_worker(captured_envs),
    )
    monkeypatch.setattr(
        auto_cmd, "_verify_worker_sidecars_present", lambda *a, **kw: None
    )
    monkeypatch.setattr(
        auto_cmd, "_merge_audit_sidecars", lambda *a, **kw: {"schema_version": 1}
    )
    monkeypatch.setattr(
        auto_cmd, "_atomic_write_json", lambda *a, **kw: None
    )
    monkeypatch.setattr(auto_cmd, "_reap_orphans", lambda *a, **kw: None)

    (tmp_path / ".claude").mkdir()

    auto_cmd._dispatch_tracks_concurrent(
        tracks=[["1"]],
        effective_workers=1,
        project_root=tmp_path,
        ns=None,
    )

    assert len(captured_envs) == 1
    worker_env = captured_envs[0]
    assert worker_env.get("SBTDD_E2E_STUB_DISPATCH") == "1", (
        "v1.0.8 A2 regression: SBTDD_E2E_STUB_DISPATCH must propagate "
        "from parent to worker unchanged"
    )
    assert worker_env.get("V108_A2_REGRESSION_MARKER") == "propagated", (
        "v1.0.8 A2-2 regression: unrelated custom env vars must also "
        "propagate (no filtering allowlist)"
    )
```

- [ ] **Step 9: Run sec.0.1 chain after refactor**

Run: `pytest tests/test_auto_cmd.py::test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch -v`
Expected: PASS (behavior unchanged from Green).

Run: `make verify`
Expected: clean.

- [ ] **Step 10: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T2 Refactor: extract env-capturing fake worker helpers in test_auto_cmd"`

Expected: `refactor:` commit + cascade into close-task `chore:` commit + T2 checkbox `[x]`.

---

## Task 3: A4 — Gate regression test class `TestE2EStubGate`

**Goal:** Add comprehensive regression suite for the v1.0.8 A1 stub gate. 4 tests covering: gate fires, gate does not fire (env unset), gate does not fire (skill outside set), stdout marker semantic.

**Files:**
- Test: `tests/test_superpowers_dispatch.py` (add new class `TestE2EStubGate` near end of file, after existing classes)

**Spec mapping:** Escenario A4-1 (class structure), A4-2 (monkeypatch target invariant), A4-3 (positive case raises on subprocess attempt), A1-2 / A1-3 / A1-4 (behaviors covered by tests).

- [ ] **Step 1: Read existing class patterns to match style**

Run: `grep -n "^class TestInvokeSkill" tests/test_superpowers_dispatch.py`
Expected: line numbers of existing test classes. Read one (e.g., `TestInvokeSkillMembershipGate`) to mimic structure.

- [ ] **Step 2: Write the failing Red test class (4 stub methods raising NotImplementedError)**

Append to end of `tests/test_superpowers_dispatch.py`:

```python
class TestE2EStubGate:
    """v1.0.8 Pillar A4: regression tests for SBTDD_E2E_STUB_DISPATCH gate.

    Each test monkeypatches ``subprocess_utils.run_with_timeout`` at the
    bottom of the call chain so the gate at the top of
    :func:`superpowers_dispatch.invoke_skill` is exercised end-to-end
    (real ``invoke_skill`` execution; only the subprocess call is faked).
    Monkeypatching ``invoke_skill`` itself would break the gate test
    semantic (gate would never run).

    See ``sbtdd/spec-behavior.md`` v1.0.8 sec.4.4 escenarios A4-1..A4-3.
    """

    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """v1.0.8 A4-1 (covers A1-1 + A1-4): env=1 + stubbable skill -> stub."""
        raise NotImplementedError("v1.0.8 T3 Red placeholder")

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """v1.0.8 A4-2 (covers A1-2): env unset -> real path attempted."""
        raise NotImplementedError("v1.0.8 T3 Red placeholder")

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """v1.0.8 A4-3 (covers A1-3): env=1 + non-stubbable -> real path."""
        raise NotImplementedError("v1.0.8 T3 Red placeholder")

    def test_gate_stdout_contains_marker(self, monkeypatch):
        """v1.0.8 A4-4 (covers A1-4): stub stdout has '[sbtdd e2e stub]' literal."""
        raise NotImplementedError("v1.0.8 T3 Red placeholder")
```

- [ ] **Step 3: Run the Red tests to verify they fail**

Run: `pytest tests/test_superpowers_dispatch.py::TestE2EStubGate -v`
Expected: 4 FAILURES with `NotImplementedError: v1.0.8 T3 Red placeholder`.

- [ ] **Step 4: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the 4 failing tests are intentional Red phase; close-phase verification would abort on the NotImplementedErrors. Use raw git commit.

```bash
git add tests/test_superpowers_dispatch.py
git commit -m "test: v1.0.8 T3 Red — TestE2EStubGate scaffolding with 4 placeholder tests"
```

Expected: Commit recorded; `git status` clean; state unchanged.

- [ ] **Step 5: Write the Green — replace each test method with real body**

Replace the four test method bodies in `tests/test_superpowers_dispatch.py::TestE2EStubGate`:

```python
class TestE2EStubGate:
    """(docstring preserved from Red phase)"""

    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """v1.0.8 A4-1 (covers A1-1 + A1-4): env=1 + stubbable skill -> stub."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

        def _fail(*args, **kwargs):
            raise AssertionError(
                "v1.0.8 A4-3 regression: subprocess attempted but gate "
                "should have fired"
            )

        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils, "run_with_timeout", _fail
        )

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert isinstance(result, SkillResult)
        assert result.returncode == 0
        assert result.skill == "test-driven-development"
        assert result.stderr == ""

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """v1.0.8 A4-2 (covers A1-2): env unset -> real path attempted."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.delenv("SBTDD_E2E_STUB_DISPATCH", raising=False)

        captured = {"called": False}

        def _capture(cmd, **kwargs):
            captured["called"] = True
            captured["cmd"] = cmd
            return type(
                "_CP", (), {"returncode": 0, "stdout": "real", "stderr": ""}
            )()

        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils, "run_with_timeout", _capture
        )

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-2 regression: gate fired even though env var unset; "
            "production path was incorrectly bypassed"
        )
        assert isinstance(result, SkillResult)
        assert result.returncode == 0
        # Real path returns subprocess output, not the stub marker.
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """v1.0.8 A4-3 (covers A1-3): env=1 + non-stubbable -> real path."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")

        captured = {"called": False}

        def _capture(cmd, **kwargs):
            captured["called"] = True
            return type(
                "_CP", (), {"returncode": 0, "stdout": "real", "stderr": ""}
            )()

        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils, "run_with_timeout", _capture
        )

        # /verification-before-completion is in _SUBPROCESS_INCOMPATIBLE_SKILLS
        # but NOT in _E2E_STUBBABLE_SKILLS, so the v1.0.8 A1 gate must skip
        # it even with env var set. The v1.0.4 membership gate is bypassed
        # via allow_interactive_skill=True (production wrapper path).
        result = superpowers_dispatch.invoke_skill(
            "verification-before-completion",
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-3 regression: gate fired for a skill outside "
            "_E2E_STUBBABLE_SKILLS; production "
            "/verification-before-completion path was incorrectly bypassed"
        )
        assert isinstance(result, SkillResult)
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_stdout_contains_marker(self, monkeypatch):
        """v1.0.8 A4-4 (covers A1-4): stub stdout has '[sbtdd e2e stub]' literal."""
        import superpowers_dispatch

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils,
            "run_with_timeout",
            lambda *a, **kw: (_ for _ in ()).throw(
                AssertionError("subprocess attempted")
            ),
        )

        result = superpowers_dispatch.invoke_skill(
            "systematic-debugging",
            args=[],
            allow_interactive_skill=True,
        )

        assert result.stdout.startswith("[sbtdd e2e stub] /"), (
            f"Expected stdout to start with '[sbtdd e2e stub] /' marker; "
            f"got: {result.stdout!r}"
        )
        assert "systematic-debugging" in result.stdout
        assert "bypassed (SBTDD_E2E_STUB_DISPATCH=1)" in result.stdout
```

- [ ] **Step 6: Run the Green tests to verify all 4 pass**

Run: `pytest tests/test_superpowers_dispatch.py::TestE2EStubGate -v`
Expected: 4 PASSED.

Run: `make verify`
Expected: clean sec.0.1 chain.

- [ ] **Step 7: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T3 Green: implement 4 TestE2EStubGate regression tests"`

Expected: `feat:` commit.

- [ ] **Step 8: Write the Refactor — extract shared monkeypatch helpers**

The 4 tests share `_fail`/`_capture` patterns for monkeypatching `run_with_timeout`. Extract shared helper methods to the class to reduce duplication.

Add 2 static methods to `TestE2EStubGate` at the top of the class (before the 4 test methods):

```python
    @staticmethod
    def _capture_run_with_timeout(monkeypatch) -> dict:
        """Return a capture dict + monkeypatch run_with_timeout to record calls.

        Returns the capture dict so individual tests can introspect:
        ``captured["called"]`` (bool) and ``captured["cmd"]`` (list[str]).
        """
        import superpowers_dispatch

        captured: dict = {"called": False, "cmd": None}

        def _capture(cmd, **kwargs):
            captured["called"] = True
            captured["cmd"] = cmd
            return type(
                "_CP", (), {"returncode": 0, "stdout": "real", "stderr": ""}
            )()

        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils, "run_with_timeout", _capture
        )
        return captured

    @staticmethod
    def _fail_if_subprocess_called(monkeypatch) -> None:
        """Monkeypatch run_with_timeout to raise AssertionError if invoked.

        Used by tests asserting the gate fires (subprocess must NEVER be
        reached when env var is set + skill is stubbable).
        """
        import superpowers_dispatch

        def _fail(*args, **kwargs):
            raise AssertionError(
                "v1.0.8 A4 regression: subprocess attempted but gate "
                "should have fired"
            )

        monkeypatch.setattr(
            superpowers_dispatch.subprocess_utils, "run_with_timeout", _fail
        )
```

Then refactor each of the 4 test methods to call the helpers instead of inlining the monkeypatch:

```python
    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """v1.0.8 A4-1 (covers A1-1 + A1-4): env=1 + stubbable skill -> stub."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
        self._fail_if_subprocess_called(monkeypatch)

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert isinstance(result, SkillResult)
        assert result.returncode == 0
        assert result.skill == "test-driven-development"
        assert result.stderr == ""

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """v1.0.8 A4-2 (covers A1-2): env unset -> real path attempted."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.delenv("SBTDD_E2E_STUB_DISPATCH", raising=False)
        captured = self._capture_run_with_timeout(monkeypatch)

        result = superpowers_dispatch.invoke_skill(
            "test-driven-development",
            args=["--phase=red"],
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-2 regression: gate fired even though env var unset"
        )
        assert isinstance(result, SkillResult)
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """v1.0.8 A4-3 (covers A1-3): env=1 + non-stubbable -> real path."""
        import superpowers_dispatch
        from superpowers_dispatch import SkillResult

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
        captured = self._capture_run_with_timeout(monkeypatch)

        result = superpowers_dispatch.invoke_skill(
            "verification-before-completion",
            allow_interactive_skill=True,
        )

        assert captured["called"], (
            "v1.0.8 A4-3 regression: gate fired for non-stubbable skill"
        )
        assert isinstance(result, SkillResult)
        assert "[sbtdd e2e stub]" not in result.stdout

    def test_gate_stdout_contains_marker(self, monkeypatch):
        """v1.0.8 A4-4 (covers A1-4): stub stdout has '[sbtdd e2e stub]' literal."""
        import superpowers_dispatch

        monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
        self._fail_if_subprocess_called(monkeypatch)

        result = superpowers_dispatch.invoke_skill(
            "systematic-debugging",
            args=[],
            allow_interactive_skill=True,
        )

        assert result.stdout.startswith("[sbtdd e2e stub] /"), (
            f"Expected stdout to start with '[sbtdd e2e stub] /' marker; "
            f"got: {result.stdout!r}"
        )
        assert "systematic-debugging" in result.stdout
        assert "bypassed (SBTDD_E2E_STUB_DISPATCH=1)" in result.stdout
```

- [ ] **Step 9: Run sec.0.1 chain after refactor**

Run: `pytest tests/test_superpowers_dispatch.py::TestE2EStubGate -v`
Expected: 4 PASSED (behavior unchanged from Green).

Run: `make verify`
Expected: clean.

- [ ] **Step 10: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T3 Refactor: extract shared monkeypatch helpers in TestE2EStubGate"`

Expected: `refactor:` commit + close-task cascade.

---

## Task 4: A3 — T3 e2e test redesign (unxfail + strict assertions)

**Goal:** Remove `@pytest.mark.xfail` from `test_auto_parallel_e2e_chicken_and_egg_closed`, set `SBTDD_E2E_STUB_DISPATCH=1` in subprocess env, shrink timeout 600→60, replace permissive assertions with strict happy-path assertions (rc=0, state=done, plan flipped, sidecars present with verify_chain `>= 4` entries — per iter-2 carry-forward Cas-W10 — + per-tool presence check for pytest+ruff+mypy each rc=0, audit finished status=success).

**Files:**
- Modify: `tests/test_auto_parallel_e2e.py`
  - Test function `test_auto_parallel_e2e_chicken_and_egg_closed` (line ~198): remove `@pytest.mark.xfail` decorator, update body + docstring
  - Module-level constant `_AUTO_TIMEOUT_S` (line ~66): change `600` to `60`

**Spec mapping:** Escenario A3-1 (happy path), A3-2 (post-cycle state assertions), A3-3 (sidecar verify_chain shape), A3-4 (xfail marker removed)

**Dependencies**: T1 (gate exists) + T5 (fixture has `.claude/settings.json`) MUST be completed before T4.

- [ ] **Step 1: Read current test body to plan delta**

Run: `sed -n '184,268p' tests/test_auto_parallel_e2e.py`
Expected: current xfail decorator + test body. Plan: replace lines ~184-197 (xfail decorator + decorator gap) by removing them; replace lines ~244-267 (permissive assertions) with strict assertions; update `_AUTO_TIMEOUT_S` constant.

- [ ] **Step 2: Write the failing Red — strict assertions WITHOUT env var stub yet**

Modify `tests/test_auto_parallel_e2e.py`:

(a) **Delete** the `@pytest.mark.xfail(...)` decorator block from `test_auto_parallel_e2e_chicken_and_egg_closed`. The two `@pytest.mark.skipif` decorators above it (POSIX skip + toolchain skip) MUST be preserved.

(b) Replace the function body (from `proc = subprocess.run(...)` to the end of the function) with:

```python
    # v1.0.8 A3 Red phase: strict assertions intentionally WITHOUT
    # SBTDD_E2E_STUB_DISPATCH=1 in env. Expected to fail (timeout or
    # assertion) — proves the stub gate is required. Green adds env var.
    env = os.environ.copy()

    proc = subprocess.run(
        [sys.executable, str(_RUN_SBTDD), "auto", "--parallel"],
        cwd=str(project),
        env=env,
        capture_output=True,
        text=True,
        timeout=_AUTO_TIMEOUT_S,
    )
    diagnostic = _diagnostic_message(proc.returncode, proc.stdout, proc.stderr)

    assert proc.returncode == 0, (
        f"v1.0.8 A3-1 expected rc=0; got rc={proc.returncode}.{diagnostic}"
    )

    state = json.loads(
        (project / ".claude" / "session-state.json").read_text(encoding="utf-8")
    )
    assert state["current_phase"] == "done", (
        f"v1.0.8 A3-2 expected current_phase=='done'; "
        f"got {state['current_phase']!r}.{diagnostic}"
    )

    import re

    plan_text = (project / "planning" / "claude-plan-tdd.md").read_text(
        encoding="utf-8"
    )
    assert not re.search(r"^[ \t]*- \[ \]", plan_text, re.MULTILINE), (
        f"v1.0.8 A3-2 expected all plan checkboxes flipped to [x]; "
        f"open '- [ ]' line(s) remain.{diagnostic}"
    )

    workers_dir = project / ".claude" / "auto-run-workers"
    assert workers_dir.is_dir(), (
        f"v1.0.8 A3-2 missing {workers_dir}.{diagnostic}"
    )
    sidecars = list(workers_dir.glob("*-verify.json"))
    assert sidecars, (
        f"v1.0.8 A3-2 expected >=1 sidecar in {workers_dir}.{diagnostic}"
    )
    # Per iter-2 carry-forward Cas-W10: `>= 4` (not `== 4`) + presence
    # check for the 4 known sec.0.1 tools. Future sec.0.1 extensions
    # (5th tool) MUST NOT break the assertion; the 4 known tools MUST
    # be present.
    # Per iter-2 carry-forward Cas-W5+Mel-W3: tool detection via
    # substring-anywhere match on str(cmd), NOT positional cmd[2].
    # This is robust against future cmd-shape evolution (e.g.,
    # python -X dev -m pytest, env wrappers, different module paths).
    expected_tools = {"pytest", "ruff", "mypy"}  # ruff appears twice (check + format)
    for sc in sidecars:
        payload = json.loads(sc.read_text(encoding="utf-8"))
        chain = payload.get("verify_chain")
        assert isinstance(chain, list) and len(chain) >= 4, (
            f"v1.0.8 A3-3 expected verify_chain with >=4 entries "
            f"in {sc.name}; got "
            f"{len(chain) if isinstance(chain, list) else 'non-list'}."
            f"{diagnostic}"
        )
        # Substring-anywhere tool detection. Convert each cmd list
        # to a single space-joined string and check the tool name
        # appears anywhere. Robust against cmd-shape changes.
        tools_in_chain: set[str] = set()
        for entry in chain:
            cmd = entry.get("cmd")
            if not isinstance(cmd, list):
                continue
            cmd_str = " ".join(str(p) for p in cmd)
            for tool in expected_tools:
                if tool in cmd_str:
                    tools_in_chain.add(tool)
        missing = expected_tools - tools_in_chain
        assert not missing, (
            f"v1.0.8 A3-3 expected tools {expected_tools} in verify_chain "
            f"of {sc.name}; missing {missing}; observed {tools_in_chain}."
            f"{diagnostic}"
        )
        for entry in chain:
            assert entry.get("rc") == 0, (
                f"v1.0.8 A3-3 expected all sec.0.1 tools rc=0 in "
                f"{sc.name}; got entry rc={entry.get('rc')}.{diagnostic}"
            )

    audit = json.loads(
        (project / ".claude" / "auto-run.json").read_text(encoding="utf-8")
    )
    assert audit.get("auto_finished_at") is not None, (
        f"v1.0.8 A3-2 expected auto_finished_at non-null.{diagnostic}"
    )
    assert audit.get("status") == "success", (
        f"v1.0.8 A3-2 expected status=='success'; "
        f"got {audit.get('status')!r}.{diagnostic}"
    )
```

(c) Update the function docstring (replace the existing xfail rationale paragraph) to:

```python
    """v1.0.8 A3 dogfood: ``auto --parallel`` workers complete in 60s.

    Empirical validation that v1.0.7 A1 POSIX PTY + A2 Windows hybrid
    Option B-W3 fallback close the chicken-and-egg surface confirmed
    in v1.0.6 own-cycle (workers spawned via ``subprocess.PIPE`` with
    no TTY hanging on ``close-phase /verification-before-completion``).

    v1.0.8 closes the empirical gap: the v1.0.7 600s timeout was caused
    by an upstream ``claude -p /test-driven-development`` hang in the
    fixture cwd (documented in CLAUDE.md "Known upstream limitations").
    The subprocess env carries ``SBTDD_E2E_STUB_DISPATCH=1`` so
    ``superpowers_dispatch.invoke_skill`` short-circuits the
    ``/test-driven-development`` + ``/systematic-debugging`` dispatches
    to a synthetic ``SkillResult(rc=0)`` — workers reach the actual
    chicken-and-egg surface (`_run_verification` worker-mode bypass via
    sec.0.1 chain) without the upstream LLM-dispatch hang.

    Strict happy-path assertions (per Q4'=a+):

    - subprocess returncode == 0
    - session-state.json current_phase == "done"
    - planning/claude-plan-tdd.md has zero ``- [ ]`` line-start checkboxes
    - .claude/auto-run-workers/ contains >= 1 sidecar with verify_chain
      of exactly 4 entries each rc=0
    - .claude/auto-run.json auto_finished_at non-null + status=="success"
    """
```

(d) Update the module-level constant at line ~66:

```python
# Subprocess timeout for the entire ``auto --parallel`` invocation.
# v1.0.8 A3 shrunk from 600s to 60s — the stub gate (Pillar A1)
# eliminates the upstream LLM-dispatch cost that drove the v1.0.7
# 600s budget.
_AUTO_TIMEOUT_S = 60
```

- [ ] **Step 3: Verify Red state deterministically via static grep (iter-2 carry-forward Cas-W6 resolution)**

Per iter-2 carry-forward Cas-W6: do NOT run the actual e2e test in Red phase. Running it depends on upstream `claude -p` hang behavior (flaky, slow). Instead, verify Red state DETERMINISTICALLY via static inspection: the test source has the strict assertions in place AND does NOT yet have `env["SBTDD_E2E_STUB_DISPATCH"] = "1"`.

Run:
```bash
grep -n 'SBTDD_E2E_STUB_DISPATCH' tests/test_auto_parallel_e2e.py
```
Expected: ZERO lines printed (env var not yet set in test code — the Red state).

Run:
```bash
grep -n 'rc=0' tests/test_auto_parallel_e2e.py | head
```
Expected: at least one match (strict assertions are in place per Step 2).

Run:
```bash
grep -n '@pytest.mark.xfail' tests/test_auto_parallel_e2e.py
```
Expected: ZERO matches (xfail decorator was deleted in Step 2a).

These three checks deterministically confirm the Red state without depending on upstream behavior. If desired, also run the e2e test with a SHORT timeout (e.g., 5s) to confirm it fails by timeout — but treat that as informational, NOT as the gate.

- [ ] **Step 4: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the test fails intentionally (timeout or assertion); close-phase verification would abort. Use raw git commit.

```bash
git add tests/test_auto_parallel_e2e.py
git commit -m "test: v1.0.8 T4 Red — T3 e2e strict assertions without stub gate env var"
```

Expected: Commit recorded; `git status` clean; state unchanged.

- [ ] **Step 5: Write the Green — add SBTDD_E2E_STUB_DISPATCH=1 to env**

In `tests/test_auto_parallel_e2e.py`, locate the env block within the test body:

```python
    env = os.environ.copy()
```

Replace with:

```python
    # v1.0.8 A3 Green: stub gate env var bypasses upstream claude -p hang.
    env = os.environ.copy()
    env["SBTDD_E2E_STUB_DISPATCH"] = "1"
```

- [ ] **Step 6: Run the Green test to verify it passes**

Run: `pytest tests/test_auto_parallel_e2e.py::test_auto_parallel_e2e_chicken_and_egg_closed -v`
Expected: PASSED in <60s.

Run: `make verify`
Expected: clean sec.0.1 chain.

- [ ] **Step 7: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T4 Green: T3 e2e passes with SBTDD_E2E_STUB_DISPATCH=1 in subprocess env"`

Expected: `feat:` commit.

- [ ] **Step 8: Write the Refactor — extract assertion helpers to module level**

The new test body has a long sequence of asserts. Extract them into focused module-level helpers in `tests/test_auto_parallel_e2e.py`.

Add after the existing `_diagnostic_message` helper (around line ~170):

```python
def _assert_state_done(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert session-state.json reports phase=done."""
    state = json.loads(
        (project / ".claude" / "session-state.json").read_text(encoding="utf-8")
    )
    assert state["current_phase"] == "done", (
        f"v1.0.8 A3-2 expected current_phase=='done'; "
        f"got {state['current_phase']!r}.{diagnostic}"
    )


def _assert_plan_fully_flipped(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert all plan checkboxes are [x]."""
    import re

    plan_text = (project / "planning" / "claude-plan-tdd.md").read_text(
        encoding="utf-8"
    )
    assert not re.search(r"^[ \t]*- \[ \]", plan_text, re.MULTILINE), (
        f"v1.0.8 A3-2 expected all plan checkboxes flipped to [x]; "
        f"open '- [ ]' line(s) remain.{diagnostic}"
    )


def _assert_sidecars_valid(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2/A3-3 helper: assert sidecars exist with valid verify_chain.

    Per iter-2 carry-forward Cas-W10: `>=4` entries (extensible) +
    presence check for the 4 known sec.0.1 tools (pytest, ruff,
    mypy). Future sec.0.1 extensions MUST NOT break this assertion.
    Per iter-2 carry-forward Cas-W5+Mel-W3: tool detection via
    substring-anywhere match (not positional cmd[2]) for robustness.
    """
    workers_dir = project / ".claude" / "auto-run-workers"
    assert workers_dir.is_dir(), (
        f"v1.0.8 A3-2 missing {workers_dir}.{diagnostic}"
    )
    sidecars = list(workers_dir.glob("*-verify.json"))
    assert sidecars, (
        f"v1.0.8 A3-2 expected >=1 sidecar in {workers_dir}.{diagnostic}"
    )
    # The 4 known sec.0.1 tools that MUST appear in the chain
    # (ruff appears twice: ruff check + ruff format --check; but
    # the unique tool module names are {pytest, ruff, mypy}).
    expected_tools = {"pytest", "ruff", "mypy"}
    for sc in sidecars:
        payload = json.loads(sc.read_text(encoding="utf-8"))
        chain = payload.get("verify_chain")
        assert isinstance(chain, list) and len(chain) >= 4, (
            f"v1.0.8 A3-3 expected verify_chain with >=4 entries "
            f"in {sc.name}.{diagnostic}"
        )
        # Substring-anywhere tool detection.
        tools_in_chain: set[str] = set()
        for entry in chain:
            cmd = entry.get("cmd")
            if not isinstance(cmd, list):
                continue
            cmd_str = " ".join(str(p) for p in cmd)
            for tool in expected_tools:
                if tool in cmd_str:
                    tools_in_chain.add(tool)
        missing = expected_tools - tools_in_chain
        assert not missing, (
            f"v1.0.8 A3-3 expected tools {expected_tools} in chain "
            f"of {sc.name}; missing {missing}; "
            f"observed {tools_in_chain}.{diagnostic}"
        )
        for entry in chain:
            assert entry.get("rc") == 0, (
                f"v1.0.8 A3-3 expected all sec.0.1 tools rc=0 in "
                f"{sc.name}; got {entry.get('rc')}.{diagnostic}"
            )


def _assert_audit_finished_success(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert auto-run.json reports finished + success."""
    audit = json.loads(
        (project / ".claude" / "auto-run.json").read_text(encoding="utf-8")
    )
    assert audit.get("auto_finished_at") is not None, (
        f"v1.0.8 A3-2 expected auto_finished_at non-null.{diagnostic}"
    )
    assert audit.get("status") == "success", (
        f"v1.0.8 A3-2 expected status=='success'; "
        f"got {audit.get('status')!r}.{diagnostic}"
    )
```

Then replace the inline asserts in the test body (everything after `diagnostic = _diagnostic_message(...)` line) with 4 helper calls:

```python
    diagnostic = _diagnostic_message(proc.returncode, proc.stdout, proc.stderr)
    assert proc.returncode == 0, (
        f"v1.0.8 A3-1 expected rc=0; got rc={proc.returncode}.{diagnostic}"
    )
    _assert_state_done(project, diagnostic)
    _assert_plan_fully_flipped(project, diagnostic)
    _assert_sidecars_valid(project, diagnostic)
    _assert_audit_finished_success(project, diagnostic)
```

- [ ] **Step 9: Run sec.0.1 chain after refactor**

Run: `pytest tests/test_auto_parallel_e2e.py::test_auto_parallel_e2e_chicken_and_egg_closed -v`
Expected: PASSED (behavior unchanged from Green).

Run: `make verify`
Expected: clean.

- [ ] **Step 10: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T4 Refactor: extract A3 assertion helpers in test_auto_parallel_e2e"`

Expected: `refactor:` commit + close-task cascade.

---

## Task 5: B1 — Fixture `.claude/settings.json` hardening

**Goal:** Ship `tests/fixtures/parallel-e2e/dot-claude-settings.json` with explicit permissions allow list. Update `_stage_fixture` helper to materialize it as `.claude/settings.json` in the staged tree (rename-on-copy because `.claude/` is gitignored at repo root). Extend `test_fixture_files_present` to assert presence.

**Files:**
- Create: `tests/fixtures/parallel-e2e/dot-claude-settings.json`
- Modify: `tests/test_auto_parallel_e2e.py`
  - `_stage_fixture` helper (line ~106)
  - `test_fixture_files_present` test (line ~270)

**Spec mapping:** Escenario B1-1 (fixture ships JSON), B1-2 (helper materializes), B1-3 (presence assertion)

- [ ] **Step 1: Write the failing Red — extend test_fixture_files_present with new expected file**

Modify `tests/test_auto_parallel_e2e.py::test_fixture_files_present` (line ~270). Change:

```python
    expected = (
        "spec-fixture.md",
        "pyproject.toml",
        "src/sample.py",
        "tests/test_sample.py",
        "Makefile",
        "plan-fixture.md",
    )
```

To:

```python
    expected = (
        "spec-fixture.md",
        "pyproject.toml",
        "src/sample.py",
        "tests/test_sample.py",
        "Makefile",
        "plan-fixture.md",
        "dot-claude-settings.json",
    )
```

- [ ] **Step 2: Run the Red test to verify it fails**

Run: `pytest tests/test_auto_parallel_e2e.py::test_fixture_files_present -v`
Expected: FAIL with `AssertionError: missing fixture files: ['dot-claude-settings.json']`.

- [ ] **Step 3: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the test fails because the fixture file doesn't exist yet; close-phase verification would abort. Use raw git commit.

```bash
git add tests/test_auto_parallel_e2e.py
git commit -m "test: v1.0.8 T5 Red — assert dot-claude-settings.json fixture file present"
```

Expected: Commit recorded; `git status` clean; state unchanged.

- [ ] **Step 4: Write the Green — create the fixture file**

Create new file `tests/fixtures/parallel-e2e/dot-claude-settings.json` with content:

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

- [ ] **Step 5: Update `_stage_fixture` helper to materialize the file**

In `tests/test_auto_parallel_e2e.py::_stage_fixture` (around line 106), AFTER the existing `shutil.copy(Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md", claude_dir / "plugin.local.md")` line and BEFORE the `(dest / "scratch").mkdir(exist_ok=True)` line, add:

```python
    # v1.0.8 B1: materialize dot-claude-settings.json as
    # .claude/settings.json so the staged project has explicit
    # permissions for the implementer skill's tool calls (writes to
    # scratch/, tests/, src/ + bash invocations for pytest/ruff/mypy).
    # Doble defensa: even if the v1.0.8 A1 stub gate is bypassed in a
    # future test variant, the fixture is "less broken" upstream.
    shutil.copy(
        _FIXTURE_DIR / "dot-claude-settings.json",
        claude_dir / "settings.json",
    )
```

- [ ] **Step 6: Run the Green test to verify it passes**

Run: `pytest tests/test_auto_parallel_e2e.py::test_fixture_files_present -v`
Expected: PASSED.

Run: `pytest tests/test_auto_parallel_e2e.py -v` (full module)
Expected: all module tests pass.

Run: `make verify`
Expected: clean sec.0.1 chain.

- [ ] **Step 7: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T5 Green: add dot-claude-settings.json fixture + _stage_fixture extension"`

Expected: `feat:` commit.

- [ ] **Step 8: Write the Refactor — add module-level helper constant for fixture path**

In `tests/test_auto_parallel_e2e.py`, after the existing `_FIXTURE_DIR`, `_REPO_ROOT`, `_RUN_SBTDD` constants (around line 60), add:

```python
# v1.0.8 T5: settings.json fixture path resolved at module load to
# surface missing-fixture errors at collection time instead of test
# runtime.
_FIXTURE_SETTINGS_JSON = _FIXTURE_DIR / "dot-claude-settings.json"
```

Then replace the inline `_FIXTURE_DIR / "dot-claude-settings.json"` reference in `_stage_fixture` (added in Step 5) with the constant:

```python
    shutil.copy(_FIXTURE_SETTINGS_JSON, claude_dir / "settings.json")
```

- [ ] **Step 9: Run sec.0.1 chain after refactor**

Run: `pytest tests/test_auto_parallel_e2e.py -v`
Expected: all pass.

Run: `make verify`
Expected: clean.

- [ ] **Step 10: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T5 Refactor: extract _FIXTURE_SETTINGS_JSON module constant"`

Expected: `refactor:` commit + close-task cascade.

---

## Task 6: B2 — Upstream bug archive (CLAUDE.md + memory + CHANGELOG)

**Goal:** Document the empirically-observed `claude -p` cwd-dependent hang in 3 places: project root CLAUDE.md (operator-facing), user memory dir (claude-side context), CHANGELOG `[1.0.8]` Deferred section (upstream report submission DEFERRED to v1.0.9). Add doc-coherence smoke tests pinning the new structure.

**Files:**
- Create: `tests/test_doc_coherence_v108.py` (new test file with 2 smoke tests)
- Modify: `CLAUDE.md` (add new top-level section "Known upstream limitations" appended to end of file)
- Create: `C:\Users\jbolivarg\.claude\projects\D--jbolivarg-PythonProjects-SBTDD\memory\project_v108_claude_p_hang_upstream.md`
- Modify: `C:\Users\jbolivarg\.claude\projects\D--jbolivarg-PythonProjects-SBTDD\memory\MEMORY.md` (append pointer line)
- Modify: `CHANGELOG.md` (insert `[1.0.8]` entry between `[Unreleased]` and `[1.0.7]` sections)

**Spec mapping:** Escenario B2-1 (CLAUDE.md section), B2-2 (memory file), B2-3 (MEMORY.md index), B2-4 (CHANGELOG Deferred section)

- [ ] **Step 1: Write the failing Red — doc coherence smoke test**

Create new file `tests/test_doc_coherence_v108.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-14
"""v1.0.8 T6 doc-coherence smoke tests for Pillar B2 upstream bug archive.

Asserts the cross-artifact wording requirements:

- CLAUDE.md has a "Known upstream limitations" section with required keywords.
- CHANGELOG.md has a ``[1.0.8]`` entry with a Deferred subsection naming the
  upstream report submission deferral.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_CHANGELOG = _REPO_ROOT / "CHANGELOG.md"


def test_v108_b2_claude_md_has_known_upstream_limitations_section() -> None:
    """v1.0.8 B2-1: CLAUDE.md has the upstream limitations section."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    assert "## Known upstream limitations" in text, (
        "v1.0.8 B2-1: missing '## Known upstream limitations' header"
    )
    assert "### claude -p /test-driven-development hangs" in text, (
        "v1.0.8 B2-1: missing subsection header"
    )
    for required in (
        "Manifestation",
        "Repro context",
        "Workaround",
        "Upstream report",
        "SBTDD_E2E_STUB_DISPATCH",
    ):
        assert required in text, (
            f"v1.0.8 B2-1: missing required text {required!r} in CLAUDE.md"
        )


def test_v108_b2_changelog_has_v108_deferred_section() -> None:
    """v1.0.8 B2-4: CHANGELOG [1.0.8] Deferred section lists upstream report."""
    text = _CHANGELOG.read_text(encoding="utf-8")
    assert "## [1.0.8]" in text, "v1.0.8 B2-4: missing [1.0.8] entry"
    start = text.index("## [1.0.8]")
    end = text.find("## [1.0.7]", start)
    section = text[start:end] if end > 0 else text[start:]
    assert "Deferred" in section, (
        "v1.0.8 B2-4: [1.0.8] section missing 'Deferred' subsection"
    )
    assert "anthropics/claude-code" in section, (
        "v1.0.8 B2-4: Deferred section missing upstream report reference"
    )
```

- [ ] **Step 2: Run the Red tests to verify they fail**

Run: `pytest tests/test_doc_coherence_v108.py -v`
Expected: 2 FAILED — both assertions fire because the docs haven't been updated yet.

- [ ] **Step 3: Close Red phase via raw git commit**

Per the iter-2 Red-phase commit methodology (plan header): the 2 doc-coherence tests fail because the docs haven't been updated yet; close-phase verification would abort. Use raw git commit.

```bash
git add tests/test_doc_coherence_v108.py
git commit -m "test: v1.0.8 T6 Red — doc-coherence smoke tests for upstream bug archive"
```

Expected: Commit recorded; `git status` clean; state unchanged.

- [ ] **Step 4: Write the Green — append "Known upstream limitations" section to CLAUDE.md**

Append the following section to the END of `CLAUDE.md` (after the last existing section, which is the License section):

```markdown

## Known upstream limitations

### claude -p /test-driven-development hangs in fixture-style cwd

**Manifestation**: invoking `claude -p /test-driven-development --phase=red`
as a subprocess with cwd pointing to a directory that contains
`sbtdd/spec-behavior.md` + `planning/claude-plan-tdd.md` but lacks
`.claude/settings.json` + `CLAUDE.md` causes the subprocess to hang
indefinitely (>180s empirically observed, zero stdout/stderr output)
before being timeout-killed by the caller.

**Repro context**: empirically verified in v1.0.8 T3 diagnostic 2026-05-14
via 3 reproducer scripts (in `.tmp_repro/`, gitignored). Same command in
cwd=empty temp dir returns rc=0 in ~30s with sensible output; same command
in cwd=SBTDD repo dir returns rc=0 in ~66s with sensible output. The bug
is cwd-dependent on a specific file-layout combination (fixture-style:
sbtdd/ + planning/ files without `.claude/settings.json` + `CLAUDE.md`).

**Workaround**: `tests/test_auto_parallel_e2e.py` uses
`SBTDD_E2E_STUB_DISPATCH=1` to bypass the dispatch entirely (v1.0.8
Pillar A1 stub gate in `superpowers_dispatch.invoke_skill`). In
production, properly-initialized SBTDD projects (via `/sbtdd init`)
ship a complete `.claude/settings.json` granting the permissions the
implementer skill needs — avoiding the hang. v1.0.8 Pillar B1 also adds
a minimal `.claude/settings.json` to the e2e fixture as doble defensa.

**Upstream report**: STAGED for future submission to
`anthropics/claude-code` issue tracker (see memory
`project_v108_claude_p_hang_upstream.md` for repro instructions +
diagnostic evidence). v1.0.8 does NOT submit — deferred to user decision
post-v1.0.8 ship per spec sec.5 scope exclusions.
```

- [ ] **Step 5: Write the Green — create memory archive file (LOCAL-ONLY, not test-asserted)**

Per iter-2 carry-forward Cas-W12 + Bal-I6: the memory file lives OUTSIDE the repo in the developer's per-project Claude memory dir. This is **local-only** — it will not exist on CI machines or fresh clones. The doc-coherence test created in Step 1 asserts CLAUDE.md + CHANGELOG only (which ARE in the repo); the memory file is verified by **human review of the closing commit narrative**, not by an automated assertion.

Engineer note: if executing this plan on a non-developer machine (CI, fresh clone, container), skip this step and leave a note in the close-task commit ("memory archive not staged: target machine lacks the per-developer memory dir"). The plan still ships v1.0.8 successfully because the test-asserted artifacts (CLAUDE.md + CHANGELOG) are repo-resident.

Create new file at this exact path on the developer machine:
`C:\Users\jbolivarg\.claude\projects\D--jbolivarg-PythonProjects-SBTDD\memory\project_v108_claude_p_hang_upstream.md`

Content:

```markdown
---
name: project-v108-claude-p-hang-upstream
description: claude -p /test-driven-development hangs >180s in fixture-style cwd lacking .claude/settings.json — v1.0.8 T3 diagnostic empirical findings + staged upstream report content for anthropics/claude-code
metadata:
  type: reference
---

# claude -p /test-driven-development hang (upstream bug archive)

## Manifestation

Invoking `claude -p /test-driven-development --phase=red` as a
subprocess (with `subprocess.run(cmd, capture_output=True, ...)` or
`subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE, ...)`) with cwd
pointing to a directory containing `sbtdd/spec-behavior.md` +
`planning/claude-plan-tdd.md` but LACKING `.claude/settings.json` +
`CLAUDE.md` causes the subprocess to hang indefinitely (>180s
empirically observed, zero stdout/stderr output) until timeout-killed
by the caller.

## Empirical observations (v1.0.8 T3 diagnostic 2026-05-14)

Three reproducer scripts staged in `.tmp_repro/` (gitignored):

| Script | cwd | Outcome | Wall-time | rc |
|--------|-----|---------|-----------|-----|
| `repro_t3.py` | fixture temp dir (full v1.0.7 layout) | TIMEOUT, zero output | 60s killed | n/a |
| `repro_worker.py` | fixture temp dir (single worker direct spawn) | HANG after emitting "[sbtdd] phase 2/5: task loop -- task 1/4 (red)" breadcrumb | 180s killed | n/a |
| `repro_skill_with_fixture_cwd.py` | fixture temp dir | HANG >180s zero output | 180s killed | n/a |

Contrast in cwd that DO NOT hang:

| cwd | Outcome | Wall-time | rc |
|-----|---------|-----------|-----|
| empty temp dir | "working directory is empty and not a git repo" output | ~30s | 0 |
| SBTDD repo dir | "TDD skill loaded... What behavior should the next RED-phase test cover?" interactive prompt output | ~66s | 0 |

## Root cause (best hypothesis)

The fixture cwd has the file layout that looks like a real SBTDD
project (sbtdd/, planning/, plugin.local.md) but LACKS the
`.claude/settings.json` that grants permissions for tool calls. The
`/test-driven-development` skill tries to take real actions (write
tests, run pytest, etc.) and gets blocked waiting for permission
grants that never arrive in `-p` mode (non-interactive subprocess).

The hang is observable as zero stdout/stderr output for the entire
duration — the skill is blocked at the permission-prompt phase before
any meaningful work output is emitted.

## Workaround in v1.0.8

`tests/test_auto_parallel_e2e.py` uses `SBTDD_E2E_STUB_DISPATCH=1` to
bypass `claude -p` dispatch entirely via the gate at the top of
`superpowers_dispatch.invoke_skill` (v1.0.8 Pillar A1). This makes
the e2e test deterministic + fast (<60s).

In production, properly-initialized SBTDD projects (via `/sbtdd init`)
ship a complete `.claude/settings.json` from the template — avoiding
the hang. v1.0.8 Pillar B1 also adds a minimal `.claude/settings.json`
to the e2e fixture as doble defensa (so even if the stub gate is
bypassed in a future test variant, the fixture is "less broken").

## Staged upstream report content (for future submission)

**Title**: `claude -p <skill>` hangs indefinitely with zero output in
fixture-style cwd lacking `.claude/settings.json`

**Body**:

When invoking `claude -p /test-driven-development --phase=red` as a
non-interactive subprocess with cwd containing certain markers
(SBTDD-style: `sbtdd/`, `planning/`, `.claude/plugin.local.md`) but
WITHOUT `.claude/settings.json` + `CLAUDE.md`, the subprocess hangs
indefinitely emitting zero output. Same command in other cwd (empty
temp dir, repo root with permissions) returns cleanly in 30-66s.

Reproducer (Windows 11, claude CLI vX.Y.Z — fill version at submission):

```bash
# Create fixture-style cwd
mkdir -p /tmp/repro/sbtdd /tmp/repro/planning /tmp/repro/.claude
touch /tmp/repro/sbtdd/spec-behavior.md
touch /tmp/repro/planning/claude-plan-tdd.md
cat > /tmp/repro/.claude/plugin.local.md <<'EOF'
---
stack: python
EOF
cd /tmp/repro

# This hangs indefinitely with zero output:
timeout 180 claude -p "/test-driven-development --phase=red"
echo "exit: $?"  # 124 (timeout) after 180s
```

Workaround we implemented: env var gate to bypass dispatch in tests
(`SBTDD_E2E_STUB_DISPATCH=1` short-circuits the dispatcher to a
synthetic SkillResult without spawning claude -p). Production
projects don't hit this because they have proper
`.claude/settings.json` from `/sbtdd init` template.

Suspected: skill is waiting on permission prompt that never arrives
in `-p` (print/non-interactive) mode. Could the CLI emit a clear
error or hint to operator instead of silent hang?

## Links

- v1.0.7 ship that introduced the e2e test [[project_v107_shipped]]
- v1.0.8 PRIORITY LOCKED context [[project_v108_t3_e2e_priority_locked]]
- v1.0.7 chicken-and-egg empirical context [[project_v107_pty_workers_locked]]
```

- [ ] **Step 6: Update `MEMORY.md` index with pointer**

Append the following line to
`C:\Users\jbolivarg\.claude\projects\D--jbolivarg-PythonProjects-SBTDD\memory\MEMORY.md`:

```markdown
- [v1.0.8 claude -p hang upstream archive](project_v108_claude_p_hang_upstream.md) — `claude -p /test-driven-development` hangs >180s zero output in fixture-style cwd lacking `.claude/settings.json`; workaround = `SBTDD_E2E_STUB_DISPATCH=1` env gate (v1.0.8 Pillar A1); upstream report staged for future submission
```

- [ ] **Step 7: Write the Green — add CHANGELOG [1.0.8] entry**

Modify `CHANGELOG.md`. Locate the `## [Unreleased]` section (line 11) and the `## [1.0.7]` section that follows (line 15). Insert a new section between them:

```markdown
## [1.0.8] - 2026-05-14

### Added

- `SBTDD_E2E_STUB_DISPATCH` env var stub gate in
  `superpowers_dispatch.invoke_skill` (Pillar A1) with
  **defense-in-depth runtime guard** requiring `"pytest" in
  sys.modules` to prevent accidental production env var leak from
  activating the gate (iter-2 carry-forward Cas-W11+Bal-W7
  combined fix). Test-only; production callers MUST NOT set.
  When env=1 AND `"pytest"` is loaded AND skill is in
  `_E2E_STUBBABLE_SKILLS = {"test-driven-development",
  "systematic-debugging"}`, returns synthetic `SkillResult(rc=0)`
  without spawning `claude -p`. Closes the v1.0.7 PRIORITY LOCKED
  T3 e2e empirical chicken-and-egg gap.
- 4 gate regression tests in `tests/test_superpowers_dispatch.py`
  class `TestE2EStubGate` (Pillar A4).
- Worker env propagation regression test in `tests/test_auto_cmd.py`
  (Pillar A2) pinning the `os.environ.copy()` contract.
- Fixture `tests/fixtures/parallel-e2e/dot-claude-settings.json`
  with explicit permissions allow list (`Write/Edit` for scratch/,
  tests/, src/ + `Bash` for pytest/ruff/mypy) per Pillar B1.
- Section "Known upstream limitations" in CLAUDE.md documenting
  the `claude -p /test-driven-development` cwd-dependent hang
  (Pillar B2).
- Memory archive `project_v108_claude_p_hang_upstream.md` with
  full diagnostic context + staged upstream report content
  (Pillar B2; **local-only**, NOT test-asserted).
- Doc coherence smoke tests in `tests/test_doc_coherence_v108.py`
  for Pillar B2 CLAUDE.md + CHANGELOG sections.

### Changed

- `tests/test_auto_parallel_e2e.py` redesigned (Pillar A3): no
  longer `@pytest.mark.xfail`. Subprocess env carries
  `SBTDD_E2E_STUB_DISPATCH=1`. Timeout shrunk 600s → 60s. Strict
  happy-path assertions per Q4'=a+: rc=0, state=done, plan fully
  flipped, sidecars present with verify_chain of `>= 4` entries
  (extensible per iter-2 Cas-W10) + per-tool presence check for
  the 4 known sec.0.1 tools (pytest, ruff, mypy), each rc=0,
  audit finished + success.
- `_stage_fixture` helper in `tests/test_auto_parallel_e2e.py`
  materializes `<dest>/.claude/settings.json` from the fixture
  (Pillar B1).

### Honest scope caveats (iter-2 carry-forward Bal-W5)

- After v1.0.8 lands, `tests/test_auto_parallel_e2e.py` is an
  **INFRASTRUCTURE test** — it validates env propagation, worker
  spawn, sec.0.1 chain bypass, sidecar persistence, and
  parent-side hooks. It does **NOT** exercise the real
  `/test-driven-development` LLM dispatch semantics. Production
  coverage of the dispatch path is preserved via mocked unit
  tests in `test_auto_cmd.py` + `test_close_phase_cmd.py`. A
  **CI integration test** for real dispatch (against a fixture
  with proper `.claude/settings.json`) is rolled to v1.0.9 LOCKED.
- T3 e2e PASSES on **Windows** (mandatory development env).
  **POSIX validation deferred** to CI infrastructure per v1.0.7
  W5 carry-forward (iter-2 Cas-I8).

### Process notes

v1.0.7 PRIORITY LOCKED T3 e2e empirical closure shipped. v1.0.8
diagnostic 2026-05-14 ruled out 4 of 5 v1.0.7 hypotheses (env
propagation, pytest recursion, residual A2 bug, Windows PIPE
buffer fill); root cause confirmed as upstream `claude -p` hang
in fixture-style cwd. Q1'=a baseline stubbable skills set;
Q2'=a minimal marker stdout; Q3'=a explicit permissions allow
list; Q4'=a+ deterministic assertions; Q5'=a G2 ladder
pre-staged.

**Red-phase commit methodology adjustment** (iter-2
Mel-W3+Cas-W9): v1.0.8 plan replaced the v1.0.7-precedent
temporary `@pytest.mark.xfail` workaround with raw
`git commit -m "test: ..."` for Red commits. State stays at
`current_phase=red` after Red; advances at Green close-phase.
No 6-commit window where a stale marker could survive past
Green.

Production semantics preserved — Pillar A is TEST-ONLY;
`SBTDD_E2E_STUB_DISPATCH` is namespaced + documented test-only
+ runtime-guarded via `pytest in sys.modules`. Production
workers continue to do real TDD work via real `claude -p`
dispatch. G1 cap=3 HARD Checkpoint 2 no-override 9-cycle streak
preserved (v1.0.0..v1.0.8). Pre-merge Loop 2 3-cycle
no-override streak preserved (v1.0.5+v1.0.7+v1.0.8).

### Deferred (rolled to v1.0.9 LOCKED)

Per iter-2 carry-forward Bal-W6+Bal-W7+Cas-W13, v1.0.9 LOCKED
milestones:

1. **Resolve `/sbtdd pre-merge` orchestrator-side hang**
   (chicken-and-egg). Subcommand-based pre-merge should work
   end-to-end without manual `run_magi.py` fallback. Closes
   the 9-cycle methodology debt of manual MAGI fallback.
2. **CI integration test exercising real `/test-driven-development`
   dispatch** against a known-good fixture project (with proper
   `.claude/settings.json`), as the integration safety net
   post-v1.0.8 stub gate. Backstops the honest scope caveat
   from this CHANGELOG entry.
3. **Re-evaluate stub gate runtime-guard strength**: if field
   observation shows pytest-sys.modules guard has false-negatives
   (e.g., pytest-in-IDE workflows), consider AND-gating with a
   second env var like `SBTDD_E2E_STUB_ARMED=1` for explicit
   opt-in.
4. **Upstream report submission to `anthropics/claude-code`**
   (Pillar B2 stages content in memory; user decides post-v1.0.8
   ship per spec sec.5 scope exclusions).

Other v1.0.7 deferred carry-forward (B2 worker subprocess
auto-message hardening, C2 K-4 escape hatch test coverage, C4
NF-B test count rebaseline, C8 F-A2 abort criterion diagnosis
hint); Pillar D v1.0.5 polish carry-forward; Edge cases E1-E3.

### Deferred (rolled to v1.1.0)

- Stub gate production-promotion decision review (whether to
  promote `SBTDD_E2E_STUB_DISPATCH` semantics into a production
  worker-mode bypass for `/test-driven-development`).
- All v1.0.4 carry-forward inherited items.

```

- [ ] **Step 8: Run the Green doc-coherence tests + full sec.0.1 chain**

Run: `pytest tests/test_doc_coherence_v108.py -v`
Expected: 2 PASSED.

Run: `make verify`
Expected: clean sec.0.1 chain.

- [ ] **Step 9: Close Green phase**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --variant feat --message "v1.0.8 T6 Green: add Known upstream limitations section + memory archive + CHANGELOG [1.0.8]"`

Expected: `feat:` commit.

- [ ] **Step 10: Write the Refactor — tighten CHANGELOG cross-references**

In `CHANGELOG.md` `[1.0.8]` "Process notes" section, after the line ending `Q5'=a G2 ladder pre-staged.`, append one more sentence:

```
See `sbtdd/spec-behavior.md` v1.0.8 sec.1 (Resumen ejecutivo Q1'-Q5'
resolutions) + sec.6 (G1/G2 binding stance) for full decision
rationale.
```

- [ ] **Step 11: Run sec.0.1 chain after refactor**

Run: `pytest tests/test_doc_coherence_v108.py -v`
Expected: 2 PASSED.

Run: `make verify`
Expected: clean.

- [ ] **Step 12: Close Refactor phase + Task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase --message "v1.0.8 T6 Refactor: cross-reference Q1'-Q5' decisions to spec sections in CHANGELOG"`

Expected: `refactor:` commit + close-task cascade (T6 checkbox `[x]`, state advances to `done` since T6 is the last task).

---

## Post-Task: Own-cycle dogfood activities (orchestrator)

Per spec sec.2.7 + sec.4.7 + sec.5.3, after all 6 tasks close, the orchestrator runs the dogfood activities.

### Activity D — `make verify` clean pass (NON-NEGOTIABLE)

- [ ] **Step D-1**: Run `make verify` from repo root.

Expected:
- pytest: 1309-1312 tests + 1 skipped, 0 failed
- ruff check: 0 warnings
- ruff format check: clean
- mypy --strict: 0 errors
- coverage: >= 88% (no regression below v1.0.7's 89.46%)
- wall-time: <= 200s soft / <= 220s hard

If any check fails: halt; do not proceed to pre-merge. Diagnose + fix + re-run.

### Activity E — Pre-merge gate end-to-end

- [ ] **Step E-1**: Attempt `python skills/sbtdd/scripts/run_sbtdd.py pre-merge` (orchestrator-side).

Expected:
- Loop 1 (`/requesting-code-review`) reaches clean-to-go within 10 iter cap.
- Loop 2 (`/magi:magi`) reaches verdict `>= GO_WITH_CAVEATS` full no-degraded within 5 iter cap.
- NO INV-0 override.

- [ ] **Step E-2 (fallback)**: If `/sbtdd pre-merge` hangs (same upstream bug class as v1.0.7 dogfood):
  - Run `python skills/magi/scripts/run_magi.py` manually with the cumulative diff + spec + plan.
  - Apply Loop 2 findings via mini-cycles per CLAUDE.local.md §6.
  - Document the fallback usage in CHANGELOG `[1.0.8]` Process notes (post-impl commit).

### Activity F — Production regression check

- [ ] **Step F-1**: Run the v1.0.7 worker-mode bypass tests:

```bash
pytest tests/test_close_phase_cmd.py -k "run_verification or worker_mode" -v
pytest tests/test_auto_cmd.py -k "dispatch" -v
pytest tests/test_parallel_dispatcher.py -v
```

Expected: all 19+ tests still PASS. No regression in production worker bypass semantics.

---

## Ship checklist (per CLAUDE.local.md §7)

After Activities D + E + F all green:

- [ ] All 6 task checkboxes in this plan flipped to `[x]`.
- [ ] `.claude/session-state.json` reports `current_phase: "done"`.
- [ ] `make verify` clean (Activity D).
- [ ] `git status` clean (working tree, no untracked from plan scope).
- [ ] CHANGELOG `[1.0.8]` entry present (per T6).
- [ ] Pre-merge MAGI verdict captured (Loop 2 clean GO_WITH_CAVEATS or better, full no-degraded).
- [ ] Version bump: `plugin.json` 1.0.7 → 1.0.8 + `marketplace.json` 1.0.7 → 1.0.8.
- [ ] Merge `feature/v1.0.8-bundle` → `main` (with explicit user authorization per memory `feedback_never_commit_without_explicit_request`).
- [ ] Tag `v1.0.8` + push (with explicit user authorization).

---

## Self-review (writing-plans skill checklist)

**1. Spec coverage** — every spec section mapped to a task:
- A1 (gate impl) → T1 ✓
- A2 (env propagation regression) → T2 ✓
- A3 (T3 redesign) → T4 ✓
- A4 (gate regression tests) → T3 ✓
- B1 (fixture hardening) → T5 ✓
- B2 (docs + memory + CHANGELOG) → T6 ✓
- Dogfood activities D/E/F → Post-Task section ✓
- Ship checklist (CLAUDE.local.md §7) → Ship section ✓

**2. Placeholder scan**: cero matches uppercase placeholder markers (the three INV-27 word-boundary patterns) in this plan. Every step contains actual content (test code, impl code, exact commands with expected outcomes).

**3. Type consistency**: identifiers used consistently across tasks:
- `_E2E_STUB_ENV`, `_E2E_STUBBABLE_SKILLS`, `SBTDD_E2E_STUB_DISPATCH` — same naming in T1 impl + T2/T3/T4 tests.
- `SkillResult`, `subprocess_utils.run_with_timeout`, `invoke_skill` — same fully-qualified references across tasks.
- `_stage_fixture`, `_FIXTURE_DIR`, `_FIXTURE_SETTINGS_JSON` (added T5) — consistent.
- `TestE2EStubGate.test_gate_*` method names — same in T3 Red, Green, Refactor.

**4. Ordering dependency check**: T1 before T3+T4 (gate exists); T5 before T4 (fixture has settings.json); T6 parallel-safe with T1/T2/T3/T5. Documented in plan header `Task ordering` block. Spec sec.5.1 single-track sequential remains default.

---

## Execution handoff

Plan complete. Per project convention (single-track sequential subagent-driven per v1.0.6+v1.0.7 chicken-and-egg precedent), recommended approach:

**Recommended: Subagent-Driven Development (sequential, fresh subagent per task)**
- Dispatch subagent for T1; await close-task cascade; review diff; dispatch T2; etc.
- Each subagent fresh context — no contamination across tasks.
- Two-stage review (subagent self-review + orchestrator review) per CLAUDE.local.md §6 conventions.

Pending MAGI Checkpoint 2 review of this plan + user approval. Once `plan_approved_at` is set in state, the close-phase auto-commit contract takes effect and the 4-category commit authorization unlocks per CLAUDE.local.md §5.
