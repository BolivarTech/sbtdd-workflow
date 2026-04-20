#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Pre-flight dependency validator for /sbtdd init (sec.S.1.3, sec.S.5.1.1).

Seven mandatory checks: Python >= 3.9, git, tdd-guard (+ writable data dir),
superpowers plugin discovery, magi plugin discovery, stack toolchain
(Rust/Python/C++), git working tree. Failures accumulate; check_environment
never short-circuits. Caller (init, status) decides abort vs report-only.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import subprocess_utils

#: Allowed values for DependencyCheck.status (sec.S.5.1.1 reporte formato).
VALID_STATUSES: tuple[str, ...] = ("OK", "MISSING", "BROKEN")


@dataclass(frozen=True)
class DependencyCheck:
    """Result of a single dependency check (sec.S.5.1.1 reporte estructurado)."""

    name: str
    status: str  # one of VALID_STATUSES
    detail: str
    remediation: str | None


@dataclass(frozen=True)
class DependencyReport:
    """Aggregated result of check_environment (sec.S.5.1.1)."""

    checks: tuple[DependencyCheck, ...]

    def failed(self) -> tuple[DependencyCheck, ...]:
        """Return only the checks whose status is not OK."""
        return tuple(c for c in self.checks if c.status != "OK")

    def ok(self) -> bool:
        """Return True iff every check has status OK."""
        return all(c.status == "OK" for c in self.checks)

    def format_report(self) -> str:
        """Format failures as the canonical sec.S.5.1.1 report, or empty string.

        Returns:
            Multi-line human-readable report when any check failed; the empty
            string when every check is OK (caller should not print anything).
        """
        failures = self.failed()
        if not failures:
            return ""
        lines = [
            "SBTDD init: environment check FAILED.",
            "",
            "The following dependencies are missing or not operational. Install all of",
            "them and re-run /sbtdd init:",
            "",
        ]
        for chk in failures:
            lines.append(f"  [{chk.status}]  {chk.name}")
            if chk.detail:
                lines.append(f"             {chk.detail}")
            if chk.remediation:
                lines.append(f"             Install: {chk.remediation}")
            lines.append("")
        lines.append(f"{len(failures)} issues found. /sbtdd init aborted. Exit code 2.")
        lines.append("No files were created in the project.")
        return "\n".join(lines)


def check_python() -> DependencyCheck:
    """Verify Python >= 3.9 (sec.S.1.3 item 1)."""
    v = sys.version_info
    if v >= (3, 9):
        return DependencyCheck(
            name="python",
            status="OK",
            detail=f"Python {v.major}.{v.minor}.{v.micro}",
            remediation=None,
        )
    return DependencyCheck(
        name="python",
        status="BROKEN",
        detail=f"Python {v.major}.{v.minor}.{v.micro} < 3.9 required",
        remediation="Install Python 3.9+ from python.org",
    )


def check_git() -> DependencyCheck:
    """Verify git binary is in PATH and responds (sec.S.1.3 item 2)."""
    if shutil.which("git") is None:
        return DependencyCheck(
            name="git",
            status="MISSING",
            detail="Binary not found in PATH.",
            remediation="https://git-scm.com/downloads",
        )
    try:
        result = subprocess_utils.run_with_timeout(["git", "--version"], timeout=5)
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="git",
            status="BROKEN",
            detail="git --version timed out after 5s",
            remediation="Check PATH / reinstall git",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="git",
            status="BROKEN",
            detail=f"git --version returncode={result.returncode}",
            remediation="Reinstall git",
        )
    return DependencyCheck(
        name="git",
        status="OK",
        detail=result.stdout.strip(),
        remediation=None,
    )


def check_tdd_guard_binary() -> DependencyCheck:
    """Verify tdd-guard binary is in PATH and responds (sec.S.1.3 item 3)."""
    if shutil.which("tdd-guard") is None:
        return DependencyCheck(
            name="tdd-guard",
            status="MISSING",
            detail="Binary not found in PATH.",
            remediation="npm install -g @nizos/tdd-guard",
        )
    try:
        result = subprocess_utils.run_with_timeout(["tdd-guard", "--version"], timeout=5)
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="tdd-guard",
            status="BROKEN",
            detail="tdd-guard --version timed out after 5s",
            remediation="Reinstall tdd-guard",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="tdd-guard",
            status="BROKEN",
            detail=f"tdd-guard --version returncode={result.returncode}",
            remediation="npm install -g @nizos/tdd-guard",
        )
    return DependencyCheck(
        name="tdd-guard",
        status="OK",
        detail=result.stdout.strip() or "tdd-guard present",
        remediation=None,
    )


