"""
yaml_to_config.py – CLI shim that emits per-app config fields for run_validate.sh.

Usage:
    python -m validation.veloc.yaml_to_config <app_yaml_path> <field>

When `<app_yaml_path>` points at a vanilla app.yaml under
`tests/apps/vanillas/<APP>/`, the script auto-routes to the unified
single-source-of-truth at `tests/apps/configs/<APP>.yaml` instead of
reading the legacy app.yaml.  This way consumers that already pass an
app.yaml path (run_validate.sh, etc.) automatically pick up the unified
config without any change to the calling code.

Fields:
    executable_name        – binary basename
    ckpt_executable_name   – optional resilient binary basename (usually empty)
    app_args               – validation-size args, space-joined
    num_procs              – MPI rank count
    comparison_flags       – CLI flags for validate.py comparison settings
    build_cmd              – build command
    ckpt_build_cmd         – build command for resilient binary (defaults to build_cmd)
    run_cmd                – full run command (with {mpi_ranks} substituted)
    timeout                – per-run timeout fallback
    app_input_subdir       – cd-prefix subdir (or empty)
    injection_delay        – manual injection-delay override (or empty; consumer derives from baseline)
"""

import re
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
UNIFIED_DIR = REPO_ROOT / "tests" / "apps" / "configs"
LEGACY_VANILLAS = REPO_ROOT / "tests" / "apps" / "vanillas"


def _derive_app_name(yaml_path: str) -> str | None:
    """If yaml_path is a vanilla app.yaml under tests/apps/vanillas/<APP>/,
    return APP. Otherwise None (caller falls back to legacy YAML read)."""
    p = Path(yaml_path).resolve()
    try:
        rel = p.relative_to(LEGACY_VANILLAS)
    except ValueError:
        return None
    # rel = "<APP>/app.yaml"
    if rel.name == "app.yaml" and len(rel.parts) == 2:
        return rel.parts[0]
    return None


def load_app_yaml(yaml_path: str) -> dict:
    """Load config dict.

    Auto-routes vanilla app.yaml paths to the unified config file at
    tests/apps/configs/<APP>.yaml (single source of truth).  Falls back
    to direct YAML load for any other path.
    """
    app = _derive_app_name(yaml_path)
    if app:
        unified = UNIFIED_DIR / f"{app}.yaml"
        if unified.exists():
            return _unified_to_legacy_view(yaml.safe_load(unified.read_text()), app)
    # Fallback: read the YAML as-is (preserves the legacy contract)
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def _unified_to_legacy_view(unified: dict, app: str) -> dict:
    """Project the unified-config schema onto the legacy app.yaml schema so
    downstream code (parse_run_cmd, get_comparison_flags, main()) keeps
    working unchanged.

    Mapping:
      unified.executable + unified.input_subdir + sizes.validation.app_args
        → legacy.run.cmd  (synthesized as
                           [cd <subdir> && ] mpirun -np {mpi_ranks} <exe> <args>)
      unified.build.cmd            → legacy.build.cmd
      unified.mpi_ranks            → legacy.mpi_ranks
      unified.comparison           → legacy.comparison
      unified.timeout_fallback_s   → legacy.run.timeout
      unified.category, language, description, name → mirror as-is
    """
    val_args = (unified.get("sizes", {}).get("validation", {}) or {}).get("app_args", [])
    if val_args is None:
        val_args = []
    args_str = " ".join(str(a) for a in val_args)
    exe = unified.get("executable", "")
    subdir = unified.get("input_subdir")
    if subdir:
        run_cmd = f"cd {subdir} && mpirun -np {{mpi_ranks}} {exe} {args_str}".strip()
    else:
        run_cmd = f"mpirun -np {{mpi_ranks}} {exe} {args_str}".strip()
    return {
        "name": unified.get("name", app),
        "category": unified.get("category", ""),
        "language": unified.get("language", ""),
        "description": unified.get("description", ""),
        "mpi_ranks": int(unified.get("mpi_ranks", 4)),
        "build": {
            "system": unified.get("build", {}).get("system", "make"),
            "cmd": unified.get("build", {}).get("cmd", ""),
        },
        "run": {
            "cmd": run_cmd,
            "timeout": int(unified.get("timeout_fallback_s", 360)),
        },
        "comparison": unified.get("comparison", {"method": "text"}),
        # Optional fields the loader may peek for; keep them None so the
        # `_read_yaml` callers gracefully default.
        "ckpt_executable_name": unified.get("ckpt_executable", ""),
        "ckpt_build": unified.get("ckpt_build", {}),
        "app_input_subdir": subdir,
        "injection_delay": unified.get("injection_delay", ""),
    }


