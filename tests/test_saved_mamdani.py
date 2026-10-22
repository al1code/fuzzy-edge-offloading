"""Saved sensitivity conditions must survive GUI statistics and replay."""

import json
from dataclasses import replace

import pytest

from experiments.proposed import uncertainty_mamdani_comparison as experiment
from gui import services
from src.config import (
    ExperimentConfig,
    GeneticSearchConfig,
    SwarmSearchConfig,
    SyntheticScenarioConfig,
)
from src.dataset_io import dataset_fingerprint, read_dataset


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / "sensitivity"
    experiment.run_experiment(
        folder,
        data_seeds=(42,),
        optimizer_seeds=(0,),
        scenario_config=replace(
            SyntheticScenarioConfig(), experiment=ExperimentConfig(42, 3, 2)
        ),
        genetic_config=GeneticSearchConfig(population_size=4, generations=2),
        swarm_config=SwarmSearchConfig(particle_count=3, iterations=3),
        link_rate_factors=(0.5, 1.0, 2.0),
    )
    return folder, *services.load_bundle(folder)


def test_sensitivity_statistics_keep_conditions_separate(bundle):
    _, _, rows = bundle
    stats = services.bundle_statistics(rows)
    assert len(stats) == 6
    assert {row["link_rate_factor"] for row in stats} == {0.5, 1.0, 2.0}
    for summary in stats:
        original = next(
            row
            for row in rows
            if row["method"] == summary["method"]
            and float(row["link_rate_factor"]) == summary["link_rate_factor"]
        )
        assert summary["F"] == pytest.approx(float(original["objective"]))


def test_replay_uses_saved_rates_scales_and_proposed_caps(bundle):
    folder, manifest, rows = bundle
    base = read_dataset(folder / "datasets/seed_42.json")
    for row in rows:
        dataset, run = services.restore_bundle_run(folder, row, manifest)
        assert dataset_fingerprint(dataset) == dataset_fingerprint(base)
        assert run.link_rate_factor == float(row["link_rate_factor"])
        assert run.evaluation.objective.value == pytest.approx(float(row["objective"]))
        assert run.evaluation.total_latency_seconds == pytest.approx(
            float(row["total_latency_seconds"])
        )
        assert run.evaluation.normalization.latency_seconds == pytest.approx(
            float(row["latency_normalizer"])
        )


def test_legacy_v1_manifest_has_explicitly_known_equal_weights(bundle):
    folder, manifest, rows = bundle
    assert "objective_weights" in manifest and "load_weights" in manifest
    legacy = {
        k: v
        for k, v in manifest.items()
        if k not in ("objective_weights", "load_weights")
    }
    assert services.bundle_configuration(legacy) == services.bundle_configuration(
        manifest
    )
    _, run = services.restore_bundle_run(folder, rows[-1], legacy)
    assert run.evaluation.objective.value == pytest.approx(float(rows[-1]["objective"]))
    with pytest.raises(ValueError, match="weights"):
        services.bundle_configuration({"experiment": "unknown"})


def test_saved_proposed_plan_is_rechecked_against_its_policy(bundle):
    folder, manifest, rows = bundle
    row = dict(next(row for row in rows if row["method"] == experiment.METHODS[1]))
    row["locations"] = json.dumps([1, 1, 1])
    row["ratios"] = json.dumps([1.0, 1.0, 1.0])
    with pytest.raises(ValueError, match="policy cap"):
        services.restore_bundle_run(folder, row, manifest)
