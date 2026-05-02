# BDD overlay — sbtdd-workflow v1.0.0

> Generado por `/brainstorming` el 2026-05-02 a partir de
> `sbtdd/spec-behavior-base.md` (v1.0.0 raw input post-v0.5.0).
>
> v1.0.0 ships dos pillars + v0.5.1 fold-in en single bundle per user
> directive 2026-05-02 ("v1.0.0 directo with v0.5.1 fold-in", layout A
> "2 parallel disjoint subagents"):
> - **Pillar 1** — MAGI quality / observability completion (Feature G
>   cross-check meta-reviewer + F44.3 retried_agents propagation + J2
>   ResolvedModels preflight)
> - **Pillar 2** — Schema/infrastructure (Feature I schema_version: 2 +
>   migration tool skeleton + Feature H Group B option 2 spec-snapshot +
>   option 5 auto-gen scenario stubs)
> - **v0.5.1 fold-in** — J3+J7 production wiring (33 callers) + 4 Caspar
>   Loop 2 iter 4 concerns + Windows tmp PID flake + 5 INFOs housekeeping
>
> Bumpea 0.5.0 -> 1.0.0 (MINOR per Q1=B "1.0 es solo un numero, BREAKINGs
> OK"). Honors "v1.0.0 directo" user directive over reflexive split.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5 frozen se
> mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.0** (3 pillars combined into single cycle):

1. **Pillar 1 — MAGI quality** completes the empirical observation from
   v0.5.0 cycle that MAGI Loop 2 generates false-positive CRITICAL
   findings without a meta-review pass. Feature G adds `/requesting-
   code-review` as cross-check filter between MAGI verdict and INV-29
   triage. Plus F44.3 retried_agents audit + J2 ResolvedModels preflight
   cache (cost optimization).

2. **Pillar 2 — Schema/infrastructure** future-proofs the
   `plugin.local.md` schema against future breaking changes via
   `schema_version: int = 1` field + migration tool skeleton. Plus
   Feature H Group B options 2 (spec-snapshot diff check at pre-merge)
   + 5 (auto-gen scenario stubs from `/writing-plans`) — spec-drift
   detection mechanisms beyond INV-29.

3. **v0.5.1 fold-in** (LOCKED commitments rolled forward per CHANGELOG
   `[0.5.0]`): J3+J7 production wiring (heartbeat helper actually exercised
   in production paths instead of just shipping the helper), 4 Caspar
   Loop 2 iter 4 structural concerns, Windows tmp filename PID collision
   flake fix, 5 INFOs housekeeping pass.

**Out-of-scope v1.0.0** (defer a v1.x):
- INV-31 default flip decision (dedicated cycle with field-data doc).
- Group B options 1, 3, 4, 6, 7 (opt-in flags only, not core).
- GitHub Actions CI workflow.

**Criterio de exito:**
- Tests baseline 930 + 1 skipped preservados + ~30-40 nuevos = 960-970.
- `make verify` clean (pytest + ruff + mypy --strict, runtime <= 120s).
- MAGI Loop 2 reliability sostenida; cross-check (Feature G) catches
  false-positive CRITICALs during own ship cycle (recursive payoff).
- 33 J3+J7 callers wired; heartbeat fires in all production long
  dispatches.
- Schema migration framework operational (no-op for v1 -> v2;
  populated when needed).

**Recursive payoff oportunity:** Feature G (cross-check) shipped en
este cycle. Once wired during Subagent #1 implementation, Loop 2 iter
2+ exercises cross-check on its own diff. Stronger empirical signal
than v0.5.0 heartbeat dogfood.

---

## 2. Pillar 1 — Dispatchers + observability completion

### 2.1 Feature G — MAGI cross-check meta-reviewer (TOP PRIORITY)

**Files tocados:**
- `pre_merge_cmd.py` (new `_loop2_cross_check` sub-phase)
- `auto_cmd.py` (phase4 pre-merge integration)
- `magi_dispatch.py` (audit artifact emit hook)

**Subagent #1 owned.**

**Invariante propuesto:** **INV-35** (renamed from INV-32-bis to avoid
conflict with v0.5.0 INV-32 heartbeat). MAGI Loop 2 findings DEBEN pasar
por cross-check via `/requesting-code-review` antes de routear via
INV-29 gate, salvo que `magi_cross_check: false` este set en
`plugin.local.md`.

**Cross-check semantic (CRITICAL #1+#4 redesign):** cross-check NEVER
removes findings — it ONLY annotates each finding with
`cross_check_decision: KEEP|DOWNGRADE|REJECT` y
`cross_check_rationale: <text>` fields. INV-29 (operator +
`/receiving-code-review`) is the ONLY stage that filters findings. This
guarantees:
- The operator at INV-29 always sees every finding MAGI emitted, plus
  the meta-review's recommendation alongside it.
- If the meta-review is wrong (false-positive REJECT), the real
  CRITICAL/WARNING does NOT get silently dropped — it is still
  presented for INV-29 evaluation, with the review's REJECT rationale
  visible so the operator can override.
- DOWNGRADE follows the same annotation-only pattern: the original
  severity is preserved on the surfaced finding; the review's
  recommended new severity lives in the annotation field
  (`cross_check_recommended_severity`) for operator consideration at
  INV-29.

**Escenarios Given/When/Then:**

**Escenario G1: cross-check annotates false-positive CRITICAL with REJECT**

> **Given** MAGI Loop 2 emits verdict GO_WITH_CAVEATS (3-0) con 1
> CRITICAL marked "auto_cmd._set_progress doesn't validate phase
> argument range". The actual code DOES validate. Cross-check pipeline
> active (config.magi_cross_check=True default).
> **When** `pre_merge_cmd._loop2_cross_check(diff, verdict, findings, iter_n=1)`
> ejecuta.
> **Then** `/requesting-code-review` is invoked with prompt referencing
> spec + plan + diff + MAGI verdict; review output classifies the
> CRITICAL as REJECT with rationale "phase arg validated at line N".
> The returned annotated_findings list has the SAME LENGTH as the
> original findings list (the CRITICAL is NOT removed); the surfaced
> finding has `cross_check_decision: "REJECT"` and
> `cross_check_rationale: "phase arg validated at line N"` fields
> attached. Audit artifact
> `.claude/magi-cross-check/iter1-<timestamp>.json` contains both
> `original_findings` and `annotated_findings` with the per-finding
> decision. INV-29 (operator + `/receiving-code-review`) is the only
> stage that may drop the finding.

**Escenario G2: cross-check annotates valid CRITICAL with KEEP**

> **Given** MAGI Loop 2 emits verdict with 1 valid CRITICAL ("missing
> assertion at line X").
> **When** cross-check ejecuta.
> **Then** review output classifies the CRITICAL as KEEP with rationale.
> The annotated_findings list = original list with each finding
> augmented by `cross_check_decision: "KEEP"` +
> `cross_check_rationale: <text>` fields. No finding removed. Audit
> artifact records the KEEP decision.

**Escenario G3: cross-check annotates over-cautious WARNING with DOWNGRADE**

> **Given** MAGI Loop 2 emits 5 WARNINGs, 2 of which review judges
> low-impact polish issues mistakenly flagged WARNING (review would
> classify as INFO).
> **When** cross-check ejecuta.
> **Then** review output classifies 2 as DOWNGRADE (with recommended
> new severity INFO + rationale). The annotated_findings list has
> SAME LENGTH as original; the 2 affected findings have
> `cross_check_decision: "DOWNGRADE"`,
> `cross_check_rationale: <text>`, and
> `cross_check_recommended_severity: "INFO"` fields attached. The
> finding's own `severity` field remains "WARNING" (annotation-only
> redesign — INV-29 is the only filter). Audit records both decisions
> and the recommended severity.

**Escenario G4: opt-out via `magi_cross_check: false`**

> **Given** `plugin.local.md` con `magi_cross_check: false` field set.
> **When** Loop 2 ejecuta.
> **Then** cross-check sub-phase short-circuits, returns `findings`
> unchanged (no annotations attached), audit artifact NOT written (or
> written with `cross_check_skipped: true` flag). Behavior
> backwards-compatible with v0.5.0 (no cross-check existed).

**Escenario G5: cross-check failure does not block Loop 2**

> **Given** MAGI Loop 2 emits findings; `/requesting-code-review`
> dispatch fails (subprocess error, timeout, output parse failure).
> **When** cross-check error caught.
> **Then** stderr breadcrumb emitted: `[sbtdd magi-cross-check] failed
> (will fall back to MAGI findings as-is): <error>`. Returns original
> `findings` unchanged (no annotations attached). Loop 2 continues to
> INV-29 routing as if cross-check absent. Audit artifact records
> `cross_check_failed: true` + error message. Defensive: cross-check
> is observability/quality feature, never blocks pre-merge gate.

**Escenario G6: cross-check audit artifact JSON schema**

> **Given** any cross-check execution completes.
> **When** audit file written.
> **Then** schema (annotation redesign — `filtered_findings` renamed to
> `annotated_findings`; `original_findings` always preserved verbatim;
> `cross_check_decisions` records the per-finding recommendation):
> ```json
> {
>   "iter": 1,
>   "timestamp": "2026-MM-DDTHH:MM:SSZ",
>   "magi_verdict": "GO_WITH_CAVEATS",
>   "original_findings": [
>     {"severity": "CRITICAL", "title": "...", "detail": "...", "agent": "caspar"}
>   ],
>   "cross_check_decisions": [
>     {"original_index": 0, "decision": "REJECT", "rationale": "...",
>      "recommended_severity": null}
>   ],
>   "annotated_findings": [
>     {"severity": "CRITICAL", "title": "...", "detail": "...",
>      "agent": "caspar", "cross_check_decision": "REJECT",
>      "cross_check_rationale": "...",
>      "cross_check_recommended_severity": null}
>   ]
> }
> ```
> JSON deterministic + parseable post-mortem. Length-preserved
> invariant: `len(annotated_findings) == len(original_findings)`
> always.

**Cross-check annotation carry-forward (caspar Loop 2 iter 2 WARNING):**
when re-invoking MAGI for iter N+1 after iter N findings were partly
rejected by `/receiving-code-review` (INV-29), the orchestrator MUST
include the previous iter's `cross_check_decision` +
`cross_check_rationale` + `cross_check_recommended_severity` fields in
the "Prior triage context" block of the next MAGI payload (per the
v0.5.0 magi-gate carry-forward template). Rationale: this avoids
cross-check re-running its meta-review on findings the operator already
triaged, AND surfaces the prior reviewer's KEEP/DOWNGRADE/REJECT
recommendation so MAGI agents can adjust their next-iter findings rather
than re-emit the same annotated finding. The carry-forward block is
lossless: serialize annotated_findings (full set) so MAGI agents see
both their previous output and the meta-review on top.

**Acceptance criteria mapping:**

| Criterion | Escenarios | Test fixtures |
|-----------|-----------|---------------|
| **Feature G cross-check** | G1-G6 | `tests/test_pre_merge_cross_check.py` (NEW) |
| **INV-35 enforcement** | G1+G4 | combined |
| **Audit artifact schema** | G6 | dedicated |
| **Annotation carry-forward** | sec.7.4 cross-cutting | shared with MAGI dispatch tests |

### 2.2 F44.3 — retried_agents propagation to auto-run.json audit

**Files tocados:** `auto_cmd.py` (`_serialize_progress` o
`_write_auto_run_audit` extension).

**Subagent #1 owned.**

**Background:** v0.4.0 Feature F shipped MAGIVerdict.retried_agents
field parsing. v0.5.0 deferred propagation to auto-run.json. v1.0.0
closes the gap.

**Escenario F44.3-1: retried_agents written to auto-run.json per iter**

> **Given** mid-`auto` MAGI Loop 2 iter 2; MAGI returns verdict with
> `retried_agents=["balthasar"]`.
> **When** `auto_cmd._update_progress` o `_write_auto_run_audit` fires
> post-MAGI dispatch.
> **Then** `auto-run.json` contains
> `magi_iter2_retried_agents: ["balthasar"]` field. Field type
> `list[str]`; empty list `[]` cuando no retries.

**Escenario F44.3-2: backward-compat with v0.4.0 + v0.5.0 files**

> **Given** existing `auto-run.json` from v0.4.0 or v0.5.0 (sin
> magi_iter*_retried_agents fields).
> **When** post-v1.0.0 code reads the file.
> **Then** parses cleanly; absent fields treated as `[]`. NO
> ValidationError for absent field.

### 2.3 J2 — ResolvedModels preflight dataclass

**Files tocados:**
- `models.py` (Subagent #2 owned — defines dataclass shape)
- `auto_cmd.py` (Subagent #1 owned — consumer + preflight cache)

**Cross-subagent contract:** dataclass shape pinned in spec sec.5.

**Background:** `auto_cmd` dispatches read CLAUDE.md ~70-150 times
during 36-task run to resolve per-skill model overrides. Preflight
once instead.

**Escenario J2-1: ResolvedModels caches CLAUDE.md reads**

> **Given** auto run starts; CLAUDE.md exists with INV_0 model pin
> (or doesn't pin); plugin.local.md has per-skill model fields.
> **When** `auto_cmd._phase2_task_loop` entry calls
> `_resolve_all_models_once(config)`.
> **Then** returns `ResolvedModels(implementer=..., spec_reviewer=...,
> code_review=..., magi_dispatch=...)` instance. CLAUDE.md read
> exactly ONCE. plugin.local.md fields read once. Subsequent dispatch
> calls read from cached `ResolvedModels` (zero additional disk reads).

**Escenario J2-2: CLAUDE.md INV-0 pin overrides plugin.local.md**

> **Given** CLAUDE.md contains "Use claude-opus-4-7 for all sessions"
> (INV-0 pinning regex match per `models.INV_0_PINNED_MODEL_RE`).
> plugin.local.md has `magi_dispatch_model: claude-haiku-4-5`.
> **When** `_resolve_all_models_once` ejecuta.
> **Then** ResolvedModels.magi_dispatch == "claude-opus-4-7" (INV-0
> wins per top-authority rule). plugin.local.md fields silently
> overridden + stderr breadcrumb.

**Escenario J2-2b: Global ~/.claude/CLAUDE.md pin wins over project <repo>/CLAUDE.md pin (INV-0 cascade order)**

> **Given** Both `~/.claude/CLAUDE.md` and `<repo>/CLAUDE.md` are
> present and BOTH contain INV-0 pinning regex matches but for
> DIFFERENT models: global pins `claude-opus-4-7` and project pins
> `claude-haiku-4-5`. plugin.local.md has unrelated field values.
> **When** `_resolve_all_models_once` ejecuta the cascade.
> **Then** the cascade reads global FIRST (per INV-0 maxima
> precedencia from CLAUDE.local.md jerarquia: global is top
> authority, cannot be silently overridden by project file). The
> first regex match terminates the cascade, so global wins.
> ResolvedModels.magi_dispatch == "claude-opus-4-7"; the project
> pin `claude-haiku-4-5` is NEVER applied. stderr breadcrumb
> documents the global-pin source. This is the regression guard
> for caspar Loop 2 iter 3 CRITICAL #1 (cascade had been inverted
> in iter 2).

**Escenario J2-3: ResolvedModels immutable**

> **Given** `ResolvedModels` instance returned by preflight.
> **When** test attempts `instance.implementer = "different"`.
> **Then** `FrozenInstanceError` raised (immutable per spec sec.5 contract).

---

## 3. Pillar 2 — Schema/infrastructure

### 3.1 Feature I — schema_version: 2 + migration tool skeleton

**Files tocados:**
- `config.py` (PluginConfig.schema_version field — Subagent #2 owned)
- `scripts/migrate_plugin_local.py` (NEW — Subagent #2 owned)

**Invariante propuesto:** **INV-36**. PluginConfig has `schema_version:
int = 1` field defaulting to 1 cuando absent (backward compat con v0.5.0
files); migrations tracked in `scripts/migrate_plugin_local.py` ladder.

**Escenarios:**

**Escenario I1: v0.5.0 files (no schema_version) load as schema_version=1**

> **Given** `plugin.local.md` from v0.5.0 era (no schema_version field).
> **When** `config.load_plugin_local(path)` parses.
> **Then** `cfg.schema_version == 1` (default applied silently). NO
> ValidationError. Backward compat preserved.

**Escenario I2: v1.0.0 files declare schema_version: 2**

> **Given** `plugin.local.md` con `schema_version: 2` field set.
> **When** parser ejecuta.
> **Then** `cfg.schema_version == 2`. Round-trip serialize-deserialize
> preserves value.

**Escenario I3: migrate v1 to v2 is no-op skeleton**

> **Given** v1 dict (no schema_version).
> **When** `migrate_plugin_local.migrate_to(target_version=2, data=v1_dict)`
> ejecuta.
> **Then** returns dict identico a input + `schema_version: 2` field
> added. Future migrations populate this no-op slot.

**Escenario I4: migration ladder skeleton supports future bumps**

> **Given** `migrate_plugin_local.MIGRATIONS` dict.
> **When** inspected.
> **Then** has entry `{1: lambda d: dict(d, schema_version=2)}` (or
> equivalent skeleton). Adding future migrations is one-line entry per
> version.

### 3.2 Feature H Group B option 2 — Spec-snapshot diff check

**Files tocados:**
- `scripts/spec_snapshot.py` (NEW — Subagent #2 owned)
- `pre_merge_cmd.py` (Subagent #1 owned — integration call wired by plan
  task **S1-26** ``_check_spec_snapshot_drift``)
- `auto_cmd.py` (Subagent #1 owned — plan-approval emit hook wired by
  plan task **S1-27** ``_mark_plan_approved_with_snapshot``)

**Cross-subagent contract:** `spec_snapshot.emit_snapshot(spec_path) -> dict`,
`spec_snapshot.compare(prev: dict, curr: dict) -> diff_dict`,
`spec_snapshot.persist_snapshot(path, snapshot) -> None`, and
`spec_snapshot.load_snapshot(path) -> dict` shapes pinned in spec sec.5.

**Integration contract (CRITICAL #2 fix):** the helpers shipped by
Subagent #2 are wired into the consumer surface by Subagent #1 via two
explicit plan tasks — without these, the spec H2-3 escenario is not
reachable in production. S1-26 wires the drift check at pre-merge entry;
S1-27 wires the emit hook at plan-approval transition. Backward compat:
S1-26 silently skips drift check when ``planning/spec-snapshot.json``
does not exist (pre-v1.0.0 plan-approval flows).

**Escenarios:**

**Escenario H2-1: emit_snapshot extracts scenario hashes**

> **Given** `sbtdd/spec-behavior.md` con seccion `## §4 Escenarios BDD`
> con multiple scenarios.
> **When** `spec_snapshot.emit_snapshot(path)` ejecuta.
> **Then** returns `{scenario_name: hash(Given+When+Then)}` dict per
> scenario. Hash deterministic per scenario content (whitespace-normalized).

**Escenario H2-2: compare detects modified Given/When/Then**

> **Given** prev snapshot from plan-approval time + curr snapshot
> from pre-merge time. Scenario "S1: parser handles empty input" has
> different Given/When/Then text.
> **When** `compare(prev, curr)` ejecuta.
> **Then** returns `{added: [], removed: [], modified: ["S1: parser handles empty input"]}`.

**Escenario H2-3: pre-merge fails when scenarios drifted**

> **Given** plan approved at commit X with snapshot S_X (persisted to
> `planning/spec-snapshot.json` by plan task **S1-27**
> ``_mark_plan_approved_with_snapshot``). Pre-merge at HEAD has
> different spec snapshot S_HEAD (modified Given/When/Then).
> **When** `pre_merge_cmd._check_spec_snapshot_drift` ejecuta at
> pre-merge entry (wired by plan task **S1-26**).
> **Then** raises `PreMergeError("Spec scenarios changed since plan
> approval; re-approve plan via /writing-plans + Checkpoint 2")`.
> Lists modified scenarios in error message.

**Escenario H2-4: snapshot persisted at planning/spec-snapshot.json**

> **Given** plan freshly approved (`plan_approved_at` set in state file).
> **When** plan-approval handler emits snapshot via plan task **S1-27**
> ``_mark_plan_approved_with_snapshot``.
> **Then** `planning/spec-snapshot.json` written with current snapshot.
> Committed alongside `claude-plan-tdd.md`. Pre-merge S1-26 compares
> against this.

### 3.3 Feature H Group B option 5 — Auto-generated scenario stubs

**Files tocados:**
- `superpowers_dispatch.py` (Subagent #2 owned — `invoke_writing_plans`
  prompt extension)

**Escenario H5-1: writing-plans extends prompt with scenario stub generation**

> **Given** spec-behavior.md sec.4 Escenarios with N=10 scenarios.
> Operator invokes `/writing-plans` via SBTDD pipeline.
> **When** `superpowers_dispatch.invoke_writing_plans(spec_path, ...)`
> ejecuta with extended prompt.
> **Then** Generated `planning/claude-plan-tdd-org.md` contains stub
> tests `def test_scenario_<N>_<slug>()` per scenario, with body
> `pytest.skip("Scenario stub: replace with real assertions")` and
> docstring referencing scenario number.

**Escenario H5-2: missing stub at Checkpoint 2 = plan-quality failure**

> **Given** plan generated WITHOUT a stub for one of the spec scenarios
> (operator deleted or `/writing-plans` failed to generate).
> **When** spec_lint or Checkpoint 2 evaluation runs.
> **Then** flags as plan-quality failure: "Scenario N has no
> corresponding stub test in plan; re-run /writing-plans or add manually".

---

## 4. v0.5.1 fold-in

### 4.1 J3 + J7 production wiring (largest fold-in item)

**Files tocados:** `auto_cmd.py` + `pre_merge_cmd.py` (Subagent #1 owned).

**Background:** v0.5.0 shipped `subprocess_utils.run_streamed_with_timeout`
helper but ZERO production callers (per CHANGELOG `[0.5.0]` "Per-stream
timeout (J3, opt-in)" + "Origin disambiguation (J7, opt-in)" with
"Production wiring of existing run_with_timeout callers deferred to v0.5.1").
v1.0.0 closes the gap.

**Escenario W1: 33 callers routed through run_streamed_with_timeout**

> **Given** v0.5.0 codebase has 33 `run_with_timeout(...)` callers
> across `auto_cmd.py` + `pre_merge_cmd.py` for subagent dispatches.
> **When** Subagent #1 implementation completes (T1.11-T1.16).
> **Then** ALL 33 callers route through `run_streamed_with_timeout`
> with appropriate `dispatch_label` (per existing `_set_progress`
> + `_dispatch_with_heartbeat` patterns from v0.5.0). Heartbeat
> actually fires in production for all long dispatches. Per-stream
> timeout actually enforced. Origin disambiguation actually applied.

**Escenario W2: J3 timeout fires for hung subprocesses in production**

> **Given** subprocess dispatch via wired call site; subprocess hangs
> on all open streams >=900s.
> **When** pump checks timeout.
> **Then** subprocess killed via `_kill_subprocess_tree`. Stderr
> breadcrumb. Auto cmd dispatch failure path. (Same as v0.5.0 escenario
> T1, now exercised in production.)

**Escenario W3: magi-* dispatches exempted from timeout in production**

> **Given** wired MAGI Loop 2 dispatch via `_wrap_with_heartbeat_if_auto`
> + `run_streamed_with_timeout` with `dispatch_label="magi-loop2-iter1"`.
> Default `auto_no_timeout_dispatch_labels=["magi-*"]`.
> **When** caspar opus eval takes ~10min on stdout/stderr quiet.
> **Then** timeout NOT triggered. Dispatch completes naturally. (Same
> as v0.5.0 escenario T5, now exercised in production.)

### 4.2 4 Caspar Loop 2 iter 4 concerns (W4-W7)

**Subagent #1 owned (auto_cmd + pre_merge_cmd + status_cmd).**

**Escenario W4: pre_merge_cmd._wrap_with_heartbeat_if_auto narrow except**

> **Given** v0.5.0 Loop 1 fix #5 added bare-except in
> `_wrap_with_heartbeat_if_auto` to gate on `ProgressContext.phase != 0`
> introspection. Caspar Loop 2 iter 4 W4: bare-except neutralizes the
> fail-loud `_dispatch_with_heartbeat` ValueError signal.
> **When** Subagent #1 narrows except to `(AttributeError, RuntimeError)`.
> **Then** introspection failures still gracefully fall through to direct
> call. But `ValueError` from missing dispatch_label propagates loud.
> Test: monkeypatch `_dispatch_with_heartbeat` to raise ValueError; assert
> propagation.

**Escenario W5: status_cmd.watch_main exception guard**

> **Given** v0.5.0 watch_main poll loop has no exception guard. Transient
> error during poll cycle kills the watch.
> **When** Subagent #1 wraps cycle body in try/except.
> **Then** unexpected exceptions logged to stderr (`[sbtdd watch] cycle
> error: <error>`); poll continues. Watch survives transient errors. Test:
> monkeypatch `_read_auto_run_with_retry` to raise; assert watch keeps
> running 3+ cycles.

**Escenario W6: tests use monkeypatch.setattr for _assert_main_thread bypass**

> **Given** v0.5.0 concurrent writer tests directly mutate
> `auto_cmd._assert_main_thread` to bypass for concurrency exercise.
> **When** Subagent #1 migrates to `monkeypatch.setattr(...)`.
> **Then** tests still bypass for concurrency path; cleanup automatic
> on test failure (no manual restore needed). Pattern matches Caspar W6
> recommendation.

**Escenario W7: persistence-failure vs drain-failure breadcrumb separation**

> **Given** v0.5.0 has shared dedup flag for both
> heartbeat-write-failure breadcrumbs AND auto-run.json drain-failure
> breadcrumbs. Self-defeats when persistence itself is failing path.
> **When** Subagent #1 separates dedup flags.
> **Then** distinct flags `_drain_decode_error_emitted` (auto_cmd) vs
> heartbeat counter dedup. Each breadcrumb fires once per process; both
> can fire if both error classes occur.

### 4.3 Windows tmp filename PID collision flake

**Files tocados:** `auto_cmd.py` (3 writers per Loop 2 iter 4 caspar
finding: lines ~644, 997, 2469).

**Escenario W8: thread-id in tmp filename pattern**

> **Given** Windows test `test_concurrent_write_audit_writers_serialize_via_file_lock`
> intermittent PermissionError on `os.replace` of `.tmp.{getpid()}` files
> (threads share PID).
> **When** Subagent #1 changes pattern to `.tmp.{getpid()}.{threading.get_ident()}`.
> **Then** test reliably passes 10/10 runs (vs ~80% pre-fix). Cross-platform
> compatible (POSIX still uses os.replace; just unique per-thread tmp
> filename).

### 4.4 5 INFOs housekeeping

**Subagent #1 owned (most), Subagent #2 owned (1 if applicable).**

**Escenarios:**

**Escenario I-Hk1: BaseException in _write_auto_run_audit narrowed to Exception**

> **Given** v0.5.0 `_write_auto_run_audit` catches BaseException, delaying
> SystemExit / KeyboardInterrupt.
> **When** Subagent #1 narrows except to Exception.
> **Then** SystemExit + KeyboardInterrupt propagate cleanly. Other
> exceptions still caught for resilience.

**Escenario I-Hk2: INV-34 messages append unit suffix 's'**

> **Given** v0.5.0 INV-34 ValidationError messages omit unit ("got 75"
> instead of "got 75s").
> **When** Subagent #2 (config.py owned) updates messages.
> **Then** all 4 INV-34 clauses include "s" suffix in 'got Ns' fragment.

**Escenario I-Hk3: autouse fixture promoted to conftest.py**

> **Given** v0.5.0 has autouse fixture (heartbeat queue drain, drain-state
> reset, etc.) only in `tests/test_auto_progress.py`.
> **When** Subagent #1 promotes to top-level `tests/conftest.py`.
> **Then** all test files inherit the autouse fixture; no manual
> duplication needed across test_heartbeat.py, test_auto_progress.py, etc.

**Escenario I-Hk4: bytecode-deploy fragility note in inspect.getsource**

> **Given** v0.5.0 `_with_file_lock` has runtime assertion via
> `inspect.getsource()` against `_is_owned` regression. Fragile under
> bytecode-only deployments (no .py files).
> **When** Subagent #1 either (a) removes runtime assertion (unit test
> suffices) OR (b) adds graceful fallback: `try: source = inspect.getsource(...)
> except (OSError, TypeError): source = ""`.
> **Then** assertion does not crash in bytecode-only deployment scenarios.

**Escenario I-Hk5: kill-path race documented as accepted risk**

> **Given** v0.5.0 Windows kill-path may race with reader chunks despite
> W7 drain (Loop 2 iter 4 melchior I5).
> **When** Subagent #1 documents in `subprocess_utils.py` docstring.
> **Then** doc note states: "Reader-thread fallback design has inherent
> kill-path race window; accepted-risk per single-thread auto_cmd
> invariant. v1.x evaluation: if observable in field, evaluate locked
> reader-thread shutdown."

---

## 5. Cross-subagent contracts (sec.5 pinned)

Same pattern as v0.5.0 ProgressContext — dataclass shapes + helper signatures
pinned in spec; both subagents implement against the contract; runtime
convergence at integration test.

### 5.1 ResolvedModels dataclass (J2)

```python
# models.py — Subagent #2 owns
@dataclass(frozen=True)
class ResolvedModels:
    """Cached preflight resolution of per-skill model IDs.

    Resolved once at task-loop entry per auto run via
    `auto_cmd._resolve_all_models_once(config)`. All dispatches read
    from this cache instead of re-resolving CLAUDE.md + plugin.local.md
    (~70-150 disk reads per 36-task run reduced to 1).

    INV-0 cascade: CLAUDE.md model pin (per `models.INV_0_PINNED_MODEL_RE`)
    overrides plugin.local.md fields silently; stderr breadcrumb emitted.

    INV-0 cascade order (caspar Loop 2 iter 3 CRITICAL fix —
    enforces ``~/.claude/CLAUDE.md`` *maxima precedencia* per
    INV-0): global ``~/.claude/CLAUDE.md`` is consulted FIRST; if
    it pins a model (regex match), it wins (INV-0 maxima
    precedencia is non-negotiable — global cannot be silently
    overridden by a project file). Project ``<repo>/CLAUDE.md`` is
    consulted SECOND, only when the global file is absent or has
    no pin (in that case the project pin applies because no global
    rule is being contradicted). The first file with a regex match
    terminates the cascade. Neither pinned ⇒ fall through to
    plugin.local.md per-skill fields. If a Feature E v0.3.0 helper
    for cascading reads already exists (e.g.,
    ``superpowers_dispatch._read_cascaded_claude_md`` or similar),
    implementations SHOULD delegate to it rather than duplicating
    cascade logic, BUT the helper MUST honor the same global-first
    order — any helper that consulted project-first would itself
    contradict INV-0 and is unsafe to delegate to here.
    """
    implementer: str
    spec_reviewer: str
    code_review: str
    magi_dispatch: str
```

**Pre-existing dependency note (CRITICAL #3 fix):**
``models.INV_0_PINNED_MODEL_RE`` is **pre-existing in `models.py` since
v0.3.0 Feature E** (per-skill model selection); v1.0.0 does NOT introduce
or modify it. Subagent #2 task **S2-1** only adds the new
``ResolvedModels`` dataclass next to the existing regex; it does NOT
re-export, alias, or redefine ``INV_0_PINNED_MODEL_RE``. Subagent #1
task **S1-8** consumes the regex via the standard
``import models; models.INV_0_PINNED_MODEL_RE.search(...)`` path with no
cross-subagent surface contamination. This clarification removes the
ambiguity flagged by MAGI Checkpoint 2 iter 1 CRITICAL #3.

### 5.2 PluginConfig fields (G + I)

```python
# config.py — Subagent #2 owns
@dataclass(frozen=True)
class PluginConfig:
    # ... existing fields including v0.5.0 observability ...

    # v1.0.0 Feature G — default OFF (opt-in) per balthasar Loop 2 iter 1
    # WARNING (recursive dogfood circular risk): the cross-check sub-phase
    # invokes `/requesting-code-review` from inside the pre-merge gate
    # that may itself be evaluating the cross-check implementation diff.
    # Until field data confirms the meta-reviewer is robust, ship as
    # opt-in. Operators flip via `magi_cross_check: true` in
    # plugin.local.md.
    magi_cross_check: bool = False

    # v1.0.0 Feature I
    schema_version: int = 1  # default 1 = v0.5.0 backward compat
```

### 5.3 spec_snapshot helpers (Group B option 2)

```python
# scripts/spec_snapshot.py — Subagent #2 owns
def emit_snapshot(spec_path: Path) -> dict[str, str]:
    """Parse spec sec.4 Escenarios; return {scenario_title: hash}."""

def compare(prev: dict[str, str], curr: dict[str, str]) -> dict[str, list[str]]:
    """Return {'added': [...], 'removed': [...], 'modified': [...]}."""
```

`pre_merge_cmd.py` (Subagent #1) imports `spec_snapshot.emit_snapshot` y
`spec_snapshot.compare` per the contract.

### 5.4 Audit artifacts (G + F44.3)

- `.claude/magi-cross-check/iter{N}-{timestamp}.json` (Feature G):
  schema in sec.2.1 Escenario G6.
- `auto-run.json` extension (F44.3): `magi_iter{N}_retried_agents:
  list[str]` per MAGI iter.

---

## 6. Subagent layout + execution timeline

### 6.1 Subagent partition (per design — A bundle + A parallel disjoint)

**Subagent #1 — Dispatchers + observability completion** (~25 tasks, ~6-8h):
- **Files owned**: `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`,
  `status_cmd.py`. Tests: `test_auto_progress.py`, `test_pre_merge_cross_check.py`
  (NEW), `test_pre_merge_streaming.py`, `test_dispatch_heartbeat_wiring.py`,
  `test_subprocess_utils.py`, `test_status_watch.py` (extend).
- **Forbidden**: `config.py`, `models.py`, `superpowers_dispatch.py`,
  `scripts/spec_snapshot.py` (NEW), `scripts/migrate_plugin_local.py` (NEW).
- **Sequential ordering within**: Pillar 1 features FIRST (G + F44.3 + J2
  consumer), THEN v0.5.1 fold-in (J3+J7 wiring + 4 Caspar concerns +
  Windows fix + 5 INFOs).

**Subagent #2 — Schema + new scripts + writing-plans extension** (~9 tasks, ~3-4h):
- **Files owned**: `config.py`, `models.py` (ResolvedModels addition),
  `scripts/spec_snapshot.py` (NEW), `scripts/migrate_plugin_local.py` (NEW),
  `superpowers_dispatch.py`. Tests: `test_config.py`, `test_models.py`,
  `test_spec_snapshot.py` (NEW), `test_migrate_plugin_local.py` (NEW),
  `test_superpowers_dispatch.py` (extend).
- **Forbidden**: `auto_cmd.py`, `pre_merge_cmd.py`, `magi_dispatch.py`,
  `status_cmd.py`.

### 6.2 True parallel dispatch

Single message, two Agent tool calls (proven v0.4.0 + v0.5.0 pattern).
Surfaces 100% disjoint between subagents per partition above. Within
Subagent #1, sequential ordering as specified.

### 6.3 Coordination via spec sec.5 contracts

Both subagents implement against pinned shapes; no runtime code coupling.
Integration verified at `make verify` post-merge.

### 6.4 Wall time

| Phase | Duration |
|-------|----------|
| 0. Spec + brainstorming + spec-behavior.md | DONE |
| 1. Subagent #1 (sequential within) | ~6-8h |
| 1. Subagent #2 (parallel) | ~3-4h |
| 2. `make verify` post-merge | 5min |
| 3. Final review loop (Loop 1 + Loop 2 + iter cycles) | 2-4h |
| 4. Version bump 0.5.0 -> 1.0.0 + tag + push | 10min |
| **Total** | **~9-12h** |

---

## 7. Final review loop strategy

### 7.1 MAGI Checkpoint 2 (spec + plan)

Cap=3 per CHANGELOG `[0.5.0]` process commitment. Scope-trim is
default response if doesn't converge in 3 iters; INV-0 override only
with documented rationale.

### 7.2 Loop 1 (`/requesting-code-review`)

Cap=10. Clean-to-go criterion (zero CRITICAL + zero high-impact WARNING).

### 7.3 Loop 2 (`/magi:magi`) with cross-check dogfood

Cap=5 per `auto_magi_max_iterations`. NEW: cross-check (Feature G)
**dogfooded during own ship cycle**:

**Escenario R-Dogfood: Feature G activated mid-Loop-2 (opt-in)**

> **Given** Subagent #1 ships Feature G during T1.1-T1.6 (early in
> Subagent #1 sequential order). Default config is
> `magi_cross_check: False` per balthasar WARNING (recursive dogfood
> circular risk).
> **When** orchestrator opts in for the v1.0.0 Loop 2 dogfood by setting
> `magi_cross_check: true` in the project's `plugin.local.md` BEFORE
> Loop 2 iter 1 starts.
> **Then** cross-check sub-phase runs as part of pre-merge gate. If
> MAGI emits false-positive findings, cross-check ANNOTATES them
> (CRITICAL #1+#4 redesign — never removes); operator at INV-29 sees
> both the original finding and the annotation. If cross-check itself
> fails (G5 escenario), gracefully degrades.
> **Recursive payoff confirmed**: v1.0.0 Loop 2 is the FIRST gate to
> exercise cross-check on its own diff. Output empirical signal:
> cross-check audit artifacts written for each iter under
> `.claude/magi-cross-check/`.

**Cross-check annotation carry-forward in Loop 2 iter N+1**: per
sec.2.1, when iter N completes and at least one finding is rejected
or modified by INV-29 routing, iter N+1's MAGI payload reuses the
"Prior triage context" block from the v0.5.0 magi-gate carry-forward
template, but augmented with each finding's `cross_check_decision`,
`cross_check_rationale`, and `cross_check_recommended_severity`
fields from iter N's `annotated_findings`. Rationale: gives MAGI
agents the meta-reviewer's prior call so they can refine (not
re-emit) the same finding, and avoids redundant cross-check
meta-review on findings already operator-triaged. INV-11 safety
valve still applies: after `magi_max_iterations`, escalate.

### 7.4 Invariantes preserved

- INV-9, INV-11, INV-28, INV-29: preserved sin cambio.
- INV-32, INV-33, INV-34 (v0.5.0): preserved.
- INV-35 (NEW Feature G): cross-check obligatorio antes de INV-29 gate
  (opt-out via config).
- INV-36 (NEW Feature I): schema_version field default 1; future bumps
  via migration ladder.

---

## 8. Version + distribution

### 8.1 Bump

`plugin.json` + `marketplace.json`: 0.5.0 -> 1.0.0 (MINOR per Q1=B
"BREAKINGs OK").

### 8.2 CHANGELOG `[1.0.0]` sections

- **Added** — Feature G cross-check meta-reviewer + INV-35 + audit
  artifact; F44.3 retried_agents propagation; J2 ResolvedModels preflight;
  Feature I schema_version + migration tool skeleton + INV-36; Feature H
  Group B option 2 (spec-snapshot diff check) + option 5 (auto-gen
  scenario stubs); 2 new PluginConfig fields (`magi_cross_check`,
  `schema_version`).
- **Changed** — `auto-run.json` schema gains `magi_iter{N}_retried_agents:
  list[str]` field per MAGI iter (backward-compat: absent = []).
- **Production wiring (v0.5.1 fold-in)** — 33 J3+J7 callers in
  auto_cmd + pre_merge_cmd routed through `run_streamed_with_timeout`.
  Heartbeat fires in production for all long subagent dispatches.
- **Bug fixes (v0.5.1 fold-in)** — 4 Caspar Loop 2 iter 4 concerns
  resolved (bare-except narrowed, watch_main exception guard,
  monkeypatch.setattr migration, decode-error breadcrumb separation);
  Windows tmp PID collision flake fixed via thread-id in tmp filename.
- **Process notes** — Bundle accepted via single-cycle cycle (no INV-0
  override needed if MAGI Checkpoint 2 converges in 3 iters per process
  commitment). True parallel 2-subagent dispatch pattern continued from
  v0.4.0 + v0.5.0.
- **v1.x default-flip criteria for `magi_cross_check`** (balthasar Loop 2
  iter 2 WARNING): v1.0.0 ships `magi_cross_check: false` as the
  default (opt-in initially, per balthasar Loop 2 iter 1 recursive
  dogfood circular-risk concern). The default flips to `true` in a
  future v1.x release ONLY when ALL of the following hold:
  - **(a) Non-self-referential dogfood**: cross-check has been
    exercised in at least 2 ship cycles where Feature G code itself
    is NOT under review (i.e., cycles whose diffs touch surfaces
    other than `pre_merge_cmd._loop2_cross_check` and friends), so
    the meta-review is genuinely reviewing third-party code rather
    than itself.
  - **(b) Measurable false-positive filter rate**: cross-check audit
    artifacts (`.claude/magi-cross-check/iter*-*.json`) across those
    cycles show a strictly positive count of `DOWNGRADE` or `REJECT`
    decisions that operator review at INV-29 ratified. Zero useful
    filtering = no flip.
  - **(c) Zero false-negative annotations**: zero G2 (KEEP)
    decisions are observed to have been incorrectly downgraded by a
    later operator pass — i.e., the meta-reviewer never "rubber
    stamps" a CRITICAL that operator review later finds was indeed
    a false positive that should have been REJECT/DOWNGRADE.
  Until those criteria are met, operator opts in per project via
  `magi_cross_check: true` in `plugin.local.md`. Each v1.x release
  that exercises Feature G updates a running tally of (a)/(b)/(c)
  evidence in CHANGELOG so the eventual flip is auditable.
- **Deferred (rolled to v1.x)** — INV-31 default flip dedicated cycle;
  Group B options 1, 3, 4, 6, 7; GitHub Actions CI workflow.

### 8.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.0 docs section if user-facing changes. Cross-check
  user-visible: heartbeat ticks now appear during production MAGI dispatches.
- **SKILL.md**: `### v1.0 notes` section documenting Feature G + Feature I
  + Group B options 2+5.
- **CLAUDE.md**: v1.0.0 release notes pointer.

---

## 9. Risk register v1.0.0

- **R1**. Cross-check (Feature G) introduces false-negative risk
  (downgrades CRITICAL real to INFO). Mitigation: G5 graceful failure;
  G6 audit artifact preserves original findings; cross-check NEVER
  modifies verdict, only finding set.
- **R2**. Bundle width (~12 commitments). Per CHANGELOG `[0.5.0]` process
  commitment, scope-trim is first hypothesis if MAGI Checkpoint 2
  doesn't converge in 3 iters. User explicitly chose "v1.0.0 directo"
  (option A bundle-as-is) so INV-0 acceptable per documented rationale.
- **R3**. Group B option 2 spec-snapshot risks blocking legitimate spec
  edits between plan approval and merge. Mitigation: H2-3 escenario
  PreMergeError suggests re-running /writing-plans + Checkpoint 2 to
  re-approve plan against updated spec — explicit recovery path.
- **R4**. Group B option 5 auto-gen stubs may produce noisy unimplemented
  test bodies. Mitigation: stub bodies use `pytest.skip("Scenario stub:
  replace with real assertions")` so missing implementations don't
  silently pass; H5-2 spec_lint check at Checkpoint 2.
- **R5**. v0.5.1 fold-in J3+J7 wiring: 33 sites is mechanical but high
  volume = verification overhead. Mitigation: Subagent #1 batches by
  site cluster; integration test coverage spans all clusters.
- **R6**. Schema migration tool (Feature I) is no-op for v1 to v2;
  future v3 migrations need real implementation. Mitigation: ship
  framework + ladder pattern now (skeleton); populate when needed.
- **R7**. INV-31 default-flip out-of-scope; spec-reviewer hard-block
  remains v0.5.0 default. Operator pain continues. Mitigation:
  documented out-of-scope; users opt-out via `--skip-spec-review`.
- **R8**. Cross-subagent contract coordination (ResolvedModels dataclass,
  PluginConfig fields, spec_snapshot helpers). Mitigation: pinned
  shapes in spec sec.5; same pattern as v0.5.0 ProgressContext (proven
  in v0.5.0 ship).
- **R9**. Recursive payoff dependency (Feature G dogfooded during own
  Loop 2): if Subagent #1 stalls on Feature G implementation, dogfood
  signal lost. Mitigation: G ranks first in Subagent #1 ordering;
  fallback to manual cross-check if helper not yet wired.

---

## 10. Acceptance criteria final v1.0.0

v1.0.0 ship-ready cuando:

### 10.1 Functional Pillar 1

- **F1**. Feature G cross-check sub-phase implemented in pre_merge_cmd
  + auto_cmd. G1-G6 escenarios pass.
- **F2**. Audit artifact `.claude/magi-cross-check/iter{N}-{timestamp}.json`
  written per iter. Schema per G6.
- **F3**. INV-35 documented + adopted in spec sec.7.4.
- **F4**. Default `magi_cross_check: False` (opt-in per balthasar Loop 2
  iter 1 WARNING — recursive dogfood circular risk); operator opts in
  via `magi_cross_check: true` in plugin.local.md.
- **F5**. F44.3: `retried_agents` propagated to auto-run.json. F44.3-1
  + F44.3-2 escenarios pass.
- **F6**. J2: ResolvedModels preflight reduces CLAUDE.md reads to 1 per
  auto run. J2-1, J2-2, J2-3 escenarios pass.

### 10.2 Functional Pillar 2

- **F7**. `schema_version` field added to PluginConfig. I1, I2 escenarios
  pass (backward compat).
- **F8**. Migration script skeleton at `scripts/migrate_plugin_local.py`.
  I3, I4 escenarios pass.
- **F9**. Feature H option 2 spec-snapshot. H2-1 a H2-4 escenarios pass.
- **F10**. Feature H option 5 auto-gen stubs. H5-1, H5-2 escenarios pass.

### 10.3 Functional v0.5.1 fold-in

- **F11**. J3 + J7 production wiring: 33 callers routed. W1-W3 escenarios
  pass. Heartbeat fires in production for all long dispatches.
- **F12**. 4 Caspar concerns resolved. W4-W7 escenarios pass.
- **F13**. Windows tmp PID flake fixed. W8 escenario passes 10/10 runs.
- **F14**. 5 INFOs housekeeping. I-Hk1 a I-Hk5 escenarios pass.

### 10.4 No-functional

- **NF-A**. `make verify` clean: pytest + ruff + mypy --strict, runtime
  ≤ 120s.
- **NF-B**. Tests baseline 930 + 1 skipped preservados + 30-40 nuevos
  = ~960-970.
- **NF-C**. Cross-platform. Windows-specific tests pass empirically.
- **NF-D**. Author/Version/Date headers en nuevos `.py` files
  (spec_snapshot.py, migrate_plugin_local.py).
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados
  explicitamente en sec.6.1 partition.
- **NF-F**. Recursive dogfood: Feature G activated during Loop 2 iter
  2+ exercises cross-check on own diff. Audit artifacts present.

### 10.5 Process

- **P1**. MAGI Checkpoint 2 verdict ≥ `GO_WITH_CAVEATS` full per
  INV-28. Iter cap=3 per process commitment; scope-trim if doesn't
  converge (INV-0 override only with documented rationale).
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 MAGI verdict ≥
  `GO_WITH_CAVEATS` full no-degraded.
- **P3**. CHANGELOG `[1.0.0]` entry escrita.
- **P4**. Version bump 0.5.0 -> 1.0.0 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v1.0.0` + push (con autorizacion explicita user).

### 10.6 Distribution

- **D1**. Plugin instalable via `/plugin marketplace add ...` +
  `/plugin install ...`.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos subcomandos / flags documentados en README + SKILL.md +
  CLAUDE.md.

---

## 11. Referencias

- Spec base post-v0.5.0: `sbtdd/spec-behavior-base.md` (v1.0.0 raw input).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4+v0.5 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- Brainstorming session decisions log v1.0.0:
  - Q1 = A (bundle-as-is, no scope-trim split per user pushback on
    "always-split" pattern; honors original "v1.0.0 directo" directive).
  - Q2 = A (2 parallel disjoint subagents per v0.4.0 + v0.5.0 proven
    pattern).
- v0.5.0 ship + empirical findings:
  - just-shipped tag `v0.5.0` (commit `3610a9f` on `main`).
  - 4-iter Loop 2 INV-0 acceptance with 2 APPROVE + 1 CONDITIONAL.
  - 80 commits cycle.
- v0.5.1 LOCKED commitments rolled into v1.0.0 per CHANGELOG `[0.5.0]`
  Deferred section.
- Process commitment (CHANGELOG `[0.5.0]` Process notes): scope-trim
  default for v0.6.0+ if MAGI Checkpoint 2 doesn't converge in 3 iters.
- Branch: trabajo en feature branch `feature/v1.0.0-bundle` (or main
  directly per lightweight pattern — user choice at dispatch time).
