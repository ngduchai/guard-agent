"""Per-app baseline-metadata collector.

Runs the failure-free baseline of an application's vanilla source three times
(warmup + 2 measurement passes), records the MIN of the two measurement
elapsed times, and writes the result to a per-app cache directory in the
format ``validate.py``'s existing ``--ground-truth-dir`` flag already
understands.

The cache directory layout is::

    build/baseline_cache/<APP>/
    ├── ground_truth_meta.json   # primary cache file (validate.py reads this)
    ├── stdout.txt               # baseline stdout (comparator reads this)
    ├── stderr.txt               # baseline stderr
    ├── _warmup/                 # discarded warmup artifacts (diagnostic only)
    ├── _pass2/                  # second measurement artifacts
    ├── _build/                  # incremental build dir
    └── .lock                    # fcntl flock sentinel

On a cache hit, ``collect()`` validates the key + source-tree mtime and
returns without re-running.  On a miss, it acquires an exclusive flock,
re-checks the cache (in case a concurrent process just populated it), then
runs the three baseline passes and atomically writes the meta file.

The cache key is a deterministic SHA-256 hash of seven fields that, together,
uniquely determine a baseline run::

    1. original_src           — vanilla source path
    2. original_build_cmd     — shell string (post-resolved, no @file)
    3. executable_name        — e.g. "CoMD-mpi"
    4. num_procs              — MPI rank count
    5. app_args               — list of CLI args (order-preserved)
    6. app_input_subdir       — optional subdir for in-place runs
    7. veloc_config_name      — usually "veloc.cfg"

Plus a separate freshness check on ``vanilla_src_max_mtime`` so a developer
touching a ``.c`` file under vanilla without changing app.yaml invalidates the
cache automatically.

CLI:

    # --app mode (preferred): reads app.yaml the same way run_validate.sh does
    python -m validation.veloc.collect_baseline --app CoMD

    # explicit mode: programmatic invocation from validate.py
    python -m validation.veloc.collect_baseline /path/to/vanilla \\
        --executable-name CoMD-mpi --num-procs 4 \\
        --original-args "-x 20 -y 20 -z 20"

Exit codes: 0 (cache valid: hit or freshly populated), 2 (cache miss when
``--check-only``), 1 (collection failed).
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import shlex
import shutil
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .runner import ValidationError, run_baseline
from .validate import _resolve_build_cmd


SCHEMA_VERSION = 1
COLLECTOR_VERSION = 1
META_FILENAME = "ground_truth_meta.json"
LOCK_FILENAME = ".lock"

# When walking the vanilla source for mtime, ignore these dirs / suffixes
# (they're build artefacts or VCS metadata, not source) and skip files larger
# than the size cap (almost always binary blobs / large test inputs).
_MTIME_SKIP_DIRS = {".git", ".svn", "__pycache__", "build", "_build"}
_MTIME_SKIP_SUFFIXES = {".o", ".a", ".so", ".pyc"}
_MTIME_MAX_FILE_BYTES = 50 * 1024 * 1024


class CacheMiss(Exception):
    """Raised by ``collect(check_only=True)`` when the cache is missing or stale."""


# ---------------------------------------------------------------------------
# Cache key + freshness
# ---------------------------------------------------------------------------


def _normalize_cache_key(
    *,
    original_src: Path,
    original_build_cmd: str | None,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    app_input_subdir: str | None,
    veloc_config_name: str,
) -> dict:
    """Produce the canonical cache-key dict used for hashing + display.

    Normalizations are deterministic and stable across runs / hosts (modulo
    absolute path which IS host-specific by design).  ``app_args`` order is
    preserved because it's semantic (e.g. ``-x 70 -y 70 -z 18`` differs from
    ``-y 70 -x 70 -z 18`` for some apps).
    """
    if num_procs is None:
        raise ValueError("num_procs is required")
    return {
        "original_src": str(Path(original_src).resolve()),
        "original_build_cmd": (original_build_cmd or "").strip(),
        "executable_name": (executable_name or "").strip(),
        "num_procs": int(num_procs),
        "app_args": list(app_args or []),
        "app_input_subdir": (
            None
            if app_input_subdir in (None, "")
            else app_input_subdir.strip()
        ),
        "veloc_config_name": (veloc_config_name or "veloc.cfg").strip(),
    }


def _compute_cache_key_hash(key: dict) -> str:
    canonical = json.dumps(key, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def _compute_vanilla_max_mtime(src: Path) -> tuple[float, int]:
    """Walk the vanilla source tree; return (max_mtime, file_count).

    Skips dirs in ``_MTIME_SKIP_DIRS``, suffixes in ``_MTIME_SKIP_SUFFIXES``,
    and files larger than ``_MTIME_MAX_FILE_BYTES``.  This focuses the freshness
    check on actual source code rather than build artefacts or large test data
    blobs that would otherwise trigger spurious invalidations after every run.
    """
    max_mtime = 0.0
    count = 0
    for path in src.rglob("*"):
        try:
            if not path.is_file():
                continue
        except OSError:
            continue
        if any(part in _MTIME_SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in _MTIME_SKIP_SUFFIXES:
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        if st.st_size > _MTIME_MAX_FILE_BYTES:
            continue
        if st.st_mtime > max_mtime:
            max_mtime = st.st_mtime
        count += 1
    return max_mtime, count


def _is_cache_valid(
    cache_dir: Path,
    expected_key_hash: str,
    expected_max_mtime: float,
) -> tuple[bool, str]:
    """Return ``(valid, reason)``.  ``reason`` is empty on hit."""
    meta_path = cache_dir / META_FILENAME
    if not meta_path.exists():
        return False, "no ground_truth_meta.json"
    try:
        meta = json.loads(meta_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return False, f"meta unreadable: {exc}"
    if meta.get("schema_version") != SCHEMA_VERSION:
        return False, (
            f"schema_version {meta.get('schema_version')} != "
            f"expected {SCHEMA_VERSION}"
        )
    if meta.get("cache_key_hash") != expected_key_hash:
        return False, "cache_key_hash mismatch (key changed)"
    cached_mtime = float(meta.get("vanilla_src_max_mtime", 0.0))
    if expected_max_mtime > cached_mtime + 0.5:
        # 0.5s slop guards against filesystem-mtime quantization on coarse
        # filesystems; the typical change-then-rerun scenario produces a
        # much larger delta than this.
        return False, (
            f"vanilla_src_max_mtime {expected_max_mtime:.3f} > "
            f"cached {cached_mtime:.3f} (source touched)"
        )
    # Sanity: the file the comparator will read MUST exist.
    if not (cache_dir / "stdout.txt").exists():
        return False, "stdout.txt missing"
    return True, ""


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _atomic_write_meta(cache_dir: Path, meta: dict) -> None:
    """Write the meta file via tmp+rename so we never leave a partial file."""
    tmp_path = cache_dir / (META_FILENAME + ".tmp")
    tmp_path.write_text(json.dumps(meta, indent=2, sort_keys=False))
    tmp_path.replace(cache_dir / META_FILENAME)


def _promote_pass2_outputs(pass2_dir: Path, cache_dir: Path) -> None:
    """Copy stdout.txt/stderr.txt + any other files in pass2/ that have
    siblings in cache_dir, overwriting cache_dir's versions.

    Used when pass2's elapsed time was lower than pass1's, so the cached
    timing self-consistently corresponds to the cached output files.  Both
    passes are deterministic so file content is functionally identical;
    this is purely about "the cached number reflects the cached output".
    """
    for src in pass2_dir.iterdir():
        if not src.is_file():
            continue
        dst = cache_dir / src.name
        # Don't clobber cache_dir's lock or meta file
        if dst.name in (META_FILENAME, META_FILENAME + ".tmp", LOCK_FILENAME):
            continue
        try:
            shutil.copy2(src, dst)
        except OSError:
            # Non-fatal: if a sibling can't be copied we still have cache_dir's
            # pass1 output.  Note in stderr but don't abort.
            print(
                f"[collect_baseline] warning: failed to promote {src} → {dst}",
                file=sys.stderr,
            )


def _run_baseline_or_raise(label: str, **kwargs) -> "RunResult":
    """Wrap ``run_baseline()`` so its expected ``ValidationError`` exits cleanly
    rather than dumping a traceback.
    """
    try:
        return run_baseline(**kwargs)
    except ValidationError as exc:
        raise RuntimeError(
            f"baseline {label} pass failed: {exc}"
        ) from exc


def _do_collection(
    *,
    original_src: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    original_build_cmd: str | None,
    app_input_subdir: str | None,
    veloc_config_name: str,
    cache_dir: Path,
    cache_key: dict,
    cache_key_hash: str,
    vanilla_src_max_mtime: float,
    vanilla_src_file_count: int,
) -> dict:
    """Run warmup + 2 measurement passes; write meta atomically.  Return meta dict.
    """
    warmup_dir = cache_dir / "_warmup"
    pass2_dir = cache_dir / "_pass2"
    build_dir = cache_dir / "_build"

    # Pass 1 writes DIRECTLY into cache_dir so its stdout.txt lands at the
    # path validate.py expects (baseline_out / output_file_name).  Pass 2
    # writes into _pass2/ so its outputs are available if it beats pass 1.
    print(
        f"[collect_baseline] warmup pass (timing discarded; "
        f"build_dir={build_dir.name})...",
        flush=True,
    )
    warmup_res = _run_baseline_or_raise(
        "warmup",
        source_dir=original_src,
        build_dir=build_dir,
        output_dir=warmup_dir,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        build_cmd=original_build_cmd,
        app_input_subdir=app_input_subdir,
    )
    print(
        f"[collect_baseline] warmup elapsed {warmup_res.elapsed_s:.1f}s",
        flush=True,
    )

    print("[collect_baseline] measurement pass 1 of 2...", flush=True)
    res1 = _run_baseline_or_raise(
        "pass-1",
        source_dir=original_src,
        build_dir=build_dir,
        output_dir=cache_dir,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        build_cmd=original_build_cmd,
        app_input_subdir=app_input_subdir,
    )
    print(
        f"[collect_baseline] pass-1 elapsed {res1.elapsed_s:.1f}s",
        flush=True,
    )

    print("[collect_baseline] measurement pass 2 of 2...", flush=True)
    res2 = _run_baseline_or_raise(
        "pass-2",
        source_dir=original_src,
        build_dir=build_dir,
        output_dir=pass2_dir,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        build_cmd=original_build_cmd,
        app_input_subdir=app_input_subdir,
    )
    print(
        f"[collect_baseline] pass-2 elapsed {res2.elapsed_s:.1f}s",
        flush=True,
    )

    elapsed_s = min(res1.elapsed_s, res2.elapsed_s)
    if res2.elapsed_s < res1.elapsed_s:
        # Promote pass-2's outputs into cache_dir so the cached timing
        # corresponds to the cached output files.  Files are functionally
        # identical between deterministic passes, but this keeps the cache
        # internally self-consistent.
        _promote_pass2_outputs(pass2_dir, cache_dir)

    print(
        f"[collect_baseline] selected MIN={elapsed_s:.1f}s "
        f"(pass1={res1.elapsed_s:.1f}s, pass2={res2.elapsed_s:.1f}s)",
        flush=True,
    )

    meta = {
        "schema_version": SCHEMA_VERSION,
        # validate.py:894 reads this exact key — DO NOT rename.
        "elapsed_s": elapsed_s,
        "baseline_pass1_elapsed_s": res1.elapsed_s,
        "baseline_pass2_elapsed_s": res2.elapsed_s,
        "baseline_warmup_elapsed_s": warmup_res.elapsed_s,
        "cache_key": cache_key,
        "cache_key_hash": cache_key_hash,
        "vanilla_src_max_mtime": vanilla_src_max_mtime,
        "vanilla_src_file_count": vanilla_src_file_count,
        "cached_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collector_host": socket.gethostname(),
        "collector_version": COLLECTOR_VERSION,
    }
    _atomic_write_meta(cache_dir, meta)
    return meta


def collect(
    *,
    original_src: Path,
    executable_name: str,
    num_procs: int,
    app_args: list[str],
    original_build_cmd: str | None,
    app_input_subdir: str | None,
    veloc_config_name: str,
    cache_dir: Path,
    force: bool = False,
    check_only: bool = False,
) -> tuple[Path, dict, bool]:
    """Public entry point.  Returns ``(cache_dir, meta, was_hit)``.

    On a cache hit (and ``not force``): returns ``was_hit=True`` without
    re-running.

    On a miss / stale / forced: acquires an exclusive flock, re-checks
    (handling concurrent populators), then runs warmup + 2 measurement
    passes, writes the meta file atomically, returns ``was_hit=False``.

    With ``check_only=True``: raises ``CacheMiss`` if the cache is not valid.
    Never invokes ``run_baseline()``.
    """
    original_src = Path(original_src).resolve()
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = _normalize_cache_key(
        original_src=original_src,
        original_build_cmd=original_build_cmd,
        executable_name=executable_name,
        num_procs=num_procs,
        app_args=app_args,
        app_input_subdir=app_input_subdir,
        veloc_config_name=veloc_config_name,
    )
    cache_key_hash = _compute_cache_key_hash(cache_key)
    max_mtime, file_count = _compute_vanilla_max_mtime(original_src)

    # Fast path: no lock needed for read-only validity check.
    if not force:
        valid, reason = _is_cache_valid(cache_dir, cache_key_hash, max_mtime)
        if valid:
            meta = json.loads((cache_dir / META_FILENAME).read_text())
            print(
                f"[collect_baseline] cache HIT for {original_src.name} "
                f"(elapsed_s={meta['elapsed_s']:.1f}s, "
                f"cached_at={meta.get('cached_at','?')})",
                flush=True,
            )
            return cache_dir, meta, True
        print(
            f"[collect_baseline] cache MISS for {original_src.name}: {reason}",
            flush=True,
        )

    if check_only:
        raise CacheMiss(f"cache invalid: {reason if not force else 'forced'}")

    # Slow path: acquire lock and re-check (a concurrent populator may have
    # finished while we were doing the read-only check above).
    lock_path = cache_dir / LOCK_FILENAME
    with open(lock_path, "w") as lock_fh:
        try:
            fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(
                f"[collect_baseline] another collector holds {lock_path}; "
                "waiting...",
                flush=True,
            )
            fcntl.flock(lock_fh, fcntl.LOCK_EX)
            # Re-check: the other collector may have just populated the cache.
            if not force:
                valid, reason = _is_cache_valid(
                    cache_dir, cache_key_hash, max_mtime
                )
                if valid:
                    meta = json.loads(
                        (cache_dir / META_FILENAME).read_text()
                    )
                    print(
                        f"[collect_baseline] concurrent populator finished; "
                        f"cache HIT (elapsed_s={meta['elapsed_s']:.1f}s)",
                        flush=True,
                    )
                    return cache_dir, meta, True

        meta = _do_collection(
            original_src=original_src,
            executable_name=executable_name,
            num_procs=num_procs,
            app_args=app_args,
            original_build_cmd=original_build_cmd,
            app_input_subdir=app_input_subdir,
            veloc_config_name=veloc_config_name,
            cache_dir=cache_dir,
            cache_key=cache_key,
            cache_key_hash=cache_key_hash,
            vanilla_src_max_mtime=max_mtime,
            vanilla_src_file_count=file_count,
        )
        return cache_dir, meta, False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _resolve_app_yaml(app_name: str, repo_root: Path) -> Path:
    """Replicate the lookup order from run_validate.sh: vanillas → tests →
    tests_baseline.  Raise ``FileNotFoundError`` if nothing matches.
    """
    candidates = [
        repo_root / "tests" / "apps" / "vanillas" / app_name / "app.yaml",
        repo_root / "build" / "tests" / app_name / "app.yaml",
        repo_root / "build" / "tests_baseline" / app_name / "app.yaml",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        f"no app.yaml found for {app_name!r} in any of: "
        + ", ".join(str(c) for c in candidates)
    )


def _resolve_inputs_from_app_yaml(app_name: str, repo_root: Path) -> dict:
    """Extract the seven cache-key fields + the vanilla source path from app.yaml.

    Mirrors the lookup logic in ``run_validate.sh`` and the parsing helpers in
    ``yaml_to_config.py``.
    """
    from . import yaml_to_config

    app_yaml = _resolve_app_yaml(app_name, repo_root)
    cfg = yaml_to_config.load_app_yaml(str(app_yaml))

    num_procs = int(cfg.get("mpi_ranks", 4))
    run_cmd = cfg.get("run", {}).get("cmd", "")
    if not run_cmd:
        raise ValueError(f"app.yaml {app_yaml} missing run.cmd")
    _, exe_with_path, args_str = yaml_to_config.parse_run_cmd(
        run_cmd, mpi_ranks=num_procs
    )
    # Mirror yaml_to_config.py:175 — strip the path prefix so the executable
    # name matches what run_validate.sh / validate.py / runner.py expect.
    executable_name = Path(exe_with_path).name
    app_args = shlex.split(args_str)

    build = cfg.get("build", {})
    original_build_cmd = build.get("cmd")

    # vanilla source is the dir containing the resolved app.yaml.
    original_src = app_yaml.parent

    # app_input_subdir is implicit in the run.cmd (e.g. "cd subdir && mpirun...").
    # Reuse yaml_to_config's parser so the result matches what run_validate.sh
    # extracts and what validate.py is given via --app-input-subdir.
    subdir = yaml_to_config.extract_input_subdir(run_cmd, mpi_ranks=num_procs)
    app_input_subdir = subdir if subdir else None

    return {
        "original_src": original_src,
        "executable_name": executable_name,
        "num_procs": num_procs,
        "app_args": app_args,
        "original_build_cmd": original_build_cmd,
        "app_input_subdir": app_input_subdir,
        "veloc_config_name": "veloc.cfg",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="collect_baseline",
        description=(
            "Collect per-app baseline-timing metadata into "
            "build/baseline_cache/<APP>/.  Used by validate.py's auto-detect "
            "block to skip the repeated 3-pass baseline measurement on "
            "every iter of the LLM iterative loop."
        ),
    )
    parser.add_argument(
        "original_codebase",
        nargs="?",
        default=None,
        help=(
            "Path to the vanilla source dir (explicit mode).  Mutually "
            "exclusive with --app."
        ),
    )
    parser.add_argument(
        "--app",
        default=None,
        help=(
            "App name (preferred mode).  Resolves all other inputs from "
            "tests/apps/vanillas/<APP>/app.yaml the same way run_validate.sh "
            "does.  Mutually exclusive with the positional argument."
        ),
    )
    parser.add_argument("--executable-name", default=None)
    parser.add_argument("--num-procs", type=int, default=4)
    parser.add_argument(
        "--original-args",
        default="",
        help=(
            "Shell-quoted CLI arguments passed to the application binary "
            "(e.g. \"-x 20 -y 20 -z 20\")."
        ),
    )
    parser.add_argument(
        "--original-build-cmd",
        default=None,
        help=(
            "Build command shell string.  Supports @file indirection: a "
            "value starting with '@' is treated as a path whose contents "
            "are the actual command (matches run_validate.sh's convention)."
        ),
    )
    parser.add_argument("--app-input-subdir", default=None)
    parser.add_argument("--veloc-config-name", default="veloc.cfg")
    parser.add_argument(
        "--cache-root",
        default=None,
        help=(
            "Root directory under which per-app cache dirs are created.  "
            "Default: <repo>/build/baseline_cache.  Ignored if --cache-dir "
            "is set."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help=(
            "Explicit cache directory path.  When set, --cache-root and "
            "--app-name-derived layout are bypassed."
        ),
    )
    parser.add_argument("--force", action="store_true",
                        help="Ignore an existing valid cache and re-collect.")
    parser.add_argument(
        "--check-only", action="store_true",
        help=(
            "Exit 0 if cache is valid, exit 2 if missing/stale.  Never "
            "runs the baseline."
        ),
    )

    args = parser.parse_args(argv)

    if args.app and args.original_codebase:
        parser.error("specify either --app OR <original_codebase>, not both")
    if not args.app and not args.original_codebase:
        parser.error("specify --app or <original_codebase>")

    repo_root = Path(__file__).resolve().parents[2]

    # Resolve all collector inputs from either --app mode (read app.yaml) or
    # explicit mode (use CLI flags).
    if args.app:
        try:
            resolved = _resolve_inputs_from_app_yaml(args.app, repo_root)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[collect_baseline] error: {exc}", file=sys.stderr)
            return 1
        app_name = args.app
    else:
        original_src = Path(args.original_codebase).resolve()
        if not original_src.exists():
            print(
                f"[collect_baseline] error: original codebase path does not "
                f"exist: {original_src}",
                file=sys.stderr,
            )
            return 1
        if not args.executable_name:
            print(
                "[collect_baseline] error: --executable-name is required in "
                "explicit mode",
                file=sys.stderr,
            )
            return 1
        resolved = {
            "original_src": original_src,
            "executable_name": args.executable_name,
            "num_procs": args.num_procs,
            "app_args": shlex.split(args.original_args or ""),
            "original_build_cmd": _resolve_build_cmd(args.original_build_cmd),
            "app_input_subdir": args.app_input_subdir,
            "veloc_config_name": args.veloc_config_name,
        }
        app_name = original_src.name

    # Resolve cache directory.
    if args.cache_dir:
        cache_dir = Path(args.cache_dir).resolve()
    else:
        cache_root = (
            Path(args.cache_root).resolve()
            if args.cache_root
            else repo_root / "build" / "baseline_cache"
        )
        cache_dir = cache_root / app_name

    # Run.
    try:
        _, meta, was_hit = collect(
            **resolved,
            cache_dir=cache_dir,
            force=args.force,
            check_only=args.check_only,
        )
    except CacheMiss as exc:
        # Only raised when --check-only is set.
        print(f"[collect_baseline] cache miss: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(
            f"[collect_baseline] collection failed: "
            f"{type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        f"[collect_baseline] {'HIT' if was_hit else 'POPULATED'}: "
        f"{cache_dir} (elapsed_s={meta['elapsed_s']:.1f}s)",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
