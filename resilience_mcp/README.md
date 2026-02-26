# Resilience MCP Server (Python)

MCP server that exposes resilience tools (VeLoC, load balance, scaler) so LLM-driven agents can discover and use them when generating deployment plans. This is the **default** MCP server for the Guard Agent project (all-Python stack).

## Run

The orchestrator spawns this server automatically over stdio. To run standalone (e.g. for testing):

```bash
# From repo root
pip install mcp
python -m resilience_mcp
```

## Tools

| Tool | Description |
|------|-------------|
| `veloc_configure_checkpoint` | Configure VeLoC checkpointing (interval, dir, compression). |
| `load_balance_configure` | Configure load balancing (strategy, health check path). |
| `scaler_configure` | Configure auto-scaling (min/max replicas, metric). |

## Adding a tool

Add a new `@mcp.tool()` function in `server.py` with a docstring and type hints; FastMCP will expose it via MCP automatically.
