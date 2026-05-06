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

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LintFinding:
    file: Path
    line: int
    rule: str
    severity: str
    message: str


_ESCENARIO_RE = re.compile(
    r"^(?:\*\*Escenario\s+([A-Za-z0-9-]+)[^\*]*\*\*|"
    r"#{2,3}\s+Escenario\s+([A-Za-z0-9-]+)[^\n]*)\s*$",
    re.MULTILINE,
)
_GIVEN_RE = re.compile(r"^>\s*\*\*Given\*\*", re.MULTILINE)
_WHEN_RE = re.compile(r"^>\s*\*\*When\*\*", re.MULTILINE)
_THEN_RE = re.compile(r"^>\s*\*\*Then\*\*", re.MULTILINE)


def _check_r2(path: Path, text: str) -> list[LintFinding]:
    """R2: escenario IDs unique across spec."""
    findings: list[LintFinding] = []
    seen: dict[str, list[int]] = {}
    for m in _ESCENARIO_RE.finditer(text):
        ident = m.group(1) or m.group(2)
        if ident is None:
            continue
        line = text.count("\n", 0, m.start()) + 1
        seen.setdefault(ident, []).append(line)
    for ident, lines in seen.items():
        if len(lines) > 1:
            for ln in lines:
                others = [other for other in lines if other != ln]
                findings.append(
                    LintFinding(
                        file=path,
                        line=ln,
                        rule="R2",
                        severity="error",
                        message=(f"duplicate escenario ID '{ident}' (other occurrences: {others})"),
                    )
                )
    return findings


def _check_r1(path: Path, text: str) -> list[LintFinding]:
    """R1: each escenario block has Given + When + Then bullets."""
    findings: list[LintFinding] = []
    matches = list(_ESCENARIO_RE.finditer(text))
    for i, m in enumerate(matches):
        line_start = text.count("\n", 0, m.start()) + 1
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end() : block_end]
        for label, rx in (
            ("Given", _GIVEN_RE),
            ("When", _WHEN_RE),
            ("Then", _THEN_RE),
        ):
            if not rx.search(block):
                findings.append(
                    LintFinding(
                        file=path,
                        line=line_start,
                        rule="R1",
                        severity="error",
                        message=f"escenario at line {line_start} missing {label} block",
                    )
                )
    return findings


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
    text = path.read_text(encoding="utf-8")
    findings: list[LintFinding] = []
    findings.extend(_check_r1(path, text))
    findings.extend(_check_r2(path, text))
    # Subsequent tasks 10-12 fill in R3-R5 checks.
    return findings
