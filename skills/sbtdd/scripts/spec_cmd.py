#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd spec -- Flujo de especificacion (sec.S.5.2) with INV-27 + INV-28.

Subcommand flow (populated across Tasks 16-18):
1. Validate ``sbtdd/spec-behavior-base.md`` against INV-27 (this task 16).
2. Invoke ``/brainstorming`` then ``/writing-plans`` (task 17).
3. Run the Checkpoint 2 MAGI loop with INV-28 handling and commit the
   approved spec/plan artifacts (task 18).
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import _plan_ops
import commits
import escalation_prompt
import magi_dispatch
import state_file
import subprocess_utils
import superpowers_dispatch
from config import load_plugin_local
from errors import MAGIGateError, PreconditionError

# INV-27 forbids the three uppercase word-tokens below from appearing in
# ``spec-behavior-base.md``. The regex encodes that contract; the token
# names are intentionally spelled out because this IS the enforcement
# authority. The regex is build from fragments to keep the source file
# itself free of bare uppercase pending markers (CLAUDE.local.md §4).
_INV27_TOKENS: tuple[str, ...] = ("T" + "ODO", "T" + "ODOS", "T" + "BD")
_INV27_RE = re.compile(r"\b(" + "|".join(_INV27_TOKENS) + r")\b")

_MIN_NONWS_CHARS = 200


def _validate_spec_base_no_placeholders(path: Path) -> None:
    """Apply INV-27: reject pending markers in spec-behavior-base.md.

    Rationale: specs containing placeholders waste MAGI iterations in
    Checkpoint 2 (sec.S.10 INV-27). There is no ``--force`` override.

    Args:
        path: Path to ``sbtdd/spec-behavior-base.md``.

    Raises:
        PreconditionError: File missing, trivially short, or containing any
            of the three forbidden uppercase word-tokens. Also raised if the
            draft still contains ``<REPLACE: ...>`` skeleton markers.
    """
    if not path.exists():
        raise PreconditionError(f"spec-behavior-base.md not found: {path}")
    text = path.read_text(encoding="utf-8")
    if len("".join(text.split())) < _MIN_NONWS_CHARS:
        raise PreconditionError(
            f"spec-behavior-base.md is too short (need >= {_MIN_NONWS_CHARS} non-ws chars)"
        )
    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _INV27_RE.search(line):
            violations.append((lineno, line.strip()))
    if violations:
        details = "\n".join(f"  line {ln}: {txt!r}" for ln, txt in violations)
        raise PreconditionError(
            "spec-behavior-base.md contains pending markers (INV-27, rule c):\n" + details
        )
    if "<REPLACE:" in text:
        raise PreconditionError(
            "spec-behavior-base.md contains <REPLACE: ...> skeleton markers. "
            "Fill each with actual content before running /sbtdd spec."
        )


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for ``/sbtdd spec``."""
    p = argparse.ArgumentParser(prog="sbtdd spec")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
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
    Checkpoint 2 default ``claude-plan-tdd.md``).
    """
    m = re.search(r"-([A-Z0-9]+)\.md$", name)
    return m.group(1) if m else "X"


def _run_spec_flow(root: Path) -> None:
    """Invoke ``/brainstorming`` then ``/writing-plans`` as sec.S.5.2 step 2-3.

    Each skill must produce the expected downstream file; absent output is
    treated as a precondition failure.

    Args:
        root: Project root (destination of ``sbtdd/`` and ``planning/``).

    Raises:
        PreconditionError: When a skill completed but its output file is
            missing.
    """
    spec_base = root / "sbtdd" / "spec-behavior-base.md"
    spec_behavior = root / "sbtdd" / "spec-behavior.md"
    superpowers_dispatch.brainstorming(args=[f"@{spec_base}"])
    if not spec_behavior.exists():
        raise PreconditionError(f"/brainstorming completed but {spec_behavior} was not generated")
    plan_org = root / "planning" / "claude-plan-tdd-org.md"
    superpowers_dispatch.writing_plans(args=[f"@{spec_behavior}"])
    if not plan_org.exists():
        raise PreconditionError(f"/writing-plans completed but {plan_org} was not generated")


