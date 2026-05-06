# v1.0.2 Cross-check Completion + Own-cycle Dogfood Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.0.2 — close the 4 LOCKED items rolled forward from the v1.0.1 pivot (cross-check telemetry, diff threading regression test, spec_lint enforcement, own-cycle dogfood) plus 3 defensive items (recovery empirical, meta-test, coverage threshold). 5 plan tasks (A, B, C, F, G) over 2 parallel subagent tracks; 2 methodology activities (D, E) executed by the orchestrator.

**Architecture:** 2-track parallel dispatch with disjoint surfaces. Track Alpha (`scripts/cross_check_telemetry.py` + `tests/test_pre_merge_cross_check.py` extension) is independent of Track Beta (`skills/sbtdd/scripts/spec_lint.py` + `spec_cmd.py` extension + `tests/test_invoke_skill_callsites_audit.py` + `pyproject.toml` + `Makefile`). Item D (own-cycle dogfood with `magi_cross_check: true`) and Item E (`/sbtdd spec --resume-from-magi` exercise) run mid-cycle in the orchestrator session after both tracks close, before pre-merge gate.

**Tech Stack:** Python >= 3.9, pytest, ruff, mypy --strict, pytest-cov (new dev dep), stdlib-only on hot paths. TDD-Guard active. Brainstorming refinements 2026-05-06: Q1 = 2-track parallel; Q2 = D+E methodology not plan task; Q3 = `spec_lint` R3 severity = warning initial; Q4 = coverage threshold = `floor(baseline) - 2%` measured at task close.

**Plan invariants** (cross-task contracts):

- Every commit follows `~/.claude/CLAUDE.md` Git rules: English only, no AI references, no `Co-Authored-By` lines, atomic, prefix from sec.5 of `CLAUDE.local.md` (`test:` / `feat:` / `fix:` / `refactor:` / `chore:`).
- Every phase close runs `/verification-before-completion` (sec.0.1: `pytest`, `ruff check .`, `ruff format --check .`, `mypy .`) before the commit.
- Every new `.py` file starts with the 4-line header: `#!/usr/bin/env python3` (executables only), `# Author: Julian Bolivar`, `# Version: 1.0.0`, `# Date: 2026-05-06`.
- All escenario regex matching uses `spec_snapshot._SCENARIO_HEADER_RE` line-anchored format (production regex shipped v1.0.1 A1).
- INV-37 composite-signature tripwire is preserved unchanged in all paths Item C touches.

**Commit prefix map per task type** (from `CLAUDE.local.md` §5):

| Phase | Prefix |
|-------|--------|
| Red (failing test) | `test:` |
| Green (impl) | `feat:` (new module) or `fix:` (bug fix) |
| Refactor | `refactor:` |
| Task close (mark `[x]` in plan) | `chore:` |

---

## Track Alpha — Cross-check completion (Subagent #1, sequential)

**Owner**: Subagent #1 dispatched from orchestrator.
**Surfaces** (cero overlap with Track Beta): `scripts/cross_check_telemetry.py` (new); `tests/test_cross_check_telemetry.py` (new); `tests/test_pre_merge_cross_check.py` (extend).
**Wall-time estimated**: 6-9h.

### Task 1: Item A — `aggregate()` core: happy path + empty + malformed [x]

**Files:**
- Create: `scripts/cross_check_telemetry.py`
- Create: `tests/test_cross_check_telemetry.py`

Covers escenarios A-1, A-2, A-3 from spec sec.§4.

#### Red Phase

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Tests for scripts/cross_check_telemetry.py (v1.0.2 Item A).

Covers escenarios A-1 (happy path), A-2 (empty dir), A-3 (malformed
JSON skipped) per sbtdd/spec-behavior.md sec.§4.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _make_iter_artifact(path: Path, iter_n: int, decisions: list[dict]) -> None:
    """Write a synthetic iter{N}-{ts}.json artifact."""
    payload = {
        "iter": iter_n,
        "timestamp": f"2026-05-06T0{iter_n}:00:00Z",
        "magi_verdict": "GO_WITH_CAVEATS",
        "cross_check_decisions": decisions,
        "diff_truncated": False,
        "diff_original_bytes": 12345,
        "diff_cap_bytes": 200000,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_a1_happy_path_aggregates_three_iters(tmp_path):
    """A-1: aggregate three valid iter artifacts."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-2026-05-06.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t1", "severity": "WARNING"}],
    )
    _make_iter_artifact(
        root / "iter2-2026-05-06.json",
        2,
        [{"original_index": 0, "decision": "DOWNGRADE", "rationale": "info",
          "recommended_severity": "INFO", "agent": "balthasar",
          "title": "t2", "severity": "WARNING"}],
    )
    _make_iter_artifact(
        root / "iter3-2026-05-06.json",
        3,
        [{"original_index": 0, "decision": "REJECT", "rationale": "fp",
          "recommended_severity": None, "agent": "caspar",
          "title": "t3", "severity": "WARNING"}],
    )

    report = aggregate(root)

    assert report.total_iters == 3
    assert report.decision_distribution == {"KEEP": 1, "DOWNGRADE": 1, "REJECT": 1}
    assert len(report.per_iter) == 3
    assert [p.iter for p in report.per_iter] == [1, 2, 3]
    assert 0.0 <= report.agreement_rate <= 1.0
    assert 0.0 <= report.truncation_rate <= 1.0


def test_a2_empty_directory_tolerated(tmp_path):
    """A-2: empty dir returns total_iters=0 without error."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate

    root = tmp_path / "magi-cross-check"
    root.mkdir()

    report = aggregate(root)

    assert report.total_iters == 0
    assert report.decision_distribution == {}
    assert report.per_iter == []


def test_a3_malformed_json_skipped_with_breadcrumb(tmp_path, capsys):
    """A-3: malformed JSON files skipped with stderr breadcrumb."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-good.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t", "severity": "WARNING"}],
    )
    (root / "iter2-broken.json").write_text("{not json", encoding="utf-8")
    _make_iter_artifact(
        root / "iter3-good.json",
        3,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "balthasar",
          "title": "t", "severity": "WARNING"}],
    )

    report = aggregate(root)

    assert report.total_iters == 2
    captured = capsys.readouterr()
    assert "iter2-broken.json" in captured.err
    assert "skip" in captured.err.lower() or "malformed" in captured.err.lower()


def test_aggregate_missing_root_raises_filenotfounderror(tmp_path):
    """W3 iter 1 fix: aggregate() raises FileNotFoundError when root absent."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate

    ghost = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError) as exc:
        aggregate(ghost)
    assert str(ghost) in str(exc.value)
    assert "Feature G" in str(exc.value)
```

Save to `tests/test_cross_check_telemetry.py`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_cross_check_telemetry.py -v
```

Expected: 3 FAILures with `ModuleNotFoundError: No module named 'cross_check_telemetry'`.

- [ ] **Step 3: Verify + commit Red phase**

Per `CLAUDE.local.md` §3 Red phase rule: test must fail "for the right reason" (absence of implementation). `ModuleNotFoundError` qualifies. Bypass `make verify` for Red commit (`pytest` would fail) by running individual non-pytest checks:

```bash
python -m ruff check tests/test_cross_check_telemetry.py
python -m ruff format --check tests/test_cross_check_telemetry.py
python -m mypy tests/test_cross_check_telemetry.py
git add tests/test_cross_check_telemetry.py
git commit -m "test: A-1/A-2/A-3 tripwires for cross_check_telemetry.aggregate()"
```

#### Green Phase

- [ ] **Step 4: Implement minimum**

Create `scripts/` directory if it does not exist:

```bash
mkdir -p scripts
```

