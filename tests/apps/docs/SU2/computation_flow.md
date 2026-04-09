# SU2 Computation Flow

## Overview
SU2 solves CFD and shape optimization problems using finite volume / finite element methods on unstructured meshes. Iterative solver pipeline on a fixed mesh with implicit time stepping.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Read config] --> B[Read/partition mesh]
    B --> C[Outer iteration loop]
    C --> D[Preprocessing]
    D --> D1[Set boundary conditions]
    D --> E[Spatial integration]
    E --> E1[Compute fluxes on faces]
    E1 --> E2[MPI exchange for partition boundaries]
    E --> F[Build implicit system]
    F --> G[Linear solver iteration]
    G --> G1[FGMRES/BCGSTAB with MPI]
    G --> H[Update solution]
    H --> I[Compute residual]
    I --> I1[MPI_Allreduce for global residual]
    I --> J{Converged?}
    J -->|No| C
    J -->|Yes| K[Write restart + MPI_Finalize]
```

## MPI Communication
- **Halo exchange**: MPI_Sendrecv for solution values at partition boundaries
- **Collective**: MPI_Allreduce for global residuals, CFL computation
- **Mesh partitioning**: METIS/ParMETIS at startup

## I/O Points
- Restart files: solution state for all mesh nodes
- Surface output: forces, pressure coefficients
- Volume output: flow field visualization
