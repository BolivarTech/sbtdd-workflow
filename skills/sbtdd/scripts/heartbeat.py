#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""HeartbeatEmitter and ProgressContext singleton for v0.5.0 observability.

Concurrency model (PINNED per spec sec.3):

- Module-level ``_current_progress`` reference, protected by
  ``_progress_lock: threading.Lock``.
- Writer (``auto_cmd`` main thread) calls :func:`set_current_progress`.
- Reader (HeartbeatEmitter daemon thread) calls
  :func:`get_current_progress`; operates on the immutable snapshot
  WITHOUT further locking.

The lock is forward-defensive against PEP 703 free-threaded Python and
maintainer drift; the immutable :class:`models.ProgressContext` plus
pointer assignment is correct on current CPython but depends on memory-
model implementation details that the lock approach avoids.
"""

from __future__ import annotations

import queue
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

from models import ProgressContext

_progress_lock = threading.Lock()
_current_progress: ProgressContext = ProgressContext()


def get_current_progress() -> ProgressContext:
    """Return the current ProgressContext singleton (lock-protected)."""
    with _progress_lock:
        return _current_progress


def set_current_progress(new_ctx: ProgressContext) -> None:
    """Replace the current ProgressContext singleton (lock-protected)."""
    global _current_progress
    with _progress_lock:
        _current_progress = new_ctx


def reset_current_progress() -> None:
    """Reset the singleton to its default value. Test-only helper."""
    set_current_progress(ProgressContext())


def _reset_zombie_count_for_tests() -> None:
    """Reset the class-level zombie counter. Test-only helper.

    Per sec.13.3 INFO (melchior): the zombie counter is process-global
    mutable state -- tests that exercise the C3 path must reset it to
    avoid order-dependent failures.
    """
    HeartbeatEmitter._zombie_thread_count = 0


class HeartbeatEmitter:
    """Context manager that emits stderr ticks every ``interval_seconds``.

    Wraps long subprocess dispatches (MAGI Loop 2,
    ``/requesting-code-review``, spec-reviewer) so the operator sees
    periodic liveness signals on stderr while the dispatch's own
    stdout/stderr is quiet.

    The full behavior (daemon thread, tick format, queue-based failure
    counter) is added incrementally in S1-4 through S1-7.
    """

    # Class-level zombie counter (Checkpoint 2 iter 3 caspar CRITICAL fix):
    # tracks heartbeat threads that survived ``__exit__``'s 2s join timeout.
    _zombie_thread_count: int = 0

    # C3 (Checkpoint 2 iter 4) hard threshold: when total zombies across the
    # process lifetime reach this value, ``__exit__`` raises ``RuntimeError``
    # after a best-effort fd=2 breadcrumb -- process exit becomes the bound.
    _max_zombie_threads: int = 5

    # C3 sentinel offset persisted via the failures queue: any queued plain
    # ``int`` value >= ``_ZOMBIE_SENTINEL_OFFSET`` indicates "zombie alert"
    # rather than a plain failed-write counter (legacy plain-int protocol).
    # Loop 2 W2+W7 fix: producer emits tagged tuples ``("failed_writes", n)``
    # / ``("zombie", n)``. The drain accepts BOTH protocols (tagged tuples +
    # plain ints) for backward compat with any third-party producer that
    # still emits plain ints.
    _ZOMBIE_SENTINEL_OFFSET: int = 1000

    def __init__(
        self,
        label: str,
        interval_seconds: float = 15.0,
        failures_queue: "queue.Queue[tuple[str, int] | int] | None" = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(f"interval_seconds must be > 0, got {interval_seconds!r}")
        self.label = label
        self.interval_seconds = interval_seconds
        self._failures_queue = failures_queue
        self._failed_writes = 0
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None
        # Loop 2 W4 fix: monotonic clock anchor for elapsed computation.
        # Set in ``__enter__`` so each emitter has its own dispatch start;
        # used by ``_format_tick`` to render ``elapsed=`` immune to
        # wall-clock skew (NTP step). ``None`` until ``__enter__`` fires
        # so direct ``_format_tick`` calls (unit tests with synthetic
        # ProgressContext) fall back to wall-clock from
        # ``ctx.started_at``.
        self._dispatch_started_monotonic: float | None = None

    def __enter__(self) -> "HeartbeatEmitter":
        # Loop 2 W4 fix: anchor monotonic clock BEFORE starting the thread
        # so the first tick already has a valid reference.
        self._dispatch_started_monotonic = time.monotonic()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._tick_loop,
            name=f"heartbeat-{self.label}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        zombie_alert = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            # Per Checkpoint 2 iter 2/3 caspar CRITICAL fix: a thread still
            # alive after the 2s join is blocked on a stderr write (broken
            # pipe + the write call itself blocks). EXPLICIT accounting:
            # increment a class-level ``_zombie_thread_count`` and emit a
            # structured warning to alternate channel (best-effort fd=2
            # write, swallow OSError). The thread is daemonized so process
            # exit collects it; we cannot safely interrupt a blocked syscall
            # without unsafe primitives.
            if self._thread.is_alive():
                HeartbeatEmitter._zombie_thread_count += 1
                zombie_alert = True
                try:
                    import os as _os

                    _os.write(
                        2,
                        (
                            f"[sbtdd auto] WARNING: heartbeat thread blocked at "
                            f"__exit__ for label={self.label!r} (zombie count="
                            f"{HeartbeatEmitter._zombie_thread_count}); "
                            f"daemon=True will GC at process end\n"
                        ).encode(),
                    )
                except OSError:
                    pass
                # C3 fold-in: if zombie count reaches the hard threshold,
                # persist the sentinel via the failures queue (single
                # writer to main thread) and emit a FATAL fd=2
                # breadcrumb. The sentinel is
                # ``_ZOMBIE_SENTINEL_OFFSET + zombie_count`` (>= 1000).
                #
                # INV-32 (Loop 1 fix v0.5.0): __exit__ must NEVER raise.
                # The previous ``raise RuntimeError(...)`` violated INV-32
                # ("Heartbeat thread NEVER blocks/kills auto run") AND
                # swallowed any pending real ``exc`` from the with-block
                # (Python only swallows when __exit__ returns truthy, but
                # raising from __exit__ also masks the original exc on
                # the active stack). Operator visibility is preserved via
                # the queue sentinel + fd=2 breadcrumb; if escalation is
                # needed, it must happen post-dispatch on the main thread.
                if HeartbeatEmitter._zombie_thread_count >= HeartbeatEmitter._max_zombie_threads:
                    if self._failures_queue is not None:
                        try:
                            # Loop 2 W2+W7: tagged tuple replaces +1000 sentinel.
                            self._failures_queue.put_nowait(
                                ("zombie", HeartbeatEmitter._zombie_thread_count)
                            )
                        except queue.Full:
                            pass
                    try:
                        import os as _os

                        _os.write(
                            2,
                            (
                                f"[sbtdd auto] FATAL: heartbeat zombie threshold "
                                f"reached ({HeartbeatEmitter._zombie_thread_count}"
                                f" >= {HeartbeatEmitter._max_zombie_threads})\n"
                            ).encode(),
                        )
                    except OSError:
                        pass
        # Persist a zombie-alert sentinel to the failures queue even before
        # the hard threshold so main-thread monitoring (drain helper) sees
        # the state. Loop 2 W2+W7: tagged tuple replaces +1000 sentinel.
        if zombie_alert and self._failures_queue is not None:
            try:
                self._failures_queue.put_nowait(("zombie", HeartbeatEmitter._zombie_thread_count))
            except queue.Full:
                pass
        # Final flush of failed-writes counter (single-writer rule preserved
        # -- main thread sees the put via queue API). Tagged tuple per
        # Loop 2 W2+W7.
        if self._failures_queue is not None and self._failed_writes > 0:
            try:
                self._failures_queue.put_nowait(("failed_writes", self._failed_writes))
            except queue.Full:
                pass
            try:
                sys.stderr.write(
                    f"[sbtdd auto] heartbeat completed with "
                    f"{self._failed_writes} silent write failures\n"
                )
                sys.stderr.flush()
            except OSError:
                pass
        return None

    def _tick_loop(self) -> None:
        """Emit a stderr tick every interval until ``_stop_event`` is set.

        Per Checkpoint 2 iter 1 caspar fix: check ``_stop_event.is_set()``
        BEFORE each ``_emit_tick`` to avoid the
        daemon-thread-outlives-context-manager race where the thread is
        between ``wait()`` returning (stop signaled) and the next iteration
        starting. Combined with ``Event.wait(timeout)`` (which returns
        immediately when set), this guarantees the thread terminates within
        ``max(interval, time-since-last-emit)`` of ``__exit__`` signal.
        """
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            self._emit_tick()
            if self._stop_event.wait(timeout=self.interval_seconds):
                break

    def _emit_tick(self) -> None:
        """Format + write a single tick to stderr (best-effort).

        On stderr write failure (``OSError``, e.g. broken pipe):
        - First failure: emit one warning breadcrumb (best-effort).
        - Subsequent failures: silent.
        """
        ctx = get_current_progress()
        line = self._format_tick(ctx)
        try:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
        except OSError as exc:
            self._failed_writes += 1
            # Periodic queue report every N=10 increments (incremental
            # persistence to main thread per sec.3 single-writer rule).
            if self._failures_queue is not None and self._failed_writes % 10 == 0:
                try:
                    # Loop 2 W2+W7: tagged tuple replaces plain int.
                    self._failures_queue.put_nowait(("failed_writes", self._failed_writes))
                except queue.Full:
                    pass
            if self._failed_writes == 1:
                try:
                    sys.stderr.write(
                        f"[sbtdd auto] heartbeat write failed (will continue silently): {exc}\n"
                    )
                    sys.stderr.flush()
                except OSError:
                    pass

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """Render elapsed seconds as ``<min>m<sec>s`` (clamped to >= 0)."""
        mins, secs = divmod(int(max(seconds, 0)), 60)
        return f"{mins}m{secs}s"

    def _format_tick(self, ctx: ProgressContext) -> str:
        """Format a tick line per sec.2.1 H5 (full) and H6 (null omission).

        Loop 2 W4 fix: when the emitter is active (``__enter__`` called),
        elapsed is computed from ``time.monotonic() -
        _dispatch_started_monotonic`` -- immune to wall-clock skew (NTP
        step). When the emitter has not entered (e.g. unit tests calling
        ``_format_tick`` directly with a synthetic ProgressContext),
        elapsed falls back to wall-clock derived from ``ctx.started_at``
        so the existing test surface keeps working without dispatch
        lifecycle.
        """
        parts: list[str] = []
        if ctx.iter_num:
            parts.append(f"iter {ctx.iter_num}")
        parts.append(f"phase {ctx.phase}")
        if ctx.task_index is not None and ctx.task_total is not None:
            parts.append(f"task {ctx.task_index}/{ctx.task_total}")
        if ctx.dispatch_label:
            parts.append(f"dispatch={ctx.dispatch_label}")
        if self._dispatch_started_monotonic is not None:
            # Active emitter: monotonic-based elapsed (W4 fix).
            elapsed_s = time.monotonic() - self._dispatch_started_monotonic
            parts.append(f"elapsed={self._format_elapsed(elapsed_s)}")
        elif ctx.started_at is not None:
            # Inactive emitter (test-only path): wall-clock fallback.
            elapsed_s = (datetime.now(timezone.utc) - ctx.started_at).total_seconds()
            parts.append(f"elapsed={self._format_elapsed(elapsed_s)}")
        return "[sbtdd auto] tick: " + " ".join(parts)
