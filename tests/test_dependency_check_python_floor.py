# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for :func:`dependency_check._check_python_binary` (Plan D Task 5)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

import dependency_check
import subprocess_utils


def test_check_python_binary_accepts_3_9(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        return SimpleNamespace(returncode=0, stdout="Python 3.9.18\n", stderr="")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    result = dependency_check._check_python_binary()
    assert result.status == "OK"


def test_check_python_binary_accepts_3_12(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        return SimpleNamespace(returncode=0, stdout="Python 3.12.3\n", stderr="")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    result = dependency_check._check_python_binary()
    assert result.status == "OK"
    assert "3.12.3" in result.detail


def test_check_python_binary_rejects_3_8(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        return SimpleNamespace(returncode=0, stdout="Python 3.8.19\n", stderr="")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    result = dependency_check._check_python_binary()
    assert result.status == "BROKEN"
    assert "3.8.19" in result.detail
    assert "3.9" in (result.remediation or "")


def test_check_python_binary_rejects_2_7(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        return SimpleNamespace(returncode=0, stdout="Python 2.7.18\n", stderr="")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    result = dependency_check._check_python_binary()
    assert result.status == "BROKEN"


def test_check_python_binary_rejects_unparseable_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        return SimpleNamespace(returncode=0, stdout="Python\n", stderr="")

    monkeypatch.setattr(subprocess_utils, "run_with_timeout", fake_run)
    result = dependency_check._check_python_binary()
    assert result.status == "BROKEN"
    assert "parse" in result.detail.lower() or "unknown" in result.detail.lower()


def test_check_python_binary_handles_missing_binary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import shutil
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    result = dependency_check._check_python_binary()
    assert result.status == "MISSING"
