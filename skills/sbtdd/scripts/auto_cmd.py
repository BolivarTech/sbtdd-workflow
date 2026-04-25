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
import os
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

import close_task_cmd
import commits
import receiving_review_dispatch
import spec_review_dispatch
import subprocess_utils
import superpowers_dispatch
from commits import create as commit_create
from config import PluginConfig, load_plugin_local
from dependency_check import check_environment
from drift import detect_drift
from errors import (
    ChecklistError,
    CommitError,
    DependencyError,
    DriftError,
    MAGIGateError,
    PreconditionError,
    QuotaExhaustedError,
    SpecReviewError,
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
    "spec_review_issues",
)

#: Current schema version for ``.claude/auto-run.json``. Bump when a
#: backwards-incompatible change lands (field removed, type changed,
#: status value removed). Additive changes (new status, new optional
#: field) keep the version.
_AUTO_RUN_SCHEMA_VERSION: int = 1


def _stream_subprocess(
    proc: subprocess.Popen[str],
    prefix: str,
) -> tuple[str, str]:
    """Read subprocess stdout/stderr line-by-line, rewrite to orchestrator stderr.

    Reads pipes via a thread-pair pump so neither stream starves and the
    helper works identically on POSIX and Windows (``select.select`` does
    not work on pipes on Windows -- PEP 446). Each line is prefixed with
    ``prefix`` and emitted to ``sys.stderr`` of the orchestrator with an
    explicit ``flush`` so external observers see progress in real time.

    Returns the accumulated ``(stdout, stderr)`` strings for the caller's
    diagnostic / commit-error recovery paths (``CommitError`` v0.1.6
    expects captured strings).

    Implements Feature D scenarios D1.1 (line-buffered flush), D1.2
    (prefix-aware rewrite), and D1.3 (final flush on subprocess exit).

    Args:
        proc: A ``subprocess.Popen`` opened with ``stdout=PIPE`` and
            ``stderr=PIPE`` in text mode (``text=True``).
        prefix: Tag prepended to every emitted line, e.g.
            ``"[sbtdd task-7 green]"``.

    Returns:
        Tuple ``(stdout_text, stderr_text)`` containing the verbatim
        subprocess output (without the orchestrator prefix).
    """
    stdout_buf: list[str] = []
    stderr_buf: list[str] = []

    def _pump(stream: IO[str] | None, sink: list[str]) -> None:
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            sink.append(line)
            sys.stderr.write(f"{prefix} {line}")
            sys.stderr.flush()
        stream.close()

    t_out = threading.Thread(target=_pump, args=(proc.stdout, stdout_buf), daemon=True)
    t_err = threading.Thread(target=_pump, args=(proc.stderr, stderr_buf), daemon=True)
    t_out.start()
    t_err.start()
    t_out.join()
    t_err.join()
    return ("".join(stdout_buf), "".join(stderr_buf))


#: Human-readable phase names for state-machine breadcrumbs (Feature D3).
#: Index = phase number; phase 0 is the implicit pre-flight, 1-5 mirror
#: the five auto phases (preflight, spec gate, task loop, pre-merge,
#: checklist). Stored as a tuple so callers cannot mutate it accidentally.
_PHASE_NAMES: tuple[str, ...] = (
    "pre-flight",
    "spec",
    "task loop",
    "pre-merge",
    "checklist",
)


def _emit_phase_breadcrumb(
    phase: int,
    total_phases: int,
    *,
    task_index: int | None = None,
    task_total: int | None = None,
    sub_phase: str | None = None,
) -> None:
    """Emit a one-line state-machine breadcrumb to orchestrator stderr.

    Format: ``[sbtdd] phase {p}/{t}: {phase_name} -- task {i}/{n} ({sub_phase})``.
    Task-index and sub-phase are optional for non-task-loop phases (e.g.
    pre-merge emits without ``-- task X/Y``).

    Implements Feature D3 (spec-behavior sec.2 D3.1, D3.2). Always
    flushes stderr so external observers see the line immediately even
    if Python's default buffering is line-buffered to a pipe.

    Args:
        phase: 0-indexed phase number (0..len(_PHASE_NAMES)-1).
        total_phases: Total number of phases (display denominator).
        task_index: Optional task index for task-loop phase.
        task_total: Optional task total for task-loop phase.
        sub_phase: Optional TDD sub-phase label (``red``, ``green``,
            ``refactor``, ``task-close``, ``magi-loop``, ``checklist``).
    """
    name = _PHASE_NAMES[phase] if 0 <= phase < len(_PHASE_NAMES) else f"phase-{phase}"
    line = f"[sbtdd] phase {phase}/{total_phases}: {name}"
    if task_index is not None and task_total is not None:
        suffix = f" ({sub_phase})" if sub_phase else ""
        line += f" -- task {task_index}/{task_total}{suffix}"
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def _task_progress(plan_path: Path, current_task_id: str | None) -> tuple[int | None, int | None]:
    """Return ``(task_index, task_total)`` for the active task, best-effort.

    Reads ``plan_path`` once and counts ``### Task`` headers via the same
    regex used by :mod:`_plan_ops`. ``task_index`` is 1-based: position of
    ``current_task_id`` among the headers in source order. Returns
    ``(None, None)`` on any failure (missing plan, unreadable, task id
    not found) so breadcrumb / progress wiring degrades gracefully when
    the plan layout is non-standard.

    Args:
        plan_path: Resolved path to ``planning/claude-plan-tdd.md``.
        current_task_id: Active task id from the session state.

    Returns:
        Tuple ``(index, total)`` with 1-based index, or ``(None, None)``.
    """
    if current_task_id is None:
        return (None, None)
    try:
        from _plan_ops import _TASK_HEADER_RE

        text = plan_path.read_text(encoding="utf-8")
        ids = [m.group(1) for m in _TASK_HEADER_RE.finditer(text)]
        total = len(ids)
        if total == 0:
            return (None, None)
        if current_task_id not in ids:
            return (None, total)
        return (ids.index(current_task_id) + 1, total)
    except (OSError, ValueError):
        return (None, None)


