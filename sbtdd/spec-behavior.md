# BDD overlay — sbtdd-workflow v0.4.0

> Generado por `/brainstorming` el 2026-04-25 a partir de
> `sbtdd/spec-behavior-base.md` (v1.0.0 raw input post-v0.3.0).
> v0.4.0 cubre el sub-set Feature F + J subset (J4, J5, J6, J8) per
> directiva usuario sesion 2026-04-25 ("split (b)" + "balanced J
> subset (2)").
>
> v1.0.0 cubre los items remaining (G cross-check, H Group B re-eval
> + INV-31 default, I schema_version, J remaining: D5, J2 ResolvedModels,
> J3 per-stream timeout, J7 origin ambiguity).
>
> Este BDD overlay materializa los criterios sec.S.12 del spec-base
> en escenarios Given/When/Then testables. INV-27 compliant: cero
> matches uppercase placeholder (verificable con grep).

---

## 1. Resumen ejecutivo

**Objetivo v0.4.0**: ship dos surfaces 100% disjoint en ciclo
lightweight con 2 subagents paralelos (a diferencia de v0.3.0
sequential):
- **Feature F** — MAGI dispatch hardening + tolerant agent JSON
  parsing + auto manual-synthesis recovery.
- **J subset** — 4 v0.3.0 streaming follow-through items (J4
  OSError handling, J5 SKILL.md docs hotfix, J6 _write_auto_run_audit
  progress preservation, J8 pre-merge stream_prefix wiring).

Bumpa 0.3.0 -> 0.4.0 (MINOR, non-BREAKING -- aditivo).

**Out-of-scope v0.4.0** (deferred a v1.0.0):
- Feature G (MAGI -> /requesting-code-review cross-check).
- Feature H (Group B re-eval + INV-31 default-on opt-in re-eval).
- Feature I (schema_version: 2 + migration tool).
- D5 `/sbtdd status --watch` companion subcommand.
- J2 INFO #10 ResolvedModels dataclass.
- J3 INFO #11 per-stream timeout.
- J7 caspar #1 two-pump origin ambiguity.

**Criterio de exito**: 0.3.0 -> 0.4.0 sin regresion (789 tests
baseline preservados + ~30-40 nuevos), MAGI Loop 2 reliability
recuperada empiricamente (NF16 target: tolerant parser + auto
manual-synthesis recovery rescate degraded synthesis runs sin
operator intervention), y v0.3.0 streaming surface closure (no INFO
findings de v0.3.0 iter 1+2 sangrando a v1.0.0 noise).

**Recursive payoff**: v0.4.0 ships F itself, asi que su propio final
review loop puede dogfoodearlo en vivo. Iter 1 podria fallar igual
que v0.3.0 (parser fragility), pero post-F-commit el orchestrator
puede invocar `_manual_synthesis_recovery` sobre los `.raw.json`
files para rescatar el iter sin intervencion manual.

---

## 2. Feature F -- MAGI dispatch hardening + tolerant parsing

### 2.1 Scope (4 deliverables)

- **F43**. `magi_dispatch._discover_verdict_marker(output_dir)` --
  marker-based discovery via `MAGI_VERDICT_MARKER.json` enumeration.
- **F44**. `MAGIVerdict.retried_agents: tuple[str, ...]` field con
  parser tolerance.
- **F45**. `magi_dispatch._tolerant_agent_parse(raw_json_path)` --
  preamble-tolerant agent JSON extraction.
- **F46**. `magi_dispatch._manual_synthesis_recovery(run_dir)` --
  auto-recovery cuando run_magi.py synthesizer crashes pero
  >= 1 agent succeeded.

### 2.2 Escenarios Given/When/Then

**Escenario F43.1: marker-based discovery picks most recent by mtime**

> **Given** un `output_dir` con dos `MAGI_VERDICT_MARKER.json` files
> (e.g., from a re-run scenario): `marker_old.json` con mtime
> 2026-04-25T10:00:00Z, `marker_new.json` con mtime
> 2026-04-25T11:00:00Z.
> **When** `magi_dispatch._discover_verdict_marker(output_dir)` ejecuta.
> **Then** retorna path a `marker_new.json` (max by mtime).

**Escenario F43.2: marker-based discovery falla gracefully cuando no markers**

> **Given** un `output_dir` empty o sin markers (only `.raw.json`
> files presentes from agents).
> **When** `_discover_verdict_marker(output_dir)` ejecuta.
> **Then** raises `ValidationError("No MAGI_VERDICT_MARKER.json found
> in output_dir")` con detail listing files actually present
> (debugability).

**Escenario F43.3: marker discovery defensive sobre layout changes**

> **Given** MAGI 2.2.x cambia el path donde escribe markers (e.g.,
> de `output_dir/marker.json` a `output_dir/run-XYZ/marker.json` —
> hipotetical future change).
> **When** SBTDD corre `_discover_verdict_marker(output_dir)` con
> recursive enumeration via `Path.rglob("MAGI_VERDICT_MARKER.json")`.
> **Then** picks marker from sub-dir; legacy flat-layout markers
> tambien funcionan. Robust contra layout drift.

**Escenario F44.1: retried_agents field parsed cuando present**

> **Given** un `MAGI_VERDICT_MARKER.json` con MAGI 2.2.1+ schema
> incluyendo `"retried_agents": ["caspar"]` campo.
> **When** `MAGIVerdict.from_marker(marker_path)` parsea.
> **Then** `verdict.retried_agents == ("caspar",)` (tuple coerced
> from list for immutability).

**Escenario F44.2: retried_agents defaults a tuple vacio cuando absent**

> **Given** un MAGI 2.1.x marker sin `retried_agents` field.
> **When** `MAGIVerdict.from_marker(marker_path)` parsea.
> **Then** `verdict.retried_agents == ()`. Backward compat MAGI
> 2.1.x preservado.

**Escenario F44.3: retried_agents propagado a auto-run.json**

> **Given** mid-`auto` run, MAGI iter 2 retorna verdict con
> `retried_agents=("balthasar",)`.
> **When** `auto_cmd._update_progress` o `_write_auto_run_audit`
> fires post-MAGI dispatch.
> **Then** `auto-run.json` contiene `magi_iter2_retried_agents:
> ["balthasar"]` (or similar audit field) para escalation_prompt
> visibility.

**Escenario F45.1: tolerant parse extracts JSON from preamble-wrapped result**

> **Given** un `agent.raw.json` con `result` field:
> ```
> "Based on my review of the iter-2 fixes, the streaming wiring is correctly threaded...\n\n{\"agent\": \"melchior\", \"verdict\": \"GO\", ...}"
> ```
> **When** `magi_dispatch._tolerant_agent_parse(raw_json_path)` ejecuta.
> **Then** retorna parsed agent verdict dict
> `{"agent": "melchior", "verdict": "GO", ...}` extracted via
> balanced-brace regex sobre el `result` string. Strict v0.3.0
> parser hubiera fallado.

**Escenario F45.2: tolerant parse pure-JSON result still works**

> **Given** un `agent.raw.json` con `result` field que es JSON puro
> (caspar v0.3.0 iter 2 caso): `result` empieza directamente con `{`.
> **When** `_tolerant_agent_parse(raw_json_path)` ejecuta.
> **Then** retorna parsed verdict dict identico al strict-parser
> output. Backward compat: tolerant parser superset of strict.

**Escenario F45.3: tolerant parse falla cuando zero recoverable JSON**

> **Given** un `agent.raw.json` con `result` field que es solo
> narrative (e.g., agent crashed mid-output con error message but
> no JSON).
> **When** `_tolerant_agent_parse(raw_json_path)` ejecuta.
> **Then** raises `ValidationError("No JSON object recoverable from
> {raw_json_path}")` con preview de result content (first 200
> chars) for debugging.

**Escenario F45.4: tolerant parse extrae primer balanced JSON object**

> **Given** un `agent.raw.json` con `result` que tiene multiple
> `{...}` snippets (e.g., embedded code examples in narrative
> antes del verdict JSON).
> **When** `_tolerant_agent_parse(raw_json_path)` ejecuta el regex.
> **Then** extrae el primer balanced `{...}` que parsea como verdict
> JSON con `agent` field present (validation: must contain agent
> name from {melchior, balthasar, caspar}). Skips `{"key": "val"}`
> code-example snippets.

**Escenario F46.1: manual synthesis recovery cuando 1+ agent succeeded**

> **Given** un `run_dir` post-MAGI invocation donde
> run_magi.py synthesizer aborto con `RuntimeError: Only 1 agent(s)
> succeeded` pero 2 de 3 agents tienen `.raw.json` files con valid
> verdicts (preamble-wrapped).
> **When** `magi_dispatch._manual_synthesis_recovery(run_dir)` ejecuta.
> **Then** reads `*.raw.json`, applies F45 tolerant parser to each,
> synthesizes manually using same VERDICT_RANK weights as
> run_magi.py, emits `manual-synthesis.json` con flag
> `recovered: true` y `recovery_reason: "synthesizer-failure"`.
> Returns synthesized verdict.

**Escenario F46.2: manual recovery preserves agent dissent**

> **Given** raw.json files: melchior REJECT, balthasar APPROVE,
> caspar APPROVE.
> **When** `_manual_synthesis_recovery(run_dir)` ejecuta.
> **Then** synthesized verdict reflects 2-1 majority approve, but
> dissenting opinion from melchior preserved en verdict's findings
> + dissent fields. Same rank logic que run_magi.py synthesize.py.

**Escenario F46.3: manual recovery falla cuando zero recoverable**

> **Given** un `run_dir` donde todos los agents fallaron (every
> raw.json file has non-recoverable result fields per F45.3).
> **When** `_manual_synthesis_recovery(run_dir)` ejecuta.
> **Then** raises `MAGIGateError("No recoverable agent verdicts in
> run_dir; manual synthesis impossible")`. Operator must investigate
> raw.json files manually OR retry MAGI iter.

**Escenario F46.4: manual recovery fires automaticamente en MAGI dispatch**

> **Given** SBTDD invoca `magi_dispatch.dispatch_magi(...)` que
> internamente runs `run_magi.py`. Synthesis crashes con RuntimeError.
> **When** dispatch wrapper detects exit code != 0 + error pattern
> matches "Only N agent(s) succeeded" + N >= 1.
> **Then** automaticamente invokes `_manual_synthesis_recovery(run_dir)`,
> emits stderr breadcrumb `[sbtdd magi] synthesizer failed; manual
> synthesis recovery applied (N/3 agents)`, returns recovered
> verdict to caller. Default ON; suppress via `--no-magi-recovery`
> flag (when operator wants strict run_magi.py-only).

**Escenario F46.5: --no-magi-recovery flag respected**

> **Given** SBTDD invocation con `--no-magi-recovery`. Synthesizer
> crashes.
> **When** dispatch wrapper detects synthesizer crash.
> **Then** raises `MAGIGateError` con synthesizer original message;
> NO auto-recovery invoked. Strict behavior preserved per operator
> choice.

### 2.3 Acceptance criteria mapping (sec.S.12 v0.4.0)

| Criterion | Escenario | Test fixture |
|-----------|-----------|--------------|
| **F43**: marker-based discovery | F43.1, F43.2, F43.3 | `tests/test_magi_hardening.py` |
| **F44**: retried_agents field | F44.1, F44.2, F44.3 | `tests/test_magi_hardening.py` |
| **F45**: tolerant agent JSON parsing | F45.1, F45.2, F45.3, F45.4 | `tests/test_magi_hardening.py` |
| **F46**: manual synthesis recovery | F46.1, F46.2, F46.3, F46.4, F46.5 | `tests/test_manual_synthesis_recovery.py` |

### 2.4 Invariantes Feature F

- INV-28 (degraded MAGI no-exit) preservado: manual recovery NO
  contradice degraded handling — recovery fires solo on synthesizer
  crash with >= 1 agent succeeded; degraded verdict (< 3 agents
  with valid output) sigue consumiendo iter sin exit signal.
- INV-29 (/receiving-code-review gate) preservado sin cambio.
- Recovery NO es backdoor para skip MAGI: tolerant parser requires
  balanced JSON object AND parsable AND verdict in
  VERDICT_RANK known set AND agent field in {melchior, balthasar,
  caspar}.
- Marker file format: JSON con `verdict`, `iteration`, `agents`,
  `retried_agents`, `timestamp`, `synthesizer_status`. Schema fixed
  in `models.py`.
- Backward compat: MAGI 2.1.x (sin retried_agents, sin marker
  files) sigue funcionando via path-based discovery fallback +
  retried_agents default `()`.

---

## 3. J subset -- v0.3.0 streaming follow-through

### 3.1 Scope (4 deliverables)

- **J4**. INFO #12 `_update_progress` OSError handling.
- **J5**. balthasar #1 SKILL.md exit code docs hotfix (line 78).
- **J6**. balthasar #2 `_write_auto_run_audit` preserves `progress`
  field.
- **J8**. caspar #3 pre-merge stream_prefix wiring.

### 3.2 Escenarios Given/When/Then

**Escenario J4.1: _update_progress wraps OSError gracefully**

> **Given** mid-`auto` run con disk full (simulated via mock
> raising `OSError(28, "No space left")` from `tmp.write_text`).
> **When** `auto_cmd._update_progress(auto_run_path, ...)` fires.
> **Then** OSError caught, stderr breadcrumb emitted `[sbtdd]
> warning: progress write failed: OSError(28, ...). Auto run continues
> (observability degraded).` Auto run proceeds NOT killed.

**Escenario J4.2: _update_progress preserves auto-run.json on os.replace failure**

> **Given** atomic rename fails (OSError on Windows during
> concurrent reader holding file open + retry exhaustion at 20
> attempts).
> **When** `_update_progress` exhausts retry loop.
> **Then** original `auto-run.json` preserved (tmp file removed
> via try/finally), warning emitted, auto continues. No silent
> data loss.

**Escenario J5.1: SKILL.md line 78 documents exit 1 not exit 2**

> **Given** `skills/sbtdd/SKILL.md` v0.4.0 ship.
> **When** se lee la seccion `### v0.3 flags` describing
> `--model-override` invalid skill name behavior.
> **Then** texto exacto contiene `"exit 1 (USER_ERROR)"` (no `exit
> 2 (PRECONDITION_FAILED)`). Matches `auto_cmd._parse_model_overrides`
> raises `ValidationError` -> exit 1 actual implementation per
> errors.EXIT_CODES.

**Escenario J6.1: _write_auto_run_audit preserves existing progress field**

> **Given** `.claude/auto-run.json` existing con
> `{"progress": {"phase": 2, "task_index": 14, ...}, "started_at":
> "..."}`.
> **When** `auto_cmd._write_auto_run_audit(audit)` ejecuta para
> serializar `AutoRunAudit.to_dict()` (que normalmente NO contiene
> progress field).
> **Then** post-write, `auto-run.json` contiene tanto el audit
> snapshot fields AS WELL AS el progress field preservado del
> previous state. No transient drop.

**Escenario J6.2: _write_auto_run_audit cuando progress field absent**

> **Given** auto-run.json sin progress field (e.g., very early in
> auto run, before phase 1).
> **When** `_write_auto_run_audit(audit)` ejecuta.
> **Then** post-write, auto-run.json contiene audit fields. progress
> field permanece absent (D4.3 absent-tolerant downstream).

**Escenario J8.1: pre-merge MAGI dispatch threads stream_prefix**

> **Given** `pre_merge_cmd._loop2(...)` invoking `magi_dispatch.invoke_magi`
> for Loop 2 iter N.
> **When** dispatch fires.
> **Then** argv passed a `magi_dispatch.invoke_magi` includes
> `stream_prefix="[sbtdd pre-merge magi-loop2]"`. Subprocess output
> streams a operator stderr en tiempo real durante MAGI invocation
> (5-10 min for opus-based agents).

**Escenario J8.2: pre-merge code-review dispatch threads stream_prefix**

> **Given** `pre_merge_cmd._loop1(...)` invoking
> `superpowers_dispatch.invoke_skill("requesting-code-review", ...)`.
> **When** dispatch fires.
> **Then** argv includes `stream_prefix="[sbtdd pre-merge loop1
> iter-N]"` per iteration.

**Escenario J8.3: pre-merge mini-cycle TDD dispatches thread stream_prefix**

> **Given** `pre_merge_cmd._apply_finding_via_mini_cycle(finding)` invocando
> implementer subagent for Red phase.
> **When** dispatch fires.
> **Then** argv includes
> `stream_prefix="[sbtdd pre-merge fix-finding-N red]"` para cada
> phase del mini-cycle (red/green/refactor).

### 3.3 Acceptance criteria mapping

| Criterion | Escenario | Test fixture |
|-----------|-----------|--------------|
| **J4**: OSError handling | J4.1, J4.2 | `tests/test_auto_progress.py` (extended) |
| **J5**: SKILL.md docs hotfix | J5.1 | `tests/test_skill_md.py` (extended) |
| **J6**: audit preserves progress | J6.1, J6.2 | `tests/test_auto_progress.py` (extended) |
| **J8**: pre-merge stream_prefix | J8.1, J8.2, J8.3 | `tests/test_pre_merge_streaming.py` (new) |

### 3.4 Invariantes J subset

- INV-22 (sequential auto) preservado.
- INV-26 (audit trail) extendido: audit writes preserve progress
  field rather than drop.
- v0.3.0 contract preservado: D4.3 absent-progress-tolerant
  parser sigue funcionando; nueva preservation no rompe nada.

---

## 4. Final review loop (post-implementation)

### 4.1 Scope

Identico a v0.3.0: MAGI -> /receiving-code-review loop hasta exit
criterion (verdict `GO_WITH_CAVEATS` full + 0 CRITICAL + 0 WARNING
+ 0 Conditions for Approval), cap 5 iter.

### 4.2 Special v0.4.0 dogfood pattern

**Recursive payoff oportunity**: este ciclo ships F itself. Si
iter 1 final review hits MAGI synthesizer crash (mismo failure mode
como v0.3.0 iter 2), el orchestrator puede invocar el recien
shipado `_manual_synthesis_recovery` para rescatar el iter sin
intervencion manual. Empirical validation de F durante su propio
ship cycle.

**Escenario R2.1: F dogfood en iter 2+ rescues crashed synthesis**

> **Given** v0.4.0 final review iter 2. F shipped en commit C
> earlier in this cycle. MAGI synthesizer crashes igual que v0.3.0
> (preamble-wrapped agent JSON).
> **When** `magi_dispatch.dispatch_magi(...)` wrapper detecta
> crash + ≥1 agent succeeded.
> **Then** auto-invokes `_manual_synthesis_recovery(run_dir)`,
> reads .raw.json files, parses tolerantly, emits
> `manual-synthesis.json`, returns rescued verdict to orchestrator.
> Iter completes WITHOUT manual intervention. F empirically
> validated.

**Escenario R2.2: F dogfood en iter 1 (pre-F-commit) requires manual recovery**

> **Given** v0.4.0 final review iter 1, F NOT YET committed (still
> in subagent #1's working tree). MAGI crashes.
> **When** orchestrator detects crash.
> **Then** orchestrator manually applies v0.3.0 playbook (read
> raw.json, manual synthesize, document). NORMAL behavior; subagent
> #1's F commits land BEFORE final review starts (orchestrator
> coordinates).

### 4.3 Other escenarios (R1.x identical to v0.3.0 spec)

R1.1-R1.7 from v0.3.0 spec apply identically:
- R1.1 exit on GO_WITH_CAVEATS clean.
- R1.2 continue on CRITICAL findings.
- R1.3 continue on WARNING findings or Conditions.
- R1.4 continue on degraded MAGI (INV-28).
- R1.5 cap 5 iter -> escalation_prompt.
- R1.6 rejected findings feed iter+1 context.
- R1.7 Loop 1 surrogate via make verify.

### 4.4 Invariantes final review

- INV-9, INV-11, INV-28, INV-29 preservados sin cambio.
- F's auto-recovery operates within INV-28 scope (degraded =
  recovered manual synthesis still counts as iteration consumed,
  not exit signal).

