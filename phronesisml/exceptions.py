"""Phronesis exception hierarchy.

All custom exceptions inherit from PhronesisError so callers can catch
the entire SDK surface with a single clause while still being able to
target specific failure modes.
"""

__all__ = [
    "PhronesisError",
    "AgentError",
    "AgentNotImplementedError",
    "ConfigurationError",
    "DataError",
    "DataLoadError",
    "DataTransformError",
    "DataValidationError",
    "EngineError",
    "EngineSelectionError",
    "WorkflowError",
]


class PhronesisError(Exception):
    """Base exception for all Phronesis errors."""


class ConfigurationError(PhronesisError):
    """Raised when required configuration is missing or invalid."""


class DataError(PhronesisError):
    """Raised for data loading, validation, or transformation failures."""


class DataLoadError(DataError):
    """Raised when data cannot be loaded from the specified source."""


class DataTransformError(DataError):
    """Raised when a data transformation fails."""


class DataValidationError(DataError):
    """Raised when data fails schema or quality validation checks."""


class EngineError(PhronesisError):
    """Raised when a computation engine operation fails."""


class EngineSelectionError(EngineError):
    """Raised when no suitable engine can be selected for the given data."""


class WorkflowError(PhronesisError):
    """Raised when the LangGraph workflow encounters a failure."""


class AgentError(PhronesisError):
    """Raised when an agent execution fails.

    Attributes:
        error_type: Exception class name from the agent (e.g. ``"DataLoadError"``).
        error_message: Original exception message from the agent.
        error_context: Optional structured context dict for debugging.

    """

    def __init__(
        self,
        message: str,
        *,
        error_type: str | None = None,
        error_message: str | None = None,
        error_context: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_type = error_type
        self.error_message = error_message
        self.error_context = error_context


class AgentNotImplementedError(AgentError):
    """Raised by agent stubs that have not been implemented yet."""
