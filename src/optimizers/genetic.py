"""Adaptive genetic location search; ratio evaluation is supplied separately."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import fsum, inf
from random import Random

from src.config import GeneticSearchConfig, LoadBalanceConfig
from src.evaluation import PlanEvaluation
from src.load_balance import CapacityExceededError
from src.objective import NormalizationConstants, ObjectiveConfig
from src.optimizers.locations import evaluate_locations_exact
from src.random_utils import RandomState
from src.scenario import OffloadingScenario
from src.validation import validate_non_negative, validate_unit_interval


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    """Generation 0 is initialization; mean objective excludes infeasible plans."""

    generation: int
    best_objective_value: float
    mean_feasible_objective_value: float
    feasible_individuals: int
    unique_locations: int
    evaluations_completed: int


@dataclass(frozen=True, slots=True)
class GeneticSearchResult:
    """Best observed feasible plan, not a guaranteed global optimum."""

    best: PlanEvaluation
    best_locations: tuple[int, ...]
    history: tuple[GenerationSummary, ...]
    evaluations: int
    infeasible_evaluations: int


@dataclass(frozen=True, slots=True)
class _Individual:
    locations: tuple[int, ...]
    evaluation: PlanEvaluation | None

    @property
    def objective_value(self) -> float:
        return inf if self.evaluation is None else self.evaluation.objective.value


def calculate_relative_fitness(
    objectives: Sequence[float | None],
) -> tuple[float, ...]:
    """Scale Eq. (32)'s 1/F by min(F) to avoid inverse overflow.

    None denotes an infeasible individual and has zero selection weight.
    If any F is exactly zero, select only zero-objective individuals with
    equal weight. Reject an entirely infeasible population.
    """

    objectives = tuple(objectives)
    feasible = [value for value in objectives if value is not None]
    if not feasible:
        raise ValueError("population must contain a feasible individual")
    for value in feasible:
        validate_non_negative(value, "objective value")
    minimum = min(feasible)
    if minimum == 0.0:
        return tuple(float(value == 0.0) for value in objectives)
    return tuple(0.0 if value is None else minimum / value for value in objectives)


def adaptive_probability(
    fitness: float,
    mean_fitness: float,
    max_fitness: float,
    *,
    high: float,
    low: float,
) -> float:
    """Apply the piecewise form of Eqs. (34)-(35); flat populations use high."""

    for value, name in (
        (fitness, "fitness"),
        (mean_fitness, "mean_fitness"),
        (max_fitness, "max_fitness"),
    ):
        validate_non_negative(value, name)
    validate_unit_interval(high, "high")
    validate_unit_interval(low, "low")
    if high <= low:
        raise ValueError("high must exceed low")
    if mean_fitness > max_fitness or fitness > max_fitness:
        raise ValueError("fitness and mean_fitness must not exceed max_fitness")
    if max_fitness == mean_fitness or fitness < mean_fitness:
        return high
    fraction = (fitness - mean_fitness) / (max_fitness - mean_fitness)
    return max(low, min(high, high - (high - low) * fraction))


def _roulette(fitness: tuple[float, ...], rng: Random) -> int:
    target = rng.random() * fsum(fitness)
    cumulative = 0.0
    for index, weight in enumerate(fitness):
        cumulative += weight
        if weight > 0.0 and target < cumulative:
            return index
    # The weighted sum may differ by a final rounding unit from accumulation.
    return max(index for index, weight in enumerate(fitness) if weight > 0.0)


def _crossover(
    first: tuple[int, ...], second: tuple[int, ...], rng: Random
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    start = rng.randrange(len(first))
    stop = rng.randrange(start + 1, len(first) + 1)
    return (
        first[:start] + second[start:stop] + first[stop:],
        second[:start] + first[start:stop] + second[stop:],
    )


def _mutate(
    locations: tuple[int, ...],
    server_count: int,
    probability: float,
    rng: Random,
    *,
    allow_local: bool = True,
) -> tuple[int, ...]:
    alternatives = server_count if allow_local else server_count - 1
    if alternatives == 0:
        return locations
    genes = list(locations)
    for index, gene in enumerate(genes):
        if rng.random() < probability:
            replacement = rng.randrange(alternatives) + int(not allow_local)
            genes[index] = replacement + int(replacement >= gene)
    return tuple(genes)


def _mean(values: tuple[float, ...]) -> float:
    # Divide before summing to avoid overflow; bound rounding at equal extremes.
    return max(
        min(values), min(max(values), fsum(value / len(values) for value in values))
    )


def search_locations(
    scenario: OffloadingScenario,
    evaluator: Callable[[tuple[int, ...]], PlanEvaluation],
    *,
    random_state: RandomState,
    config: GeneticSearchConfig | None = None,
    allow_local: bool = True,
) -> GeneticSearchResult:
    """Search M+1 location genes with a bounded, reproducible upper-layer GA.

    The evaluator supplies ratios and must retain the supplied locations
    in scenario task order. Capacity violations have zero selection weight;
    other errors propagate. One all-local individual seeds initialization;
    remaining genes are uniform random. Elitism preserves the best result.
    No evaluation cache is imposed on a potentially stochastic lower layer.
    A fresh independent RandomState is needed for replay from the same seed.

    Selection/crossover use f_u=1/F, scaled without changing probabilities.
    Mutation follows printed Eq. (35)'s f_l=F (Eq. 36), despite its upper-
    layer context. Its statistics exclude infeasible individuals. These
    interpretation and initialization choices are explicitly documented.
    Edge-only comparisons set allow_local=False: genes are then 1..M and
    initialization includes a round-robin assignment instead of all-local.
    An infeasible round-robin seed is an initialization failure, not proof
    that no feasible full-edge plan exists.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    if not isinstance(random_state, RandomState):
        raise TypeError("random_state must be a RandomState")
    if config is None:
        config = GeneticSearchConfig()
    elif not isinstance(config, GeneticSearchConfig):
        raise TypeError("config must be a GeneticSearchConfig")
    if not isinstance(allow_local, bool):
        raise TypeError("allow_local must be a bool")
    rng = random_state.python_random
    task_count, server_count = len(scenario.tasks), len(scenario.servers)
    evaluations = 0
    infeasible_evaluations = 0
    reference_normalization: NormalizationConstants | None = None

    def evaluate(locations: tuple[int, ...]) -> _Individual:
        nonlocal evaluations, infeasible_evaluations, reference_normalization
        evaluations += 1
        try:
            result = evaluator(locations)
        except CapacityExceededError:
            infeasible_evaluations += 1
            return _Individual(locations, None)
        if not isinstance(result, PlanEvaluation):
            raise TypeError("evaluator must return a PlanEvaluation")
        if not isinstance(result.normalization, NormalizationConstants):
            raise TypeError("evaluator must retain NormalizationConstants")
        if reference_normalization is None:
            reference_normalization = result.normalization
        elif result.normalization != reference_normalization:
            raise ValueError("evaluator changed the fixed normalization")
        if len(result.tasks) != task_count:
            raise ValueError("evaluator changed the supplied task count")
        for task, gene, item in zip(
            scenario.tasks, locations, result.tasks, strict=True
        ):
            server_id = (
                None if gene == 0 else scenario.servers[gene - 1].server.server_id
            )
            if (
                item.decision.task_id != task.task.task_id
                or item.decision.server_id != server_id
            ):
                raise ValueError(
                    "evaluator changed the supplied task order or locations"
                )
        validate_non_negative(result.objective.value, "objective value")
        return _Individual(locations, result)

    initial = (
        (0,) * task_count
        if allow_local
        else tuple(index % server_count + 1 for index in range(task_count))
    )
    population = [evaluate(initial)]
    if not allow_local and population[0].evaluation is None:
        raise CapacityExceededError(
            "round-robin Edge initialization exceeds capacity; "
            "this is not proof that every Edge assignment is infeasible"
        )
    population.extend(
        evaluate(
            tuple(
                rng.randrange(int(not allow_local), server_count + 1)
                for _ in range(task_count)
            )
        )
        for _ in range(config.population_size - 1)
    )
    history = []
    for generation in range(config.generations + 1):
        objectives = tuple(
            None if individual.evaluation is None else individual.objective_value
            for individual in population
        )
        fitness = calculate_relative_fitness(objectives)
        feasible_values = tuple(value for value in objectives if value is not None)
        best = min(population, key=lambda individual: individual.objective_value)
        mean_objective = _mean(feasible_values)
        history.append(
            GenerationSummary(
                generation,
                best.objective_value,
                mean_objective,
                len(feasible_values),
                len({individual.locations for individual in population}),
                evaluations,
            )
        )
        if generation == config.generations:
            break
        mean_fitness = _mean(fitness)
        max_fitness, max_objective = max(fitness), max(feasible_values)
        offspring = sorted(
            population, key=lambda individual: individual.objective_value
        )[: config.elite_count]
        while len(offspring) < config.population_size:
            first_index, second_index = _roulette(fitness, rng), _roulette(fitness, rng)
            parents = (population[first_index], population[second_index])
            crossover_probability = adaptive_probability(
                max(fitness[first_index], fitness[second_index]),
                mean_fitness,
                max_fitness,
                high=config.crossover_high,
                low=config.crossover_low,
            )
            children = (parents[0].locations, parents[1].locations)
            if rng.random() < crossover_probability:
                children = _crossover(*children, rng)
            for child, parent in zip(children, parents, strict=True):
                if len(offspring) == config.population_size:
                    break
                mutation_probability = adaptive_probability(
                    parent.objective_value,
                    mean_objective,
                    max_objective,
                    high=config.mutation_high,
                    low=config.mutation_low,
                )
                offspring.append(
                    evaluate(
                        _mutate(
                            child,
                            server_count,
                            mutation_probability,
                            rng,
                            allow_local=allow_local,
                        )
                    )
                )
        population = offspring
    assert best.evaluation is not None
    return GeneticSearchResult(
        best.evaluation,
        best.locations,
        tuple(history),
        evaluations,
        infeasible_evaluations,
    )


def solve_genetic(
    scenario: OffloadingScenario,
    *,
    normalization: NormalizationConstants,
    random_state: RandomState,
    config: GeneticSearchConfig | None = None,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
) -> GeneticSearchResult:
    """Stage-7 GA with the affine ratio reference; deliberately not BOALBFS."""

    def evaluator(locations: tuple[int, ...]) -> PlanEvaluation:
        return evaluate_locations_exact(
            scenario,
            locations,
            normalization=normalization,
            objective_config=objective_config,
            load_config=load_config,
        )

    return search_locations(
        scenario, evaluator, random_state=random_state, config=config
    )