Save to `scripts/cross_check_telemetry.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""scripts/cross_check_telemetry.py — aggregate cross-check artifacts.

Standalone tooling (not part of skills/sbtdd/scripts/ runtime path).
Consumes .claude/magi-cross-check/iter{N}-{ts}.json artifacts emitted
by pre_merge_cmd._loop2_with_cross_check (v1.0.0 Feature G) and
produces aggregated metrics (markdown or JSON).

Per spec sec.2.1 v1.0.2 Item A.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class IterReport:
    iter: int
    verdict: str
    decisions: dict[str, int]
    agents: dict[str, int]
    severity: dict[str, int]
    diff_truncated: bool
    diff_original_bytes: int


@dataclass(frozen=True)
class TelemetryReport:
    total_iters: int
    decision_distribution: dict[str, int]
    per_iter: list[IterReport]
    agreement_rate: float
    truncation_rate: float


def _parse_iter(payload: dict[str, Any]) -> IterReport:
    decisions: dict[str, int] = {}
    agents: dict[str, int] = {}
    severity: dict[str, int] = {}
    cross = payload.get("cross_check_decisions", [])
    for d in cross:
        decisions[d["decision"]] = decisions.get(d["decision"], 0) + 1
        agents[d.get("agent", "?")] = agents.get(d.get("agent", "?"), 0) + 1
        sev = d.get("severity", "?")
        severity[sev] = severity.get(sev, 0) + 1
    return IterReport(
        iter=int(payload["iter"]),
        verdict=str(payload.get("magi_verdict", "")),
        decisions=decisions,
        agents=agents,
        severity=severity,
        diff_truncated=bool(payload.get("diff_truncated", False)),
        diff_original_bytes=int(payload.get("diff_original_bytes", 0)),
    )


def aggregate(
    root: Path,
    cycle_pattern: str = "iter*-*.json",
) -> TelemetryReport:
    """Aggregate cross-check artifacts under root.

    Args:
        root: Directory containing iter{N}-{ts}.json artifacts.
        cycle_pattern: Glob pattern matching v1.0.0 Feature G output.

    Returns:
        TelemetryReport. Empty dir returns total_iters=0 without error.

    Raises:
        FileNotFoundError: root does not exist (guidance-rich message).
    """
    if not root.exists():
        raise FileNotFoundError(
            f"Cross-check artifacts root not found: {root}\n"
            "Expected `.claude/magi-cross-check/` from v1.0.0 Feature G."
        )
    iters: list[IterReport] = []
    for path in sorted(root.glob(cycle_pattern)):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                f"[cross_check_telemetry] skip malformed {path}: {exc}\n"
            )
            continue
        try:
            iters.append(_parse_iter(payload))
        except (KeyError, ValueError, TypeError) as exc:
            sys.stderr.write(
                f"[cross_check_telemetry] skip malformed {path}: {exc}\n"
            )
            continue
    iters.sort(key=lambda i: i.iter)

    decision_dist: dict[str, int] = {}
    truncated_count = 0
    severity_match = 0
    severity_total = 0
    for ir in iters:
        for k, v in ir.decisions.items():
            decision_dist[k] = decision_dist.get(k, 0) + v
        if ir.diff_truncated:
            truncated_count += 1
        for k, v in ir.decisions.items():
            severity_total += v
            if k == "KEEP":
                severity_match += v

    agreement = severity_match / severity_total if severity_total else 0.0
    truncation = truncated_count / len(iters) if iters else 0.0

    return TelemetryReport(
        total_iters=len(iters),
        decision_distribution=decision_dist,
        per_iter=iters,
        agreement_rate=agreement,
        truncation_rate=truncation,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python -m pytest tests/test_cross_check_telemetry.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Verify + commit Green phase**

```bash
make verify
git add scripts/cross_check_telemetry.py
git commit -m "feat: cross_check_telemetry.aggregate() core (A-1/A-2/A-3)"
```

#### Refactor Phase

- [ ] **Step 7: Refactor (optional cleanup)**

Review `_parse_iter` — acceptable as-is. Confirm `from __future__ import annotations` at top. If no changes needed, skip step 8.

- [ ] **Step 8: Verify + commit Refactor phase**

```bash
make verify
# If changes were made:
# git add scripts/cross_check_telemetry.py
# git commit -m "refactor: <description>"
```

#### Task close

- [ ] **Step 9: Mark `[x]` in plan + close task**

Edit `planning/claude-plan-tdd.md` (the approved plan, copied from this org file post-Checkpoint-2) to mark Task 1 `[x]`.

```bash
git add planning/claude-plan-tdd.md
git commit -m "chore: mark task 1 complete (A core aggregate)"
```

---

### Task 2: Item A — Markdown formatter (escenario A-4) [x]

**Files:**
- Modify: `scripts/cross_check_telemetry.py`
- Modify: `tests/test_cross_check_telemetry.py`

#### Red Phase

- [ ] **Step 1: Append failing tests**

Append to `tests/test_cross_check_telemetry.py`:

```python
def test_a4_markdown_output_well_formed(tmp_path):
    """A-4: markdown output contains required tables."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_markdown

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1-x.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t", "severity": "WARNING"}],
    )

    report = aggregate(root)
    md = format_markdown(report)

    assert "Decision distribution" in md
    assert "Per-iter breakdown" in md
    assert "Per-agent" in md
    assert "Per-severity" in md
    assert "|---" in md
    assert "KEEP" in md


def test_a4_empty_markdown_no_iterations_message(tmp_path):
    """A-4 empty: markdown shows 'No iterations found' for empty dir."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_markdown

    root = tmp_path / "empty"
    root.mkdir()
    md = format_markdown(aggregate(root))

    assert "No iterations found" in md
```

- [ ] **Step 2: Run** — `pytest tests/test_cross_check_telemetry.py::test_a4_markdown_output_well_formed -v`. Expected FAIL with `ImportError: cannot import name 'format_markdown'`.

- [ ] **Step 3: Verify + commit Red**

```bash
python -m ruff check tests/test_cross_check_telemetry.py
python -m ruff format --check tests/test_cross_check_telemetry.py
python -m mypy tests/test_cross_check_telemetry.py
git add tests/test_cross_check_telemetry.py
git commit -m "test: A-4 markdown formatter tripwire"
```

#### Green Phase

- [ ] **Step 4: Append impl**

Append to `scripts/cross_check_telemetry.py`:

```python
def format_markdown(report: TelemetryReport) -> str:
    """Format a TelemetryReport as human-readable markdown."""
    if report.total_iters == 0:
        return "# Cross-check telemetry\n\nNo iterations found.\n"
    lines = ["# Cross-check telemetry", ""]
    lines.append(f"Total iters: {report.total_iters}")
    lines.append(f"Agreement rate: {report.agreement_rate:.2%}")
    lines.append(f"Truncation rate: {report.truncation_rate:.2%}")
    lines.append("")
    lines.append("## Decision distribution")
    lines.append("| Decision | Count |")
    lines.append("|---|---|")
    for k in sorted(report.decision_distribution):
        lines.append(f"| {k} | {report.decision_distribution[k]} |")
    lines.append("")
    lines.append("## Per-iter breakdown")
    lines.append("| Iter | Verdict | KEEP | DOWNGRADE | REJECT | Truncated |")
    lines.append("|---|---|---|---|---|---|")
    for ir in report.per_iter:
        d = ir.decisions
        lines.append(
            f"| {ir.iter} | {ir.verdict} | "
            f"{d.get('KEEP', 0)} | {d.get('DOWNGRADE', 0)} | "
            f"{d.get('REJECT', 0)} | {ir.diff_truncated} |"
        )
    lines.append("")
    lines.append("## Per-agent rate")
    lines.append("| Agent | Findings |")
    lines.append("|---|---|")
    agg_agents: dict[str, int] = {}
    for ir in report.per_iter:
        for a, c in ir.agents.items():
            agg_agents[a] = agg_agents.get(a, 0) + c
    for a in sorted(agg_agents):
        lines.append(f"| {a} | {agg_agents[a]} |")
    lines.append("")
    lines.append("## Per-severity")
    lines.append("| Severity | Count |")
    lines.append("|---|---|")
    agg_sev: dict[str, int] = {}
    for ir in report.per_iter:
        for s, c in ir.severity.items():
            agg_sev[s] = agg_sev.get(s, 0) + c
    for s in sorted(agg_sev):
        lines.append(f"| {s} | {agg_sev[s]} |")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 5: Run all tests pass**

```bash
python -m pytest tests/test_cross_check_telemetry.py -v
```

Expected: 5 PASS.

- [ ] **Step 6: Verify + Green commit**

```bash
make verify
git add scripts/cross_check_telemetry.py
git commit -m "feat: A-4 markdown formatter for TelemetryReport"
```

- [ ] **Step 7-8: Refactor + verify (skip commit if no changes)**
- [ ] **Step 9: Task close**

```bash
git add planning/claude-plan-tdd.md
git commit -m "chore: mark task 2 complete (A markdown formatter)"
```

---

### Task 3: Item A — JSON formatter (escenario A-5)

**Files:**
- Modify: `scripts/cross_check_telemetry.py`
- Modify: `tests/test_cross_check_telemetry.py`

#### Red Phase

- [ ] **Step 1: Append test**

```python
def test_a5_json_output_parseable(tmp_path):
    """A-5: JSON output round-trips through json.loads."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate, format_json

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t", "severity": "WARNING"}],
    )

    report = aggregate(root)
    text = format_json(report)
    parsed = json.loads(text)

    assert set(parsed.keys()) >= {
        "total_iters", "decision_distribution", "per_iter",
        "agreement_rate", "truncation_rate",
    }
    assert parsed["total_iters"] == 1
    assert isinstance(parsed["per_iter"], list)
    assert isinstance(parsed["agreement_rate"], (int, float))
```

