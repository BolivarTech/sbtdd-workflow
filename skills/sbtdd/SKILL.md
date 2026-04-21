---
name: sbtdd
description: >
  SBTDD + Superpowers multi-agent workflow orchestrator. Use when working on a
  project that follows the SBTDD methodology (Spec + Behavior + Test Driven
  Development) and needs to execute one of the nine workflow operations:
  init, spec, close-phase, close-task, status, pre-merge, finalize, auto,
  resume. Trigger phrases: "sbtdd init", "sbtdd close phase", "advance TDD
  phase", "run pre-merge review", "finalize SBTDD plan", "sbtdd auto",
  "shoot-and-forget SBTDD run", "resume SBTDD", "sbtdd resume", "continue
  interrupted SBTDD session", or any "/sbtdd <subcommand>" invocation. NOT
  suitable for projects that do not use SBTDD -- only invoke when the project
  has `sbtdd/spec-behavior-base.md` or `.claude/plugin.local.md` with `stack` set.
---

# SBTDD Workflow -- Spec + Behavior + Test Driven Development Orchestrator

> `~/.claude/CLAUDE.md` has absolute precedence (INV-0). This skill is a
> dispatcher -- it never overrides the developer's global Code Standards.

## Overview

SBTDD (Spec + Behavior + Test Driven Development) combines three disciplines:

- **SDD (Spec Driven Development):** a textual specification (`sbtdd/spec-behavior.md`)
  is authoritative. No behavior is implemented that is not declared there.
- **BDD (Behavior Driven Development):** Given/When/Then scenarios in the spec
  document expected behavior in testable form.
- **TDD (Test Driven Development):** Red-Green-Refactor discipline, enforced
  physically by TDD-Guard hooks and procedurally by `/test-driven-development`.

This plugin orchestrates the SBTDD lifecycle end to end: from blank spec through
pre-merge gates to a ship-ready branch. Every state transition produces an atomic
git commit following the sec.M.5 prefix map (`test:` / `feat:` / `fix:` /
`refactor:` / `chore:`). Two mandatory pre-merge loops -- automated code review
(`/requesting-code-review`) and multi-perspective review (`/magi:magi`) -- gate
the branch before `/finishing-a-development-branch`.

The plugin follows the architectural pattern of MAGI (one skill, one entrypoint,
Python-backed scripts). The skill below is the dispatcher; all state-changing
logic lives in `scripts/run_sbtdd.py` and the nine `{subcommand}_cmd.py` modules.

## Subcommand dispatch

| Subcommand | Purpose | When to invoke |
|------------|---------|----------------|
| `init` | Bootstrap an SBTDD project (generate rules, hooks, skeleton spec) | Once per destination project, greenfield |
| `spec` | Run the spec pipeline (`/brainstorming` -> `/writing-plans` -> MAGI Checkpoint 2) | After `init`, before any code; iteratively until MAGI approves |
| `close-phase` | Close one TDD phase (Red/Green/Refactor) atomically: verify + commit + advance state | After implementing each phase, before moving to the next |
| `close-task` | Mark `[x]` in the plan + commit `chore:` + advance state to the next `[ ]` | After the Refactor phase of a task (also auto-invoked by `close-phase refactor`) |
| `status` | Read-only structured report of state + git + plan + drift | At any time, safe to invoke (read-only) |
| `pre-merge` | Run Loop 1 (`/requesting-code-review` until clean-to-go) + Loop 2 (`/magi:magi` gate) | When all plan tasks are `[x]` and `current_phase: "done"` |
| `finalize` | Run the sec.M.7 checklist + invoke `/finishing-a-development-branch` | After `pre-merge` returns exit 0 |
| `auto` | Shoot-and-forget full cycle: task loop + pre-merge + checklist (stops before `/finishing-a-development-branch`) | When the user wants unattended execution of an approved plan |
| `resume` | Diagnose interrupted runs (quota exhaustion, crash, reboot) and delegate recovery | After an `auto` run aborted mid-flight, or after any interruption |

Invocation pattern: `/sbtdd <subcommand> [args...]`. Under the hood, every
subcommand routes through `run_sbtdd.py` (see `## Execution pipeline` below).

## Complexity gate

