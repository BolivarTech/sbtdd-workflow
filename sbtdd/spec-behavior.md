# BDD overlay — sbtdd-workflow v1.0.6

> Generado 2026-05-09 a partir de `sbtdd/spec-behavior-base.md` v1.0.6.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5
> precedent (chicken-and-egg until Pillar A J-1+J-2+J-3 lands).
>
> v1.0.6 = **operational unblock + polish carry-forward cycle** per
> Bal v1.0.4 INFO #17 magnet-release recommendation. Two pillars:
> Pillar A PRIMARY (J-1+J-2+J-3 subprocess hang fix via real
> headless detection); Pillar B LOCKED (C.2 plan archaeology trim
> methodology + K-1..K-5 cherry-picked Loop 2 v1.0.5 iter-1 polish
> WARNINGs).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex. R5 compliant: frontmatter
> docstring above.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.6**: desbloquea `/sbtdd spec` + `/sbtdd pre-merge`
end-to-end (currently require manual fallback per spec sec.6.4) +
cierra Pillar C C.2 methodology deferred de v1.0.5 + 5 cherry-picked
Loop 2 v1.0.5 iter-1 polish WARNINGs.

Decisiones macro (baked in spec-base, confirmed by user 2026-05-09):

- **Q1 (scope) = B**: operational unblock + polish (Pillar A J-1+J-2+J-3
  subprocess hang fix + Pillar B C.2 + K-1..K-5 polish).
- **Q2 (subprocess fix) = a**: real headless detection
  (`SBTDD_HEADLESS` env var + `os.isatty(0)` check).
- **Q3 (INV stance) = a**: strict no-INV-0 — preserve 7-cycle
  Checkpoint 2 + 2-cycle pre-merge Loop 2 streaks.

Decisiones de brainstorming refinement 2026-05-09 (Q1'-Q5'):

- **Q1' (subagent partition) = c**: `auto --parallel` self-dispatch
  dogfood. Eats own dogfood; validates v1.0.5 production-grade
  `--parallel` end-to-end. Fallback: manual subagent dispatch if
  `auto --parallel` surfaces issues mid-cycle. `partition_by_tracks`
  computes disjoint tracks at runtime per file-conflict edges.
- **Q2' (env var truthy values) = a**: exact list `"1"`, `"true"`,
  `"yes"` case-insensitive. Predictable; matches v1.0.4 Items A+B
  convention.
- **Q3' (K-3 deprecation window) = a**: 1-cycle alias
  `_preflight_triplet_check = _preflight` ships v1.0.6;
  alias removed in v1.0.7. `_preflight_triplet_check` is private
  helper (underscore-prefixed); 1-cycle alias is courtesy not
  contract.
- **Q4' (K-5 CC regex strictness) = b**: liberal scope regex
  `[^()]+`. Goal is robust triplet detection in
  `_preflight_triplet_check`, NOT enforcing CC spec compliance.
  False-negatives (regex rejects valid `feat(...)` because scope
  has unexpected chars) cause HARD-BLOCK to fire incorrectly,
  surprising operators. False-positives (accept `feat(weird scope):`)
  just mean triplet check passes — no harm since commit content
  was gated by `make verify` + close-phase.
- **Q5' (G2 ladder) = a**: default ladder per spec-base baseline.
  Iter 3 trigger → defer K-2..K-5 polish first → defer C.2 second
  → only Pillar A J-1+J-2+J-3 hard-LOCKED. Symmetric to v1.0.5
  (Pillar C → Pillar B → Pillar A) which worked empirically.

**Hybrid methodology continued**: brainstorming + writing-plans
in-session via Skill tool (NO `claude -p` subprocess —
chicken-and-egg until Pillar A lands). Opcion A manual `run_magi.py`
for Checkpoint 2 + Loop 2 dispatch per v1.0.2..v1.0.5 precedent.

**Criterio de exito v1.0.6**:

- Tests baseline 1248 + 1 skipped preservados + ~10-15 nuevos =
  ~1258-1265 final.
- `make verify` runtime <= 200s soft / 220s hard (acknowledges
  v1.0.5 baseline 171s + ~10-20s incremental).
- Coverage threshold mantenido en 88% (v1.0.5 measured 89.88%;
  v1.0.6 must not regress below).
- **`/sbtdd spec` end-to-end empirical validation**: under
  `SBTDD_HEADLESS=1`, `/sbtdd spec` raises `PreconditionError`
  LOUD-FAST con recovery message naming `--resume-from-magi`.
  Under interactive TTY, `/sbtdd spec` proceeds normally
  (regression test).
- **`/sbtdd pre-merge` end-to-end empirical validation**: under
  `SBTDD_HEADLESS=1`, raises `PreconditionError` LOUD-FAST con
  recovery message naming manual `run_magi.py` fallback. Under
  TTY, Loop 1 + Loop 2 proceed per existing path.
- **`auto --parallel` self-dispatch dogfood**: v1.0.6 own-cycle
  impl phase dispatched via `auto --parallel`. Empirically
  validates v1.0.5 I-1+I-2+I-3 production-grade end-to-end.
- **G1 binding HARD respetado**: cap=3 HARD para Checkpoint 2
  sin INV-0. **7-cycle Checkpoint 2 no-override streak goal**.
- **Pre-merge Loop 2 streak preservation**: v1.0.5 re-established
  from 1 cycle. v1.0.6 = 2 cycles consecutive sin INV-0 goal.

---

## 2. Items LOCKED

### 2.1 Item J-1+J-2+J-3 unified — Real headless detection (Pillar A PRIMARY CRITICAL, T1)

**Track**: T1 (single logical unit; J-1+J-2+J-3 inseparable in helper +
enforcement).

