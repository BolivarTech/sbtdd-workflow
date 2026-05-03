from __future__ import annotations

import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_settings_json_template_exists():
    assert (TEMPLATES_DIR / "settings.json.template").exists()


def test_settings_json_template_is_valid_json():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_settings_json_template_has_three_required_hooks():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    assert set(hooks.keys()) == {"PreToolUse", "UserPromptSubmit", "SessionStart"}


def test_settings_json_template_pretool_has_write_matcher():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    pretool = data["hooks"]["PreToolUse"]
    assert len(pretool) >= 1
    entry = pretool[0]
    assert entry["matcher"] == "Write|Edit|MultiEdit|TodoWrite"
    assert entry["hooks"][0]["command"] == "tdd-guard"


def test_settings_json_template_session_start_has_startup_matcher():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    session = data["hooks"]["SessionStart"]
    assert session[0]["matcher"] == "startup|resume|clear"
    assert session[0]["hooks"][0]["command"] == "tdd-guard"


def test_settings_json_template_user_prompt_has_tdd_guard():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    ups = data["hooks"]["UserPromptSubmit"]
    assert ups[0]["hooks"][0]["command"] == "tdd-guard"


def test_plugin_local_template_exists():
    assert (TEMPLATES_DIR / "plugin.local.md.template").exists()


