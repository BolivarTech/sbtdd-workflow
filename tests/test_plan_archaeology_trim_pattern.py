#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.6 Item C.2 (carry-forward from v1.0.5 iter-2 G2 ladder defer):
plan archaeology trim methodology smoke test.

Asserts cross-artifact reference between SKILL.md and
templates/CLAUDE.local.md.template for the ship-time procedure pattern.
"""

from __future__ import annotations

from pathlib import Path


_SKILL_MD = Path("skills/sbtdd/SKILL.md")
_TEMPLATE = Path("templates/CLAUDE.local.md.template")
_PROCEDURE_PATTERN = "plan archaeology trim"


def test_c2_1_skill_md_documents_ship_time_trim_procedure() -> None:
    """C2-1: SKILL.md documents the ship-time plan archaeology trim procedure."""
    assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
    text = _SKILL_MD.read_text(encoding="utf-8").lower()
    assert _PROCEDURE_PATTERN in text, (
        f"SKILL.md must reference '{_PROCEDURE_PATTERN}' procedure (case-insensitive)"
    )
    # Must also mention the destination (CHANGELOG Process notes section)
    assert "process notes" in text or "changelog" in text, (
        "SKILL.md procedure must mention CHANGELOG Process notes destination"
    )


def test_c2_2_template_references_archaeology_trim() -> None:
    """C2-2: CLAUDE.local.md.template references the archaeology trim procedure."""
    assert _TEMPLATE.exists(), f"Template not found at {_TEMPLATE}"
    text = _TEMPLATE.read_text(encoding="utf-8").lower()
    assert _PROCEDURE_PATTERN in text, (
        f"Template must reference '{_PROCEDURE_PATTERN}' procedure (case-insensitive)"
    )


def test_c2_3_smoke_cross_artifact_reference_exists_in_both() -> None:
    """C2-3: drift between SKILL.md + template caught (both must reference)."""
    skill_text = _SKILL_MD.read_text(encoding="utf-8").lower()
    template_text = _TEMPLATE.read_text(encoding="utf-8").lower()
    skill_has = _PROCEDURE_PATTERN in skill_text
    template_has = _PROCEDURE_PATTERN in template_text
    assert skill_has and template_has, (
        f"Drift detected: SKILL.md has='{skill_has}', template has='{template_has}'. "
        f"Both must reference '{_PROCEDURE_PATTERN}' pattern."
    )
