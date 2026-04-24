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


def test_check_tdd_guard_binary_passes_resolved_path_to_subprocess(monkeypatch):
    """Windows: subprocess must receive the ``.cmd``-resolved path, not bare name.

    ``npm install -g @nizos/tdd-guard`` installs ``tdd-guard.cmd`` on Windows.
    Python's ``subprocess.run([...], shell=False)`` does not apply PATHEXT, so
    passing bare ``"tdd-guard"`` as argv[0] raises ``FileNotFoundError``
    (WinError 2) even when ``shutil.which("tdd-guard")`` succeeds. The check
    must resolve the path via ``shutil.which`` and forward the full path.
    Regression observed 2026-04-24 when ``/sbtdd auto`` preflight crashed on
    Windows.
    """
    from dependency_check import check_tdd_guard_binary

    resolved_path = r"C:\Users\jbolivarg\AppData\Roaming\npm\tdd-guard.CMD"
    monkeypatch.setattr("shutil.which", lambda name: resolved_path if name == "tdd-guard" else None)
    captured: dict = {}

    class FakeProc:
        returncode = 0
        stdout = "tdd-guard v2.0.0"
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    chk = check_tdd_guard_binary()
    assert chk.status == "OK"
    # The resolved full path must travel as argv[0]; never the bare name.
    assert captured["cmd"][0] == resolved_path
    assert captured["cmd"][1] == "--version"


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


def test_check_stack_toolchain_python_uses_python_m_invocation(monkeypatch):
    """Python tool checks MUST use ``python -m <module>``, not bare binary.

    Regression for the 2026-04-24 false-negative: on Windows, a stale
    ``pytest.EXE`` from an older Python install (Python 3.6 Scripts/ on
    PATH ahead of 3.14) resolved via shutil.which but crashed at
    ``pytest --version`` with returncode=1 -- even though Python 3.14's
    ``python -m pytest`` ran the 609-test suite cleanly. Similarly,
    ``ruff`` / ``mypy`` installed only as modules under the active
    interpreter (no Scripts/ entry point exposed to PATH) reported
    MISSING. The fix aligns the check with ``plugin.local.md``'s
    ``verification_commands`` (which already use ``python -m <tool>``).
    """
    import sys

    from dependency_check import check_stack_toolchain

    captured: list = []

    class FakeProc:
        returncode = 0
        stdout = "tool 1.0.0"
        stderr = ""

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured.append(cmd)
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    check_stack_toolchain("python")
    # All three Python-stack invocations must take the python -m form.
    assert len(captured) == 3
    for cmd in captured:
        assert cmd[0] == sys.executable, f"expected sys.executable as argv[0], got {cmd[0]!r}"
        assert cmd[1] == "-m", f"expected '-m' as argv[1], got {cmd[1]!r}"
        assert cmd[2] in {"pytest", "ruff", "mypy"}
        assert cmd[3] == "--version"


def test_check_python_tool_reports_missing_when_module_not_importable(monkeypatch):
    """python -m <tool> with 'No module named' stderr must map to MISSING."""
    from dependency_check import _check_python_module_tool

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "C:\\Python314\\python.exe: No module named ruff\n"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = _check_python_module_tool("ruff", "python (ruff)")
    assert chk.status == "MISSING"
    assert chk.remediation == "pip install ruff"


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


def test_check_environment_aggregates_all_eight_items(tmp_path, monkeypatch):
    """All eight fixed checks must run even if earlier ones fail (no short-circuit).

    Eight = 7 sec.S.1.3 mandatory deps + claude CLI (Task 4a / MAGI ckpt2 iter 2
    caspar WARNING). The term "7 deps" in CLAUDE.md External Dependencies remains
    accurate for the sec.S.1.3 contract; claude CLI is a companion check surfaced
    during pre-flight.
    """
    from dependency_check import check_environment

    # Ensure git present (so git check passes); force tdd-guard missing.

    def fake_which(name: str) -> str | None:
        return None if name == "tdd-guard" else f"/usr/bin/{name}"

    monkeypatch.setattr("shutil.which", fake_which)

    class FakeProc:
        returncode = 0
        stdout = "v1"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    # Plugins root empty -> superpowers + magi MISSING; but check_environment
    # still continues through all items.
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / ".git").mkdir()

    rep = check_environment(
        stack="python",
        project_root=project_root,
        plugins_root=plugins_root,
    )
    # Names collected confirm every stage ran.
    names = {c.name for c in rep.checks}
    # Non-toolchain names
    assert "python" in names
    assert "git" in names
    assert "tdd-guard" in names
    assert "tdd-guard data directory" in names
    assert "claude CLI" in names
    assert "superpowers plugin" in names
    assert "magi plugin" in names
    assert "git working tree" in names
    # Toolchain names (3 for python stack)
    assert "python (pytest)" in names
    assert "python (ruff)" in names
    assert "python (mypy)" in names


