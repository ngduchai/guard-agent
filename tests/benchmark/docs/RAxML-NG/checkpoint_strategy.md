# RAxML-NG Checkpoint Strategy

## Reference Implementation
Built-in `CheckpointManager` class that serializes the complete search state. A fault-tolerant fork exists at https://github.com/lukashuebner/ft-raxml-ng using ULFM for automatic MPI recovery.

## Checkpoint Library
Native file I/O. The FT fork adds ULFM (User-Level Failure Mitigation) for MPI-level recovery.

## What Is Checkpointed
- Best tree found so far (topology + branch lengths)
- All model parameters (per partition)
- Search state (current iteration, RNG state, SPR radius)
- Bootstrap replicate progress

## Where Checkpoints Are Placed
After each completed SPR round and after each bootstrap replicate.

## Restart Logic
1. On startup, check for `.ckp` file matching the run ID
2. If found: deserialize search state, resume from last SPR round
3. Automatic: re-invoking same command with same `--prefix` auto-restarts

## Checkpoint Overhead
Negligible (~0.01% of runtime). Checkpoint is < 100 KB.
