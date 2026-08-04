"""Download and curate the bundled demo datasets into ``data/``.

Supervised demo: Iris classification (``scikit-learn/iris``).
Unsupervised demo: credit-card customer clustering / anomaly detection
(``scikit-learn/credit-card-clients``).

Both are fetched straight from the Hugging Face Hub and then curated
so they work out of the box with the Phronesis SDK:

- ``iris.csv``: the ``Species`` target is renamed to ``class`` so the
  SDK's target detector can pick it up unambiguously.
- ``credit_card_clients.csv``: the ``ID`` and
  ``default.payment.next.month`` columns are dropped (leaving a pure
  clustering feature set) and numeric cells are normalized so both the
  pandas and polars engines parse the file.

Run from the repo root::

    uv run python scripts/download_demo_data.py
"""

from __future__ import annotations

import shutil
import time
import urllib.error
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _download(url: str, dest: Path, attempts: int = 5) -> None:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "phronesisml-demo/0.3"})
            with (
                urllib.request.urlopen(request, timeout=120) as response,
                dest.open("wb") as handle,
            ):
                shutil.copyfileobj(response, handle)
            return
        except (urllib.error.URLError, OSError) as exc:
            last_error = exc
            print(f"    retry {attempt}/{attempts} after {exc}")
            time.sleep(2**attempt)
    raise RuntimeError(f"failed to download {url}: {last_error}") from last_error


def _curate_iris(dest: Path) -> None:
    import pandas as pd

    df = pd.read_csv(dest)
    df = df.rename(columns={"Species": "class"})
    df.to_csv(dest, index=False)


def _curate_credit_card(dest: Path) -> None:
    import pandas as pd

    df = pd.read_csv(dest)
    df = df.drop(columns=["ID", "default.payment.next.month"])
    df.to_csv(dest, index=False)


SOURCES = {
    "iris.csv": (
        "https://huggingface.co/datasets/scikit-learn/iris/resolve/main/Iris.csv",
        "Iris classification demo (150 rows, supervised).",
        _curate_iris,
    ),
    "credit_card_clients.csv": (
        "https://huggingface.co/datasets/scikit-learn/credit-card-clients/resolve/main/UCI_Credit_Card.csv",
        "Credit-card customer profiles (30,000 rows, unsupervised clustering demo).",
        _curate_credit_card,
    ),
}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, (url, description, curator) in SOURCES.items():
        dest = DATA_DIR / filename
        if dest.exists():
            print(f"[skip] {filename} already present")
            continue
        print(f"[get ] {filename} <- {url}")
        _download(url, dest)
        curator(dest)
        print(f"[done] {filename} ({description})")


if __name__ == "__main__":
    main()
