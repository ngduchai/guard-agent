# AMG Checkpoint Strategy

## Reference Implementation
The checkpointed version uses the **MPI-FT-Bench** framework, which wraps AMG with FTI-based checkpoint/restart support.

## Checkpoint Library
- **FTI** (Fault Tolerance Interface)
- FTI provides multi-level checkpoint support (L1: local, L2: partner copy, L3: Reed-Solomon, L4: parallel file system)

## What Is Checkpointed
Solver state required to resume the PCG iteration:
- Solution vector: `x` (fine level)
- Residual vector: `r`
- Search direction: `p`
- Preconditioned residual: `s`
- Scalar state: `num_iterations`, `rel_residual_norm`
- The multigrid hierarchy (coarse matrices, interpolation operators) is **not** checkpointed (it is rebuilt from the fine-level matrix, which is constant)

Total checkpoint size: ~2.0 MB per rank for a 40^3 problem

## Where Checkpoints Are Placed
At the **top of the PCG iteration loop**, before the V-cycle preconditioner is applied:

```
for (int iter = start_iter; iter < max_iters; iter++) {
    // <- CHECKPOINT HERE (FTI_Snapshot)
    AMG_V_cycle(A, r, s);  // preconditioner
    alpha = dot(r, s);      // MPI_Allreduce
    ...
}
```

## Restart Logic
1. Call `FTI_Init` and check recovery status via `FTI_Status`
2. If recovering: FTI restores all protected variables (solution, residual, search direction, scalars)
3. Rebuild the multigrid hierarchy from the problem definition (constant; not checkpointed)
4. Resume PCG iteration from the saved iteration count
5. If no checkpoint exists: start from iteration 0 with initial guess x=0

## Checkpoint Overhead
- Per-checkpoint overhead: ~1-3% of total runtime (L1 local checkpoint)
- Checkpoint frequency: configurable via FTI configuration file
- Solver vectors are small relative to the full multigrid hierarchy, keeping checkpoints lightweight
- FTI configuration via `config.fti` specifying checkpoint levels and intervals
