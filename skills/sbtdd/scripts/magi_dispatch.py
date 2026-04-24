#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dispatcher for the /magi:magi plugin (sec.S.5.6 Loop 2, Checkpoint 2).

Transport: uses subprocess ``claude -p`` to invoke sub-skills across plugin
boundaries (the only available transport from Python code). Aligned with
MAGI v2.1.4 pattern and documented in CLAUDE.md External Dependencies.

MAGI output contract (as of v2.1.4):

- **stdout** = ASCII banner + markdown report (``format_report`` in
  ``skills/magi/scripts/reporting.py``). *Not* machine-readable JSON.
- **``<output-dir>/magi-report.json``** = canonical JSON written by
  ``run_magi.main`` (``run_magi.py:536``). Structure::

      {
        "agents": [...],
        "consensus": {
          "consensus": "<label>",              # e.g. "GO (2-1)"
          "consensus_verdict": "approve|...",
          "conditions": [{"agent": ..., "condition": ...}, ...],
          "findings": [{...}, ...],
          ...
        },
        "degraded": bool,                      # present only if < 3 agents
        "failed_agents": [...]                 # present only if < 3 agents
      }

This module therefore:

- Creates a temp dir, passes ``--output-dir <tmpdir>`` to the slash command,
  and reads ``magi-report.json`` from disk after the subprocess exits.
- Never attempts to parse stdout as JSON (the canonical ASCII banner would
  always fail :func:`json.loads`).
- Applies :mod:`quota_detector` to stderr before reporting generic failures
  (sec.S.11.4).
- Maps MAGI's banner label (``"GO (2-1)"``, ``"HOLD -- TIE"``,
  ``"STRONG NO-GO"``, ...) to the sbtdd :data:`models.VERDICT_RANK` enum by
  stripping the ``(N-M)`` split suffix and normalising whitespace/hyphens
  (see :func:`_normalise_verdict_label` for the exact contract).
- Exposes :class:`MAGIVerdict` as the typed output for Loop 2 consumers
  (``pre_merge_cmd``, ``auto_cmd``).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import quota_detector
import subprocess_utils
from errors import MAGIGateError, QuotaExhaustedError, ValidationError
from models import VERDICT_RANK, verdict_meets_threshold

# ISO 8601 strict with timezone -- MUST match the regex in state_file.py to
# keep the timestamp contract uniform across artifacts (MAGI Loop 2 Milestone
# B iter 1 Finding 2, melchior). Timezone suffix (Z | +HH:MM | -HH:MM) is
# mandatory; naive datetimes are rejected.
_ISO_8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")

# MAGI banner labels carry an optional ``(N-M)`` split suffix that encodes
# majority-minority agent counts (e.g. ``"GO (2-1)"``). The split carries no
# VERDICT_RANK information -- only the prefix maps to the enum -- so we strip
# it before normalisation. See ``skills/magi/scripts/consensus.py`` docstrings.
_MAGI_SPLIT_SUFFIX_RE = re.compile(r"\s*\(\d+-\d+\)\s*$")


def _resolve_timestamp(timestamp: str | None) -> str:
    """Return a validated ISO 8601 timestamp for artifact persistence.

    Centralised so ``write_verdict_artifact`` stays readable and future
    artifact writers (eg. ``auto-run.json``) can reuse the same contract
    instead of re-implementing the None-default + validation logic.

    Args:
        timestamp: Caller-supplied ISO 8601 string, or ``None`` to stamp
            the current UTC instant.

    Returns:
        The canonical ISO 8601 string that will be persisted.

    Raises:
        ValidationError: If ``timestamp`` is a non-None value that is not
            a well-formed ISO 8601 string with timezone suffix.
    """
    if timestamp is None:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if not isinstance(timestamp, str) or not _ISO_8601_RE.match(timestamp):
        raise ValidationError(
            f"timestamp must be ISO 8601 with timezone (Z or +/-HH:MM), got {timestamp!r}"
        )
    return timestamp


@dataclass(frozen=True)
class MAGIVerdict:
    """Parsed result of a /magi:magi invocation (sec.S.5.6)."""

    verdict: str  # key of VERDICT_RANK
    degraded: bool
    conditions: tuple[str, ...]
    findings: tuple[dict[str, Any], ...]
    raw_output: str


