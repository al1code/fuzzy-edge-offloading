import pytest

from src.config import LoadBalanceConfig
from src.load_balance import (
    ResourceVector,
    calculate_load_variance,
    calculate_server_load,
)


@pytest.fixture
def capacity() -> ResourceVector:
    return ResourceVector(8e9, 20e6, 1024.0)


def test_server_load_sums_reservations_and_matches_resource_fractions(
    capacity: ResourceVector,
) -> None:
    reservation = ResourceVector(2e9, 2.5e6, 128.0)
    load = calculate_server_load(capacity, (reservation, reservation))

    assert load.cpu_utilization == pytest.approx(0.5)
    assert load.bandwidth_utilization == pytest.approx(0.25)
    assert load.memory_utilization == pytest.approx(0.25)
    assert load.weighted_load == pytest.approx(1 / 3)


def test_custom_resource_weights_change_load(capacity: ResourceVector) -> None:
    load = calculate_server_load(
        capacity,
        (ResourceVector(4e9, 5e6, 256.0),),
        config=LoadBalanceConfig(0.5, 0.3, 0.2),
    )

    assert load.weighted_load == pytest.approx(0.375)


def test_idle_server_has_zero_load(capacity: ResourceVector) -> None:
    load = calculate_server_load(capacity, ())

    assert load.cpu_utilization == load.bandwidth_utilization == 0.0
    assert load.memory_utilization == load.weighted_load == 0.0


def test_exact_capacity_is_allowed(capacity: ResourceVector) -> None:
    load = calculate_server_load(capacity, (capacity,))

    assert load.cpu_utilization == load.bandwidth_utilization == 1.0
    assert load.memory_utilization == load.weighted_load == 1.0


def test_weight_roundoff_keeps_full_load_at_one(capacity: ResourceVector) -> None:
    load = calculate_server_load(
        capacity, (capacity,), config=LoadBalanceConfig(0.5, 0.5000000005, 0.0)
    )

    assert load.weighted_load == 1.0


@pytest.mark.parametrize(
    ("reservation", "message"),
    [
        (ResourceVector(8e9 + 1, 0.0, 0.0), "CPU"),
        (ResourceVector(0.0, 20e6 + 1, 0.0), "bandwidth"),
        (ResourceVector(0.0, 0.0, 1025.0), "memory"),
    ],
)
def test_overallocated_resources_are_rejected(
    capacity: ResourceVector, reservation: ResourceVector, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        calculate_server_load(capacity, (reservation,))


def test_joint_reservations_cannot_exceed_capacity(capacity: ResourceVector) -> None:
    reservation = ResourceVector(5e9, 1e6, 64.0)

    with pytest.raises(ValueError, match="CPU"):
        calculate_server_load(capacity, (reservation, reservation))


@pytest.mark.parametrize(
    "field", ["cpu_cycles_per_second", "bandwidth_hz", "memory_mb"]
)
def test_capacity_denominators_must_be_positive(field: str) -> None:
    kwargs = {
        "cpu_cycles_per_second": 8e9,
        "bandwidth_hz": 20e6,
        "memory_mb": 1024.0,
        field: 0.0,
    }

    with pytest.raises(ValueError, match=field):
        calculate_server_load(ResourceVector(**kwargs), ())


@pytest.mark.parametrize(
    "field", ["cpu_cycles_per_second", "bandwidth_hz", "memory_mb"]
)
@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
def test_resource_vector_rejects_invalid_quantities(field: str, value: float) -> None:
    kwargs = {"cpu_cycles_per_second": 0.0, "bandwidth_hz": 0.0, "memory_mb": 0.0}
    kwargs[field] = value

    with pytest.raises(ValueError, match=field):
        ResourceVector(**kwargs)


def test_server_load_requires_resource_vectors(capacity: ResourceVector) -> None:
    with pytest.raises(TypeError, match="capacity"):
        calculate_server_load(None, ())
    with pytest.raises(TypeError, match="allocations"):
        calculate_server_load(capacity, (None,))
    with pytest.raises(TypeError, match="config"):
        calculate_server_load(capacity, (), config=0)


@pytest.mark.parametrize(
    ("loads", "expected"),
    [((0.2, 0.8), 0.09), ((0.0, 1.0), 0.25), ((0.4,), 0.0), ((0.5, 0.5, 0.5), 0.0)],
)
def test_load_variance_is_population_variance(
    loads: tuple[float, ...], expected: float
) -> None:
    assert calculate_load_variance(loads) == pytest.approx(expected)


def test_idle_servers_are_included_in_load_variance() -> None:
    assert calculate_load_variance((1 / 3, 0.0)) == pytest.approx(1 / 36)


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_load_variance_rejects_invalid_loads(value: float) -> None:
    with pytest.raises(ValueError, match="server load"):
        calculate_load_variance((0.5, value))


def test_load_variance_rejects_empty_system() -> None:
    with pytest.raises(ValueError, match="at least one"):
        calculate_load_variance(())
