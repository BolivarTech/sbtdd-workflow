# v1.0.4 Real Headless Detection + Parallel Dispatcher + Close-phase Mandate Implementation Plan

> Generado 2026-05-07 a partir de sbtdd/spec-behavior.md v1.0.4 via
> superpowers:writing-plans skill (interactive session, brainstorming
> Q1+Q2+Q3+Q4+Q5 resolved). Frontmatter required by spec_lint R5
> (Item C v1.0.2 enforcement).
>
> v1.0.4 ships 3 pillars: Pillar A (Items A+B coupled real headless
> detection + 600s LOUD-FAST fix); Pillar B (Item C parallel task
> dispatcher with --parallel flag); Pillar C (Item D doc-only
> per-phase close-phase mandate).
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax (open + closed bracket forms) for tracking.

**Goal:** Ship v1.0.4 — eliminate `/receiving-code-review` interactive subprocess hang via real headless detection (env var + isatty + override) coupled with 600s LOUD-FAST PreconditionError fix; codify multi-track parallel subagent pattern as plugin feature via `--parallel` flag on `/sbtdd auto`; mandate per-phase close-phase commands via 3-touchpoint doc-only enforcement (SKILL.md + CLAUDE.local.md.template + writing-plans skill prompt extension). 9 plan tasks across 2 parallel subagent tracks; 4 methodology activities (Activity E'-pre + Activity D' retry + Activity E'-post + parallel dispatcher dogfood) executed by orchestrator.

**Architecture:** 2-track parallel dispatch with disjoint surfaces. Track Alpha (Items A+B coupled, 5 sequential tasks) modifies `skills/sbtdd/scripts/superpowers_dispatch.py` + extends `tests/test_superpowers_dispatch.py` + `tests/test_invoke_skill_callsites_audit.py`. Track Beta (Items C+D sequential, 4 tasks) creates `skills/sbtdd/scripts/dag_parser.py` + `skills/sbtdd/scripts/parallel_dispatcher.py` (NEW modules), modifies `skills/sbtdd/scripts/auto_cmd.py` + tests, applies Item D doc-only updates to `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template` + writing-plans skill prompt extension + smoke test. Cero file overlap. Activities mid-cycle (E'-pre before Track dispatch; D' retry + E'-post + parallel dogfood after Track close) run in orchestrator session before pre-merge gate.

**State file write serialization**: Track Alpha owns Tasks 1-5 (sequential close). Track Beta owns Tasks 6-9 (sequential close). State file `current_task_id` advances 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → done. `state_file.save()` atomic `os.replace` (existing v0.5.0 pattern) ensures no partial writes. Concurrent close-task invocations against disjoint task IDs are safe per v0.4.0+v0.5.0+v1.0.0+v1.0.2+v1.0.3 precedent.

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict, stdlib-only on hot paths. TDD-Guard active in same worktree (parallel-safe per spec sec.3 since Tracks have disjoint surfaces). Brainstorming refinements 2026-05-07: Q1 = 2-track parallel (Alpha A+B coupled, Beta C+D sequential); Q2 = Item C `--parallel` flag on `/sbtdd auto` (no new subcommand); Q3 = Item D Option B mandate close-phase per phase commit via 3-touchpoint doc-only; Q4 = Activity E' Option C both pre + post Track-close exercises; Q5 auto-resolved cap=3 HARD G1, iter-2 CRITICAL trigger pre-staged.

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-07`.
- **Phase close protocol (Q3 Option B mandate, this cycle ships it)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each Red/Green/Refactor verify-clean. Manual `git commit` per phase BYPASSES the phase-advance + state-file update + verification gate; treated as NON-CONFORMING and triggers drift detection on next `close-task`. v1.0.4 cycle is the FIRST to enforce this via plan template — own-cycle dogfood.
- **Task close protocol (Q2 Option B v1.0.2 mandate, preserved)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review` after Refactor close-phase. Use `--skip-spec-review` to bypass INV-31 spec-reviewer dispatch (~1-2 min/task overhead acceptable but not required for these infrastructure items).
- INV-37 composite-signature tripwire preserved unchanged in all paths.
- Item C v1.0.2 spec_lint gate (R1-R5) preserved unchanged.

**Commit prefix map per phase** (from `CLAUDE.local.md` §5):

| Phase | Prefix | Closer |
|-------|--------|--------|
| Red (failing test) | `test:` | `close-phase` |
| Green (impl) | `feat:` (new module/feature) or `fix:` (bug fix) | `close-phase` |
| Refactor | `refactor:` | `close-phase` |
| Task close | `chore:` (automated) | `close-task --skip-spec-review` |

---

## Track Alpha — Items A+B coupled real headless detection (Subagent #1, sequential A1 → A2 → A3 → A4 → A5)

**Owner**: Subagent #1 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Beta):
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py`
- Extend: `tests/test_superpowers_dispatch.py`
- Extend: `tests/test_invoke_skill_callsites_audit.py`

**Wall-time estimated**: ~1 day.

### Task 1: Item A.1 — `_is_headless_context` helper + escenarios A-2 + A-3 + A-4

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (add helper after `_SUBPROCESS_INCOMPATIBLE_SKILLS` set)
- Test: `tests/test_superpowers_dispatch.py` (extend with `class TestIsHeadlessContext`)

Covers escenarios A-2, A-3, A-4 from spec sec.4.1.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestIsHeadlessContext:
    """v1.0.4 Item A escenarios A-2, A-3, A-4 — _is_headless_context detection."""

    def test_sbtdd_headless_env_var_forces_headless(self, monkeypatch):
        """A-2: SBTDD_HEADLESS=1 forces headless regardless of isatty()."""
        from superpowers_dispatch import _is_headless_context

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        # Even if isatty would return True, env var wins
        assert _is_headless_context() is True

    def test_sbtdd_headless_case_insensitive(self, monkeypatch):
        """A-2: SBTDD_HEADLESS accepts 1/true/yes case-insensitive."""
        from superpowers_dispatch import _is_headless_context

        for value in ("1", "true", "True", "TRUE", "yes", "Yes", "YES"):
            monkeypatch.setenv("SBTDD_HEADLESS", value)
            assert _is_headless_context() is True, f"value={value!r} should be headless"

    def test_sbtdd_headless_other_values_not_headless(self, monkeypatch):
        """A-2: SBTDD_HEADLESS=0/empty/garbage does NOT force headless."""
        from superpowers_dispatch import _is_headless_context

        for value in ("0", "false", "no", "", "garbage"):
            monkeypatch.setenv("SBTDD_HEADLESS", value)
            # Falls through to isatty check; default depends on stdin state
            # We patch isatty to True so the result is unambiguously False
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.isatty.return_value = True
                assert _is_headless_context() is False, f"value={value!r} should not force headless"

    def test_stdin_not_tty_triggers_headless(self, monkeypatch):
        """A-3: stdin.isatty() False AND no env override triggers headless."""
        from superpowers_dispatch import _is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        monkeypatch.delenv("SBTDD_INTERACTIVE", raising=False)
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert _is_headless_context() is True

    def test_sbtdd_interactive_overrides_isatty(self, monkeypatch):
        """A-4: SBTDD_INTERACTIVE=1 overrides stdin.isatty() False."""
        from superpowers_dispatch import _is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        monkeypatch.setenv("SBTDD_INTERACTIVE", "1")
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            assert _is_headless_context() is False

    def test_isatty_oserror_safe_default_headless(self, monkeypatch):
        """Defensive: isatty() raises OSError → safe default is headless."""
        from superpowers_dispatch import _is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        monkeypatch.delenv("SBTDD_INTERACTIVE", raising=False)
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.side_effect = OSError("not a tty")
            assert _is_headless_context() is True
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestIsHeadlessContext -v`
Expected: FAIL with `AttributeError: module 'superpowers_dispatch' has no attribute '_is_headless_context'`.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Red phase verify-clean confirms tests fail for the correct reason (missing implementation, not import error). Atomic `test:` commit landed. State file advances `current_phase: red → green`.

#### Green Phase

- [ ] **Step 4: Implement `_is_headless_context` helper**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py`. Add after `_SUBPROCESS_INCOMPATIBLE_SKILLS` definition:

```python
def _is_headless_context() -> bool:
    """Return True if SBTDD is running in a headless context.

    v1.0.4 Item A real headless detection. Replaces v1.0.1 conservative
    whitelist + override-only baseline.

    Detection signals (any one is sufficient):
    - ``SBTDD_HEADLESS`` env var is "1" / "true" / "yes" (case-insensitive)
    - ``sys.stdin.isatty()`` returns False AND ``SBTDD_INTERACTIVE`` env
      var is NOT set to "1" / "true" / "yes"

    Defensive default: if isatty() raises (e.g., closed stdin in CI), return
    True so subprocess-incompatible skills are blocked rather than allowed
    to spawn and hang.

    Returns:
        True if headless context detected, False otherwise.
    """
    headless = os.environ.get("SBTDD_HEADLESS", "").lower()
    if headless in {"1", "true", "yes"}:
        return True
    interactive = os.environ.get("SBTDD_INTERACTIVE", "").lower()
    if interactive in {"1", "true", "yes"}:
        return False
    try:
        return not sys.stdin.isatty()
    except (AttributeError, OSError):
        return True
```

Confirm `import os` and `import sys` present at top of file (likely already imported).

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestIsHeadlessContext -v`
Expected: 6/6 tests PASS.

Run: `make verify`
Expected: All checks green (pytest, ruff check, ruff format, mypy).

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Green phase verify-clean passes. Atomic `feat:` commit landed (subject: `feat: add _is_headless_context helper for v1.0.4 Item A`). State file advances `current_phase: green → refactor`.

#### Refactor Phase

- [ ] **Step 7: Refactor — extract HEADLESS_TRUTHY constant if duplicated**

If `{"1", "true", "yes"}` literal appears in another module or seems likely to (e.g., new wrappers in Task 4), extract to module-level:

```python
_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes"})


def _is_headless_context() -> bool:
    ...
    headless = os.environ.get("SBTDD_HEADLESS", "").lower()
    if headless in _TRUTHY_ENV_VALUES:
        return True
    interactive = os.environ.get("SBTDD_INTERACTIVE", "").lower()
    if interactive in _TRUTHY_ENV_VALUES:
        return False
    ...
```

If only used once, skip refactor (YAGNI). Document decision in commit message.

- [ ] **Step 8: Run tests to verify still PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestIsHeadlessContext -v`
Expected: 6/6 tests PASS (no regression).

Run: `make verify`
Expected: Clean.

- [ ] **Step 9: close-phase Refactor**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Refactor phase verify-clean passes. Atomic `refactor:` commit landed (e.g. `refactor: extract _TRUTHY_ENV_VALUES constant`) OR no-op if YAGNI applied. State file advances `current_phase: refactor → done` for this task.

- [ ] **Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: All `[ ]` checkboxes in Task 1 section flipped to `[x]`. Atomic `chore: mark task 1 complete` commit landed (plan diff only). State file advances `current_task_id: 1 → 2`.

---

### Task 2: Item A.2 — Extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + escenarios A-5

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (extend frozenset + update module docstring)
- Test: `tests/test_superpowers_dispatch.py` (add A-5 test)

Covers escenario A-5 from spec sec.4.1.

#### Red Phase

- [ ] **Step 1: Write the failing test**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestSubprocessIncompatibleSkillsExtended:
    """v1.0.4 Item A.2 escenario A-5 — receiving-code-review added to set."""

    def test_receiving_code_review_in_incompatible_set(self):
        """A-5: receiving-code-review extended in v1.0.4."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "receiving-code-review" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_brainstorming_writing_plans_preserved_v101(self):
        """A-5: v1.0.1 baseline (brainstorming, writing-plans) preserved."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "brainstorming" in _SUBPROCESS_INCOMPATIBLE_SKILLS
        assert "writing-plans" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_set_is_frozenset_immutable(self):
        """Defensive: set is frozenset to prevent runtime mutation."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert isinstance(_SUBPROCESS_INCOMPATIBLE_SKILLS, frozenset)

    def test_module_docstring_documents_audit_history(self):
        """A-5 doc-coherence: module docstring records v1.0.1 + v1.0.4 additions."""
        import superpowers_dispatch

        docstring = superpowers_dispatch.__doc__ or ""
        assert "v1.0.1" in docstring
        assert "brainstorming" in docstring
        assert "writing-plans" in docstring
        assert "v1.0.4" in docstring
        assert "receiving-code-review" in docstring
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestSubprocessIncompatibleSkillsExtended -v`
Expected: 1/4 PASS (frozenset check), 3/4 FAIL (receiving-code-review not in set; docstring missing v1.0.4 entry).

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Red phase verify-clean confirms targeted FAILs. `test:` commit landed.

#### Green Phase

- [ ] **Step 4: Extend the set + update module docstring**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py`:

```python
"""Dispatcher for invoking superpowers skills via claude -p subprocess.

...

Subprocess-incompatible skill audit history:
- v1.0.1 (Finding A discovery): brainstorming, writing-plans — both
  require multi-turn interactive dialogue with the operator and cannot
  complete via a single non-interactive subprocess invocation.
- v1.0.4 (v1.0.3 Activity D' empirical hang during Loop 1 fix-finding
  triage step): receiving-code-review — operator triages findings
  interactively before the code-review wrapper accepts/rejects each.

A skill is subprocess-incompatible iff it requires multi-turn
interactive dialogue with the operator. Adding a new entry to the set
without empirical evidence (subprocess hang or silent-no-op observed)
is forbidden — operators must run the skill manually in interactive
session and document the failure mode in CHANGELOG before promoting.
"""

_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset({
    "brainstorming",
    "writing-plans",
    "receiving-code-review",  # v1.0.4 added per v1.0.3 Activity D' dogfood
})
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestSubprocessIncompatibleSkillsExtended -v`
Expected: 4/4 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: extend _SUBPROCESS_INCOMPATIBLE_SKILLS for receiving-code-review`).

#### Refactor Phase

- [ ] **Step 7: Refactor — no changes expected**

The set extension is minimal; docstring documents audit history. No refactor opportunity. Skip.

- [ ] **Step 8: close-phase Refactor (no-op)**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: No-op refactor commit OR phase advance with empty diff (depending on close-phase semantics). State file advances.

- [ ] **Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 2 checkboxes flipped, `chore:` commit, state file advances.

---

### Task 3: Item A.3 — Wire `_is_headless_context` into `invoke_skill` + escenarios A-1 + A-6 + A-7

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (`invoke_skill` function)
- Test: `tests/test_superpowers_dispatch.py` (add A-1, A-6, A-7 tests)

Covers escenarios A-1, A-6, A-7 from spec sec.4.1.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestInvokeSkillHeadlessGate:
    """v1.0.4 Item A.3 escenarios A-1, A-6, A-7 — invoke_skill headless gate."""

    def test_a1_receiving_code_review_raises_in_headless(self, monkeypatch):
        """A-1: invoke_skill('receiving-code-review', ...) raises in headless."""
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        with pytest.raises(PreconditionError) as exc_info:
            invoke_skill("receiving-code-review", "any prompt")
        assert "Skill `/receiving-code-review` cannot run via `claude -p`" in str(exc_info.value)
        assert "headless context" in str(exc_info.value)

    def test_a1_no_subprocess_spawned_when_blocked(self, monkeypatch):
        """A-1: PreconditionError raised BEFORE subprocess spawn (no Popen call)."""
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        with patch("subprocess.run") as mock_run:
            with pytest.raises(PreconditionError):
                invoke_skill("receiving-code-review", "any prompt")
            mock_run.assert_not_called()

    def test_a6_allow_interactive_skill_bypasses_gate(self, monkeypatch):
        """A-6: allow_interactive_skill=True bypasses headless gate."""
        from superpowers_dispatch import invoke_skill

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        # Mock subprocess to avoid actually spawning claude -p
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            # Should NOT raise — override active
            result = invoke_skill(
                "receiving-code-review",
                "any prompt",
                allow_interactive_skill=True,
            )
            mock_run.assert_called_once()

    def test_a7_brainstorming_wrapper_backward_compat(self, monkeypatch):
        """A-7: existing brainstorming wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import brainstorming

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        # Wrapper should pass allow_interactive_skill=True internally
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = brainstorming("any prompt")
            mock_run.assert_called_once()

    def test_a7_writing_plans_wrapper_backward_compat(self, monkeypatch):
        """A-7: existing writing_plans wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import writing_plans

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = writing_plans("any prompt")
            mock_run.assert_called_once()

    def test_skills_not_in_set_pass_through(self, monkeypatch):
        """Defensive: skills NOT in _SUBPROCESS_INCOMPATIBLE_SKILLS pass through."""
        from superpowers_dispatch import invoke_skill

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            # systematic-debugging is NOT in the incompatible set
            result = invoke_skill("systematic-debugging", "any prompt")
            mock_run.assert_called_once()
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillHeadlessGate -v`
Expected: 6/6 FAIL — invoke_skill currently does not check `_is_headless_context()` for incompatible-set membership; PreconditionError not raised.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `test:` commit landed.

#### Green Phase

- [ ] **Step 4: Wire helper into `invoke_skill`**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py` `invoke_skill` function:

```python
def invoke_skill(
    skill: str,
    prompt: str,
    *,
    allow_interactive_skill: bool = False,
    timeout: int = 600,
    output_dir: Path | None = None,
    model: str | None = None,
) -> str:
    """Invoke a superpowers skill via `claude -p` subprocess.

    v1.0.4 Item A.3: pre-spawn headless gate checks
    `_is_headless_context()` for skills in
    `_SUBPROCESS_INCOMPATIBLE_SKILLS`. When triggered, raises
    `PreconditionError` BEFORE subprocess.run is called, eliminating
    the v1.0.3 600s subprocess hang manifestation.

    Override hatch: `allow_interactive_skill=True` bypasses the gate
    for known-safe interactive callsites (e.g., wrappers controlled
    by interactive Loop 1 triage).

    Args:
        skill: Slash-command name (e.g., "receiving-code-review").
        prompt: Skill input.
        allow_interactive_skill: Bypass headless gate (default False).
        timeout: Subprocess timeout in seconds (default 600).
        output_dir: Optional directory for skill output artifacts.
        model: Optional model override (opus/sonnet/haiku).

    Returns:
        Subprocess stdout.

    Raises:
        PreconditionError: If skill is incompatible AND headless
            context detected AND allow_interactive_skill is False.
        ...
    """
    if (
        skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
        and _is_headless_context()
        and not allow_interactive_skill
    ):
        raise PreconditionError(_build_headless_recovery_message(skill))

    # ... existing subprocess.run path unchanged ...
```

For Task 3 implementation, `_build_headless_recovery_message` will be a placeholder helper that returns a minimal string. Task 4 builds out the full per-skill recovery dictionary. Add the placeholder:

```python
def _build_headless_recovery_message(skill: str) -> str:
    """Placeholder; full implementation in Task 4."""
    return (
        f"Skill `/{skill}` cannot run via `claude -p` subprocess in "
        f"headless context (interactive dialogue required)."
    )
```

Also confirm wrappers `brainstorming` + `writing_plans` already pass `allow_interactive_skill=True` (they did in v1.0.1; if not, add):

```python
def brainstorming(prompt: str, ...) -> str:
    return invoke_skill("brainstorming", prompt, ..., allow_interactive_skill=True)


def writing_plans(prompt: str, ...) -> str:
    return invoke_skill("writing-plans", prompt, ..., allow_interactive_skill=True)
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillHeadlessGate -v`
Expected: 6/6 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: wire _is_headless_context gate into invoke_skill`).

#### Refactor Phase

- [ ] **Step 7: Refactor — confirm wrappers + extract gate logic if duplicated**

If multiple wrappers will need `allow_interactive_skill=True`, no further refactor needed — kwarg already in place. If gate logic appears in 2+ places, extract to private helper. Likely YAGNI; skip.

- [ ] **Step 8: Run tests to verify still PASS**

Run: `make verify`
Expected: Clean.

- [ ] **Step 9: close-phase Refactor**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

- [ ] **Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 4: Item B — Build full `_build_headless_recovery_message` + `_PER_SKILL_RECOVERY` + escenarios B-1 + B-2 + B-3

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (replace placeholder + add `_PER_SKILL_RECOVERY` dict + `_GENERIC_RECOVERY` constant)
- Test: `tests/test_superpowers_dispatch.py` (add B-1, B-2, B-3 tests)

Covers escenarios B-1, B-2, B-3 from spec sec.4.2.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestBuildHeadlessRecoveryMessage:
    """v1.0.4 Item B escenarios B-1, B-2, B-3 — recovery message detail + per-skill."""

    def test_b1_message_includes_recovery_options(self, monkeypatch):
        """B-1: PreconditionError message includes all recovery options."""
        from superpowers_dispatch import _build_headless_recovery_message

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = False
            msg = _build_headless_recovery_message("receiving-code-review")
        assert "Skill `/receiving-code-review` cannot run via `claude -p`" in msg
        assert "SBTDD_HEADLESS=1" in msg
        assert "stdin.isatty()=False" in msg
        assert "Run `/receiving-code-review` manually" in msg
        assert "python skills/magi/scripts/run_magi.py" in msg
        assert "SBTDD_INTERACTIVE=1" in msg

    def test_b2_per_skill_recovery_brainstorming(self):
        """B-2: brainstorming recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_headless_recovery_message

        msg = _build_headless_recovery_message("brainstorming")
        assert "Run `/brainstorming` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_writing_plans(self):
        """B-2: writing-plans recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_headless_recovery_message

        msg = _build_headless_recovery_message("writing-plans")
        assert "Run `/writing-plans` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_receiving_code_review(self):
        """B-2: receiving-code-review recovery references run_magi.py + sec.6.4."""
        from superpowers_dispatch import _build_headless_recovery_message

        msg = _build_headless_recovery_message("receiving-code-review")
        assert "Run `/receiving-code-review` manually in interactive session" in msg
        assert "skills/magi/scripts/run_magi.py code-review" in msg
        assert "spec sec.6.4" in msg

    def test_b2_unknown_skill_uses_generic_recovery(self):
        """B-2: unknown skill name falls back to generic recovery message."""
        from superpowers_dispatch import _build_headless_recovery_message, _GENERIC_RECOVERY

        msg = _build_headless_recovery_message("never-shipped-skill")
        # Generic recovery substring should appear in the message
        for line in _GENERIC_RECOVERY.splitlines():
            line = line.strip()
            if line:
                assert line in msg, f"Generic recovery line missing: {line!r}"

    def test_b3_no_subprocess_when_blocked_under_one_second(self, monkeypatch):
        """B-3: PreconditionError raised within 1 second (NOT 600s hang)."""
        import time
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        monkeypatch.setenv("SBTDD_HEADLESS", "1")
        start = time.monotonic()
        with patch("subprocess.run") as mock_run:
            with pytest.raises(PreconditionError):
                invoke_skill("receiving-code-review", "any prompt")
            mock_run.assert_not_called()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Expected <1s; took {elapsed:.2f}s"

    def test_b1_message_reports_actual_env_var_value(self, monkeypatch):
        """B-1: SBTDD_HEADLESS reported value is actual env var content (not hardcoded)."""
        from superpowers_dispatch import _build_headless_recovery_message

        monkeypatch.setenv("SBTDD_HEADLESS", "true")
        msg = _build_headless_recovery_message("receiving-code-review")
        assert "SBTDD_HEADLESS=true" in msg

    def test_b1_message_reports_unset_when_env_absent(self, monkeypatch):
        """B-1: SBTDD_HEADLESS=<unset> when env var not present."""
        from superpowers_dispatch import _build_headless_recovery_message

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        msg = _build_headless_recovery_message("receiving-code-review")
        assert "SBTDD_HEADLESS=<unset>" in msg
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestBuildHeadlessRecoveryMessage -v`
Expected: 8/8 FAIL — placeholder from Task 3 returns minimal string; per-skill dictionary not implemented.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Replace placeholder with full implementation**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py`:

```python
_PER_SKILL_RECOVERY: Mapping[str, str] = MappingProxyType({
    "brainstorming": (
        "  1. Run `/brainstorming` manually in interactive Claude Code session,\n"
        "     then use `/sbtdd spec --resume-from-magi`."
    ),
    "writing-plans": (
        "  1. Run `/writing-plans` manually in interactive Claude Code session,\n"
        "     then use `/sbtdd spec --resume-from-magi`."
    ),
    "receiving-code-review": (
        "  1. Run `/receiving-code-review` manually in interactive session, OR\n"
        "  2. Fall back to manual `python skills/magi/scripts/run_magi.py code-review <payload>`\n"
        "     per spec sec.6.4 + apply mini-cycle TDD fixes manually."
    ),
})

_GENERIC_RECOVERY = (
    "  1. Run the skill manually in interactive session,\n"
    "     then resume the SBTDD workflow."
)


def _build_headless_recovery_message(skill: str) -> str:
    """Construct the operator-facing recovery message for a blocked skill.

    Args:
        skill: Slash-command name (e.g., "receiving-code-review").

    Returns:
        Multi-line operator-facing message including:
        - Reason (skill incompatible + headless context detected)
        - Detected env state (SBTDD_HEADLESS value + stdin.isatty())
        - Per-skill recovery options (or generic if skill unknown)
        - Generic SBTDD_INTERACTIVE escape-hatch hint
    """
    sbtdd_headless = os.environ.get("SBTDD_HEADLESS", "<unset>")
    try:
        isatty = sys.stdin.isatty()
    except (AttributeError, OSError):
        isatty = False
    per_skill = _PER_SKILL_RECOVERY.get(skill, _GENERIC_RECOVERY)
    return (
        f"Skill `/{skill}` cannot run via `claude -p` subprocess in "
        f"headless context (interactive dialogue required). Detected:\n"
        f"  SBTDD_HEADLESS={sbtdd_headless} | stdin.isatty()={isatty}\n"
        f"Recovery options:\n"
        f"{per_skill}\n"
        f"  Set SBTDD_INTERACTIVE=1 if you ARE in interactive context\n"
        f"  but isatty() returns false (rare; e.g., piped script)."
    )
```

Confirm `from types import MappingProxyType` and `from typing import Mapping` are imported.

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestBuildHeadlessRecoveryMessage -v`
Expected: 8/8 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: build per-skill headless recovery messages for v1.0.4 Item B`).

#### Refactor Phase

- [ ] **Step 7: Refactor — extract message format string if reusable**

If recovery message format becomes verbose, extract template. Likely YAGNI; skip.

- [ ] **Step 8: close-phase Refactor + Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 5: Audit existing callsites — extend `test_invoke_skill_callsites_audit.py`

**Files:**
- Modify: `tests/test_invoke_skill_callsites_audit.py` (extend AST-based audit to cover new headless gate)

#### Red Phase

- [ ] **Step 1: Write the failing test**

Append to `tests/test_invoke_skill_callsites_audit.py`:

```python
class TestHeadlessGateCallsiteConsistency:
    """v1.0.4 Item A.5 — audit no callsite bypasses headless gate inappropriately."""

    def test_no_invoke_skill_call_with_allow_interactive_skill_true_outside_known_safe(self):
        """Audit: allow_interactive_skill=True only at known-safe callsites.

        Known-safe callsites (v1.0.4 baseline):
        - skills/sbtdd/scripts/superpowers_dispatch.py: brainstorming + writing_plans wrappers
        - tests/* (all test files allowed; pytest fixture context)

        Any new callsite passing allow_interactive_skill=True OUTSIDE these
        locations is a regression — must be removed or whitelisted with
        rationale comment.
        """
        repo_root = Path(__file__).resolve().parents[1]
        skills_dir = repo_root / "skills" / "sbtdd" / "scripts"

        # Whitelist: callsite location → reason
        # Permite tracking explicito de excepciones; cualquier nueva entrada
        # require code review + ratio en este test.
        WHITELIST = {
            "superpowers_dispatch.py": "wrapper functions brainstorming/writing_plans pass override internally per v1.0.1 baseline",
            # Add new entries with explicit rationale in code review
        }

        offenders: list[tuple[str, int, str]] = []
        for py_file in skills_dir.rglob("*.py"):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                # Match invoke_skill(...) or *_dispatch.invoke_skill(...)
                func = node.func
                func_name = None
                if isinstance(func, ast.Name):
                    func_name = func.id
                elif isinstance(func, ast.Attribute):
                    func_name = func.attr
                if func_name != "invoke_skill":
                    continue
                # Look for allow_interactive_skill=True keyword
                for kw in node.keywords:
                    if kw.arg == "allow_interactive_skill":
                        if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            file_basename = py_file.name
                            if file_basename not in WHITELIST:
                                offenders.append((str(py_file.relative_to(repo_root)), node.lineno, "allow_interactive_skill=True"))

        assert not offenders, (
            "Found unwhitelisted callsites passing allow_interactive_skill=True:\n"
            + "\n".join(f"  {path}:{lineno} ({reason})" for path, lineno, reason in offenders)
            + "\nAdd to WHITELIST with rationale or remove the override."
        )

    def test_subprocess_dispatch_module_imports_ast_safe(self):
        """Defensive: AST audit can parse superpowers_dispatch.py without error."""
        repo_root = Path(__file__).resolve().parents[1]
        path = repo_root / "skills" / "sbtdd" / "scripts" / "superpowers_dispatch.py"
        # Must parse without SyntaxError
        ast.parse(path.read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run tests to verify either PASS (if no offenders) OR FAIL (if surfaced)**

Run: `pytest tests/test_invoke_skill_callsites_audit.py::TestHeadlessGateCallsiteConsistency -v`
Expected: 2/2 PASS (whitelisted brainstorming + writing_plans wrappers; no other callsites pass override). If FAIL, investigate offenders + decide whitelist or remove.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

(If tests already PASS, the `test:` commit captures the regression-guard; this is a defensive test that may not have a Red phase if the codebase is clean. If genuine Red, fix offenders before commit.)

#### Green Phase

- [ ] **Step 4: No production code changes expected**

The test is purely a regression guard. Production code is correct as of Task 4 close.

If Step 2 surfaced offenders, fix each by either: (a) removing the override (preferred), OR (b) adding to WHITELIST with rationale (only if subagent has explicit reason e.g. interactive Loop 1 triage callsite).

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_invoke_skill_callsites_audit.py -v`
Expected: All audit tests PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green (no-op or fix commit)**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Refactor Phase

- [ ] **Step 7: Skip refactor (audit test is canonical form)**
- [ ] **Step 8: close-phase Refactor + Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

## Track Beta — Items C+D parallel dispatcher + close-phase mandate (Subagent #2, sequential T6 → T7 → T8 → T9)

**Owner**: Subagent #2 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Alpha):
- Create: `skills/sbtdd/scripts/dag_parser.py` (NEW)
- Create: `skills/sbtdd/scripts/parallel_dispatcher.py` (NEW)
- Modify: `skills/sbtdd/scripts/auto_cmd.py`
- Create: `tests/test_dag_parser.py` (NEW)
- Create: `tests/test_parallel_dispatcher.py` (NEW)
- Modify: `tests/test_auto_cmd.py`
- Modify: `skills/sbtdd/SKILL.md` (Item D doc)
- Modify: `templates/CLAUDE.local.md.template` (Item D doc)
- Create: `tests/test_close_phase_subagent_pattern.py` (NEW, Item D smoke)

**Wall-time estimated**: ~2 days.

### Task 6: Item C.1 — `dag_parser.py` module + escenarios C-1 + C-2 + C-3 + C-4

**Files:**
- Create: `skills/sbtdd/scripts/dag_parser.py`
- Create: `tests/test_dag_parser.py`

Covers escenarios C-1, C-2, C-3, C-4 from spec sec.4.3.

#### Red Phase

- [ ] **Step 1: Write failing tests**

Create `tests/test_dag_parser.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.1 — dag_parser module tests.

Covers escenarios C-1 (Task block parsing), C-2 (addBlockedBy
extraction), C-3 (cycle detection), C-4 (antichain identification)
from spec sec.4.3.
"""

from __future__ import annotations

from pathlib import Path
import textwrap

import pytest

from dag_parser import parse_plan, Task, TaskGraph
from errors import ValidationError


@pytest.fixture
def simple_plan(tmp_path: Path) -> Path:
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        # Plan

        ### Task 1: Foo

        **Files:**
        - Modify: `src/foo.py`

        ### Task 2: Bar

        **Files:**
        - Modify: `src/bar.py`

        **Depends on**: Task 1

        ### Task 3: Baz

        **Files:**
        - Modify: `src/baz.py`
        """))
    return plan


