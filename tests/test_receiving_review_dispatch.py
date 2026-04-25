# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for ``skills/sbtdd/scripts/receiving_review_dispatch.py`` (v0.2.1 B6).

The shared module exists so both ``pre_merge_cmd._loop2`` and
``auto_cmd._apply_spec_review_findings_via_mini_cycle`` can route findings
through ``/receiving-code-review`` using one canonical prompt + one canonical
parser. v0.2 kept these private to ``pre_merge_cmd``; v0.2.1 promotes them to
a shared module so the auto-feedback loop reuses them.

Backward-compat: ``pre_merge_cmd._parse_receiving_review`` and
``pre_merge_cmd._RECEIVING_REVIEW_FORMAT_CONTRACT`` remain importable as
re-exports so existing tests keep passing.
"""

from __future__ import annotations

from typing import Any


def test_format_contract_is_a_nonempty_string() -> None:
    """The format-contract preamble is a public, nonempty constant."""
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        RECEIVING_REVIEW_FORMAT_CONTRACT,
    )

    assert isinstance(RECEIVING_REVIEW_FORMAT_CONTRACT, str)
    assert len(RECEIVING_REVIEW_FORMAT_CONTRACT) > 0
    # The instruction must mention the two markdown sections the parser
    # expects so any future edit that drops them is caught here.
    assert "## Accepted" in RECEIVING_REVIEW_FORMAT_CONTRACT
    assert "## Rejected" in RECEIVING_REVIEW_FORMAT_CONTRACT


def test_parse_receiving_review_extracts_accepted_and_rejected() -> None:
    """The public parser returns ``(accepted, rejected)`` lists from skill stdout."""
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        parse_receiving_review,
    )

    class Result:
        stdout = (
            "Some preamble.\n"
            "## Accepted\n"
            "- finding A\n"
            "- finding B\n"
            "\n"
            "## Rejected\n"
            "- finding C (rationale: misread spec)\n"
        )

    accepted, rejected = parse_receiving_review(Result())
    assert accepted == ["finding A", "finding B"]
    assert rejected == ["finding C (rationale: misread spec)"]


def test_pre_merge_cmd_re_exports_legacy_parser_for_backward_compat() -> None:
    """``pre_merge_cmd._parse_receiving_review`` keeps working post-promotion."""
    import pre_merge_cmd
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        parse_receiving_review,
    )

    # Identity check: the legacy private name must point at the new public one.
    assert pre_merge_cmd._parse_receiving_review is parse_receiving_review


def test_pre_merge_cmd_re_exports_legacy_format_contract_for_backward_compat() -> None:
    """``pre_merge_cmd._RECEIVING_REVIEW_FORMAT_CONTRACT`` keeps working."""
    import pre_merge_cmd
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        RECEIVING_REVIEW_FORMAT_CONTRACT,
    )

    assert pre_merge_cmd._RECEIVING_REVIEW_FORMAT_CONTRACT == RECEIVING_REVIEW_FORMAT_CONTRACT


def test_conditions_to_skill_args_includes_format_contract_first() -> None:
    """``conditions_to_skill_args`` puts the format contract first, then quoted findings."""
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        RECEIVING_REVIEW_FORMAT_CONTRACT,
        conditions_to_skill_args,
    )

    args = conditions_to_skill_args(("first finding", 'second "quoted" finding'))
    assert args[0] == RECEIVING_REVIEW_FORMAT_CONTRACT
    assert args[1] == '"first finding"'
    assert args[2] == '"second "quoted" finding"'


def test_parse_receiving_review_handles_mixed_case_headers() -> None:
    """Header capitalisation variants all map to the canonical buckets."""
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        parse_receiving_review,
    )

    class Result:
        stdout = "##ACCEPTED\n- one\n##  rejected\n- two (rationale: x)\n"

    accepted, rejected = parse_receiving_review(Result())
    assert accepted == ["one"]
    assert rejected == ["two (rationale: x)"]


def test_parse_receiving_review_returns_empty_when_stdout_missing() -> None:
    """Result lacking ``stdout`` attribute -> ``([], [])`` (no crash)."""
    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        parse_receiving_review,
    )

    class _NoStdout:
        pass

    accepted, rejected = parse_receiving_review(_NoStdout())  # type: ignore[arg-type]
    assert accepted == []
    assert rejected == []


def test_parse_receiving_review_signature_matches_legacy(monkeypatch: Any) -> None:
    """Public ``parse_receiving_review`` accepts the same shape as the legacy private fn."""
    import inspect

    from receiving_review_dispatch import (  # type: ignore[import-not-found]
        parse_receiving_review,
    )

    sig = inspect.signature(parse_receiving_review)
    # Single positional/keyword param `skill_result` -- mirrors v0.2.0
    # `_parse_receiving_review(skill_result)`. Keeps callers working without
    # adapter shims.
    assert list(sig.parameters) == ["skill_result"]
