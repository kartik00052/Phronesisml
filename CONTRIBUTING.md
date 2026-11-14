# Contributing to PhronesisML

Thank you for your interest in contributing to PhronesisML! This guide will help you get started.

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/PhronesisML.git
   cd PhronesisML
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # .venv\Scripts\activate   # Windows
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

   > **Using [uv](https://docs.astral.sh/uv)?** `uv sync --all-extras` installs the
   > exact locked environment from the committed `uv.lock` instead.

4. **Install pre-commit hooks (optional but recommended):**
   ```bash
   pip install pre-commit
   pre-commit install
   ```

For backend/web work, add the `web` extra (or install everything with
`uv sync --all-extras`):

```bash
pip install -e ".[dev,web]"
```

## Backend (FastAPI)

The optional web adapter lives in `backend/` and serves the SDK over
`/api/v1` (REST + WebSocket).

```bash
uvicorn backend.app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

Backend tests are included in the default `pytest` run (`testpaths` in
`pyproject.toml`):

```bash
pytest backend/tests                 # contract tests (no model training)
pytest backend/tests -m integration  # real-pipeline tests (opt-in, slow)
python backend/tests/e2e_smoke.py    # standalone HTTP smoke test
```

## Frontend (React)

Requires Node 22+ and pnpm (`corepack enable`).

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:5173
pnpm typecheck
pnpm lint
pnpm test       # Vitest
pnpm build
pnpm test:e2e   # Playwright
```

## Code Quality

### Linting
```bash
ruff check phronesisml/
ruff format phronesisml/
```

### Type Checking
```bash
mypy phronesisml/ --ignore-missing-imports
```

### Running Tests
```bash
pytest
```

### Full Check
```bash
ruff check phronesisml/ && mypy phronesisml/ --ignore-missing-imports && pytest
```

## Branch Strategy

- `main` — stable release branch
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `docs/<name>` — documentation changes

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass: `ruff check phronesisml/`, `mypy phronesisml/ --ignore-missing-imports`, `pytest`
4. Submit a PR with a clear description of the change

## Commit Messages

Use conventional commits:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add missing tests`
- `refactor: improve code structure`

## Reporting Issues

Use the GitHub issue tracker. Include:
- Python version
- OS
- Minimal reproducible example
- Expected vs actual behavior

## Code Style

- Follow existing conventions in the codebase
- Use type hints on all public functions
- Add docstrings to new public APIs
- Keep changes minimal and focused
