from dataclasses import replace
from math import exp

import numpy as np
import pytest

from src.config import GeneticSearchConfig, LoadBalanceConfig, SwarmSearchConfig
from src.evaluation import derive_normalization, evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import ObjectiveConfig
from src.optimizers import sapso
from src.optimizers.exact import solve_exact
from src.optimizers.locations import evaluate_locations_exact
from src.random_utils import create_random_state
from tests.scenario_helpers import make_scenario


def test_annealing_matches_equation_40_and_zero_temperature_limit() -> None:
    assert sapso.annealing_probability(0.2, 0.3, 0.05) == 1.0
    assert sapso.annealing_probability(0.3, 0.3, 0.05) == 1.0
    assert sapso.annealing_probability(0.3, 0.2, 0.05) == pytest.approx(exp(-2.0))
    assert sapso.annealing_probability(0.3, 0.2, 0.0) == 0.0


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"particle_count": 1}, ValueError),
        ({"iterations": -1}, ValueError),
        ({"iterations": True}, TypeError),
        ({"inertia_low": 0.95}, ValueError),
        ({"cognitive": -1.0}, ValueError),
        ({"velocity_limit": 0.0}, ValueError),
        ({"initial_temperature": float("nan")}, ValueError),
        ({"cooling_rate": 0.0}, ValueError),
        ({"cooling_rate": 1.1}, ValueError),
    ],
)
def test_invalid_swarm_parameters_fail_early(kwargs: dict, error: type) -> None:
    with pytest.raises(error):
        SwarmSearchConfig(**kwargs)


def test_fixed_locations_reach_known_endpoint_and_keep_historical_best() -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    config = SwarmSearchConfig(iterations=30, initial_temperature=100.0)
    weights = ObjectiveConfig(1.0, 0.0, 0.0)
    state = create_random_state(42)
    python_before = state.python_random.getstate()
    result = sapso.solve_sapso(
        scenario,
        (1, 2),
        normalization=normalization,
        random_state=state,
        config=config,
        objective_config=weights,
        load_config=LoadBalanceConfig(1.0, 0.0, 0.0),
    )
    reference = evaluate_locations_exact(
        scenario, (1, 2), normalization=normalization, objective_config=weights
    )
    assert result.best.objective.value == pytest.approx(reference.objective.value)
    assert [task.decision.offloading_ratio for task in result.best.tasks] == [1.0, 1.0]
    assert result.evaluations == config.evaluation_budget
    assert len(result.best_history) == config.iterations + 1
    assert all(a >= b for a, b in zip(result.best_history, result.best_history[1:]))
    assert result.accepted_worse > 0
    assert state.python_random.getstate() == python_before
    assert [server.load.weighted_load for server in result.best.servers] == [0.5, 0.5]


def test_selected_zero_keeps_reservation_and_local_dimensions_stay_zero() -> None:
    scenario = replace(
        make_scenario(),
        security_threshold=0.0,
        links=tuple(
            replace(link, rate_bits_per_second=4e6) if link.task_id == "t2" else link
            for link in make_scenario().links
        ),
    )
    for locations in ((1, 2), (0, 2)):
        result = sapso.solve_sapso(
            scenario,
            locations,
            normalization=derive_normalization(scenario),
            random_state=create_random_state(42),
            config=SwarmSearchConfig(iterations=30),
            objective_config=ObjectiveConfig(0.8, 0.0, 0.2),
        )
        assert result.best.tasks[1].decision.offloading_ratio == 0.0
        assert result.best.tasks[1].decision.server_id == "s2"
        assert result.best.servers[1].load.weighted_load > 0.0
        if locations[0] == 0:
            assert result.best.tasks[0].decision.offloading_ratio == 0.0
            assert result.best.tasks[0].decision.server_id is None


