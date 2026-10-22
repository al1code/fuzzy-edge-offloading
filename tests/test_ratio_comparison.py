import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import replace
from itertools import pairwise
from math import sqrt
from pathlib import Path

import pytest

from experiments.proposed import ratio_comparison as experiment
from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, read_dataset
from src.evaluation import evaluate_plan
from src.load_balance import CapacityExceededError
from src.optimizers.exact import solve_exact
from src.optimizers.genetic import solve_genetic
from src.optimizers.locations import evaluate_locations_exact
from src.random_utils import create_random_state
from src.scenario import OffloadingDecision
from src.synthetic import generate_synthetic_dataset

SMALL = replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))
SWARM = SwarmSearchConfig(particle_count=3, iterations=3)
GENETIC = GeneticSearchConfig(population_size=4, generations=2)


def _replay(dataset, row):
    locations, ratios = json.loads(row["locations"]), json.loads(row["ratios"])
    return evaluate_plan(
        dataset.scenario,
        tuple(
            OffloadingDecision(
                task.task.task_id,
                ratio,
                None
                if gene == 0
                else dataset.scenario.servers[gene - 1].server.server_id,
            )
            for task, gene, ratio in zip(
                dataset.scenario.tasks, locations, ratios, strict=True
            )
        ),
        normalization=dataset.normalization,
    )


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_pairs_share_inputs_and_locations_and_replay(seed: int) -> None:
    dataset = generate_synthetic_dataset(SMALL)
    rows = experiment.compare_ratios(dataset, seed, swarm_config=SWARM)
    again = experiment.compare_ratios(dataset, seed, swarm_config=SWARM)
    assert [{**r, "search_seconds": 0} for r in rows] == [
        {**r, "search_seconds": 0} for r in again
    ]
    swarm, exact = rows
    assert swarm["locations"] == exact["locations"] == "[1, 2, 1]"
    assert swarm["sha256"] == exact["sha256"] == dataset_fingerprint(dataset)
    assert swarm["load_variance"] == exact["load_variance"]
    assert swarm["zero_ratio_objective"] == exact["zero_ratio_objective"]
    zero = _replay(dataset, {**exact, "ratios": "[0.0, 0.0, 0.0]"})
    assert exact["zero_ratio_objective"] == zero.objective.value
    assert exact["objective"] <= zero.objective.value + 1e-12
    assert swarm["plan_evaluations"] == SWARM.evaluation_budget
    assert exact["plan_evaluations"] == 1
    assert exact["endpoint_tests"] == 2 * len(dataset.scenario.tasks)
    assert exact["objective"] <= swarm["objective"] + 1e-12
    assert swarm["gap_to_exact"] == swarm["objective"] - exact["objective"]
    assert set(json.loads(exact["ratios"])) <= {0.0, 1.0}
    for row in rows:
        result = _replay(dataset, row)
        assert result.objective.value == row["objective"]
        assert result.total_security_risk == row["total_security_risk"]
        assert result.normalization == dataset.normalization
        assert row["search_seconds"] >= 0.0


def test_all_local_and_selected_zero_preserve_location_semantics() -> None:
    dataset = generate_synthetic_dataset(SMALL)
    rows = experiment.compare_ratios(
        dataset, 0, swarm_config=SWARM, locations=(0, 0, 0)
    )
    assert all(r["plan_evaluations"] == 1 and r["endpoint_tests"] == 0 for r in rows)
    assert rows[0]["objective"] == rows[1]["objective"]
    assert rows[0]["objective"] == rows[0]["zero_ratio_objective"]
    exact = experiment.compare_ratios(dataset, 0, swarm_config=SWARM)[1]
    result = _replay(dataset, exact)
    assert any(
        t.decision.offloading_ratio == 0 and t.decision.server_id is not None
        for t in result.tasks
    )
    assert any(server.load.weighted_load > 0 for server in result.servers)


