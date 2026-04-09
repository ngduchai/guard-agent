# AMReX Computation Flow

## Overview
AMReX is a block-structured AMR framework. A typical application (e.g., advection) runs a time-stepping loop with subcycling across AMR levels, regridding periodically to adapt the mesh.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Initialize Amr] --> B[Time step loop]
    B --> C[Regrid check]
    C -->|Regrid needed| D[Tag cells + create new grids]
    D --> D1[MPI load balance + redistribute]
    C --> E[Advance coarse level]
    E --> F[Subcycle fine levels]
    F --> F1[Advance fine level dt/r times]
    F1 --> F2[MPI FillPatch for ghost cells]
    F --> G[Average down fine→coarse]
    G --> H{Checkpoint interval?}
    H -->|Yes| I[WriteCheckpointFile]
    H -->|No| J{More steps?}
    I --> J
    J -->|Yes| B
    J -->|No| K[MPI_Finalize]
```

## MPI Communication
- **FillPatch**: ghost cell filling via MPI for each level
- **Regridding**: redistribute boxes across ranks for load balance
- **Average down**: fine→coarse data transfer (local or MPI)

## I/O Points
- Checkpoint directories: `chk00000/`, `chk00100/`, etc.
- Plot files for visualization
