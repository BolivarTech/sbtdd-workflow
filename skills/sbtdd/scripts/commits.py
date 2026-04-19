#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Git commit helpers enforcing sec.M.5 prefixes + INV-0/5-7 rules.

All plugin commits go through this module so validation is centralized:
- Only allowed prefixes (sec.M.5).
- English-only messages (Code Standards Git section).
- No Co-Authored-By lines (INV-7).
- No Claude/AI references (INV-7).
"""

from __future__ import annotations

import re

import subprocess_utils
from errors import ValidationError
from models import COMMIT_PREFIX_MAP

_ALLOWED_PREFIXES: frozenset[str] = frozenset(COMMIT_PREFIX_MAP.values())


def validate_prefix(prefix: str) -> None:
    """Raise ValidationError if prefix is not in the allowed set."""
    if prefix not in _ALLOWED_PREFIXES:
        raise ValidationError(
            f"commit prefix '{prefix}' not in {sorted(_ALLOWED_PREFIXES)} (sec.M.5)"
        )


_FORBIDDEN_MESSAGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Co-Authored-By", re.IGNORECASE),
    re.compile(r"\bClaude\b", re.IGNORECASE),
    re.compile(r"\bAI\b"),
    re.compile(r"\bassistant\b", re.IGNORECASE),
)

# Spanish denylist - Spanish-specific verbs and endings that do not appear
# in English technical commit messages. Non-exhaustive but covers Scenario
# 10 canonical case + high-frequency patterns that slip through.
#
# Tras MAGI Checkpoint 2 iter 2 (caspar): removidas palabras con alto riesgo
# de falso-positivo en ingles:
#   - `la`, `el`, `los`, `las`, `una`, `un` (demasiado comunes en siglas
#     inglesas como "LA" time zone, "el" en nombres propios).
#   - `para` solo (false positive en commit messages que mencionen
#     "parallel", "parametric", etc. via partial matches aun con \b -
#     mejor usar verbos Spanish-exclusive).
#   - `funcion` sin tilde (false positive en "function" partial; mejor
#     confiar en `parseador`/`agente` que son tokens uniquely-Spanish).
# Trade-off: menos recall de espanol, mejor precision para english-clean.
_SPANISH_DENYLIST: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bimplement(ar|acion|a|amos|e|en)\b", re.IGNORECASE),
    re.compile(r"\barregl(ar|a|amos|e|en|ado)\b", re.IGNORECASE),
    re.compile(r"\banadir\b", re.IGNORECASE),  # 'anadir' without tilde
    re.compile(r"\bcorrig(ir|io|iendo|iendo)\b", re.IGNORECASE),
    re.compile(r"\bagreg(ar|amos|ue|ando|ado)\b", re.IGNORECASE),
    re.compile(r"\b(parseador|agente)\b", re.IGNORECASE),  # Spanish-unique tokens
    re.compile(r"\b(nueva|nuevos|nuevas|ambos|ambas)\b", re.IGNORECASE),
    re.compile(r"\bdel\b", re.IGNORECASE),  # Spanish-only contraction
)

# Non-ASCII letter range (excludes ASCII punctuation, digits, whitespace).
_NON_ASCII_LETTERS = re.compile(r"[^\x00-\x7F]")


def validate_message(message: str) -> None:
    """Reject commit messages that violate INV-0 / INV-5..7.

    Checks (in order):
    1. Forbidden patterns: Co-Authored-By, Claude, AI, assistant.
    2. Non-ASCII letters (strong signal of non-English).
    3. Spanish denylist of common verbs and function words.

    Args:
        message: Full commit message (without prefix).

    Raises:
        ValidationError: If any check triggers.
    """
    for pattern in _FORBIDDEN_MESSAGE_PATTERNS:
        match = pattern.search(message)
        if match:
            raise ValidationError(
                f"commit message contains forbidden pattern '{match.group(0)}' "
                f"(INV-7, ~/.claude/CLAUDE.md Git section)"
            )
    non_ascii = _NON_ASCII_LETTERS.search(message)
    if non_ascii:
        raise ValidationError(
            f"commit message must be English - contains non-ASCII character "
            f"{non_ascii.group(0)!r} at position {non_ascii.start()} (INV-6)"
        )
    for pattern in _SPANISH_DENYLIST:
        match = pattern.search(message)
        if match:
            raise ValidationError(
                f"commit message must be English - detected Spanish word "
                f"'{match.group(0)}' (INV-6). Rewrite in English."
            )


def create(prefix: str, message: str, cwd: str | None = None) -> str:
    """Validate and create a git commit with `{prefix}: {message}`.

    Args:
        prefix: TDD-phase prefix (test/feat/fix/refactor/chore).
        message: Commit message body (will be prefixed with `{prefix}: `).
        cwd: Working directory for the git command.

    Returns:
        Output from `git commit` (stdout).

    Raises:
        ValidationError: If prefix invalid, or message contains forbidden
        patterns (Co-Authored-By, Claude/AI refs).
        RuntimeError: If git commit returns non-zero.
    """
    validate_prefix(prefix)
    validate_message(message)
    full_message = f"{prefix}: {message}"
    result = subprocess_utils.run_with_timeout(
        ["git", "commit", "-m", full_message],
        timeout=30,
        cwd=cwd,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git commit failed (returncode={result.returncode}): {result.stderr}")
    return result.stdout
