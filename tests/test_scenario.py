from dataclasses import FrozenInstanceError, replace

import pytest

from src.scenario import OffloadingDecision, ServerProfile, TaskProfile, WirelessLink
from tests.scenario_helpers import make_scenario


def test_scenario_snapshots_mutable_input_collections() -> None:
    base = make_scenario()
    tasks, servers, links = list(base.tasks), list(base.servers), list(base.links)
    scenario = replace(base, tasks=tasks, servers=servers, links=links)
    tasks.clear()
    servers.clear()
    links.clear()
    assert scenario == base
    with pytest.raises(FrozenInstanceError):
        scenario.security_threshold = 0.2


@pytest.mark.parametrize("field", ["tasks", "servers", "links"])
def test_scenario_rejects_empty_or_wrongly_typed_collections(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        replace(make_scenario(), **{field: ()})
    with pytest.raises(TypeError, match=field):
        replace(make_scenario(), **{field: (object(),)})


@pytest.mark.parametrize("field", ["tasks", "servers"])
def test_scenario_requires_unique_inventory_ids(field: str) -> None:
    base = make_scenario()
    profiles = getattr(base, field)
    with pytest.raises(ValueError, match="IDs must be unique"):
        replace(base, **{field: (profiles[0], profiles[0])})


def test_scenario_requires_complete_unique_known_links() -> None:
    base = make_scenario()
    with pytest.raises(ValueError, match="duplicate"):
        replace(base, links=(*base.links, base.links[0]))
    with pytest.raises(ValueError, match="cover exactly"):
        replace(base, links=base.links[:-1])
    with pytest.raises(ValueError, match="cover exactly"):
        replace(base, links=(*base.links[:-1], WirelessLink("missing", "s1", 40e6)))


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_scenario_rejects_invalid_thresholds(value: float) -> None:
    with pytest.raises(ValueError, match="security_threshold"):
        replace(make_scenario(), security_threshold=value)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_scenario_requires_positive_bandwidth_capacity(value: float) -> None:
    with pytest.raises(ValueError, match="bandwidth_capacity_hz"):
        replace(make_scenario(), bandwidth_capacity_hz=value)


@pytest.mark.parametrize(
    "field", ["local_cpu_cycles_per_second", "bandwidth_hz", "memory_mb"]
)
@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_task_profile_rejects_invalid_positive_quantities(
    field: str, value: float
) -> None:
    with pytest.raises(ValueError):
        replace(make_scenario().tasks[0], **{field: value})


def test_task_and_server_profiles_reject_wrong_models() -> None:
    with pytest.raises(TypeError, match="Task"):
        TaskProfile(object(), 1e9, 0.5, 5e6, 256.0)
    with pytest.raises(TypeError, match="EdgeServer"):
        ServerProfile(object(), 4e9)


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_task_profile_rejects_invalid_security_levels(value: float) -> None:
    with pytest.raises(ValueError, match="security_level"):
        replace(make_scenario().tasks[0], security_level=value)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_server_profile_and_link_require_positive_rates(value: float) -> None:
    with pytest.raises(ValueError, match="allocated CPU"):
        replace(make_scenario().servers[0], allocated_cpu_cycles_per_second=value)
    with pytest.raises(ValueError, match="rate_bits_per_second"):
        WirelessLink("t1", "s1", value)


@pytest.mark.parametrize("value", [True, "1", None])
def test_profiles_reject_non_numeric_parameters(value: object) -> None:
    with pytest.raises(TypeError):
        replace(make_scenario().tasks[0], security_level=value)
    with pytest.raises(TypeError):
        replace(make_scenario().servers[0], allocated_cpu_cycles_per_second=value)
    with pytest.raises(TypeError):
        WirelessLink("t1", "s1", value)


@pytest.mark.parametrize("value", ["", "  ", 1, True])
def test_decision_and_link_identifiers_are_not_coerced(value: object) -> None:
    error = ValueError if isinstance(value, str) else TypeError
    with pytest.raises(error, match="task_id"):
        OffloadingDecision(value, 0.0)
    with pytest.raises(error, match="server_id"):
        OffloadingDecision("t1", 0.0, value)
    with pytest.raises(error, match="task_id"):
        WirelessLink(value, "s1", 40e6)
    with pytest.raises(error, match="server_id"):
        WirelessLink("t1", value, 40e6)


def test_local_choice_cannot_discard_positive_offloaded_work() -> None:
    with pytest.raises(ValueError, match="requires a selected server"):
        OffloadingDecision("t1", 0.4)
    assert OffloadingDecision("t1", 0.0).server_id is None
    assert OffloadingDecision("t1", 0.0, "s1").server_id == "s1"


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_decision_requires_unit_interval_ratio(value: float) -> None:
    with pytest.raises(ValueError, match="offloading_ratio"):
        OffloadingDecision("t1", value, "s1")
