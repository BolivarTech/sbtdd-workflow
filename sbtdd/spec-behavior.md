# BDD overlay — sbtdd-workflow v1.0.8

> Generado 2026-05-14 a partir de `sbtdd/spec-behavior-base.md` v1.0.8.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1+v1.0.2+v1.0.3+v1.0.4
> +v1.0.5+v1.0.6+v1.0.7 precedent (chicken-and-egg until v1.0.8
> Pillar A ships + v1.0.9 own-cycle validates empirically).
>
> v1.0.8 = **T3 e2e empirical chicken-and-egg closure via test-only
> stub gate (PRIORITY LOCKED)** per user mandate 2026-05-10. v1.0.8
> diagnostic 2026-05-14 empirically ruled out 4 of 5 v1.0.7
> hypotheses; root cause confirmed: worker `_phase2_task_loop`
> invokes `superpowers_dispatch.test_driven_development(...)` which
> spawns `claude -p /test-driven-development` — a real LLM dispatch
> that **hangs indefinitely in the synthetic fixture cwd** (>180s
> zero output, empirically verified). Two pillars:
>
> - **Pillar A PRIMARY (HARD-LOCKED)** — env var stub gate at top
>   of `superpowers_dispatch.invoke_skill` (A1) + worker env
>   propagation regression test (A2) + T3 redesign unxfailed (A3)
>   + 4 gate regression tests (A4).
> - **Pillar B LOCKED (defensive + archival)** — fixture
>   `.claude/settings.json` hardening (B1) + CLAUDE.md "Known
>   upstream limitations" section + memory archive of upstream bug
>   (B2). Upstream report submission DEFERRED to user post-v1.0.8.
>
> Source of truth autoritativo para
> v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5
> +v1.0.6+v1.0.7 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex. R5 compliant:
> frontmatter docstring above.

---

## Iter-2 carry-forward — Checkpoint 2 iter 1 triage applied 2026-05-14

> Per CLAUDE.local.md §6 v1.0.0+ carry-forward block format. Verdict
> iter 1: GO_WITH_CAVEATS (3-0) full no-degraded — Mel CONDITIONAL
> 74% + Bal APPROVE 82% + Cas CONDITIONAL 78%. 0 CRITICAL + 13
> WARNINGs + 8 INFOs. 11 of 13 WARNINGs accepted + 5 of 8 INFOs
> accepted; 2 WARNINGs + 3 INFOs rejected with grounded rationale.
> Structural changes applied warrant iter 2 re-invocation per
> CLAUDE.local.md §6 Gate MAGI table.

| Iter | Severity | Title (verbatim from iter 1) | Decision | Rationale |
|------|----------|------------------------------|----------|-----------|
| 1 | warning | T2 regression test likely fails for the wrong reason (missing dispatcher scaffolding) _(mel)_ | keep | Resolved plan T2 Step 2 monkeypatches: add `close_task_cmd._merge_scratch_plans` stub (auto_cmd.py:2124 getattr fallback). Other dispatcher internals safe via `ns=None` minimal-argv path. |
| 1 | warning | T2 violates Red→Green semantics; Step 6 comment-only diff games _preflight _(mel)_ | keep | Resolved plan T2 Green: substantive doc update — docstring extension on `_dispatch_tracks_concurrent` documenting the env propagation contract + inline comment block. Two doc surfaces, not a 1-line comment. |
| 1 | warning | Reliance on temporary `@pytest.mark.xfail` to land Red commits is brittle _(mel)_ | keep | Resolved methodology: Red commits use raw `git commit -m "test: ..."` (CLAUDE.local.md §5 authorized prefix under plan-approved contract); close-phase invoked only for Green + Refactor (state advance). Removed all `@pytest.mark.xfail` temporary-marker instructions from plan. Documented as methodology adjustment in plan header. |
| 1 | warning | T3 `test_gate_does_not_fire_when_env_unset` may trip on `_apply_inv0_model_check` or `_build_skill_cmd` side-effects _(mel)_ | reject | Evidence: `superpowers_dispatch.py:169-170` `_apply_inv0_model_check(configured_model=None, ...)` short-circuits at `if configured_model is None: return None` BEFORE any I/O. The test calls `invoke_skill(...)` with default `model=None`, so the function returns None immediately. `_build_skill_cmd` is pure list construction (no I/O). Path is safe. |
| 1 | warning | Stub gate trades real e2e coverage for test determinism — be honest about it _(bal)_ | keep | Resolved CHANGELOG `[1.0.8]` Added + SKILL.md v1.0.8 notes: explicit caveat that T3 is now an infrastructure test (env propagation + sidecar + audit + sec.0.1 chain bypass); real `/test-driven-development` dispatch is NOT exercised by T3. Production coverage via unit tests in test_auto_cmd.py + test_close_phase_cmd.py only. |
| 1 | warning | Methodology debt: 9th consecutive cycle on manual MAGI fallback signals self-hosting limit _(bal)_ | keep | Resolved CHANGELOG `[1.0.8]` Deferred section: explicit v1.0.9 LOCKED milestone "resolve `/sbtdd pre-merge` orchestrator-side hang (chicken-and-egg) for subcommand-based pre-merge end-to-end". Don't let methodology debt slide indefinitely. |
| 1 | warning | Long-term env-var collision risk needs a v1.0.9 follow-up _(bal)_ | keep (combined with W11) | See Cas-W11 resolution — `if "pytest" not in sys.modules` runtime guard added to Item A1 in v1.0.8 (NOT deferred). Combined fix covers both. |
| 1 | warning | TDD gaming in T2: Red test designed to pass immediately, Green is a one-line comment _(cas)_ | keep (duplicate of W2) | Same fix as Mel-W2 (substantive Green doc). |
| 1 | warning | Temporary xfail markers proposed to bypass close-phase Red verification (T3/T5/T6) _(cas)_ | keep (duplicate of W3) | Same fix as Mel-W3 (raw git commit for Red). |
| 1 | warning | verify_chain `exactly 4 entries` assertion is brittle to future sec.0.1 extensions _(cas)_ | keep | Resolved escenarios A3-2 + A3-3 + plan T4: change `len(chain) == 4` to `len(chain) >= 4` + explicit per-tool presence assertion checking the 4 known commands (`pytest`, `ruff check`, `ruff format --check`, `mypy`) appear in the chain. |
| 1 | warning | Stub gate placement bypasses ALL defense-in-depth with no runtime production safeguard _(cas)_ | keep | Resolved Item A1 implementation: added `if "pytest" not in sys.modules: gate inactive` runtime guard. Workers / production processes do NOT import pytest at runtime (close_phase invokes pytest via separate `[sys.executable, "-m", "pytest"]` subprocess), so accidental env var leak into production has ZERO effect — gate cannot fire without pytest loaded. Strong defense-in-depth at runtime, not just naming convention. |
| 1 | warning | Escenario B2-2 hardcodes a user-specific memory path that is not in the repo _(cas)_ | keep | Resolved escenario B2-2: rephrased to clarify the memory file lives in the user's per-project Claude memory dir (OUTSIDE the repo), is NOT test-asserted, and is verified by human review of the closing commit narrative. Only CLAUDE.md + CHANGELOG are test-asserted (via `tests/test_doc_coherence_v108.py` per plan T6). |
| 1 | warning | R1 mitigation overstated: no test exercises real `/test-driven-development` dispatch end-to-end after stub lands _(cas)_ | keep (partial) | Resolved sec.8 R1: honest mitigation phrasing — production T1+T2 unit tests preserve UNIT coverage via mocked subprocess; NO automated INTEGRATION test exercises real `/test-driven-development` post-v1.0.8. Manual smoke-test via `/sbtdd auto` on a real project remains the integration safety net. CI integration → v1.0.9 LOCKED backlog. |
| 1 | info | Test count arithmetic in NF-B doesn't quite match plan additions _(mel)_ | keep | Resolved NF-B: tightened from "~5-8 nuevos = ~1309-1312 final" to "~8 nuevos = 1312 final". Exact count: T1 (1 smoke) + T2 (1 regression) + T3 (4 gate) + T6 (2 doc-coherence) = 8 net new. |
| 1 | info | Gate ordering vs v1.0.7 A2 worker-context guard is correct but document precedence rationale _(mel)_ | keep | Resolved Item A1 docstring: added explicit precedence note that the stub gate fires before A2 worker-context guard — when both `SBTDD_E2E_STUB_DISPATCH=1` AND `SBTDD_AUTO_PARALLEL_WORKER=1` are set, stub wins (correct for test path). |
| 1 | info | Risk R2 mitigations sound but runtime warning would harden it further _(mel)_ | reject | Superseded by Cas-W11 stronger fix (`pytest in sys.modules` runtime guard). The pytest-loaded check is a stricter defense-in-depth than a stderr warning, so a separate runtime warning would be redundant noise. |
| 1 | info | Task 6 applies full TDD ceremony to what is essentially a doc commit _(bal)_ | reject | Doc-coherence smoke tests have real value (pin cross-artifact wording requirement); the TDD ceremony enforcing them is CLAUDE.local.md §3 strict policy. Removing the ceremony would create a methodology exception that's harder to justify than the slight overhead. No change. |
| 1 | info | T2 Step 6 'add a throwaway comment' exposes process friction _(bal)_ | keep (same as W2) | Resolved by T2 restructure (substantive Green doc). |
| 1 | info | Memory file path is Windows-absolute; document OS portability or use a relative path _(bal)_ | keep (same as W12) | Resolved by B2-2 rephrase + plan T6 Step 5 clarification that the memory file is local-only outside the repo. |
| 1 | info | Plan ordering, Q-decisions, and G2 scope-trim ladder are sound _(bal)_ | n/a | Positive validation; preserved. |
| 1 | info | POSIX acceptance criteria ambiguous — `T3 e2e PASSES` covers Windows only _(cas)_ | keep | Resolved NF-B + sec.6 acceptance criteria: explicit "T3 e2e PASSES on Windows (mandatory); POSIX validation deferred to CI per v1.0.7 W5 carry-forward". Updated CHANGELOG language to mirror. |

