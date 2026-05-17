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

_MPI_LAUNCHERS = {"mpirun", "mpiexec", "mpioptions", "orterun", "orted",
                  "hydra_pmi_proxy", "srun", "prterun", "prted"}
_SHELL_INTERPRETERS = {"bash", "sh", "zsh", "ksh", "dash"}
_PYTHON_INTERPRETERS = {"python", "python2", "python3"}


def _argv_basename(token: str) -> str:
    """Return the basename of an argv token, stripping any path and
    common version suffixes (``python3.12`` → ``python3``)."""
    name = os.path.basename(token)
    # Strip a trailing ``.<digits>`` suffix only for python3.x style.
    if name.startswith("python3.") and name[8:].isdigit():
        return "python3"
    return name


def match_rank_pids(ps_output: str, executable_name: str) -> list[int]:
    """Return PIDs whose command-line indicates they are the *executable_name*
    rank process.

    *ps_output* is the output of ``ps -eo pid,cmd --no-headers`` (one
    process per line, ``pid <space> cmdline``).  The match logic:

      * If ``argv[0]`` basename is an MPI launcher, **skip** — never a
        rank, always the parent of one.
      * If ``argv[0]`` basename is a Python interpreter, **skip** — the
        injector must not kill the validation harness or a stray
        ``python validate.py --executable-name <X>`` whose argv contains
        the binary name as a flag value.
      * If ``argv[0]`` basename is a shell interpreter (bash/sh/zsh/...),
        treat ``argv[1]`` basename as the effective executable name —
        this covers MMSP / HPCG / SST style wrappers.  The ``argv[0]``
        basename of the wrapper script (``mmsp_run.sh``, ``xhpcg_run``)
        is what the caller passes as ``executable_name``.  The ``bash
        run_validate.sh`` wrapper is filtered out here because its
        ``argv[1]`` basename is ``run_validate.sh``, not the app
        name — even if the app name appears later in argv.
      * Otherwise, match when ``argv[0]`` basename equals
        *executable_name*.

    The matcher is intentionally pure — it takes a string in, returns
    pids out — so that the friendly-fire regression suite can drive it
    with synthetic ps output without touching the OS.
    """
    target = os.path.basename(executable_name)
    pids: list[int] = []
    for line in ps_output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) < 2:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        cmd = parts[1]
        argv = cmd.split()
        if not argv:
            continue
        argv0 = _argv_basename(argv[0])
        if argv0 in _MPI_LAUNCHERS or argv0 in _PYTHON_INTERPRETERS:
            continue
        if argv0 in _SHELL_INTERPRETERS:
            # Shell wrapper: the "real" rank is identified by argv[1].
            if len(argv) < 2:
                continue
            argv1 = _argv_basename(argv[1])
            if argv1 == target:
                pids.append(pid)
            continue
        if argv0 == target:
            pids.append(pid)
    return pids


def _build_descendants(ppid_of: dict[int, int], parent_pid: int) -> set[int]:
    """Return all PIDs whose ancestry chain reaches *parent_pid*."""
    descendants: set[int] = set()
    for pid in ppid_of:
        cur = pid
        seen: set[int] = set()
        while cur in ppid_of:
            if cur in seen:  # ppid loop guard (shouldn't happen, but defensive)
                break
            seen.add(cur)
            parent = ppid_of[cur]
            if parent == parent_pid:
                descendants.add(pid)
                break
            if parent == 0 or parent == 1:
                break
            cur = parent
    return descendants


def _ps_with_ppid_local() -> tuple[str, dict[int, int]]:
    """Run ``ps -eo pid,ppid,cmd --no-headers`` locally; return
    ``(pid_cmd_output, ppid_map)`` where ``pid_cmd_output`` is in the
    ``pid cmd`` format that :func:`match_rank_pids` expects.
    """
    out = subprocess.check_output(
        ["ps", "-eo", "pid,ppid,cmd", "--no-headers"],
        text=True,
    )
    return _split_ppid_from_pscmd(out)


def _split_ppid_from_pscmd(raw_out: str) -> tuple[str, dict[int, int]]:
    """Take ``pid ppid cmd`` lines and return ``(pid cmd, ppid_map)``.

    Defensive against malformed lines: any line that doesn't have at
    least three whitespace-separated fields is dropped from both
    outputs.
    """
    pid_cmd_lines: list[str] = []
    ppid_of: dict[int, int] = {}
    for line in raw_out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
            ppid = int(parts[1])
        except ValueError:
            continue
        ppid_of[pid] = ppid
        pid_cmd_lines.append(f"{parts[0]} {parts[2]}")
    return "\n".join(pid_cmd_lines), ppid_of


def _find_rank_pids_local(
    executable_name: str,
    parent_pid: int | None = None,
) -> list[int]:
    """Return PIDs of rank processes on the **local** machine.

    Uses :func:`match_rank_pids` to identify candidates by argv structure
    (rejects MPI launchers, python interpreters, and the validation
    wrapper).  When *parent_pid* is given, candidates are further
    restricted to descendants of *parent_pid* — defence in depth against
    a second unrelated mpirun job running the same binary on the same
    machine.
    """
    try:
        pid_cmd_out, ppid_of = _ps_with_ppid_local()
    except Exception:
        return []
    candidates = match_rank_pids(pid_cmd_out, executable_name)
    if parent_pid is None:
        return candidates
    descendants = _build_descendants(ppid_of, parent_pid)
    return [pid for pid in candidates if pid in descendants]


def _find_rank_pids_remote(
    host: str,
    executable_name: str,
    parent_pid: int | None = None,
) -> list[int]:
    """Return PIDs of rank processes on a **remote** node via SSH.

    Uses ``ssh -o BatchMode=yes`` so that it never hangs waiting for a
    password prompt (assumes passwordless SSH is configured, which is
    standard on HPC clusters).

    The *parent_pid* descendant filter only applies when the parent
    process actually lives on the remote node — typically not the case
    in multi-node MPI (mpirun runs on one node, ranks on others).  When
    that mismatch happens, the descendant filter would yield an empty
    set and the matcher's argv-based rejection alone is what guards
    against friendly-fire.
    """
    try:
        raw = subprocess.check_output(
            [
                "ssh",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=5",
                host,
                "ps", "-eo", "pid,ppid,cmd", "--no-headers",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return []
    pid_cmd_out, ppid_of = _split_ppid_from_pscmd(raw)
    candidates = match_rank_pids(pid_cmd_out, executable_name)
    if parent_pid is None:
        return candidates
    descendants = _build_descendants(ppid_of, parent_pid)
    if not descendants:
        # Parent likely doesn't live on this node (multi-node MPI);
        # fall back to the argv-based match alone.
        return candidates
    return [pid for pid in candidates if pid in descendants]


def find_rank_pids(
    host: str,
    executable_name: str,
    parent_pid: int | None = None,
) -> list[int]:
    """Return PIDs of rank processes on *host*.

    Dispatches to local or remote discovery depending on whether *host*
    refers to the current machine.
    """
    if _is_local(host):
        return _find_rank_pids_local(executable_name, parent_pid)
    return _find_rank_pids_remote(host, executable_name, parent_pid)


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
            # Pass parent_pid to scope the search to descendants of mpirun
            # on the local node (defence in depth on top of comm matching).
            pids = find_rank_pids(host, executable_name, parent_pid=parent_pid)
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
