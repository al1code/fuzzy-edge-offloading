"""Utilities for deterministic random number generation."""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from src.config import DEFAULT_RANDOM_SEED


@dataclass(frozen=True, slots=True)
class RandomState:
    """Container for reproducible Python and NumPy random generators."""

    seed: int
    python_random: random.Random
    numpy_random: np.random.Generator


def create_random_state(seed: int = DEFAULT_RANDOM_SEED) -> RandomState:
    """Create independent deterministic random generators for one experiment."""

    if seed < 0:
        msg = "seed must be non-negative"
        raise ValueError(msg)
    return RandomState(
        seed=seed,
        python_random=random.Random(seed),
        numpy_random=np.random.default_rng(seed),
    )


def seed_global_generators(seed: int = DEFAULT_RANDOM_SEED) -> None:
    """Seed global generators for libraries that still rely on global state."""

    if seed < 0:
        msg = "seed must be non-negative"
        raise ValueError(msg)
    random.seed(seed)
    np.random.seed(seed)
