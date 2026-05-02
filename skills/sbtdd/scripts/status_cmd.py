#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.1.0
# Date: 2026-05-02
"""/sbtdd status - read-only report of state + git + plan + drift (sec.S.5.5).

Enforces INV-4 (no state file -> manual mode: only init/spec/status operate)
and INV-17 (drift surfaced explicitly, never silenced). Never mutates any
artifact -- status is the diagnostic subcomando.

v0.5.0 adds the ``--watch`` companion mode (sec.2.2, W1-W6) that polls
``.claude/auto-run.json`` and emits a TTY rewrite-line render or one
JSON object per progress change. Helpers live alongside the existing
``main`` function so they can be unit-tested in isolation.

Exit codes: 0 success, 1 state file corrupt (StateFileError), 3 drift
detected, 130 SIGINT during ``--watch``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import subprocess_utils
from drift import detect_drift
from errors import StateFileError, ValidationError
from state_file import load as load_state


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sbtdd status",
        description="Read-only status report of active SBTDD session.",
    )
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    # v0.5.0: --watch companion mode + interval/json flags (sec.2.2 W1-W6).
    p.add_argument(
        "--watch",
        action="store_true",
        help="Live poll of .claude/auto-run.json (W1-W6).",
    )
    p.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Poll interval in seconds (>= 0.1). Only meaningful with --watch.",
    )
    p.add_argument(
        "--json",
        dest="json_mode",
        action="store_true",
        help="Emit JSON per progress change (only with --watch).",
    )
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
    # v0.5.0: --watch dispatches to the live-poll loop and bypasses the
    # one-shot report. The watch loop targets .claude/auto-run.json
    # rather than session-state.json (auto runs vs interactive runs).
    # Look up watch_main on the live module so monkeypatched stubs
    # (in run_sbtdd test harness) take effect.
    if getattr(ns, "watch", False):
        import status_cmd as _self

        return _self.watch_main(
            root / ".claude" / "auto-run.json",
            interval=ns.interval,
            json_mode=ns.json_mode,
        )
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
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is None:
        drift_line = "Drift:         none\n"
    else:
        drift_line = (
            f"Drift:         detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}\n"
            f"               reason: {drift_report.reason}\n"
        )
    sys.stdout.write(
        f"Active task:   {state.current_task_id or 'null'}"
        f" - {state.current_task_title or 'null'}\n"
        f"Active phase:  {state.current_phase}\n"
        f"HEAD commit:   {sha} {subject}\n"
        f"Plan progress: {completed}/{total} tasks [x]\n"
        f"Last verif:    {last_v_at} - {last_v_res}\n"
        f"{drift_line}"
    )
    return 3 if drift_report is not None else 0


run = main


# ---------------------------------------------------------------------------
# v0.5.0 — /sbtdd status --watch helpers (sec.2.2 W1-W6)
# ---------------------------------------------------------------------------


def validate_watch_interval(interval: float) -> None:
    """W6: reject sub-100ms intervals (would spin CPU without operator value).

    Raises:
        ValidationError: When ``interval`` is below the 0.1s floor.
    """
    if interval < 0.1:
        raise ValidationError(f"--interval must be >= 0.1s (sub-100ms spins CPU); got {interval}")


def _watch_render_tty(progress: dict[str, Any]) -> str:
    """W1: format a ProgressContext snapshot for a TTY rewrite-line render."""
    parts: list[str] = []
    if progress.get("iter_num"):
        parts.append(f"iter {progress['iter_num']}")
    parts.append(f"phase {progress.get('phase', 0)}")
    if progress.get("task_index") is not None and progress.get("task_total") is not None:
        parts.append(f"task {progress['task_index']}/{progress['task_total']}")
    if progress.get("dispatch_label"):
        parts.append(f"dispatch={progress['dispatch_label']}")
    return "[sbtdd watch] " + " ".join(parts)


def _watch_loop_once(auto_run_path: Path, *, json_mode: bool) -> int:
    """W3: single-poll cycle. Returns 0 if missing file (operator-friendly).

    Designed to be unit-testable independent of the real poll loop in
    :func:`watch_main`. The full loop reuses these helpers but adds the
    polling cadence and SIGINT handling.
    """
    if not auto_run_path.exists():
        sys.stderr.write("[sbtdd status] no auto run in progress\n")
        return 0
    return 0  # full loop wired in S2-9 (see :func:`watch_main`).


def _read_auto_run_with_retry(
    auto_run_path: Path, *, max_retries: int = 5
) -> dict[str, Any] | None:
    """W4: 5x exponential backoff on JSON parse error.

    Sleep occurs BETWEEN attempts (not after the last one) — total budget
    is 4 sleeps (50+100+200+400ms = 750ms) for 5 attempts. Per Checkpoint
    2 iter 1 melchior fix (no wasted sleep after final failed attempt).
    """
    backoff_schedule = [0.05, 0.1, 0.2, 0.4]  # 4 sleeps between 5 attempts
    for attempt_idx in range(max_retries):
        try:
            data = json.loads(auto_run_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            if attempt_idx < len(backoff_schedule):
                time.sleep(backoff_schedule[attempt_idx])
            continue
        if isinstance(data, dict):
            return data
        return None
    return None


@dataclass
class WatchPollState:
    """W4 slow-poll fallback: track JSON parse failures, adjust interval.

    Critical (Checkpoint 2 iter 1 caspar fix): only triggered by ACTUAL
    JSON parse contention failures (5x retry exhaustion). Idle auto-runs
    that return same data successfully are NOT failures — they keep the
    default poll interval so operators see updates promptly when MAGI
    dispatch ends.
    """

    default_interval: float
    current_interval: float = field(default=0.0)
    consecutive_parse_failures: int = 0
    cap_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.current_interval == 0.0:
            self.current_interval = self.default_interval

    def record_parse_failure(self) -> None:
        """Called ONLY when ``_read_auto_run_with_retry`` returns None."""
        self.consecutive_parse_failures += 1
        if self.consecutive_parse_failures >= 3:
            self.current_interval = min(self.current_interval * 2, self.cap_seconds)

    def record_parse_success(self) -> None:
        """Called when JSON parsed (even if progress dict equals previous)."""
        if self.current_interval > self.default_interval:
            self.current_interval = self.default_interval
        self.consecutive_parse_failures = 0


def _watch_render_one(
    auto_run_path: Path,
    *,
    json_mode: bool,
    last_progress: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Single-poll render. Returns the new progress dict or last_progress."""
    data = _read_auto_run_with_retry(auto_run_path, max_retries=5)
    if data is None:
        return last_progress
    progress = data.get("progress", {}) or {}
    if progress != last_progress:
        if json_mode:
            sys.stdout.write(json.dumps({"timestamp": time.time(), "progress": progress}) + "\n")
        else:
            sys.stdout.write("\r" + _watch_render_tty(progress) + " ")
        sys.stdout.flush()
    return progress