---

## 5. Subagent layout + execution timeline

### 5.1 Layout (parallel — surfaces 100% disjoint)

| Phase | Duracion proyectada | Subagents | Output |
|-------|--------------------|-----------|--------|
| 0. Spec + brainstorming + spec-behavior.md | DONE | -- | esta seccion |
| 1. Subagent #1 (F) | ~2.5h | parallel | 4-6 atomic commits |
| 1. Subagent #2 (J subset) | ~2-2.5h | parallel | 4-5 atomic commits |
| 2. `make verify` post-merge | ~5min | -- | 4 checks clean |
| 3. Final review loop MAGI -> /receiving-code-review | 1-2h | -- | 1-3 iter expected (lower than v0.3.0 because F itself rescues) |
| 4. Version bump + tag + push | ~10min | -- | 0.3.0 -> 0.4.0 |
| **Total wall time** | **~4-5h** | -- | -- |

### 5.2 Subagent dispatch contracts

**Subagent #1 (F)**:
- Input: spec-behavior.md sec.2 (Feature F escenarios F43.1-F46.5).
- Files tocados: `skills/sbtdd/scripts/magi_dispatch.py`,
  `skills/sbtdd/scripts/models.py`, new
  `tests/test_magi_hardening.py`, new
  `tests/test_manual_synthesis_recovery.py`.
