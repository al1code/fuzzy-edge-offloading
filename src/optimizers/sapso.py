"""SA-PSO ratios (Eqs. 36-40) and the existing genetic location layer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import exp

import numpy as np

from src.config import GeneticSearchConfig, LoadBalanceConfig, SwarmSearchConfig
from src.evaluation import PlanEvaluation, evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import NormalizationConstants, ObjectiveConfig
from src.optimizers.genetic import GeneticSearchResult, search_locations
from src.optimizers.locations import validate_locations
from src.random_utils import RandomState
from src.scenario import OffloadingDecision, OffloadingScenario
from src.validation import validate_non_negative


@dataclass(frozen=True, slots=True)
class SwarmSearchResult:
    best: PlanEvaluation
    evaluations: int
    best_history: tuple[float, ...]
    accepted_worse: int


@dataclass(frozen=True, slots=True)
class BOALBFSResult:
    genetic: GeneticSearchResult
    plan_evaluations: int
    accepted_worse: int


def annealing_probability(
    candidate: float, current: float, temperature: float
) -> float:
    """Eq. (40); at underflowed zero temperature, reject all worse moves."""

    for value, name in (
        (candidate, "candidate"),
        (current, "current"),
        (temperature, "temperature"),
    ):
        validate_non_negative(value, name)
    if candidate <= current:
        return 1.0
    return exp(-(candidate - current) / temperature) if temperature > 0.0 else 0.0


def solve_sapso(
    scenario: OffloadingScenario,
    locations: Sequence[int],
    *,
    normalization: NormalizationConstants,
    random_state: RandomState,
    config: SwarmSearchConfig | None = None,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
) -> SwarmSearchResult:
    """Search ratios for fixed locations, without using the analytical oracle.

    Capacity depends only on locations, so check it before drawing particles.
    All-local needs one evaluation. Otherwise initialize uniform ratios and
    velocities, pin local dimensions to zero, and project proposals to [0,1].
    A rejected proposal retains the new velocity, not the new position.
    Personal/global historical bests never worsen after annealing acceptance.
    """

    locations = validate_locations(scenario, locations)
    if not isinstance(random_state, RandomState):
        raise TypeError("random_state must be a RandomState")
    if config is None:
        config = SwarmSearchConfig()
    elif not isinstance(config, SwarmSearchConfig):
        raise TypeError("config must be a SwarmSearchConfig")
    evaluations = 0

    def evaluate(ratios: np.ndarray) -> PlanEvaluation:
        nonlocal evaluations
        evaluations += 1
        decisions = tuple(
            OffloadingDecision(
                task.task.task_id,
                float(ratio),
                None if gene == 0 else scenario.servers[gene - 1].server.server_id,
            )
            for task, gene, ratio in zip(scenario.tasks, locations, ratios, strict=True)
        )
        return evaluate_plan(
            scenario,
            decisions,
            normalization=normalization,
            objective_config=objective_config,
            load_config=load_config,
        )

    local_dimensions = np.array(locations) == 0
    precheck = evaluate(np.zeros(len(locations)))
    if local_dimensions.all():
        return SwarmSearchResult(precheck, evaluations, (precheck.objective.value,), 0)
    rng = random_state.numpy_random
    shape = (config.particle_count, len(locations))
    positions = rng.random(shape)
    velocities = rng.uniform(-config.velocity_limit, config.velocity_limit, shape)
    positions[:, local_dimensions] = velocities[:, local_dimensions] = 0.0
    initial = [evaluate(position) for position in positions]
    values = np.array([result.objective.value for result in initial])
    personal_positions, personal_values = positions.copy(), values.copy()
    best_index = int(np.argmin(values))
    best, best_position = initial[best_index], positions[best_index].copy()
    history, accepted_worse = [best.objective.value], 0
    for iteration in range(1, config.iterations + 1):
        inertia = (
            config.inertia_high
            - (config.inertia_high - config.inertia_low) * iteration / config.iterations
        )
        temperature = config.initial_temperature * config.cooling_rate ** (
            iteration - 1
        )
        with np.errstate(over="raise", invalid="raise"):
            velocities = (
                inertia * velocities
                + config.cognitive
                * rng.random(shape)
                * (personal_positions - positions)
                + config.social * rng.random(shape) * (best_position - positions)
            )
        velocities = np.clip(velocities, -config.velocity_limit, config.velocity_limit)
        velocities[:, local_dimensions] = 0.0
        proposals = np.clip(positions + velocities, 0.0, 1.0)
        for index, proposal in enumerate(proposals):
            result = evaluate(proposal)
            value = result.objective.value
            probability = annealing_probability(
                value, float(values[index]), temperature
            )
            if value <= values[index] or rng.random() < probability:
                accepted_worse += int(value > values[index])
                positions[index], values[index] = proposal, value
                if value < personal_values[index]:
                    personal_positions[index], personal_values[index] = proposal, value
                if value < best.objective.value:
                    best, best_position = result, proposal.copy()
        history.append(best.objective.value)
    return SwarmSearchResult(best, evaluations, tuple(history), accepted_worse)


def solve_boalbfs(
    scenario: OffloadingScenario,
    *,
    normalization: NormalizationConstants,
    random_state: RandomState,
    genetic_config: GeneticSearchConfig | None = None,
    swarm_config: SwarmSearchConfig | None = None,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
) -> BOALBFSResult:
    """Couple GA locations to SA-PSO ratios, retaining actual plan-call counts."""

    plan_evaluations = accepted_worse = 0

    def evaluator(locations: tuple[int, ...]) -> PlanEvaluation:
        nonlocal plan_evaluations, accepted_worse
        try:
            result = solve_sapso(
                scenario,
                locations,
                normalization=normalization,
                random_state=random_state,
                config=swarm_config,
                objective_config=objective_config,
                load_config=load_config,
            )
        except CapacityExceededError:
            # Infeasibility is detected by the single precheck, before any swarm.
            plan_evaluations += 1
            raise
        plan_evaluations += result.evaluations
        accepted_worse += result.accepted_worse
        return result.best

    genetic = search_locations(
        scenario, evaluator, random_state=random_state, config=genetic_config
    )
    return BOALBFSResult(genetic, plan_evaluations, accepted_worse)
