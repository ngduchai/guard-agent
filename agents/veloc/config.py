"""Agent configuration from environment (shared with deployment agents)."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings loaded from env and .env."""

    # LLM: prefer OpenAI, fallback to Anthropic
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_model: str = "gpt-5.2"  # or claude-3-5-haiku
    llm_provider: str = "openai"  # openai | anthropic

    # Optional
    environment_type: str = os.getenv("ENVIRONMENT_TYPE", "hpc")

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()

