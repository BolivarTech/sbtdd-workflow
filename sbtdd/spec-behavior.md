# BDD overlay — sbtdd-workflow v1.0.1

> Generado 2026-05-03 a partir de `sbtdd/spec-behavior-base.md` v1.0.1.
> Hand-crafted en sesion interactiva (no via `claude -p /brainstorming`
> subprocess) por consistencia con Finding A discovery del v1.0.0
> dogfood — el subprocess pattern es exactamente el bug que v1.0.1
> arregla.
>
> v1.0.1 ships el "Plugin self-hosting fix" como single-pillar release.
> 4 items LOCKED del CHANGELOG `[1.0.0]` Deferred section pivotaron a
> v1.0.2 per user directive 2026-05-03.
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4+v0.5+v1.0
> frozen se mantiene en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder.

---

## 1. Resumen ejecutivo

**Objetivo v1.0.1**: arreglar tres findings del dogfood empirico de
`/sbtdd spec` contra el propio repo del plugin (2026-05-03):

- **Finding A** (CRITICAL): `claude -p /<skill>` subprocess broken
  para Skills interactivos (`/brainstorming`, `/writing-plans`).
- **Finding B** (IMPORTANT): `spec_snapshot._SECTION_RE` regex
  demasiado estricta vs production specs.
- **Finding C** (IMPORTANT): `spec_cmd._run_spec_flow` no valida output
  de Skills dispatcheados (mtime check missing).

Cuatro items LOCKED single-pillar:

1. **A0 output validation tripwire** — mtime check post-subprocess.
2. **A1 permissive escenario regex** — distributed escenarios soportados.
3. **A2 headless-mode detection** — raise antes del subprocess broken.
4. **A3 `--resume-from-magi` recovery flag** — skip dispatch step.

**Criterio de exito**:
- 1033 + 1 skipped tests preservados + ~21-25 nuevos = ~1054-1058
  (5 A0 + 5 A1 + 5 A2 + 6 A3 + Pre-A2 audit step verification).
- `make verify` <= 150s (soft-target <= 140s).
- Empirical: en sesion Claude Code nueva, `/brainstorming` +
  `/writing-plans` interactivos + `/sbtdd spec --resume-from-magi`
  completa end-to-end.
- v1.0.0 cycle's CHANGELOG `[1.0.0]` Deferred items rolled forward a
  v1.0.2 (no perdidos).

**Out of scope**: cross-check telemetry, diff threading, spec_lint,
own-cycle dogfood (todos a v1.0.2). v1.1.0+ items unchanged.

---

## 2. Items LOCKED

### 2.1 Item A0 — Output validation tripwire (Finding C fix)

**Archivos tocados**:
- `skills/sbtdd/scripts/spec_cmd.py` (extender `_run_spec_flow`).
- Tests: `tests/test_spec_cmd.py`.

**Invariante propuesto**: **INV-37**. `_run_spec_flow` DEBE validar que
outputs de `superpowers_dispatch.brainstorming` y `writing_plans` fueron
escritos durante el subprocess via composite-signature check
(mtime_ns + size + sha256), no solo que existen pre-subprocess y no solo
mtime (que es FS-precision-fragile y can collision under fast clocks).

**Composite signature rationale (C1/W5/W7 fix)**:

A bare `mtime_ns` check is fragile against three failure modes:
1. **FS precision floors**: some filesystems (FAT32, network mounts,
   container overlayfs) round mtime to 1s or 2s precision; a fast
   subprocess can rewrite within the same tick, leaving `mtime_after ==
   mtime_before` despite content change (false negative — A0 misses
   real write).
2. **Same-content rewrite**: a subprocess that rewrites the file with
   identical bytes still bumps mtime on most FSes but can land on the
   same `mtime_ns` under coarse-clock conditions; size + sha256
   disambiguate.
3. **Touched-but-empty**: a subprocess that touches the file but writes
   the same content (silent no-op rewrite) leaves the file functionally
   unchanged. Composite signature catches this.

The composite signature `(mtime_ns, size, sha256)` is **invariant under
all three failure modes**: any genuine content change shifts at least
one of the three components; pure no-ops leave all three identical.

**Implementacion**:

```python
def _file_signature(path: Path) -> tuple[int, int, str]:
    """Composite signature for output-validation tripwire.

    Returns (mtime_ns, size, sha256-of-content). Equal-tuple post-
    subprocess vs pre-subprocess means no genuine content change
    occurred (resilient to FS-precision and same-content rewrite).
    """
    st = path.stat()
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return (st.st_mtime_ns, st.st_size, h.hexdigest())


def _run_spec_flow(root: Path) -> None:
    spec_base = root / "sbtdd" / "spec-behavior-base.md"
    spec_behavior = root / "sbtdd" / "spec-behavior.md"
    plan_org = root / "planning" / "claude-plan-tdd-org.md"

    # Capture pre-subprocess signature (or None if file absent).
    spec_sig_before = _file_signature(spec_behavior) if spec_behavior.exists() else None
    plan_sig_before = _file_signature(plan_org) if plan_org.exists() else None

    superpowers_dispatch.brainstorming(args=[f"@{spec_base}"])
    if not spec_behavior.exists():
        raise PreconditionError(...)
    spec_sig_after = _file_signature(spec_behavior)
    if spec_sig_before is not None and spec_sig_after == spec_sig_before:
        raise PreconditionError(
            f"/brainstorming exit 0 pero {spec_behavior} no fue modificado "
            f"(composite signature mtime+size+sha256 sin cambio). Verifica "
            f"sesion interactiva o usa --resume-from-magi si artifacts "
            f"producidos manualmente."
        )

    superpowers_dispatch.writing_plans(args=[f"@{spec_behavior}"])
    if not plan_org.exists():
        raise PreconditionError(...)
    plan_sig_after = _file_signature(plan_org)
    if plan_sig_before is not None and plan_sig_after == plan_sig_before:
        raise PreconditionError(...)
```