- TDD-Guard: ON.
- Forbidden: any J-subset file.
- Done: 4 deliverables F43-F46 implemented + tests passing +
  `make verify` clean.

**Subagent #2 (J subset)**:
- Input: spec-behavior.md sec.3 (J4, J5, J6, J8 escenarios).
- Files tocados: `skills/sbtdd/scripts/auto_cmd.py` (J4 OSError
  wrap + J6 audit progress preservation), `skills/sbtdd/SKILL.md`
  (J5 docs hotfix), `skills/sbtdd/scripts/pre_merge_cmd.py` (J8
  stream_prefix wiring), tests/test_auto_progress.py (extended for
  J4/J6), tests/test_skill_md.py (extended for J5), new
  tests/test_pre_merge_streaming.py (J8).
- TDD-Guard: ON.
- Forbidden: `skills/sbtdd/scripts/magi_dispatch.py`,
  `skills/sbtdd/scripts/models.py`.
- Done: 4 deliverables implemented + tests passing + `make verify`
  clean.

### 5.3 Coordination

**Surfaces 100% disjoint**: F touches `magi_dispatch.py` + `models.py`
(no auto_cmd, no pre_merge); J touches `auto_cmd.py` + `pre_merge_cmd.py`
+ `SKILL.md` (no magi_dispatch, no models). Zero risk de auto_cmd.py
merge conflict como v0.3.0.