@pytest.fixture
def cyclic_plan(tmp_path: Path) -> Path:
    plan = tmp_path / "cyclic.md"
    plan.write_text(textwrap.dedent("""\
        # Plan

        ### Task 1: Foo

        **Files:**
        - Modify: `src/foo.py`

        **Depends on**: Task 2

        ### Task 2: Bar

        **Files:**
        - Modify: `src/bar.py`

        **Depends on**: Task 1
        """))
    return plan


def test_c1_parses_task_blocks(simple_plan: Path):
    """C-1: dag_parser parses ### Task N: blocks into TaskGraph."""
    graph = parse_plan(simple_plan)
    assert isinstance(graph, TaskGraph)
    assert set(graph.tasks.keys()) == {"1", "2", "3"}
    assert graph.tasks["1"].title == "Foo"
    assert graph.tasks["2"].title == "Bar"
    assert graph.tasks["3"].title == "Baz"


def test_c1_extracts_files_lists(simple_plan: Path):
    """C-1: each Task has Files list extracted."""
    graph = parse_plan(simple_plan)
    assert "src/foo.py" in graph.tasks["1"].files
    assert "src/bar.py" in graph.tasks["2"].files
    assert "src/baz.py" in graph.tasks["3"].files


def test_c2_extracts_depends_on_dependencies(simple_plan: Path):
    """C-2: 'Depends on: Task M' extracted as edge."""
    graph = parse_plan(simple_plan)
    assert graph.edges.get("2", set()) == {"1"}
    assert graph.edges.get("1", set()) == set()
    assert graph.edges.get("3", set()) == set()


