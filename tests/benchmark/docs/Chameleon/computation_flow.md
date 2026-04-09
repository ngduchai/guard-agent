# Chameleon Computation Flow

## Overview
Chameleon provides dense linear algebra (Cholesky, LU, QR, LQ) using sequential tile-based task algorithms on distributed heterogeneous clusters. Uses StarPU or PaRSEC as interchangeable task runtime backends.

## Main Loop
```mermaid
flowchart TD
    A[MPI_Init + StarPU init] --> B[Create tile matrix descriptors]
    B --> C[Submit tile tasks to runtime]
    C --> D[StarPU/PaRSEC scheduler]
    D --> D1[POTRF: factor diagonal tile]
    D1 --> D2[TRSM: solve panel tiles]
    D2 --> D3[SYRK/GEMM: update trailing tiles]
    D --> E{DAG complete?}
    E -->|No| D
    E -->|Yes| F[Synchronize + gather result]
    F --> G[Finalize runtimes + MPI_Finalize]
```

## MPI Communication
- Handled by StarPU-MPI or PaRSEC (automatic, asynchronous)
- 2D block-cyclic tile distribution
- Data transfers triggered by task dependencies

## I/O Points
- Matrix generated in-memory, result verified via residual norm
