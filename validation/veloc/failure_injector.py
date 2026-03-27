"""
failure_injector.py – Inject process failures into a running MPI job.

Supports **multi-node** MPI executions where rank processes are spread
across several nodes.  A target node is chosen at random, then a rank
process on that node is located (via ``ssh`` + ``ps``) and killed with
``SIGKILL``.

Node discovery (in priority order):
  1. ``--nodes node1,node2,...``  – explicit comma-separated list.
  2. ``--hostfile /path/to/file`` – one hostname per line (blank lines and
     ``#``-comments are skipped; ``slots=`` suffixes are stripped).
  3. Environment variables ``SLURM_JOB_NODELIST`` / ``PBS_NODEFILE`` /
     ``COBALT_NODEFILE``.
  4. Fallback to **localhost** – fully backward-compatible with the
     previous single-node implementation.

When the selected node is the local host the injector kills the process
directly (no SSH), preserving the original single-node behaviour.
"""

from __future__ import annotations

import argparse
import os
import random
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Hostname helpers
# ---------------------------------------------------------------------------

_LOCAL_NAMES: set[str] | None = None


def _local_hostnames() -> set[str]:
    """Return a set of names / IPs that refer to the current machine."""
    global _LOCAL_NAMES
    if _LOCAL_NAMES is not None:
        return _LOCAL_NAMES
    names: set[str] = {"localhost", "127.0.0.1", "::1"}
    try:
        hn = socket.gethostname()
        names.add(hn)
        names.add(socket.getfqdn(hn))
        # Also add the short hostname (before the first dot).
        if "." in hn:
            names.add(hn.split(".")[0])
    except OSError:
        pass
    _LOCAL_NAMES = names
    return _LOCAL_NAMES


def _is_local(host: str) -> bool:
    """Return True if *host* refers to the machine running this script."""
    return host in _local_hostnames()


# ---------------------------------------------------------------------------
# Node-list resolution
# ---------------------------------------------------------------------------

