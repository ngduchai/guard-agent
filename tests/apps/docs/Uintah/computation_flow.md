# Uintah Computation Flow

## Overview
Uintah is a task-based AMR framework using a DAG scheduler. Applications express computation as tasks with data dependencies; the runtime schedules execution and manages MPI communication.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + Parse input .ups] --> B[Create grid + DataWarehouse]
    B --> C[Time step loop]
    C --> D["Compile task graph (tasks declare requires/computes)"]
    D --> E[DAG scheduler executes tasks]
    E --> E1[Task: compute fluxes]
    E1 --> E2[Task: update state]
    E2 --> E3["MPI for ghost cells between tasks"]
    E3 --> F{Regrid needed?}
    F -->|Yes| G["Refine/coarsen + load balance"]
    G --> H{Checkpoint interval?}
    F -->|No| H
    H -->|Yes| I["DataArchiver::output"]
    I --> J{More steps?}
    H -->|No| J
    J -->|Yes| C
    J -->|No| K[MPI_Finalize]
```

## MPI Communication
- **Implicit**: scheduler handles all MPI based on task dependencies
- **Ghost cells**: automatic based on task requirements
- **Load balancing**: dynamic redistribution of patches

## I/O Points
- Checkpoint: DataArchiver writes all DataWarehouse variables
- UDA (Uintah Data Archive) directory structure

## Output Format
UDA directories contain per-timestep checkpoint data. Stdout prints:
```
Timestep 100  Time=0.50  WallTime=120.5s  Patches=800
```
**How to compare**: use Uintah's `compare_uda` tool; or compare DataWarehouse variable dumps with numeric tolerance.
