# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd pre-merge subcommand (sec.S.5.6)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from magi_dispatch import MAGIVerdict


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "done",
    current_task_id: str | None = None,
    current_task_title: str | None = None,
    plan_approved_at: str | None = "2026-04-20T03:30:00Z",
) -> Path:
    """Write a minimal valid state file into tmp_path/.claude."""
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    state = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": current_task_id,
        "current_task_title": current_task_title,
        "current_phase": current_phase,
        "phase_started_at_commit": "abc1234",
        "last_verification_at": "2026-04-20T03:30:00Z",
        "last_verification_result": "passed",
        "plan_approved_at": plan_approved_at,
    }
    state_path = claude / "session-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _seed_plan_all_done(tmp_path: Path) -> Path:
    """Write a plan where every task has all checkboxes marked [x]."""
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    plan.write_text(
        "# Plan\n\n### Task 1: done\n- [x] step\n\n### Task 2: done\n- [x] step\n",
        encoding="utf-8",
    )
    return plan


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo with one initial commit so HEAD resolves."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def test_pre_merge_cmd_module_importable() -> None:
    import pre_merge_cmd

    assert hasattr(pre_merge_cmd, "main")


def test_pre_merge_aborts_when_state_not_done(tmp_path: Path) -> None:
    import pre_merge_cmd
    from errors import PreconditionError

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="green", current_task_id="1", current_task_title="t")
    _seed_plan_all_done(tmp_path)
    with pytest.raises(PreconditionError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])


def test_pre_merge_aborts_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pre_merge_cmd
    from drift import DriftReport
    from errors import DriftError

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    monkeypatch.setattr(
        pre_merge_cmd,
        "detect_drift",
        lambda *a, **kw: DriftReport("done", "test", "[ ]", "stub"),
    )
    with pytest.raises(DriftError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into tmp_path/.claude."""
    import shutil

    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _make_skill_result(stdout: str = "", returncode: int = 0):  # type: ignore[no-untyped-def]
    """Return a minimal SkillResult for dispatcher monkeypatching."""
    from superpowers_dispatch import SkillResult

    return SkillResult(skill="stub", returncode=returncode, stdout=stdout, stderr="")


def test_pre_merge_loop1_exits_on_clean_to_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop 1 returns immediately when first call already clean-to-go."""
    import pre_merge_cmd
    import superpowers_dispatch

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    _seed_plugin_local(tmp_path)

    calls = {"req": 0, "rcv": 0}

    def fake_requesting(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls["req"] += 1
        return _make_skill_result(stdout="Review: clean-to-go")

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls["rcv"] += 1
        return _make_skill_result(stdout="")

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_requesting)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    # Bypass drift: at state=done with current_task_id=None, the shipped
    # heuristic defaults to "[ ]" which triggers the done+open-tasks drift
    # rule -- unrelated to Loop 1 semantics under test.
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)
    # Loop 2 stub: bypass for Loop-1-only test; pre_merge_cmd may still call
    # _loop2 depending on Task order. Patch _loop2 to a no-op here.
    monkeypatch.setattr(
        pre_merge_cmd, "_loop2", lambda root, cfg, override, ns: None, raising=False
    )
    # Guard against unexpected MAGI verdict artifact write.
    import magi_dispatch

    monkeypatch.setattr(
        magi_dispatch,
        "write_verdict_artifact",
        lambda *a, **kw: None,
    )

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert calls["req"] == 1
    assert calls["rcv"] == 0


