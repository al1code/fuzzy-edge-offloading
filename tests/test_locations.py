from dataclasses import replace
from itertools import product

import numpy as np
import pytest

from src.config import LoadBalanceConfig
from src.evaluation import derive_normalization, evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.optimizers.locations import evaluate_locations_exact, validate_locations
from src.scenario import OffloadingDecision
from tests.scenario_helpers import make_scenario


@pytest.mark.parametrize(
    "weights",
    [ObjectiveConfig(), ObjectiveConfig(1.0, 0.0, 0.0), ObjectiveConfig(0.0, 0.0, 1.0)],
)
def test_fixed_location_reference_matches_exhaustive_ratios_and_global_oracle(
    weights: ObjectiveConfig,
) -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    values = []
    for locations in product(range(3), repeat=2):
        result = evaluate_locations_exact(
            scenario, locations, normalization=normalization, objective_config=weights
        )
        options = tuple(
            (OffloadingDecision(task.task.task_id, 0.0),)
            if gene == 0
            else tuple(
                OffloadingDecision(
                    task.task.task_id,
                    ratio,
                    scenario.servers[gene - 1].server.server_id,
                )
                for ratio in (0.0, 0.25, 0.5, 0.75, 1.0)
            )
            for task, gene in zip(scenario.tasks, locations, strict=True)
        )
        expected = min(
            evaluate_plan(
                scenario, plan, normalization=normalization, objective_config=weights
            ).objective.value
            for plan in product(*options)
        )
        assert result.objective.value == pytest.approx(expected)
        values.append(result.objective.value)
    exact = solve_exact(scenario, normalization=normalization, objective_config=weights)
    assert min(values) == pytest.approx(exact.best.objective.value)


def test_selected_zero_ratio_is_retained_when_it_improves_load_balance() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        security_threshold=0.0,
        links=tuple(
            replace(link, rate_bits_per_second=4e6) if link.task_id == "t2" else link
            for link in scenario.links
        ),
    )
    result = evaluate_locations_exact(
        scenario,
        (1, 2),
        normalization=derive_normalization(scenario),
        objective_config=ObjectiveConfig(0.8, 0.0, 0.2),
    )
    assert [task.decision for task in result.tasks] == [
        OffloadingDecision("t1", 1.0, "s1"),
        OffloadingDecision("t2", 0.0, "s2"),
    ]
    assert result.objective.value == pytest.approx(0.4)


def test_equal_endpoint_values_choose_zero_without_removing_selected_servers() -> None:
    scenario = replace(make_scenario(), security_threshold=0.0)
    result = evaluate_locations_exact(
        scenario,
        (1, 2),
        normalization=derive_normalization(scenario),
        objective_config=ObjectiveConfig(0.0, 1.0, 0.0),
    )
    assert all(task.decision.offloading_ratio == 0.0 for task in result.tasks)
    assert [task.decision.server_id for task in result.tasks] == ["s1", "s2"]
    assert all(server.load.weighted_load > 0.0 for server in result.servers)


def test_capacity_violation_is_not_repaired_or_hidden_by_zero_ratios() -> None:
    scenario = replace(make_scenario(), bandwidth_capacity_hz=9e6)
    with pytest.raises(CapacityExceededError, match="bandwidth allocation"):
        evaluate_locations_exact(
            scenario, (1, 1), normalization=derive_normalization(scenario)
        )


def test_location_lists_are_not_mutated_and_numpy_integers_become_plain_ints() -> None:
    locations = [np.int64(0), np.int64(2)]
    assert validate_locations(make_scenario(), locations) == (0, 2)
    assert locations == [0, 2]
    assert all(
        type(value) is int for value in validate_locations(make_scenario(), locations)
    )


@pytest.mark.parametrize(
    "locations, error",
    [
        ((), ValueError),
        ((0,), ValueError),
        ((0, 3), ValueError),
        ((0, -1), ValueError),
        ((0, True), TypeError),
        ((0, 1.0), TypeError),
        ((0, "1"), TypeError),
    ],
)
def test_invalid_location_chromosomes_are_rejected(
    locations: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        validate_locations(make_scenario(), locations)


@pytest.mark.parametrize(
    "field, message",
    [
        ("scenario", "OffloadingScenario"),
        ("normalization", "NormalizationConstants"),
        ("objective_config", "ObjectiveConfig"),
        ("load_config", "LoadBalanceConfig"),
    ],
)
def test_wrong_evaluation_types_are_rejected(field: str, message: str) -> None:
    scenario = make_scenario()
    kwargs = {
        "scenario": scenario,
        "locations": (0, 0),
        "normalization": derive_normalization(scenario),
        field: object(),
    }
    with pytest.raises(TypeError, match=message):
        evaluate_locations_exact(**kwargs)


def test_custom_load_weights_are_forwarded_to_the_common_evaluator() -> None:
    scenario = make_scenario()
    result = evaluate_locations_exact(
        scenario,
        (1, 2),
        normalization=derive_normalization(scenario),
        load_config=LoadBalanceConfig(1.0, 0.0, 0.0),
    )
    assert [server.load.weighted_load for server in result.servers] == [0.5, 0.5]
