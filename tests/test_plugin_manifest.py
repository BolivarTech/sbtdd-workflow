# tests/test_plugin_manifest.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for .claude-plugin/plugin.json.

Validates the plugin manifest follows sec.S.3.1 of the functional contract:
name, version, description, author, repository, license, keywords, skills path.
Version MUST match .claude-plugin/marketplace.json (sec.S.3.3).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _load_plugin() -> dict:
    assert PLUGIN_JSON.is_file(), f"plugin.json missing at {PLUGIN_JSON}"
    return json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))


def test_plugin_json_is_valid_json() -> None:
    _load_plugin()


def test_plugin_name_is_sbtdd_workflow() -> None:
    d = _load_plugin()
    assert d["name"] == "sbtdd-workflow"


def test_plugin_version_is_semver() -> None:
    d = _load_plugin()
    assert re.match(r"^\d+\.\d+\.\d+$", d["version"]), f"version must be semver: {d['version']}"


def test_plugin_version_is_current_v0_2_patch() -> None:
    """Plugin must ship a 0.2.x patch on the v0.2 series until the v0.3 bump.

    Originally pinned to ``0.1.0`` (Milestone E ship); relaxed to ``0.1.x`` so
    fix-only releases on v0.1 didn't require editing this test. Retargeted to
    ``0.2.x`` at the v0.2 bump (Task I3) so the same tripwire continues to
    flag accidental bumps until the v0.3 line opens.
    """
    d = _load_plugin()
    assert re.match(r"^0\.2\.\d+$", d["version"]), (
        f"version must be on the v0.2.x patch series until v0.3 bump, got {d['version']}"
    )


def test_plugin_has_description() -> None:
    d = _load_plugin()
    assert isinstance(d["description"], str) and len(d["description"]) >= 20


def test_plugin_author_structure() -> None:
    d = _load_plugin()
    assert isinstance(d["author"], dict)
    assert "name" in d["author"]
    assert "url" in d["author"]


def test_plugin_repository_points_to_bolivartech() -> None:
    d = _load_plugin()
    assert "BolivarTech/sbtdd-workflow" in d["repository"]


def test_plugin_license_is_dual_mit_apache() -> None:
    d = _load_plugin()
    assert d["license"] == "MIT OR Apache-2.0"


def test_plugin_has_skills_path() -> None:
    d = _load_plugin()
    assert d["skills"] == "./skills/"


def test_plugin_keywords_include_sbtdd() -> None:
    d = _load_plugin()
    assert "sbtdd" in d.get("keywords", [])


def test_plugin_version_syncs_with_marketplace() -> None:
    """sec.S.3.3: plugin.json version MUST match marketplace.json version.

    Between Task 5 (plugin.json created) and Task 6 (marketplace.json created),
    marketplace.json does not exist yet. We skip (not silently pass) during
    that window -- the test becomes an unconditional assertion once Task 6
    lands. Silent early-return would hide genuine regressions once both files
    are in place, so skip is preferred.
    """
    if not MARKETPLACE_JSON.is_file():
        pytest.skip("marketplace.json not yet written (Task 6 pending)")
    plugin_v = _load_plugin()["version"]
    marketplace = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
    marketplace_top_v = marketplace["version"]
    assert plugin_v == marketplace_top_v, (
        f"version mismatch: plugin.json={plugin_v}, marketplace.json={marketplace_top_v}"
    )
    # And the entry for this plugin inside the marketplace catalog
    for entry in marketplace["plugins"]:
        if entry["name"] == "sbtdd-workflow":
            assert entry["version"] == plugin_v, (
                f"marketplace plugin entry version mismatch: {entry['version']} vs {plugin_v}"
            )
            break
    else:  # pragma: no cover
        raise AssertionError("sbtdd-workflow entry missing from marketplace.json")
