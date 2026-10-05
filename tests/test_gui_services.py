"""The dashboard must preserve core mathematics and saved experiment evidence."""

import copy
import hashlib
import json
from dataclasses import replace

import pytest

from experiments.baseline.mode_comparison import run_experiment as run_modes
from experiments.proposed.ratio_comparison import run_experiment as run_ratios
from gui.services import (
    METHODS,
    bundle_statistics,
    context_key,
    evaluate_manual,
    export_run,
    load_bundle,
    plan_rows,
    restore_bundle_run,
    run_method,
    update_assessment,
)
from src.config import (
    ExperimentConfig,
    FuzzySecurityConfig,
    GeneticSearchConfig,
    LoadBalanceConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, dataset_from_json, dataset_to_json
from src.evaluation import evaluate_plan
from src.fuzzy_security import SecurityPerspectives, assess_security
from src.load_balance import CapacityExceededError
from src.models import TriangularFuzzyNumber
from src.objective import ObjectiveConfig
from src.optimizers.exact import solve_exact
from src.synthetic import generate_synthetic_dataset

SMALL = replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))
GA = GeneticSearchConfig(population_size=4, generations=2)
SWARM = SwarmSearchConfig(particle_count=3, iterations=3)
OPTIONS = {
    "seed": 0,
    "genetic": GA,
    "swarm": SWARM,
    "objective": ObjectiveConfig(),
    "load": LoadBalanceConfig(),
}


@pytest.fixture
def dataset():
    return generate_synthetic_dataset(SMALL)


@pytest.mark.parametrize("method", METHODS)
def test_methods_replay_and_are_repeatable(dataset, method):
    run = run_method(dataset, method, **OPTIONS)
    again = run_method(dataset, method, **OPTIONS)
    assert run.evaluation == again.evaluation
    assert run.history == again.history
    replay = evaluate_plan(
        dataset.scenario,
        tuple(t.decision for t in run.evaluation.tasks),
        normalization=dataset.normalization,
    )
    assert replay == run.evaluation
    assert run.search_seconds >= 0
    if method in ("Edge", "Analytical", "BOALBFS"):
        assert run.ga_evaluations == GA.evaluation_budget
    if method == "BOALBFS":
        assert (
            0 < run.plan_evaluations <= GA.evaluation_budget * SWARM.evaluation_budget
        )
    if method == "Analytical":
        assert run.plan_evaluations == GA.evaluation_budget
        assert (
            0
            < run.endpoint_tests
            <= 2 * SMALL.experiment.task_count * GA.evaluation_budget
        )
    if method == "Exact":
        assert (
            run.evaluation
            == solve_exact(dataset.scenario, normalization=dataset.normalization).best
        )
    if method == "Local":
        assert all(t.decision.server_id is None for t in run.evaluation.tasks)
    if method == "Edge":
        assert all(t.decision.offloading_ratio == 1 for t in run.evaluation.tasks)


@pytest.mark.parametrize("method", METHODS)
def test_custom_weights_reach_common_evaluator(dataset, method):
    objective = ObjectiveConfig(0.6, 0.3, 0.1)
    load = LoadBalanceConfig(0.2, 0.7, 0.1)
    run = run_method(
        dataset, method, **{**OPTIONS, "objective": objective, "load": load}
    )
    assert run.evaluation == evaluate_plan(
        dataset.scenario,
        tuple(t.decision for t in run.evaluation.tasks),
        normalization=dataset.normalization,
        objective_config=objective,
        load_config=load,
    )


def test_manual_plan_does_not_silently_clip_local_ratio(dataset):
    local = run_method(dataset, "Local", **OPTIONS)
    records = plan_rows(local.evaluation)
    assert (
        evaluate_manual(
            dataset, records, objective=OPTIONS["objective"], load=OPTIONS["load"]
        ).evaluation
        == local.evaluation
    )
    records[0]["ratio_percent"] = 25
    with pytest.raises(ValueError):
        evaluate_manual(
            dataset, records, objective=OPTIONS["objective"], load=OPTIONS["load"]
        )
    records[0]["server"] = dataset.scenario.servers[0].server.server_id
    records[0]["ratio_percent"] = 0
    selected = evaluate_manual(
        dataset, records, objective=OPTIONS["objective"], load=OPTIONS["load"]
    )
    assert (
        selected.evaluation.total_latency_seconds
        == local.evaluation.total_latency_seconds
    )
    assert selected.evaluation.servers[0].load.cpu_utilization > 0


def test_interactive_budgets_are_guarded(dataset):
    with pytest.raises(ValueError, match="unknown method"):
        run_method(dataset, "made-up", **OPTIONS)
    with pytest.raises(ValueError, match="budget"):
        run_method(
            dataset,
            "BOALBFS",
            **{
                **OPTIONS,
                "genetic": GeneticSearchConfig(population_size=30, generations=30),
                "swarm": SwarmSearchConfig(particle_count=24, iterations=60),
            },
        )
    large = generate_synthetic_dataset(
        replace(SMALL, experiment=ExperimentConfig(42, 6, 2))
    )
    with pytest.raises(ValueError):
        run_method(large, "Exact", **OPTIONS)


def test_manual_and_edge_capacity_failures_are_not_repaired():
    limited = generate_synthetic_dataset(
        replace(SMALL, server_cpu_capacity_cycles_per_second=10e9)
    )
    records = [
        {
            "task_id": t.task.task_id,
            "server": limited.scenario.servers[0].server.server_id,
            "ratio_percent": 0.0,
        }
        for t in limited.scenario.tasks
    ]
    with pytest.raises(CapacityExceededError):
        evaluate_manual(
            limited, records, objective=OPTIONS["objective"], load=OPTIONS["load"]
        )
    with pytest.raises(ValueError):
        run_method(limited, "Edge", **OPTIONS)


