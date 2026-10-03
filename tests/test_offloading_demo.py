import json
import subprocess
import sys
from pathlib import Path

import pytest


def run_demo(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-m", "experiments.baseline.offloading_demo", *args],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def test_demo_combines_security_latency_and_load_for_supplied_decisions() -> None:
    result = run_demo()

    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["example_type"] == "synthetic_worked_example_not_an_optimization"
    scenarios = output["scenarios"]
    assert [s["offloading_ratio"] for s in scenarios] == [0.0, 0.4, 1.0]
    assert [s["latency"]["total_seconds"] for s in scenarios] == pytest.approx(
        [1.2, 0.92, 0.5]
    )
    assert [s["offloading_risk"] for s in scenarios] == pytest.approx(
        [0.0, 0.048322505397121946, 0.12080626349280486]
    )
    assert scenarios[0]["selected_server_load"]["weighted_load"] == 0.0
    assert scenarios[1]["selected_server_load"]["weighted_load"] == pytest.approx(1 / 3)
    assert scenarios[1]["load_variance"] == pytest.approx(1 / 36)
    assert scenarios[2]["load_variance"] == scenarios[1]["load_variance"]


def test_slow_link_can_make_full_offloading_slower_than_local_execution() -> None:
    result = run_demo("--link-rate-mbps", "4", "--ratios", "0", "1")

    assert result.returncode == 0
    scenarios = json.loads(result.stdout)["scenarios"]
    assert scenarios[0]["latency"]["total_seconds"] == pytest.approx(1.2)
    assert scenarios[1]["latency"]["total_seconds"] == pytest.approx(2.3)


def test_demo_threshold_changes_risk_without_changing_latency() -> None:
    result = run_demo("--security-threshold", "0.4", "--ratios", "0.4")

    assert result.returncode == 0
    scenario = json.loads(result.stdout)["scenarios"][0]
    assert scenario["offloading_risk"] == 0.0
    assert scenario["latency"]["total_seconds"] == pytest.approx(0.92)


@pytest.mark.parametrize(
    "args",
    [
        ("--ratios", "1.1"),
        ("--ratios", "nan"),
        ("--link-rate-mbps", "0", "--ratios", "0.4"),
        ("--link-rate-mbps", "-1"),
        ("--security-threshold", "inf"),
    ],
)
def test_demo_rejects_invalid_arguments(args: tuple[str, ...]) -> None:
    result = run_demo(*args)

    assert result.returncode == 2
    assert "error:" in result.stderr
    assert result.stdout == ""
