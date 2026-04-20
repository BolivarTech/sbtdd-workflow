from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError


def test_dependency_check_is_frozen_dataclass():
    from dependency_check import DependencyCheck

    chk = DependencyCheck(
        name="git",
        status="OK",
        detail="git version 2.43.0",
        remediation=None,
    )
    with pytest.raises(FrozenInstanceError):
        chk.status = "MISSING"  # type: ignore[misc]


def test_dependency_check_requires_four_fields():
    from dependency_check import DependencyCheck

    fields = set(DependencyCheck.__dataclass_fields__)
    assert fields == {"name", "status", "detail", "remediation"}


def test_check_status_values_restricted():
    from dependency_check import VALID_STATUSES

    assert VALID_STATUSES == ("OK", "MISSING", "BROKEN")


def test_dependency_report_aggregates_checks():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(
        checks=(
            DependencyCheck("python", "OK", "3.12.0", None),
            DependencyCheck(
                "tdd-guard", "MISSING", "not in PATH", "npm install -g @nizos/tdd-guard"
            ),
        )
    )
    assert len(rep.checks) == 2


def test_dependency_report_failed_returns_only_non_ok():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(
        checks=(
            DependencyCheck("python", "OK", "3.12.0", None),
            DependencyCheck("git", "MISSING", "not found", "install git"),
            DependencyCheck("magi", "BROKEN", "wrong version", "update"),
        )
    )
    failed = rep.failed()
    assert len(failed) == 2
    assert {c.name for c in failed} == {"git", "magi"}


def test_dependency_report_ok_returns_true_when_all_ok():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(
        checks=(
            DependencyCheck("python", "OK", "3.12", None),
            DependencyCheck("git", "OK", "2.43", None),
        )
    )
    assert rep.ok() is True


def test_dependency_report_ok_returns_false_when_any_non_ok():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(
        checks=(
            DependencyCheck("python", "OK", "3.12", None),
            DependencyCheck("git", "MISSING", "", "install git"),
        )
    )
    assert rep.ok() is False


def test_format_report_includes_all_failures_and_count():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(
        checks=(
            DependencyCheck(
                "tdd-guard",
                "MISSING",
                "Binary not found in PATH.",
                "npm install -g @nizos/tdd-guard",
            ),
            DependencyCheck(
                "magi",
                "MISSING",
                "Plugin not discoverable under ~/.claude/plugins/.",
                "/plugin marketplace add BolivarTech/magi",
            ),
        )
    )
    out = rep.format_report()
    assert "tdd-guard" in out
    assert "magi" in out
    assert "[MISSING]" in out
    assert "2 issues found" in out
    assert "No files were created" in out


def test_format_report_empty_when_all_ok():
    from dependency_check import DependencyCheck, DependencyReport

    rep = DependencyReport(checks=(DependencyCheck("python", "OK", "3.12", None),))
    assert rep.format_report() == ""


def test_check_python_passes_on_current_interpreter():
    from dependency_check import check_python

    chk = check_python()
    assert chk.name == "python"
    assert chk.status == "OK"
    assert "3." in chk.detail


def test_check_git_returns_missing_when_not_in_path(monkeypatch):
    from dependency_check import check_git

    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_git()
    assert chk.status == "MISSING"
    assert chk.remediation is not None


def test_check_git_returns_ok_when_present(monkeypatch):
    from dependency_check import check_git

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/git")

    class FakeProc:
        returncode = 0
        stdout = "git version 2.43.0\n"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_git()
    assert chk.status == "OK"
    assert "2.43" in chk.detail


def test_check_tdd_guard_binary_missing(monkeypatch):
    from dependency_check import check_tdd_guard_binary

    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_tdd_guard_binary()
    assert chk.status == "MISSING"
    assert "npm install -g" in (chk.remediation or "")


def test_check_tdd_guard_data_dir_writable(tmp_path):
    from dependency_check import check_tdd_guard_data_dir

    chk = check_tdd_guard_data_dir(project_root=tmp_path)
    assert chk.status == "OK"
    assert (tmp_path / ".claude" / "tdd-guard" / "data").exists()


def test_check_superpowers_missing_when_no_skills(tmp_path):
    from dependency_check import check_superpowers

    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "MISSING"
    assert "superpowers" in chk.detail.lower() or "plugin" in chk.detail.lower()


