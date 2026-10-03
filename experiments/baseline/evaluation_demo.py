"""Compare supplied two-task plans using one scenario and fixed normalizers."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from experiments.baseline.fuzzy_security_demo import (
    EXPERT_WEIGHTS,
    PERSPECTIVE_CONFIG,
    build_example_assessments,
)
from src.evaluation import derive_normalization, evaluate_plan
from src.fuzzy_security import assess_security
from src.models import EdgeServer, Task
from src.objective import ObjectiveConfig
from src.scenario import (
    OffloadingDecision,
    OffloadingScenario,
    ServerProfile,
    TaskProfile,
    WirelessLink,
)


def main() -> None:
    """Print complete inputs, fuzzy intermediates, constraints, and objectives."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--security-threshold", type=float, default=0.6)
    parser.add_argument("--link-rate-mbps", type=float, default=40.0)
    args = parser.parse_args()
    try:
        assessments = build_example_assessments()
        security = assess_security(
            assessments,
            expert_weights=EXPERT_WEIGHTS,
            security_threshold=args.security_threshold,
            config=PERSPECTIVE_CONFIG,
        )
        tasks = tuple(
            TaskProfile(
                Task(f"task-{index}", float(index), index * 1_200_000_000.0, 3.0),
                1_000_000_000.0,
                security.security_level,
                5_000_000.0,
                256.0,
            )
            for index in (1, 2)
        )
        servers = tuple(
            ServerProfile(
                EdgeServer(f"edge-{index}", 8_000_000_000.0, 100.0, 100.0, 1024.0),
                4_000_000_000.0,
            )
            for index in (1, 2)
        )
        scenario = OffloadingScenario(
            tasks,
            servers,
            tuple(
                WirelessLink(
                    task.task.task_id,
                    server.server.server_id,
                    args.link_rate_mbps * 1_000_000,
                )
                for task in tasks
                for server in servers
            ),
            bandwidth_capacity_hz=20_000_000.0,
            security_threshold=args.security_threshold,
        )
        normalization = derive_normalization(scenario)
        plans = {
            "local": (
                OffloadingDecision("task-1", 0.0),
                OffloadingDecision("task-2", 0.0),
            ),
            "edge_balanced": (
                OffloadingDecision("task-1", 1.0, "edge-1"),
                OffloadingDecision("task-2", 1.0, "edge-2"),
            ),
            "partial_balanced": (
                OffloadingDecision("task-1", 0.4, "edge-1"),
                OffloadingDecision("task-2", 0.6, "edge-2"),
            ),
            "partial_concentrated": (
                OffloadingDecision("task-1", 0.4, "edge-1"),
                OffloadingDecision("task-2", 0.6, "edge-1"),
            ),
        }
        results = {}
        for name, decisions in plans.items():
            result = evaluate_plan(scenario, decisions, normalization=normalization)
            results[name] = {
                **asdict(result),
                "objective_value": result.objective.value,
            }
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "example_type": "synthetic_two_task_equation_check_not_an_optimization",
                "scenario": asdict(scenario),
                "expert_assessments_shared_by_tasks": [asdict(a) for a in assessments],
                "expert_weights": EXPERT_WEIGHTS,
                "perspective_weights": asdict(PERSPECTIVE_CONFIG),
                "security_assessment_shared_by_tasks": asdict(security),
                "objective_weights": asdict(ObjectiveConfig()),
                "normalization": asdict(normalization),
                "plans": results,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
