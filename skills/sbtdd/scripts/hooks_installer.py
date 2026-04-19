#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Idempotent merge of .claude/settings.json (sec.S.5.1 Fase 3, sec.S.7.2).

When init runs on a project that already has settings.json with user
hooks, we must preserve those hooks and ADD ours — never overwrite.
Subsequent runs with identical inputs must produce byte-identical
output (idempotency invariant).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def read_existing(path: Path | str) -> dict[str, Any]:
    """Read existing settings.json or return {} if missing.

    Args:
        path: Path to settings.json.

    Returns:
        Parsed dict, or empty dict if the file does not exist.

    Raises:
        json.JSONDecodeError: If the file exists but is malformed.
    """
    p = Path(path)
    if not p.exists():
        return {}
    data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return data


def merge(
    existing_path: Path | str,
    plugin_hooks: dict[str, Any],
    target_path: Path | str,
) -> None:
    """Merge plugin hooks into existing settings.json, writing atomically.

    Preserves all user hooks; appends plugin hooks alongside them. Write
    pattern: write to tmp file in same directory, then os.replace —
    atomic on POSIX and Windows. If ``os.replace`` raises ``OSError``
    (cross-device rename, permission denied, etc.), the tmp file is
    unlinked before re-raising so no stray ``*.tmp.<pid>`` file leaks
    onto disk (mirrors ``state_file.save``; MAGI Loop 2 Finding 6).

    Args:
        existing_path: Path to existing settings.json (may not exist).
        plugin_hooks: Plugin hook fragment to merge in. Expected shape:
            {"hooks": {"<event>": [hook_entry, ...], ...}}
        target_path: Where to write the merged result.

    Raises:
        OSError: If the atomic replace fails. No partial file and no
            tmp left behind.
    """
    existing = read_existing(existing_path)
    existing_hooks = existing.setdefault("hooks", {})
    for event, entries in plugin_hooks.get("hooks", {}).items():
        existing_list = existing_hooks.setdefault(event, [])
        for entry in entries:
            if entry not in existing_list:
                existing_list.append(entry)
    target = Path(target_path)
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        # Clean up the partially-written tmp so the directory is left in
        # a consistent state; re-raise so callers see the underlying
        # failure (MAGI Loop 2 Finding 6; mirrors state_file.save).
        tmp.unlink(missing_ok=True)
        raise
