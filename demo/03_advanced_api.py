"""Demo 3 — Advanced API: run_pipeline with AetherMLConfig."""
import asyncio
from aetherml import run_pipeline, AetherMLConfig


async def main():
    print("=" * 60)
    print("DEMO 3a: run_pipeline() — full async pipeline")
    print("=" * 60)
    result = await run_pipeline(data_path="demo/customers.csv")
    print(f"  Target:     {result['target_column']}")
    print(f"  Task:       {result['task_type']}")
    print(f"  Model:      {result['best_model_type']}")
    print(f"  Score:      {result['best_model_score']:.4f}")
    print(f"  Features:   {result['n_features']}")
    print()

    print("=" * 60)
    print("DEMO 3b: run_pipeline() — selected stages only")
    print("=" * 60)
    result2 = await run_pipeline(
        data_path="demo/customers.csv",
        stages=["upload", "etl", "validation", "eda"],
    )
    print(f"  Validation passed: {result2['validation_passed']}")
    print(f"  Numeric columns:  {result2['numeric_columns']}")
    print()

    print("=" * 60)
    print("DEMO 3c: run_pipeline() — custom config (force Pandas)")
    print("=" * 60)
    config = AetherMLConfig()
    config.engine.preferred = "pandas"
    result3 = await run_pipeline(
        data_path="demo/customers.csv",
        config=config,
    )
    print(f"  Engine: Pandas (forced)")
    print(f"  Model:  {result3['best_model_type']}")
    print(f"  Score:  {result3['best_model_score']:.4f}")


asyncio.run(main())
