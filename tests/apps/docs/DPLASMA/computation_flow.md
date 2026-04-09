# DPLASMA Computation Flow

## Overview
DPLASMA provides dense linear algebra operations (Cholesky, LU, QR) on distributed tile matrices using the PaRSEC task-based runtime. Tasks are scheduled dynamically based on data dependencies in a DAG.

## Main Loop

```mermaid
flowchart TD
    A[MPI_Init + PaRSEC init] --> B[Create tile matrix descriptor]
    B --> C[Generate task DAG for factorization]
    C --> D[PaRSEC scheduler executes DAG]

    subgraph dag ["Task DAG execution (tile Cholesky example)"]
        direction TB
        T1["POTRF: factor diagonal tile (k,k)"]
        T2["TRSM: solve panel tiles (i,k) using L(k,k)"]
        T3["SYRK/GEMM: update trailing tiles (i,j)"]
        T4{All tiles processed?}
        T1 --> T2 --> T3 --> T4
        T4 -->|"No (next k)"| T1
        T4 -->|Yes| T5[DAG complete]
    end

    D --> T1
    T5 --> E[Gather result + verify residual]
    E --> F[PaRSEC finalize + MPI_Finalize]
```

## MPI Communication
- **Implicit**: PaRSEC runtime handles all data movement between ranks
- **2D block-cyclic**: tiles distributed across a process grid
- **Overlap**: communication overlapped with computation automatically

## I/O Points
- Matrix generated in-place (no file I/O for benchmarking)
- Verification: residual check printed to stdout

## Output Format
```
[****] TIME(s)     0.42 : dpotrf  N= 1000  NB= 200  P= 2  Q= 2  NTH= 1  : 4.762 gflops
       ||Ax-b|| / (||A||*||x||+||b||) = 2.34e-16
```
**How to compare**: verify residual norm is below machine epsilon (~1e-14 for double). The residual line is the correctness check.
