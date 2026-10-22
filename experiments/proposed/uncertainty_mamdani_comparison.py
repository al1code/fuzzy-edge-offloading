"""Compare baseline BOALBFS with the proposed Mamdani ratio caps.

Both methods share inputs, normalization, search budgets, and optimizer seeds.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
from collections.abc import Mapping, Sequence
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
from src.evaluation import PlanEvaluation, derive_normalization
from src.fuzzy_controller import (
    calculate_aggregate_assessment_uncertainty,
    derive_task_ratio_caps,
    evaluate_uncertainty_aware_offloading,
)
from src.fuzzy_security import SecurityPerspectives, aggregate_expert_assessments
from src.models import TriangularFuzzyNumber
from src.objective import ObjectiveConfig
from src.optimizers.sapso import solve_boalbfs
from src.random_utils import create_random_state
from src.scenario import OffloadingScenario, WirelessLink
from src.synthetic import SyntheticDataset, generate_synthetic_dataset
from src.validation import validate_integer, validate_positive, validate_unit_interval

METHODS = ("Baseline BOALBFS", "Uncertainty-aware Mamdani")
DEFAULT_DATA_SEEDS = (7, 21, 42, 84, 2026)
METRICS = (
    "objective",
    "total_latency_seconds",
    "total_security_risk",
    "uncertainty_weighted_exposure",
    "load_variance",
    "mean_offloading_ratio",
    "mean_allowed_cap",
    "max_cap_excess",
    "search_seconds",
    "plan_evaluations",
    "ga_evaluations",
    "accepted_worse",
)


def _validate_seeds(values: Sequence[int], name: str) -> tuple[int, ...]:
    values = tuple(values)
    if not values or len(set(values)) != len(values):
        raise ValueError(f"{name} must be nonempty and contain unique values")
    for value in values:
        validate_integer(value, name)
    return values


def _validate_factors(values: Sequence[float]) -> tuple[float, ...]:
    values = tuple(values)
    if not values or len(set(values)) != len(values):
        raise ValueError("link_rate_factors must be nonempty and unique")
    for value in values:
        validate_positive(value, "link_rate_factor")
    return tuple(float(value) for value in values)


def scaled_scenario(
    scenario: OffloadingScenario, link_rate_factor: float
) -> OffloadingScenario:
    """Return an immutable scenario whose wireless rates share one multiplier.

    The multiplier is only a documented sensitivity condition.  It leaves
    tasks, expert assessments, capacities, and policy caps intact.
    """

    if not isinstance(scenario, OffloadingScenario):
        raise TypeError("scenario must be an OffloadingScenario")
    validate_positive(link_rate_factor, "link_rate_factor")
    if link_rate_factor == 1.0:
        return scenario
    return replace(
        scenario,
        links=tuple(
            WirelessLink(
                link.task_id,
                link.server_id,
                link.rate_bits_per_second * link_rate_factor,
            )
            for link in scenario.links
        ),
    )


def derive_task_uncertainties(dataset: SyntheticDataset) -> dict[str, float]:
    """Derive one reproducible assessment-spread value per task from raw TFNs."""

    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    values = {}
    for profile, assessments in zip(
        dataset.scenario.tasks, dataset.expert_assessments, strict=True
    ):
        aggregate = aggregate_expert_assessments(
            assessments, dataset.configuration.expert_weights
        )
        uncertainty = calculate_aggregate_assessment_uncertainty(aggregate)
        validate_unit_interval(uncertainty, "assessment uncertainty")
        values[profile.task.task_id] = uncertainty
    return values


def derive_task_caps(dataset: SyntheticDataset) -> dict[str, float]:
    """Apply the standalone policy to the dataset's task-order raw inputs."""

    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    values = derive_task_ratio_caps(
        tuple(profile.security_level for profile in dataset.scenario.tasks),
        dataset.expert_assessments,
        dataset.configuration.expert_weights,
    )
    if len(values) != len(dataset.scenario.tasks):
        raise ValueError("ratio cap count must match the scenario task count")
    result = {}
    for profile, value in zip(dataset.scenario.tasks, values, strict=True):
        validate_unit_interval(value, "allowed offloading ratio")
        result[profile.task.task_id] = float(value)
    return result


def _locations(evaluation: PlanEvaluation, scenario: OffloadingScenario) -> list[int]:
    index = {
        profile.server.server_id: i + 1 for i, profile in enumerate(scenario.servers)
    }
    return [
        0 if task.decision.server_id is None else index[task.decision.server_id]
        for task in evaluation.tasks
    ]


