# Especificacion base — sbtdd-workflow v1.0.5 (post-v1.0.4 ship)

> Raw input para `/brainstorming` (primera fase del ciclo SBTDD para v1.0.5).
> `/brainstorming` consumira este archivo y generara `sbtdd/spec-behavior.md`
> (BDD overlay con escenarios Given/When/Then testables).
>
> Generado 2026-05-08 post-v1.0.4 ship (tag `v1.0.4` at commit `87f14a3`,
> branch `feature/v1.0.5-bundle` branched off `main` HEAD `b1c5262` =
> v1.0.4 merge commit).
>
> v1.0.5 ships los items LOCKED documentados en CHANGELOG.md `[Unreleased]`
> + memory `project_v105_parallel_correctness_locked.md` per user mandate
> 2026-05-08 ("documenta I-1, I-2 e I-3 para el proximo patch, deben quedar
> resueltos"). Items A+B+C foundation shipped en v1.0.4; v1.0.5 cierra los
> operational hygiene gaps que bloquean production-grade `--parallel`
> end-to-end + ships Item D Q3 OPTION A (close_task_cmd._preflight code-side
> enforcement) + spec sec.8 stale risk-register sweep + plan archaeology
> trim methodology.
>
> Per Balthasar v1.0.4 iter-6b INFO: "v1.0.5 is becoming a magnet release —
> schedule a polish-only cycle soon". Scope-trim upfront. v1.0.5 = focused
> production-readiness pillar (3 CRITICAL `--parallel` gaps + Item D Q3-A
> code-side) + polish-only secondary pillar (spec sweep + plan trim).
> Defer v1.0.5+ accumulated backlog (I-4 cosmetic, I-5 CI handling,
> partition_by_collision deletion, real-world dogfood validation, audit
> GAPs L1.0.4-A through L1.0.4-D, make verify runtime polish, etc.) to
> v1.0.6 polish-only cycle.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0+v1.0.1
> +v1.0.2+v1.0.3+v1.0.4 frozen se mantiene en
> `sbtdd/sbtdd-workflow-plugin-spec-base.md`; este documento NO lo reemplaza
> — agrega el delta v1.0.5 a la base.
>
> Archivo cumple INV-27: cero matches uppercase placeholder word-boundary
> verificable con `spec_cmd._INV27_RE` regex.
>
> v1.0.5 G1 binding HARD: cap=3 sin INV-0 path para Checkpoint 2
> (precedente cerrado v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4 = 5-cycle no-override
> Checkpoint 2 streak; v1.0.4 broke pre-merge Loop 2 streak via INV-0 but
> Checkpoint 2 streak preserved). G2 binding: scope-trim default si Loop 2
> iter 3 no converge (defer Pillar B polish a v1.0.6 si necesario; Pillar A
> CRITICAL items son hard-LOCKED).
>
> v1.0.4 introduced **5-cycle pre-merge no-override streak BROKEN** via INV-0
> at iter-6b (Mel APPROVE 82%, 2 caspar CRITICALs verified false-positive).
> v1.0.5 goal: cleanly close pre-merge gate WITHOUT INV-0 (re-establish
> streak from 1 cycle).

---

## 1. Objetivo

**v1.0.5 = "Production-grade `--parallel` + Item D code-side enforcement"**:
arregla los 3 LOCKED CRITICAL `--parallel` opt-in path correctness gaps
documentados en v1.0.4 ship CHANGELOG `[Unreleased]` (I-1/I-2/I-3) + ships
Item D Q3 OPTION A code-side enforcement architecture (replaces v1.0.4's
attempted 3-touchpoint doc-only that was scope-trimmed) + completes spec
sec.8 stale risk-register sweep (R1+R-NEW1+R5 references to eliminated
v1.0.4 mechanisms) + plan archaeology trim methodology.

Tres clases de items:

### Clase 1 — Pillar A PRIMARY (LOCKED CRITICAL)

- **Item I-1 — Worker subprocesses overwrite parent audit trail (INV-26)**.
  Location: `auto_cmd.py:3593-3605`. Workers re-write `.claude/auto-run.json`
  clobbering parent's start-time + aggregate task counts. Fix per architectural
  options: (a) per-worker sidecar files merged by parent post-batch; (b)
  workers signal via stdout, parent owns audit; (c) workers self-identify
  and skip audit write entirely. Acceptance: parent audit-run.json after
  parallel dispatch contains original start_time + aggregate task counts +
  per-worker completion records. INV-26 verified by integration test.

- **Item I-2 — Plan checkbox lost-update race in `mark_and_advance`**.
  Location: `close_task_cmd.py:108-123`. Concurrent workers calling
  `mark_and_advance` have no cross-process lock around plan-tdd.md
  read-modify-write. One worker's `[x]` flip can be silently overwritten.
  Fix per architectural options: (a) `fcntl.flock` POSIX / `msvcrt.locking`
  Windows around plan RMW; (b) workers don't flip plan checkboxes — parent
  flips all atomically post-batch; (c) per-worker scratch plan files merged
  by parent. Acceptance: race regression test with N concurrent
  `multiprocessing.Process` workers asserts all N flips visible
  (Windows-portable via `multiprocessing.get_context("spawn")` + module-level
  helper).

- **Item I-3 — Worker subprocesses don't inherit operator CLI flags**.
  Location: `auto_cmd.py:1564-1576`. Only `--task-ids` + `--no-recursive`
  propagated to workers. Missing: `--plugins-root`, `--magi-max-iterations`,
  `--magi-threshold`, `--verification-retries`, `--model-override`. Fix:
  `_dispatch_tracks_concurrent` builds each worker's argv with parent's flag
  values for every relevant flag (introspect via `argparse` namespace).
  Acceptance: forwarding test passes `--magi-threshold=GO
  --verification-retries=5` to parent + asserts each worker subprocess
  receives those values (intercept via mock `subprocess.Popen`). Document
  explicit forwardable-flags list in helper docstring.

### Clase 2 — Pillar B LOCKED (HIGH VALUE)

- **Item D Q3 OPTION A — code-side enforcement via
  `close_task_cmd._preflight`**. Replaces v1.0.4's attempted 3-touchpoint
  doc-only enforcement that was scope-trimmed per iter-2 Option D. v1.0.4
  Loop 2 iter 1 + iter 2 + iter 3 surfaced 3-agent unanimous WARNING that
  doc-only enforcement repeats v1.0.2's failure mode + v1.0.3 dogfood
  divergence (third consecutive cycle of doc-only attempts). Architecturally
  preferred path per Mel + Bal + Cas iter-1 recommendations.

  **Implementation outline**: extend `close_task_cmd._preflight` to detect
  when commit chain since `phase_started_at_commit` lacks the
  `test:`/`feat:|fix:`/`refactor:` triplet (i.e., subagent emitted raw
  `git commit` per phase instead of `close-phase`). When detected, raise
  `PreconditionError("Phase advance gate appears bypassed — close-phase
  per phase required")` with operator-actionable guidance. NOT a
  soft-warning (which was iter-1 fold-in attempted in v1.0.4) — this is
  hard-block enforcement. Combined with existing v1.0.2 Q2 Option B
  `/sbtdd close-task` automation mandate.

  Acceptance: integration test asserting `close_task_cmd._preflight`
  raises `PreconditionError` when commit chain since
  `phase_started_at_commit` lacks the canonical TDD triplet. Plus
  backward-compat test asserting normal close-phase + close-task flow
  proceeds without trigger. Plus `--skip-preflight` flag for emergency
  override (operator-controlled escape valve).

### Clase 3 — Pillar C LOCKED (METHODOLOGY)

- **Spec sec.8 stale risk-register sweep**. v1.0.4 ship documented
  iter-3 triage breadcrumb at top of spec-behavior.md noting stale Item D
  references in sec.4.4 + sec.8 (R1/R5/R-NEW1) + sec.9.1 F4 + sec.10 Q3
  carried forward as DEFERRED-to-v1.0.5 backlog markers but remained in
  active spec text. v1.0.5 cycle clean-sweeps these references. Doc-only
  scope.

- **Plan archaeology trim methodology**. v1.0.4 plan reached ~2200 lines
  carrying iter-by-iter triage context inline. Balthasar v1.0.4 iter-6b
  INFO #17: "Plan size disproportionate to code delta — maintenance debt
  accumulating". v1.0.5 establishes methodology pattern: at ship-time,
  collapse iter-triage archaeology from plan body into CHANGELOG narrative
  (separate the "active plan" from "iteration history"). Doc-only +
  procedure documentation.

### Out of scope v1.0.5 (rolled forward a v1.0.6)

- **I-4 stale INV-22 docstring** (cosmetic) — `auto_cmd.py:18, :954-962`
  module docstring still says "sequential only" but v1.0.4 ships parallel.
  Defer to v1.0.6 polish-only cycle.
- **I-5 partition_by_collision DeprecationWarning CI handling** — pytest
  filterwarnings module-mark mitigates locally; CI elevation handling defer.
- **`_run_single_task_isolated` removal candidate** — pending dogfood
  confirmation (chicken-and-egg: requires v1.0.5 LOCKED items to ship before
  real-world dogfood is feasible).
- **`partition_by_collision` deletion** (v1.x timeline per current
  DeprecationWarning).
- **Real-world `--parallel` end-to-end dogfood validation** — chicken-and-egg
  until v1.0.5 LOCKED items land.
- **Audit GAPs L1.0.4-A through L1.0.4-D** (Trigger criteria informational,
  Carry-forward "Prior triage context" block emit path, Review summary
  artifact auto-emission, Per-project setup checklist template thinness) —
  v1.0.3 audit carry-forward.
- **`make verify` runtime polish** (151-194s vs 165s NF-A hard target) —
  ~30-40s incremental from real `multiprocessing.Process` + cross-process
  `subprocess.run` smoke; v1.0.6 polish.
- **`/receiving-code-review` interactive subprocess regression test** —
  v1.0.4 empirical observation that subprocess didn't hang across 6+
  pre-merge runs; worth confirming in v1.0.5 with explicit regression test
  (LOW priority since v1.0.4 Items A+B prevent the path from being exercised
  inappropriately).

### Out of scope v1.0.5+ (rolled forward a v1.0.6+)

- All items inherited from v1.0.4 carry-forward (`agreement_rate` rename to
  `keep_rate`, `spec_lint` R3 promote, per-module coverage raise to 85%,
  pytest-cov dev dep, INV-31 default flip cycle, GitHub Actions CI workflow,
  Group B options 1/3/4/6/7, Migration tool real test, AST dead-helper
  detector codification, W8 Windows fs retry-loop, `_read_auto_run_audit`
  skeleton wiring, spec sec.7.1.3 G2 amendment, `magi_cross_check`
  default-flip).

### Criterio de exito v1.0.5

- Plugin instalable desde `BolivarTech/sbtdd-workflow` (marketplace
  `bolivartech-sbtdd`); version bumpea 1.0.4 -> 1.0.5.
- Tests baseline 1226 + 1 skipped preservados sin regresion + ~25-40
  nuevos (I-1 audit-trail integration: ~6-10; I-2 plan checkbox race:
  ~5-8 incl. real multiprocessing race test; I-3 flag forwarding: ~4-6;
  Item D Q3-A close_task_cmd._preflight: ~6-10; spec sweep: 0; plan trim
  methodology: ~2-3 doc-coherence smoke tests).
- `make verify` runtime <= 200s soft target / 220s hard (acknowledges
  v1.0.4 incremental cost from real multiprocessing tests; v1.0.6 polish
  may reduce).
- Coverage threshold mantenido en 88% (per Q4 v1.0.2 baseline);
  no regression below.
- **Production-grade `--parallel` empirical validation end-to-end**:
  v1.0.5 own-cycle dogfood Track Alpha + Track Beta dispatched VIA THE
  v1.0.4 `--parallel` flag (eat own dogfood). Combined acceptance criterion
  per CHANGELOG `[Unreleased]`: integration test exercising `--parallel`
  end-to-end on real synthetic 2-track plan with 4 disjoint tasks asserting
  ALL 3 gaps (I-1/I-2/I-3) closed.
- **Item D Q3 OPTION A empirical validation**: v1.0.5 own-cycle subagents
  test the new `close_task_cmd._preflight` enforcement empirically (some
  tasks intentionally bypass close-phase to verify hard-block fires; rest
  follow canonical close-phase per phase to verify normal flow proceeds).
- v1.0.4 LOCKED carry-forward del CHANGELOG `[1.0.4]` Deferred (v1.0.5)
  section enteramente cerrados.
- **G1 binding respetado**: cap=3 HARD para Checkpoint 2; sin INV-0.
  6-cycle Checkpoint 2 no-override streak preserved
  (v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4+v1.0.5).
- **Pre-merge Loop 2 streak re-establish from 1 cycle**: v1.0.4 broke
  via INV-0 at iter-6b; v1.0.5 goal = clean convergence at GO_WITH_CAVEATS
  full no-degraded WITHOUT INV-0 override.
- G2 binding respetado: scope-trim default si Loop 2 iter 3 no converge —
  defer Pillar C (spec sweep + plan trim methodology) a v1.0.6 si necesario;
  Pillar A items son hard-LOCKED. Pillar B (Item D Q3-A) high-value
  defer-tolerant under G2 ladder.

---

## 2. Alcance v1.0.5 — items LOCKED post-v1.0.4 ship

### 2.1 Item I-1 — Worker subprocesses overwrite parent audit trail (Pillar A PRIMARY CRITICAL)

**Track**: pending Q1 partition decision (likely Pillar A track).

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (lines ~3593-3605 audit-trail
  write path + worker mode short-circuit)
- Possibly modify: `skills/sbtdd/scripts/state_file.py` (if sidecar approach
  chosen, add audit-sidecar helper)
- New tests in `tests/test_auto_cmd.py` (extend) for INV-26 verification

**Empirical context (v1.0.4 ship)**:

`auto_cmd._dispatch_tracks_concurrent` spawns N subprocess workers; each
worker re-enters `auto_cmd.main()` with `--task-ids` filter + `--no-recursive`.
Worker mode currently writes to `.claude/auto-run.json` clobbering parent's
record. Post-batch, parent reloads state but parent's auto-run.json is
either empty (clobbered last) or contains only one worker's record.

**Architectural decision required (Q for brainstorming)**:

Three viable approaches:
- **Option (a)** — **Per-worker sidecar files merged by parent post-batch**.
  Workers write `.claude/auto-run-track-{hash(task_ids)}.json`. Parent
  post-batch merges all sidecars into main `.claude/auto-run.json` (sorted
  by task ID order). Pros: deterministic merge order, no race. Cons: more
  file I/O, cleanup complexity.
- **Option (b)** — **Workers signal via stdout, parent owns audit**.
  Workers print structured "audit-event: {...}" lines to stdout; parent
  collects + writes to its own audit file. Pros: single writer. Cons:
  stdout interleaving across workers; structured format spec needed.
- **Option (c)** — **Workers self-identify and skip audit write entirely**.
  Add `is_worker_mode = bool(ns.no_recursive)` short-circuit in audit-write
  helper. Parent owns ALL audit writes (including post-batch aggregation
  via worker exit codes + post-merge state file diff). Pros: simplest
  implementation, single writer. Cons: parent has less granular per-worker
  visibility.

Brainstorming evaluates simplicity vs visibility trade-off.

### 2.2 Item I-2 — Plan checkbox lost-update race (Pillar A PRIMARY CRITICAL)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (lines ~108-123
  `mark_and_advance` plan RMW path)
