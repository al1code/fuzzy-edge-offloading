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
        [sys.executable, "-B", "-m", "experiments.baseline.exact_demo", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_default_demo_completes_small_search_and_retains_inputs_and_results() -> None:
    process = run_demo()
    assert process.returncode == 0
    output = json.loads(process.stdout)
    assert output["example_type"] == "exact_small_instance_verification_not_boalbfs"
    assert output["task_count"] == 3
    assert output["server_count"] == 2
    assert output["candidates_checked"] == output["feasible_candidates"] == 125
    assert output["infeasible_candidates"] == 0
    assert output["best_objective_value"] <= output["local_objective_value"]
    assert output["best"]["normalization"] == output["normalization"]
    assert len(output["best"]["tasks"]) == 3
    assert len(output["best"]["servers"]) == 2
    assert set(output["objective_weights"].values()) == {1 / 3}
    assert set(output["load_weights"].values()) == {1 / 3}
    assert output["runtime"]["python"]


def test_repeated_small_search_is_deterministic() -> None:
    first = run_demo("--seed", "0", "--tasks", "2", "--servers", "1")
    second = run_demo("--seed", "0", "--tasks", "2", "--servers", "1")
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["seed"] == 0


def test_replayed_dataset_uses_saved_fingerprint_and_normalizers(
    tmp_path: Path,
) -> None:
    dataset = generate_synthetic_dataset(
        replace(SyntheticScenarioConfig(), experiment=ExperimentConfig(7, 3, 2))
    )
    path = tmp_path / "small.json"
    write_dataset(dataset, path)
    before = path.read_bytes()
    process = run_demo("--input", str(path))
    assert process.returncode == 0
    output = json.loads(process.stdout)
    assert output["sha256"] == dataset_fingerprint(dataset)
    assert (
        output["normalization"]["latency_seconds"]
        == dataset.normalization.latency_seconds
    )
    assert path.read_bytes() == before


def test_paper_sized_scenario_is_rejected_without_a_truncated_exact_result() -> None:
    process = run_demo("--tasks", "60", "--servers", "3")
    assert process.returncode == 2
    assert "exceeding max_candidates=100000" in process.stderr
    assert "use a smaller scenario" in process.stderr
    assert process.stdout == ""


@pytest.mark.parametrize(
    "args",
    [
        ("--seed", "-1"),
        ("--tasks", "0"),
        ("--servers", "0"),
        ("--max-candidates", "124"),
        ("--max-candidates", "0"),
        ("--max-candidates", "2.5"),
    ],
)
def test_invalid_arguments_fail_without_partial_output(args: tuple[str, ...]) -> None:
    process = run_demo(*args)
    assert process.returncode == 2
    assert "error:" in process.stderr
    assert process.stdout == ""


def test_replay_rejects_ignored_generation_flags_and_missing_files(
    tmp_path: Path,
) -> None:
    path = str(tmp_path / "missing.json")
    ignored = run_demo("--input", path, "--seed", "42")
    assert ignored.returncode == 2
    assert "cannot be combined" in ignored.stderr
    missing = run_demo("--input", path)
    assert missing.returncode == 2
    assert "error:" in missing.stderr
    assert missing.stdout == ""
