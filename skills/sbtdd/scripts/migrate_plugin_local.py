#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""plugin.local.md schema migration tool skeleton (Feature I, INV-36).

Per spec sec.3.1: migrations are tracked in :data:`MIGRATIONS`; each entry
is a callable taking the current dict and returning the dict at the next
schema version. v1 -> v2 is a no-op skeleton (just adds the
``schema_version`` field).

Future migrations populate the ladder. The helper :func:`migrate_to`
walks the ladder from the current version (``data.get("schema_version",
1)``) up to the requested target.

Sec.9.1 deferred-import contract: this module imports only Python
stdlib; it must NOT import :mod:`auto_cmd`, :mod:`pre_merge_cmd`,
:mod:`magi_dispatch`, or :mod:`status_cmd`.
"""

from __future__ import annotations

from typing import Any, Callable


def _v1_to_v2(data: dict[str, Any]) -> dict[str, Any]:
    """No-op migration v1 -> v2: just declare ``schema_version=2``.

    Returns a new dict; does not mutate ``data`` (caller-input immutability
    contract honored by :func:`migrate_to`).
    """
    return {**data, "schema_version": 2}


#: Migration ladder. Each key ``N`` is the *current* schema version; the
#: associated callable produces the dict at version ``N+1``.
#:
#: To add a v2 -> v3 migration, append ``2: _v2_to_v3`` and define the
#: callable. Operators run::
#:
#:     python -m migrate_plugin_local <plugin.local.md path> --to <target_version>
#:
#: (a CLI entrypoint may land in a future release; the registry is the
#: stable API for now).
MIGRATIONS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {
    1: _v1_to_v2,
}


def migrate_to(*, target_version: int, data: dict[str, Any]) -> dict[str, Any]:
    """Migrate ``data`` dict to the target schema version.

    Walks the :data:`MIGRATIONS` ladder from the current version
    (``data.get("schema_version", 1)``) up to ``target_version``,
    applying each step.

    Args:
        target_version: Target ``schema_version`` to migrate to.
        data: Parsed plugin.local.md frontmatter dict.

    Returns:
        Migrated dict at the target schema version. The caller's input
        ``data`` dict is not mutated; each migration step returns a new
        dict.

    Raises:
        ValueError: If the ladder lacks a migration entry for some
            intermediate version (e.g. caller asked for v3 but only
            v1 -> v2 is registered).
    """
    current = data.get("schema_version", 1)
    while current < target_version:
        if current not in MIGRATIONS:
            raise ValueError(
                f"No migration defined from schema_version {current} "
                f"to {current + 1}. Add an entry to MIGRATIONS dict."
            )
        data = MIGRATIONS[current](data)
        current += 1
    # I2 fix (v1.0.0 O-2 Loop 1 review): always return a fresh dict object
    # so the no-op path (target_version == data['schema_version']) does not
    # alias the caller's input. Each migration step in the ladder already
    # returns a new dict via dict-spread; this defensive copy guarantees
    # the contract on the no-op branch as well.
    return dict(data)
