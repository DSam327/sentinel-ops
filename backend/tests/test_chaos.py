"""
Unit tests for ChaosEngine fault injection and telemetry simulation.
"""

from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.engine.chaos import ChaosEngine
from app.core.models import ChaosScenarioId, ServiceHealthStatus


def test_n_plus_one_chaos_injection():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)

    alert = chaos.inject_chaos(ChaosScenarioId.N_PLUS_ONE_QUERY)
    assert alert.scenario_id == ChaosScenarioId.N_PLUS_ONE_QUERY
    assert alert.firing_service == "api-gateway"
    assert alert.current_value >= 2400.0

    # Verify payment service marked FAILING
    pay_node = topology.get_node("payment-service")
    assert pay_node.status == ServiceHealthStatus.FAILING
    assert pay_node.connection_pool_pct >= 95.0

    # Verify anomalous trace was recorded
    traces = telemetry.get_recent_traces(1)
    assert len(traces) == 1
    assert traces[0].has_error is True
    assert "N+1" in traces[0].summary or "SEQUENTIAL" in traces[0].summary


def test_cascading_timeout_injection():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)

    alert = chaos.inject_chaos(ChaosScenarioId.CASCADING_TIMEOUT)
    assert alert.scenario_id == ChaosScenarioId.CASCADING_TIMEOUT
    order_node = topology.get_node("order-service")
    assert order_node.status == ServiceHealthStatus.FAILING

    traces = telemetry.get_recent_traces(1)
    assert len(traces) == 1
    assert traces[0].total_duration_ms > 10000.0


def test_chaos_resolution():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)

    chaos.inject_chaos(ChaosScenarioId.MEMORY_LEAK)
    assert chaos.active_incident is not None

    chaos.resolve_incident()
    assert chaos.active_incident is None
    assert topology.get_node("inventory-service").status == ServiceHealthStatus.HEALTHY
