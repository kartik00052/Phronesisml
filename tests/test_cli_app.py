"""Unit tests for the Phronesis CLI interface."""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from phronesisml.interfaces.cli.app import _setup_logging, app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestSetupLogging:
    def test_verbose_sets_debug_level(self) -> None:
        with patch("phronesisml.interfaces.cli.app.logging.basicConfig") as mock_bc:
            _setup_logging(verbose=True)
            mock_bc.assert_called_once()
            assert mock_bc.call_args.kwargs["level"] == logging.DEBUG

    def test_not_verbose_sets_info_level(self) -> None:
        with patch("phronesisml.interfaces.cli.app.logging.basicConfig") as mock_bc:
            _setup_logging(verbose=False)
            mock_bc.assert_called_once()
            assert mock_bc.call_args.kwargs["level"] == logging.INFO


class TestInfoCommand:
    def test_info_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 0

    def test_info_prints_version(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["info"])
        assert "0.1.0" in result.output

    def test_info_prints_Phronesis(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["info"])
        assert "Phronesis" in result.output
