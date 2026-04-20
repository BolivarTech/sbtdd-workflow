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
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    for placeholder in ("{Author}", "{ErrorType}", "{stack}"):
        assert placeholder in raw, (
            f"placeholder {placeholder} missing from CLAUDE.local.md.template"
        )


def test_claude_local_template_expands_without_residual_placeholders():
    from templates import expand

    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    out = expand(
        raw,
        {
            "Author": "Julian Bolivar",
            "ErrorType": "MyErr",
            "stack": "python",
            "verification_commands": "pytest / ruff / mypy",
        },
    )
    assert "{Author}" not in out
    assert "{ErrorType}" not in out
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
