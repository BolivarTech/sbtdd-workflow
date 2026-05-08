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

**Goal:** Ship v1.0.5 — close v1.0.4 LOCKED commitments documented in CHANGELOG `[Unreleased]` (I-1/I-2/I-3 production-grade `--parallel` correctness gaps) + ship Item D Q3 OPTION A code-side enforcement (replaces v1.0.4's scope-trimmed Q3 Option B doc-only attempt) + plan archaeology trim methodology pattern. 5 plan tasks across 3 parallel subagent tracks (cero file overlap); 3 mid-cycle methodology activities (production-grade `--parallel` integration test + Item D Q3-A empirical validation + pre-merge gate clean WITHOUT INV-0).

**Architecture:** 3-track parallel dispatch with disjoint surfaces. Track Alpha (auto_cmd.py only, 2 sequential tasks I-1 → I-3) implements per-worker sidecar audit-trail pattern + worker CLI flag forwarding. Track Beta (close_task_cmd.py + run_sbtdd.py argparse, 2 sequential tasks I-2 → D Q3-A) implements per-worker scratch plan flip-merge pattern + close_task_cmd._preflight HARD-BLOCK with --skip-preflight emergency override. Track Gamma (SKILL.md + template + smoke test, 1 task) implements plan archaeology trim methodology documentation (C.1 spec sweep already applied inline in spec-behavior.md sec.8). Manual orchestrator dispatch via Agent tool fan-out (NOT auto --parallel self-dispatch — chicken-and-egg avoidance per Q1 Option C).

**State file write serialization**: Track Alpha owns Tasks 1-2 (sequential close). Track Beta owns Tasks 3-4 (sequential close). Track Gamma owns Task 5 (single close). State file `current_task_id` advances 1 → 2 → 3 → 4 → 5 → done. `state_file.save()` atomic `os.replace` (existing v0.5.0 pattern) ensures no partial writes. Tracks have disjoint task IDs and disjoint file surfaces; concurrent close-task invocations are safe per v0.4.0+v0.5.0+v1.0.0+v1.0.2+v1.0.3+v1.0.4 precedent.

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict, stdlib-only on hot paths. TDD-Guard active in same worktree (parallel-safe per spec sec.3 since Tracks have disjoint surfaces). Brainstorming refinements 2026-05-08: Q1 = 3-track parallel disjoint (Alpha I-1+I-3, Beta I-2+D Q3-A, Gamma C.2); Q2 = per-worker sidecar I-1; Q3 = per-worker scratch I-2; Q4 = `--skip-preflight` flag-only emergency override; Q5 = strict no-INV-0 stance.

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-08`.
- **Phase close protocol (Q3 Option B v1.0.4 mandate, preserved + soon-to-be-enforced via Item D Q3-A)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each Red/Green/Refactor verify-clean. Manual `git commit` per phase BYPASSES the phase-advance + state-file update + verification gate; close-task v1.0.5 will HARD-BLOCK once Item D Q3-A lands (Track Beta Task 4).
- **Task close protocol**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review` after Refactor close-phase. Use `--skip-spec-review` to bypass INV-31 spec-reviewer dispatch (~1-2 min/task overhead acceptable but not required for these infrastructure items).
- **Track Beta sequential ordering MANDATORY**: Task 3 (I-2) lands FIRST. Task 4 (D Q3-A) lands AFTER Task 3 completes. Both modify `close_task_cmd.py` — within-track sequential coordination required.
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
**Surfaces** (cero overlap with Track Beta + Track Gamma):
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Extend: `tests/test_auto_cmd.py`

**Wall-time estimated**: ~1 day.

### Task 1: Item I-1 — Per-worker sidecar audit-trail pattern

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_audit_sidecar_path` helper + worker-mode `_write_audit` redirect + `_merge_audit_sidecars` post-batch helper + `_dispatch_tracks_concurrent` post-batch hook)
- Test: `tests/test_auto_cmd.py` (extend with `class TestPerWorkerSidecarAudit`)

Covers escenarios I1-1 through I1-5 from spec sec.4.1.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

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

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestPerWorkerSidecarAudit -v`
Expected: 5/5 FAIL with `AttributeError: module 'auto_cmd' has no attribute '_audit_sidecar_path'` (and same for `_merge_audit_sidecars`).

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Red phase verify-clean confirms tests fail for the correct reason (missing implementation, not import error). Atomic `test:` commit landed. State file advances `current_phase: red → green`.

#### Green Phase

- [ ] **Step 4: Implement `_audit_sidecar_path` + `_write_audit` redirect + `_merge_audit_sidecars`**

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

- [ ] **Step 5: Wire `_merge_audit_sidecars` into `_dispatch_tracks_concurrent`**

Modify `_dispatch_tracks_concurrent` post-batch:

```python
def _dispatch_tracks_concurrent(
    tracks: list[list[str]],
    effective_workers: int,
    project_root: Path,
    ns: argparse.Namespace,
) -> None:
    """... existing dispatch logic ..."""
    # ... existing thread-pool + Queue + Popen workers ...
    # ... wait all workers complete ...

    # v1.0.5 Item I-1: merge per-worker audit sidecars into canonical
    merged_audit = _merge_audit_sidecars(tracks, project_root)
    _atomic_write_json(project_root / ".claude" / "auto-run.json", merged_audit)
```

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestPerWorkerSidecarAudit -v`
Expected: 5/5 PASS.

Run: `make verify`
Expected: All checks green (pytest, ruff check, ruff format, mypy).

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Green phase verify-clean passes. Atomic `feat:` commit landed (e.g. `feat: per-worker sidecar audit-trail pattern for v1.0.5 Item I-1`).

#### Refactor Phase

- [ ] **Step 8: Refactor — review for duplication / extract helpers if needed**

If `_atomic_write_json` already existed in another module (e.g., `state_file.py`), import + use it instead of duplicating. Otherwise, leave the new helper in place. Document choice in commit message.

- [ ] **Step 9: Run tests to verify still PASS**

Run: `make verify`
Expected: Clean.

- [ ] **Step 10: close-phase Refactor**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `refactor:` commit landed (or `--allow-empty` if no actual refactor).

- [ ] **Step 11: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 1 checkboxes flipped to `[x]`. Atomic `chore: mark task 1 complete` commit. State file advances `current_task_id: 1 → 2`.

---

### Task 2: Item I-3 — Worker CLI flag forwarding via `_FORWARDABLE_FLAGS` + `_build_worker_argv`

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `_FORWARDABLE_FLAGS` MappingProxyType + `_build_worker_argv` helper + `_dispatch_tracks_concurrent` argv builder integration)
- Test: `tests/test_auto_cmd.py` (extend with `class TestWorkerFlagForwarding`)

Covers escenarios I3-1 through I3-3 from spec sec.4.3.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

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

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestWorkerFlagForwarding -v`
Expected: 3/3 FAIL with `ImportError` (helpers don't exist yet).

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `test:` commit landed.

#### Green Phase

- [ ] **Step 4: Implement `_FORWARDABLE_FLAGS` + `_build_worker_argv`**

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

- [ ] **Step 5: Wire `_build_worker_argv` into `_dispatch_tracks_concurrent`**

Replace inline argv build in `_dispatch_tracks_concurrent` with `_build_worker_argv(task_ids, ns)` call. Pass `ns` parameter through the call chain if not already present.

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestWorkerFlagForwarding -v`
Expected: 3/3 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: worker CLI flag forwarding for v1.0.5 Item I-3`).

#### Refactor Phase

- [ ] **Step 8: Refactor — confirm `_run_sbtdd_path` not duplicated**

If `_run_sbtdd_path` (or equivalent) already exists in another module, import + use. Otherwise leave as-is.

- [ ] **Step 9: close-phase Refactor + Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 2 closed. State file advances `current_task_id: 2 → 3`.

---

## Track Beta — I-2 plan checkbox scratch + D Q3-A preflight enforcement (Subagent #2, sequential T3 → T4)

**Owner**: Subagent #2 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Alpha + Track Gamma):
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
        """I2-4: cross-process race regression test via multiprocessing.spawn."""
        import multiprocessing
        from close_task_cmd import _scratch_plan_path, _merge_scratch_plans

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        main_plan = plan_dir / "claude-plan-tdd.md"
        main_plan.write_text(
            "### Task 1\n- [ ] step\n\n### Task 2\n- [ ] step\n\n"
            "### Task 3\n- [ ] step\n\n### Task 4\n- [ ] step\n",
            encoding="utf-8",
        )
        (tmp_path / ".claude").mkdir()

        ctx = multiprocessing.get_context("spawn")
        barrier = ctx.Barrier(2)
        # Spawn 2 worker processes that flip disjoint task IDs concurrently
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
            assert p.exitcode == 0, f"Worker exited {p.exitcode}"

        # Parent post-batch merge
        _merge_scratch_plans([["1", "3"], ["2", "4"]], tmp_path)
        merged_text = main_plan.read_text(encoding="utf-8")
        # ALL 4 flips visible (no lost updates)
        assert merged_text.count("[x]") == 4


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


def _flip_checkbox(plan_text: str, task_id: str) -> str:
    """Flip first [ ] checkbox under '### Task <id>' header to [x]."""
    import re
    pattern = re.compile(rf"(### Task {re.escape(task_id)}.*?)(- \[ \])", re.DOTALL)
    return pattern.sub(r"\1- [x]", plan_text, count=1)


def _apply_flips_for_task_ids(main_text: str, scratch_text: str, task_ids: list[str]) -> str:
    """Apply scratch's flips for task_ids into main text.

    v1.0.5 Item I-2: collects [ ] → [x] flips from scratch for the
    specified task_ids, applies to main. Disjoint task IDs guarantee
    no flip conflict.
    """
    for tid in task_ids:
        # If scratch has [x] under "### Task <tid>" but main has [ ], flip in main
        # (Simplest impl: directly flip first [ ] under header in main)
        main_text = _flip_checkbox(main_text, tid)
    return main_text


def _merge_scratch_plans(tracks: list[list[str]], project_root: Path) -> None:
    """Parent post-batch: merge per-worker scratch flips into main plan.

    v1.0.5 Item I-2: each worker's scratch contains flips for ITS task IDs.
    Workers have disjoint task IDs (per partition_by_tracks invariant).
    Therefore merge = collect flips from each scratch + apply to main.
    No 3-way conflict possible. Cleans up scratch files post-merge.
    """
    main_path = project_root / "planning" / "claude-plan-tdd.md"
    main_text = main_path.read_text(encoding="utf-8")
    for task_ids in tracks:
        scratch_path = _scratch_plan_path(tuple(sorted(task_ids)), project_root)
        if not scratch_path.exists():
            continue  # worker didn't flip any (early failure)
        scratch_text = scratch_path.read_text(encoding="utf-8")
        main_text = _apply_flips_for_task_ids(main_text, scratch_text, task_ids)
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

- [ ] **Step 5: Wire `_merge_scratch_plans` into `auto_cmd._dispatch_tracks_concurrent` post-batch**

Modify `skills/sbtdd/scripts/auto_cmd.py` `_dispatch_tracks_concurrent`:

```python
def _dispatch_tracks_concurrent(...) -> None:
    # ... existing dispatch + wait ...
    # v1.0.5 Item I-1: merge per-worker audit sidecars (already added Task 1)
    merged_audit = _merge_audit_sidecars(tracks, project_root)
    _atomic_write_json(project_root / ".claude" / "auto-run.json", merged_audit)

    # v1.0.5 Item I-2: merge per-worker scratch plans
    from close_task_cmd import _merge_scratch_plans
    _merge_scratch_plans(tracks, project_root)
```

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestPerWorkerScratchPlan -v`
Expected: 4/4 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: per-worker scratch plan flip-merge for v1.0.5 Item I-2`).

