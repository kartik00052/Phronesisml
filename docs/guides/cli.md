# CLI

PhronesisML provides a Typer-based CLI that wraps the SDK.

!!! info
    Install the CLI extras first: `pip install phronesisml[cli]`

## Commands

### `phronesisml run`

Run the full ML pipeline on a dataset:

```bash
phronesisml run data/customers.csv
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
phronesisml run data.csv --engine polars --nulls fill

# Verbose output
phronesisml run data.csv -v
```

### `phronesisml info`

Show information about PhronesisML:

```bash
phronesisml info
```

## Running via Docker

```bash
docker run -p 8000:8000 ghcr.io/kartik00052/phronesisml:v0.2.0
```

This starts the REST API server, not the CLI.