- [ ] **Step 2: Run** — Expected FAIL `ImportError: cannot import name 'format_json'`.
- [ ] **Step 3: Red commit `test: A-5 JSON formatter tripwire`**

#### Green Phase

- [ ] **Step 4: Append impl**

```python
def format_json(report: TelemetryReport) -> str:
    """Format a TelemetryReport as JSON (machine-readable)."""
    payload = {
        "total_iters": report.total_iters,
        "decision_distribution": dict(report.decision_distribution),
        "per_iter": [
            {
                "iter": ir.iter,
                "verdict": ir.verdict,
                "decisions": dict(ir.decisions),
                "agents": dict(ir.agents),
                "severity": dict(ir.severity),
                "diff_truncated": ir.diff_truncated,
                "diff_original_bytes": ir.diff_original_bytes,
            }
            for ir in report.per_iter
        ],
        "agreement_rate": report.agreement_rate,
        "truncation_rate": report.truncation_rate,
    }
    return json.dumps(payload, indent=2)
```

- [ ] **Step 5-6: Verify pass + Green commit `feat: A-5 JSON formatter`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 3 complete`**

---

### Task 4: Item A — CLI wrapper + arg parsing

**Files:**
- Modify: `scripts/cross_check_telemetry.py`
- Modify: `tests/test_cross_check_telemetry.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_cli_default_format_markdown(tmp_path, capsys):
    """CLI invokes aggregate + format_markdown by default."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t", "severity": "WARNING"}],
    )

    rc = main(["--root", str(root)])
    captured = capsys.readouterr()

    assert rc == 0
    assert "Decision distribution" in captured.out


def test_cli_format_json_flag(tmp_path, capsys):
    """CLI --format json outputs JSON parseable text."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    _make_iter_artifact(
        root / "iter1.json",
        1,
        [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
          "recommended_severity": None, "agent": "melchior",
          "title": "t", "severity": "WARNING"}],
    )

    rc = main(["--root", str(root), "--format", "json"])
    captured = capsys.readouterr()

    assert rc == 0
    parsed = json.loads(captured.out)
    assert parsed["total_iters"] == 1


def test_cli_missing_root_exit_2(tmp_path, capsys):
    """CLI raises FileNotFoundError ⇒ exit code 2."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import main

    rc = main(["--root", str(tmp_path / "does-not-exist")])
    captured = capsys.readouterr()

    assert rc == 2
    assert "not found" in captured.err.lower()
```

- [ ] **Step 2-3: Red commit `test: CLI flag handling for cross_check_telemetry`**

#### Green Phase

- [ ] **Step 4: Append CLI**

```python
def main(argv: list[str] | None = None) -> int:
    """Entrypoint for `python scripts/cross_check_telemetry.py [...]`."""
    import argparse

    parser = argparse.ArgumentParser(prog="cross_check_telemetry")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(".claude/magi-cross-check"),
        help="Directory containing iter{N}-{ts}.json artifacts",
    )
    parser.add_argument(
        "--cycle",
        default="iter*-*.json",
        help="Glob pattern for iteration files",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
    )
    ns = parser.parse_args(argv)

    try:
        report = aggregate(ns.root, cycle_pattern=ns.cycle)
    except FileNotFoundError as exc:
        sys.stderr.write(f"{exc}\n")
        return 2

    if ns.format == "json":
        sys.stdout.write(format_json(report))
    else:
        sys.stdout.write(format_markdown(report))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5-6: Verify pass + Green commit `feat: CLI entrypoint for cross_check_telemetry`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 4 complete`**

---

### Task 5: Item A — Performance smoke (escenario A-6 NF32)

**Files:**
- Modify: `tests/test_cross_check_telemetry.py`

#### Red Phase

- [ ] **Step 1: Append test (regression-guard mode — impl already linear)**

```python
import time


@pytest.mark.slow
def test_a6_linear_performance_100_files(tmp_path):
    """A-6: 100 valid iter artifacts aggregate < 5s wall-clock (NF32)."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from cross_check_telemetry import aggregate

    root = tmp_path / "magi-cross-check"
    root.mkdir()
    for i in range(1, 101):
        _make_iter_artifact(
            root / f"iter{i}-x.json",
            i,
            [{"original_index": 0, "decision": "KEEP", "rationale": "ok",
              "recommended_severity": None, "agent": "melchior",
              "title": "t", "severity": "WARNING"}],
        )

    t0 = time.monotonic()
    report = aggregate(root)
    elapsed = time.monotonic() - t0

    assert report.total_iters == 100
    assert elapsed < 5.0, f"NF32 violation: {elapsed:.2f}s for 100 files"
```

- [ ] **Step 2: Run** — Expected PASS (impl is already linear). If fails: invoke `/systematic-debugging`; do NOT proceed without root cause.

- [ ] **Step 3: Verify + commit (regression guard)**

```bash
make verify
git add tests/test_cross_check_telemetry.py
git commit -m "test: A-6 performance regression guard for aggregate()"
```

- [ ] **Step 9: Task close `chore: mark task 5 complete`** (no Green/Refactor needed since impl is already correct).

---

### Task 6: Item B — Diff threading regression tests (escenarios B-1, B-2)

**Files:**
- Modify: `tests/test_pre_merge_cross_check.py`

#### Red Phase

- [ ] **Step 1: Append regression tests**

Append to `tests/test_pre_merge_cross_check.py`:

```python
def test_b1_cross_check_prompt_embeds_diff_when_provided():
    """B-1: prompt contains '## Cumulative diff under review' when diff != ''."""
    from pre_merge_cmd import _build_cross_check_prompt

    diff = "--- a/foo.py\n+++ b/foo.py\n@@ -1 +1 @@\n-old\n+new\n"
    findings = [{"severity": "WARNING", "agent": "melchior",
                 "title": "t", "detail": "d"}]
    prompt = _build_cross_check_prompt(diff, "GO_WITH_CAVEATS", findings)

    assert "## Cumulative diff under review" in prompt
    assert "old" in prompt and "new" in prompt


def test_b2_cross_check_prompt_omits_diff_when_empty():
    """B-2: prompt does NOT contain diff section when diff == ''."""
    from pre_merge_cmd import _build_cross_check_prompt

    findings = [{"severity": "WARNING", "agent": "melchior",
                 "title": "t", "detail": "d"}]
    prompt = _build_cross_check_prompt("", "GO_WITH_CAVEATS", findings)

    assert "## Cumulative diff under review" not in prompt
    assert "MAGI verdict: GO_WITH_CAVEATS" in prompt
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_pre_merge_cross_check.py::test_b1_cross_check_prompt_embeds_diff_when_provided tests/test_pre_merge_cross_check.py::test_b2_cross_check_prompt_omits_diff_when_empty -v
```

Expected: 2 PASS (impl already exists per spec sec.2.2 — `_build_cross_check_prompt` shipped v1.0.0 mid-cycle iter 2→3 fix).

If either fails: invoke `/systematic-debugging`; do NOT proceed without root cause.

- [ ] **Step 3: Verify + commit (regression guard)**

```bash
make verify
git add tests/test_pre_merge_cross_check.py
git commit -m "test: B-1/B-2 regression guards for diff threading in cross-check prompt"
```

- [ ] **Step 9: Task close `chore: mark task 6 complete`**

---

## Track Beta — spec_lint + meta-test + coverage (Subagent #2, sequential)

**Owner**: Subagent #2 dispatched from orchestrator.
**Surfaces**: `skills/sbtdd/scripts/spec_lint.py` (new); `skills/sbtdd/scripts/spec_cmd.py` (extend `_run_magi_checkpoint2`); `tests/test_spec_lint.py` (new); `tests/test_spec_cmd.py` (extend); `tests/test_invoke_skill_callsites_audit.py` (new); `pyproject.toml` (modify); `Makefile` (modify).
**Wall-time estimated**: 16-25h.

### Task 7: Item C — `LintFinding` dataclass + `lint_spec()` skeleton [x]

**Files:**
- Create: `skills/sbtdd/scripts/spec_lint.py`
- Create: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Write failing tests**

Create `tests/test_spec_lint.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Tests for skills/sbtdd/scripts/spec_lint.py (v1.0.2 Item C).

Covers escenarios C-R1-1..R5-2, C-int-1, C-int-2, C-cli-1 per
sbtdd/spec-behavior.md sec.§4.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest


