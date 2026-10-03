"""Project configuration objects.

The course project requires reproducible experiments and clearly documented
parameter choices. This module keeps those choices in one place instead of
spreading raw constants across the implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.validation import validate_integer, validate_weights

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
