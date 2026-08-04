"""Comprehensive test suite for the ExplainabilityService.

Tests cover:
- Tree models (RandomForest, GradientBoosting, ExtraTrees, DecisionTree)
- Linear models (LinearRegression, LogisticRegression, Ridge, Lasso, ElasticNet)
- Wrapped estimators (Pipelines, GridSearchCV, CalibratedClassifierCV, VotingClassifier)
- SVM (SVC, SVR)
- KNN (KNeighborsClassifier)
- MLP (MLPClassifier)
- Fallback routing
- Resource management (sampling, background size)
- Deterministic outputs
- Empty/invalid inputs
- Feature importance generation
- Multi-class classification
- Regression
- Backward compatibility with old API

Run: python tests/test_explainability.py
"""

from __future__ import annotations

import unittest
from typing import Any

import numpy as np

# ── Helpers ───────────────────────────────────────────────────────


def _make_classification_data(
    n_samples: int = 100,
    n_features: int = 5,
    n_classes: int = 2,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    X = rng.random((n_samples, n_features))
    if n_classes == 2:
        y = (X[:, 0] > 0.5).astype(int)
    else:
        y = (X[:, 0] * n_classes).astype(int) % n_classes
    feature_names = [f"f{i}" for i in range(n_features)]
    return X, y, feature_names


def _make_regression_data(
    n_samples: int = 100,
    n_features: int = 4,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    X = rng.random((n_samples, n_features))
    y = X @ np.array([1.0, 2.0, 3.0, 4.0]) + rng.normal(0, 0.1, n_samples)
    feature_names = [f"x{i}" for i in range(n_features)]
    return X, y, feature_names


def _assert_valid_result(result: dict[str, Any], n_features: int) -> None:
    """Assert the result dict has the expected structure."""
    assert "feature_importance" in result, "Missing feature_importance"
    assert "explainer_type" in result, "Missing explainer_type"
    assert "sampled" in result, "Missing sampled"
    assert "n_samples_used" in result, "Missing n_samples_used"
    assert "max_samples" in result, "Missing max_samples"
    assert isinstance(result["feature_importance"], dict), "feature_importance not a dict"
    assert len(result["feature_importance"]) > 0, "feature_importance is empty"
    assert result["explainer_type"] in {
        "TreeExplainer",
        "LinearExplainer",
        "PermutationExplainer",
        "KernelExplainer",
    }, f"Unknown explainer_type: {result['explainer_type']}"
    assert isinstance(result["sampled"], bool), "sampled not a bool"
    assert result["n_samples_used"] > 0, "n_samples_used <= 0"


# ── Tests ─────────────────────────────────────────────────────────


class TestTreeModels(unittest.TestCase):
    """Test SHAP explainability for tree-based models."""

    def test_random_forest_classifier(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_gradient_boosting_classifier(self) -> None:
        from sklearn.ensemble import GradientBoostingClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = GradientBoostingClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_extra_trees_classifier(self) -> None:
        from sklearn.ensemble import ExtraTreesClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = ExtraTreesClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_decision_tree_classifier(self) -> None:
        from sklearn.tree import DecisionTreeClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = DecisionTreeClassifier(random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_random_forest_regressor(self) -> None:
        from sklearn.ensemble import RandomForestRegressor

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_gradient_boosting_regressor(self) -> None:
        from sklearn.ensemble import GradientBoostingRegressor

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = GradientBoostingRegressor(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")


class TestLinearModels(unittest.TestCase):
    """Test SHAP explainability for linear models."""

    def test_linear_regression(self) -> None:
        from sklearn.linear_model import LinearRegression

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = LinearRegression()
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")

    def test_logistic_regression(self) -> None:
        from sklearn.linear_model import LogisticRegression

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = LogisticRegression(max_iter=200, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")

    def test_ridge(self) -> None:
        from sklearn.linear_model import Ridge

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = Ridge()
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")

    def test_lasso(self) -> None:
        from sklearn.linear_model import Lasso

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = Lasso(max_iter=200)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")

    def test_elasticnet(self) -> None:
        from sklearn.linear_model import ElasticNet

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_regression_data()
        model = ElasticNet(max_iter=200)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")


class TestOtherModels(unittest.TestCase):
    """Test SHAP explainability for SVM, KNN, MLP (non-tree, non-linear)."""

    def test_svc(self) -> None:
        from sklearn.svm import SVC

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=60)
        model = SVC(kernel="rbf")
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        # SVM goes to PermutationExplainer (or Kernel if Permutation unavailable)
        self.assertIn(
            result["explainer_type"],
            {"PermutationExplainer", "KernelExplainer"},
        )

    def test_knn(self) -> None:
        from sklearn.neighbors import KNeighborsClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=60)
        model = KNeighborsClassifier(n_neighbors=3)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertIn(
            result["explainer_type"],
            {"PermutationExplainer", "KernelExplainer"},
        )

    def test_mlp(self) -> None:
        from sklearn.neural_network import MLPClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=80)
        model = MLPClassifier(hidden_layer_sizes=(10,), max_iter=200, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertIn(
            result["explainer_type"],
            {"PermutationExplainer", "KernelExplainer"},
        )


class TestWrappedEstimators(unittest.TestCase):
    """Test SHAP explainability for wrapped estimators."""

    def test_pipeline(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", RandomForestClassifier(n_estimators=10, random_state=42)),
            ]
        )
        pipe.fit(X, y)
        result = compute_explanations(pipe, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_grid_search_cv(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import GridSearchCV

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=60)
        model = GridSearchCV(
            RandomForestClassifier(random_state=42),
            {"n_estimators": [5, 10]},
            cv=2,
            n_jobs=1,
        )
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_calibrated_classifier(self) -> None:
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.svm import LinearSVC

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=60)
        base = LinearSVC(max_iter=200, random_state=42)
        model = CalibratedClassifierCV(base, cv=2)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        # CalibratedClassifierCV is NOT unwrapped — it's a valid fitted wrapper
        # SHAP routes it through PermutationExplainer (non-tree, non-linear)
        self.assertIn(
            result["explainer_type"],
            {"PermutationExplainer", "KernelExplainer"},
        )

    def test_voting_classifier(self) -> None:
        from sklearn.ensemble import RandomForestClassifier, VotingClassifier
        from sklearn.linear_model import LogisticRegression

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=80)
        model = VotingClassifier(
            estimators=[
                ("lr", LogisticRegression(max_iter=200, random_state=42)),
                ("rf", RandomForestClassifier(n_estimators=5, random_state=42)),
            ],
            voting="soft",
        )
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        # First estimator is LogisticRegression → LinearExplainer
        self.assertEqual(result["explainer_type"], "LinearExplainer")

    def test_bagging_classifier(self) -> None:
        from sklearn.ensemble import BaggingClassifier, RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_samples=60)
        model = BaggingClassifier(
            estimator=RandomForestClassifier(n_estimators=5, random_state=42),
            n_estimators=3,
            random_state=42,
        )
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))