**Scope-trim ladder NOT invoked**: 0 CRITICAL findings in iter 1 means G2 scope-trim default does NOT fire. All 6 plan tasks (T1+T2+T3+T4+T5+T6) stay in scope; Pillar A hard-LOCKED, Pillar B preserved.

---

## Checkpoint 2 close-out — iter 2 convergence 2026-05-14

> Verdict iter 2: GO_WITH_CAVEATS (3-0) full no-degraded — Mel
> APPROVE 82% + Bal APPROVE 82% + Cas CONDITIONAL 76%. 0 CRITICAL
> + 8 WARNINGs + 9 INFOs (down from 13W + 8I in iter 1 —
> convergence pattern). G1 cap=3 HARD respected with margin
> (converged at iter 2). **9-cycle Checkpoint 2 no-override
> streak preserved** (v1.0.0..v1.0.8 = 9 consecutive sin INV-0).

Per CLAUDE.local.md §6 GO_WITH_CAVEATS full no-degraded path: "Si
bajo riesgo (doc/tests/naming/logging/msgs/comentarios), sale sin
re-evaluar". Caspar's 3 Conditions for Approval (the only holdout
finding cluster) are bajo-riesgo polish per Caspar's own framing
("should be folded during impl, not deferred to v1.0.9"):

1. **Cas-W4+Cas-W7 (TDD-Guard hazard during Green write window)**
   — RESOLVED via plan-header documented `tdd-guard off/on`
   toggle pattern for tasks T1+T2+T5+T6 Green phases that edit
   non-test files. Well-precedented per CLAUDE.local.md §3
   multi-agent rules; operator-scope only (subagents cannot
   toggle). Spec sec.4 escenarios unchanged (no behavior change
   needed).
2. **Cas-W5+Mel-W3 (verify_chain `cmd[2]` positional fragile)**
   — RESOLVED via substring-anywhere matching in plan T4 Step 2
   + Step 8 helper. Tool detection scans `" ".join(cmd)` for
   each known tool name; future cmd-shape evolution (e.g.,
   `python -X dev -m pytest`, env wrappers) cannot break the
   assertion. Spec escenario A3-3 wording updated below to
   match.
3. **Cas-W6 (T4 Red phase depends on external upstream behavior)**
   — RESOLVED via static `grep` verification in plan T4 Step 3.
   Replaced "run test, expect fail/timeout" with deterministic
   source-code inspection: assert `SBTDD_E2E_STUB_DISPATCH` NOT
   yet in test file + strict assertions in place + no leftover
   xfail decorator. The actual e2e test execution happens in
   Step 6 (Green) once env var is added.

Mel + Bal explicitly recommended NO iter 3 ("none warrant a
third iter" — Bal; "Apply at GO_WITH_CAVEATS full no-degraded"
— Mel). Caspar agreed: "With these conditions applied, this
bundle is ship-ready and preserves the 9-cycle Checkpoint 2
no-override streak."

Remaining 5 INFOs from iter 2 (memory file audit trail
unauditable, smoke-test cadence commitment, T2 characterization
acceptable, pytest IDE edge case in v1.0.9, phase_started_at_commit
under raw-Red methodology) are deferred to v1.0.9 backlog OR
ACK-ed as positive validations (Bal-I3/I4/I5/I6/I7). No further
spec/plan changes required.

**Checkpoint 2 EXIT: ship-ready at GO_WITH_CAVEATS (3-0) full
no-degraded**. Plan ready for user approval gate (Phase 5);
post-approval, dispatch impl phase per plan sec.5.1 single-track
sequential subagent execution.

---

## v1.0.8 implementation design pivot (post-Checkpoint 2, recorded
at pre-merge Loop 2 iter 1 — 2026-05-15)

> Per Loop 2 iter-1 Mel-W4/Bal-W1/Cas-W3 findings: spec/impl drift
> on the W11 runtime safeguard. Recording the as-shipped design here
> rather than rewriting all sec.4 / sec.2 escenarios that reference
> the original pytest-sys.modules guard. The spec text below remains
> as the Checkpoint-2-approved design baseline; this pivot section is
> authoritative for the as-shipped behavior.

**Design pivot**: the gate's runtime production safeguard switched
from Caspar W11 option (a) `"pytest" in sys.modules` to Caspar W11
option (b) AND-gate on a second env var `SBTDD_E2E_TEST_RUNNER`.

**Reason**: T4 implementation diagnostic revealed that the pytest
sys.modules check fails to fire in the legitimate e2e use case
where `tests/test_auto_parallel_e2e.py` spawns
`python run_sbtdd.py auto --parallel` as a subprocess. The
subprocess inherits env vars via `os.environ.copy()` but does NOT
import pytest in the subprocess process (auto_cmd has no pytest
runtime dependency). The original (a) guard correctly classified
the subprocess as "production-mode" but in this specific case the
subprocess IS a test-spawned process that needs the gate to fire.

**Defense-in-depth preserved**: option (b) requires BOTH env vars
set simultaneously. Production accidental leak of a single env var
(via shared shell profile, devcontainer template, `.env` copy) has
zero effect. Both vars must leak together for the gate to fire — a
much lower probability event than single-var leak.

**Approved at Loop 2 iter 1 (within Caspar W11's pre-approved
design space)**: Caspar explicitly listed option (b) as one of the
three valid alternatives in iter 1 finding W11. Switching from (a)
to (b) is within the design space MAGI already approved; no new
design surface introduced.

**As-shipped gate condition** (per `superpowers_dispatch._e2e_stub_active()`):

```python
def _e2e_stub_active() -> bool:
    return (
        os.environ.get(_E2E_STUB_ENV) == "1"
        and os.environ.get(_E2E_TEST_RUNNER_ENV) == "1"
    )
```

Used by 4 callsites: `superpowers_dispatch.invoke_skill` (T1 + T4
expansion), `spec_review_dispatch.dispatch_spec_reviewer` (T4
expansion), `magi_dispatch.invoke_magi` (T4 expansion),
`auto_cmd._verify_worker_sidecars_present` (T4 expansion +
Loop 2 iter-1 Cas-W1 fix). Single-sourced predicate per Loop 2
iter-1 Mel-W3 fix.

**Escenario A1-6 supersession**: the escenario in sec.4.1 still
describes the pytest sys.modules check as the production safeguard.
As shipped, replace mentally:
- "`"pytest" NOT in sys.modules`" → "second env var
  `SBTDD_E2E_TEST_RUNNER` NOT set to `"1"`"
- The behavior contract (gate does NOT fire when production
  conditions hold) remains identical; only the runtime mechanism
  changed.

A spec-base + spec-behavior rewrite reconciling all escenarios to
the AND-gate as shipped is **v1.0.9 LOCKED**: "spec/impl drift
reconciliation post v1.0.8 W11 pivot". Until then, this section is
the authoritative as-shipped reference.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.8**: cerrar la brecha empirica de v1.0.7 T3 e2e via
un gate test-only en `superpowers_dispatch.invoke_skill`. Despues
de v1.0.8:

- T3 e2e test (`tests/test_auto_parallel_e2e.py`) ya no esta xfail.
- T3 corre en <60s en lugar de timeout-ing a 600s.
- T3 valida el **chicken-and-egg surface real** que v1.0.7 A1+A2
  fue disenado para cerrar (workers alcanzan `_run_verification`
  worker-mode bypass via sec.0.1 chain, sin TTY-dependent hang).
- T3 aisla la validacion del costo + upstream bug del dispatch real
  de `/test-driven-development`.

Decisiones macro (resueltas en brainstorming 2026-05-14):

