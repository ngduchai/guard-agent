# ExaML Checkpoint Strategy

## Reference Implementation
ExaML has built-in checkpointing inherited from RAxML-Light, writing tree topology and model parameters after each search iteration.

## Checkpoint Library
Native file I/O (no external library).

## What Is Checkpointed
- Best tree topology (Newick format)
- Branch lengths for all edges
- Per-partition model parameters (substitution rates, base frequencies, alpha shape)
- Current search iteration number
- Random number generator state

## Where Checkpoints Are Placed
After each completed SPR round, before starting the next search iteration.

## Restart Logic
1. Check for `ExaML_binaryCheckpoint.*` files
2. If found: parse tree, restore model parameters, resume from saved iteration
3. If not: start fresh with random or parsimony starting tree

## Checkpoint Overhead
Minimal (~0.1% of runtime) since checkpoint is just tree + parameters (few KB).