Before delegating to Python, assess whether the user's request actually needs
state transitions. If the user asks a simple factual question about SBTDD
methodology (e.g., "what does INV-27 mean?", "what is the commit prefix for a
Refactor phase?"), respond directly from the embedded rules in `## sbtdd-rules`
below -- no Python invocation needed.

Invoke Python (via `run_sbtdd.py`) when the user asks for:

- Any of the nine subcommands (explicit: `/sbtdd init`, `/sbtdd close-phase`, ...).
- State interrogation that must be accurate (e.g., "what phase am I on?",
  "is my plan complete?").
- Any action that mutates `.claude/session-state.json`, the plan, or git.

Do NOT invoke Python for:

- Explaining methodology sections (answer from the embedded `## sbtdd-rules`).
- Clarifying commit prefix rules (answer from the embedded `## sbtdd-tdd-cycle`).
- Meta-questions about the plugin (version, repository, license) -- answer
  from the `plugin.json` manifest directly.

## Execution pipeline

All state-changing subcommands route through a single Python entrypoint:

```
python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <subcommand> [args...]
```

The dispatcher (`run_sbtdd.py`) parses the subcommand, validates preconditions
(INV-12), loads `.claude/session-state.json` (INV-4) and `.claude/plugin.local.md`,
and delegates to `skills/sbtdd/scripts/{subcommand}_cmd.py`. Every subcommand
emits exit codes according to the canonical taxonomy (sec.S.11.1):

| Exit | Symbol | Meaning |
|------|--------|---------|
| 0 | SUCCESS | Nominal completion |
| 1 | USER_ERROR | Invalid flags, unknown subcommand |
| 2 | PRECONDITION_FAILED | Missing dependency, schema mismatch, uppercase placeholder tokens in spec (INV-27) |
| 3 | DRIFT_DETECTED | State/git/plan divergence; user must resolve manually (INV-17) |
| 4 | FILE_CONFLICT | `init` aborted due to existing non-empty artifacts |
| 5 | SMOKE_TEST_FAILED | `init` Phase 4 (post-setup smoke test) failed |
| 6 | VERIFICATION_IRREMEDIABLE | sec.M.0.1 verification failed; auto cannot recover |
| 7 | LOOP1_DIVERGENT | `/requesting-code-review` did not converge in 10 iter |
| 8 | MAGI_GATE_BLOCKED | `/magi:magi` verdict below threshold after max iter (INV-11) |
| 9 | CHECKLIST_FAILED | `finalize` sec.M.7 checklist item failed |
| 11 | QUOTA_EXHAUSTED | Anthropic API quota detected via `quota_detector.py` (INV-30) |
| 130 | INTERRUPTED | SIGINT (Ctrl+C) |

**MAGI invocation pattern.** Two subcommands invoke MAGI:
- `spec` at Checkpoint 2: `/magi:magi revisa @sbtdd/spec-behavior.md y @planning/claude-plan-tdd-org.md`.
  Iteration cap: `magi_max_iterations` (default 3). Exceeding escalates to user with candidate root causes.
- `pre-merge` Loop 2: after Loop 1 returns clean-to-go, invoke `/magi:magi` on
  the accumulated diff. Same iteration cap (default 3). `auto` uses `auto_magi_max_iterations`
  (default 5) to compensate for the absence of human supervision.

Both invocations honor **INV-28** (degraded verdict with fewer than 3 agents
does NOT count as a loop-exit signal; consumes one iteration and re-invokes
MAGI). Exception: `STRONG_NO_GO` degraded still aborts immediately (2 agents
saying NO-GO is evidence enough).

Both invocations honor **INV-29** (every MAGI finding that requires a code change
MUST be evaluated by `/receiving-code-review` before the mini-cycle TDD is
applied; rejected findings are logged and fed back as context into the next
MAGI iteration to break sterile loops).

## sbtdd-rules

The authoritative rules live in the destination project's
`CLAUDE.local.md` (installed from `templates/CLAUDE.local.md.template` by
`sbtdd init`). The summary below lets the skill answer common rule questions
without opening Python.

### Commit prefix map (sec.M.5)

| Context | Prefix | Example |
|---------|--------|---------|
| Red phase close | `test:` | `test: add parser edge case for empty input` |
| Green phase close (new feature) | `feat:` | `feat: implement parser minimum viable logic` |
| Green phase close (bug fix) | `fix:` | `fix: handle trailing whitespace in values` |
| Refactor phase close | `refactor:` | `refactor: extract validation into separate fn` |
| Task close (checkbox `[x]`) | `chore:` | `chore: mark task 3 complete` |
| Loop 1/2 mini-cycle fix | `test:` -> `fix:` -> `refactor:` | Three atomic commits per finding |

### Commit discipline (INV-5..8)

- English prose only (no Spanish, no other languages).
- No `Co-Authored-By` lines.
- No references to Claude / AI / assistant in commit messages.
- Atomic: one commit = one concern = one prefix. Never mix phases or tasks.
- Outside the four authorized categories (phase close, task close, Loop 1 fix,
  Loop 2 fix), commits require explicit user permission (INV-8).

### Plan-approved contract (`plan_approved_at != null`)

Once `/sbtdd spec` approves the plan (sets `plan_approved_at` in
`.claude/session-state.json`), the plugin is pre-authorized to create commits
in the four categories above without prompting. Outside those categories, the
user is still prompted.

### Degraded MAGI (INV-28)

A MAGI verdict with `degraded: true` (fewer than 3 agents returned usable
output) NEVER counts as a loop-exit signal. The iteration is consumed and
MAGI is re-invoked. Exception: `STRONG_NO_GO` degraded aborts immediately
(sec.S.10.3).

### Spec-base placeholder rejection (INV-27)

`sbtdd/spec-behavior-base.md` MUST NOT contain the uppercase word-boundary
tokens (the three uppercase placeholder markers enumerated in INV-27, rule
of sec.S.10.4 of the contract). There is no `--force` override. Rationale:
specs with placeholders waste MAGI iterations at Checkpoint 2. Lowercase
"todos" (Spanish natural text meaning "all") is explicitly allowed.

### Global authority (INV-0)

`~/.claude/CLAUDE.md` overrides every other configuration file, including
this SKILL.md, `CLAUDE.local.md`, and `plugin.local.md`. No override flags
exist. Every subcommand honors (does not redefine) the developer's global
Code Standards.

## sbtdd-tdd-cycle

The Red-Green-Refactor cycle is enforced by two layers:

- **TDD-Guard** (physical): hooks intercept file writes in real time. Writing
  code without a failing test triggers a hard block. Toggle via quick prompt
  (`tdd-guard on` / `tdd-guard off`) configured through the `UserPromptSubmit`
  hook.
- **`/test-driven-development`** (procedural): the Superpowers skill guides
  the agent through the cycle disciplinedly. Invoked at the start of each task.

### Red phase

- Allowed: failing tests (assertion failures OR compile/type errors on the
  absent implementation).
- Blocked: production code, tests that pass trivially.
- Close ritual (three steps, strict):
  1. `/verification-before-completion` -- confirm the test fails for the correct reason.
  2. Atomic commit with prefix `test:`.
  3. Advance `.claude/session-state.json`: `current_phase: "green"`, update
     `phase_started_at_commit`, `last_verification_at`, `last_verification_result`.

### Green phase

- Allowed: minimum implementation that turns the Red tests green.
- Blocked: modifying tests, adding unrelated functionality.
- Close ritual: `/verification-before-completion` + commit prefix `feat:` (new
  feature) or `fix:` (hardening / bug-fix) + state advance to `refactor`.

### Refactor phase

- Allowed: structural improvements, renames, deduplication, doc-comments.
- Blocked: changing behavior, adding functionality, editing tests.
- Close ritual: `/verification-before-completion` + commit `refactor:` +
  state advance to `done` + auto-invoke `close-task` (mark `[x]` + commit
  `chore:` + advance to next `[ ]` or set `current_phase: "done"` if plan complete).

### When a test fails unexpectedly

Invoke `/systematic-debugging` BEFORE proposing a fix. Diagnose the root cause
(missing implementation vs. environmental issue vs. test bug) and then apply
the appropriate fix. Do not patch symptoms.

### Close-phase delegation

The agent should NOT attempt the three-step close by hand. Always invoke
`/sbtdd close-phase` -- the Python command handles the drift check, invokes
`/verification-before-completion`, runs `commits.create` with the validated
prefix, and updates the state file atomically. Manual close = drift risk.
