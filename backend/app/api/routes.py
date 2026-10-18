"""
FastAPI REST and Server-Sent Events (SSE) endpoints for SentinelOps.
Powers the live React Flow interactive visual dashboard.
"""

import json
import asyncio
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.models import ChaosScenarioId, IncidentAlert
from app.core.state import SREIncidentState, AgentThoughtStep
from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.engine.chaos import ChaosEngine
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.agents.orchestrator import SREAgentOrchestrator
from app.ast_analyzer.visitor import CodeASTAnalyzer


from app.evals.benchmark import SentinelOpsBenchmark, BenchmarkSuiteReport


# Global Singletons for Dashboard Session State
topology = ServiceTopology()
telemetry = TelemetryEngine()
git_tracker = GitTracker()
chaos = ChaosEngine(topology, telemetry, git_tracker)
inferrer = DynamicTopologyInferrer(topology)
orchestrator = SREAgentOrchestrator(topology, telemetry, git_tracker, inferrer)

router = APIRouter(prefix="/api")


class ASTInspectRequest(BaseModel):
    code_or_diff: str
    filename: str = "patch.py"


class BlastRadiusSimulateRequest(BaseModel):
    service_name: str
    error_rate: float = 0.85
    latency_p99_ms: float = 2400.0


@router.post("/benchmark/run")
def run_benchmark() -> BenchmarkSuiteReport:
    """Runs the 5-metric quantitative evaluation suite across all chaos scenarios."""
    return SentinelOpsBenchmark.run_full_benchmark()


@router.post("/topology/blast-radius")
def simulate_blast_radius(req: BlastRadiusSimulateRequest) -> Dict[str, Any]:
    """Dynamically simulates upstream and downstream blast radius for any selected service."""
    if req.service_name not in topology.graph:
        raise HTTPException(status_code=404, detail=f"Service '{req.service_name}' not found in topology.")
    
    downstream = topology.get_downstream_dependencies(req.service_name)
    upstream = topology.get_upstream_callers(req.service_name)
    blast_radius = topology.get_blast_radius(req.service_name)
    
    return {
        "service_name": req.service_name,
        "blast_radius_score": blast_radius["blast_radius_score"],
        "downstream_impacted": downstream,
        "upstream_callers_at_risk": upstream,
        "total_impacted_services": len(set(downstream + upstream)),
    }


@router.get("/topology")
def get_topology() -> Dict[str, Any]:
    """Returns the current microservice mesh formatted for React Flow."""
    return topology.export_for_react_flow()


@router.get("/scenarios")
def get_scenarios() -> List[Dict[str, str]]:
    """Returns available chaos outage scenarios for one-click injection."""
    return [
        {
            "id": ChaosScenarioId.N_PLUS_ONE_QUERY.value,
            "title": "N+1 Query Regression",
            "service": "payment-service",
            "description": "Sequential SQL calls inside user card loop, saturating Postgres pool to 98%.",
        },
        {
            "id": ChaosScenarioId.CASCADING_TIMEOUT.value,
            "title": "Cascading Timeout Cascade",
            "service": "order-service",
            "description": "Shipping client timeout set to 60s, starving thread pool and causing 504 gateway cascade.",
        },
        {
            "id": ChaosScenarioId.MEMORY_LEAK.value,
            "title": "Pod CrashLoop / OOMKilled",
            "service": "inventory-service",
            "description": "Unbounded memoization dictionary in SKU lookup causing process memory to hit 99% (Exit 137).",
        },
        {
            "id": ChaosScenarioId.REDIS_STAMPEDE.value,
            "title": "Redis Cache Stampede",
            "service": "order-service",
            "description": "All category cache TTLs expire simultaneously without jitter, surging DB CPU to 96%.",
        },
    ]


