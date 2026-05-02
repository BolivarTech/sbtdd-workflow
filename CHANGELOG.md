# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with
subsections BREAKING / Added / Changed / Fixed / Deprecated / Removed.

The plugin is pre-1.0 (`v0.1.x`); the CHANGELOG starts recording changes
introduced during Milestone D hardening and will be human-curated for
every post-v0.1 release.

## Unreleased (Deferred — tracked for v1.0.0)

v0.3.0 shipped Track D (auto progress visibility) and Track E (per-skill
model selection) as a focused subset of the v1.0.0 backlog. Open
v1.0.0 LOCKED items remaining:

- D5 `/sbtdd status --watch` companion command (poll
  `.claude/auto-run.json` and stream the `progress` field to a separate
  TTY without re-entering `auto_cmd`). Deferred from v0.3.0 because the
  emitter (`_update_progress` atomic write contract) is in place but the
  reader/poller wants its own subcommand and a small terminal UI; it is
  orthogonal to the v0.3.0 streaming + breadcrumb deliverables.
- E2 `schema_version: 2` bump for `plugin.local.md` (formal schema
  versioning of the four model fields). v0.3.0 added the fields under
  the existing schema with `null` defaults so v0.2.x configs continue
  to load unchanged. Bumping requires a migration story for older
  configs which is part of the v1.0.0 schema-versioning pass.
- F (per-phase MAGI lite at refactor close), G (Group B spec-drift
  detection options (1)-(7) re-evaluation with v0.2/v0.2.1/v0.2.2/v0.3
  field data), H (INV-31 default-on opt-in re-evaluation based on field
  data of whether the spec-reviewer per-task default flips to opt-in).
- MAGI dispatch hardening + `retried_agents` telemetry (marker-based
  path discovery defensive over `--output-dir`; consume new MAGI
  2.2.1+ `retried_agents` field in verdict parsing).
- MAGI → `/requesting-code-review` cross-check (meta-reviewer pattern;
  user has validated empirically in adjacent projects -- catches MAGI
  false-positive CRITICALs before INV-29 gate).

## [0.4.0] - 2026-04-25

### Added

- **Feature F — MAGI dispatch hardening** (post-v0.3.0 pre-1.0 work):
  - `magi_dispatch._discover_verdict_marker(output_dir)` enumerates
    `MAGI_VERDICT_MARKER.json` files via recursive glob and returns the
    most recent by mtime (F43). Iter 2 wires the helper as the primary
    discovery path inside `invoke_magi`, with graceful fallback to the
    legacy `magi-report.json` lookup so MAGI 2.x layouts (which still
    write `magi-report.json`) continue to work unchanged. Forward-compat
    for future MAGI versions that emit `MAGI_VERDICT_MARKER.json`.
    Marker schema (HF2 alignment with the impl-side documentation in
    `magi_dispatch._MARKER_FILENAME` docstring): the four canonical
    fields are `verdict`, `iteration`, `agents`, `timestamp`. Optional
    fields tolerated by the parser: `retried_agents`,
    `synthesizer_status`.
  - `MAGIVerdict.retried_agents: tuple[str, ...]` consumes the new
    MAGI 2.2.1+ telemetry field with default `()` for MAGI 2.1.x
    backward compat (F44). v0.4.0 ships the dataclass field + parser
    + JSON-serialisability guarantee, sufficient for downstream
    consumers (`escalation_prompt`) to read the field directly from
    `MAGIVerdict` instances when they hold them. Note: full propagation
    of `retried_agents` into the `auto-run.json` audit field is
    **deferred to v1.0.0** alongside Features G/H per scope balance --
    the field is parsed and serialisable today but not yet written
    into the persistent audit chain by `auto_cmd._write_auto_run_audit`.
  - `magi_dispatch._tolerant_agent_parse(raw_json_path)` (F45) parses
    a single agent's `*.raw.json` file accepting both pure-JSON
    `result` payloads (preserving v0.3.x strict-parser semantics) and
    preamble-wrapped payloads where the verdict JSON is preceded by a
    narrative paragraph. Iter 2 hardens validation so every accepted
    candidate dict carries an `agent` field in `{melchior, balthasar,
    caspar}` AND a `verdict` field in
    `models.VERDICT_RANK ∪ {approve, conditional, reject}`; verdict
    typos (e.g. `"GO_LATER"`) no longer slip through to silently
    weigh as 0.0 in `_manual_synthesis_recovery`.
  - `magi_dispatch._manual_synthesis_recovery(run_dir)` (F46) rescues a
    `MAGIVerdict` when the MAGI synthesizer crashed (`"Only N agent(s)
    succeeded"` stderr) but at least one agent persisted recoverable
    JSON. Wires into `invoke_magi` after `quota_detector.detect` so
    credit exhaustion is never masked by recovery (sec.S.11.4).
    Persists a `manual-synthesis.json` recovery report flagged
    `recovered: true` / `recovery_reason: "synthesizer-failure"` for
    audit trails.
- **Feature J — v0.3.0 streaming follow-through**: `pre_merge_cmd`
  Loop 1 + Loop 2 + per-finding dispatches now thread the
  `stream_prefix` parameter end-to-end so MAGI/code-review subprocess
  output reaches the orchestrator's stderr line-by-line during
  multi-minute consensus runs (J8). `_update_progress` swallows
  `OSError` and preserves the existing `auto-run.json` (J4).
  `_write_auto_run_audit` reads the on-disk payload before writing so
  the existing `progress` field survives audit merges (J6).

### Changed

- **`magi_dispatch.invoke_magi(allow_recovery: bool = True)`** —
  auto-recovery on synthesizer crash now defaults ON (F46.5). Existing
  callers silently pick up the recovery path, which converts an
  expensive class of failure (manual rerun on synthesizer crash) into
  an audited automatic recovery with a `[sbtdd magi] synthesizer
  failed; manual synthesis recovery applied (N findings)` stderr
  breadcrumb. Pass `allow_recovery=False` to restore strict
  behavior (synthesizer crash → `MAGIGateError` propagation) for
  callers that need to detect the original failure mode.
- SKILL.md v0.3 flags section corrected to use exit `1` (matching the
  actual `argparse`/`SystemExit` taxonomy) instead of exit `2`
  documented during the v0.3.0 ship (J5).

### Process

- Loop 1 surrogate via `make verify` clean (pytest 818, ruff,
  format, mypy --strict). Lightweight pattern v0.3.0 + v0.4.0
  precedent.
- MAGI Loop 2 converged in 2 iterations: iter 1 returned
  GO_WITH_CAVEATS (2-0) degraded (caspar agent crashed at 283s
  with the same `Expecting value: line 1 column 1 (char 0)` JSON
  decode error observed in v0.3.0 iter 1) with 3 WARNING + 6
  INFO findings; iter 2 applied all WARNING findings via Loop 2
  fix mini-cycles and deferred the 6 INFO findings via documented
  scope decisions, returning STRONG GO (2-0) degraded (caspar
  crashed again at 191s -- chronic infrastructure fragility). Both
  surviving agents independently and unambiguously recommended
  ship.
- **MAGI iter 2 manual synthesis acceptance**: per INV-28 strict
  reading, degraded verdicts cannot trigger Loop 2 exit; per
  pragmatic reading + v0.3.0 precedent, the agent verdicts were
  unambiguous (STRONG GO with zero CRITICAL / zero WARNING / zero
  Conditions) and the parser fragility is exactly the v1.0.0
  Feature F LOCKED scope manifesting recursively (caspar crashed
  in v0.3.0 iter 1, v0.4.0 iter 1, v0.4.0 iter 2 — pattern is
  clear). Manual acceptance authorized once by user directive
  2026-04-25 ("A pero solo esta vez"); recorded as exceptional in
  the project memory (`feedback_manual_synthesis_exceptional.md`)
  so future cycles default to retry rather than rubber-stamping
  ship decisions on degraded synthesis.
