"""Bounded exhaustive verification of the current affine offloading model."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from src.config import LoadBalanceConfig
from src.evaluation import PlanEvaluation, evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import NormalizationConstants, ObjectiveConfig
from src.scenario import OffloadingDecision, OffloadingScenario
from src.validation import validate_integer

DEFAULT_MAX_CANDIDATES = 100_000


@dataclass(frozen=True, slots=True)
class ExactSearchResult:
    """A complete search result, including rejected capacity-infeasible plans."""

    best: PlanEvaluation
    candidates_checked: int
    feasible_candidates: int
    infeasible_candidates: int


def solve_exact(
    scenario: OffloadingScenario,
    *,
    normalization: NormalizationConstants,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
) -> ExactSearchResult:
    """Find a global optimum of the implemented model on a small instance.

    With fixed resources, links, and normalization, latency and risk are
    affine in each ratio; load and feasibility depend only on assignment.
    Thus at least one optimum has all ratios at 0 or 1. Enumerate local
    (no server, 0) and each selected server at both endpoints, retaining
    zero-ratio reservations. This is not the paper's BOALBFS algorithm.

    Reject (2*M+1)**N candidates above the budget before evaluating any
    plan. Do not return a truncated search as exact. Ties keep the first
    candidate: task/server scenario order, local first, then each server
    at ratio 0 followed by 1. Comparisons use floating-point objective
    values without a tolerance that could discard a real improvement.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    if not isinstance(normalization, NormalizationConstants):
        raise TypeError("normalization must be NormalizationConstants")
    if objective_config is not None and not isinstance(
        objective_config, ObjectiveConfig
    ):
        raise TypeError("objective_config must be an ObjectiveConfig")
    if load_config is not None and not isinstance(load_config, LoadBalanceConfig):
        raise TypeError("load_config must be a LoadBalanceConfig")
    validate_integer(max_candidates, "max_candidates", minimum=1)
    candidate_count = (2 * len(scenario.servers) + 1) ** len(scenario.tasks)
    if candidate_count > max_candidates:
        raise ValueError(
            f"exact search needs {candidate_count} candidates, exceeding "
            f"max_candidates={max_candidates}; use a smaller scenario"
        )

    options = tuple(
        (OffloadingDecision(task.task.task_id, 0.0),)
        + tuple(
            OffloadingDecision(task.task.task_id, ratio, server.server.server_id)
            for server in scenario.servers
            for ratio in (0.0, 1.0)
        )
        for task in scenario.tasks
    )
    plans = product(*options)
    # The first candidate is all-local and needs no edge resource reservations.
    best = evaluate_plan(
        scenario,
        next(plans),
        normalization=normalization,
        objective_config=objective_config,
        load_config=load_config,
    )
    feasible_candidates = 1
    infeasible_candidates = 0
    for decisions in plans:
        try:
            result = evaluate_plan(
                scenario,
                decisions,
                normalization=normalization,
                objective_config=objective_config,
                load_config=load_config,
            )
        except CapacityExceededError:
            infeasible_candidates += 1
            continue
        feasible_candidates += 1
        if result.objective.value < best.objective.value:
            best = result
    return ExactSearchResult(
        best, candidate_count, feasible_candidates, infeasible_candidates
    )
