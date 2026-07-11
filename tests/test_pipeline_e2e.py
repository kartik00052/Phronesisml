"""End-to-end regression test for the full 11-stage pipeline.

This test runs the complete pipeline (upload → etl → validation → eda
→ target_detection → feature_engineering → model_selection → evaluation
→ explainability → reporting → storage) on a small synthetic dataset
and asserts it completes without exception.

This is the primary regression test for the data contract bug
(Feature Engineering drops target → Model Selection gets KeyError).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from aetherml.workflow.graph import PIPELINE_ORDER


@pytest.fixture
def synthetic_csv(tmp_path: Path) -> str:
    """Write a small synthetic classification dataset to a CSV file."""
    rng = __import__("numpy").random.RandomState(42)
    n = 50
    df = pd.DataFrame(
        {
            "feature_a": rng.randn(n),
            "feature_b": rng.randn(n),
            "feature_c": rng.randn(n),
            "label": rng.choice(["spam", "ham"], size=n),
        }
    )
    csv_path = tmp_path / "synthetic.csv"
    df.to_csv(csv_path, index=False)
    return str(csv_path)


class TestFullPipelineE2E:
    """Run the full 11-stage pipeline end-to-end on a synthetic dataset."""

    @pytest.mark.asyncio
    async def test_full_11_stage_pipeline_completes(self, synthetic_csv: str) -> None:
        """The full pipeline must complete without exception.

        This is the primary regression test for the KeyError: 'target'
        bug.  Feature Engineering drops the target from state.features;
        Model Selection must reconstruct the full DataFrame by joining
        with upstream data.
        """
        from aetherml import run_pipeline

        result = await run_pipeline(
            data_path=synthetic_csv,
            stages=list(PIPELINE_ORDER),
        )

        # Pipeline must return a summary dict
        assert isinstance(result, dict)

        # All expected summary keys must be present
        assert "row_count" in result
        assert "column_count" in result
        assert "target_column" in result
        assert "task_type" in result
        assert "best_model_type" in result
        assert "evaluation_metrics" in result

        # Data must have been processed
        assert result["row_count"] == 50
        assert result["target_column"] is not None
        assert result["task_type"] in ("classification", "regression", "ambiguous")
        assert result["best_model_type"] is not None
        assert result["evaluation_metrics"] is not None

    @pytest.mark.asyncio
    async def test_pipeline_stages_all_executed(self, synthetic_csv: str) -> None:
        """Every stage in PIPELINE_ORDER must be represented in the result."""
        from aetherml import run_pipeline

        result = await run_pipeline(
            data_path=synthetic_csv,
            stages=list(PIPELINE_ORDER),
        )

        # Upload stage must have loaded data
        assert result["row_count"] is not None and result["row_count"] > 0

        # Validation must have run
        assert result["validation_passed"] is not None

        # Target detection must have identified a target
        assert result["target_column"] is not None

        # Feature engineering must have produced features
        assert result["n_features"] is not None and result["n_features"] > 0

        # Model selection must have trained a model
        assert result["best_model_type"] is not None

        # Evaluation must have computed metrics
        assert result["evaluation_metrics"] is not None
        assert len(result["evaluation_metrics"]) > 0

        # Explainability must have produced an explanation
        assert result["explanation_sampled"] is not None

        # Reporting must have produced a report
        assert result["final_report_length"] is not None
        assert result["final_report_length"] > 0
