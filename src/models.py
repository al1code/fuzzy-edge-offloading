"""Core domain models for the fuzzy task-offloading study."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TriangularFuzzyNumber:
    """Triangular fuzzy number represented as ``(low, modal, high)``."""

    low: float
    modal: float
    high: float

    def __post_init__(self) -> None:
        if not self.low <= self.modal <= self.high:
            msg = "triangular fuzzy number must satisfy low <= modal <= high"
            raise ValueError(msg)

    def centroid(self) -> float:
        """Return the standard centroid defuzzification value."""

        return (self.low + self.modal + self.high) / 3.0

    def paper_transformation_value(self) -> float:
        """Return the transformation value used by the reference paper."""

        return (self.low + 4.0 * self.modal + self.high) / 6.0


@dataclass(frozen=True, slots=True)
class Task:
    """Computational task considered by the offloading algorithms."""

    task_id: str
    data_size_mb: float
    required_cpu_cycles: float
    deadline_seconds: float

    def __post_init__(self) -> None:
        if not self.task_id:
            msg = "task_id must not be empty"
            raise ValueError(msg)
        if self.data_size_mb <= 0.0:
            msg = "data_size_mb must be greater than zero"
            raise ValueError(msg)
        if self.required_cpu_cycles <= 0.0:
            msg = "required_cpu_cycles must be greater than zero"
            raise ValueError(msg)
        if self.deadline_seconds <= 0.0:
            msg = "deadline_seconds must be greater than zero"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class EdgeServer:
    """Edge server resource description used by assignment decisions."""

    server_id: str
    cpu_capacity_cycles_per_second: float
    uplink_bandwidth_mbps: float
    downlink_bandwidth_mbps: float
    memory_capacity_mb: float

    def __post_init__(self) -> None:
        if not self.server_id:
            msg = "server_id must not be empty"
            raise ValueError(msg)
        if self.cpu_capacity_cycles_per_second <= 0.0:
            msg = "cpu_capacity_cycles_per_second must be greater than zero"
            raise ValueError(msg)
        if self.uplink_bandwidth_mbps <= 0.0:
            msg = "uplink_bandwidth_mbps must be greater than zero"
            raise ValueError(msg)
        if self.downlink_bandwidth_mbps <= 0.0:
            msg = "downlink_bandwidth_mbps must be greater than zero"
            raise ValueError(msg)
        if self.memory_capacity_mb <= 0.0:
            msg = "memory_capacity_mb must be greater than zero"
            raise ValueError(msg)
