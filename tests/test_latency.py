from math import log

import pytest

from src.latency import (
    LatencyBreakdown,
    calculate_task_latency,
    calculate_wireless_rate,
)
from src.models import Task


@pytest.fixture
def task() -> Task:
    return Task("task-1", 1.0, 1_200_000_000.0, 2.0)


@pytest.mark.parametrize(
    ("ratio", "local", "transmission", "edge", "total"),
    [
        (0.0, 1.2, 0.0, 0.0, 1.2),
        (0.4, 0.72, 0.08, 0.12, 0.92),
        (1.0, 0.0, 0.2, 0.3, 0.5),
    ],
)
def test_latency_matches_hand_calculated_terms(
    task: Task,
    ratio: float,
    local: float,
    transmission: float,
    edge: float,
    total: float,
) -> None:
    result = calculate_task_latency(
        task,
        offloading_ratio=ratio,
        local_cpu_cycles_per_second=1e9,
        edge_cpu_cycles_per_second=4e9,
        transmission_rate_bits_per_second=40e6,
    )

    assert result.local_seconds == pytest.approx(local)
    assert result.transmission_seconds == pytest.approx(transmission)
    assert result.edge_seconds == pytest.approx(edge)
    assert result.total_seconds == pytest.approx(total)


def test_local_only_execution_needs_no_edge_allocation_or_link(task: Task) -> None:
    result = calculate_task_latency(
        task, offloading_ratio=0.0, local_cpu_cycles_per_second=1e9
    )

    assert result.total_seconds == pytest.approx(1.2)
    assert result.edge_seconds == result.transmission_seconds == 0.0


def test_total_latency_uses_paper_sum_not_parallel_max() -> None:
    result = LatencyBreakdown(0.72, 0.08, 0.12)

    assert result.total_seconds == pytest.approx(0.92)


def test_data_size_changes_transmission_without_double_counting_cpu_cycles() -> None:
    first = calculate_task_latency(
        Task("one-mb", 1.0, 1.2e9, 2.0),
        offloading_ratio=0.4,
        local_cpu_cycles_per_second=1e9,
        edge_cpu_cycles_per_second=4e9,
        transmission_rate_bits_per_second=40e6,
    )
    second = calculate_task_latency(
        Task("two-mb", 2.0, 1.2e9, 2.0),
        offloading_ratio=0.4,
        local_cpu_cycles_per_second=1e9,
        edge_cpu_cycles_per_second=4e9,
        transmission_rate_bits_per_second=40e6,
    )

    assert second.transmission_seconds == pytest.approx(0.16)
    assert second.local_seconds == first.local_seconds
    assert second.edge_seconds == first.edge_seconds


@pytest.mark.parametrize("ratio", [-0.1, 1.1, float("nan"), float("inf")])
def test_latency_rejects_invalid_offloading_ratios(task: Task, ratio: float) -> None:
    with pytest.raises(ValueError, match="offloading_ratio"):
        calculate_task_latency(
            task, offloading_ratio=ratio, local_cpu_cycles_per_second=1e9
        )


@pytest.mark.parametrize(
    "field", ["edge_cpu_cycles_per_second", "transmission_rate_bits_per_second"]
)
def test_positive_offloading_requires_positive_active_resources(
    task: Task, field: str
) -> None:
    kwargs = {
        "offloading_ratio": 0.4,
        "local_cpu_cycles_per_second": 1e9,
        "edge_cpu_cycles_per_second": 4e9,
        "transmission_rate_bits_per_second": 40e6,
        field: 0.0,
    }

    with pytest.raises(ValueError, match=field):
        calculate_task_latency(task, **kwargs)


@pytest.mark.parametrize(
    "field",
    [
        "local_cpu_cycles_per_second",
        "edge_cpu_cycles_per_second",
        "transmission_rate_bits_per_second",
    ],
)
@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
def test_latency_rejects_invalid_resources_even_on_local_path(
    task: Task, field: str, value: float
) -> None:
    kwargs = {"offloading_ratio": 0.0, "local_cpu_cycles_per_second": 1e9, field: value}

    with pytest.raises(ValueError, match=field):
        calculate_task_latency(task, **kwargs)


def test_latency_requires_task_model() -> None:
    with pytest.raises(TypeError, match="Task"):
        calculate_task_latency(
            None, offloading_ratio=0.0, local_cpu_cycles_per_second=1e9
        )


def test_wireless_rate_has_one_bit_per_hz_at_unit_snr() -> None:
    rate = calculate_wireless_rate(
        bandwidth_hz=1e6,
        transmission_power_watts=0.1,
        channel_gain=0.01,
        noise_density_watts_per_hz=1e-11,
    )

    assert rate == pytest.approx(1e6)


def test_wireless_rate_squares_amplitude_gain() -> None:
    rate = calculate_wireless_rate(
        bandwidth_hz=1e6,
        transmission_power_watts=0.1,
        channel_gain=0.02,
        noise_density_watts_per_hz=1e-11,
    )

    assert rate == pytest.approx(2_321_928.094887362)


def test_wireless_rate_preserves_weak_signal_precision() -> None:
    rate = calculate_wireless_rate(
        bandwidth_hz=1.0,
        transmission_power_watts=1e-14,
        channel_gain=1.0,
        noise_density_watts_per_hz=1.0,
    )

    assert rate == pytest.approx(1e-14 / log(2.0), rel=1e-12, abs=0.0)


@pytest.mark.parametrize("field", ["channel_gain", "transmission_power_watts"])
def test_wireless_rate_is_zero_without_signal(field: str) -> None:
    kwargs = {
        "bandwidth_hz": 1e6,
        "transmission_power_watts": 0.1,
        "channel_gain": 0.01,
        "noise_density_watts_per_hz": 1e-11,
        field: 0.0,
    }

    assert calculate_wireless_rate(**kwargs) == 0.0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("bandwidth_hz", 0.0),
        ("noise_density_watts_per_hz", 0.0),
        ("transmission_power_watts", -1.0),
        ("channel_gain", -1.0),
        ("channel_gain", float("nan")),
        ("bandwidth_hz", float("inf")),
    ],
)
def test_wireless_rate_rejects_invalid_parameters(field: str, value: float) -> None:
    kwargs = {
        "bandwidth_hz": 1e6,
        "transmission_power_watts": 0.1,
        "channel_gain": 0.01,
        "noise_density_watts_per_hz": 1e-11,
        field: value,
    }

    with pytest.raises(ValueError, match=field):
        calculate_wireless_rate(**kwargs)
