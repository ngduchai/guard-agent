#!/usr/bin/env bash
# ROSS recovery hook — diagnostic for v25.
# pholdio with --io-store=0 silently no-ops if checkpoint files are
# missing or empty.  This hook reports the rio files' status before
# attempt_2 launches, so we can tell whether pholdio's load is failing
# because the files don't exist (write-side bug) or because pholdio
# ignores them (read-side bug).
set -u

echo "[ross-recovery-hook] cwd: $(pwd)"
ls -la pholdio_checkpoint* 2>&1 | head -10 | sed 's/^/[ross-recovery-hook]   /'
if [ ! -f pholdio_checkpoint.rio-md ]; then
    echo "[ross-recovery-hook] WARNING: pholdio_checkpoint.rio-md MISSING — load will silently no-op"
fi
echo "[ross-recovery-hook] gvt.txt: $(cat pholdio_gvt.txt 2>/dev/null || echo '(missing)')"
