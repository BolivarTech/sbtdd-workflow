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
)

#: Allowed values for the headless `on_exhausted` policy in
#: `.claude/magi-auto-policy.json` (Feature A, v0.2 NF10).
AUTO_POLICIES: tuple[str, ...] = ("abort", "override_strong_go_only", "retry_once")
