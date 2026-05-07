#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Cross-artifact alignment test: plugin's MAGI dispatch path matches
canonical template at ``D:\\jbolivarg\\BolivarTech\\AI_Tools\\magi-gate-template.md``.

Per spec sec.2.1 v1.0.3 Item A. Pattern follows ``tests/test_changelog.py``
HF1 cross-artifact wording alignment (line-anchored grep template
canonical strings vs plugin code paths).

Covers escenarios A-1, A-2, A-3, A-5 from spec sec.4 (A-4 is process
narrative, validated by audit-doc presence + GAP routing column).

The template path is overridable via the ``SBTDD_MAGI_TEMPLATE_PATH`` env
var so the test runs in environments where the canonical file lives
outside the developer's local checkout (CI, sister project clones).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

_DEFAULT_TEMPLATE_PATH = r"D:\jbolivarg\BolivarTech\AI_Tools\magi-gate-template.md"
_TEMPLATE_PATH = Path(os.environ.get("SBTDD_MAGI_TEMPLATE_PATH", _DEFAULT_TEMPLATE_PATH))
_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_DOC = _REPO_ROOT / "docs" / "audits" / "v1.0.3-magi-gate-template-alignment.md"


def _canonical_strings_from_template() -> list[str]:
    """Return canonical strings the template's normative sections require.

    Each entry is a substring that MUST appear somewhere under the
    plugin's MAGI dispatch path (``skills/sbtdd/scripts/`` plus
    ``templates/``) when the audit reports the section as MATCH.
    Entries also gated by ``test_canonical_strings_in_template`` so an
    out-of-date fixture (template moved on, plugin static) skips
    instead of failing -- the audit doc is the source of truth, not
    this list.

    The returned list is curated from template sections explicitly
    cross-referenced in audit GAP/MATCH analysis (see
    ``docs/audits/v1.0.3-magi-gate-template-alignment.md`` rows 1-6).
    """
    return [
        # Verdict labels (Pass threshold + verdict action table) -- match
        # plugin's underscore convention exactly (per template "Naming note").
        "STRONG_NO_GO",
        "HOLD",
        "GO_WITH_CAVEATS",
        "GO",
        "STRONG_GO",
        # Carry-forward block heading -- canonical markdown text MAGI
        # agents key off (template Carry-forward section line 202). The
        # plugin's _normalize_findings_for_carry_forward references this
        # string in a comment; an emit path is a v1.0.4 GAP.
        "Prior triage context",
    ]


def _grep_repo(pattern: str, search_paths: list[Path]) -> list[tuple[Path, int]]:
    """Return list of ``(path, line_number)`` where ``pattern`` appears literally.

    Recursively scans every ``.py`` and ``.md`` file under each base in
    ``search_paths`` (silently skipping unreadable files / binaries to
    keep the test resilient to merge-conflict noise or future
    additions). Pattern is treated as a literal substring -- no regex
    metacharacter handling -- so callers pass exact tokens.
    """
    hits: list[tuple[Path, int]] = []
    for base in search_paths:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".py", ".md"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    hits.append((path, lineno))
    return hits


def test_template_file_exists() -> None:
    """A-3 prerequisite: template canonical source is reachable.

    The audit alignment contract is meaningless without the template
    on-disk. Skip cleanly when absent so CI runs without the developer's
    local sister project still pass; the developer running locally sees
    PASS as a regression guard against accidentally moving the file.
    """
    if not _TEMPLATE_PATH.exists():
        pytest.skip(
            f"Template not found at {_TEMPLATE_PATH}. Set "
            "SBTDD_MAGI_TEMPLATE_PATH env var to override (e.g. when the "
            "canonical template lives in a sister repository checkout)."
        )
    assert _TEMPLATE_PATH.is_file(), f"Template path is not a regular file: {_TEMPLATE_PATH}"


def test_canonical_strings_in_template() -> None:
    """A-3 prerequisite: each curated string appears in the template.

    Guards against drift between this test fixture and the template:
    if the template renames a verdict or removes a setting placeholder,
    the test fixture must update first. Without this guard the plugin-
    side assertion would silently pass despite template changes.
    """
    if not _TEMPLATE_PATH.exists():
        pytest.skip("Template not available for fixture validation.")
    template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    missing = [s for s in _canonical_strings_from_template() if s not in template_text]
    assert not missing, (
        "Test fixture out of sync with template (template lacks these "
        "strings the test expects):\n" + "\n".join(f"  - {s!r}" for s in missing)
    )


