#!/usr/bin/env python3
"""run_parallel_queue_ctl.py — CLI control plane for run_parallel_queue.py.

Appends JSONL command records to ``build/_experiment_state/queue_control.jsonl``
that the running orchestrator polls (~2s cadence) inside its main wait loop.
Each command gets a UUID; the orchestrator writes one ack record per command
to ``build/_experiment_state/queue_control.ack.jsonl`` and this client tails
that file by id to surface the result.

Subcommands::

    add    --app NAME --queue {gen,exec} [--kind {validate,bench}]
           [--iter N] [--immediate] [--force]
    remove --app NAME [--queue {gen,exec,all}]
    list

Duplicate-detection rule (server-side, under the orchestrator's state_lock):

    add --queue gen
        Refused if the app is already in any ACTIVE state (READY_FOR_GEN /
        GENERATING / QUEUED_FOR_EXECUTOR / EXECUTING / QUEUED_FOR_BENCH /
        BENCHING) OR already in the gen queue.  Pass ``--force`` to override.

    add --queue exec
        Refused if the app is currently EXECUTING/BENCHING or already in the
        executor (main or priority) queue.  Pass ``--force`` to override.

``remove`` only drains pending queue entries — it never kills an in-flight
gen iter or executor task.  Per OP-0, killing running execution requires
explicit user-driven SIGINT/SIGTERM on the orchestrator process.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
EXP_STATE_DIR = REPO_ROOT / "build" / "_experiment_state"
PID_FILE = EXP_STATE_DIR / "parallel_orchestrator.pid"
CONTROL_FILE = EXP_STATE_DIR / "queue_control.jsonl"
ACK_FILE = EXP_STATE_DIR / "queue_control.ack.jsonl"

# Default wait window for an ack.  Orchestrator polls every ~2s, plus the
# current task may hold state_lock briefly, so anything below ~5s would
# false-fail under normal load.
DEFAULT_ACK_TIMEOUT_S = 10.0
ACK_POLL_INTERVAL_S = 0.2


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _assert_orchestrator_alive() -> int:
    """Verify the orchestrator named in the pid file is actually running.

    Returns its pid.  Raises SystemExit with a clear message if the pid file
    is missing, malformed, or stale (pid not present in the process table).
    """
    if not PID_FILE.exists():
        raise SystemExit(
            f"No orchestrator pid file at {PID_FILE} — "
            f"is run_parallel_queue.py running?"
        )
    try:
        pid = int(PID_FILE.read_text().strip())
    except Exception as exc:
        raise SystemExit(f"Cannot parse pid from {PID_FILE}: {exc}")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        raise SystemExit(
            f"Stale pid file {PID_FILE} (pid {pid} not running) — "
            f"orchestrator died.  Remove the file and relaunch."
        )
    except PermissionError:
        # Someone else's pid landed in the slot — treat as alive (we cannot
        # signal it but it is running).  The orchestrator's own ctl handler
        # will simply never apply our command; the ack-wait will time out.
        pass
    return pid


def _send_and_wait(record: dict, timeout_s: float) -> dict:
    """Append *record* to the control file and wait for a matching ack.

    Snaps the current ack-file byte offset BEFORE appending so pre-existing
    acks for other commands cannot be misread as ours.  Returns the ack
    record, or a synthetic ``{"status": "timeout"}`` record if no ack
    arrived within *timeout_s*.
    """
    cmd_id = record["id"]
    EXP_STATE_DIR.mkdir(parents=True, exist_ok=True)
    ack_offset = ACK_FILE.stat().st_size if ACK_FILE.exists() else 0

    with CONTROL_FILE.open("a") as fh:
        fh.write(json.dumps(record) + "\n")

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if ACK_FILE.exists():
            try:
                with ACK_FILE.open("r") as fh:
                    fh.seek(ack_offset)
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(obj, dict) and obj.get("id") == cmd_id:
                            return obj
            except OSError:
                pass
        time.sleep(ACK_POLL_INTERVAL_S)

    return {
        "id": cmd_id,
        "ts": _utc_iso(),
        "status": "timeout",
        "msg": (f"no ack within {timeout_s:.1f}s — orchestrator may be busy "
                f"or wedged; check build/run_logs/parallel_queue_*.log"),
    }


def _new_id() -> str:
    return str(uuid.uuid4())


def _print_ack(ack: dict) -> int:
    """Print ack to stdout; return CLI exit code (0 on ok/noop, 1 otherwise)."""
    status = ack.get("status", "?")
    msg = ack.get("msg", "")
    # For list, msg is a JSON blob — pretty-print it on success.
    if status == "ok":
        try:
            blob = json.loads(msg)
            if isinstance(blob, dict):
                print(json.dumps(blob, indent=2))
                return 0
        except json.JSONDecodeError:
            pass
    print(f"[ctl] {status}: {msg}")
    return 0 if status in ("ok", "noop") else 1


def cmd_add(args: argparse.Namespace) -> int:
    _assert_orchestrator_alive()
    record: dict = {
        "id": _new_id(),
        "ts": _utc_iso(),
        "cmd": "add",
        "app": args.app,
        "queue": args.queue,
        "force": bool(args.force),
    }
    if args.queue == "exec":
        record["kind"] = args.kind
        if args.iter is not None:
            record["iter"] = args.iter
        record["immediate"] = bool(args.immediate)
    ack = _send_and_wait(record, args.ack_timeout_s)
    return _print_ack(ack)


def cmd_remove(args: argparse.Namespace) -> int:
    _assert_orchestrator_alive()
    record = {
        "id": _new_id(),
        "ts": _utc_iso(),
        "cmd": "remove",
        "app": args.app,
        "queue": args.queue,
    }
    ack = _send_and_wait(record, args.ack_timeout_s)
    return _print_ack(ack)


def cmd_list(args: argparse.Namespace) -> int:
    _assert_orchestrator_alive()
    record = {
        "id": _new_id(),
        "ts": _utc_iso(),
        "cmd": "list",
    }
    ack = _send_and_wait(record, args.ack_timeout_s)
    return _print_ack(ack)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "CLI control plane for run_parallel_queue.py.  Append commands "
            "to the orchestrator's queue_control.jsonl and wait for an ack."
        ),
    )
    parser.add_argument(
        "--ack-timeout-s", type=float, default=DEFAULT_ACK_TIMEOUT_S,
        help=f"Seconds to wait for an ack record (default {DEFAULT_ACK_TIMEOUT_S})",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Add an app to the gen or executor queue")
    add.add_argument("--app", required=True, help="App name (must be in initial --apps list)")
    add.add_argument("--queue", choices=["gen", "exec"], required=True)
    add.add_argument("--kind", choices=["validate", "bench"], default="validate",
                     help="Executor task kind when --queue exec (default validate)")
    add.add_argument("--iter", type=int, default=None,
                     help="Iter number for validate (default = app.iter or 1)")
    add.add_argument("--immediate", action="store_true",
                     help="Push to the executor priority queue so this task "
                          "runs NEXT (still serialized after the current task)")
    add.add_argument("--force", action="store_true",
                     help="Override duplicate-detection refusal (use sparingly)")
    add.set_defaults(func=cmd_add)

    rm = sub.add_parser("remove", help="Drain pending queue entries for an app")
    rm.add_argument("--app", required=True)
    rm.add_argument("--queue", choices=["gen", "exec", "all"], default="all",
                    help="Which queue(s) to scan (default all)")
    rm.set_defaults(func=cmd_remove)

    ls = sub.add_parser("list", help="Snapshot queues + per-app state")
    ls.set_defaults(func=cmd_list)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
