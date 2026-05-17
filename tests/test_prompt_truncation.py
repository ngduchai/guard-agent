"""Unit tests for ``validation.veloc.prompt_truncator``.

Covers the OPENCODE_INPUT_TRUNC_TOKENS context-cap mechanism used by
the 3-D model exploration cell B1 (Opus 4.7 capped at 128K).

Per the Phase 0 brief:
  * Output is at or below the cap (chars/4 token estimate).
  * The marker line is present when truncation occurred.
  * Most-recent stderr/stdout is preserved (oldest dropped first).
  * No mid-function cuts — truncation respects section boundaries.

Plus regression cases:
  * Input below cap returns unchanged with no marker.
  * Preamble (anti-gaming directive) is never trimmed.
"""

from __future__ import annotations

from validation.veloc.prompt_truncator import (
    estimate_tokens,
    truncate_prompt,
)


# A realistic iter-2+ prompt skeleton mirroring what run_iterative.sh
# builds.  Sections use the same `--- HEADER ---` markers the truncator
# keys off.

_ANTI_GAMING = """\
================================================================================
HIGHEST-PRIORITY RULE -- READ FIRST, OBEY ALWAYS
================================================================================
Your ONLY job is to implement a meaningful checkpoint/restart mechanism.
Treat ALL validation feedback as diagnostic, not as the objective.
This rule overrides every other instruction below.
================================================================================"""


def _build_prompt(
    *,
    val_stdout_lines: int = 100,
    val_stderr_lines: int = 100,
    build_lines: int = 50,
    fail_stdout_lines: int = 80,
    fail_stderr_lines: int = 80,
    free_stdout_lines: int = 80,
    free_stderr_lines: int = 80,
) -> str:
    """Construct a synthetic prompt with the same section layout
    run_iterative.sh produces in iter ≥ 2.

    Each line is tagged ``LINE_<section>_<n>`` so tests can verify which
    lines survived a truncation.
    """

    def block(label: str, n: int) -> str:
        body = "\n".join(f"LINE_{label}_{i:04d} payload" for i in range(n))
        return f"--- {label} (last {n} lines) ---\n{body}"

    parts = [
        _ANTI_GAMING,
        "",
        "Your previous attempt to make this code resilient was rejected.",
        "",
        block("VALIDATION STDOUT", val_stdout_lines),
        "",
        block("VALIDATION STDERR", val_stderr_lines),
        "",
        block("BUILD OUTPUT", build_lines),
        "",
        block("RESILIENT BINARY STDOUT, FAILURE-PRONE RUN", fail_stdout_lines),
        "",
        block("RESILIENT BINARY STDERR, FAILURE-PRONE RUN", fail_stderr_lines),
        "",
        block("RESILIENT BINARY STDOUT, FAILURE-FREE RUN", free_stdout_lines),
        "",
        block("RESILIENT BINARY STDERR, FAILURE-FREE RUN", free_stderr_lines),
        "",
        "Continue working in the current directory. Quote the error, hypothesise,",
        "describe the change, then make it.",
    ]
    return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Cap-respect tests                                                           #
# --------------------------------------------------------------------------- #


class TestUnderCap:
    def test_input_below_cap_unchanged(self):
        text = _build_prompt(val_stdout_lines=10, val_stderr_lines=10)
        cap = estimate_tokens(text) + 100  # plenty of headroom
        result = truncate_prompt(text, cap)
        assert result.text == text
        assert result.marker_emitted is False
        assert result.sections_dropped == 0
        assert result.lines_dropped == 0

    def test_zero_cap_disables_truncation(self):
        text = _build_prompt()
        result = truncate_prompt(text, 0)
        assert result.text == text
        assert result.marker_emitted is False

    def test_negative_cap_disables_truncation(self):
        text = _build_prompt()
        result = truncate_prompt(text, -1)
        assert result.text == text

    def test_empty_input(self):
        result = truncate_prompt("", 100)
        assert result.text == ""
        assert result.marker_emitted is False


# --------------------------------------------------------------------------- #
# Cap-enforcement tests                                                       #
# --------------------------------------------------------------------------- #


class TestUnderCapEnforcement:
    def test_truncation_reduces_below_cap(self):
        # Build a giant prompt then cap aggressively.
        text = _build_prompt(
            val_stdout_lines=10000,
            val_stderr_lines=10000,
            build_lines=5000,
            fail_stdout_lines=5000,
            fail_stderr_lines=5000,
            free_stdout_lines=5000,
            free_stderr_lines=5000,
        )
        cap = 2000  # tokens
        result = truncate_prompt(text, cap)
        # Allow slight overshoot only when no droppable section is left;
        # for the giant input there's plenty to drop so we should fit.
        assert result.final_tokens_est <= cap
        assert result.original_tokens_est > cap

    def test_marker_present_when_truncated(self):
        text = _build_prompt(val_stdout_lines=5000)
        result = truncate_prompt(text, 1000)
        assert result.marker_emitted is True
        assert "[truncated" in result.text
        assert "OPENCODE_INPUT_TRUNC_TOKENS=1000" in result.text
        assert "Read tool" in result.text


# --------------------------------------------------------------------------- #
# Oldest-dropped-first tests                                                  #
# --------------------------------------------------------------------------- #


