#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd auto -- shoot-and-forget full-cycle (sec.S.5.8, INV-22..26).

Five-phase flow:

1. Phase 1 -- pre-flight dependency check + state / plan_approved_at
   validation (Task 27).
2. Phase 2 -- sequential task loop with TDD cycles per task (Task 28).
3. Phase 3 -- pre-merge with elevated MAGI budget (Task 29).
4. Phase 4 -- sec.M.7 checklist validation (Task 30).
5. Phase 5 -- report + ``.claude/auto-run.json`` audit trail (Task 30).

Design invariants enforced here:

- **INV-22** (sequential only): never spawn parallel subprocesses.
- **INV-23** (TDD-Guard inviolable): never writes to
  ``.claude/settings.json`` (spied in Task 31 test).
- **INV-24** (conservative): verification retries exhaust -> exit 6.
- **INV-25** (branch-scoped): never invokes
  ``/finishing-a-development-branch`` -- leaves the branch clean for
  the user to merge/PR manually.
- **INV-26** (audit trail): writes ``.claude/auto-run.json`` with
  per-phase timestamps and verdict.

Dry-run short-circuits BEFORE any subprocess work (Finding 4) so a
preview works even when git / tdd-guard / plugins are unavailable.

INV-24 (conservative defaults) does NOT apply inside ``auto`` itself --
auto commits atomically at every phase boundary, so no uncommitted work
is ever left behind mid-run. The CONTINUE-by-default contract for
uncommitted work lives in :mod:`resume_cmd` (see
``resume_cmd._resolve_uncommitted``) and engages only when the user
re-enters via ``/sbtdd resume`` after an externally-caused interruption
(crash, quota, Ctrl+C). This cross-reference exists to forestall the
common reader question "where is INV-24 enforced in auto?" -- the answer
is "in resume; auto never needs it".
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import close_task_cmd
import subprocess_utils
import superpowers_dispatch
from commits import create as commit_create
from config import PluginConfig, load_plugin_local
from dependency_check import check_environment
from drift import detect_drift
from errors import (
    ChecklistError,
    DependencyError,
    DriftError,
    MAGIGateError,
    PreconditionError,
    QuotaExhaustedError,
    ValidationError,
    VerificationIrremediableError,
)
from models import COMMIT_PREFIX_MAP
from state_file import SessionState
from state_file import load as load_state
from state_file import save as save_state


#: Allowed values for AutoRunAudit.status. Extending this set is a schema
#: change: bump ``_AUTO_RUN_SCHEMA_VERSION`` below and update tests.
_ALLOWED_AUTO_RUN_STATUSES: tuple[str, ...] = (
    "success",
    "magi_gate_blocked",
    "verification_irremediable",
    "loop1_divergent",
    "quota_exhausted",
    "checklist_failed",
    "drift_detected",
    "precondition_failed",
)

#: Current schema version for ``.claude/auto-run.json``. Bump when a
#: backwards-incompatible change lands (field removed, type changed,
#: status value removed). Additive changes (new status, new optional
#: field) keep the version.
_AUTO_RUN_SCHEMA_VERSION: int = 1


