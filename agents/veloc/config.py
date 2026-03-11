"""Agent configuration from environment (shared with deployment agents)."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _default_project_root() -> str:
    """Project root for agent file paths when GUARD_AGENT_PROJECT_ROOT is not set."""
    repo = Path(__file__).resolve().parents[2]
    return str((repo / "build").resolve())


class Settings(BaseSettings):
    """Settings loaded from env and .env."""

    # LLM: prefer OpenAI, fallback to Anthropic
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-5.2"  # or claude-3-5-haiku
    llm_provider: str = "openai"  # openai | anthropic

    # Optional
    environment_type: str = os.getenv("ENVIRONMENT_TYPE", "hpc")

    # Project root for paths (source_root, workspace_root, examples). Set via
    # GUARD_AGENT_PROJECT_ROOT in env (see get_project_root).
    project_root: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_project_root() -> str:
    """Resolved project root: env GUARD_AGENT_PROJECT_ROOT or build dir created by setup.sh."""
    raw = (os.getenv("GUARD_AGENT_PROJECT_ROOT") or (get_settings().project_root or "")).strip()
    return str(Path(raw).resolve()) if raw else _default_project_root()


def get_settings() -> Settings:
    return Settings()