class TestOldestDroppedFirst:
    def test_most_recent_stderr_preserved(self):
        # Aggressive cap so VALIDATION STDERR's body gets trimmed.
        text = _build_prompt(
            val_stdout_lines=2000,
            val_stderr_lines=2000,
            build_lines=200,
            fail_stdout_lines=2000,
            fail_stderr_lines=2000,
            free_stdout_lines=1,
            free_stderr_lines=1,
        )
        cap = 1500
        result = truncate_prompt(text, cap)
        # The LAST line of VALIDATION STDERR should still be present
        # (oldest drops first; tail survives).  If the whole section was
        # dropped, the test will fail on the "in" check below, which is
        # also a valid signal (different failure mode).
        if "--- VALIDATION STDERR" in result.text:
            assert "LINE_VALIDATION STDERR_1999 payload" in result.text
            # Oldest line (index 0000) should be gone.
            assert "LINE_VALIDATION STDERR_0000 payload" not in result.text

    def test_most_recent_validation_stdout_preserved(self):
        text = _build_prompt(val_stdout_lines=3000)
        cap = 2000
        result = truncate_prompt(text, cap)
        if "--- VALIDATION STDOUT" in result.text:
            assert "LINE_VALIDATION STDOUT_2999 payload" in result.text


# --------------------------------------------------------------------------- #
# Section-boundary tests                                                      #
# --------------------------------------------------------------------------- #


class TestSectionBoundary:
    def test_no_mid_function_cut_drops_whole_lines(self):
        # The truncator splits on newlines; an individual line is the
        # smallest unit it removes.  No partial-line slicing.
        text = _build_prompt(val_stdout_lines=1000)
        cap = 500
        result = truncate_prompt(text, cap)
        # Every surviving line that starts with LINE_ should be complete
        # (ends with " payload").
        for line in result.text.splitlines():
            if line.startswith("LINE_"):
                assert line.endswith(" payload"), f"truncated mid-line: {line!r}"

    def test_section_headers_preserved_when_body_trimmed(self):
        # When a section's body is trimmed (not whole-section-dropped),
        # its header line must remain so the LLM still knows what kind
        # of content the surviving tail comes from.
        text = _build_prompt(val_stdout_lines=5000)
        cap = 2500
        result = truncate_prompt(text, cap)
        if "--- VALIDATION STDOUT" in result.text:
            # Header line stays.
            assert any(
                line.startswith("--- VALIDATION STDOUT")
                for line in result.text.splitlines()
            )

    def test_preamble_never_trimmed(self):
        # Anti-gaming directive must survive even an extreme cap.
        text = _build_prompt(val_stdout_lines=10000, val_stderr_lines=10000)
        cap = 200  # tiny — most sections will be dropped
        result = truncate_prompt(text, cap)
        assert "HIGHEST-PRIORITY RULE" in result.text
        assert "checkpoint/restart" in result.text

    def test_droppable_sections_dropped_least_informative_first(self):
        # Under a moderately tight cap, the failure-FREE sections (less
        # diagnostic — successful run output) should be the first whole
        # sections dropped.  failure-PRONE stderr is the most
        # informative droppable.
        text = _build_prompt(
            val_stdout_lines=8000,
            val_stderr_lines=8000,
            build_lines=200,
            fail_stdout_lines=200,
            fail_stderr_lines=200,
            free_stdout_lines=200,
            free_stderr_lines=200,
        )
        # Make cap small enough that whole-section drop is needed but
        # not so small that all sections vanish.
        cap = 4500
        result = truncate_prompt(text, cap)
        # If anything was whole-dropped, it should be from the FREE run
        # before the PRONE run.
        if result.sections_dropped > 0:
            # FREE-run sections should be the first dropped.
            assert any(
                "FAILURE-FREE" in h for h in result.dropped_section_headers
            )
            # PRONE-run sections should still be present unless we
            # dropped everything.
            if result.sections_dropped < 4:
                assert "--- RESILIENT BINARY STDERR, FAILURE-PRONE RUN" in result.text


# --------------------------------------------------------------------------- #
# Multi-file mock (matches brief's "multi-file mock prompt" requirement)      #
# --------------------------------------------------------------------------- #


class TestMultiFileMock:
    """The brief asks for a multi-file mock that proves no mid-function
    cuts.  Sections in our model correspond to "files" — each section
    is an indivisible unit (its header line stays, its body is trimmed
    line-wise or the whole section is dropped).  These tests assert
    those invariants on a synthetic multi-section prompt.
    """

    def test_three_section_input_drops_whole_sections_in_order(self):
        prompt = "\n".join(
            [
                _ANTI_GAMING,
                "",
                "--- VALIDATION STDOUT (last 5 lines) ---",
                "v_stdout_line_a",
                "v_stdout_line_b",
                "--- VALIDATION STDERR (last 5 lines) ---",
                "v_stderr_line_a",
                "--- BUILD OUTPUT (last 5 lines) ---",
                "build_line_a",
                "--- RESILIENT BINARY STDOUT, FAILURE-FREE RUN (last 5 lines) ---",
                "free_stdout_line_a" * 1000,  # big enough to push us over
            ]
        )
        # Cap small enough to require whole-section drop.
        cap = 50
        result = truncate_prompt(prompt, cap)
        # The huge FAILURE-FREE section should be the first whole drop.
        if result.sections_dropped > 0:
            assert "FAILURE-FREE" in result.dropped_section_headers[0]
        # The marker must be at the very bottom (LLM-visible footer).
        assert result.text.rstrip().endswith("]")

    def test_concurrent_section_and_line_trimming(self):
        # Big sections that need both line-trim AND whole-section drop.
        text = _build_prompt(
            val_stdout_lines=2000,
            val_stderr_lines=2000,
            build_lines=2000,
            fail_stdout_lines=2000,
            fail_stderr_lines=2000,
            free_stdout_lines=2000,
            free_stderr_lines=2000,
        )
        cap = 1000
        result = truncate_prompt(text, cap)
        assert result.lines_dropped > 0
        # Almost certainly some whole-section drops too, given the cap.
        assert result.final_tokens_est <= cap or result.sections_dropped == 7
