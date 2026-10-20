"""The proposed Mamdani caps must constrain every optimisation path."""

import pytest

from src.config import GeneticSearchConfig, SwarmSearchConfig
from src.evaluation import derive_normalization, evaluate_plan
from src.objective import ObjectiveConfig
from src.optimizers.locations import evaluate_locations_exact
from src.optimizers.sapso import solve_boalbfs, solve_sapso
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from tests.scenario_helpers import make_scenario


@pytest.fixture
def caps() -> dict[str, float]:
    return {"t1": 0.35, "t2": 0.60}


def test_common_evaluator_rejects_a_ratio_above_its_policy_cap(caps) -> None:
    scenario = make_scenario()
    with pytest.raises(ValueError, match="policy cap"):
        evaluate_plan(
            scenario,
            (OffloadingDecision("t1", 0.36, "s1"), OffloadingDecision("t2", 0.0)),
            normalization=derive_normalization(scenario),
            ratio_caps=caps,
        )


@pytest.mark.parametrize(
    "invalid",
    [
        {"t1": 0.5},
        {"t1": 0.5, "t2": 0.5, "other": 0.5},
        {"t1": -0.1, "t2": 0.5},
        {"t1": 0.5, "t2": 1.1},
    ],
)
def test_cap_mapping_must_be_complete_and_unit_bounded(invalid) -> None:
    scenario = make_scenario()
    with pytest.raises(ValueError):
        evaluate_plan(
            scenario,
            (OffloadingDecision("t1", 0.0), OffloadingDecision("t2", 0.0)),
            normalization=derive_normalization(scenario),
            ratio_caps=invalid,
        )


def test_fixed_location_reference_uses_the_cap_endpoint(caps) -> None:
    scenario = make_scenario()
    result = evaluate_locations_exact(
        scenario,
        (1, 2),
        normalization=derive_normalization(scenario),
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
        ratio_caps=caps,
    )

    assert [task.decision.offloading_ratio for task in result.tasks] == pytest.approx(
        [0.35, 0.60]
    )


def test_sapso_normalizes_search_coordinates_then_respects_caps(caps) -> None:
    scenario = make_scenario()
    result = solve_sapso(
        scenario,
        (1, 2),
        normalization=derive_normalization(scenario),
        random_state=create_random_state(7),
        config=SwarmSearchConfig(particle_count=4, iterations=8),
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
        ratio_caps=caps,
    )

    assert result.evaluations == 37
    assert result.best.tasks[0].decision.offloading_ratio <= caps["t1"]
    assert result.best.tasks[1].decision.offloading_ratio <= caps["t2"]


def test_two_layer_solver_forwards_the_same_caps(caps) -> None:
    scenario = make_scenario()
    result = solve_boalbfs(
        scenario,
        normalization=derive_normalization(scenario),
        random_state=create_random_state(7),
        genetic_config=GeneticSearchConfig(population_size=4, generations=2),
        swarm_config=SwarmSearchConfig(particle_count=3, iterations=2),
        ratio_caps=caps,
    )

    assert all(
        task.decision.offloading_ratio <= caps[task.decision.task_id]
        for task in result.genetic.best.tasks
    )
