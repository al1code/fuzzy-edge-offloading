"""Project configuration objects.

The course project requires reproducible experiments and clearly documented
parameter choices. This module keeps those choices in one place instead of
spreading raw constants across the implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

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
    """Top-level configuration shared by reproducible experiments."""

    random_seed: int = DEFAULT_RANDOM_SEED
    task_count: int = 30
    server_count: int = 5

    def __post_init__(self) -> None:
        if self.random_seed < 0:
            msg = "random_seed must be non-negative"
            raise ValueError(msg)
        if self.task_count <= 0:
            msg = "task_count must be greater than zero"
            raise ValueError(msg)
        if self.server_count <= 0:
            msg = "server_count must be greater than zero"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FuzzySecurityConfig:
    """Weights for the paper's fuzzy security perspectives."""

    task_data_weight: float = 1.0 / 3.0
    task_type_weight: float = 1.0 / 3.0
    terminal_lifecycle_weight: float = 1.0 / 3.0

    def __post_init__(self) -> None:
        weights = (
            self.task_data_weight,
            self.task_type_weight,
            self.terminal_lifecycle_weight,
        )
        if any(weight < 0.0 for weight in weights):
            msg = "security weights must be non-negative"
            raise ValueError(msg)
        if not abs(sum(weights) - 1.0) <= 1e-9:
            msg = "security weights must sum to 1.0"
            raise ValueError(msg)
