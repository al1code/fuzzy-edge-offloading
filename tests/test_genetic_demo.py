import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from src.config import ExperimentConfig, SyntheticScenarioConfig
from src.dataset_io import dataset_fingerprint, write_dataset
from src.synthetic import generate_synthetic_dataset


def run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "experiments.baseline.genetic_demo", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


def test_default_demo_runs_paper_range_counts_without_claiming_boalbfs() -> None:
    process = run_demo()
    assert process.returncode == 0, process.stderr
    output = json.loads(process.stdout)
    assert (
        output["example_type"] == "adaptive_ga_with_affine_ratio_reference_not_boalbfs"
    )
    assert output["task_count"] == 60
    assert output["server_count"] == 3
    assert output["evaluation_budget"] == output["evaluations"] == 755
    assert output["exact_comparison"] is None
    assert len(output["best"]["decisions"]) == 60
    assert len(output["history"]) == 26
    assert output["best_objective_value"] <= output["local_objective_value"]


def test_small_demo_replays_exactly_and_can_compare_with_exhaustive_reference() -> None:
    args = (
        "--tasks",
        "3",
        "--servers",
        "2",
        "--population",
        "8",
        "--generations",
        "3",
        "--verify-exact",
        "--optimizer-seed",
        "0",
    )
    first, second = run_demo(*args), run_demo(*args)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    output = json.loads(first.stdout)
    assert output["optimizer_seed"] == 0
    assert output["exact_comparison"]["candidates_checked"] == 125
    assert output["exact_comparison"]["absolute_gap"] == pytest.approx(0.0)
    assert output["evaluations"] == 29


def test_saved_data_is_not_redrawn_or_modified_and_optimizer_seed_is_separate(
    tmp_path: Path,
) -> None:
    dataset = generate_synthetic_dataset(
        replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(7, 3, 2))
    )
    path = tmp_path / "small.json"
    write_dataset(dataset, path)
    before = path.read_bytes()
    process = run_demo(
        "--input", str(path), "--optimizer-seed", "1", "--generations", "0"
    )
    assert process.returncode == 0
    output = json.loads(process.stdout)
    assert output["seed"] == 7
    assert output["optimizer_seed"] == 1
    assert output["sha256"] == dataset_fingerprint(dataset)
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        ("--population", "1"),
        ("--generations", "-1"),
        ("--optimizer-seed", "-1"),
        ("--tasks", "0"),
        ("--servers", "0"),
        ("--seed", "-1"),
        ("--verify-exact",),
        ("--generations", "2.5"),
    ],
)
def test_invalid_arguments_and_large_exact_verification_fail_cleanly(
    args: tuple[str, ...],
) -> None:
    process = run_demo(*args)
    assert process.returncode == 2
    assert process.stdout == ""
    assert "error:" in process.stderr


def test_replay_rejects_ignored_generation_flags_and_missing_files(
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "missing.json")
    ignored = run_demo("--input", path, "--tasks", "3")
    assert ignored.returncode == 2
    assert "cannot be combined" in ignored.stderr
    missing = run_demo("--input", path)
    assert missing.returncode == 2
    assert missing.stdout == ""
    assert "error:" in missing.stderr


def test_overloaded_large_scenario_reports_infeasible_evaluations_not_a_false_failure() -> (
    None
):
    process = run_demo(
        "--tasks", "140", "--servers", "3", "--population", "6", "--generations", "2"
    )
    assert process.returncode == 0
    output = json.loads(process.stdout)
    assert output["infeasible_evaluations"] > 0
    assert output["evaluations"] == 16
    assert output["best_objective_value"] <= output["local_objective_value"]


def test_boalbfs_demo_replays_and_reports_both_search_budgets() -> None:
    args = ("--method", "boalbfs", "--tasks", "3", "--servers", "2", "--verify-exact")
    first, second = run_demo(*args), run_demo(*args)
    assert first.returncode == second.returncode == 0, first.stderr
    assert first.stdout == second.stdout
    output = json.loads(first.stdout)
    assert output["example_type"] == "two_layer_ga_sapso_with_documented_assumptions"
    assert output["evaluations"] == output["evaluation_budget"] == 55
    assert output["swarm_config"]["particle_count"] == 8
    assert output["plan_evaluation_budget"] == 55 * 89
    assert 55 < output["plan_evaluations"] <= output["plan_evaluation_budget"]
    assert output["best_objective_value"] <= output["local_objective_value"]
    assert output["exact_comparison"]["absolute_gap"] >= -1e-12


@pytest.mark.parametrize(
    "args",
    [
        ("--particles", "8"),
        ("--method", "boalbfs", "--particles", "1"),
        ("--method", "boalbfs", "--pso-iterations", "-1"),
    ],
)
def test_swarm_flags_are_validated_and_not_silently_ignored(
    args: tuple[str, ...],
) -> None:
    process = run_demo(*args)
    assert process.returncode == 2
    assert process.stdout == ""
    assert "error:" in process.stderr