def test_policy_ratio_comparison_pairs_baseline_and_mamdani() -> None:
    dataset = generate_synthetic_dataset(SMALL)
    rows = experiment.compare_policy_ratios(dataset, 0, swarm_config=SWARM)

    assert [row["method"] for row in rows] == list(experiment.POLICY_METHODS)
    baseline_sapso, baseline_exact, capped_sapso, capped_exact = rows
    assert {row["sha256"] for row in rows} == {dataset_fingerprint(dataset)}
    assert all(row["locations"] == "[1, 2, 1]" for row in rows)
    assert baseline_sapso["mean_allowed_cap"] == capped_sapso["mean_allowed_cap"]
    assert baseline_exact["mean_allowed_cap"] == capped_exact["mean_allowed_cap"]
    assert capped_sapso["max_cap_excess"] == 0.0
    assert capped_exact["max_cap_excess"] == 0.0
    assert baseline_sapso["plan_evaluations"] == capped_sapso["plan_evaluations"]
    assert baseline_exact["endpoint_tests"] == capped_exact["endpoint_tests"]
    assert capped_exact["objective"] >= baseline_exact["objective"]
    assert capped_exact["uncertainty_weighted_exposure"] <= (
        baseline_exact["uncertainty_weighted_exposure"] + 1e-12
    )


def test_counts_are_real_calls_and_measurement_order_alternates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.optimizers import locations, sapso

    calls = {"SA-PSO": 0, "Analytical": 0}
    order = []
    for module, method in ((sapso, "SA-PSO"), (locations, "Analytical")):
        original = module.evaluate_plan

        def counted(*args, _method=method, _original=original, **kwargs):
            calls[_method] += 1
            order.append(_method)
            return _original(*args, **kwargs)

        monkeypatch.setattr(module, "evaluate_plan", counted)
    experiment.compare_ratios(generate_synthetic_dataset(SMALL), 1, swarm_config=SWARM)
    assert calls == {"SA-PSO": SWARM.evaluation_budget, "Analytical": 1}
    assert order[0] == "Analytical"


def test_summary_uses_dataset_means_not_repeats_as_independent_data() -> None:
    rows = [
        {
            "method": method,
            "data_seed": seed,
            **dict.fromkeys(experiment.METRICS, value),
        }
        for method in experiment.METHODS
        for seed, values in ((7, (1.0, 3.0)), (42, (5.0, 7.0)))
        for value in values
    ]
    summary = experiment.summarize(rows)[0]
    assert summary["mean"] == 4.0
    assert summary["sd_between_datasets"] == pytest.approx(sqrt(8))
    assert summary["datasets"] == 2 and summary["runs"] == 4
    one = experiment.summarize([r for r in rows if r["data_seed"] == 7])[0]
    assert one["sd_between_datasets"] is None


@pytest.mark.parametrize("scope", ["fixed", "pipeline"])
def test_saved_bundle_has_replayable_decisions_and_verified_hashes(
    tmp_path: Path,
    scope: str,
) -> None:
    output = tmp_path / "comparison"
    rows = experiment.run_experiment(
        output,
        data_seeds=(7, 42),
        optimizer_seeds=(0, 1),
        scenario_config=SMALL,
        swarm_config=SWARM,
        genetic_config=GENETIC,
        scope=scope,
    )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["methods"] == list(
        experiment.METHODS if scope == "fixed" else experiment.PIPELINE_METHODS
    )
    assert "experiments/proposed/ratio_comparison.py" in manifest["source_sha256"]
    for path, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
    with (output / "runs.csv").open(encoding="utf-8", newline="") as stream:
        saved = list(csv.DictReader(stream))
    assert len(rows) == len(saved) == 8
    for row in saved:
        dataset = read_dataset(output / "datasets" / f"seed_{row['data_seed']}.json")
        assert _replay(dataset, row).objective.value == float(row["objective"])
    assert (output / "comparison.png").read_bytes().startswith(b"\x89PNG")
    before = (output / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        experiment.run_experiment(output)
    assert (output / "manifest.json").read_bytes() == before


@pytest.mark.parametrize("field", ["data_seeds", "optimizer_seeds"])
@pytest.mark.parametrize("seeds", [(), (1, 1), (-1,), (True,)])
def test_invalid_seeds_fail_before_writing(
    tmp_path: Path, field: str, seeds: tuple
) -> None:
    output = tmp_path / "invalid"
    with pytest.raises((TypeError, ValueError)):
        experiment.run_experiment(output, **{field: seeds})
    assert not output.exists()


def test_infeasible_locations_and_other_errors_are_not_hidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = generate_synthetic_dataset(
        replace(SMALL, server_cpu_capacity_cycles_per_second=5e9)
    )
    with pytest.raises(CapacityExceededError):
        experiment.compare_ratios(dataset, 0, swarm_config=SWARM)

    def broken(*args, **kwargs):
        raise ValueError("bad calculation")

    monkeypatch.setattr(experiment, "solve_sapso", broken)
    with pytest.raises(ValueError, match="bad calculation"):
        experiment.compare_ratios(
            generate_synthetic_dataset(SMALL), 0, swarm_config=SWARM
        )


@pytest.mark.parametrize("scope", ["fixed", "pipeline"])
def test_cli_runs_small_experiment_and_rejects_existing_output(
    tmp_path: Path, scope: str
) -> None:
    output = tmp_path / "cli"
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-B",
        "-m",
        "experiments.proposed.ratio_comparison",
        "--output",
        str(output),
        "--scope",
        scope,
        "--population",
        "4",
        "--generations",
        "2",
        "--tasks",
        "3",
        "--servers",
        "2",
        "--data-seeds",
        "42",
        "--optimizer-seeds",
        "0",
        "--particles",
        "3",
        "--pso-iterations",
        "3",
    ]
    kwargs = {
        "capture_output": True,
        "encoding": "utf-8",
        "cwd": Path(__file__).resolve().parents[1],
        "timeout": 30,
    }
    result = subprocess.run(command, check=False, **kwargs)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["runs"] == 2
    assert subprocess.run(command, check=False, **kwargs).returncode == 2


