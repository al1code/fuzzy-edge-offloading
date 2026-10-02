import pytest

from src.models import EdgeServer, Task, TriangularFuzzyNumber


def test_triangular_fuzzy_number_centroid() -> None:
    fuzzy_number = TriangularFuzzyNumber(low=0.1, modal=0.2, high=0.9)

    assert fuzzy_number.centroid() == pytest.approx(0.4)


def test_triangular_fuzzy_number_paper_transformation_value() -> None:
    fuzzy_number = TriangularFuzzyNumber(low=0.1, modal=0.2, high=0.9)

    assert fuzzy_number.paper_transformation_value() == pytest.approx(0.3)


def test_triangular_fuzzy_number_rejects_invalid_order() -> None:
    with pytest.raises(ValueError):
        TriangularFuzzyNumber(low=0.7, modal=0.5, high=0.9)


def test_task_accepts_positive_values() -> None:
    task = Task(
        task_id="task-1",
        data_size_mb=2.5,
        required_cpu_cycles=1_000_000.0,
        deadline_seconds=0.8,
    )

    assert task.task_id == "task-1"


def test_task_rejects_empty_identifier() -> None:
    with pytest.raises(ValueError):
        Task(
            task_id="",
            data_size_mb=2.5,
            required_cpu_cycles=1_000_000.0,
            deadline_seconds=0.8,
        )


def test_edge_server_accepts_positive_resource_values() -> None:
    server = EdgeServer(
        server_id="server-1",
        cpu_capacity_cycles_per_second=10_000_000.0,
        uplink_bandwidth_mbps=25.0,
        downlink_bandwidth_mbps=50.0,
        memory_capacity_mb=2048.0,
    )

    assert server.server_id == "server-1"
    assert server.memory_capacity_mb == 2048.0


def test_edge_server_rejects_invalid_capacity() -> None:
    with pytest.raises(ValueError):
        EdgeServer(
            server_id="server-1",
            cpu_capacity_cycles_per_second=0.0,
            uplink_bandwidth_mbps=25.0,
            downlink_bandwidth_mbps=50.0,
            memory_capacity_mb=2048.0,
        )


def test_edge_server_rejects_invalid_memory_capacity() -> None:
    with pytest.raises(ValueError):
        EdgeServer(
            server_id="server-1",
            cpu_capacity_cycles_per_second=10_000_000.0,
            uplink_bandwidth_mbps=25.0,
            downlink_bandwidth_mbps=50.0,
            memory_capacity_mb=0.0,
        )
