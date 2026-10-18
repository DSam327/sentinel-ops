"""
Unit tests for GraphRAGRetriever: multi-hop topological traversal,
trace anomaly detection, and semantic commit ranking.
"""

from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.engine.chaos import ChaosEngine
from app.graph_rag.retriever import GraphRAGRetriever
from app.core.models import ChaosScenarioId


def test_graph_rag_retrieves_n_plus_one_root_cause():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)
    retriever = GraphRAGRetriever(topology, telemetry, git_tracker)

    # 1. Inject N+1 Query incident
    alert = chaos.inject_chaos(ChaosScenarioId.N_PLUS_ONE_QUERY)

    # 2. Execute Graph RAG retrieval
    bundle = retriever.retrieve_incident_evidence(alert)

    # 3. Assert evidence correctly isolates the culprit
    assert bundle.firing_service == "api-gateway"
    assert "payment-service" in bundle.suspect_services_ranked

    # Assert offending commit is identified and scored highly
    commit_hashes = [c.commit_hash for c in bundle.suspect_commits]
    assert "f4a81c79" in commit_hashes

    top_commit = next(c for c in bundle.suspect_commits if c.commit_hash == "f4a81c79")
    assert top_commit.author == "alex.chen@company.internal"
    assert "eager validate" in top_commit.message

    # Assert anomalous trace spans captured the DB loop via fingerprinting or latency z-score
    assert len(bundle.anomalous_spans) > 0
    span_reasons = " ".join([s.anomaly_reason for s in bundle.anomalous_spans])
    assert "Repeated query loop" in span_reasons or "Latency z-score" in span_reasons or "Elevated duration" in span_reasons


def test_graph_rag_retrieves_cascading_timeout_root_cause():
    topology = ServiceTopology()
    telemetry = TelemetryEngine()
    git_tracker = GitTracker()
    chaos = ChaosEngine(topology, telemetry, git_tracker)
    retriever = GraphRAGRetriever(topology, telemetry, git_tracker)

    alert = chaos.inject_chaos(ChaosScenarioId.CASCADING_TIMEOUT)
    bundle = retriever.retrieve_incident_evidence(alert)

    assert "order-service" in bundle.suspect_services_ranked
    commit_hashes = [c.commit_hash for c in bundle.suspect_commits]
    assert "b92d04a1" in commit_hashes  # Shipping timeout commit
