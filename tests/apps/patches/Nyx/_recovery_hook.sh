#!/usr/bin/env bash
# Nyx recovery hook for attempt_2.
#
# AMReX (Nyx's runtime) accepts amr.restart=<chk-dir> as a CLI arg,
# but the actual chkpoint dirs are named per amr.check_file=chk =>
# chkNNNNN (5-digit padded step numbers).
#
# Static recovery args hardcoded chk00010 (early), causing attempt_2
# to redo most of the simulation.  This hook symlinks
# chk_recovery -> the LATEST complete chkNNNNN dir, so recovery args
# `amr.restart=chk_recovery` transparently uses whatever step
# attempt_1 reached.
set -u

# Pick the latest COMPLETE chk dir.  AMReX writes Header file last
# (after all level data), so its presence indicates a complete write.
SELECTED=""
for D in $(ls -t -d chk[0-9]* 2>/dev/null); do
    if [ -f "$D/Header" ]; then
        SELECTED="$D"
        break
    fi
    echo "[nyx-recovery-hook] skipping incomplete $D (no Header)" >&2
done

if [ -z "$SELECTED" ]; then
    echo "[nyx-recovery-hook] no complete chk*/ found; attempt_2 will fail"
    exit 0
fi

ln -sfn "$SELECTED" chk_recovery
echo "[nyx-recovery-hook] chk_recovery -> $SELECTED"