- INV-29 honored: every MAGI finding evaluated for technical merit
  before the mini-cycle TDD application. 0 findings rejected;
  3 WARNING applied via mini-cycles, 6 INFO deferred via docs.

## [0.3.0] - 2026-04-25

### Added

- **Feature D — auto progress visibility** (UX gap from v0.2 dogfood:
  multi-hour `/sbtdd auto` runs with `tee`-buffered subprocess output
  looked hung). Four primitives ship:
  1. `auto_cmd._stream_subprocess(proc, prefix)` — line-buffered
     thread-pair pump that reads subprocess stdout/stderr via
     `iter(stream.readline, "")` in two daemon threads and rewrites
     each line to orchestrator stderr with an explicit `flush()` so
     external observers see progress in real time. Returns the
     accumulated `(stdout, stderr)` tuple for `CommitError` v0.1.6
     diagnostic recovery.
  2. `auto_cmd._build_run_sbtdd_argv(subcommand, extra_args)` — argv
     builder that always prefixes invocations with `python -u` so the
     dispatched subprocess does not buffer at the Python layer.
  3. `auto_cmd._emit_phase_breadcrumb(phase, total_phases, ...)` —
     state-machine one-line breadcrumb emitted at every auto phase
     transition (pre-flight → spec → task loop → pre-merge → checklist)
     and within the task loop on every TDD sub-phase advance.
  4. `auto_cmd._update_progress(auto_run_path, ...)` — atomic
     `tmp+os.replace` writer for the `progress` field of
     `.claude/auto-run.json` (`{phase, task_index, task_total, sub_phase}`)
     with a Windows PermissionError retry loop. The four keys are now
     ALWAYS emitted (Finding #4 fix from MAGI iter 1): unknown values
     surface as JSON `null` so future `/sbtdd status --watch` consumers
     can rely on the shape contract.
  5. `subprocess_utils.run_with_timeout` gains an optional
     `stream_prefix: str | None = None` kwarg. When `None` (default)
     behavior is byte-identical to v0.2.x (`subprocess.run(...,
     capture_output=True)`). When set, the helper switches to
     `subprocess.Popen` + `auto_cmd._stream_subprocess(proc,
     stream_prefix)` so subprocess output reaches the operator's
     stderr line-by-line during execution. The returned object remains
     `subprocess.CompletedProcess` for compat with all 30+ existing
     callers.
  6. `superpowers_dispatch.invoke_skill`, `magi_dispatch.invoke_magi`,
     and `spec_review_dispatch.dispatch_spec_reviewer` thread an
     optional `stream_prefix` through to `run_with_timeout` so the
     auto path now streams real subprocess output during 5-10 min
     `/test-driven-development` invocations. Default-None preserves
     v0.2.x behavior for non-auto callers.
  7. Tests: 9 regression tests across `tests/test_auto_streaming.py`
     (D1.1 line-buffered flush, D1.2 prefix rewrite, D1.3 SIGTERM
     load-bearing test redesigned to exercise the helper concurrently
     with `proc.terminate()`, D2.1 argv -u prefix, D3.1/D3.2
     breadcrumbs) and `tests/test_auto_progress.py` (D4.1 atomicity
     under concurrent reads, D4.2 strict shape with null sentinels,
     D4.3 absent-field tolerance).
- **Feature E — per-skill model selection** (cost optimization). Long
  `/sbtdd auto` runs that inherit Opus from the user's session can
  dominate the Anthropic bill; v0.3.0 ships per-skill `--model` wiring:
  1. Four optional fields in `plugin.local.md`:
     `implementer_model`, `spec_reviewer_model`, `code_review_model`,
     `magi_dispatch_model`. Default `null` = inherit session,
     preserving v0.2.x behavior exactly.
  2. Cascade resolver (CLI override > plugin.local.md > None) with
     INV-0 enforcement: if `~/.claude/CLAUDE.md` pins a model
     globally (regex `INV_0_PINNED_MODEL_RE`), that wins and a stderr
     breadcrumb is emitted explaining the cost implication. Iter 1
     fix tightens the regex to require a pinning suffix (`for all
     sessions`, `globally`, `as default`) to eliminate false positives
     in narrative prose like "do not use claude-opus-4-7" or "for
     example, use claude-haiku-4-5".
  3. `--model-override <skill>:<model>` CLI flag on `/sbtdd auto`
     for one-off bumps. Repeatable; multiple skills can be overridden
     per invocation.
  4. `dependency_check.check_model_ids(...)` validates that requested
     model strings match `models.ALLOWED_CLAUDE_MODEL_IDS`.
  5. Recommended baseline shipped commented in
     `templates/plugin.local.md.template`: Sonnet 4.6 for implementer
     and code review (depth needed for refactors + security
     detection), Haiku 4.5 for spec reviewer (pattern-match task),
     `null` for `magi_dispatch_model` (MAGI's 3 sub-agents pick their
     own model internally; only the outer dispatcher process is
     controlled by this flag).
  6. Projected cost reduction on a 36-task `auto` run: ~70-80% vs
     default-Opus session, preserving Opus only in the 3-5 MAGI Loop
     2 iterations where multi-perspective consensus value is highest.
  7. Tests: 21 regression tests across `tests/test_config_models.py`,
     `tests/test_dispatch_model_kwarg.py`,
     `tests/test_auto_model_override.py`,
     `tests/test_dependency_check_models.py`,
     `tests/test_models_constants.py`,
     `tests/test_template_baseline.py`, plus 2 new false-positive
     regression tests in `tests/test_models_constants.py` for the
     tightened INV-0 regex.

### Changed

- `_update_progress` now ALWAYS emits the four keys
  `{phase, task_index, task_total, sub_phase}`, using JSON `null` for
  values unknown at the call site. Spec sec.2 D4.2 "shape exacto"
  contract is now satisfied at runtime (was: keys conditionally
  omitted when `_task_progress` returned `(None, None)` on missing
  plan or task-id-not-found). Downstream consumers (e.g. v0.4.0
  `/sbtdd status --watch`) can rely on the shape rather than guarding
  every key access.
- `INV_0_PINNED_MODEL_RE` tightened from
  `\b(?:use|pin|...)\s+(claude-...)` to require a pinning suffix
  (`globally`, `for all sessions`, `as default`, `as the (default|
  fixed|pinned) model`, `across all sessions`). Eliminates the
  false-positive surface flagged by MAGI iter 1 WARNING (do not use
  claude-opus-4-7 in this skill, "for example, use claude-haiku-4-5
  to optimize cost", "we always use claude-sonnet-4-6 in this
  codebase notes" — none of these now match). The original imperative
  example `Use claude-opus-4-7 for all sessions` continues to match.
- `_update_progress` docstring documents the single-writer assumption
  for `.claude/auto-run.json`. The read-modify-write window between
  `read_text` and `os.replace` is intentionally unlocked because INV-22
  guarantees a single auto orchestrator process. Future companion
  writers (e.g. `/sbtdd status --watch` poller) MUST be read-only or
  introduce a sentinel-file CAS.

### Deferred (rolled to v0.4.0 / v1.0.0)

- D5 `/sbtdd status --watch` companion command (emitter is in place,
  reader pending).
- E2 `schema_version: 2` bump in `plugin.local.md` (the four new
  fields ship under the existing schema with `null` defaults).
- F per-phase MAGI lite at refactor close.
- G Group B spec-drift detection options (1)-(7) re-evaluation.
- H INV-31 default-on opt-in re-evaluation based on field data.
- INFO finding #10 (single `ResolvedModels` dataclass at preflight
  threading all four model fields through every dispatch site, vs the
  current per-call resolver).
- INFO finding #11 (per-stream timeout in `_stream_subprocess` for the
  pathological case where a subprocess writes a long line without a
  newline and never exits without an external SIGTERM; outer
  `subprocess_utils.run_with_timeout` already enforces a wall-clock
  cap).