def test_pre_merge_loop1_applies_fixes_until_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Loop 1 calls receiving-code-review between iterations until clean-to-go."""
    import pre_merge_cmd
    import superpowers_dispatch

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    _seed_plugin_local(tmp_path)

    sequence = iter(
        [
            _make_skill_result(stdout="[WARNING] style issue"),
            _make_skill_result(stdout="Review: clean-to-go"),
        ]
    )

    calls = {"req": 0, "rcv": 0}

    def fake_requesting(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls["req"] += 1
        return next(sequence)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls["rcv"] += 1
        return _make_skill_result(stdout="")

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_requesting)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)
    monkeypatch.setattr(
        pre_merge_cmd, "_loop2", lambda root, cfg, override, ns: None, raising=False
    )
    import magi_dispatch

    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **kw: None)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert calls["req"] == 2
    assert calls["rcv"] == 1


def test_pre_merge_loop1_aborts_after_10_iterations_exit_7(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always [WARNING] -> Loop1DivergentError; dispatcher maps to exit 7."""
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, Loop1DivergentError

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    _seed_plugin_local(tmp_path)

    def fake_requesting(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="[WARNING] still unresolved")

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="")

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_requesting)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)

    with pytest.raises(Loop1DivergentError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert EXIT_CODES[Loop1DivergentError] == 7


# ---------------------------------------------------------------------------
# Task 21 -- Loop 2 tests (INV-28 degraded + INV-29 receiving-code-review).
# ---------------------------------------------------------------------------


def _make_verdict(
    verdict: str = "GO",
    degraded: bool = False,
    conditions: tuple[str, ...] = (),
    findings: tuple[dict[str, object], ...] = (),
) -> "MAGIVerdict":
    """Return a MAGIVerdict matching the magi_dispatch dataclass contract."""
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=verdict,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output=f'{{"verdict": "{verdict}"}}',
    )


def _patch_loop1_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub Loop 1 so Loop 2 tests can focus on MAGI semantics."""
    import pre_merge_cmd

    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)


def _seed_loop2_env(tmp_path: Path) -> None:
    """Seed all preconditions for /sbtdd pre-merge Loop 2 tests."""
    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    _seed_plugin_local(tmp_path)


def _patch_no_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    import pre_merge_cmd

    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)


def test_pre_merge_loop2_exits_on_full_go(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Loop 2 with GO full exits after 1 iteration and writes the verdict file."""
    import magi_dispatch
    import pre_merge_cmd

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)
    calls = {"magi": 0}

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        calls["magi"] += 1
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert calls["magi"] == 1
    artifact = tmp_path / ".claude" / "magi-verdict.json"
    assert artifact.exists()
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert data["degraded"] is False
    assert data["verdict"] == "GO"


def test_pre_merge_loop2_retries_on_degraded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-28: degraded verdict consumes iteration, re-invoke expected."""
    import magi_dispatch
    import pre_merge_cmd

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    sequence = iter(
        [
            _make_verdict("GO", degraded=True),
            _make_verdict("GO", degraded=False),
        ]
    )

    calls = {"magi": 0}

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        calls["magi"] += 1
        return next(sequence)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert calls["magi"] == 2


def test_pre_merge_loop2_strong_no_go_aborts_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """STRONG_NO_GO raises MAGIGateError on the first iteration."""
    import magi_dispatch
    import pre_merge_cmd
    from errors import MAGIGateError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    calls = {"magi": 0}

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        calls["magi"] += 1
        return _make_verdict("STRONG_NO_GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert calls["magi"] == 1


def test_pre_merge_loop2_go_with_caveats_blocks_gate_on_accepted_conditions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepted condition (low-risk or structural) now BLOCKS the gate.

    MAGI Loop 2 iter-3 redesign: ``_loop2`` no longer orchestrates a
    mini-cycle (the caller has nothing to stage, which produced three
    empty commits in iter 1/2). Instead it writes the accepted conditions
    to ``.claude/magi-conditions.md`` and raises :class:`MAGIGateError`
    (exit 8). The user applies the conditions via ``close-phase`` and
    re-runs ``pre-merge``.
    """
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import MAGIGateError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    calls = {"magi": 0}

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        calls["magi"] += 1
        return _make_verdict(
            "GO_WITH_CAVEATS",
            degraded=False,
            conditions=("fix docstring naming",),
        )

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="## Accepted\n- fix docstring naming\n")

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert calls["magi"] == 1
    assert (tmp_path / ".claude" / "magi-conditions.md").exists()


