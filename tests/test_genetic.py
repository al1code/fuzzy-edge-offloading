import random
from dataclasses import replace
from functools import partial
from math import inf, nextafter
from random import Random

import numpy as np
import pytest

from src.config import GeneticSearchConfig
from src.evaluation import derive_normalization
from src.objective import NormalizationConstants, ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.optimizers.genetic import (
    _crossover,
    _mean,
    _mutate,
    _roulette,
    adaptive_probability,
    calculate_relative_fitness,
    search_locations,
    solve_genetic,
)
from src.optimizers.locations import evaluate_locations_exact
from src.random_utils import create_random_state
from tests.scenario_helpers import make_scenario


def test_relative_fitness_matches_reciprocal_ratios_without_inverse_overflow() -> None:
    assert calculate_relative_fitness((0.2, 0.4, None, 0.8)) == (1.0, 0.5, 0.0, 0.25)
    assert calculate_relative_fitness((1e-310, 2e-310)) == pytest.approx((1.0, 0.5))
    assert calculate_relative_fitness((3.0, 3.0)) == (1.0, 1.0)


def test_zero_objectives_select_only_zero_solutions_and_infeasible_has_no_weight() -> (
    None
):
    assert calculate_relative_fitness((None, 0.0, 1.0, 0.0)) == (0.0, 1.0, 0.0, 1.0)


@pytest.mark.parametrize("values", [(), (None,), (None, None)])
def test_entirely_infeasible_population_is_rejected(values: tuple[object, ...]) -> None:
    with pytest.raises(ValueError, match="feasible"):
        calculate_relative_fitness(values)


@pytest.mark.parametrize(
    "value, error",
    [
        (-0.1, ValueError),
        (float("nan"), ValueError),
        (inf, ValueError),
        (True, TypeError),
        ("1", TypeError),
    ],
)
def test_invalid_objective_values_are_not_selection_weights(
    value: object, error: type[Exception]
) -> None:
    with pytest.raises(error, match="objective value"):
        calculate_relative_fitness((value,))


@pytest.mark.parametrize(
    "fitness, mean, maximum, expected",
    [
        (1.0, 2.0, 4.0, 0.9),
        (2.0, 2.0, 4.0, 0.9),
        (3.0, 2.0, 4.0, 0.75),
        (4.0, 2.0, 4.0, 0.6),
        (4.0, 4.0, 4.0, 0.9),
        (0.0, 0.0, 0.0, 0.9),
    ],
)
def test_adaptive_probability_matches_hand_calculated_piecewise_formula(
    fitness: float, mean: float, maximum: float, expected: float
) -> None:
    assert adaptive_probability(
        fitness, mean, maximum, high=0.9, low=0.6
    ) == pytest.approx(expected)


def test_common_positive_scaling_does_not_change_crossover_probability() -> None:
    original = adaptive_probability(3.0, 2.0, 4.0, high=0.9, low=0.6)
    assert adaptive_probability(0.75, 0.5, 1.0, high=0.9, low=0.6) == original


def test_mutation_uses_printed_lower_objective_convention_not_reciprocal_fitness() -> (
    None
):
    assert adaptive_probability(1.0, 2.0, 4.0, high=0.1, low=0.001) == 0.1
    assert adaptive_probability(4.0, 2.0, 4.0, high=0.1, low=0.001) == pytest.approx(
        0.001
    )


@pytest.mark.parametrize(
    "field, value, error",
    [
        ("fitness", -1.0, ValueError),
        ("fitness", 5.0, ValueError),
        ("mean_fitness", 5.0, ValueError),
        ("max_fitness", float("inf"), ValueError),
        ("high", 1.1, ValueError),
        ("low", -0.1, ValueError),
        ("low", 0.9, ValueError),
        ("fitness", True, TypeError),
    ],
)
def test_invalid_adaptive_probability_arguments_are_rejected(
    field: str, value: object, error: type[Exception]
) -> None:
    kwargs = {
        "fitness": 3.0,
        "mean_fitness": 2.0,
        "max_fitness": 4.0,
        "high": 0.9,
        "low": 0.6,
        field: value,
    }
    with pytest.raises(error):
        adaptive_probability(**kwargs)


def test_roulette_never_selects_infeasible_zero_weight_individuals() -> None:
    rng = Random(42)
    assert {_roulette((0.0, 1.0, 0.0, 0.5), rng) for _ in range(1000)} == {1, 3}


def test_roulette_handles_zero_target_without_selecting_a_zero_weight() -> None:
    class ZeroRandom(Random):
        def random(self) -> float:
            return 0.0

    assert _roulette((0.0, 1.0), ZeroRandom()) == 1


def test_roulette_rounding_fallback_keeps_a_positive_weight() -> None:
    class EndpointRandom(Random):
        def random(self) -> float:
            return 1.0

    assert _roulette((0.0, 1.0, 0.5, 0.0), EndpointRandom()) == 2


