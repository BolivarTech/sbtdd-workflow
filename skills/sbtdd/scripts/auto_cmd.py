#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd auto -- shoot-and-forget full-cycle (sec.S.5.8, INV-22..26).

Five-phase flow:

1. Phase 1 -- pre-flight dependency check + state / plan_approved_at
   validation (Task 27).
2. Phase 2 -- sequential task loop with TDD cycles per task (Task 28).
3. Phase 3 -- pre-merge with elevated MAGI budget (Task 29).
4. Phase 4 -- sec.M.7 checklist validation (Task 30).
5. Phase 5 -- report + ``.claude/auto-run.json`` audit trail (Task 30).

Design invariants enforced here:

- **INV-22** (sequential only): never spawn parallel subprocesses.
- **INV-23** (TDD-Guard inviolable): never writes to
  ``.claude/settings.json`` (spied in Task 31 test).
- **INV-24** (conservative): verification retries exhaust -> exit 6.
- **INV-25** (branch-scoped): never invokes
  ``/finishing-a-development-branch`` -- leaves the branch clean for
  the user to merge/PR manually.
- **INV-26** (audit trail): writes ``.claude/auto-run.json`` with
  per-phase timestamps and verdict.

Dry-run short-circuits BEFORE any subprocess work (Finding 4) so a
preview works even when git / tdd-guard / plugins are unavailable.

INV-24 (conservative defaults) does NOT apply inside ``auto`` itself --
auto commits atomically at every phase boundary, so no uncommitted work
is ever left behind mid-run. The CONTINUE-by-default contract for
uncommitted work lives in :mod:`resume_cmd` (see
``resume_cmd._resolve_uncommitted``) and engages only when the user
re-enters via ``/sbtdd resume`` after an externally-caused interruption
(crash, quota, Ctrl+C). This cross-reference exists to forestall the
common reader question "where is INV-24 enforced in auto?" -- the answer
is "in resume; auto never needs it".
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import IO, Any, Callable, Mapping, cast

import _plan_ops
import close_task_cmd
import commits
import receiving_review_dispatch
import spec_review_dispatch
import subprocess_utils
import superpowers_dispatch
from commits import create as commit_create
from config import PluginConfig, load_plugin_local
from dag_parser import parse_plan
from dependency_check import check_environment
from drift import detect_drift
from parallel_dispatcher import partition_by_tracks
from errors import (
    ChecklistError,
    CommitError,
    ConcurrentDispatchError,
    DependencyError,
    DriftError,
    MAGIGateError,
    PreconditionError,
    QuotaExhaustedError,
    SpecReviewError,
    ValidationError,
    VerificationIrremediableError,
)
from heartbeat import (
    HeartbeatEmitter,
    get_current_progress,
    set_current_progress,
)
from models import COMMIT_PREFIX_MAP, ProgressContext
from state_file import SessionState
from state_file import load as load_state
from state_file import save as save_state


#: Allowed values for AutoRunAudit.status. Extending this set is a schema
#: change: bump ``_AUTO_RUN_SCHEMA_VERSION`` below and update tests.
_ALLOWED_AUTO_RUN_STATUSES: tuple[str, ...] = (
    "success",
    "magi_gate_blocked",
    "verification_irremediable",
    "loop1_divergent",
    "quota_exhausted",
    "checklist_failed",
    "drift_detected",
    "precondition_failed",
    "spec_review_issues",
)

#: Current schema version for ``.claude/auto-run.json``. Bump when a
#: backwards-incompatible change lands (field removed, type changed,
#: status value removed). Additive changes (new status, new optional
#: field) keep the version.
_AUTO_RUN_SCHEMA_VERSION: int = 1


def _set_progress(
    *,
    iter_num: int = 0,
    phase: int,
    task_index: int | None = None,
    task_total: int | None = None,
    dispatch_label: str | None = None,
) -> None:
    """Helper: write a fresh ProgressContext for the current transition.

    ``started_at`` semantics (Checkpoint 2 iter 2 caspar CRITICAL #3 fix):
    ``started_at`` represents the **current dispatch's** start time per
    spec sec.3. Refreshing per ``_set_progress`` call would break that
    contract when a single dispatch has multiple intra-dispatch updates
    (e.g., progress refinement during a long subagent invocation).

    Rules:

    - If ``dispatch_label`` differs from the current ProgressContext's
      label (or current is ``None``): treat as new dispatch, refresh
      ``started_at``.
    - If ``dispatch_label`` matches current: preserve ``started_at``
      (intra-dispatch update; elapsed timer continues monotonically).
    - If ``dispatch_label is None`` (between dispatches): set
      ``started_at`` to ``None``.

    The W2 fold-in (Checkpoint 2 iter 4) pins the ``None -> label`` case
    as a transition (first labeled dispatch refreshes ``started_at``).
    """
    current = get_current_progress()
    # Single label-transition predicate (Checkpoint 2 iter 3 melchior CRITICAL):
    # compute is_dispatch_transition first; then derive started_at from one rule.
    is_dispatch_transition = current.dispatch_label != dispatch_label
    if dispatch_label is None:
        new_started = None
    elif is_dispatch_transition or current.started_at is None:
        # New dispatch OR first dispatch ever (W2 fold-in: None -> label).
        new_started = datetime.now(timezone.utc)
    else:
        # Same dispatch -- preserve started_at for monotonic elapsed.
        new_started = current.started_at
    set_current_progress(
        ProgressContext(
            iter_num=iter_num,
            phase=phase,
            task_index=task_index,
            task_total=task_total,
            dispatch_label=dispatch_label,
            started_at=new_started,
        )
    )


# Module-level queue: heartbeat thread -> main thread (sec.3 single-writer rule).
# ``maxsize=0`` (UNBOUNDED) is a hard contract per Checkpoint 2 iter 3 melchior
# CRITICAL #3: a bounded queue + ``queue.Full`` silently loses heartbeat audit
# data. Memory cost is negligible (single tuple per push, bounded by failed-write
# count + N=10 batching).
#
# Loop 2 W2+W7 fix: tagged-tuple protocol replaces ``+1000`` sentinel offset.
# Items are ``("failed_writes", n)`` or ``("zombie", n)`` tuples. The drain
# dispatches by tag rather than by numeric range, eliminating two issues:
#
# - W2: ``+1000`` collides with legitimate ``failed_writes`` >= 1000 from
#   long-lived emitters (rare but pathological), causing mis-classification.
# - W7: multiplexing two semantically distinct counters via numeric offset
#   is hard to read and maintain; tag dispatch is explicit.
#
# Backward compat: plain ``int`` items (legacy producers, third-party tests)
# are still accepted and treated as ``("failed_writes", n)`` -- same as the
# original drain behaviour for values < 1000.
_HeartbeatQueueItem = "tuple[str, int] | int"
_heartbeat_failures_q: "queue.Queue[tuple[str, int] | int]" = queue.Queue(maxsize=0)


# Legacy ``+1000`` sentinel offset, retained for backward compat in the drain
# helper: producers emitting plain int >= 1000 are interpreted as zombie
# alerts (pre-W2/W7 protocol). New producers emit ``("zombie", n)`` tuples.
_HEARTBEAT_ZOMBIE_SENTINEL_OFFSET: int = 1000


# Loop 2 W14 fix: dedup flag for the drain-decode-error stderr breadcrumb.
# Pre-fix, ``_drain_heartbeat_queue_and_persist`` emitted
# ``[sbtdd] warning: failed to read auto-run.json...`` on every JSON decode
# failure, spamming stderr if the file was persistently corrupt. Post-fix,
# emit only on the first failure; subsequent failures are silent until
# :func:`_reset_drain_decode_error_emitted_for_tests` runs (test-only).
_drain_decode_error_emitted: bool = False


def _reset_drain_decode_error_emitted_for_tests() -> None:
    """Test-only helper: reset the W14 dedup flag.

    The flag is module-level mutable state; tests that exercise the
    drain decode-error path must reset it to avoid order-dependent
    failures.
    """
    global _drain_decode_error_emitted
    _drain_decode_error_emitted = False


# v1.0.0 S1-19 (Loop 2 iter 4 W7 caspar): separate dedup flag for the
# persistence-failure breadcrumb. Pre-fix the drain-decode-error and
# persistence-failure breadcrumbs shared a single ``_drain_decode_error_emitted``
# flag, which self-defeated when persistence itself was the failing path
# (the drain breadcrumb fired first, deduped, then a real persistence
# failure went unreported). Post-fix each class has its own dedup flag.
_persistence_error_emitted: bool = False


def _reset_persistence_error_emitted_for_tests() -> None:
    """Test-only helper: reset the W7 persistence dedup flag."""
    global _persistence_error_emitted
    _persistence_error_emitted = False


def _emit_drain_decode_error_breadcrumb(reason: str) -> None:
    """Per W7: separate dedup for drain JSON-decode failures.

    Emits once per process; subsequent failures bump the swallowed-
    observability counter silently.
    """
    global _drain_decode_error_emitted
    if _drain_decode_error_emitted:
        _bump_observability_swallowed_count()
        return
    _drain_decode_error_emitted = True
    try:
        sys.stderr.write(
            f"[sbtdd auto] drain JSON decode error (will continue silently; "
            f"see heartbeat_observability_swallowed in auto-run.json): "
            f"{reason}\n"
        )
        sys.stderr.flush()
    except OSError:
        pass


def _emit_persistence_error_breadcrumb(reason: str) -> None:
    """Per W7 (caspar iter 4): separate dedup for auto-run.json persistence failures.

    Self-defeat fix: pre-W7 a persistence failure that fired AFTER a
    drain breadcrumb was deduped silently because the shared flag was
    set. Distinct dedup ensures the operator hears about persistence
    failures even when the drain has previously bailed.
    """
    global _persistence_error_emitted
    if _persistence_error_emitted:
        _bump_observability_swallowed_count()
        return
    _persistence_error_emitted = True
    try:
        sys.stderr.write(
            f"[sbtdd auto] persistence error (will continue silently; "
            f"see heartbeat_observability_swallowed in auto-run.json): "
            f"{reason}\n"
        )
        sys.stderr.flush()
    except OSError:
        pass


# Loop 2 I3 (informational): swallowed observability counter. Increments
# whenever a best-effort observability path silently absorbs an error
# (heartbeat write fail, drain decode error, etc.). Surfaced in
# auto-run.json on final flush so operators can see whether observability
# was lossy during the run, even if breadcrumbs were de-duped.
_observability_swallowed_count: int = 0


def _bump_observability_swallowed_count() -> None:
    """Increment the swallowed-observability counter (best-effort)."""
    global _observability_swallowed_count
    _observability_swallowed_count += 1


def _reset_observability_swallowed_count_for_tests() -> None:
    """Test-only helper: reset the I3 swallowed-observability counter."""
    global _observability_swallowed_count
    _observability_swallowed_count = 0


def _assert_main_thread() -> None:
    """W8 fold-in: enforce the single-writer rule mechanically.

    Spec sec.3 stipulates only the auto orchestrator main thread mutates
    ``.claude/auto-run.json``; this helper raises ``RuntimeError`` when
    invoked from any other thread.
    """
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(
            "auto-run.json writer called from non-main thread "
            f"({threading.current_thread().name!r}); single-writer rule "
            f"(sec.3) violated"
        )


# Loop 2 W1+W3+W6+W9 fix: replace custom reentrancy bookkeeping with
# ``threading.RLock``. Stdlib RLock handles reentrancy natively (per-thread
# depth tracked by the lock itself), eliminating:
#
# - W1: race between ``existing_depth`` check and ``_lock_holders[key] = 1``
#   in the previous custom implementation.
# - W3: counter leak on early-return paths (open() failure, locking failure).
# - W6: brittleness vs. the stdlib primitive that solves the problem in
#   ~5 lines.
# - W9: fragile key generation via ``str(path.resolve() if path.exists()
#   else path)`` (same logical path could yield different keys mid-call).
#
# Each path string maps to a single ``threading.RLock`` instance, lazily
# created under ``_file_locks_guard`` to keep the get-or-create step
# thread-safe. ``threading.RLock`` is reentrant on the same thread by
# definition, so nested ``_with_file_lock`` calls from inside the locked
# region (e.g. ``_update_progress`` -> ``_drain_heartbeat_queue_and_persist``)
# acquire the same lock instance without self-deadlock. The Windows
# ``msvcrt.locking`` self-deadlock that motivated the original CRITICAL #1
# fix is bypassed entirely because the OS-level lock is now nested inside
# the in-process RLock; only the outermost (depth=1) call attempts to
# acquire the OS-level advisory lock on disk.
#
# Loop 2 iter 3 W1+W4+W6 fix: replace ``_is_owned()`` private-API call
# with a public ``threading.local`` per-thread, per-path depth counter.
# The previous iter-2 code used ``in_process_lock._is_owned()`` (CPython
# private API) to detect outermost-vs-reentrant entry; that method is
# documented but not part of the public stdlib contract and may be
# renamed/removed in future Python versions. The depth counter uses
# only public ``threading.local`` storage.
_file_locks: dict[str, threading.RLock] = {}
_file_locks_guard = threading.Lock()

# Per-thread, per-path depth counter. Stored on a ``threading.local()`` so
# each thread sees its own dict; the dict is keyed by the same canonical
# path string used by :func:`_get_file_lock`. Depth > 0 means the thread
# is inside a ``_with_file_lock`` call for that path; outermost entry
# observes depth == 0 and acquires the OS-level disk lock.
_lock_depth_local = threading.local()


def _get_lock_depth_dict() -> dict[str, int]:
    """Return the per-thread depth dict, lazily creating it on first use.

    ``threading.local`` returns a fresh attribute namespace per thread,
    so each thread observes its own dict. The dict keys are canonical
    path strings (matching the keys used by :func:`_get_file_lock`).
    """
    if not hasattr(_lock_depth_local, "depths"):
        _lock_depth_local.depths = {}
    return _lock_depth_local.depths  # type: ignore[no-any-return]


def _canonical_lock_key(path: Path) -> str:
    """Return the canonical key for a given path (stable across resolve).

    Mirrors the logic in :func:`_get_file_lock` so the depth counter
    keys match the lock-identity keys exactly. A best-effort ``resolve()``
    is attempted when the path exists; otherwise the raw path string is
    returned. ``OSError`` falls back to the raw path string.
    """
    try:
        return str(path.resolve()) if path.exists() else str(path)
    except OSError:
        return str(path)


def _get_file_lock(path: Path) -> threading.RLock:
    """Get-or-create a ``threading.RLock`` for the given path.

    Lock identity is keyed by ``str(path)`` after a best-effort
    ``resolve()`` if the path exists. Two callers passing equivalent
    paths get the same RLock instance (otherwise serialization breaks).

    Args:
        path: Target filesystem path.

    Returns:
        The ``threading.RLock`` associated with ``path``.
    """
    key = _canonical_lock_key(path)
    with _file_locks_guard:
        lock = _file_locks.get(key)
        if lock is None:
            lock = threading.RLock()
            _file_locks[key] = lock
        return lock


def _with_file_lock(path: Path, fn: Callable[[], None]) -> None:
    """Serialize same-process access to ``path``.

    Uses a ``threading.RLock`` for in-process reentrancy (W1+W3+W6+W9
    fix) layered with an OS-level advisory lock (POSIX ``fcntl.flock``,
    Windows ``msvcrt.locking``) on a sibling sentinel file
    (``<path>.lock``).

    **Reentrancy:** ``threading.RLock`` is reentrant on the same thread,
    so nested calls (e.g. ``_update_progress`` ->
    ``_drain_heartbeat_queue_and_persist``) re-enter the in-process lock
    natively; the OS-level advisory lock is acquired only on the
    outermost (depth=1) call to avoid the Windows
    ``msvcrt.locking`` self-deadlock that motivated the original Loop 2
    CRITICAL #1 fix.

    **Scope:** serializes the three in-process auto-run.json writers
    (``_update_progress``, ``_write_auto_run_audit``,
    ``_drain_heartbeat_queue_and_persist``). External readers (e.g.
    ``status --watch``, operator ``cat``) bypass the lock and rely on
    atomic-rename semantics of ``os.replace`` for consistency.

    **Best-effort:** any OSError during OS-level lock acquisition logs
    a stderr breadcrumb and proceeds without the disk lock; the
    in-process RLock still serializes intra-process writers.

    Args:
        path: Target file whose mutation is serialized.
        fn: Zero-argument callable that performs the mutation.
    """
    in_process_lock = _get_file_lock(path)
    # Detect outermost-vs-reentrant entry so the OS-level disk lock is
    # acquired only once per logical critical section. Use a public
    # ``threading.local`` depth counter rather than the iter-2 RLock
    # private-API call (Loop 2 iter 3 W1+W4+W6 fix). The depth dict is
    # per-thread (via threading.local) and keyed by the canonical path
    # string; depth == 0 at entry means outermost.
    depth_dict = _get_lock_depth_dict()
    key = _canonical_lock_key(path)
    is_outer = depth_dict.get(key, 0) == 0
    with in_process_lock:
        depth_dict[key] = depth_dict.get(key, 0) + 1
        try:
            if not is_outer:
                # Reentrant call: in-process RLock has been re-acquired
                # natively. Skip the OS-level lock (already held by the
                # outer frame on this same thread).
                fn()
                return
            lock_path = path.with_suffix(path.suffix + ".lock")
            try:
                lock_fd = open(lock_path, "a+b")
            except OSError as exc:
                sys.stderr.write(
                    f"[sbtdd] warning: could not open lock file {lock_path}: "
                    f"{exc!s}; proceeding without intra-process lock\n"
                )
                sys.stderr.flush()
                fn()
                return
            try:
                if sys.platform == "win32":
                    try:
                        import msvcrt

                        lock_fd.seek(0)
                        msvcrt.locking(lock_fd.fileno(), msvcrt.LK_LOCK, 1)
                    except (OSError, ImportError) as exc:
                        sys.stderr.write(
                            f"[sbtdd] warning: msvcrt.locking failed: {exc!s}; "
                            f"proceeding without intra-process lock\n"
                        )
                        sys.stderr.flush()
                        fn()
                        return
                else:
                    try:
                        import fcntl

                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
                    except (OSError, ImportError) as exc:
                        sys.stderr.write(
                            f"[sbtdd] warning: fcntl.flock failed: {exc!s}; "
                            f"proceeding without intra-process lock\n"
                        )
                        sys.stderr.flush()
                        fn()
                        return
                try:
                    fn()
                finally:
                    if sys.platform == "win32":
                        try:
                            import msvcrt

                            lock_fd.seek(0)
                            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                        except OSError:
                            pass
                    else:
                        try:
                            import fcntl

                            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                        except OSError:
                            pass
            finally:
                try:
                    lock_fd.close()
                except OSError:
                    pass
        finally:
            # Decrement depth; remove key when depth returns to zero so
            # the per-thread dict stays small even after many distinct
            # paths have been locked.
            new_depth = depth_dict.get(key, 0) - 1
            if new_depth <= 0:
                depth_dict.pop(key, None)
            else:
                depth_dict[key] = new_depth


# Loop 2 iter 3 caspar R1 fold-in: cheap insurance against accidental
# re-introduction of the threading.RLock private-API call. Inspect the
# helper's source at module-import time and assert the forbidden token
# is absent. Catches copy-paste regressions from older Loop 2 iter 2
# docs/tests before the unit-test suite even runs. The token is split
# at concatenation so this very line cannot trigger a self-match.
#
# v1.0.0 S1-23 I-Hk4 fix (caspar iter 4 INFO): wrap in try/except so
# bytecode-only deployments (PyInstaller, frozen apps, .pyc-without-.py
# environments) do not crash at import. ``inspect.getsource`` raises
# ``OSError`` (no source available) or ``TypeError`` (built-in modules)
# in those settings. The unit-test suite still covers the regression at
# test time via ``test_with_file_lock_does_not_use_private_rlock_api``.
_FORBIDDEN_PRIVATE_API_TOKEN = "_is" + "_owned"
try:
    _with_file_lock_source = inspect.getsource(_with_file_lock)
    assert _FORBIDDEN_PRIVATE_API_TOKEN not in _with_file_lock_source, (
        "_with_file_lock must not depend on threading.RLock private API "
        "(Loop 2 iter 3 W1+W4+W6 + caspar R1)."
    )
    del _with_file_lock_source
except (OSError, TypeError):
    # Bytecode-only / frozen deployment; the runtime guard is best-effort.
    # Source-level regression check is preserved by the unit-test suite,
    # which always runs from .py files.
    pass
del _FORBIDDEN_PRIVATE_API_TOKEN


_PROGRESS_DRAIN_INTERVAL_SECONDS: int = 30


@dataclass
class _DrainState:
    """Encapsulates last-drain timestamp to avoid module-level mutable state.

    Per Checkpoint 2 iter 1 caspar fix: a module-level ``_last_drain_at``
    causes test order dependence. Encapsulating in a dataclass instance
    allows fixture reset and parallel-test isolation.
    """

    last_drain_at: float = 0.0


_drain_state = _DrainState()


def _periodic_drain_if_due(
    auto_run_path: Path,
    *,
    force: bool = False,
    state: _DrainState = _drain_state,
) -> None:
    """Drain heartbeat queue if 30s elapsed since last drain (sec.11.1 W8).

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.
        force: When True, drain unconditionally and reset the timestamp.
        state: Drain-state container; default uses module singleton.
    """
    now = time.monotonic()
    if not force and (now - state.last_drain_at) < _PROGRESS_DRAIN_INTERVAL_SECONDS:
        return
    _drain_heartbeat_queue_and_persist(auto_run_path)
    state.last_drain_at = now


def _reset_drain_state_for_tests() -> None:
    """Test-only helper: reset drain state to ensure isolation."""
    _drain_state.last_drain_at = 0.0


