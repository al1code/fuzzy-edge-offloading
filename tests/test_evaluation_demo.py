import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "experiments.baseline.evaluation_demo", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_demo_compares_complete_supplied_plans_on_one_fixed_scenario() -> None:
    result = run_demo()
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert (
        output["example_type"]
        == "synthetic_two_task_equation_check_not_an_optimization"
    )
    assert output["security_assessment_shared_by_tasks"][
        "security_level"
    ] == pytest.approx(0.47125)
    assert len(output["scenario"]["tasks"]) == len(output["scenario"]["servers"]) == 2
    plans = output["plans"]
    assert [plans[name]["objective_value"] for name in plans] == pytest.approx(
        [1 / 3, 17 / 36, 107 / 270, 13 / 30]
    )
    assert all(
        plan["normalization"] == output["normalization"] for plan in plans.values()
    )


def test_demo_can_show_edge_execution_preferred_when_offloading_risk_is_zero() -> None:
    result = run_demo("--security-threshold", "0.4")
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["normalization"]["security_risk"] == 1.0
    plans = output["plans"]
    assert plans["edge_balanced"]["objective_value"] < plans["local"]["objective_value"]
    assert all(plan["total_security_risk"] == 0.0 for plan in plans.values())


@pytest.mark.parametrize(
    "args",
    [
        ("--security-threshold", "nan"),
        ("--security-threshold", "1.1"),
        ("--link-rate-mbps", "0"),
        ("--link-rate-mbps", "-1"),
        ("--link-rate-mbps", "inf"),
    ],
)
def test_demo_rejects_invalid_scenario_inputs(args: tuple[str, ...]) -> None:
    result = run_demo(*args)
    assert result.returncode == 2
    assert "error:" in result.stderr
    assert result.stdout == ""