- **Q1' (stub gate scope) = a**: `_E2E_STUBBABLE_SKILLS = frozenset(
  {"test-driven-development", "systematic-debugging"})`. Minimo
  scope. YAGNI — `/brainstorming` y `/writing-plans` ya estan
  membership-gated en `_SUBPROCESS_INCOMPATIBLE_SKILLS`; no hay
  e2e test que los exercise actualmente.
- **Q2' (stub stdout content) = a**: marker minimal
  `[sbtdd e2e stub] /{skill} bypassed (SBTDD_E2E_STUB_DISPATCH=1)`.
  Sin args, sin cwd, sin timestamp. El worker no parsea stdout —
  solo `returncode`. Marker sirve para grep en post-mortems;
  entropy adicional rompe asserts deterministas.
- **Q3' (fixture permissions) = a**: lista explicita de allow
  rules (`Write/Edit` para `scratch/**` + `tests/**` + `src/**`;
  `Bash(pytest *)` + `Bash(ruff *)` + `Bash(mypy *)`). Sin `**`
  wildcard — wildcard oculta futuros bugs de permissions con
  overpermissive grant.
- **Q4' (T3 assertion strictness) = a+**: asserts deterministas =
  `rc==0` + `current_phase=="done"` + plan sin `^- [ ]` lines + >=1
  sidecar + cada sidecar con `verify_chain` de exactamente 4
  entries (pytest+ruff check+ruff format+mypy) cada uno rc=0 +
  `auto_finished_at` non-null + `status=="success"`. **Omitir**
  assert exact commit count (case-3 `--allow-empty` fallback + worker
  filter producen counts subtle — invitan flakiness).
- **Q5' (MAGI Checkpoint 2 budget + G2 ladder pre-stage) = a**:
  bundle pequeno (4 A + 2 B = 6 items). Esperar 1-2 iters
  convergence. Iter 3 trigger G2 scope-trim default: defer B2
  first (archival-only, low value-per-cost) → defer B1 second
  (defensive but not blocking) → Pillar A hard-LOCKED.

**Hybrid methodology continued**: brainstorming + writing-plans
in-session via Skill tool (NO `claude -p` subprocess —
chicken-and-egg until v1.0.8 Pillar A lands + v1.0.9 own-cycle
validates). Opcion A manual `run_magi.py` for Checkpoint 2 + Loop
2 dispatch per v1.0.2..v1.0.7 precedent.

**Criterio de exito v1.0.8**:

- Tests baseline 1304 + 1 skipped + ~5-8 nuevos = ~1309-1312 final.
- `make verify` runtime <= 200s soft / 220s hard.
- Coverage threshold mantenido en 88% (v1.0.7 89.46%; v1.0.8 no
  regresion below 88%).
- **T3 e2e PASSES (not xfail)** en <60s con
  `SBTDD_E2E_STUB_DISPATCH=1` en subprocess env. Empirical
  chicken-and-egg closure CONFIRMED end-to-end.
- **G1 binding HARD respetado**: cap=3 sin INV-0. **9-cycle
  Checkpoint 2 no-override streak goal** (v1.0.0..v1.0.8
  consecutive).
- **Pre-merge Loop 2 streak**: 3-cycle goal (v1.0.5+v1.0.7+v1.0.8
  consecutive sin INV-0).

---

## 2. Items LOCKED

### 2.1 Item A1 — `SBTDD_E2E_STUB_DISPATCH` env var stub gate (Pillar A PRIMARY HARD-LOCKED)

**Track**: single subagent (T1 first; bloqueante para A3+A4 tests).

**Archivos**:
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  - Add module-level constant `_E2E_STUB_ENV: str = "SBTDD_E2E_STUB_DISPATCH"`
  - Add module-level constant `_E2E_STUBBABLE_SKILLS: frozenset[str] =
    frozenset({"test-driven-development", "systematic-debugging"})`
  - Add gate as FIRST check at top of `invoke_skill` body
- Update docstring of `invoke_skill` documenting the gate + explicit
  test-only warning + production caveat.

**Empirical context (v1.0.8 T3 diagnostic 2026-05-14)**:

`tests/test_auto_parallel_e2e_chicken_and_egg_closed` (v1.0.7 A3)
xfail-marked because subprocess timeout at 600s. v1.0.8 diagnostic
empirically traced root cause via 3 reproducer scripts in
`.tmp_repro/` (gitignored):

1. `repro_t3.py`: full subprocess via test path → workers spawn but
   timeout at 60s with stdout/stderr empty (orchestrator captures
   worker output via PIPE without surfacing).
2. `repro_worker.py`: single worker direct spawn → emits breadcrumb
   `[sbtdd] phase 2/5: task loop -- task 1/4 (red)` then hangs;
   confirms worker reached `_phase2_task_loop` entry and hangs at
   `superpowers_dispatch.test_driven_development(...)`.
3. `repro_skill_with_fixture_cwd.py`: claude -p direct invocation
   with cwd=fixture-temp-dir → hangs >180s zero output. Same
   command in cwd=SBTDD repo: rc=0 in 66s. Same command in
   cwd=empty temp dir: rc=0 in 30s. Bug is cwd-dependent on
   fixture-style file layout WITHOUT `.claude/settings.json` +
   `CLAUDE.md`.

4 of 5 v1.0.7 hypotheses ruled out by evidence:
- env propagation works (worker received SBTDD_AUTO_PARALLEL_WORKER=1)
- pytest recursion never reached (hang occurs BEFORE pytest)
- A2 fix is correct (only bypasses `/verification-before-completion`,
  not implementer skill — out-of-scope for v1.0.7 A2)
- Windows PIPE buffer not full (only 1 line of worker stderr
  emitted before hang)

Single remaining hypothesis CONFIRMED: `/test-driven-development`
is an LLM-driven code-generation call that hangs upstream in the
fixture cwd.

**Implementation outline** (revised per iter-2 carry-forward W11+W7
combined fix — pytest sys.modules runtime guard + I2 precedence
docstring note):

```python
# superpowers_dispatch.py module-level (after _SUBPROCESS_INCOMPATIBLE_SKILLS)

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
#: :func:`invoke_skill` checks ``"pytest" in sys.modules`` — production
#: workers do NOT import pytest at runtime (they invoke pytest as a
#: separate subprocess via ``[sys.executable, "-m", "pytest"]`` in
#: :func:`close_phase_cmd._run_verification` worker-mode bypass), so
#: the gate cannot fire in production. Test runners (pytest itself,
#: pytest-cov, conftest.py loaders) load pytest into sys.modules
#: BEFORE collecting tests, so the gate fires correctly in test
#: environments.
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


def invoke_skill(skill, args=None, ..., allow_interactive_skill=False):
    """... existing v1.0.7 docstring ...

    v1.0.8 Pillar A1 addendum: test-only stub gate. When the env var
    :data:`_E2E_STUB_ENV` (``SBTDD_E2E_STUB_DISPATCH``) is set to
    ``"1"`` AND ``"pytest"`` is in :data:`sys.modules` AND ``skill``
    is in :data:`_E2E_STUBBABLE_SKILLS`, this function short-circuits
    to a synthetic ``SkillResult(rc=0)`` without spawning
    ``claude -p``. The gate is checked FIRST so it short-circuits
    ALL downstream dispatch logic.

    **Gate precedence** (iter-2 carry-forward I2): the v1.0.8 A1
    stub gate is positioned BEFORE the v1.0.7 A2 worker-context
    guard, the v1.0.6 J-3 headless guard, and the v1.0.4 membership
    gate. When both ``SBTDD_E2E_STUB_DISPATCH=1`` AND
    ``SBTDD_AUTO_PARALLEL_WORKER=1`` are set (test scenario where
    the parent test sets the stub env var, which propagates to
    worker subprocess via ``os.environ.copy()`` per A2), the stub
    gate wins — correct for the test path because the worker would
    otherwise crash on its inability to dispatch to claude -p.

    **Defense-in-depth via pytest sys.modules guard** (iter-2
    carry-forward W11): the gate requires both the env var AND
    ``"pytest" in sys.modules``. Production processes (auto_cmd
    orchestrator, worker subprocesses spawned via
    ``_dispatch_tracks_concurrent``) do NOT import pytest at
    runtime, so even if ``SBTDD_E2E_STUB_DISPATCH=1`` is
    accidentally exported in production (e.g., CI config leak,
    shared shell profile, copied dev environment), the gate
    remains inactive. This converts the gate from "test-by-
    convention" (naming + docstring + frozen membership set) to
    "test-by-runtime-check" (pytest module presence is verifiable
    at gate evaluation time).
    """
    # v1.0.8 Pillar A1: test-only stub gate. Checked FIRST so it
    # short-circuits ALL downstream dispatch logic (v1.0.4
    # membership gate + v1.0.6 J-3 headless guard + v1.0.7 A2
    # worker-context guard). Three conjunctive conditions:
    #   1. SBTDD_E2E_STUB_DISPATCH=1 in environment (test sets it)
    #   2. "pytest" in sys.modules (runtime guard against env leak)
    #   3. skill is in _E2E_STUBBABLE_SKILLS (frozen membership)
    # Production processes fail condition 2 even if they accidentally
    # have condition 1 set.
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
    # ... v1.0.7 gate logic preserved unchanged below ...
```

### 2.2 Item A2 — Worker env propagation regression (Pillar A)

**Track**: single subagent (T2, after T1).

**Archivos**:
- Verify (no code change): `skills/sbtdd/scripts/auto_cmd.py`
  line ~2061 (`worker_env = os.environ.copy()`)
- Extend: `tests/test_auto_cmd.py` with 1 regression test pinning
  the contract that all env vars (including
  `SBTDD_E2E_STUB_DISPATCH`) propagate from parent → worker env.

**Implementation note**: `os.environ.copy()` already passes all env
vars through. The new test fixates the contract so a future refactor
that introduces env var filtering would surface as a regression.

### 2.3 Item A3 — T3 e2e test redesign (Pillar A)

**Track**: single subagent (T4, after T1+T2+A4 regression tests
landed so the gate semantics are tested-before-used).

**Archivos**:
- Modify: `tests/test_auto_parallel_e2e.py`
  - Remove `@pytest.mark.xfail` decorator from
    `test_auto_parallel_e2e_chicken_and_egg_closed`
  - Set `env["SBTDD_E2E_STUB_DISPATCH"] = "1"` in subprocess `env`
    dict; preserve full `os.environ.copy()` baseline so
    claude/git/pytest/ruff/mypy stay discoverable on PATH
  - Shrink `_AUTO_TIMEOUT_S` from 600 to 60
  - Update test docstring removing xfail rationale; add stub gate
    rationale + reference to Pillar A1 design
  - Strengthen assertions per Q4'=a+ resolution (see sec.4.3
    escenarios A3-1 / A3-2)

**Acceptance**: T3 runs in <60s, asserts full happy path, passes
reliably on Windows (mandatory) + POSIX (deferred to CI per v1.0.7
W5 carry-forward).

### 2.4 Item A4 — Gate regression tests (Pillar A)

**Track**: single subagent (T3, after T1).

**Archivos**:
- Extend: `tests/test_superpowers_dispatch.py` with new test class
  `TestE2EStubGate` (4 tests per Q1'=a, Q2'=a, Q4'=a+).

**Test class structure**:

```python
class TestE2EStubGate:
    """v1.0.8 Pillar A4: regression tests for SBTDD_E2E_STUB_DISPATCH gate.

    Each test monkeypatches ``subprocess_utils.run_with_timeout`` at
    the bottom of the call chain so the gate at the top of
    :func:`superpowers_dispatch.invoke_skill` is exercised end-to-end
    (real ``invoke_skill`` execution; only the subprocess call is
    faked). Monkeypatching ``invoke_skill`` itself would break the
    gate test semantic (gate would never run).
    """

    def test_gate_fires_for_stubbable_skill_with_env_set(self, monkeypatch):
        """v1.0.8 A4-1: env=1 + stubbable skill -> synthetic rc=0, no subprocess."""

    def test_gate_does_not_fire_when_env_unset(self, monkeypatch):
        """v1.0.8 A4-2: env unset -> real subprocess path attempted."""

    def test_gate_does_not_fire_for_skill_outside_stubbable_set(self, monkeypatch):
        """v1.0.8 A4-3: env=1 + non-stubbable skill -> real path."""

    def test_gate_stdout_contains_marker(self):
        """v1.0.8 A4-4: stub stdout contains literal '[sbtdd e2e stub]' marker."""
```

### 2.5 Item B1 — Fixture `.claude/settings.json` hardening (Pillar B)

**Track**: single subagent (T5, can run parallel to T1-T4 since
disjoint files).

**Archivos**:
- Create: `tests/fixtures/parallel-e2e/dot-claude-settings.json`
- Modify: `tests/test_auto_parallel_e2e.py::_stage_fixture` helper
  to copy fixture file to `<dest>/.claude/settings.json` (rename-on-
  copy because `.claude/` is gitignored — ship under a non-dotfile
  name in the fixture, materialize as dotfile in staged tree)
- Extend: `tests/test_auto_parallel_e2e.py::test_fixture_files_present`
  with assertion that the new fixture file exists

**Permissions content** (per Q3'=a):

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

**Goal**: doble defensa. Even if the stub gate is bypassed in a
future test variant, the fixture is "less broken" from the wrapper
claude perspective — `claude -p` should be able to proceed with
the granted permissions instead of hanging on permission prompts.

### 2.6 Item B2 — Upstream bug archive (Pillar B)

**Track**: single subagent (T6, can run parallel to T1-T5).

**Archivos**:
- Modify: `CLAUDE.md` (project root) — add top-level section
  "Known upstream limitations" with documented bug + repro context
  + workaround (cross-referenced to v1.0.8 Pillar A1)
- Create: memory file `memory/project_v108_claude_p_hang_upstream.md`
  in user's project memory dir (`C:\Users\jbolivarg\.claude\projects\
  D--jbolivarg-PythonProjects-SBTDD\memory\`)
- Update: `memory/MEMORY.md` index with pointer to the new memory
- Modify: `CHANGELOG.md` `[1.0.8]` "Deferred" section explicitly
  lists the upstream report submission as deferred to user
  decision post-v1.0.8 ship

**CLAUDE.md section content** (per spec-base sec.2.6 template):

```markdown
## Known upstream limitations

### claude -p /test-driven-development hangs in fixture-style cwd

**Manifestation**: invoking `claude -p /test-driven-development
--phase=red` as a subprocess with cwd pointing to a directory that
contains `sbtdd/spec-behavior.md` + `planning/claude-plan-tdd.md`
but lacks `.claude/settings.json` + `CLAUDE.md` causes the
subprocess to hang indefinitely (>180s empirically observed, zero
stdout/stderr output) before timeout-killed by the caller.

**Repro context**: empirically verified in v1.0.8 T3 diagnostic
2026-05-14 via 3 reproducer scripts (`.tmp_repro/repro_*.py`,
gitignored). Same command in cwd=empty temp dir returns rc=0 in
~30s; same command in cwd=SBTDD repo dir returns rc=0 in ~66s.
Bug is cwd-dependent on a specific file-layout combination.

**Workaround**: `tests/test_auto_parallel_e2e.py` uses
`SBTDD_E2E_STUB_DISPATCH=1` to bypass the dispatch entirely
(v1.0.8 Pillar A1 stub gate). In production, properly-initialized
SBTDD projects (via `/sbtdd init`) ship a complete
`.claude/settings.json` granting the permissions the implementer
skill needs — avoiding the hang.

**Upstream report**: STAGED for future submission to
`anthropics/claude-code` issue tracker (see memory
`project_v108_claude_p_hang_upstream.md` for repro instructions +
diagnostic evidence). v1.0.8 does NOT submit — deferred to user
decision post-v1.0.8 ship per spec sec.5 scope exclusions.
```

### 2.7 v1.0.8 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B ship).

**Activities**:

1. **Activity D `make verify` clean pass** (NON-NEGOTIABLE): tests
   1304 + 1 skipped + ~5-8 new = ~1309-1312, coverage >= 88%,
   runtime <= 200s soft / 220s hard. T3 unxfailed and PASSES.
2. **Activity E `/sbtdd pre-merge` end-to-end**: re-establish
   3-cycle Loop 2 no-override streak.
3. **Activity F production T1+T2 regression check**: 19 worker-mode
   bypass tests still pass.

---

## 3. Cross-module contracts

v1.0.8 introduces:

- **Item A1**: NEW `superpowers_dispatch._E2E_STUB_ENV` constant +
  NEW `superpowers_dispatch._E2E_STUBBABLE_SKILLS` frozenset + NEW
  gate at top of `invoke_skill`. Gate is the FIRST check (before
  the v1.0.7 A2 worker guard / v1.0.6 J-3 headless guard / v1.0.4
  membership gate).
- **Item A2**: PRESERVED `auto_cmd._dispatch_tracks_concurrent`
  worker env propagation contract (`worker_env =
  os.environ.copy()`). Pinned by new regression test.
- **Item A3**: T3 e2e test no longer xfail; subprocess env carries
  `SBTDD_E2E_STUB_DISPATCH=1`; timeout shrunk 600 → 60.
- **Item A4**: NEW test class `TestE2EStubGate` in
  `tests/test_superpowers_dispatch.py`.
- **Item B1**: NEW `tests/fixtures/parallel-e2e/dot-claude-settings.json`
  fixture + staging helper extension.
- **Item B2**: NEW section "Known upstream limitations" in CLAUDE.md
  + NEW memory file + CHANGELOG Deferred section update.

**Contratos preservados (no modificados)**:

- `_SUBPROCESS_INCOMPATIBLE_SKILLS` membership gate (v1.0.4) +
  override hatch (`allow_interactive_skill=True`).
- `_apply_inv0_model_check` cascade (v0.3.0).
- v1.0.6 J-3 `subprocess_utils.is_headless_context()` guard.
- v1.0.7 A2 `SBTDD_AUTO_PARALLEL_WORKER=1` worker-context guard.
- `SkillResult` dataclass schema (skill, returncode, stdout, stderr).
- `PreconditionError` / `ValidationError` / `QuotaExhaustedError`
  exception hierarchy.
- INV-37 composite-signature output validation tripwire.
- `state_file.SessionState` schema (no migration).
- v1.0.5 per-worker sidecar + scratch + flag forwarding patterns.
- v1.0.7 A1 POSIX PTY allocation + A2 Windows hybrid + sec.0.1
  chain bypass + `_persist_worker_verify_evidence` +
  `_verify_worker_sidecars_present` LOUD-FAIL contract.

---

## 4. Escenarios BDD

### 4.1 Item A1 — Env var stub gate semantics

**Escenario A1-1: Gate fires for stubbable skill with env var set AND pytest loaded**

> **Given** `os.environ["SBTDD_E2E_STUB_DISPATCH"] == "1"` AND
> `"pytest" in sys.modules` (test context) AND
> `skill == "test-driven-development"` (member of
> `_E2E_STUBBABLE_SKILLS`).
> **When** `superpowers_dispatch.invoke_skill(skill, args=[...],
> cwd=..., allow_interactive_skill=True)` invoked.
> **Then** Returns `SkillResult(skill="test-driven-development",
> returncode=0, stdout="[sbtdd e2e stub] /test-driven-development
> bypassed (SBTDD_E2E_STUB_DISPATCH=1)", stderr="")` IMMEDIATELY.
> NO call to `subprocess_utils.run_with_timeout`. NO call to
> `_build_skill_cmd`. NO call to `_apply_inv0_model_check`. NO
> downstream gate evaluation (v1.0.4 membership, v1.0.6 J-3
> headless, v1.0.7 A2 worker-context).

**Escenario A1-2: Gate does not fire when env var unset**

> **Given** `os.environ` does NOT contain `SBTDD_E2E_STUB_DISPATCH`
> (or contains a non-`"1"` value) AND `"pytest" in sys.modules`
> (test context — gate would otherwise fire if env was set) AND
> `skill == "test-driven-development"`.
> **When** `invoke_skill(skill, ...)` invoked.
> **Then** Gate short-circuits FALSE (env var check fails); flow
> proceeds to existing v1.0.7 gate logic (v1.0.7 A2 worker-context
> guard + v1.0.4 membership gate + v1.0.6 J-3 headless guard).
> Eventually reaches `subprocess_utils.run_with_timeout(["claude",
> "-p", ...])` per production semantics.

**Escenario A1-3: Gate does not fire for skill outside stubbable set**

> **Given** `os.environ["SBTDD_E2E_STUB_DISPATCH"] == "1"` AND
> `skill == "verification-before-completion"` (NOT in
> `_E2E_STUBBABLE_SKILLS`).
> **When** `invoke_skill(skill, ...)` invoked.
> **Then** Gate short-circuits FALSE (skill membership check
> fails); flow proceeds to existing v1.0.7 gate logic. Production
> `/verification-before-completion` path NOT affected even with
> env var set.

**Escenario A1-4: Stub stdout contains literal marker**

> **Given** Gate fires (A1-1 conditions).
> **When** Caller inspects `result.stdout`.
> **Then** `result.stdout.startswith("[sbtdd e2e stub] /")` is True.
> Substring `"bypassed (SBTDD_E2E_STUB_DISPATCH=1)"` is present.
> Marker is grep-friendly for post-mortem failure diagnosis.

**Escenario A1-5: Gate position is FIRST in invoke_skill body**

> **Given** Source code of `superpowers_dispatch.invoke_skill`
> read.
> **When** Linter / inspection identifies the gate block.
> **Then** The gate is positioned ABOVE the v1.0.7 A2 worker-
> context guard (which is currently the first guard). Gate
> precedence is documented in the function docstring including
> the precedence pair (when both `SBTDD_E2E_STUB_DISPATCH=1` AND
> `SBTDD_AUTO_PARALLEL_WORKER=1` are set, stub wins — correct for
> the test path).

**Escenario A1-6: Gate does NOT fire when pytest not loaded (production safeguard)**

> **Given** `os.environ["SBTDD_E2E_STUB_DISPATCH"] == "1"` is set
> (e.g., accidentally leaked into production env) AND `"pytest"
> NOT in sys.modules` (production process: orchestrator,
> worker subprocess, none import pytest at runtime) AND
> `skill == "test-driven-development"`.
> **When** `invoke_skill(skill, ...)` invoked.
> **Then** Gate short-circuits FALSE (pytest sys.modules check
> fails); flow proceeds to existing v1.0.7 gate logic. Production
> path is NOT bypassed — accidental env var leak has ZERO effect.
> Defense-in-depth runtime guard prevents test-only gate from
> firing in production processes per iter-2 carry-forward
> Cas-W11.

### 4.2 Item A2 — Worker env propagation regression

**Escenario A2-1: Parent env var propagates to worker subprocess via os.environ.copy()**

> **Given** `os.environ["SBTDD_E2E_STUB_DISPATCH"] == "1"` in the
> parent orchestrator process.
> **When** `_dispatch_tracks_concurrent` is invoked with a single
> track (synthetic minimal plan); the helper builds `worker_env =
> os.environ.copy()` and passes to `_spawn_worker(argv, env=
> worker_env, ...)`.
> **Then** The `env` dict received by `_spawn_worker` contains key
> `"SBTDD_E2E_STUB_DISPATCH"` with value `"1"`. (The test
> monkeypatches `_spawn_worker` to capture the env dict; no real
> subprocess spawn required.)

**Escenario A2-2: Env propagation is unfiltered (no allowlist)**

> **Given** Parent env contains multiple custom vars (e.g.
> `SBTDD_E2E_STUB_DISPATCH=1`, `MY_TEST_VAR=foo`).
> **When** `_dispatch_tracks_concurrent` builds `worker_env`.
> **Then** ALL custom vars present in parent env are present in
> `worker_env` (regression test pins this; future refactors that
> introduce filtering would surface).

### 4.3 Item A3 — T3 e2e test redesign end-to-end

**Escenario A3-1: T3 happy path with stub gate**

> **Given** Fixture staged at temp_dir per `_stage_fixture` (4-task
> plan + spec + plugin.local.md + `.claude/settings.json` per B1) +
> session-state seeded with `current_phase=red, task_id=1,
> plan_approved_at=non-null` + subprocess env contains
> `SBTDD_E2E_STUB_DISPATCH=1` AND inherited
> `os.environ.copy()` baseline.
> **When** Test runs
> `subprocess.run([python, run_sbtdd.py, auto, --parallel],
> cwd=tmp_dir, env=env, timeout=60)`.
> **Then** Subprocess returns `rc=0` within 60s. NO
> `subprocess.TimeoutExpired` raised.

**Escenario A3-2: T3 post-cycle state assertions**

> **Given** A3-1 completed successfully.
> **When** Test inspects post-cycle artifacts in tmp_dir.
> **Then** All of the following are True:
> - `.claude/session-state.json` parses; `current_phase == "done"`.
> - `planning/claude-plan-tdd.md` has NO `^[ \t]*- \[ \]` line
>   matches (regex multiline) — all task checkboxes flipped to
>   `[x]`.
> - `.claude/auto-run-workers/` exists; at least one file matches
>   glob `*-verify.json`. Each sidecar parses as JSON with
>   `"verify_chain"` key; the list has **AT LEAST 4 entries**
>   (extensible for future sec.0.1 additions per iter-2 carry-
>   forward Cas-W10); the 4 known sec.0.1 tools (pytest, ruff
>   check, ruff format, mypy) MUST be present (validated via
>   per-tool presence check, not by exact length); every entry
>   has `"rc": 0`.
> - `.claude/auto-run.json` parses; `auto_finished_at` is non-null;
>   `status == "success"`.

**Escenario A3-3: T3 sidecar verify_chain contains the 4 known sec.0.1 tools (substring detection)**

> **Given** A3-2 found at least one sidecar.
> **When** Test inspects the first sidecar's `verify_chain` list.
> **Then** Each entry's `"cmd"` field is a list whose string-joined
> representation (`" ".join(str(p) for p in cmd)`) contains the
> tool name. The 4 known sec.0.1 tools MUST appear in the chain
> via **substring-anywhere matching** (per iter-2 Checkpoint 2
> close-out Cas-W5+Mel-W3 resolution): `pytest`, `ruff` (which
> appears twice — `ruff check` + `ruff format --check`), `mypy`.
> Positional indexing like `cmd[2]` is NOT used — robust against
> future cmd-shape evolution (e.g., `python -X dev -m pytest`,
> env wrappers, different module paths). Additional entries
> beyond these 4 are acceptable (future sec.0.1 extensions per
> iter-2 carry-forward Cas-W10 resolution).

**Escenario A3-4: T3 xfail marker removed**

> **Given** Source of `tests/test_auto_parallel_e2e.py` read.
> **When** Linter / inspection scans the decorator list of
> `test_auto_parallel_e2e_chicken_and_egg_closed`.
> **Then** NO `@pytest.mark.xfail` decorator present. The two
> existing `@pytest.mark.skipif` decorators (POSIX skip + toolchain
> skip) preserved.

### 4.4 Item A4 — Gate regression tests

**Escenario A4-1: TestE2EStubGate class exists with 4 tests**

> **Given** Source of `tests/test_superpowers_dispatch.py` read.
> **When** Linter / inspection scans class definitions.
> **Then** Class `TestE2EStubGate` exists with 4 test methods:
> - `test_gate_fires_for_stubbable_skill_with_env_set`
> - `test_gate_does_not_fire_when_env_unset`
> - `test_gate_does_not_fire_for_skill_outside_stubbable_set`
> - `test_gate_stdout_contains_marker`

**Escenario A4-2: Each test monkeypatches subprocess_utils.run_with_timeout (not invoke_skill itself)**

> **Given** Tests in `TestE2EStubGate` use monkeypatch fixture.
> **When** Linter inspects the monkeypatch targets.
> **Then** Tests monkeypatch
> `superpowers_dispatch.subprocess_utils.run_with_timeout` (or
> equivalent lower-level subprocess call), NOT
> `superpowers_dispatch.invoke_skill` directly. This ensures the
> gate at the top of `invoke_skill` is exercised end-to-end during
> the test (real invoke_skill execution; only the subprocess call
> faked).

**Escenario A4-3: Gate test (positive case) raises if subprocess attempted**

> **Given** A4-1 + A4-2 setup; monkeypatch
> `run_with_timeout` to raise `AssertionError("subprocess attempted
> but gate should have fired")` if called.
> **When**
> `test_gate_fires_for_stubbable_skill_with_env_set` runs with
> `monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")` and
> `superpowers_dispatch.test_driven_development(args=["--phase=red"])`.
> **Then** Test passes — gate fires, returns synthetic SkillResult,
> `run_with_timeout` never called, no AssertionError raised.

### 4.5 Item B1 — Fixture hardening

**Escenario B1-1: Fixture ships dot-claude-settings.json with explicit allow list**

> **Given** `tests/fixtures/parallel-e2e/` directory inspected.
> **When** Files enumerated.
> **Then** File `dot-claude-settings.json` exists. Parses as JSON.
> Contains `permissions.allow` list with at least the entries
> documented in spec sec.2.5 (Write/Edit/Bash patterns for
> scratch+tests+src + pytest/ruff/mypy).

**Escenario B1-2: _stage_fixture helper materializes settings.json into staged tree**

> **Given** Test calls `_stage_fixture(dest)`.
> **When** Helper completes.
> **Then** File `<dest>/.claude/settings.json` exists with same
> JSON content as `tests/fixtures/parallel-e2e/dot-claude-settings.json`.
> The rename-on-copy preserves the file content byte-for-byte.

**Escenario B1-3: test_fixture_files_present asserts new fixture file**

> **Given** Source of `test_fixture_files_present` test inspected.
> **When** Linter scans the `expected` tuple of fixture filenames.
> **Then** `"dot-claude-settings.json"` is present in the tuple.

### 4.6 Item B2 — Upstream bug archive

**Escenario B2-1: CLAUDE.md has "Known upstream limitations" section**

> **Given** Project root `CLAUDE.md` read.
> **When** Linter scans markdown headers.
> **Then** Section `## Known upstream limitations` exists (level-2
> header). Subsection `### claude -p /test-driven-development hangs
> in fixture-style cwd` exists (level-3). Section body contains:
> the word `Manifestation`, the word `Repro context`, the word
> `Workaround`, the word `Upstream report`, and a reference to
> `SBTDD_E2E_STUB_DISPATCH`.

**Escenario B2-2: Memory archive file written by engineer (NOT test-asserted, local-only)**

> **Given** Plan T6 Step 5 instructs creating a memory file at the
> user's per-project Claude memory dir (OUTSIDE the repo; path is
> developer-machine-specific). Per iter-2 carry-forward Cas-W12
> resolution: this escenario is **NOT test-asserted** — the memory
> dir lives outside the repo, so any test asserting its presence
> would fail on CI and fresh clones. Only CLAUDE.md (B2-1) +
> CHANGELOG (B2-4) are test-asserted via
> `tests/test_doc_coherence_v108.py` per plan T6.
> **When** Engineer executes plan T6 Step 5 locally on the
> developer machine where the memory dir exists.
> **Then** A file `project_v108_claude_p_hang_upstream.md` is
> created in the developer's per-project Claude memory dir with
> frontmatter `metadata.type: reference`. Body contains: repro
> script names (`repro_t3.py`, `repro_worker.py`,
> `repro_skill_with_fixture_cwd.py`), the 3 cwd cases (empty,
> SBTDD repo, fixture temp dir), the wall-time observations (30s,
> 66s, >180s), the staged upstream report content. Body links
> via `[[project_v107_shipped]]` and
> `[[project_v108_t3_e2e_priority_locked]]`. **Verified by human
> review of the T6 closing commit narrative**, not by automated
> assertion.

**Escenario B2-3: MEMORY.md index updated with pointer**

> **Given** `MEMORY.md` index file read.
> **When** Linter scans pointer lines.
> **Then** A line exists matching format `- [...](project_v108_claude_p_hang_upstream.md)
> — ...` with a one-line hook summarizing the bug.

**Escenario B2-4: CHANGELOG [1.0.8] Deferred section lists upstream report submission**

> **Given** `CHANGELOG.md` `[1.0.8]` entry read.
> **When** Linter scans the Deferred subsection.
> **Then** A bullet exists explicitly naming the deferral
> ("Upstream report submission to `anthropics/claude-code`") with
> rationale ("v1.0.8 stages content in memory; user decides post-
> ship").

### 4.7 Cross-cutting v1.0.8 own-cycle dogfood

**Escenario D-1: make verify clean post-impl**

> **Given** Pillar A + Pillar B implemented and committed.
> **When** Operator runs `make verify` in repo root.
> **Then** All checks pass: `pytest` (1309-1312 tests + 1 skipped,
> 0 failed), `ruff check .` (0 warnings), `ruff format --check .`
> (clean), `mypy --strict .` (0 errors), coverage `>= 88%`,
> wall-time `<= 200s` soft / `<= 220s` hard.

**Escenario D-2: T3 e2e PASSES (not xfail)**

> **Given** Pillar A1+A2+A3+A4 implemented + Pillar B1 fixture
> staged.
> **When** Operator runs
> `pytest tests/test_auto_parallel_e2e.py::test_auto_parallel_e2e_chicken_and_egg_closed
> -v`.
> **Then** Test PASSES (not xfail / not xpass). Outcome reported
> as `PASSED`. Wall-time `< 60s`.

**Escenario E-1: Pre-merge Loop 1 + Loop 2 end-to-end**

> **Given** All tasks `[x]` in plan + state `done` + Pillar A + B
> shipped.
> **When** Operator runs `/sbtdd pre-merge` OR manual fallback
> via `python skills/magi/scripts/run_magi.py` per v1.0.2..v1.0.7
> precedent if `/sbtdd pre-merge` hangs on upstream bug.
> **Then** Loop 1 reaches clean-to-go within 10 iter cap. Loop 2
> reaches verdict `>= GO_WITH_CAVEATS` full no-degraded within 5
> iter cap. **NO INV-0 override applied**. 3-cycle Loop 2
> no-override streak preserved (v1.0.5 + v1.0.7 + v1.0.8).

**Escenario F-1: Production T1+T2 regression check**

> **Given** Pillar A1 stub gate landed.
> **When** Operator runs the 19 worker-mode bypass tests from
> v1.0.7 (`test_close_phase_cmd::test_run_verification_*` worker
> tests + `test_auto_cmd::test_dispatch_*` + `test_parallel_dispatcher::*`).
> **Then** All 19 tests PASS. No regression in production worker
> bypass semantics.

---

## 5. Subagent layout + execution timeline

### 5.1 Single-track sequential (recommended for v1.0.8 own-cycle)

**Rationale**: v1.0.8 bundle is small (6 items) and Pillar A items
have ordering dependencies (T1 must land before A3/A4 tests can be
written meaningfully). Sequential single-subagent path matches the
v1.0.7 Q1'=a chicken-and-egg workaround pattern (proven to ship
reliably in v1.0.6 + v1.0.7 cycles).

**Within-cycle ordering** (proposed for MAGI Checkpoint 2 review):

1. **T1 = A1**: Stub gate + module constants in
   `superpowers_dispatch.py`. ~30-60 min.
2. **T2 = A2**: Env propagation regression test in
   `test_auto_cmd.py`. No prod code change. ~20-30 min.
3. **T3 = A4**: 4 gate regression tests in
   `test_superpowers_dispatch.py`. Validates T1 semantics. ~45-60
   min.
4. **T4 = A3**: T3 e2e redesign (unxfail + env var + asserts) in
   `test_auto_parallel_e2e.py`. Depends on T1 (gate exists) +
   B1 (fixture has settings.json). ~30-45 min.
5. **T5 = B1**: Fixture `dot-claude-settings.json` + staging
   helper extension. Parallel to T1-T3 (disjoint files). ~20-30
   min.
6. **T6 = B2**: CLAUDE.md section + memory file + MEMORY.md index
   + CHANGELOG Deferred update. Parallel to T1-T5 (disjoint
   files). ~30-45 min.

**Total wall-time estimate**: ~3-5 hours sequential, including
close-phase chains (red/green/refactor + verify + commit per
task). Substantially under the v1.0.7 ~21-31h estimate due to
much smaller scope.

### 5.2 Parallel partition (alternative — depends on MAGI verdict)

If MAGI Checkpoint 2 prefers partition (validates Q5'=a default),
Tracks could split:

- **Track Alpha**: T1 → T3 → T4 (gate + gate tests + e2e
  redesign; ordering bound).
- **Track Beta**: T2 (env propagation regression; depends only on
  prod path being valid post-T1 land).
- **Track Gamma**: T5 → T6 (B1 fixture + B2 docs/archive;
  disjoint from everything else).

Partition matches v0.4.0 / v0.5.0 / v1.0.0 / v1.0.5 / v1.0.7
2-3 track parallel patterns. Use only if MAGI flags single-track
as bottleneck.

### 5.3 Mid-cycle methodology (orchestrator)

**Activities post-Pillar A + Pillar B ship**:

1. Activity D: `make verify` clean validation.
2. Activity E: `/sbtdd pre-merge` end-to-end OR manual fallback.
3. Activity F: production T1+T2 regression check.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (precedente cerrado v1.0.0..v1.0.7
  = 8-cycle no-override streak). NO INV-0 path. v1.0.8 goal:
  9-cycle Checkpoint 2 streak.
- Bundle scope focused (2 pillars, 6 items) — esperamos converger
  en 1-2 iters.
- **Iter-2 CRITICAL trigger**: if iter 2 still surfaces ANY
  CRITICAL finding, scope-trim immediately per G2 ladder
  (Q5'=a default):
  1. Defer Pillar B2 first (archival-only, low value-per-cost).
  2. Defer Pillar B1 second (defensive but not blocking).
  3. Pillar A A1+A2+A3+A4 hard-LOCKED.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- v1.0.8 own-cycle: `/sbtdd pre-merge` Loop 1 dispatch should
  work end-to-end (orchestrator inherits TTY; not blocked by
  upstream bug).

### 6.3 Loop 2 (`/magi:magi`) — strict no-INV-0 stance

- **Cap=5** per `auto_magi_max_iterations`.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding stance (Q3=a strict per v1.0.7 precedent)**: si
  Loop 2 iter 3 no converge clean, scope-trim per spec-base
  sec.6.1 ladder.
- **NO INV-0 override** without explicit user authorization.
  Escalate to user BEFORE applying INV-0 per memory
  `feedback_manual_synthesis_exceptional`.
- **Goal**: 3-cycle pre-merge Loop 2 no-override streak
  (v1.0.5+v1.0.7+v1.0.8 consecutive).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` hangs during v1.0.8 own-cycle (same upstream
bug class as v1.0.7 dogfood), operator MUST fall back to manual
`python skills/magi/scripts/run_magi.py` direct dispatch + manual
mini-cycle commits. Document en CHANGELOG `[1.0.8]` Process
notes. Precedente v1.0.0..v1.0.7.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.7 → 1.0.8.

### 7.2 CHANGELOG `[1.0.8]` sections

- **Added** — `SBTDD_E2E_STUB_DISPATCH` env var stub gate in
  `superpowers_dispatch.invoke_skill` (Pillar A1) with
  defense-in-depth runtime guard requiring `"pytest" in sys.modules`
  to prevent accidental production env var leak from activating
  the gate (iter-2 carry-forward Cas-W11+Bal-W7 combined fix);
  4 gate regression tests `TestE2EStubGate` (Pillar A4); env
  propagation regression test in `test_auto_cmd.py` (Pillar A2);
  fixture `tests/fixtures/parallel-e2e/dot-claude-settings.json`
  (Pillar B1); "Known upstream limitations" section in CLAUDE.md
  (Pillar B2); memory `project_v108_claude_p_hang_upstream.md`
  archiving the upstream bug (Pillar B2; **local-only**, not
  test-asserted).

  **Honest scope caveat** (iter-2 carry-forward Bal-W5): after
  v1.0.8 lands, T3 (`tests/test_auto_parallel_e2e.py`) is an
  INFRASTRUCTURE test (env propagation, worker spawn, sec.0.1
  chain bypass, sidecar persistence, parent-side hooks) — it does
  NOT exercise the real `/test-driven-development` dispatch
  semantics. Production unit coverage of the dispatch path is
  preserved via mocked tests in `test_auto_cmd.py` +
  `test_close_phase_cmd.py`; CI integration test for real
  dispatch is v1.0.9 LOCKED backlog.
- **Changed** — `tests/test_auto_parallel_e2e.py` redesigned: no
  longer xfail, subprocess env carries
  `SBTDD_E2E_STUB_DISPATCH=1`, timeout 600→60, strict happy-path
  assertions per Q4'=a+ (Pillar A3); `_stage_fixture` helper
  materializes `<dest>/.claude/settings.json` (Pillar B1).
- **Process notes** — v1.0.7 PRIORITY LOCKED T3 e2e empirical
  closure shipped. v1.0.8 diagnostic 2026-05-14 ruled out 4 of 5
  v1.0.7 hypotheses; root cause confirmed as upstream `claude -p`
  hang in fixture-style cwd. Q1'=a baseline stubbable skills set;
  Q2'=a minimal marker stdout; Q3'=a explicit permissions allow
  list; Q4'=a+ deterministic assertions; Q5'=a G2 ladder
  pre-staged. Production semantics preserved — Pillar A is
  TEST-ONLY; `SBTDD_E2E_STUB_DISPATCH` is namespaced + documented
  test-only; production workers continue to do real TDD work via
  real `claude -p` dispatch. G1 cap=3 HARD Checkpoint 2 no-override
  9-cycle streak preserved (v1.0.0..v1.0.8). Pre-merge Loop 2
  3-cycle no-override streak preserved (v1.0.5+v1.0.7+v1.0.8).
- **Deferred (rolled to v1.0.9)** — Upstream report submission
  to `anthropics/claude-code` (Pillar B2 stages content in
  memory; user decides post-v1.0.8 ship). **v1.0.9 LOCKED
  milestones** added per iter-2 carry-forward Bal-W6+Bal-W7+
  Cas-W13:
  1. Resolve `/sbtdd pre-merge` orchestrator-side hang
     (chicken-and-egg) so subcommand-based pre-merge works
     end-to-end without manual `run_magi.py` fallback. Closes
     the 9-cycle methodology debt of manual MAGI fallback
     (Bal-W6).
  2. CI integration test exercising real `/test-driven-development`
     dispatch (e.g., against a known-good fixture project with
     `.claude/settings.json` properly configured), as the
     integration safety net post-v1.0.8 stub gate (Cas-W13).
  3. Re-evaluate stub gate runtime-guard strength: if observed
     in field that pytest sys.modules guard has false-negatives
     (e.g., pytest-in-IDE workflows), consider AND-gating with a
     second env var like `SBTDD_E2E_STUB_ARMED=1` for explicit
     opt-in (Bal-W7).

  v1.0.7 deferred carry-forward (B2 worker subprocess
  auto-message hardening, C2 K-4 escape hatch test coverage, C4
  NF-B test count rebaseline, C8 F-A2 abort criterion diagnosis
  hint); Pillar D v1.0.5 polish carry-forward; Edge cases E1-E3.
- **Deferred (rolled to v1.1.0)** — Stub gate production-promotion
  decision review (whether to promote `SBTDD_E2E_STUB_DISPATCH`
  semantics into a production worker-mode bypass for
  `/test-driven-development`); all v1.0.4 carry-forward inherited
  items.

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.8 section adding short note about the test-only
  env var `SBTDD_E2E_STUB_DISPATCH` (with explicit "production
  callers MUST NOT set this" warning).
- **SKILL.md** (`skills/sbtdd/SKILL.md`): `### v1.0.8 notes`
  section documenting Pillar A1 stub gate + production semantics
  preservation + Pillar B1+B2 fixture hardening + upstream archive.
- **CLAUDE.md** (project root): v1.0.8 release notes pointer
  added; "Known upstream limitations" section added per Pillar B2.

---

## 8. Risk register v1.0.8

- **R1** (revised per iter-2 carry-forward Cas-W13). Stub gate
  could mask future regressions in real `/test-driven-development`
  dispatch path (since T3 no longer exercises it). **Honest
  mitigation status**: production T1+T2 unit tests in
  `test_auto_cmd.py` + `test_close_phase_cmd.py` preserve **UNIT
  coverage** of the dispatch path via mocked subprocess (fake
  `SkillResult`, monkeypatched `run_with_timeout`). After v1.0.8
  lands, **NO automated INTEGRATION test exercises a real
  `claude -p /test-driven-development` invocation**. The integration
  safety net is **manual smoke-test via `/sbtdd auto` on a real
  project** (any plan-approved SBTDD project would surface
  dispatch-path regressions on first auto run). T3 explicitly
  validates the dispatch INFRASTRUCTURE (env propagation, worker
  spawn, sec.0.1 chain bypass, sidecar persistence, parent-side
  LOUD-FAIL contract) — NOT the skill dispatch semantics. **CI
  integration test for real dispatch** is rolled to v1.0.9 LOCKED
  backlog.
- **R2**. Env var name `SBTDD_E2E_STUB_DISPATCH` could be set
  accidentally in production. Mitigation: namespace `SBTDD_E2E_*`
  signals test-only intent; docstring explicit warning; documented
  in CLAUDE.md + SKILL.md + README; gate fires only for the
  narrowly-scoped `_E2E_STUBBABLE_SKILLS` set (production
  `/verification-before-completion` path NOT affected even if env
  var is set).
- **R3**. Pillar A4 regression tests might monkeypatch
  `invoke_skill` itself instead of the dispatch path, breaking the
  gate test semantic. Mitigation: spec sec.4.4 A4-2 escenario
  pins the monkeypatch target as `subprocess_utils.run_with_timeout`
  (or equivalent lower-level call), NOT `invoke_skill`. Code
  review enforces this.
- **R4**. Fixture `.claude/settings.json` schema could become
  inconsistent with upstream Claude Code permissions format if the
  format evolves. Mitigation: fixture schema kept minimal +
  documented in spec; periodic re-validation in v1.1.0+ cycle.
- **R5**. Upstream bug archive (B2) could become stale if
  `anthropics/claude-code` fixes the hang upstream without us
  noticing. Mitigation: memory
  `project_v108_claude_p_hang_upstream.md` scheduled for v1.1.0
  re-check; if upstream is fixed, B2 archive can be marked
  resolved (but the test stub stays as cinturon de seguridad
  against regression).
- **R6**. Test-only env var could be confused with a production
  feature flag by operators reading the source. Mitigation:
  module-level constants `_E2E_STUB_ENV` and
  `_E2E_STUBBABLE_SKILLS` have underscore prefix (private by
  convention) + docstring explicit "test-only" warning + CLAUDE.md
  cross-reference. Naming includes `E2E` token signaling test
  framework intent.
- **R7**. `/sbtdd pre-merge` Loop 1 + Loop 2 hang during v1.0.8
  own-cycle (same upstream bug class). Mitigation: manual
  fallback to `run_magi.py` per v1.0.0..v1.0.7 precedent +
  CHANGELOG Process notes documents the fallback usage.

---

## 9. Acceptance criteria final v1.0.8

v1.0.8 ship-ready cuando:

### 9.1 Functional Items A1+A2+A3+A4 + B1+B2

- **F1**. F213-F215 (A1): env var stub gate at top of
  `invoke_skill` short-circuiting `claude -p` dispatch for
  stubbable skills. Verified via escenarios A1-1, A1-2, A1-3,
  A1-4, A1-5.
- **F2**. F216 (A2): worker env propagation regression test
  passes; no production code change. Verified via escenarios
  A2-1, A2-2.
- **F3**. F217-F219 (A3): T3 e2e test redesigned, no longer xfail,
  passes in <60s with strict happy-path assertions. Verified via
  escenarios A3-1, A3-2, A3-3, A3-4.
- **F4**. F220 (A4): 4 new gate regression tests pass. Verified
  via escenarios A4-1, A4-2, A4-3.
- **F5**. F221-F222 (B1): fixture ships `.claude/settings.json`
  with explicit allow list; staging helper materializes it.
  Verified via escenarios B1-1, B1-2, B1-3.
- **F6**. F223-F225 (B2): CLAUDE.md "Known upstream limitations"
  section added; new memory archived + MEMORY.md index updated;
  CHANGELOG deferred list updated. Verified via escenarios B2-1,
  B2-2, B2-3, B2-4.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s
  hard. Verified via escenario D-1.
- **NF-B**. Tests baseline 1304 + 1 skipped + 8 nuevos (T1: 1 smoke
  + T2: 1 regression + T3: 4 gate + T6: 2 doc-coherence) =
  **1312 + 1 skipped** final. T3 e2e PASSES (not xfail) **on
  Windows (mandatory)** per iter-2 carry-forward Mel-I1 + Cas-I8
  resolutions. POSIX validation deferred to CI per v1.0.7 W5
  carry-forward; CHANGELOG explicitly states the platform
  qualifier. Verified via escenario D-2.
- **NF-C**. Cross-platform (Windows + POSIX): gate semantics
  platform-agnostic (pytest sys.modules check + env var read are
  OS-independent); T3 runs on Windows (mandatory) + POSIX
  (deferred to CI per W5 carry-forward).
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos (per project convention for any `.py` file).
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados (Pillar A: `superpowers_dispatch.py`,
  `test_superpowers_dispatch.py`, `test_auto_parallel_e2e.py`,
  `test_auto_cmd.py`; Pillar B:
  `tests/fixtures/parallel-e2e/dot-claude-settings.json`,
  `CLAUDE.md`, `CHANGELOG.md`, memory dir).

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**.
  9-cycle Checkpoint 2 no-override streak preserved
  (v1.0.0..v1.0.8 consecutive).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (3-cycle Loop 2 streak goal: v1.0.5+v1.0.7+v1.0.8 consecutive).
  If unable to converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0 per memory
  `feedback_manual_synthesis_exceptional`.
- **P3**. CHANGELOG `[1.0.8]` entry written con secciones Added /
  Changed / Process notes / Deferred + Pillar A A1+A2+A3+A4 +
  Pillar B B1+B2 + dogfood findings + claim that v1.0.7 T3 e2e
  empirical gap closed.
- **P4**. Version bump 1.0.7 -> 1.0.8 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.8` + push (con autorizacion explicita user
  per memory `feedback_never_commit_without_explicit_request`).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion (INV-29).
- **P7**. v1.0.8 own-cycle dogfood: T3 unxfailed + PASSES in
  <60s + 19 production unit tests still pass. Verified via
  escenarios D-1, D-2, F-1.

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence (CHANGELOG, CLAUDE.md, README,
  SKILL.md mention v1.0.8 ship + items + T3 empirical closure
  consistently).
- **D3**. Documented:
  - `SBTDD_E2E_STUB_DISPATCH` env var in
    `superpowers_dispatch.py` docstring + README operational
    notes + SKILL.md v1.0.8 notes (as test-only, with explicit
    warning).
  - CLAUDE.md "Known upstream limitations" section per Pillar B2.
  - CHANGELOG `[1.0.8]` Deferred section lists upstream report
    submission as deferred.

---

## 9.5 Inherited invariants (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording, INV-37
composite-signature output validation tripwire, Item C v1.0.2
spec_lint gate, Q4 v1.0.2 coverage threshold protocol, v1.0.3
cross-check Windows long-filename fix, v1.0.4 Items A+B
membership-based subprocess gate, v1.0.4 Path 3 `--parallel`
architecture, v1.0.5 per-worker sidecar + scratch + flag
forwarding, v1.0.6 J-1+J-2+J-3 headless detection + J-3
invoke_skill guard, v1.0.7 A1 POSIX PTY + A2 Windows hybrid +
worker-mode sec.0.1 bypass + Q2'=b worker-context runtime guard —
all preserved unchanged. v1.0.8 ADDS the env var stub gate as the
FIRST check in `invoke_skill` (above all prior gates), preserving
production semantics by gating on the namespaced + skill-bounded
condition.

---

## 10. Referencias

- Spec base v1.0.8: `sbtdd/spec-behavior-base.md` (in working tree).
- Contrato autoritativo v0.1..v1.0.7 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.7 ship record: tag `v1.0.7` (commit `b97ed1a`); merge
  `b97ed1a` on `main`; branch `feature/v1.0.8-bundle` branched off
  main HEAD.
- v1.0.8 PRIORITY LOCKED memory:
  `project_v108_t3_e2e_priority_locked.md` (full v1.0.7 T3 xfail
  context + 5-hypothesis prioritization).
- v1.0.8 diagnostic reproducer scripts in `.tmp_repro/`
  (gitignored):
  - `repro_t3.py` — full subprocess via test path
  - `repro_worker.py` — single worker direct spawn
  - `repro_skill_with_fixture_cwd.py` — claude -p with cwd=fixture
- v1.0.9 deferred backlog: upstream report submission + v1.0.7
  carry-forward items.
- v1.1.0 deferred backlog: stub gate production-promotion
  decision review + all v1.0.4 carry-forward inherited items.
- Brainstorming refinement decisions (2026-05-14):
  - Q1' = a baseline stubbable skills set (test-driven-development +
    systematic-debugging only).
  - Q2' = a minimal marker stdout.
  - Q3' = a explicit permissions allow list (no wildcard).
  - Q4' = a+ deterministic assertions (omit exact commit count).
  - Q5' = a G2 ladder pre-staged (B2 → B1 → A hard-LOCKED).
- Branch: trabajo en `feature/v1.0.8-bundle` (branched off `main`
  HEAD `b97ed1a`).
