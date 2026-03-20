"""
LLM performance metrics collection and export for the VeloC agent.

Provides:
  - Dataclasses for structured metric storage (ToolCallMetrics, StepMetrics,
    TurnMetrics, SessionMetrics).
  - MetricsCollector – a stateful collector used inside _stream_agent_loop to
    record per-turn latency, token counts, tool call timing, step timing, and
    the full per-turn conversation (user context, model response, tool calls /
    results).
  - log_session()    – always saves a full session log to
                       ``<BUILD_DIR>/log/<codebase>_<YYYYMMDD>.json``.
  - export_metrics() – serialises a SessionMetrics object to a JSON file on
                       disk (kept for backward-compat / download endpoint).
  - metrics_summary() – returns a compact dict suitable for embedding in the
                        "done" SSE event so the web UI and terminal can display
                        a quick summary.

No external dependencies – uses only the Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ToolCallMetrics:
    """Timing record for a single tool call."""
    name: str
    elapsed_s: float
    args: Optional[Dict[str, Any]] = None   # parsed arguments (best-effort)
    result_snippet: Optional[str] = None    # first 500 chars of result


@dataclass
class StepMetrics:
    """Timing record for a single agent step (STEP_SUMMARY → STEP_RESULT)."""
    step: int
    name: str
    started_at: str          # ISO-8601 UTC
    elapsed_s: Optional[float] = None   # None until STEP_RESULT arrives


@dataclass
class ConversationEvent:
    """
    A single event in the per-turn conversation record.

    ``kind`` is one of:
      - ``"context_user"``    – a user message that was in the LLM context for
                                this turn (may be from a previous turn).
      - ``"context_assistant"`` – an assistant message in context (prior turn).
      - ``"model_response"``  – the model's text output for this turn.
      - ``"tool_call"``       – a tool invocation (name + args).
      - ``"tool_result"``     – the result returned by a tool.
    """
    kind: str
    content: str
    name: Optional[str] = None   # tool name (for tool_call / tool_result)
    args: Optional[Dict[str, Any]] = None  # tool args (for tool_call)


@dataclass
class TurnMetrics:
    """Metrics for one LLM API call (one turn of the tool-calling loop)."""
    turn: int
    started_at: str          # ISO-8601 UTC
    elapsed_s: float
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    tool_calls: List[ToolCallMetrics] = field(default_factory=list)
    steps: List[StepMetrics] = field(default_factory=list)
    # Per-turn conversation record: context messages + model response + tool
    # calls/results that occurred during this turn.
    conversation_events: List[ConversationEvent] = field(default_factory=list)


@dataclass
class SessionMetrics:
    """Full performance record for one agent session."""
    session_id: str
    codebase: str            # extracted from user prompt (e.g. "art_simple")
    started_at: str          # ISO-8601 UTC
    finished_at: Optional[str] = None
    total_elapsed_s: Optional[float] = None
    llm_model: Optional[str] = None   # LLM model name used for this session
    summary: Dict[str, Any] = field(default_factory=dict)
    turns: List[TurnMetrics] = field(default_factory=list)
    # Full conversation history (role + content for every message).
    conversation: List[Dict[str, Any]] = field(default_factory=list)
    # Final result dict from _build_result (status, summary, error_message, etc.)
    final_result: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MetricsCollector:
    """
    Stateful collector used inside ``_stream_agent_loop``.

    Lifecycle::

        collector = MetricsCollector()
        collector.start_session()

        for turn in range(...):
            collector.start_turn(turn)
            # ... LLM call ...
            collector.end_turn(turn, response.usage)

            # Record model response text:
            collector.record_model_response(turn, text)

            # for each tool call:
            t0 = time.monotonic()
            # ... dispatch tool ...
            collector.record_tool_call(name, time.monotonic() - t0,
                                       args=args_dict, result=result_str)

            # from _parse_step_events results:
            collector.record_step_start(step_num, step_name)
            # ... later ...
            collector.record_step_end(step_num)

        metrics = collector.finish_session(chat_messages, final_result,
                                           codebase="art_simple")
    """

    def __init__(self) -> None:
        self._session_id: str = str(uuid.uuid4())
        self._session_start: float = 0.0
        self._session_started_at: str = ""
        self._turn_start: float = 0.0
        self._turn_started_at: str = ""
        self._current_turn: int = 0
        # turn_num → TurnMetrics (in-progress)
        self._turns: Dict[int, TurnMetrics] = {}
        # step_num → (start_monotonic, StepMetrics)
        self._open_steps: Dict[int, tuple[float, StepMetrics]] = {}

    # ── Session ──────────────────────────────────────────────────────────────

    def start_session(self) -> None:
        """Record session start time and generate a session ID."""
        self._session_start = time.monotonic()
        self._session_started_at = _utcnow()

    @property
    def session_id(self) -> str:
        return self._session_id

    # ── Turns ─────────────────────────────────────────────────────────────────

    def start_turn(self, turn: int) -> None:
        """Record the start of an LLM API call."""
        self._current_turn = turn
        self._turn_start = time.monotonic()
        self._turn_started_at = _utcnow()

    def end_turn(self, turn: int, usage: Any) -> None:
        """
        Record the end of an LLM API call.

        ``usage`` is the ``CompletionUsage`` object from the OpenAI response
        (may be ``None`` if the provider does not return token counts).
        """
        elapsed = time.monotonic() - self._turn_start
        prompt_tokens: Optional[int] = None
        completion_tokens: Optional[int] = None
        total_tokens: Optional[int] = None
        if usage is not None:
            try:
                prompt_tokens = int(usage.prompt_tokens)
                completion_tokens = int(usage.completion_tokens)
                total_tokens = int(usage.total_tokens)
            except (AttributeError, TypeError, ValueError):
                pass

        tm = TurnMetrics(
            turn=turn,
            started_at=self._turn_started_at,
            elapsed_s=round(elapsed, 3),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
        self._turns[turn] = tm

    # ── Conversation events ───────────────────────────────────────────────────

    def record_context_messages(
        self, turn: int, messages: List[Dict[str, Any]]
    ) -> None:
        """
        Record the messages that were in the LLM context for this turn.

        Only user and assistant messages are recorded (system prompt is
        omitted to keep the log concise).  Tool messages are also omitted
        here; they are captured via ``record_tool_call`` / ``record_tool_result``.
        """
        tm = self._turns.get(turn)
        if tm is None:
            return
        for msg in messages:
            role = msg.get("role", "")
            if role == "system":
                continue  # skip system prompt
            if role == "tool":
                continue  # captured separately
            content = msg.get("content") or ""
            if isinstance(content, list):
                # Some providers return content as a list of parts.
                content = " ".join(
                    p.get("text", "") if isinstance(p, dict) else str(p)
                    for p in content
                )
            kind = "context_user" if role == "user" else "context_assistant"
            tm.conversation_events.append(
                ConversationEvent(kind=kind, content=str(content))
            )

    def record_model_response(self, turn: int, text: str) -> None:
        """Record the model's text output for this turn."""
        tm = self._turns.get(turn)
        if tm is not None and text:
            tm.conversation_events.append(
                ConversationEvent(kind="model_response", content=text)
            )

    # ── Tool calls ────────────────────────────────────────────────────────────

    def record_tool_call(
        self,
        name: str,
        elapsed_s: float,
        args: Optional[Dict[str, Any]] = None,
        result: Optional[str] = None,
    ) -> None:
        """Append a tool call record to the current turn."""
        tm = self._turns.get(self._current_turn)
        if tm is None:
            return
        snippet = result[:500] if result else None
        tm.tool_calls.append(
            ToolCallMetrics(
                name=name,
                elapsed_s=round(elapsed_s, 3),
                args=args,
                result_snippet=snippet,
            )
        )
        # Also record as conversation events.
        tm.conversation_events.append(
            ConversationEvent(kind="tool_call", content="", name=name, args=args)
        )
        if result is not None:
            tm.conversation_events.append(
                ConversationEvent(
                    kind="tool_result",
                    content=snippet or "",
                    name=name,
                )
            )

    # ── Steps ─────────────────────────────────────────────────────────────────

    def record_step_start(self, step: int, name: str) -> None:
        """Record the start of an agent step (from a STEP_SUMMARY event)."""
        sm = StepMetrics(step=step, name=name, started_at=_utcnow())
        self._open_steps[step] = (time.monotonic(), sm)

    def record_step_end(self, step: int) -> None:
        """
        Record the end of an agent step (from a STEP_RESULT event) and attach
        it to the current turn.
        """
        entry = self._open_steps.pop(step, None)
        if entry is None:
            return
        t0, sm = entry
        sm.elapsed_s = round(time.monotonic() - t0, 3)
        tm = self._turns.get(self._current_turn)
        if tm is not None:
            tm.steps.append(sm)

    # ── Finalise ──────────────────────────────────────────────────────────────

    def finish_session(
        self,
        conversation: List[Dict[str, Any]],
        final_result: Dict[str, Any],
        codebase: str = "session",
        llm_model: Optional[str] = None,
    ) -> SessionMetrics:
        """
        Finalise the session and return a ``SessionMetrics`` object.

        ``conversation`` is the full chat message list (including system prompt).
        ``final_result`` is the structured result dict from ``_build_result``.
        ``codebase`` is a short name extracted from the user prompt (used for
        the log filename).
        ``llm_model`` is the LLM model name used for this session.
        """
        total_elapsed = round(time.monotonic() - self._session_start, 3)
        finished_at = _utcnow()

        turns_list = [self._turns[k] for k in sorted(self._turns)]

        # Aggregate totals.
        total_tool_calls = sum(len(t.tool_calls) for t in turns_list)
        total_prompt = sum(t.prompt_tokens or 0 for t in turns_list)
        total_completion = sum(t.completion_tokens or 0 for t in turns_list)
        total_tokens = sum(t.total_tokens or 0 for t in turns_list)
        # Use None for token totals if no turn reported any tokens.
        any_tokens = any(t.total_tokens is not None for t in turns_list)

        # Compute per-turn averages for the summary.
        n_turns = len(turns_list)
        avg_elapsed = round(total_elapsed / n_turns, 3) if n_turns > 0 else None
        avg_tokens = round(total_tokens / n_turns) if n_turns > 0 and any_tokens else None

        summary: Dict[str, Any] = {
            "total_turns": n_turns,
            "total_tool_calls": total_tool_calls,
            "total_prompt_tokens": total_prompt if any_tokens else None,
            "total_completion_tokens": total_completion if any_tokens else None,
            "total_tokens": total_tokens if any_tokens else None,
            "avg_elapsed_per_turn_s": avg_elapsed,
            "avg_tokens_per_turn": avg_tokens,
            "final_status": final_result.get("status", "unknown"),
            "final_summary": final_result.get("summary"),
            "final_error": final_result.get("error_message") or final_result.get("assistant_question"),
        }

        # Sanitise conversation: drop raw_llm_response / llm_trace keys that
        # may be embedded in assistant messages; keep role + content only.
        clean_conv: List[Dict[str, Any]] = []
        for msg in conversation:
            entry: Dict[str, Any] = {"role": msg.get("role", "unknown")}
            if "content" in msg:
                entry["content"] = msg["content"]
            if "tool_calls" in msg:
                entry["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                entry["tool_call_id"] = msg["tool_call_id"]
            clean_conv.append(entry)

        # Sanitise final_result: drop large/internal fields before storing.
        clean_result: Optional[Dict[str, Any]] = None
        if final_result:
            clean_result = {
                k: v for k, v in final_result.items()
                if k not in ("raw_llm_response", "llm_trace", "metrics", "metrics_path")
            }

        return SessionMetrics(
            session_id=self._session_id,
            codebase=codebase,
            started_at=self._session_started_at,
            finished_at=finished_at,
            total_elapsed_s=total_elapsed,
            llm_model=llm_model,
            summary=summary,
            turns=turns_list,
            conversation=clean_conv,
            final_result=clean_result,
        )


# ---------------------------------------------------------------------------
# Codebase name extraction
# ---------------------------------------------------------------------------

def extract_codebase_name(messages: List[Dict[str, Any]]) -> str:
    """
    Heuristically extract a short codebase name from the first user message.

    Tries (in order):
    1. A path component that looks like a project name
       (e.g. ``examples/art_simple`` → ``art_simple``).
    2. A snake_case identifier with at least one underscore (e.g.
       ``matrix_mul_mpi``, ``art_simple``).
    3. The first CamelCase or long identifier that is not a stop-word.
    4. Falls back to ``"session"``.
    """
    text = ""
    for msg in messages:
        if msg.get("role") == "user":
            text = str(msg.get("content") or "")
            break
    if not text:
        return "session"

    # 1. Path-like tokens: grab the last component.
    path_matches = re.findall(r"[\w.-]+/[\w./-]+", text)
    for pm in path_matches:
        parts = [p for p in pm.replace("\\", "/").split("/") if p and p != "."]
        if parts:
            candidate = parts[-1]
            # Strip common extensions.
            candidate = re.sub(r"\.(c|cc|cpp|h|py|f90|f|txt|md|sh)$", "", candidate)
            if len(candidate) >= 3:
                return _sanitise_name(candidate)

    # 2. snake_case identifiers with at least one underscore (likely project names).
    snake_matches = re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", text)
    stop_snake = {"with_the", "in_the", "of_the"}
    for sm in snake_matches:
        if sm not in stop_snake and len(sm) >= 4:
            return _sanitise_name(sm)

    # 3. CamelCase / long identifiers.
    words = re.findall(r"[A-Za-z][A-Za-z0-9_]{3,}", text)
    stop = {"with", "that", "this", "from", "have", "will", "your", "code",
            "file", "path", "make", "help", "want", "need", "using", "into",
            "each", "some", "more", "also", "then", "when", "where", "which",
            "should", "would", "could", "their", "there", "about", "after",
            "before", "every", "other", "these", "those", "being", "doing",
            "Please", "Describe", "application", "environment", "cluster",
            "resilient", "deployment", "checkpointing", "tolerate"}
    for w in words:
        if w not in stop:
            return _sanitise_name(w.lower())

    return "session"


def _sanitise_name(name: str) -> str:
    """Replace non-alphanumeric characters with underscores; truncate to 40."""
    name = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    return name[:40] or "session"


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def log_session(metrics: SessionMetrics, output_dir: str) -> str:
    """
    Save the full session log to ``<output_dir>/log/<codebase>_<YYYYMMDD>.json``.

    If a file with the same name already exists (same codebase, same date) a
    counter suffix is appended (``_2``, ``_3``, …) so no session is ever
    silently overwritten.

    Returns the absolute path of the written file.
    """
    log_dir = Path(output_dir) / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    base_name = f"{metrics.codebase}_{date_str}"
    file_path = log_dir / f"{base_name}.json"

    # Avoid overwriting an existing file from a different session.
    counter = 2
    while file_path.exists():
        file_path = log_dir / f"{base_name}_{counter}.json"
        counter += 1

    data = asdict(metrics)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    return str(file_path)


def export_metrics(metrics: SessionMetrics, output_dir: str) -> str:
    """
    Serialise ``metrics`` to a JSON file and return the file path.

    The file is written to ``<output_dir>/metrics/metrics_<session_id>.json``.
    The ``metrics/`` subdirectory is created if it does not exist.

    .. note::
        Prefer :func:`log_session` for the always-on audit log.  This function
        is kept for the web UI download endpoint which uses the session UUID as
        the filename.
    """
    metrics_dir = Path(output_dir) / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    file_path = metrics_dir / f"metrics_{metrics.session_id}.json"

    data = asdict(metrics)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    return str(file_path)


def metrics_summary(metrics: SessionMetrics) -> Dict[str, Any]:
    """
    Return a compact summary dict suitable for embedding in the ``done`` SSE
    event.  Includes session ID, total elapsed time, aggregate counts, and
    per-turn breakdown with timing and token data.
    """
    s = metrics.summary
    per_turn = [
        {
            "turn": t.turn,
            "started_at": t.started_at,
            "elapsed_s": t.elapsed_s,
            "prompt_tokens": t.prompt_tokens,
            "completion_tokens": t.completion_tokens,
            "total_tokens": t.total_tokens,
            "tool_call_count": len(t.tool_calls),
            "step_count": len(t.steps),
            # Include tool call names for richer compact format.
            "tool_call_names": [tc.name for tc in t.tool_calls],
            # Include step numbers and names for richer compact format.
            "step_numbers": [st.step for st in t.steps],
            "step_names": [st.name for st in t.steps],
        }
        for t in metrics.turns
    ]
    return {
        "session_id": metrics.session_id,
        "codebase": metrics.codebase,
        "started_at": metrics.started_at,
        "finished_at": metrics.finished_at,
        "total_elapsed_s": metrics.total_elapsed_s,
        "llm_model": metrics.llm_model,
        "total_turns": s.get("total_turns"),
        "total_tool_calls": s.get("total_tool_calls"),
        "total_prompt_tokens": s.get("total_prompt_tokens"),
        "total_completion_tokens": s.get("total_completion_tokens"),
        "total_tokens": s.get("total_tokens"),
        "avg_elapsed_per_turn_s": s.get("avg_elapsed_per_turn_s"),
        "avg_tokens_per_turn": s.get("avg_tokens_per_turn"),
        "final_status": s.get("final_status"),
        "final_summary": s.get("final_summary"),
        "per_turn": per_turn,
    }
