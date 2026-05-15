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
import os
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
# v1.0.8 T5: settings.json fixture path resolved at module load to
# surface missing-fixture errors at collection time instead of test
# runtime.
_FIXTURE_SETTINGS_JSON = _FIXTURE_DIR / "dot-claude-settings.json"
# Subprocess timeout for the entire ``auto --parallel`` invocation.
# v1.0.8 A3 shrunk from 600s to 120s -- the stub gate (Pillar A1)
# eliminates the upstream LLM-dispatch cost that drove the v1.0.7
# 600s budget. Loop 2 iter-1 Cas-W5 fix: raised 60 -> 120 to tolerate
# CI runner variance (empirical local wall-time ~15s; 120s gives
# 8x headroom for slow CI workers without sacrificing fast-fail).
_AUTO_TIMEOUT_S = 120


def _toolchain_available() -> bool:
    """Return ``True`` when ``pytest``/``ruff``/``mypy`` are importable as modules.

    v1.0.7 T3 dogfood empirical fix: worker close-phase invokes these via
    ``sys.executable -m <tool>`` (NOT bare names). The dev env must have
    them pip-installed for the active Python; bare PATH presence is not
    required. Skips when any tool is missing rather than producing a
    misleading test failure.
    """
    import importlib.util

    return all(importlib.util.find_spec(t) is not None for t in ("pytest", "ruff", "mypy"))


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
    # v1.0.8 B1: materialize dot-claude-settings.json as
    # .claude/settings.json so the staged project has explicit
    # permissions for the implementer skill's tool calls (writes to
    # scratch/, tests/, src/ + bash invocations for pytest/ruff/mypy).
    # Doble defensa: even if the v1.0.8 A1 stub gate is bypassed in a
    # future test variant, the fixture is "less broken" upstream.
    shutil.copy(_FIXTURE_SETTINGS_JSON, claude_dir / "settings.json")
    # v1.0.8 T4: pre-create .claude/tdd-guard/data so the auto preflight
    # dependency_check.check_tdd_guard_data_dir succeeds without a
    # writable-probe roundtrip race. Required for the stubbed e2e path
    # to reach the worker chicken-and-egg surface.
    (claude_dir / "tdd-guard" / "data").mkdir(parents=True, exist_ok=True)
    # v1.0.8 T4: stage a .gitignore that excludes runtime artifacts
    # produced by the auto cycle (.claude/, __pycache__/, cache dirs)
    # so phase 4 checklist's git status clean check passes. Renamed on
    # copy because shipping a literal .gitignore in the fixture dir
    # could match this repo's own ignore rules and skip files.
    shutil.copy(_FIXTURE_DIR / "dot-gitignore", dest / ".gitignore")
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