def _normalise_verdict_label(raw: str) -> str:
    """Convert the human-readable ``'GO WITH CAVEATS'`` form to enum form.

    Strict contract (MAGI Checkpoint 2 iter 1 WARNING -- caspar):

    - Leading/trailing whitespace is stripped.
    - Internal whitespace runs are collapsed to a single underscore.
    - Hyphens are converted to underscores (``STRONG-NO-GO`` -> ``STRONG_NO_GO``).
    - Input MUST already be uppercase after stripping. Lowercase or mixed
      case triggers :class:`ValidationError` from the caller (``parse_verdict``
      only accepts the strict form because MAGI's contract guarantees uppercase
      emission; accepting casual variants would hide upstream bugs).
    - Internal characters outside ``[A-Z0-9_\\s-]`` are rejected.

    Args:
        raw: The ``verdict`` string from MAGI JSON output.

    Returns:
        The normalised label (may or may not be a valid
        :data:`models.VERDICT_RANK` key -- the caller validates membership).

    Raises:
        ValidationError: If the input contains lowercase letters, mixed case,
            or characters outside the strict set. ``parse_verdict`` wraps this
            into a caller-visible error.
    """
    stripped = raw.strip()
    if not stripped:
        raise ValidationError("MAGI verdict label is empty")
    # Character class: uppercase letters, digits, whitespace, underscore,
    # hyphen. No lowercase, no punctuation.
    if not re.fullmatch(r"[A-Z0-9_\s-]+", stripped):
        raise ValidationError(
            f"MAGI verdict label '{raw}' contains invalid characters "
            f"(expected [A-Z0-9_ -] only; lowercase/mixed-case not accepted)"
        )
    # Collapse runs of whitespace to single underscore; convert hyphens.
    normalised = re.sub(r"\s+", "_", stripped).replace("-", "_")
    # Collapse runs of underscores (defensive; shouldn't happen given inputs).
    normalised = re.sub(r"_+", "_", normalised)
    return normalised


def parse_verdict(raw_output: str) -> MAGIVerdict:
    """Parse the JSON output of /magi:magi into a typed verdict.

    Args:
        raw_output: stdout captured from the magi subprocess.

    Returns:
        MAGIVerdict with validated label.

    Raises:
        ValidationError: If the output is not JSON, misses ``verdict``, or
            carries an unknown label. The magi plugin contract guarantees
            one of six labels (sec.S.2.3 cross-file contract); other values
            indicate an upstream change the plugin must be updated for.
    """
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"MAGI output is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"MAGI output must be a JSON object, got {type(payload).__name__}")
    if "verdict" not in payload:
        raise ValidationError("MAGI output missing required 'verdict' field")
    label = _normalise_verdict_label(str(payload["verdict"]))
    if label not in VERDICT_RANK:
        raise ValidationError(
            f"unknown MAGI verdict '{payload['verdict']}' (normalised '{label}'); "
            f"expected one of {sorted(VERDICT_RANK)}"
        )
    degraded = bool(payload.get("degraded", False))
    raw_conditions = payload.get("conditions", [])
    if raw_conditions is None:
        raw_conditions = []
    if not isinstance(raw_conditions, list):
        raise ValidationError(
            f"MAGI 'conditions' must be a list, got {type(raw_conditions).__name__}"
        )
    conditions = tuple(str(c) for c in raw_conditions)
    raw_findings = payload.get("findings", [])
    if raw_findings is None:
        raw_findings = []
    if not isinstance(raw_findings, list):
        raise ValidationError(f"MAGI 'findings' must be a list, got {type(raw_findings).__name__}")
    findings: tuple[dict[str, Any], ...] = tuple(
        dict(f) if isinstance(f, dict) else {"message": str(f)} for f in raw_findings
    )
    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output=raw_output,
    )


def _strip_magi_split_suffix(label: str) -> str:
    """Remove the ``(N-M)`` split suffix from a MAGI banner label.

    ``"GO (2-1)"`` -> ``"GO"``; ``"GO WITH CAVEATS (3-0)"`` ->
    ``"GO WITH CAVEATS"``. Labels without the suffix (``"STRONG NO-GO"``,
    ``"HOLD -- TIE"``, ``"STRONG GO"``) pass through unchanged.
    """
    return _MAGI_SPLIT_SUFFIX_RE.sub("", label).strip()


