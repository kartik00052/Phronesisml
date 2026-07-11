"""Engine selection agent — select computation engine within the workflow.

This agent runs early in the pipeline and selects the appropriate
computation engine based on data characteristics.  Writes to
``state.active_engine``.

Design:
- Stateless: all inputs come from ``WorkflowState``.
- Delegates to ``engines.engine_selector.select_engine()`` for the
  actual selection logic.
- If the user has already forced an engine via config, this agent
  simply records the choice.
- If no data is available yet, defaults to pandas (safe fallback).
"""

from __future__ import annotations

import logging
from typing import Any

from aetherml.agents.base import AgentResult, Tool

logger = logging.getLogger(__name__)


class EngineSelectionAgent:
    """Agent responsible for selecting the computation engine.

    Args:
        config: Optional ``AetherMLConfig`` for engine preferences.

    """

    name = "engine_selection"
    description = "Select the best computation engine based on data characteristics."

    def __init__(self, config: Any | None = None) -> None:
        self._config = config

    async def run(self, state: Any) -> AgentResult:
        """Select an engine and record the choice in state.

        Reads from: ``state.raw_data``, ``state.data_path``.

        Writes to: ``state.active_engine``.

        """
        from aetherml.engines.engine_selector import select_engine

        logger.info("Engine selection agent: selecting engine.")

        try:
            data_path = getattr(state, "data_path", None)
            raw_data = getattr(state, "raw_data", None)

            engine = select_engine(
                config=self._config,
                data_path=data_path,
                df=raw_data,
            )

            engine_name = engine.engine_type.value
            logger.info("Engine selection agent: selected '%s'.", engine_name)

            return AgentResult(
                success=True,
                data={"active_engine": engine_name},
                metadata={
                    "engine_type": engine_name,
                    "data_path": data_path,
                },
            )

        except Exception as exc:
            msg = f"Engine selection failed: {exc}"
            logger.exception(msg)
            return AgentResult(
                success=False,
                error=msg,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )

    def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="select_engine",
                description="Select the optimal computation engine for the current dataset.",
                parameters={
                    "preferred": {
                        "type": "string",
                        "description": "Override engine selection (pandas/polars/spark).",
                    },
                },
            ),
        ]
