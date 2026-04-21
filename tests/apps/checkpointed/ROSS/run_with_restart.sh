#!/bin/bash

# Check if RIO checkpoint exists
if [ -f "pholdio_checkpoint.rio-md" ] && [ -f "pholdio_gvt.txt" ]; then
    GVT=$(cat pholdio_gvt.txt | tr -d '[:space:]')
    # Calculate remaining simulation time
    TOTAL_END=10000
    # Remaining = total - checkpoint_gvt (the chained run simulates this many more time units)
    REMAINING=$(python3 -c "print(int($TOTAL_END - $GVT))")
    echo "Restarting from checkpoint at GVT=$GVT, running remaining $REMAINING time units"
    mpirun -np 2 --oversubscribe ./_build/models/pholdio/pholdio \
        --synch=3 --end=$REMAINING --nlp=2000 --extramem=100000 --io-store=0
else
    echo "No checkpoint found, starting fresh"
    mpirun -np 2 --oversubscribe ./_build/models/pholdio/pholdio \
        --synch=3 --end=10000 --nlp=2000 --extramem=100000 --io-store=1
fi
