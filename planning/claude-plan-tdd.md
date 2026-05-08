# v1.0.5 Production-grade `--parallel` + Item D Q3-A code-side enforcement Implementation Plan

> Generado 2026-05-08 a partir de sbtdd/spec-behavior.md v1.0.5 via
> superpowers:writing-plans skill (interactive session, brainstorming
> Q1+Q2+Q3+Q4+Q5 resolved). Frontmatter required by spec_lint R5.
>
> v1.0.5 ships 3 focused pillars:
> - Pillar A PRIMARY (LOCKED CRITICAL): I-1 + I-2 + I-3 production-grade
>   `--parallel` correctness gaps closure
> - Pillar B LOCKED (HIGH VALUE): Item D Q3 OPTION A code-side
>   enforcement via `close_task_cmd._preflight` HARD-BLOCK
> - Pillar C LOCKED (METHODOLOGY): C.1 spec sec.8 sweep (APPLIED INLINE
>   in spec) + C.2 plan archaeology trim methodology
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax (open + closed bracket forms) for tracking.
>
> **Iter 1 Checkpoint 2 triage applied 2026-05-08** (verdict
> GO_WITH_CAVEATS 3-0, 5 CRITICAL + 12 WARNING; full triage
> rationale in spec-behavior.md header). Plan deltas applied:
> - **CRITICAL #1+#3** (mel+cas, fabricated flips): Task 3 Step 4
>   `_apply_flips_for_task_ids` rewritten as `_apply_flips_from_diff`
>   (derives flips from scratch-vs-main diff; no longer takes
>   `task_ids` param; partial worker failure no longer fabricates).
>   Added escenario I2-3b regression test.
> - **CRITICAL #2** (mel, regex cross-boundary): Task 3 Step 4
>   `_flip_checkbox` regex anchored to next `### Task` header (or
>   EOF) using `_TASK_HEADER_RE` walker. Added escenario I2-5
>   regression test.
> - **CRITICAL #4** (cas, architectural): Track Alpha + Track Beta
>   "cero overlap" Q1 claim was function-level FALSE — both wired
>   into `_dispatch_tracks_concurrent`. Resolved by **Track Alpha
>   T1 Step 5 owns ALL `_dispatch_tracks_concurrent` post-batch
>   wiring** (audit-merge + scratch-merge + reaper); Track Beta T3
>   Step 5 = NO `auto_cmd.py` modification (helper-only). Surfaces
>   become file-level disjoint.
> - **CRITICAL #5** (cas, wrong commit-window): Task 4 Step 4
>   `_preflight` triplet check scoped to "since last `chore: mark
>   task` commit" (not `phase_started_at_commit`). Added
>   `_last_chore_task_close_sha` helper. Updated escenarios D-1+D-2;
>   added D-2b first-task branch-root case.
> - **WARNINGs** addressed: duplicate `test_d4` renamed (now
>   `test_d4_no_chore_commit_first_task_branch_root_boundary` +
>   `test_d5_partial_triplet_raises`); orphan reaper added to
>   Task 1 Step 5 (escenario I1-6); race regression test
>   strengthened (real `multiprocessing.Process` + spawn context +
>   Barrier-synchronized RMW + 50× repeat); DRY atomic-write
>   acknowledged via Task 1 Step 8 / Task 3 Step 8 refactor pass.
>
> **Iter 2 Checkpoint 2 triage applied 2026-05-08** (verdict
> GO_WITH_CAVEATS 3-0 with 6 CRITICAL — **iter-2 CRITICAL trigger
> FIRES**; pre-staged response invoked). Plan deltas:
> - **Pillar C (Track Gamma T5) DEFERRED to v1.0.6** per pre-staged
>   G2 ladder. Plan now ships 4 plan tasks (T1+T2 Track Alpha,
>   T3+T4 Track Beta) instead of 5.
> - **Plan T3 Step 4 spec/plan drift FIXED** (iter-1 fix applied
>   to spec but not plan code block — operator editing miss):
>   plan T3 Step 4 implementation code rewritten verbatim from spec
>   sec.2.2 step 3+4 with anchored `_flip_checkbox` (`_TASK_HEADER_RE`
>   walker) + `_apply_flips_from_diff` (no `task_ids` param) +
>   `_section_has_flipped` + `_iter_task_ids` helpers.
> - **Track Alpha T1 → Track Beta T3 ordering hardened**: dropped
>   "stub the import temporarily" fallback. Plan invariants block
>   adds explicit subagent-dispatch-ordering constraint: Track Beta
>   T3 MUST land BEFORE Track Alpha T1 Step 5 wiring step. T1
>   Steps 1-4 + T2 can run parallel with Track Beta T3+T4.
> - **Plan T3 Step 1 Red phase** extended with explicit test
>   methods: `test_i2_3b_partial_worker_failure_no_fabrication` +
>   `test_i2_5_anchored_flip_checkbox_respects_section_boundaries`.
> - **Plan I2-4 race test**: explicit `for _ in range(50):` repeat
>   wrapping multiprocessing barrier-synchronized RMW; assert no
>   flip lost across all 50 iterations.
> - **Plan T1 Step 8 + T3 Step 8** atomic-write DRY consolidation
>   made UNCONDITIONAL: extract shared `_atomic_write_json` to
>   `state_file.py`; both modules import from there.
> - **`_reap_orphans` race-safety**: mtime/lock guard added — only
>   reaps files older than dispatcher start time + 5min margin.
> - **`_last_chore_task_close_sha` task-ID verification**: optional
>   second-line check parses task-ID from chore subject; mismatch
>   surfaces diagnostic info in PreconditionError.

**Goal:** Ship v1.0.5 — close v1.0.4 LOCKED commitments documented in CHANGELOG `[Unreleased]` (I-1/I-2/I-3 production-grade `--parallel` correctness gaps) + ship Item D Q3 OPTION A code-side enforcement (replaces v1.0.4's scope-trimmed Q3 Option B doc-only attempt). **Pillar C plan archaeology trim methodology DEFERRED to v1.0.6** per iter-2 Checkpoint 2 CRITICAL trigger (2026-05-08). **4 plan tasks across 2 parallel subagent tracks** (Alpha T1+T2; Beta T3→T4 sequential); 3 mid-cycle methodology activities (production-grade `--parallel` integration test + Item D Q3-A empirical validation + pre-merge gate clean WITHOUT INV-0).

**Architecture:** 3-track parallel dispatch with disjoint surfaces. Track Alpha (auto_cmd.py only, 2 sequential tasks I-1 → I-3) implements per-worker sidecar audit-trail pattern + worker CLI flag forwarding. Track Beta (close_task_cmd.py + run_sbtdd.py argparse, 2 sequential tasks I-2 → D Q3-A) implements per-worker scratch plan flip-merge pattern + close_task_cmd._preflight HARD-BLOCK with --skip-preflight emergency override. Track Gamma (SKILL.md + template + smoke test, 1 task) implements plan archaeology trim methodology documentation (C.1 spec sweep already applied inline in spec-behavior.md sec.8). Manual orchestrator dispatch via Agent tool fan-out (NOT auto --parallel self-dispatch — chicken-and-egg avoidance per Q1 Option C).

**State file write serialization**: Track Alpha owns Tasks 1-2 (sequential close). Track Beta owns Tasks 3-4 (sequential close). State file `current_task_id` advances 1 → 2 → 3 → 4 → done. `state_file.save()` atomic `os.replace` (existing v0.5.0 pattern) ensures no partial writes. Tracks have disjoint task IDs and disjoint file surfaces (Track Gamma deferred to v1.0.6); concurrent close-task invocations are safe per v0.4.0+v0.5.0+v1.0.0+v1.0.2+v1.0.3+v1.0.4 precedent.

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict, stdlib-only on hot paths. TDD-Guard active in same worktree (parallel-safe per spec sec.3 since Tracks have disjoint surfaces). Brainstorming refinements 2026-05-08: Q1 = 3-track parallel disjoint (Alpha I-1+I-3, Beta I-2+D Q3-A, Gamma C.2); Q2 = per-worker sidecar I-1; Q3 = per-worker scratch I-2; Q4 = `--skip-preflight` flag-only emergency override; Q5 = strict no-INV-0 stance.

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-08`.
- **Phase close protocol (Q3 Option B v1.0.4 mandate, preserved + soon-to-be-enforced via Item D Q3-A)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each Red/Green/Refactor verify-clean. Manual `git commit` per phase BYPASSES the phase-advance + state-file update + verification gate; close-task v1.0.5 will HARD-BLOCK once Item D Q3-A lands (Track Beta Task 4).
- **Task close protocol**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review` after Refactor close-phase. Use `--skip-spec-review` to bypass INV-31 spec-reviewer dispatch (~1-2 min/task overhead acceptable but not required for these infrastructure items).
- **Track Beta sequential ordering MANDATORY**: Task 3 (I-2) lands FIRST. Task 4 (D Q3-A) lands AFTER Task 3 completes. Both modify `close_task_cmd.py` — within-track sequential coordination required.
- **Cross-track dispatch-ordering invariant (iter-2 CRITICAL #4 hardening)**: Track Beta T3 MUST land in git BEFORE Track Alpha T1 Step 5 (the wiring step that imports `from close_task_cmd import _merge_scratch_plans`). Track Alpha T1 Steps 1-4 (sidecar pattern, no cross-track import) + T2 (flag forwarding) CAN run in parallel with Track Beta T3+T4. Orchestrator MUST sequence dispatch: dispatch Track Beta subagent FIRST + wait for T3 close commit → THEN dispatch Track Alpha subagent (which executes T1 Steps 1-4 → T2 → T1 Step 5 in order). The "stub temporarily and rebase" fallback is RETRACTED — too brittle, risks landing broken intermediate state.
- INV-37 composite-signature tripwire preserved unchanged in all paths.
- Item C v1.0.2 spec_lint gate (R1-R5) preserved unchanged.
- v1.0.4 Items A+B membership-based subprocess gate preserved unchanged.
- v1.0.4 Path 3 `--parallel` architecture (`partition_by_tracks` + `_dispatch_tracks_concurrent` + `--task-ids` + `--no-recursive`) preserved unchanged. v1.0.5 EXTENDS via Track Alpha (I-1+I-3) + Track Beta (I-2) post-batch merge helpers.

**Commit prefix map per phase** (from `CLAUDE.local.md` §5):

| Phase | Prefix | Closer |
|-------|--------|--------|
| Red (failing test) | `test:` | `close-phase` |
| Green (impl) | `feat:` (new module/feature) or `fix:` (bug fix) | `close-phase` |
| Refactor | `refactor:` | `close-phase` |
| Task close | `chore:` (automated) | `close-task --skip-spec-review` |

---

## Track Alpha — I-1 worker audit-trail sidecar + I-3 CLI flag forwarding (Subagent #1, sequential T1 → T2)

**Owner**: Subagent #1 dispatched from orchestrator.
**Surfaces** (file-disjoint with Track Beta post iter-2 CRITICAL #4 architectural fix; Track Gamma deferred to v1.0.6):
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Extend: `tests/test_auto_cmd.py`

**Wall-time estimated**: ~1 day.

### Task 1: Item I-1 — Per-worker sidecar audit-trail pattern

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_audit_sidecar_path` helper + worker-mode `_write_audit` redirect + `_merge_audit_sidecars` post-batch helper + `_dispatch_tracks_concurrent` post-batch hook)
- Test: `tests/test_auto_cmd.py` (extend with `class TestPerWorkerSidecarAudit`)

