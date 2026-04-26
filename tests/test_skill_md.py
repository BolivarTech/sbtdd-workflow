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


def test_skill_has_fallback_section() -> None:
    text = _read_skill()
    assert re.search(r"^##\s+Fallback\s*$", text, flags=re.MULTILINE), (
        "Fallback section required (sec.S.6.3 item 7)"
    )


def test_skill_sections_in_correct_order() -> None:
    """sec.S.6.3: sections appear in the mandated order."""
    text = _read_skill()
    required_headers = [
        "## Overview",
        "## Subcommand dispatch",
        "## Complexity gate",
        "## Execution pipeline",
        "## sbtdd-rules",
        "## sbtdd-tdd-cycle",
        "## Fallback",
    ]
    positions = []
    for header in required_headers:
        idx = text.find("\n" + header + "\n")
        assert idx >= 0, f"missing header line: {header}"
        positions.append(idx)
    assert positions == sorted(positions), (
        f"section headers are out of order: {positions} vs sorted {sorted(positions)}"
    )


def test_skill_subcommand_dispatch_table_has_ten_rows() -> None:
    """Task I1b (D2/D3): dispatch table documents 10 subcommands in v0.2.

    v0.1 shipped nine subcommands (init, spec, close-phase, close-task, status,
    pre-merge, finalize, auto, resume). v0.2 Feature B adds a tenth
    (review-spec-compliance) for manual/executing-plans flows. The dispatch
    table at the top of the ``## Subcommand dispatch`` section must contain
    exactly ten data rows (v0.3+ subsections like ``### v0.3 flags`` may
    introduce additional tables further down the section -- skip past them
    by stopping at the first blank line after the dispatch table closes).
    """
    text = _read_skill()
    section = re.search(
        r"^## Subcommand dispatch\s*$(.*?)^##\s",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert section, "Subcommand dispatch section missing"
    body = section.group(1)
    # Collect only the FIRST contiguous run of data rows -- the dispatch
    # table proper. Subsequent tables (v0.3 flags model fields, etc.)
    # appear after a blank line and any narrative paragraphs in between.
    data_rows: list[str] = []
    in_table = False
    for line in body.splitlines():
        if re.match(r"^\|\s*`[^`]+`", line):
            data_rows.append(line)
            in_table = True
        elif in_table:
            # First non-data-row after the table closes the run.
            break
    assert len(data_rows) == 10, f"expected 10 dispatch rows (v0.2), found {len(data_rows)}"


def test_skill_lists_review_spec_compliance_subcommand() -> None:
    """Task I1b (D3): SKILL.md mentions the new v0.2 subcommand."""
    text = _read_skill()
    assert "review-spec-compliance" in text, (
        "SKILL.md must mention review-spec-compliance (v0.2 Feature B)"
    )


def test_skill_documents_v02_flags() -> None:
    """Task I1b (D3): SKILL.md documents the four new v0.2 flags."""
    text = _read_skill()
    for flag in ("--override-checkpoint", "--reason", "--non-interactive", "--skip-spec-review"):
        assert flag in text, f"SKILL.md must document v0.2 flag '{flag}'"


def test_skill_has_nontrivial_body() -> None:
    """Content-based non-triviality check (F7 MAGI iter 2).

    An earlier draft of this test pinned a `>= 200 lines` floor. Line count
    is an arbitrary proxy; we now assert the **content** property: every one
    of the seven sections mandated by sec.S.6.3 must be present with a
    non-empty body (at least one non-blank line after the header before the
    next header or EOF). If each section has real content, line count is a
    natural consequence (~300+ lines as shipped) and the prior floor adds
    nothing.

    This is independent of `test_skill_sections_in_correct_order` (which
    pins ORDER) and of `test_skill_has_*_section` (which pin PRESENCE of
    the header). This test pins that each section has a body.
    """
    text = _read_skill()
    required_headers = [
        "## Overview",
        "## Subcommand dispatch",
        "## Complexity gate",
        "## Execution pipeline",
        "## sbtdd-rules",
        "## sbtdd-tdd-cycle",
        "## Fallback",
    ]
    # Find each header's position; then check that the next non-blank line
    # after the header is NOT another header (which would indicate an empty
    # section).
    for header in required_headers:
        pattern = re.compile(rf"^{re.escape(header)}\s*$", flags=re.MULTILINE)
        match = pattern.search(text)
        assert match is not None, f"missing header: {header}"
        # Slice from end of header to find the next non-blank line
        body_start = match.end()
        # Look at the next ~500 chars (enough for a real section body)
        window = text[body_start : body_start + 500]
        # Strip the immediate newline after the header and any blank lines
        stripped = window.lstrip("\n \t")
        assert stripped, f"section '{header}' has no body before EOF"
        # Ensure the first non-blank line after the header is NOT another H2
        first_line = stripped.split("\n", 1)[0]
        assert not first_line.startswith("## "), (
            f"section '{header}' is empty (immediately followed by another H2: '{first_line}')"
        )


def test_v03_flags_section_documents_exit_1_for_invalid_model_override() -> None:
    """J5.1: SKILL.md v0.3 flags section uses 'exit 1' not 'exit 2'.

    The v0.3 flags section describes ``--model-override`` validation.
    Invalid skill names or model IDs are rejected by
    ``auto_cmd._parse_model_overrides`` which raises
    :class:`ValidationError`. Per ``errors.EXIT_CODES`` that maps to
    exit ``1`` (USER_ERROR), not exit ``2`` (PRECONDITION_FAILED).

    This test guards against the docs drift originally flagged by
    balthasar finding #1 in v0.3.0 final review iter 2.
    """
    skill = SKILL_PATH.read_text(encoding="utf-8")
    # Find the v0.3 flags section
    assert "### v0.3 flags" in skill, "missing '### v0.3 flags' section in SKILL.md"
    section_start = skill.index("### v0.3 flags")
    # Slice to next H2-or-H3 to bound the section
    rest = skill[section_start + len("### v0.3 flags") :]
    # Look for the next ``\n## `` or ``\n### `` boundary
    next_h2 = rest.find("\n## ")
    next_h3 = rest.find("\n### ")
    candidates = [c for c in (next_h2, next_h3) if c >= 0]
    section_end = (section_start + len("### v0.3 flags") + min(candidates)) if candidates else len(skill)
    section = skill[section_start:section_end]
    # Must say exit 1 (USER_ERROR), not exit 2 (PRECONDITION_FAILED)
    assert "exit `1` (USER_ERROR)" in section or "exit 1 (USER_ERROR)" in section, (
        "v0.3 flags section must document 'exit 1 (USER_ERROR)' for invalid "
        "--model-override values; matches auto_cmd._parse_model_overrides "
        "raising ValidationError -> errors.EXIT_CODES[ValidationError] == 1"
    )
    assert "exit `2`" not in section, (
        "v0.3 flags section must NOT claim exit 2 for invalid "
        "--model-override values; that is wrong"
    )
    assert "exit 2 (PRECONDITION_FAILED)" not in section, (
        "v0.3 flags section must NOT claim exit 2 (PRECONDITION_FAILED) "
        "for invalid --model-override values; the actual exit is 1"
    )
