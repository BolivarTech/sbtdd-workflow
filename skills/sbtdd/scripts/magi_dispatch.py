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
import sys
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
    """Parsed result of a /magi:magi invocation (sec.S.5.6).

    v0.4.0 Feature F (F44) extends the dataclass with ``retried_agents``,
    a tuple of agent names that the MAGI 2.2.1+ orchestrator had to retry
    (transient infra failure, timeout, etc.). Defaults to ``()`` so MAGI
    2.1.x markers and tests written against the v0.3.x shape continue to
    construct verdicts unchanged.
    """

    verdict: str  # key of VERDICT_RANK
    degraded: bool
    conditions: tuple[str, ...]
    findings: tuple[dict[str, Any], ...]
    raw_output: str
    # v0.4.0 Feature F (F44): MAGI 2.2.1+ retried_agents telemetry.
    # Parser tolerates absence; defaults to empty tuple for backward
    # compat with MAGI 2.1.x markers.
    retried_agents: tuple[str, ...] = ()

    @classmethod
    def from_marker(cls, marker_path: Path | str) -> MAGIVerdict:
        """Parse a MAGI verdict marker JSON file into a MAGIVerdict.

        v0.4.0 Feature F (F44): consumes the
        ``MAGI_VERDICT_MARKER.json`` files emitted by MAGI 2.2.1+ (and
        legacy MAGI 2.1.x markers when present). The marker carries the
        same logical fields as ``magi-report.json`` -- verdict label,
        degraded flag, conditions, findings -- plus the optional
        ``retried_agents`` telemetry list.

        The implementation delegates to :func:`parse_magi_report` to
        preserve every sec.S.10 invariant around verdict-label
        validation, then re-constructs the dataclass with
        ``retried_agents`` populated. This keeps the strict label
        validation in a single helper and makes future MAGI report
        layout drift cheap to mirror.

        Args:
            marker_path: Filesystem path to the marker JSON file.

        Returns:
            :class:`MAGIVerdict` with ``retried_agents`` set to a tuple
            (possibly empty) of strings.

        Raises:
            ValidationError: Forwarded from :func:`parse_magi_report`
                when the marker JSON is malformed or carries an unknown
                verdict label.
        """
        data = json.loads(Path(marker_path).read_text(encoding="utf-8"))
        retried_raw = data.get("retried_agents") or ()
        retried = tuple(str(a) for a in retried_raw)
        verdict = parse_magi_report(data)
        return cls(
            verdict=verdict.verdict,
            degraded=verdict.degraded,
            conditions=verdict.conditions,
            findings=verdict.findings,
            raw_output=verdict.raw_output,
            retried_agents=retried,
        )


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


def _build_magi_cmd(
    context_paths: list[str],
    output_dir: str | None = None,
    model: str | None = None,
) -> list[str]:
    """Build the argv list for ``claude -p /magi:magi`` with @file refs.

    The slash command and its flags MUST be packed into the single prompt
    string passed to ``claude -p``. ``claude`` itself does NOT accept
    ``--output-dir`` -- that flag belongs to MAGI's ``run_magi.py`` and has
    to travel through the prompt so the sub-session forwards it.

    When ``model`` is provided (v0.3.0 Feature E), ``--model <id>`` is
    inserted BEFORE the ``-p`` flag so claude routes the outer dispatcher
    process to the chosen model. The 3 sub-agents Melchior/Balthasar/Caspar
    pick their own model internally per MAGI plugin contract -- that is
    NOT controlled here. With ``model=None`` argv is byte-identical to
    v0.2.x.
    """
    prompt_parts = ["/magi:magi"]
    for path in context_paths:
        prompt_parts.append(f"@{path}")
    if output_dir is not None:
        prompt_parts.extend(["--output-dir", output_dir])
    cmd: list[str] = ["claude"]
    if model is not None:
        cmd.extend(["--model", model])
    cmd.extend(["-p", " ".join(prompt_parts)])
    return cmd