Covers escenarios I1-1 through I1-5 from spec sec.4.1.

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_auto_cmd.py`:

```python
class TestPerWorkerSidecarAudit:
    """v1.0.5 Item I-1 escenarios I1-1 through I1-5 — per-worker sidecar pattern."""

    def test_i1_1_worker_mode_redirects_audit_to_sidecar(self, tmp_path, monkeypatch):
        """I1-1: worker mode redirects audit write to sidecar."""
        from auto_cmd import _write_audit, _audit_sidecar_path
        import argparse

        ns = argparse.Namespace(no_recursive=True, task_ids="1,3")
        audit_data = {"start_time": "2026-05-08T10:00:00Z", "tasks": ["1", "3"]}
        (tmp_path / ".claude").mkdir()

        _write_audit(audit_data, tmp_path, ns)

        sidecar = _audit_sidecar_path(("1", "3"), tmp_path)
        assert sidecar.exists()
        assert not (tmp_path / ".claude" / "auto-run.json").exists()
        loaded = json.loads(sidecar.read_text(encoding="utf-8"))
        assert loaded == audit_data

    def test_i1_2_orchestrator_mode_writes_canonical_audit(self, tmp_path, monkeypatch):
        """I1-2: orchestrator mode writes canonical audit-run.json."""
        from auto_cmd import _write_audit
        import argparse

        ns = argparse.Namespace(no_recursive=False, task_ids=None)
        audit_data = {"start_time": "2026-05-08T10:00:00Z", "tasks": ["1", "2", "3", "4"]}
        (tmp_path / ".claude").mkdir()

        _write_audit(audit_data, tmp_path, ns)

        canonical = tmp_path / ".claude" / "auto-run.json"
        assert canonical.exists()
        loaded = json.loads(canonical.read_text(encoding="utf-8"))
        assert loaded == audit_data

    def test_i1_3_parent_post_batch_merges_sidecars(self, tmp_path):
        """I1-3: parent post-batch merges sidecars + cleans up."""
        from auto_cmd import _audit_sidecar_path, _merge_audit_sidecars

        (tmp_path / ".claude").mkdir()
        # Pre-dispatch parent audit
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(json.dumps({"start_time": "2026-05-08T10:00:00Z"}), encoding="utf-8")
        # Three workers wrote sidecars
        sidecar_a = _audit_sidecar_path(("1", "3"), tmp_path)
        sidecar_b = _audit_sidecar_path(("2",), tmp_path)
        sidecar_c = _audit_sidecar_path(("4",), tmp_path)
        sidecar_a.write_text(json.dumps({"task_ids": ["1", "3"], "completed_at": "T1"}), encoding="utf-8")
        sidecar_b.write_text(json.dumps({"task_ids": ["2"], "completed_at": "T2"}), encoding="utf-8")
        sidecar_c.write_text(json.dumps({"task_ids": ["4"], "completed_at": "T3"}), encoding="utf-8")

        merged = _merge_audit_sidecars([["1", "3"], ["2"], ["4"]], tmp_path)

        assert merged["start_time"] == "2026-05-08T10:00:00Z"
        assert merged["aggregate_task_count"] == 4
        assert len(merged["per_worker"]) == 3
        # Sidecars cleaned up
        assert not sidecar_a.exists()
        assert not sidecar_b.exists()
        assert not sidecar_c.exists()

    def test_i1_4_missing_sidecar_handled_gracefully(self, tmp_path):
        """I1-4: worker terminated before sidecar write → graceful no_audit_data entry."""
        from auto_cmd import _merge_audit_sidecars

        (tmp_path / ".claude").mkdir()
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(json.dumps({"start_time": "2026-05-08T10:00:00Z"}), encoding="utf-8")
        # No sidecar files exist (workers crashed before write)

        merged = _merge_audit_sidecars([["1"], ["2"]], tmp_path)

        assert len(merged["per_worker"]) == 2
        for entry in merged["per_worker"]:
            assert entry["status"] == "no_audit_data"
            assert "Worker terminated before sidecar write" in entry["note"]

    def test_i1_5_inv26_audit_trail_integrity(self, tmp_path):
        """I1-5: INV-26 audit-trail integrity post-batch (full round-trip)."""
        from auto_cmd import _audit_sidecar_path, _merge_audit_sidecars

        (tmp_path / ".claude").mkdir()
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(
            json.dumps({"start_time": "2026-05-08T10:00:00Z", "planned_tasks": ["1", "2", "3", "4"]}),
            encoding="utf-8",
        )
        # 2 tracks completed
        sidecar_a = _audit_sidecar_path(("1", "3"), tmp_path)
        sidecar_b = _audit_sidecar_path(("2", "4"), tmp_path)
        sidecar_a.write_text(json.dumps({"task_ids": ["1", "3"], "completed_at": "T1"}), encoding="utf-8")
        sidecar_b.write_text(json.dumps({"task_ids": ["2", "4"], "completed_at": "T2"}), encoding="utf-8")

        merged = _merge_audit_sidecars([["1", "3"], ["2", "4"]], tmp_path)

        # INV-26 verified: original start_time + aggregate_task_count + per_worker present
        assert merged["start_time"] == "2026-05-08T10:00:00Z"  # original preserved
        assert merged["aggregate_task_count"] == 4
        assert len(merged["per_worker"]) == 2
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestPerWorkerSidecarAudit -v`
Expected: 5/5 FAIL with `AttributeError: module 'auto_cmd' has no attribute '_audit_sidecar_path'` (and same for `_merge_audit_sidecars`).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Red phase verify-clean confirms tests fail for the correct reason (missing implementation, not import error). Atomic `test:` commit landed. State file advances `current_phase: red → green`.

#### Green Phase

- [x] **Step 4: Implement `_audit_sidecar_path` + `_write_audit` redirect + `_merge_audit_sidecars`**

Modify `skills/sbtdd/scripts/auto_cmd.py`. Add helpers:

```python
import hashlib

