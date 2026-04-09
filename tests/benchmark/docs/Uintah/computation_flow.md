# Uintah Computation Flow

## Overview
Uintah is a task-based AMR framework using a DAG scheduler. Applications express computation as tasks with data dependencies; the runtime schedules execution and manages MPI communication.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + Parse input .ups] --> B[Create grid + DataWarehouse]
    B --> C[Time step loop]
    C --> D[Compile task graph]
    D --> D1[Tasks declare requires/computes]
    D --> E[DAG scheduler executes tasks]
    E --> E1[Task: compute fluxes]
    E1 --> E2[Task: update state]
    E2 --> E3[MPI for ghost cells between tasks]
    E --> F[Regrid check]
    F -->|AMR| G[Refine/coarsen + load balance]
    F --> H{Checkpoint interval?}
    H -->|Yes| I[DataArchiver::output]
    H -->|No| J{More steps?}
    I --> J
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
