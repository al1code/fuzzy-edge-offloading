from pathlib import Path

import pytest

from src.config import ExperimentConfig, FuzzySecurityConfig, ProjectPaths


def test_project_paths_follow_repository_layout(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    assert paths.root == tmp_path.resolve()
    assert paths.data_generated == tmp_path.resolve() / "data" / "generated"
    assert paths.data_author_provided == tmp_path.resolve() / "data" / "author_provided"
    assert paths.results_figures == tmp_path.resolve() / "results" / "figures"
    assert paths.results_tables == tmp_path.resolve() / "results" / "tables"


def test_experiment_config_accepts_default_values() -> None:
    config = ExperimentConfig()

    assert config.random_seed == 42
    assert config.task_count == 30
    assert config.server_count == 5


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("random_seed", -1),
        ("task_count", 0),
        ("server_count", 0),
    ],
)
def test_experiment_config_rejects_invalid_values(
    field_name: str,
    invalid_value: int,
) -> None:
    kwargs = {field_name: invalid_value}

    with pytest.raises(ValueError):
        ExperimentConfig(**kwargs)


def test_fuzzy_security_config_requires_weights_to_sum_to_one() -> None:
    config = FuzzySecurityConfig(
        task_data_weight=0.5,
        task_type_weight=0.3,
        terminal_lifecycle_weight=0.2,
    )

    assert config.task_data_weight == 0.5
    assert config.task_type_weight == 0.3
    assert config.terminal_lifecycle_weight == 0.2


def test_fuzzy_security_config_rejects_invalid_weights() -> None:
    with pytest.raises(ValueError):
        FuzzySecurityConfig(
            task_data_weight=0.5,
            task_type_weight=0.5,
            terminal_lifecycle_weight=0.5,
        )
