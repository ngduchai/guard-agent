# Chameleon Computation Flow

## Overview
Chameleon provides dense linear algebra (Cholesky, LU, QR, LQ) using sequential tile-based task algorithms on distributed heterogeneous clusters. Uses StarPU or PaRSEC as interchangeable task runtime backends.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + StarPU init] --> B[Create tile matrix descriptors]
    B --> C[Submit tile tasks to runtime]
    C --> D[StarPU/PaRSEC scheduler]

    subgraph dag ["Task DAG execution (tile Cholesky)"]
        direction TB
        T1["POTRF: factor diagonal tile"]
        T2["TRSM: solve panel tiles"]
        T3["SYRK/GEMM: update trailing tiles"]
        T4{All tiles processed?}
        T1 --> T2 --> T3 --> T4
        T4 -->|"No (next k)"| T1
        T4 -->|Yes| T5[DAG complete]
    end

    D --> T1
    T5 --> E[Synchronize + gather result]
    E --> F[Verify residual norm]
    F --> G[Finalize runtimes + MPI_Finalize]
```

## MPI Communication
- Handled by StarPU-MPI or PaRSEC (automatic, asynchronous)
- 2D block-cyclic tile distribution
- Data transfers triggered by task dependencies

## I/O Points
- Matrix generated in-memory, result verified via residual norm

## Output Format
```
||Ax-b||/(||A||*||x||+||b||) = 1.87e-16
Time: 0.35s  Gflop/s: 5.71
```
**How to compare**: verify residual norm < machine epsilon (~1e-14). This is the built-in correctness metric.