- INFO finding #12 (`_update_progress` OSError handling at call sites:
  observability metadata failure should not crash the auto run; the
  retry loop is sensibly bounded but propagation is unguarded).

### Process

- Loop 1 surrogate via `make verify` clean (pytest + ruff check + ruff
  format + mypy --strict, runtime <60s). The v0.2.x convention of
  using `/requesting-code-review` as the formal Loop 1 driver is
  preserved for hand-driven runs; for the v0.3.0 internal cycle the
  `make verify` gate served as the equivalent mechanical filter
  (Track D + Track E commits f0ded82..a73d7a5 each closed via
  `make verify` clean).
- MAGI Loop 2 converged in 2 iterations: iter 1 returned HOLD (1-1,
  caspar degraded) with 2 CRITICAL + 6 WARNING + 3 INFO findings;
  iter 2 applied all CRITICAL and WARNING findings via Loop 2 fix
  mini-cycles (`test:` → `fix:` → `refactor:` per finding) and
  deferred the 3 INFO findings via documented scope decision (above).
- INV-29 honored: every MAGI finding evaluated for technical merit
  before the mini-cycle TDD application; 0 findings rejected this
  iteration (all CRITICAL+WARNING substantive).
- **MAGI iter 2 synthesizer recovery via manual synthesis.** The MAGI
  v2.2.2 orchestrator aborted iter 2 with `RuntimeError: Only 1
  agent(s) succeeded` because melchior + balthasar wrapped their
  agent JSON in narrative preamble, defeating the strict parser
  (caspar parsed cleanly). Inspecting the `.raw.json` files showed
  all three agents produced unambiguous GO verdicts: melchior GO 88%
  (4 INFO findings), balthasar approve/GO_WITH_CAVEATS 88% (3 INFO),
  caspar approve 85% (3 INFO) — zero CRITICAL, zero WARNING, zero
  Conditions for Approval across all three. Effective consensus
  GO (3-0). Manual synthesis was treated as authoritative for the
  exit-criterion check; the synthesizer failure is exactly the
  v1.0.0 Feature F LOCKED item (MAGI dispatch hardening +
  marker-based discovery + tolerant agent-output parsing) manifesting
  empirically. The full v0.3.0 ship is the empirical justification
  to prioritize Feature F early in v1.0.0. Raw outputs and the
  manual synthesis are preserved in
  `.claude/magi-runs/v030-iter2/{melchior,balthasar,caspar}.raw.json`
  for the audit trail.

## [0.2.2] - 2026-04-25

### Documentation

- WARNING #12 (INV-31 default-on surprise risk) closed via prominent
  operational callout. README.md gains a per-environment matrix
  immediately after the install commands (quota-constrained /
  superpowers-missing / long-auto-run / standard) so users see the
  flip-`--skip-spec-review` decision before their first
  `/sbtdd close-task` or `/sbtdd auto`. SKILL.md gains a parallel
  `## Operational impact (INV-31 default-on)` section describing the
  symptom-action mapping and the 1-3 `claude -p` per-task cost. The
  prior callout (v0.2.1 commit `d6f1128`) remained accurate but was
  buried inside `### v0.2 flags`; v0.2.2 surfaces it as the first
  operational note new users encounter. Pure docs hotfix -- no code,
  no test changes, no behavior change.

## [0.2.1] - 2026-04-25

### Added

- B6 auto-feedback loop in `auto_cmd._phase2_task_loop`. When the
  spec-reviewer raises `SpecReviewError`, the new helper
  `_apply_spec_review_findings_via_mini_cycle` routes the reviewer's
  `issues` through `/receiving-code-review` (extending INV-29 to
  spec-review findings, not just MAGI conditions), runs a mini-cycle
  TDD fix (`test:` → `fix:` → `refactor:`) per accepted finding via
  `commits.create` (so prefix + English-only + no-AI guards fire), and
  re-dispatches the reviewer on the now-mutated diff. Outer safety
  valve `_B6_MAX_FEEDBACK_ITERATIONS=3` mirrors the INV-11 cadence
  used by Checkpoint 2 / pre-merge Loop 2; exhaustion re-raises
  `SpecReviewError` carrying the cumulative rejection history so
  operators see the trail without grepping logs. Spec-review budget
  (`auto_max_spec_review_seconds`) is charged per dispatch inside the
  feedback loop too, so a long mini-cycle still respects the cost
  guardrail.
- `receiving_review_dispatch.py` shared module promoting
  `RECEIVING_REVIEW_FORMAT_CONTRACT`, `parse_receiving_review`, and
  `conditions_to_skill_args` from their previous private names in
  `pre_merge_cmd`. Both `pre_merge_cmd._loop2` (Loop 2 MAGI
  conditions) and `auto_cmd._apply_spec_review_findings_via_mini_cycle`
  (B6) now consume the same single-sourced helpers. `pre_merge_cmd`
  retains the legacy private-name re-exports
  (`_RECEIVING_REVIEW_FORMAT_CONTRACT`, `_parse_receiving_review`,
  `_conditions_to_skill_args`) for backward compatibility with v0.2
  tests.
- 13 new regression tests across `tests/test_receiving_review_dispatch.py`
  (8 tests covering helper promotion + backward-compat re-exports) and
  `tests/test_auto_cmd_b6_feedback_loop.py` (5 tests covering
  accepted-finding mini-cycle, all-rejected re-dispatch, outer safety
  valve exhaustion, the `_B6_MAX_FEEDBACK_ITERATIONS=3` constant, and
  mini-cycle prefix-validation through `commits.create`).

### Changed

- `dispatch_spec_reviewer` default `max_iterations` reverted to `3`
  (was `1` in v0.2.0). v0.2.0 pinned this to 1 because the loop
  re-invoked the reviewer on byte-identical inputs (no feedback path
  mutated the diff between iterations), so iter 2+ burned quota for
  zero semantic benefit. v0.2.1 ships the auto-feedback loop above:
  accepted findings drive a mini-cycle TDD fix per outer iteration,
  giving the safety valve real work to do. The v0.2.0 regression test
  `test_dispatch_default_max_iterations_is_one_per_b6_defer` is renamed
  to `test_dispatch_default_max_iterations_is_three_per_b6_shipped`
  and asserts `default == 3`.

### Fixed

- INV-31 hard-block contract now honors the original spec-base §2.2
  promise: spec-reviewer issues no longer kill the whole autonomous
  execution at the first false positive. The contract widens to "MUST
  pass reviewer approval OR reach safety valve with documented
  rejections", with `--skip-spec-review` remaining available as the
  manual escape valve. On a 36-task `/sbtdd auto` run, a single
  reviewer issue at task 15 now triggers the feedback loop instead of
  aborting the run.

### Deferred (rolled to v0.2.2 or v1.0.0)

WARNING #11 (cost/latency guardrail) shipped in v0.2.0 hotfix
`70b8602` (`auto_max_spec_review_seconds` config + breadcrumb).
WARNING #17 (pending-marker race) shipped in v0.2.0 hotfix
`22b7e7d` (atomic write via tmp + os.replace).

