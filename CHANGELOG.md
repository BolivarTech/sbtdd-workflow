# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with
subsections BREAKING / Added / Changed / Fixed / Deprecated / Removed.

The plugin is pre-1.0 (`v0.1.x`); the CHANGELOG starts recording changes
introduced during Milestone D hardening and will be human-curated for
every post-v0.1 release.

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

## Unreleased

### BREAKING

- `auto_cmd._write_auto_run_audit` no longer accepts `dict` payloads.
  Callers must pass an `AutoRunAudit` instance. Rationale: strict
  schema enforcement per Milestone D hardening (MAGI pre-merge D iter 1
  Caspar finding). Migration: construct `AutoRunAudit(...)` from
  existing dict fields using `AutoRunAudit(**payload_dict)`. Field
  validation now raises `TypeError` on schema mismatch (previously
  silent dict-passthrough).

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

### Deferred (tracked for v0.3.0)

v0.3 backlog consolidates everything that is NOT a v0.2 LOCKED blocker per user directive session 2026-04-23. Two groupings: (A) operational/infra items originally in v0.2 backlog, now moved; (B) seven complementary spec-drift detection options layered on top of the v0.2 (8) primary integration.

#### Group A — operational / infra items (moved from v0.2)

- **Auto progress streaming — v0.3 LOCKED PRIORITY** (user directive
  session 2026-04-24 after observing v0.2 auto runs). **UX problem**:
  the subprocess stdout is pipe-buffered (Python stdio + ``tee``) so a
  multi-hour run of ``/sbtdd auto`` shows an empty log file while ~60
  commits land on git. Visually indistinguishable from a hung process
  — the user repeatedly asked "is it doing anything?" during v0.2 runs
  because there was no observable signal other than polling git log
  and ``session-state.json`` manually. The silence is a real failure
  mode: users will Ctrl+C a working process because they assume it
  stalled, losing hours of autonomous execution.

  **Locked v0.3 deliverables** (all four land together; individually
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
- **(2) Spec-snapshot diff** — `planning/spec-snapshot.json` captured at plan approval; pre-merge entry diffs current spec-behavior.md against snapshot; silent spec edits fail gate. Orthogonal audit layer catching a risk class (8) cannot. **Proposed LOCKED for v0.3 regardless of v0.2 empirical data.**
- **(3) Inverted traceability matrix** — per-task `Scenario coverage:` line in plan; `close-task` validates the task's diff references scenarios listed. Plan-writer accountability.
- **(4) Per-phase MAGI-lite** — `/magi:magi analysis` on task diff + task scenarios (not full spec) at each `close-phase refactor`. 3-perspective semantic check (higher fidelity than (8)'s 1-perspective). Opt-in via flag; cost-expensive.
- **(5) Auto-generated scenario stubs** — extend `/writing-plans` to emit `test_<scenario_N>_<slug>()` skeletons; missing = Checkpoint 2 failure. Plan-time enforcement upstream of any runtime check. **Strong candidate for v0.3 LOCKED** if v0.2 shows planners forgetting scenarios.
- **(6) Watermark comments** — `# Implements: spec-behavior.md §4.X` + lint rule. Human-readable traceability surviving refactors.
- **(7) LLM drift detector** — dedicated `spec_drift_detector.py` invoking `claude -p` full spec + diff at `close-phase`. Mostly redundant with (8); keep as opt-in for cross-task semantic drift.

**Tentative v0.3 minimum viable** (subject to v0.2 empirical data): Group A items per operational need + Group B (2) + (5). Optional: (1) as pre-filter if (8) cost proves problematic. (3), (4), (6), (7) opt-in via flags.

(Milestones A-C changelog is implied from the git log; post-v0.1
releases will carry fully human-curated entries. Milestone E is the last
milestone before the `v0.1.0` public ship tag. v0.2 release blockers:
interactive MAGI escalation prompt + superpowers spec-reviewer integration
ONLY. v0.3 scope: all operational items originally in v0.2 backlog +
complementary spec-drift options (1)-(7), re-evaluated with v0.2 field
data.)