def test_lint_finding_dataclass_shape():
    """LintFinding is a frozen dataclass with required fields."""
    from spec_lint import LintFinding

    assert is_dataclass(LintFinding)
    f = LintFinding(
        file=Path("x.md"), line=1, rule="R1",
        severity="error", message="m",
    )
    assert f.file == Path("x.md")
    assert f.line == 1
    assert f.rule == "R1"
    assert f.severity == "error"
    assert f.message == "m"
    with pytest.raises(Exception):
        f.line = 99  # type: ignore[misc]


def test_lint_spec_clean_file_returns_empty_list(tmp_path):
    """Clean spec returns empty list of findings."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# Title\n\n"
        "> Generado 2026-05-06 a partir de sbtdd/spec-behavior-base.md\n\n"
        "## 1. Section\n\n"
        "**Escenario X-1: example**\n\n"
        "> **Given** something\n"
        "> **When** action\n"
        "> **Then** result\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)

    assert findings == []
```

- [ ] **Step 2: Run** — Expected FAIL `ModuleNotFoundError`.
- [ ] **Step 3: Red commit `test: spec_lint LintFinding dataclass + clean-spec tripwire`**

#### Green Phase

- [ ] **Step 4: Implement skeleton**

Create `skills/sbtdd/scripts/spec_lint.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""skills/sbtdd/scripts/spec_lint.py — H5-2 spec_lint enforcement.

Mechanical lint checks against spec-behavior.md and plan-tdd-org.md.
Invoked from spec_cmd._run_magi_checkpoint2 BEFORE magi_dispatch.invoke_magi
to catch malformed specs before they consume MAGI iter budget.

Per spec sec.2.3 v1.0.2 Item C. 5 rules R1-R5; Q3 dictamen R3=warning.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LintFinding:
    file: Path
    line: int
    rule: str
    severity: str
    message: str


def lint_spec(path: Path) -> list[LintFinding]:
    """Run mechanical lint checks against a spec file.

    Returns:
        list of LintFinding (empty = clean). Error-severity findings
        block Checkpoint 2; warning-severity emit stderr breadcrumb
        but do not block.
    """
    if not path.exists():
        return [LintFinding(
            file=path, line=0, rule="R0",
            severity="error",
            message=f"spec file not found: {path}",
        )]
    text = path.read_text(encoding="utf-8")
    findings: list[LintFinding] = []
    # Subsequent tasks 8-12 fill in R1-R5 checks.
    return findings
```

- [ ] **Step 5: Run tests pass**
- [ ] **Step 6: Green commit `feat: spec_lint module skeleton with LintFinding dataclass`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 7 complete`**

---

### Task 8: Item C — R1 escenario well-formed (escenarios C-R1-1, C-R1-2) [x]

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_c_r1_1_well_formed_escenario_passes(tmp_path):
    """C-R1-1: escenario with all bullets returns no R1 finding."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: ejemplo**\n\n"
        "> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r1 = [f for f in findings if f.rule == "R1"]
    assert r1 == []


def test_c_r1_2_missing_given_fails(tmp_path):
    """C-R1-2: escenario missing Given block emits R1 error."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: bad**\n\n"
        "> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r1 = [f for f in findings if f.rule == "R1"]
    assert len(r1) == 1
    assert r1[0].severity == "error"
    assert "given" in r1[0].message.lower()
```

- [ ] **Step 2-3: Red commit `test: C-R1 escenario well-formed checks`**

#### Green Phase

- [ ] **Step 4: Implement R1**

In `skills/sbtdd/scripts/spec_lint.py` add (after `LintFinding` dataclass, before `lint_spec`):

```python
import re

_ESCENARIO_RE = re.compile(
    r"^(?:\*\*Escenario\s+([A-Za-z0-9-]+)[^\*]*\*\*|"
    r"#{2,3}\s+Escenario\s+([A-Za-z0-9-]+)[^\n]*)\s*$",
    re.MULTILINE,
)
_GIVEN_RE = re.compile(r"^>\s*\*\*Given\*\*", re.MULTILINE)
_WHEN_RE = re.compile(r"^>\s*\*\*When\*\*", re.MULTILINE)
_THEN_RE = re.compile(r"^>\s*\*\*Then\*\*", re.MULTILINE)


def _check_r1(path: Path, text: str) -> list[LintFinding]:
    """R1: each escenario block has Given + When + Then bullets."""
    findings: list[LintFinding] = []
    matches = list(_ESCENARIO_RE.finditer(text))
    for i, m in enumerate(matches):
        line_start = text.count("\n", 0, m.start()) + 1
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.end():block_end]
        for label, rx in (("Given", _GIVEN_RE), ("When", _WHEN_RE), ("Then", _THEN_RE)):
            if not rx.search(block):
                findings.append(LintFinding(
                    file=path, line=line_start, rule="R1",
                    severity="error",
                    message=f"escenario at line {line_start} missing {label} block",
                ))
    return findings
```

Update `lint_spec` to call R1:

```python
def lint_spec(path: Path) -> list[LintFinding]:
    if not path.exists():
        return [LintFinding(file=path, line=0, rule="R0",
                            severity="error",
                            message=f"spec file not found: {path}")]
    text = path.read_text(encoding="utf-8")
    findings: list[LintFinding] = []
    findings.extend(_check_r1(path, text))
    return findings
```

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint R1 escenario well-formed check`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 8 complete`**

---

### Task 9: Item C — R2 unique IDs (escenarios C-R2-1, C-R2-2) [x]

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_c_r2_1_unique_ids_pass(tmp_path):
    """C-R2-1: distinct escenario IDs return no R2 finding."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: a**\n\n> **Given** g\n> **When** w\n> **Then** t\n\n"
        "**Escenario X-2: b**\n\n> **Given** g\n> **When** w\n> **Then** t\n\n"
        "**Escenario Y-1: c**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    assert [f for f in findings if f.rule == "R2"] == []


def test_c_r2_2_duplicate_id_fails(tmp_path):
    """C-R2-2: duplicate escenario ID emits R2 errors for both occurrences."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "**Escenario X-1: first**\n\n> **Given** g\n> **When** w\n> **Then** t\n\n"
        "**Escenario X-1: dup**\n\n> **Given** g\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r2 = [f for f in findings if f.rule == "R2"]
    assert len(r2) == 2
    assert all(f.severity == "error" for f in r2)
```

- [ ] **Step 2-3: Red commit `test: C-R2 unique escenario IDs`**

#### Green Phase

- [ ] **Step 4: Implement R2**

Add to `skills/sbtdd/scripts/spec_lint.py`:

```python
def _check_r2(path: Path, text: str) -> list[LintFinding]:
    """R2: escenario IDs unique across spec."""
    findings: list[LintFinding] = []
    seen: dict[str, list[int]] = {}
    for m in _ESCENARIO_RE.finditer(text):
        ident = m.group(1) or m.group(2)
        if ident is None:
            continue
        line = text.count("\n", 0, m.start()) + 1
        seen.setdefault(ident, []).append(line)
    for ident, lines in seen.items():
        if len(lines) > 1:
            for ln in lines:
                others = [l for l in lines if l != ln]
                findings.append(LintFinding(
                    file=path, line=ln, rule="R2",
                    severity="error",
                    message=f"duplicate escenario ID '{ident}' (other occurrences: {others})",
                ))
    return findings
```

Append `findings.extend(_check_r2(path, text))` to `lint_spec`.

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint R2 unique IDs check`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 9 complete`**

---

### Task 10: Item C — R3 monotonic headers warning (escenarios C-R3-1, C-R3-2)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_c_r3_1_monotonic_headers_pass(tmp_path):
    """C-R3-1: monotonic ## N headers return no R3 finding."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. one\n\n## 2. two\n\n## 3. three\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    assert [f for f in findings if f.rule == "R3"] == []


def test_c_r3_2_skip_emits_warning_severity(tmp_path):
    """C-R3-2: header skip emits R3 finding at warning severity (Q3)."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. one\n\n## 2. two\n\n## 5. five\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r3 = [f for f in findings if f.rule == "R3"]
    assert len(r3) >= 1
    assert all(f.severity == "warning" for f in r3)
```

- [ ] **Step 2-3: Red commit `test: C-R3 monotonic headers warning severity`**

#### Green Phase

- [ ] **Step 4: Implement R3**

```python
_HEADER_RE = re.compile(r"^##\s+(\d+)\.\s", re.MULTILINE)


def _check_r3(path: Path, text: str) -> list[LintFinding]:
    """R3: section headers ## N. monotonic (warning per Q3)."""
    findings: list[LintFinding] = []
    last = 0
    for m in _HEADER_RE.finditer(text):
        n = int(m.group(1))
        line = text.count("\n", 0, m.start()) + 1
        if n != last + 1 and last != 0:
            findings.append(LintFinding(
                file=path, line=line, rule="R3",
                severity="warning",
                message=f"section header skip: ## {n}. follows ## {last}.",
            ))
        last = n
    return findings
