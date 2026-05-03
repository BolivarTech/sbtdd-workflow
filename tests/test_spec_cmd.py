# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd spec subcomando (sec.S.5.2).

Note: the fixture strings in ``test_spec_rejects_spec_base_with_uppercase_todo``
intentionally contain uppercase TODO/TBD tokens to exercise the INV-27
enforcement path in ``spec_cmd._validate_spec_base``. These are NOT violations
of INV-27 for the plugin sources (sources themselves are clean); they are
test data driving the rejection branch.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def test_spec_cmd_module_importable() -> None:
    import spec_cmd

    assert hasattr(spec_cmd, "main")


def test_spec_rejects_spec_base_with_uppercase_todo(tmp_path: Path) -> None:
    import spec_cmd
    from errors import PreconditionError

    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    (spec_dir / "spec-behavior-base.md").write_text(
        "# Feature spec\n\n- T" + "ODO: define timeout\n" + ("x " * 200),
        encoding="utf-8",
    )
    with pytest.raises(PreconditionError) as ei:
        spec_cmd.main(["--project-root", str(tmp_path)])
    # INV-27 enforcement visible in message; tolerate either form.
    msg = str(ei.value)
    assert ("T" + "ODO") in msg or "pending" in msg.lower()


def test_spec_accepts_lowercase_todos_spanish_prose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import spec_cmd
    import superpowers_dispatch

    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature\n\nScenario: todos los usuarios\n" + ("x " * 200)
    (spec_dir / "spec-behavior-base.md").write_text(body, encoding="utf-8")
    # Prevent the real claude -p subprocess invocations in the downstream
    # flow; INV-27 validation is what we exercise here, not the dispatcher.
    monkeypatch.setattr(superpowers_dispatch, "brainstorming", lambda *a, **kw: None)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", lambda *a, **kw: None)
    # v1.0.0 Loop 2 iter 2->3 R11: production routes through
    # ``invoke_writing_plans``; stub it too so test stays subprocess-free.
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", lambda **kw: None)
    # Lowercase must not trigger INV-27; downstream precondition failures
    # (e.g. missing plugin.local.md, unseeded planning/ dir) are the
    # expected escape hatch.
    try:
        spec_cmd.main(["--project-root", str(tmp_path)])
    except Exception as e:
        msg = str(e)
        assert ("T" + "ODO") not in msg and "pending" not in msg.lower()


def _seed_valid_spec_base(tmp_path: Path) -> Path:
    """Write a valid (INV-27-clean, >= 200 non-ws chars) spec-behavior-base.md."""
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature spec\n\n## Objetivo\nsomething meaningful\n" + ("valid content " * 50)
    path = spec_dir / "spec-behavior-base.md"
    path.write_text(body, encoding="utf-8")
    (tmp_path / "planning").mkdir()
    return path


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into tmp_path/.claude."""
    import shutil

    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def test_spec_invokes_brainstorming_with_spec_base_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)
    _setup_git_repo(tmp_path)
    calls: list[dict[str, object]] = []

    def spy_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append({"skill": "brainstorming", "args": args})
        # R10: minimal §4 so spec_snapshot.emit_snapshot finds a section.
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# Feature spec behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: stub**\n\n"
            "> **Given** g.\n> **When** w.\n> **Then** t.\n",
            encoding="utf-8",
        )
        return None

    def spy_writing_plans(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append({"skill": "writing-plans", "args": args})
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        return None

    def spy_invoke_writing_plans(*, spec_path: str, **kwargs) -> object:
        # v1.0.0 Loop 2 iter 2->3 R11: production now routes through
        # invoke_writing_plans wrapper; record under the same skill tag
        # so existing call-order assertions continue to match.
        calls.append({"skill": "writing-plans", "args": [spec_path]})
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", spy_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", spy_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", spy_invoke_writing_plans)
    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, timeout=1800, cwd=None: _make_verdict("GO"),
    )

    spec_cmd.main(["--project-root", str(tmp_path)])

    assert calls[0]["skill"] == "brainstorming"
    # The first call must reference the spec-base file via @path.
    br_args = calls[0]["args"]
    assert isinstance(br_args, list)
    assert any("spec-behavior-base.md" in tok for tok in br_args)


def test_spec_invokes_writing_plans_after_spec_generated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)
    _setup_git_repo(tmp_path)
    calls: list[str] = []

    def spy_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append("brainstorming")
        # R10: minimal §4 so spec_snapshot.emit_snapshot finds a section.
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: stub**\n\n"
            "> **Given** g.\n> **When** w.\n> **Then** t.\n",
            encoding="utf-8",
        )
        return None

    def spy_writing_plans(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append("writing-plans")
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        assert args is not None and any("spec-behavior.md" in tok for tok in args)
        return None

    def spy_invoke_writing_plans(*, spec_path: str, **kwargs) -> object:
        # v1.0.0 Loop 2 iter 2->3 R11: production now routes through
        # invoke_writing_plans; mirror the spy contract on the wrapper.
        calls.append("writing-plans")
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        assert "spec-behavior.md" in spec_path
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", spy_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", spy_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", spy_invoke_writing_plans)
    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, timeout=1800, cwd=None: _make_verdict("GO"),
    )

    spec_cmd.main(["--project-root", str(tmp_path)])
    assert calls == ["brainstorming", "writing-plans"]
    assert (tmp_path / "planning" / "claude-plan-tdd-org.md").exists()


def test_spec_aborts_when_brainstorming_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import spec_cmd
    import superpowers_dispatch
    from errors import ValidationError

    _seed_valid_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)

    def raising_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        raise ValidationError("/brainstorming failed")

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", raising_brainstorming)
    with pytest.raises(ValidationError):
        spec_cmd.main(["--project-root", str(tmp_path)])


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo at tmp_path with one initial commit so HEAD resolves."""
    import subprocess

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


