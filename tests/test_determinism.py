"""Determinism contract tests.

Same dataset + same config + same seed must produce identical metrics,
best model, and report across repeated runs (AI_QUALITY_GATE.md §1.3).

The only permitted difference is the unique run identifier embedded in
the report; every other byte of the report must be identical.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from phronesisml import Phronesis, PhronesisConfig

_RUN_ID_RE = re.compile(r"run_[0-9a-f]{32}")


@pytest.fixture(scope="module")
def deterministic_csv(tmp_path_factory) -> str:
    rng = np.random.default_rng(42)
    n = 200
    df = pd.DataFrame(
        {
            "feat_a": rng.normal(size=n),
            "feat_b": rng.integers(0, 10, n),
            "feat_c": rng.normal(size=n),
            "target": (rng.normal(size=n) > 0).astype(int),
        }
    )
    path = tmp_path_factory.mktemp("determinism") / "data.csv"
    df.to_csv(path, index=False)
    return str(path)


def _run_full(path: str) -> tuple[dict, str, str, str]:
    config = PhronesisConfig()
    config.engine.preferred = "pandas"
    ml = Phronesis(path, config)
    ml.run()
    return (
        vars(ml.evaluate()),
        ml.report(),
        ml.generate_report(format="html"),
        type(ml.get_model()).__name__,
    )


def test_full_pipeline_deterministic(deterministic_csv: str) -> None:
    metrics1, report1, html1, model1 = _run_full(deterministic_csv)
    metrics2, report2, html2, model2 = _run_full(deterministic_csv)

    assert model1 == model2
    assert metrics1 == metrics2
    assert _RUN_ID_RE.sub("<run_id>", report1) == _RUN_ID_RE.sub("<run_id>", report2)
    assert _RUN_ID_RE.sub("<run_id>", html1) == _RUN_ID_RE.sub("<run_id>", html2)
