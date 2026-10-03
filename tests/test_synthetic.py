import random
from dataclasses import FrozenInstanceError, replace
from math import log2

import numpy as np
import pytest

from src.config import (
    ExperimentConfig,
    FuzzySecurityConfig,
    PositiveRange,
    SyntheticScenarioConfig,
)
from src.evaluation import evaluate_plan
from src.fuzzy_security import assess_security
from src.objective import NormalizationConstants
from src.scenario import OffloadingDecision
from src.synthetic import RuntimeVersions, generate_synthetic_dataset


def small_config(seed: int = 42) -> SyntheticScenarioConfig:
    return SyntheticScenarioConfig(experiment=ExperimentConfig(seed, 3, 2))


def test_same_config_and_seed_produce_identical_inputs_and_metadata() -> None:
    first = generate_synthetic_dataset(small_config())
    second = generate_synthetic_dataset(small_config())
    assert first == second
    assert first.scenario.tasks is not second.scenario.tasks
    assert first.runtime.bit_generator == "PCG64"
    with pytest.raises(FrozenInstanceError):
        first.scenario.security_threshold = 0.1


def test_different_seed_changes_generated_inputs_not_fixed_settings() -> None:
    first = generate_synthetic_dataset(small_config(42))
    second = generate_synthetic_dataset(small_config(43))
    assert first.scenario.tasks != second.scenario.tasks
    assert first.scenario.links != second.scenario.links
    assert first.scenario.servers == second.scenario.servers


def test_generation_does_not_touch_global_python_or_numpy_random_states() -> None:
    python_before = random.getstate()
    numpy_before = np.random.get_state()
    generate_synthetic_dataset(small_config())
    assert random.getstate() == python_before
    numpy_after = np.random.get_state()
    assert numpy_before[0] == numpy_after[0]
    np.testing.assert_array_equal(numpy_before[1], numpy_after[1])
    assert numpy_before[2:] == numpy_after[2:]


def test_task_work_and_security_come_from_recorded_raw_inputs() -> None:
    dataset = generate_synthetic_dataset(small_config())
    config = dataset.configuration
    for profile, cycles, assessments in zip(
        dataset.scenario.tasks,
        dataset.cpu_cycles_per_bit,
        dataset.expert_assessments,
        strict=True,
    ):
        assert (
            config.data_size_mb.low
            <= profile.task.data_size_mb
            <= config.data_size_mb.high
        )
        assert config.cpu_cycles_per_bit.low <= cycles <= config.cpu_cycles_per_bit.high
        assert (
            profile.task.required_cpu_cycles
            == profile.task.data_size_mb * 8_000_000 * cycles
        )
        security = assess_security(
            assessments,
            expert_weights=config.expert_weights,
            security_threshold=config.security_threshold,
            config=config.security,
        )
        assert profile.security_level == security.security_level
        for assessment in assessments:
            for triangle in (
                assessment.task_data,
                assessment.task_type,
                assessment.terminal_lifecycle,
            ):
                assert 0.0 <= triangle.low <= triangle.modal <= triangle.high < 1.0


def test_all_task_server_links_follow_shannon_formula_with_recorded_gain() -> None:
    dataset = generate_synthetic_dataset(small_config())
    config = dataset.configuration
    assert len(dataset.scenario.links) == 6
    assert [(link.task_id, link.server_id) for link in dataset.scenario.links] == [
        (t.task.task_id, s.server.server_id)
        for t in dataset.scenario.tasks
        for s in dataset.scenario.servers
    ]
    by_task = {task.task.task_id: task for task in dataset.scenario.tasks}
    for link, gain in zip(dataset.scenario.links, dataset.channel_gains, strict=True):
        bandwidth = by_task[link.task_id].bandwidth_hz
        expected = bandwidth * log2(
            1
            + config.transmission_power_watts
            * gain**2
            / (bandwidth * config.noise_density_watts_per_hz)
        )
        assert link.rate_bits_per_second == pytest.approx(expected, rel=1e-12)