def test_fuzzy_edit_preserves_draws_and_rebuilds_all_shared_scores(dataset):
    raw = (SecurityPerspectives(*([TriangularFuzzyNumber(0.1, 0.2, 0.3)] * 3)),) * 3
    config = FuzzySecurityConfig(0.8, 0.1, 0.1)
    updated = update_assessment(
        dataset,
        0,
        raw,
        expert_weights=(0.6, 0.3, 0.1),
        perspective_config=config,
        threshold=0.8,
    )
    assert dataset_fingerprint(updated) != dataset_fingerprint(dataset)
    assert dataset_from_json(dataset_to_json(updated)) == updated
    assert updated.scenario.links == dataset.scenario.links
    assert updated.cpu_cycles_per_bit == dataset.cpu_cycles_per_bit
    assert updated.channel_gains == dataset.channel_gains
    assert updated.expert_assessments[1:] == dataset.expert_assessments[1:]
    for task, assessments in zip(
        updated.scenario.tasks, updated.expert_assessments, strict=True
    ):
        expected = assess_security(
            assessments,
            expert_weights=(0.6, 0.3, 0.1),
            security_threshold=0.8,
            config=config,
        )
        assert task.security_level == expected.security_level
    assert updated.normalization.security_risk != dataset.normalization.security_risk
    with pytest.raises(ValueError):
        update_assessment(
            dataset,
            -1,
            raw,
            expert_weights=(0.6, 0.3, 0.1),
            perspective_config=config,
            threshold=0.8,
        )


def test_export_is_a_complete_replayable_snapshot(dataset):
    run = run_method(dataset, "Analytical", **OPTIONS)
    payload = json.loads(export_run(dataset, run, **OPTIONS, edits=True))
    assert dataset_from_json(json.dumps(payload["dataset"])) == dataset
    assert payload["manual_fuzzy_edits"] is True
    assert payload["kind"] == "gui_run_not_published_experiment"
    assert payload["summary"]["objective"] == run.evaluation.objective.value
    assert payload["decisions"] == plan_rows(run.evaluation)
    key = context_key(dataset, OPTIONS["objective"], OPTIONS["load"], GA, SWARM, 0)
    assert key != context_key(
        dataset, OPTIONS["objective"], OPTIONS["load"], GA, SWARM, 1
    )
    assert key != context_key(
        dataset, ObjectiveConfig(0.6, 0.3, 0.1), OPTIONS["load"], GA, SWARM, 0
    )


@pytest.fixture(params=["fixed", "pipeline", "modes"])
def bundle(request, tmp_path):
    folder = tmp_path / "bundle"
    kwargs = {
        "data_seeds": (7,),
        "optimizer_seeds": (0, 1),
        "scenario_config": SMALL,
        "genetic_config": GA,
        "swarm_config": SWARM,
    }
    if request.param == "modes":
        run_modes(folder, **kwargs)
    else:
        run_ratios(folder, scope=request.param, **kwargs)
    manifest, rows = load_bundle(folder)
    return folder, manifest, rows


def test_saved_decisions_replay_with_all_metrics_and_statistics(bundle):
    folder, manifest, rows = bundle
    for row in rows:
        dataset, run = restore_bundle_run(folder, row, manifest)
        assert run.evaluation.objective.value == float(row["objective"])
        assert run.evaluation.normalization == dataset.normalization
    stats = bundle_statistics(rows)
    assert all(s["Veri"] == 1 and s["F_SD"] is None for s in stats)
    assert len(stats) == len({r.get("method", r.get("mode")) for r in rows})


def test_saved_metric_disagreement_is_rejected(bundle):
    folder, manifest, rows = bundle
    changed = {**rows[0], "total_security_risk": "999"}
    with pytest.raises(ValueError, match="replayed"):
        restore_bundle_run(folder, changed, manifest)
    if "locations" in rows[0]:
        changed = {**rows[0], "locations": "[-1, 1, 1]"}
        with pytest.raises(ValueError):
            restore_bundle_run(folder, changed, manifest)


def test_bundle_corruption_incomplete_and_path_traversal_are_rejected(bundle):
    folder, manifest, _ = bundle
    manifest_file = folder / "manifest.json"
    manifest_file.write_text(
        json.dumps({**manifest, "status": "running"}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="incomplete"):
        load_bundle(folder)
    outside = folder.parent / "outside.txt"
    outside.write_text("test", encoding="utf-8")
    unsafe = copy.deepcopy(manifest)
    unsafe["artifact_sha256"]["../outside.txt"] = hashlib.sha256(b"test").hexdigest()
    manifest_file.write_text(json.dumps(unsafe), encoding="utf-8")
    with pytest.raises(ValueError, match="leaves"):
        load_bundle(folder)
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    with (folder / "runs.csv").open("a", encoding="utf-8") as stream:
        stream.write("corrupt")
    with pytest.raises(ValueError, match="checksum"):
        load_bundle(folder)


def test_baseline_statistics_exclude_partial_failure(bundle):
    _, _, rows = bundle
    if "mode" not in rows[0]:
        return
    changed = copy.deepcopy(rows)
    changed[0]["status"] = "infeasible"
    changed[0]["objective"] = ""
    stats = bundle_statistics(changed)
    affected = next(s for s in stats if s["method"] == changed[0]["mode"])
    assert affected["F"] is None and affected["Veri"] == 0
