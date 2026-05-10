# v1.0.7 A3 fixture Makefile.
# Mirrors the orchestrator's sec.0.1 chain so worker close-phase has a
# `make verify` fallback alongside the v1.0.7 A2 worker-mode shell-direct
# chain. Both paths produce identical sec.0.1 evidence.

.PHONY: verify test lint format typecheck

verify: test lint format typecheck

test:
	pytest

lint:
	ruff check .

format:
	ruff format --check .

typecheck:
	mypy .
