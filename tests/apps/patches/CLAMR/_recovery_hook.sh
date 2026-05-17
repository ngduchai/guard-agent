#!/usr/bin/env bash
# CLAMR recovery hook for attempt_2.
#
# CLAMR's `-R <file>` flag (input.cpp:case 'R') restarts from a backup
# file.  CLAMR's Crux module writes backups to
# `checkpoint_output/backupNNNNN.crx` (crux/crux.cpp:265) or `.h5` if
# HDF5 enabled.  This hook symlinks `checkpoint_output/backup_latest.crx`
# (or .h5) -> the LATEST backupNNNNN file, so the recovery args
# `-R checkpoint_output/backup_latest.crx` transparently uses whatever
# cycle attempt_1 reached.
set -u

CKPT_DIR="checkpoint_output"
if [ ! -d "$CKPT_DIR" ]; then
    echo "[clamr-recovery-hook] no checkpoint_output/ found; attempt_2 will fail"
    exit 0
fi

# Try .crx first, then .h5
LATEST=""
for ext in crx h5; do
    F=$(ls -t "$CKPT_DIR"/backup*.${ext} 2>/dev/null | head -1)
    if [ -n "$F" ] && [ -s "$F" ]; then
        LATEST="$F"
        EXT="$ext"
        break
    fi
done

if [ -z "$LATEST" ]; then
    echo "[clamr-recovery-hook] no checkpoint_output/backup*.{crx,h5} found"
    exit 0
fi

# Strip checkpoint_output/ prefix for relative symlink target
TARGET="${LATEST#${CKPT_DIR}/}"
ln -sfn "$TARGET" "${CKPT_DIR}/backup_latest.${EXT}"
echo "[clamr-recovery-hook] ${CKPT_DIR}/backup_latest.${EXT} -> $TARGET"
