"""Smoke tests for the CLI interface.

The CLI is a thin consumer of the SDK public API (AI_QUALITY_GATE.md §2.3):
it parses input, calls ``phronesisml.simple`` or ``Phronesis``, and displays
results.  These tests verify the surface is wired end-to-end without
re-testing SDK internals.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from phronesisml.interfaces.cli.app import _reconfigure_utf8
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
    for command in (
        "train",
        "analyze",
        "validate",
        "profile",
        "explain",
        "report",
        "compare",
        "version",
        "capabilities",
        "doctor",
    ):
        assert command in result.output


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


# ── Extended CLI surface (v0.3.0) ────────────────────────────────


def test_cli_version_reports_version() -> None:
    from phronesisml import __version__

    result = CLI_RUNNER.invoke(cli_app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_cli_capabilities_reports_surface() -> None:
    from phronesisml import __version__

    result = CLI_RUNNER.invoke(cli_app, ["capabilities"])
    assert result.exit_code == 0
    assert __version__ in result.output
    assert "upload" in result.output
    assert "doctor" in result.output


def test_cli_doctor_reports_ok() -> None:
    result = CLI_RUNNER.invoke(cli_app, ["doctor"])
    assert result.exit_code == 0
    assert "status: ok" in result.output


def test_cli_analyze_on_tiny_dataset(tiny_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["analyze", tiny_csv, "--engine", "pandas"])
    assert result.exit_code == 0
    assert "rows ×" in result.output


def test_cli_profile_on_tiny_dataset(tiny_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["profile", tiny_csv, "--engine", "pandas"])
    assert result.exit_code == 0
    assert "rows ×" in result.output


def test_cli_validate_on_tiny_dataset(tiny_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["validate", tiny_csv, "--engine", "pandas"])
    assert result.exit_code == 0
    assert "Validation" in result.output


def test_cli_report_writes_output_file(tiny_csv: str, tmp_path) -> None:
    output = tmp_path / "report.md"
    result = CLI_RUNNER.invoke(
        cli_app, ["report", tiny_csv, "--engine", "pandas", "--output", str(output)]
    )
    assert result.exit_code == 0
    assert output.is_file()
    assert output.read_text(encoding="utf-8").startswith("#")


def test_cli_command_missing_file_exits_nonzero(tmp_path_factory) -> None:
    missing = tmp_path_factory.mktemp("cli_missing2") / "nope.csv"
    result = CLI_RUNNER.invoke(cli_app, ["analyze", str(missing)])
    assert result.exit_code == 1


def test_cli_reconfigure_utf8_handles_non_ascii_glyphs() -> None:
    """Regression: a cp1252 Windows pipe must not break on CLI glyphs (e.g. ``→``).

    Rich's legacy Windows renderer raises UnicodeEncodeError when writing
    non-ASCII glyphs to a cp1252-coded pipe. The CLI forces UTF-8 on stdout
    and stderr at import; this exercises the same reconfigure against a
    simulated legacy stream.
    """
    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    _reconfigure_utf8(stream)
    stream.write("upload → etl → validation")
    stream.flush()
    assert stream.buffer.getvalue().decode("utf-8") == "upload → etl → validation"


def test_cli_reconfigure_utf8_ignores_unreconfigurable_stream() -> None:
    stream = io.StringIO()
    _reconfigure_utf8(stream)
    stream.write("upload → etl")
    assert stream.getvalue() == "upload → etl"
