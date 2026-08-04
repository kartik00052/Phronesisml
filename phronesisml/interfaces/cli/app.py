"""Phronesis CLI — Typer-based command-line interface.

This is a **thin consumer** of the SDK public API.  It contains no
business logic — it parses arguments, calls ``Phronesis.run_pipeline()``,
and displays results.

Entry point: ``phronesisml`` (defined in ``pyproject.toml`` ``[project.scripts]``).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

try:
    import typer
    from rich.console import Console
    from rich.logging import RichHandler
except ImportError as exc:
    raise ImportError(
        "CLI requires extra dependencies. Install with:\n  pip install phronesisml[cli]"
    ) from exc

app = typer.Typer(
    name="phronesisml",
    help="PhronesisML — Automated Machine Learning lifecycle SDK.",
    add_completion=False,
)
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )


def _require_file(data_path: str) -> str:
    """Validate a data path exists, exiting the CLI on failure."""
    if not Path(data_path).exists():
        console.print(f"[red]Error:[/red] File not found: {data_path}")
        raise typer.Exit(code=1)
    return data_path


def _fail(exc: Exception) -> None:
    """Report a command failure and exit non-zero."""
    console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(code=1) from exc


@app.command()
def run(
    data_path: str = typer.Argument(..., help="Path to the input dataset (CSV, Parquet, JSON)."),
    engine: str | None = typer.Option(
        None,
        "--engine",
        "-e",
        help="Force a specific engine (pandas, polars, spark). Default: auto-select.",
    ),
    null_strategy: str = typer.Option(
        "drop",
        "--nulls",
        "-n",
        help="Null handling strategy: drop, fill, flag.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the Phronesis pipeline on a dataset."""
    _setup_logging(verbose)

    if not Path(data_path).exists():
        console.print(f"[red]Error:[/red] File not found: {data_path}")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]Phronesis[/bold blue] — processing [cyan]{data_path}[/cyan]")

    try:
        result = asyncio.run(
            _run_pipeline(data_path=data_path, engine=engine, null_strategy=null_strategy),
        )
        console.print("[bold green]Pipeline completed successfully.[/bold green]")
        console.print(f"Rows processed: {result.get('row_count', 'N/A')}")
        console.print(f"Columns: {result.get('column_count', 'N/A')}")
        console.print(f"Transformations: {result.get('transformations', 'N/A')}")
    except Exception as exc:
        console.print(f"[red]Pipeline failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc


async def _run_pipeline(
    data_path: str,
    engine: str | None,
    null_strategy: str,
) -> dict[str, Any]:
    """Internal async pipeline runner — calls the SDK public API."""
    from phronesisml import run_pipeline

    return await run_pipeline(
        data_path=data_path,
        engine_preference=engine,
        null_strategy=null_strategy,
    )


@app.command()
def info() -> None:
    """Show Phronesis version and installed components."""
    from phronesisml import __version__

    console.print(f"[bold]Phronesis[/bold] v{__version__}")
    console.print(f"Python {sys.version}")

    # Check optional dependencies
    deps = {"polars": "Polars", "pandas": "Pandas", "langgraph": "LangGraph"}
    for module, name in deps.items():
        try:
            mod = __import__(module)
            ver = getattr(mod, "__version__", "installed")
            console.print(f"  [green]{name}[/green]: {ver}")
        except ImportError:
            console.print(f"  [yellow]{name}[/yellow]: not installed")


@app.command()
def version() -> None:
    """Print the installed phronesisml version."""
    from phronesisml import version as api_version

    console.print(api_version())


@app.command()
def capabilities() -> None:
    """Report SDK capabilities: tasks, engines, stages, APIs."""
    from phronesisml import capabilities as api_capabilities

    info = api_capabilities()
    console.print(f"[bold]phronesisml[/bold] v{info['version']} (offline={info['offline']})")
    console.print(f"[bold]Task types:[/bold] {', '.join(info['task_types'])}")
    console.print(f"[bold]Engines:[/bold] {', '.join(info['engines'].keys())}")
    console.print(
        f"[bold]Pipeline stages ({len(info['pipeline_stages'])}):[/bold] "
        + " → ".join(info["pipeline_stages"])
    )
    console.print(
        f"[bold]SDK methods ({len(info['sdk_methods'])}):[/bold] " + ", ".join(info["sdk_methods"])
    )
    console.print(
        f"[bold]CLI commands ({len(info['cli_commands'])}):[/bold] "
        + ", ".join(info["cli_commands"])
    )
    console.print(f"[bold]Extras:[/bold] {', '.join(info['extras'])}")


@app.command()
def doctor() -> None:
    """Run offline dependency and self checks."""
    from phronesisml import health

    report = health()
    if report["status"] == "ok":
        console.print(
            f"[bold green]status: ok[/bold green] (phronesisml v{report['version']}, "
            f"Python {report['python']})"
        )
    else:
        console.print(
            f"[bold yellow]status: {report['status']}[/bold yellow] "
            f"(phronesisml v{report['version']}, Python {report['python']})"
        )
        console.print(f"  Missing core dependencies: {', '.join(report['missing_core'])}")
    for label, check in report["dependencies"].items():
        if check["installed"]:
            console.print(f"  [green]{label}[/green]: {check['version']}")
        else:
            console.print(f"  [yellow]{label}[/yellow]: not installed")
    if report["missing_core"]:
        raise typer.Exit(code=1)


@app.command()
def analyze(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Load, clean, validate, and profile a dataset."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import analyze as api_analyze

        profile = api_analyze(data_path, engine=engine, null_strategy=null_strategy)
        rows, cols = profile.shape
        console.print(
            f"[bold]Profile[/bold] of [cyan]{data_path}[/cyan]: {rows} rows × {cols} columns"
        )
        console.print(f"  Memory: {profile.memory_usage_bytes / 1024 / 1024:.2f} MB")
        console.print(f"  Validation passed: {profile.validation_passed}")
        for col, count in profile.missing_counts.items():
            if count:
                console.print(f"  [yellow]{col}[/yellow]: {count} missing")
    except Exception as exc:
        _fail(exc)


@app.command()
def validate(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Load, clean, and validate a dataset."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import validate as api_validate

        result = api_validate(data_path, engine=engine, null_strategy=null_strategy)
        status = "passed" if result.passed else "failed"
        console.print(
            f"[bold]Validation[/bold] of [cyan]{data_path}[/cyan]: [green]{status}[/green]"
        )
        console.print(
            f"  {result.n_rows} rows × {result.n_columns} columns, "
            f"{result.duplicate_rows} duplicate rows"
        )
        for issue in result.issues:
            console.print(f"  [yellow]{issue}[/yellow]")
    except Exception as exc:
        _fail(exc)


@app.command()
def profile(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Profile a dataset (alias of ``analyze``)."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import profile as api_profile

        summary = api_profile(data_path, engine=engine, null_strategy=null_strategy)
        rows, cols = summary.shape
        console.print(
            f"[bold]Profile[/bold] of [cyan]{data_path}[/cyan]: {rows} rows × {cols} columns"
        )
        console.print(f"  Memory: {summary.memory_usage_bytes / 1024 / 1024:.2f} MB")
    except Exception as exc:
        _fail(exc)


@app.command()
def train(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    cv: int | None = typer.Option(None, "--cv", help="Cross-validation folds (>=2)."),
    model_type: str | None = typer.Option(None, "--model", "-m", help="Specific model to train."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run the full ML pipeline and report the trained model."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import train as api_train

        result = api_train(
            data_path,
            engine=engine,
            null_strategy=null_strategy,
            cv=cv,
            model_type=model_type,
        )
        console.print(
            f"[bold]Trained:[/bold] {result.best_model_type} (score={result.best_score:.4f})"
        )
        if result.task_type:
            console.print(f"  Task: {result.task_type}")
        if result.estimated_training_cost != "unknown":
            console.print(f"  Estimated training cost: {result.estimated_training_cost}")
        if result.artifact_uri:
            console.print(f"  Artifacts: {result.artifact_uri}")
    except Exception as exc:
        _fail(exc)


@app.command()
def explain(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Explain model predictions using SHAP."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import explain as api_explain

        result = api_explain(data_path, engine=engine, null_strategy=null_strategy)
        console.print(f"[bold]Feature importance[/bold] (explainer: {result.explainer_type})")
        for feature, importance in result.feature_importance.items():
            console.print(f"  {feature}: {importance:.4f}")
    except Exception as exc:
        _fail(exc)


@app.command()
def report(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    output: str | None = typer.Option(
        None, "--output", "-o", help="Write report to a Markdown file."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Generate a Markdown report of the full pipeline."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import report as api_report

        text = api_report(data_path, engine=engine, null_strategy=null_strategy)
        if output is not None:
            Path(output).write_text(text, encoding="utf-8")
            console.print(f"[bold]Report written:[/bold] {output}")
        else:
            console.print(text)
    except Exception as exc:
        _fail(exc)


@app.command()
def compare(
    data_path: str = typer.Argument(..., help="Path to the input dataset."),
    model: list[str] = typer.Option(  # noqa: B008 — repeatable option
        None, "--model", "-m", help="Model(s) to compare (repeatable)."
    ),
    engine: str | None = typer.Option(None, "--engine", "-e", help="Force an engine."),
    null_strategy: str = typer.Option(
        "drop", "--nulls", "-n", help="Null strategy: drop, fill, flag."
    ),
    cv: int | None = typer.Option(None, "--cv", help="Cross-validation folds (>=2)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Train several models on a dataset and rank them."""
    _setup_logging(verbose)
    _require_file(data_path)
    try:
        from phronesisml import compare as api_compare

        result = api_compare(
            data_path,
            list(model) or None,
            engine=engine,
            null_strategy=null_strategy,
            cv=cv,
        )
        better = "higher" if result.higher_is_better else "lower"
        console.print(
            f"[bold]Comparison[/bold] ({result.task_type}, "
            f"{result.primary_metric}: {better} is better)"
        )
        for rank, row in enumerate(result.ranking, start=1):
            console.print(f"  #{rank} {row['model']}: {row['value']:.4f}")
    except Exception as exc:
        _fail(exc)


if __name__ == "__main__":
    app()
