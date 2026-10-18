"""
End-to-End integration tests for SentinelOps SRE Multi-Agent Swarm.
Validates that the swarm autonomously diagnoses, verifies, and remediates all incidents.
"""

from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.engine.chaos import ChaosEngine
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.agents.orchestrator import SREAgentOrchestrator
from app.core.models import ChaosScenarioId
from app.core.state import IncidentStateStatus


def test_swarm_resolves_n_plus_one_incident():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)
    inferrer = DynamicTopologyInferrer(topology)
    orchestrator = SREAgentOrchestrator(topology, telemetry, git_tracker, inferrer)

    # 1. Trigger N+1 Query Outage
    alert = chaos.inject_chaos(ChaosScenarioId.N_PLUS_ONE_QUERY)

    # 2. Run Autonomous Swarm
    final_state = orchestrator.run_investigation(alert)

    # 3. Assertions
    assert final_state.status == IncidentStateStatus.RESOLVED
    assert final_state.active_hypothesis is not None
    assert final_state.active_hypothesis.suspected_service == "payment-service"

    # Verify offending commit identified
    assert final_state.remediation_patch is not None
    assert final_state.remediation_patch.original_commit_hash == "f4a81c79"
    assert final_state.remediation_patch.commit_author_blamed == "alex.chen@company.internal"

    # Verify sandbox passed
    assert final_state.sandbox_result is not None
    assert final_state.sandbox_result.verified is True
    assert final_state.sandbox_result.ast_check_passed is True

    # Verify postmortem report generated
    assert final_state.final_rca_report is not None
    assert "SRE Incident Postmortem" in final_state.final_rca_report
    assert "f4a81c79" in final_state.final_rca_report


def test_swarm_resolves_cascading_timeout_incident():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)
    inferrer = DynamicTopologyInferrer(topology)
    orchestrator = SREAgentOrchestrator(topology, telemetry, git_tracker, inferrer)

    alert = chaos.inject_chaos(ChaosScenarioId.CASCADING_TIMEOUT)
    final_state = orchestrator.run_investigation(alert)

    assert final_state.status == IncidentStateStatus.RESOLVED
    assert final_state.active_hypothesis.suspected_service == "order-service"
    assert final_state.remediation_patch.original_commit_hash == "b92d04a1"
    assert final_state.sandbox_result.verified is True


def test_swarm_resolves_memory_leak_incident():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)
    inferrer = DynamicTopologyInferrer(topology)
    orchestrator = SREAgentOrchestrator(topology, telemetry, git_tracker, inferrer)

    alert = chaos.inject_chaos(ChaosScenarioId.MEMORY_LEAK)
    final_state = orchestrator.run_investigation(alert)

    assert final_state.status == IncidentStateStatus.RESOLVED
    assert final_state.active_hypothesis.suspected_service == "inventory-service"
    assert final_state.remediation_patch.original_commit_hash == "c319e73b"
    assert final_state.sandbox_result.verified is True
