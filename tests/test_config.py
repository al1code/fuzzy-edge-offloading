import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest

from src.config import (
    ExperimentConfig,
    FuzzySecurityConfig,
    LoadBalanceConfig,
    ProjectPaths,
)


def test_project_paths_follow_repository_layout(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    assert paths.root == tmp_path.resolve()
    assert paths.data_generated == tmp_path.resolve() / "data" / "generated"
    assert paths.data_author_provided == tmp_path.resolve() / "data" / "author_provided"
    assert paths.results_figures == tmp_path.resolve() / "results" / "figures"
    assert paths.results_tables == tmp_path.resolve() / "results" / "tables"


def test_experiment_config_accepts_default_values() -> None:
    config = ExperimentConfig()

    assert config.random_seed == 42
    assert config.task_count == 30
    assert config.server_count == 5


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("random_seed", -1),
        ("task_count", 0),
        ("server_count", 0),
    ],
)
def test_experiment_config_rejects_invalid_values(
    field_name: str,
    invalid_value: int,
) -> None:
    kwargs = {field_name: invalid_value}

    with pytest.raises(ValueError):
        ExperimentConfig(**kwargs)


def test_fuzzy_security_config_requires_weights_to_sum_to_one() -> None:
    config = FuzzySecurityConfig(
        task_data_weight=0.5,
        task_type_weight=0.3,
        terminal_lifecycle_weight=0.2,
    )

    assert config.task_data_weight == 0.5
    assert config.task_type_weight == 0.3
    assert config.terminal_lifecycle_weight == 0.2


def test_fuzzy_security_config_rejects_invalid_weights() -> None:
    with pytest.raises(ValueError):
        FuzzySecurityConfig(
            task_data_weight=0.5,
            task_type_weight=0.5,
            terminal_lifecycle_weight=0.5,
        )


@pytest.mark.parametrize("field_name", ["random_seed", "task_count", "server_count"])
@pytest.mark.parametrize("value", [1.5, True, float("nan"), float("inf"), "3"])
def test_experiment_config_requires_integer_parameters(
    field_name: str, value: object
) -> None:
    with pytest.raises(TypeError, match=field_name):
        ExperimentConfig(**{field_name: value})


@pytest.mark.parametrize("value", [-0.1, float("nan"), float("inf")])
def test_fuzzy_security_config_rejects_invalid_weight_values(value: float) -> None:
    with pytest.raises(ValueError, match="security weights"):
        FuzzySecurityConfig(
            task_data_weight=value,
            task_type_weight=0.0,
            terminal_lifecycle_weight=1.0,
        )


def test_fuzzy_security_config_rejects_boolean_weights() -> None:
    with pytest.raises(TypeError, match="security weights"):
        FuzzySecurityConfig(True, 0.0, 0.0)


def test_fuzzy_security_config_accepts_zero_perspective_weights() -> None:
    config = FuzzySecurityConfig(
        task_data_weight=1.0,
        task_type_weight=0.0,
        terminal_lifecycle_weight=0.0,
    )

    assert config.task_data_weight == 1.0


def test_load_balance_config_defaults_to_equal_resource_weights() -> None:
    config = LoadBalanceConfig()

    assert (config.cpu_weight, config.bandwidth_weight, config.memory_weight) == (
        1 / 3,
        1 / 3,
        1 / 3,
    )


@pytest.mark.parametrize(
    "weights", [(0.5, 0.5, 0.5), (-0.1, 0.5, 0.6), (float("nan"), 0.0, 1.0)]
)
def test_load_balance_config_rejects_invalid_weights(
    weights: tuple[float, ...],
) -> None:
    with pytest.raises(ValueError, match="load balance weights"):
        LoadBalanceConfig(*weights)


def test_numpy_configuration_scalars_can_be_recorded_as_standard_json() -> None:
    experiment = ExperimentConfig(np.int64(42), np.int32(3), np.int64(2))
    security = FuzzySecurityConfig(np.float32(0.5), np.float32(0.25), np.float32(0.25))
    load = LoadBalanceConfig(np.float32(0.5), np.float32(0.25), np.float32(0.25))

    for config, scalar_type in ((experiment, int), (security, float), (load, float)):
        values = asdict(config)
        assert all(type(value) is scalar_type for value in values.values())
        assert json.loads(json.dumps(values, allow_nan=False)) == values