def _update_progress(
    auto_run_path: Path,
    *,
    phase: int,
    task_index: int | None,
    task_total: int | None,
    sub_phase: str | None,
) -> None:
    """Write the ``progress`` field of ``auto-run.json`` atomically.

    Mirrors the atomic-write pattern of :func:`state_file.save` and
    :func:`_write_auto_run_audit` (tmp file + ``os.replace``). A
    concurrent reader sees either the prior payload or the new one,
    never a torn JSON document (Feature D4 / spec-behavior sec.2 D4.1).

    The file may already contain other top-level keys (``schema_version``,
    ``auto_started_at``, etc.); they are preserved unchanged. When the
    file does not exist, an empty dict is the starting point so the
    helper is safe to call even before :func:`_write_auto_run_audit`.

    .. note:: **Single-writer assumption (intentional, MAGI iter 1
       finding #5).**

       The read-modify-write between :func:`pathlib.Path.read_text` and
       :func:`os.replace` is NOT lock-protected. If any other writer
       (signal handler, future ``/sbtdd status --watch`` companion,
       OS-level backup tool) updates ``auto-run.json`` between the read
       and the replace, that writer's payload is silently overwritten
       (last-writer-wins, no conflict detection).

       INV-22 (sequential-only execution) currently rules out concurrent
       SBTDD writers in production: the auto orchestrator is the only
       process that mutates ``.claude/auto-run.json`` during a run, and
       :mod:`resume_cmd` runs only after the orchestrator has exited.
       File-level locking is therefore intentionally NOT implemented in
       v0.3.0 -- it would add cross-platform complexity (``fcntl`` vs
       ``msvcrt``) for zero present benefit.

       Any future feature that introduces a second writer (parallel
       monitor, recovery hook, the v0.4.0 ``status --watch`` poller)
       MUST either remain strictly read-only on this path OR introduce
       a sentinel-file CAS protocol (e.g. write a ``.lock`` file with
       the current revision number, retry on mismatch). Updating this
       function alone is insufficient -- the contract belongs to all
       writers of ``auto-run.json``. Document the second writer in the
       spec, bump ``_AUTO_RUN_SCHEMA_VERSION``, and revisit this
       docstring before merging.

    Args:
        auto_run_path: Path to ``.claude/auto-run.json``.
        phase: 0-indexed phase number.
        task_index: Optional 1-based task index (omitted when ``None``).
        task_total: Optional total task count (omitted when ``None``).
        sub_phase: Optional sub-phase label (``red``, ``green``,
            ``refactor``, ``task-close``, ``magi-loop``, ``checklist``);
            omitted when ``None``.

    Raises:
        OSError: ``os.replace`` failed; tmp file is cleaned up before
            re-raising so nothing leaks.
    """
    if auto_run_path.exists():
        try:
            existing: dict[str, object] = json.loads(auto_run_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}
        auto_run_path.parent.mkdir(parents=True, exist_ok=True)
    # MAGI iter 1 finding #4 fix: always emit the four keys
    # ``{phase, task_index, task_total, sub_phase}`` to satisfy
    # spec sec.2 D4.2 "shape exacto" literally. ``None`` values become
    # JSON ``null`` rather than absent keys so future
    # ``/sbtdd status --watch`` consumers can rely on the shape and
    # treat ``null`` as the explicit "unknown" sentinel.
    progress: dict[str, object | None] = {
        "phase": phase,
        "task_index": task_index,
        "task_total": task_total,
        "sub_phase": sub_phase,
    }
    existing["progress"] = progress
    tmp = auto_run_path.with_suffix(auto_run_path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    # ``os.replace`` is atomic on POSIX and Windows, but on Windows it
    # can transiently fail with PermissionError when another process /
    # thread has the destination file open without FILE_SHARE_DELETE
    # (concurrent reader pattern from D4.1). Retry a small number of
    # times with a short sleep so the writer recovers from the race
    # window without breaking the atomicity contract; the reader still
    # never observes torn JSON because we never write into the target
    # path directly.
    last_err: OSError | None = None
    for _ in range(20):
        try:
            os.replace(tmp, auto_run_path)
            return
        except PermissionError as exc:
            last_err = exc
            time.sleep(0.005)
        except OSError as exc:
            last_err = exc
            break
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    assert last_err is not None
    raise last_err


def _build_run_sbtdd_argv(
    subcommand: str,
    extra_args: list[str] | None = None,
) -> list[str]:
    """Build subprocess argv for invoking ``run_sbtdd.py`` with ``python -u``.

    The ``-u`` flag disables Python output buffering at the dispatcher
    level so :func:`_stream_subprocess` reads complete lines as the
    sub-process emits them (Feature D2 / spec-behavior sec.2 D2.1).
    Centralising argv construction in a single helper means future
    callers can never forget the ``-u`` flag and break streaming.

    Args:
        subcommand: SBTDD subcommand name (``close-phase``, ``status``,
            etc.).
        extra_args: Optional list of additional CLI args appended after
            the subcommand.

    Returns:
        ``[sys.executable, "-u", "<run_sbtdd.py>", subcommand, *extra_args]``.
    """
    run_sbtdd = (Path(__file__).resolve().parent / "run_sbtdd.py").as_posix()
    argv: list[str] = [sys.executable, "-u", run_sbtdd, subcommand]
    if extra_args:
        argv.extend(extra_args)
    return argv


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
    # v0.3.0 Feature E -- per-skill model selection. Repeatable;
    # accumulates into ``ns.model_override`` as a ``list[str]`` of
    # ``<skill>:<model>`` tokens that ``_parse_model_overrides`` decodes
    # downstream. Cascade: CLAUDE.md > CLI override > plugin.local.md
    # > None (inherit session).
    p.add_argument(
        "--model-override",
        action="append",
        default=[],
        metavar="<skill>:<model>",
        help=(
            "Override the per-skill model for this run only. Repeatable. "
            "Valid skill names: implementer, spec_reviewer, code_review, "
            "magi_dispatch. Cascade: CLAUDE.md > CLI override > "
            "plugin.local.md > None (inherit session)."
        ),
    )
    return p


# ---------------------------------------------------------------------------
# v0.3.0 Feature E -- per-skill model selection (Track E, disjoint from D).
# ---------------------------------------------------------------------------

#: Canonical skill names accepted by ``--model-override <skill>:<model>``.
#: Frozen at module load: ``frozenset`` so callers cannot mutate the
#: validation set at runtime. Mirrors :data:`config._MODEL_FIELDS` (with
#: the ``_model`` suffix stripped) -- the field map in ``_resolve_model``
#: stays the source of truth for the suffix translation.
_VALID_MODEL_OVERRIDE_SKILLS: frozenset[str] = frozenset(
    {"implementer", "spec_reviewer", "code_review", "magi_dispatch"}
)


def _parse_model_overrides(raw_values: list[str]) -> dict[str, str]:
    """Parse repeated ``--model-override <skill>:<model>`` CLI tokens.

    Returns a dict mapping skill name (one of the four canonical names in
    :data:`_VALID_MODEL_OVERRIDE_SKILLS`) to model ID. Raises
    :class:`ValidationError` on missing separator or unknown skill name;
    the dispatcher in :mod:`run_sbtdd` converts ValidationError to exit
    code 1 (USER_ERROR) per sec.S.11.1.

    Args:
        raw_values: List of ``<skill>:<model>`` tokens collected from
            ``argparse.action='append'``. May be empty.

    Returns:
        Dict ``{skill_name: model_id}``; empty when ``raw_values`` is empty.

    Raises:
        ValidationError: A token has no ``:`` separator OR the skill name
            is not in :data:`_VALID_MODEL_OVERRIDE_SKILLS`.
    """
    out: dict[str, str] = {}
    for raw in raw_values:
        if ":" not in raw:
            raise ValidationError(f"--model-override expects '<skill>:<model>'; got {raw!r}")
        skill, _, model = raw.partition(":")
        if skill not in _VALID_MODEL_OVERRIDE_SKILLS:
            raise ValidationError(
                f"invalid --model-override skill name {skill!r}. Valid: "
                f"{', '.join(sorted(_VALID_MODEL_OVERRIDE_SKILLS))}"
            )
        out[skill] = model
    return out


def _resolve_model(
    skill: str,
    config: PluginConfig,
    cli_overrides: dict[str, str],
) -> str | None:
    """Resolve the effective configured model for a skill at dispatch time.

    Cascade: CLI override > plugin.local.md field > None. INV-0
    (``~/.claude/CLAUDE.md`` global pin) is enforced downstream by each
    dispatch module's ``_apply_inv0_model_check`` -- this helper does NOT
    re-implement INV-0 because that gate must run on every invocation
    regardless of whether the cascade landed on CLI or config.

    Args:
        skill: Canonical skill name (one of
            :data:`_VALID_MODEL_OVERRIDE_SKILLS`).
        config: Loaded :class:`PluginConfig`; carries the four
            ``*_model`` fields from ``plugin.local.md``.
        cli_overrides: Pre-parsed ``--model-override`` map (output of
            :func:`_parse_model_overrides`).

    Returns:
        The model ID to pass to the dispatch module's ``model=`` kwarg,
        or ``None`` when neither layer of the cascade set a value (the
        plugin then inherits the session's default model — byte-identical
        to v0.2.x behaviour).
    """
    if skill in cli_overrides:
        return cli_overrides[skill]
    field_map: dict[str, str | None] = {
        "implementer": config.implementer_model,
        "spec_reviewer": config.spec_reviewer_model,
        "code_review": config.code_review_model,
        "magi_dispatch": config.magi_dispatch_model,
    }
    return field_map.get(skill)


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


def _run_spec_review_gate(
    task_id: str,
    plan_path: Path,
    root: Path,
    *,
    model: str | None = None,
) -> None:
    """Dispatch the spec-reviewer before :func:`close_task_cmd.mark_and_advance` (INV-31).

    Thin wrapper around :func:`spec_review_dispatch.dispatch_spec_reviewer`
    that flattens :func:`_phase2_task_loop`'s inner ``else`` branch: callers
    see a single gate line instead of a multi-kwarg dispatch dict. The real
    dispatcher raises :class:`SpecReviewError` on non-approval after the
    safety-valve iteration cap; the raise propagates to
    :func:`_phase2_task_loop`'s ``except SpecReviewError`` branch, which
    records the blocked task count in ``.claude/auto-run.json`` before
    re-raising.

    Mirrors :func:`close_task_cmd._run_spec_review` for the interactive
    task-close path; both share the INV-31 contract. Auto relies on the
    dispatcher raising (no defensive ``result.approved`` check) because
    the try/except already captures the failure and the stub fixtures
    exercising auto drive :class:`SpecReviewError` directly to cover the
    blocked-advance test path (see
    ``tests/test_auto_cmd_spec_review.py``).

    Args:
        task_id: Plan task id whose diff is being reviewed.
        plan_path: Path to the approved plan.
        root: Project root directory.
        model: Optional Claude model ID (v0.3.0 Feature E). When set,
            forwarded to the dispatcher's ``model=`` kwarg for the
            INV-0 + ``--model`` injection cascade. When ``None`` (default)
            the kwarg is omitted entirely so test stubs that pre-date
            v0.3.0 keep working.
    """
    if model is None:
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id=task_id,
            plan_path=plan_path,
            repo_root=root,
        )
    else:
        spec_review_dispatch.dispatch_spec_reviewer(
            task_id=task_id,
            plan_path=plan_path,
            repo_root=root,
            model=model,
        )