### 2.2 Item A1 — Permissive escenario regex (Finding B fix)

**Archivos tocados**:
- `skills/sbtdd/scripts/spec_snapshot.py` (`emit_snapshot` two-tier).
- Tests: `tests/test_spec_snapshot.py`.

**Implementacion**:

```python
def emit_snapshot(spec_path: Path) -> dict[str, str]:
    text = spec_path.read_text(encoding="utf-8")

    # Tier 1: legacy format (## §4 Escenarios). Backward compat preserved.
    section_match = _SECTION_RE.search(text)
    if section_match:
        scenarios = _extract_scenarios(section_match.group(1))
        if scenarios:
            return scenarios
        # Legacy section present but empty -> fall through to Tier 2
        # rather than raising (more forgiving).

    # Tier 2: distributed format. Scan whole document for **Escenario
    # X: ...** blocks (plus ## / ### Escenario X: ... headings).
    scenarios = _extract_scenarios(text)
    if not scenarios:
        raise ValueError(
            f"No escenarios found in {spec_path} (neither legacy "
            f"## §4 Escenarios section nor distributed **Escenario** "
            f"blocks). Spec-snapshot drift detection requires at least "
            f"one scenario."
        )
    return scenarios
```

Zero-match guard preservado en Tier 2.

### 2.3 Item A2 — Headless-mode detection (Finding A mitigation)

**Archivos tocados**:
- `skills/sbtdd/scripts/superpowers_dispatch.py` (extender
  `invoke_skill`).
- Tests: `tests/test_superpowers_dispatch.py`.

**`allow_interactive_skill` kwarg rationale (C2/W6 fix)**:

A blanket `raise` for any skill in `_SUBPROCESS_INCOMPATIBLE_SKILLS`
breaks legitimate callers: the wrapper functions
(`brainstorming`, `writing_plans`) and the `_make_wrapper` /
`_invoke_skill` internals are precisely the **safe path** through
which interactive skills SHOULD be invoked (they handle the manual-
dispatch coordination). A blanket gate would force every wrapper to
either bypass the gate (defeating purpose) or use a sentinel
(redundant). The clean solution is an opt-in kwarg
`allow_interactive_skill: bool = False`:

- **Default `False`** = safe-by-default for headless CLI / external
  callers; raises immediately with recovery guidance.
- **Explicit `True`** = wrapper-aware override; permits the same
  call to proceed (wrappers ARE the safe path, they pass `True`
  internally).
- **Pre-A2 migration**: the existing direct callers of `invoke_skill`
  in production (`_make_wrapper` factory + `_invoke_skill` helper)
  and tests (4 callsites in `test_superpowers_dispatch.py`) MUST be
  migrated to pass `allow_interactive_skill=True` BEFORE A2 lands,
  else A2 silently breaks them. See Plan Task Pre-A2 for the audit
  + migration step.

**Implementacion**:

```python
_SUBPROCESS_INCOMPATIBLE_SKILLS: frozenset[str] = frozenset({
    "brainstorming",
    "writing-plans",
})

def invoke_skill(skill, args=None, ..., allow_interactive_skill=False):
    if skill in _SUBPROCESS_INCOMPATIBLE_SKILLS and not allow_interactive_skill:
        raise PreconditionError(
            f"Skill /{skill} cannot be invoked via `claude -p` subprocess "
            f"(output is silently empty); requires interactive Claude Code "
            f"session. Run /{skill} manualmente or use the wrapper function "
            f"(superpowers_dispatch.{skill_to_wrapper_name(skill)}) which "
            f"passes the override automatically. For recovery after manual "
            f"dispatch, use `sbtdd spec --resume-from-magi`."
        )
    # Existing flow para no-interactive Skills (magi:magi, etc.) and
    # wrapper-driven calls (allow_interactive_skill=True) for interactive
    # skills.
    ...
```

### 2.4 Item A3 — `--resume-from-magi` recovery flag (supports A2)

**Archivos tocados**:
- `skills/sbtdd/scripts/spec_cmd.py` (`_build_parser` + `main`).
- Tests: `tests/test_spec_cmd.py`.

**Implementacion**:

