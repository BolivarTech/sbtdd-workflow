"""Tests for skills/sbtdd/scripts/models.py — immutable registries."""

from __future__ import annotations

from types import MappingProxyType

import pytest


def test_commit_prefix_map_is_mapping_proxy():
    from models import COMMIT_PREFIX_MAP

    assert isinstance(COMMIT_PREFIX_MAP, MappingProxyType)


def test_commit_prefix_map_rejects_mutation():
    from models import COMMIT_PREFIX_MAP

    with pytest.raises(TypeError):
        COMMIT_PREFIX_MAP["new"] = "whatever"  # type: ignore[index]


def test_commit_prefix_map_has_required_keys():
    from models import COMMIT_PREFIX_MAP

    assert COMMIT_PREFIX_MAP["red"] == "test"
    assert COMMIT_PREFIX_MAP["green_feat"] == "feat"
    assert COMMIT_PREFIX_MAP["green_fix"] == "fix"
    assert COMMIT_PREFIX_MAP["refactor"] == "refactor"
    assert COMMIT_PREFIX_MAP["task_close"] == "chore"


def test_verdict_rank_ordering():
    from models import VERDICT_RANK

    assert VERDICT_RANK["STRONG_NO_GO"] < VERDICT_RANK["HOLD"]
    assert VERDICT_RANK["HOLD"] < VERDICT_RANK["HOLD_TIE"]
    assert VERDICT_RANK["HOLD_TIE"] < VERDICT_RANK["GO_WITH_CAVEATS"]
    assert VERDICT_RANK["GO_WITH_CAVEATS"] < VERDICT_RANK["GO"]
    assert VERDICT_RANK["GO"] < VERDICT_RANK["STRONG_GO"]


def test_verdict_meets_threshold_positive():
    from models import verdict_meets_threshold

    assert verdict_meets_threshold("GO", "GO_WITH_CAVEATS") is True
    assert verdict_meets_threshold("GO_WITH_CAVEATS", "GO_WITH_CAVEATS") is True


def test_verdict_meets_threshold_negative():
    from models import verdict_meets_threshold

    assert verdict_meets_threshold("HOLD", "GO_WITH_CAVEATS") is False
    assert verdict_meets_threshold("STRONG_NO_GO", "GO") is False


def test_verdict_rank_is_mapping_proxy():
    from models import VERDICT_RANK

    assert isinstance(VERDICT_RANK, MappingProxyType)


def test_valid_subcommands_is_tuple():
    from models import VALID_SUBCOMMANDS

    assert isinstance(VALID_SUBCOMMANDS, tuple)


def test_valid_subcommands_has_ten():
    from models import VALID_SUBCOMMANDS

    assert len(VALID_SUBCOMMANDS) == 10


def test_valid_subcommands_contents():
    from models import VALID_SUBCOMMANDS

    expected = (
        "init",
        "spec",
        "close-phase",
        "close-task",
        "status",
        "pre-merge",
        "finalize",
        "auto",
        "resume",
        "review-spec-compliance",
    )
    assert VALID_SUBCOMMANDS == expected


def test_valid_subcommands_includes_review_spec_compliance():
    """Feature B, Task H7: /sbtdd review-spec-compliance <task-id> is dispatchable."""
    from models import VALID_SUBCOMMANDS

    assert "review-spec-compliance" in VALID_SUBCOMMANDS


def test_valid_subcommands_rejects_mutation():
    from models import VALID_SUBCOMMANDS

    with pytest.raises((TypeError, AttributeError)):
        VALID_SUBCOMMANDS[0] = "hacked"  # type: ignore[index]


# ---------------------------------------------------------------------------
# ProgressContext (v0.5.0 sec.3 — heartbeat snapshot dataclass).
# ---------------------------------------------------------------------------


def test_progress_context_default_construction_uses_zero_and_none():
    from models import ProgressContext

    ctx = ProgressContext()
    assert ctx.iter_num == 0
    assert ctx.phase == 0
    assert ctx.task_index is None
    assert ctx.task_total is None
    assert ctx.dispatch_label is None
    assert ctx.started_at is None


def test_progress_context_full_construction_preserves_fields():
    from datetime import datetime, timezone

    from models import ProgressContext

    ts = datetime(2026, 5, 1, 12, 34, 56, tzinfo=timezone.utc)
    ctx = ProgressContext(
        iter_num=2,
        phase=3,
        task_index=14,
        task_total=36,
        dispatch_label="magi-loop2-iter2",
        started_at=ts,
    )
    assert (ctx.iter_num, ctx.phase, ctx.task_index, ctx.task_total) == (2, 3, 14, 36)
    assert ctx.dispatch_label == "magi-loop2-iter2"
    assert ctx.started_at == ts


def test_progress_context_is_frozen():
    from dataclasses import FrozenInstanceError

    from models import ProgressContext

    ctx = ProgressContext()
    with pytest.raises(FrozenInstanceError):
        ctx.iter_num = 5  # type: ignore[misc]
