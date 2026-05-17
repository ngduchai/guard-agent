#!/usr/bin/env bash
# WarpX recovery hook for attempt_2.
#
# WarpX (AMReX-based) accepts amr.restart=<path-to-chk-dir> as a CLI
# arg, but the actual checkpoint dirs are named per the diagnostics
# config: patches/WarpX/test_input/inputs_validation sets
# `diagnostics.diags_names = chkpoint` so dirs land at
# `diags/chkpointNNNNNN` (8-digit padded step numbers).
#
# A static recovery-args choice would either:
#   (a) pick an early chkpoint (always exists, but attempt_2 redoes
#       most of attempt_1's work), or
#   (b) pick a late chkpoint (less redo, but might not exist if
#       attempt_1 was killed early).
#
# This hook avoids both by symlinking diags/chk_recovery -> the LATEST
# chkpointNNNNNN dir at attempt_2 launch time.  attempt_2's recovery
# args specify amr.restart=diags/chk_recovery, which transparently
# resolves to whatever step attempt_1 reached.
set -u

# Pick the latest COMPLETE chkpoint dir.  AMReX writes WarpXHeader first,
# then per-level data (Level_0/Bx_fp_H, By_fp_H, ...).  If the kill lands
# during Level_0/ writing, WarpXHeader exists but the level data is
# partial — AMReX restart then errors with "Couldn't open file:
# Level_0/By_fp_H".  We validate by checking for By_fp_H specifically.
SELECTED=""
for D in $(ls -t -d diags/chkpoint[0-9]* 2>/dev/null); do
    if [ -f "$D/Level_0/By_fp_H" ]; then
        SELECTED="$D"
        break
    fi
    echo "[warpx-recovery-hook] skipping incomplete $D (missing Level_0/By_fp_H)" >&2
done

if [ -z "$SELECTED" ]; then
    echo "[warpx-recovery-hook] no complete diags/chkpoint*/ found; attempt_2 will fail"
    exit 0
fi

# Strip the "diags/" prefix because the symlink target is relative to
# the symlink's containing directory.
TARGET="${SELECTED#diags/}"
ln -sfn "$TARGET" diags/chk_recovery
echo "[warpx-recovery-hook] diags/chk_recovery -> $TARGET (full path: $SELECTED)"
