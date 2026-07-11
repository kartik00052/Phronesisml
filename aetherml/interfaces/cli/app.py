"""AetherML CLI — Typer-based command-line interface.

This is a **thin consumer** of the SDK public API.  It contains no
business logic — it parses arguments, calls ``aetherml.run_pipeline()``,
and displays results.

Entry point: ``aetherml`` (defined in ``pyproject.toml`` ``[project.scripts]``).
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(
    name="aetherml",
    help="AetherML — Automated Machine Learning lifecycle SDK.",
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
    """Run the AetherML pipeline on a dataset."""
    _setup_logging(verbose)

    if not Path(data_path).exists():
        console.print(f"[red]Error:[/red] File not found: {data_path}")
        raise typer.Exit(code=1)

    console.print(f"[bold blue]AetherML[/bold blue] — processing [cyan]{data_path}[/cyan]")

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
    from aetherml import run_pipeline

    return await run_pipeline(
        data_path=data_path,
        engine_preference=engine,
        null_strategy=null_strategy,
    )


@app.command()
def info() -> None:
    """Show AetherML version and installed components."""
    from aetherml import __version__

    console.print(f"[bold]AetherML[/bold] v{__version__}")
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


if __name__ == "__main__":
    app()
