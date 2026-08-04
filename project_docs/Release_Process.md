# PhronesisML — Release Process

> **Version:** 0.2.2 · **Date:** 2026-08-04
> **Status:** Operational summary of `AI_QUALITY_GATE.md` §7 (Release Rules) + the phased plan in `IMPLEMENTATION_ROADMAP.md` §21–24.

## 1. Versioning

- Semantic versioning `MAJOR.MINOR.PATCH`. Pre-1.0, behavior-correcting fixes ship in `MINOR` (Phase 1 → `0.3.x`); API breaks ship in `MAJOR` (1.0).
- Version lives in exactly one place: `phronesisml/__init__.py:__version__`, then propagated consistently (CLI `info`).

## 2. Commit convention

Conventional commits: `fix:`, `feat:`, `docs:`, `chore:`, `style:`, `release:`, `refactor:`. `CHANGELOG.md` gets an entry for every release citing fix IDs (BUG-xx, ISSUE-xx).

## 3. Breaking vs non-breaking

- **Non-breaking by default.** Observable-behavior changes are additive/opt-in unless explicitly approved as breaking.
- Breaking changes require per-item approval + migration note.
- Historical example: 0.2.0 rename AetherML → PhronesisML was a deliberate breaking release (documented in CHANGELOG).
- Contract rule: once a field ships in the SDK/CLI envelope it is frozen; new fields are additive-only.

## 4. Gate before tagging

1. §9 gate green: `ruff check .`, `ruff format --check .`, `mypy phronesisml`, full `pytest -q`.
2. Clean-room wheel smoke test: build wheel, install in a fresh venv (correct Python floor), run CLI + SDK end-to-end.
3. Docs sync (§4) and `project_state.json` regenerated (§12).
4. `CHANGELOG.md` entry.

## 5. Release timeline (from IMPLEMENTATION_ROADMAP §21)

| Phase | Version | Scope |
|---|---|---|
| 1 | 0.3.x | Correctness hardening — BUG-01…05, ISSUE-06…08 + regression tests, CLI test suite, post-fix gate |
| 2 | 0.4.x–0.5.x | Beta surfaces — schema validation, recommendation with WHY, drift check, run ledger, extra reports |
| 3 | 1.0 | Pipeline serialization, local serving, ONNX + model registry, spark hardening, frozen API contract |

Each phase ends with: full toolchain green, clean-room wheel smoke test, `CHANGELOG.md` entry, docs sync.

## 6. Packaging rules (gate §6)

- Build with `hatchling`; never hand-package.
- Extras must match `pyproject.toml`: `cli, spark, mlflow, excel, dev, all`. (There is no `[docs]` extra.)
- `py.typed` ships (type hints are a feature).

## 7. Release checklist

- [ ] Gate green (lint/format/types/tests)
- [ ] Clean-room wheel smoke (CLI + SDK)
- [ ] Docs synced; `project_state.json` regenerated
- [ ] `CHANGELOG.md` updated with fix IDs
- [ ] Version bumped in `__init__.py` and propagated
