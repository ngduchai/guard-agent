#!/usr/bin/env bash
# QMCPACK recovery hook for attempt_2.
#
# Static He.cont.xml previously hardcoded series 5 → attempt_2 redoes
# series 6..28 (~90% of the 60-series optimization loop).  This hook
# finds the LATEST He.sNNN.vp.h5 file written by attempt_1 and rewrites
# He.cont.xml to:
#   1. project series = N+1
#   2. override_variational_parameters href = He.sNNN.vp.h5
#   3. loop max = 60 - (N+1) (remaining series to complete)
#
# The hook expects He.cont.xml to be present (overlaid from
# patches/QMCPACK/examples/molecules/He/) — it ONLY updates the
# series-specific fields.
set -u

LATEST_VP=$(ls -t He.s*.vp.h5 2>/dev/null | head -1)
if [ -z "$LATEST_VP" ]; then
    echo "[qmcpack-recovery-hook] no He.s*.vp.h5 found; attempt_2 will fail"
    exit 0
fi

# Extract series number: "He.s028.vp.h5" -> "028" -> 28
N_STR="${LATEST_VP#He.s}"
N_STR="${N_STR%.vp.h5}"
N=$(printf '%d' "$((10#$N_STR))" 2>/dev/null) || N=0

NEXT_SERIES=$((N + 1))
REMAINING_LOOPS=$((60 - NEXT_SERIES))
if [ "$REMAINING_LOOPS" -lt 1 ]; then REMAINING_LOOPS=1; fi

if [ ! -f He.cont.xml ]; then
    echo "[qmcpack-recovery-hook] He.cont.xml missing; attempt_2 will fail"
    exit 0
fi

# Update the 3 series-specific fields in He.cont.xml in place.
# Pattern: series="N", href="He.sNNN.vp.h5", loop max="N"
sed -i \
    -e "s|<project id=\"He\" series=\"[0-9]\+\">|<project id=\"He\" series=\"${NEXT_SERIES}\">|" \
    -e "s|<override_variational_parameters href=\"He.s[0-9]\+\.vp\.h5\"/>|<override_variational_parameters href=\"${LATEST_VP}\"/>|" \
    -e "s|<loop max=\"[0-9]\+\">|<loop max=\"${REMAINING_LOOPS}\">|" \
    He.cont.xml

echo "[qmcpack-recovery-hook] updated He.cont.xml: series=${NEXT_SERIES} vp=${LATEST_VP} loop_max=${REMAINING_LOOPS}"
