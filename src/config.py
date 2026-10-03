"""Project configuration objects.

The course project requires reproducible experiments and clearly documented
parameter choices. This module keeps those choices in one place instead of
spreading raw constants across the implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.validation import (
    validate_integer,
    validate_positive,
    validate_unit_interval,
    validate_weights,
)

DEFAULT_RANDOM_SEED = 42


@dataclass(frozen=True, slots=True)
class ProjectPaths:
    """Repository paths used by experiments and generated artifacts."""

    root: Path
    data_generated: Path
    data_author_provided: Path
    results_figures: Path
    results_tables: Path

    @classmethod
    def from_root(cls, root: str | Path) -> ProjectPaths:
        """Build the standard project path layout from the repository root."""

        root_path = Path(root).resolve()
        return cls(
            root=root_path,
            data_generated=root_path / "data" / "generated",
            data_author_provided=root_path / "data" / "author_provided",
            results_figures=root_path / "results" / "figures",
            results_tables=root_path / "results" / "tables",
        )


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    """Experiment configuration; task/server defaults are small smoke-test sizes."""

    random_seed: int = DEFAULT_RANDOM_SEED
    task_count: int = 30
    server_count: int = 5

    def __post_init__(self) -> None:
        validate_integer(self.random_seed, "random_seed")
        validate_integer(self.task_count, "task_count", minimum=1)
        validate_integer(self.server_count, "server_count", minimum=1)


@dataclass(frozen=True, slots=True)
class FuzzySecurityConfig:
    """Perspective weights eta_k; equal defaults follow the paper's Table 4."""

    task_data_weight: float = 1.0 / 3.0
    task_type_weight: float = 1.0 / 3.0
    terminal_lifecycle_weight: float = 1.0 / 3.0

    def __post_init__(self) -> None:
        weights = (
            self.task_data_weight,
            self.task_type_weight,
            self.terminal_lifecycle_weight,
        )
        validate_weights(weights, "security weights")


@dataclass(frozen=True, slots=True)
class LoadBalanceConfig:
    """CPU, bandwidth, and memory weights alpha_1..3 from Eq. (5)."""

    cpu_weight: float = 1.0 / 3.0
    bandwidth_weight: float = 1.0 / 3.0
    memory_weight: float = 1.0 / 3.0

    def __post_init__(self) -> None:
        validate_weights(
            (self.cpu_weight, self.bandwidth_weight, self.memory_weight),
            "load balance weights",
        )


@dataclass(frozen=True, slots=True)
class PositiveRange:
    """Finite positive bounds for a continuous uniform draw; equality is allowed."""

    low: float
    high: float

    def __post_init__(self) -> None:
        validate_positive(self.low, "range.low")
        validate_positive(self.high, "range.high")
        if self.low > self.high:
            raise ValueError("range.low must not exceed range.high")
        object.__setattr__(self, "low", float(self.low))
        object.__setattr__(self, "high", float(self.high))


@dataclass(frozen=True, slots=True)
class SyntheticScenarioConfig:
    """Recorded numeric-scenario choices, not the recovered author generator.

    Default counts select the lower Table 4 bounds. Small test counts remain
    valid. See references/synthetic_data.md for every default's provenance.
    Equal expert weights and all uniform ranges are project assumptions.
    """

    experiment: ExperimentConfig = ExperimentConfig(task_count=60, server_count=3)
    security: FuzzySecurityConfig = FuzzySecurityConfig()
    expert_weights: tuple[float, ...] = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
    security_threshold: float = 0.6
    data_size_mb: PositiveRange = PositiveRange(0.5, 5.0)
    cpu_cycles_per_bit: PositiveRange = PositiveRange(200.0, 800.0)
    task_bandwidth_hz: PositiveRange = PositiveRange(250_000.0, 1_000_000.0)
    task_memory_mb: PositiveRange = PositiveRange(8.0, 32.0)
    channel_gain: PositiveRange = PositiveRange(0.0001, 0.001)
    local_cpu_cycles_per_second: float = 3_000_000_000.0
    allocated_edge_cpu_cycles_per_second: float = 10_000_000_000.0
    server_cpu_capacity_cycles_per_second: float = 200_000_000_000.0
    server_memory_capacity_mb: float = 1024.0
    bandwidth_capacity_hz: float = 20_000_000.0
    transmission_power_watts: float = 0.1
    noise_density_watts_per_hz: float = 1e-17
    inventory_link_rate_mbps: float = 100.0
    deadline_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not isinstance(self.experiment, ExperimentConfig):
            raise TypeError("experiment must be an ExperimentConfig")
        if not isinstance(self.security, FuzzySecurityConfig):
            raise TypeError("security must be a FuzzySecurityConfig")
        object.__setattr__(self, "expert_weights", tuple(self.expert_weights))
        validate_weights(self.expert_weights, "expert weights")
        validate_unit_interval(self.security_threshold, "security_threshold")
        # NumPy float32 arithmetic must not change precision after JSON replay.
        # Validate before conversion so booleans/strings are never coerced.
        object.__setattr__(
            self, "expert_weights", tuple(float(w) for w in self.expert_weights)
        )
        object.__setattr__(self, "security_threshold", float(self.security_threshold))
        object.__setattr__(
            self,
            "experiment",
            ExperimentConfig(
                int(self.experiment.random_seed),
                int(self.experiment.task_count),
                int(self.experiment.server_count),
            ),
        )
        object.__setattr__(
            self,
            "security",
            FuzzySecurityConfig(
                float(self.security.task_data_weight),
                float(self.security.task_type_weight),
                float(self.security.terminal_lifecycle_weight),
            ),
        )
        for name in (
            "data_size_mb",
            "cpu_cycles_per_bit",
            "task_bandwidth_hz",
            "task_memory_mb",
            "channel_gain",
        ):
            if not isinstance(getattr(self, name), PositiveRange):
                raise TypeError(f"{name} must be a PositiveRange")
        for name in (
            "local_cpu_cycles_per_second",
            "allocated_edge_cpu_cycles_per_second",
            "server_cpu_capacity_cycles_per_second",
            "server_memory_capacity_mb",
            "bandwidth_capacity_hz",
            "transmission_power_watts",
            "noise_density_watts_per_hz",
            "inventory_link_rate_mbps",
            "deadline_seconds",
        ):
            validate_positive(getattr(self, name), name)
            object.__setattr__(self, name, float(getattr(self, name)))
