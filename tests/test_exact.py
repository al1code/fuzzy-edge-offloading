from dataclasses import replace
from itertools import product

import numpy as np
import pytest

from src.config import ExperimentConfig, LoadBalanceConfig, SyntheticScenarioConfig
from src.evaluation import derive_normalization, evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import NormalizationConstants, ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.scenario import OffloadingDecision
from src.synthetic import generate_synthetic_dataset
from tests.scenario_helpers import make_scenario


def test_default_weights_match_hand_calculated_local_optimum() -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    result = solve_exact(scenario, normalization=normalization)
    assert result.best.objective.value == pytest.approx(1 / 3)
    assert result.best.total_latency_seconds == pytest.approx(3.6)
    assert result.best.total_security_risk == 0.0
    assert [task.decision for task in result.best.tasks] == [
        OffloadingDecision("t1", 0.0),
        OffloadingDecision("t2", 0.0),
    ]
    assert result.best.normalization is normalization
    assert result.candidates_checked == result.feasible_candidates == 25
    assert result.infeasible_candidates == 0


def test_latency_only_finds_full_offloading_with_explicit_scales_and_load_weights() -> (
    None
):
    scenario = make_scenario()
    result = solve_exact(
        scenario,
        normalization=NormalizationConstants(10.0, 1.0),
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
        load_config=LoadBalanceConfig(1.0, 0.0, 0.0),
    )
    assert result.best.total_latency_seconds == pytest.approx(1.5)
    assert result.best.objective.value == pytest.approx(0.15)
    assert [task.decision for task in result.best.tasks] == [
        OffloadingDecision("t1", 1.0, "s1"),
        OffloadingDecision("t2", 1.0, "s1"),
    ]
    assert result.best.servers[0].load.weighted_load == 1.0


def test_optimum_can_reserve_a_server_for_a_task_with_zero_offloading() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        security_threshold=0.0,
        links=tuple(
            replace(link, rate_bits_per_second=4e6) if link.task_id == "t2" else link
            for link in scenario.links
        ),
    )
    normalization = derive_normalization(scenario)
    result = solve_exact(
        scenario,
        normalization=normalization,
        objective_config=ObjectiveConfig(0.8, 0.0, 0.2),
    )
    assert normalization.latency_seconds == pytest.approx(5.8)
    assert [task.decision for task in result.best.tasks] == [
        OffloadingDecision("t1", 1.0, "s1"),
        OffloadingDecision("t2", 0.0, "s2"),
    ]
    assert result.best.objective.value == pytest.approx(0.4)
    assert result.best.objective.load_variance == 0.0

    # Independent arithmetic checks interior ratios, not just endpoint plans.
    options = [(None, 0.0)] + [
        (server, ratio)
        for server in ("s1", "s2")
        for ratio in (0.0, 0.25, 0.5, 0.75, 1.0)
    ]
    grid_values = []
    for (server1, ratio1), (server2, ratio2) in product(options, repeat=2):
        latency = 1.2 * (1 - ratio1) + 0.5 * ratio1
        latency += 2.4 * (1 - ratio2) + 4.6 * ratio2
        loads = [int(server1 == s) / 3 + int(server2 == s) / 3 for s in ("s1", "s2")]
        variance = (loads[0] - loads[1]) ** 2 / 4
        grid_values.append(0.8 * latency / 5.8 + 0.2 * variance)
    assert result.best.objective.value == pytest.approx(min(grid_values))


@pytest.mark.parametrize("seed", [0, 7, 42])
@pytest.mark.parametrize(
    "weights",
    [ObjectiveConfig(), ObjectiveConfig(1.0, 0.0, 0.0), ObjectiveConfig(0.0, 0.5, 0.5)],
)
def test_endpoint_optimum_bounds_dense_ratio_grid_on_generated_scenarios(
    seed: int, weights: ObjectiveConfig
) -> None:
    dataset = generate_synthetic_dataset(
        replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(seed, 2, 2))
    )
    scenario = dataset.scenario
    result = solve_exact(
        scenario, normalization=dataset.normalization, objective_config=weights
    )
    options = tuple(
        (OffloadingDecision(task.task.task_id, 0.0),)
        + tuple(
            OffloadingDecision(task.task.task_id, ratio, server.server.server_id)
            for server in scenario.servers
            for ratio in (0.0, 0.25, 0.5, 0.75, 1.0)
        )
        for task in scenario.tasks
    )
    grid_minimum = min(
        evaluate_plan(
            scenario,
            plan,
            normalization=dataset.normalization,
            objective_config=weights,
        ).objective.value
        for plan in product(*options)
    )
    assert result.best.objective.value == pytest.approx(grid_minimum, abs=1e-14)