```python
def _build_parser():
    p = argparse.ArgumentParser(...)
    p.add_argument(
        "--resume-from-magi",
        action="store_true",
        help="Skip /brainstorming + /writing-plans dispatch (assume "
             "artifacts already produced by the operator manually); "
             "go directly to MAGI Checkpoint 2.",
    )
    ...

def main(argv=None):
    parser = _build_parser()
    ns = parser.parse_args(argv)
    root = Path(ns.project_root)

    # INV-27 hard rule — always validate placeholder absence even when
    # --resume-from-magi is passed (W4 spec/plan alignment fix).
    _validate_spec_base_no_placeholders(root / "sbtdd" / "spec-behavior-base.md")

    if not ns.resume_from_magi:
        _run_spec_flow(root)
    else:
        # Structural validation of operator-produced artifacts before MAGI
        # dispatch (W2/W8 fix). Existence-only check is insufficient — an
        # empty or stub-only spec/plan would silently waste a MAGI iter.
        spec_behavior_path = root / "sbtdd" / "spec-behavior.md"
        plan_org_path = root / "planning" / "claude-plan-tdd-org.md"

        # spec-behavior.md must yield a parseable snapshot (>=1 escenario).
        # W3 caspar iter 2 fix: widen exception class to include OSError
        # (FS-level read failures: permission denied, broken symlink, etc.)
        # so structural validation never leaks an unexpected exception
        # type to the operator. Regression test ensures exception leakage
        # caught at A3 boundary.
        try:
            snapshot = spec_snapshot.emit_snapshot(spec_behavior_path)
        except (FileNotFoundError, ValueError, OSError) as exc:
            raise PreconditionError(
                f"--resume-from-magi requires a valid {spec_behavior_path} "
                f"(spec_snapshot.emit_snapshot failed: {exc}). Run "
                f"/brainstorming manually first."
            ) from exc
        if not snapshot:
            raise PreconditionError(
                f"--resume-from-magi requires {spec_behavior_path} to "
                f"contain at least one escenario; emit_snapshot returned "
                f"empty dict."
            )

        # plan-tdd-org.md must contain >=1 `### Task` heading AND >=1 `- [ ]`
        # checkbox (regex-based structural check).
        plan_text = plan_org_path.read_text(encoding="utf-8")
        if not re.search(r"^###\s+Task\b", plan_text, re.MULTILINE):
            raise PreconditionError(
                f"--resume-from-magi requires {plan_org_path} to contain "
                f"at least one `### Task` heading; plan appears malformed."
            )
        if not re.search(r"^-\s+\[\s\]", plan_text, re.MULTILINE):
            raise PreconditionError(
                f"--resume-from-magi requires {plan_org_path} to contain "
                f"at least one `- [ ]` checkbox; plan appears empty."
            )

    cfg = load_plugin_local(root / ".claude" / "plugin.local.md")
    _run_magi_checkpoint2(root, cfg, ns)
    # ... rest unchanged
