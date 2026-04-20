# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for pre_merge_cmd exit 8 stderr summary (Plan D Task 12)."""

from __future__ import annotations

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
        lambda context_paths, cwd: _FakeVerdict(),
    )
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda v: False)
    monkeypatch.setattr(
        superpowers_dispatch,
        "receiving_code_review",
        lambda args, cwd: {"accepted": list(_FakeVerdict.conditions), "rejected": []},
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
        pre_merge_cmd._loop2(root, cfg, threshold_override=None)
    captured = capsys.readouterr()
    # magi-conditions.md written
    assert (root / ".claude" / "magi-conditions.md").exists()
    # Stderr summary
    assert "accepted=2" in captured.err or "2 accepted" in captured.err
    assert "rejected=0" in captured.err or "0 rejected" in captured.err
    assert "magi-conditions.md" in captured.err
    assert "close-phase" in captured.err
