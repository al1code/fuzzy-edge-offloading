"""Validation for optional task-specific offloading-ratio upper bounds."""

from __future__ import annotations

from collections.abc import Mapping

from src.scenario import OffloadingScenario
from src.validation import validate_unit_interval


def validate_ratio_caps(
    scenario: OffloadingScenario,
    ratio_caps: Mapping[str, float] | None,
) -> dict[str, float] | None:
    """Return immutable-style copied caps aligned with every scenario task.

    ``None`` keeps the reproduced paper baseline unconstrained.  A supplied
    mapping must cover every task exactly, so a proposed-policy experiment
    cannot silently leave one task unrestricted.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    if ratio_caps is None:
        return None
    if not isinstance(ratio_caps, Mapping):
        raise TypeError("ratio_caps must be a mapping or None")
    expected_ids = {profile.task.task_id for profile in scenario.tasks}
    if set(ratio_caps) != expected_ids:
        raise ValueError("ratio_caps must contain exactly one cap for each task")
    validated: dict[str, float] = {}
    for task_id in expected_ids:
        cap = ratio_caps[task_id]
        validate_unit_interval(cap, f"ratio cap for {task_id}")
        validated[task_id] = float(cap)
    return validated
