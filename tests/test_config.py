from pathlib import Path

import pytest
from dataclasses import FrozenInstanceError

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "plugin-locals"


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
        auto_max_spec_review_seconds=3600,
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
        auto_max_spec_review_seconds=3600,
        tdd_guard_enabled=True,
        worktree_policy="optional",
    )
    assert isinstance(cfg.verification_commands, tuple)


def test_load_valid_python_config():
    from config import load_plugin_local, PluginConfig

    cfg = load_plugin_local(FIXTURES_DIR / "valid-python.md")
    assert isinstance(cfg, PluginConfig)
    assert cfg.stack == "python"
    assert cfg.author == "Julian Bolivar"
    assert cfg.magi_max_iterations == 3
    assert cfg.auto_magi_max_iterations == 5
    assert isinstance(cfg.verification_commands, tuple)
    assert "pytest" in cfg.verification_commands


def test_load_missing_file():
    from config import load_plugin_local
    from errors import ValidationError

    with pytest.raises(ValidationError):
        load_plugin_local(Path("/nonexistent/path.md"))


def test_validate_rejects_invalid_stack(tmp_path):
    from config import load_plugin_local
    from errors import ValidationError

    content = """---
stack: ruby
author: "Test"
error_type: null
verification_commands:
  - "pytest"
plan_path: "p"
plan_org_path: "p"
spec_base_path: "s"
spec_path: "s"
state_file_path: ".claude/s.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---
"""
    f = tmp_path / "bad.md"
    f.write_text(content)
    with pytest.raises(ValidationError) as exc_info:
        load_plugin_local(f)
    assert "stack" in str(exc_info.value)


def test_validate_rejects_auto_magi_less_than_base():
    from config import load_plugin_local
    from errors import ValidationError

    # auto_magi_max_iterations must be >= magi_max_iterations (sec.S.4.3)
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""---
stack: python
author: "T"
error_type: null
verification_commands:
  - "pytest"
plan_path: "p"
plan_org_path: "p"
spec_base_path: "s"
spec_path: "s"
state_file_path: ".claude/s.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 5
auto_magi_max_iterations: 3
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---
""")
        path = f.name
    with pytest.raises(ValidationError) as exc_info:
        load_plugin_local(path)
    assert "auto_magi_max_iterations" in str(exc_info.value)


def test_plugin_config_new_observability_fields_have_defaults(tmp_path):
    """v0.5.0: 5 new PluginConfig fields with documented defaults."""
    config_path = tmp_path / "plugin.local.md"
    config_path.write_text("""---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest, "ruff check ."]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
---
""")
    from config import load_plugin_local
    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 900
    assert cfg.auto_heartbeat_interval_seconds == 15
    assert cfg.status_watch_default_interval_seconds == 1.0
    assert cfg.auto_origin_disambiguation is True
    assert cfg.auto_no_timeout_dispatch_labels == ("magi-*",)


def test_plugin_config_observability_fields_overridable(tmp_path):
    config_path = tmp_path / "plugin.local.md"
    config_path.write_text("""---
stack: python
author: Julian Bolivar
error_type: SBTDDError
verification_commands: [pytest]
plan_path: planning/claude-plan-tdd.md
plan_org_path: planning/claude-plan-tdd-org.md
spec_base_path: sbtdd/spec-behavior-base.md
spec_path: sbtdd/spec-behavior.md
state_file_path: .claude/session-state.json
magi_threshold: GO_WITH_CAVEATS
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 2
tdd_guard_enabled: true
worktree_policy: optional
auto_per_stream_timeout_seconds: 600
auto_heartbeat_interval_seconds: 30
status_watch_default_interval_seconds: 0.5
auto_origin_disambiguation: false
auto_no_timeout_dispatch_labels: ["magi-*", "long-build-*"]
---
""")
    from config import load_plugin_local
    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 600
    assert cfg.auto_heartbeat_interval_seconds == 30
    assert cfg.status_watch_default_interval_seconds == 0.5
    assert cfg.auto_origin_disambiguation is False
    assert cfg.auto_no_timeout_dispatch_labels == ("magi-*", "long-build-*")