## 0.1.7 - 2026-04-24

### Fixed

- `/test-driven-development` subprocess timeout default raised from
  600s to 1800s via `_SKILL_TIMEOUT_OVERRIDES`. Empirical v0.2 auto
  run G2 green phase (2026-04-24): the implementer subagent's combined
  read-plan + write-tests + implement + run-verify pass exceeded the
  600s default on a substantial task (root-cause classifier +
  `build_escalation_context`). Same pattern as the v0.1.2 bump for
  `/writing-plans`.

### Added

- 1 new regression test pins the `/test-driven-development` default
  timeout at 1800s (mirrors the existing `/writing-plans` test).

## 0.1.6 - 2026-04-24

### Fixed

- `auto_cmd._phase2_task_loop` CommitError recovery now covers two more
  cases beyond v0.1.5's HEAD-advanced branch:
  - **Unstaged tracked-file modifications**: the implementer subagent
    edited files but never ran `git add`. Auto now runs `git add -u`
    (tracked-file modifications only, no untracked surprises) and
    retries `commit_create`. Observed F2 green phase 2026-04-24: the
    subagent rewrote `_resolve_magi_plugin_json` + added
    `_magi_cache_base` but didn't stage, leaving the impl in the
    working tree while auto's commit failed with "nothing to commit".
  - **Phase-collapse empty commit**: if after `git add -u` there is
    STILL nothing staged (e.g., the implementer did red+green together
    in an earlier commit, leaving the current phase with no residual
    work), record a `git commit --allow-empty` marker so state still
    advances. Verification has already proven the phase's acceptance
    criterion is met; the empty commit carries a "(no-op; phase
    collapsed into earlier commit)" suffix for log legibility.

### Changed

- v0.1.5's test `test_auto_phase2_reraises_commit_error_when_head_did_not_move`
  renamed to `test_auto_phase2_allow_empty_fallback_when_head_did_not_move`
  and its assertion flipped: the HEAD-unchanged + nothing-staged path
  now records an empty marker commit instead of re-raising.

### Added

- 1 new regression test asserting `git add -u` captures tracked-file
  modifications (no empty marker; real phase content committed).

## 0.1.5 - 2026-04-24

### Fixed

- `auto_cmd._phase2_task_loop` now recovers when the implementer
  subagent commits phase work itself. `/writing-plans` emits plans
  with explicit `git add` + `git commit -m` steps per phase (plus
  `git commit --allow-empty` for refactor). The implementer following
  the plan literally commits each phase, leaving auto's own
  `commit_create` to hit an empty stage and raise `CommitError`
  ("nothing to commit"). Observed 2026-04-24 during the first
  successful F1 auto run: three plan-prescribed commits landed,
  then auto crashed at the refactor phase commit call. Recovery: wrap
  `commit_create` in `try/except CommitError`; on failure, verify
  HEAD SHA advanced past `pre_phase_sha` to confirm the implementer's
  commit is authoritative, then proceed. If HEAD did not advance,
  the error is genuine and re-raises.
- `close_task_cmd.mark_and_advance` skips the `git add` +
  `commit_create` steps when `flip_task_checkboxes` returns
  bytes-identical output (i.e., the plan checkboxes are already
  flipped to `[x]`). Previously it unconditionally ran the stage +
  commit, triggering `CommitError` and leaving state stuck at
  `current_phase=refactor`. State advance to the next open task
  still runs so bookkeeping doesn't stall.

### Added

- 3 new regression tests: two for `auto_cmd` (implementer-precommitted
  recovery + nothing-staged-nothing-committed re-raise) and one for
  `close_task_cmd` (no-op flip + state advance).

## 0.1.4 - 2026-04-24

### Fixed

- `superpowers_dispatch._build_skill_cmd` now packs the slash command
  and every skill arg into the single prompt string passed to
  `claude -p`, instead of appending them as separate argv tokens. The
  v0.1.0 shape `["claude", "-p", "/<skill>", "--flag"]` caused `claude`
  to parse `--flag` as one of its own CLI options and reject with
  `error: unknown option '<flag>'`. Observed when `/sbtdd auto`
  invoked `/test-driven-development --phase=red` (auto's phase loop).
  Same pattern fixed for `_build_magi_cmd` in v0.1.2 — now consistent
  across both dispatchers.

### Documentation

- `auto_cmd._phase2_task_loop` docstring now explicitly flags the
  task-loop's minimal prompt as a v0.1.x limitation. `/test-driven-development`
  is a prose-only skill with no formal `--phase` argument; the current
  call forwards the phase as a narrative hint and the sub-session
  discovers task context (id, plan path, files) by reading
  `session-state.json` and the plan on its own. Workable via
  `cwd=root` but fragile. **Feature B of v0.2** replaces this with an
  explicit task-context prompt builder.

### Added

- 1 new test in `test_superpowers_dispatch` asserting argv is exactly
  `["claude", "-p", "<single prompt>"]` and the prompt string embeds
  the slash command + every passed arg.

## 0.1.3 - 2026-04-24

### Fixed

- `check_stack_toolchain("python")` now invokes each tool via
  `[sys.executable, "-m", <module>, "--version"]` instead of
  `shutil.which(bare_name) + [bare_name, "--version"]`. Observed two
  false-negative modes on layered Python installs (2026-04-24): (a)
  `shutil.which("pytest")` resolved a stale Python 3.6 `pytest.EXE`
  from a Scripts/ directory on PATH that crashed with returncode=1 even
  though Python 3.14's `python -m pytest` ran the 609-test suite
  cleanly; (b) `ruff` / `mypy` installed only as modules under the
  active interpreter (no Scripts/ entry points exposed on PATH)
  reported MISSING. The new `_check_python_module_tool` helper aligns
  the check with `plugin.local.md`'s `verification_commands` (which
  already use `python -m <tool>`), maps `No module named` stderr to
  MISSING with a `pip install <tool>` remediation, and other non-zero
  exits to BROKEN. Rust + C++ stacks keep the binary-resolution path
  unchanged.

### Added

- 2 new tests in `test_dependency_check`: one pins the
  `[sys.executable, "-m", <module>, "--version"]` invocation form for
  all three Python-stack tools; one verifies `No module named` stderr
  maps to MISSING rather than BROKEN.

## 0.1.2 - 2026-04-24

### Fixed

- `magi_dispatch.invoke_magi` now packs the `--output-dir <tmpdir>` flag
  inside the single prompt string passed to `claude -p`, instead of
  appending it as separate argv tokens. The v0.1.1 fix appended the flag
  as bare argv entries after `-p /magi:magi`, which `claude` itself
  parsed — rejecting with `error: unknown option '--output-dir'`. The
  flag belongs to MAGI's `run_magi.py`, so it has to travel inside the
  prompt for the sub-session to forward it. Observed live: v0.2
  Checkpoint 2 converged in 2 iterations (HOLD_TIE → GO_WITH_CAVEATS
  full non-degraded) against real `claude -p` traffic with this change.
- `superpowers_dispatch` now defaults `/writing-plans` subprocess timeout
  to 1800s (was 600s). Empirical observation during v0.2 Checkpoint 2
  first run (2026-04-23): `/writing-plans` exceeded the 600s default
  even when the plan document was already fully written to disk — the
  sub-session spent non-trivial post-write time on closing actions, and
  the 600s SIGTERM aborted `/sbtdd spec` before MAGI Checkpoint 2 could
  run. Per-skill override table (`_SKILL_TIMEOUT_OVERRIDES`) lets other
  skills keep the 600s baseline; caller-supplied `timeout=` kwargs still
  win per-call.
