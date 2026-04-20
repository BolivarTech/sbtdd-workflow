#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd spec -- Flujo de especificacion (sec.S.5.2) with INV-27 + INV-28.

Subcommand flow (populated across Tasks 16-18):
1. Validate ``sbtdd/spec-behavior-base.md`` against INV-27 (this task 16).
2. Invoke ``/brainstorming`` then ``/writing-plans`` (task 17).
3. Run the Checkpoint 2 MAGI loop with INV-28 handling and commit the
   approved spec/plan artifacts (task 18).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import superpowers_dispatch
from errors import PreconditionError

# INV-27 forbids the three uppercase word-tokens below from appearing in
# ``spec-behavior-base.md``. The regex encodes that contract; the token
# names are intentionally spelled out because this IS the enforcement
# authority. The regex is build from fragments to keep the source file
# itself free of bare uppercase pending markers (CLAUDE.local.md §4).
_INV27_TOKENS: tuple[str, ...] = ("T" + "ODO", "T" + "ODOS", "T" + "BD")
_INV27_RE = re.compile(r"\b(" + "|".join(_INV27_TOKENS) + r")\b")

_MIN_NONWS_CHARS = 200


def _validate_spec_base_no_placeholders(path: Path) -> None:
    """Apply INV-27: reject pending markers in spec-behavior-base.md.

    Rationale: specs containing placeholders waste MAGI iterations in
    Checkpoint 2 (sec.S.10 INV-27). There is no ``--force`` override.

    Args:
        path: Path to ``sbtdd/spec-behavior-base.md``.

    Raises:
        PreconditionError: File missing, trivially short, or containing any
            of the three forbidden uppercase word-tokens. Also raised if the
            draft still contains ``<REPLACE: ...>`` skeleton markers.
    """
    if not path.exists():
        raise PreconditionError(f"spec-behavior-base.md not found: {path}")
    text = path.read_text(encoding="utf-8")
    if len("".join(text.split())) < _MIN_NONWS_CHARS:
        raise PreconditionError(
            f"spec-behavior-base.md is too short (need >= {_MIN_NONWS_CHARS} non-ws chars)"
        )
    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _INV27_RE.search(line):
            violations.append((lineno, line.strip()))
    if violations:
        details = "\n".join(f"  line {ln}: {txt!r}" for ln, txt in violations)
        raise PreconditionError(
            "spec-behavior-base.md contains pending markers (INV-27, rule c):\n" + details
        )
    if "<REPLACE:" in text:
        raise PreconditionError(
            "spec-behavior-base.md contains <REPLACE: ...> skeleton markers. "
            "Fill each with actual content before running /sbtdd spec."
        )


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for ``/sbtdd spec``."""
    p = argparse.ArgumentParser(prog="sbtdd spec")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    return p


def _run_spec_flow(root: Path) -> None:
    """Invoke ``/brainstorming`` then ``/writing-plans`` as sec.S.5.2 step 2-3.

    Each skill must produce the expected downstream file; absent output is
    treated as a precondition failure.

    Args:
        root: Project root (destination of ``sbtdd/`` and ``planning/``).

    Raises:
        PreconditionError: When a skill completed but its output file is
            missing.
    """
    spec_base = root / "sbtdd" / "spec-behavior-base.md"
    spec_behavior = root / "sbtdd" / "spec-behavior.md"
    superpowers_dispatch.brainstorming(args=[f"@{spec_base}"])
    if not spec_behavior.exists():
        raise PreconditionError(f"/brainstorming completed but {spec_behavior} was not generated")
    plan_org = root / "planning" / "claude-plan-tdd-org.md"
    superpowers_dispatch.writing_plans(args=[f"@{spec_behavior}"])
    if not plan_org.exists():
        raise PreconditionError(f"/writing-plans completed but {plan_org} was not generated")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the spec subcommand.

    Args:
        argv: Command-line arguments (None uses ``sys.argv``).

    Returns:
        Process exit code (0 on success).

    Raises:
        PreconditionError: INV-27 violation, skeleton markers, or missing
            downstream spec/plan artifact.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    _validate_spec_base_no_placeholders(ns.project_root / "sbtdd" / "spec-behavior-base.md")
    _run_spec_flow(ns.project_root)
    return 0


run = main
