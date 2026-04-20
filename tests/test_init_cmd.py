# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd init subcomando (sec.S.5.1)."""

from __future__ import annotations

import pytest


def test_init_cmd_module_importable() -> None:
    import init_cmd

    assert hasattr(init_cmd, "main")


def test_init_parses_stack_flag() -> None:
    import init_cmd

    with pytest.raises(SystemExit) as ei:
        init_cmd.main(["--help"])
    assert ei.value.code == 0


def test_init_rejects_invalid_stack() -> None:
    import init_cmd

    with pytest.raises(SystemExit):
        init_cmd.main(["--stack", "not-a-real-stack"])
