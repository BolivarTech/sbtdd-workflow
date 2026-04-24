#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Spec-reviewer dispatch for the sbtdd-workflow plugin (v0.2 Feature B).

This module implements INV-31 of the SBTDD methodology: every task close in
``auto_cmd`` and ``close_task_cmd`` (interactive) MUST pass a spec-reviewer
approval before ``mark_and_advance`` advances state, unless the
``--skip-spec-review`` flag is set or a stub fixture is injected.

The dispatcher invokes the superpowers
``subagent-driven-development/spec-reviewer-prompt.md`` subagent for one task
at a time, passing the task text extracted from the approved plan plus the
diff of commits produced for that task. The subagent classifies findings
into three defect classes (missing requirements, extra/unneeded work,
misunderstandings) and returns a JSON payload parsed by
:func:`_parse_reviewer_output`.

Public contract:

* :class:`SpecIssue` / :class:`SpecReviewResult` — immutable result types
  consumed by ``auto_cmd._phase2_task_loop`` and ``close_task_cmd``.
* :func:`dispatch_spec_reviewer` — runs the reviewer with an N-iteration
  safety valve (default 3 per task, matching the Checkpoint 2 pattern)
  and writes one audit artifact per dispatch under
  ``.claude/spec-reviews/<task-id>-<timestamp>.json``.

Exit-code mapping (via :data:`errors.EXIT_CODES`):

* :class:`SpecReviewError` → 12 (``SPEC_REVIEW_ISSUES``), raised when the
  safety valve is exhausted with issues still outstanding.
* :class:`QuotaExhaustedError` → 11, raised when
  :mod:`quota_detector` matches the reviewer subprocess stderr.
* :class:`ValidationError` → 1, raised when the reviewer stdout is not a
  well-formed JSON payload.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import quota_detector
import subprocess_utils
from errors import QuotaExhaustedError, SpecReviewError, ValidationError

_SeverityLit = Literal["MISSING", "EXTRA", "MISUNDERSTANDING"]

#: Skill reference passed to ``claude -p`` when invoking the reviewer
#: subagent. Kept as a module-level constant so the stubbed integration
#: tests can monkeypatch it (mirrors the ``magi_dispatch`` pattern).
_REVIEWER_SKILL_REF = "/superpowers:subagent-driven-development/spec-reviewer-prompt.md"


@dataclass(frozen=True)
class SpecIssue:
    """One finding raised by the spec-reviewer for a single task.

    Attributes:
        severity: Defect class as classified by the reviewer. One of
            ``"MISSING"`` (requirement not implemented),
            ``"EXTRA"`` (over-engineering outside spec scope),
            ``"MISUNDERSTANDING"`` (solved wrong problem / wrong way).
        text: Human-readable description of the finding emitted by the
            reviewer subagent.
    """

    severity: _SeverityLit
    text: str


@dataclass(frozen=True)
class SpecReviewResult:
    """Aggregate outcome of a spec-reviewer dispatch for one task.

    Attributes:
        approved: ``True`` when the reviewer raised no issues for the
            task's diff; ``False`` when at least one issue requires
            remediation before ``close_task_cmd.mark_and_advance`` may
            advance state.
        issues: Immutable tuple of :class:`SpecIssue` entries. Empty when
            ``approved`` is ``True``.
        reviewer_iter: Count of reviewer iterations consumed for this
            task, bounded by the safety valve (default 3 per task).
        artifact_path: Filesystem path to the audit artifact written
            under ``.claude/spec-reviews/`` for this dispatch. ``None``
            when no artifact was produced (e.g. construction in tests).
    """

    approved: bool
    issues: tuple[SpecIssue, ...]
    reviewer_iter: int
    artifact_path: Path | None


def _parse_reviewer_output(raw: str) -> tuple[bool, tuple[SpecIssue, ...]]:
    """Decode the reviewer subagent's JSON payload.

    Args:
        raw: The raw stdout string emitted by the reviewer subprocess.

    Returns:
        A ``(approved, issues)`` tuple. ``approved`` is ``True`` when the
        reviewer raised no blocking findings; ``issues`` is an immutable
        tuple of :class:`SpecIssue` — empty when ``approved`` is ``True``.

    Raises:
        ValidationError: If ``raw`` is not valid JSON, or if the ``issues``
            field is present but not a list.
    """
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"spec-reviewer output is not valid JSON: {exc}") from exc
    approved = bool(payload.get("approved", False))
    issues_raw = payload.get("issues", []) or []
    if not isinstance(issues_raw, list):
        raise ValidationError("spec-reviewer 'issues' must be a list")
    issues = tuple(
        SpecIssue(
            severity=str(i.get("severity", "MISSING")).upper(),  # type: ignore[arg-type]
            text=str(i.get("text", "")),
        )
        for i in issues_raw
    )
    return approved, issues


