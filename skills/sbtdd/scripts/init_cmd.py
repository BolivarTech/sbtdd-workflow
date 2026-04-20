#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""/sbtdd init -- atomic 5-phase bootstrap (sec.S.5.1).

Phases: 1 pre-flight deps, 2 arg resolution, 3 atomic generation,
4 smoke test, 5 report. Invariant all-or-nothing: abort at any phase
leaves the project intact (staging dir discarded on error).

Atomicity contract (MAGI Milestone C iter 1 Finding 2): every file
created during Phase 3a AND Phase 3b lands FIRST in a tempdir built
from ``tempfile.mkdtemp(prefix='sbtdd-init-')``. The dest_root is NOT
touched until Phase 4 smoke test (which runs against the tempdir)
passes. Phase 5 performs a single atomic relocation from tempdir to
dest_root. If Phase 4 fails, the tempdir is cleaned up and dest_root
remains byte-identical to its pre-invocation state -- satisfying
sec.S.5.1 all-or-nothing.

Honours INV-0 (global authority of ``~/.claude/CLAUDE.md``) and INV-12
(preconditions validated before any mutation).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

from config import load_plugin_local as load_plugin_local
from dependency_check import DependencyReport, check_environment
from errors import DependencyError, PreconditionError, ValidationError
from hooks_installer import merge as merge_hooks
from templates import expand

# Root of the plugin distribution (repo root when running from source).
# scripts/init_cmd.py is at skills/sbtdd/scripts/init_cmd.py, so repo root is
# four parents up.
_PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TEMPLATES_DIR = _PLUGIN_ROOT / "templates"


#: Stack-specific verification commands written into CLAUDE.local.md (sec.S.4.2).
_VERIF_CMDS: dict[str, tuple[str, ...]] = {
    "rust": (
        "cargo nextest run",
        "cargo audit",
        "cargo clippy --all-targets -- -D warnings",
        "cargo fmt --check",
    ),
    "python": (
        "python -m pytest",
        "python -m ruff check .",
        "python -m ruff format --check .",
        "python -m mypy .",
    ),
    "cpp": ("ctest --output-junit ctest-junit.xml",),
}