def test_c2_extracts_addblockedby_dependencies(tmp_path: Path):
    """C-2: 'addBlockedBy: [Task M, Task K]' extracted as edges."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: A

        **Files:**
        - Modify: `a.py`

        ### Task 2: B

        **Files:**
        - Modify: `b.py`

        **addBlockedBy**: [Task 1]

        ### Task 3: C

        **Files:**
        - Modify: `c.py`

        **addBlockedBy**: [Task 1, Task 2]
        """))
    graph = parse_plan(plan)
    assert graph.edges["2"] == {"1"}
    assert graph.edges["3"] == {"1", "2"}


def test_c3_detects_cycle(cyclic_plan: Path):
    """C-3: cyclic dependencies raise ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(cyclic_plan)
    msg = str(exc_info.value).lower()
    assert "cycle" in msg or "cyclic" in msg


def test_c4_antichain_identification(simple_plan: Path):
    """C-4: antichains() returns ordered list of parallelizable batches."""
    graph = parse_plan(simple_plan)
    chains = graph.antichains()
    assert len(chains) == 2
    # First antichain: tasks with no dependencies (1 + 3)
    assert chains[0] == {"1", "3"}
    # Second antichain: tasks unblocked after first batch (2)
    assert chains[1] == {"2"}


def test_c4_antichain_single_task_per_batch_when_chain(tmp_path: Path):
    """C-4: linear chain produces single-task antichains."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: A

        **Files:**
        - Modify: `a.py`

        ### Task 2: B

        **Files:**
        - Modify: `b.py`

        **Depends on**: Task 1

        ### Task 3: C

        **Files:**
        - Modify: `c.py`

        **Depends on**: Task 2
        """))
    graph = parse_plan(plan)
    chains = graph.antichains()
    assert chains == [{"1"}, {"2"}, {"3"}]


def test_c4_antichain_all_independent_single_batch(tmp_path: Path):
    """C-4: fully independent tasks produce single antichain."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: A

        **Files:**
        - Modify: `a.py`

        ### Task 2: B

        **Files:**
        - Modify: `b.py`

        ### Task 3: C

        **Files:**
        - Modify: `c.py`
        """))
    graph = parse_plan(plan)
    chains = graph.antichains()
    assert chains == [{"1", "2", "3"}]


def test_c1_empty_plan_returns_empty_graph(tmp_path: Path):
    """Defensive: plan with no Task blocks returns empty graph."""
    plan = tmp_path / "empty.md"
    plan.write_text("# Plan\n\nNo tasks here.\n")
    graph = parse_plan(plan)
    assert graph.tasks == {}
    assert graph.antichains() == []


def test_c1_task_without_files_section_parses(tmp_path: Path):
    """Defensive: task without Files: section parses with empty files set."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: Doc-only

        Some description without Files block.
        """))
    graph = parse_plan(plan)
    assert "1" in graph.tasks
    assert graph.tasks["1"].files == set()


def test_c2_unknown_dependency_target_raises(tmp_path: Path):
    """Defensive: dependency on non-existent task raises ValidationError."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: A

        **Files:**
        - Modify: `a.py`

        **Depends on**: Task 999
        """))
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(plan)
    msg = str(exc_info.value).lower()
    assert "999" in msg or "unknown" in msg
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_dag_parser.py -v`
Expected: All FAIL — `dag_parser` module does not exist.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Implement `dag_parser.py`**

Create `skills/sbtdd/scripts/dag_parser.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.1 — DAG parser for plan-tdd.md.

Parses planning/claude-plan-tdd.md task blocks + dependency markers
to build a directed acyclic graph used by `parallel_dispatcher.py`
for batch dispatch.

Public API:
    parse_plan(plan_path: Path) -> TaskGraph
    class Task (dataclass)
    class TaskGraph (with .tasks, .edges, .antichains())
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from errors import ValidationError


_TASK_HEADER_RE = re.compile(r"^### Task (\d+)(?::|\s)\s*(.*)$", re.MULTILINE)
_FILES_BLOCK_RE = re.compile(
    r"^\*\*Files:\*\*\s*\n((?:^\s*-\s+(?:Create|Modify|Test)\s*:\s*[`\S].+\n?)+)",
    re.MULTILINE,
)
_FILE_LINE_RE = re.compile(
    r"^\s*-\s+(?:Create|Modify|Test)\s*:\s*`?([^`\s]+)`?",
    re.MULTILINE,
)
_DEPENDS_ON_RE = re.compile(
    r"^\*\*Depends on\*\*\s*:\s*Task\s+(\d+)\s*$", re.MULTILINE
)
_ADD_BLOCKED_BY_RE = re.compile(
    r"^\*\*addBlockedBy\*\*\s*:\s*\[(.+?)\]\s*$", re.MULTILINE
)
_TASK_REF_RE = re.compile(r"Task\s+(\d+)")


@dataclass(frozen=True)
class Task:
    """One task entry from the plan."""

    id: str
    title: str
    files: frozenset[str] = field(default_factory=frozenset)


@dataclass
class TaskGraph:
    """Directed acyclic graph of plan tasks.

    Attributes:
        tasks: Mapping of task_id -> Task dataclass.
        edges: Mapping of task_id -> set of task_ids it depends on
            (predecessors). edges[X] = {A, B} means X depends on A AND B,
            so A + B must complete before X.
    """

    tasks: dict[str, Task] = field(default_factory=dict)
    edges: dict[str, set[str]] = field(default_factory=dict)

    def antichains(self) -> list[set[str]]:
        """Return ordered list of maximal antichains (parallel batches).

        First antichain contains tasks with no dependencies. Subsequent
        antichains contain tasks whose dependencies all appear in
        prior antichains. Output respects ONLY explicit dependencies;
        file-surface collision detection is a separate step in
        `parallel_dispatcher.partition_by_collision`.

        Returns:
            List of sets; each set is a parallel batch (in plan order).
        """
        result: list[set[str]] = []
        completed: set[str] = set()
        remaining = set(self.tasks.keys())
        while remaining:
            batch = {
                tid for tid in remaining
                if self.edges.get(tid, set()) <= completed
            }
            if not batch:
                # Should not happen if cycle check passed; defensive
                raise ValidationError(
                    f"Antichain partition stalled; possible cycle in remaining: {remaining}"
                )
            result.append(batch)
            completed |= batch
            remaining -= batch
        return result


def _extract_files(task_text: str) -> frozenset[str]:
    """Extract Files: list from a task body."""
    match = _FILES_BLOCK_RE.search(task_text)
    if not match:
        return frozenset()
    block = match.group(0)
    return frozenset(_FILE_LINE_RE.findall(block))


def _extract_dependencies(task_text: str) -> set[str]:
    """Extract Depends on: + addBlockedBy: dependencies as task IDs."""
    deps: set[str] = set()
    for m in _DEPENDS_ON_RE.finditer(task_text):
        deps.add(m.group(1))
    abb_match = _ADD_BLOCKED_BY_RE.search(task_text)
    if abb_match:
        for ref_match in _TASK_REF_RE.finditer(abb_match.group(1)):
            deps.add(ref_match.group(1))
    return deps


def _split_task_blocks(plan_text: str) -> list[tuple[str, str, str]]:
    """Split plan text into (task_id, title, body) tuples.

    Returns one entry per ### Task N: block, with body containing
    everything from the header up to (but not including) the next
    ### Task N: header or end-of-file.
    """
    headers = list(_TASK_HEADER_RE.finditer(plan_text))
    if not headers:
        return []
    blocks: list[tuple[str, str, str]] = []
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(plan_text)
        body = plan_text[start:end]
        blocks.append((m.group(1), m.group(2).strip(), body))
    return blocks


def _detect_cycle(edges: dict[str, set[str]]) -> list[str] | None:
    """Return cycle path if found, else None. Tarjan-style DFS."""
    visited: set[str] = set()
    stack: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        if node in stack:
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]
        if node in visited:
            return None
        visited.add(node)
        stack.add(node)
        path.append(node)
        for dep in edges.get(node, set()):
            cycle = dfs(dep)
            if cycle is not None:
                return cycle
        stack.discard(node)
        path.pop()
        return None

    for node in edges:
        cycle = dfs(node)
        if cycle is not None:
            return cycle
    return None


def parse_plan(plan_path: Path) -> TaskGraph:
    """Parse plan file into TaskGraph.

    Args:
        plan_path: Path to planning/claude-plan-tdd.md.

    Returns:
        TaskGraph with tasks + edges populated.

    Raises:
        ValidationError: If plan contains a dependency cycle OR
            references a non-existent task.
    """
    plan_text = plan_path.read_text(encoding="utf-8")
    blocks = _split_task_blocks(plan_text)
    tasks: dict[str, Task] = {}
    edges: dict[str, set[str]] = {}
    for tid, title, body in blocks:
        tasks[tid] = Task(id=tid, title=title, files=_extract_files(body))
        edges[tid] = _extract_dependencies(body)

    # Validate dependency targets exist
    all_ids = set(tasks.keys())
    for tid, deps in edges.items():
        unknown = deps - all_ids
        if unknown:
            raise ValidationError(
                f"Task {tid} depends on unknown task(s): {sorted(unknown)}"
            )

    # Cycle detection
    cycle = _detect_cycle(edges)
    if cycle is not None:
        raise ValidationError(
            f"Cyclic dependency detected: {' -> '.join(cycle)}"
        )

    return TaskGraph(tasks=tasks, edges=edges)
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_dag_parser.py -v`
Expected: 12/12 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: add dag_parser module for v1.0.4 Item C`).

#### Refactor Phase

- [ ] **Step 7: Refactor — extract helper functions if needed**

Module already structured by responsibility (split, extract files, extract deps, cycle detect, parse). Skip refactor.

- [ ] **Step 8: close-phase Refactor + Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 7: Item C.2 — `parallel_dispatcher.py` module + escenarios C-5 + C-6

**Files:**
- Create: `skills/sbtdd/scripts/parallel_dispatcher.py`
- Create: `tests/test_parallel_dispatcher.py`

Covers escenarios C-5, C-6 from spec sec.4.3.

#### Red Phase

- [ ] **Step 1: Write failing tests**

Create `tests/test_parallel_dispatcher.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.2 — parallel_dispatcher module tests.

Covers escenarios C-5 (file collision detection) + C-6 (disjoint
passthrough) from spec sec.4.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dag_parser import Task, TaskGraph
from parallel_dispatcher import partition_by_collision, _files_collide


def _make_graph(tasks_with_files: dict[str, set[str]]) -> TaskGraph:
    tasks = {
        tid: Task(id=tid, title=f"Task {tid}", files=frozenset(files))
        for tid, files in tasks_with_files.items()
    }
    return TaskGraph(tasks=tasks, edges={tid: set() for tid in tasks})


def test_c5_collision_detection_shared_file():
    """C-5: tasks sharing a file collide."""
    graph = _make_graph({"1": {"a.py"}, "2": {"a.py"}})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is True


def test_c5_partition_collision_splits_batch():
    """C-5: collision-detected antichain splits into 2 sub-batches."""
    graph = _make_graph({"1": {"auto_cmd.py"}, "2": {"auto_cmd.py"}})
    batches = partition_by_collision({"1", "2"}, graph)
    # Two single-task batches (cannot run parallel)
    assert len(batches) == 2
    assert {"1"} in batches
    assert {"2"} in batches


def test_c6_disjoint_files_pass_through():
    """C-6: tasks with disjoint files yield single batch."""
    graph = _make_graph({"1": {"a.py"}, "2": {"b.py"}})
    batches = partition_by_collision({"1", "2"}, graph)
    assert batches == [{"1", "2"}]


def test_c6_no_files_pass_through():
    """C-6: tasks without files (doc-only) pass through as single batch."""
    graph = _make_graph({"1": set(), "2": set()})
    batches = partition_by_collision({"1", "2"}, graph)
    assert batches == [{"1", "2"}]


def test_c5_three_way_collision():
    """C-5: three tasks pairwise-colliding split fully."""
    graph = _make_graph({
        "1": {"a.py"},
        "2": {"a.py"},
        "3": {"a.py"},
    })
    batches = partition_by_collision({"1", "2", "3"}, graph)
    assert len(batches) == 3
    assert all(len(b) == 1 for b in batches)


def test_c6_partial_collision_groups():
    """C-6: 1+2 collide on a.py; 3 disjoint → batches [{1,3}, {2}] OR [{2,3}, {1}]."""
    graph = _make_graph({
        "1": {"a.py"},
        "2": {"a.py"},
        "3": {"b.py"},
    })
    batches = partition_by_collision({"1", "2", "3"}, graph)
    # Total 3 tasks distributed; one batch must be size 2 (with 3 + non-colliding task)
    # and one batch must contain the leftover colliding task
    flat = {tid for batch in batches for tid in batch}
    assert flat == {"1", "2", "3"}
    sizes = sorted(len(b) for b in batches)
    assert sizes == [1, 2]


def test_c5_singleton_passthrough():
    """C-5/C-6: singleton antichain returns single-task batch."""
    graph = _make_graph({"1": {"a.py"}})
    batches = partition_by_collision({"1"}, graph)
    assert batches == [{"1"}]


def test_c5_files_collide_helper_disjoint():
    """C-5: _files_collide returns False for disjoint sets."""
    graph = _make_graph({"1": {"a.py"}, "2": {"b.py"}})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is False


def test_c5_files_collide_helper_empty():
    """C-5: _files_collide returns False for empty file sets."""
    graph = _make_graph({"1": set(), "2": set()})
    assert _files_collide(graph.tasks["1"], graph.tasks["2"]) is False
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_parallel_dispatcher.py -v`
Expected: All FAIL — module does not exist.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Implement `parallel_dispatcher.py`**

Create `skills/sbtdd/scripts/parallel_dispatcher.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item C.2 — Parallel task dispatcher.

Coordinates concurrent task execution within an antichain
(dependency-free batch from `dag_parser.TaskGraph.antichains()`),
splitting the antichain into file-surface-disjoint sub-batches
to avoid same-worktree write conflicts.

Public API:
    partition_by_collision(antichain, graph) -> list[set[str]]
    dispatch_batch(batch, graph, ...) — opt-in concurrent dispatch
"""