def watch_main(
    auto_run_path: Path,
    *,
    interval: float,
    json_mode: bool,
) -> int:
    """W1-W6: full ``status --watch`` poll loop.

    Distinguishes (a) idle (parse success, same data), (b) contention
    (parse failure after 5x retries), and (c) file-disappearance (path
    stops existing mid-poll, e.g. auto-run finished + cleaned up). Per
    Checkpoint 2 iter 1 + iter 2 caspar fixes.
    """
    validate_watch_interval(interval)
    if not auto_run_path.exists():
        sys.stderr.write("[sbtdd status] no auto run in progress\n")
        return 0
    state = WatchPollState(default_interval=interval)
    last_progress: dict[str, Any] | None = None
    try:
        while True:
            # Re-check existence each poll: file may disappear mid-watch
            # (auto-run completed + .claude/ cleanup). Distinguish from
            # contention.
            if not auto_run_path.exists():
                sys.stderr.write(
                    "\n[sbtdd status] auto run ended (auto-run.json no longer present)\n"
                )
                sys.stderr.flush()
                return 0
            new_progress = _watch_render_one(
                auto_run_path, json_mode=json_mode, last_progress=last_progress
            )
            data = _read_auto_run_with_retry(auto_run_path, max_retries=5)
            if data is None:
                state.record_parse_failure()
                # Per Checkpoint 2 iter 3 caspar W9 fix: align breadcrumb
                # cadence with slow-poll trigger threshold (3) rather than 5.
                if state.consecutive_parse_failures % 3 == 0:
                    sys.stderr.write(
                        f"[sbtdd status] contention: JSON parse failed after "
                        f"5 retries (cumulative={state.consecutive_parse_failures})\n"
                    )
                    sys.stderr.flush()
            else:
                state.record_parse_success()
                last_progress = new_progress
            time.sleep(state.current_interval)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return 130
