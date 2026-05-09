# Especificacion base — sbtdd-workflow v1.0.6 (post-v1.0.5 ship)

> Generado 2026-05-09 a partir de v1.0.5 ship record + v1.0.4 LOCKED carry-forward (subprocess hang fix) + v1.0.5 Loop 2 iter-1 polish WARNINGs cherry-picked.
>
> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para
> v1.0.6). `/brainstorming` consumira este archivo y generara
> `sbtdd/spec-behavior.md` (BDD overlay con escenarios Given/When/Then
> testables).
>
> Generado 2026-05-09 post-v1.0.5 ship (tag `v1.0.5` at commit
> `8539af1`, branch `feature/v1.0.6-bundle` branched off `main` HEAD
> `d5f68bb` = v1.0.5 docs commit on top of `8539af1` merge).
>
> v1.0.6 = **operational unblock + polish cycle** per Bal v1.0.4
> INFO #17 magnet-release recommendation ("schedule a polish-only
> cycle soon"). Two focused pillars:
>
> - **Pillar A PRIMARY (HIGH operational value, LOCKED CRITICAL)** —
>   `/sbtdd spec` + `/sbtdd pre-merge` interactive subprocess hang
>   root-cause + fix via real headless detection (`SBTDD_HEADLESS=1`
>   env var + `os.isatty(0)` check). Originally v1.0.4 LOCKED commitment
>   J-class (per memory `project_v104_subprocess_headless_detection`),
>   deferred to v1.0.5, deferred again to v1.0.6 — no longer deferable.
> - **Pillar B LOCKED (LOW-RISK polish carry-forward)** — Track Gamma
>   C.2 plan archaeology trim methodology (deferred from v1.0.5
>   iter-2 G2 ladder) + 5 cherry-picked Loop 2 iter-1 polish
>   WARNINGs.
>
> v1.0.6 INV stance: **strict no-INV-0** (Q3 brainstorming decision)
> — preserve 7-cycle Checkpoint 2 streak goal + 2-cycle pre-merge
> Loop 2 streak (re-established at v1.0.5 from 1 cycle post-v1.0.4
> break). G1 cap=3 HARD Checkpoint 2 sin INV-0 path. G2 binding
> pre-staged: scope-trim ladder defers Pillar B polish items first,
> then Item C.2 methodology, finally only Pillar A
> (J-1+J-2+J-3) hard-LOCKED.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento NO lo
> reemplaza — agrega el delta v1.0.6 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder
> word-boundary verificable con `spec_cmd._INV27_RE` regex.

---

## 1. Objetivo

**v1.0.6 = "Operational unblock (subprocess hang fix) + polish carry-forward"**:
desbloquea `/sbtdd spec` + `/sbtdd pre-merge` end-to-end (currently
require manual fallback per spec sec.6.4) + cierra Pillar C C.2
methodology deferred de v1.0.5 + 5 cherry-picked Loop 2 iter-1 polish
WARNINGs.

Tres clases de items:

### Clase 1 — Pillar A PRIMARY (LOCKED CRITICAL — operational unblock)

