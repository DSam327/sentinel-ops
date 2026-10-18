"""
Triage Agent for SentinelOps SRE Swarm.
Analyzes initial P1 alert, computes topological blast radius, and generates candidate hypotheses.
"""

from datetime import datetime, timezone
import uuid

from app.core.state import (
    SREIncidentState,
    AgentRole,
    AgentThoughtStep,
    Hypothesis,
    IncidentStateStatus,
)
from app.graph_rag.topology import ServiceTopology
from app.core.models import ServiceType


class TriageAgent:
    """
    Initial responder agent. Isolates blast radius and generates ranked hypotheses.
    """

    def __init__(self, topology: ServiceTopology):
        self.topology = topology

    def execute(self, state: SREIncidentState) -> SREIncidentState:
        firing_service = state.alert.firing_service
        blast_radius = self.topology.get_blast_radius(firing_service)
        state.blast_radius = blast_radius

        # Downstream dependencies and callers of state stores
        suspects = blast_radius.downstream_dependencies + [firing_service]

        # Rank candidate hypotheses
        hypotheses = []
        for svc in suspects:
            node = self.topology.get_node(svc)
            if not node:
                continue

            # State stores (DB, cache) reflect caller query patterns
            if node.service_type in (ServiceType.DATABASE, ServiceType.CACHE):
                if node.connection_pool_pct > 70.0 or node.cpu_pct > 80.0:
                    callers = self.topology.get_upstream_callers(svc)
                    for caller in callers:
                        hypotheses.append(
                            Hypothesis(
                                id=f"hypo-{uuid.uuid4().hex[:6]}",
                                suspected_service=caller,
                                root_cause_type="DATABASE_SATURATION_OR_N_PLUS_ONE",
                                confidence=0.92,
                                reasoning=(
                                    f"Upstream caller '{caller}' is saturating downstream storage '{svc}' "
                                    f"(pool: {node.connection_pool_pct:.1f}%, cpu: {node.cpu_pct:.1f}%)."
                                ),
                            )
                        )
                continue

            # Application Services
            if node.service_type == ServiceType.SERVICE:
                if node.connection_pool_pct > 70.0 or node.p99_latency_ms > 1000.0:
                    hypotheses.append(
                        Hypothesis(
                            id=f"hypo-{uuid.uuid4().hex[:6]}",
                            suspected_service=svc,
                            root_cause_type="DATABASE_SATURATION_OR_N_PLUS_ONE",
                            confidence=0.88,
                            reasoning=(
                                f"Service '{svc}' exhibits elevated latency ({node.p99_latency_ms:.1f}ms) "
                                f"and connection pool saturation ({node.connection_pool_pct:.1f}%)."
                            ),
                        )
                    )
                elif node.memory_pct > 80.0:
                    hypotheses.append(
                        Hypothesis(
                            id=f"hypo-{uuid.uuid4().hex[:6]}",
                            suspected_service=svc,
                            root_cause_type="MEMORY_LEAK_OR_RESOURCE_EXHAUSTION",
                            confidence=0.89,
                            reasoning=f"Service '{svc}' memory consumption is critical at {node.memory_pct:.1f}%.",
                        )
                    )
                elif node.error_rate > 0.10 or node.p99_latency_ms > 500.0:
                    hypotheses.append(
                        Hypothesis(
                            id=f"hypo-{uuid.uuid4().hex[:6]}",
                            suspected_service=svc,
                            root_cause_type="CASCADING_TIMEOUT_OR_DEPENDENCY_FAILURE",
                            confidence=0.86,
                            reasoning=f"Service '{svc}' error rate is elevated at {node.error_rate * 100:.1f}%.",
                        )
                    )
            elif node.service_type == ServiceType.GATEWAY:
                # Ingress gateway is typically a symptom
                hypotheses.append(
                    Hypothesis(
                        id=f"hypo-{uuid.uuid4().hex[:6]}",
                        suspected_service=svc,
                        root_cause_type="INGRESS_SYMPTOM",
                        confidence=0.30,
                        reasoning=f"Ingress gateway '{svc}' is reporting 5xx errors caused by downstream backpressure.",
                    )
                )

        # Fallback hypothesis if metrics are in early ramp-up
        if not hypotheses:
            hypotheses.append(
                Hypothesis(
                    id=f"hypo-{uuid.uuid4().hex[:6]}",
                    suspected_service=firing_service,
                    root_cause_type="UNKNOWN_LATENCY_SPIKE",
                    confidence=0.50,
                    reasoning=f"Alert fired on {firing_service}; investigating direct dependencies.",
                )
            )

        # Sort by confidence descending
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        state.hypotheses = hypotheses
        state.active_hypothesis = hypotheses[0]
        state.status = IncidentStateStatus.INVESTIGATING

        # Record thought step
        state.thought_history.append(
            AgentThoughtStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                role=AgentRole.TRIAGE,
                thought=(
                    f"Triage complete for alert '{state.alert.title}'. "
                    f"Computed blast radius across {len(blast_radius.all_affected_nodes)} services. "
                    f"Formulated {len(hypotheses)} hypotheses. Leading suspect: '{hypotheses[0].suspected_service}'."
                ),
                tool_name="get_blast_radius",
                tool_input={"firing_service": firing_service},
                tool_output={"affected_services": blast_radius.all_affected_nodes},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        return state