def test_pre_merge_loop2_aborts_after_max_iterations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Always HOLD -> MAGIGateError after magi_max_iterations (default 3)."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import MAGIGateError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    calls = {"magi": 0}

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        calls["magi"] += 1
        return _make_verdict("HOLD", degraded=False)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="## Accepted\n")

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert calls["magi"] == 3


def test_pre_merge_writes_magi_verdict_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After success, magi-verdict.json contains required fields."""
    import magi_dispatch
    import pre_merge_cmd

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict(
            "GO",
            degraded=False,
            conditions=(),
            findings=({"message": "m"},),
        )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    art = json.loads((tmp_path / ".claude" / "magi-verdict.json").read_text(encoding="utf-8"))
    assert "timestamp" in art
    assert art["verdict"] == "GO"
    assert art["degraded"] is False
    assert "conditions" in art
    assert "findings" in art


def test_pre_merge_loop2_rejects_unknown_threshold_override_with_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 5: unknown --magi-threshold -> ValidationError (not KeyError)."""
    import pre_merge_cmd
    from errors import ValidationError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    with pytest.raises(ValidationError):
        pre_merge_cmd.main(["--project-root", str(tmp_path), "--magi-threshold", "BANANA"])


def test_pre_merge_loop2_accepted_condition_emits_no_commits_and_writes_conditions_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAGI Loop 2 iter-3 redesign: accepted condition writes file, emits no commits.

    Replaces the pre-iter-3 contract that ``_loop2`` orchestrated a
    3-commit mini-cycle. ``_loop2`` cannot synthesize code edits (the
    fix diff lives in the caller), so the iter-1/2 design produced
    three empty commits. The redesign hands the accepted conditions to
    the user via ``.claude/magi-conditions.md`` and blocks the gate
    (exit 8). The user then applies the conditions via ``close-phase``
    (which has real TDD cycle support) and re-runs ``pre-merge``.
    """
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import MAGIGateError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict(
            "GO_WITH_CAVEATS",
            degraded=False,
            conditions=("refactor public API signature",),
        )

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="## Accepted\n- refactor public API signature\n")

    invocations: list[tuple[str, str]] = []

    # Guard: monkeypatch the ``commits`` module so any accidental call to
    # ``commits.create`` from within ``_loop2`` would register here. The
    # iter-3 redesign removed the mini-cycle orchestration; we assert
    # zero invocations to detect a regression to the empty-commit path.
    import commits as commits_module

    def fake_commit_create(prefix: str, message: str, cwd: str | None = None) -> str:
        invocations.append((prefix, message))
        return "stub"

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    monkeypatch.setattr(commits_module, "create", fake_commit_create)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    # No empty mini-cycle commits from _loop2 any more.
    assert invocations == []
    # Conditions file exists and contains the accepted condition.
    conditions_text = (tmp_path / ".claude" / "magi-conditions.md").read_text(encoding="utf-8")
    assert "refactor public API signature" in conditions_text


def test_pre_merge_loop2_rejected_condition_feeds_into_next_iteration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 1 rejected-path: rejected conditions feed into next MAGI invocation."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    sequence = iter(
        [
            _make_verdict(
                "GO_WITH_CAVEATS",
                degraded=False,
                conditions=("unreasonable redesign ask",),
            ),
            _make_verdict("GO", degraded=False),
        ]
    )

    iter_paths_seen: list[list[str]] = []

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        iter_paths_seen.append(list(context_paths))
        return next(sequence)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(
            stdout="## Rejected\n- unreasonable redesign ask (rationale: not in scope)\n"
        )

    commit_calls: list[str] = []

    import commits as commits_module

    def fake_commit_create(prefix: str, message: str, cwd: str | None = None) -> str:
        commit_calls.append(prefix)
        return "stub"

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    monkeypatch.setattr(commits_module, "create", fake_commit_create)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    # No mini-cycle commits because the only condition was rejected.
    assert commit_calls == []
    # Second invocation includes the feedback file as a context path.
    assert len(iter_paths_seen) == 2
    feedback_path = str(tmp_path / ".claude" / "magi-feedback.md")
    assert feedback_path in iter_paths_seen[1]


def test_parse_receiving_review_extracts_accepted_and_rejected_sections() -> None:
    """Parser returns both lists with bullet characters stripped."""
    import pre_merge_cmd

    stdout = (
        "Intro\n"
        "## Accepted\n"
        "- first condition\n"
        "- second condition\n"
        "\n"
        "## Rejected\n"
        "- rejected one (rationale: ...)\n"
    )
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == ["first condition", "second condition"]
    assert rejected == ["rejected one (rationale: ...)"]


def test_parse_receiving_review_handles_empty_sections() -> None:
    """Header with no bullets returns ([], [])."""
    import pre_merge_cmd

    stdout = "## Accepted\n\n"
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == []
    assert rejected == []


def test_parse_receiving_review_empty_stdout_returns_empty_lists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty stdout returns ([], []); _loop2 then raises ValidationError."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import ValidationError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=""))
    assert accepted == []
    assert rejected == []

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict(
            "GO_WITH_CAVEATS",
            degraded=False,
            conditions=("some condition",),
        )

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(stdout="")

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    with pytest.raises(ValidationError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])


def test_loop2_writes_magi_feedback_file_when_rejections_accumulate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rejections from iter 1 appear in .claude/magi-feedback.md on iter 2."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    sequence = iter(
        [
            _make_verdict(
                "GO_WITH_CAVEATS",
                degraded=False,
                conditions=("redo all tests",),
            ),
            _make_verdict("GO", degraded=False),
        ]
    )

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return next(sequence)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(
            stdout="## Rejected\n- redo all tests (rationale: out of scope)\n"
        )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    pre_merge_cmd.main(["--project-root", str(tmp_path)])
    feedback = (tmp_path / ".claude" / "magi-feedback.md").read_text(encoding="utf-8")
    assert "redo all tests" in feedback


def test_loop2_does_not_write_feedback_file_when_no_rejections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single GO full with no conditions: magi-feedback.md MUST NOT exist."""
    import magi_dispatch
    import pre_merge_cmd

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert not (tmp_path / ".claude" / "magi-feedback.md").exists()


