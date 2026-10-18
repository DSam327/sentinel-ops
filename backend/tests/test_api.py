"""
Unit and integration tests for SentinelOps FastAPI REST and SSE endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_get_topology_endpoint():
    response = client.get("/api/topology")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 8


def test_get_scenarios_endpoint():
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) == 4
    scenario_ids = [s["id"] for s in scenarios]
    assert "N_PLUS_ONE_QUERY" in scenario_ids
    assert "CASCADING_TIMEOUT" in scenario_ids


def test_full_incident_api_lifecycle():
    # 1. Inject Chaos
    inject_res = client.post("/api/chaos/inject/N_PLUS_ONE_QUERY")
    assert inject_res.status_code == 200
    alert_data = inject_res.json()
    assert alert_data["scenario_id"] == "N_PLUS_ONE_QUERY"

    # 2. Verify Active Incident
    active_res = client.get("/api/incident/active")
    assert active_res.status_code == 200
    assert active_res.json()["active_scenario"] == "N_PLUS_ONE_QUERY"

    # 3. Trigger Autonomous Swarm Investigation
    agent_res = client.post("/api/agent/investigate")
    assert agent_res.status_code == 200
    state_data = agent_res.json()
    assert state_data["status"] == "RESOLVED"
    assert state_data["remediation_patch"]["original_commit_hash"] == "f4a81c79"
    assert state_data["sandbox_result"]["verified"] is True

    # 4. Reset Mesh
    reset_res = client.post("/api/chaos/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "SUCCESS"


def test_otlp_trace_ingestion_endpoint():
    otlp_payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "external-order-worker"}}
                    ]
                },
                "scopeSpans": [
                    {
                        "spans": [
                            {
                                "traceId": "t-1001",
                                "spanId": "s-parent",
                                "name": "POST /worker/jobs",
                                "startTimeUnixNano": "1000000000",
                                "endTimeUnixNano": "1025000000",
                                "attributes": [{"key": "http.status_code", "value": {"intValue": 200}}],
                                "status": {"code": 0},
                            },
                            {
                                "traceId": "t-1001",
                                "spanId": "s-child",
                                "parentSpanId": "s-parent",
                                "name": "POST /payments/charge",
                                "startTimeUnixNano": "1005000000",
                                "endTimeUnixNano": "1020000000",
                                "attributes": [{"key": "payment.amount", "value": {"intValue": 99}}],
                                "status": {"code": 0},
                            },
                        ]
                    }
                ],
            }
        ]
    }
    res = client.post("/v1/traces", json=otlp_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["spans_received"] == 2