- New tests in `tests/test_close_task_cmd.py` (extend) — real
  `multiprocessing.Process` race test asserting all N flips visible

**Empirical context (v1.0.4 design gap)**:

`close_task_cmd.mark_and_advance` reads plan-tdd.md, modifies (flip `[ ]`
to `[x]` for current task), writes back via plain file write. No
cross-process lock. Two concurrent workers calling `mark_and_advance` for
disjoint task IDs can race: worker A reads plan, worker B reads plan,
both modify, A writes (flip 1), B writes (flip 2) — A's flip lost.

v1.0.4 sequential default unaffected (single writer). v1.0.4 `--parallel`
opt-in path SUSCEPTIBLE.

**Architectural decision required (Q for brainstorming)**:

Three viable approaches:
- **Option (a)** — **Cross-process file lock** (`fcntl.flock` POSIX /
  `msvcrt.locking` Windows) around plan RMW. Pros: drop-in fix, minimal
  refactor. Cons: cross-platform locking primitives differ; deadlock risk
  if exception during locked section.
- **Option (b)** — **Workers don't flip plan checkboxes; parent flips all
  atomically post-batch**. `_phase2_task_loop` worker mode skips
  `mark_and_advance` plan-write step (cursor advance only). Parent
  post-batch loops over completed task IDs + flips checkboxes in single
  RMW. Pros: single writer eliminates race entirely. Cons: changes
  per-task atomicity contract (plan-flip no longer atomic with chore
  commit per task in worker mode).
