"""Feature engineering — transforming validated data into model-ready features.

``ml.feature_engineering.engineer`` contains the real engineering logic,
called by the Feature Engineering agent.
"""

from phronesisml.ml.feature_engineering.engineer import engineer_features

__all__ = ["engineer_features"]