@router.post("/chaos/inject/{scenario_id}")
def inject_chaos(scenario_id: ChaosScenarioId) -> IncidentAlert:
    """Injects a chosen fault scenario into the live mesh and returns the firing alert."""
    try:
        alert = chaos.inject_chaos(scenario_id)
        return alert
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chaos/reset")
def reset_mesh() -> Dict[str, str]:
    """Resets the microservice mesh to a completely healthy baseline."""
    chaos.resolve_incident()
    return {"status": "SUCCESS", "message": "All services restored to healthy baseline."}


@router.get("/incident/active")
def get_active_incident() -> Dict[str, Any]:
    """Returns currently active alert and scenario, if any."""
    return {
        "active_incident": chaos.active_incident.model_dump() if chaos.active_incident else None,
        "active_scenario": chaos.active_scenario.value if chaos.active_scenario else None,
    }


@router.post("/agent/investigate")
def run_investigation() -> SREIncidentState:
    """Runs the multi-agent swarm synchronously and returns final RCA and hotfix PR."""
    if not chaos.active_incident:
        raise HTTPException(
            status_code=400,
            detail="No active incident. Please inject a chaos scenario first.",
        )
    return orchestrator.run_investigation(chaos.active_incident)


@router.get("/agent/stream")
async def stream_agent_investigation():
    """
    Server-Sent Events (SSE) endpoint streaming real-time agent thoughts,
    tool invocations, skeptic refutations, and verified hotfix PRs.
    """
    if not chaos.active_incident:
        raise HTTPException(
            status_code=400,
            detail="No active incident. Please inject a chaos scenario first.",
        )

    alert = chaos.active_incident

    async def event_generator():
        async for thought in orchestrator.stream_investigation(alert):
            data = json.dumps(thought.model_dump())
            yield f"data: {data}\n\n"
            await asyncio.sleep(0.4)  # Visual pacing for the live demo

        # Send terminal complete event
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/ast/inspect")
def inspect_code_ast(req: ASTInspectRequest) -> Dict[str, Any]:
    """Exposes live AST syntax analyzer for interactive UI inspection."""
    report = CodeASTAnalyzer.analyze_diff(req.code_or_diff, filename=req.filename)
    return report.model_dump()


@router.post("/v1/traces")
def ingest_otlp_traces(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standard OpenTelemetry OTLP/HTTP JSON Ingestion Endpoint.
    Accepts W3C trace hierarchies from external collectors/services and updates live mesh topology.
    """
    from app.core.models import TraceSpan

    spans_to_ingest: List[TraceSpan] = []
    resource_spans = payload.get("resourceSpans", [])

    for r_span in resource_spans:
        service_name = "unknown-service"
        for attr in r_span.get("resource", {}).get("attributes", []):
            if attr.get("key") in ("service.name", "service_name"):
                service_name = attr.get("value", {}).get("stringValue", service_name)

        for scope in r_span.get("scopeSpans", []):
            for raw_span in scope.get("spans", []):
                trace_id = raw_span.get("traceId", "trace-unknown")
                span_id = raw_span.get("spanId", "span-unknown")
                parent_id = raw_span.get("parentSpanId")
                name = raw_span.get("name", "operation")

                start_ns = int(raw_span.get("startTimeUnixNano", 0))
                end_ns = int(raw_span.get("endTimeUnixNano", start_ns))
                duration_ms = (end_ns - start_ns) / 1e6 if end_ns > start_ns else 10.0

                status_code = raw_span.get("status", {}).get("code", 0)
                has_error = status_code == 2

                attrs = {}
                for attr in raw_span.get("attributes", []):
                    k = attr.get("key")
                    v_dict = attr.get("value", {})
                    v = next(iter(v_dict.values())) if v_dict else None
                    if k:
                        attrs[k] = v

                spans_to_ingest.append(
                    TraceSpan(
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_span_id=parent_id,
                        service_name=service_name,
                        operation_name=name,
                        duration_ms=round(duration_ms, 2),
                        has_error=has_error,
                        attributes=attrs,
                    )
                )

    summary = inferrer.ingest_spans(spans_to_ingest)
    return {
        "status": "SUCCESS",
        "spans_received": len(spans_to_ingest),
        "inference_summary": summary,
    }

