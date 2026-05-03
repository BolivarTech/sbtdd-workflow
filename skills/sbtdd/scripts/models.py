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
from dataclasses import dataclass
from datetime import datetime
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
#: model fields are ignored and a stderr breadcrumb is emitted.
#:
#: v0.3.0 hotfix (MAGI iter 1 findings #3 + #8): the original
#: verb-only form ``\b(?:use|pin|...)\s+claude-...\b`` had a real
#: false-positive surface in narrative prose -- "don't use
#: claude-opus-4-7", "we always use claude-sonnet-4-6 in this codebase
#: notes", "for example, use claude-haiku-4-5 to optimize cost" all
#: matched and silently downgraded plugin.local.md to session default.
#:
#: The fix requires a pinning suffix immediately after the model id:
#: one of ``globally``, ``for all sessions``, ``as default``,
#: ``as the (default|fixed|pinned) model``, ``across all sessions``,
#: ``in every session``, ``for every session``. This keeps the regex
#: cheap (single-pass on CLAUDE.md text), case-insensitive, and word-
#: boundary anchored, while eliminating the narrative-prose surface.
#:
#: Operators who want to pin a model must use one of those imperatives
#: (e.g. ``Use claude-opus-4-7 for all sessions``). The README and
#: SKILL.md cost-optimization sections document the canonical phrases.
INV_0_PINNED_MODEL_RE: "re.Pattern[str]" = re.compile(
    r"\b(?:use|pin|pinned|always|stick to|enforce)\s+"
    r"(claude-(?:opus|sonnet|haiku)-\d+(?:-\d+)?(?:-\d{8})?)"
    # Required pinning suffix follows immediately (allowing the optional
    # verb ``as`` between the model id and the suffix nominal).
    r"(?:\s+(?:"
    r"globally"
    r"|for\s+all\s+sessions"
    r"|across\s+all\s+sessions"
    r"|in\s+every\s+session"
    r"|for\s+every\s+session"
    r"|as\s+default"
    r"|as\s+the\s+(?:default|fixed|pinned)\s+model"
    r"))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ProgressContext:
    """Immutable snapshot of auto-run progress (sec.3 of v0.5.0 spec).

    Reader/writer protocol pinned in spec sec.3:

    - Writer (:mod:`auto_cmd` main thread) creates a NEW
      ``ProgressContext`` per phase / task / dispatch transition and
      assigns to the module-level singleton via the lock-protected
      setter in :mod:`heartbeat`.
    - Reader (HeartbeatEmitter daemon thread) calls
      :func:`heartbeat.get_current_progress` to read; the returned
      snapshot is immutable so no further locking is required.

    The ``started_at`` field tracks the **current dispatch's** start
    time, NOT the phase start nor the overall auto-run start.
    Heartbeat ticks render ``elapsed=`` relative to this dispatch.

    Serialization to ``.claude/auto-run.json`` uses ISO 8601 UTC with
    the ``Z`` suffix (e.g. ``"2026-05-01T12:34:56Z"``).
    """

    iter_num: int = 0
    phase: int = 0
    task_index: int | None = None
    task_total: int | None = None
    dispatch_label: str | None = None
    started_at: datetime | None = None


@dataclass(frozen=True)
class ResolvedModels:
    """Cached preflight resolution of per-skill model IDs (spec sec.5.1).

    Resolved once at task-loop entry per auto run via
    :func:`auto_cmd._resolve_all_models_once`. All dispatches read from
    this cache instead of re-resolving CLAUDE.md + plugin.local.md
    (~70-150 disk reads per 36-task run reduced to 1).

    INV-0 cascade order (caspar Loop 2 iter 3 CRITICAL fix -- enforces
    ``~/.claude/CLAUDE.md`` *maxima precedencia* per INV-0): the global
    ``~/.claude/CLAUDE.md`` is consulted FIRST; if it pins a model
    (regex match against :data:`INV_0_PINNED_MODEL_RE`), it wins (INV-0
    *maxima precedencia* is non-negotiable -- the global rule cannot be
    silently overridden by a project file). The project ``<repo>/CLAUDE.md``
    is consulted SECOND, only when the global file is absent or has no
    pin. The first file with a regex match terminates the cascade.
    Neither pinned ⇒ fall through to ``plugin.local.md`` per-skill
    fields. When both files have INV-0 pins for *different* models, two
    stderr breadcrumbs fire: the regular cascade message documenting
    the global-pin source AND a shadow message
    ``[sbtdd] INV-0 cascade: global pin <X> OVERRIDES project pin <Y>;
    project pin shadowed (per INV-0 maxima precedencia)``. Same-pin
    case suppresses the shadow message (no surprise to surface).

    The dataclass is frozen so resolved IDs cannot be mutated after
    preflight; consumers in :mod:`auto_cmd` and :mod:`pre_merge_cmd`
    rely on the immutability invariant for thread-safety during the
    task-loop.

    Cross-subagent contract (spec sec.5.1, sec.9.1): this dataclass is
    OWNED by Subagent #2; consumers under Subagent #1 (``auto_cmd``,
    ``pre_merge_cmd``, ``magi_dispatch``, ``status_cmd``) MUST NOT be
    imported by this module at module-load time -- the deferred-import
    test in :mod:`tests.test_models` enforces the contract.
    """

    implementer: str
    spec_reviewer: str
    code_review: str
    magi_dispatch: str
