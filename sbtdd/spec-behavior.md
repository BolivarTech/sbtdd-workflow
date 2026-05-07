# BDD overlay — sbtdd-workflow v1.0.4

> Generado 2026-05-07 a partir de `sbtdd/spec-behavior-base.md` v1.0.4.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1+v1.0.2+v1.0.3 precedent
> (Finding A subprocess pattern preserved hasta v1.0.4 ships los
> fixes propios — chicken-and-egg).
>
> v1.0.4 ships los items LOCKED CRITICAL del original cycle plan
> per memory `project_v104_subprocess_headless_detection.md` +
> `project_v104_parallel_task_dispatcher.md` mas methodology gap
> fix surfaced empirically en v1.0.3 dogfood (close-phase skip
> when raw `git commit` used per Q2 v1.0.2 mandate).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.4**: arregla el v1.0.4 LOCKED CRITICAL del CHANGELOG
`[1.0.3]` Deferred section — real headless detection eliminating
the `/receiving-code-review` interactive subprocess hang that blocked
v1.0.3 Activity D' + Activity E' empirical validation. Plus the
v1.0.3 LOCKED parallel task dispatcher per memory
`project_v104_parallel_task_dispatcher.md`. Plus methodology gap
fix (close-phase per-phase mandate via Q3 Option B doc-only
enforcement) surfaced empirically by both Track Alpha + Track Beta
v1.0.3 subagents.

Tres pillars:

- **Pillar A PRIMARY (LOCKED CRITICAL)** — Items A+B coupled real
  headless detection + 600s LOUD-FAST PreconditionError fix.
- **Pillar B LOCKED HIGH VALUE** — Item C parallel task dispatcher
  with `--parallel` flag on existing `/sbtdd auto`.
- **Pillar C LOCKED defensive** — Item D phase auto-advance
  methodology gap fix via Q3 Option B doc-only mandate.

Decisiones de brainstorming 2026-05-07 (Q1-Q5):

