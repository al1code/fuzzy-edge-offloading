"""Shared numeric constraints for experiment inputs and domain models."""

from __future__ import annotations

from collections.abc import Sequence
from math import fsum, isclose, isfinite
from numbers import Integral, Real


def validate_integer(
    value: int,
    name: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> None:
    """Reject booleans, fractional counts, and integers outside the bounds."""

    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be at most {maximum}")


def validate_finite(value: float, name: str) -> None:
    """Require a finite real number before comparing or combining inputs."""

    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number")
    if not isfinite(value):
        raise ValueError(f"{name} must be a finite real number")


def validate_positive(value: float, name: str) -> None:
    """Require a finite resource quantity greater than zero."""

    validate_finite(value, name)
    if value <= 0.0:
        raise ValueError(f"{name} must be greater than zero")


def validate_non_negative(value: float, name: str) -> None:
    """Allow zero for unused resources, while rejecting invalid quantities."""

    validate_finite(value, name)
    if value < 0.0:
        raise ValueError(f"{name} must be non-negative")


def validate_unit_interval(value: float, name: str) -> None:
    """Require a finite score, threshold, or ratio in the closed unit interval."""

    validate_finite(value, name)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0")


def validate_weights(weights: Sequence[float], name: str) -> None:
    """Require non-negative weights summing to one within roundoff tolerance."""

    if not weights:
        raise ValueError(f"{name} must not be empty")
    for weight in weights:
        validate_unit_interval(weight, name)
    if not isclose(fsum(weights), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"{name} must sum to 1.0")
