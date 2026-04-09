# ExaML Computation Flow

## Overview
ExaML (Exascale Maximum Likelihood) performs phylogenetic tree inference using maximum likelihood on partitioned multi-gene datasets. MPI parallelization distributes alignment columns across ranks.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Parse alignment] --> B[Initialize random tree]
    B --> C[ML search loop]
    C --> D[Evaluate per-partition likelihood on local columns]
    D --> D2["MPI_Allreduce sum log-likelihoods"]
    D2 --> E[SPR rearrangements]
    E --> F[Optimize branch lengths]
    F --> G{Improved?}
    G -->|Yes| H[Write checkpoint]
    H --> C
    G -->|No| I[Output best tree + MPI_Finalize]
```

## MPI Communication
- **Data parallel**: alignment columns distributed cyclically across ranks
- **Collective**: `MPI_Allreduce` to sum per-site log-likelihoods
- **Broadcast**: `MPI_Bcast` for tree topology updates after SPR moves

## I/O Points
- Checkpoint: `ExaML_binaryCheckpoint.*` with tree + model params
- Final: best tree in Newick format + log-likelihood score

## Output Format
```
Final GAMMA-based Score of best tree: -12345.678901
Tree written to ExaML_result.T1
```
**How to compare**: extract the `Final GAMMA-based Score`; numeric comparison with tolerance ~1e-2 (ML scores can vary slightly across restarts due to rounding).
