import random

import numpy as np
import pytest

from src.random_utils import create_random_state, seed_global_generators


def test_create_random_state_is_reproducible() -> None:
    first = create_random_state(seed=123)
    second = create_random_state(seed=123)

    assert first.python_random.random() == second.python_random.random()
    assert first.numpy_random.random() == second.numpy_random.random()


def test_create_random_state_uses_independent_generators() -> None:
    state = create_random_state(seed=123)

    first_draw = state.python_random.random()
    _ = random.random()
    second_state = create_random_state(seed=123)

    assert first_draw == second_state.python_random.random()


def test_seed_global_generators_controls_legacy_random_state() -> None:
    seed_global_generators(seed=999)
    python_draw = random.random()
    numpy_draw = np.random.random()

    seed_global_generators(seed=999)

    assert random.random() == python_draw
    assert np.random.random() == numpy_draw


def test_random_helpers_reject_negative_seed() -> None:
    with pytest.raises(ValueError):
        create_random_state(seed=-1)

    with pytest.raises(ValueError):
        seed_global_generators(seed=-1)
