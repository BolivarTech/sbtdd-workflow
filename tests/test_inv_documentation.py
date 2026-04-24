# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Regression-pinning tests for INV-24 / INV-29 / TOCTOU docstring contracts.

Covers Plan D Phase 4 Tasks 14-16:

- Task 14: ``auto_cmd`` module docstring cross-references INV-24 semantics
  and points readers at ``resume_cmd._resolve_uncommitted`` for the
  CONTINUE-by-default contract.
- Task 15: ``pre_merge_cmd._loop2`` docstring formalises the INV-29
  feedback-loop contract (rejected conditions fed back to MAGI context
  to break sterile loops).
- Task 16: ``init_cmd._mkdir_tracked`` documents the TOCTOU window
  between ``_collect_created_dirs`` and ``mkdir(exist_ok=False)`` as
  acceptable for the single-user ``/sbtdd init`` invocation pattern.

These tests are pure contract pins -- they assert that the documentation
is present, not that any runtime behavior changed.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import auto_cmd
import init_cmd
import pre_merge_cmd
import resume_cmd

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_auto_cmd_docstring_references_inv24_semantics() -> None:
    doc = auto_cmd.__doc__ or ""
    assert "INV-24" in doc
    # Must explain that uncommitted-work CONTINUE default is in resume.
    assert "resume" in doc.lower() and "continue" in doc.lower()


def test_resume_resolve_uncommitted_docstring_mentions_inv24() -> None:
    doc = resume_cmd._resolve_uncommitted.__doc__ or ""
    assert "INV-24" in doc
    assert "CONTINUE" in doc


def test_pre_merge_loop2_docstring_mentions_inv29() -> None:
    doc = pre_merge_cmd._loop2.__doc__ or ""
    assert "INV-29" in doc
    assert "feedback" in doc.lower() or "rejection" in doc.lower() or "rejected" in doc.lower()


def test_init_cmd_mkdir_tracked_documents_toctou() -> None:
    doc = init_cmd._mkdir_tracked.__doc__ or ""
    # TOCTOU acknowledgement comment is acceptable inside docstring or
    # immediately below the function. Inspect source for the keyword.
    source = inspect.getsource(init_cmd._mkdir_tracked)
    assert "TOCTOU" in source or "race" in source.lower()
    # Silence unused-variable lint while preserving the docstring probe
    # as a sanity guard.
    assert isinstance(doc, str)


def test_inv31_documented_in_claude_md() -> None:
    """INV-31 (spec-reviewer gate) must appear as a bold bullet in CLAUDE.md
    Invariants Summary -- not merely as a prose reference in the v0.2 LOCKED
    section. The canonical bullet format is `- **INV-31** ...`.
    """
    import re

    text = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert re.search(r"^- \*\*INV-31\*\*", text, re.MULTILINE), (
        "CLAUDE.md Invariants Summary must contain the INV-31 bullet"
    )
    # The bullet must reference the spec-reviewer gate concept.
    assert "spec-reviewer" in text.lower(), "CLAUDE.md INV-31 bullet must mention spec-reviewer"


def test_inv31_documented_in_spec_base() -> None:
    """INV-31 must be registered in sbtdd/sbtdd-workflow-plugin-spec-base.md
    sec.S.10 using the same bold bullet format used for INV-22..INV-30.
    """
    import re

    text = (REPO_ROOT / "sbtdd" / "sbtdd-workflow-plugin-spec-base.md").read_text(encoding="utf-8")
    assert re.search(r"^- \*\*INV-31\b", text, re.MULTILINE), (
        "spec-base sec.S.10 must register INV-31 with a bold bullet"
    )
    assert "spec-reviewer" in text.lower(), "spec-base INV-31 entry must mention spec-reviewer"
