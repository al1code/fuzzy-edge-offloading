import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "experiments.baseline.fuzzy_security_demo",
            *args,
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_demo_outputs_reproducible_traceable_json() -> None:
    first = run_demo()
    second = run_demo()

    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    result = json.loads(first.stdout)
    assert result["example_type"] == "synthetic_worked_example"
    assert len(result["expert_assessments"]) == 2
    assert result["assessment"]["security_level"] == pytest.approx(0.47125)
    assert result["offloading_risk"] == pytest.approx(
        0.048322505397121946, rel=1e-12, abs=1e-15
    )


@pytest.mark.parametrize(
    ("option", "value", "message"),
    [
        ("--security-threshold", "nan", "security_threshold"),
        ("--offloading-ratio", "1.1", "offloading_ratio"),
    ],
)
def test_demo_reports_invalid_arguments(option: str, value: str, message: str) -> None:
    result = run_demo(option, value)

    assert result.returncode == 2
    assert message in result.stderr
    assert result.stdout == ""


def test_demo_accepts_changed_threshold_and_local_execution() -> None:
    result = run_demo("--security-threshold", "0.4", "--offloading-ratio", "0.0")

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["assessment"]["security_risk"] == 0.0
    assert output["offloading_risk"] == 0.0