class TestMultiClass(unittest.TestCase):
    """Test SHAP explainability for multi-class classification."""

    def test_random_forest_multiclass(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_classes=4)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")
        # All feature importance values should be non-negative
        for v in result["feature_importance"].values():
            self.assertGreaterEqual(v, 0.0)


class TestResourceManagement(unittest.TestCase):
    """Test resource management (sampling, background size)."""

    def test_sampling_with_large_dataset(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import ExplainConfig, compute_explanations

        X, y, names = _make_classification_data(n_samples=200)
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(X, y)

        config = ExplainConfig(max_samples=50)
        result = compute_explanations(model, X, names, config=config)
        _assert_valid_result(result, len(names))
        self.assertTrue(result["sampled"])
        self.assertEqual(result["n_samples_used"], 50)
        self.assertEqual(result["max_samples"], 50)

    def test_no_sampling_when_within_limit(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import ExplainConfig, compute_explanations

        X, y, names = _make_classification_data(n_samples=30)
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(X, y)

        config = ExplainConfig(max_samples=100)
        result = compute_explanations(model, X, names, config=config)
        _assert_valid_result(result, len(names))
        self.assertFalse(result["sampled"])
        self.assertEqual(result["n_samples_used"], 30)

    def test_deterministic_sampling(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import ExplainConfig, compute_explanations

        X, y, names = _make_classification_data(n_samples=200)
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(X, y)

        config = ExplainConfig(max_samples=50, random_seed=42)
        r1 = compute_explanations(model, X, names, config=config)
        r2 = compute_explanations(model, X, names, config=config)
        # Same seed → same sample → same importance values
        self.assertEqual(r1["feature_importance"], r2["feature_importance"])

    def test_background_size_configurable(self) -> None:
        from phronesisml.ml.explainability.service import ExplainConfig

        config = ExplainConfig(background_size=50)
        self.assertEqual(config.background_size, 50)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_dataset_raises(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X = np.empty((0, 3))
        model = RandomForestClassifier(n_estimators=5)
        # Can't fit on empty data, but we test the validation
        with self.assertRaises(ValueError):
            compute_explanations(model, X, ["a", "b", "c"])

    def test_no_features_raises(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X = np.empty((10, 0))
        model = RandomForestClassifier(n_estimators=5)
        with self.assertRaises((ValueError, IndexError)):
            compute_explanations(model, X, [])

    def test_single_feature(self) -> None:
        from sklearn.tree import DecisionTreeClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X = np.random.default_rng(42).random((50, 1))
        y = (X[:, 0] > 0.5).astype(int)
        model = DecisionTreeClassifier(random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, ["only_feature"])
        _assert_valid_result(result, 1)

    def test_missing_shap_library(self) -> None:
        import unittest.mock

        with unittest.mock.patch.dict("sys.modules", {"shap": None}):
            from sklearn.ensemble import RandomForestClassifier

            from phronesisml.ml.explainability.service import compute_explanations

            X, y, names = _make_classification_data(n_samples=20)
            model = RandomForestClassifier(n_estimators=5, random_state=42)
            model.fit(X, y)
            with self.assertRaises(ImportError):
                compute_explanations(model, X, names)


class TestBackwardCompatibility(unittest.TestCase):
    """Test that the old shap_explainer.py API still works."""

    def test_old_api_imports(self) -> None:
        from phronesisml.ml.explainability.shap_explainer import (
            _LINEAR_MODEL_KEYWORDS,
            _TREE_MODEL_KEYWORDS,
            DEFAULT_MAX_SAMPLES,
        )

        self.assertEqual(DEFAULT_MAX_SAMPLES, 100)
        self.assertIn("forest", _TREE_MODEL_KEYWORDS)
        self.assertIn("linear", _LINEAR_MODEL_KEYWORDS)

    def test_old_api_tree_model(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.shap_explainer import compute_shap_explanations

        X, y, names = _make_classification_data()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_shap_explanations(model, X, names, max_samples=50)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "TreeExplainer")

    def test_old_api_linear_model(self) -> None:
        from sklearn.linear_model import LinearRegression

        from phronesisml.ml.explainability.shap_explainer import compute_shap_explanations

        X, y, names = _make_regression_data()
        model = LinearRegression()
        model.fit(X, y)
        result = compute_shap_explanations(model, X, names, max_samples=50)
        _assert_valid_result(result, len(names))
        self.assertEqual(result["explainer_type"], "LinearExplainer")


class TestFeatureImportance(unittest.TestCase):
    """Test that feature importance outputs are valid and consistent."""

    def test_importance_values_non_negative(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        for name, importance in result["feature_importance"].items():
            self.assertGreaterEqual(importance, 0.0, f"Negative importance for {name}")

    def test_importance_keys_match_feature_names(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        self.assertEqual(set(result["feature_importance"].keys()), set(names))

    def test_importance_sums_to_positive(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data()
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        total = sum(result["feature_importance"].values())
        self.assertGreater(total, 0.0, "Total importance should be positive")

    def test_more_important_feature_ranked_higher(self) -> None:
        """Feature f0 should have highest importance since y depends on it."""
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import compute_explanations

        X, y, names = _make_classification_data(n_features=5)
        model = RandomForestClassifier(n_estimators=20, random_state=42)
        model.fit(X, y)
        result = compute_explanations(model, X, names)
        # f0 should be the most important feature
        sorted_features = sorted(
            result["feature_importance"].items(), key=lambda x: x[1], reverse=True
        )
        self.assertEqual(sorted_features[0][0], "f0")


class TestModelUnwrapping(unittest.TestCase):
    """Test that _unwrap_model correctly handles various wrappers."""

    def test_unwrap_pipeline(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        from phronesisml.ml.explainability.service import _unwrap_model

        pipe = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", RandomForestClassifier(n_estimators=5)),
            ]
        )
        unwrapped = _unwrap_model(pipe)
        self.assertIsInstance(unwrapped, RandomForestClassifier)

    def test_unwrap_grid_search(self) -> None:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import GridSearchCV

        from phronesisml.ml.explainability.service import _unwrap_model

        X, y, _ = _make_classification_data(n_samples=30)
        gs = GridSearchCV(
            RandomForestClassifier(random_state=42),
            {"n_estimators": [5]},
            cv=2,
            n_jobs=1,
        )
        gs.fit(X, y)
        unwrapped = _unwrap_model(gs)
        self.assertIsInstance(unwrapped, RandomForestClassifier)

    def test_unwrap_already_base(self) -> None:
        from sklearn.ensemble import RandomForestClassifier

        from phronesisml.ml.explainability.service import _unwrap_model

        model = RandomForestClassifier(n_estimators=5)
        unwrapped = _unwrap_model(model)
        self.assertIs(unwrapped, model)


class TestExplainabilityAgent(unittest.TestCase):
    """Agent-level guard: designated target must never appear in features."""

    def test_agent_excludes_designated_target_from_feature_names(self) -> None:
        import asyncio
        from types import SimpleNamespace

        import pandas as pd
        from sklearn.linear_model import LinearRegression

        from phronesisml.agents.explainability.agent import ExplainabilityAgent
        from phronesisml.engines.pandas_engine import PandasEngine

        rng = np.random.RandomState(0)
        X = rng.randn(30, 2)
        y = X[:, 0] * 2.0 + 1.0
        model = LinearRegression().fit(X, y)

        df = pd.DataFrame(X, columns=["x1", "x2"])
        df["target"] = y

        agent = ExplainabilityAgent(engine=PandasEngine())
        state = SimpleNamespace(
            trained_model=model,
            features=df,
            validated_data=None,
            processed_data=None,
            target_column="target",
            feature_names=["x1", "x2", "target"],  # leak from upstream stage
        )
        result = asyncio.run(agent.run(state))
        self.assertTrue(result.success)
        report = result.data["explanation_report"]
        self.assertNotIn("target", report["feature_importance"])
        self.assertEqual(set(report["feature_importance"]), {"x1", "x2"})
        self.assertEqual(report["n_features_used"], 2)

    def test_agent_skips_stale_feature_names_absent_from_frame(self) -> None:
        import asyncio
        from types import SimpleNamespace

        import pandas as pd
        from sklearn.linear_model import LinearRegression

        from phronesisml.agents.explainability.agent import ExplainabilityAgent
        from phronesisml.engines.pandas_engine import PandasEngine

        rng = np.random.RandomState(1)
        X = rng.randn(20, 2)
        y = X[:, 0] - X[:, 1]
        model = LinearRegression().fit(X, y)

        df = pd.DataFrame(X, columns=["x1", "x2"])
        agent = ExplainabilityAgent(engine=PandasEngine())
        state = SimpleNamespace(
            trained_model=model,
            features=df,
            validated_data=None,
            processed_data=None,
            target_column=None,
            feature_names=["x1", "x2", "ghost"],  # stale name not in frame
        )
        result = asyncio.run(agent.run(state))
        self.assertTrue(result.success)
        report = result.data["explanation_report"]
        self.assertEqual(set(report["feature_importance"]), {"x1", "x2"})
        self.assertEqual(report["n_features_used"], 2)

    def test_explanation_report_carries_resource_fields(self) -> None:
        from phronesisml.sdk import ExplanationReport

        report = ExplanationReport(
            feature_importance={"a": 1.0},
            explainer_type="TreeExplainer",
            sampled=False,
            n_samples_used=50,
            n_features_used=1,
            max_samples=100,
        )
        self.assertEqual(report.n_features_used, 1)
        self.assertEqual(report.max_samples, 100)


# ── Runner ────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
