import pytest


def test_validate_prefix_accepts_known():
    from commits import validate_prefix

    for prefix in ("test", "feat", "fix", "refactor", "chore"):
        validate_prefix(prefix)  # no raise


def test_validate_prefix_rejects_unknown():
    from commits import validate_prefix
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_prefix("wip")


def test_validate_message_rejects_co_authored_by():
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        validate_message("add parser\n\nCo-Authored-By: someone")
    assert "Co-Authored-By" in str(exc_info.value)


def test_validate_message_rejects_claude_reference():
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_message("add parser suggested by Claude")


def test_validate_message_rejects_ai_reference():
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_message("fix: regression found by AI assistant")


def test_validate_message_rejects_spanish_implementar():
    """Scenario 10 (spec-behavior.md sec.4.5): reject 'implementar' as Spanish."""
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        validate_message("implementar parser")
    assert "English" in str(exc_info.value) or "Spanish" in str(exc_info.value)


def test_validate_message_rejects_spanish_arreglar():
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_message("arreglar bug en la funcion")


def test_validate_message_rejects_spanish_anadir():
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_message("anadir nuevos tests")


def test_validate_message_rejects_non_ascii_chars():
    """Non-ASCII letters are a strong signal of non-English content."""
    from commits import validate_message
    from errors import ValidationError

    with pytest.raises(ValidationError):
        validate_message("anadir soporte para caracteres especiales")  # has tilde n


def test_validate_message_accepts_clean_english():
    from commits import validate_message

    validate_message("add parser for empty input edge case")  # no raise


def test_validate_message_accepts_english_del_keyword():
    """Regression: 'del' is a valid English keyword (Python builtin, shell 'del').

    The prior Spanish denylist treated 'del' as Spanish, falsely rejecting
    legitimate English commits like 'del obsolete cache entries'. Remove that
    entry from the denylist (MAGI Loop 2 Finding 1).
    """
    from commits import validate_message

    validate_message("fix: del obsolete cache entries after TTL")  # no raise
    validate_message("refactor: del loop variable after use")  # no raise


def test_validate_message_accepts_technical_english_with_numbers():
    from commits import validate_message

    validate_message("fix: off-by-one in loop bound (issue #42)")  # no raise


def test_create_invokes_git_commit(monkeypatch, tmp_path):
    from commits import create

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))

        class R:
            returncode = 0
            stdout = "[main abc1234] test: foo"
            stderr = ""

        return R()

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    create(prefix="test", message="add parser edge case", cwd=str(tmp_path))
    # At least one call should be `git commit -m "test: add parser edge case"`.
    commit_calls = [c for c in calls if "commit" in c]
    assert len(commit_calls) == 1
    assert commit_calls[0][-1] == "test: add parser edge case"


def test_create_rejects_before_git_call(monkeypatch):
    from commits import create
    from errors import ValidationError

    def fake_run(cmd, **kwargs):
        raise AssertionError("git should not be invoked on invalid input")

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(ValidationError):
        create(prefix="wip", message="fine message", cwd=".")


def test_create_wraps_subprocess_timeout_as_sbtdd_error(monkeypatch):
    """subprocess.TimeoutExpired from git commit must surface as SBTDDError.

    Per MAGI Loop 2 Finding 5: dispatchers that catch SBTDDError must
    also catch subprocess timeouts from git invocations; otherwise the
    exit-code taxonomy leaks TimeoutExpired uncaught.
    """
    import subprocess

    from commits import create
    from errors import SBTDDError

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=30)

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(SBTDDError) as exc_info:
        create(prefix="feat", message="a valid message", cwd=".")
    assert "timeout" in str(exc_info.value).lower() or "timed out" in str(exc_info.value).lower()


def test_create_wraps_git_non_zero_as_sbtdd_error(monkeypatch):
    """git commit returning non-zero must surface as SBTDDError, not RuntimeError."""
    from commits import create
    from errors import SBTDDError

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = ""
            stderr = "fatal: bad commit"

        return R()

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)
    with pytest.raises(SBTDDError) as exc_info:
        create(prefix="feat", message="a valid message", cwd=".")
    assert "git commit failed" in str(exc_info.value)


def test_create_full_input_validation_chain(monkeypatch):
    """Validates the chain: prefix -> message -> git (short-circuits on first fail)."""
    from commits import create
    from errors import ValidationError

    def fake_run(cmd, **kwargs):
        raise AssertionError("git should not run - validation must short-circuit")

    monkeypatch.setattr("commits.subprocess_utils.run_with_timeout", fake_run)

    # Bad prefix:
    with pytest.raises(ValidationError, match="prefix"):
        create(prefix="invalid", message="ok message", cwd=".")
    # Bad message (valid prefix):
    with pytest.raises(ValidationError, match="forbidden pattern"):
        create(prefix="feat", message="add Claude integration", cwd=".")


