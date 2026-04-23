# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) with
subsections BREAKING / Added / Changed / Fixed / Deprecated / Removed.

The plugin is pre-1.0 (`v0.1.x`); the CHANGELOG starts recording changes
introduced during Milestone D hardening and will be human-curated for
every post-v0.1 release.

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

### Deferred (tracked for v0.2.0)

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
- MAGI-version coupling in parity tests — track for v0.2 if MAGI v2.2+
  changes schema (Caspar iter 3 final recommendation). The two parity
  tests in `test_distribution_coherence.py` (required-keys subset check
  + `repository` field-form check) pin against MAGI v2.1.3 artifacts
  cached locally; if MAGI evolves its manifest schema, these tests must
  be refreshed against the new cache snapshot to remain meaningful.
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

v0.3 backlog composed of the seven complementary spec-drift detection options evaluated alongside the v0.2 spec-reviewer integration but explicitly deferred per user directive session 2026-04-23. These layer on top of the v0.2 (8) primary integration to add mechanical cheap filters, plan-time enforcement, and audit extensions. Full option matrix + rationale in local `CLAUDE.md` "v0.3 backlog — complementary spec-drift detection options".

- **(1) `scenario_coverage_check.py`** — mechanical regex pre-filter parsing `sbtdd/spec-behavior.md §4` + grep'ing `tests/` for scenario references. Runs at `close-task` before invoking v0.2 reviewer to skip tasks trivially covered. Cost: zero (stdlib).
- **(2) Spec-snapshot diff** — `planning/spec-snapshot.json` captured at plan approval; pre-merge entry diffs current spec-behavior.md against snapshot; silent spec edits fail gate. Orthogonal audit layer catching a risk class (8) cannot. **Proposed LOCKED for v0.3 regardless of v0.2 empirical data.**
- **(3) Inverted traceability matrix** — per-task `Scenario coverage:` line in plan; `close-task` validates the task's diff references scenarios listed. Plan-writer accountability.
- **(4) Per-phase MAGI-lite** — `/magi:magi analysis` on task diff + task scenarios (not full spec) at each `close-phase refactor`. 3-perspective semantic check (higher fidelity than (8)'s 1-perspective). Opt-in via flag; cost-expensive.
- **(5) Auto-generated scenario stubs** — extend `/writing-plans` to emit `test_<scenario_N>_<slug>()` skeletons; missing = Checkpoint 2 failure. Plan-time enforcement upstream of any runtime check. **Strong candidate for v0.3 LOCKED** if v0.2 shows planners forgetting scenarios.
- **(6) Watermark comments** — `# Implements: spec-behavior.md §4.X` + lint rule. Human-readable traceability surviving refactors.
- **(7) LLM drift detector** — dedicated `spec_drift_detector.py` invoking `claude -p` full spec + diff at `close-phase`. Mostly redundant with (8); keep as opt-in for cross-task semantic drift.

**Tentative v0.3 minimum viable** (subject to v0.2 empirical data): (2) + (5). Optional: (1) as pre-filter if (8) cost proves problematic. (3), (4), (6), (7) opt-in via flags.

(Milestones A-C changelog is implied from the git log; post-v0.1
releases will carry fully human-curated entries. Milestone E is the last
milestone before the `v0.1.0` public ship tag. v0.2 release blockers:
interactive MAGI escalation prompt + superpowers spec-reviewer integration.
v0.3 scope: complementary spec-drift options (1)-(7) re-evaluated with
v0.2 field data.)
