"""Synthetic fixture: callsite without override (should fail audit)."""

from __future__ import annotations

from typing import Any


def fake_call() -> None:
    invoke_skill(
        skill="brainstorming",
        args=["@spec.md"],
    )


def invoke_skill(**kwargs: Any) -> None:  # pragma: no cover
    return None
