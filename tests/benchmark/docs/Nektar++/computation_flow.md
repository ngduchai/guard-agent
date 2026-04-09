# Nektar++ Computation Flow

## Overview
Nektar++ solves PDEs using spectral/hp element methods with high-order polynomial bases. Time-stepping uses multi-stage schemes (e.g., IMEX for incompressible Navier-Stokes with operator splitting).

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Read session XML] --> B[Create mesh + expansion]
    B --> C[Time step loop]
    C --> D[Stage 1: Advection explicit]
    D --> D1[Evaluate nonlinear terms]
    D1 --> D2[MPI exchange for element boundaries]
    D --> E[Stage 2: Diffusion implicit]
    E --> E1[Helmholtz solve per element]
    E --> F[Stage 3: Pressure correction]
    F --> F1[Poisson solve - global CG with MPI]
    F --> G[Update velocity + pressure]
    G --> H{Checkpoint interval?}
    H -->|Yes| I[Write .fld checkpoint]
    H -->|No| J{More steps?}
    I --> J
    J -->|Yes| C
    J -->|No| K[Final output + MPI_Finalize]
```

## MPI Communication
- **Element-wise**: discontinuous Galerkin exchanges at element interfaces
- **Global solves**: CG/GMRES with MPI_Allreduce for inner products
- **Decomposition**: mesh elements distributed via METIS/SCOTCH partitioning

## I/O Points
- `.fld` field files (checkpoint/restart)
- `.chk` checkpoint files (HDF5 or XML format)
