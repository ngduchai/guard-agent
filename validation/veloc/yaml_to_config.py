"""
yaml_to_config.py – Convert app.yaml to the format expected by run_validate.sh.

Usage:
    python -m validation.veloc.yaml_to_config <app_yaml_path> <field>

Fields:
    executable_name   – Binary name extracted from run.cmd
    app_args          – Arguments extracted from run.cmd
    num_procs         – MPI rank count
    comparison_flags  – CLI flags for validate.py comparison settings
    build_cmd         – Build command from app.yaml
    run_cmd           – Full run command (with {mpi_ranks} substituted)
"""

import re
import sys
from pathlib import Path

import yaml


def load_app_yaml(yaml_path: str) -> dict:
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def parse_run_cmd(run_cmd: str, mpi_ranks: int = 4) -> tuple[str, str, str]:
    """Parse a run command into (full_cmd, executable, args).

    Handles formats:
      "mpirun -np {mpi_ranks} ./bin/app -x 10"
      "mpirun --oversubscribe -np {mpi_ranks} ./_build/app args"
      "./_build/Tests/CLZ/3d/Test_CLZ_3d"
      "LD_LIBRARY_PATH=... mpirun -np {mpi_ranks} ./app args"
    """
    # Substitute {mpi_ranks}
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))

    # Strip env var prefixes (FOO=bar ...)
    tokens = cmd.split()
    start = 0
    for i, t in enumerate(tokens):
        if "=" in t and not t.startswith("-"):
            start = i + 1
        else:
            break

    rest = tokens[start:]

    # Skip mpirun and its flags
    exe_idx = 0
    if rest and rest[0] in ("mpirun", "mpiexec", "srun"):
        exe_idx = 1
        while exe_idx < len(rest) and rest[exe_idx].startswith("-"):
            exe_idx += 1
            # Skip the value of flags like -np N, --oversubscribe (no value)
            if exe_idx < len(rest) and not rest[exe_idx].startswith("-"):
                # Check if previous flag takes a value
                prev = rest[exe_idx - 1]
                if prev in ("-np", "-n", "-N", "--num-procs"):
                    exe_idx += 1

    if exe_idx >= len(rest):
        return cmd, run_cmd.split()[-1], ""

    exe = rest[exe_idx]
    args = " ".join(rest[exe_idx + 1 :])
    return cmd, exe, args


def get_comparison_flags(config: dict) -> str:
    """Build validate.py CLI flags from comparison config.

    The app.yaml files use short method names (``numeric``, ``text``)
    while ``validate.py``'s CLI expects hyphenated names
    (``numeric-tolerance``, ``text-diff``).  This function translates
    between the two conventions.
    """
    # Map short app.yaml names → validate.py CLI names
    _METHOD_MAP: dict[str, str] = {
        "numeric": "numeric-tolerance",
        "text": "text-diff",
    }

    comp = config.get("comparison", {})
    raw_method = comp.get("method", "hash")
    method = _METHOD_MAP.get(raw_method, raw_method)
    flags = [f"--comparison-method {method}"]

    tol = comp.get("tolerance")
    if tol is not None and method == "numeric-tolerance":
        flags.append(f"--numeric-atol {tol}")
        flags.append(f"--numeric-rtol {tol}")

    ssim = comp.get("ssim_threshold")
    if ssim is not None:
        flags.append(f"--ssim-threshold {ssim}")

    dataset = comp.get("hdf5_dataset")
    if dataset:
        flags.append(f"--hdf5-dataset {dataset}")

    ignore_patterns = comp.get("ignore_patterns")
    if ignore_patterns:
        patterns_str = " ".join(f'"{p}"' for p in ignore_patterns)
        flags.append(f"--text-ignore-patterns {patterns_str}")

    output_file = comp.get("output_file")
    if output_file:
        flags.append(f"--output-file-name {output_file}")

    return " ".join(flags)


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <app.yaml> <field>", file=sys.stderr)
        sys.exit(1)

    yaml_path = sys.argv[1]
    field = sys.argv[2]

    config = load_app_yaml(yaml_path)
    mpi_ranks = config.get("mpi_ranks", 4)
    run_cmd_raw = config.get("run", {}).get("cmd", "")
    _, exe, args = parse_run_cmd(run_cmd_raw, mpi_ranks)

    if field == "executable_name":
        # Return just the basename for the executable
        print(Path(exe).name)
    elif field == "app_args":
        print(args)
    elif field == "num_procs":
        print(mpi_ranks)
    elif field == "comparison_flags":
        print(get_comparison_flags(config))
    elif field == "build_cmd":
        print(config.get("build", {}).get("cmd", ""))
    elif field == "run_cmd":
        full_cmd = run_cmd_raw.replace("{mpi_ranks}", str(mpi_ranks))
        print(full_cmd)
    elif field == "timeout":
        print(config.get("run", {}).get("timeout", 120))
    else:
        print(f"Unknown field: {field}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
