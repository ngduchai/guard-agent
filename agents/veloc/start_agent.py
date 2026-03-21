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
import re
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
_PURPLE  = "\033[95m"


def _hr(char: str = "─", color: str = _DIM) -> None:
    print(color + char * _WIDTH + _RESET)


def _wrap(text: str, indent: int = 4) -> str:
    prefix = " " * indent
    return textwrap.fill(text, width=_WIDTH - indent, initial_indent=prefix, subsequent_indent=prefix)


_ITALIC  = "\033[3m"
_UNDERLINE = "\033[4m"


def _md_to_ansi(text: str, base_color: str = _YELLOW) -> str:
    """Convert a subset of Markdown to ANSI-escaped terminal text.

    Handles: headings (#/##/###), bold (**), italic (*/_), inline code (`),
    fenced code blocks (```), unordered lists (- / *), horizontal rules (---),
    and blockquotes (>).  Everything is tinted with *base_color* so the output
    stays visually consistent with the caller's colour scheme.
    """
    lines = text.splitlines()
    out: list[str] = []
    in_code_block = False
    code_fence_re = re.compile(r"^```")

    for line in lines:
        # ── Fenced code blocks ────────────────────────────────────────────────
        if code_fence_re.match(line):
            in_code_block = not in_code_block
            if in_code_block:
                out.append(f"{_DIM}{base_color}{'─' * (_WIDTH - 4)}{_RESET}")
            else:
                out.append(f"{_DIM}{base_color}{'─' * (_WIDTH - 4)}{_RESET}")
            continue

        if in_code_block:
            out.append(f"  {_DIM}{base_color}{line}{_RESET}")
            continue

        # ── Headings ──────────────────────────────────────────────────────────
        h_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if h_match:
            level = len(h_match.group(1))
            content = h_match.group(2)
            # Apply inline formatting inside heading
            content = _inline_md(content, base_color)
            prefix = "  " * max(0, level - 1)
            out.append(f"{prefix}{_BOLD}{_UNDERLINE}{base_color}{content}{_RESET}")
            continue

        # ── Horizontal rule ───────────────────────────────────────────────────
        if re.match(r"^[-*_]{3,}\s*$", line):
            out.append(f"{_DIM}{base_color}{'─' * _WIDTH}{_RESET}")
            continue

        # ── Blockquote ────────────────────────────────────────────────────────
        bq_match = re.match(r"^>\s?(.*)", line)
        if bq_match:
            content = _inline_md(bq_match.group(1), base_color)
            out.append(f"  {_DIM}{base_color}│ {content}{_RESET}")
            continue

        # ── Unordered list items ──────────────────────────────────────────────
        li_match = re.match(r"^(\s*)[-*+]\s+(.*)", line)
        if li_match:
            indent_str = li_match.group(1)
            content = _inline_md(li_match.group(2), base_color)
            out.append(f"{indent_str}  {base_color}•{_RESET} {base_color}{content}{_RESET}")
            continue

        # ── Ordered list items ────────────────────────────────────────────────
        oli_match = re.match(r"^(\s*)(\d+)\.\s+(.*)", line)
        if oli_match:
            indent_str = oli_match.group(1)
            num = oli_match.group(2)
            content = _inline_md(oli_match.group(3), base_color)
            out.append(f"{indent_str}  {base_color}{num}.{_RESET} {base_color}{content}{_RESET}")
            continue

        # ── Normal paragraph line ─────────────────────────────────────────────
        out.append(f"{base_color}{_inline_md(line, base_color)}{_RESET}")

    return "\n".join(out)


def _inline_md(text: str, base_color: str = _YELLOW) -> str:
    """Apply inline Markdown formatting (bold, italic, code) with ANSI codes."""
    # Inline code: `code`
    text = re.sub(
        r"`([^`]+)`",
        lambda m: f"{_DIM}{base_color}{m.group(1)}{_RESET}{base_color}",
        text,
    )
    # Bold+italic: ***text***
    text = re.sub(
        r"\*\*\*(.+?)\*\*\*",
        lambda m: f"{_BOLD}{_ITALIC}{m.group(1)}{_RESET}{base_color}",
        text,
    )
    # Bold: **text** or __text__
    text = re.sub(
        r"\*\*(.+?)\*\*|__(.+?)__",
        lambda m: f"{_BOLD}{m.group(1) or m.group(2)}{_RESET}{base_color}",
        text,
    )
    # Italic: *text* or _text_
    text = re.sub(
        r"\*(.+?)\*|_(.+?)_",
        lambda m: f"{_ITALIC}{m.group(1) or m.group(2)}{_RESET}{base_color}",
        text,
    )
    return text


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


