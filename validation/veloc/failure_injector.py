import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def find_target_rank_pid(parent_pid: int, executable_name: str) -> int | None:
    """
    Best-effort search for a rank process whose command line includes
    executable_name.

    NOTE: Some MPI implementations launch ranks from separate launcher
    daemons or via ssh, and those ranks may not appear as descendants of
    the local mpirun PID. To make failure injection robust across such
    setups, we search the entire process table for commands containing
    the executable name instead of restricting ourselves to the mpirun
    process tree.
    """
    try:
        out = subprocess.check_output(
            ["ps", "-o", "pid,ppid,cmd", "--no-headers"],
            text=True,
        )
    except Exception:
        return None

    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[2]

        # Heuristic filters: avoid killing mpirun itself or obvious non-rank
        # processes such as the injector/python.
        if executable_name in cmd and "mpirun" not in cmd and "python" not in cmd:
            return pid

    return None


def inject_failure_once(parent_pid: int, executable_name: str, max_wait: float) -> bool:
    """
    Try for up to max_wait seconds to kill one rank process.
    Returns True if an injection was performed, False otherwise.
    """
    deadline = time.time() + max_wait
    while time.time() < deadline:
        # If the parent has died, stop trying.
        if not os.path.exists(f"/proc/{parent_pid}"):
            return False

        target = find_target_rank_pid(parent_pid, executable_name)
        if target is not None:
            try:
                os.kill(target, signal.SIGKILL)
                print(f"[injector] killed rank PID {target}", flush=True)
                return True
            except ProcessLookupError:
                # Process disappeared between lookup and kill; retry.
                pass
            except PermissionError:
                print("[injector] permission error while killing rank", flush=True)
                return False

        time.sleep(0.5)

    return False


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inject a single process failure into a running MPI job."
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        required=True,
        help="PID of the mpirun process to monitor",
    )
    parser.add_argument(
        "--executable-name",
        required=True,
        help="Name of the MPI application executable to look for in child commands",
    )
    parser.add_argument(
        "--flag-path",
        required=True,
        help="Path to a file that will be created when injection succeeds",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=10.0,
        help="Seconds to wait before starting to search for a target rank",
    )
    parser.add_argument(
        "--max-wait-seconds",
        type=float,
        default=20.0,
        help="Maximum time to keep trying to inject a failure after delay",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    flag_path = Path(args.flag_path)

    time.sleep(args.delay_seconds)

    injected = inject_failure_once(
        parent_pid=args.parent_pid,
        executable_name=args.executable_name,
        max_wait=args.max_wait_seconds,
    )

    if injected:
        try:
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            flag_path.write_text("injection_success\n", encoding="utf-8")
        except Exception:
            # Even if we cannot write the flag, we still consider the injector done.
            print("[injector] failed to write injection flag", flush=True)
        return 0

    print("[injector] no suitable rank found for failure injection", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

