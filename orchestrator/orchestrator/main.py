"""
Orchestrator API: accepts user code + description + resilience requirements,
instructs the LLM (with tool context from the resilience MCP), returns a deployment plan.
"""

import sys
from pathlib import Path

# Repo root (guard-agent/) so that "shared" can be imported
_repo_root = Path(__file__).resolve().parents[2]
if _repo_root.exists():
    sys.path.insert(0, str(_repo_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from orchestrator.llm import get_deployment_plan_from_llm
from orchestrator.mcp_client import list_tools

# Import shared schemas (run from repo root: PYTHONPATH=. uvicorn orchestrator.main:app)
try:
    from shared.schemas import (  # type: ignore
        DeploymentPlan,
        DeploymentStep,
        EnvironmentType,
        TransformRequest,
    )
except ImportError:
    from schemas import (
        DeploymentPlan,
        DeploymentStep,
        EnvironmentType,
        TransformRequest,
    )

app = FastAPI(
    title="Guard Agent Orchestrator",
    description="Transform code into resilient-enabled deployment plans using LLM and MCP resilience tools",
    version="0.1.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/tools")
def tools_list():
    """List resilience tools available from the MCP server (for debugging)."""
    tools = list_tools()
    return {"tools": tools}


@app.post("/v1/transform", response_model=DeploymentPlan)
async def transform(req: TransformRequest):
    """
    Transform user code and requirements into a resilient deployment plan.
    The orchestrator instructs the LLM with context from the resilience MCP tools.
    """
    reqs = [r.model_dump() for r in req.resilience_requirements]
    out = await get_deployment_plan_from_llm(
        code=req.code,
        description=req.description,
        resilience_requirements=reqs,
        environment=req.environment.value,
    )
    if "error" in out and out.get("error"):
        raise HTTPException(status_code=502, detail=out["error"])
    steps = [
        DeploymentStep(
            id=s.get("id", f"step{i}"),
            name=s.get("name", ""),
            description=s.get("description", ""),
            tool_used=s.get("tool_used"),
            tool_args=s.get("tool_args") or {},
            order=s.get("order", i),
        )
        for i, s in enumerate(out.get("steps", []))
    ]
    return DeploymentPlan(
        summary=out.get("summary", ""),
        steps=steps,
        transformed_code=out.get("transformed_code"),
        environment=req.environment,
        raw_llm_response=out.get("raw_llm_response"),
    )