def parse_magi_report(report: dict[str, Any], raw_output: str = "") -> MAGIVerdict:
    """Parse MAGI's canonical ``magi-report.json`` structure into a MAGIVerdict.

    The report layout is fixed by ``skills/magi/scripts/run_magi.py:536``
    (top-level ``agents``, ``consensus``; optional ``degraded`` +
    ``failed_agents``). The banner label lives at ``consensus.consensus``
    and may carry a ``(N-M)`` split suffix -- stripped here since the
    suffix is not part of the VERDICT_RANK enum.

    Args:
        report: Parsed JSON dict loaded from ``magi-report.json``.
        raw_output: Optional ASCII banner + report from MAGI stdout, stored
            on the returned :class:`MAGIVerdict` for downstream diagnostics.
            Defaults to ``json.dumps(report)`` when empty.

    Returns:
        :class:`MAGIVerdict` with normalised VERDICT_RANK label, degraded
        flag, and condition/finding tuples.

    Raises:
        ValidationError: If the report is not a dict, is missing
            ``consensus.consensus``, carries an unknown label after
            normalisation, or has malformed ``conditions`` / ``findings``
            lists. The MAGI contract guarantees one of six VERDICT_RANK
            labels; any other value indicates an upstream change the
            plugin must be updated for.
    """
    if not isinstance(report, dict):
        raise ValidationError(f"MAGI report must be a JSON object, got {type(report).__name__}")
    consensus = report.get("consensus")
    if not isinstance(consensus, dict):
        raise ValidationError("MAGI report missing required 'consensus' object")
    label_raw = consensus.get("consensus")
    if not isinstance(label_raw, str) or not label_raw.strip():
        raise ValidationError("MAGI report 'consensus.consensus' missing or not a string")
    label_stripped = _strip_magi_split_suffix(label_raw)
    label = _normalise_verdict_label(label_stripped)
    if label not in VERDICT_RANK:
        raise ValidationError(
            f"unknown MAGI verdict '{label_raw}' (normalised '{label}'); "
            f"expected one of {sorted(VERDICT_RANK)}"
        )
    degraded = bool(report.get("degraded", False))
    raw_conditions = consensus.get("conditions") or []
    if not isinstance(raw_conditions, list):
        raise ValidationError(
            f"MAGI 'consensus.conditions' must be a list, got {type(raw_conditions).__name__}"
        )
    conditions_extracted: list[str] = []
    for entry in raw_conditions:
        if isinstance(entry, dict):
            conditions_extracted.append(str(entry.get("condition", "")))
        else:
            conditions_extracted.append(str(entry))
    conditions = tuple(conditions_extracted)
    raw_findings = consensus.get("findings") or []
    if not isinstance(raw_findings, list):
        raise ValidationError(
            f"MAGI 'consensus.findings' must be a list, got {type(raw_findings).__name__}"
        )
    findings: tuple[dict[str, Any], ...] = tuple(
        dict(f) if isinstance(f, dict) else {"message": str(f)} for f in raw_findings
    )
    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output=raw_output or json.dumps(report),
    )


def _build_magi_cmd(context_paths: list[str], output_dir: str | None = None) -> list[str]:
    """Build the argv list for ``claude -p /magi:magi`` with @file refs.

    The slash command and its flags MUST be packed into the single prompt
    string passed to ``claude -p``. ``claude`` itself does NOT accept
    ``--output-dir`` -- that flag belongs to MAGI's ``run_magi.py`` and has
    to travel through the prompt so the sub-session forwards it.
    """
    prompt_parts = ["/magi:magi"]
    for path in context_paths:
        prompt_parts.append(f"@{path}")
    if output_dir is not None:
        prompt_parts.extend(["--output-dir", output_dir])
    return ["claude", "-p", " ".join(prompt_parts)]


def invoke_magi(
    context_paths: list[str],
    timeout: int = 1800,
    cwd: str | None = None,
) -> MAGIVerdict:
    """Invoke /magi:magi and return a parsed MAGIVerdict.

    MAGI writes its canonical report to ``<output-dir>/magi-report.json``
    (``run_magi.py:536``). We create a :class:`tempfile.TemporaryDirectory`,
    pass its path via ``--output-dir``, and read the JSON from disk after
    the subprocess exits. The ASCII banner on stdout is preserved on the
    returned :class:`MAGIVerdict.raw_output` for diagnostics but is never
    parsed as JSON.

    Args:
        context_paths: Files passed to MAGI as ``@file`` references
            (spec-behavior.md, planning/claude-plan-tdd.md, or the diff).
        timeout: Wall-clock seconds before SIGTERM. Default 1800 (30 min)
            because MAGI runs 3 sub-agents sequentially and may need longer
            than superpowers skills.
        cwd: Working directory.

    Returns:
        :class:`MAGIVerdict` parsed from ``magi-report.json``.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        MAGIGateError: If the subprocess timed out, exited non-zero without
            matching a quota pattern, or returned 0 but did not write the
            expected ``magi-report.json``. Mapped to exit 8
            (MAGI_GATE_BLOCKED) by run_sbtdd.py.
        ValidationError: If the report JSON is malformed or carries an
            unknown verdict label (raised by :func:`parse_magi_report`,
            mapped to exit 1).
    """
    with tempfile.TemporaryDirectory(prefix="sbtdd-magi-") as tmpdir:
        cmd = _build_magi_cmd(context_paths, output_dir=tmpdir)
        try:
            result = subprocess_utils.run_with_timeout(cmd, timeout=timeout, capture=True, cwd=cwd)
        except subprocess.TimeoutExpired as exc:
            raise MAGIGateError(f"/magi:magi timed out after {exc.timeout}s") from exc

        if result.returncode != 0:
            exhaustion = quota_detector.detect(result.stderr)
            if exhaustion is not None:
                msg = f"{exhaustion.kind}: {exhaustion.raw_message}"
                if exhaustion.reset_time:
                    msg += f" (reset: {exhaustion.reset_time})"
                raise QuotaExhaustedError(msg)
            raise MAGIGateError(
                f"/magi:magi failed (returncode={result.returncode}): {result.stderr.strip()}"
            )

        report_path = Path(tmpdir) / "magi-report.json"
        if not report_path.exists():
            raise MAGIGateError(
                f"/magi:magi returned 0 but did not write 'magi-report.json' to "
                f"{tmpdir} (stderr={result.stderr.strip()!r})"
            )
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"MAGI report JSON is malformed: {exc}") from exc
        return parse_magi_report(report, raw_output=result.stdout)