def invoke_magi(
    context_paths: list[str],
    timeout: int = 1800,
    cwd: str | None = None,
    *,
    model: str | None = None,
    skill_field_name: str = "magi_dispatch_model",
    stream_prefix: str | None = None,
    allow_recovery: bool = True,
) -> MAGIVerdict:
    """Invoke /magi:magi and return a parsed MAGIVerdict.

    MAGI writes its canonical report to ``<output-dir>/magi-report.json``
    (``run_magi.py:536``). We create a :class:`tempfile.TemporaryDirectory`,
    pass its path via ``--output-dir``, and read the JSON from disk after
    the subprocess exits. The ASCII banner on stdout is preserved on the
    returned :class:`MAGIVerdict.raw_output` for diagnostics but is never
    parsed as JSON.

    v0.4.0 Feature F (F46): when the MAGI synthesizer crashes
    (``returncode != 0`` plus stderr matching ``"Only N agent(s) succeeded"``)
    but at least one per-agent ``*.raw.json`` was persisted, the wrapper
    invokes :func:`_manual_synthesis_recovery` to rescue a verdict from
    the surviving raw outputs. Recovery is governed by
    ``allow_recovery``: when ``False`` the v0.3.x behavior of raising
    :class:`MAGIGateError` is preserved verbatim. Quota detection always
    runs first (sec.S.11.4) so credit-exhaustion never silently turns
    into a recovered verdict. INV-28 stays orthogonal: a recovered
    verdict with ``degraded=True`` (fewer than 3 agents recovered) still
    cannot pass the Loop 2 gate at the caller.

    Args:
        context_paths: Files passed to MAGI as ``@file`` references
            (spec-behavior.md, planning/claude-plan-tdd.md, or the diff).
        timeout: Wall-clock seconds before SIGTERM. Default 1800 (30 min)
            because MAGI runs 3 sub-agents sequentially and may need longer
            than superpowers skills.
        cwd: Working directory.
        model: Optional Claude model id forwarded to the outer dispatcher
            via ``claude --model`` (v0.3.0 Feature E).
        skill_field_name: ``plugin.local.md`` key consulted by the INV-0
            cascade (defaults to ``"magi_dispatch_model"``).
        stream_prefix: When set, the subprocess is run with line-by-line
            tee of stdout/stderr to the operator's stderr (v0.3.0 Feature D
            iter 2 fix). When ``None`` the legacy capture path is used
            byte-identically.
        allow_recovery: When ``True`` (default, F46), the
            ``_manual_synthesis_recovery`` branch fires on synthesizer
            crashes. When ``False`` the original
            :class:`MAGIGateError` is raised unchanged -- useful for
            operators wanting strict ``run_magi.py``-only semantics.

    Returns:
        :class:`MAGIVerdict` parsed from ``magi-report.json``, or
        recovered via manual synthesis when the synthesizer crashed.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        MAGIGateError: If the subprocess timed out, exited non-zero without
            matching a quota pattern (and recovery is disabled or also
            failed), or returned 0 but did not write the expected
            ``magi-report.json``. Mapped to exit 8 (MAGI_GATE_BLOCKED) by
            run_sbtdd.py.
        ValidationError: If the report JSON is malformed or carries an
            unknown verdict label (raised by :func:`parse_magi_report`,
            mapped to exit 1).
    """
    # v0.3.0 Feature E: INV-0 cascade then optional --model injection.
    from superpowers_dispatch import _apply_inv0_model_check

    effective_model = _apply_inv0_model_check(model, skill_field_name)
    with tempfile.TemporaryDirectory(prefix="sbtdd-magi-") as tmpdir:
        cmd = _build_magi_cmd(context_paths, output_dir=tmpdir, model=effective_model)
        # iter 2 finding #1 + #7: thread stream_prefix so MAGI Loop 2
        # output reaches the orchestrator's stderr line-by-line during
        # the (often multi-minute) consensus run. Only pass when supplied
        # so test fakes that pre-date v0.3.0 keep accepting the call.
        rwt_kwargs: dict[str, Any] = {"timeout": timeout, "capture": True, "cwd": cwd}
        if stream_prefix is not None:
            rwt_kwargs["stream_prefix"] = stream_prefix
        try:
            result = subprocess_utils.run_with_timeout(cmd, **rwt_kwargs)
        except subprocess.TimeoutExpired as exc:
            raise MAGIGateError(f"/magi:magi timed out after {exc.timeout}s") from exc

        if result.returncode != 0:
            # Quota detection always runs first so credit exhaustion is
            # never masked by recovery (sec.S.11.4).
            exhaustion = quota_detector.detect(result.stderr)
            if exhaustion is not None:
                msg = f"{exhaustion.kind}: {exhaustion.raw_message}"
                if exhaustion.reset_time:
                    msg += f" (reset: {exhaustion.reset_time})"
                raise QuotaExhaustedError(msg)
            # v0.4.0 Feature F (F46): rescue verdicts from per-agent
            # raw outputs when the synthesizer specifically crashed
            # but at least one agent persisted JSON. Skipped when the
            # operator passed ``allow_recovery=False`` (F46.5).
            if allow_recovery and _SYNTH_CRASH_RE.search(result.stderr or ""):
                try:
                    rescued = _manual_synthesis_recovery(Path(tmpdir))
                except MAGIGateError:
                    # Recovery itself failed (no recoverable agents).
                    # Fall through to the original error so the caller
                    # sees the synthesizer message instead of the
                    # recovery one -- the synthesizer message is the
                    # primary diagnostic.
                    pass
                else:
                    # HF1 (sec.2.5): the canonical breadcrumb prefix
                    # "[sbtdd magi] synthesizer failed; manual synthesis recovery applied"
                    # MUST appear on a single source line so docs / spec
                    # / impl can be cross-checked via whitespace-normalised
                    # substring search (tests/test_changelog.py).
                    _msg = "[sbtdd magi] synthesizer failed; manual synthesis recovery applied"
                    sys.stderr.write(f"{_msg} ({len(rescued.findings)} findings)\n")
                    sys.stderr.flush()
                    return rescued
            raise MAGIGateError(
                f"/magi:magi failed (returncode={result.returncode}): {result.stderr.strip()}"
            )

        # v0.4.0 Feature F (F43, iter 2 W1): prefer the forward-compat
        # ``MAGI_VERDICT_MARKER.json`` discovered via recursive glob so
        # future MAGI versions that move the artifact into per-run
        # sub-directories continue to work without code changes. Falls
        # back to the legacy ``magi-report.json`` lookup when no marker
        # exists, which is the current MAGI 2.x contract -- without the
        # fallback this integration would break every shipped MAGI
        # version, so the safety net is mandatory until MAGI emits the
        # marker schema natively.
        try:
            report_path = _discover_verdict_marker(tmpdir)
        except ValidationError:
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


