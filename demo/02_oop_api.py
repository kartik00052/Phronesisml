"""Demo 2 — OOP API: incremental pipeline with the AetherML class."""
from aetherml import AetherML

print("=" * 60)
print("DEMO 2: AetherML class — step by step")
print("=" * 60)

ml = AetherML("demo/customers.csv")

ml.load()
print("[1] Data loaded")
print(f"    {ml}")

s = ml.summary()
print(f"[2] Summary: {s.rows} rows x {s.columns} columns, {s.memory_mb:.1f} MB")
print(f"    Numeric columns: {s.numeric_columns}")

ml.clean(null_strategy="drop")
print("[3] Data cleaned (ETL)")

v = ml.validate()
print(f"[4] Validation: {'PASSED' if v.passed else 'FAILED'}")
print(f"    Rows: {v.rows}, Cols: {v.columns}, Duplicates: {v.duplicate_rows}")

e = ml.eda()
print(f"[5] EDA: {e.shape[0]} rows, {len(e.numeric_columns)} numeric cols")

t = ml.detect_target()
print(f"[6] Target: {t.column} (task={t.task_type}, confidence={t.confidence:.2f})")

f = ml.engineer_features()
print(f"[7] Features: {f.n_features} features from {f.n_rows} rows")

m = ml.train()
print(f"[8] Model: {m.model_type}, score={m.score:.4f}, trials={m.trials_used}")

ev = ml.evaluate()
print(f"[9] Eval: accuracy={ev.accuracy}, f1={ev.f1_macro}, r2={ev.r2}")

ex = ml.explain()
print(f"[10] Explain: {ex.explainer_type}, {len(ex.feature_importance)} features")

report = ml.report()
print(f"[11] Report: {len(report)} chars")
print()
print("--- Report Preview (first 500 chars) ---")
print(report[:500])
print("---")
print()
print(f"Final: {ml}")
