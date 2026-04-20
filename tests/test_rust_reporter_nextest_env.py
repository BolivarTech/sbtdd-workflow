# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for NEXTEST_EXPERIMENTAL_LIBTEST_JSON env-var gate (Plan D Task 7)."""

from __future__ import annotations

from typing import Any

import pytest

from errors import ValidationError
from reporters import rust_reporter


def test_ensure_env_var_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXTEST_EXPERIMENTAL_LIBTEST_JSON", raising=False)
    with pytest.raises(ValidationError) as exc:
        rust_reporter.ensure_nextest_experimental_env()
    assert "NEXTEST_EXPERIMENTAL_LIBTEST_JSON" in str(exc.value)
    assert "1" in str(exc.value)


def test_ensure_env_var_raises_when_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTEST_EXPERIMENTAL_LIBTEST_JSON", "0")
    with pytest.raises(ValidationError):
        rust_reporter.ensure_nextest_experimental_env()


def test_ensure_env_var_accepts_one(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXTEST_EXPERIMENTAL_LIBTEST_JSON", "1")
    rust_reporter.ensure_nextest_experimental_env()  # No raise.


def test_run_pipeline_fails_loud_when_env_var_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NEXTEST_EXPERIMENTAL_LIBTEST_JSON", raising=False)

    calls: list[Any] = []

    class _FakePopen:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            calls.append((args, kwargs))
            raise AssertionError("Popen called before env var check")

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    with pytest.raises(ValidationError, match="NEXTEST_EXPERIMENTAL_LIBTEST_JSON"):
        rust_reporter.run_pipeline()
    assert calls == []


def test_run_pipeline_happy_path_with_env_var_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Finding 7 (Plan D iter 1): no `check_env` escape hatch -- the
    # pre-check is production-safety logic, not test plumbing. Tests
    # that need the pipeline to proceed monkeypatch the env var itself.
    monkeypatch.setenv("NEXTEST_EXPERIMENTAL_LIBTEST_JSON", "1")
    calls: list[Any] = []

    class _FakePopen:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            calls.append((args, kwargs))
            self.stdout = None
            self.returncode = 0

        def communicate(self, timeout: Any = None) -> tuple[bytes, bytes]:
            return (b"", b"")

        def wait(self, timeout: Any = None) -> int:
            return 0

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", _FakePopen)
    rc = rust_reporter.run_pipeline()
    assert rc == 0
    assert len(calls) == 2