def test_contiguous_crossover_preserves_valid_genes_and_parent_tuples() -> None:
    first, second = (0, 0, 0, 0), (1, 1, 1, 1)
    left, right = _crossover(first, second, Random(7))
    changed = [index for index, value in enumerate(left) if value == 1]
    assert changed
    assert changed == list(range(min(changed), max(changed) + 1))
    assert all(a + b == 1 for a, b in zip(left, right, strict=True))
    assert first == (0, 0, 0, 0)
    assert second == (1, 1, 1, 1)
    assert _crossover((0,), (1,), Random(0)) == ((1,), (0,))


def test_mutation_changes_selected_genes_without_invalidating_locations() -> None:
    original = (0, 1, 2, 3)
    assert _mutate(original, 3, 0.0, Random(42)) == original
    mutated = _mutate(original, 3, 1.0, Random(42))
    assert all(0 <= value <= 3 for value in mutated)
    assert all(a != b for a, b in zip(original, mutated, strict=True))
    assert original == (0, 1, 2, 3)
    assert _mutate((0, 1), 1, 1.0, Random(42)) == (1, 0)


def test_mean_is_finite_for_large_values_and_exact_on_flat_tiny_values() -> None:
    assert _mean((1e308, 1e308)) == 1e308
    tiny = nextafter(0.0, 1.0)
    assert _mean((tiny, tiny, tiny)) == tiny


@pytest.mark.parametrize("seed", [0, 7, 42])
@pytest.mark.parametrize(
    "weights",
    [ObjectiveConfig(), ObjectiveConfig(1.0, 0.0, 0.0), ObjectiveConfig(0.8, 0.0, 0.2)],
)
def test_small_known_runs_match_oracle_and_have_monotonic_elite_history(
    seed: int, weights: ObjectiveConfig
) -> None:
    scenario = replace(make_scenario(), security_threshold=0.0)
    normalization = derive_normalization(scenario)
    config = GeneticSearchConfig(population_size=20, generations=10, elite_count=2)
    result = solve_genetic(
        scenario,
        normalization=normalization,
        random_state=create_random_state(seed),
        config=config,
        objective_config=weights,
    )
    exact = solve_exact(scenario, normalization=normalization, objective_config=weights)
    assert result.best.objective.value == pytest.approx(exact.best.objective.value)
    assert result.evaluations == config.evaluation_budget == 200
    assert result.infeasible_evaluations == 0
    assert len(result.history) == 11
    assert [entry.generation for entry in result.history] == list(range(11))
    assert [entry.evaluations_completed for entry in result.history] == [
        20 + generation * 18 for generation in range(11)
    ]
    values = [entry.best_objective_value for entry in result.history]
    assert values == sorted(values, reverse=True)
    assert all(1 <= entry.unique_locations <= 20 for entry in result.history)
    assert result.best.normalization is normalization
    replay = evaluate_locations_exact(
        scenario,
        result.best_locations,
        normalization=normalization,
        objective_config=weights,
    )
    assert replay == result.best


def test_ga_can_find_a_selected_zero_ratio_optimum() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        security_threshold=0.0,
        links=tuple(
            replace(link, rate_bits_per_second=4e6) if link.task_id == "t2" else link
            for link in scenario.links
        ),
    )
    result = solve_genetic(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(42),
        config=GeneticSearchConfig(population_size=20, generations=5),
        objective_config=ObjectiveConfig(0.8, 0.0, 0.2),
    )
    assert result.best.objective.value == pytest.approx(0.4)
    assert result.best.tasks[0].decision.offloading_ratio == 1.0
    assert result.best.tasks[1].decision.offloading_ratio == 0.0
    assert result.best.tasks[1].decision.server_id is not None


def test_capacity_infeasible_offspring_are_counted_without_false_objectives() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        servers=tuple(
            replace(server, server=replace(server.server, memory_capacity_mb=1.0))
            for server in scenario.servers
        ),
    )
    config = GeneticSearchConfig(population_size=8, generations=3)
    result = solve_genetic(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(42),
        config=config,
    )
    assert result.infeasible_evaluations > 0
    assert result.evaluations == config.evaluation_budget
    assert all(task.decision.server_id is None for task in result.best.tasks)
    assert all(entry.feasible_individuals >= 1 for entry in result.history)


def test_single_task_single_server_and_zero_objective_remain_supported() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        tasks=scenario.tasks[:1],
        servers=scenario.servers[:1],
        links=scenario.links[:1],
        security_threshold=0.0,
    )
    config = GeneticSearchConfig(population_size=5, generations=3)
    result = solve_genetic(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(0),
        config=config,
        objective_config=ObjectiveConfig(0.0, 1.0, 0.0),
    )
    assert result.best.objective.value == 0.0
    assert result.evaluations == config.evaluation_budget
    assert all(entry.best_objective_value == 0.0 for entry in result.history)


