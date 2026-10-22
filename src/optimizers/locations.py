"""Location chromosomes and an affine fixed-location ratio reference."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from src.config import LoadBalanceConfig
from src.evaluation import PlanEvaluation, evaluate_plan
from src.fuzzy_security import calculate_security_risk
from src.latency import calculate_task_latency
from src.objective import NormalizationConstants, ObjectiveConfig, calculate_objective
from src.ratio_caps import validate_ratio_caps
from src.scenario import OffloadingDecision, OffloadingScenario
from src.validation import validate_integer


def validate_locations(
    scenario: OffloadingScenario, locations: Sequence[int]
) -> tuple[int, ...]:
    """Snapshot genes in task order: 0 is local, j selects server j-1."""

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    locations = tuple(locations)
    if len(locations) != len(scenario.tasks):
        raise ValueError("exactly one location for each scenario task is required")
    for gene in locations:
        validate_integer(gene, "location", maximum=len(scenario.servers))
    return tuple(int(gene) for gene in locations)


def evaluate_locations_exact(
    scenario: OffloadingScenario,
    locations: Sequence[int],
    *,
    normalization: NormalizationConstants,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
    ratio_caps: Mapping[str, float] | None = None,
) -> PlanEvaluation:
    """Optimize endpoint ratios for fixed locations, not locations themselves.

    Compare each task at 0 and its cap (1 by default). Reservations and load
    depend only on locations; ties choose 0 and retain the reservation.
    """

    locations = validate_locations(scenario, locations)
    ratio_caps = validate_ratio_caps(scenario, ratio_caps)
    if not isinstance(normalization, NormalizationConstants):
        raise TypeError("normalization must be NormalizationConstants")
    if objective_config is None:
        objective_config = ObjectiveConfig()
    elif not isinstance(objective_config, ObjectiveConfig):
        raise TypeError("objective_config must be an ObjectiveConfig")
    if load_config is not None and not isinstance(load_config, LoadBalanceConfig):
        raise TypeError("load_config must be a LoadBalanceConfig")
    links = {(link.task_id, link.server_id): link for link in scenario.links}
    decisions = []
    for task, gene in zip(scenario.tasks, locations, strict=True):
        if gene == 0:
            decisions.append(OffloadingDecision(task.task.task_id, 0.0))
            continue
        cap = 1.0 if ratio_caps is None else ratio_caps[task.task.task_id]
        server = scenario.servers[gene - 1]
        risk = calculate_security_risk(task.security_level, scenario.security_threshold)
        endpoint_values = []
        for ratio in (0.0, cap):
            latency = calculate_task_latency(
                task.task,
                offloading_ratio=ratio,
                local_cpu_cycles_per_second=task.local_cpu_cycles_per_second,
                edge_cpu_cycles_per_second=server.allocated_cpu_cycles_per_second,
                transmission_rate_bits_per_second=links[
                    (task.task.task_id, server.server.server_id)
                ].rate_bits_per_second,
            )
            endpoint_values.append(
                calculate_objective(
                    latency.total_seconds,
                    risk * ratio,
                    0.0,
                    normalization=normalization,
                    config=objective_config,
                ).value
            )
        ratio = cap if endpoint_values[1] < endpoint_values[0] else 0.0
        decisions.append(
            OffloadingDecision(task.task.task_id, ratio, server.server.server_id)
        )
    return evaluate_plan(
        scenario,
        decisions,
        normalization=normalization,
        objective_config=objective_config,
        load_config=load_config,
        ratio_caps=ratio_caps,
    )
