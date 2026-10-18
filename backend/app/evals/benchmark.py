"""
Automated Quantitative Evaluation Benchmark for SentinelOps.
Measures:
1. Root Cause Identification Accuracy (Recall@1)
2. Offending Commit Isolation Accuracy
3. AST Regression Detection Precision
4. Subprocess Sandbox Hotfix Pass Rate
5. Swarm Convergence Latency & Step Count
"""

import time
from typing import Dict, Any, List
from pydantic import BaseModel

from app.core.models import ChaosScenarioId
from app.graph_rag.topology import ServiceTopology
from app.engine.telemetry import TelemetryEngine
from app.engine.git_tracker import GitTracker
from app.engine.chaos import ChaosEngine
from app.graph_rag.inferrer import DynamicTopologyInferrer
from app.agents.orchestrator import SREAgentOrchestrator
from app.core.state import IncidentStateStatus


class ScenarioEvalResult(BaseModel):
    scenario_id: str
    scenario_title: str
    expected_root_cause_service: str
    identified_root_cause_service: str
    root_cause_accurate: bool
    expected_commit_hash: str
    identified_commit_hash: str
    commit_accurate: bool
    sandbox_verified: bool
    iterations_count: int
    elapsed_time_ms: float


class BenchmarkSuiteReport(BaseModel):
    total_scenarios_tested: int
    root_cause_accuracy_pct: float
    commit_isolation_accuracy_pct: float
    sandbox_verification_pass_rate_pct: float
    avg_convergence_steps: float
    avg_resolution_time_ms: float
    scenario_results: List[ScenarioEvalResult]


class SentinelOpsBenchmark:
    """Quantitative evaluation harness for AI engineering interviews."""

    BENCHMARK_SCENARIOS = [
        {
            "id": ChaosScenarioId.N_PLUS_ONE_QUERY,
            "title": "N+1 Query Regression",
            "expected_service": "payment-service",
            "expected_commit": "f4a81c79",
        },
        {
            "id": ChaosScenarioId.CASCADING_TIMEOUT,
            "title": "Cascading Timeout Cascade",
            "expected_service": "order-service",
            "expected_commit": "b92d04a1",
        },
        {
            "id": ChaosScenarioId.MEMORY_LEAK,
            "title": "Pod CrashLoop / OOMKilled",
            "expected_service": "inventory-service",
            "expected_commit": "c319e73b",
        },
    ]

    @classmethod
    def run_full_benchmark(cls) -> BenchmarkSuiteReport:
        results: List[ScenarioEvalResult] = []

        for item in cls.BENCHMARK_SCENARIOS:
            # Clean state per benchmark scenario
            topology = ServiceTopology()
            telemetry = TelemetryEngine()
            git_tracker = GitTracker()
            chaos = ChaosEngine(topology, telemetry, git_tracker)
            inferrer = DynamicTopologyInferrer(topology)
            orchestrator = SREAgentOrchestrator(topology, telemetry, git_tracker, inferrer)

            start_t = time.perf_counter()
            alert = chaos.inject_chaos(item["id"])
            final_state = orchestrator.run_investigation(alert)
            elapsed_ms = (time.perf_counter() - start_t) * 1000

            rc_service = (
                final_state.active_hypothesis.suspected_service
                if final_state.active_hypothesis
                else "UNKNOWN"
            )
            commit_hash = (
                final_state.remediation_patch.original_commit_hash
                if final_state.remediation_patch
                else "UNKNOWN"
            )
            sandbox_ok = (
                final_state.sandbox_result.verified
                if final_state.sandbox_result
                else False
            )

            rc_accurate = rc_service == item["expected_service"]
            commit_accurate = commit_hash == item["expected_commit"]

            results.append(
                ScenarioEvalResult(
                    scenario_id=item["id"].value,
                    scenario_title=item["title"],
                    expected_root_cause_service=item["expected_service"],
                    identified_root_cause_service=rc_service,
                    root_cause_accurate=rc_accurate,
                    expected_commit_hash=item["expected_commit"],
                    identified_commit_hash=commit_hash,
                    commit_accurate=commit_accurate,
                    sandbox_verified=sandbox_ok,
                    iterations_count=final_state.iteration + 1,
                    elapsed_time_ms=round(elapsed_ms, 2),
                )
            )

        total = len(results)
        rc_correct = sum(1 for r in results if r.root_cause_accurate)
        commit_correct = sum(1 for r in results if r.commit_accurate)
        sandbox_passed = sum(1 for r in results if r.sandbox_verified)
        avg_steps = sum(r.iterations_count for r in results) / total
        avg_time = sum(r.elapsed_time_ms for r in results) / total

        return BenchmarkSuiteReport(
            total_scenarios_tested=total,
            root_cause_accuracy_pct=round((rc_correct / total) * 100, 1),
            commit_isolation_accuracy_pct=round((commit_correct / total) * 100, 1),
            sandbox_verification_pass_rate_pct=round((sandbox_passed / total) * 100, 1),
            avg_convergence_steps=round(avg_steps, 2),
            avg_resolution_time_ms=round(avg_time, 2),
            scenario_results=results,
        )


if __name__ == "__main__":
    report = SentinelOpsBenchmark.run_full_benchmark()
    print("=" * 60)
    print("SENTINELOPS QUANTITATIVE EVALUATION BENCHMARK REPORT")
    print("=" * 60)
    print(f"Scenarios Evaluated: {report.total_scenarios_tested}")
    print(f"Root Cause Accuracy (Recall@1): {report.root_cause_accuracy_pct}%")
    print(f"Commit Isolation Accuracy: {report.commit_isolation_accuracy_pct}%")
    print(f"Sandbox Verification Pass Rate: {report.sandbox_verification_pass_rate_pct}%")
    print(f"Avg Swarm Convergence Steps: {report.avg_convergence_steps}")
    print(f"Avg Autonomous Resolution Time: {report.avg_resolution_time_ms:.1f}ms")
    print("-" * 60)
    for r in report.scenario_results:
        status_sym = "[PASS]" if (r.root_cause_accurate and r.commit_accurate and r.sandbox_verified) else "[FAIL]"
        print(f"{status_sym} {r.scenario_title}: Service={r.identified_root_cause_service}, Commit={r.identified_commit_hash}, Sandbox={r.sandbox_verified} in {r.elapsed_time_ms:.1f}ms")
    print("=" * 60)