- **Q1 — Subagent partition**: Option 2 — 2-track parallel.
  - Track Alpha (subagent #1, sequential A → B coupled): Items
    A+B headless detection refactor in `superpowers_dispatch.py`
    + tests. ~1 dia wall-time.
  - Track Beta (subagent #2, sequential C → D): Item C parallel
    dispatcher (new modules + auto_cmd flag) + Item D doc-only
    enforcement. ~2 dias wall-time.
  - Cero file overlap verificado: Alpha touches
    `superpowers_dispatch.py` + `test_superpowers_dispatch.py` +
    `test_invoke_skill_callsites_audit.py` extension; Beta touches
    `dag_parser.py` (new), `parallel_dispatcher.py` (new),
    `auto_cmd.py`, `test_dag_parser.py` (new),
    `test_parallel_dispatcher.py` (new), `test_auto_cmd.py`,
    plan template, `skills/sbtdd/SKILL.md` (Item D doc).

- **Q2 — Item C API surface**: Option A — `--parallel` flag on
  existing `/sbtdd auto` subcommand. Default off; sequential
  preserves v1.0.3 behavior exactly. No new subcommand surface.

- **Q3 — Item D Option A vs B**: Option B — mandate close-phase
  per Red/Green/Refactor commit via doc-only enforcement. Higher
  discipline; v1.0.3 dogfood proved subagents diverged from v1.0.2
  Q2 Option B mandate despite documentation, but v1.0.4 elevates
  the convention to the plan template + writing-plans extension +
  subagent-driven-development docs (3-touchpoint enforcement vs
  v1.0.2 single I5 process notes mention). NO `close_task_cmd`
  modification.

- **Q4 — Activity E' sequencing**: Option C — both pre-Track-close
  AND post-Track-close exercises. Pre validates `--resume-from-magi`
  happy path during plan-approval phase; post validates R10
  commit-conflict + R4 autoregen interaction post-impl. Both
  non-gating per hybrid methodology.

- **Q5 — MAGI Checkpoint 2 budget**: cap=3 HARD G1 binding
  preserved (4-cycle no-override streak v1.0.0+v1.0.1+v1.0.2+v1.0.3);
  iter-2 CRITICAL trigger preserved per v1.0.3 spec sec.6.1; G2
  scope-trim ladder defers Item D doc-only first → Item C parallel
  dispatcher second; Items A+B hard-LOCKED (cycle's primary
  CRITICAL).

**Hybrid methodology continued**: Opcion A manual `run_magi.py`
for Checkpoint 2 dispatch per v1.0.2+v1.0.3 precedent (v1.0.4
own-cycle brainstorming + writing-plans NOT via subprocess;
chicken-and-egg since v1.0.4 ships the fix itself). Activity E'-pre
exercises `--resume-from-magi` BEFORE Track dispatch; Activity
E'-post exercises post-impl as smoke test.

**Criterio de exito v1.0.4 (refinado vs spec-base)**:

- Tests baseline 1105 + 1 skipped preservados + ~35-50 nuevos =
  ~1140-1155 final (Item A headless detection ~12-18; Item B
  recovery message ~3-5; Item C parallel dispatcher ~15-20 incl.
  DAG parser + collision detection + cumulative-diff Loop 2
  wiring; Item D doc-only smoke ~3-5).
- `make verify` runtime <= 165s (NF-A); soft-target <= 155s.
- Coverage threshold mantenido en 88% (per Q4 v1.0.2 baseline).
- **Activity D' retry empirical validation**: `/sbtdd pre-merge`
  end-to-end completion sin subprocess hang on
  `/receiving-code-review`.
- **Activity E'-pre validated**: `/sbtdd spec --resume-from-magi`
  happy path on hand-crafted artifacts during plan-approval phase.
- **Activity E'-post validated**: `--resume-from-magi` smoke test
  post Track-close; observable R4+R10 interactions documented
  (non-gating).
- **Parallel dispatcher dogfood**: v1.0.4 own-cycle uses Item C
  `--parallel` flag during Track Beta own-cycle (chicken-and-egg
  signal: validates Item C while implementing it).
- v1.0.3 LOCKED carry-forward del CHANGELOG `[1.0.3]` Deferred
  (v1.0.4) section enteramente cerrados.
- G1 binding respetado: cap=3 HARD; sin INV-0. 5-cycle no-override
  streak preserved.
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no
  converge — defer Item D doc-only first; then Item C; Items A+B
  hard-LOCKED.

---

## 2. Items LOCKED

### 2.1 Item A — Real headless detection (Pillar A PRIMARY CRITICAL, Track Alpha)

**Track**: Alpha (subagent #1, sequential A → B coupled).

**Archivos**:
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (`invoke_skill` + helper `_is_headless_context()` + extend
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` set).
- Extend: `tests/test_superpowers_dispatch.py` (escenarios A-1
  through A-7 + B-1 through B-3).
- Extend: `tests/test_invoke_skill_callsites_audit.py`
  (allow_interactive_skill audit unchanged; add audit for
  `_is_headless_context` callsites consistency).

**Empirical context (v1.0.3 ship)**:

`/sbtdd pre-merge` Loop 1 fix-finding triage step invoked
`/receiving-code-review` via subprocess. Hung 600s waiting
interactive input. Operator killed via TaskStop + manual fallback
per spec sec.6.4. v1.0.1's `_SUBPROCESS_INCOMPATIBLE_SKILLS = {
"brainstorming", "writing-plans"}` whitelist did NOT include
`receiving-code-review` despite empirically interactive.
Conservative baseline + override hatch
(`allow_interactive_skill: bool = False`) caught silent-no-op
manifestation post-spawn but not the 600s hang manifestation.

**Implementation**:

1. New helper `_is_headless_context() -> bool`:
   ```python
   def _is_headless_context() -> bool:
       """Return True if SBTDD is running in a headless context.

       Detection signals (any one is sufficient):
       - SBTDD_HEADLESS env var is "1" / "true" / "yes" (case-insensitive)
       - sys.stdin.isatty() returns False AND SBTDD_INTERACTIVE env var
         is NOT set to "1" / "true" / "yes"
       """
       headless = os.environ.get("SBTDD_HEADLESS", "").lower()
       if headless in {"1", "true", "yes"}:
           return True
       interactive = os.environ.get("SBTDD_INTERACTIVE", "").lower()
       if interactive in {"1", "true", "yes"}:
           return False
       try:
           return not sys.stdin.isatty()
       except (AttributeError, OSError):
           return True  # safe default
   ```

2. Extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set:
   ```python
   _SUBPROCESS_INCOMPATIBLE_SKILLS = frozenset({
       "brainstorming",
       "writing-plans",
       "receiving-code-review",  # v1.0.4 added per v1.0.3 dogfood
   })
   ```

3. Document membership criteria in module docstring:
   ```
   A skill is subprocess-incompatible iff it requires multi-turn
   interactive dialogue with the operator (cannot complete via
   single non-interactive subprocess invocation).

   Audit history:
   - v1.0.1: brainstorming + writing-plans (Finding A discovery).
   - v1.0.4: + receiving-code-review (v1.0.3 Activity D' empirical
     hang during Loop 1 fix-finding triage).
   ```

4. Modify `invoke_skill(skill, prompt, ..., allow_interactive_skill=False)`:
   ```python
   def invoke_skill(skill, prompt, ..., allow_interactive_skill=False):
       if (
           skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
           and _is_headless_context()
           and not allow_interactive_skill
       ):
           raise PreconditionError(
               _build_headless_recovery_message(skill)
           )
       # existing subprocess.run path unchanged
       ...
   ```

5. `allow_interactive_skill=True` kwarg preserved as override
   (backward compat for v1.0.1 wrappers `brainstorming(...)`,
   `writing_plans(...)`). New wrapper `receiving_code_review(...)`
   passes `allow_interactive_skill=True` ONLY when caller is a
   known-safe interactive callsite (e.g., interactive Loop 1
   triage in operator-controlled session). Default-off elsewhere.

**Tests**: ~12-18 covering escenarios A-1 through A-7.

### 2.2 Item B — 600s subprocess hang LOUD-FAST fix (Pillar A PRIMARY CRITICAL, Track Alpha, coupled with A)

**Track**: Alpha (subagent #1, after Item A).

**Archivos**: same as Item A (coupled within `superpowers_dispatch.py`).

**Empirical context**: v1.0.3 Activity D' hang manifested as 600s
subprocess wait-then-fail. v1.0.1 only caught silent-no-op
manifestation (skill ran but produced no output) via post-spawn
heuristics; PRE-spawn hang (operator-blocking) was uncaught.

**Implementation**:

1. New helper `_build_headless_recovery_message(skill: str) -> str`:
   ```python
   def _build_headless_recovery_message(skill: str) -> str:
       sbtdd_headless = os.environ.get("SBTDD_HEADLESS", "<unset>")
       try:
           isatty = sys.stdin.isatty()
       except (AttributeError, OSError):
           isatty = False
       per_skill = _PER_SKILL_RECOVERY.get(skill, _GENERIC_RECOVERY)
       return (
           f"Skill `/{skill}` cannot run via `claude -p` subprocess in "
           f"headless context (interactive dialogue required). Detected:\n"
           f"  SBTDD_HEADLESS={sbtdd_headless} | stdin.isatty()={isatty}\n"
           f"Recovery options:\n"
           f"{per_skill}\n"
           f"  Set SBTDD_INTERACTIVE=1 if you ARE in interactive context\n"
           f"  but isatty() returns false (rare; e.g., piped script)."
       )
   ```

2. Per-skill recovery dictionary `_PER_SKILL_RECOVERY`:
   ```python
   _PER_SKILL_RECOVERY = {
       "brainstorming": (
           "  1. Run `/brainstorming` manually in interactive Claude "
           "Code session,\n     then use `/sbtdd spec --resume-from-magi`."
       ),
       "writing-plans": (
           "  1. Run `/writing-plans` manually in interactive Claude "
           "Code session,\n     then use `/sbtdd spec --resume-from-magi`."
       ),
       "receiving-code-review": (
           "  1. Run `/receiving-code-review` manually in interactive "
           "session, OR\n  2. Fall back to manual `python "
           "skills/magi/scripts/run_magi.py code-review <payload>`\n"
           "     per spec sec.6.4 + apply mini-cycle TDD fixes manually."
       ),
   }
   _GENERIC_RECOVERY = (
       "  1. Run the skill manually in interactive session,\n"
       "     then resume the SBTDD workflow."
   )
   ```

3. Coupled with Item A: `invoke_skill` raises `PreconditionError`
   BEFORE subprocess spawn when headless detected. Eliminates 600s
   hang by construction.

**Tests**: ~3-5 covering B-1 through B-3.

### 2.3 Item C — Parallel task dispatcher (Pillar B LOCKED HIGH VALUE, Track Beta)

**Track**: Beta (subagent #2, first sequential task).

**Archivos**:
- Create: `skills/sbtdd/scripts/dag_parser.py` (NEW module).
- Create: `skills/sbtdd/scripts/parallel_dispatcher.py` (NEW module).
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (`--parallel` flag
  wiring; sequential default preserved).
- Create: `tests/test_dag_parser.py` (NEW).
- Create: `tests/test_parallel_dispatcher.py` (NEW).
- Modify: `tests/test_auto_cmd.py` (extend with parallel mode tests).

**Empirical context**: v0.4.0 + v0.5.0 + v1.0.0 + v1.0.2 + v1.0.3
cycles all manually dispatched 2-track parallel subagents via the
orchestrator Agent tool. ~40% wall-time savings vs sequential.
Pattern hand-coded each cycle. v1.0.4 codifies as plugin feature.

**Implementation**:

1. `dag_parser.py` — parses `planning/claude-plan-tdd.md`:
   - Extract `### Task N:` blocks via line-anchored regex.
   - Extract dependency markers per task: `**Depends on**: Task M`
     OR `**addBlockedBy**: [Task M, Task K]` OR
     `**Files:** ...` for file surface collision detection.
   - Build directed acyclic graph: nodes = tasks, edges = explicit
     dependencies. Validate acyclic (raise `ValidationError` on
     cycle).
   - Public API:
     ```python
     def parse_plan(plan_path: Path) -> TaskGraph:
         """Parse plan file, return TaskGraph."""

     class TaskGraph:
         tasks: dict[str, Task]  # task_id -> Task
         edges: dict[str, set[str]]  # task_id -> dependency task_ids
         def antichains(self) -> list[set[str]]:
             """Return list of maximal antichains (parallel batches)
             respecting dependencies + file-surface collisions."""
     ```

2. `parallel_dispatcher.py` — file surface collision detection +
   batch dispatch:
   - `_files_collide(task_a: Task, task_b: Task) -> bool` — true
     if any file appears in both tasks' `Files:` lists (Create or
     Modify).
   - `partition_by_collision(antichain: set[str], graph: TaskGraph)
     -> list[set[str]]` — splits dependency-free batch into
     surface-disjoint sub-batches.
   - `dispatch_batch(batch: set[str], graph: TaskGraph, ...)` —
     spawns N subagent processes concurrently via subprocess.Popen
     (or signals orchestrator to use Agent tool fan-out — exact
     transport pending Track Beta subagent investigation).
   - Coordinate state file writes: each subagent writes its own
     `current_task_id` + phase advances; parallel_dispatcher uses
     file-lock or atomic-rename semantics to avoid race conditions
     on `.claude/session-state.json`.

3. `auto_cmd.py` — `--parallel` flag wiring:
   - Default `parallel: bool = False` preserves v1.0.3 sequential
     behavior exactly (no regression).
   - When `--parallel`:
     - Parse plan via `dag_parser.parse_plan(...)`.
     - Iterate antichains; for each: partition by collision;
       dispatch sub-batch concurrently.
     - Wait all subagents in batch complete before next batch.
     - MAGI Loop 2 fires ONCE at end on cumulative diff (vs
       per-task in sequential).
     - TDD-Guard semantics per spec sec.3 multi-agent rules:
       parallel mode in same worktree requires TDD-Guard OFF
       (operator toggle). Document in `--parallel` help text +
       README + raise warning on entry if TDD-Guard ON detected.

4. Backward compat: existing `auto_cmd._task_loop` sequential code
   path preserved; new code path branches on `parallel` flag.

**Tests**: ~15-20 covering escenarios C-1 through C-9.

### 2.4 Item D — Phase auto-advance methodology gap fix (Pillar C LOCKED defensive, Track Beta, doc-only)

**Track**: Beta (subagent #2, after Item C).

**Archivos** (DOC-ONLY, NO production code):
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add
  close-phase per-commit mandate).
- Modify: `templates/CLAUDE.local.md.template` (template guidance
  to destination projects).
- Modify: writing-plans skill prompt extension (plan template
  generation includes close-phase commands per Red/Green/Refactor
  step, NOT raw `git commit`).
- Create: `tests/test_close_phase_subagent_pattern.py` (smoke test
  for doc-coherence; pattern follows v1.0.2 Item E doc-only smoke).

**Empirical context**: v1.0.3 Track Alpha + Track Beta both had to
manually edit `.claude/session-state.json` to advance
`current_phase` from `red` → `refactor` before invoking close-task.
Plan's literal `git commit` commands skip the close-phase wrapper
that does phase advance. v1.0.2 Q2 Option B mandate
(`/sbtdd close-task` automation) was insufficient because plans
still emitted raw `git commit` instructions per Red/Green/Refactor
phase commit.

**Implementation (Q3 Option B — mandate close-phase per phase commit)**:

1. `skills/sbtdd/SKILL.md` orchestrator rules add explicit:
   > Subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py
   > close-phase` after each Red/Green/Refactor verify-clean. Manual
   > `git commit` per phase BYPASSES the phase-advance + state-file
   > update + verification gate; treated as NON-CONFORMING and
   > triggers drift detection on next `close-task`.

2. `templates/CLAUDE.local.md.template` updated to include the
   per-phase close-phase rule + reference to close-phase command +
   reference to v1.0.4 Item D rationale.

3. Writing-plans skill prompt extension: plan template generation
   produces TDD steps as:
   ```markdown
   - [ ] **Step N (Red): Write failing test**

   ```python
   ...
   ```

   - [ ] **Step N+1: Run pytest -v, verify FAIL**
   - [ ] **Step N+2: close-phase Red**

   Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

   Expected: pytest verify-clean fails (Red phase legitimacy),
   atomic `test:` commit landed, state file advances to `green`.
   ```

4. Smoke test in `tests/test_close_phase_subagent_pattern.py`:
   - Asserts that `skills/sbtdd/SKILL.md` contains the per-phase
     close-phase mandate string (case-sensitive substring match).
   - Asserts that `templates/CLAUDE.local.md.template` contains
     the same.
   - Asserts that the writing-plans skill prompt extension (or
     template fixture) contains the close-phase command in
     per-phase steps (ASCII-anchored regex).

**Tests**: ~3-5 covering escenarios D-1 through D-3.

### 2.5 Activity D' retry — Linux/POSIX dogfood completion (methodology, mid-cycle orchestrator)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (config + run de comandos).

**Pasos del orchestrator post Track-Alpha + Track-Beta close**:

1. Verify Items A+B fix landed in working tree
   (`superpowers_dispatch.py` includes `_is_headless_context` +
   extended `_SUBPROCESS_INCOMPATIBLE_SKILLS`).
2. Set `SBTDD_INTERACTIVE=1` env var (operator IS in interactive
   Claude Code session).
3. Run `/sbtdd pre-merge` end-to-end:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
4. Verify `/receiving-code-review` subprocess fires successfully
   under interactive context (Item A `SBTDD_INTERACTIVE=1`
   override permits).
5. Verify Loop 1 fix-finding triage step completes WITHOUT 600s
   hang.
6. Capture Loop 2 cross-check artifacts:
   ```bash
   ls .claude/magi-cross-check/iter*-*.json
   ```
7. Document findings in CHANGELOG `[1.0.4]` Process notes:
   - Cross-check meta-reviewer succeeded (FIRST empirical fire on
     full /sbtdd pre-merge path post v1.0.3 Item B Windows fix).
   - Iter count Loop 2.
   - Cross-check decision distribution.
   - Per-skill recovery messages observed for any skill that hit
     PreconditionError (none expected with `SBTDD_INTERACTIVE=1`).

**Failure mode** (R7 risk): if Items A+B fix incomplete, document
+ retry. Methodology activity is non-blocking for ship per hybrid
methodology semantics.

### 2.6 Activity E'-pre — pre-Track-close `--resume-from-magi` (methodology, Q4 Option C)

**Track**: Methodology (orchestrator), BEFORE Track Alpha + Beta dispatch.

**Archivos**: ninguno (test path exercise).

**Pasos del orchestrator** (during plan-approval phase, after
brainstorming + writing-plans manual interactive completion):

1. Verify spec-behavior.md + plan-tdd-org.md exist (this cycle's
   plan-approval phase).
2. Pre-flight spec_lint dry-run (W5 v1.0.1 fix):
   ```bash
   python -m skills.sbtdd.scripts.spec_lint sbtdd/spec-behavior.md
   python -m skills.sbtdd.scripts.spec_lint planning/claude-plan-tdd-org.md
   ```
3. Invoke `/sbtdd spec --resume-from-magi`:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
   ```
4. Observe:
   - Brainstorming/writing-plans subprocess NOT spawned (verifiable
     via lack of subprocess output).
   - MAGI Checkpoint 2 dispatched on existing artifacts.
   - INV-37 composite-signature check fires correctly (no false
     PreconditionError).
   - Plan approval state file written on convergence.
5. Document observable behavior in CHANGELOG `[1.0.4]` Process
   notes:
   - Wall-clock end-to-end.
   - INV-37 tripwire behavior.
   - Any unexpected interactions.

**Note**: Activity E'-pre exercises the v1.0.1 A3
`--resume-from-magi` happy path on hand-crafted artifacts. It does
NOT exercise the v1.0.4 Items A+B fix because Checkpoint 2 dispatch
does not invoke `/receiving-code-review`. Activity D' retry covers
that.

### 2.7 Activity E'-post — post-Track-close `--resume-from-magi` smoke test (methodology, Q4 Option C)

**Track**: Methodology mid-cycle (orchestrator), AFTER Track-close
+ AFTER Activity D' retry.

**Archivos**: ninguno (test path exercise + Process notes).

**Pasos del orchestrator** (post Activity D'):

1. Spec-behavior.md + plan-tdd-org.md exist + are committed (true
   post-Track-close).
2. Pre-flight spec_lint dry-run (W5 v1.0.1 fix):
   ```bash
   python -m skills.sbtdd.scripts.spec_lint sbtdd/spec-behavior.md
   python -m skills.sbtdd.scripts.spec_lint planning/claude-plan-tdd-org.md
   ```
3. Invoke `/sbtdd spec --resume-from-magi` (post-impl):
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
   ```
4. Observe:
   - R10 commit-conflict observability: artifacts already
     committed; `_commit_approved_artifacts` behavior (no-op?
     amend? new commit?).
   - R4 autoregen interaction: spec-snapshot regenerated
     idempotently if Item D from v1.0.3 was rolled forward to
     v1.0.5 (still pending).
   - State file mutations: existing post-impl state vs
     `_create_state_file` overwrite behavior.
5. Document observable gaps in CHANGELOG `[1.0.4]` Process notes:
   - R10 commit-conflict behavior.
   - R4 autoregen-interaction behavior (or N/A if v1.0.5).
   - Any other unexpected behavior.

**Failure mode**: methodology activity is **non-gating for ship**.
If E'-post fails, document specific failure mode + roll forward to
v1.0.5 fix.

### 2.8 Parallel dispatcher dogfood (chicken-and-egg empirical signal)

**Track**: Methodology mid-cycle (orchestrator), during Track Beta
own-cycle.

**Sequencing constraint**: Track Beta must land Item C with
sequential `make verify` clean BEFORE the orchestrator opt-in to
`--parallel` for any subsequent task. Chicken-and-egg: cycle uses
the dispatcher being implemented, so failures self-attribute.

**Pasos**:

1. Track Beta lands Item C tests + impl + sequential `make verify`
   passes.
2. Track Beta lands Item D doc-only commits.
3. Orchestrator confirms `dag_parser` + `parallel_dispatcher` ship
   tests green.
4. Orchestrator dispatches v1.0.4 cycle's NEXT task (e.g.,
   CHANGELOG write, README update, version bump) USING
   `--parallel` mode if multi-task batch identified. Single-task
   batch falls back to sequential by construction.
5. Document parallel dispatch outcome in CHANGELOG `[1.0.4]`
   Process notes:
   - Wall-clock comparison vs sequential estimate.
   - Any race conditions or state-file conflicts observed.
   - DAG parser correctness (no missed dependencies).

**Failure mode**: if dispatcher dogfood surfaces blocking issue,
fall back to sequential dispatch + document as v1.0.5 refinement.
Non-gating for ship.

---

## 3. Cross-module contracts

v1.0.4 NO introduce nuevos cross-cuts mas alla de:

- **Item A+B coupled**: extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set
  + add `_is_headless_context` + add `_build_headless_recovery_message`
  in `superpowers_dispatch.py`. Existing `invoke_skill` signature
  preserved (positional + kwargs); `allow_interactive_skill=False`
  default unchanged.
- **Item C**: NEW modules `dag_parser.py` + `parallel_dispatcher.py`
  with explicit public API. No mutation of existing helpers.
  `auto_cmd.py` adds `--parallel` flag; sequential default
  unchanged.
- **Item D**: doc-only; NO Python module changes. Adds
  `tests/test_close_phase_subagent_pattern.py` smoke.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` (existing
  en `errors.py`).
- `subprocess_utils.run_with_timeout` unchanged.
- `_compute_loop2_diff_with_meta` (v1.0.0) unchanged.
- `_loop2_with_cross_check` (v1.0.0) unchanged.
- `_run_magi_checkpoint2` (v1.0.0+v1.0.1+v1.0.2) unchanged.
- INV-37 composite-signature output validation tripwire (v1.0.1)
  unchanged.
- `close_phase_cmd` + `close_task_cmd` unchanged (Item D Q3 Option
  B doc-only does NOT modify these per design — code path
  preserved).
- `state_file.SessionState` schema unchanged.
- `commits.validate_prefix` unchanged.

---

## 4. Escenarios BDD

Distribuidos por item (Tier 2 permissive regex per v1.0.1 Item A1).
Top-level numbering uses `## 4.` (R3 monotonic check satisfied).

### 4.1 Item A — Real headless detection

**Escenario A-1: SBTDD_HEADLESS=1 forces headless**

> **Given** Caller of `invoke_skill("receiving-code-review", ...)`
> con `os.environ["SBTDD_HEADLESS"] = "1"` y stdin TTY-attached.
> **When** `invoke_skill` invoked.
> **Then** `PreconditionError` raised BEFORE subprocess spawn.
> Error message contains "Skill `/receiving-code-review` cannot
> run via `claude -p` subprocess in headless context".

**Escenario A-2: SBTDD_HEADLESS=true case-insensitive**

> **Given** `os.environ["SBTDD_HEADLESS"] = "True"`.
> **When** `_is_headless_context()` invoked.
> **Then** Returns True. Case-insensitive accepts "1", "true", "yes",
> "TRUE", "Yes" (deterministic).

**Escenario A-3: stdin not TTY triggers headless**

> **Given** Caller con `os.environ["SBTDD_HEADLESS"]` unset y
> `sys.stdin.isatty()` returns False (e.g., piped script).
> **When** `_is_headless_context()` invoked.
> **Then** Returns True.

**Escenario A-4: SBTDD_INTERACTIVE=1 overrides isatty**

> **Given** `sys.stdin.isatty()` returns False y
> `os.environ["SBTDD_INTERACTIVE"] = "1"`.
> **When** `_is_headless_context()` invoked.
> **Then** Returns False. SBTDD_INTERACTIVE is the operator escape
> hatch for piped-script-but-actually-interactive contexts.

**Escenario A-5: receiving-code-review in incompatible set**

> **Given** Default `_SUBPROCESS_INCOMPATIBLE_SKILLS` frozenset.
> **When** `"receiving-code-review" in _SUBPROCESS_INCOMPATIBLE_SKILLS`.
> **Then** Returns True. Set membership extended from v1.0.1
> {brainstorming, writing-plans} to v1.0.4 {brainstorming,
> writing-plans, receiving-code-review}.

**Escenario A-6: allow_interactive_skill=True bypasses headless gate**

> **Given** Caller of `invoke_skill("receiving-code-review", ...,
> allow_interactive_skill=True)` con headless context.
> **When** `invoke_skill` invoked.
> **Then** No PreconditionError raised. Subprocess attempt proceeds
> as v1.0.1 baseline (operator-controlled override).

**Escenario A-7: brainstorming + writing-plans backward compat**

> **Given** Existing v1.0.1 wrappers `brainstorming(...)` +
> `writing_plans(...)` que pasan `allow_interactive_skill=True`
> internamente.
> **When** Wrappers invoked under headless context.
> **Then** No PreconditionError. Subprocess attempt proceeds
> (v1.0.1 behavior preserved).

### 4.2 Item B — 600s subprocess hang LOUD-FAST fix (coupled with A)

**Escenario B-1: PreconditionError message includes recovery options**

> **Given** Headless context + skill in incompatible set + no
> override.
> **When** `_build_headless_recovery_message("receiving-code-review")`
> invoked.
> **Then** Returned string contains:
> - "Skill `/receiving-code-review` cannot run via `claude -p`"
> - "SBTDD_HEADLESS=" + actual value
> - "stdin.isatty()=" + actual bool
> - Per-skill recovery: "Run `/receiving-code-review` manually" +
>   "fall back to manual `python skills/magi/scripts/run_magi.py`"
> - Generic recovery: "Set SBTDD_INTERACTIVE=1 if you ARE in
>   interactive context".

**Escenario B-2: per-skill recovery for brainstorming**

> **Given** `_build_headless_recovery_message("brainstorming")`.
> **When** Invoked.
> **Then** Returned string contains "Run `/brainstorming` manually
> in interactive Claude Code session, then use
> `/sbtdd spec --resume-from-magi`".

**Escenario B-3: 600s hang eliminated by construction**

> **Given** Headless context + `/receiving-code-review` invocation
> attempt.
> **When** `invoke_skill` called.
> **Then** `PreconditionError` raised WITHIN 1 second (NOT 600s).
> No subprocess process spawned (verifiable via no Popen call in
> test mock).

### 4.3 Item C — Parallel task dispatcher

**Escenario C-1: dag_parser parses Task blocks**

> **Given** Plan file con multiple `### Task N:` headers.
> **When** `dag_parser.parse_plan(plan_path)` invoked.
> **Then** Returned `TaskGraph` contains one `Task` per `### Task
> N:` block, indexed by task ID. Each Task has title + Files list
> + dependency markers extracted.

**Escenario C-2: dag_parser extracts addBlockedBy dependencies**

> **Given** Task block con `**addBlockedBy**: [Task 1, Task 3]` o
> equivalent.
> **When** parse_plan invoked.
> **Then** Resulting `TaskGraph.edges` mapping for that task
> includes "1" and "3" task IDs.

**Escenario C-3: dag_parser detects cycles**

> **Given** Plan file con cycle: Task 1 depends on Task 2, Task 2
> depends on Task 1.
> **When** parse_plan invoked.
> **Then** `ValidationError` raised with message identifying the
> cycle.

**Escenario C-4: antichain identification**

> **Given** TaskGraph: Task 1 → Task 2, Task 1 → Task 3, Task 4
> independent.
> **When** `graph.antichains()` invoked.
> **Then** Returns ordered list: first antichain {1, 4}; second
> antichain {2, 3}. Tasks 2 + 3 batched after Task 1 + 4 complete.

**Escenario C-5: file surface collision detection**

> **Given** Antichain {Task 2, Task 3} con Task 2 modifies
> `auto_cmd.py` y Task 3 also modifies `auto_cmd.py`.
> **When** `partition_by_collision({2, 3}, graph)` invoked.
> **Then** Returns 2 sub-batches: [{2}, {3}] (cannot run parallel
> due to file collision).

**Escenario C-6: file surface disjoint passthrough**

> **Given** Antichain {Task 2, Task 3} con disjoint Files lists.
> **When** `partition_by_collision({2, 3}, graph)` invoked.
> **Then** Returns single sub-batch: [{2, 3}] (parallel-safe).

**Escenario C-7: --parallel flag opt-in**

> **Given** `python skills/sbtdd/scripts/run_sbtdd.py auto --parallel`
> con plan having parallelizable tasks.
> **When** Subcommand invoked.
> **Then** Tasks dispatched in parallel-safe batches. Wall-clock
> reduced vs sequential. MAGI Loop 2 fires ONCE on cumulative diff.

**Escenario C-8: sequential default preserved**

> **Given** `python skills/sbtdd/scripts/run_sbtdd.py auto` (no
> `--parallel` flag) con same plan as C-7.
> **When** Subcommand invoked.
> **Then** Tasks dispatched sequentially exactly as v1.0.3
> behavior. Per-task MAGI Loop 2 (or end-of-cycle, whichever
> v1.0.3 specifies). Backward compat verified.

**Escenario C-9: TDD-Guard ON parallel mode warning**

> **Given** TDD-Guard hooks active in `.claude/settings.json` +
> `--parallel` flag.
> **When** Subcommand invoked.
> **Then** Warning emitted to stderr: "Parallel mode in same
> worktree with TDD-Guard ON may produce false bloqueos. Toggle
> off with `tdd-guard off` per spec sec.3 multi-agent rules, OR
> use `/using-git-worktrees` for per-subagent worktree."

### 4.4 Item D — Phase auto-advance methodology gap fix (doc-only)

**Escenario D-1: SKILL.md mandates close-phase per-phase**

> **Given** Updated `skills/sbtdd/SKILL.md` post-Track-Beta-close.
> **When** Grep for "close-phase per-phase" pattern OR equivalent
> mandate text.
> **Then** SKILL.md contains explicit instruction: "Subagents MUST
> invoke `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
> after each Red/Green/Refactor verify-clean. Manual `git commit`
> per phase BYPASSES the phase-advance + state-file update +
> verification gate".

**Escenario D-2: CLAUDE.local.md.template references close-phase per phase**

> **Given** Updated `templates/CLAUDE.local.md.template`.
> **When** Grep for close-phase mandate.
> **Then** Template contains the same per-phase close-phase
> mandate text + reference to v1.0.4 Item D rationale.

**Escenario D-3: writing-plans skill prompt extension produces close-phase steps**

> **Given** writing-plans skill prompt extension (or template
> fixture under `templates/`) for plan generation.
> **When** Grep for `close-phase` per Red/Green/Refactor step.
> **Then** Plan generation template/fixture includes per-phase
> step "close-phase Red" / "close-phase Green" / "close-phase
> Refactor" using the literal command
> `python skills/sbtdd/scripts/run_sbtdd.py close-phase` as
> opposed to raw `git commit`.

---

## 5. Subagent layout + execution timeline

### 5.1 Track Alpha (subagent #1, sequential A → B coupled)

**Owner**: code-architect or general-purpose subagent.
**Scope**: Items A+B coupled in `superpowers_dispatch.py` + tests.
**Wall-time estimado**: ~1 dia.

Sequential ordering:

1. **A** (~0.7 dia): real headless detection — `_is_headless_context`
   helper + extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + integrate
   into `invoke_skill` + tests.
2. **B** (~0.3 dia, coupled with A): recovery message helper +
   per-skill dictionary + integration tests + 600s hang elimination
   tests.

Sin dependencias inter-track durante implementation phase.

### 5.2 Track Beta (subagent #2, sequential C → D)

**Owner**: code-architect or general-purpose subagent.
**Scope**: Item C parallel dispatcher (new modules) + Item D
doc-only enforcement.
**Wall-time estimado**: ~2 dias.

Sequential ordering rationale:

1. **C** (~1.5 dia): parallel dispatcher = `dag_parser.py` (new) +
   `parallel_dispatcher.py` (new) + `auto_cmd.py` `--parallel`
   flag + tests. Bulk of cycle scope.
2. **D** (~0.5 dia): doc-only updates to SKILL.md +
   CLAUDE.local.md.template + writing-plans skill prompt extension
   + smoke test.

Sin dependencias inter-track.

### 5.3 Mid-cycle methodology (orchestrator)

**Owner**: orchestrator (single Claude Code session).
**Scope**: Activity E'-pre + Activity D' retry + Activity E'-post +
parallel dispatcher dogfood.
**Wall-time estimado**: ~1-1.5 dia total.

Triggered:

1. **Activity E'-pre** (~30-45 min): BEFORE Track Alpha + Beta
   dispatch. Exercise `--resume-from-magi` happy path on
   hand-crafted artifacts during plan-approval phase.
2. **Activity D' retry** (~30-45 min): AFTER Track-Alpha + Track-Beta
   close + AFTER Items A+B fix landed. Run `/sbtdd pre-merge`
   end-to-end with `SBTDD_INTERACTIVE=1`.
3. **Activity E'-post** (~15-30 min): AFTER Activity D'. Smoke test
   `--resume-from-magi` post-impl. Non-gating.
4. **Parallel dispatcher dogfood** (~15-30 min): AFTER Item C tests
   green. Use `--parallel` mode for v1.0.4 cycle's next batch
   (e.g., CHANGELOG + README + version bump).

### 5.4 True parallelism observado

Surfaces Track Alpha vs Track Beta:

| Surface | Alpha | Beta |
|---------|-------|------|
| `superpowers_dispatch.py` | yes (Items A+B modify) | — |
| `tests/test_superpowers_dispatch.py` | yes (extend) | — |
| `tests/test_invoke_skill_callsites_audit.py` | yes (extend) | — |
| `dag_parser.py` (new) | — | yes |
| `parallel_dispatcher.py` (new) | — | yes |
| `auto_cmd.py` | — | yes (--parallel flag) |
| `tests/test_dag_parser.py` (new) | — | yes |
| `tests/test_parallel_dispatcher.py` (new) | — | yes |
| `tests/test_auto_cmd.py` | — | yes (extend) |
| `skills/sbtdd/SKILL.md` | — | yes (Item D doc) |
| `templates/CLAUDE.local.md.template` | — | yes (Item D doc) |
| writing-plans extension | — | yes (Item D doc) |
| `tests/test_close_phase_subagent_pattern.py` (new) | — | yes (Item D smoke) |

**Cero overlap**. Tracks pueden run truly parallel sin merge
conflicts.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (CHANGELOG `[1.0.0]`, precedente
  cerrado v1.0.1+v1.0.2+v1.0.3 = 4-streak no-override). NO INV-0
  path.
- Bundle scope multi-pillar (4 plan tasks across 3 pillars) —
  esperamos converger en 1-2 iters.
- **Iter 2 CRITICAL trigger** (v1.0.3 spec sec.6.1, first empirical
  fire during v1.0.3): if Loop 2 iter 2 still surfaces ANY CRITICAL
  finding (post-iter-1-triage-fix), scope-trim immediately rather
  than burning iter 3. Pre-staged decision: Item D doc-only defer
  to v1.0.5 first; if needed, also Item C (parallel dispatcher)
  defer to v1.0.5; only Items A+B (Pillar A) son hard-LOCKED for
  v1.0.4 ship.
- Si llega a iter 3 sin convergencia (despite iter-2 trigger),
  default scope-trim ladder applies:
  1. Defer Item D doc-only to v1.0.5 (smallest, doc-only).
  2. Defer Item C parallel dispatcher to v1.0.5 (high-value but
     deferable; existing manual pattern continues).
  3. Items A+B son hard-LOCKED (cycle's primary CRITICAL — Finding
     A regression of v1.0.3 hang).

**Methodology decision**: Checkpoint 2 dispatch usa **Opcion A
manual `run_magi.py`** per hybrid methodology + v1.0.2+v1.0.3
precedent. Activity E'-pre exercises `--resume-from-magi` BEFORE
Track dispatch but does NOT replace manual run_magi for Checkpoint
2 itself.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- Bundle scope minimal — esperamos converger en 1 iter.

### 6.3 Loop 2 (`/magi:magi`) — Activity D' retry dogfood

- **Cap=5** per `auto_magi_max_iterations`.
- **Cross-check enabled**: Activity D' ENTREGA es running
  `/sbtdd pre-merge` post Items A+B fix con `SBTDD_INTERACTIVE=1`.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding fallback**: si Loop 2 iter 3 no converge clean,
  scope-trim per spec-base sec.6.1 ladder. Item D defer first;
  then Item C; Items A+B hard-LOCKED.
- **Manual fallback** (R7 mitigation): si `/sbtdd pre-merge` STILL
  hits failure mode after Items A+B fix (unexpected bug), escape
  via Ctrl+C + `python skills/magi/scripts/run_magi.py code-review
  <payload>` (precedente v1.0.0+v1.0.1+v1.0.2+v1.0.3).

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.4 own-cycle
(e.g., new regression), el operator MUST fall back a manual
`python skills/magi/scripts/run_magi.py` direct dispatch + manual
mini-cycle commits. Document en CHANGELOG `[1.0.4]` Process notes.

**Verbatim fallback command**:

```bash
mkdir -p .claude/magi-runs/v104-loop2-iter1
{
  cat .claude/magi-runs/v104-loop2-iter1-header.md
  echo "---"
  cat sbtdd/spec-behavior.md
  echo "---"
  cat planning/claude-plan-tdd.md
} > .claude/magi-runs/v104-loop2-iter1-payload.md
python skills/magi/scripts/run_magi.py code-review \
  .claude/magi-runs/v104-loop2-iter1-payload.md \
  --model opus --timeout 900 \
  --output-dir .claude/magi-runs/v104-loop2-iter1
```

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.3 → 1.0.4.

### 7.2 CHANGELOG `[1.0.4]` sections

- **Added** —
  Real headless detection helpers in `superpowers_dispatch.py`
  (`_is_headless_context`, `_build_headless_recovery_message`,
  `_PER_SKILL_RECOVERY` map; Items A+B);
  `dag_parser.py` (new module — Item C);
  `parallel_dispatcher.py` (new module — Item C);
  `--parallel` flag on `/sbtdd auto` (Item C);
  Per-phase close-phase mandate in SKILL.md +
  CLAUDE.local.md.template + writing-plans skill prompt extension
  (Item D doc-only);
  `tests/test_close_phase_subagent_pattern.py` (Item D smoke).
- **Changed** —
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` set extended to include
  `receiving-code-review` (Item A);
  `auto_cmd.py` accepts `--parallel` flag (Item C, default off
  preserves v1.0.3 sequential behavior).
- **Process notes** — Activity D' retry findings (cross-check
  meta-reviewer FIRST empirical fire on /sbtdd pre-merge end-to-end;
  iter count Loop 2; cross-check decision distribution; Items
  A+B fix validated empirically via Loop 1 fix-finding triage
  step completing without 600s hang); Activity E'-pre findings
  (`--resume-from-magi` happy path on hand-crafted artifacts;
  INV-37 tripwire behavior; wall-clock); Activity E'-post findings
  (R10 commit-conflict observability; R4 autoregen interaction
  observability — likely N/A until v1.0.5; non-gating); parallel
  dispatcher dogfood findings (wall-clock comparison vs sequential
  estimate; race conditions or state-file conflicts observed; DAG
  parser correctness); v1.0.3 LOCKED carry-forward closed.
- **Deferred (rolled to v1.0.5)** — v1.0.3 deferred Items C/D/E
  (drift detector line-anchored regex; spec-snapshot autoregen;
  close-task convention codification beyond v1.0.4 doc-only);
  audit GAPs L1.0.4-A through L1.0.4-D (Trigger criteria
  informational alignment; Carry-forward "Prior triage context"
  block emit path; Review summary artifact auto-emission;
  Per-project setup checklist template thinness).
- **Deferred (rolled to v1.0.5+)** — agreement_rate→keep_rate API
  rename; spec_lint R3 promote to error severity; per-module
  coverage raise to 85% baseline; pytest-cov dev dep registration;
  INV-31 default flip cycle; Group B options 1, 3, 4, 6, 7;
  Migration tool real test (Feature I primer migration v1->v2);
  AST-based dead-helper detector codification; W8 Windows
  file-system retry-loop; `_read_auto_run_audit` skeleton wiring;
  spec sec.7.1.3 G2 amendment; `magi_cross_check` default-flip a
  `true`.

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.4 docs section sobre real headless detection +
  parallel dispatcher `--parallel` flag + per-phase close-phase
  convention.
- **SKILL.md**: `### v1.0.4 notes` section documentando 4 plan
  tasks across 3 pillars + 4 methodology activities + close-phase
  per-phase mandate.
- **CLAUDE.md**: v1.0.4 release notes pointer.

---

## 8. Risk register v1.0.4

(Extends spec-base R1-R8 + R-NEW1-R-NEW3 added per design review.)

- **R1** (spec-base): Item A real headless detection may be too
  strict and reject legitimate `claude -p` uses where the
  orchestrator IS in interactive context but isatty() returns false
  (rare: piped script wrapping claude CLI). Mitigation:
  `SBTDD_INTERACTIVE=1` env var override documented + tested
  (escenario A-4).
- **R2** (spec-base): Item A breaking behavior for callers that
  ignored the v1.0.1 whitelist warning. Mitigation: backward compat
  preserved (override still works); audit existing callsites via
  test_invoke_skill_callsites_audit.py v1.0.2 meta-test.
- **R3** (spec-base): Item C parallel dispatcher DAG analysis may
  misclassify tasks as parallel-safe when they have implicit
  dependencies. Mitigation: file surface collision detection covers
  explicit `**Files:**` declarations; implicit dependencies
  surfaced via empirical dogfood (parallel dispatcher dogfood
  validates v1.0.4 own-cycle).
- **R4** (spec-base): Item C cumulative-diff Loop 2 may consume more
  MAGI iter budget if cumulative diff is large vs per-task.
  Mitigation: spec sec.6.1 iter-2 CRITICAL trigger pre-stage +
  scope-trim ladder fallback.
- **R5** (spec-base): Item D doc-only enforcement historically
  lower compliance per v1.0.3 evidence. Mitigation: 3-touchpoint
  enforcement (SKILL.md + CLAUDE.local.md.template + writing-plans
  extension) vs v1.0.2 single I5 process notes; smoke test
  asserts presence of mandate text in all three.
- **R6** (spec-base): Bundle scope multi-pillar (3 pillars + 4
  methodology activities) aumenta riesgo de Loop 2 non-convergence.
  Mitigation: G2 binding scope-trim ladder defer Item D first →
  Item C second; Items A+B hard-LOCKED.
- **R7** (spec-base): Items A+B fix incomplete — Activity D' retry
  could fail again. Mitigation: methodology activity is
  non-blocking for ship; document failures + defer to v1.0.5 retry;
  manual fallback via run_magi.py preserves ship viability.
- **R8** (spec-base): Item C parallel dispatcher own-cycle dogfood
  may surface edge cases not covered by tests. Mitigation: cycle
  uses sequential dispatch as fallback if parallel dogfood
  surfaces blocking issue; document as v1.0.5 refinement.
- **R-NEW1** (design review): Item A env-var detection may break
  legitimate test runs. Mitigation: pytest fixtures explicitly
  set `SBTDD_HEADLESS` / `SBTDD_INTERACTIVE` env vars when invoking
  wrapper functions; tests document the contract via escenarios
  A-2 + A-4.
- **R-NEW2** (design review): Item C parallel dispatcher
  chicken-and-egg dogfood — cycle uses dispatcher being
  implemented. Mitigation: Track Beta lands sequential `make verify`
  green BEFORE orchestrator opt-in to `--parallel` dogfood;
  failures self-attribute to Item C impl.
- **R-NEW3** (design review): Item A `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  set extension may surface MORE skills empirically incompatible
  (e.g., other interactive skills not yet observed). Mitigation:
  audit doc in Item A documents criteria + current set; v1.0.5+
  extends as empirically observed.

---

## 9. Acceptance criteria final v1.0.4

v1.0.4 ship-ready cuando:

### 9.1 Functional Items A-D + Activities D'-E'

- **F1**. F145-F150 (Item A): real headless detection (env var +
  isatty + override) + extended `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  set + module docstring criteria documented + backward compat
  preserved.
- **F2**. F151-F152 (Item B): PreconditionError messages + per-skill
  recovery dictionary + 600s hang elimination by construction.
- **F3**. F153-F157 (Item C): parallel dispatcher (DAG parser +
  antichain identification + file surface collision detection +
  cumulative-diff Loop 2 + sequential default preserved).
- **F4**. F158-F161 (Item D): doc-only per-phase close-phase
  mandate in SKILL.md + CLAUDE.local.md.template + writing-plans
  skill prompt extension + smoke test.
- **F5** (methodology): Activity D' retry empirical validation
  (cross-check + Loop 1 triage step pass).
- **F6** (methodology): Activity E'-pre empirical validation
  (`--resume-from-magi` happy path on plan-approval phase).
- **F7** (methodology): Activity E'-post empirical validation
  (R10 + R4 observability post-impl, non-gating).
- **F8** (methodology): parallel dispatcher dogfood
  (chicken-and-egg empirical signal post Track Beta close).

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 165s. Soft-target
  <= 155s.
- **NF-B**. Tests baseline 1105 + 1 skipped + ~35-50 nuevos =
  ~1140-1155 final.
- **NF-C**. Cross-platform (Windows + POSIX) — Item A headless
  detection validated on both via env var + isatty.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `superpowers_dispatch.py` (Items A+B); nuevos
  modulos (`dag_parser.py`, `parallel_dispatcher.py`); `auto_cmd.py`
  (Item C `--parallel` flag wiring); `skills/sbtdd/SKILL.md` +
  `templates/CLAUDE.local.md.template` (Item D doc).

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path. 4-cycle
  no-override streak preserved (becomes 5-cycle with v1.0.4 ship).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded. **`/sbtdd pre-merge`
  end-to-end completion** without subprocess hang (Items A+B
  validated empirically via Activity D' retry).
- **P3**. CHANGELOG `[1.0.4]` entry written con secciones Added /
  Changed / Process notes + Activity D' retry findings + Activity
  E'-pre + Activity E'-post findings + parallel dispatcher
  dogfood observations.
- **P4**. Version bump 1.0.3 -> 1.0.4 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.4` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion. **P6 IS POSSIBLE for the first
  time via subprocess** post Items A+B fix.
- **P7**. `/sbtdd spec --resume-from-magi` exercised end-to-end
  during plan-approval phase (Activity E'-pre).
- **P8**. `/sbtdd pre-merge` exercised end-to-end during pre-merge
  phase (Activity D' retry).
- **P9**. v1.0.4 own-cycle uses Item C parallel dispatcher during
  Track Beta own-cycle (parallel dispatcher dogfood).

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.4 ship + 4 plan tasks
  across 3 pillars + 4 methodology activities + dogfood
  observations).
- **D3**. Nuevos modulos + flags + env vars documentados:
  - `dag_parser.py` + `parallel_dispatcher.py` en README + SKILL.md.
  - `--parallel` flag en `auto_cmd` documented.
  - `SBTDD_HEADLESS` + `SBTDD_INTERACTIVE` env vars documented.
  - Per-phase close-phase mandate documented in plan template +
    SKILL.md + CLAUDE.local.md.template.

---

## 9.5 Inherited invariants from v0.4.x and v1.0.1+v1.0.2+v1.0.3 (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording (canonical
single-line text `[sbtdd magi] synthesizer failed; manual synthesis
recovery applied`) is preserved verbatim across spec / CHANGELOG /
impl per the cross-artifact alignment contract
(`tests/test_changelog.py`). v1.0.4 ships no behavioral change to
this path.

The INV-37 composite-signature output validation tripwire (v1.0.1
Item A0) is preserved verbatim — `_run_spec_flow` mtime + size +
sha256 check applies during v1.0.4 own-cycle if operator drives
`/sbtdd spec` instead of using `--resume-from-magi`. Items A+B
real headless detection runs in `superpowers_dispatch.invoke_skill`
BEFORE subprocess spawn; INV-37 tripwire path unchanged.

The Item C v1.0.2 `spec_lint` gate (R1-R5 rules with R3 warning
per Q3) is preserved unchanged. v1.0.4 Activity E'-pre +
Activity E'-post pre-flight spec_lint dry-run (W5 v1.0.1 fix)
catches self-inflicted R5/R1 violations before
`--resume-from-magi` invocation.

The Q4 v1.0.2 coverage threshold = `floor(baseline) - 2%` protocol
is preserved at 88% (measured baseline 90.12% in v1.0.2 ship).
v1.0.4 must not regress below 88%.

The v1.0.3 cross-check Windows long-filename fix (Item B
`@<filepath>` reference + project-relative temp dir) is preserved
unchanged. Activity D' retry exercises the path on Windows;
cross-check meta-reviewer should fire correctly post Items A+B fix.

---

## 10. Referencias

- Spec base v1.0.4: `sbtdd/spec-behavior-base.md`
  (uncommitted en branch `feature/v1.0.4-bundle`).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3
  frozen: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.3 ship record: tag `v1.0.3` (commit `39a9c18`); merge
  `0aeff7d` on `main`.
- v1.0.2 ship record: tag `v1.0.2` (commit `80731e6`); merge
  `3169767` on `main`.
- v1.0.1 ship record: tag `v1.0.1` (commit `8fc0db4` on `main`).
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.3 LOCKED carry-forward to v1.0.4: ver CHANGELOG `[1.0.3]`
  Process notes + Deferred (rolled to v1.0.4) section. CRITICAL
  unblocking item: real headless detection.
- v1.0.4 LOCKED memories:
  - `project_v104_subprocess_headless_detection.md` (CRITICAL).
  - `project_v104_parallel_task_dispatcher.md` (HIGH VALUE).
- v1.0.5 deferred backlog: audit GAPs L1.0.4-A through L1.0.4-D
  from v1.0.3 audit + Items C/D/E from v1.0.3 deferral. Bundle
  as v1.0.5 polish pillar per Balthasar v1.0.3 iter 3 INFO
  recommendation.
- Brainstorming refinement decisions (2026-05-07):
  - Q1 — 2-track parallel partition: Track Alpha = Items A+B
    coupled (`superpowers_dispatch.py` + tests); Track Beta =
    Items C+D (parallel dispatcher new modules + `auto_cmd.py`
    `--parallel` flag + Item D doc-only enforcement).
  - Q2 — Item C API surface: `--parallel` flag on existing
    `/sbtdd auto` subcommand. No new subcommand.
  - Q3 — Item D Option B mandate close-phase per Red/Green/
    Refactor commit via doc-only enforcement (3-touchpoint:
    SKILL.md + CLAUDE.local.md.template + writing-plans extension).
  - Q4 — Activity E' Option C: both pre-Track-close + post-
    Track-close exercises of `--resume-from-magi`. Both non-gating
    per hybrid methodology.
  - Q5 — auto-resolved by precedent: cap=3 HARD G1; iter-2 CRITICAL
    trigger preserved; G2 scope-trim ladder defer Item D first
    → Item C second; Items A+B hard-LOCKED.
- Branch: trabajo en `feature/v1.0.4-bundle` (branched off `main`
  HEAD `0aeff7d` = v1.0.3 merge commit).
