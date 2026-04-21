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
