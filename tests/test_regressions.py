"""Regression tests for Phase-1 correctness hardening (BUG-01..05, ISSUE-06..08).

Each test pins the fixed behaviour so the original defect cannot silently
return:

- BUG-01: feature engineering must not mutate upstream workflow state,
  and the outlier flag is metadata-only by default.
- BUG-02: ambiguous targets resolve to a concrete task class from the
  actual target values, and metrics derive from the selected model class.
- BUG-04: ``best_pipeline`` exposes both ``params`` and ``best_params``;
  readers prefer ``best_params`` and fall back to ``params``.
- BUG-05: ``run_id``/``status`` are populated for every pipeline run.
- ISSUE-07: the ``max_time_seconds`` time budget is enforced between
  trials with bounded single-trial overshoot.
"""

from __future__ import annotations

import warnings
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")
warnings.filterwarnings("ignore", category=FutureWarning, module="sklearn")


# ── Helpers ───────────────────────────────────────────────────────────


def _make_regression_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "sqft": rng.integers(500, 5000, n),
            "bedrooms": rng.integers(1, 6, n),
            "age": rng.integers(0, 100, n),
            "price": (rng.random(n) * 300000 + 100000).round(2),
        }
    )
    return df


def _make_classification_df(n: int = 500, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "age": rng.integers(18, 80, n),
            "income": rng.normal(50000, 15000, n).round(2),
            "score": rng.uniform(0, 100, n).round(1),
            "category": rng.choice(["A", "B", "C"], n),
            "target": rng.choice([0, 1], n),
        }
    )
    return df


def _write_csv(df: pd.DataFrame, path: Any) -> str:
    df.to_csv(path, index=False)
    return str(path)


# ── BUG-01: feature engineering mutates upstream state ────────────────


def test_bug01_engineer_does_not_mutate_input_frame() -> None:
    from phronesisml.engines.pandas_engine import PandasEngine
    from phronesisml.ml.feature_engineering.engineer import engineer_features

    df = _make_regression_df(n=300)
    engine = PandasEngine()
    df_orig = df.copy(deep=True)

    result, log = engineer_features(df, engine, target_column="price")

    # Caller frame must be untouched (BUG-01).
    pd.testing.assert_frame_equal(df, df_orig)
    # Outlier flag must NOT be part of the feature matrix by default.
    assert "outlier_flag" not in result.columns
    # But the log should still record the outlier metadata.
    outlier_steps = [s for s in log["steps"] if s.get("action") == "detect_outliers"]
    assert len(outlier_steps) == 1
    assert outlier_steps[0]["outlier_flag_included"] is False


def test_bug01_outlier_flag_only_when_opted_in() -> None:
    from phronesisml.engines.pandas_engine import PandasEngine
    from phronesisml.ml.feature_engineering.engineer import engineer_features

    df = _make_regression_df(n=300)
    # Inject clear outliers so IQR detection actually flags rows.
    df.loc[0, "age"] = 5000
    df.loc[1, "age"] = -5000
    df.loc[2, "sqft"] = 500000
    engine = PandasEngine()
    df_orig = df.copy(deep=True)

    result, log = engineer_features(
        df,
        engine,
        target_column="price",
        include_outlier_flag=True,
        select_features=False,
    )

    # Caller frame still untouched.
    pd.testing.assert_frame_equal(df, df_orig)
    # Opt-in exposes the flag column and records it in the log.
    assert "outlier_flag" in result.columns
    outlier_steps = [s for s in log["steps"] if s.get("action") == "detect_outliers"]
    assert len(outlier_steps) == 1
    assert outlier_steps[0]["outliers_detected"] > 0
    assert outlier_steps[0]["outlier_flag_included"] is True


def test_bug01_feature_selection_config_plumbs_flag() -> None:
    from phronesisml.configs.settings import FeatureSelectionConfig

    # Default off, opt-in available (BUG-01 plumbing).
    assert FeatureSelectionConfig().include_outlier_flag is False
    assert FeatureSelectionConfig(include_outlier_flag=True).include_outlier_flag is True


# ── BUG-02: ambiguous-target task class + metric consistency ──────────


def test_bug02_resolve_task_class_mapping() -> None:
    from phronesisml.ml.automl.auto_selector import resolve_task_class

    continuous = pd.Series(np.random.default_rng(0).normal(size=100))
    assert resolve_task_class(continuous, "ambiguous") == "regression"
    assert resolve_task_class(continuous, "ambiguous") != "classification"

    # Non-integral values → regression even with low cardinality.
    non_integral = pd.Series([0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5])
    assert resolve_task_class(non_integral, "ambiguous") == "regression"

    # Integral values with low cardinality → classification.
    integral_low = pd.Series([0, 1, 2, 3, 4] * 4)
    assert resolve_task_class(integral_low, "ambiguous") == "classification"

    # Explicit task types pass through unchanged.
    assert resolve_task_class(continuous, "classification") == "classification"
    assert resolve_task_class(continuous, "regression") == "regression"


def test_bug02_ambiguous_classifier_on_continuous_target_reports_no_metrics() -> None:
    from phronesisml.ml.evaluation.metrics import evaluate_model

    class FakeClassifier:
        """Minimal sklearn-like classifier with a trained ``classes_``."""

        def __init__(self, classes: Any) -> None:
            self.classes_ = classes

        def predict(self, features: Any) -> Any:
            return np.zeros(len(features), dtype=int)

    df = _make_regression_df(n=200)
    model = FakeClassifier(classes=np.array([0, 1]))

    report = evaluate_model(
        model=model,
        df=df,
        target_column="price",
        task_type="ambiguous",
    )

    # A classifier on a continuous target yields NO fabricated metrics
    # and an explicit caveat (BUG-02 fix).
    assert report["metrics"] == {}
    assert "classifier" in (report["ambiguity_caveat"] or "")


