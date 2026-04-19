import json


def test_read_existing_settings_returns_dict(tmp_path):
    from hooks_installer import read_existing

    target = tmp_path / "settings.json"
    target.write_text(json.dumps({"hooks": {"PreToolUse": []}}))
    result = read_existing(target)
    assert result == {"hooks": {"PreToolUse": []}}


def test_read_missing_returns_empty_dict(tmp_path):
    from hooks_installer import read_existing

    missing = tmp_path / "missing.json"
    assert read_existing(missing) == {}


def test_merge_preserves_user_hooks_and_adds_plugin(tmp_path):
    from hooks_installer import merge

    user_settings = {
        "hooks": {
            "PreToolUse": [
                {"matcher": "Write", "hooks": [{"type": "command", "command": "eslint"}]}
            ]
        }
    }
    plugin_hooks = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|MultiEdit|TodoWrite",
                    "hooks": [{"type": "command", "command": "tdd-guard"}],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [{"type": "command", "command": "tdd-guard"}],
                }
            ],
        }
    }
    existing = tmp_path / "settings.json"
    existing.write_text(json.dumps(user_settings))
    target = tmp_path / "settings.json"
    merge(existing_path=existing, plugin_hooks=plugin_hooks, target_path=target)
    result = json.loads(target.read_text())
    # Both user and plugin hooks should be in PreToolUse.
    commands = [h["hooks"][0]["command"] for h in result["hooks"]["PreToolUse"]]
    assert "eslint" in commands
    assert "tdd-guard" in commands
    # SessionStart (plugin-only) should exist.
    assert "SessionStart" in result["hooks"]
