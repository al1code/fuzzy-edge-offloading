"""Utilities for deterministic random number generation."""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from src.config import DEFAULT_RANDOM_SEED
from src.validation import validate_integer


@dataclass(frozen=True, slots=True)
class RandomState:
    """Container for reproducible Python and NumPy random generators."""

    seed: int
    python_random: random.Random
    numpy_random: np.random.Generator


def create_random_state(seed: int = DEFAULT_RANDOM_SEED) -> RandomState:
    """Create independent Python and NumPy streams with an explicit PCG64 generator."""

    validate_integer(seed, "seed")
    seed = int(seed)
    return RandomState(
        seed=seed,
        python_random=random.Random(seed),
        numpy_random=np.random.Generator(np.random.PCG64(seed)),
    )


def seed_global_generators(seed: int = DEFAULT_RANDOM_SEED) -> None:
    """Validate a shared seed in [0, 2**32 - 1], then seed both legacy globals."""

    validate_integer(seed, "seed", maximum=2**32 - 1)
    seed = int(seed)
    random.seed(seed)
    np.random.seed(seed)