@dataclass(frozen=True)
class AutoRunAudit:
    """Frozen schema for ``.claude/auto-run.json`` (INV-26 audit trail).

    Formalises the opportunistic dict writes used in Milestone C. Every
    field is required; ``to_dict`` is symmetric with ``from_dict`` and
    the shape is asserted by ``validate_schema``. Bump
    ``schema_version`` via ``_AUTO_RUN_SCHEMA_VERSION`` for
    backwards-incompatible changes.

    Attributes:
        schema_version: Integer version (1 for v0.1 of the plugin).
        auto_started_at: ISO 8601 timestamp of ``main`` entry.
        auto_finished_at: ISO 8601 timestamp of ``main`` exit, or
            ``None`` when the run is still in progress / aborted mid-way.
        status: One of :data:`_ALLOWED_AUTO_RUN_STATUSES`.
        verdict: The gating MAGI verdict string (``GO`` / ``GO_WITH_CAVEATS``
            / ``STRONG_NO_GO`` / ...), or ``None`` if the run aborted
            before Phase 3 completed.
        degraded: ``True`` when MAGI returned degraded consensus; ``None``
            if no verdict was obtained.
        accepted_conditions: Count of MAGI conditions accepted by
            ``/receiving-code-review`` across all Loop 2 iterations.
        rejected_conditions: Count of MAGI conditions rejected by
            ``/receiving-code-review``.
        tasks_completed: Number of plan tasks that reached
            ``current_phase == 'done'`` during this auto run.
        error: Free-form error message when ``status != 'success'``,
            ``None`` on success.
    """

    schema_version: int
    auto_started_at: str
    auto_finished_at: str | None
    status: str
    verdict: str | None
    degraded: bool | None
    accepted_conditions: int
    rejected_conditions: int
    tasks_completed: int
    error: str | None

    def validate_schema(self) -> None:
        """Raise :class:`ValidationError` on any schema inconsistency."""
        if self.schema_version != _AUTO_RUN_SCHEMA_VERSION:
            raise ValidationError(
                f"AutoRunAudit.schema_version={self.schema_version} != "
                f"expected {_AUTO_RUN_SCHEMA_VERSION}"
            )
        if self.status not in _ALLOWED_AUTO_RUN_STATUSES:
            raise ValidationError(
                f"AutoRunAudit.status={self.status!r} not in {sorted(_ALLOWED_AUTO_RUN_STATUSES)}"
            )
        if self.accepted_conditions < 0:
            raise ValidationError(
                f"AutoRunAudit.accepted_conditions={self.accepted_conditions} < 0"
            )
        if self.rejected_conditions < 0:
            raise ValidationError(
                f"AutoRunAudit.rejected_conditions={self.rejected_conditions} < 0"
            )
        if self.tasks_completed < 0:
            raise ValidationError(f"AutoRunAudit.tasks_completed={self.tasks_completed} < 0")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AutoRunAudit:
        """Build an :class:`AutoRunAudit` from a parsed JSON dict."""

        def _coerce_int(value: object, default: int) -> int:
            if value is None:
                return default
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, str)):
                return int(value)
            raise TypeError(f"cannot coerce {type(value).__name__} to int")

        return cls(
            schema_version=_coerce_int(data.get("schema_version"), _AUTO_RUN_SCHEMA_VERSION),
            auto_started_at=str(data["auto_started_at"]),
            auto_finished_at=(
                str(data["auto_finished_at"]) if data.get("auto_finished_at") is not None else None
            ),
            status=str(data.get("status", "success")),
            verdict=(str(data["verdict"]) if data.get("verdict") is not None else None),
            degraded=(bool(data["degraded"]) if data.get("degraded") is not None else None),
            accepted_conditions=_coerce_int(data.get("accepted_conditions"), 0),
            rejected_conditions=_coerce_int(data.get("rejected_conditions"), 0),
            tasks_completed=_coerce_int(data.get("tasks_completed"), 0),
            error=(str(data["error"]) if data.get("error") is not None else None),
        )


def _build_parser() -> argparse.ArgumentParser:
    """Return the argparse parser for ``sbtdd auto``."""
    p = argparse.ArgumentParser(prog="sbtdd auto")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--plugins-root",
        type=Path,
        default=Path.home() / ".claude" / "plugins",
    )
    p.add_argument("--magi-max-iterations", type=int, default=None)
    p.add_argument("--magi-threshold", type=str, default=None)
    p.add_argument("--verification-retries", type=int, default=None)
    p.add_argument("--dry-run", action="store_true")
    return p