def test_allowed_prefixes_is_derived_from_commit_prefix_map():
    """DRY: _ALLOWED_PREFIXES must be sourced from models.COMMIT_PREFIX_MAP to prevent drift."""
    import inspect

    import commits
    from commits import _ALLOWED_PREFIXES
    from models import COMMIT_PREFIX_MAP

    source = inspect.getsource(commits)
    assert "COMMIT_PREFIX_MAP" in source, (
        "_ALLOWED_PREFIXES must be derived from models.COMMIT_PREFIX_MAP "
        "(DRY, sec.M.5 cross-file contract)"
    )
    assert _ALLOWED_PREFIXES == frozenset(COMMIT_PREFIX_MAP.values()), (
        "_ALLOWED_PREFIXES must equal frozenset(COMMIT_PREFIX_MAP.values())"
    )


def test_license_files_exist():
    from pathlib import Path

    root = Path(__file__).parent.parent
    assert (root / "LICENSE").exists(), "MIT LICENSE file missing (sec.S.12.2)"
    assert (root / "LICENSE-APACHE").exists(), "Apache LICENSE file missing"


def test_license_dual_in_pyproject():
    from pathlib import Path

    root = Path(__file__).parent.parent
    content = (root / "pyproject.toml").read_text()
    assert 'license = "MIT OR Apache-2.0"' in content


class TestValidatePrefixFromSubjectCCScope:
    """v1.0.6 K-5: liberal CC scope syntax support (Q4'=b liberal regex).

    Covers escenarios K-5a + K-5b + K-5c from spec sec.4.8.
    """

    def test_k5a_bare_prefix_matches_backwards_compat(self) -> None:
        """K-5a: bare prefix `test:` still matches (v1.0.5 backwards compat)."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("test: add failing test for X") == "test"
        assert extract_prefix_from_subject("feat: implement Y") == "feat"
        assert extract_prefix_from_subject("fix: bug Z") == "fix"
        assert extract_prefix_from_subject("refactor: extract helper") == "refactor"
        assert extract_prefix_from_subject("chore: mark task 1 complete") == "chore"

    def test_k5b_scoped_prefix_matches_NEW(self) -> None:
        """K-5b: `test(scope): ...` scoped prefix matches per Q4'=b liberal."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("test(close-task): add failing test") == "test"
        assert extract_prefix_from_subject("feat(close-task): implement") == "feat"
        assert extract_prefix_from_subject("fix(commits): bug fix") == "fix"
        assert extract_prefix_from_subject("refactor(state-file): extract helper") == "refactor"

    def test_k5c_liberal_scope_content_accepted(self) -> None:
        """K-5c: liberal regex `[^()]+` accepts any non-paren scope content."""
        from commits import extract_prefix_from_subject

        # Uppercase scope
        assert extract_prefix_from_subject("feat(Close-Task): X") == "feat"
        # Underscore scope
        assert extract_prefix_from_subject("fix(close_task): X") == "fix"
        # Space in scope
        assert extract_prefix_from_subject("refactor(some scope): X") == "refactor"
        # Numeric scope
        assert extract_prefix_from_subject("test(123): X") == "test"
        # Mixed
        assert extract_prefix_from_subject("feat(My-Scope_v2): X") == "feat"

    def test_k5e_cc_breaking_change_marker_supported(self) -> None:
        """K-5e (iter-1 cas WARNING): CC spec `!` breaking-change marker matches."""
        from commits import extract_prefix_from_subject

        # Bare with breaking marker
        assert extract_prefix_from_subject("feat!: drop legacy API") == "feat"
        assert extract_prefix_from_subject("fix!: backwards-incompatible bug fix") == "fix"
        # Scoped with breaking marker
        assert extract_prefix_from_subject("feat(api)!: drop legacy") == "feat"
        assert extract_prefix_from_subject("refactor(close-task)!: rename helper") == "refactor"

    def test_k5f_colon_without_trailing_space_supported(self) -> None:
        """K-5f (iter-1 mel WARNING): colon without trailing whitespace matches."""
        from commits import extract_prefix_from_subject

        # No space after colon
        assert extract_prefix_from_subject("feat:Implementation") == "feat"
        assert extract_prefix_from_subject("test(scope):add tests") == "test"
        # Colon at end of line (just prefix, empty body — uncommon but valid syntax)
        assert extract_prefix_from_subject("feat:") == "feat"

    def test_k5_extraction_is_liberal_validation_is_separate(self) -> None:
        """K-5 (Q4'=b + iter-1 bal+cas WARNING): extraction is liberal; validation is downstream.

        Returned prefix is NOT validated against `_ALLOWED_PREFIXES`.
        Caller (e.g., _preflight triplet check) validates separately.
        """
        from commits import extract_prefix_from_subject

        # Known prefixes extract correctly
        assert extract_prefix_from_subject("docs: update README") == "docs"
        # Unknown lowercase prefix extracts (extraction is liberal)
        assert extract_prefix_from_subject("madeup: subject") == "madeup"
        # No-colon subject returns None
        assert extract_prefix_from_subject("noprefix subject only") is None
        # Non-alphabetic prefix returns None (regex requires `[a-z]+`)
        assert extract_prefix_from_subject("123: numeric prefix") is None

    def test_k5_subject_with_no_colon_returns_none(self) -> None:
        """K-5: subject without colon doesn't match prefix syntax."""
        from commits import extract_prefix_from_subject

        assert extract_prefix_from_subject("just a subject without colon") is None
