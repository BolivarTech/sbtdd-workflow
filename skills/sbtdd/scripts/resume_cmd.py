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


def _decide_delegation(
    state: Any, tree_dirty: bool, runtime: dict[str, bool]
) -> tuple[str | None, list[str]]:
    """Decide which downstream subcommand to invoke based on state snapshot.

    Decision tree (sec.S.5.10):

    - ``current_phase`` in (``red``, ``green``, ``refactor``) + tree
      clean + ``auto-run.json`` present -> ``auto_cmd`` (a previous auto
      run was interrupted mid-cycle; resume it).
    - ``current_phase`` in (``red``, ``green``, ``refactor``) + tree
      clean + no ``auto-run.json`` -> no delegation (manual mode; user
      drives next close-phase themselves).
    - ``current_phase`` in TDD phases + tree dirty ->
      ``uncommitted-resolution`` (decision deferred to Phase 4).
    - ``current_phase == 'done'`` + tree dirty ->
      ``uncommitted-resolution``.
    - ``current_phase == 'done'`` + tree clean + verdict present ->
      ``finalize_cmd``.
    - ``current_phase == 'done'`` + tree clean + no verdict +
      ``auto-run.json`` present -> ``auto_cmd`` (MAGI Loop 2 iter 1
      Finding 9: interrupted auto whose task loop completed; resume
      auto so the elevated MAGI budget and audit trail are honoured).
    - ``current_phase == 'done'`` + tree clean + no verdict +
      no ``auto-run.json`` -> ``pre_merge_cmd`` (manual task loop
      finished; run Loop 1 + Loop 2 interactively).

    Args:
        state: :class:`state_file.SessionState` (duck-typed to the
            ``current_phase`` attribute; ``_FakeState`` in tests also
            satisfies the contract).
        tree_dirty: Whether ``git status --short`` reported non-empty.
        runtime: Mapping with keys ``auto-run.json`` /
            ``magi-verdict.json`` -> bool (present).

    Returns:
        ``(module_name_or_sentinel, extra_args)``. ``module_name`` is
        ``None`` when no delegation is appropriate;
        ``"uncommitted-resolution"`` signals the caller to enter Phase 4.
    """
    if state.current_phase in ("red", "green", "refactor") and not tree_dirty:
        if runtime.get("auto-run.json"):
            return ("auto_cmd", [])
        return (None, [])
    if state.current_phase in ("red", "green", "refactor") and tree_dirty:
        return ("uncommitted-resolution", [])
    if state.current_phase == "done":
        if tree_dirty:
            return ("uncommitted-resolution", [])
        # MAGI Loop 2 iter 1 Finding 9: an auto run that advanced every
        # task to done but died before Loop 2 produced magi-verdict.json
        # MUST resume as auto (elevated budget + auto-run.json audit
        # trail), not as fresh pre-merge (interactive budget, no audit
        # update). The signal is ``auto-run.json`` present alongside a
        # missing verdict. When neither auto-run.json nor verdict
        # exists the user drove the task loop manually; delegate to
        # pre_merge_cmd as before.
        if not runtime.get("magi-verdict.json"):
            if runtime.get("auto-run.json"):
                return ("auto_cmd", [])
            return ("pre_merge_cmd", [])
        return ("finalize_cmd", [])
    return (None, [])


def _delegate(module_name: str, root: Path, extra: list[str]) -> int:
    """Import and invoke ``<module>.main`` with ``--project-root``.

    Uses ``importlib`` so the decision tree does not pull every
    subcommand's transitive dependency chain at resume module import
    time.

    Args:
        module_name: Name of a ``*_cmd`` module (``auto_cmd``,
            ``pre_merge_cmd``, ``finalize_cmd``).
        root: Project root directory passed as ``--project-root``.
        extra: Extra CLI arguments appended after ``--project-root``.

    Returns:
        The ``main``-supplied return code from the delegated subcommand.
    """
    import importlib

    mod = importlib.import_module(module_name)
    rc: int = mod.main(["--project-root", str(root)] + extra)
    return rc


def _resolve_uncommitted(ns: argparse.Namespace, root: Path) -> str:
    """Resolve uncommitted working-tree changes per INV-24.

    Default behavior is CONCRETELY CONSERVATIVE (INV-24): keep user work
    untouched. The only paths that actually call ``git checkout HEAD -- .``
    / ``git clean -fd`` are:

    - ``--discard-uncommitted`` flag set (explicit programmatic escape).
    - Interactive ``R`` response (explicit human confirmation).

    ``--auto`` + dirty tree prints CONTINUE and returns; never destroys
    work silently. If no flag is set and the process is non-interactive
    (e.g. CI), ``input()`` will raise or return empty -- the empty-default
    branch returns CONTINUE.

    ``git clean -fd`` is deliberately used WITHOUT ``-x`` so files in
    ``.gitignore`` (``.venv/``, build artifacts, caches) survive the
    reset. The contract is: "discard uncommitted changes", not "nuke
    everything that isn't in git".

    Args:
        ns: Parsed argparse namespace.
        root: Project root directory.

    Returns:
        One of ``"CONTINUE"``, ``"RESET"``, ``"ABORT"``.
    """
    if ns.discard_uncommitted:
        subprocess_utils.run_with_timeout(
            ["git", "checkout", "HEAD", "--", "."], timeout=30, cwd=str(root)
        )
        subprocess_utils.run_with_timeout(["git", "clean", "-fd"], timeout=30, cwd=str(root))
        sys.stdout.write("Uncommitted work discarded.\n")
        return "RESET"
    if ns.auto:
        sys.stdout.write("CONTINUE (preserving uncommitted work). Next close-phase will decide.\n")
        return "CONTINUE"
    sys.stdout.write("\nUncommitted work detected. Options:\n")
    sys.stdout.write("  [C] Continue - keep uncommitted and resume.\n")
    sys.stdout.write("  [R] Reset    - discard and resume from HEAD.\n")
    sys.stdout.write("  [A] Abort    - exit without changes.\n")
    try:
        choice = (input("Choice [C/R/A]: ") or "C").strip().upper()
    except EOFError:
        choice = "C"
    if choice == "R":
        subprocess_utils.run_with_timeout(
            ["git", "checkout", "HEAD", "--", "."], timeout=30, cwd=str(root)
        )
        subprocess_utils.run_with_timeout(["git", "clean", "-fd"], timeout=30, cwd=str(root))
        return "RESET"
    if choice == "A":
        return "ABORT"
    return "CONTINUE"


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
    report = _report_diagnostic(root)
    _recheck_environment(root)
    module_name, extra = _decide_delegation(
        report["state"], report["tree_dirty"], report["runtime"]
    )
    if module_name is None:
        sys.stdout.write("Nothing to delegate. Run a manual subcommand.\n")
        return 0
    if ns.dry_run:
        sys.stdout.write(f"Would delegate to: {module_name} with args {extra}\n")
        return 0
    if module_name == "uncommitted-resolution":
        action = _resolve_uncommitted(ns, root)
        if action == "ABORT":
            return 130
        # After resolving, re-diagnose and re-decide (tree may now be
        # clean + a fresh decision applies).
        new_report = _report_diagnostic(root)
        module_name, extra = _decide_delegation(
            new_report["state"], new_report["tree_dirty"], new_report["runtime"]
        )
        if module_name is None or module_name == "uncommitted-resolution":
            return 0
        return _delegate(module_name, root, extra)
    return _delegate(module_name, root, extra)


run = main