- **Item J-1 — `SBTDD_HEADLESS=1` env var detection in
  subprocess dispatch wrappers**. Location: `superpowers_dispatch.py`
  `invoke_skill()` + `magi_dispatch.py` callsites + any
  subprocess.Popen/run wrapper that dispatches an interactive skill.
  Read `os.environ.get("SBTDD_HEADLESS")`; if truthy ("1", "true",
  "yes" case-insensitive), context is **explicitly headless**. Refuse
  subprocess dispatch for skills in `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  (currently `{brainstorming, writing-plans, receiving-code-review}`)
  with LOUD-FAST `PreconditionError` + actionable recovery guidance
  (cite `--resume-from-magi` for `/sbtdd spec`; cite manual
  `run_magi.py` for `/sbtdd pre-merge`).

- **Item J-2 — `os.isatty(0)` detection as fallback for unset env
  var**. Location: same wrappers as J-1. When `SBTDD_HEADLESS` env
  var is unset/empty, fall back to `os.isatty(0)` (stdin TTY check).
  If `not os.isatty(0)`, context is **implicitly headless** (e.g.,
  CI runner, subprocess of subprocess, piped invocation). Same
  refusal behavior as J-1. When stdin IS a TTY (interactive
  terminal), allow dispatch normally — preserves v1.0.5 behavior
  for interactive Claude Code sessions.

- **Item J-3 — Unified detection helper +
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` enforcement**. New module
  `subprocess_utils.is_headless_context() -> bool` consolidates
  J-1+J-2 logic. All `invoke_skill` callsites for skills in
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` MUST go through this guard
  (existing `allow_interactive_skill=True` override hatch
  preserved per v1.0.4 Items A+B). Acceptance: integration test
  asserting `SBTDD_HEADLESS=1 python -m skills.sbtdd.scripts.run_sbtdd
  spec` raises `PreconditionError` with recovery message naming
  `--resume-from-magi`. Plus regression test asserting normal
  interactive invocation (TTY stdin) succeeds via existing path.

### Clase 2 — Pillar B LOCKED (LOW-RISK polish carry-forward)

- **Item C.2 — Plan archaeology trim methodology** (carry-forward
  from v1.0.5 iter-2 G2 ladder defer). Same scope as v1.0.5 Track
  Gamma T5: methodology pattern documented in
  `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template` +
  smoke test `tests/test_plan_archaeology_trim_pattern.py`. Doc-only
  + 1 smoke test.

- **Item K-1 — `_section_has_flipped` per-checkbox parity** (Loop 2
  v1.0.5 iter-1 cas WARNING). Currently checks whole-section for
  `- [x]`; should match per-checkbox so a section with mixed
  `- [ ]` + `- [x]` returns False (not yet fully flipped). Affects
  `_apply_flips_from_diff` correctness in edge cases.

- **Item K-2 — `getattr` late-import fallback removal**
  (Loop 2 v1.0.5 iter-1 bal+cas WARNING). v1.0.5's defensive
  `getattr(close_task_cmd, "_merge_scratch_plans", noop)` fallback
  is no longer needed post-T3-land. Replace with direct
  `from close_task_cmd import _merge_scratch_plans` at function
  body (still late-import for cross-module dep correctness, but
  drop the noop fallback to surface helper-removal regressions).

- **Item K-3 — `_preflight_triplet_check` API rename to canonical
  `_preflight`** (Loop 1 v1.0.5 iter-2 bal Important #2 deferred to
  CHANGELOG). v1.0.5 implementer chose split helper for SRP +
  testability; cycle approved naming. v1.0.6 closes the deviation:
  rename `_preflight_triplet_check` to `_preflight`, update
  `close_task_cmd.main` callsite + 6+ test class references +
  monkeypatch in `_install_happy_path_patches`.

- **Item K-4 — `_FORWARDABLE_FLAGS` argparse-presence guard** (Loop
  2 v1.0.5 iter-1 cas WARNING). Currently iterates over hardcoded
  list assuming each flag exists in argparse namespace. Add guard
  asserting each `_FORWARDABLE_FLAGS` key exists as `argparse`
  attribute on the parent's namespace; raise `ValidationError` at
  startup if list drifts from argparse definition.

- **Item K-5 — Triplet check robust to Conventional Commits scope
  syntax** (Loop 2 v1.0.5 iter-1 cas WARNING). Currently
  `commits.validate_prefix` matches bare prefixes (`test:`, `feat:`,
  `fix:`, `refactor:`); should also match `test(scope):`,
  `feat(close-task):`, etc. per Conventional Commits spec. Affects
  `_preflight_triplet_check` regex matching when subagents emit
  scoped subjects. Update commit_create + validate_prefix + 1-2
  triplet-check callsites.

### Out of scope v1.0.6 (rolled forward a v1.0.7+)

- v1.0.5 deferred 4 polish WARNINGs not cherry-picked (defer
  rationale per item):
  - `mark_and_advance` API split (bal) — risky API change; defer
    to v1.0.7 LOCKED if `mark_and_advance` API churn surfaces in
    operator feedback
  - I2-4 race test runtime cost optimization (cas) — nice-to-have;
    defer to v1.0.7 polish-only
  - `--skip-preflight` UX discoverability touchpoint (bal) — doc-only;
    fold into v1.0.7 polish if README/SKILL.md edits cluster there
  - I-3 model_override list-value flattening test strengthening
    (mel) — narrow; defer to v1.0.7 if needed
- Coverage drift -0.45% trend monitoring (bal+mel) — process-only
  task, deferred indefinitely (no concrete action item)
- Worker-mode hardcoded plan path / `_apply_flips_from_diff`
  ValueError edge case (mel) — narrow drift cases unlikely; defer
  to v1.0.7 if surfaces in field
- All v1.0.4 carry-forward inherited items (`agreement_rate` rename,
  `spec_lint` R3 promote, per-module coverage 85%, GitHub Actions CI,
  Migration tool real test, AST dead-helper detector codification,
  W8 Windows fs retry-loop, `_read_auto_run_audit` skeleton wiring,
  spec sec.7.1.3 G2 amendment, `magi_cross_check` default-flip,
  Group B options 1/3/4/6/7) — defer to v1.1.0 cycle (major version
  bump for breaking changes)

### Criterio de exito v1.0.6

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.5 -> 1.0.6.
- Tests baseline 1248 + 1 skipped preservados sin regresion + ~10-15
  nuevos (J-1+J-2+J-3 headless detection: ~5-7; C.2 plan archaeology
  smoke: ~2-3; K-1..K-5 polish: ~3-5).
- `make verify` runtime <= 200s soft / 220s hard (acknowledges v1.0.5
  baseline 171s + ~10-20s incremental from new tests).
- Coverage threshold mantenido en 88% (v1.0.5 measured 89.88%; v1.0.6
  must not regress below).
- **`/sbtdd spec` end-to-end empirical validation**: under
  `SBTDD_HEADLESS=1`, `/sbtdd spec` raises `PreconditionError`
  LOUD-FAST con recovery message naming `--resume-from-magi`. Under
  interactive TTY, `/sbtdd spec` proceeds normally per existing path
  (regression test).
- **`/sbtdd pre-merge` end-to-end empirical validation**: under
  `SBTDD_HEADLESS=1`, `/sbtdd pre-merge` raises `PreconditionError`
  LOUD-FAST con recovery message naming manual `run_magi.py`
  fallback. Under interactive TTY, Loop 1 + Loop 2 proceed per
  existing path.
- **G1 binding HARD respetado**: cap=3 HARD para Checkpoint 2; sin
  INV-0. **7-cycle Checkpoint 2 no-override streak goal**
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6).
- **Pre-merge Loop 2 no-override streak preservation goal**:
  v1.0.5 re-established from 1 cycle. v1.0.6 = 2 cycles consecutive
  goal (sin INV-0 at Loop 2).
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no
  converge — defer Pillar B polish items K-2..K-5 first → defer
  Item C.2 methodology second → only Pillar A J-1+J-2+J-3 hard-LOCKED.

---

## 2. Alcance v1.0.6 — items LOCKED post-v1.0.5 ship

### 2.1 Item J-1 — `SBTDD_HEADLESS=1` env var detection (Pillar A PRIMARY CRITICAL)

**Track**: pending Q1 partition decision (likely Track Alpha).

**Archivos**:
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (`invoke_skill` headless guard pre-spawn)
- Modify: `skills/sbtdd/scripts/magi_dispatch.py` (analogous guard
  for MAGI dispatch when target skill is interactive)
- Modify: `skills/sbtdd/scripts/subprocess_utils.py` (new
  `is_headless_context()` helper consolidating J-1+J-2)
- Extend: `tests/test_superpowers_dispatch.py`,
  `tests/test_subprocess_utils.py` (new test class for headless
  detection)

**Empirical context (v1.0.5 ship reconfirmation)**:

v1.0.5 attempted `/sbtdd pre-merge`; ran Loop 1 iter-1 + iter-2
successfully but hung at iter-2 close on `/receiving-code-review`
subprocess (killed at 1200s timeout). v1.0.4 ship record claimed
"the hang was situational, not systemic" — v1.0.5 reconfirmed it IS
systemic. Manual fallback per spec sec.6.4 (`python skills/magi/scripts/run_magi.py`
direct dispatch + manual mini-cycle commits) used for v1.0.5 ship.

Root cause: interactive Claude skills (`/brainstorming`,
`/writing-plans`, `/receiving-code-review`) require a TTY for
their interactive prompts; when invoked via `claude -p` subprocess
they wait silently for input that never arrives.

**Implementation outline**:

```python
# subprocess_utils.py (new module-level helper)
def is_headless_context() -> bool:
    """v1.0.6 J-1+J-2: detect headless execution context.

    Returns True if either:
    - SBTDD_HEADLESS env var is set to truthy ("1", "true", "yes"
      case-insensitive) -- explicit headless declaration by operator
      or CI runner.
    - sys.stdin.isatty() returns False -- implicit headless (subprocess
      of subprocess, piped invocation, CI runner without explicit env).

    Returns False when stdin is a TTY AND env var unset/false --
    interactive Claude Code session, allow normal subprocess dispatch.
    """
    explicit = os.environ.get("SBTDD_HEADLESS", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return True
    try:
        return not sys.stdin.isatty()
    except (OSError, AttributeError):
        # Closed stdin or unusual environment -> assume headless
        return True
```

```python
# superpowers_dispatch.py invoke_skill (extended)
def invoke_skill(skill_name: str, ..., allow_interactive_skill: bool = False):
    """v1.0.4 Items A+B subprocess gate + v1.0.6 J-1+J-2+J-3 headless
    detection extension.
    """
    if skill_name in _SUBPROCESS_INCOMPATIBLE_SKILLS:
        if not allow_interactive_skill:
            raise PreconditionError(_build_recovery_message(skill_name))
        # Operator opted in via override -- but if context is headless,
        # subprocess will hang silently. Refuse LOUD-FAST per v1.0.6 J-3:
        if subprocess_utils.is_headless_context():
            raise PreconditionError(
                f"Cannot dispatch interactive skill {skill_name!r} via "
                f"`claude -p` subprocess: context is headless "
                f"(SBTDD_HEADLESS=1 set OR stdin not a TTY). The skill "
                f"requires an interactive terminal for its prompts. "
                f"Recovery: {_build_recovery_message(skill_name)}"
            )
    # ... existing subprocess dispatch ...
```

**Acceptance**: integration test with `SBTDD_HEADLESS=1` env set →
`/sbtdd spec` raises `PreconditionError` LOUD-FAST with message
naming `--resume-from-magi`; `/sbtdd pre-merge` raises with
message naming manual `run_magi.py` fallback. Regression test with
TTY stdin (mock `sys.stdin.isatty()` returning True) → existing
path proceeds normally.

### 2.2 Item J-2 — `os.isatty(0)` fallback (Pillar A PRIMARY CRITICAL)

Already covered by J-1's `is_headless_context()` helper which
includes the `sys.stdin.isatty()` fallback when env var is
unset/empty. J-2 is logically inseparable from J-1; ships in same
helper + same tests.

### 2.3 Item J-3 — Unified detection helper + `_SUBPROCESS_INCOMPATIBLE_SKILLS` enforcement (Pillar A PRIMARY CRITICAL)

Already covered by J-1's `subprocess_utils.is_headless_context()`
module-level helper. J-3 enforces the helper at all `invoke_skill`
callsites for skills in `_SUBPROCESS_INCOMPATIBLE_SKILLS` (currently
3 skills; future skills added to the set get the headless check
automatically). Existing `allow_interactive_skill=True` override
hatch preserved per v1.0.4 Items A+B contract — operator opt-in
still required, but operator opt-in PLUS headless context = refuse
(can't honor opt-in safely if subprocess will hang).

### 2.4 Item C.2 — Plan archaeology trim methodology (Pillar B carry-forward)

Carry-forward from v1.0.5 iter-2 G2 ladder defer. Same scope as
v1.0.5 Track Gamma T5 spec sec.2.6:

- Modify `skills/sbtdd/SKILL.md`: add ship-time procedure section
  "At v1.0.X ship time, extract iter-by-iter triage context from
  `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]` Process
  notes section. Trim plan-tdd.md to 'active plan only' (scope +
  tasks + acceptance; no iter-1/iter-2/iter-3 archaeology)."
- Modify `templates/CLAUDE.local.md.template`: add same procedure
  reference for destination projects + cross-link to SKILL.md.
- Create `tests/test_plan_archaeology_trim_pattern.py`: smoke test
  asserting both files contain the procedure reference (case-
  insensitive substring match per v1.0.4 doc-only smoke test
  pattern).

### 2.5 Items K-1..K-5 — Polish WARNINGs (Pillar B)

**K-1** `_section_has_flipped` per-checkbox parity:
- Modify: `close_task_cmd.py:_section_has_flipped`
- Tests: extend `tests/test_close_task_cmd.py` race scenarios with
  mixed-checkbox section (some `[x]`, some `[ ]`) →
  `_apply_flips_from_diff` must not assume already-flipped just
  because section contains one `[x]`.

**K-2** `getattr` late-import fallback removal:
- Modify: `auto_cmd.py:_dispatch_tracks_concurrent` post-batch
  hook. Replace `getattr(close_task_cmd, "_merge_scratch_plans", noop)`
  with direct `from close_task_cmd import _merge_scratch_plans`
  (still late-import inside function body for cross-module dep
  correctness; drop the noop fallback).
- Tests: existing tests cover; ensure no regression.

**K-3** `_preflight_triplet_check` to `_preflight` rename:
- Modify: `close_task_cmd.py` (function definition + 1 callsite),
  `tests/test_close_task_cmd.py` (TestPreflightHardBlock class +
  6+ test method assertions + `_install_happy_path_patches`
  monkeypatch target).
- Backwards-compat: keep `_preflight_triplet_check = _preflight`
  alias for one cycle; deprecation marker comment indicates
  removal in v1.0.7.

**K-4** `_FORWARDABLE_FLAGS` argparse-presence guard:
- Modify: `auto_cmd.py:_build_worker_argv`. At module load,
  validate each `_FORWARDABLE_FLAGS` ns_attr exists in
  `_build_argparse_parser()` output; raise `ValidationError` at
  module import if drift detected.
- Tests: meta-test asserting drift detection fires when fake flag
  added to `_FORWARDABLE_FLAGS` not in argparse.

**K-5** Triplet check robust to Conventional Commits scope syntax:
- Modify: `commits.py:validate_prefix` regex extended to match
  `test:`, `test(scope):`, `feat:`, `feat(scope):`, etc.
- Modify: `close_task_cmd.py:_preflight_triplet_check` regex
  matchers analogous extension.
- Tests: extend `tests/test_commits.py` + `tests/test_close_task_cmd.py`
  with scoped subjects.

### 2.6 v1.0.6 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B ship).

**Activities**:

1. **`/sbtdd spec` headless detection empirical validation** (~30
   min): set `SBTDD_HEADLESS=1` env var + invoke `/sbtdd spec`;
   assert `PreconditionError` raised with recovery message naming
   `--resume-from-magi`. Then unset env var + invoke in interactive
   TTY context; assert proceeds normally to existing flow.

2. **`/sbtdd pre-merge` headless detection empirical validation**
   (~30 min): same pattern as #1 but for pre-merge with manual
   `run_magi.py` recovery message.

3. **Pre-merge gate clean WITHOUT INV-0** (~variable): `/sbtdd
   pre-merge` end-to-end on interactive TTY. Per Q3 strict no-INV-0
   stance (v1.0.5 Q5 carry-forward): if Loop 2 doesn't converge
   cleanly within cap=5, escalate to user BEFORE applying INV-0.

4. **`/sbtdd spec --resume-from-magi` empirical validation**
   (deferred from v1.0.3 Activity E + v1.0.4 Activity E'): now
   feasible end-to-end since Pillar A J-1 empowers the recovery
   path semantically.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.6 NO propone
nuevos invariantes (los items son bug fix + polish + carry-forward).

Critical durante implementacion v1.0.6:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  7-cycle Checkpoint 2 no-override streak goal preserved
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5+v1.0.6). NO INV-0
  override en Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.6 multi-pillar bundle podria necesitar scope-trim si Loop 2
  hits structural findings — defer Pillar B polish items K-2..K-5
  first → defer Item C.2 second; Pillar A J-1+J-2+J-3 hard-LOCKED.
- **Pre-merge Loop 2 streak preservation**: v1.0.5 re-established
  from 1 cycle. v1.0.6 goal = 2 cycles consecutive sin INV-0. If
  unable to converge cleanly, escalate to user BEFORE applying INV-0
  override (per memory `feedback_manual_synthesis_exceptional`).
- **`/sbtdd spec` + `/sbtdd pre-merge` empirical dogfood requerida**
  post Pillar A ship: v1.0.6 cycle MUST exercise own dogfood under
  both headless (SBTDD_HEADLESS=1) AND interactive (TTY) contexts
  to validate J-1+J-2+J-3 fixes empirically.

### Stack y runtime

Sin cambios vs v1.0.5:
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
  v1.0.0..v1.0.5 = 6-cycle no-override streak; v1.0.6 preserves to 7).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F180 v1.0.5; v1.0.6 starts at F181.)

### Item J-1+J-2 — Headless detection helper

**F181**. New module-level helper
`subprocess_utils.is_headless_context() -> bool` consolidating
`SBTDD_HEADLESS` env var check + `sys.stdin.isatty()` fallback.

**F182**. Truthy values for `SBTDD_HEADLESS` env var: "1", "true",
"yes" case-insensitive (matches v1.0.4 Items A+B convention).

**F183**. When env var unset/empty/falsy AND stdin is a TTY:
return False (interactive context, allow dispatch). When env var
truthy OR stdin not a TTY: return True (headless context, refuse
dispatch for incompatible skills).

**F184**. OSError or AttributeError on `sys.stdin.isatty()` →
assume headless (defensive default).

### Item J-3 — Enforcement at incompatible skill callsites

**F185**. `superpowers_dispatch.invoke_skill()` extended with
headless context check: when skill in
`_SUBPROCESS_INCOMPATIBLE_SKILLS` AND
`subprocess_utils.is_headless_context()` returns True, raise
`PreconditionError` with recovery message naming the appropriate
fallback per skill (`--resume-from-magi` for `/brainstorming` +
`/writing-plans`; manual `run_magi.py` for `/receiving-code-review`).

**F186**. `magi_dispatch.py` analogous guard for MAGI dispatch when
target skill is interactive.

**F187**. `allow_interactive_skill=True` override hatch preserved
per v1.0.4 Items A+B contract; but headless context refusal cannot
be overridden (subprocess will hang, no safe path).

### Item C.2 — Plan archaeology trim methodology

**F188**. `skills/sbtdd/SKILL.md` documents ship-time plan
archaeology trim procedure.

**F189**. `templates/CLAUDE.local.md.template` includes
archaeology trim guidance for destination projects.

**F190**. `tests/test_plan_archaeology_trim_pattern.py` smoke test
asserts SKILL.md + template both reference the procedure.

### Items K-1..K-5 — Polish

**F191** (K-1). `_section_has_flipped` per-checkbox parity.

**F192** (K-2). `getattr` late-import fallback removed; direct
`from close_task_cmd import _merge_scratch_plans` inside function
body.

**F193** (K-3). `_preflight_triplet_check` renamed to `_preflight`
+ 1-cycle deprecation alias.

**F194** (K-4). `_FORWARDABLE_FLAGS` argparse-presence guard at
module import.

**F195** (K-5). Triplet check + `commits.validate_prefix` regex
extended for Conventional Commits scope syntax.

### Requerimientos no-funcionales (NF)

**NF47**. `make verify` runtime <= 200s soft target / 220s hard
(acknowledges v1.0.5 baseline 171s + new tests).

**NF48**. v1.0.5 plans (with state file v1.0.5 schema) parse
correctly; no migration required for v1.0.6.

**NF49**. Per-module coverage threshold preserved at 88% (no
regression).

**NF50**. v1.0.6 own-cycle dogfood under both headless
(SBTDD_HEADLESS=1) AND interactive (TTY) contexts validates
J-1+J-2+J-3 fixes empirically.

**NF51**. v1.0.6 ship WITHOUT INV-0 override at pre-merge Loop 2
(2-cycle streak goal).

**NF52**. v1.0.6 ship WITHOUT INV-0 override at Checkpoint 2
(7-cycle streak goal).

---

## 5. Scope exclusions

Out-of-scope v1.0.6 (rolled forward a v1.0.7+):

- 4 v1.0.5 deferred polish WARNINGs not cherry-picked
- Coverage drift trend monitoring
- Worker-mode hardcoded plan path / `_apply_flips_from_diff`
  ValueError edge case

Out-of-scope v1.0.6+ (rolled forward a v1.1.0):

- All v1.0.4 carry-forward inherited items (`agreement_rate`
  rename, `spec_lint` R3 promote, per-module coverage 85%, GitHub
  Actions CI workflow, Migration tool real test, AST dead-helper
  detector codification, W8 Windows fs retry-loop,
  `_read_auto_run_audit` skeleton wiring, spec sec.7.1.3 G2
  amendment, `magi_cross_check` default-flip, Group B options
  1/3/4/6/7) — defer to v1.1.0 cycle (major version bump for
  breaking changes)

---

## 6. Criterios de aceptacion finales

v1.0.6 ship-ready cuando:

### 6.1 Functional Items J-1/J-2/J-3 + C.2 + K-1..K-5

- **F1**. F181-F184: J-1+J-2 headless detection helper +
  truthy/falsy/TTY semantics.
- **F2**. F185-F187: J-3 enforcement at incompatible skill
  callsites + override hatch contract preserved.
- **F3**. F188-F190: C.2 plan archaeology trim methodology
  documented + smoke test.
- **F4**. F191 (K-1): `_section_has_flipped` per-checkbox parity.
- **F5**. F192 (K-2): `getattr` late-import fallback removed.
- **F6**. F193 (K-3): `_preflight_triplet_check` renamed +
  deprecation alias.
- **F7**. F194 (K-4): `_FORWARDABLE_FLAGS` argparse-presence guard.
- **F8**. F195 (K-5): Conventional Commits scope syntax support.

### 6.2 No-functional

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

### 6.3 Process

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
  pre-merge` validated under both headless (SBTDD_HEADLESS=1) AND
  interactive (TTY) contexts.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.6 ship + items + dogfood
  observations).
