"""Versioned JSON snapshots for replaying the same generated experiment inputs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields
from numbers import Integral, Real
from pathlib import Path
from typing import Any

from src.config import (
    ExperimentConfig,
    FuzzySecurityConfig,
    PositiveRange,
    SyntheticScenarioConfig,
)
from src.fuzzy_security import SecurityPerspectives
from src.models import EdgeServer, Task, TriangularFuzzyNumber
from src.objective import NormalizationConstants
from src.scenario import OffloadingScenario, ServerProfile, TaskProfile, WirelessLink
from src.synthetic import GENERATOR_VERSION, RuntimeVersions, SyntheticDataset
from src.validation import validate_integer

SCHEMA_VERSION = 1
DATASET_KIND = "synthetic_method_reimplementation_not_author_data"
PARAMETER_NOTES = "references/synthetic_data.md"


def _json_number(value: object) -> int | float:
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, Real):
        return float(value)
    raise TypeError(f"cannot serialize {type(value).__name__} to JSON")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
        default=_json_number,
    )


def _payload(dataset: SyntheticDataset) -> dict[str, object]:
    if not isinstance(dataset, SyntheticDataset):
        raise TypeError("dataset must be a SyntheticDataset")
    return {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "dataset_kind": DATASET_KIND,
        "parameter_notes": PARAMETER_NOTES,
        "dataset": asdict(dataset),
    }


def dataset_fingerprint(dataset: SyntheticDataset) -> str:
    """SHA-256 of canonical inputs and metadata; not proof of data authenticity."""

    return hashlib.sha256(
        _canonical_json(_payload(dataset)).encode("utf-8")
    ).hexdigest()


def dataset_to_json(dataset: SyntheticDataset) -> str:
    """Encode a complete, deterministic snapshot without timestamps or NaN."""

    payload = _payload(dataset)
    payload["sha256"] = dataset_fingerprint(dataset)
    return (
        json.dumps(
            payload, sort_keys=True, indent=2, allow_nan=False, default=_json_number
        )
        + "\n"
    )


def write_dataset(dataset: SyntheticDataset, path: str | Path) -> None:
    """Write UTF-8 JSON, creating parent directories but never replacing a file."""

    data = dataset_to_json(dataset).encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(data)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON value: {value}")


def _record(model: type, value: object) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        field.name for field in fields(model)
    }:
        raise ValueError(f"invalid or missing {model.__name__} fields")
    return dict(value)


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError("dataset sequences must be JSON arrays")
    return value


def _read_config(value: object) -> SyntheticScenarioConfig:
    values = _record(SyntheticScenarioConfig, value)
    values["experiment"] = ExperimentConfig(
        **_record(ExperimentConfig, values["experiment"])
    )
    values["security"] = FuzzySecurityConfig(
        **_record(FuzzySecurityConfig, values["security"])
    )
    values["expert_weights"] = tuple(_list(values["expert_weights"]))
    for name in (
        "data_size_mb",
        "cpu_cycles_per_bit",
        "task_bandwidth_hz",
        "task_memory_mb",
        "channel_gain",
    ):
        values[name] = PositiveRange(**_record(PositiveRange, values[name]))
    return SyntheticScenarioConfig(**values)


def _read_scenario(value: object) -> OffloadingScenario:
    values = _record(OffloadingScenario, value)
    tasks = []
    for item in _list(values["tasks"]):
        task = _record(TaskProfile, item)
        task["task"] = Task(**_record(Task, task["task"]))
        tasks.append(TaskProfile(**task))
    servers = []
    for item in _list(values["servers"]):
        server = _record(ServerProfile, item)
        server["server"] = EdgeServer(**_record(EdgeServer, server["server"]))
        servers.append(ServerProfile(**server))
    values["tasks"] = tuple(tasks)
    values["servers"] = tuple(servers)
    values["links"] = tuple(
        WirelessLink(**_record(WirelessLink, item)) for item in _list(values["links"])
    )
    return OffloadingScenario(**values)


def _read_assessment(value: object) -> SecurityPerspectives:
    values = _record(SecurityPerspectives, value)
    return SecurityPerspectives(
        **{
            name: TriangularFuzzyNumber(**_record(TriangularFuzzyNumber, number))
            for name, number in values.items()
        }
    )


def dataset_from_json(data: str) -> SyntheticDataset:
    """Verify the version/hash and restore typed, validated inputs without RNGs.

    All recorded fields are required: missing parameters must not quietly
    become today's defaults. Unknown fields/versions and duplicate keys are
    rejected. The original generation runtime is retained, not relabeled.
    """

    payload = json.loads(
        data, object_pairs_hook=_unique_object, parse_constant=_reject_constant
    )
    expected = {
        "schema_version",
        "generator_version",
        "dataset_kind",
        "parameter_notes",
        "dataset",
        "sha256",
    }
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError("invalid dataset document fields")
    validate_integer(
        payload["schema_version"],
        "schema_version",
        minimum=SCHEMA_VERSION,
        maximum=SCHEMA_VERSION,
    )
    if (
        payload["generator_version"] != GENERATOR_VERSION
        or payload["dataset_kind"] != DATASET_KIND
        or payload["parameter_notes"] != PARAMETER_NOTES
    ):
        raise ValueError("unsupported dataset generator or provenance")
    recorded_hash = payload.pop("sha256")
    calculated_hash = hashlib.sha256(
        _canonical_json(payload).encode("utf-8")
    ).hexdigest()
    if recorded_hash != calculated_hash:
        raise ValueError("dataset checksum mismatch")
    values = _record(SyntheticDataset, payload["dataset"])
    values["configuration"] = _read_config(values["configuration"])
    values["scenario"] = _read_scenario(values["scenario"])
    values["normalization"] = NormalizationConstants(
        **_record(NormalizationConstants, values["normalization"])
    )
    values["runtime"] = RuntimeVersions(**_record(RuntimeVersions, values["runtime"]))
    values["expert_assessments"] = tuple(
        tuple(_read_assessment(item) for item in _list(assessments))
        for assessments in _list(values["expert_assessments"])
    )
    values["cpu_cycles_per_bit"] = tuple(_list(values["cpu_cycles_per_bit"]))
    values["channel_gains"] = tuple(_list(values["channel_gains"]))
    return SyntheticDataset(**values)


def read_dataset(path: str | Path) -> SyntheticDataset:
    """Restore a saved snapshot for fair comparison on identical inputs."""

    return dataset_from_json(Path(path).read_text(encoding="utf-8"))
