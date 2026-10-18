"""
SentinelOps FastAPI Application Entry Point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router

app = FastAPI(
    title="SentinelOps",
    description="Autonomous SRE Incident Triage & Root Cause Analysis Swarm with Temporal GraphRAG and AST Sandboxing",
    version="1.0.0",
)

# Enable CORS for local Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import router, ingest_otlp_traces

app.include_router(router)
app.post("/v1/traces")(ingest_otlp_traces)



@app.get("/")
def root():
    return {
        "system": "SentinelOps SRE Swarm",
        "status": "ONLINE",
        "docs_url": "/docs",
        "endpoints": {
            "topology": "/api/topology",
            "scenarios": "/api/scenarios",
            "inject_chaos": "/api/chaos/inject/{scenario_id}",
            "stream_agent": "/api/agent/stream",
        },
    }


@app.get("/health")
def health_check():
    return {"status": "HEALTHY"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
