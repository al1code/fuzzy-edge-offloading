"""Core domain models for the fuzzy task-offloading study."""

from __future__ import annotations

from dataclasses import dataclass

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

    def centroid(self) -> float:
        """Return the standard centroid defuzzification value."""

        return (self.low + self.modal + self.high) / 3.0

    def paper_transformation_value(self) -> float:
        """Return (low + 4 * modal + high) / 6 from the paper's Eq. (12)."""

        return (self.low + 4.0 * self.modal + self.high) / 6.0


@dataclass(frozen=True, slots=True)
class Task:
    """Task with data in decimal MB and total required CPU cycles.

    ``required_cpu_cycles`` represents D_i * C_i in the paper, not its
    per-bit coefficient C_i. One MB equals 8,000,000 bits. A deadline is
    project metadata; it is not part of the paper's task tuple H_i.
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


@dataclass(frozen=True, slots=True)
class EdgeServer:
    """Resource inventory, not yet a full implementation of Eqs. (6)-(8).

    Uplink/downlink Mbps describe link rates, not the wireless bandwidth
    capacity Lambda in Hz. CPU cycles per second are not interchangeable
    with the MIPS capacity reported in the paper's Table 4.
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
