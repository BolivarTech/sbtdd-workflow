#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""skills/sbtdd/scripts/spec_lint.py - H5-2 spec_lint enforcement.

Mechanical lint checks against spec-behavior.md and plan-tdd-org.md.
Invoked from spec_cmd._run_magi_checkpoint2 BEFORE magi_dispatch.invoke_magi
to catch malformed specs before they consume MAGI iter budget.

Per spec sec.2.3 v1.0.2 Item C. 5 rules R1-R5; Q3 dictamen R3=warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LintFinding:
    file: Path
    line: int
    rule: str
    severity: str
    message: str


def lint_spec(path: Path) -> list[LintFinding]:
    """Run mechanical lint checks against a spec file.

    Returns:
        list of LintFinding (empty = clean). Error-severity findings
        block Checkpoint 2; warning-severity emit stderr breadcrumb
        but do not block.
    """
    if not path.exists():
        return [
            LintFinding(
                file=path,
                line=0,
                rule="R0",
                severity="error",
                message=f"spec file not found: {path}",
            )
        ]
    path.read_text(encoding="utf-8")
    findings: list[LintFinding] = []
    # Subsequent tasks 8-12 fill in R1-R5 checks.
    return findings
