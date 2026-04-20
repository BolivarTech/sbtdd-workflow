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
from pathlib import Path


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


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init subcommand.

    Args:
        argv: Command-line arguments (None uses sys.argv).

    Returns:
        Process exit code (0 on success).
    """
    parser = _build_parser()
    parser.parse_args(argv)
    return 0


run = main
