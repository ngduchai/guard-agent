"""Orchestrator configuration from environment."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from env and .env."""

    # LLM: prefer OpenAI, fallback to Anthropic
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-4o-mini"  # or claude-3-5-haiku
    llm_provider: str = "openai"  # openai | anthropic

    # MCP: command to run resilience MCP server (stdio)
    mcp_server_command: str | None = os.getenv(
        "MCP_SERVER_COMMAND",
        "python3",
    )
    mcp_server_args: str = os.getenv(
        "MCP_SERVER_ARGS",
        "-m resilience_mcp",
    )

    # Optional
    environment_type: str = os.getenv("ENVIRONMENT_TYPE", "hpc")

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
