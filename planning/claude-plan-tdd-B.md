# Milestone B: Integration Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir la capa de integracion del plugin sbtdd-workflow — `dependency_check.py` (pre-flight validator de 7 deps), `run_sbtdd.py` (dispatcher scaffold con mapeo `SBTDDError` -> exit codes), `superpowers_dispatch.py` (wrapper typed de 12 skills superpowers), `magi_dispatch.py` (invocacion + parsing veredicto), 3 reporters TDD-Guard (`tdd_guard_schema`, `rust_reporter`, `ctest_reporter`), y 6 template files (`CLAUDE.local.md.template`, `plugin.local.md.template`, `settings.json.template`, `spec-behavior-base.md.template`, `conftest.py.template`, `gitignore.fragment`). Todo con `make verify` limpio. Subcomandos (`*_cmd.py`) se dejan para Milestone C+.

**Architecture:** Python 3.9+ consumiendo la infraestructura Milestone A (`errors.EXIT_CODES`, `errors.CommitError`, `models.VERDICT_RANK`, `models.VALID_SUBCOMMANDS`, `models.COMMIT_PREFIX_MAP`, `subprocess_utils.run_with_timeout`, `subprocess_utils.kill_tree`, `quota_detector.detect`, `drift.detect_drift`, `drift._evaluate_drift`, `commits.create`, `commits.validate_prefix`, `commits.validate_message`, `config.load_plugin_local`, `templates.expand`, `hooks_installer.merge`, `state_file.load/save`). Cada integracion module es una fachada tipada; la logica de negocio (subcomandos) consume estas fachadas en Milestone C. Frozen dataclasses para reportes de salida (`DependencyReport`, `MAGIVerdict`, `TestJSON`). Todo I/O externo enrutado via `subprocess_utils` para consistencia de timeouts + Windows kill-tree (NF5).

**Tech Stack:** Python 3.9+ stdlib + PyYAML 6 (ya presente en dev deps de Milestone A). No se agregan runtime deps nuevas.

---

## File Structure

Archivos creados en este milestone:

```
skills/sbtdd/scripts/
├── dependency_check.py               # check_environment() + DependencyReport + 7 checks
├── run_sbtdd.py                      # Entrypoint dispatcher (scaffold, no *_cmd aun)
├── superpowers_dispatch.py           # Typed wrappers for 12 superpowers skills + quota detect
├── magi_dispatch.py                  # /magi:magi invoke + MAGIVerdict + degraded + conditions
└── reporters/
    ├── tdd_guard_schema.py           # TestJSON dataclasses + writer
    ├── rust_reporter.py              # cargo nextest | tdd-guard-rust via Popen pipe
    └── ctest_reporter.py             # JUnit XML -> TestJSON via tdd_guard_schema

templates/
├── CLAUDE.local.md.template          # Parameterizable project rules
├── plugin.local.md.template          # YAML frontmatter schema
├── settings.json.template            # 3 TDD-Guard hooks (PreToolUse/UserPromptSubmit/SessionStart)
├── spec-behavior-base.md.template    # SBTDD spec skeleton (no uppercase markers)
├── conftest.py.template              # Python stack pytest hooks (with SBTDD delimiters)
└── gitignore.fragment                # Entries to append to destination .gitignore

tests/
├── test_dependency_check.py
├── test_run_sbtdd.py
├── test_superpowers_dispatch.py
├── test_magi_dispatch.py
├── test_reporters_schema.py
├── test_reporters_rust.py
├── test_reporters_ctest.py
└── test_templates_files.py           # Validation of the 6 template files

tests/fixtures/
├── magi-outputs/                     # Synthetic MAGI JSON verdicts (full, degraded, unknown, etc.)
├── ctest-junit/                      # Synthetic JUnit XML (passed, failed, mixed, empty)
└── conftest-merge/                   # conftest.py samples for merge/replace/skip modes
```

Tareas: 25 total (Tasks 1-24 + Task 4a inserted for the claude CLI check — see
"MAGI Checkpoint 2 iter 2 applied fixes" below). Orden lineal por dependencias:
Fase 1 (dependency_check + dispatcher scaffold) -> Fase 2 (dispatchers
superpowers/magi) -> Fase 3 (reporters) -> Fase 4 (templates). Cada tarea asume
las previas completas.

**Comandos de verificacion por fase TDD** (sec.M.0.1 + CLAUDE.local.md §0.1):

```bash
python -m pytest tests/ -v          # All pass, 0 fail
python -m ruff check .              # 0 warnings
python -m ruff format --check .     # Clean
python -m mypy .                    # No type errors
```

Atajo: `make verify` corre los 4 en orden.

**Supuestos post-Milestone A (consumidos, no re-implementados):**

- `errors.EXIT_CODES: Mapping[type[SBTDDError], int]` — mapping canonico sec.S.11.1.
- `errors.SBTDDError`, `ValidationError`, `StateFileError`, `DriftError`, `DependencyError`, `PreconditionError`, `MAGIGateError`, `QuotaExhaustedError`, `CommitError` — 9 subclases.
- `models.COMMIT_PREFIX_MAP`, `models.VERDICT_RANK`, `models.VALID_SUBCOMMANDS`, `models.verdict_meets_threshold`.
- `subprocess_utils.run_with_timeout(cmd, timeout, capture, cwd)` + `subprocess_utils.kill_tree(proc)`.
- `quota_detector.detect(stderr) -> QuotaExhaustion | None`.
- `drift.detect_drift`, `drift._evaluate_drift`, `drift.DriftReport`.
- `commits.create(prefix, message, cwd)`, `commits.validate_prefix`, `commits.validate_message`.
- `config.load_plugin_local(path) -> PluginConfig`.
- `templates.expand(template, context) -> str`.
- `hooks_installer.merge(existing_path, plugin_hooks, target_path)` + `hooks_installer.read_existing`.
- `state_file.load`, `state_file.save`, `state_file.SessionState`, `state_file.validate_schema`.
- `conftest.py` en root ya inyecta `skills/sbtdd/scripts/` en `sys.path`.

---

## Commit prefix policy

**Context (MAGI Checkpoint 2 iter 1 WARNING — balthasar):** all 25 tasks
(Tasks 1-24 + Task 4a) commit with the `test:` prefix rather than splitting each task into strict
`test:` (failing Red) + `feat:`/`fix:` (Green) pairs. This is deliberate and
consistent with the precedent set by Milestone A:

- **Milestone A precedent.** In `planning/claude-plan-tdd-A.md` the fresh-
  module scaffolding tasks (e.g., Tasks 2-7 covering `models.py`, `errors.py`,
  `state_file.py`, etc.) used single `test:` commits containing both the
  failing tests and the minimum implementation that makes them pass. That plan
  was approved by MAGI with 3-0 `GO` + full consensus and executed cleanly.
  Milestone B replicates the same pattern for consistency.
- **Rationale.** The SBTDD methodology (CLAUDE.local.md §5 + sec.M.5 row 1)
  classifies a commit that introduces a new test by its primary artefact. For
  fresh modules where (a) the test file and the implementation file are both
  brand-new, (b) the implementation is mechanical (dataclass fields, enum
  values, type-hint wrappers), and (c) there is no pre-existing bug to fix,
  the single-commit form is the canonical `test:` entry in the sec.M.5 table.
  Splitting would produce a transient intermediate state where the test
  references an unresolved import — increasing reviewer noise without adding
  signal.
- **When strict Red/Green split IS required.** If a task introduces new
  behavior into an already-existing module that downstream code depends on
  (i.e., not a fresh scaffolding), the canonical `test:` → `feat:`/`fix:`
  split MUST be used. In Milestone B this applies to: none of the 25 tasks
  (every module is born in this milestone; none has pre-existing consumers to
  regress against).
- **TDD discipline is preserved.** Each task still writes tests FIRST (Step 1),
  runs them FAILING (Step 2), then writes the minimum implementation (Step 3),
  and verifies PASS (Step 4). The only compression is that Steps 1-4 collapse
  into a single `test:` commit at Step 5 — the `/verification-before-completion`
  gate still applies before the commit lands.
- **Integrity check.** Every `test:` commit in this milestone must:
  1. Contain both new tests AND the new implementation file(s) the tests
     exercise.
  2. Leave `make verify` green on HEAD.
  3. Correspond to exactly one task in this plan (atomicity — no task
     bundling).
  4. Use an English message, no `Co-Authored-By`, no Claude/AI references
     (global `~/.claude/CLAUDE.md` §Git).

Future milestones that add behavior on top of these fresh modules (Milestones
C/D) will revert to the strict Red → Green split where applicable.

---

## Test isolation policy

**Context (MAGI Checkpoint 2 iter 1 WARNING — caspar):** tests that replace
module attributes (`shutil.which`, `subprocess.Popen`, `subprocess_utils.run_with_timeout`,
`superpowers_dispatch.invoke_skill`, etc.) MUST use `monkeypatch.setattr`
exclusively — never direct assignment. Pytest's `monkeypatch` fixture
auto-restores originals on test teardown, guaranteeing no cross-test
pollution. Direct `module.attr = fake` in a test body bypasses that
auto-restore and can make later tests in the same session behave non-
deterministically depending on collection order.

Rule of thumb for this milestone:

- Every `setattr` target in `tests/test_*.py` MUST be the `monkeypatch`
  fixture method form: `monkeypatch.setattr("pkg.mod.name", fake)` or
  `monkeypatch.setattr(obj, "attr", fake)`.
- Direct assignment (`superpowers_dispatch.invoke_skill = fake`) is
  forbidden outside `conftest.py` module-scoped fixtures that explicitly
  yield-and-restore.
- `monkeypatch.setitem` is the approved form for dict-like mutation of
  `SUBCOMMAND_DISPATCH` (used extensively in Task 7's tests); it auto-
  restores the item.

**Fix 5 (MAGI ckpt2 iter 2 WARNING — caspar).** The earlier iter-1 proposal
added a standalone meta-test file `tests/test_monkeypatch_isolation.py` that
relied on cross-test ordering (alphabetical pytest collection) to observe
monkeypatch teardown. Order is not guaranteed across platforms, so the
meta-test has been DROPPED. The isolation policy is now documented directly
as a convention at the top of the repo-root `conftest.py` (see the
docstring comment added below) and enforced by code review during Milestone
B's task-by-task close. No standalone meta-test file is added in this
milestone.

The enforcement text to add as a comment near the top of the repo-root
`conftest.py` (where `sys.path` is already manipulated, so the file is the
natural home for this policy statement):

```python
# Test isolation policy (MAGI Checkpoint 2 iter 2, caspar WARNING):
# tests MUST use ``monkeypatch.setattr(...)`` / ``monkeypatch.setitem(...)``
# to replace module attributes or dict items for the duration of a test.
# Direct assignment (``superpowers_dispatch.invoke_skill = fake``) is
# FORBIDDEN outside fixtures that explicitly yield-and-restore: it bypasses
# pytest's auto-restore and can make later tests in the same session behave
# non-deterministically depending on collection order. Every Task Step-1
# code block in Milestones B/C/D already conforms — reviewers reject diffs
# that break this rule.
```

This comment is added to `conftest.py` as part of Task 23's green step
(where `conftest.py.template` is landed in `templates/`; the repo-root
`conftest.py` receives the comment at the same commit — see Task 23 Step 3
addendum).

---

## Deferred from MAGI Checkpoint 2

Three INFO-level findings were explicitly deferred to Milestone C+ during
iter 1 of the MAGI review. They are tracked here to avoid losing visibility:

1. **INV-27 `<REPLACE:` regex enforcement (melchior INFO).** Task 22's
   spec-behavior-base template uses `<REPLACE: ...>` markers as intentional
   fill-in placeholders. `spec_cmd.py` in Milestone C must explicitly allow
   these (and reject the three forbidden uppercase pending markers — the
   specific words are enumerated in INV-27 of the spec; naming them here
   would itself violate INV-27 for this plan file). The regex, test
   fixtures, and acceptance test live in the `spec_cmd.py` task in
   Milestone C, not here.
2. **Task 18 tautological test (balthasar INFO).** Task 18 is a coverage-
   extension task on an already-green implementation. Its Step 1 test for
   `run` returning 0 is superficially tautological but still prevents silent
   regression if the return contract changes. Rewording to a more discriminating
   assertion is deferred; see the `WARNING — Task 18 TDD discipline` fix
   below for the partial remediation applied in this revision (the Step 1
   test is reclassified and the commit message is made explicit about
   "coverage extension, not red-green" to avoid confusion).
3. **Dispatch table `Protocol` type (caspar INFO).** Task 7 uses
   `Callable[[list[str]], int]` for the subcommand handler signature. A more
   expressive `typing.Protocol` with named methods (`run(argv: list[str]) -> int`)
   would let Milestone C+ `*_cmd.py` modules be referenced by their module
   object directly. Deferred to Milestone C when the first real handler is
   wired; conversion will be a single local refactor with no breaking change
   to the dispatch table.

---

## MAGI Checkpoint 2 iter 2 applied fixes

Iter-2 verdict: `GO_WITH_CAVEATS (3-0) full, non-degraded`. Caspar flagged
a CRITICAL architectural contradiction between CLAUDE.md and the `claude -p`
transport used by Tasks 8 / 10, plus four secondary warnings. Iter-3
confirms the resolution. The complete iter-2 delta applied to this plan:

- **Fix 1 (CRITICAL — CLAUDE.md reconciliation).** The CLAUDE.md
  "External Dependencies" paragraph that previously read "the plugin does
  not depend on `claude -p` for its own operation" has been rewritten in
  place (gitignored local file) to state: the orchestrator skill itself
  runs in-session, but cross-plugin sub-skill invocation from Python
  DOES use `claude -p` subprocess — aligned with MAGI v2.1.3. Tasks 8
  and 10 module docstrings simplified to cite CLAUDE.md directly and
  drop the earlier "reinterpretation" framing.
- **Fix 2 (WARNING — missing `claude` CLI dependency check).** New
  Task 4a adds `check_claude_cli()` (inserted between Task 4 and Task 5;
  downstream Tasks 5-24 keep stable numbering). Task 6's aggregator now
  includes the new check; plan total is 25 tasks.
- **Fix 3 (WARNING — E402 mid-file imports).** Tasks 3, 5, 12, 13 each
  have an explicit directive above the Step-3 code block instructing
  that the import lines shown inline MUST be lifted into the module's
  top-of-file import group (matching the Milestone A convention). The
  snippet placement is for readability only; final committed source
  must not leave imports mid-file.
- **Fix 4 (WARNING — rust_reporter pipeline cleanup).** Task 16's
  pipeline is restructured so the post-EOF `nextest.wait(...)` call
  shares the same `except TimeoutExpired` clause as the reporter
  `communicate(...)` call; the clause kills BOTH procs via
  `subprocess_utils.kill_tree` before re-raising, closing the prior
  orphan-on-nextest-timeout path. A new explicit test
  (`test_run_pipeline_nextest_wait_timeout_also_kills_both_procs`)
  covers that code path.
- **Fix 5 (WARNING — monkeypatch isolation meta-test fragile).** The
  proposed `tests/test_monkeypatch_isolation.py` meta-test relied on
  pytest's alphabetical collection order to observe monkeypatch
  teardown across two adjacent tests — not portable. The meta-test is
  DROPPED; the isolation convention is documented as a comment at the
  top of the repo-root `conftest.py` (added as an addendum to Task 23's
  commit). Reviewers enforce at code-review time.
- **Fix 6 (WARNING — untrackable manual smoke test).** The iter-1
  "manual smoke test" acceptance bullet is REPLACED by a new test file
  `tests/test_superpowers_dispatch_integration.py` that runs a cheap
  `claude --version` invocation guarded by
  `@pytest.mark.skipif(shutil.which("claude") is None, ...)`. The test
  is committed as part of Task 9 (same atomic unit). Environments
  without the CLI show SKIP (not FAIL); environments with the CLI
  prove transport end-to-end.
- **Fix 7 (INFO acknowledgement — commit prefix policy).** The existing
  "Commit prefix policy" section already addresses melchior's iter-1
  note; no further action in iter-2.
- **Fix 8 (WARNING — magic-number slack in pipeline).** Task 16 now
  exposes `_NEXTEST_EXIT_SLACK_SECONDS: int = 5` as a named module
  constant with a short comment explaining its purpose; a test asserts
  the constant's value so it cannot silently drift.

The iter-2 INFO items (Task 18 coverage framing, git-log navigability of
`test:`-only commits, INV-27 self-reference) remain deferred; none
blocks iter-3 approval.

---

## Phase 1: Pre-flight + dispatcher scaffold (Tasks 1-7 + Task 4a — foundation for all subsequent subcommands)

### Task 1: `dependency_check.py` — `DependencyCheck` dataclass + `CheckStatus` enum-like

**Files:**
- Create: `skills/sbtdd/scripts/dependency_check.py`
- Create: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError


def test_dependency_check_is_frozen_dataclass():
    from dependency_check import DependencyCheck
    chk = DependencyCheck(
        name="git",
        status="OK",
        detail="git version 2.43.0",
        remediation=None,
    )
    with pytest.raises(FrozenInstanceError):
        chk.status = "MISSING"  # type: ignore[misc]


def test_dependency_check_requires_four_fields():
    from dependency_check import DependencyCheck
    fields = set(DependencyCheck.__dataclass_fields__)
    assert fields == {"name", "status", "detail", "remediation"}


def test_check_status_values_restricted():
    from dependency_check import VALID_STATUSES
    assert VALID_STATUSES == ("OK", "MISSING", "BROKEN")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'dependency_check'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/dependency_check.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Pre-flight dependency validator for /sbtdd init (sec.S.1.3, sec.S.5.1.1).

Seven mandatory checks: Python >= 3.9, git, tdd-guard (+ writable data dir),
superpowers plugin discovery, magi plugin discovery, stack toolchain
(Rust/Python/C++), git working tree. Failures accumulate; check_environment
never short-circuits. Caller (init, status) decides abort vs report-only.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Allowed values for DependencyCheck.status (sec.S.5.1.1 reporte formato).
VALID_STATUSES: tuple[str, ...] = ("OK", "MISSING", "BROKEN")


@dataclass(frozen=True)
class DependencyCheck:
    """Result of a single dependency check (sec.S.5.1.1 reporte estructurado)."""

    name: str
    status: str  # one of VALID_STATUSES
    detail: str
    remediation: str | None
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 3 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add DependencyCheck frozen dataclass with status enum"
```

---

### Task 2: `dependency_check.py` — `DependencyReport` + `failed()` + `format_report()`

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_dependency_report_aggregates_checks():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("python", "OK", "3.12.0", None),
        DependencyCheck("tdd-guard", "MISSING", "not in PATH",
                        "npm install -g @nizos/tdd-guard"),
    ))
    assert len(rep.checks) == 2


def test_dependency_report_failed_returns_only_non_ok():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("python", "OK", "3.12.0", None),
        DependencyCheck("git", "MISSING", "not found", "install git"),
        DependencyCheck("magi", "BROKEN", "wrong version", "update"),
    ))
    failed = rep.failed()
    assert len(failed) == 2
    assert {c.name for c in failed} == {"git", "magi"}


def test_dependency_report_ok_returns_true_when_all_ok():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("python", "OK", "3.12", None),
        DependencyCheck("git", "OK", "2.43", None),
    ))
    assert rep.ok() is True


def test_dependency_report_ok_returns_false_when_any_non_ok():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("python", "OK", "3.12", None),
        DependencyCheck("git", "MISSING", "", "install git"),
    ))
    assert rep.ok() is False


def test_format_report_includes_all_failures_and_count():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("tdd-guard", "MISSING", "Binary not found in PATH.",
                        "npm install -g @nizos/tdd-guard"),
        DependencyCheck("magi", "MISSING",
                        "Plugin not discoverable under ~/.claude/plugins/.",
                        "/plugin marketplace add BolivarTech/magi"),
    ))
    out = rep.format_report()
    assert "tdd-guard" in out
    assert "magi" in out
    assert "[MISSING]" in out
    assert "2 issues found" in out
    assert "No files were created" in out


def test_format_report_empty_when_all_ok():
    from dependency_check import DependencyCheck, DependencyReport
    rep = DependencyReport(checks=(
        DependencyCheck("python", "OK", "3.12", None),
    ))
    assert rep.format_report() == ""
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'DependencyReport'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py`:

```python
@dataclass(frozen=True)
class DependencyReport:
    """Aggregated result of check_environment (sec.S.5.1.1)."""

    checks: tuple[DependencyCheck, ...]

    def failed(self) -> tuple[DependencyCheck, ...]:
        """Return only the checks whose status is not OK."""
        return tuple(c for c in self.checks if c.status != "OK")

    def ok(self) -> bool:
        """Return True iff every check has status OK."""
        return all(c.status == "OK" for c in self.checks)

    def format_report(self) -> str:
        """Format failures as the canonical sec.S.5.1.1 report, or empty string.

        Returns:
            Multi-line human-readable report when any check failed; the empty
            string when every check is OK (caller should not print anything).
        """
        failures = self.failed()
        if not failures:
            return ""
        lines = [
            "SBTDD init: environment check FAILED.",
            "",
            "The following dependencies are missing or not operational. Install all of",
            "them and re-run /sbtdd init:",
            "",
        ]
        for chk in failures:
            lines.append(f"  [{chk.status}]  {chk.name}")
            if chk.detail:
                lines.append(f"             {chk.detail}")
            if chk.remediation:
                lines.append(f"             Install: {chk.remediation}")
            lines.append("")
        lines.append(f"{len(failures)} issues found. /sbtdd init aborted. Exit code 2.")
        lines.append("No files were created in the project.")
        return "\n".join(lines)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 9 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add DependencyReport aggregator with failed/ok/format_report"
```

---

### Task 3: `dependency_check.py` — individual check functions (Python, git, tdd-guard)

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_check_python_passes_on_current_interpreter():
    from dependency_check import check_python
    chk = check_python()
    assert chk.name == "python"
    assert chk.status == "OK"
    assert "3." in chk.detail


def test_check_git_returns_missing_when_not_in_path(monkeypatch):
    from dependency_check import check_git
    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_git()
    assert chk.status == "MISSING"
    assert chk.remediation is not None


def test_check_git_returns_ok_when_present(monkeypatch):
    from dependency_check import check_git
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/git")

    class FakeProc:
        returncode = 0
        stdout = "git version 2.43.0\n"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_git()
    assert chk.status == "OK"
    assert "2.43" in chk.detail


def test_check_tdd_guard_binary_missing(monkeypatch):
    from dependency_check import check_tdd_guard_binary
    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_tdd_guard_binary()
    assert chk.status == "MISSING"
    assert "npm install -g" in (chk.remediation or "")


def test_check_tdd_guard_data_dir_writable(tmp_path):
    from dependency_check import check_tdd_guard_data_dir
    chk = check_tdd_guard_data_dir(project_root=tmp_path)
    assert chk.status == "OK"
    assert (tmp_path / ".claude" / "tdd-guard" / "data").exists()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'check_python'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py`. The five `import`
lines below MUST be lifted to the top-of-file import group next to
`from __future__ import annotations` and `from dataclasses import dataclass`
from Task 1 — they appear at the start of the snippet here purely for
readability. Leaving them mid-file would trigger Ruff `E402` on green.
(Fix 3 / MAGI ckpt2 iter 2 caspar WARNING; consolidated per Milestone A
convention.)

```python
# Consolidated to top of file per E402 / Milestone A convention.
import shutil
import subprocess
import sys
from pathlib import Path

import subprocess_utils


def check_python() -> DependencyCheck:
    """Verify Python >= 3.9 (sec.S.1.3 item 1)."""
    v = sys.version_info
    if v >= (3, 9):
        return DependencyCheck(
            name="python",
            status="OK",
            detail=f"Python {v.major}.{v.minor}.{v.micro}",
            remediation=None,
        )
    return DependencyCheck(
        name="python",
        status="BROKEN",
        detail=f"Python {v.major}.{v.minor}.{v.micro} < 3.9 required",
        remediation="Install Python 3.9+ from python.org",
    )


def check_git() -> DependencyCheck:
    """Verify git binary is in PATH and responds (sec.S.1.3 item 2)."""
    if shutil.which("git") is None:
        return DependencyCheck(
            name="git",
            status="MISSING",
            detail="Binary not found in PATH.",
            remediation="https://git-scm.com/downloads",
        )
    try:
        result = subprocess_utils.run_with_timeout(
            ["git", "--version"], timeout=5
        )
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="git",
            status="BROKEN",
            detail="git --version timed out after 5s",
            remediation="Check PATH / reinstall git",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="git",
            status="BROKEN",
            detail=f"git --version returncode={result.returncode}",
            remediation="Reinstall git",
        )
    return DependencyCheck(
        name="git",
        status="OK",
        detail=result.stdout.strip(),
        remediation=None,
    )


