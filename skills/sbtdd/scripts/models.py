#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Immutable registries for sbtdd-workflow plugin.

Single source of truth for commit prefixes, MAGI verdict ranks, and the
list of valid subcommand names. All registries are exposed as
MappingProxyType or tuple to prevent runtime mutation (sec.S.8.5).
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Mapping

_COMMIT_PREFIX_MAP_MUTABLE: dict[str, str] = {
    "red": "test",
    "green_feat": "feat",
    "green_fix": "fix",
    "refactor": "refactor",
    "task_close": "chore",
}

#: Read-only TDD phase → git commit prefix mapping (sec.M.5).
COMMIT_PREFIX_MAP: Mapping[str, str] = MappingProxyType(_COMMIT_PREFIX_MAP_MUTABLE)

_VERDICT_RANK_MUTABLE: dict[str, int] = {
    "STRONG_NO_GO": 0,
    "HOLD": 1,
    "HOLD_TIE": 2,
    "GO_WITH_CAVEATS": 3,
    "GO": 4,
    "STRONG_GO": 5,
}

#: Read-only MAGI verdict label → integer rank mapping (sec.S.11.1 + CLAUDE.md crossfile).
VERDICT_RANK: Mapping[str, int] = MappingProxyType(_VERDICT_RANK_MUTABLE)


def verdict_meets_threshold(verdict: str, threshold: str) -> bool:
    """Return True if ``verdict`` is at least as strong as ``threshold``.

    Both arguments must be keys of :data:`VERDICT_RANK`.

    Args:
        verdict: MAGI verdict label produced by the consensus synthesis.
        threshold: Minimum acceptable verdict label from plugin.local.md.

    Returns:
        True if ``VERDICT_RANK[verdict] >= VERDICT_RANK[threshold]``.

    Raises:
        KeyError: If either argument is not a known verdict label.
    """
    return VERDICT_RANK[verdict] >= VERDICT_RANK[threshold]


#: Ordered tuple of all valid subcommand names (sec.S.2.2 inventario).
VALID_SUBCOMMANDS: tuple[str, ...] = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
    "review-spec-compliance",
)

#: Allowed values for the headless `on_exhausted` policy in
#: `.claude/magi-auto-policy.json` (Feature A, v0.2 NF10).
AUTO_POLICIES: tuple[str, ...] = ("abort", "override_strong_go_only", "retry_once")


#: Claude model IDs the plugin recognizes as valid for ``--model`` arg
#: passing in dispatch wrappers. v0.3.0 ships the 4.x family snapshot
#: (Opus 4.7, Sonnet 4.6, Haiku 4.5). Bump this tuple when Anthropic
#: ships a new family; update SKILL.md operational impact accordingly.
ALLOWED_CLAUDE_MODEL_IDS: tuple[str, ...] = (
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
    "claude-haiku-4-5-20251001",
)


#: Regex used by superpowers_dispatch / magi_dispatch to detect when the
#: developer's global ``~/.claude/CLAUDE.md`` pins a Claude model
#: explicitly. INV-0 cascade: if the global file pins, plugin.local.md
#: model fields are ignored and a stderr breadcrumb is emitted. The
#: regex matches phrases like ``use claude-X-Y for``, ``pin claude-X-Y``,
#: or ``always claude-X-Y``. Word-boundary anchored to avoid false
#: positives in narrative prose.
INV_0_PINNED_MODEL_RE: "re.Pattern[str]" = re.compile(
    r"\b(?:use|pin|pinned|always|stick to|enforce)\s+"
    r"(claude-(?:opus|sonnet|haiku)-\d+(?:-\d+)?(?:-\d{8})?)\b",
    re.IGNORECASE,
)
