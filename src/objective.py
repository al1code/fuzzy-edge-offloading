"""Fixed normalization and the weighted minimization objective, Eqs. (17)-(19)."""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum

from src.validation import validate_non_negative, validate_positive, validate_weights


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    """Delta weights; equal defaults follow Table 4, not a fitted preference."""

    latency_weight: float = 1.0 / 3.0
    risk_weight: float = 1.0 / 3.0
    load_weight: float = 1.0 / 3.0

    def __post_init__(self) -> None:
        validate_weights(
            (self.latency_weight, self.risk_weight, self.load_weight),
            "objective weights",
        )


@dataclass(frozen=True, slots=True)
class NormalizationConstants:
    """Positive reference scales, fixed across decisions and compared methods."""

    latency_seconds: float
    security_risk: float

    def __post_init__(self) -> None:
        validate_positive(self.latency_seconds, "latency normalizer")
        validate_positive(self.security_risk, "risk normalizer")


@dataclass(frozen=True, slots=True)
class ObjectiveBreakdown:
    """Normalized metrics and each weighted contribution to F."""

    normalized_latency: float
    normalized_risk: float
    load_variance: float
    latency_term: float
    risk_term: float
    load_term: float

    @property
    def value(self) -> float:
        """Smaller is better; this is F, not the reciprocal genetic fitness."""

        return fsum((self.latency_term, self.risk_term, self.load_term))


def calculate_objective(
    total_latency_seconds: float,
    total_security_risk: float,
    load_variance: float,
    *,
    normalization: NormalizationConstants,
    config: ObjectiveConfig | None = None,
) -> ObjectiveBreakdown:
    """Apply Eq. (19) without clipping metrics or changing reference scales.

    Explicit scales can yield normalized metrics above one. Such a result
    is retained, not silently clipped. Load variance is not normalized again.
    """

    validate_non_negative(total_latency_seconds, "total latency")
    validate_non_negative(total_security_risk, "total risk")
    validate_non_negative(load_variance, "load variance")
    if not isinstance(normalization, NormalizationConstants):
        raise TypeError("normalization must be NormalizationConstants")
    if config is None:
        config = ObjectiveConfig()
    elif not isinstance(config, ObjectiveConfig):
        raise TypeError("config must be an ObjectiveConfig")
    normalized_latency = total_latency_seconds / normalization.latency_seconds
    normalized_risk = total_security_risk / normalization.security_risk
    validate_non_negative(normalized_latency, "normalized latency")
    validate_non_negative(normalized_risk, "normalized risk")
    weights = (config.latency_weight, config.risk_weight, config.load_weight)
    total_weight = fsum(weights)
    terms = tuple(
        w * metric / total_weight
        for w, metric in zip(
            weights, (normalized_latency, normalized_risk, load_variance), strict=True
        )
    )
    validate_non_negative(fsum(terms), "objective value")
    return ObjectiveBreakdown(
        normalized_latency, normalized_risk, load_variance, *terms
    )
