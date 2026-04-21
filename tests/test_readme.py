# tests/test_readme.py
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Contract test for README.md (public GitHub README).

Validates presence of the required sections (parity with MAGI README):
shields, Why SBTDD?, Installation, Usage (subcommand table), Architecture,
Tests, License. Intentionally does NOT assert on prose content to avoid
over-coupling.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"
CONTRIBUTING_PATH = REPO_ROOT / "CONTRIBUTING.md"

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


def _read_readme() -> str:
    assert README_PATH.is_file(), f"README.md missing at {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


def test_readme_exists_and_non_empty() -> None:
    text = _read_readme()
    assert len(text) > 2000, f"README.md too short ({len(text)} chars); expected >= 2000"


def test_readme_has_title() -> None:
    text = _read_readme()
    assert re.search(r"^#\s+SBTDD", text, flags=re.MULTILINE), (
        "README must have a top-level H1 starting with 'SBTDD'"
    )


def test_readme_has_python_shield() -> None:
    text = _read_readme()
    assert "python-3.9" in text.lower() or "python 3.9" in text.lower(), (
        "README must declare Python 3.9+ via shield or prose"
    )


def test_readme_has_license_shield() -> None:
    text = _read_readme()
    assert "MIT" in text and "Apache" in text, (
        "README must reference dual MIT OR Apache-2.0 license"
    )


def test_readme_why_sbtdd_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Why SBTDD\?", text, flags=re.MULTILINE), (
        "README must have 'Why SBTDD?' section (parity with MAGI README)"
    )


def test_readme_installation_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Installation\s*$", text, flags=re.MULTILINE)


def test_readme_installation_references_marketplace_add() -> None:
    text = _read_readme()
    assert "/plugin marketplace add" in text, "README must document marketplace add command"
    assert "BolivarTech/sbtdd-workflow" in text


def test_readme_installation_references_plugin_install() -> None:
    text = _read_readme()
    assert "/plugin install sbtdd-workflow" in text


def test_readme_installation_references_local_dev_symlink() -> None:
    text = _read_readme()
    assert "claude --plugin-dir" in text or ".claude/skills" in text, (
        "README must document at least one local-dev mechanism"
    )


def test_readme_usage_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Usage\s*$", text, flags=re.MULTILINE)


def test_readme_mentions_all_nine_subcommands() -> None:
    text = _read_readme()
    for sub in NINE_SUBCOMMANDS:
        # Match as standalone token (prevents substring false positives like "status" in "statuses")
        assert re.search(rf"\b{re.escape(sub)}\b", text), f"README must mention subcommand '{sub}'"


def test_readme_end_to_end_flow() -> None:
    text = _read_readme()
    # Must describe the typical flow init -> spec -> close-phase -> pre-merge -> finalize
    assert "init" in text and "spec" in text and "pre-merge" in text and "finalize" in text


def test_readme_architecture_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+Architecture\s*$", text, flags=re.MULTILINE) or re.search(
        r"^##\s+Project Structure\s*$", text, flags=re.MULTILINE
    ), "README must have Architecture or Project Structure section"


def test_readme_tests_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+(Running )?Tests", text, flags=re.MULTILINE) or re.search(
        r"make verify", text
    ), "README must document how to run tests"


def test_readme_license_section() -> None:
    text = _read_readme()
    assert re.search(r"^##\s+License\s*$", text, flags=re.MULTILINE)


def test_readme_references_contributing() -> None:
    text = _read_readme()
    assert "CONTRIBUTING" in text or "Contributing" in text, (
        "README must reference CONTRIBUTING.md or a Contributing section"
    )


def test_readme_no_uppercase_placeholders() -> None:
    """Extends the rationale of INV-27 (which applies to `sbtdd/spec-behavior-base.md`)
    to the public README. INV-27 itself is scoped to the spec-base input of the
    `/sbtdd spec` pipeline; this test does not enforce INV-27 on the README (which
    is outside its formal scope) but prevents placeholder markers from shipping
    in the GitHub-visible surface for the same rationale: they signal unfinished
    work and erode perceived quality.
    """
    text = _read_readme()
    # Tokens are assembled at runtime so this test file itself never embeds them
    # literally. Concatenating the two halves ("TO" + "DO") keeps the source
    # clean under INV-27-like scans without needing a path-exclusion list.
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"README contains forbidden placeholder '{token}' (extends INV-27 rationale to README)"
        )


def test_contributing_file_exists() -> None:
    assert CONTRIBUTING_PATH.is_file(), f"CONTRIBUTING.md missing at {CONTRIBUTING_PATH}"


def test_contributing_has_title() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    assert re.search(r"^#\s+Contributing", text, flags=re.MULTILINE)


def test_contributing_references_commit_prefixes() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    for prefix in ("test:", "feat:", "fix:", "refactor:", "chore:"):
        assert prefix in text, f"CONTRIBUTING must mention commit prefix '{prefix}'"


def test_contributing_references_inv0() -> None:
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    assert "INV-0" in text or "~/.claude/CLAUDE.md" in text, (
        "CONTRIBUTING must reference the global authority rule"
    )


def test_contributing_no_uppercase_placeholders() -> None:
    """Extends the rationale of INV-27 to CONTRIBUTING.md. INV-27 itself is
    scoped to `sbtdd/spec-behavior-base.md`; this test applies the same
    hygiene guard to the contributor-facing documentation.
    """
    text = CONTRIBUTING_PATH.read_text(encoding="utf-8")
    # Runtime-assembled tokens keep this test file clean under INV-27-like scans
    # (concatenation avoids embedding the literal markers in the source).
    t1 = "TO" + "DO"
    t2 = t1 + "S"
    t3 = "T" + "BD"
    for token in (t1, t2, t3):
        assert not re.search(rf"\b{token}\b", text), (
            f"CONTRIBUTING contains forbidden placeholder '{token}' "
            "(extends INV-27 rationale to CONTRIBUTING.md)"
        )