def _build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for ``/sbtdd init``."""
    p = argparse.ArgumentParser(prog="sbtdd init")
    p.add_argument("--stack", choices=("rust", "python", "cpp"), default=None)
    p.add_argument("--author", type=str, default=None)
    p.add_argument("--error-type", type=str, default=None)
    p.add_argument(
        "--conftest-mode",
        choices=("merge", "replace", "skip"),
        default="merge",
    )
    p.add_argument("--force", action="store_true")
    p.add_argument("--project-root", type=Path, default=Path.cwd())
    p.add_argument(
        "--plugins-root",
        type=Path,
        default=Path.home() / ".claude" / "plugins",
    )
    return p


def _resolve_args(ns: argparse.Namespace) -> argparse.Namespace:
    """Prompt for missing stack/author/error_type when a TTY is attached.

    In non-interactive mode every missing required flag raises
    :class:`ValidationError` so the caller maps to exit 1.
    """
    if ns.stack is None:
        if sys.stdin.isatty():
            raw = input("Stack (rust/python/cpp): ").strip()
            if raw not in ("rust", "python", "cpp"):
                raise ValidationError(f"stack must be rust, python, or cpp; got '{raw}'")
            ns.stack = raw
        else:
            raise ValidationError("--stack is required in non-interactive mode")
    if ns.author is None:
        if sys.stdin.isatty():
            ns.author = input("Author name: ").strip() or "Unknown"
        else:
            raise ValidationError("--author is required in non-interactive mode")
    if ns.stack == "rust" and ns.error_type is None:
        if sys.stdin.isatty():
            ns.error_type = input("Error type name (e.g. MyErr): ").strip() or "Error"
        else:
            raise ValidationError("--error-type is required for --stack rust")
    return ns


def _make_staging_dir() -> Path:
    """Create a tempdir mirroring the dest_root tree during init.

    All Phase 3a + Phase 3b writes land here; dest_root is untouched
    until Phase 5 relocation after Phase 4 smoke-test succeeds.
    """
    td = Path(tempfile.mkdtemp(prefix="sbtdd-init-"))
    (td / ".claude").mkdir()
    (td / "sbtdd").mkdir()
    (td / "planning").mkdir()
    return td


def _phase3a_generate(ns: argparse.Namespace, staging: Path, dest_root: Path) -> None:
    """Write CLAUDE.local.md + .claude/plugin.local.md into STAGING (not dest_root).

    Pre-flight check against dest_root for existing CLAUDE.local.md runs
    here (requires ``--force`` to overwrite).
    """
    if (dest_root / "CLAUDE.local.md").exists() and not ns.force:
        raise PreconditionError("CLAUDE.local.md already exists; use --force to overwrite")
    tpl_c = (_TEMPLATES_DIR / "CLAUDE.local.md.template").read_text(encoding="utf-8")
    ctx = {
        "author": ns.author,
        "error_type": ns.error_type or "Error",
        "stack": ns.stack,
        "verification_commands": "\n".join(_VERIF_CMDS[ns.stack]),
    }
    (staging / "CLAUDE.local.md").write_text(expand(tpl_c, ctx), encoding="utf-8")
    tpl_p = (_TEMPLATES_DIR / "plugin.local.md.template").read_text(encoding="utf-8")
    (staging / ".claude" / "plugin.local.md").write_text(expand(tpl_p, ctx), encoding="utf-8")


def _settings_payload() -> dict[str, Any]:
    """Return the three-hook TDD-Guard payload merged into settings.json."""
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|MultiEdit|TodoWrite",
                    "hooks": [{"type": "command", "command": "tdd-guard"}],
                }
            ],
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [{"type": "command", "command": "tdd-guard"}],
                }
            ],
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "tdd-guard"}]}],
        }
    }


def _install_conftest_staged(staging: Path, dest_root: Path, mode: str) -> None:
    """Write the Python TDD-Guard conftest into staging per --conftest-mode."""
    target = staging / "conftest.py"
    existing_target = dest_root / "conftest.py"
    tpl = (_TEMPLATES_DIR / "conftest.py.template").read_text(encoding="utf-8")
    if mode == "replace" and existing_target.exists():
        target.write_text(tpl, encoding="utf-8")
        return
    if mode == "merge" and existing_target.exists():
        existing = existing_target.read_text(encoding="utf-8")
        start = "# --- SBTDD TDD-Guard reporter START ---"
        end = "# --- SBTDD TDD-Guard reporter END ---"
        if start in existing and end in existing:
            pre, rest = existing.split(start, 1)
            _, post = rest.split(end, 1)
            target.write_text(pre + tpl + post, encoding="utf-8")
            return
        target.write_text(existing.rstrip("\n") + "\n\n" + tpl, encoding="utf-8")
        return
    target.write_text(tpl, encoding="utf-8")


def _phase3b_install(ns: argparse.Namespace, staging: Path, dest_root: Path) -> None:
    """Write settings.json, spec-base, planning/.gitkeep, .gitignore, conftest to STAGING.

    Existing user content in dest_root is READ to preserve overrides but
    OUTPUT lands in staging only. Phase 5 relocation is what makes these
    changes visible in dest_root.
    """
    staged_settings = staging / ".claude" / "settings.json"
    existing_settings = dest_root / ".claude" / "settings.json"
    merge_hooks(existing_settings, _settings_payload(), staged_settings)

    staged_spec_base = staging / "sbtdd" / "spec-behavior-base.md"
    if not (dest_root / "sbtdd" / "spec-behavior-base.md").exists():
        tpl = (_TEMPLATES_DIR / "spec-behavior-base.md.template").read_text(encoding="utf-8")
        staged_spec_base.write_text(tpl, encoding="utf-8")

    staged_gitkeep = staging / "planning" / ".gitkeep"
    staged_gitkeep.write_text("", encoding="utf-8")

    staged_gi = staging / ".gitignore"
    frag = (_TEMPLATES_DIR / "gitignore.fragment").read_text(encoding="utf-8")
    existing_gi = dest_root / ".gitignore"
    existing = existing_gi.read_text(encoding="utf-8") if existing_gi.exists() else ""
    new_lines = [line for line in frag.splitlines() if line and line not in existing]
    merged = existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n" if new_lines else existing
    staged_gi.write_text(merged, encoding="utf-8")

    if ns.stack == "python" and ns.conftest_mode != "skip":
        _install_conftest_staged(staging, dest_root, ns.conftest_mode)


def _phase4_smoke_test(staging: Path) -> None:
    """Validate the STAGED tree before Phase 5 relocation.

    Runs exclusively against staging -- dest_root is untouched if this raises.
    Two checks:

    1. ``.claude/settings.json`` parses as JSON and contains the three
       required hook events (PreToolUse, UserPromptSubmit, SessionStart).
    2. ``.claude/plugin.local.md`` is consumed by :func:`config.load_plugin_local`
       without raising.

    Raises:
        PreconditionError: settings.json malformed or missing hooks.
        ValidationError: plugin.local.md frontmatter invalid (propagated from
            ``load_plugin_local``).
    """
    settings = staging / ".claude" / "settings.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PreconditionError(f"smoke test: settings.json not parseable: {exc}") from exc
    for event in ("PreToolUse", "UserPromptSubmit", "SessionStart"):
        if event not in data.get("hooks", {}):
            raise PreconditionError(f"smoke test: hook '{event}' missing")
    plugin_local = staging / ".claude" / "plugin.local.md"
    load_plugin_local(plugin_local)


def _phase5_relocate(staging: Path, dest_root: Path) -> list[Path]:
    """Relocate the staged tree into ``dest_root`` with best-effort atomicity.

    Copies each staged file into its destination location under
    ``dest_root``. True cross-volume atomicity would require
    ``os.rename`` of the parent directory, which fails across volumes
    and is unreliable on Windows when ``dest_root`` already exists --
    so we implement "best effort atomicity with rollback": on any
    per-file copy failure (disk full, permission denied on the N-th
    file, etc.), the helper removes every file it already copied plus
    every subdirectory it freshly created to host them, then re-raises
    the original exception. A subsequent ``/sbtdd init`` invocation
    therefore sees a clean ``dest_root`` and can retry cleanly. Fix for
    MAGI Loop 2 iter 1 Finding 3 (file rollback) + iter 2 W_iter2_1
    (empty-directory rollback).

    Rollback guarantees:
      - Every path in the returned ``created`` list up to the failure
        point is removed via ``Path.unlink(missing_ok=True)``.
      - Every directory in the tracked ``created_dirs`` list -- the
        subdirectories the copy itself materialised via
        ``parent.mkdir(parents=True)`` -- is removed leaf-to-root via
        ``os.rmdir``. Directories that pre-existed are NOT touched
        (they are not tracked). ``os.rmdir`` is deliberately strict
        (fails if the directory is non-empty) so the rollback can
        only delete what the copy itself created.
      - Rollback errors (e.g. unlink fails because a concurrent process
        grabbed the file, or rmdir fails because the user dropped a
        file into a tracked dir during the copy) are swallowed; the
        original copy failure is what the caller cares about and is
        re-raised unchanged.

    Args:
        staging: Root of the prepared tree (typically a tempdir).
        dest_root: Final destination; must exist and be writable.

    Returns:
        List of destination paths that were created, in copy order.
        On exception this list is NOT returned; the rollback handler
        consumes it internally before re-raising.

    Raises:
        OSError: Any filesystem failure during the copy loop is
            propagated unchanged after rollback completes.
    """
    staged_files = [p for p in staging.rglob("*") if p.is_file()]
    created: list[Path] = []
    created_dirs: list[Path] = []
    try:
        for src in staged_files:
            rel = src.relative_to(staging)
            target = dest_root / rel
            _mkdir_tracked(target.parent, dest_root, created_dirs)
            shutil.copy2(src, target)
            created.append(target)
    except Exception:
        _rollback_partial_copy(created, created_dirs)
        raise
    return created


def _mkdir_tracked(directory: Path, dest_root: Path, created_dirs: list[Path]) -> None:
    """Create ``directory`` and record every ancestor freshly made under dest_root.

    Acts like ``directory.mkdir(parents=True, exist_ok=True)`` but also
    appends to ``created_dirs`` every directory from ``directory`` up
    toward (but not including) ``dest_root`` that did NOT exist prior
    to the call. The ordering preserves descendants-AFTER-ancestors
    so the rollback handler can walk the list in reverse and call
    ``os.rmdir`` leaf-to-root without violating the "only empty dirs
    can be removed" contract.
    """
    # Walk from ``directory`` up to ``dest_root`` collecting missing ancestors.
    # Stop at ``dest_root`` OR at the filesystem root (where ``cursor.parent``
    # returns ``cursor``); the latter only triggers if ``directory`` is not
    # under ``dest_root`` (programmer error) -- we fall back to no tracking
    # rather than looping forever.
    pending: list[Path] = []
    cursor = directory
    while cursor != dest_root:
        if cursor.parent == cursor:
            return  # reached FS root without hitting dest_root; bail safely
        if cursor.exists():
            break
        pending.append(cursor)
        cursor = cursor.parent
    # Parents-first so inner dirs can be mkdir()d after their parent exists.
    for path in reversed(pending):
        path.mkdir(exist_ok=False)
        created_dirs.append(path)


def _rollback_partial_copy(copied: list[Path], created_dirs: list[Path]) -> None:
    """Remove every file + empty subdir created during a failed relocate.

    Helper for :func:`_phase5_relocate`: the rollback MUST NOT raise --
    doing so would mask the original copy failure (which carries the
    useful diagnostic like "disk full" or "permission denied"). Unlink
    failures (e.g. another process has the file open on Windows) are
    swallowed because the caller will observe them on the next
    ``/sbtdd init`` retry via the Phase 1 dependency check.

    Directory removal uses ``os.rmdir`` (strict: fails if non-empty)
    and walks ``created_dirs`` in reverse so leaves are removed before
    their parents. This guarantees we only remove directories the copy
    itself created; any dir the user may have populated concurrently
    would trigger ``OSError`` on ``rmdir`` which we swallow.
    """
    import os as _os

    for path in copied:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    for directory in reversed(created_dirs):
        try:
            _os.rmdir(directory)
        except OSError:
            pass


def _cleanup_staging(staging: Path) -> None:
    """Delete the staging tempdir. Silent on OSError to avoid masking aborts."""
    try:
        shutil.rmtree(staging, ignore_errors=True)
    except OSError:
        pass


def _phase5_report(
    ns: argparse.Namespace,
    created: list[Path],
    report: DependencyReport,
) -> None:
    """Write the human-readable Phase 5 summary to stdout."""
    del ns  # present for future extension; unused today.
    lines: list[str] = [""]
    for chk in report.checks:
        lines.append(f"[{chk.status.lower()}] {chk.name} - {chk.detail}")
    lines.append("")
    lines.append("Created:")
    for p in created:
        lines.append(f"  {p}")
    lines.append("")
    lines.append("Next steps:")
    lines.append("  1. Edit sbtdd/spec-behavior-base.md with the feature requirements.")
    lines.append("  2. Run /sbtdd spec to generate the TDD plan.")
    sys.stdout.write("\n".join(lines) + "\n")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the init subcommand.

    Args:
        argv: Command-line arguments (None uses sys.argv).

    Returns:
        Process exit code (0 on success).

    Raises:
        ValidationError: Missing required flags in non-interactive mode.
        DependencyError: Pre-flight check aggregated failures.
        PreconditionError: Phase 3a/3b/4 detected a blocking condition.
    """
    parser = _build_parser()
    ns = parser.parse_args(argv)
    ns = _resolve_args(ns)
    report = check_environment(ns.stack, ns.project_root, ns.plugins_root)
    if not report.ok():
        sys.stderr.write(report.format_report() + "\n")
        raise DependencyError(f"{len(report.failed())} pre-flight checks failed")
    staging = _make_staging_dir()
    try:
        _phase3a_generate(ns, staging, ns.project_root)
        _phase3b_install(ns, staging, ns.project_root)
        _phase4_smoke_test(staging)
        created = _phase5_relocate(staging, ns.project_root)
    except Exception:
        _cleanup_staging(staging)
        raise
    _cleanup_staging(staging)
    _phase5_report(ns, created, report)
    return 0


run = main
