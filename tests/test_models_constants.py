#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E model registry constants."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import models


def test_allowed_claude_model_ids_is_tuple() -> None:
    """E6.1: ALLOWED_CLAUDE_MODEL_IDS is immutable (tuple, not list)."""
    assert isinstance(models.ALLOWED_CLAUDE_MODEL_IDS, tuple)
    with pytest.raises((AttributeError, TypeError)):
        models.ALLOWED_CLAUDE_MODEL_IDS.append("foo")  # type: ignore[attr-defined]


def test_allowed_claude_model_ids_contains_current_4x_families() -> None:
    """E6.2: tuple contains at least Opus 4.7, Sonnet 4.6, Haiku 4.5."""
    ids = set(models.ALLOWED_CLAUDE_MODEL_IDS)
    assert "claude-opus-4-7" in ids
    assert "claude-sonnet-4-6" in ids
    assert "claude-haiku-4-5-20251001" in ids


# ----- INV-0 pinning regex tightening (MAGI iter 1 findings #3 + #8) -----
#
# Iter 1 surfaced false positives in narrative prose against the v0.3.0
# baseline regex ``\b(?:use|pin|...)\s+(claude-...)``: phrases like
# ``don't use claude-opus-4-7`` (negation), ``you might use
# claude-sonnet-4-6 in some cases`` (descriptive), or ``for example,
# use claude-haiku-4-5`` (documentation snippet) all match and silently
# downgrade plugin.local.md to session default. The fix tightens the
# regex to require a pinning suffix (e.g. ``for all sessions``,
# ``globally``, ``as default``, ``as the default model``).


def test_inv0_regex_matches_imperative_with_for_all_sessions() -> None:
    """Iter 2 finding #3/#8: legit pin "Use claude-X for all sessions" matches."""
    m = models.INV_0_PINNED_MODEL_RE.search("Use claude-opus-4-7 for all sessions.")
    assert m is not None
    assert m.group(1) == "claude-opus-4-7"


def test_inv0_regex_matches_globally_suffix() -> None:
    """Iter 2 finding #3/#8: "Pin claude-X globally" matches."""
    m = models.INV_0_PINNED_MODEL_RE.search("Pin claude-sonnet-4-6 globally.")
    assert m is not None
    assert m.group(1) == "claude-sonnet-4-6"


def test_inv0_regex_matches_as_default_suffix() -> None:
    """Iter 2 finding #3/#8: "Always claude-X as default" matches."""
    m = models.INV_0_PINNED_MODEL_RE.search("Always claude-haiku-4-5 as default.")
    assert m is not None
    assert m.group(1) == "claude-haiku-4-5"


def test_inv0_regex_matches_as_the_pinned_model() -> None:
    """Iter 2 finding #3/#8: "use claude-X as the pinned model" matches."""
    m = models.INV_0_PINNED_MODEL_RE.search(
        "Use claude-opus-4-7 as the pinned model for this developer."
    )
    assert m is not None
    assert m.group(1) == "claude-opus-4-7"


def test_inv0_regex_does_not_match_negation_prose() -> None:
    """Iter 2 finding #3/#8: "don't use claude-X" must NOT match.

    Negation in narrative prose was the iter 1 baseline's worst false
    positive: an operator writing 'do not use claude-opus-4-7 in this
    skill' to advise AGAINST the model would silently pin it.
    """
    m = models.INV_0_PINNED_MODEL_RE.search("Do not use claude-opus-4-7 in this skill.")
    assert m is None


def test_inv0_regex_does_not_match_remember_prose() -> None:
    """Iter 2 finding #3/#8: "always remember to use claude-X conventions" must NOT match."""
    m = models.INV_0_PINNED_MODEL_RE.search(
        "Always remember to use claude-haiku-4-5 conventions when reviewing PRs."
    )
    assert m is None


def test_inv0_regex_does_not_match_descriptive_codebase_note() -> None:
    """Iter 2 finding #3/#8: "stick to claude-X for code review" must NOT match.

    Without an explicit ``globally`` / ``for all sessions`` suffix the
    phrase is a descriptive narrative note about one workflow, not a
    global pin.
    """
    m = models.INV_0_PINNED_MODEL_RE.search("Stick to claude-sonnet-4-6 for code review.")
    assert m is None


def test_inv0_regex_does_not_match_documentation_example() -> None:
    """Iter 2 finding #3/#8: "for example, use claude-X to optimize cost" must NOT match."""
    m = models.INV_0_PINNED_MODEL_RE.search(
        "For example, use claude-haiku-4-5 to optimize cost on cheap tasks."
    )
    assert m is None


def test_inv0_regex_does_not_match_might_use_some_cases() -> None:
    """Iter 2 finding #3/#8: "you might use claude-X in some cases" must NOT match."""
    m = models.INV_0_PINNED_MODEL_RE.search(
        "You might use claude-sonnet-4-6 in some cases."
    )
    assert m is None
