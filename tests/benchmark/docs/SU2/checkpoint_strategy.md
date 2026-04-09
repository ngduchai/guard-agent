# SU2 Checkpoint Strategy

## Reference Implementation
Native restart file writing via `SU2_SOL` module. Restart files contain the complete solution state.

## Checkpoint Library
Native binary I/O (built into SU2).

## What Is Checkpointed
- Conservative variables at all mesh nodes
- Mesh partition information
- Iteration counter and convergence history
- Turbulence model variables (if applicable)

## Where Checkpoints Are Placed
Written at the end of each outer iteration (or at configurable intervals via `OUTPUT_WRT_FREQ`).

## Restart Logic
1. Set `RESTART_SOL=YES` in config file
2. SU2 reads restart file, initializes solution
3. Continues iterating from restored state

## Checkpoint Overhead
- I/O: ~0.5-1 second for 1M node mesh
- Typically negligible compared to solver time per iteration