def parse_run_cmd(run_cmd: str, mpi_ranks: int = 4) -> tuple[str, str, str]:
    """Parse a run command into (full_cmd, executable, args).

    Handles formats:
      "mpirun -np {mpi_ranks} ./bin/app -x 10"
      "mpirun --oversubscribe -np {mpi_ranks} ./_build/app args"
      "./_build/Tests/CLZ/3d/Test_CLZ_3d"
      "LD_LIBRARY_PATH=... mpirun -np {mpi_ranks} ./app args"
      "cd <subdir> && mpirun -np {mpi_ranks} ./app args"
      "cd <subdir> && LD_LIBRARY_PATH=... mpirun -np {mpi_ranks} ./app args"
    """
    # Substitute {mpi_ranks}
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks))

    # Strip leading "cd <subdir> && " prefix.  The subdir itself is recovered
    # via extract_input_subdir() and forwarded as --app-input-subdir; here we
    # only need the post-cd command so executable/args parsing isn't fooled
    # into returning "cd" as the executable.
    cmd_stripped = re.sub(r"^\s*cd\s+\S+\s*&&\s*", "", cmd)

    # Strip env var prefixes (FOO=bar ...)
    tokens = cmd_stripped.split()
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


def extract_input_subdir(run_cmd: str, mpi_ranks: int = 4) -> str | None:
    """Extract the input subdir from a run command's leading ``cd <subdir> &&`` prefix.

    Some apps (HPCG, SPARTA, …) ship their inputs alongside the binary in a
    subdir of the source tree, and their app.yaml encodes that with a
    ``cd <subdir> && mpirun …`` prefix.  Returns the subdir relative to the
    app source root, or None when run.cmd has no ``cd`` prefix.

    Examples:
        "cd bin && mpirun -np 4 ./xhpcg_run --rt=120"          → "bin"
        "cd examples/free && mpirun -np 4 ./spa_mpi -in foo"   → "examples/free"
        "mpirun -np 4 ./bin/CoMD-mpi -x 70"                    → None
    """
    cmd = run_cmd.replace("{mpi_ranks}", str(mpi_ranks)).strip()
    m = re.match(r"^\s*cd\s+(\S+)\s*&&\s*", cmd)
    return m.group(1) if m else None


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
        # Streaming variants pass through unchanged; CLI accepts them
        # directly (validate.py --comparison-method choices include them).
        "streaming-text": "streaming-text",
        "streaming-numeric": "streaming-numeric",
    }

    comp = config.get("comparison", {})
    raw_method = comp.get("method", "hash")
    method = _METHOD_MAP.get(raw_method, raw_method)
    flags = [f"--comparison-method {method}"]

    tol = comp.get("tolerance")
    # Apply tolerance to numeric-tolerance AND streaming-numeric (the
    # streaming variant uses the same numeric tolerance pathway).
    if tol is not None and method in ("numeric-tolerance", "streaming-numeric"):
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

    keep_patterns = comp.get("keep_patterns")
    if keep_patterns:
        patterns_str = " ".join(f'"{p}"' for p in keep_patterns)
        flags.append(f"--text-keep-patterns {patterns_str}")

    strip_patterns = comp.get("strip_patterns")
    if strip_patterns:
        patterns_str = " ".join(f'"{p}"' for p in strip_patterns)
        flags.append(f"--text-strip-patterns {patterns_str}")

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
    elif field == "ckpt_build_cmd":
        ckpt = config.get("ckpt_build")
        if ckpt:
            print(ckpt.get("cmd", ""))
        else:
            # Fall back to vanilla build command
            print(config.get("build", {}).get("cmd", ""))
    elif field == "run_cmd":
        full_cmd = run_cmd_raw.replace("{mpi_ranks}", str(mpi_ranks))
        print(full_cmd)
    elif field == "timeout":
        print(config.get("run", {}).get("timeout", 120))
    elif field == "ckpt_executable_name":
        # Optional in app.yaml; empty when the resilient binary uses the same
        # name as the vanilla one.
        print(config.get("ckpt_executable_name", ""))
    elif field == "app_input_subdir":
        # Optional explicit override; otherwise infer from the leading
        # "cd <subdir> &&" prefix in run.cmd.
        explicit = config.get("app_input_subdir")
        if explicit:
            print(explicit)
        else:
            sub = extract_input_subdir(run_cmd_raw, mpi_ranks)
            print(sub or "")
    elif field == "injection_delay":
        # Optional per-app override of the default adaptive injection delay.
        print(config.get("injection_delay", ""))
    else:
        print(f"Unknown field: {field}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