def _write_artifact(
    result_payload: dict[str, Any],
    repo_root: Path,
    task_id: str,
) -> Path:
    """Persist one reviewer dispatch as a JSON audit artifact.

    Creates ``<repo_root>/.claude/spec-reviews/`` if missing. The filename
    is ``<task_id>-<iso-timestamp>.json`` with colons replaced by dashes
    so Windows filesystems accept it.

    Args:
        result_payload: Dict with ``task_id``, ``approved``, ``iter_history``,
            and ``final_issues`` keys.
        repo_root: Destination project root.
        task_id: Plan task id used as filename prefix.

    Returns:
        Absolute path of the written artifact.
    """
    directory = repo_root / ".claude" / "spec-reviews"
    directory.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z").replace(":", "-")
    artifact = directory / f"{task_id}-{ts}.json"
    artifact.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    return artifact


def _extract_task_text(plan_text: str, task_id: str) -> str:
    """Return the slice of the plan that describes the named task.

    The plan format (``planning/claude-plan-tdd.md``) uses
    ``### Task <id>: <title>`` headers. This helper scans for the matching
    header and returns content up to the next ``### Task`` header (or EOF).
    Parsing is intentionally forgiving — if no match is found, the whole
    plan is returned so the reviewer still has context.

    Args:
        plan_text: Full content of the approved plan.
        task_id: Plan task id to locate (e.g. ``"H3"``, ``"1"``).

    Returns:
        The task's section text, or the whole plan when no match is found.
    """
    marker = f"### Task {task_id}:"
    start = plan_text.find(marker)
    if start == -1:
        return plan_text
    end = plan_text.find("### Task ", start + len(marker))
    if end == -1:
        return plan_text[start:]
    return plan_text[start:end]


def _build_reviewer_prompt(task_id: str, task_text: str, diff_text: str) -> str:
    """Compose the reviewer subagent prompt for one task.

    The prompt embeds the directive ``"Verify by reading code, NOT by
    trusting implementer report."`` verbatim from the
    ``spec-reviewer-prompt.md`` skill — that line is the contract the
    reviewer subagent enforces against optimistic implementer reports
    (rationale: ``CLAUDE.md`` v0.2 Feature B section).

    Args:
        task_id: Plan task id; surfaces in the prompt header for the
            reviewer's traceability.
        task_text: Task section text extracted from the approved plan.
        diff_text: ``git diff`` output for the task's commits.

    Returns:
        The fully assembled prompt string passed to ``claude -p``.
    """
    return (
        f"Task: {task_id}\n\n"
        f"Task text:\n{task_text}\n\n"
        f"Diff:\n{diff_text}\n\n"
        "Verify by reading code, NOT by trusting implementer report."
    )


def _build_artifact_payload(
    task_id: str,
    *,
    approved: bool,
    iter_history: list[dict[str, Any]],
    issues: tuple[SpecIssue, ...],
) -> dict[str, Any]:
    """Compose the audit-artifact JSON body for a finalized dispatch.

    Both the approval and safety-valve-exhaustion paths persist the same
    schema, differing only in the ``approved`` flag and the (possibly
    empty) ``final_issues`` list. Centralising the shape here keeps the
    two call sites in :func:`dispatch_spec_reviewer` from drifting.

    Args:
        task_id: Plan task id, copied into the artifact body.
        approved: Final reviewer verdict for the dispatch.
        iter_history: Per-iteration tally accumulated during the loop.
        issues: Outstanding findings for the exhaustion path; empty
            tuple for the approval path.

    Returns:
        A ``dict`` ready to be serialised by :func:`_write_artifact`.
    """
    return {
        "task_id": task_id,
        "approved": approved,
        "iter_history": iter_history,
        "final_issues": [{"severity": i.severity, "text": i.text} for i in issues],
    }


def _collect_task_diff(repo_root: Path, task_id: str) -> str:
    """Return the diff of the commits produced for ``task_id``.

    v0.2 baseline uses the last three commits of ``HEAD`` as a proxy for
    the task's Red/Green/Refactor trio; that matches the per-task commit
    cadence enforced by the SBTDD methodology (sec.5). Git failures are
    swallowed so the dispatcher stays operational in test fixtures that
    don't construct a real repo.

    Args:
        repo_root: Destination project root.
        task_id: Plan task id, forwarded only to the error-path comment.

    Returns:
        ``git diff`` output as text, or an empty string when the command
        fails (no repo, empty history, ...). The reviewer handles missing
        diff context gracefully.
    """
    del task_id  # Reserved for future commit-range inference.
    try:
        result = subprocess_utils.run_with_timeout(
            ["git", "-C", str(repo_root), "log", "-p", "-n", "3", "HEAD"],
            timeout=30,
            capture=True,
        )
    except subprocess.TimeoutExpired:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout or ""