Both subagents commit to `main` (lightweight pattern, no feature
branch). Orchestrator coordina dispatch parallel, espera DONE de
ambos, then drives final review.

### 5.4 Final review loop dispatch (orchestrator)

Mismo pattern v0.3.0:
1. `make verify` clean (Loop 1 surrogate).
2. Compute diff range (HEAD_pre_v040..HEAD).
3. Iter 1: invoke `/magi:magi` con prompt referencing spec + plan +
   diff. Si synthesizer crashes AND F shipped en working tree -> use
   F's `_manual_synthesis_recovery` (escenario R2.1). Si no -> v0.3.0
   playbook manual.
4. Parse verdict + findings. Eval exit criterion.
5. Si NO exit: route findings via /receiving-code-review (INV-29) +
   mini-cycle TDD per accepted finding. Re-invoke MAGI iter+1.
6. Cap 5 iter; exhausted -> escalation_prompt.

---

## 6. Version + distribution

### 6.1 Bump

`plugin.json` + `marketplace.json`: 0.3.0 -> 0.4.0 (MINOR).

Justificacion MINOR (no MAJOR): aditivo puro. F adds new helpers
(no public-API breakage, dispatch wrapper backward-compat). J subset
extends existing surfaces (no behavior flip). retried_agents field
optional (default `()`). marker-based discovery has fallback to
path-based. Tolerant parser is superset of strict parser.

