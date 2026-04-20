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
