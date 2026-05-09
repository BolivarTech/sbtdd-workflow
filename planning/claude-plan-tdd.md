# v1.0.6 Operational Unblock + Polish Implementation Plan

> Generado 2026-05-09 a partir de sbtdd/spec-behavior.md v1.0.6 via
> superpowers:writing-plans skill (interactive session, brainstorming
> Q1'-Q5' resolved). Frontmatter required by spec_lint R5.
>
> v1.0.6 ships 2 focused pillars:
> - Pillar A PRIMARY (LOCKED CRITICAL): J-1+J-2+J-3 subprocess hang
>   fix via real headless detection (SBTDD_HEADLESS env var +
>   os.isatty(0) fallback)
> - Pillar B LOCKED (LOW-RISK polish carry-forward): C.2 plan
>   archaeology trim methodology + K-1..K-5 cherry-picked Loop 2
>   v1.0.5 iter-1 polish WARNINGs
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use markdown checkbox syntax for tracking.

**Goal:** Ship v1.0.6 — close v1.0.4 J-class LOCKED commitment (subprocess hang fix via real headless detection) deferred via v1.0.5 + ship Pillar B C.2 plan archaeology trim methodology (carry-forward from v1.0.5 iter-2 G2 ladder defer) + 5 cherry-picked v1.0.5 Loop 2 iter-1 polish WARNINGs (K-1..K-5). 7 plan tasks; v1.0.6 own-cycle uses `auto --parallel` self-dispatch dogfood (Q1'=c) to validate v1.0.5 production-grade `--parallel` end-to-end.

**Architecture:** Pillar A (T1) introduces `subprocess_utils.is_headless_context() -> bool` consolidating SBTDD_HEADLESS env var + os.isatty(0) fallback; enforced at `superpowers_dispatch.invoke_skill` + `magi_dispatch.py` callsites for skills in `_SUBPROCESS_INCOMPATIBLE_SKILLS`. Headless context refusal cannot be overridden (subprocess will hang silently). Pillar B (T2-T7) is doc methodology (T2) + 5 polish items touching `close_task_cmd.py` + `commits.py` + `auto_cmd.py`. Runtime partition computed by `partition_by_tracks` into 4 disjoint tracks (Track A={T1}, Track B={T3,T5,T7}, Track C={T4,T6}, Track D={T2}).

**Tech Stack:** Python >= 3.9, pytest, pytest-cov, ruff, mypy --strict, stdlib-only on hot paths. TDD-Guard active. Brainstorming Q-decisions: Q1=B operational unblock + polish; Q2=a real headless detection; Q3=a strict no-INV-0; Q1'=c auto --parallel self-dispatch; Q2'=a env var truthy exact list 1/true/yes; Q3'=a K-3 1-cycle deprecation alias; Q4'=b liberal CC scope regex; Q5'=a default G2 ladder.

**Iter 1 Checkpoint 2 triage applied 2026-05-09** (verdict GO_WITH_CAVEATS 3-0, 0 CRITICAL + 14 WARNING + 6 INFO; no scope-trim required). Plan deltas inlined per task; full triage rationale in `sbtdd/spec-behavior.md` header:
- T1: K-4 loud-fast guard (mel+bal+cas TRIPLE) — remove try/except wrap; ValidationError unconditionally fatal at module import. NOTE: K-4 is in T6, not T1; reference here for cross-cuts.
- T3 (K-1): line-anchored regex `^- \[x\]` / `^- \[ \]` (mel WARNING) + 2 race regression tests (bal WARNING).
- T6 (K-4): loud-fast guard + private-attribute documentation acknowledgment.
- T7 (K-5): regex extended to `^([a-z]+)(?:\([^()]+\))?!?:(?:\s|$)` for CC `!` breaking-marker + colon-without-trailing-space (mel+cas WARNING). Docstring tightened "extraction is NOT validation" (bal+cas).
- T4 cross-track ordering RELAXED (bal WARNING): late-import resolves at call-time; T4 can run truly parallel with Track B. Plan invariants block updated.
- T5 (K-3): alias identity test relaxed to module-load-time only (cas WARNING).
- F-A2 dogfood: explicit abort criteria + worker headless audit documented (bal INFO + cas WARNING).

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-09`.
- **Phase close protocol (Q3 Option B v1.0.4 mandate + v1.0.5 Item D Q3-A HARD-BLOCK enforced)**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-phase` after each Red/Green/Refactor verify-clean. Manual `git commit` per phase BYPASSES the phase-advance + state-file update + verification gate; **close-task HARD-BLOCKS via `_preflight_triplet_check` (renamed to `_preflight` post-K-3) when commit chain since last `chore: mark task` lacks the canonical TDD triplet**. Override available via `--skip-preflight` (audit-logged to stderr; emergency only).
- **Task close protocol**: subagents MUST invoke `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review` after Refactor close-phase. Use `--skip-spec-review` to bypass INV-31 spec-reviewer dispatch (~1-2 min/task overhead acceptable but not required for these infrastructure items).
- **Within-track sequential ordering**: Track B (T3 → T5 → T7 sequential, all touch `close_task_cmd.py`); Track C (T4 → T6 sequential, both touch `auto_cmd.py`). Tracks A + D run independently (file-disjoint with all others).
- **Cross-track import dependency (v1.0.5 carry-forward, iter-1 bal WARNING relaxation)**: T4 (K-2 in `auto_cmd.py:_dispatch_tracks_concurrent`) imports `_merge_scratch_plans` from `close_task_cmd` via late-import inside function body. After K-2 lands, the v1.0.5 `getattr` noop fallback is removed. **T4 can run truly parallel with Track B (T3+T5+T7)** because the import resolves at CALL-TIME (when `_dispatch_tracks_concurrent` is invoked), NOT at module-load-time. `_merge_scratch_plans` already ships in v1.0.5 — no missing-helper risk during impl. (Pre-iter-1 plan over-stated this dependency; relaxed per bal WARNING #6.)
- INV-37 composite-signature tripwire preserved unchanged.
- Item C v1.0.2 spec_lint gate (R1-R5) preserved unchanged.
- v1.0.4 Items A+B membership-based subprocess gate preserved + EXTENDED with v1.0.6 J-3 headless guard.
- v1.0.4 Path 3 `--parallel` architecture (`partition_by_tracks` + `_dispatch_tracks_concurrent` + `--task-ids` + `--no-recursive`) preserved unchanged. v1.0.6 EXERCISES it via Q1'=c self-dispatch dogfood.
- v1.0.5 per-worker sidecar (I-1) + scratch (I-2) + flag forwarding (I-3) patterns preserved unchanged. v1.0.6 K-2 removes the `getattr` noop fallback that was defensive scaffolding for v1.0.5 Track Alpha → Track Beta cross-track import dependency.

**Commit prefix map per phase** (from `CLAUDE.local.md` §5):

| Phase | Prefix | Closer |
|-------|--------|--------|
| Red (failing test) | `test:` | `close-phase` |
| Green (impl) | `feat:` (new module/feature) or `fix:` (bug fix) | `close-phase` |
| Refactor | `refactor:` | `close-phase` |
| Task close | `chore:` (automated) | `close-task --skip-spec-review` |

---

## Track A — J-1+J-2+J-3 Real headless detection (Subagent #1, single task T1)

**Owner**: Subagent #1 dispatched from orchestrator (or `auto --parallel` worker per Q1'=c).
**Surfaces** (cero overlap with Track B + Track C + Track D):
- Modify: `skills/sbtdd/scripts/subprocess_utils.py` (new `is_headless_context()` helper)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (`invoke_skill` headless guard)
- Modify: `skills/sbtdd/scripts/magi_dispatch.py` (analogous guard)
- Extend: `tests/test_subprocess_utils.py` + `tests/test_superpowers_dispatch.py`

**Wall-time estimated**: ~0.5 day.

### Task 1: J-1+J-2+J-3 unified — Real headless detection helper + invoke_skill guard

**Files:**
- Modify: `skills/sbtdd/scripts/subprocess_utils.py` (add `is_headless_context()` module-level helper)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py` (add headless guard after membership check)
- Modify: `skills/sbtdd/scripts/magi_dispatch.py` (add analogous guard if MAGI dispatches interactive skills)
- Modify: `tests/test_subprocess_utils.py` (extend with `TestIsHeadlessContext` class)
- Modify: `tests/test_superpowers_dispatch.py` (extend with `TestInvokeSkillHeadlessGuard` class)

Covers escenarios J-1 through J-10 from spec sec.4.1+4.2.

#### Red Phase

- [x] **Step 1: Write the failing tests for `is_headless_context()` helper**

Append to `tests/test_subprocess_utils.py`:

```python
class TestIsHeadlessContext:
    """v1.0.6 J-1+J-2: real headless detection helper.

    Covers escenarios J-1 through J-5 from spec sec.4.1.
    """

    def test_j1_env_var_truthy_returns_headless(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """J-1: SBTDD_HEADLESS=1 returns True regardless of stdin TTY."""
        from subprocess_utils import is_headless_context

        for value in ("1", "true", "TRUE", "yes", "Yes", "YES", "True"):
            monkeypatch.setenv("SBTDD_HEADLESS", value)
            assert is_headless_context() is True, f"value={value!r} should return True"

    def test_j2_env_var_falsy_tty_returns_interactive(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-2: env var unset/falsy + TTY stdin returns False (interactive)."""
        from subprocess_utils import is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        # Mock sys.stdin.isatty() to return True
        import sys
        class FakeStdin:
            def isatty(self) -> bool:
                return True
        monkeypatch.setattr(sys, "stdin", FakeStdin())
        assert is_headless_context() is False

    def test_j3_env_var_falsy_non_tty_returns_headless(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-3: env var unset + non-TTY stdin returns True (implicit headless)."""
        from subprocess_utils import is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        import sys
        class FakeStdin:
            def isatty(self) -> bool:
                return False
        monkeypatch.setattr(sys, "stdin", FakeStdin())
        assert is_headless_context() is True

    def test_j4_isatty_exception_returns_headless_defensively(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-4: OSError or AttributeError on isatty() returns True (defensive)."""
        from subprocess_utils import is_headless_context

        monkeypatch.delenv("SBTDD_HEADLESS", raising=False)
        import sys
        class FakeStdin:
            def isatty(self) -> bool:
                raise OSError("closed stdin")
        monkeypatch.setattr(sys, "stdin", FakeStdin())
        assert is_headless_context() is True

        class FakeStdinNoIsatty:
            pass  # no isatty attribute
        monkeypatch.setattr(sys, "stdin", FakeStdinNoIsatty())
        assert is_headless_context() is True

    def test_j5_env_var_values_not_in_truthy_set_are_falsy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-5: 'on', 'enabled', 'y', etc. are FALSY per Q2'=a exact list."""
        from subprocess_utils import is_headless_context

        # TTY stdin so falsy env var → interactive
        import sys
        class FakeStdin:
            def isatty(self) -> bool:
                return True
        monkeypatch.setattr(sys, "stdin", FakeStdin())

        for value in ("on", "enabled", "y", "t", "0", "false", "no", ""):
            monkeypatch.setenv("SBTDD_HEADLESS", value)
            assert is_headless_context() is False, f"value={value!r} should be FALSY (Q2'=a)"

    def test_j5b_env_var_whitespace_stripped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-5b: leading/trailing whitespace stripped before truthy check."""
        from subprocess_utils import is_headless_context

        for value in ("  1  ", "\ttrue\t", " yes\n"):
            monkeypatch.setenv("SBTDD_HEADLESS", value)
            assert is_headless_context() is True, f"value={value!r} should strip"
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_subprocess_utils.py::TestIsHeadlessContext -v`
Expected: 6/6 FAIL — `is_headless_context` doesn't exist yet (`ImportError`).

- [x] **Step 3: Write the failing tests for `invoke_skill` headless guard**

Append to `tests/test_superpowers_dispatch.py`:

```python
class TestInvokeSkillHeadlessGuard:
    """v1.0.6 J-3: invoke_skill refuses headless dispatch for incompatible skills.

    Covers escenarios J-6 through J-10 from spec sec.4.2.
    """

    def test_j6_invoke_skill_refuses_headless_with_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-6: allow_interactive_skill=True + headless context = REFUSE."""
        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        monkeypatch.setattr("superpowers_dispatch.subprocess_utils.is_headless_context", lambda: True)

        with pytest.raises(PreconditionError) as excinfo:
            invoke_skill("receiving-code-review", "test prompt", allow_interactive_skill=True)
        msg = str(excinfo.value)
        assert "Cannot dispatch interactive skill" in msg
        assert "context is headless" in msg
        assert "receiving-code-review" in msg
        # Recovery message included
        assert "run_magi.py" in msg or "Recovery" in msg

    def test_j7_invoke_skill_allows_interactive_with_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-7: allow_interactive_skill=True + interactive TTY = dispatch normally."""
        from superpowers_dispatch import invoke_skill

        monkeypatch.setattr("superpowers_dispatch.subprocess_utils.is_headless_context", lambda: False)
        # Mock subprocess dispatch so we don't actually spawn claude
        called: dict[str, object] = {}

        def fake_dispatch(*args: object, **kwargs: object) -> str:
            called["dispatched"] = True
            return "fake-output"

        monkeypatch.setattr("superpowers_dispatch._dispatch_via_subprocess", fake_dispatch)

        result = invoke_skill("receiving-code-review", "test prompt", allow_interactive_skill=True)
        assert called.get("dispatched") is True
        assert result == "fake-output"

    def test_j8_invoke_skill_blocks_default_no_override_regardless_of_context(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """J-8: no override → membership check fires first; headless check NOT consulted."""
        from errors import PreconditionError
        from superpowers_dispatch import invoke_skill

        # Even with interactive TTY, default behavior is REFUSE for incompatible skill
        monkeypatch.setattr("superpowers_dispatch.subprocess_utils.is_headless_context", lambda: False)

        with pytest.raises(PreconditionError) as excinfo:
            invoke_skill("brainstorming", "test prompt")
        msg = str(excinfo.value)
        # v1.0.4 recovery message (no "Cannot dispatch...headless" prefix since membership check fires first)
        assert "brainstorming" in msg
        assert "Cannot dispatch interactive skill" not in msg, "headless check should not fire when membership check already blocks"
```

- [x] **Step 4: Run tests to verify FAIL**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillHeadlessGuard -v`
Expected: 3/3 FAIL — `invoke_skill` doesn't have headless guard yet (raises wrong message OR proceeds when it shouldn't).

- [x] **Step 5: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit (e.g. `test: v1.0.6 T1 J-1+J-2+J-3 real headless detection - failing tests`).

#### Green Phase

- [x] **Step 6: Implement `is_headless_context()` helper in `subprocess_utils.py`**

Add to top of `skills/sbtdd/scripts/subprocess_utils.py` after existing imports (need to add `import os` if not present):

```python
import os  # v1.0.6 J-1: env var lookup
```

Append at module level (after existing helpers):

```python
def is_headless_context() -> bool:
    """v1.0.6 J-1+J-2: detect headless execution context.

    Returns True when:

    * ``SBTDD_HEADLESS`` env var truthy (``"1"``, ``"true"``, ``"yes"``
      case-insensitive per Q2'=a) -- explicit headless declaration
      by operator or CI runner.
    * ``sys.stdin.isatty()`` returns False -- implicit headless
      (subprocess of subprocess, piped invocation, CI runner without
      explicit env var).
    * ``OSError`` or ``AttributeError`` raised by ``isatty()`` --
      defensive default (assume headless when uncertain).

    Returns False when stdin IS a TTY AND env var unset/falsy --
    interactive Claude Code session, allow normal subprocess dispatch.

    Used by :func:`superpowers_dispatch.invoke_skill` (and
    analogous callsites in :mod:`magi_dispatch`) to refuse subprocess
    dispatch for skills in ``_SUBPROCESS_INCOMPATIBLE_SKILLS`` when
    the context cannot support the interactive prompts that those
    skills require.
    """
    explicit = os.environ.get("SBTDD_HEADLESS", "").strip().lower()
    if explicit in {"1", "true", "yes"}:
        return True
    try:
        return not sys.stdin.isatty()
    except (OSError, AttributeError):
        # Closed stdin or unusual environment -> assume headless defensively
        return True
```

- [x] **Step 7: Run subprocess_utils tests to verify PASS**

Run: `pytest tests/test_subprocess_utils.py::TestIsHeadlessContext -v`
Expected: 6/6 PASS.

- [x] **Step 8: Implement `invoke_skill` headless guard in `superpowers_dispatch.py`**

Modify `skills/sbtdd/scripts/superpowers_dispatch.py:invoke_skill`. Find the existing membership check (around line 336-337):

```python
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
        raise PreconditionError(_build_recovery_message(skill))
```

Add the new headless guard immediately after (preserves v1.0.4 contract — membership check fires first when no override; headless check fires only when operator opted in):

```python
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
        raise PreconditionError(_build_recovery_message(skill))
    # v1.0.6 J-3: even when operator opts in via allow_interactive_skill=True,
    # subprocess dispatch will hang silently if context is headless (env var
    # SBTDD_HEADLESS=1 set OR stdin is not a TTY). Refuse LOUD-FAST -- operator
    # opt-in cannot make subprocess work without a TTY.
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and subprocess_utils.is_headless_context():
        raise PreconditionError(
            f"Cannot dispatch interactive skill {skill!r} via "
            f"`claude -p` subprocess: context is headless "
            f"(SBTDD_HEADLESS truthy OR stdin not a TTY). The skill "
            f"requires an interactive terminal for its prompts. "
            f"Recovery: {_build_recovery_message(skill)}"
        )
```

Confirm `import subprocess_utils` (or `from . import subprocess_utils`) is present at module top; if not, add after existing imports.

- [x] **Step 9: Run superpowers_dispatch tests to verify PASS**

Run: `pytest tests/test_superpowers_dispatch.py::TestInvokeSkillHeadlessGuard -v`
Expected: 3/3 PASS.

- [x] **Step 10: Add analogous guard to `magi_dispatch.py` (if applicable)**

Inspect `skills/sbtdd/scripts/magi_dispatch.py` for any callsite that dispatches interactive skills via subprocess. If MAGI itself is non-interactive (today: all 3 sub-agents are non-interactive analysis), there may be no callsite to modify — in that case, add a comment marker at module top documenting the future-proof contract:

```python
# v1.0.6 J-3 future-proof: MAGI dispatches its own sub-agents (Melchior,
# Balthasar, Caspar) which are non-interactive analysis tasks. If a future
# MAGI mode dispatches an interactive Claude skill via subprocess, the
# subprocess_utils.is_headless_context() guard MUST be invoked pre-spawn
# analogous to superpowers_dispatch.invoke_skill (see v1.0.6 spec sec.2.1
# escenarios J-6+J-7).
```

If `magi_dispatch.py` does dispatch interactive skills, mirror the J-3 guard structure from Step 8.

- [x] **Step 11: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green (pytest 1248 baseline + 9 new tests = 1257 passed; ruff check; ruff format --check; mypy --strict; coverage >= 88%).

- [x] **Step 12: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `feat:` commit (e.g. `feat: v1.0.6 T1 J-1+J-2+J-3 real headless detection helper + invoke_skill guard`).

#### Refactor Phase

- [x] **Step 13: Refactor — confirm shared module-level constants if duplicated**

If the truthy-set `{"1", "true", "yes"}` is referenced in multiple places (e.g., docs strings, README), extract to a module-level `_HEADLESS_TRUTHY_VALUES: frozenset[str]` constant for DRY. Likely not needed for this small surface; skip if no duplication.

- [x] **Step 14: Run tests to verify still PASS**

Run: `make verify`
Expected: Clean.

- [x] **Step 15: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 1 closed. State file advances `current_task_id: 1 → 2`.

---

## Track B — Polish in close_task_cmd.py + commits.py (Subagent #2, sequential T3 → T5 → T7)

**Owner**: Subagent #2 dispatched from orchestrator (or `auto --parallel` worker per Q1'=c).
**Surfaces** (file-disjoint with Track A + Track C + Track D):
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (T3 K-1 _section_has_flipped, T5 K-3 rename + alias, T7 K-5 triplet check regex)
- Modify: `skills/sbtdd/scripts/commits.py` (T7 K-5 validate_prefix regex extension)
- Extend: `tests/test_close_task_cmd.py` + `tests/test_commits.py`

**Wall-time estimated**: ~0.6 day (3 tasks sequential due to shared close_task_cmd.py).

**Within-track ordering**: T3 (K-1) → T5 (K-3 rename + alias) → T7 (K-5 CC scope). Order matters because T5 renames `_preflight_triplet_check` → `_preflight`, and T7 modifies the (renamed) function's regex matchers.

### Task 3: K-1 _section_has_flipped per-checkbox parity

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (per-checkbox semantic)
- Extend: `tests/test_close_task_cmd.py` (TestSectionHasFlippedPerCheckbox class)

Covers escenarios K-1a through K-1c from spec sec.4.4.

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_close_task_cmd.py` after existing `TestPerWorkerScratchPlan` or similar class:

```python
class TestSectionHasFlippedPerCheckbox:
    """v1.0.6 K-1: _section_has_flipped per-checkbox parity.

    Covers escenarios K-1a through K-1c from spec sec.4.4. Pre-fix:
    returned True on first [x] in section. Post-fix: requires ALL
    checkboxes in section to be [x] for True.
    """

    def test_k1a_mixed_checkbox_section_returns_false(self) -> None:
        """K-1a: section with both [x] and [ ] returns False (not fully flipped)."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n"
            "- [x] Step 1\n"
            "- [ ] Step 2\n"
            "- [x] Step 3\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is False, (
            "Mixed-checkbox section should NOT be considered flipped"
        )

    def test_k1b_fully_flipped_section_returns_true(self) -> None:
        """K-1b: section with all [x] returns True."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n"
            "- [x] Step 1\n"
            "- [x] Step 2\n"
            "- [x] Step 3\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is True

    def test_k1c_empty_section_returns_false(self) -> None:
        """K-1c: section with no checkboxes returns False (vacuously not flipped)."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n"
            "Description only, no checkboxes.\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is False

    def test_k1d_single_open_checkbox_returns_false(self) -> None:
        """K-1d (regression for v1.0.5): section with single [ ] and no [x] returns False."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n"
            "- [ ] Step 1\n"
            "\n### Task 2\n"
            "- [x] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is False

    def test_k1e_single_flipped_checkbox_returns_true(self) -> None:
        """K-1e (preserve v1.0.5): single [x] checkbox + no [ ] returns True."""
        from close_task_cmd import _section_has_flipped

        plan_text = (
            "### Task 1\n"
            "- [x] Step 1\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        assert _section_has_flipped(plan_text, "1") is True

    def test_k1f_codeblock_x_inside_section_does_not_count(self) -> None:
        """K-1f (iter-1 mel WARNING): line-anchored regex ignores `[x]` inside code blocks."""
        from close_task_cmd import _section_has_flipped

        # `[x]` appears inside a code block (not at line start) -- should NOT count
        plan_text = (
            "### Task 1\n"
            "Example code: `if x is None:` shows `[x]` syntax\n"
            "- [ ] Step 1\n"  # actual checkbox open
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        # has_x=False (no `^- [x]`), has_open=True → False
        assert _section_has_flipped(plan_text, "1") is False, (
            "Pre-fix substring check would have returned True (matched `[x]` in prose); "
            "post-fix line-anchored regex returns False"
        )

    def test_k1g_v105_i2_race_partial_worker_failure_no_fabrication(
        self, tmp_path: Path
    ) -> None:
        """K-1g (iter-1 bal WARNING): per-checkbox parity preserves v1.0.5 I-2 race contract.

        Worker A scratch shows partial T1 flips (1 of 2 steps `[x]`, 1 still `[ ]`);
        `_apply_flips_from_diff` MUST NOT fabricate full-task `[x]` for T1
        in main plan based on the partial scratch state.
        """
        from close_task_cmd import _apply_flips_from_diff

        main_plan = (
            "### Task 1\n"
            "- [ ] Step A\n"
            "- [ ] Step B\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        # Worker A scratch: T1 partially flipped (Step A done, Step B not done)
        scratch_a = (
            "### Task 1\n"
            "- [x] Step A\n"
            "- [ ] Step B\n"  # NOT flipped
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )

        merged = _apply_flips_from_diff(main_plan, scratch_a)
        # Per K-1 line-anchored + per-checkbox parity: T1 section in scratch
        # is NOT fully flipped (has both [x] and [ ]) → main plan T1 unchanged
        # NO fabrication of full-task `[x]` flip
        assert "- [ ] Step B" in merged, (
            "T1 Step B remained unflipped in main plan (no fabrication)"
        )

    def test_k1h_v105_i2_race_full_worker_completion_flips_correctly(
        self, tmp_path: Path
    ) -> None:
        """K-1h (iter-1 bal WARNING): fully-flipped scratch correctly propagates to main."""
        from close_task_cmd import _apply_flips_from_diff

        main_plan = (
            "### Task 1\n"
            "- [ ] Step A\n"
            "- [ ] Step B\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )
        # Worker A scratch: T1 FULLY flipped
        scratch_a = (
            "### Task 1\n"
            "- [x] Step A\n"
            "- [x] Step B\n"
            "\n### Task 2\n"
            "- [ ] Step 1\n"
        )

        merged = _apply_flips_from_diff(main_plan, scratch_a)
        # T1 fully flipped in scratch (per K-1 semantic) → propagates to main
        assert "- [x] Step A" in merged
        assert "- [x] Step B" in merged
        # T2 untouched
        assert "- [ ] Step 1" in merged
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_task_cmd.py::TestSectionHasFlippedPerCheckbox -v`
Expected: At least 1 test FAILS — pre-fix `_section_has_flipped` returns True on any `[x]` in section, so `test_k1a_mixed_checkbox_section_returns_false` fails (expected False, gets True).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit (e.g. `test: v1.0.6 T3 K-1 _section_has_flipped per-checkbox - failing tests`).

#### Green Phase

- [x] **Step 4: Implement per-checkbox parity in `_section_has_flipped` (iter-1 mel WARNING line-anchored regex)**

Modify `skills/sbtdd/scripts/close_task_cmd.py:_section_has_flipped`. Pre-fix likely uses `"- [x]" in section_text` (returns True on any `[x]`). Post-fix: section is "flipped" iff there exists at least one `[x]` AND no `[ ]` in the section, **using line-anchored multiline regex** to avoid false-positives from `[x]` appearing inside code blocks or descriptive prose (iter-1 mel WARNING):

```python
# v1.0.6 K-1: line-anchored checkbox patterns. Only `- [x]` / `- [ ]`
# at line start counts. Defends against `[x]` appearing in code blocks
# or descriptive prose (iter-1 mel WARNING — line-anchor robustness).
_CHECKBOX_FLIPPED_RE = re.compile(r"^[ \t]*- \[x\]", re.MULTILINE)
_CHECKBOX_OPEN_RE = re.compile(r"^[ \t]*- \[ \]", re.MULTILINE)


def _section_has_flipped(plan_text: str, task_id: str) -> bool:
    """Return True iff the task section is fully flipped to [x].

    v1.0.6 K-1 (per-checkbox parity fix + line-anchored regex):
    section is "flipped" only when it contains at least one ``- [x]``
    line AND zero ``- [ ]`` lines. Both checks use line-anchored
    multiline regex (`^- \\[x\\]` and `^- \\[ \\]`) to avoid false-
    positives from checkbox-like substrings appearing inside code
    blocks or descriptive prose.

    Pre-fix returned True on any ``- [x]`` substring even with
    remaining ``- [ ]``; that semantic broke ``_apply_flips_from_diff``
    correctness in the partial-worker-failure edge case (cas WARNING
    from Loop 2 v1.0.5 iter-1).

    Vacuously False when section has no checkboxes (descriptive only).
    """
    bounds = _section_bounds(plan_text, task_id)
    if bounds is None:
        return False
    section_start, section_end = bounds
    section_text = plan_text[section_start:section_end]
    has_x = bool(_CHECKBOX_FLIPPED_RE.search(section_text))
    has_open = bool(_CHECKBOX_OPEN_RE.search(section_text))
    return has_x and not has_open
```

Confirm `import re` present at module top (likely already; v1.0.5 uses it for `_TASK_HEADER_RE`).

- [x] **Step 5: Run K-1 tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestSectionHasFlippedPerCheckbox -v`
Expected: 5/5 PASS.

- [x] **Step 6: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green. Pay special attention to existing `_apply_flips_from_diff` tests + I-2 race regression tests — confirm semantic change doesn't break v1.0.5 contract.

- [x] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `fix:` commit (e.g. `fix: v1.0.6 T3 K-1 _section_has_flipped per-checkbox parity (cas WARNING)`).

#### Refactor Phase

- [x] **Step 8: Refactor — verify docstring + cross-references**

Confirm `_section_has_flipped` docstring matches new semantic. Search for any other callsites that rely on the pre-fix semantic and update them. Likely no other callsites; `_apply_flips_from_diff` is the primary consumer and it benefits from the fix.

- [x] **Step 9: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 3 closed. State file advances `current_task_id: 3 → 4`.

---

### Task 5: K-3 _preflight_triplet_check rename to _preflight + 1-cycle alias

**Files:**
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (rename function + add 1-cycle alias)
- Modify: `tests/test_close_task_cmd.py` (TestPreflightHardBlock + `_install_happy_path_patches` references)

Covers escenarios K-3a + K-3b from spec sec.4.6.

#### Red Phase

- [x] **Step 1: Write the failing tests**

Append to `tests/test_close_task_cmd.py`:

```python
class TestPreflightRenameAndAlias:
    """v1.0.6 K-3: _preflight_triplet_check renamed to _preflight + 1-cycle alias.

    Covers escenarios K-3a + K-3b from spec sec.4.6. Q3'=a 1-cycle window;
    alias removed in v1.0.7.
    """

    def test_k3a_canonical_preflight_callable(self, tmp_path: Path) -> None:
        """K-3a: close_task_cmd._preflight is the canonical name."""
        import close_task_cmd

        assert hasattr(close_task_cmd, "_preflight"), "Canonical _preflight must exist"
        assert callable(close_task_cmd._preflight), "_preflight must be callable"

    def test_k3b_legacy_alias_still_callable(self, tmp_path: Path) -> None:
        """K-3b: close_task_cmd._preflight_triplet_check alias resolves to _preflight.

        iter-1 cas WARNING relaxation: assert module-load-time identity ONLY.
        Monkeypatch of one name does NOT propagate to the alias (Python
        attribute semantics). Callers monkeypatching tests should target
        the canonical name (`_preflight`) per v1.0.6 K-3 migration guidance.
        """
        import close_task_cmd
        import importlib

        # Re-import to ensure clean module-load-time state (no prior monkeypatch leakage)
        importlib.reload(close_task_cmd)

        assert hasattr(close_task_cmd, "_preflight_triplet_check"), (
            "1-cycle deprecation alias must exist (removed in v1.0.7)"
        )
        # At module-load time (no monkeypatch), alias IS the canonical
        assert close_task_cmd._preflight_triplet_check is close_task_cmd._preflight, (
            "Alias must be `_preflight_triplet_check = _preflight` at module-load time. "
            "Note: post-monkeypatch identity may diverge (Python attribute semantics)."
        )

    def test_k3c_deprecation_marker_in_source(self) -> None:
        """K-3c: source contains DEPRECATED comment marker for grep-ability."""
        from pathlib import Path
        source = Path("skills/sbtdd/scripts/close_task_cmd.py").read_text(encoding="utf-8")
        assert "DEPRECATED" in source and "v1.0.7" in source, (
            "Source must contain DEPRECATED + v1.0.7 markers near the alias"
        )
```

- [x] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightRenameAndAlias -v`
Expected: 3/3 FAIL — `_preflight` doesn't exist yet (only `_preflight_triplet_check` does).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit.

#### Green Phase

- [x] **Step 4: Rename `_preflight_triplet_check` to `_preflight` + add alias**

Modify `skills/sbtdd/scripts/close_task_cmd.py`:

1. Rename the function definition `def _preflight_triplet_check(state, project_root, *, skip_preflight=False)` to `def _preflight(state, project_root, *, skip_preflight=False)`.

2. Update the single internal callsite in `close_task_cmd.main` (search for `_preflight_triplet_check(` invocation) — change to `_preflight(`.

3. Add the 1-cycle deprecation alias immediately after the renamed function definition:

```python
# DEPRECATED: 1-cycle alias for v1.0.6 -> v1.0.7 backwards compat (Q3'=a).
# Operator scripts that monkeypatch the old name (uncommon since
# `_preflight_triplet_check` is a private helper) get one cycle to migrate.
# Alias removed in v1.0.7 per CHANGELOG [1.0.6] Deferred section.
_preflight_triplet_check = _preflight
```

- [x] **Step 5: Update all test references**

Modify `tests/test_close_task_cmd.py`:

1. In `TestPreflightHardBlock` test class (and any other test class that references `_preflight_triplet_check`): rename method body references from `_preflight_triplet_check(` to `_preflight(`. (Imports of `from close_task_cmd import _preflight_triplet_check` → `from close_task_cmd import _preflight`.)

2. In `_install_happy_path_patches` helper: change `monkeypatch.setattr("close_task_cmd._preflight_triplet_check", ...)` → `monkeypatch.setattr("close_task_cmd._preflight", ...)`.

3. PRESERVE the alias-test class `TestPreflightRenameAndAlias` (added in Step 1) which asserts both names work.

Use Edit with `replace_all=True` for bulk renames in test file:

```bash
# Identify all callsites first
grep -n "_preflight_triplet_check" tests/test_close_task_cmd.py
```

Then update each callsite to use `_preflight` (except in TestPreflightRenameAndAlias which intentionally tests both names).

- [x] **Step 6: Run K-3 tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightRenameAndAlias -v`
Expected: 3/3 PASS.

- [x] **Step 7: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green (existing TestPreflightHardBlock tests still pass via renamed function).

- [x] **Step 8: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `refactor:` commit (rename is structural refactor, not feature/fix; e.g. `refactor: v1.0.6 T5 K-3 rename _preflight_triplet_check to _preflight + 1-cycle alias`).

> Note: per `~/.claude/CLAUDE.md` Git rules, prefix selection follows the
> nature of the change. K-3 is a rename (refactor), not a new feature
> (feat) or bug fix (fix). Use `--variant refactor` if `close-phase`
> defaults to feat/fix; otherwise the close-phase wrapper picks the
> right prefix from state.

#### Refactor Phase

- [x] **Step 9: Refactor — verify cross-artifact references**

Search the codebase for any remaining `_preflight_triplet_check` references that should be updated to `_preflight`:

```bash
grep -rn "_preflight_triplet_check" --include="*.py" --include="*.md" .
```

Expected matches:
- `close_task_cmd.py`: alias definition + DEPRECATED comment (KEEP)
- `tests/test_close_task_cmd.py::TestPreflightRenameAndAlias`: intentional alias tests (KEEP)
- `sbtdd/spec-behavior.md`: documentation references (KEEP — historical record per spec)
- `CHANGELOG.md`: historical record (KEEP)
- Any other code references should be migrated to `_preflight`.

- [x] **Step 10: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 5 closed. State file advances `current_task_id: 5 → 6`.

---

### Task 7: K-5 Triplet check robust to Conventional Commits scope syntax

**Files:**
- Modify: `skills/sbtdd/scripts/commits.py` (add `validate_prefix_from_subject` helper or extend existing matcher)
- Modify: `skills/sbtdd/scripts/close_task_cmd.py` (extend triplet matchers)
- Extend: `tests/test_commits.py` + `tests/test_close_task_cmd.py`

Covers escenarios K-5a through K-5d from spec sec.4.8.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_commits.py`:

```python
class TestValidatePrefixFromSubjectCCScope:
    """v1.0.6 K-5: liberal CC scope syntax support (Q4'=b liberal regex).

    Covers escenarios K-5a + K-5b + K-5c from spec sec.4.8.
    """

    def test_k5a_bare_prefix_matches_backwards_compat(self) -> None:
        """K-5a: bare prefix `test:` still matches (v1.0.5 backwards compat)."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("test: add failing test for X") == "test"
        assert extract_prefix_from_subject("feat: implement Y") == "feat"
        assert extract_prefix_from_subject("fix: bug Z") == "fix"
        assert extract_prefix_from_subject("refactor: extract helper") == "refactor"
        assert extract_prefix_from_subject("chore: mark task 1 complete") == "chore"

    def test_k5b_scoped_prefix_matches_NEW(self) -> None:
        """K-5b: `test(scope): ...` scoped prefix matches per Q4'=b liberal."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("test(close-task): add failing test") == "test"
        assert extract_prefix_from_subject("feat(close-task): implement") == "feat"
        assert extract_prefix_from_subject("fix(commits): bug fix") == "fix"
        assert extract_prefix_from_subject("refactor(state-file): extract helper") == "refactor"

    def test_k5c_liberal_scope_content_accepted(self) -> None:
        """K-5c: liberal regex `[^()]+` accepts any non-paren scope content."""
        from commits import extract_prefix_from_subject

        # Uppercase scope
        assert extract_prefix_from_subject("feat(Close-Task): X") == "feat"
        # Underscore scope
        assert extract_prefix_from_subject("fix(close_task): X") == "fix"
        # Space in scope
        assert extract_prefix_from_subject("refactor(some scope): X") == "refactor"
        # Numeric scope
        assert extract_prefix_from_subject("test(123): X") == "test"
        # Mixed
        assert extract_prefix_from_subject("feat(My-Scope_v2): X") == "feat"

    def test_k5e_cc_breaking_change_marker_supported(self) -> None:
        """K-5e (iter-1 cas WARNING): CC spec `!` breaking-change marker matches."""
        from commits import extract_prefix_from_subject

        # Bare with breaking marker
        assert extract_prefix_from_subject("feat!: drop legacy API") == "feat"
        assert extract_prefix_from_subject("fix!: backwards-incompatible bug fix") == "fix"
        # Scoped with breaking marker
        assert extract_prefix_from_subject("feat(api)!: drop legacy") == "feat"
        assert extract_prefix_from_subject("refactor(close-task)!: rename helper") == "refactor"

    def test_k5f_colon_without_trailing_space_supported(self) -> None:
        """K-5f (iter-1 mel WARNING): colon without trailing whitespace matches."""
        from commits import extract_prefix_from_subject

        # No space after colon
        assert extract_prefix_from_subject("feat:Implementation") == "feat"
        assert extract_prefix_from_subject("test(scope):add tests") == "test"
        # Colon at end of line (just prefix, empty body — uncommon but valid syntax)
        assert extract_prefix_from_subject("feat:") == "feat"

    def test_k5_extraction_is_liberal_validation_is_separate(self) -> None:
        """K-5 (Q4'=b + iter-1 bal+cas WARNING): extraction is liberal; validation is downstream.

        Returned prefix is NOT validated against `_ALLOWED_PREFIXES`.
        Caller (e.g., _preflight triplet check) validates separately.
        """
        from commits import extract_prefix_from_subject

        # Known prefixes extract correctly
        assert extract_prefix_from_subject("docs: update README") == "docs"
        # Unknown lowercase prefix extracts (extraction is liberal)
        assert extract_prefix_from_subject("madeup: subject") == "madeup"
        # No-colon subject returns None
        assert extract_prefix_from_subject("noprefix subject only") is None
        # Non-alphabetic prefix returns None (regex requires `[a-z]+`)
        assert extract_prefix_from_subject("123: numeric prefix") is None

    def test_k5_subject_with_no_colon_returns_none(self) -> None:
        """K-5: subject without colon doesn't match prefix syntax."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("just a subject without colon") is None
```

Append to `tests/test_close_task_cmd.py`:

```python
class TestPreflightTripletCCScope:
    """v1.0.6 K-5: _preflight accepts CC scoped triplet subjects.

    Covers escenario K-5d from spec sec.4.8.
    """

    def test_k5d_triplet_check_accepts_scoped_subjects(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """K-5d: scoped TDD triplet (test(scope): + feat(scope): + refactor(scope):) passes."""
        from close_task_cmd import _preflight

        # Mock _last_chore_task_close_sha + _git_log_between to return scoped subjects
        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc1234",
        )
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test(close-task): write failing test",
                "feat(close-task): implement",
                "refactor(close-task): extract helper",
            ],
        )
        state = {"current_task_id": "3"}

        # Should NOT raise (canonical TDD triplet present in scoped form)
        _preflight(state, tmp_path)

    def test_k5d_triplet_check_accepts_mixed_bare_and_scoped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """K-5d (variant): mix of bare + scoped subjects in chain still passes triplet."""
        from close_task_cmd import _preflight

        monkeypatch.setattr(
            "close_task_cmd._last_chore_task_close_sha",
            lambda project_root=None: "abc1234",
        )
        monkeypatch.setattr(
            "close_task_cmd._git_log_between",
            lambda start_sha, project_root=None: [
                "test: write failing test",  # bare prefix
                "feat(close-task): implement",  # scoped prefix
                "refactor: extract",  # bare prefix
            ],
        )
        state = {"current_task_id": "3"}

        # Should NOT raise (triplet still present even with mix)
        _preflight(state, tmp_path)
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_commits.py::TestValidatePrefixFromSubjectCCScope tests/test_close_task_cmd.py::TestPreflightTripletCCScope -v`
Expected: 7/7 FAIL — `extract_prefix_from_subject` doesn't exist yet; `_preflight` raises on scoped subjects.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit.

#### Green Phase

- [ ] **Step 4: Implement `extract_prefix_from_subject` in `commits.py`**

Add to `skills/sbtdd/scripts/commits.py` after existing `validate_prefix`:

```python
# v1.0.6 K-5 (Q4'=b liberal regex + iter-1 mel+cas WARNING extensions):
# extract TDD prefix from a commit subject. Matches:
#  * Bare: `test:`, `test: msg`, `test:msg` (no trailing space required)
#  * Scoped: `test(scope):`, `test(scope): msg`
#  * Breaking-change marker: `feat!:`, `feat(scope)!:` (CC spec)
# Liberal scope content `[^()]+` per Q4'=b operator UX rationale.
# Trailing anchor `(?:\s|$)` accepts colon-with-or-without trailing
# whitespace per iter-1 mel WARNING (subjects like `feat:Implementation`
# without space were rejected by pre-iter-1 `:\s` strict anchor).
_PREFIX_FROM_SUBJECT_RE = re.compile(r"^([a-z]+)(?:\([^()]*\))?!?:(?:\s|$)")


def extract_prefix_from_subject(subject: str) -> str | None:
    """Extract TDD prefix from a commit subject.

    Matches both bare and Conventional Commits forms:

    * Bare: ``test: add failing test`` -> ``"test"``
    * Bare no-space: ``test:add failing test`` -> ``"test"``
    * Scoped: ``test(close-task): add failing test`` -> ``"test"``
    * Breaking-change: ``feat!: drop legacy API`` -> ``"feat"``
    * Scoped breaking-change: ``feat(api)!: drop legacy`` -> ``"feat"``

    Liberal scope content per Q4'=b: any non-paren chars accepted
    (uppercase, underscores, spaces, digits all OK). Trailing anchor
    accepts colon-with-or-without whitespace per iter-1 mel WARNING.

    Returns None when subject doesn't match prefix syntax (no colon
    after prefix, or non-alphabetic prefix).

    **Important (iter-1 bal+cas WARNING)**: prefix extraction is NOT
    prefix validation. The returned prefix is NOT validated against
    :data:`_ALLOWED_PREFIXES`; downstream callers (e.g.,
    :func:`close_task_cmd._preflight` triplet check) validate
    separately if needed. This separation is intentional: liberal
    extraction surfaces all candidate prefixes; strict downstream
    validation enforces the allowed set.

    Args:
        subject: Commit subject line (first line of commit message).

    Returns:
        The bare prefix (``"test"``, ``"feat"``, etc.) or None if no
        match.
    """
    match = _PREFIX_FROM_SUBJECT_RE.match(subject)
    if match is None:
        return None
    return match.group(1)
```

Confirm `import re` is present at module top (likely already there).

- [ ] **Step 5: Run commits tests to verify PASS**

Run: `pytest tests/test_commits.py::TestValidatePrefixFromSubjectCCScope -v`
Expected: 5/5 PASS.

- [ ] **Step 6: Update `_preflight` triplet matchers in `close_task_cmd.py`**

Modify `skills/sbtdd/scripts/close_task_cmd.py:_preflight`. Find the existing triplet check (around line 390):

```python
    has_test = any(s.startswith("test:") for s in subjects)
    has_green = any(s.startswith(("feat:", "fix:")) for s in subjects)
    has_refactor = any(s.startswith("refactor:") for s in subjects)
```

Replace with `extract_prefix_from_subject`-based matchers:

```python
    # v1.0.6 K-5 (Q4'=b liberal CC scope): extract prefix from each
    # subject so scoped forms like `test(close-task):` match alongside
    # bare `test:`. Falls back to v1.0.5 startswith semantic for unknown
    # extraction failures (None) to preserve fail-safe behavior.
    from commits import extract_prefix_from_subject

    extracted = [extract_prefix_from_subject(s) for s in subjects]
    has_test = "test" in extracted
    has_green = "feat" in extracted or "fix" in extracted
    has_refactor = "refactor" in extracted
```

Confirm `from commits import extract_prefix_from_subject` is added at module top (or inside the function for late-import; either is acceptable for this small surface).

- [ ] **Step 7: Run K-5d tests to verify PASS**

Run: `pytest tests/test_close_task_cmd.py::TestPreflightTripletCCScope -v`
Expected: 2/2 PASS.

- [ ] **Step 8: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green. Confirm existing TestPreflightHardBlock tests still pass with the new extraction-based matchers (bare prefixes still extracted correctly).

- [ ] **Step 9: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `feat:` commit (e.g. `feat: v1.0.6 T7 K-5 liberal CC scope syntax in extract_prefix_from_subject + _preflight triplet`).

#### Refactor Phase

- [ ] **Step 10: Refactor — verify regex documentation + edge cases**

Confirm `_PREFIX_FROM_SUBJECT_RE` regex docstring documents the Q4'=b liberal scope rationale. Add a brief comment explaining why the regex anchors to start-of-string (`^`) and requires colon-space (`:\s`) — defensive against false-positive matches in subjects that contain `(text):` mid-string.

- [ ] **Step 11: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 7 closed. State file advances `current_task_id: 7 → 4` (next [ ] in plan source order).

---

## Track C — Polish in auto_cmd.py (Subagent #3, sequential T4 → T6)

**Owner**: Subagent #3 dispatched from orchestrator (or `auto --parallel` worker per Q1'=c).
**Surfaces** (file-disjoint with Track A + Track B + Track D):
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (T4 K-2 getattr removal, T6 K-4 _FORWARDABLE_FLAGS guard)
- Extend: `tests/test_auto_cmd.py`

**Wall-time estimated**: ~0.4 day (2 tasks sequential due to shared auto_cmd.py).

**Within-track ordering**: T4 (K-2 getattr removal) → T6 (K-4 argparse guard). Order can be flipped without coupling concerns; T4 → T6 chosen because T4 is smaller surface.

### Task 4: K-2 getattr late-import fallback removal

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` post-batch hook
- Extend: `tests/test_auto_cmd.py` (regression test for direct-import semantic)

Covers escenario K-2 from spec sec.4.5.

#### Red Phase

- [x] **Step 1: Write the failing test**

Append to `tests/test_auto_cmd.py`:

```python
class TestK2GetattrFallbackRemoved:
    """v1.0.6 K-2: getattr late-import fallback removed.

    Covers escenario K-2 from spec sec.4.5. Pre-fix used
    getattr(close_task_cmd, "_merge_scratch_plans", noop) for defensive
    scaffolding during v1.0.5 Track Alpha -> Track Beta cross-track
    import dependency development. Post-T3-land, the fallback is dead
    code and hides regressions if helper somehow removed.
    """

    def test_k2_no_getattr_fallback_in_dispatch_post_batch(self) -> None:
        """K-2: source contains direct import, NOT getattr fallback."""
        from pathlib import Path
        source = Path("skills/sbtdd/scripts/auto_cmd.py").read_text(encoding="utf-8")
        # Verify the getattr noop fallback pattern is absent
        assert "getattr(close_task_cmd, \"_merge_scratch_plans\"" not in source, (
            "v1.0.6 K-2: getattr fallback should be removed; use direct import"
        )
        # Verify direct import is present (late-import inside function body)
        assert "from close_task_cmd import _merge_scratch_plans" in source, (
            "v1.0.6 K-2: direct late-import should be present in dispatch hook"
        )
```

- [x] **Step 2: Run test to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestK2GetattrFallbackRemoved -v`
Expected: 1 FAIL (assuming v1.0.5 source has the getattr fallback).

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit.

#### Green Phase

- [x] **Step 4: Replace getattr fallback with direct late-import**

Modify `skills/sbtdd/scripts/auto_cmd.py:_dispatch_tracks_concurrent`. Find the post-batch hook (likely contains `getattr(close_task_cmd, "_merge_scratch_plans", ...)` pattern):

Pre-fix (v1.0.5 defensive scaffolding):

```python
    # v1.0.5 iter-1 CRITICAL #4: late-import + getattr noop fallback
    # for defensive resilience pre-T3-land in test harnesses.
    import close_task_cmd
    merge_scratch_plans = getattr(close_task_cmd, "_merge_scratch_plans", lambda *a, **k: None)
    merge_scratch_plans(tracks, project_root)
```

Post-fix (v1.0.6 K-2):

```python
    # v1.0.6 K-2 (Q-cleanup): direct late-import inside function body.
    # Cross-module dep correctness preserved via late-import (cross-track
    # T1 -> T3 timing per v1.0.5 Track Alpha/Beta hardening). The
    # getattr noop fallback (defensive scaffolding from v1.0.5) is
    # removed; if `_merge_scratch_plans` is removed in a future cycle,
    # ImportError surfaces immediately rather than silently no-op'ing.
    from close_task_cmd import _merge_scratch_plans
    _merge_scratch_plans(tracks, project_root)
```

- [x] **Step 5: Run K-2 test to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestK2GetattrFallbackRemoved -v`
Expected: 1/1 PASS.

- [x] **Step 6: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green. Critical: existing v1.0.5 I-2 race regression tests + I-1 sidecar tests must still pass via the new direct import.

- [x] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `refactor:` commit (this is structural cleanup, not feature/fix; e.g. `refactor: v1.0.6 T4 K-2 remove getattr noop fallback in _dispatch_tracks_concurrent`).

#### Refactor Phase

- [x] **Step 8: Refactor — verify no other defensive getattr patterns to clean up**

Search for similar `getattr(<module>, "<helper>", ...)` patterns elsewhere in the codebase:

```bash
grep -n "getattr.*_merge_scratch_plans\|getattr.*_apply_flips_from_diff" --include="*.py" -r skills/sbtdd/
```

Expected: zero matches post-fix. If other similar patterns exist as defensive scaffolding from v1.0.5, document in CHANGELOG `[1.0.6]` Process notes for future cleanup but DO NOT modify in this task (out of scope; would scope-creep).

- [x] **Step 9: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 4 closed. State file advances `current_task_id: 4 → 5`.

---

### Task 6: K-4 _FORWARDABLE_FLAGS argparse-presence guard

**Files:**
- Modify: `skills/sbtdd/scripts/auto_cmd.py` (add module-level argparse-presence guard for `_FORWARDABLE_FLAGS`)
- Extend: `tests/test_auto_cmd.py` (meta-test asserting drift detection fires)

Covers escenarios K-4a + K-4b from spec sec.4.7.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_auto_cmd.py`:

```python
class TestK4ForwardableFlagsArgparseGuard:
    """v1.0.6 K-4: _FORWARDABLE_FLAGS argparse-presence guard.

    Covers escenarios K-4a + K-4b from spec sec.4.7.
    """

    def test_k4a_clean_forwardable_flags_passes(self) -> None:
        """K-4b (positive): real _FORWARDABLE_FLAGS matches argparse dest set."""
        # Module already imported in test session; if guard fires at module load,
        # this test only runs when guard is satisfied (positive case).
        import auto_cmd
        # Verify guard helper exists + returns None on clean state
        assert hasattr(auto_cmd, "_validate_forwardable_flags_against_argparse"), (
            "K-4 guard helper must exist"
        )
        # Invocation with current state should not raise
        auto_cmd._validate_forwardable_flags_against_argparse()

    def test_k4a_drift_detected_raises_validation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """K-4a: synthetic _FORWARDABLE_FLAGS with drifted key raises ValidationError."""
        from errors import ValidationError
        import auto_cmd

        # Inject a fake forwardable flag NOT in argparse dest set
        from types import MappingProxyType
        fake_flags = MappingProxyType({
            **dict(auto_cmd._FORWARDABLE_FLAGS),
            "nonexistent_fake_flag_for_drift_test": "--nonexistent-fake-flag",
        })
        monkeypatch.setattr(auto_cmd, "_FORWARDABLE_FLAGS", fake_flags)

        with pytest.raises(ValidationError) as excinfo:
            auto_cmd._validate_forwardable_flags_against_argparse()
        msg = str(excinfo.value)
        assert "nonexistent_fake_flag_for_drift_test" in msg, (
            "Drift error message must name the offending key(s)"
        )
        assert "_FORWARDABLE_FLAGS" in msg or "argparse" in msg, (
            "Drift error must explain context"
        )
```

- [ ] **Step 2: Run tests to verify FAIL**

Run: `pytest tests/test_auto_cmd.py::TestK4ForwardableFlagsArgparseGuard -v`
Expected: 2/2 FAIL — `_validate_forwardable_flags_against_argparse` doesn't exist yet.

- [ ] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit.

#### Green Phase

- [ ] **Step 4: Implement `_validate_forwardable_flags_against_argparse` helper**

Modify `skills/sbtdd/scripts/auto_cmd.py`. Add the helper near `_FORWARDABLE_FLAGS` definition (around line 1435):

```python
def _validate_forwardable_flags_against_argparse() -> None:
    """v1.0.6 K-4: validate `_FORWARDABLE_FLAGS` keys exist in argparse dest set.

    Detects drift between the hardcoded `_FORWARDABLE_FLAGS` mapping
    and the `_build_argparse_parser()` argparse definition. Raises
    `ValidationError` UNCONDITIONALLY at module import time (or on
    explicit invocation in tests) if any key in `_FORWARDABLE_FLAGS`
    is not a known dest name in the parser.

    Rationale: `_build_worker_argv` uses `_FORWARDABLE_FLAGS` to
    propagate operator flags to subprocess workers. If a flag is
    added to `_FORWARDABLE_FLAGS` but not registered in argparse,
    `getattr(ns, ns_attr, None)` would silently return None and the
    flag would never be forwarded -- subtle bug. Loud-fast detection
    at module load surfaces drift immediately.

    **Private-attribute fragility acknowledgment (iter-1 mel WARNING)**:
    this helper traverses argparse internals (`parser._actions` +
    `action.choices` for subparsers). These are private attrs not
    part of argparse's public API; future argparse refactors could
    break this introspection. Acceptable trade-off given the
    coverage value (drift detection at module load time saves
    debugging cost). If argparse changes, this helper updates here
    in one place.
    """
    from errors import ValidationError

    parser = _build_argparse_parser()
    # Private-attribute traversal (acknowledged fragility per docstring).
    dest_names: set[str] = set()
    for action in parser._actions:
        if action.dest:
            dest_names.add(action.dest)
    # Also walk subparsers if present
    for action in parser._actions:
        if hasattr(action, "choices") and isinstance(action.choices, dict):
            for sub_parser in action.choices.values():
                for sub_action in sub_parser._actions:
                    if sub_action.dest:
                        dest_names.add(sub_action.dest)

    missing = [
        ns_attr for ns_attr in _FORWARDABLE_FLAGS
        if ns_attr not in dest_names
    ]
    if missing:
        raise ValidationError(
            f"v1.0.6 K-4: _FORWARDABLE_FLAGS drift detected -- the "
            f"following keys are NOT registered as argparse dest names: "
            f"{sorted(missing)}. Either remove them from "
            f"_FORWARDABLE_FLAGS or add them to _build_argparse_parser()."
        )


# v1.0.6 K-4 (iter-1 mel+bal+cas TRIPLE WARNING fix): invoke guard at module
# import UNCONDITIONALLY. ValidationError is fatal at import time -- drift
# surfaces immediately. Pre-iter-1 plan wrapped this in try/except with an
# SBTDD_STRICT_K4_GUARD opt-out env var; that defeated the loud-fast intent
# (silent swallow in production). Retracted per iter-1 triage.
_validate_forwardable_flags_against_argparse()
```

- [ ] **Step 5: Run K-4 tests to verify PASS**

Run: `pytest tests/test_auto_cmd.py::TestK4ForwardableFlagsArgparseGuard -v`
Expected: 2/2 PASS.

- [ ] **Step 6: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green. Confirm existing `_FORWARDABLE_FLAGS` (5 keys per v1.0.5) all present in argparse dest set.

- [ ] **Step 7: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `feat:` commit (e.g. `feat: v1.0.6 T6 K-4 _FORWARDABLE_FLAGS argparse-presence guard`).

#### Refactor Phase

- [ ] **Step 8: Refactor — verify guard semantics + cleanup**

Confirm the guard at module import is unconditionally fatal (no try/except wrap, no opt-out env var per iter-1 mel+bal+cas TRIPLE WARNING fix). The `SBTDD_STRICT_K4_GUARD` env var concept is RETRACTED — drift always fatal at module load.

Optionally: if `_build_argparse_parser` is expensive (full subparser tree), consider caching its result or only validating the relevant subparser (auto). For v1.0.6 simplicity, run the full validation at module load — overhead is one-time + small.

- [ ] **Step 9: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 6 closed. State file advances `current_task_id: 6 → 7`.

---

## Track D — C.2 Plan archaeology trim methodology (Subagent #4, single task T2)

**Owner**: Subagent #4 (lightweight; could be orchestrator in-session) or `auto --parallel` worker per Q1'=c.
**Surfaces** (cero overlap with Track A + Track B + Track C):
- Modify: `skills/sbtdd/SKILL.md` (orchestrator skill rules — add ship-time archaeology trim procedure)
- Modify: `templates/CLAUDE.local.md.template` (template guidance for destination projects)
- Create: `tests/test_plan_archaeology_trim_pattern.py` (smoke test)

**Wall-time estimated**: ~0.3 day.

### Task 2: C.2 Plan archaeology trim methodology + smoke test

**Files:**
- Create: `tests/test_plan_archaeology_trim_pattern.py`
- Modify: `skills/sbtdd/SKILL.md`
- Modify: `templates/CLAUDE.local.md.template`

Covers escenarios C2-1 through C2-3 from spec sec.4.3.

#### Red Phase

- [x] **Step 1: Write the failing smoke test**

Create new file `tests/test_plan_archaeology_trim_pattern.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.6 Item C.2 (carry-forward from v1.0.5 iter-2 G2 ladder defer):
plan archaeology trim methodology smoke test.

Asserts cross-artifact reference between SKILL.md and
templates/CLAUDE.local.md.template for the ship-time procedure pattern.
"""
from __future__ import annotations

from pathlib import Path


_SKILL_MD = Path("skills/sbtdd/SKILL.md")
_TEMPLATE = Path("templates/CLAUDE.local.md.template")
_PROCEDURE_PATTERN = "plan archaeology trim"


def test_c2_1_skill_md_documents_ship_time_trim_procedure() -> None:
    """C2-1: SKILL.md documents the ship-time plan archaeology trim procedure."""
    assert _SKILL_MD.exists(), f"SKILL.md not found at {_SKILL_MD}"
    text = _SKILL_MD.read_text(encoding="utf-8").lower()
    assert _PROCEDURE_PATTERN in text, (
        f"SKILL.md must reference '{_PROCEDURE_PATTERN}' procedure (case-insensitive)"
    )
    # Must also mention the destination (CHANGELOG Process notes section)
    assert "process notes" in text or "changelog" in text, (
        "SKILL.md procedure must mention CHANGELOG Process notes destination"
    )


def test_c2_2_template_references_archaeology_trim() -> None:
    """C2-2: CLAUDE.local.md.template references the archaeology trim procedure."""
    assert _TEMPLATE.exists(), f"Template not found at {_TEMPLATE}"
    text = _TEMPLATE.read_text(encoding="utf-8").lower()
    assert _PROCEDURE_PATTERN in text, (
        f"Template must reference '{_PROCEDURE_PATTERN}' procedure (case-insensitive)"
    )


def test_c2_3_smoke_cross_artifact_reference_exists_in_both() -> None:
    """C2-3: drift between SKILL.md + template caught (both must reference)."""
    skill_text = _SKILL_MD.read_text(encoding="utf-8").lower()
    template_text = _TEMPLATE.read_text(encoding="utf-8").lower()
    skill_has = _PROCEDURE_PATTERN in skill_text
    template_has = _PROCEDURE_PATTERN in template_text
    assert skill_has and template_has, (
        f"Drift detected: SKILL.md has='{skill_has}', template has='{template_has}'. "
        f"Both must reference '{_PROCEDURE_PATTERN}' pattern."
    )
```

- [x] **Step 2: Run smoke test to verify FAIL**

Run: `pytest tests/test_plan_archaeology_trim_pattern.py -v`
Expected: 3/3 FAIL — SKILL.md + template don't mention "plan archaeology trim" yet.

- [x] **Step 3: close-phase Red**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `test:` commit.

#### Green Phase

- [x] **Step 4: Update `skills/sbtdd/SKILL.md` with archaeology trim procedure**

Find the existing "## Notes" section at end of `skills/sbtdd/SKILL.md` (or insert before it). Add new section:

```markdown
### Plan archaeology trim methodology (v1.0.6 C.2)

At ship-time of each v1.0.X release, the orchestrator SHOULD apply
the **plan archaeology trim** procedure to keep `planning/claude-plan-tdd.md`
focused on the active scope rather than accumulating iter-by-iter
triage context across cycles:

1. **Extract iter triage context** from
   `planning/claude-plan-tdd.md` into the CHANGELOG `[N.N.N]`
   "Process notes" section. Iter-1 / iter-2 / iter-3 triage decisions
   are valuable historical record but bloat the active plan.
2. **Trim plan-tdd.md to "active plan only"** -- current scope +
   tasks + acceptance criteria; no iter archaeology.
3. **Optional belt-and-suspenders**: keep
   `planning/claude-plan-tdd-org.md` as immutable archaeology
   while `planning/claude-plan-tdd.md` is the trimmed canonical
   active plan. Both files coexist; `*-org.md` is the historical
   record, `claude-plan-tdd.md` is the operational reference.

Originally proposed by Balthasar v1.0.4 INFO #17 ("Plan size
disproportionate to code delta -- maintenance debt accumulating");
deferred via v1.0.5 iter-2 G2 ladder; landed in v1.0.6 Item C.2.
The methodology is doc-only (no code change); see
`templates/CLAUDE.local.md.template` for destination project
guidance.
```

- [x] **Step 5: Update `templates/CLAUDE.local.md.template` with template guidance**

Find an appropriate section in `templates/CLAUDE.local.md.template` (likely near the methodology / sec.1 specification flow section). Add:

```markdown
### Plan archaeology trim (v1.0.6 C.2 cross-link)

When shipping each v1.0.X release of YOUR project that uses SBTDD,
apply the **plan archaeology trim** procedure documented in the
plugin's `skills/sbtdd/SKILL.md` (section "Plan archaeology trim
methodology"). In summary:

1. Extract iter-by-iter triage context from
   `planning/claude-plan-tdd.md` into CHANGELOG `[N.N.N]` Process
   notes section.
2. Trim plan-tdd.md to "active plan only" (scope + tasks +
   acceptance; no iter archaeology).
3. Optional: keep `planning/claude-plan-tdd-org.md` as immutable
   historical record while plan-tdd.md is the trimmed canonical
   reference.

Doc-only methodology; no runtime impact. See plugin SKILL.md for
the canonical procedure.
```

- [x] **Step 6: Run smoke test to verify PASS**

Run: `pytest tests/test_plan_archaeology_trim_pattern.py -v`
Expected: 3/3 PASS.

- [x] **Step 7: Run full test suite to verify no regression**

Run: `make verify`
Expected: All checks green.

- [x] **Step 8: close-phase Green**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`

Expected: Atomic `feat:` commit (e.g. `feat: v1.0.6 T2 C.2 plan archaeology trim methodology in SKILL.md + template + smoke test`).

#### Refactor Phase

- [x] **Step 9: Refactor — verify cross-artifact consistency**

Confirm that the SKILL.md and template both reference each other (cross-link). Verify the smoke test catches drift in either direction (e.g., remove pattern from one file → smoke test fails). Run smoke test once more for confidence:

Run: `pytest tests/test_plan_archaeology_trim_pattern.py -v`
Expected: 3/3 PASS (still).

- [x] **Step 10: close-phase Refactor + close-task**

Run: `python skills/sbtdd/scripts/run_sbtdd.py close-phase`
Run: `python skills/sbtdd/scripts/run_sbtdd.py close-task --skip-spec-review`

Expected: Task 2 closed. State file advances `current_task_id: 2 → 3`.

---

## Mid-cycle methodology activities (orchestrator)

Triggered AFTER Track A + Track B + Track C + Track D all complete +
commits land. Each activity is non-blocking for ship per hybrid
methodology semantics; documented in CHANGELOG `[1.0.6]` Process
notes regardless of outcome.

### Activity F-J9 — `/sbtdd spec` headless detection empirical validation

**Owner**: orchestrator.
**When**: AFTER Track A close + Item J-1+J-2+J-3 landed.
**Wall-time**: ~30 min.

**Steps**:

```bash
# Set explicit headless env var
SBTDD_HEADLESS=1 python skills/sbtdd/scripts/run_sbtdd.py spec
```

Expected: `PreconditionError` raised LOUD-FAST with message naming `--resume-from-magi` recovery path. Exit code 2. No 600s timeout hang.

Then unset env var and invoke in interactive TTY:

```bash
unset SBTDD_HEADLESS  # POSIX; or `Remove-Item Env:SBTDD_HEADLESS` PowerShell
python skills/sbtdd/scripts/run_sbtdd.py spec
```

Expected: spec flow proceeds via existing path (will eventually hit `/brainstorming` or `/writing-plans` dispatch which may still encounter the chicken-and-egg pattern; if the operator wants end-to-end `/sbtdd spec`, they hand-craft the artifacts first then invoke `/sbtdd spec --resume-from-magi`).

Document outcome in CHANGELOG `[1.0.6]` Process notes.

### Activity F-J10 — `/sbtdd pre-merge` headless detection empirical validation

**Owner**: orchestrator.
**When**: AFTER Track A close + Item J-1+J-2+J-3 landed + state file at `current_phase: "done"`.
**Wall-time**: ~30 min.

**Steps**:

```bash
SBTDD_HEADLESS=1 python skills/sbtdd/scripts/run_sbtdd.py pre-merge
```

Expected: `PreconditionError` raised LOUD-FAST with message naming manual `run_magi.py` fallback. Exit code 2. No 1200s timeout hang.

Document outcome in CHANGELOG `[1.0.6]` Process notes.

### Activity F-A2 — `auto --parallel` self-dispatch dogfood (Q1'=c)

**Owner**: orchestrator.
**When**: Concurrent with all 7 plan tasks (this IS the dispatch mechanism per Q1'=c).
**Wall-time**: ~1.5 days (parallel dispatch wall-time).

**Steps**:

```bash
# Pre-flight (iter-2 bal WARNING — cheap insurance against partition crash)
python skills/sbtdd/scripts/run_sbtdd.py auto --parallel --dry-run

# v1.0.6 own-cycle uses auto --parallel for impl phase per Q1'=c
python skills/sbtdd/scripts/run_sbtdd.py auto --parallel
```

Pre-flight `--dry-run` validates `partition_by_tracks` computes cleanly (no missing task surface declaration, no file-conflict cycle) without spawning workers — ~5 min insurance vs ~half-day recovery debt if partition fails mid-dispatch.

Expected: `partition_by_tracks` computes disjoint tracks per file-conflict edges. Subprocess workers dispatch per partition; each worker processes its track sequentially per within-track ordering documented in spec sec.5.1. Parent post-batch merges sidecar audits + scratch plan flips per v1.0.5 contract.

After dispatch, ALL of the following must be verifiable:
- Parent `.claude/auto-run.json` contains start_time + 7 task records (validates v1.0.5 I-1)
- Plan-tdd.md has 7 `[x]` checkbox flips, no lost updates (validates v1.0.5 I-2)
- Each worker subprocess received forwarded operator flags (validates v1.0.5 I-3)
- All TDD triplet commits per task in git log (`test:` + `feat:|fix:` + `refactor:` + `chore:`) — possibly with CC scope syntax post-T7 K-5
- State file `current_phase: "done"` post-completion

This empirically validates v1.0.5 production-grade `--parallel` end-to-end (deferred dogfood from v1.0.5 sec.2.7).

**Explicit abort criteria** (iter-1 bal INFO addressed): fall back to manual 2-track subagent dispatch via Agent tool fan-out (Q1' option b) if ANY of:

- (a) `partition_by_tracks` raises (e.g., file-conflict edge cycle, missing task surface declaration).
- (b) Any worker subprocess crashes on import (e.g., K-4 ValidationError fires due to genuine `_FORWARDABLE_FLAGS` drift introduced mid-cycle). **Diagnosis hint** (iter-2 mel WARNING): on abort (b) firing, BEFORE falling back to manual 2-track Q1' option b, check stderr for `ValidationError` from K-4 guard — if present, fix the drift in `_FORWARDABLE_FLAGS` (or argparse) first, then retry `auto --parallel`. K-4 catching real drift IS the desired loud-fast behavior; the abort fallback is for genuine infrastructure failures, not for K-4-detected bugs.
- (c) Post-batch sidecar/scratch merge validation fails (corrupt state, lost flips, or audit-trail integrity check fails).
- (d) Operator interrupts mid-dispatch (Ctrl+C or quota exhaustion via `quota_detector.py`).

Document fallback invocation in CHANGELOG `[1.0.6]` Process notes.

**Worker headless audit** (iter-1 cas WARNING addressed): `auto --parallel` workers DO inherit `SBTDD_HEADLESS` env var from parent process (subprocess inheritance). Workers' `sys.stdin` is typically NOT a TTY (subprocess pipe). So `is_headless_context()` will return True in worker context. **However, workers do NOT dispatch interactive skills** — they execute `close-phase` + `close-task` automation only, which use deterministic git operations + state file writes. The J-3 guard in `superpowers_dispatch.invoke_skill` should NOT fire in worker context because no worker-reachable code path invokes `_SUBPROCESS_INCOMPATIBLE_SKILLS` skills. If it DOES fire, that's a real bug surfacing — abort criterion (b) catches it. Audit before mid-cycle dispatch:

```bash
grep -rn "invoke_skill" skills/sbtdd/scripts/auto_cmd.py skills/sbtdd/scripts/close_phase_cmd.py skills/sbtdd/scripts/close_task_cmd.py 2>&1 | grep -v "^#"
```

Expected: no `invoke_skill` callsites in the worker-reachable code path. Document audit results in CHANGELOG `[1.0.6]` Process notes.

### Activity F-Resume — `/sbtdd spec --resume-from-magi` empirical validation

**Owner**: orchestrator.
**When**: AFTER Track A close + Item J-1+J-2+J-3 landed.
**Wall-time**: ~30 min.

**Steps**:

```bash
# Hand-craft sbtdd/spec-behavior.md + planning/claude-plan-tdd-org.md in
# interactive Claude Code session via /brainstorming + /writing-plans
# (already done for v1.0.6 cycle; same artifacts can be re-used).

# Then invoke --resume-from-magi
python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
```

Expected: structural validation passes (INV-27 + spec snapshot + plan checkboxes) → MAGI Checkpoint 2 dispatched → verdict received per cap=3 HARD G1 binding. Now feasible end-to-end since v1.0.6 Pillar A J-1+J-2+J-3 empowers the recovery path semantically (no subprocess hang).

Document outcome in CHANGELOG `[1.0.6]` Process notes.

### Activity P2 — Pre-merge gate clean WITHOUT INV-0 (Q3=a strict)

**Owner**: orchestrator.
**When**: AFTER all 7 plan tasks closed + Activity F-A2 confirmed.
**Wall-time**: variable (~1-2 hours best case; up to ~1 day with mini-cycle iterations).

**Steps**:

```bash
# Interactive TTY context (post Pillar A landed)
python skills/sbtdd/scripts/run_sbtdd.py pre-merge
```

Expected: Loop 1 (`/requesting-code-review`) iterates until clean-to-go. Loop 2 (`/magi:magi`) iterates until verdict >= `GO_WITH_CAVEATS` full no-degraded.

Per Q3=a strict no-INV-0 stance: if Loop 2 doesn't converge cleanly within cap=5, escalate to user BEFORE applying INV-0 override. G2 binding pre-staged: scope-trim ladder defers K-2..K-5 polish first → defers C.2 second → only Pillar A J-1+J-2+J-3 hard-LOCKED.

**2-cycle pre-merge Loop 2 streak goal**: v1.0.5 re-established the streak from 1 cycle post-v1.0.4 break. v1.0.6 = 2 cycles consecutive sin INV-0 goal.

Document outcome in CHANGELOG `[1.0.6]` Process notes.

---

## Plan invariants summary

- **7 active plan tasks** distributed across 4 parallel subagent tracks
  (Track A 1 task T1; Track B 3 tasks T3+T5+T7 sequential; Track C 2
  tasks T4+T6 sequential; Track D 1 task T2).
- **5 mid-cycle methodology activities** executed by orchestrator
  (F-J9 `/sbtdd spec` headless validation + F-J10 `/sbtdd pre-merge`
  headless validation + F-A2 `auto --parallel` self-dispatch dogfood
  + F-Resume `/sbtdd spec --resume-from-magi` validation + P2
  pre-merge gate clean WITHOUT INV-0).
- **Per-phase close-phase mandate** applied to ALL 7 tasks per Q3
  Option B v1.0.4 mandate + v1.0.5 Item D Q3-A HARD-BLOCK enforced
  via `_preflight` (renamed post-T5 K-3).
- **Cero file overlap** between Track A + Track B + Track C + Track D
  surfaces (verified via spec sec.5.1 expected partition; runtime
  `partition_by_tracks` enforces).
- **Within-track sequential ordering**: Track B (T3 → T5 → T7;
  shared close_task_cmd.py); Track C (T4 → T6; shared auto_cmd.py).
- **Cross-track import dependency (v1.0.5 carry-forward, iter-1 bal WARNING relaxation)**:
  T4 K-2 removes the v1.0.5 `getattr` noop fallback that defended
  against Track Alpha → Track Beta cross-track import dependency
  development. T4 can run TRULY PARALLEL with Track B (T3+T5+T7)
  because the late-import inside `_dispatch_tracks_concurrent`
  resolves at CALL-TIME, NOT module-load-time. `_merge_scratch_plans`
  already ships in v1.0.5 — no missing-helper risk during impl.
  (Pre-iter-1 plan over-stated this dependency; relaxed per bal
  WARNING #6.)
- **Tests baseline**: 1248 + 1 skipped → ~1258-1265 final.
- **Coverage threshold**: >= 88% (per Q4 v1.0.2 baseline).
- **`make verify` runtime**: <= 200s soft / 220s hard NF-A
  (acknowledges v1.0.5 baseline 171s + new tests).
- **MAGI Checkpoint 2**: cap=3 HARD G1 binding; iter-2 CRITICAL
  trigger preserved; G2 scope-trim ladder defers K-2..K-5 first
  → C.2 second; Pillar A J-1+J-2+J-3 hard-LOCKED.
- **Pre-merge Loop 2**: cap=5 with strict no-INV-0 stance per Q3=a;
  escalate to user BEFORE applying INV-0 override.
- **No `Co-Authored-By`, no AI references, English commits, no force
  push** per `~/.claude/CLAUDE.md` Git rules.

---

## Self-review summary

**Spec coverage**:
- F1 (J-1+J-2 helper) → T1 Steps 1-7
- F2 (J-3 enforcement) → T1 Steps 8-12
- F3 (C.2) → T2 Steps 1-10
- F4 (K-1 per-checkbox) → T3 Steps 1-9
- F5 (K-2 getattr removal) → T4 Steps 1-9
- F6 (K-3 rename + alias) → T5 Steps 1-10
- F7 (K-4 argparse guard) → T6 Steps 1-9
- F8 (K-5 CC scope) → T7 Steps 1-11

All 8 functional requirements have plan tasks. All 27 BDD escenarios
(J-1..J-10 + C2-1..C2-3 + K-1a..K-1e + K-2 + K-3a..K-3c + K-4a..K-4b
+ K-5a..K-5d + A-1..A-2) covered by tasks (A-1+A-2 covered by
mid-cycle Activity F-A2 dogfood, not standalone task).

**Placeholder scan**: no INV-27 marker patterns nor implement-later
language. All steps contain actual code or exact commands.

**Type consistency**: helper signatures consistent across tasks
(`is_headless_context() -> bool`, `extract_prefix_from_subject(str) -> str | None`,
`_preflight(state, project_root, *, skip_preflight=False)`, etc.).

**Within-track + cross-track ordering**: Track B sequential T3 → T5 → T7
documented; Track C sequential T4 → T6 documented; Track A + Track D
isolated. T4 K-2 cross-track ordering after T3+T5+T7 documented in
plan invariants.
