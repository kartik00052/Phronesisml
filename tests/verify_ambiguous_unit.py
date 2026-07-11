"""Verify ambiguous target detection behavior — the key Pass 4 test case."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pandas as pd

from aetherml.agents.target_detection.agent import TargetDetectionAgent
from aetherml.data.profilers.stats import profile_dataset
from aetherml.engines.pandas_engine import PandasEngine
from aetherml.ml.target_detection.detector import AMBIGUITY_THRESHOLD


async def main() -> None:
    engine = PandasEngine()
    agent = TargetDetectionAgent(engine=engine)

    # Ambiguous: 'grade' is numeric with exactly 3 unique values
    # Feature columns are constant (1 unique each) so they get zero
    # confidence and 'grade' is the only candidate.
    df = pd.DataFrame(
        {
            "feature_a": [1.0] * 10,
            "feature_b": [10] * 10,
            "grade": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        }
    )

    profile = profile_dataset(df, engine)
    state = SimpleNamespace(
        processed_data=df,
        data_profile=profile,
        validated_data=None,
    )

    result = await agent.run(state)

    print("=== AMBIGUOUS TARGET TEST ===")
    print(f"target_column:   {result.data['target_column']}")
    print(f"task_type:       {result.data['task_type']}")
    print(f"confidence:      {result.data['target_detection_confidence']}")
    print(f"ambiguity_reason: {result.data['ambiguity_reason']}")
    print(f"THRESHOLD:       {AMBIGUITY_THRESHOLD}")
    print()

    # The critical assertions
    assert result.data["target_column"] == "grade"
    assert result.data["task_type"] == "ambiguous"
    assert result.data["target_detection_confidence"] < AMBIGUITY_THRESHOLD
    assert result.data["ambiguity_reason"] is not None
    assert "3 unique values" in result.data["ambiguity_reason"]

    print("ALL ASSERTIONS PASSED!")
    print()
    print("The agent surfaces low confidence (below threshold) and a")
    print("human-readable ambiguity_reason instead of silently guessing.")


if __name__ == "__main__":
    asyncio.run(main())
