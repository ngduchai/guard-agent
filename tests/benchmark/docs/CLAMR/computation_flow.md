# CLAMR Computation Flow

## Overview
CLAMR (Cell-based Adaptive Mesh Refinement) is a mini-application from LANL that solves the shallow water equations on a 2D adaptive mesh using a finite volume method. It dynamically refines and coarsens the mesh based on solution gradients. Each MPI rank owns a partition of the adaptive mesh cells, and load balancing is performed periodically to redistribute cells as the mesh adapts.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Initialize 2D mesh + initial conditions] --> B[Time step loop]
    B --> C[Compute time step dt — CFL condition]
    C --> D[MPI_Allreduce for global min dt]
    D --> E[Halo exchange for cell state variables]
    E --> F[Compute fluxes across cell faces — finite volume]
    F --> G[Update cell state: H, U, V]
    G --> H[AMR: refine/coarsen based on gradient criteria]
    H --> I[Load balance — repartition cells across ranks]
    I --> J[Rebuild neighbor connectivity]
    J --> K{More timesteps?}
    K -->|Yes| B
    K -->|No| L[MPI_Finalize + Output]
```

## MPI Communication Pattern
- **Halo exchange**: `MPI_Isend`/`MPI_Irecv`/`MPI_Waitall` for ghost cell values (water height, velocities) across rank boundaries
- **Global reduction**: `MPI_Allreduce(MPI_MIN)` for computing the global CFL time step
- **Load balancing**: periodic repartitioning using space-filling curves (Hilbert curve); cells are migrated between ranks via `MPI_Isend`/`MPI_Irecv`
- **Decomposition**: 2D spatial decomposition with dynamic load balancing; cell count per rank changes as the mesh adapts

## I/O Points
- Graphics output: optional periodic output of mesh and solution fields for visualization (via OpenGL or file)
- Checkpoint output: native checkpoint files written periodically
- Final output: prints conservation metrics, timing, and cell counts to stdout