### 6.2 CHANGELOG.md `[0.4.0]` sections

- **Added** -- F (4 deliverables: marker discovery, retried_agents
  field, tolerant parser, manual synthesis recovery) + J subset
  (4 deliverables: OSError handling, SKILL.md docs hotfix, audit
  progress preservation, pre-merge streaming).
- **Changed** -- (vacio o minor: pre-merge dispatch sites now thread
  stream_prefix when invoked via auto path).
- **Process notes** -- F's recursive payoff: shipped F empirically
  validated during own final review loop via R2.1 dogfood. Loop 1
  surrogate via `make verify` per lightweight pattern.
- **Deferred (rolled to v1.0.0)** -- G cross-check, H Group B
  re-eval + INV-31 default, I schema_version, J1 D5 status --watch,
  J2 ResolvedModels, J3 per-stream timeout, J7 origin ambiguity.

### 6.3 README + SKILL.md

- README: v0.4.0 docs section if user-facing changes (mostly
  internal infra; possibly add a "MAGI reliability" mini-section
  documenting Feature F user-facing benefit).
- SKILL.md: J5 docs hotfix (line 78 exit code correction). Possibly
  add `### v0.4 notes` section documenting F's auto-recovery.
- CLAUDE.md (proyecto): update con v0.4.0 release notes pointer.

