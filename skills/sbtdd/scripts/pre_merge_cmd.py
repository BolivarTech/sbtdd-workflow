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
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import escalation_prompt
import magi_dispatch
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

#: Safety valve for Loop 1 (sec.S.5.6, INV-11). Exceeding aborts with exit 7.
_LOOP1_MAX: int = 10

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
    for _ in range(1, _LOOP1_MAX + 1):
        result = superpowers_dispatch.requesting_code_review(cwd=str(root))
        if _is_clean_to_go(result):
            return
        superpowers_dispatch.receiving_code_review(cwd=str(root))
    raise Loop1DivergentError(f"Loop 1 did not converge in {_LOOP1_MAX} iterations")


#: Regex matching ``## Accepted`` / ``## Rejected`` section headers.
#:
#: MAGI Loop 2 iter 1 Finding 7: the prior ``.startswith("## accepted")``
#: check required a literal single space and broke on ``##Accepted`` /
#: ``##  Accepted``. The regex accepts zero-or-more whitespace after the
#: hashes and is case-insensitive, covering every emitted form of the
#: superpowers skill header (hyphenated, spaced, upper-case, mixed).
_SECTION_HEADER_RE: re.Pattern[str] = re.compile(
    r"^##\s*(Accepted|Rejected)\b",
    re.IGNORECASE,
)


def _parse_receiving_review(
    skill_result: superpowers_dispatch.SkillResult,
) -> tuple[list[str], list[str]]:
    """Parse /receiving-code-review stdout into (accepted, rejected) lists.

    Expected stdout format (markdown bullet lists under two headers)::

        ## Accepted
        - condition text 1
        - condition text 2

        ## Rejected
        - condition text 3 (rationale: ...)

    Heading recognition (MAGI Loop 2 iter 1 Finding 7): the parser uses
    :data:`_SECTION_HEADER_RE` to accept every observed spelling of the
    section header -- ``##Accepted`` (no space), ``## Accepted``
    (canonical), ``##   Accepted`` (multi-space), ``## ACCEPTED``
    (upper-case), ``## aCCepteD`` (mixed case). All forms are mapped
    onto the ``accepted`` / ``rejected`` section buckets regardless of
    capitalisation.

    Returns ``([accepted_texts], [rejected_texts])`` with leading bullet /
    dash / whitespace stripped. Either section may be absent (empty list).
    A completely empty stdout returns ``([], [])`` -- the caller (``_loop2``)
    treats this as "no decisions produced, re-raise" via a dedicated
    :class:`errors.ValidationError` path.
    """
    accepted: list[str] = []
    rejected: list[str] = []
    # Map canonical section name (lower-cased header group) -> target
    # list. Using a dict instead of an if-chain keeps the dispatch
    # declarative and makes the set of recognised sections explicit.
    dispatch: dict[str, list[str]] = {"accepted": accepted, "rejected": rejected}
    section: list[str] | None = None
    stdout = getattr(skill_result, "stdout", "") or ""
    for line in stdout.splitlines():
        s = line.strip()
        match = _SECTION_HEADER_RE.match(s)
        if match is not None:
            section = dispatch[match.group(1).lower()]
            continue
        if section is not None and s.startswith(("-", "*")):
            section.append(s.lstrip("-* ").strip())
    return accepted, rejected


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


#: Instruction prepended to every /receiving-code-review dispatch. The
#: superpowers skill is prose-only -- it teaches how to RESPOND to
#: feedback but does not define a machine-parseable output format. Without
#: this instruction the subagent produces free-form analysis that
#: :func:`_parse_receiving_review` cannot extract decisions from,
#: triggering ``ValidationError: /receiving-code-review produced no
#: decisions``. Observed v0.2 pre-merge Loop 2 2026-04-24. The instruction
#: gives the subagent an explicit contract while still allowing the
#: skill's technical-evaluation discipline (the forbidden-responses
#: rules in the skill prevent lazy blanket-accept output).
_RECEIVING_REVIEW_FORMAT_CONTRACT = (
    "After technical evaluation of the MAGI findings below, your reply "
    "MUST end with EXACTLY these two markdown sections (and nothing "
    "else after them): ``## Accepted`` followed by ``- <verbatim "
    "finding text>`` lines for findings you accept, and "
    "``## Rejected`` followed by ``- <verbatim finding text> "
    "(rationale: ...)`` lines for findings you reject. Every finding "
    "MUST appear under exactly one section. Findings to evaluate:"
)


def _conditions_to_skill_args(conditions: tuple[str, ...]) -> list[str]:
    """Serialise MAGI conditions as CLI args for /receiving-code-review.

    The skill accepts findings as positional arguments embedded in the
    ``claude -p`` prompt. A leading instruction (see
    :data:`_RECEIVING_REVIEW_FORMAT_CONTRACT`) forces the subagent to
    emit output in the ``## Accepted`` / ``## Rejected`` markdown shape
    that :func:`_parse_receiving_review` parses -- the skill itself is
    prose-only and would otherwise return free-form analysis the parser
    cannot extract decisions from.
    """
    quoted = [f'"{c}"' for c in conditions]
    return [_RECEIVING_REVIEW_FORMAT_CONTRACT, *quoted]


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
    rejections: list[str] = []
    last_accepted: tuple[str, ...] = ()
    last_rejected: tuple[str, ...] = ()
    verdict_history: list[magi_dispatch.MAGIVerdict] = []
    for iteration in range(1, cfg.magi_max_iterations + 1):
        iter_paths = list(diff_paths)
        if rejections:
            iter_paths.append(str(_write_magi_feedback_file(root, rejections)))
        verdict = magi_dispatch.invoke_magi(context_paths=iter_paths, cwd=str(root))
        verdict_history.append(verdict)
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(
                f"MAGI STRONG_NO_GO at iter {iteration}",
                verdict=verdict.verdict,
                iteration=iteration,
            )
        if verdict.conditions:
            review_result = superpowers_dispatch.receiving_code_review(
                args=_conditions_to_skill_args(verdict.conditions),
                cwd=str(root),
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


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd pre-merge (Loop 1 + Loop 2, sec.S.5.6)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    _preflight(root)
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _loop1(root)
    verdict = _loop2(root, cfg, ns.magi_threshold, ns)
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return 0


run = main