def _print_metrics_summary(metrics: dict[str, Any]) -> None:
    """Print a formatted performance summary block to the terminal."""
    if not metrics:
        return

    _hr("═", _BLUE)
    print(f"{_BLUE}{_BOLD}  📊 Performance Summary{_RESET}")
    _hr("─", _DIM)

    session_id   = metrics.get("session_id", "n/a")
    total_s      = metrics.get("total_elapsed_s")
    total_turns  = metrics.get("total_turns", 0)
    total_tools  = metrics.get("total_tool_calls", 0)
    total_tok    = metrics.get("total_tokens")
    prompt_tok   = metrics.get("total_prompt_tokens")
    compl_tok    = metrics.get("total_completion_tokens")

    print(f"  {_DIM}Session ID  :{_RESET} {session_id}")
    if total_s is not None:
        print(f"  {_DIM}Total time  :{_RESET} {total_s:.1f} s")
    print(f"  {_DIM}LLM turns   :{_RESET} {total_turns}")
    print(f"  {_DIM}Tool calls  :{_RESET} {total_tools}")
    if total_tok is not None:
        tok_str = f"{total_tok:,}"
        if prompt_tok is not None and compl_tok is not None:
            tok_str += f"  (prompt: {prompt_tok:,} | completion: {compl_tok:,})"
        print(f"  {_DIM}Tokens used :{_RESET} {tok_str}")

    per_turn = metrics.get("per_turn") or []
    if per_turn:
        _hr("─", _DIM)
        print(f"  {_DIM}Per-turn breakdown:{_RESET}")
        header = f"  {'Turn':>4}  {'Elapsed':>8}  {'Tokens':>8}  {'Tool calls':>10}  {'Steps':>5}"
        print(f"{_DIM}{header}{_RESET}")
        for t in per_turn:
            turn_n   = t.get("turn", "?")
            elapsed  = t.get("elapsed_s")
            tokens   = t.get("total_tokens")
            tools    = t.get("tool_call_count", 0)
            steps    = t.get("step_count", 0)
            elapsed_str = f"{elapsed:.1f} s" if elapsed is not None else "  n/a  "
            tokens_str  = f"{tokens:,}"      if tokens  is not None else "   n/a"
            print(
                f"  {turn_n:>4}  {elapsed_str:>8}  {tokens_str:>8}  {tools:>10}  {steps:>5}"
            )

    _hr("═", _BLUE)


# ---------------------------------------------------------------------------
# RAG / knowledge base insight box renderers
# ---------------------------------------------------------------------------

def _print_rag_query(ev: dict[str, Any]) -> None:
    """Render a knowledge-base query insight box in the shell."""
    query = ev.get("query", "")
    results = ev.get("results", [])
    count = ev.get("results_count", len(results))
    rag_enabled = ev.get("rag_enabled", True)

    _hr("─", _PURPLE)
    if not rag_enabled:
        print(f"{_PURPLE}{_BOLD}  🔍 [Knowledge Base] RAG disabled — query skipped{_RESET}")
        _hr("─", _PURPLE)
        return

    print(f"{_PURPLE}{_BOLD}  🔍 [Knowledge Base] Query{_RESET}")
    print(f"  {_DIM}Query :{_RESET} {query}")
    print(f"  {_DIM}Hits  :{_RESET} {count}")
    if results:
        for i, r in enumerate(results[:3], 1):
            title = r.get("title", "")
            score = r.get("score", 0.0)
            category = r.get("category", "")
            confidence = r.get("confidence", 0.0)
            print(f"  {_DIM}  [{i}] {title}{_RESET}  "
                  f"{_DIM}(cat={category}, score={score:.2f}, conf={confidence:.2f}){_RESET}")
            snippet = r.get("content", "")[:120]
            if snippet:
                print(f"       {_DIM}{snippet}…{_RESET}")
    _hr("─", _PURPLE)


def _print_rag_store(ev: dict[str, Any]) -> None:
    """Render a knowledge-base store insight box in the shell."""
    title = ev.get("title", "")
    category = ev.get("category", "")
    confidence = ev.get("confidence", 0.8)
    insight_id = ev.get("insight_id", "")
    rag_enabled = ev.get("rag_enabled", True)

    _hr("─", _PURPLE)
    if not rag_enabled:
        print(f"{_PURPLE}{_BOLD}  💾 [Knowledge Base] RAG disabled — store skipped{_RESET}")
        _hr("─", _PURPLE)
        return

    print(f"{_PURPLE}{_BOLD}  💾 [Knowledge Base] Insight Stored{_RESET}")
    print(f"  {_DIM}Title     :{_RESET} {title}")
    print(f"  {_DIM}Category  :{_RESET} {category}")
    print(f"  {_DIM}Confidence:{_RESET} {confidence:.2f}")
    if insight_id:
        print(f"  {_DIM}ID        :{_RESET} {insight_id[:16]}…")
    _hr("─", _PURPLE)