def _audit_sidecar_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
    """Per-worker audit sidecar path.

    v1.0.5 Item I-1: deterministic name per task-IDs hash. Each worker
    writes its audit to its own sidecar; parent post-batch merges all
    sidecars into canonical auto-run.json.

    Args:
        task_ids: Sorted tuple of task IDs assigned to this worker.
        project_root: Project root path.

    Returns:
        Path to sidecar file.
    """
    digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
    return project_root / ".claude" / f"auto-run-track-{digest}.json"


def _write_audit(audit: dict, project_root: Path, ns: argparse.Namespace) -> None:
    """Write audit record. v1.0.5 Item I-1: workers redirect to sidecar.

    Worker mode (--no-recursive + --task-ids) → writes per-worker sidecar.
    Orchestrator mode → writes canonical .claude/auto-run.json.
    """
    if getattr(ns, "no_recursive", False) and getattr(ns, "task_ids", None):
        task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
        audit_path = _audit_sidecar_path(task_ids_tuple, project_root)
    else:
        audit_path = project_root / ".claude" / "auto-run.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(audit_path, audit)


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomic JSON write via write-temp + os.replace (cross-platform)."""
    import json
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _merge_audit_sidecars(
    tracks: list[list[str]], project_root: Path
) -> dict:
    """Parent post-batch: merge per-worker sidecars into canonical audit.

    v1.0.5 Item I-1: collects per-worker sidecar files (created by workers
    during dispatch) into the canonical auto-run.json. Preserves parent's
    pre-dispatch record + adds per-worker completion info + aggregate
    task count. Cleans up sidecar files post-merge.

    Args:
        tracks: List of dispatched track task-ID lists.
        project_root: Project root.

    Returns:
        Merged audit dict.
    """
    import json
    canonical_path = project_root / ".claude" / "auto-run.json"
    canonical = (
        json.loads(canonical_path.read_text(encoding="utf-8"))
        if canonical_path.exists()
        else {}
    )
    per_worker: list[dict] = []
    for task_ids in tracks:
        sidecar_path = _audit_sidecar_path(tuple(sorted(task_ids)), project_root)
        if sidecar_path.exists():
            sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            per_worker.append(sidecar_data)
            sidecar_path.unlink(missing_ok=True)
        else:
            per_worker.append({
                "task_ids": list(task_ids),
                "status": "no_audit_data",
                "note": "Worker terminated before sidecar write",
            })
    canonical["per_worker"] = per_worker
    canonical["aggregate_task_count"] = sum(len(tids) for tids in tracks)
    return canonical
```

Confirm `import os`, `import json`, `import argparse`, `from pathlib import Path` are present at top of file.

- [x] **Step 5: Wire `_merge_audit_sidecars` AND `_merge_scratch_plans` into `_dispatch_tracks_concurrent` (iter-1 CRITICAL #4: Track Alpha owns ALL post-batch hooks) + `_reap_orphans` pre-flight (iter-1 WARNING fix)**

Modify `_dispatch_tracks_concurrent` post-batch:

```python
def _dispatch_tracks_concurrent(
    tracks: list[list[str]],
    effective_workers: int,
    project_root: Path,
    ns: argparse.Namespace,
) -> None:
    """... existing dispatch logic ..."""
    # v1.0.5 iter-1 WARNING + iter-2 race-safety fix: reap orphan
    # sidecar/scratch from prior crashed run BEFORE new dispatch
    # (prevents stale data contamination). mtime guard avoids
    # clobbering concurrent SBTDD instances. See escenario I1-6.
    import time
    _reap_orphans(project_root, dispatch_start_epoch=time.time())

    # ... existing thread-pool + Queue + Popen workers ...
    # ... wait all workers complete ...

    # v1.0.5 Item I-1: merge per-worker audit sidecars into canonical
    merged_audit = _merge_audit_sidecars(tracks, project_root)
    _atomic_write_json(project_root / ".claude" / "auto-run.json", merged_audit)

    # v1.0.5 Item I-2 (iter-1 CRITICAL #4: wired here per architectural fix —
    # Track Alpha owns ALL _dispatch_tracks_concurrent post-batch hooks;
    # Track Beta provides the helper in close_task_cmd.py only):
    from close_task_cmd import _merge_scratch_plans
    _merge_scratch_plans(tracks, project_root)


def _reap_orphans(project_root: Path, dispatch_start_epoch: float) -> None:
    """v1.0.5 iter-1 WARNING + iter-2 race-safety fix: clean stale
    per-worker sidecar/scratch files from a prior crashed run.

    iter-2 race-safety mtime guard: only reaps files older than
    dispatch_start_epoch - 300s (5min margin). This avoids clobbering
    sidecars/scratches from a CONCURRENT SBTDD instance that started
    just before this dispatch (iter-2 cas WARNING). Concurrent
    instances are rare but possible (operator running parallel
    `--parallel` jobs). Idempotent: safe to invoke multiple times.
    """
    import time

    claude_dir = project_root / ".claude"
    if not claude_dir.exists():
        return
    cutoff = dispatch_start_epoch - 300.0  # 5min margin
    for pattern in ("auto-run-track-*.json", "plan-scratch-*.md"):
        for stale in claude_dir.glob(pattern):
            try:
                mtime = stale.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                stale.unlink(missing_ok=True)
```

Caller updates: `_dispatch_tracks_concurrent` invokes as
`_reap_orphans(project_root, time.time())` at top of dispatch.

**Architectural note (iter-1 CRITICAL #4 fix)**: original Q1
"cero overlap" claim was function-level FALSE — both Track Alpha
and Track Beta needed wiring into `_dispatch_tracks_concurrent`.
Resolved by **consolidating ALL post-batch hook wiring into Track
Alpha T1** (this step). Track Beta T3 provides
`_merge_scratch_plans` as a pure helper in `close_task_cmd.py`
(see Task 3 Step 4 + Step 5 helper-only note). Result:
file-level disjoint surfaces (Track Alpha touches only
`auto_cmd.py`; Track Beta touches only `close_task_cmd.py` +
`run_sbtdd.py` argparse).

**Coordination**: Track Alpha T1 imports
`close_task_cmd._merge_scratch_plans` — soft dependency requiring
Track Beta T3 commits to land first OR Track Alpha T1 stubs
the import temporarily. Orchestrator dispatches Track Beta T3
before Track Alpha T1 wiring step (within-track sequential per
Track Alpha's I-1 sidecar-only step → I-3 forwarding → wiring
via Step 5 final).

- [x] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestPerWorkerSidecarAudit -v`
Expected: 5/5 PASS + reaper test (escenario I1-6) passes.

Run: `make verify`
Expected: All checks green (pytest, ruff check, ruff format, mypy).

- [x] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Green phase verify-clean passes. Atomic `feat:` commit landed (e.g. `feat: per-worker sidecar audit-trail pattern for v1.0.5 Item I-1`).

#### Refactor Phase

- [x] **Step 8: Refactor — review for duplication / extract helpers if needed**

If `_atomic_write_json` already existed in another module (e.g., `state_file.py`), import + use it instead of duplicating. Otherwise, leave the new helper in place. Document choice in commit message.

- [x] **Step 9: Run tests to verify still PASS**

Run: `make verify`
Expected: Clean.

- [x] **Step 10: close-phase Refactor**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `refactor:` commit landed (or `--allow-empty` if no actual refactor).

- [x] **Step 11: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 1 checkboxes flipped to `[x]`. Atomic `chore: mark task 1 complete` commit. State file advances `current_task_id: 1 → 2`.

---

### Task 2: Item I-3 — Worker CLI flag forwarding via `_FORWARDABLE_FLAGS` + `_build_worker_argv`

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_FORWARDABLE_FLAGS` MappingProxyType + `_build_worker_argv` helper + `_dispatch_tracks_concurrent` argv builder integration)
- Test: `tests/test_auto_cmd.py` (extend with `class TestWorkerFlagForwarding`)

Covers escenarios I3-1 through I3-3 from spec sec.4.3.

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_auto_cmd.py`:

```python
class TestWorkerFlagForwarding:
    """v1.0.5 Item I-3 escenarios I3-1 through I3-3 — worker CLI flag forwarding."""

    def test_i3_1_forwardable_flags_propagate_to_worker_argv(self):
        """I3-1: forwardable flags propagate to worker argv with non-None values."""
        from auto_cmd import _build_worker_argv
        import argparse

        ns = argparse.Namespace(
            plugins_root=None,
            magi_max_iterations=None,
            magi_threshold="GO",
            verification_retries=5,
            model_override=None,
        )
        argv = _build_worker_argv(["1", "3"], ns)

        assert "--task-ids" in argv
        assert "1,3" in argv
        assert "--no-recursive" in argv
        assert "--magi-threshold" in argv
        assert "GO" in argv
        assert "--verification-retries" in argv
        assert "5" in argv
        # Non-None flags propagated; None flags omitted
        assert "--plugins-root" not in argv
        assert "--magi-max-iterations" not in argv
        assert "--model-override" not in argv

    def test_i3_2_missing_flags_omit_from_worker_argv(self):
        """I3-2: all-None flags produce minimal argv (no empty/None flags)."""
        from auto_cmd import _build_worker_argv
        import argparse

        ns = argparse.Namespace(
            plugins_root=None,
            magi_max_iterations=None,
            magi_threshold=None,
            verification_retries=None,
            model_override=None,
        )
        argv = _build_worker_argv(["1", "3"], ns)

        # Only the minimal set: python, run_sbtdd.py, auto, --task-ids, IDs, --no-recursive
        assert "--task-ids" in argv
        assert "--no-recursive" in argv
        for flag_name in ("--plugins-root", "--magi-max-iterations", "--magi-threshold",
                           "--verification-retries", "--model-override"):
            assert flag_name not in argv

    def test_i3_3_documented_forwardable_list_matches(self):
        """I3-3: _FORWARDABLE_FLAGS matches documented helper docstring."""
        from auto_cmd import _FORWARDABLE_FLAGS, _build_worker_argv

        # Documented forwardable list (per spec sec.2.3)
        expected_keys = {
            "plugins_root",
            "magi_max_iterations",
            "magi_threshold",
            "verification_retries",
            "model_override",
        }
        assert set(_FORWARDABLE_FLAGS.keys()) == expected_keys

        # Helper docstring mentions all forwardable flag names
        docstring = _build_worker_argv.__doc__ or ""
        for flag_value in _FORWARDABLE_FLAGS.values():
            assert flag_value in docstring, f"Helper docstring missing: {flag_value}"
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestWorkerFlagForwarding -v`
Expected: 3/3 FAIL with `ImportError` (helpers don't exist yet).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `test:` commit landed.

#### Green Phase

- [x] **Step 4: Implement `_FORWARDABLE_FLAGS` + `_build_worker_argv`**

Modify `skills/sbtdd/scripts/auto_cmd.py`:

```python
from types import MappingProxyType
from typing import Mapping

_FORWARDABLE_FLAGS: Mapping[str, str] = MappingProxyType({
    # argparse-namespace-attr → CLI-flag-name
    "plugins_root": "--plugins-root",
    "magi_max_iterations": "--magi-max-iterations",
    "magi_threshold": "--magi-threshold",
    "verification_retries": "--verification-retries",
    "model_override": "--model-override",
})


def _build_worker_argv(task_ids: list[str], ns: argparse.Namespace) -> list[str]:
    """Build subprocess argv for a worker, forwarding parent's CLI flags.

    v1.0.5 Item I-3: forwards _FORWARDABLE_FLAGS values from parent's
    argparse namespace to worker subprocess. Documented forwardable list:
    --plugins-root, --magi-max-iterations, --magi-threshold,
    --verification-retries, --model-override.

    Args:
        task_ids: Task IDs assigned to this worker.
        ns: Parent's argparse namespace.

    Returns:
        Worker argv list ready for subprocess.Popen.
    """
    import sys
    argv = [
        sys.executable,
        str(_run_sbtdd_path()),
        "auto",
        "--task-ids", ",".join(task_ids),
        "--no-recursive",
    ]
    for ns_attr, cli_flag in _FORWARDABLE_FLAGS.items():
        value = getattr(ns, ns_attr, None)
        if value is not None:
            argv.extend([cli_flag, str(value)])
    return argv


def _run_sbtdd_path() -> Path:
    """Return path to run_sbtdd.py entry point."""
    return Path(__file__).resolve().parent / "run_sbtdd.py"
```

- [x] **Step 5: Wire `_build_worker_argv` into `_dispatch_tracks_concurrent`**

Replace inline argv build in `_dispatch_tracks_concurrent` with `_build_worker_argv(task_ids, ns)` call. Pass `ns` parameter through the call chain if not already present.

- [x] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestWorkerFlagForwarding -v`
Expected: 3/3 PASS.

Run: `make verify`
Expected: Clean.

- [x] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: worker CLI flag forwarding for v1.0.5 Item I-3`).

#### Refactor Phase

- [x] **Step 8: Refactor — confirm `_run_sbtdd_path` not duplicated**

If `_run_sbtdd_path` (or equivalent) already exists in another module, import + use. Otherwise leave as-is.

- [x] **Step 9: close-phase Refactor + Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 2 closed. State file advances `current_task_id: 2 → 3`.

---

## Track Beta — I-2 plan checkbox scratch + D Q3-A preflight enforcement (Subagent #2, sequential T3 → T4)

**Owner**: Subagent #2 dispatched from orchestrator.
**Surfaces** (file-disjoint with Track Alpha; Track Gamma deferred to v1.0.6):
- Modify: `skills/sbtdd/scripts/close_task_cmd.py`
- Modify: `skills/sbtdd/scripts/run_sbtdd.py` (argparse `--skip-preflight`)
- Extend: `tests/test_close_task_cmd.py`

**Wall-time estimated**: ~1 day.

**CRITICAL — within-track sequential ordering**: Task 3 (I-2) lands FIRST. Task 4 (D Q3-A) lands AFTER Task 3 completes. Both modify `close_task_cmd.py`. Task 4's `_preflight` extension is independent of Task 3's `mark_and_advance` redirect, but Task 3 must commit first to avoid merge conflicts within the worker.

### Task 3: Item I-2 — Per-worker scratch plan + flip-merge pattern

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (add `_scratch_plan_path` + `_apply_flips_for_task_ids` + `_merge_scratch_plans` helpers + `mark_and_advance` worker-mode redirect)
- Test: `tests/test_close_task_cmd.py` (extend with `class TestPerWorkerScratchPlan`)

Covers escenarios I2-1 through I2-4 from spec sec.4.2.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_close_task_cmd.py`:

```python
class TestPerWorkerScratchPlan:
    """v1.0.5 Item I-2 escenarios I2-1 through I2-4 — per-worker scratch + flip-merge."""

    def test_i2_1_worker_mode_writes_flip_to_scratch(self, tmp_path):
        """I2-1: worker mode redirects flip to per-worker scratch."""
        from close_task_cmd import _scratch_plan_path, mark_and_advance
        import argparse

        # Synthesize main plan
        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 3: Demo\n\n- [ ] **Step 1**\n- [ ] **Step 2**\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        ns = argparse.Namespace(no_recursive=True, task_ids="3")
        state = {"current_task_id": "3", "current_phase": "refactor"}
        mark_and_advance(state, tmp_path, ns)

        scratch = _scratch_plan_path(("3",), tmp_path)
        assert scratch.exists()
        scratch_text = scratch.read_text(encoding="utf-8")
        assert "[x]" in scratch_text  # flip applied to scratch
        # Main plan UNCHANGED in worker mode
        main_text = main_plan.read_text(encoding="utf-8")
        assert "[x]" not in main_text

    def test_i2_2_orchestrator_mode_writes_to_main_plan(self, tmp_path):
        """I2-2: orchestrator mode writes flip directly to main plan (v1.0.4 behavior)."""
        from close_task_cmd import mark_and_advance
        import argparse

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 3: Demo\n\n- [ ] **Step 1**\n",
            encoding="utf-8",
        )

        ns = argparse.Namespace(no_recursive=False, task_ids=None)
        state = {"current_task_id": "3", "current_phase": "refactor"}
        mark_and_advance(state, tmp_path, ns)

        main_text = main_plan.read_text(encoding="utf-8")
        assert "[x]" in main_text  # flip applied directly to main

    def test_i2_3_parent_post_batch_merges_scratch_flips(self, tmp_path):
        """I2-3: parent post-batch merges scratch flips into main."""
        from close_task_cmd import _scratch_plan_path, _merge_scratch_plans

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 1\n- [ ] T1 step\n\n### Task 2\n- [ ] T2 step\n\n"
            "### Task 3\n- [ ] T3 step\n\n### Task 4\n- [ ] T4 step\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        # Worker A scratch (T1 + T3 flipped)
        scratch_a = _scratch_plan_path(("1", "3"), tmp_path)
        scratch_a.write_text(
            "### Task 1\n- [x] T1 step\n\n### Task 2\n- [ ] T2 step\n\n"
            "### Task 3\n- [x] T3 step\n\n### Task 4\n- [ ] T4 step\n",
            encoding="utf-8",
        )
        # Worker B scratch (T2 + T4 flipped)
        scratch_b = _scratch_plan_path(("2", "4"), tmp_path)
        scratch_b.write_text(
            "### Task 1\n- [ ] T1 step\n\n### Task 2\n- [x] T2 step\n\n"
            "### Task 3\n- [ ] T3 step\n\n### Task 4\n- [x] T4 step\n",
            encoding="utf-8",
        )

        _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)

        merged_text = main_plan.read_text(encoding="utf-8")
        # ALL 4 flips visible in main
        assert merged_text.count("[x]") == 4
        # Scratch files cleaned up
        assert not scratch_a.exists()
        assert not scratch_b.exists()

    def test_i2_4_real_multiprocessing_race_regression(self, tmp_path):
        """I2-4: cross-process race regression test via multiprocessing.spawn.

        v1.0.5 iter-2 WARNING fix: explicit `for _ in range(50):` repeat
        loop wrapping the multiprocessing barrier-synchronized RMW.
        Asserts no flip lost across all 50 iterations to amplify
        race-window detection per spec sec.4.2 escenario I2-4.
        """
        import multiprocessing
        from close_task_cmd import _scratch_plan_path, _merge_scratch_plans

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan_path = plan_dir / "claude-plan-tdd.md"
        original_plan = (
            "### Task 1\n- [ ] step\n\n### Task 2\n- [ ] step\n\n"
            "### Task 3\n- [ ] step\n\n### Task 4\n- [ ] step\n"
        )
        (tmp_path / ".claude").mkdir()

        ctx = multiprocessing.get_context("spawn")

        for iteration in range(50):
            # Reset main plan + cleanup any stale scratch from prior loop
            main_plan_path.write_text(original_plan, encoding="utf-8")
            for stale in (tmp_path / ".claude").glob("plan-scratch-*.md"):
                stale.unlink(missing_ok=True)

            barrier = ctx.Barrier(2)
            procs = [
                ctx.Process(
                    target=_scratch_writer_worker,
                    args=(str(tmp_path), ["1", "3"], barrier),
                ),
                ctx.Process(
                    target=_scratch_writer_worker,
                    args=(str(tmp_path), ["2", "4"], barrier),
                ),
            ]
            for p in procs:
                p.start()
            for p in procs:
                p.join(timeout=30)
                assert p.exitcode == 0, (
                    f"Iter {iteration}: worker exited {p.exitcode}"
                )

            _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)
            merged_text = main_plan_path.read_text(encoding="utf-8")
            # ALL 4 flips visible across all 50 iterations (no lost updates)
            assert merged_text.count("[x]") == 4, (
                f"Iter {iteration}: lost flip — got {merged_text.count('[x]')} "
                f"[x] in merged plan, expected 4"
            )

    def test_i2_3b_partial_worker_failure_no_fabrication(self, tmp_path):
        """I2-3b (iter-1 CRITICAL #1+#3 fix): worker crashes after flipping
        T1 in scratch but BEFORE flipping T3 → main gets T1 only; T3
        remains [ ] (no fabricated flip). Operator can resume via
        `/sbtdd auto --task-ids T3` later.

        Pre-fix behavior would have flipped both T1 AND T3 in main
        regardless of scratch state. iter-1 CRITICAL #1+#3 fix derives
        flips from scratch-vs-main diff.
        """
        from close_task_cmd import (
            _scratch_plan_path,
            _merge_scratch_plans,
            _flip_checkbox,
        )
        import shutil

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 1\n- [ ] step\n\n### Task 2\n- [ ] step\n\n"
            "### Task 3\n- [ ] step\n\n### Task 4\n- [ ] step\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        # Simulate worker A (assigned [1, 3]) that crashed after flipping
        # T1 in scratch but BEFORE flipping T3:
        scratch_a = _scratch_plan_path(("1", "3"), tmp_path)
        shutil.copy2(main_plan, scratch_a)
        text = scratch_a.read_text(encoding="utf-8")
        text = _flip_checkbox(text, "1")  # T1 flipped, T3 NOT flipped
        scratch_a.write_text(text, encoding="utf-8")

        # Worker B (assigned [2, 4]) completed normally:
        scratch_b = _scratch_plan_path(("2", "4"), tmp_path)
        shutil.copy2(main_plan, scratch_b)
        text = scratch_b.read_text(encoding="utf-8")
        text = _flip_checkbox(text, "2")
        text = _flip_checkbox(text, "4")
        scratch_b.write_text(text, encoding="utf-8")

        # Parent merge — must derive flips from scratch-vs-main diff
        _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)
        merged_text = main_plan.read_text(encoding="utf-8")
        # T1 flipped (scratch_a had [x]); T3 NOT flipped (scratch_a [ ]);
        # T2 flipped; T4 flipped → exactly 3 [x], NOT 4
        assert merged_text.count("[x]") == 3, (
            f"Expected 3 flips (T1+T2+T4); got {merged_text.count('[x]')}. "
            "Pre-fix bug would fabricate T3 flip."
        )
        # T3 specifically must remain [ ]
        from close_task_cmd import _section_has_flipped
        assert not _section_has_flipped(merged_text, "3"), (
            "T3 was fabricated as flipped — iter-1 CRITICAL #1+#3 regression"
        )

    def test_i2_5_anchored_flip_checkbox_respects_section_boundaries(self, tmp_path):
        """I2-5 (iter-1 CRITICAL #2 fix): anchored regex bounds flips to
        current task's section. Pre-fix unanchored regex with re.DOTALL
        could match a [ ] from a LATER task when current task has no [ ].
        """
        from close_task_cmd import _flip_checkbox, _section_has_flipped

        # Plan: Task 3 has NO [ ] checkbox; Task 4 has [ ]
        plan_text = (
            "### Task 3\nThe operator already removed the checkbox.\n\n"
            "### Task 4\n- [ ] step\n"
        )

        # Flip T3 — pre-fix would match Task 4's [ ] across the boundary
        result = _flip_checkbox(plan_text, "3")

        # Anchored impl: T3 has no [ ] → result unchanged (idempotent guard)
        assert result == plan_text, (
            "Pre-fix regex would have flipped Task 4's [ ] across boundary"
        )
        # T4's [ ] still intact:
        assert not _section_has_flipped(result, "4"), (
            "T4 boundary violated — iter-1 CRITICAL #2 regression"
        )


def _scratch_writer_worker(project_root_str: str, task_ids: list[str], barrier) -> None:
    """Top-level helper for multiprocessing.Process spawn (must be picklable)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))
    from close_task_cmd import _scratch_plan_path
    import shutil

    project_root = Path(project_root_str)
    barrier.wait()
    scratch = _scratch_plan_path(tuple(sorted(task_ids)), project_root)
    if not scratch.exists():
        shutil.copy2(project_root / "planning" / "claude-plan-tdd.md", scratch)
    text = scratch.read_text(encoding="utf-8")
    for tid in task_ids:
        # Flip the [ ] checkbox under "### Task N" header
        text = text.replace(
            f"### Task {tid}\n- [ ] step",
            f"### Task {tid}\n- [x] step",
            1,
        )
    scratch.write_text(text, encoding="utf-8")
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_task_cmd.py::TestPerWorkerScratchPlan -v`
Expected: 4/4 FAIL (helpers don't exist yet).

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Implement `_scratch_plan_path` + `mark_and_advance` redirect + `_merge_scratch_plans`**

Modify `skills/sbtdd/scripts/close_task_cmd.py`:

```python
import hashlib
import shutil