from __future__ import annotations

from dag_parser import Task, TaskGraph


def _files_collide(task_a: Task, task_b: Task) -> bool:
    """Return True if two tasks share at least one file surface."""
    if not task_a.files or not task_b.files:
        return False
    return bool(task_a.files & task_b.files)


def partition_by_collision(
    antichain: set[str],
    graph: TaskGraph,
) -> list[set[str]]:
    """Split a dependency-free antichain into surface-disjoint sub-batches.

    Two tasks can run in the same parallel batch only if their
    `Files:` lists are disjoint. This function greedy-packs tasks
    into sub-batches so that every task in a sub-batch is
    pairwise-disjoint with every other task in the same sub-batch.

    Args:
        antichain: Set of task IDs (output of TaskGraph.antichains()).
        graph: The TaskGraph (for Task lookup).

    Returns:
        List of sets; each set is a sub-batch where all tasks have
        disjoint file surfaces. Single-task sub-batches indicate the
        task collides with every other task in the antichain.
    """
    if not antichain:
        return []
    remaining = list(antichain)
    sub_batches: list[set[str]] = []
    while remaining:
        head = remaining.pop(0)
        batch = {head}
        head_files = graph.tasks[head].files
        merged_files = set(head_files)
        leftover: list[str] = []
        for tid in remaining:
            tid_files = graph.tasks[tid].files
            if not (tid_files & merged_files):
                batch.add(tid)
                merged_files |= tid_files
            else:
                leftover.append(tid)
        sub_batches.append(batch)
        remaining = leftover
    return sub_batches
