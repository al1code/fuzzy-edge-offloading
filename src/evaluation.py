"""Common, optimizer-independent evaluation of complete offloading plans."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum

from src.config import LoadBalanceConfig
from src.fuzzy_security import calculate_offloading_risk, calculate_security_risk
from src.latency import LatencyBreakdown, calculate_task_latency
from src.load_balance import (
    ResourceVector,
    ServerLoad,
    calculate_load_variance,
    calculate_server_load,
)
from src.objective import (
    NormalizationConstants,
    ObjectiveBreakdown,
    ObjectiveConfig,
    calculate_objective,
)
from src.scenario import OffloadingDecision, OffloadingScenario
from src.validation import validate_non_negative


@dataclass(frozen=True, slots=True)
class TaskEvaluation:
    """One task's supplied decision and its latency/risk breakdown."""

    decision: OffloadingDecision
    latency: LatencyBreakdown
    security_risk: float
    offloading_risk: float


@dataclass(frozen=True, slots=True)
class ServerEvaluation:
    """One server's load; idle servers are retained with zero utilization."""

    server_id: str
    load: ServerLoad


@dataclass(frozen=True, slots=True)
class PlanEvaluation:
    """Traceable result ordered by the scenario, not by decision input order."""

    tasks: tuple[TaskEvaluation, ...]
    servers: tuple[ServerEvaluation, ...]
    total_latency_seconds: float
    total_security_risk: float
    normalization: NormalizationConstants
    objective: ObjectiveBreakdown


def derive_normalization(scenario: OffloadingScenario) -> NormalizationConstants:
    """Derive decision-independent upper bounds once for a shared scenario.

    Sum each task's largest local/full-edge endpoint latency. Eq. (16) is
    affine in x for a fixed server, so endpoints bound all partial choices.
    Ignoring joint capacity constraints can make this a conservative bound,
    not an attainable maximum. Risk scale is sum(mu_i), or 1 if every mu_i
    is zero. These are explicit project assumptions, not recovered author
    constants. Persist and reuse the returned scales across all methods.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    links = {(link.task_id, link.server_id): link for link in scenario.links}
    latency_bounds = []
    risks = []
    for profile in scenario.tasks:
        endpoints = [
            calculate_task_latency(
                profile.task,
                offloading_ratio=0.0,
                local_cpu_cycles_per_second=profile.local_cpu_cycles_per_second,
            ).total_seconds
        ]
        for server in scenario.servers:
            endpoints.append(
                calculate_task_latency(
                    profile.task,
                    offloading_ratio=1.0,
                    local_cpu_cycles_per_second=profile.local_cpu_cycles_per_second,
                    edge_cpu_cycles_per_second=server.allocated_cpu_cycles_per_second,
                    transmission_rate_bits_per_second=links[
                        (profile.task.task_id, server.server.server_id)
                    ].rate_bits_per_second,
                ).total_seconds
            )
        latency_bounds.append(max(endpoints))
        risks.append(
            calculate_security_risk(profile.security_level, scenario.security_threshold)
        )
    return NormalizationConstants(fsum(latency_bounds), fsum(risks) or 1.0)


def evaluate_plan(
    scenario: OffloadingScenario,
    decisions: Sequence[OffloadingDecision],
    *,
    normalization: NormalizationConstants,
    objective_config: ObjectiveConfig | None = None,
    load_config: LoadBalanceConfig | None = None,
) -> PlanEvaluation:
    """Evaluate one complete plan; reject invalid/infeasible assignments.

    Selected reservations depend on y, even when x=0. There is no queue,
    deadline constraint, ratio optimization, implicit resource reallocation,
    or global bandwidth constraint beyond the cited per-server equations.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    if not isinstance(normalization, NormalizationConstants):
        raise TypeError("normalization must be NormalizationConstants")
    decisions = tuple(decisions)
    if any(not isinstance(decision, OffloadingDecision) for decision in decisions):
        raise TypeError("decisions must contain OffloadingDecision objects")
    by_task = {decision.task_id: decision for decision in decisions}
    if len(by_task) != len(decisions):
        raise ValueError("duplicate task decision")
    if set(by_task) != {profile.task.task_id for profile in scenario.tasks}:
        raise ValueError("exactly one decision for each scenario task is required")
    servers = {profile.server.server_id: profile for profile in scenario.servers}
    links = {(link.task_id, link.server_id): link for link in scenario.links}
    allocations: dict[str, list[ResourceVector]] = {
        server_id: [] for server_id in servers
    }
    task_results = []
    for profile in scenario.tasks:
        decision = by_task[profile.task.task_id]
        edge_cpu = 0.0
        rate = 0.0
        if decision.server_id is not None:
            if decision.server_id not in servers:
                raise ValueError(f"unknown selected server: {decision.server_id}")
            edge_cpu = servers[decision.server_id].allocated_cpu_cycles_per_second
            rate = links[(decision.task_id, decision.server_id)].rate_bits_per_second
            allocations[decision.server_id].append(
                ResourceVector(edge_cpu, profile.bandwidth_hz, profile.memory_mb)
            )
        latency = calculate_task_latency(
            profile.task,
            offloading_ratio=decision.offloading_ratio,
            local_cpu_cycles_per_second=profile.local_cpu_cycles_per_second,
            edge_cpu_cycles_per_second=edge_cpu,
            transmission_rate_bits_per_second=rate,
        )
        risk = calculate_security_risk(
            profile.security_level, scenario.security_threshold
        )
        task_results.append(
            TaskEvaluation(
                decision,
                latency,
                risk,
                calculate_offloading_risk(
                    risk, decision.offloading_ratio, int(decision.server_id is not None)
                ),
            )
        )
    server_results = []
    for server_id, profile in servers.items():
        capacity = ResourceVector(
            profile.server.cpu_capacity_cycles_per_second,
            scenario.bandwidth_capacity_hz,
            profile.server.memory_capacity_mb,
        )
        try:
            load = calculate_server_load(
                capacity, allocations[server_id], config=load_config
            )
        except ValueError as exc:
            raise ValueError(f"server {server_id}: {exc}") from exc
        server_results.append(ServerEvaluation(server_id, load))
    total_latency = fsum(task.latency.total_seconds for task in task_results)
    total_risk = fsum(task.offloading_risk for task in task_results)
    validate_non_negative(total_latency, "total latency")
    validate_non_negative(total_risk, "total risk")
    variance = calculate_load_variance(
        tuple(server.load.weighted_load for server in server_results)
    )
    objective = calculate_objective(
        total_latency,
        total_risk,
        variance,
        normalization=normalization,
        config=objective_config,
    )
    return PlanEvaluation(
        tuple(task_results),
        tuple(server_results),
        total_latency,
        total_risk,
        normalization,
        objective,
    )
