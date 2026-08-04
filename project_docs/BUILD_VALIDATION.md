# PhronesisML — Build Validation

> **Purpose:** Evidence that `phronesisml==0.3.0` builds reproducibly through both `python -m build` (pip) and `uv build`, and that the artifacts pass `twine check` and an import smoke test.
> **Date:** 2026-08-05
> **Backend:** `hatchling` (PEP 517). Version is dynamic (`[tool.hatch.version] path = "phronesisml/__init__.py"`).
> **Status:** PASSED.

## 1. Build commands

| Tool | Command | Result |
|---|---|---|
| pip | `python -m build` | `phronesisml-0.3.0.tar.gz` + `phronesisml-0.3.0-py3-none-any.whl` |
| uv | `uv build` | `dist\phronesisml-0.3.0.tar.gz` + `dist\phronesisml-0.3.0-py3-none-any.whl` |

Both tools produce identical artifact names at version 0.3.0 (dynamic version read from `phronesisml/__init__.py`).

## 2. Artifact inspection

| Artifact | Entries | Notes |
|---|---|---|
| Wheel (`-py3-none-any.whl`) | 108 | Package + `py.typed`, `ml/reports/templates/full_report.md`, `dist-info` (METADATA, WHEEL, entry_points.txt, LICENSE, RECORD). No tests/docs/project planning files |
| sdist (`.tar.gz`) | 115 | Package + `uv.lock`, `.python-version`, CHANGELOG/CONTRIBUTING/SECURITY/CODE_OF_CONDUCT, LICENSE. Excludes `docs/`, `project_docs/`, `.github/`, `mkdocs.yml`, `Makefile`, `requirements.txt`, `tests/`, `data/` |

## 3. Metadata checks

| Check | Result |
|---|---|
| `twine check dist/*` | PASSED for all 4 artifacts (incl. legacy 0.2.2 artifacts present at the time) |
| Wheel METADATA version | `0.3.0` |
| Wheel entry_points | `[console_scripts] phronesisml = phronesisml.interfaces.cli.app:app` |
| License file | Included in wheel `dist-info/licenses/LICENSE` |

## 4. Import smoke test (wheel install)

```bash
pip install --force-reinstall --no-deps dist/phronesisml-0.3.0-py3-none-any.whl
python -c "import phronesisml; print(phronesisml.__version__)"   # -> 0.3.0
```

Same smoke test is wired into CI (`build` job) against the wheel built from the tag.

## 5. Version single-sourcing

`pyproject.toml` declares `dynamic = ["version"]` and `[tool.hatch.version] path = "phronesisml/__init__.py"`. The single `__version__ = "0.3.0"` in `phronesisml/__init__.py` feeds:
- build metadata (verified via `importlib.metadata.version`),
- runtime `phronesisml.__version__`,
- SDK `Phronesis.version()` / `health()`.

No other version literals exist (checked: only `__init__.py` + build outputs).

## 6. CI coverage

`.github/workflows/ci.yml` `build` job (runs on every push/PR and gates the PyPI publish):
1. `python -m build` (pip leg)
2. `uv build` (uv leg)
3. `twine check dist/*`
4. Wheel reinstall + `import phronesisml` smoke test