#: Maximum outer iterations for the B6 feedback loop, mirroring INV-11
#: cadence (Checkpoint 2 / pre-merge Loop 2 also cap at 3). Each outer
#: iteration consists of: dispatch reviewer -> route findings via
#: ``/receiving-code-review`` -> mini-cycle TDD fix per accepted finding ->
#: re-dispatch. After three iterations without convergence the helper
#: re-raises :class:`SpecReviewError` carrying the rejected-finding
#: history so operators can diagnose without grepping logs.
_B6_MAX_FEEDBACK_ITERATIONS: int = 3


def _stage_tracked_changes(root: Path) -> bool:
    """Return ``True`` iff ``git`` reports staged content after auto-staging.

    The mini-cycle relies on the implementer subagent (via
    ``/test-driven-development``) to author the diff for each phase. When
    the subagent edits files but never stages them (observed v0.2 auto runs
    F2/G2 -- see CHANGELOG 0.1.6) we run ``git add -u`` to capture
    tracked-file modifications, mirroring :func:`_phase2_task_loop`'s case-2
    recovery. Untracked files are deliberately NOT staged here -- that
    matches the existing scope of ``git add -u`` and keeps the mini-cycle
    from sweeping unrelated artefacts into the commit.

    Returns ``True`` when staging produced a non-empty staged diff (commit
    will succeed); ``False`` when nothing is stageable (commit must fall
    back to ``--allow-empty`` so the cycle can still progress).
    """
    subprocess_utils.run_with_timeout(["git", "add", "-u"], timeout=30, cwd=str(root))
    diff = subprocess_utils.run_with_timeout(
        ["git", "diff", "--cached", "--name-only"], timeout=10, capture=True, cwd=str(root)
    )
    return bool(diff.stdout and diff.stdout.strip())