- **D3**. Documented:
  - J-1+J-2+J-3 headless detection in `subprocess_utils.py`
    docstring + README common-flags section + SKILL.md v1.0.6 notes.
  - C.2 plan archaeology trim procedure in SKILL.md +
    `templates/CLAUDE.local.md.template`.
  - K-3 `_preflight_triplet_check` to `_preflight` rename in
    CHANGELOG + 1-cycle deprecation alias mention.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.6

- **R1**. J-1+J-2 isatty detection may false-positive in some CI
  environments where stdin is a pseudo-TTY but interactive skills
  still hang. Mitigation: explicit `SBTDD_HEADLESS=1` env var
  takes precedence; operators in problematic CI set the var
  explicitly.
- **R2**. K-3 `_preflight_triplet_check` to `_preflight` rename may
  break operator scripts that monkeypatch the old name. Mitigation:
  1-cycle deprecation alias preserves backwards compat; deprecation
  marker comment clearly signals migration timeline (removal in
  v1.0.7).
- **R3**. K-5 Conventional Commits scope syntax extension may
  introduce false positives for non-CC subjects that happen to
  contain `(text):` pattern. Mitigation: regex anchored to
  start-of-string + bounded scope content per CC spec; tests cover
  edge cases.
- **R4**. v1.0.6 own-cycle dogfood under SBTDD_HEADLESS=1 may surface
  J-1+J-2+J-3 fix gaps not caught by tests. Mitigation: dogfood is
  non-blocking for ship (acceptance via tests primarily; dogfood
  empirical is bonus); if dogfood fails, document + roll forward to
  v1.0.7 patch.
