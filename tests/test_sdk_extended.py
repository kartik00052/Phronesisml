"""Extended SDK + Simple API tests.

Covers the v0.3.0 SDK consolidation surface (AI_QUALITY_GATE.md §16,
MASTER_FUNCTION_MATRIX.md §16/§17/§19):

- ``Phronesis``: ``predict``, ``compare``, ``save``, ``restore``,
  ``version``, ``capabilities``, ``health`` and the ``ModelComparison`` /
  ``SavedRun`` dataclasses.
- ``simple`` API: ``profile``, ``predict``, ``compare``, ``save``,
  ``restore``, ``version``, ``capabilities``, ``health`` plus their
  ``*_async`` twins.
- The full 18-file artifact suite produced by ``save_artifacts``.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from phronesisml import __version__

_SUPERVISED_STAGES = 11
_ARTIFACT_SET = {
    "evaluation.json",
    "metrics.json",
    "model.json",
    "training.json",
    "feature_metadata.json",
    "target_detection.json",
    "resource_estimation.json",
    "engine_selection.json",
    "eda.json",
    "validation.json",
    "shap.json",
    "config.json",
    "report.md",
    "report.html",
    "pipeline.json",
    "model.joblib",
    "logs.txt",
    "run_metadata.json",
}


@pytest.fixture(scope="module")
def classification_csv(tmp_path_factory) -> str:
    rng = np.random.default_rng(7)
    n = 120
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 80, n),
            "income": rng.normal(50000, 15000, n).round(2),
            "score": rng.uniform(0, 100, n).round(1),
            "target": (rng.normal(size=n) > 0).astype(int),
        }
    )
    path = tmp_path_factory.mktemp("sdk_extended") / "data.csv"
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture
def raw_df(classification_csv: str) -> pd.DataFrame:
    return pd.read_csv(classification_csv)


@pytest.fixture
def make_ml(classification_csv: str):
    """Build a fresh, pandas-engine Phronesis instance per test."""
    from phronesisml import Phronesis, PhronesisConfig

    def _make() -> Phronesis:
        config = PhronesisConfig()
        config.engine.preferred = "pandas"
        return Phronesis(classification_csv, config)

    return _make


# ── SDK: introspection ────────────────────────────────────────────


def test_sdk_version_matches_package(make_ml) -> None:
    assert make_ml().version() == __version__


def test_sdk_capabilities_report_is_deterministic(make_ml) -> None:
    info1 = make_ml().capabilities()
    info2 = make_ml().capabilities()
    assert info1 == info2
    assert info1["name"] == "phronesisml"
    assert info1["version"] == __version__
    assert info1["offline"] is True
    assert info1["deterministic"] is True
    assert len(info1["pipeline_stages"]) == _SUPERVISED_STAGES
    assert info1["pipeline_stages"][0] == "upload"
    assert info1["pipeline_stages"][-1] == "storage"
    for method in (
        "run",
        "train",
        "predict",
        "compare",
        "save",
        "restore",
        "version",
        "capabilities",
        "health",
    ):
        assert method in info1["sdk_methods"]
    for command in (
        "run",
        "info",
        "train",
        "analyze",
        "validate",
        "profile",
        "explain",
        "report",
        "compare",
        "version",
        "capabilities",
        "doctor",
    ):
        assert command in info1["cli_commands"]


def test_sdk_health_reports_ok(make_ml) -> None:
    report = make_ml().health()
    assert report["status"] == "ok"
    assert report["version"] == __version__
    assert report["python"].startswith("3.")
    assert report["dependencies"]["pandas"]["installed"] is True
    assert report["missing_core"] == []


# ── SDK: prediction ───────────────────────────────────────────────


def test_predict_requires_trained_model_without_pipeline(make_ml, raw_df) -> None:
    ml = make_ml()
    with pytest.raises(ValueError, match="No trained model available"):
        ml._predict_ready(raw_df.head(3))


def test_predict_trains_and_returns_one_prediction_per_row(make_ml, raw_df) -> None:
    ml = make_ml()
    predictions = ml.predict(raw_df.head(5))
    assert len(predictions) == 5
    assert all(int(p) in {0, 1} for p in predictions)


def test_predict_ignores_target_column(make_ml, raw_df) -> None:
    ml = make_ml()
    with_target = ml.predict(raw_df.head(4))
    without_target = ml.predict(raw_df.drop(columns=["target"]).head(4))
    assert with_target == without_target


def test_predict_is_deterministic_across_runs(make_ml, raw_df) -> None:
    ml1 = make_ml()
    ml2 = make_ml()
    assert ml1.predict(raw_df.head(6)) == ml2.predict(raw_df.head(6))


# ── SDK: comparison ───────────────────────────────────────────────


def test_compare_ranks_baseline_and_requested_model(make_ml) -> None:
    ml = make_ml()
    comparison = ml.compare(["random_forest"])

    assert isinstance(comparison.best_model, str)
    assert comparison.primary_metric in {
        "accuracy",
        "precision_macro",
        "recall_macro",
        "f1_macro",
        "roc_auc",
        "rmse",
        "mae",
        "r2",
    }
    assert comparison.ranking
    assert comparison.ranking[0]["model"] == comparison.best_model
    assert {"model", "primary_metric", "value"} <= set(comparison.ranking[0])

    ranked = [row["value"] for row in comparison.ranking]
    assert ranked == sorted(ranked, reverse=comparison.higher_is_better)

    baseline = (ml._state.best_pipeline or {}).get("model_type")
    trained = [m["model"] for m in comparison.models if m.get("metrics")]
    assert baseline in trained


def test_compare_as_dict_is_json_serializable(make_ml) -> None:
    comparison = make_ml().compare(["random_forest"])
    payload = comparison.as_dict()
    assert payload["task_type"] == comparison.task_type
    assert payload["ranking"] == comparison.ranking
    json.dumps(payload)


# ── SDK: save / restore ───────────────────────────────────────────


def test_save_writes_full_artifact_set(make_ml, tmp_path) -> None:
    ml = make_ml()
    info = ml.save(str(tmp_path / "runs"))

    artifact_dir = __import__("pathlib").Path(info["artifact_uri"])
    assert artifact_dir.is_dir()
    names = {p.name for p in artifact_dir.iterdir()}
    assert names == _ARTIFACT_SET
    assert len(info["saved_files"]) == len(_ARTIFACT_SET)

    metadata = json.loads((artifact_dir / "run_metadata.json").read_text(encoding="utf-8"))
    assert metadata["run_id"] == ml._state.run_id
    assert metadata["status"] == "completed"
    assert metadata["version"] == __version__


def test_save_restore_roundtrip_predictions_match(make_ml, raw_df, tmp_path) -> None:
    from phronesisml import Phronesis

    ml = make_ml()
    ml.train()
    direct = ml.predict(raw_df.head(5))
    features = ml.get_features().head(3)

    info = ml.save(str(tmp_path / "runs"))
    saved = Phronesis.restore(info["artifact_uri"])

    assert saved.run_id == ml._state.run_id
    assert saved.task_type == ml._state.task_type
    assert saved.target_column == ml._state.target_column
    assert saved.feature_names == ml._state.feature_names
    assert saved.model is not None
    assert saved.model_info["model_type"] == (ml._state.best_pipeline or {}).get("model_type")
    assert saved.predict(raw_df.head(5)) == direct
    assert len(saved.predict(features, already_engineered=True)) == 3


def test_restore_missing_directory_raises(make_ml, tmp_path) -> None:
    from phronesisml import Phronesis

    with pytest.raises(FileNotFoundError, match="Saved run artifact missing"):
        Phronesis.restore(str(tmp_path / "nope"))


def test_restore_requires_model_file(make_ml, tmp_path) -> None:
    from phronesisml import Phronesis

    ml = make_ml()
    info = ml.save(str(tmp_path / "runs"))
    artifact_dir = __import__("pathlib").Path(info["artifact_uri"])
    (artifact_dir / "model.joblib").unlink()
    with pytest.raises(FileNotFoundError, match="Saved model missing"):
        Phronesis.restore(str(artifact_dir))


# ── Simple API: sync ──────────────────────────────────────────────


def test_simple_profile(classification_csv: str) -> None:
    from phronesisml import analyze, profile

    p = profile(classification_csv, engine="pandas")
    a = analyze(classification_csv, engine="pandas")
    assert p.shape == a.shape
    assert p.validation_passed is True
    assert set(p.column_names) == {"age", "income", "score", "target"}


def test_simple_predict(classification_csv: str, raw_df) -> None:
    from phronesisml import predict

    predictions = predict(classification_csv, raw_df.head(3), engine="pandas")
    assert len(predictions) == 3
    assert all(int(p) in {0, 1} for p in predictions)


def test_simple_compare(classification_csv: str) -> None:
    from phronesisml import compare

    result = compare(classification_csv, ["random_forest"], engine="pandas")
    assert isinstance(result.best_model, str)
    assert result.ranking
    assert result.models


def test_simple_save_restore_roundtrip(classification_csv: str, raw_df, tmp_path) -> None:
    from phronesisml import restore, save

    info = save(classification_csv, str(tmp_path / "runs"), engine="pandas")
    saved = restore(info["artifact_uri"])
    assert saved.model is not None
    assert len(saved.predict(raw_df.head(2))) == 2


def test_simple_recommend_matches_select_model(classification_csv: str) -> None:
    from phronesisml import recommend, select_model

    rec = recommend(classification_csv, engine="pandas")
    sel = select_model(classification_csv, engine="pandas")
    assert rec.best_model_type == sel.best_model_type
    assert rec.best_score == sel.best_score
    assert rec.evaluation_metrics == sel.evaluation_metrics


def test_simple_load_roundtrip(classification_csv: str, raw_df, tmp_path) -> None:
    from phronesisml import load, save

    info = save(classification_csv, str(tmp_path / "runs"), engine="pandas")
    saved = load(info["artifact_uri"])
    assert saved.model is not None
    assert len(saved.predict(raw_df.head(2))) == 2


def test_public_api_surface_is_exported() -> None:
    import phronesisml

    required = {
        "train",
        "analyze",
        "predict",
        "evaluate",
        "profile",
        "clean",
        "validate",
        "recommend",
        "compare",
        "report",
        "explain",
        "save",
        "load",
        "version",
        "capabilities",
        "health",
    }
    assert required.issubset(set(phronesisml.__all__))
    for name in required:
        assert callable(getattr(phronesisml, name)), name
    for name in sorted(required):
        assert callable(getattr(phronesisml, name + "_async")), name + "_async"


def test_simple_introspection() -> None:
    from phronesisml import capabilities, health, version

    assert version() == __version__
    info = capabilities()
    assert info["name"] == "phronesisml"
    assert info["version"] == __version__
    assert len(info["pipeline_stages"]) == _SUPERVISED_STAGES
    report = health()
    assert report["status"] == "ok"
    assert report["version"] == __version__


# ── Simple API: async ─────────────────────────────────────────────


async def test_async_profile(classification_csv: str) -> None:
    from phronesisml import profile_async

    profile = await profile_async(classification_csv, engine="pandas")
    assert profile.shape == (120, 4)
    assert profile.validation_passed is True


async def test_async_predict(classification_csv: str, raw_df) -> None:
    from phronesisml import predict_async

    predictions = await predict_async(classification_csv, raw_df.head(3), engine="pandas")
    assert len(predictions) == 3


async def test_async_compare(classification_csv: str) -> None:
    from phronesisml import compare_async

    result = await compare_async(classification_csv, ["random_forest"], engine="pandas")
    assert isinstance(result.best_model, str)
    assert result.ranking


async def test_async_save_restore(classification_csv: str, raw_df, tmp_path) -> None:
    from phronesisml import restore_async, save_async

    info = await save_async(classification_csv, str(tmp_path / "runs"), engine="pandas")
    saved = await restore_async(info["artifact_uri"])
    assert saved.model is not None
    assert len(saved.predict(raw_df.head(2))) == 2


async def test_async_recommend(classification_csv: str) -> None:
    from phronesisml import recommend_async, select_model_async

    rec = await recommend_async(classification_csv, engine="pandas")
    sel = await select_model_async(classification_csv, engine="pandas")
    assert rec.best_model_type == sel.best_model_type
    assert rec.best_score == sel.best_score


async def test_async_load(classification_csv: str, raw_df, tmp_path) -> None:
    from phronesisml import load_async, save_async

    info = await save_async(classification_csv, str(tmp_path / "runs"), engine="pandas")
    saved = await load_async(info["artifact_uri"])
    assert saved.model is not None
    assert len(saved.predict(raw_df.head(2))) == 2


async def test_async_introspection() -> None:
    from phronesisml import capabilities_async, health_async, version_async

    assert await version_async() == __version__
    info = await capabilities_async()
    assert info["name"] == "phronesisml"
    report = await health_async()
    assert report["status"] == "ok"