def _print_rag_update(ev: dict[str, Any]) -> None:
    """Render a knowledge-base update insight box in the shell."""
    title = ev.get("title", "")
    insight_id = ev.get("insight_id", "")
    confidence = ev.get("confidence")
    rag_enabled = ev.get("rag_enabled", True)

    _hr("─", _PURPLE)
    if not rag_enabled:
        print(f"{_PURPLE}{_BOLD}  ✏️  [Knowledge Base] RAG disabled — update skipped{_RESET}")
        _hr("─", _PURPLE)
        return

    print(f"{_PURPLE}{_BOLD}  ✏️  [Knowledge Base] Insight Updated{_RESET}")
    if title:
        print(f"  {_DIM}Title     :{_RESET} {title}")
    if insight_id:
        print(f"  {_DIM}ID        :{_RESET} {insight_id[:16]}…")
    if confidence is not None:
        print(f"  {_DIM}Confidence:{_RESET} {confidence:.2f}")
    _hr("─", _PURPLE)


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

        # Collect all events so we can reorder tool_call / tool_result events
        # to appear immediately after the step_summary that announced them.
        # The OpenAI API always returns tool calls after all text content, so
        # without buffering the shell would show:
        #   step_summary(1) → step_result(1) → step_summary(2) → step_result(2)
        #   → tool_call(1) → tool_result(1) → tool_call(2) → tool_result(2)
        # With buffering we reorder to:
        #   step_summary(1) → tool_call(1) → tool_result(1) → step_result(1)
        #   → step_summary(2) → tool_call(2) → tool_result(2) → step_result(2)
        _turn_events: list[dict[str, Any]] = []
        _done_event: dict[str, Any] | None = None
        _error_event: dict[str, Any] | None = None

        async for event in stream_veloc_agent(messages):
            etype = event.get("type", "")
            if etype == "done":
                final_result = event.get("result") or {}
                # Capture metrics from the done event (top-level key).
                _done_metrics = event.get("metrics") or (final_result or {}).get("metrics")
                if _done_metrics and not (final_result or {}).get("metrics"):
                    final_result["metrics"] = _done_metrics
                if _done_metrics and not (final_result or {}).get("metrics_path"):
                    final_result["metrics_path"] = event.get("result", {}).get("metrics_path")
                _done_event = event
            elif etype == "error":
                _error_event = event
            else:
                _turn_events.append(event)

        # ── Reorder events to reflect the correct reasoning flow ─────────────
        # The OpenAI API always returns tool calls after all text content, so
        # the raw stream order is:
        #   thinking → step_summary(1) → thinking → step_result(1) → …
        #   → tool_call(1) → tool_result(1) → tool_call(2) → tool_result(2)
        #
        # We reorder to the desired reasoning flow:
        #   thinking → step_summary(1) → thinking → tool_call(1) → tool_result(1)
        #   → step_result(1) → thinking → step_summary(2) → …
        #
        # Strategy: inject each step's tool_call/tool_result events immediately
        # BEFORE the step_result event for that step (preserving any thinking
        # blocks that appear between step_summary and step_result).

        # Build a map: step_num → [tool_call, tool_result, ...] events
        _step_tool_events: dict[int, list[dict[str, Any]]] = {}
        _unstepped_tool_events: list[dict[str, Any]] = []
        for ev in _turn_events:
            if ev.get("type") in ("tool_call", "tool_result"):
                s = ev.get("step")
                if s is not None:
                    _step_tool_events.setdefault(s, []).append(ev)
                else:
                    _unstepped_tool_events.append(ev)

        # Build the reordered event list:
        # Inject tool_call/tool_result events immediately before the step_result
        # for the same step number.
        _reordered: list[dict[str, Any]] = []
        _injected_steps: set[int] = set()
        for ev in _turn_events:
            etype = ev.get("type", "")
            if etype in ("tool_call", "tool_result") and ev.get("step") is not None:
                # Will be injected before the matching step_result — skip here.
                continue
            if etype == "step_result":
                s = ev.get("step")
                if s is not None and s not in _injected_steps:
                    _injected_steps.add(s)
                    _reordered.extend(_step_tool_events.get(s, []))
            _reordered.append(ev)
        # Append any tool events that had no step association.
        _reordered.extend(_unstepped_tool_events)

        # ── Print the reordered events ────────────────────────────────────────
        for event in _reordered:
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
                # The agent now emits thinking chunks with STEP_SUMMARY /
                # STEP_RESULT markers already stripped and interleaved with
                # step_summary / step_result events in the correct order.
                # A thinking event may arrive before OR after a step_summary,
                # reflecting the LLM's actual reasoning flow.
                text = event.get("text", "").strip()
                if text:
                    print(f"\n{_YELLOW}{_BOLD}💭 [thinking]{_RESET}")
                    print(_md_to_ansi(text, base_color=_YELLOW))

            elif etype == "final":
                # The raw final text — skip; done event handles rendering
                pass

            elif etype == "rag_query":
                _print_rag_query(event)

            elif etype == "rag_store":
                _print_rag_store(event)

            elif etype == "rag_update":
                _print_rag_update(event)

        if _error_event is not None:
            _print_final_error(_error_event.get("message", "Unknown error"))
            return

        if final_result is None:
            _print_final_error("Agent returned no result.")
            return

        # ── Print performance metrics ─────────────────────────────────────────
        metrics = final_result.get("metrics")
        if metrics:
            _print_metrics_summary(metrics)
            saved_path = final_result.get("metrics_path")
            if saved_path:
                print(f"  {_DIM}📁 Metrics saved to:{_RESET} {saved_path}")
                _hr("═", _BLUE)

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