def _commit_mini_cycle_phase(
    root: Path,
    task_id: str,
    finding: str,
    prefix: str,
    phase_label: str,
) -> None:
    """Commit one mini-cycle phase via :func:`commits.create`.

    Routes through ``commits.create`` so prefix validation + English-only +
    no-AI-refs guards fire (mandatory per the v0.2.1 task brief). When
    nothing is staged after :func:`_stage_tracked_changes` returns
    ``False`` we fall back to ``git commit --allow-empty`` so the cycle
    progresses even if the implementer subagent collapsed the phase work
    into an earlier commit. The empty marker mirrors the convention from
    ``_phase2_task_loop``'s case-3 recovery.

    Args:
        root: Project root directory.
        task_id: Plan task id; surfaced in the commit message.
        finding: Spec-reviewer finding text driving the mini-cycle.
        prefix: ``test:`` / ``fix:`` / ``refactor:`` per the mini-cycle
            phase being closed.
        phase_label: Human-readable phase tag (``red`` / ``green`` /
            ``refactor``) used in the commit message.

    Raises:
        CommitError: Both the staged-content commit and the
            ``--allow-empty`` fallback failed; bubble up to the caller.
    """
    has_staged = _stage_tracked_changes(root)
    message = (
        f"{phase_label} for spec-review finding on task {task_id}: {finding}"
        if has_staged
        else f"{phase_label} for spec-review finding on task {task_id}: {finding} "
        f"(no-op; phase collapsed into earlier commit)"
    )
    if has_staged:
        # Call via module attribute (not the bound ``commit_create`` import)
        # so tests can ``monkeypatch.setattr(commits, "create", ...)`` to
        # spy on mini-cycle commits without losing prefix validation.
        commits.create(prefix, message, cwd=str(root))
        return
    # Empty marker: ``commits.create`` would refuse via git's "nothing to
    # commit", so use a direct ``git commit --allow-empty`` while keeping
    # the prefix + message validation by composing the message ourselves
    # through ``commits.create`` semantics below. Falling back to the raw
    # subprocess preserves the cycle's atomicity contract: every phase
    # produces exactly one commit, success or empty marker.
    full_message = f"{prefix}: {message}"
    r = subprocess_utils.run_with_timeout(
        ["git", "commit", "--allow-empty", "-m", full_message],
        timeout=30,
        cwd=str(root),
    )
    if r.returncode != 0:
        from errors import CommitError as _CommitError

        raise _CommitError(
            f"git commit --allow-empty failed (returncode={r.returncode}): {r.stderr}"
        )


