# deal.II Computation Flow

## Overview
deal.II is an adaptive finite element framework. A typical simulation iteratively refines the mesh based on error estimators, solves the PDE on each refined mesh, and outputs results. Uses MPI via p4est for distributed triangulation.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Create triangulation] --> B[Refinement cycle loop]
    B --> C[Distribute DOFs]
    C --> D[Assemble system matrix + RHS]
    D --> D1[Local element assembly]
    D1 --> D2[Compress + communicate ghost DOFs]
    D --> E[Solve linear system]
    E --> E1[PETSc/Trilinos iterative solver]
    E1 --> E2[MPI communication in solver]
    E --> F[Estimate error]
    F --> G[Mark cells for refinement/coarsening]
    G --> H[Execute refinement]
    H --> H1[p4est repartition + load balance]
    H --> I{More cycles?}
    I -->|Yes| B
    I -->|No| J[Output + MPI_Finalize]
```

## MPI Communication
- **p4est**: manages distributed octree mesh, handles repartitioning
- **Linear algebra**: PETSc or Trilinos distributed vectors/matrices
- **Ghost exchange**: automatic for finite element DOF values

## I/O Points
- VTU output for visualization (per-rank files)
- Checkpoint: Triangulation serialization to file