def _scratch_plan_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
    """Per-worker scratch plan path.

    v1.0.5 Item I-2: deterministic name per task-IDs hash. Each worker
    writes flip(s) to its own scratch plan; parent post-batch merges
    all scratch flips into main plan.
    """
    digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
    return project_root / ".claude" / f"plan-scratch-{digest}.md"


def _atomic_write(path: Path, text: str) -> None:
    """Atomic text write via write-temp + os.replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


import re

# v1.0.5 iter-1 CRITICAL #2 fix: anchored regex walker.
_TASK_HEADER_RE = re.compile(r"^### Task ", re.MULTILINE)


def _iter_task_ids(plan_text: str) -> list[str]:
    """Yield task IDs in plan order.

    v1.0.5 iter-1 helper: parses `### Task <id>` headers + extracts the
    ID token (first whitespace-bounded word after "### Task ").
    """
    ids: list[str] = []
    header_iter = re.finditer(r"^### Task (\S+)", plan_text, re.MULTILINE)
    for m in header_iter:
        ids.append(m.group(1).rstrip(":"))
    return ids


def _section_bounds(plan_text: str, task_id: str) -> tuple[int, int] | None:
    """Return (section_start, section_end) char offsets for the task's
    section. Section start = end of `### Task <id>` header line; end =
    start of next `### Task ` header (or end-of-file). Returns None if
    task not found.

    v1.0.5 iter-1 CRITICAL #2 fix: bounds search to current task's
    section so flips never cross task boundaries.
    """
    header_re = re.compile(rf"^### Task {re.escape(task_id)}\b", re.MULTILINE)
    header_match = header_re.search(plan_text)
    if header_match is None:
        return None
    section_start = header_match.end()
    next_header = _TASK_HEADER_RE.search(plan_text, section_start)
    section_end = next_header.start() if next_header else len(plan_text)
    return section_start, section_end


def _section_has_flipped(plan_text: str, task_id: str) -> bool:
    """True iff the task section contains '- [x]' (flipped state).

    v1.0.5 iter-1 helper: bounded section extraction identical to
    `_flip_checkbox` so 'has flipped' check uses the same task-section
    window.
    """
    bounds = _section_bounds(plan_text, task_id)
    if bounds is None:
        return False
    section_start, section_end = bounds
    return "- [x]" in plan_text[section_start:section_end]


def _flip_checkbox(plan_text: str, task_id: str) -> str:
    """Flip first `- [ ]` checkbox in task's section to `- [x]`.

    v1.0.5 iter-1 CRITICAL #2 fix: regex anchored to current task's
    section bounded by next `### Task ` header (or EOF). Prevents the
    pre-fix `(### Task {tid}.*?)(- \\[ \\])` with `re.DOTALL` from
    matching a `[ ]` checkbox belonging to a LATER task when the
    current task has no `[ ]` of its own. Idempotent: returns plan_text
    unchanged if section has no `- [ ]` (already flipped or no
    checkbox).
    """
    bounds = _section_bounds(plan_text, task_id)
    if bounds is None:
        raise ValueError(f"Task {task_id} not found in plan")
    section_start, section_end = bounds
    section = plan_text[section_start:section_end]
    flipped_section = section.replace("- [ ]", "- [x]", 1)
    if flipped_section == section:
        return plan_text  # idempotent: already flipped or no checkbox
    return plan_text[:section_start] + flipped_section + plan_text[section_end:]


def _apply_flips_from_diff(main_text: str, scratch_text: str) -> str:
    """Apply only the `[ ]→[x]` transitions present in scratch relative
    to main. Iterates per-task-section using `_iter_task_ids`; flips a
    main checkbox only when the same task section in scratch has the
    `[x]` state.

    v1.0.5 iter-1 CRITICAL #1+#3 fix: replaces the prior
    `_apply_flips_for_task_ids(main, scratch, task_ids)` design which
    ignored `scratch_text` and unconditionally flipped every task_id
    in main, fabricating false-positive flips when workers crashed
    before scratch-write.
    """
    result = main_text
    for task_id in _iter_task_ids(scratch_text):
        if _section_has_flipped(scratch_text, task_id) and \
           not _section_has_flipped(result, task_id):
            result = _flip_checkbox(result, task_id)
    return result


def _merge_scratch_plans(tracks: list[list[str]], project_root: Path) -> None:
    """Parent post-batch: merge per-worker scratch plans into main.

    v1.0.5 iter-1 CRITICAL #1+#3 fix: flips derived from
    scratch-vs-main diff via `_apply_flips_from_diff`, NOT from
    `task_ids` parameter. If a worker crashed before flipping its
    task, scratch will lack the flip and main is left unchanged for
    that task — no fabrication of false-positive checkbox state.

    Workers have disjoint task IDs (per partition_by_tracks invariant);
    therefore merge = collect flips from each scratch by direct diff +
    apply to main. Cleans up scratch files post-merge.
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
    _atomic_write(main_path, main_text)


