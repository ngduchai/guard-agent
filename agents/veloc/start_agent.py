"""
Interactive entrypoint for the deployment agent (OpenAI Agents SDK + VeloC).

Uses the streaming agent API so users can see each reasoning step live as the
LLM processes their prompt.  The agent narrates its own work step-by-step
(why, how, tools called, result) without requiring user intervention between
steps.  User input is only requested when the LLM explicitly asks for it.

Stdin handling
--------------
- **Interactive (TTY):** reads one message at a time; an empty line ends the
  current message.  The loop continues after each agent response so the user
  can answer follow-up questions.
- **Non-interactive (piped / redirected):** reads ALL of stdin at once as the
  first (and only) user message, then exits.  This prevents leftover stdin
  lines from leaking back to the parent shell as commands.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import textwrap
from typing import Any

from agents.veloc.agent import stream_veloc_agent


# ---------------------------------------------------------------------------
# Terminal rendering helpers
# ---------------------------------------------------------------------------

_WIDTH = 80
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_CYAN   = "\033[36m"
_GREEN  = "\033[32m"
_YELLOW = "\033[33m"
_RED    = "\033[31m"
_BLUE   = "\033[34m"
_MAGENTA= "\033[35m"


def _hr(char: str = "─", color: str = _DIM) -> None:
    print(color + char * _WIDTH + _RESET)


def _wrap(text: str, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(text, width=_WIDTH - indent, initial_indent=prefix, subsequent_indent=prefix)


def _print_step_summary(ev: dict[str, Any]) -> None:
    step = ev.get("step", "?")
    name = ev.get("name", "")
    why  = ev.get("why", "")
    how  = ev.get("how", "")
    tools = ev.get("tools", [])

    _hr("─")
    print(f"{_CYAN}{_BOLD}  Step {step}: {name}{_RESET}")
    if why:
        print(f"{_DIM}  Why  :{_RESET} {_wrap(why, 9).lstrip()}")
    if how:
        print(f"{_DIM}  How  :{_RESET} {_wrap(how, 9).lstrip()}")
    if tools:
        tool_str = ", ".join(f"⚙ {t}" for t in tools)
        print(f"{_DIM}  Tools:{_RESET} {_MAGENTA}{tool_str}{_RESET}")


def _print_step_result(ev: dict[str, Any]) -> None:
    step   = ev.get("step", "?")
    result = ev.get("result", "")
    if result:
        print(f"{_GREEN}  ✓ Step {step} result:{_RESET} {_wrap(result, 4).lstrip()}")


def _print_tool_call(ev: dict[str, Any]) -> None:
    name = ev.get("name", "?")
    args = ev.get("args", {})
    args_str = json.dumps(args, ensure_ascii=False)
    if len(args_str) > 120:
        args_str = args_str[:120] + "…"
    print(f"  {_BLUE}▶ tool:{_RESET} {_MAGENTA}{name}{_RESET}({_DIM}{args_str}{_RESET})")


def _print_tool_result(ev: dict[str, Any]) -> None:
    name   = ev.get("name", "?")
    result = ev.get("result", "")
    # Show only first 300 chars of result to keep output readable
    snippet = result if len(result) <= 300 else result[:300] + "…[truncated]"
    print(f"  {_DIM}  ← {name}: {snippet}{_RESET}")


def _print_final_success(summary: str) -> None:
    _hr("═", _GREEN)
    print(f"{_GREEN}{_BOLD}  ✓ Task completed successfully{_RESET}")
    if summary:
        for line in summary.splitlines():
            print(f"    {line}")
    _hr("═", _GREEN)


def _print_final_ask(question: str) -> None:
    _hr("─", _YELLOW)
    print(f"{_YELLOW}{_BOLD}  ⚠ Agent needs more information:{_RESET}")
    print(_wrap(question, 4))
    _hr("─", _YELLOW)


def _print_final_error(message: str) -> None:
    _hr("─", _RED)
    print(f"{_RED}{_BOLD}  ✗ Error:{_RESET}")
    print(_wrap(message, 4))
    _hr("─", _RED)


# ---------------------------------------------------------------------------
# Input helpers
# ---------------------------------------------------------------------------

_IS_TTY: bool = sys.stdin.isatty()


def _read_first_message() -> str:
    """
    Read the initial user message.

    - **TTY (interactive):** prompt line-by-line; an empty line ends input.
    - **Non-TTY (piped/redirected):** read ALL of stdin at once so that no
      leftover bytes leak back to the parent shell as commands.
    """
    if not _IS_TTY:
        # Consume all of stdin in one shot.
        return sys.stdin.read().strip()

    # Interactive mode: read until empty line.
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


def _read_followup_message(question: str) -> str:
    """
    Read a follow-up answer from the user after the agent asks a question.

    In non-TTY mode we cannot interactively prompt, so return empty string
    (the caller will exit gracefully).
    """
    if not _IS_TTY:
        return ""

    print(
        "\nAnswer the agent's question above (multi-line, end with an empty line).\n"
        "Type 'quit' or 'exit' to stop.\n"
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


# ---------------------------------------------------------------------------
# Main streaming interaction loop
# ---------------------------------------------------------------------------

async def _handle_single_interaction() -> None:
    messages: list[dict[str, Any]] = []

    # ── First message ──────────────────────────────────────────────────────
    message = _read_first_message()
    if not message:
        print("Empty message, nothing to do.")
        return

    if message.strip().lower() in {"quit", "exit"}:
        print("Exiting.")
        return

    messages.append({"role": "user", "content": message})

    while True:
        print(f"\n{_CYAN}Agent is processing your request…{_RESET}")
        _hr("═", _CYAN)

        final_result: dict[str, Any] | None = None

        async for event in stream_veloc_agent(messages):
            etype = event.get("type", "")

            if etype == "step_summary":
                _print_step_summary(event)

            elif etype == "step_result":
                _print_step_result(event)

            elif etype == "tool_call":
                _print_tool_call(event)

            elif etype == "tool_result":
                _print_tool_result(event)

            elif etype == "thinking":
                # Raw LLM text — only show if it doesn't contain step markers
                # (step markers are already rendered as step_summary/step_result)
                text = event.get("text", "")
                if "STEP_SUMMARY:" not in text and "STEP_RESULT:" not in text and text.strip():
                    snippet = text[:400] + "…" if len(text) > 400 else text
                    print(f"\n{_YELLOW}{_BOLD}💭 [thinking]{_RESET} {_YELLOW}{snippet}{_RESET}")

            elif etype == "final":
                # The raw final text — skip; done event handles rendering
                pass

            elif etype == "error":
                _print_final_error(event.get("message", "Unknown error"))
                return

            elif etype == "done":
                final_result = event.get("result") or {}

        if final_result is None:
            _print_final_error("Agent returned no result.")
            return

        status = final_result.get("status", "error")

        if status == "success":
            _print_final_success(final_result.get("summary", ""))
            return

        elif status == "ask":
            question = final_result.get(
                "assistant_question",
                "Please provide more detail about your code, target environment, and resilience requirements.",
            )
            _print_final_ask(question)
            messages.append({"role": "assistant", "content": question})

            # In non-TTY mode we cannot interactively answer — exit gracefully.
            if not _IS_TTY:
                print(f"\n{_DIM}(Non-interactive mode: cannot answer follow-up question. Exiting.){_RESET}")
                return

            answer = _read_followup_message(question)
            if not answer or answer.strip().lower() in {"quit", "exit"}:
                print("Exiting.")
                return
            messages.append({"role": "user", "content": answer})
            # Loop back to run the agent again with the answer.
            continue

        elif status == "plan":
            # Legacy plan status — print summary
            plan = final_result.get("plan") or {}
            summary = plan.get("summary", "")
            steps = plan.get("steps", [])
            _hr("═", _CYAN)
            print(f"{_CYAN}{_BOLD}  Deployment Plan{_RESET}")
            if summary:
                print(_wrap(summary, 4))
            for step in sorted(steps, key=lambda s: s.get("order", 0)):
                print(f"  - [{step.get('id', '?')}] {step.get('name', '')}")
                desc = step.get("description", "")
                if desc:
                    print(_wrap(desc, 6))
            _hr("═", _CYAN)
            return

        else:
            # error or unknown
            _print_final_error(
                final_result.get("assistant_question")
                or final_result.get("error_message")
                or f"Unexpected status: {status}"
            )
            return


def main() -> None:
    print(
        f"{_CYAN}{_BOLD}Deployment Agent (OpenAI Agents SDK + VeloC){_RESET}\n"
        f"{_DIM}{'─' * _WIDTH}{_RESET}\n"
        "The agent will narrate each step of its reasoning live.\n"
        "It will only ask you a question if it genuinely needs more information.\n"
        f"Type {_BOLD}'quit'{_RESET} or {_BOLD}'exit'{_RESET} as your prompt to stop.\n"
    )
    asyncio.run(_handle_single_interaction())


if __name__ == "__main__":
    main()
