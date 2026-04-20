#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd resume -- diagnostic wrapper (sec.S.5.10, INV-30).

Recovery path for any SBTDD run interrupted by quota exhaustion, crash,
reboot, or explicit Ctrl+C. The state file + atomic commits form the
checkpoint chain; worst-case loss is uncommitted work in the current
phase only.

Flow (phases):

1. Phase 1 -- diagnostic read: state + git HEAD + working tree + runtime
   artifacts (auto-run.json, magi-verdict.json) are reported to stdout
   WITHOUT mutation.
2. Phase 2 -- dependency + drift re-check (same contract as init's
   pre-flight; runs before any delegation).
3. Phase 3 -- delegation decision tree. Based on state/phase/artifacts,
   choose the downstream subcommand (``auto_cmd`` / ``pre_merge_cmd`` /
   ``finalize_cmd``) or flag uncommitted-resolution.
4. Phase 4 -- uncommitted work resolution with INV-24 conservative
   default (CONTINUE preserves user work; ``--discard-uncommitted`` is
   the explicit escape valve; interactive `R`/`A` also available).

Default behaviour on uncommitted work: CONTINUE. Any destructive action
(git checkout + clean) requires either ``--discard-uncommitted`` or an
explicit ``R`` response in interactive mode.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import subprocess_utils
from config import load_plugin_local
from dependency_check import check_environment
from drift import detect_drift
from errors import DependencyError, DriftError, PreconditionError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``sbtdd resume``."""
    p = argparse.ArgumentParser(prog="sbtdd resume")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument("--auto", action="store_true")
    p.add_argument("--discard-uncommitted", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p


def _report_diagnostic(root: Path) -> dict[str, Any]:
    """Print and return a diagnostic snapshot for the active session.

    Reads three canonical sources -- state file, git HEAD + status, and
    the presence of runtime artifacts (``magi-verdict.json`` /
    ``auto-run.json``) -- and emits a human-readable report to stdout.
    Pure diagnostic: no mutation, no prompts.

    The returned dict feeds into the delegation decision tree (Task 35)
    so the subsequent phases share a single snapshot (avoids races
    between repeated reads in each phase).

    Args:
        root: Project root directory.

    Returns:
        A dict with keys ``state`` (:class:`state_file.SessionState`),
        ``head_sha`` (short SHA or ``"-"`` when HEAD is missing),
        ``tree_dirty`` (bool), ``runtime`` (mapping of artifact basename
        -> bool present).
    """
    state_path = root / ".claude" / "session-state.json"
    state = load_state(state_path)
    head_r = subprocess_utils.run_with_timeout(
        ["git", "log", "-1", "--format=%h|%s"], timeout=10, cwd=str(root)
    )
    raw = head_r.stdout.strip()
    if "|" in raw:
        sha, subject = raw.split("|", 1)
    else:
        sha, subject = ("-", "-")
    status_r = subprocess_utils.run_with_timeout(
        ["git", "status", "--short"], timeout=10, cwd=str(root)
    )
    dirty = status_r.stdout.strip() != ""
    runtime = {
        "magi-verdict.json": (root / ".claude" / "magi-verdict.json").exists(),
        "auto-run.json": (root / ".claude" / "auto-run.json").exists(),
    }
    sys.stdout.write("State file:\n")
    sys.stdout.write(f"  current_task_id:          {state.current_task_id}\n")
    sys.stdout.write(f"  current_task_title:       {state.current_task_title}\n")
    sys.stdout.write(f"  current_phase:            {state.current_phase}\n")
    sys.stdout.write(f"  plan_approved_at:         {state.plan_approved_at}\n")
    sys.stdout.write(f"  phase_started_at_commit:  {state.phase_started_at_commit}\n")
    sys.stdout.write(f"  last_verification_at:     {state.last_verification_at}\n")
    sys.stdout.write(f"  last_verification_result: {state.last_verification_result}\n")
    sys.stdout.write(f"Git HEAD:     {sha} {subject}\n")
    sys.stdout.write(f"Working tree: {'DIRTY' if dirty else 'clean'}\n")
    for art, present in runtime.items():
        sys.stdout.write(f"  {art}: {'present' if present else 'absent'}\n")
    return {"state": state, "head_sha": sha, "tree_dirty": dirty, "runtime": runtime}


def _recheck_environment(root: Path) -> None:
    """Re-run pre-flight + drift detection before delegating.

    Guards against ``resume`` blindly re-delegating to ``auto`` /
    ``pre-merge`` / ``finalize`` when the environment is itself broken.
    Aggregates failures the same way as ``init`` -- no short-circuit.

    Args:
        root: Project root directory.

    Raises:
        DependencyError: Pre-flight reported non-OK.
        DriftError: State vs git vs plan inconsistency detected.
    """
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    report = check_environment(cfg.stack, root, Path.home() / ".claude" / "plugins")
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    state = load_state(root / ".claude" / "session-state.json")
    plan_path = root / state.plan_path
    dr = detect_drift(root / ".claude" / "session-state.json", plan_path, root)
    if dr is not None:
        raise DriftError(
            f"drift at resume: state={dr.state_value}, HEAD={dr.git_value}:, plan={dr.plan_value}"
        )


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd resume (diagnostic + delegation wrapper)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    plugin_local = root / ".claude" / "plugin.local.md"
    if not plugin_local.exists():
        raise PreconditionError(
            f"plugin.local.md not found at {plugin_local}. Run /sbtdd init first."
        )
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        sys.stdout.write(
            "No active SBTDD session to resume.\n"
            "Project is in manual mode. Invoke /sbtdd spec to bootstrap a feature.\n"
        )
        return 0
    _report_diagnostic(root)
    _recheck_environment(root)
    return 0


run = main