def mark_and_advance(state: dict, project_root: Path, ns: argparse.Namespace = None) -> None:
    """Flip current task checkbox + advance state file.

    v1.0.5 Item I-2: in worker mode (--no-recursive + --task-ids),
    writes flip to per-worker scratch plan instead of main. Parent
    post-batch merges all scratch plans.
    """
    plan_path = project_root / "planning" / "claude-plan-tdd.md"

    if ns and getattr(ns, "no_recursive", False) and getattr(ns, "task_ids", None):
        # Worker mode: write flip to scratch (parent merges later)
        task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
        scratch_path = _scratch_plan_path(task_ids_tuple, project_root)
        scratch_path.parent.mkdir(parents=True, exist_ok=True)
        if not scratch_path.exists():
            shutil.copy2(plan_path, scratch_path)
        text = scratch_path.read_text(encoding="utf-8")
        flipped = _flip_checkbox(text, state["current_task_id"])
        _atomic_write(scratch_path, flipped)
    else:
        # Orchestrator/sequential mode: write directly to main plan
        text = plan_path.read_text(encoding="utf-8")
        flipped = _flip_checkbox(text, state["current_task_id"])
        _atomic_write(plan_path, flipped)
    # ... existing state file advance ... (preserved unchanged)
```

Confirm `import os`, `import argparse`, `from pathlib import Path` are present.

- [ ] **Step 5: NO `auto_cmd.py` modification (iter-1 CRITICAL #4 architectural fix — Track Beta is helper-only)**

Per iter-1 CRITICAL #4 fix: Track Beta provides the
`_merge_scratch_plans` helper as a pure function in
`close_task_cmd.py` only. **Wiring** of `_merge_scratch_plans` into
`_dispatch_tracks_concurrent` post-batch lives in Task 1 (Track
Alpha) — see Task 1 Step 5 which now invokes BOTH
`_merge_audit_sidecars` AND `_merge_scratch_plans` post-batch.

Track Beta's only obligation here: ensure `_merge_scratch_plans` is
importable from `close_task_cmd` (module-level definition; Step 4
already provides this).

Validation step: confirm helper signature matches Task 1 Step 5
import expectation (`from close_task_cmd import _merge_scratch_plans`):

```bash
python -c "from close_task_cmd import _merge_scratch_plans; print(_merge_scratch_plans.__name__)"
# Expected: _merge_scratch_plans
```

No git commit produced by this step (no auto_cmd.py modification).

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestPerWorkerScratchPlan -v`
Expected: 4/4 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: per-worker scratch plan flip-merge for v1.0.5 Item I-2`).

#### Refactor Phase

- [ ] **Step 8: Refactor — DRY-consolidate `_atomic_write_json` to `state_file.py` (UNCONDITIONAL per iter-2 WARNING fix)**

iter-2 WARNING (mel + bal): atomic-write helpers duplicated across `auto_cmd.py` + `close_task_cmd.py` + temp-file naming collision under concurrent writers. Pre-fix design said "Likely YAGNI; skip if minimal duplication" — RETRACTED. iter-2 mandates unconditional consolidation.

Modify `skills/sbtdd/scripts/state_file.py` — add module-level shared helpers (preserve existing v0.5.0 atomic-write pattern):

```python
import json
import os
import tempfile
from pathlib import Path


