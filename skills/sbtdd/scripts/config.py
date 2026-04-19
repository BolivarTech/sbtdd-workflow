#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""plugin.local.md YAML frontmatter parser (sec.S.4.2 schema).

PluginConfig is a frozen dataclass with one attribute per field of the
schema. load_plugin_local validates the YAML frontmatter and returns
an instance; any schema violation raises ValidationError.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PluginConfig:
    """Parsed configuration from .claude/plugin.local.md (sec.S.4.2)."""

    stack: Literal["rust", "python", "cpp"]
    author: str
    error_type: str | None
    verification_commands: tuple[str, ...]
    plan_path: str
    plan_org_path: str
    spec_base_path: str
    spec_path: str
    state_file_path: str
    magi_threshold: Literal["STRONG_GO", "GO", "GO_WITH_CAVEATS"]
    magi_max_iterations: int
    auto_magi_max_iterations: int
    auto_verification_retries: int
    tdd_guard_enabled: bool
    worktree_policy: Literal["optional", "required"]
