# ExaML Computation Flow

## Overview
ExaML (Exascale Maximum Likelihood) performs phylogenetic tree inference using maximum likelihood on partitioned multi-gene datasets. MPI parallelization distributes alignment columns across ranks.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Parse alignment] --> B[Initialize random tree]
    B --> C[ML search loop]
    C --> D[Evaluate likelihood]
    D --> D1[Per-partition likelihood on local columns]
    D1 --> D2[MPI_Allreduce sum likelihood]
    D --> E[SPR rearrangements]
    E --> F[Optimize branch lengths]
    F --> G{Improved?}
    G -->|Yes| C
    G -->|No| H[Checkpoint tree]
    H --> I[Output best tree + MPI_Finalize]
```

## MPI Communication
- **Data parallel**: alignment columns distributed across ranks via cyclic assignment
- **Collective**: `MPI_Allreduce` to sum per-site log-likelihoods across ranks
- **Broadcast**: `MPI_Bcast` for tree topology updates after SPR moves

## I/O Points
- Checkpoint files: tree topology + model parameters written periodically
- Final output: best tree in Newick format + log-likelihood score
