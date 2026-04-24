# tests/test_distribution_coherence.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Cross-artifact coherence tests for Milestone E distribution.

Validates invariants that span multiple files: version sync across manifests,
subcommand parity across SKILL.md + README, license consistency.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILL_MD = REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
README_MD = REPO_ROOT / "README.md"
CHANGELOG_MD = REPO_ROOT / "CHANGELOG.md"

NINE_SUBCOMMANDS = frozenset(
    (
        "init",
        "spec",
        "close-phase",
        "close-task",
        "status",
        "pre-merge",
        "finalize",
        "auto",
        "resume",
    )
)


def test_plugin_and_marketplace_versions_match() -> None:
    plugin_v = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    mkt = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    assert plugin_v == mkt["version"]
    entry = next(p for p in mkt["plugins"] if p["name"] == "sbtdd-workflow")
    assert plugin_v == entry["version"]


def test_plugin_and_marketplace_license_match() -> None:
    plugin_license = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["license"]
    assert plugin_license == "MIT OR Apache-2.0"
    readme = README_MD.read_text(encoding="utf-8")
    assert "MIT" in readme and "Apache-2.0" in readme


def test_skill_and_readme_subcommands_match() -> None:
    skill = SKILL_MD.read_text(encoding="utf-8")
    readme = README_MD.read_text(encoding="utf-8")
    for sub in NINE_SUBCOMMANDS:
        assert re.search(rf"\b{re.escape(sub)}\b", skill), f"SKILL.md missing subcommand '{sub}'"
        assert re.search(rf"\b{re.escape(sub)}\b", readme), f"README missing subcommand '{sub}'"


def test_all_artifacts_mention_bolivartech_org() -> None:
    for path in (PLUGIN_JSON, MARKETPLACE_JSON, README_MD):
        text = path.read_text(encoding="utf-8")
        assert "BolivarTech" in text, f"{path.name} missing BolivarTech reference"


def test_changelog_still_present_and_references_v0_1() -> None:
    """Milestone D created CHANGELOG.md; Milestone E must not remove it."""
    assert CHANGELOG_MD.is_file()
    changelog = CHANGELOG_MD.read_text(encoding="utf-8")
    assert "Unreleased" in changelog or "0.1" in changelog


def _semver_key(v: str) -> tuple[int, ...]:
    """Convert '2.1.4' -> (2, 1, 4); non-numeric segments sort last (-1)."""
    parts: list[int] = []
    for seg in v.split("."):
        try:
            parts.append(int(seg))
        except ValueError:
            parts.append(-1)
    return tuple(parts)


def _resolve_magi_plugin_json() -> Path:
    """Resolve the path to MAGI's plugin.json, honoring MAGI_PLUGIN_ROOT override."""
    magi_root_env = os.environ.get("MAGI_PLUGIN_ROOT")
    if magi_root_env:
        return Path(magi_root_env) / ".claude-plugin" / "plugin.json"
    # Default cache location used by Claude Code on Windows/POSIX.
    return (
        Path.home()
        / ".claude"
        / "plugins"
        / "cache"
        / "bolivartech-plugins"
        / "magi"
        / "2.1.3"
        / ".claude-plugin"
        / "plugin.json"
    )


MAGI_PLUGIN_JSON = _resolve_magi_plugin_json()


@pytest.mark.skipif(
    not MAGI_PLUGIN_JSON.is_file(),
    reason=(
        f"MAGI plugin.json not found at {MAGI_PLUGIN_JSON}; set MAGI_PLUGIN_ROOT to override. "
        "Parity check is a local-dev convenience, not a CI enforcement — "
        "addresses F3 MAGI iter 2."
    ),
)
def test_plugin_json_has_required_keys_matching_magi() -> None:
    """Parity with MAGI's plugin.json — required-keys subset check (F4 MAGI iter 2).

    This is a **local-dev parity check**, NOT a Claude Code spec validation.
    Anthropic does not formally publish a plugin manifest schema as of
    v0.1.0 ship date; the authoritative reference is MAGI v2.1.3's
    `plugin.json`, which is the template the SBTDD plugin follows
    field-for-field.

    **F4 MAGI iter 2 fix:** previous draft asserted `set(sbtdd.keys()) ==
    set(magi.keys())` (exact equality). That check breaks the moment MAGI
    adds an optional field (e.g., `dependencies`, `homepage`, `engines`) —
    both plugins would be healthy but the test would false-positive.
    Replaced with a **subset check on the six fields we care about**
    (`name`, `version`, `author`, `repository`, `license`, `skills`).
    Optional fields MAGI may add are now silently tolerated.

    **F3 MAGI iter 2 fix:** the skip condition is now a `@pytest.mark.skipif`
    decorator (not an inline `pytest.skip` call). This surfaces the skip
    reason in pytest's short summary (`-rs` flag) and documents the test as
    local-dev-only rather than CI-enforcement.
    """
    sbtdd = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    magi = json.loads(MAGI_PLUGIN_JSON.read_text(encoding="utf-8"))

    required_keys = {"name", "version", "author", "repository", "license", "skills"}
    sbtdd_keys = frozenset(sbtdd.keys())
    magi_keys = frozenset(magi.keys())

    # Both manifests MUST declare the six required keys. Optional extras on
    # either side are tolerated.
    assert required_keys.issubset(sbtdd_keys), (
        f"sbtdd plugin.json missing required keys: {required_keys - sbtdd_keys}"
    )
    assert required_keys.issubset(magi_keys), (
        f"magi plugin.json missing required keys (MAGI-side drift): {required_keys - magi_keys}"
    )