def _row(
    dataset: SyntheticDataset,
    scenario: OffloadingScenario,
    method: str,
    optimizer_seed: int,
    link_rate_factor: float,
    evaluation: PlanEvaluation,
    *,
    plan_evaluations: int,
    ga_evaluations: int,
    accepted_worse: int,
    elapsed: float,
    caps: Mapping[str, float],
    uncertainties: Mapping[str, float],
) -> dict:
    cap_excess = [
        max(0.0, task.decision.offloading_ratio - caps[task.decision.task_id])
        for task in evaluation.tasks
        if task.decision.server_id is not None
    ]
    uncertainty_exposure = sum(
        task.offloading_risk * uncertainties[task.decision.task_id]
        for task in evaluation.tasks
    )
    return {
        "method": method,
        "data_seed": dataset.configuration.experiment.random_seed,
        "optimizer_seed": optimizer_seed,
        "link_rate_factor": link_rate_factor,
        "sha256": dataset_fingerprint(dataset),
        "locations": json.dumps(_locations(evaluation, scenario)),
        "ratios": json.dumps(
            [task.decision.offloading_ratio for task in evaluation.tasks]
        ),
        "objective": evaluation.objective.value,
        "total_latency_seconds": evaluation.total_latency_seconds,
        "total_security_risk": evaluation.total_security_risk,
        "uncertainty_weighted_exposure": uncertainty_exposure,
        "load_variance": evaluation.objective.load_variance,
        "mean_offloading_ratio": mean(
            task.decision.offloading_ratio for task in evaluation.tasks
        ),
        "mean_allowed_cap": mean(caps.values()),
        "max_cap_excess": max(cap_excess, default=0.0),
        "search_seconds": elapsed,
        "plan_evaluations": plan_evaluations,
        "ga_evaluations": ga_evaluations,
        "accepted_worse": accepted_worse,
        "latency_normalizer": evaluation.normalization.latency_seconds,
        "risk_normalizer": evaluation.normalization.security_risk,
        **asdict(evaluation.objective),
    }


def compare_pipelines(
    dataset: SyntheticDataset,
    optimizer_seed: int,
    *,
    genetic_config: GeneticSearchConfig,
    swarm_config: SwarmSearchConfig,
    link_rate_factor: float = 1.0,
) -> list[dict]:
    """Run a paired baseline/proposed BOALBFS comparison under one condition."""

    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    validate_integer(optimizer_seed, "optimizer_seed")
    if not isinstance(genetic_config, GeneticSearchConfig):
        raise TypeError("genetic_config must be a GeneticSearchConfig")
    if not isinstance(swarm_config, SwarmSearchConfig):
        raise TypeError("swarm_config must be a SwarmSearchConfig")
    validate_positive(link_rate_factor, "link_rate_factor")

    caps = derive_task_caps(dataset)
    uncertainties = derive_task_uncertainties(dataset)
    scenario = scaled_scenario(dataset.scenario, link_rate_factor)
    normalization = derive_normalization(scenario)
    results = {}
    # Alternating run order prevents one method always receiving a warmer machine.
    order = METHODS if optimizer_seed % 2 == 0 else METHODS[::-1]
    for method in order:
        state = create_random_state(optimizer_seed)
        start = perf_counter()
        outcome = solve_boalbfs(
            scenario,
            normalization=normalization,
            random_state=state,
            genetic_config=genetic_config,
            swarm_config=swarm_config,
            ratio_caps=caps if method == METHODS[1] else None,
        )
        results[method] = (outcome, perf_counter() - start)
    return [
        _row(
            dataset,
            scenario,
            method,
            optimizer_seed,
            link_rate_factor,
            outcome.genetic.best,
            plan_evaluations=outcome.plan_evaluations,
            ga_evaluations=outcome.genetic.evaluations,
            accepted_worse=outcome.accepted_worse,
            elapsed=elapsed,
            caps=caps,
            uncertainties=uncertainties,
        )
        for method, (outcome, elapsed) in ((m, results[m]) for m in METHODS)
    ]