#### Refactor Phase

- [ ] **Step 8: Refactor — confirm `_atomic_write` consistent across modules**

If `_atomic_write_json` (auto_cmd) + `_atomic_write` (close_task_cmd) duplicate logic, consider extracting to shared helper. Likely YAGNI; skip if minimal duplication.

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

    def test_d4_no_phase_started_at_commit_no_op(self, tmp_path):
        """D-4: state without phase_started_at_commit → no-op (first task)."""
        from close_task_cmd import _preflight

        state = {"current_task_id": "1"}  # no phase_started_at_commit

        # Should NOT raise (first task, no chain to check)
        _preflight(state, tmp_path)

    def test_d4_partial_triplet_raises(self, tmp_path, monkeypatch):
        """D-4: commit chain with only 2 of 3 triplet prefixes → still raises."""
        from close_task_cmd import _preflight
        from errors import PreconditionError

        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",
                "feat: implement",
                # missing refactor
            ],
        )
        state = {"current_task_id": "3", "phase_started_at_commit": "abc123"}

        with pytest.raises(PreconditionError):
            _preflight(state, tmp_path)
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightHardBlock -v`
Expected: 5/5 FAIL — `_preflight` doesn't yet have `skip_preflight` parameter or triplet check.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Extend `_preflight` with TDD triplet check + `skip_preflight` parameter**

Modify `skills/sbtdd/scripts/close_task_cmd.py`. Add or extend `_preflight`:

```python
import sys
import subprocess


