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


_INTERACTIVE_SKILLS = frozenset({"brainstorming", "writing-plans", "receiving-code-review"})
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


def _innermost_function_name_at_line(tree: ast.Module, target_line: int) -> str | None:
    """Return the innermost ``FunctionDef`` / ``AsyncFunctionDef`` name whose
    body span contains ``target_line``.

    v1.0.4 Path 3 sub-issue 3 (Cas WARNING): used by the
    ``allow_interactive_skill=True`` whitelist audit to identify the
    enclosing function for a call site, enabling function-level rather
    than file-level whitelisting.

    Args:
        tree: Parsed module AST.
        target_line: 1-indexed line number of the call site.

    Returns:
        Innermost function name (deepest nesting wins by smallest span),
        or ``None`` for module-level calls.
    """
    candidates: list[tuple[int, str]] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        fn_start = fn.lineno
        fn_end = getattr(fn, "end_lineno", fn_start) or fn_start
        if fn_start <= target_line <= fn_end:
            candidates.append((fn_end - fn_start, fn.name))
    if not candidates:
        return None
    # Innermost = smallest span.
    candidates.sort()
    return candidates[0][1]


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


def test_f3_wrapper_files_excluded_from_audit():
    """F-3: superpowers_dispatch.py is in _EXCLUDED_FILES."""
    assert "skills/sbtdd/scripts/superpowers_dispatch.py" in _EXCLUDED_FILES


def test_f4_unknown_skill_passes_through(tmp_path):
    """F-4: unknown skill name is not in interactive set ⇒ no violation."""
    fixture = tmp_path / "unknown.py"
    fixture.write_text(
        "def f():\n"
        '    invoke_skill(skill="custom-skill", args=["x"])\n'
        "def invoke_skill(**kw): return None\n",
        encoding="utf-8",
    )

    violations = _check_path(fixture)

    assert violations == []


def test_audit_set_tracks_subprocess_incompatible_skills():
    """v1.0.4 Loop 1 mini-cycle (IMPORTANT-2 finding): the audit set MUST
    superset the production ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` frozenset.

    Rationale: ``_check_path`` only flags missing-override callsites for
    skills in ``_INTERACTIVE_SKILLS``. If a new skill is added to the
    production set without updating the audit set, ``invoke_skill(
    skill='<new-skill>', ...)`` callsites without ``allow_interactive_skill=
    True`` slip past the regression guard. Meta-test catches the desync
    directly, future-proofing against any v1.x.y extension.
    """
    from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

    missing = _SUBPROCESS_INCOMPATIBLE_SKILLS - _INTERACTIVE_SKILLS
    assert not missing, (
        f"Audit set out of sync with production: {sorted(missing)} "
        f"present in _SUBPROCESS_INCOMPATIBLE_SKILLS but missing from "
        f"_INTERACTIVE_SKILLS. Update line 18 of "
        f"test_invoke_skill_callsites_audit.py."
    )


def test_production_callsites_pass_audit():
    """Full repo audit: all interactive-skill callsites in scripts/ + tests/
    pass override check (excluding wrappers + without_override fixture)."""
    audited_dirs = (
        _REPO_ROOT / "skills" / "sbtdd" / "scripts",
        _REPO_ROOT / "tests",
    )
    all_violations: list[str] = []
    for d in audited_dirs:
        for path in d.rglob("*.py"):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            if rel in _EXCLUDED_FILES:
                continue
            if "without_override.py" in path.name:
                continue
            all_violations.extend(_check_path(path))

    assert not all_violations, (
        "Interactive-skill callsites missing override:\n"
        + "\n".join(all_violations)
        + "\n\nFix: add allow_interactive_skill=True or use wrapper."
    )


# ---------------------------------------------------------------------------
# v1.0.4 Item A.5 (Task 5) -- audit no callsite bypasses headless gate
# inappropriately via ``allow_interactive_skill=True`` outside known-safe
# locations.
#
# Complementary to the "missing override" audit above (which catches
# UNDER-application). This new audit catches OVER-application: callsites
# that pass ``allow_interactive_skill=True`` without belonging to a
# whitelisted location are a regression and must be removed or
# whitelisted with rationale comment.
# ---------------------------------------------------------------------------