def _run_mini_cycle_for_finding(
    root: Path,
    task_id: str,
    finding: str,
    retries: int,
    *,
    implementer_model: str | None = None,
) -> None:
    """Run one ``test:`` -> ``fix:`` -> ``refactor:`` mini-cycle per finding.

    Each phase invokes ``/test-driven-development`` (with the finding text
    as narrative context so the implementer subagent knows what to fix),
    runs ``/verification-before-completion`` with the same retry budget as
    the surrounding task-loop phases, then commits via
    :func:`_commit_mini_cycle_phase` so prefix + message validation
    happens through ``commits.create``.

    The mini-cycle is sequential and atomic: three commits land per finding
    in strict ``test`` -> ``fix`` -> ``refactor`` order. Empty phases (the
    implementer subagent collapsed work) produce ``--allow-empty`` markers
    instead of skipping so the cycle's commit count stays predictable for
    audit purposes.

    Args:
        root: Project root directory.
        task_id: Plan task id (carried into the commit messages).
        finding: Verbatim accepted finding from ``/receiving-code-review``.
        retries: Verification retry budget per phase, matching the
            surrounding ``_phase2_task_loop`` value.
        implementer_model: Optional v0.3.0 Feature E per-skill model
            ID forwarded to the ``test_driven_development`` dispatcher.
            ``None`` (default) preserves the v0.2.x argv shape.
    """
    phase_prefix_pairs: tuple[tuple[str, str], ...] = (
        ("red", COMMIT_PREFIX_MAP["red"]),
        ("green", COMMIT_PREFIX_MAP["green_fix"]),
        ("refactor", COMMIT_PREFIX_MAP["refactor"]),
    )
    for phase_label, prefix in phase_prefix_pairs:
        # v0.3.0 Feature E: omit model kwargs entirely when None so test
        # stubs pre-dating v0.3.0 keep accepting the call signature.
        if implementer_model is None:
            superpowers_dispatch.test_driven_development(
                args=[f"--phase={phase_label}", f"--finding={finding}", f"--task-id={task_id}"],
                cwd=str(root),
            )
        else:
            superpowers_dispatch.test_driven_development(
                args=[f"--phase={phase_label}", f"--finding={finding}", f"--task-id={task_id}"],
                cwd=str(root),
                model=implementer_model,
                skill_field_name="implementer_model",
            )
        _run_verification_with_retries(root, retries)
        _commit_mini_cycle_phase(root, task_id, finding, prefix, phase_label)


