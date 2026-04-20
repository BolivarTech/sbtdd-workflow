#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd status - read-only report of state + git + plan + drift (sec.S.5.5).

Exit codes: 0 success, 1 state file corrupt (StateFileError), 3 drift detected.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import subprocess_utils
from drift import detect_drift
from errors import StateFileError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sbtdd status",
        description="Read-only status report of active SBTDD session.",
    )
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def _count_plan_tasks(plan_path: Path) -> tuple[int, int]:
    """Return (completed, total) for task sections in the plan.

    A task section is considered completed when it contains at least one
    ``- [x]`` checkbox and no ``- [ ]`` remaining.
    """
    if not plan_path.exists():
        return (0, 0)
    text = plan_path.read_text(encoding="utf-8")
    task_headers = re.findall(r"^### Task (\S+?):", text, flags=re.MULTILINE)
    total = len(task_headers)
    completed = 0
    sections = re.split(r"^### Task \S+?:", text, flags=re.MULTILINE)
    for section in sections[1:]:
        if "- [ ]" not in section and "- [x]" in section:
            completed += 1
    return (completed, total)


def _read_head_commit(project_root: Path) -> tuple[str, str]:
    """Return (short_sha, subject) of HEAD, or ("-", "-") if unavailable."""
    try:
        result = subprocess_utils.run_with_timeout(
            ["git", "log", "-1", "--format=%h|%s"], timeout=10, cwd=str(project_root)
        )
    except Exception:
        return ("-", "-")
    if result.returncode != 0:
        return ("-", "-")
    parts = result.stdout.strip().split("|", 1)
    return (parts[0], parts[1]) if len(parts) == 2 else ("-", "-")


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        sys.stdout.write(
            "No active SBTDD session (state file missing).\n"
            "Project is in manual mode. Invoke /sbtdd spec to bootstrap a feature.\n"
        )
        return 0
    try:
        state = load_state(state_path)
    except StateFileError as exc:
        sys.stderr.write(f"StateFileError: {exc}\n")
        return 1
    plan_path = root / state.plan_path
    completed, total = _count_plan_tasks(plan_path)
    sha, subject = _read_head_commit(root)
    last_v_at = state.last_verification_at or "null"
    last_v_res = state.last_verification_result or "null"
    sys.stdout.write(
        f"Active task:   {state.current_task_id or 'null'}"
        f" - {state.current_task_title or 'null'}\n"
        f"Active phase:  {state.current_phase}\n"
        f"HEAD commit:   {sha} {subject}\n"
        f"Plan progress: {completed}/{total} tasks [x]\n"
        f"Last verif:    {last_v_at} - {last_v_res}\n"
    )
    # Drift detection wired in Task 3; call always and ignore return for now.
    _ = detect_drift(state_path, plan_path, root)
    return 0


run = main
