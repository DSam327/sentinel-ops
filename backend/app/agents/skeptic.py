"""
Adversarial Skeptic Agent for SentinelOps SRE Swarm.
Challenges diagnoses, filters out superficial symptoms, and refutes false leads.
"""

from datetime import datetime, timezone
import uuid

from app.core.state import (
    SREIncidentState,
    AgentRole,
    AgentThoughtStep,
    SkepticReview,
    IncidentStateStatus,
)


class SkepticAgent:
    """
    Adversarial reviewer. Tests whether evidence represents true root cause or downstream victim symptom.
    """

    def execute(self, state: SREIncidentState) -> SREIncidentState:
        hypothesis = state.active_hypothesis
        if not hypothesis:
            state.status = IncidentStateStatus.ESCALATED
            return state

        # Retrieve last investigation step
        last_step = state.thought_history[-1] if state.thought_history else None
        ast_findings = (
            last_step.tool_output.get("ast_findings")
            if last_step and last_step.tool_output
            else None
        )

        has_ast_proof = ast_findings and (
            ast_findings.get("has_critical_violations")
            or len(ast_findings.get("violations", [])) > 0
        )
        service = hypothesis.suspected_service

        # Refutation logic: Is this service merely a symptom?
        is_symptom_only = False
        refutation_reason = None

        if service in ["api-gateway"]:
            is_symptom_only = True
            refutation_reason = (
                "api-gateway is an ingress proxy. Latency spikes here reflect downstream callee starvation, "
                "not ingress code faults. Rejecting as primary root cause."
            )

        if is_symptom_only or not has_ast_proof:
            # Refute active hypothesis
            hypothesis.is_refuted = True
            hypothesis.refutation_reason = refutation_reason or "Insufficient AST code proof or symptom-only telemetry."

            review = SkepticReview(
                approved=False,
                confidence_score=0.20,
                critique=hypothesis.refutation_reason,
                counter_evidence=["No AST violation found in target service", "Caller is symptom of downstream blockage"],
            )
            state.skeptic_reviews.append(review)

            # Record thought step
            state.thought_history.append(
                AgentThoughtStep(
                    step_id=f"step-{uuid.uuid4().hex[:6]}",
                    role=AgentRole.SKEPTIC,
                    thought=(
                        f"REFUTED hypothesis for '{service}': {hypothesis.refutation_reason} "
                        "Pivoting to next suspect in blast radius."
                    ),
                    tool_name="adversarial_refutation",
                    tool_input={"suspected_service": service},
                    tool_output={"approved": False, "reason": hypothesis.refutation_reason},
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )

            # Advance to next non-refuted hypothesis
            remaining = [h for h in state.hypotheses if not h.is_refuted]
            state.iteration += 1

            if remaining and state.iteration < state.max_iterations:
                state.active_hypothesis = remaining[0]
                state.status = IncidentStateStatus.INVESTIGATING
            else:
                state.status = IncidentStateStatus.ESCALATED

            return state

        # Confirmation logic: Smoking gun verified
        review = SkepticReview(
            approved=True,
            confidence_score=0.96,
            critique=(
                f"VERIFIED: Commit {ast_findings.get('commit_hash')} contains verified AST violation "
                f"matching incident signature in service '{service}'."
            ),
            counter_evidence=[],
        )
        state.skeptic_reviews.append(review)

        state.thought_history.append(
            AgentThoughtStep(
                step_id=f"step-{uuid.uuid4().hex[:6]}",
                role=AgentRole.SKEPTIC,
                thought=(
                    f"CONFIRMED root cause in '{service}'. "
                    f"AST proof verified in commit {ast_findings.get('commit_hash')}. "
                    "Approved for hotfix remediation and sandbox execution."
                ),
                tool_name="adversarial_verification",
                tool_input={"service": service, "commit": ast_findings.get("commit_hash")},
                tool_output={"approved": True, "confidence": 0.96},
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        state.status = IncidentStateStatus.REMEDIATING
        return state
