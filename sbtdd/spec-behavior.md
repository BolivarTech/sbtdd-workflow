# BDD overlay — sbtdd-workflow v1.0.5

> Generado 2026-05-08 a partir de `sbtdd/spec-behavior-base.md` v1.0.5.
> Hand-crafted en sesion interactiva (sesion Claude Code activa,
> brainstorming via Skill tool in-session, NO via `claude -p`
> subprocess) por consistencia con v1.0.1+v1.0.2+v1.0.3+v1.0.4
> precedent (v1.0.4 Items A+B prevent subprocess-incompatible skills
> from spawning, but interactive Skill invocation in-session is the
> canonical path).
>
> v1.0.5 ships los items LOCKED documentados en CHANGELOG.md
> `[Unreleased]` + memory `project_v105_parallel_correctness_locked.md`
> per user mandate 2026-05-08 ("documenta I-1, I-2 e I-3 para el
> proximo patch, deben quedar resueltos"). Foundation Items A+B+C
> shipped en v1.0.4; v1.0.5 cierra los operational hygiene gaps que
> bloquean production-grade `--parallel` end-to-end + ships Item D
> Q3 OPTION A (close_task_cmd._preflight code-side enforcement) +
> spec sec.8 stale risk-register sweep + plan archaeology trim
> methodology.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> +v1.0.1+v1.0.2+v1.0.3+v1.0.4 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex.
>
> **Iter 1 Checkpoint 2 triage applied 2026-05-08** (verdict
> GO_WITH_CAVEATS 3-0, 5 CRITICAL + 12 WARNING):
> - **CRITICAL #1+#3** (mel+cas): `_apply_flips_for_task_ids` rewritten
>   to derive flips from scratch-vs-main diff (no longer takes
>   `task_ids` parameter; flips fabricated on partial worker failure
>   no longer possible) — sec.2.2 step 3 updated.
> - **CRITICAL #2** (mel): `_flip_checkbox` regex anchored to next
>   `### Task` header (or end-of-file) so flips never cross task
>   boundaries — sec.2.2 step 2 updated.
> - **CRITICAL #4** (cas, architectural): "cero overlap" Q1 claim
>   was FALSE — Track Alpha T1 + Track Beta T3 both wired into
>   `_dispatch_tracks_concurrent`. Resolved by **consolidating ALL
>   post-batch hooks into Track Alpha T1**: Track Alpha owns audit
>   sidecar merge AND scratch plan merge wiring; Track Beta T3
>   provides `_merge_scratch_plans` helper in `close_task_cmd.py`
>   only — sec.2.1, sec.2.2, sec.5.1, sec.5.2, sec.5.4 updated.
> - **CRITICAL #5** (cas): `_preflight` commit-window scope changed
>   from `phase_started_at_commit` to "since last `chore: mark task`
>   commit subject" — handles task-N-close + task-(N+1)-open boundary
>   cleanly without phase-state coupling — sec.2.4 step 1 updated.
> - **WARNINGS** addressed: DRY atomic-write helper consolidated to
>   single shared `state_file._atomic_write_json`; duplicate
>   `test_d4` test name renamed to `test_d4_audit_breadcrumb`;
>   I-2 race regression test specified to use real
>   `multiprocessing.Process` workers (NOT thread-mocks) with
>   `Barrier`-synchronized RMW window; stale sidecar/scratch cleanup
>   added to dispatcher pre-flight (parent re-invocation reaps
>   orphans before new dispatch).
> - **REJECTED** (fact-grounded): Cas WARNING "Q5 strict no-INV-0
>   pressures false convergence" — Q5 explicitly includes
>   escalate-to-user-BEFORE-INV-0 per memory
>   `feedback_manual_synthesis_exceptional`; pressure for honest
>   scope-trim discipline, not false convergence.
> - **DEFERRED** (Bal INFO): D Q3-A timing risk acknowledged
>   (within-track sequential I-2 → D Q3-A already orders correctly).
>
> **Iter 2 Checkpoint 2 triage applied 2026-05-08** (verdict
> GO_WITH_CAVEATS 3-0 with 6 CRITICAL — **iter-2 CRITICAL trigger
> FIRES** per spec sec.6.1; pre-staged response invoked):
> - **Pillar C (Track Gamma C.2 plan archaeology trim methodology)
>   DEFERRED to v1.0.6** per pre-staged G2 ladder. All 3 agents
>   independently recommended this. Bal confidence drop 72→68%
>   signals bundle-width concern. Pillar A hard-LOCKED + Pillar B
>   (D Q3-A) preserved.
> - **Plan T3 Step 4 spec/plan drift** (iter-1 fix applied to spec
>   but not plan code block — operator editing miss): plan T3 Step
>   4 implementation code rewritten verbatim from spec sec.2.2
>   step 3+4 (anchored `_flip_checkbox` + `_apply_flips_from_diff`
>   + `_section_has_flipped` + `_iter_task_ids` helpers).
>   Re-introduces no iter-1 CRITICALs.
> - **Track Alpha T1 → Track Beta T3 ordering hardened**: dropped
>   "stub the import temporarily" fallback. Plan invariants block
>   adds explicit subagent-dispatch-ordering constraint: Track Beta
>   T3 MUST land before Track Alpha T1 Step 5 wiring. Orchestrator
>   enforces via subagent dispatch sequencing (Track Beta T3 → T4
>   first; Track Alpha T1 Step 5 last; T1 Steps 1-4 + T2 can run
>   in parallel with Track Beta).
> - **Plan T3 Step 1 Red phase** extended with explicit test
>   methods for escenarios I2-3b (partial worker failure
>   no-fabrication) + I2-5 (anchored regex boundary) per Cas
>   WARNING.
> - **Plan I2-4 race test** strengthened: explicit `for _ in
>   range(50):` repeat loop wrapping the multiprocessing
>   barrier-synchronized RMW + assert no flip lost across all 50
>   iterations.
> - **Plan T1 Step 8 + T3 Step 8** atomic-write DRY consolidation
>   made UNCONDITIONAL (no longer "Likely YAGNI; skip if minimal
>   duplication"): MUST extract shared `_atomic_write_json` to
>   `state_file.py` (existing v0.5.0 pattern); both modules import
>   from there.
> - **`_reap_orphans` race-safety**: added mtime/lock guard — only
>   reaps files older than dispatcher start time + 5min margin to
>   avoid clobbering concurrent SBTDD instances per Cas WARNING.
> - **`_last_chore_task_close_sha`**: added optional task-ID
>   verification (parse `chore: mark task <N> complete` subject;
>   if state file's prior task-ID doesn't match, surface as
>   diagnostic info in PreconditionError per Cas WARNING).

---

## 1. Resumen ejecutivo

**Objetivo v1.0.5**: production-grade `--parallel` correctness + Item
D code-side enforcement. Three focused pillars:

- **Pillar A PRIMARY (LOCKED CRITICAL)** — I-1 worker audit-trail
  clobber + I-2 plan checkbox lost-update race + I-3 worker CLI flag
  forwarding gap. Closes the 3 opt-in `--parallel` path correctness
  gaps documented in v1.0.4 ship CHANGELOG `[Unreleased]`.
- **Pillar B LOCKED (HIGH VALUE)** — Item D Q3 OPTION A code-side
  enforcement via `close_task_cmd._preflight` HARD-BLOCK. Replaces
  v1.0.4's attempted Q3 Option B 3-touchpoint doc-only that was
  scope-trimmed per iter-2 Option D.
- **Pillar C** — C.1 spec sec.8 stale risk-register sweep
  (APPLIED INLINE during brainstorming). **C.2 plan archaeology
  trim methodology DEFERRED to v1.0.6** per iter-2 CRITICAL trigger
  pre-staged response (2026-05-08).

Decisiones de brainstorming 2026-05-08 (Q1-Q5):

- **Q1 — Subagent partition**: Option C — 3-track parallel disjoint
  surfaces. **Iter-1 CRITICAL #4 refinement**: original "cero
  overlap" claim was function-level FALSE; resolved by consolidating
  ALL `_dispatch_tracks_concurrent` post-batch hook wiring into
  Track Alpha T1; Track Beta T3 provides pure helper functions in
  `close_task_cmd.py` only (no `auto_cmd.py` modifications). After
  fix, surfaces are file-level disjoint (sec.5.4 table).
  - Track Alpha (`auto_cmd.py` + tests): I-1 sidecar pattern + I-3
    flag forwarding + post-batch wiring for I-2 scratch-merge
    helpers
  - Track Beta (`close_task_cmd.py` + `run_sbtdd.py` argparse +
    tests): I-2 helpers (no auto_cmd.py wiring) + D Q3-A
    (within-track sequential: I-2 first, then D Q3-A)
  - Track Gamma (spec/SKILL.md/template/smoke): **DEFERRED to
    v1.0.6** per iter-2 CRITICAL trigger pre-staged response
    (2026-05-08). C.1 sweep already applied inline; C.2 methodology
    deferred.
  - Manual orchestrator dispatch via Agent tool fan-out (NOT `auto
    --parallel` self-dispatch — chicken-and-egg avoidance; v1.0.5
    uses external Agent tool dispatch, deferring `--parallel`
    self-dispatch dogfood to v1.0.6 post v1.0.5 production
    validation).

- **Q2 — I-1 architectural choice**: Option A — Per-worker sidecar
  files (`.claude/auto-run-track-{hash}.json`) merged by parent
  post-batch via os.replace. Robustness winner per per-worker
  isolation + atomic writes + cross-platform + forensics-friendly.

- **Q3 — I-2 architectural choice**: Option C — Per-worker scratch
  plan files merged by parent post-batch via flip-collect. Same
  isolation pattern as I-1; preserves per-task atomicity; trivially
  cross-platform; merge is simple flip-collect (no 3-way conflict
  due to disjoint task IDs).

- **Q4 — Item D Q3-A `--skip-preflight` scope**: Option A — flag-only
  emergency override + stderr audit breadcrumb. NO env var (v1.0.4
  Items A+B iter-1 lesson: env-var heuristics led to wrong
  abstractions). Explicit + ephemeral + audit-loggable.

- **Q5 — MAGI Checkpoint 2 budget + INV-0 stance**: Option A — strict
  no-INV-0 (re-establish pre-merge Loop 2 streak from 1 cycle
  post-v1.0.4 break). cap=3 HARD G1 Checkpoint 2 (6-cycle no-override
  streak goal). Pre-merge Loop 2 cap=5 with bias toward G2 scope-trim
  ladder over INV-0. If Loop 2 doesn't converge cleanly: escalate to
  user BEFORE applying INV-0.

**Hybrid methodology continued**: Opcion A manual `run_magi.py` for
Checkpoint 2 dispatch per v1.0.2+v1.0.3+v1.0.4 precedent (v1.0.5
own-cycle brainstorming + writing-plans NOT via subprocess; chicken-
and-egg now resolved per v1.0.4 Items A+B ship but precedent
preserved).

**Criterio de exito v1.0.5**:

- Tests baseline 1226 + 1 skipped preservados + ~25-40 nuevos =
  ~1250-1265 final.
- `make verify` runtime <= 200s soft / 220s hard (acknowledges v1.0.4
  baseline 195s + new tests; v1.0.6 polish may reduce).
- Coverage threshold mantenido en 88%.
- **Production-grade `--parallel` integration test acceptance** per
  CHANGELOG `[Unreleased]`: synthetic 2-track plan with 4 disjoint
  tasks asserting ALL 3 gaps closed (I-1 audit-trail integrity +
  I-2 all checkbox flips visible + I-3 worker flag forwarding).
- **Item D Q3-A empirical validation**: intentional-bypass test cases
  verify hard-block fires; canonical close-phase test cases verify
  normal flow.
- **G1 binding respetado**: cap=3 HARD para Checkpoint 2; sin INV-0.
  6-cycle Checkpoint 2 no-override streak preserved.
- **Pre-merge Loop 2 streak re-establish**: clean GO_WITH_CAVEATS
  full no-degraded WITHOUT INV-0 override.

---

## 2. Items LOCKED

### 2.1 Item I-1 — Worker audit-trail clobber via per-worker sidecar pattern (Pillar A PRIMARY CRITICAL, Track Alpha)

**Track**: Alpha (with I-3, both in `auto_cmd.py`).

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (worker mode short-circuit
  + parent post-batch merge helper).
- Extend: `tests/test_auto_cmd.py` (sidecar pattern + merge tests +
  INV-26 integration test).

**Empirical context (v1.0.4 ship)**:

`auto_cmd._dispatch_tracks_concurrent` spawns N subprocess workers;
each worker re-enters `auto_cmd.main()` with `--task-ids` filter +
`--no-recursive`. Worker mode currently writes to
`.claude/auto-run.json` clobbering parent's record. Post-batch,
parent reloads state but parent's auto-run.json is either empty
(clobbered last) or contains only one worker's record. INV-26
(audit-trail integrity) violated.

**Implementation (Q2 = Option A per-worker sidecar)**:

1. New helper `_audit_sidecar_path(task_ids: tuple[str, ...]) -> Path`:
   ```python
   def _audit_sidecar_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
       """Return per-worker audit sidecar path.

       Args:
           task_ids: Sorted tuple of task IDs assigned to this worker.
           project_root: Project root path.

       Returns:
           Path to sidecar file (deterministic name per task-IDs hash).
       """
       import hashlib
       digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
       return project_root / ".claude" / f"auto-run-track-{digest}.json"
   ```

2. Worker mode `_write_audit` redirect:
   ```python
   def _write_audit(audit: dict, project_root: Path, ns: argparse.Namespace) -> None:
       """Write audit record. v1.0.5 Item I-1: workers redirect to sidecar."""
       if ns.no_recursive and ns.task_ids:
           # Worker mode: write to per-worker sidecar
           task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
           audit_path = _audit_sidecar_path(task_ids_tuple, project_root)
       else:
           # Orchestrator mode: write to canonical audit-run.json
           audit_path = project_root / ".claude" / "auto-run.json"
       audit_path.parent.mkdir(parents=True, exist_ok=True)
       _atomic_write_json(audit_path, audit)  # write-temp + os.replace
   ```

3. New helper `_merge_audit_sidecars(tracks, project_root)`:
   ```python
   def _merge_audit_sidecars(
       tracks: list[list[str]], project_root: Path
   ) -> dict:
       """Parent post-batch: merge per-worker sidecars into canonical audit.

       Args:
           tracks: List of dispatched track task-ID lists.
           project_root: Project root.

       Returns:
           Merged audit dict (parent's pre-dispatch record + per-worker
           sidecars + per-worker exit codes / completion timestamps).
       """
       canonical = _read_audit(project_root)  # parent's pre-dispatch record
       per_worker: list[dict] = []
       for task_ids in tracks:
           sidecar_path = _audit_sidecar_path(tuple(sorted(task_ids)), project_root)
           if sidecar_path.exists():
               sidecar_data = _read_json(sidecar_path)
               per_worker.append(sidecar_data)
               # Cleanup: remove sidecar after successful merge
               sidecar_path.unlink(missing_ok=True)
           else:
               # Worker didn't write sidecar (early kill / crash before write)
               per_worker.append({
                   "task_ids": task_ids,
                   "status": "no_audit_data",
                   "note": "Worker terminated before sidecar write",
               })
       canonical["per_worker"] = per_worker
       canonical["aggregate_task_count"] = sum(len(tids) for tids in tracks)
       return canonical
   ```

4. `_dispatch_tracks_concurrent` post-batch (Track Alpha T1 owns
   ALL post-batch hooks per iter-1 CRITICAL #4 architectural fix):
   ```python
   def _dispatch_tracks_concurrent(tracks, project_root, ns) -> None:
       # ... pre-flight: reap stale sidecars/scratches from prior
       #     crashed run (iter-1 WARNING fix; sec.2.2 step 4) ...
       _reap_orphans(project_root)

       # ... existing dispatch logic (Popen workers + wait) ...

       # After all workers complete: Track Alpha T1 invokes BOTH
       # post-batch merges (audit sidecar via I-1 + plan scratch via
       # I-2). Track Beta T3 provides _merge_scratch_plans helper
       # only; wiring lives here in auto_cmd.py.
       merged_audit = _merge_audit_sidecars(tracks, project_root)
       _atomic_write_json(
           project_root / ".claude" / "auto-run.json", merged_audit
       )
       # I-2 plan scratch flip-merge (helper imported from
       # close_task_cmd; defined in Track Beta T3, wired here):
       from close_task_cmd import _merge_scratch_plans
       _merge_scratch_plans(tracks, project_root)
   ```

   **Architectural note (CRITICAL #4 fix)**: Q1 Option C "cero
   overlap" original claim that Track Alpha + Track Beta surfaces
   were 100% disjoint was FALSE — both tracks needed to wire merge
   helpers into `_dispatch_tracks_concurrent`. Resolution:
   **consolidate ALL `_dispatch_tracks_concurrent` post-batch hook
   wiring into Track Alpha T1**. Track Beta T3 provides the
   `_merge_scratch_plans` helper as a pure function in
   `close_task_cmd.py` (importable, no auto_cmd.py modifications).
   Track Alpha T1 imports + calls it post-merge-audit. Track surfaces
   become truly disjoint at the file level (Track Alpha touches only
   `auto_cmd.py`; Track Beta touches only `close_task_cmd.py` +
   `run_sbtdd.py` argparse). See sec.5.4 surfaces table.

**Tests**: ~6-10 covering escenarios I1-1 through I1-5 + reaper
escenario I1-6 (orphan sidecar from prior crash detected + cleaned
pre-dispatch).

### 2.2 Item I-2 — Plan checkbox lost-update race via per-worker scratch + flip-merge (Pillar A PRIMARY CRITICAL, Track Beta)

**Track**: Beta (with D Q3-A, both in `close_task_cmd.py`).

**Archivos**:
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (`mark_and_advance`
  worker-mode redirect + parent post-batch merge helper).
- Extend: `tests/test_close_task_cmd.py` (real `multiprocessing.Process`
  race regression test).

**Empirical context (v1.0.4 design gap)**:

`close_task_cmd.mark_and_advance` reads plan-tdd.md, modifies (flip
`[ ]` to `[x]` for current task), writes back via plain file write.
No cross-process lock. Two concurrent workers calling
`mark_and_advance` for disjoint task IDs can race: worker A reads,
worker B reads, both modify, A writes (flip 1), B writes (flip 2) —
A's flip silently lost. v1.0.4 sequential default unaffected
(single writer); v1.0.4 `--parallel` opt-in path susceptible.

**Implementation (Q3 = Option C per-worker scratch + flip-merge)**:

1. New helper `_scratch_plan_path(task_ids, project_root)`:
   ```python
   def _scratch_plan_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
       """Per-worker scratch plan path."""
       import hashlib
       digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
       return project_root / ".claude" / f"plan-scratch-{digest}.md"
   ```

2. Worker mode `mark_and_advance` redirect:
   ```python
   def mark_and_advance(state: dict, project_root: Path, ns: argparse.Namespace = None) -> None:
       """Flip current task checkbox + advance state.

       v1.0.5 Item I-2: in worker mode (--no-recursive + --task-ids),
       writes flip to per-worker scratch plan instead of main plan.
       Parent post-batch merges all scratch plans into main.
       """
       if ns and ns.no_recursive and ns.task_ids:
           # Worker mode: write flip to scratch (parent merges later)
           task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
           scratch_path = _scratch_plan_path(task_ids_tuple, project_root)
           if not scratch_path.exists():
               # First flip in this worker: copy from main plan
               import shutil
               shutil.copy2(project_root / "planning" / "claude-plan-tdd.md", scratch_path)
           plan_text = scratch_path.read_text(encoding="utf-8")
           flipped = _flip_checkbox(plan_text, state["current_task_id"])
           _atomic_write(scratch_path, flipped)
       else:
           # Orchestrator/sequential mode: write directly to main plan
           plan_path = project_root / "planning" / "claude-plan-tdd.md"
           plan_text = plan_path.read_text(encoding="utf-8")
           flipped = _flip_checkbox(plan_text, state["current_task_id"])
           _atomic_write(plan_path, flipped)
       # ... existing state file advance ...
   ```

3. **(iter-1 CRITICAL #1+#3 fix)** Helper `_flip_checkbox(plan_text,
   task_id)` MUST anchor to next `### Task` header so flips never
   cross task-section boundaries (CRITICAL #2 fix):

   ```python
   _TASK_HEADER_RE = re.compile(r"^### Task ", re.MULTILINE)

   def _flip_checkbox(plan_text: str, task_id: str) -> str:
       """Flip [ ] → [x] for the given task_id.

       v1.0.5 iter-1 CRITICAL #2 fix: regex anchored to current
       task's section boundaries. Search window = `### Task {task_id}`
       header to next `### Task ` header (or EOF). Prevents the
       previous regex `(### Task {tid}.*?)(- \\[ \\])` with
       `re.DOTALL` from matching a `[ ]` checkbox belonging to a
       LATER task when the current task has no `[ ]` of its own.
       """
       header_re = re.compile(rf"^### Task {re.escape(task_id)}\b", re.MULTILINE)
       header_match = header_re.search(plan_text)
       if header_match is None:
           raise ValueError(f"Task {task_id} not found in plan")
       section_start = header_match.end()
       next_header = _TASK_HEADER_RE.search(plan_text, section_start)
       section_end = next_header.start() if next_header else len(plan_text)
       section = plan_text[section_start:section_end]
       flipped_section = section.replace("- [ ]", "- [x]", 1)
       if flipped_section == section:
           return plan_text  # idempotent: already flipped or no checkbox
       return plan_text[:section_start] + flipped_section + plan_text[section_end:]
   ```

4. **(iter-1 CRITICAL #1+#3 fix)** `_merge_scratch_plans` MUST derive
   flips from scratch-vs-main diff, NOT from worker's task_ids
   parameter. Previous design fabricated flips on partial worker
   failure (worker assigned T3 but crashed before flipping → parent
   would still flip T3 in main). Resolution: only flip in main when
   scratch ACTUALLY contains the flip:

   ```python
   def _merge_scratch_plans(tracks: list[list[str]], project_root: Path) -> None:
       """Parent post-batch: merge per-worker scratch plans into main.

       v1.0.5 iter-1 CRITICAL #1+#3 fix: flips derived from
       scratch-vs-main diff, NOT from `task_ids` parameter. If a
       worker crashed before flipping its task, scratch will lack
       the flip and main is left unchanged for that task — no
       fabrication of false-positive checkbox state.

       Each worker's scratch contains main plan + flips for the
       subset of its task IDs it ACTUALLY processed. Workers have
       disjoint task IDs (per partition_by_tracks invariant).
       Therefore merge = collect flips from each scratch by direct
       diff + apply to main.
       """
       main_path = project_root / "planning" / "claude-plan-tdd.md"
       main_text = main_path.read_text(encoding="utf-8")
       for task_ids in tracks:
           scratch_path = _scratch_plan_path(tuple(sorted(task_ids)), project_root)
           if not scratch_path.exists():
               continue  # worker didn't write scratch (early failure)
           scratch_text = scratch_path.read_text(encoding="utf-8")
           main_text = _apply_flips_from_diff(main_text, scratch_text)
           scratch_path.unlink(missing_ok=True)
       _atomic_write_json_fallback_text(main_path, main_text)


   def _apply_flips_from_diff(main_text: str, scratch_text: str) -> str:
       """Apply only the [ ]→[x] transitions present in scratch
       relative to main. Iterates per-task-section using
       `_TASK_HEADER_RE` to walk both texts in lockstep; flips a
       main checkbox only when the same task section in scratch
       has the [x] state.

       v1.0.5 iter-1 CRITICAL #1+#3 fix: replaces the prior
       `_apply_flips_for_task_ids(main, scratch, task_ids)` design
       which ignored `scratch_text` and unconditionally flipped
       every task_id in main, fabricating flips when workers
       crashed before scratch-write.
       """
       # Walk both texts task-section by task-section. For each
       # task whose scratch section contains "- [x]" but main
       # section contains "- [ ]", apply the flip in main.
       result = main_text
       for task_id in _iter_task_ids(scratch_text):
           if _section_has_flipped(scratch_text, task_id) and \
              not _section_has_flipped(result, task_id):
               result = _flip_checkbox(result, task_id)
       return result


   def _section_has_flipped(plan_text: str, task_id: str) -> bool:
       """True iff task section contains '- [x]' (uses same anchored
       window as `_flip_checkbox`)."""
       # ... bounded section extraction identical to _flip_checkbox ...
       # ... return "- [x]" in section ...
   ```

5. `_dispatch_tracks_concurrent` post-batch invocation **lives in
   Track Alpha T1** per iter-1 CRITICAL #4 architectural fix (see
   sec.2.1 step 4). Track Beta T3 provides the helper functions
   (`_scratch_plan_path`, `_merge_scratch_plans`,
   `_apply_flips_from_diff`, `_section_has_flipped`,
   `_iter_task_ids`, anchored `_flip_checkbox`) in
   `close_task_cmd.py`; Track Beta does NOT modify `auto_cmd.py`.

6. **(iter-1 WARNING fix)** `_reap_orphans(project_root)` cleans
   stale `.claude/auto-run-track-*.json` and
   `.claude/plan-scratch-*.md` from prior crashed run before new
   dispatch. Implemented in `auto_cmd.py` (Track Alpha T1 territory),
   invoked at top of `_dispatch_tracks_concurrent`.

**Tests**: ~5-8 covering escenarios I2-1 through I2-4 incl. real
`multiprocessing.Process` + `multiprocessing.get_context("spawn")` +
Barrier race regression test.

### 2.3 Item I-3 — Worker CLI flag forwarding (Pillar A PRIMARY CRITICAL, Track Alpha)

**Track**: Alpha (with I-1).

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
  (`_dispatch_tracks_concurrent` worker invocation builder).
- Extend: `tests/test_auto_cmd.py` (forwarding contract test).

**Empirical context (v1.0.4 design gap)**:

`_dispatch_tracks_concurrent` builds worker argv as
`[python, run_sbtdd.py, auto, --task-ids, T1,T3, --no-recursive]`.
Operator flags from parent's argv NOT forwarded:
- `--plugins-root <path>`
- `--magi-max-iterations <N>`
- `--magi-threshold <verdict>`
- `--verification-retries <N>`
- `--model-override <model>`

Workers run with DEFAULT config regardless of operator flags.

**Implementation**:

1. New helper `_FORWARDABLE_FLAGS: Mapping[str, str] = MappingProxyType(...)`:
   ```python
   _FORWARDABLE_FLAGS: Mapping[str, str] = MappingProxyType({
       # argparse-namespace-attr → CLI-flag-name
       "plugins_root": "--plugins-root",
       "magi_max_iterations": "--magi-max-iterations",
       "magi_threshold": "--magi-threshold",
       "verification_retries": "--verification-retries",
       "model_override": "--model-override",
   })
   ```

2. New helper `_build_worker_argv(task_ids, ns) -> list[str]`:
   ```python
   def _build_worker_argv(task_ids: list[str], ns: argparse.Namespace) -> list[str]:
       """Build subprocess argv for a worker, forwarding parent's flags.

       v1.0.5 Item I-3: forwards _FORWARDABLE_FLAGS values from parent's
       argparse namespace. Documented forwardable list:
       --plugins-root, --magi-max-iterations, --magi-threshold,
       --verification-retries, --model-override.
       """
       argv = [
           sys.executable, str(_run_sbtdd_path()),
           "auto",
           "--task-ids", ",".join(task_ids),
           "--no-recursive",
       ]
       for ns_attr, cli_flag in _FORWARDABLE_FLAGS.items():
           value = getattr(ns, ns_attr, None)
           if value is not None:
               argv.extend([cli_flag, str(value)])
       return argv
   ```

3. `_dispatch_tracks_concurrent` uses `_build_worker_argv(task_ids, ns)`
   for each Popen invocation.

**Tests**: ~4-6 covering escenarios I3-1 through I3-3 (forwarding
contract per flag + mock subprocess.Popen + assert args).

### 2.4 Item D Q3 OPTION A — close_task_cmd._preflight code-side enforcement (Pillar B HIGH VALUE, Track Beta)

**Track**: Beta (after I-2; both in `close_task_cmd.py`).

**Archivos**:
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (`_preflight`
  extension).
- Modify: `skills/sbtdd/scripts/run_sbtdd.py` (argparse for
  `--skip-preflight` close-task subparser flag).
- Extend: `tests/test_close_task_cmd.py` (preflight enforcement +
  override behavior + audit breadcrumb).

**Empirical context (v1.0.4 iter-2 scope-trim Option D rationale)**:

v1.0.4 attempted Q3 Option B (3-touchpoint doc-only enforcement:
SKILL.md + CLAUDE.local.md.template + writing-plans extension +
soft-warning tripwire). Loop 2 iter 1 surfaced 3-agent unanimous
WARNING that doc-only fails (v1.0.2 single touchpoint failed; v1.0.3
dogfood divergence; v1.0.4 multiplication doesn't address
compliance). User selected Option D scope-trim per spec sec.6.1 G2
ladder; Item D entirely DEFERRED to v1.0.5 LOCKED with Q3 OPTION A
(code-side enforcement) commitment.

**Implementation (Q4 = Option A flag-only override)**:

1. Extend `close_task_cmd._preflight`:
   ```python
   def _preflight(state: dict, project_root: Path | None = None,
                  skip_preflight: bool = False) -> None:
       """v1.0.5 Item D Q3 OPTION A: hard-block when phase advance gate bypassed.

       Detects when commit chain since `phase_started_at_commit` lacks
       the canonical TDD triplet (test:/feat:|fix:/refactor:). Raises
       `PreconditionError` with operator-actionable guidance. Operator
       emergency override via `--skip-preflight` flag (audit-logged).

       Args:
           state: SessionState dict.
           project_root: Project root.
           skip_preflight: Operator emergency override (--skip-preflight flag).
       """
       # ... existing checks ...

       if skip_preflight:
           sys.stderr.write(
               f"[sbtdd close-task] WARNING: --skip-preflight active; "
               f"phase advance gate enforcement BYPASSED for "
               f"task_id={state.get('current_task_id')} since SHA "
               f"{state.get('phase_started_at_commit')}. Audit-logged.\n"
           )
           return

       # v1.0.5 iter-1 CRITICAL #5 fix: commit-window scope changed
       # from `phase_started_at_commit` to "since last `chore: mark
       # task` commit subject". Rationale (cas iter-1 CRITICAL #5):
       # `phase_started_at_commit` advances on every phase close
       # within a task, so when `_preflight` runs at task-close time
       # it sees only the LAST phase's commits — never the full Red
       # + Green + Refactor triplet. Boundary "since last chore:
       # mark task" reliably brackets the entire current task's
       # phase-close commits without phase-state coupling.
       last_chore_sha = _last_chore_task_close_sha(project_root)
       # last_chore_sha == None for the first task in the plan;
       # boundary becomes branch root in that case.
       subjects = _git_log_between(
           last_chore_sha, project_root=project_root,
       )
       has_test = any(s.startswith("test:") for s in subjects)
       has_green = any(s.startswith(("feat:", "fix:")) for s in subjects)
       has_refactor = any(s.startswith("refactor:") for s in subjects)
       if not (has_test and has_green and has_refactor):
           raise PreconditionError(
               f"Phase advance gate bypassed: commit chain since "
               f"{'last chore commit ' + last_chore_sha if last_chore_sha else 'branch root'} "
               f"lacks test:/feat:|fix:/refactor: triplet. "
               f"Per SBTDD INV-1 + INV-5..7, each task close requires "
               f"close-phase invocation per Red/Green/Refactor phase. "
               f"Recovery: invoke `python skills/sbtdd/scripts/run_sbtdd.py "
               f"close-phase` once per pending phase OR pass "
               f"--skip-preflight if emergency operator override is "
               f"appropriate (audit-logged via stderr breadcrumb)."
           )

   def _last_chore_task_close_sha(project_root: Path | None) -> str | None:
       """Return SHA of most recent commit with subject matching
       `chore: mark task <N> complete`, or None if no such commit
       exists on current branch.

       v1.0.5 iter-1 CRITICAL #5: this is the canonical "previous
       task close" boundary used by `_preflight` triplet check.
       Rebase/squash limitation acknowledged: if operator squashed
       prior task-close commits, this returns the most recent
       surviving `chore:` subject; risk: false-positive triplet
       detection if squash produced a hybrid subject. Mitigated
       by `--skip-preflight` flag for emergency operator override.
       """
       # `git log --pretty=%H%x09%s` filtered for "chore: mark task"
       # subject prefix; returns first SHA or None.
       ...
   ```

2. Argparse `close-task` subparser:
   ```python
   close_task_p.add_argument(
       "--skip-preflight",
       action="store_true",
       default=False,
       help="v1.0.5 Item D Q3-A emergency override: bypass phase advance "
            "gate enforcement. Audit-logged via stderr breadcrumb.",
   )
   ```

3. `close_task_cmd.cmd` reads `ns.skip_preflight` and passes to
   `_preflight(state, project_root, skip_preflight=ns.skip_preflight)`.

**Tests**: ~6-10 covering escenarios D-1 through D-4 (preflight
enforcement + override + audit breadcrumb + backward-compat).

### 2.5 Item C.1 — Spec sec.8 stale risk-register sweep (Pillar C METHODOLOGY, Track Gamma) — APPLIED INLINE

**Track**: Gamma (with C.2).

**Status**: APPLIED INLINE in this very document. The risk register
in spec sec.8 below has been clean-swept of stale references to
eliminated v1.0.4 mechanisms (SBTDD_INTERACTIVE env var, Item D
3-touchpoint enforcement, etc.). No strikethrough carry-forward;
risk register reflects current v1.0.5 architectural state cleanly.

### 2.6 Item C.2 — Plan archaeology trim methodology (Pillar C METHODOLOGY, Track Gamma) — DEFERRED to v1.0.6

**Status**: **DEFERRED to v1.0.6** per iter-2 CRITICAL trigger
pre-staged response (spec sec.6.1 G2 ladder). Iter-2 surfaced 6
CRITICAL findings; all 3 agents recommended deferral; user
authorized 2026-05-08. v1.0.5 ships Pillar A (I-1+I-2+I-3) +
Pillar B (D Q3-A) only. v1.0.6 LOCKED commitment for C.2.

**Track**: Gamma — **DEFERRED**.

**Archivos**:
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add
  ship-time archaeology trim procedure section).
- Modify: `templates/CLAUDE.local.md.template` (template guidance for
  destination projects).
- Create: `tests/test_plan_archaeology_trim_pattern.py` (smoke test
  for doc-coherence — pattern follows v1.0.4 doc-only smoke tests).

**Empirical context (v1.0.4 ship Balthasar INFO #17)**:

v1.0.4 plan reached ~2200 lines (vs ~600-800 line baseline of v1.0.3).
Cause: iter-by-iter triage context preserved inline (iter-1 fixes,
iter-2 surgical fixes + scope-trim, iter-3 polish, iter-5 Path 3
re-implementation). v1.0.5 ship-time should collapse iteration
archaeology from plan body into CHANGELOG narrative.

**Implementation outline**:

Methodology pattern:
1. **At ship-time**: extract iter-by-iter triage context from
   `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]` "Process
   notes" section.
2. **Trim plan-tdd.md to "active plan only"**: current scope + tasks
   + acceptance criteria; no iter-1/iter-2/iter-3 archaeology.
3. **Document procedure in `skills/sbtdd/SKILL.md`** orchestrator
   rules + `templates/CLAUDE.local.md.template`.
4. **Cross-artifact coherence smoke test**: assert SKILL.md + template
   both reference the procedure.

Optional belt-and-suspenders: keep `planning/claude-plan-tdd-org.md`
as immutable archaeology while `planning/claude-plan-tdd.md` =
trimmed canonical (precedent already exists per v1.0.X cycles).

**Tests**: ~2-3 doc-coherence smoke tests asserting SKILL.md +
template reference the procedure.

### 2.7 v1.0.5 own-cycle dogfood (orchestrator)

**Track**: orchestrator (post Pillar A + Pillar B + Pillar C ship).

**Activities** (NON-`--parallel` self-dispatch — chicken-and-egg
deferred to v1.0.6):

1. **Items I-1+I-2+I-3 acceptance integration test**: synthesize
   2-track plan with 4 disjoint tasks. Dispatch via `auto --parallel`
   from controlled test fixture. Assert per CHANGELOG `[Unreleased]`
   combined acceptance criterion:
   - Parent's `.claude/auto-run.json` contains start_time + 4 task
     records (I-1)
   - Plan-tdd.md has 4 `[x]` checkbox flips, no lost updates (I-2)
   - Each worker subprocess receives forwarded operator flags (I-3)
   - All TDD triplet commits per task in git log
   - State file `current_phase: "done"` post-completion

2. **Item D Q3-A empirical validation**: synthesize task with
   intentional bypass (raw `git commit` instead of `close-phase`) →
   assert `close-task` raises `PreconditionError` with actionable
   message. Synthesize task with canonical close-phase per phase →
   assert `close-task` proceeds normally. Synthesize task with bypass
   + `--skip-preflight` → assert `close-task` proceeds + stderr
   breadcrumb emitted.

3. **Pre-merge gate clean WITHOUT INV-0**: v1.0.5 explicit goal per
   Q5. If Loop 2 doesn't converge cleanly within cap=5: escalate to
   user BEFORE applying INV-0.

4. **`--parallel` self-dispatch dogfood DEFERRED to v1.0.6** post-v1.0.5
   production validation. v1.0.5 cycle uses MANUAL Agent tool fan-out
   (precedent v0.4.0 through v1.0.4) for Track Alpha + Beta + Gamma
   dispatch.

---

## 3. Cross-module contracts

v1.0.5 introduces new cross-cuts limited to:

- **Item I-1**: NEW per-worker sidecar pattern in `auto_cmd.py`
  (`_audit_sidecar_path`, `_merge_audit_sidecars`, worker mode
  `_write_audit` redirect). Existing `_write_audit` orchestrator-mode
  signature preserved.
- **Item I-2** (iter-1 CRITICAL #1+#2+#3+#4 fix applied): NEW
  per-worker scratch pattern HELPERS in `close_task_cmd.py` only
  (`_scratch_plan_path`, `_merge_scratch_plans`,
  `_apply_flips_from_diff`, `_section_has_flipped`,
  `_iter_task_ids`, anchored `_flip_checkbox`) + worker mode
  `mark_and_advance` redirect. Sequential / orchestrator mode
  unchanged. `mark_and_advance` signature extends with optional
  `ns: argparse.Namespace = None` parameter (backward-compat default).
  **Wiring** (`_dispatch_tracks_concurrent` post-batch invocation)
  lives in `auto_cmd.py` Track Alpha T1, not Track Beta. Track Beta
  does NOT modify `auto_cmd.py`.
- **Item I-3**: NEW `_FORWARDABLE_FLAGS` MappingProxyType +
  `_build_worker_argv(task_ids, ns)` helper in `auto_cmd.py`.
  `_dispatch_tracks_concurrent` uses helper for worker argv builds.
- **Item D Q3-A** (iter-1 CRITICAL #5 fix applied): extends
  `close_task_cmd._preflight` with `skip_preflight: bool = False`
  parameter + git-log-based triplet check **scoped to "since last
  `chore: mark task` commit"** (not `phase_started_at_commit`) +
  new `_last_chore_task_close_sha` helper + `--skip-preflight`
  argparse flag in `run_sbtdd.py` close-task subparser.
  `close_task_cmd.cmd` reads flag from namespace + passes to
  preflight.
- **Item C.2**: doc-only changes to `skills/sbtdd/SKILL.md` +
  `templates/CLAUDE.local.md.template`. NO Python module changes.
  New smoke test `tests/test_plan_archaeology_trim_pattern.py`.

**Contratos preservados (no modificados)**:

- `PreconditionError` / `ValidationError` / `MAGIGateError` (existing).
- `subprocess_utils.run_with_timeout` unchanged.
- `_compute_loop2_diff_with_meta`, `_loop2_with_cross_check`,
  `_run_magi_checkpoint2` (v1.0.0 + v1.0.4 architecture) unchanged.
- INV-37 composite-signature output validation tripwire unchanged.
- `state_file.SessionState` schema unchanged (no schema migration).
- `commits.validate_prefix` unchanged.
- `partition_by_tracks` (v1.0.4 Path 3) unchanged.
- `_dispatch_tracks_concurrent` core thread-pool + queue + Popen logic
  unchanged; only argv builder + post-batch hooks added.
- v1.0.4 Items A+B membership-based subprocess gate
  (`_SUBPROCESS_INCOMPATIBLE_SKILLS` + `_build_recovery_message`)
  unchanged.

---

## 4. Escenarios BDD

### 4.1 Item I-1 — Per-worker sidecar audit-trail

**Escenario I1-1: worker mode redirects audit write to sidecar**

> **Given** Worker invocation `auto --task-ids T1,T3 --no-recursive`.
> **When** Worker calls `_write_audit(audit_data, ...)`.
> **Then** Audit data written to `.claude/auto-run-track-{hash}.json`
> sidecar (NOT `.claude/auto-run.json`). File written via atomic
> `os.replace` pattern.

**Escenario I1-2: orchestrator mode writes canonical audit**

> **Given** Orchestrator invocation `auto --parallel` (no --no-recursive).
> **When** Parent calls `_write_audit(audit_data, ...)`.
> **Then** Audit data written to canonical `.claude/auto-run.json`
> via atomic `os.replace`.

**Escenario I1-3: parent post-batch merges sidecars**

> **Given** 3 workers completed, each wrote sidecar
> `auto-run-track-{hash_A}.json`, `auto-run-track-{hash_B}.json`,
> `auto-run-track-{hash_C}.json`.
> **When** Parent calls `_merge_audit_sidecars(tracks, project_root)`.
> **Then** Returned dict contains: original parent's pre-dispatch
> record (start_time + planned task counts) + per_worker list
> (3 entries, one per sidecar) + aggregate_task_count (sum of all
> task IDs). Sidecar files deleted after successful merge.

**Escenario I1-4: missing sidecar handled gracefully**

> **Given** Worker terminated before writing sidecar (early kill /
> crash).
> **When** Parent calls `_merge_audit_sidecars(tracks, project_root)`.
> **Then** Per-worker entry contains `{"task_ids": [...],
> "status": "no_audit_data", "note": "Worker terminated before
> sidecar write"}`. Merge succeeds; canonical audit-run.json reflects
> partial state cleanly.

**Escenario I1-5: INV-26 audit-trail integrity verified**

> **Given** Parent dispatched 4 tasks across 2 tracks via `--parallel`.
> All workers completed successfully.
> **When** `make verify` runs integration test.
> **Then** Final `.claude/auto-run.json` contains:
> - Original `start_time` (parent's pre-dispatch)
> - `aggregate_task_count == 4`
> - `per_worker` list with 2 entries (one per track)
> - Each per-worker entry has its task_ids + completion timestamp
> No clobber detected; INV-26 satisfied.

**Escenario I1-6: orphan sidecar/scratch from prior crashed run reaped pre-dispatch (iter-1 WARNING fix)**

> **Given** Prior `auto --parallel` crashed mid-dispatch leaving
> stale `.claude/auto-run-track-{hash}.json` and
> `.claude/plan-scratch-{hash}.md` from a prior worker.
> **When** Operator re-invokes `auto --parallel`.
> **Then** `_dispatch_tracks_concurrent._reap_orphans` runs at
> dispatch entry, removes stale sidecar+scratch files matching the
> patterns, and proceeds with clean state. Stale data does NOT
> contaminate new run's merge step.

### 4.2 Item I-2 — Per-worker scratch plan flip-merge

**Escenario I2-1: worker mode writes flip to scratch**

> **Given** Worker invocation processing task `T3` (in `[ ]` state in
> main plan).
> **When** Worker calls `mark_and_advance(state, project_root, ns)`.
> **Then** Worker creates `.claude/plan-scratch-{hash}.md` (copy of
> main plan), flips `T3` checkbox `[ ]` → `[x]` in scratch, writes
> scratch via atomic `os.replace`. Main plan UNCHANGED in worker mode.

**Escenario I2-2: orchestrator/sequential mode writes to main plan**

> **Given** Sequential or orchestrator invocation (no --no-recursive +
> --task-ids).
> **When** Calling code invokes `mark_and_advance(state, project_root)`.
> **Then** Flip applied directly to main plan-tdd.md via atomic
> `os.replace`. v1.0.4 sequential behavior preserved exactly.

**Escenario I2-3: parent post-batch merges scratch flips via diff (iter-1 CRITICAL #1+#3 fix)**

> **Given** 2 workers completed: worker A processed tasks T1+T3
> (scratch shows `[x]` for T1, T3); worker B processed tasks T2+T4
> (scratch shows `[x]` for T2, T4). Main plan has `[ ]` for all 4.
> **When** Parent calls `_merge_scratch_plans(tracks, project_root)`.
> **Then** `_apply_flips_from_diff(main, scratch_A)` walks both
> texts and applies T1+T3 flips (only present in scratch_A);
> `_apply_flips_from_diff(main, scratch_B)` walks both texts and
> applies T2+T4 flips. Main plan has `[x]` for ALL 4 tasks. Scratch
> files deleted post-merge.

**Escenario I2-3b: partial worker failure does NOT fabricate flips (iter-1 CRITICAL #1+#3 fix)**

> **Given** Worker A assigned tasks T1+T3 but crashed after
> flipping T1 in scratch + before flipping T3 (scratch shows
> `[x]` for T1, `[ ]` for T3).
> **When** Parent calls `_merge_scratch_plans(tracks, project_root)`.
> **Then** Main plan gets `[x]` for T1 only (derived from
> scratch-vs-main diff). T3 remains `[ ]` in main. Operator can
> resume the partial work via `/sbtdd auto --task-ids T3` later.
> No false-positive flip fabricated. Critical regression vs
> pre-fix design which would have flipped both T1 AND T3
> regardless of scratch state.

**Escenario I2-4: real multiprocessing race regression test (iter-1 WARNING strengthened)**

> **Given** Synthetic 4-task plan + 2-worker dispatch using real
> `multiprocessing.get_context("spawn")` + `multiprocessing.Process`
> + `multiprocessing.Barrier(parties=2)` to synchronize the
> read-modify-write window precisely.
> **When** Both workers call `mark_and_advance` for their disjoint
> task IDs; the Barrier blocks both at the read step until both
> arrive, then releases simultaneously to maximize race likelihood
> on the write step. Workers are real subprocesses (not threads,
> not mocks) — exercises true cross-process file write race.
> **Then** Per-worker scratch files (NOT main plan) capture each
> worker's flip independently; parent merge produces all 4 flips
> in main plan. Test asserts main plan integrity AFTER merge by
> reading `git status` (clean tree post-flip) + parsing main plan
> for 4 `[x]` checkboxes. Cross-platform (Windows + POSIX) via
> `spawn` context + module-level helper function (picklable).
> Repeated 50× to amplify race-window detection.

**Escenario I2-5: anchored `_flip_checkbox` regex respects task-section boundaries (iter-1 CRITICAL #2 fix)**

> **Given** Plan with `### Task 3` section that contains NO
> `- [ ]` checkbox (operator already removed it manually) +
> `### Task 4` section with `- [ ]` checkbox.
> **When** `_flip_checkbox(plan_text, "3")` invoked.
> **Then** Plan text is returned UNCHANGED (idempotent guard
> triggers). Task 4's `[ ]` is NOT incorrectly flipped to `[x]`.
> Pre-fix regex `(### Task 3.*?)(- \[ \])` with `re.DOTALL`
> would have matched Task 4's `[ ]`; anchored implementation
> bounds search to Task 3's section only.

### 4.3 Item I-3 — Worker CLI flag forwarding

**Escenario I3-1: forwardable flags propagate to worker argv**

> **Given** Operator invocation
> `auto --parallel --magi-threshold=GO --verification-retries=5`.
> **When** `_dispatch_tracks_concurrent` builds worker argv via
> `_build_worker_argv(task_ids, ns)`.
> **Then** Worker argv contains
> `[..., --task-ids, T1,T3, --no-recursive, --magi-threshold, GO,
> --verification-retries, 5]`. All `_FORWARDABLE_FLAGS` with non-None
> values appended.

**Escenario I3-2: missing flags omit from worker argv**

> **Given** Operator invocation `auto --parallel` (no other flags).
> **When** Worker argv built.
> **Then** argv contains ONLY `[..., --task-ids, T1,T3, --no-recursive]`.
> No empty/None flags appended (would confuse argparse).

**Escenario I3-3: documented forwardable list matches `_FORWARDABLE_FLAGS`**

> **Given** `_FORWARDABLE_FLAGS` MappingProxyType definition in
> `auto_cmd.py`.
> **When** Test asserts dictionary keys + helper docstring
> enumerate same flags.
> **Then** Documented list = `--plugins-root`,
> `--magi-max-iterations`, `--magi-threshold`,
> `--verification-retries`, `--model-override`. Drift between code +
> docs caught by smoke test.

### 4.4 Item D Q3 OPTION A — close_task_cmd._preflight enforcement

**Escenario D-1: bypass detected → PreconditionError (iter-1 CRITICAL #5 fix — commit-window since last `chore:` mark task)**

> **Given** Active task. Commit chain since the last
> `chore: mark task <N> complete` commit (or branch root if
> none) contains only raw `git commit` subjects (no
> `test:`/`feat:|fix:`/`refactor:` triplet).
> **When** `close_task_cmd._preflight(state, project_root)` invoked.
> **Then** `PreconditionError` raised. Message contains:
> - "Phase advance gate bypassed: commit chain since
>   {last chore SHA | branch root} lacks test:/feat:|fix:/refactor:
>   triplet"
> - "INV-1 + INV-5..7"
> - "Recovery: invoke `python skills/sbtdd/scripts/run_sbtdd.py
>   close-phase` once per pending phase"
> - "OR pass --skip-preflight if emergency operator override"

**Escenario D-2: canonical close-phase chain → no trigger**

> **Given** Active task. Commit chain since the last
> `chore: mark task <N> complete` commit contains canonical TDD
> triplet: 1× `test:` + 1× `feat:` (or `fix:`) + 1× `refactor:`
> (the three phase-close commits for the current task).
> **When** `close_task_cmd._preflight(state, project_root)` invoked.
> **Then** No exception raised. Preflight proceeds normally.

**Escenario D-2b: first task in plan (no prior `chore:` commits) → boundary is branch root**

> **Given** First task in the plan. No `chore: mark task` commits
> exist on current branch yet.
> **When** `_last_chore_task_close_sha(project_root)` invoked.
> **Then** Returns `None`. `_preflight` falls back to branch-root
> boundary (effectively all commits on the branch). Triplet check
> still validates the test:/feat:|fix:/refactor: pattern is present.

**Escenario D-3: --skip-preflight bypasses + audit breadcrumb**

> **Given** Bypass scenario (no triplet in commit chain) + operator
> passed `--skip-preflight` flag.
> **When** `close_task_cmd._preflight(state, project_root,
> skip_preflight=True)` invoked.
> **Then** No exception raised. stderr breadcrumb emitted:
> `[sbtdd close-task] WARNING: --skip-preflight active; phase advance
> gate enforcement BYPASSED for task_id=<N> since SHA <sha>.
> Audit-logged.`

**Escenario D-4: empirical validation in v1.0.5 own-cycle**

> **Given** v1.0.5 own-cycle synthesizes test cases for both bypass
> + canonical paths.
> **When** Cycle's tests run via `make verify`.
> **Then** Bypass cases assert `PreconditionError` raised. Canonical
> cases assert no exception. Override cases assert breadcrumb +
> proceed. Item D Q3-A empirically validated.

### 4.5 Item C.2 — Plan archaeology trim methodology

**Escenario C2-1: SKILL.md documents ship-time trim procedure**

> **Given** Updated `skills/sbtdd/SKILL.md` post-Track-Gamma close.
> **When** Grep for "plan archaeology trim" pattern.
> **Then** SKILL.md contains explicit ship-time procedure:
> "At v1.0.X ship time, extract iter-by-iter triage context from
> `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]` Process
> notes section. Trim plan-tdd.md to 'active plan only' (scope +
> tasks + acceptance; no iter archaeology)."

**Escenario C2-2: CLAUDE.local.md.template references archaeology trim**

> **Given** Updated `templates/CLAUDE.local.md.template`.
> **When** Grep for archaeology trim pattern.
> **Then** Template contains the same procedure reference + cross-link
> to SKILL.md authoritative version.

**Escenario C2-3: smoke test asserts cross-artifact reference**

> **Given** `tests/test_plan_archaeology_trim_pattern.py` (new).
> **When** Test runs.
> **Then** Asserts SKILL.md AND `templates/CLAUDE.local.md.template`
> both contain "plan archaeology trim" reference (case-insensitive
> substring match). Drift between docs caught.

---

## 5. Subagent layout + execution timeline

### 5.1 Track Alpha (subagent #1, sequential I-1 → I-3)

**Owner**: code-architect or general-purpose subagent.
**Scope**: I-1 + I-3 in `auto_cmd.py` + `tests/test_auto_cmd.py`.
**Wall-time estimado**: ~1 dia.

Sequential ordering rationale:
1. **I-1** (~0.6 dia): per-worker sidecar pattern (worker mode
   redirect + parent post-batch merge helper + cleanup).
2. **I-3** (~0.4 dia): `_FORWARDABLE_FLAGS` + `_build_worker_argv`
   helper + `_dispatch_tracks_concurrent` integration.

Sin dependencias inter-track.

### 5.2 Track Beta (subagent #2, sequential I-2 → D Q3-A) — helper-only per iter-1 CRITICAL #4

**Owner**: code-architect or general-purpose subagent.
**Scope**: I-2 + D Q3-A in `close_task_cmd.py` + `run_sbtdd.py`
argparse + `tests/test_close_task_cmd.py`. **Track Beta does NOT
modify `auto_cmd.py`** — all `_dispatch_tracks_concurrent` post-batch
hook wiring lives in Track Alpha T1 (sec.2.1 step 4 + iter-1
CRITICAL #4 architectural fix).
**Wall-time estimado**: ~1 dia.

Sequential ordering rationale:
1. **I-2** (~0.5 dia): per-worker scratch + flip-merge HELPERS
   (`_scratch_plan_path`, `_merge_scratch_plans`,
   `_apply_flips_from_diff`, `_section_has_flipped`,
   `_iter_task_ids`, anchored `_flip_checkbox`) + worker-mode
   redirect in `mark_and_advance`. Pure functions; importable
   from Track Alpha. NO `auto_cmd.py` changes.
2. **D Q3-A** (~0.5 dia): `_preflight` extension with
   commit-window scoped to "since last `chore: mark task` commit"
   per iter-1 CRITICAL #5 fix + `--skip-preflight` argparse +
   audit breadcrumb + `_last_chore_task_close_sha` helper.

Sin dependencias inter-track (Track Alpha imports Track Beta's
helpers; Track Alpha must merge AFTER Track Beta's commits land,
which the orchestrator enforces via subagent dispatch ordering).

### 5.3 Track Gamma — DEFERRED to v1.0.6

**Status**: DEFERRED per iter-2 CRITICAL trigger pre-staged response.
v1.0.5 ships only Track Alpha + Track Beta. C.1 sweep already
applied inline; no Track Gamma work for v1.0.5.

### 5.4 True parallelism observado (iter-1 CRITICAL #4 fix + iter-2 Pillar C deferral)

Surfaces Track Alpha vs Track Beta — **truly disjoint at file level
after iter-1 CRITICAL #4 architectural fix; Track Gamma deferred to
v1.0.6 per iter-2 trigger**:

| Surface | Alpha | Beta |
|---------|-------|------|
| `skills/sbtdd/scripts/auto_cmd.py` | yes (I-1+I-3 + post-batch wiring for I-2 helpers + `_reap_orphans`) | — |
| `tests/test_auto_cmd.py` | yes (extend) | — |
| `skills/sbtdd/scripts/close_task_cmd.py` | — | yes (I-2 helpers + D Q3-A + anchored `_flip_checkbox` + `_last_chore_task_close_sha`) |
| `skills/sbtdd/scripts/run_sbtdd.py` | — | yes (--skip-preflight argparse) |
| `tests/test_close_task_cmd.py` | — | yes (extend) |
| `skills/sbtdd/scripts/state_file.py` | yes (DRY consolidation: shared `_atomic_write_json`) | yes (import shared helper) |

**Disjoint at file level for production code**. Track Alpha imports
Track Beta's helpers (`from close_task_cmd import _merge_scratch_plans`).
Per iter-2 hardening: this is a **HARD subagent-dispatch-ordering
constraint**, not a soft dependency. Orchestrator MUST dispatch Track
Beta T3 → T4 BEFORE Track Alpha T1 Step 5 (the wiring step). Track
Alpha T1 Steps 1-4 (sidecar pattern) + T2 (flag forwarding) can run
in parallel with Track Beta T3+T4. Only T1 Step 5 has the import
dependency. The "stub the import temporarily and rebase" fallback
mentioned in earlier drafts is RETRACTED — too brittle, error-prone,
risks landing broken intermediate state. `state_file.py` shared by
both tracks for DRY atomic-write consolidation: Track Alpha lands
the consolidation; Track Beta imports the consolidated helper.

Original Q1 "cero overlap" claim refined per iter-1+iter-2 audits:
was function-modification-level FALSE (iter-1, both touched
`_dispatch_tracks_concurrent`); fixed by consolidating wiring into
Track Alpha T1 only. iter-2 surfaced cross-module-import
architectural concern resolved via explicit subagent-dispatch
ordering invariant (above).

### 5.5 Mid-cycle methodology (orchestrator)

**Owner**: orchestrator (single Claude Code session).
**Scope**: post Track-Alpha + Track-Beta + Track-Gamma close.
**Wall-time estimado**: ~1 dia total.

Triggered AFTER all 3 tracks close + commits land:

1. **Production-grade `--parallel` integration test** (~30-60 min):
   synthetic 2-track plan with 4 disjoint tasks. Run via `auto
   --parallel`. Assert combined acceptance criterion (I-1 + I-2 + I-3
   all closed). REPORT findings in CHANGELOG `[1.0.5]` Process notes.

2. **Item D Q3-A empirical validation** (~30-45 min): synthetic test
   cases for bypass / canonical / override scenarios. Validates Q3-A
   enforcement empirically.

3. **Pre-merge gate clean WITHOUT INV-0** (~variable): `/sbtdd
   pre-merge` end-to-end. Per Q5 strict no-INV-0 stance: if Loop 2
   doesn't converge cleanly within cap=5, escalate to user BEFORE
   applying INV-0.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

- **Cap=3 HARD** per G1 binding (CHANGELOG `[1.0.0]`, precedente
  cerrado v1.0.1+v1.0.2+v1.0.3+v1.0.4 = 5-streak no-override
  Checkpoint 2). NO INV-0 path. v1.0.5 goal: 6-cycle Checkpoint 2
  streak.
- Bundle scope focused (3 pillars) — esperamos converger en 1-2 iters.
- **Iter 2 CRITICAL trigger** (v1.0.3 spec sec.6.1, v1.0.4 second
  empirical fire): if Loop 2 iter 2 still surfaces ANY CRITICAL
  finding (post-iter-1-triage-fix), scope-trim immediately rather
  than burning iter 3. Pre-staged decision: defer Track Gamma (C.1+
  C.2) first; if needed, also Track Beta (D Q3-A); only Pillar A
  (I-1+I-2+I-3) son hard-LOCKED for v1.0.5 ship.
- Si llega a iter 3 sin convergencia, default scope-trim ladder
  applies:
  1. Defer Track Gamma to v1.0.6 (smallest, doc-only).
  2. Defer Track Beta D Q3-A to v1.0.6 (high-value but defer-tolerant).
  3. Pillar A (I-1+I-2+I-3) son hard-LOCKED.

**Methodology decision**: Checkpoint 2 dispatch usa **Opcion A
manual `run_magi.py`** per hybrid methodology + v1.0.2+v1.0.3+v1.0.4
precedent.

### 6.2 Loop 1 (`/requesting-code-review`)

- **Cap=10**. Clean-to-go criterion: zero CRITICAL + zero
  high-impact WARNING.
- Bundle scope minimal (3 tracks, mostly small fixes) — esperamos
  converger en 1-2 iters.

### 6.3 Loop 2 (`/magi:magi`) — strict no-INV-0 stance

- **Cap=5** per `auto_magi_max_iterations`.
- **Carry-forward block** (CLAUDE.local.md §6 v1.0.0+) presente
  desde iter 2.
- **G2 binding stance (Q5 = A strict)**: si Loop 2 iter 3 no
  converge clean, scope-trim per spec-base sec.6.1 ladder (Track
  Gamma defer first → Track Beta defer second → Pillar A hard-LOCKED).
- **NO INV-0 override** without explicit user authorization. If
  Loop 2 doesn't converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0 (per memory
  `feedback_manual_synthesis_exceptional`).
- **Goal**: re-establish pre-merge Loop 2 no-override streak from
  1 cycle.

### 6.4 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails durante el v1.0.5 own-cycle
(e.g., new regression), el operator MUST fall back a manual
`python skills/magi/scripts/run_magi.py` direct dispatch + manual
mini-cycle commits. Document en CHANGELOG `[1.0.5]` Process notes.
Precedentes v1.0.0 through v1.0.4.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.4 → 1.0.5.

### 7.2 CHANGELOG `[1.0.5]` sections

- **Added** —
  Per-worker sidecar audit-trail pattern (`_audit_sidecar_path`,
  `_merge_audit_sidecars`; Item I-1);
  Per-worker scratch plan + flip-merge pattern (`_scratch_plan_path`,
  `_merge_scratch_plans`; Item I-2);
  `_FORWARDABLE_FLAGS` MappingProxyType + `_build_worker_argv` helper
  (Item I-3);
  `close_task_cmd._preflight` HARD-BLOCK with `--skip-preflight`
  override + audit breadcrumb (Item D Q3 OPTION A);
  Plan archaeology trim methodology in SKILL.md +
  `templates/CLAUDE.local.md.template` (Item C.2 doc + smoke test).
- **Changed** —
  `mark_and_advance` signature extends with optional
  `ns: argparse.Namespace = None` parameter (worker-mode redirect);
  `_dispatch_tracks_concurrent` worker argv builder uses
  `_build_worker_argv` helper + invokes post-batch merge helpers.
- **Process notes** — Pillar A architectural choices Q2/Q3
  (per-worker isolation pattern unified across I-1/I-2); Pillar B Q4
  (--skip-preflight flag-only per v1.0.4 lesson); Q5 strict no-INV-0
  stance + 6-cycle Checkpoint 2 streak goal; production-grade
  `--parallel` integration test acceptance per CHANGELOG
  `[Unreleased]` v1.0.4 commitment; Item D Q3-A empirical
  validation; v1.0.5 own-cycle dogfood NO `--parallel`
  self-dispatch (deferred to v1.0.6); pre-merge Loop 2 streak
  re-establish outcome.
- **Deferred (rolled to v1.0.6)** — I-4 stale INV-22 docstring
  cosmetic; I-5 partition_by_collision DeprecationWarning CI handling;
  `_run_single_task_isolated` removal candidate; real-world
  `--parallel` end-to-end dogfood validation; audit GAPs L1.0.4-A
  through L1.0.4-D (v1.0.3 carry-forward); `make verify` runtime
  polish below 165s NF-A target; `--parallel` self-dispatch dogfood.
- **Deferred (rolled to v1.0.6+)** — All items inherited from v1.0.4
  carry-forward (per CHANGELOG `[1.0.4]` Deferred sections).

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.5 docs section sobre per-worker sidecar pattern +
  per-worker scratch pattern + Item D Q3-A `--skip-preflight` flag +
  plan archaeology trim methodology.
- **SKILL.md**: `### v1.0.5 notes` section documentando 6 items +
  Pillar A architectural choices + Item D Q3-A enforcement + plan
  archaeology trim procedure.
- **CLAUDE.md** (project root, gitignored per CLAUDE.local.md sec.1
  policy): v1.0.5 release notes pointer.

---

## 8. Risk register v1.0.5 (CLEAN — Pillar C.1 sweep applied)

(Sweep applied: stale references to eliminated v1.0.4 mechanisms
[SBTDD_INTERACTIVE env var, Item D 3-touchpoint enforcement,
env-var/isatty heuristic, etc.] REMOVED. Risk register reflects
current v1.0.5 architectural state cleanly.)

- **R1**. I-1 sidecar approach may surface cleanup issues if parent
  crashes mid-merge (orphaned sidecar files). Mitigation: parent
  re-invocation detects orphaned sidecars + retries merge logic
  before new dispatch. Atomic os.replace ensures partial sidecar
  writes never persist. Cross-platform robust.
- **R2**. I-2 per-worker scratch pattern requires disjoint task IDs
  invariant (workers don't overlap on same checkboxes). Mitigation:
  `partition_by_tracks` v1.0.4 invariant guarantees disjoint task IDs
  per track. Smoke test asserts invariant in v1.0.5 own-cycle dogfood.
- **R3**. I-3 forwarded flags may include sensitive values
  (`--model-override` could expose internal model names). Mitigation:
  forwardable list documented + audit-loggable; no secrets in
  forwarded flags by construction.
- **R4**. Item D Q3-A hard-block may surprise existing operators in
  workflows that don't follow canonical close-phase per-phase
  pattern. Mitigation: `--skip-preflight` flag-only emergency
  override + clear error message + audit breadcrumb. v1.0.5 own-cycle
  dogfood validates both bypass + canonical paths empirically.
- **R5**. Plan archaeology trim methodology is doc + smoke test;
  if methodology pattern proves incomplete (e.g., needs more
  procedural detail), v1.0.6 refinement.
- **R6**. v1.0.5 own-cycle integration test exercises `--parallel`
  end-to-end via test fixture (NOT real production work). Real-world
  `--parallel` self-dispatch dogfood deferred to v1.0.6 post v1.0.5
  production-validation. Mitigation: v1.0.6 LOCKED commitment.
- **R7**. Pre-merge Loop 2 streak re-establish goal (Q5 = A strict)
  may not be achievable if cycle surfaces fundamental architectural
  questions. Mitigation: G2 scope-trim ladder (defer Track Gamma
  first, then Track Beta D Q3-A); INV-0 remains available but
  escalated to user before application.
- **R8**. Within-track sequential ordering (Track Beta I-2 → D Q3-A)
  required because both modify `close_task_cmd.py`. Mitigation:
  subagent prompt explicitly orders I-2 first; D Q3-A second; tests
  assert no regression in I-2 work after D Q3-A lands.

---

## 9. Acceptance criteria final v1.0.5

v1.0.5 ship-ready cuando:

### 9.1 Functional Items I-1/I-2/I-3 + D Q3-A + C.1 + C.2

- **F1**. F162-F165 (Item I-1): per-worker sidecar pattern + parent
  post-batch merge + INV-26 integration test + missing-sidecar
  graceful handling.
- **F2**. F166-F168 (Item I-2): per-worker scratch + flip-merge +
  real `multiprocessing.Process` race regression test.
- **F3**. F169-F171 (Item I-3): `_FORWARDABLE_FLAGS` MappingProxyType
  + `_build_worker_argv` helper + forwarding contract test.
- **F4**. F172-F175 (Item D Q3-A): `_preflight` HARD-BLOCK +
  `--skip-preflight` flag-only override + audit breadcrumb +
  backward-compat preserved + 4 acceptance tests.
- **F5**. F176-F177 (Item C.1): spec sec.8 stale risk-register
  clean-sweep applied (this very document — RISK REGISTER reflects
  current v1.0.5 state cleanly).
- **F6** (Item C.2): **DEFERRED to v1.0.6** per iter-2 CRITICAL
  trigger pre-staged response. F178-F180 not applicable to v1.0.5.
- **F7** (own-cycle integration test): production-grade `--parallel`
  integration test acceptance per CHANGELOG `[Unreleased]` (synthetic
  2-track plan + 4 disjoint tasks + ALL 3 gaps closed).
- **F8** (Item D Q3-A empirical validation): bypass + canonical +
  override test cases pass.

### 9.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict + coverage >= 88%, runtime <= 200s soft / 220s hard
  (acknowledges v1.0.4 baseline 195s + new tests).
- **NF-B**. Tests baseline 1226 + 1 skipped + ~25-40 nuevos =
  ~1250-1265 final.
- **NF-C**. Cross-platform (Windows + POSIX) — I-2 race test
  validated on both via `multiprocessing.get_context("spawn")` +
  module-level helper.
- **NF-D**. Author/Version/Date headers en archivos modificados/
  nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados.

### 9.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; **NO INV-0 path**. 6-cycle
  Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (re-establish streak from 1 cycle post v1.0.4 break per Q5 = A).
  If unable to converge cleanly within cap=5: escalate to user
  BEFORE applying INV-0.
- **P3**. CHANGELOG `[1.0.5]` entry written con secciones Added /
  Changed / Process notes + Pillar A architectural choices + Pillar B
  Item D Q3-A enforcement + Pillar C.1 sweep + Pillar C.2 methodology
  + dogfood findings.
- **P4**. Version bump 1.0.4 -> 1.0.5 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.5` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2
  iter findings sin excepcion.
- **P7**. v1.0.5 own-cycle integration test empirically validates
  I-1+I-2+I-3 fixes via synthetic 2-track plan.
- **P8**. Item D Q3-A empirical validation: intentional-bypass test
  cases verify hard-block fires; canonical close-phase test cases
  verify normal flow.

### 9.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.5 ship + 6 items + dogfood
  observations).
- **D3**. Documented:
  - I-1 per-worker sidecar pattern in `auto_cmd.py` docstring.
  - I-2 per-worker scratch pattern in `close_task_cmd.py` docstring.
  - I-3 `_FORWARDABLE_FLAGS` documented in helper docstring.
  - Item D Q3-A `--skip-preflight` flag in run_sbtdd help + README.
  - Plan archaeology trim procedure in SKILL.md +
    `templates/CLAUDE.local.md.template`.

---

## 9.5 Inherited invariants from v0.4.x and v1.0.1+v1.0.2+v1.0.3+v1.0.4 (cross-artifact wording)

The HF1 manual-synthesis recovery breadcrumb wording (canonical
single-line text `[sbtdd magi] synthesizer failed; manual synthesis
recovery applied`) is preserved verbatim across spec / CHANGELOG /
impl per the cross-artifact alignment contract
(`tests/test_changelog.py`). v1.0.5 ships no behavioral change to
this path.

The INV-37 composite-signature output validation tripwire (v1.0.1
Item A0) is preserved verbatim — `_run_spec_flow` mtime + size +
sha256 check applies during v1.0.5 own-cycle if operator drives
`/sbtdd spec` instead of using `--resume-from-magi`. Items I-1/I-2
runtime per-worker sidecar/scratch patterns operate in subprocess
boundaries; INV-37 tripwire path unchanged.

The Item C v1.0.2 `spec_lint` gate (R1-R5 rules with R3 warning per
Q3) is preserved unchanged.

The Q4 v1.0.2 coverage threshold = `floor(baseline) - 2%` protocol
is preserved at 88% (v1.0.4 measured 90.37%; v1.0.5 must not regress
below).

The v1.0.3 cross-check Windows long-filename fix (Item B
`@<filepath>` reference + project-relative temp dir) is preserved
unchanged.

The v1.0.4 Items A+B membership-based subprocess gate
(`_SUBPROCESS_INCOMPATIBLE_SKILLS` + `_build_recovery_message` +
override hatch `allow_interactive_skill=True`) is preserved
unchanged.

The v1.0.4 Path 3 `--parallel` architecture (`partition_by_tracks` +
`_dispatch_tracks_concurrent` + `--task-ids` filter +
`--no-recursive` guard) is preserved unchanged. v1.0.5 EXTENDS this
architecture with per-worker sidecar (I-1) + per-worker scratch
(I-2) + flag forwarding (I-3) post-batch merge helpers.

---

## 10. Referencias

- Spec base v1.0.5: `sbtdd/spec-behavior-base.md`
  (uncommitted en branch `feature/v1.0.5-bundle`).
- Contrato autoritativo
  v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.4 ship record: tag `v1.0.4` (commit `87f14a3`); merge
  `b1c5262` on `main`.
- v1.0.3 ship record: tag `v1.0.3` (commit `39a9c18`); merge
  `0aeff7d` on `main`.
- v1.0.4 LOCKED carry-forward to v1.0.5 per CHANGELOG `[Unreleased]`
  section (committed `6320124` + finalized in `[1.0.4]` section
  committed `87f14a3`).
- v1.0.5 LOCKED memories:
  - `project_v105_parallel_correctness_locked.md` (CRITICAL —
    I-1/I-2/I-3 details + acceptance criteria).
  - `project_v104_shipped.md` (full v1.0.4 ship record + cycle
    metrics).
- v1.0.6 deferred backlog: I-4 cosmetic + I-5 CI handling +
  partition_by_collision deletion + real-world dogfood + audit GAPs +
  make verify polish + `--parallel` self-dispatch dogfood + all
  v1.0.4 carry-forward inherited items.
- Brainstorming refinement decisions (2026-05-08):
  - Q1 — 3-track parallel disjoint surfaces: Track Alpha = I-1+I-3
    (auto_cmd.py only); Track Beta = I-2+D Q3-A (close_task_cmd.py +
    run_sbtdd.py); Track Gamma = C.1+C.2 (spec/SKILL.md/template/
    smoke test).
  - Q2 — I-1 per-worker sidecar files merged by parent post-batch
    (robustness winner per per-worker isolation + atomic writes +
    cross-platform + forensics-friendly).
  - Q3 — I-2 per-worker scratch plan files + flip-merge by parent
    post-batch (same isolation pattern as I-1; preserves per-task
    atomicity; merge is simple flip-collect due to disjoint task IDs).
  - Q4 — Item D Q3-A `--skip-preflight` flag-only emergency override
    + stderr audit breadcrumb (no env var per v1.0.4 architectural
    lesson).
  - Q5 — strict no-INV-0 stance: re-establish pre-merge Loop 2
    no-override streak from 1 cycle; bias toward G2 scope-trim
    ladder over INV-0; if Loop 2 doesn't converge cleanly within
    cap=5, escalate to user BEFORE applying INV-0.
- Branch: trabajo en `feature/v1.0.5-bundle` (branched off `main`
  HEAD `b1c5262` = v1.0.4 merge commit).
