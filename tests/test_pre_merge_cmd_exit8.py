# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for pre_merge_cmd exit 8 stderr summary (Plan D Task 12)."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pytest

import magi_dispatch
import pre_merge_cmd
import superpowers_dispatch
from errors import MAGIGateError


class _FakeVerdict:
    conditions = ("Refactor X", "Rename Y")
    verdict = "GO_WITH_CAVEATS"
    degraded = False


def _make_cfg() -> Any:
    return type(
        "Cfg",
        (),
        {
            "plan_path": "planning/claude-plan-tdd.md",
            "magi_threshold": "GO_WITH_CAVEATS",
            "magi_max_iterations": 3,
        },
    )()


def _make_ns() -> argparse.Namespace:
    """Return a minimal argparse namespace with Feature A flags at defaults."""
    return argparse.Namespace(override_checkpoint=False, reason=None, non_interactive=False)


def test_loop2_writes_conditions_and_emits_stderr_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cfg = _make_cfg()
    root = tmp_path
    (root / ".claude").mkdir()
    (root / "planning").mkdir()
    (root / "planning" / "claude-plan-tdd.md").write_text("### Task 1:\n- [x]\n")

    # magi returns verdict with conditions; receiving-review accepts 2, rejects 0.
    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, cwd, **_kw: _FakeVerdict(),
    )
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda v: False)
    monkeypatch.setattr(
        superpowers_dispatch,
        "receiving_code_review",
        lambda args, cwd, **_kw: {"accepted": list(_FakeVerdict.conditions), "rejected": []},
    )
    monkeypatch.setattr(
        pre_merge_cmd,
        "_parse_receiving_review",
        lambda r: (list(_FakeVerdict.conditions), []),
    )
    monkeypatch.setattr(
        pre_merge_cmd,
        "_conditions_to_skill_args",
        lambda cs: list(cs),
    )

    with pytest.raises(MAGIGateError):
        pre_merge_cmd._loop2(root, cfg, threshold_override=None, ns=_make_ns())
    captured = capsys.readouterr()
    # magi-conditions.md written
    assert (root / ".claude" / "magi-conditions.md").exists()
    # Stderr summary
    assert "accepted=2" in captured.err or "2 accepted" in captured.err
    assert "rejected=0" in captured.err or "0 rejected" in captured.err
    assert "magi-conditions.md" in captured.err
    assert "close-phase" in captured.err


def test_loop2_unlinks_stale_conditions_on_successful_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MAGI Loop 2 D iter 1 Caspar: successful pre-merge removes stale file.

    When a prior pre-merge run exited 8 it wrote ``magi-conditions.md``.
    If the next run passes cleanly (no conditions or gate met), the
    stale file must be removed -- otherwise ``resume_cmd`` detects it as
    a pending mid-exit-8 state and misdirects the user to
    ``sbtdd close-phase`` even though the conditions were already
    resolved. This is a trap for users iterating locally.
    """

    class _CleanVerdict:
        conditions: tuple[str, ...] = ()
        verdict = "GO"
        degraded = False

    cfg = _make_cfg()
    root = tmp_path
    (root / ".claude").mkdir()
    (root / "planning").mkdir()
    (root / "planning" / "claude-plan-tdd.md").write_text("### Task 1:\n- [x]\n")

    # Seed a stale conditions file from a prior run.
    stale = root / ".claude" / "magi-conditions.md"
    stale.write_text("# stale content from previous exit 8 run\n", encoding="utf-8")
    assert stale.exists()

    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, cwd, **_kw: _CleanVerdict(),
    )
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda v: False)
    monkeypatch.setattr(magi_dispatch, "verdict_passes_gate", lambda v, t: True)

    result = pre_merge_cmd._loop2(root, cfg, threshold_override=None, ns=_make_ns())
    assert result is not None
    # Stale file must be gone once the gate passed cleanly.
    assert not stale.exists(), "stale magi-conditions.md not cleaned up on GO verdict"


def test_loop2_cleans_stale_before_new_write_on_conditions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stale cleanup happens at loop entry, not only on success.

    If the current run also produces conditions, the file is rewritten
    fresh (new frontmatter) rather than being left as a mix of old and
    new content. The guarantee: at most one ``magi-conditions.md`` exists
    after a ``_loop2`` call, and its frontmatter always matches the
    current invocation.
    """
    cfg = _make_cfg()
    root = tmp_path
    (root / ".claude").mkdir()
    (root / "planning").mkdir()
    (root / "planning" / "claude-plan-tdd.md").write_text("### Task 1:\n- [x]\n")

    stale = root / ".claude" / "magi-conditions.md"
    stale.write_text("---\nmagi_iteration: 99\n---\n# stale from iter 99\n", encoding="utf-8")

    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, cwd, **_kw: _FakeVerdict(),
    )
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda v: False)
    monkeypatch.setattr(
        superpowers_dispatch,
        "receiving_code_review",
        lambda args, cwd, **_kw: {"accepted": list(_FakeVerdict.conditions), "rejected": []},
    )
    monkeypatch.setattr(
        pre_merge_cmd,
        "_parse_receiving_review",
        lambda r: (list(_FakeVerdict.conditions), []),
    )
    monkeypatch.setattr(
        pre_merge_cmd,
        "_conditions_to_skill_args",
        lambda cs: list(cs),
    )

    with pytest.raises(MAGIGateError):
        pre_merge_cmd._loop2(root, cfg, threshold_override=None, ns=_make_ns())
    _ = capsys.readouterr()  # drain stderr so it does not clutter output
    # File exists (new write) and does NOT carry the stale iter 99 marker.
    assert stale.exists()
    content = stale.read_text("utf-8")
    assert "magi_iteration: 99" not in content
    assert "stale from iter 99" not in content
