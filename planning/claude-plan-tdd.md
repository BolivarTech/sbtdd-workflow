# v1.0.1 Plugin Self-Hosting Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.0.1 = "Plugin self-hosting fix" — 4 items addressing 3 dogfood findings of v1.0.0, plus a pre-migration step:
- **A1** permissive escenario regex (Finding B fix in `spec_snapshot.emit_snapshot`)
- **Pre-A2** audit + migration of direct `invoke_skill` callers (3 production + 4 test sites; opt them into `allow_interactive_skill=True` BEFORE A2's gate lands)
- **A0** output validation tripwire with composite signature mtime+size+sha256 (Finding C fix in `spec_cmd._run_spec_flow`)
- **A2** headless-mode detection with `allow_interactive_skill` kwarg (Finding A mitigation in `superpowers_dispatch.invoke_skill`)
- **A3** `--resume-from-magi` recovery flag with structural validation (supports A2 in `spec_cmd._build_parser` + `main`)

**Architecture:** Single-subagent sequential execution (bundle is small, ~12-17h). All items modify compatible files — no cross-subagent partition needed.

**Sequential ordering**: A1 → Pre-A2 → A0 → A2 → A3 (per spec sec.5 rationale — A1 unblocks own-cycle pre-merge first; Pre-A2 prepares callers for A2's safe-by-default gate; A0 is permanent defense-in-depth runtime tripwire (NOT redundant with A2's static gate — A0 catches future regressions in the set membership and FS-precision edge cases); A2 patches root cause for the known set; A3 enables recovery path with structural validation of operator-produced artifacts).

**Tech Stack:** Python 3.9+, threading + dataclasses + re + pathlib (stdlib only), pytest, ruff, mypy --strict.

---

## Pre-flight contracts

### Branch + working tree

- Branch: working on `feature/v1.0.1-bundle` (branched from `main` HEAD `0992407` = v1.0.0 ship).
- Working tree clean before each task starts. Verify via `git status` empty.
- Implementation commits land on the dev branch; merge to main only after pre-merge gate passes.

### NF-A budget

`make verify` <= 150s budget. Soft-target <= 140s (W6 caspar iter 2: relaxed from <=130s to account for sha256 hashing CPU cost in `_file_signature`). v1.0.0 baseline 117s + ~21 new tests should keep under target.

### Surfaces

| File | Owner | Edit type |
|------|-------|-----------|
| `skills/sbtdd/scripts/spec_cmd.py` | A0 + A3 | Add `_file_signature` helper + extend `_run_spec_flow` (composite-signature checks); extend `_build_parser` + `main` (resume flag + structural validation) |
| `skills/sbtdd/scripts/spec_snapshot.py` | A1 | Refactor `emit_snapshot` (Tier 1 + Tier 2) |
| `skills/sbtdd/scripts/superpowers_dispatch.py` | Pre-A2 + A2 | Pre-A2: opt `_make_wrapper` (line ~291) + `_invoke_skill` (line ~369-370) into `allow_interactive_skill=True`. A2: add `_SUBPROCESS_INCOMPATIBLE_SKILLS` + extend `invoke_skill` with `allow_interactive_skill` kwarg + safe-by-default gate. |
| Test files | per-item | tests/test_spec_cmd.py, tests/test_spec_snapshot.py, tests/test_superpowers_dispatch.py (Pre-A2: opt 4 callsites into override) |

### Plan-approved contract

Once `/sbtdd spec` approves this plan (sets `plan_approved_at`), the four authorized commit categories per CLAUDE.local.md §5 fire automatically: phase close (test:/feat:/fix:/refactor:), task close (chore:), Loop 1 mini-cycle, Loop 2 mini-cycle.

---

## Task A1: Permissive escenario regex (`spec_snapshot.emit_snapshot`)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_snapshot.py:104-130` (function `emit_snapshot`)
- Test: `tests/test_spec_snapshot.py` (add 5 new tests; preserve existing tests)

