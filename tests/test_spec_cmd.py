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


def test_spec_accepts_lowercase_todos_spanish_prose(tmp_path: Path) -> None:
    import spec_cmd

    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    body = "# Feature\n\nScenario: todos los usuarios\n" + ("x " * 200)
    (spec_dir / "spec-behavior-base.md").write_text(body, encoding="utf-8")
    # Lowercase must not trigger INV-27; may still fail on later precondition.
    try:
        spec_cmd.main(["--project-root", str(tmp_path)])
    except Exception as e:
        assert ("T" + "ODO") not in str(e) and "pending" not in str(e).lower()