```

Append `findings.extend(_check_r3(path, text))` to `lint_spec`.

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint R3 monotonic headers warning`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 10 complete`**

---

### Task 11: Item C — R4 INV-27 mechanical extension (escenario C-R4-1)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append test**

```python
def test_c_r4_1_inv27_extends_to_spec_behavior(tmp_path):
    """C-R4-1: spec-behavior.md with uppercase placeholder emits R4 error.

    Synthetic fixture must use one of the three INV-27 tokens; we look up
    spec_cmd._INV27_TOKENS to avoid hardcoding.
    """
    from spec_cmd import _INV27_TOKENS
    from spec_lint import lint_spec

    token = _INV27_TOKENS[0]
    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        f"## 1. Section\n\nThis line contains {token} marker.\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r4 = [f for f in findings if f.rule == "R4"]
    assert len(r4) >= 1
    assert all(f.severity == "error" for f in r4)
    assert any("INV-27" in f.message for f in r4)
```

- [ ] **Step 2-3: Red commit `test: C-R4 INV-27 extends to spec-behavior.md`**

#### Green Phase

- [ ] **Step 4: Implement R4**

Add to `skills/sbtdd/scripts/spec_lint.py`:

```python
from spec_cmd import _INV27_RE


def _check_r4(path: Path, text: str) -> list[LintFinding]:
    """R4: cero matches uppercase placeholder (INV-27 mechanical)."""
    findings: list[LintFinding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _INV27_RE.search(line):
            findings.append(LintFinding(
                file=path, line=lineno, rule="R4",
                severity="error",
                message=f"INV-27 mechanical: line {lineno} contains uppercase placeholder",
            ))
    return findings
```

Append `findings.extend(_check_r4(path, text))` to `lint_spec`.

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint R4 INV-27 extension`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 11 complete`**

---

### Task 12: Item C — R5 frontmatter docstring (escenarios C-R5-1, C-R5-2)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_c_r5_1_frontmatter_present_passes(tmp_path):
    """C-R5-1: '> Generado YYYY-MM-DD ...' present in first 30 lines passes."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n\n> Generado 2026-05-06 a partir de sbtdd/spec-behavior-base.md\n\n"
        "## 1. Section\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    assert [f for f in findings if f.rule == "R5"] == []


def test_c_r5_2_missing_frontmatter_fails(tmp_path):
    """C-R5-2: missing frontmatter emits R5 error at line 1."""
    from spec_lint import lint_spec

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n\n## 1. Section\n\nNo frontmatter at all.\n",
        encoding="utf-8",
    )

    findings = lint_spec(spec)
    r5 = [f for f in findings if f.rule == "R5"]
    assert len(r5) == 1
    assert r5[0].severity == "error"
    assert r5[0].line == 1
```

- [ ] **Step 2-3: Red commit `test: C-R5 frontmatter docstring check`**

#### Green Phase

- [ ] **Step 4: Implement R5**

```python
_FRONTMATTER_RE = re.compile(
    r"^>\s*Generado\s+\d{4}-\d{2}-\d{2}\s+a\s+partir\s+de\s+\S+",
    re.MULTILINE,
)


def _check_r5(path: Path, text: str) -> list[LintFinding]:
    """R5: frontmatter docstring in first 30 lines."""
    head = "\n".join(text.splitlines()[:30])
    if not _FRONTMATTER_RE.search(head):
        return [LintFinding(
            file=path, line=1, rule="R5",
            severity="error",
            message="missing frontmatter docstring '> Generado YYYY-MM-DD a partir de <source>'",
        )]
    return []
```

Append `findings.extend(_check_r5(path, text))` to `lint_spec`.

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint R5 frontmatter docstring check`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 12 complete`**

---

### Task 13: Item C — Integration en `_run_magi_checkpoint2` (escenarios C-int-1, C-int-2)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_cmd.py`
- Modify: `tests/test_spec_cmd.py`

#### Red Phase

- [ ] **Step 1: Append tests**

Append to `tests/test_spec_cmd.py`:

```python
def test_c_int_1_lint_error_aborts_checkpoint2(tmp_path, monkeypatch):
    """C-int-1: spec_lint R1 error aborts before magi_dispatch.invoke_magi."""
    import spec_cmd
    from errors import ValidationError

    root = tmp_path
    (root / "sbtdd").mkdir()
    (root / "planning").mkdir()
    spec = root / "sbtdd" / "spec-behavior.md"
    plan = root / "planning" / "claude-plan-tdd-org.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. Section\n\n**Escenario X-1: bad**\n\n> **When** w\n> **Then** t\n",
        encoding="utf-8",
    )
    plan.write_text(
        "# Plan\n> Generado 2026-05-06 a partir de y.md\n\n## 1. Section\n",
        encoding="utf-8",
    )

    invoke_called = []
    monkeypatch.setattr(
        "magi_dispatch.invoke_magi",
        lambda *a, **kw: invoke_called.append(True),
    )

    cfg = type("Cfg", (), {"magi_max_iterations": 3, "magi_threshold": "GO_WITH_CAVEATS"})()
    ns = type("NS", (), {"override_checkpoint": False, "reason": None,
                          "resume_from_magi": False})()
    with pytest.raises(ValidationError) as exc:
        spec_cmd._run_magi_checkpoint2(root, cfg, ns)

    assert "spec_lint" in str(exc.value).lower()
    assert "R1" in str(exc.value)
    assert invoke_called == []


def test_c_int_2_lint_warning_emits_breadcrumb_proceeds(tmp_path, monkeypatch, capsys):
    """C-int-2: R3 warning emits stderr breadcrumb but does not abort."""
    import spec_cmd

    root = tmp_path
    (root / "sbtdd").mkdir()
    (root / "planning").mkdir()
    spec = root / "sbtdd" / "spec-behavior.md"
    plan = root / "planning" / "claude-plan-tdd-org.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. one\n\n## 2. two\n\n## 5. five\n",
        encoding="utf-8",
    )
    plan.write_text(
        "# Plan\n> Generado 2026-05-06 a partir de y.md\n\n## 1. Section\n",
        encoding="utf-8",
    )

    invoke_called = []
    def fake_invoke(*a, **kw):
        invoke_called.append(True)
        return {"verdict": "GO", "iterations": [], "degraded": False}
    monkeypatch.setattr("magi_dispatch.invoke_magi", fake_invoke)
    monkeypatch.setattr(spec_cmd, "_create_state_file", lambda *a, **kw: None)
    monkeypatch.setattr(spec_cmd, "_commit_approved_artifacts", lambda *a, **kw: None)

    cfg = type("Cfg", (), {"magi_max_iterations": 3, "magi_threshold": "GO_WITH_CAVEATS"})()
    ns = type("NS", (), {"override_checkpoint": False, "reason": None,
                          "resume_from_magi": False})()
    spec_cmd._run_magi_checkpoint2(root, cfg, ns)

    captured = capsys.readouterr()
    assert "spec-lint" in captured.err.lower() or "R3" in captured.err
    assert invoke_called == [True]
```

- [ ] **Step 2-3: Red commit `test: C-int-1/C-int-2 spec_lint integration in checkpoint2`**

#### Green Phase

- [ ] **Step 4: Patch `_run_magi_checkpoint2`**

In `skills/sbtdd/scripts/spec_cmd.py`, locate `_run_magi_checkpoint2` (~line 525). At the top of the function body — AFTER any existing precondition checks (e.g., file existence) but BEFORE `magi_dispatch.invoke_magi` — insert:

```python
    # v1.0.2 Item C: spec_lint pre-dispatch gate
    import spec_lint
    spec_path = root / "sbtdd" / "spec-behavior.md"
    plan_path = root / "planning" / "claude-plan-tdd-org.md"
    for path in (spec_path, plan_path):
        if not path.exists():
            continue
        findings = spec_lint.lint_spec(path)
        for w in (f for f in findings if f.severity == "warning"):
            sys.stderr.write(
                f"[sbtdd spec-lint] {w.file}:{w.line} ({w.rule}) {w.message}\n"
            )
        errors = [f for f in findings if f.severity == "error"]
        if errors:
            details = "\n".join(
                f"  {e.file}:{e.line} ({e.rule}) {e.message}"
                for e in errors
            )
            from errors import ValidationError
            raise ValidationError(
                "spec_lint blocked Checkpoint 2 dispatch:\n"
                f"{details}\n"
                "Fix violations and re-run /sbtdd spec."
            )
```

Verify `import sys` is present at top of `spec_cmd.py`; add if missing.

**Lint timing contract (C1 iter 1 fix)**: this insertion places the
spec_lint gate at the TOP of `_run_magi_checkpoint2`, BEFORE the
existing MAGI iter loop. Concretely: the lint runs ONCE per
`/sbtdd spec` invocation, NOT once per MAGI iter. If lint raises
`ValidationError`, the cycle aborts BEFORE entering the iter loop,
so the safety valve cap=3 G1 binding budget is NOT consumed. The
operator fixes the lint violations and re-runs `/sbtdd spec`, which
starts a fresh iter budget. Verify the insertion point is upstream
of any `for iter_n in range(cfg.magi_max_iterations):` loop in
`_run_magi_checkpoint2`.

- [ ] **Step 5: Run tests pass**
- [ ] **Step 6: Green commit `feat: integrate spec_lint gate in _run_magi_checkpoint2`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 13 complete`**

---

### Task 14: Item C — CLI standalone (escenario C-cli-1)

**Files:**
- Modify: `skills/sbtdd/scripts/spec_lint.py`
- Modify: `tests/test_spec_lint.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_c_cli_1_clean_spec_exit_0(tmp_path):
    """C-cli-1: clean spec ⇒ exit 0."""
    from spec_lint import main

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n> Generado 2026-05-06 a partir de x.md\n\n"
        "## 1. Section\n",
        encoding="utf-8",
    )

    rc = main([str(spec)])
    assert rc == 0


