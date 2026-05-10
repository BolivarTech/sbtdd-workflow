#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-09
"""v1.0.7 A3 — F-A2 dogfood empirical end-to-end test for ``auto --parallel``.

Stages the ``tests/fixtures/parallel-e2e/`` synthetic project into a
temporary git repo, then invokes ``python skills/sbtdd/scripts/run_sbtdd.py
auto --parallel`` as a real subprocess and asserts the chicken-and-egg
surface (workers spawned via :func:`auto_cmd._dispatch_tracks_concurrent`
hanging on ``close-phase /verification-before-completion``) is closed
empirically.

Skip rules:

- POSIX: skipped per Q1'=a / NF-C — Windows is the mandatory dev env;
  POSIX validation deferred to v1.0.8 or CI.
- Missing bare ``ruff`` / ``mypy`` on PATH: skipped — worker close-phase
  invokes those binaries by bare name (see
  :func:`close_phase_cmd._run_verification` worker-mode block); without
  them on PATH the worker fails for a reason orthogonal to the
  chicken-and-egg surface this test validates.

Acceptance (Windows happy path):

- ``returncode == 0`` from ``auto --parallel`` subprocess.
- ``.claude/auto-run.json`` exists with non-null ``auto_started_at`` and
  ``schema_version``.
- Plan checkboxes all flipped (``- [ ]`` not present in
  ``planning/claude-plan-tdd.md`` after the cycle).
- ``.claude/session-state.json`` ``current_phase == "done"``.
- ``.claude/auto-run-workers/`` directory contains at least one sidecar
  matching ``<pid>-<monotonic_ns>-<uuid8>-verify.json`` produced by
  :func:`close_phase_cmd._persist_worker_verify_evidence`.
- Each sidecar contains a valid ``verify_chain`` JSON list (per-tool
  ``cmd``/``rc``/``stdout``/``stderr`` records).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Plan T3: pytest.mark.timeout(700) is informational; pytest-timeout is
# not installed in this project. Real subprocess timeout enforcement is
# done via subprocess.run(timeout=...) inside the test body.
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow,
    pytest.mark.timeout(700),
]


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "parallel-e2e"
_REPO_ROOT = Path(__file__).resolve().parents[1]
_RUN_SBTDD = _REPO_ROOT / "skills" / "sbtdd" / "scripts" / "run_sbtdd.py"
# Subprocess timeout for the entire ``auto --parallel`` invocation.
# Generous enough for real worker close-phase chains (~3 min/worker on a
# warm ruff/mypy cache) but bounded so a hang surfaces as a test failure
# rather than blocking the suite indefinitely.
_AUTO_TIMEOUT_S = 600


def _toolchain_available() -> bool:
    """Return ``True`` when bare ``pytest``/``ruff``/``mypy`` are on PATH.

    Worker close-phase invokes these by bare name (no ``python -m``
    prefix), so the dev env must expose them as standalone binaries for
    the worker chain to complete. Missing any one of them produces a
    skip rather than a misleading test failure.
    """
    return all(shutil.which(b) is not None for b in ("pytest", "ruff", "mypy"))


def _git_init_with_identity(root: Path) -> None:
    """Initialise a git repo with a tester identity + initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True, capture_output=True)
    for key, value in (
        ("user.email", "tester@example.com"),
        ("user.name", "Tester"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=str(root),
            check=True,
            capture_output=True,
        )
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: seed v1.0.7 a3 fixture", "-q"],
        cwd=str(root),
        check=True,
        capture_output=True,
    )