---

## 7. Risk register v0.4.0

- **R1**. Tolerant agent JSON parsing introduces false-positive
  recovery -- mitigation: regex requires balanced `{...}` AND valid
  JSON-parse AND `agent` field in known set AND `verdict` in
  VERDICT_RANK; manual synthesis report flags recovery clearly with
  `recovered: true` flag.
- **R2**. Marker-based MAGI discovery breaks if MAGI changes marker
  schema -- mitigation: SBTDD tolera ausencia de campos opcionales en
  marker; mantener test contra MAGI versions cacheadas; fallback a
  path-based discovery preserved as compat.
- **R3**. Auto-recovery silently masks legit MAGI failures --
  mitigation: stderr breadcrumb prominent + `recovered: true` flag
  + `--no-magi-recovery` opt-out for strict mode.
- **R4**. Subagent #1 + #2 parallel timing variance: if subagent #1
  finishes much later than #2, the dogfood pattern (R2.1) for final
  review is delayed -- mitigation: orchestrator waits for both DONE
  before final review starts; F lands BEFORE iter 1 review.
- **R5**. Iter 1 final review fails because F not yet "in production"
  during subagent #1 work -- mitigation: orchestrator coordina dispatch;
  subagents both DONE before final review; F's commits LANDED before
  iter 1 invocation.

