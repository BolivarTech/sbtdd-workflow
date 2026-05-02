# BDD overlay — sbtdd-workflow v0.5.0

> Generado por `/brainstorming` el 2026-05-01 a partir de
> `sbtdd/spec-behavior-base.md` (v1.0.0 raw input post-v0.3.0) + decisiones
> de session 2026-05-01:
> - Q1 = B (1.0 es siguiente milestone, no graduacion formal; BREAKINGs OK)
> - Q2 = C (large bundle: todo LOCKED salvo INV-31 default flip)
> - Q3 = C (observability con ambos modos: heartbeat in-band + status --watch
>   out-of-band)
> - Q4 = C (heartbeat content: liveness + dispatch + macro progress)
> - Approach C: **split en v0.5.0 (observability) + v1.0.0 (semantic
>   features + tag estable)**.
>
> v0.5.0 es el primer ciclo del split. Ships el pillar observability +
> v0.4.1 hotfixes folded in. Bumpea 0.4.0 -> 0.5.0 (MINOR, non-BREAKING --
> aditivo).
>
> v1.0.0 cubre el resto del backlog post-v0.3.0: Feature G (cross-check),
> F44.3 (retried_agents propagation), J2 (ResolvedModels preflight), Feature
> I (schema_version + migrate skeleton), Feature H Group B option 2
> (spec-snapshot diff check), option 5 (auto-gen scenario stubs). Out of
> scope v1.0.0: INV-31 default flip decision (defer a v1.x con field-data
> doc), Group B option 1 / 3 / 4 / 6 / 7 (opt-in flags only).
>
> Source of truth autoritativo para v0.1+v0.2+v0.3+v0.4 frozen se mantiene
> en `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
>
> INV-27 compliant: cero matches uppercase placeholder en este archivo.

---

## 1. Resumen ejecutivo

**Objetivo v0.5.0:** ship observability foundation como pilar central del
ciclo. UX gap empirico: durante dispatches largos (MAGI 5-10 min,
`/requesting-code-review` 2-5 min) el operador ve nada en stderr y el
proceso parece muerto. v0.5.0 cierra ese gap con dos modos
complementarios:

- **Heartbeat in-band** (nuevo) — context manager wrapping long dispatches;
  daemon thread emite stderr breadcrumb cada ~15s con iter / phase / task /
  dispatch / elapsed.
- **`/sbtdd status --watch`** (D5) — companion subcommand que poll
  `auto-run.json` mtime y renderiza live status; default TTY rewrite-line,
  `--json` flag para piping out-of-band.

Plus dos refinements al streaming pump existente:
- **Per-stream timeout** (J3) — kill subprocess que no escribe newlines en
  N seconds (catches actual hangs vs heartbeat alive).
- **Origin disambiguation** (J7) — etiqueta `[stdout]` / `[stderr]` cuando
  ambos streams emiten en mismo flush window (ambiguity en MAGI subprocess
  output).

Plus folded:
- **v0.4.1 hotfixes** — 3 doc-alignment items de v0.4.0 MAGI iter 1+2 INFO
  findings (recovery breadcrumb wording alignment spec ↔ CHANGELOG ↔
  impl, marker file schema actual emission docs, F45 verdict-set behavior
  delta documentation).

**Known Limitations folded from Checkpoint 2 iter 3 caspar finding:**
- **started_at race window during dispatch_label transitions**: in theory,
  a heartbeat tick could fire between the moment `_set_progress` mutates
  `_current_progress` to a new dispatch's pre-state and finishes the
  atomic snapshot replacement. Under current single-threaded `auto_cmd`
  this race window does NOT occur (writer + caller are same thread,
  reader thread sees consistent post-write state). Documented for future
  parallel auto_cmd designs that may relax single-thread invariant.

**Out-of-scope v0.5.0** (defer a v1.0.0):
- Feature G (MAGI -> /requesting-code-review cross-check).
- Feature H Group B re-eval + INV-31 default-on opt-in re-eval.
- Feature I (schema_version: 2 + migration tool).
- F44.3 retried_agents propagation a auto-run.json (sub-item de Feature F
  closure).
- J2 INFO #10 ResolvedModels preflight dataclass.
- J7-tangent origin-stream parsing of internal subprocess events (this
  spec only adds basic disambiguation labels, not deep origin tracing).

**Criterio de exito:**
- Tests baseline 818 (v0.4.0) preservados + ~30-40 nuevos = 848-858.
- `make verify` clean (pytest + ruff + mypy --strict, runtime <= 90s).
- MAGI Loop 2 final review converge en <= 3 iter (recursive payoff: si
  caspar crashea otra vez, F's auto manual-synthesis recovery YA shipped
  en v0.4.0 lo rescata; v0.5.0 ADDITIONALLY el operador ve EXACTAMENTE en
  que esta colgado durante MAGI dispatch tiempo real via heartbeat).
- Zero regression en streaming surface de v0.3.0 / v0.4.0.

**Recursive payoff oportunity:** v0.5.0 ships heartbeat + status --watch
durante su propio cycle. El final review loop (MAGI 5-10 min per dispatch)
es el caso de uso paradigmatico para heartbeat. Si el subagent que ships
heartbeat lo hace primero en el cycle, el orchestrator's MAGI Loop 2 puede
empirically validar UX en vivo.

---

## 2. Pillar observability — 4 deliverables + hotfixes

### 2.1 Heartbeat in-band emitter (NEW)

**Files tocados:** `models.py` (+`ProgressContext` dataclass),
`scripts/heartbeat.py` (NEW module — sibling a `subprocess_utils.py`, NO
sub-directory), `auto_cmd.py` (+ProgressContext write hooks en las 10
transitions enumeradas en sec.3 + HeartbeatEmitter wraps long dispatches).

**Invariantes nuevos propuestos:**
- INV-32 (propuesta): heartbeat thread NO debe bloquear ni matar el auto run
  bajo ningun fallo (stderr broken pipe, OSError, etc.). Failures se
  swallow con counter + breadcrumb on first failure only.

**Escenario H1: heartbeat emite primer tick a t=0 + ticks subsiguientes cada interval**

> **Given** auto run en mid-MAGI Loop 2 dispatch (subprocess running ~5
> min sin escribir nada en stderr). HeartbeatEmitter recien __enter__'d.
> **When** thread loop arranca.
> **Then** stderr emite **inmediatamente** (t=0) linea
> `[sbtdd auto] tick: iter 2 phase 3 task 14/36 dispatch=magi-loop2-iter2 elapsed=0m0s`
> (operator ve liveness signal ASAP). Despues, cada 15s, emite tick
> subsiguiente con elapsed creciendo monotonically dentro del mismo
> dispatch. Pinned post-Checkpoint 2 iter 3 melchior finding: emit-at-entry
> semantica documentada explicit, alineada con impl que llama
> `_emit_tick()` BEFORE el primer `_stop_event.wait(interval)`.

**Escenario H2: heartbeat NO bloquea exit cuando dispatch termina**

> **Given** HeartbeatEmitter activo en context manager wrap de un dispatch.
> Implementacion PINNED (post-iter 2): thread loop usa `threading.Event.wait(interval)`
> en lugar de `time.sleep(interval)` — la wait es interruptible por signal.
> **When** el dispatch retorna (subprocess termina, o exception, o timeout).
> **Then** `__exit__` calls `_stop_event.set()` to interrupt the thread's
> `Event.wait(15)` mid-sleep + then `.join(timeout=2s)`. Thread sale del
> wait inmediatamente al recibir el signal y ejecuta su cleanup. Dispatch
> return path no se bloquea > 2s waiting for thread under any tick cadence.

> **Implementation note:** time.sleep(15) NO es aceptable para tick loop —
> `__exit__.join(2s)` no puede interrumpir un sleep activo, asi que un thread
> mid-sleep al momento de exit forzaria al join a esperar hasta 15s mas
> antes de poder limpiar. `threading.Event.wait(timeout=15)` resuelve esto:
> wait retorna inmediatamente cuando event se setea, o transcurre el
> timeout completo si nunca se setea (caso normal entre ticks).

**Escenario H3: heartbeat resilient a stderr write failure + queue-based persistence**

> **Given** HeartbeatEmitter activo con stderr cerrado / broken pipe (caso
> patologico: piping to head, terminal closed, etc.).
> **When** thread loop intenta escribir tick.
> **Then** OSError caught, counter `_failed_writes` incrementa, primer
> fallo emite single warning a stderr en formato
> `[sbtdd auto] heartbeat write failed (will continue silently): <error>`,
> ticks subsiguientes silent. Auto run NO killed; thread sigue runneando
> hasta __exit__ signal. **Adicionalmente** (post-iter 2/3 + Checkpoint 2
> melchior/caspar findings), cada N=10 incrementos del counter, thread
> envia el counter a `_failures_queue: queue.Queue[int]` via `put_nowait`.
> El queue es drained por el main thread (auto_cmd) en cada
> `_update_progress` call y persistido a `auto-run.json` bajo
> `heartbeat_failed_writes_total` field — heartbeat thread NUNCA escribe
> directamente al archivo (sec.3 single-writer rule). Si stderr ES el
> broken pipe, el audit trail sigue capturando counter via queue → main
> thread → auto-run.json.

> **And given** HeartbeatEmitter `__exit__` invocado con `_failed_writes > 0`.
> **When** exit fires.
> **Then** envia el counter final a `_failures_queue.put_nowait` (best-effort;
> swallow on queue.Full) + logs summary breadcrumb a stderr en formato
> `[sbtdd auto] heartbeat completed with N silent write failures`
> (best-effort; si stderr broken, breadcrumb pierde pero counter ya esta
> en queue para drain del main thread).

**Escenario H4: ProgressContext immutable per-snapshot, lock-protected reference swap**

> **Given** auto_cmd writes `ProgressContext` cada phase/task/dispatch
> transition usando module-level singleton reference. Module exports
> `_progress_lock: threading.Lock` + `_current_progress: ProgressContext`
> + getter/setter protocol PINNED post-iter 2 / iter 3 (cross-reference
> sec.3 mutation contract).
> **When** HeartbeatEmitter thread reads ProgressContext mid-update.
> **Then** read sees EITHER pre-update snapshot OR post-update snapshot,
> never partial state. **Pinned implementation**: frozen dataclass +
> threading.Lock-protected get/set in `scripts/heartbeat.py`. Writer
> calls `set_current_progress(new_ctx)` (acquires lock, swaps reference,
> releases). Reader calls `get_current_progress()` (acquires lock, reads
> reference, releases) — operates on returned immutable snapshot WITHOUT
> further locking. Lock chosen sobre lockless atomic-pointer approach
> (iter 1 design) per iter 2 caspar finding: cheap immunization contra
> PEP 703 free-threaded Python + maintainer drift.

**Escenario H5: heartbeat content matches design Q4 = C**

> **Given** ProgressContext con `iter_num=2, phase=3, task_index=14,
> task_total=36, dispatch_label="magi-loop2-iter2", started_at=...`.
> **When** tick fires con elapsed=15s.
> **Then** stderr line es exactamente
> `[sbtdd auto] tick: iter 2 phase 3 task 14/36 dispatch=magi-loop2-iter2 elapsed=0m15s`
> (cuatro fields + elapsed con format `<min>m<sec>s`).

**Escenario H6: heartbeat omite fields null gracefully**

> **Given** ProgressContext en preflight phase (phase=1, task_index=None,
> task_total=None, dispatch_label=None).
> **When** tick fires.
> **Then** stderr line es
> `[sbtdd auto] tick: phase 1 elapsed=0m45s`
> (omite iter / task / dispatch fields cuando son None; no escribe `task=None/None`).

### 2.2 `/sbtdd status --watch` companion subcommand (D5)

**Files tocados:** `status_cmd.py` (extension --watch + helpers),
`run_sbtdd.py` (subcommand argv parsing accepts --watch + --interval +
--json flags).

**Escenario W1: watch poll loop renderiza TTY rewrite-line por default**

> **Given** auto run activo escribiendo `auto-run.json` con progress
> snapshots.
> **When** otra terminal corre `python run_sbtdd.py status --watch`.
> **Then** stdout muestra rewrite-line render (\\r + clear) con spinner +
> texto `iter N phase P task T/N dispatch=L elapsed=T` actualizado cada
> 1s default.

**Escenario W2: watch --json modo emite linea JSON por cambio**

> **Given** auto run activo + watch invocado con `--json`.
> **When** cada poll detecta cambio en `auto-run.json` progress fields.
> **Then** stdout emite una linea
> `{"timestamp": "<iso8601>", "progress": {<fields>}}`. Skip duplicates by
> hash (no spam si nada cambio).

**Escenario W3: watch sale exit 0 si auto-run.json missing**

> **Given** ningun auto run activo (no `.claude/auto-run.json` file).
> **When** se invoca `status --watch`.
> **Then** stderr breadcrumb `[sbtdd status] no auto run in progress` +
> exit 0 inmediato. NO espera ni reintenta.

**Escenario W4: watch tolerant a JSON parse error mid-write con visible counter + slow-poll fallback**

> **Given** auto run actively writing `auto-run.json` via tmpfile + os.replace
> atomic rename. Race window: poll lee `auto-run.json` mid-rename con bytes
> incompletos. Adicionalmente Windows AV scanners pueden retener el archivo
> mid-rename hasta ~500ms (typical) o sustained durante AV storms (>1s).
> **When** poll JSON parse fails.
> **Then** retry 5x con exponential backoff (50ms, 100ms, 200ms, 400ms,
> 500ms cap = ~1.25s total budget); si fail-5, increment internal counter
> `_json_parse_failures`, emit stderr breadcrumb
> `[sbtdd status] contention: JSON parse failed after 5 retries (cumulative=N)`
> en exhaustion (visible al operador, NO silent), skip render cycle, continue
> next poll. NO crash.

> **And given** `_json_parse_failures >= 3` consecutive **JSON parse failures**
> (sustained AV storm detected; **NO** counted: idle auto run with no
> progress changes — that returns same data successfully, NOT a parse
> failure).
> **When** next poll cycle scheduled.
> **Then** **slow-poll fallback** active: poll interval doubled
> (default 1s → 2s; cap at 10s). Counter resets cuando next JSON parse
> succeeds (NOT cuando idle returns same data). Avoids busy-loop
> saturating disk during sustained AV; idle auto run continues at default
> interval (operator wants live updates, not slow-poll).

> **Critical distinction (PINNED post-Checkpoint 2 iter 1 caspar finding):**
> `record_failure()` solo se llama cuando `_read_auto_run_with_retry`
> retorna `None` (5x retries exhausted on JSON parse error), NO cuando el
> retry succeeds and progress dict equals previous (idle case). Conflating
> idle vs contention degrades watch UX: an idle auto-run would falsely
> trigger slow-poll, masking when MAGI dispatch finishes.

**Escenario W5: watch handles Ctrl+C cleanly**

> **Given** watch corriendo en TTY mode con rewrite-line active.
> **When** operator hits Ctrl+C.
> **Then** restore terminal cursor + emit final newline + exit 130 (SIGINT
> standard exit code).

**Escenario W6: watch --interval flag override default 1s poll**

> **Given** invocacion con `--interval=5`.
> **When** poll loop runs.
> **Then** poll cada 5 seconds en lugar de 1s default. Validation: interval
> >= 0.1s (sub-100ms genera CPU spinning sin valor); else ValidationError
> -> exit 1.

### 2.3 Per-stream timeout (J3)

**Files tocados:** `subprocess_utils.py` streaming pump (extends `last_write_at`
tracking + kill on silent stream).

> **v0.5.0 ship scope (Loop 2 WARNING #4 alignment):** v0.5.0 ships J3
> as an **opt-in helper** (`subprocess_utils.run_streamed_with_timeout`).
> The behavioral contract below (timeout floor, allowlist, semantics)
> describes the helper's behavior, not the production-wired behavior of
> existing `run_with_timeout` callers. Production wiring of the 33
> existing dispatch sites in `auto_cmd.py` / `pre_merge_cmd.py` is
> **deferred to v0.5.1** per CHANGELOG `[0.5.0]` Deferred section.
> Existing callers retain their pre-v0.5.0 wall-clock-only timeout
> until they are migrated.

**Default rationale:** `auto_per_stream_timeout_seconds = 900` (15 min).
Iter 2 review consolido el balance entre iter 1 caspar finding ("600s mata
legitimate caspar runs >10min") y iter 2 melchior/balthasar pushback ("1800s
demasiado generoso para default"). 900s = 15min cubre worst-case caspar opus
runs observados (~10 min) con 5min margin antes de kill, sin overshoot.

**Absolute timeout floor (PINNED post-Checkpoint 2 iter 1 caspar finding):**
INV-34 clause 4: `auto_per_stream_timeout_seconds >= 600`. Razon: incluso
con clause 1 (timeout >= 5*interval), si interval=15 entonces timeout
podria ser tan bajo como 75s — que kill legitimate caspar opus runs (~10 min
empirically observed). 600s absolute floor garantiza que ningun dispatch
caspar normal sea killed por config user pathological. Validation message:
`auto_per_stream_timeout_seconds must be >= 600s (caspar opus runs observed
empirically up to 10min); got <T>s`.

**Allowlist mechanism (post-iter 2):** field
`auto_no_timeout_dispatch_labels: list[str]` con default `["magi-*"]` glob
exempts MAGI dispatches por completo del per-stream timeout. Razon empirica:
MAGI agents escriben a `.raw.json` files INTERNAMENTE pero el subprocess
mismo puede stay quiet en stdout/stderr durante el opus eval (hasta 10+ min
observado). Per-stream timeout fires-on-silence en ese subprocess seria
falso positivo. Allowlist exempts `magi-*` labels mientras preserve timeout
para subagent dispatches normales (TDD phase agents, code-review, etc.) que
deberian escribir logs regularmente.

**Semantica per-stream (PINNED post-iter 2):** kill SOLO cuando TODOS
los streams active estan silent simultaneamente — `all-streams silent`
(lenient). Caso edge: subprocess que escribe regularmente a stdout pero
nunca a stderr (legitimo: stderr reserved for errors solo) NO triggers
kill bajo lenient policy. Aggressive `any-stream silent` policy fue
considered + rejected per iter 2 caspar finding (kills healthy subprocesses
con asymmetric stream usage).

Adicionalmente: `subprocess_utils` tracking applies SOLO a subprocess
dispatches; NO al stderr del orchestrator mismo (heartbeat thread writes
a stderr orchestrator NO triggerea timeout).

**Escenario T1: subprocess que NO escribe a NINGUN stream OPEN kills despues timeout**

> **Given** subprocess corriendo que escribe nada en stdout NI stderr,
> ambos streams OPEN (no EOF received). `auto_per_stream_timeout_seconds=900`.
> Dispatch label NO matchea allowlist.
> **When** transcurren 900s sin que NINGUN stream open emit chunk.
> **Then** subprocess killed via existing kill-tree path (taskkill on
> Windows BEFORE proc.kill — preserves R3-1 invariant from MAGI v2.1.x;
> ver T7). Stderr breadcrumb
> `[sbtdd] killed subprocess (all open streams silent for >900s); ` +
> `add 'dispatch_label_pattern' to plugin.local.md auto_no_timeout_dispatch_labels to exempt`.
> Auto cmd trata el dispatch como failure (existing exit code path, no
> new).

**Escenario T2: dispatch normal con writes regulares no triggers kill**

> **Given** subprocess activo escribiendo lineas regulares (e.g., MAGI
> agent progress).
> **When** poll loop checks `last_write_at` despues de cada read.
> **Then** `last_write_at[stream] = time.monotonic()` resetted. Timeout
> nunca expires durante dispatch saludable.

**Escenario T3: timeout configurable via plugin.local.md**

> **Given** `plugin.local.md` con `auto_per_stream_timeout_seconds: 600`
> override (operator quiere kill mas agresivo en CI / quick-fail context).
> **When** auto run starts.
> **Then** PluginConfig.auto_per_stream_timeout_seconds == 600; pump uses
> 600s no 900s default. Override valido si operator entiende risk.

**Escenario T4: invariante timeout >> N * heartbeat_interval validado**

> **Given** PluginConfig load detecta
> `auto_per_stream_timeout_seconds < 5 * auto_heartbeat_interval_seconds`
> (e.g., timeout=10s, interval=15s — timeout fires antes del primer tick).
> **When** PluginConfig validation runs.
> **Then** raises `ValidationError("auto_per_stream_timeout_seconds must
> be >= 5 * auto_heartbeat_interval_seconds; got T=<t>s, I=<i>s")`. Plugin
> abort con exit 1 antes de cualquier dispatch. Razon: timeout corto
> bloquea heartbeat antes de su primer signal de vida. Multiplier 5x
> rationale: garantiza minimo 5 ticks visibles al operador antes de
> que el subprocess pueda ser killed por silence — operator awareness
> precede kill.

**Escenario T5: allowlist exempts magi-* dispatches del timeout**

> **Given** dispatch con `dispatch_label="magi-loop2-iter2"` (matches
> default allowlist `["magi-*"]`). subprocess no emite stdout/stderr
> durante 900s (caspar opus eval typical).
> **When** pump checks timeout for matching label.
> **Then** timeout NO kicks in para esta dispatch — pump treats label
> match as exempt. Subprocess corre sin kill until natural completion or
> external timeout from MAGI orchestrator. Stderr breadcrumb opcional
> `[sbtdd] timeout exempt: dispatch_label=magi-loop2-iter2 matched allowlist`
> (one-shot per dispatch on first 60s tick, no spam).

**Escenario T6: allowlist customizable via plugin.local.md**

> **Given** `plugin.local.md` con
> `auto_no_timeout_dispatch_labels: ["magi-*", "long-build-*"]` override.
> **When** pump checks timeout for `dispatch_label="long-build-foo"`.
> **Then** matches custom allowlist glob; timeout exempt. Operator extiende
> allowlist a otros tipos de dispatches conocidos slow.

**Escenario T7: closed stream excluded from timeout tracking**

> **Given** subprocess que cierra stdout deliberadamente (e.g., stdin
> redirect upstream que cierra stdout-as-fd-1). stderr permanece open y
> escribe regularmente.
> **When** pump detects EOF en stdout via read returning empty.
> **Then** stdout REMOVED de tracking set; solo stderr cuenta toward
> timeout. NO kill mientras stderr emit chunks regularly. Distingue
> closed (EOF received, legitimate single-stream) vs quiet-but-open
> (potential hang).

**Escenario T8: Windows kill-tree order R3-1 invariant preserved**

> **Given** subprocess timeout fires en Windows. Kill path executes.
> **When** subprocess_utils.kill_subprocess_tree(proc) called.
> **Then** `taskkill /F /T /PID <pid>` executes BEFORE `proc.kill()` —
> preserves R3-1 invariant inherited from MAGI v2.1.x (taskkill orphan
> children first, then proc.kill main). Test
> `tests/test_subprocess_utils.py::test_kill_tree_order_preserved`
> mocks subprocess + verifica order via call sequence assertion.

### 2.4 Origin disambiguation (J7)

**Files tocados:** `subprocess_utils.py` streaming pump (detect interleaved
emission, prefix lines), `config.py` (+`auto_origin_disambiguation: bool = True`
field).

> **v0.5.0 ship scope (Loop 2 WARNING #4 alignment):** v0.5.0 ships J7
> as an **opt-in helper** inside the same
> `subprocess_utils.run_streamed_with_timeout` entry point as J3. The
> 100ms-window prefix logic described below applies only to that
> helper's call sites; existing pump consumers in `auto_cmd.py` /
> `pre_merge_cmd.py` retain unprefixed streaming until v0.5.1
> production-wires them. See CHANGELOG `[0.5.0]` Deferred section.

**Config gate rationale:** post-MAGI Checkpoint 2 review v0.5.0 iter 1,
parser-sensitive contexts (downstream tools que consumen raw subprocess
output) pueden fallar al ver prefix conditional. Solucion: feature gated
behind `auto_origin_disambiguation: bool = True` (default ON para visibility
gain). Operator que pipea output a parser regex puede setear `false` en
`plugin.local.md` para preservar bytes raw.

**"Same iteration" semantica PINNED (post-iter 2 melchior+caspar findings):**
platform-dependent primitives (`select.select` Unix, `selectors.DefaultSelector`
Windows) tienen polling granularity que varia. Para spec deterministic,
"same iteration" se define como **ambos streams emiten chunks dentro de la
misma 50ms temporal window** del read loop. Implementation:
- Pump records `last_chunk_at[stream]` per chunk emitted via `time.monotonic()`.
- Cuando se emiten chunks de stream A, check si
  `time.monotonic() - last_chunk_at[other_stream] < 0.050` — si si,
  prefijar AMBOS chunks (current + recent other-stream).
- Cross-platform behavioral test (`tests/test_subprocess_utils.py::test_origin_disambig_temporal_window`)
  spawns subprocess que emite 1 chunk a stdout + 1 chunk a stderr con
  `time.sleep(0.005)` between (well within 50ms window) y verifica
  prefix appears en ambos. Test passes en Unix + Windows uniformly.
- Window 50ms chosen como balance: short enough que sequential single-stream
  output (e.g., logs scrolling 1+ second apart) NO triggers prefix; large
  enough que platform polling jitter no reverte el detection.

**Escenario O1: solo stdout activo no prefija (feature ON)**

> **Given** `auto_origin_disambiguation=True` (default). Subprocess que
> solo emite a stdout (e.g., normal text output).
> **When** pump reads.
> **Then** lines pass-through sin prefix. `[stdout]` NO aparece. Cero
> overhead para single-stream caso.

**Escenario O2: ambos streams en misma read iteration prefijan**

> **Given** `auto_origin_disambiguation=True`. Subprocess emitiendo a
> ambos stdout + stderr en misma read iteration del pump (e.g., MAGI
> agent escribiendo verdict to stdout y synthesizer writing progress
> to stderr concurrently).
> **When** pump detects ambos streams ready en misma iteration
> (cross-platform: select.select en Unix, selectors.DefaultSelector en
> Windows).
> **Then** lines de stdout prefixed con `[stdout] `, lines de stderr
> prefixed con `[stderr] `. Operator distinguishes origin sin ambiguity.

**Escenario O3: alternating iterations pasan unprefixed**

> **Given** `auto_origin_disambiguation=True`. Subprocess que alterna:
> iter 1 solo stdout, iter 2 solo stderr, iter 3 solo stdout.
> **When** pump processes cada iteration.
> **Then** iterations con single-stream activity NO add prefix. Solo
> iterations con AMBOS streams active simultaneously add prefix. Mantiene
> reading flow natural cuando streams no overlap.

**Escenario O4: feature disabled preserva bytes raw**

> **Given** `plugin.local.md` con `auto_origin_disambiguation: false`
> override (downstream parser depends on raw output).
> **When** subprocess emit ambos streams interleaved.
> **Then** lines pass-through sin prefix bajo cualquier condicion.
> Comportamiento idem v0.4.0 baseline. Operator opt-out preserva
> backward-compat con parsers strict.

### 2.5 v0.4.1 hotfixes folded in

3 doc-alignment items observados en v0.4.0 MAGI iter 1+2 INFO findings:

**Hotfix HF1: recovery breadcrumb wording alignment**

> **Given** Feature F manual synthesis recovery shipped en v0.4.0. Spec
> dice `[sbtdd magi] synthesizer failed; manual synthesis recovery applied
> (N/3 agents)`. CHANGELOG dice cosa parecida. Implementation actual
> emit slightly diferente.
> **When** se inspecciona spec + CHANGELOG.md + impl.
> **Then** los 3 deben tener wording identical character-for-character.
> Specifically: spec-behavior-base.md sec.2.2.4 + CHANGELOG `[0.4.0]` +
> `magi_dispatch._manual_synthesis_recovery` stderr write.

**Hotfix HF2: marker file schema docs**

> **Given** Feature F marker-based discovery shipped en v0.4.0. Marker
> file format documented en spec-base sec.2.2.1. Actual emission code
> escribe ligeramente differente schema.
> **When** se compara spec doc vs actual emission.
> **Then** docs match impl. Specifically: marker JSON contiene fields
> documented (verdict, iteration, agents, retried_agents, timestamp,
> synthesizer_status). Si impl emite mas/menos, docs se actualizan O impl
> se ajusta.

**Hotfix HF3: F45 verdict-set behavior delta documentation**

> **Given** F45 tolerant agent JSON parser shipped en v0.4.0 con behavior
> delta vs strict parser: validates verdict in known set
> (`models.VERDICT_RANK`).
> **When** operador lee CHANGELOG `[0.4.0]` Added section.
> **Then** delta documented explicitly: "Tolerant parser additionally
> validates that the parsed `verdict` field is in the known
> `VERDICT_RANK` set; agent JSON with unknown verdict raises
> ValidationError instead of silently passing through."

### 2.6 Acceptance criteria mapping

| Criterion | Escenarios | Test fixtures |
|-----------|-----------|---------------|
| **Heartbeat emitter** | H1-H6 | `tests/test_heartbeat.py` (NEW) |
| **status --watch** | W1-W6 | `tests/test_status_watch.py` (NEW) |
| **Per-stream timeout** | T1-T8 (incl. INV-34 + allowlist + closed-stream + kill-tree order) | `tests/test_subprocess_utils.py`, `tests/test_config.py` (extended) |
| **Origin disambiguation** | O1-O4 (incl. config gate + 50ms temporal window) | `tests/test_subprocess_utils.py` (extended) |
| **Mechanical smoke fixtures** | R2.3 | `tests/test_heartbeat_smoke.py` (NEW) |
| **v0.4.1 hotfixes** | HF1-HF3 | `tests/test_changelog.py`, `tests/test_skill_md.py` (extended) |

### 2.7 Invariantes resumen pillar observability

- **INV-32 (propuesta)**: heartbeat thread NO debe bloquear ni matar el auto
  run bajo ningun fallo. Implementation: try/except wrap + counter; primer
  fallo single warning a stderr; ticks subsiguientes silent.
  **Incremental persistence (PINNED post-iter 2/3)**: heartbeat thread
  REPORTA cada N=10 incrementos del `_failed_writes` counter al main thread
  via `_heartbeat_failures_q: queue.Queue[int]`. Main thread drena la queue
  en cada `_update_progress()` call y persiste counter a `auto-run.json`
  bajo `heartbeat_failed_writes_total` field. **Single-writer rule**: solo
  main thread toca el archivo (ver sec.3 mutation contract). **Exit-time
  surfacing obligatorio**: `__exit__` envia un valor final del counter a
  la queue + logs summary breadcrumb si `_failed_writes > 0`. Audit trail
  NO depende de stderr funcionando — broken heartbeat surfaces via
  auto-run.json incluso cuando stderr ES el broken pipe.
- **INV-33 (propuesta)**: per-stream timeout es last-resort kill, no first
  resort. Heartbeat (alive signaling) + watch (out-of-band visibility) son
  las primeras lineas de defensa contra "looks dead" UX. Timeout solo
  kicks in cuando subprocess geniunamente esta colgado sin escribir.
- **INV-34 (propuesta)**: relacion timeout-vs-interval + absolute floor + ceiling.
  PluginConfig load valida (4 clauses, cada una con error message distinto):
  - **Clause 1**: `auto_per_stream_timeout_seconds >= 5 * auto_heartbeat_interval_seconds`
    (ratio multiplier).
  - **Clause 2**: `auto_heartbeat_interval_seconds <= 60` (absolute ceiling —
    interval no puede exceder 1 min sin operator awareness loss; PINNED
    post-iter 3 caspar finding).
  - **Clause 3**: `auto_heartbeat_interval_seconds >= 5` (absolute floor —
    sub-5s ticks spam stderr sin valor; testing fixtures override este
    floor via explicit fixture parameter, no via plugin.local.md).
  - **Clause 4** (PINNED post-Checkpoint 2 iter 1 caspar finding):
    `auto_per_stream_timeout_seconds >= 600` (absolute timeout floor —
    incluso con clause 1, interval=15 permite timeout=75s que matar
    caspar opus legitimate runs). 600s = 10min cubre observed worst-case.

  **Validation order PINNED (post Loop 2 v0.5.0 WARNING #1/#7)**: clauses
  son verificadas en orden `4 → 2 → 3 → 1` en `config.py:load_plugin_local`.
  Razon: cheapest single-field absolute-bound checks (clauses 4, 2, 3)
  fire first; the two-field ratio (clause 1) checks last. Bajo este
  ordering una fixture que viola SOLO clause 1 no puede existir porque
  clauses 2 + 4 mathematicamente subsumen clause 1: cualquier
  `timeout >= 600` AND `interval <= 60` implica
  `5 * interval ≤ 300 ≤ 600 ≤ timeout`, satisfaciendo clause 1. Clause 1
  permanece en code como **defense-in-depth** contra futuro weakening de
  clauses 2 o 4. Ver `docs/v0.5.0-config-matrix.md` `### W1` para la
  prueba completa.

  Violation raises `ValidationError` con exit 1. Razon: si timeout fires
  antes del primer heartbeat tick, el operador nunca ve signal de vida y
  el subprocess es killed en silencio. Las 4 clauses combinan: timeout
  in `[600, inf)`, interval in `[5, 60]`, timeout >= 5*interval (always
  true with absolute floors).
- INV-22 (sequential auto) preservado: nada nuevo cambia el sequential
  contract.
- INV-26 (audit trail) extendido: `auto-run.json` ahora SIEMPRE contiene
  `progress` field con ProgressContext snapshot (J6 ya preservaba; v0.5.0
  garantiza que se ESCRIBE en cada transition, no solo opcional).
  Adicionalmente registra `heartbeat_failed_writes_total` per INV-32.

---

## 3. ProgressContext schema contract

Nuevo dataclass en `models.py`, immutable per-snapshot:

```python
@dataclass(frozen=True)
class ProgressContext:
    iter_num: int = 0                  # current MAGI iter or 0 if not in MAGI
    phase: int = 0                     # 1=preflight, 2=task-loop, 3=pre-merge, 4=verify, 5=report
    task_index: int | None = None      # within phase 2 task loop
    task_total: int | None = None      # plan task count
    dispatch_label: str | None = None  # e.g. "magi-loop2-iter2", "loop1-iter1"
    started_at: datetime | None = None # for elapsed calculation; None pre-phase 1
```

**Mutation contract (PINNED — single concurrency model):**

- **Holder location**: module-level singleton reference in
  `scripts/heartbeat.py` (pinned per sec.4.2). Module attr name:
  `_current_progress: ProgressContext`. Adicionalmente: module-level
  `_progress_lock: threading.Lock`.
- **Writer protocol**: `auto_cmd` creates a NEW frozen ProgressContext
  object on each phase/task/dispatch transition. Writer calls
  `set_current_progress(new_ctx)` que adquiere `_progress_lock`,
  asigna `_current_progress = new_ctx`, libera lock. Lock overhead
  negligible (microseconds) y forward-compat con PEP 703 free-threaded
  Python.
- **Reader protocol**: HeartbeatEmitter daemon thread calls
  `get_current_progress() -> ProgressContext`. Getter adquiere
  `_progress_lock`, lee referencia, libera. Reader entonces opera sobre
  el snapshot returned SIN seguir holding el lock; snapshot is immutable
  (`frozen=True` dataclass) — safe para read concurrente sin lock
  adicional.
- **No partial reads possible**: lock-protected get/set guarantees reader
  either sees pre-update reference OR post-update reference. Frozen
  dataclass guarantees no concurrent mutation post-read.
- **Pinned post-iter 2 (caspar PEP 703 finding)**: el lock approach es
  cheap immunization contra futuro free-threaded Python (PEP 703) y
  contra maintainer drift. La iter 1 "atomic pointer no-lock" approach
  funciona en CPython actual pero depende de implementation detail; el
  lock approach es agnostic a memory model.
- **`started_at` semantics (PINNED post-iter 3 + Checkpoint 2 iter 2 caspar findings)**:
  ProgressContext.started_at = **DISPATCH started_at** (timestamp del
  dispatch en curso, no del phase ni del auto run). Razon: heartbeat
  tick muestra `elapsed=` que el operador interpreta como "tiempo del
  dispatch actual"; coincide con esa interpretacion. Phase started_at
  vive en auto-run.json top-level (ya existe, no afectado). Auto run
  started_at vive separado en auto-run.json top-level desde v0.4.0.
  Tres timestamps ortogonales con scopes distintos.
  - **Refresh contract (Checkpoint 2 iter 2 caspar CRITICAL fix):**
    `_set_progress` helper PRESERVES `started_at` cuando el `dispatch_label`
    no cambia entre invocaciones (intra-dispatch update). REFRESHES
    `started_at = now()` SOLO cuando el `dispatch_label` cambia respecto
    al ProgressContext actual O cuando current.started_at era None. Sets
    `started_at = None` cuando `dispatch_label = None` (between-dispatches
    state). Este contrato hace el `elapsed=` heartbeat tick monotonic
    dentro de un mismo dispatch sin importar cuantas veces se llame
    `_set_progress` con la misma label.
- **`started_at` serialization format (PINNED post-iter 3 melchior finding)**:
  ISO 8601 UTC con sufijo `Z`, e.g., `"2026-05-01T12:34:56Z"`. Igual
  que existing `started_at` field en auto-run.json top-level (preserva
  consistency cross-field). datetime serializada via
  `.isoformat(timespec='seconds') + 'Z'` cuando UTC; `.astimezone(timezone.utc)`
  precede serialization si datetime tiene tzinfo distinto.
- **Single-writer rule auto-run.json (PINNED post-iter 3 melchior+caspar finding)**:
  SOLO el main thread (auto_cmd) escribe a `auto-run.json`. Heartbeat
  thread reporta `_failed_writes` counter al main thread via
  thread-safe Queue (`_heartbeat_failures_q: queue.Queue[int]`). Main
  thread drena la queue en cada `_update_progress()` call y serializa
  el counter al JSON. NO race condition porque heartbeat thread NO toca
  el archivo directamente. Esta arquitectura preserva el J6 atomic
  rename pattern + protege contra concurrent file writes.
- **Explicit transition list (writer call sites)**: auto_cmd MUST update
  `_current_progress` at exactly these transitions:
  1. Start of phase 1 (pre-flight check).
  2. Start of phase 2 (task loop entry).
  3. Each task index advance within phase 2.
  4. Start of each dispatch within a task (Red / Green / Refactor TDD;
     spec-reviewer; code-review).
  5. Start of phase 3 (pre-merge entry).
  6. Each MAGI Loop 2 iter advance within phase 3.
  7. Each dispatch within phase 3 (Loop 1 review, Loop 2 MAGI, mini-cycle
     fix dispatches).
  8. Start of phase 4 (verify).
  9. Start of phase 5 (report).
  10. End-of-phase final updates (set dispatch_label=None when between
      dispatches).

  Subagent #1 implementer must enumerate these 10 call sites in
  `auto_cmd.py` to avoid drift between spec and impl.

**Serialization to auto-run.json:** `auto-run.json` gains/extends `progress`
key under top-level (J6 already preserved field; v0.5.0 ensures every
transition writes it):

```json
{
  "started_at": "2026-05-01T12:00:00Z",
  "progress": {
    "iter_num": 2,
    "phase": 3,
    "task_index": 14,
    "task_total": 36,
    "dispatch_label": "magi-loop2-iter2",
    "started_at": "2026-05-01T12:34:56Z"
  },
  "...other audit fields..."
}
```

**Backward compat:** `auto-run.json` files de v0.4.0 sin `progress` field
siguen parsable; D4.3 absent-tolerant downstream preservado. Si watch lee
v0.4.0 file sin progress, render minimal "alive: <elapsed>" without
phase/task/dispatch fields.

---

## 4. Subagent layout (parallel 2-subagent, surfaces disjoint)

### 4.1 Pre-arranque

**Orchestrator escribe contrato `ProgressContext` schema EN ESTE SPEC**
(sec.3) antes de dispatch. Ambos subagents implementan contra el contrato,
sin code dependency runtime.

### 4.2 Subagent #1 — Heartbeat track

- Files: `models.py` (+ProgressContext dataclass), new
  `scripts/heartbeat.py` (HeartbeatEmitter context manager + daemon
  thread loop + module-level `_current_progress` singleton + `get_current_progress()`
  getter — sibling module to `subprocess_utils.py`, NO directory rename),
  `auto_cmd.py` (+ProgressContext write hooks on the 10 explicit transitions
  enumerated in sec.3 + HeartbeatEmitter wraps long dispatches +
  `heartbeat_failed_writes_total` field in auto-run.json audit).
- Tests: `tests/test_heartbeat.py` (NEW, escenarios H1-H6),
  `tests/test_models.py` (extended for ProgressContext immutability +
  serialize/deserialize), `tests/test_auto_progress.py` (extended for
  ProgressContext written to auto-run.json on each of 10 transitions +
  heartbeat_failed_writes_total preserved).
- TDD-Guard: ON.
- Forbidden: `status_cmd.py`, streaming pump in `subprocess_utils.py`,
  CHANGELOG.md, SKILL.md.

### 4.3 Subagent #2 — Streaming + watch + docs track

- Files: `subprocess_utils.py` streaming pump (J3 per-stream timeout +
  J7 origin disambiguation extensions), `status_cmd.py` (--watch + helpers
  with 5x exponential-backoff JSON retry per W4),
  `run_sbtdd.py` (subcommand argv extensions: --watch, --interval, --json),
  `config.py` (+5 nuevos campos: `auto_per_stream_timeout_seconds: int = 900`,
  `auto_heartbeat_interval_seconds: int = 15`,
  `status_watch_default_interval_seconds: float = 1.0`,
  `auto_origin_disambiguation: bool = True`,
  `auto_no_timeout_dispatch_labels: list[str] = field(default_factory=lambda: ["magi-*"])`;
  PLUS validation `auto_per_stream_timeout_seconds >= 5 * auto_heartbeat_interval_seconds`
  per INV-34, raises ValidationError on violation),
  CHANGELOG.md (v0.4.1 hotfix sections + `[0.5.0]`), SKILL.md (--watch docs +
  v0.4.1 corrections), CLAUDE.md (release notes pointer for v0.5.0),
  new `docs/v0.5.0-config-matrix.md` (field/invariant matrix per R9 mitigation:
  tabla unica con default + validation + docs locations + CHANGELOG line por
  cada uno de los 5 config fields y 3 invariantes).
- Tests: `tests/test_status_watch.py` (NEW, escenarios W1-W6),
  `tests/test_subprocess_utils.py` (extended escenarios T1-T4, O1-O4),
  `tests/test_config.py` (extended for 5 new fields + INV-34 validation
  + `test_inv34_violation_examples` enumerating pathological combinations),
  `tests/test_changelog.py` (extended HF1-HF3 docs alignment),
  `tests/test_skill_md.py` (extended HF1-HF3).
- TDD-Guard: ON.
- Forbidden: `models.py`, `auto_cmd.py`, `scripts/heartbeat.py`.

### 4.4 Conflict surface analysis

`subprocess_utils.py` is NOT a shared touchpoint:
- Subagent #1 puts heartbeat en archivo NEW: `scripts/heartbeat.py`
  (sibling module to `subprocess_utils.py`, NOT a sub-directory). Cero
  touch al `subprocess_utils.py` existing.
- Subagent #2 modifies streaming pump in existing `subprocess_utils.py`.
  Cero touch al `scripts/heartbeat.py` module.

Cero overlap. True parallel dispatch (single-message 2 Agent tool calls)
viable, repeating v0.4.0 pattern.

`config.py` is NOT a shared touchpoint either: only Subagent #2 touches it
(adding 5 new fields + INV-34 validation). Subagent #1 reads PluginConfig
fields via existing API, doesn't modify the file.

### 4.5 Coordination

Both subagents commit a `main` directly (lightweight pattern, no feature
branch). Orchestrator dispatches paralelo en single message, espera DONE
de ambos, then drives final review.

---

## 5. Final review loop

### 5.1 Scope identico v0.4.0

MAGI -> /receiving-code-review loop hasta exit criterion (verdict
`GO_WITH_CAVEATS` full + 0 CRITICAL + 0 WARNING + 0 Conditions for
Approval), cap 5 iter.

### 5.2 Dogfood pattern + mechanical validation (NF-F two-track)

**Recursive payoff oportunity** (track A: opportunistic): este ciclo ships
heartbeat + status --watch. Iter 1 final review NO los tendra activos
(pre-commit-of-features). Iter 2+ SI los tendra (post commits de subagent
#1 y #2). Validacion empirica EN VIVO durante el ciclo de ship.

**Mechanical validation** (track B: deterministic, OBLIGATORIO post-MAGI iter 1):
addressing R6 caspar finding (recursive dogfood blind spot — circular
dependency on the feature being validated). Track B se ejecuta independiente
de cualquier MAGI iter, durante phase 2 (`make verify` post-merge):

- **Sleep fixture test (PINNED post-iter 2 — protect NF-A budget):**
  `tests/test_heartbeat_smoke.py` (NEW) corre un HeartbeatEmitter
  configurado con `auto_heartbeat_interval_seconds=0.5` (sub-second
  override via test fixture) wrapping `time.sleep(2.5)` (5 ticks @ 0.5s
  interval = 2.5s wall time total). Test consume <3s del 90s budget en
  vez de los 45s problematicos del iter 1 design. Verifica via captured
  stderr que SE EMITIERON 4-5 ticks esperados con format correcto.
  Independent de MAGI dispatch.
  - **Alternativa monkey-patched clock**: si el sub-second cadence introduces
    timing flakiness en CI, fallback es monkey-patch `time.monotonic` con
    fake clock advancing 15s per "tick" — wall time remains <0.1s.
    Implementation Subagent #1 chooses based on flakiness empirics.
- **Watch smoke fixture**: `tests/test_status_watch.py` corre poll loop
  contra fixture `auto-run.json` con simulated transitions, verifica
  TTY render OR JSON output deterministic. Tambien sub-second polling
  via fixture override (`status_watch_default_interval_seconds=0.1`).

**Escenario R2.1: heartbeat dogfood en iter 2+ rescata UX during long MAGI**
*(track A — opportunistic, supplementary to mechanical)*

> **Given** v0.5.0 final review iter 2. Subagent #1's heartbeat shipped
> earlier in cycle. MAGI Loop 2 dispatch tarda ~5 min (caspar opus full
> review).
> **When** orchestrator wraps the MAGI dispatch en HeartbeatEmitter context
> manager.
> **Then** stderr emite tick cada 15s. Operador no ve "looks dead".
> Empirical UX confirmation in production-like conditions. NO es la
> validation principal — track B mechanical sleep fixture es authoritative.

**Escenario R2.2: status --watch dogfood en iter 2+ from second terminal**
*(track A — opportunistic)*

> **Given** v0.5.0 final review iter 2. Subagent #2's status --watch shipped.
> **When** operador desde otra terminal corre
> `python run_sbtdd.py status --watch`.
> **Then** TTY rewrite-line render muestra iter / phase / dispatch /
> elapsed live. Empirical UX confirmation; track B (mechanical poll loop
> against fixture) is authoritative.

**Escenario R2.3: mechanical heartbeat smoke fixture validates feature**
*(track B — deterministic, OBLIGATORIO; PINNED post-iter 2 NF-A budget)*

> **Given** Subagent #1 ships HeartbeatEmitter + ProgressContext. Phase 2
> `make verify` runs.
> **When** `tests/test_heartbeat_smoke.py::test_emitter_emits_ticks` corre
> con HeartbeatEmitter configurado en sub-second interval (0.5s) wrapping
> `time.sleep(2.5)` — total wall time <3s del 90s budget.
> **Then** captured stderr contiene 4-5 lineas matching tick format
> `[sbtdd auto] tick: ... elapsed=0m0s`, `...elapsed=0m1s`, `...elapsed=0m1s`,
> `...elapsed=0m2s`, `...elapsed=0m2s` (plus or minus 1 line for timing
> edges). Test passes deterministically without depending on MAGI dispatch.
> Feature validated as mechanical requirement.

### 5.3 Other escenarios (R1.x identical to v0.4.0 spec)

R1.1-R1.7 from v0.4.0 spec apply identically:
- R1.1 exit on GO_WITH_CAVEATS clean.
- R1.2 continue on CRITICAL findings.
- R1.3 continue on WARNING findings or Conditions.
- R1.4 continue on degraded MAGI (INV-28).
- R1.5 cap 5 iter -> escalation_prompt.
- R1.6 rejected findings feed iter+1 context.
- R1.7 Loop 1 surrogate via `make verify`.

Plus newly-applicable v0.5.0:
- **R1.8** Cross-check MAGI verdict via `docs/magi-gate-template.md` —
  even though Feature G (formal cross-check via /requesting-code-review)
  defers a v1.0.0, the template's verdict action table provides operator
  guidance for ambiguous verdicts.

### 5.4 Invariantes final review

- INV-9, INV-11, INV-28, INV-29 preservados sin cambio.
- F's auto-recovery (v0.4.0 shipped) sigue activo si MAGI synthesizer crash
  with >= 1 agent succeeded.
- v0.5.0 heartbeat + status --watch are PRESENT durante final review iter
  2+; recursive payoff R2.1, R2.2.

---

## 6. Subagent layout + execution timeline

### 6.1 Layout (parallel — surfaces 100% disjoint)

| Phase | Duracion proyectada | Subagents | Output |
|-------|--------------------|-----------|--------|
| 0. Spec + brainstorming + spec-behavior.md | DONE | -- | esta seccion |
| 1. Subagent #1 (Heartbeat) | ~3-4h | parallel | 6-9 atomic commits |
| 1. Subagent #2 (Streaming + watch + docs) | ~3-4h | parallel | 6-9 atomic commits |
| 2. `make verify` post-merge + mechanical smoke fixtures | ~10min | -- | 4 checks clean + heartbeat/watch fixtures pass |
| 3. Final review loop MAGI -> /receiving-code-review | 1-2h | -- | 1-3 iter expected |
| 4. Version bump + tag + push | ~10min | -- | 0.4.0 -> 0.5.0 |
| **Total wall time** | **~6-8h** | -- | -- |

**Padding rationale (post-MAGI Checkpoint 2 review v0.5.0 iter 1):**
estimate elevado de 4-5h a 6-8h para cubrir threading edge cases (daemon
thread join hygiene, race avoidance via reference-swap), TTY render
testing on multiple terminals, Windows-specific AV-related JSON race
retries (5x exponential backoff implementation), config validation
implementation (INV-34 timeout-vs-interval), mechanical smoke fixtures
(track B sec.5.2). Bundle width acknowledged: 4 deliverables + 3 hotfixes +
5 nuevos config fields + 3 nuevos invariantes (INV-32, INV-33, INV-34
con 4 clauses) — 50-100% padding sobre v0.4.0 baseline cycle.

### 6.2 True parallel dispatch

Pattern repetido de v0.4.0 (validated): single message, two Agent tool
calls. Surfaces 100% disjoint per sec.4.4 — zero merge conflict risk.

### 6.3 Final review loop dispatch (orchestrator)

Mismo pattern v0.4.0:
1. `make verify` clean (Loop 1 surrogate).
2. Compute diff range (HEAD_pre_v050..HEAD).
3. Iter 1: invoke `/magi:magi` con prompt referencing spec + plan + diff.
   Si synthesizer crashes -> use F's `_manual_synthesis_recovery`
   (escenario R2.1 from v0.4.0 spec, F shipped en v0.4.0).
4. Parse verdict + findings. Eval exit criterion.
5. Si NO exit: route findings via /receiving-code-review (INV-29) +
   mini-cycle TDD per accepted finding. Re-invoke MAGI iter+1.
6. Cap 5 iter; exhausted -> escalation_prompt with template's verdict
   action table guidance.

---

## 7. Version + distribution

### 7.1 Bump

`plugin.json` + `marketplace.json`: 0.4.0 -> 0.5.0 (MINOR).

Justificacion MINOR (no MAJOR): aditivo puro. New helpers (HeartbeatEmitter,
ProgressContext, status --watch subcommand). Existing flows unchanged
backward-compat (auto-run.json field optional, default values for new
PluginConfig fields). Per-stream timeout default 900s + `magi-*` dispatch
label allowlist (per sec.2.3 final decision post-iter 2 review) — mas
restrictivo que el v0.4.0 baseline (que no tenia timeout) pero balanceado:
catches genuine hangs sin matar dispatches caspar opus que escriben a
.raw.json files antes que stdout/stderr.

### 7.2 CHANGELOG.md `[0.5.0]` sections

- **Added** — Heartbeat in-band emitter, `/sbtdd status --watch` subcommand,
  per-stream timeout (J3), origin disambiguation (J7), ProgressContext
  dataclass + `get_current_progress()` getter en `scripts/heartbeat.py`,
  **5 new PluginConfig fields** (`auto_per_stream_timeout_seconds`,
  `auto_heartbeat_interval_seconds`, `status_watch_default_interval_seconds`,
  `auto_origin_disambiguation`, `auto_no_timeout_dispatch_labels`), **3 new
  invariants** (INV-32 heartbeat resilience + queue persistence; INV-33
  timeout last-resort; INV-34 timeout-vs-interval 4-clause validation).
- **Changed** — `auto-run.json` schema gains `progress` field (J6 already
  preserved; v0.5.0 garantiza emission on every transition).
- **Hotfixes folded** — recovery breadcrumb wording alignment, marker file
  schema docs, F45 verdict-set delta docs.
- **Process notes** — true parallel 2-subagent dispatch repeated. Recursive
  payoff: heartbeat + status --watch dogfooded en own cycle iter 2+.
  Loop 1 surrogate via `make verify`.
- **Deferred (rolled to v1.0.0)** — Feature G (cross-check), F44.3
  (retried_agents propagation to auto-run.json), J2 (ResolvedModels), I
  (schema_version), H Group B options 2+5, INV-31 default decision.

### 7.3 README + SKILL.md + CLAUDE.md

- **README:** mini-section "Observability" documentando heartbeat + watch
  user-facing benefit. Cross-reference to `docs/magi-gate-template.md` for
  cross-project applicability.
- **SKILL.md:** `### v0.5 notes` section docs --watch + heartbeat.
  Hotfix HF1 corrections inline.
- **CLAUDE.md (proyecto):** v0.5.0 release notes pointer.

---

## 8. Risk register v0.5.0

- **R1**. Heartbeat thread races con auto_cmd ProgressContext writes —
  mitigation: immutable replacement pattern (whole new ProgressContext per
  transition, reference swap atomic in Python). Lock fallback if needed.
- **R2**. Per-stream timeout false positive (kills healthy slow subprocess)
  — mitigation: default 900s post-MAGI iter 2 review (consolidated balance
  entre iter 1 caspar finding "600s mata caspar runs >10min" y iter 2
  melchior+balthasar pushback "1800s demasiado generoso"); allowlist
  `auto_no_timeout_dispatch_labels: ["magi-*"]` exempts MAGI dispatches
  por completo (silent durante opus eval is legitimate); INV-34 validation
  prevents pathological combinations con heartbeat_interval; "all-streams
  silent" semantics preserve subprocesses con asymmetric stream usage.
- **R3**. Origin disambiguation prefix breaks downstream parsers que esperan
  raw subprocess output — mitigation: prefix only when BOTH streams active
  in same window; passthrough cuando single stream.
- **R4**. status --watch JSON parse race during atomic-write window —
  mitigation: 5x exponential backoff (50/100/200/400/500ms cap = 1.25s
  total budget) covers Windows os.replace + AV scanner hold cases (post-iter 2
  caspar finding). On exhaustion, emit visible `contention:` breadcrumb to
  stderr with cumulative counter (NOT silent), skip render cycle. AV storm
  sustained surface to operator.
- **R5**. Subagent #1 + #2 timing variance: si #1 finishes mucho mas tarde
  que #2, el dogfood R2.1 (heartbeat in iter 2+) is delayed -- mitigation:
  orchestrator waits for both DONE before final review starts; both feature
  sets LANDED before iter 1 invocation.
- **R6**. Caspar fragility cronica (5to ciclo consecutivo posible) —
  mitigation: F's auto manual-synthesis recovery shipped en v0.4.0; v0.5.0
  heartbeat ADDITIONALLY shows operator EN VIVO si caspar specifically esta
  colgado vs otros agents progressing.
- **R7**. Bundle aditivo pero amplio (4 deliverables + 3 hotfixes + 5
  config fields + 3 invariantes propuestos) — MAGI Checkpoint 2 verdict
  difficulty similar a v0.4.0 (que was 8 deliverables).
  Mitigation: surfaces 100% disjoint reduces review friction; templated
  patterns (HeartbeatEmitter context manager, status --watch poll loop)
  son standard idioms.
- **R8**. Bundle width carries non-trivial maintenance cost despite
  disjoint surfaces (post-iter 2 balthasar finding) — 5 nuevos config
  fields + 3 invariantes son superficie ongoing-maintenance. Mitigation:
  templates en estandar idioms (Event.wait, threading.Lock,
  context manager) reducen surprise; cada campo tiene default y
  validation upfront, evitando "configurable to invalid combinations"
  drift class.
- **R9**. Doc-drift recurrence (post-iter 3 balthasar finding) — HF1-HF3
  hotfixes en v0.5.0 fueron caused exactly por config/invariant drift en
  v0.4.0. Adding 5 fields + 3 invariantes en una bump amplifica risk.
  Mitigation: Subagent #2 produces ship-time **field/invariant matrix**
  como deliverable adicional (`docs/v0.5.0-config-matrix.md`) cubriendo
  default + validation + docs locations + CHANGELOG line para cada uno
  de los 5 fields y 3 invariantes. Single-source matrix forces consistency
  cross-doc.

---

## 9. Acceptance criteria final v0.5.0

v0.5.0 ship-ready cuando:

### 9.1 Functional (Pillar observability)

- **F1**. Heartbeat in-band emitter — H1-H6 escenarios pass.
- **F2**. `/sbtdd status --watch` — W1-W6 escenarios pass.
- **F3**. Per-stream timeout (J3) — T1-T8 escenarios pass (incl. INV-34
  validation in PluginConfig + `auto_no_timeout_dispatch_labels` allowlist
  exempt para `magi-*` + closed-stream EOF tracking exemption + Windows
  kill-tree R3-1 order preservation).
- **F4**. Origin disambiguation (J7) — O1-O4 escenarios pass (incl.
  `auto_origin_disambiguation` config gate + 50ms temporal window
  cross-platform behavioral test).
- **F5**. ProgressContext dataclass + auto-run.json contract — backward
  compat con v0.4.0 files preserved; `heartbeat_failed_writes_total`
  field registrado per INV-32.
- **F6**. Mechanical smoke fixtures (R2.3) — `tests/test_heartbeat_smoke.py`
  pass deterministically, independent de MAGI dispatch.

### 9.2 Functional (v0.4.1 hotfixes folded)

- **HF1**. Recovery breadcrumb wording alignment — spec/CHANGELOG/impl
  match character-for-character.
- **HF2**. Marker file schema docs match impl emission.
- **HF3**. F45 verdict-set delta documented in CHANGELOG.

### 9.3 No-functional

- **NF-A**. `make verify` clean: pytest + ruff check + ruff format + mypy
  --strict, runtime <= 90s.
- **NF-B**. Tests totales >= 818 baseline + nuevos = 848-858 estimado.
- **NF-C**. Cross-platform.
- **NF-D**. Author/Version/Date headers en nuevos `.py` files (heartbeat.py).
- **NF-E**. Zero modificacion a modulos frozen excepto los enumerados
  explicitamente en sec.4.2 / 4.3.
- **NF-F**. UX validated via two-track approach (sec.5.2):
  - **Track B (mechanical, OBLIGATORIO)**: `tests/test_heartbeat_smoke.py`
    sleep fixture verifies tick emission deterministically. Independent
    de MAGI dispatch.
  - **Track A (empirical, supplementary)**: long MAGI dispatches en iter
    2+ emit heartbeat ticks visible al operador (R2.1). Confirma UX en
    production-like conditions; NO authoritative.

### 9.4 Process

- **P1**. MAGI Checkpoint 2 verdict >= `GO_WITH_CAVEATS` full per INV-28.
  Iter budget 3 + INV-0 override available.
- **P2**. Pre-merge Loop 1 clean-to-go (via `make verify` surrogate) +
  Loop 2 MAGI verdict >= `GO_WITH_CAVEATS` full.
- **P3**. CHANGELOG.md `[0.5.0]` entry escrita con secciones de sec.7.2.
- **P4**. Version bump 0.4.0 -> 0.5.0 sync `plugin.json` +
  `marketplace.json`.
- **P5**. Tag `v0.5.0` + push (con autorizacion explicita user).

### 9.5 Distribution

- **D1**. Plugin instalable via `/plugin marketplace add ...` +
  `/plugin install ...`.
- **D2**. Cross-artifact coherence tests actualizados.
- **D3**. Nuevos subcomandos / flags documentados en README + SKILL.md +
  CLAUDE.md.

---

## 10. Referencias

- Spec base post-v0.3.0: `sbtdd/spec-behavior-base.md` (v1.0.0 raw input;
  v0.5.0 cubre el split observability subset).
- Contrato autoritativo v0.1+v0.2+v0.3+v0.4 frozen:
  `sbtdd/sbtdd-workflow-plugin-spec-base.md`.
- Brainstorming session decisions log v0.5.0:
  - Q1 = B (1.0 es siguiente milestone, BREAKINGs OK).
  - Q2 = C (large bundle, all LOCKED minus INV-31 default flip).
  - Q3 = C (heartbeat in-band + status --watch out-of-band).
  - Q4 = C (heartbeat content: liveness + dispatch + macro progress).
  - Approach C: split en v0.5.0 (observability) + v1.0.0 (semantic
    features).
- v0.4.0 ship + empirical findings:
  - `memory/project_v040_shipped.md` (v0.4.0 ship record).
  - Caspar fragility cronica observada en 4 ciclos consecutivos.
- Cross-project alignment (just shipped commit `b4a37d6`):
  - `docs/magi-gate-template.md` — canonical template, 10 sub-sections
    + per-project setup + provenance.
  - `docs/cross-project/2026-05-01-magi-claude-local-patch.md` — patch
    artifact for MAGI plugin's `CLAUDE.local.md` §2.
  - `CLAUDE.local.md` §6 — 5 nuevas sub-sections absorbidas (gitignored,
    local persistent).
- Historical precedent:
  - v0.2.1 lightweight pattern (~3h, 4 LOCKED items).
  - v0.3.0 lightweight + sequential 2 subagents (~5h).
  - v0.4.0 lightweight + true parallel 2 subagents (~4-5h, surfaces
    disjoint).
- v1.0.0 deferred items roadmap:
  - Feature G (`memory/project_v100_magi_cross_check.md`).
  - Feature H Group B re-eval + INV-31 default.
  - Feature I schema_version + migrate skeleton.
  - F44.3 retried_agents propagation.
  - J2 ResolvedModels preflight.
- Branch: trabajo en `main` directamente (lightweight pattern, no feature
  branch).

---

## 11. Known Limitations (post-iter 4 acceptance)

**Status:** spec acceptado por user 2026-05-01 con verdict `GO WITH CAVEATS
(3-0)` full no-degraded en iter 4. **INV-0 override authorization explicit
del user** para skip-additional-iter despues de pattern de convergencia
observado: 4 iters consecutivos al threshold, ~10-13 new findings cada iter,
arquitectura consistently approved por 3 agents, findings de spec precision
y doc consistency en lugar de defectos arquitecturales. Analogo al precedent
v0.4.0 manual synthesis acceptance ("solo esta vez").

Las siguientes findings de iter 4 quedan documentadas como Known Limitations
para que Subagent #1 / #2 las resuelvan durante implementation phase, NOT
diferidas a v0.5.x patches (excepto donde explicitly indicado).

### 11.1 To resolve durante Subagent implementation

**CRITICAL #1: H3 vs single-writer rule wording contradiction (caspar iter 4)**
- Issue: H3 escenario describes heartbeat thread "calling
  `auto_cmd._update_heartbeat_failed_writes`" — sounds like direct write.
  Sec.3 PINNED single-writer rule says heartbeat thread reports via Queue,
  main thread writes.
- Resolution path: Subagent #1 implements per sec.3 single-writer rule
  (Queue-based reporting). H3 wording is descriptive of the OUTCOME, not
  prescriptive of mechanism — the actual code reflects sec.3.

**W1 / W7: INV-34 four-clause validation needs split error messages + worked examples (melchior + balthasar)**
- Issue: T4 escenario tests one violation; INV-34 has 4 clauses (post-Checkpoint 2 iter 1 caspar finding added clause 4 absolute timeout floor).
- Resolution path: Subagent #2 implements PluginConfig validation con 3
  separate `if` predicates + 3 distinct ValidationError messages naming the
  violated clause. R9 matrix deliverable (`docs/v0.5.0-config-matrix.md`)
  includes worked example per clause.

**W2 / W6: 50ms temporal window CI flakiness (melchior + balthasar)**
- Issue: 50ms window risks platform-jitter false positives en Windows CI.
- Resolution path: Subagent #2 implements origin disambig test with
  fixture-injectable window override (default 50ms wall-clock; tests
  override to monkey-patched clock or larger window).

**W3: `_failed_writes` queue drain semantics (melchior)**
- Issue: queue.Queue drain pattern not specified — max? sum? latest?
- Resolution path: Subagent #1 pins drain to `max()` semantics — counter is
  monotonically non-decreasing, latest value reflects total. Documented in
  heartbeat.py module docstring.

**W8: Counter persistence latency unbounded (caspar)**
- Issue: heartbeat reports to queue, main drains on `_update_progress`. If
  transitions infrequent (5+ min apart), counter sits in queue.
- Resolution path: Subagent #1 adds periodic queue drain in main loop —
  even without phase/task transition, main thread drains queue every
  `_progress_drain_interval_seconds` (new const, default 30s) and writes
  counter to auto-run.json if delta vs last persisted.

**W9: Origin disambig retroactive-prefix semantics (caspar)**
- Issue: when pump prefixes a chunk because both streams active in window,
  what about chunks already emitted earlier in same window?
- Resolution path: PINNED forward-only — chunks already emitted are NOT
  retroactively prefixed. Pump tracks `_window_starts_at` per window; only
  chunks emitted AFTER window detected dual-stream activity get prefix.
  First chunk of a dual-stream window may be unprefixed (acceptable
  precision tradeoff vs buffering complexity).

**W10: R1 mitigation contradicts sec.3 PINNED concurrency model (caspar)**
- Issue: Risk register R1 still mentions "immutable replacement pattern"
  from iter 1 design.
- Resolution path: trivial spec text update — Subagent #2 updates R1
  mitigation text in CHANGELOG `[0.5.0]` Process notes section to reference
  lock-protected approach. Inline fix during CHANGELOG composition.

**W11: Allowlist glob no protection against trivial wildcards (caspar)**
- Issue: `auto_no_timeout_dispatch_labels: ["*"]` exempts everything — defeats timeout.
- Resolution path: Subagent #2 implements `PluginConfig` validation
  rejecting bare `"*"` o lista vacia con valido `"*"` solo. Acceptable
  globs include `"magi-*"`, `"specific-name"`. Validation message:
  `"auto_no_timeout_dispatch_labels: bare '*' rejected (would defeat
  timeout); use specific glob"`.

**W12: W4 slow-poll counter reset semantics (caspar)**
- Issue: counter resets on "next render succeeds" but entry condition is
  "3 consecutive failures". Asymmetric.
- Resolution path: PINNED — counter resets on FIRST successful render
  after fallback active (asymmetric is intentional: enter slowly to avoid
  false positives, exit quickly to restore responsiveness).

### 11.2 Deferred to v0.5.x patches (per Balthasar option scope trim)

**W5: Per-stream timeout default-on contradicts INV-33 framing (balthasar)**
- Issue: INV-33 says "timeout is last resort"; default-on contradicts.
- Decision: REPHRASE INV-33 wording (NOT flip default). Heartbeat is
  first-line UX, watch is second-line monitoring, timeout is third-line
  failsafe. All three are default-on; "last resort" means "operator
  intervention is the truly-last; timeout precedes that". Subagent #2
  rephrases INV-33 in spec sec.2.7 + matrix.

**W4 / R8 / R9: Bundle width long-tail maintenance cost (balthasar across iters)**
- Issue: 5 config fields + 3 invariants is wide ongoing-maintenance.
- Decision: ACCEPTED — R8/R9 mitigations (templated idioms + R9 single-source
  matrix deliverable) are the response. Balthasar iter 4 scope-trim option
  (split J3+J7 to v0.5.1) NOT taken — full bundle ships as planned.

### 11.3 INFO findings (8 total)

INFO findings de iter 4 son polish / acknowledgments. Resolution durante
implementation per agent recommendation; no separate spec edits needed.

### 11.4 INV-0 override authorization audit trail

User explicitly authorized acceptance at iter 4 via session 2026-05-01,
preceded by 3-iter cap escalation prompt mostrando opciones (1) iter 4
override / (2) accept / (3) pause / (4) scope trim. User chose (2). Pattern
of convergence (verdict stable at threshold across 4 iters, findings
character refining-not-architecturing) supports the authorization.

This authorization applies SOLO to esta spec (v0.5.0 BDD overlay). Future
specs default a strict iter cap=3 escalation per CLAUDE.local.md §6 sin
override implicit.
