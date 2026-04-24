#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Interactive MAGI escalation prompt (Feature A, v0.2.0).

Fires when INV-11 safety valve exhausts in `/sbtdd spec` (Checkpoint 2) or
`/sbtdd pre-merge` (Loop 2). INV-22 forbids running inside `/sbtdd auto`:
auto invocations consult `.claude/magi-auto-policy.json` instead.

Public API:
    build_escalation_context(iterations, plan_id, context) -> EscalationContext
    format_escalation_message(ctx) -> str
    prompt_user(ctx, options) -> UserDecision
    apply_decision(decision, ctx, root) -> int  # writes audit artifact

Precedent: Milestone D Checkpoint 2 iter 3 chat escalation (commit 5d7bfc4).
"""

from __future__ import annotations

import enum
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from magi_dispatch import MAGIVerdict
from models import AUTO_POLICIES


class _RootCause(enum.Enum):
    INFRA_TRANSIENT = "infra_transient"  # same agent fails across iters
    PLAN_VS_SPEC = "plan_vs_spec"  # CRITICAL findings persist
    STRUCTURAL_DEFECT = "structural_defect"  # STRONG_NO_GO from >=1 agent
    SPEC_AMBIGUITY = "spec_ambiguity"  # confidence trending down


_ContextLit = Literal["checkpoint2", "pre-merge", "auto"]
_ActionLit = Literal["override", "retry", "abandon", "alternative"]


@dataclass(frozen=True)
class EscalationOption:
    letter: str  # 'a' | 'b' | 'c' | 'd'
    action: _ActionLit
    rationale: str  # shown in the menu after the action verb
    caveat: str = ""  # optional consequence / tradeoff line


@dataclass(frozen=True)
class EscalationContext:
    iterations: tuple[dict[str, Any], ...]  # per-iter verdict snapshots
    plan_id: str
    context: _ContextLit
    per_agent_verdicts: tuple[tuple[str, str], ...]  # (agent_name, verdict)
    findings: tuple[tuple[str, str], ...]  # (severity, text)
    root_cause: _RootCause


@dataclass(frozen=True)
class UserDecision:
    chosen_option: str
    action: _ActionLit
    reason: str


_ROOT_LABELS: dict[_RootCause, str] = {
    _RootCause.INFRA_TRANSIENT: "transient-infra (agent degraded repite)",
    _RootCause.PLAN_VS_SPEC: "plan-vs-spec gap (CRITICAL findings persisten)",
    _RootCause.STRUCTURAL_DEFECT: "defecto estructural (STRONG_NO_GO)",
    _RootCause.SPEC_AMBIGUITY: "spec ambiguity (confidence trending down)",
}

_OPT_OVERRIDE = EscalationOption(
    letter="a",
    action="override",
    rationale="Override INV-0 (user authority)",
    caveat="requires --reason; audit artifact written.",
)
_OPT_RETRY = EscalationOption(
    letter="b",
    action="retry",
    rationale="Re-invocar MAGI una iter mas (safety valve +1)",
    caveat="consume iter extra; INV-0 override del INV-11.",
)
_OPT_ALTERNATIVE = EscalationOption(
    letter="c",
    action="alternative",
    rationale="Replan: split spec o ajustar scope",
    caveat="reinicia flujo desde sec.1.",
)
_OPT_ABANDON = EscalationOption(
    letter="d",
    action="abandon",
    rationale="Exit 8 (v0.1 behavior) + artefactos para review manual",
    caveat="default en non-TTY.",
)

_MENU_LETTERS = ("a", "b", "c", "d")

_HEADLESS_POLICY_FILE = ".claude/magi-auto-policy.json"
_AUDIT_DIR = ".claude/magi-escalations"
_PENDING_MARKER = ".claude/magi-escalation-pending.md"


def _finding_severity(finding: Any, default: str = "INFO") -> str:
    """Normalize a finding's ``severity`` field to an uppercase string."""
    return str(finding.get("severity", default)).upper()


def _classify_root_cause(iterations: list[MAGIVerdict]) -> _RootCause:
    """Infer the dominant failure mode across iterations."""
    if any(v.verdict == "STRONG_NO_GO" for v in iterations):
        return _RootCause.STRUCTURAL_DEFECT
    degraded_count = sum(1 for v in iterations if v.degraded)
    if degraded_count >= 2 and degraded_count >= len(iterations) / 2:
        return _RootCause.INFRA_TRANSIENT
    critical_across = [
        any(_finding_severity(f, default="") == "CRITICAL" for f in v.findings) for v in iterations
    ]
    if sum(critical_across) >= 2:
        return _RootCause.PLAN_VS_SPEC
    return _RootCause.SPEC_AMBIGUITY