**Per-spec scenarios to satisfy**: A1-1, A1-2, A1-3, A1-4, A1-5 (sec.4 of spec).

- [ ] **Step 1: Write failing test for A1-2 (distributed escenarios)**

Add to `tests/test_spec_snapshot.py` a test asserting that a spec with `**Escenario X-1: ...**` blocks distributed across `## 2. Pillar 1` + `## 3. Pillar 2` (no `## §4 Escenarios` header) parses correctly. Returns dict with both escenario titles.

- [ ] **Step 2: Run test — should FAIL with ValueError**

Run: `python -m pytest tests/test_spec_snapshot.py::test_emit_snapshot_distributed_escenarios_across_sections -xvs`
Expected: FAIL with `ValueError: No §4 Escenarios section found`.

- [ ] **Step 3: Commit Red phase**

```bash
git add tests/test_spec_snapshot.py
git commit -m "test: A1-2 distributed escenarios across pillar sections (Red)"
```

- [ ] **Step 4: Refactor `emit_snapshot` to Tier 1 + Tier 2**

Modify `spec_snapshot.py emit_snapshot`:
1. Tier 1: search `_SECTION_RE` for legacy `## §4 Escenarios` header. If matched AND `_extract_scenarios` returns non-empty, return that.
2. Tier 2 (fallback): if Tier 1 missed (no header) OR matched section is empty, run `_extract_scenarios` on whole document text.
3. If both tiers yield zero, raise `ValueError` with message mentioning both legacy + distributed patterns.

- [ ] **Step 5: Run test — should PASS**

Run: `python -m pytest tests/test_spec_snapshot.py::test_emit_snapshot_distributed_escenarios_across_sections -xvs`
Expected: PASS.

- [ ] **Step 6: Run full spec_snapshot test suite — verify no regressions**

Run: `python -m pytest tests/test_spec_snapshot.py -v`
Expected: ALL pass (existing Tier 1 path tests still work).

- [ ] **Step 7: Commit Green phase**

```bash
git add skills/sbtdd/scripts/spec_snapshot.py
git commit -m "feat: A1 emit_snapshot Tier 2 fallback for distributed escenarios"
```

- [ ] **Step 8: Add 4 more A1 tests (Refactor)**