**Archivos**:
- Modify: `skills/sbtdd/scripts/subprocess_utils.py` (new
  `is_headless_context() -> bool` helper consolidating env var
  check + isatty fallback)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (`invoke_skill` headless guard pre-spawn for skills in
  `_SUBPROCESS_INCOMPATIBLE_SKILLS`)
- Modify: `skills/sbtdd/scripts/magi_dispatch.py` (analogous
  guard for MAGI dispatch when target skill is interactive)
- Extend: `tests/test_subprocess_utils.py` + `tests/test_superpowers_dispatch.py`
  (new test classes for headless detection + enforcement)

**Empirical context (v1.0.5 ship reconfirmation)**:

v1.0.5 attempted `/sbtdd pre-merge`; ran Loop 1 iter-1 + iter-2
successfully but hung at iter-2 close on `/receiving-code-review`
subprocess (killed at 1200s timeout). v1.0.4 ship record claimed
hang was "situational, not systemic"; v1.0.5 reconfirmed it IS
systemic. Manual fallback per spec sec.6.4 used for v1.0.5 ship.

Root cause: interactive Claude skills require TTY for prompts; under
`claude -p` subprocess they wait silently for input that never
arrives.

**Implementation**:

```python
# subprocess_utils.py (new module-level helper)
def is_headless_context() -> bool:
    """v1.0.6 J-1+J-2: detect headless execution context.

    Returns True when:
    - SBTDD_HEADLESS env var truthy ("1", "true", "yes" case-insensitive
      per Q2'=a) — explicit headless declaration.
    - sys.stdin.isatty() returns False — implicit headless (subprocess
      of subprocess, piped invocation, CI runner without explicit env).
    - OSError or AttributeError on isatty() — defensive default.

    Returns False when stdin IS a TTY AND env var unset/falsy —
    interactive Claude Code session, allow normal subprocess dispatch.
    """
    explicit = os.environ.get("SBTDD_HEADLESS", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return True
    try:
        return not sys.stdin.isatty()
    except (OSError, AttributeError):
        return True
```

```python
# superpowers_dispatch.py invoke_skill (extended)
def invoke_skill(skill_name: str, *, allow_interactive_skill: bool = False, ...):
    """v1.0.4 Items A+B subprocess gate + v1.0.6 J-1+J-2+J-3 headless
    detection extension.

    Membership check (v1.0.4): if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
    and operator did NOT pass allow_interactive_skill=True, raise
    PreconditionError pre-spawn with recovery message.

    Headless check (v1.0.6 NEW): even when operator opts in via
    allow_interactive_skill=True, if context is headless (env var
    OR not TTY), refuse anyway — subprocess will hang silently;
    operator opt-in cannot make subprocess work without a TTY.
    """
    if skill_name in _SUBPROCESS_INCOMPATIBLE_SKILLS:
        if not allow_interactive_skill:
            raise PreconditionError(_build_recovery_message(skill_name))
        if subprocess_utils.is_headless_context():
            raise PreconditionError(
                f"Cannot dispatch interactive skill {skill_name!r} via "
                f"`claude -p` subprocess: context is headless "
                f"(SBTDD_HEADLESS truthy OR stdin not a TTY). The skill "
                f"requires an interactive terminal for its prompts. "
                f"Recovery: {_build_recovery_message(skill_name)}"
            )
    # ... existing subprocess dispatch ...
```

`magi_dispatch.py` analogous guard for any subprocess dispatch path
that targets an interactive skill (today: MAGI itself is non-interactive,
so likely no callsite to extend; future-proofs the API).

### 2.2 Item C.2 — Plan archaeology trim methodology (Pillar B carry-forward, T2)

**Track**: T2 (doc-only; isolated surfaces).

**Archivos**:
- Modify: `skills/sbtdd/SKILL.md` (add ship-time procedure section)
- Modify: `templates/CLAUDE.local.md.template` (template guidance
  + cross-link to SKILL.md)
- Create: `tests/test_plan_archaeology_trim_pattern.py` (smoke test)

**Implementation outline**:

Methodology pattern documented:
1. At ship-time, extract iter-by-iter triage context from
   `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]`
   "Process notes" section.
2. Trim plan-tdd.md to "active plan only" (current scope + tasks
   + acceptance criteria; no iter archaeology).
3. Optional: keep `planning/claude-plan-tdd-org.md` as immutable
   archaeology while `planning/claude-plan-tdd.md` = trimmed
   canonical.

Smoke test asserts SKILL.md AND `templates/CLAUDE.local.md.template`
both contain "plan archaeology trim" reference (case-insensitive
substring match).

### 2.3 Items K-1..K-5 — Polish (Pillar B)

**K-1 (T3) — `_section_has_flipped` per-checkbox parity**:

- Modify: `close_task_cmd.py:_section_has_flipped`
- Tests: extend `tests/test_close_task_cmd.py` race scenarios with
  mixed-checkbox section (some `[x]`, some `[ ]`) →
  `_apply_flips_from_diff` must not assume already-flipped just
  because section contains one `[x]`.

**K-2 (T4) — `getattr` late-import fallback removal**:

- Modify: `auto_cmd.py:_dispatch_tracks_concurrent` post-batch
  hook. Replace `getattr(close_task_cmd, "_merge_scratch_plans", noop)`
  with direct `from close_task_cmd import _merge_scratch_plans`
  (still late-import inside function body for cross-module dep
  correctness; drop the noop fallback to surface helper-removal
  regressions).
- Tests: existing tests cover; ensure no regression.

**K-3 (T5) — `_preflight_triplet_check` → `_preflight` rename + 1-cycle alias**:

- Modify: `close_task_cmd.py` (function definition + 1 callsite
  in `main`)
- Modify: `tests/test_close_task_cmd.py` (TestPreflightHardBlock
  class + 6+ test method assertions + `_install_happy_path_patches`
  monkeypatch target)
