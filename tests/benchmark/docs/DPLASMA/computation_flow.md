# DPLASMA Computation Flow

## Overview
DPLASMA provides dense linear algebra operations (Cholesky, LU, QR) on distributed tile matrices using the PaRSEC task-based runtime. Tasks are scheduled dynamically based on data dependencies in a DAG.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + PaRSEC init] --> B[Create tile matrix descriptor]
    B --> C[Generate task DAG]
    C --> D[PaRSEC scheduler]
    D --> D1[Task: POTRF on diagonal tile]
    D1 --> D2[Task: TRSM on panel tiles]
    D2 --> D3[Task: SYRK/GEMM on trailing tiles]
    D --> E{All tasks complete?}
    E -->|No| D
    E -->|Yes| F[Gather result + verify]
    F --> G[PaRSEC finalize + MPI_Finalize]
```

## MPI Communication
- **Implicit**: PaRSEC runtime handles all data movement between MPI ranks
- **2D block-cyclic**: matrix tiles distributed across a process grid
- **Overlap**: communication overlapped with computation automatically

## I/O Points
- Matrix generated in-place (no file I/O for benchmarking)
- Verification: residual check printed to stdout