def summarize(rows: Sequence[Mapping[str, object]]) -> list[dict]:
    """Average optimizer repeats before treating datasets as observations."""

    summaries = []
    for factor in sorted({float(row["link_rate_factor"]) for row in rows}):
        for method in METHODS:
            group = [
                row
                for row in rows
                if row["method"] == method and float(row["link_rate_factor"]) == factor
            ]
            seeds = sorted({int(row["data_seed"]) for row in group})
            for metric in METRICS:
                dataset_means = [
                    mean(
                        float(row[metric])
                        for row in group
                        if int(row["data_seed"]) == seed
                    )
                    for seed in seeds
                ]
                summaries.append(
                    {
                        "method": method,
                        "link_rate_factor": factor,
                        "metric": metric,
                        "mean": mean(dataset_means),
                        "sd_between_datasets": stdev(dataset_means)
                        if len(dataset_means) > 1
                        else None,
                        "datasets": len(dataset_means),
                        "runs": len(group),
                    }
                )
    return summaries


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _policy_hand_example() -> dict:
    """Show the controller's intended distinction at identical security level."""

    narrow = TriangularFuzzyNumber(0.7, 0.7, 0.7)
    wide = TriangularFuzzyNumber(0.4, 0.7, 1.0)
    narrow_perspectives = SecurityPerspectives(narrow, narrow, narrow)
    wide_perspectives = SecurityPerspectives(wide, wide, wide)
    return {
        "security_level": 0.7,
        "narrow_triangle": [narrow.low, narrow.modal, narrow.high],
        "wide_triangle": [wide.low, wide.modal, wide.high],
        "narrow_uncertainty": calculate_aggregate_assessment_uncertainty(
            narrow_perspectives
        ),
        "wide_uncertainty": calculate_aggregate_assessment_uncertainty(
            wide_perspectives
        ),
    }


def _add_hand_example_caps(example: dict) -> dict:
    """Keep controller outputs beside the human-readable triangles."""

    example = dict(example)
    example["narrow_allowed_offloading_ratio"] = evaluate_uncertainty_aware_offloading(
        example["security_level"], example["narrow_uncertainty"]
    ).allowed_offloading_ratio
    example["wide_allowed_offloading_ratio"] = evaluate_uncertainty_aware_offloading(
        example["security_level"], example["wide_uncertainty"]
    ).allowed_offloading_ratio
    return example


def _plot(path: Path, summaries: Sequence[Mapping[str, object]]) -> None:
    factors = sorted({float(row["link_rate_factor"]) for row in summaries})
    figure = Figure(figsize=(11, 7), layout="constrained")
    FigureCanvasAgg(figure)
    panels = (
        ("objective", "Objective F", "Lower is better"),
        ("total_latency_seconds", "Total modeled latency", "Seconds"),
        ("total_security_risk", "Paper-model offloading risk", "Score"),
        (
            "uncertainty_weighted_exposure",
            "Uncertainty-weighted exposure",
            "Diagnostic score",
        ),
    )
    lookup = {
        (row["method"], float(row["link_rate_factor"]), row["metric"]): row
        for row in summaries
    }
    positions = np.arange(len(factors))
    width = 0.34
    for axis, (metric, title, ylabel) in zip(
        figure.subplots(2, 2).flat, panels, strict=True
    ):
        for offset, (method, color) in enumerate(
            zip(METHODS, ("#626a73", "#16896b"), strict=True)
        ):
            rows = [lookup[(method, factor, metric)] for factor in factors]
            values = [float(row["mean"]) for row in rows]
            errors = [
                0.0
                if row["sd_between_datasets"] is None
                else float(row["sd_between_datasets"])
                for row in rows
            ]
            axis.bar(
                positions + (offset - 0.5) * width,
                values,
                width,
                yerr=errors,
                capsize=3,
                color=color,
                label=method,
            )
        axis.set_title(title)
        axis.set_ylabel(ylabel)
        axis.set_xticks(positions, [f"{factor:g}x" for factor in factors])
        axis.set_xlabel("Wireless link-rate sensitivity factor")
        axis.grid(axis="y", alpha=0.2)
        axis.set_axisbelow(True)
    figure.axes[0].legend(loc="best", fontsize=8)
    figure.suptitle(
        "Baseline vs uncertainty-aware Mamdani policy\n"
        "Dataset means; error bars = sample SD between dataset means"
    )
    figure.savefig(path, dpi=160)


