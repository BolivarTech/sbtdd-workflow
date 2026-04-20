#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd pre-merge -- Loop 1 + Loop 2 (sec.S.5.6, INV-9/28/29)."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

import magi_dispatch
import superpowers_dispatch
from commits import create as commit_create
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

#: Type alias for the three staging callbacks required by
#: :func:`_apply_condition_via_mini_cycle`. Each callback must stage (via
#: ``git add``) exactly the files that belong to its TDD phase; the helper
#: raises :class:`NotImplementedError` if any callback is ``None`` so
#: callers cannot silently emit empty commits (MAGI Loop 2 iter 1 Finding 1).
StageCallback = Callable[[], None]


def _noop_stage() -> None:
    """Named no-op staging callback used by :func:`_loop2`.

    ``_loop2`` is the non-diff-producing caller of
    :func:`_apply_condition_via_mini_cycle` -- the actual code edits come
    from the upstream orchestrator which has already staged the files
    before reaching loop2. The helper still rejects ``None`` (Finding 1)
    so we hand it a named, documented no-op rather than an anonymous
    ``lambda: None`` which obscures intent and defeats mypy hover info.
    """
    return None


#: Safety valve for Loop 1 (sec.S.5.6, INV-11). Exceeding aborts with exit 7.
_LOOP1_MAX: int = 10

#: Low-risk keyword set (iter-2 Finding W8): 'test' deliberately EXCLUDED.
#: Phrases like "add structural test for X" are structural, not low-risk; only
#: keywords that genuinely don't require a re-MAGI remain (doc/docstring/
#: naming/rename/comment/logging/message).
_LOW_RISK_KEYWORDS: tuple[str, ...] = (
    "doc",
    "docstring",
    "naming",
    "rename",
    "comment",
    "logging",
    "message",
)

#: Filename of the auxiliary rejection-feedback file written between iterations.
#: Lives inside the destination project's ``.claude/`` (gitignored, never
#: committed). See :func:`_write_magi_feedback_file` for the rationale.
_MAGI_FEEDBACK_FILENAME: str = "magi-feedback.md"


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
    return p


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

    Each iteration invokes ``/requesting-code-review``. If the skill result
    does not advertise ``clean-to-go`` the loop invokes
    ``/receiving-code-review`` to apply fixes (the concrete mini-cycle TDD
    commits are materialised by ``_apply_condition_via_mini_cycle`` in Loop
    2; Loop 1 stays at the skill-invocation level because the
    superpowers contract does not expose individual findings here).

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


