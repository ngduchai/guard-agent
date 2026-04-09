# miniFE Checkpoint Strategy

## Reference Implementation
The checkpointed version uses the **MPI-FT-Bench** framework, which wraps miniFE with FTI-based checkpoint/restart support.

## Checkpoint Library
- **FTI** (Fault Tolerance Interface)
- FTI provides multi-level checkpoint support (L1: local, L2: partner copy, L3: Reed-Solomon, L4: parallel file system)

## What Is Checkpointed
All solver state required to resume the CG iteration:
- Solution vector: `x`
- Residual vector: `r`
- Search direction: `p`
- Scalar state: `num_iterations`, `rtrans`, `oldrtrans`
- The sparse matrix `A` and RHS `b` are **not** checkpointed (they are constant and can be reassembled)

Total checkpoint size: ~3.0 MB per rank for a 100^3 mesh on 8 ranks (vectors only)

## Where Checkpoints Are Placed
At the **top of the CG iteration loop**, before the SpMV:

```
for (int iter = start_iter; iter < max_iters; iter++) {
    // <- CHECKPOINT HERE (FTI_Snapshot)
    matvec(A, p, Ap);
    ...
}
```

## Restart Logic
1. Call `FTI_Init` and check if this is a recovery run (`FTI_Status`)
2. If recovering: FTI restores all protected variables automatically
3. The CG loop resumes from the saved iteration count
4. If no checkpoint exists: start from iteration 0 with initial guess x=0

## Checkpoint Overhead
- Per-checkpoint overhead: ~1-3% of total runtime (L1 local checkpoint)
- Checkpoint frequency: configurable via FTI configuration file
- L4 (PFS) checkpoints are more expensive but survive node failures
- FTI configuration via `config.fti` file specifying checkpoint levels and intervals
