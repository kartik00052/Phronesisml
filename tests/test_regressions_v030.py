"""Regression tests for defects confirmed during the v0.3.0 QA pass (NEW-09..NEW-13).

Each test pins the *fixed* behaviour.  All five defects are now fixed in
the release-verification pass, so every test runs unconditionally:

- NEW-09 (FIXED): ``predict()`` / restore→predict accepts raw rows with
  string categoricals (ETL encoding maps now reach the transform recipe).
- NEW-10 (FIXED): CLI ``compare`` without ``-m`` no longer crashes.
- NEW-11 (FIXED): ``resource_estimation.json`` carries real estimates,
  not the placeholder (sampling node wired in the SDK ``_run_stages``).
- NEW-12 (FIXED): CLI exposes an ``evaluate`` command.
- NEW-13 (FIXED): numeric target columns with 2–5 unique values are
  treated consistently by the target detector.
- NEW-15 (FIXED): ``compare()`` with an unknown model type propagates a
  ``WorkflowError`` instead of silently dropping the model from the
  ranking.
- NEW-16 (FIXED): HTML reports HTML-escape user-controlled data (column
  names, target values, caveats) so a malicious feature name cannot
  inject a raw ``<script>`` / ``<img onerror>`` payload into
  ``generate_report(format='html')`` or the saved ``report.html``.

NEW-14 (doc drift) is a documentation-only issue tracked in the audit.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from typer.testing import CliRunner

from phronesisml.interfaces.cli.app import app as cli_app

CLI_RUNNER = CliRunner()

# ── Shared fixtures ────────────────────────────────────────────────────


def _make_csv_with_string_category(path: Path, n: int = 200, seed: int = 42) -> str:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "num_feat": rng.normal(50, 15, n).round(2),
            "cat_feat": rng.choice(["alpha", "beta", "gamma"], n),
            "y": rng.integers(0, 10, n).astype(float),
        }
    )
    df.to_csv(path, index=False)
    return str(path)


@pytest.fixture()
def string_category_csv(tmp_path: Path) -> str:
    return _make_csv_with_string_category(tmp_path / "catdata.csv")


# ── NEW-09: predict crashes on string categoricals ─────────────────────


def test_new09_predict_accepts_raw_string_categorical(string_category_csv: str) -> None:
    from phronesisml import Phronesis

    ml = Phronesis(string_category_csv)
    ml.train()
    preds = ml.predict([{"num_feat": 51.2, "cat_feat": "beta"}])
    assert len(preds) == 1


def test_new09_recipe_encoding_maps_present(string_category_csv: str) -> None:
    from phronesisml import Phronesis

    ml = Phronesis(string_category_csv)
    ml.train()
    recipe = ml.state.feature_transform or {}
    assert "cat_feat" in recipe.get("categorical_columns", []), (
        "string categorical must be recorded as categorical in the recipe"
    )
    assert "cat_feat" in recipe.get("encoding_maps", {})


# ── NEW-10: CLI compare without -m ─────────────────────────────────────


def test_new10_cli_compare_default_no_crash(string_category_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["compare", string_category_csv])
    assert result.exit_code == 0, result.output


# ── NEW-11: resource_estimation.json placeholder ───────────────────────


def test_new11_resource_estimation_populated(string_category_csv: str, tmp_path: Path) -> None:
    from phronesisml import Phronesis

    ml = Phronesis(string_category_csv)
    info = ml.run(mode="balanced").save(tmp_path)
    est_file = Path(info["artifact_uri"]) / "resource_estimation.json"
    assert est_file.exists()
    payload = json.loads(est_file.read_text(encoding="utf-8"))
    assert payload.get("reason") != "pre-flight resource estimation did not run"


# ── NEW-12: CLI evaluate command ───────────────────────────────────────


def test_new12_cli_has_evaluate_command(string_category_csv: str) -> None:
    result = CLI_RUNNER.invoke(cli_app, ["evaluate", string_category_csv])
    assert result.exit_code == 0, result.output


# ── NEW-13: detector 2–5 unique boundary consistency ───────────────────


def test_new13_numeric_2_to_5_unique_consistent() -> None:
    from phronesisml.ml.target_detection.detector import _score_column

    n_rows = 200
    signals_by_count: dict[int, list[str]] = {}
    task_by_count: dict[int, str] = {}
    for n_unique in (2, 3, 4, 5):
        out = _score_column(
            col="num",
            is_numeric=True,
            n_unique=n_unique,
            n_rows=n_rows,
            collected=pd.Series([float(i) for i in range(n_unique)] * (n_rows // n_unique)),
            col_summary={},
        )
        signals_by_count[n_unique] = out["signals"]
        task_by_count[n_unique] = out["task_type"]

    assert task_by_count == {2: "ambiguous", 3: "ambiguous", 4: "ambiguous", 5: "ambiguous"}
    assert signals_by_count[2] == signals_by_count[3], (
        "2 unique and 3–5 unique must share one signal"
    )


# ── NEW-15: compare swallows invalid model names ────────────────────────
# NEW-15 (FIXED): ``compare()`` with an unknown model type no longer
# silently drops the request.  The ``WorkflowError`` from the
# model_selection agent propagates to the caller instead.


def test_new15_compare_invalid_model_raises(string_category_csv: str) -> None:
    from phronesisml import compare
    from phronesisml.exceptions import WorkflowError

    with pytest.raises(WorkflowError) as excinfo:
        compare(string_category_csv, ["definitely_not_a_model"])
    assert "not found" in str(excinfo.value)


def test_new15_compare_invalid_model_cli_nonzero(string_category_csv: str) -> None:
    result = CLI_RUNNER.invoke(
        cli_app, ["compare", string_category_csv, "-m", "definitely_not_a_model"]
    )
    assert result.exit_code != 0, result.output
    assert "not found" in result.output


# ── NEW-16: HTML report XSS via feature names ───────────────────────────


@pytest.fixture()
def xss_dataset(tmp_path: Path) -> str:
    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "<script>alert(9)</script>": rng.normal(50, 15, 150).round(2),
            "<img src=x onerror=alert(7)>": rng.choice(["a", "b", "c"], 150),
            "y": rng.integers(0, 2, 150),
        }
    )
    path = tmp_path / "xss_data.csv"
    df.to_csv(path, index=False)
    return str(path)


def test_new16_html_report_escapes_malicious_feature_names(
    xss_dataset: str, tmp_path: Path
) -> None:
    from phronesisml import Phronesis

    ml = Phronesis(xss_dataset)
    info = ml.run(mode="balanced").save(tmp_path)
    html = ml.generate_report(format="html")
    saved = Path(info["artifact_uri"]) / "report.html"

    assert "<script>alert(9)</script>" not in html
    assert "<img src=x onerror=alert(7)>" not in html
    assert "&lt;script&gt;alert(9)&lt;/script&gt;" in html
    assert "&lt;img src=x onerror=alert(7)&gt;" in html
    assert saved.exists(), "report.html artifact must still be written"
    assert "<script>alert(9)</script>" not in saved.read_text(encoding="utf-8")


def test_new16_markdown_report_keeps_markdown_shape(xss_dataset: str) -> None:
    from phronesisml import Phronesis

    ml = Phronesis(xss_dataset)
    ml.run(mode="balanced")
    md = ml.generate_report(format="markdown")
    assert "- **" in md, "markdown report keeps its markdown structure"
