#!/bin/bash
### Estimate progress rate for different HPC storage systems
### on projected exascale system with varying percentage of
### system memory checkpointed.
### Usage: ./fig9.sh

echo "Checkpointing 20% Memory"
./progress_rate 0.2
echo ""

echo "Checkpointing 30% Memory"
./progress_rate 0.3
echo ""

echo "Checkpointing 40% Memory"
./progress_rate 0.4
echo ""

echo "Checkpointing 50% Memory"
./progress_rate 0.5
echo ""
