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

    def __init__(
        self,
        label: str,
        interval_seconds: float = 15.0,
        failures_queue: "queue.Queue[int] | None" = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError(
                f"interval_seconds must be > 0, got {interval_seconds!r}"
            )
        self.label = label
        self.interval_seconds = interval_seconds
        self._failures_queue = failures_queue
        self._failed_writes = 0
        self._stop_event: threading.Event | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "HeartbeatEmitter":
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
        if self._thread is not None:
            self._thread.join(timeout=2.0)
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
        """Format + write a single tick to stderr (best-effort)."""
        ctx = get_current_progress()
        line = self._format_tick(ctx)
        try:
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
        except OSError:
            self._failed_writes += 1

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """Render elapsed seconds as ``<min>m<sec>s`` (clamped to >= 0)."""
        mins, secs = divmod(int(max(seconds, 0)), 60)
        return f"{mins}m{secs}s"

    def _format_tick(self, ctx: ProgressContext) -> str:
        """Format a tick line per sec.2.1 H5 (full) and H6 (null omission)."""
        parts: list[str] = []
        if ctx.iter_num:
            parts.append(f"iter {ctx.iter_num}")
        parts.append(f"phase {ctx.phase}")
        if ctx.task_index is not None and ctx.task_total is not None:
            parts.append(f"task {ctx.task_index}/{ctx.task_total}")
        if ctx.dispatch_label:
            parts.append(f"dispatch={ctx.dispatch_label}")
        if ctx.started_at is not None:
            elapsed_s = (datetime.now(timezone.utc) - ctx.started_at).total_seconds()
            parts.append(f"elapsed={self._format_elapsed(elapsed_s)}")
        return "[sbtdd auto] tick: " + " ".join(parts)
