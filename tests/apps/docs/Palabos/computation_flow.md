# Palabos Computation Flow

## Overview
Palabos solves fluid dynamics using the Lattice Boltzmann Method (LBM). Each timestep is a pipeline of collision, streaming, and boundary condition stages on a fixed Cartesian lattice distributed across MPI ranks.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Create lattice] --> B[Time step loop]
    B --> C["Collision: apply BGK/MRT on each cell"]
    C --> D["Streaming: propagate populations to neighbors"]
    D --> D2["MPI halo exchange for boundary cells"]
    D2 --> E[Apply boundary conditions]
    E --> F["Compute macroscopic: density, velocity"]
    F --> G{Output interval?}
    G -->|Yes| H[Write VTK / checkpoint]
    H --> I{More steps?}
    G -->|No| I
    I -->|Yes| B
    I -->|No| J[MPI_Finalize]
```

## MPI Communication
- **Halo exchange**: populations at subdomain boundaries exchanged via `MPI_Sendrecv`
- **Decomposition**: 3D block decomposition of the lattice
- **Collective**: `MPI_Reduce` for global statistics

## I/O Points
- VTK output for visualization
- Checkpoint: binary lattice state via `saveBinaryBlock`/`loadBinaryBlock`

## Output Format
VTK files for visualization. Checkpoint is a binary block containing all population values per cell. Stdout prints step number and macroscopic quantities.
**How to compare**: compare checkpoint binary files byte-for-byte (hash), or extract density/velocity fields and compare with numeric tolerance ~1e-10.
