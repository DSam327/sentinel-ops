"""
Data models for SentinelOps SRE Incident Engine & Graph RAG.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ServiceHealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILING = "FAILING"


class ServiceType(str, Enum):
    GATEWAY = "GATEWAY"
    SERVICE = "SERVICE"
    DATABASE = "DATABASE"
    CACHE = "CACHE"
    THIRD_PARTY = "THIRD_PARTY"


class ProtocolType(str, Enum):
    HTTP = "HTTP"
    GRPC = "GRPC"
    TCP = "TCP"


class ChaosScenarioId(str, Enum):
    N_PLUS_ONE_QUERY = "N_PLUS_ONE_QUERY"
    CASCADING_TIMEOUT = "CASCADING_TIMEOUT"
    MEMORY_LEAK = "MEMORY_LEAK"
    REDIS_STAMPEDE = "REDIS_STAMPEDE"


class ServiceNode(BaseModel):
    name: str
    service_type: ServiceType
    status: ServiceHealthStatus = ServiceHealthStatus.HEALTHY
    p99_latency_ms: float = 25.0
    error_rate: float = 0.001  # fraction e.g. 0.1%
    cpu_pct: float = 20.0
    memory_pct: float = 30.0
    connection_pool_pct: float = 15.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ServiceEdge(BaseModel):
    source: str
    target: str
    protocol: ProtocolType = ProtocolType.HTTP
    normal_latency_ms: float = 10.0
    current_latency_ms: float = 10.0
    error_rate: float = 0.0
    call_rate_rpm: int = 1200


class TraceSpan(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time_offset_ms: float = 0.0
    duration_ms: float
    status_code: int = 200
    attributes: Dict[str, Any] = Field(default_factory=dict)
    has_error: bool = False
    error_message: Optional[str] = None


class TraceTree(BaseModel):
    trace_id: str
    root_span_id: str
    spans: List[TraceSpan]
    total_duration_ms: float
    has_error: bool
    summary: Optional[str] = None


class LogEntry(BaseModel):
    timestamp: str
    service_name: str
    level: str  # INFO, WARN, ERROR, CRITICAL
    message: str
    trace_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class GitCommit(BaseModel):
    commit_hash: str
    author: str
    timestamp_mins_ago: int
    service_name: str
    message: str
    files_changed: List[str]
    diff: str
    risk_score: float = 0.0


class MetricPoint(BaseModel):
    timestamp_offset_s: int
    p99_latency_ms: float
    error_rate: float
    throughput_rps: float
    cpu_pct: float
    memory_pct: float
    connection_pool_pct: float


class IncidentAlert(BaseModel):
    alert_id: str
    title: str
    firing_service: str
    metric_name: str
    threshold: float
    current_value: float
    timestamp: str
    severity: str = "P1-CRITICAL"
    scenario_id: Optional[ChaosScenarioId] = None


class SubgraphContext(BaseModel):
    failing_service: str
    upstream_callers: List[str]
    downstream_dependencies: List[str]
    all_affected_nodes: List[str]
    anomalous_edges: List[Dict[str, Any]]
