.PHONY: lint format typecheck test test-fast check build build-uv sync install clean

# ── Lint / format ────────────────────────────────────────────────
lint:
	python -m ruff check phronesisml/ tests/ --no-fix

format:
	python -m ruff format phronesisml/ tests/
	python -m ruff check phronesisml/ tests/ --fix

# ── Type checking ─────────────────────────────────────────────────
typecheck:
	python -m mypy phronesisml/ --ignore-missing-imports

# ── Tests ─────────────────────────────────────────────────────────
test:
	python -m pytest tests/ -q --tb=short

test-fast:
	python -m pytest tests/ -q --tb=short -x -n auto

# ── Combined gate ─────────────────────────────────────────────────
check: lint typecheck test
	@echo "All checks passed."

# ── pip workflow ──────────────────────────────────────────────────
install:
	python -m pip install -e ".[dev,cli,excel,docs]"

# ── uv workflow ───────────────────────────────────────────────────
sync:
	uv sync --all-extras

install-uv:
	uv pip install -e ".[dev,cli,excel,docs]"

# ── Build / release ───────────────────────────────────────────────
build:
	python -m build

build-uv:
	uv build

release-check: build
	twine check dist/*

# ── Cleanup ───────────────────────────────────────────────────────
clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in [pathlib.Path('dist'), pathlib.Path('build')] + [pathlib.Path('.').rglob('*.egg-info')] if isinstance(p, pathlib.Path)]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.mypy_cache')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.ruff_cache')]"