- **Option (c)** — **Per-worker scratch plan files merged by parent**.
  Each worker writes its own scratch plan file. Parent post-batch
  3-way-merges all scratch plans into main plan-tdd.md. Pros: workers
  preserve atomic-flip semantics. Cons: 3-way merge complexity; sidecar
  cleanup; ordering ambiguity.

Brainstorming evaluates atomicity preservation vs simplicity.

### 2.3 Item I-3 — Worker CLI flag forwarding (Pillar A PRIMARY CRITICAL)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (`_dispatch_tracks_concurrent`
  worker invocation builder, ~line 1564-1576)
- New tests in `tests/test_auto_cmd.py` (extend) for forwarding contract

**Empirical context (v1.0.4 design gap)**:

`_dispatch_tracks_concurrent` builds worker argv as
`[python, run_sbtdd.py, auto, --task-ids, T1,T3, --no-recursive]`. Operator
flags from parent's argv NOT forwarded:
- `--plugins-root <path>`
- `--magi-max-iterations <N>`
- `--magi-threshold <verdict>`
- `--verification-retries <N>`
- `--model-override <model>`

Workers run with DEFAULT config regardless of operator flags. Operator
sets `--magi-threshold=STRONG_GO` expecting strict gate; workers run with
default `GO_WITH_CAVEATS`.

