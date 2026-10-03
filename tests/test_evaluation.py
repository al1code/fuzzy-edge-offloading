from dataclasses import replace

import pytest

from src.config import LoadBalanceConfig
from src.evaluation import derive_normalization, evaluate_plan
from src.objective import NormalizationConstants, ObjectiveConfig
from src.scenario import OffloadingDecision
from tests.scenario_helpers import make_scenario

RISK = 0.12080626349280486


def test_local_edge_and_partial_plans_match_independent_arithmetic() -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)
    assert normalization.latency_seconds == pytest.approx(3.6)
    assert normalization.security_risk == pytest.approx(2 * RISK)
    local = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 0.0), OffloadingDecision("t2", 0.0)),
        normalization=normalization,
    )
    edge = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s2")),
        normalization=normalization,
    )
    partial = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 0.4, "s1"), OffloadingDecision("t2", 0.6, "s2")),
        normalization=normalization,
    )
    assert local.total_latency_seconds == pytest.approx(3.6)
    assert local.total_security_risk == 0.0
    assert local.objective.value == pytest.approx(1 / 3)
    assert all(server.load.weighted_load == 0.0 for server in local.servers)
    assert edge.total_latency_seconds == pytest.approx(1.5)
    assert edge.total_security_risk == pytest.approx(2 * RISK)
    assert edge.objective.value == pytest.approx(17 / 36)
    assert partial.total_latency_seconds == pytest.approx(2.48)
    assert partial.total_security_risk == pytest.approx(RISK)
    assert partial.objective.normalized_latency == pytest.approx(31 / 45)
    assert partial.objective.normalized_risk == pytest.approx(0.5)
    assert partial.objective.load_variance == 0.0
    assert partial.objective.value == pytest.approx(107 / 270)
    assert partial.tasks[0].latency.local_seconds == pytest.approx(0.72)
    assert partial.tasks[0].latency.transmission_seconds == pytest.approx(0.08)
    assert partial.tasks[0].latency.edge_seconds == pytest.approx(0.12)
    assert partial.normalization is local.normalization is edge.normalization


def test_concentrating_work_keeps_latency_risk_but_increases_population_variance() -> (
    None
):
    scenario = make_scenario()
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 0.4, "s1"), OffloadingDecision("t2", 0.6, "s1")),
        normalization=derive_normalization(scenario),
    )
    assert result.total_latency_seconds == pytest.approx(2.48)
    assert result.total_security_risk == pytest.approx(RISK)
    assert result.servers[0].load.weighted_load == pytest.approx(2 / 3)
    assert result.servers[1].load.weighted_load == 0.0
    assert result.objective.load_variance == pytest.approx(1 / 9)
    assert result.objective.value == pytest.approx(13 / 30)


def test_selected_zero_ratio_retains_reservations_not_offloading_latency_or_risk() -> (
    None
):
    scenario = make_scenario()
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 0.0, "s1"), OffloadingDecision("t2", 0.0)),
        normalization=derive_normalization(scenario),
    )
    assert result.total_latency_seconds == pytest.approx(3.6)
    assert result.total_security_risk == 0.0
    assert result.tasks[0].latency.edge_seconds == 0.0
    assert result.servers[0].load.weighted_load == pytest.approx(1 / 3)
    assert result.objective.load_variance == pytest.approx(1 / 36)


def test_decision_order_does_not_change_results_or_task_associations() -> None:
    scenario = make_scenario()
    decisions = (
        OffloadingDecision("t1", 0.4, "s1"),
        OffloadingDecision("t2", 0.6, "s2"),
    )
    normalization = derive_normalization(scenario)
    assert evaluate_plan(
        scenario, decisions, normalization=normalization
    ) == evaluate_plan(scenario, list(reversed(decisions)), normalization=normalization)


@pytest.mark.parametrize(
    "decisions, message",
    [
        ((), "exactly one"),
        ((OffloadingDecision("t1", 0.0),), "exactly one"),
        (
            (OffloadingDecision("t1", 0.0), OffloadingDecision("unknown", 0.0)),
            "exactly one",
        ),
        ((OffloadingDecision("t1", 0.0), OffloadingDecision("t1", 0.0)), "duplicate"),
        (
            (OffloadingDecision("t1", 0.4, "unknown"), OffloadingDecision("t2", 0.0)),
            "unknown selected server",
        ),
    ],
)
def test_plan_requires_exactly_one_known_location_per_task(
    decisions: tuple[OffloadingDecision, ...], message: str
) -> None:
    scenario = make_scenario()
    with pytest.raises(ValueError, match=message):
        evaluate_plan(scenario, decisions, normalization=derive_normalization(scenario))


