#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd close-task - mark [x] + chore commit + advance state (sec.S.5.4).

Implements the sec.S.5.4 three-step protocol:
1. Flip all ``- [ ]`` checkboxes in the active task section to ``- [x]``.
2. Create an atomic ``chore: mark task {id} complete`` commit containing
   only the plan edit.
3. Advance ``session-state.json`` to the next open task (fresh red phase)
   or mark the plan ``done`` if this was the last task.

Enforces INV-3 (plan checkboxes monotonic: [x] never unset) and is
subject to INV-12 (every subcomando validates preconditions before
mutating state). The ``chore:`` commit honours INV-5..7 commit discipline
via :mod:`commits`.

v0.2 Feature B (INV-31): before advancing state, the subcommand dispatches
the superpowers spec-reviewer for the closing task unless the
``--skip-spec-review`` escape valve is set. A non-approved result surfaces
as :class:`SpecReviewError` (exit 12) and leaves state untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import _plan_ops
import spec_review_dispatch
import subprocess_utils
from commits import create as commit_create
from drift import detect_drift
from errors import DriftError, PreconditionError, SpecReviewError
from state_file import SessionState, load as load_state, save as save_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sbtdd close-task")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--skip-spec-review",
        action="store_true",
        help="Skip spec-reviewer dispatch (INV-31 escape valve)",
    )
    return p


def _preflight(root: Path) -> SessionState:
    """Validate state + drift before any mutation."""
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "refactor":
        raise PreconditionError(
            f"close-task requires current_phase='refactor', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value} "
            f"({drift_report.reason})"
        )
    return state


def _current_head_sha(root: Path) -> str:
    """Return short SHA of HEAD via ``git rev-parse --short``."""
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# v1.0.5 Item I-2 -- per-worker scratch plan + flip-merge pattern
# (escenarios I2-1..I2-5).
#
# Workers in the v1.0.4 ``--parallel`` opt-in path concurrently invoke
# ``mark_and_advance`` for disjoint task IDs, but the original
# read-modify-write of ``planning/claude-plan-tdd.md`` had no
# cross-process serialisation -- one worker's flip could be silently
# overwritten by another. The helpers below redirect each worker's flip
# to a deterministic per-worker scratch plan; the parent post-batch
# merges all scratch flips into the main plan. Disjoint task IDs (per
# the v1.0.4 ``partition_by_tracks`` invariant) guarantee disjoint
# checkbox flips, so the merge is a simple flip-collect (no 3-way
# conflict). Sequential mode is unaffected.
# ---------------------------------------------------------------------------


# v1.0.5 iter-1 CRITICAL #2 fix: anchored regex walker; ensures flip ops
# never cross task-section boundaries.
_TASK_HEADER_RE = re.compile(r"^### Task ", re.MULTILINE)


def _scratch_plan_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
    """Per-worker scratch plan path.

    v1.0.5 Item I-2: deterministic name per task-IDs hash. Each worker
    writes flip(s) to its own scratch plan; parent post-batch merges all
    scratch flips into main plan via :func:`_merge_scratch_plans`.
    """
    digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
    return project_root / ".claude" / f"plan-scratch-{digest}.md"