#: Filename of the per-run MAGI verdict marker emitted by MAGI 2.2.1+
#: under the ``--output-dir`` tree. SBTDD consumes the marker via
#: :func:`_discover_verdict_marker` (recursive glob, picks max mtime).
#:
#: Marker schema (HF2, sec.2.5):
#:
#: - ``"verdict"``    — canonical MAGI verdict label (e.g. ``"GO"``)
#: - ``"iteration"``  — 1-indexed iter number within the run
#: - ``"agents"``     — list of agent identifiers that contributed
#: - ``"timestamp"``  — ISO 8601 UTC string with ``Z`` suffix
#:
#: Optional fields (parser tolerates absence): ``retried_agents``,
#: ``synthesizer_status``. SBTDD never writes the marker -- it is the
#: consumer side of the MAGI 2.2.1+ contract.
_MARKER_FILENAME = "MAGI_VERDICT_MARKER.json"

#: Canonical names of the three MAGI agents. Used by
#: :func:`_tolerant_agent_parse` to discriminate verdict objects from
#: incidental ``{...}`` snippets (e.g. embedded code examples) inside
#: an agent's narrative ``result`` field.
_VALID_AGENT_NAMES: frozenset[str] = frozenset({"melchior", "balthasar", "caspar"})

#: Canonical set of verdict labels accepted by :func:`_tolerant_agent_parse`.
#: Iter 2 W2 (MAGI Loop 2 v0.4.0 iter 1 melchior WARNING #2): per spec
#: sec.2.4 the recovery parser must validate ``verdict`` is in a known
#: set in addition to validating ``agent`` is in :data:`_VALID_AGENT_NAMES`.
#: The union covers both axes:
#:
#: - Per-agent verdicts (``approve`` / ``conditional`` / ``reject``) emitted
#:   by individual MAGI agents when their JSON contract is honored.
#: - Synthesis labels (``STRONG_GO`` / ``GO`` / ``GO_WITH_CAVEATS`` /
#:   ``HOLD_TIE`` / ``HOLD`` / ``STRONG_NO_GO``) which historically appear
#:   in per-agent payloads when the synthesizer crashed mid-write or the
#:   agent itself emits a synthesis-style label (observed in v0.3.0
#:   recovery fixtures).
#:
#: A typo'd verdict (e.g. ``"GO_LATER"``, ``"maybe"``) is now rejected
#: outright instead of silently weighing 0.0 in
#: :func:`_manual_synthesis_recovery`. Mirrors the
#: ``models.VERDICT_RANK`` keys plus the lowercase agent verbs.
_VALID_AGENT_VERDICTS: frozenset[str] = frozenset(VERDICT_RANK) | frozenset(
    {"approve", "conditional", "reject"}
)


