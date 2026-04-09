# Palabos Checkpoint Strategy

## Reference Implementation
Native parallel checkpointing using MPI-IO with `saveBinaryBlock()` / `loadBinaryBlock()`.

## Checkpoint Library
Native MPI-IO (built into Palabos).

## What Is Checkpointed
- All population distributions f[0..q-1] for every lattice cell
- External scalar fields if present
- Iteration counter

## Where Checkpoints Are Placed
At configurable intervals in the time step loop (typically every N iterations).

## Restart Logic
1. Call `loadBinaryBlock(lattice, filename)` at startup
2. Restores all populations and external fields
3. Set iteration counter to saved value
4. Resume time stepping

## Checkpoint Overhead
- I/O dominated: ~76 MB per rank for 128^3 D3Q19
- With MPI-IO: ~1-3 seconds per checkpoint on local SSD