def _expand_slurm_nodelist(nodelist: str) -> list[str]:
    """Expand a SLURM compact nodelist like ``node[01-03,05]`` into individual
    hostnames.

    Falls back to ``scontrol show hostnames`` if available, otherwise uses a
    simple regex-based expander that handles the most common bracket notation.
    """
    # Try scontrol first (most reliable).
    try:
        out = subprocess.check_output(
            ["scontrol", "show", "hostnames", nodelist],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        hosts = [h.strip() for h in out.splitlines() if h.strip()]
        if hosts:
            return hosts
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Simple regex expander for ``prefix[01-03,05]`` patterns.
    m = re.match(r"^([A-Za-z_.\-]*)(\[.+\])$", nodelist)
    if not m:
        # No bracket notation – treat as a single hostname or comma-separated.
        return [h.strip() for h in nodelist.split(",") if h.strip()]

    prefix = m.group(1)
    bracket_body = m.group(2)[1:-1]  # strip surrounding [ ]
    hosts: list[str] = []
    for part in bracket_body.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            width = len(lo)
            for i in range(int(lo), int(hi) + 1):
                hosts.append(f"{prefix}{str(i).zfill(width)}")
        else:
            hosts.append(f"{prefix}{part}")
    return hosts


def _parse_hostfile(path: str) -> list[str]:
    """Parse a hostfile (one host per line, optional ``slots=N`` suffix)."""
    hosts: list[str] = []
    try:
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Strip optional ``slots=N`` or ``max_slots=N`` suffixes.
                host = re.split(r"\s+", line)[0]
                if host and host not in hosts:
                    hosts.append(host)
    except OSError as exc:
        print(f"[injector] warning: cannot read hostfile {path}: {exc}", flush=True)
    return hosts


def resolve_nodes(
    explicit_nodes: str | None = None,
    hostfile: str | None = None,
) -> list[str]:
    """Return a deduplicated list of hostnames participating in the MPI job.

    Resolution order:
      1. *explicit_nodes* (comma-separated string).
      2. *hostfile* path.
      3. ``SLURM_JOB_NODELIST`` environment variable.
      4. ``PBS_NODEFILE`` / ``COBALT_NODEFILE`` environment variable.
      5. Fallback to ``["localhost"]``.
    """
    # 1. Explicit --nodes
    if explicit_nodes:
        raw = [h.strip() for h in explicit_nodes.split(",") if h.strip()]
        if raw:
            return list(dict.fromkeys(raw))  # deduplicate, preserve order

    # 2. Explicit --hostfile
    if hostfile:
        hosts = _parse_hostfile(hostfile)
        if hosts:
            return hosts

    # 3. SLURM
    slurm_nl = os.environ.get("SLURM_JOB_NODELIST", "")
    if slurm_nl:
        hosts = _expand_slurm_nodelist(slurm_nl)
        if hosts:
            return list(dict.fromkeys(hosts))

    # 4. PBS / COBALT nodefile
    for env_var in ("PBS_NODEFILE", "COBALT_NODEFILE"):
        nf = os.environ.get(env_var, "")
        if nf:
            hosts = _parse_hostfile(nf)
            if hosts:
                return hosts

    # 5. Fallback
    return ["localhost"]


# ---------------------------------------------------------------------------
# Process discovery (local and remote)
# ---------------------------------------------------------------------------

def _find_rank_pids_local(executable_name: str) -> list[int]:
    """Return PIDs of rank processes on the **local** machine."""
    try:
        out = subprocess.check_output(
            ["ps", "-eo", "pid,cmd", "--no-headers"],
            text=True,
        )
    except Exception:
        return []

    pids: list[int] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[1]
        if executable_name in cmd and "mpirun" not in cmd and "python" not in cmd:
            pids.append(pid)
    return pids


def _find_rank_pids_remote(host: str, executable_name: str) -> list[int]:
    """Return PIDs of rank processes on a **remote** node via SSH.

    Uses ``ssh -o BatchMode=yes`` so that it never hangs waiting for a
    password prompt (assumes passwordless SSH is configured, which is
    standard on HPC clusters).
    """
    try:
        out = subprocess.check_output(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                host,
                "ps", "-eo", "pid,cmd", "--no-headers",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []

    pids: list[int] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[1]
        if executable_name in cmd and "mpirun" not in cmd and "python" not in cmd:
            pids.append(pid)
    return pids


def find_rank_pids(host: str, executable_name: str) -> list[int]:
    """Return PIDs of rank processes on *host*.

    Dispatches to local or remote discovery depending on whether *host*
    refers to the current machine.
    """
    if _is_local(host):
        return _find_rank_pids_local(executable_name)
    return _find_rank_pids_remote(host, executable_name)


# ---------------------------------------------------------------------------
# Kill helpers
# ---------------------------------------------------------------------------

def _kill_local(pid: int) -> bool:
    """Kill a process on the local machine.  Returns True on success."""
    try:
        os.kill(pid, signal.SIGKILL)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        print(f"[injector] permission error killing local PID {pid}", flush=True)
        return False


def _kill_remote(host: str, pid: int) -> bool:
    """Kill a process on a remote node via SSH.  Returns True on success."""
    try:
        subprocess.check_call(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                host,
                "kill", "-9", str(pid),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False


def kill_rank(host: str, pid: int) -> bool:
    """Kill rank process *pid* on *host*.

    Uses a local ``os.kill`` when *host* is the current machine, otherwise
    falls back to SSH.
    """
    if _is_local(host):
        return _kill_local(pid)
    return _kill_remote(host, pid)


# ---------------------------------------------------------------------------
# Core injection logic
# ---------------------------------------------------------------------------

def inject_failure_once(
    nodes: list[str],
    executable_name: str,
    parent_pid: int,
    max_wait: float,
) -> tuple[bool, str | None, int | None]:
    """Try for up to *max_wait* seconds to kill one rank process across *nodes*.

    A node is chosen at random on each attempt.  If the chosen node has no
    matching rank processes, another node is tried (round-robin through a
    shuffled copy of the node list) before sleeping and retrying.

    Returns ``(injected, host, pid)`` where *injected* is True if a kill
    succeeded, *host* is the node where the kill happened, and *pid* is the
    killed process ID.
    """
    deadline = time.time() + max_wait

    while time.time() < deadline:
        # If the parent (mpirun) has died, stop trying.
        if not os.path.exists(f"/proc/{parent_pid}"):
            return False, None, None

        # Shuffle nodes so we pick a random target each iteration.
        shuffled = list(nodes)
        random.shuffle(shuffled)

        for host in shuffled:
            pids = find_rank_pids(host, executable_name)
            if not pids:
                continue

            target_pid = random.choice(pids)
            if kill_rank(host, target_pid):
                print(
                    f"[injector] killed rank PID {target_pid} on node {host}",
                    flush=True,
                )
                return True, host, target_pid

        # No suitable process found on any node this round – wait and retry.
        time.sleep(0.5)

    return False, None, None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inject a single process failure into a running MPI job.  "
            "Supports multi-node clusters via SSH."
        ),
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        required=True,
        help="PID of the mpirun process to monitor (on the local node)",
    )
    parser.add_argument(
        "--executable-name",
        required=True,
        help="Name of the MPI application executable to look for in process commands",
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
    # --- Multi-node options ---
    parser.add_argument(
        "--nodes",
        default=None,
        help=(
            "Comma-separated list of hostnames participating in the MPI job.  "
            "When omitted the injector tries --hostfile, then SLURM/PBS env "
            "vars, then falls back to localhost."
        ),
    )
    parser.add_argument(
        "--hostfile",
        default=None,
        help=(
            "Path to a hostfile (one hostname per line).  Used when --nodes "
            "is not provided."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    args = parse_args(argv)
    flag_path = Path(args.flag_path)

    nodes = resolve_nodes(
        explicit_nodes=args.nodes,
        hostfile=args.hostfile,
    )
    print(f"[injector] resolved nodes: {nodes}", flush=True)

    time.sleep(args.delay_seconds)

    injected, host, pid = inject_failure_once(
        nodes=nodes,
        executable_name=args.executable_name,
        parent_pid=args.parent_pid,
        max_wait=args.max_wait_seconds,
    )

    if injected:
        try:
            flag_path.parent.mkdir(parents=True, exist_ok=True)
            # Write structured info so callers can inspect which node/pid was hit.
            flag_path.write_text(
                f"injection_success\nhost={host}\npid={pid}\n",
                encoding="utf-8",
            )
        except Exception:
            print("[injector] failed to write injection flag", flush=True)
        return 0

    print("[injector] no suitable rank found for failure injection", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
