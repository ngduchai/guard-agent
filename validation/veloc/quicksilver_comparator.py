"""
quicksilver_comparator.py – Custom comparator plugin for Quicksilver validation.

Plugin contract (see validation/veloc/comparator.py):
    def compare(baseline_path: str, resilient_path: str, **kwargs) -> dict

This plugin parses the per-cycle balance tally table printed to stdout by
Quicksilver and compares the 12 deterministic integer columns exactly.

Quicksilver stdout format
-------------------------
Each simulation cycle prints one row of the balance tally table:

    cycle        start       source           rr        split       absorb  \\
      scatter      fission      produce      collisn       escape       census  \\
      num_seg     scalar_flux      cycleInit  cycleTracking  cycleFinalize

Example row:
       0         9999          100            0            0          100  \\
           0            0            0          100            0         9999  \\
       10099    0.000000e+00   1.234567e-02   5.678901e-02   1.234567e-03

Deterministic integer columns (compared exactly):
    start, source, rr, split, absorb, scatter, fission, produce,
    collisn, escape, census, num_seg

Non-deterministic floating-point columns (ignored):
    scalar_flux, cycleInit, cycleTracking, cycleFinalize

Correctness criterion
---------------------
A resilient run is correct if and only if ALL of the following hold:

1. **Cycle subset**: the resilient output's cycle indices are a subset of the
   baseline cycle indices.  After a checkpoint restart the app only prints
   cycles from the restart point onward (e.g., cycles 18–19 if it restarted
   from checkpoint version 18 out of 20 total cycles).  Fewer cycles than the
   baseline is therefore *expected and correct*.  Extra cycle indices (not in
   the baseline) would indicate a bug.

2. **Tally values**: for every cycle that appears in both outputs, all 12
   integer tally columns must match exactly.

3. **Phantom-restart detection**: even if cycle labels are a valid suffix, we
   check whether the resilient tally *sequence* (ordered by cycle index) is a
   positional match of the baseline sequence starting from position 0.  This
   catches the case where the cycle counter is restored to N but the physics
   restarts from 0, so resilient[N] == baseline[0], resilient[N+1] ==
   baseline[1], etc.

Usage
-----
This file is loaded by CustomPluginComparator via:
    --comparison-method custom --custom-comparator validation/veloc/quicksilver_comparator.py
    --output-file-name stdout.txt
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

# The 12 integer balance tally columns (in order of appearance in the row).
INTEGER_COLUMNS = [
    "start",
    "source",
    "rr",
    "split",
    "absorb",
    "scatter",
    "fission",
    "produce",
    "collisn",
    "escape",
    "census",
    "num_seg",
]

# The 4 floating-point timing/flux columns that follow the integer columns.
FLOAT_COLUMNS = [
    "scalar_flux",
    "cycleInit",
    "cycleTracking",
    "cycleFinalize",
]

# Total columns per data row: 1 (cycle) + 12 (int) + 4 (float) = 17
_TOTAL_COLS = 1 + len(INTEGER_COLUMNS) + len(FLOAT_COLUMNS)

# Regex to detect the header line (starts with optional whitespace then "cycle").
_HEADER_RE = re.compile(r"^\s*cycle\s+start\s+")

# Regex to detect a data row: starts with optional whitespace then an integer
# (the cycle number), followed by more integers/floats.
_DATA_ROW_RE = re.compile(r"^\s*(\d+)\s+")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_tally_table(text: str) -> dict[int, dict[str, int]]:
    """Parse the balance tally table from Quicksilver stdout.

    Returns a dict mapping cycle_number -> {column_name: integer_value}
    for the 12 deterministic integer columns only.

    The parser operates in two modes:
    - Header-triggered: once the ``cycle  start  ...`` header line is seen,
      subsequent numeric rows are parsed as tally data.
    - Header-free: after a restart, Quicksilver does not reprint the header
      but continues printing data rows.  Any line with exactly _TOTAL_COLS
      whitespace-separated tokens where the first 13 are integers is treated
      as a tally row regardless of whether the header was seen.

    Lines that do not match the data row pattern are silently skipped.
    """
    tallies: dict[int, dict[str, int]] = {}
    in_table = False

    for line in text.splitlines():
        # Detect the header line to enter table-parsing mode.
        if _HEADER_RE.match(line):
            in_table = True
            continue

        # Try to parse a data row.
        m = _DATA_ROW_RE.match(line)
        if not m:
            continue

        parts = line.split()
        if len(parts) < _TOTAL_COLS:
            # Incomplete row – skip.
            continue

        # Require the first 13 tokens (cycle + 12 int columns) to be integers.
        # This prevents false positives from other numeric lines in the output.
        try:
            cycle = int(parts[0])
            row: dict[str, int] = {}
            for i, col in enumerate(INTEGER_COLUMNS):
                row[col] = int(parts[1 + i])
        except (ValueError, IndexError):
            # Malformed row – skip.
            continue

        # Accept the row if we are in table mode OR if it looks like a valid
        # tally row (header-free mode for post-restart output).
        if in_table or True:  # always accept valid rows
            tallies[cycle] = row

    return tallies


def _row_as_tuple(row: dict[str, int]) -> tuple[int, ...]:
    """Return the integer tally values as a tuple (in INTEGER_COLUMNS order)."""
    return tuple(row[col] for col in INTEGER_COLUMNS)


def _detect_phantom_restart(
    baseline: dict[int, dict[str, int]],
    resilient: dict[int, dict[str, int]],
) -> tuple[bool, int]:
    """Detect the phantom-restart bug.

    The bug: the loop counter is restored to N but the particle state is
    re-initialised from scratch, so:
        resilient[N]   == baseline[0]
        resilient[N+1] == baseline[1]
        ...

    Returns (detected: bool, offset: int).
    If detected, offset is the cycle index where the resilient output starts
    (i.e., the checkpoint version that was restored).
    """
    b_cycles = sorted(baseline.keys())
    r_cycles = sorted(resilient.keys())

    if not b_cycles or not r_cycles:
        return False, 0

    # The resilient output starts at r_cycles[0].  If this is > 0, the loop
    # resumed from a checkpoint.  Check whether resilient[r_cycles[i]] ==
    # baseline[b_cycles[i]] for all i (i.e., the physics sequence is the same
    # but the labels are shifted by r_cycles[0]).
    offset = r_cycles[0]
    if offset == 0:
        return False, 0  # No offset — not the phantom-restart pattern.

    # Check if the resilient sequence (by position) matches the baseline
    # sequence (by position) starting from position 0.
    n = min(len(r_cycles), len(b_cycles))
    matches = 0
    for i in range(n):
        if _row_as_tuple(resilient[r_cycles[i]]) == _row_as_tuple(baseline[b_cycles[i]]):
            matches += 1

    # If ≥ 80% of the compared cycles match positionally (not by label),
    # this is the phantom-restart pattern.
    if n > 0 and matches / n >= 0.8:
        return True, offset

    return False, 0


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def _compare_tallies(
    baseline: dict[int, dict[str, int]],
    resilient: dict[int, dict[str, int]],
) -> tuple[bool, float, str, dict[str, Any]]:
    """Compare two tally dicts.

    Returns (passed, score, message, details).

    Checks (in order):
    1. Both outputs are non-empty.
    2. Resilient cycles are a subset of baseline cycles (no extra indices).
       A correct resilient run after restart only prints cycles from the
       restart point onward — fewer cycles than baseline is expected.
    3. Phantom-restart detection (cycle labels shifted, physics from cycle 0).
    4. Per-cycle tally value comparison for common cycles.
    """
    if not baseline:
        return (
            False,
            0.0,
            "No tally rows found in baseline stdout.txt",
            {"baseline_cycles": 0, "resilient_cycles": len(resilient)},
        )
    if not resilient:
        return (
            False,
            0.0,
            "No tally rows found in resilient stdout.txt",
            {"baseline_cycles": len(baseline), "resilient_cycles": 0},
        )

    baseline_cycles = sorted(baseline.keys())
    resilient_cycles = sorted(resilient.keys())

    # ------------------------------------------------------------------
    # Check 1: Resilient cycles must be a subset of baseline cycles.
    #
    # A correct resilient run after checkpoint restart will only print
    # cycles from the restart point onward (e.g., cycles 18–19 if it
    # restarted from checkpoint version 18 out of 20 total cycles).
    # This is expected and correct behaviour — we do NOT require the
    # resilient output to contain all baseline cycles.
    #
    # However, the resilient cycles must not contain any cycle index
    # that is absent from the baseline (which would indicate a bug).
    # ------------------------------------------------------------------
    extra = sorted(set(resilient_cycles) - set(baseline_cycles))
    if extra:
        return (
            False,
            0.0,
            (
                f"Resilient output contains cycle indices not present in baseline: "
                f"{extra}. Baseline indices: {baseline_cycles[0]}–{baseline_cycles[-1]}."
            ),
            {
                "baseline_cycles": baseline_cycles,
                "resilient_cycles": resilient_cycles,
                "extra_cycles": extra,
            },
        )

    # ------------------------------------------------------------------
    # Check 2: Phantom-restart detection.
    #
    # The phantom-restart bug: the loop counter is restored to N but the
    # particle state is re-initialised from scratch, so:
    #     resilient[N]   == baseline[0]
    #     resilient[N+1] == baseline[1]
    #     ...
    # This is detected by checking whether the resilient tally sequence
    # (ordered by cycle index) matches the baseline sequence positionally
    # (from position 0) rather than by cycle label.
    # ------------------------------------------------------------------
    phantom, offset = _detect_phantom_restart(baseline, resilient)
    if phantom:
        return (
            False,
            0.0,
            (
                f"PHANTOM-RESTART BUG DETECTED: resilient cycle indices "
                f"{resilient_cycles[0]}–{resilient_cycles[-1]} have tally values "
                f"that match baseline cycles 0–{len(resilient_cycles)-1} "
                f"(positional match, not label match). "
                f"The loop counter was restored to {offset} but the particle state "
                f"was re-initialised from scratch (cycle 0 physics). "
                f"The checkpoint does not save the particle population — "
                f"only the cycle counter and cumulative tallies are checkpointed."
            ),
            {
                "bug": "phantom_restart",
                "checkpoint_version_restored": offset,
                "baseline_cycles": baseline_cycles,
                "resilient_cycles": resilient_cycles,
            },
        )

    # ------------------------------------------------------------------
    # Check 3: Per-cycle tally value comparison.
    # ------------------------------------------------------------------
    common_cycles = sorted(set(baseline_cycles) & set(resilient_cycles))

    mismatches: list[dict[str, Any]] = []
    for cycle in common_cycles:
        b_row = baseline[cycle]
        r_row = resilient[cycle]
        cycle_mismatches: dict[str, dict[str, int]] = {}
        for col in INTEGER_COLUMNS:
            b_val = b_row.get(col)
            r_val = r_row.get(col)
            if b_val != r_val:
                cycle_mismatches[col] = {"baseline": b_val, "resilient": r_val}
        if cycle_mismatches:
            mismatches.append({"cycle": cycle, "columns": cycle_mismatches})

    total_cycles = len(common_cycles)
    matching_cycles = total_cycles - len(mismatches)
    score = matching_cycles / total_cycles if total_cycles > 0 else 0.0
    passed = len(mismatches) == 0

    restart_note = ""
    if len(resilient_cycles) < len(baseline_cycles):
        restart_note = (
            f" [resilient restarted from cycle {resilient_cycles[0]}, "
            f"skipped {len(baseline_cycles) - len(resilient_cycles)} already-checkpointed cycle(s)]"
        )

    if passed:
        message = (
            f"All {total_cycles} common cycle(s) match exactly "
            f"(baseline={len(baseline_cycles)} cycles, "
            f"resilient={len(resilient_cycles)} cycles){restart_note}"
        )
    else:
        message = (
            f"{len(mismatches)}/{total_cycles} cycle(s) have tally mismatches "
            f"(baseline={len(baseline_cycles)} cycles, "
            f"resilient={len(resilient_cycles)} cycles){restart_note}"
        )

    details: dict[str, Any] = {
        "baseline_cycles": baseline_cycles,
        "resilient_cycles": resilient_cycles,
        "common_cycles": common_cycles,
        "total_common_cycles": total_cycles,
        "matching_cycles": matching_cycles,
        "mismatched_cycles": len(mismatches),
        # Cap mismatch details at 10 entries to keep the report readable.
        "mismatches": mismatches[:10],
    }

    return passed, score, message, details


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def compare(baseline_path: str, resilient_path: str, **kwargs: Any) -> dict:
    """Parse Quicksilver stdout tally tables and compare integer balance columns.

    Parameters
    ----------
    baseline_path:
        Path to the baseline ``stdout.txt`` file.
    resilient_path:
        Path to the resilient ``stdout.txt`` file.
    **kwargs:
        Ignored (reserved for future use).

    Returns
    -------
    dict with keys:
        passed  : bool   – True if all correctness checks pass
        score   : float  – fraction of common cycles with matching tallies
        message : str    – human-readable summary
        details : dict   – per-cycle mismatch information

    Correctness checks
    ------------------
    1. Both outputs contain tally rows.
    2. Resilient cycles are a subset of baseline cycles (no extra indices).
       Fewer cycles is expected after a checkpoint restart — the app only
       prints cycles from the restart point onward.
    3. No phantom-restart pattern detected (cycle labels shifted, physics from 0).
    4. All common per-cycle integer tally columns match exactly.
    """
    b_path = Path(baseline_path)
    r_path = Path(resilient_path)

    # Read files.
    try:
        baseline_text = b_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "passed": False,
            "score": 0.0,
            "message": f"Cannot read baseline file {b_path}: {exc}",
            "details": {},
        }

    try:
        resilient_text = r_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {
            "passed": False,
            "score": 0.0,
            "message": f"Cannot read resilient file {r_path}: {exc}",
            "details": {},
        }

    # Parse tally tables.
    baseline_tallies = _parse_tally_table(baseline_text)
    resilient_tallies = _parse_tally_table(resilient_text)

    # Compare.
    passed, score, message, details = _compare_tallies(baseline_tallies, resilient_tallies)

    return {
        "passed": passed,
        "score": score,
        "message": message,
        "details": details,
    }