```

---

## 3. Cross-module contracts

v1.0.1 es scope chico — single-subagent execution. No hay particion
disjoint requerida; todas las tareas tocan archivos compatibles
secuencialmente. Sin embargo, los siguientes contratos preservados
(no modificados) son consumidos por las nuevas tareas:

- **`PreconditionError`** (existing en `errors.py`): A0, A2 raisean
  esta clase. Mapped to exit 2 (PRECONDITION_FAILED) por
  `run_sbtdd.py`.
- **`subprocess_utils.run_with_timeout`** (existing): A0 NO toca; A2
  evita llamarlo cuando Skill es interactive-only.
- **`spec_snapshot._extract_scenarios`** (existing): A1 lo reusa para
  el Tier 2 fallback path.
- **`spec_snapshot.emit_snapshot`** (refactored by A1; consumed by A3):
  A3's `--resume-from-magi` structural validation calls
  `emit_snapshot(spec_behavior_path)` to verify the operator-produced
  spec yields >=1 escenario before MAGI dispatch. This makes A3
  depend on A1 having shipped first (matches sequential ordering A1
  → ... → A3 in sec.5).

---

## §4 Escenarios BDD

### Item A0 — Output validation tripwire

**Escenario A0-1: brainstorming subprocess silently no-op detected**

> **Given** `sbtdd/spec-behavior.md` exists with mtime T0 (artifact del
> ciclo previo). `superpowers_dispatch.brainstorming` is monkeypatched
> a un stub que NO modifica el archivo (simula `claude -p` headless
> no-op).
> **When** `spec_cmd._run_spec_flow(root)` ejecuta.
> **Then** raises `PreconditionError` con mensaje incluyendo el path
> de `spec-behavior.md` y la palabra "no fue modificado". Mensaje
> sugiere `--resume-from-magi` recovery flag.

**Escenario A0-2: writing_plans subprocess silently no-op detected**

> **Given** `sbtdd/spec-behavior.md` y `planning/claude-plan-tdd-org.md`
> existen del ciclo previo con mtimes T0a, T0b. `brainstorming` stub
> ACTUALIZA spec-behavior.md (mtime sube), pero `writing_plans` stub
> NO modifica plan-org.md.
> **When** `_run_spec_flow` ejecuta.
> **Then** brainstorming pasa el check; writing_plans falla — raises
> `PreconditionError` referenciando plan-tdd-org.md path.

**Escenario A0-3: first-run with no prior artifacts works**

> **Given** Ningun spec-behavior.md ni plan-org.md existen pre-flow
> (proyecto recien initialized). Ambos stubs ESCRIBEN sus archivos
> correctamente durante el subprocess.
> **When** `_run_spec_flow` ejecuta.
> **Then** mtime check skipped para "first-run" path (file no existia
> pre-subprocess); existence check sigue verificando que ahora si
> existe. Sin error.

**Escenario A0-4: both subprocesses write correctly — happy path**

> **Given** Ambos archivos existen con mtimes T0a, T0b. Ambos stubs
> ACTUALIZAN sus archivos (mtime sube post-subprocess).
> **When** `_run_spec_flow` ejecuta.
> **Then** Sin error. Tracing-level: ambos checks pasan.

**Escenario A0-5: file rewritten with same content fast clock detected as no-op via signature equality**

> **Given** `sbtdd/spec-behavior.md` exists con signature
> `(mtime_ns=T0, size=N, sha256=H)`. The brainstorming stub rewrites
> the file with **identical bytes** under a fast-clock filesystem
> (e.g., FAT32 / network mount / container overlay) where mtime
> rounds to 1s precision; the rewrite lands within the same tick so
> `mtime_ns == T0` post-subprocess. Size and sha256 unchanged because
> content is identical.
> **When** `_run_spec_flow` ejecuta and reaches the
> `_file_signature(spec_behavior)` post-brainstorming check.
> **Then** Composite signature `(T0, N, H)` equals
> `spec_sig_before == (T0, N, H)`. Tuple equality detected → raises
> `PreconditionError` flagging the no-op rewrite. Bare-mtime check
> would have caught this specific instance (mtime equal), but the
> rationale extends to coarse-clock cases where two distinct write
> ticks may yield identical mtime tuples while content also matches —
> composite signature catches that via size + sha256 corroboration.
> This escenario guards against the FS-precision regression class
> documented in spec sec.2.1 composite-signature rationale.

### Item A1 — Permissive escenario regex

**Escenario A1-1: legacy fixture with §4 header still works**

> **Given** Spec con header literal `## §4 Escenarios BDD\n\n
> **Escenario 1: ejemplo**\n\n> Given...When...Then...`.
> **When** `spec_snapshot.emit_snapshot(path)` ejecuta.
> **Then** Returns `{"ejemplo": <hash>}` dict. Tier 1 path used (legacy
> regex matched).

**Escenario A1-2: distributed escenarios across pillar sections**

> **Given** Spec real production-style con escenarios distribuidos:
> `## 2. Pillar 1\n\n**Escenario X-1: ...**\n...` y
> `## 3. Pillar 2\n\n**Escenario Y-1: ...**\n...`. Sin header
> `## §4 Escenarios`.
> **When** `emit_snapshot(path)` ejecuta.
> **Then** Returns `{"X-1: ...": <hash1>, "Y-1: ...": <hash2>}`.
> Tier 1 falla; Tier 2 path used (whole-document scan).

**Escenario A1-3: zero escenarios anywhere raises ValueError**

> **Given** Spec sin ningun bloque `**Escenario X:**` ni `### Escenario`
> ni `## Escenario` heading. Solo prose.
> **When** `emit_snapshot(path)` ejecuta.
> **Then** Raises `ValueError` con mensaje "No escenarios found"
> mencionando ambos patterns (legacy + distributed). Zero-match guard
> preservado.

**Escenario A1-4: legacy header present but empty falls through to Tier 2**

> **Given** Spec con `## §4 Escenarios BDD` header literal pero sin
> contenido en esa seccion (escenarios distribuidos en otras secs).
> **When** `emit_snapshot(path)` ejecuta.
> **Then** Tier 1 falla por seccion vacia; Tier 2 succeeds. NO error;
> returns escenarios distribuidos. Forgiving fallback documented.

**Escenario A1-5: prose mention of word 'escenario' in commentary doesn't match scenario regex**

> **Given** Spec contains a section discussing scenario design in
> prose form, e.g. plain sentences like
> `"En el escenario donde el operador..."` or
> `"Este escenario fue evaluado por MAGI..."`. The word "escenario"
> appears but NOT in the strict `**Escenario X: ...**` /
> `## Escenario X: ...` / `### Escenario X: ...` form. NO real
> scenario blocks anywhere in the document.
> **When** `spec_snapshot.emit_snapshot(path)` ejecuta.
> **Then** Both Tier 1 and Tier 2 yield zero escenarios — the
> permissive Tier 2 regex still requires the strict scenario-block
> boundary syntax (bold-asterisks delimiters or heading prefix +
> trailing colon). Plain-prose mentions of the word "escenario" are
> NOT captured. Raises `ValueError("No escenarios found ...")`. This
> regression-guards Tier 2 from over-matching: the Tier 2 widening was
> for distributed-but-still-structured scenarios, not for plain prose.

### Item A2 — Headless-mode detection

**Escenario A2-1: brainstorming raises in headless mode**

> **Given** `superpowers_dispatch.invoke_skill(skill="brainstorming",
> args=[...])` invoked from script context (no Claude Code interactive
> session presente).
> **When** invoke_skill ejecuta.
> **Then** Raises `PreconditionError` ANTES de spawn subprocess.
> Mensaje incluye "Skill /brainstorming es interactivo" + sugiere
> `--resume-from-magi` recovery path.

