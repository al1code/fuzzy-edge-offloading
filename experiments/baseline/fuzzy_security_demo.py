"""Deterministic worked example; not a reproduction of the paper's experiments."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from src.config import FuzzySecurityConfig
from src.fuzzy_security import (
    SecurityPerspectives,
    assess_security,
    calculate_offloading_risk,
)
from src.models import TriangularFuzzyNumber

EXPERT_WEIGHTS = (0.25, 0.75)
PERSPECTIVE_CONFIG = FuzzySecurityConfig(0.5, 0.3, 0.2)


def build_example_assessments() -> tuple[SecurityPerspectives, SecurityPerspectives]:
    """Return the illustrative expert inputs shared by both worked demos."""

    return (
        SecurityPerspectives(
            TriangularFuzzyNumber(0.1, 0.2, 0.5),
            TriangularFuzzyNumber(0.2, 0.4, 0.8),
            TriangularFuzzyNumber(0.6, 0.7, 0.9),
        ),
        SecurityPerspectives(
            TriangularFuzzyNumber(0.4, 0.6, 0.9),
            TriangularFuzzyNumber(0.3, 0.5, 0.7),
            TriangularFuzzyNumber(0.1, 0.2, 0.3),
        ),
    )


def main() -> None:
    """Print the example inputs and all intermediate assessment results."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--security-threshold", type=float, default=0.6)
    parser.add_argument("--offloading-ratio", type=float, default=0.4)
    parser.add_argument("--server-assignment", type=int, choices=(0, 1), default=1)
    args = parser.parse_args()
    assessments = build_example_assessments()
    try:
        result = assess_security(
            assessments,
            expert_weights=EXPERT_WEIGHTS,
            security_threshold=args.security_threshold,
            config=PERSPECTIVE_CONFIG,
        )
        offloading_risk = calculate_offloading_risk(
            result.security_risk, args.offloading_ratio, args.server_assignment
        )
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "example_type": "synthetic_worked_example",
                "expert_assessments": [asdict(a) for a in assessments],
                "expert_weights": EXPERT_WEIGHTS,
                "perspective_weights": asdict(PERSPECTIVE_CONFIG),
                "security_threshold": args.security_threshold,
                "offloading_ratio": args.offloading_ratio,
                "server_assignment": args.server_assignment,
                "assessment": asdict(result),
                "offloading_risk": offloading_risk,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
