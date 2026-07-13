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

4. **Install pre-commit hooks (optional but recommended):**
   ```bash
   pip install pre-commit
   pre-commit install
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
