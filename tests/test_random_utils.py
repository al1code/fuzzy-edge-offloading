import random
from collections.abc import Iterator

import numpy as np
import pytest

from src.random_utils import create_random_state, seed_global_generators


@pytest.fixture(autouse=True)
def restore_global_random_states() -> Iterator[None]:
    python_state = random.getstate()
    numpy_state = np.random.get_state()
    try:
        yield
    finally:
        random.setstate(python_state)
        np.random.set_state(numpy_state)


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


@pytest.mark.parametrize("value", [1.5, True, float("nan"), "42"])
def test_random_helpers_reject_non_integer_seeds(value: object) -> None:
    with pytest.raises(TypeError, match="seed"):
        create_random_state(seed=value)
    with pytest.raises(TypeError, match="seed"):
        seed_global_generators(seed=value)


def test_invalid_global_seed_leaves_both_generators_unchanged() -> None:
    random.seed(123)
    np.random.seed(123)
    expected_python = random.Random(123).random()
    expected_numpy = np.random.RandomState(123).random_sample(4)

    with pytest.raises(ValueError, match="seed"):
        seed_global_generators(seed=2**32)

    assert random.random() == expected_python
    np.testing.assert_array_equal(np.random.random(4), expected_numpy)


def test_local_generators_do_not_change_global_states() -> None:
    random.seed(123)
    np.random.seed(123)
    expected_python = random.Random(123).random()
    expected_numpy = np.random.RandomState(123).random_sample(4)

    state = create_random_state(seed=987)
    state.python_random.random()
    state.numpy_random.random(10)

    assert random.random() == expected_python
    np.testing.assert_array_equal(np.random.random(4), expected_numpy)


def test_generator_sequences_are_reproducible_after_global_draws() -> None:
    first = create_random_state(seed=123)
    first_python = [first.python_random.random() for _ in range(5)]
    first_numpy = first.numpy_random.random(5)
    seed_global_generators(seed=987)
    random.random()
    np.random.random(10)
    second = create_random_state(seed=123)

    assert first_python == [second.python_random.random() for _ in range(5)]
    np.testing.assert_array_equal(first_numpy, second.numpy_random.random(5))


def test_modern_generators_accept_seeds_above_legacy_limit() -> None:
    first = create_random_state(seed=2**64)
    second = create_random_state(seed=2**64)

    assert first.python_random.random() == second.python_random.random()
    np.testing.assert_array_equal(
        first.numpy_random.random(4), second.numpy_random.random(4)
    )


@pytest.mark.parametrize("seed", [0, 2**32 - 1])
def test_global_generators_accept_boundary_seeds(seed: int) -> None:
    seed_global_generators(seed)
    expected_python = random.random()
    expected_numpy = np.random.random()
    seed_global_generators(seed)

    assert random.random() == expected_python
    assert np.random.random() == expected_numpy


def test_random_helpers_accept_numpy_integer_seeds() -> None:
    state = create_random_state(seed=np.int64(42))
    seed_global_generators(seed=np.int64(42))

    assert state.python_random.random() == random.random()


def test_numpy_stream_uses_recorded_pcg64_algorithm() -> None:
    state = create_random_state(42)
    expected = np.random.Generator(np.random.PCG64(42))

    assert isinstance(state.numpy_random.bit_generator, np.random.PCG64)
    np.testing.assert_array_equal(state.numpy_random.random(100), expected.random(100))


def test_separate_experiments_do_not_advance_each_others_streams() -> None:
    first = create_random_state(42)
    second = create_random_state(42)
    reference = create_random_state(42)
    first.python_random.random()
    first.numpy_random.random(100)

    assert [second.python_random.random() for _ in range(10)] == [
        reference.python_random.random() for _ in range(10)
    ]
    np.testing.assert_array_equal(
        second.numpy_random.random(10), reference.numpy_random.random(10)
    )
