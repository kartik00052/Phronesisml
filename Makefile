.PHONY: lint format typecheck test check clean build docker

lint:
	python -m ruff check phronesisml/ tests/ --no-fix

format:
	python -m ruff format phronesisml/ tests/
	python -m ruff check phronesisml/ tests/ --fix

typecheck:
	python -m mypy phronesisml/ --ignore-missing-imports

test:
	python -m pytest tests/ -q --tb=short

check: lint typecheck test
	@echo "All checks passed."

build:
	python -m build

docker:
	docker build -t phronesisml:latest .
	docker run -d --name phronesisml -p 8000:8000 phronesisml:latest

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info/