**Implementation approach (relatively unambiguous)**:

In `_dispatch_tracks_concurrent`, when building worker argv, append the
parent's flag values for every relevant flag (introspect via `argparse`
namespace `ns`). Document explicit forwardable-flags list in helper
docstring. Forwarding test: pass `--magi-threshold=GO --verification-retries=5`
to parent + assert each worker subprocess receives those values (intercept
via mock `subprocess.Popen` + assert args).

Less brainstorming-debate than I-1/I-2; may merge into single Item.

### 2.4 Item D Q3 OPTION A — close_task_cmd._preflight code-side enforcement (Pillar B HIGH VALUE)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (`_preflight` extension)
- Modify: `skills/sbtdd/scripts/run_sbtdd.py` (argparse for `--skip-preflight`
  emergency override)
- New tests in `tests/test_close_task_cmd.py` (extend) — preflight enforcement
  + override behavior

**Empirical context (v1.0.4 iter-2 scope-trim Option D rationale)**:

v1.0.4 attempted Q3 Option B (3-touchpoint doc-only enforcement: SKILL.md
+ CLAUDE.local.md.template + writing-plans extension + soft-warning
tripwire). Loop 2 iter 1 surfaced 3-agent unanimous WARNING that doc-only
fails (v1.0.2 single touchpoint failed; v1.0.3 dogfood divergence; v1.0.4
multiplication doesn't address compliance). User selected Option D
scope-trim per spec sec.6.1 G2 ladder; Item D entirely DEFERRED to v1.0.5
LOCKED with Q3 OPTION A (code-side enforcement) commitment.

**Implementation outline**:

Extend `close_task_cmd._preflight` with new check:

```python
def _preflight(state: dict, project_root: Path | None = None) -> None:
    # ... existing checks ...

    # v1.0.5 Item D Q3 OPTION A: hard-block when phase advance gate bypassed
    start_sha = state.get("phase_started_at_commit")
    if start_sha:
        subjects = _git_log_between(start_sha, project_root=project_root)
        has_test = any(s.startswith("test:") for s in subjects)
        has_green = any(s.startswith(("feat:", "fix:")) for s in subjects)
        has_refactor = any(s.startswith("refactor:") for s in subjects)
        if not (has_test and has_green and has_refactor):
            raise PreconditionError(
                f"Phase advance gate bypassed: commit chain since "
                f"{start_sha} lacks test:/feat:|fix:/refactor: triplet. "
                f"Per SBTDD INV-1 + INV-5..7, each task close requires "
                f"close-phase invocation per Red/Green/Refactor phase. "
                f"Operator emergency override: --skip-preflight (audit-logged)."
            )
```

Plus `--skip-preflight` argparse flag for emergency operator override
(audit-logged via stderr breadcrumb).

**Acceptance criteria**:

1. Integration test: synthesize plan + commit chain WITHOUT TDD triplet →
   `close-task` raises `PreconditionError` with actionable message.
2. Backward-compat test: synthesize plan + commit chain WITH canonical
   triplet → `close-task` proceeds normally.
3. Override test: `--skip-preflight` flag bypasses check + emits audit
   breadcrumb.
4. v1.0.5 own-cycle empirical validation: some intentional bypass tasks
   verify hard-block fires; canonical close-phase tasks verify normal
   flow.

### 2.5 Item Pillar C.1 — Spec sec.8 stale risk-register sweep (Pillar C METHODOLOGY)

**Track**: pending Q1 partition decision (likely methodology / orchestrator).

**Archivos**:
- Modify: `sbtdd/spec-behavior-base.md` (sec.8 risk register clean-sweep)
- Modify: `sbtdd/spec-behavior.md` (post-brainstorming, normal flow updates)

**Empirical context**:

v1.0.4 cycle's iter-1 + iter-2 + iter-3 triage applied scope changes
(Items A+B simplification dropped env-var/isatty heuristic; Item D
deferred entirely; Path 3 architecture replaced Path 2). The original
spec-behavior-base.md sec.8 risk register R1 + R-NEW1 + R5 still
references eliminated v1.0.4 mechanisms (SBTDD_INTERACTIVE env var,
Item D 3-touchpoint enforcement, etc.). v1.0.4 ship documented as
"OBSOLETE" with strikethrough but text remains.

**Implementation**: clean-sweep stale references in v1.0.5 spec-base
upfront (this very document — applied during brainstorming sec.8 update).
Document principle: when
scope-trim or simplification eliminates a v1.0.X mechanism, the next
cycle's spec-base sweeps the references rather than carrying strikethrough
forward.

### 2.6 Item Pillar C.2 — Plan archaeology trim methodology (Pillar C METHODOLOGY)

**Track**: pending Q1 partition decision.

**Archivos**:
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add
  archaeology trim ship-time procedure)
