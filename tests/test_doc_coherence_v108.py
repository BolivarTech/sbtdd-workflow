#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-14
"""v1.0.8 T6 doc-coherence smoke tests for Pillar B2 upstream bug archive.

Asserts the cross-artifact wording requirements:

- CLAUDE.md has a "Known upstream limitations" section with required keywords.
- CHANGELOG.md has a ``[1.0.8]`` entry with a Deferred subsection naming the
  upstream report submission deferral.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CLAUDE_MD = _REPO_ROOT / "CLAUDE.md"
_CHANGELOG = _REPO_ROOT / "CHANGELOG.md"


def test_v108_b2_claude_md_has_known_upstream_limitations_section() -> None:
    """v1.0.8 B2-1: CLAUDE.md has the upstream limitations section."""
    text = _CLAUDE_MD.read_text(encoding="utf-8")
    assert "## Known upstream limitations" in text, (
        "v1.0.8 B2-1: missing '## Known upstream limitations' header"
    )
    assert "### claude -p /test-driven-development hangs" in text, (
        "v1.0.8 B2-1: missing subsection header"
    )
    for required in (
        "Manifestation",
        "Repro context",
        "Workaround",
        "Upstream report",
        "SBTDD_E2E_STUB_DISPATCH",
    ):
        assert required in text, (
            f"v1.0.8 B2-1: missing required text {required!r} in CLAUDE.md"
        )


def test_v108_b2_changelog_has_v108_deferred_section() -> None:
    """v1.0.8 B2-4: CHANGELOG [1.0.8] Deferred section lists upstream report."""
    text = _CHANGELOG.read_text(encoding="utf-8")
    assert "## [1.0.8]" in text, "v1.0.8 B2-4: missing [1.0.8] entry"
    start = text.index("## [1.0.8]")
    end = text.find("## [1.0.7]", start)
    section = text[start:end] if end > 0 else text[start:]
    assert "Deferred" in section, (
        "v1.0.8 B2-4: [1.0.8] section missing 'Deferred' subsection"
    )
    assert "anthropics/claude-code" in section, (
        "v1.0.8 B2-4: Deferred section missing upstream report reference"
    )
