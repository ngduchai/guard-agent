# Guard Agent

An AI agentic system that helps developers transform code **without** resilient protection into **resilient-enabled deployments** for supercomputers (HPC) or cloud. The system follows a two-component architecture.

**Quick start:** `./setup.sh` then `./build/run_list_tools.sh` (see [Installation](#installation) and [Examples](#examples)).

1. **Orchestrator** – Accepts user code, description, and resilience/QoS requirements; instructs LLMs (e.g., GPT, Claude) to produce a deployment plan and optionally transformed code.
2. **Resilience MCP Server** – A Model Context Protocol (MCP) server where resilience solutions (e.g., VeLoC checkpoint library, load balancers, scalers) register as **tools**. The LLM uses these tools to integrate resiliency into the deployment.

## Architecture (high level)

- **User input**: Workflow/code description + resilience/QoS constraints.
- **Orchestrator**: Receives the prompt, discovers tools from the MCP server, calls the LLM to reason and plan, and returns a deployment/execution plan. It can consume monitoring feedback from the target environment.
- **LLMs**: Used for reasoning and planning (e.g., which resilience tools to apply and how).
- **Agent(s)**: Driven by the orchestrator and LLM; produce the deployment plan and interact with the MCP (tool discovery and invocation).
- **MCP**: Registry of resilience tools; tools register here; agents use it to discover and call tools.
- **Resilience tools**: e.g., VeLoC (checkpointing), load balance, scaler; they register with the MCP and are used in the generated deployment.

## Repository layout

The project is **all-Python**.

```
guard-agent/
├── orchestrator/          # Orchestrator service (Python)
├── resilience_mcp/        # MCP server for resilience tools (Python)
├── shared/                # Shared schemas (e.g., deployment plan, requirements)
├── examples/              # Example scripts (list tools, call tool, transform request)
├── build/                 # Created by setup.sh: venv + run_*.sh scripts
├── setup.sh               # Create build env and runner scripts
└── README.md
```

## Installation

**Requirements:** Python 3.10+.

### Recommended: build environment (for running everything and examples)

From the repository root, run the setup script. It creates a `build/` directory with a virtualenv and installs all dependencies (orchestrator, resilience MCP, shared). Runner scripts are created so you can start the API or run examples without setting `PYTHONPATH` manually.

```bash
cd guard-agent
./setup.sh
```

This creates:

- `build/venv/` – virtualenv with dependencies installed
- `build/run_list_tools.sh` – list MCP tools
- `build/run_call_mcp_tool.sh` – call a resilience tool
- `build/run_transform_request.sh` – send a transform request to the API
- `build/run_orchestrator.sh` – start the orchestrator server

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

The orchestrator spawns the resilience MCP server automatically; ensure the repo root is on `PYTHONPATH` when using the default `python3 -m resilience_mcp` so that the `resilience_mcp` package can be found.

---

## Examples

After running `./setup.sh`, use the scripts in `build/` to run the examples. All commands below are from the **repository root**.

| Example | Command | Description |
|--------|---------|-------------|
| List MCP tools | `./build/run_list_tools.sh` | List resilience tools from the MCP server. No API key or server required. |
| Call a tool | `./build/run_call_mcp_tool.sh` | Call `veloc_configure_checkpoint` with sample args and print the result. No API key required. |
| Transform request | `./build/run_transform_request.sh` | Send a sample transform request to the orchestrator API. **Requires the orchestrator to be running** (see below). For real LLM plans, set `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in the environment used to start the orchestrator. |
| Start orchestrator | `./build/run_orchestrator.sh` | Start the orchestrator API on port 8000 (for use with the transform request example). |

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
python examples/list_tools.py
python examples/call_mcp_tool.py
python examples/transform_request.py    # optional: pass base URL as first argument
```

More detail: `examples/README.md`.

---

## Adding a new resilience tool

Add a new `@mcp.tool()` function in `resilience_mcp/server.py` (or a module it imports). The orchestrator discovers it automatically via MCP `tools/list`.

---

## Environment variables

| Context | Variable | Description |
|--------|----------|-------------|
| Orchestrator | `OPENAI_API_KEY` | OpenAI API key (for `LLM_PROVIDER=openai`). |
| Orchestrator | `ANTHROPIC_API_KEY` | Anthropic API key (for `LLM_PROVIDER=anthropic`). |
| Orchestrator | `LLM_PROVIDER` | `openai` (default) or `anthropic`. |
| Orchestrator | `LLM_MODEL` | Model name (e.g. `gpt-4o-mini`, `claude-3-5-haiku`). |
| Orchestrator | `MCP_SERVER_COMMAND` | Command to run the MCP server (default `python3`). |
| Orchestrator | `MCP_SERVER_ARGS` | Arguments (default `-m resilience_mcp`). |
| Orchestrator | `ENVIRONMENT_TYPE` | Optional; e.g. `hpc`, `cloud`. |
| Resilience MCP | — | None required when run by the orchestrator. |