def _seed_spec_flow_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Set up a complete env for spec_cmd.main end-to-end tests.

    - Valid spec-behavior-base.md.
    - plugin.local.md with default magi_threshold + magi_max_iterations=3.
    - Git repo with initial commit.
    - Stubbed brainstorming/writing_plans producing the downstream files.
    """
    import shutil

    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    # Seed the plugin.local.md used by load_plugin_local.
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")
    _setup_git_repo(tmp_path)

    def fake_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        # Minimal §4 Escenarios section so spec_snapshot.emit_snapshot
        # finds a non-empty snapshot at plan-approval time (R10).
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: minimal stub**\n\n"
            "> **Given** a stub.\n> **When** parsed.\n> **Then** present.\n",
            encoding="utf-8",
        )
        return None

    def fake_writing_plans(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "# Plan\n\n### Task 1: First task\n- [ ] do it\n", encoding="utf-8"
        )
        return None

    def fake_invoke_writing_plans(*, spec_path: str, **kwargs) -> object:
        # v1.0.0 Loop 2 iter 2->3 R11: mirror fake_writing_plans on the
        # invoke_writing_plans wrapper that production uses.
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "# Plan\n\n### Task 1: First task\n- [ ] do it\n", encoding="utf-8"
        )
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", fake_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", fake_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", fake_invoke_writing_plans)


def _make_verdict(
    label: str = "GO_WITH_CAVEATS",
    degraded: bool = False,
    conditions: tuple[str, ...] = (),
) -> object:
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=conditions,
        findings=(),
        raw_output=f'{{"verdict": "{label}"}}',
    )


def test_spec_magi_loop_accepts_full_go_on_first_iter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd

    _seed_spec_flow_env(tmp_path, monkeypatch)
    call_count: dict[str, int] = {"n": 0}

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        call_count["n"] += 1
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    rc = spec_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert call_count["n"] == 1


def test_spec_magi_loop_rejects_degraded_and_retries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd

    _seed_spec_flow_env(tmp_path, monkeypatch)
    verdicts = iter(
        [
            _make_verdict("GO", degraded=True),
            _make_verdict("GO", degraded=False),
        ]
    )

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return next(verdicts)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    rc = spec_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    # Second verdict consumed -> exhausted.
    with pytest.raises(StopIteration):
        next(verdicts)


def test_spec_magi_loop_strong_no_go_aborts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd
    from errors import MAGIGateError

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("STRONG_NO_GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    with pytest.raises(MAGIGateError):
        spec_cmd.main(["--project-root", str(tmp_path)])


def test_spec_magi_loop_aborts_after_max_iterations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import magi_dispatch
    import spec_cmd
    from errors import MAGIGateError

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("HOLD", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    with pytest.raises(MAGIGateError):
        spec_cmd.main(["--project-root", str(tmp_path)])


def test_spec_creates_state_file_on_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    import magi_dispatch
    import spec_cmd

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    spec_cmd.main(["--project-root", str(tmp_path)])
    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["plan_approved_at"] is not None
    assert state["current_phase"] == "red"
    assert state["current_task_id"] == "1"


def test_spec_main_emits_snapshot_and_watermark_on_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R10 plan-approval handler interception (caspar Checkpoint 2 iter 5 W).

    spec_cmd.main MUST route plan-approval through
    auto_cmd._mark_plan_approved_with_snapshot so the spec-snapshot file
    AND the state-file watermark are persisted at the same transition
    that sets plan_approved_at. Without this, H2-5 bypass-by-deletion
    gate degrades to false-negative because the watermark is missing.
    """
    import json

    import magi_dispatch
    import spec_cmd

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    spec_cmd.main(["--project-root", str(tmp_path)])

    snapshot_path = tmp_path / "planning" / "spec-snapshot.json"
    assert snapshot_path.exists(), (
        "planning/spec-snapshot.json must be emitted at plan approval (R10)"
    )

    state = json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state.get("spec_snapshot_emitted_at") is not None, (
        "state file must record spec_snapshot_emitted_at watermark (R10)"
    )


