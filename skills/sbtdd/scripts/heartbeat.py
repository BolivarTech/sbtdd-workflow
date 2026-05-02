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

import threading

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


# HeartbeatEmitter scaffold; full behavior (thread loop, queue, format)
# is built incrementally in S1-3 through S1-7.
class HeartbeatEmitter:
    """Placeholder; replaced in subsequent v0.5.0 tasks."""
