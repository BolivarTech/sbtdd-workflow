#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Shared plan-editing helpers used by close_task_cmd, spec_cmd, auto_cmd.

Public API:
- flip_task_checkboxes(plan_text, task_id) -> plan_text with ``- [ ]`` flipped
  to ``- [x]`` inside the section whose header matches ``task_id``.
- next_task(plan_text, after_task_id) -> ``(id, title)`` of the next task with
  at least one ``- [ ]`` checkbox after ``after_task_id``, or ``(None, None)``.
- first_open_task(plan_text) -> ``(id, title)`` of the first task containing
  ``- [ ]``, raises :class:`PreconditionError` if none.

Module filename is underscore-prefixed to signal "internal to plugin but
shared across cmd modules" (distinct from pure stdlib helpers). The public
function identifiers deliberately do NOT carry a leading underscore so
other ``*_cmd.py`` modules consume them without reaching into private
symbols (Finding 6 Balthasar + iter-2 Finding W1).
"""

from __future__ import annotations

import re

from errors import PreconditionError

_TASK_HEADER_RE = re.compile(r"^### Task (\S+?): (.+)$", re.MULTILINE)


def _task_section_bounds(plan_text: str, task_id: str) -> tuple[int, int]:
    """Return ``(start, end)`` offsets delimiting the section for ``task_id``.

    Start is the offset immediately AFTER the ``### Task <id>:`` header line;
    end is the offset of the next task header (or end-of-string).

    Raises:
        PreconditionError: If no section matches ``task_id``.
    """
    header = re.compile(rf"^### Task {re.escape(task_id)}:", re.MULTILINE)
    m = header.search(plan_text)
    if not m:
        raise PreconditionError(f"task '{task_id}' not found in plan")
    nm = _TASK_HEADER_RE.search(plan_text, m.end())
    end = nm.start() if nm else len(plan_text)
    return (m.end(), end)


def flip_task_checkboxes(plan_text: str, task_id: str) -> str:
    """Flip every ``- [ ]`` inside the section for ``task_id`` to ``- [x]``.

    Args:
        plan_text: Full plan contents.
        task_id: Identifier matching ``### Task <id>:``.

    Returns:
        New plan text with the target section's checkboxes flipped; sections
        of other tasks are untouched.

    Raises:
        PreconditionError: Propagated from :func:`_task_section_bounds` when
            ``task_id`` is not present in ``plan_text``.
    """
    start, end = _task_section_bounds(plan_text, task_id)
    section = plan_text[start:end].replace("- [ ]", "- [x]")
    return plan_text[:start] + section + plan_text[end:]


def next_task(plan_text: str, after_task_id: str) -> tuple[str | None, str | None]:
    """Return ``(id, title)`` of the next open task strictly after ``after_task_id``.

    Args:
        plan_text: Full plan contents.
        after_task_id: Identifier whose successor we want.

    Returns:
        Tuple ``(id, title)`` of the first task with at least one ``- [ ]``
        checkbox whose header appears AFTER ``after_task_id`` in source
        order; ``(None, None)`` if no such task exists (plan complete).
    """
    tasks = [(m.group(1), m.group(2).strip()) for m in _TASK_HEADER_RE.finditer(plan_text)]
    found = False
    for tid, title in tasks:
        if found:
            start, end = _task_section_bounds(plan_text, tid)
            if "- [ ]" in plan_text[start:end]:
                return (tid, title)
        if tid == after_task_id:
            found = True
    return (None, None)


def first_open_task(plan_text: str) -> tuple[str, str]:
    """Return ``(id, title)`` of the first task in ``plan_text`` with ``- [ ]``.

    Raises:
        PreconditionError: If no task section contains an open checkbox.
    """
    for m in _TASK_HEADER_RE.finditer(plan_text):
        tid = m.group(1)
        title = m.group(2).strip()
        start, end = _task_section_bounds(plan_text, tid)
        if "- [ ]" in plan_text[start:end]:
            return (tid, title)
    raise PreconditionError("plan has no open [ ] tasks")
