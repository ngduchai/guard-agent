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
    D1 --> D2["Fill ghost cells via RefineSchedule (MPI)"]
    D2 --> E["Synchronize: coarsen fine → coarse"]
    E --> F{Regrid needed?}
    F -->|Yes| G["GriddingAlgorithm: cluster + load balance"]
    G --> G1[Redistribute patches across ranks]
    G1 --> H{Checkpoint interval?}
    F -->|No| H
    H -->|Yes| I["RestartManager::writeRestartFile"]
    I --> J{More steps?}
    H -->|No| J
    J -->|Yes| C
    J -->|No| K[MPI_Finalize]
```

## MPI Communication
- **RefineSchedule**: fill ghost cells (MPI + local copy)
- **CoarsenSchedule**: synchronize fine → coarse
- **Load balancing**: redistribute patches across ranks during regrid

## I/O Points
- Restart files: HDF5-based via RestartManager
- Visualization: VisIt data files

## Output Format
Restart is HDF5-based (patch hierarchy + all patch data). Stdout prints:
```
Timestep 100: time=0.50  dt=0.005  regrid=yes  patches=1200
```
**How to compare**: compare HDF5 restart files using `h5diff`; or extract timestep/time values from stdout with numeric tolerance.