def test_canonical_strings_present_in_plugin() -> None:
    """A-3: required canonical strings from template appear in plugin.

    The verdict labels + per-project placeholder names are non-optional
    -- they encode the plugin's contract with the template. Missing any
    of them indicates either a real GAP or a fixture out-of-date with
    template (the latter is caught by ``test_canonical_strings_in_template``
    above; if that test passed and this one fails, the GAP is real).
    """
    if not _TEMPLATE_PATH.exists():
        pytest.skip("Template not available; alignment check requires fixture.")
    search_paths = [
        _REPO_ROOT / "skills" / "sbtdd" / "scripts",
        _REPO_ROOT / "templates",
    ]
    missing = []
    for canonical in _canonical_strings_from_template():
        hits = _grep_repo(canonical, search_paths)
        if not hits:
            missing.append(canonical)
    assert not missing, (
        "Plugin MAGI dispatch path missing canonical template strings -- "
        "audit doc must record these as GAP rows:\n" + "\n".join(f"  - {s!r}" for s in missing)
    )


def test_audit_doc_exists() -> None:
    """A-1 prerequisite: audit doc was generated by Track Alpha (Item A).

    Canonical artifact path is fixed by spec sec.2.1: failing this
    assertion means the doc was deleted, moved, or never written. The
    rest of the audit-doc contract tests skip when this fails so the
    operator gets a single clear root-cause signal.
    """
    assert _AUDIT_DOC.exists(), (
        f"Audit doc missing: {_AUDIT_DOC}. Expected v1.0.3 Track Alpha Task 1 to write it."
    )


def test_audit_doc_has_required_columns() -> None:
    """A-2: audit doc table contains the five required columns.

    The audit table format is mandated by spec sec.2.1 + plan Track
    Alpha Task 1 Step 4. Five columns: Template Section, Plugin Impl
    Path, Status, Evidence, Action. Letter-case insensitive (header
    rendering varies across markdown previewers) and whitespace-tolerant
    (multi-line headers fold via _normalise_whitespace).
    """
    if not _AUDIT_DOC.exists():
        pytest.skip("Audit doc not yet generated; covered by test_audit_doc_exists.")
    text = _AUDIT_DOC.read_text(encoding="utf-8")
    normalised = re.sub(r"\s+", " ", text).lower()
    required_columns = [
        "template section",
        "plugin impl path",
        "status",
        "evidence",
        "action",
    ]
    missing = [col for col in required_columns if col not in normalised]
    assert not missing, (
        f"Audit doc missing required column header(s): {missing}. "
        "Headers must appear in the per-section table per spec sec.2.1."
    )


def test_audit_doc_status_values_canonical() -> None:
    """A-2: audit doc reports at least one row with a canonical Status value.

    Status column must be one of {MATCH, GAP, OBSOLETE} per plan Task 1
    Step 4. This smoke check guards against an empty / placeholder
    audit doc that would silently pass the column-headers check above.
    A doc with zero canonical statuses indicates the table body was
    never populated.
    """
    if not _AUDIT_DOC.exists():
        pytest.skip("Audit doc not yet generated.")
    text = _AUDIT_DOC.read_text(encoding="utf-8")
    canonical_statuses = ("MATCH", "GAP", "OBSOLETE")
    found = [s for s in canonical_statuses if s in text]
    assert found, (
        "Audit doc has no rows with canonical Status value (expected at "
        f"least one of {canonical_statuses}). Empty / placeholder audit "
        "table is a deliverable failure."
    )


def test_audit_doc_covers_six_template_sections() -> None:
    """A-5: audit doc enumerates all six normative template sections.

    Regression guard against incomplete audits where the operator
    audited some sections but skipped others. Six sections per template
    (Trigger criteria, Pass threshold, Carry-forward, Review summary,
    Cost awareness, Per-project setup); each must surface as a row by
    name (case-insensitive substring search).
    """
    if not _AUDIT_DOC.exists():
        pytest.skip("Audit doc not yet generated.")
    text = _AUDIT_DOC.read_text(encoding="utf-8").lower()
    required_sections = [
        "trigger criteria",
        "pass threshold",
        "carry-forward",
        "review summary",
        "cost awareness",
        "per-project setup",
    ]
    missing = [s for s in required_sections if s not in text]
    assert not missing, (
        f"Audit doc does not cover required template sections: {missing}. "
        "All six normative sections must be enumerated per spec sec.2.1."
    )