def test_changed_security_threshold_does_not_redraw_inputs_or_change_link_rates() -> (
    None
):
    first = generate_synthetic_dataset(small_config())
    second = generate_synthetic_dataset(replace(small_config(), security_threshold=0.0))
    assert first.scenario.tasks == second.scenario.tasks
    assert first.scenario.links == second.scenario.links
    assert first.expert_assessments == second.expert_assessments
    assert second.normalization.security_risk == 1.0


def test_custom_expert_weights_and_single_expert_are_supported() -> None:
    config = replace(
        small_config(),
        expert_weights=(1.0,),
        security=FuzzySecurityConfig(0.5, 0.3, 0.2),
    )
    dataset = generate_synthetic_dataset(config)
    assert all(len(a) == 1 for a in dataset.expert_assessments)
    expected = assess_security(
        dataset.expert_assessments[0],
        expert_weights=(1.0,),
        security_threshold=config.security_threshold,
        config=config.security,
    )
    assert dataset.scenario.tasks[0].security_level == expected.security_level


def test_fixed_ranges_generate_the_requested_constant_values() -> None:
    config = replace(
        small_config(),
        data_size_mb=PositiveRange(1.0, 1.0),
        cpu_cycles_per_bit=PositiveRange(500.0, 500.0),
        task_bandwidth_hz=PositiveRange(1e6, 1e6),
        task_memory_mb=PositiveRange(16.0, 16.0),
        channel_gain=PositiveRange(0.001, 0.001),
    )
    dataset = generate_synthetic_dataset(config)
    assert all(t.task.required_cpu_cycles == 4e9 for t in dataset.scenario.tasks)
    assert dataset.channel_gains == (0.001,) * 6


@pytest.mark.parametrize("seed", [0, 2**64, np.int64(42)])
def test_supported_seed_boundaries_remain_reproducible(seed: int) -> None:
    assert generate_synthetic_dataset(small_config(seed)) == generate_synthetic_dataset(
        small_config(seed)
    )


def test_default_paper_range_counts_have_valid_local_and_round_robin_plans() -> None:
    dataset = generate_synthetic_dataset()
    assert len(dataset.scenario.tasks) == 60
    assert len(dataset.scenario.servers) == 3
    local = tuple(
        OffloadingDecision(t.task.task_id, 0.0) for t in dataset.scenario.tasks
    )
    edge = tuple(
        OffloadingDecision(
            t.task.task_id, 1.0, dataset.scenario.servers[index % 3].server.server_id
        )
        for index, t in enumerate(dataset.scenario.tasks)
    )
    local_result = evaluate_plan(
        dataset.scenario, local, normalization=dataset.normalization
    )
    edge_result = evaluate_plan(
        dataset.scenario, edge, normalization=dataset.normalization
    )
    assert local_result.total_security_risk == 0.0
    assert all(s.load.cpu_utilization == 1.0 for s in edge_result.servers)
    assert edge_result.objective.normalized_risk == pytest.approx(1.0)


def test_large_workload_is_not_repaired_to_hide_infeasible_full_offloading() -> None:
    dataset = generate_synthetic_dataset(
        SyntheticScenarioConfig(experiment=ExperimentConfig(42, 140, 3))
    )
    decisions = tuple(
        OffloadingDecision(
            t.task.task_id, 1.0, dataset.scenario.servers[index % 3].server.server_id
        )
        for index, t in enumerate(dataset.scenario.tasks)
    )
    with pytest.raises(ValueError, match="CPU allocation exceeds capacity"):
        evaluate_plan(dataset.scenario, decisions, normalization=dataset.normalization)
    assert len(dataset.scenario.tasks) == 140
    assert dataset.configuration.server_cpu_capacity_cycles_per_second == 200e9