- `dependency_check.check_tdd_guard_binary` now resolves the binary path
  via `shutil.which` and forwards the full path as `argv[0]` to the
  subprocess. On Windows, `npm install -g @nizos/tdd-guard` installs
  `tdd-guard.cmd` (a `.cmd` batch shim, not `.exe`); Python's
  `subprocess.run([...], shell=False)` does NOT apply PATHEXT and
  therefore raised `FileNotFoundError` (WinError 2) when argv[0] was the
  bare name `"tdd-guard"`. Observed as a crash in `auto` Phase 1
  preflight on 2026-04-24. Resolving the full path first makes the
  invocation work cross-platform without `shell=True`.

### Added

- 12 new tests covering the three fixes: 8 in `test_magi_dispatch`
  (prompt-string packing, disk-based report reading, split-suffix
  stripping, degraded flag propagation, missing/malformed report paths),
  3 in `test_superpowers_dispatch` (new default timeout pinning), 1 in
  `test_dependency_check` (Windows `.cmd` resolution regression guard).

## 0.1.1 - 2026-04-23

### Fixed

- `magi_dispatch.invoke_magi` no longer parses MAGI stdout as JSON. The
  canonical machine-readable output is `<output-dir>/magi-report.json` on
  disk; stdout is the ASCII banner + markdown report produced by
  `reporting.format_report`. v0.1.0 incorrectly called
  `json.loads(result.stdout)` which always failed with
  `ValidationError: MAGI output is not valid JSON: Expecting value: line 1
  column 1 (char 0)`, blocking every `/sbtdd spec` and `/sbtdd pre-merge`
  invocation. Fix follows the "Option 1" pattern (sbtdd-side only, zero
  changes to MAGI): `invoke_magi` now creates a `tempfile.TemporaryDirectory`,
  passes `--output-dir <tmpdir>` to the slash command, and reads
  `magi-report.json` from disk. stdout is preserved on
  `MAGIVerdict.raw_output` for diagnostics. Also added a new parser
  `parse_magi_report(report: dict, raw_output: str = "") -> MAGIVerdict`
  that handles MAGI's native structure (`consensus.consensus` banner label,
  top-level `degraded` flag, `consensus.conditions` list of
  `{agent, condition}` dicts). The label's optional `(N-M)` split suffix
  is stripped before normalisation via a new `_strip_magi_split_suffix`
  helper + `_MAGI_SPLIT_SUFFIX_RE` regex. `parse_verdict` retained
  unchanged for the sbtdd-flat `magi-verdict.json` artifact round-trip.

### Added

- 8 new tests in `test_magi_dispatch.py` covering the disk-based contract:
  happy path with `--output-dir` assertion, split-suffix stripping on
  labels, top-level `degraded` flag propagation, missing-report error
  path, malformed-JSON error path, `parse_magi_report` condition
  extraction, no-split-suffix labels (`STRONG GO` / `STRONG NO-GO` /
  `HOLD -- TIE`), missing-consensus rejection, unknown-label rejection.

## [0.2.0] - 2026-04-24

### BREAKING

- `auto_cmd._write_auto_run_audit` no longer accepts `dict` payloads.
  Callers must pass an `AutoRunAudit` instance. Rationale: strict
  schema enforcement per Milestone D hardening (MAGI pre-merge D iter 1
  Caspar finding). Migration: construct `AutoRunAudit(...)` from
  existing dict fields using `AutoRunAudit(**payload_dict)`. Field
  validation now raises `TypeError` on schema mismatch (previously
  silent dict-passthrough).
- INV-31 spec-reviewer gate ships as a HARD BLOCK in v0.2.0 (scope
  deviation from `sbtdd/spec-behavior-base.md` §2.2). Any spec-reviewer
  `issue` raises `SpecReviewError` (exit 12) and aborts the current
  task close. The §2.2 promise of routing through
  `/receiving-code-review` + mini-cycle TDD fix + re-dispatch up to the
  3-iter safety valve is **deferred to v0.2.1** (see Unreleased
  "B6 auto-feedback loop — LOCKED v0.2.1 release blocker"). Operators
  recover by either (a) passing `--skip-spec-review` to
  `close_task_cmd` / `auto_cmd` and reviewing manually, or (b) fixing
  the diff and re-running the subcommand. As a corollary,
  `dispatch_spec_reviewer` ships with default `max_iterations=1` in
  v0.2 (will revert to `3` in v0.2.1). Flagged by MAGI Loop 2 v0.2
  pre-merge 2026-04-24 as CRITICAL findings #4/#14 + WARNING #13.

### Added

- `AutoRunAudit` dataclass in `auto_cmd.py` formalising the
  `.claude/auto-run.json` schema.
- `MAGIGateError` kw-only typed attrs: `accepted_conditions`,
  `rejected_conditions`, `verdict`, `iteration`.
- Python 3.9 version floor enforcement in `dependency_check`.
- Cargo shim version regex validation (clippy / fmt / nextest / audit).
- `NEXTEST_EXPERIMENTAL_LIBTEST_JSON` env gate in `rust_reporter` to
  refuse running under incompatible nextest output modes.
- `ctest_reporter` now raises a specific `ValidationError` on empty
  JUnit XML rather than returning an empty suite.
- Resume mid-exit-8 detection via `.claude/magi-conditions.md`
  presence; `resume` directs the user to `sbtdd close-phase` for each
  pending condition before re-running `sbtdd pre-merge`.
- Pre-merge exit 8 emits a user-facing stderr summary explaining what
  to do next, so the exit code is self-explanatory without reading the
  conditions file first.
- `auto-run.json` is now written atomically via tmp + `os.replace`;
  a process killed mid-write leaves the previous audit intact.
- `pre_merge._loop2` unlinks any stale
  `.claude/magi-conditions.md` from a previous exit-8 run on entry, so
  successful gates never leave the trap file behind.
- INV-24 / INV-29 / TOCTOU contract docstrings on the relevant
  functions in `auto_cmd`, `pre_merge_cmd`, and `init_cmd`.

### Changed

- `auto_cmd._write_auto_run_audit`: strict `AutoRunAudit` signature
  only; schema is validated before any byte hits disk.
- `MAGIGateError`: optional kw-only typed attrs added; backward
  compatible for legacy positional callers.
- `resume_cmd._assert_state_stable_between_reads`: softened to only
  raise on CONTENT divergence between the two reads. mtime-only
  divergence emits a stderr warning and continues -- Windows NTFS
  editor saves bump mtime without rewriting bytes, and the previous
  strict check trapped users unnecessarily.
- `_read_audit_tasks_completed` now logs to stderr when falling back
  to `0`, so silent best-effort recovery is still observable.
- Cargo shim version regex tightened to per-shim anchored patterns
  (`clippy`, `rustfmt`, `cargo-nextest-nextest`, `cargo-audit-audit`)
  instead of the loose `^\w+\s+\d+\.\d+` pattern.

### Added (Milestone E -- distribution artifacts v0.1 ship)

- `skills/sbtdd/SKILL.md` orchestrator skill following the seven-section
  structure mandated by sec.S.6.3 (Overview -> Subcommand dispatch ->
  Complexity gate -> Execution pipeline -> sbtdd-rules -> sbtdd-tdd-cycle
  -> Fallback).
- `.claude-plugin/plugin.json` at version `0.1.0` (name `sbtdd-workflow`,
  dual license MIT OR Apache-2.0, `repository` field as a plain URL string
  matching MAGI v2.1.3's form, pointing to
  `github.com/BolivarTech/sbtdd-workflow`).