def test_c_cli_1_error_exit_1(tmp_path):
    """CLI returns 1 when error finding present (R5 missing frontmatter)."""
    from spec_lint import main

    spec = tmp_path / "spec.md"
    spec.write_text(
        "# T\n\n## 1. No frontmatter\n",
        encoding="utf-8",
    )

    rc = main([str(spec)])
    assert rc == 1


def test_c_cli_1_missing_file_exit_2(tmp_path):
    """CLI returns 2 when path does not exist."""
    from spec_lint import main

    rc = main([str(tmp_path / "ghost.md")])
    assert rc == 2
```

- [ ] **Step 2-3: Red commit `test: C-cli-1 spec_lint exit codes`**

#### Green Phase

- [ ] **Step 4: Append CLI**

Append to `skills/sbtdd/scripts/spec_lint.py`:

```python
def main(argv: list[str] | None = None) -> int:
    """Entrypoint for `python -m skills.sbtdd.scripts.spec_lint <path>`."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="spec_lint")
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--severity",
        choices=("error", "warning", "info"),
        default=None,
    )
    parser.add_argument(
        "--rule",
        choices=("R1", "R2", "R3", "R4", "R5"),
        default=None,
    )
    ns = parser.parse_args(argv)

    if not ns.path.exists():
        sys.stderr.write(f"spec file not found: {ns.path}\n")
        return 2

    findings = lint_spec(ns.path)
    if ns.rule:
        findings = [f for f in findings if f.rule == ns.rule]
    if ns.severity:
        findings = [f for f in findings if f.severity == ns.severity]

    for f in findings:
        sys.stdout.write(
            f"{f.file}:{f.line} ({f.rule} {f.severity}) {f.message}\n"
        )

    has_error = any(f.severity == "error" for f in findings)
    return 1 if has_error else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

- [ ] **Step 5-6: Verify pass + Green commit `feat: spec_lint CLI standalone`**
- [ ] **Step 7-9: Refactor + Task close `chore: mark task 14 complete`**

---

### Task 15: Item F — Meta-test core (escenarios F-1, F-2)

**Files:**
- Create: `tests/fixtures/audit_callsites/__init__.py`
- Create: `tests/fixtures/audit_callsites/with_override.py`
- Create: `tests/fixtures/audit_callsites/without_override.py`
- Create: `tests/test_invoke_skill_callsites_audit.py`

#### Red Phase

- [ ] **Step 1: Write fixtures + test (regression-guard mode)**

Create `tests/fixtures/audit_callsites/__init__.py` (empty file).

Create `tests/fixtures/audit_callsites/with_override.py`:

```python
"""Synthetic fixture: callsite with allow_interactive_skill=True override."""

def fake_call() -> None:
    invoke_skill(
        skill="brainstorming",
        args=["@spec.md"],
        allow_interactive_skill=True,
    )


def invoke_skill(**kwargs):  # pragma: no cover
    return None
```

Create `tests/fixtures/audit_callsites/without_override.py`:

```python
"""Synthetic fixture: callsite without override (should fail audit)."""

def fake_call() -> None:
    invoke_skill(
        skill="brainstorming",
        args=["@spec.md"],
    )


def invoke_skill(**kwargs):  # pragma: no cover
    return None
```

Create `tests/test_invoke_skill_callsites_audit.py`:

```python
#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-06
"""Meta-test enforcing allow_interactive_skill=True on direct invoke_skill
callsites for skills in _SUBPROCESS_INCOMPATIBLE_SKILLS.

