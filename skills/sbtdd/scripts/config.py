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

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml  # PyYAML — authorized by CLAUDE.md ("runtime dependencies allowed
# where unavoidable (config.py parses YAML frontmatter …
# acceptable since it runs only at session start and init)").
# Per MAGI Checkpoint 2 iter 1 (balthasar): replaces the brittle
# custom parser of the draft plan.

from errors import ValidationError

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*", re.DOTALL)


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
    auto_max_spec_review_seconds: int
    tdd_guard_enabled: bool
    worktree_policy: Literal["optional", "required"]


def load_plugin_local(path: Path | str) -> PluginConfig:
    """Parse .claude/plugin.local.md and validate against sec.S.4.2.

    Args:
        path: Path to plugin.local.md.

    Returns:
        PluginConfig instance.

    Raises:
        ValidationError: If file missing, malformed frontmatter, or any
        schema constraint violated.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"plugin.local.md not found: {p}") from exc
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValidationError(f"no YAML frontmatter in {p}")
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ValidationError(f"invalid YAML frontmatter in {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(
            f"YAML frontmatter in {p} must be a mapping, got {type(data).__name__}"
        )
    # Convert verification_commands list → tuple for immutability.
    if isinstance(data.get("verification_commands"), list):
        data["verification_commands"] = tuple(data["verification_commands"])
    # Semantic validation beyond type-checking (sec.S.4.3).
    valid_stacks = {"rust", "python", "cpp"}
    if data.get("stack") not in valid_stacks:
        raise ValidationError(f"stack='{data.get('stack')}' not in {sorted(valid_stacks)}")
    valid_thresholds = {"STRONG_GO", "GO", "GO_WITH_CAVEATS"}
    if data.get("magi_threshold") not in valid_thresholds:
        raise ValidationError(
            f"magi_threshold='{data.get('magi_threshold')}' not in {sorted(valid_thresholds)}"
        )
    valid_policies = {"optional", "required"}
    if data.get("worktree_policy") not in valid_policies:
        raise ValidationError(
            f"worktree_policy='{data.get('worktree_policy')}' not in {sorted(valid_policies)}"
        )
    mag = data.get("magi_max_iterations")
    auto_mag = data.get("auto_magi_max_iterations")
    if not isinstance(mag, int) or mag < 1:
        raise ValidationError(f"magi_max_iterations must be int >= 1, got {mag!r}")
    if not isinstance(auto_mag, int) or auto_mag < mag:
        raise ValidationError(
            f"auto_magi_max_iterations ({auto_mag}) must be int >= magi_max_iterations ({mag})"
        )
    retries = data.get("auto_verification_retries")
    if not isinstance(retries, int) or retries < 0:
        raise ValidationError(f"auto_verification_retries must be int >= 0, got {retries!r}")
    # auto_max_spec_review_seconds: cumulative wall-time budget for the
    # spec-reviewer in /sbtdd auto. Default 3600s (1h) per v0.2.1 brief
    # so plugin.local.md files written by older inits still load. Once
    # the budget is exhausted, _phase2_task_loop skips dispatch_spec_reviewer
    # for the remaining tasks (cost guardrail; INV-22 / INV-26).
    budget = data.get("auto_max_spec_review_seconds", 3600)
    if not isinstance(budget, int) or budget < 0:
        raise ValidationError(f"auto_max_spec_review_seconds must be int >= 0, got {budget!r}")
    data["auto_max_spec_review_seconds"] = budget
    if not isinstance(data.get("verification_commands"), tuple):
        raise ValidationError("verification_commands must be a non-empty list")
    if len(data["verification_commands"]) == 0:
        raise ValidationError("verification_commands must be non-empty")
    try:
        return PluginConfig(**data)
    except TypeError as exc:
        raise ValidationError(f"schema mismatch in {p}: {exc}") from exc