Add tests for:
- A1-1 (legacy fixture regression).
- A1-3 (zero-match guard).
- A1-4 (legacy header empty falls through).
- A1-5 (prose mention of word "escenario" in commentary doesn't match scenario regex — Tier 2 widening must NOT match plain prose, only structured `**Escenario X: ...**` / `## Escenario X: ...` / `### Escenario X: ...` blocks).

- [ ] **Step 9: Run new tests + full suite**

Run: `python -m pytest tests/test_spec_snapshot.py -v`
Expected: ALL pass.

- [ ] **Step 10: Commit Refactor**

```bash
git add tests/test_spec_snapshot.py
git commit -m "test: A1 round-out coverage with A1-1/A1-3/A1-4 (Refactor)"
```

- [ ] **Step 11: Mark task complete**

```bash
# Mark [x] in plan
git add planning/claude-plan-tdd.md .claude/session-state.json
git commit -m "chore: mark task A1 complete"
```

---

## Task Pre-A2: Audit + Migration of direct invoke_skill callers

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py:291` (in `_make_wrapper` factory body)
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py:369-370` (in `_invoke_skill`)
- Modify: `tests/test_superpowers_dispatch.py:41,67,85,98` (4 direct callsites)

**Rationale**: A2 will gate `invoke_skill(skill="brainstorming"|"writing-plans")` behind `allow_interactive_skill=False` default. Production wrappers and existing tests legitimately call `invoke_skill` with these names — they must opt into the override BEFORE A2 lands or A2 silently breaks them.

**Empirical audit (from /receiving-code-review iter 1 triage grep)**:

| Site | File | Line | Migration |
|------|------|------|-----------|
| Production | superpowers_dispatch.py | 291 | `_make_wrapper` factory: pass `allow_interactive_skill=True` |
| Production | superpowers_dispatch.py | 369-370 | `_invoke_skill` helper: pass `allow_interactive_skill=True` |
| Test | test_superpowers_dispatch.py | 41 | `invoke_skill("brainstorming", ..., allow_interactive_skill=True)` |
| Test | test_superpowers_dispatch.py | 67 | same |
| Test | test_superpowers_dispatch.py | 85 | same |
| Test | test_superpowers_dispatch.py | 98 | `invoke_skill("writing-plans", ..., allow_interactive_skill=True)` |

- [ ] Step 1: grep audit (output captured above as evidence)
- [ ] Step 2: edit `_make_wrapper` factory body line 291
- [ ] Step 3: edit `_invoke_skill` line 369-370
- [ ] Step 4: edit 4 test callsites in test_superpowers_dispatch.py
- [ ] Step 5: run `make verify` — all should pass (override permits same behavior)
- [ ] Step 6: commit `refactor: pre-A2 migrate direct invoke_skill callers to wrapper-aware override`
- [ ] Step 7: mark task complete chore: commit

---

## Task A0: Output validation tripwire (`spec_cmd._run_spec_flow`)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_cmd.py:112-133` (function `_run_spec_flow`; add `_file_signature` helper)
- Test: `tests/test_spec_cmd.py` (add 5 new tests)

**Per-spec scenarios to satisfy**: A0-1, A0-2, A0-3, A0-4, A0-5 (sec.4 of spec).

- [ ] **Step 1: Write failing test for A0-1 (brainstorming silently no-op)**

Add to `tests/test_spec_cmd.py` a test where:
- Pre-existing `sbtdd/spec-behavior.md` exists.
- `superpowers_dispatch.brainstorming` monkeypatched to a no-op stub.
- Run `_run_spec_flow(tmp_path)`.
- Assert `PreconditionError` raised with message containing "no fue modificado".

- [ ] **Step 2: Run test — should FAIL**

Expected: FAIL — currently no mtime check, so PreconditionError NOT raised about unchanged mtime.

- [ ] **Step 3: Commit Red phase**

```bash
git add tests/test_spec_cmd.py
git commit -m "test: A0-1 brainstorming no-op mtime check (Red)"
```

- [ ] **Step 4: Extend `_run_spec_flow` with composite-signature checks (`_file_signature` helper)**

Modify `spec_cmd.py:112`:
1. Add module-level helper `_file_signature(path: Path) -> tuple[int, int, str]` returning `(mtime_ns, size, sha256_of_content)`. Uses `hashlib.sha256` + chunked read (65536 bytes). See spec sec.2.1 pseudo-code for exact shape.
2. In `_run_spec_flow`: capture `spec_sig_before = _file_signature(path) if path.exists() else None` for spec_behavior.
3. Call `superpowers_dispatch.brainstorming(...)`.
4. Check `path.exists()` (existing) + new composite check: `if sig_before is not None and _file_signature(path) == sig_before: raise PreconditionError(...)`. Compare full tuple equality — equal tuple → no-op detected.
5. Same pattern for `plan_org` after `writing_plans()`.
6. First-run path (file absent pre-subprocess) tolerated by `sig_before is None` short-circuit.
7. Composite signature is resilient against three failure modes: FS-precision floors (mtime collision), same-content rewrite, and touched-but-empty subprocess output. See spec sec.2.1 rationale.

- [ ] **Step 5: Run test — should PASS**

- [ ] **Step 5b: Write failing test for A0-5 (FS-precision same-content rewrite)**

Add to `tests/test_spec_cmd.py` a test where:
- Pre-existing `sbtdd/spec-behavior.md` exists with known content C.
- Monkeypatch `_file_signature` (or stage the file) so that pre and post signatures collide on `mtime_ns` (simulate fast-clock FS) AND content is rewritten with **identical bytes** (same size, same sha256). Result: `_file_signature` returns the SAME tuple before and after — composite-equality detects no-op.
- Assert `PreconditionError` raised with message containing "no fue modificado" and "composite signature".

Run the test — should PASS once the composite-signature implementation is in place. This regression-guards against the FS-precision class documented in spec sec.2.1.

- [ ] **Step 5c: Add 2 edge-case tests for `_file_signature` (W7 caspar iter 2)**

Add to `tests/test_spec_cmd.py`:
1. `test_file_signature_handles_empty_file` — file with size 0 returns signature `(mtime_ns, 0, sha256(b""))` where `sha256(b"")` is the well-known constant `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. Asserts the helper handles empty content correctly.
2. `test_file_signature_handles_large_file` — file >100MB (use `tmp_path / "large.bin"` written via streaming chunked write). Confirm `_file_signature` reads via 64KB chunks (per impl) and returns correct sha256 without loading whole file into memory. Use `@pytest.mark.slow` marker since this is a multi-second test on slower disks.

These edge cases close the W7 caspar concern about composite-signature edge case test coverage. Skip binary content since production specs are text-only (UTF-8); empty + large suffice.

- [ ] **Step 6: Add 3 more A0 tests**

Tests for A0-2 (writing_plans no-op), A0-3 (first-run path), A0-4 (happy path).

- [ ] **Step 7: Run full spec_cmd test suite**

Run: `python -m pytest tests/test_spec_cmd.py -v`
Expected: ALL pass (existing tests with stubs that DO write the files still happy).

- [ ] **Step 8: Commit Green + Refactor**

```bash
git add skills/sbtdd/scripts/spec_cmd.py tests/test_spec_cmd.py
git commit -m "feat: A0 mtime tripwire in _run_spec_flow"
```

- [ ] **Step 9: Mark task complete**

```bash
git commit -m "chore: mark task A0 complete"
```

---

## Task A2: Headless-mode detection (`superpowers_dispatch.invoke_skill`)

**Files:**
- Modify: `skills/sbtdd/scripts/superpowers_dispatch.py:135-209` (function `invoke_skill` + add module-level set + `allow_interactive_skill` kwarg)
- Test: `tests/test_superpowers_dispatch.py` (add 5 new tests)

**Per-spec scenarios to satisfy**: A2-1, A2-2, A2-3, A2-4, A2-5.

- [ ] **Step 1: Write failing test for A2-1**

Add test asserting `invoke_skill(skill="brainstorming", args=[...])` raises `PreconditionError` with message containing "es interactivo".

- [ ] **Step 2: Run test — should FAIL**

Expected: FAIL — currently invoke_skill spawns subprocess regardless.

- [ ] **Step 3: Commit Red**

```bash
git add tests/test_superpowers_dispatch.py
git commit -m "test: A2-1 brainstorming headless detection (Red)"
```

- [ ] **Step 4: Add `_SUBPROCESS_INCOMPATIBLE_SKILLS` set + safe-by-default gate with `allow_interactive_skill` kwarg**

Modify `superpowers_dispatch.py`:
1. Module-level: `_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset({"brainstorming", "writing-plans"})`. Renamed from the working-name `_INTERACTIVE_ONLY_SKILLS` per /receiving-code-review iter 1 W1 triage — the new name reflects the actual cause (subprocess transport is incompatible) rather than the symptom (interactivity).
2. Add new kwarg `allow_interactive_skill: bool = False` to `invoke_skill` signature.
3. In `invoke_skill` body, BEFORE subprocess:
   ```python
   if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
       raise PreconditionError(...)  # see spec sec.2.3 message
   ```
4. Import `PreconditionError` from `errors`.

**Note**: this step assumes Task Pre-A2 has already migrated the 3 production callsites + 4 test callsites to pass `allow_interactive_skill=True`. If Pre-A2 was skipped or partial, A2's gate will silently break those callsites at this step — verify Pre-A2 is fully landed before proceeding.

- [ ] **Step 5: Run test — should PASS**

- [ ] **Step 6: Add 4 more A2 tests**

Tests for A2-2 (writing-plans), A2-3 (regression: magi:magi or other non-interactive), A2-4 (whitelist semantic — unknown skill passes through), A2-5 (wrapper functions pass `allow_interactive_skill=True` internally so direct wrapper call still works — regression-guards against blanket-raise pattern).

- [ ] **Step 7: Update existing tests that direct-call `invoke_skill(skill="brainstorming")`**

Review test suite for direct calls. Replace with calls to wrapper functions (`brainstorming()`, `writing_plans()`) that monkeypatch the wrapper itself, not the underlying `invoke_skill`.

- [ ] **Step 8: Run full test suite**

Run: `make verify`
Expected: ALL pass, runtime <= 150s.

- [ ] **Step 9: Commit Green + Refactor**

```bash
git add skills/sbtdd/scripts/superpowers_dispatch.py tests/test_superpowers_dispatch.py tests/...
git commit -m "feat: A2 _INTERACTIVE_ONLY_SKILLS headless detection"
```

- [ ] **Step 10: Mark task complete**

```bash
git commit -m "chore: mark task A2 complete"
```

---

## Task A3: `--resume-from-magi` recovery flag

**Files:**
- Modify: `skills/sbtdd/scripts/spec_cmd.py:79-99` (`_build_parser`) + `:333-348` (`main`)
- Test: `tests/test_spec_cmd.py` (add 5 new tests across 6 escenarios)

**Per-spec scenarios to satisfy**: A3-1, A3-2, A3-3, A3-4, A3-5, A3-6.

- [ ] **Step 1: Write failing test for A3-1**

Add test where:
- Pre-stage `sbtdd/spec-behavior.md` and `planning/claude-plan-tdd-org.md` (operator-produced).
- Spies for brainstorming + writing_plans that `pytest.fail` if called.
- Stub `magi_dispatch.invoke_magi` to return GO verdict.
- Call `spec_cmd.main(["--project-root", str(tmp), "--resume-from-magi"])`.
- Assert dispatch spies NOT called; state file exists post-call.

- [ ] **Step 2: Run test — should FAIL**

Expected: FAIL — `--resume-from-magi` flag doesn't exist (argparse error: unrecognized argument).

- [ ] **Step 3: Commit Red**

```bash
git add tests/test_spec_cmd.py
git commit -m "test: A3-1 --resume-from-magi flag skips dispatch (Red)"
```

- [ ] **Step 4: Add flag to parser + skip logic in main + structural validation**

Modify `_build_parser` to add `--resume-from-magi` flag (`action="store_true"`).

Modify `main`:
1. Always run `_validate_spec_base_no_placeholders` (INV-27 hard) — moved OUTSIDE the `if not ns.resume_from_magi:` block per W4 spec/plan alignment fix.
2. Always load `cfg`.
3. If `not ns.resume_from_magi`: run `_run_spec_flow(root)`.
4. Else (`--resume-from-magi` path): structural validation BEFORE MAGI dispatch (W2/W8 fix; existence-only check is insufficient — empty/stub spec wastes a MAGI iter):
   - Call `spec_snapshot.emit_snapshot(spec_behavior_path)`. Must succeed (returns non-empty dict). Else `PreconditionError` referencing the spec path + the underlying parse error. Catches `FileNotFoundError` AND `ValueError`.
   - Read `plan_org` text. Assert `re.search(r"^###\s+Task\b", text, re.MULTILINE)` matches (>= 1 task heading) AND `re.search(r"^-\s+\[\s\]", text, re.MULTILINE)` matches (>= 1 unchecked checkbox). Else `PreconditionError` identifying which structural check failed.
5. Continue with `_run_magi_checkpoint2` + `_create_state_file` + `_mark_plan_approved_with_snapshot` + `_commit_approved_artifacts` (unchanged).

- [ ] **Step 5: Run test — should PASS**

- [ ] **Step 6: Add A3 combinatorial + structural tests (4 combinatorial cases + 2 structural-validation cases)**

**Combinatorial tests for the flag matrix** (W10 expansion — all four combinations of `--resume-from-magi` × `--override-checkpoint`):
- (a) `--resume-from-magi` only (skip dispatch, normal MAGI cap=3 path).
- (b) `--override-checkpoint --reason=...` only (no resume; safety-valve override; corresponds to A3-4 base scenario without resume).
- (c) Both `--resume-from-magi --override-checkpoint --reason=...` (A3-4: dispatch skipped + safety-valve override path active).
- (d) Neither flag (happy-path regression — full dispatch + normal cap=3).

**Plus structural-validation tests**:
- A3-2 (INV-27 still validated even with flag — moved validation outside conditional per W4).
- A3-3 (artifacts missing → abort with `PreconditionError`).
- A3-5 (malformed spec rejected — `spec_snapshot.emit_snapshot` raises `ValueError` or returns empty dict; structural check fires before MAGI dispatch).
- A3-6 (malformed plan rejected — missing `### Task` heading OR missing `- [ ]` checkbox; structural check fires before MAGI dispatch).
- **A3-7 exception leakage regression** (W3 caspar iter 2): monkeypatch `spec_snapshot.emit_snapshot` to raise `OSError("simulated FS read failure")`; assert `--resume-from-magi` path catches it (per widened `except (FileNotFoundError, ValueError, OSError)` in spec sec.2.4) and re-raises as `PreconditionError`, NOT a leaked OSError to the operator. Regression-guards the W3 widening.

- [ ] **Step 7: Run full test suite**

Run: `make verify`
Expected: ALL pass.

- [ ] **Step 8: Commit Green**

```bash
git add skills/sbtdd/scripts/spec_cmd.py tests/test_spec_cmd.py
git commit -m "feat: A3 --resume-from-magi recovery flag with INV-27 preserved"
```

- [ ] **Step 9: Update README + SKILL.md**

Document the new flag with example use case (recovery after manual brainstorming).

- [ ] **Step 10: Commit docs**

```bash
git add README.md skills/sbtdd/SKILL.md
git commit -m "docs: A3 --resume-from-magi user docs"
```

- [ ] **Step 11: Mark task complete**

```bash
git commit -m "chore: mark task A3 complete"
```

---

## Task O-1: Final make verify

- [ ] **Step 1: Run make verify**

Run: `make verify`
Expected: ~1054-1058 passed + 1 skipped, runtime <= 150s.

- [ ] **Step 2: Verify test count delta**

Should be ~1054-1058 (1033 baseline + ~21 new from A1=5 + A0=5 + A2=5 + A3=6 + Pre-A2=0 net new + iter 1 triage expansion).

---

## Task O-2: Pre-merge MAGI gate

- [ ] **Step 1: Verify `magi_cross_check: true` in plugin.local.md**

- [ ] **Step 2: Run `/sbtdd pre-merge`**

Run: `python skills/sbtdd/scripts/run_sbtdd.py pre-merge`
Expected: Loop 1 clean-to-go, Loop 2 verdict >= GO_WITH_CAVEATS full.

**Note**: If `/sbtdd pre-merge` itself breaks during the v1.0.1 own-cycle (chicken-and-egg: A0/A1/A2/A3 fixes shipping in this cycle ARE the same code path that pre-merge exercises), fall back to manual `python skills/magi/scripts/run_magi.py code-review <payload>` direct dispatch + manual mini-cycle commits per spec sec.6.5. Document the fallback choice + iteration in CHANGELOG `[1.0.1]` Process notes. v0.5.0 + v1.0.0 ship cycles set precedent for this manual fallback.

- [ ] **Step 3: For each Loop 2 finding, run `/receiving-code-review` per INV-29**

- [ ] **Step 4: Apply ACCEPT findings via mini-cycle TDD**

- [ ] **Step 5: Verify cross-check audit artifacts present in `.claude/magi-cross-check/`**

This is the v1.0.1 first-time own-cycle dogfood signal of Feature G.

---

## Task O-3: Version bump 1.0.0 → 1.0.1

- [ ] **Step 1: Bump versions in plugin.json + marketplace.json**

- [ ] **Step 2: Update CHANGELOG `[1.0.1]` entry + CLAUDE.md release notes pointer**

Sections: Added (A0/A1/A2/A3 features), Fixed (Findings A/B/C), Process notes (dogfood lessons + INV-37 + items rolled to v1.0.2), Deferred (4 items rolled forward to v1.0.2).

**I5 cross-reference**: Add INV-37 to `CLAUDE.md` Invariants Summary section as part of the v1.0.1 release notes pointer (per /receiving-code-review iter 1 I5 triage). The invariant text per spec sec.2.1: "INV-37 — `_run_spec_flow` DEBE validar outputs de superpowers_dispatch.brainstorming/writing_plans via composite-signature check (mtime_ns + size + sha256), no solo existence."

- [ ] **Step 3: Run make verify clean**

- [ ] **Step 4: Commit version bump**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json CHANGELOG.md
git commit -m "chore: bump to 1.0.1"
```

---

## Task O-4: Tag v1.0.1 + push

- [ ] **Step 1: Merge feature branch to main**

```bash
git checkout main
git merge --no-ff feature/v1.0.1-bundle -m "Merge for v1.0.1 release"
```

- [ ] **Step 2: Tag v1.0.1**

```bash
git tag -a v1.0.1 HEAD -m "v1.0.1 — Plugin self-hosting fix"
```

- [ ] **Step 3: PAUSE for explicit user authorization (per CLAUDE.md global rule)**

- [ ] **Step 4: Push (after authorization)**

```bash
git push origin main
git push origin v1.0.1
```

- [ ] **Step 5: Cleanup local branch**

```bash
git branch -d feature/v1.0.1-bundle
```

---

## Plan summary

| Task | Item | Files | Est. time | Tests added |
|------|------|-------|-----------|-------------|
| A1 | Permissive escenario regex | spec_snapshot.py | 2-3h | 5 |
| Pre-A2 | Migrate direct invoke_skill callers | superpowers_dispatch.py + tests | 0.5-1h | 0 (refactor; existing tests cover) |
| A0 | Output validation tripwire (composite signature) | spec_cmd.py | 2-3h | 5 |
| A2 | Headless-mode detection (allow_interactive_skill kwarg) | superpowers_dispatch.py | 2-3h | 5 |
| A3 | --resume-from-magi flag (+ structural validation) | spec_cmd.py | 3-4h | 6 |
| O-1 | Final make verify | (verification) | 0.5h | 0 |
| O-2 | Pre-merge MAGI gate | (review) | 1-2h | 0 |
| O-3 | Version bump | manifests + CHANGELOG + CLAUDE.md INV-37 | 0.5h | 0 |
| O-4 | Tag + push | git ops | 0.5h | 0 |
| **Total** | | | **~12-17h** | **~21 new tests** |

**Single-pillar discipline preserved**. G1 binding cap=3 HARD for Checkpoint 2; bundle small enough to converge in 1-2 iters expected.

**Deferred to v1.0.2** (per CHANGELOG `[1.0.0]` Deferred + `[1.0.1]` Process notes):
- Cross-check telemetry aggregation script
- Cross-check prompt diff threading (W-NEW1)
- H5-2 spec_lint enforcement
- Own-cycle cross-check dogfood

**Deferred to v1.0.3** (CHANGELOG `[1.0.0]` Deferred):
- Parallel task dispatcher with deferred MAGI gate
