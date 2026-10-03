"""Find a bounded exact reference optimum on a small synthetic scenario."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from src.config import ExperimentConfig, LoadBalanceConfig, SyntheticScenarioConfig
from src.dataset_io import DATASET_KIND, dataset_fingerprint, read_dataset
from src.evaluation import evaluate_plan
from src.objective import ObjectiveConfig
from src.optimizers.exact import DEFAULT_MAX_CANDIDATES, solve_exact
from src.scenario import OffloadingDecision
from src.synthetic import generate_synthetic_dataset


def main() -> None:
    """Print an exact reference result without writing files or changing inputs."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--tasks", type=int)
    parser.add_argument("--servers", type=int)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES)
    args = parser.parse_args()
    if args.input is not None and any(
        value is not None for value in (args.seed, args.tasks, args.servers)
    ):
        parser.error("--input cannot be combined with generation parameters")
    try:
        if args.input is not None:
            dataset = read_dataset(args.input)
        else:
            config = replace(
                SyntheticScenarioConfig(),
                experiment=ExperimentConfig(
                    random_seed=42 if args.seed is None else args.seed,
                    task_count=3 if args.tasks is None else args.tasks,
                    server_count=2 if args.servers is None else args.servers,
                ),
            )
            dataset = generate_synthetic_dataset(config)
        objective_config = ObjectiveConfig()
        load_config = LoadBalanceConfig()
        result = solve_exact(
            dataset.scenario,
            normalization=dataset.normalization,
            objective_config=objective_config,
            load_config=load_config,
            max_candidates=args.max_candidates,
        )
        local = evaluate_plan(
            dataset.scenario,
            tuple(
                OffloadingDecision(task.task.task_id, 0.0)
                for task in dataset.scenario.tasks
            ),
            normalization=dataset.normalization,
            objective_config=objective_config,
            load_config=load_config,
        )
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "example_type": "exact_small_instance_verification_not_boalbfs",
                "dataset_kind": DATASET_KIND,
                "sha256": dataset_fingerprint(dataset),
                "seed": int(dataset.configuration.experiment.random_seed),
                "task_count": len(dataset.scenario.tasks),
                "server_count": len(dataset.scenario.servers),
                "runtime": asdict(dataset.runtime),
                "normalization": asdict(dataset.normalization),
                "objective_weights": asdict(objective_config),
                "load_weights": asdict(load_config),
                "max_candidates": args.max_candidates,
                "candidates_checked": result.candidates_checked,
                "feasible_candidates": result.feasible_candidates,
                "infeasible_candidates": result.infeasible_candidates,
                "local_objective_value": local.objective.value,
                "best_objective_value": result.best.objective.value,
                "best": asdict(result.best),
                "parameter_notes": "references/synthetic_data.md",
                "search_notes": "references/exact_search.md",
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
