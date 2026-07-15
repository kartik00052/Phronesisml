"""PhronesisML services layer.

This package provides a unified namespace for business logic,
separating concerns from agent orchestration.  Services are
pure functions with no agent dependency.

Submodules:
    storage: Artifact persistence (extracted from StorageAgent).
    data_resolution: Feature/target reconstruction from workflow state.

The facade below re-exports the existing ``data/`` and ``ml/``
modules for discoverability.  These are the canonical imports —
existing ``phronesisml.data`` and ``phronesisml.ml`` paths remain
valid for backward compatibility.
"""

from __future__ import annotations

__all__ = [
    "data_resolution",
    "storage",
]

from phronesisml.services import data_resolution, storage

__all__ += [
    # Data layer
    "cleaning",
    "file_loader",
    "profilers",
    "validators",
    # ML layer
    "anomaly",
    "automl",
    "clustering",
    "evaluation",
    "explainability",
    "reports",
]


# Lazy re-exports to avoid circular imports
def __getattr__(name: str) -> object:
    _lazy = {
        # Data
        "cleaning": "phronesisml.data.transformers.cleaning",
        "file_loader": "phronesisml.data.loaders.file_loader",
        "profilers": "phronesisml.data.profilers.stats",
        "validators": "phronesisml.data.validators.checks",
        # ML
        "anomaly": "phronesisml.ml.anomaly.detector",
        "automl": "phronesisml.ml.automl.trainer",
        "clustering": "phronesisml.ml.clustering.algorithms",
        "evaluation": "phronesisml.ml.evaluation.metrics",
        "explainability": "phronesisml.ml.explainability.service",
        "reports": "phronesisml.ml.reports.builder",
    }
    if name in _lazy:
        import importlib

        module = importlib.import_module(_lazy[name])
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