def _apply_spec_review_findings_via_mini_cycle(
    initial_error: "SpecReviewError",
    task_id: str,
    plan_path: Path,
    root: Path,
    cfg: PluginConfig,
    ns: argparse.Namespace,
    spec_review_budget_seconds: int,
    spec_review_elapsed: float,
) -> tuple[float, bool]:
    """Run the v0.2.1 B6 auto-feedback loop for one task close (INV-31 expanded).

    Spec-base §2.2 promised: on spec-reviewer ``issues``, route findings
    through ``/receiving-code-review`` -> mini-cycle TDD fix per accepted
    finding -> re-dispatch reviewer -> loop up to the safety valve. v0.2.0
    deferred this; v0.2.1 ships it.

    Algorithm (one outer iteration per dispatched reviewer call):

    1. Route the failing-iteration's ``issues`` through
       ``/receiving-code-review`` with the
       :data:`receiving_review_dispatch.RECEIVING_REVIEW_FORMAT_CONTRACT`
       prompt so the subagent's reply ends with ``## Accepted`` /
       ``## Rejected`` markdown sections.
    2. Parse accepted vs rejected via
       :func:`receiving_review_dispatch.parse_receiving_review`.
    3. For each accepted finding, run
       :func:`_run_mini_cycle_for_finding` so 3 commits
       (``test:`` -> ``fix:`` -> ``refactor:``) land per finding through
       :func:`commits.create` (prefix + English-only validation fires).
       Rejected findings produce no commits -- their rationale is the
       implicit feedback for the next reviewer dispatch.
    4. Re-dispatch :func:`spec_review_dispatch.dispatch_spec_reviewer` on
       the now-mutated diff. On ``SpecReviewError`` increment the outer
       iteration count and recurse; on approval return clean.
    5. After :data:`_B6_MAX_FEEDBACK_ITERATIONS` outer iterations without
       approval, re-raise the last :class:`SpecReviewError` so the
       :func:`_phase2_task_loop` audit branch records the failure.

    Spec-review budget: every reviewer dispatch in the outer loop charges
    the same ``cfg.auto_max_spec_review_seconds`` budget that the primary
    dispatch consumes. When the budget exhausts mid-loop the helper
    returns ``True`` in the second tuple slot so the caller can continue
    with ``--skip-spec-review`` semantics for downstream tasks.

    Args:
        initial_error: The :class:`SpecReviewError` from the first reviewer
            dispatch; its ``issues`` seed iteration 1 of the feedback loop.
        task_id: Plan task id whose close is being unblocked.
        plan_path: Path to the approved plan (forwarded to the dispatcher).
        root: Project root directory.
        cfg: Plugin configuration (carries the verification retries).
        ns: Parsed argparse namespace (forwarded for compat with future
            override flags).
        spec_review_budget_seconds: Cumulative reviewer budget for the
            run (``cfg.auto_max_spec_review_seconds``).
        spec_review_elapsed: Elapsed reviewer wall-time before this
            helper was invoked.

    Returns:
        ``(updated_elapsed, budget_exhausted)``. When ``budget_exhausted``
        is ``True`` the caller MUST stop dispatching the reviewer for
        subsequent tasks (matching the v0.2 cost guardrail breadcrumb).

    Raises:
        SpecReviewError: Outer safety valve exhausted without convergence;
            payload preserves the most recent ``issues`` and a synthesized
            ``rejected_history`` of cumulative rejections.
    """
    retries = (
        ns.verification_retries
        if ns.verification_retries is not None
        else cfg.auto_verification_retries
    )
    # v0.3.0 Feature E -- resolve per-skill models once for the helper's
    # lifetime so the same cascade decision applies to every dispatch in
    # the outer feedback loop. ``ns.model_override_map`` is populated by
    # ``main`` from ``--model-override`` flags; absent in test fixtures
    # that build a bare Namespace, so default to {}.
    cli_overrides = getattr(ns, "model_override_map", {}) or {}
    implementer_model = _resolve_model("implementer", cfg, cli_overrides)
    spec_reviewer_model = _resolve_model("spec_reviewer", cfg, cli_overrides)
    code_review_model = _resolve_model("code_review", cfg, cli_overrides)
    last_error: "SpecReviewError" = initial_error
    cumulative_rejections: list[str] = []
    elapsed = spec_review_elapsed
    for outer_iter in range(1, _B6_MAX_FEEDBACK_ITERATIONS):
        # Route the current iteration's issues through /receiving-code-review.
        review_args = receiving_review_dispatch.conditions_to_skill_args(last_error.issues)
        # v0.3.0 Feature E: omit model kwargs when None so stubs pre-dating
        # v0.3.0 keep accepting the call signature.
        if code_review_model is None:
            review_result = superpowers_dispatch.receiving_code_review(
                args=review_args,
                cwd=str(root),
            )
        else:
            review_result = superpowers_dispatch.receiving_code_review(
                args=review_args,
                cwd=str(root),
                model=code_review_model,
                skill_field_name="code_review_model",
            )
        accepted, rejected = receiving_review_dispatch.parse_receiving_review(review_result)
        if not accepted and not rejected:
            # The skill produced no decisions -- treat as a hard stop. This
            # mirrors the ``_loop2`` behavior where empty parse output is a
            # ValidationError. Re-raising the underlying SpecReviewError
            # keeps the audit trail uniform with the v0.2 hard-block path.
            raise last_error
        cumulative_rejections.extend(f"iter {outer_iter} rejected: {r}" for r in rejected)
        # Run a mini-cycle per accepted finding so the next reviewer
        # dispatch sees a mutated diff (the input change that the v0.2
        # baseline was missing).
        for finding in accepted:
            _run_mini_cycle_for_finding(
                root, task_id, finding, retries, implementer_model=implementer_model
            )
        # Re-dispatch reviewer; budget-track the call.
        if elapsed >= spec_review_budget_seconds:
            # Budget exhausted mid-loop: stop here and signal the caller
            # to skip downstream reviewer calls. The task close still
            # advances because the mini-cycle commits proved (or marked)
            # the accepted findings, mirroring the v0.2 cost-guardrail
            # contract.
            return elapsed, True
        review_started = time.monotonic()
        try:
            if spec_reviewer_model is None:
                spec_review_dispatch.dispatch_spec_reviewer(
                    task_id=task_id,
                    plan_path=plan_path,
                    repo_root=root,
                )
            else:
                spec_review_dispatch.dispatch_spec_reviewer(
                    task_id=task_id,
                    plan_path=plan_path,
                    repo_root=root,
                    model=spec_reviewer_model,
                )
        except SpecReviewError as exc:
            last_error = exc
            elapsed += time.monotonic() - review_started
            continue
        # Re-dispatch returned clean -> task may close.
        elapsed += time.monotonic() - review_started
        return elapsed, False
    # Outer safety valve exhausted: re-raise with cumulative rejection history.
    rejection_history_text = "; ".join(cumulative_rejections) or "(none recorded)"
    raise SpecReviewError(
        f"B6 feedback loop exhausted after {_B6_MAX_FEEDBACK_ITERATIONS} outer "
        f"iterations for task {task_id}; rejection history: {rejection_history_text}",
        task_id=task_id,
        iteration=_B6_MAX_FEEDBACK_ITERATIONS,
        issues=last_error.issues,
    )


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

    .. note::
       **v0.1.x limitation (pending v0.2 Feature B redesign).**
       The current call shape ``test_driven_development(args=[f"--phase={phase}"])``
       forwards the phase as a narrative hint inside the ``claude -p`` prompt.
       The superpowers ``/test-driven-development`` skill is prose-only and does
       NOT formally define a ``--phase`` flag; it interprets the hint via
       Claude's natural-language understanding. No task context (task id, plan
       path, file list, acceptance criteria) is passed explicitly -- the
       sub-session has to discover context by reading
       ``planning/claude-plan-tdd.md`` and ``.claude/session-state.json`` on
       its own. This is workable via ``cwd=str(root)`` but fragile. **Feature
       B of v0.2** (``spec_review_dispatch`` + task-loop redesign) will
       replace this with an explicit task-context prompt builder. Until then,
       auto's task loop relies on the sub-session's discovery heuristics.

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
    # Cost guardrail (v0.2.1, MAGI Loop 2 v0.2 pre-merge WARNING #11):
    # cumulative spec-reviewer wall-time across the run is capped by
    # ``cfg.auto_max_spec_review_seconds`` (default 3600s = 1h). When the
    # budget is exhausted before a task's reviewer call, that task proceeds
    # with ``--skip-spec-review`` semantics (no dispatch) and a stderr
    # breadcrumb is emitted exactly once. Subsequent tasks continue to
    # skip; ``mark_and_advance`` still runs so the plan progresses.
    spec_review_budget_seconds = cfg.auto_max_spec_review_seconds
    spec_review_elapsed = 0.0
    spec_review_breadcrumb_emitted = False
    # v0.3.0 Feature E -- resolve per-skill model IDs once per task-loop
    # entry; the cascade (CLI override > plugin.local.md > None) is the
    # same for every dispatch in the loop. INV-0 fires inside each
    # dispatch module so the cascade output here is the *configured*
    # model, not necessarily the one ultimately used.
    cli_overrides = getattr(ns, "model_override_map", {}) or {}
    implementer_model = _resolve_model("implementer", cfg, cli_overrides)
    spec_reviewer_model = _resolve_model("spec_reviewer", cfg, cli_overrides)
    # Feature D3 + D4: emit one entry breadcrumb for phase 2 ("task
    # loop") so operators see the run move past pre-flight before the
    # first subagent dispatch, and persist progress atomically into
    # ``auto-run.json`` so a concurrent reader can poll the run state
    # without racing the writer. ``_task_progress`` is best-effort; on
    # failure we still emit the phase line without the task counter.
    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
    _emit_phase_breadcrumb(
        phase=2,
        total_phases=5,
        task_index=_t_idx,
        task_total=_t_total,
        sub_phase=current.current_phase,
    )
    _update_progress(
        auto_run,
        phase=2,
        task_index=_t_idx,
        task_total=_t_total,
        sub_phase=current.current_phase,
    )
    try:
        while current.current_task_id is not None:
            phase_idx = (
                _PHASE_ORDER.index(current.current_phase)
                if current.current_phase in _PHASE_ORDER
                else 0
            )
            for phase in _PHASE_ORDER[phase_idx:]:
                pre_phase_sha = _current_head_sha(root)
                # v0.3.0 Feature E: gate on ``implementer_model is None``
                # so the kwargs are omitted entirely when the cascade
                # resolved to None. Stubs that do NOT accept the new
                # kwargs (test fixtures pre-dating v0.3.0) keep working.
                if implementer_model is None:
                    superpowers_dispatch.test_driven_development(
                        args=[f"--phase={phase}"], cwd=str(root)
                    )
                else:
                    superpowers_dispatch.test_driven_development(
                        args=[f"--phase={phase}"],
                        cwd=str(root),
                        model=implementer_model,
                        skill_field_name="implementer_model",
                    )
                _run_verification_with_retries(root, retries)
                prefix = _phase_prefix(phase)
                try:
                    commit_create(
                        prefix, f"{phase} for task {current.current_task_id}", cwd=str(root)
                    )
                except CommitError:
                    # ``git commit`` returns rc=1 with "nothing to commit" for
                    # three distinct reasons we must handle differently
                    # (2026-04-24 observations):
                    #
                    # 1. HEAD advanced: implementer committed the phase directly
                    #    (plan-prescribed ``git commit``). That commit IS the
                    #    phase close; proceed with state advance.
                    # 2. HEAD unchanged AND ``git status`` shows tracked-file
                    #    modifications: implementer edited files but never
                    #    staged. ``git add -u`` captures the modifications (no
                    #    untracked files, so this stays scoped) and a retry
                    #    commits the real phase work.
                    # 3. HEAD unchanged AND nothing to stage: implementer
                    #    collapsed phases (e.g., did red+green together in an
                    #    earlier commit, leaving the current phase with no
                    #    residual work). Record an empty commit so auto's
                    #    state still advances; verification has already proven
                    #    the phase's acceptance criterion is met.
                    if _current_head_sha(root) == pre_phase_sha:
                        # Case 2: stage tracked-file modifications and retry.
                        subprocess_utils.run_with_timeout(
                            ["git", "add", "-u"], timeout=30, cwd=str(root)
                        )
                        try:
                            commit_create(
                                prefix,
                                f"{phase} for task {current.current_task_id}",
                                cwd=str(root),
                            )
                        except CommitError:
                            # Case 3: still nothing to commit -> empty marker
                            # commit mirroring the plan-prescribed
                            # refactor-phase --allow-empty convention.
                            r = subprocess_utils.run_with_timeout(
                                [
                                    "git",
                                    "commit",
                                    "--allow-empty",
                                    "-m",
                                    f"{prefix}: {phase} for task "
                                    f"{current.current_task_id} "
                                    f"(no-op; phase collapsed into earlier commit)",
                                ],
                                timeout=30,
                                cwd=str(root),
                            )
                            if r.returncode != 0:
                                raise
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
                    # Feature D3 + D4: breadcrumb + progress AFTER state
                    # save, BEFORE the next subagent dispatch (red->green
                    # or green->refactor).
                    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
                    _emit_phase_breadcrumb(
                        phase=2,
                        total_phases=5,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=next_phase,
                    )
                    _update_progress(
                        auto_run,
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=next_phase,
                    )
                else:
                    # H6 (INV-31): spec-reviewer gate BEFORE mark_and_advance.
                    assert current.current_task_id is not None
                    if spec_review_elapsed >= spec_review_budget_seconds:
                        if not spec_review_breadcrumb_emitted:
                            sys.stderr.write(
                                f"[auto] spec-review budget "
                                f"{spec_review_budget_seconds}s exceeded; "
                                f"remaining tasks proceed with "
                                f"--skip-spec-review\n"
                            )
                            spec_review_breadcrumb_emitted = True
                    else:
                        review_started = time.monotonic()
                        try:
                            _run_spec_review_gate(
                                current.current_task_id,
                                plan_path,
                                root,
                                model=spec_reviewer_model,
                            )
                            spec_review_elapsed += time.monotonic() - review_started
                        except SpecReviewError as exc:
                            # B6 (v0.2.1): spec-reviewer raised; route findings
                            # through /receiving-code-review + mini-cycle TDD
                            # fix per accepted finding + re-dispatch reviewer
                            # up to _B6_MAX_FEEDBACK_ITERATIONS. Helper either
                            # converges (returns) or re-raises SpecReviewError
                            # which propagates to the outer except branch.
                            spec_review_elapsed += time.monotonic() - review_started
                            spec_review_elapsed, budget_exhausted = (
                                _apply_spec_review_findings_via_mini_cycle(
                                    exc,
                                    current.current_task_id,
                                    plan_path,
                                    root,
                                    cfg,
                                    ns,
                                    spec_review_budget_seconds,
                                    spec_review_elapsed,
                                )
                            )
                            if budget_exhausted and not spec_review_breadcrumb_emitted:
                                sys.stderr.write(
                                    f"[auto] spec-review budget "
                                    f"{spec_review_budget_seconds}s exceeded "
                                    f"during B6 feedback loop; remaining tasks "
                                    f"proceed with --skip-spec-review\n"
                                )
                                spec_review_breadcrumb_emitted = True
                    # W1: delegate to public helper in close_task_cmd instead
                    # of duplicating the entire flip / commit chore / advance
                    # sequence.
                    current = close_task_cmd.mark_and_advance(current, root)
                    tasks_completed += 1
                    # Feature D3 + D4: breadcrumb + progress AFTER
                    # mark_and_advance, BEFORE the first dispatch on the
                    # new task. ``current.current_phase`` is "red" (or
                    # "done" when the plan completes); both are valid
                    # sub_phase labels for the breadcrumb.
                    _t_idx, _t_total = _task_progress(plan_path, current.current_task_id)
                    _emit_phase_breadcrumb(
                        phase=2,
                        total_phases=5,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=current.current_phase,
                    )
                    _update_progress(
                        auto_run,
                        phase=2,
                        task_index=_t_idx,
                        task_total=_t_total,
                        sub_phase=current.current_phase,
                    )
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
    except SpecReviewError:
        # INV-31 audit: on safety-valve exhaustion, persist the partial
        # tasks_completed count + error classifier BEFORE re-raising so
        # operators can diagnose without grepping logs. Mirrors the
        # MAGIGateError audit path in ``main``.
        _write_auto_run_audit(
            auto_run,
            AutoRunAudit(
                schema_version=_AUTO_RUN_SCHEMA_VERSION,
                auto_started_at=started_at,
                auto_finished_at=_now_iso(),
                status="spec_review_issues",
                verdict=None,
                degraded=None,
                accepted_conditions=0,
                rejected_conditions=0,
                tasks_completed=tasks_completed,
                error="SpecReviewError",
            ),
        )
        raise
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

    Atomicity contract (MAGI Loop 2 D iter 1 Caspar): the on-disk file
    is always either the fully-formed previous audit or the fully-formed
    new audit -- never a truncated half-write. A process killed between
    the tmp-write and the ``os.replace`` call leaves the previous
    ``auto-run.json`` intact, preserving the "last-persisted audit =
    truth" invariant that ``resume_cmd`` relies on. The pattern mirrors
    :func:`state_file.save` to keep the two state-on-disk writers
    consistent.

    Args:
        path: Absolute path to ``auto-run.json`` (parent is created).
        payload: :class:`AutoRunAudit` instance, validated before write.

    Raises:
        TypeError: ``payload`` is not an :class:`AutoRunAudit` instance.
        ValidationError: ``payload.validate_schema`` failed.
        OSError: ``os.replace`` failed; tmp file cleaned up before
            re-raising so nothing leaks.
    """
    if not isinstance(payload, AutoRunAudit):
        raise TypeError(
            f"_write_auto_run_audit requires AutoRunAudit, got {type(payload).__name__}"
        )
    payload.validate_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write via tmp + os.replace (MAGI Loop 2 D iter 1 Caspar):
    # mirrors state_file.save so a process killed mid-write never leaves
    # a corrupted auto-run.json. If os.replace fails the tmp file is
    # cleaned up before the error propagates so nothing leaks.
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload.to_dict(), indent=2), encoding="utf-8")
    try:
        os.replace(tmp, path)  # atomic on POSIX and Windows
    except OSError:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    """Entry point for /sbtdd auto (shoot-and-forget full-cycle)."""
    parser = _build_parser()
    ns = parser.parse_args(argv)
    # v0.3.0 Feature E -- decode --model-override tokens into a dict and
    # stash on the namespace so downstream phases can read it without
    # re-parsing. Malformed tokens raise ValidationError BEFORE any
    # filesystem / subprocess work so the dispatcher (run_sbtdd.py)
    # can map them to exit 1 (USER_ERROR) without leaving partial state.
    ns.model_override_map = _parse_model_overrides(ns.model_override or [])
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
    iter 2 Caspar -- raise-safe audit). Missing file returns 0 silently
    (expected cold-start path). Malformed content still returns 0 but
    emits a stderr diagnostic so operators see that a previously-valid
    audit has regressed (MAGI Loop 2 D iter 1 Balthasar WARNING --
    silent fallback could otherwise mask real corruption).
    """
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text("utf-8"))
        return int(data.get("tasks_completed", 0))
    except (json.JSONDecodeError, ValueError, TypeError, OSError) as exc:
        # TypeError covers `int({...})` when a caller writes a nested
        # object where a scalar was expected; the remaining three cover
        # unreadable bytes / malformed JSON / non-numeric content. All
        # four are "something went wrong -- surface it on stderr but do
        # not abort the auto-run-error path".
        sys.stderr.write(
            f"warning: failed to parse {path}: {type(exc).__name__}: {exc}. "
            f"Falling back to tasks_completed=0 for auto-run audit. "
            f"If this file was previously valid, the run may have been "
            f"interrupted mid-write or corrupted externally.\n"
        )
        return 0


run = main