@pytest.mark.parametrize(
    "resource, capacity, name",
    [
        ("cpu_capacity_cycles_per_second", 7e9, "CPU"),
        ("memory_capacity_mb", 500.0, "memory"),
        ("bandwidth_capacity_hz", 9e6, "bandwidth"),
    ],
)
def test_capacity_infeasible_plans_are_counted_and_never_returned(
    resource: str, capacity: float, name: str
) -> None:
    scenario = make_scenario()
    if resource == "bandwidth_capacity_hz":
        scenario = replace(scenario, bandwidth_capacity_hz=capacity)
        expected_infeasible = 8
    else:
        scenario = replace(
            scenario,
            servers=(
                replace(
                    scenario.servers[0],
                    server=replace(scenario.servers[0].server, **{resource: capacity}),
                ),
                scenario.servers[1],
            ),
        )
        expected_infeasible = 4
    with pytest.raises(CapacityExceededError, match=f"server s1: {name}"):
        evaluate_plan(
            scenario,
            (OffloadingDecision("t1", 0.0, "s1"), OffloadingDecision("t2", 0.0, "s1")),
            normalization=derive_normalization(scenario),
        )
    result = solve_exact(
        scenario,
        normalization=derive_normalization(scenario),
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
    )
    assert result.best.total_latency_seconds == pytest.approx(1.5)
    assert result.candidates_checked == 25
    assert result.infeasible_candidates == expected_infeasible
    assert result.feasible_candidates == 25 - expected_infeasible
    assert [task.decision.server_id for task in result.best.tasks] == ["s1", "s2"]


def test_all_local_remains_feasible_when_no_edge_reservation_fits() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        servers=tuple(
            replace(server, server=replace(server.server, memory_capacity_mb=1.0))
            for server in scenario.servers
        ),
    )
    result = solve_exact(scenario, normalization=derive_normalization(scenario))
    assert result.feasible_candidates == 1
    assert result.infeasible_candidates == 24
    assert all(task.decision.server_id is None for task in result.best.tasks)


def test_single_server_has_three_choices_per_task_and_zero_load_variance() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        servers=scenario.servers[:1],
        links=tuple(link for link in scenario.links if link.server_id == "s1"),
    )
    result = solve_exact(scenario, normalization=derive_normalization(scenario))
    assert result.candidates_checked == result.feasible_candidates == 9
    assert result.best.objective.load_variance == 0.0


def test_equal_objectives_keep_all_local_without_extra_reservations() -> None:
    scenario = replace(make_scenario(), security_threshold=0.0)
    kwargs = {
        "normalization": derive_normalization(scenario),
        "objective_config": ObjectiveConfig(0.0, 1.0, 0.0),
    }
    first = solve_exact(scenario, **kwargs)
    second = solve_exact(scenario, **kwargs)
    assert first == second
    assert first.best.objective.value == 0.0
    assert all(task.decision.server_id is None for task in first.best.tasks)


def test_budget_is_checked_before_evaluating_a_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_evaluation(*args: object, **kwargs: object) -> None:
        pytest.fail("budget rejection must happen before evaluating a candidate")

    monkeypatch.setattr("src.optimizers.exact.evaluate_plan", unexpected_evaluation)
    scenario = make_scenario()
    with pytest.raises(ValueError, match="25 candidates.*max_candidates=24"):
        solve_exact(
            scenario, normalization=derive_normalization(scenario), max_candidates=24
        )


def test_exact_budget_boundary_and_numpy_integer_are_accepted() -> None:
    scenario = make_scenario()
    result = solve_exact(
        scenario,
        normalization=derive_normalization(scenario),
        max_candidates=np.int64(25),
    )
    assert result.candidates_checked == 25


@pytest.mark.parametrize(
    "budget, error",
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (25.0, TypeError),
        ("25", TypeError),
        (None, TypeError),
    ],
)
def test_invalid_budget_is_rejected(budget: object, error: type[Exception]) -> None:
    scenario = make_scenario()
    with pytest.raises(error, match="max_candidates"):
        solve_exact(
            scenario,
            normalization=derive_normalization(scenario),
            max_candidates=budget,
        )


@pytest.mark.parametrize(
    "field, message",
    [
        ("scenario", "OffloadingScenario"),
        ("normalization", "NormalizationConstants"),
        ("objective_config", "ObjectiveConfig"),
        ("load_config", "LoadBalanceConfig"),
    ],
)
def test_invalid_domain_types_are_not_treated_as_infeasible(
    field: str, message: str
) -> None:
    scenario = make_scenario()
    kwargs = {
        "scenario": scenario,
        "normalization": derive_normalization(scenario),
        field: object(),
    }
    with pytest.raises(TypeError, match=message):
        solve_exact(**kwargs)


def test_non_capacity_calculation_errors_are_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fail_after_local(*args: object, **kwargs: object) -> object:
        nonlocal calls
        calls += 1
        if calls > 1:
            raise ValueError("invalid calculation, not a capacity violation")
        return evaluate_plan(*args, **kwargs)

    monkeypatch.setattr("src.optimizers.exact.evaluate_plan", fail_after_local)
    scenario = make_scenario()
    with pytest.raises(ValueError, match="invalid calculation"):
        solve_exact(scenario, normalization=derive_normalization(scenario))
    assert calls == 2