def build_escalation_context(
    iterations: list[MAGIVerdict],
    plan_id: str,
    context: _ContextLit,
) -> EscalationContext:
    """Collect iter history + classify root cause."""
    snapshots = tuple(
        {
            "verdict": v.verdict,
            "degraded": v.degraded,
            "n_conditions": len(v.conditions),
            "n_findings": len(v.findings),
        }
        for v in iterations
    )
    per_agent: tuple[tuple[str, str], ...] = ()  # v0.2: MAGI does not expose per-agent breakdown
    findings = tuple(
        (_finding_severity(f), str(f.get("text", f))) for v in iterations for f in v.findings
    )
    return EscalationContext(
        iterations=snapshots,
        plan_id=plan_id,
        context=context,
        per_agent_verdicts=per_agent,
        findings=findings,
        root_cause=_classify_root_cause(iterations),
    )


def _compose_options(ctx: EscalationContext) -> tuple[EscalationOption, ...]:
    """Build a context-aware menu (<=4 options) keyed by root cause.

    STRUCTURAL_DEFECT only exposes (a) abandon; every other root cause
    exposes override, retry, alternative, abandon so the canonical
    template emits four sequential letters.
    """
    if ctx.root_cause == _RootCause.STRUCTURAL_DEFECT:
        opts: tuple[EscalationOption, ...] = (_OPT_ABANDON,)
    else:
        opts = (_OPT_OVERRIDE, _OPT_RETRY, _OPT_ALTERNATIVE, _OPT_ABANDON)
    return tuple(
        EscalationOption(
            letter=_MENU_LETTERS[i],
            action=o.action,
            rationale=o.rationale,
            caveat=o.caveat,
        )
        for i, o in enumerate(opts)
    )


def format_escalation_message(ctx: EscalationContext) -> str:
    """Render the canonical escalation template (<=40 lines).

    Output mirrors the precedent from Milestone D Checkpoint 2 iter 3
    escalation (commit 5d7bfc4): root-cause hint, iter counter, findings
    tally, and the dynamic option menu followed by the Spanish prompt.
    """
    n = len(ctx.iterations)
    last = ctx.iterations[-1] if ctx.iterations else {"verdict": "?", "degraded": False}
    root_label = _ROOT_LABELS[ctx.root_cause]
    opts = _compose_options(ctx)
    lines = [
        f"MAGI iter {n} FINAL ({ctx.context}): veredicto '{last['verdict']}' degraded={last['degraded']}.",
        f"Causa raiz inferida: {root_label}.",
        f"Safety valve INV-11 exhausted tras {n} iter.",
        "",
        "Escalando al usuario per INV-11 + INV-18:",
        "",
        f"Estado plan {ctx.plan_id}:",
        f"- Iteraciones: {n}",
        f"- Findings residuales: {len(ctx.findings)}",
        "",
        "Opciones per INV-0 (user authority):",
    ]
    for o in opts:
        line = f"- ({o.letter}) {o.action}: {o.rationale}."
        if o.caveat:
            line += f" {o.caveat}"
        lines.append(line)
    lines.append("")
    lines.append("¿Cuál?")
    return "\n".join(lines)


_DEFAULT_POLICY = "abort"


def _read_headless_policy(root: Path) -> str:
    """Return the configured policy or 'abort' (default)."""
    p = root / _HEADLESS_POLICY_FILE
    if not p.is_file():
        return _DEFAULT_POLICY
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _DEFAULT_POLICY
    policy = str(data.get("on_exhausted", _DEFAULT_POLICY))
    return policy if policy in AUTO_POLICIES else _DEFAULT_POLICY


def _decision_for(
    options: tuple[EscalationOption, ...],
    action: _ActionLit,
    reason: str,
) -> UserDecision:
    """Build a ``UserDecision`` from the option whose action matches.

    Falls back to ``options[-1]`` when no option carries ``action`` (e.g. a
    STRUCTURAL_DEFECT menu that only exposes abandon). The resulting
    decision reflects the matched option's action, not the requested one.
    """
    match = next((o for o in options if o.action == action), options[-1])
    return UserDecision(chosen_option=match.letter, action=match.action, reason=reason)