@pytest.mark.skipif(
    not MAGI_PLUGIN_JSON.is_file(),
    reason=(
        f"MAGI plugin.json not found at {MAGI_PLUGIN_JSON}; set MAGI_PLUGIN_ROOT to override. "
        "Parity check is a local-dev convenience, not a CI enforcement."
    ),
)
def test_plugin_json_repository_field_form_matches_magi() -> None:
    """F5 MAGI iter 2: verify `repository` field form parity at runtime.

    The plan declares that the SBTDD plugin uses the **string form** for
    `repository` because MAGI v2.1.3 uses the string form. This test ties
    that claim to runtime evidence: the two manifests must use the same
    Python type for the field (both `str`, or both `dict`). If MAGI ever
    switches to the object form `{"url": "...", "type": "git"}`, this
    test fails and we schedule a migration commit rather than silently
    drifting apart.

    Skipped when MAGI cache is unavailable (same condition as above).
    """
    sbtdd = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
    magi = json.loads(MAGI_PLUGIN_JSON.read_text(encoding="utf-8"))
    assert isinstance(sbtdd["repository"], type(magi["repository"])), (
        f"repository field form drift: "
        f"sbtdd is {type(sbtdd['repository']).__name__}, "
        f"magi is {type(magi['repository']).__name__} — "
        "migration commit required to re-align"
    )


def test_no_uppercase_placeholders_in_skill_md() -> None:
    """Extends the rationale of INV-27 to the user-facing orchestrator skill.

    **Scope note (F5 + F11 from MAGI iter 1):** INV-27 formally applies only to
    `sbtdd/spec-behavior-base.md` (it guards the input to `/sbtdd spec`). This
    test does NOT enforce INV-27; it extends the same *rationale* (placeholder
    markers signal unfinished work) to the SKILL.md artifact, which is the
    first user-visible surface of the plugin.

    Intentionally scoped to `SKILL.md` only -- NOT to `README.md` or
    `CHANGELOG.md`, which legitimately discuss INV-27 and its history and
    would therefore false-positive on a blanket grep. Per-artifact guards for
    README and CONTRIBUTING already live in `test_readme.py` (those tests
    exclude their own rationale prose by virtue of the concatenation pattern).
    """
    # Runtime assembly keeps this file itself clean: the literal markers never
    # appear in source. The inline concatenation ("TO" + "DO", etc.) guarantees
    # the guard does not trip on its own implementation.
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    text = SKILL_MD.read_text(encoding="utf-8")
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"SKILL.md contains forbidden placeholder '{token}' "
            "(extends INV-27 rationale to SKILL.md)"
        )


def test_semver_key_orders_patch_bump() -> None:
    from tests.test_distribution_coherence import _semver_key

    assert _semver_key("2.1.4") > _semver_key("2.1.3")
    assert _semver_key("2.2.0") > _semver_key("2.1.99")
    assert _semver_key("3.0.0") > _semver_key("2.99.99")


def test_semver_key_handles_mixed_version_strings() -> None:
    from tests.test_distribution_coherence import _semver_key

    # non-numeric segment sorts BELOW numeric (we use -1 as the sentinel)
    assert _semver_key("2.1.3") > _semver_key("2.1.beta")
    assert _semver_key("2.1.0") > _semver_key("garbage")
    # ties resolve deterministically
    assert _semver_key("2.1.3") == _semver_key("2.1.3")


def test_resolve_magi_plugin_json_picks_latest_semver(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    # Build synthetic cache with 2.1.3 and 2.1.4
    for v in ("2.1.3", "2.1.4"):
        d = tmp_path / "bolivartech-plugins" / "magi" / v / ".claude-plugin"
        d.mkdir(parents=True)
        (d / "plugin.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("MAGI_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(
        "pathlib.Path.home",
        lambda: tmp_path.parent,  # home()/.claude/plugins/cache -> tmp_path
    )
    # Compose the expected base the resolver walks to
    monkeypatch.setattr(
        "tests.test_distribution_coherence._magi_cache_base",
        lambda: tmp_path / "bolivartech-plugins" / "magi",
    )
    resolved = _resolve_magi_plugin_json()
    assert resolved.parent.parent.name == "2.1.4"


def test_resolve_magi_plugin_json_honors_env_override(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    monkeypatch.setenv("MAGI_PLUGIN_ROOT", str(tmp_path))
    result = _resolve_magi_plugin_json()
    assert result == tmp_path / ".claude-plugin" / "plugin.json"


def test_resolve_magi_plugin_json_graceful_when_cache_missing(tmp_path, monkeypatch) -> None:
    from tests.test_distribution_coherence import _resolve_magi_plugin_json
    monkeypatch.delenv("MAGI_PLUGIN_ROOT", raising=False)
    monkeypatch.setattr(
        "tests.test_distribution_coherence._magi_cache_base",
        lambda: tmp_path / "does-not-exist",
    )
    result = _resolve_magi_plugin_json()
    assert not result.is_file()  # triggers existing skipif gate
