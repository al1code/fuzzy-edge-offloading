"""Paired Local / Edge / Local-Edge experiment with replayable evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from dataclasses import asdict, dataclass, replace
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
from src.load_balance import CapacityExceededError
from src.objective import ObjectiveConfig
from src.optimizers.genetic import GenerationSummary, search_locations
from src.optimizers.sapso import solve_boalbfs
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from src.synthetic import SyntheticDataset, generate_synthetic_dataset
from src.validation import validate_integer

MODES = ("Local", "Edge", "Local-Edge")
DEFAULT_DATA_SEEDS = (7, 21, 42, 84, 2026)
METRICS = (
    "objective",
    "total_latency_seconds",
    "total_security_risk",
    "load_variance",
    "normalized_risk",
    "mean_offloading_ratio",
    "search_seconds",
    "plan_evaluations",
    "gain_vs_local_percent",
    "gain_vs_edge_percent",
)


@dataclass(frozen=True, slots=True)
class ModeRun:
    mode: str
    data_seed: int
    optimizer_seed: int
    sha256: str
    status: str
    reason: str | None
    search_seconds: float
    ga_evaluations: int
    plan_evaluations: int
    infeasible_evaluations: int
    evaluation: PlanEvaluation | None
    history: tuple[GenerationSummary, ...]


def compare_modes(
    dataset: SyntheticDataset,
    optimizer_seed: int,
    *,
    genetic_config: GeneticSearchConfig,
    swarm_config: SwarmSearchConfig,
) -> tuple[ModeRun, ...]:
    """Each mode receives identical immutable inputs and normalization.

    Edge uses the same GA budget, but full ratios and server-only genes.
    Local-Edge uses additional swarm evaluations; this is a mode comparison,
    not an equal-compute-budget algorithm benchmark. No result cherry-picking.
    """
    fingerprint = dataset_fingerprint(dataset)
    runs = []
    for mode in MODES:
        start = perf_counter()
        ga_calls, plan_calls, infeasible, history = 0, 0, 0, ()
        reason, status = None, "feasible"
        if mode == "Local":
            result = evaluate_plan(
                dataset.scenario,
                tuple(
                    OffloadingDecision(task.task.task_id, 0.0)
                    for task in dataset.scenario.tasks
                ),
                normalization=dataset.normalization,
            )
            plan_calls = 1
        elif mode == "Edge":

            def evaluate_edge(locations: tuple[int, ...]) -> PlanEvaluation:
                nonlocal plan_calls, infeasible
                plan_calls += 1
                try:
                    return evaluate_plan(
                        dataset.scenario,
                        tuple(
                            OffloadingDecision(
                                task.task.task_id,
                                1.0,
                                dataset.scenario.servers[gene - 1].server.server_id,
                            )
                            for task, gene in zip(
                                dataset.scenario.tasks, locations, strict=True
                            )
                        ),
                        normalization=dataset.normalization,
                    )
                except CapacityExceededError:
                    infeasible += 1
                    raise

            try:
                edge = search_locations(
                    dataset.scenario,
                    evaluate_edge,
                    random_state=create_random_state(optimizer_seed),
                    config=genetic_config,
                    allow_local=False,
                )
                result, history, ga_calls = edge.best, edge.history, edge.evaluations
            except CapacityExceededError as exc:
                result, status, reason = None, "no_feasible_initial_plan", str(exc)
                ga_calls = plan_calls
        else:
            hybrid = solve_boalbfs(
                dataset.scenario,
                normalization=dataset.normalization,
                random_state=create_random_state(optimizer_seed),
                genetic_config=genetic_config,
                swarm_config=swarm_config,
            )
            result, history = hybrid.genetic.best, hybrid.genetic.history
            ga_calls, plan_calls = hybrid.genetic.evaluations, hybrid.plan_evaluations
            infeasible = hybrid.genetic.infeasible_evaluations
        runs.append(
            ModeRun(
                mode,
                dataset.configuration.experiment.random_seed,
                optimizer_seed,
                fingerprint,
                status,
                reason,
                perf_counter() - start,
                ga_calls,
                plan_calls,
                infeasible,
                result,
                history,
            )
        )
    return tuple(runs)


def run_rows(runs: tuple[ModeRun, ...]) -> list[dict]:
    """Flatten metrics while keeping paired gains on the same data/search seed."""
    by_pair = {(r.data_seed, r.optimizer_seed, r.mode): r for r in runs}
    rows = []
    for run in runs:
        row = {
            key: value
            for key, value in asdict(run).items()
            if key not in ("evaluation", "history")
        }
        result = run.evaluation
        row.update({metric: None for metric in METRICS if metric not in row})
        if result is not None:
            row.update(
                objective=result.objective.value,
                total_latency_seconds=result.total_latency_seconds,
                total_security_risk=result.total_security_risk,
                load_variance=result.objective.load_variance,
                normalized_risk=result.objective.normalized_risk,
                normalized_latency=result.objective.normalized_latency,
                latency_term=result.objective.latency_term,
                risk_term=result.objective.risk_term,
                load_term=result.objective.load_term,
                mean_offloading_ratio=mean(
                    t.decision.offloading_ratio for t in result.tasks
                ),
                selected_zero_ratio_tasks=sum(
                    t.decision.server_id is not None
                    and t.decision.offloading_ratio == 0.0
                    for t in result.tasks
                ),
            )
            for reference, field in (
                ("Local", "gain_vs_local_percent"),
                ("Edge", "gain_vs_edge_percent"),
            ):
                baseline = by_pair[
                    (run.data_seed, run.optimizer_seed, reference)
                ].evaluation
                if baseline is not None and baseline.objective.value > 0.0:
                    row[field] = (
                        100.0
                        * (baseline.objective.value - result.objective.value)
                        / baseline.objective.value
                    )
        rows.append(row)
    return rows


def summarize(rows: list[dict]) -> list[dict]:
    """Average search repeats first, then independent dataset means.

    Error bars are sample SD across dataset means, not confidence intervals.
    Exclude incomplete groups explicitly; never turn failures into zero scores.
    """
    summaries = []
    for mode in MODES:
        mode_rows = [row for row in rows if row["mode"] == mode]
        seeds = sorted({row["data_seed"] for row in mode_rows})
        for metric in METRICS:
            dataset_means, within_sds = [], []
            for seed in seeds:
                group = [row for row in mode_rows if row["data_seed"] == seed]
                if not all(
                    row["status"] == "feasible" and row[metric] is not None
                    for row in group
                ):
                    continue
                values = [row[metric] for row in group]
                dataset_means.append(mean(values))
                if len(values) > 1:
                    within_sds.append(stdev(values))
            summaries.append(
                {
                    "mode": mode,
                    "metric": metric,
                    "mean": mean(dataset_means) if dataset_means else None,
                    "sd_between_datasets": stdev(dataset_means)
                    if len(dataset_means) > 1
                    else None,
                    "mean_sd_within_dataset": mean(within_sds) if within_sds else None,
                    "complete_datasets": len(dataset_means),
                    "total_datasets": len(seeds),
                    "feasible_runs": sum(
                        row["status"] == "feasible" for row in mode_rows
                    ),
                    "total_runs": len(mode_rows),
                }
            )
    return summaries


def _write_json(path: Path, value: object) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def _write_csv(path: Path, rows: list[dict]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _plot(
    path: Path, summaries: list[dict], task_count: int, server_count: int
) -> None:
    figure = Figure(figsize=(11, 7), layout="constrained")
    FigureCanvasAgg(figure)
    panels = (
        ("objective", "Weighted objective F", "Lower is better"),
        ("total_latency_seconds", "Sum of task latencies", "Seconds (not search time)"),
        (
            "normalized_risk",
            "Normalized offloading risk",
            "Model risk score, not attack probability",
        ),
        ("load_variance", "Server load variance", "Dimensionless"),
    )
    index = {(s["mode"], s["metric"]): s for s in summaries}
    for axis, (metric, title, unit) in zip(
        figure.subplots(2, 2).flat, panels, strict=True
    ):
        values = [index[(mode, metric)]["mean"] for mode in MODES]
        deviations = [index[(mode, metric)]["sd_between_datasets"] for mode in MODES]
        errors = deviations if all(sd is not None for sd in deviations) else None
        bars = axis.bar(
            MODES,
            [float("nan") if v is None else v for v in values],
            yerr=errors,
            capsize=4,
            color=("#606870", "#be5353", "#21856b"),
            width=0.55,
        )
        axis.bar_label(
            bars,
            labels=["" if v is None else f"{v:.4g}" for v in values],
            padding=6,
        )
        for position, value in enumerate(values):
            if value is None:
                axis.text(
                    position,
                    0.02,
                    "unavailable",
                    ha="center",
                    transform=axis.get_xaxis_transform(),
                )
        axis.set_title(title, fontsize=12)
        axis.set_ylabel(unit, fontsize=9)
        axis.margins(y=0.25)
        lower = min(
            (
                value - (sd or 0.0)
                for value, sd in zip(values, deviations, strict=True)
                if value is not None
            ),
            default=0.0,
        )
        axis.set_ylim(bottom=min(0.0, lower * 1.2))
        axis.set_axisbelow(True)
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle(
        f"Execution modes | {task_count} tasks / {server_count} servers\n"
        "Dataset means; error bars = sample SD (not CI, omitted when undefined)",
        fontsize=13,
    )
    figure.savefig(path, dpi=160)


def run_experiment(
    output: Path,
    *,
    data_seeds: tuple[int, ...] = DEFAULT_DATA_SEEDS,
    optimizer_seeds: tuple[int, ...] = (0, 1, 2),
    scenario_config: SyntheticScenarioConfig | None = None,
    genetic_config: GeneticSearchConfig | None = None,
    swarm_config: SwarmSearchConfig | None = None,
) -> tuple[ModeRun, ...]:
    """Create one new result bundle; refuse to overwrite any existing directory."""
    for seeds in (data_seeds, optimizer_seeds):
        if not seeds or len(set(seeds)) != len(seeds):
            raise ValueError("seed lists must be nonempty and contain no duplicates")
        for seed in seeds:
            validate_integer(seed, "seed")
    scenario_config = (
        scenario_config if scenario_config is not None else SyntheticScenarioConfig()
    )
    genetic_config = (
        genetic_config
        if genetic_config is not None
        else GeneticSearchConfig(population_size=12, generations=8)
    )
    swarm_config = (
        swarm_config if swarm_config is not None else SwarmSearchConfig(iterations=15)
    )
    for config, expected in (
        (scenario_config, SyntheticScenarioConfig),
        (genetic_config, GeneticSearchConfig),
        (swarm_config, SwarmSearchConfig),
    ):
        if not isinstance(config, expected):
            raise TypeError(f"config must be a {expected.__name__}")
    root = Path(__file__).resolve().parents[2]
    source_files = sorted(
        (
            *root.joinpath("src").rglob("*.py"),
            *root.joinpath("experiments").rglob("*.py"),
        )
    )
    source_hashes = {
        str(p.relative_to(root)).replace("\\", "/"): hashlib.sha256(
            p.read_bytes()
        ).hexdigest()
        for p in source_files
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "datasets").mkdir()
    manifest = {
        "experiment": "execution-modes-v1",
        "status": "running",
        "interpretation": "Fig. 2 question under project assumptions; not recovered author experiment",
        "data_seeds": list(data_seeds),
        "optimizer_seeds": list(optimizer_seeds),
        "scenario_config": asdict(scenario_config),
        "genetic_config": asdict(genetic_config),
        "swarm_config": asdict(swarm_config),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "platform": platform.platform(),
        },
        "source_sha256": source_hashes,
        "objective_weights": asdict(ObjectiveConfig()),
        "load_weights": asdict(LoadBalanceConfig()),
        "normalization": "fixed per scenario and shared by all modes; stored in snapshots",
        "ga_evaluation_budget_per_search": genetic_config.evaluation_budget,
        "hybrid_plan_evaluation_budget_per_search": genetic_config.evaluation_budget
        * swarm_config.evaluation_budget,
        "statistics": "mean search repeats within each dataset, then mean/sample SD of dataset means",
        "limitations": "Small sample is exploratory; unequal plan budgets; no optimality or significance claim",
    }
    _write_json(output / "manifest.json", manifest)
    runs = []
    for seed in data_seeds:
        dataset = generate_synthetic_dataset(
            replace(
                scenario_config,
                experiment=replace(scenario_config.experiment, random_seed=seed),
            )
        )
        write_dataset(dataset, output / "datasets" / f"seed_{seed}.json")
        for optimizer_seed in optimizer_seeds:
            print(
                f"Data seed {seed}, optimizer seed {optimizer_seed}",
                file=sys.stderr,
                flush=True,
            )
            runs.extend(
                compare_modes(
                    dataset,
                    optimizer_seed,
                    genetic_config=genetic_config,
                    swarm_config=swarm_config,
                )
            )
    runs = tuple(runs)
    rows = run_rows(runs)
    summaries = summarize(rows)
    _write_json(output / "runs.json", [asdict(run) for run in runs])
    _write_csv(output / "runs.csv", rows)
    _write_csv(output / "summary.csv", summaries)
    _plot(
        output / "comparison.png",
        summaries,
        scenario_config.experiment.task_count,
        scenario_config.experiment.server_count,
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
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tasks", type=int, default=60)
    parser.add_argument("--servers", type=int, default=3)
    parser.add_argument(
        "--data-seeds", type=int, nargs="+", default=list(DEFAULT_DATA_SEEDS)
    )
    parser.add_argument("--optimizer-seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--generations", type=int, default=8)
    parser.add_argument("--particles", type=int, default=8)
    parser.add_argument("--pso-iterations", type=int, default=15)
    args = parser.parse_args()
    try:
        runs = run_experiment(
            args.output,
            data_seeds=tuple(args.data_seeds),
            optimizer_seeds=tuple(args.optimizer_seeds),
            scenario_config=replace(
                SyntheticScenarioConfig(),
                experiment=ExperimentConfig(
                    task_count=args.tasks, server_count=args.servers
                ),
            ),
            genetic_config=GeneticSearchConfig(
                population_size=args.population, generations=args.generations
            ),
            swarm_config=SwarmSearchConfig(
                particle_count=args.particles, iterations=args.pso_iterations
            ),
        )
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "runs": len(runs),
                "feasible_runs": sum(run.status == "feasible" for run in runs),
                "objective_summary": [
                    s for s in summarize(run_rows(runs)) if s["metric"] == "objective"
                ],
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
