"""
examinimd_comparator.py – Custom comparator plugin for ExaMiniMD validation.

Plugin contract (see validation/veloc/comparator.py):
    def compare(baseline_path: str, resilient_path: str, **kwargs) -> dict

This plugin parses the per-timestep thermodynamic output table printed to
stdout by ExaMiniMD and compares the three physics columns with a tight
relative tolerance.

ExaMiniMD stdout format
-----------------------
The simulation prints a header line followed by one row per ``thermo`` interval:

    #Timestep Temperature PotE ETot Time Atomsteps/s
    0 1.400000 -6.332812 -4.232820 0.000000 0.000000e+00
    10 1.266963 -6.133598 -4.233161 0.123456 2.560000e+07
    ...
    100 0.732072 -5.330936 -4.232833 1.234567 2.560000e+07

    #Procs Particles | Time T_Force T_Neigh T_Comm T_Other | Steps/s Atomsteps/s ...
    1 256000 | ... PERFORMANCE

Physics columns (compared with relative tolerance):
    Temperature, PotE, ETot

Non-deterministic columns (ignored):
    Time, Atomsteps/s

LAMMPS-style output (--print-lammps flag) is also supported:

    Step Temp E_pair TotEng CPU
         0 1.400000 -6.332812 -4.232820 0.000000
    ...
    Loop time of ... on ... procs for ... steps with ... atoms

Correctness criterion
---------------------
All per-timestep physics columns (Temperature, PotE, ETot) must match within
``rtol`` (default 1e-6) between the baseline and resilient runs.

The resilient run may restart from a VeloC checkpoint, so early timestep rows
may be absent from the resilient output.  Only **common** timesteps are
compared.

Score: fraction of common timesteps where all three physics columns match
within tolerance (1.0 = perfect).

Usage
-----
This file is loaded by CustomPluginComparator via:
    --comparison-method custom
    --custom-comparator validation/veloc/examinimd_comparator.py
    --output-file-name stdout.txt
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Column definitions
# ---------------------------------------------------------------------------

# Physics columns that must match (relative tolerance).
PHYSICS_COLUMNS = ["Temperature", "PotE", "ETot"]

# Default relative tolerance for floating-point comparison.
DEFAULT_RTOL = 1e-6

# Regex: ExaMiniMD default header line.
_HEADER_RE = re.compile(r"^\s*#Timestep\s+Temperature\s+PotE\s+ETot\s+")

# Regex: LAMMPS-style header line.
_LAMMPS_HEADER_RE = re.compile(r"^\s*Step\s+Temp\s+E_pair\s+TotEng\s+CPU\s*$")

# Regex: data row – starts with optional whitespace then an integer (timestep).
_DATA_ROW_RE = re.compile(r"^\s*(\d+)\s+")

# Regex: PERFORMANCE summary line (skip).
_PERF_RE = re.compile(r"PERFORMANCE\s*$")

# Regex: "Loop time of ..." line (LAMMPS-style end marker, skip).
_LOOP_RE = re.compile(r"^\s*Loop time of")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_thermo_table(
    text: str,
) -> dict[int, dict[str, float]]:
    """Parse the thermodynamic output table from ExaMiniMD stdout.

    Supports both the default ExaMiniMD format and the LAMMPS-compatible
    format (enabled with ``--print-lammps``).

    Returns a dict mapping ``timestep -> {column_name: float_value}``
    for the three physics columns only.  Timing columns are discarded.

    Lines that do not match the data row pattern are silently skipped.
    """
    thermo: dict[int, dict[str, float]] = {}
    in_table = False
    lammps_mode = False

    for line in text.splitlines():
        # Skip PERFORMANCE summary and Loop-time lines.
        if _PERF_RE.search(line) or _LOOP_RE.match(line):
            in_table = False
            continue

        # Detect default ExaMiniMD header.
        if _HEADER_RE.match(line):
            in_table = True
            lammps_mode = False
            continue

        # Detect LAMMPS-style header.
        if _LAMMPS_HEADER_RE.match(line):
            in_table = True
            lammps_mode = True
            continue

        if not in_table:
            continue

        # Try to parse a data row.
        m = _DATA_ROW_RE.match(line)
        if not m:
            # Blank or non-numeric line – keep scanning (multiple thermo blocks
            # may appear if the run was restarted).
            continue

        parts = line.split()

        # Default format: Timestep Temperature PotE ETot Time Atomsteps/s  (6 cols)
        # LAMMPS format:  Step Temp E_pair TotEng CPU                       (5 cols)
        min_cols = 5 if lammps_mode else 6
        if len(parts) < min_cols:
            continue  # Incomplete row – skip.

        try:
            timestep = int(parts[0])
            if lammps_mode:
                # LAMMPS: Step Temp E_pair TotEng CPU
                temperature = float(parts[1])
                pote = float(parts[2])
                etot = float(parts[3])
            else:
                # Default: Timestep Temperature PotE ETot Time Atomsteps/s
                temperature = float(parts[1])
                pote = float(parts[2])
                etot = float(parts[3])

            thermo[timestep] = {
                "Temperature": temperature,
                "PotE": pote,
                "ETot": etot,
            }
        except (ValueError, IndexError):
            # Malformed row – skip.
            continue

    return thermo


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------

def _values_close(a: float, b: float, rtol: float) -> bool:
    """Return True if |a - b| / max(|a|, |b|, 1e-300) <= rtol."""
    denom = max(abs(a), abs(b), 1e-300)
    return abs(a - b) / denom <= rtol


def _compare_thermo(
    baseline: dict[int, dict[str, float]],
    resilient: dict[int, dict[str, float]],
    rtol: float = DEFAULT_RTOL,
) -> tuple[bool, float, str, dict[str, Any]]:
    """Compare two thermo dicts.

    Returns ``(passed, score, message, details)``.
    """
    if not baseline:
        return (
            False,
            0.0,
            "No thermo rows found in baseline stdout.txt",
            {"baseline_timesteps": 0, "resilient_timesteps": len(resilient)},
        )
    if not resilient:
        return (
            False,
            0.0,
            "No thermo rows found in resilient stdout.txt",
            {"baseline_timesteps": len(baseline), "resilient_timesteps": 0},
        )

    baseline_steps = sorted(baseline.keys())
    resilient_steps = sorted(resilient.keys())

    # The resilient run may have fewer timesteps if it restarted from a
    # checkpoint.  Compare only the timesteps present in BOTH outputs.
    common_steps = sorted(set(baseline_steps) & set(resilient_steps))

    if not common_steps:
        return (
            False,
            0.0,
            (
                f"No common timesteps between baseline ({baseline_steps[:5]}…) "
                f"and resilient ({resilient_steps[:5]}…)"
            ),
            {
                "baseline_timesteps": baseline_steps,
                "resilient_timesteps": resilient_steps,
                "common_timesteps": [],
            },
        )

    mismatches: list[dict[str, Any]] = []
    for step in common_steps:
        b_row = baseline[step]
        r_row = resilient[step]
        step_mismatches: dict[str, dict[str, float]] = {}
        for col in PHYSICS_COLUMNS:
            b_val = b_row.get(col)
            r_val = r_row.get(col)
            if b_val is None or r_val is None:
                step_mismatches[col] = {
                    "baseline": b_val,
                    "resilient": r_val,
                    "reason": "missing value",
                }
            elif not _values_close(b_val, r_val, rtol):
                rel_err = abs(b_val - r_val) / max(abs(b_val), abs(r_val), 1e-300)
                step_mismatches[col] = {
                    "baseline": b_val,
                    "resilient": r_val,
                    "rel_err": rel_err,
                }
        if step_mismatches:
            mismatches.append({"timestep": step, "columns": step_mismatches})

    total_steps = len(common_steps)
    matching_steps = total_steps - len(mismatches)
    score = matching_steps / total_steps if total_steps > 0 else 0.0
    passed = len(mismatches) == 0

    if passed:
        message = (
            f"All {total_steps} common timestep(s) match within rtol={rtol:.1e} "
            f"(baseline={len(baseline_steps)} steps, "
            f"resilient={len(resilient_steps)} steps)"
        )
    else:
        message = (
            f"{len(mismatches)}/{total_steps} timestep(s) have thermo mismatches "
            f"(rtol={rtol:.1e}; "
            f"baseline={len(baseline_steps)} steps, "
            f"resilient={len(resilient_steps)} steps)"
        )

    details: dict[str, Any] = {
        "rtol": rtol,
        "baseline_timesteps": baseline_steps,
        "resilient_timesteps": resilient_steps,
        "common_timesteps": common_steps,
        "total_common_timesteps": total_steps,
        "matching_timesteps": matching_steps,
        "mismatched_timesteps": len(mismatches),
        # Cap mismatch details at 10 entries to keep the report readable.
        "mismatches": mismatches[:10],
    }

    return passed, score, message, details


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def compare(baseline_path: str, resilient_path: str, **kwargs: Any) -> dict:
    """Parse ExaMiniMD thermo tables and compare physics columns.

    Parameters
    ----------
    baseline_path:
        Path to the baseline ``stdout.txt`` file.
    resilient_path:
        Path to the resilient ``stdout.txt`` file.
    rtol:
        Relative tolerance for floating-point comparison (default: 1e-6).
        Can be passed as a keyword argument.
    **kwargs:
        Additional keyword arguments are ignored.

    Returns
    -------
    dict with keys:
        passed  : bool   – True if all common timestep physics columns match
        score   : float  – fraction of common timesteps with matching physics
        message : str    – human-readable summary
        details : dict   – per-timestep mismatch information
    """
    rtol = float(kwargs.get("rtol", DEFAULT_RTOL))

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

    # Parse thermo tables.
    baseline_thermo = _parse_thermo_table(baseline_text)
    resilient_thermo = _parse_thermo_table(resilient_text)

    passed, score, message, details = _compare_thermo(
        baseline_thermo, resilient_thermo, rtol=rtol
    )

    return {
        "passed": passed,
        "score": score,
        "message": message,
        "details": details,
    }


# ---------------------------------------------------------------------------
# CLI self-test (run directly: python examinimd_comparator.py <f1> <f2>)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <baseline_stdout.txt> <resilient_stdout.txt> [rtol]"
        )
        sys.exit(1)

    _rtol = float(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_RTOL
    result = compare(sys.argv[1], sys.argv[2], rtol=_rtol)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)
