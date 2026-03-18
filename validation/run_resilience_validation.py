import argparse
import hashlib
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from .run_validation import configure_and_build, run_with_retries, start_mpi_run


def _load_hdf5_array(path: Path, dataset: str):
    """Load a numeric dataset from an HDF5 file. Requires h5py."""
    try:
        import h5py
    except ImportError:
        raise RuntimeError(
            "SSIM comparison requires h5py. Install with: pip install h5py"
        ) from None
    with h5py.File(path, "r") as f:
        if dataset not in f:
            available = list(f.keys())
            raise KeyError(
                f"Dataset {dataset!r} not found in {path}. "
                f"Available: {available}"
            )
        return f[dataset][...]


def _compute_ssim(path1: Path, path2: Path, dataset: str) -> float:
    """Compute Structural Similarity Index between two HDF5 datasets. Requires scikit-image."""
    try:
        from skimage.metrics import structural_similarity
    except ImportError:
        raise RuntimeError(
            "SSIM comparison requires scikit-image. Install with: pip install scikit-image"
        ) from None
    arr1 = _load_hdf5_array(path1, dataset)
    arr2 = _load_hdf5_array(path2, dataset)
    if arr1.shape != arr2.shape:
        raise ValueError(
            f"Shape mismatch: {path1} has {arr1.shape}, {path2} has {arr2.shape}"
        )
    # data_range: max value range for the type; use global max of both arrays
    data_range = max(float(arr1.max() - arr1.min()), float(arr2.max() - arr2.min()), 1.0)
    # Default win_size is 7; use an odd value <= smallest extent
    min_extent = min(arr1.shape)
    win_size = min(7, min_extent)
    if win_size % 2 == 0:
        win_size = max(1, win_size - 1)
    result = structural_similarity(
        arr1, arr2, data_range=data_range, channel_axis=None, win_size=win_size
    )
    value = result[0] if isinstance(result, tuple) else result
    return float(value)


