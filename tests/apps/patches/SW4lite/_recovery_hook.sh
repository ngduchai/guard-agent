#!/usr/bin/env bash
# SW4lite recovery hook for attempt_2.
#
# SW4lite's `restart file=NAME` directive in the input opens NAME literally
# (CheckPoint.C:411).  Static config previously hardcoded
# `restart file=restart.cycle=050.sw4checkpoint` (early cycle) → attempt_2
# redoes most of the simulation.
#
# This hook symlinks `restart.recovery.sw4checkpoint` -> the LATEST
# COMPLETE restart.cycle=NNN.sw4checkpoint file (one with By_fp_H, the
# last data block written, indicating a complete checkpoint).  The
# patched validation_test_restart.in references the symlink name.
set -u

# Pick the latest COMPLETE checkpoint file.  Note these are FILES not
# directories — SW4lite has all Level data inline in the .sw4checkpoint
# file, but we treat the cycle=050 directory check from WarpX-pattern
# as analogous: just check file existence + non-zero size.
SELECTED=""
for F in $(ls -t restart.cycle=*.sw4checkpoint 2>/dev/null); do
    if [ -s "$F" ]; then
        SELECTED="$F"
        break
    fi
    echo "[sw4lite-recovery-hook] skipping empty $F" >&2
done

if [ -z "$SELECTED" ]; then
    echo "[sw4lite-recovery-hook] no restart.cycle=*.sw4checkpoint found; attempt_2 will fail"
    exit 0
fi

ln -sfn "$SELECTED" restart.recovery.sw4checkpoint
echo "[sw4lite-recovery-hook] restart.recovery.sw4checkpoint -> $SELECTED"
