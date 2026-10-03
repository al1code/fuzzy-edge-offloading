from dataclasses import replace

import pytest

from src.config import ExperimentConfig, PositiveRange, SyntheticScenarioConfig


def test_defaults_distinguish_paper_parameters_from_project_assumptions() -> None:
    config = SyntheticScenarioConfig()
    assert config.experiment == ExperimentConfig(42, 60, 3)
    assert config.local_cpu_cycles_per_second == 3e9
    assert config.allocated_edge_cpu_cycles_per_second == 10e9
    assert config.server_memory_capacity_mb == 1024.0
    assert config.bandwidth_capacity_hz == 20e6
    assert config.transmission_power_watts == 0.1
    assert config.server_cpu_capacity_cycles_per_second == 200e9
    assert config.noise_density_watts_per_hz == 1e-17


@pytest.mark.parametrize(
    "args",
    [(0.0, 1.0), (-1.0, 1.0), (2.0, 1.0), (float("nan"), 1.0), (1.0, float("inf"))],
)
def test_ranges_reject_invalid_bounds(args: tuple[float, float]) -> None:
    with pytest.raises(ValueError):
        PositiveRange(*args)


def test_ranges_accept_fixed_values_but_not_boolean_bounds() -> None:
    assert PositiveRange(1.0, 1.0).low == 1.0
    with pytest.raises(TypeError):
        PositiveRange(True, 1.0)


@pytest.mark.parametrize(
    "field",
    [
        "local_cpu_cycles_per_second",
        "allocated_edge_cpu_cycles_per_second",
        "server_cpu_capacity_cycles_per_second",
        "server_memory_capacity_mb",
        "bandwidth_capacity_hz",
        "transmission_power_watts",
        "noise_density_watts_per_hz",
        "inventory_link_rate_mbps",
        "deadline_seconds",
    ],
)
@pytest.mark.parametrize("value", [0.0, -1.0, float("inf"), float("nan"), True])
def test_scalar_parameters_require_finite_positive_numbers(
    field: str, value: object
) -> None:
    error = TypeError if isinstance(value, bool) else ValueError
    with pytest.raises(error, match=field):
        replace(SyntheticScenarioConfig(), **{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "data_size_mb",
        "cpu_cycles_per_bit",
        "task_bandwidth_hz",
        "task_memory_mb",
        "channel_gain",
    ],
)
def test_range_parameters_require_typed_ranges(field: str) -> None:
    with pytest.raises(TypeError, match=field):
        replace(SyntheticScenarioConfig(), **{field: (1.0, 2.0)})


@pytest.mark.parametrize("field", ["experiment", "security"])
def test_nested_configurations_are_not_coerced(field: str) -> None:
    with pytest.raises(TypeError, match=field):
        replace(SyntheticScenarioConfig(), **{field: object()})


@pytest.mark.parametrize("value", [-0.1, 1.1, float("inf"), float("nan"), True])
def test_security_threshold_requires_unit_interval(value: object) -> None:
    error = TypeError if isinstance(value, bool) else ValueError
    with pytest.raises(error, match="security_threshold"):
        replace(SyntheticScenarioConfig(), security_threshold=value)


@pytest.mark.parametrize(
    "weights", [(), (0.2, 0.2), (-0.1, 1.1), (float("nan"),), (True,)]
)
def test_expert_weights_are_explicit_valid_normalized_inputs(
    weights: tuple[object, ...],
) -> None:
    error = TypeError if weights == (True,) else ValueError
    with pytest.raises(error, match="expert weights"):
        replace(SyntheticScenarioConfig(), expert_weights=weights)


def test_mutable_weights_are_snapshotted_and_small_counts_are_allowed() -> None:
    weights = [0.25, 0.75]
    config = SyntheticScenarioConfig(
        experiment=ExperimentConfig(0, 1, 1), expert_weights=weights
    )
    weights.clear()
    assert config.expert_weights == (0.25, 0.75)
    assert config.experiment.task_count == 1
