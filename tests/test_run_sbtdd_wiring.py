#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for Milestone C dispatcher wiring in ``run_sbtdd.py``.

Each test verifies that ``SUBCOMMAND_DISPATCH`` routes a given subcomando
to the real ``*_cmd.main`` function, replacing the Milestone B placeholder
handlers. See plan Tasks 37-45 + Task 46 cleanup.
"""

from __future__ import annotations


def test_dispatcher_routes_status_to_status_cmd():
    import run_sbtdd
    import status_cmd

    assert run_sbtdd.SUBCOMMAND_DISPATCH["status"] is status_cmd.main


def test_dispatcher_status_returns_0_with_no_state(tmp_path):
    import run_sbtdd

    rc = run_sbtdd.main(["status", "--project-root", str(tmp_path)])
    assert rc == 0


def test_dispatcher_routes_close_task_to_close_task_cmd():
    import close_task_cmd
    import run_sbtdd

    assert run_sbtdd.SUBCOMMAND_DISPATCH["close-task"] is close_task_cmd.main


def test_dispatcher_routes_close_phase_to_close_phase_cmd():
    import close_phase_cmd
    import run_sbtdd

    assert run_sbtdd.SUBCOMMAND_DISPATCH["close-phase"] is close_phase_cmd.main


def test_dispatcher_routes_init_to_init_cmd():
    import init_cmd
    import run_sbtdd

    assert run_sbtdd.SUBCOMMAND_DISPATCH["init"] is init_cmd.main


def test_dispatcher_routes_spec_to_spec_cmd():
    import run_sbtdd
    import spec_cmd

    assert run_sbtdd.SUBCOMMAND_DISPATCH["spec"] is spec_cmd.main