def atomic_write_json(path: Path, data: object) -> None:
    """Atomic JSON write via tempfile.mkstemp + os.replace (DRY shared
    across auto_cmd + close_task_cmd per v1.0.5 iter-2 WARNING fix).

    Uses tempfile.mkstemp so concurrent writers in same directory get
    unique temp names (no collision risk).
    """
    fd, tmp_str = tempfile.mkstemp(
        suffix=".tmp", prefix=path.name + ".", dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_str, path)
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise


def atomic_write_text(path: Path, text: str) -> None:
    """Atomic text write — mirror of atomic_write_json for plan/scratch
    files. Same temp-file collision avoidance via tempfile.mkstemp.
    """
    fd, tmp_str = tempfile.mkstemp(
        suffix=".tmp", prefix=path.name + ".", dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_str, path)
    except Exception:
        try:
            os.unlink(tmp_str)
        except OSError:
            pass
        raise
```

Then in `close_task_cmd.py`: replace local `_atomic_write` definition with `from state_file import atomic_write_text as _atomic_write`. Track Alpha T1 Step 8 does the same for `_atomic_write_json`.

Run: `make verify` — expected clean. Commit `refactor:` (e.g., `refactor: DRY-consolidate atomic_write_{json,text} to state_file per v1.0.5 iter-2`).

- [ ] **Step 9: close-phase Refactor + Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 3 closed. State file advances `current_task_id: 3 → 4`.

---

### Task 4: Item D Q3 OPTION A — `close_task_cmd._preflight` HARD-BLOCK + `--skip-preflight` flag

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (extend `_preflight` with TDD triplet check + `skip_preflight` parameter)
- Modify: `skills/sbtdd/scripts/run_sbtdd.py` (argparse `--skip-preflight` on `close-task` subparser)
- Test: `tests/test_close_task_cmd.py` (extend with `class TestPreflightHardBlock`)

Covers escenarios D-1 through D-4 from spec sec.4.4.

**REQUIRES Task 3 to land FIRST** (within-track sequential ordering — both modify `close_task_cmd.py`).

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_close_task_cmd.py`:

