import hashlib
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from src.config import ExperimentConfig, SyntheticScenarioConfig
from src.dataset_io import (
    dataset_fingerprint,
    dataset_from_json,
    dataset_to_json,
    read_dataset,
    write_dataset,
)
from src.evaluation import evaluate_plan
from src.scenario import OffloadingDecision
from src.synthetic import RuntimeVersions, SyntheticDataset, generate_synthetic_dataset


@pytest.fixture
def dataset() -> SyntheticDataset:
    return generate_synthetic_dataset(
        SyntheticScenarioConfig(experiment=ExperimentConfig(42, 3, 2))
    )


def rehash(payload: dict) -> str:
    payload.pop("sha256")
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    payload["sha256"] = hashlib.sha256(encoded).hexdigest()
    return json.dumps(payload)


def test_serialization_is_deterministic_and_complete(dataset: SyntheticDataset) -> None:
    first = dataset_to_json(dataset)
    assert first == dataset_to_json(dataset)
    payload = json.loads(first)
    assert (
        payload["dataset_kind"] == "synthetic_method_reimplementation_not_author_data"
    )
    assert payload["sha256"] == dataset_fingerprint(dataset)
    assert "expert_assessments" in payload["dataset"]
    assert "channel_gains" in payload["dataset"]
    assert "configuration" in payload["dataset"]
    assert "timestamp" not in first
    assert dataset_from_json(first) == dataset


def test_disk_round_trip_preserves_inputs_and_evaluation(
    dataset: SyntheticDataset, tmp_path: Path
) -> None:
    path = tmp_path / "generated" / "scenario.json"
    write_dataset(dataset, path)
    loaded = read_dataset(path)
    assert loaded == dataset
    decisions = tuple(
        OffloadingDecision(task.task.task_id, 0.0) for task in dataset.scenario.tasks
    )
    assert evaluate_plan(
        loaded.scenario, decisions, normalization=loaded.normalization
    ) == evaluate_plan(dataset.scenario, decisions, normalization=dataset.normalization)
    assert path.read_bytes() == dataset_to_json(dataset).encode("utf-8")


def test_snapshot_replay_never_draws_random_numbers(
    dataset: SyntheticDataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("replay must not draw a new scenario")

    monkeypatch.setattr("src.synthetic.create_random_state", forbidden)
    assert dataset_from_json(dataset_to_json(dataset)) == dataset


def test_saved_generation_runtime_is_not_replaced_by_current_runtime(
    dataset: SyntheticDataset,
) -> None:
    earlier = replace(dataset, runtime=RuntimeVersions("3.13.0", "2.4.0", "PCG64"))
    assert dataset_from_json(dataset_to_json(earlier)).runtime == earlier.runtime
    assert dataset_fingerprint(earlier) != dataset_fingerprint(dataset)


def test_existing_file_is_not_replaced(
    dataset: SyntheticDataset, tmp_path: Path
) -> None:
    path = tmp_path / "scenario.json"
    write_dataset(dataset, path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_dataset(dataset, path)
    assert path.read_bytes() == original


def test_invalid_dataset_cannot_create_a_file_or_directory(tmp_path: Path) -> None:
    path = tmp_path / "new-directory" / "scenario.json"
    with pytest.raises(TypeError, match="SyntheticDataset"):
        write_dataset(object(), path)
    assert not path.parent.exists()
    with pytest.raises(TypeError, match="SyntheticDataset"):
        dataset_fingerprint(object())


@pytest.mark.parametrize(
    "data",
    [
        '{"x":1,"x":2}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        "[]",
        "{}",
        "{",
    ],
)
def test_invalid_json_or_document_shapes_are_rejected(data: str) -> None:
    with pytest.raises(ValueError):
        dataset_from_json(data)


@pytest.mark.parametrize("version", [0, 2, True])
def test_unknown_or_boolean_schema_versions_are_rejected(
    dataset: SyntheticDataset, version: object
) -> None:
    payload = json.loads(dataset_to_json(dataset))
    payload["schema_version"] = version
    with pytest.raises((TypeError, ValueError), match="schema_version"):
        dataset_from_json(json.dumps(payload))


@pytest.mark.parametrize(
    "field", ["generator_version", "dataset_kind", "parameter_notes"]
)
def test_unsupported_provenance_is_rejected(
    dataset: SyntheticDataset, field: str
) -> None:
    payload = json.loads(dataset_to_json(dataset))
    payload[field] = "unknown"
    with pytest.raises(ValueError, match="unsupported"):
        dataset_from_json(json.dumps(payload))


def test_checksum_detects_accidental_edits(dataset: SyntheticDataset) -> None:
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["scenario"]["tasks"][0]["task"]["data_size_mb"] += 0.1
    with pytest.raises(ValueError, match="checksum mismatch"):
        dataset_from_json(json.dumps(payload))


def test_missing_or_extra_parameters_cannot_become_hidden_defaults(
    dataset: SyntheticDataset,
) -> None:
    payload = json.loads(dataset_to_json(dataset))
    del payload["dataset"]["configuration"]["expert_weights"]
    with pytest.raises(ValueError, match="SyntheticScenarioConfig fields"):
        dataset_from_json(rehash(payload))
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["scenario"]["tasks"][0]["task"]["new_field"] = 1
    with pytest.raises(ValueError, match="Task fields"):
        dataset_from_json(rehash(payload))


def test_wrong_array_shapes_and_invalid_numeric_fields_are_rejected(
    dataset: SyntheticDataset,
) -> None:
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["configuration"]["expert_weights"] = {"expert": 1}
    with pytest.raises(TypeError, match="JSON arrays"):
        dataset_from_json(rehash(payload))
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["scenario"]["links"][0]["rate_bits_per_second"] = True
    with pytest.raises(TypeError, match="rate_bits_per_second"):
        dataset_from_json(rehash(payload))


def test_rehashed_but_inconsistent_raw_inputs_do_not_pass_validation(
    dataset: SyntheticDataset,
) -> None:
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["scenario"]["tasks"][0]["security_level"] = 0.0
    with pytest.raises(ValueError, match="expert assessments"):
        dataset_from_json(rehash(payload))
    payload = json.loads(dataset_to_json(dataset))
    payload["dataset"]["normalization"]["latency_seconds"] *= 2
    with pytest.raises(ValueError, match="normalization"):
        dataset_from_json(rehash(payload))


def test_numpy_integer_and_real_configuration_values_are_serializable() -> None:
    config = SyntheticScenarioConfig(
        experiment=ExperimentConfig(np.int64(42), 2, 1),
        expert_weights=(np.float32(0.25), np.float32(0.75)),
    )
    dataset = generate_synthetic_dataset(config)
    assert dataset_from_json(dataset_to_json(dataset)) == dataset