---

## 8. Acceptance criteria final v0.4.0

v0.4.0 ship-ready cuando:

- [ ] Feature F 4 deliverables implementados + escenarios F43-F46
      pass.
- [ ] J subset 4 deliverables implementados + escenarios J4, J5, J6,
      J8 pass.
- [ ] Final review loop alcanzado exit en <= 5 iter con MAGI verdict
      `GO_WITH_CAVEATS` full + 0 CRITICAL + 0 WARNING + 0 Conditions
      pendientes.
- [ ] `make verify` clean (pytest + ruff + mypy --strict, runtime
      <= 90s).
- [ ] Tests baseline 789 preservados + ~30-40 nuevos = 819-829.
- [ ] CHANGELOG `[0.4.0]` entry escrita.
- [ ] Version bump 0.3.0 -> 0.4.0 sync `plugin.json` +
      `marketplace.json`.
- [ ] Tag `v0.4.0` creado + push origin/main + push tag (con
      authorization explicita user).
- [ ] README + SKILL.md (J5 hotfix mandatory, otros opcionales).
- [ ] Memory `project_v040_shipped.md` written + MEMORY.md index
      updated.
- [ ] R2.1 dogfood empirically validated (or documented why not
      observed in this cycle's iter sequence).

---

## 9. Referencias

- Spec base post-v0.3.0: `sbtdd/spec-behavior-base.md` (v1.0.0
  raw input; v0.4.0 cubre F + J subset).
- Contrato autoritativo v0.1+v0.2+v0.3 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- Brainstorming session decisions log v0.4.0:
  - (b) Split: v0.4.0 = F + small J, v1.0.0 = G + H + I + remaining.
  - (2) Balanced J subset: J4 + J5 + J6 + J8.
  - Lightweight + 2 parallel subagents (surfaces disjoint).
  - Final review = MAGI -> /receiving-code-review loop con dogfood
    rescue option (escenario R2.1).
- v0.3.0 ship + empirical findings:
  - `project_v030_shipped.md` (v0.3.0 ship record).
  - `.claude/magi-runs/v030-iter1/magi-report.json` (iter 1 findings).
  - `.claude/magi-runs/v030-iter2/{melchior,balthasar,caspar}.raw.json`
    (synthesizer crash, manual recovery rationale).
- Historical precedent:
  - v0.2.1 lightweight pattern (~3h, 4 LOCKED items).
  - v0.3.0 lightweight + sequential 2 subagents + 2-iter MAGI
    Loop 2 (~5h, 10 deliverables).
- v1.0.0 deferred items roadmap:
  - `project_v100_magi_cross_check.md` (Feature G).
  - Group B options re-evaluation (Feature H).
  - schema_version + migration tool (Feature I).
- Branch: trabajo en `main` directamente (lightweight pattern, no
  feature branch).
