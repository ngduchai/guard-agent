# Palabos Computation Flow

## Overview
Palabos solves fluid dynamics using the Lattice Boltzmann Method (LBM). Each timestep is a pipeline of collision, streaming, and boundary condition stages on a fixed Cartesian lattice distributed across MPI ranks.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Create lattice] --> B[Time step loop]
    B --> C[Collision step]
    C --> C1[Apply BGK/MRT collision on each cell]
    C --> D[Streaming step]
    D --> D1[Propagate populations to neighbor cells]
    D1 --> D2[MPI halo exchange for boundary cells]
    D --> E[Boundary conditions]
    E --> F[Compute macroscopic quantities]
    F --> F1[density, velocity from populations]
    F --> G{Output interval?}
    G -->|Yes| H[Write VTK / checkpoint]
    G -->|No| I{More steps?}
    H --> I
    I -->|Yes| B
    I -->|No| J[MPI_Finalize]
```

## MPI Communication
- **Halo exchange**: populations at subdomain boundaries exchanged via MPI_Sendrecv
- **Decomposition**: 3D block decomposition of the lattice
- **Collective**: MPI_Reduce for global statistics (average velocity, etc.)

## I/O Points
- VTK output for visualization
- Checkpoint: binary lattice state via saveBinaryBlock/loadBinaryBlock