**Escenario A2-2: writing-plans raises in headless mode**

> **Given** `invoke_skill(skill="writing-plans", args=[...])`.
> **When** invoke_skill ejecuta.
> **Then** Same as A2-1 con skill name = writing-plans.

**Escenario A2-3: magi:magi works in headless mode unchanged (regression)**

> **Given** `invoke_skill(skill="magi:magi", args=[...])` (or via
> `magi_dispatch.invoke_magi` wrapper).
> **When** invoke_skill ejecuta.
> **Then** Sin error en pre-subprocess check. Subprocess spawn
> proceeds. Existing v1.0.0 behavior preserved.

**Escenario A2-4: unknown skill name passes through (whitelist semantic)**

> **Given** `invoke_skill(skill="custom-skill", args=[...])` con skill
> name no en `_SUBPROCESS_INCOMPATIBLE_SKILLS` set.
> **When** invoke_skill ejecuta.
> **Then** Pre-check passes (whitelist semantic, no blacklist). Subprocess
> spawn proceeds. Conservative-by-default — solo Skills demonstrably-broken
> en `_SUBPROCESS_INCOMPATIBLE_SKILLS` set.

**Escenario A2-5: wrapper functions pass allow_interactive_skill=True internally so direct wrapper call still works**

> **Given** Production caller invokes the high-level wrapper
> `superpowers_dispatch.brainstorming(args=[...])` (NOT the low-level
> `invoke_skill`). The wrapper internally delegates to
> `invoke_skill(skill="brainstorming", ..., allow_interactive_skill=True)`.
> Same applies to `writing_plans` and any future wrapper produced via
> `_make_wrapper` factory or `_invoke_skill` helper.
> **When** wrapper call ejecuta.
> **Then** `invoke_skill`'s gate evaluates `skill in
> _SUBPROCESS_INCOMPATIBLE_SKILLS` → `True`, BUT
> `allow_interactive_skill=True` → gate short-circuits and proceeds to
> the subprocess flow. NO PreconditionError raised. Wrappers ARE the
> safe path — they coordinate manual dispatch and the operator already
> opted into interactive context. This escenario regression-guards
> against the C2/W6 blanket-raise pattern: if wrapper migration is
> incomplete, this escenario fails immediately and surfaces the gap.

### Item A3 — `--resume-from-magi` recovery flag

**Escenario A3-1: flag skips brainstorming and writing_plans**

> **Given** `sbtdd/spec-behavior.md` y `planning/claude-plan-tdd-org.md`
> existen (operator-produced). `superpowers_dispatch.brainstorming` y
> `writing_plans` monkeypatched a spies que registran si fueron called.
> **When** `spec_cmd.main(["--resume-from-magi", "--project-root",
> str(tmp)])` ejecuta.
> **Then** Spies NOT called. MAGI Checkpoint 2 dispatched. State file
> escrito. Commit chore: ejecutado.

**Escenario A3-2: flag still validates spec-base placeholder**

> **(Tentative — see decision below)** Si `--resume-from-magi` set pero
> spec-base contiene markers de INV-27 violation, behavior puede ser:
> (a) skip validation tambien (aggressive bypass), o (b) validate
> still (conservative). v1.0.1 implementation: **option (b) — validate
> still** porque INV-27 es invariante hard, no override-able. Test
> verifica que con marker presente raise sigue firing aunque
> --resume-from-magi sea pasado.

**Escenario A3-3: flag aborts when artifacts missing**

> **Given** `--resume-from-magi` flag set pero `spec-behavior.md` o
> `plan-tdd-org.md` no existen.
> **When** `spec_cmd.main([...])` ejecuta.
> **Then** Raises `PreconditionError` antes de MAGI dispatch.
> Mensaje sugiere correr `/brainstorming` + `/writing-plans` antes
> de re-tentar con flag.

**Escenario A3-4: flag combined with --override-checkpoint works**

> **Given** Operator quiere skip dispatch step Y override safety-valve
> exhaustion (escenario edge: ya tienen artifacts y MAGI cap=3 esta a
> punto de fail).
> **When** `spec_cmd.main(["--resume-from-magi", "--override-checkpoint",
> "--reason", "..."]).
> **Then** Both flags coexist. Dispatch skipped + safety-valve override
> path active. Test verifica composicion.

**Escenario A3-5: malformed spec rejected by structural validation**

> **Given** `--resume-from-magi` flag set. `sbtdd/spec-behavior.md`
> exists but is malformed: contains no `**Escenario` blocks nor any
> `## §4 Escenarios` section — only prose. `spec_snapshot.emit_snapshot`
> raises `ValueError` for this input (or returns empty dict).
> **When** `spec_cmd.main(["--resume-from-magi", ...])` ejecuta.
> **Then** Raises `PreconditionError` BEFORE MAGI dispatch is attempted.
> Error message references the spec path + the underlying
> `spec_snapshot.emit_snapshot` failure reason. Suggests running
> `/brainstorming` manually first. This guards W2/W8: existence check
> alone would let a stub-only spec proceed and waste a MAGI iter on an
> uninspectable input.

**Escenario A3-6: malformed plan rejected by structural validation**

