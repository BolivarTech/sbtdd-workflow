import pytest
from dataclasses import FrozenInstanceError


def test_plugin_config_is_frozen():
    from config import PluginConfig

    cfg = PluginConfig(
        stack="python",
        author="Test",
        error_type=None,
        verification_commands=("pytest", "ruff check ."),
        plan_path="planning/claude-plan-tdd.md",
        plan_org_path="planning/claude-plan-tdd-org.md",
        spec_base_path="sbtdd/spec-behavior-base.md",
        spec_path="sbtdd/spec-behavior.md",
        state_file_path=".claude/session-state.json",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        auto_magi_max_iterations=5,
        auto_verification_retries=1,
        tdd_guard_enabled=True,
        worktree_policy="optional",
    )
    with pytest.raises(FrozenInstanceError):
        cfg.stack = "rust"  # type: ignore[misc]


def test_plugin_config_verification_commands_is_tuple():
    from config import PluginConfig

    cfg = PluginConfig(
        stack="python",
        author="Test",
        error_type=None,
        verification_commands=("pytest",),
        plan_path="",
        plan_org_path="",
        spec_base_path="",
        spec_path="",
        state_file_path="",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        auto_magi_max_iterations=5,
        auto_verification_retries=1,
        tdd_guard_enabled=True,
        worktree_policy="optional",
    )
    assert isinstance(cfg.verification_commands, tuple)