- `.claude-plugin/marketplace.json` BolivarTech catalog entry at version
  `0.1.0` synchronized with `plugin.json` (sec.S.3.3).
- Public `README.md` with four static shields (Python 3.9+, license, ruff,
  mypy), "Why SBTDD? Why multi-agent?" section, Installation (marketplace
  + local dev), Usage (nine-subcommand table + end-to-end flow),
  Architecture, and License sections (parity with MAGI `README.md`).
- `CONTRIBUTING.md` contributor guide with commit-prefix reference,
  pre-merge expectations, and invariant addition procedure.
- Five new contract test files covering the distribution artifacts:
  `tests/test_skill_md.py` (**19 tests**: see Task-by-task breakdown in the
  Acceptance section), `tests/test_plugin_manifest.py` (**11 tests**,
  includes 1 that skips when marketplace.json absent then asserts when
  present), `tests/test_marketplace_manifest.py` (**9 tests**),
  `tests/test_readme.py` (**22 tests**, 17 for README + 5 for
  CONTRIBUTING.md), and `tests/test_distribution_coherence.py`
  (**8 tests**: 6 cross-artifact + 2 MAGI-parity smoke — required-keys
  subset check + `repository` field-form check, both decorated with
  `@pytest.mark.skipif` when MAGI cache absent).
  **Total new: 69 tests** (528 baseline). Reachable totals: **595** (CI
  environment without MAGI cache installed — the 2 skipif-guarded MAGI
  parity tests skip), **597** (local development with MAGI cache present
  — every conditional test runs). Range reflects the skipif-guarded MAGI
  parity tests. Skip-aware phrasing mandated by F2 MAGI iter 2 to make
  the accounting exact.

### Changed

- `README.md`: rewrote from the previous single-line stub into the full
  user-facing GitHub README.

### Fixed

- `dispatch_spec_reviewer` default `max_iterations` pinned to `1` (was
  `3` in the original B6 design). v0.2 ships INV-31 as a HARD BLOCK: no
  feedback path mutates the reviewer input between iterations, so any
  iteration count above 1 would just re-emit the same `issues` and waste
  quota. The default reverts to `3` in v0.2.1 once the auto-feedback
  loop (B6) lands and gives the safety valve real work to do. See the
  Unreleased "B6 auto-feedback loop" entry above for the v0.2.1
  deliverables.

### Deferred (tracked for v0.2.0 — LOCKED release blockers only)

User directive session 2026-04-23: "solo vamos con lo lock a v0.2 todo lo demas a v0.3". Only the two LOCKED items below are v0.2.0 release blockers. Everything else originally in v0.2 backlog (CI workflow, schema_version, C++ adapters, $schema verification, MAGI parity refresh) moved to v0.3.0.

- **MAGI version-agnostic parity tests — LOCKED v0.2.0 release blocker**
  (user directive session 2026-04-23: "actualiza MAGI de una vez en v0.2").
  v0.1 `test_distribution_coherence.py` hardcodes MAGI cache path to
  version `2.1.3`. MAGI shipped v2.1.4 (patch bump, no schema change —
  verified: only `"version"` string differs between 2.1.3 and 2.1.4
  `plugin.json`; `marketplace.json` byte-identical). Rather than bump
  the hardcoded pin (repeating for every future patch), v0.2 MUST make
  the pin version-agnostic via a resolver that enumerates installed
  MAGI versions under `~/.claude/plugins/cache/bolivartech-plugins/magi/`
  and picks the latest by semver ordering. Implementation scope: rewrite
  `_resolve_magi_plugin_json()` in `test_distribution_coherence.py` to
  scan `cache_base.iterdir()`, sort by `_semver_key(version)` tuple
  `(major, minor, patch)`, pick max. Add `test_semver_key_handles_mixed_version_strings`
  validating tie-break + non-numeric handling. `MAGI_PLUGIN_ROOT` env var
  override preserved for CI. Graceful skipif on empty cache. Existing
  subset-based parity tests tolerate optional field additions from MAGI
  (Plan E iter-2 fix). Moved from v0.3 Group A (where it was tracked as
  "MAGI-version coupling refresh") to v0.2 LOCKED per session 2026-04-23
  directive. Full spec in local `CLAUDE.md` "v0.2 requirement (LOCKED) —
  MAGI version-agnostic parity tests" section.
