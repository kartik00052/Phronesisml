"""PhronesisML performance baseline benchmark.

Measures: startup, graph compilation, cached graph reuse, workflow execution,
engine routing, cached DataFrame collection, and memory usage.

Run: python benchmarks/bench_baseline.py
"""

from __future__ import annotations

import gc
import os
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

# ── Helpers ──────────────────────────────────────────────────────


def _mem_mb() -> float:
    """RSS in MB (Windows-compatible via psutil fallback)."""
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def _make_csv(n_rows: int = 5000) -> str:
    """Create a small CSV for benchmarking."""
    import numpy as np

    rng = np.random.default_rng(42)
    df = pd.DataFrame(
        {
            "id": range(n_rows),
            "feature_a": rng.normal(0, 1, n_rows),
            "feature_b": rng.normal(5, 2, n_rows),
            "category": rng.choice(["X", "Y", "Z"], n_rows),
            "target": rng.integers(0, 2, n_rows),
        }
    )
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as tmp:
        df.to_csv(tmp.name, index=False)
        return tmp.name


def _bench(
    label: str,
    func: Callable,
    *args: object,
    runs: int = 3,
    warmup: int = 1,
    **kwargs: object,
) -> tuple[float, object]:
    """Run func multiple times, return median time."""
    times = []
    for _ in range(warmup):
        func(*args, **kwargs)
    for _ in range(runs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        times.append(time.perf_counter() - t0)
    median = sorted(times)[len(times) // 2]
    return median, result


# ── Benchmarks ───────────────────────────────────────────────────


def bench_startup() -> dict:
    """Cold import time."""
    results = {}
    # Time the full package import
    times = []
    for _ in range(3):
        # Force reimport
        mods = [k for k in sys.modules if k.startswith("phronesisml")]
        for m in mods:
            del sys.modules[m]
        gc.collect()
        t0 = time.perf_counter()
        times.append(time.perf_counter() - t0)
    results["import_phronesisml_sec"] = sorted(times)[1]  # median of 3

    # Time Phronesis class instantiation
    csv_path = _make_csv(100)
    from phronesisml import Phronesis

    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        Phronesis(csv_path)
        times.append(time.perf_counter() - t0)
    results["init_phronesis_sec"] = sorted(times)[len(times) // 2]
    os.unlink(csv_path)
    return results


def bench_graph_compilation() -> dict:
    """Graph build + compile time, and cached reuse."""

    from phronesisml.sdk import Phronesis
    from phronesisml.workflow.graph import build_graph, clear_graph_cache

    csv_path = _make_csv(500)
    ml = Phronesis(csv_path)
    # Force agent creation
    _ = ml._get_agents()
    agents = ml._agents

    results = {}

    # Cold compile (no cache)
    clear_graph_cache()
    gc.collect()
    times = []
    for _ in range(3):
        clear_graph_cache()
        t0 = time.perf_counter()
        build_graph(agents)
        times.append(time.perf_counter() - t0)
    results["graph_compile_cold_sec"] = sorted(times)[1]

    # Warm compile (cached)
    build_graph(agents)  # prime cache
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        build_graph(agents)
        times.append(time.perf_counter() - t0)
    results["graph_compile_cached_sec"] = sorted(times)[len(times) // 2]

    speedup = results["graph_compile_cold_sec"] / max(results["graph_compile_cached_sec"], 1e-9)
    results["cache_speedup"] = round(speedup, 2)

    os.unlink(csv_path)
    return results


def bench_workflow_execution() -> dict:
    """Full pipeline execution time."""
    from phronesisml import Phronesis

    csv_path = _make_csv(2000)
    results = {}

    # Full pipeline
    times = []
    mem_before = _mem_mb()
    for _ in range(2):
        gc.collect()
        t0 = time.perf_counter()
        ml = Phronesis(csv_path)
        ml.run()
        times.append(time.perf_counter() - t0)
    results["full_pipeline_sec"] = sorted(times)[0]  # best of 2
    mem_after = _mem_mb()
    results["pipeline_memory_mb"] = (
        round(mem_after - mem_before, 2) if mem_before > 0 else "N/A (psutil not installed)"
    )

    os.unlink(csv_path)
    return results


def bench_engine_routing() -> dict:
    """Engine selection time for different file sizes."""

    from phronesisml.configs.settings import PhronesisConfig
    from phronesisml.engines.engine_selector import select_engine

    results = {}

    # Small file → should select pandas
    small_csv = _make_csv(100)
    config = PhronesisConfig()
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        engine = select_engine(config, data_path=small_csv)
        times.append(time.perf_counter() - t0)
    results["engine_select_small_sec"] = sorted(times)[len(times) // 2]
    results["engine_selected_small"] = type(engine).__name__
    os.unlink(small_csv)

    # Medium file → should select polars
    med_csv = _make_csv(50000)
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        engine = select_engine(config, data_path=med_csv)
        times.append(time.perf_counter() - t0)
    results["engine_select_medium_sec"] = sorted(times)[len(times) // 2]
    results["engine_selected_medium"] = type(engine).__name__
    os.unlink(med_csv)

    return results


def bench_cached_collect() -> dict:
    """DataFrame cached_collect overhead."""
    import numpy as np

    from phronesisml.engines.pandas_engine import PandasEngine

    engine = PandasEngine()
    df = pd.DataFrame(
        {
            "a": np.random.normal(0, 1, 10000),
            "b": np.random.normal(5, 2, 10000),
            "c": np.random.choice(["X", "Y"], 10000),
        }
    )

    results = {}

    # First collect (cache miss)
    times = []
    for _ in range(3):
        engine.clear_collect_cache()
        t0 = time.perf_counter()
        engine.cached_collect(df)
        times.append(time.perf_counter() - t0)
    results["collect_cold_sec"] = sorted(times)[1]

    # Second collect (cache hit)
    engine.cached_collect(df)  # prime
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        engine.cached_collect(df)
        times.append(time.perf_counter() - t0)
    results["collect_cached_sec"] = sorted(times)[len(times) // 2]

    speedup = results["collect_cold_sec"] / max(results["collect_cached_sec"], 1e-9)
    results["cache_speedup"] = round(speedup, 2)

    return results


# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  PhronesisML Performance Baseline Benchmark")
    print("=" * 60)

    all_results = {}

    print("\n[1/6] Startup...")
    all_results["startup"] = bench_startup()
    print(f"  import: {all_results['startup']['import_phronesisml_sec'] * 1000:.0f}ms")
    print(f"  init:   {all_results['startup']['init_phronesis_sec'] * 1000:.0f}ms")

    print("\n[2/6] Graph compilation...")
    all_results["graph"] = bench_graph_compilation()
    print(f"  cold:    {all_results['graph']['graph_compile_cold_sec'] * 1000:.0f}ms")
    print(f"  cached:  {all_results['graph']['graph_compile_cached_sec'] * 1000:.0f}ms")
    print(f"  speedup: {all_results['graph']['cache_speedup']}x")

    print("\n[3/6] Workflow execution (full pipeline, 2000 rows)...")
    all_results["workflow"] = bench_workflow_execution()
    print(f"  time:    {all_results['workflow']['full_pipeline_sec']:.2f}s")
    print(f"  memory:  {all_results['workflow']['pipeline_memory_mb']}")

    print("\n[4/6] Engine routing...")
    all_results["engine"] = bench_engine_routing()
    eng = all_results["engine"]
    small_ms = eng["engine_select_small_sec"] * 1000
    med_ms = eng["engine_select_medium_sec"] * 1000
    print(f"  small (100 rows):  {small_ms:.0f}ms -> {eng['engine_selected_small']}")
    print(f"  medium (50k rows): {med_ms:.0f}ms -> {eng['engine_selected_medium']}")

    print("\n[5/6] Cached DataFrame collection...")
    all_results["collect"] = bench_cached_collect()
    print(f"  cold:    {all_results['collect']['collect_cold_sec'] * 1000:.1f}ms")
    print(f"  cached:  {all_results['collect']['collect_cached_sec'] * 1000:.3f}ms")
    print(f"  speedup: {all_results['collect']['cache_speedup']}x")

    print("\n[6/6] Memory snapshot...")
    all_results["memory_rss_mb"] = _mem_mb()
    print(f"  RSS: {all_results['memory_rss_mb']:.1f} MB")

    # Save baseline
    import json

    baseline_path = Path("benchmarks/baseline.json")
    baseline_path.write_text(json.dumps(all_results, indent=2, default=str))
    print(f"\nBaseline saved to {baseline_path}")
    print("=" * 60)
