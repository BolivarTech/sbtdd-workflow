# tests/test_skill_md.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for skills/sbtdd/SKILL.md.

Validates the orchestrator skill file is present, has valid YAML frontmatter,
declares the nine subcommands, documents the Python invocation pattern, and
follows the seven-section structure mandated by sec.S.6.3 of the contract.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"

NINE_SUBCOMMANDS = (
    "init",
    "spec",
    "close-phase",
    "close-task",
    "status",
    "pre-merge",
    "finalize",
    "auto",
    "resume",
)


def _read_skill() -> str:
    assert SKILL_PATH.is_file(), f"SKILL.md missing at {SKILL_PATH}"
    return SKILL_PATH.read_text(encoding="utf-8")


def test_skill_file_is_readable_and_non_empty() -> None:
    """Replaces the tautological `assert SKILL_PATH.exists()`.

    Verifies the file is present AND has enough bytes to be a real skill
    file (not an empty placeholder) AND is valid UTF-8. The trivial
    existence check is already covered implicitly by every other test
    via `_read_skill()`; this test adds the non-trivial property
    `len(text) > 100`.
    """
    assert SKILL_PATH.is_file(), f"SKILL.md missing at {SKILL_PATH}"
    text = SKILL_PATH.read_text(encoding="utf-8")
    assert len(text) > 100, f"SKILL.md too short to be a real skill file ({len(text)} bytes)"


def test_skill_has_yaml_frontmatter() -> None:
    text = _read_skill()
    assert text.startswith("---\n"), "SKILL.md must start with YAML frontmatter"
    # Frontmatter terminator on its own line
    assert re.search(r"^---\s*$", text, flags=re.MULTILINE), "frontmatter must close with ---"


def test_skill_frontmatter_declares_name_sbtdd() -> None:
    text = _read_skill()
    assert re.search(r"^name:\s*sbtdd\s*$", text, flags=re.MULTILINE), (
        "frontmatter must declare name: sbtdd"
    )


def test_skill_frontmatter_has_description_block() -> None:
    text = _read_skill()
    # Description is a scalar block (">" YAML multi-line folded or literal)
    assert re.search(r"^description:\s*>", text, flags=re.MULTILINE) or re.search(
        r"^description:\s*\|", text, flags=re.MULTILINE
    ), "frontmatter must declare description (folded or literal block)"


def test_skill_has_main_title() -> None:
    text = _read_skill()
    assert re.search(r"^#\s+SBTDD", text, flags=re.MULTILINE), (
        "SKILL.md must have a top-level H1 starting with 'SBTDD'"
    )


def test_skill_has_overview_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Overview\s*$", text, flags=re.MULTILINE), (
        "Overview section required (sec.S.6.3 item 1)"
    )


def test_skill_has_subcommand_dispatch_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Subcommand dispatch\s*$", text, flags=re.MULTILINE), (
        "Subcommand dispatch section required (sec.S.6.3 item 2)"
    )


def test_skill_mentions_all_nine_subcommands() -> None:
    text = _read_skill()
    for sub in NINE_SUBCOMMANDS:
        assert sub in text, f"SKILL.md must reference subcommand '{sub}'"


def test_skill_has_complexity_gate_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Complexity gate\s*$", text, flags=re.MULTILINE), (
        "Complexity gate section required (sec.S.6.3 item 3)"
    )


def test_skill_has_no_skeleton_sentinel() -> None:
    """F8 MAGI iter 2: reject SKILL.md shipping with the Task 1b skeleton sentinel.

    Task 1b creates SKILL.md with an explicit `<!-- SKELETON: ... -->` comment
    that flags the body as pending. Task 2 removes that comment as it populates
    the first three sections. This test is introduced in Task 2 (alongside the
    removal itself) so that the no-sentinel property is verified at the exact
    moment the sentinel is deleted, eliminating the window between sentinel
    removal and guard arming that would exist if this test were deferred to
    Task 4 (Caspar iter 3 fix).

    We match on the stable prefix of the comment (`<!-- SKELETON:` with the
    literal text used in Task 1b) rather than an exact full-text match so that
    a minor edit to the sentinel body in Task 1b does not require a matching
    edit here.
    """
    text = _read_skill()
    assert "<!-- SKELETON:" not in text, (
        "SKILL.md still contains the Task 1b skeleton sentinel; "
        "Task 2 must remove it while populating the first three sections"
    )


def test_skill_has_execution_pipeline_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Execution pipeline\s*$", text, flags=re.MULTILINE), (
        "Execution pipeline section required (sec.S.6.3 item 4)"
    )


def test_skill_documents_python_invocation_pattern() -> None:
    text = _read_skill()
    # The canonical invocation line from sec.S.6.3 item 4
    assert re.search(
        r"\$\{CLAUDE_PLUGIN_ROOT\}/skills/sbtdd/scripts/run_sbtdd\.py",
        text,
    ), "SKILL.md must document the ${CLAUDE_PLUGIN_ROOT}/.../run_sbtdd.py pattern"


def test_skill_has_sbtdd_rules_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+sbtdd-rules\s*$", text, flags=re.MULTILINE), (
        "sbtdd-rules section required (sec.S.6.3 item 5)"
    )


def test_skill_has_sbtdd_tdd_cycle_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+sbtdd-tdd-cycle\s*$", text, flags=re.MULTILINE), (
        "sbtdd-tdd-cycle section required (sec.S.6.3 item 6)"
    )


def test_skill_rules_reference_commit_prefix_map() -> None:
    text = _read_skill()
    # All five sec.M.5 prefixes must appear, confirming the rules section is non-trivial
    for prefix in ("test:", "feat:", "fix:", "refactor:", "chore:"):
        assert prefix in text, f"SKILL.md must reference commit prefix '{prefix}'"


def test_skill_mentions_invariants() -> None:
    text = _read_skill()
    # At minimum reference the critical invariants mentioned throughout the plugin
    for inv in ("INV-0", "INV-27", "INV-28", "INV-29"):
        assert inv in text, f"SKILL.md must reference invariant '{inv}'"
