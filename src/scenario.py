"""Explicit, immutable inputs for a multi-task offloading experiment."""

from __future__ import annotations

from dataclasses import dataclass

from src.models import EdgeServer, Task
from src.validation import validate_positive, validate_unit_interval


def _validate_identifier(value: str, name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")


@dataclass(frozen=True, slots=True)
class TaskProfile:
    """Task, terminal CPU, fuzzy-derived security level, and reservations.

    Bandwidth is Hz, not bits/s; memory is decimal MB. The security level
    comes from assess_security(...).security_level, not a random risk score.
    """

    task: Task
    local_cpu_cycles_per_second: float
    security_level: float
    bandwidth_hz: float
    memory_mb: float

    def __post_init__(self) -> None:
        if not isinstance(self.task, Task):
            raise TypeError("task must be a Task")
        validate_positive(self.local_cpu_cycles_per_second, "local CPU")
        validate_unit_interval(self.security_level, "security_level")
        validate_positive(self.bandwidth_hz, "bandwidth_hz")
        validate_positive(self.memory_mb, "memory_mb")


@dataclass(frozen=True, slots=True)
class ServerProfile:
    """Existing server inventory plus its per-selected-task CPU allocation.

    The Mbps inventory fields do not specify task-to-server wireless rates.
    Those are supplied explicitly as WirelessLink inputs.
    """

    server: EdgeServer
    allocated_cpu_cycles_per_second: float

    def __post_init__(self) -> None:
        if not isinstance(self.server, EdgeServer):
            raise TypeError("server must be an EdgeServer")
        validate_positive(self.allocated_cpu_cycles_per_second, "allocated CPU")


@dataclass(frozen=True, slots=True)
class WirelessLink:
    """Rate for one task/server pair in bits/s, consistent with its bandwidth."""

    task_id: str
    server_id: str
    rate_bits_per_second: float

    def __post_init__(self) -> None:
        _validate_identifier(self.task_id, "task_id")
        _validate_identifier(self.server_id, "server_id")
        validate_positive(self.rate_bits_per_second, "rate_bits_per_second")


@dataclass(frozen=True, slots=True)
class OffloadingScenario:
    """One shared scenario for every compared method; no random generation.

    Every task/server pair has exactly one positive link rate. Lambda is
    shared across server bandwidth denominators, following Eq. (7).
    """

    tasks: tuple[TaskProfile, ...]
    servers: tuple[ServerProfile, ...]
    links: tuple[WirelessLink, ...]
    bandwidth_capacity_hz: float
    security_threshold: float

    def __post_init__(self) -> None:
        for name, expected_type in (
            ("tasks", TaskProfile),
            ("servers", ServerProfile),
            ("links", WirelessLink),
        ):
            values = tuple(getattr(self, name))
            if not values:
                raise ValueError(f"{name} must not be empty")
            if any(not isinstance(value, expected_type) for value in values):
                raise TypeError(f"{name} must contain {expected_type.__name__} objects")
            object.__setattr__(self, name, values)
        validate_positive(self.bandwidth_capacity_hz, "bandwidth_capacity_hz")
        validate_unit_interval(self.security_threshold, "security_threshold")
        task_ids = {profile.task.task_id for profile in self.tasks}
        server_ids = {profile.server.server_id for profile in self.servers}
        if len(task_ids) != len(self.tasks):
            raise ValueError("task IDs must be unique")
        if len(server_ids) != len(self.servers):
            raise ValueError("server IDs must be unique")
        pairs = {(link.task_id, link.server_id) for link in self.links}
        if len(pairs) != len(self.links):
            raise ValueError("duplicate task/server link")
        expected_pairs = {
            (task_id, server_id) for task_id in task_ids for server_id in server_ids
        }
        if pairs != expected_pairs:
            raise ValueError(
                "links must cover exactly the scenario's task/server pairs"
            )


@dataclass(frozen=True, slots=True)
class OffloadingDecision:
    """One location and ratio per task, consistent with the M+1 location space.

    None denotes local-only execution and requires x=0. A selected server
    with x=0 remains selected: its reservation still counts in Eqs. (6)-(8).
    """

    task_id: str
    offloading_ratio: float
    server_id: str | None = None

    def __post_init__(self) -> None:
        _validate_identifier(self.task_id, "task_id")
        validate_unit_interval(self.offloading_ratio, "offloading_ratio")
        if self.server_id is None:
            if self.offloading_ratio != 0.0:
                raise ValueError("positive offloading_ratio requires a selected server")
        else:
            _validate_identifier(self.server_id, "server_id")
