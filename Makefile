.PHONY: setup profile build eval eval-live format check test docker

setup:
	uv sync --locked
profile:
	uv run --locked python scripts/profile_data.py
build:
	uv run --locked python -m app build
eval:
	uv run --locked python -m app eval --tier 1
eval-live:
	uv run --env-file .env --locked python -m app eval --tier 2
format:
	uv run --locked ruff format app tests evals scripts
	uv run --locked ruff check --fix app tests evals scripts
check:
	uv run --locked ruff format --check app tests evals scripts
	uv run --locked ruff check app tests evals scripts
	uv run --locked mypy
test:
	uv run --locked pytest -q
docker:
	docker build -t cloudnova-track-b:local .
