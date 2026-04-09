#!/bin/bash
### Script to remove temp/unwanted files produced by job runs
### Usage: ./cleanup.sh <clean-dir>

### Print usage
usage() {
    echo "Usage: ./cleanup.sh <clean-dir>"
}

CLEAN_DIR=$1

# Validate command line args
if [ "$1" == "" ] || [ ! -d "$1" ]; then
    usage
    exit 1
fi

cd $CLEAN_DIR

# Remove unnecessary files
rm -f *.yaml nvmf-*.log CoMD_state-*.txt hosts_* pdsh_hosts_*
