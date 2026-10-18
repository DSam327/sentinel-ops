"""
Unit tests for ServiceTopology and Graph operations.
"""

from app.graph_rag.topology import ServiceTopology
from app.core.models import ServiceHealthStatus


def test_topology_initialization():
    topology = ServiceTopology()
    assert len(topology.graph.nodes) == 8
    assert len(topology.graph.edges) == 10
    assert "api-gateway" in topology.graph.nodes
    assert "payment-service" in topology.graph.nodes
    assert "postgres-primary" in topology.graph.nodes


def test_blast_radius_computation():
    topology = ServiceTopology()
    # When payment-service fails:
    # Upstream callers should include order-service and api-gateway
    # Downstream dependencies should include postgres-primary
    blast = topology.get_blast_radius("payment-service")
    assert "order-service" in blast.upstream_callers
    assert "api-gateway" in blast.upstream_callers
    assert "postgres-primary" in blast.downstream_dependencies
    assert "payment-service" in blast.all_affected_nodes


def test_react_flow_export_structure():
    topology = ServiceTopology()
    rf = topology.export_for_react_flow()
    assert "nodes" in rf
    assert "edges" in rf
    assert len(rf["nodes"]) == 8

    # Verify React Flow node schema
    gw_node = next(n for n in rf["nodes"] if n["id"] == "api-gateway")
    assert "position" in gw_node
    assert "x" in gw_node["position"]
    assert "data" in gw_node
    assert gw_node["data"]["status"] == ServiceHealthStatus.HEALTHY.value
    assert "p99LatencyMs" in gw_node["data"]