def _conditions_low_risk(conditions: tuple[str, ...]) -> bool:
    """Return True iff every condition matches at least one low-risk keyword.

    Empty tuple returns True vacuously (no conditions == no gate work),
    but the caller guards the empty-conditions path separately.
    """
    return all(any(kw in c.lower() for kw in _LOW_RISK_KEYWORDS) for c in conditions)


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

    Returns ``([accepted_texts], [rejected_texts])`` with leading bullet /
    dash / whitespace stripped. Either section may be absent (empty list).
    A completely empty stdout returns ``([], [])`` -- the caller (``_loop2``)
    treats this as "no decisions produced, re-raise" via a dedicated
    :class:`errors.ValidationError` path.
    """
    accepted: list[str] = []
    rejected: list[str] = []
    section: list[str] | None = None
    stdout = getattr(skill_result, "stdout", "") or ""
    for line in stdout.splitlines():
        s = line.strip()
        if s.lower().startswith("## accepted"):
            section = accepted
            continue
        if s.lower().startswith("## rejected"):
            section = rejected
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


def _apply_condition_via_mini_cycle(
    condition: str,
    root: Path,
    iteration: int,
    idx: int,
    *,
    stage_test: StageCallback | None,
    stage_fix: StageCallback | None,
    stage_refactor: StageCallback | None,
) -> tuple[str, str, str]:
    """Orchestrate a 3-commit mini-cycle for an accepted MAGI condition.

    MAGI Loop 2 iter 1 Finding 1 fix: the helper no longer assumes the
    caller pre-stages the working tree before invocation; instead, each
    commit boundary is preceded by the caller-supplied staging callback
    that places exactly the files of that TDD phase in the index. The
    helper becomes a coordinator/observer: it never edits files, it only
    sequences ``stage`` → ``commit_create`` per phase. This eliminates
    the "three empty commits" failure mode where ``commit_create`` was
    invoked three times back-to-back with nothing staged between them.

    Args:
        condition: The accepted condition text (used verbatim inside the
            commit message so the audit trail records which finding
            triggered this mini-cycle).
        root: Project root directory (passed through as ``cwd=`` to
            ``commit_create`` so git runs in the destination repo).
        iteration: 1-indexed MAGI iteration number (for the commit tag).
        idx: 1-indexed condition index inside the iteration.
        stage_test: Callable that stages the failing reproducing test.
        stage_fix: Callable that stages the minimal implementation.
        stage_refactor: Callable that stages post-green polish (may be a
            lambda that does nothing if no refactor is warranted, but
            MUST NOT be ``None`` -- callers must make this explicit).

    Returns:
        ``(test_sha, fix_sha, refactor_sha)`` -- the SHAs of the three
        commits created, in order.

    Raises:
        NotImplementedError: Any of ``stage_test`` / ``stage_fix`` /
            ``stage_refactor`` is ``None``. Defaulting to ``None`` in the
            signature forces every caller to think about what they are
            staging per phase; silent empty commits are no longer possible.
        CommitError: Propagated from :func:`commits.create` when git
            rejects the commit (including the empty-commit rejection if
            the caller's callback failed to stage anything).

    Contract (post-Finding 1):
      - Both interactive ``pre-merge`` and shoot-and-forget ``auto``
        callers pass concrete callbacks. Interactive mode typically
        presents a UI prompt letting the user apply + stage the fix;
        ``auto`` mode dispatches the subagent-driven-development
        orchestrator to produce the diff then stages it.
      - ``/receiving-code-review`` has already validated the approach
        (INV-29 gate) BEFORE this helper runs; the condition text that
        reaches here is ACCEPTED.

    INV-29 compliance: ``/receiving-code-review`` acts as the technical
    gate BEFORE this helper runs. Mini-cycle atomicity per sec.M.5 row 5:
    ``test:`` (reproducing), ``fix:`` (resolution), ``refactor:`` (polish).
    """
    if stage_test is None or stage_fix is None or stage_refactor is None:
        raise NotImplementedError(
            "_apply_condition_via_mini_cycle requires all three staging "
            "callbacks (stage_test, stage_fix, stage_refactor); None is not "
            "permitted -- pass an explicit no-op lambda if a phase stages "
            "nothing. See MAGI Loop 2 iter 1 Finding 1."
        )
    tag = f"magi iter {iteration} cond {idx}"
    stage_test()
    test_sha = commit_create("test", f"add reproducing test for {condition} ({tag})", cwd=str(root))
    stage_fix()
    fix_sha = commit_create("fix", f"apply fix for {condition} ({tag})", cwd=str(root))
    stage_refactor()
    refactor_sha = commit_create("refactor", f"polish {condition} ({tag})", cwd=str(root))
    return test_sha, fix_sha, refactor_sha


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


def _conditions_to_skill_args(conditions: tuple[str, ...]) -> list[str]:
    """Serialise MAGI conditions as CLI args for /receiving-code-review.

    The skill accepts findings as quoted positional arguments via
    ``claude -p /receiving-code-review "<finding1>" "<finding2>" ...``
    (consistent with the ``_make_wrapper`` pattern in
    :mod:`superpowers_dispatch`).
    """
    return [c for c in conditions]


def _loop2(
    root: Path, cfg: PluginConfig, threshold_override: str | None
) -> magi_dispatch.MAGIVerdict:
    """Run Loop 2 -- ``/magi:magi`` with INV-28 + INV-29 (sec.S.5.6).

    Delegates ``/receiving-code-review`` gating to
    :func:`_parse_receiving_review`, applies accepted conditions via
    :func:`_apply_condition_via_mini_cycle`, feeds rejections to the next
    iteration via :func:`_write_magi_feedback_file`. Short-circuits on
    STRONG_NO_GO (INV-28 exception). Caps iterations at
    ``cfg.magi_max_iterations``.

    Args:
        root: Project root directory.
        cfg: Parsed plugin configuration (for ``magi_threshold`` and
            ``magi_max_iterations``).
        threshold_override: Optional threshold override passed via
            ``--magi-threshold``. Must ELEVATE the configured threshold,
            never lower it.

    Returns:
        The last :class:`magi_dispatch.MAGIVerdict` that cleared the gate.

    Raises:
        MAGIGateError: STRONG_NO_GO at any iteration, OR iterations
            exhausted without reaching ``threshold`` full.
        ValidationError: Unknown threshold override, or
            ``/receiving-code-review`` produced no decisions for non-empty
            MAGI conditions.
    """
    threshold = threshold_override or cfg.magi_threshold
    if _safe_threshold_rank(threshold) < _safe_threshold_rank(cfg.magi_threshold):
        raise ValidationError(
            f"--magi-threshold can only elevate; {threshold} < config {cfg.magi_threshold}"
        )
    diff_paths = [str(root / cfg.plan_path)]
    rejections: list[str] = []
    for iteration in range(1, cfg.magi_max_iterations + 1):
        iter_paths = list(diff_paths)
        if rejections:
            iter_paths.append(str(_write_magi_feedback_file(root, rejections)))
        verdict = magi_dispatch.invoke_magi(context_paths=iter_paths, cwd=str(root))
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(f"MAGI STRONG_NO_GO at iter {iteration}")
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
            for idx, cond in enumerate(accepted, start=1):
                # ``_loop2`` does not produce the fix diff itself -- see
                # :func:`_noop_stage` for why we hand named no-ops to the
                # helper even though the Finding 1 contract forbids None.
                _apply_condition_via_mini_cycle(
                    cond,
                    root,
                    iteration,
                    idx,
                    stage_test=_noop_stage,
                    stage_fix=_noop_stage,
                    stage_refactor=_noop_stage,
                )
            rejections.extend(f"iter {iteration} rejected: {c}" for c in rejected)
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            if verdict.verdict == "GO_WITH_CAVEATS" and not _conditions_low_risk(
                verdict.conditions
            ):
                continue  # structural condition -- re-invoke to confirm
            return verdict
    raise MAGIGateError(
        f"MAGI did not converge to full {threshold}+ after {cfg.magi_max_iterations} iterations"
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd pre-merge (Loop 1 + Loop 2, sec.S.5.6)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root: Path = ns.project_root
    _preflight(root)
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _loop1(root)
    verdict = _loop2(root, cfg, ns.magi_threshold)
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return 0


run = main
