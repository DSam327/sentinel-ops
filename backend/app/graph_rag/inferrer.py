"""
Dynamic Service Topology Inferrer for SentinelOps.
Constructs and updates the microservice DAG directly from raw, unstructured OpenTelemetry spans.
Computes real-time edge latencies, error rates, and cyclic dependency regressions.
"""

from typing import List, Dict, Tuple, Any, Optional
from collections import defaultdict
import numpy as np
import networkx as nx

from app.core.models import TraceSpan, ServiceEdge, ProtocolType
from app.graph_rag.topology import ServiceTopology


class InferredDependencyEdge:
    def __init__(self, source: str, target: str):
        self.source = source
        self.target = target
        self.latencies_ms: List[float] = []
        self.error_count: int = 0
        self.call_count: int = 0

    def record_call(self, duration_ms: float, has_error: bool) -> None:
        self.latencies_ms.append(duration_ms)
        self.call_count += 1
        if has_error:
            self.error_count += 1

    @property
    def p99_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.percentile(self.latencies_ms, 99))

    @property
    def p50_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return float(np.percentile(self.latencies_ms, 50))

    @property
    def error_rate(self) -> float:
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count


class DynamicTopologyInferrer:
    """
    Ingests flat streams of OpenTelemetry spans, reconstructs call trees,
    and dynamically infers service dependency topology and health metrics.
    """

    def __init__(self, topology: ServiceTopology):
        self.topology = topology
        self.inferred_edges: Dict[Tuple[str, str], InferredDependencyEdge] = {}

    def ingest_spans(self, spans: List[TraceSpan]) -> Dict[str, Any]:
        """
        Ingests a batch of raw trace spans and updates the live topology.
        Returns inference summary including any discovered cycles or anomalies.
        """
        # 1. Group spans by trace_id and index by span_id
        traces: Dict[str, Dict[str, TraceSpan]] = defaultdict(dict)
        for span in spans:
            traces[span.trace_id][span.span_id] = span

        new_edges_discovered = 0

        # 2. Reconstruct parent-child invocations
        for trace_id, span_map in traces.items():
            for span_id, span in span_map.items():
                if span.parent_span_id and span.parent_span_id in span_map:
                    parent_span = span_map[span.parent_span_id]
                    # If crosses service boundary, record edge
                    if parent_span.service_name != span.service_name:
                        edge_key = (parent_span.service_name, span.service_name)
                        if edge_key not in self.inferred_edges:
                            self.inferred_edges[edge_key] = InferredDependencyEdge(
                                source=parent_span.service_name,
                                target=span.service_name,
                            )
                            new_edges_discovered += 1

                        self.inferred_edges[edge_key].record_call(
                            duration_ms=span.duration_ms,
                            has_error=span.has_error or span.status_code >= 400,
                        )

        # 3. Synchronize inferred metrics into live NetworkX topology
        for (u, v), edge_data in self.inferred_edges.items():
            if self.topology.graph.has_edge(u, v):
                self.topology.update_edge_status(
                    source=u,
                    target=v,
                    current_latency_ms=round(edge_data.p99_latency_ms, 1),
                    error_rate=round(edge_data.error_rate, 4),
                )
            else:
                # Add newly inferred dynamic edge to the graph
                new_edge = ServiceEdge(
                    source=u,
                    target=v,
                    protocol=ProtocolType.HTTP,
                    normal_latency_ms=round(edge_data.p50_latency_ms, 1),
                    current_latency_ms=round(edge_data.p99_latency_ms, 1),
                    error_rate=round(edge_data.error_rate, 4),
                )
                self.topology.graph.add_edge(u, v, data=new_edge)

        # 4. Detect topological anomalies: Cycles
        cycles = self.detect_circular_dependencies()

        return {
            "spans_processed": len(spans),
            "traces_processed": len(traces),
            "total_inferred_edges": len(self.inferred_edges),
            "new_edges_discovered": new_edges_discovered,
            "circular_dependencies": cycles,
        }

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detects if any circular call loops have formed in the microservice mesh (A -> B -> C -> A).
        """
        try:
            return list(nx.simple_cycles(self.topology.graph))
        except Exception:
            return []