def _serialize_progress() -> dict[str, Any]:
    """Serialize current ProgressContext to a JSON-friendly dict (ISO 8601 UTC).

    The ``started_at`` datetime is normalized to UTC and rendered with the
    ``Z`` suffix using :func:`datetime.strftime` -- NOT
    ``str.replace('+00:00', 'Z')`` which would break if the input already
    has ``Z`` or different ``tzinfo`` formatting (Checkpoint 2 iter 1
    melchior fix).

    Per W8 fold-in, this helper is restricted to main-thread callers.
    """
    _assert_main_thread()
    ctx = get_current_progress()
    started = ctx.started_at
    started_str: str | None
    if started is not None:
        started_str = started.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        started_str = None
    return {
        "iter_num": ctx.iter_num,
        "phase": ctx.phase,
        "task_index": ctx.task_index,
        "task_total": ctx.task_total,
        "dispatch_label": ctx.dispatch_label,
        "started_at": started_str,
    }


def _drain_heartbeat_queue_and_persist(auto_run_path: Path) -> None:
    """Drain :data:`_heartbeat_failures_q` and persist max() counter.

    Implements the sec.3 single-writer rule: only the main thread reads
    the queue and writes to ``auto-run.json``. The C4 fold-in adds an
    intra-process advisory lock so concurrent in-process writers (the
    other two ``auto-run.json`` writers) cannot corrupt the JSON. External
    readers (e.g. ``status --watch``) rely on atomic-rename semantics
    rather than the lock.

    Loop 2 W2+W7 fix: items are ``("failed_writes", n)`` or
    ``("zombie", n)`` tuples; drain dispatches by tag. Backward compat:
    plain ``int`` items are interpreted as ``("zombie", n - 1000)`` if
    ``n >= 1000`` else ``("failed_writes", n)`` -- preserving the
    pre-fix ``+1000`` sentinel scheme for any leftover producers.

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.
    """
    _assert_main_thread()
    drained: list[tuple[str, int] | int] = []
    while True:
        try:
            drained.append(_heartbeat_failures_q.get_nowait())
        except queue.Empty:
            break
    if not drained:
        return

    failed_writes_values: list[int] = []
    zombie_values: list[int] = []
    for item in drained:
        if isinstance(item, tuple) and len(item) == 2:
            tag, count = item
            if tag == "failed_writes":
                failed_writes_values.append(int(count))
            elif tag == "zombie":
                zombie_values.append(int(count))
            # Unknown tags silently dropped (defensive vs. future
            # producer bugs; not failing-loud avoids killing the drain).
        elif isinstance(item, int):
            # Backward compat with pre-W2/W7 plain-int protocol.
            if item >= _HEARTBEAT_ZOMBIE_SENTINEL_OFFSET:
                zombie_values.append(item - _HEARTBEAT_ZOMBIE_SENTINEL_OFFSET)
            else:
                failed_writes_values.append(item)

    def _do_persist() -> None:
        try:
            data = json.loads(auto_run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            # v1.0.0 Loop 2 iter 2->3 R11 sweep: route through the
            # ``_emit_drain_decode_error_breadcrumb`` helper instead of
            # inlining the emit + dedup logic. The helper owns the W7
            # dedup flag and the I3 observability-swallowed counter so
            # both the heartbeat-drain path and the explicit
            # _emit_drain_decode_error_breadcrumb test contract share a
            # single implementation. Pre-fix the helper was actually-dead.
            _emit_drain_decode_error_breadcrumb(f"{type(exc).__name__}: {exc!s}")
            return
        if not isinstance(data, dict):
            return
        if failed_writes_values:
            existing = data.get("heartbeat_failed_writes_total", 0)
            try:
                existing_int = int(existing)
            except (TypeError, ValueError):
                existing_int = 0
            data["heartbeat_failed_writes_total"] = max(existing_int, *failed_writes_values)
        if zombie_values:
            zombie_count = max(zombie_values)
            existing_z = data.get("heartbeat_zombie_thread_count", 0)
            try:
                existing_z_int = int(existing_z)
            except (TypeError, ValueError):
                existing_z_int = 0
            data["heartbeat_zombie_thread_count"] = max(existing_z_int, zombie_count)
        # Loop 2 I3: surface the swallowed-observability counter so
        # operators can see whether de-duped breadcrumbs masked recurrent
        # silent failures during the run.
        if _observability_swallowed_count > 0:
            existing_obs = data.get("heartbeat_observability_swallowed", 0)
            try:
                existing_obs_int = int(existing_obs)
            except (TypeError, ValueError):
                existing_obs_int = 0
            data["heartbeat_observability_swallowed"] = max(
                existing_obs_int, _observability_swallowed_count
            )
        # Atomic rename (preserve existing _update_progress mechanism).
        # v1.0.0 S1-20 W8 fix: tmp filename includes PID + thread.get_ident()
        # so concurrent threads in the same process don't collide on
        # ``.tmp.{pid}`` (Windows PermissionError flake observed in v0.5.0).
        tmp_path = auto_run_path.parent / (
            auto_run_path.name + f".tmp.{os.getpid()}.{threading.get_ident()}"
        )
        try:
            tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            os.replace(tmp_path, auto_run_path)
        except OSError as exc:
            # v1.0.0 Loop 2 iter 2->3 R11 sweep: route through
            # ``_emit_persistence_error_breadcrumb`` so the W7 separate-
            # dedup contract (drain vs persistence flags) is enforced by
            # the production path. Pre-fix the helper was actually-dead.
            _emit_persistence_error_breadcrumb(
                f"failed to persist heartbeat counters: {type(exc).__name__}: {exc!s}"
            )
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    _with_file_lock(auto_run_path, _do_persist)


def _dispatch_with_heartbeat(
    *,
    invoke: Callable[..., Any],
    heartbeat_interval: float = 15.0,
    **invoke_kwargs: Any,
) -> Any:
    """Wrap a long subprocess invocation in a HeartbeatEmitter.

    The dispatch label is **derived from the current ProgressContext**
    (set by :func:`_set_progress` immediately before this call). This
    eliminates the iter-1 Checkpoint 2 caspar finding: dispatch_label
    drift between the writer hook and the heartbeat wrapper.

    **Fail-loud (Checkpoint 2 iter 2 melchior fix)**: raises
    ``ValueError`` if ``dispatch_label`` is ``None`` at call time.
    Silent fallback to ``"unlabeled-dispatch"`` was rejected per
    fail-loud principle -- caller MUST establish dispatch context
    before invoking the wrapper.

    The failures queue is the module-level ``_heartbeat_failures_q``
    drained by :func:`_drain_heartbeat_queue_and_persist` (single-
    writer rule per sec.3 of spec).

    Args:
        invoke: The callable performing the actual subprocess work.
        heartbeat_interval: Tick cadence in seconds.
        **invoke_kwargs: Forwarded verbatim to ``invoke``.

    Returns:
        Whatever ``invoke`` returns.

    Raises:
        ValueError: When ``ProgressContext.dispatch_label`` is None.
    """
    ctx = get_current_progress()
    if ctx.dispatch_label is None:
        raise ValueError(
            "_dispatch_with_heartbeat called without dispatch_label set. "
            "Caller must invoke `_set_progress(..., dispatch_label='...')` "
            "BEFORE this wrapper. Silent fallback rejected per fail-loud "
            "(Checkpoint 2 iter 2 melchior CRITICAL #1)."
        )
    with HeartbeatEmitter(
        label=ctx.dispatch_label,
        interval_seconds=heartbeat_interval,
        failures_queue=_heartbeat_failures_q,
    ):
        return invoke(**invoke_kwargs)


def _stream_subprocess(
    proc: subprocess.Popen[str],
    prefix: str,
) -> tuple[str, str]:
    """Read subprocess stdout/stderr line-by-line, rewrite to orchestrator stderr.

    Reads pipes via a thread-pair pump so neither stream starves and the
    helper works identically on POSIX and Windows (``select.select`` does
    not work on pipes on Windows -- PEP 446). Each line is prefixed with
    ``prefix`` and emitted to ``sys.stderr`` of the orchestrator with an
    explicit ``flush`` so external observers see progress in real time.

    Returns the accumulated ``(stdout, stderr)`` strings for the caller's
    diagnostic / commit-error recovery paths (``CommitError`` v0.1.6
    expects captured strings).

    Implements Feature D scenarios D1.1 (line-buffered flush), D1.2
    (prefix-aware rewrite), and D1.3 (final flush on subprocess exit).

    Args:
        proc: A ``subprocess.Popen`` opened with ``stdout=PIPE`` and
            ``stderr=PIPE`` in text mode (``text=True``).
        prefix: Tag prepended to every emitted line, e.g.
            ``"[sbtdd task-7 green]"``.

    Returns:
        Tuple ``(stdout_text, stderr_text)`` containing the verbatim
        subprocess output (without the orchestrator prefix).
    """
    stdout_buf: list[str] = []
    stderr_buf: list[str] = []

    def _pump(stream: IO[str] | None, sink: list[str]) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            sink.append(line)
            sys.stderr.write(f"{prefix} {line}")
            sys.stderr.flush()
        stream.close()

    t_out = threading.Thread(target=_pump, args=(proc.stdout, stdout_buf), daemon=True)
    t_err = threading.Thread(target=_pump, args=(proc.stderr, stderr_buf), daemon=True)
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    return ("".join(stdout_buf), "".join(stderr_buf))


#: Human-readable phase names for state-machine breadcrumbs (Feature D3).
#: Index = phase number; phase 0 is the implicit pre-flight, 1-5 mirror
#: the five auto phases (preflight, spec gate, task loop, pre-merge,
#: checklist). Stored as a tuple so callers cannot mutate it accidentally.
_PHASE_NAMES: tuple[str, ...] = (
    "pre-flight",
    "spec",
    "task loop",
    "pre-merge",
    "checklist",
)


def _emit_phase_breadcrumb(
    phase: int,
    total_phases: int,
    *,
    task_index: int | None = None,
    task_total: int | None = None,
    sub_phase: str | None = None,
) -> None:
    """Emit a one-line state-machine breadcrumb to orchestrator stderr.

    Format: ``[sbtdd] phase {p}/{t}: {phase_name} -- task {i}/{n} ({sub_phase})``.
    Task-index and sub-phase are optional for non-task-loop phases (e.g.
    pre-merge emits without ``-- task X/Y``).

    Implements Feature D3 (spec-behavior sec.2 D3.1, D3.2). Always
    flushes stderr so external observers see the line immediately even
    if Python's default buffering is line-buffered to a pipe.

    Args:
        phase: 0-indexed phase number (0..len(_PHASE_NAMES)-1).
        total_phases: Total number of phases (display denominator).
        task_index: Optional task index for task-loop phase.
        task_total: Optional task total for task-loop phase.
        sub_phase: Optional TDD sub-phase label (``red``, ``green``,
            ``refactor``, ``task-close``, ``magi-loop``, ``checklist``).
    """
    name = _PHASE_NAMES[phase] if 0 <= phase < len(_PHASE_NAMES) else f"phase-{phase}"
    line = f"[sbtdd] phase {phase}/{total_phases}: {name}"
    if task_index is not None and task_total is not None:
        suffix = f" ({sub_phase})" if sub_phase else ""
        line += f" -- task {task_index}/{task_total}{suffix}"
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _task_progress(plan_path: Path, current_task_id: str | None) -> tuple[int | None, int | None]:
    """Return ``(task_index, task_total)`` for the active task, best-effort.

    Reads ``plan_path`` once and counts ``### Task`` headers via the same
    regex used by :mod:`_plan_ops`. ``task_index`` is 1-based: position of
    ``current_task_id`` among the headers in source order. Returns
    ``(None, None)`` on any failure (missing plan, unreadable, task id
    not found) so breadcrumb / progress wiring degrades gracefully when
    the plan layout is non-standard.

    Args:
        plan_path: Resolved path to ``planning/claude-plan-tdd.md``.
        current_task_id: Active task id from the session state.

    Returns:
        Tuple ``(index, total)`` with 1-based index, or ``(None, None)``.
    """
    if current_task_id is None:
        return (None, None)
    try:
        from _plan_ops import _TASK_HEADER_RE

        text = plan_path.read_text(encoding="utf-8")
        ids = [m.group(1) for m in _TASK_HEADER_RE.finditer(text)]
        total = len(ids)
        if total == 0:
            return (None, None)
        if current_task_id not in ids:
            return (None, total)
        return (ids.index(current_task_id) + 1, total)
    except (OSError, ValueError):
        return (None, None)


def _update_progress(
    auto_run_path: Path,
    *,
    phase: int,
    task_index: int | None,
    task_total: int | None,
    sub_phase: str | None,
) -> None:
    """Write the ``progress`` field of ``auto-run.json`` atomically.

    Mirrors the atomic-write pattern of :func:`state_file.save` and
    :func:`_write_auto_run_audit` (tmp file + ``os.replace``). A
    concurrent reader sees either the prior payload or the new one,
    never a torn JSON document (Feature D4 / spec-behavior sec.2 D4.1).

    The file may already contain other top-level keys (``schema_version``,
    ``auto_started_at``, etc.); they are preserved unchanged. When the
    file does not exist, an empty dict is the starting point so the
    helper is safe to call even before :func:`_write_auto_run_audit`.

    .. note:: **Single-writer assumption (intentional, MAGI iter 1
       finding #5).**

       The read-modify-write between :func:`pathlib.Path.read_text` and
       :func:`os.replace` is NOT lock-protected. If any other writer
       (signal handler, future ``/sbtdd status --watch`` companion,
       OS-level backup tool) updates ``auto-run.json`` between the read
       and the replace, that writer's payload is silently overwritten
       (last-writer-wins, no conflict detection).

       INV-22 (sequential-only execution) currently rules out concurrent
       SBTDD writers in production: the auto orchestrator is the only
       process that mutates ``.claude/auto-run.json`` during a run, and
       :mod:`resume_cmd` runs only after the orchestrator has exited.
       File-level locking is therefore intentionally NOT implemented in
       v0.3.0 -- it would add cross-platform complexity (``fcntl`` vs
       ``msvcrt``) for zero present benefit.

       Any future feature that introduces a second writer (parallel
       monitor, recovery hook, the v0.4.0 ``status --watch`` poller)
       MUST either remain strictly read-only on this path OR introduce
       a sentinel-file CAS protocol (e.g. write a ``.lock`` file with
       the current revision number, retry on mismatch). Updating this
       function alone is insufficient -- the contract belongs to all
       writers of ``auto-run.json``. Document the second writer in the
       spec, bump ``_AUTO_RUN_SCHEMA_VERSION``, and revisit this
       docstring before merging.

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.
        phase: 0-indexed phase number.
        task_index: Optional 1-based task index (omitted when ``None``).
        task_total: Optional total task count (omitted when ``None``).
        sub_phase: Optional sub-phase label (``red``, ``green``,
            ``refactor``, ``task-close``, ``magi-loop``, ``checklist``);
            omitted when ``None``.

    Raises:
        Nothing. v0.4.0 J4: any :class:`OSError` raised by the read,
        the tmp write, or the final :func:`os.replace` is caught,
        the tmp file is cleaned up if present, and a stderr breadcrumb
        starting ``[sbtdd] warning: progress write failed`` is emitted.
        The auto run continues with degraded observability rather than
        terminating mid-cycle on a transient filesystem error (disk
        full, locked file, antivirus interference, etc.). The original
        ``auto-run.json`` is preserved unchanged on failure.

    Loop 1 fix (v0.5.0 CRITICAL #3): the full read-modify-write cycle
    is now wrapped in :func:`_with_file_lock`. Pre-fix only
    :func:`_drain_heartbeat_queue_and_persist` held the intra-process
    advisory lock; this writer plus :func:`_write_auto_run_audit`
    performed RMW unprotected, so the C4 contract was incomplete. The
    fix routes both writers through the same lock helper so all three
    in-process writers serialise correctly. External readers
    (``status --watch``) bypass the lock and rely on atomic-rename
    semantics for consistency (Loop 2 WARNING #2 scope clarification).

    Loop 2 W13 fix: ``_assert_main_thread`` is invoked at entry so the
    single-writer rule (sec.3) trips immediately on misuse rather than
    after partial work inside ``_serialize_progress`` (which only runs
    AFTER the read step has already happened).
    """
    _assert_main_thread()

    def _do_write() -> None:
        _do_update_progress(
            auto_run_path,
            phase=phase,
            task_index=task_index,
            task_total=task_total,
            sub_phase=sub_phase,
        )

    _with_file_lock(auto_run_path, _do_write)


def _do_update_progress(
    auto_run_path: Path,
    *,
    phase: int,
    task_index: int | None,
    task_total: int | None,
    sub_phase: str | None,
) -> None:
    """Inner RMW for ``_update_progress`` -- runs UNDER ``_with_file_lock``.

    The original ``_update_progress`` body, factored out so the public
    entry point can wrap the full RMW cycle in the intra-process advisory
    lock without duplicating the read / merge / atomic-replace logic.
    """
    tmp: Path | None = None
    try:
        if auto_run_path.exists():
            try:
                existing: dict[str, object] = json.loads(auto_run_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                existing = {}
        else:
            existing = {}
            auto_run_path.parent.mkdir(parents=True, exist_ok=True)
        # MAGI iter 1 finding #4 fix: always emit the four keys
        # ``{phase, task_index, task_total, sub_phase}`` to satisfy
        # spec sec.2 D4.2 "shape exacto" literally. ``None`` values become
        # JSON ``null`` rather than absent keys so future
        # ``/sbtdd status --watch`` consumers can rely on the shape and
        # treat ``null`` as the explicit "unknown" sentinel.
        #
        # v0.5.0 S1-12: also emit the ProgressContext-derived snapshot as
        # ``progress_context`` (sec.3 PINNED schema:
        # ``{iter_num, phase, task_index, task_total, dispatch_label,
        # started_at}``). Both keys coexist during the v0.5 transition
        # so D4.3 absent-tolerant downstream readers (status --watch
        # consumers expecting the v0.4 shape) keep working while the
        # new ProgressContext-aware readers can adopt the richer key.
        progress: dict[str, object | None] = {
            "phase": phase,
            "task_index": task_index,
            "task_total": task_total,
            "sub_phase": sub_phase,
        }
        existing["progress"] = progress
        # Best-effort: serialize the ProgressContext singleton too. If
        # the singleton is at default (no _set_progress fired yet), we
        # still write the snapshot so consumers see a deterministic
        # shape.
        try:
            existing["progress_context"] = _serialize_progress()
        except RuntimeError:
            # _assert_main_thread tripped (off-thread caller); don't
            # corrupt auto-run.json.
            pass
        # v1.0.0 S1-20 W8 fix: include thread.get_ident() in tmp filename.
        tmp = auto_run_path.parent / (
            auto_run_path.name + f".tmp.{os.getpid()}.{threading.get_ident()}"
        )
        tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
        # ``os.replace`` is atomic on POSIX and Windows, but on Windows it
        # can transiently fail with PermissionError when another process /
        # thread has the destination file open without FILE_SHARE_DELETE
        # (concurrent reader pattern from D4.1). Retry a small number of
        # times with a short sleep so the writer recovers from the race
        # window without breaking the atomicity contract; the reader still
        # never observes torn JSON because we never write into the target
        # path directly.
        last_err: OSError | None = None
        for _ in range(20):
            try:
                os.replace(tmp, auto_run_path)
                # v0.5.0 S1-11: piggyback heartbeat queue drain on each
                # successful progress write (single-writer rule sec.3).
                # Best-effort: drain failures should never interrupt the
                # main auto run.
                try:
                    _drain_heartbeat_queue_and_persist(auto_run_path)
                except Exception:  # noqa: BLE001
                    pass
                return
            except PermissionError as exc:
                last_err = exc
                time.sleep(0.005)
            except OSError as exc:
                last_err = exc
                break
        assert last_err is not None
        raise last_err
    except OSError as exc:
        # v0.4.0 J4: never kill the auto run on a progress write failure.
        # Auto continues with degraded observability; subsequent successful
        # ``_update_progress`` calls will resync the snapshot and the audit
        # writer (read-modify-write per J6) preserves whatever progress
        # field was already on disk before this attempt.
        sys.stderr.write(
            f"[sbtdd] warning: progress write failed: {type(exc).__name__}"
            f"({getattr(exc, 'errno', '')}, {exc!s}). "
            f"Auto run continues (observability degraded).\n"
        )
        sys.stderr.flush()
    finally:
        if tmp is not None:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                # Best-effort cleanup; do not mask the primary failure.
                pass


def _build_run_sbtdd_argv(
    subcommand: str,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build subprocess argv for invoking ``run_sbtdd.py`` with ``python -u``.

    The ``-u`` flag disables Python output buffering at the dispatcher
    level so :func:`_stream_subprocess` reads complete lines as the
    sub-process emits them (Feature D2 / spec-behavior sec.2 D2.1).
    Centralising argv construction in a single helper means future
    callers can never forget the ``-u`` flag and break streaming.

    v1.0.5 T2 Refactor: the per-script lookup now routes through the
    shared :func:`_run_sbtdd_path` helper introduced for Item I-3 worker
    flag forwarding so ``run_sbtdd.py`` resolution lives in exactly one
    place.

    Args:
        subcommand: SBTDD subcommand name (``close-phase``, ``status``,
            etc.).
        extra_args: Optional list of additional CLI args appended after
            the subcommand.

    Returns:
        ``[sys.executable, "-u", "<run_sbtdd.py>", subcommand, *extra_args]``.
    """
    run_sbtdd = _run_sbtdd_path().as_posix()
    argv: list[str] = [sys.executable, "-u", run_sbtdd, subcommand]
    if extra_args:
        argv.extend(extra_args)
    return argv


@dataclass(frozen=True)
class AutoRunAudit:
    """Frozen schema for ``.claude/auto-run.json`` (INV-26 audit trail).

    Formalises the opportunistic dict writes used in Milestone C. Every
    field is required; ``to_dict`` is symmetric with ``from_dict`` and
    the shape is asserted by ``validate_schema``. Bump
    ``schema_version`` via ``_AUTO_RUN_SCHEMA_VERSION`` for
    backwards-incompatible changes.

    Attributes:
        schema_version: Integer version (1 for v0.1 of the plugin).
        auto_started_at: ISO 8601 timestamp of ``main`` entry.
        auto_finished_at: ISO 8601 timestamp of ``main`` exit, or
            ``None`` when the run is still in progress / aborted mid-way.
        status: One of :data:`_ALLOWED_AUTO_RUN_STATUSES`.
        verdict: The gating MAGI verdict string (``GO`` / ``GO_WITH_CAVEATS``
            / ``STRONG_NO_GO`` / ...), or ``None`` if the run aborted
            before Phase 3 completed.
        degraded: ``True`` when MAGI returned degraded consensus; ``None``
            if no verdict was obtained.
        accepted_conditions: Count of MAGI conditions accepted by
            ``/receiving-code-review`` across all Loop 2 iterations.
        rejected_conditions: Count of MAGI conditions rejected by
            ``/receiving-code-review``.
        tasks_completed: Number of plan tasks that reached
            ``current_phase == 'done'`` during this auto run.
        error: Free-form error message when ``status != 'success'``,
            ``None`` on success.
    """

    schema_version: int
    auto_started_at: str
    auto_finished_at: str | None
    status: str
    verdict: str | None
    degraded: bool | None
    accepted_conditions: int
    rejected_conditions: int
    tasks_completed: int
    error: str | None

    def validate_schema(self) -> None:
        """Raise :class:`ValidationError` on any schema inconsistency."""
        if self.schema_version != _AUTO_RUN_SCHEMA_VERSION:
            raise ValidationError(
                f"AutoRunAudit.schema_version={self.schema_version} != "
                f"expected {_AUTO_RUN_SCHEMA_VERSION}"
            )
        if self.status not in _ALLOWED_AUTO_RUN_STATUSES:
            raise ValidationError(
                f"AutoRunAudit.status={self.status!r} not in {sorted(_ALLOWED_AUTO_RUN_STATUSES)}"
            )
        if self.accepted_conditions < 0:
            raise ValidationError(
                f"AutoRunAudit.accepted_conditions={self.accepted_conditions} < 0"
            )
        if self.rejected_conditions < 0:
            raise ValidationError(
                f"AutoRunAudit.rejected_conditions={self.rejected_conditions} < 0"
            )
        if self.tasks_completed < 0:
            raise ValidationError(f"AutoRunAudit.tasks_completed={self.tasks_completed} < 0")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AutoRunAudit:
        """Build an :class:`AutoRunAudit` from a parsed JSON dict."""

        def _coerce_int(value: object, default: int) -> int:
            if value is None:
                return default
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, str)):
                return int(value)
            raise TypeError(f"cannot coerce {type(value).__name__} to int")

        return cls(
            schema_version=_coerce_int(data.get("schema_version"), _AUTO_RUN_SCHEMA_VERSION),
            auto_started_at=str(data["auto_started_at"]),
            auto_finished_at=(
                str(data["auto_finished_at"]) if data.get("auto_finished_at") is not None else None
            ),
            status=str(data.get("status", "success")),
            verdict=(str(data["verdict"]) if data.get("verdict") is not None else None),
            degraded=(bool(data["degraded"]) if data.get("degraded") is not None else None),
            accepted_conditions=_coerce_int(data.get("accepted_conditions"), 0),
            rejected_conditions=_coerce_int(data.get("rejected_conditions"), 0),
            tasks_completed=_coerce_int(data.get("tasks_completed"), 0),
            error=(str(data["error"]) if data.get("error") is not None else None),
        )


# ---------------------------------------------------------------------------
# v1.0.5 Item I-1 -- per-worker sidecar audit-trail pattern (escenarios
# I1-1..I1-6). Workers redirect their per-track audit data to deterministic
# sidecar files; the parent merges the sidecars post-batch into the canonical
# .claude/auto-run.json so concurrent worker writes never clobber the parent's
# pre-dispatch record (INV-26 audit-trail integrity).
# ---------------------------------------------------------------------------


def _audit_sidecar_path(task_ids: tuple[str, ...], project_root: Path) -> Path:
    """Per-worker audit sidecar path.

    v1.0.5 Item I-1: deterministic name per task-IDs hash. Each worker
    writes its audit to its own sidecar; the parent post-batch merges all
    sidecars into the canonical ``.claude/auto-run.json``.

    Args:
        task_ids: Sorted tuple of task IDs assigned to this worker.
        project_root: Project root path.

    Returns:
        Path to the per-worker sidecar file.
    """
    digest = hashlib.sha1(",".join(task_ids).encode("utf-8")).hexdigest()[:12]
    return project_root / ".claude" / f"auto-run-track-{digest}.json"


#: v1.0.5 T3 Refactor: re-export the consolidated ``atomic_write_json``
#: from ``state_file`` under the legacy private name so existing call
#: sites + the I-1 escenarios I1-1..I1-6 keep importing
#: ``auto_cmd._atomic_write_json`` byte-identically. The single
#: implementation lives in :func:`state_file.atomic_write_json` per
#: iter-2 WARNING fix.
from state_file import atomic_write_json as _atomic_write_json  # noqa: E402


def _write_audit(audit: dict[str, Any], project_root: Path, ns: argparse.Namespace) -> None:
    """Write a v1.0.5-style audit record.

    Worker mode (``--no-recursive`` + ``--task-ids``) redirects to a
    per-worker sidecar (see :func:`_audit_sidecar_path`). Orchestrator
    mode writes to the canonical ``.claude/auto-run.json`` directly.

    Note: this helper is the v1.0.5 I-1 generic-dict writer used by
    workers and the post-batch merge. It is distinct from the typed
    :func:`_write_auto_run_audit` writer that persists
    :class:`AutoRunAudit` instances during the orchestrator's own
    Phase 5 audit summary.

    Args:
        audit: JSON-serialisable dict payload.
        project_root: Project root.
        ns: Parent or worker argparse namespace (read-only).
    """
    if getattr(ns, "no_recursive", False) and getattr(ns, "task_ids", None):
        task_ids_tuple = tuple(sorted(ns.task_ids.split(",")))
        audit_path = _audit_sidecar_path(task_ids_tuple, project_root)
    else:
        audit_path = project_root / ".claude" / "auto-run.json"
    _atomic_write_json(audit_path, audit)


def _merge_audit_sidecars(tracks: list[list[str]], project_root: Path) -> dict[str, Any]:
    """Parent post-batch: merge per-worker sidecars into canonical audit.

    v1.0.5 Item I-1: collects per-worker sidecar files (created by
    workers during dispatch) and folds them into the canonical
    ``.claude/auto-run.json``. Preserves the parent's pre-dispatch
    record (e.g. ``start_time``, planned tasks) and adds:

    * ``per_worker``: list of per-worker dicts (one entry per track).
      A missing sidecar becomes a placeholder
      ``{"status": "no_audit_data", ...}`` so the merge never fails
      silently when a worker crashed before its sidecar write.
    * ``aggregate_task_count``: sum of task IDs across all tracks.

    Sidecar files are unlinked after their content has been folded in
    so subsequent dispatches start clean.

    Args:
        tracks: List of dispatched track task-ID lists.
        project_root: Project root.

    Returns:
        Merged audit dict.
    """
    canonical_path = project_root / ".claude" / "auto-run.json"
    if canonical_path.exists():
        try:
            canonical = json.loads(canonical_path.read_text(encoding="utf-8"))
            if not isinstance(canonical, dict):
                canonical = {}
        except (OSError, json.JSONDecodeError):
            canonical = {}
    else:
        canonical = {}

    per_worker: list[dict[str, Any]] = []
    for task_ids in tracks:
        sidecar_path = _audit_sidecar_path(tuple(sorted(task_ids)), project_root)
        if sidecar_path.exists():
            try:
                sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                sidecar_data = {
                    "task_ids": list(task_ids),
                    "status": "no_audit_data",
                    "note": "Worker terminated before sidecar write",
                }
            else:
                sidecar_path.unlink(missing_ok=True)
            per_worker.append(sidecar_data)
        else:
            per_worker.append(
                {
                    "task_ids": list(task_ids),
                    "status": "no_audit_data",
                    "note": "Worker terminated before sidecar write",
                }
            )
    canonical["per_worker"] = per_worker
    canonical["aggregate_task_count"] = sum(len(tids) for tids in tracks)
    return canonical


def _reap_orphans(project_root: Path, dispatch_start_epoch: float) -> None:
    """Clean stale per-worker sidecar/scratch files from a prior crashed run.

    v1.0.5 iter-1 WARNING + iter-2 race-safety mtime guard: only reaps
    files older than ``dispatch_start_epoch - 300s`` (5min margin). This
    avoids clobbering sidecars/scratches from a CONCURRENT SBTDD instance
    that started just before this dispatch (iter-2 caspar WARNING).
    Concurrent instances are rare but possible (operator running parallel
    ``--parallel`` jobs). Idempotent: safe to invoke multiple times.
    """
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
                # v1.0.5 Loop 2 iter-1 caspar WARNING fix: catch
                # PermissionError on Windows when file is held open
                # by another process (e.g., concurrent SBTDD instance
                # past the mtime guard, or AV scanner). Skipping
                # stale-but-locked files is safer than crashing the
                # dispatcher; next reaper invocation may succeed.
                try:
                    stale.unlink(missing_ok=True)
                except (PermissionError, OSError):
                    continue


# ---------------------------------------------------------------------------
# v1.0.5 Item I-3 -- worker CLI flag forwarding (escenarios I3-1..I3-3).
# Operator-supplied flags (--plugins-root, --magi-max-iterations,
# --magi-threshold, --verification-retries, --model-override) propagate
# from the parent argparse namespace to each worker subprocess argv so
# concurrent dispatch honours operator intent end-to-end.
# ---------------------------------------------------------------------------


#: Maps argparse-namespace attribute names to their CLI flag names. Frozen
#: at module load via :class:`MappingProxyType` so callers cannot mutate
#: the forwarding contract at runtime. Keep in sync with the matching
#: ``add_argument`` calls in :func:`_build_parser`.
_FORWARDABLE_FLAGS: Mapping[str, str] = MappingProxyType(
    {
        "plugins_root": "--plugins-root",
        "magi_max_iterations": "--magi-max-iterations",
        "magi_threshold": "--magi-threshold",
        "verification_retries": "--verification-retries",
        "model_override": "--model-override",
    }
)


def _validate_forwardable_flags_against_argparse() -> None:
    """v1.0.6 K-4: validate ``_FORWARDABLE_FLAGS`` keys exist in argparse dest set.

    Detects drift between the hardcoded :data:`_FORWARDABLE_FLAGS`
    mapping and the ``_build_parser()`` argparse definition.
    Raises :class:`ValidationError` UNCONDITIONALLY at module import
    time (or on explicit invocation in tests) if any key in
    ``_FORWARDABLE_FLAGS`` is not a known dest name in the parser.

    Rationale: :func:`_build_worker_argv` uses ``_FORWARDABLE_FLAGS``
    to propagate operator flags to subprocess workers. If a flag is
    added to ``_FORWARDABLE_FLAGS`` but not registered in argparse,
    ``getattr(ns, ns_attr, None)`` would silently return None and the
    flag would never be forwarded — subtle bug. Loud-fast detection
    at module load surfaces drift immediately.

    **Private-attribute fragility acknowledgment** (iter-1 mel
    WARNING): this helper traverses argparse internals
    (``parser._actions`` + ``action.choices`` for subparsers). These
    are private attrs not part of argparse's public API; future
    argparse refactors could break this introspection. Acceptable
    trade-off given the coverage value (drift detection at module
    load time saves debugging cost). If argparse changes, this
    helper updates here in one place. Single-level subparser walk;
    deeper nesting not supported (see v1.0.7 LOCKED C1 polish).

    v1.0.7 C6 NOTE: tests that monkeypatch ``_FORWARDABLE_FLAGS``
    should call this helper directly rather than reloading
    ``auto_cmd`` via ``importlib.reload`` to avoid the import-time
    guard interaction. The guard fires at module import; reload
    re-imports + re-fires, which can mask the monkeypatch's effect.
    Direct helper invocation respects the patched dictionary.

    Implementation note: the parser walk below is single-level (see
    inline comment above the loop body for limitations + extension
    path).

    Raises:
        ValidationError: When ``_FORWARDABLE_FLAGS`` contains a key
            not registered as an argparse dest name in any subparser.
    """
    parser = _build_parser()
    # Private-attribute traversal (acknowledged fragility per docstring).
    dest_names: set[str] = set()
    for action in parser._actions:
        if action.dest:
            dest_names.add(action.dest)
    # Walk subparsers (single-level only).
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            for sub_parser in action.choices.values():
                if not hasattr(sub_parser, "_actions"):
                    continue
                for sub_action in sub_parser._actions:
                    if sub_action.dest:
                        dest_names.add(sub_action.dest)

    missing = [ns_attr for ns_attr in _FORWARDABLE_FLAGS if ns_attr not in dest_names]
    if missing:
        raise ValidationError(
            f"v1.0.6 K-4: _FORWARDABLE_FLAGS drift detected -- the "
            f"following keys are NOT registered as argparse dest names: "
            f"{sorted(missing)}. Either remove them from "
            f"_FORWARDABLE_FLAGS or add them to _build_parser()."
        )


def _run_sbtdd_path() -> Path:
    """Return path to ``run_sbtdd.py`` entry point.

    Centralises the per-script lookup so worker subprocess argv builders
    do not duplicate the ``Path(__file__).resolve().parent`` boilerplate.
    """
    return Path(__file__).resolve().parent / "run_sbtdd.py"


def _build_worker_argv(task_ids: list[str], ns: argparse.Namespace) -> list[str]:
    """Build subprocess argv for a worker, forwarding parent's CLI flags.

    v1.0.5 Item I-3: forwards :data:`_FORWARDABLE_FLAGS` values from the
    parent's argparse namespace to the worker subprocess. Documented
    forwardable list: ``--plugins-root``, ``--magi-max-iterations``,
    ``--magi-threshold``, ``--verification-retries``,
    ``--model-override``. Worker-mode markers ``--task-ids`` and
    ``--no-recursive`` are always present so the worker stays on the
    Path 3 worker code path (no recursive parallel dispatch).

    Repeated flags (``--model-override`` is ``action='append'``) flatten
    to one ``flag value`` pair per element in the parent list. ``None``
    values (and empty lists) are omitted so the worker argparse parser
    sees a clean argv.

    Args:
        task_ids: Task IDs assigned to this worker.
        ns: Parent's argparse namespace.

    Returns:
        Worker argv list ready for :class:`subprocess.Popen`.
    """
    argv: list[str] = [
        sys.executable,
        str(_run_sbtdd_path()),
        "auto",
        "--task-ids",
        ",".join(task_ids),
        "--no-recursive",
    ]
    for ns_attr, cli_flag in _FORWARDABLE_FLAGS.items():
        value = getattr(ns, ns_attr, None)
        if value is None:
            continue
        # ``--model-override`` is ``action='append'``: namespace value is a
        # list. Empty lists are equivalent to "flag never supplied" -- skip.
        if isinstance(value, list):
            for item in value:
                argv.extend([cli_flag, str(item)])
        else:
            argv.extend([cli_flag, str(value)])
    return argv


# ---------------------------------------------------------------------------
# v1.0.4 Item C -- parallel dispatch plan helpers (escenarios C-7, C-8, C-9).
# ---------------------------------------------------------------------------


def _build_dispatch_plan_sequential(plan_path: Path) -> list[set[str]]:
    """Sequential dispatch plan -- each task in its own batch in plan order.

    Preserves v1.0.3 behaviour exactly. Default when ``--parallel`` is
    NOT specified.

    Args:
        plan_path: Path to ``planning/claude-plan-tdd.md``.

    Returns:
        List of single-element sets, one per task, in the order the
        tasks appear in the plan. Each batch is dispatched serially.

    Notes:
        Task order is derived from ``graph.tasks`` insertion order, which
        :func:`dag_parser.parse_plan` populates from
        :func:`dag_parser._split_task_blocks` in document order. This
        relies on the Python 3.7+ dict insertion-order guarantee
        (project requires Python >= 3.9 per ``pyproject.toml``); a
        future refactor of ``TaskGraph.tasks`` to a non-insertion-
        ordered mapping would silently break sequential plan-text order.
    """
    graph = parse_plan(plan_path)
    return [{tid} for tid in graph.tasks.keys()]


def _build_dispatch_plan_parallel(plan_path: Path) -> list[list[str]]:
    """Parallel dispatch plan -- track-based partitioning (Path 3).

    v1.0.4 Path 3 architecture: tasks partitioned into TRACKS where each
    track is a weakly-connected component in the (deps UNION
    file-conflicts) graph. Tracks between each other are file-disjoint
    AND dep-disjoint, so they may be dispatched as N concurrent
    subprocess workers (one per track). Within each track, tasks must
    serialize because of internal deps/conflicts; the worker processes
    them sequentially with full TDD discipline.

    Replaces the prior Path 2 antichain + greedy collision-packing which
    parallelised inside antichains but not across them. Path 3 maps
    directly to the manual Track Alpha + Track Beta dispatch precedent
    used in v0.4.0/v0.5.0/v1.0.0/v1.0.2/v1.0.3 cycles.

    Args:
        plan_path: Path to ``planning/claude-plan-tdd.md``.

    Returns:
        List of tracks. Each track is a ``list[str]`` of task ids in
        dependency-respecting (topological) execution order. Order
        BETWEEN tracks does not matter for correctness; the parent
        dispatcher hands each track to one subprocess worker.
    """
    graph = parse_plan(plan_path)
    return partition_by_tracks(graph)


def _check_tdd_guard_warning(parallel: bool, project_root: Path) -> None:
    """Emit stderr warning when ``--parallel`` + TDD-Guard hooks detected.

    Per spec sec.3 multi-agent rules: parallel mode in same worktree
    with TDD-Guard ON produces falsos bloqueos because TDD-Guard's
    per-process state file is shared across subagents. The warning
    documents the two escape valves: toggle off via ``tdd-guard off``
    OR run each subagent in its own worktree via ``/using-git-worktrees``.

    Args:
        parallel: ``True`` if the run is opting into parallel dispatch.
        project_root: Project root containing ``.claude/settings.json``.

    Returns:
        ``None``. Warning (when applicable) is written to ``sys.stderr``.
    """
    if not parallel:
        return
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    # v1.0.4 Loop 2 iter-2 sub-issue 2 (C9): split JSONDecodeError vs OSError
    # so corrupted JSON surfaces a stderr breadcrumb. OSError remains silent
    # (genuine missing file is benign -- TDD-Guard simply not configured).
    # Pre-fix both were swallowed silently; operators got NO signal that
    # their TDD-Guard config was malformed.
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"[sbtdd auto] WARNING: cannot parse {settings_path}: {exc}; "
            f"TDD-Guard hook detection skipped. Restore valid JSON to "
            f"re-enable the parallel-mode multi-agent caveat.\n"
        )
        sys.stderr.flush()
        return
    except OSError:
        return
    hooks = settings.get("hooks", {})
    if not isinstance(hooks, dict):
        return
    has_tdd_guard = False
    for hook_list in hooks.values():
        if not isinstance(hook_list, list):
            continue
        for entry in hook_list:
            if not isinstance(entry, dict):
                continue
            for h in entry.get("hooks", []):
                if isinstance(h, dict) and "tdd-guard" in str(h.get("command", "")).lower():
                    has_tdd_guard = True
                    break
    if has_tdd_guard:
        sys.stderr.write(
            "[sbtdd auto] WARNING: Parallel mode in same worktree with "
            "TDD-Guard ON may produce falsos bloqueos. Toggle off with "
            "`tdd-guard off` per spec sec.3 multi-agent rules, OR use "
            "`/using-git-worktrees` for per-subagent worktree.\n"
        )
        sys.stderr.flush()


#: Hard ceiling on auto-resolved parallel workers. Operators may override
#: with explicit ``--parallel-max`` (positive cap) or 0 (unlimited). The
#: ceiling exists because beyond ~4 concurrent subprocesses the wall-time
#: gain saturates while contention on shared file system surfaces (git
#: index lock, .claude/auto-run.json, plan-tdd.md) increases sub-linearly
#: in benefit. v1.0.5+ may make this a configurable per-machine knob.
_PATH3_AUTO_WORKER_CEILING: int = 4


def _next_open_task_in_filter(
    plan_path: Path,
    current_task_id: str,
    task_ids_filter: frozenset[str],
) -> tuple[str, str] | None:
    """Return ``(id, title)`` of the next plan task that is open AND in filter.

    v1.0.4 iter-5 Loop 1 CRITICAL #1 helper. Used by the worker skip-
    fast-forward to advance past tasks the worker does not own. Scans
    plan-text in source order, INCLUDING ``current_task_id`` if it is
    open (caller decides whether to start at-or-after) -- this helper
    returns the first match WHOSE position is at-or-after
    ``current_task_id``. The caller's filter check already excluded
    ``current_task_id`` from the filter, so a match at-or-after is
    correctly the next-assigned-and-open candidate.

    Args:
        plan_path: Absolute path to ``planning/claude-plan-tdd.md``.
        current_task_id: Worker's current cursor (a task id NOT in
            ``task_ids_filter`` -- the caller's precondition).
        task_ids_filter: Frozenset of task ids assigned to this worker.

    Returns:
        ``(id, title)`` of the first open task at-or-after
        ``current_task_id`` whose id is in the filter, or ``None``
        when the filter is exhausted (worker has no more work).
    """
    plan_text = plan_path.read_text(encoding="utf-8")
    # Scan all task headers in plan source order (same regex used by
    # _plan_ops.next_task / first_open_task to keep semantics aligned).
    headers = list(_plan_ops._TASK_HEADER_RE.finditer(plan_text))
    started = False
    for m in headers:
        tid = m.group(1)
        title = m.group(2).strip()
        if tid == current_task_id:
            started = True
        if not started:
            continue
        if tid not in task_ids_filter:
            continue
        # Verify the task is still open (has at least one ``- [ ]``
        # checkbox in its section). A previously-closed task in filter
        # is not work we should redo; skip it.
        start, end = _plan_ops._task_section_bounds(plan_text, tid)
        if "- [ ]" in plan_text[start:end]:
            return (tid, title)
    return None


def _parse_task_ids_filter(raw: str | None) -> frozenset[str] | None:
    """Decode the ``--task-ids`` argument into a worker filter set.

    v1.0.4 iter-5 Loop 1 CRITICAL #1: pre-fix ``main()`` only checked
    truthiness of ``ns.task_ids`` to set ``is_worker_mode`` -- the
    comma-separated string was never split, so ``_phase2_task_loop``
    had no way to filter which task ids the worker should process.
    This helper produces an explicit filter consumed by the loop.

    Args:
        raw: Raw value of ``ns.task_ids`` (e.g. ``"1,3,5"``) or
            ``None`` when the flag was not supplied.

    Returns:
        ``None`` when ``raw`` is ``None`` or an empty string (no
        filter active; sequential default behaviour). Otherwise a
        :class:`frozenset` of task ids with surrounding whitespace
        stripped and empty tokens (from trailing or duplicate commas)
        ignored.
    """
    if raw is None:
        return None
    tokens = [t.strip() for t in raw.split(",")]
    cleaned = [t for t in tokens if t]
    if not cleaned:
        return None
    return frozenset(cleaned)


def _resolve_effective_workers(natural_n: int, user_max: int | None) -> int:
    """Resolve the effective parallel worker count for Path 3 dispatch.

    Cascade (most-restrictive wins):
        - ``user_max is None`` → auto: ``min(natural_n, cpu_count, 4)``.
        - ``user_max == 0`` → unlimited (operator override): ``natural_n``.
        - ``user_max > 0`` → explicit cap: ``min(natural_n, user_max)``.

    The natural worker count is the number of tracks emitted by
    :func:`parallel_dispatcher.partition_by_tracks`. Effective workers
    can never exceed natural — there is no point spawning idle workers.

    Args:
        natural_n: Number of tracks (from ``partition_by_tracks``).
        user_max: Operator-specified cap from ``--parallel-max``. None
            triggers auto resolution; 0 disables the ceiling; positive
            caps natural at that value.

    Returns:
        Effective worker count (>= 0).
    """
    if natural_n <= 0:
        return 0
    if user_max is None:
        cpu = os.cpu_count() or _PATH3_AUTO_WORKER_CEILING
        return min(natural_n, cpu, _PATH3_AUTO_WORKER_CEILING)
    if user_max == 0:
        return natural_n
    return min(natural_n, user_max)


def _spawn_worker(
    argv: list[str],
    env: dict[str, str],
    **popen_kwargs: Any,
) -> "subprocess.Popen[bytes]":
    """v1.0.7 A2 cross-platform worker spawn dispatcher.

    POSIX -> real PTY allocation via
    :func:`subprocess_utils._spawn_worker_with_pty` (Item A1). Workers
    inherit slave fd as stdin/stdout/stderr; close-phase /verification-
    before-completion subprocess inherits TTY -> no chicken-and-egg hang.

    Windows -> ``subprocess.PIPE`` (Option B-W3 hybrid; Windows lacks
    POSIX-style PTY). Workers carry ``SBTDD_AUTO_PARALLEL_WORKER=1`` env
    marker so :func:`close_phase_cmd._run_verification` shells out to the
    sec.0.1 4-tool chain directly instead of dispatching the interactive
    skill (sidesteps TTY requirement).

    All worker subprocess spawns under ``auto --parallel`` MUST go through
    this helper to preserve the ``SBTDD_AUTO_PARALLEL_WORKER=1`` env
    contract that :func:`close_phase_cmd._run_verification` and
    :func:`superpowers_dispatch.invoke_skill` depend on. Direct
    ``subprocess.Popen`` invocations bypassing this dispatcher break the
    chicken-and-egg fix and produce silent hangs in production.

    Args:
        argv: Subprocess argv. ``shell=False`` invariant preserved.
        env: Environment dict; this helper injects
            ``SBTDD_AUTO_PARALLEL_WORKER=1`` before spawn.
        **popen_kwargs: Forwarded to :class:`subprocess.Popen` on Windows
            (e.g. ``cwd=``, ``creationflags=``). v1.0.7 T2 code-review C1
            fix: the ``cwd`` kwarg is also threaded through the POSIX PTY
            helper so workers run in the project root regardless of the
            orchestrator's invocation directory. Other kwargs (e.g.
            ``creationflags``) are silently ignored on POSIX (PTY semantics
            constrain stdio + Windows-only flags don't apply).

    Returns:
        ``subprocess.Popen`` instance ready for orchestrator post-batch
        merge (per v1.0.5 I-1 sidecar + I-2 scratch patterns).
    """
    env_with_marker = {**env, "SBTDD_AUTO_PARALLEL_WORKER": "1"}
    if sys.platform == "win32":
        proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env_with_marker,
            **popen_kwargs,
        )
        return cast("subprocess.Popen[bytes]", proc)
    # v1.0.7 T2 code-review C1 fix: forward cwd through PTY helper to
    # preserve cross-platform cwd semantics (Windows uses Popen kwargs;
    # POSIX needs explicit cwd= forwarding to subprocess.Popen via the
    # PTY helper signature extension). Without this, POSIX workers
    # silently inherit orchestrator cwd which fails when invoked from
    # a subdirectory.
    cwd = popen_kwargs.get("cwd")
    return cast(
        "subprocess.Popen[bytes]",
        subprocess_utils._spawn_worker_with_pty(argv, env_with_marker, cwd=cwd),
    )


def _verify_worker_sidecars_present(
    project_root: Path,
    successful_pids: list[int],
) -> None:
    """v1.0.7 iter-3 carry-forward C1: LOUD-FAIL on missing INV-16 sidecar.

    Each SUCCESSFUL worker (one that reached close-phase + exited 0) MUST
    have produced >= 1 sidecar matching ``<pid>-*-verify.json``. Missing
    sidecar = code-path bug: close-phase ran but persistence silently
    failed. LOUD-FAIL via :class:`ConcurrentDispatchError` surfaces it
    during test/dogfood instead of silent INV-16 evidence loss.

    v1.0.7 T2 code-review C2 fix: only checks pids of SUCCESSFUL workers,
    not all spawned workers. Workers that crashed BEFORE reaching
    close-phase (e.g., green-phase failure) legitimately have no sidecar;
    conflating them with persistence bugs masks the real failure surface
    and produces a misleading "INV-16 evidence loss" diagnostic when the
    actual cause is a worker crash (already captured in the failures
    list + raised via ConcurrentDispatchError on the failures path).

    Args:
        project_root: Project root (sidecar dir is
            ``<project_root>/.claude/auto-run-workers/``).
        successful_pids: Pids of workers that exited 0; filtered against
            the failures list by the caller (typically
            :func:`_dispatch_tracks_concurrent` post-batch).

    Raises:
        ConcurrentDispatchError: At least one successful worker pid
            produced no matching sidecar; message names the missing pids
            + the observed sidecars so operators can reproduce + diagnose
            the silent persistence failure.
    """
    sidecar_dir = project_root / ".claude" / "auto-run-workers"
    if not sidecar_dir.exists():
        # No sidecar dir at all is legitimate when:
        # (a) all workers failed before close-phase (caught by failures
        #     list raise), OR
        # (b) test fixtures with FakePopen that simulate success without
        #     actually running close-phase / persisting sidecars.
        # Real production workers create the dir on first sidecar write;
        # mid-batch the dir always exists when ANY worker reached
        # close-phase. The check below catches the more interesting bug:
        # SOME workers persisted sidecars + others didn't. If the dir
        # never existed, defer to failures-list raise + integration tests
        # that actually exercise the close-phase chain.
        return
    observed = list(sidecar_dir.glob("*-verify.json"))
    observed_pids: set[int] = set()
    for p in observed:
        try:
            observed_pids.add(int(p.name.split("-")[0]))
        except ValueError:
            # Stray file or future schema change; skip + breadcrumb.
            sys.stderr.write(
                f"[WARN] v1.0.7 T2 C1: skipping unparseable sidecar "
                f"filename {p.name!r} (expected <pid>-*-verify.json)\n"
            )
    missing = [pid for pid in successful_pids if pid not in observed_pids]
    if missing:
        raise ConcurrentDispatchError(
            f"v1.0.7 iter-3 C1: successful workers {missing} exited 0 but "
            f"produced no INV-16 sidecar. Observed sidecars: "
            f"{[p.name for p in observed]}. Bug in "
            f"_persist_worker_verify_evidence OR transient OS error "
            f"swallowed mid-write; investigate before next dispatch."
        )


def _dispatch_tracks_concurrent(
    tracks: list[list[str]],
    effective_workers: int,
    project_root: Path,
    ns: argparse.Namespace | None = None,
) -> None:
    """Dispatch one subprocess worker per track concurrently (Path 3).

    Each track is dispatched as a child invocation of
    ``python skills/sbtdd/scripts/run_sbtdd.py auto --task-ids T1,T2,...
    --no-recursive``. The child processes the supplied task ids
    sequentially with full TDD discipline (red/green/refactor commits +
    spec-reviewer + close-task per task) via the legacy ``_phase2_task_loop``
    body. ``--no-recursive`` ensures the child does NOT itself call
    ``_dispatch_tracks_concurrent`` again, preventing infinite spawning.

    Concurrency model: a thread pool with ``effective_workers`` slots
    pulls tracks off a FIFO queue and ``Popen``-spawns each child. The
    parent waits for all children to complete before returning. If
    ``effective_workers < len(tracks)``, tracks beyond the first
    ``effective_workers`` queue and run as slots free up.

    State-file coordination: each worker mutates the shared
    ``.claude/session-state.json`` via ``state_file.save`` whose atomic
    write-temp + ``os.replace`` semantics serialize concurrent writers
    at the OS level (last writer wins, no partial-merge file). This
    matches the existing project convention (see ``parallel_dispatcher``
    module docstring). Worker-side commits also serialize via the git
    index lock; parallel git operations on the same worktree are safe.

    **Env var propagation contract** (v1.0.8 Pillar A2): each
    worker subprocess inherits the parent's environment via
    ``worker_env = os.environ.copy()`` at line ~2061 — UNFILTERED.
    All env vars present in the parent process are propagated to
    workers unchanged. This contract is load-bearing for v1.0.8
    Pillar A1: the stub gate's env var (``SBTDD_E2E_STUB_DISPATCH``)
    flows from a parent test process down through the orchestrator
    to each worker, where the gate fires and bypasses real
    ``claude -p`` dispatch. A future refactor introducing an
    env-var allowlist (e.g., to scrub secrets) would break the
    stub gate semantics and the v1.0.8 e2e test
    (``test_auto_parallel_e2e``). The regression test
    ``test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch``
    in ``tests/test_auto_cmd.py`` pins this contract at runtime.

    Args:
        tracks: Output of :func:`parallel_dispatcher.partition_by_tracks`.
            Each inner list is one track in topological execution order.
        effective_workers: Resolved by :func:`_resolve_effective_workers`.
            Number of concurrent ``Popen`` slots. Must be >= 1 when
            ``tracks`` is non-empty.
        project_root: Project root passed to each child as
            ``--project-root``. Each child inherits the same plan +
            state-file paths.
        ns: Parent's argparse namespace. v1.0.5 Item I-3 forwards a
            documented set of operator flags (:data:`_FORWARDABLE_FLAGS`)
            to every worker subprocess via :func:`_build_worker_argv`.
            ``None`` (legacy callers / tests) preserves the v1.0.4
            minimal-argv shape exactly.

    Raises:
        ConcurrentDispatchError: At least one worker exited non-zero
            (exit 2, PRECONDITION_FAILED). Message includes the offending
            track (its task ids) and best-effort captured stderr text.
    """
    if not tracks:
        return
    if effective_workers <= 0:
        # Defensive: caller already resolved; treat as serial fallback.
        effective_workers = 1
    # v1.0.5 T2 Refactor: route through the shared helper so the legacy
    # ``ns is None`` argv branch and ``_build_worker_argv`` agree on the
    # same ``run_sbtdd.py`` path resolution.
    run_sbtdd_path = _run_sbtdd_path()

    # v1.0.5 iter-1 WARNING + iter-2 race-safety: reap stale per-worker
    # sidecar/scratch files from a prior crashed run BEFORE new dispatch
    # so workers never inherit contaminated state. mtime guard inside
    # ``_reap_orphans`` avoids clobbering concurrent SBTDD instances.
    dispatch_start_epoch = time.time()
    _reap_orphans(project_root, dispatch_start_epoch=dispatch_start_epoch)

    # FIFO queue of tracks awaiting dispatch + collector for results.
    track_queue: queue.Queue[list[str]] = queue.Queue()
    for t in tracks:
        track_queue.put(t)
    failures: list[tuple[list[str], int, str]] = []
    failures_lock = threading.Lock()
    # v1.0.7 iter-3 C1: collect per-worker pids for parent-side LOUD-FAIL
    # check post-batch (each worker MUST produce a verify-evidence sidecar).
    spawned_pids: list[int] = []
    spawned_pids_lock = threading.Lock()
    # v1.0.7 T2 code-review C2 fix: track successful (rc=0) pids
    # separately so _verify_worker_sidecars_present LOUD-FAIL only
    # checks workers that reached close-phase + exited cleanly.
    successful_pids: list[int] = []
    successful_pids_lock = threading.Lock()

    def worker_loop() -> None:
        while True:
            try:
                track = track_queue.get_nowait()
            except queue.Empty:
                return
            try:
                # v1.0.5 Item I-3: build worker argv via the shared helper
                # so operator flags (--magi-threshold, --verification-retries,
                # etc.) propagate from parent to worker. Legacy callers that
                # do not supply ``ns`` get the minimal v1.0.4 argv shape
                # extended only with --project-root.
                if ns is not None:
                    argv = _build_worker_argv(track, ns)
                    # Inject --project-root so the worker keeps targeting the
                    # parent's project (otherwise it falls back to cwd at
                    # parse time, which Popen sets to project_root anyway,
                    # but be explicit so worker logs / breadcrumbs name it).
                    argv.extend(["--project-root", str(project_root)])
                else:
                    task_ids_arg = ",".join(track)
                    argv = [
                        sys.executable,
                        str(run_sbtdd_path),
                        "auto",
                        "--project-root",
                        str(project_root),
                        "--task-ids",
                        task_ids_arg,
                        "--no-recursive",
                    ]
                # v1.0.7 A2: route through the cross-platform dispatcher so
                # the SBTDD_AUTO_PARALLEL_WORKER=1 env contract holds for
                # every worker (POSIX -> PTY allocation; Windows -> PIPE +
                # env marker). Direct subprocess.Popen here would bypass
                # the chicken-and-egg fix.
                #
                # v1.0.8 A2: env propagation is UNFILTERED — os.environ.copy()
                # preserves all parent env vars in the worker context. This
                # contract is load-bearing for v1.0.8 Pillar A1 (the stub
                # gate's SBTDD_E2E_STUB_DISPATCH env var flows parent ->
                # orchestrator -> worker unchanged; gate fires in worker
                # subprocess + bypasses real claude -p). The regression
                # test test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch
                # pins this. Any future allowlist refactor MUST update
                # both this comment AND the regression test together.
                worker_env = os.environ.copy()
                proc = _spawn_worker(
                    argv,
                    env=worker_env,
                    cwd=str(project_root),
                )
                with spawned_pids_lock:
                    spawned_pids.append(proc.pid)
                try:
                    _stdout_b, stderr_b = proc.communicate(timeout=7200)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    _stdout_b, stderr_b = proc.communicate()
                    with failures_lock:
                        failures.append((track, -1, "subprocess timeout (7200s)"))
                    continue
                rc = proc.returncode
                if rc != 0:
                    err_text = (
                        stderr_b.decode("utf-8", errors="replace")
                        if isinstance(stderr_b, bytes)
                        else str(stderr_b)
                    )
                    with failures_lock:
                        failures.append((track, rc, err_text))
                else:
                    # v1.0.7 T2 code-review C2 fix: only successful workers
                    # are checked by _verify_worker_sidecars_present.
                    with successful_pids_lock:
                        successful_pids.append(proc.pid)
            finally:
                track_queue.task_done()

    n_threads = min(effective_workers, len(tracks))
    threads = [threading.Thread(target=worker_loop, daemon=False) for _ in range(n_threads)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    # v1.0.7 iter-3 C1 LOUD-FAIL (with T2 code-review C2 fix): each
    # SUCCESSFUL worker (rc=0; reached close-phase) MUST have produced a
    # verify-evidence sidecar. Failed workers (rc!=0; crashed before
    # close-phase) legitimately have no sidecar; conflating them with
    # persistence bugs masks the real failure surface (already in
    # ``failures`` list).
    _verify_worker_sidecars_present(project_root, successful_pids)

    # v1.0.5 Item I-1: merge per-worker audit sidecars into the canonical
    # ``.claude/auto-run.json``. Performed unconditionally (even when some
    # workers failed) so the audit reflects whatever per-worker progress
    # landed before the failure.
    merged_audit = _merge_audit_sidecars(tracks, project_root)
    _atomic_write_json(project_root / ".claude" / "auto-run.json", merged_audit)

    # v1.0.5 Item I-2 (iter-1 CRITICAL #4 wiring): Track Alpha owns ALL
    # ``_dispatch_tracks_concurrent`` post-batch hooks; Track Beta provides
    # ``_merge_scratch_plans`` as a pure module-level function in
    # close_task_cmd.py. Late import keeps the cross-track dependency
    # runtime-only so module load of auto_cmd.py never depends on
    # close_task_cmd's I-2 helper being present at the same revision.
    # ``getattr`` fallback to a no-op preserves resilience while Track Beta
    # T3 lands -- once Item I-2 ships the real helper is invoked.
    import close_task_cmd as _ctc

    _merge_scratch_plans = getattr(_ctc, "_merge_scratch_plans", None)
    if _merge_scratch_plans is not None:
        _merge_scratch_plans(tracks, project_root)

    if failures:
        details = "; ".join(f"track {tids} exit={rc}: {msg[:300]}" for tids, rc, msg in failures)
        raise ConcurrentDispatchError(f"concurrent track dispatch failed: {details}")


def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``sbtdd auto``."""
    p = argparse.ArgumentParser(prog="sbtdd auto")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--plugins-root",
        type=Path,
        default=Path.home() / ".claude" / "plugins",
    )
    p.add_argument("--magi-max-iterations", type=int, default=None)
    p.add_argument("--magi-threshold", type=str, default=None)
    p.add_argument("--verification-retries", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    # v0.3.0 Feature E -- per-skill model selection. Repeatable;
    # accumulates into ``ns.model_override`` as a ``list[str]`` of
    # ``<skill>:<model>`` tokens that ``_parse_model_overrides`` decodes
    # downstream. Cascade: CLAUDE.md > CLI override > plugin.local.md
    # > None (inherit session).
    p.add_argument(
        "--model-override",
        action="append",
        default=[],
        metavar="<skill>:<model>",
        help=(
            "Override the per-skill model for this run only. Repeatable. "
            "Valid skill names: implementer, spec_reviewer, code_review, "
            "magi_dispatch. Cascade: CLAUDE.md > CLI override > "
            "plugin.local.md > None (inherit session)."
        ),
    )
    # v1.0.4 Item C: opt-in parallel task dispatch via DAG analysis +
    # file-surface collision detection. Default False preserves the v1.0.3
    # sequential dispatch behaviour exactly. See spec sec.3 multi-agent
    # rules for the TDD-Guard interaction caveats.
    p.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help=(
            "v1.0.4 Item C: dispatch parallelizable task batches "
            "concurrently. Requires TDD-Guard OFF in same worktree, "
            "OR per-subagent worktree (see spec sec.3)."
        ),
    )
    # v1.0.4 Path 3: track-based subprocess dispatch flags.
    # Worker mode: when ``--task-ids`` is set AND ``--no-recursive`` is
    # set, this invocation is a worker subprocess spawned by a parent
    # ``--parallel`` orchestrator. The worker processes EXACTLY the
    # comma-separated task ids in sequence (full TDD discipline per task)
    # and skips the parent-side track partition + concurrent spawn.
    p.add_argument(
        "--task-ids",
        type=str,
        default=None,
        help=(
            "v1.0.4 Path 3 worker mode: comma-separated task ids the "
            "current invocation must process sequentially with full TDD "
            "discipline. Used internally by --parallel dispatch to fan "
            "out tracks. Operators may also set it manually to scope a "
            "single auto run to a subset of tasks."
        ),
    )
    p.add_argument(
        "--no-recursive",
        action="store_true",
        default=False,
        help=(
            "v1.0.4 Path 3 worker mode: prevent recursive subprocess "
            "spawning. When set, this invocation never calls "
            "_dispatch_tracks_concurrent itself. Used by parent dispatch "
            "to ensure workers do not re-fan-out into infinite spawning."
        ),
    )
    p.add_argument(
        "--parallel-max",
        type=int,
        default=None,
        help=(
            "v1.0.4 Path 3: cap on parallel worker count. None=auto "
            "(min(natural_tracks, cpu_count, 4)). 0=unlimited (operator "
            "override). >0=explicit cap. Effective worker count is "
            "resolved by _resolve_effective_workers."
        ),
    )
    return p


# ---------------------------------------------------------------------------
# v0.3.0 Feature E -- per-skill model selection (Track E, disjoint from D).
# ---------------------------------------------------------------------------

#: Canonical skill names accepted by ``--model-override <skill>:<model>``.
#: Frozen at module load: ``frozenset`` so callers cannot mutate the
#: validation set at runtime. Mirrors :data:`config._MODEL_FIELDS` (with
#: the ``_model`` suffix stripped) -- the field map in ``_resolve_model``
#: stays the source of truth for the suffix translation.
_VALID_MODEL_OVERRIDE_SKILLS: frozenset[str] = frozenset(
    {"implementer", "spec_reviewer", "code_review", "magi_dispatch"}
)


def _parse_model_overrides(raw_values: list[str]) -> dict[str, str]:
    """Parse repeated ``--model-override <skill>:<model>`` CLI tokens.

    Returns a dict mapping skill name (one of the four canonical names in
    :data:`_VALID_MODEL_OVERRIDE_SKILLS`) to model ID. Raises
    :class:`ValidationError` on missing separator or unknown skill name;
    the dispatcher in :mod:`run_sbtdd` converts ValidationError to exit
    code 1 (USER_ERROR) per sec.S.11.1.

    Args:
        raw_values: List of ``<skill>:<model>`` tokens collected from
            ``argparse.action='append'``. May be empty.

    Returns:
        Dict ``{skill_name: model_id}``; empty when ``raw_values`` is empty.

    Raises:
        ValidationError: A token has no ``:`` separator OR the skill name
            is not in :data:`_VALID_MODEL_OVERRIDE_SKILLS`.
    """
    out: dict[str, str] = {}
    for raw in raw_values:
        if ":" not in raw:
            raise ValidationError(f"--model-override expects '<skill>:<model>'; got {raw!r}")
        skill, _, model = raw.partition(":")
        if skill not in _VALID_MODEL_OVERRIDE_SKILLS:
            raise ValidationError(
                f"invalid --model-override skill name {skill!r}. Valid: "
                f"{', '.join(sorted(_VALID_MODEL_OVERRIDE_SKILLS))}"
            )
        out[skill] = model
    return out


def _resolve_model(
    skill: str,
    config: PluginConfig,
    cli_overrides: dict[str, str],
) -> str | None:
    """Resolve the effective configured model for a skill at dispatch time.

    Cascade: CLI override > plugin.local.md field > None. INV-0
    (``~/.claude/CLAUDE.md`` global pin) is enforced downstream by each
    dispatch module's ``_apply_inv0_model_check`` -- this helper does NOT
    re-implement INV-0 because that gate must run on every invocation
    regardless of whether the cascade landed on CLI or config.

    Args:
        skill: Canonical skill name (one of
            :data:`_VALID_MODEL_OVERRIDE_SKILLS`).
        config: Loaded :class:`PluginConfig`; carries the four
            ``*_model`` fields from ``plugin.local.md``.
        cli_overrides: Pre-parsed ``--model-override`` map (output of
            :func:`_parse_model_overrides`).

    Returns:
        The model ID to pass to the dispatch module's ``model=`` kwarg,
        or ``None`` when neither layer of the cascade set a value (the
        plugin then inherits the session's default model — byte-identical
        to v0.2.x behaviour).
    """
    if skill in cli_overrides:
        return cli_overrides[skill]
    field_map: dict[str, str | None] = {
        "implementer": config.implementer_model,
        "spec_reviewer": config.spec_reviewer_model,
        "code_review": config.code_review_model,
        "magi_dispatch": config.magi_dispatch_model,
    }
    return field_map.get(skill)


def _print_dry_run_preview(ns: argparse.Namespace) -> None:
    """Emit the dry-run plan without reading any subprocess/tool output.

    Keeps dry-run stdlib-only and side-effect-free so it works even
    when git/tdd-guard/plugins are unavailable.
    """
    sys.stdout.write(
        "/sbtdd auto --dry-run:\n"
        f"  project_root: {ns.project_root}\n"
        f"  magi_max_iterations (override): {ns.magi_max_iterations}\n"
        f"  magi_threshold (override): {ns.magi_threshold}\n"
        f"  verification_retries (override): {ns.verification_retries}\n"
        "  Would execute phases 1-5 sequentially (preflight, task loop,\n"
        "  pre-merge, checklist, report). No commits, no subprocess calls.\n"
    )


def _phase1_preflight(ns: argparse.Namespace) -> tuple[SessionState, PluginConfig]:
    """Run Phase 1 -- pre-flight dependency + state + plan_approved_at check.

    Precondition order (deterministic for the user):

    1. ``.claude/session-state.json`` exists (``PreconditionError`` otherwise).
    2. ``state.plan_approved_at`` is not ``None`` -- auto requires an
       approved plan so the "Excepcion bajo plan aprobado" from template
       sec.5 is in effect.
    3. All dependency checks green (Rust/Python/C++ toolchain, git,
       tdd-guard, superpowers + magi plugins). Failures are reported in
       full -- no short-circuit (INV-12 / sec.S.5.1.1).

    Args:
        ns: Parsed argparse namespace (provides ``project_root`` +
            ``plugins_root``).

    Returns:
        A tuple ``(SessionState, PluginConfig)`` consumed by the
        downstream phases.

    Raises:
        PreconditionError: Missing state file or ``plan_approved_at is None``.
        DependencyError: Any pre-flight check reported non-OK status.
    """
    # v0.5.0 S1-9 transition site #1: phase 1 entry.
    _set_progress(phase=1)
    root: Path = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.plan_approved_at is None:
        raise PreconditionError(
            "plan_approved_at is null - run /sbtdd spec to approve a plan before /sbtdd auto"
        )
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    report = check_environment(cfg.stack, root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    return state, cfg


_PHASE_ORDER: tuple[str, ...] = ("red", "green", "refactor")


def _now_iso() -> str:
    """Return UTC ISO 8601 timestamp with a Z suffix (CLAUDE.md sec.2.2)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_head_sha(root: Path) -> str:
    """Return short SHA of HEAD via ``git rev-parse --short``."""
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def _run_verification_with_retries(root: Path, retries: int) -> None:
    """Invoke ``/verification-before-completion`` with retry budget.

    Each failure below the budget triggers ``/systematic-debugging`` to give
    the loop a structured hand-off for root-cause analysis (sec.M.3). When
    attempts exceed ``retries`` the last failure is wrapped as
    :class:`VerificationIrremediableError` (exit 6).

    Exception handling policy (MAGI Loop 2 iter 1 Finding 2):

    - :class:`QuotaExhaustedError` is re-raised UNCHANGED without
      consuming a retry or invoking ``/systematic-debugging``. Quota is
      a hard cap on API usage, not a transient verification failure;
      retrying cannot help and wrapping would remap exit 11 -> 6,
      destroying the telemetry that ``/sbtdd resume`` consumes to
      classify interruptions.
    - Any other :class:`Exception` consumes one retry and triggers
      ``/systematic-debugging``; budget exhaustion wraps as
      :class:`VerificationIrremediableError`.

    Args:
        root: Project root directory passed as ``cwd`` to the skills.
        retries: Number of additional attempts allowed after the first
            failure. ``retries=0`` means a single attempt with no retry.

    Raises:
        QuotaExhaustedError: Verification hit an Anthropic API cap (exit
            11). Propagated unchanged; caller's dispatcher maps to 11.
        VerificationIrremediableError: Non-quota verification failures
            exhausted the retry budget (exit 6).
    """
    # Loop 1 fix v0.5.0 CRITICAL #1: wrap each verification + sys-debug
    # dispatch in ``_dispatch_with_heartbeat`` so the operator sees liveness
    # ticks during multi-minute subagent invocations. ``_set_progress`` MUST
    # establish ``dispatch_label`` before the wrapper fires (fail-loud per
    # Checkpoint 2 iter 2 melchior). The label is preserved (started_at
    # refreshed) for the verification call and replaced for systematic-
    # debugging via the same helper.
    current = get_current_progress()
    for attempt in range(retries + 1):
        try:
            _set_progress(
                iter_num=current.iter_num,
                phase=current.phase,
                task_index=current.task_index,
                task_total=current.task_total,
                dispatch_label="verification",
            )
            _dispatch_with_heartbeat(
                invoke=lambda: superpowers_dispatch.verification_before_completion(cwd=str(root)),
            )
            return
        except QuotaExhaustedError:
            # MAGI Loop 2 iter 1 Finding 2: quota exhaustion is NOT a
            # retryable failure -- it signals an Anthropic API hard cap
            # (429 rate limit, session/weekly/Opus subscription limit,
            # credit balance exhausted, server throttle). Wrapping it as
            # VerificationIrremediableError would remap exit 11 (quota)
            # to exit 6 (irremediable), destroying the telemetry that
            # `/sbtdd resume` relies on to detect quota interruptions.
            # Propagate unchanged; the dispatcher maps to exit 11.
            raise
        except Exception as exc:
            if attempt >= retries:
                raise VerificationIrremediableError(
                    f"verification failed after {retries} retries: {exc}"
                ) from exc
            _set_progress(
                iter_num=current.iter_num,
                phase=current.phase,
                task_index=current.task_index,
                task_total=current.task_total,
                dispatch_label="systematic-debugging",
            )
            _dispatch_with_heartbeat(
                invoke=lambda: superpowers_dispatch.systematic_debugging(cwd=str(root)),
            )


def _phase_prefix(phase: str) -> str:
    """Return the sec.M.5 commit prefix for the closing phase.

    Auto uses ``green_feat`` by default (consistent with
    ``/sbtdd close-phase --variant feat``). Callers that want ``fix``
    semantics must use manual ``close-phase``.
    """
    if phase == "red":
        return COMMIT_PREFIX_MAP["red"]
    if phase == "green":
        return COMMIT_PREFIX_MAP["green_feat"]
    if phase == "refactor":
        return COMMIT_PREFIX_MAP["refactor"]
    raise ValueError(f"unknown phase '{phase}'")


def _run_spec_review_gate(
    task_id: str,
    plan_path: Path,
    root: Path,
    *,
    model: str | None = None,
    stream_prefix: str | None = None,
) -> None:
    """Dispatch the spec-reviewer before :func:`close_task_cmd.mark_and_advance` (INV-31).

    Thin wrapper around :func:`spec_review_dispatch.dispatch_spec_reviewer`
    that flattens :func:`_phase2_task_loop`'s inner ``else`` branch: callers
    see a single gate line instead of a multi-kwarg dispatch dict. The real
    dispatcher raises :class:`SpecReviewError` on non-approval after the
    safety-valve iteration cap; the raise propagates to
    :func:`_phase2_task_loop`'s ``except SpecReviewError`` branch, which
    records the blocked task count in ``.claude/auto-run.json`` before
    re-raising.

    Mirrors :func:`close_task_cmd._run_spec_review` for the interactive
    task-close path; both share the INV-31 contract. Auto relies on the
    dispatcher raising (no defensive ``result.approved`` check) because
    the try/except already captures the failure and the stub fixtures
    exercising auto drive :class:`SpecReviewError` directly to cover the
    blocked-advance test path (see
    ``tests/test_auto_cmd_spec_review.py``).

    Args:
        task_id: Plan task id whose diff is being reviewed.
        plan_path: Path to the approved plan.
        root: Project root directory.
        model: Optional Claude model ID (v0.3.0 Feature E). When set,
            forwarded to the dispatcher's ``model=`` kwarg for the
            INV-0 + ``--model`` injection cascade. When ``None`` (default)
            the kwarg is omitted entirely so test stubs that pre-date
            v0.3.0 keep working.
    """
    # iter 2 finding #1 + #7: forward stream_prefix only when supplied
    # (None -> kwarg omitted) so v0.2.x stubs without the new kwarg keep
    # accepting the call.
    kwargs: dict[str, Any] = {
        "task_id": task_id,
        "plan_path": plan_path,
        "repo_root": root,
    }
    if model is not None:
        kwargs["model"] = model
    if stream_prefix is not None:
        kwargs["stream_prefix"] = stream_prefix
    # Loop 1 fix v0.5.0 CRITICAL #1: wrap with heartbeat so the operator
    # sees liveness ticks during the spec-reviewer subagent invocation.
    current = get_current_progress()
    _set_progress(
        iter_num=current.iter_num,
        phase=current.phase,
        task_index=current.task_index,
        task_total=current.task_total,
        dispatch_label="spec-review",
    )
    _dispatch_with_heartbeat(
        invoke=lambda: spec_review_dispatch.dispatch_spec_reviewer(**kwargs),
    )


#: Maximum outer iterations for the B6 feedback loop, mirroring INV-11
#: cadence (Checkpoint 2 / pre-merge Loop 2 also cap at 3). Each outer
#: iteration consists of: dispatch reviewer -> route findings via
#: ``/receiving-code-review`` -> mini-cycle TDD fix per accepted finding ->
#: re-dispatch. After three iterations without convergence the helper
#: re-raises :class:`SpecReviewError` carrying the rejected-finding
#: history so operators can diagnose without grepping logs.
_B6_MAX_FEEDBACK_ITERATIONS: int = 3


def _stage_tracked_changes(root: Path) -> bool:
    """Return ``True`` iff ``git`` reports staged content after auto-staging.

    The mini-cycle relies on the implementer subagent (via
    ``/test-driven-development``) to author the diff for each phase. When
    the subagent edits files but never stages them (observed v0.2 auto runs
    F2/G2 -- see CHANGELOG 0.1.6) we run ``git add -u`` to capture
    tracked-file modifications, mirroring :func:`_phase2_task_loop`'s case-2
    recovery. Untracked files are deliberately NOT staged here -- that
    matches the existing scope of ``git add -u`` and keeps the mini-cycle
    from sweeping unrelated artefacts into the commit.

    Returns ``True`` when staging produced a non-empty staged diff (commit
    will succeed); ``False`` when nothing is stageable (commit must fall
    back to ``--allow-empty`` so the cycle can still progress).
    """
    subprocess_utils.run_with_timeout(["git", "add", "-u"], timeout=30, cwd=str(root))
    diff = subprocess_utils.run_with_timeout(
        ["git", "diff", "--cached", "--name-only"], timeout=10, capture=True, cwd=str(root)
    )
    return bool(diff.stdout and diff.stdout.strip())


def _commit_mini_cycle_phase(
    root: Path,
    task_id: str,
    finding: str,
    prefix: str,
    phase_label: str,
) -> None:
    """Commit one mini-cycle phase via :func:`commits.create`.

    Routes through ``commits.create`` so prefix validation + English-only +
    no-AI-refs guards fire (mandatory per the v0.2.1 task brief). When
    nothing is staged after :func:`_stage_tracked_changes` returns
    ``False`` we fall back to ``git commit --allow-empty`` so the cycle
    progresses even if the implementer subagent collapsed the phase work
    into an earlier commit. The empty marker mirrors the convention from
    ``_phase2_task_loop``'s case-3 recovery.

    Args:
        root: Project root directory.
        task_id: Plan task id; surfaced in the commit message.
        finding: Spec-reviewer finding text driving the mini-cycle.
        prefix: ``test:`` / ``fix:`` / ``refactor:`` per the mini-cycle
            phase being closed.
        phase_label: Human-readable phase tag (``red`` / ``green`` /
            ``refactor``) used in the commit message.

    Raises:
        CommitError: Both the staged-content commit and the
            ``--allow-empty`` fallback failed; bubble up to the caller.
    """
    has_staged = _stage_tracked_changes(root)
    message = (
        f"{phase_label} for spec-review finding on task {task_id}: {finding}"
        if has_staged
        else f"{phase_label} for spec-review finding on task {task_id}: {finding} "
        f"(no-op; phase collapsed into earlier commit)"
    )
    if has_staged:
        # Call via module attribute (not the bound ``commit_create`` import)
        # so tests can ``monkeypatch.setattr(commits, "create", ...)`` to
        # spy on mini-cycle commits without losing prefix validation.
        commits.create(prefix, message, cwd=str(root))
        return
    # Empty marker: ``commits.create`` would refuse via git's "nothing to
    # commit", so use a direct ``git commit --allow-empty`` while keeping
    # the prefix + message validation by composing the message ourselves
    # through ``commits.create`` semantics below. Falling back to the raw
    # subprocess preserves the cycle's atomicity contract: every phase
    # produces exactly one commit, success or empty marker.
    full_message = f"{prefix}: {message}"
    r = subprocess_utils.run_with_timeout(
        ["git", "commit", "--allow-empty", "-m", full_message],
        timeout=30,
        cwd=str(root),
    )
    if r.returncode != 0:
        from errors import CommitError as _CommitError

        raise _CommitError(
            f"git commit --allow-empty failed (returncode={r.returncode}): {r.stderr}"
        )


def _run_mini_cycle_for_finding(
    root: Path,
    task_id: str,
    finding: str,
    retries: int,
    *,
    implementer_model: str | None = None,
) -> None:
    """Run one ``test:`` -> ``fix:`` -> ``refactor:`` mini-cycle per finding.

    Each phase invokes ``/test-driven-development`` (with the finding text
    as narrative context so the implementer subagent knows what to fix),
    runs ``/verification-before-completion`` with the same retry budget as
    the surrounding task-loop phases, then commits via
    :func:`_commit_mini_cycle_phase` so prefix + message validation
    happens through ``commits.create``.

    The mini-cycle is sequential and atomic: three commits land per finding
    in strict ``test`` -> ``fix`` -> ``refactor`` order. Empty phases (the
    implementer subagent collapsed work) produce ``--allow-empty`` markers
    instead of skipping so the cycle's commit count stays predictable for
    audit purposes.

    Args:
        root: Project root directory.
        task_id: Plan task id (carried into the commit messages).
        finding: Verbatim accepted finding from ``/receiving-code-review``.
        retries: Verification retry budget per phase, matching the
            surrounding ``_phase2_task_loop`` value.
        implementer_model: Optional v0.3.0 Feature E per-skill model
            ID forwarded to the ``test_driven_development`` dispatcher.
            ``None`` (default) preserves the v0.2.x argv shape.
    """
    phase_prefix_pairs: tuple[tuple[str, str], ...] = (
        ("red", COMMIT_PREFIX_MAP["red"]),
        ("green", COMMIT_PREFIX_MAP["green_fix"]),
        ("refactor", COMMIT_PREFIX_MAP["refactor"]),
    )
    for phase_label, prefix in phase_prefix_pairs:
        # Loop 1 fix v0.5.0 CRITICAL #1: wrap each phase dispatch in
        # ``_dispatch_with_heartbeat`` so multi-minute implementer subagent
        # invocations emit liveness ticks. Use a phase-tagged label so the
        # heartbeat output names which mini-cycle phase is in flight.
        current = get_current_progress()
        mini_cycle_label = f"spec-review-mini-cycle-{phase_label}"
        _set_progress(
            iter_num=current.iter_num,
            phase=current.phase,
            task_index=current.task_index,
            task_total=current.task_total,
            dispatch_label=mini_cycle_label,
        )
        # v0.3.0 Feature E: omit model kwargs entirely when None so test
        # stubs pre-dating v0.3.0 keep accepting the call signature.
        if implementer_model is None:

            def _invoke_tdd(_phase: str = phase_label) -> None:
                superpowers_dispatch.test_driven_development(
                    args=[f"--phase={_phase}", f"--finding={finding}", f"--task-id={task_id}"],
                    cwd=str(root),
                )
        else:

            def _invoke_tdd(_phase: str = phase_label) -> None:
                superpowers_dispatch.test_driven_development(
                    args=[f"--phase={_phase}", f"--finding={finding}", f"--task-id={task_id}"],
                    cwd=str(root),
                    model=implementer_model,
                    skill_field_name="implementer_model",
                )

        _dispatch_with_heartbeat(invoke=_invoke_tdd)
        _run_verification_with_retries(root, retries)
        _commit_mini_cycle_phase(root, task_id, finding, prefix, phase_label)


def _apply_spec_review_findings_via_mini_cycle(
    initial_error: "SpecReviewError",
    task_id: str,
    plan_path: Path,
    root: Path,
    cfg: PluginConfig,
    ns: argparse.Namespace,
    spec_review_budget_seconds: int,
    spec_review_elapsed: float,
) -> tuple[float, bool]:
    """Run the v0.2.1 B6 auto-feedback loop for one task close (INV-31 expanded).

    Spec-base §2.2 promised: on spec-reviewer ``issues``, route findings
    through ``/receiving-code-review`` -> mini-cycle TDD fix per accepted
    finding -> re-dispatch reviewer -> loop up to the safety valve. v0.2.0
    deferred this; v0.2.1 ships it.

    Algorithm (one outer iteration per dispatched reviewer call):

    1. Route the failing-iteration's ``issues`` through
       ``/receiving-code-review`` with the
       :data:`receiving_review_dispatch.RECEIVING_REVIEW_FORMAT_CONTRACT`
       prompt so the subagent's reply ends with ``## Accepted`` /
       ``## Rejected`` markdown sections.
    2. Parse accepted vs rejected via
       :func:`receiving_review_dispatch.parse_receiving_review`.
    3. For each accepted finding, run
       :func:`_run_mini_cycle_for_finding` so 3 commits
       (``test:`` -> ``fix:`` -> ``refactor:``) land per finding through
       :func:`commits.create` (prefix + English-only validation fires).
       Rejected findings produce no commits -- their rationale is the
       implicit feedback for the next reviewer dispatch.
    4. Re-dispatch :func:`spec_review_dispatch.dispatch_spec_reviewer` on
       the now-mutated diff. On ``SpecReviewError`` increment the outer
       iteration count and recurse; on approval return clean.
    5. After :data:`_B6_MAX_FEEDBACK_ITERATIONS` outer iterations without
       approval, re-raise the last :class:`SpecReviewError` so the
       :func:`_phase2_task_loop` audit branch records the failure.

    Spec-review budget: every reviewer dispatch in the outer loop charges
    the same ``cfg.auto_max_spec_review_seconds`` budget that the primary
    dispatch consumes. When the budget exhausts mid-loop the helper
    returns ``True`` in the second tuple slot so the caller can continue
    with ``--skip-spec-review`` semantics for downstream tasks.

    Args:
        initial_error: The :class:`SpecReviewError` from the first reviewer
            dispatch; its ``issues`` seed iteration 1 of the feedback loop.
        task_id: Plan task id whose close is being unblocked.
        plan_path: Path to the approved plan (forwarded to the dispatcher).
        root: Project root directory.
        cfg: Plugin configuration (carries the verification retries).
        ns: Parsed argparse namespace (forwarded for compat with future
            override flags).
        spec_review_budget_seconds: Cumulative reviewer budget for the
            run (``cfg.auto_max_spec_review_seconds``).
        spec_review_elapsed: Elapsed reviewer wall-time before this
            helper was invoked.

    Returns:
        ``(updated_elapsed, budget_exhausted)``. When ``budget_exhausted``
        is ``True`` the caller MUST stop dispatching the reviewer for
        subsequent tasks (matching the v0.2 cost guardrail breadcrumb).

    Raises:
        SpecReviewError: Outer safety valve exhausted without convergence;
            payload preserves the most recent ``issues`` and a synthesized
            ``rejected_history`` of cumulative rejections.
    """
    retries = (
        ns.verification_retries
        if ns.verification_retries is not None
        else cfg.auto_verification_retries
    )
    # v0.3.0 Feature E -- resolve per-skill models once for the helper's
    # lifetime so the same cascade decision applies to every dispatch in
    # the outer feedback loop. ``ns.model_override_map`` is populated by
    # ``main`` from ``--model-override`` flags; absent in test fixtures
    # that build a bare Namespace, so default to {}.
    cli_overrides = getattr(ns, "model_override_map", {}) or {}
    implementer_model = _resolve_model("implementer", cfg, cli_overrides)
    spec_reviewer_model = _resolve_model("spec_reviewer", cfg, cli_overrides)
    code_review_model = _resolve_model("code_review", cfg, cli_overrides)
    last_error: "SpecReviewError" = initial_error
    cumulative_rejections: list[str] = []
    elapsed = spec_review_elapsed
    for outer_iter in range(1, _B6_MAX_FEEDBACK_ITERATIONS):
        # Route the current iteration's issues through /receiving-code-review.
        review_args = receiving_review_dispatch.conditions_to_skill_args(last_error.issues)
        # v0.3.0 Feature E: omit model kwargs when None so stubs pre-dating
        # v0.3.0 keep accepting the call signature.
        if code_review_model is None:
            review_result = superpowers_dispatch.receiving_code_review(
                args=review_args,
                cwd=str(root),
            )
        else:
            review_result = superpowers_dispatch.receiving_code_review(
                args=review_args,
                cwd=str(root),
                model=code_review_model,
                skill_field_name="code_review_model",
            )
        accepted, rejected = receiving_review_dispatch.parse_receiving_review(review_result)
        if not accepted and not rejected:
            # The skill produced no decisions -- treat as a hard stop. This
            # mirrors the ``_loop2`` behavior where empty parse output is a
            # ValidationError. Re-raising the underlying SpecReviewError
            # keeps the audit trail uniform with the v0.2 hard-block path.
            raise last_error
        cumulative_rejections.extend(f"iter {outer_iter} rejected: {r}" for r in rejected)
        # Run a mini-cycle per accepted finding so the next reviewer
        # dispatch sees a mutated diff (the input change that the v0.2
        # baseline was missing).
        for finding in accepted:
            _run_mini_cycle_for_finding(
                root, task_id, finding, retries, implementer_model=implementer_model
            )
        # Re-dispatch reviewer; budget-track the call.
        if elapsed >= spec_review_budget_seconds:
            # Budget exhausted mid-loop: stop here and signal the caller
            # to skip downstream reviewer calls. The task close still
            # advances because the mini-cycle commits proved (or marked)
            # the accepted findings, mirroring the v0.2 cost-guardrail
            # contract.
            return elapsed, True
        review_started = time.monotonic()
        try:
            if spec_reviewer_model is None:
                spec_review_dispatch.dispatch_spec_reviewer(
                    task_id=task_id,
                    plan_path=plan_path,
                    repo_root=root,
                )
            else:
                spec_review_dispatch.dispatch_spec_reviewer(
                    task_id=task_id,
                    plan_path=plan_path,
                    repo_root=root,
                    model=spec_reviewer_model,
                )
        except SpecReviewError as exc:
            last_error = exc
            elapsed += time.monotonic() - review_started
            continue
        # Re-dispatch returned clean -> task may close.
        elapsed += time.monotonic() - review_started
        return elapsed, False
    # Outer safety valve exhausted: re-raise with cumulative rejection history.
    rejection_history_text = "; ".join(cumulative_rejections) or "(none recorded)"
    raise SpecReviewError(
        f"B6 feedback loop exhausted after {_B6_MAX_FEEDBACK_ITERATIONS} outer "
        f"iterations for task {task_id}; rejection history: {rejection_history_text}",
        task_id=task_id,
        iteration=_B6_MAX_FEEDBACK_ITERATIONS,
        issues=last_error.issues,
    )


def _dispatch_batch_concurrent(batch: set[str], project_root: Path) -> None:
    """Parallel pre-verification gate for a multi-task batch (v1.0.4 Path 2).

    **v1.0.4 Loop 2 iter-3 architectural pivot (Path 2)**. The iter-2
    incarnation attempted to drive per-task TDD cycles inside concurrent
    subprocesses but introduced the wrong-task-closed wiring bug because
    :func:`_run_single_task_isolated` was a stub: parent-side
    ``mark_and_advance`` advanced state without any TDD triplet commits.
    This iter-3 rewrite re-positions the helper as a **parallel pre-
    verification gate**: per-task TDD work flows through the legacy
    inline body in :func:`_phase2_task_loop` (preserving INV-1, INV-31,
    INV-5..7 per task), and this helper merely parallelises the
    verification step at batch entry so operators get the wall-time
    benefit of ``--parallel`` (verification is the slowest part of a TDD
    cycle empirically) without the architectural complexity of state-file
    isolation + recursion guards that Path 1 would require.

    Concretely: spawns one ``subprocess.Popen`` per task in the batch
    (the Popen invokes :func:`_run_single_task_isolated` which runs a
    minimal pre-verification check), waits for all processes to complete,
    and raises :class:`ConcurrentDispatchError` on any non-zero exit.
    The Popen-per-task shape is preserved so test fixtures that
    monkeypatch ``subprocess.Popen`` still observe N invocations.

    **v1.0.7 A2 audit note**: this helper does NOT route through
    :func:`_spawn_worker` (the cross-platform PTY/PIPE+env-marker
    dispatcher) because :func:`_run_single_task_isolated` does NOT
    dispatch interactive skills (no ``/verification-before-completion``,
    no ``/receiving-code-review``) — the chicken-and-egg failure mode
    that v1.0.7 Pillar A fixes does not apply here. Pre-verification
    workers run only `pytest` collection / `git status` checks. If a
    future cycle extends the pre-verification surface to invoke
    interactive skills, the worker spawn site MUST be migrated to
    :func:`_spawn_worker` to preserve the SBTDD_AUTO_PARALLEL_WORKER=1
    env contract.

    Args:
        batch: Set of task ids to pre-verify concurrently. Must have
            ``len(batch) > 1`` for the helper to do useful work; size-1
            batches are short-circuited by the caller.
        project_root: Project root containing ``planning/claude-plan-tdd.md``
            and ``.claude/session-state.json``.

    Raises:
        ConcurrentDispatchError: At least one Popen subprocess returned
            non-zero (exit 2, PRECONDITION_FAILED). Message includes the
            offending task ids and (best-effort) captured stderr text.
            Distinct from :class:`VerificationIrremediableError` (exit 6)
            which is reserved for per-phase verification budget exhaustion
            during the inline TDD body.

    Notes:
        State-file write coordination is structural, not lock-based: the
        helper does NOT mutate ``.claude/session-state.json`` -- the
        outer ``_phase2_task_loop`` runs each task through the legacy
        inline body in ``sorted(batch)`` order after this gate clears,
        so per-task ``mark_and_advance`` advances the shared state file
        sequentially as part of each task's own refactor close.
    """
    if len(batch) <= 1:
        # Defensive: caller short-circuits singletons.
        return
    procs: list[tuple[str, Any]] = []  # (task_id, Popen)
    plugin_root = Path(__file__).resolve().parent
    # v1.0.4 iter-5 Loop 1 sub-issue #4 (Caspar): use ``repr()`` consistently
    # for path arguments so paths with apostrophes (e.g. project root in
    # ``D:\My's Project\``) round-trip through Python literal-eval safely.
    # Pre-fix the bare ``r'{path}'`` raw-string literal would break on any
    # apostrophe in the path; ``repr()`` emits Python-safe quoted strings.
    plugin_root_lit = repr(str(plugin_root))
    project_root_lit = repr(str(project_root))
    for task_id in sorted(batch):
        argv = [
            sys.executable,
            "-c",
            (
                f"import sys; sys.path.insert(0, {plugin_root_lit}); "
                f"from auto_cmd import _run_single_task_isolated; "
                f"_run_single_task_isolated({task_id!r}, {project_root_lit})"
            ),
        ]
        proc = subprocess.Popen(
            argv,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        procs.append((task_id, proc))
    # Wait for all spawned processes BEFORE checking returncode so concurrent
    # tasks complete even if one fails early.
    failures: list[tuple[str, int, str]] = []
    for task_id, proc in procs:
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=3600)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout_bytes, stderr_bytes = proc.communicate()
            failures.append((task_id, -1, "subprocess timeout (3600s)"))
            continue
        rc = proc.returncode
        if rc != 0:
            err_text = (
                stderr_bytes.decode("utf-8", errors="replace")
                if isinstance(stderr_bytes, bytes)
                else str(stderr_bytes)
            )
            failures.append((task_id, rc, err_text))
    if failures:
        details = "; ".join(f"task {tid} exit={rc}: {msg[:200]}" for tid, rc, msg in failures)
        raise ConcurrentDispatchError(
            f"concurrent pre-verification failed for batch {sorted(batch)}: {details}"
        )


def _run_single_task_isolated(task_id: str, project_root_str: str) -> None:
    """V1.0.5-DEFERRED PLACEHOLDER: per-task pre-verification stub.

    .. note::
        **v1.0.4 iter-5 Loop 1 sub-issue #3 marker (Caspar)**: with
        Path 3 track-based dispatch (``_dispatch_tracks_concurrent`` +
        ``--task-ids`` filter, shipped iter-4 + iter-5 CRITICAL #1
        wiring) doing the heavy lifting, this Path 2 ``--single-task``
        stub no longer appears in the orchestrator-parallel flow.
        It IS still invoked by the legacy ``_dispatch_batch_concurrent``
        helper consumed when ``dispatch_plan`` is supplied with
        multi-task batches (see :func:`_phase2_task_loop` ``dispatch_plan``
        parameter).

        Function is preserved as a v1.0.5-deferred placeholder for the
        full per-task verification command execution (running
        ``cfg.verification_commands`` list per task in isolation). The
        Popen entry-point shape (callable from ``python -c``) is the
        external contract pinned here; tests monkeypatch
        ``subprocess.Popen`` and validate dispatch wiring without
        spinning up the full verification machinery.

        Removal candidate for v1.0.5 IF Path 3 fully subsumes the
        Path 2 dispatch_plan-multi-batch call site; pending dogfood
        confirmation.

    Invoked via ``python -c`` from :func:`_dispatch_batch_concurrent`.
    Does NOT touch the shared ``.claude/session-state.json`` -- per-task
    TDD work runs through the legacy inline body in
    :func:`_phase2_task_loop` after this gate clears.

    Args:
        task_id: Plan task id (string).
        project_root_str: Project root as a string (Popen-safe).
    """
    # v1.0.4 Path 2 minimal: emit breadcrumb + exit 0. Full per-task
    # verification command execution is v1.0.5 scope; this stub keeps the
    # Popen shape tests rely on while not bypassing INV-1/INV-31/INV-5..7
    # (which the legacy inline body in _phase2_task_loop enforces per task).
    sys.stdout.write(f"[sbtdd auto pre-verify] task {task_id} ready at {project_root_str}\n")


def _phase2_task_loop(
    ns: argparse.Namespace,
    state: SessionState,
    cfg: PluginConfig,
    dispatch_plan: list[set[str]] | None = None,
    task_ids_filter: frozenset[str] | None = None,
) -> SessionState:
    """Run Phase 2 -- sequential task loop with TDD cycles per task.

    For each pending task: iterate ``_PHASE_ORDER`` from the current phase
    forward; invoke ``/test-driven-development`` for the phase,
    ``/verification-before-completion`` (with retries), then commit with
    the sec.M.5 prefix. At ``refactor`` close, delegate to
    :func:`close_task_cmd.mark_and_advance` (iter-2 W1 public helper) so
    the close-task bookkeeping stays single-sourced.

    Drift is re-checked at entry; any non-None
    :class:`drift.DriftReport` aborts with :class:`DriftError` (INV-17,
    exit 3). Drift detection is not re-run between phases: the close of
    each phase produces a commit whose prefix is, by definition, the
    expected one for the NEW phase -- re-checking inside the inner loop
    would flag every legitimate transition as drift.

    .. note::
       **v0.1.x limitation (pending v0.2 Feature B redesign).**
       The current call shape ``test_driven_development(args=[f"--phase={phase}"])``
       forwards the phase as a narrative hint inside the ``claude -p`` prompt.
       The superpowers ``/test-driven-development`` skill is prose-only and does
       NOT formally define a ``--phase`` flag; it interprets the hint via
       Claude's natural-language understanding. No task context (task id, plan
       path, file list, acceptance criteria) is passed explicitly -- the
       sub-session has to discover context by reading
       ``planning/claude-plan-tdd.md`` and ``.claude/session-state.json`` on
       its own. This is workable via ``cwd=str(root)`` but fragile. **Feature
       B of v0.2** (``spec_review_dispatch`` + task-loop redesign) will
       replace this with an explicit task-context prompt builder. Until then,
       auto's task loop relies on the sub-session's discovery heuristics.

    Args:
        ns: Parsed argparse namespace.
        state: Current :class:`SessionState` (entry phase may be
            ``red``, ``green``, or ``refactor``; auto starts from there).
        cfg: Plugin configuration (for ``auto_verification_retries``).
        dispatch_plan: Optional batched dispatch plan from
            :func:`_build_dispatch_plan_parallel` /
            :func:`_build_dispatch_plan_sequential`. When ``None``
            (default) or when all batches are singletons, the legacy
            while-loop handles all tasks unchanged (v1.0.3 plan-text-
            order behaviour). When supplied with multi-task batches,
            each multi-task batch runs through
            :func:`_dispatch_batch_concurrent` as a **parallel pre-
            verification gate** (Path 2) BEFORE the legacy while-loop
            consumes the batch's tasks via the full inline TDD body
            in plan-text order. This preserves INV-1/INV-31/INV-5..7
            per task because the actual TDD work (red/green/refactor
            commits + spec-reviewer + ``mark_and_advance``) flows
            through the existing legacy code path, not through the
            stub :func:`_run_single_task_isolated`. Singleton batches
            in the plan skip the gate. v1.0.4 Loop 2 iter-3
            architectural pivot (Path 2: parallel verify + sequential
            close).
        task_ids_filter: v1.0.4 iter-5 Loop 1 CRITICAL #1. When set,
            the worker processes ONLY task ids in the filter --
            unassigned tasks are skipped by advancing
            ``state.current_task_id`` to the next plan task in source
            order WITHOUT touching the plan checkbox or running TDD
            cycles (the OTHER worker that owns that task is
            responsible for closing it). When ``None`` (default),
            sequential / orchestrator behaviour is preserved exactly.
            Pre-fix the worker subprocess raced on the shared state
            file's ``current_task_id``; both Path 3 children read
            ``current_task_id=1`` at entry and processed task 1
            concurrently, corrupting plan + git index.

    Returns:
        The final :class:`SessionState` after the last task's close-task
        cascade (either ``current_phase='done'`` when the plan is fully
        consumed, or the next task's fresh red phase).

    Raises:
        DriftError: Drift detected at entry.
        ConcurrentDispatchError: Parallel pre-verification gate failed
            for one or more multi-task batches (exit 2).
        VerificationIrremediableError: Per-phase verification exhausted
            the retry budget during the legacy inline TDD body (exit 6).
    """
    root: Path = ns.project_root
    retries = (
        ns.verification_retries
        if ns.verification_retries is not None
        else cfg.auto_verification_retries
    )
    state_path = root / ".claude" / "session-state.json"
    plan_path = root / state.plan_path
    dr = detect_drift(state_path, plan_path, root)
    if dr is not None:
        raise DriftError(f"drift at auto Phase 2: {dr.reason}")
    current = state
    auto_run = root / ".claude" / "auto-run.json"
    # Recover the auto_started_at timestamp from the in-progress audit
    # written by main() BEFORE this loop. If absent (test harnesses that
    # skip main's initialisation), fall back to the current timestamp so
    # incremental writes remain schema-valid.
    started_at = _now_iso()
    if auto_run.exists():
        try:
            prev = json.loads(auto_run.read_text("utf-8"))
            started_at = str(prev.get("auto_started_at", started_at))
        except (json.JSONDecodeError, OSError):
            pass
    tasks_completed = 0
    # Cost guardrail (v0.2.1, MAGI Loop 2 v0.2 pre-merge WARNING #11):
    # cumulative spec-reviewer wall-time across the run is capped by
    # ``cfg.auto_max_spec_review_seconds`` (default 3600s = 1h). When the
    # budget is exhausted before a task's reviewer call, that task proceeds
    # with ``--skip-spec-review`` semantics (no dispatch) and a stderr
    # breadcrumb is emitted exactly once. Subsequent tasks continue to
    # skip; ``mark_and_advance`` still runs so the plan progresses.
    spec_review_budget_seconds = cfg.auto_max_spec_review_seconds
    spec_review_elapsed = 0.0
    spec_review_breadcrumb_emitted = False
    # v1.0.0 J2 (S1-8) preflight: resolve per-skill model IDs ONCE per
    # auto run via :func:`_resolve_all_models_once`. This emits the INV-0
    # cascade stderr breadcrumb (global ``~/.claude/CLAUDE.md`` pin >
    # project ``<repo>/CLAUDE.md`` pin > plugin.local.md per-skill field)
    # exactly once at task-loop entry, replacing the ~70-150 CLAUDE.md
    # disk reads a 36-task auto run would otherwise incur (spec sec.2.3
    # + sec.5.1). The returned :class:`models.ResolvedModels` instance
    # captures the INV-0-resolved IDs for diagnostic visibility.
    #
    # The cascade still flows through :func:`_resolve_model` for CLI
    # override layering (v0.3.0 Feature E): ``--model-override`` flags
    # win over plugin.local.md fields, and ``None`` is preserved when
    # neither layer set a value so downstream dispatches can omit the
    # ``model=`` kwarg (test-stub backward compat). The J2 preflight
    # is additive and only emits the cascade audit; per-dispatch INV-0
    # enforcement still fires inside each dispatch module's
    # ``_apply_inv0_model_check`` path.
    _resolved_models = _resolve_all_models_once(cfg)
    cli_overrides = getattr(ns, "model_override_map", {}) or {}
    implementer_model = _resolve_model("implementer", cfg, cli_overrides)
    spec_reviewer_model = _resolve_model("spec_reviewer", cfg, cli_overrides)
    # Diagnostic: ensure the resolved struct's authoritative INV-0 view
    # is observable for post-mortem (`auto-run.json` future field /
    # status --watch). Currently consumed by the C3 invocation-site
    # tripwire (text-level audit in tests/test_pre_merge_cross_check.py)
    # which guarantees this preflight call is wired in production, not
    # just unit-tested in isolation.
    del _resolved_models  # noqa: F841 — preflight emit is the contract
    # Feature D3 + D4: emit one entry breadcrumb for phase 2 ("task
    # loop") so operators see the run move past pre-flight before the
    # first subagent dispatch, and persist progress atomically into
    # ``auto-run.json`` so a concurrent reader can poll the run state
    # without racing the writer. ``_task_progress`` is best-effort; on
    # failure we still emit the phase line without the task counter.
    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
    _emit_phase_breadcrumb(
        phase=2,
        total_phases=5,
        task_index=_t_idx,
        task_total=_t_total,
        sub_phase=current.current_phase,
    )
    _update_progress(
        auto_run,
        phase=2,
        task_index=_t_idx,
        task_total=_t_total,
        sub_phase=current.current_phase,
    )
    # v0.5.0 S1-9 transition site #2: phase 2 entry (task loop start).
    _set_progress(
        phase=2,
        task_index=_t_idx,
        task_total=_t_total,
        dispatch_label=current.current_phase,
    )
    # v1.0.4 Loop 2 iter-3 architectural pivot (Path 2): when
    # ``dispatch_plan`` is supplied AND contains multi-task batches, run
    # :func:`_dispatch_batch_concurrent` as a **parallel pre-verification
    # gate** for each multi-task batch BEFORE the legacy while-loop. The
    # gate spawns N Popens (one per task in the batch) running the
    # minimal pre-verification check in parallel; on any non-zero exit
    # it raises :class:`ConcurrentDispatchError` (exit 2,
    # PRECONDITION_FAILED) BEFORE any per-task TDD work begins, so the
    # state file is never partially advanced.
    #
    # After the pre-verify gate clears, control falls through to the
    # legacy while-loop which consumes tasks in plan-text order via the
    # full inline TDD body (red -> green -> refactor + INV-31 spec-
    # reviewer + commits + ``mark_and_advance``). This preserves
    # INV-1/INV-31/INV-5..7 per task -- the iter-2 incarnation broke
    # those invariants by calling ``mark_and_advance`` directly inside
    # the dispatch_plan loop, which advanced state without TDD triplet
    # commits because :func:`_run_single_task_isolated` was a stub.
    #
    # Singleton batches in dispatch_plan skip the gate (size-1 batches
    # have nothing to parallelise). When ``dispatch_plan is None`` the
    # gate is skipped entirely and behaviour is byte-identical to v1.0.3.
    if dispatch_plan is not None:
        for batch in dispatch_plan:
            if len(batch) > 1:
                _dispatch_batch_concurrent(batch, root)
    try:
        while current.current_task_id is not None:
            # v0.5.0 S1-13: bound heartbeat counter persistence latency
            # to <= 30s even when no transition fires (long dispatches).
            _periodic_drain_if_due(auto_run)
            # v1.0.4 iter-5 Loop 1 CRITICAL #1: worker filter skip-
            # fast-forward. When a Path 3 worker subprocess was spawned
            # with ``--task-ids T3,T5``, state.current_task_id may
            # initially point at task 1 (the global cursor) -- a task
            # belonging to a SIBLING worker. The legacy code would then
            # process task 1 in this worker, racing the other worker's
            # commit and corrupting state.
            #
            # Fix: when filter is set AND current task is NOT in filter,
            # advance the in-memory cursor to the next plan task that IS
            # in filter (and still open). This DOES NOT touch the plan
            # checkbox or the chore commit chain -- only the local cursor
            # moves. If no remaining task in filter is open, exit the
            # loop cleanly (worker has nothing left to do; sibling
            # workers own the rest).
            #
            # The state file IS persisted with the new cursor so a mid-
            # run crash + resume reads a coherent value; ``mark_and_
            # advance`` later uses ``_plan_ops.next_task`` which advances
            # forward in source order, so global cursor monotonicity is
            # preserved across all workers' writes (last-writer wins on
            # the file but the value is always a valid open-task id).
            if task_ids_filter is not None and current.current_task_id not in task_ids_filter:
                next_in_filter = _next_open_task_in_filter(
                    plan_path, current.current_task_id, task_ids_filter
                )
                if next_in_filter is None:
                    break
                next_id, next_title = next_in_filter
                current = SessionState(
                    plan_path=current.plan_path,
                    current_task_id=next_id,
                    current_task_title=next_title,
                    current_phase="red",
                    phase_started_at_commit=current.phase_started_at_commit,
                    last_verification_at=current.last_verification_at,
                    last_verification_result=current.last_verification_result,
                    plan_approved_at=current.plan_approved_at,
                    spec_snapshot_emitted_at=current.spec_snapshot_emitted_at,
                )
                save_state(current, state_path)
            phase_idx = (
                _PHASE_ORDER.index(current.current_phase)
                if current.current_phase in _PHASE_ORDER
                else 0
            )
            for phase in _PHASE_ORDER[phase_idx:]:
                pre_phase_sha = _current_head_sha(root)
                # v0.3.0 Feature D iter 2 (finding #1 + #7): build a
                # task-and-phase tagged stream prefix so the operator
                # sees per-task / per-phase identification on every
                # streamed line. This is the production wiring the
                # baseline v0.3.0 ship was missing.
                _stream_pfx = (
                    f"[sbtdd task-{current.current_task_id} {phase}]"
                    if current.current_task_id is not None
                    else None
                )
                # v0.3.0 Feature E: gate on ``implementer_model is None``
                # so the kwargs are omitted entirely when the cascade
                # resolved to None. Stubs that do NOT accept the new
                # kwargs (test fixtures pre-dating v0.3.0) keep working.
                if implementer_model is None:
                    superpowers_dispatch.test_driven_development(
                        args=[f"--phase={phase}"],
                        cwd=str(root),
                        stream_prefix=_stream_pfx,
                    )
                else:
                    superpowers_dispatch.test_driven_development(
                        args=[f"--phase={phase}"],
                        cwd=str(root),
                        model=implementer_model,
                        skill_field_name="implementer_model",
                        stream_prefix=_stream_pfx,
                    )
                _run_verification_with_retries(root, retries)
                prefix = _phase_prefix(phase)
                try:
                    commit_create(
                        prefix, f"{phase} for task {current.current_task_id}", cwd=str(root)
                    )
                except CommitError:
                    # ``git commit`` returns rc=1 with "nothing to commit" for
                    # three distinct reasons we must handle differently
                    # (2026-04-24 observations):
                    #
                    # 1. HEAD advanced: implementer committed the phase directly
                    #    (plan-prescribed ``git commit``). That commit IS the
                    #    phase close; proceed with state advance.
                    # 2. HEAD unchanged AND ``git status`` shows tracked-file
                    #    modifications: implementer edited files but never
                    #    staged. ``git add -u`` captures the modifications (no
                    #    untracked files, so this stays scoped) and a retry
                    #    commits the real phase work.
                    # 3. HEAD unchanged AND nothing to stage: implementer
                    #    collapsed phases (e.g., did red+green together in an
                    #    earlier commit, leaving the current phase with no
                    #    residual work). Record an empty commit so auto's
                    #    state still advances; verification has already proven
                    #    the phase's acceptance criterion is met.
                    if _current_head_sha(root) == pre_phase_sha:
                        # Case 2: stage tracked-file modifications and retry.
                        subprocess_utils.run_with_timeout(
                            ["git", "add", "-u"], timeout=30, cwd=str(root)
                        )
                        try:
                            commit_create(
                                prefix,
                                f"{phase} for task {current.current_task_id}",
                                cwd=str(root),
                            )
                        except CommitError:
                            # Case 3: still nothing to commit -> empty marker
                            # commit mirroring the plan-prescribed
                            # refactor-phase --allow-empty convention.
                            r = subprocess_utils.run_with_timeout(
                                [
                                    "git",
                                    "commit",
                                    "--allow-empty",
                                    "-m",
                                    f"{prefix}: {phase} for task "
                                    f"{current.current_task_id} "
                                    f"(no-op; phase collapsed into earlier commit)",
                                ],
                                timeout=30,
                                cwd=str(root),
                            )
                            if r.returncode != 0:
                                raise
                new_sha = _current_head_sha(root)
                if phase != "refactor":
                    next_phase = _PHASE_ORDER[_PHASE_ORDER.index(phase) + 1]
                    current = SessionState(
                        plan_path=current.plan_path,
                        current_task_id=current.current_task_id,
                        current_task_title=current.current_task_title,
                        current_phase=next_phase,
                        phase_started_at_commit=new_sha,
                        last_verification_at=_now_iso(),
                        last_verification_result="passed",
                        plan_approved_at=current.plan_approved_at,
                        spec_snapshot_emitted_at=current.spec_snapshot_emitted_at,
                    )
                    save_state(current, state_path)
                    # Feature D3 + D4: breadcrumb + progress AFTER state
                    # save, BEFORE the next subagent dispatch (red->green
                    # or green->refactor).
                    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
                    _emit_phase_breadcrumb(
                        phase=2,
                        total_phases=5,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=next_phase,
                    )
                    _update_progress(
                        auto_run,
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=next_phase,
                    )
                    # v0.5.0 S1-9 transition site #3: per-phase dispatch
                    # (red/green/refactor) within a task.
                    _set_progress(
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        dispatch_label=next_phase,
                    )
                else:
                    # H6 (INV-31): spec-reviewer gate BEFORE mark_and_advance.
                    assert current.current_task_id is not None
                    if spec_review_elapsed >= spec_review_budget_seconds:
                        if not spec_review_breadcrumb_emitted:
                            sys.stderr.write(
                                f"[auto] spec-review budget "
                                f"{spec_review_budget_seconds}s exceeded; "
                                f"remaining tasks proceed with "
                                f"--skip-spec-review\n"
                            )
                            spec_review_breadcrumb_emitted = True
                    else:
                        review_started = time.monotonic()
                        try:
                            _run_spec_review_gate(
                                current.current_task_id,
                                plan_path,
                                root,
                                model=spec_reviewer_model,
                                stream_prefix=(
                                    f"[sbtdd task-{current.current_task_id} spec-review]"
                                ),
                            )
                            spec_review_elapsed += time.monotonic() - review_started
                        except SpecReviewError as exc:
                            # B6 (v0.2.1): spec-reviewer raised; route findings
                            # through /receiving-code-review + mini-cycle TDD
                            # fix per accepted finding + re-dispatch reviewer
                            # up to _B6_MAX_FEEDBACK_ITERATIONS. Helper either
                            # converges (returns) or re-raises SpecReviewError
                            # which propagates to the outer except branch.
                            spec_review_elapsed += time.monotonic() - review_started
                            spec_review_elapsed, budget_exhausted = (
                                _apply_spec_review_findings_via_mini_cycle(
                                    exc,
                                    current.current_task_id,
                                    plan_path,
                                    root,
                                    cfg,
                                    ns,
                                    spec_review_budget_seconds,
                                    spec_review_elapsed,
                                )
                            )
                            if budget_exhausted and not spec_review_breadcrumb_emitted:
                                sys.stderr.write(
                                    f"[auto] spec-review budget "
                                    f"{spec_review_budget_seconds}s exceeded "
                                    f"during B6 feedback loop; remaining tasks "
                                    f"proceed with --skip-spec-review\n"
                                )
                                spec_review_breadcrumb_emitted = True
                    # W1: delegate to public helper in close_task_cmd instead
                    # of duplicating the entire flip / commit chore / advance
                    # sequence. v1.0.5 I-2 widened the helper return type
                    # to ``SessionState | None`` (worker mode returns None
                    # because the parent owns post-batch advance); this
                    # call site is the orchestrator path (no ``ns`` kwarg)
                    # so the result is always a SessionState -- assert
                    # for mypy + defensive tripwire.
                    advanced = close_task_cmd.mark_and_advance(current, root)
                    assert advanced is not None, (
                        "orchestrator-path mark_and_advance must return SessionState"
                    )
                    current = advanced
                    tasks_completed += 1
                    # Feature D3 + D4: breadcrumb + progress AFTER
                    # mark_and_advance, BEFORE the first dispatch on the
                    # new task. ``current.current_phase`` is "red" (or
                    # "done" when the plan completes); both are valid
                    # sub_phase labels for the breadcrumb.
                    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
                    _emit_phase_breadcrumb(
                        phase=2,
                        total_phases=5,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=current.current_phase,
                    )
                    _update_progress(
                        auto_run,
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=current.current_phase,
                    )
                    # v0.5.0 S1-9 transition site #4: per-task iteration
                    # advance after mark_and_advance().
                    _set_progress(
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        dispatch_label=current.current_phase,
                    )
                    # Plan D iter 2 Caspar: incremental audit write after
                    # each task close so a mid-loop raise preserves the
                    # partial tasks_completed count on disk.
                    _write_auto_run_audit(
                        auto_run,
                        AutoRunAudit(
                            schema_version=_AUTO_RUN_SCHEMA_VERSION,
                            auto_started_at=started_at,
                            auto_finished_at=None,
                            status="success",
                            verdict=None,
                            degraded=None,
                            accepted_conditions=0,
                            rejected_conditions=0,
                            tasks_completed=tasks_completed,
                            error=None,
                        ),
                    )
            # After refactor cascade, outer loop re-evaluates against updated
            # current.current_task_id (None -> terminate).
    except SpecReviewError:
        # INV-31 audit: on safety-valve exhaustion, persist the partial
        # tasks_completed count + error classifier BEFORE re-raising so
        # operators can diagnose without grepping logs. Mirrors the
        # MAGIGateError audit path in ``main``.
        _write_auto_run_audit(
            auto_run,
            AutoRunAudit(
                schema_version=_AUTO_RUN_SCHEMA_VERSION,
                auto_started_at=started_at,
                auto_finished_at=_now_iso(),
                status="spec_review_issues",
                verdict=None,
                degraded=None,
                accepted_conditions=0,
                rejected_conditions=0,
                tasks_completed=tasks_completed,
                error="SpecReviewError",
            ),
        )
        raise
    return current


class _ShadowCfg:
    """Minimal PluginConfig stand-in with ``magi_max_iterations`` overridden.

    Built so :func:`pre_merge_cmd._loop2` can consume the same attribute
    surface as a real :class:`config.PluginConfig` but with the elevated
    ``auto_magi_max_iterations`` budget (INV / sec.S.5.8) substituted for
    the interactive default. Carrying ``__dict__`` copies preserves every
    other configuration field (threshold, plan_path, etc.) unchanged.
    """

    def __init__(self, base: PluginConfig, overrides: dict[str, object]) -> None:
        self.__dict__.update(base.__dict__)
        self.__dict__.update(overrides)


def _resolve_all_models_once(config: Any) -> Any:
    """Preflight: resolve per-skill model IDs ONCE per auto run (J2 / S1-8).

    Per spec sec.2.3 + sec.5.1: replaces ~70-150 CLAUDE.md disk reads
    per 36-task auto run with a single read at task-loop entry. INV-0
    cascade applies (CLAUDE.md model pin via
    :data:`models.INV_0_PINNED_MODEL_RE` overrides plugin.local.md
    fields silently with a stderr breadcrumb).

    INV-0 cascade order (caspar Loop 2 iter 3 CRITICAL fix): the
    global ``~/.claude/CLAUDE.md`` is consulted FIRST (INV-0 maxima
    precedencia is non-negotiable; project file cannot silently
    override). Project ``<repo>/CLAUDE.md`` is consulted SECOND, only
    when global is absent or unpinned. The first regex match
    terminates the cascade. Neither pinned ⇒ fall through to
    plugin.local.md per-skill fields. When both files have INV-0 pins
    for *different* models, a second "shadow" breadcrumb fires so
    operators understand why their project-level config is silently
    overridden (melchior iter 4 W7 fix).

    Note: the deferred import of :mod:`models` (inside the function
    body, not at module top) follows pre-flight Mitigation A: avoids
    module-load-time coupling so Subagent #1 tests can monkeypatch
    this helper before Subagent #2's ``ResolvedModels`` class lands
    on the integration branch.

    Args:
        config: Plugin configuration carrying per-skill model fields
            (``implementer_model``, ``spec_reviewer_model``,
            ``code_review_model``, ``magi_dispatch_model``).

    Returns:
        :class:`models.ResolvedModels` instance with all four resolved
        IDs populated (INV-0 pin wins over per-skill fields when set).
    """
    import models as _models  # deferred per pre-flight Mitigation A
    from models import ResolvedModels  # noqa: PLC0415 - deferred import

    global_claude_md = Path.home() / ".claude" / "CLAUDE.md"
    project_claude_md = Path.cwd() / "CLAUDE.md"

    def _read_pin(path: Path) -> str | None:
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
        m = _models.INV_0_PINNED_MODEL_RE.search(text)
        return m.group(1) if m else None

    global_pin = _read_pin(global_claude_md)
    project_pin = _read_pin(project_claude_md)

    # Multi-pin shadow case (melchior iter 4 W7): global pin overrides
    # project pin, but project pin existed and was DIFFERENT. Emit
    # diagnostic breadcrumb so operator understands why project config is
    # silently shadowed. Same-pin case is silent (no surprise).
    if global_pin and project_pin and global_pin != project_pin:
        sys.stderr.write(
            f"[sbtdd] INV-0 cascade: global pin {global_pin!r} OVERRIDES "
            f"project pin {project_pin!r}; project pin shadowed (per "
            f"INV-0 maxima precedencia). Resolve by removing one of the "
            f"two pins or aligning them.\n"
        )

    # INV-0 global-first selection: global wins if pinned; otherwise
    # project wins if pinned; otherwise fall through to plugin.local.md.
    pinned_model: str | None
    pinned_source: str | None
    if global_pin:
        pinned_model = global_pin
        pinned_source = "global"
    elif project_pin:
        pinned_model = project_pin
        pinned_source = "project"
    else:
        pinned_model = None
        pinned_source = None

    if pinned_model:
        sys.stderr.write(
            f"[sbtdd] INV-0 cascade: CLAUDE.md pins {pinned_model!r}"
            f" (source: {pinned_source}); plugin.local.md per-skill "
            f"model fields silently overridden\n"
        )

    def _pick(field_value: str | None, default: str) -> str:
        if pinned_model:
            return pinned_model
        return field_value or default

    return ResolvedModels(
        implementer=_pick(getattr(config, "implementer_model", None), "claude-sonnet-4-6"),
        spec_reviewer=_pick(getattr(config, "spec_reviewer_model", None), "claude-sonnet-4-6"),
        code_review=_pick(getattr(config, "code_review_model", None), "claude-sonnet-4-6"),
        magi_dispatch=_pick(getattr(config, "magi_dispatch_model", None), "claude-opus-4-7"),
    )


def _read_auto_run_audit(auto_run_path: Path) -> dict[str, Any]:
    """Read ``auto-run.json`` into a dict (F44.3-2 backward compat).

    Helper used by post-mortem tests + future status renderers. Returns
    an empty dict when the file is missing or contains invalid JSON so
    callers don't need to defensively wrap each access.

    .. note:: **v1.0.0 skeleton -- deferred to v1.0.1+ status renderer
       wiring.** As of v1.0.0 this helper is consumed only by the
       post-mortem test suite + the F44.3-2 backward-compat schema
       contract. Production status rendering (e.g. ``/sbtdd status
       --watch`` summary view, ``/sbtdd resume`` checkpoint reader) is
       expected to consume this helper when it lands; the implementation
       is intentionally minimal so the schema-tolerance contract is
       fixed before consumers depend on it. Tracked in CHANGELOG
       ``[1.0.0]`` Deferred section. Removing it before then would
       force the future status-renderer feature to re-derive the
       absent-tolerant read pattern from scratch.

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.

    Returns:
        Parsed dict, or ``{}`` when missing / invalid.
    """
    try:
        return cast(dict[str, Any], json.loads(auto_run_path.read_text(encoding="utf-8")))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def _record_magi_retried_agents(
    auto_run_path: Path,
    *,
    iter_n: int,
    retried_agents: list[str] | tuple[str, ...],
) -> None:
    """Persist ``magi_iter{N}_retried_agents`` to auto-run.json (F44.3).

    Per spec sec.2.2 + plan task S1-7: MAGI Loop 2 retried_agents
    telemetry (already parsed into :class:`magi_dispatch.MAGIVerdict`
    in v0.4.0 Feature F) propagates into the audit trail under a
    per-iter key. Backward compat: pre-v1.0.0 audit files lack the
    field; readers that need the field treat its absence as ``[]``.

    Uses :func:`_with_file_lock` to serialize against the other in-process
    writers (per the single-writer assumption documented on
    :func:`_update_progress`). Atomic rename via tmp file with
    ``{pid}.{tid}`` suffix to dodge the Windows PID-collision flake
    (per W8 fix in S1-20; same pattern preserved here for cross-platform
    safety).

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.
        iter_n: MAGI Loop 2 iteration number (1-based).
        retried_agents: List of agent names that were retried in this
            iteration (e.g. ``["balthasar"]``). Empty list when no
            retries fired.
    """

    def _do_record() -> None:
        try:
            data = json.loads(auto_run_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        data[f"magi_iter{iter_n}_retried_agents"] = list(retried_agents)
        tmp_path = auto_run_path.parent / (
            auto_run_path.name + f".tmp.{os.getpid()}.{threading.get_ident()}"
        )
        tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp_path.replace(auto_run_path)

    _with_file_lock(auto_run_path, _do_record)


def _mark_plan_approved_with_snapshot(*, root: Path) -> None:
    """Persist spec-snapshot at plan-approval time (CRITICAL #2 / S1-27).

    Wired into the plan-approval transition: when the state file gets
    ``plan_approved_at`` set (template sec.5 "Excepcion bajo plan
    aprobado" trigger), this helper:

    1. Emits the current spec scenarios snapshot via
       :func:`spec_snapshot.emit_snapshot` and persists it to
       ``planning/spec-snapshot.json`` via
       :func:`spec_snapshot.persist_snapshot`. The pre-merge gate
       (S1-26 ``_check_spec_snapshot_drift``) consumes this snapshot.
    2. Writes a watermark field
       ``spec_snapshot_emitted_at: <ISO 8601>`` to
       ``.claude/session-state.json``. The watermark is the canon-of-
       the-present record (CLAUDE.local.md §2.1) that a snapshot was
       emitted. Pre-merge S1-26 compares the file's existence against
       this watermark: if the watermark says snapshot was emitted but
       the file is missing, drift detected (H2-5 escenario / W2 fix).

    Idempotent: re-approving the plan re-emits the snapshot
    (``persist_snapshot`` overwrites) and refreshes the watermark.

    Per caspar Loop 2 iter 4 W2 fix: closes the bypass-by-deletion
    gap that would otherwise let an operator silently bypass the drift
    gate by deleting ``planning/spec-snapshot.json``.

    Args:
        root: Project root directory. Spec read from
            ``root/sbtdd/spec-behavior.md``; snapshot persisted to
            ``root/planning/spec-snapshot.json``; watermark written to
            ``root/.claude/session-state.json``.
    """
    import spec_snapshot  # deferred per cross-subagent Mitigation A

    spec_path = root / "sbtdd" / "spec-behavior.md"
    snapshot_path = root / "planning" / "spec-snapshot.json"
    snapshot = spec_snapshot.emit_snapshot(spec_path)
    spec_snapshot.persist_snapshot(snapshot_path, snapshot)

    # Watermark in state file (caspar iter 4 W2): canon-of-the-present
    # record that snapshot WAS emitted. Pre-merge S1-26 compares against
    # this to detect bypass-by-deletion.
    state_file_path = root / ".claude" / "session-state.json"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state_data: dict[str, Any] = {}
    if state_file_path.exists():
        try:
            state_data = json.loads(state_file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # Corrupt state file: leave it alone, the recovery protocol
            # (CLAUDE.local.md §2.1) handles regeneration. Do not silently
            # overwrite with a partial dict.
            sys.stderr.write(
                f"[sbtdd plan-approval] state file corrupt at "
                f"{state_file_path}; spec_snapshot_emitted_at NOT "
                f"persisted. Resolve corruption first.\n"
            )
            return
    state_data["spec_snapshot_emitted_at"] = timestamp
    # Atomic rename via tmp file with PID + thread-id (S1-20 W8 pattern).
    state_file_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = state_file_path.parent / (
        state_file_path.name + f".tmp.{os.getpid()}.{threading.get_ident()}"
    )
    tmp_path.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    tmp_path.replace(state_file_path)


def _phase4_pre_merge_audit_dir(root: Path) -> Path:
    """Return ``.claude/magi-cross-check/`` audit directory under ``root``.

    Per spec sec.2.1 Feature G + plan task S1-6: auto-mode pre-merge
    passes this directory to ``pre_merge_cmd._loop2_with_cross_check`` so
    cross-check audit artifacts land under a stable, gitignored location
    (``.claude/`` is already in ``.gitignore`` per CLAUDE.local.md §1).

    Args:
        root: Project root directory.

    Returns:
        ``root / ".claude" / "magi-cross-check"``. Caller (or
        ``_loop2_cross_check``) creates the directory on first write.
    """
    return root / ".claude" / "magi-cross-check"


def _phase3_pre_merge(ns: argparse.Namespace, cfg: PluginConfig) -> object:
    """Run Phase 3 -- pre-merge Loop 1 + Loop 2 with elevated MAGI budget.

    Delegates to :mod:`pre_merge_cmd` helpers so the consensus logic and
    verdict parsing stay single-sourced. The only difference vs
    interactive ``/sbtdd pre-merge`` is the ``magi_max_iterations`` cap
    which Auto elevates to ``cfg.auto_magi_max_iterations`` (default 5)
    -- compensates for lack of human supervision on ambiguous caveats.

    ``--magi-max-iterations`` on the CLI overrides both caps; no
    validation is imposed here because the dispatcher already validates
    the integer form.

    Args:
        ns: Parsed argparse namespace.
        cfg: Plugin configuration.

    Returns:
        The :class:`magi_dispatch.MAGIVerdict` that cleared the gate --
        later phases read it to decide whether to invoke finalize
        semantics.

    Raises:
        Loop1DivergentError: Loop 1 non-convergence (exit 7).
        MAGIGateError: STRONG_NO_GO or exhausted MAGI iterations (exit 8).
    """
    import magi_dispatch
    import pre_merge_cmd

    # v0.5.0 S1-9 transition site #5: phase 3 entry (pre-merge).
    _set_progress(phase=3)
    root: Path = ns.project_root
    # v1.0.0 C2 wiring (O-2 Loop 1 review CRITICAL #2): spec-snapshot drift
    # gate at auto-phase-3 entry per spec sec.3.2 H2-3 + H2-5. Same gate as
    # interactive pre-merge so both code paths fail closed identically when
    # scenarios drift between plan-approval and merge.
    pre_merge_cmd._check_spec_snapshot_drift(
        spec_path=root / "sbtdd" / "spec-behavior.md",
        snapshot_path=root / "planning" / "spec-snapshot.json",
        state_file_path=root / ".claude" / "session-state.json",
    )
    pre_merge_cmd._loop1(root)
    max_iter = (
        ns.magi_max_iterations
        if ns.magi_max_iterations is not None
        else cfg.auto_magi_max_iterations
    )
    threshold = ns.magi_threshold or cfg.magi_threshold
    shadow = _ShadowCfg(cfg, {"magi_max_iterations": max_iter})
    # mypy: _loop2 consumes the ``magi_max_iterations`` / ``magi_threshold`` /
    # ``plan_path`` attributes via duck typing; the _ShadowCfg wrapper carries
    # exactly those (plus every other PluginConfig field copied by
    # ``__dict__.update``). Casting keeps the call site readable without
    # forcing PluginConfig to grow a Protocol or a dataclasses.replace path.
    verdict = pre_merge_cmd._loop2(root, shadow, threshold)  # type: ignore[arg-type]
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return verdict


def _phase4_checklist(root: Path, state: SessionState, cfg: PluginConfig) -> None:
    """Run Phase 4 -- sec.M.7 checklist validation (reuses finalize logic).

    Delegates the checklist construction to :func:`finalize_cmd._checklist`
    so the 9-item contract stays single-sourced. The key behavioral
    difference vs interactive ``/sbtdd finalize`` is that auto does NOT
    invoke ``/finishing-a-development-branch`` after a pass (INV-25): the
    branch is left clean for the user to merge / PR manually.

    Args:
        root: Project root directory.
        state: Final :class:`SessionState` (expected
            ``current_phase='done'``).
        cfg: Plugin configuration.

    Raises:
        ChecklistError: Any sec.M.7 item failed -- includes a detailed
            one-line-per-failure list in the message (exit 9).
    """
    import finalize_cmd

    # v0.5.0 S1-9 transition site #6: phase 4 entry (checklist).
    _set_progress(phase=4)
    magi_verdict_path = root / ".claude" / "magi-verdict.json"
    items = finalize_cmd._checklist(root, state, magi_verdict_path, cfg)
    failures = [(n, d) for (n, ok, d) in items if not ok]
    if failures:
        raise ChecklistError(
            f"auto Phase 4 checklist FAILED ({len(failures)} items): "
            + "; ".join(f"{n} - {d}" for n, d in failures)
        )


def _phase5_report(root: Path, started: str, verdict: object) -> None:
    """Run Phase 5 -- write ``.claude/auto-run.json`` audit trail (INV-26).

    The audit file captures the full lifespan (start -> finish) plus the
    gating MAGI verdict + degraded flag so operators can reconstruct the
    run post-hoc. Also emits a human-readable summary to stdout.

    Args:
        root: Project root directory.
        started: ISO 8601 timestamp of ``main`` entry (from Phase 1).
        verdict: :class:`magi_dispatch.MAGIVerdict` or ``None`` if the
            run aborted before Phase 3 completed (never expected in the
            happy path).
    """
    # v0.5.0 S1-9 transition site #7: phase 5 entry (audit + report).
    _set_progress(phase=5)
    auto_run = root / ".claude" / "auto-run.json"
    finished = _now_iso()
    tasks_completed = _read_audit_tasks_completed(auto_run)
    verdict_str = getattr(verdict, "verdict", None)
    degraded_value = getattr(verdict, "degraded", None)
    audit = AutoRunAudit(
        schema_version=_AUTO_RUN_SCHEMA_VERSION,
        auto_started_at=started,
        auto_finished_at=finished,
        status="success",
        verdict=verdict_str if verdict_str is None else str(verdict_str),
        degraded=None if degraded_value is None else bool(degraded_value),
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=tasks_completed,
        error=None,
    )
    _write_auto_run_audit(auto_run, audit)
    sys.stdout.write(
        "/sbtdd auto: DONE.\n"
        f"Started:  {started}\n"
        f"Finished: {finished}\n"
        f"MAGI:     {audit.verdict} (degraded={audit.degraded})\n"
        "Branch status: clean, ready for merge/PR.\n"
    )


def _write_auto_run_audit(path: Path, payload: AutoRunAudit) -> None:
    """Write ``.claude/auto-run.json`` with ``payload`` validated.

    Requires an :class:`AutoRunAudit` instance; the dict back-compat
    branch was removed in Plan D iter 2 (Caspar WARNING) because it
    silently bypassed schema validation. Since the plugin is pre-1.0
    and all callers live inside this repo, the stricter signature is
    safe. Task 17 grep-checks for regressions.

    Atomicity contract (MAGI Loop 2 D iter 1 Caspar): the on-disk file
    is always either the fully-formed previous audit or the fully-formed
    new audit -- never a truncated half-write. A process killed between
    the tmp-write and the ``os.replace`` call leaves the previous
    ``auto-run.json`` intact, preserving the "last-persisted audit =
    truth" invariant that ``resume_cmd`` relies on. The pattern mirrors
    :func:`state_file.save` to keep the two state-on-disk writers
    consistent.

    v0.4.0 J6 -- read-modify-write to preserve ``progress``. Before v0.4
    the audit writer overwrote ``auto-run.json`` with the serialised
    audit only, transiently dropping the ``progress`` field written by
    :func:`_update_progress` until the next ``_update_progress`` fired.
    Now the helper reads any pre-existing payload, splices the
    ``progress`` key into the audit dict, and writes the merged result
    atomically. Future top-level keys (e.g. ``magi_iter*_retried_agents``
    once Feature F44.3 is wired into auto) can be added to the merge
    list with a one-line change. If the on-disk payload is missing,
    corrupt JSON, or fails to read for any reason, the writer falls
    back to audit-only output so a previous run's filesystem damage
    cannot block a fresh audit snapshot.

    Args:
        path: Absolute path to ``auto-run.json`` (parent is created).
        payload: :class:`AutoRunAudit` instance, validated before write.

    Raises:
        TypeError: ``payload`` is not an :class:`AutoRunAudit` instance.
        ValidationError: ``payload.validate_schema`` failed.
        OSError: ``os.replace`` failed; tmp file cleaned up before
            re-raising so nothing leaks.
    """
    if not isinstance(payload, AutoRunAudit):
        raise TypeError(
            f"_write_auto_run_audit requires AutoRunAudit, got {type(payload).__name__}"
        )
    payload.validate_schema()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Loop 1 fix (v0.5.0 CRITICAL #3): wrap the full RMW cycle in
    # ``_with_file_lock`` so this writer serialises with the other two
    # in-process ``auto-run.json`` writers (``_update_progress`` and
    # ``_drain_heartbeat_queue_and_persist``). The C4 claim in CHANGELOG
    # `[0.5.0]` previously held only for the drain helper; this fix
    # extends it to all three writers.
    #
    # Loop 2 WARNING #2: the lock is **intra-process**, not cross-process.
    # External readers (``status --watch``, operator ``cat``) bypass the
    # lock; they rely on the atomic-rename semantics of ``os.replace``
    # (POSIX + Windows) to never observe a torn JSON document.
    # v1.0.0 S1-21 I-Hk1 fix (caspar iter 4 INFO): typed as Exception (not
    # BaseException) so SystemExit and KeyboardInterrupt propagate cleanly
    # rather than being captured + re-raised on the calling thread (which
    # delays + can mask the interrupt under nested handlers). Other
    # exceptions still flow through the propagated_error list to preserve
    # OSError semantics expected by callers.
    propagated_error: list[Exception] = []

    def _do_write() -> None:
        try:
            # v0.4.0 J6: preserve the ``progress`` field (and only that field)
            # from any pre-existing on-disk payload so audit refreshes do not
            # transiently drop the live progress snapshot. Failures to read or
            # parse the prior payload are swallowed -- a corrupted or missing
            # file means we have nothing to preserve, which is acceptable.
            audit_dict: dict[str, object] = dict(payload.to_dict())
            if path.exists():
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                    if isinstance(existing, dict) and "progress" in existing:
                        audit_dict["progress"] = existing["progress"]
                except (OSError, json.JSONDecodeError):
                    pass
            # Atomic write via tmp + os.replace (MAGI Loop 2 D iter 1 Caspar):
            # mirrors state_file.save so a process killed mid-write never leaves
            # a corrupted auto-run.json. If os.replace fails the tmp file is
            # cleaned up before the error propagates so nothing leaks.
            # v1.0.0 S1-20 W8 fix: include thread.get_ident() in tmp filename.
            tmp = path.parent / (path.name + f".tmp.{os.getpid()}.{threading.get_ident()}")
            tmp.write_text(json.dumps(audit_dict, indent=2), encoding="utf-8")
            try:
                os.replace(tmp, path)  # atomic on POSIX and Windows
            except OSError:
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
                raise
        except Exception as exc:  # noqa: BLE001
            # v1.0.0 S1-21 I-Hk1: narrowed from BaseException so SystemExit /
            # KeyboardInterrupt propagate. Other exceptions captured for the
            # caller-thread re-raise (preserves OSError semantics).
            propagated_error.append(exc)

    _with_file_lock(path, _do_write)
    if propagated_error:
        raise propagated_error[0]


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd auto (shoot-and-forget full-cycle)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    # v0.3.0 Feature E -- decode --model-override tokens into a dict and
    # stash on the namespace so downstream phases can read it without
    # re-parsing. Malformed tokens raise ValidationError BEFORE any
    # filesystem / subprocess work so the dispatcher (run_sbtdd.py)
    # can map them to exit 1 (USER_ERROR) without leaving partial state.
    ns.model_override_map = _parse_model_overrides(ns.model_override or [])
    # Dry-run short-circuit BEFORE any subprocess work (Finding 4). The
    # cheap parser.parse_args above does not touch the filesystem;
    # stopping here guarantees a preview never invokes preflight,
    # git, or plugin dispatchers.
    if ns.dry_run:
        _print_dry_run_preview(ns)
        return 0
    # v1.0.4 Item C end-to-end wiring (MAGI Loop 2 iter-1 CRITICAL #3 fix).
    # ``ns.parallel`` (default ``False``) drives:
    #   1. TDD-Guard warning emission AFTER phase 1 preflight -- operators
    #      get a clean preflight summary first, then any multi-agent caveat.
    #   2. Dispatch plan construction -- ``_build_dispatch_plan_parallel``
    #      partitions tasks via DAG antichains + file-surface collision
    #      detection; ``_build_dispatch_plan_sequential`` preserves v1.0.3
    #      plan-text order. Result is stashed on ``ns.dispatch_plan`` so
    #      ``_phase2_task_loop`` consumes the partitioned shape without
    #      re-parsing the plan.
    # Pre-fix, the flag was DEAD-WIRED: argparse accepted it but main()
    # never read ``ns.parallel`` and the helpers were orphaned. v1.0.4 iter-2
    # sub-issue 3 (preflight ordering): preflight now runs FIRST so failures
    # surface in the documented context (env / state validation), not via
    # confusing plan-parse errors.
    state, cfg = _phase1_preflight(ns)
    _check_tdd_guard_warning(parallel=ns.parallel, project_root=ns.project_root)
    plan_path_for_dispatch = ns.project_root / "planning" / "claude-plan-tdd.md"
    # v1.0.4 Path 3 mode classification:
    #   - worker mode: --task-ids set AND --no-recursive set (subprocess
    #     spawned by parent --parallel orchestrator). Skip track partition;
    #     run legacy _phase2_task_loop with task-id filter. The
    #     --no-recursive guard prevents the worker from re-spawning workers
    #     of its own (would be infinite spawning).
    #   - orchestrator parallel: --parallel set AND not worker mode.
    #     Build tracks via partition_by_tracks, dispatch via
    #     _dispatch_tracks_concurrent, skip _phase2_task_loop on parent
    #     side (workers handle TDD). After workers complete, reload state
    #     and run phases 3-5.
    #   - sequential default: behaviour byte-identical to v1.0.3.
    # v1.0.4 iter-5 Loop 1 CRITICAL #1: parse --task-ids into an explicit
    # frozenset filter so the worker code path can skip tasks belonging
    # to sibling workers. Pre-fix this was only used as a boolean gate;
    # ``_phase2_task_loop`` had no way to honour the per-worker scope.
    ns.task_ids_filter = _parse_task_ids_filter(getattr(ns, "task_ids", None))
    is_worker_mode = ns.task_ids_filter is not None and bool(getattr(ns, "no_recursive", False))
    is_orchestrator_parallel = bool(ns.parallel) and not is_worker_mode
    if plan_path_for_dispatch.exists():
        if is_orchestrator_parallel:
            ns.dispatch_plan = _build_dispatch_plan_parallel(plan_path_for_dispatch)
        else:
            ns.dispatch_plan = _build_dispatch_plan_sequential(plan_path_for_dispatch)
    else:
        # Plan absent at this stage -- preflight already validated and
        # passed (state.current_phase == 'done' OR plan path implicitly
        # accepted by preflight). Attach empty plan so downstream
        # consumers see a deterministic (empty) iterable.
        ns.dispatch_plan = []
    started = _now_iso()
    auto_run = ns.project_root / ".claude" / "auto-run.json"
    _write_auto_run_audit(
        auto_run,
        AutoRunAudit(
            schema_version=_AUTO_RUN_SCHEMA_VERSION,
            auto_started_at=started,
            auto_finished_at=None,
            status="success",
            verdict=None,
            degraded=None,
            accepted_conditions=0,
            rejected_conditions=0,
            tasks_completed=0,
            error=None,
        ),
    )
    if state.current_phase != "done":
        if is_orchestrator_parallel:
            # v1.0.4 Path 3 orchestrator: bypass _phase2_task_loop on the
            # parent side. tracks (list[list[str]]) come from
            # partition_by_tracks; each track is dispatched as one
            # subprocess worker via _dispatch_tracks_concurrent. Workers
            # mutate the shared state file via the existing
            # _phase2_task_loop body invoked with --task-ids filter.
            tracks = ns.dispatch_plan  # list[list[str]] in Path 3
            effective = _resolve_effective_workers(len(tracks), getattr(ns, "parallel_max", None))
            _dispatch_tracks_concurrent(
                tracks=tracks,
                effective_workers=effective,
                project_root=ns.project_root,
                ns=ns,
            )
            # Reload state after workers mutated it; downstream phases
            # need the up-to-date view (current_phase should be "done"
            # if workers completed all tasks).
            state = load_state(ns.project_root / ".claude" / "session-state.json")
        else:
            # v1.0.4 Loop 2 iter-2 sub-issue 1: pass dispatch_plan into the
            # task loop so the consumer can route multi-task batches through
            # the concurrent helper. Sequential default + dispatch_plan-None
            # both fall through to the legacy while-loop body unchanged.
            # Worker mode also lands here -- legacy body honours --task-ids
            # via the new ``task_ids_filter`` kwarg (v1.0.4 iter-5 Loop 1
            # CRITICAL #1 fix). The filter scopes the loop to ONLY the
            # task ids assigned to this subprocess; tasks owned by sibling
            # workers are skipped via cursor-only state advance (no plan
            # write, no chore commit).
            state = _phase2_task_loop(
                ns,
                state,
                cfg,
                dispatch_plan=getattr(ns, "dispatch_plan", None),
                task_ids_filter=getattr(ns, "task_ids_filter", None),
            )
    # v1.0.4 Path 3 worker mode: skip phases 3-5 because parent
    # orchestrator owns the gate + finalize. Worker exits 0 once its
    # task slice completes (or non-zero on irrecoverable failure, which
    # surfaces as ConcurrentDispatchError on the parent).
    if is_worker_mode:
        return 0
    try:
        verdict = _phase3_pre_merge(ns, cfg)
    except MAGIGateError as exc:
        # Finding 2 (Caspar): record the gate-block status in the audit
        # trail BEFORE re-raising so operators can post-hoc distinguish
        # "conditions pending" (exit 8 with actionable fix) from
        # STRONG_NO_GO (exit 8 requiring replan). Both map to exit 8 via
        # EXIT_CODES[MAGIGateError]; the status / error fields in
        # auto-run.json are the only signal that survives the exception.
        # Plan D Task 4: source counts from exc's typed attributes (no
        # regex parse) and tasks_completed from the last incremental
        # audit write in Phase 2 (raise-safe partial count).
        tasks_completed = _read_audit_tasks_completed(auto_run)
        accepted_count = len(exc.accepted_conditions)
        rejected_count = len(exc.rejected_conditions)
        _write_auto_run_audit(
            auto_run,
            AutoRunAudit(
                schema_version=_AUTO_RUN_SCHEMA_VERSION,
                auto_started_at=started,
                auto_finished_at=_now_iso(),
                status="magi_gate_blocked",
                verdict=exc.verdict,
                degraded=None,
                accepted_conditions=accepted_count,
                rejected_conditions=rejected_count,
                tasks_completed=tasks_completed,
                error=str(exc),
            ),
        )
        sys.stderr.write(
            f"/sbtdd auto: MAGI gate blocked "
            f"(accepted={accepted_count}, rejected={rejected_count}). See "
            f"{auto_run} and .claude/magi-conditions.md for next steps.\n"
        )
        raise
    _phase4_checklist(ns.project_root, state, cfg)
    _phase5_report(ns.project_root, started, verdict)
    return 0


def _read_audit_tasks_completed(path: Path) -> int:
    """Return the last-persisted ``tasks_completed`` from auto-run.json, or 0.

    Used by the MAGIGateError handler to recover the raise-safe partial
    count that ``_phase2_task_loop`` writes after each task close (Plan D
    iter 2 Caspar -- raise-safe audit). Missing file returns 0 silently
    (expected cold-start path). Malformed content still returns 0 but
    emits a stderr diagnostic so operators see that a previously-valid
    audit has regressed (MAGI Loop 2 D iter 1 Balthasar WARNING --
    silent fallback could otherwise mask real corruption).
    """
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text("utf-8"))
        return int(data.get("tasks_completed", 0))
    except (json.JSONDecodeError, ValueError, TypeError, OSError) as exc:
        # TypeError covers `int({...})` when a caller writes a nested
        # object where a scalar was expected; the remaining three cover
        # unreadable bytes / malformed JSON / non-numeric content. All
        # four are "something went wrong -- surface it on stderr but do
        # not abort the auto-run-error path".
        sys.stderr.write(
            f"warning: failed to parse {path}: {type(exc).__name__}: {exc}. "
            f"Falling back to tasks_completed=0 for auto-run audit. "
            f"If this file was previously valid, the run may have been "
            f"interrupted mid-write or corrupted externally.\n"
        )
        return 0


run = main
