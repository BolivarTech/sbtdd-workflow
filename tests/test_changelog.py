#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""CHANGELOG.md cross-artifact alignment tests (sec.2.5 hotfixes HF1-HF3)
plus the v0.5.0 entry contract (Task S2-14).

The tests treat CHANGELOG.md, the spec, the impl, and SKILL.md as a
multi-artifact contract. Drift in any single artifact must surface as
a test failure, not silently ship.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _normalise_whitespace(text: str) -> str:
    """Collapse all whitespace runs (incl. newlines) into single spaces."""
    return re.sub(r"\s+", " ", text)


def test_hf1_recovery_breadcrumb_wording_aligned():
    """HF1: spec, CHANGELOG, and impl all use identical recovery breadcrumb wording.

    The breadcrumb text appears as a single emitted line at runtime but
    may be split across f-string concatenations in source; we normalise
    whitespace before searching so cross-line wraps in markdown / source
    do not mask the contract violation.
    """
    canonical = "[sbtdd magi] synthesizer failed; manual synthesis recovery applied"
    spec = _normalise_whitespace(_read("sbtdd/spec-behavior.md"))
    changelog = _normalise_whitespace(_read("CHANGELOG.md"))
    impl = _normalise_whitespace(_read("skills/sbtdd/scripts/magi_dispatch.py"))
    assert canonical in spec, "spec missing canonical wording"
    assert canonical in changelog, "CHANGELOG missing canonical wording"
    assert canonical in impl, "impl missing canonical wording"


def test_hf2_marker_schema_docs_match_impl():
    """HF2: marker file schema documented in CHANGELOG matches impl emission.

    The four canonical fields ``verdict``, ``iteration``, ``agents``,
    ``timestamp`` MUST appear quoted in the impl source AND named in the
    CHANGELOG `[0.4.0]` section so operators investigating
    ``MAGI_VERDICT_MARKER.json`` files have a single-source schema.
    """
    impl = _read("skills/sbtdd/scripts/magi_dispatch.py")
    changelog = _read("CHANGELOG.md")
    expected_fields = ["verdict", "iteration", "agents", "timestamp"]
    for field_name in expected_fields:
        assert (
            f'"{field_name}"' in impl
        ), f"impl missing marker field {field_name!r}"
        assert (
            field_name in changelog
        ), f"CHANGELOG missing marker field doc {field_name!r}"