def test_invalid_config_type_and_derived_overflow_are_rejected() -> None:
    with pytest.raises(TypeError, match="SyntheticScenarioConfig"):
        generate_synthetic_dataset(object())
    config = replace(small_config(), data_size_mb=PositiveRange(1e308, 1e308))
    with pytest.raises(ValueError, match="required_cpu_cycles"):
        generate_synthetic_dataset(config)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("configuration", object(), "SyntheticScenarioConfig"),
        ("scenario", object(), "OffloadingScenario"),
        ("normalization", object(), "NormalizationConstants"),
        ("runtime", object(), "RuntimeVersions"),
        ("cpu_cycles_per_bit", (), "raw task inputs"),
        ("channel_gains", (), "channel gains"),
        ("expert_assessments", (), "raw task inputs"),
    ],
)
def test_dataset_rejects_mismatched_input_types_and_dimensions(
    field: str, value: object, message: str
) -> None:
    with pytest.raises((ValueError, TypeError), match=message):
        replace(generate_synthetic_dataset(small_config()), **{field: value})


def test_dataset_rejects_raw_input_or_scenario_inconsistency() -> None:
    dataset = generate_synthetic_dataset(small_config())
    with pytest.raises(ValueError, match="counts"):
        replace(
            dataset,
            configuration=replace(
                dataset.configuration, experiment=ExperimentConfig(42, 4, 2)
            ),
        )
    with pytest.raises(ValueError, match="one assessment"):
        replace(
            dataset,
            expert_assessments=(
                (dataset.expert_assessments[0][0],),
                *dataset.expert_assessments[1:],
            ),
        )
    with pytest.raises(TypeError, match="SecurityPerspectives"):
        replace(
            dataset,
            expert_assessments=((object(),) * 3, *dataset.expert_assessments[1:]),
        )
    with pytest.raises(ValueError, match="channel_gain"):
        replace(dataset, channel_gains=(-1.0, *dataset.channel_gains[1:]))
    with pytest.raises(ValueError, match="D_i"):
        replace(
            dataset,
            cpu_cycles_per_bit=(
                dataset.cpu_cycles_per_bit[0] + 1,
                *dataset.cpu_cycles_per_bit[1:],
            ),
        )
    scenario = replace(dataset.scenario, security_threshold=0.2)
    with pytest.raises(ValueError, match="scenario settings"):
        replace(dataset, scenario=scenario)


def test_runtime_strings_must_be_present() -> None:
    with pytest.raises(ValueError, match="runtime versions"):
        RuntimeVersions("", "2.5.3", "PCG64")


@pytest.mark.parametrize(
    "change, message",
    [
        ("task_range", "outside its recorded range"),
        ("terminal", "terminal settings"),
        ("server", "server settings"),
        ("gain", "gain lies outside"),
        ("link", "link rate"),
        ("normalization", "normalization"),
        ("cycles_nan", "cpu_cycles_per_bit"),
    ],
)
def test_recorded_values_cannot_drift_from_configuration_or_equations(
    change: str, message: str
) -> None:
    dataset = generate_synthetic_dataset(small_config())
    values = {}
    if change in ("task_range", "terminal"):
        first = dataset.scenario.tasks[0]
        first = (
            replace(first, task=replace(first.task, data_size_mb=6.0))
            if change == "task_range"
            else replace(first, local_cpu_cycles_per_second=2e9)
        )
        values["scenario"] = replace(
            dataset.scenario, tasks=(first, *dataset.scenario.tasks[1:])
        )
    elif change == "server":
        first = dataset.scenario.servers[0]
        first = replace(first, server=replace(first.server, memory_capacity_mb=2048.0))
        values["scenario"] = replace(
            dataset.scenario, servers=(first, *dataset.scenario.servers[1:])
        )
    elif change == "gain":
        values["channel_gains"] = (0.1, *dataset.channel_gains[1:])
    elif change == "link":
        first = dataset.scenario.links[0]
        values["scenario"] = replace(
            dataset.scenario,
            links=(
                replace(first, rate_bits_per_second=first.rate_bits_per_second * 2),
                *dataset.scenario.links[1:],
            ),
        )
    elif change == "normalization":
        values["normalization"] = NormalizationConstants(1.0, 1.0)
    else:
        values["cpu_cycles_per_bit"] = (float("nan"), *dataset.cpu_cycles_per_bit[1:])
    with pytest.raises(ValueError, match=message):
        replace(dataset, **values)
