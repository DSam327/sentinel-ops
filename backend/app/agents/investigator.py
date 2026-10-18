"""
Investigator Agent for SentinelOps SRE Swarm.
Uses deterministic diagnostic tools to gather evidence: trace anomalies, metrics, and AST diff inspections.
"""

from datetime import datetime, timezone
import uuid

from app.core.state import (
    SREIncidentState,
    AgentRole,
    AgentThoughtStep,
    IncidentStateStatus,
)
from app.agents.tools import AgentToolRegistry


class InvestigatorAgent:
    """
    Forensic investigator. Collects metric proof, trace span outliers, and runs AST checks on commits.
    """

    def __init__(self, tool_registry: AgentToolRegistry):
        self.tools = tool_registry

    def execute(self, state: SREIncidentState) -> SREIncidentState:
        hypothesis = state.active_hypothesis
        if not hypothesis:
            state.status = IncidentStateStatus.ESCALATED
            return state

        service = hypothesis.suspected_service

        # Tool Call 1: Query Service Metrics
        metrics = self.tools.query_service_metrics(service)

        # Tool Call 2: Query Trace Anomalies
        traces = self.tools.query_trace_anomalies(service)

        # Tool Call 3: Get Recent Commits
        commits = self.tools.get_recent_commits(service)

        # Tool Call 4: AST Code Inspection on candidate commits
        ast_findings = None
        offending_commit = None
        if commits.get("commits"):
            for candidate in commits["commits"]:
                findings = self.tools.inspect_commit_ast(candidate["commit_hash"])
                if findings.get("has_critical_violations"):
                    ast_findings = findings
                    offending_commit = candidate
                    break
            if not offending_commit and commits["commits"]:
                offending_commit = commits["commits"][0]
                ast_findings = self.tools.inspect_commit_ast(offending_commit["commit_hash"])

        # Summarize evidence
        evidence_summary = (
            f"Investigated service '{service}'. "
            f"Current P99: {metrics.get('current_p99_latency_ms')}ms, "
            f"Pool: {metrics.get('connection_pool_pct')}%, "
            f"Anomalous spans found: {traces.get('anomalous_spans_count')}."
        )

        if offending_commit and ast_findings:
            violation_types = [v["violation_type"] for v in ast_findings.get("violations", [])]
            evidence_summary += (
                f" CRITICAL AST REGRESSION detected in commit {offending_commit['commit_hash']} "
                f"by {offending_commit['author']}: {violation_types}."
            )

        state.thought_history.append(
            AgentThoughtStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                role=AgentRole.INVESTIGATOR,
                thought=evidence_summary,
                tool_name="investigate_service_forensics",
                tool_input={"service_name": service},
                tool_output={
                    "metrics": metrics,
                    "anomalies": traces.get("anomalous_spans_count"),
                    "ast_findings": ast_findings,
                },
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        state.status = IncidentStateStatus.VERIFYING
        return state