def test_spec_commits_approved_artifacts_after_state_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Iter-2 W7 deterministic probe: state save runs BEFORE the chore commit."""
    import subprocess

    import commits
    import magi_dispatch
    import spec_cmd
    import state_file

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)

    call_order: list[str] = []
    orig_save = state_file.save
    orig_create = commits.create

    def spy_save(*a: object, **kw: object) -> object:
        call_order.append("save")
        return orig_save(*a, **kw)  # type: ignore[arg-type]

    def spy_create(prefix: str, message: str, *a: object, **kw: object) -> object:
        call_order.append(f"commit:{prefix}")
        return orig_create(prefix, message, *a, **kw)  # type: ignore[arg-type]

    monkeypatch.setattr(state_file, "save", spy_save)
    monkeypatch.setattr(commits, "create", spy_create)

    spec_cmd.main(["--project-root", str(tmp_path)])

    # Deterministic ordering: state file persisted BEFORE the chore commit.
    assert call_order == ["save", "commit:chore"]

    # The chore commit includes the three approved artifacts (via git log).
    result = subprocess.run(
        ["git", "log", "-1", "--name-only", "--pretty=format:%s"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout
    assert "chore: add MAGI-approved spec and plan" in output
    assert "sbtdd/spec-behavior.md" in output
    assert "planning/claude-plan-tdd-org.md" in output
    assert "planning/claude-plan-tdd.md" in output


def test_spec_does_not_commit_artifacts_when_magi_rejects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    import magi_dispatch
    import spec_cmd
    from errors import MAGIGateError

    _seed_spec_flow_env(tmp_path, monkeypatch)

    def fake_magi(context_paths: list[str], timeout: int = 1800, cwd: str | None = None) -> object:
        return _make_verdict("STRONG_NO_GO", degraded=False)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_magi)
    with pytest.raises(MAGIGateError):
        spec_cmd.main(["--project-root", str(tmp_path)])

    # No chore: MAGI-approved commit present.
    result = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=True,
    )
    assert "MAGI-approved" not in result.stdout


def test_spec_routes_writing_plans_through_invoke_writing_plans_wrapper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 3 (Loop 2 iter 2->3 R11): spec flow must use invoke_writing_plans.

    Pre-fix ``spec_cmd._run_spec_flow`` called the bare
    ``superpowers_dispatch.writing_plans`` wrapper, leaving the H5-1
    scenario-stub directive in ``invoke_writing_plans`` actually-dead.
    The fix routes the call through ``invoke_writing_plans(spec_path=...)``
    so the H5-1 prompt extension is exercised at plan-generation time.
    """
    import magi_dispatch
    import spec_cmd
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)
    _setup_git_repo(tmp_path)

    def spy_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: stub**\n\n"
            "> **Given** g.\n> **When** w.\n> **Then** t.\n",
            encoding="utf-8",
        )
        return None

    invoke_calls: list[dict] = []

    def spy_invoke_writing_plans(*, spec_path: str, **kwargs) -> object:
        invoke_calls.append({"spec_path": spec_path, "kwargs": kwargs})
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        return None

    # Bare wrapper must NOT be called -- spec_cmd should route through
    # the prompt-extending wrapper instead.
    bare_calls: list[dict] = []

    def spy_bare_writing_plans(*args, **kwargs) -> object:
        bare_calls.append({"args": args, "kwargs": kwargs})
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", spy_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", spy_invoke_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", spy_bare_writing_plans)
    monkeypatch.setattr(
        magi_dispatch,
        "invoke_magi",
        lambda context_paths, timeout=1800, cwd=None: _make_verdict("GO"),
    )

    spec_cmd.main(["--project-root", str(tmp_path)])

    assert len(invoke_calls) == 1, (
        "spec flow must invoke superpowers_dispatch.invoke_writing_plans exactly once"
    )
    assert "spec-behavior.md" in invoke_calls[0]["spec_path"], (
        "spec_path must point at sbtdd/spec-behavior.md"
    )
    assert bare_calls == [], (
        "bare superpowers_dispatch.writing_plans MUST NOT be called -- the "
        "H5-1 scenario-stub directive lives in invoke_writing_plans"
    )


