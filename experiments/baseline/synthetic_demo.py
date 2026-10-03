"""Generate or replay a synthetic dataset and check supplied round-robin plans."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from src.config import ExperimentConfig, LoadBalanceConfig, SyntheticScenarioConfig
from src.dataset_io import (
    DATASET_KIND,
    dataset_fingerprint,
    read_dataset,
    write_dataset,
)
from src.evaluation import evaluate_plan
from src.load_balance import CapacityExceededError
from src.objective import ObjectiveConfig
from src.scenario import OffloadingDecision
from src.synthetic import GENERATOR_VERSION, generate_synthetic_dataset


def main() -> None:
    """Print a compact summary; optional output is a full replayable snapshot."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--tasks", type=int)
    parser.add_argument("--servers", type=int)
    parser.add_argument("--security-threshold", type=float)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    generation_options = (args.seed, args.tasks, args.servers, args.security_threshold)
    if args.input is not None and any(
        value is not None for value in generation_options
    ):
        parser.error("--input cannot be combined with generation parameters")
    try:
        if args.input is not None:
            dataset = read_dataset(args.input)
        else:
            defaults = SyntheticScenarioConfig()
            experiment = defaults.experiment
            config = replace(
                defaults,
                experiment=ExperimentConfig(
                    random_seed=experiment.random_seed
                    if args.seed is None
                    else args.seed,
                    task_count=experiment.task_count
                    if args.tasks is None
                    else args.tasks,
                    server_count=experiment.server_count
                    if args.servers is None
                    else args.servers,
                ),
                security_threshold=defaults.security_threshold
                if args.security_threshold is None
                else args.security_threshold,
            )
            dataset = generate_synthetic_dataset(config)
        scenario = dataset.scenario
        objective_config = ObjectiveConfig()
        load_config = LoadBalanceConfig()
        plans = {
            "local": tuple(
                OffloadingDecision(task.task.task_id, 0.0) for task in scenario.tasks
            ),
            "edge_round_robin": tuple(
                OffloadingDecision(
                    task.task.task_id,
                    1.0,
                    scenario.servers[index % len(scenario.servers)].server.server_id,
                )
                for index, task in enumerate(scenario.tasks)
            ),
            "partial_half_round_robin": tuple(
                OffloadingDecision(
                    task.task.task_id,
                    0.5,
                    scenario.servers[index % len(scenario.servers)].server.server_id,
                )
                for index, task in enumerate(scenario.tasks)
            ),
        }
        results = {}
        for name, decisions in plans.items():
            try:
                result = evaluate_plan(
                    scenario,
                    decisions,
                    normalization=dataset.normalization,
                    objective_config=objective_config,
                    load_config=load_config,
                )
            except CapacityExceededError as exc:
                results[name] = {"feasible": False, "reason": str(exc)}
            else:
                results[name] = {
                    "feasible": True,
                    "total_latency_seconds": result.total_latency_seconds,
                    "total_security_risk": result.total_security_risk,
                    "objective": asdict(result.objective),
                    "objective_value": result.objective.value,
                }
        if args.output is not None:
            write_dataset(dataset, args.output)
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "example_type": "synthetic_generation_and_plan_checks_not_optimization",
                "dataset_kind": DATASET_KIND,
                "generator_version": GENERATOR_VERSION,
                "sha256": dataset_fingerprint(dataset),
                "seed": int(dataset.configuration.experiment.random_seed),
                "task_count": len(scenario.tasks),
                "server_count": len(scenario.servers),
                "runtime": asdict(dataset.runtime),
                "normalization": asdict(dataset.normalization),
                "objective_weights": asdict(objective_config),
                "load_weights": asdict(load_config),
                "parameter_notes": "references/synthetic_data.md",
                "output_path": str(args.output.resolve())
                if args.output is not None
                else None,
                "plans": results,
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
