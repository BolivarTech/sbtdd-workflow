#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dataclass representation + writer for the TDD-Guard ``test.json`` schema.

TDD-Guard expects a JSON document with the exact shape::

    {
      "testModules": [
        {
          "moduleId": "<path>",
          "tests": [
            {
              "name": "<name>",
              "fullName": "<name>",
              "state": "passed|failed|skipped",
              "errors": [{"message": "...", "stack": "..."}]    # optional
            }
          ]
        }
      ],
      "reason": "passed|failed|interrupted"
    }

The project-root ``conftest.py`` already produces this document for the
Python stack. This module factors out the schema so ``ctest_reporter``
and ``rust_reporter`` can reuse the same typed structure + writer. It
also gives ``conftest.py.template`` (Task 23) a concrete reference.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from errors import ValidationError

#: Allowed ``state`` values (TDD-Guard contract).
VALID_STATES: tuple[str, ...] = ("passed", "failed", "skipped")

#: Allowed ``reason`` values (TDD-Guard contract).
VALID_REASONS: tuple[str, ...] = ("passed", "failed", "interrupted")


@dataclass(frozen=True)
class TestError:
    """Single failure representation."""

    message: str
    stack: str


@dataclass(frozen=True)
class TestEntry:
    """Individual test result (post-run)."""

    name: str
    full_name: str
    state: str
    errors: tuple[TestError, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValidationError(f"TestEntry.state='{self.state}' not in {list(VALID_STATES)}")


@dataclass(frozen=True)
class TestModule:
    """Collection of tests grouped by module_id (typically a file path)."""

    module_id: str
    tests: tuple[TestEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TestJSON:
    """Root object of the TDD-Guard test.json document."""

    test_modules: tuple[TestModule, ...]
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in VALID_REASONS:
            raise ValidationError(f"TestJSON.reason='{self.reason}' not in {list(VALID_REASONS)}")

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the exact JSON shape TDD-Guard expects."""
        modules: list[dict[str, Any]] = []
        for m in self.test_modules:
            tests_out: list[dict[str, Any]] = []
            for t in m.tests:
                entry: dict[str, Any] = {
                    "name": t.name,
                    "fullName": t.full_name,
                    "state": t.state,
                }
                if t.errors:
                    entry["errors"] = [{"message": e.message, "stack": e.stack} for e in t.errors]
                tests_out.append(entry)
            modules.append({"moduleId": m.module_id, "tests": tests_out})
        return {"testModules": modules, "reason": self.reason}


def write_test_json(doc: TestJSON, target: Path) -> None:
    """Write ``doc`` to ``target`` atomically (tmp + os.replace).

    Creates parent directories if missing. On :class:`OSError` during the
    final ``os.replace``, the tmp file is unlinked before re-raising so no
    ``*.tmp.<pid>`` residue is left behind (mirrors ``state_file.save``
    and ``magi_dispatch.write_verdict_artifact``).

    Args:
        doc: Fully constructed :class:`TestJSON` to serialise.
        target: Destination path (typically
            ``.claude/tdd-guard/data/test.json``).

    Raises:
        OSError: If the atomic replace fails.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(doc.to_dict(), indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