> **Given** `--resume-from-magi` flag set. `sbtdd/spec-behavior.md` is
> structurally valid (yields snapshot). `planning/claude-plan-tdd-org.md`
> exists but is malformed: either contains no `### Task` heading
> (no task structure) OR contains no `- [ ]` checkbox (empty / all
> tasks pre-marked complete — wrong artifact stage).
> **When** `spec_cmd.main(["--resume-from-magi", ...])` ejecuta.
> **Then** Raises `PreconditionError` BEFORE MAGI dispatch. Error
> message identifies which structural check failed (Task heading
> regex vs checkbox regex) and the path. Operator guidance: regenerate
> plan via `/writing-plans` or hand-craft a valid plan-org file before
> retrying. Same defense-in-depth rationale as A3-5.

---

## 5. Subagent layout + execution timeline

v1.0.1 = single-subagent sequential execution. Bundle es chico (4
items, 10-15h estimado total) y todos tocan archivos compatibles:

- A0 → `spec_cmd.py` (function `_run_spec_flow`)
- A1 → `spec_snapshot.py` (function `emit_snapshot`)
- A2 → `superpowers_dispatch.py` (function `invoke_skill`)
- A3 → `spec_cmd.py` (function `_build_parser` + `main`)

Items A0 + A3 ambos tocan `spec_cmd.py` pero son edits independientes
(distintas funciones). Items A1, A2 son completamente separados.

**Sequential ordering recommended**: A1 → Pre-A2 → A0 → A2 → A3.

Rationale:
- **A1 first**: arregla el bug que crashea immediately al final del
  spec_cmd flow. Sin A1, no podemos correr el ciclo sobre el propio
  repo (Finding B).
- **Pre-A2 second**: audit + migrate the existing direct callers of
  `invoke_skill` (3 production sites in `superpowers_dispatch.py` +
  4 test callsites) to pass `allow_interactive_skill=True` BEFORE
  A2 lands its safe-by-default gate; otherwise A2 silently breaks
  the wrappers and the test suite. Plan task body documents the
  empirical audit (grep evidence preserved).
- **A0 second** (after A1 + Pre-A2): A0 is **permanent
  defense-in-depth runtime tripwire**. Even after A2 lands, a future
  regression in `_SUBPROCESS_INCOMPATIBLE_SKILLS` set membership (or
  a new interactive skill missed from the set) is caught at runtime
  by A0's composite-signature check on the actual output file. A0 is
  not redundant with A2; A0 is the **runtime guard** detecting
  "subprocess produced no output" while A2 is the **static guard**
  detecting "this skill should not have been dispatched as
  subprocess". Both are needed: A2 covers the known-broken set; A0
  covers the long tail (new interactive skills, regressions, FS-
  precision edge cases).
- **A2 third**: arregla el silent-no-op causa raiz para los skills
  conocidos. Con Pre-A2 ya aplicado, los wrappers y tests usan el
  override correctamente.
- **A3 last**: recovery flag. Habilita el path para futuros operators
  que quieran bypass dispatch despues de manual brainstorming.

**Wall time**: ~10-15h total una sola sesion. Single subagent o
manual dispatch del orchestrator.

---

## 6. Final review loop strategy

### 6.1 MAGI Checkpoint 2 (spec + plan)

Cap = 3 HARD per G1 binding (CHANGELOG `[1.0.0]`). NO INV-0 path.
Bundle es chico (4 items, single-pillar) — deberia converger en
1-2 iters limpios. Si llega a iter 3 sin convergencia, scope-trim
mandatorio (no override).

### 6.2 Loop 1 (`/requesting-code-review`)

Cap=10. Clean-to-go criterion: zero CRITICAL + zero high-impact
WARNING. Bundle scope minimal — esperamos converger en 1 iter.

### 6.3 Loop 2 (`/magi:magi`)

Cap=5 per `auto_magi_max_iterations`. Cross-check (Feature G v1.0.0)
disponible — `magi_cross_check: true` flag set en `plugin.local.md`
durante este ciclo.

**Important caveat**: Loop 2 propio dispatch via `/sbtdd pre-merge`
**REQUIRES Item A0+A1 already shipped** porque sino spec_cmd crashea
en mtime check (A0 absent) o spec_snapshot regex (A1 absent). Por
diseño, v1.0.1 own-cycle Loop 2 USES the v1.0.1 fixes — first
self-validation pass.

### 6.4 G2 binding active

Si Loop 2 iter 3 no converge clean, scope-trim default (defer items
a v1.0.2 si necesario). Bundle chico mitiga este riesgo.

### 6.5 Loop 2 own-cycle fallback

If `/sbtdd pre-merge` itself fails on iter X due to an A0/A1/A2/A3
regression triggering during the v1.0.1 own-cycle (chicken-and-egg:
the same fixes are shipping during a cycle that uses them), the
operator MUST fall back to manual `python skills/magi/scripts/run_magi.py
code-review <payload>` direct dispatch + manual mini-cycle commits,
exactly as v1.0.0 cycle was conducted before Feature G cross-check
existed in production. Document the fallback choice + iteration in
CHANGELOG `[1.0.1]` Process notes. The v0.5.0 + v1.0.0 ship cycles
are precedent that this manual fallback is workable; R4 risk register
entry covers this scenario.

