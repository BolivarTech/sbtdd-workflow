#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-08
"""v1.0.4 Path 3 sub-issue 2 (Mel WARNING): AST audit asserting
``pre_merge_cmd``'s ``/receiving-code-review`` invocation goes through
``superpowers_dispatch.invoke_skill`` (or the ``receiving_code_review``
wrapper which itself delegates to ``invoke_skill``), NOT through a raw
``subprocess.Popen`` / ``subprocess.run`` to ``claude -p``.

Why this audit exists:
    The v1.0.1 ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` whitelist + the
    headless detection planned for v1.0.4 only protect the
    ``invoke_skill`` code path. If ``pre_merge_cmd`` were to bypass the
    wrapper and dispatch ``claude -p receiving-code-review`` directly via
    ``subprocess`` (which v1.0.3 dogfood empirically observed hanging
    600s), the safety net would be defeated. This AST test guards the
    contract structurally: ANY future change that calls subprocess with
    a ``receiving-code-review`` skill name is flagged before merge.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

PRE_MERGE_PATH = Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts" / "pre_merge_cmd.py"


def _collect_subprocess_calls(tree: ast.AST) -> list[ast.Call]:
    """Return every ``subprocess.Popen``/``subprocess.run`` Call node."""
    out: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # subprocess.Popen / subprocess.run
        if isinstance(func, ast.Attribute):
            if isinstance(func.value, ast.Name) and func.value.id == "subprocess":
                if func.attr in {"Popen", "run", "check_call", "check_output"}:
                    out.append(node)
        # imported as Popen / run
        elif isinstance(func, ast.Name):
            if func.id in {"Popen", "run", "check_call", "check_output"}:
                out.append(node)
    return out


def test_pre_merge_no_raw_subprocess_to_receiving_code_review() -> None:
    """``pre_merge_cmd.py`` MUST NOT contain any subprocess invocation
    whose argv string-literals reference ``receiving-code-review``.

    The legitimate path is through ``superpowers_dispatch.receiving_code_review``
    (wrapper of ``invoke_skill``), which honors the v1.0.1
    ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` whitelist and the v1.0.4 real
    headless detection. Bypassing the wrapper defeats both safety nets.
    """
    src = PRE_MERGE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    subprocess_calls = _collect_subprocess_calls(tree)

    # Render each call's argv (positional + kwargs) literal as text so we
    # can grep for skill name strings. We tolerate non-literal argv (e.g.,
    # variables) since those are a different audit problem.
    flagged: list[str] = []
    for call in subprocess_calls:
        # Convert all string-literal args + kwargs to text for grep.
        literals: list[str] = []
        for a in call.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                literals.append(a.value)
            elif isinstance(a, ast.List):
                for el in a.elts:
                    if isinstance(el, ast.Constant) and isinstance(el.value, str):
                        literals.append(el.value)
        for kw in call.keywords:
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                literals.append(kw.value.value)
        joined = " | ".join(literals)
        if "receiving-code-review" in joined:
            flagged.append(f"line {call.lineno}: argv contains 'receiving-code-review' literal")

    assert not flagged, (
        "pre_merge_cmd.py invokes subprocess with 'receiving-code-review' "
        "literal in argv -- this bypasses the invoke_skill safety net and "
        "the v1.0.4 real headless detection. Use "
        "superpowers_dispatch.receiving_code_review() instead. Findings:\n" + "\n".join(flagged)
    )


def test_pre_merge_uses_canonical_receiving_code_review_wrapper() -> None:
    """``pre_merge_cmd.py`` MUST reference the canonical wrapper
    ``superpowers_dispatch.receiving_code_review`` at least once.

    This is a positive existence check complementing the negative AST
    audit above: it ensures the wrapper IS the dispatch path actually
    used by pre_merge_cmd. Combined with the negative test, the audit
    proves the canonical path is used and no raw subprocess bypass
    exists.
    """
    src = PRE_MERGE_PATH.read_text(encoding="utf-8")
    # Look for the wrapper invocation pattern (qualified or imported).
    pattern = re.compile(
        r"superpowers_dispatch\.receiving_code_review|"
        r"\breceiving_code_review\s*\("
    )
    assert pattern.search(src), (
        "pre_merge_cmd.py must dispatch /receiving-code-review via the "
        "superpowers_dispatch.receiving_code_review wrapper (which "
        "delegates to invoke_skill). Wrapper invocation not found in "
        "module source -- mini-cycle fix routing is broken or bypassed."
    )
