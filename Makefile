.PHONY: check lint typecheck test protected

# The one command that runs every strict check. The night loop and CI both use it.
check: lint typecheck test

lint:
	uv run ruff check .
	uv run ruff format --check .

typecheck:
	uv run mypy src tests checks runner

test:
	uv run pytest

# Fails when the diff against BASE (default main) touches a protected path.
protected:
	python3 checks/check_protected_paths.py --base $(or $(BASE),main)
