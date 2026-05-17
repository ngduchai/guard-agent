"""Section-aware prompt truncator for the iter-loop wrapper.

Used by ``validation/veloc/scripts/run_iterative.sh`` when the
``OPENCODE_INPUT_TRUNC_TOKENS`` env var is set (3-D model exploration
cell B1: Opus 4.7 capped at 128K context).  Truncates a constructed
iter prompt so its rough token count fits under the cap while
preserving the most informative content.

Design (per Phase 0 brief):
    * Cut at section boundaries (``--- ... ---`` headers); never split
      mid-function.
    * For stdout / stderr sections, drop the OLDEST lines first (they
      are appended to the prompt by ``run_iterative.sh`` via ``tail
      -N``, so dropping from the TOP of the in-prompt block keeps the
      most recent — and most diagnostic — output).
    * If after per-section trimming the cap is still exceeded, drop
      entire trailing sections in priority order (least-informative
      sections first; the anti-gaming directive and initial-prompt
      preamble are always preserved).
    * Emit a single marker line so the LLM knows what's missing and
      can request specific files via Read.

The token count is estimated as ``len(text) / 4`` — a standard English
approximation.  Exact tokenisation would require pulling in
``tiktoken`` per provider; the cap is itself an approximation (cell B1
caps at 128K to mimic the historical context-window norm), so the
approximation is acceptable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# Characters per token (rough English approximation, used by OpenAI's
# tiktoken docs as a back-of-envelope rule).
_CHARS_PER_TOKEN = 4.0


# Section headers we recognise in iter-2+ prompts built by
# ``run_iterative.sh``.  Order matters when we have to drop whole
# sections under extreme cap pressure: later entries are dropped first.
# Anti-gaming directive + initial preamble are never dropped — they live
# in ``_PREAMBLE_SECTIONS`` and ``_TAIL_SECTIONS`` respectively.
_DROP_ORDER: List[str] = [
    # Most-droppable first (kept last in prompt construction order):
    "--- RESILIENT BINARY STDERR, FAILURE-FREE RUN",
    "--- RESILIENT BINARY STDOUT, FAILURE-FREE RUN",
    "--- RESILIENT BINARY STDERR, FAILURE-PRONE RUN",
    "--- RESILIENT BINARY STDOUT, FAILURE-PRONE RUN",
    "--- BUILD OUTPUT",
    "--- VALIDATION STDERR",
    "--- VALIDATION STDOUT",
]


_MARKER_TEMPLATE = (
    "[truncated {sections_dropped} sections / {lines_dropped} lines under "
    "OPENCODE_INPUT_TRUNC_TOKENS={cap} cap — agent may use Read tool to "
    "fetch specific files from build/iterative_logs/<APP>_<LABEL>/iter_*/]"
)


@dataclass
class TruncationResult:
    """Outcome of a truncation pass."""

    text: str
    original_tokens_est: int
    final_tokens_est: int
    sections_dropped: int = 0
    lines_dropped: int = 0
    sections_trimmed: int = 0
    marker_emitted: bool = False
    dropped_section_headers: List[str] = field(default_factory=list)


def estimate_tokens(text: str) -> int:
    """Rough token estimate for English-ish text (chars / 4).

    Stable, dependency-free, and matches the order-of-magnitude
    accuracy needed for a coarse 128K-byte cap.
    """
    return int(len(text) / _CHARS_PER_TOKEN)


def _split_into_sections(text: str) -> List[List[str]]:
    """Split ``text`` at lines starting with ``--- ``.

    Returns a list of sections, where each section is a list of lines.
    The first section is the preamble (everything before the first
    ``--- `` marker) and contains the anti-gaming directive +
    failure-analysis discipline text.  Subsequent sections each start
    with a ``--- ... ---`` header line.
    """
    sections: List[List[str]] = []
    current: List[str] = []
    for line in text.splitlines():
        if line.startswith("--- ") and current:
            sections.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append(current)
    return sections


def _join_sections(sections: List[List[str]]) -> str:
    """Inverse of ``_split_into_sections``.  Preserves trailing newline
    conventions used by ``run_iterative.sh`` (each section is joined by
    a single newline; the final string ends with a newline)."""
    return "\n".join("\n".join(sec) for sec in sections) + "\n"


def _trim_oldest_lines(section: List[str], target_lines: int) -> int:
    """Drop oldest content lines from a section, keeping its header
    line (first entry) and the last ``target_lines`` content lines.

    Returns the number of lines dropped (0 if the section is already
    below the target).
    """
    if target_lines < 0:
        target_lines = 0
    header = section[0] if section and section[0].startswith("--- ") else None
    body_start = 1 if header is not None else 0
    body_len = len(section) - body_start
    if body_len <= target_lines:
        return 0
    drop = body_len - target_lines
    # Mutate in place: keep header + last target_lines body lines.
    del section[body_start : body_start + drop]
    return drop


def truncate_prompt(text: str, max_tokens: int) -> TruncationResult:
    """Truncate ``text`` so its estimated token count fits under
    ``max_tokens``.

    Strategy (in order):
      1. If already under cap → return unchanged.
      2. Trim each droppable section's body to a floor of 20 lines
         (oldest dropped first) until under cap.
      3. If still over cap, drop entire droppable sections from the
         end of ``_DROP_ORDER`` (least informative first).
      4. Emit a marker line at the bottom recording what was dropped.

    The preamble (anti-gaming directive + initial-prompt / failure-
    analysis-discipline text) is NEVER touched — it's the highest-
    priority frame for the LLM.

    Args:
        text: The fully-constructed iter prompt.
        max_tokens: Cap from ``OPENCODE_INPUT_TRUNC_TOKENS``.  Values
            <= 0 disable truncation (returns input unchanged).

    Returns:
        A ``TruncationResult`` with the (possibly trimmed) text and
        bookkeeping.
    """
    original_tokens = estimate_tokens(text)
    if max_tokens <= 0 or original_tokens <= max_tokens:
        return TruncationResult(
            text=text,
            original_tokens_est=original_tokens,
            final_tokens_est=original_tokens,
        )

    # Reserve a small budget for the trailing marker so the final
    # output (text + marker) actually fits under max_tokens.  The
    # marker template is bounded; we estimate once.
    _marker_budget = estimate_tokens(
        _MARKER_TEMPLATE.format(sections_dropped=999, lines_dropped=999999, cap=max_tokens)
    ) + 2  # +2 for surrounding whitespace
    effective_cap = max(1, max_tokens - _marker_budget)

    sections = _split_into_sections(text)
    # Preamble is sections[0] (no leading marker line).  Droppable
    # sections are everything starting at index 1 that has a header in
    # _DROP_ORDER.  Anything else (rare in current run_iterative.sh) is
    # preserved as if it were preamble.
    droppable_idx_by_header: dict[str, int] = {}
    for i, sec in enumerate(sections[1:], start=1):
        if not sec:
            continue
        header_line = sec[0]
        for h in _DROP_ORDER:
            if header_line.startswith(h):
                droppable_idx_by_header[h] = i
                break

    lines_dropped_total = 0
    sections_trimmed = 0

    # Pass 1: progressively shrink each droppable section.  Start at the
    # last (least-informative) section so the most-informative ones
    # retain their lines for as long as possible.
    floor = 20  # lines kept per section minimum (before whole-section drop)
    for header in _DROP_ORDER:
        if estimate_tokens(_join_sections(sections)) <= effective_cap:
            break
        i = droppable_idx_by_header.get(header)
        if i is None:
            continue
        dropped = _trim_oldest_lines(sections[i], floor)
        if dropped > 0:
            lines_dropped_total += dropped
            sections_trimmed += 1

    # Pass 2: if still over cap, drop entire sections from the END of
    # _DROP_ORDER (least informative first).
    sections_dropped: List[str] = []
    while estimate_tokens(_join_sections(sections)) > effective_cap:
        # Find the last droppable header still present.
        target_header = None
        target_idx = None
        for header in _DROP_ORDER:
            i = droppable_idx_by_header.get(header)
            if i is not None and i < len(sections):
                target_header = header
                target_idx = i
                break
        if target_idx is None:
            # Nothing left to drop — can't fit under cap.  Return what
            # we have (will still emit marker so the LLM sees the
            # situation).
            break
        # Count what we're about to drop.
        sec = sections[target_idx]
        body_lines = max(0, len(sec) - 1)  # exclude header
        lines_dropped_total += body_lines
        sections_dropped.append(target_header)
        # Remove the section entirely.
        del sections[target_idx]
        # Reindex the lookup table since we deleted an entry.
        droppable_idx_by_header = {}
        for i, s in enumerate(sections[1:], start=1):
            if not s:
                continue
            hl = s[0]
            for h in _DROP_ORDER:
                if hl.startswith(h):
                    droppable_idx_by_header[h] = i
                    break

    # Append the marker so the LLM knows the prompt has been clipped.
    marker_emitted = (lines_dropped_total > 0) or bool(sections_dropped)
    if marker_emitted:
        marker = _MARKER_TEMPLATE.format(
            sections_dropped=len(sections_dropped),
            lines_dropped=lines_dropped_total,
            cap=max_tokens,
        )
        # Append as its own trailing section so it survives any future
        # re-truncation passes (a re-truncator would treat it as
        # preamble since it has no `--- ` header).
        sections.append([marker])

    final_text = _join_sections(sections)
    return TruncationResult(
        text=final_text,
        original_tokens_est=original_tokens,
        final_tokens_est=estimate_tokens(final_text),
        sections_dropped=len(sections_dropped),
        lines_dropped=lines_dropped_total,
        sections_trimmed=sections_trimmed,
        marker_emitted=marker_emitted,
        dropped_section_headers=sections_dropped,
    )


def main() -> None:  # pragma: no cover — thin shell entry point
    """CLI used by ``run_iterative.sh``.

    Reads the prompt from stdin, writes the (possibly truncated)
    prompt to stdout, and writes a one-line JSON bookkeeping record to
    stderr so the iter log captures what happened.
    """
    import json
    import os
    import sys

    cap_raw = os.environ.get("OPENCODE_INPUT_TRUNC_TOKENS", "").strip()
    try:
        cap = int(cap_raw) if cap_raw else 0
    except ValueError:
        # Bad cap value → behave as if unset (don't crash the iter loop).
        cap = 0

    text = sys.stdin.read()
    result = truncate_prompt(text, cap)
    sys.stdout.write(result.text)
    sys.stderr.write(
        json.dumps(
            {
                "cap_tokens": cap,
                "original_tokens_est": result.original_tokens_est,
                "final_tokens_est": result.final_tokens_est,
                "sections_dropped": result.sections_dropped,
                "lines_dropped": result.lines_dropped,
                "sections_trimmed": result.sections_trimmed,
                "marker_emitted": result.marker_emitted,
                "dropped_section_headers": result.dropped_section_headers,
            }
        )
        + "\n"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