def test_failed_run_is_not_marked_complete(tmp_path: Path) -> None:
    output = tmp_path / "infeasible"
    with pytest.raises(CapacityExceededError):
        experiment.run_experiment(
            output,
            data_seeds=(42,),
            optimizer_seeds=(0,),
            scenario_config=replace(SMALL, server_cpu_capacity_cycles_per_second=5e9),
            swarm_config=SWARM,
        )
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "running"
    assert not (output / "summary.csv").exists()


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_pipeline_pair_is_replayable_and_matches_existing_genetic_solver(
    seed: int,
) -> None:
    dataset = generate_synthetic_dataset(SMALL)
    kwargs = {"genetic_config": GENETIC, "swarm_config": SWARM}
    rows = experiment.compare_pipelines(dataset, seed, **kwargs)
    again = experiment.compare_pipelines(dataset, seed, **kwargs)
    assert [{**r, "search_seconds": 0} for r in rows] == [
        {**r, "search_seconds": 0} for r in again
    ]
    oracle = solve_exact(dataset.scenario, normalization=dataset.normalization)
    existing = solve_genetic(
        dataset.scenario,
        normalization=dataset.normalization,
        random_state=create_random_state(seed),
        config=GENETIC,
    )
    assert _replay(dataset, rows[1]) == existing.best
    for row in rows:
        result = _replay(dataset, row)
        assert result.objective.value == row["objective"]
        assert result.normalization == dataset.normalization
        assert row["sha256"] == dataset_fingerprint(dataset)
        assert row["ga_evaluations"] == GENETIC.evaluation_budget
        assert oracle.best.objective.value <= row["objective"] + 1e-12
        assert row["objective"] <= row["all_local_objective"] + 1e-12
        conditional = evaluate_locations_exact(
            dataset.scenario,
            json.loads(row["locations"]),
            normalization=dataset.normalization,
        )
        assert row["gap_to_exact"] == row["objective"] - conditional.objective.value
        history = json.loads(row["best_history"])
        assert len(history) == GENETIC.generations + 1
        assert history[-1] == row["objective"]
        assert all(b <= a for a, b in pairwise(history))
    assert rows[1]["gap_to_exact"] == 0
    assert (
        rows[1]["objective_delta_vs_sapso"]
        == rows[1]["objective"] - rows[0]["objective"]
    )
    assert rows[0]["all_local_objective"] == rows[1]["all_local_objective"]