def _stage_fixture(dest: Path) -> str:
    """Copy fixture project into ``dest``; return seed commit SHA."""
    # Copy fixture project files into dest.
    shutil.copytree(_FIXTURE_DIR, dest, dirs_exist_ok=True)
    # planning/claude-plan-tdd.md is the canonical plan path the
    # orchestrator parses; mirror plan-fixture.md into that location.
    planning = dest / "planning"
    planning.mkdir(exist_ok=True)
    shutil.copy(dest / "plan-fixture.md", planning / "claude-plan-tdd.md")
    # sbtdd/spec-behavior.md is required by phase 1 preflight in some
    # configurations; write the synthetic spec into the canonical path.
    sbtdd_dir = dest / "sbtdd"
    sbtdd_dir.mkdir(exist_ok=True)
    shutil.copy(dest / "spec-fixture.md", sbtdd_dir / "spec-behavior-base.md")
    shutil.copy(dest / "spec-fixture.md", sbtdd_dir / "spec-behavior.md")
    # Seed plugin.local.md from the project's valid-python fixture so
    # PluginConfig loads a known-good Python stack baseline.
    claude_dir = dest / ".claude"
    claude_dir.mkdir(exist_ok=True)
    shutil.copy(
        Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md",
        claude_dir / "plugin.local.md",
    )
    # scratch/ holds the per-task touch targets declared in plan-fixture.md.
    (dest / "scratch").mkdir(exist_ok=True)
    _git_init_with_identity(dest)
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(dest),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return sha


def _seed_session_state(dest: Path, seed_sha: str) -> None:
    """Write a minimal approved-plan ``.claude/session-state.json``.

    ``auto`` requires ``plan_approved_at`` non-null + ``current_phase``
    set to ``red`` (or ``done`` to short-circuit) so the
    "Excepcion bajo plan aprobado" contract is in effect.
    """
    state = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "1",
        "current_task_title": "Create scratch alpha",
        "current_phase": "red",
        "phase_started_at_commit": seed_sha,
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": "2026-05-09T00:00:00Z",
    }
    (dest / ".claude" / "session-state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8"
    )