Per spec sec.2.6 v1.0.2 Item F. Regression-guards future contributors
adding callsites without the override.
"""

from __future__ import annotations

import ast
from pathlib import Path


_INTERACTIVE_SKILLS = frozenset({"brainstorming", "writing-plans"})
_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXCLUDED_FILES = {
    "skills/sbtdd/scripts/superpowers_dispatch.py",
}


def _walk_invoke_skill_calls(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute) and node.func.attr == "invoke_skill":
            yield node
        elif isinstance(node.func, ast.Name) and node.func.id == "invoke_skill":
            yield node


def _check_path(path: Path) -> list[str]:
    violations = []
    for call in _walk_invoke_skill_calls(path):
        skill_kw = next(
            (kw for kw in call.keywords
             if kw.arg == "skill"
             and isinstance(kw.value, ast.Constant)
             and kw.value.value in _INTERACTIVE_SKILLS),
            None,
        )
        if skill_kw is None:
            continue
        has_override = any(
            kw.arg == "allow_interactive_skill"
            and isinstance(kw.value, ast.Constant)
            and kw.value.value is True
            for kw in call.keywords
        )
        if not has_override:
            violations.append(
                f"{path}:{call.lineno} invokes "
                f"invoke_skill(skill='{skill_kw.value.value}') "
                f"without allow_interactive_skill=True"
            )
    return violations


def test_f1_synthetic_fixture_without_override_fails():
    """F-1: synthetic fixture lacking override is detected by AST walk."""
    fixture = _REPO_ROOT / "tests" / "fixtures" / "audit_callsites" / "without_override.py"

    violations = _check_path(fixture)

    assert len(violations) == 1
    assert "without_override.py" in violations[0]
    assert "brainstorming" in violations[0]


def test_f2_synthetic_fixture_with_override_passes():
    """F-2: synthetic fixture with override produces no violation."""
    fixture = _REPO_ROOT / "tests" / "fixtures" / "audit_callsites" / "with_override.py"

    violations = _check_path(fixture)

    assert violations == []
```

- [ ] **Step 2: Run tests** — Expected PASS (this is regression-guard mode; impl is in the test file itself + synthetic fixtures).

- [ ] **Step 3: Verify + commit (regression guard)**

```bash
make verify
git add tests/test_invoke_skill_callsites_audit.py tests/fixtures/audit_callsites/
git commit -m "test: F-1/F-2 meta-test core (synthetic fixtures + AST walk)"
```

- [ ] **Step 9: Task close `chore: mark task 15 complete`**

---

### Task 16: Item F — Excludes + edge cases + production audit (F-3, F-4)

**Files:**
- Modify: `tests/test_invoke_skill_callsites_audit.py`

#### Red Phase

- [ ] **Step 1: Append tests**

```python
def test_f3_wrapper_files_excluded_from_audit():
    """F-3: superpowers_dispatch.py is in _EXCLUDED_FILES."""
    assert "skills/sbtdd/scripts/superpowers_dispatch.py" in _EXCLUDED_FILES


def test_f4_unknown_skill_passes_through(tmp_path):
    """F-4: unknown skill name is not in interactive set ⇒ no violation."""
    fixture = tmp_path / "unknown.py"
    fixture.write_text(
        'def f():\n'
        '    invoke_skill(skill="custom-skill", args=["x"])\n'
        'def invoke_skill(**kw): return None\n',
        encoding="utf-8",
    )

    violations = _check_path(fixture)

    assert violations == []


def test_production_callsites_pass_audit():
    """Full repo audit: all interactive-skill callsites in scripts/ + tests/
    pass override check (excluding wrappers + without_override fixture)."""
    audited_dirs = (
        _REPO_ROOT / "skills" / "sbtdd" / "scripts",
        _REPO_ROOT / "tests",
    )
    all_violations: list[str] = []
    for d in audited_dirs:
        for path in d.rglob("*.py"):
            rel = path.relative_to(_REPO_ROOT).as_posix()
            if rel in _EXCLUDED_FILES:
                continue
            if "without_override.py" in path.name:
                continue
            all_violations.extend(_check_path(path))

    assert not all_violations, (
        "Interactive-skill callsites missing override:\n"
        + "\n".join(all_violations)
        + "\n\nFix: add allow_interactive_skill=True or use wrapper."
    )
```

- [ ] **Step 2: Run** — Expected PASS (assuming v1.0.1 pre-A2 migration was complete).

If `test_production_callsites_pass_audit` FAILS: this is a real regression. Diagnose via `/systematic-debugging`. Either fix the offending callsite via mini-cycle TDD or add to `_EXCLUDED_FILES` with explicit justification.

- [ ] **Step 3: Verify + commit**

```bash
make verify
git add tests/test_invoke_skill_callsites_audit.py
git commit -m "test: F-3/F-4 excludes + production audit"
```

- [ ] **Step 9: Task close `chore: mark task 16 complete`**

---

### Task 17: Item G — Add `pytest-cov` + initial coverage config (placeholder threshold=0)

**Files:**
- Modify: `pyproject.toml`

This task has no test (config-only). Skip Red phase.

#### Green Phase

- [ ] **Step 1: Modify `pyproject.toml`**

Replace the `dev` deps list to add `pytest-cov`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",
    "pyyaml>=6.0",
    "types-pyyaml>=6.0",
    "ruff>=0.3",
    "mypy>=1.5",
]
```

**Add `[tool.coverage.*]` tables at the end of `pyproject.toml`** (C3
iter 1 fix — explicit insertion guidance to avoid landing inside
`[[tool.mypy.overrides]]` block which would silently corrupt mypy
config):

1. Open `pyproject.toml` and verify the file ends with the **last**
   `[[tool.mypy.overrides]]` block (currently terminates with
   `disable_error_code = ["type-arg", "misc", "unused-ignore"]`).
2. **Append a blank line** after the last `disable_error_code = ...`
   line. This blank line is structurally meaningful — without it, the
   subsequent `[tool.coverage.run]` table header could be parsed as
   continuing the `[[tool.mypy.overrides]]` table on some readers.
3. Append the two new tables AFTER the blank line:

```toml

[tool.coverage.run]
source = ["skills/sbtdd/scripts"]
omit = [
    "skills/sbtdd/scripts/__init__.py",
    "templates/*",
]

[tool.coverage.report]
fail_under = 0
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "def __repr__",
]
```

4. **Verification**: after editing, run the appropriate one-liner
   for your Python version to confirm the file parses as valid TOML
   AND the new tables landed at top level:

   - **Python 3.11+ (uses stdlib `tomllib`)**:
     ```bash
     python -c "import tomllib; data = tomllib.loads(open('pyproject.toml','rb').read()); assert 'coverage' in data['tool'], 'coverage tables not at top level'; print('OK')"
     ```
   - **Python 3.9/3.10 (no stdlib `tomllib`)**: install `tomli` if
     unavailable, then check (W2 iter 2 fix — `import tomli`, NOT
     `import yaml` which was the iter-1 typo):
     ```bash
     python -c "import tomli" || pip install tomli
     python -c "import tomli; data = tomli.loads(open('pyproject.toml').read()); assert 'coverage' in data['tool'], 'coverage tables not at top level'; print('OK')"
     ```
   The assertion `'coverage' in data['tool']` confirms the new
   `[tool.coverage.run]` and `[tool.coverage.report]` tables are
   top-level (not silently nested inside `[[tool.mypy.overrides]]`).
   Print `OK` on success; AssertionError on failed insertion.
5. **mypy regression smoke**: run `python -m mypy --version && python -m
   mypy . | head -20` and confirm output mentions `Success: no issues
   found` (or the existing pre-Task-17 baseline). If mypy errors
   appear with messages like `Section [tool.mypy.overrides] does not
   accept key 'source'`, the append landed inside the wrong table —
   undo the edit and retry following step 2 carefully.

- [ ] **Step 2: Install dev deps + smoke test**

```bash
python -m pip install -e ".[dev]"
python -m pytest --cov=skills/sbtdd/scripts --cov-report=term -q tests/test_models.py
```

Expected: pytest runs with coverage instrumentation; one test file completes.

- [ ] **Step 3: Verify + commit**

```bash
make verify
git add pyproject.toml
git commit -m "feat: add pytest-cov dev dep + coverage config (placeholder threshold)"
```

- [ ] **Step 9: Task close `chore: mark task 17 complete`**

---

### Task 18: Item G — Extend Makefile `verify` target (escenario G-1)

**Files:**
- Modify: `Makefile`

#### Green Phase

- [ ] **Step 1: Replace `Makefile` contents**

```makefile
.PHONY: test lint format typecheck coverage verify

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check .

format:
	python -m ruff format --check .

typecheck:
	python -m mypy .

coverage:
	python -m pytest --cov=skills/sbtdd/scripts --cov-report=term-missing tests/

verify: lint format typecheck coverage
```

Note (C1 iter 2 fix — caspar CRITICAL NF-A breach): `verify` does
NOT depend on `test` because `coverage` already runs `pytest` (with
`--cov` instrumentation). Including both would double-execute the
test suite, breaking NF-A budget (`make verify` runtime <= 160s).
The standalone `test:` target remains for dev workflow (`-v`
verbose, no coverage instrumentation overhead).

- [ ] **Step 2: Smoke test**

```bash
make verify
```

Expected: all 5 targets succeed (placeholder `fail_under=0` will not block coverage).

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "feat: extend Makefile verify target with coverage check (G-1)"
```

- [ ] **Step 9: Task close `chore: mark task 18 complete`**

---

### Task 19: Item G — Measure baseline + commit final threshold (escenario G-2)

**Files:**
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

#### Green Phase

- [ ] **Step 1: Measure baseline**

```bash
python -m pytest --cov=skills/sbtdd/scripts --cov-report=term-missing tests/ 2>&1 | tee /tmp/coverage-baseline.txt
```

Capture the final `TOTAL` line; the third column is the percentage.

- [ ] **Step 2: Compute threshold**

`threshold = floor(measured_pct) - 2`. Examples: 85% → 83; 92% → 90; 78% → 76.

- [ ] **Step 3: Update `pyproject.toml`**

Replace `fail_under = 0` with `fail_under = <computed_threshold>`.

- [ ] **Step 4: Smoke test threshold**

```bash
make verify
```

Expected: PASS (measured >= threshold by construction).

- [ ] **Step 5: Append CHANGELOG `[1.0.2]` baseline section**

Add to top of `CHANGELOG.md` (above `[1.0.1]`):

```markdown
## [1.0.2] - <ship-date>

### Per-module coverage baseline (Item G)

Measured 2026-05-XX during task 19 close. Threshold = `floor(baseline) - 2%`.

| Module | Coverage % |
|--------|------------|
| <module> | <pct> |
| ... | ... |

Final `--cov-fail-under` value: **<threshold>**.

Excludes (per `[tool.coverage.run].omit`):
- `skills/sbtdd/scripts/__init__.py` (package marker, no logic).
- `templates/*` (template files, not Python code).

Modules under 85% target eventual (v1.0.5+ raise candidates): <list>.
```

- [ ] **Step 6: Verify + commit**

```bash
make verify
git add pyproject.toml CHANGELOG.md
git commit -m "feat: set coverage threshold to <N>% (baseline + 2% slack)"
```

- [ ] **Step 9: Task close `chore: mark task 19 complete`**

---

## Methodology Activities (Orchestrator, post-tracks pre-pre-merge)

These are NOT plan tasks (no Red-Green-Refactor commits). They are orchestrator-driven exercises documented in CHANGELOG `[1.0.2]` Process notes.

### Activity E — P7 empirical proof-of-recovery (~15-30min)

Triggered after both Track Alpha + Track Beta close (all `[x]` in plan, state file `current_phase: "done"`):

1. Verify spec-behavior.md + plan-tdd-org.md exist in repo.

2. **Pre-flight spec_lint dry-run** (W5 iter 1 fix — balthasar
   pre-Activity-E gate to catch self-inflicted R1/R2/R4/R5 blocks
   before they cost wall-time on a doomed `/sbtdd spec` invocation).
   With Item C shipped (Tasks 7-14), `_run_magi_checkpoint2` will
   refuse to dispatch MAGI if THIS spec/plan fail lint. Pre-flight
   runs the lint OUT-OF-BAND so the operator can fix before
   triggering the gated path:

```bash
python -m skills.sbtdd.scripts.spec_lint sbtdd/spec-behavior.md
python -m skills.sbtdd.scripts.spec_lint planning/claude-plan-tdd-org.md
```

   Exit code 0 (clean) on both files = proceed. Exit code 1 (errors
   present) = STOP, fix the violations (most likely R1 escenario
   well-formed if hand-craft missed Given/When/Then bullets, or R5
   frontmatter docstring drift), commit the spec/plan fix, and
   re-run the dry-run before continuing. Warnings (R3 monotonic
   skip) are advisory — surface them but do not block.

3. Invoke `/sbtdd spec --resume-from-magi` from this Claude Code session:

```bash
python skills/sbtdd/scripts/run_sbtdd.py spec --resume-from-magi
```

4. Verify post-conditions:
   - No `/brainstorming` or `/writing-plans` subprocess spawn (observable via process tree or stderr breadcrumb).
   - MAGI Checkpoint 2 dispatched on existing artifacts.
   - State file `.claude/session-state.json` written with `plan_approved_at: <ts>` if verdict >= GO_WITH_CAVEATS.

4. Document result in CHANGELOG `[1.0.2]` Process notes:
   - Success / failure.
   - Wall-clock time.
   - Observable gaps.

### Activity D — Own-cycle cross-check dogfood (~30-45min)

Triggered after Activity E completes:

1. Set `magi_cross_check: true` in `.claude/plugin.local.md`:

```yaml
---
stack: python
magi_cross_check: true   # v1.0.2 dogfood
---
```

2. Run `/sbtdd pre-merge`:

```bash
python skills/sbtdd/scripts/run_sbtdd.py pre-merge
```

3. Capture artifacts:

```bash
ls .claude/magi-cross-check/iter*-*.json
```

4. Run telemetry script (Item A) on the artifacts:

```bash
python scripts/cross_check_telemetry.py --root .claude/magi-cross-check --format markdown > /tmp/v102-cross-check.md
cat /tmp/v102-cross-check.md
```

5. Document findings in CHANGELOG `[1.0.2]` Process notes:
   - Iter count Loop 2.
   - Cross-check decision distribution (KEEP / DOWNGRADE / REJECT counts).
   - Meta-reviewer agreement rate vs MAGI verdicts.
   - Observable gaps.

If Item D surfaces a production bug in cross-check path (R8 risk): abort cycle, escalate to user, evaluate scope (mini-fix in v1.0.2 if minimal vs new cycle v1.0.2.1). Manual fallback warm command per spec sec.6.4:

```bash
mkdir -p .claude/magi-runs/v102-loop2-iter1
{
  cat .claude/magi-runs/v102-loop2-iter1-header.md
  echo "---"
  cat sbtdd/spec-behavior.md
  echo "---"
  cat planning/claude-plan-tdd.md
} > .claude/magi-runs/v102-loop2-iter1-payload.md
python skills/magi/scripts/run_magi.py code-review \
  .claude/magi-runs/v102-loop2-iter1-payload.md \
  --model opus --timeout 900 \
  --output-dir .claude/magi-runs/v102-loop2-iter1
```

---

## Pre-merge gate sequencing

After Activities D + E:

1. Loop 1: `/requesting-code-review` cap=10, esperamos 1-2 iters convergence.
2. Loop 2: `/magi:magi` cap=5, with cross-check enabled (Item D toggle).
3. G2 binding fallback: if Loop 2 iter 3 does not converge clean, scope-trim — defer F + G to v1.0.3. D and E already executed, cannot defer.

## Finalization (Task 20 — orchestrator-only)

After pre-merge passes:

1. Run `/finishing-a-development-branch`.
2. Bump `plugin.json` + `marketplace.json` to `1.0.2`.
3. Append final CHANGELOG `[1.0.2]` sections (Added / Changed / Process notes / Deferred).
4. Tag `v1.0.2` + push (with explicit user authorization).
5. Memory write: `project_v102_shipped.md`.

---

## Process notes (iter 1 fix additions)

**I2/I4 — Coverage gate permissive window (Tasks 17 → 19):** between
Task 17 (which lands `[tool.coverage.report] fail_under = 0`
placeholder) and Task 19 (which sets the real threshold = `floor(baseline)
- 2%`), the `make verify` coverage check is structurally a no-op —
any coverage value passes the `>= 0` gate. This window spans Tasks 17,
18, and 19 (estimated 6-13h wall-time of Track Beta). It is
intentional: Task 17 isolates pyproject config wiring, Task 18 isolates
Makefile target wiring, Task 19 isolates baseline measurement +
threshold commitment. Splitting these gives clear narrative + atomic
commits per concern. The trade-off is the permissive window. Mitigation:
Track Beta MUST proceed Tasks 17 → 18 → 19 sequentially without
multi-day gap; if interrupted (e.g. quota exhaustion mid-Track-Beta),
resume MUST land Task 19 before the next track-close. Document this
constraint in `.claude/auto-run.json` audit trail when applicable.

**I5 — Task close checkbox edit pattern:** Task 1 step 9 explicitly
shows the checkbox edit pattern:

```bash
# Edit planning/claude-plan-tdd.md to mark Task N as [x]
git add planning/claude-plan-tdd.md
git commit -m "chore: mark task N complete"
```

Tasks 2-19 step 9 reference this pattern by writing `Task close
chore: mark task N complete`. The implicit convention is: open
`planning/claude-plan-tdd.md` (the post-Checkpoint-2 approved plan,
copied from this org file), find the `### Task N:` header, change its
top-level `- [ ]` checkbox to `- [x]`, then run the `git add ... &&
git commit -m "chore: mark task N complete"` pair. Subagents executing
the plan: this is non-negotiable — the chore commit MUST include the
`planning/claude-plan-tdd.md` diff, never just an empty commit. The
state file `.claude/session-state.json` advance happens automatically
via `/sbtdd close-task` if invoked, or manually otherwise.

---

## Self-Review

**Spec coverage:**

| Spec section | Plan task |
|--------------|-----------|
| 2.1 Item A | Tasks 1-5 |
| 2.2 Item B | Task 6 |
| 2.3 Item C | Tasks 7-14 |
| 2.4 Item D (methodology) | Activity D |
| 2.5 Item E (methodology) | Activity E |
| 2.6 Item F | Tasks 15-16 |
| 2.7 Item G | Tasks 17-19 |
| §4 Escenarios A-1..A-6 | Tasks 1-5 |
| §4 Escenarios B-1, B-2 | Task 6 |
| §4 Escenarios C-R1-1..R5-2, C-int-1, C-int-2, C-cli-1 | Tasks 8-14 |
| §4 Escenarios F-1..F-4 | Tasks 15-16 |
| §4 Escenarios G-1, G-2 | Tasks 18-19 |

All 26 escenarios covered. All 5 plan items covered with TDD cycles. D + E covered with methodology activity steps.

**Placeholder scan:** No INV-27 uppercase placeholder tokens, no `implement later`, no `add error handling` weasel words, no half-defined steps in plan text. All steps contain exact code or exact commands. The `<ship-date>`, `<measured-pct>`, `<computed_threshold>`, `<list>` markers in CHANGELOG section template are intentional fill-ins resolved at task 19 close (not plan placeholders).

**Type consistency:**
- `LintFinding` fields stable across Tasks 7-14 (file, line, rule, severity, message).
- `aggregate(root, cycle_pattern)` signature stable across Tasks 1-4.
- `format_markdown(report)` / `format_json(report)` accept `TelemetryReport` consistently.
- `_INTERACTIVE_SKILLS` and `_EXCLUDED_FILES` constants consistent across Tasks 15-16.
- `_INV27_RE` imported from `spec_cmd` in Task 11 matches `spec_cmd._INV27_RE` definition.

---

## Execution Handoff

Plan complete and saved to `planning/claude-plan-tdd-org.md`. Per the SBTDD methodology (CLAUDE.local.md §1 Flujo de especificacion), the next steps are:

1. **Manual review (Checkpoint 1)** of `planning/claude-plan-tdd-org.md` by the user.
2. **MAGI Checkpoint 2** evaluating spec + plan together (`/magi:magi` cap=3 G1 HARD).
3. Iterate plan based on MAGI findings, rewriting refined version to `planning/claude-plan-tdd.md`.
4. Once verdict >= GO_WITH_CAVEATS full, dispatch Track Alpha + Track Beta as 2 parallel subagents per `superpowers:dispatching-parallel-agents` + `superpowers:subagent-driven-development`.

The "Subagent-Driven vs Inline Execution" choice from the writing-plans skill is resolved by the SBTDD methodology: **subagent-driven is the project default** per `feedback_subagent_delegation.md` memory, with Track Alpha + Track Beta dispatched in parallel after MAGI Checkpoint 2 approval.
