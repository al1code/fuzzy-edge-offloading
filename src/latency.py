"""Computation and communication latency from Eqs. (1)-(4), (16).

Rates are in bits/s, CPU allocations in cycles/s, and returned times in seconds.
The functions evaluate a supplied decision; they do not choose a server or ratio.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import fsum, log, log1p

from src.models import Task
from src.validation import (
    validate_finite,
    validate_non_negative,
    validate_positive,
    validate_unit_interval,
)

BITS_PER_MEGABYTE = 8_000_000


@dataclass(frozen=True, slots=True)
class LatencyBreakdown:
    """The three additive latency terms in the paper's Eq. (16)."""

    local_seconds: float
    transmission_seconds: float
    edge_seconds: float

    def __post_init__(self) -> None:
        validate_non_negative(self.local_seconds, "local_seconds")
        validate_non_negative(self.transmission_seconds, "transmission_seconds")
        validate_non_negative(self.edge_seconds, "edge_seconds")

    @property
    def total_seconds(self) -> float:
        """Return local + transmission + edge latency, following Eq. (16)."""

        return fsum((self.local_seconds, self.transmission_seconds, self.edge_seconds))


def calculate_wireless_rate(
    *,
    bandwidth_hz: float,
    transmission_power_watts: float,
    channel_gain: float,
    noise_density_watts_per_hz: float,
) -> float:
    """Evaluate Eq. (4): b * log2(1 + p * g**2 / (b * zeta)).

    To make b * zeta a noise power, this API interprets zeta as a noise
    spectral density in W/Hz. This is a documented dimensional assumption;
    the paper calls zeta noise power. Gain is the amplitude used in g**2.
    Zero transmission power or channel gain gives a zero rate.
    """

    validate_positive(bandwidth_hz, "bandwidth_hz")
    validate_non_negative(transmission_power_watts, "transmission_power_watts")
    validate_non_negative(channel_gain, "channel_gain")
    validate_positive(noise_density_watts_per_hz, "noise_density_watts_per_hz")
    noise_power = bandwidth_hz * noise_density_watts_per_hz
    validate_positive(noise_power, "derived noise power")
    signal_power = transmission_power_watts * channel_gain * channel_gain
    validate_non_negative(signal_power, "derived signal power")
    signal_to_noise_ratio = signal_power / noise_power
    validate_finite(signal_to_noise_ratio, "derived signal-to-noise ratio")
    rate = bandwidth_hz * log1p(signal_to_noise_ratio) / log(2.0)
    validate_non_negative(rate, "derived wireless rate")
    return rate


def calculate_task_latency(
    task: Task,
    *,
    offloading_ratio: float,
    local_cpu_cycles_per_second: float,
    edge_cpu_cycles_per_second: float = 0.0,
    transmission_rate_bits_per_second: float = 0.0,
) -> LatencyBreakdown:
    """Evaluate one task on its selected server using Eqs. (1)-(3), (16).

    ``required_cpu_cycles`` already equals D_i * C_i. It must not be
    multiplied by data size again. Data size is converted from decimal MB
    to bits only for transmission. x=0 needs no server or wireless rate;
    x>0 requires a positive per-task CPU allocation and positive link rate.
    The supplied edge CPU rate is an allocation, not total server capacity.
    """

    if not isinstance(task, Task):
        raise TypeError("task must be a Task")
    validate_unit_interval(offloading_ratio, "offloading_ratio")
    validate_positive(local_cpu_cycles_per_second, "local_cpu_cycles_per_second")
    validate_non_negative(edge_cpu_cycles_per_second, "edge_cpu_cycles_per_second")
    validate_non_negative(
        transmission_rate_bits_per_second, "transmission_rate_bits_per_second"
    )
    local_seconds = (
        (1.0 - offloading_ratio)
        * task.required_cpu_cycles
        / local_cpu_cycles_per_second
    )
    if offloading_ratio == 0.0:
        return LatencyBreakdown(local_seconds, 0.0, 0.0)

    validate_positive(edge_cpu_cycles_per_second, "edge_cpu_cycles_per_second")
    validate_positive(
        transmission_rate_bits_per_second, "transmission_rate_bits_per_second"
    )
    transmission_seconds = (
        offloading_ratio
        * task.data_size_mb
        * BITS_PER_MEGABYTE
        / transmission_rate_bits_per_second
    )
    edge_seconds = (
        offloading_ratio * task.required_cpu_cycles / edge_cpu_cycles_per_second
    )
    return LatencyBreakdown(local_seconds, transmission_seconds, edge_seconds)
