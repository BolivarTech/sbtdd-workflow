# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Task G9b: A8 invariant -- Feature A never invoked from ``auto_cmd``.

Two orthogonal guarantees:

1. **Static import check** -- ``auto_cmd.py`` must not import the TTY-driven
   entry point ``prompt_user`` from ``escalation_prompt``. Importing the
   headless-safe helpers (``build_escalation_context``, ``apply_decision``)
   is permitted.
2. **Behavioral check** -- driving ``auto_cmd`` through a MAGI non-convergence
   path (Loop 2 exhaustion) must never call ``prompt_user``. The function is
   patched to raise on invocation; the run must abort via the headless policy
   / ``MAGIGateError`` path instead.

Spec refs: ``spec-behavior-base.md:282`` (A8), ``~/.claude/CLAUDE.md`` INV-22.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "skills" / "sbtdd" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _names_imported_by(module_path: Path, from_module: str) -> set[str]:
    """Return the set of names imported from ``from_module`` by the given file."""
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == from_module:
            names.update(alias.name for alias in node.names)
    return names


def test_auto_cmd_does_not_import_prompt_user() -> None:
    """A8 static guarantee: ``auto_cmd.py`` must not import any TTY-driven
    entry point from ``escalation_prompt``. Importing
    ``build_escalation_context`` / ``apply_decision`` is permitted (both are
    headless-safe); ``prompt_user`` is not."""
    imported = _names_imported_by(SCRIPTS_DIR / "auto_cmd.py", "escalation_prompt")
    assert "prompt_user" not in imported, (
        "INV-22 / A8 violation: auto_cmd imports escalation_prompt.prompt_user. "
        "auto_cmd must remain headless; use apply_decision with a headless "
        "UserDecision synthesized from .claude/magi-auto-policy.json instead."
    )


def _setup_git_repo(root: Path) -> None:
    """Init a git repo with one commit so HEAD resolves cleanly.

    Mirrors ``tests/test_auto_cmd.py::_setup_git_repo`` rather than importing
    it, keeping this A8 test self-contained.
    """
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )
    (root / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )


def _seed_plugin_local(root: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into ``root/.claude``."""
    claude = root / ".claude"
    claude.mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, claude / "plugin.local.md")


def test_auto_cmd_magi_exhaustion_never_calls_prompt_user(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A8 behavioral guarantee: drive ``auto_cmd`` through a MAGI
    non-convergence path where ``pre_merge_cmd._loop2`` raises
    :class:`MAGIGateError` (simulating exhausted-iterations from HOLD
    verdicts). ``prompt_user`` is patched to raise on invocation. The run
    must abort with ``MAGIGateError`` without ever calling ``prompt_user`` --
    the headless ``auto_cmd`` path must never delegate to the TTY prompt.
    """
    import auto_cmd
    import escalation_prompt
    import pre_merge_cmd
    from config import load_plugin_local
    from errors import MAGIGateError

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    prompt_user_calls: list[object] = []

    def _boom_prompt(*a: object, **kw: object) -> None:
        prompt_user_calls.append((a, kw))
        raise AssertionError("prompt_user invoked inside auto_cmd -- INV-22 / A8 violated")

    def _fake_loop2(root: Path, shadow_cfg: object, threshold: str | None) -> object:
        raise MAGIGateError("MAGI iterations exhausted with HOLD verdicts")

    monkeypatch.setattr(escalation_prompt, "prompt_user", _boom_prompt)
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)
    monkeypatch.setattr(pre_merge_cmd, "_loop2", _fake_loop2)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    with pytest.raises(MAGIGateError):
        auto_cmd._phase3_pre_merge(ns, cfg)

    # Explicit breadcrumb per plan Step 5 note: guard against vacuous pass.
    assert prompt_user_calls == [], (
        "prompt_user was invoked during auto_cmd MAGI exhaustion -- "
        "INV-22 violation. auto_cmd must remain headless."
    )