def run_baseline(
    source_dir: Path,
    build_dir: Path,
    output_dir: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
) -> None:
    """Build and run the baseline (non-resilient) application once."""
    configure_and_build(source_dir, build_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stdout_path = output_dir / "stdout_baseline.txt"
    stderr_path = output_dir / "stderr_baseline.txt"

    proc = start_mpi_run(
        build_dir=build_dir,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )
    code = proc.wait()
    if code != 0:
        raise RuntimeError(
            f"Baseline run failed with exit code {code} "
            f"(see {stdout_path} and {stderr_path})"
        )


def file_hash(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute a SHA-256 hash of a file."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _extract_checkpoint_dirs_from_veloc_cfg(cfg_path: Path) -> list[Path]:
    """
    Best-effort parsing of a VeloC config file to find checkpoint/scratch
    directories that should be cleared before validation.
    """
    keys = {"scratch", "persistent"}
    dirs: list[Path] = []

    try:
        text = cfg_path.read_text(encoding="utf-8")
    except OSError:
        return dirs

    for line in text.splitlines():
        # Strip comments
        if "#" in line:
            line = line.split("#", 1)[0]
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip().lower()
        if key not in keys:
            continue
        for token in val.split(","):
            token = token.strip()
            if not token:
                continue
            p = Path(token)
            # Be conservative: only handle absolute paths.
            if p.is_absolute():
                dirs.append(p)
    return dirs


def _clear_checkpoint_dirs(dirs: list[Path]) -> None:
    """
    Remove all contents from the given directories, without deleting the
    directories themselves.
    """
    for d in dirs:
        try:
            if not d.exists() or not d.is_dir():
                continue
            # Extra safety: avoid obviously dangerous paths.
            if str(d) in {"/", ""}:
                continue
            for child in d.iterdir():
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    try:
                        child.unlink()
                    except OSError:
                        pass
        except OSError:
            # Best-effort cleanup; ignore individual failures.
            pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a baseline (non-resilient) MPI application and a resilient "
            "MPI application with failure injection, then compare their outputs."
        )
    )

    # Baseline app config
    parser.add_argument(
        "--baseline-source-dir",
        required=True,
        help="Source directory for the baseline application (with CMakeLists.txt)",
    )
    parser.add_argument(
        "--baseline-build-dir",
        required=True,
        help="Build directory for the baseline application",
    )
    parser.add_argument(
        "--baseline-executable-name",
        required=True,
        help="Executable name for the baseline application",
    )
    parser.add_argument(
        "--baseline-args",
        default="",
        help=(
            "Command-line arguments for the baseline application, "
            "given as a single shell-style string (parsed with shlex.split)."
        ),
    )

    # Resilient app config
    parser.add_argument(
        "--resilient-source-dir",
        required=True,
        help="Source directory for the resilient application (with CMakeLists.txt)",
    )
    parser.add_argument(
        "--resilient-build-dir",
        required=True,
        help="Build directory for the resilient application",
    )
    parser.add_argument(
        "--resilient-executable-name",
        required=True,
        help="Executable name for the resilient application",
    )
    parser.add_argument(
        "--resilient-args",
        default="",
        help=(
            "Command-line arguments for the resilient application, "
            "given as a single shell-style string (parsed with shlex.split)."
        ),
    )

    # Common settings
    parser.add_argument(
        "--num-procs",
        type=int,
        default=4,
        help="Number of MPI processes (ranks) to launch with mpirun",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help=(
            "Directory where baseline and resilient outputs are stored. "
            "Subdirectories 'baseline' and 'resilient' are created inside."
        ),
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=10,
        help="Maximum number of resilient attempts before giving up",
    )
    parser.add_argument(
        "--injection-delay",
        type=float,
        default=5.0,
        help="Seconds to wait before injecting a failure into the MPI run",
    )
    parser.add_argument(
        "--output-file-name",
        default="recon.h5",
        help=(
            "Name of the output file produced by both applications that should "
            "be compared for equality (default: recon.h5). The file is expected "
            "to be created in each app's run/output directory."
        ),
    )
    parser.add_argument(
        "--install-resilient",
        action="store_true",
        help=(
            "If set, run `cmake --install` for the resilient build (with the "
            "install prefix set to the build directory). Enable this when the "
            "resilient example requires installed runtime config like veloc.cfg."
        ),
    )
    parser.add_argument(
        "--veloc-config-name",
        default="veloc.cfg",
        help=(
            "Filename of the VeloC configuration file for the resilient "
            "application (default: veloc.cfg). If found, the checkpoint/"
            "scratch directories it references will be cleared before "
            "validation."
        ),
    )
    parser.add_argument(
        "--comparison-method",
        choices=("hash", "ssim"),
        default="ssim",
        help=(
            "How to compare baseline and resilient output files: "
            "'hash' = byte-identical (SHA-256); "
            "'ssim' = Structural Similarity Index on HDF5 dataset (default)."
        ),
    )
    parser.add_argument(
        "--ssim-threshold",
        type=float,
        default=0.9999,
        help="Minimum SSIM value for validation to pass (default: 0.9999). Used only if --comparison-method=ssim.",
    )
    parser.add_argument(
        "--hdf5-dataset",
        default="data",
        help=(
            "HDF5 dataset name or path to compare when using SSIM "
            "(default: data). Example: 'data' or '/data'."
        ),
    )

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)

    baseline_source = Path(args.baseline_source_dir).resolve()
    baseline_build = Path(args.baseline_build_dir).resolve()
    resilient_source = Path(args.resilient_source_dir).resolve()
    resilient_build = Path(args.resilient_build_dir).resolve()
    output_root = Path(args.output_dir).resolve()

    baseline_args = shlex.split(args.baseline_args)
    resilient_args = shlex.split(args.resilient_args)

    baseline_out_dir = output_root / "baseline"
    resilient_out_dir = output_root / "resilient"

    # Clean per-run output directories to avoid confusion.
    for d in (baseline_out_dir, resilient_out_dir):
        if d.exists():
            shutil.rmtree(d)

    print("[resilience-validation] running baseline application...", flush=True)
    run_baseline(
        source_dir=baseline_source,
        build_dir=baseline_build,
        output_dir=baseline_out_dir,
        executable_name=args.baseline_executable_name,
        num_procs=args.num_procs,
        app_args=baseline_args,
    )

    # For the resilient application, ensure checkpoint/scratch directories
    # referenced in its VeloC config are empty so the run starts from a
    # clean state.
    cfg_candidates = [
        resilient_build / args.veloc_config_name,
        resilient_source / args.veloc_config_name,
    ]
    checkpoint_dirs: list[Path] = []
    for cfg in cfg_candidates:
        if cfg.exists():
            checkpoint_dirs = _extract_checkpoint_dirs_from_veloc_cfg(cfg)
            if checkpoint_dirs:
                print(
                    "[resilience-validation] clearing VeloC checkpoint/scratch "
                    "directories before resilient run:",
                    flush=True,
                )
                for d in checkpoint_dirs:
                    print(f"  - {d}", flush=True)
                _clear_checkpoint_dirs(checkpoint_dirs)
            break

    print(
        "[resilience-validation] running resilient application with "
        "failure injection and retries...",
        flush=True,
    )
    run_with_retries(
        source_dir=resilient_source,
        build_dir=resilient_build,
        output_dir=resilient_out_dir,
        executable_name=args.resilient_executable_name,
        num_procs=args.num_procs,
        app_args=resilient_args,
        max_attempts=args.max_attempts,
        injection_delay=args.injection_delay,
        run_install=args.install_resilient,
        success_output_filename=args.output_file_name,
    )

    # Keep all validation artifacts under output_root; do not assume the baseline
    # writes outputs into its build directory.
    baseline_output_file = baseline_out_dir / args.output_file_name
    resilient_output_file = resilient_out_dir / args.output_file_name

    print(f"  baseline:  {baseline_output_file}", flush=True)
    print(f"  resilient: {resilient_output_file}", flush=True)

    if args.comparison_method == "ssim":
        print(
            "[resilience-validation] comparing outputs with SSIM "
            f"(dataset={args.hdf5_dataset!r}, threshold={args.ssim_threshold})",
            flush=True,
        )
        ssim_value = _compute_ssim(
            baseline_output_file,
            resilient_output_file,
            args.hdf5_dataset,
        )
        print(f"[resilience-validation] SSIM = {ssim_value:.6f}", flush=True)
        identical = ssim_value >= args.ssim_threshold
        if identical:
            print(
                f"[resilience-validation] SUCCESS: SSIM {ssim_value:.6f} >= "
                f"threshold {args.ssim_threshold}.",
                flush=True,
            )
            return 0
        print(
            f"[resilience-validation] FAILURE: SSIM {ssim_value:.6f} < "
            f"threshold {args.ssim_threshold}.",
            flush=True,
        )
        return 1

    # Hash comparison
    print(
        "[resilience-validation] comparing outputs with SHA-256 hash",
        flush=True,
    )
    baseline_hash = file_hash(baseline_output_file)
    resilient_hash = file_hash(resilient_output_file)
    print(f"[resilience-validation] baseline  hash: {baseline_hash}", flush=True)
    print(f"[resilience-validation] resilient hash: {resilient_hash}", flush=True)
    identical = baseline_hash == resilient_hash
    if identical:
        print(
            "[resilience-validation] SUCCESS: baseline and resilient outputs are identical.",
            flush=True,
        )
        return 0
    print(
        "[resilience-validation] FAILURE: baseline and resilient outputs differ.",
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

