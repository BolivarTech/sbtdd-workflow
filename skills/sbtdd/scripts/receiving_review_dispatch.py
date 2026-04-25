#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Shared ``/receiving-code-review`` dispatch helpers (v0.2.1 B6 promotion).

The superpowers ``/receiving-code-review`` skill is prose-only: it teaches
the subagent how to RESPOND to feedback with technical rigor but does not
define a machine-parseable output format. To consume the skill from Python
we prepend a format-contract instruction that forces the subagent to end
its reply with two markdown sections (``## Accepted`` / ``## Rejected``);
:func:`parse_receiving_review` then extracts the per-section bullet items.

Both ``pre_merge_cmd._loop2`` (Loop 2 MAGI conditions) and
``auto_cmd._apply_spec_review_findings_via_mini_cycle`` (B6 spec-reviewer
findings) call this module so the prompt + parser shape stays single-sourced.

Backward compatibility: ``pre_merge_cmd`` re-exports
:data:`RECEIVING_REVIEW_FORMAT_CONTRACT` as ``_RECEIVING_REVIEW_FORMAT_CONTRACT``
and :func:`parse_receiving_review` as ``_parse_receiving_review`` so the
v0.2.0 private names remain importable for tests written against the
previous module layout.
"""

from __future__ import annotations

import re

import superpowers_dispatch

#: Regex matching ``## Accepted`` / ``## Rejected`` section headers.
#:
#: Forgiving on whitespace and case to absorb the format variants the
#: superpowers skill has emitted in practice (``##Accepted``,
#: ``## Accepted``, ``##  Accepted``, ``## ACCEPTED``, ``## aCCepteD``).
#: Mirrors :data:`pre_merge_cmd._SECTION_HEADER_RE`'s prior behavior
#: so nothing changes for callers that came in via the legacy private name.
_SECTION_HEADER_RE: re.Pattern[str] = re.compile(
    r"^##\s*(Accepted|Rejected)\b",
    re.IGNORECASE,
)


#: Instruction prepended to every ``/receiving-code-review`` dispatch.
#:
#: The skill is prose-only: without a machine-parseable contract it
#: produces free-form analysis that :func:`parse_receiving_review` cannot
#: extract decisions from, triggering ``ValidationError: /receiving-code-review
#: produced no decisions``. The instruction below gives the subagent an
#: explicit output contract while still allowing the skill's
#: technical-evaluation discipline (the forbidden-responses rules in the
#: skill prevent lazy blanket-accept output).
RECEIVING_REVIEW_FORMAT_CONTRACT: str = (
    "After technical evaluation of the MAGI findings below, your reply "
    "MUST end with EXACTLY these two markdown sections (and nothing "
    "else after them): ``## Accepted`` followed by ``- <verbatim "
    "finding text>`` lines for findings you accept, and "
    "``## Rejected`` followed by ``- <verbatim finding text> "
    "(rationale: ...)`` lines for findings you reject. Every finding "
    "MUST appear under exactly one section. Findings to evaluate:"
)


def parse_receiving_review(
    skill_result: superpowers_dispatch.SkillResult | object,
) -> tuple[list[str], list[str]]:
    """Parse ``/receiving-code-review`` stdout into ``(accepted, rejected)``.

    Expected stdout format (markdown bullet lists under two headers)::

        ## Accepted
        - condition text 1
        - condition text 2

        ## Rejected
        - condition text 3 (rationale: ...)

    Heading recognition is case-insensitive and tolerant of whitespace
    variants (see :data:`_SECTION_HEADER_RE`). Either section may be
    absent (empty list). A completely empty stdout returns ``([], [])``;
    callers (``_loop2`` for MAGI, B6's mini-cycle helper for spec-reviewer)
    treat this as "no decisions produced, re-raise" via a dedicated
    :class:`errors.ValidationError` path.

    Args:
        skill_result: An object exposing a ``stdout`` string attribute
            (typically a :class:`superpowers_dispatch.SkillResult`). When
            ``stdout`` is missing or non-string, both lists return empty.

    Returns:
        A ``(accepted_texts, rejected_texts)`` tuple with leading bullet
        / dash / whitespace stripped from each line.
    """
    accepted: list[str] = []
    rejected: list[str] = []
    dispatch: dict[str, list[str]] = {"accepted": accepted, "rejected": rejected}
    section: list[str] | None = None
    stdout_attr = getattr(skill_result, "stdout", "") or ""
    stdout = stdout_attr if isinstance(stdout_attr, str) else ""
    for line in stdout.splitlines():
        s = line.strip()
        match = _SECTION_HEADER_RE.match(s)
        if match is not None:
            section = dispatch[match.group(1).lower()]
            continue
        if section is not None and s.startswith(("-", "*")):
            section.append(s.lstrip("-* ").strip())
    return accepted, rejected


def conditions_to_skill_args(conditions: tuple[str, ...]) -> list[str]:
    """Serialise a tuple of findings as CLI args for ``/receiving-code-review``.

    The skill accepts findings as positional arguments embedded in the
    ``claude -p`` prompt. The leading instruction
    (:data:`RECEIVING_REVIEW_FORMAT_CONTRACT`) forces the subagent to emit
    output in the ``## Accepted`` / ``## Rejected`` markdown shape that
    :func:`parse_receiving_review` consumes. Each finding is embedded
    quoted so the subagent receives the verbatim text.

    Args:
        conditions: Findings to evaluate. May be MAGI conditions (Loop 2)
            or spec-reviewer issue texts (B6 mini-cycle).

    Returns:
        ``[format_contract, '"finding 1"', '"finding 2"', ...]`` ready
        to pass as the ``args`` kwarg of
        :func:`superpowers_dispatch.receiving_code_review`.
    """
    quoted = [f'"{c}"' for c in conditions]
    return [RECEIVING_REVIEW_FORMAT_CONTRACT, *quoted]
