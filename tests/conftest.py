#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Shared pytest fixtures for the sbtdd-workflow test suite.

Per v1.0.0 S1-22 (Loop 2 iter 4 I-Hk3 caspar): the autouse module-state
fixture that drains :mod:`auto_cmd` mutable globals between tests was
promoted from ``tests/test_auto_progress.py`` to this top-level
``tests/conftest.py`` so it applies to ALL test files. Pre-promotion
the fixture only ran for ``test_auto_progress.py``; tests in other
files that exercise auto_cmd state (e.g. ``test_heartbeat.py``,
``test_status_watch.py``) had to duplicate the drain plumbing or risk
order-dependent failures when a prior file's test polluted module-level
state.
"""

from __future__ import annotations

import queue
import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is on sys.path so tests can import the
# plugin modules (auto_cmd, pre_merge_cmd, etc.) directly.
sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))


@pytest.fixture(autouse=True)
def _reset_auto_cmd_module_state():
    """Drain module-level state on :mod:`auto_cmd` between tests.

    Resets:

    - ``_heartbeat_failures_q`` (queue.Queue) -- producers/tests put
      items; drain helpers consume them. A leak across tests would
      shift later assertions.
    - ``_drain_state.last_drain_at`` -- timestamp guard for periodic
      drain skip logic (``_periodic_drain_if_due``).
    - ``_drain_decode_error_emitted`` -- W14 dedup flag for stderr
      breadcrumb.
    - ``_persistence_error_emitted`` -- v1.0.0 W7 dedup flag.
    - ``_observability_swallowed_count`` -- I3 swallowed counter.
    - ``_cross_check_disabled_breadcrumb_emitted`` (on
      :mod:`pre_merge_cmd`) -- v1.0.0 G4 breadcrumb dedup.
    - ``_assert_main_thread`` attribute -- restored if a legacy test
      swapped it via direct mutation (new tests prefer
      ``monkeypatch.setattr`` per W6).

    The fixture runs in setup AND teardown so a mid-run failure cannot
    poison downstream tests.
    """
    # Lazy-import inside the fixture so test collection of unrelated
    # modules (e.g., test_marketplace_manifest.py) is not coupled to
    # auto_cmd's module-load side effects.
    try:
        import auto_cmd
    except ImportError:
        # auto_cmd unavailable in this collection context (rare, e.g.
        # collection-only mode without scripts/ on sys.path); fixture
        # is a no-op.
        yield
        return

    original_assert = auto_cmd._assert_main_thread

    def _drain_all() -> None:
        while not auto_cmd._heartbeat_failures_q.empty():
            try:
                auto_cmd._heartbeat_failures_q.get_nowait()
            except queue.Empty:
                break
        auto_cmd._reset_drain_state_for_tests()
        auto_cmd._reset_drain_decode_error_emitted_for_tests()
        auto_cmd._reset_observability_swallowed_count_for_tests()
        if hasattr(auto_cmd, "_reset_persistence_error_emitted_for_tests"):
            auto_cmd._reset_persistence_error_emitted_for_tests()
        # v1.0.0 G4 breadcrumb dedup (pre_merge_cmd).
        try:
            import pre_merge_cmd
        except ImportError:
            return
        if hasattr(pre_merge_cmd, "_reset_cross_check_breadcrumb_for_tests"):
            pre_merge_cmd._reset_cross_check_breadcrumb_for_tests()

    _drain_all()
    try:
        yield
    finally:
        _drain_all()
        auto_cmd._assert_main_thread = original_assert
