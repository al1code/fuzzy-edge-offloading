"""Fuzzy security assessment from Jin et al., Scientific Reports (2024).

The pipeline implements Eqs. (11)-(15). It is weighted triangular-fuzzy-number
assessment, not a Mamdani/Sugeno rule-based inference system. See
``references/fuzzy_security.md`` for sources and reproduction decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import expm1, fsum

from src.config import FuzzySecurityConfig
from src.models import TriangularFuzzyNumber
from src.validation import (
    validate_integer,
    validate_unit_interval,
    validate_weights,
)


@dataclass(frozen=True, slots=True)
class SecurityPerspectives:
    """One expert's or an aggregate's three security assessments in [0, 1]."""

    task_data: TriangularFuzzyNumber
    task_type: TriangularFuzzyNumber
    terminal_lifecycle: TriangularFuzzyNumber

    def __post_init__(self) -> None:
        for name in ("task_data", "task_type", "terminal_lifecycle"):
            number = getattr(self, name)
            if not isinstance(number, TriangularFuzzyNumber):
                raise TypeError(f"{name} must be a TriangularFuzzyNumber")
            validate_unit_interval(number.low, f"{name}.low")
            validate_unit_interval(number.high, f"{name}.high")


@dataclass(frozen=True, slots=True)
class FuzzySecurityResult:
    """Traceable result for one task, retaining fuzzy and crisp intermediates."""

    aggregated_perspectives: SecurityPerspectives
    task_data_score: float
    task_type_score: float
    terminal_lifecycle_score: float
    security_level: float
    security_risk: float


def _weighted_fuzzy_number(
    numbers: Sequence[TriangularFuzzyNumber], weights: Sequence[float]
) -> TriangularFuzzyNumber:
    # Accepted weights already sum to one; division removes tolerance roundoff.
    total_weight = fsum(weights)
    return TriangularFuzzyNumber(
        low=fsum(w * n.low for w, n in zip(weights, numbers, strict=True))
        / total_weight,
        modal=fsum(w * n.modal for w, n in zip(weights, numbers, strict=True))
        / total_weight,
        high=fsum(w * n.high for w, n in zip(weights, numbers, strict=True))
        / total_weight,
    )


def aggregate_expert_assessments(
    assessments: Sequence[SecurityPerspectives],
    expert_weights: Sequence[float],
) -> SecurityPerspectives:
    """Combine L expert assessments component-wise using Eq. (11).

    Weights must align with the assessment order, be non-negative, and sum
    to one. Empty input and mismatched lengths are rejected. Expert weights
    are explicit inputs because the paper does not supply their values.
    """

    assessments = tuple(assessments)
    expert_weights = tuple(expert_weights)
    if not assessments:
        raise ValueError("at least one expert assessment is required")
    if len(assessments) != len(expert_weights):
        raise ValueError("each expert assessment must have exactly one weight")
    if any(not isinstance(a, SecurityPerspectives) for a in assessments):
        raise TypeError("assessments must contain SecurityPerspectives")
    validate_weights(expert_weights, "expert weights")

    return SecurityPerspectives(
        task_data=_weighted_fuzzy_number(
            tuple(a.task_data for a in assessments), expert_weights
        ),
        task_type=_weighted_fuzzy_number(
            tuple(a.task_type for a in assessments), expert_weights
        ),
        terminal_lifecycle=_weighted_fuzzy_number(
            tuple(a.terminal_lifecycle for a in assessments), expert_weights
        ),
    )


def calculate_security_risk(security_level: float, security_threshold: float) -> float:
    """Return mu_i from Eq. (14), positive only when S_i < theta.

    The prose following Eq. (14) reverses this condition. This reproduction
    follows the equation. ``expm1`` preserves precision for small shortfalls.
    """

    validate_unit_interval(security_level, "security_level")
    validate_unit_interval(security_threshold, "security_threshold")
    if security_level >= security_threshold:
        return 0.0
    return -expm1(-(security_threshold - security_level))


def calculate_offloading_risk(
    security_risk: float,
    offloading_ratio: float,
    server_assignment: int,
) -> float:
    """Return xi_ij = x_i * y_ij * mu_i from Eq. (15).

    ``server_assignment`` is the binary matrix entry y_ij, not a server ID.
    Local-only execution or an unselected server contributes zero risk.
    """

    validate_unit_interval(security_risk, "security_risk")
    validate_unit_interval(offloading_ratio, "offloading_ratio")
    validate_integer(server_assignment, "server_assignment", maximum=1)
    return offloading_ratio * server_assignment * security_risk


def assess_security(
    assessments: Sequence[SecurityPerspectives],
    *,
    expert_weights: Sequence[float],
    security_threshold: float,
    config: FuzzySecurityConfig | None = None,
) -> FuzzySecurityResult:
    """Evaluate one task through Eqs. (11)-(14), preserving each stage.

    Perspective weights default to Table 4's equal eta_k. The security
    threshold must be supplied explicitly; the paper reports a range, not
    a single default. This function does not draw random values or alter RNGs.
    """

    validate_unit_interval(security_threshold, "security_threshold")
    if config is None:
        config = FuzzySecurityConfig()
    aggregated = aggregate_expert_assessments(assessments, expert_weights)
    scores = (
        aggregated.task_data.paper_transformation_value(),
        aggregated.task_type.paper_transformation_value(),
        aggregated.terminal_lifecycle.paper_transformation_value(),
    )
    weights = (
        config.task_data_weight,
        config.task_type_weight,
        config.terminal_lifecycle_weight,
    )
    security_level = fsum(w * s for w, s in zip(weights, scores, strict=True))
    security_level /= fsum(weights)
    return FuzzySecurityResult(
        aggregated_perspectives=aggregated,
        task_data_score=scores[0],
        task_type_score=scores[1],
        terminal_lifecycle_score=scores[2],
        security_level=security_level,
        security_risk=calculate_security_risk(security_level, security_threshold),
    )
