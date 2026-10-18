"""
Service Mesh Dependency Topology using NetworkX for SentinelOps.
Provides graph traversal, blast radius computation, and React Flow UI export.
"""

from typing import Dict, List, Optional, Any, Tuple
import networkx as nx
from app.core.models import (
    ServiceNode,
    ServiceEdge,
    ServiceHealthStatus,
    ServiceType,
    ProtocolType,
    SubgraphContext,
)


class ServiceTopology:
    """
    Maintains the directed dependency graph of the microservice architecture.
    Edges represent dependencies: (Caller) -> (Callee / Dependency).
    """

    def __init__(self):
        self.graph = nx.DiGraph()
        self._initialize_default_mesh()

    def _initialize_default_mesh(self) -> None:
        """
        Builds a canonical high-scale e-commerce/fintech microservice mesh.
        """
        # Define Nodes
        services = [
            ServiceNode(
                name="api-gateway",
                service_type=ServiceType.GATEWAY,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=28.0,
                error_rate=0.0005,
                cpu_pct=24.0,
                memory_pct=35.0,
                connection_pool_pct=18.0,
                metadata={"tier": "ingress", "replicas": 6},
            ),
            ServiceNode(
                name="auth-service",
                service_type=ServiceType.SERVICE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=12.0,
                error_rate=0.0002,
                cpu_pct=18.0,
                memory_pct=28.0,
                connection_pool_pct=12.0,
                metadata={"tier": "core", "replicas": 4},
            ),
            ServiceNode(
                name="order-service",
                service_type=ServiceType.SERVICE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=35.0,
                error_rate=0.0008,
                cpu_pct=32.0,
                memory_pct=42.0,
                connection_pool_pct=25.0,
                metadata={"tier": "business", "replicas": 5},
            ),
            ServiceNode(
                name="payment-service",
                service_type=ServiceType.SERVICE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=45.0,
                error_rate=0.0004,
                cpu_pct=28.0,
                memory_pct=38.0,
                connection_pool_pct=20.0,
                metadata={"tier": "pci-dss", "replicas": 4},
            ),
            ServiceNode(
                name="inventory-service",
                service_type=ServiceType.SERVICE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=22.0,
                error_rate=0.0003,
                cpu_pct=25.0,
                memory_pct=32.0,
                connection_pool_pct=15.0,
                metadata={"tier": "business", "replicas": 3},
            ),
            ServiceNode(
                name="postgres-primary",
                service_type=ServiceType.DATABASE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=8.0,
                error_rate=0.0001,
                cpu_pct=30.0,
                memory_pct=55.0,
                connection_pool_pct=35.0,
                metadata={"tier": "storage", "engine": "PostgreSQL 16", "max_conn": 500},
            ),
            ServiceNode(
                name="redis-cache",
                service_type=ServiceType.CACHE,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=2.0,
                error_rate=0.0,
                cpu_pct=15.0,
                memory_pct=40.0,
                connection_pool_pct=10.0,
                metadata={"tier": "cache", "engine": "Redis 7.2", "hit_ratio": 0.985},
            ),
            ServiceNode(
                name="third-party-shipping",
                service_type=ServiceType.THIRD_PARTY,
                status=ServiceHealthStatus.HEALTHY,
                p99_latency_ms=120.0,
                error_rate=0.002,
                cpu_pct=0.0,
                memory_pct=0.0,
                connection_pool_pct=0.0,
                metadata={"tier": "external", "sla_timeout_s": 2.5},
            ),
        ]

        for s in services:
            self.graph.add_node(s.name, data=s)

        # Define Edges: (Caller) -> (Callee)
        dependencies = [
            ServiceEdge(source="api-gateway", target="auth-service", protocol=ProtocolType.GRPC, normal_latency_ms=8.0, current_latency_ms=8.0),
            ServiceEdge(source="api-gateway", target="order-service", protocol=ProtocolType.HTTP, normal_latency_ms=20.0, current_latency_ms=20.0),
            ServiceEdge(source="order-service", target="auth-service", protocol=ProtocolType.GRPC, normal_latency_ms=5.0, current_latency_ms=5.0),
            ServiceEdge(source="order-service", target="payment-service", protocol=ProtocolType.HTTP, normal_latency_ms=25.0, current_latency_ms=25.0),
            ServiceEdge(source="order-service", target="inventory-service", protocol=ProtocolType.GRPC, normal_latency_ms=15.0, current_latency_ms=15.0),
            ServiceEdge(source="order-service", target="third-party-shipping", protocol=ProtocolType.HTTP, normal_latency_ms=110.0, current_latency_ms=110.0),
            ServiceEdge(source="payment-service", target="postgres-primary", protocol=ProtocolType.TCP, normal_latency_ms=6.0, current_latency_ms=6.0),
            ServiceEdge(source="inventory-service", target="postgres-primary", protocol=ProtocolType.TCP, normal_latency_ms=7.0, current_latency_ms=7.0),
            ServiceEdge(source="inventory-service", target="redis-cache", protocol=ProtocolType.TCP, normal_latency_ms=2.0, current_latency_ms=2.0),
            ServiceEdge(source="order-service", target="redis-cache", protocol=ProtocolType.TCP, normal_latency_ms=2.5, current_latency_ms=2.5),
        ]

        for edge in dependencies:
            self.graph.add_edge(edge.source, edge.target, data=edge)

    def get_node(self, service_name: str) -> Optional[ServiceNode]:
        if service_name in self.graph.nodes:
            return self.graph.nodes[service_name]["data"]
        return None

    def update_node_status(self, service_name: str, **kwargs) -> Optional[ServiceNode]:
        node = self.get_node(service_name)
        if node:
            for k, v in kwargs.items():
                if hasattr(node, k):
                    setattr(node, k, v)
        return node

    def update_edge_status(self, source: str, target: str, **kwargs) -> Optional[ServiceEdge]:
        if self.graph.has_edge(source, target):
            edge = self.graph[source][target]["data"]
            for k, v in kwargs.items():
                if hasattr(edge, k):
                    setattr(edge, k, v)
            return edge
        return None

    def get_upstream_callers(self, service_name: str) -> List[str]:
        """Services that directly call this service (in-edges)."""
        if service_name not in self.graph:
            return []
        return list(self.graph.predecessors(service_name))

    def get_downstream_dependencies(self, service_name: str) -> List[str]:
        """Services that this service calls (out-edges)."""
        if service_name not in self.graph:
            return []
        return list(self.graph.successors(service_name))

    def get_all_upstream_callers(self, service_name: str) -> List[str]:
        """Transitive ancestors: all callers impacted if this service degrades."""
        if service_name not in self.graph:
            return []
        # Ancestors in DiGraph where edges are Caller -> Callee
        return list(nx.ancestors(self.graph, service_name))

    def get_all_downstream_dependencies(self, service_name: str) -> List[str]:
        """Transitive descendants: all services this depends on that could be the true root cause."""
        if service_name not in self.graph:
            return []
        return list(nx.descendants(self.graph, service_name))

    def get_blast_radius(self, failing_service: str, max_hops: int = 2) -> SubgraphContext:
        """
        Computes the complete blast radius context for an incident:
        1. Upstream callers facing customer-facing degradation.
        2. Downstream dependencies that may be the actual root cause.
        """
        if failing_service not in self.graph:
            return SubgraphContext(
                failing_service=failing_service,
                upstream_callers=[],
                downstream_dependencies=[],
                all_affected_nodes=[failing_service],
                anomalous_edges=[],
            )

        upstreams = self.get_all_upstream_callers(failing_service)
        downstreams = self.get_all_downstream_dependencies(failing_service)
        affected = set([failing_service] + upstreams + downstreams)

        anomalous_edges = []
        for u, v, data in self.graph.edges(data=True):
            edge: ServiceEdge = data["data"]
            if edge.current_latency_ms > (edge.normal_latency_ms * 2.5) or edge.error_rate > 0.05:
                anomalous_edges.append({
                    "source": u,
                    "target": v,
                    "normal_latency_ms": edge.normal_latency_ms,
                    "current_latency_ms": edge.current_latency_ms,
                    "error_rate": edge.error_rate,
                })

        return SubgraphContext(
            failing_service=failing_service,
            upstream_callers=upstreams,
            downstream_dependencies=downstreams,
            all_affected_nodes=list(affected),
            anomalous_edges=anomalous_edges,
        )

    def export_for_react_flow(self) -> Dict[str, Any]:
        """
        Exports nodes and edges formatted specifically for React Flow canvas.
        Pre-computes clean hierarchical coordinates.
        """
        # Layout coordinates (X, Y)
        layout_positions = {
            "api-gateway": {"x": 400, "y": 50},
            "auth-service": {"x": 200, "y": 180},
            "order-service": {"x": 550, "y": 180},
            "payment-service": {"x": 420, "y": 320},
            "inventory-service": {"x": 680, "y": 320},
            "third-party-shipping": {"x": 880, "y": 240},
            "postgres-primary": {"x": 420, "y": 480},
            "redis-cache": {"x": 680, "y": 480},
        }

        nodes = []
        for name in self.graph.nodes:
            node_data: ServiceNode = self.graph.nodes[name]["data"]
            pos = layout_positions.get(name, {"x": 100, "y": 100})
            nodes.append({
                "id": name,
                "type": "customServiceNode",
                "position": pos,
                "data": {
                    "id": name,
                    "label": name,
                    "serviceType": node_data.service_type.value,
                    "status": node_data.status.value,
                    "p99LatencyMs": node_data.p99_latency_ms,
                    "errorRate": round(node_data.error_rate * 100, 2),
                    "cpuPct": round(node_data.cpu_pct, 1),
                    "memoryPct": round(node_data.memory_pct, 1),
                    "connPoolPct": round(node_data.connection_pool_pct, 1),
                    "metadata": node_data.metadata,
                },
            })

        edges = []
        for u, v, data in self.graph.edges(data=True):
            edge_data: ServiceEdge = data["data"]
            is_anomalous = (
                edge_data.current_latency_ms > (edge_data.normal_latency_ms * 2.0)
                or edge_data.error_rate > 0.05
            )
            edges.append({
                "id": f"e-{u}-{v}",
                "source": u,
                "target": v,
                "animated": is_anomalous,
                "style": {
                    "stroke": "#ef4444" if is_anomalous else "#64748b",
                    "strokeWidth": 3 if is_anomalous else 1.5,
                },
                "data": {
                    "protocol": edge_data.protocol.value,
                    "normalLatencyMs": edge_data.normal_latency_ms,
                    "currentLatencyMs": edge_data.current_latency_ms,
                    "errorRate": edge_data.error_rate,
                    "isAnomalous": is_anomalous,
                },
            })

        return {"nodes": nodes, "edges": edges}

    def reset_to_healthy(self) -> None:
        """Restores all nodes and edges to healthy baseline state."""
        self._initialize_default_mesh()