- **R5**. Pre-merge Loop 2 streak preservation goal (Q3 strict
  no-INV-0) may not be achievable if cycle surfaces fundamental
  architectural questions. Mitigation: G2 scope-trim ladder
  (defer Pillar B polish items first → then C.2 methodology); INV-0
  remains available but escalated to user before application.
- **R6**. Pillar A scope creep: J-1+J-2+J-3 are tightly coupled but
  Q1 partition decision matters for subagent dispatch. Likely
  single-track ownership.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.5 ship record: tag `v1.0.5` (commit `8539af1`); branch
  `feature/v1.0.6-bundle` branched off `main` HEAD `d5f68bb`
  (v1.0.5 docs commit on top of `8539af1` merge).
- v1.0.4 ship record: tag `v1.0.4` (commit `87f14a3`); merge
  `b1c5262` on `main`.
- v1.0.5 LOCKED memories:
  - `project_v105_shipped.md` (full v1.0.5 ship record + cycle
    metrics)
  - `project_v104_subprocess_headless_detection.md` (CRITICAL —
    J-class items J-1+J-2+J-3 details + acceptance criteria)
- v1.0.6 deferred backlog: 4 polish WARNINGs not cherry-picked +
  worker-mode edge cases + coverage drift trend monitoring.
- v1.1.0 deferred backlog: all v1.0.4 carry-forward inherited
  items.
