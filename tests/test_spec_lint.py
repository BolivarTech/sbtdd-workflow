#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Tests for skills/sbtdd/scripts/spec_lint.py (v1.0.2 Item C).

Covers escenarios C-R1-1..R5-2, C-int-1, C-int-2, C-cli-1 per
sbtdd/spec-behavior.md sec.§4.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest


def test_lint_finding_dataclass_shape():
    """LintFinding is a frozen dataclass with required fields."""
    from spec_lint import LintFinding

    assert is_dataclass(LintFinding)
    f = LintFinding(
        file=Path("x.md"),
        line=1,
        rule="R1",
        severity="error",
        message="m",
    )
    assert f.file == Path("x.md")
    assert f.line == 1
    assert f.rule == "R1"
    assert f.severity == "error"
    assert f.message == "m"
    with pytest.raises(Exception):
        f.line = 99  # type: ignore[misc]


def test_lint_spec_clean_file_returns_empty_list(tmp_path):
    """Clean spec returns empty list of findings."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# Title\n\n"
        "> Generado 2026-05-06 a partir de sbtdd/spec-behavior-base.md\n\n"
        "## 1. Section\n\n"
        "**Escenario X-1: example**\n\n"
        "> **Given** something\n"
        "> **When** action\n"
        "> **Then** result\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)

    assert findings == []


def test_c_r1_1_well_formed_escenario_passes(tmp_path):
    """C-R1-1: escenario with all bullets returns no R1 finding."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: ejemplo**\n\n"
        "> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r1 = [f for f in findings if f.rule == "R1"]
    assert r1 == []


def test_c_r1_2_missing_given_fails(tmp_path):
    """C-R1-2: escenario missing Given block emits R1 error."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: bad**\n\n"
        "> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r1 = [f for f in findings if f.rule == "R1"]
    assert len(r1) == 1
    assert r1[0].severity == "error"
    assert "given" in r1[0].message.lower()
