"""Data resolution service — reconstruct features + target from workflow state.

Extracted from ``agents/base.py`` to separate data resolution logic
from agent contracts.  Used by ModelSelectionAgent and EvaluationAgent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResolvedData:
    """Result of resolving features + target from workflow state.

    Used by ModelSelectionAgent and EvaluationAgent to avoid
    duplicating the features/target reconstruction logic.
    """

    collected: Any  # pd.DataFrame with features + target joined
    feature_names: list[str]
    target_column: str


def resolve_features_target(
    state: Any,
    engine: Any,
) -> ResolvedData:
    """Resolve features + target from workflow state.

    Encapsulates the shared logic used by ModelSelectionAgent and
    EvaluationAgent to reconstruct a full DataFrame (features + target)
    from the workflow state.

    Args:
        state: The current ``WorkflowState``.
        engine: The active ``BaseEngine`` for data operations.

    Returns:
        A ``ResolvedData`` with the collected DataFrame, feature names,
        and target column name.

    Raises:
        ValueError: If required state fields are missing.
    """
    target_column = getattr(state, "target_column", None)
    if target_column is None:
        msg = "No target_column in workflow state."
        raise ValueError(msg)

    feature_names = getattr(state, "feature_names", None)

    upstream = state.validated_data if state.validated_data is not None else state.processed_data
    if upstream is None:
        msg = "No validated_data or processed_data in workflow state."
        raise ValueError(msg)

    if state.features is not None:
        features_df = engine.cached_collect(state.features)
        upstream_df = engine.cached_collect(upstream)
        if target_column in upstream_df.columns:
            collected = features_df.copy()
            collected[target_column] = upstream_df[target_column].values
        else:
            collected = features_df
    else:
        collected = engine.cached_collect(upstream)

    if feature_names is None:
        feature_names = [c for c in collected.columns if c != target_column]

    return ResolvedData(
        collected=collected,
        feature_names=feature_names,
        target_column=target_column,
    )
