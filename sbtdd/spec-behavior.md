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
>
> **iter 1 triage applied 2026-05-07** (post Checkpoint 2 iter 1
> verdict GO_WITH_CAVEATS 3-0 con 2 CRITICAL + 14 WARNING + 5 INFO):
> Item A SIMPLIFICADO — drop `_is_headless_context()` helper +
> `SBTDD_HEADLESS`/`SBTDD_INTERACTIVE` env vars. Gate by
> `_SUBPROCESS_INCOMPATIBLE_SKILLS` membership + `allow_interactive_skill`
> override only. Activity D' retry methodology updated (drop env var
> step, validate gate-fires + manual recovery). Item D extended con
> soft-warning tripwire en `close_task_cmd._preflight`. dag_parser
> code-fence-aware regex + iterative cycle detection. Deterministic
> antichain partition + synthetic concurrent state-file write test.

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

### 2.1 Item A — Subprocess-incompatible gate (Pillar A PRIMARY CRITICAL, Track Alpha) — iter 1 triage SIMPLIFIED

**Track**: Alpha (subagent #1, sequential A → B coupled).

**Archivos**:
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
  (extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + module docstring
  + integrate gate into `invoke_skill`; iter 1 triage dropped
  `_is_headless_context()` helper + `SBTDD_HEADLESS`/
  `SBTDD_INTERACTIVE` env vars per caspar CRITICAL #1+#2).
- Extend: `tests/test_superpowers_dispatch.py` (escenarios A-1
  through A-5 + B-1 through B-3).
- Extend: `tests/test_invoke_skill_callsites_audit.py`
  (allow_interactive_skill whitelist audit; no env-var coverage
  needed post-simplification).

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

**iter 1 triage CRITICAL #1+#2 root-cause**:

caspar Checkpoint 2 iter 1 verified that the original env-var/
isatty heuristic does NOT fix the v1.0.3 bug: in operator's main
session (TTY=True), gate does NOT fire, subprocess spawns, 600s
hang persists. Additionally, Activity D' retry's proposed
`SBTDD_INTERACTIVE=1` step is paradoxical (bypasses the very gate
it claims to validate). Both CRITICALs share root cause = the
heuristic is the wrong abstraction for the v1.0.3 bug surface.

**Implementation (post iter 1 triage)**:

1. Extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + module docstring:
   ```python
   """Dispatcher for invoking superpowers skills via claude -p subprocess.

   ...

   Subprocess-incompatible skill audit history:
   - v1.0.1 (Finding A discovery): brainstorming, writing-plans.
     Manifestation: silent no-op (subprocess returns without
     producing skill output). Caught post-spawn via INV-37
     composite-signature check (v1.0.1 Item A0).
   - v1.0.4 (v1.0.3 Activity D' empirical hang during Loop 1
     fix-finding triage step): receiving-code-review.
     Manifestation: 600s subprocess hang waiting interactive input.
     Cannot be caught post-spawn (operator-blocking); requires
     pre-spawn gate.

   A skill is subprocess-incompatible iff it requires multi-turn
   interactive dialogue with the operator. Adding a new entry to
   the set without empirical evidence (subprocess hang or silent-
   no-op observed) is forbidden -- operators must run the skill
   manually in interactive session and document the failure mode
   in CHANGELOG before promoting.

   Gate semantics (v1.0.4 post iter 1 triage): subprocess spawn
   for incompatible skills is BLOCKED UNCONDITIONALLY unless caller
   passes `allow_interactive_skill=True`. The override is the
   explicit opt-in for known-safe wrappers that have arranged for
   subprocess success (silent-no-op tolerated by v1.0.1 wrappers
   via INV-37 post-detection; or operator-controlled interactive
   callsites). NO env-var/isatty heuristic -- caspar iter 1
   CRITICAL verified the heuristic does not fix the v1.0.3 bug
   in operator main sessions.
   """

   _SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset({
       "brainstorming",
       "writing-plans",
       "receiving-code-review",  # v1.0.4 added per v1.0.3 dogfood
   })
   ```

2. Modify `invoke_skill(skill, prompt, ..., allow_interactive_skill=False)`:
   ```python
   def invoke_skill(skill, prompt, ..., allow_interactive_skill=False):
       if (
           skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
           and not allow_interactive_skill
       ):
           raise PreconditionError(
               _build_recovery_message(skill)
           )
       # existing subprocess.run path unchanged
       ...
   ```

3. `allow_interactive_skill=True` kwarg preserved as override
   (backward compat for v1.0.1 wrappers `brainstorming(...)`,
   `writing_plans(...)` which rely on subprocess silent-no-op
   pattern + INV-37 post-detection). New wrapper
   `receiving_code_review(...)` does NOT pass override by default
   (no caller can legitimately allow 600s hang to spawn). Specific
   known-safe interactive callsites pass override explicitly with
   inline rationale comment + Task 4 (formerly Task 5) audit entry.

**Tests**: ~8-12 covering escenarios A-1 through A-5 (post triage:
A-2/A-3/A-4 env-var escenarios dropped; A-1 simplified to
membership + override semantics).

### 2.2 Item B — 600s subprocess hang LOUD-FAST fix (Pillar A PRIMARY CRITICAL, Track Alpha, coupled with A)

**Track**: Alpha (subagent #1, after Item A).

**Archivos**: same as Item A (coupled within `superpowers_dispatch.py`).

**Empirical context**: v1.0.3 Activity D' hang manifested as 600s
subprocess wait-then-fail. v1.0.1 only caught silent-no-op
manifestation (skill ran but produced no output) via post-spawn
heuristics; PRE-spawn hang (operator-blocking) was uncaught.

**Implementation (post iter 1 triage — simplified, no env-var formatting)**:

1. New helper `_build_recovery_message(skill: str) -> str`:
   ```python
   def _build_recovery_message(skill: str) -> str:
       per_skill = _PER_SKILL_RECOVERY.get(skill, _GENERIC_RECOVERY)
       return (
           f"Skill `/{skill}` cannot run via `claude -p` subprocess "
           f"(empirically incompatible: requires multi-turn interactive "
           f"dialogue or hangs > 600s). Recovery options:\n"
           f"{per_skill}\n"
           f"To override (only when caller has arranged interactive "
           f"completion path), pass `allow_interactive_skill=True` to "
           f"`invoke_skill(...)`."
       )
   ```

2. Per-skill recovery dictionary `_PER_SKILL_RECOVERY`:
   ```python
   _PER_SKILL_RECOVERY: Mapping[str, str] = MappingProxyType({
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
   })
   _GENERIC_RECOVERY = (
       "  1. Run the skill manually in interactive session,\n"
       "     then resume the SBTDD workflow."
   )
   ```

3. Coupled with Item A: `invoke_skill` raises `PreconditionError`
   BEFORE subprocess spawn when skill is in incompatible set + no
   override. Eliminates 600s hang by construction (gate fires
   regardless of caller's TTY state).

**Tests**: ~3-5 covering B-1 through B-3 (env-var formatting tests
B-1-env-var + B-1-isatty dropped; B-3 1-second timing test
preserved as PreconditionError-by-construction guarantee).

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

### 2.4 Item D — DEFERRED to v1.0.5 LOCKED (iter 2 scope-trim per spec sec.6.1 G2 ladder)

**Status**: DEFERRED ENTIRELY. No v1.0.4 implementation work.

**Rationale (iter 2 scope-trim Option D selected by user 2026-05-07)**:

iter 2 surfaced 3 CRITICAL findings — caspar's CRITICAL #3 ("§3
cross-module contract contradicts §2.4 + plan T9 — close_task_cmd IS
modified") + persistent 3-agent WARNING (melchior + balthasar +
caspar) about Item D 3-touchpoint doc-only enforcement INSUFFICIENCY
(third consecutive cycle of doc-only convention attempts: v1.0.2 Q2
Option B I5 process notes; v1.0.3 dogfood demonstrated divergence;
v1.0.4 attempted 3-touchpoint multiplication + tripwire fold-in).

Per spec sec.6.1 iter-2 CRITICAL trigger pre-stage: "scope-trim
ladder defers Item D doc-only first → defer Item C parallel
dispatcher second → Items A+B hard-LOCKED". Trigger fired; ladder
applied at first step (defer Item D).

**v1.0.5 LOCKED commitment**: Item D ships as Q3 OPTION A — code-side
enforcement via `close_task_cmd._preflight` modification. Architectural
preference 3-agent unanimous. NOT doc-only multiplication. Specifics
deferred to v1.0.5 brainstorming + plan.

**v1.0.4 surfaces NOT touched by Item D scope-trim**:
- `skills/sbtdd/SKILL.md` — unchanged in v1.0.4.
- `templates/CLAUDE.local.md.template` — unchanged in v1.0.4.
- writing-plans skill prompt extension — unchanged in v1.0.4.
- `skills/sbtdd/scripts/close_task_cmd.py` — unchanged in v1.0.4.
- `tests/test_close_phase_subagent_pattern.py` — NOT created in v1.0.4.
- `tests/test_close_task_cmd.py` — no D-4 tripwire test in v1.0.4.

The Q3 Option B 3-touchpoint mandate that v1.0.4 originally proposed
is REVERTED in scope. The Q2 v1.0.2 Option B `/sbtdd close-task`
automation mandate (single I5 touchpoint) remains in force unchanged.

### 2.5 Activity D' retry — Linux/POSIX dogfood completion (methodology, mid-cycle orchestrator)

**Track**: Methodology mid-cycle (orchestrator, no subagent).

**Archivos**: ninguno (config + run de comandos).

**Pasos del orchestrator post Track-Alpha + Track-Beta close (post iter 1 triage CRITICAL #2 fix)**:

1. Verify Items A+B fix landed in working tree
   (`superpowers_dispatch.py` includes extended
   `_SUBPROCESS_INCOMPATIBLE_SKILLS` set with `receiving-code-review`
   + simplified gate logic without env-var detection).
2. Run `/sbtdd pre-merge` end-to-end (NO env var setup needed —
   gate fires unconditionally for incompatible skills):
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
3. Verify `/receiving-code-review` subprocess invocation by
   `pre_merge_cmd` raises `PreconditionError` PRE-spawn (Items
   A+B fix validates here — gate fires by construction).
4. Operator manually runs `/receiving-code-review` skill via
   interactive Claude Code session per the recovery message
   guidance, applies findings + mini-cycle TDD fixes, then
   resumes `/sbtdd pre-merge` (ideally via `--resume` or
   re-invocation).
5. Verify Loop 1 fix-finding triage step completes WITHOUT 600s
   hang.
6. Capture Loop 2 cross-check artifacts:
   ```bash
   ls .claude/magi-cross-check/iter*-*.json
   ```
7. Document findings in CHANGELOG `[1.0.4]` Process notes:
   - PreconditionError raised PRE-spawn for `/receiving-code-review`
     (Items A+B fix validated by gate-fires + recovery path success).
   - Iter count Loop 2.
   - Cross-check decision distribution (post Item B Windows fix).
   - Recovery message observed (per-skill recovery dictionary
     produced operator-actionable guidance).

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

v1.0.4 NO introduce nuevos cross-cuts mas alla de (post iter 2
scope-trim Option D):

- **Item A+B coupled (post iter 1 triage SIMPLIFIED)**: extend
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + add
  `_build_recovery_message` + `_PER_SKILL_RECOVERY` mapping in
  `superpowers_dispatch.py`. Existing `invoke_skill` signature
  preserved (positional + kwargs); `allow_interactive_skill=False`
  default unchanged. NO `_is_headless_context()` helper. NO env-var
  detection. Gate is membership-based + override.
- **Item C**: NEW modules `dag_parser.py` + `parallel_dispatcher.py`
  with explicit public API. No mutation of existing helpers.
  `auto_cmd.py` adds `--parallel` flag; sequential default
  unchanged. Cycle detection iterative (Kahn's). Antichain partition
  deterministic (sorted task IDs).
- **Item D**: DEFERRED ENTIRELY to v1.0.5 LOCKED per iter 2 G2
  scope-trim Option D. NO v1.0.4 modifications to `close_task_cmd`,
  `SKILL.md`, `templates/CLAUDE.local.md.template`, or writing-plans
  extension. NO new tests `test_close_phase_subagent_pattern.py` or
  D-4 tripwire tests in `test_close_task_cmd.py`.

**Contratos preservados (no modificados) en v1.0.4**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` (existing
  en `errors.py`).
- `subprocess_utils.run_with_timeout` unchanged.
- `_compute_loop2_diff_with_meta` (v1.0.0) unchanged.
- `_loop2_with_cross_check` (v1.0.0) unchanged.
- `_run_magi_checkpoint2` (v1.0.0+v1.0.1+v1.0.2) unchanged.
- INV-37 composite-signature output validation tripwire (v1.0.1)
  unchanged.
- `close_phase_cmd` + `close_task_cmd` unchanged (Item D DEFERRED
  per iter 2 scope-trim; v1.0.5 will modify `close_task_cmd._preflight`
  per Option A code-side enforcement architecture).
- `state_file.SessionState` schema unchanged.
- `commits.validate_prefix` unchanged.

---

## 4. Escenarios BDD

Distribuidos por item (Tier 2 permissive regex per v1.0.1 Item A1).
Top-level numbering uses `## 4.` (R3 monotonic check satisfied).

### 4.1 Item A — Subprocess-incompatible gate (post iter 1 triage SIMPLIFIED)

**Escenario A-1: invoke_skill blocks receiving-code-review unconditionally without override**

> **Given** Caller of `invoke_skill("receiving-code-review", ...)`
> WITHOUT `allow_interactive_skill=True` (regardless of TTY state,
> env vars, or caller context).
> **When** `invoke_skill` invoked.
> **Then** `PreconditionError` raised BEFORE subprocess spawn.
> Error message contains "Skill `/receiving-code-review` cannot
> run via `claude -p` subprocess (empirically incompatible:
> requires multi-turn interactive dialogue or hangs > 600s)".

**Escenario A-2: receiving-code-review in incompatible set**

> **Given** Default `_SUBPROCESS_INCOMPATIBLE_SKILLS` frozenset.
> **When** `"receiving-code-review" in _SUBPROCESS_INCOMPATIBLE_SKILLS`.
> **Then** Returns True. Set membership extended from v1.0.1
> {brainstorming, writing-plans} to v1.0.4 {brainstorming,
> writing-plans, receiving-code-review}. Module docstring
> documents the audit history with v1.0.1 + v1.0.4 entries.

**Escenario A-3: allow_interactive_skill=True bypasses gate**

> **Given** Caller of `invoke_skill("receiving-code-review", ...,
> allow_interactive_skill=True)` (any caller context).
> **When** `invoke_skill` invoked.
> **Then** No PreconditionError raised. Subprocess attempt proceeds
> as v1.0.1 baseline (operator-controlled override). Override is
> the explicit opt-in for known-safe wrappers that have arranged
> for subprocess success.

**Escenario A-4: brainstorming + writing-plans backward compat**

> **Given** Existing v1.0.1 wrappers `brainstorming(...)` +
> `writing_plans(...)` que pasan `allow_interactive_skill=True`
> internamente.
> **When** Wrappers invoked.
> **Then** No PreconditionError. Subprocess attempt proceeds
> (v1.0.1 behavior preserved; silent-no-op manifestation tolerated
> via INV-37 post-detection).

**Escenario A-5: skills not in incompatible set pass through**

> **Given** Caller of `invoke_skill("systematic-debugging", ...)`
> (skill NOT in `_SUBPROCESS_INCOMPATIBLE_SKILLS`) without override.
> **When** `invoke_skill` invoked.
> **Then** No PreconditionError. Subprocess spawn proceeds normally
> (existing subprocess.run path unchanged for skills outside
> incompatible set).

### 4.2 Item B — 600s subprocess hang LOUD-FAST fix (coupled with A, post iter 1 triage SIMPLIFIED)

**Escenario B-1: PreconditionError message includes recovery options**

> **Given** Skill in incompatible set + no override.
> **When** `_build_recovery_message("receiving-code-review")`
> invoked.
> **Then** Returned string contains:
> - "Skill `/receiving-code-review` cannot run via `claude -p` subprocess"
> - "empirically incompatible: requires multi-turn interactive dialogue or hangs > 600s"
> - Per-skill recovery: "Run `/receiving-code-review` manually" +
>   "fall back to manual `python skills/magi/scripts/run_magi.py`" +
>   "spec sec.6.4"
> - Override hint: "pass `allow_interactive_skill=True` to
>   `invoke_skill(...)`" (only when caller has arranged interactive
>   completion path).

**Escenario B-2: per-skill recovery for brainstorming**

> **Given** `_build_recovery_message("brainstorming")`.
> **When** Invoked.
> **Then** Returned string contains "Run `/brainstorming` manually
> in interactive Claude Code session, then use
> `/sbtdd spec --resume-from-magi`".

**Escenario B-3: 600s hang eliminated by construction**

> **Given** Caller invokes `/receiving-code-review` via
> `invoke_skill` without override.
> **When** `invoke_skill` called.
> **Then** `PreconditionError` raised WITHIN 1 second (NOT 600s).
> No subprocess process spawned (verifiable via no Popen call in
> test mock). Holds regardless of caller's TTY state, env vars, or
> Claude Code session context (gate is membership-based, not
> heuristic-based).

### 4.3 Item C — Parallel task dispatcher

**Escenario C-1: dag_parser parses Task blocks (post iter 1 triage code-fence-aware)**

> **Given** Plan file con multiple `### Task N:` headers AND
> markdown code-fenced regions that contain example `### Task N:`
> patterns inside backtick blocks (e.g., writing-plans extension
> template).
> **When** `dag_parser.parse_plan(plan_path)` invoked.
> **Then** Returned `TaskGraph` contains one `Task` per real
> `### Task N:` block (column 0, outside code fences), indexed by
> task ID. Code-fenced example headers are SKIPPED (not added as
> phantom tasks). Each Task has title + Files list + dependency
> markers extracted. Implementation: `_split_task_blocks` strips
> fenced regions (delimited by triple backtick) before applying
> `_TASK_HEADER_RE`.

**Escenario C-2: dag_parser extracts addBlockedBy dependencies**

> **Given** Task block con `**addBlockedBy**: [Task 1, Task 3]` o
> equivalent.
> **When** parse_plan invoked.
> **Then** Resulting `TaskGraph.edges` mapping for that task
> includes "1" and "3" task IDs.

**Escenario C-3: dag_parser detects cycles (post iter 1 triage iterative)**

> **Given** Plan file con cycle: Task 1 depends on Task 2, Task 2
> depends on Task 1.
> **When** parse_plan invoked.
> **Then** `ValidationError` raised with message identifying the
> cycle. Implementation uses iterative Kahn's algorithm (or Tarjan
> with explicit stack) instead of recursive DFS — eliminates
> Python recursion limit failure mode for plans with > 1000
> dependency depth.

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

**Escenario C-10: deterministic antichain partition (iter 1 triage W7 fold-in)**

> **Given** Antichain {Task 2, Task 3, Task 4} con Task 2 modifies
> `auto_cmd.py`, Task 3 modifies `dag_parser.py`, Task 4 modifies
> `auto_cmd.py` (collides with Task 2).
> **When** `partition_by_collision` invoked twice with same input.
> **Then** Both invocations return IDENTICAL batch lists (not
> just same sizes). Implementation sorts task IDs ascending before
> greedy first-fit packing, eliminating Python set iteration order
> dependency. Test asserts exact batches `[{2, 3}, {4}]` (or
> deterministic equivalent).

**Escenario C-11: synthetic concurrent state-file write race (iter 1 triage W6 fold-in)**

> **Given** Two subagents simultaneously call `state_file.save()`
> against disjoint task IDs (e.g., subagent A advancing Task 5
> phase while subagent B advancing Task 6 phase).
> **When** Concurrent saves race against `.claude/session-state.json`.
> **Then** Final state file is consistent (one of {state-A,
> state-B}, never partial-merge nor corrupt JSON). Implementation
> uses explicit serialization: `parallel_dispatcher` SERIALIZES
> close-task invocations OR uses `fcntl.flock` (POSIX) /
> `msvcrt.locking` (Windows) wrapper around state-file
> read-modify-write. Test uses `multiprocessing.Process` with
> shared barrier to maximize race exposure; asserts final
> JSON parses correctly + matches one of the expected states.

### 4.4 Item D — DEFERRED to v1.0.5 LOCKED (iter 2 scope-trim Option D)

Escenarios D-1 through D-4 originally specified for v1.0.4 are
DEFERRED ENTIRELY to v1.0.5. No D-* escenarios apply to v1.0.4 ship
acceptance criteria.

v1.0.5 brainstorming will redesign Item D per Q3 OPTION A
(code-side enforcement via `close_task_cmd._preflight`) producing
new escenarios. The v1.0.4 D-1..D-4 escenarios below are preserved
as historical context only — DO NOT IMPLEMENT in v1.0.4.

<details>
<summary>v1.0.4-deferred D-* escenarios (historical reference only — DEFERRED)</summary>

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

**Escenario D-4: close-task soft-warning tripwire detects phase-advance bypass (iter 1 triage WARNING #5 fold-in)**

> **Given** Active task con `phase_started_at_commit=<sha>`. Commit
> chain since `<sha>` lacks at least one `test:` + one `feat:|fix:`
> + one `refactor:` prefix (i.e., subagent emitted raw `git commit`
> per phase instead of `close-phase`).
> **When** `close_task_cmd._preflight` invoked.
> **Then** Soft-warning emitted to stderr (does NOT block close-task):
> "[sbtdd close-task] WARNING: Phase advance gate appears bypassed
> (no test:/feat:|fix:/refactor: triplet in commit chain since
> {phase_started_at_commit}). Per v1.0.4 Item D mandate, subagents
> MUST invoke `close-phase` after each Red/Green/Refactor verify-
> clean. Continuing close-task; revisit close-phase per-phase
> convention." Close-task proceeds. Soft-warning converts
> unobservable doc drift into runtime signal per melchior+balthasar+
> caspar 3-agent agreement on Item D 3-touchpoint enforcement
> insufficiency. Two test cases: (a) bypass detected → WARNING
> emitted; (b) close-phase used per phase (commit chain has triplet)
> → no WARNING.

</details>

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

### 9.1 Functional Items A-C + Activities D'-E' (post iter 2 scope-trim Option D — Item D DEFERRED)

- **F1**. F145-F150 (Item A post iter 1+2 triage SIMPLIFIED):
  membership-based gate (no env-var/isatty heuristic) + extended
  `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + module docstring criteria
  documented + backward compat preserved (v1.0.1 wrappers via
  `allow_interactive_skill=True`).
- **F2**. F151-F152 (Item B post iter 1 triage SIMPLIFIED):
  `_build_recovery_message` + per-skill recovery dictionary + 600s
  hang elimination by construction (gate fires PRE-spawn regardless
  of caller TTY state).
- **F3**. F153-F157 (Item C post iter 1+2 triage): parallel dispatcher
  (DAG parser code-fence-aware + iterative cycle detection +
  antichain identification + file-surface collision detection
  deterministic via sorted IDs + cumulative-diff Loop 2 + sequential
  default preserved + concurrent state-file write race test).
- ~~**F4** (Item D)~~: **DEFERRED to v1.0.5 LOCKED** per iter 2
  scope-trim Option D. v1.0.5 brainstorming will redesign Item D
  per Q3 OPTION A code-side enforcement architecture. No v1.0.4
  ship acceptance criterion for Item D.
- **F5** (methodology): Activity D' retry empirical validation
  (gate fires PRE-spawn for `/receiving-code-review` invocation by
  pre_merge_cmd; manual recovery path completes Loop 1 without
  600s hang).
- **F6** (methodology): Activity E'-pre empirical validation
  (`--resume-from-magi` happy path on plan-approval phase).
- **F7** (methodology, BEST-EFFORT post iter 2 scope-trim): Activity
  E'-post (`--resume-from-magi` post-impl smoke; non-gating).
- **F8** (methodology, BEST-EFFORT post iter 2 scope-trim): parallel
  dispatcher dogfood (chicken-and-egg signal; non-gating).

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 165s. Soft-target
  <= 155s.
- **NF-B**. Tests baseline 1105 + 1 skipped + ~25-35 nuevos (post
  iter 2 scope-trim of Item D tripwire tests) = ~1130-1140 final.
- **NF-C**. Cross-platform (Windows + POSIX) — Item C concurrent
  state-file write test validated on both (multiprocessing.Process
  with shared barrier).
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados: `superpowers_dispatch.py` (Items A+B simplified);
  nuevos modulos (`dag_parser.py`, `parallel_dispatcher.py`);
  `auto_cmd.py` (Item C `--parallel` flag wiring). NO modificacion
  a `close_task_cmd.py`, `skills/sbtdd/SKILL.md`,
  `templates/CLAUDE.local.md.template`, ni writing-plans extension
  (Item D DEFERRED).

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
  Track Beta own-cycle (parallel dispatcher dogfood) — BEST-EFFORT,
  non-gating per iter 2 scope-trim demote.

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.4 ship — Items A+B+C
  shipped (2 pillars: A real headless gate + B parallel dispatcher);
  Item D DEFERRED to v1.0.5 LOCKED).
- **D3**. Nuevos modulos + flags documentados:
  - `dag_parser.py` + `parallel_dispatcher.py` en README + SKILL.md.
  - `--parallel` flag en `auto_cmd` documented.
  - NO env vars introduced (post iter 1 triage simplification dropped
    `SBTDD_HEADLESS`/`SBTDD_INTERACTIVE` env vars).
  - Item D DEFERRED to v1.0.5 — no plan template / SKILL.md /
    CLAUDE.local.md.template changes in v1.0.4.

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