def run_experiment(
    output: Path,
    *,
    data_seeds: Sequence[int] = DEFAULT_DATA_SEEDS,
    optimizer_seeds: Sequence[int] = (0, 1, 2),
    scenario_config: SyntheticScenarioConfig | None = None,
    genetic_config: GeneticSearchConfig | None = None,
    swarm_config: SwarmSearchConfig | None = None,
    link_rate_factors: Sequence[float] = (1.0,),
) -> list[dict]:
    """Persist a replayable controlled comparison without overwriting output."""

    output = Path(output)
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    data_seeds = _validate_seeds(data_seeds, "data_seeds")
    optimizer_seeds = _validate_seeds(optimizer_seeds, "optimizer_seeds")
    link_rate_factors = _validate_factors(link_rate_factors)
    scenario_config = scenario_config or SyntheticScenarioConfig()
    genetic_config = genetic_config or GeneticSearchConfig(
        population_size=12, generations=8
    )
    swarm_config = swarm_config or SwarmSearchConfig(iterations=15)
    for value, expected in (
        (scenario_config, SyntheticScenarioConfig),
        (genetic_config, GeneticSearchConfig),
        (swarm_config, SwarmSearchConfig),
    ):
        if not isinstance(value, expected):
            raise TypeError(f"configuration must be a {expected.__name__}")

    root = Path(__file__).resolve().parents[2]
    sources = sorted(
        (
            *root.joinpath("src").rglob("*.py"),
            *root.joinpath("experiments").rglob("*.py"),
        )
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "datasets").mkdir()
    manifest = {
        "experiment": "uncertainty-aware-mamdani-v1",
        "status": "running",
        "methods": list(METHODS),
        "data_seeds": list(data_seeds),
        "optimizer_seeds": list(optimizer_seeds),
        "link_rate_factors": list(link_rate_factors),
        "scenario_config": asdict(scenario_config),
        "genetic_config": asdict(genetic_config),
        "swarm_config": asdict(swarm_config),
        "objective_weights": asdict(ObjectiveConfig()),
        "load_weights": asdict(LoadBalanceConfig()),
        "controller": {
            "type": "Type-1 Mamdani, min-max inference, centroid defuzzification",
            "inputs": ["paper-derived security level", "aggregated-TFN spread"],
            "output": "per-task allowed offloading-ratio cap",
        },
        "control": "same generated dataset, scaled scenario, normalization, optimizer seed, and GA/SA-PSO budgets per pair",
        "uncertainty_weighted_exposure": "sum(task offloading risk * assessment spread); diagnostic, not an attack probability or paper metric",
        "statistics": "mean optimizer repeats within a dataset, then mean/sample SD across independent dataset means",
        "link_sensitivity": "All link factors are recorded synthetic sensitivity conditions; factor 1 is the base scenario.",
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
            "platform": platform.platform(),
        },
        "source_sha256": {
            str(path.relative_to(root)).replace("\\", "/"): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sources
        },
    }
    _write_json(output / "manifest.json", manifest)
    rows = []
    for data_seed in data_seeds:
        dataset = generate_synthetic_dataset(
            replace(
                scenario_config,
                experiment=replace(scenario_config.experiment, random_seed=data_seed),
            )
        )
        write_dataset(dataset, output / "datasets" / f"seed_{data_seed}.json")
        for factor in link_rate_factors:
            for optimizer_seed in optimizer_seeds:
                rows.extend(
                    compare_pipelines(
                        dataset,
                        optimizer_seed,
                        genetic_config=genetic_config,
                        swarm_config=swarm_config,
                        link_rate_factor=factor,
                    )
                )
    summaries = summarize(rows)
    _write_csv(output / "runs.csv", rows)
    _write_csv(output / "summary.csv", summaries)
    _write_json(
        output / "hand_example.json", _add_hand_example_caps(_policy_hand_example())
    )
    _plot(output / "comparison.png", summaries)
    manifest["status"] = "complete"
    manifest["artifact_sha256"] = {
        str(path.relative_to(output)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    _write_json(output / "manifest.json", manifest)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tasks", type=int, default=60)
    parser.add_argument("--servers", type=int, default=3)
    parser.add_argument(
        "--data-seeds", type=int, nargs="+", default=list(DEFAULT_DATA_SEEDS)
    )
    parser.add_argument("--optimizer-seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--link-rate-factors", type=float, nargs="+", default=[1.0])
    parser.add_argument("--population", type=int, default=12)
    parser.add_argument("--generations", type=int, default=8)
    parser.add_argument("--particles", type=int, default=8)
    parser.add_argument("--pso-iterations", type=int, default=15)
    args = parser.parse_args()
    try:
        rows = run_experiment(
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
            link_rate_factors=tuple(args.link_rate_factors),
        )
    except (TypeError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "output": str(args.output.resolve()),
                "runs": len(rows),
                "methods": list(METHODS),
                "factors": list(args.link_rate_factors),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