- Modify: `templates/CLAUDE.local.md.template` (template guidance)
- New tests/smoke: `tests/test_plan_archaeology_trim_pattern.py`

**Empirical context (v1.0.4 ship Balthasar INFO #17)**:

v1.0.4 plan reached ~2200 lines (vs ~600-800 line baseline of v1.0.3).
Cause: iter-by-iter triage context preserved inline (iter-1 fixes,
iter-2 surgical fixes + scope-trim, iter-3 polish, iter-5 Path 3
re-implementation). v1.0.5 ship-time should collapse this iteration
archaeology from plan body into CHANGELOG narrative.

**Implementation outline**:

Methodology pattern:
1. At ship-time, extract iter-by-iter triage context from plan-tdd.md
   into CHANGELOG `[N.N.N]` Process notes section.
2. Trim plan-tdd.md to "active plan only" (current scope + tasks +
   acceptance criteria; no iter-1/iter-2/iter-3 archaeology).
3. Document procedure in `skills/sbtdd/SKILL.md` orchestrator rules
   + `templates/CLAUDE.local.md.template`.
4. Cross-artifact coherence test: plan-tdd.md byte size at ship <=
   threshold (e.g., 1000 lines) OR plan-tdd-org.md kept as immutable
   archaeology while plan-tdd.md = trimmed canonical.

This is methodology + doc + smoke test — relatively low complexity.

### 2.7 v1.0.5 own-cycle dogfood

**Track**: orchestrator (post Pillar A + Pillar B + Pillar C ship).

**Activities**:
1. **Items A+B+C v1.0.5 dogfood via `--parallel`**: dispatch v1.0.5
   own-cycle Track Alpha + Track Beta via `auto --parallel` (eats own
   dogfood; first cycle to use `--parallel` for production work).
2. **Item D Q3-A empirical validation**: some tasks intentionally bypass
   close-phase to verify hard-block; rest follow canonical to verify
   normal flow.
3. **Pre-merge gate clean WITHOUT INV-0**: v1.0.5 goal = re-establish
   pre-merge Loop 2 no-override streak from 1 cycle.

---

## 3. Restricciones y constraints duros

Todos los invariantes INV-0 a INV-37 preservados. v1.0.5 NO propone
nuevos invariantes (los items son mostly bug fixes + scope-trim follow-up).

Critical durante implementacion v1.0.5:

- **G1 binding HARD**: cap=3 sin INV-0 path en MAGI Checkpoint 2.
  6-cycle Checkpoint 2 no-override streak preserved. NO INV-0 override
  in Checkpoint 2.
- **G2 binding**: Loop 2 iter 3 verdict triggers scope-trim default.
  v1.0.5 multi-pillar bundle podria necesitar scope-trim si Loop 2 hits
  structural findings — defer Pillar C (spec sweep + plan trim methodology)
  a v1.0.6. Pillar A items son hard-LOCKED.
- **Pre-merge Loop 2 streak re-establishment**: v1.0.4 broke via INV-0.
  v1.0.5 goal = clean GO_WITH_CAVEATS full no-degraded WITHOUT INV-0.
  If unable, escalate to user before applying INV-0 override (per
  feedback memory `feedback_manual_synthesis_exceptional` discipline).
- **`--parallel` empirical dogfood requerida** post Pillar A ship: v1.0.5
  cycle MUST exercise own dogfood via `auto --parallel` to validate I-1+
  I-2+I-3 fixes empirically.

### Stack y runtime

Sin cambios vs v1.0.4:
- Python 3.9+, mypy --strict, cross-platform, stdlib-only en hot paths.
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
- G1 binding cap=3 HARD para Checkpoint 2 (CHANGELOG `[1.0.0]`,
  precedente cerrado v1.0.1+v1.0.2+v1.0.3+v1.0.4 streak; v1.0.5 preserves).

---

## 4. Funcionalidad requerida (SDD)

(F-series continua desde F161 v1.0.4; v1.0.5 starts at F162.)

### Item I-1 — Worker audit-trail clobber

**F162**. `auto_cmd._dispatch_tracks_concurrent` worker mode does NOT
overwrite parent's `.claude/auto-run.json`.

**F163**. Architectural choice (a/b/c per sec.2.1) implemented + documented.

**F164**. Parent post-batch audit-run.json contains: original start_time
+ aggregate task counts + per-worker completion records.

**F165**. INV-26 (audit-trail integrity) verified by integration test.

### Item I-2 — Plan checkbox lost-update race

**F166**. Concurrent workers calling `mark_and_advance` for disjoint task
IDs produce deterministic plan state (all checkboxes flipped to `[x]`).

**F167**. Architectural choice (a/b/c per sec.2.2) implemented + documented.

**F168**. Race regression test using real `multiprocessing.Process` +
shared barrier asserts all N flips visible (Windows-portable).

### Item I-3 — Worker CLI flag forwarding

**F169**. `_dispatch_tracks_concurrent` worker argv includes operator's
relevant flag values: `--plugins-root`, `--magi-max-iterations`,
`--magi-threshold`, `--verification-retries`, `--model-override`.

**F170**. Forwardable-flags list documented in helper docstring.

**F171**. Forwarding test asserts each worker subprocess receives parent's
flag values (mock `subprocess.Popen` + assert args).

### Item D Q3 OPTION A — close_task_cmd._preflight enforcement

**F172**. `close_task_cmd._preflight` raises `PreconditionError` when
commit chain since `phase_started_at_commit` lacks test:/feat:|fix:/refactor:
triplet.

**F173**. Error message provides operator-actionable guidance + cites
`phase_started_at_commit` SHA + canonical recovery path (close-phase per
phase from clean state).

**F174**. `--skip-preflight` argparse flag bypasses check + emits stderr
audit breadcrumb (operator emergency override).

**F175**. Backward-compat: normal close-phase + close-task flow with
canonical TDD triplet proceeds without trigger.

### Pillar C.1 — Spec sec.8 stale risk-register sweep

**F176**. `sbtdd/spec-behavior-base.md` sec.8 risk register sweeps
references to eliminated v1.0.4 mechanisms (SBTDD_INTERACTIVE env var,
Item D 3-touchpoint enforcement).

**F177**. v1.0.5 spec-behavior.md (post-brainstorming) reflects clean
risk register without strikethrough carry-forward.

### Pillar C.2 — Plan archaeology trim methodology

**F178**. `skills/sbtdd/SKILL.md` documents ship-time plan archaeology
trim procedure.

**F179**. `templates/CLAUDE.local.md.template` includes archaeology trim
guidance for destination projects.

**F180**. `tests/test_plan_archaeology_trim_pattern.py` smoke test asserts
SKILL.md + template both reference the procedure.

### Requerimientos no-funcionales (NF)

**NF42**. `make verify` runtime <= 200s soft target / 220s hard
(acknowledges v1.0.4 baseline 194s + new tests). v1.0.6 polish may reduce.

**NF43**. v1.0.4 plans (with state file post-v1.0.4 schema) parse
correctly; no migration required for v1.0.5.

**NF44**. Per-module coverage threshold preserved at 88% (no regression).

**NF45**. v1.0.5 own-cycle dogfood via `--parallel` empirical validation
of I-1+I-2+I-3 fixes.

**NF46**. v1.0.5 ship WITHOUT INV-0 override at pre-merge Loop 2
(re-establish streak).

---

## 5. Scope exclusions

Out-of-scope v1.0.5 (rolled forward a v1.0.6):

- I-4 stale INV-22 docstring (cosmetic)
- I-5 partition_by_collision DeprecationWarning CI handling
- `_run_single_task_isolated` removal candidate
- Real-world `--parallel` end-to-end dogfood validation (chicken-and-egg)
- Audit GAPs L1.0.4-A through L1.0.4-D (v1.0.3 carry-forward)
- `make verify` runtime polish below 165s NF-A target

Out-of-scope v1.0.5+ (rolled forward a v1.0.6+):

All items inherited from v1.0.4 carry-forward (per CHANGELOG `[1.0.4]`
Deferred sections + this document sec.1 "Out of scope v1.0.5+").

---

## 6. Criterios de aceptacion finales

v1.0.5 ship-ready cuando:

### 6.1 Functional Items I-1/I-2/I-3 + D Q3-A + C.1 + C.2

- **F1**. F162-F165: I-1 worker audit-trail integrity (per architectural
  choice) + INV-26 integration test.
- **F2**. F166-F168: I-2 plan checkbox race (per architectural choice) +
  multiprocessing race test.
- **F3**. F169-F171: I-3 worker CLI flag forwarding + forwarding test.
- **F4**. F172-F175: Item D Q3-A close_task_cmd._preflight enforcement +
  --skip-preflight override + 4 acceptance tests.
- **F5**. F176-F177: spec sec.8 stale risk-register clean-sweep.
- **F6**. F178-F180: plan archaeology trim methodology documented +
  smoke test.

### 6.2 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format + mypy
  --strict + coverage >= 88%, runtime <= 200s soft / 220s hard.
- **NF-B**. Tests baseline 1226 + 1 skipped + ~25-40 nuevos =
  ~1250-1265 final.
- **NF-C**. Cross-platform (Windows + POSIX) — I-2 race test validated
  on both via `multiprocessing.get_context("spawn")`.
- **NF-D**. Author/Version/Date headers en archivos modificados/nuevos.
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados.

### 6.3 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path. 6-cycle
  Checkpoint 2 no-override streak preserved.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  `GO_WITH_CAVEATS` full no-degraded **WITHOUT INV-0 override**
  (re-establish streak from 1 cycle post v1.0.4 break).
- **P3**. CHANGELOG `[1.0.5]` entry written con secciones Added /
  Changed / Process notes + Pillar A I-1+I-2+I-3 architectural choices
  + Pillar B Item D Q3-A enforcement + Pillar C.1 sweep + Pillar C.2
  methodology + dogfood findings.
- **P4**. Version bump 1.0.4 -> 1.0.5 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.5` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2 iter
  findings sin excepcion.
- **P7**. v1.0.5 own-cycle dogfood via `--parallel` empirically validates
  I-1/I-2/I-3 fixes.
- **P8**. Item D Q3-A empirical validation: intentional-bypass test cases
  verify hard-block; canonical close-phase test cases verify normal flow.

### 6.4 Distribution

- **D1**. Plugin instalable desde `BolivarTech/sbtdd-workflow`
  marketplace (`bolivartech-sbtdd`).
- **D2**. Cross-artifact coherence tests actualizados (CHANGELOG,
  CLAUDE.md, README, SKILL.md mention v1.0.5 ship + 6 items + dogfood
  observations).
- **D3**. Documented:
  - I-1/I-2/I-3 architectural choices in CHANGELOG + helper docstrings.
  - Item D Q3-A `--skip-preflight` flag in run_sbtdd help + README.
  - Plan archaeology trim procedure in SKILL.md + CLAUDE.local.md.template.

---

## 7. Dependencias externas nuevas

Runtime: ninguna nueva. Dev: ninguna nueva.

---

## 8. Risk register v1.0.5

- **R1**. I-1 architectural choice (sidecar / stdout / single-writer) may
  surface trade-offs not visible at brainstorming. Mitigation: brainstorming
  Q1 evaluates 3 options; pick simplest correct.
- **R2**. I-2 cross-process locking primitives differ POSIX vs Windows.
  Mitigation: Option (b) parent-owns-flips eliminates locking entirely;
  Option (c) per-worker scratch files cross-platform via os.replace.
- **R3**. Item D Q3-A `_preflight` hard-block may surprise existing operators
  in non-SBTDD workflows. Mitigation: `--skip-preflight` flag + clear error
  message + audit breadcrumb. Defer broad rollout if v1.0.5 dogfood surfaces
  issues.
- **R4**. Plan archaeology trim methodology is doc + smoke; if methodology
  pattern proves incomplete, v1.0.6 refinement.
- **R5**. v1.0.5 own-cycle dogfood via `--parallel` may surface I-1/I-2/I-3
  fix gaps not caught by tests. Mitigation: dogfood is non-blocking for ship
  (acceptance via tests primarily; dogfood empirical is bonus); if dogfood
  fails, document + roll forward to v1.0.6 patch.
- **R6**. Pre-merge Loop 2 streak re-establish goal may not be achievable
  if cycle surfaces fundamental architectural questions. Mitigation: G2
  scope-trim ladder (defer Pillar C first, then Pillar B Item D); INV-0
  remains available but escalated to user before application.

---

## 9. Referencias

- Contrato autoritativo: `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.4 ship record: tag `v1.0.4` (commit `87f14a3`); merge `b1c5262`
  on `main`.
- v1.0.3 ship record: tag `v1.0.3` (commit `39a9c18`); merge `0aeff7d`
  on `main`.
- v1.0.4 LOCKED carry-forward to v1.0.5 per CHANGELOG `[Unreleased]`
  section (committed `6320124` + finalized in `[1.0.4]` section
  committed `87f14a3`).
- v1.0.5 LOCKED memories:
  - `project_v105_parallel_correctness_locked.md` (CRITICAL —
    I-1/I-2/I-3 details + acceptance criteria).
  - `project_v104_shipped.md` (full v1.0.4 ship record + cycle metrics).
- v1.0.6 deferred backlog: I-4 cosmetic + I-5 CI handling +
  partition_by_collision deletion + real-world dogfood + audit GAPs +
  make verify polish + all v1.0.4 carry-forward inherited items.
- Branch: trabajo en `feature/v1.0.5-bundle` (branched off `main` HEAD
  `b1c5262` = v1.0.4 merge commit).

---

## Nota sobre siguiente paso

Este archivo cumple INV-27 (cero matches uppercase placeholder
word-boundary verificable con regex). Listo como input para
`/brainstorming`.

**Methodology v1.0.5 own-cycle**: per CLAUDE.local.md sec.1 Flujo de
especificacion + v1.0.4 Process notes precedent, brainstorming se correra
en sesion interactiva (esta sesion) via Skill tool in-session. NO via
`claude -p` subprocess (preserve consistency con v1.0.1+v1.0.2+v1.0.3
+v1.0.4 precedent — v1.0.4 Items A+B prevent subprocess-incompatible
skills from spawning, but interactive Skill invocation in-session is the
canonical path).

**Hybrid methodology continued**: Opcion A manual `run_magi.py` for
Checkpoint 2 dispatch per v1.0.2+v1.0.3+v1.0.4 precedent.
`/sbtdd spec --resume-from-magi` Activity E' validation may exercise
v1.0.5 own-cycle (deferred from v1.0.3 + v1.0.4); chicken-and-egg now
resolved per v1.0.4 Items A+B ship.

Decisiones pendientes clave para brainstorming (Q1-Q5 estimated):

1. **Subagent partition (Q1)**: 6 items (I-1, I-2, I-3, D Q3-A, C.1
   sweep, C.2 methodology). Posibles particiones disjoint:
   - **Single subagent sequential**: ~3-4 dias wall-time.
   - **2-track parallel** (precedent v1.0.4): Track Alpha = I-1+I-2+I-3
     coupled (worker correctness in auto_cmd.py + close_task_cmd.py);
     Track Beta = D Q3-A + C.1 + C.2 (close_task_cmd.py preflight + spec
     sweep + methodology). Risk: Track Alpha + Beta both touch
     close_task_cmd.py — surface OVERLAP. Brainstorming evaluates partition.
   - **3-track parallel**: Track Alpha = I-1+I-2+I-3 (auto_cmd.py worker
     paths); Track Beta = D Q3-A (close_task_cmd.py preflight); Track
     Gamma = C.1+C.2 (spec sweep + methodology docs). 100% disjoint
     surfaces. Higher coordination overhead but safer.
   - **`--parallel` self-dispatch dogfood**: dispatch v1.0.5 own-cycle
     via `auto --parallel` (eats own dogfood). Requires Pillar A items
     to land FIRST (chicken-and-egg) — methodology question.

2. **I-1 architectural choice (Q2)**: option (a) sidecar / (b) stdout
   signal / (c) single-writer-parent. Brainstorming evaluates.

3. **I-2 architectural choice (Q3)**: option (a) cross-process lock /
   (b) parent-owns-flips / (c) per-worker scratch. Brainstorming
   evaluates atomicity preservation vs simplicity.

4. **Item D Q3-A `--skip-preflight` flag scope (Q4)**: should override
   bypass be (a) opt-in flag operators must pass / (b) env var
   `SBTDD_SKIP_PREFLIGHT=1` / (c) both. Brainstorming evaluates UX.

5. **MAGI Checkpoint 2 budget allocation (Q5)**: bundle multi-pillar.
   Esperamos converger en 1-2 iters; iter 3 triggers G2 scope-trim
   default. Defer Pillar C (sweep + methodology) a v1.0.6 first; then
   Pillar B (Item D Q3-A); Pillar A I-1+I-2+I-3 hard-LOCKED.

Brainstorming refinara estas decisiones basado en complejidad, risk, y
empirical findings de v1.0.0+v1.0.1+v1.0.2+v1.0.3+v1.0.4 precedents.
