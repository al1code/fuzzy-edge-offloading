import pytest

from src.config import FuzzySecurityConfig
from src.fuzzy_security import (
    SecurityPerspectives,
    aggregate_expert_assessments,
    assess_security,
    calculate_offloading_risk,
    calculate_security_risk,
)
from src.models import TriangularFuzzyNumber


@pytest.fixture
def expert_assessments() -> tuple[SecurityPerspectives, SecurityPerspectives]:
    return (
        SecurityPerspectives(
            task_data=TriangularFuzzyNumber(0.1, 0.2, 0.5),
            task_type=TriangularFuzzyNumber(0.2, 0.4, 0.8),
            terminal_lifecycle=TriangularFuzzyNumber(0.6, 0.7, 0.9),
        ),
        SecurityPerspectives(
            task_data=TriangularFuzzyNumber(0.4, 0.6, 0.9),
            task_type=TriangularFuzzyNumber(0.3, 0.5, 0.7),
            terminal_lifecycle=TriangularFuzzyNumber(0.1, 0.2, 0.3),
        ),
    )


def crisp_perspectives(value: float) -> SecurityPerspectives:
    number = TriangularFuzzyNumber(value, value, value)
    return SecurityPerspectives(number, number, number)


def test_expert_aggregation_matches_hand_calculated_components(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    result = aggregate_expert_assessments(expert_assessments, (0.25, 0.75))

    assert (result.task_data.low, result.task_data.modal, result.task_data.high) == (
        pytest.approx((0.325, 0.5, 0.8))
    )
    assert (result.task_type.low, result.task_type.modal, result.task_type.high) == (
        pytest.approx((0.275, 0.475, 0.725))
    )
    lifecycle = result.terminal_lifecycle
    assert (lifecycle.low, lifecycle.modal, lifecycle.high) == pytest.approx(
        (0.225, 0.325, 0.45)
    )


def test_assessment_pipeline_matches_independent_hand_calculation(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    result = assess_security(
        expert_assessments,
        expert_weights=(0.25, 0.75),
        security_threshold=0.6,
        config=FuzzySecurityConfig(0.5, 0.3, 0.2),
    )

    assert result.task_data_score == pytest.approx(25 / 48)
    assert result.task_type_score == pytest.approx(29 / 60)
    assert result.terminal_lifecycle_score == pytest.approx(79 / 240)
    assert result.security_level == pytest.approx(0.47125)
    # Risk constants were checked independently with 50-digit Decimal arithmetic.
    assert result.security_risk == pytest.approx(
        0.12080626349280486, rel=1e-12, abs=1e-15
    )
    assert calculate_offloading_risk(result.security_risk, 0.4, 1) == pytest.approx(
        0.048322505397121946, rel=1e-12, abs=1e-15
    )


def test_assessment_defaults_to_equal_perspective_weights() -> None:
    assessment = SecurityPerspectives(
        TriangularFuzzyNumber(0.1, 0.1, 0.1),
        TriangularFuzzyNumber(0.4, 0.4, 0.4),
        TriangularFuzzyNumber(0.7, 0.7, 0.7),
    )
    result = assess_security(
        (assessment,), expert_weights=(1.0,), security_threshold=0.3
    )

    assert result.security_level == pytest.approx(0.4)
    assert result.security_risk == 0.0


def test_zero_perspective_weights_select_one_score(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    result = assess_security(
        expert_assessments,
        expert_weights=(0.25, 0.75),
        security_threshold=0.6,
        config=FuzzySecurityConfig(0.0, 1.0, 0.0),
    )

    assert result.security_level == result.task_type_score


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_degenerate_triangles_preserve_scale_endpoints(value: float) -> None:
    result = assess_security(
        (crisp_perspectives(value),),
        expert_weights=(1.0,),
        security_threshold=0.5,
    )

    assert result.security_level == value


def test_weight_roundoff_does_not_push_endpoint_score_out_of_range() -> None:
    result = assess_security(
        (crisp_perspectives(1.0), crisp_perspectives(1.0)),
        expert_weights=(0.5, 0.5000000005),
        security_threshold=1.0,
        config=FuzzySecurityConfig(0.5, 0.5000000005, 0.0),
    )

    assert result.security_level == 1.0
    assert result.security_risk == 0.0


def test_zero_weight_expert_does_not_influence_result(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    result = aggregate_expert_assessments(expert_assessments, (1.0, 0.0))

    assert result == expert_assessments[0]


def test_single_expert_preserves_assessment(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    result = aggregate_expert_assessments((expert_assessments[0],), (1.0,))

    assert result == expert_assessments[0]


def test_joint_expert_and_weight_permutation_preserves_result(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
) -> None:
    first = aggregate_expert_assessments(expert_assessments, (0.25, 0.75))
    second = aggregate_expert_assessments(expert_assessments[::-1], (0.75, 0.25))

    assert first == second


@pytest.mark.parametrize(
    ("security_level", "threshold", "expected"),
    [
        (0.2, 0.7, 0.3934693402873666),
        (0.0, 1.0, 0.6321205588285577),
        (0.5, 0.5, 0.0),
        (0.7, 0.5, 0.0),
        (0.0, 0.0, 0.0),
        (1.0, 1.0, 0.0),
    ],
)
def test_security_risk_follows_equation_not_reversed_prose(
    security_level: float, threshold: float, expected: float
) -> None:
    assert calculate_security_risk(security_level, threshold) == pytest.approx(expected)


def test_security_risk_preserves_very_small_positive_shortfalls() -> None:
    assert calculate_security_risk(0.0, 1e-14) == pytest.approx(
        1e-14, rel=1e-12, abs=0.0
    )


def test_higher_security_levels_reduce_risk() -> None:
    risks = [calculate_security_risk(level, 0.8) for level in (0.1, 0.4, 0.7, 0.8)]

    assert risks[0] > risks[1] > risks[2] > risks[3] == 0.0


@pytest.mark.parametrize(
    ("ratio", "assignment", "expected"),
    [(0.0, 1, 0.0), (1.0, 1, 0.4), (0.25, 1, 0.1), (1.0, 0, 0.0)],
)
def test_offloading_risk_handles_local_partial_and_full_execution(
    ratio: float, assignment: int, expected: float
) -> None:
    assert calculate_offloading_risk(0.4, ratio, assignment) == pytest.approx(expected)


@pytest.mark.parametrize("assignment", [-1, 2])
def test_offloading_risk_rejects_non_binary_assignments(assignment: int) -> None:
    with pytest.raises(ValueError, match="server_assignment"):
        calculate_offloading_risk(0.4, 0.5, assignment)


@pytest.mark.parametrize("assignment", [0.5, True])
def test_offloading_risk_requires_integer_assignments(assignment: object) -> None:
    with pytest.raises(TypeError, match="server_assignment"):
        calculate_offloading_risk(0.4, 0.5, assignment)


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), float("inf")])
def test_risk_functions_reject_invalid_scores_thresholds_and_ratios(
    value: float,
) -> None:
    with pytest.raises(ValueError, match="security_level"):
        calculate_security_risk(value, 0.5)
    with pytest.raises(ValueError, match="security_threshold"):
        calculate_security_risk(0.5, value)
    with pytest.raises(ValueError, match="security_risk"):
        calculate_offloading_risk(value, 0.5, 0)
    with pytest.raises(ValueError, match="offloading_ratio"):
        calculate_offloading_risk(0.4, value, 0)


@pytest.mark.parametrize(
    "weights", [(), (1.0,), (0.4, 0.4), (-0.1, 1.1), (float("nan"), 1.0)]
)
def test_aggregation_rejects_invalid_expert_weights(
    expert_assessments: tuple[SecurityPerspectives, SecurityPerspectives],
    weights: tuple[float, ...],
) -> None:
    with pytest.raises(ValueError):
        aggregate_expert_assessments(expert_assessments, weights)


def test_aggregation_rejects_empty_assessments() -> None:
    with pytest.raises(ValueError, match="at least one"):
        aggregate_expert_assessments((), ())


def test_aggregation_rejects_incorrect_assessment_objects() -> None:
    with pytest.raises(TypeError, match="SecurityPerspectives"):
        aggregate_expert_assessments((None,), (1.0,))


@pytest.mark.parametrize("field_name", ["task_data", "task_type", "terminal_lifecycle"])
@pytest.mark.parametrize(
    "number",
    [TriangularFuzzyNumber(-0.1, 0.2, 0.9), TriangularFuzzyNumber(0.1, 0.2, 1.1)],
)
def test_security_perspectives_reject_triangles_outside_unit_interval(
    field_name: str, number: TriangularFuzzyNumber
) -> None:
    valid = TriangularFuzzyNumber(0.1, 0.2, 0.9)
    kwargs = {"task_data": valid, "task_type": valid, "terminal_lifecycle": valid}
    kwargs[field_name] = number

    with pytest.raises(ValueError, match=field_name):
        SecurityPerspectives(**kwargs)


def test_security_perspectives_require_triangular_fuzzy_numbers() -> None:
    valid = TriangularFuzzyNumber(0.1, 0.2, 0.9)

    with pytest.raises(TypeError, match="TriangularFuzzyNumber"):
        SecurityPerspectives(0.5, valid, valid)


def test_pipeline_rejects_invalid_threshold_before_assessment() -> None:
    with pytest.raises(ValueError, match="security_threshold"):
        assess_security((), expert_weights=(), security_threshold=float("nan"))