def _extract_first_balanced_json(text: str) -> str | None:
    """Return the first balanced ``{...}`` JSON-looking substring, or ``None``.

    Walks the text once tracking brace depth, ignoring braces inside
    JSON string literals (with ``\\`` escape-handling). Returns the full
    substring from the first ``{`` to its matching ``}``. Pure stdlib;
    no regex backtracking.

    The caller is responsible for actually JSON-parsing the returned
    substring -- this helper only locates a syntactic candidate.

    Args:
        text: Source text to scan.

    Returns:
        Substring covering the first balanced ``{...}`` block, or
        ``None`` when no balanced block is found.
    """
    depth = 0
    start = -1
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : i + 1]
    return None


def _tolerant_agent_parse(raw_json_path: Path | str) -> dict[str, Any]:
    """Parse an agent's ``*.raw.json`` file with preamble tolerance.

    v0.4.0 Feature F (F45): MAGI v2.2.2 agents sometimes wrap their
    verdict JSON in a narrative preamble inside the ``result`` field
    (e.g. ``"Based on my review...\\n\\n{json}"``). The strict parser
    in ``run_magi.py:synthesize.py`` rejects these payloads outright.

    This helper:

    1. Loads the outer ``*.raw.json`` envelope and extracts the
       ``result`` string.
    2. Tries a strict ``json.loads(result)`` first -- if ``result``
       is pure JSON the function returns immediately, preserving
       byte-identical behavior with the v0.3.x strict parser
       (caspar v0.3.0 iter 2 case).
    3. Otherwise walks ``result`` extracting successive balanced
       ``{...}`` substrings via :func:`_extract_first_balanced_json`,
       JSON-parsing each, and returning the first one that parses
       cleanly **and** carries an ``agent`` field naming one of
       :data:`_VALID_AGENT_NAMES`. This skips embedded code-example
       dicts (``{"key": "val"}``) that lack an agent identity.

    Args:
        raw_json_path: Path to the agent's ``*.raw.json`` file written
            by the MAGI orchestrator.

    Returns:
        Parsed agent verdict dict (the inner JSON object, not the outer
        envelope).

    Raises:
        ValidationError: If the outer envelope lacks a ``result``
            string, or no balanced JSON object inside ``result``
            parses to a dict whose ``agent`` field is one of
            :data:`_VALID_AGENT_NAMES`. The message includes a 200-char
            preview of ``result`` for debugability.
    """
    raw_data = json.loads(Path(raw_json_path).read_text(encoding="utf-8"))
    result = raw_data.get("result")
    if not isinstance(result, str):
        raise ValidationError(
            f"No 'result' string in {raw_json_path} (got {type(result).__name__})"
        )
    # Fast path: pure-JSON result preserves strict-parser semantics.
    try:
        candidate = json.loads(result)
        if _is_valid_verdict_dict(candidate):
            return candidate  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass
    # Preamble-tolerant path: extract balanced ``{...}`` substrings,
    # discard non-verdict candidates, return the first verdict-shaped
    # one. ``cursor`` walks forward through ``result`` so each iteration
    # makes strict progress.
    cursor = 0
    while cursor < len(result):
        substring = _extract_first_balanced_json(result[cursor:])
        if substring is None:
            preview = result[:200].replace("\n", " ")
            raise ValidationError(
                f"No JSON object recoverable from {raw_json_path}: result preview: {preview!r}"
            )
        # Locate the substring within the remaining slice and advance the
        # cursor past it regardless of parse outcome -- guarantees the
        # loop terminates even when the same substring would otherwise
        # be re-extracted.
        local_idx = result[cursor:].find(substring)
        next_cursor = cursor + local_idx + len(substring)
        try:
            candidate = json.loads(substring)
        except json.JSONDecodeError:
            cursor = next_cursor
            continue
        if _is_valid_verdict_dict(candidate):
            return candidate  # type: ignore[no-any-return]
        cursor = next_cursor
    preview = result[:200].replace("\n", " ")
    raise ValidationError(
        f"No JSON object recoverable from {raw_json_path}: result preview: {preview!r}"
    )


