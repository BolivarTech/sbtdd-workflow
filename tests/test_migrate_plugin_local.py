#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Unit tests for v1.0.0 Feature I migration tool skeleton (sec.3.1)."""

from __future__ import annotations

import pytest


def test_i3_migrate_v1_to_v2_is_no_op_skeleton():
    """I3: v1 -> v2 migration is no-op skeleton (just adds schema_version field)."""
    from migrate_plugin_local import migrate_to

    v1_data = {"stack": "python", "author": "Julian Bolivar"}
    result = migrate_to(target_version=2, data=v1_data)
    assert result["stack"] == "python"
    assert result["author"] == "Julian Bolivar"
    assert result["schema_version"] == 2


def test_i4_migration_ladder_supports_future_bumps():
    """I4: MIGRATIONS dict has v1 entry; future bumps add entries."""
    from migrate_plugin_local import MIGRATIONS

    assert 1 in MIGRATIONS
    assert callable(MIGRATIONS[1])


def test_migrate_to_target_equals_current_is_no_op():
    """When target_version == current schema_version, nothing happens (idempotent)."""
    from migrate_plugin_local import migrate_to

    v2_data = {"stack": "python", "schema_version": 2}
    result = migrate_to(target_version=2, data=v2_data)
    assert result == v2_data


def test_migrate_to_unknown_jump_raises_value_error():
    """Walking past the registered MIGRATIONS ladder raises ValueError."""
    from migrate_plugin_local import migrate_to

    v1_data = {"stack": "python"}
    with pytest.raises(ValueError, match="No migration defined"):
        # target_version=99 is past every registered ladder entry, so the loop
        # eventually hits a missing entry and must raise.
        migrate_to(target_version=99, data=v1_data)


def test_migrate_to_does_not_mutate_input_dict():
    """migrate_to should return a new dict (or at least not mutate caller's input keys)."""
    from migrate_plugin_local import migrate_to

    v1_data = {"stack": "python"}
    snapshot_before = dict(v1_data)
    _ = migrate_to(target_version=2, data=v1_data)
    # The caller's original dict must not have schema_version implanted
    # (defensive contract: callers may rely on input immutability).
    assert v1_data == snapshot_before


def test_i2_migrate_to_no_op_returns_distinct_object(tmp_path):
    """I2 (v1.0.0 O-2 Loop 1 review): no-op path returns a distinct dict object.

    When ``target_version == current``, the migration loop never iterates;
    callers must not be able to mutate the returned dict and silently mutate
    the caller's input via the same reference.
    """
    from migrate_plugin_local import migrate_to

    v2_data = {"stack": "python", "schema_version": 2}
    result = migrate_to(target_version=2, data=v2_data)
    # Logical equality preserved.
    assert result == v2_data
    # Defensive contract: distinct object so caller mutation of result
    # does not leak into the caller's input dict.
    assert result is not v2_data
    # Verify isolation by mutating the returned dict.
    result["stack"] = "rust"
    assert v2_data["stack"] == "python"
