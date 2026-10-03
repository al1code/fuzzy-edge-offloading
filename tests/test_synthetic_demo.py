import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.dataset_io import dataset_fingerprint, read_dataset


def run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "experiments.baseline.synthetic_demo", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )


def test_default_demo_is_a_sixty_task_generation_check_not_optimization() -> None:
    result = run_demo()
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert (
        output["example_type"]
        == "synthetic_generation_and_plan_checks_not_optimization"
    )
    assert output["task_count"] == 60
    assert output["server_count"] == 3
    assert output["output_path"] is None
    assert set(output["objective_weights"].values()) == {1 / 3}
    assert set(output["load_weights"].values()) == {1 / 3}
    plans = output["plans"]
    assert all(plan["feasible"] for plan in plans.values())
    assert plans["local"]["total_security_risk"] == 0.0
    assert plans["edge_round_robin"]["objective"]["normalized_risk"] == pytest.approx(
        1.0
    )
    assert plans["partial_half_round_robin"]["objective"][
        "normalized_risk"
    ] == pytest.approx(0.5)


def test_same_cli_parameters_produce_the_same_fingerprint_and_results() -> None:
    args = ("--seed", "0", "--tasks", "3", "--servers", "2")
    first, second = run_demo(*args), run_demo(*args)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["seed"] == 0


def test_export_and_replay_use_identical_saved_inputs(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    generated = run_demo("--tasks", "3", "--servers", "2", "--output", str(path))
    loaded = run_demo("--input", str(path))
    assert generated.returncode == loaded.returncode == 0
    first, second = json.loads(generated.stdout), json.loads(loaded.stdout)
    assert (
        first["sha256"] == second["sha256"] == dataset_fingerprint(read_dataset(path))
    )
    assert first["plans"] == second["plans"]
    assert first["normalization"] == second["normalization"]
    duplicate = run_demo("--output", str(path))
    assert duplicate.returncode == 2
    assert "error:" in duplicate.stderr
    assert read_dataset(path).configuration.experiment.task_count == 3


def test_large_demo_reports_infeasible_plans_without_presenting_scores() -> None:
    result = run_demo("--tasks", "140", "--servers", "3")
    assert result.returncode == 0
    plans = json.loads(result.stdout)["plans"]
    assert plans["local"]["feasible"]
    for name in ("edge_round_robin", "partial_half_round_robin"):
        assert not plans[name]["feasible"]
        assert "CPU allocation exceeds capacity" in plans[name]["reason"]
        assert "objective_value" not in plans[name]


@pytest.mark.parametrize(
    "args",
    [
        ("--seed", "-1"),
        ("--tasks", "0"),
        ("--servers", "0"),
        ("--security-threshold", "nan"),
        ("--security-threshold", "1.1"),
        ("--seed", "1.5"),
    ],
)
def test_cli_rejects_invalid_generation_parameters(args: tuple[str, ...]) -> None:
    result = run_demo(*args)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert result.stdout == ""


def test_input_cannot_be_silently_combined_with_ignored_generation_flags(
    tmp_path: Path,
) -> None:
    result = run_demo("--input", str(tmp_path / "snapshot.json"), "--seed", "42")
    assert result.returncode == 2
    assert "cannot be combined" in result.stderr


def test_missing_or_malformed_input_is_reported_without_partial_output(
    tmp_path: Path,
) -> None:
    result = run_demo("--input", str(tmp_path / "missing.json"))
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert result.stdout == ""
