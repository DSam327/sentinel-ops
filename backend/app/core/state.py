"""
State definitions for SentinelOps Multi-Agent SRE Swarm.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.core.models import (
    IncidentAlert,
    SubgraphContext,
    GitCommit,
    TraceSpan,
)
from app.sandbox.runner import SandboxVerificationResult


class IncidentStateStatus(str, Enum):
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    VERIFYING = "VERIFYING"
    REMEDIATING = "REMEDIATING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class AgentRole(str, Enum):
    TRIAGE = "TRIAGE"
    INVESTIGATOR = "INVESTIGATOR"
    SKEPTIC = "SKEPTIC"
    REMEDIATOR = "REMEDIATOR"


class AgentThoughtStep(BaseModel):
    step_id: str
    role: AgentRole
    thought: str
    tool_name: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    timestamp: str


class Hypothesis(BaseModel):
    id: str
    suspected_service: str
    root_cause_type: str
    confidence: float
    reasoning: str
    is_refuted: bool = False
    refutation_reason: Optional[str] = None


class SkepticReview(BaseModel):
    approved: bool
    confidence_score: float
    critique: str
    counter_evidence: List[str] = []
    required_followup_tool: Optional[str] = None


class RemediationPatch(BaseModel):
    service_name: str
    target_file: str
    commit_author_blamed: str
    original_commit_hash: str
    proposed_code: str
    unified_diff: str
    explanation: str


class SREIncidentState(BaseModel):
    alert: IncidentAlert
    status: IncidentStateStatus = IncidentStateStatus.TRIAGING
    iteration: int = 0
    max_iterations: int = 5
    blast_radius: Optional[SubgraphContext] = None
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    active_hypothesis: Optional[Hypothesis] = None
    thought_history: List[AgentThoughtStep] = Field(default_factory=list)
    skeptic_reviews: List[SkepticReview] = Field(default_factory=list)
    remediation_patch: Optional[RemediationPatch] = None
    sandbox_result: Optional[SandboxVerificationResult] = None
    final_rca_report: Optional[str] = None
