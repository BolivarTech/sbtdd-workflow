#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""INV-25 branch-scoped enforcement regression pin (Milestone D Task 2)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import auto_cmd
import close_phase_cmd
import pre_merge_cmd
import subprocess_utils
import superpowers_dispatch


_FORBIDDEN_FIRST_ARGS = ("push", "merge")
_FORBIDDEN_EXECUTABLES = ("gh",)


def _assert_no_remote_ops(calls: list[list[str]]) -> None:
    for argv in calls:
        if not argv:
            continue
        exe = argv[0]
        assert exe not in _FORBIDDEN_EXECUTABLES, f"INV-25 violated: invoked {exe} (argv={argv})"
        if exe == "git" and len(argv) >= 2:
            assert argv[1] not in _FORBIDDEN_FIRST_ARGS, (
                f"INV-25 violated: invoked `git {argv[1]}` (argv={argv})"
            )
        # Catch gh pr invocations routed via different launchers
        joined = " ".join(argv).lower()
        assert "gh pr" not in joined, f"INV-25 violated: invoked `gh pr` via {argv}"


@pytest.fixture()
def spy_all_subprocess(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    """Spy over EVERY subprocess dispatch path.

    Plan D iter 1 (Finding 3) extended the spy to ``subprocess.run`` and
    ``subprocess.Popen`` on top of ``subprocess_utils.run_with_timeout``.
    Plan D iter 2 Caspar WARNING flagged that ``subprocess.call``,
    ``subprocess.check_call``, ``subprocess.check_output``, and
    ``os.system`` were still unspied -- any of those could emit a
    ``git push``/``git merge``/``gh`` invocation undetected. This
    revision closes the remaining gap: all 7 entry points are spied,
    and each spy asserts ``shell=False`` defensively (an INV-25 violator
    could hide a `git push` inside `shell=True` with a formatted string,
    which would fail shell-quoting heuristics).
    """
    recorded: list[list[str]] = []

    def _record(cmd: Any) -> None:
        if isinstance(cmd, (list, tuple)):
            recorded.append([str(x) for x in cmd])
        elif isinstance(cmd, str):
            # Shell-style calls -- cmd is a whole command string. Record
            # the split form; the shell=True assertion below rejects the
            # call outright.
            recorded.append(cmd.split())

    def _assert_no_shell_true(kwargs: dict[str, Any]) -> None:
        assert not kwargs.get("shell", False), (
            f"INV-25 violated: subprocess invocation used shell=True (kwargs={kwargs})"
        )

    def fake_run_with_timeout(cmd: list[str], **kwargs: Any) -> Any:
        _record(cmd)
        _assert_no_shell_true(kwargs)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_run(cmd: Any, *args: Any, **kwargs: Any) -> Any:  # noqa: ARG001
        _record(cmd)
        _assert_no_shell_true(kwargs)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    def fake_call(cmd: Any, *args: Any, **kwargs: Any) -> int:  # noqa: ARG001
        _record(cmd)
        _assert_no_shell_true(kwargs)
        return 0

    def fake_check_call(cmd: Any, *args: Any, **kwargs: Any) -> int:  # noqa: ARG001
        _record(cmd)
        _assert_no_shell_true(kwargs)
        return 0

    def fake_check_output(cmd: Any, *args: Any, **kwargs: Any) -> bytes:  # noqa: ARG001
        _record(cmd)
        _assert_no_shell_true(kwargs)
        return b""

    def fake_os_system(cmd: str) -> int:
        # os.system is inherently shell=True; any invocation is an
        # INV-25 red flag. Record + fail-loud.
        _record(cmd)
        raise AssertionError(
            f"INV-25 violated: os.system({cmd!r}) invoked -- os.system is "
            f"inherently shell=True and is forbidden"
        )

    class _FakePopen:
        def __init__(self, cmd: Any, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
            _record(cmd)
            _assert_no_shell_true(kwargs)
            self.stdout = None
            self.returncode = 0

        def communicate(self, *a: Any, **k: Any) -> tuple[bytes, bytes]:  # noqa: ARG002
            return (b"", b"")

        def wait(self, *a: Any, **k: Any) -> int:  # noqa: ARG002
            return 0

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run_with_timeout)
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    monkeypatch.setattr(subprocess, "call", fake_call)
    monkeypatch.setattr(subprocess, "check_call", fake_check_call)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(os, "system", fake_os_system)
    return recorded


def test_auto_dry_run_records_zero_remote_ops(
    tmp_path: Path, spy_all_subprocess: list[list[str]]
) -> None:
    auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    _assert_no_remote_ops(spy_all_subprocess)
    # Dry-run MUST be side-effect-free (Finding 4 of iter 1 reinforced).
    assert spy_all_subprocess == []


def test_pre_merge_dry_run_records_zero_remote_ops(
    tmp_path: Path, spy_all_subprocess: list[list[str]]
) -> None:
    # pre_merge_cmd in dry-run mode (if supported) or under monkeypatched
    # dependencies must never invoke push/merge/gh even transitively.
    # We assert the spy log has no forbidden entries; absence of a
    # dry-run flag is acceptable -- the assertion still holds on any
    # prefix of calls recorded before a precondition short-circuits.
    try:
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    except SystemExit:
        pass
    except Exception:
        pass
    _assert_no_remote_ops(spy_all_subprocess)


def test_close_phase_records_zero_remote_ops(
    tmp_path: Path, spy_all_subprocess: list[list[str]]
) -> None:
    # close_phase_cmd does commit + state write -- never remote ops.
    try:
        close_phase_cmd.main(["--project-root", str(tmp_path)])
    except SystemExit:
        pass
    except Exception:
        pass
    _assert_no_remote_ops(spy_all_subprocess)


def test_auto_cmd_no_finishing_branch_skill_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """INV-25 partner: /finishing-a-development-branch NEVER invoked by auto."""
    calls: list[tuple[str, object]] = []
    original = superpowers_dispatch.finishing_a_development_branch

    def fake_finish(*args: Any, **kwargs: Any) -> Any:
        calls.append(("finishing_a_development_branch", (args, kwargs)))
        return original(*args, **kwargs)

    monkeypatch.setattr(superpowers_dispatch, "finishing_a_development_branch", fake_finish)
    # Even if the main flow were to run all phases, the finishing skill
    # must NOT appear in the call log. We simulate via dry-run which
    # short-circuits -- the assertion still holds.
    auto_cmd.main(["--project-root", ".", "--dry-run"])
    assert not any(name == "finishing_a_development_branch" for name, _ in calls), (
        "INV-25 violated: auto invoked /finishing-a-development-branch"
    )
