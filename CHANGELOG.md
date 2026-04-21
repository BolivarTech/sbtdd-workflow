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
- **Continuous spec-drift detection** — v0.1 verifies code-vs-spec
  alignment only at two gates (Checkpoint 2 MAGI before code, pre-merge
  Loop 2 MAGI after all code). Gaps can surface only at pre-merge (e.g.,
  Milestone A caspar caught `detect_drift` missing Scenario 4). Evaluate
  for v0.2 (full option matrix + decision rationale in local
  `CLAUDE.md`; public-facing summary here): (1) `scenario_coverage_check.py`
  parsing `sbtdd/spec-behavior.md §4` + enforcing at least one test
  per scenario at `close-task`; (2) spec-snapshot diff check at
  pre-merge entry via `planning/spec-snapshot.json`; (3) inverted
  traceability matrix — per-task `Scenario coverage:` line in plan;
  (4) per-phase MAGI-lite analysis on each `close-phase refactor`;
  (5) auto-generated scenario test stubs from `/writing-plans`; (6)
  `# Implements: spec-behavior.md §4.X` watermark comments + lint
  rule; (7) LLM-based drift detector invoking `claude -p` at
  `close-phase`. Recommended minimum: (1) + (5); (2) as audit; (4)/(7)
  opt-in via `--spec-drift-check` flag. Rationale: Milestone A's
  Scenario-4 class of defects (plan-level tests green but spec-level
  scenario uncovered) is the target; options 1-3 are mechanical,
  4-7 are semantic.
- **Interactive escalation prompt on MAGI exhaustion** — v0.1 does NOT
  prompt the user interactively when the safety valve (INV-11) exhausts.
  It writes artifacts (`.claude/magi-conditions.md`, `.claude/magi-feedback.md`,
  iter-report.json), emits stderr summary, and exits 8. User must re-invoke
  manually. Deliberate for headless contexts (auto_cmd INV-22 sequential,
  CI, non-TTY). But for interactive `spec_cmd` and `pre_merge_cmd`, a
  guided prompt would materially improve UX. During Milestone D Checkpoint
  2 iter 3 DEGRADED, the assistant-orchestrator presented options a/b/c/d
  in chat and the user replied `a`; that conversation pattern could be
  native to the plugin. Evaluate for v0.2: (1) `input()`-based prompt in
  `spec_cmd`/`pre_merge_cmd` when `sys.stdin.isatty()` and no `--non-interactive`
  flag, offering `(a)` INV-0 override, `(b)` retry iteration, `(c)` abandon,
  `(d)` v0.1 behavior; (2) `--override-checkpoint --reason "<text>"` CLI
  flag with mandatory reason string (paired with decision-record artifact
  at `.claude/magi-escalations/<timestamp>.json` for audit trail); (3)
  `.claude/magi-auto-policy.json` upfront config for `auto_cmd` headless
  path (`{on_exhausted: "abort" | "override_strong_go_only" | "retry_once"}`,
  default `abort`); (4) `resume_cmd` detects `.claude/magi-escalation-pending.md`
  and prompts resume if user Ctrl+C-ed the original prompt. Design
  invariants: skippable in non-TTY (EOFError wrap, same pattern as
  `resume_cmd`), forbidden in `auto_cmd` (INV-22), every override produces
  audit artifact, default behavior = v0.1 (backward compat), `--reason`
  mandatory on override. Target: automate the chat-orchestrator
  conversation pattern observed through Milestones A-E.

(Milestones A-C changelog is implied from the git log; post-v0.1
releases will carry fully human-curated entries. Milestone E is the last
milestone before the `v0.1.0` public ship tag.)
