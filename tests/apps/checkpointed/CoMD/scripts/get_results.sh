#!/bin/bash
### Consolidate results for CoMD runs by parsing log files.
### Pretty print results to stdout and create .tsv results
### file, which can be imported in Excel, Google Sheets, etc.
### Usage: ./get_results.sh <results-dir>

set -o pipefail

### Print usage
usage() {
    echo "Usage: ./get_results.sh <results-dir>"
}

### Find chkpt load time for given file
load_time() {
    local LTIME=$(grep chkptLoad $1 2>/dev/null | tail -n 1 | awk '{ print $6 }')
    if [[ $? -eq 0 ]] && [[ "$LTIME" != "" ]]; then
        echo $LTIME
    else
        echo "N/A"
    fi
}

### Find chkpt store time for given file
store_time() {
    local fail=0
    local STIME=$(grep chkptStore $1 2>/dev/null | tail -n 1 | awk '{ print $6 }')
    if [ $? -ne 0 ]; then
        fail=1
    fi
    local NCALLS=$(grep chkptStore $1 2>/dev/null | head -n 1 | awk '{ print $2 }')
    if [ $? -ne 0 ]; then
         fail=1
    fi
    if [[ $fail -eq 0 ]] && [[ "$STIME" != "" ]]; then
        echo "scale=4; $STIME/$NCALLS" | bc -l
    else
        echo "N/A"
    fi
}

# Configuration parameters
BACKEND=("nvme-cr" "posix") # backend
NNODES=("1" "2" "4" "8" "16") # number of nodes
PPN=("1" "2" "4" "8" "16" "28") # ppn
SCALING=("" "weak" "strong") # scaling study
RESULTS_FILE=comd-results.tsv
RESULTS_DIR=$1

# Validate command line args
if [ "$1" == "" ] || [ ! -d "$1" ]; then
    usage
    exit 1
fi

cd $RESULTS_DIR
rm -f $RESULTS_FILE

for backend in "${BACKEND[@]}"; do

    # Each backend has its own specific modes
    if [ "$backend" == "nvme-cr" ]; then
        MODE=("local" "remote")
    else # posix
        MODE=("ssd" "lustre" "ramdisk")
    fi

    for scaling in "${SCALING[@]}"; do

        # For some log files, scaling might not be specified
        if [ "$scaling" == "" ]; then
            scale="unknown"
        else
            scale=$scaling
            scaling="-$scaling"
        fi

        for mode in "${MODE[@]}"; do

            for nnodes in "${NNODES[@]}"; do

                file=comd-$backend"$scaling"-$mode-$nnodes-"${PPN[0]}".log
                if [ ! -f "$file" ]; then
                    # If file doesn't exist skip to next node cnt
                    continue
                fi

                echo "BACKEND=$backend, SCALING=$scale, MODE=$mode, NODES=$nnodes" \
                    | tee -a $RESULTS_FILE
                echo "-------------------------------------------"
                echo -e 'PPN\tPROCS\tCHKPT(s)\tRECOVERY(s)' \
                    | tee -a $RESULTS_FILE
                echo "-------------------------------------------"

                for ppn in "${PPN[@]}"; do
                    file=comd-$backend"$scaling"-$mode-$nnodes-"$ppn".log
                    LTIME=$(load_time $file)
                    STIME=$(store_time $file)
                    PROCS=$(( $nnodes * $ppn ))
                    echo -e "$ppn"'\t'"$PROCS"'\t'"$STIME"'\t\t'"$LTIME"
                    echo -e "$ppn"'\t'"$PROCS"'\t'"$STIME"'\t'"$LTIME" \
                        >> $RESULTS_FILE
                done

                echo "-------------------------------------------"
                echo "" | tee -a $RESULTS_FILE
            done
        done
    done
done
