"""
Telemetry and Trace Generator for SentinelOps.
Produces OpenTelemetry-compliant trace spans and Prometheus time-series metrics.
"""

import time
import random
import uuid
from typing import List, Dict, Any, Optional
from app.core.models import (
    TraceSpan,
    TraceTree,
    LogEntry,
    MetricPoint,
    ChaosScenarioId,
)


class TelemetryEngine:
    """
    Simulates high-fidelity distributed telemetry:
    - OpenTelemetry Trace trees (root spans, child spans, RPC metadata, DB statements)
    - Prometheus-style timeseries metrics
    - Structured JSON logs
    """

    def __init__(self):
        self._traces_buffer: List[TraceTree] = []
        self._logs_buffer: List[LogEntry] = []

    def generate_healthy_trace(self) -> TraceTree:
        """
        Generates a standard healthy checkout flow trace:
        api-gateway (25ms)
          -> auth-service (6ms)
          -> order-service (18ms)
               -> payment-service (12ms)
                    -> postgres-primary (3ms)
               -> inventory-service (8ms)
                    -> redis-cache (1.5ms)
        """
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        root_span_id = f"span-gw-{uuid.uuid4().hex[:8]}"

        spans: List[TraceSpan] = []

        # 1. API Gateway
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=root_span_id,
                service_name="api-gateway",
                operation_name="POST /api/v1/checkout",
                start_time_offset_ms=0.0,
                duration_ms=28.4,
                status_code=200,
                attributes={"http.method": "POST", "http.status_code": 200, "client.ip": "192.168.1.104"},
            )
        )

        # 2. Auth Service
        auth_span_id = f"span-auth-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=auth_span_id,
                parent_span_id=root_span_id,
                service_name="auth-service",
                operation_name="rpc VerifyToken",
                start_time_offset_ms=1.2,
                duration_ms=5.8,
                status_code=200,
                attributes={"rpc.system": "grpc", "auth.user_id": "usr_9912", "jwt.valid": True},
            )
        )

        # 3. Order Service
        order_span_id = f"span-order-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=root_span_id,
                service_name="order-service",
                operation_name="POST /internal/orders/create",
                start_time_offset_ms=7.5,
                duration_ms=19.5,
                status_code=200,
                attributes={"http.method": "POST", "order.id": "ord_8819"},
            )
        )

        # 4. Payment Service
        pay_span_id = f"span-pay-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=pay_span_id,
                parent_span_id=order_span_id,
                service_name="payment-service",
                operation_name="POST /payments/charge",
                start_time_offset_ms=9.0,
                duration_ms=11.2,
                status_code=200,
                attributes={"payment.amount_cents": 4999, "payment.currency": "USD"},
            )
        )

        # 5. Postgres Primary
        db_span_id = f"span-db-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=db_span_id,
                parent_span_id=pay_span_id,
                service_name="postgres-primary",
                operation_name="SELECT * FROM cards WHERE user_id = :uid",
                start_time_offset_ms=10.5,
                duration_ms=3.1,
                status_code=200,
                attributes={"db.system": "postgresql", "db.statement": "SELECT * FROM cards WHERE user_id = 'usr_9912' AND is_active = true"},
            )
        )

        tree = TraceTree(
            trace_id=trace_id,
            root_span_id=root_span_id,
            spans=spans,
            total_duration_ms=28.4,
            has_error=False,
            summary="Normal checkout transaction completed successfully",
        )
        self._traces_buffer.append(tree)
        return tree

    def generate_n_plus_one_trace(self) -> TraceTree:
        """
        Generates an anomalous trace showcasing the classic N+1 regression:
        payment-service executes 240 sequential SQL statements under one transaction,
        blowing latency up to 2400ms and maxing Postgres connection pool.
        """
        trace_id = f"trace-incident-n1-{uuid.uuid4().hex[:8]}"
        root_span_id = f"span-gw-{uuid.uuid4().hex[:8]}"
        spans: List[TraceSpan] = []

        # Gateway span reflects the caller's massive delay
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=root_span_id,
                service_name="api-gateway",
                operation_name="POST /api/v1/checkout",
                start_time_offset_ms=0.0,
                duration_ms=2450.0,
                status_code=504,
                has_error=True,
                error_message="Gateway Timeout: Upstream response exceeded 2000ms SLA",
                attributes={"http.method": "POST", "http.status_code": 504},
            )
        )

        order_span_id = f"span-order-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=root_span_id,
                service_name="order-service",
                operation_name="POST /internal/orders/create",
                start_time_offset_ms=5.0,
                duration_ms=2435.0,
                status_code=500,
                has_error=True,
                error_message="Payment service upstream timeout",
            )
        )

        pay_span_id = f"span-pay-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=pay_span_id,
                parent_span_id=order_span_id,
                service_name="payment-service",
                operation_name="PaymentOrchestrator.verify_and_charge",
                start_time_offset_ms=8.0,
                duration_ms=2410.0,
                status_code=500,
                has_error=True,
                error_message="ConnectionAcquisitionTimeout: Database pool exhausted (98% in-use)",
                attributes={
                    "code.filepath": "app/services/payment_orchestrator.py",
                    "code.lineno": 46,
                    "db.pool.wait_time_ms": 1820.0,
                },
            )
        )

        # 12 representative sequential SQL child spans representing 240 iterative loop queries
        curr_offset = 12.0
        for i in range(12):
            span_id = f"span-pg-n1-{i}"
            spans.append(
                TraceSpan(
                    trace_id=trace_id,
                    span_id=span_id,
                    parent_span_id=pay_span_id,
                    service_name="postgres-primary",
                    operation_name=f"SELECT * FROM card_verification WHERE card_id = 'card_{i}'",
                    start_time_offset_ms=curr_offset,
                    duration_ms=18.5,
                    status_code=200,
                    attributes={
                        "db.system": "postgresql",
                        "db.statement": f"SELECT * FROM card_verification WHERE card_id = 'c_{i}'",
                        "db.pool.wait_time_ms": 12.0,
                    },
                )
            )
            curr_offset += 19.0

        tree = TraceTree(
            trace_id=trace_id,
            root_span_id=root_span_id,
            spans=spans,
            total_duration_ms=2450.0,
            has_error=True,
            summary="Catastrophic N+1 sequential database loop detected in PaymentOrchestrator.verify_and_charge",
        )
        self._traces_buffer.append(tree)
        return tree

    def generate_cascading_timeout_trace(self) -> TraceTree:
        """
        Generates trace for Scenario 2: CASCADING_TIMEOUT.
        Third-party shipping hangs for 35 seconds, order service holds thread,
        gateway returns 504.
        """
        trace_id = f"trace-incident-cascade-{uuid.uuid4().hex[:8]}"
        root_span_id = f"span-gw-{uuid.uuid4().hex[:8]}"
        spans: List[TraceSpan] = []

        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=root_span_id,
                service_name="api-gateway",
                operation_name="POST /api/v1/checkout",
                start_time_offset_ms=0.0,
                duration_ms=15000.0,
                status_code=504,
                has_error=True,
                error_message="Gateway Timeout: Upstream order-service hung",
            )
        )

        order_span_id = f"span-order-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=root_span_id,
                service_name="order-service",
                operation_name="ShippingClient.create_consignment",
                start_time_offset_ms=10.0,
                duration_ms=14980.0,
                status_code=500,
                has_error=True,
                error_message="ReadTimeout: Request to third-party shipping hung without circuit break",
                attributes={
                    "client.timeout_configured_s": 60.0,
                    "client.expected_sla_s": 2.0,
                    "code.filepath": "app/clients/shipping_client.py",
                },
            )
        )

        ship_span_id = f"span-ship-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=ship_span_id,
                parent_span_id=order_span_id,
                service_name="third-party-shipping",
                operation_name="POST /v2/shipments",
                start_time_offset_ms=15.0,
                duration_ms=14950.0,
                status_code=408,
                has_error=True,
                error_message="Upstream partner latency degraded",
            )
        )

        tree = TraceTree(
            trace_id=trace_id,
            root_span_id=root_span_id,
            spans=spans,
            total_duration_ms=15000.0,
            has_error=True,
            summary="Cascading thread exhaustion: Shipping client timeout misconfigured to 60s",
        )
        self._traces_buffer.append(tree)
        return tree

    def generate_memory_leak_trace(self) -> TraceTree:
        """
        Generates trace for Scenario 3: MEMORY_LEAK in inventory-service.
        """
        trace_id = f"trace-incident-oom-{uuid.uuid4().hex[:8]}"
        root_span_id = f"span-gw-{uuid.uuid4().hex[:8]}"
        spans: List[TraceSpan] = []

        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=root_span_id,
                service_name="api-gateway",
                operation_name="GET /api/v1/inventory/sku_882",
                start_time_offset_ms=0.0,
                duration_ms=5200.0,
                status_code=502,
                has_error=True,
                error_message="Bad Gateway: inventory-service connection reset by peer (Pod OOMKilled)",
            )
        )

        inv_span_id = f"span-inv-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=inv_span_id,
                parent_span_id=root_span_id,
                service_name="inventory-service",
                operation_name="SkuCache.get_cached_sku_payload",
                start_time_offset_ms=5.0,
                duration_ms=5180.0,
                status_code=500,
                has_error=True,
                error_message="KilledProcess: SIGKILL signal received (cgroup memory limit 2Gi exceeded)",
                attributes={
                    "k8s.termination_reason": "OOMKilled",
                    "k8s.exit_code": 137,
                    "code.filepath": "app/services/sku_cache.py",
                },
            )
        )

        tree = TraceTree(
            trace_id=trace_id,
            root_span_id=root_span_id,
            spans=spans,
            total_duration_ms=5200.0,
            has_error=True,
            summary="Pod OOMKilled (Exit 137): Unbounded dictionary growth in SkuCache",
        )
        self._traces_buffer.append(tree)
        return tree

    def generate_redis_stampede_trace(self) -> TraceTree:
        """
        Generates trace for Scenario 4: REDIS_STAMPEDE.
        """
        trace_id = f"trace-incident-stampede-{uuid.uuid4().hex[:8]}"
        root_span_id = f"span-gw-{uuid.uuid4().hex[:8]}"
        spans: List[TraceSpan] = []

        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=root_span_id,
                service_name="api-gateway",
                operation_name="GET /api/v1/categories/top",
                start_time_offset_ms=0.0,
                duration_ms=1850.0,
                status_code=200,
                has_error=False,
            )
        )

        order_span_id = f"span-order-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=order_span_id,
                parent_span_id=root_span_id,
                service_name="order-service",
                operation_name="CatalogCacheManager.get_category_items",
                start_time_offset_ms=5.0,
                duration_ms=1840.0,
                status_code=200,
            )
        )

        # Cache Miss Span
        redis_span_id = f"span-redis-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=redis_span_id,
                parent_span_id=order_span_id,
                service_name="redis-cache",
                operation_name="GET catalog:category:101",
                start_time_offset_ms=6.0,
                duration_ms=1.5,
                status_code=200,
                attributes={"cache.hit": False, "cache.key": "catalog:category:101"},
            )
        )

        # Fallback surge to primary database
        db_span_id = f"span-db-{uuid.uuid4().hex[:8]}"
        spans.append(
            TraceSpan(
                trace_id=trace_id,
                span_id=db_span_id,
                parent_span_id=order_span_id,
                service_name="postgres-primary",
                operation_name="SELECT * FROM categories JOIN items ...",
                start_time_offset_ms=8.0,
                duration_ms=1820.0,
                status_code=200,
                attributes={
                    "db.statement": "SELECT * FROM categories JOIN items ON categories.id = items.category_id",
                    "db.query_queue_time_ms": 1650.0,
                    "db.cpu_pct": 96.0,
                },
            )
        )

        tree = TraceTree(
            trace_id=trace_id,
            root_span_id=root_span_id,
            spans=spans,
            total_duration_ms=1850.0,
            has_error=False,
            summary="Thundering herd cache stampede: All category keys expired at same second",
        )
        self._traces_buffer.append(tree)
        return tree

    def generate_metric_series(
        self,
        service_name: str,
        is_incident: bool = False,
        scenario_id: Optional[ChaosScenarioId] = None,
        duration_points: int = 15,
    ) -> List[MetricPoint]:
        """
        Generates realistic 15-minute time-series points leading up to an incident.
        """
        points = []
        for i in range(duration_points):
            offset_s = -(duration_points - i) * 60

            # Normal baseline
            p99 = 25.0 + random.uniform(-3, 3)
            err = 0.001
            cpu = 20.0 + random.uniform(-2, 2)
            mem = 35.0 + random.uniform(-2, 2)
            pool = 20.0 + random.uniform(-3, 3)

            # If incident is active and we are in the last 5 minutes
            if is_incident and i >= (duration_points - 5):
                severity_factor = (i - (duration_points - 6)) / 5.0
                if scenario_id == ChaosScenarioId.N_PLUS_ONE_QUERY:
                    if service_name in ["payment-service", "api-gateway"]:
                        p99 = 25.0 + (2400.0 * severity_factor)
                        err = 0.001 + (0.35 * severity_factor)
                    if service_name == "postgres-primary":
                        pool = 20.0 + (78.0 * severity_factor)
                        cpu = 20.0 + (65.0 * severity_factor)
                elif scenario_id == ChaosScenarioId.CASCADING_TIMEOUT:
                    if service_name in ["order-service", "api-gateway"]:
                        p99 = 35.0 + (14000.0 * severity_factor)
                        err = 0.001 + (0.60 * severity_factor)
                elif scenario_id == ChaosScenarioId.MEMORY_LEAK:
                    if service_name == "inventory-service":
                        mem = 35.0 + (64.0 * severity_factor)
                        if mem > 95.0:
                            err = 0.40
                elif scenario_id == ChaosScenarioId.REDIS_STAMPEDE:
                    if service_name == "postgres-primary":
                        cpu = 30.0 + (65.0 * severity_factor)
                        p99 = 8.0 + (1800.0 * severity_factor)

            points.append(
                MetricPoint(
                    timestamp_offset_s=offset_s,
                    p99_latency_ms=round(p99, 1),
                    error_rate=round(err, 4),
                    throughput_rps=round(120.0 + random.uniform(-10, 10), 1),
                    cpu_pct=round(min(100.0, cpu), 1),
                    memory_pct=round(min(100.0, mem), 1),
                    connection_pool_pct=round(min(100.0, pool), 1),
                )
            )
        return points

    def get_recent_traces(self, limit: int = 10) -> List[TraceTree]:
        return self._traces_buffer[-limit:]