def dispatch_spec_reviewer(
    *,
    task_id: str,
    plan_path: Path,
    repo_root: Path,
    max_iterations: int = 1,
    timeout: int = 900,
) -> SpecReviewResult:
    """Run the spec-reviewer for ONE task with a bounded retry budget.

    The reviewer subagent is invoked via ``claude -p`` on
    ``spec-reviewer-prompt.md`` with the task text extracted from the
    approved plan plus the last three commits of ``HEAD``. The reviewer
    returns a JSON verdict consumed by :func:`_parse_reviewer_output`.

    The loop short-circuits on approval and writes a single audit artifact
    summarising the iteration history under ``.claude/spec-reviews/``.
    When the safety valve is exhausted (``max_iterations`` reached with
    issues still outstanding), the artifact is still written for
    post-mortem before :class:`SpecReviewError` is raised — this mirrors
    the MAGI Loop 2 convention where verdict artifacts precede the
    dispatcher exception.

    Args:
        task_id: Plan task id whose diff will be reviewed.
        plan_path: Path to the approved plan (``planning/claude-plan-tdd.md``).
        repo_root: Destination project root; used both as git cwd and as
            audit-artifact base.
        max_iterations: Safety valve cap. **Pinned to 1 in v0.2** per MAGI
            Loop 2 CRITICAL finding (2026-04-24): the loop re-invokes the
            reviewer on byte-identical inputs across iterations because
            spec-base §2.2's mini-cycle TDD feedback between dispatches is
            explicitly deferred to v0.2.1 (B6 relaxation). Without feedback
            the reviewer is nominally deterministic, so iter 2+ burn quota
            for zero semantic benefit. When v0.2.1 lands
            ``/receiving-code-review`` + mini-cycle fix + re-dispatch the
            default bumps back to 3.
        timeout: Per-call subprocess timeout in seconds (default 900, the
            reviewer budget prescribed by ``CLAUDE.md`` v0.2 Feature B).

    Returns:
        :class:`SpecReviewResult` with ``approved=True`` on success; the
        ``artifact_path`` points at the just-written JSON audit record.

    Raises:
        SpecReviewError: Safety valve exhausted, reviewer process exited
            non-zero without a matching quota pattern, or the subprocess
            timed out.
        QuotaExhaustedError: :mod:`quota_detector` matched a pattern in
            the reviewer subprocess stderr.
        ValidationError: Reviewer stdout could not be parsed as the
            expected JSON shape.
    """
    plan_text = plan_path.read_text(encoding="utf-8")
    task_text = _extract_task_text(plan_text, task_id)
    diff_text = _collect_task_diff(repo_root, task_id)
    prompt = _build_reviewer_prompt(task_id, task_text, diff_text)
    cmd = ["claude", "-p", _REVIEWER_SKILL_REF, prompt]
    iter_history: list[dict[str, Any]] = []
    for iteration in range(1, max_iterations + 1):
        try:
            result = subprocess_utils.run_with_timeout(
                cmd,
                timeout=timeout,
                capture=True,
                cwd=str(repo_root),
            )
        except subprocess.TimeoutExpired as exc:
            raise SpecReviewError(
                f"spec-reviewer timed out at iter {iteration} for task {task_id}",
                task_id=task_id,
                iteration=iteration,
            ) from exc
        if result.returncode != 0:
            exhaustion = quota_detector.detect(result.stderr or "")
            if exhaustion is not None:
                raise QuotaExhaustedError(f"{exhaustion.kind}: {exhaustion.raw_message}")
            raise SpecReviewError(
                f"spec-reviewer exited {result.returncode} at iter {iteration} for task {task_id}",
                task_id=task_id,
                iteration=iteration,
            )
        approved, issues = _parse_reviewer_output(result.stdout or "")
        iter_history.append({"iter": iteration, "approved": approved, "n_issues": len(issues)})
        if approved:
            artifact = _write_artifact(
                _build_artifact_payload(
                    task_id, approved=True, iter_history=iter_history, issues=()
                ),
                repo_root,
                task_id,
            )
            return SpecReviewResult(
                approved=True,
                issues=(),
                reviewer_iter=iteration,
                artifact_path=artifact,
            )
        if iteration == max_iterations:
            artifact = _write_artifact(
                _build_artifact_payload(
                    task_id, approved=False, iter_history=iter_history, issues=issues
                ),
                repo_root,
                task_id,
            )
            raise SpecReviewError(
                f"spec-reviewer safety valve exhausted for task {task_id} "
                f"after {iteration} iterations ({len(issues)} issues)",
                task_id=task_id,
                iteration=iteration,
                issues=tuple(i.text for i in issues),
            )
    raise SpecReviewError(
        f"unreachable: max_iterations must be >= 1 for task {task_id}",
        task_id=task_id,
        iteration=0,
    )
