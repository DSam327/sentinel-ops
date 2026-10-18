"""
Unit tests for DynamicTopologyInferrer: reconstructing DAGs from raw OTel spans.
"""

from app.graph_rag.topology import ServiceTopology
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.engine.telemetry import TelemetryEngine


def test_infer_topology_from_raw_spans():
    topology = ServiceTopology()
    inferrer = DynamicTopologyInferrer(topology)
    telemetry = TelemetryEngine()

    # Generate 5 healthy traces
    traces = [telemetry.generate_healthy_trace() for _ in range(5)]
    all_spans = []
    for t in traces:
        all_spans.extend(t.spans)

    summary = inferrer.ingest_spans(all_spans)

    assert summary["spans_processed"] == len(all_spans)
    assert summary["traces_processed"] == 5
    assert summary["total_inferred_edges"] > 0

    # Verify that Gateway -> Order -> Payment -> Postgres edge was inferred
    assert ("api-gateway", "order-service") in inferrer.inferred_edges
    assert ("order-service", "payment-service") in inferrer.inferred_edges
    assert ("payment-service", "postgres-primary") in inferrer.inferred_edges

    # Verify edge latency computed
    edge = inferrer.inferred_edges[("api-gateway", "order-service")]
    assert edge.call_count == 5
    assert edge.p99_latency_ms > 0.0


def test_detect_circular_dependency():
    topology = ServiceTopology()
    inferrer = DynamicTopologyInferrer(topology)

    # Artificially inject a circular edge: postgres-primary -> api-gateway
    from app.core.models import ServiceEdge, ProtocolType
    topology.graph.add_edge(
        "postgres-primary",
        "api-gateway",
        data=ServiceEdge(
            source="postgres-primary",
            target="api-gateway",
            protocol=ProtocolType.HTTP,
            normal_latency_ms=10.0,
            current_latency_ms=10.0,
        ),
    )

    cycles = inferrer.detect_circular_dependencies()
    assert len(cycles) > 0
    cycle_nodes = set().union(*cycles)
    assert "api-gateway" in cycle_nodes
    assert "postgres-primary" in cycle_nodes
