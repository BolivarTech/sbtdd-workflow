#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Meta-test enforcing allow_interactive_skill=True on direct invoke_skill
callsites for skills in _SUBPROCESS_INCOMPATIBLE_SKILLS.

Per spec sec.2.6 v1.0.2 Item F. Regression-guards future contributors
adding callsites without the override.
"""

from __future__ import annotations

import ast
from pathlib import Path


_INTERACTIVE_SKILLS = frozenset({"brainstorming", "writing-plans"})
_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXCLUDED_FILES = {
    "skills/sbtdd/scripts/superpowers_dispatch.py",
}


def _walk_invoke_skill_calls(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "invoke_skill":
            yield node
        elif isinstance(node.func, ast.Name) and node.func.id == "invoke_skill":
            yield node


def _check_path(path: Path) -> list[str]:
    violations = []
    for call in _walk_invoke_skill_calls(path):
        skill_kw = next(
            (
                kw
                for kw in call.keywords
                if kw.arg == "skill"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value in _INTERACTIVE_SKILLS
            ),
            None,
        )
        if skill_kw is None:
            continue
        has_override = any(
            kw.arg == "allow_interactive_skill"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for kw in call.keywords
        )
        if not has_override:
            violations.append(
                f"{path}:{call.lineno} invokes "
                f"invoke_skill(skill='{skill_kw.value.value}') "
                f"without allow_interactive_skill=True"
            )
    return violations


def test_f1_synthetic_fixture_without_override_fails():
    """F-1: synthetic fixture lacking override is detected by AST walk."""
    fixture = _REPO_ROOT / "tests" / "fixtures" / "audit_callsites" / "without_override.py"

    violations = _check_path(fixture)

    assert len(violations) == 1
    assert "without_override.py" in violations[0]
    assert "brainstorming" in violations[0]


def test_f2_synthetic_fixture_with_override_passes():
    """F-2: synthetic fixture with override produces no violation."""
    fixture = _REPO_ROOT / "tests" / "fixtures" / "audit_callsites" / "with_override.py"

    violations = _check_path(fixture)

    assert violations == []
