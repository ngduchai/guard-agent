# Examples

Simple examples for using Guard Agent (orchestrator and resilience MCP).

Run from repo root with the build environment (after `./setup.sh`):

```bash
./build/run_list_tools.sh
./build/run_call_mcp_tool.sh
./build/run_transform_request.sh   # requires orchestrator server + API key
```

Or manually with the same venv and PYTHONPATH:

```bash
source build/venv/bin/activate
PYTHONPATH=orchestrator:. python examples/list_tools.py
```

## Examples

| Script | Description |
|--------|-------------|
| `list_tools.py` | List resilience tools from the MCP server (no API key). |
| `call_mcp_tool.py` | Call a single MCP tool (e.g. VeLoC config) and print the result. |
| `transform_request.py` | Send a transform request to the orchestrator API (orchestrator must be running; needs `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for real LLM calls). |