# ---------------------------------------------------------------------------
# MAGI Loop 2 iter 3 redesign: ``_loop2`` writes accepted conditions to
# ``.claude/magi-conditions.md`` and raises :class:`MAGIGateError` instead
# of orchestrating a mini-cycle it cannot populate with real diffs.
# ---------------------------------------------------------------------------


def test_loop2_writes_conditions_file_and_exits_8_when_accepted_conditions_exist(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Accepted conditions -> ``.claude/magi-conditions.md`` + MAGIGateError."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, MAGIGateError

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict(
            "GO_WITH_CAVEATS",
            degraded=False,
            conditions=("tighten error message for timeout branch",),
        )

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(
            stdout="## Accepted\n- tighten error message for timeout branch\n"
        )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    with pytest.raises(MAGIGateError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    conditions_path = tmp_path / ".claude" / "magi-conditions.md"
    assert conditions_path.exists()
    body = conditions_path.read_text(encoding="utf-8")
    assert "tighten error message for timeout branch" in body
    assert EXIT_CODES[MAGIGateError] == 8


def test_loop2_returns_0_when_verdict_strong_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """STRONG_GO with no conditions: return normally, no conditions file."""
    import magi_dispatch
    import pre_merge_cmd

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return _make_verdict("STRONG_GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / ".claude" / "magi-conditions.md").exists()


def test_loop2_returns_0_when_no_conditions_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All MAGI conditions rejected by /receiving-code-review -> exit 0.

    Rejected conditions still feed the ``magi-feedback.md`` loop (sterile-
    loop breaker). The gate exits cleanly when the residual verdict is
    above threshold and no accepted conditions remain.
    """
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    sequence = iter(
        [
            _make_verdict(
                "GO_WITH_CAVEATS",
                degraded=False,
                conditions=("unjustified ask",),
            ),
            _make_verdict("GO", degraded=False),
        ]
    )

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return next(sequence)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(
            stdout="## Rejected\n- unjustified ask (rationale: out of scope)\n"
        )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert not (tmp_path / ".claude" / "magi-conditions.md").exists()


def test_loop2_still_writes_magi_feedback_md_for_rejected_conditions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rejected conditions still feed ``magi-feedback.md`` (sterile-loop breaker preserved)."""
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_loop2_env(tmp_path)
    _patch_no_drift(monkeypatch)
    _patch_loop1_clean(monkeypatch)

    sequence = iter(
        [
            _make_verdict(
                "GO_WITH_CAVEATS",
                degraded=False,
                conditions=("bogus condition",),
            ),
            _make_verdict("GO", degraded=False),
        ]
    )

    def fake_invoke(
        context_paths: list[str], timeout: int = 1800, cwd: str | None = None
    ) -> object:
        return next(sequence)

    def fake_receiving(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        return _make_skill_result(
            stdout="## Rejected\n- bogus condition (rationale: not applicable)\n"
        )

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)

    pre_merge_cmd.main(["--project-root", str(tmp_path)])
    feedback = (tmp_path / ".claude" / "magi-feedback.md").read_text(encoding="utf-8")
    assert "bogus condition" in feedback


# ---------------------------------------------------------------------------
# MAGI Loop 2 iter 1 Finding 7: tighten receiving-code-review parser
# against heading variations (##Accepted / ## ACCEPTED / mixed case).
# ---------------------------------------------------------------------------


def test_parse_receiving_review_handles_no_space_after_hashes() -> None:
    """Finding 7: ``##Accepted`` (no space after ##) must be recognised."""
    import pre_merge_cmd

    stdout = "##Accepted\n- cond 1\n\n##Rejected\n- cond 2\n"
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == ["cond 1"]
    assert rejected == ["cond 2"]


def test_parse_receiving_review_handles_uppercase_headers() -> None:
    """Finding 7: ``## ACCEPTED`` / ``## REJECTED`` upper-case recognised."""
    import pre_merge_cmd

    stdout = "## ACCEPTED\n- cond A\n\n## REJECTED\n- cond B\n"
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == ["cond A"]
    assert rejected == ["cond B"]


def test_parse_receiving_review_handles_multispace_after_hashes() -> None:
    """Finding 7: ``##   Accepted`` (multi-space) must be recognised."""
    import pre_merge_cmd

    stdout = "##   Accepted\n- cond X\n"
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == ["cond X"]
    assert rejected == []


def test_parse_receiving_review_handles_mixedcase_headers() -> None:
    """Finding 7: ``## aCCepteD`` / ``## reJecTed`` mixed-case recognised."""
    import pre_merge_cmd

    stdout = "## aCCepteD\n- cond 1\n\n## reJecTed\n- cond 2\n"
    accepted, rejected = pre_merge_cmd._parse_receiving_review(_make_skill_result(stdout=stdout))
    assert accepted == ["cond 1"]
    assert rejected == ["cond 2"]


def test_build_conditions_frontmatter_returns_valid_yaml_block_with_all_fields(
    tmp_path: Path,
) -> None:
    """Finding 3 (Caspar): ``_build_conditions_frontmatter`` helper contract.

    The helper is invoked once per ``_write_magi_conditions_file`` call
    but its output is self-contained enough to justify a dedicated
    test: it must return a well-formed YAML frontmatter block (opened
    and closed by ``---`` on their own lines) carrying exactly four
    keys (``generated_at``, ``magi_iteration``, ``pre_merge_head_sha``,
    ``verdict``) in the order Option A declares, with a trailing blank
    line so the caller can concatenate the body without extra plumbing.
    """
    import pre_merge_cmd

    verdict = _make_verdict("STRONG_GO", conditions=())
    fm = pre_merge_cmd._build_conditions_frontmatter(tmp_path, verdict, iteration=5)
    lines = fm.splitlines()
    assert lines[0] == "---"
    assert lines[-1] == ""  # trailing blank enforced via ``---\n\n``
    assert "---" in lines[1:-1]
    # Keys in declared order.
    body = [line for line in lines[1:-2] if line and line != "---"]
    assert body[0].startswith("generated_at:")
    assert body[1] == "magi_iteration: 5"
    assert body[2].startswith("pre_merge_head_sha:")
    assert body[3] == "verdict: STRONG_GO"


def test_write_magi_conditions_file_emits_frontmatter_for_traceability(
    tmp_path: Path,
) -> None:
    """Finding 3 (Caspar): conditions file header is a YAML frontmatter block.

    ``_write_magi_conditions_file`` overwrites ``.claude/magi-conditions.md``
    on every pre-merge invocation, losing prior iteration history.
    Option A mitigates this by embedding a YAML frontmatter block with
    ``generated_at`` (ISO 8601), ``magi_iteration`` (1-indexed int),
    ``pre_merge_head_sha`` (short SHA or ``unknown`` when not a git repo),
    and ``verdict`` so each overwrite is self-describing and a log
    reader can reconstruct the sequence post-hoc.
    """
    import subprocess as _subprocess

    import pre_merge_cmd

    # tmp_path is not a git repo; _build_conditions_frontmatter must
    # handle the missing-repo case gracefully (head_sha="unknown").
    _subprocess.run = _subprocess.run  # mypy no-op; keep import live

    verdict = _make_verdict("GO_WITH_CAVEATS", conditions=("cond 1",))
    path = pre_merge_cmd._write_magi_conditions_file(["cond 1"], tmp_path, verdict, iteration=2)
    body = path.read_text(encoding="utf-8")
    lines = body.splitlines()
    assert lines[0] == "---", f"first line must open frontmatter, got: {lines[0]!r}"
    # Find the closing '---' after the opener.
    close_idx = next((i for i, line in enumerate(lines[1:], start=1) if line == "---"), -1)
    assert close_idx > 0, "frontmatter block must close with '---'"
    frontmatter = "\n".join(lines[1:close_idx])
    assert "generated_at:" in frontmatter
    assert "magi_iteration: 2" in frontmatter
    assert "pre_merge_head_sha:" in frontmatter
    assert "verdict: GO_WITH_CAVEATS" in frontmatter


def test_write_magi_conditions_file_body_structure(tmp_path: Path) -> None:
    """Finding 1: conditions file body includes step-by-step recovery guidance.

    MAGI Loop 2 iter 3 Finding 1 (Balthasar): first-time users may not
    know the full state-machine transition after exit 8. The generated
    ``.claude/magi-conditions.md`` must include a concrete worked example
    showing the close-phase -> close-task -> pre-merge recovery
    sequence, plus an explicit pointer to ``.claude/magi-feedback.md``
    for the rejected-feedback loop.
    """
    import pre_merge_cmd

    verdict = _make_verdict("GO_WITH_CAVEATS", conditions=("cond A",))
    path = pre_merge_cmd._write_magi_conditions_file(
        ["cond A", "cond B"], tmp_path, verdict, iteration=2
    )
    body = path.read_text(encoding="utf-8")
    assert "## How to apply these conditions" in body
    assert "sbtdd close-phase --variant test" in body
    assert "sbtdd close-phase --variant fix" in body
    assert "sbtdd close-phase --variant refactor" in body
    assert "sbtdd close-task" in body
    assert "sbtdd pre-merge" in body
    assert ".claude/magi-feedback.md" in body


def test_gitignore_covers_magi_feedback_file() -> None:
    """MAGI Loop 2 iter 1 Finding 8: ``.claude/magi-feedback.md`` ignored.

    ``_write_magi_feedback_file`` writes rejection history to
    ``.claude/magi-feedback.md`` between MAGI iterations. The file MUST
    be gitignored so the TDD Red/Green/Refactor commits never accidentally
    ship it. Verified by scanning ``.gitignore`` for either an explicit
    ``magi-feedback.md`` entry or a blanket ``.claude/`` directory
    pattern (which the project already uses).
    """
    repo_root = Path(__file__).parent.parent
    gitignore_text = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert ".claude/" in gitignore_text or "magi-feedback.md" in gitignore_text, (
        "`.gitignore` must cover `.claude/magi-feedback.md` so pre-merge iter-debug state is never committed"
    )
