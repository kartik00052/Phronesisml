# Troubleshooting

Common issues and their solutions.

---

## Installation Issues

### `ModuleNotFoundError: No module named 'phronesisml'`

**Cause:** Package not installed or wrong Python environment.

```bash
# Verify installation
pip show phronesisml

# Reinstall if needed
pip install --force-reinstall phronesisml
```

### `ERROR: Could not find a version that satisfies the requirement`

**Cause:** Python version too old.

```bash
python --version  # Need 3.11+
```

### `xlrd not found` when reading `.xls` files

**Cause:** Legacy Excel format requires an extra dependency.

```bash
pip install xlrd
```

---

## Data Issues

### `DataLoadError: Cannot detect format from extension`

**Cause:** File has an unrecognized extension.

**Solution:** Rename the file with a supported extension (`.csv`, `.xlsx`, `.parquet`, `.json`, `.feather`) or pass the format explicitly:

```python
from phronesisml.data.loaders.file_loader import load_file
df = load_file("data.xyz", engine, format="csv")
```

### `DataLoadError: File does not exist`

**Cause:** Wrong file path.

```python
from pathlib import Path
path = Path("data.csv")
print(f"Exists: {path.exists()}")
print(f"Absolute: {path.resolve()}")
```

### `DataValidationError: DataFrame is empty`

**Cause:** The uploaded file has no rows.

**Solution:** Check the source data. If the file is valid but the loader is misconfigured, try a different engine:

```python
profile = analyze("data.csv", engine="pandas")  # Try pandas explicitly
```

---

## Engine Issues

### `EngineError: Expected Polars DataFrame, got DataFrame`

**Cause:** Engine type mismatch. This was a known bug in v0.2.0 — Polars engine methods didn't handle Pandas DataFrames. **Fixed in v0.2.1.**

**Solution:** Update to the latest version:

```bash
pip install --upgrade phronesisml
```

### `ModuleNotFoundError: No module named 'polars'`

**Cause:** Polars not installed.

```bash
pip install polars
```

### `ModuleNotFoundError: No module named 'pyspark'`

**Cause:** Spark not installed.

```bash
pip install phronesisml[spark]
```

---

## Training Issues

### `WorkflowError: Pipeline execution failed`

**Cause:** An agent in the pipeline failed. The error message will indicate which agent.

**Debugging:**

```python
from phronesisml import Phronesis

ml = Phronesis("data.csv")

# Run stages individually to find the failure
ml.load()
ml.clean()
ml.validate()
ml.eda()
target = ml.detect_target()
print(f"Target: {target.column}, Task: {target.task_type}")

# Continue step by step
features = ml.engineer_features()
model = ml.train()  # This is where it might fail
```

### Low accuracy / poor model performance

**Causes and solutions:**

| Symptom | Possible Cause | Solution |
|---------|---------------|----------|
| Accuracy near random | Target column misidentified | Set target manually |
| All metrics are 0 | Data not cleaned properly | Try `null_strategy="fill"` |
| Very slow training | Large dataset, no engine selected | Use `engine="polars"` |
| Overfitting | Small dataset, complex model | Use `cv=5` for cross-validation |

### `AgentError: Agent 'target_detection' failed`

**Cause:** Target detection couldn't identify a suitable target column.

**Solution:** Check your data — the target column should be present and have a reasonable number of unique values (2–50 for classification, >5 for regression).

---

## CLI Issues

### `phronesisml: command not found`

**Cause:** CLI extras not installed.

```bash
pip install phronesisml[cli]
```

### `Click requires a unicode text terminal`

**Cause:** Running CLI in a non-interactive environment (CI).

**Solution:** Use the Python SDK instead:

```python
from phronesisml import Phronesis
ml = Phronesis("data.csv")
ml.run()
```

---

## Performance Issues

### Training is slow

**Solutions:**

1. **Use Polars:** `config.engine.preferred = "polars"`
2. **Skip unnecessary stages:** Only run what you need
3. **Reduce dataset size:** Sample large datasets before training
4. **Use cross-validation sparingly:** `cv=3` instead of `cv=10`

### High memory usage

**Solutions:**

1. **Use Polars:** More memory-efficient than Pandas
2. **Use Spark:** For datasets > 500 MB: `pip install phronesisml[spark]`
3. **Drop unnecessary columns:** Before training, remove columns you don't need

### Graph compilation is slow on first run

**Expected behavior:** The first `run()` call compiles the LangGraph graph (~0.5s overhead). Subsequent calls reuse the cached graph.

---

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from phronesisml import Phronesis
ml = Phronesis("data.csv")
ml.run()
```

Or via CLI:

```bash
phronesisml run data.csv -v
```

### Inspect Intermediate State

```python
ml = Phronesis("data.csv")
ml.run()

# Access the full workflow state
state = ml._state

print(f"Raw data shape: {state.raw_data.shape}")
print(f"Processed data shape: {state.processed_data.shape}")
print(f"Target column: {state.target_column}")
print(f"Task type: {state.task_type}")
print(f"Feature names: {state.feature_names}")
print(f"Model type: {type(state.trained_model).__name__}")
```

### Test Individual Agents

```python
from phronesisml.agents.upload.agent import UploadAgent
from phronesisml.engines.pandas_engine import PandasEngine

engine = PandasEngine()
agent = UploadAgent(engine)

# Test with a mock state
result = agent.run({"data_path": "test.csv"})
print(f"Success: {result.success}")
print(f"Data shape: {result.data['raw_data'].shape}")
```

---

## Getting Help

If none of these solutions work:

1. **Check the [GitHub Issues](https://github.com/kartik00052/PhronesisML/issues)** — search for similar problems
2. **Open a new issue** with:
   - Python version (`python --version`)
   - PhronesisML version (`pip show phronesisml`)
   - Full error traceback
   - Minimal reproducible example
3. **Check the [API Reference](api.md)** for method signatures and return types
