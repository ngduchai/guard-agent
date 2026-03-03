"""
Interactive entrypoint for the deployment agent (LangGraph + MCP + VeloC).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agents.deploy.agent_graph import build_agent_graph
from agents.deploy.mcp_client import call_tool, list_tools

# Run these MCP tools automatically when a plan is ready; no user confirmation.
AUTO_EXECUTE_TOOLS = frozenset({
    "ensure_directory",
    "copy_tree",
    "list_project_files",
    "read_code_file",
    "veloc_configure_checkpoint",
})

try:
    # Prefer shared schemas when running from repo root
    from shared.schemas import (  # type: ignore
        DeploymentPlan,
        DeploymentStep,
    )
except ImportError:  # pragma: no cover - fallback for packaged usage
    from schemas import DeploymentPlan, DeploymentStep  # type: ignore


def _read_single_message() -> str:
    """
    Read a single free-form message from the user (possibly multi-line).
    """
    print(
        "\nEnter your prompt (multi-line, end with an empty line).\n"
        "Type 'quit' or 'exit' on a line by itself to stop the program.\n"
    )
    lines: list[str] = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        if line.strip() == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


GRAPH = build_agent_graph()


def _print_plan(plan: dict[str, Any]) -> None:
    summary = plan.get("summary", "")
    steps = plan.get("steps", [])
    transformed = plan.get("transformed_code")

    print("\n=== Deployment Plan Summary ===")
    print(summary or "<no summary>")

    if not steps:
        print("\n(no steps returned by model)")
        return

    print("\n=== Steps ===")
    for step in sorted(steps, key=lambda s: s.get("order", 0)):
        print(f"- [{step.get('id', '?')}] {step.get('name', '')}")
        desc = step.get("description", "")
        if desc:
            print(f"  {desc}")
        tool_used = step.get("tool_used")
        if tool_used:
            print(f"  MCP tool: {tool_used} with args: {step.get('tool_args', {})}")

    if transformed:
        print("\n=== Example Transformed Code Snippet ===")
        print(transformed)


def _apply_plan_steps(
    plan: dict[str, Any],
    skip_step_ids: frozenset[str] | None = None,
) -> None:
    tools = {t.get("name"): t for t in list_tools()}
    steps = plan.get("steps", [])
    skip = skip_step_ids or frozenset()
    if not steps:
        print("No steps to apply.")
        return

    print("\n=== Executing MCP-backed steps ===")
    for step in sorted(steps, key=lambda s: s.get("order", 0)):
        step_id = step.get("id")
        if step_id and step_id in skip:
            continue
        tool_name = step.get("tool_used")
        if not tool_name:
            continue
        args = step.get("tool_args") or {}
        print(f"* Step {step.get('id', '?')}: calling tool '{tool_name}' with args {args}")
        if tool_name not in tools:
            print(f"  ! Skipping: tool '{tool_name}' not exposed by MCP server.")
            continue
        result = call_tool(tool_name, args)
        print(f"  -> Result: {result}")


async def _handle_single_interaction() -> None:
    state: dict[str, Any] = {"messages": []}
    debug_llm = os.getenv("DEPLOY_AGENT_DEBUG_LLM", "").lower() in {"1", "true", "yes", "on"}

    while True:
        message = _read_single_message()
        if not message:
            print("Empty message, nothing to do.")
            return

        if message.strip().lower() in {"quit", "exit"}:
            print("Exiting.")
            return

        state["messages"].append({"role": "user", "content": message})

        print("\nThinking with deployment agent (this may take a while)...")
        result = await GRAPH.ainvoke(state)
        status = result.get("status", "error")

        if debug_llm:
            trace = result.get("llm_trace") or []
            if isinstance(trace, list) and trace:
                print("\n[Debug] LLM interaction trace:")
                for idx, entry in enumerate(trace, start=1):
                    if not isinstance(entry, dict):
                        continue
                    step = entry.get("step", "?")
                    prompt = entry.get("prompt", "") or ""
                    resp = entry.get("response", "") or ""
                    print(f"\n--- LLM Call {idx} (step: {step}) ---")
                    max_len = 2000
                    p_snip = prompt if len(prompt) <= max_len else prompt[:max_len] + "\n...[prompt truncated]..."
                    r_snip = resp if len(resp) <= max_len else resp[:max_len] + "\n...[response truncated]..."
                    print("\n[Prompt]:")
                    print(p_snip)
                    print("\n[Response]:")
                    print(r_snip)

        if status == "ask":
            question = result.get(
                "assistant_question",
                "Please provide more detail about your code, target environment, and resilience requirements.",
            )
            print(f"\nAgent: {question}")
            state["messages"].append({"role": "assistant", "content": question})
            continue

        if status == "plan":
            plan_dict = result.get("plan") or {}
            steps = plan_dict.get("steps") or []
            tools = {t.get("name"): t for t in list_tools()}
            executed_ids: list[str] = []
            for step in sorted(steps, key=lambda s: s.get("order", 0)):
                tool_name = step.get("tool_used")
                if not tool_name or tool_name not in AUTO_EXECUTE_TOOLS:
                    continue
                if tool_name not in tools:
                    print(f"\nAgent: Copy/setup failed — tool '{tool_name}' not exposed by MCP server.")
                    break
                args = step.get("tool_args") or {}
                try:
                    call_tool(tool_name, args)
                    executed_ids.append(step.get("id") or "")
                except Exception as e:
                    print(f"\nAgent: Copy/setup failed — {e}. Fix the issue and try again.")
                    break
            else:
                if executed_ids:
                    print("\n(Copy and discovery steps were run automatically.)")
                _print_plan(plan_dict)
                choice = input(
                    "\nApply file-edit steps from this plan now? [y/N]: "
                ).strip().lower()
                if choice == "y":
                    _apply_plan_steps(plan_dict, skip_step_ids=frozenset(executed_ids))
            break

        # Error or unexpected status: show detailed debug info so we can fix prompts / parsing.
        question = result.get(
            "assistant_question",
            "The agent encountered an error interpreting your request.",
        )
        print(f"\nAgent: {question}")
        print(f"\n[Debug] Agent status: {status}")
        print(f"[Debug] Agent state keys: {list(result.keys())}")
        if not debug_llm:
            raw = result.get("raw_llm_response")
            if isinstance(raw, str) and raw:
                max_len = 2000
                snippet = raw if len(raw) <= max_len else raw[:max_len] + "\n...[truncated]..."
                print("\n[Debug] Raw LLM response:")
                print(snippet)
        break


def main() -> None:
    print(
        "Deployment Agent (LangGraph + MCP)\n"
        "----------------------------------\n"
        "Type 'quit' or 'exit' as your prompt (on its own line) to stop.\n"
    )
    asyncio.run(_handle_single_interaction())


if __name__ == "__main__":
    main()