def check_tdd_guard_binary() -> DependencyCheck:
    """Verify tdd-guard binary is in PATH and responds (sec.S.1.3 item 3)."""
    if shutil.which("tdd-guard") is None:
        return DependencyCheck(
            name="tdd-guard",
            status="MISSING",
            detail="Binary not found in PATH.",
            remediation="npm install -g @nizos/tdd-guard",
        )
    try:
        result = subprocess_utils.run_with_timeout(
            ["tdd-guard", "--version"], timeout=5
        )
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="tdd-guard",
            status="BROKEN",
            detail="tdd-guard --version timed out after 5s",
            remediation="Reinstall tdd-guard",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="tdd-guard",
            status="BROKEN",
            detail=f"tdd-guard --version returncode={result.returncode}",
            remediation="npm install -g @nizos/tdd-guard",
        )
    return DependencyCheck(
        name="tdd-guard",
        status="OK",
        detail=result.stdout.strip() or "tdd-guard present",
        remediation=None,
    )


def check_tdd_guard_data_dir(project_root: Path) -> DependencyCheck:
    """Verify .claude/tdd-guard/data/ is creatable and writable (sec.S.1.3 item 3)."""
    data_dir = project_root / ".claude" / "tdd-guard" / "data"
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        probe = data_dir / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return DependencyCheck(
            name="tdd-guard data directory",
            status="BROKEN",
            detail=f"{data_dir} not writable: {exc}",
            remediation="Check filesystem permissions on the project directory.",
        )
    return DependencyCheck(
        name="tdd-guard data directory",
        status="OK",
        detail=f"{data_dir} writable",
        remediation=None,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 14 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add python/git/tdd-guard individual dependency checks"
```

---

### Task 4: `dependency_check.py` — plugin discovery checks (superpowers, magi)

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_check_superpowers_missing_when_no_skills(tmp_path):
    from dependency_check import check_superpowers
    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "MISSING"
    assert "superpowers" in chk.detail.lower() or "plugin" in chk.detail.lower()


def test_check_superpowers_ok_with_all_twelve_skills(tmp_path):
    from dependency_check import check_superpowers, SUPERPOWERS_SKILLS
    base = tmp_path / "cache" / "superpowers" / "skills"
    for skill in SUPERPOWERS_SKILLS:
        (base / skill).mkdir(parents=True)
        (base / skill / "SKILL.md").write_text("# " + skill, encoding="utf-8")
    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "OK"


def test_check_superpowers_broken_when_partial(tmp_path):
    from dependency_check import check_superpowers, SUPERPOWERS_SKILLS
    base = tmp_path / "cache" / "superpowers" / "skills"
    # Install only the first 5 of 12 skills.
    for skill in SUPERPOWERS_SKILLS[:5]:
        (base / skill).mkdir(parents=True)
        (base / skill / "SKILL.md").write_text("# " + skill, encoding="utf-8")
    chk = check_superpowers(plugins_root=tmp_path)
    assert chk.status == "BROKEN"
    # Ensure the detail lists at least one missing skill.
    assert any(name in chk.detail for name in SUPERPOWERS_SKILLS[5:])


def test_check_magi_missing_when_no_scripts(tmp_path):
    from dependency_check import check_magi
    chk = check_magi(plugins_root=tmp_path)
    assert chk.status == "MISSING"


def test_check_magi_ok_with_skill_and_script(tmp_path):
    from dependency_check import check_magi
    base = tmp_path / "cache" / "magi" / "skills" / "magi"
    base.mkdir(parents=True)
    (base / "SKILL.md").write_text("# magi", encoding="utf-8")
    (base / "scripts").mkdir()
    (base / "scripts" / "run_magi.py").write_text("# run", encoding="utf-8")
    chk = check_magi(plugins_root=tmp_path)
    assert chk.status == "OK"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'check_superpowers'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py`:

```python
#: 12 superpowers skills required by sec.S.1.3 item 4.
SUPERPOWERS_SKILLS: tuple[str, ...] = (
    "brainstorming",
    "writing-plans",
    "test-driven-development",
    "verification-before-completion",
    "requesting-code-review",
    "receiving-code-review",
    "executing-plans",
    "subagent-driven-development",
    "dispatching-parallel-agents",
    "systematic-debugging",
    "using-git-worktrees",
    "finishing-a-development-branch",
)


def _find_skill_md(plugins_root: Path, plugin_name: str, skill_name: str) -> Path | None:
    """Return the first ``SKILL.md`` under ``plugins_root/**/{plugin}/**/skills/{skill}/``."""
    if not plugins_root.exists():
        return None
    for candidate in plugins_root.rglob(f"{plugin_name}/**/skills/{skill_name}/SKILL.md"):
        return candidate
    return None


def check_superpowers(plugins_root: Path) -> DependencyCheck:
    """Verify all 12 superpowers skills are discoverable (sec.S.1.3 item 4)."""
    missing: list[str] = []
    for skill in SUPERPOWERS_SKILLS:
        if _find_skill_md(plugins_root, "superpowers", skill) is None:
            missing.append(skill)
    if len(missing) == len(SUPERPOWERS_SKILLS):
        return DependencyCheck(
            name="superpowers plugin",
            status="MISSING",
            detail=f"Plugin not discoverable under {plugins_root}.",
            remediation="/plugin marketplace add obra/superpowers && /plugin install",
        )
    if missing:
        return DependencyCheck(
            name="superpowers plugin",
            status="BROKEN",
            detail=f"missing skills: {', '.join(missing)}",
            remediation="Reinstall superpowers via /plugin install",
        )
    return DependencyCheck(
        name="superpowers plugin",
        status="OK",
        detail=f"{len(SUPERPOWERS_SKILLS)} skills found",
        remediation=None,
    )


def check_magi(plugins_root: Path) -> DependencyCheck:
    """Verify the magi plugin is discoverable (sec.S.1.3 item 5)."""
    skill_md = _find_skill_md(plugins_root, "magi", "magi")
    if skill_md is None:
        return DependencyCheck(
            name="magi plugin",
            status="MISSING",
            detail=f"Plugin not discoverable under {plugins_root}.",
            remediation="/plugin marketplace add BolivarTech/magi",
        )
    run_magi = skill_md.parent / "scripts" / "run_magi.py"
    if not run_magi.exists():
        return DependencyCheck(
            name="magi plugin",
            status="BROKEN",
            detail=f"run_magi.py missing at {run_magi}",
            remediation="Reinstall magi via /plugin install",
        )
    return DependencyCheck(
        name="magi plugin",
        status="OK",
        detail=f"found at {skill_md.parent}",
        remediation=None,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 19 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add superpowers and magi plugin discovery checks"
```

---

### Task 4a: `dependency_check.py` — `claude` CLI check (Fix 2 / WARNING — caspar)

**Context (MAGI Checkpoint 2 iter 2 WARNING — caspar):** `superpowers_dispatch.invoke_skill`
and `magi_dispatch.invoke_magi` both shell out to the `claude` CLI via
subprocess `claude -p`. If the binary is missing at runtime, the dispatchers
raise `ValidationError` only at first invocation (mid-spec or mid-pre-merge)
— too late for the all-or-nothing `init` contract. The pre-flight validator
must reject a missing `claude` binary upfront alongside the other 7
dependencies.

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_check_claude_cli_missing_when_not_in_path(monkeypatch):
    from dependency_check import check_claude_cli
    monkeypatch.setattr("shutil.which", lambda name: None)
    chk = check_claude_cli()
    assert chk.status == "MISSING"
    assert chk.name == "claude CLI"
    assert chk.remediation is not None


def test_check_claude_cli_ok_when_present(monkeypatch):
    from dependency_check import check_claude_cli
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    class FakeProc:
        returncode = 0
        stdout = "claude-code 1.0.30\n"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_claude_cli()
    assert chk.status == "OK"
    assert "claude-code" in chk.detail or "1.0" in chk.detail


def test_check_claude_cli_broken_on_nonzero_returncode(monkeypatch):
    from dependency_check import check_claude_cli
    monkeypatch.setattr(
        "shutil.which",
        lambda name: "/usr/bin/claude" if name == "claude" else None,
    )

    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "error"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    chk = check_claude_cli()
    assert chk.status == "BROKEN"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'check_claude_cli'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py` (imports already at top
from Task 3 — `shutil`, `subprocess`, `subprocess_utils` are reused):

```python
def check_claude_cli() -> DependencyCheck:
    """Verify the ``claude`` CLI is in PATH (required by superpowers/magi dispatchers).

    Both :mod:`superpowers_dispatch` and :mod:`magi_dispatch` shell out via
    ``claude -p``; without the binary the workflow cannot invoke sub-skills.
    Surfaced during pre-flight so ``init`` fails fast before any file is
    created (sec.S.1.3 companion check; MAGI Checkpoint 2 iter 2 caspar fix).
    """
    if shutil.which("claude") is None:
        return DependencyCheck(
            name="claude CLI",
            status="MISSING",
            detail="Binary 'claude' not found in PATH.",
            remediation="Install Claude Code from https://claude.com/claude-code",
        )
    try:
        result = subprocess_utils.run_with_timeout(
            ["claude", "--version"], timeout=5
        )
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name="claude CLI",
            status="BROKEN",
            detail="claude --version timed out after 5s",
            remediation="Reinstall Claude Code",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name="claude CLI",
            status="BROKEN",
            detail=f"claude --version returncode={result.returncode}",
            remediation="Reinstall Claude Code",
        )
    detail = (result.stdout or result.stderr).strip().splitlines()[0] if (
        (result.stdout or result.stderr).strip()
    ) else "claude present"
    return DependencyCheck(
        name="claude CLI",
        status="OK",
        detail=detail,
        remediation=None,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 22 tests (19 after Task 4 + 3 new).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add claude CLI dependency check for cross-plugin dispatchers"
```

---

### Task 5: `dependency_check.py` — stack toolchain checks + working tree

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_check_working_tree_ok_with_git_dir(tmp_path):
    from dependency_check import check_working_tree
    (tmp_path / ".git").mkdir()
    chk = check_working_tree(project_root=tmp_path)
    assert chk.status == "OK"


def test_check_working_tree_missing_without_git(tmp_path):
    from dependency_check import check_working_tree
    chk = check_working_tree(project_root=tmp_path)
    assert chk.status == "MISSING"
    assert "git init" in (chk.remediation or "")


def test_check_stack_toolchain_python_ok(monkeypatch):
    from dependency_check import check_stack_toolchain
    monkeypatch.setattr("shutil.which", lambda name: f"/usr/bin/{name}")

    class FakeProc:
        returncode = 0
        stdout = "version 1.0.0"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    checks = check_stack_toolchain("python")
    assert all(c.status == "OK" for c in checks), [c.name for c in checks if c.status != "OK"]
    names = {c.name for c in checks}
    assert names == {"python (pytest)", "python (ruff)", "python (mypy)"}


def test_check_stack_toolchain_rust_missing_tdd_guard_rust(monkeypatch):
    from dependency_check import check_stack_toolchain

    def fake_which(name: str) -> str | None:
        return None if name == "tdd-guard-rust" else f"/usr/bin/{name}"

    monkeypatch.setattr("shutil.which", fake_which)

    class FakeProc:
        returncode = 0
        stdout = "v1"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    checks = check_stack_toolchain("rust")
    # tdd-guard-rust missing -> BROKEN (blocks reporter); other cargo tools OK.
    broken = [c for c in checks if c.status == "MISSING"]
    assert len(broken) == 1
    assert broken[0].name.endswith("tdd-guard-rust")


def test_check_stack_toolchain_rejects_unknown_stack():
    from dependency_check import check_stack_toolchain
    from errors import ValidationError
    with pytest.raises(ValidationError):
        check_stack_toolchain("haskell")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'check_working_tree'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py`. The `from errors import
ValidationError` line MUST be lifted to the top-of-file import group (next
to the imports consolidated in Task 3); it appears at the start of the
snippet here purely for readability. (Fix 3 / MAGI ckpt2 iter 2 caspar
WARNING; consolidated per Milestone A convention.)

```python
# Consolidated to top of file per E402 / Milestone A convention.
from errors import ValidationError

#: Per-stack toolchain binaries (sec.S.1.3 item 6). Keyed by stack; values are
#: (binary_name, display_name) tuples. The reporter entry for Rust is separate
#: because it is mandatory and has a distinct remediation URL.
_STACK_TOOLCHAINS: dict[str, tuple[tuple[str, str], ...]] = {
    "rust": (
        ("cargo", "rust (cargo)"),
        ("cargo-nextest", "rust (cargo-nextest)"),
        ("cargo-audit", "rust (cargo-audit)"),
        ("cargo-clippy", "rust (cargo-clippy)"),
        ("cargo-fmt", "rust (cargo-fmt)"),
        ("tdd-guard-rust", "rust (tdd-guard-rust)"),
    ),
    "python": (
        ("pytest", "python (pytest)"),
        ("ruff", "python (ruff)"),
        ("mypy", "python (mypy)"),
    ),
    "cpp": (
        ("cmake", "cpp (cmake)"),
        ("ctest", "cpp (ctest)"),
    ),
}


def _check_binary(binary: str, display: str) -> DependencyCheck:
    """Check that ``binary`` is in PATH and ``{binary} --version`` exits 0."""
    if shutil.which(binary) is None:
        return DependencyCheck(
            name=display,
            status="MISSING",
            detail=f"{binary} not found in PATH.",
            remediation=f"Install {binary} for your OS",
        )
    try:
        result = subprocess_utils.run_with_timeout(
            [binary, "--version"], timeout=5
        )
    except subprocess.TimeoutExpired:
        return DependencyCheck(
            name=display,
            status="BROKEN",
            detail=f"{binary} --version timed out",
            remediation=f"Reinstall {binary}",
        )
    if result.returncode != 0:
        return DependencyCheck(
            name=display,
            status="BROKEN",
            detail=f"{binary} --version returncode={result.returncode}",
            remediation=f"Reinstall {binary}",
        )
    return DependencyCheck(
        name=display,
        status="OK",
        detail=(result.stdout or result.stderr).strip().splitlines()[0]
        if (result.stdout or result.stderr).strip()
        else f"{binary} present",
        remediation=None,
    )


def check_stack_toolchain(stack: str) -> tuple[DependencyCheck, ...]:
    """Run all toolchain checks for the chosen stack (sec.S.1.3 item 6).

    Args:
        stack: One of ``rust``, ``python``, ``cpp``.

    Returns:
        Tuple of ``DependencyCheck`` for each required binary. The caller
        aggregates them into the overall :class:`DependencyReport`.

    Raises:
        ValidationError: If ``stack`` is not one of the three supported values.
    """
    if stack not in _STACK_TOOLCHAINS:
        raise ValidationError(
            f"stack='{stack}' not in {sorted(_STACK_TOOLCHAINS)}"
        )
    return tuple(_check_binary(b, d) for b, d in _STACK_TOOLCHAINS[stack])


def check_working_tree(project_root: Path) -> DependencyCheck:
    """Verify .git/ exists (sec.S.1.3 item 7). init does NOT run ``git init``."""
    if (project_root / ".git").exists():
        return DependencyCheck(
            name="git working tree",
            status="OK",
            detail=f".git/ present at {project_root}",
            remediation=None,
        )
    return DependencyCheck(
        name="git working tree",
        status="MISSING",
        detail=f".git/ not found at {project_root}",
        remediation="Run 'git init' in the project directory before re-running /sbtdd init",
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 27 tests (24 after Task 5 impl + 3 from Task 4a claude CLI).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add stack toolchain and working tree dependency checks"
```

---

### Task 6: `dependency_check.py` — `check_environment()` aggregator (no short-circuit)

**Files:**
- Modify: `skills/sbtdd/scripts/dependency_check.py`
- Modify: `tests/test_dependency_check.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_dependency_check.py (append)
def test_check_environment_aggregates_all_eight_items(tmp_path, monkeypatch):
    """All eight fixed checks must run even if earlier ones fail (no short-circuit).

    Eight = 7 sec.S.1.3 mandatory deps + claude CLI (Task 4a / MAGI ckpt2 iter 2
    caspar WARNING). The term "7 deps" in CLAUDE.md External Dependencies remains
    accurate for the sec.S.1.3 contract; claude CLI is a companion check surfaced
    during pre-flight.
    """
    from dependency_check import check_environment, SUPERPOWERS_SKILLS
    # Ensure git present (so git check passes); force tdd-guard missing.

    def fake_which(name: str) -> str | None:
        return None if name == "tdd-guard" else f"/usr/bin/{name}"

    monkeypatch.setattr("shutil.which", fake_which)

    class FakeProc:
        returncode = 0
        stdout = "v1"
        stderr = ""

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    # Plugins root empty -> superpowers + magi MISSING; but check_environment
    # still continues through all items.
    plugins_root = tmp_path / "plugins"
    plugins_root.mkdir()
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / ".git").mkdir()

    rep = check_environment(
        stack="python",
        project_root=project_root,
        plugins_root=plugins_root,
    )
    # Names collected confirm every stage ran.
    names = {c.name for c in rep.checks}
    # Non-toolchain names
    assert "python" in names
    assert "git" in names
    assert "tdd-guard" in names
    assert "tdd-guard data directory" in names
    assert "claude CLI" in names
    assert "superpowers plugin" in names
    assert "magi plugin" in names
    assert "git working tree" in names
    # Toolchain names (3 for python stack)
    assert "python (pytest)" in names
    assert "python (ruff)" in names
    assert "python (mypy)" in names


def test_check_environment_returns_dependency_report(tmp_path, monkeypatch):
    from dependency_check import check_environment, DependencyReport
    monkeypatch.setattr("shutil.which", lambda name: None)
    rep = check_environment(
        stack="python",
        project_root=tmp_path,
        plugins_root=tmp_path,
    )
    assert isinstance(rep, DependencyReport)
    assert rep.ok() is False


def test_check_environment_never_raises_on_failing_checks(tmp_path, monkeypatch):
    """Even when every single check fails, check_environment returns a report."""
    from dependency_check import check_environment
    monkeypatch.setattr("shutil.which", lambda name: None)
    rep = check_environment(
        stack="rust",
        project_root=tmp_path,
        plugins_root=tmp_path,
    )
    # 8 fixed checks (7 sec.S.1.3 deps + claude CLI from Task 4a) + 6 rust
    # toolchain checks = 14 total; all failing.
    assert len(rep.checks) >= 14
    assert rep.ok() is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: FAIL con `ImportError: cannot import name 'check_environment'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/dependency_check.py`:

```python
def check_environment(
    stack: str,
    project_root: Path,
    plugins_root: Path,
) -> DependencyReport:
    """Run all pre-flight checks aggregating failures (sec.S.5.1.1).

    Eight fixed checks (7 sec.S.1.3 mandatory deps + ``claude CLI`` companion
    from Task 4a) plus per-stack toolchain checks. Order matters only for the
    reader; no check short-circuits the next. Every exception from an
    individual check is contained — any uncaught issue becomes a BROKEN entry
    so the caller sees the complete picture.

    Args:
        stack: One of ``rust``, ``python``, ``cpp``.
        project_root: Destination project directory (for .git/ check and
            tdd-guard data dir).
        plugins_root: Root under which Claude Code plugins are cached
            (typically ``~/.claude/plugins``).

    Returns:
        DependencyReport whose ``.checks`` tuple contains every check.

    Raises:
        ValidationError: If ``stack`` is not one of the three supported values
            (raised by :func:`check_stack_toolchain`, surfaces immediately —
            this is a caller programming error, not an environment issue).
    """
    checks: list[DependencyCheck] = []
    checks.append(check_python())
    checks.append(check_git())
    checks.append(check_tdd_guard_binary())
    checks.append(check_tdd_guard_data_dir(project_root))
    checks.append(check_claude_cli())
    checks.append(check_superpowers(plugins_root))
    checks.append(check_magi(plugins_root))
    # check_stack_toolchain raises on unknown stack — propagate; this is a
    # programming error, not an environment issue.
    checks.extend(check_stack_toolchain(stack))
    checks.append(check_working_tree(project_root))
    return DependencyReport(checks=tuple(checks))
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_dependency_check.py -v`
Expected: PASS — 30 tests (27 after Task 5 + 3 check_environment-specific).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/dependency_check.py tests/test_dependency_check.py
git commit -m "test: add check_environment aggregator for all preflight items"
```

---

### Task 7: `run_sbtdd.py` — dispatcher scaffold + exit code mapping

**Files:**
- Create: `skills/sbtdd/scripts/run_sbtdd.py`
- Create: `tests/test_run_sbtdd.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_run_sbtdd.py
from __future__ import annotations

import pytest


def test_main_rejects_unknown_subcommand(capsys):
    from run_sbtdd import main
    code = main(["unknown-sub"])
    assert code == 1
    out = capsys.readouterr()
    assert "unknown" in (out.err + out.out).lower() or "invalid" in (out.err + out.out).lower()


def test_main_rejects_empty_argv(capsys):
    from run_sbtdd import main
    code = main([])
    assert code == 1


def test_main_accepts_all_nine_valid_subcommands(monkeypatch):
    """Dispatch succeeds (returns 0) for each name in VALID_SUBCOMMANDS when stub is installed."""
    from models import VALID_SUBCOMMANDS
    import run_sbtdd

    for sub in VALID_SUBCOMMANDS:
        monkeypatch.setitem(run_sbtdd.SUBCOMMAND_DISPATCH, sub, lambda argv: 0)
        assert run_sbtdd.main([sub]) == 0


def test_main_maps_validation_error_to_exit_1(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import ValidationError

    def raising(argv):
        raise ValidationError("bad input")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "init", raising)
    assert main(["init"]) == 1


def test_main_maps_dependency_error_to_exit_2(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import DependencyError

    def raising(argv):
        raise DependencyError("missing")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "init", raising)
    assert main(["init"]) == 2


def test_main_maps_drift_error_to_exit_3(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import DriftError

    def raising(argv):
        raise DriftError("drift")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "status", raising)
    assert main(["status"]) == 3


def test_main_maps_magi_gate_error_to_exit_8(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import MAGIGateError

    def raising(argv):
        raise MAGIGateError("STRONG_NO_GO")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "pre-merge", raising)
    assert main(["pre-merge"]) == 8


def test_main_maps_quota_exhausted_error_to_exit_11(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import QuotaExhaustedError

    def raising(argv):
        raise QuotaExhaustedError("rate limit")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "spec", raising)
    assert main(["spec"]) == 11


def test_main_maps_keyboard_interrupt_to_exit_130(monkeypatch):
    from run_sbtdd import main, SUBCOMMAND_DISPATCH

    def raising(argv):
        raise KeyboardInterrupt()

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "auto", raising)
    assert main(["auto"]) == 130


def test_main_maps_unknown_sbtdd_error_to_exit_1(monkeypatch):
    """Unknown SBTDDError subclass (not in EXIT_CODES) falls back to exit 1."""
    from run_sbtdd import main, SUBCOMMAND_DISPATCH
    from errors import SBTDDError

    class UnmappedError(SBTDDError):
        pass

    def raising(argv):
        raise UnmappedError("unknown")

    monkeypatch.setitem(SUBCOMMAND_DISPATCH, "status", raising)
    assert main(["status"]) == 1


def test_dispatch_table_has_all_nine_subcommands():
    from run_sbtdd import SUBCOMMAND_DISPATCH
    from models import VALID_SUBCOMMANDS
    assert set(SUBCOMMAND_DISPATCH.keys()) == set(VALID_SUBCOMMANDS)


def test_all_default_handlers_raise_not_implemented_validation_error():
    """Default handlers raise ValidationError pending Milestone C+ implementation."""
    from run_sbtdd import _default_handler_factory
    from errors import ValidationError
    handler = _default_handler_factory("init")
    with pytest.raises(ValidationError, match="not yet implemented"):
        handler([])
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_run_sbtdd.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'run_sbtdd'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/run_sbtdd.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""sbtdd-workflow single entrypoint (sec.S.2.3, sec.S.5, sec.S.11.1-11.2).

Invoked as ``python run_sbtdd.py <subcommand> [args...]`` from the skill.
Validates the subcommand name against :data:`models.VALID_SUBCOMMANDS`,
then dispatches to the matching ``{subcommand}_cmd.run`` function.

Exit codes are derived from :data:`errors.EXIT_CODES` — unknown
:class:`errors.SBTDDError` subclasses fall through to exit 1. ``KeyboardInterrupt``
becomes exit 130 (sec.S.11.3). All other uncaught exceptions surface with
traceback and exit 1 (bug report channel per sec.S.11.2).

In Milestone B the dispatch table is wired with placeholder handlers that
raise :class:`errors.ValidationError` for unimplemented subcommands. Milestone C+
replaces each entry with the real ``{subcommand}_cmd.run``.
"""

from __future__ import annotations

import sys
from typing import Callable, MutableMapping

from errors import EXIT_CODES, SBTDDError, ValidationError
from models import VALID_SUBCOMMANDS

#: Handler signature: consumes the subcommand's argv tail and returns an exit code.
SubcommandHandler = Callable[[list[str]], int]


def _default_handler_factory(name: str) -> SubcommandHandler:
    """Return a placeholder handler that reports not-yet-implemented."""

    def _handler(_argv: list[str]) -> int:
        raise ValidationError(
            f"subcommand '{name}' not yet implemented (Milestone C+ will wire the real handler)"
        )

    return _handler


# MILESTONE-C-REPLACE-POINT: replace each default handler with the real
# ``{subcommand}_cmd.run`` function as each module lands in Milestones C and
# D. Grep for this marker to find the wiring site. The dispatch table's
# shape (MutableMapping[str, SubcommandHandler]) is stable — only the
# values change. See Plan B "Deferred from MAGI Checkpoint 2" item 3 for
# the planned Protocol-typing refactor.
#: Subcommand name -> handler. Tests and Milestone C+ ``monkeypatch``/replace
#: entries here to install real ``{subcommand}_cmd.run`` functions without
#: touching the dispatcher.
SUBCOMMAND_DISPATCH: MutableMapping[str, SubcommandHandler] = {
    name: _default_handler_factory(name) for name in VALID_SUBCOMMANDS
}


def _print_usage() -> None:
    sys.stderr.write(
        "usage: run_sbtdd.py <subcommand> [args...]\n"
        f"  subcommands: {', '.join(VALID_SUBCOMMANDS)}\n"
    )


def _exit_code_for(exc: SBTDDError) -> int:
    """Look up ``type(exc)`` in :data:`EXIT_CODES`; fall back to 1 when unknown."""
    return EXIT_CODES.get(type(exc), 1)


def main(argv: list[str] | None = None) -> int:
    """Parse argv, dispatch to the matching subcommand, map exceptions to codes.

    Args:
        argv: Tokens after the program name. When ``None`` uses ``sys.argv[1:]``.

    Returns:
        Exit code per sec.S.11.1 taxonomy.
    """
    tokens = list(sys.argv[1:]) if argv is None else list(argv)
    if not tokens:
        _print_usage()
        return 1
    name, rest = tokens[0], tokens[1:]
    if name not in SUBCOMMAND_DISPATCH:
        sys.stderr.write(f"unknown subcommand: '{name}'\n")
        _print_usage()
        return 1
    handler = SUBCOMMAND_DISPATCH[name]
    try:
        return handler(rest)
    except KeyboardInterrupt:
        sys.stderr.write("\nInterrupted by user (SIGINT). Exiting.\n")
        return 130
    except SBTDDError as exc:
        sys.stderr.write(f"{type(exc).__name__}: {exc}\n")
        return _exit_code_for(exc)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_run_sbtdd.py -v`
Expected: PASS — 12 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/run_sbtdd.py tests/test_run_sbtdd.py
git commit -m "test: add run_sbtdd dispatcher scaffold with EXIT_CODES mapping"
```

---

## Phase 2: Dispatchers (Tasks 8-13 — superpowers + magi wrappers)

### Task 8: `superpowers_dispatch.py` — `SkillResult` + `invoke_skill` core

**Files:**
- Create: `skills/sbtdd/scripts/superpowers_dispatch.py`
- Create: `tests/test_superpowers_dispatch.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_superpowers_dispatch.py
from __future__ import annotations

import subprocess
import pytest


def test_skill_result_is_frozen_dataclass():
    from superpowers_dispatch import SkillResult
    from dataclasses import FrozenInstanceError
    res = SkillResult(skill="brainstorming", returncode=0, stdout="ok", stderr="")
    with pytest.raises(FrozenInstanceError):
        res.returncode = 1  # type: ignore[misc]


def test_invoke_skill_returns_skill_result_on_success(monkeypatch):
    from superpowers_dispatch import invoke_skill, SkillResult

    class FakeProc:
        returncode = 0
        stdout = "hello"
        stderr = ""

    calls: dict = {}

    def fake_run(cmd, timeout, capture=True, cwd=None):
        calls["cmd"] = cmd
        calls["timeout"] = timeout
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    result = invoke_skill("brainstorming", args=["arg1"], timeout=42)
    assert isinstance(result, SkillResult)
    assert result.skill == "brainstorming"
    assert result.returncode == 0
    assert result.stdout == "hello"
    assert calls["timeout"] == 42
    # Must use shell=False (as list), no shell=True risk.
    assert isinstance(calls["cmd"], list)
    # Command must include skill invocation marker.
    assert any("brainstorming" in t for t in calls["cmd"])


def test_invoke_skill_raises_quota_on_quota_pattern(monkeypatch):
    from superpowers_dispatch import invoke_skill
    from errors import QuotaExhaustedError

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "Request rejected (429)"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(QuotaExhaustedError) as exc_info:
        invoke_skill("brainstorming")
    assert "429" in str(exc_info.value) or "rate_limit" in str(exc_info.value)


def test_invoke_skill_non_quota_nonzero_raises_validation_error(monkeypatch):
    from superpowers_dispatch import invoke_skill
    from errors import ValidationError

    class FakeProc:
        returncode = 2
        stdout = ""
        stderr = "some unrelated error"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(ValidationError) as exc_info:
        invoke_skill("brainstorming")
    assert "returncode=2" in str(exc_info.value) or "returncode" in str(exc_info.value)


def test_invoke_skill_wraps_timeout_as_validation_error(monkeypatch):
    from superpowers_dispatch import invoke_skill
    from errors import ValidationError

    def fake_run(cmd, timeout, capture=True, cwd=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(ValidationError, match="timed out"):
        invoke_skill("writing-plans")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_superpowers_dispatch.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'superpowers_dispatch'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/superpowers_dispatch.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dispatcher for superpowers skills (/<skill> via claude -p subprocess).

Transport: uses subprocess ``claude -p`` to invoke sub-skills across plugin
boundaries (the only available transport from Python code). Aligned with
MAGI v2.1.3 pattern and documented in CLAUDE.md External Dependencies.

The plugin invokes superpowers skills (``/brainstorming``, ``/writing-plans``,
``/requesting-code-review``, etc.) via the claude CLI. Each wrapper
materialises the invocation as a subprocess and converts failures into
typed :class:`errors.SBTDDError` subclasses so dispatchers at
``run_sbtdd.py`` map them to the sec.S.11.1 exit code taxonomy.

Quota exhaustion (sec.S.11.4) is detected on stderr via
:mod:`quota_detector` BEFORE a generic failure is reported — the caller
then sees :class:`errors.QuotaExhaustedError` and exits 11.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

import quota_detector
import subprocess_utils
from errors import QuotaExhaustedError, ValidationError


@dataclass(frozen=True)
class SkillResult:
    """Outcome of a successful skill invocation.

    Failures never reach the caller as a ``SkillResult`` — they are raised
    as typed exceptions. ``returncode`` is therefore always ``0`` in
    practice but is preserved for diagnostic logs.
    """

    skill: str
    returncode: int
    stdout: str
    stderr: str


def _build_skill_cmd(skill: str, args: list[str] | None) -> list[str]:
    """Build the argv list for ``claude -p`` invoking ``skill``.

    Centralised so ``invoke_skill`` and future callers (e.g. a direct
    pipeline driver) stay in sync.
    """
    cmd = ["claude", "-p", f"/{skill}"]
    if args:
        cmd.extend(args)
    return cmd


def invoke_skill(
    skill: str,
    args: list[str] | None = None,
    timeout: int = 600,
    cwd: str | None = None,
) -> SkillResult:
    """Invoke a superpowers skill via ``claude -p`` subprocess.

    Args:
        skill: Skill name without leading slash (``brainstorming``,
            ``writing-plans``, ...).
        args: Extra tokens appended after the skill invocation.
        timeout: Wall-clock seconds before SIGTERM (sec.S.8.6 — explicit
            timeout mandatory).
        cwd: Working directory; ``None`` uses current.

    Returns:
        :class:`SkillResult` with returncode, stdout, stderr.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        ValidationError: If the subprocess timed out OR exited non-zero without
            matching a quota pattern. Mapped to exit 1 by run_sbtdd.py.
    """
    cmd = _build_skill_cmd(skill, args)
    try:
        result = subprocess_utils.run_with_timeout(
            cmd, timeout=timeout, capture=True, cwd=cwd
        )
    except subprocess.TimeoutExpired as exc:
        raise ValidationError(
            f"skill '/{skill}' timed out after {exc.timeout}s"
        ) from exc

    if result.returncode != 0:
        exhaustion = quota_detector.detect(result.stderr)
        if exhaustion is not None:
            msg = f"{exhaustion.kind}: {exhaustion.raw_message}"
            if exhaustion.reset_time:
                msg += f" (reset: {exhaustion.reset_time})"
            raise QuotaExhaustedError(msg)
        raise ValidationError(
            f"skill '/{skill}' failed (returncode={result.returncode}): {result.stderr.strip()}"
        )
    return SkillResult(
        skill=skill,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_superpowers_dispatch.py -v`
Expected: PASS — 5 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/superpowers_dispatch.py tests/test_superpowers_dispatch.py
git commit -m "test: add superpowers invoke_skill core with quota detection"
```

---

### Task 9: `superpowers_dispatch.py` — typed wrappers for each superpowers skill

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
- Modify: `tests/test_superpowers_dispatch.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_superpowers_dispatch.py (append)
def test_typed_wrappers_cover_all_twelve_skills(monkeypatch):
    """One typed wrapper per superpowers skill; each calls invoke_skill."""
    from superpowers_dispatch import (
        brainstorming,
        writing_plans,
        test_driven_development,
        verification_before_completion,
        requesting_code_review,
        receiving_code_review,
        executing_plans,
        subagent_driven_development,
        dispatching_parallel_agents,
        systematic_debugging,
        using_git_worktrees,
        finishing_a_development_branch,
        SkillResult,
    )

    calls: list[str] = []

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        calls.append(skill)
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    brainstorming(["spec.md"])
    writing_plans(["behavior.md"])
    test_driven_development()
    verification_before_completion()
    requesting_code_review()
    receiving_code_review()
    executing_plans(["plan.md"])
    subagent_driven_development()
    dispatching_parallel_agents()
    systematic_debugging()
    using_git_worktrees()
    finishing_a_development_branch()
    assert calls == [
        "brainstorming",
        "writing-plans",
        "test-driven-development",
        "verification-before-completion",
        "requesting-code-review",
        "receiving-code-review",
        "executing-plans",
        "subagent-driven-development",
        "dispatching-parallel-agents",
        "systematic-debugging",
        "using-git-worktrees",
        "finishing-a-development-branch",
    ]


def test_typed_wrappers_forward_args_and_timeout(monkeypatch):
    from superpowers_dispatch import brainstorming, SkillResult
    captured: dict = {}

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        captured["skill"] = skill
        captured["args"] = args
        captured["timeout"] = timeout
        return SkillResult(skill=skill, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    brainstorming(args=["x", "y"], timeout=900)
    assert captured["skill"] == "brainstorming"
    assert captured["args"] == ["x", "y"]
    assert captured["timeout"] == 900
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_superpowers_dispatch.py -v`
Expected: FAIL con `ImportError: cannot import name 'brainstorming'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/superpowers_dispatch.py` (the `import sys as
_sys` line must be lifted into the top-of-file import block per the "Import
note" immediately below — E402 / Milestone A convention; body snippet assumes
`_sys` already in scope):

```python
# NOTE: wrappers must call invoke_skill via module attribute (not closure capture)
# so tests can monkeypatch "superpowers_dispatch.invoke_skill" at runtime.
# Fix for MAGI Checkpoint 2 iter 1 CRITICAL 1 (melchior): closure binding
# made monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake) a no-op.
# The wrapper resolves ``invoke_skill`` by reaching into the module's own
# namespace at call time (``sys.modules[__name__].invoke_skill``), which IS
# what ``monkeypatch.setattr`` replaces.


def _make_wrapper(skill_name: str):  # noqa: ANN202 — generator helper
    """Return a typed wrapper function bound to ``skill_name``.

    Resolves ``invoke_skill`` at call time via the module's own attribute
    table so ``monkeypatch.setattr('superpowers_dispatch.invoke_skill', ...)``
    takes effect in tests.
    """

    def _wrapper(
        args: list[str] | None = None,
        timeout: int = 600,
        cwd: str | None = None,
    ) -> SkillResult:
        module = _sys.modules[__name__]
        fn = module.invoke_skill  # late-bound: tests can replace via monkeypatch
        return fn(skill_name, args=args, timeout=timeout, cwd=cwd)

    _wrapper.__name__ = skill_name.replace("-", "_")
    _wrapper.__doc__ = f"Invoke the /{skill_name} superpowers skill."
    return _wrapper


brainstorming = _make_wrapper("brainstorming")
writing_plans = _make_wrapper("writing-plans")
test_driven_development = _make_wrapper("test-driven-development")
verification_before_completion = _make_wrapper("verification-before-completion")
requesting_code_review = _make_wrapper("requesting-code-review")
receiving_code_review = _make_wrapper("receiving-code-review")
executing_plans = _make_wrapper("executing-plans")
subagent_driven_development = _make_wrapper("subagent-driven-development")
dispatching_parallel_agents = _make_wrapper("dispatching-parallel-agents")
systematic_debugging = _make_wrapper("systematic-debugging")
using_git_worktrees = _make_wrapper("using-git-worktrees")
finishing_a_development_branch = _make_wrapper("finishing-a-development-branch")
```

> **Import note.** `import sys as _sys` is listed here inside the Task 9
> append block for readability, but the final file must have the import at
> the top of the module (E402 compliance). Reference `import sys` is already
> needed by the module once this append lands; consolidate into the top-of-
> file imports of Task 8 when both are applied — do NOT leave a mid-file
> import in the committed source. The consolidated top-of-file import block
> for `superpowers_dispatch.py` after Task 9 is:
>
> ```python
> from __future__ import annotations
>
> import subprocess
> import sys as _sys
> from dataclasses import dataclass
>
> import quota_detector
> import subprocess_utils
> from errors import QuotaExhaustedError, ValidationError
> ```

Additionally, add a test that verifies monkeypatch now propagates correctly
to the wrappers (closure-rebind regression guard):

```python
# tests/test_superpowers_dispatch.py (append after the two existing Task 9 tests)
def test_wrapper_monkeypatch_propagates_through_module_attr(monkeypatch):
    """Regression guard for the closure-rebind bug (MAGI ckpt2 CRITICAL 1)."""
    from superpowers_dispatch import brainstorming, SkillResult

    def fake_invoke(skill, args=None, timeout=600, cwd=None):
        return SkillResult(skill=skill, returncode=0, stdout="patched", stderr="")

    # Must patch via the module attribute, which the wrapper resolves at call time.
    monkeypatch.setattr("superpowers_dispatch.invoke_skill", fake_invoke)
    result = brainstorming()
    assert result.stdout == "patched", (
        "wrapper closure captured invoke_skill; monkeypatch must replace "
        "module attribute and be picked up via sys.modules[__name__].invoke_skill"
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_superpowers_dispatch.py tests/test_superpowers_dispatch_integration.py -v`
Expected: PASS — 8 tests in `test_superpowers_dispatch.py` (5 from Task 8 + 2
original Task 9 + 1 monkeypatch regression guard) + 1 integration test
(SKIPPED when `claude` is absent, PASSED when present) from the new
`test_superpowers_dispatch_integration.py`.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/superpowers_dispatch.py tests/test_superpowers_dispatch.py tests/test_superpowers_dispatch_integration.py
git commit -m "test: add typed wrappers for 12 superpowers skills"
```

**Automated integration test (MAGI ckpt2 iter 2 WARNING — caspar; supersedes
the iter-1 manual smoke test):** add a new test file
`tests/test_superpowers_dispatch_integration.py` guarded by `pytest.mark.skipif`
so it skips cleanly in environments without the `claude` CLI installed. The
test replaces the previously-untrackable manual smoke acceptance item.

```python
# tests/test_superpowers_dispatch_integration.py (new file)
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""End-to-end integration test: claude CLI subprocess round-trip.

Skipped automatically when `claude` is not on PATH so CI and local
environments without the CLI stay green.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

_CLAUDE_PATH = shutil.which("claude")


@pytest.mark.skipif(
    _CLAUDE_PATH is None,
    reason="claude CLI not installed; integration test skipped",
)
def test_claude_cli_version_invocation() -> None:
    """Invoke ``claude --version`` and assert a non-empty stdout + exit 0.

    Cheap enough to run on every ``make verify`` when the CLI is present,
    and skipped otherwise. Replaces the iter-1 manual smoke-test acceptance
    item with a trackable automated check.
    """
    result = subprocess.run(
        [_CLAUDE_PATH, "--version"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, (
        f"claude --version failed: rc={result.returncode} stderr={result.stderr!r}"
    )
    assert result.stdout.strip(), "claude --version produced empty stdout"
```

Commit alongside the Task 9 commit (same atomic unit — both add coverage for
the superpowers dispatch transport path):

```bash
git add tests/test_superpowers_dispatch_integration.py
# Folded into the Task 9 commit above; no separate commit.
```

---

### Task 10: `magi_dispatch.py` — `MAGIVerdict` dataclass + verdict validation

**Files:**
- Create: `skills/sbtdd/scripts/magi_dispatch.py`
- Create: `tests/test_magi_dispatch.py`
- Create: `tests/fixtures/magi-outputs/go_full.json`
- Create: `tests/fixtures/magi-outputs/strong_no_go_full.json`
- Create: `tests/fixtures/magi-outputs/go_with_caveats_degraded.json`
- Create: `tests/fixtures/magi-outputs/unknown_verdict.json`

- [x] **Step 1: Write failing test**

```python
# tests/test_magi_dispatch.py
from __future__ import annotations

import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "magi-outputs"


def test_magi_verdict_is_frozen_dataclass():
    from magi_dispatch import MAGIVerdict
    from dataclasses import FrozenInstanceError
    v = MAGIVerdict(
        verdict="GO",
        degraded=False,
        conditions=(),
        findings=(),
        raw_output="",
    )
    with pytest.raises(FrozenInstanceError):
        v.verdict = "HOLD"  # type: ignore[misc]


def test_parse_verdict_accepts_all_six_known_labels():
    from magi_dispatch import parse_verdict
    for label in ("STRONG_NO_GO", "HOLD", "HOLD_TIE",
                  "GO_WITH_CAVEATS", "GO", "STRONG_GO"):
        payload = {"verdict": label, "degraded": False,
                   "conditions": [], "findings": []}
        parsed = parse_verdict(json.dumps(payload))
        assert parsed.verdict == label


def test_parse_verdict_normalises_spaces_to_underscores():
    from magi_dispatch import parse_verdict
    payload = {"verdict": "GO WITH CAVEATS", "degraded": False,
               "conditions": [], "findings": []}
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "GO_WITH_CAVEATS"


def test_parse_verdict_rejects_unknown_label():
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    payload = {"verdict": "MAYBE", "degraded": False,
               "conditions": [], "findings": []}
    with pytest.raises(ValidationError, match="MAYBE"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_missing_verdict_field():
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    with pytest.raises(ValidationError, match="verdict"):
        parse_verdict(json.dumps({"degraded": False}))


def test_parse_verdict_rejects_non_json():
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    with pytest.raises(ValidationError, match="JSON"):
        parse_verdict("not valid json at all")


def test_parse_verdict_degraded_flag_preserved():
    from magi_dispatch import parse_verdict
    payload = {"verdict": "GO", "degraded": True,
               "conditions": [], "findings": []}
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.degraded is True


def test_parse_verdict_extracts_conditions_and_findings_as_tuples():
    from magi_dispatch import parse_verdict
    payload = {
        "verdict": "GO_WITH_CAVEATS",
        "degraded": False,
        "conditions": ["doc test edge case", "add audit log"],
        "findings": [{"severity": "INFO", "message": "consider renaming"}],
    }
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.conditions == ("doc test edge case", "add audit log")
    assert len(parsed.findings) == 1
    assert parsed.findings[0]["severity"] == "INFO"
    # Immutability: conditions is tuple.
    assert isinstance(parsed.conditions, tuple)


def test_parse_verdict_loads_from_fixture_go_full():
    from magi_dispatch import parse_verdict
    parsed = parse_verdict((FIXTURES / "go_full.json").read_text(encoding="utf-8"))
    assert parsed.verdict == "GO"
    assert parsed.degraded is False


def test_parse_verdict_loads_from_fixture_degraded():
    from magi_dispatch import parse_verdict
    parsed = parse_verdict(
        (FIXTURES / "go_with_caveats_degraded.json").read_text(encoding="utf-8")
    )
    assert parsed.verdict == "GO_WITH_CAVEATS"
    assert parsed.degraded is True


def test_parse_verdict_loads_from_fixture_strong_no_go():
    from magi_dispatch import parse_verdict
    parsed = parse_verdict(
        (FIXTURES / "strong_no_go_full.json").read_text(encoding="utf-8")
    )
    assert parsed.verdict == "STRONG_NO_GO"


def test_parse_verdict_rejects_unknown_fixture():
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    with pytest.raises(ValidationError):
        parse_verdict((FIXTURES / "unknown_verdict.json").read_text(encoding="utf-8"))


# Strict normalisation edge cases (MAGI Checkpoint 2 iter 1 WARNING — caspar).

def test_parse_verdict_rejects_lowercase_label():
    """Lowercase input must NOT be silently normalised to uppercase."""
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    payload = {"verdict": "go with caveats", "degraded": False,
               "conditions": [], "findings": []}
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_rejects_mixed_case_label():
    """Mixed case ('Go_With_Caveats') must be rejected."""
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    payload = {"verdict": "Go_With_Caveats", "degraded": False,
               "conditions": [], "findings": []}
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_strips_leading_trailing_whitespace():
    """Leading/trailing whitespace is stripped before validation."""
    from magi_dispatch import parse_verdict
    payload = {"verdict": "  GO_WITH_CAVEATS  ", "degraded": False,
               "conditions": [], "findings": []}
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "GO_WITH_CAVEATS"


def test_parse_verdict_rejects_empty_label():
    """Empty or whitespace-only verdict string is rejected."""
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    payload = {"verdict": "   ", "degraded": False,
               "conditions": [], "findings": []}
    with pytest.raises(ValidationError, match="empty"):
        parse_verdict(json.dumps(payload))


def test_parse_verdict_normalises_hyphenated_label():
    """Hyphens in labels are converted to underscores ('STRONG-NO-GO')."""
    from magi_dispatch import parse_verdict
    payload = {"verdict": "STRONG-NO-GO", "degraded": False,
               "conditions": [], "findings": []}
    parsed = parse_verdict(json.dumps(payload))
    assert parsed.verdict == "STRONG_NO_GO"


def test_parse_verdict_rejects_label_with_punctuation():
    """Punctuation beyond underscore/hyphen is rejected."""
    from magi_dispatch import parse_verdict
    from errors import ValidationError
    payload = {"verdict": "GO!WITH!CAVEATS", "degraded": False,
               "conditions": [], "findings": []}
    with pytest.raises(ValidationError, match="invalid characters"):
        parse_verdict(json.dumps(payload))
```

Create fixtures:

`tests/fixtures/magi-outputs/go_full.json`:
```json
{
  "verdict": "GO",
  "degraded": false,
  "conditions": [],
  "findings": []
}
```

`tests/fixtures/magi-outputs/strong_no_go_full.json`:
```json
{
  "verdict": "STRONG_NO_GO",
  "degraded": false,
  "conditions": [],
  "findings": [
    {"severity": "CRITICAL", "message": "architecture regression"}
  ]
}
```

`tests/fixtures/magi-outputs/go_with_caveats_degraded.json`:
```json
{
  "verdict": "GO WITH CAVEATS",
  "degraded": true,
  "conditions": ["add doctest to edge case"],
  "findings": [
    {"severity": "INFO", "message": "consider caching"}
  ]
}
```

`tests/fixtures/magi-outputs/unknown_verdict.json`:
```json
{
  "verdict": "MAYBE_LATER",
  "degraded": false,
  "conditions": [],
  "findings": []
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'magi_dispatch'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/magi_dispatch.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dispatcher for the /magi:magi plugin (sec.S.5.6 Loop 2, Checkpoint 2).

Transport: uses subprocess ``claude -p`` to invoke sub-skills across plugin
boundaries (the only available transport from Python code). Aligned with
MAGI v2.1.3 pattern and documented in CLAUDE.md External Dependencies.

``/magi:magi`` is invoked via the claude CLI (subprocess). Its output is
expected to be a JSON document with the fields ``verdict``, ``degraded``,
``conditions``, ``findings``. This module:

- Invokes the skill via :mod:`subprocess_utils` (same timeout + Windows
  kill-tree discipline as other dispatchers, NF5).
- Applies :mod:`quota_detector` to stderr before reporting generic failures
  (sec.S.11.4).
- Parses the JSON output and validates ``verdict`` against
  :data:`models.VERDICT_RANK`. Labels with spaces are normalised to
  underscores (``"GO WITH CAVEATS"`` -> ``"GO_WITH_CAVEATS"``) since the
  magi plugin emits the human-readable form. Normalisation is strict: only
  whitespace-to-underscore conversion + uppercasing on an already-uppercase
  token. Lowercase / mixed-case / trailing-junk inputs are rejected with
  :class:`ValidationError` (see ``_normalise_verdict_label`` for the exact
  contract).
- Exposes :class:`MAGIVerdict` as the typed output for Loop 2 consumers
  (``pre_merge_cmd``, ``auto_cmd``) that will be built in Milestone C+.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from typing import Any

import quota_detector
import subprocess_utils
from errors import MAGIGateError, QuotaExhaustedError, ValidationError
from models import VERDICT_RANK


@dataclass(frozen=True)
class MAGIVerdict:
    """Parsed result of a /magi:magi invocation (sec.S.5.6)."""

    verdict: str  # key of VERDICT_RANK
    degraded: bool
    conditions: tuple[str, ...]
    findings: tuple[dict[str, Any], ...]
    raw_output: str


def _normalise_verdict_label(raw: str) -> str:
    """Convert the human-readable ``'GO WITH CAVEATS'`` form to enum form.

    Strict contract (MAGI Checkpoint 2 iter 1 WARNING — caspar):

    - Leading/trailing whitespace is stripped.
    - Internal whitespace runs are collapsed to a single underscore.
    - Hyphens are converted to underscores (``STRONG-NO-GO`` -> ``STRONG_NO_GO``).
    - Input MUST already be uppercase after stripping. Lowercase or mixed
      case triggers :class:`ValidationError` from the caller (``parse_verdict``
      only accepts the strict form because MAGI's contract guarantees uppercase
      emission; accepting casual variants would hide upstream bugs).
    - Internal characters outside ``[A-Z0-9_\\s-]`` are rejected.

    Args:
        raw: The ``verdict`` string from MAGI JSON output.

    Returns:
        The normalised label (may or may not be a valid
        :data:`models.VERDICT_RANK` key — the caller validates membership).

    Raises:
        ValidationError: If the input contains lowercase letters, mixed case,
            or characters outside the strict set. ``parse_verdict`` wraps this
            into a caller-visible error.
    """
    stripped = raw.strip()
    if not stripped:
        raise ValidationError("MAGI verdict label is empty")
    # Character class: uppercase letters, digits, whitespace, underscore,
    # hyphen. No lowercase, no punctuation.
    if not re.fullmatch(r"[A-Z0-9_\s-]+", stripped):
        raise ValidationError(
            f"MAGI verdict label '{raw}' contains invalid characters "
            f"(expected [A-Z0-9_ -] only; lowercase/mixed-case not accepted)"
        )
    # Collapse runs of whitespace to single underscore; convert hyphens.
    normalised = re.sub(r"\s+", "_", stripped).replace("-", "_")
    # Collapse runs of underscores (defensive; shouldn't happen given inputs).
    normalised = re.sub(r"_+", "_", normalised)
    return normalised


def parse_verdict(raw_output: str) -> MAGIVerdict:
    """Parse the JSON output of /magi:magi into a typed verdict.

    Args:
        raw_output: stdout captured from the magi subprocess.

    Returns:
        MAGIVerdict with validated label.

    Raises:
        ValidationError: If the output is not JSON, misses ``verdict``, or
            carries an unknown label. The magi plugin contract guarantees
            one of six labels (sec.S.2.3 cross-file contract); other values
            indicate an upstream change the plugin must be updated for.
    """
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"MAGI output is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(
            f"MAGI output must be a JSON object, got {type(payload).__name__}"
        )
    if "verdict" not in payload:
        raise ValidationError("MAGI output missing required 'verdict' field")
    label = _normalise_verdict_label(str(payload["verdict"]))
    if label not in VERDICT_RANK:
        raise ValidationError(
            f"unknown MAGI verdict '{payload['verdict']}' (normalised '{label}'); "
            f"expected one of {sorted(VERDICT_RANK)}"
        )
    degraded = bool(payload.get("degraded", False))
    raw_conditions = payload.get("conditions") or ()
    if not isinstance(raw_conditions, list):
        raise ValidationError(
            f"MAGI 'conditions' must be a list, got {type(raw_conditions).__name__}"
        )
    conditions = tuple(str(c) for c in raw_conditions)
    raw_findings = payload.get("findings") or ()
    if not isinstance(raw_findings, list):
        raise ValidationError(
            f"MAGI 'findings' must be a list, got {type(raw_findings).__name__}"
        )
    findings: tuple[dict[str, Any], ...] = tuple(
        dict(f) if isinstance(f, dict) else {"message": str(f)} for f in raw_findings
    )
    return MAGIVerdict(
        verdict=label,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output=raw_output,
    )
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: PASS — 18 tests (12 original + 6 strict-normalisation edge cases
added per MAGI Checkpoint 2 iter 1 WARNING — caspar).

> **Import note.** The `_normalise_verdict_label` implementation uses
> `re`; `import re` MUST be added to the top-of-file import block (E402
> compliance), NOT inside the function body. The consolidated top-of-file
> imports for `magi_dispatch.py` after Task 10 is:
>
> ```python
> from __future__ import annotations
>
> import json
> import re
> import subprocess
> from dataclasses import dataclass
> from typing import Any
>
> import quota_detector
> import subprocess_utils
> from errors import MAGIGateError, QuotaExhaustedError, ValidationError
> from models import VERDICT_RANK
> ```
>
> (The `import re` inside the function in the code block above is a display
> artifact — when assembling the final `.py` file move it to the module
> header.)

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/magi_dispatch.py tests/test_magi_dispatch.py tests/fixtures/magi-outputs/
git commit -m "test: add MAGIVerdict dataclass and parse_verdict with six-label enum"
```

---

### Task 11: `magi_dispatch.py` — `invoke_magi` subprocess wrapper + quota detection

**Files:**
- Modify: `skills/sbtdd/scripts/magi_dispatch.py`
- Modify: `tests/test_magi_dispatch.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_magi_dispatch.py (append)
def test_invoke_magi_returns_verdict_on_success(monkeypatch):
    from magi_dispatch import invoke_magi

    class FakeProc:
        returncode = 0
        stdout = '{"verdict": "GO", "degraded": false, "conditions": [], "findings": []}'
        stderr = ""

    captured: dict = {}

    def fake_run(cmd, timeout, capture=True, cwd=None):
        captured["cmd"] = cmd
        return FakeProc()

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    v = invoke_magi(context_paths=["spec.md", "plan.md"])
    assert v.verdict == "GO"
    # Command must be a list (shell=False), include magi reference.
    assert isinstance(captured["cmd"], list)
    assert any("magi" in tok for tok in captured["cmd"])


def test_invoke_magi_wraps_timeout_as_magi_gate_error(monkeypatch):
    import subprocess
    from magi_dispatch import invoke_magi
    from errors import MAGIGateError

    def fake_run(cmd, timeout, capture=True, cwd=None):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr("subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(MAGIGateError, match="timed out"):
        invoke_magi(context_paths=["spec.md"])


def test_invoke_magi_raises_quota_on_quota_pattern(monkeypatch):
    from magi_dispatch import invoke_magi
    from errors import QuotaExhaustedError

    class FakeProc:
        returncode = 1
        stdout = ""
        stderr = "You've hit your session limit - resets 3:45pm"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(QuotaExhaustedError):
        invoke_magi(context_paths=["spec.md"])


def test_invoke_magi_non_quota_nonzero_raises_magi_gate_error(monkeypatch):
    from magi_dispatch import invoke_magi
    from errors import MAGIGateError

    class FakeProc:
        returncode = 3
        stdout = ""
        stderr = "consensus agent failure"

    monkeypatch.setattr(
        "subprocess_utils.run_with_timeout",
        lambda cmd, timeout, capture=True, cwd=None: FakeProc(),
    )
    with pytest.raises(MAGIGateError, match="returncode=3"):
        invoke_magi(context_paths=["spec.md"])
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: FAIL con `ImportError: cannot import name 'invoke_magi'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/magi_dispatch.py`:

```python
def _build_magi_cmd(context_paths: list[str]) -> list[str]:
    """Build the argv list for ``claude -p /magi:magi`` with @file refs."""
    cmd = ["claude", "-p", "/magi:magi"]
    for path in context_paths:
        cmd.append(f"@{path}")
    return cmd


def invoke_magi(
    context_paths: list[str],
    timeout: int = 1800,
    cwd: str | None = None,
) -> MAGIVerdict:
    """Invoke /magi:magi and return a parsed MAGIVerdict.

    Args:
        context_paths: Files passed to MAGI as ``@file`` references
            (spec-behavior.md, planning/claude-plan-tdd.md, or the diff).
        timeout: Wall-clock seconds before SIGTERM. Default 1800 (30 min)
            because MAGI runs 3 sub-agents sequentially and may need longer
            than superpowers skills.
        cwd: Working directory.

    Returns:
        :class:`MAGIVerdict` parsed from subprocess stdout.

    Raises:
        QuotaExhaustedError: If stderr matches any quota pattern (sec.S.11.4).
        MAGIGateError: If the subprocess timed out, OR exited non-zero
            without matching a quota pattern. Mapped to exit 8
            (MAGI_GATE_BLOCKED) by run_sbtdd.py.
        ValidationError: If stdout was not valid MAGI JSON / unknown verdict
            (raised by :func:`parse_verdict`, mapped to exit 1).
    """
    cmd = _build_magi_cmd(context_paths)
    try:
        result = subprocess_utils.run_with_timeout(
            cmd, timeout=timeout, capture=True, cwd=cwd
        )
    except subprocess.TimeoutExpired as exc:
        raise MAGIGateError(
            f"/magi:magi timed out after {exc.timeout}s"
        ) from exc

    if result.returncode != 0:
        exhaustion = quota_detector.detect(result.stderr)
        if exhaustion is not None:
            msg = f"{exhaustion.kind}: {exhaustion.raw_message}"
            if exhaustion.reset_time:
                msg += f" (reset: {exhaustion.reset_time})"
            raise QuotaExhaustedError(msg)
        raise MAGIGateError(
            f"/magi:magi failed (returncode={result.returncode}): {result.stderr.strip()}"
        )
    return parse_verdict(result.stdout)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: PASS — 16 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/magi_dispatch.py tests/test_magi_dispatch.py
git commit -m "test: add invoke_magi with quota detection and MAGIGateError mapping"
```

---

### Task 12: `magi_dispatch.py` — `verdict_passes_gate` + degraded semantics (INV-28)

**Files:**
- Modify: `skills/sbtdd/scripts/magi_dispatch.py`
- Modify: `tests/test_magi_dispatch.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_magi_dispatch.py (append)
def test_verdict_passes_gate_strong_go_full_passes():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    v = MAGIVerdict("STRONG_GO", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is True


def test_verdict_passes_gate_go_full_passes():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    v = MAGIVerdict("GO", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is True


def test_verdict_passes_gate_below_threshold_fails():
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    v = MAGIVerdict("HOLD", False, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is False


def test_verdict_passes_gate_degraded_always_fails_even_strong_go():
    """INV-28: degraded verdicts NEVER count as gate-pass (except STRONG_NO_GO abort)."""
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    v = MAGIVerdict("STRONG_GO", True, (), (), "")
    assert verdict_passes_gate(v, threshold="GO_WITH_CAVEATS") is False


def test_verdict_is_strong_no_go_returns_true_for_strong_no_go():
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go
    assert verdict_is_strong_no_go(MAGIVerdict("STRONG_NO_GO", False, (), (), "")) is True


def test_verdict_is_strong_no_go_true_even_when_degraded():
    """INV-28 exception: STRONG_NO_GO degraded still aborts."""
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go
    assert verdict_is_strong_no_go(MAGIVerdict("STRONG_NO_GO", True, (), (), "")) is True


def test_verdict_is_strong_no_go_false_for_other_verdicts():
    from magi_dispatch import MAGIVerdict, verdict_is_strong_no_go
    for label in ("HOLD", "HOLD_TIE", "GO_WITH_CAVEATS", "GO", "STRONG_GO"):
        assert verdict_is_strong_no_go(
            MAGIVerdict(label, False, (), (), "")
        ) is False


def test_verdict_passes_gate_rejects_unknown_threshold():
    """Unknown threshold raises ValidationError (MAGI ckpt2 iter 1 WARNING — melchior).

    Per Milestone A ``errors.py``, schema violations (including unrecognised
    threshold labels) are ``ValidationError``. The previous ``(ValidationError,
    KeyError)`` tuple was ambiguous; the contract is now strict.
    """
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    from errors import ValidationError
    v = MAGIVerdict("GO", False, (), (), "")
    with pytest.raises(ValidationError, match="threshold"):
        verdict_passes_gate(v, threshold="MAYBE")


def test_verdict_passes_gate_rejects_lowercase_threshold():
    """Threshold must be uppercase enum member; lowercase rejected."""
    from magi_dispatch import MAGIVerdict, verdict_passes_gate
    from errors import ValidationError
    v = MAGIVerdict("GO", False, (), (), "")
    with pytest.raises(ValidationError):
        verdict_passes_gate(v, threshold="go_with_caveats")
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: FAIL con `ImportError: cannot import name 'verdict_passes_gate'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/magi_dispatch.py`. The `from models import
verdict_meets_threshold` line MUST be lifted to the top-of-file import
group of `magi_dispatch.py` (next to the existing `from models import
VERDICT_RANK` imported in Task 10); it appears at the start of the
snippet here purely for readability. (Fix 3 / MAGI ckpt2 iter 2 caspar
WARNING; consolidated per Milestone A convention.)

```python
# Consolidated to top of file per E402 / Milestone A convention.
from models import verdict_meets_threshold


def verdict_is_strong_no_go(verdict: MAGIVerdict) -> bool:
    """Return True for STRONG_NO_GO (full or degraded) — INV-28 exception.

    Loop 2 short-circuits on STRONG_NO_GO regardless of degraded flag because
    2 agents voting NO_GO is already decisive evidence (sec.S.5.6.b).
    """
    return verdict.verdict == "STRONG_NO_GO"


def verdict_passes_gate(verdict: MAGIVerdict, threshold: str) -> bool:
    """Evaluate whether ``verdict`` clears the Loop 2 gate (INV-28 applied).

    A verdict passes only when BOTH conditions hold:

    1. ``verdict.verdict`` is ``>= threshold`` in :data:`models.VERDICT_RANK`.
    2. ``verdict.degraded`` is ``False`` (INV-28: degraded verdicts never
       count as gate-pass, regardless of label).

    Args:
        verdict: Parsed MAGI output.
        threshold: Minimum label from ``plugin.local.md`` (``magi_threshold``).

    Returns:
        True iff the verdict should terminate Loop 2 with success.

    Raises:
        ValidationError: If ``threshold`` is not in
            :data:`models.VERDICT_RANK`. (MAGI Checkpoint 2 iter 1 WARNING —
            melchior: the wrapper converts the underlying ``KeyError`` from
            :func:`models.verdict_meets_threshold` into the project-canonical
            ``ValidationError`` so callers see a single typed error.)
    """
    if threshold not in VERDICT_RANK:
        raise ValidationError(
            f"unknown MAGI threshold '{threshold}'; expected one of "
            f"{sorted(VERDICT_RANK)}"
        )
    if verdict.degraded:
        return False
    return verdict_meets_threshold(verdict.verdict, threshold)
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: PASS — 31 tests (18 after Task 10 + 4 Task 11 + 9 Task 12:
8 original in iter 1 plan + 1 new lowercase-threshold edge case).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/magi_dispatch.py tests/test_magi_dispatch.py
git commit -m "test: add verdict_passes_gate and STRONG_NO_GO helper for INV-28"
```

---

### Task 13: `magi_dispatch.py` — `write_verdict_artifact` for `.claude/magi-verdict.json`

**Files:**
- Modify: `skills/sbtdd/scripts/magi_dispatch.py`
- Modify: `tests/test_magi_dispatch.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_magi_dispatch.py (append)
def test_write_verdict_artifact_creates_parent_directories(tmp_path):
    from magi_dispatch import MAGIVerdict, write_verdict_artifact
    v = MAGIVerdict("GO_WITH_CAVEATS", False,
                    conditions=("fix edge case",),
                    findings=(),
                    raw_output='{"verdict":"GO_WITH_CAVEATS"}')
    target = tmp_path / ".claude" / "magi-verdict.json"
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["verdict"] == "GO_WITH_CAVEATS"
    assert data["degraded"] is False
    assert data["conditions"] == ["fix edge case"]
    assert data["timestamp"] == "2026-04-19T10:00:00Z"


def test_write_verdict_artifact_is_atomic(tmp_path):
    """write fails -> no partial file, no tmp leak."""
    from magi_dispatch import MAGIVerdict, write_verdict_artifact
    v = MAGIVerdict("GO", False, (), (), "")
    target = tmp_path / "subdir" / "verdict.json"
    # Parent doesn't exist; function MUST create it.
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    assert target.exists()
    # No stray tmp files.
    assert list(target.parent.glob("*.tmp.*")) == []


def test_write_verdict_artifact_preserves_degraded_flag(tmp_path):
    from magi_dispatch import MAGIVerdict, write_verdict_artifact
    v = MAGIVerdict("GO", True, (), (), "")
    target = tmp_path / "verdict.json"
    write_verdict_artifact(v, target, timestamp="2026-04-19T10:00:00Z")
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["degraded"] is True
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: FAIL con `ImportError: cannot import name 'write_verdict_artifact'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/magi_dispatch.py`. The `import os` and
`from pathlib import Path` lines MUST be lifted to the top-of-file import
group of `magi_dispatch.py`; they appear at the start of the snippet
here purely for readability. (Fix 3 / MAGI ckpt2 iter 2 caspar
WARNING; consolidated per Milestone A convention.)

```python
# Consolidated to top of file per E402 / Milestone A convention.
import os
from pathlib import Path


def write_verdict_artifact(
    verdict: MAGIVerdict,
    target: Path,
    timestamp: str,
) -> None:
    """Write ``.claude/magi-verdict.json`` atomically (sec.S.5.6 postcondicion).

    The file is consumed by ``finalize`` (sec.M.7) to reject degraded
    verdicts as gate-blocking. Field layout matches the spec contract:
    ``timestamp``, ``verdict``, ``degraded``, ``conditions``, ``findings``.

    Args:
        verdict: Parsed MAGI verdict.
        target: Destination file path. Parent directories are created.
        timestamp: ISO 8601 string with ``Z`` suffix (caller supplies;
            state_file._validate_iso8601 conventions apply).

    Raises:
        OSError: If the atomic replace fails. No partial file, no
            ``*.tmp.<pid>`` leak.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": timestamp,
        "verdict": verdict.verdict,
        "degraded": verdict.degraded,
        "conditions": list(verdict.conditions),
        "findings": [dict(f) for f in verdict.findings],
    }
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_magi_dispatch.py -v`
Expected: PASS — 34 tests (31 after Task 12 + 3 new for write_verdict_artifact).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/magi_dispatch.py tests/test_magi_dispatch.py
git commit -m "test: add write_verdict_artifact for .claude/magi-verdict.json"
```

---

## Phase 3: Reporters (Tasks 14-18 — TDD-Guard test.json schema + stack adapters)

### Task 14: `reporters/tdd_guard_schema.py` — dataclasses for `test.json`

**Files:**
- Create: `skills/sbtdd/scripts/reporters/tdd_guard_schema.py`
- Create: `tests/test_reporters_schema.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_reporters_schema.py
from __future__ import annotations

import json
import pytest


def test_test_error_is_frozen_dataclass():
    from reporters.tdd_guard_schema import TestError
    from dataclasses import FrozenInstanceError
    err = TestError(message="msg", stack="trace")
    with pytest.raises(FrozenInstanceError):
        err.message = "other"  # type: ignore[misc]


def test_test_entry_defaults_to_no_errors():
    from reporters.tdd_guard_schema import TestEntry
    e = TestEntry(name="t1", full_name="tests/t.py::t1", state="passed")
    assert e.errors == ()


def test_test_module_collects_entries():
    from reporters.tdd_guard_schema import TestEntry, TestModule
    e1 = TestEntry(name="t1", full_name="f::t1", state="passed")
    e2 = TestEntry(name="t2", full_name="f::t2", state="failed")
    m = TestModule(module_id="tests/t.py", tests=(e1, e2))
    assert len(m.tests) == 2


def test_test_json_valid_reason_values():
    from reporters.tdd_guard_schema import VALID_REASONS
    assert VALID_REASONS == ("passed", "failed", "interrupted")


def test_test_json_rejects_invalid_state():
    from reporters.tdd_guard_schema import TestEntry, VALID_STATES
    from errors import ValidationError
    assert VALID_STATES == ("passed", "failed", "skipped")
    with pytest.raises(ValidationError):
        TestEntry(name="t1", full_name="f::t1", state="bogus")


def test_test_json_to_dict_contract():
    from reporters.tdd_guard_schema import (
        TestEntry, TestError, TestModule, TestJSON,
    )
    e = TestEntry(
        name="t1",
        full_name="tests/t.py::t1",
        state="failed",
        errors=(TestError(message="oops", stack="frame"),),
    )
    m = TestModule(module_id="tests/t.py", tests=(e,))
    j = TestJSON(test_modules=(m,), reason="failed")
    data = j.to_dict()
    assert data == {
        "testModules": [
            {
                "moduleId": "tests/t.py",
                "tests": [
                    {
                        "name": "t1",
                        "fullName": "tests/t.py::t1",
                        "state": "failed",
                        "errors": [{"message": "oops", "stack": "frame"}],
                    }
                ],
            }
        ],
        "reason": "failed",
    }


def test_test_json_omits_errors_key_when_empty():
    from reporters.tdd_guard_schema import TestEntry, TestModule, TestJSON
    e = TestEntry(name="t1", full_name="f::t1", state="passed")
    j = TestJSON(
        test_modules=(TestModule(module_id="f", tests=(e,)),),
        reason="passed",
    )
    data = j.to_dict()
    # Passing tests: no "errors" key (conftest.py behavior).
    assert "errors" not in data["testModules"][0]["tests"][0]
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporters_schema.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'reporters.tdd_guard_schema'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/reporters/tdd_guard_schema.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Dataclass representation + writer for the TDD-Guard ``test.json`` schema.

TDD-Guard expects a JSON document with the exact shape::

    {
      "testModules": [
        {
          "moduleId": "<path>",
          "tests": [
            {
              "name": "<name>",
              "fullName": "<name>",
              "state": "passed|failed|skipped",
              "errors": [{"message": "...", "stack": "..."}]    # optional
            }
          ]
        }
      ],
      "reason": "passed|failed|interrupted"
    }

The project-root ``conftest.py`` already produces this document for the
Python stack. This module factors out the schema so ``ctest_reporter``
and ``rust_reporter`` can reuse the same typed structure + writer. It
also gives ``conftest.py.template`` (Task 23) a concrete reference.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from errors import ValidationError

#: Allowed ``state`` values (TDD-Guard contract).
VALID_STATES: tuple[str, ...] = ("passed", "failed", "skipped")

#: Allowed ``reason`` values (TDD-Guard contract).
VALID_REASONS: tuple[str, ...] = ("passed", "failed", "interrupted")


@dataclass(frozen=True)
class TestError:
    """Single failure representation."""

    message: str
    stack: str


@dataclass(frozen=True)
class TestEntry:
    """Individual test result (post-run)."""

    name: str
    full_name: str
    state: str
    errors: tuple[TestError, ...] = ()

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValidationError(
                f"TestEntry.state='{self.state}' not in {list(VALID_STATES)}"
            )


@dataclass(frozen=True)
class TestModule:
    """Collection of tests grouped by module_id (typically a file path)."""

    module_id: str
    tests: tuple[TestEntry, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TestJSON:
    """Root object of the TDD-Guard test.json document."""

    test_modules: tuple[TestModule, ...]
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in VALID_REASONS:
            raise ValidationError(
                f"TestJSON.reason='{self.reason}' not in {list(VALID_REASONS)}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to the exact JSON shape TDD-Guard expects."""
        modules: list[dict[str, Any]] = []
        for m in self.test_modules:
            tests_out: list[dict[str, Any]] = []
            for t in m.tests:
                entry: dict[str, Any] = {
                    "name": t.name,
                    "fullName": t.full_name,
                    "state": t.state,
                }
                if t.errors:
                    entry["errors"] = [
                        {"message": e.message, "stack": e.stack} for e in t.errors
                    ]
                tests_out.append(entry)
            modules.append({"moduleId": m.module_id, "tests": tests_out})
        return {"testModules": modules, "reason": self.reason}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporters_schema.py -v`
Expected: PASS — 7 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/reporters/tdd_guard_schema.py tests/test_reporters_schema.py
git commit -m "test: add TDD-Guard test.json dataclasses and to_dict serialiser"
```

---

### Task 15: `reporters/tdd_guard_schema.py` — atomic `write_test_json` function

**Files:**
- Modify: `skills/sbtdd/scripts/reporters/tdd_guard_schema.py`
- Modify: `tests/test_reporters_schema.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_reporters_schema.py (append)
def test_write_test_json_creates_parent_dir_and_writes(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry, TestModule, TestJSON, write_test_json,
    )
    j = TestJSON(
        test_modules=(TestModule(
            module_id="tests/t.py",
            tests=(TestEntry(name="t1", full_name="f::t1", state="passed"),),
        ),),
        reason="passed",
    )
    target = tmp_path / ".claude" / "tdd-guard" / "data" / "test.json"
    write_test_json(j, target)
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["reason"] == "passed"
    assert data["testModules"][0]["moduleId"] == "tests/t.py"


def test_write_test_json_atomic_no_tmp_leak(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry, TestModule, TestJSON, write_test_json,
    )
    j = TestJSON(
        test_modules=(TestModule(
            module_id="m",
            tests=(TestEntry(name="t", full_name="m::t", state="passed"),),
        ),),
        reason="passed",
    )
    target = tmp_path / "test.json"
    write_test_json(j, target)
    # No *.tmp.<pid> file should remain.
    assert list(tmp_path.glob("*.tmp.*")) == []


def test_write_test_json_overwrites_existing(tmp_path):
    from reporters.tdd_guard_schema import (
        TestEntry, TestModule, TestJSON, write_test_json,
    )
    target = tmp_path / "test.json"
    target.write_text('{"stale": true}', encoding="utf-8")
    j = TestJSON(
        test_modules=(TestModule(
            module_id="m",
            tests=(TestEntry(name="t", full_name="m::t", state="passed"),),
        ),),
        reason="passed",
    )
    write_test_json(j, target)
    data = json.loads(target.read_text(encoding="utf-8"))
    assert "stale" not in data
    assert data["reason"] == "passed"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporters_schema.py -v`
Expected: FAIL con `ImportError: cannot import name 'write_test_json'`.

- [x] **Step 3: Write minimal implementation**

Append to `skills/sbtdd/scripts/reporters/tdd_guard_schema.py`:

```python
def write_test_json(doc: TestJSON, target: Path) -> None:
    """Write ``doc`` to ``target`` atomically (tmp + os.replace).

    Creates parent directories if missing. On :class:`OSError` during the
    final ``os.replace``, the tmp file is unlinked before re-raising so no
    ``*.tmp.<pid>`` residue is left behind (mirrors ``state_file.save``
    and ``magi_dispatch.write_verdict_artifact``).

    Args:
        doc: Fully constructed :class:`TestJSON` to serialise.
        target: Destination path (typically
            ``.claude/tdd-guard/data/test.json``).

    Raises:
        OSError: If the atomic replace fails.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(doc.to_dict(), indent=2), encoding="utf-8")
    try:
        os.replace(tmp, target)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporters_schema.py -v`
Expected: PASS — 10 tests.

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/reporters/tdd_guard_schema.py tests/test_reporters_schema.py
git commit -m "test: add write_test_json atomic writer with tmp cleanup on error"
```

---

### Task 16: `reporters/rust_reporter.py` — `cargo nextest | tdd-guard-rust` pipeline

**Files:**
- Create: `skills/sbtdd/scripts/reporters/rust_reporter.py`
- Create: `tests/test_reporters_rust.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_reporters_rust.py
from __future__ import annotations

import subprocess
import pytest


def test_run_pipeline_invokes_nextest_piped_to_tdd_guard_rust(monkeypatch):
    from reporters import rust_reporter

    call_log: list[tuple[str, list[str]]] = []

    class FakeProc:
        def __init__(self, cmd, stdout=None, stdin=None, **kwargs):
            self.returncode = 0
            self.cmd = cmd
            self.stdout = b"junit-output"
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (self.stdout, self.stderr)

        def wait(self, timeout=None):
            return self.returncode

        def poll(self):
            return self.returncode

    def fake_popen(cmd, stdout=None, stdin=None, stderr=None, **kwargs):
        call_log.append(("popen", cmd))
        return FakeProc(cmd, stdout=stdout, stdin=stdin)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rc = rust_reporter.run_pipeline(cwd=".")
    assert rc == 0
    # Two popens: cargo nextest, then tdd-guard-rust.
    assert len(call_log) == 2
    first, second = call_log[0][1], call_log[1][1]
    assert "cargo" in first[0]
    assert any("nextest" in tok for tok in first)
    assert "tdd-guard-rust" in second[0]


def test_run_pipeline_no_shell_obligatorio(monkeypatch):
    """Both Popen calls MUST use lists (shell=False equivalent); no str commands."""
    from reporters import rust_reporter

    captured_shell: list[bool] = []

    class FakeProc:
        def __init__(self, *a, **k):
            self.returncode = 0
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (b"", b"")

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    def fake_popen(cmd, shell=False, **kwargs):
        captured_shell.append(shell)
        assert isinstance(cmd, list), f"Popen must receive list, got {type(cmd).__name__}"
        return FakeProc()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rust_reporter.run_pipeline(cwd=".")
    assert all(s is False for s in captured_shell)


def test_run_pipeline_propagates_nonzero_from_tdd_guard_rust(monkeypatch):
    from reporters import rust_reporter

    class FailingProc:
        def __init__(self, *a, **k):
            self.returncode = 2
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (b"", b"")

        def wait(self, timeout=None):
            return 2

        def poll(self):
            return 2

    class PassingProc(FailingProc):
        returncode = 0

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    calls: list[object] = []

    def fake_popen(cmd, **kwargs):
        # First call (nextest) passes, second (tdd-guard-rust) fails.
        proc = PassingProc() if not calls else FailingProc()
        calls.append(proc)
        return proc

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    rc = rust_reporter.run_pipeline(cwd=".")
    assert rc == 2


def test_run_pipeline_honours_timeout_and_kills_both_procs(monkeypatch):
    """Triple-flagged MAGI Checkpoint 2 iter 1 WARNING (melchior/caspar/balthasar).

    When the pipeline exceeds its timeout, both processes must be
    kill-tree'd (Windows taskkill-before-kill via subprocess_utils.kill_tree)
    and ``subprocess.TimeoutExpired`` must surface to the caller.
    """
    from reporters import rust_reporter

    killed: list[object] = []

    class HangingProc:
        def __init__(self, *a, **k):
            self.returncode = None
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 1)

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=timeout or 1)

        def poll(self):
            return None

    procs: list[HangingProc] = []

    def fake_popen(cmd, **kwargs):
        proc = HangingProc()
        procs.append(proc)
        return proc

    def fake_kill_tree(proc):
        killed.append(proc)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("subprocess_utils.kill_tree", fake_kill_tree)

    with pytest.raises(subprocess.TimeoutExpired):
        rust_reporter.run_pipeline(cwd=".", timeout=1)

    # Both nextest AND reporter procs must have been kill-tree'd.
    assert len(killed) == 2
    assert procs[0] in killed
    assert procs[1] in killed


def test_run_pipeline_default_timeout_is_documented(monkeypatch):
    """The default timeout is 300s (documented in module docstring)."""
    from reporters import rust_reporter
    # The module exposes the constant for discoverability.
    assert rust_reporter._DEFAULT_TIMEOUT_SEC == 300


def test_run_pipeline_nextest_exit_slack_constant_exposed():
    """The nextest post-EOF slack is a named constant, not a magic number.

    Elevated per MAGI Checkpoint 2 iter 2 WARNING (melchior): hardcoded
    5-second timeouts inside the cleanup path are a maintenance smell.
    """
    from reporters import rust_reporter
    assert rust_reporter._NEXTEST_EXIT_SLACK_SECONDS == 5


def test_run_pipeline_nextest_wait_timeout_also_kills_both_procs(monkeypatch):
    """Fix 4 (MAGI ckpt2 iter 2 caspar WARNING): if the *nextest* post-EOF
    wait times out (while reporter has already finished cleanly), both
    procs must still be kill-tree'd before TimeoutExpired re-raises.
    Orphaning nextest here would leak a child process."""
    from reporters import rust_reporter

    killed: list[object] = []

    class ReporterFinishedProc:
        """Reporter exits cleanly before timeout."""

        def __init__(self):
            self.returncode = 0
            self.stdout = b"ok"
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            return (self.stdout, self.stderr)

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    class NextestHangingProc:
        """Nextest hangs past the exit slack."""

        def __init__(self):
            self.returncode = None
            self.stdout = b""
            self.stderr = b""

        def communicate(self, input=None, timeout=None):
            raise subprocess.TimeoutExpired(cmd="nextest", timeout=timeout or 1)

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd="nextest", timeout=timeout or 1)

        def poll(self):
            return None

    procs: list[object] = []

    def fake_popen(cmd, **kwargs):
        # First call -> nextest (hangs), second -> reporter (finishes).
        proc: object
        if not procs:
            proc = NextestHangingProc()
        else:
            proc = ReporterFinishedProc()
        procs.append(proc)
        return proc

    def fake_kill_tree(proc):
        killed.append(proc)

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    monkeypatch.setattr("subprocess_utils.kill_tree", fake_kill_tree)

    with pytest.raises(subprocess.TimeoutExpired):
        rust_reporter.run_pipeline(cwd=".", timeout=60)

    # Both procs kill-tree'd despite only nextest being the timeout cause.
    assert len(killed) == 2
    assert procs[0] in killed, "nextest (the hanging one) must be killed"
    assert procs[1] in killed, "reporter must also be killed defensively"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporters_rust.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'reporters.rust_reporter'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/reporters/rust_reporter.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Rust stack TDD-Guard reporter: pipeline ``cargo nextest`` | ``tdd-guard-rust``.

Invoked as ``verification_commands[0]`` by ``--stack rust`` (sec.S.4.2).
Runs ``cargo nextest run --message-format libtest-json-plus`` (the machine-
readable JSON format nextest emits) and pipes stdout into the external
``tdd-guard-rust`` binary, which translates it into the canonical
``.claude/tdd-guard/data/test.json`` schema.

Never uses ``shell=True``. Arguments passed as lists. The ``tdd-guard-rust``
binary is a mandatory external dependency (sec.S.1.3 item 6 Rust); dependency
check (dependency_check.check_stack_toolchain('rust')) verifies it before
any reporter invocation.

Deliberate ``subprocess.Popen`` exception (vs the project-standard
``subprocess_utils.run_with_timeout``): piping stdout of one process into
stdin of another requires two concurrent handles, which the helper does not
expose. The timeout discipline from NF5 is preserved here manually via the
``timeout`` parameter + ``subprocess_utils.kill_tree`` for cleanup on the
two Popens (MAGI Checkpoint 2 iter 1 triple-flagged WARNING from melchior,
caspar, and balthasar).
"""

from __future__ import annotations

import subprocess
import sys
from typing import Iterable

import subprocess_utils


_NEXTEST_CMD: tuple[str, ...] = (
    "cargo",
    "nextest",
    "run",
    "--message-format",
    "libtest-json-plus",
)
_TDD_GUARD_RUST_CMD: tuple[str, ...] = ("tdd-guard-rust",)
#: Default timeout for the nextest + reporter pipeline. Long runs are
#: legitimate (integration suites), but 5 min is the outer bound before
#: the caller must explicitly raise the cap.
_DEFAULT_TIMEOUT_SEC: int = 300
#: Slack window given to ``cargo nextest`` to flush and exit after the
#: downstream reporter has already consumed its stdout. Nextest's epilog
#: (JSON footer + child-test teardown) runs post-EOF on the pipe, and 5s
#: is empirically more than enough on CI. Elevated to a named constant
#: per MAGI Checkpoint 2 iter 2 WARNING (melchior): hardcoded integers in
#: timeout paths are a maintenance smell.
_NEXTEST_EXIT_SLACK_SECONDS: int = 5


def run_pipeline(
    cwd: str | None = None,
    nextest_cmd: Iterable[str] = _NEXTEST_CMD,
    reporter_cmd: Iterable[str] = _TDD_GUARD_RUST_CMD,
    timeout: int = _DEFAULT_TIMEOUT_SEC,
) -> int:
    """Run ``cargo nextest run | tdd-guard-rust`` as a two-process pipeline.

    Args:
        cwd: Working directory for both subprocesses. ``None`` uses current.
        nextest_cmd: Override the nextest invocation (tests / future stacks).
        reporter_cmd: Override the reporter invocation.
        timeout: Wall-clock seconds for the combined pipeline before
            SIGTERM + cleanup via :func:`subprocess_utils.kill_tree`.
            Default 300s (5 min). Raising the cap is the caller's
            responsibility.

    Returns:
        The exit code of the reporter subprocess (right-hand side of the
        pipe). The caller (verification runner) propagates this to its
        overall return code.

    Raises:
        subprocess.TimeoutExpired: If the combined pipeline exceeds
            ``timeout``. Both nextest and tdd-guard-rust are kill-tree'd
            (Windows taskkill-before-kill via
            :func:`subprocess_utils.kill_tree`) before the exception
            surfaces. The caller can wrap this as needed.
    """
    nextest = subprocess.Popen(
        list(nextest_cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
    )
    reporter = subprocess.Popen(
        list(reporter_cmd),
        stdin=nextest.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        cwd=cwd,
    )
    # Close nextest's stdout in the parent so the reporter sees EOF when
    # nextest exits (POSIX pipeline semantics).
    if nextest.stdout is not None:
        nextest.stdout.close()
    try:
        out, err = reporter.communicate(timeout=timeout)
        # Reporter is done; ensure nextest is also wrapped up within the
        # explicit slack window. This wait CAN itself raise TimeoutExpired
        # (e.g., nextest hangs after emitting its JSON footer) and that
        # path is just as lethal as the reporter timing out — so the same
        # except-clause below handles both, killing BOTH procs before
        # re-raising. Fix 4 (MAGI ckpt2 iter 2 caspar WARNING): the
        # cleanup path is shared and guaranteed so no orphan remains on
        # either failure mode.
        nextest.wait(timeout=_NEXTEST_EXIT_SLACK_SECONDS)
    except subprocess.TimeoutExpired:
        # Kill BOTH processes cross-platform (Windows taskkill-before-kill)
        # regardless of which wait raised. kill_tree is idempotent on an
        # already-exited proc (subprocess_utils guarantees this on both
        # POSIX and Windows).
        subprocess_utils.kill_tree(reporter)
        subprocess_utils.kill_tree(nextest)
        # Drain pipes to avoid zombie FDs; ignore further timeouts here.
        for proc in (reporter, nextest):
            try:
                proc.communicate(timeout=_NEXTEST_EXIT_SLACK_SECONDS)
            except subprocess.TimeoutExpired:
                pass
        raise
    if err:
        sys.stderr.write(err.decode("utf-8", errors="replace"))
    if out:
        sys.stdout.write(out.decode("utf-8", errors="replace"))
    return reporter.returncode


def main() -> int:
    """Entry point when invoked as a standalone script."""
    return run_pipeline()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporters_rust.py -v`
Expected: PASS — 7 tests (3 original + 2 timeout-and-kill-tree tests added
per MAGI Checkpoint 2 iter 1 WARNING triple-flagged by melchior/caspar/balthasar,
+ 2 new MAGI ckpt2 iter 2 tests: `_NEXTEST_EXIT_SLACK_SECONDS` constant
exposed (Fix 8 / melchior) and `nextest_wait_timeout_also_kills_both_procs`
(Fix 4 / caspar)).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/reporters/rust_reporter.py tests/test_reporters_rust.py
git commit -m "test: add rust_reporter nextest to tdd-guard-rust pipeline"
```

---

### Task 17: `reporters/ctest_reporter.py` — parse JUnit XML -> `TestJSON`

**Files:**
- Create: `skills/sbtdd/scripts/reporters/ctest_reporter.py`
- Create: `tests/test_reporters_ctest.py`
- Create: `tests/fixtures/ctest-junit/all_passed.xml`
- Create: `tests/fixtures/ctest-junit/mixed.xml`
- Create: `tests/fixtures/ctest-junit/empty.xml`
- Create: `tests/fixtures/ctest-junit/missing_classname.xml` (MAGI ckpt2 iter 1 WARNING — melchior)
- Create: `tests/fixtures/ctest-junit/classname_and_suite_empty.xml` (defensive pathological input)

- [x] **Step 1: Write failing test**

```python
# tests/test_reporters_ctest.py
from __future__ import annotations

import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "ctest-junit"


def test_parse_junit_all_passed():
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "all_passed.xml")
    assert doc.reason == "passed"
    # Two test cases across one suite.
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) == 2
    assert all(t.state == "passed" for t in all_tests)


def test_parse_junit_mixed_has_failed_reason_and_errors():
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "mixed.xml")
    assert doc.reason == "failed"
    all_tests = {t.name: t for m in doc.test_modules for t in m.tests}
    assert all_tests["Trivial.Pass"].state == "passed"
    assert all_tests["Parser.Fails"].state == "failed"
    assert len(all_tests["Parser.Fails"].errors) >= 1
    assert "expected" in all_tests["Parser.Fails"].errors[0].message.lower()


def test_parse_junit_empty_yields_passed_reason_no_tests():
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "empty.xml")
    assert doc.reason == "passed"
    assert doc.test_modules == () or all(len(m.tests) == 0 for m in doc.test_modules)


def test_parse_junit_missing_file_raises_validation_error():
    from reporters.ctest_reporter import parse_junit
    from errors import ValidationError
    with pytest.raises(ValidationError, match="not found"):
        parse_junit(FIXTURES / "does_not_exist.xml")


def test_parse_junit_invalid_xml_raises_validation_error(tmp_path):
    from reporters.ctest_reporter import parse_junit
    from errors import ValidationError
    bad = tmp_path / "bad.xml"
    bad.write_text("<not-valid", encoding="utf-8")
    with pytest.raises(ValidationError, match="XML"):
        parse_junit(bad)


def test_run_writes_test_json_at_destination(tmp_path):
    from reporters.ctest_reporter import run
    src = FIXTURES / "mixed.xml"
    dst = tmp_path / ".claude" / "tdd-guard" / "data" / "test.json"
    rc = run(src, dst)
    assert rc == 0
    assert dst.exists()
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert data["reason"] == "failed"
    assert any(
        t["state"] == "failed"
        for m in data["testModules"]
        for t in m["tests"]
    )


def test_parse_junit_falls_back_to_suite_name_when_classname_missing():
    """MAGI Checkpoint 2 iter 1 WARNING (melchior).

    Some ctest toolchains emit ``<testcase classname=""`` or omit the
    ``classname`` attribute entirely. In that case the parser must fall
    back to the enclosing ``<testsuite name="...">`` rather than producing
    ``.testname`` strings.
    """
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "missing_classname.xml")
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) == 2
    # Both tests must have non-empty, suite-prefixed names (no leading dot).
    for t in all_tests:
        assert "." in t.name
        assert not t.name.startswith(".")
        # Fallback: classname == suite name "Fallback".
        assert t.name.startswith("Fallback.")


def test_parse_junit_handles_all_missing_attributes():
    """Pathological input: classname missing AND suite name missing.

    Defensive coverage: the parser must not crash; it uses ``'unknown'`` as
    the last-resort fallback.
    """
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "classname_and_suite_empty.xml")
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) >= 1
    # No crash, no empty-prefix names.
    for t in all_tests:
        assert t.name
        assert not t.name.startswith(".")
```

Create fixtures:

`tests/fixtures/ctest-junit/all_passed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="CoreSuite" tests="2" failures="0" errors="0">
    <testcase classname="Core" name="startup" time="0.01"/>
    <testcase classname="Core" name="shutdown" time="0.02"/>
  </testsuite>
</testsuites>
```

`tests/fixtures/ctest-junit/mixed.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="ParserSuite" tests="2" failures="1" errors="0">
    <testcase classname="Trivial" name="Pass" time="0.01"/>
    <testcase classname="Parser" name="Fails" time="0.03">
      <failure message="expected &apos;{&apos; at line 3" type="AssertionFailure">
        Stack trace:
          parser.cpp:142
      </failure>
    </testcase>
  </testsuite>
</testsuites>
```

`tests/fixtures/ctest-junit/empty.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
</testsuites>
```

`tests/fixtures/ctest-junit/missing_classname.xml` (some toolchains emit
`classname=""` or omit it entirely — MAGI ckpt2 iter 1 WARNING, melchior):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="Fallback" tests="2" failures="0" errors="0">
    <testcase classname="" name="Alpha" time="0.01"/>
    <testcase name="Beta" time="0.02"/>
  </testsuite>
</testsuites>
```

`tests/fixtures/ctest-junit/classname_and_suite_empty.xml` (pathological —
both classname and suite name missing):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite tests="1" failures="0" errors="0">
    <testcase name="Orphan" time="0.01"/>
  </testsuite>
</testsuites>
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reporters_ctest.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'reporters.ctest_reporter'`.

- [x] **Step 3: Write minimal implementation**

Create `skills/sbtdd/scripts/reporters/ctest_reporter.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""C++ stack TDD-Guard reporter: parse ctest JUnit XML -> test.json.

Invoked as the second command in ``verification_commands`` for
``--stack cpp`` (sec.S.4.2). Reads the file produced by
``ctest --output-junit <path>`` and writes the TDD-Guard JSON via
:mod:`reporters.tdd_guard_schema`.

v0.1 only supports the JUnit XML emitted by ``ctest`` itself; other
runners (GoogleTest direct, Catch2, bazel, meson) are out of scope
(sec.S.13 item 8).

XXE / entity expansion risk (MAGI Checkpoint 2 iter 1 WARNING — caspar):
ctest JUnit output is trusted local input produced by the project's own
build, NOT network-received content. We use stdlib
:mod:`xml.etree.ElementTree` without ``defusedxml`` because (1) adding a
runtime dependency contradicts INV-20 ("stdlib-only on hot paths"), (2)
the input is under the same trust boundary as the source tree, and (3)
``ET.parse`` in CPython 3.9+ does not resolve external entities by default.
If v0.2 adds support for runner output received across trust boundaries
(CI agents, remote builders), swap to ``defusedxml.ElementTree.parse`` and
pin ``defusedxml>=0.7``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from errors import ValidationError
from reporters.tdd_guard_schema import (
    TestEntry,
    TestError,
    TestJSON,
    TestModule,
    write_test_json,
)


def _collect_errors(testcase: ET.Element) -> tuple[TestError, ...]:
    """Extract <failure> and <error> children as TestError entries."""
    errors: list[TestError] = []
    for tag in ("failure", "error"):
        for node in testcase.findall(tag):
            message = node.attrib.get("message", "").strip()
            body = (node.text or "").strip()
            errors.append(TestError(message=message or tag, stack=body))
    return tuple(errors)


def _state_for(testcase: ET.Element) -> str:
    """Map JUnit XML testcase children to TDD-Guard state."""
    if testcase.find("failure") is not None or testcase.find("error") is not None:
        return "failed"
    if testcase.find("skipped") is not None:
        return "skipped"
    return "passed"


def _resolve_classname(testcase: ET.Element, fallback_suite_name: str) -> str:
    """Return a non-empty classname for ``testcase`` (MAGI ckpt2 WARNING — melchior).

    ctest ``--output-junit`` usually emits ``<testcase classname="X" ...>``,
    but some toolchains emit ``classname=""`` or omit the attribute
    entirely. In those cases fall back to the enclosing ``<testsuite>``'s
    ``name`` attribute (already available as ``module_id``).

    Args:
        testcase: The ``<testcase>`` element.
        fallback_suite_name: The enclosing suite's ``name`` attribute.

    Returns:
        A non-empty classname. ``"unknown"`` only if both classname AND
        suite name are missing/empty (pathological input).
    """
    classname = testcase.attrib.get("classname", "").strip()
    if classname:
        return classname
    if fallback_suite_name and fallback_suite_name != "unknown":
        return fallback_suite_name
    return "unknown"


def parse_junit(path: Path) -> TestJSON:
    """Parse a ctest JUnit XML file into a :class:`TestJSON` document.

    Args:
        path: Path to the JUnit XML file (typically produced by
            ``ctest --output-junit``).

    Returns:
        Fully populated :class:`TestJSON`.

    Raises:
        ValidationError: If ``path`` does not exist or the XML is malformed.
    """
    if not path.exists():
        raise ValidationError(f"JUnit XML file not found: {path}")
    try:
        # Trusted local input — see module docstring "XXE / entity expansion
        # risk" section for rationale on not using defusedxml here.
        tree = ET.parse(path)  # noqa: S314
    except ET.ParseError as exc:
        raise ValidationError(f"invalid JUnit XML in {path}: {exc}") from exc
    root = tree.getroot()
    # ctest emits <testsuites> at root; tolerate a single-<testsuite> root too.
    suites: list[ET.Element] = (
        list(root.findall("testsuite")) if root.tag == "testsuites" else [root]
    )
    modules: list[TestModule] = []
    any_failed = False
    for suite in suites:
        module_id = suite.attrib.get("name", "unknown")
        entries: list[TestEntry] = []
        for tc in suite.findall("testcase"):
            classname = _resolve_classname(tc, module_id)
            name = tc.attrib.get("name", "unknown")
            full_name = f"{classname}.{name}" if classname else name
            state = _state_for(tc)
            if state == "failed":
                any_failed = True
            entries.append(
                TestEntry(
                    name=full_name,
                    full_name=f"{module_id}::{full_name}",
                    state=state,
                    errors=_collect_errors(tc),
                )
            )
        modules.append(TestModule(module_id=module_id, tests=tuple(entries)))
    reason = "failed" if any_failed else "passed"
    return TestJSON(test_modules=tuple(modules), reason=reason)


def run(junit_path: Path, target: Path) -> int:
    """Parse JUnit XML at ``junit_path`` and write test.json at ``target``.

    Returns:
        0 on success. Non-zero reserved for future error paths; currently
        every failure raises :class:`ValidationError` which the caller
        (verification runner) catches.
    """
    doc = parse_junit(junit_path)
    write_test_json(doc, target)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point when invoked as a standalone script.

    Usage: ``python ctest_reporter.py <junit.xml> <test.json>``
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        sys.stderr.write(
            "usage: ctest_reporter.py <junit.xml> <test.json>\n"
        )
        return 1
    return run(Path(args[0]), Path(args[1]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reporters_ctest.py -v`
Expected: PASS — 8 tests (6 original + 2 new classname-fallback coverage
added per MAGI Checkpoint 2 iter 1 WARNING — melchior).

- [x] **Step 5: Commit**

```bash
git add skills/sbtdd/scripts/reporters/ctest_reporter.py tests/test_reporters_ctest.py tests/fixtures/ctest-junit/
git commit -m "test: add ctest_reporter JUnit XML parser to TDD-Guard JSON"
```

---

### Task 18: `reporters/ctest_reporter.py` — skipped tests + large-suite coverage

**Files:**
- Modify: `tests/test_reporters_ctest.py`
- Create: `tests/fixtures/ctest-junit/with_skipped.xml`

**Task classification (MAGI Checkpoint 2 iter 1 WARNING — caspar):** this is
a **coverage-extension** task, not a strict Red→Green TDD cycle. The
existing `parse_junit` already handles `<skipped>` children and multiple
suites — this task adds explicit fixtures + assertions that document and
lock those behaviors against regression. The `test:` commit prefix is
appropriate per the "Commit prefix policy" section of this plan (row 1 of
sec.M.5 covers test additions on already-green code). The Step 1 test for
`run` returning `0` is intentionally a contract-lock assertion (not a
discriminating red test); it catches a silent contract change if the
return code semantics ever drift from "0 on success".

- [x] **Step 1: Write failing-or-locking test (coverage extension)**

```python
# tests/test_reporters_ctest.py (append)
def test_parse_junit_skipped_recorded_as_skipped_state():
    """Red/lock test: <skipped> child must produce state='skipped'.

    If ctest_reporter._state_for() ever regressed to returning 'passed' for
    <skipped>, this assertion would fail. This is the discriminating coverage
    for the skipped-state branch.
    """
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "with_skipped.xml")
    all_tests = {t.name: t for m in doc.test_modules for t in m.tests}
    assert all_tests["Slow.Ignored"].state == "skipped"
    # A skipped-only run with no failures is still "passed" by TDD-Guard semantics.
    assert doc.reason == "passed"


def test_parse_junit_multiple_suites_preserve_boundaries():
    """Red/lock test: each <testsuite> becomes its own TestModule.

    Locks the one-suite-per-module mapping. A regression that flattened all
    testcases into a single module would fail this assertion.
    """
    from reporters.ctest_reporter import parse_junit
    doc = parse_junit(FIXTURES / "with_skipped.xml")
    module_ids = [m.module_id for m in doc.test_modules]
    # The fixture has two <testsuite>s.
    assert len(module_ids) == 2
    assert len(set(module_ids)) == 2


def test_run_returns_zero_on_success_contract_lock(tmp_path):
    """Contract-lock: run() returns exit-code 0 on successful write.

    Deliberately tautological vs current implementation — guards against a
    silent contract change (e.g. returning the internal parser's 'reason'
    string instead of 0). Per Plan B "Deferred from MAGI Checkpoint 2",
    rewording to a more discriminating assertion is deferred to Milestone C
    when verification_commands wiring gives us a richer signal.
    """
    from reporters.ctest_reporter import run
    dst = tmp_path / "test.json"
    assert run(FIXTURES / "all_passed.xml", dst) == 0
    # Locking also: the destination file must exist and parse as JSON.
    assert dst.exists()
    json.loads(dst.read_text(encoding="utf-8"))  # raises if malformed
```

Create fixture `tests/fixtures/ctest-junit/with_skipped.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites>
  <testsuite name="FastSuite" tests="1" failures="0" errors="0">
    <testcase classname="Fast" name="Ok" time="0.00"/>
  </testsuite>
  <testsuite name="SlowSuite" tests="1" failures="0" errors="0">
    <testcase classname="Slow" name="Ignored" time="0.00">
      <skipped message="disabled in config"/>
    </testcase>
  </testsuite>
</testsuites>
```

- [x] **Step 2: Run tests — coverage additions over existing ctest_reporter**

Run: `python -m pytest tests/test_reporters_ctest.py -v`
Expected: PASS — 11 tests (8 after Task 17 classname-fallback additions +
3 new). The new tests pass first-run because the implementation already
handles `<skipped>` children and multiple suites; this task extends
coverage per sec.M.5 row 1 (test: prefix for test additions regardless of
first-run pass/fail). Classified as coverage-extension per the rationale
at the top of this task.

- [x] **Step 3: (no new impl needed — see classification note)**

- [x] **Step 4: Verify all tests pass**

Run: `python -m pytest tests/test_reporters_ctest.py -v`
Expected: PASS — 11 tests.

- [x] **Step 5: Commit**

```bash
git add tests/test_reporters_ctest.py tests/fixtures/ctest-junit/with_skipped.xml
git commit -m "test: add skipped and multi-suite coverage for ctest_reporter"
```

---

## Phase 4: Templates (Tasks 19-24 — 6 template files consumed by init_cmd in Milestone C)

### Task 19: `templates/settings.json.template` — 3 TDD-Guard hooks

**Files:**
- Create: `templates/settings.json.template`
- Create: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py
from __future__ import annotations

import json
from pathlib import Path
import pytest

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def test_settings_json_template_exists():
    assert (TEMPLATES_DIR / "settings.json.template").exists()


def test_settings_json_template_is_valid_json():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_settings_json_template_has_three_required_hooks():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    assert set(hooks.keys()) == {"PreToolUse", "UserPromptSubmit", "SessionStart"}


def test_settings_json_template_pretool_has_write_matcher():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    pretool = data["hooks"]["PreToolUse"]
    assert len(pretool) >= 1
    entry = pretool[0]
    assert entry["matcher"] == "Write|Edit|MultiEdit|TodoWrite"
    assert entry["hooks"][0]["command"] == "tdd-guard"


def test_settings_json_template_session_start_has_startup_matcher():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    session = data["hooks"]["SessionStart"]
    assert session[0]["matcher"] == "startup|resume|clear"
    assert session[0]["hooks"][0]["command"] == "tdd-guard"


def test_settings_json_template_user_prompt_has_tdd_guard():
    data = json.loads((TEMPLATES_DIR / "settings.json.template").read_text(encoding="utf-8"))
    ups = data["hooks"]["UserPromptSubmit"]
    assert ups[0]["hooks"][0]["command"] == "tdd-guard"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL con `FileNotFoundError` or `AssertionError: file does not exist`.

- [x] **Step 3: Write minimal implementation**

Create `templates/settings.json.template`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|TodoWrite",
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ],
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [{ "type": "command", "command": "tdd-guard" }]
      }
    ]
  }
}
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: PASS — 6 tests.

- [x] **Step 5: Commit**

```bash
git add templates/settings.json.template tests/test_templates_files.py
git commit -m "test: add settings.json.template with 3 TDD-Guard hooks"
```

---

### Task 20: `templates/plugin.local.md.template` — YAML frontmatter schema

**Files:**
- Create: `templates/plugin.local.md.template`
- Modify: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py (append)
def test_plugin_local_template_exists():
    assert (TEMPLATES_DIR / "plugin.local.md.template").exists()


def test_plugin_local_template_loads_as_plugin_config():
    """After placeholder expansion, the file must parse via config.load_plugin_local."""
    from config import load_plugin_local
    from templates import expand
    raw = (TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    context = {
        "stack": "python",
        "author": "Test Author",
        "error_type": "null",
    }
    expanded = expand(raw, context)
    import tempfile
    from pathlib import Path as _P
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fp:
        fp.write(expanded)
        tmp = _P(fp.name)
    try:
        cfg = load_plugin_local(tmp)
        assert cfg.stack == "python"
        assert cfg.author == "Test Author"
        assert cfg.magi_threshold == "GO_WITH_CAVEATS"
        assert cfg.magi_max_iterations == 3
        assert cfg.auto_magi_max_iterations >= cfg.magi_max_iterations
    finally:
        tmp.unlink()


def test_plugin_local_template_has_all_required_keys():
    raw = (TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    required = [
        "stack:",
        "author:",
        "error_type:",
        "verification_commands:",
        "plan_path:",
        "plan_org_path:",
        "spec_base_path:",
        "spec_path:",
        "state_file_path:",
        "magi_threshold:",
        "magi_max_iterations:",
        "auto_magi_max_iterations:",
        "auto_verification_retries:",
        "tdd_guard_enabled:",
        "worktree_policy:",
    ]
    for key in required:
        assert key in raw, f"plugin.local.md.template missing key {key}"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL — template file missing.

- [x] **Step 3: Write minimal implementation**

Create `templates/plugin.local.md.template`:

```markdown
---
stack: {stack}
author: "{author}"
error_type: {error_type}
verification_commands:
  - "pytest"
  - "ruff check ."
  - "ruff format --check ."
  - "mypy ."
plan_path: "planning/claude-plan-tdd.md"
plan_org_path: "planning/claude-plan-tdd-org.md"
spec_base_path: "sbtdd/spec-behavior-base.md"
spec_path: "sbtdd/spec-behavior.md"
state_file_path: ".claude/session-state.json"
magi_threshold: "GO_WITH_CAVEATS"
magi_max_iterations: 3
auto_magi_max_iterations: 5
auto_verification_retries: 1
tdd_guard_enabled: true
worktree_policy: "optional"
---

# Local configuration for the sbtdd-workflow plugin

Generated by `/sbtdd init`. Edit manually if the stack or toolchain changes.
Not committed to git (covered by `.claude/` gitignore).

`verification_commands` above is the Python-stack default. For Rust or C++,
init regenerates this block at setup time; see `sbtdd-workflow-plugin-spec.md`
sec.S.4.2 for the stack-specific variants.
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: PASS — 9 tests.

- [x] **Step 5: Commit**

```bash
git add templates/plugin.local.md.template tests/test_templates_files.py
git commit -m "test: add plugin.local.md.template with default YAML frontmatter"
```

---

### Task 21: `templates/CLAUDE.local.md.template` — parameterized project rules

**Files:**
- Create: `templates/CLAUDE.local.md.template`
- Modify: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py (append)
def test_claude_local_template_exists():
    assert (TEMPLATES_DIR / "CLAUDE.local.md.template").exists()


def test_claude_local_template_placeholders_present():
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    for placeholder in ("{Author}", "{ErrorType}", "{stack}"):
        assert placeholder in raw, f"placeholder {placeholder} missing from CLAUDE.local.md.template"


def test_claude_local_template_expands_without_residual_placeholders():
    from templates import expand
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    out = expand(raw, {
        "Author": "Julian Bolivar",
        "ErrorType": "MyErr",
        "stack": "python",
        "verification_commands": "pytest / ruff / mypy",
    })
    assert "{Author}" not in out
    assert "{ErrorType}" not in out
    assert "{stack}" not in out
    assert "Julian Bolivar" in out


def test_claude_local_template_contains_no_uppercase_markers():
    """INV-27 spec placeholder rejection applies to templates as well."""
    import re
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    assert not re.search(r"\bTODO\b", raw)
    assert not re.search(r"\bTODOS\b", raw)
    assert not re.search(r"\bTBD\b", raw)


def test_claude_local_template_references_verification_section():
    raw = (TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    # Must reference the verification commands section (sec.0.1 in destination).
    assert "0.1" in raw or "verification" in raw.lower()
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL — template missing.

- [x] **Step 3: Write minimal implementation**

Create `templates/CLAUDE.local.md.template`:

```markdown
# CLAUDE.local.md — Project rules (stack: {stack})

> Local project rules. Not tracked by git. Maintained by the developer; the
> plugin reads and enforces but never edits this file.
> Global standards in `~/.claude/CLAUDE.md` always take precedence (INV-0).

---

## 0. Mandatory Code Standards

Read `~/.claude/CLAUDE.md` before writing any code. It is authoritative.

### 0.1 Verification after each TDD phase

Run these after closing each Red, Green, or Refactor phase
({stack} stack):

{verification_commands}

### 0.2 Project-specific rules

| Area | Rule |
|------|------|
| Author header | Every `.py` file starts with `# Author: {Author}`, `# Version: 1.0.0`, `# Date: YYYY-MM-DD` |
| Error type | `{ErrorType}` is the project's root error type |
| Stack | `{stack}` |
| Line length | 100 |

---

## 1. Methodology

SBTDD (Spec + Behavior + Test Driven Development). Read the plugin spec at
`sbtdd/sbtdd-workflow-plugin-spec.md` for the full flow. Key docs:

- `sbtdd/spec-behavior-base.md` — input to `/brainstorming`
- `sbtdd/spec-behavior.md` — output of `/brainstorming`, input to `/writing-plans`
- `planning/claude-plan-tdd-org.md` — raw plan (pre-MAGI)
- `planning/claude-plan-tdd.md` — approved plan (post-MAGI Checkpoint 2)

`/sbtdd init` has already bootstrapped the project. Use `/sbtdd spec` to
start a feature, then `/sbtdd close-phase` after each Red/Green/Refactor,
`/sbtdd close-task` at Refactor close, `/sbtdd pre-merge` when all tasks are
complete, and `/sbtdd finalize` to wrap the branch.

---

## 2. Artefactos y fuentes de estado

Three runtime state sources (sec.M.2 of the spec):

1. `.claude/session-state.json` — canon del presente (TDD phase + task).
2. Git commits — canon del pasado.
3. `planning/claude-plan-tdd.md` — canon del futuro (checkboxes).

On drift the plugin aborts with exit 3 (sec.S.9.2). Do not reconcile
silently.

---

## 3. Ciclo TDD

Red -> Green -> Refactor, enforced by TDD-Guard hooks (installed by
`/sbtdd init`) plus `/test-driven-development`. Close phases via
`/sbtdd close-phase` which runs verification (sec.0.1) then creates an
atomic commit with the sec.M.5 prefix.

---

## 5. Git

Follow `~/.claude/CLAUDE.md` Git section. Commits use the prefix map:

| Context | Prefix |
|---------|--------|
| Red close | `test:` |
| Green close | `feat:` or `fix:` |
| Refactor close | `refactor:` |
| Task close | `chore:` |

Under an approved plan (`plan_approved_at` non-null in the state file) the
plugin commits autonomously for the four authorised categories. Outside
that window, commits require explicit user permission.
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: PASS — 14 tests.

- [x] **Step 5: Commit**

```bash
git add templates/CLAUDE.local.md.template tests/test_templates_files.py
git commit -m "test: add CLAUDE.local.md.template with Author/ErrorType/stack placeholders"
```

---

### Task 22: `templates/spec-behavior-base.md.template` — SBTDD spec skeleton

**Files:**
- Create: `templates/spec-behavior-base.md.template`
- Modify: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py (append)
def test_spec_behavior_base_template_exists():
    assert (TEMPLATES_DIR / "spec-behavior-base.md.template").exists()


def test_spec_behavior_base_template_no_uppercase_markers():
    """INV-27: spec-behavior-base.md.template must not contain the three pending-marker words."""
    import re
    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    assert not re.search(r"\bTODO\b", raw)
    assert not re.search(r"\bTODOS\b", raw)
    assert not re.search(r"\bTBD\b", raw)


def test_spec_behavior_base_template_has_replace_markers():
    """Skeleton uses <REPLACE: ...> markers (not the uppercase pending words) to indicate user edits."""
    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    assert "<REPLACE:" in raw


def test_spec_behavior_base_template_has_sbtdd_sections():
    raw = (TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
    for section in ("Objetivo", "Requerimientos", "Escenarios", "Restricciones"):
        assert section in raw, f"section '{section}' missing from spec template"
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL — template missing.

- [x] **Step 3: Write minimal implementation**

Create `templates/spec-behavior-base.md.template`:

```markdown
# Especificacion de comportamiento — feature: <REPLACE: feature name>

> Base pre-brainstorming. Input to `/brainstorming`. Edit every <REPLACE:...>
> marker with the actual content before running `/sbtdd spec`. The plugin
> rejects this file with exit 2 if any of the three uppercase pending-marker
> words remain (INV-27); use the `<REPLACE:...>` placeholder form while
> drafting.

---

## 1. Objetivo

<REPLACE: one sentence — what this feature achieves for the user>

---

## 2. Requerimientos SDD

### Requerimientos funcionales (F)

F1. <REPLACE: first functional requirement>
F2. <REPLACE: second functional requirement>

### Requerimientos no-funcionales (NF)

NF1. <REPLACE: performance / reliability / portability goal>

---

## 3. Restricciones y constraints duros

- <REPLACE: hard constraint 1>
- <REPLACE: hard constraint 2>

---

## 4. Escenarios BDD (Given / When / Then)

### Escenario 1: <REPLACE: scenario name>

> **Given:** <REPLACE: pre-condition>
> **When:** <REPLACE: action>
> **Then:** <REPLACE: observable outcome>

### Escenario 2: <REPLACE: scenario name>

> **Given:** <REPLACE: pre-condition>
> **When:** <REPLACE: action>
> **Then:** <REPLACE: observable outcome>

---

## 5. Scope exclusions

- <REPLACE: out-of-scope item 1>
- <REPLACE: out-of-scope item 2>

---

## 6. Criterios de aceptacion finales

- <REPLACE: measurable criterion 1>
- <REPLACE: measurable criterion 2>
```

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: PASS — 18 tests.

- [x] **Step 5: Commit**

```bash
git add templates/spec-behavior-base.md.template tests/test_templates_files.py
git commit -m "test: add spec-behavior-base template with REPLACE placeholders"
```

---

### Task 23: `templates/conftest.py.template` — pytest reporter block

**Files:**
- Create: `templates/conftest.py.template`
- Modify: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py (append)
def test_conftest_template_exists():
    assert (TEMPLATES_DIR / "conftest.py.template").exists()


def test_conftest_template_has_sbtdd_markers():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert "# --- SBTDD TDD-Guard reporter START ---" in raw
    assert "# --- SBTDD TDD-Guard reporter END ---" in raw


def test_conftest_template_has_required_pytest_hooks():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    for hook in (
        "pytest_sessionstart",
        "pytest_sessionfinish",
        "pytest_runtest_makereport",
    ):
        assert hook in raw


def test_conftest_template_writes_to_expected_test_json_path():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert ".claude/tdd-guard/data/test.json" in raw or (
        ".claude" in raw and "tdd-guard" in raw and "test.json" in raw
    )


def test_conftest_template_is_valid_python(tmp_path):
    import ast
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    # Must parse cleanly as Python — no placeholders that break syntax.
    ast.parse(raw)


def test_conftest_template_has_author_header():
    raw = (TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    assert "# Author:" in raw
    assert "# Version:" in raw
    assert "# Date:" in raw
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL — template missing.

- [x] **Step 3: Write minimal implementation**

Create `templates/conftest.py.template`:

```python
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Pytest reporter for TDD-Guard (installed by /sbtdd init --stack python)."""

# --- SBTDD TDD-Guard reporter START ---
import json
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent
_DATA_DIR = _PROJECT_ROOT / ".claude" / "tdd-guard" / "data"
_TEST_RESULTS_FILE = _DATA_DIR / "test.json"


def pytest_sessionstart(session):
    """Ensure the tdd-guard data directory exists before tests run."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """Write test results to tdd-guard's expected JSON format."""
    modules = {}
    for item in session.items:
        module_id = item.nodeid.split("::")[0]
        report = getattr(item, "_tdd_guard_report", None)
        state = "skipped"
        errors = []
        if report is not None:
            if report.passed:
                state = "passed"
            elif report.failed:
                state = "failed"
                if report.longrepr:
                    errors.append({
                        "message": str(report.longrepr).split("\n")[-1],
                        "stack": str(report.longrepr),
                    })
            elif report.skipped:
                state = "skipped"
        entry = {
            "name": item.name,
            "fullName": item.nodeid,
            "state": state,
        }
        if errors:
            entry["errors"] = errors
        modules.setdefault(module_id, []).append(entry)

    reason = "passed"
    if exitstatus == pytest.ExitCode.INTERRUPTED:
        reason = "interrupted"
    elif exitstatus != pytest.ExitCode.OK:
        reason = "failed"

    result = {
        "testModules": [
            {"moduleId": mid, "tests": tests}
            for mid, tests in modules.items()
        ],
        "reason": reason,
    }
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _TEST_RESULTS_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Capture the call-phase report for each test."""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item._tdd_guard_report = report

# --- SBTDD TDD-Guard reporter END ---
```

**Addendum (Fix 5 — MAGI ckpt2 iter 2 caspar):** same commit also appends
the test-isolation policy comment at the top of the existing repo-root
`conftest.py` (the comment text is documented verbatim in the "Test
isolation policy" section earlier in this plan). The comment replaces the
dropped `tests/test_monkeypatch_isolation.py` meta-test. Both changes land
together so the policy statement is visible in the same atomic unit.

- [x] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: PASS — 24 tests.

- [x] **Step 5: Commit**

```bash
git add templates/conftest.py.template conftest.py tests/test_templates_files.py
git commit -m "test: add conftest.py.template with SBTDD block delimiters"
```

---

### Task 24: `templates/gitignore.fragment` + full `make verify`

**Files:**
- Create: `templates/gitignore.fragment`
- Modify: `tests/test_templates_files.py`

- [x] **Step 1: Write failing test**

```python
# tests/test_templates_files.py (append)
def test_gitignore_fragment_exists():
    assert (TEMPLATES_DIR / "gitignore.fragment").exists()


def test_gitignore_fragment_contains_required_entries():
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    required = [
        ".claude/",
        "CLAUDE.local.md",
    ]
    for entry in required:
        assert entry in raw, f".gitignore fragment missing {entry}"


def test_gitignore_fragment_ends_with_newline():
    """Fragment should end with newline so append concatenation doesn't join lines."""
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    assert raw.endswith("\n")


def test_gitignore_fragment_has_header_comment():
    raw = (TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    # A comment identifies the fragment so a reader knows where the entries came from.
    assert "SBTDD" in raw or "sbtdd" in raw
```

- [x] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_templates_files.py -v`
Expected: FAIL — fragment missing.

- [x] **Step 3: Write minimal implementation**

Create `templates/gitignore.fragment`:

```
# --- SBTDD-workflow appended by /sbtdd init ---
.claude/
CLAUDE.local.md
CLAUDE.md
sbtdd/spec-behavior.md
# --- end SBTDD-workflow ---
```

- [x] **Step 4: Run full `make verify`**

Run:

```bash
python -m pytest tests/ -v
python -m ruff check .
python -m ruff format --check .
python -m mypy .
```

Expected: all four pass cleanly. Full test count at end of Milestone B
should be roughly 113 (Milestone A) + ~34 (Milestone B, including MAGI
Checkpoint 2 iter-2 fixes: +3 for Task 4a claude-CLI, +2 for rust_reporter
Fix 4/8, +1 for test_superpowers_dispatch_integration.py Fix 6; net vs the
dropped meta-test file) = ~147 tests across ~18 test files (test_monkeypatch_isolation.py
dropped; test_superpowers_dispatch_integration.py added).

- [x] **Step 5: Commit**

```bash
git add templates/gitignore.fragment tests/test_templates_files.py
git commit -m "test: add gitignore.fragment template with SBTDD entries"
```

---

## Milestone B — Acceptance

Tras completar las 25 tareas (Tasks 1-24 + Task 4a):

- **4 modulos Python** nuevos bajo `skills/sbtdd/scripts/`: `dependency_check.py`, `run_sbtdd.py`, `superpowers_dispatch.py`, `magi_dispatch.py`.
- **3 reporters** bajo `skills/sbtdd/scripts/reporters/`: `tdd_guard_schema.py`, `rust_reporter.py`, `ctest_reporter.py`.
- **6 template files** bajo `templates/`: `settings.json.template`, `plugin.local.md.template`, `CLAUDE.local.md.template`, `spec-behavior-base.md.template`, `conftest.py.template`, `gitignore.fragment`.
- **9 test files** bajo `tests/`: `test_dependency_check.py`, `test_run_sbtdd.py`, `test_superpowers_dispatch.py`, `test_superpowers_dispatch_integration.py` (skipif-guarded claude-CLI integration test; MAGI Checkpoint 2 iter 2 WARNING — caspar), `test_magi_dispatch.py`, `test_reporters_schema.py`, `test_reporters_rust.py`, `test_reporters_ctest.py`, `test_templates_files.py`.
- **3 fixture directories** bajo `tests/fixtures/`: `magi-outputs/` (4 JSON files), `ctest-junit/` (6 XML files: `all_passed`, `mixed`, `empty`, `with_skipped`, `missing_classname`, `classname_and_suite_empty`), `conftest-merge/` (for Task 23).
- `make verify` limpio: pytest + ruff check + ruff format --check + mypy (strict).
- **25 commits atomicos** con prefijos sec.M.5 (todos `test:` — see "Commit prefix policy" section of this plan documenting the Milestone A precedent for fresh-module scaffolding; ningun `refactor:` porque no hay behavior-preserving cleanup, ningun `chore:` porque no hay bookkeeping separado del ciclo TDD, ningun `fix:` porque no hay bugs preexistentes).
- **Automated claude-CLI integration test (MAGI ckpt2 iter 2 WARNING — caspar; supersedes the iter-1 manual smoke test acceptance item):** the file `tests/test_superpowers_dispatch_integration.py` (added as part of Task 9, see Task 9 Step 1 additions below) runs a cheap `claude --version` (or `claude -p /brainstorming --help`) invocation guarded by `@pytest.mark.skipif(shutil.which("claude") is None, reason="claude CLI not installed")`. Exit 0 + non-empty stdout required. The test is skipped (not failed) in environments without the CLI, so CI and local runs both remain clean. This replaces the earlier untrackable "manual smoke test" acceptance item.

Productos habilitados para Milestone C:
- `dependency_check.check_environment` -> consumido por `init_cmd.py` Fase 1 y `auto_cmd.py` Fase 1.
- `run_sbtdd.SUBCOMMAND_DISPATCH` -> 9 entries placeholder que Milestone C reemplaza con `{subcommand}_cmd.run`.
- `superpowers_dispatch.{brainstorming, writing_plans, ...}` -> invocados por `spec_cmd`, `pre_merge_cmd`, `auto_cmd`, `finalize_cmd`.
- `magi_dispatch.{invoke_magi, verdict_passes_gate, verdict_is_strong_no_go, write_verdict_artifact}` -> usados por `spec_cmd` (Checkpoint 2) y `pre_merge_cmd` (Loop 2).
- `reporters.tdd_guard_schema.{TestJSON, write_test_json}` -> referencia canonica del schema TDD-Guard.
- `reporters.rust_reporter.run_pipeline` -> invocado por `verification_commands[0]` en stack Rust.
- `reporters.ctest_reporter.run` -> invocado por `verification_commands[1]` en stack C++.
- `templates/*.template` + `templates/gitignore.fragment` -> consumidos por `init_cmd.py` Fase 3 via `templates.expand` y `hooks_installer.merge`.

No implementados en Milestone B (para milestones C-E):
- Los 9 `*_cmd.py` subcomandos (init, spec, close-phase, close-task, status, pre-merge, finalize, auto, resume).
- `skills/sbtdd/SKILL.md`.
- `.claude-plugin/plugin.json` + `marketplace.json`.
- `README.md`.

---

## Self-Review

**1. Spec coverage (`spec-behavior.md` sec.4 Escenarios BDD):**

Milestone B is the integration scaffolding layer. Its tests do not directly
exercise scenarios 11-19 (those require the `*_cmd.py` subcommands from
Milestone C+), but it produces every module/template those scenarios depend
on:

- **Escenario 11** (`/sbtdd init` happy path Rust) -> enabled by Tasks 1-6
  (dependency_check.check_environment), Task 7 (run_sbtdd dispatch),
  Tasks 19-24 (6 templates).
- **Escenario 12** (`/sbtdd spec` MAGI loop) -> enabled by Tasks 10-13
  (MAGIVerdict + invoke_magi + verdict_passes_gate + write_verdict_artifact),
  Task 22 (spec-behavior-base template).
- **Escenario 13** (`/sbtdd close-phase` cycle) -> relies on Milestone A's
  `commits.create` + `state_file.save`; no new Milestone B modules required.
- **Escenario 14** (`/sbtdd close-task`) -> same as 13.
- **Escenario 15** (`/sbtdd status` drift detection) -> relies on Milestone A's
  `drift.detect_drift`; run_sbtdd dispatcher (Task 7) adds the CLI entry.
- **Escenario 16** (`/sbtdd pre-merge` Loop 1+2) -> enabled by Tasks 8-9
  (superpowers `requesting_code_review` + `receiving_code_review`), Tasks 10-13
  (magi_dispatch).
- **Escenario 17** (`/sbtdd finalize` checklist) -> enabled by Task 13
  (write_verdict_artifact is the file `finalize` reads).
- **Escenario 18** (`/sbtdd auto` full cycle) -> enabled by every module in
  this milestone (auto orchestrates the full toolchain).
- **Escenario 19** (`/sbtdd resume`) -> enabled by Task 7 (dispatcher
  returning structured exit codes) + state_file (Milestone A).

**2. INV coverage:**

| INV | Addressed by |
|-----|--------------|
| INV-0 (global authority) | Documented in CLAUDE.local.md template (Task 21); commits.py already enforces (Milestone A) |
| INV-11 (safety valves) | magi_dispatch returns MAGIVerdict; threshold + iteration logic lives in Milestone C subcomandos, but this milestone provides the typed primitives |
| INV-16 (evidence before assertions) | reporters write test.json canonically so verification can cite literal output |
| INV-19-21 (Python 3.9+, cross-platform, stdlib-only on hot paths) | No new runtime deps; dependency_check, run_sbtdd, superpowers_dispatch, magi_dispatch, reporters all stdlib + PyYAML (already in Milestone A dev deps, used only by config.py) |
| INV-27 (spec-base limpia) | Task 22 test enforces no the three pending-marker words in the template itself |
| INV-28 (MAGI degraded) | Task 12 test coverage: `verdict_passes_gate` rejects all degraded verdicts regardless of label; `verdict_is_strong_no_go` still returns True for degraded STRONG_NO_GO |
| INV-29 (receiving-code-review gate) | Skill wrapper `receiving_code_review` exposed by Task 9; actual feedback loop logic lives in Milestone C pre_merge_cmd |

**3. Commit prefix audit (sec.M.5):**

- All 25 tasks (Tasks 1-24 + Task 4a) commit with `test:` prefix — each task follows Red-Green with
  tests first (or adds test coverage atop an already-passing implementation
  per sec.M.5 row 1). Detailed rationale is in the "Commit prefix policy"
  section earlier in this plan, added in response to MAGI Checkpoint 2
  iter 1 WARNING (balthasar). The policy documents the Milestone A precedent
  (Tasks 2-7 of Plan A used the same pattern and passed MAGI 3-0 full GO).
  No `refactor:`, `fix:`, or `chore:` commits because:
  - No bug fixes (fresh code).
  - No behavior-preserving cleanup (green implementations go straight to
    passing; polish belongs in future refactor commits).
  - No bookkeeping separate from the TDD cycle (template files are shipped
    alongside their tests).

**4. Placeholder scan:** grep por los tres marcadores uppercase + "fill in" /
"implement later" — ninguno encontrado como token pending. `<REPLACE: ...>`
en `spec-behavior-base.md.template` (Task 22) es el marcador intencional
que reemplaza el uppercase pending prohibido por INV-27.

**5. Type / name consistency:** nombres usados consistentemente:

- `DependencyCheck`, `DependencyReport`, `VALID_STATUSES`, `SUPERPOWERS_SKILLS`,
  `check_environment`, `check_python`, `check_git`, `check_tdd_guard_binary`,
  `check_tdd_guard_data_dir`, `check_superpowers`, `check_magi`,
  `check_stack_toolchain`, `check_working_tree` (dependency_check.py).
- `SUBCOMMAND_DISPATCH`, `SubcommandHandler`, `_default_handler_factory`,
  `main`, `_exit_code_for` (run_sbtdd.py).
- `SkillResult`, `invoke_skill`, `brainstorming`, `writing_plans`,
  `test_driven_development`, `verification_before_completion`,
  `requesting_code_review`, `receiving_code_review`, `executing_plans`,
  `subagent_driven_development`, `dispatching_parallel_agents`,
  `systematic_debugging`, `using_git_worktrees`,
  `finishing_a_development_branch` (superpowers_dispatch.py).
- `MAGIVerdict`, `parse_verdict`, `invoke_magi`, `verdict_passes_gate`,
  `verdict_is_strong_no_go`, `write_verdict_artifact`,
  `_normalise_verdict_label` (magi_dispatch.py).
- `TestError`, `TestEntry`, `TestModule`, `TestJSON`, `VALID_STATES`,
  `VALID_REASONS`, `write_test_json` (reporters/tdd_guard_schema.py).
- `run_pipeline`, `main` (reporters/rust_reporter.py).
- `parse_junit`, `run`, `main` (reporters/ctest_reporter.py).

**6. Consistency with Milestone A:**

- Exit codes: every `*_cmd.py` in Milestone C will propagate `SBTDDError`
  subclasses; `run_sbtdd.main` (Task 7) catches them and looks up
  `errors.EXIT_CODES`. Adding a new exception in Milestone C only requires
  updating `errors.py` — the dispatcher needs no change.
- Subprocess policy: every external call in this milestone routes through
  `subprocess_utils.run_with_timeout` (or `subprocess.Popen` with `shell=False`
  for `rust_reporter`'s pipeline — a deliberate exception because stdout/
  stdin must be wired between two processes which `run_with_timeout` does not
  expose; tested explicitly that `shell=False` is preserved).
- Atomicity: every new writer (`write_verdict_artifact`, `write_test_json`)
  mirrors `state_file.save` and `hooks_installer.merge` — tmp file +
  `os.replace` + unlink-on-error.

**7. MAGI Checkpoint 2 readiness:** plan is concrete (no uppercase pending
markers; all Python code blocks contain the actual implementation), task
granularity is bite-sized (2-5 min each), and scope aligns with the
declared Milestone B boundaries.

---

## Execution Handoff

Plan saved to `planning/claude-plan-tdd-org-B.md` (pre-MAGI original).
Checkpoint 2 (MAGI) runs next. Post-approval plan is saved to
`planning/claude-plan-tdd-B.md` with any required adjustments applied.

Dos execution options post-aprobacion:

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task,
review between tasks, fast iteration. Milestone B is linear so this maps
cleanly.

**2. Inline Execution** — execute tasks in-session with `/executing-plans`.

Post-Milestone B, the three remaining milestones are:

- **Milestone C** — `init_cmd.py`, `spec_cmd.py`, `close_phase_cmd.py`,
  `close_task_cmd.py`, `status_cmd.py`. Replaces five entries in
  `run_sbtdd.SUBCOMMAND_DISPATCH`.
- **Milestone D** — `pre_merge_cmd.py`, `finalize_cmd.py`, `auto_cmd.py`,
  `resume_cmd.py`. Replaces the remaining four entries.
- **Milestone E** — `skills/sbtdd/SKILL.md`, `.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, `README.md`.



