"""Generate sample customer dataset for demos."""
import numpy as np
import pandas as pd

np.random.seed(42)
n = 200
df = pd.DataFrame(
    {
        "age": np.random.randint(18, 70, n),
        "income": np.random.normal(50000, 15000, n).round(0),
        "score": np.random.uniform(300, 850, n).round(1),
        "years_employed": np.random.randint(0, 30, n),
        "debt_ratio": np.random.uniform(0.0, 1.0, n).round(3),
        "num_products": np.random.randint(1, 8, n),
        "churned": np.random.choice([0, 1], n, p=[0.7, 0.3]),
    }
)
df.to_csv("demo/customers.csv", index=False)
print(f"Created demo/customers.csv: {n} rows, {df.shape[1]} columns")
print(df.head())
