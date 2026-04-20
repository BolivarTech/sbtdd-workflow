# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for reporters.ctest_reporter (Task 17)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "ctest-junit"


def test_parse_junit_all_passed():
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "all_passed.xml")
    assert doc.reason == "passed"
    # Two test cases across one suite.
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) == 2
    assert all(t.state == "passed" for t in all_tests)


def test_parse_junit_mixed_has_failed_reason_and_errors():
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "mixed.xml")
    assert doc.reason == "failed"
    all_tests = {t.name: t for m in doc.test_modules for t in m.tests}
    assert all_tests["Trivial.Pass"].state == "passed"
    assert all_tests["Parser.Fails"].state == "failed"
    assert len(all_tests["Parser.Fails"].errors) >= 1
    assert "expected" in all_tests["Parser.Fails"].errors[0].message.lower()


def test_parse_junit_empty_yields_passed_reason_no_tests():
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "empty.xml")
    assert doc.reason == "passed"
    assert doc.test_modules == () or all(len(m.tests) == 0 for m in doc.test_modules)


def test_parse_junit_missing_file_raises_validation_error():
    from reporters.ctest_reporter import parse_junit
    from errors import ValidationError

    with pytest.raises(ValidationError, match="not found"):
        parse_junit(FIXTURES / "does_not_exist.xml")


def test_parse_junit_invalid_xml_raises_validation_error(tmp_path):
    from reporters.ctest_reporter import parse_junit
    from errors import ValidationError

    bad = tmp_path / "bad.xml"
    bad.write_text("<not-valid", encoding="utf-8")
    with pytest.raises(ValidationError, match="XML"):
        parse_junit(bad)


def test_run_writes_test_json_at_destination(tmp_path):
    from reporters.ctest_reporter import run

    src = FIXTURES / "mixed.xml"
    dst = tmp_path / ".claude" / "tdd-guard" / "data" / "test.json"
    rc = run(src, dst)
    assert rc == 0
    assert dst.exists()
    data = json.loads(dst.read_text(encoding="utf-8"))
    assert data["reason"] == "failed"
    assert any(t["state"] == "failed" for m in data["testModules"] for t in m["tests"])


def test_parse_junit_falls_back_to_suite_name_when_classname_missing():
    """MAGI Checkpoint 2 iter 1 WARNING (melchior).

    Some ctest toolchains emit ``<testcase classname=""`` or omit the
    ``classname`` attribute entirely. In that case the parser must fall
    back to the enclosing ``<testsuite name="...">`` rather than producing
    ``.testname`` strings.
    """
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "missing_classname.xml")
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) == 2
    # Both tests must have non-empty, suite-prefixed names (no leading dot).
    for t in all_tests:
        assert "." in t.name
        assert not t.name.startswith(".")
        # Fallback: classname == suite name "Fallback".
        assert t.name.startswith("Fallback.")


def test_parse_junit_handles_all_missing_attributes():
    """Pathological input: classname missing AND suite name missing.

    Defensive coverage: the parser must not crash; it uses ``'unknown'`` as
    the last-resort fallback.
    """
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "classname_and_suite_empty.xml")
    all_tests = [t for m in doc.test_modules for t in m.tests]
    assert len(all_tests) >= 1
    # No crash, no empty-prefix names.
    for t in all_tests:
        assert t.name
        assert not t.name.startswith(".")


def test_parse_junit_skipped_recorded_as_skipped_state():
    """Red/lock test: <skipped> child must produce state='skipped'.

    If ctest_reporter._state_for() ever regressed to returning 'passed' for
    <skipped>, this assertion would fail. This is the discriminating coverage
    for the skipped-state branch.
    """
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "with_skipped.xml")
    all_tests = {t.name: t for m in doc.test_modules for t in m.tests}
    assert all_tests["Slow.Ignored"].state == "skipped"
    # A skipped-only run with no failures is still "passed" by TDD-Guard semantics.
    assert doc.reason == "passed"


def test_parse_junit_multiple_suites_preserve_boundaries():
    """Red/lock test: each <testsuite> becomes its own TestModule.

    Locks the one-suite-per-module mapping. A regression that flattened all
    testcases into a single module would fail this assertion.
    """
    from reporters.ctest_reporter import parse_junit

    doc = parse_junit(FIXTURES / "with_skipped.xml")
    module_ids = [m.module_id for m in doc.test_modules]
    # The fixture has two <testsuite>s.
    assert len(module_ids) == 2
    assert len(set(module_ids)) == 2


def test_run_returns_zero_on_success_contract_lock(tmp_path):
    """Contract-lock: run() returns exit-code 0 on successful write.

    Deliberately tautological vs current implementation -- guards against a
    silent contract change (e.g. returning the internal parser's 'reason'
    string instead of 0). Per Plan B "Deferred from MAGI Checkpoint 2",
    rewording to a more discriminating assertion is deferred to Milestone C
    when verification_commands wiring gives us a richer signal.
    """
    from reporters.ctest_reporter import run

    dst = tmp_path / "test.json"
    assert run(FIXTURES / "all_passed.xml", dst) == 0
    # Locking also: the destination file must exist and parse as JSON.
    assert dst.exists()
    json.loads(dst.read_text(encoding="utf-8"))  # raises if malformed
