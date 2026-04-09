# Chameleon Checkpoint Strategy

## Reference Implementation
When using StarPU-MPI as backend, fault tolerance is provided at the runtime level. StarPU supports converting task graphs to asynchronous distributed checkpointing with local restart.

## Checkpoint Library
StarPU runtime-level fault tolerance (research-grade, presented at FTXS 2020).

## What Is Checkpointed
- Tile data for all local tiles
- Task graph execution state
- Runtime internal state

## Where Checkpoints Are Placed
Automatic at runtime level - no application code modification needed. StarPU determines checkpoint intervals based on task completion.

## Restart Logic
Local restart: only the failed rank restarts, fetching lost tiles from replicas or recomputation.

## Checkpoint Overhead
Runtime-dependent, typically 3-8% for tile Cholesky.