def _diagnostic_message(rc: int, stdout: str, stderr: str) -> str:
    """Format a multi-line diagnostic for failure-mode reports."""
    return (
        f"\n--- auto --parallel rc={rc} ---\n"
        f"--- STDOUT (last 4KB) ---\n{stdout[-4096:]}\n"
        f"--- STDERR (last 4KB) ---\n{stderr[-4096:]}\n"
    )


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="v1.0.7 A3 mandatory on Windows; POSIX deferred to v1.0.8",
)
@pytest.mark.skipif(
    not _toolchain_available(),
    reason=(
        "Worker close-phase requires bare pytest/ruff/mypy on PATH; "
        "skipping when one or more is missing (orthogonal to A1/A2 surface)."
    ),
)
def test_auto_parallel_e2e_chicken_and_egg_closed(tmp_path: Path) -> None:
    """v1.0.7 A3 dogfood: ``auto --parallel`` completes end-to-end on Windows.

    Empirical validation that A1 POSIX PTY allocation + A2 Windows hybrid
    Option B-W3 fallback close the chicken-and-egg surface confirmed in
    v1.0.6 own-cycle (workers spawned via ``subprocess.PIPE`` with no TTY
    hanging on ``close-phase /verification-before-completion``).

    The test runs ``auto --parallel`` as a real subprocess against the
    staged ``tests/fixtures/parallel-e2e/`` synthetic project; on Windows
    workers MUST take the v1.0.7 A2 worker-mode bypass path
    (``SBTDD_AUTO_PARALLEL_WORKER=1`` env -> shell-direct sec.0.1 chain
    in :func:`close_phase_cmd._run_verification`) so close-phase completes
    without invoking the interactive skill.

    Outcome semantics (per plan T3 escalation rubric):

    - PASS: chicken-and-egg empirically closed end-to-end.
    - FAIL with hang at ~600s: A2 worker-mode bypass NOT firing OR
      ``SBTDD_AUTO_PARALLEL_WORKER`` env var not propagated. Diagnose
      worker stderr.
    - FAIL with non-zero rc: orthogonal failure (missing dep, plan
      parser, sidecar collision, MAGI/superpowers unavailable in
      pre-merge). Read stderr to identify.
    """
    project = tmp_path / "project"
    project.mkdir()
    seed_sha = _stage_fixture(project)
    _seed_session_state(project, seed_sha)

    proc = subprocess.run(
        [sys.executable, str(_RUN_SBTDD), "auto", "--parallel"],
        cwd=str(project),
        capture_output=True,
        text=True,
        timeout=_AUTO_TIMEOUT_S,
    )
    diagnostic = _diagnostic_message(proc.returncode, proc.stdout, proc.stderr)

    # Acceptance #1: subprocess returncode 0.
    assert proc.returncode == 0, f"auto --parallel exited non-zero{diagnostic}"

    # Acceptance #2: .claude/auto-run.json exists and is well-formed.
    auto_run = project / ".claude" / "auto-run.json"
    assert auto_run.exists(), f"auto-run.json missing{diagnostic}"
    audit = json.loads(auto_run.read_text(encoding="utf-8"))
    assert audit.get("auto_started_at"), f"auto_started_at missing{diagnostic}"
    assert audit.get("schema_version"), f"schema_version missing{diagnostic}"

    # Acceptance #3: plan checkboxes all flipped to [x].
    plan_text = (project / "planning" / "claude-plan-tdd.md").read_text(encoding="utf-8")
    assert "- [ ]" not in plan_text, (
        f"plan still has open checkboxes (workers did not advance state){diagnostic}"
    )

    # Acceptance #4: state file says done.
    state = json.loads((project / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_phase"] == "done", (
        f"current_phase={state['current_phase']!r} (expected 'done'){diagnostic}"
    )

    # Acceptance #5: per-worker sidecars present under .claude/auto-run-workers/.
    sidecar_dir = project / ".claude" / "auto-run-workers"
    assert sidecar_dir.exists(), f"auto-run-workers/ missing{diagnostic}"
    sidecars = list(sidecar_dir.glob("*-verify.json"))
    assert sidecars, f"no sidecars produced (worker close-phase did not run){diagnostic}"

    # Acceptance #6: each sidecar contains a valid verify_chain.
    for sidecar in sidecars:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        chain = payload.get("verify_chain")
        assert isinstance(chain, list) and chain, (
            f"sidecar {sidecar.name} verify_chain malformed: {payload!r}{diagnostic}"
        )
        for entry in chain:
            assert "cmd" in entry and "rc" in entry, (
                f"sidecar {sidecar.name} entry missing cmd/rc: {entry!r}"
            )

    # POSIX-only INV-16 evidence assertion (skipped here since Windows
    # uses subprocess.PIPE in the hybrid Option B-W3 path so isatty
    # observes False; the chicken-and-egg fix is the SBTDD_AUTO_PARALLEL_WORKER
    # env var bypass, not isatty).
    if sys.platform != "win32":
        # Inspect first sidecar's pytest stdout for the marker.
        first = json.loads(sidecars[0].read_text(encoding="utf-8"))
        pytest_entries = [e for e in first["verify_chain"] if e.get("cmd", [None])[0] == "pytest"]
        if pytest_entries:
            stdout = pytest_entries[0].get("stdout", "")
            assert "isatty=True" in stdout, (
                f"POSIX worker missing isatty=True marker; got: {stdout[-512:]}"
            )


def test_fixture_files_present() -> None:
    """Sanity check: fixture files exist at expected paths.

    Runs unconditionally on all platforms so the fixture itself is
    audited even when the e2e dogfood test skips. Catches stale fixture
    pruning by accident.
    """
    expected = (
        "spec-fixture.md",
        "pyproject.toml",
        "src/sample.py",
        "tests/test_sample.py",
        "Makefile",
        "plan-fixture.md",
    )
    missing = [name for name in expected if not (_FIXTURE_DIR / name).exists()]
    assert not missing, f"missing fixture files: {missing}"


def test_run_sbtdd_entrypoint_exists() -> None:
    """Sanity check: the run_sbtdd.py entrypoint resolved by the test exists."""
    assert _RUN_SBTDD.exists(), f"run_sbtdd.py not found at {_RUN_SBTDD}"
