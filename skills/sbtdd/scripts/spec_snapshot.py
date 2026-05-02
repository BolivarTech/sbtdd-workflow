#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Spec scenario snapshot + diff for v1.0.0 Feature H option 2 (sec.3.2).

:func:`emit_snapshot` parses ``sbtdd/spec-behavior.md`` sec.4 Escenarios
block, extracts scenario title + Given/When/Then text per scenario, and
hashes the whitespace-normalized content. The pre-merge gate compares
against a previously persisted snapshot (``planning/spec-snapshot.json``)
to detect spec drift between plan approval and merge.

Sec.9.1 deferred-import contract: this module imports only stdlib; it
must NOT import :mod:`auto_cmd`, :mod:`pre_merge_cmd`,
:mod:`magi_dispatch`, or :mod:`status_cmd`. The cross-subagent integration
wires the helpers via deferred imports inside the consuming functions in
those modules (Subagent #1 surfaces, plan tasks S1-26 + S1-27).

Cross-subagent contract (spec sec.5.3): the four public helpers --
:func:`emit_snapshot`, :func:`compare`, :func:`persist_snapshot`,
:func:`load_snapshot` -- are pinned by signature; consumers must not rely
on internals (regex form, hash algorithm) since both are implementation
details of the snapshot format. ``compare`` / ``persist_snapshot`` /
``load_snapshot`` ship in plan task S2-6.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

#: Header recogniser for scenario blocks. Per spec sec.3.2 H2-1 impl note,
#: tolerates three forms used across spec-behavior.md drafts:
#:
#: - ``**Escenario <title>**`` (bold inline; canonical v1.0.0 form)
#: - ``## Escenario <title>`` (double-hash heading)
#: - ``### Escenario <title>`` (triple-hash heading)
#:
#: The trailing closing ``**`` for the bold form is captured by the regex
#: in ``_extract_scenarios`` so it does not bleed into the title.
_SCENARIO_HEADER_RE = re.compile(
    r"^(?:\*\*Escenario\s+(?P<bold_title>[^\*]+?)\*\*|"
    r"#{2,3}\s+Escenario\s+(?P<heading_title>[^\n]+?))\s*$",
    re.MULTILINE,
)

#: Section locator for ``## §?4 ... Escenarios`` (with or without § marker
#: and with or without trailing label after "Escenarios"). Matches the
#: synthetic test fixtures using ``## §4 Escenarios BDD`` while remaining
#: tolerant of natural-language section labels.
#:
#: The terminator ``(?=^##\s+§?\d|\Z)`` matches the *next* numbered section
#: header (``## 5. ...`` or ``## §5 ...``) or end-of-file. It deliberately
#: does NOT terminate on a ``## Escenario X: ...`` line so the
#: double-hash scenario header form is preserved as part of the section
#: body and is recognised by :data:`_SCENARIO_HEADER_RE`.
_SECTION_RE = re.compile(
    r"^##\s*§?4[^\n]*Escenarios[^\n]*\n([\s\S]*?)(?=^##\s+§?\d|\Z)",
    re.MULTILINE,
)


def _normalize(text: str) -> str:
    """Whitespace-normalize ``text`` so trivial reformats don't change hash.

    Collapses any run of whitespace (including newlines) to a single space
    and strips leading / trailing whitespace. This means re-flowing a
    ``Given/When/Then`` line across two lines or adding extra indentation
    does NOT perturb the hash.
    """
    return re.sub(r"\s+", " ", text.strip())


def _extract_scenarios(section_text: str) -> dict[str, str]:
    """Extract ``{title: hash}`` map from a §4 Escenarios section body.

    Splits the section on scenario header lines and hashes each block's
    body (everything between this header and the next, exclusive).
    """
    matches = list(_SCENARIO_HEADER_RE.finditer(section_text))
    snapshot: dict[str, str] = {}
    for idx, match in enumerate(matches):
        title = (match.group("bold_title") or match.group("heading_title") or "").strip()
        if not title:
            continue
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
        body = section_text[body_start:body_end]
        normalized = _normalize(body)
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        snapshot[title] = digest
    return snapshot


def emit_snapshot(spec_path: Path) -> dict[str, str]:
    """Parse spec sec.4 Escenarios; return ``{scenario_title: hash}``.

    Args:
        spec_path: Path to ``sbtdd/spec-behavior.md``.

    Returns:
        Dict mapping scenario title (stripped of ``**Escenario `` / ``**``
        wrappers, or trimmed of header markers) to SHA-256 hex digest of
        the whitespace-normalized scenario body (everything from the
        header line up to the next scenario header).

    Raises:
        ValueError: When no §4 Escenarios section is found OR the section
            contains zero scenario blocks. Per WARNING melchior zero-match
            guard: silently returning ``{}`` would later compare equal to
            another empty snapshot from a similarly broken spec, masking
            real drift.
    """
    text = spec_path.read_text(encoding="utf-8")
    section_match = _SECTION_RE.search(text)
    if not section_match:
        raise ValueError(
            f"No §4 Escenarios section found in {spec_path}; "
            f"spec-snapshot drift detection requires the section header."
        )
    section_text = section_match.group(1)
    snapshot = _extract_scenarios(section_text)
    if not snapshot:
        raise ValueError(
            f"§4 Escenarios section in {spec_path} contains zero scenarios; "
            f"refusing to emit empty snapshot (would mask drift)."
        )
    return snapshot