class TestHeadlessGateCallsiteConsistency:
    """v1.0.4 Item A.5 -- audit no callsite bypasses headless gate inappropriately."""

    def test_no_invoke_skill_call_with_allow_interactive_skill_true_outside_known_safe(self):
        """Audit: ``allow_interactive_skill=True`` only at known-safe callsites.

        Known-safe callsites (v1.0.4 baseline):
        - ``skills/sbtdd/scripts/superpowers_dispatch.py``: ``brainstorming``,
          ``writing_plans``, ``receiving_code_review``, and other wrappers
          built via ``_make_wrapper`` pass the override internally per the
          v1.0.1 Pre-A2 migration baseline.
        - ``tests/*``: every test file is allowed (pytest fixture context;
          monkeypatched stubs may need to drive the subprocess code path).

        Any new ``invoke_skill(..., allow_interactive_skill=True)`` callsite
        in ``skills/sbtdd/scripts/`` outside these locations is a regression
        and must be removed or whitelisted with explicit rationale comment.
        """
        skills_dir = _REPO_ROOT / "skills" / "sbtdd" / "scripts"

        # v1.0.4 Path 3 sub-issue 3 (Cas WARNING): function-level whitelist.
        # Pre-fix the whitelist was file-level (any function in
        # superpowers_dispatch.py could pass allow_interactive_skill=True
        # without triggering the audit). Post-fix only the explicitly
        # listed (file, function-or-closure) pairs are exempt; any new
        # function that needs the override must extend this map AND
        # document rationale alongside.
        WHITELIST_FUNCTIONS = {
            ("superpowers_dispatch.py", "_wrapper"): (
                "Closure inside _make_wrapper -- per-skill wrappers "
                "(brainstorming/writing_plans/receiving_code_review) "
                "pass override internally per v1.0.1 Pre-A2 migration "
                "baseline + v1.0.4 Item A.2 gate"
            ),
            ("superpowers_dispatch.py", "_invoke_skill"): (
                "Internal helper that wraps invoke_skill for callers "
                "passing kwargs dict; preserves override propagation "
                "from wrapper functions per v1.0.1 Pre-A2"
            ),
        }

        offenders: list[tuple[str, int, str]] = []
        for py_file in skills_dir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match invoke_skill(...) or *_dispatch.invoke_skill(...).
                func = node.func
                func_name: str | None = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name != "invoke_skill":
                    continue
                # Look for ``allow_interactive_skill=True`` keyword.
                for kw in node.keywords:
                    if kw.arg == "allow_interactive_skill":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            file_basename = py_file.name
                            # Find enclosing function via in-file scan
                            # (stdlib ast lacks parent links).
                            enclosing = _innermost_function_name_at_line(tree, node.lineno)
                            key = (file_basename, enclosing or "<module>")
                            if key not in WHITELIST_FUNCTIONS:
                                offenders.append(
                                    (
                                        py_file.relative_to(_REPO_ROOT).as_posix(),
                                        node.lineno,
                                        f"allow_interactive_skill=True in "
                                        f"function '{enclosing or '<module>'}'",
                                    )
                                )

        assert not offenders, (
            "Found unwhitelisted callsites passing allow_interactive_skill=True:\n"
            + "\n".join(f"  {path}:{lineno} ({reason})" for path, lineno, reason in offenders)
            + "\nAdd (file, function) to WHITELIST_FUNCTIONS with rationale or remove the override."
        )

    def test_subprocess_dispatch_module_imports_ast_safe(self):
        """Defensive: AST audit can parse superpowers_dispatch.py without error."""
        path = _REPO_ROOT / "skills" / "sbtdd" / "scripts" / "superpowers_dispatch.py"
        # Must parse without SyntaxError.
        ast.parse(path.read_text(encoding="utf-8"))
