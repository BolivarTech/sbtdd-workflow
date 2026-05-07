"""Synthetic fixture: callsite with allow_interactive_skill=True override."""

from __future__ import annotations

from typing import Any


def fake_call() -> None:
    invoke_skill(
        skill="brainstorming",
        args=["@spec.md"],
        allow_interactive_skill=True,
    )


def invoke_skill(**kwargs: Any) -> None:  # pragma: no cover
    return None