- Branch: trabajo en `feature/v1.0.6-bundle` (branched off `main`
  HEAD `d5f68bb` = v1.0.5 docs commit).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.6 own-cycle**: per CLAUDE.local.md sec.1 Flujo
de especificacion + v1.0.5 Process notes precedent, brainstorming
se correra en sesion interactiva (esta sesion) via Skill tool
in-session. NO via `claude -p` subprocess (Pillar A J-1+J-2+J-3
hasn't shipped YET — chicken-and-egg, manual interactive Skill
invocation in-session is the canonical path until Pillar A lands
+ closes the loop).

**Hybrid methodology continued**: Opcion A manual `run_magi.py` for
Checkpoint 2 dispatch per v1.0.2+v1.0.3+v1.0.4+v1.0.5 precedent.
Once v1.0.6 Pillar A J-1+J-2+J-3 lands, future cycles' MAGI
Checkpoint 2 dispatch CAN attempt subprocess path (`/sbtdd spec`
end-to-end), with the new headless detection raising fail-fast
in headless contexts.

Decisiones pendientes clave para brainstorming (Q1-Q5 estimated):

1. **Subagent partition (Q1)**: 7 items (J-1+J-2+J-3 in Pillar A;
   C.2 + K-1+K-2+K-3+K-4+K-5 in Pillar B). Posibles particiones:
   - **Single subagent sequential**: J-1+J-2+J-3 first (logically
     coupled, single helper) → C.2 → K-1..K-5. ~2-3 dias wall-time.
   - **2-track parallel**: Track Alpha = Pillar A J-1+J-2+J-3
     (subprocess_utils.py + superpowers_dispatch.py + magi_dispatch.py
     + tests); Track Beta = Pillar B C.2 + K-1..K-5 (close_task_cmd.py
     + auto_cmd.py + commits.py + SKILL.md + template + tests).
     File-disjoint surfaces. ~1.5 dias wall-time. Recommended.
   - **Use `auto --parallel` self-dispatch dogfood**: deferred from
     v1.0.5; v1.0.6 could use it post Pillar A ship to dispatch
     remaining tasks. Nice-to-have; not blocking.

