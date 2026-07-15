"""Memory safety detection and enforcement for PhronesisML.

Provides system RAM detection and safe memory limit enforcement to
prevent OOM crashes. The ``MemorySafety`` class detects available
RAM and compares it against estimated resource requirements.

Design:
- Uses ``psutil`` for cross-platform RAM detection (with fallback).
- Never crashes on detection failure — returns safe defaults.
- Provides ``MemoryStatus`` enum for clear status reporting.
"""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MemoryStatus(StrEnum):
    """Status of memory safety check.

    Attributes:
        OK: Estimated memory is within safe limits.
        WARNING: Estimated memory is high but manageable.
        CRITICAL: Estimated memory exceeds critical threshold —
            sampling may not be sufficient.
        UNKNOWN: Could not determine memory status.
    """

    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MemorySafety:
    """System memory detection and safety enforcement.

    Args:
        max_memory_gb: Maximum safe memory in GB (default 4.0).
        critical_memory_gb: Critical threshold in GB (default 8.0).

    Example::

        safety = MemorySafety(max_memory_gb=4.0)
        status, available_gb = safety.check_available_memory()
        if status == MemoryStatus.CRITICAL:
            print("Not enough memory!")
    """

    def __init__(
        self,
        max_memory_gb: float = 4.0,
        critical_memory_gb: float = 8.0,
    ) -> None:
        self._max_memory_gb = max_memory_gb
        self._critical_memory_gb = critical_memory_gb
        self._available_gb: float | None = None

    def get_available_memory_gb(self) -> float:
        """Detect available system RAM in GB.

        Uses ``psutil`` if available, falls back to a conservative estimate.

        Returns:
            Available memory in GB, or a conservative default (4.0 GB)
            if detection fails.
        """
        if self._available_gb is not None:
            return self._available_gb

        try:
            import psutil

            mem = psutil.virtual_memory()
            self._available_gb = mem.available / (1024**3)
            logger.debug(
                "Detected available memory: %.1f GB (total: %.1f GB, used: %.1f%%)",
                self._available_gb,
                mem.total / (1024**3),
                mem.percent,
            )
            return self._available_gb
        except ImportError:
            logger.warning(
                "psutil not installed — using conservative memory estimate (4.0 GB). "
                "Install with: pip install psutil"
            )
            self._available_gb = 4.0
            return self._available_gb
        except Exception as exc:
            logger.warning(
                "Could not detect available memory: %s — using conservative estimate (4.0 GB)",
                exc,
            )
            self._available_gb = 4.0
            return self._available_gb

    def get_total_memory_gb(self) -> float:
        """Detect total system RAM in GB.

        Returns:
            Total memory in GB, or a conservative default (8.0 GB)
            if detection fails.
        """
        try:
            import psutil

            mem = psutil.virtual_memory()
            return mem.total / (1024**3)
        except Exception:
            return 8.0

    def check_available_memory(self) -> tuple[MemoryStatus, float]:
        """Check if there's enough memory for processing.

        Returns:
            A tuple of (status, available_gb).
        """
        available_gb = self.get_available_memory_gb()

        if available_gb >= self._critical_memory_gb:
            return MemoryStatus.OK, available_gb
        elif available_gb >= self._max_memory_gb:
            return MemoryStatus.WARNING, available_gb
        else:
            return MemoryStatus.CRITICAL, available_gb

    def estimate_memory_status(
        self,
        estimated_memory_gb: float,
    ) -> MemoryStatus:
        """Compare estimated memory against available memory.

        Args:
            estimated_memory_gb: Estimated memory requirement in GB.

        Returns:
            MemoryStatus indicating whether it's safe to proceed.
        """
        available_gb = self.get_available_memory_gb()

        if estimated_memory_gb > available_gb:
            return MemoryStatus.CRITICAL
        elif estimated_memory_gb > available_gb * 0.7:
            return MemoryStatus.WARNING
        else:
            return MemoryStatus.OK

    def get_safe_actions(self, estimated_memory_gb: float) -> list[str]:
        """Recommend actions when memory is insufficient.

        Args:
            estimated_memory_gb: Estimated memory requirement in GB.

        Returns:
            List of recommended action strings.
        """
        available_gb = self.get_available_memory_gb()

        if estimated_memory_gb <= available_gb:
            return []

        actions = []
        actions.append(
            f"Estimated memory ({estimated_memory_gb:.1f} GB) exceeds "
            f"available memory ({available_gb:.1f} GB)."
        )
        actions.append("Recommended actions:")
        actions.append("  - Enable PySpark engine for distributed processing")
        actions.append("  - Reduce sample_size in SamplingConfig")
        actions.append("  - Filter columns to reduce dataset width")
        actions.append("  - Increase available system memory")

        return actions

    def validate_estimates(
        self,
        estimates: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate a full set of resource estimates against memory limits.

        Args:
            estimates: Dict from ``ResourceEstimator.estimate()``.

        Returns:
            Dict with ``status``, ``safe``, ``warnings``, ``blockers``,
            ``recommended_actions``.
        """
        estimated_memory_gb = estimates.get("estimated_memory_gb", 0)
        status = self.estimate_memory_status(estimated_memory_gb)
        available_gb = self.get_available_memory_gb()

        warnings: list[str] = []
        blockers: list[str] = []
        safe = True

        if status == MemoryStatus.CRITICAL:
            safe = False
            blockers.append(
                f"Dataset requires ~{estimated_memory_gb:.1f} GB but only "
                f"{available_gb:.1f} GB is available. Processing cannot proceed safely."
            )
        elif status == MemoryStatus.WARNING:
            warnings.append(
                f"Dataset requires ~{estimated_memory_gb:.1f} GB "
                f"({estimated_memory_gb / available_gb:.0%} of available {available_gb:.1f} GB). "
                f"Monitor memory usage closely."
            )

        return {
            "status": status.value,
            "safe": safe,
            "warnings": warnings,
            "blockers": blockers,
            "available_memory_gb": round(available_gb, 2),
            "estimated_memory_gb": round(estimated_memory_gb, 2),
            "recommended_actions": self.get_safe_actions(estimated_memory_gb),
        }
