import pytest

from src.fuzzy_controller import (
    RULE_BASE,
    calculate_aggregate_assessment_uncertainty,
    calculate_assessment_uncertainty,
    derive_task_policy_decisions,
    derive_task_ratio_caps,
    evaluate_uncertainty_aware_offloading,
    triangular_membership,
)
from src.fuzzy_security import SecurityPerspectives
from src.models import TriangularFuzzyNumber


def _perspectives() -> SecurityPerspectives:
    return SecurityPerspectives(
        task_data=TriangularFuzzyNumber(0.1, 0.2, 0.4),
        task_type=TriangularFuzzyNumber(0.1, 0.4, 0.7),
        terminal_lifecycle=TriangularFuzzyNumber(0.0, 0.5, 0.9),
    )


def test_uncertainty_is_mean_width_of_aggregate_triangles() -> None:
    assert calculate_aggregate_assessment_uncertainty(_perspectives()) == pytest.approx(
        0.6
    )


def test_uncertainty_aggregates_experts_before_measuring_width() -> None:
    first = _perspectives()
    crisp = TriangularFuzzyNumber(0.6, 0.6, 0.6)
    second = SecurityPerspectives(crisp, crisp, crisp)

    assert calculate_assessment_uncertainty((first, second), (0.5, 0.5)) == (
        pytest.approx(0.3)
    )


def test_high_security_low_uncertainty_allows_more_offloading() -> None:
    confident = evaluate_uncertainty_aware_offloading(0.9, 0.1)
    uncertain = evaluate_uncertainty_aware_offloading(0.9, 0.9)

    assert confident.allowed_offloading_ratio > uncertain.allowed_offloading_ratio
    assert confident.allowed_offloading_ratio > 0.7
    assert uncertain.allowed_offloading_ratio < 0.4


def test_low_security_is_restricted_at_every_uncertainty_level() -> None:
    caps = [
        evaluate_uncertainty_aware_offloading(0.1, uncertainty).allowed_offloading_ratio
        for uncertainty in (0.1, 0.5, 0.9)
    ]

    assert max(caps) < 0.15


def test_cap_stays_bounded_on_input_grid() -> None:
    values = [i / 10 for i in range(11)]
    caps = [
        evaluate_uncertainty_aware_offloading(
            security, uncertainty
        ).allowed_offloading_ratio
        for security in values
        for uncertainty in values
    ]
    assert all(0.0 <= cap <= 1.0 for cap in caps)


def test_high_uncertainty_reduces_cap_for_high_security_anchor() -> None:
    confident = evaluate_uncertainty_aware_offloading(0.9, 0.1)
    uncertain = evaluate_uncertainty_aware_offloading(0.9, 0.9)
    assert confident.allowed_offloading_ratio > uncertain.allowed_offloading_ratio


def test_centroid_resolution_is_numerically_stable() -> None:
    decisions = [
        evaluate_uncertainty_aware_offloading(
            security, uncertainty, centroid_resolution=resolution
        )
        for resolution in (101, 1001, 5001)
        for security, uncertainty in ((0.2, 0.7), (0.8, 0.2))
    ]
    for offset in (0, 1):
        values = [
            decisions[offset + 2 * resolution_index].allowed_offloading_ratio
            for resolution_index in range(3)
        ]
        assert max(values) - min(values) < 0.003


def test_trace_shows_the_expected_corner_rule() -> None:
    decision = evaluate_uncertainty_aware_offloading(1.0, 0.0)

    assert len(decision.rule_activations) == 9
    assert len(decision.active_rules) == 1
    rule = decision.active_rules[0]
    assert (rule.security_label, rule.uncertainty_label, rule.output_label) == (
        "high",
        "low",
        "high",
    )
    assert rule.strength == 1.0
    assert RULE_BASE[("high", "low")] == "high"


def test_ratio_caps_are_derived_without_dataset_coupling() -> None:
    first = _perspectives()
    caps = derive_task_ratio_caps((0.9, 0.1), ((first,), (first,)), (1.0,))
    decisions = derive_task_policy_decisions((0.9, 0.1), ((first,), (first,)), (1.0,))

    assert len(caps) == 2
    assert caps == pytest.approx(
        tuple(decision.allowed_offloading_ratio for decision in decisions)
    )
    assert caps[0] > caps[1]


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.0, 1.0), (0.25, 0.5), (0.5, 0.0), (1.0, 0.0)],
)
def test_left_shoulder_triangle(value: float, expected: float) -> None:
    assert triangular_membership(value, 0.0, 0.0, 0.5) == pytest.approx(expected)


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_controller_rejects_invalid_inputs(value: float) -> None:
    with pytest.raises(ValueError):
        evaluate_uncertainty_aware_offloading(value, 0.5)
    with pytest.raises(ValueError):
        evaluate_uncertainty_aware_offloading(0.5, value)


@pytest.mark.parametrize("resolution", [2, 3.5, True])
def test_controller_rejects_invalid_centroid_resolution(resolution: object) -> None:
    with pytest.raises((TypeError, ValueError), match="centroid_resolution"):
        evaluate_uncertainty_aware_offloading(
            0.5,
            0.5,
            centroid_resolution=resolution,  # type: ignore[arg-type]
        )
