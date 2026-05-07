# v1.0.4 Real Headless Detection + Parallel Dispatcher + Close-phase Mandate Implementation Plan

> Generado 2026-05-07 a partir de sbtdd/spec-behavior.md v1.0.4 via
> superpowers:writing-plans skill (interactive session, brainstorming
> Q1+Q2+Q3+Q4+Q5 resolved). Frontmatter required by spec_lint R5
> (Item C v1.0.2 enforcement).
>
> v1.0.4 ships 2 pillars (post iter 2 scope-trim Option D 2026-05-07):
> Pillar A (Items A+B coupled subprocess-incompatible gate + 600s
> LOUD-FAST fix); Pillar B (Item C parallel task dispatcher with
> --parallel flag). **Pillar C (Item D) DEFERRED ENTIRELY to v1.0.5
> LOCKED** per spec sec.6.1 G2 ladder firing on iter 2 CRITICAL #3.
>
> **iter 1 triage applied 2026-05-07** (post Checkpoint 2 iter 1
> verdict GO_WITH_CAVEATS 3-0; 2 CRITICAL + 14 WARNING + 5 INFO):
> Task 2 ABSORBED into Task 1 (single set extension + tests after
> CRITICAL #1 simplification dropped helper). Task 3 simplified
> (membership + override gate; no env-var detection). Task 4
> recovery message simplified (no env-var formatting). Task 6
> dag_parser + code-fence-aware regex + iterative cycle detection
> (WARNING melchior + caspar). Task 7 deterministic sort + synthetic
> concurrent state-file write test (WARNING melchior + balthasar).
>
> **iter 2 surgical fixes + scope-trim applied 2026-05-07** (post
> Checkpoint 2 iter 2 verdict GO_WITH_CAVEATS 3-0; 3 CRITICAL + 11
> WARNING + 6 INFO; iter-2 CRITICAL trigger fired): Task 6
> _detect_cycle converted recursive DFS → iterative Kahn's (CRITICAL
> #1 surgical fix). Task 7 partition_by_collision sorts task IDs
> ascending before greedy packing (CRITICAL #2 surgical fix).
> **Task 9 DEFERRED ENTIRELY** per Option D (CRITICAL #3 + 3-agent
> WARNING about doc-only insufficiency). Activity D' retry drops
> SBTDD_INTERACTIVE=1 step.
>
> Effective task layout post-iter-2-trim: 7 active tasks (4 Alpha +
> 3 Beta). Task numbering preserved 1-9 with T2 ABSORBED + T9
> DEFERRED.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax (open + closed bracket forms) for tracking.

**Goal:** Ship v1.0.4 — eliminate `/receiving-code-review` interactive subprocess hang via subprocess-incompatible gate (membership + override semantics; pre-spawn block) coupled with 600s LOUD-FAST PreconditionError fix; codify multi-track parallel subagent pattern as plugin feature via `--parallel` flag on `/sbtdd auto`. **Item D (per-phase close-phase mandate + tripwire) DEFERRED ENTIRELY to v1.0.5 LOCKED** per iter 2 scope-trim Option D — v1.0.5 will ship Q3 OPTION A code-side enforcement architecture instead. 7 active plan tasks (T2 ABSORBED, T9 DEFERRED) across 2 parallel subagent tracks; 4 methodology activities (Activity E'-pre + Activity D' retry + Activity E'-post + parallel dispatcher dogfood) executed by orchestrator (last 2 demoted to BEST-EFFORT non-gating per iter 2 scope-trim).

**Architecture:** 2-track parallel dispatch with disjoint surfaces. Track Alpha (Items A+B coupled, 4 sequential tasks post-triage; T2 ABSORBED into T1) modifies `skills/sbtdd/scripts/superpowers_dispatch.py` + extends `tests/test_superpowers_dispatch.py` + `tests/test_invoke_skill_callsites_audit.py`. Track Beta (Item C only post iter 2 scope-trim, 3 tasks T6+T7+T8; T9 DEFERRED) creates `skills/sbtdd/scripts/dag_parser.py` + `skills/sbtdd/scripts/parallel_dispatcher.py` (NEW modules), modifies `skills/sbtdd/scripts/auto_cmd.py` + tests. **No Item D doc-only or tripwire modifications in v1.0.4** (deferred). Cero file overlap. Activities mid-cycle (E'-pre before Track dispatch; D' retry after Track close; E'-post + parallel dogfood best-effort) run in orchestrator session before pre-merge gate.

**State file write serialization**: Track Alpha owns Tasks 1-5 (sequential close, T2 ABSORBED no-op). Track Beta owns Tasks 6-8 (sequential close, T9 DEFERRED no-op). State file `current_task_id` advances 1 → 3 → 4 → 5 → 6 → 7 → 8 → done (skipping 2 ABSORBED + 9 DEFERRED). `state_file.save()` atomic `os.replace` (existing v0.5.0 pattern) ensures no partial writes. Concurrent close-task invocations against disjoint task IDs are safe per v0.4.0+v0.5.0+v1.0.0+v1.0.2+v1.0.3 precedent + v1.0.4 Task 7 synthetic concurrent test (iter 1 triage W6 fold-in).

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

### Task 1: Item A.1 — Extend `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + module docstring (iter 1 triage: ABSORBS T2)

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (extend frozenset + update module docstring with v1.0.4 audit history entry)
- Test: `tests/test_superpowers_dispatch.py` (extend with `class TestSubprocessIncompatibleSkillsExtended`)

Covers escenarios A-2, A-5 from spec sec.4.1 (post triage: A-3 + A-4 env-var escenarios DROPPED per CRITICAL #1+#2 simplification).

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestSubprocessIncompatibleSkillsExtended:
    """v1.0.4 Item A.1 escenarios A-2 + A-5 — set extension + docstring audit history (post iter 1 triage)."""

    def test_a5_receiving_code_review_in_incompatible_set(self):
        """A-5: receiving-code-review extended in v1.0.4."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "receiving-code-review" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_a5_brainstorming_writing_plans_preserved_v101(self):
        """A-5: v1.0.1 baseline (brainstorming, writing-plans) preserved."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert "brainstorming" in _SUBPROCESS_INCOMPATIBLE_SKILLS
        assert "writing-plans" in _SUBPROCESS_INCOMPATIBLE_SKILLS

    def test_a2_set_is_frozenset_immutable(self):
        """A-2: set is frozenset to prevent runtime mutation."""
        from superpowers_dispatch import _SUBPROCESS_INCOMPATIBLE_SKILLS

        assert isinstance(_SUBPROCESS_INCOMPATIBLE_SKILLS, frozenset)

    def test_a5_module_docstring_documents_audit_history(self):
        """A-5 doc-coherence: module docstring records v1.0.1 + v1.0.4 additions."""
        import superpowers_dispatch

        docstring = superpowers_dispatch.__doc__ or ""
        assert "v1.0.1" in docstring
        assert "brainstorming" in docstring
        assert "writing-plans" in docstring
        assert "v1.0.4" in docstring
        assert "receiving-code-review" in docstring

    def test_a5_module_docstring_documents_gate_semantics(self):
        """A-5 doc-coherence (post iter 1 triage): module docstring documents
        membership-based gate semantics (NOT env-var/isatty heuristic)."""
        import superpowers_dispatch

        docstring = superpowers_dispatch.__doc__ or ""
        assert "BLOCKED UNCONDITIONALLY" in docstring
        assert "allow_interactive_skill=True" in docstring
        assert "NO env-var/isatty heuristic" in docstring
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestSubprocessIncompatibleSkillsExtended -v`
Expected: receiving-code-review check FAILs (set not extended), docstring checks FAIL (module docstring doesn't yet have v1.0.4 entry or gate semantics block).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Red phase verify-clean confirms tests fail for the correct reason. Atomic `test:` commit landed. State file advances `current_phase: red → green`.

#### Green Phase

- [x] **Step 4: Extend the set + update module docstring**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py`:

```python
"""Dispatcher for invoking superpowers skills via claude -p subprocess.

...

Subprocess-incompatible skill audit history:
- v1.0.1 (Finding A discovery): brainstorming, writing-plans.
  Manifestation: silent no-op (subprocess returns without producing
  skill output). Caught post-spawn via INV-37 composite-signature
  check (v1.0.1 Item A0).
- v1.0.4 (v1.0.3 Activity D' empirical hang during Loop 1 fix-finding
  triage step): receiving-code-review. Manifestation: 600s subprocess
  hang waiting interactive input. Cannot be caught post-spawn
  (operator-blocking); requires pre-spawn gate.

A skill is subprocess-incompatible iff it requires multi-turn
interactive dialogue with the operator. Adding a new entry to the
set without empirical evidence (subprocess hang or silent-no-op
observed) is forbidden -- operators must run the skill manually in
interactive session and document the failure mode in CHANGELOG
before promoting.

Gate semantics (v1.0.4 post iter 1 triage): subprocess spawn for
incompatible skills is BLOCKED UNCONDITIONALLY unless caller passes
allow_interactive_skill=True. The override is the explicit opt-in
for known-safe wrappers that have arranged for subprocess success
(silent-no-op tolerated by v1.0.1 wrappers via INV-37 post-detection;
or operator-controlled interactive callsites). NO env-var/isatty
heuristic -- caspar Checkpoint 2 iter 1 CRITICAL verified the
heuristic does not fix the v1.0.3 bug in operator main sessions.
"""

_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset({
    "brainstorming",
    "writing-plans",
    "receiving-code-review",  # v1.0.4 added per v1.0.3 Activity D' dogfood
})
```

- [x] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestSubprocessIncompatibleSkillsExtended -v`
Expected: 5/5 PASS.

Run: `make verify`
Expected: Clean.

- [x] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `feat:` commit (e.g. `feat: extend _SUBPROCESS_INCOMPATIBLE_SKILLS for receiving-code-review (v1.0.4 Item A.1, T2 absorbed)`).

#### Refactor Phase

- [x] **Step 7: Refactor — no changes expected**

Set extension is minimal. Docstring documents audit history. Skip refactor.

- [x] **Step 8: close-phase Refactor (no-op or empty diff)**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

- [x] **Step 9: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 1 checkboxes flipped, `chore:` commit, state file advances `current_task_id: 1 → 3` (skipping ABSORBED Task 2).

---

### Task 2: ABSORBED INTO TASK 1 (iter 1 triage CRITICAL #1+#2; iter 2 confirmed)

**Status**: ABSORBED — no implementation work required.

iter 1 triage SIMPLIFIED Item A. Set extension that was Task 2's
scope is part of Task 1 Step 4. Subagents skip this header entirely;
orchestrator advances state file from `current_task_id: 1 → 3`
upon Task 1 close. No commits, no tests, no execution work for T2.

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

### Task 3: Item A.2 — Wire membership-based gate into `invoke_skill` + escenarios A-1 + A-3 + A-4 + A-5 (post iter 1 triage SIMPLIFIED)

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (`invoke_skill` function — add membership + override gate, NO env-var detection)
- Test: `tests/test_superpowers_dispatch.py` (add A-1, A-3, A-4, A-5 tests)

Covers escenarios A-1, A-3, A-4, A-5 from spec sec.4.1 (post triage: NO `_is_headless_context()` helper; gate is membership-based with `allow_interactive_skill` override).

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestInvokeSkillMembershipGate:
    """v1.0.4 Item A.2 escenarios A-1, A-3, A-4, A-5 — invoke_skill gate (post iter 1 triage)."""

    def test_a1_receiving_code_review_raises_unconditionally(self):
        """A-1: invoke_skill('receiving-code-review', ...) raises without override (any context)."""
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        with pytest.raises(PreconditionError) as exc_info:
            invoke_skill("receiving-code-review", "any prompt")
        assert "Skill `/receiving-code-review` cannot run via `claude -p` subprocess" in str(exc_info.value)
        assert "empirically incompatible" in str(exc_info.value)

    def test_a1_no_subprocess_spawned_when_blocked(self):
        """A-1: PreconditionError raised BEFORE subprocess spawn (no Popen call)."""
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        with patch("subprocess.run") as mock_run:
            with pytest.raises(PreconditionError):
                invoke_skill("receiving-code-review", "any prompt")
            mock_run.assert_not_called()

    def test_a3_allow_interactive_skill_bypasses_gate(self):
        """A-3: allow_interactive_skill=True bypasses gate (override active)."""
        from superpowers_dispatch import invoke_skill

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = invoke_skill(
                "receiving-code-review",
                "any prompt",
                allow_interactive_skill=True,
            )
            mock_run.assert_called_once()

    def test_a4_brainstorming_wrapper_backward_compat(self):
        """A-4: existing brainstorming wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import brainstorming

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = brainstorming("any prompt")
            mock_run.assert_called_once()

    def test_a4_writing_plans_wrapper_backward_compat(self):
        """A-4: existing writing_plans wrapper preserves v1.0.1 behavior."""
        from superpowers_dispatch import writing_plans

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = writing_plans("any prompt")
            mock_run.assert_called_once()

    def test_a5_skills_not_in_set_pass_through(self):
        """A-5: skills NOT in _SUBPROCESS_INCOMPATIBLE_SKILLS pass through."""
        from superpowers_dispatch import invoke_skill

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
            result = invoke_skill("systematic-debugging", "any prompt")
            mock_run.assert_called_once()

    def test_a1_gate_fires_in_tty_session(self):
        """A-1 (post iter 1 triage CRITICAL #1+#2): gate fires regardless of TTY state.
        This is the key fix vs caspar's CRITICAL — operator main session has TTY=True
        but gate must STILL fire to prevent v1.0.3 hang."""
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        with patch("sys.stdin") as mock_stdin:
            mock_stdin.isatty.return_value = True  # operator main session
            with pytest.raises(PreconditionError):
                invoke_skill("receiving-code-review", "any prompt")
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillMembershipGate -v`
Expected: 7/7 FAIL — invoke_skill currently does not check `_SUBPROCESS_INCOMPATIBLE_SKILLS` membership; PreconditionError not raised.

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `test:` commit landed.

#### Green Phase

- [x] **Step 4: Wire membership gate into `invoke_skill`**

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

    v1.0.4 Item A (post iter 1 triage SIMPLIFIED): pre-spawn
    membership gate. Subprocess-incompatible skills (in
    `_SUBPROCESS_INCOMPATIBLE_SKILLS`) are BLOCKED UNCONDITIONALLY
    unless caller passes `allow_interactive_skill=True`. When
    blocked, raises `PreconditionError` BEFORE subprocess.run is
    called, eliminating the v1.0.3 600s subprocess hang
    manifestation by construction.

    NO env-var/isatty heuristic per caspar Checkpoint 2 iter 1
    CRITICAL verification: TTY-based detection does NOT fix the
    v1.0.3 bug because operator main sessions have TTY=True (gate
    would not fire, subprocess would spawn, hang persists).

    Override hatch: `allow_interactive_skill=True` is the explicit
    opt-in for known-safe wrappers that have arranged for
    subprocess success (silent-no-op tolerated by v1.0.1 wrappers
    via INV-37 post-detection; or operator-controlled interactive
    callsites with inline rationale comment).

    Args:
        skill: Slash-command name (e.g., "receiving-code-review").
        prompt: Skill input.
        allow_interactive_skill: Bypass membership gate (default False).
        timeout: Subprocess timeout in seconds (default 600).
        output_dir: Optional directory for skill output artifacts.
        model: Optional model override (opus/sonnet/haiku).

    Returns:
        Subprocess stdout.

    Raises:
        PreconditionError: If skill is in incompatible set AND
            `allow_interactive_skill` is False.
        ...
    """
    if (
        skill in _SUBPROCESS_INCOMPATIBLE_SKILLS
        and not allow_interactive_skill
    ):
        raise PreconditionError(_build_recovery_message(skill))

    # ... existing subprocess.run path unchanged ...
```

For Task 3 implementation, `_build_recovery_message` will be a placeholder helper that returns a minimal string. Task 4 builds out the full per-skill recovery dictionary. Add the placeholder:

```python
def _build_recovery_message(skill: str) -> str:
    """Placeholder; full implementation in Task 4."""
    return (
        f"Skill `/{skill}` cannot run via `claude -p` subprocess "
        f"(empirically incompatible)."
    )
```

Also confirm wrappers `brainstorming` + `writing_plans` already pass `allow_interactive_skill=True` (they did in v1.0.1; if not, add):

```python
def brainstorming(prompt: str, ...) -> str:
    return invoke_skill("brainstorming", prompt, ..., allow_interactive_skill=True)


def writing_plans(prompt: str, ...) -> str:
    return invoke_skill("writing-plans", prompt, ..., allow_interactive_skill=True)
```

- [x] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillMembershipGate -v`
Expected: 7/7 PASS.

Run: `make verify`
Expected: Clean.

- [x] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: wire membership gate into invoke_skill (v1.0.4 Item A.2 post iter 1 triage)`).

#### Refactor Phase

- [x] **Step 7: Refactor — confirm wrappers + extract gate logic if duplicated**

If multiple wrappers will need `allow_interactive_skill=True`, no further refactor needed — kwarg already in place. If gate logic appears in 2+ places, extract to private helper. Likely YAGNI; skip.

- [x] **Step 8: Run tests to verify still PASS**

Run: `make verify`
Expected: Clean.

- [x] **Step 9: close-phase Refactor**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

- [x] **Step 10: close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

---

### Task 4: Item B — Build `_build_recovery_message` + `_PER_SKILL_RECOVERY` + escenarios B-1 + B-2 + B-3 (post iter 1 triage SIMPLIFIED)

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (replace placeholder + add `_PER_SKILL_RECOVERY` dict + `_GENERIC_RECOVERY` constant; helper renamed `_build_headless_recovery_message` → `_build_recovery_message` per iter 1 triage simplification)
- Test: `tests/test_superpowers_dispatch.py` (add B-1, B-2, B-3 tests)

Covers escenarios B-1, B-2, B-3 from spec sec.4.2 (post triage: env-var formatting tests B-1-env-var + B-1-isatty DROPPED per CRITICAL #1+#2 simplification).

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestBuildRecoveryMessage:
    """v1.0.4 Item B escenarios B-1, B-2, B-3 — recovery message (post iter 1 triage simplified)."""

    def test_b1_message_includes_recovery_options(self):
        """B-1: PreconditionError message includes recovery options."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("receiving-code-review")
        assert "Skill `/receiving-code-review` cannot run via `claude -p` subprocess" in msg
        assert "empirically incompatible" in msg
        assert "Run `/receiving-code-review` manually" in msg
        assert "python skills/magi/scripts/run_magi.py" in msg
        assert "spec sec.6.4" in msg
        assert "allow_interactive_skill=True" in msg

    def test_b2_per_skill_recovery_brainstorming(self):
        """B-2: brainstorming recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("brainstorming")
        assert "Run `/brainstorming` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_writing_plans(self):
        """B-2: writing-plans recovery references --resume-from-magi."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("writing-plans")
        assert "Run `/writing-plans` manually in interactive Claude Code session" in msg
        assert "/sbtdd spec --resume-from-magi" in msg

    def test_b2_per_skill_recovery_receiving_code_review(self):
        """B-2: receiving-code-review recovery references run_magi.py + sec.6.4."""
        from superpowers_dispatch import _build_recovery_message

        msg = _build_recovery_message("receiving-code-review")
        assert "Run `/receiving-code-review` manually in interactive session" in msg
        assert "skills/magi/scripts/run_magi.py code-review" in msg
        assert "spec sec.6.4" in msg

    def test_b2_unknown_skill_uses_generic_recovery(self):
        """B-2: unknown skill name falls back to generic recovery message."""
        from superpowers_dispatch import _build_recovery_message, _GENERIC_RECOVERY

        msg = _build_recovery_message("never-shipped-skill")
        for line in _GENERIC_RECOVERY.splitlines():
            line = line.strip()
            if line:
                assert line in msg, f"Generic recovery line missing: {line!r}"

    def test_b3_no_subprocess_when_blocked_under_one_second(self):
        """B-3: PreconditionError raised within 1 second (NOT 600s hang)."""
        import time
        from superpowers_dispatch import invoke_skill
        from errors import PreconditionError

        start = time.monotonic()
        with patch("subprocess.run") as mock_run:
            with pytest.raises(PreconditionError):
                invoke_skill("receiving-code-review", "any prompt")
            mock_run.assert_not_called()
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Expected <1s; took {elapsed:.2f}s"
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestBuildRecoveryMessage -v`
Expected: 6/6 FAIL — placeholder from Task 3 returns minimal string; per-skill dictionary not implemented.

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

#### Green Phase

- [x] **Step 4: Replace placeholder with full implementation (post iter 1 triage simplified, no env-var formatting)**

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


def _build_recovery_message(skill: str) -> str:
    """Construct the operator-facing recovery message for a blocked skill.

    v1.0.4 post iter 1 triage SIMPLIFIED: no env-var formatting
    (gate is membership-based, not heuristic-based — no env state
    to report).

    Args:
        skill: Slash-command name (e.g., "receiving-code-review").

    Returns:
        Multi-line operator-facing message including:
        - Reason (skill empirically incompatible)
        - Per-skill recovery options (or generic if skill unknown)
        - Override hint (allow_interactive_skill=True for known-safe
          callers).
    """
    per_skill = _PER_SKILL_RECOVERY.get(skill, _GENERIC_RECOVERY)
    return (
        f"Skill `/{skill}` cannot run via `claude -p` subprocess "
        f"(empirically incompatible: requires multi-turn interactive "
        f"dialogue or hangs > 600s). Recovery options:\n"
        f"{per_skill}\n"
        f"To override (only when caller has arranged interactive "
        f"completion path), pass `allow_interactive_skill=True` to "
        f"`invoke_skill(...)`."
    )
```

Confirm `from types import MappingProxyType` and `from typing import Mapping` are imported.

- [x] **Step 5: Run tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestBuildRecoveryMessage -v`
Expected: 6/6 PASS.

Run: `make verify`
Expected: Clean.

- [x] **Step 6: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: `feat:` commit landed (e.g. `feat: build per-skill headless recovery messages for v1.0.4 Item B`).

#### Refactor Phase

- [x] **Step 7: Refactor — extract message format string if reusable**

If recovery message format becomes verbose, extract template. Likely YAGNI; skip.

- [x] **Step 8: close-phase Refactor + Step 9: close-task**

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

### Task 6: Item C.1 — `dag_parser.py` module + escenarios C-1 + C-2 + C-3 + C-4 (iter 1 triage: code-fence-aware + iterative cycle detection)

**Files:**
- Create: `skills/sbtdd/scripts/dag_parser.py`
- Create: `tests/test_dag_parser.py`

Covers escenarios C-1, C-2, C-3, C-4 from spec sec.4.3.

**iter 1 triage fold-ins** (WARNING melchior #3 + caspar #5 + caspar #6):
- C-1: `_split_task_blocks` strips markdown code-fenced regions (delimited by triple backtick) BEFORE applying `_TASK_HEADER_RE`. Phantom task headers inside code fences (e.g., writing-plans extension template's literal `### Task N:` examples) MUST NOT be added to graph.
- C-3: cycle detection uses ITERATIVE Kahn's algorithm (or Tarjan with explicit stack) instead of recursive DFS. Eliminates Python recursion limit failure mode for plans with > 1000 dependency depth.
- New regression test: `parse_plan(planning/claude-plan-tdd.md)` returns exactly 8 tasks (T1..T9 minus ABSORBED T2), NOT 8 + phantoms-from-fences.

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


def test_c1_code_fence_aware_skips_phantom_headers(tmp_path: Path):
    """C-1 iter 1 triage WARNING (melchior + caspar): code-fenced ### Task N:
    examples MUST NOT pollute graph as phantom tasks."""
    plan = tmp_path / "plan.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: Real

        **Files:**
        - Modify: `real.py`

        Example template embedded in plan:

        ```markdown
        ### Task 99: Phantom

        **Files:**
        - Modify: `phantom.py`
        ```

        ### Task 2: AlsoReal

        **Files:**
        - Modify: `also_real.py`
        """))
    graph = parse_plan(plan)
    # Only T1 + T2 — phantom T99 inside fence MUST be skipped
    assert set(graph.tasks.keys()) == {"1", "2"}
    assert "99" not in graph.tasks


def test_c3_iterative_cycle_detection_no_recursion_limit(tmp_path: Path):
    """C-3 iter 1 triage WARNING (caspar): cycle detection iterative — no
    recursion limit failure for deep dependency chains."""
    plan_lines = ["# Deep chain plan"]
    # 1500 sequential tasks: each depends on the previous
    for i in range(1, 1501):
        plan_lines.append(f"\n### Task {i}: T{i}")
        plan_lines.append("\n**Files:**")
        plan_lines.append(f"- Modify: `t{i}.py`")
        if i > 1:
            plan_lines.append(f"\n**Depends on**: Task {i - 1}")
    plan = tmp_path / "deep.md"
    plan.write_text("\n".join(plan_lines))
    # Recursive DFS would hit Python recursion limit (default 1000).
    # Iterative algorithm must succeed without RecursionError.
    graph = parse_plan(plan)
    assert len(graph.tasks) == 1500
    chains = graph.antichains()
    # Linear chain: 1500 antichains, one task each
    assert len(chains) == 1500


def test_c3_iterative_cycle_detection_self_loop(tmp_path: Path):
    """C-3 iter 1 triage: self-loop is a cycle — iterative algorithm detects."""
    plan = tmp_path / "self.md"
    plan.write_text(textwrap.dedent("""\
        ### Task 1: SelfLoop

        **Files:**
        - Modify: `self.py`

        **Depends on**: Task 1
        """))
    with pytest.raises(ValidationError) as exc_info:
        parse_plan(plan)
    msg = str(exc_info.value).lower()
    assert "cycle" in msg or "cyclic" in msg
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


_CODE_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


def _strip_code_fences(plan_text: str) -> str:
    """Replace markdown code-fenced regions with blank lines preserving line numbers.

    Per iter 1 triage WARNING #3+#15 + iter 2 verification: ### Task N:
    headers inside code fences are EXAMPLES (e.g., writing-plans extension
    template) and MUST NOT pollute the graph as phantom tasks. Replace
    fenced regions with same number of blank lines so byte offsets used
    by downstream regexes remain stable.
    """
    def _replace(match: re.Match[str]) -> str:
        return "\n" * match.group(0).count("\n")
    return _CODE_FENCE_RE.sub(_replace, plan_text)


def _split_task_blocks(plan_text: str) -> list[tuple[str, str, str]]:
    """Split plan text into (task_id, title, body) tuples.

    Returns one entry per ### Task N: block, with body containing
    everything from the header up to (but not including) the next
    ### Task N: header or end-of-file. Code-fenced regions are
    stripped before regex application (iter 1 triage WARNING #3+#15).
    """
    cleaned = _strip_code_fences(plan_text)
    headers = list(_TASK_HEADER_RE.finditer(cleaned))
    if not headers:
        return []
    blocks: list[tuple[str, str, str]] = []
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(cleaned)
        body = cleaned[start:end]
        blocks.append((m.group(1), m.group(2).strip(), body))
    return blocks


def _detect_cycle(edges: dict[str, set[str]]) -> list[str] | None:
    """Return cycle path if found, else None.

    iter 1 triage WARNING #16 + iter 2 CRITICAL #1 fix: ITERATIVE
    Kahn's algorithm. Nodes whose dependencies are all completed get
    removed from the graph progressively; any node never removed
    participates in a cycle. Eliminates Python recursion limit failure
    mode for plans with > 1000 dependency depth.
    """
    in_degree: dict[str, int] = {node: 0 for node in edges}
    for node, deps in edges.items():
        for dep in deps:
            in_degree.setdefault(dep, 0)
    for node, deps in edges.items():
        for _ in deps:
            in_degree[node] = in_degree.get(node, 0) + 1

    queue = [node for node, deg in in_degree.items() if deg == 0]
    completed: set[str] = set()
    while queue:
        node = queue.pop(0)
        completed.add(node)
        # When `node` completes, every dependent of `node` (i.e., every
        # X where `node` in edges[X]) loses one inbound edge.
        for x, deps in edges.items():
            if node in deps and x not in completed and x not in queue:
                in_degree[x] -= 1
                if in_degree[x] == 0:
                    queue.append(x)

    leftover = set(in_degree.keys()) - completed
    if not leftover:
        return None
    # Reconstruct cycle path by following edges from any leftover node.
    start = sorted(leftover)[0]
    path: list[str] = [start]
    seen: set[str] = {start}
    current = start
    while True:
        next_nodes = [d for d in edges.get(current, set()) if d in leftover]
        if not next_nodes:
            return path
        nxt = sorted(next_nodes)[0]
        if nxt in seen:
            cycle_start = path.index(nxt)
            return path[cycle_start:] + [nxt]
        path.append(nxt)
        seen.add(nxt)
        current = nxt


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

### Task 7: Item C.2 — `parallel_dispatcher.py` module + escenarios C-5 + C-6 + C-10 + C-11 (iter 1 triage: deterministic sort + concurrent test)

**Files:**
- Create: `skills/sbtdd/scripts/parallel_dispatcher.py`
- Create: `tests/test_parallel_dispatcher.py`

Covers escenarios C-5, C-6, C-10, C-11 from spec sec.4.3.

**iter 1 triage fold-ins** (WARNING melchior #4 + melchior #7 + balthasar #4):
- C-10: `partition_by_collision` SORTS task IDs ascending before greedy first-fit packing — deterministic output regardless of Python set iteration order.
- C-11: synthetic concurrent state-file write race test using `multiprocessing.Process` with shared barrier; asserts final state file is consistent (one of expected states, never partial-merge nor corrupt JSON). State-file serialization via `parallel_dispatcher` queueing OR `fcntl.flock` (POSIX) / `msvcrt.locking` (Windows) wrapper.

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


def test_c6_partial_collision_groups_deterministic():
    """C-6 + C-10 (iter 1 triage): 1+2 collide on a.py; 3 disjoint.
    Ascending-id sort + greedy first-fit → exact batches [{1, 3}, {2}]."""
    graph = _make_graph({
        "1": {"a.py"},
        "2": {"a.py"},
        "3": {"b.py"},
    })
    batches = partition_by_collision({"1", "2", "3"}, graph)
    # Deterministic: sorted ids → "1" packed first with disjoint "3";
    # "2" left over (collides with "1" on a.py).
    assert batches == [{"1", "3"}, {"2"}]


def test_c10_partition_deterministic_across_invocations():
    """C-10 iter 1 triage: same input MUST produce same output across calls
    (eliminates Python set iteration order dependency)."""
    graph = _make_graph({
        "1": {"x.py"},
        "2": {"y.py"},
        "3": {"x.py"},
        "4": {"z.py"},
    })
    # Run twice; results must be byte-identical
    batches_1 = partition_by_collision({"1", "2", "3", "4"}, graph)
    batches_2 = partition_by_collision({"1", "2", "3", "4"}, graph)
    assert batches_1 == batches_2
    # Pin canonical ordering: ascending-id greedy fit
    assert batches_1 == [{"1", "2", "4"}, {"3"}]


def test_c11_synthetic_concurrent_state_file_write(tmp_path):
    """C-11 iter 1 triage: synthetic concurrent state-file write race.

    Two processes call state_file.save() simultaneously against
    disjoint task IDs. Final file must parse as valid JSON and
    match one of the expected states (never partial-merge).
    """
    import json
    import multiprocessing
    from state_file import save, SessionState  # adjust import path as needed

    state_path = tmp_path / "session-state.json"
    state_path.write_text(json.dumps({"current_task_id": "0", "current_phase": "red"}))

    def writer(task_id: str, barrier: multiprocessing.Barrier) -> None:
        barrier.wait()  # synchronize start
        new_state = SessionState(current_task_id=task_id, current_phase="green")
        save(state_path, new_state)

    barrier = multiprocessing.Barrier(2)
    procs = [
        multiprocessing.Process(target=writer, args=(tid, barrier))
        for tid in ("5", "6")
    ]
    for p in procs:
        p.start()
    for p in procs:
        p.join()

    # File must exist and parse cleanly
    text = state_path.read_text()
    parsed = json.loads(text)  # must NOT raise
    # Final state must be one of the writers' states (never partial-merge)
    assert parsed.get("current_task_id") in {"5", "6"}
    assert parsed.get("current_phase") == "green"


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

    iter 1 triage WARNING #7 + iter 2 CRITICAL #2 fix: input task IDs
    are SORTED ASCENDING before greedy first-fit packing -- output is
    deterministic regardless of Python set iteration order.

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
    remaining = sorted(antichain)  # iter 2 CRITICAL #2 fix: deterministic order
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

### Task 9: Item D — DEFERRED ENTIRELY to v1.0.5 (iter 2 scope-trim Option D)

**Status**: DEFERRED — no v1.0.4 implementation work. Subagents skip this header entirely; orchestrator advances state file from `current_task_id: 8 → done` upon Task 8 close (no T9 work to perform).

**Rationale (iter 2 Checkpoint 2 scope-trim per spec sec.6.1 G2 ladder)**: iter 2 surfaced 3 CRITICAL findings; caspar CRITICAL #3 ("§3 cross-module contract contradicts §2.4 + plan T9") + persistent 3-agent WARNING (melchior + balthasar + caspar) about Item D 3-touchpoint doc-only enforcement INSUFFICIENCY (third consecutive cycle of doc-only convention attempts: v1.0.2 Q2 Option B I5 process notes; v1.0.3 dogfood demonstrated divergence; v1.0.4 attempted 3-touchpoint multiplication + tripwire fold-in). Per spec sec.6.1 iter-2 CRITICAL trigger pre-stage: scope-trim ladder defers Item D first. User selected Option D (hybrid: surgical fixes for #1+#2 + scope-trim Item D for #3) on 2026-05-07.

**v1.0.5 LOCKED commitment**: Item D ships as **Q3 OPTION A** — code-side enforcement via `close_task_cmd._preflight` modification. Architectural preference confirmed by 3-agent unanimous flag in v1.0.4 iter 1 + iter 2. NOT doc-only multiplication. Specifics deferred to v1.0.5 brainstorming + plan.

**v1.0.4 surfaces NOT touched in this cycle**:
- `skills/sbtdd/SKILL.md` — unchanged in v1.0.4.
- `templates/CLAUDE.local.md.template` — unchanged in v1.0.4.
- writing-plans skill prompt extension — unchanged / NOT created in v1.0.4.
- `skills/sbtdd/scripts/close_task_cmd.py` — unchanged in v1.0.4.
- `tests/test_close_phase_subagent_pattern.py` — NOT created in v1.0.4.
- `tests/test_close_task_cmd.py` — no D-4 tripwire test in v1.0.4.

The Q2 v1.0.2 Option B `/sbtdd close-task` automation mandate (single I5 touchpoint) remains in force unchanged. v1.0.5 will replace this with code-side enforcement.

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

### Activity D' retry — `/sbtdd pre-merge` end-to-end (AFTER Track close, post iter 1+2 triage)

**When**: AFTER Track Alpha + Track Beta close + Items A+B fix
landed in working tree.

**Steps (post iter 1 triage CRITICAL #2 fix — drop SBTDD_INTERACTIVE step)**:

1. Verify Items A+B fix landed:
   ```bash
   grep -n "_SUBPROCESS_INCOMPATIBLE_SKILLS" skills/sbtdd/scripts/superpowers_dispatch.py
   grep -n "receiving-code-review" skills/sbtdd/scripts/superpowers_dispatch.py
   ```
   Expected: set membership extended to include `receiving-code-review`.
   NO `_is_headless_context` helper present (iter 1 simplification).
2. Run `/sbtdd pre-merge` end-to-end (NO env var setup; gate fires
   unconditionally for incompatible skills):
   ```bash
   python skills/sbtdd/scripts/run_sbtdd.py pre-merge
   ```
3. Verify `/receiving-code-review` subprocess invocation by
   `pre_merge_cmd` raises `PreconditionError` PRE-spawn (Items A+B
   fix validates here — gate fires by construction).
4. Operator manually runs `/receiving-code-review` skill via
   interactive Claude Code session per the recovery message
   guidance, applies findings + mini-cycle TDD fixes, then resumes
   `/sbtdd pre-merge` (re-invoke).
5. Verify Loop 1 fix-finding triage step completes WITHOUT 600s
   hang (PreconditionError raised in <1s + manual recovery).
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

After all 7 active plan tasks (T2 ABSORBED, T9 DEFERRED post iter 2 scope-trim) closed + 4 methodology activities executed (last 2 best-effort non-gating):

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

- **7 active plan tasks** (post iter 2 scope-trim Option D): T2
  ABSORBED into T1 (iter 1 triage); T9 DEFERRED entirely to v1.0.5
  (iter 2 scope-trim). Track Alpha 4 active tasks (T1, T3, T4, T5);
  Track Beta 3 active tasks (T6, T7, T8).
- **4 methodology activities** executed by orchestrator (E'-pre +
  D' retry + E'-post + parallel dogfood); last 2 demoted to
  BEST-EFFORT non-gating per iter 2 scope-trim.
- **Per-phase close-phase mandate** (Q3 Option B) applied to all
  7 active tasks via plan template (own-cycle dogfood). Note: Q3
  Option B's broader doc-only enforcement scope (Item D in SKILL.md
  + template + extension) is DEFERRED to v1.0.5; v1.0.4 cycle just
  uses close-phase per-phase locally without shipping the convention
  enforcement to destination projects.
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


## MAGI Conditions for Approval

- Spec+plan are technically sound post-iter-2 scope-trim, but residual Item-D references and an outdated risk register create ship-time confusion that warrants surgical fixes before iter-3 lock-in.
- Pragmatic GO_WITH_CAVEATS — scope-trim correctly applied, Items A+B+C deliverable, but plan has stale Track Beta scope text and dogfood methodology has chicken-and-egg risks worth flagging.
- Task 2 phantom checkboxes will fork subagent execution; Track Beta scope + risk register stale post iter-2 trim — surgical fixes required pre-dispatch