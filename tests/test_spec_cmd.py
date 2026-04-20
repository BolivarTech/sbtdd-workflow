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
    monkeypatch.setattr(
        superpowers_dispatch,
        "brainstorming",
        lambda *a, **kw: None,
    )
    monkeypatch.setattr(
        superpowers_dispatch,
        "writing_plans",
        lambda *a, **kw: None,
    )
    # Lowercase must not trigger INV-27; may still fail on later precondition.
    try:
        spec_cmd.main(["--project-root", str(tmp_path)])
    except Exception as e:
        assert ("T" + "ODO") not in str(e) and "pending" not in str(e).lower()


def _seed_valid_spec_base(tmp_path: Path) -> Path:
    """Write a valid (INV-27-clean, >= 200 non-ws chars) spec-behavior-base.md."""
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature spec\n\n## Objetivo\nsomething meaningful\n" + ("valid content " * 50)
    path = spec_dir / "spec-behavior-base.md"
    path.write_text(body, encoding="utf-8")
    (tmp_path / "planning").mkdir()
    return path


def test_spec_invokes_brainstorming_with_spec_base_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import spec_cmd
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    calls: list[dict[str, object]] = []

    def spy_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append({"skill": "brainstorming", "args": args})
        # Side effect: produce the downstream file so the validator moves on.
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# Feature spec behavior\nContent\n", encoding="utf-8"
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

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", spy_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", spy_writing_plans)
    spec_cmd.main(["--project-root", str(tmp_path)])

    assert calls[0]["skill"] == "brainstorming"
    # The first call must reference the spec-base file via @path.
    br_args = calls[0]["args"]
    assert isinstance(br_args, list)
    assert any("spec-behavior-base.md" in tok for tok in br_args)


def test_spec_invokes_writing_plans_after_spec_generated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import spec_cmd
    import superpowers_dispatch

    _seed_valid_spec_base(tmp_path)
    calls: list[str] = []

    def spy_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append("brainstorming")
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\nContent\n", encoding="utf-8"
        )
        return None

    def spy_writing_plans(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        calls.append("writing-plans")
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            "### Task 1: sample\n- [ ] work\n", encoding="utf-8"
        )
        # writing_plans arg should reference spec-behavior.md
        assert args is not None and any("spec-behavior.md" in tok for tok in args)
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", spy_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", spy_writing_plans)
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

    def raising_brainstorming(
        args: list[str] | None = None, timeout: int = 600, cwd: str | None = None
    ) -> object:
        raise ValidationError("/brainstorming failed")

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", raising_brainstorming)
    with pytest.raises(ValidationError):
        spec_cmd.main(["--project-root", str(tmp_path)])
