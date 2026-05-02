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


def test_resolved_models_dataclass_shape():
    """Spec sec.5.1: ResolvedModels has implementer/spec_reviewer/code_review/magi_dispatch fields."""
    from models import ResolvedModels

    rm = ResolvedModels(
        implementer="claude-sonnet-4-6",
        spec_reviewer="claude-sonnet-4-6",
        code_review="claude-sonnet-4-6",
        magi_dispatch="claude-opus-4-7",
    )
    assert rm.implementer == "claude-sonnet-4-6"
    assert rm.spec_reviewer == "claude-sonnet-4-6"
    assert rm.code_review == "claude-sonnet-4-6"
    assert rm.magi_dispatch == "claude-opus-4-7"


def test_resolved_models_is_frozen():
    """Spec sec.5.1: ResolvedModels frozen dataclass (J2-3)."""
    from dataclasses import FrozenInstanceError

    from models import ResolvedModels

    rm = ResolvedModels(
        implementer="a", spec_reviewer="b", code_review="c", magi_dispatch="d"
    )
    with pytest.raises(FrozenInstanceError):
        rm.implementer = "z"  # type: ignore[misc]


def test_models_module_does_not_import_consumer_modules():
    """Sec.9.1 deferred-import contract: models.py must not import consumer modules.

    auto_cmd, pre_merge_cmd, magi_dispatch, status_cmd are all DOWNSTREAM consumers
    of ResolvedModels. If models.py imports any of them at module-load time, the
    cross-subagent contract for parallel dispatch (Mitigation A) breaks: any cycle
    that depends on import order fails when subagent commits land in opposite
    sequences. See spec sec.9.1.
    """
    import inspect

    import models

    source = inspect.getsource(models)
    forbidden = ("auto_cmd", "pre_merge_cmd", "magi_dispatch", "status_cmd")
    for name in forbidden:
        # Look for import-statement patterns -- "import X" or "from X import"
        # at the top level. Substring search is sufficient because models.py is
        # small enough for any false-positive (e.g. a docstring mention) to be
        # caught by manual review.
        assert f"import {name}" not in source, (
            f"models.py must not import {name} at module-load time "
            f"(spec sec.9.1 deferred-import contract)"
        )
        assert f"from {name}" not in source, (
            f"models.py must not import from {name} at module-load time "
            f"(spec sec.9.1 deferred-import contract)"
        )
