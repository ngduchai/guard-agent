#!/usr/bin/env bash
# HyPar recovery hook for attempt_2.
#
# HyPar's `restart_iter` parameter in solver.inp ONLY adjusts the file
# numbering counter and the simulation-time counter
# (TimeInitialize.c:52: TS->waqt = restart_iter * dt).  The actual
# initial state is ALWAYS read from `initial.bin` — the binary does
# NOT read op_NNNNN.bin files at startup
# (src/Simulation/InitialSolution.c).
#
# This hook copies the latest op_NNNNN.bin (written by attempt_1) over
# initial.bin so that attempt_2's "initial state" is actually the
# saved checkpoint state.  Combined with restart_iter set to the
# matching iteration, this gives true recovery semantics.
set -u

LATEST=$(ls -t op_*.bin 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    echo "[hypar-recovery-hook] no op_*.bin found in $(pwd); attempt_2 will start fresh"
    exit 0
fi

# Extract FILE NUMBER from op_NNNNN.bin -> NNNNN
FILE_NUM="${LATEST#op_}"
FILE_NUM="${FILE_NUM%.bin}"
FILE_NUM="${FILE_NUM#0}"
FILE_NUM="${FILE_NUM#0}"
FILE_NUM="${FILE_NUM#0}"
FILE_NUM="${FILE_NUM#0}"
FILE_NUM="${FILE_NUM:-0}"

# Convert FILE NUMBER to ACTUAL ITER COUNT.  HyPar writes op_NNNNN.bin
# every `file_op_iter` iterations (read from solver.inp).  The PREVIOUS
# version of this hook set restart_iter=FILE_NUM directly, but HyPar
# uses restart_iter as an iteration count (TimeInitialize.c:52:
# TS->waqt = restart_iter * dt) — so a small FILE_NUM caused attempt_2
# to think it had only done a few iterations and re-run the full
# n_iter range, defeating recovery.
FILE_OP_ITER=$(grep -oE 'file_op_iter[[:space:]]+[0-9]+' solver.inp 2>/dev/null \
                 | awk '{print $2}' | head -1)
FILE_OP_ITER="${FILE_OP_ITER:-1}"
ITER=$(( FILE_NUM * FILE_OP_ITER ))

cp -f "$LATEST" initial.bin
echo "[hypar-recovery-hook] copied $LATEST -> initial.bin (file_num=$FILE_NUM, file_op_iter=$FILE_OP_ITER, iter=$ITER)"

# Patch solver.inp's restart_iter line to match the loaded iteration so
# HyPar's filename counter and simulation-time counter resume from the
# right point instead of starting at 0.
if [ -f solver.inp ]; then
    if grep -q "^[[:space:]]*restart_iter" solver.inp 2>/dev/null; then
        sed -i "s|^[[:space:]]*restart_iter.*|  restart_iter $ITER|" solver.inp
        echo "[hypar-recovery-hook] patched solver.inp restart_iter -> $ITER"
    else
        sed -i "/^begin/a\\  restart_iter $ITER" solver.inp
        echo "[hypar-recovery-hook] inserted restart_iter $ITER into solver.inp"
    fi
fi