```python
class TestPreflightHardBlock:
    """v1.0.5 Item D Q3-A escenarios D-1 through D-4 — preflight enforcement."""

    def test_d1_bypass_detected_raises_precondition(self, tmp_path, monkeypatch):
        """D-1: commit chain without TDD triplet → PreconditionError."""
        from close_task_cmd import _preflight
        from errors import PreconditionError

        # Mock _git_log_between to return chain without triplet
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "raw commit 1",
                "another raw commit",
            ],
        )
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        with pytest.raises(PreconditionError) as exc_info:
            _preflight(state, tmp_path)

        msg = str(exc_info.value)
        assert "Phase advance gate bypassed" in msg
        assert "test:/feat:|fix:/refactor: triplet" in msg
        assert "INV-1" in msg
        assert "close-phase" in msg
        assert "--skip-preflight" in msg

    def test_d2_canonical_triplet_no_trigger(self, tmp_path, monkeypatch):
        """D-2: canonical TDD triplet in commit chain → no PreconditionError."""
        from close_task_cmd import _preflight

        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement minimum",
                "refactor: clean up",
            ],
        )
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        # Should NOT raise
        _preflight(state, tmp_path)

    def test_d3_skip_preflight_bypasses_with_breadcrumb(self, tmp_path, capsys):
        """D-3: --skip-preflight bypasses + emits stderr breadcrumb."""
        from close_task_cmd import _preflight

        # Bypass scenario: no triplet, but skip_preflight=True
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        # Should NOT raise (override active)
        _preflight(state, tmp_path, skip_preflight=True)

        captured = capsys.readouterr()
        assert "[sbtdd close-task] WARNING" in captured.err
        assert "--skip-preflight active" in captured.err
        assert "task_id=3" in captured.err
        assert "abc123" in captured.err
        assert "Audit-logged" in captured.err

    def test_d4_no_chore_commit_first_task_branch_root_boundary(self, tmp_path, monkeypatch):
        """D-2b (iter-1 CRITICAL #5 fix): no prior `chore: mark task` commit
        → boundary is branch root + canonical triplet OK → no raise."""
        from close_task_cmd import _preflight

        # Simulate: first task in plan, no prior chore commit exists
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: None,
        )
        # Branch root → HEAD contains canonical triplet
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement",
                "refactor: extract helper",
            ],
        )
        state = {"current_task_id": "1"}

        # Should NOT raise (first task, branch-root boundary, full triplet)
        _preflight(state, tmp_path)

    def test_d5_partial_triplet_raises(self, tmp_path, monkeypatch):
        """D-1 (iter-1 CRITICAL #5 fix): commit chain since last chore: mark
        task with only 2 of 3 triplet prefixes → still raises."""
        from close_task_cmd import _preflight
        from errors import PreconditionError

        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc123",
        )
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement",
                # missing refactor
            ],
        )
        state = {"current_task_id": "3"}

        with pytest.raises(PreconditionError) as excinfo:
            _preflight(state, tmp_path)
        # iter-1 CRITICAL #5: error message references "since last chore commit"
        # boundary (or "branch root") — NOT phase_started_at_commit
        assert "since" in str(excinfo.value)
        assert "abc123" in str(excinfo.value) or "chore" in str(excinfo.value)
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightHardBlock -v`
Expected: 5/5 FAIL — `_preflight` doesn't yet have `skip_preflight` parameter or triplet check.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Extend `_preflight` with TDD triplet check + `skip_preflight` parameter (iter-1 CRITICAL #5: commit-window scope = "since last `chore: mark task` commit")**

Modify `skills/sbtdd/scripts/close_task_cmd.py`. Add or extend `_preflight`:

```python
import sys
import subprocess


def _git_log_between(start_sha: str | None, project_root: Path | None = None) -> list[str]:
    """Return commit subjects between start_sha (exclusive) and HEAD (inclusive).

    iter-1 CRITICAL #5 fix: when start_sha is None (no prior chore commit
    on branch), returns ALL commits on current branch (boundary = branch
    root).
    """
    cwd = str(project_root) if project_root else None
    if start_sha is None:
        # Boundary = branch root → all commits on HEAD
        rev_range = "HEAD"
    else:
        rev_range = f"{start_sha}..HEAD"
    result = subprocess.run(
        ["git", "log", rev_range, "--format=%s"],
        capture_output=True, text=True, check=False, cwd=cwd,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _last_chore_task_close_sha(project_root: Path | None = None) -> str | None:
    """Return SHA of most recent `chore: mark task <N> complete` commit.

    iter-1 CRITICAL #5 fix: this is the canonical "previous task close"
    boundary for the `_preflight` triplet check. Returns None if no such
    commit exists on current branch (first task in plan).

    Rebase/squash limitation: if operator squashed prior task-close
    commits, this returns the most recent surviving `chore:` subject
    matching the pattern; risk: false-positive triplet detection if
    squash produced a hybrid subject. Mitigated by `--skip-preflight`
    flag for emergency operator override.
    """
    cwd = str(project_root) if project_root else None
    result = subprocess.run(
        ["git", "log", "HEAD", "--format=%H%x09%s"],
        capture_output=True, text=True, check=False, cwd=cwd,
    )
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        # Match: "chore: mark task <N> complete" (allow trailing variants)
        if subject.startswith("chore: mark task ") and " complete" in subject:
            return sha
    return None


def _preflight(state: dict, project_root: Path | None = None,
               skip_preflight: bool = False) -> None:
    """Preflight checks before task close.

    v1.0.5 Item D Q3 OPTION A (iter-1 CRITICAL #5 fix): hard-block when
    phase advance gate is bypassed. Detects when commit chain since the
    last `chore: mark task <N> complete` commit (or branch root if none
    exists) lacks the canonical TDD triplet (test:/feat:|fix:/refactor:).
    Raises `PreconditionError` with operator-actionable guidance.
    Operator emergency override via `--skip-preflight` flag (audit-logged
    via stderr breadcrumb).

    Why "since last chore commit" instead of `phase_started_at_commit`
    (iter-1 CRITICAL #5 rationale): `phase_started_at_commit` advances on
    every phase close within a task, so when `_preflight` runs at
    task-close time it sees only the LAST phase's commits — never the
    full Red+Green+Refactor triplet. Boundary "since last chore: mark
    task" reliably brackets the entire current task's phase-close
    commits without phase-state coupling.

    Args:
        state: SessionState dict.
        project_root: Project root.
        skip_preflight: Operator emergency override (--skip-preflight flag).
    """
    if skip_preflight:
        sys.stderr.write(
            f"[sbtdd close-task] WARNING: --skip-preflight active; "
            f"phase advance gate enforcement BYPASSED for "
            f"task_id={state.get('current_task_id')}. Audit-logged.\n"
        )
        return

    last_chore_sha = _last_chore_task_close_sha(project_root)
    boundary_label = (
        f"last chore commit {last_chore_sha}"
        if last_chore_sha is not None else "branch root"
    )
    subjects = _git_log_between(last_chore_sha, project_root=project_root)
    has_test = any(s.startswith("test:") for s in subjects)
    has_green = any(s.startswith(("feat:", "fix:")) for s in subjects)
    has_refactor = any(s.startswith("refactor:") for s in subjects)
    if not (has_test and has_green and has_refactor):
        from errors import PreconditionError
        raise PreconditionError(
            f"Phase advance gate bypassed: commit chain since "
            f"{boundary_label} lacks test:/feat:|fix:/refactor: triplet. "
            f"Per SBTDD INV-1 + INV-5..7, each task close requires "
            f"close-phase invocation per Red/Green/Refactor phase. "
            f"Recovery: invoke `python skills/sbtdd/scripts/run_sbtdd.py "
            f"close-phase` once per pending phase OR pass --skip-preflight "
            f"if emergency operator override is appropriate (audit-logged "
            f"via stderr breadcrumb)."
        )