2. **J-1+J-2 truthy values for `SBTDD_HEADLESS` env var (Q2)**:
   exact match list (`"1"`, `"true"`, `"yes"` case-insensitive)
   per F182 baseline OR also accept `"on"`, `"enabled"`, etc. for
   broader UX. Brainstorming evaluates UX vs precision.

3. **K-3 backwards-compat strategy (Q3)**: 1-cycle deprecation
   alias `_preflight_triplet_check = _preflight` removed in v1.0.7
   (per F193 baseline) OR longer deprecation window (2-3 cycles).
   Brainstorming evaluates operator migration cost vs API churn.

4. **K-5 Conventional Commits regex strictness (Q4)**: bounded
   scope content (per CC spec, scope is `[a-z0-9-]+` lowercase
   alphanumeric + dashes) OR liberal (any non-paren content).
   Strict matches CC spec literally; liberal accepts more
   real-world subjects. Brainstorming evaluates.

5. **MAGI Checkpoint 2 budget allocation (Q5)**: bundle 8 items
   (J-1+J-2+J-3 + C.2 + K-1..K-5) — esperamos converger en 1-2
   iters dado que Pillar A es bien-scoped + Pillar B es polish.
   Iter 3 triggers G2 scope-trim default. Defer Pillar B polish
   K-2..K-5 a v1.0.7 first; then C.2; Pillar A J-1+J-2+J-3
   hard-LOCKED.

Brainstorming refinara estas decisiones basado en complejidad,
risk, y empirical findings de v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4
+v1.0.5 precedents.
