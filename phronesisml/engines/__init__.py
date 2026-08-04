"""PhronesisML computation engines.

``engines.engine_selector.select_engine`` builds the right engine;
``engines.recommend`` provides pure recommendation heuristics that work
without instantiating engines.
"""

from phronesisml.engines.base_engine import BaseEngine, EngineType
from phronesisml.engines.engine_selector import select_engine
from phronesisml.engines.recommend import (
    engine_capabilities,
    engine_comparison_report,
    recommend_engine,
)

__all__ = [
    "BaseEngine",
    "EngineType",
    "engine_capabilities",
    "engine_comparison_report",
    "recommend_engine",
    "select_engine",
]
