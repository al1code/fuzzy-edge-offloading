"""Small adapters from the existing numerical engine to the local dashboard."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from time import perf_counter

from src.config import (
    FuzzySecurityConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    SwarmSearchConfig,
)
from src.dataset_io import dataset_fingerprint, dataset_to_json, read_dataset
from src.evaluation import PlanEvaluation, derive_normalization, evaluate_plan
from src.fuzzy_security import SecurityPerspectives, assess_security
from src.objective import ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.optimizers.genetic import search_locations
from src.optimizers.locations import evaluate_locations_exact, validate_locations
from src.optimizers.sapso import solve_boalbfs
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from src.synthetic import SyntheticDataset
from src.validation import validate_non_negative

METHODS = ("Local", "Edge", "BOALBFS", "Analytical", "Exact")
MAX_EXACT_CANDIDATES = 5000
MAX_PLAN_BUDGET = 100000


@dataclass(frozen=True)
class DashboardRun:
    method: str
    evaluation: PlanEvaluation
    search_seconds: float
    ga_evaluations: int = 0
    plan_evaluations: int = 1
    endpoint_tests: int = 0
    infeasible_evaluations: int = 0
    history: tuple[float, ...] = ()


def run_method(
    dataset: SyntheticDataset,
    method: str,
    *,
    seed: int,
    genetic: GeneticSearchConfig,
    swarm: SwarmSearchConfig,
    objective: ObjectiveConfig,
    load: LoadBalanceConfig,
) -> DashboardRun:
    """Use the same dataset/scales/weights; guard interactive search budgets."""
    if method not in METHODS:
        raise ValueError(f"unknown method: {method}")
    if (
        method == "BOALBFS"
        and genetic.evaluation_budget * swarm.evaluation_budget > MAX_PLAN_BUDGET
    ):
        raise ValueError(f"interactive plan budget exceeds {MAX_PLAN_BUDGET}")
    state = create_random_state(seed)
    scenario = dataset.scenario
    options = {
        "normalization": dataset.normalization,
        "objective_config": objective,
        "load_config": load,
    }
    endpoint_tests = 0

    def evaluator(locations: tuple[int, ...]) -> PlanEvaluation:
        nonlocal endpoint_tests
        if method == "Edge":
            return evaluate_plan(
                scenario,
                tuple(
                    OffloadingDecision(
                        t.task.task_id, 1.0, scenario.servers[g - 1].server.server_id
                    )
                    for t, g in zip(scenario.tasks, locations, strict=True)
                ),
                **options,
            )
        endpoint_tests += 2 * sum(g != 0 for g in locations)
        return evaluate_locations_exact(scenario, locations, **options)

    start = perf_counter()
    if method == "Local":
        plan = evaluate_plan(
            scenario,
            tuple(OffloadingDecision(t.task.task_id, 0.0) for t in scenario.tasks),
            **options,
        )
        return DashboardRun(method, plan, perf_counter() - start)
    if method == "Exact":
        result = solve_exact(scenario, max_candidates=MAX_EXACT_CANDIDATES, **options)
        return DashboardRun(
            method,
            result.best,
            perf_counter() - start,
            plan_evaluations=result.candidates_checked,
            infeasible_evaluations=result.infeasible_candidates,
        )
    if method == "BOALBFS":
        result = solve_boalbfs(
            scenario,
            random_state=state,
            genetic_config=genetic,
            swarm_config=swarm,
            **options,
        )
        search, calls = result.genetic, result.plan_evaluations
    else:
        search = search_locations(
            scenario,
            evaluator,
            random_state=state,
            config=genetic,
            allow_local=method != "Edge",
        )
        calls = search.evaluations
    return DashboardRun(
        method,
        search.best,
        perf_counter() - start,
        search.evaluations,
        calls,
        endpoint_tests,
        search.infeasible_evaluations,
        tuple(h.best_objective_value for h in search.history),
    )


def evaluate_manual(
    dataset: SyntheticDataset,
    records: Sequence[dict],
    *,
    objective: ObjectiveConfig,
    load: LoadBalanceConfig,
) -> DashboardRun:
    servers = {s.server.server_id for s in dataset.scenario.servers}
    for record in records:
        if record["server"] != "Local" and record["server"] not in servers:
            raise ValueError("server must be Local or a scenario server")
        validate_non_negative(record["ratio_percent"], "ratio_percent")
    decisions = tuple(
        OffloadingDecision(
            r["task_id"],
            r["ratio_percent"] / 100,
            None if r["server"] == "Local" else r["server"],
        )
        for r in records
    )
    start = perf_counter()
    plan = evaluate_plan(
        dataset.scenario,
        decisions,
        normalization=dataset.normalization,
        objective_config=objective,
        load_config=load,
    )
    return DashboardRun("Manual", plan, perf_counter() - start)


def update_assessment(
    dataset: SyntheticDataset,
    index: int,
    assessments: Sequence[SecurityPerspectives],
    *,
    expert_weights: Sequence[float],
    perspective_config: FuzzySecurityConfig,
    threshold: float,
) -> SyntheticDataset:
    """Recompute all scores affected by shared weights, then fix new scales.

    CPU/link draws remain unchanged. Rebuilt typed snapshots validate consistency;
    the UI must discard previous runs because the input fingerprint has changed.
    """
    if not 0 <= index < len(dataset.scenario.tasks):
        raise ValueError("invalid task index")
    raw = list(dataset.expert_assessments)
    raw[index] = tuple(assessments)
    config = replace(
        dataset.configuration,
        expert_weights=tuple(expert_weights),
        security=perspective_config,
        security_threshold=threshold,
    )
    tasks = tuple(
        replace(
            t,
            security_level=assess_security(
                a,
                expert_weights=config.expert_weights,
                security_threshold=threshold,
                config=perspective_config,
            ).security_level,
        )
        for t, a in zip(dataset.scenario.tasks, raw, strict=True)
    )
    scenario = replace(dataset.scenario, tasks=tasks, security_threshold=threshold)
    return replace(
        dataset,
        configuration=config,
        scenario=scenario,
        expert_assessments=tuple(raw),
        normalization=derive_normalization(scenario),
    )


def plan_rows(plan: PlanEvaluation) -> list[dict]:
    return [
        {
            "task_id": t.decision.task_id,
            "server": t.decision.server_id or "Local",
            "ratio_percent": t.decision.offloading_ratio * 100,
            "local_seconds": t.latency.local_seconds,
            "transmission_seconds": t.latency.transmission_seconds,
            "edge_seconds": t.latency.edge_seconds,
            "total_seconds": t.latency.total_seconds,
            "security_risk": t.security_risk,
            "offloading_risk": t.offloading_risk,
        }
        for t in plan.tasks
    ]


def summary_row(run: DashboardRun) -> dict:
    p = run.evaluation
    return {
        "method": run.method,
        "objective": p.objective.value,
        "latency_seconds": p.total_latency_seconds,
        "model_risk": p.total_security_risk,
        "load_variance": p.objective.load_variance,
        "search_seconds": run.search_seconds,
        "ga_evaluations": run.ga_evaluations,
        "plan_evaluations": run.plan_evaluations,
        "endpoint_tests": run.endpoint_tests,
        "infeasible_evaluations": run.infeasible_evaluations,
    }


def context_key(dataset, objective, load, genetic, swarm, seed) -> str:
    """Tie displayed runs to the exact inputs and optimizer settings."""
    return json.dumps(
        [
            dataset_fingerprint(dataset),
            asdict(objective),
            asdict(load),
            asdict(genetic),
            asdict(swarm),
            seed,
        ],
        sort_keys=True,
        allow_nan=False,
    )


def export_run(
    dataset,
    run,
    *,
    objective,
    load,
    genetic,
    swarm,
    seed,
    edits=False,
    source="generated",
) -> str:
    payload = {
        "kind": "gui_run_not_published_experiment",
        "schema_version": 1,
        "dataset": json.loads(dataset_to_json(dataset)),
        "summary": summary_row(run),
        "plan": asdict(run.evaluation),
        "decisions": plan_rows(run.evaluation),
        "best_history": run.history,
        "objective_config": asdict(objective),
        "load_config": asdict(load),
        "genetic_config": asdict(genetic),
        "swarm_config": asdict(swarm),
        "optimizer_seed": seed,
        "manual_fuzzy_edits": edits,
        "input_source": source,
        "python": platform.python_version(),
    }
    return json.dumps(payload, indent=2, allow_nan=False)


def list_bundles(root: Path) -> list[Path]:
    return sorted(
        p.parent for p in (root / "results").glob("*/manifest.json") if p.is_file()
    )


def _bundle_file(folder: Path, name: str) -> Path:
    path = (folder / name).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError("artifact path leaves experiment directory")
    return path


def load_bundle(folder: Path) -> tuple[dict, list[dict]]:
    """Verify saved output bytes before presenting them as experiment evidence."""
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise ValueError("experiment is incomplete")
    hashes = manifest.get("artifact_sha256")
    if not isinstance(hashes, dict) or "runs.csv" not in hashes:
        raise ValueError("missing experiment artifact hashes")
    for name, digest in hashes.items():
        if (
            hashlib.sha256(_bundle_file(folder, name).read_bytes()).hexdigest()
            != digest
        ):
            raise ValueError(f"artifact checksum mismatch: {name}")
    with (folder / "runs.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("experiment has no records")
    return manifest, rows


def restore_bundle_run(folder: Path, row: dict, manifest: dict):
    dataset = read_dataset(
        _bundle_file(folder, f"datasets/seed_{int(row['data_seed'])}.json")
    )
    if dataset_fingerprint(dataset) != row["sha256"]:
        raise ValueError("run/dataset fingerprint mismatch")
    if "locations" in row:
        genes = validate_locations(dataset.scenario, json.loads(row["locations"]))
        ratios = json.loads(row["ratios"])
        decisions = tuple(
            OffloadingDecision(
                t.task.task_id,
                x,
                None if g == 0 else dataset.scenario.servers[g - 1].server.server_id,
            )
            for t, g, x in zip(dataset.scenario.tasks, genes, ratios, strict=True)
        )
        history = tuple(json.loads(row.get("best_history", "[]")))
    else:
        records = json.loads(
            _bundle_file(folder, "runs.json").read_text(encoding="utf-8")
        )
        record = next(
            r
            for r in records
            if str(r["data_seed"]) == row["data_seed"]
            and str(r["optimizer_seed"]) == row["optimizer_seed"]
            and r["mode"] == row["mode"]
        )
        if record["evaluation"] is None:
            raise ValueError("selected run has no feasible plan")
        decisions = tuple(
            OffloadingDecision(**t["decision"]) for t in record["evaluation"]["tasks"]
        )
        history = tuple(h["best_objective_value"] for h in record["history"])
    objective = ObjectiveConfig(**manifest["objective_weights"])
    load = LoadBalanceConfig(**manifest["load_weights"])
    evaluation = evaluate_plan(
        dataset.scenario,
        decisions,
        normalization=dataset.normalization,
        objective_config=objective,
        load_config=load,
    )
    for field, actual in {
        "objective": evaluation.objective.value,
        "total_latency_seconds": evaluation.total_latency_seconds,
        "total_security_risk": evaluation.total_security_risk,
        "load_variance": evaluation.objective.load_variance,
        "normalized_latency": evaluation.objective.normalized_latency,
        "normalized_risk": evaluation.objective.normalized_risk,
    }.items():
        if field in row and actual != float(row[field]):
            raise ValueError(f"replayed {field} differs from saved run")
    return dataset, DashboardRun(
        row.get("method", row.get("mode")),
        evaluation,
        float(row["search_seconds"]),
        int(row.get("ga_evaluations") or 0),
        int(row["plan_evaluations"]),
        int(row.get("endpoint_tests") or 0),
        int(row.get("infeasible_evaluations") or 0),
        history,
    )


def bundle_statistics(rows: list[dict]) -> list[dict]:
    """Reuse the experiment's aggregation, including incomplete-group exclusion."""
    if "method" in rows[0]:
        from experiments.proposed.ratio_comparison import summarize

        metrics_to_parse = (
            "objective",
            "search_seconds",
            "total_latency_seconds",
            "total_security_risk",
            "load_variance",
        )
        options = {
            "methods": tuple(dict.fromkeys(r["method"] for r in rows)),
            "metrics": metrics_to_parse,
        }
    else:
        from experiments.baseline.mode_comparison import METRICS, summarize

        metrics_to_parse = METRICS
        options = {}

    numeric = [
        {
            **row,
            **{
                field: float(row[field]) if row.get(field) else None
                for field in metrics_to_parse
            },
        }
        for row in rows
    ]
    summaries = summarize(numeric, **options)
    records = []
    method_field = "method" if "method" in rows[0] else "mode"
    for method in dict.fromkeys(row[method_field] for row in rows):
        metrics = {r["metric"]: r for r in summaries if r[method_field] == method}
        score = metrics["objective"]
        records.append(
            {
                "method": method,
                "F": score["mean"],
                "F_SD": score["sd_between_datasets"],
                "Arama_s": metrics["search_seconds"]["mean"],
                "Gorev_s": metrics["total_latency_seconds"]["mean"],
                "Risk": metrics["total_security_risk"]["mean"],
                "Yuk": metrics["load_variance"]["mean"],
                "Veri": score.get("complete_datasets", score.get("datasets")),
            }
        )
    return records
