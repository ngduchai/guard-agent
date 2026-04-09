# AMG Computation Flow

## Overview
AMG (Algebraic Multigrid) is a parallel algebraic multigrid solver proxy application from LLNL. It solves large sparse linear systems arising from structured-grid discretizations using a multigrid V-cycle preconditioner with a Krylov solver (typically PCG or GMRES). The code sets up a Laplacian-type problem on a 3D structured grid, builds the multigrid hierarchy by coarsening, and iterates to convergence.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Setup 3D structured grid problem] --> B[Build AMG hierarchy: coarsening + interpolation]
    B --> C[Krylov solver loop — PCG]
    C --> D[Apply AMG V-cycle preconditioner]
    D --> V0["V-cycle(level 0)"]

    subgraph vcycle ["V-cycle at level ℓ"]
        direction TB
        S1["Pre-smooth: Gauss-Seidel sweeps on Aℓxℓ = bℓ"]
        S2["Compute residual: rℓ = bℓ − Aℓxℓ"]
        S3["Restrict: bℓ₊₁ = Rℓ · rℓ"]
        S4["Set xℓ₊₁ = 0"]
        S5{Is ℓ+1 coarsest?}
        S6["Direct solve: xℓ₊₁ = Aℓ₊₁⁻¹ bℓ₊₁"]
        S7["Recurse: V-cycle(ℓ+1)"]
        S8["Interpolate: xℓ ← xℓ + Pℓ · xℓ₊₁"]
        S9["Post-smooth: Gauss-Seidel sweeps on Aℓxℓ = bℓ"]
        S10[Return corrected xℓ]

        S1 --> S2 --> S3 --> S4 --> S5
        S5 -->|Yes| S6 --> S8
        S5 -->|No| S7 --> S8
        S8 --> S9 --> S10
    end

    V0 --> S1
    S10 --> E["SpMV: A · p — with halo exchange"]
    E --> F["Dot products — MPI_Allreduce"]
    F --> G[Update solution x and residual r]
    G --> H{Converged or max iters?}
    H -->|No| C
    H -->|Yes| I[MPI_Finalize + Output]
```

### V-cycle Execution Trace (3 levels)

```
PCG iteration:
  Apply V-cycle as preconditioner:
    Pre-smooth (GS) on level 0
      Restrict residual → level 1
      Pre-smooth (GS) on level 1
        Restrict residual → level 2 (coarsest)
        Direct solve on level 2
        Interpolate correction → level 1
      Post-smooth (GS) on level 1
    Interpolate correction → level 0
    Post-smooth (GS) on level 0        ← V-cycle ends here
  SpMV: compute A·p
  Dot products (MPI_Allreduce)
  Update x and r
  Check convergence → loop or exit
```

## MPI Communication Pattern
- **Halo exchange**: `MPI_Isend`/`MPI_Irecv`/`MPI_Waitall` for exchanging ghost values at each grid level during smoothing and SpMV; 26-neighbor stencil communication on structured grids
- **Global reductions**: `MPI_Allreduce(MPI_SUM)` for dot products in PCG (two per iteration), and `MPI_Allreduce(MPI_MAX)` for convergence checks
- **Coarse grid**: coarsest level may be replicated or gathered to a subset of ranks for direct solve
- **Decomposition**: 3D block decomposition of the structured grid

## I/O Points
- Final output: prints iteration count, final residual norm, convergence factor, and timing breakdown to stdout
- No intermediate file output in the default configuration
- Problem setup parameters specified via command-line arguments