def prompt_user(
    ctx: EscalationContext,
    options: tuple[EscalationOption, ...],
    *,
    non_interactive: bool = False,
    project_root: Path | None = None,
) -> UserDecision:
    """Print the formatted escalation message + prompt user for choice.

    Non-TTY / --non-interactive / auto path: apply headless policy from
    .claude/magi-auto-policy.json (default 'abort' = option d).

    TTY path: loop input() until user enters a valid letter; then collect
    a one-line reason (mandatory for override action).
    """
    sys.stderr.write(format_escalation_message(ctx) + "\n")
    tty = sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False
    if non_interactive or not tty:
        policy = _read_headless_policy(project_root or Path.cwd())
        # MAGI Loop 2 v0.2 pre-merge WARNING #2 (2026-04-24): in headless
        # paths, the configured policy is silently applied. CI users who
        # never opted into ``.claude/magi-auto-policy.json`` get the
        # ``abort`` default and never discover the knob exists. Emit a
        # one-line stderr breadcrumb so operators at least see the choice
        # being made and can grep their CI logs to find the configuration
        # surface. Cost: one stderr line per pre-merge / spec / auto-mode
        # exhaustion, which is rare. Quiet for normal TTY runs.
        sys.stderr.write(
            f"[escalation_prompt] headless policy='{policy}' "
            f"(configure .claude/magi-auto-policy.json to change)\n"
        )
        # MAGI Loop 2 v0.2 pre-merge WARNING #4 (2026-04-24):
        # ``override_strong_go_only`` originally tested
        # ``ctx.root_cause != STRUCTURAL_DEFECT`` -- but
        # ``_classify_root_cause`` only returns STRUCTURAL_DEFECT when a
        # STRONG_NO_GO verdict appears in the history. The predicate
        # therefore overrode on INFRA_TRANSIENT, PLAN_VS_SPEC, AND
        # SPEC_AMBIGUITY (every non-STRONG_NO_GO failure mode), which is
        # the inverse of what the policy name suggests. Operators who
        # picked ``override_strong_go_only`` expecting "auto-override
        # only when MAGI was leaning toward GO" instead got auto-override
        # on degraded HOLD loops, plan-vs-spec gaps, and ambiguous specs.
        # The fix tightens the predicate: only override when the
        # most-recent verdict is STRONG_GO or GO (i.e. the verdict was
        # genuinely on the GO side and the safety valve still tripped --
        # likely an infra/transient issue worth overriding). Other
        # verdicts (HOLD, HOLD_TIE, GO_WITH_CAVEATS, STRONG_NO_GO) keep
        # the human-in-the-loop default of ``abort``.
        if policy == "override_strong_go_only":
            last_iter = ctx.iterations[-1] if ctx.iterations else None
            last_verdict = str(last_iter.get("verdict", "")) if isinstance(last_iter, dict) else ""
            if last_verdict in ("GO", "STRONG_GO"):
                return _decision_for(
                    options, "override", "headless policy: override_strong_go_only"
                )
        if policy == "retry_once" and any(o.action == "retry" for o in options):
            return _decision_for(options, "retry", "headless policy: retry_once")
        return _decision_for(options, "abandon", "headless policy: abort (default)")

    # TTY path: persist a pending-marker BEFORE the first input() so a Ctrl+C
    # between marker-write and decision-return leaves a recoverable checkpoint
    # for resume_cmd. KeyboardInterrupt bypasses the normal-exit cleanup
    # (no try/finally) so the marker survives process kill; EOFError and
    # successful decisions both exit through _finish which removes the marker.
    root = project_root or Path.cwd()
    pending = root / _PENDING_MARKER
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_text(
        json.dumps(
            {
                "plan_id": ctx.plan_id,
                "context": ctx.context,
                "root_cause": ctx.root_cause.value,
                "iterations": list(ctx.iterations),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    def _finish(decision: UserDecision) -> UserDecision:
        if pending.is_file():
            pending.unlink()
        return decision

    valid = {o.letter: o for o in options}
    while True:
        try:
            choice = input("Option (a/b/c/d): ").strip().lower()
        except EOFError:
            return _finish(
                _decision_for(options, "abandon", "EOFError during prompt; headless default")
            )
        if choice in valid:
            break
        sys.stderr.write(f"Invalid choice '{choice}'; expected one of {sorted(valid)}.\n")
    opt = valid[choice]
    if opt.action == "override":
        try:
            reason = input("Reason (mandatory for override): ").strip()
        except EOFError:
            reason = ""
        if not reason:
            sys.stderr.write("Override requires non-empty --reason; falling back to abandon.\n")
            return _finish(_decision_for(options, "abandon", "override requested without reason"))
        return _finish(UserDecision(chosen_option=choice, action="override", reason=reason))
    return _finish(
        UserDecision(chosen_option=choice, action=opt.action, reason=f"user chose {opt.action}")
    )


def apply_decision(decision: UserDecision, ctx: EscalationContext, project_root: Path) -> int:
    """Write audit artifact + return process exit code.

    Returns:
        0 if decision is override/retry/alternative (caller continues);
        8 if abandon (exit 8 matches v0.1 behavior so wrappers can propagate).
    """
    artifact_dir = project_root / _AUDIT_DIR
    artifact_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    safe_ts = ts.replace(":", "-")
    artifact = artifact_dir / f"{safe_ts}-{ctx.plan_id}.json"
    payload = {
        "decision": decision.action,
        "chosen_option": decision.chosen_option,
        "reason": decision.reason,
        "escalation_context": {
            "iterations": list(ctx.iterations),
            "plan_id": ctx.plan_id,
            "root_cause": ctx.root_cause.value,
            "n_findings": len(ctx.findings),
        },
        "timestamp": ts,
        "plan_id": ctx.plan_id,
        "magi_context": ctx.context,
    }
    artifact.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 8 if decision.action == "abandon" else 0
