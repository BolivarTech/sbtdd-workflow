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

from dataclasses import dataclass

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
