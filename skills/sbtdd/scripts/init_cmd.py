#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd init -- atomic 5-phase bootstrap (sec.S.5.1).

Phases: 1 pre-flight deps, 2 arg resolution, 3 atomic generation,
4 smoke test, 5 report. Invariant all-or-nothing: abort at any phase
leaves the project intact (staging dir discarded on error).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dependency_check import check_environment
from errors import DependencyError, ValidationError


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


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init subcommand.

    Args:
        argv: Command-line arguments (None uses sys.argv).

    Returns:
        Process exit code (0 on success).

    Raises:
        ValidationError: Missing required flags in non-interactive mode.
        DependencyError: Pre-flight check aggregated failures.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    ns = _resolve_args(ns)
    report = check_environment(ns.stack, ns.project_root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    return 0


run = main
