"""Evaluate supplied ratios in a worked example, without optimizing a decision."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from experiments.baseline.fuzzy_security_demo import (
    EXPERT_WEIGHTS,
    PERSPECTIVE_CONFIG,
    build_example_assessments,
)
from src.fuzzy_security import assess_security, calculate_offloading_risk
from src.latency import calculate_task_latency
from src.load_balance import (
    ResourceVector,
    calculate_load_variance,
    calculate_server_load,
)
from src.models import Task


def main() -> None:
    """Print the inputs and evaluated local, partial, and full-edge scenarios."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ratios", nargs="+", type=float, default=(0.0, 0.4, 1.0))
    parser.add_argument("--security-threshold", type=float, default=0.6)
    parser.add_argument("--link-rate-mbps", type=float, default=40.0)
    args = parser.parse_args()
    task = Task("worked-task", 1.0, 1_200_000_000.0, 2.0)
    capacity = ResourceVector(8_000_000_000.0, 20_000_000.0, 1024.0)
    reservation = ResourceVector(4_000_000_000.0, 5_000_000.0, 256.0)
    assessments = build_example_assessments()
    try:
        security = assess_security(
            assessments,
            expert_weights=EXPERT_WEIGHTS,
            security_threshold=args.security_threshold,
            config=PERSPECTIVE_CONFIG,
        )
        scenarios = []
        for ratio in args.ratios:
            latency = calculate_task_latency(
                task,
                offloading_ratio=ratio,
                local_cpu_cycles_per_second=1_000_000_000.0,
                edge_cpu_cycles_per_second=reservation.cpu_cycles_per_second,
                transmission_rate_bits_per_second=args.link_rate_mbps * 1_000_000,
            )
            assigned = int(ratio > 0.0)
            load = calculate_server_load(capacity, (reservation,) if assigned else ())
            idle_load = calculate_server_load(capacity, ())
            scenarios.append(
                {
                    "offloading_ratio": ratio,
                    "server_assignment": assigned,
                    "latency": {
                        **asdict(latency),
                        "total_seconds": latency.total_seconds,
                    },
                    "offloading_risk": calculate_offloading_risk(
                        security.security_risk, ratio, assigned
                    ),
                    "selected_server_load": asdict(load),
                    "idle_server_load": asdict(idle_load),
                    "load_variance": calculate_load_variance(
                        (load.weighted_load, idle_load.weighted_load)
                    ),
                }
            )
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            {
                "example_type": "synthetic_worked_example_not_an_optimization",
                "task": asdict(task),
                "expert_assessments": [asdict(a) for a in assessments],
                "expert_weights": EXPERT_WEIGHTS,
                "perspective_weights": asdict(PERSPECTIVE_CONFIG),
                "security_threshold": args.security_threshold,
                "security_assessment": asdict(security),
                "local_cpu_cycles_per_second": 1_000_000_000.0,
                "link_rate_bits_per_second": args.link_rate_mbps * 1_000_000,
                "resource_capacity": asdict(capacity),
                "selected_task_reservation": asdict(reservation),
                "server_count": 2,
                "scenarios": scenarios,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
