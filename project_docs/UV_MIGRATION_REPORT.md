# PhronesisML — uv Migration Report

> **Purpose:** Final record of the v0.3.0 packaging/uv-migration work: what changed, why, and the validation evidence. Companion to `PACKAGING_AUDIT.md` (audit/findings), `DEPENDENCY_MATRIX.md`, `INSTALLATION_VALIDATION.md`, `BUILD_VALIDATION.md`, `CI_VALIDATION.md`.
> **Date:** 2026-08-05
> **Status:** COMPLETE — all 12 checklist steps executed.

---

## 1. Scope

PhronesisML is now installed and built through **two first-class workflows**:

- **pip** (`pip install phronesisml[...]`) — the published, tutorial path.
- **uv** (`uv sync`, `uv build`) — the fast, locked developer path.

Both produce the same `phronesisml==0.3.0` artifacts and are validated by CI.

## 2. Findings resolved (from `PACKAGING_AUDIT.md`)

| Finding | Resolution |
|---|---|
| F1 no `docs` extra | Added `[docs]` extra (`mkdocs`, `mkdocs-material`, `mkdocstrings[python]`); `docs.yml` installs it |
| F2 `dev` incomplete | Added `pytest-xdist`, `coverage`, `build`, `twine` to `[dev]` |
| F3 `all` excluded docs | `all = phronesisml[cli,spark,mlflow,excel,docs]` |
| F4 duplicated version | `dynamic = ["version"]` + `[tool.hatch.version] path = "phronesisml/__init__.py"`; single `__version__` in `__init__.py` |
| F5 stale `requirements.txt` | Regenerated; pins now match `uv.lock` resolutions for all direct deps |
| F6 `uv.lock` untracked + win32-only | `uv.lock` now tracked; `[tool.uv] environments` widened to win32/darwin(arm64)/linux. Darwin is `arm64` only — shap 0.51.0 (py<3.12) pins `numba<0.63` on darwin-x86_64, which needs `numpy<2.4` and is unsatisfiable with `numpy>=1.24,<2.5`; the lock now carries a single `numba 0.66.0` and splits `shap` 0.51.0 (py<3.12) / 0.52.0 (py≥3.12) with resolution markers |
| F7 pip-only CI | Dual pip+uv matrix, lock check, `build` job with `twine check` + import smoke |
| F8 mypy version mismatch | `python_version = "3.11"` (floor of supported range) |
| F9 Makefile POSIX-only | Added uv targets (`sync`, `install-uv`, `build-uv`), cross-platform Python-based `clean`, `test-fast` (`-n auto`) |
| F10 sdist exclusions undocumented | Commented intent in `pyproject.toml` |
| F11 Windows CLI unicode crash | UTF-8 stdio reconfigure (`backslashreplace`) at CLI import; regression tests in `tests/test_interfaces.py` |

## 3. File changes

| Path | Change |
|---|---|
| `pyproject.toml` | Dynamic version; `docs` extra; expanded `dev`; `all` += docs; `[tool.hatch.version]`; widened `[tool.uv] environments`; mypy py311; sdist comment |
| `uv.lock` | Regenerated (cross-platform, 175 pkgs), now tracked |
| `requirements.txt` | Regenerated to match lock |
| `Makefile` | uv targets + cross-platform clean |
| `.github/workflows/ci.yml` | Dual pip+uv matrix, lock check, build/twine/import-smoke job, publish gated on build |
| `.github/workflows/docs.yml` | `[docs]` extra, pip+uv matrix |
| `phronesisml/interfaces/cli/app.py` | UTF-8 stdio reconfigure (Windows cp1252-pipe fix, F11) |
| `.github/workflows/ci.yml` | Regression script wired per-leg (`uv run` vs `python`) |
| `project_docs/PACKAGING_AUDIT.md` | New — audit record |
| `project_docs/DEPENDENCY_MATRIX.md` | New — dependency mapping |
| `project_docs/INSTALLATION_VALIDATION.md` | New — install evidence |
| `project_docs/BUILD_VALIDATION.md` | New — build evidence |
| `project_docs/CI_VALIDATION.md` | New — CI evidence |
| `project_docs/project_state.json` | Updated to v0.3.0 |
| `CHANGELOG.md` | v0.3.0 packaging entries + CLI fix |

## 4. Validation evidence (summary)

| Check | Command | Result |
|---|---|---|
| Lock consistency | `uv lock --check` | PASSED (175 pkgs, win32/darwin-arm64/linux) |
| uv install | `uv sync --all-extras` | PASSED (pyspark 3.5.9, mlflow 2.22.5 installed from lock) |
| pip install | `pip install -e ".[dev,cli,excel,docs]"` (fresh py3.11 venv) | PASSED (0.3.0) |
| pip build | `python -m build` | PASSED (wheel + sdist) |
| uv build | `uv build` | PASSED (wheel + sdist) |
| Artifact check | `twine check dist/*` | PASSED |
| Metadata parity | wheel METADATA vs sdist PKG-INFO | PASSED (35 Requires-Dist each, identical) |
| Import smoke | wheel + sdist reinstall + `import phronesisml` | PASSED (both resolve from site-packages) |
| Lint | `ruff check` / `ruff format --check` | PASSED |
| Type check | `mypy phronesisml/ --ignore-missing-imports` | PASSED — **clean, 0 errors in 101 files** |
| Tests | `pytest tests/` | PASSED (305 + 2 CLI regression tests) |
| CLI parity | `phronesisml analyze/train/explain/report` via pip vs uv | PASSED — identical output (`Trained: LogisticRegression (score=1.0000)`) |
| Docs | `mkdocs build --strict` | PASSED |
| Quality gate | `make check` | PASSED |

Full detail in `INSTALLATION_VALIDATION.md`, `BUILD_VALIDATION.md`, `CI_VALIDATION.md`.

## 5. Usage guide

### pip (tutorial / published path)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -e ".[dev,cli,excel,docs]"   # develop with everything
make check
```

End users: `pip install phronesisml`, or `pip install phronesisml[cli]` for the CLI.

### uv (fast, locked path)

```bash
uv sync --all-extras    # creates .venv from uv.lock
uv run pytest tests/
uv build
```

## 6. Known constraints / follow-ups

- `twine>=7` requires `rich>=14`, conflicting with `cli`'s `rich<14`; the lock pins `twine 6.2.0`. Raise both bounds together in a future release.
- `pyspark` and `mlflow` are locked but not installed in the default local env; `phronesisml health` reports them as optional.
- `test_phronesis.py` remains a diagnostic script (runs `|| true` in CI); the gating suite is `pytest tests/`.
