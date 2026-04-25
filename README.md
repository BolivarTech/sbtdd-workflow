# SBTDD Workflow -- Spec + Behavior + Test Driven Development Orchestrator

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT%20OR%20Apache--2.0-blue.svg)](#license)
[![Ruff](https://img.shields.io/badge/linter-ruff-orange.svg)](https://docs.astral.sh/ruff/)
[![Mypy](https://img.shields.io/badge/types-mypy%20strict-informational.svg)](https://mypy-lang.org/)

<!--
F2 rationale: a live "tests passing" badge requires a GitHub Actions workflow
publishing status. Milestone E ships v0.1.0 without CI configured; we therefore
ship only the four static shields above. A dynamic "tests passing" shield
(backed by `.github/workflows/ci.yml` running `make verify`) is scheduled for
v0.2.0 and tracked under CHANGELOG's `## Unreleased` section as a deferred item.
-->


A Claude Code plugin that operationalizes **SBTDD (Spec + Behavior + Test Driven Development)** combined with the **Superpowers multi-agent skill ecosystem**.

One skill (`/sbtdd`), nine subcommands, five invariant-preserving phases: from blank spec to ship-ready branch, with mandatory pre-merge gates driven by code review + MAGI multi-perspective consensus.

---

## Why SBTDD? Why multi-agent?

### The problem

Classical TDD (Red-Green-Refactor) disciplines the implementation step, but leaves upstream decisions -- what to build, how to model the behavior, whether the design is sound -- as prose and intuition. Two chronic failure modes follow:

- **Scope drift:** the implementation satisfies its tests but diverges from the original intent because the intent was never written down atomically.
- **Local optimization:** each test passes, each commit is clean, yet the accumulated design has trade-offs nobody surfaced explicitly.

### The SBTDD answer

SBTDD layers three complementary disciplines:

| Discipline | Artifact | Authority |
|------------|----------|-----------|
| **SDD** (Spec Driven Development) | `sbtdd/spec-behavior.md` | Source of truth for what the system does |
| **BDD** (Behavior Driven Development) | Given/When/Then scenarios inside the spec | Translates intent into testable observations |
| **TDD** (Test Driven Development) | `planning/claude-plan-tdd.md` + commits | Enforces the Red-Green-Refactor discipline |

No behavior is implemented that is not declared in the spec; no code lands without a failing test reproducing its behavior; every commit is atomic and prefixed (`test:` / `feat:` / `fix:` / `refactor:` / `chore:` / `docs:`).

### Why multi-agent pre-merge?

SBTDD gates every branch through **two independent review loops** before merge:

1. **Loop 1 -- automated code review** (`/requesting-code-review`): mechanical findings (security, style, obvious bugs) are surfaced and applied via mini-cycle TDD until the diff is clean.
2. **Loop 2 -- MAGI multi-perspective review** (`/magi:magi`): three agents (Scientist, Pragmatist, Critic) evaluate trade-offs from orthogonal lenses. Their consensus -- not any single verdict -- is the gate.

Why separate? A WARNING from a mechanical reviewer can drag the MAGI agents into CONDITIONAL verdicts, contaminating the signal. Running them sequentially and independently keeps each verdict unambiguous (see CLAUDE.local.md sec.6).

### When does it pay off?

SBTDD is optimized for:

- Features with **genuine uncertainty** about the design.
- Branches whose **cost of regression is high**.
- Teams that value **auditability over speed** (every decision is a commit message).

For trivial fixes or exploratory hacks, use the fallback manual mode -- the full gate is intentionally friction-rich for non-trivial work.

---

## Installation

### From GitHub (for users)

```bash
# 1. Add the BolivarTech marketplace as a source
/plugin marketplace add BolivarTech/sbtdd-workflow

# 2. Install the plugin
/plugin install sbtdd-workflow@bolivartech-sbtdd

# 3. Bootstrap a project that uses SBTDD
cd /path/to/your/project
/sbtdd init
```

To update after new versions are published:

```bash
/plugin marketplace update
```

### Local Development

```bash
# Option 1: Plugin flag (explicit path, one-shot)
claude --plugin-dir /path/to/sbtdd-workflow

# Option 2: Symlink for auto-discovery (no flags needed)
mkdir -p .claude/skills
ln -s ../../skills/sbtdd .claude/skills/sbtdd
claude
```

The `.claude/` directory is gitignored; each developer creates their own symlink locally. Changes are picked up with `/reload-plugins` without restarting.

---

## Usage

Invoke with `/sbtdd <subcommand>` or natural trigger phrases ("advance TDD phase", "run pre-merge review", "sbtdd status").

### The nine subcommands

| Subcommand | Purpose | Typical invocation |
|------------|---------|--------------------|
| `init` | Bootstrap an SBTDD project (rules, hooks, skeleton spec, .gitignore entries) | `/sbtdd init --stack python --author "Your Name"` |
| `spec` | Run the spec pipeline: `/brainstorming` -> `/writing-plans` -> MAGI Checkpoint 2 | `/sbtdd spec` |
| `close-phase` | Close one TDD phase atomically (Red/Green/Refactor): verify + commit + advance state | `/sbtdd close-phase` (or `close-phase --variant fix` for Green-as-fix) |
| `close-task` | Mark `[x]` in the plan + `chore:` commit + advance to the next `[ ]` | `/sbtdd close-task` (auto-invoked by `close-phase refactor`) |
| `status` | Read-only structured report of state + git + plan + drift | `/sbtdd status` |
| `pre-merge` | Run Loop 1 (code review) then Loop 2 (MAGI) sequentially | `/sbtdd pre-merge` |
| `finalize` | Run sec.M.7 checklist + `/finishing-a-development-branch` | `/sbtdd finalize` |
| `auto` | Shoot-and-forget full cycle (task loop + pre-merge + checklist), stops before finalize | `/sbtdd auto` or `/sbtdd auto --dry-run` |
| `resume` | Diagnose interrupted runs and delegate recovery | `/sbtdd resume` or `/sbtdd resume --discard-uncommitted` |
| `review-spec-compliance` | Per-task spec-reviewer dispatch for manual flows (Feature B, new in v0.2). Exit 0 on approve, exit 12 on issues. | `/sbtdd review-spec-compliance <task-id>` |

### New in v0.2

- `--override-checkpoint --reason "<text>"` (on `spec`, `pre-merge`, `finalize`) -- INV-0 escape valve when a MAGI safety valve (INV-11) exhausts. `--reason` is mandatory; reason + verdict are persisted under `.claude/magi-escalations/`.
- `--non-interactive` (on `spec`, `pre-merge`) -- force the headless policy even on a TTY; applies `.claude/magi-auto-policy.json` (default `abort`).
- `--skip-spec-review` (on `close-task`) -- bypass the Feature B spec-reviewer dispatch for manual flows where compliance has already been verified by hand.

> **BREAKING — INV-31 hard block (v0.2.0).** `close-task` and `auto` now invoke the Feature B spec-reviewer by default. When the reviewer flags any issue (`SpecReviewError`, exit code **12**), the failing subcommand aborts and the operator must either fix the diff and re-run, or pass `--skip-spec-review` after manually verifying compliance. The v0.2 promise of routing reviewer issues through a `/receiving-code-review` + mini-cycle TDD feedback loop with up to 3 retry iterations is **deferred to v0.2.1** -- in v0.2.0 a single reviewer issue mid-`/sbtdd auto` aborts the whole run. Operators running quota-constrained or non-superpowers-enabled environments should set `--skip-spec-review` explicitly until v0.2.1 ships.

### Typical end-to-end flow

```bash
# 1. Bootstrap (once per project)
/sbtdd init --stack python --author "Your Name"

# 2. Write the spec base, then run the spec pipeline
#    (drafts spec-behavior.md, claude-plan-tdd-org.md, iterates via MAGI)
/sbtdd spec

# 3. Execute the plan
#    Option A: manual (one phase at a time)
/sbtdd close-phase            # after implementing Red
/sbtdd close-phase            # after Green (or: --variant fix)
/sbtdd close-phase            # after Refactor (auto-invokes close-task)
# ... repeat for each task ...

#    Option B: shoot-and-forget
/sbtdd auto

# 4. Pre-merge gates
/sbtdd pre-merge              # Loop 1 (code review) + Loop 2 (MAGI)

# 5. Finalize (runs the checklist + /finishing-a-development-branch)
/sbtdd finalize
```

### Direct CLI (bypassing the skill)

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/sbtdd/scripts/run_sbtdd.py <subcommand> [args...]
```

See `python skills/sbtdd/scripts/run_sbtdd.py --help` for the full flag reference.

---

## How it works

```
User input
  |
  v
/sbtdd skill (SKILL.md) -- complexity gate + subcommand parsing
  |
  v
run_sbtdd.py (dispatcher) -- validates preconditions + loads state
  |
  v
{subcommand}_cmd.py (one per subcommand)
  |
  +-- init_cmd.py       -- 5-phase bootstrap (pre-flight -> atomic gen -> smoke test)
  +-- spec_cmd.py       -- /brainstorming -> /writing-plans -> MAGI Checkpoint 2
  +-- close_phase_cmd.py-- drift check -> verify -> atomic commit -> state advance
  +-- close_task_cmd.py -- mark [x] + chore: commit + advance to next task
  +-- status_cmd.py     -- read-only report (state + git + plan + drift)
  +-- pre_merge_cmd.py  -- Loop 1 (review) -> Loop 2 (MAGI gate)
  +-- finalize_cmd.py   -- checklist validation + /finishing-a-development-branch
  +-- auto_cmd.py       -- 5-phase autonomous cycle (task loop + pre-merge + sec.M.7)
  +-- resume_cmd.py     -- diagnostic + delegation after interruption
```

### State model

Four orthogonal artifacts, each with exactly one writer:

- **`.claude/plugin.local.md`** (user) -- project rules (stack, verification commands, MAGI thresholds).
- **`.claude/session-state.json`** (plugin) -- canonical present (active task + phase).
- **Git commits + branch** (plugin) -- canonical past (immutable timeline).
- **`planning/claude-plan-tdd.md`** (plugin) -- canonical future + completion registry.

Drift between the three plugin-owned artifacts is detected but NEVER auto-reconciled (INV-17). The agent surfaces the divergence and defers to the user.

### Invariants

30+ invariants are enforced across the plugin surface. The most critical:

- **INV-0:** `~/.claude/CLAUDE.md` has absolute precedence over every other configuration.
- **INV-1:** Phase closes are atomic (commit + state + plan consistent after each operation).
- **INV-5..8:** Commit discipline (English, no Co-Authored-By, no AI refs, atomic, prefixed).
- **INV-9:** Pre-merge Loop 2 requires Loop 1 clean-to-go first (no parallel loops).
- **INV-11:** Every MAGI loop has a hard iteration cap; exceeding escalates with candidate root causes.
- **INV-27:** Spec base cannot contain the three uppercase placeholder markers (enumerated in sec.S.10.4 of the contract).
- **INV-28:** MAGI degraded verdict (fewer than 3 agents) never counts as loop-exit.
- **INV-29:** Every MAGI finding passes through `/receiving-code-review` before a mini-cycle TDD applies it.
- **INV-30:** Every interrupted run is resumable via `/sbtdd resume`.

The full list lives in `sbtdd/sbtdd-workflow-plugin-spec-base.md sec.S.10`.

---

## Architecture

```
.claude-plugin/
  plugin.json                 -- Plugin manifest (name, version, author, repository)
  marketplace.json            -- BolivarTech marketplace catalog entry
skills/sbtdd/
  SKILL.md                    -- Orchestrator (complexity gate + dispatch + embedded rules)
  scripts/
    __init__.py
    run_sbtdd.py              -- Entrypoint: python run_sbtdd.py <subcommand> [args]
    models.py                 -- Immutable registries (prefix map, verdict ranks)
    errors.py                 -- SBTDDError hierarchy + EXIT_CODES mapping
    config.py                 -- plugin.local.md parser (YAML frontmatter)
    state_file.py             -- session-state.json read/write/validate
    commits.py                -- git commit helpers with prefix validation
    hooks_installer.py        -- Idempotent merge of .claude/settings.json
    templates.py              -- Placeholder expansion for destination files
    drift.py                  -- state/git/plan drift detection
    subprocess_utils.py       -- Cross-platform subprocess (Windows kill-tree)
    quota_detector.py         -- Anthropic quota pattern detection (exit 11)
    dependency_check.py       -- 7-item pre-flight validator
    superpowers_dispatch.py   -- Invocation of Superpowers skills
    magi_dispatch.py          -- Invocation of /magi:magi + verdict parsing
    init_cmd.py               -- bootstrap destination project
    spec_cmd.py               -- spec pipeline with MAGI Checkpoint 2
    close_phase_cmd.py        -- three-step atomic phase close
    close_task_cmd.py         -- mark [x] + chore: commit + state advance
    status_cmd.py             -- structured read-only report
    pre_merge_cmd.py          -- Loop 1 + Loop 2 sequential gate
    finalize_cmd.py           -- sec.M.7 checklist + finishing-a-branch
    auto_cmd.py               -- shoot-and-forget full cycle
    resume_cmd.py             -- recovery from interrupted sessions
    reporters/
      __init__.py
      tdd_guard_schema.py     -- test.json schema for TDD-Guard integration
      rust_reporter.py        -- cargo nextest -> tdd-guard-rust pipeline
      ctest_reporter.py       -- ctest JUnit XML -> TDD-Guard JSON
templates/
  CLAUDE.local.md.template    -- Parameterized project rules
  plugin.local.md.template    -- Destination project configuration schema
  settings.json.template      -- Three TDD-Guard hooks for destination project
  spec-behavior-base.md.template -- SBTDD spec skeleton
  conftest.py.template        -- pytest reporter for destination project
  gitignore.fragment          -- Entries to append to destination .gitignore
tests/
  test_*.py                   -- One test module per scripts/ module
  fixtures/
    plans/
    state-files/
    plugin-locals/
    quota-errors/
    junit-xml/
    auto-run/
pyproject.toml                -- Python >= 3.9, dual license, mypy strict, ruff
conftest.py                   -- pytest hook for TDD-Guard test.json
Makefile                      -- verify, test, lint, format, typecheck targets
CHANGELOG.md                  -- Human-curated release notes (Keep a Changelog format)
CONTRIBUTING.md               -- Contributor guide
LICENSE                       -- MIT
LICENSE-APACHE                -- Apache-2.0
```

See the functional contract in `sbtdd/sbtdd-workflow-plugin-spec-base.md` for the authoritative architecture reference (sec.S.2).

---

## Running Tests

```bash
# All tests
python -m pytest tests/ -v

# Full verification (tests + lint + format + types)
make verify

# Individual checks
make test        # pytest
make lint        # ruff check
make format      # ruff format --check
make typecheck   # mypy --strict
```

---

## Requirements

| Component | Required | Notes |
|-----------|----------|-------|
| Python 3.9+ | Yes | stdlib-only on hot paths (close-phase, close-task, status) |
| `git` | Yes | All commit operations |
| `tdd-guard` binary | Yes | Real-time TDD phase enforcement in the destination project |
| `superpowers` plugin | Yes | 12 workflow skills (brainstorming, writing-plans, test-driven-development, ...) |
| `magi` plugin | Yes | Pre-merge Loop 2 + spec Checkpoint 2 |
| Per-stack toolchain | Yes (for chosen stack only) | `sbtdd init --stack <stack>` validates toolchain for the chosen stack only -- NOT for other stacks. **Rust:** `cargo`, `cargo-nextest`, `cargo-audit`, `tdd-guard-rust`. **Python:** `pytest`, `ruff`, `mypy`. **C++:** `cmake`, `ctest --output-junit`. |

`sbtdd init` runs a strict pre-flight that aggregates all missing dependencies into a single report before aborting -- no half-configured installs. The per-stack toolchain check is scoped to `--stack` (e.g., installing `sbtdd-workflow` for a Python project does NOT require Rust's `cargo-nextest`).

### Dev dependencies

```bash
pip install pytest pytest-asyncio ruff mypy pyyaml
```

Or via `uv`:

```bash
uv sync
```

---

## Publishing updates

1. Bump `"version"` in both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (must match, sec.S.3.3).
2. Update `CHANGELOG.md` (Keep a Changelog format: BREAKING / Added / Changed / Fixed / Deprecated / Removed).
3. Run `make verify` -- all tests must pass, zero lint warnings, clean formatting, no type errors.
4. Commit and push to `main` on GitHub.
5. Users pick up updates with `/plugin marketplace update`.

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the contributor guide: branching model, commit discipline, PR checklist, and the non-negotiable invariants.

In brief: SBTDD applies to its own development (dogfooding). Every contribution goes through `/sbtdd spec` -> plan approval -> task-by-task execution -> `/sbtdd pre-merge` -> `/sbtdd finalize`. No shortcuts.

---

## License

Dual licensed under [MIT](LICENSE) OR [Apache-2.0](LICENSE-APACHE), at your option. This dual-license convention is inherited from MAGI and from the Rust ecosystem.

---

## Credits

The SBTDD methodology and plugin architecture are designed and maintained by Julian Bolivar (BolivarTech). The plugin operationalizes the Superpowers skill ecosystem (Obra Inc.) and integrates with the MAGI multi-perspective plugin (also BolivarTech).

See `sbtdd/sbtdd-workflow-plugin-spec-base.md` for the authoritative functional contract (2860 lines covering sec.S.0-14: architecture, manifest, parameterization, 9 subcomandos, skill/hook specifications, conventions, state-file contract, invariants INV-0..30, exit code taxonomy, acceptance criteria).
