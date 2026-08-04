# CLI

PhronesisML provides a Typer-based CLI that wraps the SDK. Run the full ML pipeline from the command line.

!!! info
    Install the CLI extras first: `pip install phronesisml[cli]`

---

## Commands

### `phronesisml run`

Run the full ML pipeline on a dataset:

```bash
phronesisml run data/customers.csv
```

**Options:**

| Flag | Short | Description | Default |
|---|---|---|---|
| `--engine` | `-e` | Force engine: `pandas`, `polars`, `spark` | auto |
| `--nulls` | `-n` | Null strategy: `drop`, `fill`, `flag` | `drop` |
| `--verbose` | `-v` | Enable debug logging | off |

**Examples:**

```bash
# Use Polars engine with fill strategy
phronesisml run data.csv --engine polars --nulls fill

# Verbose output
phronesisml run data.csv -v

# Combine options
phronesisml run data.csv -e polars -n flag -v
```

**What it does:**

1. Loads the dataset
2. Cleans nulls and encodes types
3. Validates data quality
4. Runs statistical analysis
5. Detects the prediction target
6. Engineers features
7. Selects and trains the best model
8. Evaluates performance
9. Generates a Markdown report
10. Saves artifacts to disk

### `phronesisml info`

Show information about PhronesisML:

```bash
phronesisml info
```

**Output:**

```
Phronesis v0.3.0
Python 3.12.13 (main, Jun 11 2026, 04:05:29) [MSC v.1944 64 bit (AMD64)]
  Polars: 1.43.2
  Pandas: 2.3.3
  LangGraph: installed
```

---

## Examples

### Basic Usage

```bash
# Run with defaults
phronesisml run data.csv

# Run with Polars
phronesisml run data.csv --engine polars

# Run with verbose logging
phronesisml run data.csv -v
```

### Null Handling

```bash
# Drop rows with nulls (default)
phronesisml run data.csv --nulls drop

# Fill nulls with 0
phronesisml run data.csv --nulls fill

# Flag nulls as separate columns
phronesisml run data.csv --nulls flag
```

### Engine Selection

```bash
# Force Pandas
phronesisml run data.csv --engine pandas

# Force Polars
phronesisml run data.csv --engine polars

# Force Spark (requires pyspark)
phronesisml run data.csv --engine spark
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Pipeline failed (check error output) |
| `2` | Invalid arguments |

---

## Output Format

The CLI outputs a Markdown report to stdout. Redirect it to a file:

```bash
phronesisml run data.csv > report.md
```

Or view it with a Markdown renderer:

```bash
phronesisml run data.csv | glow -
```

---

## Verbose Mode

Enable debug logging with `-v`:

```bash
phronesisml run data.csv -v
```

**Output includes:**

- File loading details
- ETL transformations
- Validation results
- Target detection confidence
- Feature engineering steps
- Model selection process
- Training progress
- Evaluation metrics

---

## Troubleshooting

### `phronesisml: command not found`

```bash
pip install phronesisml[cli]
```

### `Click requires a unicode text terminal`

This happens in non-interactive environments (CI). Use the Python SDK instead:

```python
from phronesisml import Phronesis
ml = Phronesis("data.csv")
ml.run()
```

### Slow first run

The first `run()` call compiles the LangGraph graph (~0.5s overhead). Subsequent calls reuse the cached graph.

---

## Related

- [Simple API](simple-api.md) — One-liner Python functions
- [Advanced API](advanced-api.md) — Full pipeline control
