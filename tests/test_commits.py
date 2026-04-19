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