def test_bug02_ambiguous_regressor_yields_regression_metrics() -> None:
    from sklearn.linear_model import LinearRegression

    from phronesisml.ml.evaluation.metrics import evaluate_model

    df = _make_regression_df(n=200)
    features = ["sqft", "bedrooms", "age"]
    model = LinearRegression()
    model.fit(df[features].values, df["price"].values)

    report = evaluate_model(
        model=model,
        df=df,
        target_column="price",
        feature_names=features,
        task_type="ambiguous",
    )

    metrics = report["metrics"]
    # Regression metrics, and never classification accuracy.
    assert {"mae", "rmse", "r2"} <= set(metrics)
    assert "accuracy" not in metrics


def test_bug02_trainer_scoring_matches_task_class() -> None:
    from phronesisml.engines.pandas_engine import PandasEngine
    from phronesisml.ml.automl.auto_selector import recommend_models
    from phronesisml.ml.automl.trainer import train_models

    df = _make_classification_df(n=400)
    engine = PandasEngine()
    cands = recommend_models("ambiguous", 400, 3, 3, 0)

    result = train_models(
        df,
        engine,
        cands,
        target_column="target",
        task_type="ambiguous",
        cv=3,
        max_trials=6,
    )

    # Integral low-cardinality target resolves to classification.
    assert result["task_class"] == "classification"
    assert len(result["cv_results"]) > 0
    # Accuracy-based scores are within [0, 1].
    for entry in result["cv_results"]:
        assert 0.0 <= entry["score"] <= 1.0


# ── BUG-04: params / best_params key consistency ──────────────────────


def test_bug04_best_pipeline_exposes_both_param_keys(tmp_path) -> None:
    from phronesisml.configs.settings import PhronesisConfig
    from phronesisml.sdk import Phronesis

    path = _write_csv(_make_classification_df(n=400), tmp_path / "bug04_classification.csv")
    ml = Phronesis(path, config=PhronesisConfig())
    ml.load()
    ml.clean()
    ml.validate()
    ml.eda()
    ml.detect_target()
    ml.detect_task()
    ml.engineer_features()
    info = ml.train(cv=3, model_type="logistic_regression")

    bp = ml._state.best_pipeline or {}
    # Writer emits both keys with identical values (BUG-04 fix).
    assert "params" in bp
    assert "best_params" in bp
    assert bp["params"] == bp["best_params"]
    # Reader surfaces best_params through the SDK result.
    assert bool(info.best_params)


def test_bug04_readers_fall_back_to_legacy_params_key() -> None:
    from phronesisml._result_builders import build_model_result, build_train_result

    state = SimpleNamespace(
        best_pipeline={"model_type": "x", "params": {"C": 9}, "score": 1.0},
        evaluation_report=None,
        candidate_models=[],
        task_type="classification",
        explanation_report=None,
        final_report=None,
        artifact_uri=None,
    )
    ml = SimpleNamespace(_state=state)

    # Legacy best_pipeline that only has "params" must still be read.
    assert build_model_result(ml).best_params == {"C": 9}
    assert build_train_result(ml).best_params == {"C": 9}


# ── BUG-05: run_id / status populated ────────────────────────────────


def test_bug05_run_populates_run_id_and_status(tmp_path) -> None:
    from phronesisml.configs.settings import PhronesisConfig
    from phronesisml.sdk import Phronesis

    path = _write_csv(_make_classification_df(n=300), tmp_path / "bug05_classification.csv")
    ml = Phronesis(path, config=PhronesisConfig())
    report = ml.report()

    assert ml._state.run_id is not None
    assert ml._state.run_id.startswith("run_")
    assert ml._state.status == "completed"
    assert ml._state.run_id in report
    assert "**Status:** completed" in report


def test_bug05_failed_run_records_failed_status() -> None:
    from phronesisml.configs.settings import PhronesisConfig
    from phronesisml.exceptions import WorkflowError
    from phronesisml.sdk import Phronesis

    ml = Phronesis("does_not_exist_regression_check.csv", config=PhronesisConfig())
    with pytest.raises(WorkflowError):
        ml.report()
    assert ml._state.status == "failed"


# ── ISSUE-07: HPO time budget is bounded ─────────────────────────────


def test_issue07_time_budget_truncates_and_is_bounded() -> None:
    from phronesisml.engines.pandas_engine import PandasEngine
    from phronesisml.ml.automl.auto_selector import recommend_models
    from phronesisml.ml.automl.trainer import train_models

    df = _make_regression_df(n=3000, seed=1)
    engine = PandasEngine()
    cands = recommend_models("regression", 3000, 3, 3, 0)

    result = train_models(
        df,
        engine,
        cands,
        target_column="price",
        task_type="regression",
        max_time_seconds=1.0,
        max_trials=100,
    )

    # A single in-flight trial may overshoot, but the search stops
    # between trials and truncation is surfaced (ISSUE-07).
    assert result["truncated"] is True
    assert result["time_elapsed"] < 15.0


def test_issue07_zero_budget_raises_clean_error() -> None:
    from phronesisml.engines.pandas_engine import PandasEngine
    from phronesisml.exceptions import AgentError
    from phronesisml.ml.automl.auto_selector import recommend_models
    from phronesisml.ml.automl.trainer import train_models

    df = _make_regression_df(n=300)
    engine = PandasEngine()
    cands = recommend_models("regression", 300, 3, 3, 0)

    with pytest.raises(AgentError):
        train_models(
            df,
            engine,
            cands,
            target_column="price",
            task_type="regression",
            max_time_seconds=0,
            max_trials=10,
        )
