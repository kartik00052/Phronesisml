"""Health + capability + engine-recommend reporting (real SDK probing).

Output shapes follow ``frontend/src/types/health.ts`` and
``frontend/src/types/dataset.ts``.
"""

from __future__ import annotations

import importlib
import sys
from typing import Any

from backend.app.schemas.engine_schemas import EngineReport
from backend.app.services import dataset_service

_CORE = ("numpy", "pandas", "scipy", "sklearn")
_OPTIONAL = ("polars", "pyspark", "xgboost", "lightgbm", "catboost", "shap", "phronesisml")
_TASK_TYPES = ("classification", "regression", "clustering", "anomaly_detection")
_ENGINES = ("pandas", "polars", "spark")

__all__ = ["health", "capabilities", "engine_capabilities", "engine_recommend"]


def _probe(name: str) -> tuple[bool, str | None]:
    try:
        mod = importlib.import_module(name)
        return True, getattr(mod, "__version__", None)
    except Exception:  # noqa: BLE001
        return False, None


def _sdk_version() -> str:
    ok, ver = _probe("phronesisml")
    return ver or "0.0.0+unknown"


def _database_probe() -> dict[str, Any]:
    """Live reachability check against the configured SQLite database."""
    try:
        from sqlalchemy import text

        from backend.app.db import repositories

        with repositories.session_scope() as session:
            session.execute(text("SELECT 1"))
        return {"reachable": True}
    except Exception as exc:  # noqa: BLE001 - health must never raise
        return {"reachable": False, "error": f"{type(exc).__name__}: {exc}"}


def _storage_probe() -> dict[str, Any]:
    """Writability check for the dataset + run artifact storage roots."""
    from backend.app.config import get_settings

    settings = get_settings()
    paths = [settings.data_storage_dir, settings.run_storage_dir]
    report: dict[str, Any] = {"writable": True, "paths": [str(p) for p in paths]}
    for path in paths:
        try:
            path.mkdir(parents=True, exist_ok=True)
            probe = path / ".healthcheck"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except Exception as exc:  # noqa: BLE001 - health must never raise
            report["writable"] = False
            report["error"] = f"{path}: {type(exc).__name__}: {exc}"
    return report


def health() -> dict[str, Any]:
    deps: dict[str, Any] = {}
    missing: list[str] = []
    for name in _CORE:
        installed, ver = _probe(name)
        deps[name] = {"installed": installed, "version": ver, "optional": False}
        if not installed:
            missing.append(name)
    for name in _OPTIONAL:
        installed, ver = _probe(name)
        deps[name] = {"installed": installed, "version": ver, "optional": True}

    database = _database_probe()
    storage = _storage_probe()
    degraded = bool(missing) or not database["reachable"] or not storage["writable"]
    return {
        "status": "degraded" if degraded else "ok",
        "version": _sdk_version(),
        "python": sys.version.split()[0],
        "dependencies": deps,
        "missing_core": missing,
        "database": database,
        "storage": storage,
    }


def capabilities() -> dict[str, Any]:
    from phronesisml import _FULL_PIPELINE_STAGES  # noqa: PLC2701 (canonical stage order)

    return {
        "name": "PhronesisML",
        "version": _sdk_version(),
        "offline": True,
        "deterministic": True,
        "task_types": list(_TASK_TYPES),
        "engines": list(_ENGINES),
        "explainers": ["shap"],
        "pipeline_stages": list(_FULL_PIPELINE_STAGES),
        "sdk_methods": _sdk_methods(),
        "cli_commands": [],
        "extras": [],
        "optional_models": _optional_models(),
    }


_OPTIONAL_MODELS = ("xgboost", "lightgbm", "catboost")


def _optional_models() -> list[dict[str, Any]]:
    """Probe optional model backends so the UI never hard-codes availability."""
    reports: list[dict[str, Any]] = []
    for name in _OPTIONAL_MODELS:
        installed, ver = _probe(name)
        reports.append(
            {
                "name": name,
                "installed": installed,
                "version": ver,
                "optional": True,
                "reason": None if installed else "Optional dependency not installed",
            }
        )
    return reports


def _sdk_methods() -> list[str]:
    methods = [
        "analyze",
        "capabilities",
        "clean",
        "cluster",
        "compare",
        "config",
        "data_path",
        "detect_anomalies",
        "detect_target",
        "detect_task",
        "eda",
        "engineer",
        "engineer_features",
        "evaluate",
        "explain",
        "generate_report",
        "get_cleaned_data",
        "get_data",
        "get_features",
        "get_model",
        "health",
        "load",
        "predict",
        "profile",
        "recommend",
        "recommend_model",
        "report",
        "restore",
        "run",
        "save",
        "select_model",
        "state",
        "summary",
        "target",
        "train",
        "validate",
        "version",
    ]
    return methods


def engine_capabilities() -> dict[str, Any]:
    # Reflect the *actual* installed backends: an engine that is missing from
    # the environment must not be advertised as available.
    probe_map = {
        "pandas": True,  # always present (core dependency)
        "polars": _probe("polars")[0],
        "spark": _probe("pyspark")[0],
    }
    return EngineReport(
        engines=list(_ENGINES),
        enginesAvailable=[e for e, ok in probe_map.items() if ok],
        enginesMissing=[e for e, ok in probe_map.items() if not ok],
    ).model_dump(by_alias=True)


def engine_recommend(payload: dict[str, Any]) -> dict[str, Any]:
    return dataset_service.engine_recommend(payload)
