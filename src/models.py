"""Task, server, and triangular fuzzy-number models."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from src.validation import validate_finite, validate_positive


@dataclass(frozen=True, slots=True)
class TriangularFuzzyNumber:
    """Triangular fuzzy number represented as ``(low, modal, high)``."""

    low: float
    modal: float
    high: float

    def __post_init__(self) -> None:
        validate_finite(self.low, "low")
        validate_finite(self.modal, "modal")
        validate_finite(self.high, "high")
        if not self.low <= self.modal <= self.high:
            msg = "triangular fuzzy number must satisfy low <= modal <= high"
            raise ValueError(msg)
        # Validate before conversion; do not accept booleans or numeric strings.
        for name in ("low", "modal", "high"):
            object.__setattr__(self, name, float(getattr(self, name)))

    def centroid(self) -> float:
        """Return the standard centroid defuzzification value."""

        result = (self.low + self.modal + self.high) / 3.0
        if isfinite(result):
            return result
        # The mean is bounded by the inputs even when the unscaled sum overflows.
        scale = max(abs(self.low), abs(self.modal), abs(self.high))
        return scale * (
            (self.low / scale + self.modal / scale + self.high / scale) / 3.0
        )

    def paper_transformation_value(self) -> float:
        """Return (low + 4 * modal + high) / 6 from the paper's Eq. (12)."""

        result = (self.low + 4.0 * self.modal + self.high) / 6.0
        if isfinite(result):
            return result
        scale = max(abs(self.low), abs(self.modal), abs(self.high))
        return scale * (
            (self.low / scale + 4.0 * (self.modal / scale) + self.high / scale) / 6.0
        )


@dataclass(frozen=True, slots=True)
class Task:
    """Task data in decimal MB (8,000,000 bits) and total CPU cycles D_i * C_i.

    The deadline is metadata, outside the paper's task tuple H_i.
    """

    task_id: str
    data_size_mb: float
    required_cpu_cycles: float
    deadline_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            msg = "task_id must not be empty"
            raise ValueError(msg)
        validate_positive(self.data_size_mb, "data_size_mb")
        validate_positive(self.required_cpu_cycles, "required_cpu_cycles")
        validate_positive(self.deadline_seconds, "deadline_seconds")
        for name in ("data_size_mb", "required_cpu_cycles", "deadline_seconds"):
            object.__setattr__(self, name, float(getattr(self, name)))


@dataclass(frozen=True, slots=True)
class EdgeServer:
    """Server inventory with CPU in cycles/s, link rates in Mbps, memory in MB.

    Link rates differ from wireless bandwidth in Hz; cycles/s differ from MIPS.
    """

    server_id: str
    cpu_capacity_cycles_per_second: float
    uplink_bandwidth_mbps: float
    downlink_bandwidth_mbps: float
    memory_capacity_mb: float

    def __post_init__(self) -> None:
        if not isinstance(self.server_id, str) or not self.server_id.strip():
            msg = "server_id must not be empty"
            raise ValueError(msg)
        validate_positive(
            self.cpu_capacity_cycles_per_second, "cpu_capacity_cycles_per_second"
        )
        validate_positive(self.uplink_bandwidth_mbps, "uplink_bandwidth_mbps")
        validate_positive(self.downlink_bandwidth_mbps, "downlink_bandwidth_mbps")
        validate_positive(self.memory_capacity_mb, "memory_capacity_mb")
        for name in (
            "cpu_capacity_cycles_per_second",
            "uplink_bandwidth_mbps",
            "downlink_bandwidth_mbps",
            "memory_capacity_mb",
        ):
            object.__setattr__(self, name, float(getattr(self, name)))
