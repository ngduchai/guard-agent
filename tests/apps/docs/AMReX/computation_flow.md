# AMReX Computation Flow

## Overview
AMReX is a block-structured AMR framework. A typical application runs a time-stepping loop with subcycling across AMR levels, regridding periodically to adapt the mesh.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Initialize Amr] --> B[Time step loop]
    B --> C{Regrid needed?}
    C -->|Yes| D[Tag cells + create new grids]
    D --> D1[MPI load balance + redistribute]
    D1 --> E[Advance coarse level]
    C -->|No| E
    E --> F[Subcycle fine levels]
    F --> F1["Advance fine level dt/r times"]
    F1 --> F2["MPI FillPatch for ghost cells"]
    F2 --> G[Average down fine → coarse]
    G --> H{Checkpoint interval?}
    H -->|Yes| I[WriteCheckpointFile]
    I --> J{More steps?}
    H -->|No| J
    J -->|Yes| B
    J -->|No| K[MPI_Finalize]
```

## MPI Communication
- **FillPatch**: ghost cell filling via MPI for each level
- **Regridding**: redistribute boxes across ranks for load balance
- **Average down**: fine → coarse data transfer (local or MPI)

## I/O Points
- Checkpoint directories: `chk00000/`, `chk00100/`, etc.
- Plot files for visualization

## Output Format
Checkpoint directories contain a `Header` text file + per-level `Level_N/` subdirectories with binary MultiFab data. Plotfiles have the same structure.
**How to compare**: use AMReX's `fcompare` tool or compare Header files for metadata and MultiFab data via binary diff or numeric tolerance.
