"""Compare SA-PSO and analytical ratios, with fixed locations or a shared GA."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path
from statistics import mean, stdev
from time import perf_counter

import matplotlib
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, write_dataset
from src.evaluation import PlanEvaluation, evaluate_plan
from src.objective import ObjectiveConfig
from src.optimizers.genetic import search_locations
from src.optimizers.locations import evaluate_locations_exact, validate_locations
from src.optimizers.sapso import solve_boalbfs, solve_sapso
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from src.synthetic import SyntheticDataset, generate_synthetic_dataset
from src.validation import validate_integer

METHODS = ("SA-PSO", "Analytical")
PIPELINE_METHODS = ("GA+SA-PSO", "GA+Analytical")
DATA_SEEDS = (7, 21, 42, 84, 2026)
METRICS = ("objective", "gap_to_exact", "search_seconds", "plan_evaluations")
PIPELINE_METRICS = METRICS + (
    "total_latency_seconds",
    "total_security_risk",
    "load_variance",
    "endpoint_tests",
    "ga_evaluations",
    "objective_delta_vs_sapso",
)


def _plan_row(
    dataset: SyntheticDataset,
    method: str,
    optimizer_seed: int,
    locations: Sequence[int],
    evaluation: PlanEvaluation,
    calls: int,
    elapsed: float,
) -> dict:
    return {
        "method": method,
        "data_seed": dataset.configuration.experiment.random_seed,
        "optimizer_seed": optimizer_seed,
        "sha256": dataset_fingerprint(dataset),
        "locations": json.dumps(locations),
        "ratios": json.dumps([t.decision.offloading_ratio for t in evaluation.tasks]),
        "objective": evaluation.objective.value,
        "total_latency_seconds": evaluation.total_latency_seconds,
        "total_security_risk": evaluation.total_security_risk,
        **asdict(evaluation.objective),
        "latency_normalizer": dataset.normalization.latency_seconds,
        "risk_normalizer": dataset.normalization.security_risk,
        "plan_evaluations": calls,
        "search_seconds": elapsed,
    }


def _zero_plan(dataset: SyntheticDataset, locations: Sequence[int]) -> PlanEvaluation:
    return evaluate_plan(
        dataset.scenario,
        tuple(
            OffloadingDecision(
                task.task.task_id,
                0.0,
                None
                if gene == 0
                else dataset.scenario.servers[gene - 1].server.server_id,
            )
            for task, gene in zip(dataset.scenario.tasks, locations, strict=True)
        ),
        normalization=dataset.normalization,
    )


def compare_ratios(
    dataset: SyntheticDataset,
    optimizer_seed: int,
    *,
    swarm_config: SwarmSearchConfig,
    locations: Sequence[int] | None = None,
) -> list[dict]:
    """Hold locations, capacities, fuzzy risks and normalization fixed.

    Default locations are round-robin, not optimized or chosen after results.
    Alternate measurement order by seed; generation and serialization are
    outside the timers. Infeasible locations and calculation errors propagate.
    """
    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    validate_integer(optimizer_seed, "optimizer_seed")
    if not isinstance(swarm_config, SwarmSearchConfig):
        raise TypeError("swarm_config must be a SwarmSearchConfig")
    scenario = dataset.scenario
    if locations is None:
        locations = tuple(
            i % len(scenario.servers) + 1 for i in range(len(scenario.tasks))
        )
    locations = validate_locations(scenario, locations)
    zero_reference = _zero_plan(dataset, locations).objective.value
    results = {}
    order = METHODS if optimizer_seed % 2 == 0 else METHODS[::-1]
    for method in order:
        state = create_random_state(optimizer_seed)
        start = perf_counter()
        if method == "SA-PSO":
            swarm = solve_sapso(
                scenario,
                locations,
                normalization=dataset.normalization,
                random_state=state,
                config=swarm_config,
            )
            evaluation, calls = swarm.best, swarm.evaluations
        else:
            evaluation = evaluate_locations_exact(
                scenario, locations, normalization=dataset.normalization
            )
            calls = 1
        results[method] = (evaluation, calls, perf_counter() - start)
    reference = results["Analytical"][0].objective.value
    rows = []
    for method in METHODS:
        evaluation, calls, elapsed = results[method]
        rows.append(
            {
                **_plan_row(
                    dataset,
                    method,
                    optimizer_seed,
                    locations,
                    evaluation,
                    calls,
                    elapsed,
                ),
                "gap_to_exact": evaluation.objective.value - reference,
                "zero_ratio_objective": zero_reference,
                "endpoint_tests": (
                    2 * sum(gene != 0 for gene in locations)
                    if method == "Analytical"
                    else 0
                ),
            }
        )
    return rows


def compare_pipelines(
    dataset: SyntheticDataset,
    optimizer_seed: int,
    *,
    genetic_config: GeneticSearchConfig,
    swarm_config: SwarmSearchConfig,
) -> list[dict]:
    """Same upper GA budget; only the ratio evaluator differs.

    Locations may diverge because the fitness values differ. Count analytical
    endpoint work for every GA candidate, including infeasible candidates.
    Controls and post-search conditional checks are outside timers/counts.
    """
    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    validate_integer(optimizer_seed, "optimizer_seed")
    if not isinstance(genetic_config, GeneticSearchConfig):
        raise TypeError("genetic_config must be a GeneticSearchConfig")
    if not isinstance(swarm_config, SwarmSearchConfig):
        raise TypeError("swarm_config must be a SwarmSearchConfig")
    scenario = dataset.scenario
    local_reference = _zero_plan(dataset, (0,) * len(scenario.tasks)).objective.value
    results = {}
    order = PIPELINE_METHODS if optimizer_seed % 2 == 0 else PIPELINE_METHODS[::-1]
    for method in order:
        state = create_random_state(optimizer_seed)
        endpoint_tests = 0

        def analytical_evaluator(locations: tuple[int, ...]) -> PlanEvaluation:
            nonlocal endpoint_tests
            endpoint_tests += 2 * sum(gene != 0 for gene in locations)
            return evaluate_locations_exact(
                scenario, locations, normalization=dataset.normalization
            )

        start = perf_counter()
        if method == "GA+SA-PSO":
            result = solve_boalbfs(
                scenario,
                normalization=dataset.normalization,
                random_state=state,
                genetic_config=genetic_config,
                swarm_config=swarm_config,
            )
            genetic, calls = result.genetic, result.plan_evaluations
        else:
            # Same composition as solve_genetic, with endpoint accounting only.
            genetic = search_locations(
                scenario,
                analytical_evaluator,
                random_state=state,
                config=genetic_config,
            )
            calls = genetic.evaluations
        elapsed = perf_counter() - start
        results[method] = (genetic, calls, endpoint_tests, elapsed)
    baseline = results["GA+SA-PSO"][0].best.objective.value
    rows = []
    for method in PIPELINE_METHODS:
        genetic, calls, endpoint_tests, elapsed = results[method]
        locations = genetic.best_locations
        conditional = (
            evaluate_locations_exact(
                scenario, locations, normalization=dataset.normalization
            )
            if method == "GA+SA-PSO"
            else genetic.best
        )
        rows.append(
            {
                **_plan_row(
                    dataset,
                    method,
                    optimizer_seed,
                    locations,
                    genetic.best,
                    calls,
                    elapsed,
                ),
                "gap_to_exact": genetic.best.objective.value
                - conditional.objective.value,
                "zero_ratio_objective": _zero_plan(dataset, locations).objective.value,
                "all_local_objective": local_reference,
                "objective_delta_vs_sapso": genetic.best.objective.value - baseline,
                "endpoint_tests": endpoint_tests,
                "ga_evaluations": genetic.evaluations,
                "infeasible_evaluations": genetic.infeasible_evaluations,
                "best_history": json.dumps(
                    [h.best_objective_value for h in genetic.history]
                ),
            }
        )
    return rows


def summarize(
    rows: list[dict],
    *,
    methods: Sequence[str] = METHODS,
    metrics: Sequence[str] = METRICS,
) -> list[dict]:
    """Use dataset means as independent observations, not optimizer repeats."""
    summaries = []
    for method in methods:
        group = [row for row in rows if row["method"] == method]
        seeds = sorted({row["data_seed"] for row in group})
        for metric in metrics:
            values = [
                mean(row[metric] for row in group if row["data_seed"] == seed)
                for seed in seeds
            ]
            summaries.append(
                {
                    "method": method,
                    "metric": metric,
                    "mean": mean(values),
                    "sd_between_datasets": stdev(values) if len(values) > 1 else None,
                    "datasets": len(values),
                    "runs": len(group),
                }
            )
    return summaries


def _plot(
    path: Path,
    summaries: list[dict],
    *,
    methods: Sequence[str] = METHODS,
    pipeline: bool = False,
) -> None:
    figure = Figure(figsize=(9, 4), layout="constrained")
    FigureCanvasAgg(figure)
    for axis, metric, scale, title in zip(
        figure.subplots(1, 2),
        ("objective", "search_seconds"),
        (1.0, 1000.0),
        (
            "Objective F (lower is better)",
            "Full search time (ms, log scale)"
            if pipeline
            else "Ratio calculation time (ms)",
        ),
        strict=True,
    ):
        values = [
            next(s for s in summaries if s["method"] == m and s["metric"] == metric)
            for m in methods
        ]
        heights = [s["mean"] * scale for s in values]
        errors = [(s["sd_between_datasets"] or 0.0) * scale for s in values]
        if pipeline and metric == "search_seconds":
            axis.set_yscale("log")
            for index, (height, error, color) in enumerate(
                zip(heights, errors, ("#464646", "#16896b"), strict=True)
            ):
                axis.errorbar(
                    index, height, yerr=error, fmt="o", color=color, capsize=4
                )
                axis.annotate(
                    f"{height:.1f}",
                    (index, height + error),
                    xytext=(0, 6),
                    textcoords="offset points",
                    ha="center",
                )
            axis.set_xticks(range(len(methods)), methods)
            axis.set_xlim(-0.5, len(methods) - 0.5)
            # Zero is invalid on a log axis; keep both complete ranges visible.
            positive = [
                v
                for h, e in zip(heights, errors, strict=True)
                for v in (h, h - e)
                if v > 0
            ]
            axis.set_ylim(
                min(positive) / 2,
                max(h + e for h, e in zip(heights, errors, strict=True)) * 2,
            )
        else:
            bars = axis.bar(
                methods,
                heights,
                yerr=errors,
                color=("#464646", "#16896b"),
                capsize=4,
            )
            if pipeline:
                axis.bar_label(bars, fmt="%.6f", padding=4)
                axis.set_ylim(top=axis.get_ylim()[1] * 1.15)
            axis.set_ylim(bottom=0)
        axis.set_title(title, fontsize=11)
        axis.set_axisbelow(True)
        axis.grid(axis="y", alpha=0.2)
    figure.suptitle(
        ("Full GA pipelines" if pipeline else "Fixed-location comparison")
        + "; dataset means +/- sample SD"
    )
    figure.savefig(path, dpi=150)


def _write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def run_experiment(
    output: Path,
    *,
    data_seeds: tuple[int, ...] = DATA_SEEDS,
    optimizer_seeds: tuple[int, ...] = (0, 1, 2),
    scenario_config: SyntheticScenarioConfig | None = None,
    swarm_config: SwarmSearchConfig | None = None,
    genetic_config: GeneticSearchConfig | None = None,
    scope: str = "fixed",
) -> list[dict]:
    """Save replayable inputs and compact paired decisions without overwriting."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if scope not in ("fixed", "pipeline"):
        raise ValueError("scope must be fixed or pipeline")
    for name, seeds in (
        ("data_seeds", data_seeds),
        ("optimizer_seeds", optimizer_seeds),
    ):
        for seed in seeds:
            validate_integer(seed, name)
        if not seeds or len(set(seeds)) != len(seeds):
            raise ValueError(f"{name} must be nonempty and unique")
    scenario_config = (
        scenario_config if scenario_config is not None else SyntheticScenarioConfig()
    )
    swarm_config = (
        swarm_config if swarm_config is not None else SwarmSearchConfig(iterations=15)
    )
    if not isinstance(scenario_config, SyntheticScenarioConfig):
        raise TypeError("scenario_config must be a SyntheticScenarioConfig")
    if not isinstance(swarm_config, SwarmSearchConfig):
        raise TypeError("swarm_config must be a SwarmSearchConfig")
    genetic_config = (
        genetic_config
        if genetic_config is not None
        else GeneticSearchConfig(population_size=12, generations=8)
    )
    if not isinstance(genetic_config, GeneticSearchConfig):
        raise TypeError("genetic_config must be a GeneticSearchConfig")
    methods = PIPELINE_METHODS if scope == "pipeline" else METHODS
    metrics = PIPELINE_METRICS if scope == "pipeline" else METRICS
    root = Path(__file__).resolve().parents[2]
    sources = sorted((root / "src").rglob("*.py")) + [
        Path(__file__).resolve(),
        root / "requirements-lock.txt",
    ]
    manifest = {
        "experiment": "fixed-location-ratios-v1",
        "status": "running",
        "methods": list(methods),
        "data_seeds": list(data_seeds),
        "optimizer_seeds": list(optimizer_seeds),
        "scenario_config": asdict(scenario_config),
        "swarm_config": asdict(swarm_config),
        "objective_weights": asdict(ObjectiveConfig()),
        "load_weights": asdict(LoadBalanceConfig()),
        "locations": "round-robin; identical for both methods, no GA",
        "statistics": "mean repeats within dataset, then mean/sample SD across datasets",
        "timing": "solver calls only; fresh RNG created outside timer; order alternates by seed parity",
        "counts": "Analytical: one full-plan evaluation PLUS two endpoint tests per selected task",
        "zero_ratio_control": "One shared full-plan check outside timers; not included in solver counts. SA-PSO precheck is not its incumbent.",
        "limitations": "Conditional ratio optimum only; not global location optimum or end-to-end BOALBFS speedup",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "platform": platform.platform(),
        },
        "source_sha256": {
            str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
            for p in sources
        },
    }
    if scope == "pipeline":
        manifest.update(
            experiment="ga-ratio-pipelines-v1",
            genetic_config=asdict(genetic_config),
            locations="searched by the same GA; fitness differences can change trajectories",
            budget="equal GA candidate budget, not equal full-plan/endpoint work or wall time",
            timing="complete solver calls (GA plus ratios); RNG/data/controls/serialization excluded; order alternates",
            counts="actual full-plan calls including infeasible checks; Analytical additionally counts every task endpoint test",
            zero_ratio_control="per-method winner's locations; may differ across methods; outside timers/counts",
            other_controls="shared all-local check; post-search exact ratios at the SA-PSO winner's locations; outside timers/counts",
            gap_to_exact="conditional ratio gap at each method's OWN winner locations, not global assignment gap",
            objective_delta_vs_sapso="paired signed F difference; negative favors GA+Analytical",
            limitations="synthetic recorded assumptions; GA is not globally exact; SA-PSO random particles do not retain zero precheck; timings hardware-dependent",
        )
    output.mkdir(parents=True, exist_ok=False)
    (output / "datasets").mkdir()
    _write_json(output / "manifest.json", manifest)
    rows = []
    for seed in data_seeds:
        dataset = generate_synthetic_dataset(
            replace(
                scenario_config,
                experiment=replace(scenario_config.experiment, random_seed=seed),
            )
        )
        write_dataset(dataset, output / "datasets" / f"seed_{seed}.json")
        for optimizer_seed in optimizer_seeds:
            rows.extend(
                compare_pipelines(
                    dataset,
                    optimizer_seed,
                    genetic_config=genetic_config,
                    swarm_config=swarm_config,
                )
                if scope == "pipeline"
                else compare_ratios(dataset, optimizer_seed, swarm_config=swarm_config)
            )
    summaries = summarize(rows, methods=methods, metrics=metrics)
    for name, records in (("runs.csv", rows), ("summary.csv", summaries)):
        with (output / name).open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    _plot(
        output / "comparison.png",
        summaries,
        methods=methods,
        pipeline=scope == "pipeline",
    )
    manifest["status"] = "complete"
    manifest["artifact_sha256"] = {
        str(p.relative_to(output)).replace("\\", "/"): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in sorted(output.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    _write_json(output / "manifest.json", manifest)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scope", choices=("fixed", "pipeline"), default="fixed")
    parser.add_argument("--tasks", type=int, default=60)
    parser.add_argument("--servers", type=int, default=3)
    parser.add_argument("--data-seeds", type=int, nargs="+", default=list(DATA_SEEDS))
    parser.add_argument("--optimizer-seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--particles", type=int, default=8)
    parser.add_argument("--pso-iterations", type=int, default=15)
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--generations", type=int, default=8)
    args = parser.parse_args()
    try:
        rows = run_experiment(
            args.output,
            scope=args.scope,
            data_seeds=tuple(args.data_seeds),
            optimizer_seeds=tuple(args.optimizer_seeds),
            scenario_config=replace(
                SyntheticScenarioConfig(),
                experiment=ExperimentConfig(
                    task_count=args.tasks, server_count=args.servers
                ),
            ),
            swarm_config=SwarmSearchConfig(
                particle_count=args.particles, iterations=args.pso_iterations
            ),
            genetic_config=GeneticSearchConfig(
                population_size=args.population, generations=args.generations
            ),
        )
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "runs": len(rows),
                "summary": summarize(
                    rows,
                    methods=PIPELINE_METHODS if args.scope == "pipeline" else METHODS,
                    metrics=PIPELINE_METRICS if args.scope == "pipeline" else METRICS,
                ),
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
