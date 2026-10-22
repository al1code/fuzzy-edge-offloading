"""Proposed Type-1 Mamdani policy: security and mean TFN width -> offloading cap.

Uses min-AND, max aggregation, and centroid defuzzification.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import fsum
from numbers import Integral

from src.fuzzy_security import SecurityPerspectives, aggregate_expert_assessments
from src.validation import validate_integer, validate_unit_interval

SECURITY_LABELS = ("low", "medium", "high")
UNCERTAINTY_LABELS = ("low", "medium", "high")
OUTPUT_LABELS = ("restricted", "low", "medium", "high")

# Triples are (left, peak, right).  Endpoint triangles act as shoulders.
INPUT_MEMBERSHIP_TRIANGLES: dict[str, tuple[float, float, float]] = {
    "low": (0.0, 0.0, 0.5),
    "medium": (0.25, 0.5, 0.75),
    "high": (0.5, 1.0, 1.0),
}
OUTPUT_MEMBERSHIP_TRIANGLES: dict[str, tuple[float, float, float]] = {
    "restricted": (0.0, 0.0, 0.25),
    "low": (0.10, 0.30, 0.50),
    "medium": (0.35, 0.55, 0.75),
    "high": (0.60, 1.0, 1.0),
}

# Rule keys: (security, assessment width).
RULE_BASE: dict[tuple[str, str], str] = {
    ("low", "low"): "restricted",
    ("low", "medium"): "restricted",
    ("low", "high"): "restricted",
    ("medium", "low"): "medium",
    ("medium", "medium"): "low",
    ("medium", "high"): "restricted",
    ("high", "low"): "high",
    ("high", "medium"): "medium",
    ("high", "high"): "low",
}


@dataclass(frozen=True, slots=True)
class MembershipDegree:
    """One linguistic label and its fuzzified degree."""

    label: str
    value: float


@dataclass(frozen=True, slots=True)
class RuleActivation:
    """Trace of one Mamdani rule after min-AND antecedent evaluation."""

    security_label: str
    uncertainty_label: str
    output_label: str
    strength: float


@dataclass(frozen=True, slots=True)
class MamdaniOffloadingDecision:
    """Traceable result of one proposed-policy decision."""

    security_level: float
    assessment_uncertainty: float
    security_memberships: tuple[MembershipDegree, ...]
    uncertainty_memberships: tuple[MembershipDegree, ...]
    output_memberships: tuple[MembershipDegree, ...]
    rule_activations: tuple[RuleActivation, ...]
    allowed_offloading_ratio: float

    @property
    def active_rules(self) -> tuple[RuleActivation, ...]:
        """Return the rules which influence the aggregated output."""

        return tuple(rule for rule in self.rule_activations if rule.strength > 0.0)


def triangular_membership(
    value: float, left: float, peak: float, right: float
) -> float:
    """Return membership in a triangular or shoulder-triangular set."""

    validate_unit_interval(value, "value")
    for name, coordinate in (("left", left), ("peak", peak), ("right", right)):
        validate_unit_interval(coordinate, name)
    if not left <= peak <= right:
        raise ValueError("membership triangle must satisfy left <= peak <= right")
    if value == peak:
        return 1.0
    if value <= left or value >= right:
        return 0.0
    if value < peak:
        return (value - left) / (peak - left)
    return (right - value) / (right - peak)


def calculate_aggregate_assessment_uncertainty(
    aggregated_perspectives: SecurityPerspectives,
) -> float:
    """Return mean aggregated TFN width in [0, 1].

    Measures assessment width, not attack probability or expert disagreement.
    """

    if not isinstance(aggregated_perspectives, SecurityPerspectives):
        raise TypeError("aggregated_perspectives must be a SecurityPerspectives")
    widths = (
        aggregated_perspectives.task_data.high - aggregated_perspectives.task_data.low,
        aggregated_perspectives.task_type.high - aggregated_perspectives.task_type.low,
        aggregated_perspectives.terminal_lifecycle.high
        - aggregated_perspectives.terminal_lifecycle.low,
    )
    return min(1.0, max(0.0, fsum(widths) / len(widths)))


def calculate_assessment_uncertainty(
    assessments: Sequence[SecurityPerspectives],
    expert_weights: Sequence[float],
) -> float:
    """Aggregate expert input first, then return its mean triangular width."""

    aggregated = aggregate_expert_assessments(assessments, expert_weights)
    return calculate_aggregate_assessment_uncertainty(aggregated)


def _memberships(
    value: float,
    triangles: dict[str, tuple[float, float, float]],
    labels: tuple[str, ...],
) -> tuple[MembershipDegree, ...]:
    return tuple(
        MembershipDegree(label, triangular_membership(value, *triangles[label]))
        for label in labels
    )


def _validate_centroid_resolution(centroid_resolution: int) -> None:
    if isinstance(centroid_resolution, bool) or not isinstance(
        centroid_resolution, Integral
    ):
        raise TypeError("centroid_resolution must be an integer")
    validate_integer(centroid_resolution, "centroid_resolution", minimum=3)


def _centroid(output_strengths: dict[str, float], *, centroid_resolution: int) -> float:
    """Numerically defuzzify a max-aggregated output on a fixed [0, 1] grid."""

    _validate_centroid_resolution(centroid_resolution)
    numerator = 0.0
    denominator = 0.0
    for index in range(centroid_resolution):
        value = index / (centroid_resolution - 1)
        degree = max(
            min(
                output_strengths[label],
                triangular_membership(value, *OUTPUT_MEMBERSHIP_TRIANGLES[label]),
            )
            for label in OUTPUT_LABELS
        )
        numerator += value * degree
        denominator += degree
    if denominator == 0.0:
        raise RuntimeError("Mamdani aggregation produced an empty output set")
    return numerator / denominator


def evaluate_uncertainty_aware_offloading(
    security_level: float,
    assessment_uncertainty: float,
    *,
    centroid_resolution: int = 1001,
) -> MamdaniOffloadingDecision:
    """Apply RULE_BASE and return the cap with memberships and rule activations."""

    validate_unit_interval(security_level, "security_level")
    validate_unit_interval(assessment_uncertainty, "assessment_uncertainty")
    _validate_centroid_resolution(centroid_resolution)

    security_memberships = _memberships(
        security_level, INPUT_MEMBERSHIP_TRIANGLES, SECURITY_LABELS
    )
    uncertainty_memberships = _memberships(
        assessment_uncertainty, INPUT_MEMBERSHIP_TRIANGLES, UNCERTAINTY_LABELS
    )
    security_degrees = {item.label: item.value for item in security_memberships}
    uncertainty_degrees = {item.label: item.value for item in uncertainty_memberships}
    rules = tuple(
        RuleActivation(
            security_label=security_label,
            uncertainty_label=uncertainty_label,
            output_label=RULE_BASE[(security_label, uncertainty_label)],
            strength=min(
                security_degrees[security_label],
                uncertainty_degrees[uncertainty_label],
            ),
        )
        for security_label in SECURITY_LABELS
        for uncertainty_label in UNCERTAINTY_LABELS
    )
    output_strengths = {
        label: max(
            (rule.strength for rule in rules if rule.output_label == label),
            default=0.0,
        )
        for label in OUTPUT_LABELS
    }
    output_memberships = tuple(
        MembershipDegree(label, output_strengths[label]) for label in OUTPUT_LABELS
    )
    return MamdaniOffloadingDecision(
        security_level=float(security_level),
        assessment_uncertainty=float(assessment_uncertainty),
        security_memberships=security_memberships,
        uncertainty_memberships=uncertainty_memberships,
        output_memberships=output_memberships,
        rule_activations=rules,
        allowed_offloading_ratio=_centroid(
            output_strengths, centroid_resolution=centroid_resolution
        ),
    )


def derive_task_policy_decisions(
    security_levels: Sequence[float],
    assessments_by_task: Sequence[Sequence[SecurityPerspectives]],
    expert_weights: Sequence[float],
    *,
    centroid_resolution: int = 1001,
) -> tuple[MamdaniOffloadingDecision, ...]:
    """Return one policy decision per task without coupling to dataset storage."""

    security_levels = tuple(security_levels)
    assessments_by_task = tuple(tuple(values) for values in assessments_by_task)
    if len(security_levels) != len(assessments_by_task):
        raise ValueError(
            "security_levels and assessments_by_task must have equal length"
        )
    return tuple(
        evaluate_uncertainty_aware_offloading(
            security_level,
            calculate_assessment_uncertainty(assessments, expert_weights),
            centroid_resolution=centroid_resolution,
        )
        for security_level, assessments in zip(
            security_levels, assessments_by_task, strict=True
        )
    )


def derive_task_ratio_caps(
    security_levels: Sequence[float],
    assessments_by_task: Sequence[Sequence[SecurityPerspectives]],
    expert_weights: Sequence[float],
    *,
    centroid_resolution: int = 1001,
) -> tuple[float, ...]:
    """Return the policy's allowed ratio cap for each task."""

    return tuple(
        decision.allowed_offloading_ratio
        for decision in derive_task_policy_decisions(
            security_levels,
            assessments_by_task,
            expert_weights,
            centroid_resolution=centroid_resolution,
        )
    )
