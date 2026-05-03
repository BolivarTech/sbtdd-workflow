#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd pre-merge -- Loop 1 + Loop 2 (sec.S.5.6, INV-9/28/29).

Loop 1 runs ``/requesting-code-review`` until it reports ``clean-to-go``
(mechanical findings) with a hardcoded safety valve of 10 iterations.
Loop 2 runs ``/magi:magi`` to evaluate trade-offs and design risks. When
MAGI returns accepted conditions (through the INV-29 gate of
``/receiving-code-review``), Loop 2 writes them to
``.claude/magi-conditions.md`` and raises :class:`errors.MAGIGateError`
(exit 8) instead of emitting empty commits. The user applies each
condition via ``sbtdd close-phase`` (which has the real TDD cycle
machinery) and re-runs ``sbtdd pre-merge`` to re-evaluate. Rejected
conditions feed into ``.claude/magi-feedback.md`` so the next MAGI
invocation receives their rationale as context -- this is the sterile
loop breaker preserved from iter-1.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import escalation_prompt
import magi_dispatch
import receiving_review_dispatch
import subprocess_utils
import superpowers_dispatch
from config import PluginConfig, load_plugin_local
from drift import detect_drift
from errors import (
    DriftError,
    Loop1DivergentError,
    MAGIGateError,
    PreconditionError,
    ValidationError,
)
from models import VERDICT_RANK
from state_file import SessionState
from state_file import load as load_state

_T = TypeVar("_T")

#: Safety valve for Loop 1 (sec.S.5.6, INV-11). Exceeding aborts with exit 7.
_LOOP1_MAX: int = 10


def _wrap_with_heartbeat_if_auto(
    invoke: Callable[[], _T],
    *,
    iter_num: int = 0,
    phase: int,
    dispatch_label: str,
) -> _T:
    """Conditionally wrap ``invoke`` with auto-mode's heartbeat emitter.

    Loop 1 fix v0.5.0 CRITICAL #1: pre-merge dispatches (Loop 1
    requesting-code-review, Loop 2 invoke_magi, mini-cycle TDD) are
    multi-minute subprocess calls. Under ``/sbtdd auto`` the operator
    needs liveness ticks via ``HeartbeatEmitter`` to distinguish
    "still working" from "hung". Under interactive ``/sbtdd pre-merge``
    the operator is watching directly so the wrap is a no-op.

    The auto-mode signal is a ``ProgressContext`` whose ``phase`` field
    is non-zero (auto's ``_phase3_pre_merge`` sets ``phase=3`` before
    calling ``_loop2``). When invoked outside auto (interactive
    pre-merge or test fixtures bypassing auto), ``phase==0`` and we
    fall back to a direct call so the wrapping cost is paid only when
    the heartbeat actually serves the operator.

    Args:
        invoke: Zero-argument callable performing the dispatch.
        iter_num: Optional iteration number to include in progress.
        phase: Pre-merge phase (3) per spec sec.3 progress enumeration.
        dispatch_label: Human-readable dispatch identifier (e.g.
            ``"magi-loop2-iter1"``).

    Returns:
        Whatever ``invoke()`` returns.
    """
    try:
        from heartbeat import get_current_progress

        import auto_cmd as _auto

        current = get_current_progress()
        is_auto_mode = current.phase != 0
    except (AttributeError, ImportError, RuntimeError, LookupError):
        # Per Loop 2 iter 4 W4 fix (caspar): narrow except to introspection
        # failures only. AttributeError covers None / duck-typing misses,
        # ImportError covers missing optional deps, RuntimeError covers
        # heartbeat-state breakage, LookupError covers ContextVar.get()
        # without a default. ValueError (the fail-loud signal from
        # ``_dispatch_with_heartbeat`` when ``dispatch_label`` is None)
        # MUST propagate so the operator catches the misuse rather than
        # silently degrading to a direct call.
        is_auto_mode = False
    if is_auto_mode:
        # auto-mode active; wrap with heartbeat emitter.
        _auto._set_progress(
            iter_num=iter_num or current.iter_num,
            phase=phase,
            task_index=current.task_index,
            task_total=current.task_total,
            dispatch_label=dispatch_label,
        )
        result: _T = _auto._dispatch_with_heartbeat(invoke=invoke)
        return result
    return invoke()


#: Filename of the auxiliary rejection-feedback file written between iterations.
#: Lives inside the destination project's ``.claude/`` (gitignored, never
#: committed). See :func:`_write_magi_feedback_file` for the rationale.
_MAGI_FEEDBACK_FILENAME: str = "magi-feedback.md"

#: Filename where accepted MAGI conditions are surfaced to the user at the
#: end of a blocked Loop 2 iteration. MAGI Loop 2 iter-3 redesign: the
#: gate no longer orchestrates a mini-cycle it cannot populate (the fix
#: diff must be authored by a human or subagent via ``close-phase``).
#: Lives inside ``.claude/`` (gitignored, never committed).
_MAGI_CONDITIONS_FILENAME: str = "magi-conditions.md"
_MAGI_FINDINGS_FILENAME: str = "magi-findings.md"


