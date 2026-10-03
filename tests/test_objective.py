import pytest

from src.objective import NormalizationConstants, ObjectiveConfig, calculate_objective


def test_objective_equation_and_retained_contributions() -> None:
    result = calculate_objective(
        20.0,
        2.0,
        0.1,
        normalization=NormalizationConstants(40.0, 4.0),
        config=ObjectiveConfig(0.5, 0.3, 0.2),
    )
    assert result.normalized_latency == 0.5
    assert result.normalized_risk == 0.5
    assert result.load_variance == 0.1
    assert result.latency_term == 0.25
    assert result.risk_term == 0.15
    assert result.load_term == pytest.approx(0.02)
    assert result.value == pytest.approx(0.42)


def test_default_weights_and_metrics_above_reference_are_not_clipped() -> None:
    result = calculate_objective(
        2.0, 3.0, 0.1, normalization=NormalizationConstants(1.0, 1.0)
    )
    assert result.normalized_latency == 2.0
    assert result.normalized_risk == 3.0
    assert result.value == pytest.approx(1.7)


@pytest.mark.parametrize(
    "weights",
    [
        (0.5, 0.5, 0.5),
        (-0.1, 0.5, 0.6),
        (float("nan"), 0.0, 1.0),
        (float("inf"), 0.0, 0.0),
    ],
)
def test_objective_rejects_invalid_weights(weights: tuple[float, ...]) -> None:
    with pytest.raises(ValueError, match="objective weights"):
        ObjectiveConfig(*weights)


def test_zero_and_tolerance_accepted_weights_keep_their_meaning() -> None:
    result = calculate_objective(
        0.6,
        0.0,
        0.0,
        normalization=NormalizationConstants(1.0, 1.0),
        config=ObjectiveConfig(1.0 - 5e-10, 0.0, 0.0),
    )
    assert result.value == 0.6


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), True])
def test_normalizers_must_be_finite_strictly_positive_numbers(
    index: int, value: object
) -> None:
    args = [1.0, 1.0]
    args[index] = value
    error = TypeError if isinstance(value, bool) else ValueError
    with pytest.raises(error):
        NormalizationConstants(*args)


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf"), True])
def test_objective_rejects_invalid_metrics(index: int, value: object) -> None:
    args = [1.0, 1.0, 0.1]
    args[index] = value
    error = TypeError if isinstance(value, bool) else ValueError
    with pytest.raises(error):
        calculate_objective(*args, normalization=NormalizationConstants(1.0, 1.0))


def test_objective_rejects_invalid_configuration_types() -> None:
    with pytest.raises(TypeError, match="normalization"):
        calculate_objective(1.0, 1.0, 0.0, normalization=object())
    with pytest.raises(TypeError, match="ObjectiveConfig"):
        calculate_objective(
            1.0,
            1.0,
            0.0,
            normalization=NormalizationConstants(1.0, 1.0),
            config=object(),
        )
    with pytest.raises(TypeError):
        ObjectiveConfig(True, 0.0, 0.0)


def test_objective_rejects_normalization_overflow() -> None:
    with pytest.raises(ValueError, match="normalized latency"):
        calculate_objective(
            1e308, 0.0, 0.0, normalization=NormalizationConstants(1e-308, 1.0)
        )