def _git_log_between(start_sha: str, project_root: Path | None = None) -> list[str]:
    """Return commit subjects between start_sha (exclusive) and HEAD (inclusive)."""
    cwd = str(project_root) if project_root else None
    result = subprocess.run(
        ["git", "log", f"{start_sha}..HEAD", "--format=%s"],
        capture_output=True, text=True, check=False, cwd=cwd,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _preflight(state: dict, project_root: Path | None = None,
               skip_preflight: bool = False) -> None:
    """Preflight checks before task close.

    v1.0.5 Item D Q3 OPTION A: hard-block when phase advance gate is
    bypassed. Detects when commit chain since `phase_started_at_commit`
    lacks the canonical TDD triplet (test:/feat:|fix:/refactor:). Raises
    `PreconditionError` with operator-actionable guidance. Operator
    emergency override via `--skip-preflight` flag (audit-logged via
    stderr breadcrumb).

    Args:
        state: SessionState dict.
        project_root: Project root.
        skip_preflight: Operator emergency override (--skip-preflight flag).
    """
    if skip_preflight:
        sys.stderr.write(
            f"[sbtdd close-task] WARNING: --skip-preflight active; "
            f"phase advance gate enforcement BYPASSED for "
            f"task_id={state.get('current_task_id')} since SHA "
            f"{state.get('phase_started_at_commit')}. Audit-logged.\n"
        )
        return

    start_sha = state.get("phase_started_at_commit")
    if not start_sha:
        return  # No phase_started_at_commit → first-task no-op

    subjects = _git_log_between(start_sha, project_root=project_root)
    has_test = any(s.startswith("test:") for s in subjects)
    has_green = any(s.startswith(("feat:", "fix:")) for s in subjects)
    has_refactor = any(s.startswith("refactor:") for s in subjects)
    if not (has_test and has_green and has_refactor):
        from errors import PreconditionError
        raise PreconditionError(
            f"Phase advance gate bypassed: commit chain since {start_sha} "
            f"lacks test:/feat:|fix:/refactor: triplet. Per SBTDD "
            f"INV-1 + INV-5..7, each task close requires close-phase "
            f"invocation per Red/Green/Refactor phase. Recovery: invoke "
            f"`python skills/sbtdd/scripts/run_sbtdd.py close-phase` once "
            f"per pending phase OR pass --skip-preflight if emergency "
            f"operator override is appropriate (audit-logged via stderr "
            f"breadcrumb)."
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

Expected: Task 4 closed. State file advances `current_task_id: 4 → 5`.

---

## Track Gamma — C.2 plan archaeology trim methodology (Subagent #3, single task T5)

**Owner**: Subagent #3 (lightweight; could be orchestrator in-session).
**Surfaces** (cero overlap):
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add ship-time archaeology trim procedure)
- Modify: `templates/CLAUDE.local.md.template` (template guidance)
- Create: `tests/test_plan_archaeology_trim_pattern.py`

**Wall-time estimated**: ~0.5 day.

**Note**: C.1 (spec sec.8 stale risk-register sweep) was APPLIED INLINE in `sbtdd/spec-behavior.md` during brainstorming. No Track Gamma work needed for sweep itself.

### Task 5: Item C.2 — Plan archaeology trim methodology + smoke test

**Files:**
- Create: `tests/test_plan_archaeology_trim_pattern.py`
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `templates/CLAUDE.local.md.template`

Covers escenarios C2-1 through C2-3 from spec sec.4.5.

#### Red Phase

- [ ] **Step 1: Write the failing smoke test**

Create `tests/test_plan_archaeology_trim_pattern.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-08
"""v1.0.5 Item C.2 — plan archaeology trim methodology doc-coherence smoke test.

Covers escenarios C2-1 through C2-3 from spec sec.4.5. Pattern follows
v1.0.4 doc-only smoke tests (e.g., callsite audit pattern).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_c2_1_skill_md_documents_ship_time_trim_procedure():
    """C2-1: SKILL.md contains ship-time archaeology trim procedure."""
    skill_md = _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    # Mandate text must reference plan archaeology trim ship-time procedure
    assert re.search(r"plan\s+archaeology\s+trim", text, re.IGNORECASE), (
        "SKILL.md must reference 'plan archaeology trim' methodology "
        "(v1.0.5 Item C.2 mandate)."
    )
    # Procedure must mention CHANGELOG Process notes section
    assert "CHANGELOG" in text and "Process notes" in text, (
        "SKILL.md must document extraction of iter-by-iter triage from "
        "plan-tdd.md into CHANGELOG Process notes section."
    )


def test_c2_2_template_references_archaeology_trim():
    """C2-2: CLAUDE.local.md.template references archaeology trim procedure."""
    template = _REPO_ROOT / "templates" / "CLAUDE.local.md.template"
    text = template.read_text(encoding="utf-8")
    assert re.search(r"plan\s+archaeology\s+trim", text, re.IGNORECASE), (
        "CLAUDE.local.md.template must reference 'plan archaeology trim' "
        "methodology + cross-link to SKILL.md authoritative version."
    )


def test_c2_3_cross_artifact_reference_consistency():
    """C2-3: SKILL.md AND template both contain procedure reference."""
    skill_md = _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
    template = _REPO_ROOT / "templates" / "CLAUDE.local.md.template"
    skill_text = skill_md.read_text(encoding="utf-8").lower()
    template_text = template.read_text(encoding="utf-8").lower()
    assert "plan archaeology trim" in skill_text
    assert "plan archaeology trim" in template_text
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_plan_archaeology_trim_pattern.py -v`
Expected: 3/3 FAIL — SKILL.md + template don't yet contain "plan archaeology trim" reference.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Update `skills/sbtdd/SKILL.md` with archaeology trim procedure**

Append (or insert into appropriate section) in `skills/sbtdd/SKILL.md`:

```markdown
### v1.0.5 plan archaeology trim methodology (Item C.2)

At v1.0.X ship time, the orchestrator MUST extract iter-by-iter triage
context from `planning/claude-plan-tdd.md` into the corresponding
CHANGELOG `[N.N.N]` "Process notes" section. The active plan should
be trimmed to "active plan only" — current scope + tasks +
acceptance criteria; no iter-1/iter-2/iter-3 archaeology inline.

**Procedure**:

1. At ship-time, identify all iter-by-iter triage / mini-cycle context
   embedded in `planning/claude-plan-tdd.md`.
2. Extract this content into the CHANGELOG `[N.N.N]` Process notes
   section (preserves history in the canonical immutable record).
3. Trim `planning/claude-plan-tdd.md` to active plan only — scope +
   tasks + acceptance criteria; iter archaeology removed.
4. Optionally keep `planning/claude-plan-tdd-org.md` as immutable
   archaeology while trimmed `planning/claude-plan-tdd.md` becomes
   the canonical active plan (precedent already established).

**Rationale (Balthasar v1.0.4 iter-6b INFO #17)**: plan size
disproportionate to code delta accumulates maintenance debt. Iter
archaeology in CHANGELOG provides forensics; active plan stays
focused on what's shipping.
```

- [ ] **Step 5: Update `templates/CLAUDE.local.md.template`**

Append (or insert into appropriate section) in `templates/CLAUDE.local.md.template`:

```markdown
### Plan archaeology trim ship-time procedure (v1.0.5 Item C.2)

At v1.0.X ship time, extract iter-by-iter triage context from your
project's `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]`
Process notes section. Trim plan-tdd.md to active plan only.

See `skills/sbtdd/SKILL.md` for authoritative procedure documentation.
```

