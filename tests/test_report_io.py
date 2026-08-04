"""Tests for report I/O and extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from phronesisml.ml.reports import (
    render_metrics_table,
    report_to_dict,
    write_report,
)


@dataclass
class _StubState:
    run_id: str = "run-1"
    timestamp: str = "2026-01-01T00:00:00"
    target_column: str = "price"
    task_type: str = "regression"
    best_pipeline: str = "RandomForest"
    evaluation_report: dict = field(default_factory=lambda: {"r2": 0.9})


def test_write_report_markdown(tmp_path) -> None:
    info = write_report("# Hi\n", tmp_path / "report.md")
    assert info["fmt"] == "md"
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == "# Hi\n"
    assert info["bytes"] > 0


def test_write_report_infers_html(tmp_path) -> None:
    info = write_report("plain text", tmp_path / "out.html")
    assert info["fmt"] == "html"
    text = (tmp_path / "out.html").read_text(encoding="utf-8")
    assert "<html>" in text
    assert "plain text" in text


def test_write_report_txt_never_wraps(tmp_path) -> None:
    info = write_report("hello", tmp_path / "out.txt")
    assert info["fmt"] == "txt"
    assert (tmp_path / "out.txt").read_text(encoding="utf-8") == "hello"


def test_report_to_dict() -> None:
    result = report_to_dict(_StubState())
    assert result["run_id"] == "run-1"
    assert result["target_column"] == "price"
    assert result["task_type"] == "regression"
    assert result["model"] == "RandomForest"
    assert result["metrics"] == {"r2": 0.9}


def test_report_to_dict_missing_fields() -> None:
    result = report_to_dict(object())
    assert result["run_id"] is None
    assert result["metrics"] is None


def test_render_metrics_table() -> None:
    table = render_metrics_table({"r2": 0.9, "mae": 1.5, "name": "model"})
    assert "| Metric | Value |" in table
    assert "| r2 | 0.9 |" in table
    assert "| mae | 1.5 |" in table
    assert "model" in table


def test_render_metrics_table_skips_nested() -> None:
    table = render_metrics_table({"a": 1.0, "b": {"nested": 2}})
    assert "nested" not in table
    assert "| a | 1 |" in table


def test_render_metrics_table_include_keys() -> None:
    table = render_metrics_table({"a": 1.0, "b": 2.0}, include_keys=["b"])
    assert "| a" not in table
    assert "| b | 2 |" in table


def test_render_metrics_table_empty() -> None:
    table = render_metrics_table({})
    assert "_no data_" in table
