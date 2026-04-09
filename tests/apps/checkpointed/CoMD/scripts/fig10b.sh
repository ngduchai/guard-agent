#!/bin/bash
### Estimate progress rate for different HPC storage systems
### based on available IO banwidth of system.
### Usage: ./fig10b.sh

# Configuration parameters
TOTAL_NODE_CNT=12655 # Number of Compute nodes
IO_NODE_CNT=211 # Number of IO/Storage nodes; Calculated assuming same total node : io node ratio as Summit
MEM_BW_PER_NODE=100 # Memory bandwidth in GB/s; Limited by network bandwidth
MAX_IO_BW=50000
SYSTEMS=(  "NVMe-CR" "OrangeFS" "GlusterFS" "Lustre (buffered)" "Lustre (direct)")
CHKPT_EFF=("0.968"    "0.408"    "0.844"     "0.374"             "0.648") # checkpoint efficiency
REC_EFF=(  "0.996"    "0.994"    "0.806"     "0.922"             "0.658") # recovery efficiency
CACHE_HIT_RATE=0 # for GlusterFS and OrangeFS

i=0
for system in "${SYSTEMS[@]}"; do
    echo "$system"
    echo "--------------------"
    echo -e 'io bw\tprogress rate'
    echo "--------------------"

    for (( io_bw = 1000; io_bw < $MAX_IO_BW; io_bw += 1000 )); do
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
            rec_bw=$(echo "scale=4; ($CACHE_HIT_RATE * $TOTAL_NODE_CNT * $MEM_BW_PER_NODE) + ((1 - $CACHE_HIT_RATE) * $io_bw)" | bc -l)
        fi
        progress_rate=$(./progress_rate_test $TOTAL_NODE_CNT $io_bw ${CHKPT_EFF[i]} $rec_bw ${REC_EFF[i]})
        
        echo -e "$io_bw"'\t'"$progress_rate"
    done

    echo -e '\n'
    i=$(( i + 1 ))
done
