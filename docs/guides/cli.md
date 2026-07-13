# CLI

AetherML provides a Typer-based CLI that wraps the SDK.

!!! info
    Install the CLI extras first: `pip install aetherml[cli]`

## Commands

### `aetherml run`

Run the full ML pipeline on a dataset:

```bash
aetherml run data/customers.csv
```

**Options:**

| Flag | Description |
|---|---|
| `--engine`, `-e` | Force engine: `pandas`, `polars`, `spark` |
| `--nulls`, `-n` | Null strategy: `drop`, `fill`, `flag` |
| `--verbose`, `-v` | Enable debug logging |

**Examples:**

```bash
# Use Polars engine with fill strategy
aetherml run data.csv --engine polars --nulls fill

# Verbose output
aetherml run data.csv -v
```

### `aetherml info`

Show information about AetherML:

```bash
aetherml info
```

## Running via Docker

```bash
docker run -p 8000:8000 ghcr.io/kartik00052/aetherml:v0.1.3
```

This starts the REST API server, not the CLI.
