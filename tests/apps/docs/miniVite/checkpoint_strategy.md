# miniVite Checkpoint Strategy

## Reference Implementation
The checkpointed version uses the **MPI-FT-Bench** framework, which wraps miniVite with FTI-based checkpoint/restart support.

## Checkpoint Library
- **FTI** (Fault Tolerance Interface)
- FTI provides multi-level checkpoint support (L1: local, L2: partner copy, L3: Reed-Solomon, L4: parallel file system)

## What Is Checkpointed
Community state required to resume the Louvain iteration:
- Community assignments: `comm` (per-vertex community label)
- Community degree: `comm_degree`
- Cluster weights: `cluster_weight`
- Scalar state: `modularity`, `num_iters`, `coarsening_level`
- The graph structure (CSR arrays) is **not** checkpointed (it is constant and reloaded from the input file)

Total checkpoint size: ~3.1 MB per rank for a 2^20 vertex graph on 8 ranks

## Where Checkpoints Are Placed
At the **top of the Louvain iteration loop**, before the local modularity optimization phase:

```
while (communities_changed) {
    // <- CHECKPOINT HERE (FTI_Snapshot)
    for each local vertex:
        compute modularity gain for neighbor communities
        ...
}
```

## Restart Logic
1. Call `FTI_Init` and check recovery status via `FTI_Status`
2. If recovering: FTI restores all protected variables (community arrays, scalars)
3. Reload the graph from the input file (graph structure is not checkpointed)
4. Resume the Louvain loop from the saved iteration
5. If no checkpoint exists: start fresh with each vertex as its own community

## Checkpoint Overhead
- Per-checkpoint overhead: ~1-2% of total runtime (L1 local checkpoint)
- Checkpoint frequency: configurable via FTI configuration file
- Community arrays are small relative to graph structure, so checkpoints are lightweight
- FTI configuration via `config.fti` specifying checkpoint levels and intervals
