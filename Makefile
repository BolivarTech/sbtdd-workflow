.PHONY: test lint format typecheck coverage verify

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check .

format:
	python -m ruff format --check .

typecheck:
	python -m mypy .

coverage:
	python -m pytest --cov=skills/sbtdd/scripts --cov-report=term-missing tests/

verify: lint format typecheck coverage
