#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 C7 smoke test for SKILL.md methodology-activity procedure."""

from __future__ import annotations

from pathlib import Path


def test_skill_md_documents_methodology_activity_ship_time_procedure() -> None:
    """C7: SKILL.md contains methodology-activity ship-time procedure section."""
    skill_md = Path(__file__).parent.parent / "skills" / "sbtdd" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "methodology-activity" in text.lower()
    assert "ship time" in text.lower() or "ship-time" in text.lower()
    assert "v1.0.X+1 LOCKED" in text or "next-cycle LOCKED" in text.lower()
