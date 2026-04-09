# deal.II Computation Flow

## Overview
deal.II is an adaptive finite element framework. A typical simulation iteratively refines the mesh based on error estimators, solves the PDE on each refined mesh, and outputs results. Uses MPI via p4est for distributed triangulation.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Create triangulation] --> B[Refinement cycle loop]
    B --> C[Distribute DOFs]
    C --> D[Local element assembly]
    D --> D2[Compress + communicate ghost DOFs]
    D2 --> E["Solve linear system (PETSc/Trilinos)"]
    E --> E2[MPI communication in iterative solver]
    E2 --> F[Estimate error per cell]
    F --> G[Mark cells for refinement/coarsening]
    G --> H[Execute refinement]
    H --> H1[p4est repartition + load balance]
    H1 --> I{More cycles?}
    I -->|Yes| B
    I -->|No| J[Output VTU + MPI_Finalize]
```

## MPI Communication
- **p4est**: manages distributed octree mesh, handles repartitioning
- **Linear algebra**: PETSc or Trilinos distributed vectors/matrices
- **Ghost exchange**: automatic for finite element DOF values

## I/O Points
- VTU output for visualization (per-rank files)
- Checkpoint: Triangulation serialization to file

## Output Format
```
Cycle 0:
   Number of active cells:       1024
   Number of degrees of freedom: 4225
   Solver converged in 28 iterations.
   ||u||_L2 = 0.00368
```
**How to compare**: extract `||u||_L2` norm from the final cycle; numeric comparison with tolerance ~1e-4. Or compare VTU output files with `pvpython` diff.
