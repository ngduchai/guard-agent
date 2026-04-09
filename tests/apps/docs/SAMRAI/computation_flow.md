# SAMRAI Computation Flow

## Overview
SAMRAI provides structured AMR infrastructure. Applications define physics operators; SAMRAI handles the AMR hierarchy, communication, and load balancing.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Create PatchHierarchy] --> B[Initialize levels]
    B --> C[Time step loop]
    C --> D[Advance data on all levels]
    D --> D1[Per-patch computation]
    D1 --> D2[Fill ghost cells via RefineSchedule]
    D --> E[Synchronize levels]
    E --> E1[Coarsen fine→coarse]
    E --> F[Regrid check]
    F -->|Tag cells| G[GriddingAlgorithm regrid]
    G --> G1[Cluster + load balance + redistribute]
    F --> H{Checkpoint interval?}
    H -->|Yes| I[RestartManager::writeRestartFile]
    H -->|No| J{More steps?}
    I --> J
    J -->|Yes| C
    J -->|No| K[MPI_Finalize]
```

## MPI Communication
- **RefineSchedule**: fill ghost cells (MPI + local copy)
- **CoarsenSchedule**: synchronize fine→coarse
- **Load balancing**: redistribute patches across ranks during regrid

## I/O Points
- Restart files: HDF5-based via RestartManager
- Visualization: VisIt data files
