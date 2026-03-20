"""Agent configuration loaded from environment / .env file."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _default_project_root() -> str:
    """Fallback project root: the repo's build/ directory (created by setup.sh).

    This is used when ``GUARD_AGENT_PROJECT_ROOT`` is not set in the environment.
    The build/ directory is the agent's self-contained sandbox — it contains a
    copy of the examples/ folder and the venv, and is the only directory the
    agent is permitted to read from or write to.
    """
    repo = Path(__file__).resolve().parents[2]
    return str((repo / "build").resolve())


class Settings(BaseSettings):
    """
    All settings are read from environment variables or a .env file.

    LLM provider selection (LLM_PROVIDER):
      - ``openai``  – real OpenAI endpoint; set OPENAI_API_KEY.
      - ``argo``    – Argonne OpenAI-compatible proxy; set ARGO_API_KEY and
                      optionally ARGO_BASE_URL (default: apps-dev.inside.anl.gov/argoapi/v1).
      - ``generic`` – any OpenAI-compatible endpoint; set LLM_API_KEY + LLM_BASE_URL.

    All three providers use the same ``openai`` Python client under the hood;
    only the ``api_key`` and ``base_url`` differ.
    """

    # Provider selection
    llm_provider: str = "argo"   # openai | argo | generic
    llm_model: str = "claudesonnet46"

    # OpenAI
    openai_api_key: str | None = None

    # Argo (OpenAI-compatible proxy at Argonne)
    argo_api_key: str | None = None
    argo_base_url: str = "https://apps-dev.inside.anl.gov/argoapi/v1"

    # Generic OpenAI-compatible endpoint
    llm_api_key: str | None = None   # API key for the custom endpoint
    llm_base_url: str | None = None  # Base URL, e.g. "https://my-gateway.example.com/v1"

    # Misc
    environment_type: str = "hpc"
    project_root: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()


def get_project_root() -> str:
    """Return the agent's allowed root directory (BUILD_DIR).

    This is the single directory the agent is permitted to read from and write
    to.  ``setup.sh`` sets ``GUARD_AGENT_PROJECT_ROOT`` to the ``build/``
    directory so that the agent operates in a self-contained sandbox that
    contains a copy of the ``examples/`` folder.

    Resolution order:
    1. ``GUARD_AGENT_PROJECT_ROOT`` environment variable (set by ``setup.sh``
       runner scripts to the ``build/`` directory).
    2. ``project_root`` field in the ``.env`` / ``Settings`` object.
    3. Fallback: ``<repo_root>/build/`` (computed from this file's location).
    """
    raw = (os.getenv("GUARD_AGENT_PROJECT_ROOT") or get_settings().project_root or "").strip()
    return str(Path(raw).resolve()) if raw else _default_project_root()


# Default HTTP timeout (seconds) for LLM API calls.  Long enough for slow
# models / large contexts, but prevents an indefinite hang if the endpoint
# is unreachable or stalled.  Can be overridden by setting LLM_TIMEOUT in
# the environment.
_LLM_HTTP_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "300"))


def get_llm_client():
    """
    Return a configured ``openai.OpenAI`` client for the active provider.

    All providers use the same OpenAI Python client; only ``api_key`` and
    ``base_url`` differ:

    - ``openai``  → real OpenAI endpoint (no base_url override).
    - ``argo``    → Argonne proxy (base_url = ARGO_BASE_URL).
    - ``generic`` → custom endpoint (base_url = LLM_BASE_URL, key = LLM_API_KEY).

    A ``timeout`` of ``_LLM_HTTP_TIMEOUT`` seconds is applied at the HTTP
    level so that a slow or unreachable endpoint does not block indefinitely.
    """
    from openai import OpenAI

    s = get_settings()
    provider = s.llm_provider.strip().lower()

    if provider == "openai":
        api_key = s.openai_api_key or os.getenv("OPENAI_API_KEY")
        return OpenAI(api_key=api_key, timeout=_LLM_HTTP_TIMEOUT)

    if provider == "argo":
        api_key = (
            s.argo_api_key
            or s.openai_api_key
            or os.getenv("OPENAI_API_KEY")
        )
        return OpenAI(api_key=api_key, base_url=s.argo_base_url, timeout=_LLM_HTTP_TIMEOUT)

    if provider == "generic":
        api_key = (
            s.llm_api_key
            or s.openai_api_key
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            import warnings
            warnings.warn(
                "No API key configured for the 'generic' LLM provider. "
                "Set LLM_API_KEY (or OPENAI_API_KEY) in your environment. "
                "Falling back to 'placeholder' — requests will likely fail.",
                stacklevel=2,
            )
            api_key = "placeholder"
        base_url = s.llm_base_url or os.getenv("OPENAI_BASE_URL")
        return OpenAI(api_key=api_key, base_url=base_url, timeout=_LLM_HTTP_TIMEOUT)

    raise ValueError(
        f"Unknown llm_provider '{provider}'. "
        "Supported values: openai, argo, generic."
    )


def apply_llm_environment() -> None:
    """
    Set ``OPENAI_API_KEY`` / ``OPENAI_BASE_URL`` env vars for the active provider.

    This is kept for backward compatibility with the orchestrator which uses the
    OpenAI Agents SDK (Agent + Runner) and reads these env vars at startup.
    New code should use ``get_llm_client()`` instead.
    """
    s = get_settings()
    provider = s.llm_provider.strip().lower()

    if provider == "argo":
        api_key = s.argo_api_key or s.openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)
        if s.argo_base_url:
            os.environ.setdefault("OPENAI_BASE_URL", s.argo_base_url)
            os.environ.setdefault("OPENAI_API_BASE", s.argo_base_url)

    elif provider == "openai":
        api_key = s.openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)

    elif provider == "generic":
        api_key = s.llm_api_key or s.openai_api_key or os.getenv("OPENAI_API_KEY")
        if api_key:
            os.environ.setdefault("OPENAI_API_KEY", api_key)
        if s.llm_base_url:
            os.environ.setdefault("OPENAI_BASE_URL", s.llm_base_url)
            os.environ.setdefault("OPENAI_API_BASE", s.llm_base_url)