def _is_valid_verdict_dict(candidate: Any) -> bool:
    """Return True iff ``candidate`` is a verdict-shaped dict.

    Iter 2 W2 (MAGI Loop 2 v0.4.0 iter 1 melchior WARNING #2):
    centralises the two-axis validation that :func:`_tolerant_agent_parse`
    applies before accepting a candidate dict:

    1. ``agent`` field is one of :data:`_VALID_AGENT_NAMES`.
    2. ``verdict`` field is one of :data:`_VALID_AGENT_VERDICTS` (the
       union of ``models.VERDICT_RANK`` synthesis labels and the
       lowercase agent verbs ``approve`` / ``conditional`` / ``reject``).

    Both axes are required so a typo'd verdict (e.g. ``"GO_LATER"``)
    cannot slip into :func:`_manual_synthesis_recovery` and silently
    weigh 0.0 in the consensus arithmetic.

    Args:
        candidate: Arbitrary parsed JSON value to test.

    Returns:
        True when ``candidate`` is a dict whose ``agent`` and
        ``verdict`` fields both pass the membership checks.
    """
    if not isinstance(candidate, dict):
        return False
    if candidate.get("agent") not in _VALID_AGENT_NAMES:
        return False
    if candidate.get("verdict") not in _VALID_AGENT_VERDICTS:
        return False
    return True


#: Verdict-to-weight map mirroring ``run_magi.py:synthesize.py`` so the
#: recovery synthesis matches MAGI's own consensus arithmetic. ``approve``
#: / ``GO`` / ``STRONG_GO`` weigh +1, ``conditional`` / ``GO_WITH_CAVEATS``
#: weigh +0.5, ``reject`` / ``HOLD`` / ``STRONG_NO_GO`` weigh -1.
_VERDICT_WEIGHT: dict[str, float] = {
    "approve": 1.0,
    "GO": 1.0,
    "STRONG_GO": 1.0,
    "GO_WITH_CAVEATS": 0.5,
    "conditional": 0.5,
    "reject": -1.0,
    "HOLD": -1.0,
    "STRONG_NO_GO": -1.0,
}

#: Stderr regex marking the ``run_magi.py`` synthesizer crash mode that
#: F46 auto-recovery is allowed to rescue. The pattern intentionally
#: matches "Only N agent(s) succeeded" anywhere in stderr -- MAGI emits
#: it as part of the RuntimeError message when fewer than the required
#: minimum of agents finished cleanly. See INV-28 + sec.S.5.6.b.
_SYNTH_CRASH_RE = re.compile(r"Only\s+\d+\s+agent\(s\)\s+succeeded", re.IGNORECASE)


