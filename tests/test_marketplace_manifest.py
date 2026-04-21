# tests/test_marketplace_manifest.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for .claude-plugin/marketplace.json.

Validates the BolivarTech marketplace catalog per sec.S.3.2: owner/plugins
structure, sbtdd-workflow entry, tags, category, source path. Version MUST
match plugin.json (sec.S.3.3).
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE_JSON = REPO_ROOT / ".claude-plugin" / "marketplace.json"


def _load_marketplace() -> dict:
    assert MARKETPLACE_JSON.is_file(), f"marketplace.json missing at {MARKETPLACE_JSON}"
    return json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))


def test_marketplace_json_is_valid_json() -> None:
    _load_marketplace()


def test_marketplace_name_is_bolivartech_sbtdd() -> None:
    d = _load_marketplace()
    assert d["name"] == "bolivartech-sbtdd"


def test_marketplace_has_owner_structure() -> None:
    d = _load_marketplace()
    assert isinstance(d["owner"], dict)
    assert d["owner"]["name"] == "BolivarTech"
    assert "github.com/BolivarTech" in d["owner"]["url"]


def test_marketplace_contains_sbtdd_workflow_entry() -> None:
    d = _load_marketplace()
    names = [p["name"] for p in d.get("plugins", [])]
    assert "sbtdd-workflow" in names, f"sbtdd-workflow missing from plugins: {names}"


def test_marketplace_sbtdd_entry_has_required_fields() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    for field in (
        "name",
        "description",
        "version",
        "author",
        "source",
        "category",
        "homepage",
        "tags",
    ):
        assert field in entry, f"missing field '{field}' in sbtdd-workflow entry"


def test_marketplace_sbtdd_entry_source_is_relative() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert entry["source"] == "./", "source must be './' for root-level plugin manifest"


def test_marketplace_tags_include_sbtdd() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert "sbtdd" in entry["tags"]


def test_marketplace_has_top_level_version() -> None:
    d = _load_marketplace()
    assert "version" in d, "top-level version required for marketplace update tracking"


def test_marketplace_homepage_points_to_repo() -> None:
    d = _load_marketplace()
    entry = next(p for p in d["plugins"] if p["name"] == "sbtdd-workflow")
    assert "BolivarTech/sbtdd-workflow" in entry["homepage"]
