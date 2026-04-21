#!/bin/bash
cd examples/molecules/He

# Find the latest config.h5 checkpoint file
CKPT=$(ls -t He.s*.config.h5 2>/dev/null | head -1)

if [ -n "$CKPT" ]; then
    # Extract series number (e.g., He.s005.config.h5 -> 5)
    FILEROOT=$(echo "$CKPT" | sed 's/\.config\.h5$//')
    SERIES=$(echo "$CKPT" | sed 's/He\.s\([0-9]*\)\.config\.h5/\1/' | sed 's/^0*//')
    [ -z "$SERIES" ] && SERIES=0
    echo "Restarting from checkpoint: $CKPT (series=$SERIES, fileroot=$FILEROOT)"

    # Use series+100 to avoid conflicting with existing output files
    RESTART_SERIES=$((SERIES + 100))

    # Build restart XML: load walkers from checkpoint, skip completed sections
    python3 -c "
import xml.etree.ElementTree as ET

tree = ET.parse('he_simple_opt_ckpt.xml')
root = tree.getroot()

# Set series to a new value to avoid stat file conflicts
proj = root.find('project')
if proj is not None:
    proj.set('series', '$RESTART_SERIES')

# Remove completed <qmc> sections (first $SERIES sections)
qmc_sections = root.findall('qmc')
skip = $SERIES
removed = 0
for qmc in list(qmc_sections):
    if removed < skip:
        root.remove(qmc)
        removed += 1

# Add mcwalkerset BEFORE remaining qmc sections
from xml.etree.ElementTree import SubElement
mcs = ET.Element('mcwalkerset')
mcs.set('fileroot', '$FILEROOT')
mcs.set('node', '-1')
# Insert before the first remaining qmc
remaining = root.findall('qmc')
if remaining:
    idx = list(root).index(remaining[0])
    root.insert(idx, mcs)
else:
    root.append(mcs)

tree.write('/tmp/qmc_restart.xml', xml_declaration=True)
print(f'Skipping {removed} completed sections, {len(qmc_sections) - removed} remaining (series={$RESTART_SERIES})')
"
    ../../../build/bin/qmcpack /tmp/qmc_restart.xml
else
    echo "Starting fresh simulation"
    ../../../build/bin/qmcpack he_simple_opt_ckpt.xml
fi
