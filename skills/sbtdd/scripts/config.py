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
import sys
from dataclasses import dataclass, field
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
    # v0.3.0 Feature E -- per-skill model selection (default None = inherit
    # session model, byte-identical argv to v0.2.x).
    implementer_model: str | None = None
    spec_reviewer_model: str | None = None
    code_review_model: str | None = None
    magi_dispatch_model: str | None = None
    # v0.5.0 observability fields (sec.4.3 of spec). Defaults documented in
    # docs/v0.5.0-config-matrix.md (R9 single-source-of-truth doc) and
    # cross-validated against INV-34 four-clause checks in load_plugin_local.
    auto_per_stream_timeout_seconds: int = 900
    auto_heartbeat_interval_seconds: int = 15
    status_watch_default_interval_seconds: float = 1.0
    auto_origin_disambiguation: bool = True
    auto_no_timeout_dispatch_labels: tuple[str, ...] = field(
        default_factory=lambda: ("magi-*",)
    )


#: Canonical names of the v0.3.0 Feature E model fields. Used both by the
#: typo-detection pass below and by the dispatch resolver in
#: :mod:`auto_cmd` (CLI override -> config -> None cascade).
_MODEL_FIELDS: tuple[str, ...] = (
    "implementer_model",
    "spec_reviewer_model",
    "code_review_model",
    "magi_dispatch_model",
)


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
    # v0.3.0 Feature E -- typo detection on model fields. Common mistake:
    # using ``implementer-model`` (YAML idiomatic dash) instead of
    # ``implementer_model`` (Python attribute). Emit a warning and drop
    # the bogus key so PluginConfig(**data) does not raise on unknown kw.
    for key in list(data.keys()):
        if "-" in key and key.replace("-", "_") in _MODEL_FIELDS:
            sys.stderr.write(
                f"[sbtdd] unknown plugin.local.md key: {key} -- did you mean "
                f"{key.replace('-', '_')}?\n"
            )
            data.pop(key)
    # v0.3.0 Feature E -- per-skill model fields (optional). Validate
    # type when present so a malformed value (e.g. integer, list) does
    # not propagate to the dispatcher.
    for field_name in _MODEL_FIELDS:
        val = data.get(field_name)
        if val is not None and not isinstance(val, str):
            raise ValidationError(
                f"{field_name} must be a string or null, got {type(val).__name__}"
            )
    # v0.5.0 observability defaults applied if absent (sec.4.3 of spec).
    data.setdefault("auto_per_stream_timeout_seconds", 900)
    data.setdefault("auto_heartbeat_interval_seconds", 15)
    data.setdefault("status_watch_default_interval_seconds", 1.0)
    data.setdefault("auto_origin_disambiguation", True)
    data.setdefault("auto_no_timeout_dispatch_labels", ["magi-*"])
    if isinstance(data.get("auto_no_timeout_dispatch_labels"), list):
        data["auto_no_timeout_dispatch_labels"] = tuple(
            data["auto_no_timeout_dispatch_labels"]
        )
    # INV-34 (sec.2.7 of spec): timeout-vs-interval relationship + absolute
    # floor + ceiling validations. Validation order is 1 -> 2 -> 3 -> 4
    # because each test fixture (test_inv34_clause_N_*) varies ONE clause
    # while keeping the others at safe defaults; the most-specific clause
    # fires first under those fixtures so error messages name the violated
    # invariant uniquely.
    #
    # W1 (Checkpoint 2 iter 4 melchior + caspar): clause 1 is mathematically
    # subsumed by clauses 2 + 4 in the current default range
    # (timeout >= 600 AND interval <= 60 implies 5 * interval <= 300 <= timeout).
    # We preserve clause 1 explicitly as DEFENSE-IN-DEPTH against future
    # weakening of clauses 2 or 4 that could make clause 1 the only barrier.
    # See docs/v0.5.0-config-matrix.md for the worked-example table.
    timeout = data["auto_per_stream_timeout_seconds"]
    interval = data["auto_heartbeat_interval_seconds"]
    if not isinstance(timeout, int) or timeout < 0:
        raise ValidationError(
            f"auto_per_stream_timeout_seconds must be int >= 0, got {timeout!r}"
        )
    if not isinstance(interval, int) or interval < 0:
        raise ValidationError(
            f"auto_heartbeat_interval_seconds must be int >= 0, got {interval!r}"
        )
    # Clause 1 (ratio) checked first so fixtures targeting the ratio
    # report the ratio violation rather than masking it with clause 4.
    if timeout < 5 * interval:
        raise ValidationError(
            f"INV-34 clause 1: auto_per_stream_timeout_seconds ({timeout}) "
            f"must be >= 5 * auto_heartbeat_interval_seconds ({interval}) "
            f"= {5 * interval}; got {timeout}"
        )
    if interval > 60:
        raise ValidationError(
            f"INV-34 clause 2: auto_heartbeat_interval_seconds must be <= 60s "
            f"to keep operator awareness within 1-minute granularity; got {interval}"
        )
    if interval < 5:
        raise ValidationError(
            f"INV-34 clause 3: auto_heartbeat_interval_seconds must be >= 5s "
            f"to avoid stderr spam without value; got {interval}"
        )
    if timeout < 600:
        raise ValidationError(
            f"INV-34 clause 4: auto_per_stream_timeout_seconds must be >= 600s "
            f"(caspar opus runs observed empirically up to 10min); got {timeout}"
        )
    try:
        return PluginConfig(**data)
    except TypeError as exc:
        raise ValidationError(f"schema mismatch in {p}: {exc}") from exc
