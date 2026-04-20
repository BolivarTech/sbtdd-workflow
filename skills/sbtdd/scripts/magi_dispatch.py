#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dispatcher for the /magi:magi plugin (sec.S.5.6 Loop 2, Checkpoint 2).

Transport: uses subprocess ``claude -p`` to invoke sub-skills across plugin
boundaries (the only available transport from Python code). Aligned with
MAGI v2.1.3 pattern and documented in CLAUDE.md External Dependencies.

``/magi:magi`` is invoked via the claude CLI (subprocess). Its output is
expected to be a JSON document with the fields ``verdict``, ``degraded``,
``conditions``, ``findings``. This module:

- Invokes the skill via :mod:`subprocess_utils` (same timeout + Windows
  kill-tree discipline as other dispatchers, NF5).
- Applies :mod:`quota_detector` to stderr before reporting generic failures
  (sec.S.11.4).
- Parses the JSON output and validates ``verdict`` against
  :data:`models.VERDICT_RANK`. Labels with spaces are normalised to
  underscores (``"GO WITH CAVEATS"`` -> ``"GO_WITH_CAVEATS"``) since the
  magi plugin emits the human-readable form. Normalisation is strict: only
  whitespace-to-underscore conversion + uppercasing on an already-uppercase
  token. Lowercase / mixed-case / trailing-junk inputs are rejected with
  :class:`ValidationError` (see ``_normalise_verdict_label`` for the exact
  contract).
- Exposes :class:`MAGIVerdict` as the typed output for Loop 2 consumers
  (``pre_merge_cmd``, ``auto_cmd``) that will be built in Milestone C+.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

import quota_detector
import subprocess_utils
from errors import MAGIGateError, QuotaExhaustedError, ValidationError
from models import VERDICT_RANK, verdict_meets_threshold


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


def _build_magi_cmd(context_paths: list[str]) -> list[str]:
    """Build the argv list for ``claude -p /magi:magi`` with @file refs."""
    cmd = ["claude", "-p", "/magi:magi"]
    for path in context_paths:
        cmd.append(f"@{path}")
    return cmd


def invoke_magi(
    context_paths: list[str],
    timeout: int = 1800,
    cwd: str | None = None,
) -> MAGIVerdict:
    """Invoke /magi:magi and return a parsed MAGIVerdict.

    Args:
        context_paths: Files passed to MAGI as ``@file`` references
            (spec-behavior.md, planning/claude-plan-tdd.md, or the diff).
        timeout: Wall-clock seconds before SIGTERM. Default 1800 (30 min)
            because MAGI runs 3 sub-agents sequentially and may need longer
            than superpowers skills.
        cwd: Working directory.

    Returns:
        :class:`MAGIVerdict` parsed from subprocess stdout.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        MAGIGateError: If the subprocess timed out, OR exited non-zero
            without matching a quota pattern. Mapped to exit 8
            (MAGI_GATE_BLOCKED) by run_sbtdd.py.
        ValidationError: If stdout was not valid MAGI JSON / unknown verdict
            (raised by :func:`parse_verdict`, mapped to exit 1).
    """
    cmd = _build_magi_cmd(context_paths)
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
    return parse_verdict(result.stdout)


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
