# Plan — v1.0.7 A3 parallel e2e dogfood (synthetic 4-task fixture)

> Generado 2026-05-09. Synthetic plan referenced by
> `tests/test_auto_parallel_e2e.py` as the staged
> `planning/claude-plan-tdd.md` for the v1.0.7 A3 dogfood fixture.
>
> 4 disjoint tasks, each touching a different file under
> `scratch/`. No `Depends on`. partition_by_tracks should produce
> 4 separate tracks (one per task) so the parallel dispatcher fans
> out to multiple workers.

### Task 1: Create scratch alpha

**Files:**
- Create: `scratch/alpha.txt`

Write a one-line file at `scratch/alpha.txt` containing the text
``alpha`` so the close-phase chain has a tangible diff to commit.

### Task 2: Create scratch beta

**Files:**
- Create: `scratch/beta.txt`

Write a one-line file at `scratch/beta.txt` containing the text
``beta``.

### Task 3: Create scratch gamma

**Files:**
- Create: `scratch/gamma.txt`

Write a one-line file at `scratch/gamma.txt` containing the text
``gamma``.

### Task 4: Create scratch delta

**Files:**
- Create: `scratch/delta.txt`

Write a one-line file at `scratch/delta.txt` containing the text
``delta``.