def _print_dry_run_preview(ns: argparse.Namespace) -> None:
    """Emit the dry-run plan without reading any subprocess/tool output.

    Keeps dry-run stdlib-only and side-effect-free so it works even
    when git/tdd-guard/plugins are unavailable.
    """
    sys.stdout.write(
        "/sbtdd auto --dry-run:\n"
        f"  project_root: {ns.project_root}\n"
        f"  magi_max_iterations (override): {ns.magi_max_iterations}\n"
        f"  magi_threshold (override): {ns.magi_threshold}\n"
        f"  verification_retries (override): {ns.verification_retries}\n"
        "  Would execute phases 1-5 sequentially (preflight, task loop,\n"
        "  pre-merge, checklist, report). No commits, no subprocess calls.\n"
    )


def _phase1_preflight(ns: argparse.Namespace) -> tuple[SessionState, PluginConfig]:
    """Run Phase 1 -- pre-flight dependency + state + plan_approved_at check.

    Precondition order (deterministic for the user):

    1. ``.claude/session-state.json`` exists (``PreconditionError`` otherwise).
    2. ``state.plan_approved_at`` is not ``None`` -- auto requires an
       approved plan so the "Excepcion bajo plan aprobado" from template
       sec.5 is in effect.
    3. All dependency checks green (Rust/Python/C++ toolchain, git,
       tdd-guard, superpowers + magi plugins). Failures are reported in
       full -- no short-circuit (INV-12 / sec.S.5.1.1).

    Args:
        ns: Parsed argparse namespace (provides ``project_root`` +
            ``plugins_root``).

    Returns:
        A tuple ``(SessionState, PluginConfig)`` consumed by the
        downstream phases.

    Raises:
        PreconditionError: Missing state file or ``plan_approved_at is None``.
        DependencyError: Any pre-flight check reported non-OK status.
    """
    root: Path = ns.project_root
    state_path = root / ".claude" / "session-state.json"
    if not state_path.exists():
        raise PreconditionError(f"state file not found: {state_path}")
    state = load_state(state_path)
    if state.plan_approved_at is None:
        raise PreconditionError(
            "plan_approved_at is null - run /sbtdd spec to approve a plan before /sbtdd auto"
        )
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    report = check_environment(cfg.stack, root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    return state, cfg


_PHASE_ORDER: tuple[str, ...] = ("red", "green", "refactor")


def _now_iso() -> str:
    """Return UTC ISO 8601 timestamp with a Z suffix (CLAUDE.md sec.2.2)."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _current_head_sha(root: Path) -> str:
    """Return short SHA of HEAD via ``git rev-parse --short``."""
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    return r.stdout.strip()


def _run_verification_with_retries(root: Path, retries: int) -> None:
    """Invoke ``/verification-before-completion`` with retry budget.

    Each failure below the budget triggers ``/systematic-debugging`` to give
    the loop a structured hand-off for root-cause analysis (sec.M.3). When
    attempts exceed ``retries`` the last failure is wrapped as
    :class:`VerificationIrremediableError` (exit 6).

    Exception handling policy (MAGI Loop 2 iter 1 Finding 2):

    - :class:`QuotaExhaustedError` is re-raised UNCHANGED without
      consuming a retry or invoking ``/systematic-debugging``. Quota is
      a hard cap on API usage, not a transient verification failure;
      retrying cannot help and wrapping would remap exit 11 -> 6,
      destroying the telemetry that ``/sbtdd resume`` consumes to
      classify interruptions.
    - Any other :class:`Exception` consumes one retry and triggers
      ``/systematic-debugging``; budget exhaustion wraps as
      :class:`VerificationIrremediableError`.

    Args:
        root: Project root directory passed as ``cwd`` to the skills.
        retries: Number of additional attempts allowed after the first
            failure. ``retries=0`` means a single attempt with no retry.

    Raises:
        QuotaExhaustedError: Verification hit an Anthropic API cap (exit
            11). Propagated unchanged; caller's dispatcher maps to 11.
        VerificationIrremediableError: Non-quota verification failures
            exhausted the retry budget (exit 6).
    """
    for attempt in range(retries + 1):
        try:
            superpowers_dispatch.verification_before_completion(cwd=str(root))
            return
        except QuotaExhaustedError:
            # MAGI Loop 2 iter 1 Finding 2: quota exhaustion is NOT a
            # retryable failure -- it signals an Anthropic API hard cap
            # (429 rate limit, session/weekly/Opus subscription limit,
            # credit balance exhausted, server throttle). Wrapping it as
            # VerificationIrremediableError would remap exit 11 (quota)
            # to exit 6 (irremediable), destroying the telemetry that
            # `/sbtdd resume` relies on to detect quota interruptions.
            # Propagate unchanged; the dispatcher maps to exit 11.
            raise
        except Exception as exc:
            if attempt >= retries:
                raise VerificationIrremediableError(
                    f"verification failed after {retries} retries: {exc}"
                ) from exc
            superpowers_dispatch.systematic_debugging(cwd=str(root))


def _phase_prefix(phase: str) -> str:
    """Return the sec.M.5 commit prefix for the closing phase.

    Auto uses ``green_feat`` by default (consistent with
    ``/sbtdd close-phase --variant feat``). Callers that want ``fix``
    semantics must use manual ``close-phase``.
    """
    if phase == "red":
        return COMMIT_PREFIX_MAP["red"]
    if phase == "green":
        return COMMIT_PREFIX_MAP["green_feat"]
    if phase == "refactor":
        return COMMIT_PREFIX_MAP["refactor"]
    raise ValueError(f"unknown phase '{phase}'")


def _phase2_task_loop(
    ns: argparse.Namespace, state: SessionState, cfg: PluginConfig
) -> SessionState:
    """Run Phase 2 -- sequential task loop with TDD cycles per task.

    For each pending task: iterate ``_PHASE_ORDER`` from the current phase
    forward; invoke ``/test-driven-development`` for the phase,
    ``/verification-before-completion`` (with retries), then commit with
    the sec.M.5 prefix. At ``refactor`` close, delegate to
    :func:`close_task_cmd.mark_and_advance` (iter-2 W1 public helper) so
    the close-task bookkeeping stays single-sourced.

    Drift is re-checked at entry; any non-None
    :class:`drift.DriftReport` aborts with :class:`DriftError` (INV-17,
    exit 3). Drift detection is not re-run between phases: the close of
    each phase produces a commit whose prefix is, by definition, the
    expected one for the NEW phase -- re-checking inside the inner loop
    would flag every legitimate transition as drift.

    Args:
        ns: Parsed argparse namespace.
        state: Current :class:`SessionState` (entry phase may be
            ``red``, ``green``, or ``refactor``; auto starts from there).
        cfg: Plugin configuration (for ``auto_verification_retries``).

    Returns:
        The final :class:`SessionState` after the last task's close-task
        cascade (either ``current_phase='done'`` when the plan is fully
        consumed, or the next task's fresh red phase).

    Raises:
        DriftError: Drift detected at entry.
        VerificationIrremediableError: Phase verification exhausted the
            retry budget.
    """
    root: Path = ns.project_root
    retries = (
        ns.verification_retries
        if ns.verification_retries is not None
        else cfg.auto_verification_retries
    )
    state_path = root / ".claude" / "session-state.json"
    plan_path = root / state.plan_path
    dr = detect_drift(state_path, plan_path, root)
    if dr is not None:
        raise DriftError(f"drift at auto Phase 2: {dr.reason}")
    current = state
    auto_run = root / ".claude" / "auto-run.json"
    # Recover the auto_started_at timestamp from the in-progress audit
    # written by main() BEFORE this loop. If absent (test harnesses that
    # skip main's initialisation), fall back to the current timestamp so
    # incremental writes remain schema-valid.
    started_at = _now_iso()
    if auto_run.exists():
        try:
            prev = json.loads(auto_run.read_text("utf-8"))
            started_at = str(prev.get("auto_started_at", started_at))
        except (json.JSONDecodeError, OSError):
            pass
    tasks_completed = 0
    while current.current_task_id is not None:
        phase_idx = (
            _PHASE_ORDER.index(current.current_phase)
            if current.current_phase in _PHASE_ORDER
            else 0
        )
        for phase in _PHASE_ORDER[phase_idx:]:
            superpowers_dispatch.test_driven_development(args=[f"--phase={phase}"], cwd=str(root))
            _run_verification_with_retries(root, retries)
            prefix = _phase_prefix(phase)
            commit_create(prefix, f"{phase} for task {current.current_task_id}", cwd=str(root))
            new_sha = _current_head_sha(root)
            if phase != "refactor":
                next_phase = _PHASE_ORDER[_PHASE_ORDER.index(phase) + 1]
                current = SessionState(
                    plan_path=current.plan_path,
                    current_task_id=current.current_task_id,
                    current_task_title=current.current_task_title,
                    current_phase=next_phase,
                    phase_started_at_commit=new_sha,
                    last_verification_at=_now_iso(),
                    last_verification_result="passed",
                    plan_approved_at=current.plan_approved_at,
                )
                save_state(current, state_path)
            else:
                # W1: delegate to public helper in close_task_cmd instead
                # of duplicating the entire flip / commit chore / advance
                # sequence.
                current = close_task_cmd.mark_and_advance(current, root)
                tasks_completed += 1
                # Plan D iter 2 Caspar: incremental audit write after
                # each task close so a mid-loop raise preserves the
                # partial tasks_completed count on disk.
                _write_auto_run_audit(
                    auto_run,
                    AutoRunAudit(
                        schema_version=_AUTO_RUN_SCHEMA_VERSION,
                        auto_started_at=started_at,
                        auto_finished_at=None,
                        status="success",
                        verdict=None,
                        degraded=None,
                        accepted_conditions=0,
                        rejected_conditions=0,
                        tasks_completed=tasks_completed,
                        error=None,
                    ),
                )
        # After refactor cascade, outer loop re-evaluates against updated
        # current.current_task_id (None -> terminate).
    return current


class _ShadowCfg:
    """Minimal PluginConfig stand-in with ``magi_max_iterations`` overridden.

    Built so :func:`pre_merge_cmd._loop2` can consume the same attribute
    surface as a real :class:`config.PluginConfig` but with the elevated
    ``auto_magi_max_iterations`` budget (INV / sec.S.5.8) substituted for
    the interactive default. Carrying ``__dict__`` copies preserves every
    other configuration field (threshold, plan_path, etc.) unchanged.
    """

    def __init__(self, base: PluginConfig, overrides: dict[str, object]) -> None:
        self.__dict__.update(base.__dict__)
        self.__dict__.update(overrides)


def _phase3_pre_merge(ns: argparse.Namespace, cfg: PluginConfig) -> object:
    """Run Phase 3 -- pre-merge Loop 1 + Loop 2 with elevated MAGI budget.

    Delegates to :mod:`pre_merge_cmd` helpers so the consensus logic and
    verdict parsing stay single-sourced. The only difference vs
    interactive ``/sbtdd pre-merge`` is the ``magi_max_iterations`` cap
    which Auto elevates to ``cfg.auto_magi_max_iterations`` (default 5)
    -- compensates for lack of human supervision on ambiguous caveats.

    ``--magi-max-iterations`` on the CLI overrides both caps; no
    validation is imposed here because the dispatcher already validates
    the integer form.

    Args:
        ns: Parsed argparse namespace.
        cfg: Plugin configuration.

    Returns:
        The :class:`magi_dispatch.MAGIVerdict` that cleared the gate --
        later phases read it to decide whether to invoke finalize
        semantics.

    Raises:
        Loop1DivergentError: Loop 1 non-convergence (exit 7).
        MAGIGateError: STRONG_NO_GO or exhausted MAGI iterations (exit 8).
    """
    import magi_dispatch
    import pre_merge_cmd

    root: Path = ns.project_root
    pre_merge_cmd._loop1(root)
    max_iter = (
        ns.magi_max_iterations
        if ns.magi_max_iterations is not None
        else cfg.auto_magi_max_iterations
    )
    threshold = ns.magi_threshold or cfg.magi_threshold
    shadow = _ShadowCfg(cfg, {"magi_max_iterations": max_iter})
    # mypy: _loop2 consumes the ``magi_max_iterations`` / ``magi_threshold`` /
    # ``plan_path`` attributes via duck typing; the _ShadowCfg wrapper carries
    # exactly those (plus every other PluginConfig field copied by
    # ``__dict__.update``). Casting keeps the call site readable without
    # forcing PluginConfig to grow a Protocol or a dataclasses.replace path.
    verdict = pre_merge_cmd._loop2(root, shadow, threshold)  # type: ignore[arg-type]
    magi_dispatch.write_verdict_artifact(verdict, root / ".claude" / "magi-verdict.json")
    return verdict


def _phase4_checklist(root: Path, state: SessionState, cfg: PluginConfig) -> None:
    """Run Phase 4 -- sec.M.7 checklist validation (reuses finalize logic).

    Delegates the checklist construction to :func:`finalize_cmd._checklist`
    so the 9-item contract stays single-sourced. The key behavioral
    difference vs interactive ``/sbtdd finalize`` is that auto does NOT
    invoke ``/finishing-a-development-branch`` after a pass (INV-25): the
    branch is left clean for the user to merge / PR manually.

    Args:
        root: Project root directory.
        state: Final :class:`SessionState` (expected
            ``current_phase='done'``).
        cfg: Plugin configuration.

    Raises:
        ChecklistError: Any sec.M.7 item failed -- includes a detailed
            one-line-per-failure list in the message (exit 9).
    """
    import finalize_cmd

    magi_verdict_path = root / ".claude" / "magi-verdict.json"
    items = finalize_cmd._checklist(root, state, magi_verdict_path, cfg)
    failures = [(n, d) for (n, ok, d) in items if not ok]
    if failures:
        raise ChecklistError(
            f"auto Phase 4 checklist FAILED ({len(failures)} items): "
            + "; ".join(f"{n} - {d}" for n, d in failures)
        )


def _phase5_report(root: Path, started: str, verdict: object) -> None:
    """Run Phase 5 -- write ``.claude/auto-run.json`` audit trail (INV-26).

    The audit file captures the full lifespan (start -> finish) plus the
    gating MAGI verdict + degraded flag so operators can reconstruct the
    run post-hoc. Also emits a human-readable summary to stdout.

    Args:
        root: Project root directory.
        started: ISO 8601 timestamp of ``main`` entry (from Phase 1).
        verdict: :class:`magi_dispatch.MAGIVerdict` or ``None`` if the
            run aborted before Phase 3 completed (never expected in the
            happy path).
    """
    auto_run = root / ".claude" / "auto-run.json"
    finished = _now_iso()
    tasks_completed = _read_audit_tasks_completed(auto_run)
    verdict_str = getattr(verdict, "verdict", None)
    degraded_value = getattr(verdict, "degraded", None)
    audit = AutoRunAudit(
        schema_version=_AUTO_RUN_SCHEMA_VERSION,
        auto_started_at=started,
        auto_finished_at=finished,
        status="success",
        verdict=verdict_str if verdict_str is None else str(verdict_str),
        degraded=None if degraded_value is None else bool(degraded_value),
        accepted_conditions=0,
        rejected_conditions=0,
        tasks_completed=tasks_completed,
        error=None,
    )
    _write_auto_run_audit(auto_run, audit)
    sys.stdout.write(
        "/sbtdd auto: DONE.\n"
        f"Started:  {started}\n"
        f"Finished: {finished}\n"
        f"MAGI:     {audit.verdict} (degraded={audit.degraded})\n"
        "Branch status: clean, ready for merge/PR.\n"
    )


def _write_auto_run_audit(path: Path, payload: AutoRunAudit) -> None:
    """Write ``.claude/auto-run.json`` with ``payload`` validated.

    Requires an :class:`AutoRunAudit` instance; the dict back-compat
    branch was removed in Plan D iter 2 (Caspar WARNING) because it
    silently bypassed schema validation. Since the plugin is pre-1.0
    and all callers live inside this repo, the stricter signature is
    safe. Task 17 grep-checks for regressions.

    Args:
        path: Absolute path to ``auto-run.json`` (parent is created).
        payload: :class:`AutoRunAudit` instance, validated before write.

    Raises:
        TypeError: ``payload`` is not an :class:`AutoRunAudit` instance.
        ValidationError: ``payload.validate_schema`` failed.
    """
    if not isinstance(payload, AutoRunAudit):
        raise TypeError(
            f"_write_auto_run_audit requires AutoRunAudit, got {type(payload).__name__}"
        )
    payload.validate_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd auto (shoot-and-forget full-cycle)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    # Dry-run short-circuit BEFORE any subprocess work (Finding 4). The
    # cheap parser.parse_args above does not touch the filesystem;
    # stopping here guarantees a preview never invokes preflight,
    # git, or plugin dispatchers.
    if ns.dry_run:
        _print_dry_run_preview(ns)
        return 0
    state, cfg = _phase1_preflight(ns)
    started = _now_iso()
    auto_run = ns.project_root / ".claude" / "auto-run.json"
    _write_auto_run_audit(
        auto_run,
        AutoRunAudit(
            schema_version=_AUTO_RUN_SCHEMA_VERSION,
            auto_started_at=started,
            auto_finished_at=None,
            status="success",
            verdict=None,
            degraded=None,
            accepted_conditions=0,
            rejected_conditions=0,
            tasks_completed=0,
            error=None,
        ),
    )
    if state.current_phase != "done":
        state = _phase2_task_loop(ns, state, cfg)
    try:
        verdict = _phase3_pre_merge(ns, cfg)
    except MAGIGateError as exc:
        # Finding 2 (Caspar): record the gate-block status in the audit
        # trail BEFORE re-raising so operators can post-hoc distinguish
        # "conditions pending" (exit 8 with actionable fix) from
        # STRONG_NO_GO (exit 8 requiring replan). Both map to exit 8 via
        # EXIT_CODES[MAGIGateError]; the status / error fields in
        # auto-run.json are the only signal that survives the exception.
        # Plan D Task 4: source counts from exc's typed attributes (no
        # regex parse) and tasks_completed from the last incremental
        # audit write in Phase 2 (raise-safe partial count).
        tasks_completed = _read_audit_tasks_completed(auto_run)
        accepted_count = len(exc.accepted_conditions)
        rejected_count = len(exc.rejected_conditions)
        _write_auto_run_audit(
            auto_run,
            AutoRunAudit(
                schema_version=_AUTO_RUN_SCHEMA_VERSION,
                auto_started_at=started,
                auto_finished_at=_now_iso(),
                status="magi_gate_blocked",
                verdict=exc.verdict,
                degraded=None,
                accepted_conditions=accepted_count,
                rejected_conditions=rejected_count,
                tasks_completed=tasks_completed,
                error=str(exc),
            ),
        )
        sys.stderr.write(
            f"/sbtdd auto: MAGI gate blocked "
            f"(accepted={accepted_count}, rejected={rejected_count}). See "
            f"{auto_run} and .claude/magi-conditions.md for next steps.\n"
        )
        raise
    _phase4_checklist(ns.project_root, state, cfg)
    _phase5_report(ns.project_root, started, verdict)
    return 0


def _read_audit_tasks_completed(path: Path) -> int:
    """Return the last-persisted ``tasks_completed`` from auto-run.json, or 0.

    Used by the MAGIGateError handler to recover the raise-safe partial
    count that ``_phase2_task_loop`` writes after each task close (Plan D
    iter 2 Caspar -- raise-safe audit). Missing or malformed file returns
    0 (degraded but not corrupted).
    """
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text("utf-8"))
        return int(data.get("tasks_completed", 0))
    except (json.JSONDecodeError, ValueError, OSError):
        return 0


run = main
