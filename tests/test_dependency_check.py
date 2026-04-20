from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError


def test_dependency_check_is_frozen_dataclass():
    from dependency_check import DependencyCheck

    chk = DependencyCheck(
        name="git",
        status="OK",
        detail="git version 2.43.0",
        remediation=None,
    )
    with pytest.raises(FrozenInstanceError):
        chk.status = "MISSING"  # type: ignore[misc]


def test_dependency_check_requires_four_fields():
    from dependency_check import DependencyCheck

    fields = set(DependencyCheck.__dataclass_fields__)
    assert fields == {"name", "status", "detail", "remediation"}


def test_check_status_values_restricted():
    from dependency_check import VALID_STATUSES

    assert VALID_STATUSES == ("OK", "MISSING", "BROKEN")
