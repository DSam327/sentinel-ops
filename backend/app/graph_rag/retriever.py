"""
Hybrid Graph + Temporal Trace RAG Retriever for SentinelOps.
Combines structural topology graph traversal with temporal trace span anomaly detection and commit indexing.
"""

import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pydantic import BaseModel

from app.core.models import (
    IncidentAlert,
    TraceSpan,
    TraceTree,
    GitCommit,
    SubgraphContext,
)
from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.graph_rag.vector_store import SemanticTextStore


class AnomalousSpanEvidence(BaseModel):
    service_name: str
    operation_name: str
    duration_ms: float
    has_error: bool
    error_message: Optional[str] = None
    attributes: Dict[str, Any] = {}
    anomaly_reason: str


class SuspectCommitEvidence(BaseModel):
    commit_hash: str
    author: str
    timestamp_mins_ago: int
    service_name: str
    message: str
    relevance_score: float
    diff_snippet: str


class IncidentEvidenceBundle(BaseModel):
    alert_id: str
    firing_service: str
    blast_radius: SubgraphContext
    suspect_services_ranked: List[str]
    anomalous_spans: List[AnomalousSpanEvidence]
    suspect_commits: List[SuspectCommitEvidence]
    structural_critical_path: List[str]


class GraphRAGRetriever:
    """
    Core retrieval engine for SRE Root Cause Analysis.
    Performs multi-hop graph expansion + temporal trace anomaly scoring.
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
        self.vector_store = SemanticTextStore()
        self._index_git_commits()

    def _index_git_commits(self) -> None:
        """Indexes all git commits into the semantic vector store."""
        for commit in self.git_tracker.get_recent_commits(max_age_mins=360):
            doc_content = f"{commit.message}\n{commit.diff}\nService: {commit.service_name}"
            self.vector_store.add_document(
                doc_id=commit.commit_hash,
                content=doc_content,
                metadata={
                    "commit_hash": commit.commit_hash,
                    "service_name": commit.service_name,
                    "author": commit.author,
                    "message": commit.message,
                },
            )
        self.vector_store.build_index()

    def retrieve_incident_evidence(self, alert: IncidentAlert) -> IncidentEvidenceBundle:
        """
        Main RAG entry point:
        1. Topologically traverse the mesh from the firing service.
        2. Mine temporal trace spans for latency outliers and repetition patterns.
        3. Retrieve and rank recent git commits matching the observed failure signatures.
        """
        # Step 1: Topological Blast Radius & Suspect Services
        blast_radius = self.topology.get_blast_radius(alert.firing_service)
        all_candidate_services = blast_radius.all_affected_nodes

        # Rank services by health deviation
        service_health_scores = []
        for s_name in all_candidate_services:
            node = self.topology.get_node(s_name)
            if node:
                score = (
                    (node.p99_latency_ms / 25.0)
                    + (node.error_rate * 50.0)
                    + (node.connection_pool_pct / 20.0)
                    + (node.memory_pct / 25.0)
                )
                service_health_scores.append((s_name, score))

        # Higher score = more anomalous
        service_health_scores.sort(key=lambda x: x[1], reverse=True)
        suspect_services_ranked = [s[0] for s in service_health_scores]

        # Step 2: Temporal Trace Mining (Statistical Z-Score + Query Fingerprinting)
        recent_traces = self.telemetry.get_recent_traces(limit=5)
        anomalous_spans: List[AnomalousSpanEvidence] = []
        error_context_text = f"{alert.title} {alert.firing_service} "

        # Compute rolling distribution baseline across recent spans
        all_durations = [s.duration_ms for t in recent_traces for s in t.spans]
        mean_dur = float(np.mean(all_durations)) if all_durations else 25.0
        std_dur = float(np.std(all_durations)) if all_durations and len(all_durations) > 1 else 10.0
        if std_dur == 0:
            std_dur = 1.0

        # Cluster and count repeating query fingerprints per parent span
        query_fingerprints: Dict[Tuple[str, str], int] = defaultdict(int)
        for trace in recent_traces:
            for span in trace.spans:
                stmt = span.attributes.get("db.statement")
                if stmt:
                    normalized = re.sub(r"'[^']*'|\b\d+\b", "?", stmt).strip()
                    query_fingerprints[(span.parent_span_id or "root", normalized)] += 1

        for trace in recent_traces:
            for span in trace.spans:
                z_score = (span.duration_ms - mean_dur) / std_dur
                is_z_outlier = z_score >= 2.5
                is_duration_outlier = span.duration_ms > 200.0
                is_error = span.has_error or span.status_code >= 400

                # Check for repeated query loop pattern under parent
                stmt = span.attributes.get("db.statement")
                repetition_count = 0
                if stmt:
                    normalized = re.sub(r"'[^']*'|\b\d+\b", "?", stmt).strip()
                    repetition_count = query_fingerprints.get((span.parent_span_id or "root", normalized), 0)
                is_query_loop = repetition_count >= 5

                if is_z_outlier or is_duration_outlier or is_error or is_query_loop:
                    reason = []
                    if is_error:
                        reason.append(f"Status {span.status_code}: {span.error_message}")
                        error_context_text += f" {span.error_message or ''} "
                    if is_z_outlier:
                        reason.append(f"Latency z-score Z={z_score:.1f} ({span.duration_ms:.1f}ms)")
                        error_context_text += f" latency_outlier {span.duration_ms:.0f}ms "
                    elif is_duration_outlier:
                        reason.append(f"Elevated duration ({span.duration_ms:.1f}ms)")
                    if is_query_loop:
                        reason.append(f"Repeated query loop ({repetition_count}x calls under parent)")
                        error_context_text += " sequential_query_loop N+1 "

                    anomalous_spans.append(
                        AnomalousSpanEvidence(
                            service_name=span.service_name,
                            operation_name=span.operation_name,
                            duration_ms=span.duration_ms,
                            has_error=span.has_error,
                            error_message=span.error_message,
                            attributes=span.attributes,
                            anomaly_reason="; ".join(reason),
                        )
                    )

        # Step 3: Git Commit Relevance Ranking via Hybrid RAG
        suspect_commits: List[SuspectCommitEvidence] = []
        search_query = f"{alert.title} {error_context_text} timeout loop database memory pool cache"

        for s_name in suspect_services_ranked[:4]:
            service_commits = self.git_tracker.get_recent_commits(service_name=s_name, max_age_mins=120)
            for commit in service_commits:
                # Query vector store for this commit's relevance
                vector_results = self.vector_store.search(
                    query=search_query, top_k=5, filter_service=s_name
                )
                rel_score = 0.2  # baseline proximity score
                for chunk, sim in vector_results:
                    if chunk.metadata.get("commit_hash") == commit.commit_hash:
                        rel_score = max(rel_score, sim)

                # Prioritize commits with high risk score or matching diff tokens
                composite_score = round(rel_score * 0.6 + commit.risk_score * 0.4, 3)

                suspect_commits.append(
                    SuspectCommitEvidence(
                        commit_hash=commit.commit_hash,
                        author=commit.author,
                        timestamp_mins_ago=commit.timestamp_mins_ago,
                        service_name=commit.service_name,
                        message=commit.message,
                        relevance_score=composite_score,
                        diff_snippet=commit.diff[:450],
                    )
                )

        # Sort suspect commits by relevance score descending
        suspect_commits.sort(key=lambda x: x.relevance_score, reverse=True)

        # Step 4: Compute Structural Critical Path
        critical_path = [alert.firing_service]
        for s in suspect_services_ranked:
            if s not in critical_path:
                critical_path.append(s)

        return IncidentEvidenceBundle(
            alert_id=alert.alert_id,
            firing_service=alert.firing_service,
            blast_radius=blast_radius,
            suspect_services_ranked=suspect_services_ranked,
            anomalous_spans=anomalous_spans[:8],
            suspect_commits=suspect_commits[:5],
            structural_critical_path=critical_path[:4],
        )
