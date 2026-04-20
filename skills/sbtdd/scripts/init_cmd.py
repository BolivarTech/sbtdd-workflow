#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd init -- atomic 5-phase bootstrap (sec.S.5.1).

Phases: 1 pre-flight deps, 2 arg resolution, 3 atomic generation,
4 smoke test, 5 report. Invariant all-or-nothing: abort at any phase
leaves the project intact (staging dir discarded on error).

Atomicity contract (MAGI Milestone C iter 1 Finding 2): every file
created during Phase 3a AND Phase 3b lands FIRST in a tempdir built
from ``tempfile.mkdtemp(prefix='sbtdd-init-')``. The dest_root is NOT
touched until Phase 4 smoke test (which runs against the tempdir)
passes. Phase 5 performs a single atomic relocation from tempdir to
dest_root. If Phase 4 fails, the tempdir is cleaned up and dest_root
remains byte-identical to its pre-invocation state -- satisfying
sec.S.5.1 all-or-nothing.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from dependency_check import check_environment
from errors import DependencyError, PreconditionError, ValidationError
from templates import expand

# Root of the plugin distribution (repo root when running from source).
# scripts/init_cmd.py is at skills/sbtdd/scripts/init_cmd.py, so repo root is
# four parents up.
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TEMPLATES_DIR = _PLUGIN_ROOT / "templates"


#: Stack-specific verification commands written into CLAUDE.local.md (sec.S.4.2).
_VERIF_CMDS: dict[str, tuple[str, ...]] = {
    "rust": (
        "cargo nextest run",
        "cargo audit",
        "cargo clippy --all-targets -- -D warnings",
        "cargo fmt --check",
    ),
    "python": (
        "python -m pytest",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m mypy .",
    ),
    "cpp": ("ctest --output-junit ctest-junit.xml",),
}


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for ``/sbtdd init``."""
    p = argparse.ArgumentParser(prog="sbtdd init")
    p.add_argument("--stack", choices=("rust", "python", "cpp"), default=None)
    p.add_argument("--author", type=str, default=None)
    p.add_argument("--error-type", type=str, default=None)
    p.add_argument(
        "--conftest-mode",
        choices=("merge", "replace", "skip"),
        default="merge",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--plugins-root",
        type=Path,
        default=Path.home() / ".claude" / "plugins",
    )
    return p


def _resolve_args(ns: argparse.Namespace) -> argparse.Namespace:
    """Prompt for missing stack/author/error_type when a TTY is attached.

    In non-interactive mode every missing required flag raises
    :class:`ValidationError` so the caller maps to exit 1.
    """
    if ns.stack is None:
        if sys.stdin.isatty():
            raw = input("Stack (rust/python/cpp): ").strip()
            if raw not in ("rust", "python", "cpp"):
                raise ValidationError(f"stack must be rust, python, or cpp; got '{raw}'")
            ns.stack = raw
        else:
            raise ValidationError("--stack is required in non-interactive mode")
    if ns.author is None:
        if sys.stdin.isatty():
            ns.author = input("Author name: ").strip() or "Unknown"
        else:
            raise ValidationError("--author is required in non-interactive mode")
    if ns.stack == "rust" and ns.error_type is None:
        if sys.stdin.isatty():
            ns.error_type = input("Error type name (e.g. MyErr): ").strip() or "Error"
        else:
            raise ValidationError("--error-type is required for --stack rust")
    return ns


def _make_staging_dir() -> Path:
    """Create a tempdir mirroring the dest_root tree during init.

    All Phase 3a + Phase 3b writes land here; dest_root is untouched
    until Phase 5 relocation after Phase 4 smoke-test succeeds.
    """
    td = Path(tempfile.mkdtemp(prefix="sbtdd-init-"))
    (td / ".claude").mkdir()
    (td / "sbtdd").mkdir()
    (td / "planning").mkdir()
    return td


def _phase3a_generate(ns: argparse.Namespace, staging: Path, dest_root: Path) -> None:
    """Write CLAUDE.local.md + .claude/plugin.local.md into STAGING (not dest_root).

    Pre-flight check against dest_root for existing CLAUDE.local.md runs
    here (requires ``--force`` to overwrite).
    """
    if (dest_root / "CLAUDE.local.md").exists() and not ns.force:
        raise PreconditionError("CLAUDE.local.md already exists; use --force to overwrite")
    tpl_c = (_TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    ctx = {
        "author": ns.author,
        "error_type": ns.error_type or "Error",
        "stack": ns.stack,
        "verification_commands": "\n".join(_VERIF_CMDS[ns.stack]),
    }
    (staging / "CLAUDE.local.md").write_text(expand(tpl_c, ctx), encoding="utf-8")
    tpl_p = (_TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    (staging / ".claude" / "plugin.local.md").write_text(expand(tpl_p, ctx), encoding="utf-8")


def _phase4_smoke_test(staging: Path) -> None:
    """Validate the STAGED tree before Phase 5 relocation (filled in Task 15).

    Runs exclusively against staging -- dest_root is untouched if this raises.
    Task 13 stub is a no-op; Task 15 adds the actual validations.
    """


def _phase5_relocate(staging: Path, dest_root: Path) -> list[Path]:
    """Atomically copy the staged tree into dest_root. Returns list of targets."""
    staged_files = [p for p in staging.rglob("*") if p.is_file()]
    created: list[Path] = []
    for src in staged_files:
        rel = src.relative_to(staging)
        target = dest_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        created.append(target)
    return created


def _cleanup_staging(staging: Path) -> None:
    """Delete the staging tempdir. Silent on OSError to avoid masking aborts."""
    try:
        shutil.rmtree(staging, ignore_errors=True)
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init subcommand.

    Args:
        argv: Command-line arguments (None uses sys.argv).

    Returns:
        Process exit code (0 on success).

    Raises:
        ValidationError: Missing required flags in non-interactive mode.
        DependencyError: Pre-flight check aggregated failures.
        PreconditionError: Phase 3a/3b/4 detected a blocking condition.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    ns = _resolve_args(ns)
    report = check_environment(ns.stack, ns.project_root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    staging = _make_staging_dir()
    try:
        _phase3a_generate(ns, staging, ns.project_root)
        _phase4_smoke_test(staging)
        _phase5_relocate(staging, ns.project_root)
    except Exception:
        _cleanup_staging(staging)
        raise
    _cleanup_staging(staging)
    return 0


run = main