def test_plugin_local_template_loads_as_plugin_config():
    """After placeholder expansion, the file must parse via config.load_plugin_local."""
    from config import load_plugin_local
    from templates import expand

    raw = (TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    context = {
        "stack": "python",
        "author": "Test Author",
        "error_type": "null",
    }
    expanded = expand(raw, context)
    import tempfile
    from pathlib import Path as _P

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fp:
        fp.write(expanded)
        tmp = _P(fp.name)
    try:
        cfg = load_plugin_local(tmp)
        assert cfg.stack == "python"
        assert cfg.author == "Test Author"
        assert cfg.magi_threshold == "GO_WITH_CAVEATS"
        assert cfg.magi_max_iterations == 3
        assert cfg.auto_magi_max_iterations >= cfg.magi_max_iterations
    finally:
        tmp.unlink()


def test_claude_local_template_exists():
    assert (TEMPLATES_DIR / "CLAUDE.local.md.template").exists()


def test_claude_local_template_placeholders_present():
    """Placeholders are lowercase snake_case matching PluginConfig fields.

    MAGI Loop 2 Milestone B iter 1 Finding 3 (caspar): convention aligned
    with plugin.local.md.template so Milestone C init_cmd can build the
    expansion context from ``dataclasses.asdict(config)`` directly.
    """
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    for placeholder in ("{author}", "{error_type}", "{stack}"):
        assert placeholder in raw, (
            f"placeholder {placeholder} missing from CLAUDE.local.md.template"
        )


def test_claude_local_template_expands_without_residual_placeholders():
    from templates import expand

    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    out = expand(
        raw,
        {
            "author": "Julian Bolivar",
            "error_type": "MyErr",
            "stack": "python",
            "verification_commands": "pytest / ruff / mypy",
        },
    )
    assert "{author}" not in out
    assert "{error_type}" not in out
    assert "{stack}" not in out
    assert "Julian Bolivar" in out


def test_claude_local_template_contains_no_uppercase_markers():
    """INV-27 spec placeholder rejection applies to templates as well."""
    import re

    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    assert not re.search(r"\bTODO\b", raw)
    assert not re.search(r"\bTODOS\b", raw)
    assert not re.search(r"\bTBD\b", raw)


def test_claude_local_template_references_verification_section():
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    # Must reference the verification commands section (sec.0.1 in destination).
    assert "0.1" in raw or "verification" in raw.lower()


def test_spec_behavior_base_template_exists():
    assert (TEMPLATES_DIR / "spec-behavior-base.md.template").exists()


def test_spec_behavior_base_template_no_uppercase_markers():
    """INV-27: spec-behavior-base.md.template must not contain the three pending-marker words."""
    import re

    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    assert not re.search(r"\bTODO\b", raw)
    assert not re.search(r"\bTODOS\b", raw)
    assert not re.search(r"\bTBD\b", raw)


def test_spec_behavior_base_template_has_replace_markers():
    """Skeleton uses <REPLACE: ...> markers (not the uppercase pending words) to indicate user edits."""
    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    assert "<REPLACE:" in raw


def test_spec_behavior_base_template_has_sbtdd_sections():
    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    for section in ("Objetivo", "Requerimientos", "Escenarios", "Restricciones"):
        assert section in raw, f"section '{section}' missing from spec template"


def test_conftest_template_exists():
    assert (TEMPLATES_DIR / "conftest.py.template").exists()


def test_conftest_template_has_sbtdd_markers():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert "# --- SBTDD TDD-Guard reporter START ---" in raw
    assert "# --- SBTDD TDD-Guard reporter END ---" in raw


def test_conftest_template_has_required_pytest_hooks():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    for hook in (
        "pytest_sessionstart",
        "pytest_sessionfinish",
        "pytest_runtest_makereport",
    ):
        assert hook in raw


def test_conftest_template_writes_to_expected_test_json_path():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert ".claude/tdd-guard/data/test.json" in raw or (
        ".claude" in raw and "tdd-guard" in raw and "test.json" in raw
    )


def test_conftest_template_is_valid_python(tmp_path):
    import ast

    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    # Must parse cleanly as Python — no placeholders that break syntax.
    ast.parse(raw)


def test_conftest_template_has_author_header():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert "# Author:" in raw
    assert "# Version:" in raw
    assert "# Date:" in raw


def test_gitignore_fragment_exists():
    assert (TEMPLATES_DIR / "gitignore.fragment").exists()


def test_gitignore_fragment_contains_required_entries():
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    required = [
        ".claude/",
        "CLAUDE.local.md",
    ]
    for entry in required:
        assert entry in raw, f".gitignore fragment missing {entry}"


def test_gitignore_fragment_ends_with_newline():
    """Fragment should end with newline so append concatenation doesn't join lines."""
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    assert raw.endswith("\n")


def test_gitignore_fragment_has_header_comment():
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    # A comment identifies the fragment so a reader knows where the entries came from.
    assert "SBTDD" in raw or "sbtdd" in raw


def test_all_templates_expand_cleanly_from_snake_case_context():
    """Every template expands to zero residual ``{...}`` tokens from PluginConfig-shaped context.

    MAGI Loop 2 Milestone B iter 1 Finding 3 (caspar, WARNING): the
    placeholder convention is snake_case matching PluginConfig field
    names. Any PascalCase placeholder (eg. ``{Author}``, ``{ErrorType}``)
    would survive expansion when Milestone C ``init_cmd`` builds the
    context from ``dataclasses.asdict(config)`` and silently leave
    literal tokens in the generated project files. This test locks the
    convention: a canonical snake_case context must yield zero residual
    ``{identifier}`` tokens in every template under ``templates/``.
    """
    import re

    from templates import expand

    context = {
        # PluginConfig fields (snake_case).
        "stack": "python",
        "author": "Test Author",
        "error_type": "TestErr",
        "verification_commands": "pytest / ruff / mypy",
        # Tolerate additional fields that future templates may reference.
        "plan_path": "planning/claude-plan-tdd.md",
        "plan_org_path": "planning/claude-plan-tdd-org.md",
        "spec_base_path": "sbtdd/spec-behavior-base.md",
        "spec_path": "sbtdd/spec-behavior.md",
        "state_file_path": ".claude/session-state.json",
        "magi_threshold": "GO_WITH_CAVEATS",
        "magi_max_iterations": "3",
        "auto_magi_max_iterations": "5",
        "auto_verification_retries": "3",
        "tdd_guard_enabled": "true",
        "worktree_policy": "opt-in",
    }
    # Regex that matches ``{identifier}`` tokens -- the templates use simple
    # single-brace placeholders, not double-brace or shell syntax.
    residual_re = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
    # Only template files that go through expand() at runtime are relevant.
    # settings.json.template is literal JSON (no placeholders); gitignore.fragment
    # is literal; conftest.py.template is literal Python. spec-behavior-base uses
    # <REPLACE: ...> markers, not brace placeholders.
    for name in ("CLAUDE.local.md.template", "plugin.local.md.template"):
        raw = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        out = expand(raw, context)
        residuals = residual_re.findall(out)
        assert not residuals, (
            f"{name}: residual placeholders {residuals} after snake_case expansion; "
            f"placeholders must match PluginConfig field names (snake_case)"
        )


def test_plugin_local_template_has_all_required_keys():
    raw = (TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    required = [
        "stack:",
        "author:",
        "error_type:",
        "verification_commands:",
        "plan_path:",
        "plan_org_path:",
        "spec_base_path:",
        "spec_path:",
        "state_file_path:",
        "magi_threshold:",
        "magi_max_iterations:",
        "auto_magi_max_iterations:",
        "auto_verification_retries:",
        "tdd_guard_enabled:",
        "worktree_policy:",
    ]
    for key in required:
        assert key in raw, f"plugin.local.md.template missing key {key}"


def test_plugin_local_template_documents_v100_fields():
    """I1 (v1.0.0 O-2 Loop 1 review): template must document Feature G + I fields.

    Per v1.0.0 spec sec.5.2 the plugin.local.md schema gained two new fields:

      - ``magi_cross_check`` (Feature G, opt-in cross-check meta-reviewer)
      - ``schema_version`` (Feature I, default 1 for backward compat)

    Template-installed projects must surface these as commented exemplars so
    operators discover the new knobs without reading the spec or scripts.
    """
    raw = (TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    assert "magi_cross_check" in raw, (
        "plugin.local.md.template must document magi_cross_check (Feature G)"
    )
    assert "schema_version" in raw, (
        "plugin.local.md.template must document schema_version (Feature I)"
    )