- **Spec-reviewer integration per task — LOCKED v0.2.0 release blocker**
  (user directive session 2026-04-23: "para v0.2 solo 8, los demas para
  0.3"). v0.1 verifies code-vs-spec alignment only at two gates
  (Checkpoint 2 MAGI before code, pre-merge Loop 2 MAGI after all code) +
  TDD discipline during execution. Per-task spec drift surfaces only at
  pre-merge (e.g., Milestone A caspar caught `detect_drift` missing
  Scenario 4 at the final MAGI gate, not at Task 14/15 close). v0.2 MUST
  integrate `superpowers:subagent-driven-development/spec-reviewer-prompt.md`
  per task. Implementation scope: (a) `auto_cmd._phase2_task_loop` after
  implementer DONE + before `close_task_cmd.mark_and_advance` dispatches
  spec-reviewer subagent; input = task text + diff from task's commits;
  output = approved | issues. Issues route through `/receiving-code-review`
  (INV-29 gate extended) + mini-cycle fix + re-review; 3-iter safety valve.
  (b) `close_task_cmd --skip-spec-review` escape valve for manual flows.
  (c) New subcommand `/sbtdd review-spec-compliance <task-id>` for
  `executing-plans` / manual. (d) New module `spec_review_dispatch.py`
  with `SpecReviewResult` dataclass + audit artifact at
  `.claude/spec-reviews/<task-id>-<timestamp>.json`. (e) `StubSpecReviewer`
  in `skills_stubs.py`. (f) Proposed INV-31: every task close MUST pass
  spec-reviewer approval before `mark_and_advance` unless skip flag.
  Design invariants: reviewer on task diff + task text only (cost-bounded),
  issues through `/receiving-code-review`, non-TTY safe, audit artifact
  per invocation, quota-detector integrated (exit 11 on quota), safety
  valve 3 iters. Full spec + rationale in local `CLAUDE.md`
  "v0.2 requirement (LOCKED) — superpowers spec-reviewer integration"
  section. **Scope explicitly NOT in v0.2**: mechanical pre-filters,
  spec-snapshot diff, traceability matrix, per-phase MAGI-lite, auto-gen
  stubs, watermark comments, bespoke LLM drift detector → all deferred
  to v0.3.
- **Interactive escalation prompt on MAGI exhaustion — LOCKED v0.2.0
  release blocker** — v0.1 does NOT prompt the user interactively when
  the safety valve (INV-11) exhausts. It writes artifacts
  (`.claude/magi-conditions.md`, `.claude/magi-feedback.md`, iter-report.json),
  emits stderr summary, and exits 8. User must re-invoke manually. User
  explicitly requested (session 2026-04-21) that v0.2 reproduce the
  assistant-orchestrator conversation pattern observed through Milestones
  A-E: on exhaustion, the plugin MUST emit a structured diagnostic message
  (degraded analysis, per-agent verdicts, severity-classified findings,
  root-cause inference, 4 context-aware options labeled a/b/c/d) and
  accept a single-letter response to apply the decision. The canonical
  message template is captured verbatim in `CLAUDE.md` "v0.2 requirement
  (LOCKED)" section using the Plan D Checkpoint 2 iter 3 escalation as
  the reference (historic example: DEGRADED / Caspar JSON failure
  transient / 2/2 APPROVE unanime / 3 WARNINGs bajo-riesgo → user chose
  option `a` override → commit `5d7bfc4`). v0.2 implementation scope:
  (1) new module `escalation_prompt.py` with `build_escalation_context` /
  `format_escalation_message` / `prompt_user` / `apply_decision`;
  (2) root-cause inference classifying the failure (infra-transient,
  plan-vs-spec gap, structural defect, spec ambiguity) to compose options
  dynamically; (3) TTY-guarded `input()` with EOFError fallback + headless
  policy file `.claude/magi-auto-policy.json` for `auto_cmd`; (4)
  `--override-checkpoint --reason "<text>"` CLI flag with mandatory
  reason; (5) audit artifact `.claude/magi-escalations/<timestamp>.json`;
  (6) `resume_cmd` integration for Ctrl+C recovery; (7) golden-output
  unit tests per root-cause class × context. Design invariants: never
  runs inside `auto_cmd` (INV-22), every override produces audit artifact,
  non-TTY always safe (EOFError), backward-compat default = v0.1 behavior,
  language preserves Spanish + English mix matching session-observed
  convention, template ≤40 lines emitted. See CLAUDE.md for full spec.

### Deferred (tracked for v1.0.0)

> **v0.3 → v1.0.0 rename (user directive session 2026-04-25).** What was previously labelled the "v0.3.0" deferred backlog is now tracked under v1.0.0 -- the LOCKED items below (auto progress streaming, MAGI dispatch hardening + retried_agents, MAGI → /requesting-code-review cross-check) collectively raise the project past pre-1.0 status: stable Plugin manifest, stable session-state schema, ship-quality observability, and the validated MAGI cross-check pattern remove the "schema may change between minor versions" v0.1.x caveat. Historical references to "v0.3" inside the [0.2.0] release section above are kept verbatim (frozen historical record).

v1.0.0 backlog consolidates everything that is NOT a v0.2 LOCKED blocker per user directive session 2026-04-23. Two groupings: (A) operational/infra items originally in v0.2 backlog, now moved; (B) seven complementary spec-drift detection options layered on top of the v0.2 (8) primary integration.

#### Group A — operational / infra items (moved from v0.2)

- **MAGI → /requesting-code-review cross-check — v1.0.0 LOCKED PRIORITY**
  (user directive session 2026-04-25, validated empirically by user in
  unrelated projects). MAGI Loop 2 occasionally produces false-positive
  CRITICAL findings: it flags plan-described designs as if they were
  shipped code defects, or misreads existing safe patterns (e.g., the
  v0.2 pre-merge iter-3 `StopIteration` claim against
  `prompt_user`'s headless retry path -- disprovable by reading
  ``escalation_prompt.py`` line 241's ``next((... for ...), options[-1])``
  default + line 300's ``any(...)`` guard). Today the operator catches
  these manually via direct code inspection + ``magi-feedback.md``
  rejection rationale. The pattern that's been validated in adjacent
  projects: pipe MAGI's report through ``/requesting-code-review`` as a
  meta-reviewer that cross-checks each MAGI finding against actual
  code, then routes the cross-checked findings through INV-29's
  accept/reject gate. Findings both reviewers confirm get applied;
  findings MAGI flagged but ``/requesting-code-review`` disproves get
  auto-rejected with the disproving evidence captured in the audit
  trail. Findings ``/requesting-code-review`` discovers that MAGI
  missed get applied with high confidence.

  **Locked v1.0.0 deliverables:**

  1. New helper in ``magi_dispatch`` (or new ``magi_cross_check.py``
     module) -- ``cross_check_magi_findings(verdict, diff_paths) ->
     CrossCheckResult`` invoking ``claude -p /requesting-code-review``
     with the MAGI report + diff bundled, parsing accept/reject/new
     output from the meta-reviewer.
  2. ``pre_merge_cmd._loop2`` calls the cross-checker AFTER MAGI
     verdict + BEFORE ``/receiving-code-review`` INV-29 routing. The
     INV-29 gate now consumes the cross-checked finding list, not the
     raw MAGI list.
  3. Audit trail extends ``.claude/magi-verdict.json`` (or new
     ``.claude/magi-cross-check.json``) with the disproved findings +
     their disproving evidence.
  4. Documented as the ordering inversion of the legacy
     ``/requesting-code-review`` (Loop 1) → ``/magi:magi`` (Loop 2)
     pre-merge pipeline -- in the cross-check pattern, MAGI runs first
     for breadth, ``/requesting-code-review`` runs second for depth.
     CHANGELOG entry calls out the distinction so users of the existing
     ``pre-merge`` flow understand it's additive, not a replacement.

  **Why locked**: removes the most expensive failure mode of the v0.2
  pre-merge cycle -- sterile loops on MAGI false-positives where each
  re-iter burns ~30 min of MAGI quota for no semantic gain. User has
  used the pattern manually in adjacent projects with reported success.

- **MAGI dispatch hardening + retried_agents telemetry — v1.0.0 LOCKED**
  (user directive session 2026-04-25 post-v0.2.0 ship). Two related
  improvements over the v0.1.2 + v0.1.4 disk-read fix:

  **(a) Marker-based discovery as defensive fallback.** v0.1.2
  (`cdcdac9`) + v0.1.4 (`c9e8d55`) shipped a working pattern: pass
  ``--output-dir <tmpdir>`` packed inside the ``claude -p`` prompt,
  read ``<tmpdir>/magi-report.json`` from disk after the subprocess
  exits. This works but depends on the ``--output-dir`` flag
  travelling through the prompt-string contract intact -- if Claude
  Code's slash-command argument-passing semantics change, the temp
  dir is created but MAGI ignores it and writes to its own default
  location, leaving auto's reader looking at the wrong path.

  MAGI guarantees a stable contract since 2.0.0: ``run_magi.py`` line
  539 prints ``"\nFull report saved to: <path>"`` as its last stdout
  line, and the SKILL.md "MANDATORY FINAL OUTPUT CONTRACT" forces
  copy-verbatim into ``claude -p`` stdout. v1.0.0 should add a marker
  parser as fallback when the explicit ``--output-dir`` path is
  empty (or even as the primary strategy with ``--output-dir`` as
  belt-and-suspenders override).

  **(b) ``retried_agents`` field extraction (MAGI 2.2.1+).** New
  telemetry MAGI emits when an agent retries: ``"retried_agents":
  ["caspar"]`` at the report-top-level. ``MAGIVerdict`` should grow a
  ``retried_agents: tuple[str, ...]`` field (default empty tuple for
  MAGI 2.0.x-2.1.x compatibility). Surfaces signal that's currently
  invisible to the gate logic -- a verdict that needed a retry is
  not the same risk profile as a clean first-pass verdict, even when
  the label is identical.

  **Locked v1.0.0 deliverables (all six TDD steps, single mini-cycle
  is fine since the parser change is small):**

  1. Add ``MAGIVerdict.retried_agents: tuple[str, ...]`` (default
     ``()``); existing constructors / tests keep working because the
     field is keyword-only with a default.
  2. Add ``_REPORT_PATH_RE = re.compile(r"^Full report saved to:
     \s*(.+?)\s*$", re.MULTILINE)`` module-level constant.
  3. Add ``_load_magi_report_from_marker(stdout: str) -> dict`` helper
     that scans stdout for the marker, validates the path exists,
     reads + json.loads the file. Raises ``ValidationError`` on each
     of: marker absent, file missing, JSON malformed.
  4. ``invoke_magi`` keeps ``--output-dir`` for now but reads via the
     marker (single source of truth). Falls back to the
     ``--output-dir`` path only if the marker is absent (defensive).
  5. ``parse_magi_report`` extracts ``retried_agents`` alongside the
     existing ``degraded`` / ``failed_agents``.
  6. Six regression tests: marker present + valid file (happy path),
     marker absent (ValidationError), file missing, JSON malformed,
     ``retried_agents`` present (extracts list), ``retried_agents``
     absent (empty tuple, not error).

  **Why locked, not deferred:** v0.2 dogfood shipped the disk-read
  fix under quota pressure (4 patches v0.1.2 → v0.1.7 inside a single
  multi-hour cycle). The marker-based approach removes the fragile
  prompt-string flag-passing dependency entirely; combined with
  ``retried_agents`` telemetry, the dispatcher gains both robustness
  and observability the v0.2 baseline lacks.

- **Auto progress streaming — v1.0.0 LOCKED PRIORITY** (user directive
  session 2026-04-24 after observing v0.2 auto runs). **UX problem**:
  the subprocess stdout is pipe-buffered (Python stdio + ``tee``) so a
  multi-hour run of ``/sbtdd auto`` shows an empty log file while ~60
  commits land on git. Visually indistinguishable from a hung process
  — the user repeatedly asked "is it doing anything?" during v0.2 runs
  because there was no observable signal other than polling git log
  and ``session-state.json`` manually. The silence is a real failure
  mode: users will Ctrl+C a working process because they assume it
  stalled, losing hours of autonomous execution.

  **Locked v1.0.0 deliverables** (all four land together; individually
  insufficient):

  1. **Unbuffered dispatcher invocation.** ``run_sbtdd.py`` must call
     ``sys.stdout.reconfigure(line_buffering=True)`` (or set
     ``PYTHONUNBUFFERED=1`` / document ``python -u`` invocation) so
     every print flushes immediately. Applies to both the orchestrator
     and every subprocess wrapper (``claude -p``, ``git`` wrappers).
  2. **Per-phase progress line on stderr.** Every phase entry/exit
     emits a structured line to ``sys.stderr`` (stderr is
     line-buffered by default on most platforms and survives ``tee``
     better): format ``[auto] <ISO-8601> task=<id> phase=<name>
     action=<start|verify|commit|done> sha=<head>``. Grep-friendly,
     tooling-parseable, cheap.
  3. **Periodic ``.claude/auto-run.json`` updates.** The existing
     audit artifact gains a ``current_task_id`` + ``current_phase`` +
     ``last_updated_at`` triple written at every phase transition so
     ``/sbtdd status`` can tail it mid-run and report live progress.
     Schema change: bump ``_AUTO_RUN_SCHEMA_VERSION`` to 2, add the
     three fields as optional (backward compat).
  4. **``/sbtdd status --watch`` flag.** New read-only mode that tails
     ``session-state.json`` + ``auto-run.json`` + ``git log`` every N
     seconds, prints a compact dashboard line: ``12/28 tasks · H6/green
     · HEAD=cced3ec · 76min elapsed · est. 2-4h remaining``. Lets the
     user observe progress without reading the log file directly.

  **Why locked and not deferred**: the UX problem is not cosmetic —
  it actively undermines trust in ``auto`` and leads users to kill
  working runs. Every v0.2 auto invocation to date has triggered the
  same "is it hung?" question from the operator. Shipping v0.2 without
  addressing this ships a feature that people won't use beyond the
  first hour. Counterexample: MAGI v2.1.4 prints a per-agent banner
  + per-iteration summary to stderr, so a MAGI invocation is visibly
  progressing even when individual agent subprocess calls take 10+
  minutes. Mirror that pattern.

  **Testing**: golden tests on the stderr progress-line format
  (line-by-line comparison tolerating only the ISO-8601 timestamp),
  + integration test running a one-task stub plan and asserting that
  ``.claude/auto-run.json`` contains ``current_task_id`` after each
  simulated phase transition.
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) running `make verify`
  on push and PR, with a live "tests passing" shield (Milestone E intentionally
  ships without a `tests-passing` badge rather than publish a fake one — F2 of
  MAGI Checkpoint 2 Plan E iter 1).
- `schema_version` field in `plugin.local.md` (sec.S.13 item 5).
- GoogleTest / Catch2 / bazel / meson adapters for C++ stack (sec.S.13 item 7).
- Verify `marketplace.json` `$schema` URL
  (`https://anthropic.com/claude-code/marketplace.schema.json`) resolves
  post-push. Fallback: drop the field across both plugins in lockstep if
  Anthropic removes it or Claude Code emits a warning (F6 MAGI iter 2).
- ~~MAGI-version coupling refresh~~ — **MOVED to v0.2 LOCKED blockers**
  per user directive session 2026-04-23 ("actualiza MAGI de una vez en
  v0.2"). See v0.2.0 section above for the version-agnostic resolver spec.

#### Group B — complementary spec-drift detection options (full matrix in local CLAUDE.md)

- **(1) `scenario_coverage_check.py`** — mechanical regex pre-filter parsing `sbtdd/spec-behavior.md §4` + grep'ing `tests/` for scenario references. Runs at `close-task` before invoking v0.2 reviewer to skip tasks trivially covered. Cost: zero (stdlib).
- **(2) Spec-snapshot diff** — `planning/spec-snapshot.json` captured at plan approval; pre-merge entry diffs current spec-behavior.md against snapshot; silent spec edits fail gate. Orthogonal audit layer catching a risk class (8) cannot. **Proposed LOCKED for v1.0.0 regardless of v0.2 empirical data.**
- **(3) Inverted traceability matrix** — per-task `Scenario coverage:` line in plan; `close-task` validates the task's diff references scenarios listed. Plan-writer accountability.
- **(4) Per-phase MAGI-lite** — `/magi:magi analysis` on task diff + task scenarios (not full spec) at each `close-phase refactor`. 3-perspective semantic check (higher fidelity than (8)'s 1-perspective). Opt-in via flag; cost-expensive.
- **(5) Auto-generated scenario stubs** — extend `/writing-plans` to emit `test_<scenario_N>_<slug>()` skeletons; missing = Checkpoint 2 failure. Plan-time enforcement upstream of any runtime check. **Strong candidate for v1.0.0 LOCKED** if v0.2 shows planners forgetting scenarios.
- **(6) Watermark comments** — `# Implements: spec-behavior.md §4.X` + lint rule. Human-readable traceability surviving refactors.
- **(7) LLM drift detector** — dedicated `spec_drift_detector.py` invoking `claude -p` full spec + diff at `close-phase`. Mostly redundant with (8); keep as opt-in for cross-task semantic drift.

**Tentative v1.0.0 minimum viable** (subject to v0.2 empirical data): Group A items per operational need + Group B (2) + (5). Optional: (1) as pre-filter if (8) cost proves problematic. (3), (4), (6), (7) opt-in via flags.

(Milestones A-C changelog is implied from the git log; post-v0.1
releases will carry fully human-curated entries. Milestone E is the last
milestone before the `v0.1.0` public ship tag. v0.2 release blockers:
interactive MAGI escalation prompt + superpowers spec-reviewer integration
ONLY. Originally tracked as v0.3; renamed to v1.0.0 per user directive
session 2026-04-25 because the scope (auto progress streaming + MAGI
dispatch hardening + MAGI cross-check pattern + spec-drift options)
collectively pushes the project past pre-1.0 caveats. Group A
operational items + complementary spec-drift options (1)-(7),
re-evaluated with v0.2 field data.)
