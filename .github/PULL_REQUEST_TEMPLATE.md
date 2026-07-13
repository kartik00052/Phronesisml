## Description

Brief description of the changes in this PR.

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to change)
- [ ] Documentation update
- [ ] Refactoring (no functional changes)

## Checklist

- [ ] My code follows the project's code style (`ruff check` and `ruff format` pass)
- [ ] I have added/updated tests that prove my fix is effective or my feature works
- [ ] New and existing tests pass locally (`pytest`)
- [ ] I have updated the documentation (if applicable)
- [ ] I have added an entry to `CHANGELOG.md` (if applicable)

## Testing

Describe the tests you ran to verify your changes:

```bash
pytest tests/ -q
ruff check phronesisml/ --no-fix
ruff format --check phronesisml/
mypy phronesisml/ --ignore-missing-imports
```

## Screenshots / Output

If applicable, add screenshots or paste test output to demonstrate the change.
