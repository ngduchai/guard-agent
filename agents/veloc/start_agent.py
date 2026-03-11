"""
Interactive entrypoint for the deployment agent (OpenAI Agents SDK + VeloC).
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from agents.veloc.agent_graph import build_agent_graph

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

    if not steps and not transformed:
        print("\n(no detailed steps returned by model)")
        return

    if steps:
        print("\n=== Steps (logical plan) ===")
        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            print(f"- [{step.get('id', '?')}] {step.get('name', '')}")
            desc = step.get("description", "")
            if desc:
                print(f"  {desc}")

    if transformed:
        print("\n=== Example Transformed Code Snippet ===")
        print(transformed)


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
            _print_plan(plan_dict)
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
        "Deployment Agent (OpenAI Agents SDK)\n"
        "------------------------------------\n"
        "Type 'quit' or 'exit' as your prompt (on its own line) to stop.\n"
    )
    asyncio.run(_handle_single_interaction())


if __name__ == "__main__":
    main()

