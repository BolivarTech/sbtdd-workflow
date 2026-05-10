# Synthetic spec — v1.0.7 A3 parallel e2e dogfood fixture

> Generado 2026-05-09. Synthetic spec used by
> `tests/test_auto_parallel_e2e.py` to exercise `auto --parallel`
> end-to-end on Windows. Validates that v1.0.7 Pillar A (A1 POSIX
> PTY allocation + A2 Windows hybrid Option B-W3 fallback) closes
> the chicken-and-egg surface empirically confirmed in v1.0.6
> own-cycle dogfood.
>
> NOT a real feature — synthetic 4-task plan with disjoint scratch
> file surfaces designed to partition into multiple tracks for the
> parallel dispatcher.
>
> INV-27 compliant: cero matches uppercase placeholder word-boundary.

## 1. Objetivo

Provide an empirically-runnable fixture exercising the production
`--parallel` worker-spawn + close-phase + sidecar chain so the test
asserts no subprocess hang on
`/verification-before-completion` (or its v1.0.7 A2 worker-mode
shell-direct equivalent).

## 2. Alcance

- 4 disjoint scratch tasks, each touching a single file under
  `scratch/`.
- Plan partitions into 2-4 tracks via `partition_by_tracks` (no
  shared file surfaces, no `Depends on`).
- Each task runs full TDD cycle Red+Green+Refactor (3 phases) so
  close-phase fires its sec.0.1 chain (worker mode on Windows;
  PTY-bridged skill on POSIX).

## 3. Restricciones

- Stack Python (sec.0.1 chain = pytest + ruff + mypy).
- All fixture files cross-platform.
- No external dependencies beyond stdlib + the dev deps already in
  `pyproject.toml` (pytest, ruff, mypy).

## 4. Criterio de exito

- All 4 tasks complete via `auto --parallel` workers.
- `.claude/auto-run.json` populated with start_time + worker entries.
- Plan checkboxes all flipped to `[x]`.
- `.claude/session-state.json` `current_phase == "done"`.
- `.claude/auto-run-workers/` contains sidecars per worker pid.
- No subprocess hang within 600s test timeout.
