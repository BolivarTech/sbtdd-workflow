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


def test_inv34_clause_1_subsumed_under_clauses_2_4(tmp_path):
    """Loop 2 WARNING #1/#7: clause 1 is mathematically subsumed.

    Pre-fix this test exercised a fixture (timeout=50, interval=15) that was
    intended to violate clause 1 in isolation. After the spec PINNED order
    fix (clauses checked 4 -> 2 -> 3 -> 1), the same fixture fires clause 4
    first because 50 < 600. Clause 1 cannot be violated alone when clauses
    2 + 4 are satisfied: ``5 * interval <= 5 * 60 = 300 <= 600 <= timeout``,
    so any timeout that satisfies clause 4 (>= 600) and any interval that
    satisfies clause 2 (<= 60) automatically satisfies clause 1.

    This test documents that subsumption explicitly via two checks:

    1. The original ``timeout=50, interval=15`` fixture now reports clause 4
       (the structurally-first failing predicate under the spec PINNED order),
       confirming clause 1 cannot fire alone.
    2. A boundary fixture (``timeout=600, interval=60``) satisfies clauses
       2-4 simultaneously and consequently clause 1 is also satisfied; the
       config loads cleanly. Removing clause 1 from the implementation
       would NOT cause this fixture to fail -- but the implementation
       retains clause 1 as defense-in-depth against future weakening of
       clauses 2 or 4.

    See ``docs/v0.5.0-config-matrix.md`` `W1` section for the worked example.
    """
    base = """---
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
"""
    config_path = tmp_path / "p1.md"
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 50\nauto_heartbeat_interval_seconds: 15\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError

    # Spec PINNED order is 4 -> 2 -> 3 -> 1; the original clause-1-only
    # fixture now reports clause 4 (fires first because 50 < 600).
    with pytest.raises(ValidationError, match="INV-34 clause 4"):
        load_plugin_local(config_path)

    # Boundary fixture: satisfies clauses 2 (60 <= 60), 3 (60 >= 5),
    # 4 (600 >= 600), and consequently 1 (600 == 5 * 60). Loads cleanly.
    config_path2 = tmp_path / "p1_boundary.md"
    config_path2.write_text(
        base + "auto_per_stream_timeout_seconds: 600\nauto_heartbeat_interval_seconds: 60\n---\n"
    )
    cfg = load_plugin_local(config_path2)
    assert cfg.auto_per_stream_timeout_seconds == 600
    assert cfg.auto_heartbeat_interval_seconds == 60


def test_inv34_clause_2_ceiling_violation(tmp_path):
    base = """---
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
"""
    config_path = tmp_path / "p2.md"
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 1000\nauto_heartbeat_interval_seconds: 120\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError

    with pytest.raises(ValidationError, match="INV-34 clause 2"):
        load_plugin_local(config_path)


def test_inv34_clause_3_floor_violation(tmp_path):
    base = """---
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
"""
    config_path = tmp_path / "p3.md"
    # Spec PINNED order 4 -> 2 -> 3 -> 1: fixture must satisfy clauses 4
    # (timeout >= 600) and 2 (interval <= 60) so clause 3 is the first
    # failing predicate. timeout=900 satisfies 4 + 1; interval=2 violates 3.
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 900\nauto_heartbeat_interval_seconds: 2\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError

    with pytest.raises(ValidationError, match="INV-34 clause 3"):
        load_plugin_local(config_path)


def test_inv34_clause_1_boundary_timeout_equals_5x_interval_accepts(tmp_path):
    """Boundary: timeout == 5 * interval is accepted (>= ratio satisfied)."""
    base = """---
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
"""
    config_path = tmp_path / "boundary.md"
    # 600s = max(5*60, 600) = 600 -- boundary of clauses 1 AND 4.
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 600\nauto_heartbeat_interval_seconds: 60\n---\n"
    )
    from config import load_plugin_local

    cfg = load_plugin_local(config_path)
    assert cfg.auto_per_stream_timeout_seconds == 600
    assert cfg.auto_heartbeat_interval_seconds == 60


def test_inv34_clause_4_timeout_below_600_rejected(tmp_path):
    """Clause 4: timeout < 600s rejected even if clauses 1-3 satisfied."""
    base = """---
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
"""
    config_path = tmp_path / "p4.md"
    # 75s satisfies clause 1 (5*15=75) but violates clause 4 (>=600).
    config_path.write_text(
        base + "auto_per_stream_timeout_seconds: 75\nauto_heartbeat_interval_seconds: 15\n---\n"
    )
    from config import load_plugin_local
    from errors import ValidationError

    with pytest.raises(ValidationError, match="INV-34 clause 4"):
        load_plugin_local(config_path)


def test_allowlist_bare_wildcard_rejected(tmp_path):
    base = """---
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
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
"""
    from config import load_plugin_local
    from errors import ValidationError

    config_path = tmp_path / "p.md"
    config_path.write_text(base + 'auto_no_timeout_dispatch_labels: ["*"]\n---\n')
    with pytest.raises(ValidationError, match=r"bare '\*' rejected"):
        load_plugin_local(config_path)


def test_allowlist_empty_string_rejected(tmp_path):
    """Empty string in allowlist would also defeat timeout — rejected."""
    base = """---
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
auto_per_stream_timeout_seconds: 900
auto_heartbeat_interval_seconds: 15
"""
    from config import load_plugin_local
    from errors import ValidationError

    config_path = tmp_path / "p.md"
    config_path.write_text(base + 'auto_no_timeout_dispatch_labels: ["", "magi-*"]\n---\n')
    with pytest.raises(ValidationError, match=r"bare '\*' rejected"):
        load_plugin_local(config_path)