- [ ] **Step 6: Run tests to verify PASS**

Run: `pytest tests/test_plan_archaeology_trim_pattern.py -v`
Expected: 3/3 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `docs:` commit landed (e.g. `docs: plan archaeology trim methodology for v1.0.5 Item C.2`).

#### Refactor Phase

- [ ] **Step 8: Refactor — verify cross-artifact consistency**

Re-read SKILL.md + template snippets to ensure procedure description
is consistent. Adjust wording if needed.

- [ ] **Step 9: close-phase Refactor + Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 5 closed. State file `current_phase: "done"`,
`current_task_id: null`.

---

## Mid-cycle methodology activities (orchestrator)

Triggered AFTER Track Alpha + Track Beta + Track Gamma all complete +
commits land. Each is non-blocking for ship per hybrid methodology
semantics; documented in CHANGELOG `[1.0.5]` Process notes regardless
of outcome.

### Activity F7 — Production-grade `--parallel` integration test

**Owner**: orchestrator.
**When**: AFTER Track Alpha + Beta + Gamma close + Items I-1+I-2+I-3
landed.

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

- **5 active plan tasks** distributed across 3 parallel subagent
  tracks (Track Alpha 2 tasks T1+T2; Track Beta 2 tasks T3+T4
  sequential; Track Gamma 1 task T5).
- **3 methodology activities** executed by orchestrator (F7 production-
  grade integration test + F8 Item D Q3-A empirical validation + P2
  pre-merge gate clean WITHOUT INV-0).
- **Per-phase close-phase mandate** applied to ALL 5 tasks per Q3
  Option B v1.0.4 mandate (preserved + soon-enforced via Item D Q3-A
  hard-block from Task 4 onwards).
- **Cero file overlap** between Track Alpha + Track Beta + Track Gamma
  surfaces (verified in spec sec.5.4).
- **Within-track sequential ordering**: Track Beta MUST land Task 3
  (I-2) before Task 4 (D Q3-A). Both modify `close_task_cmd.py`.
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