def test_first_particle_step_matches_equations_37_to_39_and_projection() -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    config = SwarmSearchConfig(particle_count=3, iterations=1, velocity_limit=0.15)
    rng = create_random_state(7).numpy_random
    positions = rng.random((3, 2))
    velocities = rng.uniform(-0.15, 0.15, (3, 2))

    def values(ratios):
        return (
            3.6 - 0.7 * ratios[:, 0] - 1.4 * ratios[:, 1]
        ) / normalization.latency_seconds

    initial_values = values(positions)
    best_position = positions[int(np.argmin(initial_values))]
    rng.random((3, 2))  # The cognitive draw is consumed even when pbest == x.
    velocity = config.inertia_low * velocities + config.social * rng.random((3, 2)) * (
        best_position - positions
    )
    proposals = np.clip(positions + np.clip(velocity, -0.15, 0.15), 0.0, 1.0)
    # Every new global-best proposal is also better than its current particle.
    expected_best = min(float(min(initial_values)), float(min(values(proposals))))
    result = sapso.solve_sapso(
        scenario,
        (1, 2),
        normalization=normalization,
        random_state=create_random_state(7),
        config=config,
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
    )
    assert result.best_history == pytest.approx(
        (float(min(initial_values)), expected_best)
    )
    assert result.best_history[1] < result.best_history[0]


def test_all_local_and_infeasible_locations_do_not_draw_swarm_randomness() -> None:
    scenario = make_scenario()
    state = create_random_state(42)
    untouched = create_random_state(42)
    local = sapso.solve_sapso(
        scenario,
        (0, 0),
        normalization=derive_normalization(scenario),
        random_state=state,
    )
    assert local.evaluations == 1
    assert local.best_history == (local.best.objective.value,)
    overloaded = replace(scenario, bandwidth_capacity_hz=9e6)
    with pytest.raises(CapacityExceededError):
        sapso.solve_sapso(
            overloaded,
            (1, 1),
            normalization=derive_normalization(overloaded),
            random_state=state,
        )
    assert state.numpy_random.random() == untouched.numpy_random.random()
    assert state.python_random.random() == untouched.python_random.random()


def test_zero_iterations_still_evaluates_random_particles_without_using_oracle() -> (
    None
):
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    config = SwarmSearchConfig(particle_count=2, iterations=0)
    result = sapso.solve_sapso(
        scenario,
        (1, 2),
        normalization=normalization,
        random_state=create_random_state(42),
        config=config,
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
    )
    oracle = evaluate_locations_exact(
        scenario,
        (1, 2),
        normalization=normalization,
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
    )
    assert result.evaluations == config.evaluation_budget == 3
    assert len(result.best_history) == 1
    assert result.best.objective.value > oracle.objective.value
    assert all(0.0 < task.decision.offloading_ratio < 1.0 for task in result.best.tasks)


def test_two_layers_replay_and_count_every_plan_call_including_infeasibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = replace(make_scenario(), bandwidth_capacity_hz=9e6)
    normalization = derive_normalization(scenario)
    calls = 0

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return evaluate_plan(*args, **kwargs)

    monkeypatch.setattr(sapso, "evaluate_plan", counted)
    genetic = GeneticSearchConfig(population_size=8, generations=3)
    swarm = SwarmSearchConfig(particle_count=4, iterations=6)
    args = {
        "scenario": scenario,
        "normalization": normalization,
        "genetic_config": genetic,
        "swarm_config": swarm,
    }
    first = sapso.solve_boalbfs(**args, random_state=create_random_state(42))
    assert first.plan_evaluations == calls
    assert first.genetic.evaluations == genetic.evaluation_budget
    assert first.genetic.infeasible_evaluations > 0
    assert (
        genetic.evaluation_budget
        < calls
        <= genetic.evaluation_budget * swarm.evaluation_budget
    )
    second = sapso.solve_boalbfs(**args, random_state=create_random_state(42))
    assert second == first
    assert calls == 2 * first.plan_evaluations
    exact = solve_exact(scenario, normalization=normalization)
    assert first.genetic.best.objective.value >= exact.best.objective.value - 1e-12
    assert (
        first.genetic.history[-1].best_objective_value
        <= first.genetic.history[0].best_objective_value
    )


def test_non_capacity_errors_are_not_reported_as_infeasible() -> None:
    scenario = make_scenario()
    with pytest.raises(TypeError, match="ObjectiveConfig"):
        sapso.solve_boalbfs(
            scenario,
            normalization=derive_normalization(scenario),
            random_state=create_random_state(42),
            objective_config=object(),
        )