def test_pipeline_counts_include_infeasible_candidates_but_exclude_post_checks(
    monkeypatch,
) -> None:
    from src.optimizers import locations, sapso

    phase = "controls"
    calls = {m: 0 for m in experiment.PIPELINE_METHODS + ("controls",)}
    endpoints = dict.fromkeys(calls, 0)
    order = []
    for module in (locations, sapso):
        original = module.evaluate_plan

        def counted(*args, _original=original, **kwargs):
            calls[phase] += 1
            return _original(*args, **kwargs)

        monkeypatch.setattr(module, "evaluate_plan", counted)
    original_latency = locations.calculate_task_latency

    def counted_latency(*args, **kwargs):
        endpoints[phase] += 1
        return original_latency(*args, **kwargs)

    monkeypatch.setattr(locations, "calculate_task_latency", counted_latency)
    for name, method in (
        ("solve_boalbfs", "GA+SA-PSO"),
        ("search_locations", "GA+Analytical"),
    ):
        original = getattr(experiment, name)

        def measured(*args, _method=method, _original=original, **kwargs):
            nonlocal phase
            phase = _method
            order.append(phase)
            try:
                return _original(*args, **kwargs)
            finally:
                phase = "controls"

        monkeypatch.setattr(experiment, name, measured)
    dataset = generate_synthetic_dataset(
        replace(SMALL, server_cpu_capacity_cycles_per_second=5e9)
    )
    rows = experiment.compare_pipelines(
        dataset, 1, genetic_config=GENETIC, swarm_config=SWARM
    )
    assert order == ["GA+Analytical", "GA+SA-PSO"]
    for row in rows:
        assert row["plan_evaluations"] == calls[row["method"]]
        assert row["endpoint_tests"] == endpoints[row["method"]]
        assert row["infeasible_evaluations"] > 0
    assert calls["GA+Analytical"] == GENETIC.evaluation_budget
    assert endpoints["GA+Analytical"] > 0
    assert (
        calls["controls"] == 1
    )  # conditional check only; other controls use shared evaluator


def test_pipeline_summary_retains_signed_paired_difference() -> None:
    rows = [
        {"method": method, "data_seed": seed, "objective_delta_vs_sapso": value}
        for method in experiment.PIPELINE_METHODS
        for seed, values in ((7, (-1.0, -3.0)), (42, (1.0, -1.0)))
        for value in values
    ]
    summary = experiment.summarize(
        rows, methods=experiment.PIPELINE_METHODS, metrics=("objective_delta_vs_sapso",)
    )
    assert summary[1]["mean"] == -1
    assert summary[1]["sd_between_datasets"] == pytest.approx(sqrt(2))


@pytest.mark.parametrize(
    "options", [{"scope": "invalid"}, {"genetic_config": "invalid"}]
)
def test_invalid_pipeline_options_fail_before_writing(tmp_path, options) -> None:
    output = tmp_path / "invalid"
    with pytest.raises((TypeError, ValueError)):
        experiment.run_experiment(output, **options)
    assert not output.exists()


def test_failed_pipeline_does_not_hide_calculation_errors(
    tmp_path, monkeypatch
) -> None:
    def broken(*args, **kwargs):
        raise ValueError("bad calculation")

    monkeypatch.setattr(experiment, "solve_boalbfs", broken)
    output = tmp_path / "failed"
    with pytest.raises(ValueError, match="bad calculation"):
        experiment.run_experiment(
            output,
            scope="pipeline",
            data_seeds=(42,),
            optimizer_seeds=(0,),
            scenario_config=SMALL,
            genetic_config=GENETIC,
            swarm_config=SWARM,
        )
    assert json.loads((output / "manifest.json").read_text())["status"] == "running"
    assert not (output / "summary.csv").exists()


def test_pipeline_time_plot_has_positive_limits_and_unclipped_labels(
    tmp_path, monkeypatch
) -> None:
    from matplotlib.figure import Figure

    figures = []
    original = Figure.savefig

    def captured(figure, *args, **kwargs):
        figures.append(figure)
        return original(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", captured)
    summary = [
        {
            "method": method,
            "metric": metric,
            "mean": value,
            "sd_between_datasets": error,
        }
        for method, time in zip(
            experiment.PIPELINE_METHODS, (10000.0, 200.0), strict=True
        )
        for metric, value, error in (
            ("objective", 0.238, 0.004),
            ("search_seconds", time / 1000, time / 100000),
        )
    ]
    experiment._plot(
        tmp_path / "plot.png",
        summary,
        methods=experiment.PIPELINE_METHODS,
        pipeline=True,
    )
    axis = figures[0].axes[1]
    lower, upper = axis.get_ylim()
    assert axis.get_yscale() == "log"
    assert 0 < lower < 198
    assert upper > 10100
    figures[0].canvas.draw()
    renderer = figures[0].canvas.get_renderer()
    title = axis.title.get_window_extent(renderer)
    for label in axis.texts:
        box = label.get_window_extent(renderer)
        assert not box.overlaps(title)
        assert box.y1 < title.y0
