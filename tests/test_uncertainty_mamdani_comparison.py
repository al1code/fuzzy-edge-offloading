import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from experiments.proposed import uncertainty_mamdani_comparison as experiment
from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import read_dataset
from src.evaluation import derive_normalization, evaluate_plan
from src.scenario import OffloadingDecision
from src.synthetic import generate_synthetic_dataset

SMALL = replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2))
GENETIC = GeneticSearchConfig(population_size=4, generations=2)
SWARM = SwarmSearchConfig(particle_count=3, iterations=3)


def _replay(dataset, row: dict[str, object]):
    scenario = experiment.scaled_scenario(
        dataset.scenario, float(row["link_rate_factor"])
    )
    locations = json.loads(str(row["locations"]))
    ratios = json.loads(str(row["ratios"]))
    caps = (
        experiment.derive_task_caps(dataset)
        if row["method"] == "Uncertainty-aware Mamdani"
        else None
    )
    return evaluate_plan(
        scenario,
        tuple(
            OffloadingDecision(
                task.task.task_id,
                ratio,
                None if gene == 0 else scenario.servers[gene - 1].server.server_id,
            )
            for task, gene, ratio in zip(scenario.tasks, locations, ratios, strict=True)
        ),
        normalization=derive_normalization(scenario),
        ratio_caps=caps,
    )


def test_hand_example_keeps_security_fixed_and_penalizes_wider_triangle() -> None:
    example = experiment._add_hand_example_caps(experiment._policy_hand_example())

    assert example["security_level"] == 0.7
    assert example["narrow_uncertainty"] < example["wide_uncertainty"]
    assert (
        example["narrow_allowed_offloading_ratio"]
        > example["wide_allowed_offloading_ratio"]
    )


def test_paired_pipeline_shares_inputs_and_enforces_proposed_caps() -> None:
    dataset = generate_synthetic_dataset(SMALL)
    rows = experiment.compare_pipelines(
        dataset,
        0,
        genetic_config=GENETIC,
        swarm_config=SWARM,
    )
    replay = experiment.compare_pipelines(
        dataset,
        0,
        genetic_config=GENETIC,
        swarm_config=SWARM,
    )

    assert [{**row, "search_seconds": 0.0} for row in rows] == [
        {**row, "search_seconds": 0.0} for row in replay
    ]
    assert [row["method"] for row in rows] == list(experiment.METHODS)
    assert rows[0]["sha256"] == rows[1]["sha256"]
    assert rows[0]["link_rate_factor"] == rows[1]["link_rate_factor"] == 1.0
    assert (
        rows[0]["ga_evaluations"]
        == rows[1]["ga_evaluations"]
        == (GENETIC.evaluation_budget)
    )
    assert rows[1]["max_cap_excess"] <= 1e-12
    for row in rows:
        evaluation = _replay(dataset, row)
        assert evaluation.objective.value == pytest.approx(float(row["objective"]))
        assert evaluation.total_security_risk == pytest.approx(
            float(row["total_security_risk"])
        )


def test_scaled_scenario_changes_only_rates_and_normalization() -> None:
    dataset = generate_synthetic_dataset(SMALL)
    doubled = experiment.scaled_scenario(dataset.scenario, 2.0)

    assert doubled.tasks == dataset.scenario.tasks
    assert doubled.servers == dataset.scenario.servers
    assert all(
        after.rate_bits_per_second == pytest.approx(2 * before.rate_bits_per_second)
        for before, after in zip(dataset.scenario.links, doubled.links, strict=True)
    )
    assert derive_normalization(doubled) != dataset.normalization


def test_bundle_is_auditable_and_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "uncertainty"
    rows = experiment.run_experiment(
        output,
        data_seeds=(42,),
        optimizer_seeds=(0,),
        scenario_config=SMALL,
        genetic_config=GENETIC,
        swarm_config=SWARM,
        link_rate_factors=(1.0, 2.0),
    )

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "complete"
    assert manifest["methods"] == list(experiment.METHODS)
    assert manifest["link_rate_factors"] == [1.0, 2.0]
    assert (
        "experiments/proposed/uncertainty_mamdani_comparison.py"
        in manifest["source_sha256"]
    )
    for path, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((output / path).read_bytes()).hexdigest() == digest
    with (output / "runs.csv").open(encoding="utf-8", newline="") as stream:
        saved = list(csv.DictReader(stream))
    assert len(rows) == len(saved) == 4
    for row in saved:
        dataset = read_dataset(output / "datasets" / f"seed_{row['data_seed']}.json")
        assert _replay(dataset, row).objective.value == pytest.approx(
            float(row["objective"])
        )
    hand = json.loads((output / "hand_example.json").read_text(encoding="utf-8"))
    assert (
        hand["narrow_allowed_offloading_ratio"] > hand["wide_allowed_offloading_ratio"]
    )
    assert (output / "comparison.png").read_bytes().startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        experiment.run_experiment(output)