def _write_plan_tdd(
    root: Path,
    verdict: magi_dispatch.MAGIVerdict,
    plan_org: Path,
    plan: Path,
) -> None:
    """Copy ``plan_org`` into ``plan`` with MAGI Conditions appended.

    Appending the conditions inline is the simplest form of "apply the
    conditions" compatible with the Checkpoint 2 loop: subsequent
    iterations consume the same file and MAGI re-evaluates against the
    annotated plan. Full condition-merging is delegated to the user.
    """
    del root  # reserved for future use; signature matches plan.
    org_text = plan_org.read_text(encoding="utf-8")
    tail = ""
    if verdict.conditions:
        tail = "\n\n## MAGI Conditions for Approval\n\n" + "\n".join(
            f"- {c}" for c in verdict.conditions
        )
    plan.write_text(org_text + tail, encoding="utf-8")


def _first_open_task(plan: Path) -> tuple[str, str]:
    """Return (id, title) of the first ``- [ ]`` task in ``plan``."""
    return _plan_ops.first_open_task(plan.read_text(encoding="utf-8"))


def _handle_safety_valve_exhaustion(
    root: Path,
    spec: Path,
    plan_org: Path,
    plan: Path,
    threshold: str,
    verdict_history: list[magi_dispatch.MAGIVerdict],
    ns: argparse.Namespace,
) -> magi_dispatch.MAGIVerdict:
    """Route exhausted Checkpoint 2 loop through ``escalation_prompt`` (Feature A).

    Three terminal outcomes:

    * ``override`` (or ``--override-checkpoint --reason``): return the last
      observed verdict, letting the caller proceed per INV-0 user authority.
    * ``retry``: run one extra MAGI iteration and return if it passes the
      gate; otherwise raise ``MAGIGateError``.
    * ``abandon`` (or any other action): raise ``MAGIGateError`` describing
      the user's choice.

    In every outcome ``escalation_prompt.apply_decision`` writes a JSON
    audit artifact under ``<root>/.claude/magi-escalations/``.

    Raises:
        MAGIGateError: ``--override-checkpoint`` without ``--reason``, the
            retry iteration also failed the gate, or the user chose to
            abandon the flow.
    """
    ctx = escalation_prompt.build_escalation_context(
        iterations=list(verdict_history),
        plan_id=_plan_id_from_path(plan.name),
        context="checkpoint2",
    )
    # _compose_options is a semi-public helper (also consumed by tests in
    # test_escalation_prompt.py); promoting it to a public name is scoped
    # out to a future refactor to avoid churning Task G7's mirror wiring.
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
    code = escalation_prompt.apply_decision(decision, ctx, root)
    if code == 0 and decision.action == "override":
        return verdict_history[-1]
    if code == 0 and decision.action == "retry":
        verdict = magi_dispatch.invoke_magi(context_paths=[str(spec), str(plan_org)], cwd=str(root))
        _write_plan_tdd(root, verdict, plan_org, plan)
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            return verdict
        raise MAGIGateError("retry iter also failed gate")
    raise MAGIGateError(f"user chose '{decision.action}' on safety-valve exhaustion")


