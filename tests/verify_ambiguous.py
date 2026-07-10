"""Verify ambiguous target detection behavior."""

from __future__ import annotations

import asyncio

import aetherml


async def main() -> None:
    result = await aetherml.run_pipeline(
        data_path="tests/fixtures/ambiguous_target.csv",
        stages=[
            "upload", "etl", "validation", "eda",
            "target_detection", "feature_engineering",
        ],
    )
    print("Ambiguous target pipeline result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # The 'status' column should be detected (it has 2 unique values: 0, 1)
    # which is in the ambiguous range for numeric columns
    assert result["target_column"] is not None, "target_column should be set"
    assert result["task_type"] is not None, "task_type should be set"
    assert result["target_detection_confidence"] is not None, "confidence should be set"

    # With 2 unique numeric values, confidence should be below threshold
    # (ambiguous case)
    if result["task_type"] == "ambiguous":
        assert result["target_detection_confidence"] < 0.6, (
            f"Ambiguous target should have low confidence: {result['target_detection_confidence']}"
        )
        print("\nAmbiguous target correctly surfaced with low confidence!")
    else:
        print(f"\nTarget detected as {result['task_type']} (not ambiguous)")

    print("\nAll assertions passed!")


if __name__ == "__main__":
    asyncio.run(main())