@pytest.mark.parametrize(
    "resource, value, name",
    [
        ("cpu_capacity_cycles_per_second", 7e9, "CPU"),
        ("memory_capacity_mb", 500.0, "memory"),
        ("bandwidth_capacity_hz", 9e6, "bandwidth"),
    ],
)
@pytest.mark.parametrize("ratio", [0.0, 0.01, 1.0])
def test_capacity_constraints_apply_to_selected_reservations_even_at_zero_ratio(
    resource: str, value: float, name: str, ratio: float
) -> None:
    scenario = make_scenario()
    if resource == "bandwidth_capacity_hz":
        scenario = replace(scenario, bandwidth_capacity_hz=value)
    else:
        first = replace(
            scenario.servers[0],
            server=replace(scenario.servers[0].server, **{resource: value}),
        )
        scenario = replace(scenario, servers=(first, scenario.servers[1]))
    with pytest.raises(
        ValueError, match=f"server s1: {name} allocation exceeds capacity"
    ):
        evaluate_plan(
            scenario,
            (
                OffloadingDecision("t1", ratio, "s1"),
                OffloadingDecision("t2", ratio, "s1"),
            ),
            normalization=derive_normalization(scenario),
        )


def test_no_extra_global_bandwidth_constraint_is_invented() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario, tasks=tuple(replace(t, bandwidth_hz=15e6) for t in scenario.tasks)
    )
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s2")),
        normalization=derive_normalization(scenario),
    )
    assert [s.load.bandwidth_utilization for s in result.servers] == [0.75, 0.75]


def test_zero_risk_scenario_uses_positive_shared_scale_and_finite_objective() -> None:
    scenario = replace(make_scenario(), security_threshold=0.0)
    normalization = derive_normalization(scenario)
    assert normalization.security_risk == 1.0
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s2")),
        normalization=normalization,
    )
    assert result.objective.normalized_risk == 0.0
    assert result.objective.value == pytest.approx(5 / 36)


def test_slow_links_are_included_in_the_scenario_bound_not_method_specific_scales() -> (
    None
):
    scenario = make_scenario()
    scenario = replace(
        scenario,
        links=tuple(replace(link, rate_bits_per_second=4e6) for link in scenario.links),
    )
    normalization = derive_normalization(scenario)
    assert normalization.latency_seconds == pytest.approx(6.9)
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s2")),
        normalization=normalization,
    )
    assert result.total_latency_seconds == pytest.approx(6.9)
    assert result.objective.normalized_latency == pytest.approx(1.0)


def test_single_server_is_included_and_has_zero_load_variance() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        servers=scenario.servers[:1],
        links=tuple(link for link in scenario.links if link.server_id == "s1"),
    )
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s1")),
        normalization=derive_normalization(scenario),
    )
    assert len(result.servers) == 1
    assert result.objective.load_variance == 0.0


@pytest.mark.parametrize("ratio", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_fixed_assignment_objective_is_affine_in_ratios(ratio: float) -> None:
    scenario = make_scenario()
    normalization = derive_normalization(scenario)

    def value(x: float) -> float:
        return evaluate_plan(
            scenario,
            (OffloadingDecision("t1", x, "s1"), OffloadingDecision("t2", x, "s1")),
            normalization=normalization,
        ).objective.value

    assert value(ratio) == pytest.approx((1 - ratio) * value(0.0) + ratio * value(1.0))


def test_supplied_weights_and_scales_are_used_without_hidden_recalculation() -> None:
    scenario = make_scenario()
    result = evaluate_plan(
        scenario,
        (OffloadingDecision("t1", 1.0, "s1"), OffloadingDecision("t2", 1.0, "s2")),
        normalization=NormalizationConstants(10.0, 1.0),
        objective_config=ObjectiveConfig(1.0, 0.0, 0.0),
        load_config=LoadBalanceConfig(1.0, 0.0, 0.0),
    )
    assert result.objective.value == pytest.approx(0.15)
    assert result.servers[0].load.weighted_load == 0.5


def test_evaluator_does_not_add_deadline_constraints_or_mutate_inputs() -> None:
    scenario = make_scenario()
    scenario = replace(
        scenario,
        tasks=tuple(
            replace(t, task=replace(t.task, deadline_seconds=0.01))
            for t in scenario.tasks
        ),
    )
    decisions = [OffloadingDecision("t1", 0.0), OffloadingDecision("t2", 0.0)]
    original = list(decisions)
    result = evaluate_plan(
        scenario, decisions, normalization=derive_normalization(scenario)
    )
    assert result.total_latency_seconds == pytest.approx(3.6)
    assert decisions == original
    assert scenario.tasks[0].task.deadline_seconds == 0.01


def test_evaluator_and_bound_reject_wrong_input_types() -> None:
    scenario = make_scenario()
    with pytest.raises(TypeError, match="OffloadingScenario"):
        derive_normalization(object())
    with pytest.raises(TypeError, match="OffloadingScenario"):
        evaluate_plan(object(), (), normalization=NormalizationConstants(1.0, 1.0))
    with pytest.raises(TypeError, match="normalization"):
        evaluate_plan(scenario, (), normalization=object())
    with pytest.raises(TypeError, match="OffloadingDecision"):
        evaluate_plan(
            scenario, (object(),), normalization=derive_normalization(scenario)
        )
    with pytest.raises(TypeError, match="LoadBalanceConfig"):
        evaluate_plan(
            scenario,
            (OffloadingDecision("t1", 0.0), OffloadingDecision("t2", 0.0)),
            normalization=derive_normalization(scenario),
            load_config=object(),
        )