def test_check_environment_returns_dependency_report(tmp_path, monkeypatch):
    from dependency_check import DependencyReport, check_environment

    monkeypatch.setattr("shutil.which", lambda name: None)
    rep = check_environment(
        stack="python",
        project_root=tmp_path,
        plugins_root=tmp_path,
    )
    assert isinstance(rep, DependencyReport)
    assert rep.ok() is False


def test_check_stack_toolchain_rust_clippy_subcommand_failure_detected(monkeypatch):
    """cargo-clippy subcommand dispatch failure must surface as BROKEN.

    MAGI Loop 2 Milestone B iter 1 Finding 4 (caspar, WARNING): ``cargo-clippy``
    and ``cargo-fmt`` are shim binaries dispatched by the ``cargo`` driver. A
    shim present on PATH does not guarantee the underlying component is
    installed -- ``cargo clippy --version`` can still fail with non-zero exit
    (eg. ``error: 'clippy' is not installed for the toolchain``). The Rust
    toolchain check must therefore invoke ``cargo clippy --version`` (and
    ``cargo fmt --version``) as subcommand calls, not just ``cargo-clippy
    --version``, to catch this class of false-OK.

    Here we simulate: every binary is present on PATH, but ``cargo clippy
    --version`` returns non-zero. The check must report BROKEN for cargo-clippy.
    """
    from dependency_check import check_stack_toolchain

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    class OKProc:
        returncode = 0
        stdout = "v1"
        stderr = ""

    class FailProc:
        returncode = 101
        stdout = ""
        stderr = "error: 'clippy' is not installed for the toolchain"

    def fake_run(cmd, timeout, capture=True, cwd=None):
        # ['cargo', 'clippy', '--version'] or ['cargo', 'fmt', '--version']
        # must fail; every other command succeeds.
        if cmd[:2] == ["cargo", "clippy"] or cmd[:2] == ["cargo", "fmt"]:
            return FailProc()
        return OKProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    checks = check_stack_toolchain("rust")
    broken_clippy = [c for c in checks if "clippy" in c.name and c.status == "BROKEN"]
    assert broken_clippy, (
        f"expected BROKEN entry for cargo-clippy; got {[(c.name, c.status) for c in checks]}"
    )
    broken_fmt = [c for c in checks if "fmt" in c.name and c.status == "BROKEN"]
    assert broken_fmt, (
        f"expected BROKEN entry for cargo-fmt; got {[(c.name, c.status) for c in checks]}"
    )


def test_check_stack_toolchain_rust_clippy_subcommand_success(monkeypatch):
    """When cargo clippy --version / cargo fmt --version succeed, status is OK."""
    from dependency_check import check_stack_toolchain
    from types import SimpleNamespace

    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    # Plan D Task 6: Rust shims are now regex-validated, so each binary
    # must produce the output its own regex accepts (``clippy ...`` for
    # cargo-clippy, ``rustfmt ...`` for cargo-fmt, etc.). A single fixed
    # stdout is no longer sufficient.
    def fake_run(cmd, timeout, capture=True, cwd=None):
        if cmd[:2] == ["cargo", "clippy"]:
            stdout = "clippy 0.1.77\n"
        elif cmd[:2] == ["cargo", "fmt"]:
            stdout = "rustfmt 1.7.0-stable\n"
        elif cmd[0] == "cargo-nextest":
            stdout = "cargo-nextest-nextest 0.9.70\n"
        elif cmd[0] == "cargo-audit":
            stdout = "cargo-audit-audit 0.20.0\n"
        else:
            stdout = f"{cmd[0]} 1.0.0\n"
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="")

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    checks = check_stack_toolchain("rust")
    clippy = [c for c in checks if "clippy" in c.name]
    fmt = [c for c in checks if "fmt" in c.name]
    assert clippy and clippy[0].status == "OK"
    assert fmt and fmt[0].status == "OK"


def test_check_environment_never_raises_on_failing_checks(tmp_path, monkeypatch):
    """Even when every single check fails, check_environment returns a report."""
    from dependency_check import check_environment

    monkeypatch.setattr("shutil.which", lambda name: None)
    rep = check_environment(
        stack="rust",
        project_root=tmp_path,
        plugins_root=tmp_path,
    )
    # 8 fixed checks (7 sec.S.1.3 deps + claude CLI from Task 4a) + 6 rust
    # toolchain checks = 14 total; all failing.
    assert len(rep.checks) >= 14
    assert rep.ok() is False
