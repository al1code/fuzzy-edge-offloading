from dataclasses import asdict, replace

import numpy as np
import pytest

from src.config import GeneticSearchConfig


def test_defaults_record_operator_bounds_and_a_finite_evaluation_budget() -> None:
    config = GeneticSearchConfig()
    assert config.crossover_high == 0.9
    assert config.crossover_low == 0.6
    assert config.mutation_high == 0.1
    assert config.mutation_low == 0.001
    assert config.evaluation_budget == 755
    assert replace(config, generations=0).evaluation_budget == 30
    assert (
        replace(
            config, population_size=5, elite_count=2, generations=4
        ).evaluation_budget
        == 17
    )


@pytest.mark.parametrize(
    "field, value, error",
    [
        ("population_size", 1, ValueError),
        ("population_size", True, TypeError),
        ("population_size", 3.0, TypeError),
        ("generations", -1, ValueError),
        ("generations", False, TypeError),
        ("elite_count", 0, ValueError),
        ("elite_count", 30, ValueError),
        ("elite_count", 31, ValueError),
        ("elite_count", "1", TypeError),
        ("crossover_high", 0.6, ValueError),
        ("crossover_low", 0.95, ValueError),
        ("mutation_high", 0.001, ValueError),
        ("mutation_low", 0.2, ValueError),
        ("crossover_high", float("nan"), ValueError),
        ("mutation_low", float("inf"), ValueError),
        ("mutation_high", 1.1, ValueError),
        ("crossover_low", -0.1, ValueError),
        ("mutation_high", True, TypeError),
    ],
)
def test_invalid_configuration_is_rejected(
    field: str, value: object, error: type[Exception]
) -> None:
    with pytest.raises(error, match=field.split("_")[0]):
        replace(GeneticSearchConfig(), **{field: value})


def test_numpy_numbers_are_validated_then_snapshotted_as_json_safe_types() -> None:
    config = GeneticSearchConfig(
        population_size=np.int64(6),
        generations=np.int64(3),
        elite_count=np.int64(2),
        crossover_high=np.float32(0.9),
    )
    assert config.evaluation_budget == 18
    assert all(type(value) in (int, float) for value in asdict(config).values())