def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``sbtdd pre-merge``."""
    p = argparse.ArgumentParser(prog="sbtdd pre-merge")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--magi-threshold",
        type=str,
        default=None,
        help="Override magi_threshold (ELEVATE only).",
    )
    p.add_argument(
        "--override-checkpoint",
        action="store_true",
        help="Override MAGI gate per INV-0 on safety-valve exhaustion; requires --reason",
    )
    p.add_argument(
        "--reason",
        type=str,
        default=None,
        help="Mandatory when --override-checkpoint is set",
    )
    p.add_argument(
        "--non-interactive",
        action="store_true",
        help="Force headless path on safety-valve exhaustion (apply .claude/magi-auto-policy.json)",
    )
    return p


def _plan_id_from_path(name: str) -> str:
    """Extract plan id suffix from filename (``claude-plan-tdd-A.md`` -> ``"A"``).

    Returns ``"X"`` when the filename has no ``-<ID>.md`` suffix (the plain
    pre-merge default ``claude-plan-tdd.md``).
    """
    m = re.search(r"-([A-Z0-9]+)\.md$", name)
    return m.group(1) if m else "X"


def _preflight(root: Path) -> SessionState:
    """Verify preconditions for /sbtdd pre-merge.

    Preconditions (sec.S.5.6):
      - ``.claude/session-state.json`` exists.
      - ``current_phase`` is exactly ``done``.
      - No drift between state file, git HEAD, and plan.

    Args:
        root: Project root directory.

    Returns:
        The loaded :class:`SessionState`.

    Raises:
        PreconditionError: Missing state file or current_phase != done.
        DriftError: Drift between state / git HEAD / plan detected.
    """
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.current_phase != "done":
        raise PreconditionError(
            f"pre-merge requires current_phase='done', got '{state.current_phase}'"
        )
    plan_path = root / state.plan_path
    drift_report = detect_drift(state_path, plan_path, root)
    if drift_report is not None:
        raise DriftError(
            f"drift detected: state={drift_report.state_value}, "
            f"HEAD={drift_report.git_value}:, plan={drift_report.plan_value}"
        )
    return state


def _is_clean_to_go(result: object) -> bool:
    """Return True iff the skill's stdout advertises a ``clean-to-go`` signal.

    Accepts either ``clean-to-go`` (hyphenated) or ``clean to go`` (spaced)
    case-insensitively; the superpowers skill has emitted both forms in
    practice.
    """
    stdout_attr = getattr(result, "stdout", None) if result is not None else None
    out = stdout_attr.lower() if isinstance(stdout_attr, str) else ""
    return "clean-to-go" in out or "clean to go" in out


def _loop1(root: Path) -> None:
    """Run Loop 1 -- ``/requesting-code-review`` until clean-to-go (sec.S.5.6).

    Each iteration invokes ``/requesting-code-review``. If the skill
    result does not advertise ``clean-to-go`` the loop invokes
    ``/receiving-code-review`` to apply fixes. Loop 1 stays at the
    skill-invocation level because the superpowers contract does not
    expose individual findings here; the skill owns the remediation.

    Args:
        root: Project root directory passed to the skill as ``cwd``.

    Raises:
        Loop1DivergentError: If the loop exhausts :data:`_LOOP1_MAX`
            iterations without reaching ``clean-to-go``.
    """
    for iteration in range(1, _LOOP1_MAX + 1):
        # v0.4.0 J8.2: thread a per-iter stream_prefix so the operator
        # can correlate streamed subprocess output with the Loop 1
        # iteration that produced it. The iter number is 1-based to
        # match the safety-valve diagnostics emitted on divergence.
        loop1_prefix = f"[sbtdd pre-merge loop1 iter-{iteration}]"
        # Loop 1 fix v0.5.0 CRITICAL #1: under auto, wrap with heartbeat.
        result = _wrap_with_heartbeat_if_auto(
            invoke=lambda: superpowers_dispatch.requesting_code_review(
                cwd=str(root),
                stream_prefix=loop1_prefix,
            ),
            iter_num=iteration,
            phase=3,
            dispatch_label=f"code-review-loop1-iter{iteration}",
        )
        if _is_clean_to_go(result):
            return
        _wrap_with_heartbeat_if_auto(
            invoke=lambda: superpowers_dispatch.receiving_code_review(
                cwd=str(root),
                stream_prefix=loop1_prefix,
            ),
            iter_num=iteration,
            phase=3,
            dispatch_label=f"receiving-code-review-loop1-iter{iteration}",
        )
    raise Loop1DivergentError(f"Loop 1 did not converge in {_LOOP1_MAX} iterations")


# Backward-compat re-exports for the parser + section regex.
#
# v0.2.1 promoted ``_parse_receiving_review`` and the format contract to
# ``receiving_review_dispatch`` so ``auto_cmd._apply_spec_review_findings_via_mini_cycle``
# can share them. Tests written against the v0.2.0 private names continue
# to import from this module unchanged.
_SECTION_HEADER_RE: re.Pattern[str] = receiving_review_dispatch._SECTION_HEADER_RE
_parse_receiving_review = receiving_review_dispatch.parse_receiving_review


def _safe_threshold_rank(threshold: str) -> int:
    """Return ``VERDICT_RANK[threshold]`` or raise :class:`ValidationError`.

    Ensures threshold-override errors flow through the ``SBTDDError``
    hierarchy so the dispatcher maps them to exit 1 (USER_ERROR), not an
    unhandled ``KeyError`` (iter-2 Finding 5).
    """
    if threshold not in VERDICT_RANK:
        raise ValidationError(
            f"threshold '{threshold}' not in VERDICT_RANK "
            f"(valid values: {', '.join(sorted(VERDICT_RANK))})"
        )
    return VERDICT_RANK[threshold]


def _now_iso() -> str:
    """Return UTC ISO 8601 timestamp with a ``Z`` suffix.

    Finding 3 (Caspar): emitted in the conditions-file frontmatter as
    ``generated_at``. Kept module-local to preserve the stdlib-only
    import policy of ``pre_merge_cmd`` (no cross-module borrowing for a
    one-line helper).
    """
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_head_sha(root: Path) -> str:
    """Return short SHA of ``HEAD`` at ``root`` or ``"unknown"``.

    Uses ``git rev-parse --short HEAD`` with a 10s timeout. Non-zero
    exit (e.g. ``root`` is not a git repo, or ``HEAD`` does not point to
    a commit yet) returns the literal string ``"unknown"`` so the
    frontmatter remains valid YAML even when traceability is
    unavailable.
    """
    try:
        r = subprocess_utils.run_with_timeout(
            ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
        )
    except Exception:
        return "unknown"
    if r.returncode != 0:
        return "unknown"
    return r.stdout.strip() or "unknown"


def _build_conditions_frontmatter(
    root: Path, verdict: magi_dispatch.MAGIVerdict, iteration: int
) -> str:
    """Return a YAML frontmatter block documenting the pre-merge iteration.

    Finding 3 (Caspar): since ``_write_magi_conditions_file`` overwrites
    ``.claude/magi-conditions.md`` on every pre-merge invocation, each
    write must carry enough provenance for a reader to reconstruct the
    sequence post-hoc. The block emits four keys: ``generated_at`` (ISO
    8601 with Z suffix), ``magi_iteration`` (1-indexed int matching
    :func:`_loop2` iteration counter), ``pre_merge_head_sha`` (short
    HEAD SHA or ``unknown``), and ``verdict`` (MAGI verdict string).

    Returns the block including the leading ``---``, trailing ``---``,
    and a blank line so the caller can concatenate it as the file prefix
    without extra plumbing.
    """
    fm = "---\n"
    fm += f"generated_at: {_now_iso()}\n"
    fm += f"magi_iteration: {iteration}\n"
    fm += f"pre_merge_head_sha: {_current_head_sha(root)}\n"
    fm += f"verdict: {verdict.verdict}\n"
    fm += "---\n\n"
    return fm


def _write_magi_conditions_file(
    conditions: list[str], root: Path, verdict: magi_dispatch.MAGIVerdict, iteration: int
) -> Path:
    """Persist accepted MAGI conditions to ``.claude/magi-conditions.md``.

    MAGI Loop 2 iter-3 redesign: ``_loop2`` no longer invokes a
    mini-cycle for accepted conditions because it cannot synthesize the
    code edits (they must come from human/subagent judgment via
    ``close-phase``). Instead, the gate writes the accepted conditions to
    this file, prints user-visible instructions, and raises
    :class:`MAGIGateError` (exit 8). The user reads the file, applies
    the fixes via ``close-phase`` (which has real TDD cycle support), and
    re-runs ``pre-merge``. The feedback-for-rejections mechanism
    (:func:`_write_magi_feedback_file`) is preserved for sterile-loop
    breaking.

    Args:
        conditions: Accepted conditions (one markdown bullet per entry).
        root: Project root directory (file lands in ``root/.claude/``).
        verdict: The MAGI verdict whose conditions triggered this write
            (captured in the file header for the audit trail).
        iteration: 1-indexed MAGI iteration number (for the header).

    Returns:
        Absolute path to the written file.
    """
    path = root / ".claude" / _MAGI_CONDITIONS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    # Finding 3 (Caspar): each pre-merge invocation overwrites this
    # file, losing prior iteration history. A YAML frontmatter block
    # carrying iteration number, ISO 8601 timestamp, short HEAD SHA, and
    # the MAGI verdict makes every overwrite self-describing -- a log
    # reader (or a future append-mode audit sidecar) can reconstruct the
    # sequence post-hoc without reparsing markdown content.
    body = _build_conditions_frontmatter(root, verdict, iteration)
    body += "# MAGI Loop 2 -- accepted conditions pending\n\n"
    body += (
        f"MAGI iteration {iteration} returned verdict `{verdict.verdict}` with "
        "the following conditions accepted by `/receiving-code-review`. They are "
        "BLOCKING the pre-merge gate until applied.\n\n"
    )
    body += "## Instructions\n\n"
    body += (
        "1. For each condition below, apply the fix through the normal TDD "
        "cycle by running `sbtdd close-phase` for Red, Green, and Refactor.\n"
        "2. Once every condition is materialised as commits on the branch, "
        "re-run `sbtdd pre-merge` to re-evaluate the gate.\n"
        "3. Rejected conditions (if any) are tracked separately in "
        "`.claude/magi-feedback.md` so the next MAGI invocation receives "
        "their rationale as context.\n\n"
    )
    body += "## Accepted conditions\n\n"
    for cond in conditions:
        body += f"- {cond}\n"
    body += "\n## How to apply these conditions\n\n"
    body += (
        "Step-by-step recovery sequence (one pass per accepted condition):\n\n"
        "1. Edit code to address the condition.\n"
        "2. Add a failing test that reproduces the gap (Red phase).\n"
        '3. `sbtdd close-phase --variant test --message "<red msg>"` to '
        "close Red.\n"
        '4. `sbtdd close-phase --variant fix --message "<green msg>"` to '
        "close Green.\n"
        '5. `sbtdd close-phase --variant refactor --message "<refactor '
        'msg>"` to close Refactor.\n'
        "6. `sbtdd close-task --project-root .` to advance state to the "
        "next task (or to `done` if this was the last one).\n"
        "7. After every accepted condition has its own 3-commit cycle on "
        "the branch, re-run `sbtdd pre-merge --project-root .`. MAGI "
        "re-evaluates the new diff; if conditions are genuinely addressed "
        "the gate clears.\n\n"
        "If `/receiving-code-review` rejects one of the conditions "
        "above on a later re-run, the rejection is written to "
        "`.claude/magi-feedback.md` and fed to the next MAGI iteration "
        "as context instead of being applied.\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def _write_magi_findings_file(
    findings: tuple[dict[str, object], ...],
    root: Path,
    verdict: magi_dispatch.MAGIVerdict,
    iteration: int,
) -> Path | None:
    """Persist MAGI's full ``consensus.findings`` list to ``.claude/magi-findings.md``.

    ``magi-conditions.md`` captures the ONE-LINE agent-level summaries
    that ``/receiving-code-review`` accepts as blocking conditions, but
    those summaries rarely contain the actionable defect detail the user
    needs to fix (observed 2026-04-24 pre-merge Loop 2 iter 1: conditions
    said "four concrete correctness defects" without enumerating them).
    The detail lives in ``consensus.findings`` -- severity-tagged
    finding dicts with ``title``, ``detail``, ``sources``. This file
    persists them alongside the conditions so the user can act on the
    concrete defects without re-running MAGI just to recover output.

    Returns ``None`` when the verdict produced zero findings (no file
    written); otherwise the absolute path to the written file.
    """
    if not findings:
        return None
    path = root / ".claude" / _MAGI_FINDINGS_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    body = _build_conditions_frontmatter(root, verdict, iteration)
    body += "# MAGI Loop 2 -- consensus findings\n\n"
    body += (
        f"MAGI iteration {iteration} returned verdict `{verdict.verdict}` with "
        f"the following {len(findings)} finding(s) from the deduplicated "
        "``consensus.findings`` list. Use these as the concrete defect "
        "list when applying the accepted conditions in "
        f"``.claude/{_MAGI_CONDITIONS_FILENAME}``.\n\n"
    )
    for i, finding in enumerate(findings, start=1):
        severity = str(finding.get("severity", "unknown")).upper()
        title = str(finding.get("title", "(no title)"))
        detail = str(finding.get("detail", "")).strip()
        sources_raw = finding.get("sources", [])
        if isinstance(sources_raw, list):
            sources = ", ".join(str(s) for s in sources_raw)
        else:
            sources = str(sources_raw)
        body += f"## {i}. [{severity}] {title}\n\n"
        if sources:
            body += f"**Sources:** {sources}\n\n"
        if detail:
            body += f"{detail}\n\n"
    path.write_text(body, encoding="utf-8")
    return path


def _write_magi_feedback_file(root: Path, rejections: list[str]) -> Path:
    """Persist rejection history to ``.claude/magi-feedback.md`` for next iter.

    Implements iter-2 Finding W6 Option B: the current
    :func:`magi_dispatch.invoke_magi` signature does NOT accept an
    ``extra_context`` kwarg. Instead of extending the frozen Milestone B
    API, rejection feedback is passed through an auxiliary file that MAGI
    reads via its ``context_paths`` argument. The file lives at
    ``.claude/magi-feedback.md`` (inside the destination project's
    ``.claude/`` gitignored dir, never committed) and is overwritten each
    iteration with the full rejection history so MAGI receives cumulative
    context, not per-iter deltas.
    """
    path = root / ".claude" / _MAGI_FEEDBACK_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "# MAGI iteration feedback\n\n"
    body += (
        "The following conditions from prior iterations were REJECTED "
        "by /receiving-code-review with documented rationale. Re-raising "
        "them without new evidence produces sterile loops.\n\n"
    )
    for line in rejections:
        body += f"- {line}\n"
    path.write_text(body, encoding="utf-8")
    return path


# Backward-compat re-exports for the format contract + arg serialiser.
#
# v0.2.1 promoted these to ``receiving_review_dispatch``. Both
# ``_RECEIVING_REVIEW_FORMAT_CONTRACT`` and ``_conditions_to_skill_args``
# remain importable so v0.2.0-vintage tests continue to pass.
_RECEIVING_REVIEW_FORMAT_CONTRACT = receiving_review_dispatch.RECEIVING_REVIEW_FORMAT_CONTRACT
_conditions_to_skill_args = receiving_review_dispatch.conditions_to_skill_args


def _handle_safety_valve_exhaustion(
    root: Path,
    cfg: PluginConfig,
    verdict_history: list[magi_dispatch.MAGIVerdict],
    last_accepted: tuple[str, ...],
    last_rejected: tuple[str, ...],
    ns: argparse.Namespace,
) -> magi_dispatch.MAGIVerdict:
    """Route exhausted Loop 2 through ``escalation_prompt`` (Feature A).

    Mirror of ``spec_cmd._handle_safety_valve_exhaustion`` for pre-merge
    Loop 2. Terminal outcomes:

    * ``override`` (or ``--override-checkpoint --reason``): return the last
      observed verdict, letting the caller proceed per INV-0 user authority.
    * ``abandon`` or any other action: raise :class:`MAGIGateError` carrying
      the iteration cap and the rejected/accepted conditions seen across the
      loop (mirrors the MAGIGateError payload of the v0.1 raise path).

    In every outcome ``escalation_prompt.apply_decision`` writes a JSON
    audit artifact under ``<root>/.claude/magi-escalations/``.

    Raises:
        MAGIGateError: ``--override-checkpoint`` without ``--reason``, no
            verdict observed while overriding, or the user chose to abandon
            the flow.
    """
    last_verdict = verdict_history[-1] if verdict_history else None
    ctx = escalation_prompt.build_escalation_context(
        iterations=list(verdict_history),
        plan_id=_plan_id_from_path(Path(cfg.plan_path).name),
        context="pre-merge",
    )
    # _compose_options is a semi-public helper (also consumed by tests in
    # test_escalation_prompt.py); promoting it to a public name is scoped
    # out to keep this mirror aligned with spec_cmd's equivalent helper.
    options = escalation_prompt._compose_options(ctx)
    if ns.override_checkpoint:
        if not ns.reason:
            raise MAGIGateError("--override-checkpoint requires --reason")
        decision = escalation_prompt.UserDecision(
            chosen_option="a", action="override", reason=ns.reason
        )
    else:
        decision = escalation_prompt.prompt_user(
            ctx, options, non_interactive=ns.non_interactive, project_root=root
        )
    escalation_prompt.apply_decision(decision, ctx, root)
    if decision.action == "override" and last_verdict is not None:
        return last_verdict
    raise MAGIGateError(
        f"user chose '{decision.action}' on pre-merge Loop 2 exhaustion",
        accepted_conditions=last_accepted,
        rejected_conditions=last_rejected,
        verdict=last_verdict.verdict if last_verdict is not None else None,
        iteration=cfg.magi_max_iterations,
    )


def _loop2(
    root: Path,
    cfg: PluginConfig,
    threshold_override: str | None,
    ns: argparse.Namespace | None = None,
) -> magi_dispatch.MAGIVerdict:
    """Run Loop 2 -- ``/magi:magi`` with INV-28 + INV-29 (sec.S.5.6).

    **INV-29 contract (feedback loop).** Rejected MAGI conditions are not
    silently discarded: every ``/receiving-code-review`` rejection is
    appended to ``rejections`` and written as a feedback file that is
    passed as an extra context path on the next MAGI iteration. This
    breaks the "sterile loop" where MAGI keeps re-emitting the same
    technically-wrong condition because it has no visibility into why the
    previous iteration rejected it. The rationale is preserved across
    iterations until the gate is passed or iterations are exhausted. See
    :func:`_write_magi_feedback_file` for the on-disk format.

    **Stale-conditions invariant (D iter 1 Caspar).** On entry the loop
    unlinks any existing ``.claude/magi-conditions.md`` left by a
    previous exit-8 run. This guarantees that after ``_loop2`` returns or
    raises, at most one conditions file exists and its content matches
    the current invocation -- never a stale snapshot from resolved
    iterations. The invariant is load-bearing for
    :mod:`resume_cmd`: without it, resume would detect the stale file
    and misdirect the user to ``sbtdd close-phase`` even when the
    conditions were already applied.

    MAGI Loop 2 iter-3 redesign: the gate no longer orchestrates a
    three-commit mini-cycle for accepted conditions. ``_loop2`` cannot
    synthesize code edits -- the fix diff must come from human or
    subagent judgment via :mod:`close_phase_cmd` (which has real TDD
    cycle support). When ``/receiving-code-review`` accepts one or more
    MAGI conditions, ``_loop2``:

    1. Writes the accepted conditions to ``.claude/magi-conditions.md``
       via :func:`_write_magi_conditions_file` (with user-visible
       instructions on how to materialise the fixes).
    2. Raises :class:`MAGIGateError` (exit 8).

    The user then applies each accepted condition via ``sbtdd
    close-phase`` and re-runs ``sbtdd pre-merge``. The next run
    re-evaluates the gate against the updated diff. Rejected conditions
    still feed :func:`_write_magi_feedback_file` so subsequent MAGI
    invocations receive the rationale as context (sterile-loop breaker
    preserved). STRONG_NO_GO short-circuits the loop immediately
    (INV-28 exception). Iterations are capped at
    ``cfg.magi_max_iterations``.

    Args:
        root: Project root directory.
        cfg: Parsed plugin configuration (for ``magi_threshold`` and
            ``magi_max_iterations``).
        threshold_override: Optional threshold override passed via
            ``--magi-threshold``. Must ELEVATE the configured threshold,
            never lower it.

    Returns:
        The last :class:`magi_dispatch.MAGIVerdict` that cleared the gate
        WITH zero accepted conditions pending.

    Raises:
        MAGIGateError: STRONG_NO_GO at any iteration, accepted
            conditions pending (exit 8 -- conditions file written), or
            iterations exhausted without reaching ``threshold`` full.
        ValidationError: Unknown threshold override, or
            ``/receiving-code-review`` produced no decisions for
            non-empty MAGI conditions.
    """
    threshold = threshold_override or cfg.magi_threshold
    if _safe_threshold_rank(threshold) < _safe_threshold_rank(cfg.magi_threshold):
        raise ValidationError(
            f"--magi-threshold can only elevate; {threshold} < config {cfg.magi_threshold}"
        )
    # v1.0.0 C1 wiring (O-2 Loop 1 review): emit the G4 cross-check-disabled
    # stderr breadcrumb once per Loop 2 invocation so operators see the
    # sub-phase is OFF rather than silently inactive. No-op (early return)
    # when ``cfg.magi_cross_check`` is True.
    _emit_cross_check_disabled_breadcrumb_once(cfg)
    # MAGI Loop 2 D iter 1 Caspar: unlink any stale ``magi-conditions.md``
    # from a previous exit-8 run before starting this loop. If the gate
    # later reaches GO we leave no spurious artifact behind; if it exits
    # 8 again, ``_write_magi_conditions_file`` rewrites the file fresh
    # with current-iteration frontmatter. Net guarantee: at most one
    # ``magi-conditions.md`` exists after ``_loop2`` returns/raises, and
    # its content always matches the current invocation -- never a prior
    # run's already-resolved conditions that would trap ``resume_cmd``
    # into misdirecting the user.
    _stale_conditions = root / ".claude" / _MAGI_CONDITIONS_FILENAME
    try:
        _stale_conditions.unlink()
    except FileNotFoundError:
        pass
    diff_paths = [str(root / cfg.plan_path)]
    # Pre-existing ``magi-feedback.md`` (operator-curated context for the
    # sterile-loop breaker) gets included in iter 1 so MAGI receives the
    # operator's framing before it builds its own rejection list. The
    # subsequent ``_write_magi_feedback_file`` calls overwrite the file
    # with the in-memory rejections so subsequent iters get the
    # accumulated picture; the operator's seed lives only in iter 1.
    # Observed v0.2 pre-merge 2026-04-24 (CRITICAL #1/#3/#12 + #2/#5/#6
    # were re-flagged in iter 1 even after code-side fixes had landed
    # because MAGI only saw the plan markdown, not the new HEAD).
    operator_feedback = root / ".claude" / _MAGI_FEEDBACK_FILENAME
    seed_feedback_path = str(operator_feedback) if operator_feedback.exists() else None
    rejections: list[str] = []
    last_accepted: tuple[str, ...] = ()
    last_rejected: tuple[str, ...] = ()
    verdict_history: list[magi_dispatch.MAGIVerdict] = []
    for iteration in range(1, cfg.magi_max_iterations + 1):
        iter_paths = list(diff_paths)
        if rejections:
            iter_paths.append(str(_write_magi_feedback_file(root, rejections)))
        elif seed_feedback_path is not None and iteration == 1:
            iter_paths.append(seed_feedback_path)
        # v0.4.0 J8.1: thread a per-iter stream_prefix so the operator
        # can correlate the (slow, multi-minute) MAGI subprocess output
        # with which Loop 2 iteration is currently running.
        loop2_magi_prefix = f"[sbtdd pre-merge magi-loop2 iter-{iteration}]"
        # Loop 1 fix v0.5.0 CRITICAL #1: under auto, wrap each MAGI
        # iter in HeartbeatEmitter (label = ``magi-loop2-iter<N>``) so
        # the operator sees liveness ticks during the multi-minute
        # consensus run. ``_wrap_with_heartbeat_if_auto`` falls back
        # to a direct call under interactive pre-merge.
        verdict = _wrap_with_heartbeat_if_auto(
            invoke=lambda: magi_dispatch.invoke_magi(
                context_paths=iter_paths,
                cwd=str(root),
                stream_prefix=loop2_magi_prefix,
            ),
            iter_num=iteration,
            phase=3,
            dispatch_label=f"magi-loop2-iter{iteration}",
        )
        # v1.0.0 C1 wiring (O-2 Loop 1 review CRITICAL #1): when
        # ``cfg.magi_cross_check`` is True, route MAGI findings through the
        # ``/requesting-code-review`` meta-reviewer (Feature G, INV-35).
        # Annotation-only redesign per CRITICAL #1+#4: cross-check NEVER
        # removes findings -- it tags each with ``cross_check_decision``
        # (KEEP|DOWNGRADE|REJECT) + rationale. INV-29 (operator +
        # ``/receiving-code-review``) is the only stage that may filter.
        # Reconstruct the verdict via ``dataclasses.replace`` so downstream
        # consumers (``_write_magi_findings_file``, audit emit) see the
        # annotated set without breaking the frozen-dataclass contract.
        # ``getattr`` default keeps backward-compat with pre-v1.0.0 duck-typed
        # shadow configs (e.g. _ShadowCfg from auto_cmd) that may lack the
        # field; absence is treated as opted-out.
        if getattr(cfg, "magi_cross_check", False):
            # v1.0.0 Loop 2 iter 2->3 R11 sweep: route through the
            # ``auto_cmd._phase4_pre_merge_audit_dir`` helper so the
            # audit-directory path has a single source of truth shared
            # between pre-merge and auto-mode call sites. Deferred import
            # honors the cross-subagent boundary (pre_merge_cmd is the
            # dispatcher; auto_cmd owns the helper).
            import auto_cmd  # noqa: PLC0415 - deferred to honor cross-module boundary

            audit_dir = auto_cmd._phase4_pre_merge_audit_dir(root)
            # v1.0.0 W4 (caspar Loop 2 iter 4): normalize findings before
            # they enter the cross-check meta-reviewer. In iter 1, MAGI's
            # consensus.findings list is fresh and carries no annotation
            # fields, so this call is a no-op; in iter 2+, if a future
            # refactor were to thread prior-iter annotated findings into
            # the MAGI payload (e.g., as context), the normalizer strips
            # ``cross_check_decision`` / ``cross_check_rationale`` /
            # ``cross_check_recommended_severity`` plus the dispatch
            # diagnostic flags ``_dispatch_failure`` / ``_failure_reason``
            # so the working set stays lossless for MAGI without
            # double-bookkeeping (spec sec.2.1 W4). Defensive wiring per
            # the C3 invocation-site tripwire: keeps the contract live
            # even if iter coupling changes downstream.
            findings_for_cross_check = _normalize_findings_for_carry_forward(
                [dict(f) for f in (verdict.findings or ())]
            )
            # v1.0.0 C2 (caspar Loop 2 iter 1 CRITICAL): compute the real
            # cumulative diff so the meta-reviewer can ground its
            # KEEP/DOWNGRADE/REJECT decisions in production code rather
            # than evaluating findings text in isolation. Failure modes
            # (no origin/main, shallow clone, detached HEAD) gracefully
            # degrade to empty string with a stderr breadcrumb -- the
            # cross-check still runs, just with reduced fidelity (spec
            # sec.2.1 W-NEW1).
            #
            # v1.0.0 Loop 2 iter 2->3 W3: thread the (possibly truncated)
            # diff plus its metadata so the audit JSON records whether
            # the cap fired and what the original raw size was. Pre-fix
            # post-mortem readers had no signal that 78% of the patch had
            # been silently dropped.
            cross_check_diff, diff_original_bytes, diff_truncated = _compute_loop2_diff_with_meta(
                root
            )
            annotated_findings = _loop2_cross_check(
                diff=cross_check_diff,
                verdict=verdict.verdict,
                findings=findings_for_cross_check,
                iter_n=iteration,
                config=cfg,
                audit_dir=audit_dir,
                diff_original_bytes=diff_original_bytes,
                diff_truncated=diff_truncated,
            )
            verdict = dataclasses.replace(verdict, findings=tuple(annotated_findings))
        verdict_history.append(verdict)
        # v1.0.0 F44.3 (S1-7): persist retried_agents telemetry to
        # auto-run.json (iff present, i.e. running under auto). Interactive
        # pre-merge skips silently because no audit file exists.
        try:
            _persist_retried_agents_to_audit(root, iteration, verdict)
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"[sbtdd pre-merge] warning: failed to record retried_agents "
                f"for iter {iteration}: {exc}\n"
            )
            sys.stderr.flush()
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(
                f"MAGI STRONG_NO_GO at iter {iteration}",
                verdict=verdict.verdict,
                iteration=iteration,
            )
        if verdict.conditions:
            # v0.4.0 J8.3: tag the finding-remediation dispatch with a
            # ``fix-finding-iter-N`` prefix so the streamed output from
            # ``/receiving-code-review`` is correlated with which Loop 2
            # iteration's MAGI conditions are being processed. The
            # iter-3 redesign moved the per-finding red/green/refactor
            # mini-cycle out of pre_merge_cmd into ``sbtdd close-phase``;
            # this dispatch is the closest surface in pre_merge for the
            # operator-visibility intent of J8.3.
            fix_findings_prefix = f"[sbtdd pre-merge fix-finding-iter-{iteration}]"
            # Loop 1 fix v0.5.0 CRITICAL #1: wrap with heartbeat under auto.
            review_result = _wrap_with_heartbeat_if_auto(
                invoke=lambda: superpowers_dispatch.receiving_code_review(
                    args=_conditions_to_skill_args(verdict.conditions),
                    cwd=str(root),
                    stream_prefix=fix_findings_prefix,
                ),
                iter_num=iteration,
                phase=3,
                dispatch_label=f"receiving-magi-findings-iter{iteration}",
            )
            accepted, rejected = _parse_receiving_review(review_result)
            if not accepted and not rejected:
                raise ValidationError(
                    f"/receiving-code-review produced no decisions for "
                    f"{len(verdict.conditions)} MAGI conditions; cannot proceed"
                )
            last_accepted = tuple(accepted)
            last_rejected = tuple(rejected)
            rejections.extend(f"iter {iteration} rejected: {c}" for c in rejected)
            if accepted:
                # iter-3 redesign: surface to the user via conditions
                # file instead of emitting empty mini-cycle commits.
                conditions_path = _write_magi_conditions_file(accepted, root, verdict, iteration)
                # 2026-04-24: also persist the full MAGI ``consensus.findings``
                # list so the user has the CONCRETE defect detail, not just
                # the agent-level one-liners in magi-conditions.md. MAGI's
                # temp output dir is cleaned up when invoke_magi returns, so
                # without this persistence the detail is lost on exit 8.
                # ``getattr`` fallback keeps the call compatible with
                # verdict-like objects used in tests that do not populate
                # the ``findings`` field (they predate this persistence
                # path). Real ``MAGIVerdict`` always carries findings, so
                # the fallback only fires in test harnesses.
                findings_path = _write_magi_findings_file(
                    getattr(verdict, "findings", ()), root, verdict, iteration
                )
                # Plan D Task 12: user-facing stderr summary so exit 8
                # is self-explanatory without having to read the
                # exception message or the conditions file first.
                findings_hint = (
                    f" Concrete defect detail written to {findings_path}."
                    if findings_path is not None
                    else ""
                )
                sys.stderr.write(
                    f"pre-merge exit 8: accepted={len(accepted)}, "
                    f"rejected={len(rejected)}. Applied conditions not yet "
                    f"in diff. See {conditions_path} and run `sbtdd close-phase` "
                    f"for each, then re-run `sbtdd pre-merge`.{findings_hint}\n"
                )
                raise MAGIGateError(
                    f"MAGI iter {iteration} produced {len(accepted)} accepted "
                    f"condition(s); apply them via `sbtdd close-phase` and "
                    f"re-run `sbtdd pre-merge`. See {conditions_path}.",
                    accepted_conditions=last_accepted,
                    rejected_conditions=last_rejected,
                    verdict=verdict.verdict,
                    iteration=iteration,
                )
            # All conditions rejected: feedback is written next iter;
            # re-invoke MAGI to see if the rationale drops or escalates
            # the verdict (sterile-loop breaker).
            continue
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            return verdict
    # INV-22: callers that have not opted into Feature A (notably ``auto_cmd``
    # which runs headless) pass ``ns=None`` so this branch preserves the
    # v0.1 behavior -- raise :class:`MAGIGateError` directly without ever
    # reaching ``escalation_prompt.prompt_user``. Only ``main`` wires the
    # Feature A flags through ``ns``.
    if ns is None:
        last_verdict = verdict_history[-1] if verdict_history else None
        raise MAGIGateError(
            f"MAGI did not converge to full {threshold}+ after "
            f"{cfg.magi_max_iterations} iterations",
            accepted_conditions=last_accepted,
            rejected_conditions=last_rejected,
            verdict=last_verdict.verdict if last_verdict is not None else None,
            iteration=cfg.magi_max_iterations,
        )
    return _handle_safety_valve_exhaustion(
        root, cfg, verdict_history, last_accepted, last_rejected, ns
    )


def _check_spec_snapshot_drift(
    *,
    spec_path: Path,
    snapshot_path: Path,
    state_file_path: Path,
) -> None:
    """Verify spec scenarios have not drifted since plan approval (CRITICAL #2).

    Per spec sec.3.2 H2-3 + H2-5: pre-merge fails when scenarios drifted
    between plan approval and merge.

    Two distinct drift surfaces guarded:

    - **H2-3** (file present but content drifted): persisted snapshot at
      ``snapshot_path`` no longer matches the current spec; raises
      :class:`MAGIGateError` listing added/removed/modified scenarios.
    - **H2-5** (file deleted bypass): state-file watermark
      (``spec_snapshot_emitted_at``) says a snapshot WAS emitted but the
      file is missing -- bypass-by-deletion attempt detected, raises
      :class:`MAGIGateError`.

    Backward compat: pre-v1.0.0 plan-approval flows neither emitted a
    snapshot nor wrote the watermark; a stderr breadcrumb fires and the
    gate proceeds.

    Per caspar Loop 2 iter 4 CRITICAL fix: reuses the existing
    :class:`MAGIGateError` (no new exception class added by v1.0.0).

    Args:
        spec_path: Path to ``sbtdd/spec-behavior.md``.
        snapshot_path: Path to ``planning/spec-snapshot.json`` (the
            previously persisted snapshot).
        state_file_path: Path to ``.claude/session-state.json`` (read
            for the H2-5 watermark check).

    Raises:
        MAGIGateError: scenarios drifted (H2-3) or bypass-by-deletion
            detected via watermark (H2-5).
    """
    # Read state-file watermark (caspar iter 4 W2): canon-of-the-present
    # record of whether a snapshot was emitted.
    watermark: str | None = None
    if state_file_path.exists():
        try:
            state = json.loads(state_file_path.read_text(encoding="utf-8"))
            watermark = state.get("spec_snapshot_emitted_at")
        except json.JSONDecodeError:
            sys.stderr.write(
                f"[sbtdd pre-merge] state file corrupt at "
                f"{state_file_path}; spec-snapshot watermark check "
                f"skipped (drift gate degrades to file-only check).\n"
            )

    if not snapshot_path.exists():
        if watermark:
            # H2-5: watermark says snapshot WAS emitted, but file is gone.
            raise MAGIGateError(
                f"Spec snapshot file deleted; re-emit via /sbtdd "
                f"close-task or re-approve plan. State file watermark "
                f"shows snapshot was emitted at {watermark} but "
                f"{snapshot_path} no longer exists. The drift gate "
                f"cannot be bypassed by deleting the snapshot."
            )
        # H2-3 backward-compat path: pre-v1.0.0 plan approval (no file,
        # no watermark) is non-blocking with a breadcrumb.
        sys.stderr.write(
            f"[sbtdd pre-merge] no spec-snapshot.json at {snapshot_path}; "
            f"drift check skipped (pre-v1.0.0 plan-approval flow). "
            f"Re-approve plan to enable drift detection.\n"
        )
        sys.stderr.flush()
        return

    # Deferred import: spec_snapshot is owned by Subagent #2; deferring
    # the import follows the cross-subagent Mitigation A pattern.
    import spec_snapshot

    prev = spec_snapshot.load_snapshot(snapshot_path)
    curr = spec_snapshot.emit_snapshot(spec_path)
    diff = spec_snapshot.compare(prev, curr)
    if diff["added"] or diff["removed"] or diff["modified"]:
        raise MAGIGateError(
            f"Spec scenarios changed since plan approval; re-approve plan "
            f"via /writing-plans + Checkpoint 2.\n"
            f"  added: {diff['added']}\n"
            f"  removed: {diff['removed']}\n"
            f"  modified: {diff['modified']}"
        )


def _persist_retried_agents_to_audit(
    root: Path,
    iteration: int,
    verdict: magi_dispatch.MAGIVerdict,
) -> None:
    """F44.3 hook: persist verdict.retried_agents to auto-run.json if present.

    Called from :func:`_loop2` after each MAGI iteration. Skips silently
    when the audit file does not exist (interactive pre-merge mode runs
    standalone and has no audit trail).

    Tests monkeypatch this function to verify the wiring fires.

    Args:
        root: Project root directory.
        iteration: 1-based MAGI Loop 2 iteration index.
        verdict: :class:`magi_dispatch.MAGIVerdict` whose ``retried_agents``
            tuple is propagated.
    """
    auto_run_path = root / ".claude" / "auto-run.json"
    if not auto_run_path.exists():
        return
    # Defer the import: ``auto_cmd`` may also import ``pre_merge_cmd``,
    # so a top-level circular ``import auto_cmd`` would break in some
    # test orderings. The deferred import follows the same pattern as
    # ``_wrap_with_heartbeat_if_auto`` above.
    import auto_cmd as _auto

    _auto._record_magi_retried_agents(
        auto_run_path,
        iter_n=iteration,
        retried_agents=list(getattr(verdict, "retried_agents", ())),
    )


#: Annotation/diagnostic fields stripped from MAGI findings before re-emitting
#: them as ``findings`` in the next MAGI iter payload (caspar Loop 2 iter 4 W4).
#: The "Prior triage context" block (separate from ``findings``) is the
#: canonical record of cross-check + INV-29 decisions; the working ``findings``
#: set MUST be normalized back to the un-annotated form so annotations don't
#: accumulate unbounded across iters.
_CROSS_CHECK_ANNOTATION_FIELDS: tuple[str, ...] = (
    "cross_check_decision",
    "cross_check_rationale",
    "cross_check_recommended_severity",
    "_dispatch_failure",
    "_failure_reason",
)


def _normalize_findings_for_carry_forward(
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Strip cross-check annotation fields before re-emitting to next MAGI iter.

    Per caspar Loop 2 iter 4 W4 fix: annotation fields
    (``cross_check_decision``, ``cross_check_rationale``,
    ``cross_check_recommended_severity``) and dispatch diagnostic flags
    (``_dispatch_failure``, ``_failure_reason``) accumulate unbounded
    across MAGI iters if not stripped. The "Prior triage context" block
    (separate from ``findings``) is the canonical record; the working
    ``findings`` set MUST be normalized back to the un-annotated form
    for the next iter.

    Args:
        findings: Annotated findings list (from a prior cross-check pass).

    Returns:
        New list of finding dicts with annotation fields removed; original
        agent/severity/title/detail fields preserved.
    """
    return [
        {k: v for k, v in f.items() if k not in _CROSS_CHECK_ANNOTATION_FIELDS} for f in findings
    ]


#: Maximum diff size threaded into the cross-check prompt before truncation.
#: v0.5.0 W-NEW1 introduced a 200KB cap; v1.0.0 Loop 2 iter 2->3 R11/W3
#: empirical sweep observed cumulative v1.0.0 diffs at ~918KB, so the cap
#: was raised to 1MB to keep realistic plan-bundle diffs untruncated. MAGI
#: agents + the meta-reviewer still have finite context budgets, so the
#: hard ceiling stays in place; truncation metadata is now surfaced in
#: the cross-check audit JSON for post-mortem visibility (spec sec.2.1 W3).
_CROSS_CHECK_DIFF_MAX_BYTES: int = 1024 * 1024

#: Marker appended to truncated diffs so the meta-reviewer knows the diff
#: is partial and adjusts its evaluation accordingly.
_CROSS_CHECK_DIFF_TRUNCATION_MARKER: str = "\n[... truncated for prompt budget ...]\n"


def _compute_loop2_diff(root: Path, base_ref: str = "origin/main") -> str:
    """Compute the cumulative diff threaded into the cross-check meta-review.

    Per spec sec.2.1 W-NEW1 (Loop 2 iter 1 caspar CRITICAL fix): the
    meta-reviewer evaluates MAGI findings against the cumulative diff
    under review, NOT the empty placeholder used during initial Feature G
    plumbing. Without a real diff, the recursive payoff of the cross-check
    is invalidated -- the reviewer has no production code to ground its
    KEEP/DOWNGRADE/REJECT decisions in.

    Resolution chain (defensive against detached HEAD / shallow clone):

    1. ``git diff <base_ref>..HEAD`` (default ``origin/main``).
    2. ``git diff main..HEAD`` (when ``origin/main`` is missing).
    3. ``git diff $(git merge-base HEAD~50 HEAD)..HEAD`` (last-resort
       walking history; bounded by 50 commits to stay fast).

    On any subprocess failure the helper returns the empty string and
    emits a stderr breadcrumb so the operator sees that the cross-check
    meta-reviewer is falling back to findings-text-only evaluation.

    Output is capped at :data:`_CROSS_CHECK_DIFF_MAX_BYTES` (1MB as of
    v1.0.0; raised from the v0.5.0 200KB ceiling per the W3 sweep) and
    truncated with :data:`_CROSS_CHECK_DIFF_TRUNCATION_MARKER` when the
    raw diff exceeds the budget. Truncation metadata is exposed via
    :func:`_compute_loop2_diff_with_meta` for audit-trail consumers.

    Args:
        root: Project root directory (used as ``cwd`` for git invocations).
        base_ref: Initial git ref to diff against. Defaults to
            ``origin/main`` per the SBTDD plan-branch convention.

    Returns:
        Cumulative diff text, or ``""`` on any subprocess / fallback
        failure (graceful degradation -- never raises).
    """
    diff, _, _ = _compute_loop2_diff_with_meta(root, base_ref=base_ref)
    return diff


def _compute_loop2_diff_with_meta(
    root: Path, base_ref: str = "origin/main"
) -> tuple[str, int, bool]:
    """Compute the cumulative cross-check diff plus truncation metadata.

    Companion to :func:`_compute_loop2_diff` that surfaces the
    pre-truncation byte count + a truncation flag so callers (the
    cross-check audit writer) can record the metadata in the audit JSON.
    The truncated diff itself is identical to what :func:`_compute_loop2_diff`
    returns -- single source of truth for the truncation decision.

    Args:
        root: Project root directory.
        base_ref: Initial git ref to diff against (default ``origin/main``).

    Returns:
        Tuple ``(diff, original_bytes, truncated)`` where ``diff`` is the
        possibly-truncated text, ``original_bytes`` is the pre-truncation
        size (``len(diff)`` when no truncation occurred), and
        ``truncated`` indicates whether the cap was applied.
    """
    raw = _compute_loop2_diff_raw(root, base_ref=base_ref)
    original_bytes = len(raw)
    if original_bytes > _CROSS_CHECK_DIFF_MAX_BYTES:
        truncated = True
        diff = raw[:_CROSS_CHECK_DIFF_MAX_BYTES] + _CROSS_CHECK_DIFF_TRUNCATION_MARKER
    else:
        truncated = False
        diff = raw
    return diff, original_bytes, truncated


def _compute_loop2_diff_raw(root: Path, base_ref: str = "origin/main") -> str:
    """Internal helper that returns the *un-truncated* cumulative diff.

    Shared by :func:`_compute_loop2_diff` and
    :func:`_compute_loop2_diff_with_meta` so the resolution chain
    (``origin/main`` -> ``main`` -> merge-base fallback) is owned in one
    place. The public truncation logic lives in the two callers.
    """

    def _try(cmd: list[str]) -> str | None:
        try:
            r = subprocess_utils.run_with_timeout(cmd, timeout=30, cwd=str(root))
        except Exception as exc:  # noqa: BLE001 - graceful fallback per W-NEW1
            sys.stderr.write(
                f"[sbtdd magi-cross-check] failed to compute diff "
                f"({' '.join(cmd)}): {exc}; meta-reviewer falls back to "
                f"findings text only\n"
            )
            sys.stderr.flush()
            return ""
        if r.returncode != 0:
            return None
        return str(r.stdout)

    diff = _try(["git", "diff", f"{base_ref}..HEAD"])
    if diff is None:
        diff = _try(["git", "diff", "main..HEAD"])
    if diff is None:
        try:
            r = subprocess_utils.run_with_timeout(
                ["git", "merge-base", "HEAD~50", "HEAD"], timeout=10, cwd=str(root)
            )
            if r.returncode == 0 and r.stdout.strip():
                diff = _try(["git", "diff", f"{r.stdout.strip()}..HEAD"]) or ""
            else:
                diff = ""
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(
                f"[sbtdd magi-cross-check] failed to compute diff "
                f"(merge-base fallback): {exc}; meta-reviewer falls back to "
                f"findings text only\n"
            )
            sys.stderr.flush()
            diff = ""
    if diff is None:
        diff = ""
    return diff


def _build_cross_check_prompt(
    diff: str,
    verdict: str,
    findings: list[dict[str, Any]],
) -> str:
    """Build the meta-review prompt for ``/requesting-code-review``.

    The prompt asks the reviewer to evaluate each MAGI finding for
    technical soundness given the spec + plan + diff context. Output
    format: structured JSON with one decision per finding.

    Per spec sec.2.1 W-NEW1 (caspar Loop 2 iter 1 CRITICAL fix): when
    ``diff`` is non-empty, the prompt embeds it under a
    ``## Cumulative diff under review (truncated to 200KB)`` section so
    the reviewer can ground decisions in the actual production code,
    not just finding-text-only heuristics. Empty diff (subprocess
    fallback) omits the section so the reviewer doesn't waste budget
    on a stub.

    Args:
        diff: Cumulative diff under MAGI Loop 2 review.
        verdict: MAGI consensus verdict string (e.g. ``"GO_WITH_CAVEATS"``).
        findings: List of MAGI finding dicts.

    Returns:
        Prompt string suitable for ``superpowers_dispatch.invoke_requesting_code_review``.
    """
    findings_text = "\n".join(
        f"- [{f.get('severity', '?')}] ({f.get('agent', '?')}): "
        f"{f.get('title', '')}: {f.get('detail', '')}"
        for f in findings
    )
    diff_section = ""
    if diff:
        diff_section = (
            f"\n\n## Cumulative diff under review (truncated to 200KB)\n\n```diff\n{diff}\n```\n"
        )
    return (
        f"Evaluate if the following MAGI Loop 2 findings are technically "
        f"sound or false positives given the spec + plan + diff context.\n\n"
        f"MAGI verdict: {verdict}\n"
        f"MAGI findings:\n{findings_text}\n\n"
        f"For each finding output JSON: "
        f'{{"decisions": [{{"original_index": N, '
        f'"decision": "KEEP"|"DOWNGRADE"|"REJECT", '
        f'"rationale": "...", '
        f'"recommended_severity": "WARNING"|"INFO"|null}}, ...]}}'
        f"{diff_section}"
    )


def _dispatch_requesting_code_review(
    *,
    diff: str,
    prompt: str,
    cwd: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Dispatch ``/requesting-code-review`` skill with cross-check meta-prompt.

    Parses the skill's stdout as JSON. Returns decisions dict per
    :func:`_build_cross_check_prompt` contract. Tests monkeypatch this
    function (or the underlying ``superpowers_dispatch.requesting_code_review``)
    to inject canned review decisions.

    Per melchior Loop 2 iter 3 WARNING fix: distinguish JSON-parse-failure
    from full-dispatch-failure for audit visibility. Two distinct failure
    modes surface separately:

    - dispatch itself fails (subprocess error / timeout) -> caller in
      :func:`_loop2_cross_check` catches the exception and writes
      ``cross_check_failed: true`` to the audit artifact with reason.
    - dispatch succeeds but output is malformed JSON -> we return an
      empty-decisions dict with the diagnostic flag
      ``_dispatch_failure: "json_parse_error"`` and ``_failure_reason``
      explaining the parse error. Audit writer surfaces this as a
      separate ``dispatch_failure`` field (NOT under ``cross_check_failed``).

    Either failure mode degrades to "no findings filtered" (original
    MAGI findings flow through to INV-29 routing unchanged), but
    operators have the audit signal to investigate.

    Args:
        diff: Cumulative diff context (forwarded for callers that wire
            it through ``args``; current minimal impl passes only the
            prompt as a positional arg).
        prompt: Meta-review prompt built by :func:`_build_cross_check_prompt`.
        cwd: Working directory for the skill invocation (typically
            project root).
        **kwargs: Forwarded to the wrapper.

    Returns:
        Dict with ``decisions`` key (list of per-finding decision dicts).
        On JSON parse failure, additionally carries ``_dispatch_failure``
        and ``_failure_reason`` markers.
    """
    result = superpowers_dispatch.requesting_code_review(
        args=[prompt],
        cwd=cwd,
    )
    output_text = getattr(result, "stdout", "") or "{}"
    try:
        parsed: dict[str, Any] = json.loads(output_text)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            f"[sbtdd magi-cross-check] /requesting-code-review returned "
            f"malformed JSON (meta-review skipped, findings unchanged): "
            f"{exc}\n"
        )
        sys.stderr.flush()
        return {
            "decisions": [],
            "_dispatch_failure": "json_parse_error",
            "_failure_reason": str(exc),
        }
    parsed.setdefault("decisions", [])
    return parsed


def _apply_cross_check_decisions(
    findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Annotate findings with cross-check decisions; never remove (CRITICAL #1+#4).

    Per spec sec.2.1 redesign: cross-check is annotation-only. The returned
    list has the SAME LENGTH as ``findings``. INV-29 (operator +
    ``/receiving-code-review``) is the only stage that may filter findings.

    Each annotated finding gains the following fields:
    - ``cross_check_decision`` (KEEP | DOWNGRADE | REJECT)
    - ``cross_check_rationale`` (review text)
    - ``cross_check_recommended_severity`` (only set when DOWNGRADE; the
      original ``severity`` field is preserved unchanged; KEEP/REJECT
      surface ``None``).

    Args:
        findings: Original MAGI finding dicts.
        decisions: Per-finding decision dicts with ``original_index`` and
            ``decision`` keys (rationale + recommended_severity optional).

    Returns:
        Length-preserved list of annotated finding dicts.
    """
    decision_by_index = {d["original_index"]: d for d in decisions}
    severity_downgrade = {"CRITICAL": "WARNING", "WARNING": "INFO"}
    annotated: list[dict[str, Any]] = []
    for idx, finding in enumerate(findings):
        decision = decision_by_index.get(idx, {"decision": "KEEP"})
        action = decision.get("decision", "KEEP")
        rationale = decision.get("rationale", "")
        recommended_severity: str | None = None
        if action == "DOWNGRADE":
            recommended_severity = decision.get(
                "recommended_severity",
                severity_downgrade.get(finding.get("severity", ""), "INFO"),
            )
        annotated.append(
            {
                **finding,
                "cross_check_decision": action,
                "cross_check_rationale": rationale,
                "cross_check_recommended_severity": recommended_severity,
            }
        )
    return annotated


def _write_cross_check_audit(
    audit_dir: Path,
    *,
    iter_n: int,
    verdict: str,
    original_findings: list[dict[str, Any]],
    decisions: list[dict[str, Any]] | None = None,
    annotated_findings: list[dict[str, Any]] | None = None,
    cross_check_failed: bool = False,
    failure_reason: str | None = None,
    json_parse_failure: str | None = None,
    diff_truncated: bool = False,
    diff_original_bytes: int | None = None,
    diff_cap_bytes: int | None = None,
) -> Path:
    """Write cross-check audit artifact JSON atomically (spec sec.2.1 G6 schema).

    Atomic write: serialize to ``<path>.tmp.<pid>.<tid>``, then ``Path.replace``
    to final name. Prevents partial-write corruption if process crashes
    mid-write (per WARNING melchior — atomicization).

    Per melchior W iter 3: ``cross_check_failed`` is reserved for full-
    dispatch failures (subprocess error / unhandled exception);
    ``json_parse_failure`` surfaces as a separate ``dispatch_failure`` block
    so post-mortem can distinguish the two modes.

    Args:
        audit_dir: Directory for cross-check audit artifacts (created if absent).
        iter_n: Current MAGI Loop 2 iteration number.
        verdict: MAGI consensus verdict string.
        original_findings: Verbatim MAGI findings (always preserved).
        decisions: Per-finding cross-check decisions (None when skipped/failed).
        annotated_findings: Annotated findings (defaults to original_findings).
        cross_check_failed: True when the dispatch itself raised.
        failure_reason: Free-form failure description (only when ``cross_check_failed``).
        json_parse_failure: Reason string from JSON parse failure mode.

    Returns:
        Path to the written audit artifact.
    """
    import os
    import threading

    audit_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    audit_path = audit_dir / f"iter{iter_n}-{timestamp}.json"
    audit_data: dict[str, Any] = {
        "iter": iter_n,
        "timestamp": timestamp,
        "magi_verdict": verdict,
        "original_findings": original_findings,
        "cross_check_decisions": decisions or [],
        "annotated_findings": (
            annotated_findings if annotated_findings is not None else original_findings
        ),
    }
    if cross_check_failed:
        audit_data["cross_check_failed"] = True
        if failure_reason:
            audit_data["failure_reason"] = failure_reason
    if json_parse_failure is not None:
        audit_data["dispatch_failure"] = {
            "kind": "json_parse_error",
            "reason": json_parse_failure,
        }
    # v1.0.0 Loop 2 iter 2->3 W3: surface diff-truncation metadata so
    # post-mortem readers can tell whether the meta-reviewer evaluated
    # the full patch or a truncated subset. Pre-fix the audit JSON had
    # no signal for the W3 sweep finding (78% silent loss).
    if diff_truncated:
        audit_data["diff_truncated"] = True
        if diff_original_bytes is not None:
            audit_data["diff_original_bytes"] = diff_original_bytes
        if diff_cap_bytes is not None:
            audit_data["diff_cap_bytes"] = diff_cap_bytes
    tmp_path = audit_path.parent / (audit_path.name + f".tmp.{os.getpid()}.{threading.get_ident()}")
    tmp_path.write_text(json.dumps(audit_data, indent=2, default=str), encoding="utf-8")
    tmp_path.replace(audit_path)  # atomic rename
    return audit_path


def _loop2_cross_check(
    *,
    diff: str,
    verdict: str,
    findings: list[dict[str, Any]],
    iter_n: int,
    config: Any,
    audit_dir: Path,
    diff_original_bytes: int | None = None,
    diff_truncated: bool = False,
) -> list[dict[str, Any]]:
    """Cross-check MAGI Loop 2 findings via /requesting-code-review meta-review.

    Per spec sec.2.1 Feature G + INV-35: annotate MAGI findings with
    KEEP/DOWNGRADE/REJECT decisions BEFORE routing to INV-29 triage. Opt-
    out via ``config.magi_cross_check=False`` (default).

    Annotation-only redesign (CRITICAL #1+#4): the returned list has the
    SAME LENGTH as ``findings``; each surfaced finding is augmented with
    ``cross_check_decision``, ``cross_check_rationale``, and
    ``cross_check_recommended_severity`` fields. INV-29 (operator +
    ``/receiving-code-review``) is the only stage that may filter
    findings — silent drops here would hide real CRITICALs when the
    review is wrong.

    G4 stderr breadcrumb (spec sec.2.1 impl note): when opted out, emit
    a one-time stderr breadcrumb at Loop 2 entry so operators see the
    cross-check is OFF rather than silently inactive.

    Args:
        diff: Full diff under review (string).
        verdict: MAGI consensus verdict (e.g. ``"GO_WITH_CAVEATS"``).
        findings: List of MAGI findings dicts.
        iter_n: Current MAGI Loop 2 iteration number.
        config: PluginConfig (or duck-typed) with ``magi_cross_check`` field.
        audit_dir: Directory for cross-check audit artifacts.

    Returns:
        Annotated findings list (same length as input). On dispatch failure,
        returns the original findings unchanged (graceful fallback per G5).
    """
    if not config.magi_cross_check:
        return findings
    prompt = _build_cross_check_prompt(diff, verdict, findings)
    # v1.0.0 W3: forward the diff-truncation metadata to every audit-
    # write call site below so post-mortem readers can distinguish
    # full-diff evaluations from truncated-diff evaluations.
    audit_diff_meta: dict[str, Any] = {
        "diff_truncated": diff_truncated,
        "diff_original_bytes": diff_original_bytes,
        "diff_cap_bytes": _CROSS_CHECK_DIFF_MAX_BYTES if diff_truncated else None,
    }
    try:
        review_output = _dispatch_requesting_code_review(diff=diff, prompt=prompt)
    except Exception as exc:  # noqa: BLE001 - graceful fallback per G5
        sys.stderr.write(
            f"[sbtdd magi-cross-check] failed (will fall back to MAGI findings as-is): {exc}\n"
        )
        sys.stderr.flush()
        _write_cross_check_audit(
            audit_dir,
            iter_n=iter_n,
            verdict=verdict,
            original_findings=findings,
            cross_check_failed=True,
            failure_reason=str(exc),
            **audit_diff_meta,
        )
        return findings

    # Per melchior W iter 3: surface JSON-parse-failure as a distinct audit
    # field, separate from cross_check_failed (full-dispatch-fail).
    if review_output.get("_dispatch_failure") == "json_parse_error":
        _write_cross_check_audit(
            audit_dir,
            iter_n=iter_n,
            verdict=verdict,
            original_findings=findings,
            decisions=[],
            annotated_findings=findings,
            json_parse_failure=str(review_output.get("_failure_reason", "")),
            **audit_diff_meta,
        )
        return findings  # original findings unchanged

    decisions = review_output.get("decisions", [])
    annotated = _apply_cross_check_decisions(findings, decisions)
    _write_cross_check_audit(
        audit_dir,
        iter_n=iter_n,
        verdict=verdict,
        original_findings=findings,
        decisions=decisions,
        annotated_findings=annotated,
        **audit_diff_meta,
    )
    return annotated


#: One-time dedup flag for the G4 cross-check-disabled stderr breadcrumb.
#: Reset at process start; not per-Loop-2-invocation so a single auto run
#: emits the breadcrumb at most once even across multiple pre-merge calls.
_cross_check_disabled_breadcrumb_emitted: bool = False


def _reset_cross_check_breadcrumb_for_tests() -> None:
    """Test-only helper; resets the G4 dedup flag."""
    global _cross_check_disabled_breadcrumb_emitted
    _cross_check_disabled_breadcrumb_emitted = False


def _emit_cross_check_disabled_breadcrumb_once(config: Any) -> None:
    """Emit one-time stderr breadcrumb when cross-check is opted-out (G4 impl note).

    Per spec sec.2.1 Feature G impl note: when ``config.magi_cross_check``
    is False, emit a single stderr breadcrumb at Loop 2 entry so operators
    see cross-check is OFF rather than silently inactive. Once per Loop 2
    invocation, not per iter (dedup).

    Args:
        config: PluginConfig (or duck-typed) with ``magi_cross_check`` field.
            Pre-v1.0.0 duck-typed shadow configs (e.g. ``SimpleNamespace``)
            without the field are treated as opted-out (default False).
    """
    global _cross_check_disabled_breadcrumb_emitted
    if getattr(config, "magi_cross_check", False):
        return
    if _cross_check_disabled_breadcrumb_emitted:
        return
    _cross_check_disabled_breadcrumb_emitted = True
    sys.stderr.write(
        "[sbtdd magi-cross-check] cross-check is OFF (magi_cross_check: "
        "false in plugin.local.md). To enable meta-reviewer for this "
        "gate, set magi_cross_check: true and re-run.\n"
    )
    sys.stderr.flush()


def _invoke_magi_loop2(**kwargs: Any) -> tuple[str, list[dict[str, Any]]]:
    """Adapter shim around ``magi_dispatch.invoke_magi`` returning (verdict, findings).

    Exists primarily so :func:`_loop2_with_cross_check` can be unit-tested
    in isolation (tests monkeypatch this function). Production callers
    that already use :func:`_loop2` continue to drive
    ``magi_dispatch.invoke_magi`` directly with the full :class:`MAGIVerdict`
    return type.

    Args:
        **kwargs: Forwarded verbatim to :func:`magi_dispatch.invoke_magi`.

    Returns:
        Tuple ``(verdict_string, findings_list)`` extracted from the
        :class:`MAGIVerdict`.
    """
    verdict_obj = magi_dispatch.invoke_magi(**kwargs)
    findings_list = [dict(f) for f in getattr(verdict_obj, "findings", ())]
    return (verdict_obj.verdict, findings_list)


def _loop2_with_cross_check(
    *,
    diff: str,
    iter_n: int,
    config: Any,
    audit_dir: Path,
    **magi_kwargs: Any,
) -> tuple[str, list[dict[str, Any]]]:
    """Wrapper around MAGI Loop 2 dispatch + cross-check sub-phase.

    Per spec sec.2.1 + INV-35: cross-check ANNOTATES findings BEFORE
    INV-29 routes them to ``/receiving-code-review``. Verdict itself is
    unchanged (cross-check only modifies the findings set, never the
    verdict string).

    Per CRITICAL #1+#4 redesign: annotation-only — the returned findings
    list has the same length as MAGI's emitted findings; INV-29 is the
    only stage that may filter.

    Args:
        diff: Cumulative diff under review.
        iter_n: Current MAGI Loop 2 iteration number.
        config: PluginConfig (or duck-typed) with ``magi_cross_check`` field.
        audit_dir: Directory for cross-check audit artifacts.
        **magi_kwargs: Forwarded to :func:`_invoke_magi_loop2`.

    Returns:
        Tuple ``(verdict_string, annotated_findings_list)``.
    """
    _emit_cross_check_disabled_breadcrumb_once(config)
    verdict, findings = _invoke_magi_loop2(**magi_kwargs)
    annotated = _loop2_cross_check(
        diff=diff,
        verdict=verdict,
        findings=findings,
        iter_n=iter_n,
        config=config,
        audit_dir=audit_dir,
    )
    return verdict, annotated


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd pre-merge (Loop 1 + Loop 2, sec.S.5.6)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    _preflight(root)
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    # v1.0.0 C2 wiring (O-2 Loop 1 review CRITICAL #2): spec-snapshot drift
    # gate at pre-merge entry per spec sec.3.2 H2-3 + H2-5. Raises
    # MAGIGateError BEFORE Loop 1 / Loop 2 if scenarios drifted since plan
    # approval, or if the snapshot file was deleted while the watermark in
    # session-state.json says it WAS emitted (bypass-by-deletion guard).
    _check_spec_snapshot_drift(
        spec_path=root / "sbtdd" / "spec-behavior.md",
        snapshot_path=root / "planning" / "spec-snapshot.json",
        state_file_path=root / ".claude" / "session-state.json",
    )
    _loop1(root)
    verdict = _loop2(root, cfg, ns.magi_threshold, ns)
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return 0


run = main
