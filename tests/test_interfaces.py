"""Smoke tests for the CLI interface.

The CLI is a thin consumer of the SDK public API (AI_QUALITY_GATE.md §2.3):
it parses input, calls ``phronesisml.simple`` or ``Phronesis``, and displays
results.  These tests verify the surface is wired end-to-end without
re-testing SDK internals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from phronesisml.interfaces.cli.app import app as cli_app

CLI_RUNNER = CliRunner()


@pytest.fixture(scope="module")
def tiny_csv(tmp_path_factory) -> str:
    rng = np.random.default_rng(7)
    n = 60
    df = pd.DataFrame(
        {
            "feat_a": rng.normal(size=n),
            "feat_b": rng.integers(0, 10, n),
            "target": (rng.normal(size=n) > 0).astype(int),
        }
    )
    path = tmp_path_factory.mktemp("interfaces") / "data.csv"
    df.to_csv(path, index=False)
    return str(path)


# ── CLI ──────────────────────────────────────────────────────────


def test_cli_help_exposes_commands() -> None:
    result = CLI_RUNNER.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.output
    assert "info" in result.output


def test_cli_run_help_documents_options() -> None:
    result = CLI_RUNNER.invoke(cli_app, ["run", "--help"])
    assert result.exit_code == 0
    assert "data_path" in result.output
    assert "--engine" in result.output
    assert "--nulls" in result.output


def test_cli_info_reports_version() -> None:
    from phronesisml import __version__

    result = CLI_RUNNER.invoke(cli_app, ["info"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_run_completes_on_tiny_dataset(tiny_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["run", tiny_csv, "--engine", "pandas"])
    assert result.exit_code == 0
    assert "Pipeline completed successfully" in result.output


def test_cli_run_missing_file_exits_nonzero(tmp_path_factory) -> None:
    missing = tmp_path_factory.mktemp("cli_missing") / "nope.csv"
    result = CLI_RUNNER.invoke(cli_app, ["run", str(missing)])
    assert result.exit_code == 1
