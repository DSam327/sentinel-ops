"""
Chaos Injection Engine for SentinelOps.
Orchestrates synthetic microservice failures and triggers IncidentAlerts.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

from app.core.models import (
    ChaosScenarioId,
    IncidentAlert,
    ServiceHealthStatus,
)
from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker


class ChaosEngine:
    """
    Simulates production outages by mutating the live topology,
    generating anomalous telemetry, and firing P1 alerts.
    """

    def __init__(
        self,
        topology: ServiceTopology,
        telemetry: TelemetryEngine,
        git_tracker: GitTracker,
    ):
        self.topology = topology
        self.telemetry = telemetry
        self.git_tracker = git_tracker
        self.active_incident: Optional[IncidentAlert] = None
        self.active_scenario: Optional[ChaosScenarioId] = None

    def inject_chaos(self, scenario_id: ChaosScenarioId) -> IncidentAlert:
        """Injects a chosen failure scenario into the live system."""
        self.topology.reset_to_healthy()
        self.active_scenario = scenario_id

        if scenario_id == ChaosScenarioId.N_PLUS_ONE_QUERY:
            alert = self._inject_n_plus_one()
        elif scenario_id == ChaosScenarioId.CASCADING_TIMEOUT:
            alert = self._inject_cascading_timeout()
        elif scenario_id == ChaosScenarioId.MEMORY_LEAK:
            alert = self._inject_memory_leak()
        elif scenario_id == ChaosScenarioId.REDIS_STAMPEDE:
            alert = self._inject_redis_stampede()
        else:
            raise ValueError(f"Unknown scenario: {scenario_id}")

        self.active_incident = alert
        return alert

    def _inject_n_plus_one(self) -> IncidentAlert:
        """Scenario 1: N+1 query in payment-service."""
        self.topology.update_node_status(
            "payment-service",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=2410.0,
            error_rate=0.45,
            cpu_pct=88.0,
            connection_pool_pct=98.0,
        )
        self.topology.update_node_status(
            "api-gateway",
            status=ServiceHealthStatus.DEGRADED,
            p99_latency_ms=2450.0,
            error_rate=0.25,
        )
        self.topology.update_node_status(
            "postgres-primary",
            status=ServiceHealthStatus.DEGRADED,
            p99_latency_ms=18.5,
            connection_pool_pct=96.0,
            cpu_pct=85.0,
        )
        self.topology.update_edge_status(
            "payment-service", "postgres-primary",
            current_latency_ms=18.5,
            error_rate=0.35,
        )
        self.topology.update_edge_status(
            "order-service", "payment-service",
            current_latency_ms=2410.0,
            error_rate=0.45,
        )
        self.topology.update_edge_status(
            "api-gateway", "order-service",
            current_latency_ms=2435.0,
            error_rate=0.25,
        )

        # Generate anomalous trace
        self.telemetry.generate_n_plus_one_trace()

        return IncidentAlert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            title="CRITICAL: P99 Latency Spike & Gateway Timeouts on /api/v1/checkout",
            firing_service="api-gateway",
            metric_name="p99_latency_ms",
            threshold=500.0,
            current_value=2450.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="P1-CRITICAL",
            scenario_id=ChaosScenarioId.N_PLUS_ONE_QUERY,
        )

    def _inject_cascading_timeout(self) -> IncidentAlert:
        """Scenario 2: Cascading timeout caused by third-party shipping."""
        self.topology.update_node_status(
            "third-party-shipping",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=14950.0,
            error_rate=0.75,
        )
        self.topology.update_node_status(
            "order-service",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=14980.0,
            error_rate=0.60,
            cpu_pct=92.0,
        )
        self.topology.update_node_status(
            "api-gateway",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=15000.0,
            error_rate=0.55,
        )
        self.topology.update_edge_status(
            "order-service", "third-party-shipping",
            current_latency_ms=14950.0,
            error_rate=0.75,
        )

        self.telemetry.generate_cascading_timeout_trace()

        return IncidentAlert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            title="CRITICAL: 504 Gateway Timeout Cascade on order-service",
            firing_service="api-gateway",
            metric_name="error_rate_5xx",
            threshold=0.05,
            current_value=0.55,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="P1-CRITICAL",
            scenario_id=ChaosScenarioId.CASCADING_TIMEOUT,
        )

    def _inject_memory_leak(self) -> IncidentAlert:
        """Scenario 3: Memory leak / Pod restart loop in inventory-service."""
        self.topology.update_node_status(
            "inventory-service",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=5180.0,
            error_rate=0.50,
            memory_pct=99.2,
            cpu_pct=75.0,
        )
        self.topology.update_node_status(
            "api-gateway",
            status=ServiceHealthStatus.DEGRADED,
            p99_latency_ms=5200.0,
            error_rate=0.30,
        )
        self.topology.update_edge_status(
            "order-service", "inventory-service",
            current_latency_ms=5180.0,
            error_rate=0.50,
        )

        self.telemetry.generate_memory_leak_trace()

        return IncidentAlert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            title="CRITICAL: Pod CrashLoopBackOff & Exit 137 (OOMKilled) in inventory-service",
            firing_service="inventory-service",
            metric_name="memory_pct",
            threshold=85.0,
            current_value=99.2,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="P1-CRITICAL",
            scenario_id=ChaosScenarioId.MEMORY_LEAK,
        )

    def _inject_redis_stampede(self) -> IncidentAlert:
        """Scenario 4: Thundering herd cache stampede on database."""
        self.topology.update_node_status(
            "redis-cache",
            status=ServiceHealthStatus.DEGRADED,
            metadata={"hit_ratio": 0.031},
        )
        self.topology.update_node_status(
            "postgres-primary",
            status=ServiceHealthStatus.FAILING,
            p99_latency_ms=1820.0,
            cpu_pct=96.0,
            connection_pool_pct=94.0,
        )
        self.topology.update_node_status(
            "order-service",
            status=ServiceHealthStatus.DEGRADED,
            p99_latency_ms=1840.0,
        )

        self.telemetry.generate_redis_stampede_trace()

        return IncidentAlert(
            alert_id=f"alert-{uuid.uuid4().hex[:8]}",
            title="CRITICAL: Postgres Primary CPU 96% Surge & Connection Starvation",
            firing_service="postgres-primary",
            metric_name="cpu_pct",
            threshold=80.0,
            current_value=96.0,
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="P1-CRITICAL",
            scenario_id=ChaosScenarioId.REDIS_STAMPEDE,
        )

    def resolve_incident(self) -> None:
        """Restores system to completely healthy state."""
        self.topology.reset_to_healthy()
        self.active_incident = None
        self.active_scenario = None