def _atomic_write(path: Path, text: str) -> None:
    """Atomic text write via ``tempfile.mkstemp`` + ``os.replace``.

    Mirrors :func:`auto_cmd._atomic_write_json` (T1) for plan / scratch
    files. Concurrent writers in the same directory get unique tmp
    names via :func:`tempfile.mkstemp`, eliminating collision risk
    documented in v1.0.5 iter-2 WARNING. T3 Refactor consolidates this
    helper into ``state_file`` so both modules import a shared
    implementation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(suffix=".tmp", prefix=path.name + ".", dir=str(path.parent))
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


def _iter_task_ids(plan_text: str) -> list[str]:
    """Yield task IDs in plan order.

    v1.0.5 iter-1 helper: parses ``### Task <id>`` headers + extracts
    the first whitespace-bounded token after the header. Trailing colon
    (if present in real plans like ``### Task 1: Demo``) is stripped so
    callers always see the bare ID.
    """
    ids: list[str] = []
    for m in re.finditer(r"^### Task (\S+)", plan_text, re.MULTILINE):
        ids.append(m.group(1).rstrip(":"))
    return ids


def _section_bounds(plan_text: str, task_id: str) -> tuple[int, int] | None:
    """Return ``(section_start, section_end)`` char offsets for the task.

    Section start = end of ``### Task <id>`` header line; end = start
    of the next ``### Task `` header (or EOF). Returns ``None`` if the
    task is not present in ``plan_text``.

    v1.0.5 iter-1 CRITICAL #2 fix: bounds the search to the current
    task's section so flips never cross task boundaries. Accepts both
    bare ``### Task 1`` and ``### Task 1:`` header forms.
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
    """True iff the task section contains ``- [x]`` (flipped state).

    v1.0.5 iter-1 helper: bounded section extraction identical to
    :func:`_flip_checkbox` so 'has flipped' check uses the same
    task-section window.
    """
    bounds = _section_bounds(plan_text, task_id)
    if bounds is None:
        return False
    section_start, section_end = bounds
    return "- [x]" in plan_text[section_start:section_end]


def _flip_checkbox(plan_text: str, task_id: str) -> str:
    """Flip first ``- [ ]`` checkbox in the task's section to ``- [x]``.

    v1.0.5 iter-1 CRITICAL #2 fix: regex anchored to the current task's
    section bounded by the next ``### Task `` header (or EOF). Prevents
    the pre-fix ``(### Task {tid}.*?)(- \\[ \\])`` with ``re.DOTALL``
    from matching a ``[ ]`` checkbox belonging to a LATER task when the
    current task has no ``[ ]`` of its own. Idempotent: returns
    ``plan_text`` unchanged if the section has no ``- [ ]`` (already
    flipped or no checkbox).
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
    """Apply only the ``[ ]->[x]`` transitions present in scratch vs main.

    Iterates per-task-section using :func:`_iter_task_ids`; flips a
    main checkbox only when the same task section in scratch has the
    ``[x]`` state.

    v1.0.5 iter-1 CRITICAL #1+#3 fix: replaces the prior
    ``_apply_flips_for_task_ids(main, scratch, task_ids)`` design which
    ignored ``scratch_text`` and unconditionally flipped every
    ``task_id`` in main, fabricating false-positive flips when workers
    crashed before scratch-write.
    """
    result = main_text
    for task_id in _iter_task_ids(scratch_text):
        if _section_has_flipped(scratch_text, task_id) and not _section_has_flipped(
            result, task_id
        ):
            result = _flip_checkbox(result, task_id)
    return result


def _merge_scratch_plans(tracks: list[list[str]], project_root: Path) -> None:
    """Parent post-batch: merge per-worker scratch plans into main.

    v1.0.5 iter-1 CRITICAL #1+#3 fix: flips derived from
    scratch-vs-main diff via :func:`_apply_flips_from_diff`, NOT from
    the ``task_ids`` parameter. If a worker crashed before flipping its
    task, scratch will lack the flip and main is left unchanged for
    that task -- no fabrication of false-positive checkbox state.

    Workers have disjoint task IDs (per ``partition_by_tracks``
    invariant); therefore merge = collect flips from each scratch by
    direct diff + apply to main. Cleans up scratch files post-merge so
    subsequent dispatches start clean. No-op when ``tracks`` is empty
    or when no scratch files exist (Track Beta / orchestrator startup
    paths).
    """
    main_path = project_root / "planning" / "claude-plan-tdd.md"
    if not main_path.exists():
        return
    main_text = main_path.read_text(encoding="utf-8")
    changed = False
    for task_ids in tracks:
        scratch_path = _scratch_plan_path(tuple(sorted(task_ids)), project_root)
        if not scratch_path.exists():
            continue  # worker didn't write scratch (early failure)
        scratch_text = scratch_path.read_text(encoding="utf-8")
        new_text = _apply_flips_from_diff(main_text, scratch_text)
        if new_text != main_text:
            main_text = new_text
            changed = True
        scratch_path.unlink(missing_ok=True)
    if changed:
        _atomic_write(main_path, main_text)


def _state_field(state: Any, key: str) -> Any:
    """Return ``state[key]`` (dict) or ``getattr(state, key)`` (dataclass).

    v1.0.5 Item I-2 helper: ``mark_and_advance`` accepts either the
    production :class:`SessionState` dataclass (orchestrator path) or a
    plain dict (worker-mode test fixtures synthesise the minimum two
    keys required for the scratch flip path). This helper keeps the
    extraction in one place so the worker-mode branch does not sprinkle
    ``isinstance`` checks.
    """
    if isinstance(state, dict):
        return state.get(key)
    return getattr(state, key, None)


def mark_and_advance(
    state: SessionState | dict[str, Any],
    root: Path,
    ns: argparse.Namespace | None = None,
) -> SessionState | None:
    """Close the current task and advance state.

    Public helper (no leading underscore) so ``auto_cmd.py`` can reuse the
    exact same sequence without duplicating logic (addresses iter-2 Finding
    W1). Consumes the plan at ``state.plan_path``, mutates it atomically
    via :func:`os.replace`, creates a ``chore: mark task {id} complete``
    commit, then writes the advanced :class:`SessionState` (next open
    ``[ ]`` task in red phase, or ``done``). Returns the new
    ``SessionState``.

    Preconditions: ``state.current_task_id is not None``; the working tree
    has no pending changes outside of the plan file edit produced here
    (enforced by the caller's drift/preflight checks).

    v1.0.5 Item I-2: when ``ns`` indicates worker mode
    (``--no-recursive`` + ``--task-ids``) the function redirects the
    plan flip to the per-worker scratch plan (see
    :func:`_scratch_plan_path`). The main ``planning/claude-plan-tdd.md``
    is left UNTOUCHED in worker mode -- the parent post-batch
    :func:`_merge_scratch_plans` collects all per-worker scratch flips
    into the main plan with a single atomic write. Worker mode skips
    the chore commit + state-file advance because both are owned by
    the parent's post-batch flow. Returns ``None`` in worker mode (no
    new SessionState to surface).

    Args:
        state: Current :class:`SessionState` (orchestrator path) OR a
            plain dict carrying at least ``current_task_id`` (worker
            test fixtures). Must have a non-null ``current_task_id``
            (and, for the orchestrator path, ``current_phase='refactor'``).
        root: Project root directory.
        ns: Optional argparse namespace; when ``no_recursive`` and
            ``task_ids`` are both truthy the worker-mode scratch path
            engages (v1.0.5 I-2). ``None`` (default) preserves the
            v1.0.4 orchestrator/sequential behavior byte-identically.

    Returns:
        The advanced :class:`SessionState` (either pointing to the next
        open task or marked ``done``) for the orchestrator path; ``None``
        in worker mode.
    """
    current_task_id = _state_field(state, "current_task_id")
    if current_task_id is None:
        raise PreconditionError("mark_and_advance requires non-null current_task_id")

    # v1.0.5 Item I-2 worker-mode short-circuit: write flip to per-worker
    # scratch plan; let the parent post-batch merge fold it into main.
    if ns is not None and getattr(ns, "no_recursive", False) and getattr(ns, "task_ids", None):
        task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
        scratch_path = _scratch_plan_path(task_ids_tuple, root)
        scratch_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path = root / "planning" / "claude-plan-tdd.md"
        if not scratch_path.exists():
            # First flip in this worker: seed scratch from main plan so
            # the diff against main captures only this worker's changes.
            shutil.copy2(plan_path, scratch_path)
        scratch_text = scratch_path.read_text(encoding="utf-8")
        flipped = _flip_checkbox(scratch_text, str(current_task_id))
        if flipped != scratch_text:
            _atomic_write(scratch_path, flipped)
        return None

    # Orchestrator / sequential path -- preserve v1.0.4 behavior exactly.
    if not isinstance(state, SessionState):
        # The orchestrator/cascade path always passes SessionState; dict
        # state only reaches here from a worker test that supplied an
        # ``ns`` lacking the worker markers. Treat as a synthetic
        # orchestrator path: write directly to the main plan but skip
        # the git/state-file machinery (no SessionState to advance).
        plan_path = root / "planning" / "claude-plan-tdd.md"
        text = plan_path.read_text(encoding="utf-8")
        flipped = _flip_checkbox(text, str(current_task_id))
        if flipped != text:
            _atomic_write(plan_path, flipped)
        return None

    plan_path = root / state.plan_path
    plan_text = plan_path.read_text(encoding="utf-8")
    # ``current_task_id`` was extracted + None-checked at the top of the
    # function; re-bind to a local so mypy can narrow the type cleanly
    # (SessionState's attribute remains ``str | None``).
    task_id_str = str(current_task_id)
    new_plan = _plan_ops.flip_task_checkboxes(plan_text, task_id_str)
    if new_plan != plan_text:
        # Only write + stage + commit when the flip actually changed bytes.
        # If the implementer subagent already flipped the checkboxes as
        # part of its phase work, the plan is already at the final state
        # and a chore commit here would fail with "nothing to commit".
        tmp = plan_path.with_suffix(plan_path.suffix + f".tmp.{os.getpid()}")
        tmp.write_text(new_plan, encoding="utf-8")
        os.replace(tmp, plan_path)
        subprocess_utils.run_with_timeout(
            ["git", "add", str(plan_path.relative_to(root))],
            timeout=10,
            cwd=str(root),
        )
        commit_create("chore", f"mark task {task_id_str} complete", cwd=str(root))
    # else: plan already reflects task completion; the state advance below
    # still runs so the session bookkeeping moves to the next open task.
    new_sha = _current_head_sha(root)
    next_id, next_title = _plan_ops.next_task(new_plan, task_id_str)
    new_state = SessionState(
        plan_path=state.plan_path,
        current_task_id=next_id,
        current_task_title=next_title,
        current_phase="red" if next_id else "done",
        phase_started_at_commit=new_sha,
        last_verification_at=state.last_verification_at,
        last_verification_result=state.last_verification_result,
        plan_approved_at=state.plan_approved_at,
        spec_snapshot_emitted_at=state.spec_snapshot_emitted_at,
    )
    save_state(new_state, root / ".claude" / "session-state.json")
    return new_state


def _run_spec_review(task_id: str, state: SessionState, root: Path) -> None:
    """Dispatch the spec-reviewer and raise on non-approval (INV-31).

    Keeps :func:`main` flat: callers see a single pre-advance gate, not an
    inline reviewer-plus-error-mapping block. Returns ``None`` on approval;
    raises :class:`SpecReviewError` when the reviewer is unconvinced, which
    aborts the subcommand before ``mark_and_advance`` mutates anything.
    """
    result = spec_review_dispatch.dispatch_spec_reviewer(
        task_id=task_id,
        plan_path=root / state.plan_path,
        repo_root=root,
    )
    if not result.approved:
        raise SpecReviewError(
            f"spec-reviewer did not approve task {task_id}",
            task_id=task_id,
            iteration=result.reviewer_iter,
            issues=tuple(i.text for i in result.issues),
        )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state = _preflight(root)
    closed_task_id = state.current_task_id or ""
    if not ns.skip_spec_review:
        _run_spec_review(closed_task_id, state, root)
    new_state = mark_and_advance(state, root)
    # CLI invocation always takes the orchestrator path (no ``ns`` kwarg
    # forwarded) so ``mark_and_advance`` returns a SessionState. The
    # widened ``SessionState | None`` return type added by v1.0.5 I-2
    # is purely for the worker-mode short-circuit; assert here both as
    # mypy hint and as a defensive tripwire.
    assert new_state is not None, "close-task CLI must receive a SessionState from mark_and_advance"
    next_msg = (
        f"Next: task {new_state.current_task_id}" if new_state.current_task_id else "Plan complete."
    )
    sys.stdout.write(f"Task {closed_task_id} closed. {next_msg}\n")
    return 0


run = main
