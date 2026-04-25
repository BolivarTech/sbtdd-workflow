#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E dependency_check.check_model_ids."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import dependency_check
from config import PluginConfig


def _cfg_with(
    implementer: str | None = None,
    spec_reviewer: str | None = None,
    code_review: str | None = None,
    magi_dispatch: str | None = None,
) -> PluginConfig:
    return PluginConfig(
        stack="python",
        author="t",
        error_type=None,
        verification_commands=("pytest",),
        plan_path="planning/claude-plan-tdd.md",
        plan_org_path="planning/claude-plan-tdd-org.md",
        spec_base_path="sbtdd/spec-behavior-base.md",
        spec_path="sbtdd/spec-behavior.md",
        state_file_path=".claude/session-state.json",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        auto_magi_max_iterations=5,
        auto_verification_retries=2,
        auto_max_spec_review_seconds=3600,
        tdd_guard_enabled=True,
        worktree_policy="optional",
        implementer_model=implementer,
        spec_reviewer_model=spec_reviewer,
        code_review_model=code_review,
        magi_dispatch_model=magi_dispatch,
    )


def test_check_model_ids_warns_on_unknown_at_init() -> None:
    """E5.1: unknown model in PluginConfig returns OK status with warning detail.

    The check must not fail (status='OK') so init does not abort on a
    legitimately-fresh model ID Anthropic released between plugin
    versions; the runtime dispatch is the hard-fail path.
    """
    cfg = _cfg_with(implementer="claude-sonnet-9-9")
    result = dependency_check.check_model_ids(cfg)
    assert result.status == "OK"  # warning, not failure
    assert "claude-sonnet-9-9" in result.detail
    assert "implementer_model" in result.detail
    assert "verify spelling" in result.detail.lower()


def test_check_model_ids_passes_on_known() -> None:
    """E5.1 inverse: known model returns clean OK DependencyCheck."""
    cfg = _cfg_with(implementer="claude-sonnet-4-6")
    result = dependency_check.check_model_ids(cfg)
    assert result.status == "OK"
    # Detail should NOT mention 'unknown' for the clean path.
    assert "unknown" not in result.detail.lower()


def test_check_model_ids_passes_on_all_none() -> None:
    """Default-none config returns clean OK (no fields to check)."""
    cfg = _cfg_with()
    result = dependency_check.check_model_ids(cfg)
    assert result.status == "OK"


def test_check_model_ids_aggregates_multiple_unknown() -> None:
    """Multiple unknown model fields surface together in detail message."""
    cfg = _cfg_with(implementer="claude-foo-9-9", spec_reviewer="claude-bar-8-8")
    result = dependency_check.check_model_ids(cfg)
    assert result.status == "OK"  # still warning, not BROKEN
    assert "claude-foo-9-9" in result.detail
    assert "claude-bar-8-8" in result.detail
    assert "implementer_model" in result.detail
    assert "spec_reviewer_model" in result.detail


def test_check_model_ids_module_export() -> None:
    """check_model_ids is a top-level export of dependency_check (init wires it)."""
    assert hasattr(dependency_check, "check_model_ids")
    assert callable(dependency_check.check_model_ids)


def test_check_model_ids_returns_dependency_check_type() -> None:
    """Return value is the canonical DependencyCheck dataclass."""
    cfg = _cfg_with(implementer="claude-sonnet-4-6")
    result = dependency_check.check_model_ids(cfg)
    assert isinstance(result, dependency_check.DependencyCheck)
    assert result.name == "model_ids"