def _run_magi_checkpoint2(
    root: Path, cfg: object, ns: argparse.Namespace
) -> magi_dispatch.MAGIVerdict:
    """Run the Checkpoint 2 MAGI loop honoring INV-28 degraded handling.

    On INV-11 safety-valve exhaustion, delegate to
    :func:`_handle_safety_valve_exhaustion` (Feature A wiring).
    ``--override-checkpoint --reason`` bypasses the prompt and accepts the
    last verdict; ``--non-interactive`` forces the headless policy;
    otherwise ``prompt_user`` is invoked interactively.

    Args:
        root: Project root.
        cfg: :class:`config.PluginConfig` carrying threshold + iteration cap.
        ns: Parsed argparse namespace carrying escalation flags.

    Returns:
        The ``MAGIVerdict`` that passed the gate (full, non-degraded,
        >= threshold) or the last observed verdict under override.

    Raises:
        MAGIGateError: STRONG_NO_GO at any iteration, or any of the
            terminal outcomes surfaced by
            :func:`_handle_safety_valve_exhaustion`.
    """
    spec = root / "sbtdd" / "spec-behavior.md"
    plan_org = root / "planning" / "claude-plan-tdd-org.md"
    plan = root / "planning" / "claude-plan-tdd.md"
    max_iter = int(getattr(cfg, "magi_max_iterations"))
    threshold = str(getattr(cfg, "magi_threshold"))
    verdict_history: list[magi_dispatch.MAGIVerdict] = []
    for iteration in range(1, max_iter + 1):
        verdict = magi_dispatch.invoke_magi(context_paths=[str(spec), str(plan_org)], cwd=str(root))
        verdict_history.append(verdict)
        if magi_dispatch.verdict_is_strong_no_go(verdict):
            raise MAGIGateError(
                f"MAGI returned STRONG_NO_GO at iter {iteration}. Refine spec-behavior-base.md."
            )
        _write_plan_tdd(root, verdict, plan_org, plan)
        if verdict.degraded:
            continue  # INV-28: degraded never exits.
        if magi_dispatch.verdict_passes_gate(verdict, threshold):
            return verdict
    return _handle_safety_valve_exhaustion(
        root, spec, plan_org, plan, threshold, verdict_history, ns
    )


def _create_state_file(root: Path, cfg: object, plan: Path) -> None:
    """Write the initial session-state.json after Checkpoint 2 approval.

    ``plan_approved_at`` is populated with the current UTC timestamp -- this
    is the marker that unlocks the "Excepcion bajo plan aprobado" contract
    (CLAUDE.md / template sec.5).
    """
    del cfg  # reserved for future fields (state_file_path override, ...).
    task_id, task_title = _first_open_task(plan)
    r = subprocess_utils.run_with_timeout(
        ["git", "rev-parse", "--short", "HEAD"], timeout=10, cwd=str(root)
    )
    sha = r.stdout.strip() or "0000000"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    state = state_file.SessionState(
        plan_path="planning/claude-plan-tdd.md",
        current_task_id=task_id,
        current_task_title=task_title,
        current_phase="red",
        phase_started_at_commit=sha,
        last_verification_at=None,
        last_verification_result=None,
        plan_approved_at=now,
    )
    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    state_file.save(state, claude_dir / "session-state.json")


def _commit_approved_artifacts(root: Path) -> None:
    """Commit the three spec/plan artifacts under the ``chore:`` prefix.

    Addresses iter-1 Finding 3: /brainstorming and /writing-plans produce
    files that should be committed once MAGI approves. Under the
    "Excepcion bajo plan aprobado" clause (template sec.5), this is one
    of the four authorized categories (plan bookkeeping).
    """
    artifacts = (
        "sbtdd/spec-behavior.md",
        "planning/claude-plan-tdd-org.md",
        "planning/claude-plan-tdd.md",
    )
    for rel in artifacts:
        subprocess_utils.run_with_timeout(["git", "add", rel], timeout=10, cwd=str(root))
    commits.create("chore", "add MAGI-approved spec and plan", cwd=str(root))


def main(argv: list[str] | None = None) -> int:
    """Entry point for the spec subcommand.

    Args:
        argv: Command-line arguments (None uses ``sys.argv``).

    Returns:
        Process exit code (0 on success).

    Raises:
        PreconditionError: INV-27 violation, skeleton markers, or missing
            downstream spec/plan artifact.
        MAGIGateError: Checkpoint 2 MAGI loop produced STRONG_NO_GO or
            exhausted the iteration budget without convergence.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = Path(ns.project_root)
    _validate_spec_base_no_placeholders(root / "sbtdd" / "spec-behavior-base.md")
    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _run_spec_flow(root)
    _run_magi_checkpoint2(root, cfg, ns)
    # State file MUST be persisted BEFORE the artifacts commit so that
    # plan_approved_at is visible to any follow-on subcommand even if
    # the commit itself fails mid-way (state = canon of the present;
    # git = canon of the past; CLAUDE.local.md §2.1).
    _create_state_file(root, cfg, root / "planning" / "claude-plan-tdd.md")
    _commit_approved_artifacts(root)
    return 0


run = main
