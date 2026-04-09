# miniFE Computation Flow

## Overview
miniFE is a proxy application for unstructured implicit finite element codes. It generates a simple 3D hex mesh, assembles a sparse linear system (stiffness matrix and load vector), and solves it using a conjugate gradient (CG) iterative solver. Each MPI rank owns a contiguous block of mesh nodes; the sparse matrix is distributed by rows across ranks.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Generate hex mesh] --> B[Assemble sparse matrix A and RHS vector b]
    B --> C[Initialize CG solver: r = b - A*x, p = r]
    C --> D[CG iteration loop]
    D --> E[SpMV: w = A * p]
    E --> F[MPI halo exchange for p]
    F --> G[dot product: p^T * w — MPI_Allreduce]
    G --> H[alpha = r^T*r / p^T*w]
    H --> I[Update x = x + alpha*p]
    I --> J[Update r = r - alpha*w]
    J --> K[dot product: r^T*r — MPI_Allreduce]
    K --> L{Converged or max iters?}
    L -->|No| M[beta = r_new^T*r_new / r_old^T*r_old]
    M --> N[Update p = r + beta*p]
    N --> D
    L -->|Yes| O[MPI_Finalize + Output]
```

## MPI Communication Pattern
- **Halo exchange**: `MPI_Isend`/`MPI_Irecv`/`MPI_Waitall` to exchange shared node values before each SpMV; communication pattern derived from the sparse matrix non-zero structure
- **Global reductions**: `MPI_Allreduce(MPI_SUM)` for dot products (two per CG iteration: one for `p^T*w`, one for `r^T*r`)
- **Decomposition**: 1D row-based distribution of the sparse matrix; each rank owns a contiguous range of global node IDs

## I/O Points
- Final output: prints solver iteration count, final residual norm, and timing breakdown to stdout
- No intermediate file output in the default configuration
