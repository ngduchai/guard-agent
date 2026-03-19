# VeloC Deployment Agent

An AI agent that automatically instruments C/C++ HPC applications with [VeloC](https://veloc.readthedocs.io/) checkpoint/restart calls, making them resilient to node failures on supercomputers and cloud clusters.

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Architecture](#architecture)
   - [Component overview](#component-overview)
   - [Streaming transparency model](#streaming-transparency-model)
   - [Tool sandbox](#tool-sandbox)
   - [Event types](#event-types)
   - [File layout](#file-layout)
3. [Configuration](#configuration)
4. [Running the agent](#running-the-agent)
   - [Prerequisites](#prerequisites)
   - [Terminal (CLI) mode](#terminal-cli-mode)
   - [Web UI mode](#web-ui-mode)
   - [Piped / non-interactive mode](#piped--non-interactive-mode)
5. [Workflow the agent follows](#workflow-the-agent-follows)
6. [Tools exposed to the LLM](#tools-exposed-to-the-llm)
7. [Extending the agent](#extending-the-agent)

---

## What it does

Given a description of an existing C/C++ application and its location inside the build sandbox, the agent:

1. **Explores** the codebase with `list_directory` and `read_file`.
2. **Identifies** the critical data structures that must survive a failure.
3. **Determines** the optimal checkpoint interval (Young-Daly formula).
4. **Injects** VeloC API calls (`VELOC_Init`, `VELOC_Mem_protect`, `VELOC_Checkpoint`, `VELOC_Restart`, `VELOC_Finalize`) into the source files.
5. **Writes** the modified sources and a `veloc.cfg` configuration file.
6. **Validates** the result autonomously: writes a bash validation script, runs it with `execute_script`, inspects the output, and iterates until the test passes.
7. **Reports** a structured success/error/ask result.

The agent narrates every step of its reasoning live — you can see *why* it is doing each action, *how* it plans to do it, which tools it calls, and what the result was — without any user intervention between steps.

---

## Architecture

### Component overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User interface                           │
│                                                                 │
│   CLI (start_agent.py)          Web UI (webui.py / FastAPI)     │
│   ─ reads stdin (TTY or pipe)   ─ serves HTML + SSE endpoint    │
│   ─ prints ANSI step cards      ─ renders live step cards       │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
                 ▼                            ▼
        stream_veloc_agent()          /api/stream  (SSE)
                 │                            │
                 └──────────────┬─────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │   _stream_agent_loop  │  (agent.py)
                    │                       │
                    │  ┌─────────────────┐  │
                    │  │  OpenAI client  │  │  ← any OpenAI-compatible
                    │  │  (chat.complete)│  │    endpoint (openai / argo /
                    │  └────────┬────────┘  │    generic)
                    │           │           │
                    │  ┌────────▼────────┐  │
                    │  │  Tool dispatch  │  │
                    │  │  _dispatch_tool │  │
                    │  └────────┬────────┘  │
                    └───────────┼───────────┘
                                │
                    ┌───────────▼───────────┐
                    │   filesync_tools.py   │
                    │                       │
                    │  list_directory       │
                    │  read_file            │  ← all restricted to
                    │  write_file           │    BUILD_DIR sandbox
                    │  remove_file          │
                    │  execute_script       │
                    └───────────────────────┘
```

### Streaming transparency model

The LLM is instructed (via the system prompt) to emit two structured JSON markers in its response text before and after every logical step:

```
STEP_SUMMARY: {"step": N, "name": "...", "why": "...", "how": "...", "tools": [...]}
STEP_RESULT:  {"step": N, "result": "..."}
```

`_parse_step_events()` in `agent.py` scans the LLM's response text for these markers using regex and converts them into structured event dicts. The agent loop yields these events to callers (CLI or Web UI) so users can see the LLM's reasoning live.

**Key rule:** the LLM is instructed to proceed automatically between steps and only ask the user for input when it genuinely cannot continue without missing information (e.g. unknown code path, missing dataset).

### Tool sandbox

All file operations are restricted to `BUILD_DIR` (the directory returned by `get_project_root()`). `setup.sh` sets `GUARD_AGENT_PROJECT_ROOT` to `build/` so the agent operates in a self-contained sandbox that contains a copy of the `examples/` folder.

`execute_script` additionally:
- Sets `cwd=BUILD_DIR` and `HOME=BUILD_DIR` so relative paths and `~` stay inside the sandbox.
- Restricts `PATH` to standard system directories only.
- Runs the script in a new process group and kills the entire group on timeout.
- Truncates stdout/stderr to 8 KB each before returning them to the LLM.

### Event types

| Event type | Description |
|-----------|-------------|
| `step_summary` | LLM announced a new step: `step`, `name`, `why`, `how`, `tools` |
| `step_result` | LLM reported the outcome of a step: `step`, `result` |
| `thinking` | Raw LLM reasoning text (shown in yellow in CLI) |
| `tool_call` | Tool being invoked: `name`, `args` |
| `tool_result` | Tool output (truncated to 2 KB for display): `name`, `result` |
| `final` | LLM's final answer text (before parsing) |
| `done` | Structured result dict: `{"type": "done", "result": {...}}` |
| `error` | Unrecoverable error: `message` |

The `done` event's `result` dict has one of these shapes:

```json
{"status": "success", "summary": "..."}
{"status": "ask",     "assistant_question": "..."}
{"status": "error",   "error_message": "..."}
```

### File layout

```
agents/veloc/
├── README.md              ← this file
├── __init__.py
├── agent.py               ← core: system prompt, tool registry, streaming loop,
│                            JSON extraction, public API (stream_veloc_agent)
├── agent_graph.py         ← thin wrapper: ainvoke (batch) + astream (streaming)
├── config.py              ← Pydantic Settings: LLM provider, API keys, BUILD_DIR
├── filesync_tools.py      ← tool implementations: list_directory, read_file,
│                            write_file, remove_file, execute_script
├── llm.py                 ← (legacy) LLM client helper
├── start_agent.py         ← CLI entrypoint: reads stdin, prints ANSI step cards
├── webui.py               ← FastAPI app: /api/stream SSE endpoint + HTML frontend
├── _sdk_loader.py         ← (legacy) OpenAI Agents SDK tool loader
└── guides/
    ├── veloc_c_api.md     ← VeloC C API reference (injected into system prompt)
    ├── veloc_config.md    ← veloc.cfg format reference
    └── veloc_llm_guide.md ← VeloC usage guide for the LLM
```

---

## Configuration

All settings are read from environment variables or a `.env` file in the working directory.

### LLM provider

Set `LLM_PROVIDER` to one of:

| Value | Description | Required keys |
|-------|-------------|---------------|
| `argo` (default) | Argonne OpenAI-compatible proxy | `ARGO_API_KEY` |
| `openai` | Real OpenAI endpoint | `OPENAI_API_KEY` |
| `generic` | Any OpenAI-compatible endpoint | `LLM_API_KEY` + `LLM_BASE_URL` |

### Full environment variable reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `argo` | LLM provider: `openai`, `argo`, or `generic` |
| `LLM_MODEL` | `claudesonnet46` | Model name passed to the API |
| `OPENAI_API_KEY` | — | OpenAI API key (used by `openai` provider; fallback for others) |
| `ARGO_API_KEY` | — | Argo proxy API key |
| `ARGO_BASE_URL` | `https://apps-dev.inside.anl.gov/argoapi/v1` | Argo proxy base URL |
| `LLM_API_KEY` | — | API key for `generic` provider |
| `LLM_BASE_URL` | — | Base URL for `generic` provider |
| `GUARD_AGENT_PROJECT_ROOT` | `<repo>/build/` | Agent's file sandbox root (BUILD_DIR) |
| `ENVIRONMENT_TYPE` | `hpc` | Target environment hint passed to the LLM |

### `.env` file

Create a `.env` file in the repository root (or in `build/` when using the runner scripts):

```ini
# Argo proxy (default provider)
LLM_PROVIDER=argo
LLM_MODEL=claudesonnet46
ARGO_API_KEY=your-argo-key-here

# Or: real OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...

# Or: custom endpoint
# LLM_PROVIDER=generic
# LLM_API_KEY=your-key
# LLM_BASE_URL=https://my-gateway.example.com/v1
```

`setup.sh` copies `.env` (if present) into `build/` automatically.

---

## Running the agent

### Prerequisites

Run `setup.sh` from the repository root once to create the build environment:

```bash
cd guard-agent
./setup.sh
```

This creates:
- `build/venv/` — virtualenv with all dependencies
- `build/run_start_agent.sh` — CLI runner
- `build/run_deploy_webui.sh` — Web UI runner
- `build/examples/` — copy of `tests/examples/` for the agent to work on

Set your API key before running (or put it in `.env`):

```bash
export ARGO_API_KEY=your-key-here   # for Argo provider
# or
export OPENAI_API_KEY=sk-...        # for OpenAI provider
```

---

### Terminal (CLI) mode

The CLI mode prints each reasoning step live with ANSI colors as the LLM works.

**Interactive (TTY):**

```bash
./build/run_start_agent.sh
```

You will see a prompt. Type your request (multi-line; end with an empty line):

```
> I have an MPI matrix multiplication code in examples/matrix_mul_mpi/code.c.
> Make it resilient with VeloC checkpointing every 600 seconds.
>
```

The agent will then narrate its work step by step:

```
Agent is processing your request…
════════════════════════════════════════════════════════════════════════════════
────────────────────────────────────────────────────────────────────────────────
  Step 1: Explore codebase
  Why  : Need to understand the structure before modifying it
  How  : Call list_directory and read_file on the provided path
  Tools: ⚙ list_directory, ⚙ read_file
  ▶ tool: list_directory({"dir_path": "examples/matrix_mul_mpi"})
    ← list_directory: {"entries": [...]}
  ✓ Step 1 result: Found main loop in code.c; MPI_Allreduce is the critical call
────────────────────────────────────────────────────────────────────────────────
  Step 2: Identify critical state
  ...
```

The agent only asks you a question if it genuinely cannot proceed (e.g. it cannot find the code path you mentioned). Answer in the same terminal and press Enter twice.

Type `quit` or `exit` to stop.

**Non-interactive (piped):**

```bash
cat tests/examples/art_simple/prompt.txt | ./build/run_start_agent.sh
```

All of stdin is consumed as the first (and only) message. The agent runs to completion and exits. No stdin leaks back to the parent shell.

---

### Web UI mode

The Web UI streams step cards live in the browser using Server-Sent Events (SSE).

```bash
./build/run_deploy_webui.sh
```

Then open **http://localhost:8080** in your browser.

**What you see:**

- A chat-style interface with a prompt textarea at the bottom.
- As the agent works, **step cards** appear in real time, each showing:
  - Step number and name
  - **Why** this step is needed
  - **How** the agent plans to do it
  - **Tools** it plans to call (shown as badges)
  - Inline tool calls and their results (collapsible)
  - A **result** summary once the step completes
- The input textarea is **disabled** while the agent is working.
- It is **re-enabled** only when the agent asks a question (`status=ask`) or finishes.
- Use **Reset session** to start a new conversation.
- Use **Stop** to abort the current run.

**Keyboard shortcut:** `Ctrl+Enter` (or `Cmd+Enter` on macOS) sends the message.

**API endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the HTML frontend |
| `/api/stream` | POST | SSE stream of agent events. Body: `{"messages": [...]}` |
| `/api/chat` | POST | Legacy batch endpoint (kept for backward compatibility) |

---

### Piped / non-interactive mode

When stdin is not a TTY (e.g. piped from a file or another process), the CLI reads all of stdin at once as the first message and exits after the agent's response. This prevents leftover stdin bytes from leaking back to the parent shell as commands.

```bash
# Run with a prompt file
./build/run_start_agent.sh < tests/examples/art_simple/prompt.txt

# Or pipe from echo
echo "Make examples/matrix_mul_mpi/code.c resilient with VeloC." | ./build/run_start_agent.sh
```

---

## Workflow the agent follows

The agent is instructed to follow this 8-step workflow:

| Step | Name | Description |
|------|------|-------------|
| 1 | Understand the request | If the prompt is missing the code path, target environment, or resilience requirements, ask for the missing information. |
| 2 | Explore the codebase | Use `list_directory` and `read_file` to understand the structure. |
| 3 | Identify critical state | Determine which data structures and variables must be checkpointed. |
| 4 | Identify optimal checkpoint timing | Apply the Young-Daly formula to minimise overhead while maximising resilience. |
| 5 | Inject VeloC | Modify source files to add `VELOC_Init`, `VELOC_Mem_protect`, `VELOC_Checkpoint`, `VELOC_Restart`, `VELOC_Finalize`. Write `veloc.cfg`. |
| 6 | Write files | Use `write_file` to save all modified sources and the config. |
| 7 | Validate | Write a bash validation script with `write_file`, run it with `execute_script`, inspect `returncode`/`stdout`/`stderr`, fix and retry on failure. |
| 8 | Report | Return a structured JSON result: `success`, `ask`, or `error`. |

---

## Tools exposed to the LLM

All tools are implemented in [`filesync_tools.py`](filesync_tools.py) and restricted to `BUILD_DIR`.

| Tool | Signature | Description |
|------|-----------|-------------|
| `list_directory` | `(dir_path)` | List files and subdirectories. Returns `entries` list. |
| `read_file` | `(file_path)` | Read the full text of a file. Returns `contents`. |
| `write_file` | `(file_path, contents)` | Write text to a file, creating parent dirs. Returns `written: true`. |
| `remove_file` | `(file_path)` | Delete a single file. Directories and paths outside BUILD_DIR are rejected. Returns `removed: true`. |
| `execute_script` | `(script_path, timeout=120)` | Run a bash script inside BUILD_DIR. Returns `returncode`, `stdout`, `stderr`, `timed_out`. |

All tools return a dict. On error, the dict contains an `error` key with a human-readable message and an `allowed_root` key so the LLM can self-correct.

---

## Extending the agent

### Adding a new tool

1. Implement the tool as a plain Python function in [`filesync_tools.py`](filesync_tools.py). Use `_resolve_path()` to validate any file path argument.
2. Add it to `_TOOLS` in [`agent.py`](agent.py).
3. Add its OpenAI function-calling schema to `_build_tool_schemas()` in [`agent.py`](agent.py).
4. Add a bullet to the `## Your tools` section of `_system_prompt()` in [`agent.py`](agent.py).

### Changing the LLM provider

Set `LLM_PROVIDER` and the corresponding API key in your environment or `.env` file. No code changes are needed — `get_llm_client()` in [`config.py`](config.py) handles all three providers.

### Changing the model

Set `LLM_MODEL` in your environment or `.env` file. The value is passed directly to `chat.completions.create(model=...)`.

### Changing the system prompt

Edit `_system_prompt()` in [`agent.py`](agent.py). The prompt is rebuilt on every call so changes take effect immediately without restarting the server.