def _manual_synthesis_recovery(run_dir: Path | str) -> MAGIVerdict:
    """Recover a MAGI verdict when the synthesizer crashed.

    v0.4.0 Feature F (F46): when ``run_magi.py`` aborts with a
    ``RuntimeError`` (e.g. ``"Only N agent(s) succeeded -- fewer than
    required"``) but at least one agent persisted a ``*.raw.json``
    file, this helper:

    1. Walks ``run_dir`` for ``*.raw.json`` files.
    2. Applies :func:`_tolerant_agent_parse` (F45) to each, accepting
       both pure-JSON and preamble-wrapped agent results.
    3. Synthesises a verdict using the same weight scheme as
       ``run_magi.py:synthesize.py`` (``approve`` +1,
       ``GO_WITH_CAVEATS``/``conditional`` +0.5, ``reject``/``HOLD``
       -1) and emits a ``manual-synthesis.json`` recovery report
       flagged ``recovered: true`` /
       ``recovery_reason: "synthesizer-failure"``.

    Designed for use both standalone (operator runs it from a REPL on
    a stale ``run_dir``) and as the auto-recovery branch inside
    :func:`invoke_magi`.

    Args:
        run_dir: Directory containing per-agent ``*.raw.json`` files.

    Returns:
        :class:`MAGIVerdict` rescued from the raw outputs. ``degraded``
        is ``True`` when fewer than 3 agents had recoverable JSON.

    Raises:
        MAGIGateError: If zero agents have recoverable JSON. The
            recovery cannot proceed; the operator must investigate the
            ``*.raw.json`` files manually or retry the MAGI iteration.
    """
    base = Path(run_dir)
    raw_files = sorted(base.glob("*.raw.json"))
    parsed: list[dict[str, Any]] = []
    failures: list[str] = []
    for raw in raw_files:
        try:
            parsed.append(_tolerant_agent_parse(raw))
        except ValidationError as exc:
            failures.append(f"{raw.name}: {exc}")
    if not parsed:
        raise MAGIGateError(
            f"No recoverable agent verdicts in {base}; manual synthesis impossible. "
            f"Failures: {failures}"
        )
    score = sum(_VERDICT_WEIGHT.get(str(p.get("verdict", "")), 0.0) for p in parsed) / len(parsed)
    has_conditional = any(
        str(p.get("verdict", "")) in ("conditional", "GO_WITH_CAVEATS") for p in parsed
    )
    approves = sum(1 for p in parsed if _VERDICT_WEIGHT.get(str(p.get("verdict", "")), 0.0) > 0)
    rejects = sum(1 for p in parsed if _VERDICT_WEIGHT.get(str(p.get("verdict", "")), 0.0) < 0)
    if score == 1.0:
        label = "STRONG_GO"
    elif score == -1.0:
        label = "STRONG_NO_GO"
    elif score > 0:
        label = "GO_WITH_CAVEATS" if has_conditional else "GO"
    elif score < 0:
        label = "HOLD"
    else:
        label = "HOLD_TIE"
    findings: list[dict[str, Any]] = []
    for p in parsed:
        for f in p.get("findings", []) or []:
            if isinstance(f, dict):
                findings.append({**f, "from_agent": p.get("agent", "unknown")})
            else:
                findings.append({"message": str(f), "from_agent": p.get("agent", "unknown")})
    degraded = len(parsed) < 3
    report = {
        "recovered": True,
        "recovery_reason": "synthesizer-failure",
        "consensus": {
            "label": label,
            "score": score,
            "approves": approves,
            "rejects": rejects,
            "degraded": degraded,
        },
        "agents": [str(p.get("agent", "unknown")) for p in parsed],
        "agents_failed": failures,
        "findings": findings,
    }
    (base / "manual-synthesis.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=tuple(),
        findings=tuple(findings),
        raw_output=json.dumps(report),
        retried_agents=(),
    )


def _discover_verdict_marker(output_dir: Path | str) -> Path:
    """Discover the most recent MAGI verdict marker in an output directory.

    v0.4.0 Feature F (F43): replaces fragile path-based discovery
    (``output_dir / "magi-report.json"``) with marker enumeration via
    :meth:`pathlib.Path.rglob`. Picks the marker with max ``mtime`` so
    re-runs in the same directory return the latest result. Defensive
    against MAGI layout changes (e.g. moving markers into per-run
    sub-directories).

    Args:
        output_dir: Directory to scan recursively for
            ``MAGI_VERDICT_MARKER.json`` files.

    Returns:
        Path to the most recent marker file, ranked by modification time.

    Raises:
        ValidationError: If no markers are present, with detail listing the
            files actually present in ``output_dir`` (top-level only) for
            debugability. The listing intentionally omits sub-directories
            because a missing marker is itself the diagnostic; deeper layout
            inspection is the operator's job once the error fires.
    """
    base = Path(output_dir)
    candidates = sorted(base.rglob(_MARKER_FILENAME), key=lambda p: p.stat().st_mtime)
    if not candidates:
        present = sorted(p.name for p in base.iterdir()) if base.exists() else []
        raise ValidationError(f"No {_MARKER_FILENAME} found in {base}. Files present: {present}")
    return candidates[-1]


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