def verdict_is_strong_no_go(verdict: MAGIVerdict) -> bool:
    """Return True for STRONG_NO_GO (full or degraded) -- INV-28 exception.

    Loop 2 short-circuits on STRONG_NO_GO regardless of degraded flag because
    2 agents voting NO_GO is already decisive evidence (sec.S.5.6.b).
    """
    return verdict.verdict == "STRONG_NO_GO"


def verdict_passes_gate(verdict: MAGIVerdict, threshold: str) -> bool:
    """Evaluate whether ``verdict`` clears the Loop 2 gate (INV-28 applied).

    A verdict passes only when BOTH conditions hold:

    1. ``verdict.verdict`` is ``>= threshold`` in :data:`models.VERDICT_RANK`.
    2. ``verdict.degraded`` is ``False`` (INV-28: degraded verdicts never
       count as gate-pass, regardless of label).

    Args:
        verdict: Parsed MAGI output.
        threshold: Minimum label from ``plugin.local.md`` (``magi_threshold``).

    Returns:
        True iff the verdict should terminate Loop 2 with success.

    Raises:
        ValidationError: If ``threshold`` is not in
            :data:`models.VERDICT_RANK`. (MAGI Checkpoint 2 iter 1 WARNING --
            melchior: the wrapper converts the underlying ``KeyError`` from
            :func:`models.verdict_meets_threshold` into the project-canonical
            ``ValidationError`` so callers see a single typed error.)
    """
    if threshold not in VERDICT_RANK:
        raise ValidationError(
            f"unknown MAGI threshold '{threshold}'; expected one of {sorted(VERDICT_RANK)}"
        )
    if verdict.degraded:
        return False
    return verdict_meets_threshold(verdict.verdict, threshold)


def write_verdict_artifact(
    verdict: MAGIVerdict,
    target: Path,
    timestamp: str | None = None,
) -> None:
    """Write ``.claude/magi-verdict.json`` atomically (sec.S.5.6 postcondicion).

    The file is consumed by ``finalize`` (sec.M.7) to reject degraded
    verdicts as gate-blocking. Field layout matches the spec contract:
    ``timestamp``, ``verdict``, ``degraded``, ``conditions``, ``findings``.

    Args:
        verdict: Parsed MAGI verdict.
        target: Destination file path. Parent directories are created.
        timestamp: ISO 8601 string with timezone suffix (``Z`` or
            ``+HH:MM`` / ``-HH:MM``). When ``None`` (default) the current
            UTC instant is stamped in the project's canonical form
            (``datetime.now(timezone.utc).isoformat()`` with ``+00:00``
            rewritten to ``Z``). Same contract as
            ``state_file._validate_iso8601`` -- naive strings are rejected.

    Raises:
        ValidationError: If ``timestamp`` is a non-None value that does not
            match the ISO 8601 with-timezone contract (MAGI Loop 2
            Milestone B iter 1 Finding 2). No partial file is left on
            disk.
        OSError: If the atomic replace fails. No partial file, no
            ``*.tmp.<pid>`` leak.
    """
    stamp = _resolve_timestamp(timestamp)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": stamp,
        "verdict": verdict.verdict,
        "degraded": verdict.degraded,
        "conditions": list(verdict.conditions),
        "findings": [dict(f) for f in verdict.findings],
    }
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
