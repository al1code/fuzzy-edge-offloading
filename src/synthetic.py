"""Seeded synthetic scenarios with retained inputs for fuzzy and link calculations."""

from __future__ import annotations

import platform
from dataclasses import dataclass
from math import isclose

import numpy as np

from src.config import PositiveRange, SyntheticScenarioConfig
from src.evaluation import derive_normalization
from src.fuzzy_security import SecurityPerspectives, assess_security
from src.latency import BITS_PER_MEGABYTE, calculate_wireless_rate
from src.models import EdgeServer, Task, TriangularFuzzyNumber
from src.objective import NormalizationConstants
from src.random_utils import create_random_state
from src.scenario import OffloadingScenario, ServerProfile, TaskProfile, WirelessLink
from src.validation import validate_positive

GENERATOR_VERSION = "uniform-numeric-v1"


@dataclass(frozen=True, slots=True)
class RuntimeVersions:
    """Generation runtime, retained when a saved dataset is loaded elsewhere."""

    python: str
    numpy: str
    bit_generator: str

    def __post_init__(self) -> None:
        for value in (self.python, self.numpy, self.bit_generator):
            if not isinstance(value, str) or not value.strip():
                raise ValueError("runtime versions must be non-blank strings")


@dataclass(frozen=True, slots=True)
class SyntheticDataset:
    """Scenario plus ordered raw inputs, scales, configuration, and runtime.

    Assessments/C_i follow scenario task order; gains follow scenario link
    order. The saved scenario stores actual rates and security levels, so
    replay does not depend on drawing randomness or rebuilding those values.
    """

    configuration: SyntheticScenarioConfig
    scenario: OffloadingScenario
    expert_assessments: tuple[tuple[SecurityPerspectives, ...], ...]
    cpu_cycles_per_bit: tuple[float, ...]
    channel_gains: tuple[float, ...]
    normalization: NormalizationConstants
    runtime: RuntimeVersions

    def __post_init__(self) -> None:
        for value, expected in (
            (self.configuration, SyntheticScenarioConfig),
            (self.scenario, OffloadingScenario),
            (self.normalization, NormalizationConstants),
            (self.runtime, RuntimeVersions),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"dataset requires {expected.__name__}")
        object.__setattr__(
            self, "expert_assessments", tuple(tuple(a) for a in self.expert_assessments)
        )
        object.__setattr__(self, "cpu_cycles_per_bit", tuple(self.cpu_cycles_per_bit))
        object.__setattr__(self, "channel_gains", tuple(self.channel_gains))
        counts = self.configuration.experiment
        if (
            len(self.scenario.tasks) != counts.task_count
            or len(self.scenario.servers) != counts.server_count
        ):
            raise ValueError("scenario counts do not match the recorded configuration")
        if (
            len(self.expert_assessments) != counts.task_count
            or len(self.cpu_cycles_per_bit) != counts.task_count
        ):
            raise ValueError("raw task inputs must match scenario task order and count")
        for assessments in self.expert_assessments:
            if len(assessments) != len(self.configuration.expert_weights):
                raise ValueError("each task must have one assessment per expert weight")
            if any(not isinstance(a, SecurityPerspectives) for a in assessments):
                raise TypeError("expert_assessments must contain SecurityPerspectives")
        if len(self.channel_gains) != len(self.scenario.links):
            raise ValueError("channel gains must match scenario link order and count")
        for value in self.cpu_cycles_per_bit:
            validate_positive(value, "cpu_cycles_per_bit")
        for value in self.channel_gains:
            validate_positive(value, "channel_gain")
        self._validate_calculations()

    def _validate_calculations(self) -> None:
        """Check that recorded raw inputs/configuration explain the saved scenario."""

        config = self.configuration
        if (
            self.scenario.bandwidth_capacity_hz != config.bandwidth_capacity_hz
            or self.scenario.security_threshold != config.security_threshold
        ):
            raise ValueError("scenario settings do not match the configuration")
        for profile, cycles, assessments in zip(
            self.scenario.tasks,
            self.cpu_cycles_per_bit,
            self.expert_assessments,
            strict=True,
        ):
            for value, bounds in (
                (profile.task.data_size_mb, config.data_size_mb),
                (cycles, config.cpu_cycles_per_bit),
                (profile.bandwidth_hz, config.task_bandwidth_hz),
                (profile.memory_mb, config.task_memory_mb),
            ):
                if not bounds.low <= value <= bounds.high:
                    raise ValueError("task draw lies outside its recorded range")
            if (
                profile.local_cpu_cycles_per_second
                != config.local_cpu_cycles_per_second
                or profile.task.deadline_seconds != config.deadline_seconds
            ):
                raise ValueError("terminal settings do not match the configuration")
            expected_cycles = profile.task.data_size_mb * BITS_PER_MEGABYTE * cycles
            if not isclose(
                profile.task.required_cpu_cycles, expected_cycles, rel_tol=1e-12
            ):
                raise ValueError("task CPU work does not match D_i * C_i")
            security = assess_security(
                assessments,
                expert_weights=config.expert_weights,
                security_threshold=config.security_threshold,
                config=config.security,
            )
            if not isclose(
                profile.security_level,
                security.security_level,
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                raise ValueError("security level does not match expert assessments")
        for profile in self.scenario.servers:
            expected = EdgeServer(
                profile.server.server_id,
                config.server_cpu_capacity_cycles_per_second,
                config.inventory_link_rate_mbps,
                config.inventory_link_rate_mbps,
                config.server_memory_capacity_mb,
            )
            if (
                profile.server != expected
                or profile.allocated_cpu_cycles_per_second
                != config.allocated_edge_cpu_cycles_per_second
            ):
                raise ValueError("server settings do not match the configuration")
        tasks = {profile.task.task_id: profile for profile in self.scenario.tasks}
        for link, gain in zip(self.scenario.links, self.channel_gains, strict=True):
            if not config.channel_gain.low <= gain <= config.channel_gain.high:
                raise ValueError("channel gain lies outside its recorded range")
            rate = calculate_wireless_rate(
                bandwidth_hz=tasks[link.task_id].bandwidth_hz,
                transmission_power_watts=config.transmission_power_watts,
                channel_gain=gain,
                noise_density_watts_per_hz=config.noise_density_watts_per_hz,
            )
            if not isclose(link.rate_bits_per_second, rate, rel_tol=1e-12):
                raise ValueError("link rate does not match recorded wireless inputs")
        expected_normalization = derive_normalization(self.scenario)
        if not isclose(
            self.normalization.latency_seconds,
            expected_normalization.latency_seconds,
            rel_tol=1e-12,
        ) or not isclose(
            self.normalization.security_risk,
            expected_normalization.security_risk,
            rel_tol=1e-12,
        ):
            raise ValueError("normalization does not match the scenario bounds")


def _draw(rng: np.random.Generator, bounds: PositiveRange) -> float:
    return float(rng.uniform(bounds.low, bounds.high))


def _draw_assessment(rng: np.random.Generator) -> SecurityPerspectives:
    # Sorted independent U[0,1) draws are a numeric stress-test assumption,
    # not Table 3 linguistic labels or observations from real factory experts.
    triangles = tuple(
        TriangularFuzzyNumber(*sorted(float(value) for value in rng.random(3)))
        for _ in range(3)
    )
    return SecurityPerspectives(*triangles)


def generate_synthetic_dataset(
    config: SyntheticScenarioConfig | None = None,
) -> SyntheticDataset:
    """Generate one dataset without changing any global random state.

    Draw order is fixed: each task's D, C, bandwidth, memory, then its expert
    triangles; afterwards gains in task-major/server-minor order. A fresh
    local RNG is created from the recorded seed on each call. No capacity
    repair, resampling, or optimization is hidden in generation.
    """

    if config is None:
        config = SyntheticScenarioConfig()
    elif not isinstance(config, SyntheticScenarioConfig):
        raise TypeError("config must be a SyntheticScenarioConfig")
    rng = create_random_state(config.experiment.random_seed).numpy_random
    tasks = []
    assessments_by_task = []
    cycles_by_task = []
    for index in range(config.experiment.task_count):
        data_mb = _draw(rng, config.data_size_mb)
        cycles_per_bit = _draw(rng, config.cpu_cycles_per_bit)
        bandwidth = _draw(rng, config.task_bandwidth_hz)
        memory = _draw(rng, config.task_memory_mb)
        assessments = tuple(_draw_assessment(rng) for _ in config.expert_weights)
        security = assess_security(
            assessments,
            expert_weights=config.expert_weights,
            security_threshold=config.security_threshold,
            config=config.security,
        )
        tasks.append(
            TaskProfile(
                Task(
                    f"task-{index + 1:04d}",
                    data_mb,
                    data_mb * BITS_PER_MEGABYTE * cycles_per_bit,
                    config.deadline_seconds,
                ),
                config.local_cpu_cycles_per_second,
                security.security_level,
                bandwidth,
                memory,
            )
        )
        assessments_by_task.append(assessments)
        cycles_by_task.append(cycles_per_bit)
    servers = tuple(
        ServerProfile(
            EdgeServer(
                f"edge-{index + 1:03d}",
                config.server_cpu_capacity_cycles_per_second,
                config.inventory_link_rate_mbps,
                config.inventory_link_rate_mbps,
                config.server_memory_capacity_mb,
            ),
            config.allocated_edge_cpu_cycles_per_second,
        )
        for index in range(config.experiment.server_count)
    )
    links = []
    gains = []
    for profile in tasks:
        for server in servers:
            gain = _draw(rng, config.channel_gain)
            rate = calculate_wireless_rate(
                bandwidth_hz=profile.bandwidth_hz,
                transmission_power_watts=config.transmission_power_watts,
                channel_gain=gain,
                noise_density_watts_per_hz=config.noise_density_watts_per_hz,
            )
            links.append(
                WirelessLink(profile.task.task_id, server.server.server_id, rate)
            )
            gains.append(gain)
    scenario = OffloadingScenario(
        tuple(tasks),
        servers,
        tuple(links),
        config.bandwidth_capacity_hz,
        config.security_threshold,
    )
    return SyntheticDataset(
        config,
        scenario,
        tuple(assessments_by_task),
        tuple(cycles_by_task),
        tuple(gains),
        derive_normalization(scenario),
        RuntimeVersions(
            platform.python_version(), np.__version__, type(rng.bit_generator).__name__
        ),
    )
