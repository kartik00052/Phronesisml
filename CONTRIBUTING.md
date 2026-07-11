# Contributing to AetherML

Thank you for your interest in contributing to AetherML! This guide will help you get started.

## Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/<your-username>/AetherML.git
   cd AetherML
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

## Code Quality

### Linting
```bash
ruff check .
ruff format .
```

### Type Checking
```bash
mypy src/aetherml --ignore-missing-imports
```

### Running Tests
```bash
pytest
```

## Branch Strategy

- `main` — stable release branch
- `feat/<name>` — new features
- `fix/<name>` — bug fixes
- `docs/<name>` — documentation changes

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass: `ruff check .`, `mypy src/aetherml --ignore-missing-imports`, `pytest`
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
