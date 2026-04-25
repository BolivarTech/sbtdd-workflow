#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.3.0 Feature E PluginConfig model field extension."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

from config import load_plugin_local


def _write_minimal_plugin_local(tmp_path: Path, extra: str = "") -> Path:
    p = tmp_path / "plugin.local.md"
    p.write_text(
        "---\n"
        "stack: python\n"
        "author: Test\n"
        "error_type: TestError\n"
        "verification_commands:\n"
        "  - pytest\n"
        "plan_path: planning/claude-plan-tdd.md\n"
        "plan_org_path: planning/claude-plan-tdd-org.md\n"
        "spec_base_path: sbtdd/spec-behavior-base.md\n"
        "spec_path: sbtdd/spec-behavior.md\n"
        "state_file_path: .claude/session-state.json\n"
        "magi_threshold: GO_WITH_CAVEATS\n"
        "magi_max_iterations: 3\n"
        "auto_magi_max_iterations: 5\n"
        "auto_verification_retries: 2\n"
        "auto_max_spec_review_seconds: 3600\n"
        "tdd_guard_enabled: true\n"
        "worktree_policy: optional\n"
        f"{extra}"
        "---\n# rules\n",
        encoding="utf-8",
    )
    return p


def test_v02_plugin_local_loads_with_model_fields_default_none(tmp_path: Path) -> None:
    """E1.2: v0.2 plugin.local.md (no model fields) loads with defaults."""
    p = _write_minimal_plugin_local(tmp_path)
    cfg = load_plugin_local(p)
    assert cfg.implementer_model is None
    assert cfg.spec_reviewer_model is None
    assert cfg.code_review_model is None
    assert cfg.magi_dispatch_model is None


def test_4_model_fields_parsed_from_plugin_local(tmp_path: Path) -> None:
    """E1.1: all 4 model fields parsed when present in YAML."""
    extra = (
        "implementer_model: claude-sonnet-4-6\n"
        "spec_reviewer_model: claude-haiku-4-5\n"
        "code_review_model: claude-sonnet-4-6\n"
        "magi_dispatch_model: null\n"
    )
    p = _write_minimal_plugin_local(tmp_path, extra=extra)
    cfg = load_plugin_local(p)
    assert cfg.implementer_model == "claude-sonnet-4-6"
    assert cfg.spec_reviewer_model == "claude-haiku-4-5"
    assert cfg.code_review_model == "claude-sonnet-4-6"
    assert cfg.magi_dispatch_model is None


def test_typo_in_model_field_emits_warning(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """E1.3: dash-typo'd YAML key triggers warning, defaults None."""
    extra = "implementer-model: claude-sonnet-4-6\n"
    p = _write_minimal_plugin_local(tmp_path, extra=extra)
    cfg = load_plugin_local(p)
    captured = capfd.readouterr()
    assert cfg.implementer_model is None
    assert "did you mean implementer_model" in captured.err
