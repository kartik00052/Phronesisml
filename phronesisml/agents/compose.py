"""Agent composition — single source of truth for agent instantiation.

This module provides ``compose_agents()``, the canonical composition
root where concrete agent and engine classes are instantiated.  The
rest of the SDK depends on abstractions (``BaseAgent``, ``BaseEngine``).

Design rationale:
- Single location: eliminates duplication between ``__init__.py`` and
  ``sdk.py`` which previously had identical agent creation logic.
- Lazy imports: agent and engine imports are deferred to function body
  so that ``import phronesisml`` does not pull in every dependency
  eagerly.
- Flexible signatures: accepts either an already-selected engine or
  a data_path + config to select one automatically.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def compose_agents(
    *,
    engine: Any | None = None,
    config: Any | None = None,
    data_path: str | None = None,
) -> dict[str, Any]:
    """Compose all agents via constructor injection.

    This is the composition root — the only place where concrete agent
    and engine classes are instantiated.

    Args:
        engine: Pre-selected computation engine.  If ``None``, one is
            selected automatically based on *config* and *data_path*.
        config: SDK configuration.  Uses defaults if ``None``.
        data_path: Path to the dataset.  Used for engine selection
            when *engine* is ``None``.

    Returns:
        Mapping of agent name → agent instance (11 agents).

    """
    from phronesisml.configs.settings import PhronesisConfig

    if config is None:
        config = PhronesisConfig()

    # Select engine if not provided
    if engine is None:
        from phronesisml.engines.engine_selector import select_engine

        engine = select_engine(config=config, data_path=data_path)

    # Import agents lazily
    from phronesisml.agents.eda.agent import EDAAgent
    from phronesisml.agents.etl.agent import ETLAgent, ETLConfig
    from phronesisml.agents.evaluation.agent import EvaluationAgent
    from phronesisml.agents.explainability.agent import ExplainabilityAgent
    from phronesisml.agents.feature_engineering.agent import FeatureEngineeringAgent
    from phronesisml.agents.model_selection.agent import ModelSelectionAgent
    from phronesisml.agents.reporting.agent import ReportingAgent
    from phronesisml.agents.storage.agent import StorageAgent
    from phronesisml.agents.target_detection.agent import TargetDetectionAgent
    from phronesisml.agents.upload.agent import UploadAgent
    from phronesisml.agents.validation.agent import ValidationAgent

    agents: dict[str, Any] = {
        "upload": UploadAgent(engine=engine),
        "validation": ValidationAgent(engine=engine),
        "etl": ETLAgent(config=ETLConfig(null_strategy=config.null_strategy)),
        "eda": EDAAgent(engine=engine),
        "target_detection": TargetDetectionAgent(engine=engine),
        "feature_engineering": FeatureEngineeringAgent(
            engine=engine,
            feature_selection_config=config.feature_selection,
        ),
        "model_selection": ModelSelectionAgent(engine=engine),
        "evaluation": EvaluationAgent(engine=engine),
        "explainability": ExplainabilityAgent(engine=engine),
        "reporting": ReportingAgent(),
        "storage": StorageAgent(),
    }

    logger.debug("Composed %d agents", len(agents))
    return agents