**Verbatim fallback command** (W1 balthasar iter 2): warm + ready
to copy-paste:

```bash
mkdir -p .claude/magi-runs/v101-checkpoint2-loop2-iter1
{
  cat .claude/magi-runs/v101-loop2-iter1-header.md  # operator-prepared
  echo "---"
  cat sbtdd/spec-behavior.md
  echo "---"
  cat planning/claude-plan-tdd.md
} > .claude/magi-runs/v101-loop2-iter1-payload.md
python skills/magi/scripts/run_magi.py code-review \
  .claude/magi-runs/v101-loop2-iter1-payload.md \
  --model opus --timeout 900 \
  --output-dir .claude/magi-runs/v101-loop2-iter1
```

**A0 escape hatch documentation** (W5 caspar iter 2): the
`--resume-from-magi` flag explicitly bypasses A0 composite-signature
mtime check because operator-acknowledged manual artifacts (produced
out-of-band via `/brainstorming` + `/writing-plans` interactive
session, OR via hand-crafting like v1.0.1's own cycle) do NOT have
their mtime ticked by a subprocess. INV-37 mtime-tripwire applies
ONLY when `_run_spec_flow` dispatches Skills via subprocess; resume
path skips `_run_spec_flow` entirely. Document this in CHANGELOG
`[1.0.1]` Process notes so future operators understand the escape
semantics.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 1.0.0 → 1.0.1.

### 7.2 CHANGELOG `[1.0.1]` sections

- **Fixed** — Finding A (headless detection), Finding B (permissive
  regex), Finding C (output validation).
- **Added** — `--resume-from-magi` flag, `_SUBPROCESS_INCOMPATIBLE_SKILLS`
  set, A0 composite-signature tripwire.
- **Process notes** — dogfood findings empirical record + INV-37
  proposal + v1.0.0 LOCKED items rolled to v1.0.2.
- **Deferred (rolled to v1.0.2)** — telemetry script, diff threading,
  spec_lint, own-cycle dogfood (todos los items LOCKED del original
  v1.0.1 plan).

### 7.3 README + SKILL.md + CLAUDE.md

- **README**: v1.0.1 docs section sobre `--resume-from-magi` flag use
  case.
- **SKILL.md**: `### v1.0.1 notes` section documentando headless-mode
  detection + recovery flag.
- **CLAUDE.md**: v1.0.1 release notes pointer.

---

## 8. Risk register v1.0.1

- **R1**. Item A2 headless detection puede ser too aggressive y romper
  casos legitimos donde Skills "interactive" funcionan parcialmente.
  Mitigation: limit a `_SUBPROCESS_INCOMPATIBLE_SKILLS = {"brainstorming",
  "writing-plans"}` set conservatively; whitelist semantic, not
  blacklist.

- **R2**. Item A1 Tier 2 fallback podria over-match y capturar bloques
  que NO son escenarios reales. Mitigation: `_SCENARIO_HEADER_RE`
  preserved (requires `**Escenario\s+...**` boundary chars), no
  plain text match.

- **R3**. Item A3 `--resume-from-magi` puede ser misused como bypass
  general. Mitigation: documented como recovery-path-only; A3-2
  preserva INV-27 validation aunque el flag sea pasado.

- **R4**. v1.0.1 own-cycle pre-merge requires the same fixes that are
  shipping. Chicken-and-egg pero mitigable: este own-cycle se conduce
  manualmente (operator drives `/brainstorming` + `/writing-plans`
  interactivamente en sesion Claude Code activa, luego `/sbtdd spec`
  ejercita Checkpoint 2). Recovery flag A3 valida via test_a3_*.

- **R5**. Bundle scope minimal pero F-numbers totales son 10 (F90-F99)
  — bajo el +30-40 NF-B target del v1.0.0 spec. Acceptable porque
  v1.0.1 es defensive-only fix release; ~21-25 nuevos tests (post-iter-1
  triage expansion) es proporcional al scope.

- **R6**. Items diferidos a v1.0.2 (telemetry, diff threading,
  spec_lint, own-cycle dogfood) podrian de-prioritizar si v1.0.2
  cycle hits otros findings empiricamente. Mitigation: CHANGELOG
  `[1.0.1]` Process notes lista los 4 items rolled forward con
  explicit "v1.0.2 LOCKED" marker.

- **R7**. Test count delta (+21-25) por debajo del v1.0.0 nominal
  ratio. Mitigation: scope justifica — fixes son defensive checks +
  flag + regex relax + pre-A2 migration, no nuevas features.

---

## 9. Acceptance criteria final v1.0.1

v1.0.1 ship-ready cuando:

### 9.1 Functional Item A0

- **F1**. Composite-signature check (mtime_ns + size + sha256) antes/
  despues de brainstorming subprocess.
- **F2**. Composite-signature check antes/despues de writing-plans
  subprocess.
- **F3**. Raise `PreconditionError` con guidance si signature tuple
  unchanged.
- **F4**. First-run path (file ausente pre-subprocess) tolerado sin
  error.
- **F5**. A0-1 a A0-5 tests pass (5 escenarios; A0-5 covers FS-precision
  same-content rewrite regression class).

### 9.2 Functional Item A1

- **F6**. `emit_snapshot` Tier 1 path preserved (legacy fixtures).
- **F7**. Tier 2 fallback escanea documento entero.
- **F8**. Zero-match guard preservado; prose mentions of word
  "escenario" do NOT match (A1-5 regression guard).
- **F9**. A1-1 a A1-5 tests pass (5 escenarios).

### 9.3 Functional Item A2

- **F10**. `_SUBPROCESS_INCOMPATIBLE_SKILLS` frozenset definido.
- **F11**. `invoke_skill` raises antes del subprocess para skills en
  el set when `allow_interactive_skill=False` (default).
- **F11b**. `invoke_skill` proceeds when
  `allow_interactive_skill=True`; wrapper functions and `_make_wrapper`
  / `_invoke_skill` internals pass the override automatically.
- **F12**. Skills no-interactivos (magi:magi) sin afectacion.
- **F13**. A2-1 a A2-5 tests pass (5 escenarios; A2-5 covers wrapper
  override path).

### 9.4 Functional Item A3

- **F14**. `--resume-from-magi` flag added a `_build_parser`.
- **F15**. `spec_cmd.main` skipea `_run_spec_flow` cuando flag set.
- **F16**. INV-27 validation preservado (NOT bypassed) por flag.
- **F16b**. Structural validation (spec_snapshot parse + plan
  `### Task` heading + `- [ ]` checkbox regex) ejecuta cuando flag
  set, antes de MAGI dispatch.
- **F17**. A3-1 a A3-6 tests pass (6 escenarios; A3-5 + A3-6 cover
  malformed-artifact rejection).

### 9.5 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format +
  mypy --strict, runtime <= 150s. Soft-target <= 130s.
- **NF-B**. Tests baseline 1033 + 1 skipped + ~21-25 nuevos =
  ~1054-1058.
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en archivos modificados.
- **NF-E**. Zero modificacion a modulos frozen excepto los
  enumerados (`spec_cmd.py`, `superpowers_dispatch.py`,
  `spec_snapshot.py`).

### 9.6 Process

- **P1**. MAGI Checkpoint 2 verdict >= GO_WITH_CAVEATS full per
  INV-28. Iter cap=3 HARD per G1 binding; NO INV-0 path.
- **P2**. Pre-merge Loop 1 clean-to-go + Loop 2 verdict >=
  GO_WITH_CAVEATS full no-degraded.
- **P3**. CHANGELOG `[1.0.1]` entry written.
- **P4**. Version bump 1.0.0 → 1.0.1 sync.
- **P5**. Tag `v1.0.1` + push (con autorizacion explicita user).
- **P6**. `/receiving-code-review` skill applied to every Loop 2 iter
  findings sin excepcion.
- **P7**. Empirical proof-of-recovery: en sesion Claude Code nueva
  con `magi_cross_check: true`, correr /brainstorming +
  /writing-plans manualmente, luego `/sbtdd spec --resume-from-magi`
  debe completar end-to-end (validates A3 recovery path on real
  cycle, not just unit-test).

### 9.7 Distribution

- **D1**. Plugin instalable.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos flags documentados en README + SKILL.md + CLAUDE.md.

---

## 9.8 Inherited invariants from v0.4.x (HF1 cross-artifact wording)

The v0.4.0 manual-synthesis recovery breadcrumb wording is preserved
verbatim across spec / CHANGELOG / impl per the HF1 cross-artifact
alignment contract (`tests/test_changelog.py`). v1.0.1 ships no
behavioral change to this path; the wording is repeated here so the
v0.4.x invariant survives the v1.0.1 spec rewrite (same pattern as
v1.0.0 spec sec.10.7).

**Canonical wording**: `[sbtdd magi] synthesizer failed; manual synthesis recovery applied`

When `magi_dispatch.invoke_magi` is called with `allow_recovery=True`
(default ON since v0.4.0 F46.5) and the orchestrator-side synthesizer
crashes, the dispatch path reconstructs the consensus from per-agent
JSON outputs and emits the canonical breadcrumb to stderr. Every
artifact that documents this fall-back path uses identical wording so
HF1's whitespace-normalized cross-file search matches consistently.

---

## 10. Referencias

- Spec base v1.0.1: `sbtdd/spec-behavior-base.md` (commit `8e7295a`).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4+v0.5+v1.0 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- v1.0.0 ship record: tag `v1.0.0` (commit `0992407` on `main`).
- v1.0.0 dogfood findings (2026-05-03): preservados en sesion log;
  `MAGIGateError: did not write magi-report.json` y `ValueError: No
  §4 Escenarios section found` son los stack traces empiricos.
- v1.0.0 LOCKED commitments rolled forward a v1.0.2 per CHANGELOG
  `[1.0.0]` Deferred section + nuevo CHANGELOG `[1.0.1]` Process
  notes rolled-forward bullets.
- v1.0.3 LOCKED parallel task dispatcher: nuevo backlog item
  registrado 2026-05-03 (CHANGELOG `[1.0.0]` Deferred + memory
  `project_v103_parallel_task_dispatcher.md`).
- Branch: trabajo en `feature/v1.0.1-bundle` (branched off `main`
  HEAD `0992407` = v1.0.0 ship).
