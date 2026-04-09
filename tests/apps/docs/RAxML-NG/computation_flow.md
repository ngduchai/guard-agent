# RAxML-NG Computation Flow

## Overview
RAxML-NG performs maximum-likelihood phylogenetic inference using SPR-based tree search with fine-grained MPI+pthreads parallelism. Supports partitioned models, bootstrapping, and automatic checkpointing.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Load alignment] --> B[Generate starting trees]
    B --> C[ML optimization loop]
    C --> D[SPR round]
    D --> D1[Generate candidate SPR moves]
    D1 --> D2[Evaluate moves in parallel]
    D2 --> D3[Apply best move]
    D --> E[Optimize all branch lengths]
    E --> F[Compute likelihood]
    F --> F1[MPI_Allreduce partial likelihoods]
    F --> G{Converged?}
    G -->|No| C
    G -->|Yes| H[Write checkpoint]
    H --> I[Bootstrap / output best tree]
```

## MPI Communication
- **Coarse-grained**: independent tree searches on different MPI ranks
- **Fine-grained**: alignment sites distributed across threads within a rank
- **Collective**: `MPI_Allreduce` for likelihood aggregation across ranks

## I/O Points
- Checkpoint: `.ckp` file with full search state (written automatically)
- Output: `.raxml.bestTree`, `.raxml.log`, `.raxml.bestModel`