def test_check_superpowers_ok_with_all_twelve_skills(tmp_path):
    from dependency_check import SUPERPOWERS_SKILLS, check_superpowers

    base = tmp_path / "cache" / "superpowers" / "skills"
    for skill in SUPERPOWERS_SKILLS:
        (base / skill).mkdir(parents=True)
        (base / skill / "SKILL.md").write_text("# " + skill, encoding="utf-8")
    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "OK"


def test_check_superpowers_broken_when_partial(tmp_path):
    from dependency_check import SUPERPOWERS_SKILLS, check_superpowers

    base = tmp_path / "cache" / "superpowers" / "skills"
    # Install only the first 5 of 12 skills.
    for skill in SUPERPOWERS_SKILLS[:5]:
        (base / skill).mkdir(parents=True)
        (base / skill / "SKILL.md").write_text("# " + skill, encoding="utf-8")
    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "BROKEN"
    # Ensure the detail lists at least one missing skill.
    assert any(name in chk.detail for name in SUPERPOWERS_SKILLS[5:])


def test_check_magi_missing_when_no_scripts(tmp_path):
    from dependency_check import check_magi

    chk = check_magi(plugins_root=tmp_path)
    assert chk.status == "MISSING"


def test_check_magi_ok_with_skill_and_script(tmp_path):
    from dependency_check import check_magi

    base = tmp_path / "cache" / "magi" / "skills" / "magi"
    base.mkdir(parents=True)
    (base / "SKILL.md").write_text("# magi", encoding="utf-8")
    (base / "scripts").mkdir()
    (base / "scripts" / "run_magi.py").write_text("# run", encoding="utf-8")
    chk = check_magi(plugins_root=tmp_path)
    assert chk.status == "OK"


def test_check_claude_cli_missing_when_not_in_path(monkeypatch):
    from dependency_check import check_claude_cli

    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_claude_cli()
    assert chk.status == "MISSING"
    assert chk.name == "claude CLI"
    assert chk.remediation is not None


def test_check_claude_cli_ok_when_present(monkeypatch):
    from dependency_check import check_claude_cli

    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    class FakeProc:
        returncode = 0
        stdout = "claude-code 1.0.30\n"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_claude_cli()
    assert chk.status == "OK"
    assert "claude-code" in chk.detail or "1.0" in chk.detail


def test_check_claude_cli_broken_on_nonzero_returncode(monkeypatch):
    from dependency_check import check_claude_cli

    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "error"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_claude_cli()
    assert chk.status == "BROKEN"


def test_check_working_tree_ok_with_git_dir(tmp_path):
    from dependency_check import check_working_tree

    (tmp_path / ".git").mkdir()
    chk = check_working_tree(project_root=tmp_path)
    assert chk.status == "OK"


def test_check_working_tree_missing_without_git(tmp_path):
    from dependency_check import check_working_tree

    chk = check_working_tree(project_root=tmp_path)
    assert chk.status == "MISSING"
    assert "git init" in (chk.remediation or "")


def test_check_stack_toolchain_python_ok(monkeypatch):
    from dependency_check import check_stack_toolchain

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    class FakeProc:
        returncode = 0
        stdout = "version 1.0.0"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    checks = check_stack_toolchain("python")
    assert all(c.status == "OK" for c in checks), [c.name for c in checks if c.status != "OK"]
    names = {c.name for c in checks}
    assert names == {"python (pytest)", "python (ruff)", "python (mypy)"}


def test_check_stack_toolchain_rust_missing_tdd_guard_rust(monkeypatch):
    from dependency_check import check_stack_toolchain

    def fake_which(name: str) -> str | None:
        return None if name == "tdd-guard-rust" else f"/usr/bin/{name}"

    monkeypatch.setattr("shutil.which", fake_which)

    class FakeProc:
        returncode = 0
        stdout = "v1"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    checks = check_stack_toolchain("rust")
    # tdd-guard-rust missing -> BROKEN (blocks reporter); other cargo tools OK.
    broken = [c for c in checks if c.status == "MISSING"]
    assert len(broken) == 1
    assert "tdd-guard-rust" in broken[0].name


def test_check_stack_toolchain_rejects_unknown_stack():
    from dependency_check import check_stack_toolchain
    from errors import ValidationError

    with pytest.raises(ValidationError):
        check_stack_toolchain("haskell")
