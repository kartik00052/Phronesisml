"""Data validation — schema, type, and quality checks.

``data.validators.checks`` contains the real validation logic,
called by the Validation agent.
"""

from phronesisml.data.validators.checks import validate_dataframe

__all__ = ["validate_dataframe"]