def test_zero_generations_returns_initial_population_without_hidden_reproduction() -> (
    None
):
    scenario = make_scenario()
    config = GeneticSearchConfig(population_size=4, generations=0)
    result = solve_genetic(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(42),
        config=config,
    )
    assert result.evaluations == 4
    assert len(result.history) == 1
    assert result.history[0].generation == 0


def test_fresh_rng_replays_results_without_changing_global_random_generators() -> None:
    scenario = make_scenario()
    kwargs = {
        "normalization": derive_normalization(scenario),
        "config": GeneticSearchConfig(population_size=6, generations=3),
    }
    python_state, numpy_state = random.getstate(), np.random.get_state()
    first = solve_genetic(scenario, random_state=create_random_state(42), **kwargs)
    second = solve_genetic(scenario, random_state=create_random_state(42), **kwargs)
    assert first == second
    assert random.getstate() == python_state
    after = np.random.get_state()
    assert after[0] == numpy_state[0]
    np.testing.assert_array_equal(after[1], numpy_state[1])
    assert after[2:] == numpy_state[2:]


def test_upper_layer_accepts_a_separate_ratio_evaluator_without_a_hidden_cache() -> (
    None
):
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    calls = []

    def evaluator(locations: tuple[int, ...]):
        calls.append(locations)
        return evaluate_locations_exact(
            scenario, locations, normalization=normalization
        )

    config = GeneticSearchConfig(population_size=4, generations=2)
    result = search_locations(
        scenario, evaluator, random_state=create_random_state(42), config=config
    )
    assert len(calls) == result.evaluations == 10
    assert calls[0] == (0, 0)


@pytest.mark.parametrize(
    "field, message",
    [
        ("scenario", "OffloadingScenario"),
        ("evaluator", "callable"),
        ("random_state", "RandomState"),
        ("config", "GeneticSearchConfig"),
    ],
)
def test_wrong_upper_layer_types_are_rejected(field: str, message: str) -> None:
    scenario = make_scenario()
    kwargs = {
        "scenario": scenario,
        "evaluator": partial(
            evaluate_locations_exact,
            scenario,
            normalization=derive_normalization(scenario),
        ),
        "random_state": create_random_state(42),
        field: object(),
    }
    with pytest.raises(TypeError, match=message):
        search_locations(**kwargs)


@pytest.mark.parametrize(
    "change, message, error",
    [
        ("type", "PlanEvaluation", TypeError),
        ("count", "task count", ValueError),
        ("order", "task order", ValueError),
        ("locations", "locations", ValueError),
        ("objective", "finite", ValueError),
    ],
)
def test_invalid_lower_layer_results_are_not_accepted(
    change: str, message: str, error: type[Exception]
) -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)

    def evaluator(locations: tuple[int, ...]):
        if change == "type":
            return object()
        used = (0, 0) if change == "locations" else locations
        result = evaluate_locations_exact(scenario, used, normalization=normalization)
        if change == "count":
            return replace(result, tasks=result.tasks[:1])
        if change == "order":
            return replace(result, tasks=tuple(reversed(result.tasks)))
        if change == "objective":
            return replace(
                result, objective=replace(result.objective, latency_term=float("nan"))
            )
        return result

    with pytest.raises(error, match=message):
        search_locations(
            scenario,
            evaluator,
            random_state=create_random_state(0),
            config=GeneticSearchConfig(population_size=4, generations=0),
        )


def test_non_capacity_errors_from_lower_layer_propagate() -> None:
    def evaluator(locations: tuple[int, ...]):
        raise ValueError("calculation error, not infeasibility")

    with pytest.raises(ValueError, match="calculation error"):
        search_locations(
            make_scenario(), evaluator, random_state=create_random_state(42)
        )


def test_default_search_configuration_runs_and_retains_baseline_quality() -> None:
    scenario = make_scenario()
    result = solve_genetic(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(42),
    )
    assert result.evaluations == GeneticSearchConfig().evaluation_budget
    assert result.best.objective.value == pytest.approx(1 / 3)


@pytest.mark.parametrize("invalid_type", [False, True])
def test_lower_layer_cannot_replace_or_change_normalizers(invalid_type: bool) -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    calls = 0

    def evaluator(locations: tuple[int, ...]):
        nonlocal calls
        calls += 1
        result = evaluate_locations_exact(
            scenario, locations, normalization=normalization
        )
        if invalid_type:
            return replace(result, normalization=object())
        if calls > 1:
            return replace(result, normalization=NormalizationConstants(100.0, 1.0))
        return result

    with pytest.raises(
        TypeError if invalid_type else ValueError, match="[Nn]ormalization"
    ):
        search_locations(scenario, evaluator, random_state=create_random_state(42))
