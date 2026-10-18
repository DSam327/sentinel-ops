"""
Multi-Agent Orchestrator State Graph for SentinelOps.
Coordinates the Triage -> Investigator -> Skeptic -> Remediator loop with iteration bounds and SSE streaming.
"""

from typing import AsyncGenerator, Optional
from app.core.models import IncidentAlert
from app.core.state import (
    SREIncidentState,
    IncidentStateStatus,
    AgentThoughtStep,
)
from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.agents.tools import AgentToolRegistry
from app.agents.triage import TriageAgent
from app.agents.investigator import InvestigatorAgent
from app.agents.skeptic import SkepticAgent
from app.agents.remediator import RemediatorAgent


class SREAgentOrchestrator:
    """
    State machine orchestrator managing the adversarial multi-agent investigation lifecycle.
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
        self.tool_registry = AgentToolRegistry(
            topology=topology,
            telemetry=telemetry,
            git_tracker=git_tracker,
            inferrer=inferrer,
        )

        self.triage_agent = TriageAgent(topology)
        self.investigator_agent = InvestigatorAgent(self.tool_registry)
        self.skeptic_agent = SkepticAgent()
        self.remediator_agent = RemediatorAgent(git_tracker)

    def run_investigation(self, alert: IncidentAlert) -> SREIncidentState:
        """
        Runs the multi-agent investigation synchronously to completion.
        """
        state = SREIncidentState(alert=alert)

        # 1. Triage phase
        state = self.triage_agent.execute(state)

        # 2. Iterative Investigation & Adversarial Verification loop
        while state.status in [IncidentStateStatus.INVESTIGATING, IncidentStateStatus.VERIFYING]:
            if state.iteration >= state.max_iterations:
                state.status = IncidentStateStatus.ESCALATED
                break

            if state.status == IncidentStateStatus.INVESTIGATING:
                state = self.investigator_agent.execute(state)

            if state.status == IncidentStateStatus.VERIFYING:
                state = self.skeptic_agent.execute(state)

        # 3. Remediation phase if confirmed
        if state.status == IncidentStateStatus.REMEDIATING:
            state = self.remediator_agent.execute(state)

        return state

    async def stream_investigation(
        self, alert: IncidentAlert
    ) -> AsyncGenerator[AgentThoughtStep, None]:
        """
        Yields agent thoughts step-by-step for Server-Sent Events (SSE) streaming to the web UI.
        """
        state = SREIncidentState(alert=alert)

        # Step 1: Triage
        state = self.triage_agent.execute(state)
        yield state.thought_history[-1]

        # Step 2: Investigation & Skeptic Loop
        while state.status in [IncidentStateStatus.INVESTIGATING, IncidentStateStatus.VERIFYING]:
            if state.iteration >= state.max_iterations:
                state.status = IncidentStateStatus.ESCALATED
                break

            if state.status == IncidentStateStatus.INVESTIGATING:
                state = self.investigator_agent.execute(state)
                yield state.thought_history[-1]

            if state.status == IncidentStateStatus.VERIFYING:
                state = self.skeptic_agent.execute(state)
                yield state.thought_history[-1]

        # Step 3: Remediate
        if state.status == IncidentStateStatus.REMEDIATING:
            state = self.remediator_agent.execute(state)
            yield state.thought_history[-1]
