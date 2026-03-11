"""
Shared schemas for deployment plans, resilience requirements, and tool metadata.
Used by the orchestrator and deployment agent.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EnvironmentType(str, Enum):
    HPC = "hpc"
    CLOUD = "cloud"


class ResilienceRequirement(BaseModel):
    """User-defined resilience or QoS constraint."""

    name: str = Field(..., description="e.g. checkpoint_interval, max_failures")
    value: str | int | float | bool = Field(..., description="Constraint value or expression")
    unit: str | None = Field(None, description="Optional unit (e.g. seconds, count)")


class TransformRequest(BaseModel):
    """Request body for the transform endpoint."""

    code: str = Field(..., description="User-provided code or path reference")
    description: str = Field(..., description="Description of the workflow/application")
    resilience_requirements: list[ResilienceRequirement] = Field(
        default_factory=list,
        description="Resilience and QoS requirements",
    )
    environment: EnvironmentType = Field(
        default=EnvironmentType.HPC,
        description="Target environment (HPC or cloud)",
    )
    language: str | None = Field(None, description="Programming language of the code")


class DeploymentStep(BaseModel):
    """A single step in the deployment/execution plan."""

    id: str
    name: str
    description: str
    tool_used: str | None = Field(None, description="Tool name if this step uses one")
    tool_args: dict[str, Any] = Field(default_factory=dict)
    order: int = 0


class DeploymentPlan(BaseModel):
    """Generated deployment/execution plan with resiliency integrated."""

    plan_id: str | None = None
    summary: str = Field(..., description="Short summary of the plan")
    steps: list[DeploymentStep] = Field(default_factory=list)
    transformed_code: str | None = Field(None, description="Optional transformed code snippet")
    environment: EnvironmentType = EnvironmentType.HPC
    raw_llm_response: str | None = Field(None, description="Optional raw model output for debugging")
