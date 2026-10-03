"""Small explicit fixture, independent of the CLI and production generation."""

from src.models import EdgeServer, Task
from src.scenario import OffloadingScenario, ServerProfile, TaskProfile, WirelessLink


def make_scenario() -> OffloadingScenario:
    tasks = (
        TaskProfile(Task("t1", 1.0, 1.2e9, 3.0), 1e9, 0.47125, 5e6, 256.0),
        TaskProfile(Task("t2", 2.0, 2.4e9, 3.0), 1e9, 0.47125, 5e6, 256.0),
    )
    servers = (
        ServerProfile(EdgeServer("s1", 8e9, 100.0, 100.0, 1024.0), 4e9),
        ServerProfile(EdgeServer("s2", 8e9, 100.0, 100.0, 1024.0), 4e9),
    )
    links = tuple(
        WirelessLink(t.task.task_id, s.server.server_id, 40e6)
        for t in tasks
        for s in servers
    )
    return OffloadingScenario(tasks, servers, links, 20e6, 0.6)
