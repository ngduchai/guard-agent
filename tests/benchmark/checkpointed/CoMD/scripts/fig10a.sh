#!/bin/bash
### Estimate required hardware IO bandwidth to achieve required
### progress rate for different HPC storage systems.
### Usage: ./fig10a.sh

# Configuration parameters
TARGET_PROGRESS_RATE=0.5 # Based on CORAL-2 Exascale Proposal
TOTAL_NODE_CNT=12655 # Number of Compute nodes
IO_NODE_CNT=211 # Number of IO/Storage nodes; Calculated assuming same total node : io node ratio as Summit
MEM_BW_PER_NODE=100 # Memory bandwidth in GB/s; Limited by network bandwidth
SYSTEMS=(  "NVMe-CR" "OrangeFS" "GlusterFS" "Lustre (buffered)" "Lustre (direct)")
CHKPT_EFF=("0.968"    "0.408"    "0.844"     "0.374"             "0.648") # checkpoint efficiency
REC_EFF=(  "0.996"    "0.994"    "0.806"     "0.922"             "0.658") # recovery efficiency
CACHE_HIT_RATE=0 # for GlusterFS and OrangeFS

i=0
for system in "${SYSTEMS[@]}"; do
    echo "$system"
    echo "--------------------"
    echo -e '# nodes\tio bw'
    echo "--------------------"

    io_bw=100
    for (( nodes = 100; nodes < $TOTAL_NODE_CNT; nodes += 100 )); do
        progress_rate=0
        while ((  $(echo "$progress_rate < $TARGET_PROGRESS_RATE" | bc -l) )); do
            io_bw=$(( io_bw + 10 ))
            # Estimate recovery bandwidth
            if [ "$system" == "NVMe-CR" ] || [ "$system" == "Lustre (direct)" ]; then
                # NVMe-CR and Lustre (direct) don't buffer IO
                rec_bw=$io_bw
            elif [ "$system" == "Lustre (buffered)" ]; then
                # Lustre (buffered) reads all data from server RAM
                rec_bw=$(( $IO_NODE_CNT * MEM_BW_PER_NODE ))
            elif [ "$system" == "OrangeFS" ]; then
                # OrangeFS reads data from server RAM or server SSD
                rec_bw=$(echo "scale=4; ($CACHE_HIT_RATE * $IO_NODE_CNT * $MEM_BW_PER_NODE) + ((1 - $CACHE_HIT_RATE) * $io_bw)" | bc -l)
            else # GlusterFS
                # GlusterFS reads data from client RAM or server SSD
                rec_bw=$(echo "scale=4; ($CACHE_HIT_RATE * $nodes * $MEM_BW_PER_NODE) + ((1 - $CACHE_HIT_RATE) * $io_bw)" | bc -l)
            fi
            progress_rate=$(./progress_rate_test $nodes $io_bw ${CHKPT_EFF[i]} $rec_bw ${REC_EFF[i]})
        done
        echo -e "$nodes"'\t'"$io_bw"
    done

    echo -e '\n'
    i=$(( i + 1 ))
done
