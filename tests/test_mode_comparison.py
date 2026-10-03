import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from math import sqrt
from pathlib import Path
from random import Random

import pytest

from experiments.baseline import mode_comparison as experiment
from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, read_dataset
from src.evaluation import evaluate_plan
from src.optimizers.genetic import _mutate
from src.synthetic import generate_synthetic_dataset

GA = GeneticSearchConfig(population_size=4, generations=2)
SWARM = SwarmSearchConfig(particle_count=3, iterations=3)
SMALL = replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))


def test_modes_share_inputs_and_scales_obey_restrictions_and_replay() -> None:
    dataset = generate_synthetic_dataset(SMALL)
    first = experiment.compare_modes(dataset, 0, genetic_config=GA, swarm_config=SWARM)
    second = experiment.compare_modes(dataset, 0, genetic_config=GA, swarm_config=SWARM)
    assert tuple(replace(r, search_seconds=0.0) for r in first) == tuple(
        replace(r, search_seconds=0.0) for r in second
    )
    local, edge, hybrid = first
    assert {r.sha256 for r in first} == {dataset_fingerprint(dataset)}
    assert all(r.evaluation.normalization == dataset.normalization for r in first)
    assert all(
        t.decision.server_id is None and t.decision.offloading_ratio == 0.0
        for t in local.evaluation.tasks
    )
    assert all(
        t.decision.server_id is not None and t.decision.offloading_ratio == 1.0
        for t in edge.evaluation.tasks
    )
    assert edge.ga_evaluations == edge.plan_evaluations == GA.evaluation_budget
    assert hybrid.ga_evaluations == GA.evaluation_budget
    assert hybrid.plan_evaluations <= GA.evaluation_budget * SWARM.evaluation_budget
    assert hybrid.evaluation.objective.value <= local.evaluation.objective.value
    assert edge.evaluation.objective.normalized_risk == pytest.approx(1.0)
    # With our equal weights and risk scale, full Edge cannot beat Local.
    assert edge.evaluation.objective.value > local.evaluation.objective.value


def test_failed_edge_initialization_is_missing_not_zero_or_proven_infeasibility() -> (
    None
):
    config = replace(SMALL, server_cpu_capacity_cycles_per_second=5e9)
    runs = experiment.compare_modes(
        generate_synthetic_dataset(config), 0, genetic_config=GA, swarm_config=SWARM
    )
    edge = runs[1]
    assert edge.status == "no_feasible_initial_plan"
    assert "not proof" in edge.reason
    assert edge.evaluation is None
    assert (
        edge.plan_evaluations == edge.ga_evaluations == edge.infeasible_evaluations == 1
    )
    row = experiment.run_rows(runs)[1]
    assert row["objective"] is None
    summary = next(
        s
        for s in experiment.summarize(experiment.run_rows(runs))
        if s["mode"] == "Edge" and s["metric"] == "objective"
    )
    assert summary["mean"] is None
    assert summary["complete_datasets"] == summary["feasible_runs"] == 0


def test_server_only_mutation_never_produces_local_and_handles_one_server() -> None:
    assert _mutate((1, 1), 1, 1.0, Random(0), allow_local=False) == (1, 1)
    assert _mutate((1, 2, 3), 3, 1.0, Random(0), allow_local=False) == (3, 3, 2)


def test_statistics_use_independent_dataset_means_not_repeats_as_independent_data() -> (
    None
):
    rows = [
        {
            "mode": mode,
            "data_seed": seed,
            "status": "feasible",
            **{metric: value for metric in experiment.METRICS},
        }
        for mode in experiment.MODES
        for seed, values in ((7, (1.0, 3.0)), (42, (5.0, 7.0)))
        for value in values
    ]
    summary = experiment.summarize(rows)[0]
    assert summary["mean"] == 4.0
    assert summary["sd_between_datasets"] == pytest.approx(sqrt(8))
    assert summary["mean_sd_within_dataset"] == pytest.approx(sqrt(2))
    assert summary["complete_datasets"] == 2
    assert summary["total_runs"] == 4
    rows[2]["status"] = "no_feasible_initial_plan"
    summary = experiment.summarize(rows)[0]
    assert summary["mean"] == 2.0
    assert summary["sd_between_datasets"] is None
    assert summary["complete_datasets"] == 1


def test_result_bundle_is_auditable_and_does_not_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "experiment"
    runs = experiment.run_experiment(
        output,
        data_seeds=(7, 42),
        optimizer_seeds=(0, 1),
        scenario_config=SMALL,
        genetic_config=GA,
        swarm_config=SWARM,
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["ga_evaluation_budget_per_search"] == GA.evaluation_budget
    assert "experiments/baseline/mode_comparison.py" in manifest["source_sha256"]
    for path, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
    for run in runs:
        dataset = read_dataset(output / "datasets" / f"seed_{run.data_seed}.json")
        assert run.sha256 == dataset_fingerprint(dataset)
        replay = evaluate_plan(
            dataset.scenario,
            tuple(t.decision for t in run.evaluation.tasks),
            normalization=dataset.normalization,
        )
        assert replay == run.evaluation
    with (output / "runs.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len(runs) == 12
    assert float(rows[2]["gain_vs_local_percent"]) == pytest.approx(
        100
        * (runs[0].evaluation.objective.value - runs[2].evaluation.objective.value)
        / runs[0].evaluation.objective.value
    )
    assert (output / "comparison.png").read_bytes().startswith(b"\x89PNG")
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        experiment.run_experiment(output)
    assert (output / "manifest.json").read_bytes() == before


@pytest.mark.parametrize("seeds", [(), (1, 1), (-1,), (True,)])
def test_invalid_seed_lists_fail_before_writing(tmp_path: Path, seeds: tuple) -> None:
    output = tmp_path / "invalid"
    with pytest.raises((TypeError, ValueError)):
        experiment.run_experiment(output, data_seeds=seeds)
    assert not output.exists()


def test_unexpected_errors_propagate_instead_of_becoming_failed_mode_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*args, **kwargs):
        raise ValueError("bad calculation")

    monkeypatch.setattr(experiment, "search_locations", broken)
    with pytest.raises(ValueError, match="bad calculation"):
        experiment.compare_modes(
            generate_synthetic_dataset(SMALL), 0, genetic_config=GA, swarm_config=SWARM
        )


def test_cli_runs_single_server_and_rejects_duplicate_seeds_before_writing(
    tmp_path: Path,
) -> None:
    command = [sys.executable, "-B", "-m", "experiments.baseline.mode_comparison"]
    output = tmp_path / "cli"
    result = subprocess.run(
        command
        + [
            "--output",
            str(output),
            "--tasks",
            "3",
            "--servers",
            "1",
            "--data-seeds",
            "42",
            "--optimizer-seeds",
            "0",
            "--population",
            "4",
            "--generations",
            "2",
            "--particles",
            "3",
            "--pso-iterations",
            "3",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["feasible_runs"] == 3
    invalid_output = tmp_path / "invalid_cli"
    invalid = subprocess.run(
        command + ["--output", str(invalid_output), "--data-seeds", "42", "42"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        timeout=30,
        check=False,
    )
    assert invalid.returncode == 2
    assert not invalid_output.exists()