```

- [ ] **Step 5: Add `--skip-preflight` argparse flag to `close-task` subparser**

Modify `skills/sbtdd/scripts/run_sbtdd.py` (or wherever `close-task` subparser is built):

```python
close_task_p.add_argument(
    "--skip-preflight",
    action="store_true",
    default=False,
    help="v1.0.5 Item D Q3-A emergency override: bypass phase advance "
         "gate enforcement. Audit-logged via stderr breadcrumb.",
)
```

- [ ] **Step 6: Wire `ns.skip_preflight` through to `_preflight` in `close_task_cmd.cmd`**

Modify `close_task_cmd.cmd` (the subcommand entry point) to pass
`skip_preflight=getattr(ns, "skip_preflight", False)` to `_preflight`.

- [ ] **Step 7: Run tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightHardBlock -v`
Expected: 5/5 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 8: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: close-task preflight HARD-BLOCK for v1.0.5 Item D Q3 OPTION A`).

#### Refactor Phase

- [ ] **Step 9: Refactor — confirm `_git_log_between` consistent if duplicated elsewhere**

If `_git_log_between` (or equivalent) already exists in another module, consolidate. Otherwise leave.

- [ ] **Step 10: close-phase Refactor + Step 11: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 4 closed. State file `current_phase: "done"`, `current_task_id: null` (T5 deferred to v1.0.6 per iter-2 CRITICAL trigger; T4 is now last task in v1.0.5).

---

## Track Gamma — DEFERRED to v1.0.6

**Status**: **DEFERRED to v1.0.6** per iter-2 Checkpoint 2 CRITICAL
trigger pre-staged response (2026-05-08, user-authorized). v1.0.5
ships only Track Alpha + Track Beta. v1.0.6 LOCKED commitment for
Track Gamma C.2 methodology.

**Background**: iter 2 verdict GO_WITH_CAVEATS (3-0) surfaced 6
CRITICAL findings. All 3 agents independently recommended deferring
Pillar C per pre-staged G2 ladder (Bal confidence drop 72→68% on
bundle-width concern). Spec sec.6.1 iter-2 CRITICAL trigger fired;
Pillar A (I-1+I-2+I-3) remains hard-LOCKED + Pillar B (D Q3-A)
preserved.

**Original T5 scope (rolled to v1.0.6)**: SKILL.md + template +
smoke test for plan archaeology trim methodology. Doc-only + low-risk
+ low-value-this-cycle/high-value-future. Will land in v1.0.6 polish
cycle alongside other deferred items.

---

## Mid-cycle methodology activities (orchestrator)

Triggered AFTER Track Alpha + Track Beta complete + commits land
(Track Gamma deferred to v1.0.6 per iter-2 CRITICAL trigger). Each
activity is non-blocking for ship per hybrid methodology semantics;
documented in CHANGELOG `[1.0.5]` Process notes regardless of outcome.

### Activity F7 — Production-grade `--parallel` integration test

**Owner**: orchestrator.
**When**: AFTER Track Alpha + Beta close + Items I-1+I-2+I-3 landed.

**Steps**:

1. Synthesize 2-track plan with 4 disjoint tasks in tmp directory.
2. Run `python skills/sbtdd/scripts/run_sbtdd.py auto --parallel` from
   the synthetic plan directory.
3. Assert combined acceptance criterion per CHANGELOG `[Unreleased]`:
   - Parent's `.claude/auto-run.json` contains `start_time` + 4 task
     records (I-1)
   - Plan-tdd.md has 4 `[x]` checkbox flips, no lost updates (I-2)
   - Each worker subprocess received forwarded operator flags (I-3)
   - All TDD triplet commits per task in git log
   - State file `current_phase: "done"` post-completion
4. REPORT findings in CHANGELOG `[1.0.5]` Process notes.

**Failure mode**: if integration test surfaces gaps, document + roll
forward to v1.0.6 patch (per R6 mitigation).

### Activity F8 — Item D Q3-A empirical validation

**Owner**: orchestrator.
**When**: AFTER Track Beta close + Item D Q3-A landed.

**Steps**:

1. Synthesize task with intentional bypass (raw `git commit` only) →
   assert `close-task` raises `PreconditionError` with actionable
   message.
2. Synthesize task with canonical close-phase per phase → assert
   `close-task` proceeds normally.
3. Synthesize task with bypass + `--skip-preflight` → assert
   `close-task` proceeds + stderr breadcrumb emitted.
4. REPORT findings in CHANGELOG `[1.0.5]` Process notes.

### Activity P2 — Pre-merge gate clean WITHOUT INV-0

**Owner**: orchestrator.
**When**: AFTER all tracks + F7 + F8 complete.

**Steps**:

1. Verify all 5 active tasks `[x]` in plan-tdd.md.
2. Verify state file `current_phase: "done"`, `last_verification_result:
   "passed"`.
3. Run `python skills/sbtdd/scripts/run_sbtdd.py pre-merge`.
4. Loop 1 iterates until clean-to-go.
5. Loop 2 iterates until verdict >= GO_WITH_CAVEATS full no-degraded.
6. Per Q5 strict no-INV-0 stance: if Loop 2 doesn't converge cleanly
   within cap=5, **ESCALATE TO USER BEFORE applying INV-0 override**
   (per memory `feedback_manual_synthesis_exceptional`). Apply G2
   scope-trim ladder first (defer Track Gamma → defer Track Beta D
   Q3-A → Pillar A hard-LOCKED).

If Loop 2 fails / hangs: fall back to manual `python
skills/magi/scripts/run_magi.py code-review <payload>` per spec
sec.6.4 (precedent v1.0.0 through v1.0.4).

---

## Pre-merge gate (Loop 1 + Loop 2)

After all 5 plan tasks closed + 3 methodology activities executed
(F7 + F8 + P2 above):

1. Verify all checkboxes flipped:
   ```bash
   grep "- \[ \]" planning/claude-plan-tdd.md
   ```
   Expected: empty output.
2. Verify state file `current_phase: "done"`.
3. Verify `make verify` clean (pytest, ruff check, ruff format, mypy
   --strict, coverage >= 88%, runtime <= 220s NF-A hard).
4. Run `/sbtdd pre-merge`:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
5. Loop 1 (`/requesting-code-review`) iterates until clean-to-go.
6. Loop 2 (`/magi:magi`) iterates until verdict >= GO_WITH_CAVEATS
   full no-degraded.
7. Cross-check meta-reviewer artifacts captured under
   `.claude/magi-cross-check/`.

If Loop 2 iter 3 fails to converge, scope-trim per G2 binding
ladder (defer Track Gamma first → defer Track Beta D Q3-A second
→ Track Alpha I-1+I-2+I-3 hard-LOCKED).

**Strict no-INV-0 stance per Q5**: do NOT apply INV-0 override
without explicit user authorization. Escalate to user BEFORE
override.

---

## Finalization (post pre-merge gate clean)

1. Bump `plugin.json` + `marketplace.json` version 1.0.4 → 1.0.5.
2. Finalize CHANGELOG `[1.0.5]` with full ship record.
3. **Apply plan archaeology trim methodology (v1.0.5 Item C.2 dogfood)**:
   extract iter-by-iter triage from this plan into CHANGELOG `[1.0.5]`
   Process notes; trim `planning/claude-plan-tdd.md` to active plan
   only.
4. Update README + SKILL.md + CLAUDE.md (project root, gitignored)
   with v1.0.5 release notes.
5. Run `make verify` final check.
6. Commit version bump as `chore: bump to 1.0.5 + finalize CHANGELOG`.
7. Tag `v1.0.5` (with explicit user authorization).
8. Merge `feature/v1.0.5-bundle` into `main` (with explicit user
   authorization).
9. Push tag + main to origin (with explicit user authorization).

---

## Plan invariants summary

- **4 active plan tasks** distributed across 2 parallel subagent
  tracks (Track Alpha 2 tasks T1+T2; Track Beta 2 tasks T3+T4
  sequential). Track Gamma DEFERRED to v1.0.6 per iter-2 CRITICAL
  trigger (2026-05-08).
- **3 methodology activities** executed by orchestrator (F7 production-
  grade integration test + F8 Item D Q3-A empirical validation + P2
  pre-merge gate clean WITHOUT INV-0).
- **Per-phase close-phase mandate** applied to ALL 4 tasks per Q3
  Option B v1.0.4 mandate (preserved + soon-enforced via Item D Q3-A
  hard-block from Task 4 onwards).
- **Cero file overlap** between Track Alpha + Track Beta surfaces
  (verified in spec sec.5.4 post iter-2 CRITICAL #4 architectural
  fix; `state_file.py` shared by both for DRY atomic-write
  consolidation, with Track Alpha landing the consolidation).
- **Within-track sequential ordering**: Track Beta MUST land Task 3
  (I-2) before Task 4 (D Q3-A). Both modify `close_task_cmd.py`.
- **Cross-track dispatch-ordering invariant**: Track Beta T3 MUST
  land BEFORE Track Alpha T1 Step 5 (the wiring step importing
  `_merge_scratch_plans` from `close_task_cmd`). T1 Steps 1-4 + T2
  CAN run parallel with Track Beta T3+T4. Orchestrator sequences:
  dispatch Beta first → wait for T3 close → dispatch Alpha (which
  executes T1 Steps 1-4 → T2 → T1 Step 5 in order).
- **Tests baseline**: 1226 + 1 skipped → ~1250-1265 final.
- **Coverage threshold**: >= 88% (per Q4 v1.0.2 baseline).
- **`make verify` runtime**: <= 200s soft / 220s hard NF-A (acknowledges
  v1.0.4 baseline 195s + new tests).
- **MAGI Checkpoint 2**: cap=3 HARD G1 binding; iter-2 CRITICAL
  trigger preserved; G2 scope-trim ladder defers Track Gamma first
  → Track Beta D Q3-A second; Track Alpha I-1+I-2+I-3 hard-LOCKED.
- **Pre-merge Loop 2**: cap=5 with strict no-INV-0 stance per Q5;
  escalate to user BEFORE applying INV-0 override.
- **No `Co-Authored-By`, no AI references, English commits, no force
  push** per `~/.claude/CLAUDE.md` Git rules.