def _assert_state_done(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert session-state.json reports phase=done."""
    state = json.loads((project / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_phase"] == "done", (
        f"v1.0.8 A3-2 expected current_phase=='done'; got {state['current_phase']!r}.{diagnostic}"
    )


def _assert_plan_fully_flipped(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert all plan checkboxes are [x]."""
    import re

    plan_text = (project / "planning" / "claude-plan-tdd.md").read_text(encoding="utf-8")
    assert not re.search(r"^[ \t]*- \[ \]", plan_text, re.MULTILINE), (
        f"v1.0.8 A3-2 expected all plan checkboxes flipped to [x]; "
        f"open '- [ ]' line(s) remain.{diagnostic}"
    )


def _assert_sidecars_valid(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2/A3-3 helper: assert sidecars exist with valid verify_chain.

    Per iter-2 carry-forward Cas-W10: ``>=4`` entries (extensible) +
    presence check for the 4 known sec.0.1 tools (pytest, ruff,
    mypy). Future sec.0.1 extensions MUST NOT break this assertion.
    Per iter-2 carry-forward Cas-W5+Mel-W3: tool detection via
    substring-anywhere match (not positional cmd[2]) for robustness.
    """
    workers_dir = project / ".claude" / "auto-run-workers"
    assert workers_dir.is_dir(), f"v1.0.8 A3-2 missing {workers_dir}.{diagnostic}"
    sidecars = list(workers_dir.glob("*-verify.json"))
    assert sidecars, f"v1.0.8 A3-2 expected >=1 sidecar in {workers_dir}.{diagnostic}"
    # The 4 known sec.0.1 tools that MUST appear in the chain
    # (ruff appears twice: ruff check + ruff format --check; but
    # the unique tool module names are {pytest, ruff, mypy}).
    expected_tools = {"pytest", "ruff", "mypy"}
    for sc in sidecars:
        payload = json.loads(sc.read_text(encoding="utf-8"))
        chain = payload.get("verify_chain")
        assert isinstance(chain, list) and len(chain) >= 4, (
            f"v1.0.8 A3-3 expected verify_chain with >=4 entries in {sc.name}.{diagnostic}"
        )
        # Substring-anywhere tool detection.
        tools_in_chain: set[str] = set()
        for entry in chain:
            cmd = entry.get("cmd")
            if not isinstance(cmd, list):
                continue
            cmd_str = " ".join(str(p) for p in cmd)
            for tool in expected_tools:
                if tool in cmd_str:
                    tools_in_chain.add(tool)
        missing = expected_tools - tools_in_chain
        assert not missing, (
            f"v1.0.8 A3-3 expected tools {expected_tools} in chain "
            f"of {sc.name}; missing {missing}; "
            f"observed {tools_in_chain}.{diagnostic}"
        )
        for entry in chain:
            assert entry.get("rc") == 0, (
                f"v1.0.8 A3-3 expected all sec.0.1 tools rc=0 in "
                f"{sc.name}; got {entry.get('rc')}.{diagnostic}"
            )


def _assert_audit_finished_success(project: Path, diagnostic: str) -> None:
    """v1.0.8 A3-2 helper: assert auto-run.json reports finished + success."""
    audit = json.loads((project / ".claude" / "auto-run.json").read_text(encoding="utf-8"))
    assert audit.get("auto_finished_at") is not None, (
        f"v1.0.8 A3-2 expected auto_finished_at non-null.{diagnostic}"
    )
    assert audit.get("status") == "success", (
        f"v1.0.8 A3-2 expected status=='success'; got {audit.get('status')!r}.{diagnostic}"
    )


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="v1.0.7 A3 mandatory on Windows; POSIX deferred to v1.0.8",
)
@pytest.mark.skipif(
    not _toolchain_available(),
    reason=(
        "Worker close-phase requires pytest/ruff/mypy importable as modules; "
        "skipping when one or more is missing (orthogonal to A1/A2 surface)."
    ),
)
def test_auto_parallel_e2e_chicken_and_egg_closed(tmp_path: Path) -> None:
    """v1.0.8 A3 dogfood: ``auto --parallel`` workers complete in 60s.

    Empirical validation that v1.0.7 A1 POSIX PTY + A2 Windows hybrid
    Option B-W3 fallback close the chicken-and-egg surface confirmed
    in v1.0.6 own-cycle (workers spawned via ``subprocess.PIPE`` with
    no TTY hanging on ``close-phase /verification-before-completion``).

    v1.0.8 closes the empirical gap: the v1.0.7 600s timeout was caused
    by an upstream ``claude -p /test-driven-development`` hang in the
    fixture cwd (documented in CLAUDE.md "Known upstream limitations").
    The subprocess env carries ``SBTDD_E2E_STUB_DISPATCH=1`` so
    ``superpowers_dispatch.invoke_skill`` short-circuits the
    ``/test-driven-development`` + ``/systematic-debugging`` dispatches
    to a synthetic ``SkillResult(rc=0)`` -- workers reach the actual
    chicken-and-egg surface (`_run_verification` worker-mode bypass via
    sec.0.1 chain) without the upstream LLM-dispatch hang.

    Strict happy-path assertions (per Q4'=a+):

    - subprocess returncode == 0
    - session-state.json current_phase == "done"
    - planning/claude-plan-tdd.md has zero ``- [ ]`` line-start checkboxes
    - .claude/auto-run-workers/ contains >= 1 sidecar with verify_chain
      of exactly 4 entries each rc=0
    - .claude/auto-run.json auto_finished_at non-null + status=="success"
    """
    project = tmp_path / "project"
    project.mkdir()
    seed_sha = _stage_fixture(project)
    _seed_session_state(project, seed_sha)

    # v1.0.8 A3 Green: stub gate requires BOTH env vars per cc30d2a
    # T1+T3 follow-up fix (AND-gate prevents accidental production leak).
    env = os.environ.copy()
    env["SBTDD_E2E_STUB_DISPATCH"] = "1"
    env["SBTDD_E2E_TEST_RUNNER"] = "1"

    proc = subprocess.run(
        [sys.executable, str(_RUN_SBTDD), "auto", "--parallel"],
        cwd=str(project),
        env=env,
        capture_output=True,
        text=True,
        timeout=_AUTO_TIMEOUT_S,
    )
    diagnostic = _diagnostic_message(proc.returncode, proc.stdout, proc.stderr)
    assert proc.returncode == 0, f"v1.0.8 A3-1 expected rc=0; got rc={proc.returncode}.{diagnostic}"
    _assert_state_done(project, diagnostic)
    _assert_plan_fully_flipped(project, diagnostic)
    _assert_sidecars_valid(project, diagnostic)
    _assert_audit_finished_success(project, diagnostic)


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
        "dot-claude-settings.json",
    )
    missing = [name for name in expected if not (_FIXTURE_DIR / name).exists()]
    assert not missing, f"missing fixture files: {missing}"


def test_run_sbtdd_entrypoint_exists() -> None:
    """Sanity check: the run_sbtdd.py entrypoint resolved by the test exists."""
    assert _RUN_SBTDD.exists(), f"run_sbtdd.py not found at {_RUN_SBTDD}"
