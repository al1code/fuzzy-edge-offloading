"""Server resource utilization and population load variance, Eqs. (5)-(10)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum

from src.config import LoadBalanceConfig
from src.validation import (
    validate_non_negative,
    validate_positive,
    validate_unit_interval,
)


@dataclass(frozen=True, slots=True)
class ResourceVector:
    """CPU cycles/s, wireless bandwidth Hz, and memory MB for a resource budget.

    The same quantities describe a capacity or one selected task's reservation.
    Allocations may be zero; capacity denominators must be strictly positive.
    This is distinct from the link rates in EdgeServer's legacy Mbps fields.
    """

    cpu_cycles_per_second: float
    bandwidth_hz: float
    memory_mb: float

    def __post_init__(self) -> None:
        validate_non_negative(self.cpu_cycles_per_second, "cpu_cycles_per_second")
        validate_non_negative(self.bandwidth_hz, "bandwidth_hz")
        validate_non_negative(self.memory_mb, "memory_mb")


@dataclass(frozen=True, slots=True)
class ServerLoad:
    """Resource utilization fractions and the weighted server load Gamma_j."""

    cpu_utilization: float
    bandwidth_utilization: float
    memory_utilization: float
    weighted_load: float


def _resource_utilization(allocated: float, capacity: float, name: str) -> float:
    utilization = allocated / capacity
    if utilization > 1.0:
        raise ValueError(f"{name} allocation exceeds capacity")
    return utilization


def calculate_server_load(
    capacity: ResourceVector,
    allocations: Sequence[ResourceVector],
    *,
    config: LoadBalanceConfig | None = None,
) -> ServerLoad:
    """Calculate Eqs. (5)-(8) for reservations assigned to one server.

    Include a reservation exactly when y_ij=1. As in the paper, reserved
    resources are not scaled by x_i. Pass the shared bandwidth capacity
    Lambda as capacity.bandwidth_hz for each server in a paper scenario.
    Over-capacity assignments are rejected, not clipped or silently penalized.
    This function does not impose a new global bandwidth constraint.
    """

    if not isinstance(capacity, ResourceVector):
        raise TypeError("capacity must be a ResourceVector")
    validate_positive(capacity.cpu_cycles_per_second, "capacity.cpu_cycles_per_second")
    validate_positive(capacity.bandwidth_hz, "capacity.bandwidth_hz")
    validate_positive(capacity.memory_mb, "capacity.memory_mb")
    allocations = tuple(allocations)
    if any(not isinstance(a, ResourceVector) for a in allocations):
        raise TypeError("allocations must contain ResourceVector objects")
    if config is None:
        config = LoadBalanceConfig()
    elif not isinstance(config, LoadBalanceConfig):
        raise TypeError("config must be a LoadBalanceConfig")

    total_cpu = fsum(a.cpu_cycles_per_second for a in allocations)
    total_bandwidth = fsum(a.bandwidth_hz for a in allocations)
    total_memory = fsum(a.memory_mb for a in allocations)
    utilizations = (
        _resource_utilization(total_cpu, capacity.cpu_cycles_per_second, "CPU"),
        _resource_utilization(total_bandwidth, capacity.bandwidth_hz, "bandwidth"),
        _resource_utilization(total_memory, capacity.memory_mb, "memory"),
    )
    weights = (config.cpu_weight, config.bandwidth_weight, config.memory_weight)
    weighted_load = fsum(w * u for w, u in zip(weights, utilizations, strict=True))
    weighted_load /= fsum(weights)
    return ServerLoad(*utilizations, weighted_load)


def calculate_load_variance(server_loads: Sequence[float]) -> float:
    """Return the population variance of weighted server loads from Eq. (10).

    Include every server, including idle servers whose load is zero. An
    empty system is invalid; a one-server system has variance zero.
    """

    server_loads = tuple(server_loads)
    if not server_loads:
        raise ValueError("at least one server load is required")
    for load in server_loads:
        validate_unit_interval(load, "server load")
    mean_load = fsum(server_loads) / len(server_loads)
    return fsum((load - mean_load) ** 2 for load in server_loads) / len(server_loads)