```

Note: `dispatch_batch` (concurrent process spawn) is NOT implemented in Task 7 — exact transport (Agent tool fan-out vs subprocess.Popen) deferred to Task 8 wiring. Task 7 ships partition logic only.

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_parallel_dispatcher.py -v`
Expected: 9/9 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: add parallel_dispatcher partition logic for v1.0.4 Item C`).

#### Refactor Phase

- [ ] **Step 7: Refactor — confirm greedy packing optimal for typical cases**

Greedy packing is O(n^2) but n is small (typical antichain ≤ 10 tasks). Optimal partition is NP-hard (graph coloring); greedy is acceptable. Document decision in commit message OR module docstring.

- [ ] **Step 8: close-phase Refactor + Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 8: Item C.3 — `auto_cmd.py` `--parallel` flag wiring + escenarios C-7 + C-8 + C-9

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add `--parallel` flag + branching logic + TDD-Guard warning)
- Modify: `tests/test_auto_cmd.py` (add C-7, C-8, C-9 tests)

Covers escenarios C-7, C-8, C-9 from spec sec.4.3.

#### Red Phase

- [ ] **Step 1: Write failing tests**

Append to `tests/test_auto_cmd.py`:

```python
class TestAutoCmdParallelFlag:
    """v1.0.4 Item C.3 escenarios C-7, C-8, C-9 — --parallel flag wiring."""

    def test_c7_parallel_flag_dispatches_batches(self, tmp_path: Path, monkeypatch):
        """C-7: --parallel flag dispatches parallelizable tasks in batches."""
        # Setup synthetic plan with 2 disjoint tasks
        plan = tmp_path / "plan.md"
        plan.write_text(textwrap.dedent("""\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            ### Task 2: B

            **Files:**
            - Modify: `b.py`
            """))

        from auto_cmd import _build_dispatch_plan_parallel

        dispatch_plan = _build_dispatch_plan_parallel(plan)
        # Expect single batch with both tasks
        assert len(dispatch_plan) == 1
        assert dispatch_plan[0] == {"1", "2"}

    def test_c8_sequential_default_preserves_order(self, tmp_path: Path):
        """C-8: --parallel NOT specified preserves v1.0.3 sequential order."""
        from auto_cmd import _build_dispatch_plan_sequential

        plan = tmp_path / "plan.md"
        plan.write_text(textwrap.dedent("""\
            ### Task 1: A

            **Files:**
            - Modify: `a.py`

            ### Task 2: B

            **Files:**
            - Modify: `b.py`
            """))

        dispatch_plan = _build_dispatch_plan_sequential(plan)
        # Sequential: each batch is single-task in plan order
        assert dispatch_plan == [{"1"}, {"2"}]

    def test_c8_collision_forces_sequential_in_parallel_mode(self, tmp_path: Path):
        """C-8: file-colliding tasks split into sub-batches even under --parallel."""
        from auto_cmd import _build_dispatch_plan_parallel

        plan = tmp_path / "plan.md"
        plan.write_text(textwrap.dedent("""\
            ### Task 1: A

            **Files:**
            - Modify: `shared.py`

            ### Task 2: B

            **Files:**
            - Modify: `shared.py`
            """))

        dispatch_plan = _build_dispatch_plan_parallel(plan)
        # Both tasks modify shared.py → 2 sub-batches
        assert len(dispatch_plan) == 2
        sizes = sorted(len(b) for b in dispatch_plan)
        assert sizes == [1, 1]

    def test_c9_tdd_guard_warning_in_parallel_mode(self, tmp_path: Path, capsys):
        """C-9: --parallel emits warning when TDD-Guard hooks detected."""
        from auto_cmd import _check_tdd_guard_warning

        # Synthesize .claude/settings.json with TDD-Guard hook
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Write|Edit",
                    "hooks": [{"type": "command", "command": "tdd-guard"}],
                }]
            }
        }))

        _check_tdd_guard_warning(parallel=True, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "Parallel mode" in captured.err
        assert "TDD-Guard" in captured.err
        assert "tdd-guard off" in captured.err
        assert "/using-git-worktrees" in captured.err

    def test_c9_no_warning_in_sequential_mode(self, tmp_path: Path, capsys):
        """C-9: sequential mode (no --parallel) emits no TDD-Guard warning."""
        from auto_cmd import _check_tdd_guard_warning

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(json.dumps({
            "hooks": {"PreToolUse": [{"matcher": "Write", "hooks": [{"type": "command", "command": "tdd-guard"}]}]}
        }))

        _check_tdd_guard_warning(parallel=False, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "Parallel mode" not in captured.err

    def test_c9_no_warning_when_tdd_guard_absent(self, tmp_path: Path, capsys):
        """C-9: --parallel without TDD-Guard hooks emits no warning."""
        from auto_cmd import _check_tdd_guard_warning

        # No .claude/settings.json
        _check_tdd_guard_warning(parallel=True, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "TDD-Guard" not in captured.err

    def test_c7_run_sbtdd_auto_accepts_parallel_flag(self):
        """C-7: argparse accepts --parallel flag."""
        from run_sbtdd import _build_arg_parser

        parser = _build_arg_parser()
        ns = parser.parse_args(["auto", "--parallel"])
        assert ns.parallel is True

    def test_c7_run_sbtdd_auto_default_parallel_false(self):
        """C-7/C-8: default value of --parallel is False (preserves sequential)."""
        from run_sbtdd import _build_arg_parser

        parser = _build_arg_parser()
        ns = parser.parse_args(["auto"])
        assert ns.parallel is False
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestAutoCmdParallelFlag -v`
Expected: All FAIL — `--parallel` flag not in argparse, helper functions absent.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Wire `--parallel` flag into auto_cmd**

Modify `skills/sbtdd/scripts/auto_cmd.py`:

```python
# Add imports at top
from dag_parser import parse_plan, TaskGraph
from parallel_dispatcher import partition_by_collision


def _build_dispatch_plan_sequential(plan_path: Path) -> list[set[str]]:
    """Sequential dispatch plan — each task in its own batch in plan order.

    Preserves v1.0.3 behavior exactly. Default when --parallel NOT
    specified.
    """
    graph = parse_plan(plan_path)
    return [{tid} for tid in graph.tasks.keys()]


def _build_dispatch_plan_parallel(plan_path: Path) -> list[set[str]]:
    """Parallel dispatch plan — antichains partitioned by file collisions.

    v1.0.4 Item C: opt-in via --parallel flag. DAG analysis +
    file-surface collision detection produce parallel-safe batches.
    """
    graph = parse_plan(plan_path)
    chains = graph.antichains()
    flat: list[set[str]] = []
    for chain in chains:
        flat.extend(partition_by_collision(chain, graph))
    return flat


def _check_tdd_guard_warning(parallel: bool, project_root: Path) -> None:
    """Emit stderr warning when --parallel + TDD-Guard hooks detected.

    Per spec sec.3 multi-agent rules: parallel mode in same worktree
    with TDD-Guard ON produces false bloqueos. Document escape via
    `tdd-guard off` toggle OR per-subagent worktree.
    """
    if not parallel:
        return
    settings_path = project_root / ".claude" / "settings.json"
    if not settings_path.exists():
        return
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return
    hooks = settings.get("hooks", {})
    has_tdd_guard = False
    for hook_list in hooks.values():
        if not isinstance(hook_list, list):
            continue
        for entry in hook_list:
            if not isinstance(entry, dict):
                continue
            for h in entry.get("hooks", []):
                if isinstance(h, dict) and "tdd-guard" in str(h.get("command", "")).lower():
                    has_tdd_guard = True
                    break
    if has_tdd_guard:
        sys.stderr.write(
            "[sbtdd auto] WARNING: Parallel mode in same worktree with "
            "TDD-Guard ON may produce false bloqueos. Toggle off with "
            "`tdd-guard off` per spec sec.3 multi-agent rules, OR use "
            "`/using-git-worktrees` for per-subagent worktree.\n"
        )


# Modify run() / cmd() entry point to branch on parallel flag:
def cmd(args: argparse.Namespace) -> int:
    ...
    _check_tdd_guard_warning(parallel=args.parallel, project_root=Path.cwd())
    if args.parallel:
        dispatch_plan = _build_dispatch_plan_parallel(plan_path)
        # Concurrent dispatch via Agent tool / subprocess Popen
        # (exact transport is orchestrator-side; Track Beta documents
        # it as INFO finding for v1.0.5+ refinement)
    else:
        dispatch_plan = _build_dispatch_plan_sequential(plan_path)
    ...
```

Modify `skills/sbtdd/scripts/run_sbtdd.py` `_build_arg_parser`:

```python
def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(...)
    sub = parser.add_subparsers(dest="cmd", required=True)
    ...
    auto_p = sub.add_parser("auto", help="...")
    ...
    auto_p.add_argument(
        "--parallel",
        action="store_true",
        default=False,
        help="v1.0.4 Item C: dispatch parallelizable task batches "
             "concurrently. Requires TDD-Guard OFF in same worktree, "
             "OR per-subagent worktree (see spec sec.3).",
    )
    ...
```

- [ ] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestAutoCmdParallelFlag -v`
Expected: 8/8 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: wire --parallel flag into auto_cmd for v1.0.4 Item C`).

#### Refactor Phase

- [ ] **Step 7: Refactor — extract dispatch-plan-building if helpers grow**

Two helpers `_build_dispatch_plan_sequential` and
`_build_dispatch_plan_parallel` are minimal and have clear separation.
Skip refactor.

- [ ] **Step 8: close-phase Refactor + Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 9: Item D — Per-phase close-phase doc-only mandate + escenarios D-1 + D-2 + D-3

**Files:**
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules)
- Modify: `templates/CLAUDE.local.md.template` (template guidance to destination projects)
- Modify: writing-plans skill prompt extension (template for plan generation)
- Create: `tests/test_close_phase_subagent_pattern.py` (smoke test, doc-coherence)

Covers escenarios D-1, D-2, D-3 from spec sec.4.4.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Create `tests/test_close_phase_subagent_pattern.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-07
"""v1.0.4 Item D — close-phase per-phase mandate doc-coherence smoke test.

Covers escenarios D-1, D-2, D-3 from spec sec.4.4. Pattern follows
v1.0.2 Item E doc-only smoke (`tests/test_close_task_subagent_pattern.py`).

The actual code path of `/sbtdd close-phase` is covered by
`tests/test_close_phase_cmd.py`; this smoke asserts that documentation
references it from the 3 mandated touchpoints (Q3 Option B 3-touchpoint
enforcement vs v1.0.2 single I5 process notes).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_d1_skill_md_mandates_close_phase_per_phase():
    """D-1: SKILL.md contains the per-phase close-phase mandate."""
    skill_md = _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    # Mandate text must reference close-phase per Red/Green/Refactor
    assert "close-phase" in text
    assert "Red" in text and "Green" in text and "Refactor" in text
    # Mandate explicitly states manual `git commit` per phase is non-conforming
    assert re.search(
        r"manual.+git\s+commit.+(BYPASS|NON-CONFORMING)",
        text,
        re.IGNORECASE | re.DOTALL,
    ), (
        "SKILL.md must explicitly state that manual `git commit` per phase "
        "BYPASSES close-phase / is NON-CONFORMING (Q3 Option B mandate)."
    )


def test_d2_claude_local_template_references_close_phase():
    """D-2: CLAUDE.local.md.template references close-phase per phase."""
    template = _REPO_ROOT / "templates" / "CLAUDE.local.md.template"
    text = template.read_text(encoding="utf-8")
    assert "close-phase" in text, (
        "CLAUDE.local.md.template must reference close-phase command per "
        "Q3 Option B 3-touchpoint enforcement."
    )
    # Template must reference the per-phase Red/Green/Refactor pattern
    assert re.search(r"Red.+Green.+Refactor", text, re.DOTALL), (
        "Template must document close-phase per Red/Green/Refactor cycle."
    )


def test_d3_writing_plans_template_uses_close_phase_in_steps():
    """D-3: writing-plans skill prompt extension generates close-phase steps."""
    # The extension is documented either in SKILL.md OR a dedicated template
    # under templates/. Prefer searching templates/ first.
    extension_candidates = [
        _REPO_ROOT / "templates" / "writing-plans-extension.md",
        _REPO_ROOT / "templates" / "plan-tdd-template.md",
        _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md",
    ]
    found_in: list[Path] = []
    for candidate in extension_candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        # Look for close-phase in per-phase context
        if "close-phase" in text and re.search(
            r"close-phase\s+(Red|Green|Refactor)",
            text,
            re.IGNORECASE,
        ):
            found_in.append(candidate)
    assert found_in, (
        "writing-plans extension OR template must include 'close-phase Red/"
        "Green/Refactor' in per-phase steps. Searched: "
        + ", ".join(str(c.relative_to(_REPO_ROOT)) for c in extension_candidates)
    )


def test_d_three_touchpoint_consistency():
    """D-1+D-2+D-3 cross-check: all 3 touchpoints reference the same command literal."""
    skill_md = _REPO_ROOT / "skills" / "sbtdd" / "SKILL.md"
    template = _REPO_ROOT / "templates" / "CLAUDE.local.md.template"
    extension_candidates = [
        _REPO_ROOT / "templates" / "writing-plans-extension.md",
        _REPO_ROOT / "templates" / "plan-tdd-template.md",
    ]
    canonical_cmd = "python skills/sbtdd/scripts/run_sbtdd.py close-phase"
    skill_md_text = skill_md.read_text(encoding="utf-8")
    template_text = template.read_text(encoding="utf-8")
    assert canonical_cmd in skill_md_text or "close-phase" in skill_md_text, (
        "SKILL.md must reference the canonical close-phase command"
    )
    assert canonical_cmd in template_text or "close-phase" in template_text, (
        "CLAUDE.local.md.template must reference the canonical close-phase command"
    )
    # At least ONE of the extension candidates exists and references command
    extension_text_combined = ""
    for c in extension_candidates:
        if c.exists():
            extension_text_combined += c.read_text(encoding="utf-8")
    if extension_text_combined:
        assert canonical_cmd in extension_text_combined or "close-phase" in extension_text_combined, (
            "writing-plans extension must reference the canonical close-phase command"
        )
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_phase_subagent_pattern.py -v`
Expected: All FAIL — current SKILL.md / template / extension don't contain the per-phase mandate text.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [ ] **Step 4: Update SKILL.md with mandate**

Append to `skills/sbtdd/SKILL.md` an `### v1.0.4 close-phase per-phase mandate` section:

```markdown
### v1.0.4 close-phase per-phase mandate (Q3 Option B)

Subagents executing tasks under `subagent-driven-development` or
`executing-plans` MUST invoke
`python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each
Red/Green/Refactor verify-clean (i.e. once per TDD phase commit).

Manual `git commit` per phase BYPASSES the phase-advance + state-file
update + verification gate; treated as NON-CONFORMING and triggers
drift detection on the next `close-task`. v1.0.4 own-cycle dogfood
empirically demonstrated this gap (v1.0.3 subagents diverged from
the v1.0.2 Q2 Option B mandate by emitting raw `git commit`
instructions per phase).

The per-phase invocation:
1. Runs `/verification-before-completion` (sec.0.1: `pytest`,
   `ruff check .`, `ruff format --check .`, `mypy .`).
2. Creates atomic commit with the prefix from sec.5
   (`test:` / `feat:` / `fix:` / `refactor:`).
3. Updates `.claude/session-state.json` `current_phase` advance.

Plans generated by `/writing-plans` should emit per-phase close-phase
commands explicitly. Subagents reading raw `git commit` instructions
in plans pre-dating v1.0.4 should treat them as legacy; invoke
close-phase instead.
```

- [ ] **Step 5: Update `templates/CLAUDE.local.md.template` with mandate**

Append to `templates/CLAUDE.local.md.template` a section in §3 (TDD cycle) noting the per-phase close-phase mandate:

```markdown
### Per-phase commit protocol (v1.0.4 mandate)

Every Red/Green/Refactor phase commit MUST be created via
`python skills/sbtdd/scripts/run_sbtdd.py close-phase`, NOT via raw
`git commit`. Reasoning:

- close-phase runs `/verification-before-completion` BEFORE creating
  the commit, ensuring §0.1 is clean.
- close-phase advances `.claude/session-state.json` `current_phase`
  atomically with the commit.
- Manual `git commit` per phase BYPASSES both gates; treated as
  NON-CONFORMING and triggers drift detection on next `close-task`.

Subagents executing tasks under multi-agent dispatch (`subagent-driven-
development`, `executing-plans`, parallel `--parallel` flag) MUST
follow this protocol unconditionally. Empirically v1.0.3 cycle
surfaced this gap (subagents diverged from v1.0.2 Q2 Option B
mandate by emitting raw `git commit` steps); v1.0.4 elevates the
convention to plan template + writing-plans extension + this
template (3-touchpoint enforcement).
```

- [ ] **Step 6: Create or update writing-plans extension template**

If `templates/writing-plans-extension.md` does not exist, create it (small file documenting plan template format extension); otherwise append to existing template/SKILL.md.

Create `templates/writing-plans-extension.md`:

```markdown
# writing-plans skill prompt extension (v1.0.4 close-phase per-phase mandate)

When generating implementation plans for SBTDD projects, every TDD
step MUST emit per-phase close-phase commands instead of raw
`git commit`. Use this canonical step template:

```markdown
- [ ] **Step N (Red): Write failing test**

\`\`\`python
def test_specific_behavior():
    ...
\`\`\`

- [ ] **Step N+1: Run pytest -v, verify FAIL**

Run: \`pytest tests/path::test_name -v\`
Expected: FAIL with [reason]

- [ ] **Step N+2: close-phase Red**

Run: \`python skills/sbtdd/scripts/run_sbtdd.py close-phase\`

Expected: Red phase verify-clean confirms tests fail for the correct
reason (missing implementation, not import error). Atomic \`test:\`
commit landed. State file advances \`current_phase: red → green\`.
```

Repeat for Green (`close-phase Green` after impl + verify-clean) and
Refactor (`close-phase Refactor` after refactor + verify-clean).
After Refactor close-phase, invoke
`close-task --skip-spec-review` to mark task complete.

This pattern is mandatory for v1.0.4+ plans. Plans pre-dating v1.0.4
may use raw `git commit` syntax; subagents executing such plans
should still invoke close-phase instead per the v1.0.4 mandate
documented in `skills/sbtdd/SKILL.md` + `templates/CLAUDE.local.md.template`.
```

- [ ] **Step 7: Run tests to verify PASS**

Run: `pytest tests/test_close_phase_subagent_pattern.py -v`
Expected: 4/4 PASS.

Run: `make verify`
Expected: Clean.

- [ ] **Step 8: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `docs:` commit landed (e.g. `docs: mandate close-phase per-phase via 3-touchpoint v1.0.4 Item D`).

#### Refactor Phase

- [ ] **Step 9: Refactor — verify cross-touchpoint consistency**

Re-read SKILL.md + template + extension to confirm consistent wording. Adjust for clarity if needed.

- [ ] **Step 10: close-phase Refactor + Step 11: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

## Mid-cycle methodology activities (orchestrator)

These activities are NOT executed by Track Alpha or Track Beta
subagents. The orchestrator runs them sequentially as part of the
v1.0.4 own-cycle dogfood. Each is non-gating for ship per hybrid
methodology semantics.

### Activity E'-pre — `--resume-from-magi` happy path on hand-crafted artifacts (BEFORE Track dispatch)

**When**: After spec-behavior.md + plan-tdd-org.md committed
(this commit chain) and BEFORE dispatching Track Alpha + Track Beta
subagents.

**Steps**:

1. Pre-flight spec_lint dry-run:
   ```bash
   python skills/sbtdd/scripts/spec_lint.py sbtdd/spec-behavior.md
   python skills/sbtdd/scripts/spec_lint.py planning/claude-plan-tdd-org.md
   ```
2. Invoke `/sbtdd spec --resume-from-magi`:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
   ```
3. Observe:
   - Brainstorming/writing-plans subprocess NOT spawned.
   - MAGI Checkpoint 2 dispatched on hand-crafted artifacts.
   - INV-37 composite-signature check fires correctly.
   - Plan approval state file written on convergence.
4. Document in CHANGELOG `[1.0.4]` Process notes:
   - Wall-clock end-to-end.
   - INV-37 tripwire behavior.
   - Any unexpected interactions.

**Failure mode**: If `--resume-from-magi` fails on hand-crafted
artifacts (unexpected since artifacts pass spec_lint), fall back
to manual `run_magi.py` Checkpoint 2 dispatch per v1.0.2+v1.0.3
precedent. Document failure in CHANGELOG as v1.0.5 backlog.

### Activity D' retry — `/sbtdd pre-merge` end-to-end with SBTDD_INTERACTIVE=1 (AFTER Track close)

**When**: AFTER Track Alpha + Track Beta close + Items A+B fix
landed in working tree.

**Steps**:

1. Verify Items A+B fix landed:
   ```bash
   grep -n "_is_headless_context" skills/sbtdd/scripts/superpowers_dispatch.py
   grep -n "receiving-code-review" skills/sbtdd/scripts/superpowers_dispatch.py
   ```
2. Set `SBTDD_INTERACTIVE=1`:
   ```bash
   export SBTDD_INTERACTIVE=1  # POSIX
   $env:SBTDD_INTERACTIVE = "1"  # PowerShell
   ```
3. Run `/sbtdd pre-merge` end-to-end:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
4. Verify `/receiving-code-review` subprocess fires successfully.
5. Verify Loop 1 fix-finding triage step completes WITHOUT 600s
   hang.
6. Capture cross-check artifacts:
   ```bash
   ls .claude/magi-cross-check/iter*-*.json
   ```
7. Document findings in CHANGELOG `[1.0.4]` Process notes.

**Failure mode**: If Items A+B fix incomplete, document + retry.
Manual fallback `run_magi.py` direct dispatch + manual mini-cycle
commits preserves ship viability.

### Activity E'-post — `--resume-from-magi` post-impl smoke test (AFTER Activity D')

**When**: AFTER Activity D' retry.

**Steps**:

1. Pre-flight spec_lint dry-run (committed artifacts).
2. Invoke `/sbtdd spec --resume-from-magi` (post-impl).
3. Observe R10 commit-conflict + R4 autoregen interaction (likely
   N/A until v1.0.5).
4. Document observable gaps in CHANGELOG `[1.0.4]` Process notes.

**Failure mode**: Non-gating; document + roll forward to v1.0.5.

### Parallel dispatcher dogfood (chicken-and-egg, AFTER Track Beta close)

**When**: AFTER Track Beta lands Item C tests + impl + sequential
`make verify` clean.

**Steps**:

1. Confirm `dag_parser` + `parallel_dispatcher` ship tests green.
2. Identify v1.0.4 cycle's NEXT batch (e.g., CHANGELOG write +
   README update + version bump). If multi-task batch
   parallel-safe, dispatch via `--parallel`.
3. Document outcome in CHANGELOG `[1.0.4]` Process notes:
   - Wall-clock comparison vs sequential estimate.
   - Race conditions or state-file conflicts observed.
   - DAG parser correctness.

**Failure mode**: If dogfood surfaces blocking issue, fall back
to sequential dispatch + document as v1.0.5 refinement.

---

## Pre-merge gate (Loop 1 + Loop 2)

After all 9 plan tasks closed + 4 methodology activities executed:

1. Verify all checkboxes flipped:
   ```bash
   grep "- \[ \]" planning/claude-plan-tdd.md
   ```
   Expected: empty output.
2. Verify state file `current_phase: "done"`.
3. Verify `make verify` clean (pytest, ruff check, ruff format, mypy
   --strict, coverage >= 88%).
4. Run `/sbtdd pre-merge`:
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
5. Loop 1 (`/requesting-code-review`) iterates until clean-to-go.
6. Loop 2 (`/magi:magi`) iterates until verdict >= GO_WITH_CAVEATS
   full no-degraded.
7. Cross-check meta-reviewer artifacts captured under
   `.claude/magi-cross-check/`.

If Loop 2 iter 3 fails to converge, scope-trim per G2 binding
ladder (defer Item D first → Item C second → Items A+B hard-LOCKED).

---

## Finalization (post pre-merge gate clean)

1. Bump `plugin.json` + `marketplace.json` version 1.0.3 → 1.0.4.
2. Finalize CHANGELOG `[1.0.4]` with full ship record.
3. Update README + SKILL.md + CLAUDE.md with v1.0.4 release notes.
4. Run `make verify` final check.
5. Commit version bump as `chore: bump to 1.0.4 + finalize CHANGELOG`.
6. Tag `v1.0.4` (with explicit user authorization).
7. Merge `feature/v1.0.4-bundle` into `main` (with explicit user
   authorization).
8. Push tag + main to origin (with explicit user authorization).

---

## Plan invariants summary

- **9 plan tasks** distributed across 2 parallel subagent tracks
  (Track Alpha 5 tasks; Track Beta 4 tasks).
- **4 methodology activities** executed by orchestrator
  (E'-pre + D' retry + E'-post + parallel dogfood).
- **Per-phase close-phase mandate** (Q3 Option B) applied to ALL
  9 tasks via plan template (own-cycle dogfood ships the mandate).
- **Cero file overlap** between Track Alpha and Track Beta surfaces
  (verified in spec sec.5.4).
- **Tests baseline**: 1105 + 1 skipped → ~1140-1155 final.
- **Coverage threshold**: >= 88% (per Q4 v1.0.2 baseline).
- **`make verify` runtime**: <= 165s (NF-A); soft-target <= 155s.
- **MAGI Checkpoint 2**: cap=3 HARD G1 binding; iter-2 CRITICAL
  trigger preserved; G2 scope-trim ladder defers Item D first →
  Item C second; Items A+B hard-LOCKED.
- **No `Co-Authored-By`, no AI references, English commits, no
  force push** per `~/.claude/CLAUDE.md` Git rules.