def check_tdd_guard_data_dir(project_root: Path) -> DependencyCheck:
    """Verify .claude/tdd-guard/data/ is creatable and writable (sec.S.1.3 item 3)."""
    data_dir = project_root / ".claude" / "tdd-guard" / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return DependencyCheck(
            name="tdd-guard data directory",
            status="BROKEN",
            detail=f"{data_dir} not writable: {exc}",
            remediation="Check filesystem permissions on the project directory.",
        )
    return DependencyCheck(
        name="tdd-guard data directory",
        status="OK",
        detail=f"{data_dir} writable",
        remediation=None,
    )


#: 12 superpowers skills required by sec.S.1.3 item 4.
SUPERPOWERS_SKILLS: tuple[str, ...] = (
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "verification-before-completion",
    "requesting-code-review",
    "receiving-code-review",
    "executing-plans",
    "subagent-driven-development",
    "dispatching-parallel-agents",
    "systematic-debugging",
    "using-git-worktrees",
    "finishing-a-development-branch",
)


def _find_skill_md(plugins_root: Path, plugin_name: str, skill_name: str) -> Path | None:
    """Return the first ``SKILL.md`` under ``plugins_root/**/{plugin}/**/skills/{skill}/``."""
    if not plugins_root.exists():
        return None
    for candidate in plugins_root.rglob(f"{plugin_name}/**/skills/{skill_name}/SKILL.md"):
        return candidate
    return None


def check_superpowers(plugins_root: Path) -> DependencyCheck:
    """Verify all 12 superpowers skills are discoverable (sec.S.1.3 item 4)."""
    missing: list[str] = []
    for skill in SUPERPOWERS_SKILLS:
        if _find_skill_md(plugins_root, "superpowers", skill) is None:
            missing.append(skill)
    if len(missing) == len(SUPERPOWERS_SKILLS):
        return DependencyCheck(
            name="superpowers plugin",
            status="MISSING",
            detail=f"Plugin not discoverable under {plugins_root}.",
            remediation="/plugin marketplace add obra/superpowers && /plugin install",
        )
    if missing:
        return DependencyCheck(
            name="superpowers plugin",
            status="BROKEN",
            detail=f"missing skills: {', '.join(missing)}",
            remediation="Reinstall superpowers via /plugin install",
        )
    return DependencyCheck(
        name="superpowers plugin",
        status="OK",
        detail=f"{len(SUPERPOWERS_SKILLS)} skills found",
        remediation=None,
    )


def check_magi(plugins_root: Path) -> DependencyCheck:
    """Verify the magi plugin is discoverable (sec.S.1.3 item 5)."""
    skill_md = _find_skill_md(plugins_root, "magi", "magi")
    if skill_md is None:
        return DependencyCheck(
            name="magi plugin",
            status="MISSING",
            detail=f"Plugin not discoverable under {plugins_root}.",
            remediation="/plugin marketplace add BolivarTech/magi",
        )
    run_magi = skill_md.parent / "scripts" / "run_magi.py"
    if not run_magi.exists():
        return DependencyCheck(
            name="magi plugin",
            status="BROKEN",
            detail=f"run_magi.py missing at {run_magi}",
            remediation="Reinstall magi via /plugin install",
        )
    return DependencyCheck(
        name="magi plugin",
        status="OK",
        detail=f"found at {skill_md.parent}",
        remediation=None,
    )


def check_claude_cli() -> DependencyCheck:
    """Verify the ``claude`` CLI is in PATH (required by superpowers/magi dispatchers).

    Both :mod:`superpowers_dispatch` and :mod:`magi_dispatch` shell out via
    ``claude -p``; without the binary the workflow cannot invoke sub-skills.
    Surfaced during pre-flight so ``init`` fails fast before any file is
    created (sec.S.1.3 companion check; MAGI Checkpoint 2 iter 2 caspar fix).
    """
    if shutil.which("claude") is None:
        return DependencyCheck(
            name="claude CLI",
            status="MISSING",
            detail="Binary 'claude' not found in PATH.",
            remediation="Install Claude Code from https://claude.com/claude-code",
        )
    try:
        result = subprocess_utils.run_with_timeout(["claude", "--version"], timeout=5)
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="claude CLI",
            status="BROKEN",
            detail="claude --version timed out after 5s",
            remediation="Reinstall Claude Code",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="claude CLI",
            status="BROKEN",
            detail=f"claude --version returncode={result.returncode}",
            remediation="Reinstall Claude Code",
        )
    combined = (result.stdout or result.stderr).strip()
    detail = combined.splitlines()[0] if combined else "claude present"
    return DependencyCheck(
        name="claude CLI",
        status="OK",
        detail=detail,
        remediation=None,
    )