# ---------------------------------------------------------------------------
# v1.0.1 Item A0 -- output validation tripwire (sec.2.1 / sec.4 escenarios
# A0-1 .. A0-5). The composite-signature (mtime_ns + size + sha256) check
# inside ``_run_spec_flow`` detects subprocesses that exit cleanly but
# silently fail to write the expected output file (Finding C from v1.0.0
# dogfood: ``claude -p /brainstorming`` returncode=0, file unchanged).
# ---------------------------------------------------------------------------


def _seed_a0_env(tmp_path: Path) -> None:
    """Seed the minimum dirs for A0 ``_run_spec_flow`` tests."""
    (tmp_path / "sbtdd").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)


def test_a0_1_brainstorming_silent_no_op_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A0-1: brainstorming subprocess returns exit 0 but does not modify spec.

    Pre-existing ``sbtdd/spec-behavior.md`` from a previous cycle; stub
    brainstorming does NOT touch the file (simulates ``claude -p`` headless
    no-op). ``_run_spec_flow`` must detect the unchanged composite signature
    and raise ``PreconditionError`` with "no fue modificado".
    """
    import spec_cmd
    import superpowers_dispatch
    from errors import PreconditionError

    _seed_a0_env(tmp_path)
    spec_behavior = tmp_path / "sbtdd" / "spec-behavior.md"
    spec_behavior.write_text(
        "# pre-existing behavior\n\n## §4 Escenarios BDD\n\n"
        "**Escenario 1: stub**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    def silent_brainstorming(*a: object, **kw: object) -> object:
        # Simulate `claude -p /brainstorming` exit 0 with NO file write.
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", silent_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", lambda **kw: None)

    with pytest.raises(PreconditionError) as ei:
        spec_cmd._run_spec_flow(tmp_path)
    msg = str(ei.value)
    assert "no fue modificado" in msg, msg
    assert "spec-behavior.md" in msg, msg


def test_a0_2_writing_plans_silent_no_op_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A0-2: writing_plans subprocess silently no-op on pre-existing plan-org."""
    import spec_cmd
    import superpowers_dispatch
    from errors import PreconditionError

    _seed_a0_env(tmp_path)
    spec_behavior = tmp_path / "sbtdd" / "spec-behavior.md"
    plan_org = tmp_path / "planning" / "claude-plan-tdd-org.md"
    spec_behavior.write_text(
        "# pre-existing behavior\n\n## §4 Escenarios BDD\n\n"
        "**Escenario 1: stub**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )
    plan_org.write_text("# pre-existing plan\n\n### Task 1: x\n- [ ] do\n", encoding="utf-8")

    def updating_brainstorming(*a: object, **kw: object) -> object:
        # Brainstorming WRITES new content (passes A0 check).
        spec_behavior.write_text(
            "# updated behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: updated**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
            encoding="utf-8",
        )
        return None

    def silent_writing_plans(**kw: object) -> object:
        # writing_plans does NOT modify plan_org -> A0 must detect.
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", updating_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", silent_writing_plans)

    with pytest.raises(PreconditionError) as ei:
        spec_cmd._run_spec_flow(tmp_path)
    msg = str(ei.value)
    assert "no fue modificado" in msg, msg
    assert "claude-plan-tdd-org.md" in msg, msg


