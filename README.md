# Guard Agent

An AI agentic system that helps developers transform code **without** resilient protection into **resilient-enabled deployments** for supercomputers (HPC) or cloud. The system follows a two-component architecture.

**Quick start:** `./setup.sh` then run the orchestrator or deployment agent (see [Installation](#installation) and [Examples](#examples)).

1. **Orchestrator** – Accepts user code, description, and resilience/QoS requirements; uses the LLM with **OpenAI Agents SDK** and SDK-hosted tools only to produce a deployment plan.
2. **Tools** – Only [SDK-hosted tools](https://openai.github.io/openai-agents-python/tools/#hosted-tools) (WebSearchTool, CodeInterpreterTool, optionally FileSearchTool). No custom tools are implemented.

## Architecture (high level)

- **User input**: Workflow/code description + resilience/QoS constraints.
- **Orchestrator**: Receives the prompt, calls the LLM with SDK-hosted tools (web search, code interpreter, etc.), and returns a deployment/execution plan.
- **LLMs**: Used for reasoning and planning; they use only SDK-hosted tools (WebSearchTool, CodeInterpreterTool, etc.) via the OpenAI API.
- **Agent(s)**: Deployment agent (OpenAI Agents SDK) and orchestrator use the same SDK tools list passed to `Agent(tools=...)`.

## Repository layout

The project is **all-Python**.

```
guard-agent/
├── orchestrator/          # Orchestrator service (Python)
├── agents/veloc/          # VeloC code-injection agent (OpenAI Agents SDK)
├── shared/                # Shared schemas and resilience tools (OpenAI tool specs)
├── examples/              # Example code and transform request
├── build/                 # Created by setup.sh: venv + run_*.sh scripts
├── setup.sh               # Create build env and runner scripts
└── README.md
```

## Installation

**Requirements:** Python 3.10+.

### Recommended: build environment (for running everything and examples)

From the repository root, run the setup script. It creates a `build/` directory with a virtualenv and installs all dependencies (orchestrator, shared, agents). Runner scripts are created so you can start the API or run examples without setting `PYTHONPATH` manually.

```bash
cd guard-agent
./setup.sh
```

This creates:

- `build/venv/` – virtualenv with dependencies installed
- `build/run_transform_request.sh` – send a transform request to the API
- `build/run_orchestrator.sh` – start the orchestrator server
- `build/run_start_agent.sh` – interactive deployment agent
- `build/run_deploy_webui.sh` – deployment agent Web UI

The `build/` directory is gitignored; re-run `./setup.sh` after pulling changes if dependencies change.

### Optional: manual install (orchestrator only)

If you only want to run the orchestrator API (e.g. in your own venv):

```bash
cd guard-agent/orchestrator
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env: set OPENAI_API_KEY or ANTHROPIC_API_KEY
cd ..
PYTHONPATH=orchestrator:. python -m uvicorn orchestrator.main:app --reload
```

Ensure the repo root is on `PYTHONPATH` when running the orchestrator so that `shared` and `orchestrator` can be imported.

---

## Examples

After running `./setup.sh`, use the scripts in `build/` to run the examples. All commands below are from the **repository root**.

| Example | Command | Description |
|--------|---------|-------------|
| Transform request | `./build/run_transform_request.sh` | Send a sample transform request to the orchestrator API. **Requires the orchestrator to be running** (see below). Set `OPENAI_API_KEY` in the environment used to start the orchestrator for LLM plans. |
| Start orchestrator | `./build/run_orchestrator.sh` | Start the orchestrator API on port 8000 (for use with the transform request example). |
| List tools (API) | `curl http://127.0.0.1:8000/v1/tools` | List resilience tools exposed by the orchestrator (with orchestrator running). |

**Run the transform example (two terminals):**

```bash
# Terminal 1: start the orchestrator
./build/run_orchestrator.sh

# Terminal 2: send a transform request (default base URL http://127.0.0.1:8000)
./build/run_transform_request.sh

# Optional: use a different base URL
./build/run_transform_request.sh http://localhost:8000
```

**Run examples without the build scripts** (same venv and `PYTHONPATH` as the runners use):

```bash
source build/venv/bin/activate
export PYTHONPATH="$(pwd)/orchestrator:$(pwd)"
python examples/transform_request.py    # optional: pass base URL as first argument
```

More detail: `examples/README.md`.

---

## Tools

The deploy agent and orchestrator use **only SDK-hosted tools** from the [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/tools/#hosted-tools): `WebSearchTool`, `CodeInterpreterTool`, and optionally `FileSearchTool` (if `OPENAI_VECTOR_STORE_IDS` is set). No custom function tools are implemented; tools are passed to `Agent(tools=get_sdk_tools_list())` from `agents.veloc._sdk_loader`.

---

## Environment variables

| Context | Variable | Description |
|--------|----------|-------------|
| Orchestrator | `OPENAI_API_KEY` | OpenAI API key for the orchestrator LLM. |
| Orchestrator | `ORCHESTRATOR_LLM_MODEL` | Model name (e.g. `gpt-4o`, default `gpt-4o`). |
| Orchestrator | `ENVIRONMENT_TYPE` | Optional; e.g. `hpc`, `cloud`. |
| Deployment agent | `OPENAI_API_KEY` | OpenAI API key (used by build scripts from `build/api_key`). |
| Optional | `OPENAI_VECTOR_STORE_IDS` | Comma-separated vector store IDs to enable FileSearchTool for the agent/orchestrator. |