- Backwards-compat: keep `_preflight_triplet_check = _preflight`
  alias in `close_task_cmd.py` with comment marker
  `# DEPRECATED: alias removed in v1.0.7` (Q3'=a 1-cycle window)

**K-4 (T6) — `_FORWARDABLE_FLAGS` argparse-presence guard**:

- Modify: `auto_cmd.py:_build_worker_argv` or module-level. At
  module load, validate each `_FORWARDABLE_FLAGS` ns_attr exists
  in `_build_argparse_parser()` output dest set; raise
  `ValidationError` at module import if drift detected.
- Tests: meta-test asserting drift detection fires when fake flag
  added to `_FORWARDABLE_FLAGS` not in argparse.

**K-5 (T7) — Triplet check robust to CC scope syntax (liberal regex)**:

- Modify: `commits.py:validate_prefix` regex extended to match
  bare prefix OR `prefix(scope):` where scope = `[^()]+` (Q4'=b
  liberal).
- Modify: `close_task_cmd.py:_preflight` (post-K-3 rename) regex
  matchers analogous extension.
- Tests: extend `tests/test_commits.py` + `tests/test_close_task_cmd.py`
  with scoped subjects.

### 2.4 v1.0.6 own-cycle dogfood (orchestrator)

Activities post Pillar A + Pillar B ship:

1. **`/sbtdd spec` headless detection empirical validation** (~30 min):
   set `SBTDD_HEADLESS=1` env var + invoke `/sbtdd spec`; assert
   `PreconditionError` raised with recovery message naming
   `--resume-from-magi`. Then unset env var + invoke in interactive
   TTY context; assert proceeds normally to existing flow.

2. **`/sbtdd pre-merge` headless detection empirical validation**
   (~30 min): same pattern as #1 but for pre-merge with manual
   `run_magi.py` recovery message.

3. **`auto --parallel` self-dispatch dogfood** (Q1'=c chosen path):
   v1.0.6 impl phase dispatched via `auto --parallel`.
   `partition_by_tracks` computes disjoint tracks at runtime per
   file-conflict edges. Expected partition: Track A = {T1} (subprocess
   hang); Track B = {T3, T5, T7} (close_task_cmd.py + commits.py
   polish); Track C = {T4, T6} (auto_cmd.py polish); Track D = {T2}
   (docs). Validates v1.0.5 I-1+I-2+I-3 production-grade end-to-end.

4. **`/sbtdd spec --resume-from-magi` empirical validation**
   (deferred from v1.0.3 + v1.0.4): now feasible end-to-end since
   Pillar A J-1+J-2+J-3 empowers the recovery path semantically.

5. **Pre-merge gate clean WITHOUT INV-0** (~variable): `/sbtdd
   pre-merge` end-to-end on interactive TTY. Per Q3=a strict no-INV-0
   stance: if Loop 2 doesn't converge cleanly within cap=5,
   escalate to user BEFORE applying INV-0.

---

## 3. Cross-module contracts

v1.0.6 introduces:

- **Item J-1+J-2+J-3**: NEW `subprocess_utils.is_headless_context() -> bool`
  module-level helper. NEW guard at `superpowers_dispatch.invoke_skill`
  for skills in `_SUBPROCESS_INCOMPATIBLE_SKILLS`. NEW analogous
  guard at `magi_dispatch.py`. Existing `allow_interactive_skill=True`
  override hatch contract preserved per v1.0.4 Items A+B; but
  headless context refusal CANNOT be overridden (subprocess will
  hang, no safe path).
- **Item C.2**: doc-only changes to `skills/sbtdd/SKILL.md` +
  `templates/CLAUDE.local.md.template`. NEW smoke test
  `tests/test_plan_archaeology_trim_pattern.py`. NO Python module
  changes.
- **Item K-1**: `_section_has_flipped` semantic change in
  `close_task_cmd.py` — backwards compat preserved (still returns
  bool; just per-checkbox now). Any test asserting
  whole-section-True-on-single-`[x]` updated.
- **Item K-2**: `_dispatch_tracks_concurrent` post-batch hook
  refactored to direct `from close_task_cmd import _merge_scratch_plans`
  inside function body. Removes `getattr` noop fallback. Surfaces
  helper-removal regressions immediately.
- **Item K-3**: `_preflight_triplet_check` renamed to `_preflight`
  in `close_task_cmd.py`. 1-cycle alias `_preflight_triplet_check
  = _preflight` ships v1.0.6 with deprecation comment; alias
  removed in v1.0.7. Test class + monkeypatch targets updated.
- **Item K-4**: `_FORWARDABLE_FLAGS` argparse-presence guard fires
  at module import in `auto_cmd.py`. New `ValidationError` raise
  path if list drifts from argparse.
- **Item K-5**: `commits.validate_prefix` + `_preflight` regex
  extended with liberal CC scope syntax `[^()]+`. Backwards
  compat: bare prefixes still match.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` /
  `SBTDDError` hierarchy unchanged.
- `subprocess_utils.run_with_timeout` unchanged.
- `_compute_loop2_diff_with_meta`, `_loop2_with_cross_check`,
  `_run_magi_checkpoint2` (v1.0.0 + v1.0.4 architecture) unchanged.
- INV-37 composite-signature output validation tripwire unchanged.
- `state_file.SessionState` schema unchanged (no migration).
- `partition_by_tracks` (v1.0.4 Path 3) unchanged. v1.0.6 EXERCISES
  it at runtime via Q1'=c `auto --parallel` self-dispatch.
- v1.0.4 Items A+B membership-based subprocess gate
  (`_SUBPROCESS_INCOMPATIBLE_SKILLS` + `_build_recovery_message`)
  preserved + EXTENDED with v1.0.6 J-3 headless guard.
- v1.0.5 per-worker sidecar (I-1) + scratch (I-2) + flag forwarding
  (I-3) patterns unchanged.

---

## 4. Escenarios BDD

### 4.1 Item J-1+J-2 — Headless detection helper

**Escenario J-1: env var truthy returns headless**

> **Given** `SBTDD_HEADLESS=1` set in environment.
> **When** `subprocess_utils.is_headless_context()` invoked.
> **Then** Returns True immediately (env var takes precedence over
> isatty check). Same result for `SBTDD_HEADLESS=true`,
> `SBTDD_HEADLESS=yes`, and case variations (`TRUE`, `Yes`, etc.).

**Escenario J-2: env var falsy + TTY stdin returns interactive**

> **Given** `SBTDD_HEADLESS` unset OR set to empty/falsy value.
> AND `sys.stdin.isatty()` returns True.
> **When** `is_headless_context()` invoked.
> **Then** Returns False (interactive context detected).

**Escenario J-3: env var falsy + non-TTY stdin returns headless**

> **Given** `SBTDD_HEADLESS` unset OR falsy.
> AND `sys.stdin.isatty()` returns False (subprocess of subprocess,
> piped invocation, CI runner).
> **When** `is_headless_context()` invoked.
> **Then** Returns True (implicit headless detected via isatty).

**Escenario J-4: isatty exception returns headless defensively**

> **Given** `sys.stdin.isatty()` raises OSError or AttributeError
> (closed stdin, unusual environment).
> **When** `is_headless_context()` invoked.
> **Then** Returns True (defensive default — assume headless when
> uncertain).

**Escenario J-5: env var values not in truthy set are falsy**

> **Given** `SBTDD_HEADLESS=on` OR `SBTDD_HEADLESS=enabled` OR any
> value not in `{"1", "true", "yes"}` (case-insensitive).
> AND TTY stdin.
> **When** `is_headless_context()` invoked.
> **Then** Returns False (env var falsy → falls through to TTY check
> → TTY → interactive). Documented expectation per Q2'=a exact list.

### 4.2 Item J-3 — Enforcement at incompatible skill callsites

**Escenario J-6: invoke_skill refuses headless dispatch even with override**

> **Given** Skill `receiving-code-review` in `_SUBPROCESS_INCOMPATIBLE_SKILLS`.
> AND Operator passes `allow_interactive_skill=True`.
> AND `is_headless_context()` returns True.
> **When** `invoke_skill("receiving-code-review", allow_interactive_skill=True)`
> invoked.
> **Then** `PreconditionError` raised LOUD-FAST with message
> mentioning "Cannot dispatch interactive skill" + "context is headless"
> + recovery message naming manual `run_magi.py` fallback.
> Subprocess never spawned (operator opt-in cannot override headless
> refusal).

**Escenario J-7: invoke_skill allows interactive context with override**

> **Given** Skill `receiving-code-review` in `_SUBPROCESS_INCOMPATIBLE_SKILLS`.
> AND Operator passes `allow_interactive_skill=True`.
> AND `is_headless_context()` returns False (interactive TTY).
> **When** `invoke_skill("receiving-code-review", allow_interactive_skill=True)`
> invoked.
> **Then** Subprocess dispatched normally (existing v1.0.5 path
> preserved). v1.0.4 Items A+B override hatch honored.

**Escenario J-8: invoke_skill blocks default (no override) regardless of context**

> **Given** Skill `brainstorming` in `_SUBPROCESS_INCOMPATIBLE_SKILLS`.
> AND Operator does NOT pass `allow_interactive_skill=True`.
> **When** `invoke_skill("brainstorming")` invoked.
> **Then** `PreconditionError` raised pre-spawn with v1.0.4 recovery
> message naming `--resume-from-magi`. Headless check NOT consulted
> (membership check fires first per existing contract).

**Escenario J-9: `/sbtdd spec` end-to-end under SBTDD_HEADLESS=1**

> **Given** `SBTDD_HEADLESS=1` env var set.
> **When** Operator invokes `python skills/sbtdd/scripts/run_sbtdd.py spec`.
> **Then** `spec_cmd._run_spec_flow` attempts `/brainstorming`
> dispatch → `invoke_skill("brainstorming")` → `PreconditionError`
> raised LOUD-FAST with recovery message naming `--resume-from-magi`.
> Exit code 2 (PreconditionError per spec sec.11.1). No 600s timeout
> hang.

**Escenario J-10: `/sbtdd pre-merge` end-to-end under SBTDD_HEADLESS=1**

> **Given** `SBTDD_HEADLESS=1` env var set + state file at
> `current_phase: "done"`.
> **When** Operator invokes `python skills/sbtdd/scripts/run_sbtdd.py pre-merge`.
> **Then** `pre_merge_cmd._loop1_iter` attempts
> `/requesting-code-review` triage → `invoke_skill("receiving-code-review",
> allow_interactive_skill=True)` → `PreconditionError` raised
> LOUD-FAST with recovery message naming manual `run_magi.py`
> fallback. Exit code 2. No 1200s timeout hang.

### 4.3 Item C.2 — Plan archaeology trim methodology

**Escenario C2-1: SKILL.md documents ship-time trim procedure**

> **Given** Updated `skills/sbtdd/SKILL.md`.
> **When** Grep for "plan archaeology trim" pattern.
> **Then** SKILL.md contains explicit ship-time procedure section
> referencing CHANGELOG Process notes destination + plan-tdd.md
> active-plan-only trim.

**Escenario C2-2: CLAUDE.local.md.template references procedure**

> **Given** Updated `templates/CLAUDE.local.md.template`.
> **When** Grep for archaeology trim pattern.
> **Then** Template contains procedure reference + cross-link to
> SKILL.md authoritative version.

**Escenario C2-3: smoke test asserts cross-artifact reference**

> **Given** `tests/test_plan_archaeology_trim_pattern.py` (new).
> **When** Test runs.
> **Then** Asserts SKILL.md AND `templates/CLAUDE.local.md.template`
> both contain "plan archaeology trim" reference (case-insensitive
> substring match). Drift between docs caught.

### 4.4 Item K-1 — `_section_has_flipped` per-checkbox parity

**Escenario K-1a: mixed-checkbox section returns False**

> **Given** Plan section with both `- [x]` and `- [ ]` checkboxes
> (e.g., partial worker progress).
> **When** `_section_has_flipped(plan_text, task_id)` invoked.
> **Then** Returns False (NOT yet fully flipped). Pre-fix returned
> True on first `[x]`; post-fix requires ALL checkboxes flipped to
> return True.

**Escenario K-1b: fully-flipped section returns True**

> **Given** Plan section with all `- [x]` checkboxes (completed).
> **When** `_section_has_flipped(plan_text, task_id)` invoked.
> **Then** Returns True.

**Escenario K-1c: empty section returns False**

> **Given** Plan section with no checkboxes (descriptive only).
> **When** `_section_has_flipped(plan_text, task_id)` invoked.
> **Then** Returns False (vacuously NOT flipped; no checkboxes to flip).

### 4.5 Item K-2 — `getattr` fallback removal

**Escenario K-2: `_merge_scratch_plans` import direct + raises ImportError if missing**

> **Given** `auto_cmd._dispatch_tracks_concurrent` post-batch hook
> reaches scratch-merge step.
> AND `close_task_cmd._merge_scratch_plans` exists (v1.0.5+).
> **When** Hook executes.
> **Then** Direct `from close_task_cmd import _merge_scratch_plans`
> succeeds; helper invoked normally. Pre-fix `getattr` noop fallback
> removed; if helper somehow removed in future, ImportError raised
> immediately (no silent no-op).

### 4.6 Item K-3 — `_preflight_triplet_check` → `_preflight` rename

**Escenario K-3a: canonical `_preflight` callable**

> **Given** v1.0.6 `close_task_cmd.py`.
> **When** Test invokes `close_task_cmd._preflight(state, project_root)`.
> **Then** Function callable with same semantics as v1.0.5
> `_preflight_triplet_check`. v1.0.5 behavior preserved.

**Escenario K-3b: legacy `_preflight_triplet_check` alias still callable**

> **Given** v1.0.6 `close_task_cmd.py` with 1-cycle alias.
> **When** Test invokes `close_task_cmd._preflight_triplet_check(state,
> project_root)`.
> **Then** Alias resolves to `_preflight`; same behavior. Deprecation
> comment marker `# DEPRECATED: removed in v1.0.7` present in source.

### 4.7 Item K-4 — `_FORWARDABLE_FLAGS` argparse-presence guard

**Escenario K-4a: drift detected at module import**

> **Given** Synthetic `_FORWARDABLE_FLAGS` with key not in
> `_build_argparse_parser()` output dest set.
> **When** `auto_cmd.py` imported (or argparse-presence guard
> invoked at runtime).
> **Then** `ValidationError` raised with message naming the drifted
> flag(s). Module import fails LOUD-FAST.

**Escenario K-4b: clean `_FORWARDABLE_FLAGS` passes**

> **Given** Real `_FORWARDABLE_FLAGS` matching argparse dest set.
> **When** `auto_cmd.py` imported.
> **Then** No exception. Normal import.

### 4.8 Item K-5 — Conventional Commits scope syntax (liberal)

**Escenario K-5a: bare prefix matches (backwards compat)**

> **Given** Commit subject `test: add failing test for X`.
> **When** `commits.validate_prefix(subject)` invoked.
> **Then** Returns True (matches bare `test:` prefix). v1.0.5
> behavior preserved.

**Escenario K-5b: scoped prefix matches (NEW)**

> **Given** Commit subject `test(close-task): add failing test for X`.
> **When** `commits.validate_prefix(subject)` invoked.
> **Then** Returns True (matches `test(close-task):` scoped prefix).
> Scope = `[^()]+` liberal regex.

**Escenario K-5c: liberal scope content accepted**

> **Given** Commit subjects:
> - `feat(Close-Task): ...` (uppercase scope)
> - `fix(close_task): ...` (underscore scope)
> - `refactor(some scope): ...` (space in scope)
> - `test(123): ...` (numeric scope)
> **When** `commits.validate_prefix(subject)` invoked for each.
> **Then** All return True (liberal regex `[^()]+` accepts any
> non-paren content per Q4'=b).

**Escenario K-5d: triplet check accepts scoped subjects**

> **Given** Commit chain since last `chore: mark task` commit:
> - `test(close-task): ...`
> - `feat(close-task): ...`
> - `refactor(close-task): ...`
> **When** `_preflight(state, project_root)` invoked.
> **Then** No raise (canonical TDD triplet detected via liberal
> regex). Pre-fix would have raised PreconditionError (bare-prefix
> regex didn't match scoped subjects).

### 4.9 v1.0.6 own-cycle `auto --parallel` dogfood

**Escenario A-1: partition computed at runtime**

> **Given** v1.0.6 plan with 7 tasks (T1 J-class, T2 C.2, T3 K-1,
> T4 K-2, T5 K-3, T6 K-4, T7 K-5) + file-surface declarations per
> task.
> **When** Operator invokes `auto --parallel`.
> **Then** `partition_by_tracks` computes disjoint tracks based on
> file-conflict edges. Expected partition (subject to runtime
> verification): Track A = {T1}, Track B = {T3, T5, T7}, Track C =
> {T4, T6}, Track D = {T2}.

**Escenario A-2: `auto --parallel` self-dispatch validates v1.0.5 end-to-end**

> **Given** v1.0.6 plan + v1.0.5 production-grade `--parallel`
> code (I-1+I-2+I-3 closed).
> **When** Operator invokes `auto --parallel`.
> **Then** Subprocess workers dispatch per partition; each worker
> processes its track sequentially; parent post-batch merges
> sidecar audits + scratch plan flips per v1.0.5 contract. After
> dispatch, ALL of:
> - Parent `.claude/auto-run.json` contains start_time + 7 task
>   records (I-1)
> - Plan-tdd.md has 7 `[x]` checkbox flips, no lost updates (I-2)
> - Each worker subprocess received forwarded operator flags (I-3)
> - All TDD triplet commits per task in git log
> - State file `current_phase: "done"` post-completion
>
> Empirically validates v1.0.5 production-grade `--parallel`
> end-to-end (deferred dogfood from v1.0.5 sec.2.7).

---

## 5. Subagent layout + execution timeline

### 5.1 `auto --parallel` self-dispatch (Q1'=c primary path)

**Owner**: orchestrator dispatches `python skills/sbtdd/scripts/run_sbtdd.py
auto --parallel`; runtime computes partition.

**Wall-time estimado**: ~1.5 dias (7 tasks across 4 disjoint tracks
running concurrently per partition).

**Expected runtime partition** (subject to `partition_by_tracks`
runtime computation):

| Track | Tasks | Surfaces |
|-------|-------|----------|
| A | T1 (J-1+J-2+J-3) | `subprocess_utils.py` + `superpowers_dispatch.py` + `magi_dispatch.py` + tests |
| B | T3 (K-1) → T5 (K-3) → T7 (K-5) | `close_task_cmd.py` + `commits.py` + tests (sequential within track due to shared close_task_cmd.py) |
| C | T4 (K-2) → T6 (K-4) | `auto_cmd.py` + tests (sequential within track due to shared auto_cmd.py) |
| D | T2 (C.2) | `SKILL.md` + `templates/CLAUDE.local.md.template` + `tests/test_plan_archaeology_trim_pattern.py` (NEW) |

**Cero file overlap** between Track A + Track B + Track C + Track D
(verified via spec sec.5.1 expected partition; runtime
`partition_by_tracks` enforces).

### 5.2 Fallback: manual subagent dispatch (Q1'=c fallback)

If `auto --parallel` self-dispatch surfaces issues mid-cycle (e.g.,
v1.0.5 I-1+I-2+I-3 production-grade fix has unexpected gaps):
fall back to **manual 2-track subagent dispatch via Agent tool
fan-out** (Q1' option b):
- Track Alpha = T1 (Pillar A)
- Track Beta = T2 + T3 + T4 + T5 + T6 + T7 (Pillar B sequential)

This fallback is the same pattern v1.0.4+v1.0.5 used successfully.
Documented in CHANGELOG `[1.0.6]` Process notes if invoked.

### 5.3 Mid-cycle methodology (orchestrator)

**Owner**: orchestrator (single Claude Code session).
**Wall-time estimado**: ~0.5-1 dia.

Triggered AFTER all 7 tasks close + commits land:

1. **`/sbtdd spec` headless detection empirical validation** (~30 min)
2. **`/sbtdd pre-merge` headless detection empirical validation** (~30 min)
3. **`/sbtdd spec --resume-from-magi` empirical validation** (~30 min)
4. **Pre-merge gate clean WITHOUT INV-0** (~variable). Per Q3=a strict
   stance: if Loop 2 doesn't converge cleanly within cap=5,
   escalate to user BEFORE applying INV-0.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (CHANGELOG `[1.0.0]`, precedente
  cerrado v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5 = 6-streak no-override
  Checkpoint 2). NO INV-0 path. v1.0.6 goal: 7-cycle Checkpoint 2
  streak.
- Bundle scope focused (8 items across 2 pillars) — esperamos
  converger en 1-2 iters.
- **Iter 2 CRITICAL trigger** (v1.0.3 spec sec.6.1, v1.0.4+v1.0.5
  empirical fires): if Loop 2 iter 2 still surfaces ANY CRITICAL
  finding (post-iter-1-triage-fix), scope-trim immediately.
  Pre-staged G2 ladder (Q5'=a default):
  1. Defer K-2..K-5 polish first (4 items, low value-per-item).
  2. Defer C.2 second (doc-only).
  3. Pillar A J-1+J-2+J-3 hard-LOCKED.
- Si llega a iter 3 sin convergencia, default scope-trim ladder
  applies per above.

**Methodology decision**: Checkpoint 2 dispatch usa **Opcion A
manual `run_magi.py`** per hybrid methodology + v1.0.2..v1.0.5
precedent.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- Bundle scope minimal (8 items, mostly small fixes) — esperamos
  converger en 1-2 iters.

### 6.3 Loop 2 (`/magi:magi`) — strict no-INV-0 stance

- **Cap=5** per `auto_magi_max_iterations`.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding stance (Q3=a strict)**: si Loop 2 iter 3 no converge
  clean, scope-trim per spec-base sec.6.1 ladder (K-2..K-5 first
  → C.2 second → Pillar A hard-LOCKED).
- **NO INV-0 override** without explicit user authorization. If
  Loop 2 doesn't converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0 (per memory
  `feedback_manual_synthesis_exceptional`).
- **Goal**: preserve pre-merge Loop 2 no-override streak from
  1 cycle (v1.0.5) to 2 cycles consecutive (v1.0.6).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.6 own-cycle
(unlikely post Pillar A J-1+J-2+J-3 land, but possible if other
regressions surface), el operator MUST fall back a manual
`python skills/magi/scripts/run_magi.py` direct dispatch + manual
mini-cycle commits. Document en CHANGELOG `[1.0.6]` Process notes.
Precedentes v1.0.0..v1.0.5.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.5 → 1.0.6.

### 7.2 CHANGELOG `[1.0.6]` sections

- **Added** —
  `subprocess_utils.is_headless_context()` real headless detection
  helper consolidating `SBTDD_HEADLESS` env var + `os.isatty(0)`
  fallback (J-1+J-2);
  Headless context guard at `superpowers_dispatch.invoke_skill` +
  `magi_dispatch.py` for skills in `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  (J-3);
  Plan archaeology trim methodology in SKILL.md +
  `templates/CLAUDE.local.md.template` (C.2 doc + smoke test);
  `_FORWARDABLE_FLAGS` argparse-presence guard at module import
  (K-4);
  Conventional Commits scope syntax support (liberal `[^()]+`
  regex) in `commits.validate_prefix` + `_preflight` (K-5).
- **Changed** —
  `_section_has_flipped` per-checkbox parity (K-1);
  `_dispatch_tracks_concurrent` post-batch hook uses direct
  `from close_task_cmd import _merge_scratch_plans` (no `getattr`
  noop fallback) (K-2);
  `_preflight_triplet_check` renamed to `_preflight` (K-3);
  `_preflight_triplet_check = _preflight` 1-cycle alias preserves
  backwards compat; alias removed in v1.0.7.
- **Process notes** — Pillar A J-1+J-2+J-3 unblocks `/sbtdd spec`
  + `/sbtdd pre-merge` end-to-end (chicken-and-egg closed); Pillar
  B C.2 + K-1..K-5 polish carry-forward from v1.0.5 deferred items;
  Q1'=c `auto --parallel` self-dispatch dogfood empirically
  validates v1.0.5 production-grade `--parallel` end-to-end;
  G1 cap=3 HARD streak now 7 cycles consecutive; pre-merge Loop 2
  streak preservation (v1.0.5+v1.0.6 = 2 cycles consecutive sin
  INV-0).
- **Deferred (rolled to v1.0.7+)** — 4 v1.0.5 polish WARNINGs not
  cherry-picked (mark_and_advance API split, I2-4 race test runtime
  optimization, --skip-preflight UX discoverability,
  model_override list flattening test); Worker-mode hardcoded plan
  path / `_apply_flips_from_diff` ValueError edge case; Coverage
  drift trend monitoring.
- **Deferred (rolled to v1.1.0)** — All v1.0.4 carry-forward
  inherited items (per CHANGELOG `[1.0.4]` Deferred sections).

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.6 docs section sobre `SBTDD_HEADLESS` env var +
  fail-fast headless detection + `--skip-preflight` operator UX +
  CC scope syntax support.
- **SKILL.md**: `### v1.0.6 notes` section documentando 8 items.
- **CLAUDE.md** (project root, gitignored): v1.0.6 release notes
  pointer.

---

## 8. Risk register v1.0.6

- **R1**. J-1+J-2 isatty detection may false-positive in some CI
  environments where stdin is a pseudo-TTY but interactive skills
  still hang. Mitigation: explicit `SBTDD_HEADLESS=1` env var
  takes precedence; operators in problematic CI set the var
  explicitly. Documented in README.
- **R2**. K-3 `_preflight_triplet_check` to `_preflight` rename may
  break operator scripts that monkeypatch the old name. Mitigation:
  1-cycle alias preserves backwards compat; deprecation marker
  comment clearly signals migration timeline (removal in v1.0.7).
- **R3**. K-5 liberal scope regex `[^()]+` may introduce false
  positives for non-CC subjects that happen to contain `(text):`
  pattern. Mitigation: regex anchored to start-of-string; first
  group is the prefix verb; risk acceptable per Q4'=b operator UX
  goal (false-positives just mean triplet check passes — no harm
  since commit content was gated by make verify + close-phase).
- **R4**. v1.0.6 own-cycle dogfood under SBTDD_HEADLESS=1 may
  surface J-1+J-2+J-3 fix gaps not caught by tests. Mitigation:
  dogfood is non-blocking for ship (acceptance via tests
  primarily; dogfood empirical is bonus); if dogfood fails,
  document + roll forward to v1.0.7 patch.
- **R5**. Pre-merge Loop 2 streak preservation goal (Q3=a strict
  no-INV-0) may not be achievable if cycle surfaces fundamental
  architectural questions. Mitigation: G2 scope-trim ladder
  (defer K-2..K-5 first → then C.2 → Pillar A hard-LOCKED);
  INV-0 remains available but escalated to user before
  application.
- **R6**. Q1'=c `auto --parallel` self-dispatch dogfood may
  surface v1.0.5 I-1+I-2+I-3 production-grade fix gaps mid-cycle.
  Mitigation: fallback to manual 2-track subagent dispatch (Q1'
  option b); document in CHANGELOG `[1.0.6]` Process notes if
  invoked.

---

## 9. Acceptance criteria final v1.0.6

v1.0.6 ship-ready cuando:

### 9.1 Functional Items J-1+J-2+J-3 + C.2 + K-1..K-5

- **F1**. F181-F184 (J-1+J-2): `is_headless_context()` helper +
  truthy/falsy/TTY semantics + defensive isatty exception handling.
- **F2**. F185-F187 (J-3): enforcement at `invoke_skill` callsites
  + override hatch contract preserved + headless refusal cannot
  be overridden.
- **F3**. F188-F190 (C.2): plan archaeology trim methodology
  documented in SKILL.md + template + smoke test.
- **F4**. F191 (K-1): `_section_has_flipped` per-checkbox parity.
- **F5**. F192 (K-2): `getattr` late-import fallback removed.
- **F6**. F193 (K-3): `_preflight_triplet_check` renamed to
  `_preflight` + 1-cycle deprecation alias.
- **F7**. F194 (K-4): `_FORWARDABLE_FLAGS` argparse-presence guard.
- **F8**. F195 (K-5): liberal CC scope syntax support.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format
  + mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s
  hard.
- **NF-B**. Tests baseline 1248 + 1 skipped + ~10-15 nuevos =
  ~1258-1265 final.
- **NF-C**. Cross-platform (Windows + POSIX) — J-1+J-2 headless
  detection validated on both via env var + isatty mocking.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados.

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**.
  7-cycle Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (2-cycle streak goal post v1.0.5 re-establishment).
  If unable to converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0.
- **P3**. CHANGELOG `[1.0.6]` entry written con secciones Added /
  Changed / Process notes + Pillar A J-1+J-2+J-3 + Pillar B C.2 +
  K-1..K-5 + dogfood findings.
- **P4**. Version bump 1.0.5 -> 1.0.6 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.6` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. v1.0.6 own-cycle dogfood: `/sbtdd spec` + `/sbtdd
  pre-merge` validated under both headless (`SBTDD_HEADLESS=1`)
  AND interactive (TTY) contexts.
- **P8**. `auto --parallel` self-dispatch dogfood empirically
  validates v1.0.5 I-1+I-2+I-3 production-grade end-to-end.

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.6 ship + 8 items +
  dogfood observations).
- **D3**. Documented:
  - `SBTDD_HEADLESS` env var in README common-flags + SKILL.md
    v1.0.6 notes + `subprocess_utils.is_headless_context()` docstring.
  - C.2 plan archaeology trim procedure in SKILL.md +
    `templates/CLAUDE.local.md.template`.
  - K-3 `_preflight_triplet_check` to `_preflight` rename in
    CHANGELOG + 1-cycle deprecation alias mention.
  - K-5 CC scope syntax support in CHANGELOG.

---

## 9.5 Inherited invariants from v0.4.x..v1.0.5 (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording (canonical
single-line text `[sbtdd magi] synthesizer failed; manual synthesis
recovery applied`) is preserved verbatim across spec / CHANGELOG /
impl per the cross-artifact alignment contract
(`tests/test_changelog.py`). v1.0.6 ships no behavioral change to
this path.

The INV-37 composite-signature output validation tripwire (v1.0.1
Item A0) is preserved verbatim — `_run_spec_flow` mtime + size +
sha256 check applies during v1.0.6 own-cycle.

The Item C v1.0.2 `spec_lint` gate (R1-R5 rules with R3 warning per
Q3) is preserved unchanged.

The Q4 v1.0.2 coverage threshold = `floor(baseline) - 2%` protocol
is preserved at 88% (v1.0.5 measured 89.88%; v1.0.6 must not regress
below).

The v1.0.3 cross-check Windows long-filename fix (Item B
`@<filepath>` reference + project-relative temp dir) is preserved
unchanged.

The v1.0.4 Items A+B membership-based subprocess gate
(`_SUBPROCESS_INCOMPATIBLE_SKILLS` + `_build_recovery_message` +
override hatch `allow_interactive_skill=True`) is preserved +
EXTENDED with v1.0.6 J-3 headless guard.

The v1.0.4 Path 3 `--parallel` architecture (`partition_by_tracks` +
`_dispatch_tracks_concurrent` + `--task-ids` filter +
`--no-recursive` guard) is preserved unchanged. v1.0.6 EXERCISES
it via Q1'=c self-dispatch dogfood.

The v1.0.5 per-worker sidecar (I-1) + scratch (I-2) + flag
forwarding (I-3) patterns preserved unchanged. v1.0.6 K-2 removes
the `getattr` noop fallback that was defensive scaffolding for
v1.0.5 Track Alpha → Track Beta cross-track import dependency.

The v1.0.5 Item D Q3-A `_preflight_triplet_check` HARD-BLOCK is
preserved + RENAMED to `_preflight` per K-3 with 1-cycle backwards
compat alias.

---

## 10. Referencias

- Spec base v1.0.6: `sbtdd/spec-behavior-base.md` (committed
  `30567a2` on `feature/v1.0.6-bundle`).
- Contrato autoritativo
  v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5
  frozen: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.5 ship record: tag `v1.0.5` (commit `8539af1`); branch
  `feature/v1.0.6-bundle` branched off `main` HEAD `d5f68bb` =
  v1.0.5 docs commit on top of `8539af1` merge.
- v1.0.4 ship record: tag `v1.0.4` (commit `87f14a3`); merge
  `b1c5262` on `main`.
- v1.0.6 LOCKED memories:
  - `project_v105_shipped.md` (full v1.0.5 ship record + cycle
    metrics)
  - `project_v104_subprocess_headless_detection.md` (CRITICAL —
    J-class items J-1+J-2+J-3 details + acceptance criteria)
- v1.0.7 deferred backlog: 4 v1.0.5 polish WARNINGs not
  cherry-picked + worker-mode edge cases + coverage drift trend
  monitoring + K-3 alias removal.
- v1.1.0 deferred backlog: all v1.0.4 carry-forward inherited
  items.
- Brainstorming refinement decisions (2026-05-09):
  - Q1' = c `auto --parallel` self-dispatch dogfood (eats own
    dogfood; validates v1.0.5 production-grade `--parallel`
    end-to-end). Fallback: manual 2-track subagent dispatch (Q1'
    option b) if `auto --parallel` surfaces issues mid-cycle.
  - Q2' = a env var truthy values exact list `"1"`, `"true"`,
    `"yes"` case-insensitive (predictable; matches v1.0.4 Items
    A+B convention).
  - Q3' = a K-3 1-cycle deprecation alias removed in v1.0.7
    (private helper underscore-prefixed; courtesy not contract).
  - Q4' = b K-5 liberal scope regex `[^()]+` (operator UX over CC
    spec compliance; false-positives just mean triplet check
    passes).
  - Q5' = a default G2 ladder per spec-base baseline (defer
    K-2..K-5 first → C.2 → Pillar A hard-LOCKED); symmetric to
    v1.0.5 empirically validated pattern.
- Branch: trabajo en `feature/v1.0.6-bundle` (branched off `main`
  HEAD `d5f68bb`).