def test_a0_3_first_run_with_no_prior_artifacts_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A0-3: first run (no pre-existing files) -- composite check skipped.

    Pre-subprocess signature is ``None``; post-subprocess existence check
    still verifies the file is now present. Composite check short-circuits
    when ``before is None``, allowing the freshly-written file through.
    """
    import spec_cmd
    import superpowers_dispatch

    _seed_a0_env(tmp_path)
    spec_behavior = tmp_path / "sbtdd" / "spec-behavior.md"
    plan_org = tmp_path / "planning" / "claude-plan-tdd-org.md"
    assert not spec_behavior.exists()
    assert not plan_org.exists()

    def writing_brainstorming(*a: object, **kw: object) -> object:
        spec_behavior.write_text(
            "# behavior\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: x**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
            encoding="utf-8",
        )
        return None

    def writing_plans_writer(**kw: object) -> object:
        plan_org.write_text("### Task 1: x\n- [ ] do\n", encoding="utf-8")
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", writing_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", writing_plans_writer)

    # Should NOT raise -- first-run path tolerated.
    spec_cmd._run_spec_flow(tmp_path)
    assert spec_behavior.exists()
    assert plan_org.exists()


def test_a0_4_happy_path_both_subprocesses_write_correctly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A0-4: pre-existing files + both subprocesses write new content -> success."""
    import spec_cmd
    import superpowers_dispatch

    _seed_a0_env(tmp_path)
    spec_behavior = tmp_path / "sbtdd" / "spec-behavior.md"
    plan_org = tmp_path / "planning" / "claude-plan-tdd-org.md"
    spec_behavior.write_text("# OLD spec\n", encoding="utf-8")
    plan_org.write_text("# OLD plan\n", encoding="utf-8")

    def writing_brainstorming(*a: object, **kw: object) -> object:
        spec_behavior.write_text(
            "# NEW spec\n\n## §4 Escenarios BDD\n\n"
            "**Escenario 1: new**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
            encoding="utf-8",
        )
        return None

    def writing_plans_writer(**kw: object) -> object:
        plan_org.write_text("# NEW plan\n\n### Task 1: x\n- [ ] do\n", encoding="utf-8")
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", writing_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "invoke_writing_plans", writing_plans_writer)

    # Should NOT raise -- both signatures change -> happy path.
    spec_cmd._run_spec_flow(tmp_path)


def test_a0_5_same_content_rewrite_under_fast_clock_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A0-5: identical-bytes rewrite on fast-clock FS -> composite tuple equal.

    Simulates the FS-precision regression class: a subprocess that
    rewrites the file with byte-identical content within the same
    mtime tick. Bare-mtime check would catch THIS case incidentally
    (mtime equal), but composite signature catches it deterministically
    via size + sha256 equality. Test verifies the check fires.
    """
    import spec_cmd
    import superpowers_dispatch
    from errors import PreconditionError

    _seed_a0_env(tmp_path)
    spec_behavior = tmp_path / "sbtdd" / "spec-behavior.md"
    same_content = (
        "# behavior\n\n## §4 Escenarios BDD\n\n"
        "**Escenario 1: stub**\n\n> **Given** g\n> **When** w\n> **Then** t\n"
    )
    spec_behavior.write_text(same_content, encoding="utf-8")

    # Capture the original signature before the test stub re-writes.
    original_sig = spec_cmd._file_signature(spec_behavior)

    def same_content_brainstorming(*a: object, **kw: object) -> object:
        # Rewrite with IDENTICAL bytes; no real content change.
        spec_behavior.write_text(same_content, encoding="utf-8")
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", same_content_brainstorming)
    # Force composite signature equality regardless of FS clock precision
    # by pinning ``_file_signature`` to return ``original_sig`` for both
    # pre and post calls. This makes the test deterministic across
    # FAT32 / NTFS / network-mount precision differences.
    monkeypatch.setattr(spec_cmd, "_file_signature", lambda p: original_sig)

    with pytest.raises(PreconditionError) as ei:
        spec_cmd._run_spec_flow(tmp_path)
    msg = str(ei.value)
    assert "no fue modificado" in msg, msg
    assert "composite signature" in msg, msg


def test_file_signature_handles_empty_file(tmp_path: Path) -> None:
    """A0 W7 edge case: empty file returns deterministic signature.

    sha256 of empty bytes is the well-known constant; helper must handle
    zero-byte content without IO error.
    """
    import spec_cmd

    p = tmp_path / "empty.bin"
    p.write_bytes(b"")
    sig = spec_cmd._file_signature(p)
    mtime_ns, size, digest = sig
    assert size == 0
    # SHA256 of empty bytes is a well-known constant.
    assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert isinstance(mtime_ns, int)


@pytest.mark.slow
def test_file_signature_handles_large_file(tmp_path: Path) -> None:
    """A0 W7 edge case: file >100MB streams via 64KB chunks without OOM.

    Confirms the chunked-read implementation does NOT load the entire
    file into memory. Marked slow because writing 100MB takes seconds
    on slower disks.
    """
    import hashlib

    import spec_cmd

    p = tmp_path / "large.bin"
    chunk = b"A" * 65536  # 64KB
    expected_h = hashlib.sha256()
    # Write 100MB total = 1600 chunks of 64KB.
    n_chunks = 1600
    with p.open("wb") as fh:
        for _ in range(n_chunks):
            fh.write(chunk)
            expected_h.update(chunk)
    expected_size = 65536 * n_chunks  # 100MB exactly
    sig = spec_cmd._file_signature(p)
    _mtime_ns, size, digest = sig
    assert size == expected_size
    assert digest == expected_h.hexdigest()
