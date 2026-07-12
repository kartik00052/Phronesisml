"""Demo 1 — Simple API: one-liner functions for quick ML."""
from aetherml import analyze, train

print("=" * 60)
print("DEMO 1a: analyze() — profile a dataset in one call")
print("=" * 60)
profile = analyze("demo/customers.csv")
print(f"  Rows:       {profile.shape[0]}")
print(f"  Columns:    {profile.shape[1]}")
print(f"  Columns:    {list(profile.dtypes.keys())}")
print(f"  Memory:     {profile.memory_usage_bytes / 1024:.1f} KB")
print(f"  Validation: {'PASS' if profile.validation_passed else 'FAIL'}")
print()

print("=" * 60)
print("DEMO 1b: train() — full ML pipeline in one call")
print("=" * 60)
result = train("demo/customers.csv")
print(f"  Model:      {result.best_model_type}")
print(f"  Score:      {result.best_score:.4f}")
print(f"  Task:       {result.task_type}")
print(f"  Train cost: {result.estimated_training_cost}")
print(f"  Explainer:  {result.explainer_type}")
print(f"  Top features:")
for feat, imp in sorted(result.feature_importance.items(), key=lambda x: -x[1])[:5]:
    print(f"    {feat:20s} {imp:.4f}")
print(f"  Report length: {len(result.report)} chars")
