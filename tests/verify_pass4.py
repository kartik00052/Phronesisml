"""End-to-end pipeline verification script for Pass 4."""

from __future__ import annotations

import asyncio

import aetherml


async def main() -> None:
    result = await aetherml.run_pipeline(
        data_path="tests/fixtures/sample.csv",
        stages=[
            "upload",
            "etl",
            "validation",
            "eda",
            "target_detection",
            "feature_engineering",
        ],
    )
    print("Pipeline result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Verify no field collisions
    assert result["row_count"] == 5, f"row_count={result['row_count']}"
    assert result["column_count"] == 4, f"column_count={result['column_count']}"
    assert result["transformations"] == 2, f"transformations={result['transformations']}"
    assert result["validation_passed"] is True, f"validation_passed={result['validation_passed']}"
    assert result["target_column"] is not None, "target_column should be set"
    assert result["task_type"] is not None, "task_type should be set"
    assert result["target_detection_confidence"] is not None, "confidence should be set"
    assert result["n_features"] is not None, "n_features should be set"
    assert result["n_features"] > 0, f"n_features={result['n_features']}"

    print("\nAll assertions passed!")


if __name__ == "__main__":
    asyncio.run(main())
