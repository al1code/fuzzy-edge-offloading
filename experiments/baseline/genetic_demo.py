"""Run genetic locations with either affine-reference or SA-PSO ratios."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path

from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import DATASET_KIND, dataset_fingerprint, read_dataset
from src.evaluation import evaluate_plan
from src.objective import ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.optimizers.genetic import solve_genetic
from src.optimizers.sapso import solve_boalbfs
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from src.synthetic import generate_synthetic_dataset


def main() -> None:
    """Print traceable search results; optional exact comparison is small-only."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--method",
        choices=("genetic-reference", "boalbfs"),
        default="genetic-reference",
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--tasks", type=int)
    parser.add_argument("--servers", type=int)
    parser.add_argument("--optimizer-seed", type=int, default=42)
    parser.add_argument("--population", type=int)
    parser.add_argument("--generations", type=int)
    parser.add_argument("--particles", type=int)
    parser.add_argument("--pso-iterations", type=int)
    parser.add_argument("--verify-exact", action="store_true")
    args = parser.parse_args()
    if args.input is not None and any(
        value is not None for value in (args.seed, args.tasks, args.servers)
    ):
        parser.error("--input cannot be combined with generation parameters")
    if args.method != "boalbfs" and (
        args.particles is not None or args.pso_iterations is not None
    ):
        parser.error("swarm options require --method boalbfs")
    try:
        defaults = (
            GeneticSearchConfig(population_size=10, generations=5)
            if args.method == "boalbfs"
            else GeneticSearchConfig()
        )
        config = GeneticSearchConfig(
            population_size=defaults.population_size
            if args.population is None
            else args.population,
            generations=defaults.generations
            if args.generations is None
            else args.generations,
        )
        swarm_config = None
        if args.method == "boalbfs":
            swarm_defaults = SwarmSearchConfig()
            swarm_config = replace(
                swarm_defaults,
                particle_count=swarm_defaults.particle_count
                if args.particles is None
                else args.particles,
                iterations=swarm_defaults.iterations
                if args.pso_iterations is None
                else args.pso_iterations,
            )
        random_state = create_random_state(args.optimizer_seed)
        if args.input is not None:
            dataset = read_dataset(args.input)
        else:
            defaults = SyntheticScenarioConfig()
            experiment = defaults.experiment
            dataset = generate_synthetic_dataset(
                replace(
                    defaults,
                    experiment=ExperimentConfig(
                        experiment.random_seed if args.seed is None else args.seed,
                        experiment.task_count if args.tasks is None else args.tasks,
                        experiment.server_count
                        if args.servers is None
                        else args.servers,
                    ),
                )
            )
        objective_config, load_config = ObjectiveConfig(), LoadBalanceConfig()
        exact = (
            solve_exact(
                dataset.scenario,
                normalization=dataset.normalization,
                objective_config=objective_config,
                load_config=load_config,
            )
            if args.verify_exact
            else None
        )
        integrated = None
        if swarm_config is not None:
            integrated = solve_boalbfs(
                dataset.scenario,
                normalization=dataset.normalization,
                random_state=random_state,
                genetic_config=config,
                swarm_config=swarm_config,
                objective_config=objective_config,
                load_config=load_config,
            )
        result = (
            integrated.genetic
            if integrated is not None
            else solve_genetic(
                dataset.scenario,
                normalization=dataset.normalization,
                random_state=random_state,
                config=config,
                objective_config=objective_config,
                load_config=load_config,
            )
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
        comparison = None
        if exact is not None:
            gap = result.best.objective.value - exact.best.objective.value
            comparison = {
                "objective_value": exact.best.objective.value,
                "candidates_checked": exact.candidates_checked,
                "absolute_gap": gap,
                "relative_gap": gap / exact.best.objective.value
                if exact.best.objective.value > 0.0
                else None,
            }
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "example_type": "two_layer_ga_sapso_with_documented_assumptions"
                if integrated is not None
                else "adaptive_ga_with_affine_ratio_reference_not_boalbfs",
                "method": args.method,
                "swarm_config": asdict(swarm_config)
                if swarm_config is not None
                else None,
                "plan_evaluations": integrated.plan_evaluations
                if integrated is not None
                else result.evaluations,
                "plan_evaluation_budget": config.evaluation_budget
                * (swarm_config.evaluation_budget if swarm_config is not None else 1),
                "accepted_worse": integrated.accepted_worse
                if integrated is not None
                else None,
                "dataset_kind": DATASET_KIND,
                "sha256": dataset_fingerprint(dataset),
                "seed": int(dataset.configuration.experiment.random_seed),
                "optimizer_seed": args.optimizer_seed,
                "task_count": len(dataset.scenario.tasks),
                "server_count": len(dataset.scenario.servers),
                "runtime": asdict(dataset.runtime),
                "search_config": asdict(config),
                "evaluation_budget": config.evaluation_budget,
                "evaluations": result.evaluations,
                "infeasible_evaluations": result.infeasible_evaluations,
                "normalization": asdict(dataset.normalization),
                "objective_weights": asdict(objective_config),
                "load_weights": asdict(load_config),
                "local_objective_value": local.objective.value,
                "best_objective_value": result.best.objective.value,
                "best_locations": result.best_locations,
                "best": {
                    "decisions": [asdict(task.decision) for task in result.best.tasks],
                    "total_latency_seconds": result.best.total_latency_seconds,
                    "total_security_risk": result.best.total_security_risk,
                    "objective": asdict(result.best.objective),
                    "servers": [asdict(server) for server in result.best.servers],
                },
                "history": [asdict(generation) for generation in result.history],
                "exact_comparison": comparison,
                "search_notes": "references/README.md#boalbfs",
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
