"""
Deterministic Diagnostic Tools for SentinelOps SRE Agents.
Provides high-fidelity inspection over metrics, traces, AST diffs, and topology cycles.
"""

from typing import Dict, Any, List, Optional
from app.graph_rag.topology import ServiceTopology
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.ast_analyzer.visitor import CodeASTAnalyzer


class AgentToolRegistry:
    """
    Tool registry exposing deterministic diagnostic capabilities to the investigator agent.
    """

    def __init__(
        self,
        topology: ServiceTopology,
        telemetry: TelemetryEngine,
        git_tracker: GitTracker,
        inferrer: Optional[DynamicTopologyInferrer] = None,
    ):
        self.topology = topology
        self.telemetry = telemetry
        self.git_tracker = git_tracker
        self.inferrer = inferrer or DynamicTopologyInferrer(topology)

    def query_service_metrics(self, service_name: str, window_mins: int = 15) -> Dict[str, Any]:
        """Queries Prometheus time-series metrics for a microservice."""
        node = self.topology.get_node(service_name)
        if not node:
            return {"error": f"Service '{service_name}' not found in mesh."}

        series = self.telemetry.generate_metric_series(service_name=service_name, duration_points=window_mins)
        latest = series[-1] if series else None

        return {
            "service_name": service_name,
            "status": node.status.value,
            "current_p99_latency_ms": node.p99_latency_ms,
            "current_error_rate_pct": round(node.error_rate * 100, 2),
            "cpu_pct": node.cpu_pct,
            "memory_pct": node.memory_pct,
            "connection_pool_pct": node.connection_pool_pct,
            "recent_samples_count": len(series),
            "latest_trend": latest.model_dump() if latest else None,
        }

    def query_trace_anomalies(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Scans recent distributed traces for latency outliers and repetition patterns."""
        traces = self.telemetry.get_recent_traces(limit=5)
        anomalies = []

        for trace in traces:
            for span in trace.spans:
                if service_name and span.service_name != service_name:
                    continue

                if span.has_error or span.duration_ms > 200.0 or "anomaly.detected_pattern" in span.attributes:
                    anomalies.append({
                        "trace_id": span.trace_id,
                        "span_id": span.span_id,
                        "service_name": span.service_name,
                        "operation_name": span.operation_name,
                        "duration_ms": span.duration_ms,
                        "has_error": span.has_error,
                        "error_message": span.error_message,
                        "attributes": span.attributes,
                    })

        return {
            "total_traces_scanned": len(traces),
            "anomalous_spans_count": len(anomalies),
            "anomalous_spans": anomalies[:6],
        }

    def get_recent_commits(self, service_name: str, max_age_mins: int = 120) -> Dict[str, Any]:
        """Fetches recent git commits and authors for a specific service."""
        commits = self.git_tracker.get_recent_commits(service_name=service_name, max_age_mins=max_age_mins)
        return {
            "service_name": service_name,
            "commits_count": len(commits),
            "commits": [
                {
                    "commit_hash": c.commit_hash,
                    "author": c.author,
                    "mins_ago": c.timestamp_mins_ago,
                    "message": c.message,
                    "files_changed": c.files_changed,
                    "risk_score": c.risk_score,
                }
                for c in commits
            ],
        }

    def inspect_commit_ast(self, commit_hash: str) -> Dict[str, Any]:
        """Runs the AST Syntax Analyzer on a candidate git commit diff."""
        commit = self.git_tracker.get_commit_by_hash(commit_hash)
        if not commit:
            return {"error": f"Commit '{commit_hash}' not found."}

        # Analyze diff using AST analyzer
        target_fn = commit.files_changed[0] if commit.files_changed else "diff.py"
        ast_report = CodeASTAnalyzer.analyze_diff(commit.diff, filename=target_fn)

        return {
            "commit_hash": commit_hash,
            "service_name": commit.service_name,
            "author": commit.author,
            "message": commit.message,
            "has_critical_violations": ast_report.has_critical_violations,
            "violations_count": len(ast_report.violations),
            "violations": [v.model_dump() for v in ast_report.violations],
            "diff_snippet": commit.diff[:500],
        }

    def check_mesh_cycles(self) -> Dict[str, Any]:
        """Checks the dynamic service topology for circular call loops."""
        cycles = self.inferrer.detect_circular_dependencies()
        return {
            "has_cycles": len(cycles) > 0,
            "cycles": cycles,
        }
